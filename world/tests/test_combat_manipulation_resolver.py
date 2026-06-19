"""
Tests for the per-effector manipulation resolver
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §6.1, build layer 4b).

The defining property (§6.1 Q1): weapon handling scopes to the *specific
gripping hand*, not the body-wide average — a one-armed character with a
pistol in their good hand fights at FULL accuracy. These tests pin that
isolation on a real human ``MedicalState`` plus the resolver's blend /
fallback / override / fail-open behaviour.

Run via::

    evennia test --keepdb world.tests.test_combat_manipulation_resolver
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.core import MedicalState
from world.combat.capacity import (
    MANIPULATION_CURVE,
    MANIPULATION_OVERRIDE_CONDITION,
    manipulation_hit_factor,
    _piecewise,
)


class _Human:
    def __init__(self):
        self.db = SimpleNamespace(species="human")


def _human_state():
    return MedicalState(character=_Human())


def _attacker(hands, state):
    """A combat actor exposing what the resolver reads."""
    return SimpleNamespace(hands=hands, db=SimpleNamespace(species="human"),
                           medical_state=state)


# ----------------------------------------------------------------------
# calculate_capacity_scoped — the scoped-anatomy primitive
# ----------------------------------------------------------------------
class ScopedCapacityTests(TestCase):
    def test_intact_left_hand_scope_full(self):
        state = _human_state()
        self.assertAlmostEqual(
            state.calculate_capacity_scoped("manipulation", {"left_arm", "left_hand"}),
            1.0,
        )

    def test_left_arm_damage_scoped_to_left_only(self):
        state = _human_state()
        state.organs["left_humerus"].current_hp = 0
        state._cache_dirty = True
        left = state.calculate_capacity_scoped(
            "manipulation", {"left_arm", "left_hand"}
        )
        right = state.calculate_capacity_scoped(
            "manipulation", {"right_arm", "right_hand"}
        )
        # The wrecked left humerus drags the LEFT scope down...
        self.assertLess(left, 1.0)
        # ...but the RIGHT hand is untouched (the Q1 isolation property).
        self.assertAlmostEqual(right, 1.0)

    def test_empty_scope_fails_open(self):
        state = _human_state()
        self.assertAlmostEqual(
            state.calculate_capacity_scoped("manipulation", set()), 1.0
        )


# ----------------------------------------------------------------------
# manipulation_hit_factor — the combat consumer
# ----------------------------------------------------------------------
class ManipulationHitFactorTests(TestCase):
    def test_full_hand_full_factor(self):
        state = _human_state()
        weapon = object()
        attacker = _attacker({"left_hand": weapon}, state)
        self.assertAlmostEqual(manipulation_hit_factor(attacker, weapon), 1.0)

    def test_good_hand_unaffected_by_other_arm_loss(self):
        # The headline Q1 case: pistol in the right hand, left arm destroyed —
        # full accuracy, the missing arm is irrelevant to this weapon.
        state = _human_state()
        state.organs["left_humerus"].current_hp = 0
        state.organs["left_metacarpals"].current_hp = 0
        state._cache_dirty = True
        weapon = object()
        attacker = _attacker({"right_hand": weapon}, state)
        self.assertAlmostEqual(manipulation_hit_factor(attacker, weapon), 1.0)

    def test_damaged_gripping_hand_reduces_factor(self):
        state = _human_state()
        state.organs["right_humerus"].current_hp = 0
        state._cache_dirty = True
        weapon = object()
        attacker = _attacker({"right_hand": weapon}, state)
        self.assertLess(manipulation_hit_factor(attacker, weapon), 1.0)

    def test_two_handed_weaker_hand_drags(self):
        # Weapon gripped in both hands; one arm wrecked → the weaker hand
        # sets the handling (min blend).
        state = _human_state()
        state.organs["left_humerus"].current_hp = 0
        state._cache_dirty = True
        weapon = object()
        both = _attacker({"left_hand": weapon, "right_hand": weapon}, state)
        one_good = _attacker({"right_hand": weapon}, _human_state())
        self.assertLess(
            manipulation_hit_factor(both, weapon),
            manipulation_hit_factor(one_good, weapon),
        )

    def test_unarmed_falls_back_to_body_wide(self):
        # No weapon → body-wide manipulation (still full when intact).
        state = _human_state()
        attacker = _attacker({}, state)
        self.assertAlmostEqual(manipulation_hit_factor(attacker, None), 1.0)


class ManipulationOverrideAndFailOpenTests(TestCase):
    class _Stub:
        def __init__(self, overrides=0, scoped=0.0):
            self._overrides = overrides
            self._scoped = scoped

        def calculate_capacity_scoped(self, name, containers):
            return self._scoped

        def calculate_body_capacity(self, name):
            return self._scoped

        def get_conditions_by_type(self, ct):
            if ct == MANIPULATION_OVERRIDE_CONDITION:
                return [object()] * self._overrides
            return []

    def test_override_condition_nulls_penalty(self):
        weapon = object()
        state = self._Stub(overrides=1, scoped=0.0)
        attacker = _attacker({"right_hand": weapon}, state)
        self.assertAlmostEqual(manipulation_hit_factor(attacker, weapon), 1.0)

    def test_no_medical_model_fails_open(self):
        weapon = object()
        attacker = SimpleNamespace(
            hands={"right_hand": weapon},
            db=SimpleNamespace(species="human"),
            medical_state=None,
        )
        self.assertAlmostEqual(manipulation_hit_factor(attacker, weapon), 1.0)

    def test_curve_anchor_sanity(self):
        # Guard the curve contract the factor relies on.
        self.assertAlmostEqual(_piecewise(1.0, MANIPULATION_CURVE), 1.0)
        self.assertAlmostEqual(_piecewise(0.5, MANIPULATION_CURVE), 0.65)
        self.assertAlmostEqual(_piecewise(0.0, MANIPULATION_CURVE), 0.20)
