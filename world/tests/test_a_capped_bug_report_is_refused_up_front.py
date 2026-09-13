"""`@bug` refuses a capped player BEFORE the editor opens (#3367).

The daily cap was enforced only in the EvEditor save callback, so a
player already at the limit was walked through the title node, the
category menu and the multi-line editor, then refused at :wq with the
buffer discarded. The cap is now checked at the top of `func`, before
`start_detail_editor`; the save-time check stays as the last line of
defence.
"""
from datetime import datetime, timezone
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from commands import CmdBug as bugmod
from commands.CmdBug import CmdBug


class CappedBugReportRefusedUpFrontTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.cmd = CmdBug()
        self.cmd.caller = self.char1
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.cmdstring = "@bug"
        self.account = self.char1.account
        self.account.db.bug_report_date = datetime.now(timezone.utc).date()
        self.limit = getattr(bugmod.settings, "BUG_REPORT_DAILY_LIMIT", 30)
        # The command refuses when GitHub isn't configured; give it a config.
        for name in ("GITHUB_TOKEN", "GITHUB_REPO"):
            p = mock.patch.object(bugmod.settings, name, "x", create=True); p.start(); self.addCleanup(p.stop)
        self.editor = mock.patch.object(self.cmd, "start_detail_editor"); self.editor_mock = self.editor.start(); self.addCleanup(self.editor.stop)
        self.seen = []
        p = mock.patch.object(self.char1, "msg", side_effect=lambda text=None, **kw: self.seen.append(str(text))); p.start(); self.addCleanup(p.stop)

    def test_capped_player_is_refused_before_the_editor(self):
        self.account.db.bug_report_count = self.limit
        self.cmd.func()
        self.editor_mock.assert_not_called()
        joined = " ".join(self.seen).lower()
        self.assertIn("daily limit", joined, "no refusal shown: %r" % self.seen)
        self.assertIn("resets in", joined, "reset time not shown")

    def test_player_under_the_cap_gets_the_editor(self):
        # Control: the gate does not over-refuse.
        self.account.db.bug_report_count = self.limit - 1
        self.cmd.func()
        self.editor_mock.assert_called_once()
        self.assertNotIn("daily limit", " ".join(self.seen).lower())

    def test_refusal_does_not_consume_a_slot(self):
        self.account.db.bug_report_count = self.limit
        self.cmd.func()
        self.assertEqual(self.account.db.bug_report_count, self.limit)
