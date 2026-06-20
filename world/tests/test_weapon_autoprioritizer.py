"""
Tests for the combat weapon auto-prioritizer
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §6.1 Q2 — loadout-readiness).

Combat brings the best in-hand weapon to bear for the current engagement:
range-appropriate first (only ranged weapons reach at range; anything works
point-blank), then highest damage. A one-weapon fighter is unchanged; holding
several (multi-armed / cyber tail) is what the picker rewards.

Run via::

    evennia test --keepdb world.tests.test_weapon_autoprioritizer
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.combat.constants import NDB_PROXIMITY
from world.combat.utils import select_weapon_for_engagement


def _weapon(key, ranged, damage):
    return SimpleNamespace(
        key=key, db=SimpleNamespace(is_ranged=ranged, damage=damage)
    )


_ROOM = object()


def _char(weapons, location=_ROOM, proximity=()):
    hands = {f"hand{i}": w for i, w in enumerate(weapons)}
    return SimpleNamespace(
        hands=hands,
        location=location,
        ndb=SimpleNamespace(**{NDB_PROXIMITY: set(proximity)}),
    )


class _Target:
    """Plain (hashable) target — real Characters go in the proximity set."""
    def __init__(self, location=_ROOM):
        self.location = location


def _target(location=_ROOM):
    return _Target(location)


class SingleWeaponUnchangedTests(TestCase):
    def test_single_weapon_returned(self):
        gun = _weapon("pistol", True, 10)
        attacker = _char([gun])
        self.assertIs(
            select_weapon_for_engagement(attacker, _target()), gun
        )

    def test_unarmed_returns_none(self):
        self.assertIsNone(
            select_weapon_for_engagement(_char([]), _target())
        )


class RangedEngagementTests(TestCase):
    def test_at_range_picks_ranged_even_if_lower_damage(self):
        # Sword hits harder but can't reach; the pistol is the only option.
        tgt = _target()
        attacker = _char(
            [_weapon("sword", False, 20), _weapon("pistol", True, 10)],
            proximity=(),  # not closed to melee → at range
        )
        chosen = select_weapon_for_engagement(attacker, tgt)
        self.assertEqual(chosen.key, "pistol")

    def test_at_range_highest_damage_ranged_wins(self):
        tgt = _target()
        attacker = _char(
            [_weapon("pistol", True, 10), _weapon("rifle", True, 18)],
            proximity=(),
        )
        self.assertEqual(
            select_weapon_for_engagement(attacker, tgt).key, "rifle"
        )

    def test_at_range_only_melee_falls_back(self):
        # No ranged option: return a held weapon so the caller's reach gate
        # produces the right "can't reach" message.
        tgt = _target()
        attacker = _char([_weapon("sword", False, 20)], proximity=())
        self.assertEqual(
            select_weapon_for_engagement(attacker, tgt).key, "sword"
        )


class MeleeEngagementTests(TestCase):
    def test_in_melee_highest_damage_wins(self):
        tgt = _target()
        attacker = _char(
            [_weapon("pistol", True, 12), _weapon("sword", False, 20)],
            proximity=(tgt,),  # closed to melee
        )
        self.assertEqual(
            select_weapon_for_engagement(attacker, tgt).key, "sword"
        )

    def test_in_melee_gun_used_pointblank_if_higher_damage(self):
        tgt = _target()
        attacker = _char(
            [_weapon("hand cannon", True, 28), _weapon("knife", False, 14)],
            proximity=(tgt,),
        )
        self.assertEqual(
            select_weapon_for_engagement(attacker, tgt).key, "hand cannon"
        )


class NaturalWeaponPrecedenceTests(TestCase):
    def test_active_natural_weapon_wins_outright(self):
        claws = _weapon("claws", False, 30)
        attacker = _char([_weapon("pistol", True, 10)], proximity=())
        with patch(
            "world.medical.augments.get_active_natural_weapon",
            return_value=claws,
        ):
            self.assertIs(
                select_weapon_for_engagement(attacker, _target()), claws
            )
