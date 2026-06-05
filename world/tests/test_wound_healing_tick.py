"""Tests for the wound-healing tick channel (#307, PR-C).

Healing is the slow-recovery channel separate from stabilization
(PR-B).  An applied wound_care item registers its ``wound_healing``
effectiveness rating on the underlying organ via ``dressing_rate``;
the medical script's tick walks stabilized organs and restores HP
proportional to the stored rating.

This module exercises the pure helpers and lifecycle around the
healing channel.  Full ``MedicalScript`` integration (Evennia
script machinery) is covered separately in the live suite — here
we test the pieces the script consumes.

Run via::

    evennia test world.tests.test_wound_healing_tick
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.core import MedicalState, Organ
from world.medical.script import (
    _has_healing_work,
    _hp_per_tick,
    _process_healing,
)
from world.medical.constants import (
    WOUND_HEALING_DIVISOR,
    WOUND_HEALING_FLOOR_HP_PER_TICK,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _patient():
    char = SimpleNamespace()
    char.db = SimpleNamespace(
        species="human", archived=False, surgical_state=None,
        removed_organs=None, severed_locations=None,
    )
    char.key = "TestPatient"
    char.medical_state = MedicalState(char)
    return char


def _wound_organ(patient, organ_name, hp_loss_fraction=0.5):
    organ = patient.medical_state.organs[organ_name]
    damage = int(organ.max_hp * hp_loss_fraction)
    organ.current_hp = max(0, organ.max_hp - damage)
    organ.wound_stage = "fresh"
    return organ


def _item(effectiveness, uses_left=3):
    attrs_store = {
        "effectiveness": effectiveness,
        "uses_left": uses_left,
        "medical_type": "wound_care",
    }

    class _Attrs:
        def get(self, key):
            return attrs_store.get(key)

        def add(self, key, value):
            attrs_store[key] = value

    item = SimpleNamespace()
    item.attributes = _Attrs()
    item.key = "test-bandage"
    item._store = attrs_store
    return item


# ---------------------------------------------------------------------
# Organ.dressing_rate lifecycle
# ---------------------------------------------------------------------


class OrganDressingRateAttribute(TestCase):

    def test_default_zero(self):
        organ = Organ("heart", species="human")
        self.assertEqual(organ.dressing_rate, 0)

    def test_serializes_to_dict(self):
        organ = Organ("heart", species="human")
        organ.dressing_rate = 6
        data = organ.to_dict()
        self.assertIn("dressing_rate", data)
        self.assertEqual(data["dressing_rate"], 6)

    def test_round_trips_through_from_dict(self):
        organ = Organ("heart", species="human")
        organ.current_hp = 5
        organ.wound_stage = "fresh"
        organ.stabilized = True
        organ.dressing_rate = 8
        restored = Organ.from_dict(organ.to_dict())
        self.assertEqual(restored.dressing_rate, 8)

    def test_legacy_dict_without_field_defaults_zero(self):
        organ = Organ("heart", species="human")
        data = organ.to_dict()
        data.pop("dressing_rate", None)
        restored = Organ.from_dict(data)
        self.assertEqual(restored.dressing_rate, 0)

    def test_non_integer_dressing_rate_coerces_to_zero(self):
        """Defensive: corrupt persistence shouldn't blow up
        deserialization."""
        organ = Organ("heart", species="human")
        data = organ.to_dict()
        data["dressing_rate"] = "garbage"
        restored = Organ.from_dict(data)
        self.assertEqual(restored.dressing_rate, 0)

    def test_full_heal_clears_dressing_rate(self):
        """Heal-to-full clears both stabilized and dressing_rate so
        a future re-injury starts clean."""
        organ = Organ("heart", species="human")
        organ.current_hp = 5
        organ.wound_stage = "fresh"
        organ.stabilized = True
        organ.dressing_rate = 8
        organ.heal(organ.max_hp)
        self.assertEqual(organ.current_hp, organ.max_hp)
        self.assertEqual(organ.dressing_rate, 0)
        self.assertFalse(organ.stabilized)


# ---------------------------------------------------------------------
# _hp_per_tick
# ---------------------------------------------------------------------


class HpPerTick(TestCase):

    def test_zero_rating_returns_floor(self):
        self.assertEqual(_hp_per_tick(0), WOUND_HEALING_FLOOR_HP_PER_TICK)

    def test_low_rating_below_divisor_returns_floor(self):
        """Ratings below the divisor land at floor (0 by default —
        wound stays stable but doesn't actively heal)."""
        # WOUND_HEALING_DIVISOR is 5 by default.
        self.assertEqual(_hp_per_tick(3), WOUND_HEALING_FLOOR_HP_PER_TICK)

    def test_rating_equal_to_divisor_returns_one(self):
        """Rating = DIVISOR → 1 HP/tick."""
        # 5 // 5 = 1
        self.assertEqual(_hp_per_tick(WOUND_HEALING_DIVISOR), 1)

    def test_high_rating_scales(self):
        """Higher ratings produce more HP per tick."""
        # 10 // 5 = 2
        self.assertEqual(_hp_per_tick(10), 2)

    def test_very_high_rating_scales(self):
        # 30 // 5 = 6
        self.assertEqual(_hp_per_tick(30), 6)


# ---------------------------------------------------------------------
# _has_healing_work
# ---------------------------------------------------------------------


class HasHealingWork(TestCase):

    def test_no_organs_returns_false(self):
        state = SimpleNamespace(organs={})
        self.assertFalse(_has_healing_work(state))

    def test_unstabilized_wounded_organ_returns_false(self):
        patient = _patient()
        _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        # No stabilization, no dressing.
        self.assertFalse(_has_healing_work(patient.medical_state))

    def test_stabilized_but_no_dressing_returns_false(self):
        """Stabilization alone doesn't heal — needs a dressing rate."""
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        organ.stabilized = True
        organ.dressing_rate = 0
        self.assertFalse(_has_healing_work(patient.medical_state))

    def test_stabilized_with_dressing_returns_true(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        organ.stabilized = True
        organ.dressing_rate = 6
        self.assertTrue(_has_healing_work(patient.medical_state))

    def test_fully_healed_organ_returns_false(self):
        """Even with dressing_rate set, a fully-healed organ has
        no work left."""
        patient = _patient()
        organ = patient.medical_state.organs["heart"]
        organ.stabilized = True
        organ.dressing_rate = 6
        # current_hp == max_hp by default.
        self.assertFalse(_has_healing_work(patient.medical_state))

    def test_multiple_organs_returns_true_if_any_needs_healing(self):
        patient = _patient()
        healthy = patient.medical_state.organs["heart"]
        # Heart is healthy.
        self.assertEqual(healthy.current_hp, healthy.max_hp)
        # Lung is wounded + dressed.
        lung = _wound_organ(patient, "left_lung")
        lung.stabilized = True
        lung.dressing_rate = 6
        self.assertTrue(_has_healing_work(patient.medical_state))


# ---------------------------------------------------------------------
# _process_healing
# ---------------------------------------------------------------------


class ProcessHealing(TestCase):

    def test_unstabilized_organ_not_healed(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        before = organ.current_hp
        _process_healing(patient, patient.medical_state)
        self.assertEqual(organ.current_hp, before)

    def test_stabilized_with_dressing_heals(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.6)
        organ.stabilized = True
        organ.dressing_rate = 10  # 10 // 5 = 2 HP/tick
        before = organ.current_hp
        healed = _process_healing(patient, patient.medical_state)
        self.assertIn(organ, healed)
        self.assertEqual(organ.current_hp, before + 2)

    def test_zero_rate_organ_does_not_heal(self):
        """Stabilization with rating below the divisor (which
        rounds to 0) keeps the wound stable but doesn't heal."""
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        organ.stabilized = True
        organ.dressing_rate = 3  # 3 // 5 = 0 HP/tick
        before = organ.current_hp
        healed = _process_healing(patient, patient.medical_state)
        self.assertEqual(organ.current_hp, before)
        self.assertNotIn(organ, healed)

    def test_full_heal_clears_dressing_state(self):
        """When healing brings the organ to max HP, ``heal`` clears
        the stabilized + dressing_rate fields automatically."""
        patient = _patient()
        organ = patient.medical_state.organs["heart"]
        organ.current_hp = organ.max_hp - 2  # Need 2 HP to fully heal
        organ.wound_stage = "fresh"
        organ.stabilized = True
        organ.dressing_rate = 10  # 2 HP/tick
        _process_healing(patient, patient.medical_state)
        self.assertEqual(organ.current_hp, organ.max_hp)
        self.assertFalse(organ.stabilized)
        self.assertEqual(organ.dressing_rate, 0)

    def test_multiple_dressed_organs_all_heal(self):
        patient = _patient()
        heart = _wound_organ(patient, "heart")
        heart.stabilized = True
        heart.dressing_rate = 10
        lung = _wound_organ(patient, "left_lung")
        lung.stabilized = True
        lung.dressing_rate = 10
        heart_before = heart.current_hp
        lung_before = lung.current_hp
        healed = _process_healing(patient, patient.medical_state)
        self.assertEqual(heart.current_hp, heart_before + 2)
        self.assertEqual(lung.current_hp, lung_before + 2)
        self.assertEqual(len(healed), 2)

    def test_returns_empty_for_no_healing_work(self):
        """Defensive: when nothing's stabilized, the helper
        returns an empty list without mutating anything."""
        patient = _patient()
        result = _process_healing(patient, patient.medical_state)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------
# Integration: apply_wound_care sets dressing_rate
# ---------------------------------------------------------------------


class ApplyWoundCareSetsDressingRate(TestCase):
    """Pin the integration between PR-B's stabilization application
    and PR-C's dressing-rate registration."""

    def _setup_patient_with_wound(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        return patient, organ

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_application_registers_dressing_rate(self, _r):
        from world.medical.treatments import apply_wound_care
        patient, organ = self._setup_patient_with_wound()
        medic = _patient()
        medic.intellect = 3
        medic.motorics = 3
        item = _item({
            "bleeding": 7, "infection": 8, "pain": 3,
            "wound_healing": 6,
        })
        apply_wound_care(medic, patient, item, "chest")
        self.assertEqual(organ.dressing_rate, 6)
        self.assertTrue(organ.stabilized)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_item_without_wound_healing_rating_sets_zero(self, _r):
        """Items that lack a wound_healing rating (or set it to 0)
        stabilize the wound but don't register healing."""
        from world.medical.treatments import apply_wound_care
        patient, organ = self._setup_patient_with_wound()
        medic = _patient()
        medic.intellect = 3
        medic.motorics = 3
        item = _item({"bleeding": 5})  # No wound_healing.
        apply_wound_care(medic, patient, item, "chest")
        self.assertTrue(organ.stabilized)
        self.assertEqual(organ.dressing_rate, 0)
