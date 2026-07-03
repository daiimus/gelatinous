"""Tests for the crowd-gated, interdictable witness (crime slice 3)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import witness as wmod
from world.director.witness import (
    WITNESS_TOKENS,
    can_report,
    despawn_witness,
    spawn_witness,
    witness_chance,
    witness_report,
)


class _Room:
    def __init__(self, name):
        self.name = name


def _witness(dead=False, unconscious=False, located=True):
    w = MagicMock(name="witness")
    w.location = _Room("scene") if located else None
    w.is_dead.return_value = dead
    w.is_unconscious.return_value = unconscious
    w.pk = 42
    return w


class TestWitnessChance(TestCase):
    def _with_level(self, level):
        with patch.object(wmod.crowd_system, "calculate_crowd_level",
                          return_value=level):
            return witness_chance(_Room("r"))

    def test_empty_room_is_free(self):
        self.assertEqual(self._with_level(0), 0.0)

    def test_scales_with_crowd_and_caps(self):
        self.assertAlmostEqual(self._with_level(1), 0.55)
        self.assertAlmostEqual(self._with_level(2), 0.80)
        self.assertEqual(self._with_level(4), 0.95)  # capped

    def test_no_crowd_model_no_witness(self):
        with patch.object(wmod.crowd_system, "calculate_crowd_level",
                          side_effect=RuntimeError):
            self.assertEqual(witness_chance(_Room("r")), 0.0)


class TestSpawnWitness(TestCase):
    @patch("world.director.witness.random", return_value=0.99)
    @patch("world.director.witness.witness_chance", return_value=0.5)
    @patch("world.director.witness.create_object")
    def test_failed_roll_spawns_no_one(self, mock_create, _c, _r):
        self.assertIsNone(spawn_witness(_Room("scene")))
        mock_create.assert_not_called()

    @patch("world.director.witness.random", return_value=0.01)
    @patch("world.director.witness.witness_chance", return_value=0.5)
    @patch("world.director.witness.create_object")
    def test_spawns_marked_bystander_with_pockets(self, mock_create, _c, _r):
        shell = MagicMock()
        shell.db = SimpleNamespace()
        mock_create.return_value = shell
        w = spawn_witness(_Room("scene"))
        self.assertIs(w, shell)
        self.assertIn("bystander", mock_create.call_args.kwargs["key"])
        self.assertTrue(WITNESS_TOKENS[0] <= w.db.tokens <= WITNESS_TOKENS[1])
        self.assertTrue(w.db.is_witness)
        self.assertTrue(w.db.is_npc)   # canonical marker (absence = PC)
        self.assertIn("walkie-talkie", w.look_place)  # the visible tell
        w.execute_cmd.assert_called_once()            # reacts on the scene

    def test_no_location_no_witness(self):
        self.assertIsNone(spawn_witness(None))


class TestInterdiction(TestCase):
    def test_alive_and_conscious_can_report(self):
        self.assertTrue(can_report(_witness()))

    def test_dead_witness_is_silenced(self):
        self.assertFalse(can_report(_witness(dead=True)))

    def test_unconscious_witness_is_silenced(self):
        self.assertFalse(can_report(_witness(unconscious=True)))

    def test_gone_witness_is_silenced(self):
        self.assertFalse(can_report(_witness(located=False)))
        self.assertFalse(can_report(None))

    @patch("world.director.witness.flee_and_cower")
    @patch("world.director.dispatch.raise_event")
    def test_live_witness_reports_then_flees_to_cower(self, mock_raise,
                                                      mock_flee):
        w = _witness()
        event = MagicMock()
        self.assertTrue(witness_report(w, event))
        mock_raise.assert_called_once_with(event)
        self.assertTrue(w.execute_cmd.called)      # calls it in visibly
        mock_flee.assert_called_once_with(w)       # then RUNS, not vanishes

    @patch("world.director.witness.delay")
    @patch("world.director.dispatch.raise_event")
    def test_silenced_witness_never_reports(self, mock_raise, mock_delay):
        w = _witness(dead=True)
        self.assertFalse(witness_report(w, MagicMock()))
        mock_raise.assert_not_called()   # the force never learns
        mock_delay.assert_called_once()  # the body still gets cleanup

    @patch("world.director.witness.delay")
    @patch("world.director.travel.travel_to")
    def test_flee_travels_to_nearby_room_then_cowers(self, mock_travel,
                                                     mock_delay):
        from world.director.witness import flee_and_cower
        dest = _Room("alley")
        w = _witness()
        mock_travel.return_value = True
        with patch("world.spatial.rooms_within", return_value=[dest]):
            flee_and_cower(w)
        self.assertEqual(mock_travel.call_args.args[1], dest)
        # arrival callback = the cower
        on_arrive = mock_travel.call_args.kwargs["on_arrive"]
        on_arrive(w)
        self.assertIn("cowering", w.look_place)
        self.assertIs(mock_delay.call_args.args[1], despawn_witness)

    @patch("world.director.witness.delay")
    @patch("world.director.travel.travel_to")
    def test_flee_cowers_in_place_when_nowhere_to_run(self, mock_travel,
                                                      mock_delay):
        from world.director.witness import flee_and_cower
        w = _witness()
        with patch("world.spatial.rooms_within", return_value=[]):
            flee_and_cower(w)
        mock_travel.assert_not_called()
        self.assertIn("cowering", w.look_place)
        self.assertIs(mock_delay.call_args.args[1], despawn_witness)

    def test_despawn_deletes_living_witness(self):
        w = _witness()
        despawn_witness(w)
        w.delete.assert_called_once()

    def test_despawn_leaves_corpse_to_death_pipeline(self):
        w = _witness(dead=True)
        despawn_witness(w)
        w.delete.assert_not_called()
