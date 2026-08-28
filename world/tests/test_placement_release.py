"""Nobody works two counters at once (#2339).

The owner spotted it by looking at a room: the Snailery yard read as
three people working. Only one was.

    Pia                "is behind the shell counter, sleeves turned back"
    Ezra Vantomme      "is behind the steel counter, appraising something"
    Jordan St. Rivera  "is working the hull-slab bar"

Ezra's counter is in Kaspar Pawn & Salvage. Jordan's bar is in the Hub
and Howl. Both were off shift, out for dinner, and still wearing their
own workplace's placement line.

Two causes, and the second is the nastier:

1. Both release sites fire only when the soul holds a `duty` job at the
   moment its shift lapses. A keeper whose block ended while they were
   eating never released.
2. `placed_by_shift` -- the marker granting permission to clear -- lived
   on `ndb`, which dies on reload, while `db.temp_place` does not. After
   any restart the permission was gone and the placement was stuck
   forever. A volatile flag guarding persistent state can only leak.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import jobs


class TestTheMarkerSurvivesAReload(EvenniaCommandTest):
    def test_it_is_persistent_not_volatile(self):
        """ndb dies on reload; db.temp_place does not."""
        import inspect
        src = inspect.getsource(jobs)
        self.assertNotIn("ndb.placed_by_shift", src)
        self.assertNotIn("ndb.seated_by_shift", src)
        self.assertIn("db.placed_by_shift", src)

    def test_leaving_clears_placement_we_set(self):
        soul = self.char1
        soul.db.temp_place = "is behind the steel counter"
        soul.db.placed_by_shift = True
        jobs._leave_the_post(soul)
        self.assertEqual(soul.db.temp_place, "")
        self.assertFalse(soul.db.placed_by_shift)

    def test_it_never_tramples_a_player_authored_place(self):
        """The courtesy that made the flag necessary in the first
        place: only clear what the shift set."""
        soul = self.char1
        soul.db.temp_place = "is lounging insolently"
        soul.db.placed_by_shift = False
        jobs._leave_the_post(soul)
        self.assertEqual(soul.db.temp_place, "is lounging insolently")


class TestPlacementIsReconciled(EvenniaCommandTest):
    """Not merely caught at the transition. State that must be true is
    cheaper to check than an event that must be caught."""

    def test_think_reconciles_it_every_beat(self):
        import inspect
        from world.souls import engine
        src = inspect.getsource(engine.think)
        self.assertIn("soul.db.placed_by_shift", src)
        self.assertIn("_release_placement(soul)", src)

    def test_it_checks_both_being_at_post_and_on_shift(self):
        import inspect
        from world.souls import engine
        src = inspect.getsource(engine.think)
        block = src[src.index("soul.db.placed_by_shift"):]
        self.assertIn("at_post", block)
        self.assertIn('_in_block(hour, sched["work"])', block)
