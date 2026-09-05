"""`@path` must say that its route ignores locks.

`find_path_exits` takes a `traverser` and this debug window does not
pass one. That is defensible for a builder tool -- the topological route
is usually what you want to see -- but it is also the tool somebody
reaches for when an NPC will not walk somewhere, and THREE separate bugs
in this codebase were exactly a lock-blind route being trusted over a
lock-aware walk (#2711, #2714, #2758). An unqualified route sends the
next person down the same hour of debugging that #2321 records.
"""
from unittest import TestCase, mock

from commands.CmdPath import _traversable_by


class TestTraversabilityIsReportedSeparately(TestCase):
    def test_a_walkable_route_reports_true(self):
        with mock.patch("world.spatial.is_reachable", return_value=True):
            self.assertTrue(_traversable_by(object(), object(), object()))

    def test_a_locked_route_reports_false(self):
        with mock.patch("world.spatial.is_reachable", return_value=False):
            self.assertFalse(_traversable_by(object(), object(), object()))

    def test_it_passes_the_caller_as_the_traverser(self):
        """The whole point: it must ask the question `travel_to` asks."""
        caller, origin, target = object(), object(), object()
        with mock.patch("world.spatial.is_reachable",
                        return_value=True) as reach:
            _traversable_by(caller, origin, target)
        self.assertIs(reach.call_args.kwargs.get("traverser"), caller)

    def test_an_unanswerable_route_does_not_raise(self):
        """A debug window never blows up in a builder's face; it falls
        back to the optimistic reading and the topological route is
        still printed."""
        with mock.patch("world.spatial.is_reachable",
                        side_effect=RuntimeError("no graph")):
            self.assertTrue(_traversable_by(object(), object(), object()))

    def test_the_command_labels_the_route_lock_blind(self):
        import inspect

        import commands.CmdPath as mod
        src = inspect.getsource(mod)
        self.assertIn("Lock-blind", src)
        self.assertIn("_traversable_by(caller, origin, target)", src)
