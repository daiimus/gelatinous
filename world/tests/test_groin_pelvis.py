"""Tests for the pelvis-in-groin container fix (issue #325).

Pre-fix the pelvis organ was housed in the ``abdomen`` container, leaving
``groin`` with zero organs. Combat hits that the engine routed to the
groin fell through ``distribute_damage_to_organs("groin", ...)``'s
empty-list path, ``apply_anatomical_damage`` never called
``take_organ_damage``, and the character took zero medical damage despite
the hit message firing.

Tests cover:

* The pelvis is registered in the groin container.
* ``get_organ_by_body_location("groin")`` includes the pelvis (the
  symptomatic empty-list case is gone).
* ``distribute_damage_to_organs("groin", ...)`` resolves to the pelvis
  on a stock anatomy character — actual organ damage is applied.
* ``_get_vital_locations`` is unchanged — pelvis belongs to ``moving``
  (not a lethal capacity), so groin does not become a vital location.
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.constants import LETHAL_CAPACITY_NAMES, ORGANS
from world.medical.utils import (
    _get_vital_locations,
    get_organ_by_body_location,
)


class TestPelvisContainer(TestCase):
    def test_pelvis_lives_in_groin(self):
        self.assertEqual(ORGANS["pelvis"]["container"], "groin")

    def test_groin_container_has_pelvis(self):
        organs = get_organ_by_body_location("groin")
        self.assertIn("pelvis", organs)

    def test_abdomen_container_no_longer_has_pelvis(self):
        organs = get_organ_by_body_location("abdomen")
        self.assertNotIn("pelvis", organs)


class TestGroinDamageFlow(TestCase):
    """``distribute_damage_to_organs("groin", ...)`` must now route to the
    pelvis instead of returning the symptomatic empty dict."""

    def _stock_medical_state(self):
        from world.medical.core import MedicalState
        return MedicalState(character=None)

    def test_distribute_damage_routes_to_pelvis(self):
        from world.medical.utils import distribute_damage_to_organs

        ms = self._stock_medical_state()
        distribution = distribute_damage_to_organs(
            "groin", 10, ms, injury_type="blunt",
        )
        self.assertIn("pelvis", distribution)
        self.assertGreater(distribution["pelvis"], 0)

    def test_distribute_damage_with_target_organ_pelvis(self):
        from world.medical.utils import distribute_damage_to_organs

        ms = self._stock_medical_state()
        distribution = distribute_damage_to_organs(
            "groin", 12, ms, injury_type="blunt",
            target_organ="pelvis",
        )
        self.assertEqual(distribution, {"pelvis": 12})


class TestVitalLocationsUnchanged(TestCase):
    """Moving the pelvis to the groin must not affect the vital set —
    pelvis is in ``moving``, not a lethal capacity."""

    def test_groin_not_in_vital_set(self):
        # Defensive: groin must not show up as a vital location just
        # because it now has an organ. Pelvis isn't in
        # LETHAL_CAPACITY_NAMES, so the container shouldn't either.
        vital = _get_vital_locations(None)
        self.assertNotIn("groin", vital)

    def test_pelvis_capacity_is_not_lethal(self):
        # Guard the assumption that justifies the container move — if
        # someone reclassifies "moving" as lethal in the future, the
        # vital-set behaviour will need re-review.
        self.assertNotIn("moving", LETHAL_CAPACITY_NAMES)
