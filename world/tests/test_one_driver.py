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

The HUNT was the last body-driver left on the 45s tick, and it is a
souls goal too now — band 4, offered above patrol, because that is
precisely where it already sat: `is_patrol_idle` refused to hunt while a
soul job existed, so a unit on duty, fighting, travelling or talking
never hunted. Reproducing that exactly is the point. A merge that
quietly re-banded a security behaviour would be a design change smuggled
in under a refactor.

With that, ONE scheduler drives bodies. The director is a source of work
and a set of rules; it is not a driver.
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


class TestTheHuntIsASoulsGoal(BaseEvenniaTest):
    """The hunt was the LAST body-driver on the 45s tick. With it moved,
    the director drives nothing that has a soul."""

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        self.soul.db.role = "security"
        self.soul.db.patrol_beat = [self.room2]

    def test_the_director_tick_no_longer_hunts(self):
        """Criterion 9 itself. Fails toward the tick STILL hunting, which
        is the state this change exists to end."""
        with mock.patch("world.director.hunt.tick_hunt") as hunted:
            self.assertEqual(routines.tick_npc(self.soul), "souls")
        hunted.assert_not_called()

    def test_wants_hunt_is_pure(self):
        """The band tree has to ask before it commits. If asking emoted
        or seeded state, merely CONSIDERING a hunt would start one."""
        from world.director import hunt as hunt_mod
        with mock.patch.object(self.soul, "execute_cmd") as spoke:
            hunt_mod.wants_hunt(self.soul)
        spoke.assert_not_called()
        self.assertIsNone(getattr(self.soul.ndb, "hunt", None))

    def test_only_security_hunts(self):
        from world.director import hunt as hunt_mod
        self.soul.db.role = "civilian"
        self.soul.ndb.hunt = {"key": "x"}          # even mid-hunt
        self.assertFalse(hunt_mod.wants_hunt(self.soul))

    def test_a_live_hunt_still_owes_a_beat(self):
        from world.director import hunt as hunt_mod
        self.soul.ndb.hunt = {"key": "someone"}
        self.assertTrue(hunt_mod.wants_hunt(self.soul))

    def test_it_is_offered_above_patrol(self):
        """Both are band 4; the hunt owns an idle unit BEFORE the beat
        does. Fails toward the unit strolling past an intruder."""
        with mock.patch("world.director.hunt.wants_hunt", return_value=True):
            self.assertEqual(engine._desired_goal(self.soul, 12), (4, "hunt"))

    def test_without_a_reason_the_beat_gets_the_unit_back(self):
        with mock.patch("world.director.hunt.wants_hunt", return_value=False):
            band, goal = engine._desired_goal(self.soul, 12)
        self.assertEqual(goal, "patrol")

    def test_it_sits_where_it_already_sat(self):
        """Band 4, NOT because hunting matters less than eating, but
        because `is_patrol_idle` already refused to hunt while a soul job
        existed. Re-banding here would be a design change smuggled in
        under a refactor."""
        self.assertEqual(engine._goal_band("hunt"), 4)

    def test_the_plan_is_a_single_step(self):
        """`ndb.hunt` holds the progress. A chain would be a second place
        tracking it, and the two would drift."""
        plan = actions.plan_for(self.soul, "hunt")
        self.assertEqual([s["do"] for s in plan["steps"]], ["hunt"])

    def test_the_step_runs_the_beat_and_holds_position(self):
        from world.souls import jobs
        self.soul.db.soul_job = actions.plan_for(self.soul, "hunt")
        with mock.patch("world.director.hunt.tick_hunt",
                        return_value=True) as hunted:
            self.assertTrue(jobs.step_job(self.soul))
        hunted.assert_called_once()
        self.assertEqual(self.soul.db.soul_job["at"], 0)   # not advanced

    def test_giving_up_ends_the_job_without_faulting(self):
        """A fault COOLS the goal. Cooling `hunt` would blind the unit to
        the next intruder for the whole cooldown — a security hole
        wearing the costume of tidiness."""
        from world.souls import jobs
        self.soul.db.soul_job = actions.plan_for(self.soul, "hunt")
        with mock.patch("world.director.hunt.tick_hunt", return_value=False), \
                mock.patch.object(jobs, "fault") as faulted:
            self.assertFalse(jobs.step_job(self.soul))
        faulted.assert_not_called()
        self.assertIsNone(self.soul.db.soul_job)
