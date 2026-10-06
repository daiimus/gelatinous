"""The one door: what a body fights with (MULTI_WEAPON_COMBAT_SPEC §4-§5).

`choose_weapon(char, target)` picks the weapon THIS attack uses, by the
spec's rule order: candidates in slot order, real weapons over improvised
ones, range before natural precedence, then akimbo grouping. Held weapons
keep range-then-max in slice 1. `has_ranged_option` answers the gates.
`weapon_options` is the ordered wheel.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.combat.constants import NDB_PROXIMITY
from world.combat.weapon_choice import (aimed_weapon_name, choose_weapon, has_ranged_option,
                                        weapon_options)


class _Tags:
    def __init__(self, weapon):
        self._weapon = weapon

    def has(self, key, category=None):
        return bool(self._weapon and key == "weapon" and category == "type")


def _weapon(key, ranged, damage, *, weapon=True, **attrs):
    db = SimpleNamespace(is_ranged=ranged, damage=damage, weapon_type=attrs.pop("weapon_type", key),
                         damage_type=attrs.pop("damage_type", None), hit_bonus=attrs.pop("hit_bonus", None),
                         akimbo_family=attrs.pop("akimbo_family", None),
                         akimbo_profiles=attrs.pop("akimbo_profiles", None))
    return SimpleNamespace(key=key, db=db, tags=_Tags(weapon))


_ROOM = object()


def _char(weapons, location=_ROOM, proximity=(), slots=None):
    slots = slots or [f"hand{i}" for i in range(len(weapons))]
    hands = dict(zip(slots, weapons))
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


def _naturals(*pairs):
    return patch("world.medical.augments.get_active_natural_weapons", return_value=list(pairs))


class SingleWeaponUnchangedTests(TestCase):
    def test_single_weapon_returned(self):
        gun = _weapon("pistol", True, 10)
        choice = choose_weapon(_char([gun]), _target())
        self.assertIs(choice.item, gun)
        self.assertEqual((choice.damage, choice.hit_bonus, choice.weapon_type, choice.is_ranged, choice.akimbo),
                         (10, 0, "pistol", True, False))
        self.assertEqual(choice.slots, ("hand0",))

    def test_unarmed_returns_none(self):
        self.assertIsNone(choose_weapon(_char([]), _target()))
        self.assertFalse(has_ranged_option(_char([])))


class RealWeaponsOverImprovisedTests(TestCase):
    def test_a_tagged_weapon_shoulders_the_cigarette_aside(self):
        cig = _weapon("cigarette", False, 25, weapon=False)
        knife = _weapon("knife", False, 4)
        self.assertIs(choose_weapon(_char([cig, knife]), _target()).item, knife)

    def test_with_nothing_tagged_one_improvised_item_serves(self):
        bottle = _weapon("bottle", False, 3, weapon=False)
        chair = _weapon("chair", False, 5, weapon=False)
        options = weapon_options(_char([bottle, chair]), _target())
        self.assertEqual([o.item.key for o in options], ["chair"])


class RangedEngagementTests(TestCase):
    def test_at_range_picks_ranged_even_if_lower_damage(self):
        tgt = _target()
        attacker = _char([_weapon("sword", False, 20), _weapon("pistol", True, 10)], proximity=())
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "pistol")

    def test_at_range_highest_damage_ranged_wins(self):
        tgt = _target()
        attacker = _char([_weapon("pistol", True, 10), _weapon("rifle", True, 18)], proximity=())
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "rifle")

    def test_at_range_only_melee_falls_back(self):
        # No ranged option: a held weapon comes back so the caller's reach
        # gate produces the right "can't reach" message.
        tgt = _target()
        attacker = _char([_weapon("sword", False, 20)], proximity=())
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "sword")
        self.assertFalse(has_ranged_option(attacker))

    def test_a_knife_sorting_first_does_not_hide_the_pistol(self):
        attacker = _char([_weapon("knife", False, 4), _weapon("pistol", True, 10)])
        self.assertTrue(has_ranged_option(attacker))

    def test_the_aiming_peek_names_the_gun_not_the_claws(self):
        # The direction-aim gate passes on the pistol; the prose must name it,
        # not the claws that natural precedence would swing in melee.
        claws = _weapon("claws", False, 30)
        pistol = _weapon("pistol", True, 10)
        attacker = _char([pistol])
        with _naturals(("left_hand", claws)):
            self.assertIs(choose_weapon(attacker).item, claws)
            self.assertIs(choose_weapon(attacker, at_range=True).item, pistol)

    def test_the_aiming_peek_names_the_gun_over_a_heavier_blade(self):
        katana = _weapon("katana", False, 14)
        pistol = _weapon("pistol", True, 12)
        attacker = _char([katana, pistol])
        self.assertIs(choose_weapon(attacker).item, katana)
        self.assertIs(choose_weapon(attacker, at_range=True).item, pistol)

    def test_the_aiming_peek_with_nothing_ranged_still_names_something(self):
        knife = _weapon("knife", False, 4)
        self.assertIs(choose_weapon(_char([knife]), at_range=True).item, knife)


class TheAimLinesAgree(TestCase):
    """One helper names the weapon in the aim, stop and move lines: a
    direction aim names what would fire at range; a target aim names what
    would swing at that target, so its stop line, asked the same question,
    gives the same answer."""

    def test_a_direction_aim_names_the_gun_over_claws_and_blade(self):
        claws = _weapon("claws", False, 30)
        attacker = _char([_weapon("katana", False, 14), _weapon("pistol", True, 12)])
        with _naturals(("left_hand", claws)):
            self.assertEqual(aimed_weapon_name(attacker), "pistol")

    def test_a_target_aim_in_melee_names_the_blade_and_so_does_its_stop(self):
        tgt = _target()
        attacker = _char([_weapon("katana", False, 14), _weapon("pistol", True, 12)], proximity=(tgt,))
        self.assertEqual(aimed_weapon_name(attacker, tgt), "katana")
        self.assertEqual(aimed_weapon_name(attacker, tgt), aimed_weapon_name(attacker, tgt))

    def test_a_target_aim_at_range_names_the_gun(self):
        tgt = _target()
        attacker = _char([_weapon("katana", False, 14), _weapon("pistol", True, 12)], proximity=())
        self.assertEqual(aimed_weapon_name(attacker, tgt), "pistol")

    def test_empty_hands_fall_back_to_the_word_weapon(self):
        self.assertEqual(aimed_weapon_name(_char([])), "weapon")
        self.assertEqual(aimed_weapon_name(_char([]), _target(), fallback="fists"), "fists")


class MeleeEngagementTests(TestCase):
    def test_in_melee_highest_damage_wins(self):
        tgt = _target()
        attacker = _char([_weapon("pistol", True, 12), _weapon("sword", False, 20)], proximity=(tgt,))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "sword")

    def test_in_melee_gun_used_pointblank_if_higher_damage(self):
        tgt = _target()
        attacker = _char([_weapon("hand cannon", True, 28), _weapon("knife", False, 14)], proximity=(tgt,))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "hand cannon")


class NaturalPrecedenceAfterRangeTests(TestCase):
    """Owner ruling 2026-10-03 (§14 ruling 2): range first, then naturals."""

    def test_in_melee_deployed_claws_win_outright(self):
        tgt = _target()
        claws = _weapon("claws", False, 6)
        attacker = _char([_weapon("knife", True, 30)], proximity=(tgt,), slots=["right_hand"])
        with _naturals(("left_hand", claws)):
            choice = choose_weapon(attacker, tgt)
        self.assertIs(choice.item, claws)
        self.assertTrue(choice.natural)
        self.assertEqual(choice.slots, ())          # left_hand is not in this stub's hands

    def test_at_range_the_pistol_fires_while_the_claws_stay_out(self):
        tgt = _target()
        claws = _weapon("claws", False, 30)
        pistol = _weapon("pistol", True, 10)
        attacker = _char([pistol], proximity=())
        with _naturals(("left_hand", claws)):
            self.assertIs(choose_weapon(attacker, tgt).item, pistol)

    def test_at_range_with_no_ranged_option_the_claws_still_answer(self):
        tgt = _target()
        claws = _weapon("claws", False, 6)
        attacker = _char([_weapon("knife", False, 4)], proximity=())
        with _naturals(("left_hand", claws)):
            self.assertIs(choose_weapon(attacker, tgt).item, claws)

    def test_a_natural_on_a_grasping_host_scopes_to_that_hand(self):
        claws = _weapon("claws", False, 6)
        attacker = _char([None], slots=["left_hand"])
        with _naturals(("left_hand", claws)):
            self.assertEqual(choose_weapon(attacker).slots, ("left_hand",))


class AkimboGroupingTests(TestCase):
    PROFILES = {2: {"damage": 9, "hit_bonus": 1, "weapon_type": "tiger_claws_akimbo"}}

    def _claw(self, key="claws"):
        return _weapon(key, False, 6, weapon_type="tiger_claws", damage_type="cut",
                       akimbo_family="nailz", akimbo_profiles=dict(self.PROFILES))

    def test_two_claws_make_one_attack_on_the_pair_profile(self):
        left, right = self._claw("left claws"), self._claw("right claws")
        attacker = _char([None, None], slots=["left_hand", "right_hand"])
        with _naturals(("left_hand", left), ("right_hand", right)):
            choice = choose_weapon(attacker)
        self.assertTrue(choice.akimbo)
        self.assertEqual(choice.items, (left, right))
        self.assertEqual(choice.slots, ("left_hand", "right_hand"))
        self.assertEqual((choice.damage, choice.hit_bonus, choice.weapon_type, choice.damage_type),
                         (9, 1, "tiger_claws_akimbo", "cut"))

    def test_one_claw_keeps_the_single_profile(self):
        left = self._claw()
        attacker = _char([None], slots=["left_hand"])
        with _naturals(("left_hand", left)):
            choice = choose_weapon(attacker)
        self.assertFalse(choice.akimbo)
        self.assertEqual((choice.damage, choice.hit_bonus, choice.weapon_type), (6, 0, "tiger_claws"))

    def test_three_claws_with_a_pair_profile_make_a_pair_and_a_single(self):
        a, b, c = (self._claw(k) for k in ("a", "b", "c"))
        attacker = _char([None, None, None], slots=["left_hand", "right_hand", "tail"])
        with _naturals(("left_hand", a), ("right_hand", b), ("tail", c)):
            options = weapon_options(attacker)
        self.assertEqual([len(o.items) for o in options], [2, 1])
        self.assertEqual(options[0].items, (a, b))
        self.assertIs(options[1].item, c)

    def test_a_stored_string_count_still_groups(self):
        left = _weapon("l", False, 6, akimbo_family="nailz", akimbo_profiles={"2": {"damage": 9}})
        right = _weapon("r", False, 6, akimbo_family="nailz", akimbo_profiles={"2": {"damage": 9}})
        attacker = _char([None, None], slots=["left_hand", "right_hand"])
        with _naturals(("left_hand", left), ("right_hand", right)):
            self.assertEqual(choose_weapon(attacker).damage, 9)

    def test_different_families_never_pair(self):
        left = self._claw()
        other = _weapon("jawz", False, 8, akimbo_family="jawz", akimbo_profiles=dict(self.PROFILES))
        attacker = _char([None], slots=["left_hand"])
        with _naturals(("left_hand", left), ("jaw", other)):
            options = weapon_options(attacker)
        self.assertEqual([len(o.items) for o in options], [1, 1])

    def test_a_profile_field_outside_the_allowed_set_is_ignored(self):
        # is_ranged and natural are dataclass fields a profile could reach
        # through replace(); a stray key ("reach") would raise there. The
        # AKIMBO_PROFILE_FIELDS filter keeps all three out.
        left = _weapon("l", False, 6, akimbo_family="x",
                       akimbo_profiles={2: {"damage": 9, "is_ranged": True, "natural": False, "reach": 3}})
        right = _weapon("r", False, 6, akimbo_family="x", akimbo_profiles={2: {"damage": 9}})
        attacker = _char([None, None], slots=["a", "b"])
        with _naturals(("a", left), ("b", right)):
            choice = choose_weapon(attacker)
        self.assertEqual(choice.damage, 9)
        self.assertFalse(choice.is_ranged)
        self.assertTrue(choice.natural)
