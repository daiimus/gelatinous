"""Tests for condition-driven organ functionality modifiers (#307).

Pre-fix, ``Organ._has_disabling_conditions`` returned ``False``
unconditionally and ``get_functionality_percentage`` ignored
conditions — conditions were a decorative layer that didn't affect
capacity calculations.

The scan-based wiring (#307) gives each ``Organ`` a back-reference
to its parent ``MedicalState`` and filters body-wide conditions by
location at lookup time:

* Conditions with no location (body-wide) apply to every organ but
  default modifier ``1.0`` means no effect — pain / blood loss /
  consciousness suppression propagate through other channels.
* Location-bound conditions apply only when the organ's
  ``container`` or ``display_location`` matches the condition's
  ``location``.

``InfectionCondition`` overrides both hooks: progressive
functionality modifier (0.9 / 0.75 / 0.5) plus a binary cutoff at
severity 10.

Architectural note: scan-based design (rather than mirroring
conditions onto each organ) is the cyberware-safe pattern.  A
flesh heart swapped for a cyberware heart leaves any chest
infection in place on the body without sync logic, since the
condition never lived on the organ.  Tests cover this case
explicitly.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.conditions import (
    BleedingCondition,
    InfectionCondition,
    MedicalCondition,
)
from world.medical.core import MedicalState, Organ


def _human_character():
    """Plain-Python stub character for MedicalState init.

    ``archived`` and ``key`` are read by ``MedicalCondition.start_condition``
    when conditions are added; default values keep that path quiet
    so tests can focus on the modifier wiring.
    """
    return SimpleNamespace(
        db=SimpleNamespace(species="human", archived=False),
        key="TestSubject",
    )


# ---------------------------------------------------------------------
# Base class defaults
# ---------------------------------------------------------------------


class BaseConditionDefaults(TestCase):
    """The base ``MedicalCondition`` returns no-effect defaults so
    legacy condition subclasses (and future body-wide conditions)
    don't accidentally penalize organ function."""

    def test_disables_default_false(self):
        c = MedicalCondition("test", severity=5)
        self.assertFalse(c.disables_organ_at_severity())

    def test_modifier_default_one(self):
        c = MedicalCondition("test", severity=5)
        self.assertEqual(c.get_organ_functionality_modifier(), 1.0)


class BleedingDoesNotPenalizeOrgan(TestCase):
    """Bleeding's biology is "the body is losing volume" not "this
    organ is impaired", so it stays body-wide via blood_level rather
    than reducing per-organ functionality.  Regression guard against
    double-counting."""

    def test_bleeding_modifier_is_one(self):
        c = BleedingCondition(severity=8, location="chest")
        self.assertEqual(c.get_organ_functionality_modifier(), 1.0)

    def test_bleeding_does_not_disable(self):
        c = BleedingCondition(severity=10, location="chest")
        self.assertFalse(c.disables_organ_at_severity())


# ---------------------------------------------------------------------
# Infection ladder
# ---------------------------------------------------------------------


class InfectionFunctionalityLadder(TestCase):

    def test_severity_zero_no_effect(self):
        c = InfectionCondition(severity=0)
        self.assertEqual(c.get_organ_functionality_modifier(), 1.0)

    def test_minor_severity_small_drag(self):
        # 1-3
        for s in (1, 2, 3):
            with self.subTest(severity=s):
                self.assertEqual(
                    InfectionCondition(severity=s).get_organ_functionality_modifier(),
                    0.9,
                )

    def test_moderate_severity_quarter_off(self):
        # 4-6
        for s in (4, 5, 6):
            with self.subTest(severity=s):
                self.assertEqual(
                    InfectionCondition(severity=s).get_organ_functionality_modifier(),
                    0.75,
                )

    def test_severe_severity_half_function(self):
        # 7-9
        for s in (7, 8, 9):
            with self.subTest(severity=s):
                self.assertEqual(
                    InfectionCondition(severity=s).get_organ_functionality_modifier(),
                    0.5,
                )

    def test_critical_severity_disables(self):
        c = InfectionCondition(severity=10)
        self.assertTrue(c.disables_organ_at_severity())


# ---------------------------------------------------------------------
# Organ scan logic
# ---------------------------------------------------------------------


class OrganBackRefWired(TestCase):
    """``MedicalState`` sets ``organ.medical_state`` on the organs
    it creates so the scan can find the body-wide condition list."""

    def test_init_default_organs_sets_back_ref(self):
        state = MedicalState(_human_character())
        for name, organ in state.organs.items():
            with self.subTest(organ=name):
                self.assertIs(organ.medical_state, state)

    def test_lazy_get_organ_sets_back_ref(self):
        state = MedicalState(_human_character())
        # Drop an organ then re-fetch via get_organ.
        del state.organs["heart"]
        heart = state.get_organ("heart")
        self.assertIs(heart.medical_state, state)


class OrganScanFiltersConditionsByLocation(TestCase):

    def setUp(self):
        self.state = MedicalState(_human_character())
        self.heart = self.state.organs["heart"]      # container="chest"
        self.liver = self.state.organs["liver"]      # container="abdomen"
        self.left_eye = self.state.organs["left_eye"]
        # left_eye.display_location == "left_eye" via #346 routing
        # but container == "head"

    def test_no_conditions_full_function(self):
        self.assertEqual(self.heart.get_functionality_percentage(), 1.0)

    def test_body_wide_no_location_does_not_modify(self):
        # No-location condition reaches every organ via the scan but
        # base modifier 1.0 means no effect.
        self.state.conditions.append(MedicalCondition("test", severity=5))
        self.assertEqual(self.heart.get_functionality_percentage(), 1.0)
        self.assertEqual(self.liver.get_functionality_percentage(), 1.0)

    def test_chest_infection_affects_heart_not_liver(self):
        self.state.conditions.append(
            InfectionCondition(severity=5, location="chest")
        )
        # Heart (chest container) takes a moderate hit.
        self.assertAlmostEqual(
            self.heart.get_functionality_percentage(), 0.75,
        )
        # Liver (abdomen container) untouched.
        self.assertEqual(self.liver.get_functionality_percentage(), 1.0)

    def test_left_eye_condition_matches_display_location(self):
        # Sensory organs surface at their display_location (#346).
        # A condition at "left_eye" should hit the left eye organ
        # via display_location matching even though container="head".
        self.state.conditions.append(
            InfectionCondition(severity=5, location="left_eye")
        )
        self.assertAlmostEqual(
            self.left_eye.get_functionality_percentage(), 0.75,
        )
        # Right eye unaffected.
        right_eye = self.state.organs["right_eye"]
        self.assertEqual(right_eye.get_functionality_percentage(), 1.0)

    def test_head_container_condition_affects_all_head_organs(self):
        # Infection at "head" container — brain, eyes, ears etc.
        # all have container=head and pick it up.
        self.state.conditions.append(
            InfectionCondition(severity=4, location="head")
        )
        for name in ("brain", "left_eye", "right_eye", "left_ear"):
            with self.subTest(organ=name):
                self.assertAlmostEqual(
                    self.state.organs[name].get_functionality_percentage(),
                    0.75,
                )

    def test_critical_infection_disables_organ(self):
        self.state.conditions.append(
            InfectionCondition(severity=10, location="chest")
        )
        self.assertFalse(self.heart.is_functional())

    def test_no_back_ref_degrades_gracefully(self):
        # Standalone organ without medical_state back-ref shouldn't
        # crash — just returns no-modifier defaults.
        organ = Organ("heart")
        self.assertIsNone(organ.medical_state)
        self.assertFalse(organ._has_disabling_conditions())
        self.assertEqual(organ.get_functionality_percentage(), 1.0)


# ---------------------------------------------------------------------
# Cyberware / hot-swap scenario
# ---------------------------------------------------------------------


class CyberwareHotSwapPreservesConditions(TestCase):
    """A chest infection sits on the body, not on the heart.  When
    the flesh heart is replaced with a cyberware equivalent
    (modelled here as a fresh ``Organ`` object replacing the old in
    ``self.organs``), the infection persists naturally with no sync
    logic — because the scan-based design never mirrored it onto
    the heart in the first place."""

    def test_chest_infection_persists_through_heart_swap(self):
        state = MedicalState(_human_character())
        state.conditions.append(
            InfectionCondition(severity=5, location="chest")
        )

        old_heart = state.organs["heart"]
        # Verify infection is impairing the old heart.
        self.assertLess(
            old_heart.get_functionality_percentage(), 1.0,
        )

        # Swap in a "cyberware" heart — fresh Organ object, full HP.
        # Real cyberware replacement is far more elaborate, but the
        # core invariant we want to test is that body-wide condition
        # state is decoupled from individual organ identity.
        new_heart = Organ("heart")
        new_heart.medical_state = state
        state.organs["heart"] = new_heart

        # Body-wide infection is still there.
        self.assertEqual(len(state.conditions), 1)
        # And it still impairs the new heart (same chest container).
        self.assertLess(
            new_heart.get_functionality_percentage(), 1.0,
        )

    def test_abdomen_condition_does_not_follow_a_chest_swap(self):
        # Negative control — a liver-located condition shouldn't
        # follow when a chest organ is replaced.  Sanity-check that
        # the per-organ scan filters by location correctly.
        state = MedicalState(_human_character())
        state.conditions.append(
            InfectionCondition(severity=5, location="abdomen")
        )

        # Swap heart out.
        new_heart = Organ("heart")
        new_heart.medical_state = state
        state.organs["heart"] = new_heart

        # New heart: full function (abdomen condition doesn't match).
        self.assertEqual(new_heart.get_functionality_percentage(), 1.0)
        # Liver: still impaired.
        self.assertLess(
            state.organs["liver"].get_functionality_percentage(), 1.0,
        )


# ---------------------------------------------------------------------
# Capacity integration smoke test
# ---------------------------------------------------------------------


class CapacityScoreReflectsConditionModifiers(TestCase):

    def test_infection_reduces_capacity_via_organ_functionality(self):
        state = MedicalState(_human_character())
        # Baseline.
        base = state.calculate_body_capacity("blood_pumping")
        self.assertAlmostEqual(base, 1.0)

        # Severe chest infection → heart at 0.5 functionality →
        # blood_pumping capacity drops accordingly.
        state.conditions.append(
            InfectionCondition(severity=8, location="chest")
        )
        # Force the capacity cache off.
        state._cache_dirty = True
        impaired = state.calculate_body_capacity("blood_pumping")
        self.assertLess(impaired, base)
