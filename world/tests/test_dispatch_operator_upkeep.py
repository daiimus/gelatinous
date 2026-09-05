"""The desk does not hire a second Petra (#2181).

`ensure_dispatch_operator` looked for an operator in the dispatch ROOM
and hired one when it found none. The operator is a soul who can walk
off — and when she did, it hired a body of her, every upkeep pass.
Deleting the copy just triggered another.

Her absence is supposed to sound like the console's automation voice.
That is what this function's own docstring says, and now what it does.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import population


class TestAnAbsentOperatorIsNotAVacancy(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Colonial Constabulary Dispatch Operations"
        # patched, not assigned — a bare module-level assignment leaks
        # into every other test that imports this module
        patcher = mock.patch.object(
            population, "get_dispatch_room", return_value=self.room1)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_an_operator_in_the_room_is_returned(self):
        self.char2.db.dispatch_operator = True
        self.char2.location = self.room1
        self.assertEqual(population.ensure_dispatch_operator(), self.char2)

    def test_an_operator_elsewhere_is_not_replaced(self):
        """The bug: she is at the bar, so the desk hired another her."""
        self.char2.db.dispatch_operator = True
        self.char2.location = self.room2
        before = len(self.room1.contents)
        self.assertIsNone(population.ensure_dispatch_operator())
        self.assertEqual(len(self.room1.contents), before,
                         "hired a second operator while one exists")

    def test_a_dead_operator_does_not_block_rehiring(self):
        """A dead operator IS a vacancy — the same rule every other post
        follows, and the dispatch fixture already carries
        `post_policy = resleave` like the bars do (owner ruling
        2026-09-05, #2762).

        Death is faked through `is_dead()`, the method the code actually
        consults. This used to set `db.is_dead = True`, an ATTRIBUTE row
        no object in the world carries — which is precisely why the old
        liveness filter was always true and never removed anybody. The
        test passed by feeding the bug the one input that made it move.
        """
        self.char2.db.dispatch_operator = True
        self.char2.location = self.room2
        # no LIVE operator anywhere, so the desk may staff itself
        with mock.patch.object(type(self.char2), "is_dead",
                               return_value=True):
            op = population.ensure_dispatch_operator()
        self.assertIsNotNone(op)
        self.assertTrue(op.db.dispatch_operator)

    def test_a_living_operator_elsewhere_still_blocks_rehiring(self):
        """The distinction that keeps #2181 shut: walked off is not dead.
        Three Petras happened because the desk could not tell them
        apart."""
        self.char2.db.dispatch_operator = True
        self.char2.location = self.room2
        before = len(self.room1.contents)
        self.assertIsNone(population.ensure_dispatch_operator())
        self.assertEqual(len(self.room1.contents), before)
