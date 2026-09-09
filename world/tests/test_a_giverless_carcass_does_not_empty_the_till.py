"""Debit and credit stay under the same condition (#2814, reopened).

#2814 established the rule and left the guard in place:

    if not (giver and giver.pk):
        payout = 0

Then #2479's "buy what you can pay for" landed BELOW it and overwrote
the variable it had just zeroed:

    if block:
        bought, spent = _affordable(yields, till)
        payout = spent                      # <- guard destroyed
        block.db.register = till - payout   # <- till IS debited
    ...
    if giver and giver.pk:                  # <- nobody IS credited
        giver.tokens = ... + payout

So a carcass with no giver -- or a giver deleted inside the 1.5s
`delay` between the hand-over and the cleaver -- debits the block's
register and credits nobody. The money leaves the world. That is the
exact defect #2814 was filed to close, reintroduced by a commit that
never read the guard four lines above it, under a comment that says
"Debit and credit must sit under the SAME condition."

The butcher also emotes "counts N across the steel" while nobody was
paid.

A giverless call is reachable: `on_receive` passes `None` unless the
giver is a `Character` (`who = giver if isinstance(giver, Character)
else None`), so anything else handing over a corpse -- a script, a
fixture -- arrives giverless.
"""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world import butchery
from world.tests.test_butcher import _butcher, _corpse, _rat_snapshot


class TestTheTillIsNotEmptiedForNobody(TestCase):

    def _run(self, *, giver, till=500):
        b = _butcher()
        block = MagicMock()
        block.db.register = till
        corpse = _corpse(_rat_snapshot())
        with patch.object(butchery, "spawn") as sp:
            sp.return_value = [MagicMock()]
            butchery.process_corpse(block, b, corpse, giver)
        return b, block

    def _paying_giver(self):
        giver = MagicMock()
        giver.pk = 1
        giver.tokens = 0
        return giver

    def test_a_giverless_carcass_leaves_the_register_alone(self):
        _b, block = self._run(giver=None, till=500)
        self.assertEqual(block.db.register, 500,
                         "the till paid out with nobody to pay")

    def test_a_giver_deleted_mid_transaction_leaves_the_register_alone(self):
        """The 1.5s `delay` between hand-over and cleaver is real time;
        the giver can log out or die inside it."""
        gone = MagicMock()
        gone.pk = None
        _b, block = self._run(giver=gone, till=500)
        self.assertEqual(block.db.register, 500,
                         "the till paid out to a deleted giver")

    def test_the_butcher_does_not_claim_to_have_paid(self):
        b, _block = self._run(giver=None, till=500)
        said = " ".join(str(c.args[0]) for c in b.execute_cmd.call_args_list)
        self.assertIn("doesn't reach for the till", said)

    def test_a_real_giver_is_still_paid_and_the_till_still_debited(self):
        """The other half: this must not become 'nobody is ever paid'."""
        giver = self._paying_giver()
        _b, block = self._run(giver=giver, till=500)
        self.assertGreater(giver.tokens, 0)
        self.assertEqual(block.db.register, 500 - giver.tokens,
                         "debit and credit disagree")
