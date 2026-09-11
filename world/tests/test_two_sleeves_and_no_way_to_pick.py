"""An account with two live sleeves gets a character picker.

Regression pin for #2614.  `Account.at_post_login`'s multi-sleeve branch
was a bare `pass`, under a comment reading:

    # Multiple active characters - let user choose with 'ic <name>'
    # The default OOC behavior will handle this

"The default OOC behavior" is `DefaultAccount.at_post_login`'s
multi-character branch, which sends the character-selection screen.
This method REPLACES that one, deliberately without calling `super()`
(see its own docstring, #2613) -- so the thing named as the handler is
exactly the thing that was removed.

An account with two or more active sleeves therefore logged in to
silence: no list, no prompt, and no hint that `ic <name>` was the way
out, since the only place that was written down was a comment nobody
sees.  `AUTO_PUPPET_ON_LOGIN = False`, so this really is the branch such
an account lands in.

Comment-vs-code, with the comment naming the mechanism that was deleted.

Latent when fixed: 24 accounts live, none holding more than one active
sleeve.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from typeclasses.accounts import Account


def _account(active, archived=()):
    """A mock account with the real `at_post_login` bound to it."""
    acc = MagicMock()
    acc.key = "Tester"
    acc.attributes.get.return_value = {}
    acc._sleeves_split.return_value = (list(active), list(archived))
    acc.db.last_character = None
    acc.at_post_login = Account.at_post_login.__get__(acc, Account)
    # Bind the REAL validator too (#2615) — a bare MagicMock returns a
    # truthy stand-in, which would send a no-sleeve account down the
    # respawn path instead of chargen.
    acc.respawn_candidate = Account.respawn_candidate.__get__(acc, Account)
    return acc


class TestTwoSleevesAndNoWayToPick(TestCase):

    def test_two_active_sleeves_get_the_picker(self):
        session = MagicMock()
        acc = _account(["sleeve-a", "sleeve-b"])

        acc.at_post_login(session=session)

        acc.at_look.assert_called_once()
        self.assertEqual(
            acc.at_look.call_args.kwargs.get("target"),
            ["sleeve-a", "sleeve-b"],
        )
        acc.msg.assert_called()

    def test_the_picker_excludes_archived_sleeves(self):
        """A dead sleeve must not appear in a list that implies it can
        be puppeted. The default scopes to `self.characters`; this
        scopes to the active split."""
        session = MagicMock()
        acc = _account(["sleeve-a", "sleeve-b"], archived=["dead-one"])

        acc.at_post_login(session=session)

        # Assert the call happened before reading its args, so an
        # unfixed tree FAILS here rather than ERRORing on `call_args`
        # being None. An error is not a failure.
        acc.at_look.assert_called_once()
        self.assertNotIn(
            "dead-one", acc.at_look.call_args.kwargs.get("target"),
        )

    def test_nobody_is_auto_puppeted_with_two_sleeves(self):
        """The choice is the player's — that is the point of the branch."""
        session = MagicMock()
        acc = _account(["sleeve-a", "sleeve-b"])

        acc.at_post_login(session=session)

        acc.puppet_object.assert_not_called()

    # -- controls: the other two branches are untouched --------------

    def test_one_active_sleeve_is_still_auto_puppeted(self):
        session = MagicMock()
        acc = _account(["only-one"])

        acc.at_post_login(session=session)

        acc.puppet_object.assert_called_once_with(session, "only-one")
        acc.at_look.assert_not_called()

    def test_no_active_sleeves_still_reaches_chargen(self):
        """Zero sleeves must not fall into the picker."""
        session = MagicMock()
        acc = _account([])

        acc.at_post_login(session=session)

        acc.at_look.assert_not_called()
        acc.puppet_object.assert_not_called()

    # -- the preamble #2613 restored must survive ---------------------

    def test_the_connect_announcement_still_fires(self):
        session = MagicMock()
        acc = _account(["sleeve-a", "sleeve-b"])

        acc.at_post_login(session=session)

        acc._send_to_connect_channel.assert_called_once()
        session.msg.assert_called()
