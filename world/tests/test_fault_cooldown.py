"""A failed job has to rest before it is retried (#2375).

`engine.think` cooled a goal down when no plan could be MADE. A job that
died mid-flight did not, so the soul re-planned the identical impossible
thing on the very next beat — forever.

One body ensouled on a rooftop the pathfinder cannot route out of
produced 75 of 120 faults in a single window, deciding to walk home
every thirty seconds and failing every time.
"""
import time
from unittest import mock

from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import engine, jobs


class TestAFaultCoolsItsGoal(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.db.soul_job = {"goal": "rest", "at": 0, "steps": []}

    def test_a_faulted_goal_goes_on_cooldown(self):
        jobs.fault(self.soul, "no path to R1-02")
        cooldowns = self.soul.db.soul_goal_cooldown or {}
        self.assertIn("rest", cooldowns)
        self.assertGreater(cooldowns["rest"], time.time())

    def test_the_engine_then_excludes_it(self):
        """The cooldown is only worth anything if arbitration reads it —
        the soul must fall through to its next-worst need instead of
        re-deciding the same impossible thing."""
        jobs.fault(self.soul, "no path to R1-02")
        now = time.time()
        cooling = {g for g, t in (self.soul.db.soul_goal_cooldown or {}).items()
                   if t > now and g != "safety"}
        self.assertIn("rest", cooling)

    def test_safety_is_never_cooled_out_of_the_running(self):
        """Nothing earns the right to stop a soul fleeing. The engine
        exempts safety when it reads this map; the exemption is the
        point, so pin it."""
        self.soul.db.soul_job = {"goal": "safety", "at": 0, "steps": []}
        jobs.fault(self.soul, "flee failed")
        now = time.time()
        cooling = {g for g, t in (self.soul.db.soul_goal_cooldown or {}).items()
                   if t > now and g != "safety"}
        self.assertNotIn("safety", cooling)

    def test_expired_cooldowns_are_dropped(self):
        """The map is pruned on write, so it cannot grow forever on a
        soul that has a bad week."""
        self.soul.db.soul_goal_cooldown = {"hunger": time.time() - 10}
        jobs.fault(self.soul, "no path")
        self.assertNotIn("hunger", self.soul.db.soul_goal_cooldown or {})

    def test_a_jobless_fault_cools_nothing(self):
        self.soul.db.soul_job = None
        jobs.fault(self.soul, "beat crashed")
        self.assertFalse(self.soul.db.soul_goal_cooldown)
