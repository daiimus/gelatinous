"""Routing models how people actually move (#2231).

Two faults, same root: the graph described the world's connections but
not the world's movement.

**Lifts.** An elevator car is a moving room whose `out` exit is
re-pointed on arrival. So the raw graph had corridor -> car and
car -> lobby, and never lobby -> corridor: riding is a button press,
not an exit. Anything behind a lift was unreachable whenever the car
rested elsewhere. Live consequence — the dispatch post sits on floor 2
of the constabulary, so `plan_for("duty")` never found a route and the
colony's emergency board was never once manned. Not intermittently.
Ever. `travel._await_lift` has always known how to call a car and press
a floor; nothing ever handed it a route that asked.

**Cost.** Every step cost 1, so a rooftop shortcut beat a longer
street. But the rooftops ARE genuinely connected — Kaspar, Market, The
Last Shift and Hammett's Instep all link up there — so A* used them and
ordinary colonists commuted across the skyline. Normal people don't
walk along rooftops. Some will; they say so.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.spatial.pathfind import (
    DEFAULT_COST, ROUTE_COST, _neighbors, _route_cost, find_path,
    is_reachable, path_length,
)


class _Room:
    def __init__(self, key, kind=None):
        self.key = key
        self.exits = []
        self.db = mock.MagicMock()
        self.db.type = kind
        self.db.floors = None


class _Exit:
    def __init__(self, key, dest):
        self.key = key
        self.destination = dest
        self.db = mock.MagicMock()
        self.db.is_edge = None
        self.db.is_gap = None

    def access(self, who, kind):
        return True


class TestRouteCost(EvenniaCommandTest):
    def test_a_street_is_the_cheap_default(self):
        self.assertEqual(_route_cost(_Room("x", "street"), None), 1.0)

    def test_a_rooftop_is_dear(self):
        self.assertGreater(_route_cost(_Room("x", "rooftop"), None),
                           _route_cost(_Room("y", "street"), None))

    def test_an_unknown_kind_is_ordinary_ground(self):
        """Most of the colony isn't classified, and the common case is
        a room you'd walk through without thinking."""
        self.assertEqual(_route_cost(_Room("x", None), None), DEFAULT_COST)
        self.assertEqual(_route_cost(_Room("x", "nightclub"), None),
                         DEFAULT_COST)

    def test_a_taste_for_roofs_discounts_them(self):
        who = mock.MagicMock()
        who.db.route_taste = 0.1
        roof = _Room("roof", "rooftop")
        self.assertLess(_route_cost(roof, who), _route_cost(roof, None))

    def test_taste_never_makes_a_roof_cheaper_than_a_street(self):
        who = mock.MagicMock()
        who.db.route_taste = 0.0
        self.assertGreaterEqual(_route_cost(_Room("roof", "rooftop"), who),
                                DEFAULT_COST)

    def test_taste_does_not_touch_ordinary_ground(self):
        who = mock.MagicMock()
        who.db.route_taste = 0.1
        self.assertEqual(_route_cost(_Room("st", "street"), who), 1.0)

    def test_a_junk_taste_is_ignored_not_fatal(self):
        who = mock.MagicMock()
        who.db.route_taste = "banana"
        self.assertEqual(_route_cost(_Room("roof", "rooftop"), who),
                         ROUTE_COST["rooftop"])


class TestOrdinaryPeopleTakeTheStreet(EvenniaCommandTest):
    def _town(self):
        """A short way over two roofs, a long way along four streets."""
        start, end = _Room("Start", "street"), _Room("End", "street")
        r1, r2 = _Room("Roof A", "rooftop"), _Room("Roof B", "rooftop")
        s1, s2, s3, s4 = (_Room(f"Street {i}", "street") for i in range(4))
        start.exits = [_Exit("up", r1), _Exit("west", s1)]
        r1.exits = [_Exit("east", r2)]
        r2.exits = [_Exit("down", end)]
        s1.exits = [_Exit("west", s2)]
        s2.exits = [_Exit("west", s3)]
        s3.exits = [_Exit("west", s4)]
        s4.exits = [_Exit("north", end)]
        end.exits = []
        return start, end, (r1, r2)

    def test_the_long_street_beats_the_short_roof(self):
        start, end, roofs = self._town()
        path = find_path(start, end)
        self.assertIsNotNone(path)
        for roof in roofs:
            self.assertNotIn(roof, path)

    def test_someone_who_runs_roofs_takes_the_roof(self):
        start, end, roofs = self._town()
        runner = mock.MagicMock()
        runner.db.route_taste = 0.1
        path = find_path(start, end, traverser=runner)
        self.assertIn(roofs[0], path)

    def test_length_still_counts_steps_not_cost(self):
        """`path_length` is what 'nearest unit' means to dispatch. If it
        returned cost, a unit across the street could lose to one
        further away."""
        start, end, _ = self._town()
        self.assertEqual(path_length(start, end), 5)   # 5 street hops


class TestRidingIsARoute(EvenniaCommandTest):
    """The car reaches every floor its rider may press."""

    def _shaft(self, permitted=True):
        from typeclasses.elevator import ElevatorCarExit
        lobby, corridor = _Room("Lobby"), _Room("Secure Corridor")
        car = _Room("Elevator Car")
        out = mock.MagicMock(spec=ElevatorCarExit)
        out.key = "out"
        out.destination = lobby            # parked at the lobby
        car.exits = [out]
        car.db.floors = [[lobby, "1"], [corridor, "2"]]
        car.floor_index = lambda r: 0 if r is lobby else 1
        car._floor_permitted = lambda idx, who: permitted or idx == 0
        return lobby, corridor, car, out

    def test_the_car_offers_every_floor_not_just_the_parked_one(self):
        lobby, corridor, car, out = self._shaft()
        dests = [d for d, _e in _neighbors(car, mock.MagicMock())]
        self.assertIn(lobby, dests)
        self.assertIn(corridor, dests)      # the one it is NOT parked at

    def test_a_secured_floor_routes_only_for_a_granted_sleeve(self):
        """Same predicate the button uses — one rule, not a second copy
        of the lock."""
        lobby, corridor, car, out = self._shaft(permitted=False)
        dests = [d for d, _e in _neighbors(car, mock.MagicMock())]
        self.assertIn(lobby, dests)
        self.assertNotIn(corridor, dests)

    def test_with_no_traverser_the_shaft_is_pure_connectivity(self):
        lobby, corridor, car, out = self._shaft(permitted=False)
        dests = [d for d, _e in _neighbors(car, None)]
        self.assertIn(corridor, dests)

    def test_the_ride_is_the_car_exit(self):
        """`travel._await_lift` reads the route to know which floor to
        press, so every floor must arrive on the car's own exit."""
        lobby, corridor, car, out = self._shaft()
        for _d, ex in _neighbors(car, mock.MagicMock()):
            self.assertIs(ex, out)

    def test_a_floor_behind_a_lift_is_reachable(self):
        lobby, corridor, car, out = self._shaft()
        lobby.exits = [_Exit("elevator", car)]
        corridor.exits = []
        self.assertTrue(is_reachable(lobby, corridor,
                                     traverser=mock.MagicMock()))

    def test_an_ordinary_room_is_not_mistaken_for_a_car(self):
        plain = _Room("Kitchen", "interior")
        dest = _Room("Hall", "interior")
        ex = _Exit("out", dest)
        plain.exits = [ex]
        self.assertEqual(list(_neighbors(plain, None)), [(dest, ex)])
