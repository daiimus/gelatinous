"""Channeled actions (world/channeled.py + graffiti consumer) —
CHANNELED_ACTIONS_SPEC.

The stillness primitive: duration + tell + on_complete/on_interrupt(frac).
The taxonomy: FREE never touches it, BLOCKED verbs refuse with 'stop first',
BREAKING seams (damage/grapple/enrollment/collapse/forced move) land the
partial. Graffiti: per-letter timer, interrupted tags land with ellipsis,
vandalism finally reports.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.channeled as ch
from world.channeled import (
    begin_channel, interrupt_channel, is_channeling, refuse_if_channeling,
    stop_channel,
)


def _actor():
    a = MagicMock()
    a.ndb = SimpleNamespace(channel=None)
    a.override_place = None
    return a


class TestPrimitive(TestCase):
    def test_begin_sets_tell_and_schedules(self):
        a = _actor()
        with patch.object(ch, "delay") as d:
            ok = begin_channel(a, 10, "at the wall", lambda: None,
                               lambda f: None, key="spraying")
        self.assertTrue(ok)
        self.assertEqual(is_channeling(a), "spraying")
        self.assertEqual(a.override_place, "at the wall")
        d.assert_called_once()

    def test_second_channel_refused(self):
        a = _actor()
        with patch.object(ch, "delay"):
            begin_channel(a, 10, "t", lambda: None, lambda f: None, key="spraying")
            ok = begin_channel(a, 5, "t2", lambda: None, lambda f: None)
        self.assertFalse(ok)
        self.assertIn("busy spraying", a.msg.call_args.args[0])

    def test_completion_fires_and_restores_tell(self):
        a = _actor()
        a.override_place = "leaning on the bar."
        done = MagicMock()
        with patch.object(ch, "delay") as d:
            begin_channel(a, 10, "tagging", done, lambda f: None)
        # fire the scheduled completion with the real token
        _, args = d.call_args.args[1], d.call_args.args[2:]
        ch._finish(*args)
        done.assert_called_once()
        self.assertIsNone(is_channeling(a))
        self.assertEqual(a.override_place, "leaning on the bar.")

    def test_interrupt_lands_fraction_and_stale_timer_noops(self):
        a = _actor()
        got = {}
        with patch.object(ch, "delay") as d, \
                patch.object(ch, "monotonic", side_effect=[100.0, 104.0]):
            begin_channel(a, 10, "t", MagicMock(),
                          lambda f: got.update(frac=f))
            interrupt_channel(a)
        self.assertAlmostEqual(got["frac"], 0.4)
        self.assertIsNone(is_channeling(a))
        # the pending completion is now stale: firing it must do nothing
        args = d.call_args.args[2:]
        ch._finish(*args)   # token mismatch -> no-op, no crash

    def test_stop_is_voluntary_interrupt(self):
        a = _actor()
        got = {}
        with patch.object(ch, "delay"), \
                patch.object(ch, "monotonic", side_effect=[100.0, 101.0]):
            begin_channel(a, 10, "t", MagicMock(), lambda f: got.update(f=f))
            self.assertTrue(stop_channel(a))
        self.assertIn("f", got)

    def test_interrupt_without_channel_is_free(self):
        self.assertFalse(interrupt_channel(_actor()))

    def test_refuse_gate_strict_on_mocks(self):
        # The MagicMock trap: a bare mock actor must NOT read as channeling.
        self.assertFalse(refuse_if_channeling(MagicMock()))

    def test_consumer_exception_never_leaks(self):
        a = _actor()
        with patch.object(ch, "delay") as d:
            begin_channel(a, 10, "t", MagicMock(side_effect=RuntimeError),
                          lambda f: None)
        ch._finish(*d.call_args.args[2:])   # must not raise
        self.assertIsNone(is_channeling(a))


class TestGraffitiChannel(TestCase):
    def _cmd(self):
        from commands.CmdGraffiti import CmdGraffiti
        cmd = CmdGraffiti()
        caller = MagicMock()
        caller.ndb = SimpleNamespace(channel=None)
        caller.override_place = None
        cmd.caller = caller
        return cmd, caller

    def _can(self, paint=256, color="red"):
        can = MagicMock()
        can.db.aerosol_level = paint
        can.db.current_color = color
        can.get_display_name = lambda looker=None: "a battered spray can"
        return can

    def test_spray_channels_with_per_letter_duration(self):
        cmd, caller = self._cmd()
        can = self._can()
        with patch.object(ch, "delay") as d, \
                patch("commands.CmdGraffiti.msg_room_identity"):
            cmd._handle_spray_paint_with_spraypaint(can, "KRAKEN RULES")
        self.assertEqual(is_channeling(caller), "spraying")
        duration = d.call_args.args[0]
        self.assertAlmostEqual(duration, 3.0 + len("KRAKEN RULES") * 1.0)
        can.use_paint.assert_not_called()      # cost deducts at RESOLUTION

    def test_completion_lands_full_tag_and_reports_vandalism(self):
        cmd, caller = self._cmd()
        can = self._can()
        with patch.object(ch, "delay") as d, \
                patch("commands.CmdGraffiti.msg_room_identity"), \
                patch("commands.CmdGraffiti.create_object") as co, \
                patch("world.director.crime.report_crime") as report:
            caller.location.contents = []
            cmd._handle_spray_paint_with_spraypaint(can, "KRAKEN")
            ch._finish(*d.call_args.args[2:])
        can.use_paint.assert_called_once_with(6)
        graffiti = co.return_value
        graffiti.add_graffiti.assert_called_once()
        self.assertEqual(graffiti.add_graffiti.call_args.args[0], "KRAKEN")
        report.assert_called_once()
        self.assertEqual(report.call_args.args[0], "vandalism")

    def test_interruption_lands_partial_with_ellipsis(self):
        cmd, caller = self._cmd()
        can = self._can()
        with patch.object(ch, "delay"), \
                patch("commands.CmdGraffiti.msg_room_identity"), \
                patch("commands.CmdGraffiti.create_object") as co, \
                patch("world.director.crime.report_crime") as report, \
                patch.object(ch, "monotonic", side_effect=[100.0, 107.0]):
            caller.location.contents = []
            # 10 letters -> duration 13s; interrupted at 7s = 4 letters done
            cmd._handle_spray_paint_with_spraypaint(can, "KRAKENRULE")
            interrupt_channel(caller)
        landed = co.return_value.add_graffiti.call_args.args[0]
        self.assertEqual(landed, "KRAK...")
        can.use_paint.assert_called_once_with(4)   # pro-rata, ellipsis free
        report.assert_called_once()                # caught mid-crime still reports

    def test_interruption_before_first_letter_lands_nothing(self):
        cmd, caller = self._cmd()
        can = self._can()
        with patch.object(ch, "delay"), \
                patch("commands.CmdGraffiti.msg_room_identity"), \
                patch("commands.CmdGraffiti.create_object") as co, \
                patch.object(ch, "monotonic", side_effect=[100.0, 101.0]):
            cmd._handle_spray_paint_with_spraypaint(can, "KRAKEN")
            interrupt_channel(caller)      # 1s in: still shaking the can
        co.assert_not_called()
        can.use_paint.assert_not_called()


class TestCleaningChannel(TestCase):
    """Solvent cleaning — the second consumer: per-unit duration, graffiti
    scrubs pro-rata on interruption, blood needs the full dwell."""

    def _cmd(self):
        from commands.CmdGraffiti import CmdGraffiti
        cmd = CmdGraffiti()
        caller = MagicMock()
        caller.ndb = SimpleNamespace(channel=None)
        caller.override_place = None
        cmd.caller = caller
        return cmd, caller

    def _solvent(self, level=256):
        can = MagicMock()
        can.db.aerosol_level = level
        can.db.quality = None
        can.get_display_name = lambda looker=None: "a solvent can"
        return can

    def _graffiti(self):
        from typeclasses.objects import GraffitiObject
        g = MagicMock(spec=GraffitiObject)
        g.has_graffiti.return_value = True
        g.db = SimpleNamespace(is_blood_pool=False)
        g.remove_random_characters.return_value = 5
        return g

    def test_clean_channels_per_unit(self):
        cmd, caller = self._cmd()
        can = self._solvent()
        wall = self._graffiti()
        caller.location.contents = [wall]
        with patch.object(ch, "delay") as d, \
                patch("commands.CmdGraffiti.msg_room_identity"):
            cmd._handle_clean_with_solvent(can)
        self.assertEqual(is_channeling(caller), "cleaning")
        duration = d.call_args.args[0]
        self.assertAlmostEqual(duration, 3.0 + 10 * 1.0)   # 10-unit scrub
        can.use_solvent.assert_not_called()    # cost deducts at RESOLUTION

    def test_completion_scrubs_and_spends(self):
        cmd, caller = self._cmd()
        can = self._solvent()
        wall = self._graffiti()
        caller.location.contents = [wall]
        with patch.object(ch, "delay") as d, \
                patch("commands.CmdGraffiti.msg_room_identity"), \
                patch("commands.CmdGraffiti.delay"):
            cmd._handle_clean_with_solvent(can)
            ch._finish(*d.call_args.args[2:])
        can.use_solvent.assert_called_once_with(10)
        wall.remove_random_characters.assert_called_once_with(10)

    def test_interrupt_scrubs_pro_rata_no_blood(self):
        from typeclasses.objects import BloodPool
        cmd, caller = self._cmd()
        can = self._solvent()
        wall = self._graffiti()
        blood = MagicMock(spec=BloodPool)
        blood.db = SimpleNamespace(is_blood_pool=True,
                                   bleeding_incidents=[1])
        caller.location.contents = [wall, blood]
        with patch.object(ch, "delay"), \
                patch("commands.CmdGraffiti.msg_room_identity"), \
                patch("commands.CmdGraffiti.delay"), \
                patch.object(ch, "monotonic", side_effect=[100.0, 107.0]):
            cmd._handle_clean_with_solvent(can)
            interrupt_channel(caller)          # 7s in: 4 units worked
        can.use_solvent.assert_called_once_with(4)
        wall.remove_random_characters.assert_called_once_with(4)
        blood.clean_with_solvent.assert_not_called()   # needs full dwell

    def test_nothing_to_clean_never_channels(self):
        cmd, caller = self._cmd()
        can = self._solvent()
        caller.location.contents = []
        with patch.object(ch, "delay") as d:
            cmd._handle_clean_with_solvent(can)
        d.assert_not_called()
        self.assertIsNone(is_channeling(caller))
        self.assertIn("nothing here to clean",
                      caller.msg.call_args.args[0])


class TestTaxonomyWiring(TestCase):
    """The BLOCKED gates and BREAKING seams actually call the primitive."""

    def _busy(self):
        a = MagicMock()
        a.ndb = SimpleNamespace(channel=None)
        a.override_place = None
        with patch.object(ch, "delay"):
            begin_channel(a, 60, "t", MagicMock(), MagicMock(),
                          key="spraying")
        return a

    def test_wield_blocked_while_channeling(self):
        from commands.CmdInventory import CmdWield
        cmd = CmdWield()
        cmd.caller = self._busy()
        cmd.args = "shiv"
        cmd.func()
        self.assertIn("busy spraying", cmd.caller.msg.call_args.args[0])
        self.assertEqual(is_channeling(cmd.caller), "spraying")  # intact

    def test_xmit_blocked_while_channeling(self):
        from commands.CmdRadio import CmdTransmit
        cmd = CmdTransmit()
        cmd.caller = self._busy()
        cmd.args = "hello"
        cmd.parse()
        cmd.func()
        self.assertIn("busy spraying", cmd.caller.msg.call_args.args[0])

    def test_combat_enrollment_breaks_channel(self):
        from world.combat.utils import add_combatant
        a = self._busy()
        try:
            add_combatant(MagicMock(), a)
        except Exception:  # noqa: BLE001 — mock handler dies later; fine
            pass
        self.assertIsNone(is_channeling(a))   # the channel broke FIRST

    def test_stop_verb_aborts_channel(self):
        from commands.combat.core_actions import CmdStop
        a = self._busy()
        cmd = CmdStop()
        cmd.caller = a
        cmd.args = ""
        cmd.func()
        self.assertIsNone(is_channeling(a))
