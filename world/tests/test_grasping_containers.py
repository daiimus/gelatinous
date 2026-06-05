"""Tests for ``grasping_containers`` anatomy markup (#307, PR-H1).

The ``grasping_containers`` frozenset declares which container
locations can wield items.  Generalised beyond the literal "hand"
concept from day one so prehensile tails, grasping feet, and
multi-armed anatomies can declare their own without renaming the
concept.

Accessor: :func:`world.anatomy.get_species_grasping_containers`.

This is PR-H1 of the Mr. Hands restructure — pure data + lookup.
PR-H2 will make ``character.hands`` a derived view that walks this
set against the current severance state.

Run via::

    evennia test world.tests.test_grasping_containers
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    SPECIES_DEFINITIONS,
    get_species_grasping_containers,
)


class HumanGraspingContainers(TestCase):
    """Humans grasp with left_hand and right_hand."""

    def test_left_hand_is_grasping(self):
        grasping = get_species_grasping_containers("human")
        self.assertIn("left_hand", grasping)

    def test_right_hand_is_grasping(self):
        grasping = get_species_grasping_containers("human")
        self.assertIn("right_hand", grasping)

    def test_exactly_two_grasping_containers(self):
        grasping = get_species_grasping_containers("human")
        self.assertEqual(grasping, frozenset({"left_hand", "right_hand"}))

    def test_feet_not_grasping(self):
        grasping = get_species_grasping_containers("human")
        for foot in ("left_foot", "right_foot"):
            with self.subTest(foot=foot):
                self.assertNotIn(foot, grasping)

    def test_torso_not_grasping(self):
        grasping = get_species_grasping_containers("human")
        for torso in ("head", "chest", "abdomen", "back", "neck"):
            with self.subTest(loc=torso):
                self.assertNotIn(torso, grasping)


class RatGraspingContainers(TestCase):
    """Rats have no grasping appendages — empty set."""

    def test_rat_grasps_nothing(self):
        grasping = get_species_grasping_containers("rat")
        self.assertEqual(grasping, frozenset())

    def test_forepaws_not_grasping(self):
        """Rodent forepaws can manipulate but the system doesn't
        model them as wielding slots."""
        grasping = get_species_grasping_containers("rat")
        for paw in ("left_forepaw", "right_forepaw"):
            with self.subTest(paw=paw):
                self.assertNotIn(paw, grasping)


class SpeciesFallback(TestCase):
    """None / unknown species fall back to human, per the existing
    accessor convention."""

    def test_none_species_falls_back_to_human(self):
        grasping = get_species_grasping_containers(None)
        self.assertEqual(grasping, frozenset({"left_hand", "right_hand"}))

    def test_unknown_species_falls_back_to_human(self):
        grasping = get_species_grasping_containers("nonexistent_species")
        self.assertEqual(
            grasping, frozenset({"left_hand", "right_hand"})
        )

    def test_empty_string_falls_back_to_human(self):
        grasping = get_species_grasping_containers("")
        self.assertEqual(
            grasping, frozenset({"left_hand", "right_hand"})
        )


class ReturnType(TestCase):
    """Pinning the return type so consumers can rely on set semantics
    (membership, union, intersection)."""

    def test_returns_frozenset(self):
        grasping = get_species_grasping_containers("human")
        self.assertIsInstance(grasping, frozenset)

    def test_empty_species_returns_frozenset(self):
        """Empty result is still a frozenset, not None / set / list."""
        grasping = get_species_grasping_containers("rat")
        self.assertIsInstance(grasping, frozenset)


class GraspingIsSubsetOfSeverable(TestCase):
    """Sanity contract: grasping appendages should always be a
    subset of severable containers — anything that can hold an item
    is something a character has, and anything they have can in
    principle be lost.  Pins the modelling assumption so future
    species additions catch divergence in CI."""

    def test_human_grasping_subset_of_severable(self):
        from world.anatomy import get_species_severable_containers
        grasping = get_species_grasping_containers("human")
        severable = get_species_severable_containers("human")
        self.assertTrue(
            grasping <= severable,
            f"grasping {grasping} not a subset of severable {severable}",
        )

    def test_rat_grasping_subset_of_severable(self):
        from world.anatomy import get_species_severable_containers
        grasping = get_species_grasping_containers("rat")
        severable = get_species_severable_containers("rat")
        self.assertTrue(grasping <= severable)


class SpeciesDefinitionsShape(TestCase):
    """Pin the on-disk data shape so consumers can reach into
    SPECIES_DEFINITIONS directly when needed and the accessor stays
    in sync with the raw table."""

    def test_human_definition_has_grasping_containers(self):
        self.assertIn(
            "grasping_containers", SPECIES_DEFINITIONS["human"]
        )

    def test_rat_definition_has_grasping_containers(self):
        self.assertIn(
            "grasping_containers", SPECIES_DEFINITIONS["rat"]
        )

    def test_raw_human_value_matches_accessor(self):
        raw = SPECIES_DEFINITIONS["human"]["grasping_containers"]
        self.assertEqual(
            frozenset(raw), get_species_grasping_containers("human")
        )
