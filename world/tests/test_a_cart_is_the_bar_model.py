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
from world.identity import get_apparent_uid
from world.tests._identity_helpers import make_recognition_entry


class CartIsTheBarModelTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.tokens = 500
        # A keeper with a REAL name and a composable sdesc, so the identity
        # pipeline has both to choose between (owner: "assigned name, not
        # the actual -- we have a lot of code that does this").
        self.keeper = create_object("typeclasses.characters.Character", key="Ottilie Krug", location=self.room1)
        self.keeper.height = "short"; self.keeper.build = "stocky"; self.keeper.sdesc_keyword = "woman"
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
        self.assertIn("ask", (out or "").lower())
        # A stranger gets the SDESC, never the real name.
        self.assertIn("woman", out or "", "refusal did not use the sdesc: %r" % out)
        self.assertNotIn("Ottilie", out or "", "refusal leaked the keeper's REAL name")

    def test_refusal_uses_the_name_the_buyer_assigned_not_the_real_one(self):
        # char1 remembers this face as "Tilly" -- their own label, which may be
        # wrong, and which is what they should be told. Never `key`.
        self.char1.recognition_memory = {
            get_apparent_uid(self.keeper): make_recognition_entry(assigned_name="Tilly"),
        }
        with self._on_duty(self.keeper):
            out = self.call(CmdBuy(), "cigarette_pack_noir from food cart")
        self.assertIn("Tilly", out or "", "refusal did not use the assigned name: %r" % out)
        self.assertNotIn("Ottilie", out or "", "refusal leaked the REAL name over the assigned one")
        self.assertNotIn("woman", out or "", "refusal fell back to the sdesc despite an assigned name")

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
