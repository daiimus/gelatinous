# =============================================================================
# CORPSE OBJECT - Just-In-Time Decay System
# =============================================================================

from .items import Item
from .identity_bearer import IdentityBearerMixin
import time

class Corpse(IdentityBearerMixin, Item):
    """
    A corpse object that preserves forensic data and uses just-in-time decay.
    Decay is calculated on-demand when the corpse is looked at or referenced,
    rather than using continuous scripts.
    """
    
    def at_object_creation(self):
        """Initialize corpse with decay tracking."""
        super().at_object_creation()
        
        # Core corpse properties
        self.db.is_corpse = True
        self.db.creation_time = time.time()
        
        # Preserve original descriptions for decay calculations
        self.db.base_description = self.db.desc if self.db.desc is not None else ''
        self.db.base_longdesc = {}
        
        # Forensic data (set by death progression script)
        self.db.original_character_name = "someone"
        self.db.original_character_dbref = None  # Character object dbref
        self.db.original_account_dbref = None    # Account object dbref
        self.db.death_time = time.time()
        self.db.death_cause = "unknown"
        self.db.medical_conditions = []
        self.db.physical_description = ""
        self.db.longdesc_data = {}

        # Death-time medical snapshot (PR #186 / Issue #186).  Set by
        # :meth:`typeclasses.death_progression.DeathProgression._create_corpse_from_character`
        # to ``character.medical_state.to_dict()``.  Read via
        # :meth:`get_medical_snapshot`.  Surgical commands (harvest /
        # sever) mutate this in place; the autopsy report renders from
        # it.  Pre-PR-186 corpses still in the live DB carry ``None``;
        # consumers degrade gracefully.  Two PR-186 sibling lists track
        # what has been physically removed from the corpse since death:
        #
        # * ``removed_organs``: list of organ names that the
        #   :class:`commands.surgery.CmdHarvest` flow has extracted.
        # * ``severed_locations``: list of body-location names that
        #   :class:`commands.surgery.CmdSever` has removed.
        #
        # Both lists are initialised empty so the harvest/sever code
        # can ``append`` without a None-guard, and the autopsy report
        # uniformly renders "absent" for any organ present in either.
        self.db.medical_state_at_death = None
        self.db.removed_organs = []
        self.db.severed_locations = []

        # PR #208: tracks whether the head has been severed off this
        # corpse.  Identity-bearing snapshot fields
        # (``signature_at_death``, ``apparent_uid_at_death``,
        # ``sleeve_uid``) stay populated so ``autopsy`` and
        # :func:`world.forensics.extract_subject_from_corpse` keep
        # working — but :meth:`get_display_name` reads this flag and
        # short-circuits to the decay-stage fallback when ``True``,
        # suppressing both natural and forensic look-time recognition.
        # Set by :func:`typeclasses.items.apply_severed_head_overlay`.
        self.db.head_severed = False
        
        # Preserve character appearance data for proper display
        self.db.original_skintone = None
        self.db.original_gender = "neutral"
        
        # Decay settings
        self.db.decay_stages = {
            "fresh": 3600,      # < 1 hour
            "early": 86400,     # < 1 day
            "moderate": 259200, # < 3 days  
            "advanced": 604800, # < 1 week
            "skeletal": float('inf')  # > 1 week
        }

        # Issue #230: pre-populate all decay-stage aliases at creation so
        # ``target corpse`` / ``harvest organ from rotting corpse`` work
        # from t=0 regardless of which stage we're currently in.  Aliases
        # are append-only and stage progression is monotonic, so pre-
        # adding every stage's name covers the corpse's whole lifetime
        # without ever needing alias mutation on look.
        self._seed_decay_aliases_and_key()

    def _seed_decay_aliases_and_key(self):
        """Set the initial ``key`` and pre-add every decay-stage alias.

        Called once from :meth:`at_object_creation`.  Idempotent — safe
        to call again from migration tooling if needed.  Combines the
        stage-independent aliases (``corpse``, ``remains``, ``body``)
        with the per-stage display names from the species registry so
        search / targeting works at any stage without on-look mutation.
        """
        from world.anatomy import get_species_corpse_name

        species = self.db.species or "human"
        stage_names = {
            get_species_corpse_name(species, stage)
            for stage in ("fresh", "early", "moderate", "advanced", "skeletal")
        }
        # Stage-independent aliases — always valid regardless of decay.
        base_aliases = {"corpse", "remains", "body"}
        desired = stage_names | base_aliases

        current = set(self.aliases.all())
        for alias in desired:
            if alias not in current:
                self.aliases.add(alias)

        # Initial key: the fresh-stage name.  The room decay check
        # (see ``_refresh_decay_key_if_changed``) advances this lazily
        # on character entry as stages transition.
        fresh_name = get_species_corpse_name(species, "fresh")
        if self.key != fresh_name:
            self.key = fresh_name
    
    def get_decay_stage(self):
        """Calculate current decay stage based on time elapsed."""
        elapsed = time.time() - self.db.creation_time
        
        for stage, threshold in self.db.decay_stages.items():
            if elapsed < threshold:
                return stage
        return "skeletal"
    
    def get_decay_factor(self):
        """Get decay factor (0.0 = fresh, 1.0 = fully decayed)."""
        elapsed = time.time() - self.db.creation_time
        max_decay_time = self.db.decay_stages["advanced"]  # 1 week
        return min(1.0, elapsed / max_decay_time)

    def get_medical_snapshot(self):
        """Return the death-time medical-state snapshot, if any.

        The snapshot is :meth:`world.medical.core.MedicalState.to_dict`
        captured at the moment of corpse creation (see
        :meth:`typeclasses.death_progression.DeathProgression._create_corpse_from_character`).

        Pre-PR-#186 corpses still in the live DB return ``None``;
        consumers should degrade gracefully (autopsy renders identity
        axes only, harvest/sever refuse with a "no internal
        examination possible" message).

        Surgical commands mutate the returned dict in place and then
        re-assign it to ``self.db.medical_state_at_death`` to persist;
        callers must respect that mutation contract — do not treat the
        dict as read-only.

        Returns:
            dict | None: The serialized medical state, or ``None`` if
            no snapshot was captured.
        """
        return self.db.medical_state_at_death


    def _decay_display_name(self):
        """Return the decay-stage name used when no recognition matches.

        PR-G: delegates to the species registry so corpse fallback
        names share vocabulary with the rest of the species-aware
        naming surface (severed limbs, organs, organ-display prose).
        """
        from world.anatomy import get_species_corpse_name

        stage = self.get_decay_stage()
        species = self.db.species or "human"
        return get_species_corpse_name(species, stage)

    def get_display_name(self, looker, **kwargs):
        """Decay-stage fallback when the head has been severed.

        PR #208: a headless corpse loses the face — the dominant
        unaided-recognition cue.  When ``self.db.head_severed`` is
        ``True`` we short-circuit to the bare decay-stage name,
        suppressing both natural recognition (Pass 1 in the mixin —
        live degraded-UID lookup) and the forensic-recovery Intellect
        roll (Pass 2).  Investigators must use the explicit
        :class:`commands.forensics.CmdAutopsy` flow, which reads
        :attr:`db.signature_at_death` directly via
        :func:`world.forensics.extract_subject_from_corpse` and so
        bypasses the live-signature derivation entirely.

        Identity is *duplicated* rather than transferred on sever:
        ``signature_at_death`` / ``apparent_uid_at_death`` /
        ``sleeve_uid`` remain populated so the autopsy path keeps
        working.  Only the look-time tertiary recognition is
        suppressed here.

        We invoke :class:`IdentityBearerMixin` explicitly rather than
        through ``super()`` so duck-typed test fakes that bind this
        method onto a non-mixin class (see
        :class:`world.tests.test_corpse_decay_recognition._FakeDecayCorpse`)
        still resolve the recognition pipeline correctly.
        """
        if self.db.head_severed:
            return self._decay_display_name()
        return IdentityBearerMixin.get_display_name(self, looker, **kwargs)

    # ------------------------------------------------------------------
    # Disguise / identity signature surface
    # ------------------------------------------------------------------

    @property
    def sleeve_uid(self):
        """Expose the deceased's sleeve UID via the property surface.

        :func:`world.identity.get_apparent_uid` reads
        ``getattr(char, "sleeve_uid", None)`` rather than ``char.db.*``;
        mirroring the Character property here lets the corpse flow
        through the same identity pipeline without a separate code
        path.
        """
        return self.db.sleeve_uid

    def get_worn_items(self, location=None):
        """Return disguise-essential items still on the corpse.

        Corpses do not maintain a separate ``worn_items`` map — when a
        character dies, their kit drops into ``corpse.contents`` (and is
        treated as "still worn" for coverage purposes by
        :meth:`_build_corpse_clothing_coverage_map`).  Mirroring
        :meth:`typeclasses.clothing_mixin.ClothingMixin.get_worn_items`
        here lets :func:`world.identity.get_essential_item_type_ids`
        recompute the signature naturally as items are looted.

        Only items flagged ``disguise_essential`` are returned — that is
        all the signature pipeline consumes, and it avoids accidentally
        treating loose loot in the corpse's inventory as worn clothing.

        Args:
            location: Accepted for signature parity with the mixin;
                ignored because corpses have no per-location worn map.

        Returns:
            List of disguise-essential items currently in
            ``self.contents``.
        """
        del location  # parity with ClothingMixin.get_worn_items signature
        return [
            item
            for item in self.contents
            if getattr(item, "disguise_essential", False)
        ]

    def _get_preserved_longdesc_descriptions(self):
        """Get visible longdesc descriptions with clothing integration, like living characters.

        Symmetric ``left_*`` / ``right_*`` pairs collapse to a single
        plural line when both sides carry the same preserved longdesc
        and neither is covered by clothing — matching the living-
        character collapse path (\``AppearanceMixin._build_paired_longdesc_collapse``\)
        so braced body-noun tokens (``{eyes}`` / ``{ears}`` / ...) render
        in plural form once, instead of leaking literal braces twice.
        """
        if not self.db.longdesc_data:
            return []

        # Import anatomical display order
        try:
            from world.combat.constants import (
                ANATOMICAL_DISPLAY_ORDER,
                PAIR_MERGE_KEYS,
            )
        except ImportError:
            # Fallback order if constants not available
            ANATOMICAL_DISPLAY_ORDER = [
                "hair", "left_eye", "right_eye", "head", "face", "left_ear", "right_ear", "neck",
                "chest", "back", "abdomen", "groin",
                "left_arm", "right_arm", "left_hand", "right_hand",
                "left_thigh", "right_thigh", "left_shin", "right_shin", "left_foot", "right_foot"
            ]
            PAIR_MERGE_KEYS = {}

        descriptions = []
        longdesc_data = self.db.longdesc_data

        # Build clothing coverage map from corpse contents
        coverage_map = self._build_corpse_clothing_coverage_map()
        added_clothing_items = set()

        # Pre-compute symmetric pair collapse: which left_* anchors absorb
        # their right_* partner under a single plural render.
        collapse_anchor = {}  # left_loc -> plural-rendered description
        collapse_skip = set()  # right_loc partners to skip
        for _pair_key, (left_loc, right_loc) in PAIR_MERGE_KEYS.items():
            # Asymmetric clothing breaks the visual pairing.
            if left_loc in coverage_map or right_loc in coverage_map:
                continue
            left_desc = longdesc_data.get(left_loc)
            right_desc = longdesc_data.get(right_loc)
            if not left_desc or not right_desc:
                continue
            if left_desc != right_desc:
                continue
            # Both sides match — render once at plural number.
            processed = self._process_corpse_description_variables(
                left_desc, number="plural",
            )
            processed = self._apply_decay_to_description(processed)
            collapse_anchor[left_loc] = processed
            collapse_skip.add(right_loc)

        # Process in anatomical order, integrating clothing like living characters
        for location in ANATOMICAL_DISPLAY_ORDER:
            if location in collapse_skip:
                # Right side of a collapsed pair — already rendered at the
                # left anchor; do not render again.
                continue
            if location in coverage_map:
                # Location covered by clothing - use clothing description instead
                clothing_item = coverage_map[location]

                # Only add each clothing item once, regardless of how many locations it covers
                if clothing_item not in added_clothing_items:
                    # Get clothing description for corpse context
                    desc = self._get_clothing_desc_for_corpse(clothing_item, location)
                    if desc:
                        descriptions.append((location, desc))
                        added_clothing_items.add(clothing_item)
            else:
                final_desc = ""
                if location in collapse_anchor:
                    # Symmetric pair collapse — already pre-rendered above.
                    final_desc = collapse_anchor[location]
                elif location in longdesc_data and longdesc_data[location]:
                    description = longdesc_data[location]
                    # Process template variables like living characters do
                    processed_desc = self._process_corpse_description_variables(description)
                    # Apply decay modifications to the description
                    final_desc = self._apply_decay_to_description(processed_desc)

                # Add preserved wound descriptions for this location
                wound_descriptions = self.get_preserved_wound_descriptions(location)
                if wound_descriptions:
                    wound_text = " ".join(wound_descriptions)
                    if final_desc:
                        final_desc = f"{final_desc} {wound_text}"
                    else:
                        # No base description, just use wound descriptions
                        final_desc = wound_text

                if final_desc:
                    descriptions.append((location, final_desc))

        return descriptions
    
    def _build_corpse_clothing_coverage_map(self):
        """Build a map of body locations covered by clothing items in corpse."""
        coverage_map = {}
        
        # Get clothing items from corpse contents
        clothing_items = []
        for item in self.contents:
            # Check if item appears to be clothing (has coverage attribute)
            if item.db.coverage:
                clothing_items.append(item)
        
        # For each clothing item, map its coverage to body locations
        for item in clothing_items:
            coverage = item.db.coverage or []
            for location in coverage:
                # Use outermost item (last one wins for now - could be enhanced)
                coverage_map[location] = item
        
        return coverage_map
    
    def get_preserved_wound_descriptions(self, location=None):
        """
        Get wound descriptions for this corpse based on preserved wound data.
        
        Args:
            location (str, optional): Specific body location to check. If None, returns all wounds.
            
        Returns:
            list: List of wound description strings for the location(s)
        """
        wound_descriptions = []
        
        # Get preserved wound data
        wounds_at_death = self.db.wounds_at_death or []
        if not wounds_at_death:
            return wound_descriptions
        
        # Filter by location if specified
        relevant_wounds = wounds_at_death
        if location:
            relevant_wounds = [w for w in wounds_at_death if w.get('location') == location]
        
        # Generate descriptions for each wound
        for wound_data in relevant_wounds:
            try:
                from world.medical.wounds import get_wound_description
                
                # Generate wound description using preserved data
                wound_desc = get_wound_description(
                    injury_type=wound_data['injury_type'],
                    location=wound_data['location'],
                    severity=wound_data['severity'],
                    stage='old',  # Corpse wounds are considered 'old' stage
                    organ=wound_data.get('organ'),
                    character=self  # Pass corpse as character for any skintone processing
                )
                
                if wound_desc:
                    wound_descriptions.append(wound_desc)
                    
            except Exception as e:
                # Don't break corpse display if wound description fails
                try:
                    from evennia.comms.models import ChannelDB
                    from world.combat.constants import SPLATTERCAST_CHANNEL
                    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                    splattercast.msg(f"CORPSE_WOUND_ERROR: Failed to generate wound description for {self.key}: {e}")
                except Exception:
                    pass
                continue
        
        return wound_descriptions
    
    def _get_clothing_desc_for_corpse(self, clothing_item, location):
        """Get clothing description for corpse context."""
        # Set item context for color processing
        self._current_item_context = clothing_item
        
        # Try to get worn description first
        worn_desc = clothing_item.db.worn_desc
        if worn_desc:
            # Process template variables like living characters do
            processed_desc = self._process_corpse_description_variables(worn_desc)
            
            # Modify for corpse context - change "you" to "the corpse"
            corpse_desc = processed_desc.replace("You are wearing", "The corpse is wearing")
            corpse_desc = corpse_desc.replace("you are wearing", "the corpse is wearing")
            corpse_desc = corpse_desc.replace("Your", "The corpse's")
            corpse_desc = corpse_desc.replace("your", "the corpse's")
            
            # Ensure the description ends with proper punctuation
            corpse_desc = corpse_desc.strip()
            if corpse_desc and not corpse_desc.endswith(('.', '!', '?')):
                corpse_desc += '.'
            
            # Clear item context
            if hasattr(self, '_current_item_context'):
                delattr(self, '_current_item_context')
            
            # Apply decay modifications
            return self._apply_decay_to_description(corpse_desc)
        
        # Fallback to item description
        item_desc = clothing_item.db.desc
        if item_desc:
            # Process template variables
            processed_desc = self._process_corpse_description_variables(item_desc)
            
            # Create a simple worn description
            item_name = clothing_item.get_display_name(None)
            corpse_desc = f"The corpse is wearing {item_name}."
            
            # Clear item context
            if hasattr(self, '_current_item_context'):
                delattr(self, '_current_item_context')
                
            return self._apply_decay_to_description(corpse_desc)
        
        # Clear item context
        if hasattr(self, '_current_item_context'):
            delattr(self, '_current_item_context')
        
        return None
    
    def _format_corpse_longdescs(self, longdesc_list):
        """
        Format the longdesc descriptions for corpse display with smart paragraph breaks.
        
        Uses the same intelligent paragraph formatting as living characters for readability.
        """
        if not longdesc_list:
            return ""
        
        # Use the character's smart paragraph formatting logic
        try:
            from world.combat.constants import (
                PARAGRAPH_BREAK_THRESHOLD, 
                ANATOMICAL_REGIONS,
                REGION_BREAK_PRIORITY
            )
        except ImportError:
            # Fallback to simple formatting if constants not available
            descriptions = [desc for location, desc in longdesc_list]
            return " ".join(descriptions)
        
        paragraphs = []
        current_paragraph = []
        current_char_count = 0
        current_region = None
        
        for location, description in longdesc_list:
            # Determine which anatomical region this location belongs to
            location_region = self._get_anatomical_region(location)
            
            # Check if we should break for a new paragraph
            should_break = False
            
            if REGION_BREAK_PRIORITY and current_region and location_region != current_region:
                # Region changed - check if we should break
                if current_char_count >= PARAGRAPH_BREAK_THRESHOLD * 0.7:  # 70% threshold for region breaks
                    should_break = True
            elif current_char_count + len(description) > PARAGRAPH_BREAK_THRESHOLD:
                # Would exceed threshold - break now
                should_break = True
            
            if should_break and current_paragraph:
                # Finish current paragraph and start new one
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
                current_char_count = 0
            
            # Add description to current paragraph
            current_paragraph.append(description)
            current_char_count += len(description) + 1  # +1 for space
            current_region = location_region
        
        # Add final paragraph
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))
        
        return "\n\n".join(paragraphs)
    
    def _get_anatomical_region(self, location):
        """
        Determines which anatomical region a location belongs to.
        
        Args:
            location: Body location string
            
        Returns:
            str: Region name or 'extended' for non-standard anatomy
        """
        try:
            from world.combat.constants import ANATOMICAL_REGIONS
            
            for region_name, locations in ANATOMICAL_REGIONS.items():
                if location in locations:
                    return region_name
            return "extended"
        except ImportError:
            # Fallback if constants not available
            return "extended"
    
    def _process_corpse_description_variables(self, description, number="singular"):
        """Process template variables in corpse descriptions using preserved character data.

        Args:
            description (str): Raw longdesc prose, possibly containing brace tokens.
            number (str): ``"singular"`` (default) or ``"plural"`` — drives
                body-noun and verb flexing in ``substitute_pronoun_tokens``.
                Pass ``"plural"`` for a collapsed symmetric pair so
                ``{eyes}`` / ``{ears}`` / ``{hands}`` render in plural form.
        """
        if not description:
            return description

        # Get preserved character data for template processing
        original_name = self.db.original_character_name or "the corpse"

        # Manual processing using preserved character data (more reliable than character method)
        processed_desc = description

        # Get preserved character data
        original_gender = self.db.original_gender if self.db.original_gender is not None else 'neutral'
        original_skintone = self.db.original_skintone
        
        # Process color templates FIRST (before other processing)
        if hasattr(self, '_current_item_context'):
            # If we have item context, use the item's color
            item = getattr(self, '_current_item_context', None)
            if item and item.db.color:
                # Get the proper color code from COLOR_DEFINITIONS
                try:
                    from typeclasses.items import COLOR_DEFINITIONS
                    color_name = item.db.color
                    color_code = COLOR_DEFINITIONS.get(color_name, "")
                    if color_code:
                        # Replace {color} with proper color code and space
                        processed_desc = processed_desc.replace("{color}", f"{color_code}")
                    else:
                        # No color definition found, just remove the tag
                        processed_desc = processed_desc.replace("{color}", "")
                    
                except ImportError:
                    # Fallback if COLOR_DEFINITIONS not available
                    processed_desc = processed_desc.replace("{color}", "")
            else:
                processed_desc = processed_desc.replace("{color}", "")
        else:
            # No item context, just remove color tags
            processed_desc = processed_desc.replace("{color}", "")
        
        # Process gender pronouns and name tokens (always third person
        # for corpses).  Delegated to the shared pure helper so the
        # severed-part renderer (Appendage.return_appearance) and this
        # path stay byte-for-byte consistent.  ``{color}`` / skintone
        # handling stays corpse-side because it depends on item context.
        from world.anatomy import substitute_pronoun_tokens

        processed_desc = substitute_pronoun_tokens(
            processed_desc,
            gender=original_gender,
            name=original_name,
            number=number,
        )
        
        # Apply skintone coloring if preserved (only to body descriptions, not clothing items)
        if original_skintone and not hasattr(self, '_current_item_context'):
            try:
                from world.combat.constants import SKINTONE_PALETTE
                color_code = SKINTONE_PALETTE.get(original_skintone)
                if color_code:
                    # Apply skintone color to ALL body part descriptions
                    processed_desc = f"{color_code}{processed_desc}|n"
            except ImportError:
                # Fallback if constants not available
                pass
        
        return processed_desc
    
    def _apply_decay_to_description(self, description):
        """Modify a description based on current decay stage."""
        stage = self.get_decay_stage()
        
        decay_modifiers = {
            "fresh": "",  # No modification for fresh corpses
            "early": " The area shows early signs of pallor and cooling.",
            "moderate": " Visible discoloration and early decomposition changes are apparent.",
            "advanced": " Severe decomposition changes have altered the appearance significantly.", 
            "skeletal": " Only skeletal remains and dried tissue are visible."
        }
        
        modifier = decay_modifiers.get(stage, "")
        return f"{description}{modifier}"
    
    def return_appearance(self, looker, **kwargs):
        """Render the corpse without mutating any persistent state.

        Issue #230: previously this method called
        ``_update_decay_descriptions`` which wrote ``self.key``,
        ``self.aliases``, and ``self.db.desc`` on every look — a pure
        read with persistent side effects.  Aliases and the initial
        ``key`` are now seeded at creation
        (:meth:`_seed_decay_aliases_and_key`); ``key`` refresh on stage
        transition runs from the room's character-entry hook
        (:meth:`_refresh_decay_key_if_changed`); and the staged decay
        paragraph is computed on the fly here.  Result: ``look`` is a
        pure read.
        """
        # Lifecycle event (deletes the corpse) — acceptable mutation;
        # not a "render" side effect.
        if self._handle_complete_decay():
            return None

        stage = self.get_decay_stage()

        # Build appearance similar to character with preserved longdesc data.
        parts = []

        # 1. Corpse name and main description (computed per current stage).
        name_and_desc = [self.get_display_name(looker)]
        decay_paragraph = self._build_decay_desc_paragraph(stage)
        if decay_paragraph:
            name_and_desc.append(decay_paragraph)
        parts.append('\n'.join(name_and_desc))

        # 2. Display preserved longdesc data with clothing integration.
        if self.db.longdesc_data:
            longdesc_descriptions = self._get_preserved_longdesc_descriptions()
            if longdesc_descriptions:
                formatted_longdesc = self._format_corpse_longdescs(longdesc_descriptions)
                parts.append(formatted_longdesc)

        return '\n\n'.join(parts)
    
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when an object is moved to this corpse."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        # Clear any cached appearance data since contents changed
        if hasattr(self.ndb, 'cached_appearance'):
            delattr(self.ndb, 'cached_appearance')
        
        # Debug logging removed to reduce noise
    
    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Called when an object leaves this corpse."""
        super().at_object_leave(moved_obj, target_location, **kwargs)
        # Clear any cached appearance data since contents changed
        if hasattr(self.ndb, 'cached_appearance'):
            delattr(self.ndb, 'cached_appearance')

        # If a disguise-essential item was looted, the corpse's
        # signature has shifted: the previously-snapshot
        # ``apparent_uid_at_death`` is now stale and observers who only
        # remember the disguised UID should silently stop recognising
        # the corpse.  We do *not* recompute and store a new UID here:
        # :func:`world.identity.get_apparent_uid` re-derives lazily from
        # the live ``get_worn_items()`` view on every display, so a
        # stored value would only drift.  Clearing the snapshot is
        # enough to signal "the death-time presentation is gone".
        if getattr(moved_obj, "disguise_essential", False):
            if self.db.apparent_uid_at_death is not None:
                self.db.apparent_uid_at_death = None
    
    def _build_decay_desc_paragraph(self, stage):
        """Return the staged decay paragraph for ``stage``.  Pure.

        Issue #230: replaces the old ``_update_decay_descriptions``
        which wrote ``self.db.desc``.  This helper just *returns* the
        composed string; ``return_appearance`` slots it into the look
        output without persisting anything.

        Issue #232: the staged prose is now species-aware, delegating to
        :func:`world.anatomy.species.get_species_corpse_description` so a
        non-human corpse no longer reads as "human".  Unknown / ``None``
        species drop the species token entirely (the #215 convention).
        The death-time physical description is embedded into the fresh /
        early tiers by the helper.

        The death-time ``db.desc`` snapshot
        (``typeclasses/death_progression.py:682``) is preserved untouched
        for debug / admin / forensic tooling (Option α from the #230
        design discussion).
        """
        from world.anatomy import (
            get_species_corpse_description,
            substitute_pronoun_tokens,
        )

        species = self.db.species or "human"
        base_desc = self.db.physical_description or "A lifeless body."

        # Resolve any pronoun / name tokens carried over from the
        # death-time short description (e.g. ``mob_flavor`` entries that
        # use ``{Their}`` / ``{themselves}``).  Without this pass the
        # raw braces leak into the species template — see issue #319.
        #
        # The whole-body paragraph's braced verbs (``{hold}``, ``{carry}``,
        # ...) have a pronoun subject, so verb flex must follow the
        # pronoun's *number*: singular for he / she, plural for singular-
        # they.  Without this, neutral sleeves render "They holds
        # themselves" instead of "They hold themselves" (issue #321).
        original_gender = self.db.original_gender if self.db.original_gender is not None else 'neutral'
        original_name = self.db.original_character_name or "the corpse"
        verb_number = "singular" if original_gender in ("male", "female") else "plural"
        base_desc = substitute_pronoun_tokens(
            base_desc,
            gender=original_gender,
            name=original_name,
            number=verb_number,
        )

        return get_species_corpse_description(species, stage, base_desc)

    def _refresh_decay_key_if_changed(self):
        """Update ``self.key`` if the current decay stage no longer matches.

        Issue #230: called from :meth:`typeclasses.rooms.Room._check_corpse_decay`
        on character entry — a lifecycle event, NOT from ``look``.  This
        keeps ``look`` pure while still letting ``@find`` and direct
        ``self.key`` consumers see the current stage name.

        Aliases are not touched here: every decay-stage alias is
        pre-seeded at creation by :meth:`_seed_decay_aliases_and_key`,
        so search/targeting works at any stage regardless of which
        stage's name is currently in ``key``.
        """
        from world.anatomy import get_species_corpse_name

        species = self.db.species or "human"
        stage = self.get_decay_stage()
        stage_name = get_species_corpse_name(species, stage)
        if self.key != stage_name:
            self.key = stage_name
    def get_forensic_data(self):
        """Return forensic data for investigation purposes."""
        stage = self.get_decay_stage()
        
        forensic_info = {
            "original_name": self.db.original_character_name,
            "original_character_dbref": self.db.original_character_dbref,
            "original_account_dbref": self.db.original_account_dbref,
            "death_time": self.db.death_time,
            "death_cause": self.db.death_cause,
            "medical_conditions": self.db.medical_conditions,
            "decay_stage": stage,
            "time_since_death": self.get_time_since_death(),
            "identifiable": stage in ["fresh", "early", "moderate"]
        }
        
        return forensic_info
    
    def get_time_since_death(self):
        """Get human-readable time since death."""
        elapsed = time.time() - self.db.death_time
        
        if elapsed < 3600:
            minutes = int(elapsed / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif elapsed < 86400:
            hours = int(elapsed / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = int(elapsed / 86400)
            return f"{days} day{'s' if days != 1 else ''}"
    
    def get_original_character(self):
        """Get the original character object if it still exists."""
        if self.db.original_character_dbref:
            from evennia.utils.search import search_object
            chars = search_object(f"#{self.db.original_character_dbref}")
            return chars[0] if chars else None
        return None
    
    def get_original_account(self):
        """Get the original account object if it still exists.""" 
        if self.db.original_account_dbref:
            from evennia.utils.search import search_object
            accounts = search_object(f"#{self.db.original_account_dbref}")
            return accounts[0] if accounts else None
        return None
    
    def is_character_still_active(self):
        """Check if the original character is still active in the game."""
        char = self.get_original_character()
        if not char:
            return False
        # Character exists but might be in limbo or archived
        return char.location and char.location.key != "Limbo"
    
    def get_admin_info(self):
        """Get administrative information about this corpse (staff only)."""
        char = self.get_original_character()
        account = self.get_original_account()
        
        admin_info = {
            "corpse_dbref": self.dbref,
            "original_character_name": self.db.original_character_name,
            "original_character_dbref": self.db.original_character_dbref,
            "original_account_dbref": self.db.original_account_dbref,
            "character_still_exists": char is not None,
            "character_still_active": self.is_character_still_active(),
            "account_still_exists": account is not None,
            "creation_time": self.db.creation_time,
            "death_time": self.db.death_time,
            "decay_stage": self.get_decay_stage()
        }
        
        return admin_info
    
    def check_complete_decay(self):
        """Check if corpse should be completely decayed and cleaned up."""
        elapsed = time.time() - self.db.creation_time
        
        # 2 weeks for complete decay and cleanup
        complete_decay_time = 1209600  # 2 weeks in seconds
        
        return elapsed > complete_decay_time
    
    def _handle_complete_decay(self):
        """Handle complete decay - drop items and remove corpse (called when looked at)."""
        if not self.check_complete_decay():
            return False
            
        # Drop all items to the room
        if self.location:
            for item in self.contents:
                item.move_to(self.location, quiet=True)
                
        # Log the decay completion
        try:
            from evennia.comms.models import ChannelDB
            from world.combat.constants import SPLATTERCAST_CHANNEL
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"CORPSE_DECAY: {self.key} completely decayed and removed from {self.location}")
        except Exception:
            pass
            
        # Remove the corpse
        self.delete()
        return True