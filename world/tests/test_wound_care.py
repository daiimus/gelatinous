"""Tests for the wound_care stabilization channel (#307, PR-B).

Covers:

* ``world.medical.treatments.apply_wound_care`` — main dispatch
* ``Organ.stabilized`` lifecycle (set on application, cleared on
  full heal, serialised across to_dict/from_dict)
* ``BleedingCondition._location_stabilized`` — bleed-tick stops
  bleeding loss when the wounded organ is stabilized
* Repeat-application no-op (triage hint)
* Per-category roll outcomes (success / partial / failure)
* Item ``uses_left`` consumed on application

The treatment dispatch uses ``random.randint`` for the 3d6 roll;
tests patch it to drive deterministic outcomes.

Run via::

    evennia test world.tests.test_wound_care
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.medical.core import MedicalState, Organ
from world.medical.conditions import (
    BleedingCondition,
    InfectionCondition,
    PainCondition,
)
from world.medical.treatments import (
    FAILURE,
    PARTIAL,
    SUCCESS,
    _category_reduction,
    _is_internal_container,
    _wound_severity_from_organ,
    apply_wound_care,
    calculate_treatment_difficulty,
    calculate_treatment_skill,
    damaged_organs_at_location,
)
from world.medical.constants import (
    WOUND_CARE_BASE_DIFFICULTY,
    WOUND_CARE_BLEEDING_REDUCTION,
    WOUND_CARE_DEPTH_MODIFIER,
    WOUND_CARE_PAIN_REDUCTION,
    WOUND_CARE_SEVERITY_MODIFIERS,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _patient(intellect=2, motorics=2, conscious=True):
    """Minimal living target with a real MedicalState."""
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


def _wound_organ(patient, organ_name: str, hp_loss_fraction: float = 0.5):
    """Reduce ``organ_name`` HP on ``patient`` by ``hp_loss_fraction``."""
    organ = patient.medical_state.organs[organ_name]
    damage = int(organ.max_hp * hp_loss_fraction)
    organ.current_hp = max(0, organ.max_hp - damage)
    organ.wound_stage = "fresh"
    return organ


def _item(effectiveness: dict, uses_left: int = 3,
          medical_type: str = "wound_care"):
    """Stub item with the attributes the treatments dispatch reads."""
    attrs_store = {
        "effectiveness": effectiveness,
        "uses_left": uses_left,
        "medical_type": medical_type,
    }

    class _Attrs:
        def get(self, key):
            return attrs_store.get(key)

        def add(self, key, value):
            attrs_store[key] = value

    item = SimpleNamespace()
    item.attributes = _Attrs()
    item.key = "test-bandage"
    # Snapshot for inspection in tests:
    item._store = attrs_store
    return item


# ---------------------------------------------------------------------
# Organ.stabilized lifecycle
# ---------------------------------------------------------------------


class OrganStabilizedAttribute(TestCase):

    def test_default_false(self):
        organ = Organ("heart", species="human")
        self.assertFalse(organ.stabilized)

    def test_serializes_to_dict(self):
        organ = Organ("heart", species="human")
        organ.stabilized = True
        data = organ.to_dict()
        self.assertIn("stabilized", data)
        self.assertTrue(data["stabilized"])

    def test_round_trips_through_from_dict(self):
        organ = Organ("heart", species="human")
        organ.stabilized = True
        organ.current_hp = 5
        organ.wound_stage = "fresh"
        restored = Organ.from_dict(organ.to_dict())
        self.assertTrue(restored.stabilized)

    def test_legacy_dict_without_field_defaults_false(self):
        organ = Organ("heart", species="human")
        data = organ.to_dict()
        data.pop("stabilized", None)
        restored = Organ.from_dict(data)
        self.assertFalse(restored.stabilized)

    def test_full_heal_clears_stabilization(self):
        organ = Organ("heart", species="human")
        organ.current_hp = 5
        organ.wound_stage = "fresh"
        organ.stabilized = True
        organ.heal(organ.max_hp)
        self.assertEqual(organ.current_hp, organ.max_hp)
        self.assertFalse(organ.stabilized)


# ---------------------------------------------------------------------
# BleedingCondition stabilization interaction
# ---------------------------------------------------------------------


class BleedingStabilization(TestCase):

    def _patient_with_chest_bleed(self):
        patient = _patient()
        _wound_organ(patient, "heart", hp_loss_fraction=0.5)
        bleed = BleedingCondition(severity=5, location="chest")
        patient.medical_state.conditions.append(bleed)
        return patient, bleed

    @patch("world.combat.debug.get_splattercast")
    def test_unstabilized_bleed_drains_blood(self, mock_channel):
        mock_channel.objects.get_channel.return_value = MagicMock()
        patient, bleed = self._patient_with_chest_bleed()
        initial_blood = patient.medical_state.blood_level
        # Pin natural-healing roll high so severity doesn't drift.
        with patch("world.medical.conditions.random.randint",
                   return_value=100):
            bleed.tick_effect(patient)
        self.assertLess(
            patient.medical_state.blood_level, initial_blood,
            "Unstabilized bleeding should drain blood on tick.",
        )

    @patch("world.combat.debug.get_splattercast")
    def test_stabilized_bleed_holds_blood(self, mock_channel):
        mock_channel.objects.get_channel.return_value = MagicMock()
        patient, bleed = self._patient_with_chest_bleed()
        patient.medical_state.organs["heart"].stabilized = True
        initial_blood = patient.medical_state.blood_level
        with patch("world.medical.conditions.random.randint",
                   return_value=100):
            bleed.tick_effect(patient)
        self.assertEqual(
            patient.medical_state.blood_level, initial_blood,
            "Stabilized bleeding should not drain blood on tick.",
        )

    @patch("world.combat.debug.get_splattercast")
    def test_stabilized_undamaged_organ_does_not_shield(self, mock_channel):
        """A stabilized-but-undamaged organ at the location shouldn't
        protect an unrelated bleeding source there."""
        mock_channel.objects.get_channel.return_value = MagicMock()
        patient = _patient()
        # Lung wounded + bleeding; heart untouched but flagged
        # stabilized (degenerate scenario, but stress the guard).
        _wound_organ(patient, "left_lung", hp_loss_fraction=0.5)
        patient.medical_state.organs["heart"].stabilized = True
        bleed = BleedingCondition(severity=3, location="chest")
        patient.medical_state.conditions.append(bleed)
        initial_blood = patient.medical_state.blood_level
        with patch("world.medical.conditions.random.randint",
                   return_value=100):
            bleed.tick_effect(patient)
        self.assertLess(patient.medical_state.blood_level, initial_blood)


# ---------------------------------------------------------------------
# Skill and difficulty calculation
# ---------------------------------------------------------------------


class TreatmentSkill(TestCase):

    def test_skill_formula(self):
        actor = SimpleNamespace(intellect=4, motorics=2)
        # 4 * 0.75 + 2 * 0.25 = 3.0 + 0.5 = 3.5
        self.assertEqual(calculate_treatment_skill(actor), 3.5)

    def test_skill_missing_stats_defaults_zero(self):
        actor = SimpleNamespace()
        self.assertEqual(calculate_treatment_skill(actor), 0.0)


class TreatmentDifficulty(TestCase):

    def test_base_difficulty_at_minor_external(self):
        diff = calculate_treatment_difficulty(
            "Minor", item_internal_effective=False,
            is_internal_wound=False,
        )
        self.assertEqual(diff, WOUND_CARE_BASE_DIFFICULTY)

    def test_severity_modifier_applied(self):
        for severity, expected_mod in WOUND_CARE_SEVERITY_MODIFIERS.items():
            with self.subTest(severity=severity):
                diff = calculate_treatment_difficulty(
                    severity, item_internal_effective=False,
                    is_internal_wound=False,
                )
                self.assertEqual(
                    diff, WOUND_CARE_BASE_DIFFICULTY + expected_mod
                )

    def test_depth_modifier_for_internal_wound_with_surface_item(self):
        diff = calculate_treatment_difficulty(
            "Moderate", item_internal_effective=False,
            is_internal_wound=True,
        )
        self.assertEqual(
            diff,
            WOUND_CARE_BASE_DIFFICULTY +
            WOUND_CARE_SEVERITY_MODIFIERS["Moderate"] +
            WOUND_CARE_DEPTH_MODIFIER,
        )

    def test_depth_modifier_skipped_for_internal_item(self):
        """Surgical-grade items skip the depth penalty even when used
        on internal wounds."""
        diff = calculate_treatment_difficulty(
            "Moderate", item_internal_effective=True,
            is_internal_wound=True,
        )
        self.assertEqual(
            diff,
            WOUND_CARE_BASE_DIFFICULTY +
            WOUND_CARE_SEVERITY_MODIFIERS["Moderate"],
        )


# ---------------------------------------------------------------------
# Wound severity from organ
# ---------------------------------------------------------------------


class WoundSeverityFromOrgan(TestCase):

    def _organ_at_hp(self, current, maximum=20):
        organ = Organ("heart", species="human")
        organ.max_hp = maximum
        organ.current_hp = current
        return organ

    def test_full_hp_returns_minor(self):
        # No HP loss → Minor — never actually called this way but
        # behaviourally safe.
        organ = self._organ_at_hp(20)
        self.assertEqual(_wound_severity_from_organ(organ), "Minor")

    def test_quarter_loss_returns_moderate(self):
        organ = self._organ_at_hp(15)  # 25% lost
        self.assertEqual(_wound_severity_from_organ(organ), "Moderate")

    def test_half_loss_returns_severe(self):
        organ = self._organ_at_hp(10)  # 50% lost
        self.assertEqual(_wound_severity_from_organ(organ), "Severe")

    def test_three_quarter_loss_returns_critical(self):
        organ = self._organ_at_hp(5)  # 75% lost
        self.assertEqual(_wound_severity_from_organ(organ), "Critical")


# ---------------------------------------------------------------------
# Category reduction
# ---------------------------------------------------------------------


class CategoryReduction(TestCase):

    def test_success_full_reduction(self):
        self.assertEqual(
            _category_reduction("bleeding", SUCCESS),
            WOUND_CARE_BLEEDING_REDUCTION,
        )
        self.assertEqual(
            _category_reduction("pain", SUCCESS),
            WOUND_CARE_PAIN_REDUCTION,
        )

    def test_partial_half_reduction(self):
        self.assertEqual(
            _category_reduction("bleeding", PARTIAL),
            WOUND_CARE_BLEEDING_REDUCTION // 2,
        )

    def test_failure_zero_reduction(self):
        self.assertEqual(_category_reduction("bleeding", FAILURE), 0)
        self.assertEqual(_category_reduction("pain", FAILURE), 0)


# ---------------------------------------------------------------------
# Internal container classification
# ---------------------------------------------------------------------


class InternalContainerClassification(TestCase):

    def test_internal_cavities(self):
        for loc in ("head", "chest", "abdomen", "back", "neck", "groin"):
            with self.subTest(loc=loc):
                self.assertTrue(_is_internal_container(loc))

    def test_limbs_not_internal(self):
        for loc in ("left_arm", "right_arm", "left_hand", "left_thigh",
                    "left_shin", "left_foot", "tail"):
            with self.subTest(loc=loc):
                self.assertFalse(_is_internal_container(loc))

    def test_none_not_internal(self):
        self.assertFalse(_is_internal_container(None))


# ---------------------------------------------------------------------
# damaged_organs_at_location
# ---------------------------------------------------------------------


class DamagedOrgansAtLocation(TestCase):

    def test_finds_damaged_chest_organ(self):
        patient = _patient()
        _wound_organ(patient, "heart", hp_loss_fraction=0.3)
        results = damaged_organs_at_location(patient, "chest")
        names = [o.name for o in results]
        self.assertIn("heart", names)

    def test_skips_healthy_organs(self):
        patient = _patient()
        # No wounding — chest is healthy.
        results = damaged_organs_at_location(patient, "chest")
        self.assertEqual(results, [])

    def test_matches_via_display_location(self):
        """Eye damage surfaces at display_location='left_eye' rather
        than container='head'."""
        patient = _patient()
        _wound_organ(patient, "left_eye", hp_loss_fraction=0.4)
        results = damaged_organs_at_location(patient, "left_eye")
        names = [o.name for o in results]
        self.assertIn("left_eye", names)


# ---------------------------------------------------------------------
# apply_wound_care dispatch
# ---------------------------------------------------------------------


class ApplyWoundCareDispatch(TestCase):

    def _setup_wounded_patient(self):
        patient = _patient()
        organ = _wound_organ(patient, "heart", hp_loss_fraction=0.4)
        bleed = BleedingCondition(severity=4, location="chest")
        infect = InfectionCondition(severity=3, location="chest")
        pain = PainCondition(severity=5, location="chest")
        patient.medical_state.conditions.extend([bleed, infect, pain])
        return patient, organ, bleed, infect, pain

    def test_no_wound_at_location_returns_no_op(self):
        patient = _patient()
        medic = _medic()
        item = _item({"bleeding": 5})
        result = apply_wound_care(medic, patient, item, "chest")
        self.assertEqual(result["no_op_reason"], "no_wound")
        self.assertFalse(result["stabilized"])

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_success_stabilizes_and_reduces_categories(self, _r):
        patient, organ, bleed, infect, pain = self._setup_wounded_patient()
        medic = _medic()
        item = _item({"bleeding": 7, "infection": 8, "pain": 3})
        result = apply_wound_care(medic, patient, item, "chest")
        self.assertTrue(result["stabilized"])
        self.assertTrue(organ.stabilized)
        # All three categories full-reduced.
        self.assertEqual(
            bleed.severity, 4 - WOUND_CARE_BLEEDING_REDUCTION
        )
        self.assertEqual(
            infect.severity, 3 - WOUND_CARE_BLEEDING_REDUCTION
        )
        self.assertEqual(pain.severity, 5 - WOUND_CARE_PAIN_REDUCTION)

    @patch("world.medical.treatments.random.randint", return_value=1)
    def test_failure_still_stabilizes(self, _r):
        """Even with worst possible rolls, the act of dressing the
        wound stabilizes — buys time for a surgeon."""
        patient, organ, bleed, _i, _p = self._setup_wounded_patient()
        medic = _medic()
        item = _item({"bleeding": 0})
        original_bleed = bleed.severity
        result = apply_wound_care(medic, patient, item, "chest")
        self.assertTrue(result["stabilized"])
        self.assertTrue(organ.stabilized)
        # Severity unchanged on failure.
        self.assertEqual(bleed.severity, original_bleed)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_repeat_application_no_ops(self, _r):
        patient, organ, bleed, _i, _p = self._setup_wounded_patient()
        medic = _medic()
        item = _item({"bleeding": 7, "infection": 8, "pain": 3})
        apply_wound_care(medic, patient, item, "chest")
        bleed_after_first = bleed.severity
        # Second application — should bail with already_stabilized.
        result = apply_wound_care(medic, patient, item, "chest")
        self.assertEqual(result["no_op_reason"], "already_stabilized")
        # Severity unchanged from the no-op.
        self.assertEqual(bleed.severity, bleed_after_first)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_consumes_one_use(self, _r):
        patient, *_ = self._setup_wounded_patient()
        medic = _medic()
        item = _item({"bleeding": 7}, uses_left=3)
        apply_wound_care(medic, patient, item, "chest")
        self.assertEqual(item._store["uses_left"], 2)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_marks_all_damaged_organs_at_location_stabilized(self, _r):
        patient = _patient()
        heart = _wound_organ(patient, "heart", hp_loss_fraction=0.3)
        lung = _wound_organ(patient, "left_lung", hp_loss_fraction=0.4)
        medic = _medic()
        item = _item({"bleeding": 5})
        apply_wound_care(medic, patient, item, "chest")
        self.assertTrue(heart.stabilized)
        self.assertTrue(lung.stabilized)

    @patch("world.medical.treatments.random.randint", return_value=6)
    def test_does_not_stabilize_unrelated_locations(self, _r):
        patient = _patient()
        chest_organ = _wound_organ(patient, "heart", hp_loss_fraction=0.3)
        abdomen_organ = _wound_organ(patient, "liver", hp_loss_fraction=0.3)
        medic = _medic()
        item = _item({"bleeding": 5})
        apply_wound_care(medic, patient, item, "chest")
        self.assertTrue(chest_organ.stabilized)
        self.assertFalse(abdomen_organ.stabilized)
