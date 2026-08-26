"""The colony keeps a record of what it did (#2318).

Three surfaces recorded soul behaviour before this and none remembered:
the WSIS bus decays by design ("always 'lately', never 'ever'"),
`soul_faults` keeps the last FIVE per soul, and `server.log` hears from
souls exactly once, on arrival.

So there was no way to ask whether last week was worse than this week,
which route keeps failing, or whether anybody ever buys clothes. Every
soul bug found on 2026-08-25 — a courier who started one run and
finished none, five souls failing to path to a padlocked shutter for
hours — was found by a human happening to look.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import audit


class TestTheLineFormat(EvenniaCommandTest):
    """`kind key=value ...` — greppable with no parser, parseable with
    a trivial one. Every field is exactly one whitespace token."""

    def _line(self, fn, *a, **kw):
        # `record()` skips the write under test so the suite stops
        # appending its fixtures to the production log (#2328). These
        # tests are ABOUT the write, so they opt back in explicitly.
        with mock.patch.object(audit, "_under_test", return_value=False), \
                mock.patch.object(audit, "_logger") as lg:
            fn(*a, **kw)
        return lg.return_value.info.call_args.args[0]

    def test_a_goal_line(self):
        line = self._line(audit.goal, self.char1, "duty", band=2, hour=17.5)
        self.assertTrue(line.startswith("goal "))
        self.assertIn("goal=duty", line)
        self.assertIn("band=2", line)
        self.assertIn("hour=17.5", line)

    def test_a_fault_line_carries_the_reason(self):
        """The single most useful line in the file."""
        line = self._line(audit.fault, self.char1, "run",
                          "no path to Community Thrift")
        self.assertIn("goal=run", line)
        self.assertIn("reason=no_path_to_Community_Thrift", line)

    def test_every_field_is_one_token(self):
        """Spaces become underscores so the line splits forever."""
        line = self._line(audit.fault, self.char1, "run", "a b c d")
        for token in line.split():
            self.assertNotIn(" ", token)
        self.assertEqual(len(line.split()), len(line.split(" ")))

    def test_a_soul_is_identified_by_key_AND_dbref(self):
        """Keys repeat across resleeves; dbrefs do not."""
        line = self._line(audit.done, self.char1, "duty")
        self.assertIn(f"#{self.char1.id}", line)

    def test_missing_values_are_still_tokens(self):
        line = self._line(audit.life, self.char1, "death", None)
        self.assertIn("detail=-", line)

    def test_an_equals_in_a_value_cannot_forge_a_field(self):
        line = self._line(audit.fault, self.char1, "run", "a=b")
        self.assertIn("reason=a-b", line)

    def test_coin_records_the_counterparty(self):
        line = self._line(audit.coin, self.char1, 1, "delivery",
                          other=self.char2)
        self.assertIn("amount=1", line)
        self.assertIn("why=delivery", line)
        self.assertIn(f"#{self.char2.id}", line)


class TestObservationNeverBreaksTheThingObserved(EvenniaCommandTest):
    def test_a_broken_logger_is_swallowed(self):
        with mock.patch.object(audit, "_under_test", return_value=False), \
             mock.patch.object(audit, "_logger",
                               side_effect=RuntimeError("disk full")):
            audit.goal(self.char1, "duty")      # must not raise

    def test_a_soul_that_is_gone_still_logs(self):
        with mock.patch.object(audit, "_under_test", return_value=False), \
             mock.patch.object(audit, "_logger") as lg:
            audit.fault(None, "duty", "vanished")
        self.assertIn("who=-", lg.return_value.info.call_args.args[0])


class TestItIsWiredWhereDecisionsHappen(EvenniaCommandTest):
    """The value is entirely in the call sites. A perfect writer nobody
    calls is the exact bug this file exists to make findable."""

    def test_choosing_a_goal_is_recorded(self):
        import inspect
        from world.souls import engine
        self.assertIn("audit.goal(", inspect.getsource(engine.think))

    def test_faulting_is_recorded(self):
        import inspect
        from world.souls import jobs
        self.assertIn("audit.fault(", inspect.getsource(jobs.fault))

    def test_finishing_is_recorded(self):
        import inspect
        from world.souls import jobs
        self.assertIn("audit.done(", inspect.getsource(jobs.step_job))

    def test_wages_are_recorded(self):
        import inspect
        from world.souls import economy
        self.assertIn("audit.coin(", inspect.getsource(economy))

    def test_delivery_fees_are_recorded_paid_and_unpaid(self):
        import inspect
        from world.director import courier
        src = inspect.getsource(courier.hand_over)
        self.assertIn('"delivery"', src)
        self.assertIn('"delivery_unpaid"', src)

    def test_lifecycle_is_recorded(self):
        import inspect
        from world.souls import engine
        from typeclasses.characters import Character
        self.assertIn("audit.life(", inspect.getsource(engine.ensoul))
        self.assertIn("audit.life(", inspect.getsource(Character.at_death))


class TestRotation(EvenniaCommandTest):
    def test_it_ages_out_alongside_the_combat_audit(self):
        """Same rotation settings, so the two logs cover the same
        window and can be read against each other."""
        import inspect
        src = inspect.getsource(audit._logger)
        self.assertIn("CHANNEL_LOG_ROTATE_SIZE", src)
        self.assertIn("backupCount=100", src)


class TestTheSuiteDoesNotWriteToTheRealLog(EvenniaCommandTest):
    """The suite appended its fixtures to the production log — lines
    like `who=Char#6 at=Room reason=radio_work_crashed:_boom`, where
    `Char`, `Room` and `boom` are a fixture and a mock, not a colonist
    and an accident (#2328).

    Found by reading the log this was built to produce, which is the
    system catching its own contamination.
    """

    def test_record_is_silent_under_test(self):
        with mock.patch.object(audit, "_logger") as lg:
            audit.goal(self.char1, "duty")
        lg.assert_not_called()

    def test_the_runner_is_detected(self):
        self.assertTrue(audit._under_test())

    def test_detection_reads_the_database_not_just_argv(self):
        """Evennia's test DB is IN-MEMORY, not the `test_`-prefixed
        file the docs describe — the first version of this check
        assumed the docs and still leaked six lines."""
        import inspect
        src = inspect.getsource(audit._under_test)
        self.assertIn("memory", src)
        self.assertIn("sys.argv", src)
