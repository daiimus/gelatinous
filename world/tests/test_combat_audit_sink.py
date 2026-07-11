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
        with patch.object(dbg, "_get_audit_logger", return_value=fake), \
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
        with patch.object(dbg, "_get_audit_logger", return_value=fake):
            dbg.get_splattercast().msg("boom")           # must not raise
