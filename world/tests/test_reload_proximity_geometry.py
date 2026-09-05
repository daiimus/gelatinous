"""The post-reload sweep must not grant melee reach across rooms (#2748).

Combat handlers explicitly manage MULTI-ROOM combat -- the handler
docstring says so and it carries `db.managed_rooms`, a list -- so two
combatants on one handler are not necessarily in one room.

The sweep's only test was mutual engagement, so a fight that spanned
rooms (someone who fled next door, a ranged exchange across a boundary)
came back from a reload with MELEE proximity between characters who
cannot reach each other. Melee proximity is the state that means "close
enough to swing at", so it granted adjacency the geometry does not
support.

The sweep itself is right to exist: without it, a melee fight crossing a
reload loses its proximity set while the ticker keeps burning rounds. It
just restored more than it should.
"""
import inspect
from unittest import TestCase

import server.conf.at_server_startstop as startstop
from world.combat import proximity


class TestTheSweepFiltersOnLocation(TestCase):
    def _sweep_source(self):
        src = inspect.getsource(startstop.at_server_start)
        start = src.index("rebuild melee proximity")
        end = src.index("if relinked:", start)
        return src[start:end]

    def test_the_pair_loop_compares_locations(self):
        self.assertIn("one.location is not two.location", self._sweep_source())

    def test_the_location_test_precedes_the_engagement_test(self):
        """Order matters only for cost, but the cheap test should come
        first and the intent should be unambiguous."""
        block = self._sweep_source()
        self.assertLess(block.index("one.location is not two.location"),
                        block.index("_are_characters_in_mutual_combat"))

    def test_it_still_establishes_proximity(self):
        """The pin: the sweep exists because a melee fight crossing a
        reload otherwise loses its proximity set entirely."""
        self.assertIn("establish_proximity(one, two)", self._sweep_source())


class TestTheHelperDocumentsItsContract(TestCase):
    """`establish_proximity` guards on identity and nothing else. Every
    live caller is an advance / charge / grapple-drag path that has just
    established co-location, so the guard belongs at the call sites --
    but that has to be written down, because the sweep is the second
    place in this audit where a proximity-style relation was built
    without checking the geometry."""

    def test_the_docstring_says_it_does_not_check_geometry(self):
        doc = inspect.getdoc(proximity.establish_proximity) or ""
        self.assertIn("DOES NOT CHECK GEOMETRY", doc)

    def test_the_docstring_tells_a_future_caller_what_to_do(self):
        doc = inspect.getdoc(proximity.establish_proximity) or ""
        self.assertIn("put the test there", doc)
