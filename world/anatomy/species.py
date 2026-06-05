"""Species anatomy overlay (PR #202 / PR-G).

A minimal data + helpers layer that names body parts, corpses, and
locations by species and decay stage.  Designed as a *minimal overlay*
rather than a full anatomical refactor: humans are the assumed default,
and the only species shipped at the time of writing; non-humans will
register here when they exist, and severed items / organs / corpses
will pick up the new vocabulary automatically because every rendering
path consults these helpers.

Design notes
============

* **Decay-tier vocabulary** (per the PR-G design discussion):

    +-----------+----------------------------------------+
    | Stage     | Display                                |
    +===========+========================================+
    | fresh     | ``{species} {part}`` / ``{species} corpse`` |
    | early     | ``{species} {part}`` / ``{species} corpse`` |
    | moderate  | ``rotting {part}`` / ``rotting corpse`` |
    | advanced  | ``rotting {part}`` / ``rotting corpse`` |
    | skeletal  | ``skeletal {part}`` / ``skeletal remains`` |
    +-----------+----------------------------------------+

  Fresh/early stages reveal species cleanly; moderate/advanced
  obfuscate ("rotting" alone, no species clue); skeletal abandons
  species for the universal "skeletal" tag.  Players who want more
  precision than these glance-level tags must ``look`` for the full
  description (which still carries decay prose) or ``autopsy`` (which
  rolls Intellect for forensic recovery).

  Harvested **organs** follow the same shape via
  :data:`decay_organ_prefixes`, but the skeletal-tier tag is
  ``desiccated`` rather than ``skeletal`` — a heart or kidney doesn't
  skeletonize, it dries out.  See :func:`get_species_organ_name`.

* **No species in skeletal/rotting stages**: deliberate gameplay
  signal — late decay obscures species at a glance.  Once a body has
  rotted past recognition or reduced to bone, the casual observer
  can't tell a human from a synth without close examination.

* **Per-character override hook**: characters (or any object with a
  ``db.species`` attribute) consult this registry through their
  species key.  Unknown species fall back to the ``human`` definition
  rather than crashing — this keeps the system robust as new species
  are added incrementally.

* **No state stored on the helpers**: every call is a pure lookup
  against :data:`SPECIES_DEFINITIONS`.  This lets rendering code call
  the helpers on every ``get_display_name`` / ``return_appearance``
  invocation without performance concerns and lets decay drift propagate
  naturally as time passes (the source data — ``get_decay_stage()`` —
  is what changes, not the registry).
"""

from __future__ import annotations

#: Species registry.  Keys are stable species identifiers (lowercase,
#: underscore-separated for multi-word species like ``"glitch_synth"``);
#: values are dicts whose schema is documented inline below.
SPECIES_DEFINITIONS = {
    "human": {
        # Glance-level species tag, used in fresh/early-stage display
        # ("a human corpse", "a human left arm").  Omitted from moderate/
        # advanced/skeletal stages by the decay-prefix template.
        "display_name": "human",

        # Per-location display strings.  Keys are canonical body-
        # location identifiers (matching ``container`` values in
        # ``world.medical.constants.ORGANS`` and the ``location`` field
        # of wound records).  Values are the player-facing strings —
        # underscored canonical keys (``"left_arm"``) become spaced
        # display strings (``"left arm"``).
        "location_display": {
            "head": "head",
            "face": "face",
            "neck": "neck",
            "chest": "chest",
            "abdomen": "abdomen",
            "back": "back",
            "groin": "groin",
            "left_arm": "left arm",
            "right_arm": "right arm",
            "left_hand": "left hand",
            "right_hand": "right hand",
            "left_thigh": "left thigh",
            "right_thigh": "right thigh",
            "left_shin": "left shin",
            "right_shin": "right shin",
            "left_foot": "left foot",
            "right_foot": "right foot",
            "left_eye": "left eye",
            "right_eye": "right eye",
            "left_ear": "left ear",
            "right_ear": "right ear",
        },

        # Symmetric body-noun pair table (issue #350 / PR-A).  Each
        # entry maps a pair shorthand (``"eyes"``, ``"arms"``, ...) to
        # the ``(left_location, right_location)`` tuple it collapses.
        # Consumed by the longdesc renderer's pair-collapse pass, the
        # body-noun flex / side-aware singular routing, and the
        # ``describe`` command's pair-shorthand expansion.  Previously
        # this lived as a global ``world.combat.constants.PAIR_MERGE_KEYS``
        # constant; moving it here lets non-humans declare their own
        # anatomy (cyclops → ``{}``; insectoid compound eye → ``{}``;
        # spider → ``{"eyes": ("anterior_eyes", "posterior_eyes"), ...}``;
        # hydra → multi-head pairs).  The global constant in
        # ``world.combat.constants`` is now derived from this table.
        "pair_keys": {
            "eyes":   ("left_eye",   "right_eye"),
            "ears":   ("left_ear",   "right_ear"),
            "arms":   ("left_arm",   "right_arm"),
            "hands":  ("left_hand",  "right_hand"),
            "thighs": ("left_thigh", "right_thigh"),
            "shins":  ("left_shin",  "right_shin"),
            "feet":   ("left_foot",  "right_foot"),
        },

        # Organ table (issue #356 Phase 1). Each entry's data shape
        # mirrors the historical global ``world.medical.constants.ORGANS``
        # constant — that constant is now derived from this table so
        # existing callers keep working. Non-humans declare their own
        # organ table here (a rat's skeleton looks nothing like a
        # human's even though both have hearts and livers).
        #
        # Keys are organ identifiers; the wound system uses these as
        # the ``organ`` field on wound records.  Values declare the
        # bulk container (which longdesc surface clothing covers them
        # by), the optional ``display_location`` override (issue #346
        # — sensory organs surface at a more specific longdesc line),
        # max HP, hit weight (random-hit distribution), capacity
        # contribution wiring, and various capability flags
        # (vital / harvestable / scarring / etc.).
        "organs": {
            # HEAD CONTAINER → ORGANS INSIDE
            "brain": {
                "container": "head", "max_hp": 10, "hit_weight": "very_rare",
                "vital": True, "capacity": "consciousness", "contribution": "total",
                "special": "damage_always_scars", "can_scar": True, "can_heal": False,
                "can_be_harvested": True
            },
            "left_eye": {
                "container": "head", "display_location": "left_eye",
                "max_hp": 10, "hit_weight": "rare",
                "capacity": "sight", "contribution": "major", "disfiguring_if_lost": True,
                "damage_always_scars": True, "vulnerable_to_blunt": False,
                "can_be_harvested": True
            },
            "right_eye": {
                "container": "head", "display_location": "right_eye",
                "max_hp": 10, "hit_weight": "rare",
                "capacity": "sight", "contribution": "major", "disfiguring_if_lost": True,
                "damage_always_scars": True, "vulnerable_to_blunt": False,
                "can_be_harvested": True
            },
            "left_ear": {
                "container": "head", "display_location": "left_ear",
                "max_hp": 12, "hit_weight": "rare",
                "capacity": "hearing", "contribution": "major", "disfiguring_if_lost": True,
                "can_be_harvested": True
            },
            "right_ear": {
                "container": "head", "display_location": "right_ear",
                "max_hp": 12, "hit_weight": "rare",
                "capacity": "hearing", "contribution": "major", "disfiguring_if_lost": True,
                "can_be_harvested": True
            },
            "tongue": {
                "container": "head", "display_location": "face",
                "max_hp": 20, "hit_weight": "rare",
                "capacities": ["talking", "eating"], "talking_contribution": "major",
                "eating_contribution": "major", "disfiguring_if_lost": True,
                "can_be_harvested": True
            },
            "jaw": {
                "container": "head", "display_location": "face",
                "max_hp": 10, "hit_weight": "rare",
                "capacities": ["talking", "eating"], "talking_contribution": "major",
                "eating_contribution": "moderate", "disfiguring_if_lost": True, "can_scar": False,
                "can_be_harvested": True
            },
            # Nose — issue #355.  Surfaces at the ``face`` longdesc
            # the same way jaw and tongue do.  Damage doesn't affect a
            # named capacity (no smell capacity in scope), but it's
            # disfiguring and harvestable.
            "nose": {
                "container": "head", "display_location": "face",
                "max_hp": 8, "hit_weight": "rare",
                "disfiguring_if_lost": True,
                "can_be_harvested": True,
            },

            # NECK CONTAINER → DECAPITATION STRUCTURE
            "cervical_spine": {
                "container": "neck", "max_hp": 12, "hit_weight": "rare",
                "vital": True, "capacity": "neck_integrity", "contribution": "total",
                "causes_pain_when_damaged": True, "can_be_destroyed": True
            },

            # CHEST CONTAINER → VITAL ORGANS INSIDE
            "heart": {
                "container": "chest", "max_hp": 15, "hit_weight": "uncommon",
                "vital": True, "capacity": "blood_pumping", "contribution": "total",
                "can_be_harvested": True, "can_be_replaced": True
            },
            "left_lung": {
                "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
                "capacity": "breathing", "contribution": "major", "can_be_harvested": False,
                "backup_available": True
            },
            "right_lung": {
                "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
                "capacity": "breathing", "contribution": "major", "can_be_harvested": False,
                "backup_available": True
            },

            # ABDOMEN CONTAINER → DIGESTIVE/FILTER ORGANS INSIDE
            "liver": {
                "container": "abdomen", "max_hp": 20, "hit_weight": "uncommon",
                "vital": True, "capacity": "digestion", "contribution": "total",
                "can_be_harvested": True, "can_be_replaced": True
            },
            "left_kidney": {
                "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
                "capacity": "blood_filtration", "contribution": "major",
                "can_be_harvested": True, "backup_available": True
            },
            "right_kidney": {
                "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
                "capacity": "blood_filtration", "contribution": "major",
                "can_be_harvested": True, "backup_available": True
            },
            "stomach": {
                "container": "abdomen", "max_hp": 20, "hit_weight": "uncommon",
                "capacity": "digestion", "contribution": "moderate", "vital": False,
                "can_survive_loss": True
            },

            # BACK CONTAINER → STRUCTURAL ORGANS INSIDE
            "thoracolumbar_spine": {
                "container": "back", "max_hp": 25, "hit_weight": "uncommon",
                "capacity": "moving", "contribution": "total", "cannot_be_destroyed": True,
                "causes_pain_when_damaged": True, "paralysis_if_destroyed": True
            },

            # ARM BONES
            "left_humerus": {
                "container": "left_arm", "max_hp": 25, "hit_weight": "common",
                "capacity": "manipulation", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },
            "right_humerus": {
                "container": "right_arm", "max_hp": 25, "hit_weight": "common",
                "capacity": "manipulation", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },

            # HAND BONES
            "left_metacarpals": {
                "container": "left_hand", "max_hp": 15, "hit_weight": "uncommon",
                "capacity": "manipulation", "contribution": "moderate", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "small_bones"
            },
            "right_metacarpals": {
                "container": "right_hand", "max_hp": 15, "hit_weight": "uncommon",
                "capacity": "manipulation", "contribution": "moderate", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "small_bones"
            },

            # LEG BONES
            "left_femur": {
                "container": "left_thigh", "max_hp": 30, "hit_weight": "common",
                "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },
            "right_femur": {
                "container": "right_thigh", "max_hp": 30, "hit_weight": "common",
                "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },
            "left_tibia": {
                "container": "left_shin", "max_hp": 25, "hit_weight": "common",
                "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },
            "right_tibia": {
                "container": "right_shin", "max_hp": 25, "hit_weight": "common",
                "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "long_bone"
            },

            # FOOT BONES
            "left_metatarsals": {
                "container": "left_foot", "max_hp": 20, "hit_weight": "uncommon",
                "capacity": "moving", "contribution": "minor", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "small_bones"
            },
            "right_metatarsals": {
                "container": "right_foot", "max_hp": 20, "hit_weight": "uncommon",
                "capacity": "moving", "contribution": "minor", "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "small_bones"
            },

            # STRUCTURAL ORGAN FOR MOVEMENT (groin container — issue #325)
            "pelvis": {
                "container": "groin", "max_hp": 25, "hit_weight": "uncommon",
                "capacity": "moving", "contribution": "total", "vital": True
            },
        },

        # Severability tables (issue #356 Phase 2).  Each of these
        # was previously a global ``world.combat.constants`` constant
        # that baked humanoid limb structure into combat / severance.
        # Moved here so non-humans can declare their own anatomy
        # (rat fore/hindlimbs instead of arms/legs, tail as a new
        # severable container, etc.).
        #
        # ``severable_containers`` is the closed set of body locations
        # that can be detached as discrete items.  ``severed_head_locations``
        # is the head-cluster bundle that travels with a decapitation
        # (face, neck, eyes, ears, hair).  ``sever_hand_by_container``
        # maps a limb container to the hand-side whose wielded weapon
        # detaches with it.  ``limb_downstream_chain`` and ``limb_parent``
        # encode the proximal→distal chain (severing a thigh takes the
        # shin and foot).
        "severable_containers": frozenset({
            "head",
            "left_arm", "right_arm",
            "left_hand", "right_hand",
            "left_thigh", "right_thigh",
            "left_shin", "right_shin",
            "left_foot", "right_foot",
        }),
        "severed_head_locations": frozenset({
            "hair", "head", "face", "neck",
            "left_eye", "right_eye",
            "left_ear", "right_ear",
        }),
        "sever_hand_by_container": {
            "left_arm": "left",
            "left_hand": "left",
            "right_arm": "right",
            "right_hand": "right",
        },
        # Grasping appendages (#307, PR-H1).  Container locations that
        # can wield items — the canonical source of truth for what the
        # Mr. Hands system treats as a hand slot.  Generalised beyond
        # "hand" from day one so prehensile tails, grasping feet, and
        # multi-armed anatomies declare their own without renaming the
        # concept (a humanoid robot's three claws are
        # ``grasping_containers``; a monkey's prehensile tail joins
        # this set on monkey-species variants; an octopus declares
        # eight tentacle locations here).  Severance / install /
        # ``dress`` flows consult this to decide which containers are
        # wieldable slots.  Future PR-H2 makes ``character.hands`` a
        # derived view that walks this set against the current
        # severance state.
        "grasping_containers": frozenset({
            "left_hand", "right_hand",
        }),
        "limb_downstream_chain": {
            "left_arm":    ("left_arm", "left_hand"),
            "left_hand":   ("left_hand",),
            "left_thigh":  ("left_thigh", "left_shin", "left_foot"),
            "left_shin":   ("left_shin", "left_foot"),
            "left_foot":   ("left_foot",),
            "right_arm":   ("right_arm", "right_hand"),
            "right_hand":  ("right_hand",),
            "right_thigh": ("right_thigh", "right_shin", "right_foot"),
            "right_shin":  ("right_shin", "right_foot"),
            "right_foot":  ("right_foot",),
        },
        "limb_parent": {
            "left_hand":  "left_arm",
            "right_hand": "right_arm",
            "left_shin":  "left_thigh",
            "right_shin": "right_thigh",
            "left_foot":  "left_shin",
            "right_foot": "right_shin",
        },

        # Display order and region groupings (issue #356 Phase 3).
        # Previously global ``ANATOMICAL_DISPLAY_ORDER`` and
        # ``ANATOMICAL_REGIONS`` in world/combat/constants.py.  Non-
        # humanoid anatomies have a different render order — rats add
        # a tail at the end, insectoids might render thorax/abdomen
        # differently, plants might not have a sensible head-to-toe
        # axis at all.
        "anatomical_display_order": [
            # Head region
            "hair", "left_eye", "right_eye", "head", "face",
            "left_ear", "right_ear", "neck",
            # Torso region
            "chest", "back", "abdomen",
            # Arm region
            "left_arm", "right_arm", "left_hand", "right_hand",
            # Leg region
            "groin", "left_thigh", "right_thigh",
            "left_shin", "right_shin", "left_foot", "right_foot",
        ],
        "anatomical_regions": {
            "head_region": ["hair", "left_eye", "right_eye", "head", "face",
                            "left_ear", "right_ear", "neck"],
            "torso_region": ["chest", "back", "abdomen"],
            "arm_region": ["left_arm", "right_arm",
                           "left_hand", "right_hand"],
            "leg_region": ["groin", "left_thigh", "right_thigh",
                           "left_shin", "right_shin",
                           "left_foot", "right_foot"],
        },

        # Default longdesc surfaces a fresh character is initialized
        # with (issue #356 Phase 3).  Previously the global
        # ``DEFAULT_LONGDESC_LOCATIONS`` in world/combat/constants.py.
        # Each value defaults to ``None`` (no authored prose); the
        # ``describe`` command fills these in over time.
        "default_longdesc_locations": {
            "hair": None,
            "left_eye": None, "right_eye": None, "head": None, "face": None,
            "left_ear": None, "right_ear": None, "neck": None,
            "chest": None, "back": None, "abdomen": None, "groin": None,
            "left_arm": None, "right_arm": None,
            "left_hand": None, "right_hand": None,
            "left_thigh": None, "right_thigh": None,
            "left_shin": None, "right_shin": None,
            "left_foot": None, "right_foot": None,
        },

        # Curated vocabulary of singular body nouns the longdesc
        # token resolver flexes as NOUNS rather than verbs (issue
        # #356 follow-up; previously
        # :data:`world.combat.constants.LONGDESC_FLEX_NOUNS`).  Pair-
        # keyed singulars (eye/ear/arm/hand/...) are derived
        # automatically from ``pair_keys`` and need not be repeated
        # here.  Add words that an author would brace inside a
        # longdesc and that the renderer should number-flex; default
        # behavior for unknown braced words is to flex as a verb.
        "longdesc_flex_nouns": {
            # Limbs / joints not covered by a pair entry.
            "leg", "shoulder", "hip", "knee", "elbow", "wrist", "ankle",
            "calf", "forearm", "thumb", "finger", "toe",
            # Face / head detail.
            "lip", "nostril", "eyebrow", "eyelash", "cheek", "dimple",
            "jaw", "tooth",
            # Torso / rear.
            "rib", "collarbone", "knuckle", "nail",
            "breast", "tit", "nipple", "ass", "buttock",
            # Skin features authors commonly pluralize.
            "scar", "freckle",
        },

        # Capacity → organ wiring (issue #356 follow-up).  Previously
        # global ``world.medical.constants.BODY_CAPACITIES``.  The
        # capacities themselves (sight, hearing, breathing, moving)
        # are universal mammalian concepts; the organs that carry
        # them differ across species — a rat's "moving" references
        # hindleg/hindpaw bones, not human femur/tibia/metatarsals.
        #
        # Shape mirrors the legacy global verbatim — each entry
        # carries the organ list plus capacity-specific thresholds,
        # modifiers, and contribution wiring.
        "body_capacities": {
            "consciousness": {
                "organs": ["brain"],
                "modifiers": ["pain", "blood_pumping", "breathing",
                              "blood_filtration"],
                "effect": "unconscious_flag",
                "description": "Difference between functioning PC and "
                               "unconscious state",
            },
            "blood_pumping": {
                "organs": ["heart"],
                "fatal_threshold": 0.0,
                "directly_fatal": True,
                "affects": ["consciousness", "moving"],
                "description": "Circulation of blood through body — "
                               "zero equals death",
            },
            "breathing": {
                "organs": ["left_lung", "right_lung"],
                "fatal_threshold": 0.0,
                "organ_contribution": 0.5,
                "affects": ["consciousness", "moving"],
            },
            "digestion": {
                "organs": ["liver", "stomach"],
                "liver_contribution": 1.0,
                "stomach_contribution": 0.5,
                "fatal_threshold": 0.0,
            },
            "neck_integrity": {
                "organs": ["cervical_spine"],
                "fatal_threshold": 0.0,
                "directly_fatal": True,
                "affects": ["consciousness", "breathing", "moving"],
                "description": "Integrity of the neck — zero equals "
                               "decapitation/death",
            },
            "blood_loss": {
                "source": "bleeding_injuries",
                "directly_fatal": True,
                "description": "Blood loss kills — exact threshold "
                               "uses constants",
            },
            "sight": {
                "organs": ["left_eye", "right_eye"],
                "organ_contribution": 0.5,
                "affects": ["shooting_accuracy", "melee_hit_chance",
                            "work_speed"],
                "total_loss_penalty": "blindness",
            },
            "hearing": {
                "organs": ["left_ear", "right_ear"],
                "organ_contribution": 0.5,
                "affects": ["trade_price_improvement"],
                "total_loss_penalty": "deafness",
            },
            "moving": {
                "organs": ["thoracolumbar_spine", "pelvis",
                           "left_femur", "right_femur",
                           "left_tibia", "right_tibia",
                           "left_metatarsals", "right_metatarsals"],
                "thoracolumbar_spine_contribution": 1.0,
                "pelvis_contribution": 1.0,
                "femur_contribution": 0.4,
                "tibia_contribution": 0.4,
                "metatarsal_contribution": 0.1,
                "incapacitation_threshold": 0.15,
                "affects": ["movement_speed"],
            },
            "manipulation": {
                "organs": ["left_humerus", "right_humerus",
                           "left_metacarpals", "right_metacarpals"],
                "humerus_contribution": 0.4,
                "metacarpal_contribution": 0.2,
                "affects": ["work_speed", "melee_accuracy"],
            },
            "talking": {
                "organs": ["jaw", "tongue"],
                "affects": ["social_impact"],
                "total_loss_effects": ["cannot_negotiate", "social_penalty"],
            },
            "eating": {
                "organs": ["jaw", "tongue"],
                "jaw_primary": True,
                "affects": ["nutrition_efficiency"],
            },
            "blood_filtration": {
                "organs": ["left_kidney", "right_kidney"],
                "organ_contribution": 0.5,
                "affects": ["disease_resistance", "consciousness"],
                "total_loss_fatal": True,
            },
        },

        # Compound names used when severance carries downstream limb
        # parts off the body as a single Appendage (issue #339).
        # Severing at the thigh takes shin + foot, so the Appendage
        # reads "left leg" rather than "left thigh".  Severing at the
        # shin takes the foot, so it reads "left lower leg".  Severing
        # at the wrist or ankle is named for the cut location.  Keys
        # mirror ``limb_downstream_chain`` above.
        "severed_chain_display": {
            "left_arm":    "left arm",
            "right_arm":   "right arm",
            "left_hand":   "left hand",
            "right_hand":  "right hand",
            "left_thigh":  "left leg",
            "right_thigh": "right leg",
            "left_shin":   "left lower leg",
            "right_shin":  "right lower leg",
            "left_foot":   "left foot",
            "right_foot":  "right foot",
        },

        # Decay-tier prefix templates for severed body parts.  Rendered
        # by :func:`get_species_part_name` with ``{species}`` and
        # ``{part}`` substitution.  Note "rotting" and "skeletal" drop
        # the species token deliberately (see module docstring).
        "decay_part_prefixes": {
            "fresh":    "{species} {part}",
            "early":    "{species} {part}",
            "moderate": "rotting {part}",
            "advanced": "rotting {part}",
            "skeletal": "skeletal {part}",
        },

        # Decay-tier prefix templates for harvested organs.  Same shape
        # as ``decay_part_prefixes`` but the skeletal tier uses
        # ``desiccated`` — soft tissue dries out rather than
        # skeletonizing.  Rendered by :func:`get_species_organ_name`.
        "decay_organ_prefixes": {
            "fresh":    "{species} {organ}",
            "early":    "{species} {organ}",
            "moderate": "rotting {organ}",
            "advanced": "rotting {organ}",
            "skeletal": "desiccated {organ}",
        },

        # Decay-tier corpse-name templates.  Rendered by
        # :func:`get_species_corpse_name`.  Skeletal abandons "corpse"
        # for "remains" — a fully skeletonized body isn't a corpse in
        # the colloquial sense and the change in vocabulary signals
        # the irreversibility of that decay tier.
        "decay_corpse_names": {
            "fresh":    "human corpse",
            "early":    "human corpse",
            "moderate": "rotting corpse",
            "advanced": "rotting corpse",
            "skeletal": "skeletal remains",
        },

        # Decay-tier corpse *description* templates — the body paragraph
        # rendered on ``look`` (distinct from the glance-level name in
        # ``decay_corpse_names``).  Rendered by
        # :func:`get_species_corpse_description` with ``{species}`` and
        # ``{base_desc}`` substitution.  ``{base_desc}`` is the
        # death-time physical description; it is embedded only in the
        # fresh / early templates — by moderate the original features
        # have deteriorated enough that the snapshot no longer applies,
        # so those tiers describe the decay state generically.
        #
        # Unlike the *name* templates (which hard-drop the species token
        # at moderate+), every description tier keeps ``{species}`` so a
        # known species reads naturally at all stages ("Decomposing
        # human remains").  The token-drop convention (module docstring,
        # issue #215) is applied for *unknown* species instead: the
        # helper substitutes an empty token and collapses whitespace,
        # yielding "Decomposing remains." rather than misclaiming human.
        "decay_corpse_descriptions": {
            "fresh": (
                "A recently deceased {species} body. {base_desc} "
                "The body appears fresh, with no signs of decomposition "
                "yet visible."
            ),
            "early": (
                "A pale {species} corpse. {base_desc} The skin has begun "
                "to pale and cool, with early signs of lividity visible."
            ),
            "moderate": (
                "Decomposing {species} remains. Bloating and "
                "discoloration have begun, with a distinct odor of "
                "decay. The original features are still recognizable but "
                "deteriorating."
            ),
            "advanced": (
                "Putrid {species} remains. Advanced decomposition has set "
                "in with severe bloating, fluid leakage, and strong "
                "putrid odors. Identification is becoming difficult."
            ),
            "skeletal": (
                "Skeletal {species} remains. Only bones, dried tissue, "
                "and clothing remain. The decomposition process is nearly "
                "complete."
            ),
        },
    },

    # =================================================================
    # RAT — first non-human species (issue #356 Phase 4).
    # =================================================================
    #
    # Quadrupedal anatomy: fore/hindlimb pairs instead of arms/legs, a
    # tail as an extra severable container, and snout/fur in place of
    # face/hair on the head cluster.  Internal organs collapse to the
    # same mammalian set as human (brain, heart, lungs, liver) since
    # the physiology is shared — only the skeletal organs and HP
    # values diverge.  Cannot wield items (no hand-side map), so
    # severance never pulls a weapon onto a detached forepaw.
    "rat": {
        "display_name": "rat",

        "location_display": {
            "head": "head",
            "snout": "snout",
            "neck": "neck",
            "fur": "fur",
            "chest": "chest",
            "abdomen": "abdomen",
            "back": "back",
            "groin": "groin",
            "left_foreleg":  "left foreleg",
            "right_foreleg": "right foreleg",
            "left_forepaw":  "left forepaw",
            "right_forepaw": "right forepaw",
            "left_hindleg":  "left hindleg",
            "right_hindleg": "right hindleg",
            "left_hindpaw":  "left hindpaw",
            "right_hindpaw": "right hindpaw",
            "tail": "tail",
            "left_eye":  "left eye",
            "right_eye": "right eye",
            "left_ear":  "left ear",
            "right_ear": "right ear",
        },

        "severed_chain_display": {
            "left_foreleg":  "left foreleg",
            "right_foreleg": "right foreleg",
            "left_forepaw":  "left forepaw",
            "right_forepaw": "right forepaw",
            "left_hindleg":  "left hindleg",
            "right_hindleg": "right hindleg",
            "left_hindpaw":  "left hindpaw",
            "right_hindpaw": "right hindpaw",
            "tail":          "tail",
        },

        "decay_part_prefixes": {
            "fresh":    "{species} {part}",
            "early":    "{species} {part}",
            "moderate": "rotting {part}",
            "advanced": "rotting {part}",
            "skeletal": "skeletal {part}",
        },
        "decay_organ_prefixes": {
            "fresh":    "{species} {organ}",
            "early":    "{species} {organ}",
            "moderate": "rotting {organ}",
            "advanced": "rotting {organ}",
            "skeletal": "desiccated {organ}",
        },
        "decay_corpse_names": {
            "fresh":    "rat carcass",
            "early":    "rat carcass",
            "moderate": "rotting carcass",
            "advanced": "rotting carcass",
            "skeletal": "skeletal remains",
        },
        "decay_corpse_descriptions": {
            "fresh": (
                "A small {species} body, recently dead. {base_desc} "
                "The fur is still in place and the body shows no signs "
                "of decomposition yet."
            ),
            "early": (
                "A small {species} carcass. {base_desc} The fur has "
                "begun to mat and the small body has gone stiff."
            ),
            "moderate": (
                "Decomposing small mammalian remains. The fur is "
                "matted and falling away in patches, with a sharp odor "
                "of rot rising from the bloated body."
            ),
            "advanced": (
                "Putrid small mammalian remains. Most of the soft "
                "tissue has liquefied; the skeleton is visible through "
                "what is left of the fur."
            ),
            "skeletal": (
                "Skeletal {species} remains. Tiny bones and the long, "
                "ringed sweep of the tail are all that is left."
            ),
        },

        "pair_keys": {
            "eyes":      ("left_eye",      "right_eye"),
            "ears":      ("left_ear",      "right_ear"),
            "forelegs":  ("left_foreleg",  "right_foreleg"),
            "forepaws":  ("left_forepaw",  "right_forepaw"),
            "hindlegs":  ("left_hindleg",  "right_hindleg"),
            "hindpaws":  ("left_hindpaw",  "right_hindpaw"),
        },

        # Rat organs — shared mammalian internals (brain, heart, etc.)
        # plus rat-specific skeletal organs at fore/hindlimb / tail
        # containers.  HP values scaled down for a small body.
        "organs": {
            # Head
            "brain":     {"container": "head", "max_hp": 5, "hit_weight": "very_rare",
                          "vital": True, "capacity": "consciousness",
                          "contribution": "total"},
            "left_eye":  {"container": "head", "display_location": "left_eye",
                          "max_hp": 4, "hit_weight": "rare",
                          "capacity": "sight", "contribution": "major",
                          "disfiguring_if_lost": True},
            "right_eye": {"container": "head", "display_location": "right_eye",
                          "max_hp": 4, "hit_weight": "rare",
                          "capacity": "sight", "contribution": "major",
                          "disfiguring_if_lost": True},
            "left_ear":  {"container": "head", "display_location": "left_ear",
                          "max_hp": 5, "hit_weight": "rare",
                          "capacity": "hearing", "contribution": "major",
                          "disfiguring_if_lost": True},
            "right_ear": {"container": "head", "display_location": "right_ear",
                          "max_hp": 5, "hit_weight": "rare",
                          "capacity": "hearing", "contribution": "major",
                          "disfiguring_if_lost": True},
            "jaw":       {"container": "head", "max_hp": 5, "hit_weight": "rare",
                          "capacities": ["eating"],
                          "eating_contribution": "major"},

            # Neck
            "cervical_spine": {"container": "neck", "max_hp": 5,
                               "hit_weight": "rare", "vital": True,
                               "capacity": "neck_integrity",
                               "contribution": "total",
                               "can_be_destroyed": True},

            # Chest / abdomen / back / groin — mammalian universals
            "heart":         {"container": "chest", "max_hp": 6,
                              "hit_weight": "uncommon", "vital": True,
                              "capacity": "blood_pumping", "contribution": "total"},
            "left_lung":     {"container": "chest", "max_hp": 8,
                              "hit_weight": "uncommon", "capacity": "breathing",
                              "contribution": "major", "backup_available": True},
            "right_lung":    {"container": "chest", "max_hp": 8,
                              "hit_weight": "uncommon", "capacity": "breathing",
                              "contribution": "major", "backup_available": True},
            "liver":         {"container": "abdomen", "max_hp": 8,
                              "hit_weight": "uncommon", "vital": True,
                              "capacity": "digestion", "contribution": "total"},
            "left_kidney":   {"container": "abdomen", "max_hp": 5,
                              "hit_weight": "uncommon",
                              "capacity": "blood_filtration",
                              "contribution": "major",
                              "backup_available": True},
            "right_kidney":  {"container": "abdomen", "max_hp": 5,
                              "hit_weight": "uncommon",
                              "capacity": "blood_filtration",
                              "contribution": "major",
                              "backup_available": True},
            "stomach":       {"container": "abdomen", "max_hp": 8,
                              "hit_weight": "uncommon",
                              "capacity": "digestion",
                              "contribution": "moderate"},
            "thoracolumbar_spine": {"container": "back", "max_hp": 10,
                                    "hit_weight": "uncommon",
                                    "capacity": "moving", "contribution": "total",
                                    "cannot_be_destroyed": True,
                                    "paralysis_if_destroyed": True},
            "pelvis":        {"container": "groin", "max_hp": 10,
                              "hit_weight": "uncommon",
                              "capacity": "moving", "contribution": "total",
                              "vital": True},

            # Foreleg skeletal organs (analogous to humerus / metacarpals)
            "left_foreleg_bone":   {"container": "left_foreleg", "max_hp": 10,
                                    "hit_weight": "common",
                                    "capacity": "manipulation",
                                    "contribution": "major",
                                    "can_be_destroyed": True,
                                    "fracture_vulnerable": True,
                                    "bone_type": "long_bone"},
            "right_foreleg_bone":  {"container": "right_foreleg", "max_hp": 10,
                                    "hit_weight": "common",
                                    "capacity": "manipulation",
                                    "contribution": "major",
                                    "can_be_destroyed": True,
                                    "fracture_vulnerable": True,
                                    "bone_type": "long_bone"},
            "left_forepaw_bones":  {"container": "left_forepaw", "max_hp": 6,
                                    "hit_weight": "uncommon",
                                    "capacity": "manipulation",
                                    "contribution": "moderate",
                                    "can_be_destroyed": True,
                                    "bone_type": "small_bones"},
            "right_forepaw_bones": {"container": "right_forepaw", "max_hp": 6,
                                    "hit_weight": "uncommon",
                                    "capacity": "manipulation",
                                    "contribution": "moderate",
                                    "can_be_destroyed": True,
                                    "bone_type": "small_bones"},

            # Hindleg skeletal organs
            "left_hindleg_bone":   {"container": "left_hindleg", "max_hp": 12,
                                    "hit_weight": "common",
                                    "capacity": "moving",
                                    "contribution": "major",
                                    "can_be_destroyed": True,
                                    "fracture_vulnerable": True,
                                    "bone_type": "long_bone"},
            "right_hindleg_bone":  {"container": "right_hindleg", "max_hp": 12,
                                    "hit_weight": "common",
                                    "capacity": "moving",
                                    "contribution": "major",
                                    "can_be_destroyed": True,
                                    "fracture_vulnerable": True,
                                    "bone_type": "long_bone"},
            "left_hindpaw_bones":  {"container": "left_hindpaw", "max_hp": 8,
                                    "hit_weight": "uncommon",
                                    "capacity": "moving",
                                    "contribution": "minor",
                                    "can_be_destroyed": True,
                                    "bone_type": "small_bones"},
            "right_hindpaw_bones": {"container": "right_hindpaw", "max_hp": 8,
                                    "hit_weight": "uncommon",
                                    "capacity": "moving",
                                    "contribution": "minor",
                                    "can_be_destroyed": True,
                                    "bone_type": "small_bones"},

            # Tail — rat-unique
            "tail_vertebrae": {"container": "tail", "max_hp": 6,
                               "hit_weight": "uncommon",
                               "can_be_destroyed": True,
                               "bone_type": "long_bone"},
        },

        # Severability — rat can lose any limb or the tail; head
        # severance handled like human.
        "severable_containers": frozenset({
            "head",
            "left_foreleg", "right_foreleg",
            "left_forepaw", "right_forepaw",
            "left_hindleg", "right_hindleg",
            "left_hindpaw", "right_hindpaw",
            "tail",
        }),
        "severed_head_locations": frozenset({
            "fur", "head", "snout", "neck",
            "left_eye", "right_eye",
            "left_ear", "right_ear",
        }),
        # Rats can't wield items.
        "sever_hand_by_container": {},
        # Rats have no grasping appendages (#307, PR-H1).  Forepaws
        # can manipulate but the system doesn't model rodent
        # dexterity as wielding — they don't have an opposable grip.
        # Empty set means Mr. Hands surfaces no slots on a rat.
        "grasping_containers": frozenset(),
        # Two-segment limbs: foreleg+forepaw, hindleg+hindpaw.  No
        # three-segment thigh→shin→foot chain.
        "limb_downstream_chain": {
            "left_foreleg":  ("left_foreleg",  "left_forepaw"),
            "right_foreleg": ("right_foreleg", "right_forepaw"),
            "left_forepaw":  ("left_forepaw",),
            "right_forepaw": ("right_forepaw",),
            "left_hindleg":  ("left_hindleg",  "left_hindpaw"),
            "right_hindleg": ("right_hindleg", "right_hindpaw"),
            "left_hindpaw":  ("left_hindpaw",),
            "right_hindpaw": ("right_hindpaw",),
            "tail":          ("tail",),
        },
        "limb_parent": {
            "left_forepaw":  "left_foreleg",
            "right_forepaw": "right_foreleg",
            "left_hindpaw":  "left_hindleg",
            "right_hindpaw": "right_hindleg",
        },

        # Render order: head-cluster, torso, forelegs, hindlegs, tail.
        "anatomical_display_order": [
            "fur",
            "left_eye", "right_eye",
            "head", "snout",
            "left_ear", "right_ear",
            "neck",
            "chest", "back", "abdomen", "groin",
            "left_foreleg", "right_foreleg",
            "left_forepaw", "right_forepaw",
            "left_hindleg", "right_hindleg",
            "left_hindpaw", "right_hindpaw",
            "tail",
        ],
        "anatomical_regions": {
            "head_region": ["fur", "left_eye", "right_eye", "head", "snout",
                            "left_ear", "right_ear", "neck"],
            "torso_region": ["chest", "back", "abdomen", "groin"],
            "foreleg_region": ["left_foreleg", "right_foreleg",
                               "left_forepaw", "right_forepaw"],
            "hindleg_region": ["left_hindleg", "right_hindleg",
                               "left_hindpaw", "right_hindpaw"],
            "tail_region": ["tail"],
        },
        "default_longdesc_locations": {
            "fur": None,
            "left_eye": None, "right_eye": None,
            "head": None, "snout": None,
            "left_ear": None, "right_ear": None,
            "neck": None,
            "chest": None, "back": None, "abdomen": None, "groin": None,
            "left_foreleg": None, "right_foreleg": None,
            "left_forepaw": None, "right_forepaw": None,
            "left_hindleg": None, "right_hindleg": None,
            "left_hindpaw": None, "right_hindpaw": None,
            "tail": None,
        },

        # Rat longdesc flex vocabulary (issue #356 follow-up).
        # Pair-keyed singulars (foreleg / forepaw / hindleg /
        # hindpaw / eye / ear) flow through ``pair_keys`` and don't
        # need repeating here.  These are the rat-specific anatomy
        # words an author might brace.
        "longdesc_flex_nouns": {
            # Rat anatomy detail.
            "tail", "snout", "fur", "whisker", "paw", "claw",
            "tooth", "incisor", "tuft",
            # Shared mammalian detail still useful for rat prose.
            "rib", "nostril", "lip", "nail", "scar",
        },

        # Rat capacity wiring — internal organs collapse to mammalian
        # universals (heart / lungs / liver / kidneys identical to
        # human); skeletal capacities re-wire to rat anatomy: moving
        # references hindleg/hindpaw bones, manipulation references
        # foreleg/forepaw bones (rats use forepaws for limited food
        # handling and grooming, not fine tool use).  Talking removed
        # — rats don't have a tongue/jaw vocalization capacity in our
        # model; eating retains jaw only.
        "body_capacities": {
            "consciousness": {
                "organs": ["brain"],
                "modifiers": ["pain", "blood_pumping", "breathing",
                              "blood_filtration"],
                "effect": "unconscious_flag",
            },
            "blood_pumping": {
                "organs": ["heart"],
                "fatal_threshold": 0.0,
                "directly_fatal": True,
                "affects": ["consciousness", "moving"],
            },
            "breathing": {
                "organs": ["left_lung", "right_lung"],
                "fatal_threshold": 0.0,
                "organ_contribution": 0.5,
                "affects": ["consciousness", "moving"],
            },
            "digestion": {
                "organs": ["liver", "stomach"],
                "liver_contribution": 1.0,
                "stomach_contribution": 0.5,
                "fatal_threshold": 0.0,
            },
            "neck_integrity": {
                "organs": ["cervical_spine"],
                "fatal_threshold": 0.0,
                "directly_fatal": True,
                "affects": ["consciousness", "breathing", "moving"],
            },
            "blood_loss": {
                "source": "bleeding_injuries",
                "directly_fatal": True,
            },
            "sight": {
                "organs": ["left_eye", "right_eye"],
                "organ_contribution": 0.5,
                "total_loss_penalty": "blindness",
            },
            "hearing": {
                "organs": ["left_ear", "right_ear"],
                "organ_contribution": 0.5,
                "total_loss_penalty": "deafness",
            },
            "moving": {
                # Rat locomotion: spine + pelvis + hindlegs +
                # hindpaws.  Forelegs assist (climbing, balance) but
                # aren't load-bearing in our model — they're under
                # ``manipulation`` instead.
                "organs": ["thoracolumbar_spine", "pelvis",
                           "left_hindleg_bone", "right_hindleg_bone",
                           "left_hindpaw_bones", "right_hindpaw_bones"],
                "thoracolumbar_spine_contribution": 1.0,
                "pelvis_contribution": 1.0,
                "hindleg_bone_contribution": 0.4,
                "hindpaw_bones_contribution": 0.1,
                "incapacitation_threshold": 0.15,
                "affects": ["movement_speed"],
            },
            "manipulation": {
                # Forepaw food-handling / grooming.  Lower contribution
                # weights than human — a rat with mangled forepaws can
                # still bite/move; it just can't manipulate food.
                "organs": ["left_foreleg_bone", "right_foreleg_bone",
                           "left_forepaw_bones", "right_forepaw_bones"],
                "foreleg_bone_contribution": 0.4,
                "forepaw_bones_contribution": 0.1,
                "affects": ["work_speed"],
            },
            "eating": {
                # Rats eat with jaw + teeth; no tongue manipulation
                # like humans have.
                "organs": ["jaw"],
                "jaw_primary": True,
                "affects": ["nutrition_efficiency"],
            },
            "blood_filtration": {
                "organs": ["left_kidney", "right_kidney"],
                "organ_contribution": 0.5,
                "total_loss_fatal": True,
            },
        },
    },
}


def _resolve_species(species: str | None) -> dict:
    """Return the species definition, falling back to ``human``.

    Centralized so every helper degrades gracefully on unknown / None
    species inputs without scattering ``.get(..., SPECIES_DEFINITIONS["human"])``
    boilerplate.
    """
    if not species:
        return SPECIES_DEFINITIONS["human"]
    return SPECIES_DEFINITIONS.get(species, SPECIES_DEFINITIONS["human"])


def get_species_longdesc_flex_nouns(species: str | None) -> set:
    """Return the species's curated set of longdesc flex-nouns.

    Issue #356 follow-up.  Previously
    :data:`world.combat.constants.LONGDESC_FLEX_NOUNS`.  Pair-keyed
    singulars (eye / ear / arm / etc.) flow through ``pair_keys`` and
    are unioned with this set at lookup time; this set holds the
    species's *non-pair* body vocabulary (limbs/joints, face detail,
    skin features).

    Rats add ``tail`` / ``snout`` / ``fur`` / ``whisker`` / ``paw`` /
    ``claw`` etc.; non-mammals would replace the curated vocabulary
    entirely.

    Args:
        species: Species identifier; ``None`` / unknown falls back to
            ``"human"``.

    Returns:
        ``set[str]`` of singular body nouns.  Returns a fresh set so
        callers can mutate without aliasing the registry.
    """
    spec = _resolve_species(species)
    return set(spec.get("longdesc_flex_nouns") or ())


def get_species_body_capacities(species: str | None) -> dict:
    """Return the capacity → organ wiring table for a species.

    Issue #356 follow-up.  Previously
    :data:`world.medical.constants.BODY_CAPACITIES`.  Capacities
    themselves (sight, hearing, breathing, moving, ...) are mammalian
    universals; the organs that carry each capacity differ per
    species (a rat's "moving" references hindleg/hindpaw bones, not
    human femur/tibia/metatarsals).

    Args:
        species: Species identifier; ``None`` / unknown falls back
            to ``"human"``.

    Returns:
        ``capacity_name → spec_dict`` mapping.  Each spec carries the
        organ list plus capacity-specific thresholds, modifiers, and
        contribution wiring.  Returns a fresh dict so callers can
        mutate without aliasing the registry.
    """
    spec = _resolve_species(species)
    return {
        k: dict(v) for k, v in (spec.get("body_capacities") or {}).items()
    }


def get_species_anatomical_display_order(species: str | None) -> list:
    """Return the canonical longdesc render order for a species.

    Issue #356 Phase 3.  Previously
    :data:`world.combat.constants.ANATOMICAL_DISPLAY_ORDER`.  Rats
    place the tail at the end, insectoids might shift thorax/abdomen
    around, etc.
    """
    spec = _resolve_species(species)
    return list(spec.get("anatomical_display_order") or [])


def get_species_anatomical_regions(species: str | None) -> dict:
    """Return region groupings used by the paragraph-break formatter.

    Issue #356 Phase 3.  Previously
    :data:`world.combat.constants.ANATOMICAL_REGIONS`.
    """
    spec = _resolve_species(species)
    return {k: list(v) for k, v in (spec.get("anatomical_regions") or {}).items()}


def get_species_default_longdesc_locations(species: str | None) -> dict:
    """Return the fresh-character default longdesc map.

    Issue #356 Phase 3.  Previously
    :data:`world.combat.constants.DEFAULT_LONGDESC_LOCATIONS`.  Used
    by ``Character.at_object_creation`` to seed a new character's
    longdesc dict with the species-appropriate surfaces.
    """
    spec = _resolve_species(species)
    return dict(spec.get("default_longdesc_locations") or {})


def get_species_severable_containers(species: str | None) -> frozenset:
    """Return the closed set of severable body locations for a species.

    Issue #356 Phase 2.  Previously a global
    :data:`world.combat.constants.SEVERABLE_CONTAINERS`; species variation
    means a rat has fore/hindlimb containers in place of arm/leg
    containers, plus a tail.

    Args:
        species: Species identifier; ``None`` / unknown falls back to
            ``"human"``.

    Returns:
        ``frozenset`` of canonical body-location names.
    """
    spec = _resolve_species(species)
    value = spec.get("severable_containers") or frozenset()
    return frozenset(value)


def get_species_severed_head_locations(species: str | None) -> frozenset:
    """Return the head-cluster bundle that travels with decapitation.

    Issue #356 Phase 2.  Previously a global
    :data:`world.combat.constants.SEVERED_HEAD_LOCATIONS`.  Rats
    declare ``snout`` instead of ``face``, ``fur`` instead of ``hair``;
    insectoids might bundle antennae here; etc.
    """
    spec = _resolve_species(species)
    value = spec.get("severed_head_locations") or frozenset()
    return frozenset(value)


def get_species_grasping_containers(species: str | None) -> frozenset:
    """Return the set of container locations that can grasp items.

    #307, PR-H1.  The canonical source of truth for what the Mr.
    Hands system treats as a hand slot.  Generalised beyond the
    literal "hand" concept so prehensile tails, grasping feet, and
    multi-armed anatomies can declare their own grasping containers
    without redefining vocabulary.  A humanoid robot with three
    claws declares those three claw containers here; an octopus
    declares eight tentacle containers; a quadruped with no
    opposable grip declares an empty set.

    Args:
        species: Species identifier; ``None`` / unknown falls back
            to ``"human"``.

    Returns:
        ``frozenset`` of canonical container names.  Empty when the
        species has no grasping appendages (most animals).
    """
    spec = _resolve_species(species)
    value = spec.get("grasping_containers") or frozenset()
    return frozenset(value)


def get_species_sever_hand_by_container(species: str | None) -> dict:
    """Return the limb-container → hand-side map for wielded-weapon
    detachment (issue #356 Phase 2).

    Previously :data:`world.combat.constants.SEVER_HAND_BY_CONTAINER`.
    Species without wielding hands (most animals) declare an empty dict.
    """
    spec = _resolve_species(species)
    return dict(spec.get("sever_hand_by_container") or {})


def get_species_limb_downstream_chain(species: str | None) -> dict:
    """Return the proximal→distal severance chain (issue #356 Phase 2).

    Previously :data:`world.combat.constants.LIMB_DOWNSTREAM_CHAIN`.
    Rats have a two-segment chain for fore/hind limbs (no three-segment
    thigh→shin→foot); insectoids might declare no chain at all (whole
    leg severs as one segment).
    """
    spec = _resolve_species(species)
    return dict(spec.get("limb_downstream_chain") or {})


def get_species_limb_parent(species: str | None) -> dict:
    """Return the distal→proximal parent map (issue #356 Phase 2).

    Previously :data:`world.combat.constants.LIMB_PARENT`.  Used by
    the wound-rendering cut-point filter to suppress downstream
    severance wounds when their parent is also severed.
    """
    spec = _resolve_species(species)
    return dict(spec.get("limb_parent") or {})


def get_species_organs(species: str | None) -> dict:
    """Return the organ table for a species.

    Each entry maps an organ identifier to its spec dict (container,
    max_hp, hit_weight, capacity wiring, capability flags, etc.).
    The shape mirrors the historical global
    :data:`world.medical.constants.ORGANS` constant; the constant is
    now derived from the human entry of this registry so existing
    callers keep working unchanged.

    Species variation:

    * Bilateral humanoids (humans, rat-people) declare the familiar
      head / chest / abdomen / arm / leg organ set.
    * Quadrupedal anatomies (rat, dog) declare fore/hind limb
      organs and a tail; their internal organs collapse to the same
      shape as humanoid (brain, heart, lungs, liver) since
      mammalian physiology is shared.
    * Non-mammalian anatomies (insectoid exoskeleton, plant-based)
      declare radically different organ tables; the wound /
      capacity / harvest pipelines all consume the species table
      uniformly via this helper.

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.

    Returns:
        Organ-name → spec mapping.  Returns a fresh dict so callers
        can mutate without aliasing the registry.
    """
    spec = _resolve_species(species)
    return dict(spec.get("organs") or {})


def get_organ_spec(organ_name: str, species: str | None = None) -> dict:
    """Return the spec dict for a single organ within a species.

    Convenience wrapper around :func:`get_species_organs` for the
    common single-organ lookup pattern.  Returns an empty dict when
    the organ name isn't declared by the species, mirroring the
    historical ``ORGANS.get(organ_name, {})`` behavior so callers
    that defensively read against an unknown organ keep working.

    Args:
        organ_name: Organ identifier (e.g. ``"left_humerus"``).
        species: Species identifier; ``None`` / unknown falls back to
            ``"human"``.

    Returns:
        Spec dict or ``{}`` when the organ isn't declared.
    """
    return get_species_organs(species).get(organ_name, {})


def get_species_pair_keys(species: str | None) -> dict:
    """Return the symmetric pair table for a species.

    Each entry maps a pair shorthand (``"eyes"``, ``"arms"``, ...) to
    a ``(left_location, right_location)`` tuple.  The longdesc
    renderer's pair-collapse pass, the body-noun flex / side-aware
    singular routing, and the ``describe`` command's pair-shorthand
    expansion all consult this table to decide which surfaces pair
    on a given body.

    Species variation:

    * Bilateral humanoids (humans, rat-people, dogs) declare the
      familiar ``left_*``/``right_*`` pairs.
    * Single-instance organs (cyclops central eye, insectoid compound
      eye) declare no pair for that surface — destruction at that
      location is single-line by definition because the pair-collapse
      pass never reaches it.
    * Multi-pair anatomies (spider with anterior / posterior eye
      clusters) can declare any number of pairs keyed by the species's
      own anatomical vocabulary.

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.

    Returns:
        Pair-shorthand → ``(left, right)`` mapping.  Empty dict on
        species that declare no pairs (returns a fresh dict so callers
        can mutate without aliasing the registry).
    """
    spec = _resolve_species(species)
    return dict(spec.get("pair_keys") or {})


def get_species_location_display(species: str | None, location: str) -> str:
    """Return the display string for a body location under a species.

    Unmapped locations fall back to the raw token with underscores
    replaced by spaces — robust against ad-hoc anatomy keys that
    haven't been added to the registry yet (e.g. a future ``"tail"``
    or ``"third_arm"``).

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.
        location: Canonical body-location identifier
            (e.g. ``"left_arm"``).

    Returns:
        Display string suitable for embedding in player-facing prose.
    """
    spec = _resolve_species(species)
    mapping = spec.get("location_display") or {}
    if location in mapping:
        return mapping[location]
    return (location or "").replace("_", " ")


def get_species_part_name(
    species: str | None, location: str, decay_stage: str
) -> str:
    """Return the decay-modulated display name for a severed body part.

    Used by :class:`typeclasses.items.Appendage`,
    :class:`typeclasses.items.SeveredHead`, and any other detached
    body-part typeclass to render decay-aware glance names like
    ``"human left arm"`` (fresh) → ``"rotting left arm"`` (moderate)
    → ``"skeletal left arm"`` (skeletal).

    The output deliberately omits any article — callers compose with
    ``"a "`` / ``"the "`` per their context.

    Args:
        species: Species identifier; unknown / None → human.
        location: Canonical body-location identifier.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  Unknown stages fall back to
            the ``fresh`` template.

    Returns:
        Display string ready for use as ``self.key`` or in look output.
    """
    spec = _resolve_species(species)
    prefixes = spec.get("decay_part_prefixes") or {}
    template = prefixes.get(decay_stage) or prefixes.get("fresh") or "{part}"
    part = get_species_location_display(species, location)
    species_display = spec.get("display_name", "")
    return template.format(species=species_display, part=part)


def get_species_severed_chain_name(
    species: str | None, primary_container: str, decay_stage: str
) -> str:
    """Return the decay-modulated name for a severed limb chain (#339).

    When a limb is severed and pulls downstream parts off with it
    (severing a shin takes the foot; severing a thigh takes the whole
    leg), the resulting Appendage needs a compound anatomical name.
    Severing at ``left_thigh`` should read ``"human left leg"`` rather
    than ``"human left thigh"``; severing at ``left_shin`` should read
    ``"human left lower leg"`` rather than ``"human left shin"``.

    Falls back to :func:`get_species_part_name` (the single-container
    name) when the species has no ``severed_chain_display`` mapping or
    the container isn't listed in it. This keeps backwards compatibility
    with species that haven't been updated yet and with chain entries
    where the compound name happens to match the single name.

    Args:
        species: Species identifier; unknown / None → human.
        primary_container: The cut-point body location
            (e.g. ``"left_thigh"``).  The Appendage represents this
            location plus everything downstream.
        decay_stage: One of the standard decay-tier keys.

    Returns:
        Display string ready for use as ``appendage.key``.
    """
    spec = _resolve_species(species)
    chain_display = spec.get("severed_chain_display") or {}
    if primary_container not in chain_display:
        # No compound name for this container — fall back to the
        # canonical per-location naming.
        return get_species_part_name(species, primary_container, decay_stage)
    prefixes = spec.get("decay_part_prefixes") or {}
    template = prefixes.get(decay_stage) or prefixes.get("fresh") or "{part}"
    species_display = spec.get("display_name", "")
    part = chain_display[primary_container]
    return template.format(species=species_display, part=part)


def get_species_corpse_name(
    species: str | None, decay_stage: str
) -> str:
    """Return the decay-modulated display name for a whole corpse.

    Used by :class:`typeclasses.corpse.Corpse` to render decay-aware
    glance names like ``"human corpse"`` → ``"rotting corpse"`` →
    ``"skeletal remains"``.

    Args:
        species: Species identifier; unknown / None → human.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  Unknown stages fall back to
            the ``fresh`` template.

    Returns:
        Display string ready for use as ``corpse.key``.
    """
    spec = _resolve_species(species)
    names = spec.get("decay_corpse_names") or {}
    if decay_stage in names:
        return names[decay_stage]
    return names.get("fresh", "corpse")


def get_species_corpse_description(
    species: str | None,
    decay_stage: str | None,
    base_desc: str = "A lifeless body.",
) -> str:
    """Return the decay-modulated *body paragraph* for a whole corpse.

    Used by :class:`typeclasses.corpse.Corpse._build_decay_desc_paragraph`
    to render the description paragraph shown on ``look`` — the prose
    counterpart to the glance-level name from
    :func:`get_species_corpse_name`.  The result drifts with the corpse's
    decay stage: fresh / early embed the death-time physical description
    (``base_desc``); moderate onward describe the decay state generically
    as the original features deteriorate.

    **Unknown-species fallback (issue #215):** unknown / ``None`` species
    drop the species token entirely — an alien corpse reads "A recently
    deceased body." rather than misclaiming itself as human.  Known
    species surface their token at every tier (e.g. "Decomposing human
    remains").  This mirrors the token-drop contract of
    :func:`get_species_organ_name`.

    This helper is pure: it composes and returns a string with no I/O or
    state mutation, preserving the corpse pure-look contract (issue
    #230).

    Args:
        species: Species identifier; ``None`` or unregistered species
            drop the species token from every template.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  ``None`` or unknown stages fall
            back to the ``fresh`` template.
        base_desc: The death-time physical description, embedded in the
            fresh / early templates.  Defaults to a neutral placeholder.

    Returns:
        Description paragraph ready to slot into ``return_appearance``.
    """
    # Issue #215: detect unknown species before the human-default
    # fallback so an unregistered species renders with an empty species
    # token rather than claiming "human".
    is_known = bool(species) and species in SPECIES_DEFINITIONS
    spec = SPECIES_DEFINITIONS[species] if is_known else SPECIES_DEFINITIONS["human"]
    descriptions = spec.get("decay_corpse_descriptions") or {}
    template = descriptions.get(decay_stage) or descriptions.get("fresh")
    if not template:
        return base_desc
    species_display = spec.get("display_name", "") if is_known else ""
    rendered = template.format(species=species_display, base_desc=base_desc)
    # Collapse any double spaces / leading whitespace left behind when
    # the species token is empty (template was "... {species} ...").
    return " ".join(rendered.split())


def get_species_organ_name(
    species: str | None,
    organ_name: str,
    decay_stage: str | None = None,
) -> str:
    """Return the decay-modulated display name for a harvested organ.

    Used by :class:`typeclasses.items.Organ` to render decay-aware
    glance names like ``"human heart"`` (fresh) → ``"rotting heart"``
    (moderate) → ``"desiccated heart"`` (skeletal).  The skeletal tier
    deliberately reads ``desiccated`` rather than ``skeletal`` — soft
    tissue dries out rather than skeletonizing.

    Mirrors the contract of :func:`get_species_part_name`: fresh/early
    surface species cleanly, moderate/advanced obscure it ("rotting"
    only), and the skeletal tier abandons species entirely.  Players
    wanting more precision must ``look`` (which shows condition-keyed
    prose) or use forensic commands.

    **Unknown-species fallback (issue #215):** unknown species drop the
    species token entirely — an organ from an unregistered species
    renders as bare ``"heart"`` rather than misclaiming it as human.
    This is a feature: builders creating something truly alien get
    inscrutable organ names for free.  Late-decay tiers already drop
    species via their templates, so this only changes the
    fresh / early surface for unregistered species.

    Args:
        species: Species identifier; ``None`` or unregistered species
            drop the species token from the fresh / early template.
        organ_name: Canonical organ identifier from
            :data:`world.medical.constants.ORGANS`.  Unregistered
            organs fall back to their underscore-stripped key.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  ``None`` or unknown stages
            fall back to the ``fresh`` template.

    Returns:
        Display string ready for use as ``self.key`` or in look output.
    """
    from .organs import get_organ_display_name

    # Issue #215: detect unknown species before falling through to the
    # ``_resolve_species`` human-default behaviour.  Unknown species
    # use the human template shape (so decay tiers still work) but
    # render with an empty species token, producing bare organ names
    # at fresh / early stages.
    is_known = bool(species) and species in SPECIES_DEFINITIONS
    spec = SPECIES_DEFINITIONS[species] if is_known else SPECIES_DEFINITIONS["human"]
    prefixes = spec.get("decay_organ_prefixes") or {}
    template = (
        prefixes.get(decay_stage)
        or prefixes.get("fresh")
        or "{organ}"
    )
    organ_display = get_organ_display_name(organ_name)
    species_display = spec.get("display_name", "") if is_known else ""
    rendered = template.format(species=species_display, organ=organ_display)
    # Collapse any leading whitespace left behind when species_display
    # is empty (template was ``"{species} {organ}"``).
    return " ".join(rendered.split())
