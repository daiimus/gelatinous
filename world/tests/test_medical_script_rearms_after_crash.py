"""A medical script comes back after a boot that had no clean shutdown (#2938).

A Script's timer is `ndb._task` -- non-persistent by design. Evennia
restores it across a reload by pausing on the way down and unpausing on
the way up:

    shutdown   _pause_task    records db._paused_time  ONLY IF a task exists
    boot       _unpause_task  re-arms                  ONLY IF _paused_time is set

So any shutdown that skips the pause -- a crash, a kill, the Docker VM
going away -- leaves the row `db_is_active=True` with no task, and every
later clean reload no-ops on it. Once inert, permanently inert, with
every DB field still reading healthy. Eight live rows were found in that
state, stale by 9 to 77 days; four held drug sedations that should have
worn off in minutes.

`GLOBAL_SCRIPTS` escape this because the server re-creates and arms them
from settings at every boot. Per-object scripts have no such owner.

The fix is the hook Evennia provides for exactly this. `at_server_start`
runs for every active script at boot, AFTER `_unpause_task`, and
`start()` is idempotent -- it returns at once if a task is already
running. So on a clean reload it does nothing, and after a crash it is
the recovery. Public API only; the framework is not patched.

These tests drive the real Evennia machinery rather than mocking it:
the task object is `ndb._task`, and its `.running` flag is what the
reactor honours.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import PainCondition
from world.medical.script import start_medical_script


class _ScriptCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.body = create_object("typeclasses.characters.Character",
                                  key="a body", location=self.room1)
        self.body.msg = lambda text=None, **kw: None
        state = self.body.medical_state
        state.conditions.append(PainCondition(severity=3, location="chest"))
        self.body.medical_state = state
        self.body.save_medical_state()
        self.script = start_medical_script(self.body)

    def tearDown(self):
        try:
            self.script._stop_task()
        except Exception:
            pass
        super().tearDown()

    def crash(self):
        """Simulate a hard kill: the task is gone and nothing recorded a
        pause. This is the exact state the eight live rows were in."""
        task = self.script.ndb._task
        if task and task.running:
            task.stop()
        self.script.ndb._task = None
        self.script.db._paused_time = None
        self.script.db._manually_paused = None

    def running(self):
        task = self.script.ndb._task
        return bool(task and task.running)


class TestThePremise(_ScriptCase):
    def test_creation_arms_a_task(self):
        """Vacuity guard: if creation did not arm a task, `crash()`
        would be a no-op and every test below would pass for free."""
        self.assertTrue(self.running())

    def test_a_crash_leaves_the_row_active_but_dead(self):
        self.crash()
        self.assertTrue(self.script.db_is_active)
        self.assertFalse(self.running())

    def test_evennia_alone_does_not_recover_it(self):
        """The framework's own boot path: `_unpause_task` no-ops without
        `_paused_time`. This is the gap, pinned so the fix is not
        mistaken for redundant."""
        self.crash()
        self.script._unpause_task(auto_unpause=True)
        self.assertFalse(self.running())


class TestTheHookRecovers(_ScriptCase):
    def test_at_server_start_rearms_after_a_crash(self):
        self.crash()
        self.script.at_server_start()
        self.assertTrue(self.running())

    def test_the_interval_is_the_constant(self):
        from world.medical.constants import MEDICAL_TICK_INTERVAL
        self.crash()
        self.script.at_server_start()
        self.assertEqual(self.script.db_interval, MEDICAL_TICK_INTERVAL)

    def test_the_row_is_still_the_same_row(self):
        """Re-arming must not create a second script for the body."""
        self.crash()
        self.script.at_server_start()
        self.assertEqual(self.body.scripts.get("medical_script").count(), 1)


class TestTheHookIsIdempotent(_ScriptCase):
    def test_a_running_script_is_left_alone(self):
        """On a clean reload `_unpause_task` has already re-armed; the
        hook must not restart the timer and reset its phase."""
        before = self.script.ndb._task
        self.assertTrue(self.running())
        self.script.at_server_start()
        self.assertIs(self.script.ndb._task, before)

    def test_calling_it_twice_is_harmless(self):
        self.crash()
        self.script.at_server_start()
        first = self.script.ndb._task
        self.script.at_server_start()
        self.assertIs(self.script.ndb._task, first)
        self.assertTrue(self.running())


class TestTheFullBootPath(_ScriptCase):
    """What `update_scripts_after_server_start` actually does, in
    order: unpause, then the hook."""

    def test_crash_then_boot_sequence_recovers(self):
        self.crash()
        self.script._unpause_task(auto_unpause=True)   # framework: no-op
        self.script.at_server_start()                  # ours: recovery
        self.assertTrue(self.running())

    def test_clean_reload_sequence_does_not_double_start(self):
        self.script._pause_task(auto_pause=True)       # clean shutdown
        self.assertIsNotNone(self.script.db._paused_time)
        self.script._unpause_task(auto_unpause=True)   # framework re-arms
        task = self.script.ndb._task
        self.script.at_server_start()
        self.assertIs(self.script.ndb._task, task)
        self.assertTrue(self.running())
