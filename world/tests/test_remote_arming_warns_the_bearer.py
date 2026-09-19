"""The remote arming beep reaches whoever has the charge on them, and their room (#3350).

A charge's location is often not a room: stuck, it is the armor; carried
or held, the character. Both remote doors broadcast the arming line to
that location, so the armor's contents or the holder's other pockets were
told and nobody else. Owner: the room hears it, the bearer gets one
personal line, nobody is told twice, and the bracketed countdown is for
builders only.

Room lines are asserted on the call into msg_room_identity (the test
harness has no sessions, so a room broadcast never reaches an observer's
msg); personal lines on the bearer's msg. char1 is a Developer in this
harness, char2 a plain player.
"""
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands import CmdExplosives
from commands.CmdExplosives import CmdDetonate


class RemoteArmingWarnsTheBearerTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.detonator = create_object("typeclasses.items.RemoteDetonator",
                                       key="VECTOR UEM-3 detonator", location=self.char1)
        self.char1.wield_item(self.detonator, hand="right")

    def _charge(self, key, location, fuse=6):
        g = create_object("typeclasses.items.Item", key=key, location=location)
        g.db.is_explosive = True
        g.db.blast_damage = 0
        g.db.fuse_time = fuse
        self.detonator.db.scanned_explosives = list(self.detonator.db.scanned_explosives or []) + [g.id]
        return g

    def _detonate(self, g):
        with patch.object(CmdExplosives, "msg_room_identity") as room, patch.object(self.char2, "msg") as bearer:
            out = self.call(CmdDetonate(), f"e-{g.id} with detonator") or ""
        return out, room, [str(c) for c in bearer.call_args_list]

    def _room_lines(self, room_mock):
        # the bearer lines carry target_char; the operator's button line carries actor
        return [c.kwargs for c in room_mock.call_args_list
                if "target_char" in c.kwargs.get("char_refs", {}) and "beeps" in c.kwargs.get("template", "")]

    # --- control: a charge on the floor is announced to its room as before ---

    def test_control_a_loose_charge_is_announced_to_the_room(self):
        g = self._charge("floor charge", self.room1)
        with patch.object(CmdExplosives, "msg_room_identity") as room:
            out = self.call(CmdDetonate(), f"e-{g.id} with detonator") or ""
        self.assertIn("The floor charge beeps", out)
        self.assertIn("[6 seconds]", out, "the operator is a Developer and sees the countdown")
        floor = [c.kwargs for c in room.call_args_list if "floor charge beeps" in c.kwargs.get("template", "")]
        self.assertTrue(floor, room.call_args_list)
        self.assertIn(self.char1, floor[0]["exclude"], "the operator got their own line")

    # --- the defect: carried, held and stuck charges warned nobody ---

    def test_a_carried_charge_warns_the_holder_once_and_the_room_on_them(self):
        g = self._charge("pocket charge", self.char2)
        out, room, heard = self._detonate(g)
        beeps = [h for h in heard if "beeps" in h]
        self.assertEqual(len(beeps), 1, heard)
        self.assertIn("in your pocket beeps", beeps[0])
        self.assertNotIn("seconds]", beeps[0], "a plain player saw the countdown")
        lines = self._room_lines(room)
        self.assertEqual(len(lines), 1, room.call_args_list)
        self.assertIn("pocket beeps", lines[0]["template"])
        self.assertEqual(lines[0]["char_refs"], {"target_char": self.char2})
        self.assertIn(self.char2, lines[0]["exclude"], "the holder would be told twice")
        self.assertEqual(lines[0]["location"], self.room1)

    def test_a_held_charge_is_in_the_hand_not_the_pocket(self):
        g = self._charge("held charge", self.char2)
        self.char2.wield_item(g, hand="right")
        out, room, heard = self._detonate(g)
        beeps = [h for h in heard if "beeps" in h]
        self.assertEqual(len(beeps), 1, heard)
        self.assertIn("in your hand beeps", beeps[0])
        lines = self._room_lines(room)
        self.assertIn("in {target_char}'s hand beeps", lines[0]["template"])

    def test_a_stuck_charge_warns_the_wearer_once_before_the_countdown(self):
        vest = create_object("typeclasses.items.Item", key="plate carrier", location=self.char2)
        g = self._charge("sticky charge", vest)
        g.db.stuck_to_armor = vest
        vest.db.stuck_grenade = g
        out, room, heard = self._detonate(g)
        beeps = [i for i, h in enumerate(heard) if "beeps" in h]
        ticks = [i for i, h in enumerate(heard) if "SECONDS" in h]
        self.assertEqual(len(beeps), 1, heard)
        self.assertIn("stuck to your plate carrier beeps", heard[beeps[0]])
        self.assertTrue(ticks, "the sticky ticker's countdown did not fire: %r" % heard)
        self.assertLess(beeps[0], ticks[0], "the countdown arrived before the beep that starts it: %r" % heard)
        lines = self._room_lines(room)
        self.assertEqual(len(lines), 1, room.call_args_list)
        self.assertIn("stuck to {target_char}'s plate carrier beeps", lines[0]["template"])
        self.assertIn(self.char2, lines[0]["exclude"])

    def test_a_charge_in_the_operators_own_pocket_warns_the_operator_with_the_countdown(self):
        g = self._charge("own pocket charge", self.char1)
        with patch.object(CmdExplosives, "msg_room_identity") as room:
            out = self.call(CmdDetonate(), f"e-{g.id} with detonator") or ""
        self.assertIn("in your pocket beeps", out)
        self.assertIn("[6 seconds]", out)
        lines = self._room_lines(room)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["char_refs"], {"target_char": self.char1})
        self.assertIn(self.char1, lines[0]["exclude"])
        self.assertNotIn("seconds]", lines[0]["template"], "the plain viewer's copy carries the countdown")

    def test_detonate_all_warns_each_bearer(self):
        carried = self._charge("pocket charge", self.char2)
        vest = create_object("typeclasses.items.Item", key="plate carrier", location=self.char2)
        stuck = self._charge("sticky charge", vest)
        stuck.db.stuck_to_armor = vest
        with patch.object(CmdExplosives, "msg_room_identity") as room, patch.object(self.char2, "msg") as bearer:
            self.call(CmdDetonate(), "all with detonator")
        heard = [str(c) for c in bearer.call_args_list if "beeps" in str(c)]
        self.assertEqual(len(heard), 2, bearer.call_args_list)
        self.assertEqual(len(self._room_lines(room)), 2, room.call_args_list)
