"""Becoming overdue for service must not cancel the running job (#2695).

`_wear_and_tear` reported a maintenance threshold through `jobs.fault`
-- the job-ABORT path -- so a status change was processed as a failed
plan. `fault` does three things a maintenance notice should not:

1. cools the running goal, so a unit that crossed its service interval
   while working lost its post for the cooldown period;
2. files the audit line under whatever goal happened to be running, so
   an operator reads a `duty` fault whose message is about service
   intervals;
3. releases any recovery claim.

The neglect consequence landed on the unit's WORK rather than on the
unit. The cooldown exists for plans that CANNOT succeed (#2375); a unit
due for service has a perfectly good plan and is simply also due for
service.
"""
from unittest import TestCase, mock

from world.souls import jobs


def _soul(goal="duty"):
    soul = mock.MagicMock()
    soul.db.soul_job = {"goal": goal}
    soul.db.soul_faults = []
    soul.db.soul_goal_cooldown = {}
    soul.db.soul_recovering = 4242
    return soul


class TestNoteFaultRecordsWithoutAborting(TestCase):
    def _note(self, soul, **kw):
        with mock.patch("world.souls.audit.fault") as filed:
            jobs.note_fault(soul, "service overdue", **kw)
        return filed

    def test_it_does_not_clear_the_running_job(self):
        soul = _soul()
        self._note(soul)
        self.assertEqual(soul.db.soul_job, {"goal": "duty"},
                         "a status change cancelled the plan")

    def test_it_does_not_cool_the_goal(self):
        soul = _soul()
        self._note(soul)
        self.assertEqual(soul.db.soul_goal_cooldown, {},
                         "the unit lost its post to a service notice")

    def test_it_does_not_release_a_recovery_claim(self):
        soul = _soul()
        self._note(soul)
        self.assertEqual(soul.db.soul_recovering, 4242)

    def test_it_still_records_the_audit_line(self):
        """The point of reporting it at all."""
        soul = _soul()
        filed = self._note(soul)
        self.assertTrue(filed.called)
        self.assertEqual(filed.call_args.args[2], "service overdue")

    def test_it_labels_the_line_with_its_own_goal(self):
        soul = _soul()
        filed = self._note(soul, goal="maintenance")
        self.assertEqual(filed.call_args.args[1], "maintenance")

    def test_without_a_goal_it_borrows_the_running_one(self):
        """Backward-compatible for `fault`, which has no goal of its
        own — the failure belongs to whatever was running."""
        soul = _soul()
        filed = self._note(soul)
        self.assertEqual(filed.call_args.args[1], "duty")

    def test_it_still_appends_to_the_fault_log(self):
        soul = _soul()
        self._note(soul)
        self.assertEqual(len(soul.db.soul_faults), 1)


class TestFaultStillAborts(TestCase):
    """The pin: splitting the recording half out must not weaken the
    abort half. A plan that cannot succeed still has to stop."""

    def _fault(self, soul):
        with mock.patch("world.souls.audit.fault"), \
             mock.patch.object(jobs, "stop_travel") as stopped, \
             mock.patch.object(jobs, "_signal"):
            jobs.fault(soul, "no route at all")
        return stopped

    def test_it_clears_the_job(self):
        soul = _soul()
        self._fault(soul)
        self.assertIsNone(soul.db.soul_job)

    def test_it_cools_the_goal(self):
        soul = _soul()
        self._fault(soul)
        self.assertIn("duty", soul.db.soul_goal_cooldown)

    def test_it_releases_the_recovery_claim(self):
        soul = _soul()
        self._fault(soul)
        self.assertIsNone(soul.db.soul_recovering)

    def test_it_stops_travel(self):
        soul = _soul()
        self.assertTrue(self._fault(soul).called)


class TestTheEngineUsesTheRightChannel(TestCase):
    def test_wear_and_tear_notes_rather_than_faults(self):
        import inspect

        import world.souls.engine as engine
        src = inspect.getsource(engine._wear_and_tear)
        self.assertIn("jobs.note_fault(", src)
        self.assertNotIn("jobs.fault(", src)

    def test_it_labels_the_line_maintenance(self):
        import inspect

        import world.souls.engine as engine
        self.assertIn('goal="maintenance"',
                      inspect.getsource(engine._wear_and_tear))
