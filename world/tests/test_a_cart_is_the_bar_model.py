"""A cart is the bar model: you talk to whoever works it; `buy` does nothing (#3375).

Owner ruling 2026-09-13, three tiers as live today: bars are talk-only;
STORES keep the typed `buy` (and a manned store also serves you when you
speak to the keeper -- the owner is hesitant to make stores talk-only,
"a bit alien for a MUD"); VENDING machines are self-serve `buy`. CARTS move
to the bar model: `FoodCart.TAKES_BUY = False`, so `buy` at a cart is
refused before any coin moves and points you at whoever is working it.

The typed door at the cart used to complete the sale and narrate a
hard-coded SHELF gesture -- a cart has a board -- which is how #3375 was
found. Stores are shelf-styled, so their gesture is right.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.shop import CmdBuy


class CartIsTheBarModelTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.tokens = 500
        self.keeper = create_object("typeclasses.characters.Character", key="Ottilie", location=self.room1)
        self.cart = create_object("typeclasses.butcher.FoodCart", key="food cart", location=self.room1)
        self.cart.db.is_infinite = True
        self.cart.db.prototype_inventory = {"cigarette_pack_noir": 6}
        self.cart.db.post_keeper = self.keeper
        self.store = create_object("typeclasses.shopkeeper.ShopContainer", key="steel counter", location=self.room1)
        self.store.db.is_infinite = True
        self.store.db.prototype_inventory = {"cigarette_pack_noir": 6}
        self.store.db.post_keeper = self.keeper

    def _on_duty(self, who):
        return mock.patch("world.souls.posts.keeper_on_duty", return_value=who)

    # --- carts: bar model -------------------------------------------------------

    def test_buy_at_a_manned_cart_is_refused_and_names_the_operator(self):
        before = self.char1.tokens
        with self._on_duty(self.keeper), mock.patch("world.shop.service.hand_over") as hand_over:
            out = self.call(CmdBuy(), "cigarette_pack_noir from food cart")
        hand_over.assert_not_called()
        self.assertEqual(self.char1.tokens, before, "coin moved at a cart")
        self.assertIn("Ottilie", out or ""); self.assertIn("ask", (out or "").lower())

    def test_buy_at_an_unattended_cart_says_nobody_is_working_it(self):
        with self._on_duty(None):
            out = self.call(CmdBuy(), "cigarette_pack_noir from food cart")
        self.assertIn("nobody", (out or "").lower())
        self.assertEqual(self.char1.tokens, 500)

    # --- stores keep buy (owner hesitation: talk-only stores are alien) --------

    def test_buy_at_a_manned_store_still_sells(self):
        with self._on_duty(self.keeper):
            self.call(CmdBuy(), "cigarette_pack_noir from steel counter")
        self.assertLess(self.char1.tokens, 500, "a manned store refused buy")

    def test_buy_at_an_unbound_store_still_self_serves(self):
        shelf = create_object("typeclasses.shopkeeper.ShopContainer", key="cigarette machine", location=self.room1)
        shelf.db.is_infinite = True
        shelf.db.prototype_inventory = {"cigarette_pack_noir": 6}
        with self._on_duty(None):
            self.call(CmdBuy(), "cigarette_pack_noir from cigarette machine")
        self.assertLess(self.char1.tokens, 500, "the vending tier refused buy")
