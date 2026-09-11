"""A second session does not tear down a decant in progress.

Regression pin for #2625. `at_post_login` runs for EVERY session
(MULTISESSION_MODE=1), and with zero active sleeves it started chargen
unconditionally.

`EvMenu.__init__` closes any existing menu on the same caller, so the
second session's menu tore down the first: `_charcreate_exit_callback`
then saw zero actives and DISCONNECTED the original session with
"Sleeve decantation incomplete", while `start_character_creation` reset
`ndb.charcreate_data` and discarded everything already typed.

Ten fields into chargen on the web client, open a second tab, lose the
lot.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from typeclasses.accounts import Account


def _account(active=(), menu=None):
    acc = MagicMock()
    acc.attributes.get.return_value = {}
    acc._sleeves_split.return_value = (list(active), [])
    acc.db.last_character = None
    acc.ndb._evmenu = menu
    acc.respawn_candidate = Account.respawn_candidate.__get__(acc, Account)
    acc.at_post_login = Account.at_post_login.__get__(acc, Account)
    return acc


class TestASecondTabDoesNotRestartChargen(TestCase):

    def test_a_live_menu_blocks_a_second_chargen(self):
        acc = _account(active=(), menu=MagicMock())
        with patch("commands.charcreate.start_character_creation") as start:
            acc.at_post_login(session=MagicMock())
        start.assert_not_called()
        acc.msg.assert_called()

    def test_the_first_session_is_told_where_the_decant_is(self):
        acc = _account(active=(), menu=MagicMock())
        with patch("commands.charcreate.start_character_creation"):
            acc.at_post_login(session=MagicMock())
        said = " ".join(str(c.args[0]) for c in acc.msg.call_args_list if c.args)
        self.assertIn("another", said.lower())

    # -- controls ----------------------------------------------------

    def test_no_menu_still_starts_chargen(self):
        """The control — a guard that always blocked would pass above."""
        acc = _account(active=(), menu=None)
        with patch("commands.charcreate.start_character_creation") as start:
            acc.at_post_login(session=MagicMock())
        start.assert_called_once()

    def test_a_live_menu_does_not_block_an_ordinary_login(self):
        """Someone with a sleeve is auto-puppeted, menu or not."""
        acc = _account(active=("only-one",), menu=MagicMock())
        session = MagicMock()
        acc.at_post_login(session=session)
        acc.puppet_object.assert_called_once_with(session, "only-one")
