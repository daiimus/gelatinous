"""Three neighbours that didn't know a rule their sibling did (#2331).

All found by reading the souls audit log, and all the same shape: a
component enforcing a rule while the component doing the same job
beside it does not.

* the pathfinder skips EDGES and GAPS but had never heard of SKY ROOMS
* `_advertisers` checks reachability; the job market did not
* the wardrobe PLANNER picks by missing coverage; the wear STEP did not
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest


class TestSkyRoomsAreNotAWalk(EvenniaCommandTest):
    """`Exit.at_traverse` refuses normal movement into a sky room --
    "use jump commands to access aerial transit" -- and unlike an edge
    it carries no is_gap/is_edge flag, so nothing excluded it.

    155 sky rooms, 146 unflagged exits into them. Ossie Trelane's crane
    cab sat behind one: a twenty-room route whose FIRST hop could never
    be taken, bounced every three minutes for hours, 61% of every fault
    in the colony from one man who could not get to work.
    """

    def _sky_exit(self):
        sky = create_object("typeclasses.rooms.Room", key="In the Air")
        sky.db.is_sky_room = True
        return create_object("typeclasses.exits.Exit", key="up",
                             location=self.room1, destination=sky), sky

    def test_a_sky_exit_is_not_offered(self):
        from world.spatial.pathfind import _neighbors
        ex, _sky = self._sky_exit()
        offered = [e for _d, e in _neighbors(self.room1, self.char1)]
        self.assertNotIn(ex, offered)

    def test_not_even_to_a_roof_runner(self):
        """Unlike a gap, this is not a matter of taste: entering a sky
        room needs `jump_movement_allowed`, which the jump COMMAND sets
        and travel never does."""
        from world.spatial.pathfind import _neighbors
        ex, _sky = self._sky_exit()
        self.char1.db.route_taste = 0.2
        offered = [e for _d, e in _neighbors(self.room1, self.char1)]
        self.assertNotIn(ex, offered)

    def test_an_ordinary_exit_is_unaffected(self):
        from world.spatial.pathfind import _neighbors
        ex = create_object("typeclasses.exits.Exit", key="out",
                           location=self.room1, destination=self.room2)
        offered = [e for _d, e in _neighbors(self.room1, self.char1)]
        self.assertIn(ex, offered)


class TestNobodyIsOfferedAJobTheyCannotReach(EvenniaCommandTest):
    """The Rook was offered the Helix Lounge from inside his sealed
    basement studio -- a recluse with no exits, by design -- and
    re-took the offer every three minutes forever."""

    def test_an_unreachable_post_is_not_offered(self):
        from world.souls import posts as posts_mod
        post = create_object("typeclasses.items.Item", key="a bar",
                             location=self.room2)
        with mock.patch.object(posts_mod, "_can_reach", return_value=False):
            posts_mod._offer(self.char1, post, self.room2, "day")
        self.assertIsNone(self.char1.db.soul_job)

    def test_a_reachable_one_is(self):
        from world.souls import posts as posts_mod
        post = create_object("typeclasses.items.Item", key="a bar",
                             location=self.room2)
        with mock.patch.object(posts_mod, "_can_reach", return_value=True):
            posts_mod._offer(self.char1, post, self.room2, "day")
        self.assertEqual(self.char1.db.soul_job["goal"], "claim")

    def test_standing_in_it_counts(self):
        from world.souls import posts as posts_mod
        self.assertTrue(posts_mod._can_reach(self.char1, self.char1.location))

    def test_nowhere_is_not_reachable(self):
        from world.souls import posts as posts_mod
        self.assertFalse(posts_mod._can_reach(self.char1, None))


class TestWearReachesForWhatIsMissing(EvenniaCommandTest):
    """Bianca carried two pairs of jeans and a mesh top with her chest
    uncovered. Ranking by layer alone reached for a spare pair of
    trousers, whose name resolved to the pair she was already wearing.
    """

    def test_a_garment_covering_bare_skin_sorts_first(self):
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        wear = src[src.index('if do == "wear"'):]
        self.assertIn("modesty_of(soul)", wear)
        self.assertIn("_useful_first", wear)

    def test_it_still_falls_back_to_layer_order(self):
        """When nothing is bare, the old rung ordering still decides —
        that is the upgrade case."""
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        wear = src[src.index('if do == "wear"'):]
        self.assertIn("_rung(garment)", wear)
