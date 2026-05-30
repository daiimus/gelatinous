"""Unit tests for :class:`commands.forensics.CmdSever` (PR #190).

Mirrors the harvest test strategy: lightweight fakes + Corpse symbol
swap so ``isinstance(target, Corpse)`` accepts our stand-in.

PR #190 enhancements covered here:

* Wielded-blade gate — a ``db.can_sever`` weapon is required; a missing
  or dull weapon is refused before any cut begins.
* One-cut-at-a-time guard (``caller.ndb.sever_task``).
* Cast-time scheduling via ``utils.delay`` (``SEVER_TIME_SECONDS``).
* Combined ``intellect + motorics`` resolution vs ``SEVER_DC_INT_MOT``;
  a sum at or below ``SEVER_CRIT_FAIL_SUM`` botches (recoverable).
* Completion-time re-validation: the cut aborts with no mutation if the
  corpse moved / was destroyed, the actor stopped wielding the blade,
  or the actor entered combat during the cut.

Legacy coverage retained:

* Usage / argument parsing, non-corpse rejection, skeletal / snapshot
  gates, ambiguous listing, per-location refusals, bookkeeping
  correctness, head routing to ``SeveredHead``, wound + longdesc
  carry-forward (PR #198), head-sever identity surface (issue #208).

Run via::

    evennia test world.tests.test_cmd_sever
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands import forensics as cmd_module
from commands.forensics import CmdSever
from world.combat.constants import (
    ORGAN_CONDITION_BY_DECAY,
    SEVER_CRIT_FAIL_SUM,
    SEVER_DC_INT_MOT,
    SEVER_TIME_SECONDS,
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
        wounds_at_death=None,
        longdesc_data=None,
        dbref="#101",
        location=None,
        pk=101,
    ):
        self.key = key
        self.dbref = dbref
        self.pk = pk
        self.location = location
        self.db = _DB()
        self.db.signature_at_death = (
            "sleeve-1", "tall", "lean", "hooded", ("balaclava",),
        )
        self.db.apparent_uid_at_death = "abc123"
        self.db.medical_state_at_death = snapshot
        self.db.removed_organs = list(removed_organs or ())
        self.db.severed_locations = list(severed_locations or ())
        # PR #198 corpse-side state read by apply_sever_to_corpse.
        self.db.wounds_at_death = list(wounds_at_death or ())
        self.db.longdesc_data = dict(longdesc_data or {})
        # PR #198 decay clock fields touched by apply_severed_head_overlay.
        import time
        self.db.creation_time = time.time()
        self.db.death_time = time.time()
        self.db.death_cause = "gunshot"
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
    caller.intellect = 10
    # Pending-cast / combat re-validation state (PR #190).
    caller.ndb.sever_task = None
    caller.ndb.combat_handler = None
    return caller


def _make_weapon(*, can_sever=True, display="a knife"):
    weapon = MagicMock()
    weapon.db.can_sever = can_sever
    weapon.get_display_name = MagicMock(return_value=display)
    return weapon


def _make_corpse(caller, **kwargs):
    """Build a corpse co-located with *caller* and wire it to search."""
    kwargs.setdefault("location", caller.location)
    corpse = _FakeCorpse(**kwargs)
    caller.search.return_value = corpse
    return corpse


def _make_cmd(*, caller, args):
    cmd = CmdSever()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = ()
    return cmd


def _rolls(intel, motor):
    """A ``roll_stat`` side-effect returning per-stat fixed values."""
    def _inner(char, stat, *args, **kwargs):
        del char, args, kwargs
        return {"intellect": intel, "motorics": motor}.get(stat, 1)
    return _inner


def _immediate_delay(seconds, callback, *args, **kwargs):
    """Stand-in for ``utils.delay`` that resolves synchronously."""
    del seconds
    callback(*args, **kwargs)
    return MagicMock()


# Per-stat roll values that land the combined sum in each band.
_SUCCESS = SEVER_DC_INT_MOT  # intel + motor == DC (success boundary)
_MID_FAIL = SEVER_CRIT_FAIL_SUM + 2  # above crit band, below DC
_CRIT = 1  # sum == 2 → at/under SEVER_CRIT_FAIL_SUM (assumes >= 2)


def _split(total):
    """Split a target sum into (intellect, motorics) halves."""
    return total // 2, total - total // 2


@contextmanager
def _sever_env(*, weapon=None, intel=None, motor=None, create_return=None):
    """Patch the cast-time + roll surface for a full sever resolution."""
    weapon = weapon if weapon is not None else _make_weapon()
    if intel is None or motor is None:
        intel, motor = _split(_SUCCESS)
    create_mock = MagicMock(return_value=create_return or MagicMock())
    with patch.object(
        cmd_module, "get_wielded_weapon", return_value=weapon
    ), patch.object(
        cmd_module.utils, "delay", side_effect=_immediate_delay
    ), patch.object(
        cmd_module, "roll_stat", side_effect=_rolls(intel, motor)
    ), patch.object(
        cmd_module, "create_object", create_mock
    ):
        yield create_mock


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
        _make_corpse(
            caller, decay_stage="skeletal", snapshot=_snapshot_with_limbs()
        )
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("decomposed", caller.msg.call_args[0][0])

    def test_no_snapshot_refused(self):
        caller = _make_caller()
        _make_corpse(caller, snapshot=None)
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("predate", caller.msg.call_args[0][0])

    # ----- ambiguous form -----

    def test_ambiguous_lists_severable(self):
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
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
        _make_corpse(
            caller,
            snapshot=_snapshot_with_limbs(),
            severed_locations=[
                "head", "left_arm", "right_arm",
                "left_thigh", "right_thigh",
            ],
        )
        _make_cmd(caller=caller, args="corpse").func()
        self.assertIn("no limbs left", caller.msg.call_args[0][0])

    # ----- per-location refusals -----

    def test_non_severable_container_rejected(self):
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
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
        _make_corpse(caller, snapshot=snap)
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("no left arm", caller.msg.call_args[0][0])

    def test_already_severed_rejected(self):
        caller = _make_caller()
        _make_corpse(
            caller,
            snapshot=_snapshot_with_limbs(),
            severed_locations=["left_arm"],
        )
        _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn(
            "already been severed", caller.msg.call_args[0][0]
        )

    # ----- wielded-blade gate (PR #190) -----

    def test_no_weapon_refused(self):
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with patch.object(
            cmd_module, "get_wielded_weapon", return_value=None
        ), patch.object(cmd_module.utils, "delay") as delay:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            delay.assert_not_called()
        self.assertIn("bladed weapon", caller.msg.call_args[0][0])

    def test_dull_weapon_refused(self):
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        blunt = _make_weapon(can_sever=False, display="a club")
        with patch.object(
            cmd_module, "get_wielded_weapon", return_value=blunt
        ), patch.object(cmd_module.utils, "delay") as delay:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            delay.assert_not_called()
        self.assertIn("too dull", caller.msg.call_args[0][0])

    def test_already_mid_cut_refused(self):
        caller = _make_caller()
        caller.ndb.sever_task = MagicMock()  # a cut already pending
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with patch.object(
            cmd_module, "get_wielded_weapon", return_value=_make_weapon()
        ), patch.object(cmd_module.utils, "delay") as delay:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            delay.assert_not_called()
        self.assertIn("already mid-cut", caller.msg.call_args[0][0])

    # ----- cast-time scheduling -----

    def test_schedules_delayed_cut(self):
        """A valid request schedules the resolution rather than
        resolving inline; nothing is spawned until the timer fires."""
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with patch.object(
            cmd_module, "get_wielded_weapon", return_value=_make_weapon()
        ), patch.object(cmd_module.utils, "delay") as delay, \
                patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            delay.assert_called_once()
            self.assertEqual(delay.call_args[0][0], SEVER_TIME_SECONDS)
            mk.assert_not_called()

    # ----- completion-time re-validation (PR #190) -----

    def test_completion_aborts_if_corpse_moved_away(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        corpse.location = _FakeRoom()  # no longer co-located
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    def test_completion_aborts_if_corpse_destroyed(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        corpse.pk = None  # deleted mid-cut
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    def test_completion_aborts_if_blade_unwielded(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        # Blade present at the gate, gone by completion.
        weapon = _make_weapon()
        with patch.object(
            cmd_module, "get_wielded_weapon", side_effect=[weapon, None]
        ), patch.object(
            cmd_module.utils, "delay", side_effect=_immediate_delay
        ), patch.object(cmd_module, "create_object") as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    def test_completion_aborts_if_in_combat(self):
        caller = _make_caller()
        caller.ndb.combat_handler = MagicMock()  # dragged into a fight
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    # ----- roll outcomes -----

    def test_roll_fail_leaves_state_intact(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        intel, motor = _split(_MID_FAIL)
        with _sever_env(intel=intel, motor=motor) as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
            mk.assert_not_called()
        self.assertEqual(corpse.db.severed_locations, [])

    def test_crit_fail_no_mutation_no_item(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env(intel=_CRIT, motor=_CRIT) as mk:
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
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        fake_app = MagicMock()
        with _sever_env(create_return=fake_app) as mk:
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
        corpse = _make_corpse(
            caller, snapshot=_snapshot_with_limbs(), decay_stage="advanced"
        )
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertIn(
            ORGAN_CONDITION_BY_DECAY["advanced"], mk.call_args.kwargs["key"]
        )
        self.assertEqual(corpse.db.severed_locations, ["head"])

    def test_location_accepts_spaces(self):
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env():
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
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env():
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertIn("left_arm", corpse.db.severed_locations)

    # ----- head routing → SeveredHead super-item (PR #194) -----

    def test_head_routes_to_severed_head_typeclass(self):
        """Severing the head spawns ``typeclasses.items.SeveredHead``,
        not the plain ``Appendage`` other locations get.
        """
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="head from corpse").func()
        args, kwargs = mk.call_args
        # First positional arg is the typeclass path.
        self.assertEqual(args[0], "typeclasses.items.SeveredHead")
        self.assertIn("head", kwargs["key"])

    def test_non_head_still_routes_to_appendage(self):
        """Non-head severable locations still spawn plain Appendage."""
        caller = _make_caller()
        _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env() as mk:
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        args, _ = mk.call_args
        self.assertEqual(args[0], "typeclasses.items.Appendage")

    # ----- wound + longdesc carry-forward (PR #198) -----

    def test_successful_sever_clears_corpse_longdesc(self):
        """After a limb sever, the corpse's longdesc for that location
        is removed (it moved to the appendage)."""
        caller = _make_caller()
        corpse = _make_corpse(
            caller,
            snapshot=_snapshot_with_limbs(),
            longdesc_data={
                "left_arm": "a pale freckled arm",
                "chest": "a broad chest",
            },
        )
        with _sever_env():
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertNotIn("left_arm", corpse.db.longdesc_data)
        self.assertIn("chest", corpse.db.longdesc_data)

    def test_successful_sever_appends_stump_wound(self):
        """After a limb sever, the corpse gains a synthesized
        ``severed``-type wound at the severed location."""
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env():
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        stump_wounds = [
            w for w in corpse.db.wounds_at_death
            if w.get("injury_type") == "severed"
        ]
        self.assertEqual(len(stump_wounds), 1)
        self.assertEqual(stump_wounds[0]["location"], "left_arm")

    def test_head_sever_clears_full_head_cluster(self):
        """Severing the head clears longdesc for the entire
        SEVERED_HEAD_LOCATIONS cluster, not just ``head``."""
        caller = _make_caller()
        corpse = _make_corpse(
            caller,
            snapshot=_snapshot_with_limbs(),
            longdesc_data={
                "head": "a shaven scalp",
                "face": "sharp features",
                "neck": "a thick neck",
                "left_eye": "a milky eye",
                "chest": "a broad chest",
            },
        )
        with _sever_env():
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertEqual(set(corpse.db.longdesc_data.keys()), {"chest"})

    # ----- head-sever identity surface (issue #208) -----

    def test_head_sever_marks_corpse_head_severed(self):
        """After a successful head sever, the corpse carries
        ``db.head_severed = True`` — the gate that
        ``Corpse.get_display_name`` reads to suppress unaided
        recognition while preserving autopsy access."""
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        # Pre-sever invariant: flag absent / falsy.
        self.assertFalse(getattr(corpse.db, "head_severed", False))
        with _sever_env(create_return=MagicMock()):
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertTrue(corpse.db.head_severed)

    def test_limb_sever_does_not_mark_head_severed(self):
        """Severing a non-head limb must NOT set head_severed."""
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        with _sever_env():
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        self.assertFalse(getattr(corpse.db, "head_severed", False))

    def test_head_sever_preserves_corpse_identity_snapshot(self):
        """The corpse keeps its ``signature_at_death`` /
        ``apparent_uid_at_death`` / ``sleeve_uid`` after the head is
        severed — autopsy and recognition-memory lookups still work."""
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        sig_before = corpse.db.signature_at_death
        uid_before = corpse.db.apparent_uid_at_death
        sleeve_before = corpse.db.signature_at_death[0]
        with _sever_env():
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertEqual(corpse.db.signature_at_death, sig_before)
        self.assertEqual(corpse.db.apparent_uid_at_death, uid_before)
        self.assertEqual(corpse.db.signature_at_death[0], sleeve_before)

    def test_failed_head_sever_does_not_mark_head_severed(self):
        """Sub-DC head roll must not set ``head_severed``."""
        caller = _make_caller()
        corpse = _make_corpse(caller, snapshot=_snapshot_with_limbs())
        intel, motor = _split(_MID_FAIL)
        with _sever_env(intel=intel, motor=motor):
            _make_cmd(caller=caller, args="head from corpse").func()
        self.assertFalse(getattr(corpse.db, "head_severed", False))

    def test_failed_sever_does_not_clear_longdesc(self):
        """Sub-DC rolls must not mutate corpse longdesc."""
        caller = _make_caller()
        corpse = _make_corpse(
            caller,
            snapshot=_snapshot_with_limbs(),
            longdesc_data={"left_arm": "a pale arm"},
        )
        intel, motor = _split(_MID_FAIL)
        with _sever_env(intel=intel, motor=motor):
            _make_cmd(caller=caller, args="left_arm from corpse").func()
        # Longdesc untouched on failure.
        self.assertEqual(
            corpse.db.longdesc_data, {"left_arm": "a pale arm"}
        )
