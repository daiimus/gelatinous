"""
Tests for the sight combat-capacity consumer
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §9 layer 1).

``world/combat/capacity.py`` turns the previously-inert ``sight`` body
capacity into a multiplier on combat aim.  These tests pin the curve's
contract (anchor points + shape), the chrome/biotech suppression seam, and
the fail-open guarantee — without standing up a full combat handler.

Run via::

    evennia test --keepdb world.tests.test_combat_capacity_sight
"""

from unittest import TestCase

from world.combat.capacity import (
    SIGHT_OVERRIDE_CONDITION,
    MOVING_OVERRIDE_CONDITION,
    sight_hit_factor,
    moving_dodge_factor,
    _piecewise,
    SIGHT_CURVE_RANGED,
    SIGHT_CURVE_MELEE,
)


class _FakeMedicalState:
    """Minimal stand-in for ``MedicalState`` exposing only what the
    capacity consumer reads."""

    def __init__(self, sight=1.0, override_conditions=0):
        self._sight = sight
        self._overrides = override_conditions

    def calculate_body_capacity(self, name):
        if name == "sight":
            return self._sight
        return 1.0

    def get_conditions_by_type(self, condition_type):
        if condition_type == SIGHT_OVERRIDE_CONDITION:
            return [object()] * self._overrides
        return []


class _FakeChar:
    def __init__(self, medical_state=None):
        self.key = "Tester"
        self.medical_state = medical_state


class PiecewiseCurveTests(TestCase):
    """The interpolation primitive itself."""

    def test_hits_exact_anchor_values(self):
        for raw, expected in SIGHT_CURVE_RANGED:
            self.assertAlmostEqual(_piecewise(raw, SIGHT_CURVE_RANGED), expected)

    def test_interpolates_between_anchors(self):
        # Midway between (0.5, 0.65) and (1.0, 1.0) -> 0.825
        self.assertAlmostEqual(_piecewise(0.75, SIGHT_CURVE_RANGED), 0.825)

    def test_clamps_out_of_range(self):
        self.assertAlmostEqual(_piecewise(-5.0, SIGHT_CURVE_RANGED), 0.05)
        self.assertAlmostEqual(_piecewise(5.0, SIGHT_CURVE_RANGED), 1.0)


class RangedSightTests(TestCase):
    def _factor(self, sight):
        char = _FakeChar(_FakeMedicalState(sight=sight))
        return sight_hit_factor(char, is_ranged=True)

    def test_two_eyes_no_penalty(self):
        self.assertAlmostEqual(self._factor(1.0), 1.0)

    def test_one_eye_redundancy_protected(self):
        # One eye (0.5) keeps you above the linear 0.5 — depth perception
        # gone but still combat-capable.
        self.assertAlmostEqual(self._factor(0.5), 0.65)
        self.assertGreater(self._factor(0.5), 0.5)

    def test_blind_is_near_useless(self):
        self.assertAlmostEqual(self._factor(0.0), 0.05)

    def test_monotonic_non_decreasing(self):
        prev = -1.0
        for raw in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
            cur = self._factor(raw)
            self.assertGreaterEqual(cur, prev)
            prev = cur


class MeleeSightTests(TestCase):
    def _factor(self, sight):
        char = _FakeChar(_FakeMedicalState(sight=sight))
        return sight_hit_factor(char, is_ranged=False)

    def test_two_eyes_no_penalty(self):
        self.assertAlmostEqual(self._factor(1.0), 1.0)

    def test_one_eye_costs_nothing_in_melee(self):
        self.assertAlmostEqual(self._factor(0.5), 1.0)

    def test_blind_modest_penalty_only(self):
        # You can still grab and swing by feel.
        self.assertAlmostEqual(self._factor(0.0), 0.70)

    def test_melee_never_below_ranged_at_same_sight(self):
        for raw in (0.0, 0.25, 0.5):
            char = _FakeChar(_FakeMedicalState(sight=raw))
            melee = sight_hit_factor(char, is_ranged=False)
            ranged = sight_hit_factor(char, is_ranged=True)
            self.assertGreaterEqual(melee, ranged)


class SuppressionAndFailOpenTests(TestCase):
    def test_override_condition_nulls_penalty(self):
        # Blind, but a chrome sense-enhancer (override condition) restores aim.
        char = _FakeChar(_FakeMedicalState(sight=0.0, override_conditions=1))
        self.assertAlmostEqual(sight_hit_factor(char, is_ranged=True), 1.0)
        self.assertAlmostEqual(sight_hit_factor(char, is_ranged=False), 1.0)

    def test_no_medical_state_fails_open(self):
        char = _FakeChar(medical_state=None)
        self.assertAlmostEqual(sight_hit_factor(char, is_ranged=True), 1.0)

    def test_unreadable_capacity_fails_open(self):
        class _Broken:
            def calculate_body_capacity(self, name):
                raise RuntimeError("boom")

            def get_conditions_by_type(self, ct):
                return []

        char = _FakeChar(_Broken())
        self.assertAlmostEqual(sight_hit_factor(char, is_ranged=True), 1.0)


class _MovingMedicalState:
    def __init__(self, moving=1.0, override_conditions=0):
        self._moving = moving
        self._overrides = override_conditions

    def calculate_body_capacity(self, name):
        return self._moving if name == "moving" else 1.0

    def get_conditions_by_type(self, condition_type):
        if condition_type == MOVING_OVERRIDE_CONDITION:
            return [object()] * self._overrides
        return []


class MovingDodgeTests(TestCase):
    def _factor(self, moving):
        return moving_dodge_factor(_FakeChar(_MovingMedicalState(moving=moving)))

    def test_full_locomotion_no_penalty(self):
        self.assertAlmostEqual(self._factor(1.0), 1.0)

    def test_healthy_partial_loss_scales(self):
        # A clear penalty below full, but still mobile.
        self.assertLess(self._factor(0.5), 1.0)
        self.assertGreater(self._factor(0.5), 0.25)

    def test_incapacitation_floor_collapses_dodge(self):
        # At/below the 0.15 threshold, evasion is a flail.
        self.assertAlmostEqual(self._factor(0.15), 0.25)
        self.assertAlmostEqual(self._factor(0.0), 0.10)

    def test_monotonic_non_decreasing(self):
        prev = -1.0
        for raw in (0.0, 0.15, 0.3, 0.6, 1.0):
            cur = self._factor(raw)
            self.assertGreaterEqual(cur, prev)
            prev = cur

    def test_override_condition_nulls_penalty(self):
        char = _FakeChar(_MovingMedicalState(moving=0.0, override_conditions=1))
        self.assertAlmostEqual(moving_dodge_factor(char), 1.0)

    def test_no_medical_state_fails_open(self):
        self.assertAlmostEqual(moving_dodge_factor(_FakeChar(None)), 1.0)
