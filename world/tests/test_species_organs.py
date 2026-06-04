"""Tests for the species-keyed organ table (issue #356 Phase 1).

The historical global ``world.medical.constants.ORGANS`` constant
moved into ``SPECIES_DEFINITIONS[species]["organs"]`` so non-humans
can declare their own anatomy.  The legacy global is now a derived
alias of the human table, preserving every existing caller.

Tests verify:

* The human species declares the canonical organ table.
* ``get_species_organs`` returns the right table per species, falls
  back to human on unknown, returns a fresh dict (no aliasing).
* ``get_organ_spec(name, species)`` is a thin convenience wrapper.
* The legacy global ``ORGANS`` constant matches the human table —
  single source of truth.
* ``Organ(name, species=species)`` looks up against the species
  table.
* ``MedicalState._initialize_default_organs`` consults the owning
  character's species.
* An ad-hoc rat-stub species declaring its own minimal organ set
  produces a rat-shaped medical state (no humanoid organ leakage).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.anatomy import get_organ_spec, get_species_organs
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical.constants import ORGANS
from world.medical.core import MedicalState, Organ


class HumanOrganTableShape(TestCase):

    def test_human_declares_organs(self):
        organs = get_species_organs("human")
        # Spot-check organs we know must exist.
        for must in ("brain", "heart", "left_eye", "right_eye",
                     "left_humerus", "left_femur", "pelvis"):
            with self.subTest(must=must):
                self.assertIn(must, organs)

    def test_left_eye_routes_to_eye_surface(self):
        # The display_location override added in #346 lives in the
        # species data, not in some patch on the global constant.
        spec = get_organ_spec("left_eye", species="human")
        self.assertEqual(spec.get("display_location"), "left_eye")

    def test_heart_default_container(self):
        spec = get_organ_spec("heart", species="human")
        self.assertEqual(spec.get("container"), "chest")


class GetSpeciesOrgansHelper(TestCase):

    def test_unknown_species_falls_back_to_human(self):
        unknown = get_species_organs("alien_xenoform_qrz")
        human = get_species_organs("human")
        self.assertEqual(unknown, human)

    def test_none_species_falls_back_to_human(self):
        self.assertEqual(get_species_organs(None),
                         get_species_organs("human"))

    def test_returns_fresh_dict_no_aliasing(self):
        organs = get_species_organs("human")
        organs["test_organ"] = {"container": "test"}
        organs2 = get_species_organs("human")
        self.assertNotIn("test_organ", organs2)


class GetOrganSpecHelper(TestCase):

    def test_unknown_organ_returns_empty_dict(self):
        # Mirrors the historical ``ORGANS.get(name, {})`` behavior.
        self.assertEqual(get_organ_spec("nonexistent_organ"), {})

    def test_known_human_organ(self):
        spec = get_organ_spec("heart", species="human")
        self.assertEqual(spec.get("container"), "chest")
        self.assertTrue(spec.get("vital"))

    def test_default_species_is_human(self):
        # Backwards-compat: legacy ``get_organ_spec(name)`` without
        # a species argument resolves against the human table.
        self.assertEqual(
            get_organ_spec("brain"),
            get_organ_spec("brain", species="human"),
        )


class LegacyOrgansAliasMatchesHuman(TestCase):

    def test_global_organs_matches_human_table(self):
        # Single source of truth: the global derives from the human
        # entry of the species registry.
        self.assertEqual(
            dict(ORGANS),
            dict(SPECIES_DEFINITIONS["human"]["organs"]),
        )


class OrganLookupRespectsSpecies(TestCase):

    def test_organ_init_uses_species(self):
        # Construct a left_humerus organ explicitly as a human — it
        # should pick up the spec.
        organ = Organ("left_humerus", species="human")
        self.assertEqual(organ.container, "left_arm")
        self.assertEqual(organ.max_hp, 25)

    def test_organ_init_default_is_human(self):
        # No species → human (backwards compat).
        organ = Organ("heart")
        self.assertEqual(organ.container, "chest")

    def test_organ_init_unknown_species_falls_through(self):
        # An organ unknown to the species (because the species
        # doesn't declare it) constructs with empty spec.
        organ = Organ("rat_femur", species="human")
        self.assertEqual(organ.data, {})
        # max_hp falls through to the default-when-no-spec value.
        self.assertEqual(organ.max_hp, 10)


# ---------------------------------------------------------------------
# MedicalState species-aware initialization
# ---------------------------------------------------------------------


class _StubCharacter:
    def __init__(self, species=None):
        self.db = SimpleNamespace(species=species)


class MedicalStateRespectsSpecies(TestCase):

    def test_human_character_gets_human_organs(self):
        char = _StubCharacter(species="human")
        state = MedicalState(character=char)
        # Spot-check humanoid organs that humans declare.
        for must in ("brain", "heart", "left_humerus", "left_femur"):
            with self.subTest(must=must):
                self.assertIn(must, state.organs)

    def test_no_species_character_falls_back_to_human(self):
        char = _StubCharacter(species=None)
        state = MedicalState(character=char)
        self.assertIn("heart", state.organs)
        self.assertIn("left_humerus", state.organs)

    def test_rat_stub_isolates_organ_set(self):
        # Register an ad-hoc rat species declaring its own minimal
        # organ set; the medical state should pick up rat organs and
        # not contain any humanoid limb organs.
        SPECIES_DEFINITIONS["_test_rat"] = {
            "display_name": "test rat",
            "pair_keys": {},
            "location_display": {},
            "decay_part_prefixes": {},
            "decay_organ_prefixes": {},
            "decay_corpse_names": {},
            "decay_corpse_descriptions": {},
            "organs": {
                # Minimal rat anatomy — different bone names from human.
                "rat_brain": {"container": "head", "max_hp": 5},
                "rat_heart": {"container": "chest", "max_hp": 8, "vital": True},
                "rat_left_humerus": {"container": "left_foreleg", "max_hp": 8},
                "rat_tail_vertebrae": {"container": "tail", "max_hp": 4},
            },
        }
        try:
            char = _StubCharacter(species="_test_rat")
            state = MedicalState(character=char)
            # Has rat organs.
            self.assertIn("rat_brain", state.organs)
            self.assertIn("rat_tail_vertebrae", state.organs)
            # Does NOT inherit humanoid organs.
            self.assertNotIn("left_humerus", state.organs)
            self.assertNotIn("brain", state.organs)
            # Sanity: rat organs have rat-specific containers.
            self.assertEqual(
                state.organs["rat_tail_vertebrae"].container, "tail"
            )
        finally:
            del SPECIES_DEFINITIONS["_test_rat"]
