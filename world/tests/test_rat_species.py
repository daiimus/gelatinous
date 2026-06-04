"""Tests for the rat species (issue #356 Phase 4).

End-to-end check that the rat species data is wired correctly across
every species-aware helper.  Phases 1-3 made the architecture species-
keyed; this PR ships the actual rat data plus severed-part prose.

Coverage:

* Rat declares every required species table (organs, severability,
  display, decay, severed-part prose).
* Each species helper returns rat-specific data, not human-defaults.
* A MedicalState constructed for a rat character has rat organs and
  no humanoid organs.
* Severance helpers route through rat anatomy: severing a foreleg
  takes the forepaw via the chain; tail is severable and stands
  alone; head cluster uses snout/fur.
* Rat severed-part prose is wired across all rat severable locations.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.anatomy import (
    get_organ_spec,
    get_severed_part_description,
    get_species_anatomical_display_order,
    get_species_anatomical_regions,
    get_species_corpse_description,
    get_species_corpse_name,
    get_species_default_longdesc_locations,
    get_species_limb_downstream_chain,
    get_species_limb_parent,
    get_species_organs,
    get_species_pair_keys,
    get_species_part_name,
    get_species_severable_containers,
    get_species_sever_hand_by_container,
    get_species_severed_head_locations,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical.core import MedicalState


class RatSpeciesDeclared(TestCase):

    def test_rat_in_registry(self):
        self.assertIn("rat", SPECIES_DEFINITIONS)

    def test_rat_has_all_required_tables(self):
        rat = SPECIES_DEFINITIONS["rat"]
        for field in (
            "display_name", "location_display", "severed_chain_display",
            "decay_part_prefixes", "decay_organ_prefixes",
            "decay_corpse_names", "decay_corpse_descriptions",
            "pair_keys", "organs",
            "severable_containers", "severed_head_locations",
            "sever_hand_by_container", "limb_downstream_chain",
            "limb_parent",
            "anatomical_display_order", "anatomical_regions",
            "default_longdesc_locations",
        ):
            with self.subTest(field=field):
                self.assertIn(field, rat)


class RatOrgansDistinctFromHuman(TestCase):

    def test_rat_organs_includes_tail_vertebrae(self):
        organs = get_species_organs("rat")
        self.assertIn("tail_vertebrae", organs)
        self.assertEqual(organs["tail_vertebrae"]["container"], "tail")

    def test_rat_organs_use_foreleg_hindleg_containers(self):
        organs = get_species_organs("rat")
        # Rat-specific skeletal organs.
        self.assertIn("left_foreleg_bone", organs)
        self.assertEqual(
            organs["left_foreleg_bone"]["container"], "left_foreleg",
        )
        self.assertIn("left_hindleg_bone", organs)

    def test_rat_does_not_inherit_humanoid_arm_leg_bones(self):
        organs = get_species_organs("rat")
        self.assertNotIn("left_humerus", organs)
        self.assertNotIn("left_femur", organs)
        self.assertNotIn("left_tibia", organs)
        self.assertNotIn("left_metatarsals", organs)

    def test_shared_mammalian_organs_present(self):
        # Brain, heart, lungs, liver, etc. are the same identifier
        # across species (mammalian universals).
        organs = get_species_organs("rat")
        for name in ("brain", "heart", "left_lung", "liver",
                     "left_kidney", "stomach", "cervical_spine"):
            with self.subTest(name=name):
                self.assertIn(name, organs)

    def test_organ_spec_routes_to_species(self):
        # left_foreleg_bone is a rat-only organ; human lookup
        # returns empty.
        self.assertEqual(get_organ_spec("left_foreleg_bone", "human"), {})
        rat_spec = get_organ_spec("left_foreleg_bone", "rat")
        self.assertEqual(rat_spec["container"], "left_foreleg")


class RatSeverabilityDistinct(TestCase):

    def test_severable_includes_tail(self):
        self.assertIn("tail", get_species_severable_containers("rat"))

    def test_severable_excludes_human_arm_thigh(self):
        containers = get_species_severable_containers("rat")
        for human_only in ("left_arm", "left_hand",
                           "left_thigh", "left_shin", "left_foot"):
            with self.subTest(loc=human_only):
                self.assertNotIn(human_only, containers)

    def test_head_cluster_uses_snout_and_fur(self):
        cluster = get_species_severed_head_locations("rat")
        self.assertIn("snout", cluster)
        self.assertIn("fur", cluster)
        self.assertNotIn("face", cluster)
        self.assertNotIn("hair", cluster)

    def test_rats_dont_wield(self):
        self.assertEqual(get_species_sever_hand_by_container("rat"), {})

    def test_foreleg_chain_takes_forepaw(self):
        chain = get_species_limb_downstream_chain("rat")
        self.assertEqual(
            chain["left_foreleg"], ("left_foreleg", "left_forepaw"),
        )

    def test_tail_chain_is_single_segment(self):
        chain = get_species_limb_downstream_chain("rat")
        self.assertEqual(chain["tail"], ("tail",))

    def test_no_three_segment_chain(self):
        chain = get_species_limb_downstream_chain("rat")
        for tup in chain.values():
            self.assertLessEqual(
                len(tup), 2,
                f"rat chain should not exceed two segments: {tup}",
            )

    def test_limb_parent_maps_paws_to_legs(self):
        parents = get_species_limb_parent("rat")
        self.assertEqual(parents["left_forepaw"], "left_foreleg")
        self.assertEqual(parents["left_hindpaw"], "left_hindleg")


class RatDisplayDistinct(TestCase):

    def test_display_order_ends_with_tail(self):
        order = get_species_anatomical_display_order("rat")
        self.assertEqual(order[-1], "tail")

    def test_display_order_uses_snout_not_face(self):
        order = get_species_anatomical_display_order("rat")
        self.assertIn("snout", order)
        self.assertNotIn("face", order)

    def test_regions_have_foreleg_hindleg_tail(self):
        regions = get_species_anatomical_regions("rat")
        self.assertIn("foreleg_region", regions)
        self.assertIn("hindleg_region", regions)
        self.assertIn("tail_region", regions)
        self.assertNotIn("arm_region", regions)

    def test_default_longdesc_has_tail(self):
        defaults = get_species_default_longdesc_locations("rat")
        self.assertIn("tail", defaults)
        self.assertIn("snout", defaults)
        self.assertNotIn("left_arm", defaults)


class RatPairKeysDistinct(TestCase):

    def test_pair_keys_use_foreleg_hindleg(self):
        pairs = get_species_pair_keys("rat")
        self.assertIn("forelegs", pairs)
        self.assertIn("hindlegs", pairs)
        self.assertEqual(
            pairs["forelegs"], ("left_foreleg", "right_foreleg"),
        )

    def test_pair_keys_exclude_arms_thighs(self):
        pairs = get_species_pair_keys("rat")
        self.assertNotIn("arms", pairs)
        self.assertNotIn("thighs", pairs)


class RatDecayNaming(TestCase):

    def test_corpse_name_says_carcass(self):
        # Rats die into a "carcass", not a "corpse".
        self.assertEqual(
            get_species_corpse_name("rat", "fresh"), "rat carcass",
        )

    def test_corpse_description_mentions_fur(self):
        out = get_species_corpse_description("rat", "fresh", "A small body.")
        self.assertIn("fur", out.lower())

    def test_severed_part_name_uses_rat_prefix(self):
        # Fresh severed rat foreleg reads as "rat left foreleg".
        out = get_species_part_name("rat", "left_foreleg", "fresh")
        self.assertEqual(out, "rat left foreleg")


class RatSeveredPartProse(TestCase):

    def test_all_rat_severable_locations_have_prose(self):
        # Every rat severable container should have severed-part
        # prose at all three condition tiers.  Falls through to human
        # is wrong here — rat-specific entries should exist.
        from world.anatomy import get_species_severable_containers
        rat_severable = get_species_severable_containers("rat")
        # Sever-into-Appendage targets the cut point; for the head
        # bundle, that's "head" itself, so the relevant location set
        # equals the severable containers.
        for loc in rat_severable:
            for condition in ("pristine", "damaged", "putrid"):
                with self.subTest(loc=loc, condition=condition):
                    out = get_severed_part_description("rat", loc, condition)
                    self.assertTrue(
                        out, f"missing rat prose at {loc}/{condition}",
                    )

    def test_rat_head_prose_mentions_snout(self):
        out = get_severed_part_description("rat", "head", "pristine")
        self.assertIn("snout", out.lower())

    def test_rat_tail_prose_mentions_rings(self):
        out = get_severed_part_description("rat", "tail", "pristine")
        self.assertIn("ring", out.lower())


# ---------------------------------------------------------------------
# End-to-end: a rat character's medical state
# ---------------------------------------------------------------------


class _RatCharacter:
    """Minimal rat-character stub for MedicalState init."""

    def __init__(self):
        self.db = SimpleNamespace(species="rat")


class MedicalStateForRat(TestCase):

    def test_rat_medical_state_has_rat_organs(self):
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        for must in ("brain", "heart", "tail_vertebrae",
                     "left_foreleg_bone", "left_hindleg_bone"):
            with self.subTest(must=must):
                self.assertIn(must, state.organs)

    def test_rat_medical_state_has_no_humanoid_organs(self):
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        for must_not in ("left_humerus", "left_femur", "left_tibia",
                         "left_metacarpals", "left_metatarsals"):
            with self.subTest(must_not=must_not):
                self.assertNotIn(must_not, state.organs)

    def test_rat_organs_routes_to_rat_containers(self):
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        self.assertEqual(
            state.organs["left_foreleg_bone"].container, "left_foreleg",
        )
        self.assertEqual(
            state.organs["tail_vertebrae"].container, "tail",
        )
