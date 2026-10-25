"""#3763 -- acting reveals: the first slice of #3659.

Owner, 2026-10-24, against five played-out scenes: sitting breaks the
hide; being hit breaks it and a miss does not; an untargeted throw never
lands on a hidden person; buying breaks it; you cannot hide while in
combat or while someone is aiming at you.

The engine is `world.stealth.break_stealth`, which speaking already
calls. The new callers: `_take_posture` (sit/lie), `take_damage` (every
hit lands there: melee, shot, thrown object, blast, fall),
`ShopContainer.purchase_item` (the `buy` command and a spoken counter
order both end there). The throw pickers take the thrower as `seen_by`
and drop anyone they cannot perceive. `hide` refuses under a combat
handler or a live aim.

char2 is the hider (no staff permission); char1 watches, Unaware.
"""
from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdFurniture import CmdLie, CmdSit
from commands.CmdStealth import CmdHide
from world.combat.throwing import select_random_target_in_room
from world.perception import can_perceive
from world.stealth import UNAWARE, set_awareness


class _Hidden(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.heard = []
        self.char1.msg = lambda text=None, **kw: self.heard.append(
            str(text[0] if isinstance(text, tuple) else text))

    def hide(self, who=None):
        who = who or self.char2
        who.db.hidden = True
        set_awareness(self.char1, who, UNAWARE)
        self.assertFalse(can_perceive(self.char1, who), "premise: char1 lost them")

    def seat(self, key):
        furn = create_object("typeclasses.furniture.Furniture", key=key,
                             location=self.room1)
        furn.db.postures = ("sitting", "lying")     # a cot takes both
        return furn


class TestSittingBreaksTheHide(_Hidden):

    def test_sit(self):
        self.seat("stool")
        self.hide()
        self.call(CmdSit(), "stool", caller=self.char2)
        self.assertFalse(self.char2.db.hidden)
        self.assertEqual(self.char2.db.posture, "sitting")

    def test_lie(self):
        self.seat("cot")
        self.hide()
        self.call(CmdLie(), "cot", caller=self.char2)
        self.assertFalse(self.char2.db.hidden)

    def test_the_watcher_sees_them_emerge_first(self):
        self.seat("stool")
        self.hide()
        self.call(CmdSit(), "stool", caller=self.char2)
        joined = "\n".join(self.heard)
        self.assertIn("emerges from concealment", joined)
        self.assertLess(joined.index("emerges from concealment"),
                        joined.index("sits"), joined)

    def test_a_refused_seat_leaves_the_hide(self):
        self.hide()
        self.call(CmdSit(), "throne", caller=self.char2)   # no such seat
        self.assertTrue(self.char2.db.hidden)


class TestAHitBreaksTheHide(_Hidden):

    def test_damage_reveals(self):
        self.hide()
        self.char2.take_damage(3, location="chest", injury_type="blunt")
        self.assertFalse(self.char2.db.hidden)
        self.assertIn("emerges from concealment", "\n".join(self.heard))

    def test_no_damage_is_no_hit(self):
        self.hide()
        self.char2.take_damage(0, location="chest", injury_type="blunt")
        self.assertTrue(self.char2.db.hidden)

    def test_the_premise_a_miss_calls_nothing(self):
        """A miss never reaches take_damage: the attack loop only calls it
        on a hit (world/combat/attack.py), so nothing here to break."""
        self.hide()
        self.assertTrue(self.char2.db.hidden)


class TestAThrowNeverLandsOnTheHidden(_Hidden):

    def setUp(self):
        super().setUp()
        self.third = create_object("typeclasses.characters.Character",
                                   key="Bystander", location=self.room1)
        self.third.msg = lambda text=None, **kw: None

    def test_the_hidden_are_not_in_the_pool(self):
        self.hide()
        picks = {select_random_target_in_room(self.room1, exclude=self.char1,
                                              seen_by=self.char1)
                 for _ in range(40)}
        self.assertEqual(picks, {self.third})

    def test_only_a_hidden_person_present_means_no_landing_target(self):
        self.hide()
        self.third.location = self.room2
        self.assertIsNone(select_random_target_in_room(
            self.room1, exclude=self.char1, seen_by=self.char1))

    def test_control_without_a_thrower_everyone_is_in_the_pool(self):
        self.hide()
        self.third.location = self.room2
        self.assertIs(select_random_target_in_room(self.room1, exclude=self.char1),
                      self.char2)

    def test_control_a_visible_person_is_picked(self):
        self.third.location = self.room2
        self.assertIs(select_random_target_in_room(self.room1, exclude=self.char1,
                                                   seen_by=self.char1),
                      self.char2)


class TestBuyingBreaksTheHide(_Hidden):

    def setUp(self):
        super().setUp()
        self.counter = create_object("typeclasses.shopkeeper.ShopContainer",
                                     key="counter", location=self.room1)
        self.counter.db.prototype_inventory = {"SHIV": 5}
        self.counter.db.item_inventory = {"SHIV": 3}
        self.counter.db.is_infinite = False
        self.char2.tokens = 500

    def test_a_purchase_reveals(self):
        self.hide()
        ok, item = self.counter.purchase_item(self.char2, "SHIV")
        self.assertTrue(ok, item)
        self.assertFalse(self.char2.db.hidden)

    def test_a_refused_purchase_does_not(self):
        self.hide()
        self.char2.tokens = 0
        ok, _why = self.counter.purchase_item(self.char2, "SHIV")
        self.assertFalse(ok)
        self.assertTrue(self.char2.db.hidden)


class TestNoHidingUnderAimOrInAFight(_Hidden):

    def test_in_combat(self):
        self.char2.ndb.combat_handler = MagicMock()
        out = self.call(CmdHide(), "", caller=self.char2)
        self.assertIn("middle of a fight", out)
        self.assertFalse(self.char2.db.hidden)
        del self.char2.ndb.combat_handler

    def test_under_a_live_aim(self):
        self.char1.ndb.aiming_at = self.char2
        self.char2.ndb.aimed_at_by = self.char1
        out = self.call(CmdHide(), "", caller=self.char2)
        self.assertIn("weapon trained on you", out)
        self.assertFalse(self.char2.db.hidden)
        del self.char1.ndb.aiming_at
        del self.char2.ndb.aimed_at_by

    def test_a_stale_aim_from_another_room_does_not_count(self):
        self.char1.ndb.aiming_at = self.char2
        self.char2.ndb.aimed_at_by = self.char1
        self.char1.location = self.room2
        out = self.call(CmdHide(), "", caller=self.char2)
        self.assertIn("slip out of sight", out)
        self.assertTrue(self.char2.db.hidden)
        del self.char1.ndb.aiming_at
        del self.char2.ndb.aimed_at_by

    def test_control_hide_still_works(self):
        out = self.call(CmdHide(), "", caller=self.char2)
        self.assertIn("You slip out of sight.", out)
        self.assertTrue(self.char2.db.hidden)
