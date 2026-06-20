"""
Tests for the surplus-limb initiative bonus
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §6.1 Q2 — breadth, not power).

Grasping limbs beyond the species baseline grant an initiative bonus whose
marginal value ACCELERATES through ~6 limbs (a reason to keep adding) and then
TAPERS OFF COMPLETELY (caps). Decided 2026-06-20: not a big 3rd-hand jump.

Run via::

    evennia test --keepdb world.tests.test_initiative_limbs
"""

from types import SimpleNamespace
from unittest import TestCase

from world.combat.utils import (
    INITIATIVE_LIMB_BONUS_UNIT,
    surplus_limb_initiative_bonus,
)


def _char(num_hands, species="human"):
    hands = {f"slot{i}": None for i in range(num_hands)}
    return SimpleNamespace(hands=hands, db=SimpleNamespace(species=species))


class SurplusLimbInitiativeTests(TestCase):
    def test_human_baseline_no_bonus(self):
        self.assertEqual(surplus_limb_initiative_bonus(_char(2)), 0)

    def test_third_hand_is_a_small_jump(self):
        # T(1) = 1 → one unit. Deliberately small.
        self.assertEqual(
            surplus_limb_initiative_bonus(_char(3)), 1 * INITIATIVE_LIMB_BONUS_UNIT
        )

    def test_ramp_accelerates_to_six_limbs(self):
        bonuses = [surplus_limb_initiative_bonus(_char(n)) for n in (2, 3, 4, 5, 6)]
        # 0, 2, 6, 12, 20 with UNIT=2.
        self.assertEqual(
            bonuses,
            [0, 1 * INITIATIVE_LIMB_BONUS_UNIT, 3 * INITIATIVE_LIMB_BONUS_UNIT,
             6 * INITIATIVE_LIMB_BONUS_UNIT, 10 * INITIATIVE_LIMB_BONUS_UNIT],
        )
        # Marginal gains strictly increase up to the cap (accelerating).
        margins = [bonuses[i + 1] - bonuses[i] for i in range(len(bonuses) - 1)]
        self.assertEqual(margins, sorted(margins))
        self.assertTrue(all(m2 > m1 for m1, m2 in zip(margins, margins[1:])))

    def test_caps_at_six_limbs(self):
        peak = surplus_limb_initiative_bonus(_char(6))
        self.assertEqual(surplus_limb_initiative_bonus(_char(7)), peak)
        self.assertEqual(surplus_limb_initiative_bonus(_char(8)), peak)
        self.assertEqual(surplus_limb_initiative_bonus(_char(12)), peak)

    def test_lost_limb_no_bonus_and_no_penalty(self):
        # Below baseline: no initiative bonus (and no negative — the per-weapon
        # accuracy hit already covers losing a hand).
        self.assertEqual(surplus_limb_initiative_bonus(_char(1)), 0)
        self.assertEqual(surplus_limb_initiative_bonus(_char(0)), 0)

    def test_fail_open_without_hands(self):
        self.assertEqual(
            surplus_limb_initiative_bonus(SimpleNamespace(db=SimpleNamespace(species="human"))),
            0,
        )
