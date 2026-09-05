"""Tests for patrol routines — posts, beats, the heartbeat tick, and the
Patrol→Detect waypoint sweep."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import routines as rmod
from world.director.routines import at_waypoint, get_beat, tick_npc


class _Room:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class _Npc:
    def __init__(self, location, role="security", post=None, beat=None):
        self.location = location
        self.db = SimpleNamespace(role=role, post=post, patrol_beat=beat)
        self.ndb = SimpleNamespace()
        self.execute_cmd = MagicMock()


class TestBeat(TestCase):
    def test_post_anchors_the_cycle(self):
        base, a, b = _Room("base"), _Room("a"), _Room("b")
        npc = _Npc(base, post=base, beat=[a, b])
        self.assertEqual(get_beat(npc), [base, a, b])

    def test_post_not_duplicated(self):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[base, a])
        self.assertEqual(get_beat(npc), [base, a])

    def test_no_beat_no_cycle(self):
        npc = _Npc(_Room("x"))
        self.assertEqual(get_beat(npc), [])


@patch("world.director.routines._in_combat", return_value=False)
@patch("world.director.routines.is_travelling", return_value=False)
@patch("world.director.routines.is_assigned", return_value=False)
class TestTick(TestCase):
    def test_no_beat_none(self, *_m):
        self.assertEqual(tick_npc(_Npc(_Room("x"))), "none")

    def test_busy_skips(self, mock_assigned, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[a])
        mock_assigned.return_value = True
        self.assertEqual(tick_npc(npc), "skip")

    @patch("world.director.routines.travel_to")
    def test_walks_to_next_waypoint(self, mock_travel, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(a, post=base, beat=[a])   # cycle [base, a]; idx 0 -> base
        npc.ndb.patrol_idx = 0               # pin (fresh NPCs stagger randomly)
        self.assertEqual(tick_npc(npc), "travel")
        self.assertEqual(mock_travel.call_args.args[1], base)

    @patch("world.director.routines.at_waypoint")
    def test_arrival_advances_and_sweeps(self, mock_hook, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[a])  # at waypoint 0 (base)
        npc.ndb.patrol_idx = 0                 # pin (fresh NPCs stagger randomly)
        self.assertEqual(tick_npc(npc), "waypoint")
        self.assertEqual(npc.ndb.patrol_idx, 1)
        mock_hook.assert_called_once_with(npc)


class TestWaypointSweep(TestCase):
    @patch("world.director.security._scan_wanted")
    @patch("world.director.dispatch.raise_event")
    def test_wanted_face_raises_disturbance(self, mock_raise, mock_scan):
        felon = MagicMock(name="felon")
        mock_scan.return_value = ("UID", felon, {"count": 1})
        npc = _Npc(_Room("corner"), role="security")
        at_waypoint(npc)
        event = mock_raise.call_args.args[0]
        self.assertEqual(event.type, "disturbance")
        self.assertIs(event.source, felon)
        self.assertEqual(event.location, npc.location)
        # ...and the unit called it in over the REAL air first (comms organ
        # via xmit's no-handheld fallback) — no magic radio.
        cmds = [c.args[0] for c in npc.execute_cmd.call_args_list]
        self.assertTrue(any(c.startswith("xmit ") for c in cmds), cmds)

    @patch("world.director.security._scan_wanted",
           return_value=(None, None, None))
    @patch("world.director.dispatch.raise_event")
    def test_clean_sweep_just_emotes(self, mock_raise, _scan):
        npc = _Npc(_Room("corner"), role="security")
        at_waypoint(npc)
        mock_raise.assert_not_called()
        npc.execute_cmd.assert_called_once()

    def test_hookless_role_no_waypoint_action(self):
        # "miner" is a real civilian role now (ambient emotes) — a role
        # with no hook of any kind stays silent.
        npc = _Npc(_Room("corner"), role="cartographer")
        at_waypoint(npc)
        npc.execute_cmd.assert_not_called()


class TestPostedAssignments(TestCase):
    @patch("world.director.assignment.travel_to", return_value=True)
    def test_assignment_returns_to_the_base_not_the_spot(self, _t):
        from world.director import assignment as amod
        from world.director.assignment import assign, get_assignment

        class _Char:
            def __init__(self):
                self.location = _Room("street corner")
                self.db = SimpleNamespace(post=_Room("precinct"), role="security")
                self.ndb = SimpleNamespace()

        amod._ACTIVE.clear()
        npc = _Char()
        event = SimpleNamespace(location=_Room("scene"), type="assault",
                                payload={})
        self.assertTrue(assign(npc, event))
        self.assertEqual(get_assignment(npc).post.name, "precinct")
        amod._ACTIVE.clear()


class TestWiring(TestCase):
    def test_patrol_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@patrol", [c.key for c in cs.commands])


class TestTheStaggerSurvives(TestCase):
    """A random starting index that is not persisted is not a stagger
    (#2804, SOULS_SCALE_HARDENING_SPEC Law 4).

    `next_waypoint` rolled the draw and returned it; the only write was
    in the caller's TRAVEL branch. A unit already standing on its
    randomly-chosen waypoint fell through to `advance_waypoint`, which
    read `patrol_idx` as still-unset, collapsed it to 0, and aimed at
    index 1 — so every such unit converged on the same index, which is
    exactly the lockstep the docstring forbids. The souls planner
    discards the returned index too, so the write had to live at the
    roll or neither caller kept it.
    """

    def _npc_on_a_beat(self, rooms):
        npc = _Npc(rooms[0], beat=[r.name for r in rooms])
        return npc

    def test_the_roll_is_written_where_it_is_rolled(self):
        rooms = [_Room(f"r{i}") for i in range(5)]
        npc = self._npc_on_a_beat(rooms)
        with patch.object(rmod, "get_beat", return_value=rooms), \
             patch("random.randrange", return_value=3):
            waypoint, idx = rmod.next_waypoint(npc)
        self.assertEqual(idx, 3)
        self.assertEqual(npc.ndb.patrol_idx, 3,
                         "the draw was thrown away")

    def test_a_unit_standing_on_its_waypoint_keeps_its_draw(self):
        """The exact path that lost it: no travel, so the caller's
        write never ran and advance_waypoint saw an unset index."""
        rooms = [_Room(f"r{i}") for i in range(5)]
        npc = self._npc_on_a_beat(rooms)
        with patch.object(rmod, "get_beat", return_value=rooms), \
             patch("random.randrange", return_value=3):
            rmod.next_waypoint(npc)
            rmod.advance_waypoint(npc)
        self.assertEqual(npc.ndb.patrol_idx, 4,
                         "advanced from 0 instead of from the draw")

    def test_an_existing_index_is_not_re_rolled(self):
        rooms = [_Room(f"r{i}") for i in range(5)]
        npc = self._npc_on_a_beat(rooms)
        npc.ndb.patrol_idx = 2
        with patch.object(rmod, "get_beat", return_value=rooms), \
             patch("random.randrange", return_value=3):
            _waypoint, idx = rmod.next_waypoint(npc)
        self.assertEqual(idx, 2)

    def test_index_zero_is_not_mistaken_for_unset(self):
        """`or 0` could not tell a legitimate index 0 from None."""
        rooms = [_Room(f"r{i}") for i in range(5)]
        npc = self._npc_on_a_beat(rooms)
        npc.ndb.patrol_idx = 0
        with patch.object(rmod, "get_beat", return_value=rooms):
            rmod.advance_waypoint(npc)
        self.assertEqual(npc.ndb.patrol_idx, 1)


class TestTheCadenceIsSpentNotBrowsed(TestCase):
    """`cadence_ready` is asked during goal SELECTION and the answer may
    be discarded — a running job of the same band keeps going. Resetting
    the counter on the way past drained the cadence on beats the patrol
    was never taken, so a unit stepped immediately the first beat patrol
    actually won instead of pacing (#2804)."""

    def _marcher(self, cadence=3, waited=None):
        npc = _Npc(_Room("r"), beat=["r"])
        npc.db.patrol_cadence = cadence
        if waited is not None:
            npc.ndb.patrol_wait = waited
        return npc

    def test_a_ready_answer_does_not_reset_by_itself(self):
        npc = self._marcher(cadence=3, waited=2)
        self.assertTrue(rmod.cadence_ready(npc))
        self.assertEqual(npc.ndb.patrol_wait, 2,
                         "arbitration consumed the cadence")

    def test_taking_the_patrol_is_what_resets_it(self):
        npc = self._marcher(cadence=3, waited=2)
        rmod.cadence_ready(npc)
        rmod.cadence_taken(npc)
        self.assertEqual(npc.ndb.patrol_wait, 0)

    def test_a_waiting_beat_still_advances(self):
        """The pin: pacing must still pace. A beat spent waiting counts,
        or a slow cadence never becomes ready at all."""
        npc = self._marcher(cadence=3)
        self.assertFalse(rmod.cadence_ready(npc))
        self.assertEqual(npc.ndb.patrol_wait, 1)
        self.assertFalse(rmod.cadence_ready(npc))
        self.assertEqual(npc.ndb.patrol_wait, 2)
        self.assertTrue(rmod.cadence_ready(npc))

    def test_cadence_one_is_always_ready(self):
        npc = self._marcher(cadence=1)
        self.assertTrue(rmod.cadence_ready(npc))
        self.assertTrue(rmod.cadence_ready(npc))


class TestAPatrollingUnitPutsItsWeaponAway(TestCase):
    """`_stow_weapon` is called at `watch_once` and
    `security_completion`, and both live inside the ASSIGNMENT
    lifecycle. So a unit whose assignment ended abnormally -- or ended
    before the toggle fix (#2760) landed -- kept its riot gun out
    forever, because nothing off-assignment ever put it away.

    Measured live: one unit standing in the Constabulary lobby on
    routine duty, not assigned, not in combat, `deployed: True`
    (#2709).

    A patrolling unit with no assignment and no fight has no reason to
    be holding a weapon, and the beat is the one hook that runs
    off-assignment.
    """

    def _unit(self):
        npc = _Npc(_Room("a street"), role="security")
        npc.execute_cmd = MagicMock()
        return npc

    def _run(self, npc, assigned=False, in_combat=False):
        with patch("world.director.assignment.is_assigned",
                   return_value=assigned), \
             patch("world.combat.utils.find_character_handler",
                   return_value=object() if in_combat else None), \
             patch("world.director.security._stow_weapon") as stow, \
             patch("world.director.security._scan_wanted",
                   return_value=(None, None, None)):
            at_waypoint(npc)
        return stow

    def test_an_idle_patroller_stows(self):
        self.assertTrue(self._run(self._unit()).called,
                        "the unit kept its gun out on routine patrol")

    def test_an_assigned_unit_keeps_its_weapon(self):
        """The pin: a unit rolling to an incident is about to need it."""
        self.assertFalse(self._run(self._unit(), assigned=True).called)

    def test_a_unit_in_a_fight_keeps_its_weapon(self):
        """The more important pin — disarming mid-fight would be a far
        worse bug than the one being fixed."""
        self.assertFalse(self._run(self._unit(), in_combat=True).called)

    def test_a_civilian_is_untouched(self):
        npc = _Npc(_Room("a street"), role="civilian")
        npc.execute_cmd = MagicMock()
        with patch("world.director.security._stow_weapon") as stow:
            at_waypoint(npc)
        self.assertFalse(stow.called)
