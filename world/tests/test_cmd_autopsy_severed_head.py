"""Unit tests for ``CmdAutopsy`` widened to SeveredHead (PR #196).

PR-C widens the ``CmdAutopsy`` isinstance gate from ``Corpse`` only
to ``(Corpse, SeveredHead)`` so a disembodied head can be examined
via the same forensic surface as a corpse.  These tests lock the
widened gate and confirm the trimmed head-container snapshot flows
through the same renderer as a full-body autopsy.

The pattern mirrors :mod:`world.tests.test_cmd_autopsy`: we patch the
``commands.forensics.Corpse`` *and* ``SeveredHead`` symbols with
stand-in base classes, then point our fakes at those stand-ins so
the ``isinstance(target, (Corpse, SeveredHead))`` gate accepts them
without spinning up Evennia typeclass instances.

Run via::

    evennia test world.tests.test_cmd_autopsy_severed_head
"""

from __future__ import annotations

import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdAutopsy


class _DB:
    pass


class _FakeRoom:
    def __init__(self):
        self.contents = []


class _CorpseStandIn:
    pass


class _SeveredHeadStandIn:
    pass


class _FakeSeveredHead(_SeveredHeadStandIn):
    """Mirrors the surface CmdAutopsy / render_forensic_report read.

    Field defaults match the post-``configure_from_sever`` shape
    laid down by :func:`typeclasses.items.apply_severed_head_overlay`:
    trimmed snapshot, blanked body-wide fields, no wounds list.
    """

    def __init__(
        self,
        *,
        key="the severed head of Jorge",
        display=None,
        decay_stage="fresh",
        snapshot=None,
        removed_organs=None,
        death_cause="multiple gunshot wounds",
        death_time=None,
    ):
        self.key = key
        self.db = _DB()
        self.db.signature_at_death = (
            "sleeve-9", "tall", "lean", "hooded", ("balaclava",),
        )
        self.db.apparent_uid_at_death = "head-xyz"
        self.db.forensic_recognition_cache = None
        self.db.death_cause = death_cause
        self.db.death_time = (
            death_time if death_time is not None else time.time() - 60
        )
        # SeveredHead intentionally has no wounds_at_death; the
        # renderer's defensive ``getattr`` returns None → empty list.
        self.db.removed_organs = removed_organs or []
        self.db.severed_locations = []  # heads are terminal
        self._display = display or key
        self._decay_stage = decay_stage
        self._snapshot = snapshot

    def get_display_name(self, looker=None, **kwargs):
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


def _make_cmd(*, caller, target, args="head", switches=()):
    cmd = CmdAutopsy()
    cmd.caller = caller
    cmd.args = " " + args
    cmd.switches = list(switches)
    caller.search.return_value = target
    return cmd


def _patch_gate():
    """Patch both Corpse and SeveredHead symbols on the command module."""
    return patch.multiple(
        cmd_module,
        Corpse=_CorpseStandIn,
        SeveredHead=_SeveredHeadStandIn,
    )


def _head_snapshot():
    def org(hp, container="head"):
        return {"current_hp": hp, "max_hp": hp, "container": container}
    return {
        "organs": {
            "brain": org(10),
            "left_eye": org(10),
            "right_eye": org(10),
        },
        "conditions": [],
        "blood_level": None,
        "pain_level": None,
        "consciousness": None,
    }


class TestCmdAutopsyAcceptsSeveredHead(TestCase):
    """The widened isinstance gate accepts SeveredHead."""

    def _run(self, *, head=None, roll=99):
        caller = _make_caller()
        head = head or _FakeSeveredHead(snapshot=_head_snapshot())
        cmd = _make_cmd(caller=caller, target=head)
        with _patch_gate(), \
                patch.object(cmd_module, "msg_room_identity") as broadcast, \
                patch("world.combat.dice.roll_stat", return_value=roll):
            cmd.func()
        return caller, head, broadcast

    def test_severed_head_passes_gate(self):
        """A SeveredHead is no longer rejected with the corpse-only message."""
        caller, _, broadcast = self._run()
        # Successful autopsy renders the standard report sections.
        rendered = caller.msg.call_args[0][0]
        self.assertNotIn("can only perform", rendered)
        self.assertIn("Worn essentials", rendered)
        broadcast.assert_called_once()

    def test_organ_section_shows_head_container_only(self):
        caller, _, _ = self._run()
        rendered = caller.msg.call_args[0][0]
        self.assertIn("brain: intact", rendered)
        self.assertIn("left_eye: intact", rendered)
        self.assertIn("right_eye: intact", rendered)
        # Non-head organs are not present in the trimmed snapshot.
        self.assertNotIn("heart", rendered)
        self.assertNotIn("liver", rendered)

    def test_cause_of_death_carried_through(self):
        head = _FakeSeveredHead(
            snapshot=_head_snapshot(), death_cause="decapitation",
        )
        caller, _, _ = self._run(head=head)
        rendered = caller.msg.call_args[0][0]
        self.assertIn("decapitation", rendered)

    def test_removed_organ_renders_as_absent_on_head(self):
        head = _FakeSeveredHead(
            snapshot=_head_snapshot(), removed_organs=["brain"],
        )
        caller, _, _ = self._run(head=head)
        rendered = caller.msg.call_args[0][0]
        self.assertIn("brain: absent", rendered)

    def test_skeletal_head_short_circuits(self):
        head = _FakeSeveredHead(decay_stage="skeletal")
        caller, _, broadcast = self._run(head=head)
        broadcast.assert_not_called()
        out = caller.msg.call_args[0][0]
        self.assertIn("decomposed", out.lower())


class TestCmdAutopsyStillRejectsArbitrary(TestCase):
    """Widening must not allow arbitrary non-forensic objects through."""

    def test_plain_object_still_rejected(self):
        caller = _make_caller()
        not_a_remain = object()
        caller.search.return_value = not_a_remain
        cmd = CmdAutopsy()
        cmd.caller = caller
        cmd.args = " rock"
        cmd.switches = []
        with _patch_gate():
            cmd.func()
        caller.msg.assert_called_once()
        # Updated message mentions both surfaces.
        msg = caller.msg.call_args[0][0].lower()
        self.assertIn("corpse", msg)
        self.assertIn("severed head", msg)
