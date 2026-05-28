"""Unit tests for :class:`commands.forensics.CmdAutopsy` (PR-E + PR #186).

Exercises the command surface end-to-end with lightweight fakes so no
Evennia DB is required.  The command itself is thin glue over
:mod:`world.forensics`; these tests focus on the *contract* layer:

* Usage / argument handling.
* Non-corpse target rejection.
* Skeletal-corpse short-circuit (PR #186).
* Cache-hit silent re-render (per PR-E scope lock #4).
* Recognition-memory name surfacing *only* when the looker holds the
  revealed UID (regression: command must never auto-assign names).
* Room broadcast routes through :func:`world.identity_utils.msg_room_identity`.
* Five-section report assertions (ToD bucket, cause, wounds, organ
  status including absent-on-harvested/severed).

To bypass ``isinstance(target, Corpse)`` without patching the builtin
(which causes infinite recursion against mock.call internals), we
substitute the ``commands.forensics.Corpse`` symbol with a stand-in
base class that our fake corpse inherits from, then patch it in for
the duration of the test.

Run via::

    evennia test world.tests.test_cmd_autopsy
"""

from __future__ import annotations

import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdAutopsy
from world.combat.constants import (
    AUTOPSY_DC_BASIC,
    AUTOPSY_TIME_BUCKETS,
    CORPSE_DECAY_EARLY,
)
from world.forensics import RecognitionResult


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _DB:
    """Bare attribute holder mimicking ``obj.db``."""


class _FakeRoom:
    def __init__(self):
        self.contents = []


class _CorpseStandIn:
    """Stand-in for :class:`typeclasses.corpse.Corpse` (isinstance target)."""


class _FakeCorpse(_CorpseStandIn):
    """Minimal corpse surface the command needs."""

    def __init__(
        self,
        *,
        key="the corpse of Jorge",
        display=None,
        decay_stage="fresh",
        snapshot=None,
        removed_organs=None,
        severed_locations=None,
        wounds=None,
        death_cause="multiple gunshot wounds",
        death_time=None,
    ):
        self.key = key
        self.db = _DB()
        self.db.signature_at_death = (
            "sleeve-1", "tall", "lean", "hooded", ("balaclava",),
        )
        self.db.apparent_uid_at_death = "abc123"
        self.db.forensic_recognition_cache = None
        self.db.death_cause = death_cause
        self.db.death_time = (
            death_time if death_time is not None else time.time() - 60
        )
        self.db.wounds_at_death = wounds or []
        self.db.removed_organs = removed_organs or []
        self.db.severed_locations = severed_locations or []
        self._display = display or key
        self._decay_stage = decay_stage
        self._snapshot = snapshot

    def get_display_name(self, looker=None, **kwargs):  # noqa: D401
        del looker, kwargs
        return self._display

    def get_decay_stage(self):
        return self._decay_stage

    def get_medical_snapshot(self):
        return self._snapshot


def _make_caller(*, key="Alice", dbref="#42", memory=None, location=None):
    caller = MagicMock()
    caller.key = key
    caller.dbref = dbref
    caller.location = location or _FakeRoom()
    caller.recognition_memory = memory or {}
    caller.msg = MagicMock()
    caller.search = MagicMock()
    return caller


def _make_cmd(*, caller, target, args="corpse", switches=()):
    cmd = CmdAutopsy()
    cmd.caller = caller
    cmd.args = " " + args
    cmd.switches = list(switches)
    caller.search.return_value = target
    return cmd


def _patch_corpse():
    """Patch the command-module's Corpse symbol with our stand-in."""
    return patch.object(cmd_module, "Corpse", _CorpseStandIn)


# ---------------------------------------------------------------------
# Arg handling
# ---------------------------------------------------------------------


class TestCmdAutopsyArgs(TestCase):
    def test_no_args_prints_usage(self):
        caller = _make_caller()
        cmd = CmdAutopsy()
        cmd.caller = caller
        cmd.args = ""
        cmd.switches = []
        cmd.func()
        caller.msg.assert_called_once()
        self.assertIn("Usage:", caller.msg.call_args[0][0])
        caller.search.assert_not_called()

    def test_search_miss_returns_silently(self):
        """Evennia's ``caller.search`` already messages on miss."""
        caller = _make_caller()
        caller.search.return_value = None
        cmd = CmdAutopsy()
        cmd.caller = caller
        cmd.args = " ghost"
        cmd.switches = []
        cmd.func()
        caller.msg.assert_not_called()


# ---------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------


class TestCmdAutopsyTargetValidation(TestCase):
    def test_non_corpse_rejected(self):
        caller = _make_caller()
        not_a_corpse = object()  # NOT a Corpse instance
        caller.search.return_value = not_a_corpse
        cmd = CmdAutopsy()
        cmd.caller = caller
        cmd.args = " rock"
        cmd.switches = []
        with _patch_corpse():
            cmd.func()
        caller.msg.assert_called_once()
        self.assertIn("corpse", caller.msg.call_args[0][0].lower())

    def test_skeletal_corpse_short_circuits(self):
        """Skeletal corpses refuse autopsy with a dedicated message."""
        caller = _make_caller()
        corpse = _FakeCorpse(decay_stage="skeletal")
        cmd = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity") as broadcast, \
                patch("world.combat.dice.roll_stat") as mocked_roll:
            cmd.func()
        mocked_roll.assert_not_called()
        broadcast.assert_not_called()
        out = caller.msg.call_args[0][0]
        self.assertIn("decomposed", out.lower())


# ---------------------------------------------------------------------
# Single-tier dispatch (PR #186 dropped /deep)
# ---------------------------------------------------------------------


class TestCmdAutopsyDispatch(TestCase):
    def _run(self, *, switches=(), roll=99, corpse=None):
        caller = _make_caller()
        corpse = corpse or _FakeCorpse()
        cmd = _make_cmd(caller=caller, target=corpse, switches=switches)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity") as broadcast, \
                patch("world.combat.dice.roll_stat", return_value=roll):
            cmd.func()
        return caller, corpse, broadcast

    def test_unified_report_includes_essentials(self):
        """No more /deep gating — essentials always render on success."""
        caller, _, broadcast = self._run()
        self.assertTrue(caller.msg.called)
        rendered = caller.msg.call_args[0][0]
        self.assertIn("Worn essentials", rendered)
        broadcast.assert_called_once()
        template = broadcast.call_args.kwargs["template"]
        self.assertIn("examines", template)
        self.assertNotIn("deep autopsy", template)

    def test_dc_basic_constant_low_enough_to_tune(self):
        """Sanity: AUTOPSY_DC_BASIC remains reachable by base Intellect."""
        self.assertGreater(AUTOPSY_DC_BASIC, 0)
        self.assertLess(AUTOPSY_DC_BASIC, 10)


# ---------------------------------------------------------------------
# Report sections (PR #186)
# ---------------------------------------------------------------------


class TestCmdAutopsyReportSections(TestCase):
    def _run(self, *, corpse):
        caller = _make_caller()
        cmd = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity"), \
                patch("world.combat.dice.roll_stat", return_value=99):
            cmd.func()
        return caller.msg.call_args[0][0]

    def test_fresh_corpse_emits_recent_time_of_death_bucket(self):
        corpse = _FakeCorpse(death_time=time.time() - 30)
        rendered = self._run(corpse=corpse)
        self.assertIn(AUTOPSY_TIME_BUCKETS[0][1], rendered)

    def test_older_corpse_falls_into_later_bucket(self):
        corpse = _FakeCorpse(death_time=time.time() - CORPSE_DECAY_EARLY - 1)
        rendered = self._run(corpse=corpse)
        self.assertIn(AUTOPSY_TIME_BUCKETS[2][1], rendered)

    def test_cause_of_death_rendered(self):
        corpse = _FakeCorpse(death_cause="blunt force trauma")
        rendered = self._run(corpse=corpse)
        self.assertIn("blunt force trauma", rendered)

    def test_no_snapshot_emits_pre_mortem_unavailable_marker(self):
        corpse = _FakeCorpse(snapshot=None)
        rendered = self._run(corpse=corpse)
        self.assertIn("No internal examination possible", rendered)

    def test_organ_status_intact_damaged_destroyed(self):
        snapshot = {
            "organs": {
                "heart": {"current_hp": 10, "max_hp": 10, "container": "torso"},
                "liver": {"current_hp": 2, "max_hp": 10, "container": "torso"},
                "left_lung": {
                    "current_hp": 0, "max_hp": 10, "container": "torso",
                },
            }
        }
        corpse = _FakeCorpse(snapshot=snapshot)
        rendered = self._run(corpse=corpse)
        self.assertIn("heart: intact", rendered)
        self.assertIn("liver: damaged", rendered)
        self.assertIn("left_lung: destroyed", rendered)

    def test_removed_organ_renders_as_absent(self):
        snapshot = {
            "organs": {
                "heart": {"current_hp": 10, "max_hp": 10, "container": "torso"},
            }
        }
        corpse = _FakeCorpse(snapshot=snapshot, removed_organs=["heart"])
        rendered = self._run(corpse=corpse)
        self.assertIn("heart: absent", rendered)

    def test_severed_location_marks_contained_organs_absent(self):
        snapshot = {
            "organs": {
                "left_hand_bones": {
                    "current_hp": 8, "max_hp": 8, "container": "left_arm",
                },
            }
        }
        corpse = _FakeCorpse(
            snapshot=snapshot, severed_locations=["left_arm"],
        )
        rendered = self._run(corpse=corpse)
        self.assertIn("left_hand_bones: absent", rendered)


# ---------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------


class TestCmdAutopsyFailure(TestCase):
    def test_failed_roll_emits_inconclusive_message(self):
        caller = _make_caller()
        corpse = _FakeCorpse()
        cmd = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity"), \
                patch("world.combat.dice.roll_stat", return_value=0):
            cmd.func()
        out = caller.msg.call_args[0][0]
        self.assertIn("cannot determine", out)


# ---------------------------------------------------------------------
# Cache replay
# ---------------------------------------------------------------------


class TestCmdAutopsyCacheReplay(TestCase):
    def test_second_call_replays_without_reroll(self):
        caller = _make_caller()
        corpse = _FakeCorpse()
        cmd1 = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity"), \
                patch("world.combat.dice.roll_stat", return_value=99):
            cmd1.func()
        first_render = caller.msg.call_args[0][0]
        caller.msg.reset_mock()

        cmd2 = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity"), \
                patch(
                    "world.combat.dice.roll_stat", return_value=0,
                ) as mocked_roll:
            cmd2.func()
            mocked_roll.assert_not_called()
        second_render = caller.msg.call_args[0][0]
        # Cache hit: identical output, no reroll.
        self.assertEqual(first_render, second_render)


# ---------------------------------------------------------------------
# Name-disclosure contract
# ---------------------------------------------------------------------


class TestCmdAutopsyNameDisclosure(TestCase):
    def _run_with_result(self, *, memory, result):
        caller = _make_caller(memory=memory)
        corpse = _FakeCorpse()
        cmd = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(cmd_module, "msg_room_identity"), \
                patch.object(
                    cmd_module, "attempt_forensic_recognition",
                    return_value=result,
                ):
            cmd.func()
        return caller.msg.call_args[0][0]

    def test_no_name_surfaced_when_uid_absent_from_memory(self):
        result = RecognitionResult(
            success=True, revealed_uid="abc123", from_cache=False,
        )
        rendered = self._run_with_result(memory={}, result=result)
        self.assertNotIn("remains are those of", rendered)

    def test_name_surfaces_when_uid_present_in_memory(self):
        memory = {"abc123": {"assigned_name": "Jorge Jackson"}}
        result = RecognitionResult(
            success=True, revealed_uid="abc123", from_cache=False,
        )
        rendered = self._run_with_result(memory=memory, result=result)
        self.assertIn("Jorge Jackson", rendered)
        self.assertIn("remains are those of", rendered)

    def test_no_name_when_uid_in_memory_but_no_assigned_name(self):
        """Memory entry without ``assigned_name`` must not leak a name."""
        memory = {"abc123": {"sdesc": "the hooded one"}}
        result = RecognitionResult(
            success=True, revealed_uid="abc123", from_cache=False,
        )
        rendered = self._run_with_result(memory=memory, result=result)
        self.assertNotIn("remains are those of", rendered)


# ---------------------------------------------------------------------
# Room broadcast
# ---------------------------------------------------------------------


class TestCmdAutopsyBroadcast(TestCase):
    def test_broadcast_excludes_caller_and_uses_per_observer_helper(self):
        caller = _make_caller()
        corpse = _FakeCorpse()
        cmd = _make_cmd(caller=caller, target=corpse)
        with _patch_corpse(), \
                patch.object(
                    cmd_module, "msg_room_identity",
                ) as broadcast, \
                patch("world.combat.dice.roll_stat", return_value=99):
            cmd.func()
        broadcast.assert_called_once()
        kwargs = broadcast.call_args.kwargs
        self.assertEqual(kwargs["location"], caller.location)
        self.assertEqual(kwargs["exclude"], [caller])
        self.assertIn("actor", kwargs["char_refs"])
        self.assertIn("corpse", kwargs["char_refs"])
        self.assertIs(kwargs["char_refs"]["actor"], caller)
        self.assertIs(kwargs["char_refs"]["corpse"], corpse)

