"""
Medical Core Classes

Core classes for tracking organ health, medical conditions, and medical state
persistence. These form the foundation of the medical system.
"""

from .constants import (
    CONTRIBUTION_VALUES,
    CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD, BLOOD_LOSS_DEATH_THRESHOLD,
    PAIN_CONSCIOUSNESS_MODIFIER, PAIN_UNCONSCIOUS_THRESHOLD
)


class Organ:
    """
    Represents a single organ within a character's anatomy.
    
    Tracks current HP, max HP, and medical conditions affecting this organ.
    Integrates with the body capacity system to determine functional impact.
    """
    
    def __init__(self, organ_name, organ_data=None, species=None):
        """
        Initialize an organ instance.

        Args:
            organ_name (str): Name of the organ (key in the species'
                organ table).
            organ_data (dict, optional): Override organ data, used
                during ``from_dict`` deserialization and for tests that
                want to inject a bespoke spec.  When absent, the spec
                is looked up via
                :func:`world.anatomy.get_organ_spec(organ_name, species)`.
            species (str | None): Species identifier (issue #356
                Phase 1).  When ``None``, falls back to the human
                organ table — backwards-compatible with existing
                callers that don't yet pass a species.
        """
        self.name = organ_name
        if organ_data is not None:
            self.data = organ_data
        else:
            # Lazy import — world.anatomy imports world.medical at
            # module load via the species table import; avoid the
            # circle by deferring this lookup until __init__ time.
            from world.anatomy import get_organ_spec
            self.data = get_organ_spec(organ_name, species) or {}
        
        # Core properties
        self.max_hp = self.data.get("max_hp", 10)
        self._current_hp = self.max_hp  # Start at full health
        self.container = self.data.get("container", "unknown")
        # Display surface for wound rendering (issue #346).  Most organs
        # render their wounds at the bulk container ("heart" wounds → the
        # chest line) but sensory organs surface at a more specific
        # location ("left_eye" wounds → the left_eye line) so the
        # longdesc renderer can show destruction at the right anatomical
        # surface.  Falls back to ``container`` when the spec omits it.
        self.display_location = self.data.get("display_location") or self.container
        self.hit_weight = self.data.get("hit_weight", "common")
        
        # Functional properties
        self.vital = self.data.get("vital", False)
        self.capacity = self.data.get("capacity", None)
        self.capacities = self.data.get("capacities", [])
        self.contribution = self.data.get("contribution", "minor")
        
        # Medical conditions affecting this organ.  Kept for legacy
        # callers (``add_condition`` / ``remove_condition``) — the
        # canonical source of truth is ``MedicalState.conditions``
        # (body-wide list).  ``_has_disabling_conditions`` and
        # ``get_functionality_percentage`` scan the parent state via
        # ``self.medical_state`` rather than mirroring conditions
        # here.  See :meth:`_iter_relevant_conditions`.
        self.conditions = []

        # Back-reference to the owning ``MedicalState``, set by
        # ``MedicalState`` at organ-creation / restore time so the
        # organ can scan the body-wide condition list for entries
        # matching its location.  ``None`` until wired — methods
        # degrade gracefully when absent (e.g. organ instantiated
        # outside a MedicalState in a test stub).
        #
        # Scan-based design (over mirroring) is the cyberware-safe
        # answer: replacing this flesh organ with a cyberware
        # equivalent leaves any chest / abdomen / etc. infections
        # in place on the body without sync logic, since conditions
        # never lived on the organ.  See spec line 564 ("Prosthetic
        # Integration: New artificial limbs add new hit locations
        # with their own organ mappings").
        self.medical_state = None
        
        # Wound state tracking for longdesc integration
        self.wound_stage = None      # fresh, treated, healing, scarred
        self.injury_type = None      # bullet, cut, stab, blunt, generic
        self.wound_timestamp = None  # When the wound occurred (for future healing)

        # Stabilization flag (#307, PR-B).  Set True when wound_care
        # has been applied to a damaged organ at this location.  A
        # stabilized organ does not deteriorate further — bleeding
        # conditions at this organ's location stop draining blood,
        # severity can't escalate, wound stage doesn't progress
        # toward "old".  Healing is a separate channel (PR-C) driven
        # by the dressed item's ``wound_healing`` rating, stored in
        # ``dressing_rate`` below.
        #
        # Re-application of wound_care to a stabilized wound is a
        # no-op with a "they're already stable — get them to a
        # surgeon" hint to the caller.  The stable state persists
        # until the wound is surgically treated or the organ is
        # replaced.
        self.stabilized = False

        # Dressing rate (#307, PR-C).  ``wound_healing`` effectiveness
        # rating from the item that was applied at stabilization
        # time.  Read by the medical script's healing tick to
        # restore organ HP at a rate proportional to this value:
        #
        #     hp_per_tick = max(rating // DIVISOR, FLOOR)
        #
        # Stored as a number (not an item reference) — the item may
        # be uses-depleted and deleted before the wound fully heals,
        # but the rate persists.  Cleared on full heal or organ
        # replacement.
        self.dressing_rate = 0
        # Fractional HP progress toward the next whole point of
        # dressed healing (#501) — persisted with the organ.
        self.dressing_progress = 0.0

        # Tourniquet flag (#509).  Limb-only by application rules:
        # while True, bleeding at this organ's container is held
        # completely (no loss, no clotting) — but nothing heals and
        # removal without treatment resumes the bleed.  Cleared by
        # proper wound treatment at the location.  Ischemia cost
        # (tourniquets can't stay on forever) is the noted future
        # hook — the elapsed-time machinery makes it cheap to add.
        self.tourniqueted = False

        # Cyberware ability runtime state (AUGMENT_ABILITIES_SPEC §2,
        # #516): {ability_name: {"deployed": bool, "weapon_dbref": str}}.
        # The ability DECLARATION lives in self.data["abilities"]
        # (round-trips with the spec); this is the toggle state,
        # persisted like stabilized / tourniqueted.
        self.ability_state = {}
        
    @property
    def current_hp(self):
        return self._current_hp

    @current_hp.setter
    def current_hp(self, value):
        """Set organ HP, invalidating the parent state's caches.

        Every mutation path — combat damage, healing ticks, surgical
        procedures, admin commands, severance — assigns this
        attribute, so routing invalidation through the setter is what
        makes the cached death verdict (issue #462) safe: no caller
        discipline required.
        """
        self._current_hp = value
        state = getattr(self, "medical_state", None)
        if state is not None:
            state._invalidate_derived_state()

    def is_destroyed(self):
        """Returns True if organ HP is 0 or below."""
        return self.current_hp <= 0
        
    def is_functional(self):
        """Returns True if organ can perform its function."""
        return not self.is_destroyed() and not self._has_disabling_conditions()
        
    def _iter_relevant_conditions(self):
        """Yield conditions that apply to this organ (#307).

        Two sources, both included so modifiers compound:

        1. **Body / location-bound** — entries on
           ``self.medical_state.conditions``.  Filtered by
           ``condition.location``: ``None`` (body-wide) always
           matches; otherwise the location must equal this organ's
           ``container`` or ``display_location``.  These live on the
           body and stay with it when an organ is harvested or
           swapped — sepsis doesn't follow a transplanted heart.
        2. **Organ-bound** — entries on ``self.conditions``.  These
           live on the organ itself and travel with it through
           harvest / install pipelines — endocarditis goes with the
           heart, kidney stones go with the kidney.  No location
           filtering needed; if it's on this organ it applies.

        Degrades gracefully (no body-wide sweep) when
        ``self.medical_state`` is ``None`` — handles test stubs that
        instantiate Organ standalone without a parent state.  Organ-
        bound conditions still surface in that case since they live
        directly on ``self``.

        See ``specs/HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`` line 1396+
        for the per-condition treatment mapping that pairs with the
        condition subclasses; the three-tier model categorises which
        treatments target which conditions.
        """
        state = self.medical_state
        if state is not None:
            relevant_locs = (self.container, self.display_location)
            for condition in state.conditions:
                loc = getattr(condition, "location", None)
                if loc and loc not in relevant_locs:
                    continue
                yield condition
        # Organ-bound (#307) — always applies, no location filter.
        for condition in self.conditions:
            yield condition

    def _has_disabling_conditions(self):
        """Return True when any relevant condition is at a severity
        that fully disables this organ (#307).

        Consults ``disables_organ_at_severity()`` on each condition
        matching this organ's location.  Base
        :class:`world.medical.conditions.MedicalCondition` returns
        ``False`` by default; subclasses with a clear cutoff
        (e.g. critical infection) override.
        """
        for condition in self._iter_relevant_conditions():
            if condition.disables_organ_at_severity():
                return True
        return False

    def get_functionality_percentage(self):
        """Return the percentage of normal function this organ
        provides (#307).

        Multiplies HP-driven base function by the product of each
        relevant condition's ``get_organ_functionality_modifier()``
        — so an inflamed organ runs below capacity even when its HP
        is intact.  Body-wide conditions whose modifier defaults to
        ``1.0`` (pain, blood loss, consciousness suppression) leave
        the result untouched.

        Returns:
            float: ``0.0`` to ``1.0`` representing functional capacity.
        """
        if self.is_destroyed():
            return 0.0

        base_function = self.current_hp / self.max_hp

        modifier = 1.0
        for condition in self._iter_relevant_conditions():
            modifier *= condition.get_organ_functionality_modifier()

        return max(0.0, base_function * modifier)
        
    def take_damage(self, amount, injury_type="generic"):
        """
        Apply damage to this organ.
        
        Args:
            amount (int): Damage amount
            injury_type (str): Type of injury (for future expansion)
            
        Returns:
            bool: True if organ was destroyed by this damage
        """
        if amount <= 0:
            return False
            
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - amount)
        
        # Set wound state when damage is first applied
        if old_hp == self.max_hp:  # First damage to this organ
            self.injury_type = injury_type
            self.wound_stage = 'fresh'
            # TODO: Set wound_timestamp when time system is implemented
        elif not hasattr(self, 'injury_type') or self.injury_type == "generic":
            # Update injury type if this is more specific than previous
            self.injury_type = injury_type
        
        # Update wound stage based on organ state
        if self.current_hp <= 0:
            # All destroyed organs start as "destroyed" regardless of location
            self.wound_stage = 'destroyed'  # Immediate aftermath of destruction
        # Keep existing stage if organ was already damaged (don't reset to fresh)
        
        # Return True if this damage destroyed the organ
        return old_hp > 0 and self.current_hp <= 0
    
    def _is_limb_container(self, container):
        """
        Determine if a container represents a limb/appendage vs internal body cavity.
        
        Args:
            container (str): Body location container
            
        Returns:
            bool: True if container is a limb/appendage
        """
        # Internal body cavities - organs here get "destroyed"
        internal_containers = {
            'head', 'chest', 'abdomen', 'back', 'neck', 'groin', 'face'
        }
        
        # Limb/appendage containers - organs here get "severed"
        limb_containers = {
            'left_arm', 'right_arm', 'left_hand', 'right_hand',
            'left_thigh', 'right_thigh', 'left_shin', 'right_shin', 
            'left_foot', 'right_foot', 'tail', 'left_wing', 'right_wing'
        }
        
        # Check for tentacles or other numbered appendages
        if 'tentacle_' in container or '_leg_' in container or '_arm_' in container:
            return True
        
        return container in limb_containers
        
    def heal(self, amount):
        """
        Heal damage to this organ.
        
        Args:
            amount (int): Healing amount
            
        Returns:
            int: Actual amount healed
        """
        if amount <= 0:
            return 0
            
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        
        # Update wound stage if fully healed
        if self.current_hp == self.max_hp and hasattr(self, 'wound_stage'):
            self.wound_stage = None  # No wound if fully healed
            self.injury_type = None
            # PR-B: stabilization is wound-scoped; clears when the
            # wound is resolved.  Lets a future re-injury start with
            # a clean stabilization slate.
            self.stabilized = False
            # PR-C: dressing rate also clears on full heal — the
            # dressing has served its purpose and a future re-injury
            # starts undressed.
            self.dressing_rate = 0
        
        return self.current_hp - old_hp
        
    def apply_treatment(self, treatment_type="basic"):
        """
        Apply medical treatment to this organ's wound.
        Future-proofing method for medical treatment system.

        Args:
            treatment_type (str): Type of treatment applied

        Deferred design (#307 follow-up).  The current implementation
        only advances the wound stage; the spec describes a much
        richer treatment pipeline that's deferred to a deeper pass
        because exact mechanics need balance work first.  See
        ``specs/HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md``:

        * **G.R.I.M. skill roll** (line 1432-1478):
          ``medical_effectiveness = (intellect * 0.75) + (motorics * 0.25)``;
          d20 + skill vs difficulty threshold.
        * **Tri-modal outcomes** (line 1473): success /
          partial_success / failure with distinct effects.
        * **Tool appropriateness table** (line 1396-1419): each
          tool has per-condition effectiveness; mismatched tools
          either fail or have ``failure_consequences`` (e.g.
          ``"infection_risk_scar_tissue"``).
        * **Healing bonuses** belong here once the heal-rate
          plumbing exists (currently absent; gated on the Time
          System #301 for time-based healing ticks anyway).

        For the destroyed → severed branch (clean amputation), the
        deferred design space is wider still:

        * **Order of operations**: tourniquet placement before vs
          after the cut changes blood-loss outcome.
        * **Care quality**: clean surgical amputation vs field-cut
          drives pain reduction, infection arrest at the site, and
          long-term wound stage.
        * **Painkiller interaction**: prior / concurrent painkiller
          use modifies pain consequences (spec line 1092).
        * **``amputation_risk`` injury types** (spec line 925):
          frostbite explicitly triggers amputation as a treatment
          path, not just as a sever-from-damage path.

        Until that pass, this method only flips the stage so the
        wound rendering picks the correct decay tier.
        """
        if hasattr(self, 'wound_stage'):
            if self.wound_stage == 'fresh':
                self.wound_stage = 'treated'
            elif self.wound_stage == 'destroyed':
                # Medical treatment of destroyed organs results in clean amputation/severance
                self.wound_stage = 'severed'
    
    def advance_healing_stage(self):
        """
        Advance the wound to the next healing stage.
        Future-proofing method for time-based healing system.
        
        Note: Destroyed organs can be treated to "severed" (clean amputation/medical care).
        Severed organs are permanent and cannot heal further.
        """
        if not hasattr(self, 'wound_stage') or not self.wound_stage:
            return
            
        stage_progression = {
            'fresh': 'healing',
            'treated': 'healing', 
            'healing': 'scarred',
            'destroyed': 'destroyed',  # Stays destroyed until medical treatment
            'severed': 'severed',      # Permanent - clean amputation/medical care
            'scarred': 'scarred'       # Permanent marks
        }
        
        self.wound_stage = stage_progression.get(self.wound_stage, self.wound_stage)

        # Scarred stage only applies to organs that still have HP (non-destroyed)
        if self.wound_stage == 'scarred' and self.current_hp <= 0:
            # Destroyed organs can't become scars - they stay destroyed
            self.wound_stage = 'destroyed'

        # Scar policy (#307 follow-up): scars are **cosmetic only**.
        # Scarred-stage organs render the scarred wound prose via the
        # existing message modules (``world/medical/wounds/messages/<itype>.py``
        # ``"scarred"`` cell) and do NOT carry a functionality penalty.
        # This is intentionally distinct from two related but separate
        # mechanics the spec calls out as deferred design space:
        #
        # * **Permanent damage** (spec line 879, 923): some injury
        #   types (burn, frostbite) have ``permanent_damage_chance``.
        #   Permanent damage is FUNCTIONAL — likely modelled as
        #   reduced max_hp or a persistent functionality multiplier.
        #   Separate from scarring.
        # * **Improper healing** (spec line 1149): a failed splint
        #   has ``failure_consequences = "improper_healing_permanent_reduced_function"``.
        #   Also functional, triggered by failed treatment.
        #
        # Auto-progression from healing → scarred is gated on the
        # Time System (#301) for time-based ticks.
        
    def _invalidate_parent_state(self):
        """Invalidate the owning state's caches (organ-bound
        conditions feed functionality, hence capacities and the
        death verdict)."""
        state = getattr(self, "medical_state", None)
        if state is not None:
            state._invalidate_derived_state()

    def add_condition(self, condition):
        """Add a medical condition to this organ."""
        if condition not in self.conditions:
            self.conditions.append(condition)
            self._invalidate_parent_state()

    def remove_condition(self, condition):
        """Remove a medical condition from this organ."""
        if condition in self.conditions:
            self.conditions.remove(condition)
            self._invalidate_parent_state()
            
    def to_dict(self):
        """
        Serialize organ state for persistence.

        Returns:
            dict: Serialized organ state
        """
        return {
            "name": self.name,
            # The organ's spec dict (ANATOMY_AUGMENTS_SPEC §3.1).
            # Species-table organs could re-derive this at load, but
            # augment organs (cybernetic tail) have no table entry —
            # an organ that can't survive a save/load round trip is
            # a bug, so every organ carries its spec.
            "data": self.data,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            # Organ-bound conditions (#307 three-tier model: body /
            # location / organ).  Serialized via each condition's
            # ``to_dict`` so the data round-trips cleanly through
            # harvest / install / persistence layers rather than
            # pickling the in-memory objects.
            "conditions": [
                c.to_dict() for c in self.conditions
                if hasattr(c, "to_dict")
            ],
            "container": self.container,
            "display_location": self.display_location,
            "wound_stage": self.wound_stage,
            "injury_type": self.injury_type,
            "wound_timestamp": self.wound_timestamp,
            "stabilized": self.stabilized,
            "dressing_rate": self.dressing_rate,
            "dressing_progress": getattr(self, "dressing_progress", 0.0),
            "tourniqueted": getattr(self, "tourniqueted", False),
            "ability_state": getattr(self, "ability_state", {}) or {},
        }
        
    @classmethod
    def from_dict(cls, data):
        """
        Deserialize organ state from persistence.
        
        Args:
            data (dict): Serialized organ state
            
        Returns:
            Organ: Restored organ instance
        """
        # Snapshots carry the organ's spec dict (ANATOMY_AUGMENTS_SPEC
        # §3.1) so non-species organs (augments) restore container /
        # hit_weight / flags intact.  Legacy snapshots without it fall
        # back to the species-table lookup, exactly as before.
        organ = cls(data["name"], organ_data=data.get("data") or None)
        organ.current_hp = data.get("current_hp", organ.max_hp)
        organ.max_hp = data.get("max_hp", organ.max_hp)
        # Restore organ-bound conditions through the proper factory
        # (#307).  Each entry is either a serialized dict (post-#307)
        # or a legacy MedicalCondition instance pickled by Evennia's
        # attribute layer (pre-#307 snapshots).  Skip anything that
        # doesn't recognise as one of those shapes — preserves
        # forward-compat without choking on legacy data.
        organ.conditions = []
        from .conditions import MedicalCondition, deserialize_condition
        for entry in data.get("conditions", []):
            if isinstance(entry, dict):
                organ.conditions.append(deserialize_condition(entry))
            elif isinstance(entry, MedicalCondition):
                organ.conditions.append(entry)
        organ.wound_stage = data.get("wound_stage")
        organ.injury_type = data.get("injury_type")
        organ.wound_timestamp = data.get("wound_timestamp")
        # Stabilization (#307, PR-B).  Defaults to False so legacy
        # snapshots predating the field behave as untreated.
        organ.stabilized = bool(data.get("stabilized", False))
        # Dressing rate (#307, PR-C).  Defaults to 0 so legacy
        # snapshots predating the field behave as untreated /
        # not-healing.
        try:
            organ.dressing_rate = int(data.get("dressing_rate", 0) or 0)
            organ.dressing_progress = float(data.get("dressing_progress", 0.0) or 0.0)
            organ.tourniqueted = bool(data.get("tourniqueted", False))
        except (TypeError, ValueError):
            organ.dressing_rate = 0
        # Cyberware toggle state (#516) — plain-dict copy so the
        # restored organ never shares storage with the snapshot.
        raw_ability_state = data.get("ability_state") or {}
        organ.ability_state = {
            str(name): dict(entry) if hasattr(entry, "keys") else {}
            for name, entry in raw_ability_state.items()
        }
        # Issue #346: persisted organs may predate ``display_location`` —
        # the ``cls(data["name"])`` constructor already seeded it from
        # the ORGANS spec, so only override when the snapshot carries
        # a non-None value (preserves bespoke per-character routing if
        # we ever add it; covers the legacy-snapshot case automatically).
        snapshot_display = data.get("display_location")
        if snapshot_display:
            organ.display_location = snapshot_display
        return organ


class MedicalState:
    """
    Manages the complete medical state of a character.
    
    Coordinates between organs, conditions, vital signs, and body capacities.
    Handles persistence and provides high-level medical queries.
    """
    
    def __init__(self, character=None):
        """
        Initialize medical state.
        
        Args:
            character: Reference to the character this belongs to
        """
        self.character = character
        self.organs = {}
        self.conditions = []
        
        # Cached death verdict (issue #462).  ``None`` = stale,
        # recomputed lazily by :meth:`is_dead`.  Invalidated by the
        # ``blood_level`` / ``Organ.current_hp`` setters and by
        # condition add/remove — every input that can flip the
        # verdict.  Defined before the vital-sign assignments below
        # so the ``blood_level`` property setter can touch it.
        self._cached_is_dead = None

        # Vital signs
        self.blood_level = 100.0  # Percentage of normal blood volume
        self.pain_level = 0.0     # Current pain accumulation
        self.consciousness = 1.0  # Current consciousness level (0.0 to 1.0)

        # Cache for expensive calculations
        self._capacity_cache = {}
        self._cache_dirty = True
        
        # Initialize default human organs
        self._initialize_default_organs()
        
    def _initialize_default_organs(self):
        """Initialize the species-appropriate organ set (issue #356 Phase 1).

        Reads the species from the owning character; ``None`` /
        unknown species falls back to the human organ table.  Each
        organ is constructed with the species so its spec lookup
        targets the right table — a rat's medical state doesn't
        accidentally get a left_humerus.  Sets the back-reference
        (#307) so the organ can scan ``self.conditions`` for
        location-matching entries during functionality checks.
        """
        from world.anatomy import get_species_organs

        species = None
        if self.character is not None:
            species = getattr(self.character.db, "species", None)
        for organ_name in get_species_organs(species).keys():
            organ = Organ(organ_name, species=species)
            organ.medical_state = self
            self.organs[organ_name] = organ
            
    @property
    def blood_level(self):
        return self._blood_level

    @blood_level.setter
    def blood_level(self, value):
        """Set blood level, invalidating the cached death verdict.

        Bleeding ticks, transfusions, and admin heals all assign this
        attribute directly — the setter keeps the death cache honest
        without requiring those callers to know about it.
        """
        self._blood_level = value
        self._cached_is_dead = None

    def _invalidate_derived_state(self):
        """Mark all derived caches stale after a medical mutation."""
        self._cached_is_dead = None
        self._cache_dirty = True

    def get_organ(self, organ_name):
        """Get organ by name, creating if it doesn't exist.

        Species-aware (issue #356 Phase 1) — lazily-created organs
        consult the owning character's species so the spec lookup
        targets the right table.  Sets the parent back-reference
        (#307) on newly-created organs.
        """
        if organ_name not in self.organs:
            species = None
            if self.character is not None:
                species = getattr(self.character.db, "species", None)
            organ = Organ(organ_name, species=species)
            organ.medical_state = self
            self.organs[organ_name] = organ
        return self.organs[organ_name]
        
    def location_severable_by_organ(self, location):
        """True when any organ at ``location`` flags
        ``severable_container`` in its spec (ANATOMY_AUGMENTS_SPEC
        §3.5).  The per-character severability overlay: augment
        anatomy (the cybernetic tail) declares its own severability
        instead of needing a species-table entry."""
        for organ in self.organs.values():
            if getattr(organ, "container", None) != location:
                continue
            data = getattr(organ, "data", None)
            if data and data.get("severable_container"):
                return True
        return False

    def get_conditions_by_location(self, location):
        """Get all conditions affecting a specific body location."""
        return [c for c in self.conditions if c.location == location]
        
    def calculate_total_pain(self):
        """Calculate total pain from all conditions."""
        total_pain = sum(condition.get_pain_contribution() for condition in self.conditions)
        return total_pain
        
    def calculate_blood_loss_rate(self):
        """Calculate total blood loss per round from all bleeding conditions."""
        total_loss = sum(condition.get_blood_loss_rate() for condition in self.conditions)
        return total_loss
        
    def calculate_body_capacity(self, capacity_name):
        """Return the organ-only floor for ``capacity_name``.

        This is the **schema layer's** answer to "how much of this
        capacity does the body have left?" — derived purely from
        organ health, weighted by each organ's declared contribution
        to that capacity (see ``world.medical.constants.BODY_CAPACITIES``
        and species overrides in ``world.anatomy.species``).

        Pain, blood loss, condition-driven suppression, and other
        runtime modifiers are NOT applied here.  Those flow through
        :meth:`update_vital_signs` (which writes
        ``self.consciousness`` / ``self.pain_level`` / ``self.blood_level``)
        and are read by :meth:`is_unconscious`.  Conflating the two
        would re-derive runtime state from organ HP every call,
        breaking the substrate-readiness contract that the audit's
        Phase 6 chronic-conditions framework is built on.

        Args:
            capacity_name (str): Name of capacity to calculate
                (``"blood_pumping"``, ``"breathing"``, ``"sight"``,
                ``"moving"``, etc.).

        Returns:
            float: 0.0 to 1.0 representing the organ-only capacity
            floor, clamped and cached until ``_cache_dirty`` flips.
        """
        if not self._cache_dirty and capacity_name in self._capacity_cache:
            return self._capacity_cache[capacity_name]

        # Issue #356 follow-up: species-aware capacity wiring.  A
        # rat's "moving" references hindleg/hindpaw bones, not human
        # femur/tibia/metatarsals; without this lookup a damaged rat
        # leg would never reduce moving capacity.
        from world.anatomy import get_species_body_capacities
        species = None
        if self.character is not None:
            species = getattr(self.character.db, "species", None)
        species_capacities = get_species_body_capacities(species)
        capacity_data = species_capacities.get(capacity_name, {})
        capacity_organs = capacity_data.get("organs", [])
        
        if not capacity_organs:
            return 1.0  # No organs defined = full capacity
            
        total_capacity = 0.0
        max_possible_capacity = 0.0
        
        for organ_name in capacity_organs:
            organ = self.get_organ(organ_name)
            organ_functionality = organ.get_functionality_percentage()
            
            # Get contribution level - check for organ-specific contributions first
            contribution_value = None
            
            # Check for organ-specific contributions (e.g., liver_contribution, stomach_contribution)
            organ_contribution_key = f"{organ_name}_contribution"
            if organ_contribution_key in capacity_data:
                contribution_value = capacity_data[organ_contribution_key]
            else:
                # Check for bone-specific contributions (e.g., femur_contribution, humerus_contribution)
                bone_type = organ_name.split('_')[-1]  # Get bone name (femur, humerus, etc.)
                if bone_type in ['femur', 'tibia', 'humerus']:
                    bone_contribution_key = f"{bone_type}_contribution"
                elif 'metacarpals' in organ_name:
                    bone_contribution_key = "metacarpal_contribution"
                elif 'metatarsals' in organ_name:
                    bone_contribution_key = "metatarsal_contribution"
                else:
                    bone_contribution_key = None
                    
                if bone_contribution_key and bone_contribution_key in capacity_data:
                    contribution_value = capacity_data[bone_contribution_key]
                else:
                    # Fall back to organ's defined contribution or generic lookup
                    contribution_key = organ.data.get(f"{capacity_name}_contribution", organ.contribution)
                    if isinstance(contribution_key, str):
                        contribution_value = CONTRIBUTION_VALUES.get(contribution_key, 0.05)
                    else:
                        contribution_value = float(contribution_key)
                
            # Add to totals
            total_capacity += organ_functionality * contribution_value
            max_possible_capacity += contribution_value
            
        # Normalize to 0.0-1.0 range based on maximum possible capacity
        if max_possible_capacity > 0:
            capacity_level = total_capacity / max_possible_capacity
        else:
            capacity_level = 1.0
            
        # Clamp to valid range
        capacity_level = max(0.0, min(1.0, capacity_level))
        
        # Cache the result
        self._capacity_cache[capacity_name] = capacity_level
        return capacity_level
        
    def is_unconscious(self):
        """Return True when the character is currently unconscious.

        Reads the **runtime ``self.consciousness`` value** — *not* the
        raw consciousness capacity floor from
        :meth:`calculate_body_capacity`.  The runtime value already
        bakes in pain penalty, blood-loss penalty, and
        condition-driven consciousness suppression (see
        :meth:`update_vital_signs` for how those modifiers stack).

        Brain damage feeds in indirectly: a destroyed brain drops
        the ``consciousness`` capacity floor to zero, which
        ``update_vital_signs`` writes into ``self.consciousness``
        on each tick, which trips the threshold here.  This is the
        canonical "brain destruction is unconsciousness, not death"
        path documented in the HEALTH spec.
        """
        return self.consciousness < (CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD / 100.0)

    def is_dead(self):
        """Return the (cached) death verdict.

        The full computation walks four body capacities (organ +
        condition sweeps), and ``Character.msg`` consults this on
        every message — so the verdict is cached and recomputed only
        after a mutation invalidates it (issue #462).  Invalidation
        rides the ``Organ.current_hp`` / ``blood_level`` setters and
        condition add/remove, covering every input of
        :meth:`_compute_is_dead`.
        """
        if self._cached_is_dead is None:
            self._cached_is_dead = self._compute_is_dead()
        return self._cached_is_dead

    def _compute_is_dead(self):
        """Return True when the character has crossed a death threshold.

        Enforces exactly two death conditions, both organ-only and
        capacity-derived:

        1. **Lethal capacity floor** — any of ``blood_pumping`` /
           ``breathing`` / ``digestion`` / ``neck_integrity`` hits
           zero.  These are the four entries in
           ``LETHAL_CAPACITY_NAMES`` that drive vital-location
           targeting bias *and* enforce death (the fifth entry,
           ``consciousness``, is intentionally NOT a death gate —
           see :meth:`is_unconscious`).
        2. **Blood-loss floor** — total blood level falls below
           ``BLOOD_LOSS_DEATH_THRESHOLD``.

        Notes for the audit's substrate work:

        * Brain destruction lands as unconsciousness here (not
          death).  Eventual revival blocking lives in
          :meth:`death_progression.DeathProgressionScript._check_medical_revival_conditions`
          per the audit's Phase 2.
        * Kidney loss is **declared fatal** in the schema
          (``blood_filtration.total_loss_fatal``) but not enforced
          here — the runtime treats it as a survivable injury until
          the audit's Phase 6 chronic-conditions substrate ships a
          ``RenalFailure`` condition that produces death via the
          condition tick path.
        """
        # Death from vital organ failure
        if self.calculate_body_capacity("blood_pumping") <= 0.0:
            return True
        if self.calculate_body_capacity("breathing") <= 0.0:
            return True
        if self.calculate_body_capacity("digestion") <= 0.0:
            return True  # Liver failure
        if self.calculate_body_capacity("neck_integrity") <= 0.0:
            return True  # Decapitation - cervical spine severed (#243)

        # Death from blood loss
        if self.blood_level <= (100.0 - BLOOD_LOSS_DEATH_THRESHOLD):
            return True

        return False
        
    def update_vital_signs(self):
        """Update vital signs based on current conditions and organ state."""
        # Update pain level
        self.pain_level = self.calculate_total_pain()
        
        # Update blood loss
        blood_loss_rate = self.calculate_blood_loss_rate()
        if blood_loss_rate > 0:
            self.blood_level = max(0.0, self.blood_level - blood_loss_rate)
            
        # Update consciousness based on multiple factors
        base_consciousness = self.calculate_body_capacity("consciousness")
        
        # Pain penalty
        pain_penalty = 0.0
        if self.pain_level > PAIN_UNCONSCIOUS_THRESHOLD:
            pain_penalty = (self.pain_level - PAIN_UNCONSCIOUS_THRESHOLD) * PAIN_CONSCIOUSNESS_MODIFIER
            
        # Blood loss penalty
        blood_penalty = max(0.0, (100.0 - self.blood_level) / 100.0)
        
        # Consciousness suppression penalty from medical conditions
        consciousness_suppression_penalty = 0.0
        for condition in self.conditions:
            if hasattr(condition, 'get_consciousness_penalty'):
                consciousness_suppression_penalty += condition.get_consciousness_penalty()
        
        self.consciousness = max(0.0, base_consciousness - pain_penalty - blood_penalty - consciousness_suppression_penalty)
        
        # Mark cache as dirty after vital sign updates
        self._cache_dirty = True
        
    def take_organ_damage(self, organ_name, damage_amount, injury_type="generic"):
        """
        Apply damage to a specific organ and create appropriate medical conditions.
        
        Args:
            organ_name (str): Name of organ to damage
            damage_amount (int): Amount of damage
            injury_type (str): Type of injury
            
        Returns:
            bool: True if organ was destroyed
        """
        organ = self.get_organ(organ_name)
        was_destroyed = organ.take_damage(damage_amount, injury_type)

        # Create medical conditions based on damage type and amount (Phase 2.6)
        if damage_amount > 0:
            new_conditions = self._create_conditions_from_damage(
                damage_amount, injury_type, organ.container
            )

            # Inorganic organs (#516 follow-up, user decision
            # 2026-06-13): chrome doesn't bleed and doesn't go
            # septic — a shot-up gun arm loses function, not blood.
            # Pain stays: neural feedback from the damaged graft.
            if organ.data.get("inorganic"):
                new_conditions = [
                    c for c in new_conditions
                    if getattr(c, "condition_type", "") == "pain"
                ]

            # Add and start new conditions
            for condition in new_conditions:
                self.add_condition(condition)
        
        self._cache_dirty = True
        return was_destroyed
        
    def _create_conditions_from_damage(self, damage_amount, injury_type, location):
        """
        Create appropriate medical conditions based on damage dealt.
        
        Args:
            damage_amount (int): Amount of damage
            injury_type (str): Type of injury
            location (str): Body location affected
            
        Returns:
            list: List of medical conditions to add
        """
        try:
            from .conditions import create_condition_from_damage
            conditions = create_condition_from_damage(damage_amount, injury_type, location)
            return conditions
        except ImportError:
            # Fallback if conditions module not available
            return []
        except Exception as e:
            # Deliberate guard (#469): a condition-creation bug must not
            # abort damage application — but a wound silently producing
            # no bleeding/pain is the cheating class of failure, so it
            # is audit-logged.
            from world.combat.debug import get_splattercast
            get_splattercast().msg(
                f"CONDITION_CREATE_ERROR: {injury_type} at {location}: {e}"
            )
            return []
            
    def add_condition(self, condition):
        """
        Add a medical condition and start its ticker if needed.
        
        Args:
            condition: MedicalCondition instance
        """
        # Don't add conditions if character is archived (permanently dead)
        # Dying characters can still be resuscitated, so they should keep conditions
        character = self._get_character_reference()
        if character and character.db.archived:
            from world.combat.debug import get_splattercast
            splattercast = get_splattercast()
            char_name = character.key if character else "unknown"
            splattercast.msg(f"ADD_CONDITION: {char_name} is archived, not adding {condition.condition_type}")
            return
            
        if condition not in self.conditions:
            self.conditions.append(condition)
            # Conditions can disable organs outright (capacity → 0),
            # so they're a death-verdict input.
            self._invalidate_derived_state()

            from world.combat.debug import get_splattercast
            splattercast = get_splattercast()
            splattercast.msg(f"ADD_CONDITION: Added {condition.condition_type} severity {condition.severity}")
            
            # Start ticker if condition requires it
            if hasattr(condition, 'requires_ticker') and condition.requires_ticker:
                # Get character reference - this is a bit tricky since MedicalState
                # doesn't directly hold character reference
                character = self._get_character_reference()
                if character:
                    from world.combat.debug import get_splattercast
                    splattercast = get_splattercast()
                    splattercast.msg(f"ADD_CONDITION: Starting ticker for {condition.condition_type} on {character.key}")
                    condition.start_condition(character)
                else:
                    from world.combat.debug import get_splattercast
                    splattercast = get_splattercast()
                    splattercast.msg(f"ADD_CONDITION: No character reference found for {condition.condition_type}")
            
            # Save medical state after adding condition to ensure persistence
            if self.character:
                self.character.save_medical_state()
                    
    def remove_condition(self, condition):
        """
        Remove a medical condition and stop its ticker.
        
        Args:
            condition: MedicalCondition instance to remove
        """
        if condition in self.conditions:
            self.conditions.remove(condition)
            self._invalidate_derived_state()

            # Stop ticker if condition had one
            if hasattr(condition, 'stop_condition'):
                condition.stop_condition()
                
    def get_conditions_by_type(self, condition_type):
        """
        Get all conditions of a specific type.
        
        Args:
            condition_type (str): Type of condition to search for
            
        Returns:
            list: Conditions matching the type
        """
        return [c for c in self.conditions if c.condition_type == condition_type]
        
    def get_condition_summary(self):
        """
        Get a summary of all active medical conditions.
        
        Returns:
            dict: Summary of conditions by type with counts and severity
        """
        summary = {}
        for condition in self.conditions:
            ctype = condition.condition_type
            if ctype not in summary:
                summary[ctype] = {'count': 0, 'severity': 0, 'locations': []}
            
            summary[ctype]['count'] += 1
            summary[ctype]['severity'] += getattr(condition, 'severity', 1)
            if hasattr(condition, 'location'):
                summary[ctype]['locations'].append(condition.location)
                
        return summary
                    
    def _get_character_reference(self):
        """
        Get reference to character that owns this medical state.
        """
        return self.character
        
    def to_dict(self):
        """Serialize medical state for persistence."""
        return {
            "organs": {name: organ.to_dict() for name, organ in self.organs.items()},
            "conditions": [condition.to_dict() for condition in self.conditions],
            "blood_level": self.blood_level,
            "pain_level": self.pain_level,
            "consciousness": self.consciousness
        }
        
    @classmethod 
    def from_dict(cls, data, character=None):
        """Deserialize medical state from persistence."""
        medical_state = cls(character)
        
        # Restore organs.  Wire the back-reference (#307) so restored
        # organs can scan ``medical_state.conditions`` for relevant
        # entries — needed for ``get_functionality_percentage`` /
        # ``_has_disabling_conditions`` to fire correctly on
        # post-restore organs.
        organ_data = data.get("organs", {})
        for organ_name, organ_dict in organ_data.items():
            organ = Organ.from_dict(organ_dict)
            organ.medical_state = medical_state
            medical_state.organs[organ_name] = organ
            
        # Restore conditions via the shared factory (#307) so harvest /
        # install / persistence layers all reconstruct conditions the
        # same way.
        from .conditions import deserialize_condition
        for condition_dict in data.get("conditions", []):
            try:
                condition = deserialize_condition(condition_dict)
                medical_state.conditions.append(condition)
                # Re-start condition ticker if character is available and not archived
                # Archived characters are permanently dead; dying characters can still be resuscitated
                if character and not character.db.archived:
                    condition.start_condition(character)
            except Exception as e:
                # Deliberate guard (#469): one corrupt persisted
                # condition skips, the rest restore.  Audit-logged so
                # vanishing conditions are diagnosable.
                from world.combat.debug import get_splattercast
                get_splattercast().msg(
                    f"CONDITION_RESTORE_ERROR: skipped condition for "
                    f"{getattr(character, 'key', '?')}: {e}"
                )
            
        # Restore vital signs
        medical_state.blood_level = data.get("blood_level", 100.0)
        medical_state.pain_level = data.get("pain_level", 0.0)
        
        # Handle consciousness migration: old data stored as percentage (100.0), new as decimal (1.0)
        consciousness_value = data.get("consciousness", 1.0)
        if consciousness_value > 1.0:
            # Old percentage format, convert to decimal
            medical_state.consciousness = consciousness_value / 100.0
        else:
            # New decimal format
            medical_state.consciousness = consciousness_value
        
        return medical_state
