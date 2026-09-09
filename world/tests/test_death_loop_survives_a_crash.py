"""The death loop survives a boot with no clean shutdown, and a revived
medical tick cannot double-fire a death (#2938 follow-up).

Two scripts drive dying: `MedicalScript` decides a body has crossed the
line and calls `at_death`; `DeathProgressionScript` then runs the
90-second window that spawns the corpse and disposes of the sleeve.
Both are per-object timed Scripts, so both have the lifecycle gap
#3075 documents -- a crash or kill leaves them `db_is_active=True`
with no timer, permanently.

For the medical script that meant sedations that never wore off. For
the death script it would mean a body that died and then simply lay
there: no corpse, no husk, `db.death_processed=True` so `at_death`
refuses to retry, and `sweep_wedged_deaths` unable to see it because
that sweep restarts a progression that never STARTED and takes an
existing script row as proof one is running.

The other half of the owner's concern: once a medical script is
re-armed, a body that died while it was inert gets ticked again and
`is_dead()` is still true. That must not re-run the death. It doesn't,
because `at_death` is guarded by PERSISTENT `db.death_processed` --
the `ndb` check in `at_repeat` is a second, non-persistent guard in
front of a persistent one. These tests pin that the persistent guard
is the one that holds.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition
from world.medical.script import start_medical_script


def _crash(script):
    """The state a hard kill leaves: no task, no recorded pause."""
    task = script.ndb._task
    if task and task.running:
        task.stop()
    script.ndb._task = None
    script.db._paused_time = None
    script.db._manually_paused = None


def _running(script):
    task = script.ndb._task
    return bool(task and task.running)


class TestTheDeathScriptRearms(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.body = create_object("typeclasses.characters.Character",
                                  key="a dying body", location=self.room1)
        self.body.msg = lambda text=None, **kw: None
        # The real constructor cannot run inside EvenniaTest -- the
        # repo's own death-reload test says so and patches around it
        # ("creating a real DeathProgressionScript inside EvenniaTest
        # trips a harness artifact"). The constructor is not what is
        # under test. `_Probe` keeps the REAL class hierarchy -- the
        # real `at_server_start` and the real `at_start` -- and replaces
        # only `at_script_creation` with the two fields the timer needs.
        from typeclasses.death_progression import (
            DEATH_PROGRESSION_CHECK_INTERVAL, DeathProgressionScript)

        class _Probe(DeathProgressionScript):
            def at_script_creation(self):
                self.key = "death_progression"
                self.persistent = True
                self.interval = DEATH_PROGRESSION_CHECK_INTERVAL

        self.script = self.body.scripts.add(_Probe)

    def tearDown(self):
        try:
            self.script._stop_task()
        except Exception:
            pass
        super().tearDown()

    def test_creation_arms_a_task(self):
        """Vacuity guard for everything below."""
        self.assertTrue(_running(self.script))

    def test_evennia_alone_does_not_recover_a_crashed_death(self):
        _crash(self.script)
        self.script._unpause_task(auto_unpause=True)
        self.assertFalse(_running(self.script))

    def test_the_hook_recovers_it(self):
        _crash(self.script)
        self.script.at_server_start()
        self.assertTrue(_running(self.script))

    def test_a_clean_reload_is_not_double_started(self):
        self.script._pause_task(auto_pause=True)
        self.script._unpause_task(auto_unpause=True)
        task = self.script.ndb._task
        self.script.at_server_start()
        self.assertIs(self.script.ndb._task, task)

    def test_the_sweep_would_not_have_caught_this(self):
        """Documents WHY the hook is needed: the existing sweep sees a
        script row and concludes the progression is running."""
        from typeclasses.death_progression import is_wedged_death
        self.body.db.death_processed = True
        _crash(self.script)
        self.assertFalse(is_wedged_death(self.body))


class TestARevivedMedicalTickCannotDoubleFireDeath(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.body = create_object("typeclasses.characters.Character",
                                  key="a corpse-to-be", location=self.room1)
        self.body.msg = lambda text=None, **kw: None
        state = self.body.medical_state
        state.conditions.append(BleedingCondition(severity=8, location="chest"))
        self.body.medical_state = state
        self.body.save_medical_state()
        self.script = start_medical_script(self.body)
        # The body died while the script was inert: death already
        # processed and persisted, ndb flag gone with the process.
        self.body.db.death_processed = True
        self.body.ndb.death_processed = None
        state.blood_level = 0.0
        self.body.save_medical_state()
        self.calls = []
        real = self.body.at_death
        def counting(*a, **kw):
            self.calls.append(1)
            return real(*a, **kw)
        self.body.at_death = counting

    def tearDown(self):
        try:
            self.script._stop_task()
        except Exception:
            pass
        super().tearDown()

    def test_the_body_reads_dead(self):
        """Vacuity guard: if it is not dead the branch under test never
        runs."""
        self.assertTrue(self.body.medical_state.is_dead())

    def test_the_ndb_guard_is_gone_after_a_reload(self):
        """The non-persistent guard is exactly what a crash erases."""
        self.assertFalse(bool(self.body.ndb.death_processed))

    def test_the_persistent_guard_stops_a_second_death(self):
        _crash(self.script)
        self.script.at_server_start()
        self.script.at_repeat()
        # at_death was reached (ndb guard gone) but returned early on
        # db.death_processed -- no second death progression exists.
        self.assertEqual(self.body.scripts.get("death_progression").count(), 0)

    def test_the_medical_script_stops_rather_than_looping(self):
        _crash(self.script)
        self.script.at_server_start()
        self.script.at_repeat()
        self.assertFalse(_running(self.script))
