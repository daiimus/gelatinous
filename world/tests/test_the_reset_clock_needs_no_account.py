"""The rate-limit reset clock is global, and its signature says so (#3441).

`get_time_until_reset` declared an `account` parameter it never read.
The body computes the next UTC midnight from `datetime.now(timezone.utc)`
alone, because the reset IS global: every account's quota rolls at the
same UTC midnight, which is what `check_rate_limit` and
`increment_report_count` implement by comparing
`account.db.bug_report_date` against today's date.

A parameter that is already there is an invitation to "implement" a
per-account or per-timezone reset by editing nothing -- a reader assumes
it is honoured. Pin the honest signature: no account goes in, so nobody
believes one comes out.
"""

from datetime import datetime, timedelta, timezone
from unittest import TestCase, mock

from commands.CmdBug import CmdBug


class TestTheResetClockNeedsNoAccount(TestCase):

    def setUp(self):
        self.cmd = CmdBug()

    def test_it_is_callable_with_no_argument(self):
        self.assertIsInstance(self.cmd.get_time_until_reset(), str)

    def test_it_counts_down_to_the_next_utc_midnight(self):
        """Control: the clock is not a constant -- it reports the real
        remaining interval, and it is the UTC one."""
        noon = datetime(2026, 9, 15, 12, 30, tzinfo=timezone.utc)

        class _Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return noon

        with mock.patch("commands.CmdBug.datetime", _Clock):
            self.assertEqual(self.cmd.get_time_until_reset(),
                             "11 hours, 30 minutes")

        late = noon + timedelta(hours=11)  # 23:30 UTC

        class _LateClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return late

        with mock.patch("commands.CmdBug.datetime", _LateClock):
            self.assertEqual(self.cmd.get_time_until_reset(), "30 minutes")
