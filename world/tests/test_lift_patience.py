"""Waiting for a lift scales with the shaft (#2412).

`LIFT_PATIENCE` was a flat 15 ticks — 30 seconds at the default step delay —
while the Brackett's 16-floor shaft takes 3 + 6×15 = 93 seconds end to end.
Any ride of five floors or more therefore ran out of patience, fell through to
the ordinary walk, bounced off a door with no car behind it three times, and
faulted.

It is not hypothetical: both bar keepers carry it in their fault logs —
`travel to Escallier Snailery - Yard failed: elevator out of The Brackett Arms
- Floor 2 Landing bounced three times`.

A flat number cannot serve a 2-floor lift and a 16-floor one at once, so
patience is derived from the shaft.
"""
from unittest import mock

from evennia.utils.test_resources import BaseEvenniaTest

from world.director import travel


class _Car:
    """Minimal stand-in — `_lift_patience` only reads `db.floors`."""

    def __init__(self, floors):
        self.db = mock.Mock()
        self.db.floors = [(i, str(i)) for i in range(floors)]


class TestLiftPatienceScales(BaseEvenniaTest):

    def test_a_tall_shaft_outlasts_its_own_worst_ride(self):
        """The bug, stated as a requirement: patience must cover the longest
        ride the shaft can produce, or tall buildings strand people."""
        car = _Car(16)
        ticks = travel._lift_patience(car, 2.0)
        worst_seconds = 3 * 2 + 6 * 15          # DOOR*2 + PER_FLOOR*(n-1)
        self.assertGreaterEqual(ticks * 2.0, worst_seconds)

    def test_the_old_flat_value_would_not_have(self):
        """Pins why this changed rather than merely that it did."""
        self.assertLess(travel.LIFT_PATIENCE * 2.0, 3 * 2 + 6 * 15)

    def test_a_short_shaft_stays_brisk(self):
        """A 2-floor lift must not inherit a 16-floor building's patience."""
        self.assertLess(travel._lift_patience(_Car(2), 2.0),
                        travel._lift_patience(_Car(16), 2.0))

    def test_it_scales_with_the_step_delay(self):
        """Patience is counted in TICKS but earned in SECONDS."""
        self.assertGreater(travel._lift_patience(_Car(16), 1.0),
                           travel._lift_patience(_Car(16), 4.0))

    def test_a_car_with_no_floors_takes_the_flat_cap(self):
        """An unreadable shaft must not yield a confidently-wrong SHORT
        patience — that is the exact failure this function removes."""
        self.assertEqual(travel._lift_patience(_Car(0), 2.0),
                         travel.LIFT_PATIENCE)

    def test_an_unreadable_car_falls_back_to_the_flat_cap(self):
        """Never raise inside travel — a broken car must not stall a walk."""
        self.assertEqual(travel._lift_patience(object(), 2.0),
                         travel.LIFT_PATIENCE)
