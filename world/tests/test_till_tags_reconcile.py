"""Every register is swept, tagged or not (#2630).

The souls-economy tithe finds tills **only by tag** — the tag is the
index, per the hardening spec's law 3 ("tags for lookup, never
attribute-key queries on a hot path"). Nothing reconciled the tag against
the attribute, so a register without the tag was **silently invisible**
to the sweep rather than merely slow to find.

Live: the Hammett's Boot food cart (#5221) predates the tagging line, and
build 069's backfill covered `ShopContainer`s and not carts — so **8 of
9 tills were tagged and its register was never swept**.

It survived because the loss is money going *untaxed*: the venue keeps
more than it should, nothing faults, and no alarm sounds. The opposite
failure would have been noticed in a day.

Same shape and same fix as `_reconcile_advertiser_tags` (#2697), where a
purpose-built charging rack sat dead for the same reason. A register
without the tag is always a build gap, so this **adopts** rather than
warning — one attribute query per sweep, not per call, which is what
keeps law 3 satisfied.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls.economy import _reconcile_till_tags


class _TillCase(EvenniaTest):
    def _till(self, register, tagged):
        obj = create_object("typeclasses.objects.Object",
                            key="a hull-plate food cart",
                            location=self.room1)
        obj.db.register = register
        if tagged:
            obj.tags.add("till", category="souls")
        return obj

    def tagged_set(self):
        from evennia.utils.search import search_tag
        return list(search_tag("till", category="souls"))


class TestAnUntaggedRegisterIsAdopted(_TillCase):
    def test_it_gets_the_tag(self):
        cart = self._till(406, tagged=False)
        _reconcile_till_tags(self.tagged_set())
        self.assertTrue(cart.tags.get("till", category="souls"))

    def test_it_joins_the_swept_set(self):
        cart = self._till(406, tagged=False)
        result = _reconcile_till_tags(self.tagged_set())
        self.assertIn(cart, result)

    def test_an_empty_register_still_counts(self):
        """A register of 0 is a till that happens to be empty, not an
        absent till — `is not None`, never truthiness."""
        cart = self._till(0, tagged=False)
        result = _reconcile_till_tags(self.tagged_set())
        self.assertIn(cart, result)


class TestItDoesNotOverReach(_TillCase):
    def test_an_object_with_no_register_is_left_alone(self):
        plain = create_object("typeclasses.objects.Object", key="a crate",
                              location=self.room1)
        _reconcile_till_tags(self.tagged_set())
        self.assertFalse(plain.tags.get("till", category="souls"))

    def test_an_already_tagged_till_is_not_duplicated(self):
        cart = self._till(50, tagged=True)
        result = _reconcile_till_tags(self.tagged_set())
        self.assertEqual(sum(1 for o in result if o == cart), 1)

    def test_it_is_idempotent(self):
        self._till(406, tagged=False)
        first = _reconcile_till_tags(self.tagged_set())
        second = _reconcile_till_tags(self.tagged_set())
        self.assertEqual(len(first), len(second))


class TestTheSweepSeesTheAdoptedTill(_TillCase):
    def test_run_tithe_reaches_a_previously_invisible_register(self):
        from world.souls import economy
        cart = self._till(1000, tagged=False)
        before = int(cart.db.register or 0)
        economy.run_tithe()
        self.assertLess(int(cart.db.register or 0), before,
                        "the untagged register was still skipped")
