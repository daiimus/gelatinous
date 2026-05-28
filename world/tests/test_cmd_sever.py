"""Unit tests for :class:`commands.forensics.CmdSever` (PR #190).

Mirrors the harvest test strategy: lightweight fakes + Corpse symbol
swap so ``isinstance(target, Corpse)`` accepts our stand-in.

Coverage matrix:

* Usage / argument parsing.
* Non-corpse rejection.
* Skeletal short-circuit.
* Pre-PR-#186 snapshot-less refusal.
* Ambiguous form lists severable locations (filters non-severable
  containers and already-severed).
* Non-severable container rejection (e.g. ``chest``).
* Snapshot-missing-location rejection.
* Already-severed rejection.
* Mid-range fail vs crit-fail vs success — bookkeeping correctness.
* Condition tracks decay.
* Forward-compat: after sever-arm, harvest cannot target organs in
  that arm (verified at the harvest gate, exercised here by reading
  the post-sever ``severed_locations`` state).

Run via::

    evennia test world.tests.test_cmd_sever
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdSever
from world.combat.constants import (
    ORGAN_CONDITION_BY_DECAY,
    SEVER_CRIT_FAIL,
    SEVER_DC_BASIC,
)


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _DB:
    pass


class _FakeRoom:
    def __init__(self):
        self.contents = []


class _CorpseStandIn:
    pass


class _FakeCorpse(_CorpseStandIn):
    def __init__(
        self,
        *,
        key="the corpse of Jorge",
        display=None,
        decay_stage="fresh",
        snapshot=None,
        removed_organs=None,
        severed_locations=None,
        dbref="#101",
    ):
        self.key = key
        self.dbref = dbref
        self.db = _DB()
        self.db.signature_at_death = (
            "sleeve-1", "tall", "lean", "hooded", ("balaclava",),
        )
        self.db.apparent_uid_at_death = "abc123"
        self.db.medical_state_at_death = snapshot
        self.db.removed_organs = list(removed_organs or ())
        self.db.severed_locations = list(severed_locations or ())
        self._display = display or key
        self._decay_stage = decay_stage

    def get_display_name(self, looker=None, **kwargs):
        del looker, kwargs
        return self._display

    def get_decay_stage(self):
        return self._decay_stage

    def get_medical_snapshot(self):
        return self.db.medical_state_at_death


def _snapshot_with_limbs():
    """Snapshot with a representative slice of containers."""
    def org(hp, container):
        return {"current_hp": hp, "max_hp": hp, "container": container}
    return {
        "organs": {
            "heart": org(15, "chest"),
            "liver": org(20, "abdomen"),
            "brain": org(10, "head"),
            "left_humerus": org(25, "left_arm"),
            "right_humerus": org(25, "right_arm"),
            "left_femur": org(25, "left_thigh"),
            "right_femur": org(25, "right_thigh"),
        },
        "conditions": [],
        "blood_level": 5000,
        "pain_level": 0,
        "consciousness": True,
    }


def _make_caller(*, location=None):
    caller = MagicMock()
    caller.key = "Alice"
    caller.dbref = "#42"
    caller.location = location or _FakeRoom()
    caller.recognition_memory = {}
    caller.msg = MagicMock()
    caller.search = MagicMock()
    caller.motorics = 10
    return caller


def _make_cmd(*, caller, args):
    cmd = CmdSever()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = ()
    return cmd


class CmdSeverTests(TestCase):
    def setUp(self):
        self._patcher = patch.object(cmd_module, "Corpse", _CorpseStandIn)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    # ----- argument handling -----

    def test_no_args_prints_usage(self):
        caller = _make_caller()
        _make_cmd(caller=caller, args="").func()
        self.assertIn("Usage", caller.msg.call_args[0][0])

    def test_non_corpse_rejected(self):
        caller = _make_caller()
        caller.search.return_value = MagicMock()
        _make_cmd(caller=caller, args="left_arm from rock").func()
        caller.msg.assert_called_with(
            "You can only sever limbs from a corpse."
        )

    # ----- decay / snapshot gates -----

    def test_skeletal_short_circuit(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            decay_stage="skeletal", snapshot=_snapshot_with_limbs()
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("decomposed", caller.msg.call_args[0][0])

    def test_no_snapshot_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=None)
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("predate", caller.msg.call_args[0][0])

    # ----- ambiguous form -----

    def test_ambiguous_lists_severable(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="corpse").func()
        msg = caller.msg.call_args[0][0]
        # Limb partition + head present
        for loc in ("head", "left arm", "right arm", "left thigh"):
            self.assertIn(loc, msg)
        # Internal containers excluded
        self.assertNotIn("chest", msg)
        self.assertNotIn("abdomen", msg)

    def test_ambiguous_with_nothing_left(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with_limbs(),
            severed_locations=[
                "head", "left_arm", "right_arm",
                "left_thigh", "right_thigh",
            ],
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="corpse").func()
        self.assertIn("no limbs left", caller.msg.call_args[0][0])

    # ----- per-location refusals -----

    def test_non_severable_container_rejected(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="chest from corpse").func()
        self.assertIn(
            "not a detachable", caller.msg.call_args[0][0]
        )

    def test_missing_limb_in_snapshot(self):
        caller = _make_caller()
        # Snapshot only has chest organs — no limbs at all.
        snap = {
            "organs": {
                "heart": {
                    "current_hp": 15, "max_hp": 15, "container": "chest",
                },
            },
        }
        corpse = _FakeCorpse(snapshot=snap)
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("no left arm", caller.msg.call_args[0][0])

    def test_already_severed_rejected(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with_limbs(),
            severed_locations=["left_arm"],
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn(
            "already been severed", caller.msg.call_args[0][0]
        )

    # ----- roll outcomes -----

    def test_roll_fail_leaves_state_intact(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        fail_roll = SEVER_DC_BASIC - 1
        self.assertGreater(fail_roll, SEVER_CRIT_FAIL)
        with patch.object(cmd_module, "roll_stat", return_value=fail_roll), \
                patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    def test_crit_fail_no_mutation_no_item(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_CRIT_FAIL
        ), patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        # Unlike harvest crit-fail, sever crit-fail does NOT destroy
        # anything — state is fully intact.
        self.assertEqual(corpse.db.severed_locations, [])
        self.assertEqual(
            corpse.db.medical_state_at_death["organs"][
                "left_humerus"]["current_hp"],
            25,
        )

    def test_success_spawns_appendage_and_appends(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        fake_app = MagicMock()
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=fake_app
        ) as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_called_once()
            kwargs = mk.call_args.kwargs
            self.assertEqual(kwargs["location"], caller)
            self.assertIn("left arm", kwargs["key"])
        fake_app.configure_from_sever.assert_called_once_with(
            location_name="left_arm",
            condition=ORGAN_CONDITION_BY_DECAY["fresh"],
            corpse=corpse,
        )
        self.assertEqual(corpse.db.severed_locations, ["left_arm"])

    def test_success_condition_tracks_decay(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with_limbs(), decay_stage="advanced"
        )
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC + 5
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ) as mk:
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertIn(
            ORGAN_CONDITION_BY_DECAY["advanced"], mk.call_args.kwargs["key"]
        )

    def test_location_accepts_spaces(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ):
            _make_cmd(caller=caller, args="left arm from corpse").func()
        self.assertEqual(corpse.db.severed_locations, ["left_arm"])

    # ----- forward-compat with harvest -----

    def test_sever_then_harvest_gate_state(self):
        """After severing an arm, the gate that harvest reads — the
        ``severed_locations`` list — contains the arm.  CmdHarvest's
        ``_harvestable_organs`` exclusion is tested in
        ``test_cmd_harvest``; this test just locks the post-sever
        state contract those tests depend on.
        """
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ):
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("left_arm", corpse.db.severed_locations)

    # ----- head routing → SeveredHead super-item (PR #194) -----

    def test_head_routes_to_severed_head_typeclass(self):
        """Severing the head spawns ``typeclasses.items.SeveredHead``,
        not the plain ``Appendage`` other locations get.
        """
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ) as mk:
            _make_cmd(caller=caller, args="head from corpse").func()
        args, kwargs = mk.call_args
        # First positional arg is the typeclass path.
        self.assertEqual(args[0], "typeclasses.items.SeveredHead")
        self.assertIn("head", kwargs["key"])

    def test_non_head_still_routes_to_appendage(self):
        """Non-head severable locations still spawn plain Appendage."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with_limbs())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=SEVER_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ) as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        args, _ = mk.call_args
        self.assertEqual(args[0], "typeclasses.items.Appendage")
