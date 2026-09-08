"""A crowd is made of people, and a till buys what it pays for
(#2497, #2479).

## #2497 — crowd level counted logins, not bodies

```python
characters = [obj for obj in room.contents
              if hasattr(obj, 'has_account') and obj.has_account]
```

Evennia documents `has_account` as *"will only return **connected**
accounts"*. So the filter admitted exactly one population — players
currently logged in — and excluded every NPC, plus any linkdead player
body still standing in the room. The variable is called `characters`
and the comment says "per character", which is what made it read as
correct.

Not cosmetic. The module's own docstring says crowd level feeds witness
chance (`world/director/witness.py`) and the stealth concealment bonus
(`world/stealth.py`). With 16 NPC souls on a 24/7 clock, the
overwhelming majority of bodies in any room were the uncounted ones — so
a street packed with people had nobody to see a crime and nowhere to
disappear into.

Uses the same duck-type `world.emote._perceives` uses, imported rather
than re-derived, so the audience of a pose and the population of a
street cannot drift apart.

## #2479 — a short till bought a full carcass

`payout = min(payout, till)` clipped the **price**;
`stock_cuts(dict(yields))` stocked the **unclipped** yield. A till at
the floor of 5 paid 5 for a carcass worth 12 and received all 12
tokens' worth of stock — reachable at exactly the boundary the floor
exists to guard.

Clipping the goods instead of the money keeps the author's stated
intent ("pay what I can") and makes the two sides match. The block
keeps trading rather than refusing, which matters because its till
refills by selling that stock.

The other half of #2479 — the register debited when nobody was paid —
was already fixed under #2814 and is pinned here.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

# `_affordable` is NEW, so a module-scope import of it makes this whole
# file a loader error against the unfixed code — which would prove
# nothing about the crowd half either. Imported per test.
from world.butchery import RAT_PRODUCTS
from world.crowd import crowd_system


class TestTheStreetCountsBodies(EvenniaTest):
    def level(self):
        return crowd_system.calculate_crowd_level(self.room1)

    def npc(self, key="a stranger"):
        return create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)

    def test_npcs_raise_the_crowd_level(self):
        """Two bodies, because the bonus is 0.5 each and the level is
        `int(round(total))` — asserting on one body measures the
        rounding, not the fix."""
        before = self.level()
        self.npc("a stranger")
        self.npc("another stranger")
        self.assertGreater(self.level(), before)

    def test_several_npcs_raise_it_further(self):
        before = self.level()
        for i in range(4):
            self.npc(f"a stranger {i}")
        self.assertGreaterEqual(self.level() - before, 2.0 - 0.001)

    def test_furniture_does_not(self):
        before = self.level()
        for i in range(4):
            create_object("typeclasses.objects.Object", key=f"crate {i}",
                          location=self.room1)
        self.assertEqual(self.level(), before)

    def test_a_disconnected_player_body_still_counts(self):
        """`has_account` excluded these too — a linkdead body is still a
        body standing in the street.

        `char1`/`char2` are already in `room1` in the harness, so this
        counts them rather than moving them in: my first version
        "added" characters that were never absent and measured nothing.
        """
        self.assertFalse(self.char1.has_account)
        self.assertIn(self.char1, self.room1.contents)
        from world.emote import _perceives
        counted = [o for o in self.room1.contents if _perceives(o)]
        self.assertIn(self.char1, counted)
        self.assertIn(self.char2, counted)

    def test_it_uses_the_same_predicate_as_the_pose_audience(self):
        from world.emote import _perceives
        self.assertTrue(_perceives(self.npc()))
        self.assertFalse(_perceives(
            create_object("typeclasses.objects.Object", key="a crate",
                          location=self.room1)))


class TestTheConsumersSeeIt(EvenniaTest):
    """Crowd level is not flavour — two mechanics read it."""

    def test_stealth_reads_the_crowd(self):
        import inspect

        from world import stealth
        self.assertIn("calculate_crowd_level", inspect.getsource(stealth))

    def test_the_witness_system_reads_it_too(self):
        import inspect

        from world.director import witness
        self.assertIn("calculate_crowd_level", inspect.getsource(witness))


class TestAShortTillBuysLess(EvenniaTest):
    def affordable(self, *args):
        from world.butchery import _affordable
        return _affordable(*args)

    def yields(self):
        return [("rat_chops", 3), ("ground_mystery_meat", 3)]

    def cost(self, pairs):
        return sum(RAT_PRODUCTS[k]["buy"] * c for k, c in pairs)

    def test_a_full_till_buys_everything(self):
        want = self.yields()
        bought, spent = self.affordable(want, self.cost(want))
        self.assertEqual(dict(bought), dict(want))
        self.assertEqual(spent, self.cost(want))

    def test_a_short_till_buys_less(self):
        want = self.yields()
        bought, spent = self.affordable(want, 5)
        self.assertLess(self.cost(bought), self.cost(want))

    def test_it_never_spends_more_than_it_has(self):
        for till in range(0, 40):
            _bought, spent = self.affordable(self.yields(), till)
            self.assertLessEqual(spent, till, f"till {till}")

    def test_what_is_bought_costs_exactly_what_is_spent(self):
        """The whole defect: goods and money have to match."""
        for till in range(0, 40):
            bought, spent = self.affordable(self.yields(), till)
            self.assertEqual(self.cost(bought), spent, f"till {till}")

    def test_an_empty_till_buys_nothing(self):
        bought, spent = self.affordable(self.yields(), 0)
        self.assertEqual(spent, 0)
        self.assertEqual(self.cost(bought), 0)

    def test_it_buys_cheapest_first(self):
        """A short till should get the most animal it can, not blow the
        register on one premium cut."""
        want = [("rat_haunch", 1), ("ground_mystery_meat", 1)]
        prices = {k: RAT_PRODUCTS[k]["buy"] for k, _ in want}
        cheap = min(prices, key=prices.get)
        if prices[cheap] == max(prices.values()):
            self.skipTest("these two cuts cost the same")
        bought, _spent = self.affordable(want, prices[cheap])
        self.assertEqual(dict(bought).get(cheap), 1)


class TestTheDebitStillMatchesTheCredit(EvenniaTest):
    """#2814's half, pinned: the register must not be debited when
    nobody is paid."""

    def test_a_giverless_sale_pays_nothing(self):
        import inspect

        from world import butchery
        body = inspect.getsource(butchery.process_corpse)
        self.assertIn("if not (giver and giver.pk):", body)
        self.assertIn("payout = 0", body)
