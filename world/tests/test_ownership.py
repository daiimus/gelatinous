"""Who owns a body (#2369).

`db_account_id` is set only while a character is PUPPETED, so every
logged-out player character reads as ownerless by it. Using it as the
"is this a player's body?" test is wrong, quiet, and destructive — this
project has already lost player characters that way, and `@fixchar`
exists because ownership has been recorded three different ways over
the codebase's life.
"""

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world import ownership


class TestOwnershipSignals(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.body = create_object("typeclasses.characters.Character",
                                  key="Aiko", location=self.room1)

    def test_an_unclaimed_body_is_not_owned(self):
        with mock.patch.object(ownership, "owning_accounts",
                               wraps=ownership.owning_accounts):
            self.assertFalse(ownership.is_player_owned(self.body))

    def test_a_puppeted_body_is_owned(self):
        self.body.db_account_id = 7
        self.assertTrue(ownership.is_player_owned(self.body))

    def test_a_logged_out_character_is_still_owned(self):
        """THE case the old filter got wrong. No account id, no session
        — and somebody's character all the same."""
        self.assertIsNone(self.body.db_account_id)
        with mock.patch("evennia.accounts.models.AccountDB.objects") as accts:
            acct = mock.MagicMock()
            acct.key = "Hungion"
            acct.db._playable_characters = [self.body]
            accts.all.return_value = [acct]
            self.assertTrue(ownership.is_player_owned(self.body))
            self.assertIn(("Hungion", "playable_characters"),
                          ownership.owning_accounts(self.body))

    def test_a_legacy_puppet_lock_is_owned(self):
        """How characters were bound before `create_character()` — the
        reason `@fixchar` exists."""
        self.body.locks.add("puppet:pid(12)")
        claims = ownership.owning_accounts(self.body)
        self.assertIn("puppet-lock", [how for _who, how in claims])

    def test_a_staff_lock_is_not_ownership(self):
        """`pperm(Developer)` names a permission, not a person — every
        builder-made NPC carries it."""
        self.body.locks.add("puppet:pperm(Developer)")
        self.assertFalse(ownership.is_player_owned(self.body))

    def test_it_fails_closed_when_accounts_cannot_be_read(self):
        """The cost of a false 'nobody owns this' is somebody's
        character; the cost of a false 'somebody does' is a body left
        standing. Only one of those is recoverable."""
        with mock.patch("evennia.accounts.models.AccountDB.objects") as accts:
            accts.all.side_effect = RuntimeError("db down")
            self.assertTrue(ownership.is_player_owned(self.body))
