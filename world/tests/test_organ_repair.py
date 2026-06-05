"""Tests for the organ_repair surgical channel (#307, PR-D).

Organ repair is the surgical-grade direct channel: applying a
deep-treatment item during an open procedure restores HP to the
underlying organ on the spot, scaled by the item's
``organ_repair`` effectiveness rating.  Third channel under the
wound_care umbrella alongside stabilization (PR-B) and
slow-tick healing (PR-C).

Gating rule:

* Substance application tolerates anything (the apply succeeds)
* The ``organ_repair`` effect lands only when the wound's
  container has an open incision (or the organ is surface-
  accessible per the display_location rule from PR-A)

Run via::

    evennia test world.tests.test_organ_repair
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.core import MedicalState
from world.medical.procedures import open_incision
from world.medical.treatments import (
    FAILURE,
    PARTIAL,
    SUCCESS,
    _organ_repair_hp_gain,
    apply_wound_care,
)
from world.medical.constants import (
    ORGAN_REPAIR_DIVISOR,
    ORGAN_REPAIR_PARTIAL_DENOMINATOR,
    ORGAN_REPAIR_PARTIAL_NUMERATOR,
    WOUND_CARE_PARALLEL_CATEGORIES,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _patient(intellect=2, motorics=2, conscious=True):
    char = SimpleNamespace()
    char.intellect = intellect
    char.motorics = motorics
    char.is_unconscious = lambda: not conscious
    char.db = SimpleNamespace(
        species="human", archived=False, surgical_state=None,
        removed_organs=None, severed_locations=None,
    )
    char.key = "TestPatient"
    char.medical_state = MedicalState(char)
    return char


def _medic(intellect=3, motorics=3):
    return _patient(intellect=intellect, motorics=motorics)


def _wound_organ(patient, organ_name, hp_loss_fraction=0.5):
    organ = patient.medical_state.organs[organ_name]
    damage = int(organ.max_hp * hp_loss_fraction)
    organ.current_hp = max(0, organ.max_hp - damage)
    organ.wound_stage = "fresh"
    return organ


def _sealant(uses_left=3):
    attrs_store = {
        "effectiveness": {
            "organ_repair":  8,
            "infection":     7,
            "wound_healing": 5,
            "bleeding":      3,
            "pain":          1,
        },
        "uses_left": uses_left,
        "medical_type": "organ_repair",
    }

    class _Attrs:
        def get(self, key):
            return attrs_store.get(key)

        def add(self, key, value):
            attrs_store[key] = value

    item = SimpleNamespace()
    item.attributes = _Attrs()
    item.key = "surgical sealant"
    item._store = attrs_store
    return item


def _gauze():
    """Gauze has no organ_repair rating — confirms the category
    doesn't fire when the item doesn't declare it."""
    attrs_store = {
        "effectiveness": {
            "bleeding": 7,
            "infection": 8,
            "wound_healing": 6,
            "pain": 3,
            # No organ_repair key — rating defaults to 0.
        },
        "uses_left": 3,
        "medical_type": "wound_care",
    }

    class _Attrs:
        def get(self, key):
            return attrs_store.get(key)

        def add(self, key, value):
            attrs_store[key] = value

    item = SimpleNamespace()
    item.attributes = _Attrs()
    item.key = "gauze"
    return item


# ---------------------------------------------------------------------
# Category list contract
# ---------------------------------------------------------------------


class ParallelCategoriesIncludesOrganRepair(TestCase):

    def test_organ_repair_in_parallel_categories(self):
        self.assertIn("organ_repair", WOUND_CARE_PARALLEL_CATEGORIES)

    def test_organ_repair_is_last(self):
        """Pin the order so any future addition lands AFTER
        organ_repair rather than before (defensive: the dispatch
        is order-independent today but the explicit ordering
        documents intent)."""
        self.assertEqual(
            WOUND_CARE_PARALLEL_CATEGORIES[-1], "organ_repair",
        )


# ---------------------------------------------------------------------
# HP-gain math
# ---------------------------------------------------------------------


class OrganRepairHpGain(TestCase):

    def test_success_uses_divisor(self):
        # Rating 8, divisor 3 → 8 // 3 = 2 HP per success.
        expected = 8 // ORGAN_REPAIR_DIVISOR
        self.assertEqual(_organ_repair_hp_gain(8, SUCCESS), expected)

    def test_partial_uses_fraction(self):
        # Rating 8, divisor 3, partial 1/2 → 2 // 2 = 1 HP.
        base = 8 // ORGAN_REPAIR_DIVISOR
        expected = (
            base * ORGAN_REPAIR_PARTIAL_NUMERATOR
        ) // ORGAN_REPAIR_PARTIAL_DENOMINATOR
        self.assertEqual(_organ_repair_hp_gain(8, PARTIAL), expected)

    def test_failure_returns_zero(self):
        self.assertEqual(_organ_repair_hp_gain(8, FAILURE), 0)

    def test_zero_rating_returns_zero(self):
        self.assertEqual(_organ_repair_hp_gain(0, SUCCESS), 0)

    def test_low_rating_floors_to_zero(self):
        """Rating below divisor → 0 HP/success (predictable failure
        for very low-rated items)."""
        # 2 // 3 = 0
        self.assertEqual(_organ_repair_hp_gain(2, SUCCESS), 0)


# ---------------------------------------------------------------------
# Integration: organ_repair fires only with open incision
# ---------------------------------------------------------------------


class OrganRepairGatedOnIncision(TestCase):

    def _setup_wounded(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.6)
        return patient, organ

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_sealant_without_incision_does_not_repair(self, _r):
        """Sealant applied to a closed chest stabilizes but doesn't
        reach the heart — substance tolerance principle: apply
        succeeds, organ_repair effect doesn't land."""
        patient, organ = self._setup_wounded()
        before_hp = organ.current_hp
        result = apply_wound_care(_medic(), patient, _sealant(), "chest")
        self.assertTrue(result["stabilized"])
        self.assertEqual(
            organ.current_hp, before_hp,
            "Closed chest: organ HP should be unchanged.",
        )

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_sealant_with_incision_repairs(self, _r):
        """Sealant applied during an open procedure restores HP."""
        patient, organ = self._setup_wounded()
        # Open the chest first — simulates incise having succeeded.
        open_incision(patient, "chest", surgeon=_medic())
        before_hp = organ.current_hp
        apply_wound_care(_medic(), patient, _sealant(), "chest")
        # Sealant rating 8 / divisor 3 = 2 HP on success.
        expected_gain = 8 // ORGAN_REPAIR_DIVISOR
        self.assertEqual(organ.current_hp, before_hp + expected_gain)

    @patch("world.medical.treatments.random.randint", return_value=1)
    def test_failure_does_not_repair_even_with_incision(self, _r):
        """Bad roll by a low-skill medic: stabilization still lands,
        organ_repair doesn't.

        Minimum-skill medic + worst dice puts the total below the
        partial threshold so the failure branch fires:
        roll(3) + skill(0) + rating(8) = 11 vs partial threshold 12.
        """
        patient, organ = self._setup_wounded()
        open_incision(patient, "chest", surgeon=_medic())
        before_hp = organ.current_hp
        # Untrained medic forces failure at minimum dice rolls.
        novice = _medic(intellect=0, motorics=0)
        result = apply_wound_care(novice, patient, _sealant(), "chest")
        self.assertTrue(result["stabilized"])
        self.assertEqual(organ.current_hp, before_hp)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_gauze_does_not_repair_even_with_incision(self, _r):
        """Gauze has no organ_repair rating — even an open chest
        doesn't get organ HP back from it."""
        patient, organ = self._setup_wounded()
        open_incision(patient, "chest", surgeon=_medic())
        before_hp = organ.current_hp
        apply_wound_care(_medic(), patient, _gauze(), "chest")
        # Gauze has no organ_repair rating → no HP restored.
        self.assertEqual(organ.current_hp, before_hp)


# ---------------------------------------------------------------------
# Surface-accessible organs skip the incision gate
# ---------------------------------------------------------------------


class OrganRepairSurfaceAccess(TestCase):
    """Per the PR-A access rule: organs with display_location
    distinct from container (eyes / ears / face on humans) are
    surface-accessible.  organ_repair should reach them without
    requiring an incision."""

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_eye_repair_without_head_incision(self, _r):
        patient = _patient()
        eye = _wound_organ(
            patient, "left_eye", hp_loss_fraction=0.5,
        )
        before_hp = eye.current_hp
        apply_wound_care(
            _medic(), patient, _sealant(), "left_eye",
        )
        # Surface-accessible — repair should land without incision.
        expected_gain = 8 // ORGAN_REPAIR_DIVISOR
        self.assertEqual(eye.current_hp, before_hp + expected_gain)


# ---------------------------------------------------------------------
# SURGICAL_SEALANT prototype contract
# ---------------------------------------------------------------------


class SurgicalSealantPrototype(TestCase):

    def _load_prototype(self):
        from world.prototypes import SURGICAL_SEALANT
        return SURGICAL_SEALANT

    def test_prototype_exists(self):
        self.assertIsNotNone(self._load_prototype())

    def test_medical_type_is_organ_repair(self):
        proto = self._load_prototype()
        attrs = dict(proto["attrs"])
        self.assertEqual(attrs.get("medical_type"), "organ_repair")

    def test_effectiveness_has_organ_repair(self):
        proto = self._load_prototype()
        attrs = dict(proto["attrs"])
        effectiveness = attrs.get("effectiveness") or {}
        self.assertGreater(effectiveness.get("organ_repair", 0), 0)

    def test_has_canonical_aliases(self):
        proto = self._load_prototype()
        for alias in ("sealant", "bioseal"):
            with self.subTest(alias=alias):
                self.assertIn(alias, proto["aliases"])
