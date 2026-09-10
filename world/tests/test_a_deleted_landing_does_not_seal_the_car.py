"""A deleted landing does not seal the car (#2626).

`db.floors` holds landing rooms by dbref, and Evennia unpickles a
deleted object as `None`. `_arrive` never guarded that:

    landing = floors[target_idx][0]     # None if the room was deleted
    out = self._out_exit()
    if out: out.destination = landing   # None onto the car's only exit

and `_out_exit` found that exit ONLY by its destination — so once the
destination was None the exit was invisible to the very method that
would repoint it. Every later `_arrive` found no `out` exit and anyone
in the car stayed there. Recovery was `@tel`.

Latent when filed — both live cars have zero dead landings — and one
builder action away: the Brackett's upper floors have been rebuilt once
already. Deleting a landing without pruning `db.floors` is all it takes.

Guarded at four points rather than one, because the car reaches
`_arrive` from three different doors and the queue is a fourth:
both buttons refuse a dead floor, `_serve_queue` skips one, and
`_arrive` itself stays put if it is ever sent to one anyway.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.elevator as emod


def _car(floors, current=0, moving=False):
    car = MagicMock(name="car")
    car.db = SimpleNamespace(floors=floors, current_floor=current,
                             moving=moving, target_floor=None,
                             floor_locks={}, shaft_xy=None, call_queue=[])
    car.contents = []
    for name in ("floor_index", "current_landing", "is_docked_at",
                 "request_floor", "call_to", "_begin_move", "_arrive",
                 "_out_exit", "_enqueue", "_serve_queue", "_landing",
                 "_floor_permitted"):
        real = getattr(emod.ElevatorCar, name, None)
        if real is not None:
            setattr(car, name, real.__get__(car, emod.ElevatorCar))
    return car


class _DeadFloor(TestCase):
    """Floor 1's landing has been deleted; floors 0 and 2 are real."""

    def setUp(self):
        self.l0, self.l2 = MagicMock(name="L0"), MagicMock(name="L2")
        self.car = _car([(self.l0, "0"), (None, "1"), (self.l2, "2")])
        self.out = MagicMock(name="out")
        self.out.key = "out"
        self.out.destination = self.l0
        self.car.contents = [self.out]


class TestTheExitStaysAddressable(_DeadFloor):

    def test_it_is_found_by_key(self):
        """Control: found at all, with a live destination."""
        self.assertIs(self.car._out_exit(), self.out)

    def test_and_still_found_with_a_null_destination(self):
        """The moment that mattered: an exit whose destination is None
        was invisible to the only method that could repoint it."""
        self.out.destination = None
        self.out.db_destination_id = None
        self.assertIs(self.car._out_exit(), self.out)


class TestTheButtonsRefuseADeadFloor(_DeadFloor):

    def test_a_live_floor_still_works(self):
        """Control: the buttons are not simply refusing everything."""
        with patch.object(emod, "delay"):
            self.assertTrue(self.car.call_to(self.l2))
        self.assertTrue(self.car.db.moving)

    def test_the_call_button_refuses(self):
        rider = MagicMock()
        with patch.object(emod, "delay") as d:
            self.assertFalse(self.car.request_floor("1", rider))
        d.assert_not_called()
        self.assertIn("sealed", rider.msg.call_args.args[0])

    def test_and_nothing_was_queued(self):
        self.car.db.moving = True
        self.car.request_floor("1")
        self.assertEqual(list(self.car.db.call_queue), [])


class TestTheQueueSkipsIt(_DeadFloor):

    def test_a_dead_floor_in_the_queue_is_dropped(self):
        self.car.db.call_queue = [1, 2]
        with patch.object(emod, "delay"):
            self.car._serve_queue()
        self.assertEqual(self.car.db.target_floor, 2,
                         "the car drove to a deleted landing")

    def test_a_queue_of_only_dead_floors_empties(self):
        self.car.db.call_queue = [1]
        with patch.object(emod, "delay") as d:
            self.car._serve_queue()
        self.assertEqual(list(self.car.db.call_queue), [])
        self.assertFalse(self.car.db.moving)
        d.assert_not_called()


class TestArrivingAtOneChangesNothing(_DeadFloor):
    """The last line of defence: if the car is ever sent to a dead floor
    by some path these guards do not cover, it must not write None onto
    its own exit."""

    def test_the_exit_is_not_nulled(self):
        self.car.db.moving = True
        self.car.db.target_floor = 1
        with patch.object(emod, "delay"):
            self.car._arrive(1)
        self.assertIs(self.out.destination, self.l0)

    def test_the_car_stays_where_it_was(self):
        self.car.db.moving = True
        with patch.object(emod, "delay"):
            self.car._arrive(1)
        self.assertEqual(self.car.db.current_floor, 0)
        self.assertFalse(self.car.db.moving)

    def test_and_a_real_arrival_still_repoints(self):
        """Control: the guard has not disabled arrival."""
        self.car.db.moving = True
        self.car.db.target_floor = 2
        with patch.object(emod, "delay"):
            self.car._arrive(2)
        self.assertIs(self.out.destination, self.l2)
        self.assertEqual(self.car.db.current_floor, 2)
