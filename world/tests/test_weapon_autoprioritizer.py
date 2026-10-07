"""The one door: what a body fights with (MULTI_WEAPON_COMBAT_SPEC §4-§5).

`choose_weapon(char, target)` picks the weapon THIS attack uses, by the
spec's rule order: candidates in slot order, real weapons over improvised
ones, range before natural precedence, then akimbo grouping. The wheel
(slice 2, owner rulings §14 #1, #3, #4, #8) then takes the next option that
can reach, in the body's slot order. `has_ranged_option` answers the gates.
`weapon_options` is the ordered wheel.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.combat.constants import AKIMBO_PROFILES_BY_TYPE, NDB_LAST_WEAPON_SLOT, NDB_PROXIMITY
from world.combat.weapon_choice import (aimed_weapon_name, choose_weapon, has_ranged_option,
                                        note_weapon_used, weapon_options)


class _Tags:
    def __init__(self, weapon):
        self._weapon = weapon

    def has(self, key, category=None):
        return bool(self._weapon and key == "weapon" and category == "type")


def _weapon(key, ranged, damage, *, weapon=True, **attrs):
    db = SimpleNamespace(is_ranged=ranged, damage=damage, weapon_type=attrs.pop("weapon_type", key),
                         damage_type=attrs.pop("damage_type", None), hit_bonus=attrs.pop("hit_bonus", None))
    return SimpleNamespace(key=key, db=db, tags=_Tags(weapon))


_ROOM = object()
_LISTED = ("head", "left_hand", "right_hand")     # the human display order, abridged


def _body_order(names):
    """The body's rule, as the stub: listed slots in display order (the
    head before the hands, left hand first), then anything unlisted
    alphabetically."""
    return sorted(names, key=lambda n: (n not in _LISTED, _LISTED.index(n) if n in _LISTED else 0, n))


def _char(weapons, location=_ROOM, proximity=(), slots=None):
    slots = slots or [f"hand{i}" for i in range(len(weapons))]
    hands = dict(zip(slots, weapons))
    return SimpleNamespace(
        hands=hands,
        location=location,
        ndb=SimpleNamespace(**{NDB_PROXIMITY: set(proximity)}),
        slot_order=_body_order,
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

    def test_at_range_two_guns_alternate(self):
        tgt = _target()
        attacker = _char([_weapon("pistol", True, 10), _weapon("rifle", True, 18)], proximity=())
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "pistol")
        note_weapon_used(attacker, choose_weapon(attacker, tgt))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "rifle")
        note_weapon_used(attacker, choose_weapon(attacker, tgt))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "pistol")

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

    def test_the_aiming_peek_names_the_gun_over_a_blade_in_the_first_slot(self):
        katana = _weapon("katana", False, 14)
        pistol = _weapon("pistol", True, 12)
        attacker = _char([katana, pistol])
        self.assertIs(choose_weapon(attacker).item, katana)       # first slot, no target
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

    def test_a_target_aim_in_melee_names_what_swings_next(self):
        tgt = _target()
        attacker = _char([_weapon("katana", False, 14), _weapon("pistol", True, 12)], proximity=(tgt,))
        self.assertEqual(aimed_weapon_name(attacker, tgt), "katana")
        note_weapon_used(attacker, choose_weapon(attacker, tgt))
        self.assertEqual(aimed_weapon_name(attacker, tgt), "pistol")

    def test_the_three_target_stop_sites_pass_the_aims_target(self):
        # The stop and move lines after a TARGET aim must ask the same
        # question the aim line asked, or a retreat-free stop names the
        # pistol after the aim named the katana (PR #3702 review, round 2).
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        pins = {
            "commands/combat/special_actions.py": "aimed_weapon_name(caller, current_target)",
            "commands/combat/core_actions.py": "aimed_weapon_name(caller, aiming_target)",
            "typeclasses/exits.py": "aimed_weapon_name(traversing_object, old_aim_target)",
        }
        for rel, needle in pins.items():
            body = (root / rel).read_text(errors="ignore")
            self.assertIn(needle, body, rel)

    def test_a_target_aim_at_range_names_the_gun(self):
        tgt = _target()
        attacker = _char([_weapon("katana", False, 14), _weapon("pistol", True, 12)], proximity=())
        self.assertEqual(aimed_weapon_name(attacker, tgt), "pistol")

    def test_empty_hands_fall_back_to_the_word_weapon(self):
        self.assertEqual(aimed_weapon_name(_char([])), "weapon")
        self.assertEqual(aimed_weapon_name(_char([]), _target(), fallback="fists"), "fists")


class MeleeEngagementTests(TestCase):
    """Owner ruling §14 #1: no "then highest damage"; in melee every option
    that can reach takes its turn, first slot first."""

    def test_in_melee_the_first_slot_swings_first_whatever_it_hits_for(self):
        tgt = _target()
        attacker = _char([_weapon("pistol", True, 12), _weapon("sword", False, 20)], proximity=(tgt,))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "pistol")

    def test_in_melee_a_gun_takes_its_turn_pointblank(self):
        tgt = _target()
        attacker = _char([_weapon("knife", False, 14), _weapon("hand cannon", True, 28)], proximity=(tgt,))
        self.assertEqual(choose_weapon(attacker, tgt).item.key, "knife")
        note_weapon_used(attacker, choose_weapon(attacker, tgt))
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


class TheWheel(TestCase):
    """§6: one option per attack, the next option that can reach next, in
    slot order, wrapping; the cursor self-heals; a lone option never waits."""

    def test_a_lone_option_swings_every_time(self):
        pistol = _weapon("pistol", True, 10)
        attacker = _char([pistol])
        for _ in range(3):
            choice = choose_weapon(attacker)
            self.assertIs(choice.item, pistol)
            note_weapon_used(attacker, choice)

    def test_two_pistols_alternate_left_right_left(self):
        left, right = _weapon("left pistol", True, 10), _weapon("right pistol", True, 10)
        attacker = _char([left, right], slots=["left_hand", "right_hand"])
        seen = []
        for _ in range(4):
            choice = choose_weapon(attacker)
            seen.append(choice.item.key)
            note_weapon_used(attacker, choice)
        self.assertEqual(seen, ["left pistol", "right pistol", "left pistol", "right pistol"])

    def test_pistol_and_knife_at_range_fire_the_pistol_every_round(self):
        tgt = _target()
        attacker = _char([_weapon("knife", False, 4), _weapon("pistol", True, 10)], proximity=())
        for _ in range(3):
            choice = choose_weapon(attacker, tgt)
            self.assertEqual(choice.item.key, "pistol")
            note_weapon_used(attacker, choice)

    def test_pistol_and_knife_in_melee_alternate(self):
        tgt = _target()
        attacker = _char([_weapon("knife", False, 4), _weapon("pistol", True, 10)], proximity=(tgt,))
        seen = []
        for _ in range(3):
            choice = choose_weapon(attacker, tgt)
            seen.append(choice.item.key)
            note_weapon_used(attacker, choice)
        self.assertEqual(seen, ["knife", "pistol", "knife"])

    def test_the_cursor_self_heals_when_its_slot_is_gone(self):
        # Disarmed or severed between swings: the cursor names a slot no
        # option holds; the wheel takes the next slot after it, wrapping.
        a, c = _weapon("a", False, 5), _weapon("c", False, 5)
        attacker = _char([a, c], slots=["hand_a", "hand_c"])
        setattr(attacker.ndb, NDB_LAST_WEAPON_SLOT, "hand_b")
        self.assertEqual(choose_weapon(attacker).item.key, "c")
        setattr(attacker.ndb, NDB_LAST_WEAPON_SLOT, "hand_z")
        self.assertEqual(choose_weapon(attacker).item.key, "a")

    def test_nailz_and_jawz_alternate(self):
        # Owner ruling §14 #3. The pair groups as one option under the
        # left hand; the fangs sit on the head, a non-grasping host that
        # the display order lists before the hands (JAWZ host "head").
        left = _weapon("left claws", False, 6, weapon_type="nailz")
        right = _weapon("right claws", False, 6, weapon_type="nailz")
        fangs = _weapon("fangs", False, 8)
        attacker = _char([None, None], slots=["left_hand", "right_hand"])
        with _naturals(("left_hand", left), ("right_hand", right), ("head", fangs)):
            seen = []
            for _ in range(4):
                choice = choose_weapon(attacker)
                seen.append((choice.weapon_type, choice.lead_slot))
                note_weapon_used(attacker, choice)
        # the head comes before the hands in the body's order: fangs, pair, fangs, pair
        self.assertEqual(seen, [("fangs", "head"), ("nailz_akimbo", "left_hand"),
                                ("fangs", "head"), ("nailz_akimbo", "left_hand")])

    def test_peeks_never_turn_the_wheel(self):
        # Only note_weapon_used moves the cursor; the refused-swing case is
        # pinned in test_the_roll_takes_the_weapons_hit_bonus.
        left, right = _weapon("l", True, 10), _weapon("r", True, 10)
        attacker = _char([left, right], slots=["left_hand", "right_hand"])
        for _ in range(3):
            self.assertIs(choose_weapon(attacker).item, left)

    def test_the_peek_and_the_swing_agree(self):
        # The initiate line peeks; the swing that follows commits the same option.
        left, right = _weapon("l", True, 10), _weapon("r", True, 10)
        attacker = _char([left, right], slots=["left_hand", "right_hand"])
        peeked = choose_weapon(attacker)
        note_weapon_used(attacker, peeked)
        self.assertIs(peeked.item, left)
        self.assertIs(choose_weapon(attacker).item, right)


class AkimboGroupingTests(TestCase):
    PROFILES = {2: {"damage": 9, "hit_bonus": 1, "weapon_type": "nailz_akimbo"}}

    def _claw(self, key="claws"):
        return _weapon(key, False, 6, weapon_type="nailz", damage_type="cut")

    def test_two_claws_make_one_attack_on_the_pair_profile(self):
        left, right = self._claw("left claws"), self._claw("right claws")
        attacker = _char([None, None], slots=["left_hand", "right_hand"])
        with _naturals(("left_hand", left), ("right_hand", right)):
            choice = choose_weapon(attacker)
        self.assertTrue(choice.akimbo)
        self.assertEqual(choice.items, (left, right))
        self.assertEqual(choice.slots, ("left_hand", "right_hand"))
        self.assertEqual((choice.damage, choice.hit_bonus, choice.weapon_type, choice.damage_type),
                         (9, 1, "nailz_akimbo", "cut"))

    def test_one_claw_keeps_the_single_profile(self):
        left = self._claw()
        attacker = _char([None], slots=["left_hand"])
        with _naturals(("left_hand", left)):
            choice = choose_weapon(attacker)
        self.assertFalse(choice.akimbo)
        self.assertEqual((choice.damage, choice.hit_bonus, choice.weapon_type), (6, 0, "nailz"))

    def test_three_claws_with_a_pair_profile_make_a_pair_and_a_single(self):
        a, b, c = (self._claw(k) for k in ("a", "b", "c"))
        attacker = _char([None, None, None], slots=["left_hand", "right_hand", "tail"])
        with _naturals(("left_hand", a), ("right_hand", b), ("tail", c)):
            options = weapon_options(attacker)
        self.assertEqual([len(o.items) for o in options], [2, 1])
        self.assertEqual(options[0].items, (a, b))
        self.assertIs(options[1].item, c)

    def test_a_type_without_a_row_never_pairs(self):
        # Two knives are two options: only a weapon_type with a row in
        # AKIMBO_PROFILES_BY_TYPE groups (owner ruling §14 #14).
        self.assertNotIn("knife", AKIMBO_PROFILES_BY_TYPE)
        left, right = _weapon("l", False, 6, weapon_type="knife"), _weapon("r", False, 6, weapon_type="knife")
        attacker = _char([left, right], slots=["left_hand", "right_hand"])
        self.assertEqual([len(o.items) for o in weapon_options(attacker)], [1, 1])

    def test_two_types_with_rows_never_pair(self):
        left = self._claw()
        other = _weapon("jawz", False, 8, weapon_type="jawz")
        attacker = _char([None], slots=["left_hand"])
        with patch.dict(AKIMBO_PROFILES_BY_TYPE, {"jawz": dict(self.PROFILES)}), \
                _naturals(("left_hand", left), ("jaw", other)):
            options = weapon_options(attacker)
        self.assertEqual([len(o.items) for o in options], [1, 1])

    def test_a_profile_field_outside_the_allowed_set_is_ignored(self):
        # is_ranged and natural are dataclass fields a profile could reach
        # through replace(); a stray key ("reach") would raise there. The
        # AKIMBO_PROFILE_FIELDS filter keeps all three out.
        left, right = _weapon("l", False, 6, weapon_type="x"), _weapon("r", False, 6, weapon_type="x")
        attacker = _char([None, None], slots=["a", "b"])
        row = {2: {"damage": 9, "is_ranged": True, "natural": False, "reach": 3}}
        with patch.dict(AKIMBO_PROFILES_BY_TYPE, {"x": row}), _naturals(("a", left), ("b", right)):
            choice = choose_weapon(attacker)
        self.assertEqual(choice.damage, 9)
        self.assertFalse(choice.is_ranged)
        self.assertTrue(choice.natural)
