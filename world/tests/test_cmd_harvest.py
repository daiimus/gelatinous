"""Unit tests for :class:`commands.forensics.CmdHarvest` (PR #188).

Exercises the harvest command end-to-end with lightweight fakes so no
Evennia DB is required.  Mirrors the strategy used in
:mod:`world.tests.test_cmd_autopsy`: substitute the
``commands.forensics.Corpse`` symbol with a stand-in base class so the
``isinstance(target, Corpse)`` guard accepts our fake without patching
the ``isinstance`` builtin (which causes infinite recursion against
``mock.call`` internals).

Coverage matrix:

* Usage / argument parsing.
* Non-corpse rejection.
* Skeletal-corpse short-circuit.
* Pre-PR-#186 snapshot-less corpse refusal.
* Ambiguous ``harvest <corpse>`` lists harvestable organs.
* Snapshot organ missing / spec missing / spine refusal.
* Already-removed / inside-severed-limb / destroyed refusal.
* Roll-fail (mid-range) leaves snapshot untouched.
* Critical-fail (natural 1) zeroes ``current_hp`` in snapshot.
* Success spawns an Organ via ``create_object``, mutates snapshot,
  appends to ``removed_organs``.

Run via::

    evennia test world.tests.test_cmd_harvest
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdHarvest
from world.combat.constants import (
    HARVEST_CRIT_FAIL,
    HARVEST_DC_BASIC,
    ORGAN_CONDITION_BY_DECAY,
)


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
    """Minimal corpse surface the harvest command needs."""

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
        # PR-F (#200): CmdHarvest synthesizes a ``harvested``-type wound
        # on the corpse at the organ's container.  Seed the slot so the
        # success branch's ``list(target.db.wounds_at_death or ())``
        # round-trip preserves any pre-existing wounds from death.
        self.db.wounds_at_death = []
        self._display = display or key
        self._decay_stage = decay_stage

    def get_display_name(self, looker=None, **kwargs):  # noqa: D401
        del looker, kwargs
        return self._display

    def get_decay_stage(self):
        return self._decay_stage

    def get_medical_snapshot(self):
        return self.db.medical_state_at_death


def _snapshot_with(*, heart_hp=15, liver_hp=20, kidney_hp=15):
    """Return a minimal MedicalState.to_dict()-shaped snapshot."""
    return {
        "organs": {
            "heart": {
                "current_hp": heart_hp, "max_hp": 15, "container": "chest",
            },
            "liver": {
                "current_hp": liver_hp, "max_hp": 20, "container": "abdomen",
            },
            "left_kidney": {
                "current_hp": kidney_hp, "max_hp": 15, "container": "abdomen",
            },
            "spine": {
                "current_hp": 25, "max_hp": 25, "container": "back",
            },
            "left_lung": {
                "current_hp": 20, "max_hp": 20, "container": "chest",
            },
        },
        "conditions": [],
        "blood_level": 5000,
        "pain_level": 0,
        "consciousness": True,
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


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


class CmdHarvestTests(TestCase):
    def setUp(self):
        # Swap the Corpse symbol so our fake passes isinstance.
        self._patcher = patch.object(cmd_module, "Corpse", _CorpseStandIn)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    # ----- argument handling -----

    def test_no_args_prints_usage(self):
        caller = _make_caller()
        _make_cmd(caller=caller, args="").func()
        caller.msg.assert_called_once()
        self.assertIn("Usage", caller.msg.call_args[0][0])

    def test_non_corpse_rejected(self):
        caller = _make_caller()
        caller.search.return_value = MagicMock()  # not a _CorpseStandIn
        _make_cmd(caller=caller, args="heart from rock").func()
        msg = caller.msg.call_args[0][0].lower()
        self.assertIn("corpse", msg)
        self.assertIn("severed head", msg)

    # ----- decay / snapshot gates -----

    def test_skeletal_short_circuit(self):
        caller = _make_caller()
        corpse = _FakeCorpse(decay_stage="skeletal", snapshot=_snapshot_with())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="heart from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("decomposed", msg)

    def test_no_snapshot_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=None)
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="heart from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("predate", msg)

    # ----- ambiguous form -----

    def test_ambiguous_lists_harvestable(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("heart", msg)
        self.assertIn("liver", msg)
        self.assertIn("left kidney", msg)
        # spine is cannot_be_destroyed; lung is can_be_harvested=False
        self.assertNotIn("spine", msg)
        self.assertNotIn("lung", msg)

    def test_ambiguous_with_nothing_left(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with(),
            removed_organs=["heart", "liver", "left_kidney"],
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("no harvestable organs", msg)

    # ----- per-organ refusals -----

    def test_missing_organ_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="gallbladder from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("no gallbladder", msg)

    def test_spine_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="spine from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("too deeply integrated", msg)

    def test_lung_refused_not_harvestable(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="left_lung from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("cannot be harvested", msg)

    def test_already_removed_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with(), removed_organs=["heart"],
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="heart from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("already been removed", msg)

    def test_inside_severed_limb_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(
            snapshot=_snapshot_with(), severed_locations=["chest"],
        )
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="heart from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("went with the severed chest", msg)

    def test_destroyed_organ_refused(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with(heart_hp=0))
        caller.search.return_value = corpse
        _make_cmd(caller=caller, args="heart from corpse").func()
        msg = caller.msg.call_args[0][0]
        self.assertIn("already destroyed", msg)

    # ----- roll outcomes -----

    def test_roll_fail_leaves_state_intact(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        # Force a mid-range fail (above crit-fail, below DC).
        fail_roll = HARVEST_DC_BASIC - 1
        self.assertGreater(fail_roll, HARVEST_CRIT_FAIL)
        with patch.object(cmd_module, "roll_stat", return_value=fail_roll), \
                patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="heart from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.removed_organs, [])
        self.assertEqual(
            corpse.db.medical_state_at_death["organs"]["heart"]["current_hp"],
            15,
        )

    def test_crit_fail_destroys_organ(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_CRIT_FAIL
        ), patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="heart from corpse").func()
            mk.assert_not_called()
        self.assertEqual(
            corpse.db.medical_state_at_death["organs"]["heart"]["current_hp"],
            0,
        )
        self.assertEqual(corpse.db.removed_organs, [])

    def test_success_spawns_organ_and_mutates_snapshot(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with(), decay_stage="fresh")
        caller.search.return_value = corpse
        fake_organ = MagicMock()
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=fake_organ
        ) as mk:
            _make_cmd(caller=caller, args="heart from corpse").func()
            mk.assert_called_once()
            kwargs = mk.call_args.kwargs
            self.assertEqual(kwargs["location"], caller)
            self.assertIn("heart", kwargs["key"])
        fake_organ.configure_from_harvest.assert_called_once_with(
            organ_name="heart",
            condition=ORGAN_CONDITION_BY_DECAY["fresh"],
            corpse=corpse,
        )
        self.assertEqual(corpse.db.removed_organs, ["heart"])

    def test_success_condition_tracks_decay(self):
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with(), decay_stage="advanced")
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC + 5
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ) as mk:
            _make_cmd(caller=caller, args="liver from corpse").func()
        self.assertIn(
            ORGAN_CONDITION_BY_DECAY["advanced"], mk.call_args.kwargs["key"]
        )

    def test_organ_name_accepts_spaces(self):
        """``harvest left kidney from corpse`` → underscore-normalized."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ) as mk:
            _make_cmd(caller=caller, args="left kidney from corpse").func()
            mk.assert_called_once()
        self.assertEqual(corpse.db.removed_organs, ["left_kidney"])

    # ----- PR-F (#200) — harvested wound synthesis -----

    def test_success_synthesizes_harvested_wound_at_container(self):
        """A successful heart harvest stamps a ``harvested`` wound at chest."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ):
            _make_cmd(caller=caller, args="heart from corpse").func()
        self.assertEqual(len(corpse.db.wounds_at_death), 1)
        wound = corpse.db.wounds_at_death[0]
        self.assertEqual(wound["injury_type"], "harvested")
        # Location is the *container*, not the organ name.
        self.assertEqual(wound["location"], "chest")
        self.assertEqual(wound["organ"], "heart")
        self.assertEqual(wound["severity"], "Critical")
        self.assertEqual(wound["stage"], "old")
        self.assertEqual(wound["organ_damage"]["container"], "chest")
        self.assertEqual(wound["organ_damage"]["current_hp"], 0)

    def test_eye_harvest_targets_head_container(self):
        """Eye harvest must target ``head`` so PR-D head-cluster carry-forward triggers."""
        caller = _make_caller()
        # Snapshot needs left_eye for the eye harvest path.
        snap = _snapshot_with()
        snap["organs"]["left_eye"] = {
            "current_hp": 10, "max_hp": 10, "container": "head",
        }
        corpse = _FakeCorpse(snapshot=snap)
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ):
            _make_cmd(caller=caller, args="left eye from corpse").func()
        self.assertEqual(len(corpse.db.wounds_at_death), 1)
        wound = corpse.db.wounds_at_death[0]
        self.assertEqual(wound["location"], "head")
        self.assertEqual(wound["organ"], "left_eye")

    def test_miss_does_not_synthesize_wound(self):
        """Below-DC rolls leave wounds_at_death untouched."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC - 1
        ), patch.object(cmd_module, "create_object"):
            _make_cmd(caller=caller, args="heart from corpse").func()
        self.assertEqual(corpse.db.wounds_at_death, [])

    def test_crit_fail_does_not_synthesize_wound(self):
        """Crit-fail destroys the organ silently — no harvested wound prose."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_CRIT_FAIL
        ), patch.object(cmd_module, "create_object"):
            _make_cmd(caller=caller, args="heart from corpse").func()
        self.assertEqual(corpse.db.wounds_at_death, [])
        # And the destruction signal lives on the snapshot, not in
        # the wounds list — confirm the snapshot was zeroed.
        self.assertEqual(
            corpse.db.medical_state_at_death["organs"]["heart"]["current_hp"],
            0,
        )

    def test_harvest_preserves_pre_existing_wounds(self):
        """The new wound is appended, not replacing pre-existing wounds."""
        caller = _make_caller()
        corpse = _FakeCorpse(snapshot=_snapshot_with())
        # Seed a pre-existing wound that came from combat death.
        existing = {
            "injury_type": "bullet",
            "location": "chest",
            "severity": "Critical",
            "stage": "old",
            "organ": "heart",
            "organ_damage": {
                "current_hp": 0, "max_hp": 15, "container": "chest",
            },
        }
        corpse.db.wounds_at_death = [existing]
        caller.search.return_value = corpse
        with patch.object(
            cmd_module, "roll_stat", return_value=HARVEST_DC_BASIC
        ), patch.object(
            cmd_module, "create_object", return_value=MagicMock()
        ):
            _make_cmd(caller=caller, args="liver from corpse").func()
        self.assertEqual(len(corpse.db.wounds_at_death), 2)
        # Existing bullet wound preserved.
        self.assertIn(existing, corpse.db.wounds_at_death)
        # New harvested wound at liver's container.
        harvested = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "harvested"
        ]
        self.assertEqual(len(harvested), 1)
        self.assertEqual(harvested[0]["location"], "abdomen")
        self.assertEqual(harvested[0]["organ"], "liver")
