"""
Tests that sensory / locomotion chrome restores its capacity consumer
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC — augment wiring).

The chrome prototypes (CYBER_LEFT_EYE / CYBER_RIGHT_EYE / CYBER_LEFT_EAR /
CYBER_RIGHT_EAR / CYBER_LEG) restore a performance capacity by being
capacity-bearing replacement organs at the canonical organ names — so
``calculate_body_capacity`` counts them and every consumer sees the sense /
locomotion restored, with no special-case override. These tests drive the
actual prototype specs through a real human ``MedicalState`` and assert the
consumer factors recover.

Run via::

    evennia test --keepdb world.tests.test_capacity_chrome
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.core import MedicalState, Organ
from world.combat.capacity import sight_hit_factor, moving_dodge_factor
from world.voice import can_see, can_hear
from world.prototypes import (
    CYBER_LEFT_EYE,
    CYBER_RIGHT_EYE,
    CYBER_LEFT_EAR,
    CYBER_RIGHT_EAR,
    CYBER_LEG,
)


def _organ_spec(prototype):
    """Pull the single-organ ``organ_spec`` dict off a prototype."""
    return dict(prototype["attrs"])["organ_spec"]


def _augment_organs(prototype, side):
    """Resolve a side-agnostic augment's ``{side}`` organ specs."""
    raw = dict(prototype["attrs"])["augment_organs"]
    out = {}
    for name, spec in raw.items():
        rn = name.replace("{side}", side)
        rs = {k: (v.replace("{side}", side) if isinstance(v, str) else v)
              for k, v in spec.items()}
        out[rn] = rs
    return out


class _Patient:
    """A character whose ``medical_state`` the consumers read."""
    def __init__(self):
        self.db = SimpleNamespace(species="human")

    def attach(self):
        self.medical_state = MedicalState(character=self)
        return self.medical_state


def _install(state, organ_name, spec):
    state.organs[organ_name] = Organ(organ_name, organ_data=dict(spec))
    state._cache_dirty = True


def _destroy(state, *organ_names):
    for name in organ_names:
        if name in state.organs:
            state.organs[name].current_hp = 0
    state._cache_dirty = True


class CyberEyeRestoresSight(TestCase):
    def test_blind_then_chromed(self):
        p = _Patient()
        state = p.attach()
        self.assertTrue(can_see(p))
        self.assertAlmostEqual(sight_hit_factor(p, is_ranged=True), 1.0)

        # Both flesh eyes destroyed → blind, aim collapses.
        _destroy(state, "left_eye", "right_eye")
        self.assertFalse(can_see(p))
        self.assertLess(sight_hit_factor(p, is_ranged=True), 0.1)

        # Install chrome optics at the canonical eye slots.
        _install(state, "left_eye", _organ_spec(CYBER_LEFT_EYE))
        _install(state, "right_eye", _organ_spec(CYBER_RIGHT_EYE))
        self.assertTrue(can_see(p))
        self.assertAlmostEqual(sight_hit_factor(p, is_ranged=True), 1.0)

    def test_single_optic_restores_one_eye(self):
        p = _Patient()
        state = p.attach()
        _destroy(state, "left_eye", "right_eye")
        _install(state, "left_eye", _organ_spec(CYBER_LEFT_EYE))
        # One working eye is enough to see (perception threshold) even if
        # depth perception (ranged aim) is still imperfect.
        self.assertTrue(can_see(p))


class CyberEarRestoresHearing(TestCase):
    def test_deaf_then_chromed(self):
        p = _Patient()
        state = p.attach()
        self.assertTrue(can_hear(p))

        _destroy(state, "left_ear", "right_ear")
        self.assertFalse(can_hear(p))

        _install(state, "left_ear", _organ_spec(CYBER_LEFT_EAR))
        _install(state, "right_ear", _organ_spec(CYBER_RIGHT_EAR))
        self.assertTrue(can_hear(p))


class CyberLegRestoresMoving(TestCase):
    def test_wrecked_leg_then_chromed(self):
        p = _Patient()
        state = p.attach()
        self.assertAlmostEqual(moving_dodge_factor(p), 1.0)

        # Destroy the left leg's locomotion organs → dodge degrades.
        _destroy(state, "left_femur", "left_tibia", "left_metatarsals")
        self.assertLess(moving_dodge_factor(p), 1.0)
        wrecked = moving_dodge_factor(p)

        # Install the cybernetic leg (left side) — actuators at the canonical
        # bone names restore the moving capacity.
        for name, spec in _augment_organs(CYBER_LEG, "left").items():
            _install(state, name, spec)
        self.assertGreater(moving_dodge_factor(p), wrecked)
        self.assertAlmostEqual(moving_dodge_factor(p), 1.0)


class ChromePrototypeShape(TestCase):
    """Guard the capacity wiring the consumers depend on."""

    def test_eyes_declare_sight(self):
        for proto in (CYBER_LEFT_EYE, CYBER_RIGHT_EYE):
            self.assertEqual(_organ_spec(proto)["capacity"], "sight")

    def test_ears_declare_hearing(self):
        for proto in (CYBER_LEFT_EAR, CYBER_RIGHT_EAR):
            self.assertEqual(_organ_spec(proto)["capacity"], "hearing")

    def test_leg_organs_use_canonical_bone_names(self):
        organs = _augment_organs(CYBER_LEG, "right")
        for name in ("right_femur", "right_tibia", "right_metatarsals"):
            self.assertIn(name, organs)
            self.assertEqual(organs[name]["capacity"], "moving")
