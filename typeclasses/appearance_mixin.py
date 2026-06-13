"""
Appearance Mixin

Provides the longdesc appearance system, body description rendering,
paragraph formatting, pronoun resolution, and the main ``return_appearance``
hook used by Evennia's ``look`` command for Character objects.

Extracted from typeclasses/characters.py in Phase 4 refactoring.
"""


class AppearanceMixin:
    """
    Mixin class providing appearance and longdesc methods.

    Methods:
        get_longdesc_appearance: Build character's longdesc appearance string.
        _get_visible_body_descriptions: Get visible descriptions integrating
            clothing with the longdesc system.
        _format_longdescs_with_paragraphs: Smart paragraph-break formatter.
        _get_anatomical_region: Determine anatomical region for a location.
        has_location: Check if character has a specific body location.
        get_available_locations: Get all body locations this character has.
        set_longdesc: Set a longdesc for a specific location.
        get_longdesc: Get longdesc for a specific location.
        return_appearance: Main appearance rendering (Evennia hook for look).
        _process_description_variables: Process template variables for
            perspective-aware text.
        _get_pronoun: Get specific pronoun based on gender and type.

    Cross-cutting concerns:
        - Calls ``self._build_clothing_coverage_map()`` from ClothingMixin.
        - Reads ``self.longdesc``, ``self.worn_items`` AttributeProperties.
        - Reads ``self.hands`` via ``self.attributes.get()``.
        - Reads ``self.gender`` property from Character core.
    """

    def get_longdesc_appearance(self, looker=None, **kwargs):
        """
        Builds and returns the character's longdesc appearance.

        Args:
            looker: Character doing the looking (optional).
            **kwargs: Additional parameters.

        Returns:
            str: Formatted appearance with base description + longdescs.
        """
        # Get base description
        base_desc = self.db.desc or ""

        # Get visible body descriptions (longdesc + clothing integration)
        visible_body_descriptions = self._get_visible_body_descriptions(looker)

        if not visible_body_descriptions:
            return base_desc

        # Combine with smart paragraph formatting
        formatted_body_descriptions = self._format_longdescs_with_paragraphs(
            visible_body_descriptions
        )

        # Combine base description with body descriptions
        if base_desc:
            return f"{base_desc}\n\n{formatted_body_descriptions}"
        else:
            return formatted_body_descriptions

    def _get_visible_body_descriptions(self, looker=None):
        """
        Get all visible descriptions, integrating clothing with existing
        longdesc system.

        Args:
            looker: Character looking (for future permission checks).

        Returns:
            list: List of (location, description) tuples in anatomical order.
        """
        # Issue #356 Phase 3: species-aware display order.
        from world.anatomy import get_species_anatomical_display_order
        species = getattr(getattr(self, "db", None), "species", None)
        ANATOMICAL_DISPLAY_ORDER = get_species_anatomical_display_order(species)

        descriptions = []
        coverage_map = self._build_clothing_coverage_map()
        longdescs = self.longdesc or {}

        # Issue #350 / PR-B: locations where an organ has been destroyed
        # in place.  The authored longdesc at any such location is
        # suppressed so the destruction wound (already in the visible
        # wound list) is the sole description — the authored prose
        # otherwise lies alongside it ("His left eye is brown" + "His
        # left eye is a smoking crater"). Coverage handling is
        # delegated to ``get_character_wounds``: a destroyed eye
        # hidden under a helmet produces no wound to suppress against,
        # so the authored prose remains as a fallback.
        destroyed_locs = self._get_destroyed_locations()

        # Pre-compute symmetric left/right pairs that collapse into a single
        # pluralized line (identical longdescs, or both cleanly severed).
        collapse_map, collapse_skip = self._build_paired_longdesc_collapse(
            looker, longdescs, coverage_map, destroyed_locs
        )

        # Issue #350 / PR-C: wound-side pair collapse for both-sides-
        # destroyed-same-mechanism.  Pre-renders one pair line at the
        # left location and skips the right; takes precedence over
        # per-side wound rendering in the loop below.
        destroyed_pair_anchor, destroyed_pair_skip = (
            self._build_destroyed_pair_collapse(
                looker, coverage_map, destroyed_locs,
            )
        )

        # Track which clothing items we've already added to avoid duplicates
        added_clothing_items = set()

        # Process in anatomical order.  Per-character anatomy beyond
        # the species template (installed augments — ANATOMY_AUGMENTS
        # SPEC §3.6) renders after the species order; an augment's
        # longdesc key not in the static list must still appear.
        render_order = list(ANATOMICAL_DISPLAY_ORDER) + [
            loc for loc in longdescs if loc not in set(ANATOMICAL_DISPLAY_ORDER)
        ]
        for location in render_order:
            if location in collapse_skip:
                # Partner of a collapsed pair; rendered at the anchor location.
                continue
            if location in destroyed_pair_skip:
                # Issue #350 / PR-C: right side of a destruction pair
                # collapse; rendered at the left anchor.
                continue
            if location in destroyed_pair_anchor:
                # Issue #350 / PR-C: both sides destroyed by same
                # mechanism — single pluralized destruction line.
                descriptions.append(
                    (location, destroyed_pair_anchor[location])
                )
                continue
            if location in collapse_map:
                descriptions.append((location, collapse_map[location]))
                continue
            if location in coverage_map:
                # Location covered by clothing - use outermost item's current worn_desc
                clothing_item = coverage_map[location]

                # Only add each clothing item once, regardless of how many
                # locations it covers
                if clothing_item not in added_clothing_items:
                    # Use new method with $pron() processing and color integration
                    desc = clothing_item.get_current_worn_desc_with_perspective(
                        looker, self
                    )
                    if desc:
                        descriptions.append((location, desc))
                        added_clothing_items.add(clothing_item)
            else:
                # Location not covered - use character's longdesc if set with
                # template variable processing.
                # Per-location render path: this branch fires when the
                # location renders independently (not as part of a paired
                # collapse), which is the single-side case. Pass the
                # side so paired body-noun tokens flex to the side-aware
                # singular form (#341): "right arm" instead of "arm".
                #
                # Issue #350 / PR-B: at a destroyed location the
                # authored longdesc is suppressed — the destruction
                # wound (rendered below by the standalone-wound path)
                # is the sole description.
                if (location in longdescs and longdescs[location]
                        and location not in destroyed_locs):
                    # Chrome-aware render: flesh → skintone, inorganic
                    # → gunmetal + deployed-module expansion (#516).
                    processed_desc = self._render_body_longdesc(
                        location, longdescs[location], looker
                    )
                    descriptions.append((location, processed_desc))
                else:
                    # No longdesc for this location, but check for standalone wounds
                    try:
                        from world.medical.wounds import (
                            get_standalone_wound_description,
                        )
                        wound_desc = get_standalone_wound_description(
                            self, location, looker
                        )
                        if wound_desc:
                            descriptions.append((location, wound_desc))
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

        # Add any extended anatomy not in default order (clothing or longdesc)
        all_locations = set(longdescs.keys()) | set(coverage_map.keys())
        for location in all_locations:
            if location not in ANATOMICAL_DISPLAY_ORDER:
                if location in collapse_skip:
                    continue
                if location in destroyed_pair_skip:
                    continue
                if location in destroyed_pair_anchor:
                    descriptions.append(
                        (location, destroyed_pair_anchor[location])
                    )
                    continue
                if location in collapse_map:
                    descriptions.append((location, collapse_map[location]))
                    continue
                if location in coverage_map:
                    # Extended location with clothing
                    clothing_item = coverage_map[location]
                    if clothing_item not in added_clothing_items:
                        desc = clothing_item.get_current_worn_desc_with_perspective(
                            looker, self
                        )
                        if desc:
                            descriptions.append((location, desc))
                            added_clothing_items.add(clothing_item)
                elif location in longdescs and longdescs[location]:
                    # Extended location with longdesc — chrome-aware
                    # render (skintone for flesh, gunmetal + deployed-
                    # module expansion for inorganic; #341 side flex
                    # and wound-append handled inside the helper).
                    processed_desc = self._render_body_longdesc(
                        location, longdescs[location], looker
                    )
                    descriptions.append((location, processed_desc))
                else:
                    # No longdesc for extended location, but check for
                    # standalone wounds
                    try:
                        from world.medical.wounds import (
                            get_standalone_wound_description,
                        )
                        wound_desc = get_standalone_wound_description(
                            self, location, looker
                        )
                        if wound_desc:
                            descriptions.append((location, wound_desc))
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

        return descriptions

    def _build_paired_longdesc_collapse(self, looker, longdescs, coverage_map,
                                        destroyed_locs=None):
        """
        Compute which symmetric left/right pairs collapse into one line.

        A ``left_*``/``right_*`` pair collapses when both sides are uncovered
        and either (a) their longdescs are identical and non-empty, or (b)
        both sides have been cleanly severed. Severance deletes a location's
        longdesc key, so a single amputated limb naturally fails the identity
        test and renders on its own — only a matched, intact (or matched,
        fully amputated) pair merges.

        Issue #350 / PR-B: if either side carries a destroyed-stage organ,
        the authored-longdesc collapse (case a) is suppressed for that
        pair — the authored prose would lie alongside the destruction
        wound. Per-side rendering takes over, and PR-C will introduce
        wound-side pair-collapse for the both-sides-destroyed case.
        Severance pair-collapse (case b) is unaffected.

        Args:
            looker: Character looking.
            longdescs (dict): The character's ``location -> desc`` mapping.
            coverage_map (dict): ``location -> clothing item`` coverage.
            destroyed_locs (set | None): Locations with destroyed-stage
                organs.  ``None`` is treated as empty (call sites that
                predate PR-B).

        Returns:
            tuple: ``(collapse_map, skip_set)`` where ``collapse_map`` maps a
                ``left_*`` anchor location to its merged description string and
                ``skip_set`` holds the ``right_*`` partners to skip.
        """
        # Issue #356 Phase 3: species-aware display order.
        from world.anatomy import get_species_anatomical_display_order
        species = getattr(getattr(self, "db", None), "species", None)
        ANATOMICAL_DISPLAY_ORDER = get_species_anatomical_display_order(species)

        collapse_map = {}
        skip_set = set()
        destroyed_locs = destroyed_locs or set()

        severed_locs = self._get_severed_locations()
        # Consider every left_* location the body could render this pass.
        sources = (
            set(longdescs)
            | set(coverage_map)
            | set(ANATOMICAL_DISPLAY_ORDER)
            | severed_locs
        )

        for left_loc in sources:
            if not left_loc.startswith("left_"):
                continue
            right_loc = "right_" + left_loc[len("left_"):]
            if right_loc in skip_set:
                continue
            # Asymmetric clothing breaks the visual pairing.
            if left_loc in coverage_map or right_loc in coverage_map:
                continue

            merged = self._merge_paired_location(
                looker, left_loc, right_loc, longdescs, severed_locs,
                destroyed_locs,
            )
            if merged is not None:
                collapse_map[left_loc] = merged
                skip_set.add(right_loc)

        return collapse_map, skip_set

    def _merge_paired_location(self, looker, left_loc, right_loc,
                               longdescs, severed_locs, destroyed_locs=None):
        """
        Build the merged description for one collapsible pair, or ``None``.

        Handles the two collapse cases: identical longdescs (rendered once at
        plural number, with each side's wounds appended on its own side) and
        both-sides-severed (a single plural stump line). Identical prose is
        rendered verbatim — number-flexible words the author wrapped in
        ``{braces}`` are re-rendered to plural; everything else is unchanged.

        Issue #350 / PR-B: case 1 is suppressed when either side carries
        a destroyed-stage organ.  Per-side rendering then handles the
        destruction wounds independently; PR-C adds a paired destruction
        collapse for the both-sides-destroyed-same-mechanism case.
        """
        destroyed_locs = destroyed_locs or set()
        left_desc = longdescs.get(left_loc)
        right_desc = longdescs.get(right_loc)

        # Case 1: identical, non-empty longdescs on both sides.
        if (left_desc and right_desc and left_desc == right_desc
                and left_loc not in destroyed_locs
                and right_loc not in destroyed_locs):
            processed = self._process_description_variables(
                left_desc, looker, force_third_person=True,
                apply_skintone=True, number="plural",
            )
            parts = [processed]
            # A wound simply sits on its own side without splitting the pair.
            try:
                from world.medical.wounds import get_standalone_wound_description
                for side in (left_loc, right_loc):
                    wound_desc = get_standalone_wound_description(
                        self, side, looker
                    )
                    if wound_desc:
                        parts.append(wound_desc)
            except ImportError:
                pass
            return " ".join(parts)

        # Case 2: both sides cleanly severed (neither carries a longdesc).
        if (not left_desc and not right_desc
                and left_loc in severed_locs and right_loc in severed_locs):
            try:
                from world.medical.wounds import get_paired_severed_description
                return get_paired_severed_description(
                    self, left_loc, right_loc, looker
                )
            except ImportError:
                return None

        return None

    def _get_severed_locations(self):
        """Return the set of body locations that are cleanly severed."""
        try:
            from world.medical.wounds import get_character_wounds
        except ImportError:
            return set()

        wounds_by_location = {}
        for wound in get_character_wounds(self):
            wounds_by_location.setdefault(wound['location'], []).append(wound)

        severed = set()
        for location, location_wounds in wounds_by_location.items():
            if all(w.get('stage') == 'severed' for w in location_wounds):
                severed.add(location)
        return severed

    def _build_destroyed_pair_collapse(self, looker, coverage_map,
                                       destroyed_locs):
        """Pre-compute wound-side pair collapse for both-sides-destroyed
        symmetric pairs (issue #350 / PR-C).

        For each pair-key in the species pair table whose left+right
        sides are both in ``destroyed_locs`` AND share an injury type,
        we render one ``DESTROYED_BY_PAIR``-overlay pair line at the
        left anchor and skip the right side in the main render loop.
        Pairs with asymmetric coverage are excluded — clothing breaks
        the visual pairing the same way it does for the longdesc
        collapse pass.

        Mismatched mechanisms (left eye cut, right eye shot) fail the
        common-injury-type check inside
        :func:`world.medical.wounds.get_paired_destroyed_description`
        and the per-side rendering takes over.

        Args:
            looker: Reserved for permission checks.
            coverage_map: ``location -> clothing_item`` mapping.
            destroyed_locs: Set of locations with destroyed wounds
                (pre-computed by :meth:`_get_destroyed_locations`).

        Returns:
            ``(anchor_map, skip_set)`` — left anchors to pair-line
            strings and right partners to skip.
        """
        anchor = {}
        skip = set()
        try:
            from world.anatomy.species import get_species_pair_keys
            from world.medical.wounds import get_paired_destroyed_description
        except ImportError:
            return anchor, skip

        species = getattr(self.db, "species", None)
        for pair_key, (left_loc, right_loc) in get_species_pair_keys(species).items():
            if left_loc not in destroyed_locs:
                continue
            if right_loc not in destroyed_locs:
                continue
            # Asymmetric clothing breaks the visual pairing — same rule
            # as the longdesc-collapse pass.
            if left_loc in coverage_map or right_loc in coverage_map:
                continue
            rendered = get_paired_destroyed_description(
                self, pair_key, left_loc, right_loc, looker=looker,
            )
            if rendered:
                anchor[left_loc] = rendered
                skip.add(right_loc)
        return anchor, skip

    def _get_destroyed_locations(self):
        """Return the set of display locations with destroyed-stage wounds.

        Issue #350 / PR-B: powers the longdesc-suppression rule — at any
        location reported here the authored ``self.longdesc[location]``
        is skipped so the destruction wound is the sole description.
        Coverage interaction is inherited from
        :func:`world.medical.wounds.get_character_wounds`, which already
        filters by clothing visibility — destroyed organs hidden under
        armor remain undeclared and the authored prose stays as a
        fallback.
        """
        try:
            from world.medical.wounds import (
                get_character_wounds,
                get_destroyed_display_locations,
            )
        except ImportError:
            return set()
        return get_destroyed_display_locations(get_character_wounds(self))

    def _format_longdescs_with_paragraphs(self, longdesc_list):
        """
        Formats longdesc descriptions with smart paragraph breaks.

        Args:
            longdesc_list: List of (location, description) tuples.

        Returns:
            str: Formatted description with paragraph breaks.
        """
        from world.combat.constants import (
            PARAGRAPH_BREAK_THRESHOLD,
            REGION_BREAK_PRIORITY,
        )

        if not longdesc_list:
            return ""

        paragraphs = []
        current_paragraph = []
        current_char_count = 0
        current_region = None

        for location, description in longdesc_list:
            # Determine which anatomical region this location belongs to
            location_region = self._get_anatomical_region(location)

            # Check if we should break for a new paragraph
            should_break = False

            if (REGION_BREAK_PRIORITY and current_region and
                    location_region != current_region):
                # Region changed - check if we should break
                if current_char_count >= PARAGRAPH_BREAK_THRESHOLD * 0.7:
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
            location: Body location string.

        Returns:
            str: Region name or 'extended' for non-standard anatomy.
        """
        # Issue #356 follow-up: species-aware region grouping.  Rats
        # have foreleg/hindleg/tail regions, not arm/leg.
        from world.anatomy import get_species_anatomical_regions

        species = getattr(getattr(self, "db", None), "species", None)
        for region_name, locations in get_species_anatomical_regions(species).items():
            if location in locations:
                return region_name
        return "extended"

    def has_location(self, location):
        """
        Checks if this character has a specific body location.

        Args:
            location: Body location to check.

        Returns:
            bool: True if character has this location.
        """
        longdescs = self.longdesc or {}
        return location in longdescs

    def get_available_locations(self):
        """
        Gets list of all body locations this character has.

        Returns:
            list: List of available body location names.
        """
        longdescs = self.longdesc or {}
        return list(longdescs.keys())

    def set_longdesc(self, location, description):
        """
        Sets a longdesc for a specific location.

        Args:
            location: Body location.
            description: Description text (None to clear).

        Returns:
            bool: True if successful, False if location invalid.
        """
        if not self.has_location(location):
            return False

        longdescs = self.longdesc or {}
        longdescs[location] = description
        self.longdesc = longdescs
        return True

    def get_longdesc(self, location):
        """
        Gets longdesc for a specific location.

        Args:
            location: Body location.

        Returns:
            str or None: Description text or None if unset/invalid.
        """
        if not self.has_location(location):
            return None

        longdescs = self.longdesc or {}
        return longdescs.get(location)

    def return_appearance(self, looker, **kwargs):
        """
        Called when someone looks at this character.

        Returns a clean character appearance with name, description,
        longdesc+clothing, and wielded items.

        Args:
            looker: Character doing the looking.
            **kwargs: Additional parameters.

        Returns:
            str: Complete character appearance in clean format.
        """
        # Build appearance components
        parts = []

        # 1. Character name (header) + main description (no blank line between)
        name_and_desc = [self.get_look_header(looker)]
        if self.db.desc:
            # Initial description should NOT have skintone applied.
            # Braced verbs in the body paragraph (``{hold}``, ``{carry}``,
            # ...) take the pronoun as their subject, so verb flex must
            # follow the pronoun's *number*: singular for he / she, plural
            # for singular-they.  Without this, neutral sleeves render
            # "They holds themselves" instead of "They hold themselves"
            # (issue #321).
            body_number = (
                "singular"
                if (self.gender or "").lower() in ("male", "female")
                else "plural"
            )
            processed_desc = self._process_description_variables(
                self.db.desc, looker,
                force_third_person=True, apply_skintone=False,
                number=body_number,
            )
            name_and_desc.append(processed_desc)

        parts.append('\n'.join(name_and_desc))

        # 2. Longdesc + clothing integration (uses automatic paragraph parsing)
        if self.longdesc is None:
            # Issue #356 follow-up: species-aware default longdesc set.
            # Character.at_object_creation normally seeds this already;
            # this branch is a defensive fallback for objects somehow
            # missing the initial seed.
            try:
                from world.anatomy import get_species_default_longdesc_locations
                self.longdesc = get_species_default_longdesc_locations(
                    getattr(self.db, "species", None)
                )
            except ImportError:
                pass

        visible_body_descriptions = self._get_visible_body_descriptions(looker)
        if visible_body_descriptions:
            formatted_body_descriptions = self._format_longdescs_with_paragraphs(
                visible_body_descriptions
            )
            parts.append(formatted_body_descriptions)

        # 3. Wielded items section (using hands system).
        # Reads the derived ``hands`` property (species-aware grasping
        # slots backed by ``held_items``) — NOT the legacy ``hands``
        # attribute, which the Mr. Hands migration deletes after
        # moving data to ``held_items``.  Reading the legacy slot
        # here made this section permanently render "holding
        # nothing" (issue #460).
        hands = self.hands or {}
        # Integrated cyberware (#516) is excluded from the held list:
        # a deployed arm-gun is part of the body, represented in the
        # longdesc and dominating the sdesc — not "held".
        wielded_items = [
            item for item in hands.values()
            if item is not None and not getattr(item.db, "integrated", False)
        ]
        # Whether a deployed cyber weapon (integrated in a slot OR an
        # active natural weapon like claws) is present — used to
        # suppress the misleading "holding nothing" line, since the
        # sdesc shows them armed.
        has_deployed_chrome = any(
            getattr(item.db, "integrated", False) for item in hands.values()
            if item is not None
        )
        if not has_deployed_chrome:
            try:
                from world.medical.augments import get_active_natural_weapon
                has_deployed_chrome = get_active_natural_weapon(self) is not None
            except Exception:
                pass

        if wielded_items:
            wielded_names = [obj.get_display_name(looker) for obj in wielded_items]
            if len(wielded_names) == 1:
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding a "
                    f"{wielded_names[0]}."
                )
            elif len(wielded_names) == 2:
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding a "
                    f"{wielded_names[0]} and a {wielded_names[1]}."
                )
            else:
                # Multiple items: "a item1, a item2, and a item3"
                wielded_with_articles = [f"a {name}" for name in wielded_names]
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding "
                    f"{', '.join(wielded_with_articles[:-1])}, and "
                    f"{wielded_with_articles[-1]}."
                )
            parts.append(wielded_text)
        elif not has_deployed_chrome:
            # Show explicitly when hands are empty — but not when a
            # deployed cyber weapon fills them (the sdesc already
            # shows them armed; "holding nothing" would contradict).
            parts.append(f"{self.get_display_name(looker)} is holding nothing.")

        # 4. Staff-only comprehensive inventory (with explicit admin messaging)
        if looker.check_permstring("Builder"):
            all_contents = [obj for obj in self.contents if obj.location == self]
            if all_contents:
                content_names = [
                    f"{obj.get_display_name(looker)} [{obj.dbref}]"
                    for obj in all_contents
                ]
                parts.append(
                    f"|wWith your administrative visibility, you see:|n "
                    f"{', '.join(content_names)}"
                )

        # Join all parts with appropriate spacing (blank lines between sections)
        return '\n\n'.join(parts)

    def _location_is_inorganic(self, location):
        """True when ``location`` is cybernetic chrome (#516 review).

        Reads the medical organs at the container: any organ flagged
        ``inorganic`` makes the whole location render as metal rather
        than flesh (no skintone; gunmetal wrap).  Matches by container
        or display_location so surface keys line up with bulk organs.
        """
        state = getattr(self, "medical_state", None)
        organs = getattr(state, "organs", None) if state else None
        if not organs:
            return False
        for organ in organs.values():
            if location not in (
                getattr(organ, "container", None),
                getattr(organ, "display_location", None),
            ):
                continue
            data = getattr(organ, "data", None)
            if data and data.get("inorganic"):
                return True
        return False

    def _deployed_module_longdesc(self, location):
        """Prose for any deployed ability module at ``location``
        (#516 review item 4): the chrome arm's baseline longdesc
        expands when a weapon is out.  Returns the joined
        ``deployed_longdesc`` strings, or ``""``.
        """
        state = getattr(self, "medical_state", None)
        organs = getattr(state, "organs", None) if state else None
        if not organs:
            return ""
        out = []
        for organ in organs.values():
            if getattr(organ, "container", None) != location:
                continue
            data = getattr(organ, "data", None) or {}
            abilities = data.get("abilities") or {}
            store = getattr(organ, "ability_state", None) or {}
            for name, spec in abilities.items():
                if not (store.get(name) or {}).get("deployed"):
                    continue
                prose = spec.get("deployed_longdesc")
                if prose:
                    out.append(prose)
        return " ".join(out)

    def _deployed_slot_prose(self, location):
        """Replacement prose for a hand whose slot a deployed weapon
        has consumed (#516 review follow-up): when /shotgun fills the
        hand, the hand isn't a hand anymore — its longdesc is
        REPLACED by the ability's ``deployed_longdesc_slot``, not just
        appended to.  An ability's ``slot`` (resolved to a real
        container at install) names which location it consumes.
        Returns the prose, or ``""`` when nothing is deployed here.
        """
        state = getattr(self, "medical_state", None)
        organs = getattr(state, "organs", None) if state else None
        if not organs:
            return ""
        for organ in organs.values():
            data = getattr(organ, "data", None) or {}
            abilities = data.get("abilities") or {}
            store = getattr(organ, "ability_state", None) or {}
            for name, spec in abilities.items():
                if spec.get("slot") != location:
                    continue
                if not (store.get(name) or {}).get("deployed"):
                    continue
                prose = spec.get("deployed_longdesc_slot")
                if prose:
                    return prose
        return ""

    def _render_body_longdesc(self, location, text, looker):
        """Process one location's longdesc: flesh gets tokens +
        skintone; chrome (#516 review) gets gunmetal + any deployed-
        module expansion instead.  Wounds append either way."""
        is_chrome = self._location_is_inorganic(location)
        # A hand whose slot a deployed weapon has taken renders the
        # weapon's slot prose INSTEAD of its baseline hand text — the
        # hand has folded away.
        slot_override = self._deployed_slot_prose(location) if is_chrome else ""
        base_text = slot_override or text
        processed = self._process_description_variables(
            base_text, looker,
            force_third_person=True, apply_skintone=not is_chrome,
            side=self._side_from_location(location),
        )
        if is_chrome:
            from world.combat.constants import CHROME_DEFAULT_COLOR
            deployed = self._deployed_module_longdesc(location)
            body = f"{processed} {deployed}" if deployed else processed
            processed = f"{CHROME_DEFAULT_COLOR}{body}|n"
        try:
            from world.medical.wounds import append_wounds_to_longdesc
            processed = append_wounds_to_longdesc(
                processed, self, location, looker
            )
        except ImportError:
            pass
        return processed

    @staticmethod
    def _side_from_location(location):
        """Return ``"left"``/``"right"``/``None`` for a body location.

        Pure helper used by the per-location render path to drive
        side-aware singular flex (issue #341). Extended anatomy keys
        without a left/right prefix return ``None`` and skip the side
        prefix entirely.
        """
        if not location:
            return None
        if location.startswith("left_"):
            return "left"
        if location.startswith("right_"):
            return "right"
        return None

    def _flex_noun_vocabulary(self):
        """Return the singular nouns a longdesc number-token flexes as a noun.

        Two sources, unioned: the symmetric pair nouns derived from the
        species's pair table (eye, ear, arm, hand, thigh, shin, foot for
        humans; a cyclops contributes nothing here, a spider contributes
        its own multi-eye vocabulary) plus the curated ``LONGDESC_FLEX_NOUNS``
        body-noun vocabulary (leg, shoulder, hip, ...). These are the only
        words a number-token treats as the body's part noun; any other
        braced single word is treated as a verb.

        Species-aware via ``self.db.species`` (issue #350 / PR-A); unknown
        / None species falls through to the human pair table.
        """
        # Issue #356 follow-up: species-aware non-pair flex vocabulary.
        # Pair-keyed singulars (eye / ear / paw / etc.) are derived
        # from the species's ``pair_keys`` and unioned with the
        # species's curated non-pair set (tail / snout / fur / ... for
        # rats; leg / shoulder / hip / ... for humans).
        from world.anatomy.species import (
            get_species_longdesc_flex_nouns,
            get_species_pair_keys,
        )

        species = getattr(self.db, "species", None) if hasattr(self, "db") else None
        nouns = get_species_longdesc_flex_nouns(species)
        for left_loc, _right_loc in get_species_pair_keys(species).values():
            # "left_eye" -> "eye", "left_foot" -> "foot"
            nouns.add(left_loc.split("_", 1)[1])
        return nouns

    def _substitute_longdesc_tokens(self, desc, variables, number, side=None):
        """Resolve brace tokens in a longdesc, one token at a time.

        Resolution order per ``{token}``:
          1. Pronoun / name token present in *variables*.
          2. Number-flexible body-part token: a noun if its singular is in
             the flex-noun vocabulary (optionally with a leading ``a``/``an``),
             else a single-word verb. Both are flexed to *number*.
          3. Anything else is left literal (the brace is preserved) and logged.

        Side-aware singular flex (issue #341): when a paired body noun
        (``arm``, ``hand``, ``eye``, ``ear``, ``thigh``, ``shin``, ``foot``)
        flexes to singular AND ``side`` is provided, the side is prefixed
        — ``{arms}`` becomes ``"right arm"`` instead of bare ``"arm"`` when
        rendered from the ``right_arm`` location. Plural flex is unaffected
        (both sides present → just ``"arms"``). Articles are re-agreed:
        ``{an arm}`` with ``side="right"`` becomes ``"a right arm"``.

        Args:
            desc (str): Raw longdesc prose.
            variables (dict): Pronoun/name token → replacement.
            number (str): "singular" or "plural" for body-part tokens.
            side (str | None): ``"left"`` / ``"right"`` / ``None``.
                When set with ``number="singular"`` and the token is a
                pair-keyed body noun, the side is prefixed onto the
                singular form.

        Returns:
            str: Prose with recognised tokens substituted.
        """
        import re
        from world.anatomy.species import get_species_pair_keys
        from world.grammar import (
            _match_leading_case,
            flex_noun,
            flex_verb,
            get_article,
            singularize_noun,
        )

        flex_nouns = self._flex_noun_vocabulary()
        # Singulars that come from the species's pair table (eye, ear,
        # arm, hand, thigh, shin, foot for humans; anything a non-human
        # species declares). Side prefix applies to these. Non-pair
        # flex nouns (leg, shoulder, hip, ...) keep bare form.
        species = getattr(self.db, "species", None) if hasattr(self, "db") else None
        pair_singulars = {
            left.split("_", 1)[1]  # "left_eye" -> "eye"
            for left, _right in get_species_pair_keys(species).values()
        }
        article_re = re.compile(r"^(?:a|an)\s+(.+)$", re.IGNORECASE)

        def _resolve(match):
            body = match.group(1)

            # 1. Pronoun / name tokens.
            if body in variables:
                return str(variables[body])

            # 2. Number-flexible body-part tokens.
            art_match = article_re.match(body)
            core = art_match.group(1) if art_match else body
            if " " not in core:
                core_base = singularize_noun(core).lower()
                if core_base in flex_nouns:
                    # Side-aware singular flex (#341): prefix the side
                    # for pair-keyed nouns when rendering a single side.
                    if (number == "singular" and side
                            and core_base in pair_singulars):
                        side_phrase = f"{side} {core_base}"
                        if art_match:
                            article = get_article(side_phrase)
                            rendered = f"{article} {side_phrase}"
                        else:
                            rendered = side_phrase
                        return _match_leading_case(rendered, body)
                    return flex_noun(body, number)
                if art_match is None:
                    # Single bareword that is not a flex noun → verb.
                    return flex_verb(body, number)

            # 3. Unrecognised token: leave it literal, but log it so authors
            #    can spot typos instead of silently shipping a broken token.
            print(
                "Longdesc token not recognised, left literal: "
                f"{{{body}}} (in: {desc[:80]!r})"
            )
            return match.group(0)

        return re.sub(r"\{([^{}]+)\}", _resolve, desc)

    def _process_description_variables(
        self, desc, looker, force_third_person=False, apply_skintone=False,
        number="singular", side=None,
    ):
        """
        Process template variables in descriptions for perspective-aware text.

        Uses simple brace tokens like {their}, {they}, {name} (like {color}).
        In addition to pronoun/name tokens, number-flexible body-part words may
        be wrapped in braces ({eye}, {an eye}, {accents}); these are rendered
        to match *number* — "plural" for a collapsed pair, "singular" for a
        single side or lone survivor. Tokens the resolver does not recognise
        are left literal (a stray brace no longer drops the whole substitution).

        Args:
            desc (str): Description text with potential template variables.
            looker (Character): Who is looking at this character.
            force_third_person (bool): If True, always use 3rd person pronouns.
            apply_skintone (bool): If True, apply skintone coloring
                (for longdescs only).
            number (str): "singular" or "plural"; the grammatical number that
                braced body-part tokens should render to.
            side (str | None): ``"left"`` / ``"right"`` / ``None``. When
                ``number="singular"`` and the location is a paired body
                location (left/right side of a PAIR_MERGE_KEYS pair) and
                only this side remains, ``side`` carries the side info
                so paired body nouns render as ``"right arm"`` instead
                of bare ``"arm"`` (issue #341).

        Returns:
            str: Description with variables substituted.
        """
        if not desc or not looker:
            return desc

        # Map of available template variables based on perspective
        is_self = (looker == self) and not force_third_person

        # Get pronoun information for this character
        gender_mapping = {
            'male': 'male',
            'female': 'female',
            'neutral': 'plural',
            'nonbinary': 'plural',
            'other': 'plural',
        }

        character_gender = gender_mapping.get(self.gender, 'plural')

        # Simple template variable mapping (like {color})
        variables = {
            # Most common - possessive pronouns (lowercase)
            'their': (
                'your' if is_self
                else self._get_pronoun('possessive', character_gender)
            ),
            # Subject and object pronouns (lowercase)
            'they': (
                'you' if is_self
                else self._get_pronoun('subject', character_gender)
            ),
            'them': (
                'you' if is_self
                else self._get_pronoun('object', character_gender)
            ),
            # Possessive absolute and reflexive (less common, lowercase)
            'theirs': (
                'yours' if is_self
                else self._get_pronoun('possessive_absolute', character_gender)
            ),
            'themselves': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            'themself': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            # Capitalized versions for sentence starts
            'Their': (
                'Your' if is_self
                else self._get_pronoun(
                    'possessive', character_gender
                ).capitalize()
            ),
            'They': (
                'You' if is_self
                else self._get_pronoun('subject', character_gender).capitalize()
            ),
            'Them': (
                'You' if is_self
                else self._get_pronoun('object', character_gender).capitalize()
            ),
            'Theirs': (
                'Yours' if is_self
                else self._get_pronoun(
                    'possessive_absolute', character_gender
                ).capitalize()
            ),
            'Themselves': (
                'Yourself' if is_self
                else self._get_pronoun(
                    'reflexive', character_gender
                ).capitalize()
            ),
            'Themself': (
                'Yourself' if is_self
                else self._get_pronoun(
                    'reflexive', character_gender
                ).capitalize()
            ),
            # Character names
            'name': 'you' if is_self else self.get_display_name(looker),
            "name's": (
                'your' if is_self
                else f"{self.get_display_name(looker)}'s"
            ),
            # Legacy support for existing verbose names (can be removed later)
            'observer_pronoun_possessive': (
                'your' if is_self
                else self._get_pronoun('possessive', character_gender)
            ),
            'observer_pronoun_subject': (
                'you' if is_self
                else self._get_pronoun('subject', character_gender)
            ),
            'observer_pronoun_object': (
                'you' if is_self
                else self._get_pronoun('object', character_gender)
            ),
            'observer_pronoun_possessive_absolute': (
                'yours' if is_self
                else self._get_pronoun('possessive_absolute', character_gender)
            ),
            'observer_pronoun_reflexive': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            'observer_character_name': (
                'you' if is_self
                else self.get_display_name(looker)
            ),
            'observer_character_name_possessive': (
                'your' if is_self
                else f"{self.get_display_name(looker)}'s"
            ),
        }

        # Substitute all brace tokens one at a time. Pronoun/name tokens
        # resolve from ``variables``; otherwise a token is a number-flexible
        # body-part word (noun if its singular is a known pair noun, verb
        # otherwise). Unresolvable tokens are left literal.
        processed_desc = self._substitute_longdesc_tokens(
            desc, variables, number, side=side
        )

        # Apply skintone coloring only if requested (for longdescs only)
        if apply_skintone:
            skintone = self.db.skintone
            if skintone:
                from world.combat.constants import SKINTONE_PALETTE
                color_code = SKINTONE_PALETTE.get(skintone)
                if color_code:
                    # Wrap the entire processed description in the skintone color
                    # Reset color at end to prevent bleeding
                    processed_desc = f"{color_code}{processed_desc}|n"

        return processed_desc

    def _get_pronoun(self, pronoun_type, gender):
        """
        Get specific pronoun based on gender and type.

        Args:
            pronoun_type (str): Type of pronoun
                (subject, object, possessive, etc.)
            gender (str): Gender identifier (male, female, plural).

        Returns:
            str: Appropriate pronoun.
        """
        pronouns = {
            'male': {
                'subject': 'he',
                'object': 'him',
                'possessive': 'his',
                'possessive_absolute': 'his',
                'reflexive': 'himself',
            },
            'female': {
                'subject': 'she',
                'object': 'her',
                'possessive': 'her',
                'possessive_absolute': 'hers',
                'reflexive': 'herself',
            },
            'plural': {  # Used for they/them, nonbinary, neutral, other
                'subject': 'they',
                'object': 'them',
                'possessive': 'their',
                'possessive_absolute': 'theirs',
                'reflexive': 'themselves',
            },
        }

        return pronouns.get(gender, pronouns['plural']).get(pronoun_type, 'they')
