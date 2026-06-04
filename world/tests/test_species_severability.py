"""Tests for the species-keyed severability tables (issue #356 Phase 2).

PR-A (#350) moved ``PAIR_MERGE_KEYS`` into the species registry; Phase 1
(#356) moved ``ORGANS``.  Phase 2 completes the severance side:
``SEVERABLE_CONTAINERS``, ``SEVERED_HEAD_LOCATIONS``,
``SEVER_HAND_BY_CONTAINER``, ``LIMB_DOWNSTREAM_CHAIN``, ``LIMB_PARENT``
are now species-keyed.  Legacy globals derive from the human entry.

Tests verify:

* Each helper returns the right table per species, falls back to
  human on unknown, returns fresh data (no aliasing).
* Legacy globals match the human entries (single source of truth).
* An ad-hoc rat-stub species with two-segment fore/hindlimb chains
  produces a different chain shape than human's.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    get_species_limb_downstream_chain,
    get_species_limb_parent,
    get_species_severable_containers,
    get_species_sever_hand_by_container,
    get_species_severed_head_locations,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.combat.constants import (
    LIMB_DOWNSTREAM_CHAIN,
    LIMB_PARENT,
    SEVER_HAND_BY_CONTAINER,
    SEVERABLE_CONTAINERS,
    SEVERED_HEAD_LOCATIONS,
)


class HumanTablesMatchLegacyGlobals(TestCase):

    def test_severable_containers_matches(self):
        self.assertEqual(
            get_species_severable_containers("human"),
            SEVERABLE_CONTAINERS,
        )

    def test_severed_head_locations_matches(self):
        self.assertEqual(
            get_species_severed_head_locations("human"),
            SEVERED_HEAD_LOCATIONS,
        )

    def test_sever_hand_by_container_matches(self):
        self.assertEqual(
            get_species_sever_hand_by_container("human"),
            SEVER_HAND_BY_CONTAINER,
        )

    def test_limb_downstream_chain_matches(self):
        self.assertEqual(
            get_species_limb_downstream_chain("human"),
            LIMB_DOWNSTREAM_CHAIN,
        )

    def test_limb_parent_matches(self):
        self.assertEqual(
            get_species_limb_parent("human"),
            LIMB_PARENT,
        )


class FallbackToHumanOnUnknown(TestCase):

    def test_unknown_species_severable_containers_human(self):
        self.assertEqual(
            get_species_severable_containers("alien_xyz"),
            get_species_severable_containers("human"),
        )

    def test_none_species_falls_back(self):
        self.assertEqual(
            get_species_limb_downstream_chain(None),
            get_species_limb_downstream_chain("human"),
        )


class NoAliasingOnReturnedData(TestCase):

    def test_chain_mutation_does_not_corrupt_registry(self):
        chain = get_species_limb_downstream_chain("human")
        chain["test_limb"] = ("test_limb",)
        self.assertNotIn(
            "test_limb",
            get_species_limb_downstream_chain("human"),
        )

    def test_sever_hand_mutation_isolated(self):
        hand_map = get_species_sever_hand_by_container("human")
        hand_map["test_arm"] = "left"
        self.assertNotIn(
            "test_arm",
            get_species_sever_hand_by_container("human"),
        )


class AdHocRatStubProducesDifferentTables(TestCase):
    """Smoke test for non-human species variation: a rat declares
    two-segment fore/hindlimb chains and no humanoid arm/leg
    structures.  Verifies the helpers route to the species, not the
    human default."""

    def setUp(self):
        SPECIES_DEFINITIONS["_test_rat"] = {
            "display_name": "test rat",
            "location_display": {},
            "decay_part_prefixes": {},
            "decay_organ_prefixes": {},
            "decay_corpse_names": {},
            "decay_corpse_descriptions": {},
            "pair_keys": {
                "forelegs": ("left_foreleg", "right_foreleg"),
                "hindlegs": ("left_hindleg", "right_hindleg"),
            },
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
            "sever_hand_by_container": {},  # rats don't wield items
            "limb_downstream_chain": {
                "left_foreleg":  ("left_foreleg", "left_forepaw"),
                "right_foreleg": ("right_foreleg", "right_forepaw"),
                "left_forepaw":  ("left_forepaw",),
                "right_forepaw": ("right_forepaw",),
                "left_hindleg":  ("left_hindleg", "left_hindpaw"),
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
        }

    def tearDown(self):
        del SPECIES_DEFINITIONS["_test_rat"]

    def test_rat_severable_includes_tail(self):
        containers = get_species_severable_containers("_test_rat")
        self.assertIn("tail", containers)
        # And does NOT include human-only arm/leg names.
        self.assertNotIn("left_arm", containers)
        self.assertNotIn("left_thigh", containers)

    def test_rat_head_cluster_uses_snout_not_face(self):
        cluster = get_species_severed_head_locations("_test_rat")
        self.assertIn("snout", cluster)
        self.assertIn("fur", cluster)
        self.assertNotIn("face", cluster)
        self.assertNotIn("hair", cluster)

    def test_rat_no_wielding_hand_map(self):
        # Rats can't wield items; map is empty.
        self.assertEqual(
            get_species_sever_hand_by_container("_test_rat"), {}
        )

    def test_rat_chain_is_two_segment(self):
        chain = get_species_limb_downstream_chain("_test_rat")
        # Rats have a single forelimb chain step (no thigh→shin→foot).
        self.assertEqual(chain["left_foreleg"], ("left_foreleg", "left_forepaw"))
        self.assertEqual(chain["left_hindleg"], ("left_hindleg", "left_hindpaw"))
        # Tail severs as a single segment.
        self.assertEqual(chain["tail"], ("tail",))
        # And human entries are NOT inherited.
        self.assertNotIn("left_arm", chain)
        self.assertNotIn("left_thigh", chain)
