"""Every ownership claim names an account, or names nothing (#2683).

`owning_accounts` documented one field — `account_key` — and returned
three different kinds of identifier under it:

    claims.append((str(account_id), "puppeted"))       # a numeric ID
    claims.append((acct.key, "playable_characters"))   # an account key
    claims.append((found.group(1), "puppet-lock"))     # a regex group

The `puppet:` lock on a character commonly references the CHARACTER
(`id(394)`), not an account. Measured live across 166 bodies:

    puppet-lock          64      59 of them naming the body's own dbref
    playable_characters  57
    puppeted              2

A caller could not tell the three apart, because the tuple's second
element names the SIGNAL and not the namespace — and one real account in
this database is literally named `912640631`, so "looks numeric" was
never a usable heuristic either. The function exists for the surprising
cases and was least trustworthy exactly there.

WHAT THIS DELIBERATELY DOES NOT DO is drop the unresolved claims. Seven
live bodies — a run of `Drivel` sleeves — have no other signal at all,
and `is_player_owned` fails closed on purpose because the cost of a
false "nobody owns this" is somebody's character. The consumers are
`scripts/builds/140` and `143`, both of which delete or retype what
nobody owns. So an unresolved lock stays a claim, and says so in `how`.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import ownership as ownership_mod
from world.ownership import is_player_owned, owning_accounts


class TestEveryValueIsAnAccountKeyOrNone(EvenniaTest):

    def test_a_body_with_no_claim_has_no_claims(self):
        """Control: if everything came back claimed, the assertions
        below would be measuring nothing."""
        body = create_object("typeclasses.characters.Character",
                             key="nobody's", location=self.room1)
        body.locks.add("puppet:false()")
        self.assertEqual(owning_accounts(body), [])

    def test_a_real_account_is_reported_by_key(self):
        claims = owning_accounts(self.char1)
        self.assertTrue(claims, "the fixture body has no claim at all")
        for value, how in claims:
            if value is not None:
                self.assertEqual(value, self.account.key,
                                 f"{how} reported {value!r}")

    def test_a_self_referencing_lock_names_nobody(self):
        """The 59-of-64 case: `puppet:id(<own dbref>)` is not an
        account."""
        body = create_object("typeclasses.characters.Character",
                             key="a sleeve", location=self.room1)
        body.locks.add(f"puppet:id({body.id})")
        claims = owning_accounts(body)
        self.assertTrue(claims)
        for value, how in claims:
            if how.endswith("-unresolved"):
                self.assertIsNone(value)
            else:
                self.assertIsNotNone(value)

    def test_and_it_says_so_in_how(self):
        body = create_object("typeclasses.characters.Character",
                             key="a sleeve", location=self.room1)
        body.locks.add(f"puppet:id({body.id})")
        hows = {how for _v, how in owning_accounts(body)}
        self.assertIn("puppet-lock-unresolved", hows)

    def test_a_numeric_account_key_still_resolves(self):
        """One real account is named `912640631`, so a numeric token is
        not evidence of anything on its own."""
        # `create=True`: without it this ERRORS against the unfixed
        # tree, where the resolver does not exist yet — and an error
        # stops a test before it can assert anything.
        with patch.object(ownership_mod, "_account_named",
                          create=True) as lookup:
            lookup.return_value = self.account
            body = create_object("typeclasses.characters.Character",
                                 key="a sleeve", location=self.room1)
            body.locks.add("puppet:id(912640631)")
            values = {v for v, h in owning_accounts(body)
                      if h == "puppet-lock"}
        self.assertEqual(values, {self.account.key})


class TestItStillFailsClosed(EvenniaTest):
    """The half that must not break. Seven live `Drivel` sleeves have
    no signal but an unresolved lock, and the consumers delete what
    nobody owns."""

    def test_a_body_whose_only_claim_is_unresolved_is_still_owned(self):
        body = create_object("typeclasses.characters.Character",
                             key="Drivel", location=self.room1)
        body.locks.add(f"puppet:id({body.id})")
        claims = owning_accounts(body)
        self.assertEqual({h for _v, h in claims},
                         {"puppet-lock-unresolved"})
        self.assertTrue(is_player_owned(body),
                        "a real player sleeve became deletable")

    def test_an_unreadable_account_scan_is_still_a_claim(self):
        body = create_object("typeclasses.characters.Character",
                             key="a sleeve", location=self.room1)
        body.locks.add("puppet:false()")
        with patch("evennia.accounts.models.AccountDB.objects") as objs:
            objs.all.side_effect = RuntimeError("database on fire")
            self.assertTrue(is_player_owned(body))
