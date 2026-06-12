"""Phase 1 test contract for ANATOMY_AUGMENTS_SPEC (issue #511).

Pins the per-character anatomy substrate:

* equivalence — for a default human, body-driven location→organ
  resolution matches the static-table answers exactly;
* the rat fix — a hit at a rat's tail resolves the rat's tail
  organs and applies damage (previously a silent no-op against
  the human table);
* spec round-trip — an organ whose spec is NOT in any species
  table (an augment) survives ``to_dict``/``from_dict`` with
  container, hit weight, and flags intact;
* legacy fallback — snapshots predating the spec field still
  restore via the species-table lookup.

Run via::

    evennia test --settings settings.py world.tests.test_anatomy_substrate
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.core import MedicalState, Organ
from world.medical.utils import (
    calculate_hit_weights_for_location,
    distribute_damage_to_organs,
    get_organ_by_body_location,
    select_target_organ,
)


def _human_state():
    return MedicalState(character=None)


def _rat_state():
    rat = SimpleNamespace(db=SimpleNamespace(species="rat"), key="test-rat")
    return MedicalState(character=rat)


# A spec no species table carries — the augment shape (the
# cybernetic tail's organ, in miniature).
AUGMENT_SPEC = {
    "container": "tail",
    "max_hp": 20,
    "hit_weight": "common",
    "severable_container": True,
    "grasping": True,
}


class TestHumanEquivalence(TestCase):
    """Body-driven resolution must not change human combat at all."""

    def test_organ_resolution_matches_static_table(self):
        state = _human_state()
        locations = {o.container for o in state.organs.values()}
        for location in locations:
            self.assertEqual(
                sorted(get_organ_by_body_location(location, state)),
                sorted(get_organ_by_body_location(location)),
                f"divergence at {location}",
            )

    def test_hit_weights_match_static_table(self):
        state = _human_state()
        locations = {o.container for o in state.organs.values()}
        for location in locations:
            self.assertEqual(
                calculate_hit_weights_for_location(location, state),
                calculate_hit_weights_for_location(location),
                f"divergence at {location}",
            )


class TestRatResolution(TestCase):
    """The pre-existing species bug, pinned: rats resolve from their
    own body, not the human table."""

    def test_rat_tail_resolves_rat_organs(self):
        state = _rat_state()
        self.assertEqual(
            get_organ_by_body_location("tail", state), ["tail_vertebrae"]
        )
        # The bug being fixed: the static human table has no tail.
        self.assertEqual(get_organ_by_body_location("tail"), [])

    def test_rat_tail_takes_damage(self):
        state = _rat_state()
        distribution = distribute_damage_to_organs("tail", 4, state)
        self.assertEqual(distribution, {"tail_vertebrae": 4})

    def test_rat_tail_organ_targetable(self):
        state = _rat_state()
        organ = select_target_organ(
            "tail", precision_roll=10, attacker_skill=5, medical_state=state
        )
        self.assertEqual(organ, "tail_vertebrae")


class TestAugmentResolution(TestCase):
    """An organ added beyond the species table is hittable — the
    substrate guarantee the cybernetic tail rides on."""

    def _human_with_tail(self):
        state = _human_state()
        organ = Organ("cybernetic_tail", organ_data=dict(AUGMENT_SPEC))
        organ.medical_state = state
        state.organs["cybernetic_tail"] = organ
        return state

    def test_augment_organ_resolves_at_its_container(self):
        state = self._human_with_tail()
        self.assertEqual(
            get_organ_by_body_location("tail", state), ["cybernetic_tail"]
        )

    def test_augment_organ_takes_damage(self):
        state = self._human_with_tail()
        distribution = distribute_damage_to_organs("tail", 6, state)
        self.assertEqual(distribution, {"cybernetic_tail": 6})

    def test_human_locations_unaffected_by_augment(self):
        state = self._human_with_tail()
        self.assertEqual(
            sorted(get_organ_by_body_location("chest", state)),
            sorted(get_organ_by_body_location("chest")),
        )


class TestOrganSpecRoundTrip(TestCase):
    def test_augment_spec_survives_persistence(self):
        organ = Organ("cybernetic_tail", organ_data=dict(AUGMENT_SPEC))
        organ.current_hp = 12
        restored = Organ.from_dict(organ.to_dict())
        self.assertEqual(restored.container, "tail")
        self.assertEqual(restored.hit_weight, "common")
        self.assertEqual(restored.max_hp, 20)
        self.assertEqual(restored.current_hp, 12)
        self.assertTrue(restored.data.get("grasping"))
        self.assertTrue(restored.data.get("severable_container"))

    def test_species_organ_spec_round_trips(self):
        """Every organ carries its spec now — a rat organ restored
        outside its species context keeps the right container
        (previously this looked up the HUMAN table and got
        'unknown')."""
        rat_state = _rat_state()
        organ = rat_state.organs["tail_vertebrae"]
        restored = Organ.from_dict(organ.to_dict())
        self.assertEqual(restored.container, "tail")

    def test_legacy_snapshot_falls_back_to_species_table(self):
        organ = Organ("left_humerus")
        data = organ.to_dict()
        del data["data"]
        restored = Organ.from_dict(data)
        self.assertEqual(restored.container, "left_arm")

    def test_full_state_round_trip_with_augment(self):
        state = _human_state()
        augment = Organ("cybernetic_tail", organ_data=dict(AUGMENT_SPEC))
        augment.medical_state = state
        state.organs["cybernetic_tail"] = augment
        restored = MedicalState.from_dict(state.to_dict())
        self.assertIn("cybernetic_tail", restored.organs)
        self.assertEqual(restored.organs["cybernetic_tail"].container, "tail")
        self.assertEqual(
            get_organ_by_body_location("tail", restored), ["cybernetic_tail"]
        )
