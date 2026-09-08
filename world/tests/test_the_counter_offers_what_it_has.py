"""Two findings from #2459.

**The keeper offered food the counter then refused.** `serve_from_shelf`
checks `item_inventory` counts before selling on a finite counter, but
the keeper's own `check_stock` tool called `shelf_of`, which lists every
`prototype_inventory` key regardless of count. So a butcher would offer
rat tail stew and then refuse to sell it — which reads as the NPC lying
rather than as an empty tray.

Listing sold-out lines is RIGHT for matching: you want the dish to
match so the counter can answer "out". It is wrong for the keeper's
answer to "what have you got", so the filter goes in the tool and not
in `shelf_of`. The finite test mirrors the sale's exactly, so the tool
and the till cannot disagree.

**`clean` could not pick up a plate.** A mixed drink carries
`db.is_drink`, but a dish spawned from its prototype carries neither
that nor `db.is_ingredient` — it is marked by TAGS, `("food",
"item_type")` and `("eat", "delivery_method")`, which is the only thing
separating food from drink in this catalogue. `clean`/`wipe` is the
counter's one tidy verb, so abandoned dishes accumulated on the bar
with no way to clear them.

**Two findings did not survive checking.** `prepare` ignoring a board
entry's `proto` was fixed by #2531 — `plate_or_mix` exists precisely so
a menu entry naming a prototype is PLATED rather than mixed into a fake
drink. And the order-keyword stopword finding is raised separately: its
own reporter marked it UNCERTAIN.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.shop.service import _check_stock, shelf_of


class _CounterCase(EvenniaTest):
    def counter(self, *, infinite=False):
        counter = create_object("typeclasses.objects.Object",
                                key="a cart", location=self.room1)
        counter.db.prototype_inventory = {"rat_tail_stew": 12}
        counter.db.item_inventory = {"rat_tail_stew": 0}
        counter.db.is_infinite = infinite
        return counter


class TestSoldOutIsNotOnOffer(_CounterCase):
    def test_a_sold_out_line_is_not_listed(self):
        counter = self.counter()
        self.assertIn("empty", _check_stock(counter, "", self.char1,
                                            self.char2).lower())

    def test_a_stocked_line_is_listed(self):
        counter = self.counter()
        counter.db.item_inventory = {"rat_tail_stew": 3}
        self.assertNotIn("empty", _check_stock(counter, "", self.char1,
                                               self.char2).lower())

    def test_an_infinite_counter_lists_everything(self):
        """A prototype shelf is bottomless — its inventory values are
        PRICES, not counts."""
        counter = self.counter(infinite=True)
        self.assertNotIn("empty", _check_stock(counter, "", self.char1,
                                               self.char2).lower())

    def test_shelf_of_still_lists_it_for_matching(self):
        """The filter belongs in the tool, not the matcher: a sold-out
        dish must still MATCH so the counter can say 'out'."""
        counter = self.counter()
        self.assertTrue([k for k, _d, _w in shelf_of(counter)])

    def test_no_counter_is_handled(self):
        self.assertIn("no counter", _check_stock(None, "", self.char1,
                                                 self.char2))


class TestCleanPicksUpAPlate(EvenniaTest):
    def bar(self):
        """A plain container stands in for the counter: what is under
        test is the CLUTTER PREDICATE, and `CmdBarClear` reads
        `bar.contents` like any other object. The suite's own bar tests
        use MagicMock bars for the same reason."""
        return create_object("typeclasses.objects.Object", key="the bar",
                             location=self.room1)

    def dish(self, bar):
        item = create_object("typeclasses.items.Item",
                             key="bowl of rat tail stew", location=bar)
        item.tags.add("food", category="item_type")
        item.tags.add("eat", category="delivery_method")
        return item

    def clutter(self, bar):
        return [
            o for o in bar.contents
            if getattr(o.db, "is_drink", False)
            or getattr(o.db, "is_ingredient", False)
            or o.tags.has("food", category="item_type")
            or o.tags.has("drink", category="item_type")
        ]

    def test_a_plated_dish_counts_as_clutter(self):
        bar = self.bar()
        dish = self.dish(bar)
        self.assertIn(dish, self.clutter(bar))

    def test_a_dish_carries_no_is_drink_attribute(self):
        """Which is exactly why the old filter missed it."""
        bar = self.bar()
        dish = self.dish(bar)
        self.assertFalse(getattr(dish.db, "is_drink", False))
        self.assertFalse(getattr(dish.db, "is_ingredient", False))

    def test_a_mixed_drink_still_counts(self):
        bar = self.bar()
        drink = create_object("typeclasses.items.Item", key="a shot",
                              location=bar)
        drink.db.is_drink = True
        self.assertIn(drink, self.clutter(bar))

    def _wipe(self, bar):
        """Drive the REAL command. The suite's own bar tests use a
        MagicMock bar for the same reason: `CmdBarClear` only needs
        `contents`, `is_bartender` and a display name."""
        from unittest.mock import MagicMock
        from typeclasses.bar import CmdBarClear
        stand_in = MagicMock()
        stand_in.contents = list(bar.contents)
        stand_in.is_bartender.return_value = True
        stand_in.key = "the bar"
        stand_in.get_display_name.return_value = "the bar"
        cmd = CmdBarClear()
        cmd.obj, cmd.caller, cmd.args = stand_in, self.char1, ""
        self.char1.location = self.room1
        cmd.func()

    def test_the_command_actually_clears_a_plate(self):
        """Behavioural, not a source check — the predicate tests above
        pass either way because they restate the filter."""
        bar = self.bar()
        dish = self.dish(bar)
        self._wipe(bar)
        self.assertFalse(dish.pk, "the plate survived a wipe")

    def test_it_still_clears_a_mixed_drink(self):
        bar = self.bar()
        drink = create_object("typeclasses.items.Item", key="a shot",
                              location=bar)
        drink.db.is_drink = True
        self._wipe(bar)
        self.assertFalse(drink.pk)

    def test_it_leaves_unrelated_items_alone(self):
        bar = self.bar()
        crate = create_object("typeclasses.items.Item", key="a crate",
                              location=bar)
        self._wipe(bar)
        self.assertTrue(crate.pk, "the wipe destroyed a crate")

    def test_unrelated_items_are_left_alone(self):
        bar = self.bar()
        crate = create_object("typeclasses.items.Item", key="a crate",
                              location=bar)
        self.assertNotIn(crate, self.clutter(bar))


class TestPrepareStaysFixed(EvenniaTest):
    """#2531 — a pin, not evidence."""

    def test_prepare_plates_a_prototype_entry(self):
        import inspect
        from typeclasses import bar as barmod
        self.assertIn("plate_or_mix", inspect.getsource(barmod))
