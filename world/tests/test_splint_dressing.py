"""Splints set the over-time dressing channel on bones (issue #497).

A splint application heals the most-damaged bone once (+5, the
existing behavior) AND marks it stabilized with a dressing_rate so
the medical script's PR-C healing tick keeps knitting it over time —
splints are the bone-HP path; surgery's organ_repair is for soft
organs.

Run via::

    evennia test --settings settings.py world.tests.test_splint_dressing
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.core import MedicalState
from world.medical.script import _process_healing


class _Attrs:
    def __init__(self, **kw):
        self._v = dict(kw)

    def get(self, key, default=None):
        return self._v.get(key, default)


def _splint_item(fracture_rating=8):
    return SimpleNamespace(
        attributes=_Attrs(
            medical_type="fracture_treatment",
            effectiveness={"fracture": fracture_rating},
            uses_left=1,
            max_uses=1,
        ),
    )


def _patient_with_broken_arm():
    state = MedicalState(character=None)
    bone = state.organs["left_humerus"]
    bone.current_hp = bone.max_hp - 10  # fractured, not destroyed
    target = SimpleNamespace(medical_state=state)
    target.msg = lambda *a, **k: None
    # Downstream of treatment, apply_medical_effects runs the
    # immediate-revival check, which reads target.scripts.
    target.scripts = SimpleNamespace(get=lambda *a, **k: [])
    return target, bone


class TestSplintDressing(TestCase):
    def _apply(self, target, item):
        from world.medical.utils import apply_medical_effects

        return apply_medical_effects(item, SimpleNamespace(), target)

    def test_splint_heals_once_and_sets_dressing(self):
        target, bone = _patient_with_broken_arm()
        before = bone.current_hp
        msg = self._apply(target, _splint_item(fracture_rating=8))
        self.assertEqual(bone.current_hp, before + 5)
        self.assertTrue(bone.stabilized)
        self.assertEqual(bone.dressing_rate, 8)
        self.assertIn("knit over time", msg)

    def test_splinted_bone_knits_on_the_healing_tick(self):
        """rating 8 // divisor 5 = 1 HP per medical tick."""
        target, bone = _patient_with_broken_arm()
        self._apply(target, _splint_item(fracture_rating=8))
        hp_after_splint = bone.current_hp
        _process_healing(target, target.medical_state)
        self.assertEqual(bone.current_hp, hp_after_splint + 1)

    def test_better_dressing_not_downgraded(self):
        target, bone = _patient_with_broken_arm()
        bone.dressing_rate = 15
        self._apply(target, _splint_item(fracture_rating=8))
        self.assertEqual(bone.dressing_rate, 15)

    def test_destroyed_bones_not_splintable(self):
        """Shattered (0 HP) bones need surgery, not a splint —
        existing behavior preserved."""
        target, bone = _patient_with_broken_arm()
        bone.current_hp = 0
        self._apply(target, _splint_item())
        self.assertFalse(bone.stabilized)
