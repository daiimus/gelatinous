"""A call pressed while the car is moving is served, not discarded
(#3173).

`call_to` and `request_floor` both answered a press during a journey by
returning False and throwing it away. The car never came, the caller
stood at shut doors until `_await_lift` ran out of patience, then walked
into the closed exit three times and faulted the errand:

    travel to <anywhere> failed: elevator out of
    The Brackett Arms - Floor 1 Landing bounced three times

**45 souls live in The Brackett Arms**, which has one car and sixteen
floors, so any two of them wanting the lift inside one journey stranded
the second. Measured across the colony's retained fault lists — which
keep only the last few per soul, so it is a floor and not a total — 137
elevator bounces, 6 of them in the six hours before the fix, across 41
distinct souls.

The dwell matters as much as the queue. A walking NPC only gets a tick
every `TRAVEL_STEP_DELAY` (2.0s), so a car that arrived and left again
on the same beat would satisfy the queue while the person who called it
was still standing on the landing — a missed call instead of a dropped
one.
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
    # Tolerant bind: a name the class does not have yet stays a
    # MagicMock rather than raising. Binding it strictly makes this
    # file ERROR against the unfixed tree, and an error stops a test
    # before it can assert anything — the control has to come back as
    # failing assertions about the car.
    for name in ("floor_index", "current_landing", "is_docked_at",
                 "request_floor", "call_to", "_begin_move", "_arrive",
                 "_out_exit", "_enqueue", "_serve_queue"):
        real = getattr(emod.ElevatorCar, name, None)
        if real is not None:
            setattr(car, name, real.__get__(car, emod.ElevatorCar))
    return car


#: Same reason: read off the module with a value that FAILS the
#: comparison below if the constant is absent.
DWELL_SECONDS = getattr(emod, "DWELL_SECONDS", 0)


class _Shaft(TestCase):
    def setUp(self):
        self.l0, self.l1, self.l2 = (MagicMock(name=f"L{i}") for i in range(3))
        self.car = _car([(self.l0, "0"), (self.l1, "1"), (self.l2, "2")])


class TestTheCallIsRemembered(_Shaft):

    def test_a_call_at_rest_still_moves_the_car(self):
        """Control: the path that always worked. If calling were simply
        broken, every queue assertion below would be hollow."""
        with patch.object(emod, "delay") as d:
            self.assertTrue(self.car.call_to(self.l2))
        self.assertTrue(self.car.db.moving)
        d.assert_called()

    def test_a_call_during_a_journey_is_queued(self):
        with patch.object(emod, "delay"):
            self.car.call_to(self.l2)
        self.assertTrue(self.car.db.moving)
        self.assertTrue(self.car.call_to(self.l1))
        self.assertEqual(list(self.car.db.call_queue), [1])

    def test_two_people_pressing_one_landing_is_one_stop(self):
        with patch.object(emod, "delay"):
            self.car.call_to(self.l2)
        self.car.call_to(self.l1)
        self.car.call_to(self.l1)
        self.assertEqual(list(self.car.db.call_queue), [1])

    def test_a_rider_choosing_a_floor_mid_ride_is_queued_too(self):
        with patch.object(emod, "delay"):
            self.car.call_to(self.l2)
        self.assertTrue(self.car.request_floor("0"))
        self.assertEqual(list(self.car.db.call_queue), [0])


class TestTheCarComesBack(_Shaft):

    def arrive_at(self, idx):
        self.car.db.moving = True
        self.car.db.target_floor = idx
        with patch.object(emod, "delay") as d:
            self.car._arrive(idx)
        return d

    def test_arrival_schedules_the_next_call(self):
        self.car.db.call_queue = [0]
        d = self.arrive_at(2)
        d.assert_called_once()
        self.assertEqual(d.call_args.args[0], DWELL_SECONDS)

    def test_it_waits_before_moving_on(self):
        """The doors stand open longer than a walker's tick, or the
        queue is served while the caller is still on the landing."""
        from world.director.travel import TRAVEL_STEP_DELAY
        self.assertGreater(DWELL_SECONDS, TRAVEL_STEP_DELAY)

    def test_an_empty_queue_schedules_nothing(self):
        """Control: an idle car must not wake itself up forever."""
        d = self.arrive_at(2)
        d.assert_not_called()

    def test_serving_the_queue_starts_the_next_journey(self):
        self.car.db.call_queue = [0]
        self.car.db.current_floor = 2
        with patch.object(emod, "delay") as d:
            self.car._serve_queue()
        self.assertTrue(self.car.db.moving)
        self.assertEqual(self.car.db.target_floor, 0)
        self.assertEqual(list(self.car.db.call_queue), [])
        d.assert_called()

    def test_a_call_for_the_floor_it_is_already_on_moves_nothing(self):
        """A repeated press must not send the car on a zero-floor trip."""
        self.car.db.call_queue = [2]
        self.car.db.current_floor = 2
        with patch.object(emod, "delay") as d:
            self.car._serve_queue()
        self.assertFalse(self.car.db.moving)
        self.assertEqual(list(self.car.db.call_queue), [])
        d.assert_not_called()

    def test_it_will_not_start_a_journey_while_one_is_running(self):
        self.car.db.moving = True
        self.car.db.call_queue = [0]
        with patch.object(emod, "delay") as d:
            self.car._serve_queue()
        d.assert_not_called()
        self.assertEqual(list(self.car.db.call_queue), [0])

    def test_the_queue_is_served_in_press_order(self):
        self.car.db.call_queue = [0, 1]
        self.car.db.current_floor = 2
        with patch.object(emod, "delay"):
            self.car._serve_queue()
        self.assertEqual(self.car.db.target_floor, 0)
        self.assertEqual(list(self.car.db.call_queue), [1])
