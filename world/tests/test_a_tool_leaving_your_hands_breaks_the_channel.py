"""The channel primitive owns the tool problem; BLOCKED verbs all gate (#3376).

`drop can` mid-tag succeeded and the full tag still landed 103 seconds
later, paint deducted from a can on the floor. Eleven of the fifteen verbs
CHANNELED_ACTIONS_SPEC §2.2 declares BLOCKED never called
`refuse_if_channeling`, and the graffiti consumer privately trusted the can
it captured at start.

Owner ruling 2026-09-13: option A (finish the list) and make it GENERIC.
`begin_channel(..., tools=[...])` declares what an act needs on the actor;
`tool_left_hands` (from `release_slots` / `at_object_leave`) breaks the
channel the moment a tool leaves by any route; `_finish` re-validates.
Graffiti, solvent and surgery declare their tools.
"""
import inspect
from unittest import mock
from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from world import channeled as ch


class ToolBindingTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.can = create_object("typeclasses.items.Item", key="spray can", location=self.actor)
        self.done, self.broke = MagicMock(), MagicMock()
        self.delay = mock.patch.object(ch, "delay"); self.delay_mock = self.delay.start(); self.addCleanup(self.delay.stop)

    def begin(self, tools):
        ok = ch.begin_channel(self.actor, 10, "at the wall", self.done, self.broke, key="spraying", tools=tools)
        self.assertTrue(ok); return self.delay_mock.call_args.args[2:]   # (actor, token)

    def test_tool_leaving_possession_breaks_the_channel(self):
        self.begin([self.can])
        self.can.move_to(self.room1, quiet=True)          # the drop / give / theft route
        self.assertIsNone(ch.channel_of(self.actor), "channel survived the tool leaving")
        self.broke.assert_called_once(); self.done.assert_not_called()

    def test_tool_leaving_the_hands_breaks_the_channel(self):
        self.actor.wield_item(self.can, hand="right")
        self.begin([self.can])
        self.actor.unwield_item("right")                    # still in inventory, no longer in hand
        self.assertIsNone(ch.channel_of(self.actor), "channel survived the tool leaving the hand")
        self.broke.assert_called_once()

    def test_an_unrelated_object_leaving_does_not_break_it(self):
        other = create_object("typeclasses.items.Item", key="pebble", location=self.actor)
        self.begin([self.can])
        other.move_to(self.room1, quiet=True)
        self.assertIsNotNone(ch.channel_of(self.actor), "an unrelated item broke the channel")
        self.broke.assert_not_called()

    def test_finish_revalidates_a_tool_that_slipped_away(self):
        ghost = MagicMock(); ghost.location = None; ghost.id = 999999
        actor, token = self.begin([ghost])
        ch._finish(actor, token)
        self.done.assert_not_called(); self.broke.assert_called_once_with(1.0)

    def test_finish_completes_when_tools_are_still_held(self):
        actor, token = self.begin([self.can])
        ch._finish(actor, token)
        self.done.assert_called_once(); self.broke.assert_not_called()

    def test_consumers_declare_their_tools(self):
        from commands import CmdGraffiti
        from world.medical import procedures
        src = inspect.getsource(CmdGraffiti)
        self.assertIn("tools=[spray_can]", src); self.assertIn("tools=[solvent_can]", src)
        self.assertIn("tools=[kit]", inspect.getsource(procedures.start_procedure))


class BlockedVerbsGateTest(EvenniaCommandTest):
    """Every §2.2 BLOCKED verb refuses mid-channel with the 'stop first' line
    and leaves the channel running."""

    def setUp(self):
        super().setUp()
        p = mock.patch.object(ch, "delay"); p.start(); self.addCleanup(p.stop)
        ch.begin_channel(self.char1, 60, "at the wall", lambda: None, lambda f: None, key="spraying")
        assert ch.channel_of(self.char1)

    def _refused(self, cmd, args):
        out = self.call(cmd, args) or ""
        self.assertIn("busy", out.lower(), "%s %r was not refused: %r" % (type(cmd).__name__, args, out))
        self.assertIn("stop", out.lower())
        self.assertIsNotNone(ch.channel_of(self.char1), "%s ended the channel" % type(cmd).__name__)

    def test_inventory_verbs(self):
        from commands.CmdInventory import CmdUnwield, CmdGet, CmdDrop, CmdGive
        for cmd, args in ((CmdUnwield(), "x"), (CmdGet(), "x"), (CmdDrop(), "x"), (CmdGive(), "x to y")):
            self._refused(cmd, args)

    def test_clothing_verbs(self):
        from commands.CmdClothing import CmdWear, CmdRemove, CmdRollUp, CmdZip, CmdDress, CmdUndress
        for cmd, args in ((CmdWear(), "x"), (CmdRemove(), "x"), (CmdRollUp(), "x"), (CmdZip(), "x"), (CmdDress(), "x"), (CmdUndress(), "x")):
            self._refused(cmd, args)

    def test_fight_device_and_trade_verbs(self):
        from commands.CmdThrow import CmdThrow
        from commands.shop import CmdBuy
        from commands.combat.special_actions import CmdAim
        from commands.CmdGraffiti import CmdPress
        for cmd, args in ((CmdThrow(), "x at y"), (CmdBuy(), "x from y"), (CmdAim(), "north"), (CmdPress(), "x on y")):
            self._refused(cmd, args)
