"""A branded recipe's name does not turn conversation into an order (#2459).

`_recipe_keywords` derived a saved recipe's order keywords with a length
test alone: `len(w) > 2`. That drops `a`/`an`/`of`/`in`/`on`/`to` by
accident of length and lets `the`, `and` and `with` straight through.

So a bartender saving "The Reactor" armed the board with the keyword
`the`. `resolve_order` deliberately lets an ADDRESSED line order on a
bare board match -- that is documented design, not a bug -- so from then
on "to sully, the shift was long" poured a Reactor, took the money and
credited the register instead of answering.

Reproduced before fixing, against the real matcher:

    match_recipe("to sully, the shift was long",
                 [{"name": "The Reactor",
                   "order_keywords": ("the", "reactor")}])
      -> The Reactor

The sibling derivation `world.bar._drink_aliases` already filtered these
through `_ALIAS_STOPWORDS`; the two disagreed. The set is now imported
rather than copied so they cannot drift apart again.

No live board carries a stopword keyword today (measured: 0), because the
two authored menus hand-pick their keywords and only in-game saves reach
this path. Armed, not yet triggered.

Also covers the second half of #2459: `_check_stock` promised in its own
docstring to mirror `serve_from_shelf`'s finite test and did not -- it
dropped `always_finite`, so a board-style counter that is also
`is_infinite` would advertise a tray the till refuses. Latent today (the
live cart carries `is_infinite=False`), pinned so it stays that way.
"""
from unittest.mock import Mock

from evennia.utils.test_resources import EvenniaTest

from commands.bar_menu import _recipe_keywords
from world.bar import _ALIAS_STOPWORDS, match_recipe
from world.shop import service as service_mod

_check_stock = getattr(service_mod, "_check_stock", None)
_check_stock_board = getattr(service_mod, "_check_stock_board", None)


class RecipeKeywordTest(EvenniaTest):

    def test_the_is_not_a_keyword(self):
        self.assertNotIn("the", _recipe_keywords("The Reactor"))

    def test_and_and_with_are_not_keywords(self):
        kws = _recipe_keywords("Ash and Iron with Salt")
        self.assertNotIn("and", kws)
        self.assertNotIn("with", kws)

    def test_the_real_words_survive(self):
        # Control: filtering must not gut the name.
        kws = _recipe_keywords("The Reactor")
        self.assertIn("reactor", kws)

    def test_colour_codes_still_stripped(self):
        # #2605's fix must survive this one.
        self.assertEqual(_recipe_keywords("|rBloodwork|n"), ("bloodwork",))

    def test_a_name_that_is_all_stopwords_keeps_a_phrase(self):
        # Falling back to the unfiltered words would re-arm the defect;
        # a whole phrase orders the drink and cannot catch stray speech.
        kws = _recipe_keywords("The And")
        self.assertEqual(kws, ("the and",))
        self.assertFalse(any(k in _ALIAS_STOPWORDS for k in kws))

    def test_conversation_no_longer_orders_a_drink(self):
        # The defect, through the real matcher.
        menu = [{"name": "The Reactor",
                 "order_keywords": _recipe_keywords("The Reactor")}]
        self.assertIsNone(
            match_recipe("to sully, the shift was long", menu),
            "an ordinary sentence still pours a drink and takes the money")

    def test_the_drink_is_still_orderable_by_name(self):
        # Control: the whole point is that it stays buyable.
        menu = [{"name": "The Reactor",
                 "order_keywords": _recipe_keywords("The Reactor")}]
        got = match_recipe("pour me a reactor", menu)
        self.assertIsNotNone(got)
        self.assertEqual(got["name"], "The Reactor")


class CheckStockFiniteTest(EvenniaTest):
    """The tool and the till must not disagree about what is in stock."""

    def _post(self, *, is_infinite):
        post = Mock()
        post.db.item_inventory = {"rat_tail_stew": 0, "grilled_rat_chops": 2}
        post.db.is_infinite = is_infinite
        return post

    def _shelf(self, post):
        return [("rat_tail_stew", "bowl of rat tail stew", 5),
                ("grilled_rat_chops", "plate of grilled rat chops", 7)]

    def test_board_wrapper_exists(self):
        self.assertIsNotNone(
            _check_stock_board,
            "world.shop.service._check_stock_board is missing -- the "
            "board-style variant that makes the tool finite by STYLE")

    def test_a_board_counter_is_finite_even_when_infinite(self):
        self.assertIsNotNone(_check_stock_board, "_check_stock_board missing")
        post = self._post(is_infinite=True)
        orig = service_mod.shelf_of
        service_mod.shelf_of = self._shelf
        try:
            answer = _check_stock_board(post, "", Mock(), Mock())
        finally:
            service_mod.shelf_of = orig
        self.assertNotIn("rat tail stew", answer,
                         "the cart advertised a dish the till would refuse")
        self.assertIn("grilled rat chops", answer)

    def test_a_shelf_counter_that_is_infinite_still_lists_everything(self):
        # Control: the shelf style is NOT always_finite, so an infinite
        # shelf must keep listing its whole range.
        self.assertIsNotNone(_check_stock, "_check_stock missing")
        post = self._post(is_infinite=True)
        orig = service_mod.shelf_of
        service_mod.shelf_of = self._shelf
        try:
            answer = _check_stock(post, "", Mock(), Mock())
        finally:
            service_mod.shelf_of = orig
        self.assertIn("rat tail stew", answer)
        self.assertIn("grilled rat chops", answer)
