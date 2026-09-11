"""The combat-audit sink writes through a module-owned stdlib logger.

Evennia's threaded ``logger.log_file`` recycles its cached handle every
500th access on the reactor while queued thread writes still hold it —
every recycle boundary silently dropped the queue (7.9k lines rendered
as ``NoneType: None`` until #1094 unmasked it). The sink now owns a
stdlib rotating handler: per-write locking, safe rollover, Evennia core
untouched.
"""

import logging
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.combat.debug as dbg


class TestAuditSink(TestCase):
    def tearDown(self):
        dbg._AUDIT_LOGGER.clear()

    def test_msg_writes_through_the_owned_logger(self):
        fake = MagicMock()
        with patch.object(dbg, "_under_test", return_value=False), \
                patch.object(dbg, "_get_audit_logger", return_value=fake), \
                patch.object(dbg, "_get_live_channel", return_value=None):
            dbg.get_splattercast().msg("CONDITION_START: test line")
        fake.info.assert_called_once_with("CONDITION_START: test line")

    def test_logger_is_cached_and_rotating(self):
        dbg._AUDIT_LOGGER.clear()
        log = dbg._get_audit_logger()
        self.assertIs(dbg._get_audit_logger(), log)     # per-process cache
        self.assertFalse(log.propagate)                  # never up to root
        self.assertTrue(any(
            isinstance(h, logging.handlers.RotatingFileHandler)
            for h in log.handlers))

    def test_io_failure_never_breaks_combat(self):
        fake = MagicMock()
        fake.info.side_effect = OSError("disk full")
        with patch.object(dbg, "_under_test", return_value=False), \
                patch.object(dbg, "_get_audit_logger", return_value=fake):
            dbg.get_splattercast().msg("boom")           # must not raise


class TestTheSuiteDoesNotWriteToTheRealLog(TestCase):
    """#2328: a suite run appended its fixtures to the production log.

    `combat_audit.log` had it worst — months of runs left thousands of
    `MagicMock` references in it.
    """

    def test_the_write_is_skipped_under_test(self):
        fake = MagicMock()
        with patch.object(dbg, "_get_audit_logger", return_value=fake):
            dbg._AuditRouter().msg("fixture noise")
        fake.info.assert_not_called()

    def test_the_detector_is_shared_with_the_souls_log(self):
        """One door: the check is subtle (Evennia's test DB is
        in-memory, not `test_`-prefixed) and two copies would drift."""
        from world import audit_guard
        from world.souls import audit as souls_audit

        self.assertTrue(audit_guard.under_test())
        self.assertTrue(souls_audit._under_test())
        self.assertTrue(dbg._under_test())
