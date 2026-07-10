"""The elevator car model (VERTICALITY_AND_BUILDINGS_SPEC §1.1).

The car's position is world-state: landings gate on the car being docked,
the car's out exit is re-pointed on arrival and refuses mid-travel, and
both buttons ride the ordinary ``press`` command.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.elevator as emod
from typeclasses.elevator import (
    DOOR_SECONDS,
    RIDE_SECONDS_PER_FLOOR,
    car_docked,
)


def _bind(mock, cls, *names):
    for name in names:
        setattr(mock, name, getattr(cls, name).__get__(mock, cls))


def _car(floors, current=0, moving=False):
    car = MagicMock(name="car")
    car.db = SimpleNamespace(floors=floors, current_floor=current,
                             moving=moving, target_floor=None,
                             floor_locks={})
    car.contents = []
    _bind(car, emod.ElevatorCar,
          "floor_index", "current_landing", "is_docked_at",
          "request_floor", "call_to", "_begin_move", "_arrive",
          "_out_exit")
    return car


def _landing(name):
    room = MagicMock(name=name)
    return room


class TestFloorState(TestCase):
    def setUp(self):
        self.l1, self.l2 = _landing("alcove"), _landing("2F landing")
        self.car = _car([[self.l1, "1"], [self.l2, "2"]])

    def test_floor_index_by_label_and_room(self):
        self.assertEqual(self.car.floor_index("2"), 1)
        self.assertEqual(self.car.floor_index(" 2 "), 1)   # forgiving
        self.assertEqual(self.car.floor_index(self.l1), 0)
        self.assertIsNone(self.car.floor_index("13"))

    def test_docked_means_here_and_not_moving(self):
        self.assertIs(self.car.current_landing(), self.l1)
        self.assertTrue(self.car.is_docked_at(self.l1))
        self.assertFalse(self.car.is_docked_at(self.l2))
        self.car.db.moving = True
        self.assertFalse(self.car.is_docked_at(self.l1))
        self.assertFalse(car_docked(self.car, self.l1))
        self.assertFalse(car_docked(None, self.l1))


class TestRide(TestCase):
    def setUp(self):
        self.l1, self.l2 = _landing("alcove"), _landing("2F landing")
        self.car = _car([[self.l1, "1"], [self.l2, "2"]])

    def test_panel_press_starts_the_ride(self):
        with patch.object(emod, "delay") as d:
            self.assertTrue(self.car.request_floor("2", MagicMock()))
        self.assertTrue(self.car.db.moving)
        self.assertEqual(self.car.db.target_floor, 1)
        seconds = d.call_args.args[0]
        self.assertEqual(seconds, DOOR_SECONDS + RIDE_SECONDS_PER_FLOOR)
        # doors close at both ends
        self.car.msg_contents.assert_called_once()
        self.l1.msg_contents.assert_called_once()

    def test_bad_floor_and_double_press_refuse(self):
        rider = MagicMock()
        with patch.object(emod, "delay") as d:
            self.assertFalse(self.car.request_floor("13", rider))
            self.assertFalse(self.car.request_floor("1", rider))  # already here
            self.car.db.moving = True
            self.assertFalse(self.car.request_floor("2", rider))  # in motion
        d.assert_not_called()
        self.assertEqual(rider.msg.call_count, 3)

    def test_arrival_repoints_the_out_exit(self):
        out = MagicMock(name="out")
        out.destination = self.l1
        self.car.contents = [out]
        self.car.db.moving = True
        self.car.db.target_floor = 1
        self.car._arrive(1)
        self.assertFalse(self.car.db.moving)
        self.assertEqual(self.car.db.current_floor, 1)
        self.assertIs(out.destination, self.l2)
        self.l2.msg_contents.assert_called_once()      # doors open upstairs

    def test_quiet_arrival_snaps_without_messages(self):
        self.car.db.moving = True
        self.car._arrive(1, quiet=True)
        self.assertEqual(self.car.db.current_floor, 1)
        self.car.msg_contents.assert_not_called()
        self.l2.msg_contents.assert_not_called()

    def test_call_button_summons_or_reports(self):
        caller = MagicMock()
        with patch.object(emod, "delay"):
            self.assertFalse(self.car.call_to(self.l1, caller))   # already open
            self.assertTrue(self.car.call_to(self.l2, caller))    # summons
        self.assertTrue(self.car.db.moving)
        caller2 = MagicMock()
        self.assertFalse(self.car.call_to(self.l1, caller2))      # mid-ride
        self.assertIn("in motion", caller2.msg.call_args.args[0])


class TestExitsGate(TestCase):
    def test_landing_exit_refuses_until_docked(self):
        door = MagicMock()
        _bind(door, emod.ElevatorDoorExit, "at_traverse")
        car = _car([[door.location, "1"]], current=0)
        car.db.moving = True
        door.destination = car
        walker = MagicMock()
        door.at_traverse(walker, car)
        self.assertIn("shut", walker.msg.call_args.args[0])

    def test_car_exit_refuses_mid_travel(self):
        out = MagicMock()
        _bind(out, emod.ElevatorCarExit, "at_traverse")
        out.location.db = SimpleNamespace(moving=True)
        walker = MagicMock()
        out.at_traverse(walker, MagicMock())
        self.assertIn("moving", walker.msg.call_args.args[0])


class TestButtons(TestCase):
    def _button(self, cls):
        btn = MagicMock()
        _bind(btn, cls, "at_press")
        return btn

    def test_call_button_presses_through_to_the_car(self):
        btn = self._button(emod.ElevatorCallButton)
        presser = MagicMock()
        self.assertTrue(btn.at_press(presser))
        btn.db.elevator.call_to.assert_called_once_with(btn.location, presser)

    def test_dead_button_is_dead(self):
        btn = self._button(emod.ElevatorCallButton)
        btn.db.elevator = None
        presser = MagicMock()
        self.assertTrue(btn.at_press(presser))
        self.assertIn("dead", presser.msg.call_args.args[0])

    def test_panel_lists_floors_on_bare_press(self):
        panel = self._button(emod.ElevatorPanel)
        panel.db.elevator.db = SimpleNamespace(
            floors=[[MagicMock(), "1"], [MagicMock(), "2"]])
        presser = MagicMock()
        self.assertTrue(panel.at_press(presser, None))
        self.assertIn("1, 2", presser.msg.call_args.args[0])

    def test_panel_declines_labels_it_does_not_own(self):
        panel = self._button(emod.ElevatorPanel)
        panel.db.elevator.floor_index.return_value = None
        self.assertFalse(panel.at_press(MagicMock(), "13"))

    def test_panel_selects_a_floor(self):
        panel = self._button(emod.ElevatorPanel)
        car = panel.db.elevator
        car.floor_index.return_value = 1
        presser = MagicMock()
        self.assertTrue(panel.at_press(presser, "2"))
        car.request_floor.assert_called_once_with("2", presser)


class TestPressRouting(TestCase):
    """`press` without " on " reaches pressables; spray syntax untouched."""

    def _cmd(self, args, contents):
        from commands.CmdGraffiti import CmdPress
        cmd = CmdPress()
        cmd.args = args
        cmd.caller = MagicMock()
        cmd.caller.location.contents = contents
        return cmd

    def _pressable(self, key, aliases=(), handles=True):
        obj = MagicMock()
        obj.key = key
        obj.db.pressable = True
        obj.aliases.all.return_value = list(aliases)
        obj.at_press.return_value = handles
        return obj

    def test_name_match_presses_the_object(self):
        btn = self._pressable("call button", aliases=["button"])
        cmd = self._cmd("call button", [btn])
        self.assertTrue(cmd._press_pressable())
        btn.at_press.assert_called_once_with(cmd.caller, None)

    def test_label_falls_through_to_the_panel(self):
        panel = self._pressable("floor panel")
        cmd = self._cmd("2", [panel])
        self.assertTrue(cmd._press_pressable())
        panel.at_press.assert_called_once_with(cmd.caller, "2")

    def test_nothing_pressable_defers_to_usage(self):
        stranger = MagicMock()
        stranger.db.pressable = None       # MagicMock-truthiness guard
        cmd = self._cmd("2", [stranger])
        self.assertFalse(cmd._press_pressable())
        stranger.at_press.assert_not_called()

    def test_spray_syntax_still_routes_to_the_can(self):
        cmd = self._cmd("blue on spray can", [])
        cmd._press_spray_can = MagicMock()
        cmd.func()
        cmd._press_spray_can.assert_called_once_with("blue", "spray can")
