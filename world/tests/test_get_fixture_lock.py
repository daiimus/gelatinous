"""The get command honours get:false() fixtures (2026-07-14): a mast,
console, or wired boombox stays bolted down. Regression for a custom
CmdGet that skipped the lock check entirely."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from commands.CmdInventory import CmdGet


def _cmd():
    cmd = CmdGet()
    cmd.caller = MagicMock()
    return cmd


class TestFixtureGetGuard(TestCase):
    def _item(self, allowed, pre_get=True, err=None):
        item = MagicMock()
        item.access.return_value = allowed
        item.at_pre_get.return_value = pre_get
        item.db.get_err_msg = err
        item.get_display_name.return_value = "the boombox"
        return item

    def test_locked_fixture_refused_with_its_message(self):
        cmd = _cmd()
        item = self._item(allowed=False, err="It's wired to the wall. It stays.")
        self.assertFalse(cmd._can_be_taken(cmd.caller, item))
        cmd.caller.msg.assert_called_once_with("It's wired to the wall. It stays.")

    def test_locked_fixture_default_message(self):
        cmd = _cmd()
        item = self._item(allowed=False, err=None)
        self.assertFalse(cmd._can_be_taken(cmd.caller, item))
        self.assertIn("can't pick up", cmd.caller.msg.call_args.args[0])

    def test_pre_get_veto_cancels_silently(self):
        cmd = _cmd()
        item = self._item(allowed=True, pre_get=False)
        self.assertFalse(cmd._can_be_taken(cmd.caller, item))

    def test_free_item_passes(self):
        cmd = _cmd()
        item = self._item(allowed=True, pre_get=True)
        self.assertTrue(cmd._can_be_taken(cmd.caller, item))
