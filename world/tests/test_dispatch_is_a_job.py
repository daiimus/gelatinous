"""Dispatch hands out work; it does not seize a body (#2384).

`assign()` used to record the responder in a module dict, start its own
travel, and hold it on scene with a self-re-arming timer — while
`souls.think()` opened with `if is_assigned(soul): return`. The unit's
mind was switched OFF for the whole call.

That is a boolean where a BAND belongs, and it cost once already:
nothing cleared the assignment on death, so a wrecked unit's soul stayed
asleep permanently, even after being repaired (#2255).

Now the assignment IS a band-0 job. The unit still cannot wander off a
call — band 0 outranks every need — but it is arbitrated rather than
silenced.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.director import WorldEvent
from world.director import assignment as amod
from world.souls import engine, jobs


class _Scene(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.unit = create_object("typeclasses.llm_npc.LLMNpc",
                                  key="unit", location=self.room1)
        self.unit.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        self.unit.db.role = "security"
        self.unit.db.post = self.room1
        self.event = WorldEvent(type="assault", location=self.room2,
                                severity=2)

    def tearDown(self):
        amod.clear_assignment(self.unit)
        super().tearDown()

    def _steps(self):
        return [s["do"] for s in (self.unit.db.soul_job or {}).get("steps", [])]


class TestAssignmentIsAJob(_Scene):

    def test_a_souled_responder_is_handed_work(self):
        self.assertTrue(amod.assign(self.unit, self.event))
        self.assertEqual(self._steps(),
                         ["travel", "respond", "travel", "stand_down"])

    def test_it_sits_at_band_zero(self):
        """A unit must not wander off a call — the thing the silence
        switch was protecting. Band 0 protects it by ARBITRATION."""
        amod.assign(self.unit, self.event)
        self.assertEqual(self.unit.db.soul_job["band"], 0)
        self.assertEqual(engine._goal_band("respond"), 0)

    def test_the_director_no_longer_drives_the_body(self):
        with mock.patch.object(amod, "travel_to") as walked:
            amod.assign(self.unit, self.event)
        walked.assert_not_called()

    def test_an_unsouled_responder_is_still_driven(self):
        """Fails toward the body moving. Nothing is in this state today,
        but a responder that stands still is worse than one the old path
        walks."""
        self.unit.tags.remove(engine.SOUL_TAG[0],
                              category=engine.SOUL_TAG[1])
        with mock.patch.object(amod, "travel_to", return_value=True) as walked:
            amod.assign(self.unit, self.event)
        walked.assert_called_once()


class TestTheRespondStep(_Scene):

    def _run(self):
        return jobs.step_job(self.unit)

    def test_arrival_runs_once_then_the_watch_ticks(self):
        amod.assign(self.unit, self.event)
        self.unit.db.soul_job["at"] = 1           # as if travel finished
        with mock.patch.object(amod, "run_arrival") as arrived, \
                mock.patch.object(amod, "run_watch",
                                  return_value=True) as watched:
            self._run()
            arrived.assert_called_once()
            watched.assert_not_called()           # arrival beat only
            self._run()
            arrived.assert_called_once()          # not again
            watched.assert_called_once()

    def test_when_the_watch_ends_it_walks_home(self):
        amod.assign(self.unit, self.event)
        self.unit.db.soul_job["at"] = 1
        with mock.patch.object(amod, "run_arrival"), \
                mock.patch.object(amod, "run_watch", return_value=False):
            self._run()                            # arrival
            self._run()                            # watch says done
        self.assertEqual(self.unit.db.soul_job["at"], 2)
        self.assertEqual(self._steps()[2], "travel")

    def test_a_call_closed_under_it_is_not_a_fault(self):
        """Stood down mid-travel: the call was closed or the unit
        released. Nothing went wrong, so nothing should fault."""
        amod.assign(self.unit, self.event)
        self.unit.db.soul_job["at"] = 1
        amod.clear_assignment(self.unit)
        with mock.patch.object(jobs, "fault") as faulted:
            self._run()
        faulted.assert_not_called()
        self.assertIsNone(self.unit.db.soul_job)

    def test_standing_down_settles_through_the_director(self):
        amod.assign(self.unit, self.event)
        self.unit.db.soul_job["at"] = 3            # the stand_down step
        with mock.patch.object(amod, "finish") as settled:
            self._run()
        settled.assert_called_once()
        self.assertIsNone(self.unit.db.soul_job)


class TestTheMindStaysOn(_Scene):

    def test_think_no_longer_returns_early_on_an_assignment(self):
        """The regression that bricked a unit for good: a wrecked
        responder's soul never thought again, because nothing cleared
        the assignment and `think` bailed on it (#2255)."""
        import inspect
        src = inspect.getsource(engine.think)
        self.assertNotIn("if is_assigned(soul):", src)
