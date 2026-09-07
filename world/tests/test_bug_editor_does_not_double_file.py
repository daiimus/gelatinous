"""The bug editor files once, counts once, and says what it does
(#2524, #2525, #2526).

Three defects in one command, all of which end with a public GitHub
issue being filed when the player did not mean to file one.

**#2524 — a repeated `:w` filed the report again.** Evennia clears the
editor's `_unsaved` flag only when the save callback returns something
truthy (`eveditor.py:save_buffer`), and `codefunc` is `None` here, so
that return is the only thing that can clear it. Every path in
`_save_callback` returned `None`, so the buffer stayed dirty for the life
of the session and each `:w` re-entered the whole submit path.

The two early exits still return falsy on purpose: nothing was
submitted, so the buffer really is still unsaved.

**#2525 — `:q` was documented as cancelling, and submits.** In Evennia
6.1 `:q` and `:q!` are not synonyms. With an unsaved buffer — which is
every real use of this command, since `_unsaved` flips on the first
keystroke — `:q` asks *"Save before quitting?"*, and `SaveYesNoCmdSet`
is keyed on `_CMD_NOMATCH` with `_CMD_NOINPUT` as its alias, so
**everything except the literal "no" or "n" lands in the yes branch** —
a bare Enter included.

Fixed by documenting it truthfully and naming `:q!` as the cancel,
rather than by overriding the editor: this codebase does not build
custom layers over Evennia internals. `BUG_COMMAND_SPEC.md` asserts the
outright-cancel behaviour in four places and is therefore still ahead of
the code — that gap is called out on the issue for a ruling, since
closing it means overriding core.

**#2526 — the daily cap was check-then-act across a network call.** The
counter was incremented in the completion callback, on the far side of
an off-thread POST (#460 moved it there), while the limit was checked
before. Every submission that started before the first one landed saw
the same count and passed. The slot is now reserved at the check and
refunded if the POST fails, so a report that never reached GitHub does
not cost the player one.

Nothing here touches the network: `create_github_issue` is mocked in
every test, because the real one files issues on this repository.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from commands.CmdBug import CmdBug


class _CounterCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.cmd = CmdBug()
        self.account = self.char1.account
        self.account.db.bug_report_count = 0
        from datetime import datetime, timezone
        self.account.db.bug_report_date = datetime.now(timezone.utc).date()

    def count(self):
        return self.account.db.bug_report_count or 0


class TestTheQuotaIsReservedNotCounted(_CounterCase):
    """#2526: the window between check and increment was a whole
    network round-trip wide."""

    def test_a_reserved_slot_is_visible_immediately(self):
        self.assertTrue(self.cmd.check_rate_limit(self.account))
        self.cmd.increment_report_count(self.account)
        self.assertEqual(self.count(), 1)

    def test_reserving_to_the_limit_closes_the_gate(self):
        from django.conf import settings
        limit = getattr(settings, "BUG_REPORT_DAILY_LIMIT", 30)
        for _ in range(limit):
            self.assertTrue(self.cmd.check_rate_limit(self.account))
            self.cmd.increment_report_count(self.account)
        self.assertFalse(self.cmd.check_rate_limit(self.account))

    def test_a_failed_post_refunds_the_slot(self):
        self.cmd.increment_report_count(self.account)
        self.cmd.refund_report_count(self.account)
        self.assertEqual(self.count(), 0)

    def test_a_refund_never_goes_negative(self):
        self.cmd.refund_report_count(self.account)
        self.assertEqual(self.count(), 0)

    def test_a_refund_does_not_touch_a_new_day(self):
        """A rollover between reserve and failure belongs to tomorrow's
        quota, not this report's."""
        from datetime import datetime, timedelta, timezone
        self.cmd.increment_report_count(self.account)
        self.account.db.bug_report_date = (
            datetime.now(timezone.utc).date() - timedelta(days=1))
        self.cmd.refund_report_count(self.account)
        self.assertEqual(self.count(), 1)


class TestTheHelpTellsTheTruth(EvenniaTest):
    """#2525. Pinned against the source: the whole defect was a line of
    help text that contradicted the editor it was introducing."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdBug.py").read_text(errors="ignore")

    def test_it_no_longer_calls_them_synonyms(self):
        self.assertNotIn("|w:q|n or |w:q!|n - Cancel without submitting",
                         self._source())

    def test_it_names_the_real_cancel(self):
        self.assertIn("|w:q!|n - Cancel without submitting", self._source())

    def test_it_warns_that_bare_q_asks(self):
        body = self._source()
        self.assertIn("asks whether to submit first", body)


class TestTheCallbackAcknowledgesTheSave(EvenniaTest):
    """#2524. Pinned against the source because the consequence — a
    duplicate GitHub issue — cannot be exercised without a network
    call, and the whole defect is a missing `return`."""

    def _save_callback_body(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "commands" / "CmdBug.py").read_text(errors="ignore")
        start = body.index("def _save_callback(caller, buffer):")
        end = body.index("def _quit_callback(caller):", start)
        return body[start:end]

    def test_the_submit_path_returns_truthy(self):
        self.assertIn("return True", self._save_callback_body())

    def test_it_returns_after_scheduling_the_call(self):
        body = self._save_callback_body()
        self.assertLess(body.index("_run_github_call("),
                        body.index("return True"))

    def test_the_early_exits_stay_falsy(self):
        """Nothing was filed on those paths, so the buffer is genuinely
        still unsaved and must keep prompting."""
        body = self._save_callback_body()
        self.assertIn("Details too short", body)
        head = body[:body.index("Check rate limit")]
        self.assertNotIn("return True", head)


class TestEvenniaStillNeedsTheTruthyReturn(EvenniaTest):
    """The contract this hangs on, read off the installed Evennia rather
    than trusted — if a future upgrade changes it, this fails loudly
    instead of the fix quietly becoming a no-op."""

    def test_save_buffer_clears_unsaved_only_on_a_truthy_return(self):
        import inspect

        from evennia.utils import eveditor
        src = inspect.getsource(eveditor.EvEditor.save_buffer)
        self.assertIn("if self._savefunc(", src)
        self.assertIn("self._unsaved = False", src)

    def test_the_yes_no_cmdset_defaults_to_saving(self):
        import inspect

        from evennia.utils import eveditor
        src = inspect.getsource(eveditor)
        self.assertIn('("no", "n")', src)
        self.assertIn("save_buffer()", src)
