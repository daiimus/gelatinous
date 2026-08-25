"""Souls only queue at things they can get to (#2316).

The MOVEMENT layer is careful about access: travel calls lifts, presses
floor buttons and opens doors through real commands, and the pathfinder
filters on `access(traverser, "traverse")` and `door_blocks`. So a soul
never walks into a door it cannot open.

SELECTION was the half that never asked. `_advertisers` scores
`value / (1 + straight-line distance)` and never consults the route
graph, so the winner could be behind a locked door, up a lift the soul
may not ride, or in a sealed room.

Live consequence: the Community Thrift's free rail advertised the best
clothing in the colony (0.95) from behind a padlocked roll-shutter.
Every soul who needed clothes planned a trip there, failed to path,
faulted, and tried again on the next think — five of them at once.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions


class TestOnlyWhatTheyCanReach(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.location = self.room1
        self.shop = create_object("typeclasses.items.Item",
                                  key="a rail", location=self.room2)
        self.shop.db.advertises = {"wardrobe": 0.95}
        self.shop.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0

    def _seal(self):
        """Padlock every way into room2, the way the thrift was."""
        from evennia.objects.models import ObjectDB
        for ex in ObjectDB.objects.filter(db_destination=self.room2):
            ex.locks.replace("traverse:false()")

    def test_a_reachable_advertiser_is_offered(self):
        got = actions._advertisers(self.soul, "wardrobe")
        self.assertIn(self.room2, [r for _s, _f, r in got])

    def test_a_sealed_one_is_not(self):
        self._seal()
        actions._ad_cache["at"] = 0
        got = actions._advertisers(self.soul, "wardrobe")
        self.assertNotIn(self.room2, [r for _s, _f, r in got])

    def test_the_unfiltered_view_still_sees_it(self):
        """The scan itself is unchanged — this is a filter on top, so
        anything that wants the raw ranking can still ask for it."""
        self._seal()
        actions._ad_cache["at"] = 0
        got = actions._advertisers(self.soul, "wardrobe", reachable=False)
        self.assertIn(self.room2, [r for _s, _f, r in got])

    def test_standing_in_it_counts_as_reachable(self):
        """No route needed to something you are already inside — and
        pathfinding from a room to itself is not a question worth
        asking."""
        self.soul.location = self.room2
        self._seal()
        actions._ad_cache["at"] = 0
        got = actions._advertisers(self.soul, "wardrobe")
        self.assertIn(self.room2, [r for _s, _f, r in got])

    def test_it_is_asked_as_THIS_soul(self):
        """A door they cannot open, or a gap only a roof-runner would
        cross, must be answered for the individual — not in general."""
        import inspect
        self.assertIn("traverser=soul",
                      inspect.getsource(actions._reachable_only))

    def test_a_homeless_soul_does_not_crash_planning(self):
        self.soul.location = None
        actions._advertisers(self.soul, "wardrobe")   # must not raise

    def test_an_unroutable_question_never_breaks_a_plan(self):
        with mock.patch("world.spatial.pathfind.find_path",
                        side_effect=RuntimeError("graph on fire")):
            actions._ad_cache["at"] = 0
            got = actions._advertisers(self.soul, "wardrobe")
        self.assertEqual(got, [])


class TestItDoesNotPathfindTheWholeColony(EvenniaCommandTest):
    """Cost control. `_advertisers` runs when a soul picks a new goal,
    not every beat — but it should still stop once it has enough."""

    def test_it_stops_after_a_few_usable_options(self):
        self.assertEqual(actions.MAX_REACHABLE, 3)

    def test_callers_take_the_best_that_works(self):
        soul = self.char1
        soul.location = self.room1
        rooms = []
        for i in range(6):
            r = create_object("typeclasses.rooms.Room", key=f"shop {i}")
            create_object("typeclasses.exits.Exit", key=f"e{i}",
                          location=self.room1, destination=r)
            f = create_object("typeclasses.items.Item", key=f"rail {i}",
                              location=r)
            f.db.advertises = {"wardrobe": 0.9 - i * 0.01}
            f.tags.add("advertiser", category="souls")
            rooms.append(r)
        actions._ad_cache["at"] = 0
        got = actions._advertisers(soul, "wardrobe")
        self.assertLessEqual(len(got), actions.MAX_REACHABLE)
