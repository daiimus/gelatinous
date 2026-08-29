"""One driver per body (#2373).

The colony ran two schedulers over the same people. `director_routines`
ticked every 45s and walked patrol beats; `souls_heartbeat` ticked every
30s and walked everything else. They coordinated by reading each other's
attributes — `is_patrol_idle` checked `soul_job`, and nothing checked
the reverse.

That was tolerable while the two populations barely overlapped. After
the population merge it was 46 bodies with two drivers and none with
one, which is the definition of a splintered system rather than a
layered one.

Patrol is now a souls goal at band 4 — the idle filler the director
always described it as. The director keeps what a beat IS: the route,
the stagger, the cadence, and what happens at a stop. It no longer
supplies the feet.
"""
from unittest import mock

from evennia.utils.test_resources import BaseEvenniaTest

from world.director import routines
from world.souls import actions, engine


class TestTheDirectorYieldsTheFeet(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = self.char1
        self.npc.db.patrol_beat = [self.room2]

    def test_a_souled_body_is_not_walked_by_the_director(self):
        self.npc.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        with mock.patch.object(routines, "travel_to") as walked:
            self.assertEqual(routines.tick_npc(self.npc), "souls")
        walked.assert_not_called()

    def test_an_unsouled_body_still_walks(self):
        """Fails toward movement: a body nothing else drives must not
        freeze in the street. Nothing is in this state today, but the
        fallback is honest rather than assumed."""
        with mock.patch.object(routines, "travel_to") as walked:
            self.assertEqual(routines.tick_npc(self.npc), "travel")
        walked.assert_called_once()


class TestPatrolIsASoulsGoal(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        self.soul.db.patrol_beat = [self.room2]

    def test_it_plans_a_walk_to_the_next_stop(self):
        plan = actions.plan_for(self.soul, "patrol")
        self.assertEqual([s["do"] for s in plan["steps"]],
                         ["travel", "patrol_mark"])
        self.assertEqual(plan["steps"][0]["room"], self.room2.id)

    def test_standing_on_the_stop_it_just_works_it(self):
        self.soul.location = self.room2
        plan = actions.plan_for(self.soul, "patrol")
        self.assertEqual([s["do"] for s in plan["steps"]], ["patrol_mark"])

    def test_a_body_with_no_beat_has_no_patrol(self):
        self.soul.db.patrol_beat = None
        self.assertIsNone(actions.plan_for(self.soul, "patrol"))

    def test_it_sits_at_the_idle_band(self):
        """Band 4. Anything real — a need, a shift, a fight — outranks
        walking a loop, which is what 'idle filler' has to mean."""
        self.assertEqual(engine._goal_band("patrol"), 4)

    def test_cadence_still_paces_the_stroll(self):
        """Civilians drift and security marches. That distinction lived
        in the walker; it has to survive the walker moving."""
        self.soul.db.patrol_cadence = 3
        self.assertFalse(routines.cadence_ready(self.soul))
        self.assertFalse(routines.cadence_ready(self.soul))
        self.assertTrue(routines.cadence_ready(self.soul))
