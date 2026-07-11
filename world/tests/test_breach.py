"""Breach: sabotage/repair of breachable structures (masts).

Channel timing is world/channeled.py's tested concern; these tests fire
the captured callbacks directly and pin the state machine — the wreck/
mend round trip, the crime at commission, the shared-verb routing, and
that interruption lands nothing.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import commands.CmdBreach as breach


def _mast(intact=True, key="antenna mast"):
    mast = MagicMock()
    mast.key = key
    mast.aliases.all.return_value = ["mast"]
    mast.db = SimpleNamespace(
        breachable=True, intact=intact,
        desc="authored prose", sensory_contributions={"visual": "authored"},
        intact_desc=None, intact_sensory=None)
    return mast


def _caller(room_contents):
    caller = MagicMock()
    caller.location.contents = room_contents
    return caller


def _run_sabotage(caller):
    cmd = breach.CmdSabotage()
    cmd.caller = caller
    cmd.args = "mast"
    captured = {}

    def fake_begin(actor, duration, tell, on_complete, on_interrupt, key):
        captured.update(complete=on_complete, interrupt=on_interrupt,
                        duration=duration, key=key)
        return True

    with patch("world.channeled.begin_channel", side_effect=fake_begin), \
         patch.object(breach, "msg_room_identity"):
        cmd.func()
    return captured


class TestSabotage(TestCase):
    def test_wreck_round_trip_restores_authored_prose(self):
        mast = _mast()
        breach.wreck_structure(mast)
        self.assertIs(mast.db.intact, False)
        self.assertEqual(mast.db.desc, breach.WRECKED_DESC)
        self.assertEqual(mast.db.intact_desc, "authored prose")
        breach.mend_structure(mast)
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")
        self.assertEqual(mast.db.sensory_contributions,
                         {"visual": "authored"})

    def test_completion_wrecks_and_commits_the_crime(self):
        mast = _mast()
        caller = _caller([mast])
        captured = _run_sabotage(caller)
        self.assertEqual(captured["key"], "sabotaging")
        with patch("world.director.crime.report_crime") as crime, \
             patch.object(breach, "msg_room_identity"):
            captured["complete"]()
        self.assertIs(mast.db.intact, False)
        crime.assert_called_once_with("sabotage", caller.location,
                                      perp=caller)

    def test_interruption_lands_nothing(self):
        mast = _mast()
        caller = _caller([mast])
        captured = _run_sabotage(caller)
        with patch.object(breach, "msg_room_identity"):
            captured["interrupt"](0.9)
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")

    def test_already_wrecked_refuses(self):
        mast = _mast(intact=False)
        caller = _caller([mast])
        cmd = breach.CmdSabotage()
        cmd.caller = caller
        cmd.args = "mast"
        with patch("world.channeled.begin_channel") as begin:
            cmd.func()
        begin.assert_not_called()
        self.assertIn("already down", caller.msg.call_args.args[0])

    def test_non_breachable_room_finds_nothing(self):
        prop = MagicMock()
        prop.key = "antenna mast"
        prop.db = SimpleNamespace(breachable=None)
        caller = _caller([prop])
        self.assertIsNone(breach.find_breachable(caller, "mast"))


class TestSharedRepairVerb(TestCase):
    def test_no_breachable_match_yields_to_armor(self):
        caller = _caller([])
        self.assertFalse(breach.try_repair_structure(caller, "vest"))

    def test_wrecked_structure_claims_the_verb_and_mends(self):
        mast = _mast(intact=False)
        mast.db.intact_desc = "authored prose"
        mast.db.intact_sensory = {"visual": "authored"}
        caller = _caller([mast])
        captured = {}

        def fake_begin(actor, duration, tell, on_complete, on_interrupt, key):
            captured.update(complete=on_complete, key=key)
            return True

        with patch("world.channeled.begin_channel", side_effect=fake_begin), \
             patch.object(breach, "msg_room_identity"):
            handled = breach.try_repair_structure(caller, "mast")
        self.assertTrue(handled)
        self.assertEqual(captured["key"], "repairing")
        with patch.object(breach, "msg_room_identity"):
            captured["complete"]()
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")

    def test_intact_structure_reports_sound_without_channel(self):
        mast = _mast(intact=True)
        caller = _caller([mast])
        with patch("world.channeled.begin_channel") as begin:
            handled = breach.try_repair_structure(caller, "mast")
        self.assertTrue(handled)
        begin.assert_not_called()
        self.assertIn("standing and sound", caller.msg.call_args.args[0])
