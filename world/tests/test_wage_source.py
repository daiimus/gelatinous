"""A venue with no till is not a venue with an empty one (#2693).

`pay_wage` documents two cases: a venue post is paid from its own till,
a non-venue post draws the colony treasury. A THIRD exists and was
unhandled -- a post bound to a fixture that has no `register` attribute
at all. `int(None or 0)` is 0, so nothing was paid, and the `else` that
would have reached the treasury was never taken because `venue is not
None`.

Live-firing when found: Ossie Trelane had banked **140.56 tokens** he
could never be paid, against a crane console with no `register`, while
the treasury sat solvent at 1,150.

It stayed invisible because a missing till and an empty one are
indistinguishable downstream -- both show as an unpaid balance on
`@soul`, so the display meant to make a drought visible is exactly what
disguised it.
"""
from unittest import TestCase, mock

from world.souls import economy


class _Attrs:
    def __init__(self, present):
        self._present = present

    def has(self, key):
        return key in self._present


class _Venue:
    def __init__(self, register=None, has_register=True):
        self.db = mock.MagicMock()
        self.db.register = register
        self.attributes = _Attrs({"register"} if has_register else set())


class _Soul:
    def __init__(self, owed, venue):
        self.db = mock.MagicMock()
        self.db.soul_wage_owed = owed
        self.db.soul_venue = venue
        self.ndb = mock.MagicMock()
        self.ndb.soul_wage_pending = 0.0
        self.tokens = 0


class TestWhereTheWageComesFrom(TestCase):
    def _treasury(self, balance=1000):
        t = mock.MagicMock()
        t.db.balance = balance
        return t

    def _pay(self, soul, balance=1000):
        treasury = self._treasury(balance)
        with mock.patch.object(economy, "get_treasury", return_value=treasury), \
             mock.patch("world.souls.audit.coin"):
            paid = economy.pay_wage(soul)
        return paid, treasury

    def test_a_venue_with_no_till_draws_the_treasury(self):
        """The reported case: a control surface is not a counter."""
        soul = _Soul(140.56, _Venue(has_register=False))
        paid, treasury = self._pay(soul)
        self.assertEqual(paid, 140)
        self.assertEqual(treasury.db.balance, 860)

    def test_a_venue_with_an_empty_till_still_pays_nothing(self):
        """The pin, and the reason `has()` rather than truthiness: an
        empty till is a real, documented state -- a drought is visible,
        not a bug -- and must NOT silently fall through to the colony."""
        soul = _Soul(50.0, _Venue(register=0))
        paid, treasury = self._pay(soul)
        self.assertEqual(paid, 0)
        self.assertEqual(treasury.db.balance, 1000)
        self.assertAlmostEqual(soul.db.soul_wage_owed, 50.0, places=2)

    def test_a_funded_venue_pays_from_its_own_till(self):
        venue = _Venue(register=200)
        soul = _Soul(50.0, venue)
        paid, treasury = self._pay(soul)
        self.assertEqual(paid, 50)
        self.assertEqual(venue.db.register, 150)
        self.assertEqual(treasury.db.balance, 1000)

    def test_a_partly_funded_venue_still_pays_what_it_has(self):
        venue = _Venue(register=20)
        soul = _Soul(50.0, venue)
        paid, _t = self._pay(soul)
        self.assertEqual(paid, 20)
        self.assertEqual(venue.db.register, 0)

    def test_a_non_venue_post_still_draws_the_treasury(self):
        soul = _Soul(30.0, None)
        paid, treasury = self._pay(soul)
        self.assertEqual(paid, 30)
        self.assertEqual(treasury.db.balance, 970)

    def test_a_dry_treasury_leaves_the_balance_owed(self):
        soul = _Soul(30.0, _Venue(has_register=False))
        paid, _t = self._pay(soul, balance=0)
        self.assertEqual(paid, 0)
        self.assertAlmostEqual(soul.db.soul_wage_owed, 30.0, places=2)

    def test_the_fractional_remainder_is_never_discarded(self):
        soul = _Soul(30.75, None)
        paid, _t = self._pay(soul)
        self.assertEqual(paid, 30)
        self.assertAlmostEqual(soul.db.soul_wage_owed, 0.75, places=2)


class TestANegativeTillDoesNotInflateTheDebt(TestCase):
    """`min(owed, avail)` with a NEGATIVE `avail` gives a negative
    `paid`. Both money writes are guarded by `paid > 0` and correctly do
    nothing -- but `soul.db.soul_wage_owed = owed_f - paid` is NOT
    guarded, so a negative `paid` ADDED to the debt.

    The keeper of an overdrawn venue would accrue phantom debt equal to
    the overdraft every payday, compounding, while never being paid
    (#2703).

    Armed, not firing: zero negative registers live today.
    """

    def _pay(self, soul, balance=1000):
        treasury = mock.MagicMock()
        treasury.db.balance = balance
        with mock.patch.object(economy, "get_treasury", return_value=treasury), \
             mock.patch("world.souls.audit.coin"):
            return economy.pay_wage(soul)

    def test_a_negative_till_pays_nothing(self):
        soul = _Soul(50.0, _Venue(register=-40))
        self.assertEqual(self._pay(soul), 0)

    def test_a_negative_till_does_not_grow_the_debt(self):
        soul = _Soul(50.0, _Venue(register=-40))
        self._pay(soul)
        self.assertAlmostEqual(soul.db.soul_wage_owed, 50.0, places=2,
                               msg="the overdraft was added to the debt")

    def test_a_negative_till_is_not_further_overdrawn(self):
        venue = _Venue(register=-40)
        self._pay(_Soul(50.0, venue))
        self.assertEqual(venue.db.register, -40)

    def test_a_negative_treasury_does_not_grow_the_debt_either(self):
        soul = _Soul(50.0, None)
        self._pay(soul, balance=-100)
        self.assertAlmostEqual(soul.db.soul_wage_owed, 50.0, places=2)

    def test_a_funded_till_is_unaffected(self):
        """The pin: clamping must not change normal payment."""
        venue = _Venue(register=200)
        soul = _Soul(50.0, venue)
        self.assertEqual(self._pay(soul), 50)
        self.assertEqual(venue.db.register, 150)
