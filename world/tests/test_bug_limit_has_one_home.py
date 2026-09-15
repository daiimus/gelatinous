"""The @bug daily cap has one home: the setting (#3408).

`BUG_REPORT_DAILY_LIMIT` was read with a fallback of 30 in three places
and hardcoded as the literal "30" in the two sentences a player reads:
the save-time refusal and the command's help. Lower the knob to 5 and a
player was refused after five reports while being told the limit was
30. The tracked settings file now declares the default (overridable in
secret_settings.py), every read is a plain settings lookup, the refusal
interpolates it, and the help text names no number.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from commands.CmdBug import CmdBug


class _BugCase(EvenniaTest):
    LIMIT = 5

    def setUp(self):
        super().setUp()
        self.cmd = CmdBug()
        self.cmd.caller = self.char1
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.cmdstring = "@bug"
        self.account = self.char1.account
        self.account.db.bug_report_date = datetime.now(timezone.utc).date()
        # `override_settings`, NOT `mock.patch.object(settings, ...)`: on
        # exit mock `delattr`s a name it found through Django's lazy
        # `__getattr__`, and LazySettings forwards that delete to the real
        # Settings object -- the knob vanished for every later test in the
        # process (found while writing this file).
        override = override_settings(GITHUB_TOKEN="x", GITHUB_REPO="x",
                                     BUG_REPORT_DAILY_LIMIT=self.LIMIT)
        override.enable(); self.addCleanup(override.disable)
        self.seen = []
        p = mock.patch.object(self.char1, "msg",
                              side_effect=lambda text=None, **kw: self.seen.append(str(text)))
        p.start(); self.addCleanup(p.stop)

    def said(self):
        return " ".join(self.seen)


class TestTheSaveTimeRefusalNamesTheSetting(_BugCase):
    """Reach the editor's save callback the way the game builds it: run
    the real menu node with the editor stubbed, then call the callback
    it registered."""

    def _save_callback(self):
        nodes = {}
        def fake_menu(caller, menudata, *args, **kwargs):
            nodes.update(menudata)
        captured = {}
        def fake_editor(caller, **kwargs):
            captured.update(kwargs)
        # `start_detail_editor` imports EvEditor locally and the node
        # closes over that name, so the editor stub must be in place
        # BEFORE the menu is built, not just before the node runs.
        with mock.patch("evennia.utils.evmenu.EvMenu", fake_menu), \
             mock.patch("evennia.utils.eveditor.EvEditor", fake_editor):
            self.cmd.start_detail_editor(self.char1)
            self.assertIn("node_open_editor", nodes)
            self.char1.ndb._evmenu = SimpleNamespace(bug_title="a title")
            nodes["node_open_editor"](self.char1, "", category="other")
        self.assertIn("savefunc", captured, "editor was not built by the node")
        return captured["savefunc"]

    def test_a_capped_player_is_told_the_real_limit(self):
        self.account.db.bug_report_count = self.LIMIT
        save = self._save_callback()
        self.seen.clear()
        save(self.char1, "a description long enough to pass the floor")
        self.assertIn(f"daily limit of {self.LIMIT} bug reports", self.said())
        self.assertNotIn("30", self.said())

    def test_the_up_front_refusal_agrees(self):
        self.account.db.bug_report_count = self.LIMIT
        with mock.patch.object(self.cmd, "start_detail_editor"):
            self.cmd.func()
        self.assertIn(f"daily limit of {self.LIMIT} bug reports", self.said())


class TestTheGateReadsTheSetting(_BugCase):
    def test_under_the_cap_passes(self):
        self.account.db.bug_report_count = self.LIMIT - 1
        self.assertTrue(self.cmd.check_rate_limit(self.account))

    def test_at_the_cap_refuses(self):
        self.account.db.bug_report_count = self.LIMIT
        self.assertFalse(self.cmd.check_rate_limit(self.account))


class TestTheHelpNamesNoNumber(EvenniaTest):
    def test_help_text_carries_no_literal_limit(self):
        self.assertNotIn("30", CmdBug.__doc__)
        self.assertIn("cap", CmdBug.__doc__.lower())
