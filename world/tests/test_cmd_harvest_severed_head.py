"""Unit tests for ``CmdHarvest`` widened to SeveredHead (PR #196).

PR-C widens the ``CmdHarvest`` isinstance gate from ``Corpse`` only
to ``(Corpse, SeveredHead)`` so head-container organs (brain, eyes,
ears, …) can be harvested from a disembodied head with the same
flow as from a full corpse.

The pattern mirrors :mod:`world.tests.test_cmd_harvest`: we patch the
``commands.forensics.Corpse`` *and* ``SeveredHead`` symbols with
stand-in base classes, then point our fakes at those stand-ins.

Run via::

    evennia test world.tests.test_cmd_harvest_severed_head
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdHarvest


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
    """Mirrors the surface CmdHarvest reads off a SeveredHead.

    Matches the post-``configure_from_sever`` shape: trimmed snapshot
    containing only head-container organs, empty ``severed_locations``
    (heads are terminal), ``removed_organs`` carry-forward already
    applied.
    """

    def __init__(
        self,
        *,
        key="the severed head of Jorge",
        display=None,
        decay_stage="fresh",
        snapshot=None,
        removed_organs=None,
        dbref="#202",
    ):
        self.key = key
        self.dbref = dbref
        self.db = _DB()
        self.db.signature_at_death = (
            "sleeve-9", "tall", "lean", "hooded", ("balaclava",),
        )
        self.db.apparent_uid_at_death = "head-xyz"
        self.db.medical_state_at_death = snapshot
        self.db.removed_organs = list(removed_organs or ())
        self.db.severed_locations = []
        self._display = display or key
        self._decay_stage = decay_stage

    def get_display_name(self, looker=None, **kwargs):
        del looker, kwargs
        return self._display

    def get_decay_stage(self):
        return self._decay_stage

    def get_medical_snapshot(self):
        return self.db.medical_state_at_death


def _head_snapshot(*, brain_hp=10, left_eye_hp=10, right_eye_hp=10):
    """Trimmed head-container snapshot (mirrors apply_severed_head_overlay)."""
    return {
        "organs": {
            "brain": {
                "current_hp": brain_hp, "max_hp": 10, "container": "head",
            },
            "left_eye": {
                "current_hp": left_eye_hp, "max_hp": 10, "container": "head",
            },
            "right_eye": {
                "current_hp": right_eye_hp, "max_hp": 10, "container": "head",
            },
        },
        "conditions": [],
        "blood_level": None,
        "pain_level": None,
        "consciousness": None,
    }


def _make_caller(*, key="Alice", dbref="#42", location=None):
    caller = MagicMock()
    caller.key = key
    caller.dbref = dbref
    caller.location = location or _FakeRoom()
    caller.recognition_memory = {}
    caller.msg = MagicMock()
    caller.search = MagicMock()
    caller.motorics = 10
    return caller


def _make_cmd(*, caller, args):
    cmd = CmdHarvest()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = ()
    return cmd


class CmdHarvestSeveredHeadTests(TestCase):
    def setUp(self):
        self._patcher = patch.multiple(
            cmd_module,
            Corpse=_CorpseStandIn,
            SeveredHead=_SeveredHeadStandIn,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_severed_head_passes_isinstance_gate(self):
        """Ambiguous form on a head lists head-container organs."""
        caller = _make_caller()
        head = _FakeSeveredHead(snapshot=_head_snapshot())
        caller.search.return_value = head
        _make_cmd(caller=caller, args="head").func()
        msg = caller.msg.call_args[0][0]
        self.assertNotIn("can only harvest", msg)
        self.assertIn("brain", msg)
        self.assertIn("left eye", msg)
        self.assertIn("right eye", msg)

    def test_already_removed_head_organ_refused(self):
        """Head-organ harvest respects carry-forward ``removed_organs``."""
        caller = _make_caller()
        head = _FakeSeveredHead(
            snapshot=_head_snapshot(), removed_organs=["brain"],
        )
        caller.search.return_value = head
        _make_cmd(caller=caller, args="brain from head").func()
        msg = caller.msg.call_args[0][0].lower()
        self.assertTrue(
            "already" in msg or "no brain" in msg,
            f"unexpected refusal message: {msg!r}",
        )

    def test_non_head_organ_not_present_on_head(self):
        """A non-head organ name finds nothing on the trimmed snapshot."""
        caller = _make_caller()
        head = _FakeSeveredHead(snapshot=_head_snapshot())
        caller.search.return_value = head
        _make_cmd(caller=caller, args="heart from head").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("no heart", msg)

    def test_successful_brain_harvest_spawns_organ(self):
        """Success: ``create_object`` called and snapshot mutated."""
        caller = _make_caller()
        head = _FakeSeveredHead(snapshot=_head_snapshot())
        caller.search.return_value = head
        with patch.object(cmd_module, "create_object") as mock_create, \
                patch.object(cmd_module, "msg_room_identity"), \
                patch.object(cmd_module, "roll_stat", return_value=99):
            mock_create.return_value = MagicMock()
            _make_cmd(caller=caller, args="brain from head").func()
        mock_create.assert_called_once()
        self.assertIn("brain", head.db.removed_organs)

    def test_skeletal_head_short_circuits_harvest(self):
        caller = _make_caller()
        head = _FakeSeveredHead(
            decay_stage="skeletal", snapshot=_head_snapshot(),
        )
        caller.search.return_value = head
        _make_cmd(caller=caller, args="brain from head").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("decomposed", msg)

    def test_no_snapshot_head_refuses_harvest(self):
        """A SeveredHead without a snapshot (legacy) refuses harvest."""
        caller = _make_caller()
        head = _FakeSeveredHead(snapshot=None)
        caller.search.return_value = head
        _make_cmd(caller=caller, args="brain from head").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("predate", msg)
