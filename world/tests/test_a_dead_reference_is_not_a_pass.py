"""A reference that no longer resolves is not a pass (#3562, #3563, #3564,
#3566). Four guards from the 2026-09-15 dangling-back-reference audit read a
deleted object as None and then treated None as permission:

* a security bot whose base room was deleted uplinked its sightings from
  anywhere (`sync_bot_intel`);
* a soul whose cube or post room was deleted "slept at home" in the street
  and "worked" at nothing (the sleep and work steps);
* a soul whose post fixture was deleted stayed employed at nothing, never a
  candidate and never unemployed (the vacancy sweep);
* a security unit whose casualty was deleted never recovered anyone again
  (the recovery stamp, a raw id tested for truthiness and never released
  by a preemption or a dispatch overwrite).
"""
import inspect
from types import SimpleNamespace
from unittest import TestCase, mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.director import intel
from world.souls import engine, jobs, posts


class TheBotWithNoPostNeverSyncs(TestCase):

    def setUp(self):
        intel.clear_wanted_record()

    def tearDown(self):
        intel.clear_wanted_record()

    @staticmethod
    def _bot(post, location):
        return SimpleNamespace(db=SimpleNamespace(role="security", post=post), location=location)

    def test_a_deleted_base_reads_none_and_the_bot_keeps_its_sightings(self):
        bot = self._bot(None, SimpleNamespace(pk=5))
        intel.log_local_sighting(bot, "FACE1", "murder")
        self.assertEqual(intel.sync_bot_intel(bot), 0)
        self.assertIsNone(intel.is_wanted("FACE1"))
        self.assertEqual(bot.db.local_sightings["FACE1"]["count"], 1)

    def test_a_stale_post_instance_with_no_pk_is_not_home(self):
        base = SimpleNamespace(pk=None)
        bot = self._bot(base, base)
        intel.log_local_sighting(bot, "FACE1", "murder")
        self.assertEqual(intel.sync_bot_intel(bot), 0)

    def test_a_bot_away_from_its_post_does_not_sync(self):
        bot = self._bot(SimpleNamespace(pk=1), SimpleNamespace(pk=2))
        intel.log_local_sighting(bot, "FACE1", "murder")
        self.assertEqual(intel.sync_bot_intel(bot), 0)

    def test_control_a_bot_at_its_post_syncs(self):
        base = SimpleNamespace(pk=1)
        bot = self._bot(base, base)
        intel.log_local_sighting(bot, "FACE1", "murder")
        self.assertEqual(intel.sync_bot_intel(bot), 1)
        self.assertEqual(intel.is_wanted("FACE1")["count"], 1)


class TheSleepAndWorkStepsFaultWithoutAHomeOrPost(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = create_object("typeclasses.characters.Character", key="Dorn", location=self.room1)
        self.soul.db.is_npc = True
        self.soul.db.species = "human"
        engine.ensoul(self.soul, role="worker", home=None, post=None)
        self.said = []
        self.soul.execute_cmd = lambda text=None, **kw: self.said.append(str(text))

    def _step(self, do):
        self.soul.db.soul_job = {"goal": "rest" if do == "sleep" else "duty", "band": 2, "at": 0,
                                 "steps": [{"do": do}]}
        return jobs.step_job(self.soul)

    def test_no_home_faults_the_sleep_step(self):
        self.assertFalse(self._step("sleep"))
        self.assertIsNone(self.soul.db.soul_job)
        self.assertIn("no home at sleep step", self.soul.db.soul_faults[-1][1])
        self.assertFalse(any("settles in" in s for s in self.said))

    def test_control_at_home_the_soul_settles_in(self):
        self.soul.db.soul_home = self.room1
        with mock.patch("world.souls.needs.pressure", return_value=1.0):
            self.assertTrue(self._step("sleep"))
        self.assertTrue(any("settles in" in s for s in self.said))
        self.assertEqual(list(self.soul.db.soul_faults or []), [])

    def test_no_post_faults_the_work_step(self):
        self.assertFalse(self._step("work"))
        self.assertIsNone(self.soul.db.soul_job)
        self.assertIn("no post at work step", self.soul.db.soul_faults[-1][1])

    def test_control_at_the_post_the_shift_is_not_a_fault(self):
        self.soul.db.soul_post = self.room1
        with mock.patch("world.souls.salience.do_post_work"):
            self._step("work")
        self.assertEqual(list(self.soul.db.soul_faults or []), [])


class TheSweepReleasesASoulEmployedAtNothing(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = create_object("typeclasses.characters.Character", key="Keeper", location=self.room1)
        self.soul.db.is_npc = True
        self.soul.db.species = "human"
        engine.ensoul(self.soul, role="worker", home=self.room1, post=None)
        self.post = self.obj1
        self.post.location = self.room1
        posts.register_post(self.post, role="clerk", schedule="day", policy="successor", delay=0)

    def _claim(self, with_register):
        if with_register:
            self.post.db.register = self.obj2
        with mock.patch("world.souls.thoughts.add_thought"):
            posts.do_claim(self.soul, self.post, "day")

    def test_a_deleted_fixture_releases_its_keeper(self):
        from world.souls.population import unemployed_count
        self._claim(with_register=True)
        self.assertEqual(self.soul.db.soul_venue, self.post)
        self.assertEqual(unemployed_count([self.soul]), 0)
        self.post.delete()
        self.assertEqual(posts.release_the_orphaned(), [self.soul])
        self.assertIsNone(self.soul.db.soul_post)
        self.assertIsNone(self.soul.db.soul_venue)
        self.assertEqual(self.soul.db.soul_wage_rate, 0.0)
        self.assertEqual(unemployed_count([self.soul]), 1)
        self.assertEqual(posts.release_the_orphaned(), [])      # once

    def test_a_treasury_post_is_not_mistaken_for_a_dead_venue(self):
        self._claim(with_register=False)
        self.assertIsNone(self.soul.db.soul_venue)
        self.assertEqual(posts.release_the_orphaned(), [])
        self.assertEqual(self.soul.db.soul_post, self.room1)

    def test_a_deleted_post_room_releases_too(self):
        annex = create_object("typeclasses.rooms.Room", key="Annex")
        self.soul.db.soul_post = annex
        self.soul.db.soul_wage_rate = 0.05
        annex.delete()
        self.assertIsNone(self.soul.db.soul_post)
        self.assertEqual(posts.release_the_orphaned(), [self.soul])
        self.assertEqual(self.soul.db.soul_wage_rate, 0.0)

    def test_the_sweep_runs_the_release(self):
        self._claim(with_register=True)
        self.post.delete()
        with mock.patch("world.director.security._in_combat", return_value=False):
            posts.sweep(1000.0)
        self.assertIsNone(self.soul.db.soul_post)


class TheStampLetsGoOfTheDead(EvenniaTest):

    def _unit(self, key):
        unit = create_object("typeclasses.characters.Character", key=key, location=self.room1)
        unit.db.role = "security"
        unit.db.species = "robot"
        return unit

    def setUp(self):
        super().setUp()
        self.unit = self._unit("Unit A")
        self.casualty = self._unit("Unit B")
        self.plan = mock.patch("world.souls.actions.plan_for",
                               return_value={"goal": "recover", "at": 0, "steps": []})
        self.plan.start()
        self.addCleanup(self.plan.stop)

    def test_a_stamp_naming_a_deleted_casualty_holds_nothing(self):
        from world.director import medical
        self.unit.db.soul_recovering = 99999999
        self.assertTrue(medical.recover_casualty(self.unit, self.casualty))
        self.assertEqual(self.unit.db.soul_recovering, self.casualty.id)

    def test_a_live_stamp_still_blocks(self):
        from world.director import medical
        other = self._unit("Unit C")
        self.unit.db.soul_recovering = other.id
        self.assertFalse(medical.recover_casualty(self.unit, self.casualty))
        self.assertEqual(self.unit.db.soul_recovering, other.id)

    def test_a_dispatch_overwrite_lets_the_casualty_go(self):
        from world.director import WorldEvent, assignment
        engine.ensoul(self.unit, role="security")
        self.unit.db.soul_recovering = self.casualty.id
        self.addCleanup(assignment.clear_assignment, self.unit)
        with mock.patch("world.director.assignment.travel_to", return_value=True):
            self.assertTrue(assignment.assign(self.unit, WorldEvent("assault", self.room2)))
        self.assertIsNone(self.unit.db.soul_recovering)
        self.assertEqual(self.unit.db.soul_job["goal"], "respond")

    def test_a_preemption_lets_the_casualty_go(self):
        # The preemption branch of think() is the third drop; it is wired to
        # the same release the fault and the delivery use.
        source = inspect.getsource(engine.think)
        self.assertIn("jobs.release_recovery(soul)", source)
        soul = SimpleNamespace(db=SimpleNamespace(soul_recovering=4242))
        jobs.release_recovery(soul)
        self.assertIsNone(soul.db.soul_recovering)
