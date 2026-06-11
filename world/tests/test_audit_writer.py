"""Tests for the serialized audit-log writer (issue #489).

The writer replaced ``evennia.utils.logger.log_file`` for audit
traffic after diagnosing that helper's burst-load failure modes:
handle recycling racing in-flight thread writes, and an errback that
destroys the real error (the ``NoneType: None`` server-log floods —
each line a silently dropped audit write).

These tests drive the thread-side internals synchronously; the
serialization property itself is structural (one deferred chain).

Run via::

    evennia test --settings settings.py world.tests.test_audit_writer
"""

from __future__ import annotations

import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.combat.debug import _AuditFileWriter


class TestAuditWriterSync(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.writer = _AuditFileWriter("audit_test.log")
        patcher = patch("world.combat.debug.settings")
        self.mock_settings = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_settings.LOG_DIR = self.tmp.name
        self.mock_settings.CHANNEL_LOG_ROTATE_SIZE = 1_000_000
        self.addCleanup(self.tmp.cleanup)

    def _read(self):
        with open(os.path.join(self.tmp.name, "audit_test.log")) as f:
            return f.read()

    def test_writes_append_and_flush(self):
        self.writer._write_sync("\nline one")
        self.writer._write_sync("\nline two")
        content = self._read()
        self.assertIn("line one", content)
        self.assertIn("line two", content)

    def test_rotation_inside_the_write_path(self):
        """Crossing the size threshold renames the file to a
        timestamped generation; the next write starts fresh."""
        self.mock_settings.CHANNEL_LOG_ROTATE_SIZE = 1000
        self.writer._write_sync("\n" + "x" * 1200)
        self.writer._write_sync("\nafter rotation")

        names = os.listdir(self.tmp.name)
        rotated = [n for n in names if n.startswith("audit_test.log.")]
        self.assertEqual(len(rotated), 1)
        self.assertIn("after rotation", self._read())
        self.assertNotIn("xxx", self._read())

    def test_failure_reports_real_traceback_and_recovers(self):
        """The #489 contract: a failed write logs the actual
        traceback (never NoneType: None) and the next write reopens."""
        failure = MagicMock()
        failure.getTraceback.return_value = "Traceback: the real error"
        with patch("world.combat.debug.logger") as mock_logger:
            self.writer._handle = MagicMock()  # poisoned handle
            result = self.writer._report_failure(failure)

        self.assertIsNone(result)  # failure consumed; chain continues
        self.assertIsNone(self.writer._handle)  # reopen forced
        logged = str(mock_logger.log_err.call_args)
        self.assertIn("AUDIT_WRITE_FAILED", logged)
        self.assertIn("the real error", logged)

        # Next write recovers cleanly.
        self.writer._write_sync("\nrecovered")
        self.assertIn("recovered", self._read())
