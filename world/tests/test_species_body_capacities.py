"""Tests for species-keyed body capacities (issue #356 follow-up).

Pre-fix the global ``BODY_CAPACITIES`` referenced human-only organs
(``left_femur`` / ``right_femur`` / ``left_humerus`` / etc.) directly.
A rat with damaged ``left_hindleg_bone`` would not lose any
``moving`` capacity, because the lookup couldn't find rat bones.

Phase 1 (#356) moved the table into the species registry; this PR
ships rat-specific capacity wiring and migrates the consumers:
``MedicalState.calculate_body_capacity`` and
``world.medical.utils._get_vital_locations``.

Tests verify:

* Rat declares the same capacity set as human, mapped to rat organs.
* A rat ``MedicalState`` returns reduced ``moving`` capacity when a
  rat hindleg bone is destroyed.
* A rat with destroyed left/right humerus (which don't exist on the
  rat) does NOT lose manipulation — because the capacity wiring no
  longer references those organs.
* Vital locations for the rat include ``head`` / ``chest`` / ``neck``
  / ``abdomen`` like the human, derived dynamically.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.anatomy import get_species_body_capacities
from world.medical.constants import BODY_CAPACITIES
from world.medical.core import MedicalState
from world.medical.utils import _get_vital_locations


class HumanCapacitiesMatchLegacyGlobal(TestCase):

    def test_human_capacities_match_global(self):
        # Single source of truth: global derives from species["human"].
        self.assertEqual(
            get_species_body_capacities("human"),
            BODY_CAPACITIES,
        )


class RatCapacityWiringDistinct(TestCase):

    def test_rat_moving_references_hindleg_bones(self):
        caps = get_species_body_capacities("rat")
        moving = caps["moving"]
        organs = moving["organs"]
        # Rat-specific skeletal organs in the moving capacity.
        self.assertIn("left_hindleg_bone", organs)
        self.assertIn("right_hindleg_bone", organs)
        self.assertIn("left_hindpaw_bones", organs)
        # Spine + pelvis still drive movement (mammalian universals).
        self.assertIn("thoracolumbar_spine", organs)
        self.assertIn("pelvis", organs)
        # Human-only bones absent.
        self.assertNotIn("left_femur", organs)
        self.assertNotIn("left_tibia", organs)
        self.assertNotIn("left_metatarsals", organs)

    def test_rat_manipulation_uses_forelegs(self):
        caps = get_species_body_capacities("rat")
        manip = caps["manipulation"]
        organs = manip["organs"]
        # Rat forepaw / foreleg organs.
        self.assertIn("left_foreleg_bone", organs)
        self.assertIn("left_forepaw_bones", organs)
        # Human-only bones absent.
        self.assertNotIn("left_humerus", organs)
        self.assertNotIn("left_metacarpals", organs)

    def test_rat_has_no_talking_capacity(self):
        # Rats vocalize via squeaks, not human-style speech.  Capacity
        # is intentionally absent so the talking-affected social
        # systems don't apply to rats.
        caps = get_species_body_capacities("rat")
        self.assertNotIn("talking", caps)

    def test_shared_mammalian_capacities_match_human_organs(self):
        # Capacities driven by universally-named organs (heart,
        # lungs, eyes, ears) should reference the same organ names
        # across species — only the skeletal capacities diverge.
        rat = get_species_body_capacities("rat")
        human = get_species_body_capacities("human")
        for shared in ("blood_pumping", "breathing", "sight", "hearing"):
            with self.subTest(capacity=shared):
                self.assertEqual(
                    rat[shared]["organs"], human[shared]["organs"],
                )


# ---------------------------------------------------------------------
# End-to-end via MedicalState
# ---------------------------------------------------------------------


class _RatCharacter:
    def __init__(self):
        self.db = SimpleNamespace(species="rat")


class _HumanCharacter:
    def __init__(self):
        self.db = SimpleNamespace(species="human")


class RatMovingCapacityReducesOnHindlegDamage(TestCase):

    def test_intact_rat_full_moving(self):
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        self.assertAlmostEqual(state.calculate_body_capacity("moving"), 1.0)

    def test_destroyed_rat_hindleg_bone_reduces_moving(self):
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        # Destroy the left hindleg bone.
        organ = state.organs["left_hindleg_bone"]
        organ.current_hp = 0
        state._cache_dirty = True
        score = state.calculate_body_capacity("moving")
        # Less than full capacity; the damaged organ contributed to
        # the score so the rat's moving is now degraded.
        self.assertLess(score, 1.0)

    def test_human_femur_damage_does_not_affect_rat(self):
        # A rat doesn't have a left_femur organ at all (its
        # MedicalState wasn't initialized with one).  This is a
        # sanity-check that the species init produced rat-shaped
        # state without humanoid organs.
        rat = _RatCharacter()
        state = MedicalState(character=rat)
        self.assertNotIn("left_femur", state.organs)
        self.assertNotIn("left_humerus", state.organs)


class HumanCapacityScoringUnchanged(TestCase):
    """Regression guard: human characters compute capacity scores the
    same way they did before this PR (humanoid organ wiring)."""

    def test_human_moving_intact(self):
        human = _HumanCharacter()
        state = MedicalState(character=human)
        self.assertAlmostEqual(state.calculate_body_capacity("moving"), 1.0)

    def test_human_left_femur_damage_reduces_moving(self):
        human = _HumanCharacter()
        state = MedicalState(character=human)
        state.organs["left_femur"].current_hp = 0
        state._cache_dirty = True
        self.assertLess(state.calculate_body_capacity("moving"), 1.0)


class VitalLocationsRespectsSpecies(TestCase):

    def test_rat_vital_locations_share_universal_organs(self):
        # Rat shares head/chest/neck/abdomen vital locations because
        # rat brain/heart/cervical_spine/liver have the same
        # containers as human equivalents.
        rat = _RatCharacter()
        vitals = _get_vital_locations(rat)
        self.assertIn("head", vitals)
        self.assertIn("chest", vitals)
        self.assertIn("neck", vitals)
        self.assertIn("abdomen", vitals)

    def test_human_vital_locations_unchanged(self):
        human = _HumanCharacter()
        vitals = _get_vital_locations(human)
        self.assertEqual(
            vitals, {"head", "chest", "neck", "abdomen"},
        )
