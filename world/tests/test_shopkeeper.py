"""The Shopkeeper role: deterministic spoken orders against the real shelf,
hand-delivery purchases, base till crediting, and persona shelf grounding."""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest

import typeclasses.shopkeeper as shopmod


SHELF = [("cigarette_pack_noir", "pack of Noir cigarettes",
          {"pack", "of", "noir", "cigarettes"}),
         ("cigarette_pack_neutral", "pack of Longhaul cigarettes",
          {"pack", "of", "longhaul", "cigarettes"}),
         ("old_meridian_whiskey", "bottle of Old Meridian whiskey",
          {"bottle", "of", "old", "meridian", "whiskey", "import"})]


class TestShopOrderMatching(TestCase):
    def _match(self, speech):
        b = MagicMock()
        b._shelf = lambda: SHELF
        return shopmod.Shopkeeper._match_shop_order.__get__(
            b, shopmod.Shopkeeper)(speech)

    def test_orders_matched(self):
        for speech, want in (
                ("a pack of noirs?", None),              # cue-less question
                ("gimme a pack of noir cigarettes", "cigarette_pack_noir"),
                ("can i get the old meridian?", "old_meridian_whiskey"),
                ("longhauls, please", "cigarette_pack_neutral"),
                ("i'll take the whiskey", "old_meridian_whiskey")):
            self.assertEqual(self._match(speech), want, speech)

    def test_ambiguous_tie_flagged(self):
        # "a pack of cigarettes" overlaps both packs equally
        self.assertEqual(self._match("gimme a pack of cigarettes"),
                         "ambiguous")

    def test_non_orders_ignored(self):
        for speech in ("what's the strongest thing you sell?",
                       "rough shift?", "i smoked my last longhaul yesterday",
                       ""):
            self.assertIsNone(self._match(speech), speech)


class TestShopOrderFulfilment(TestCase):
    def _keeper(self, match="cigarette_pack_noir", stock=3, price=6,
                tokens=50, infinite=False):
        b = MagicMock()
        b.location = "room"
        counter = MagicMock()
        counter.db.is_infinite = infinite
        counter.db.item_inventory = {match: stock} if match else {}
        counter.get_price = lambda k: price
        item = MagicMock(); item.key = "pack of Noir cigarettes"
        counter.purchase_item = MagicMock(return_value=(True, item))
        b._find_counter = lambda: counter
        b._match_shop_order = lambda s: match
        b._address_handle = lambda p: "the lean man"
        patron = MagicMock(); patron.location = "room"; patron.tokens = tokens
        b._fulfil_shop_order = shopmod.Shopkeeper._fulfil_shop_order.__get__(
            b, shopmod.Shopkeeper)
        b.serve_purchase = shopmod.Shopkeeper.serve_purchase.__get__(
            b, shopmod.Shopkeeper)
        return b, counter, patron

    def test_serve_hands_item_over(self):
        b, counter, patron = self._keeper()
        b._fulfil_shop_order("gimme the noirs", patron)
        counter.purchase_item.assert_called_once_with(
            patron, "cigarette_pack_noir")
        emote = b.execute_cmd.call_args.args[0]
        self.assertIn("presses it into the lean man's hand", emote)
        self.assertIn("sweeps 6 into the till", emote)

    def test_ambiguous_asks(self):
        b, counter, patron = self._keeper(match="ambiguous")
        b._fulfil_shop_order("a pack of cigarettes", patron)
        counter.purchase_item.assert_not_called()
        self.assertIn("more particular", b.execute_cmd.call_args.args[0])

    def test_sold_out_refused(self):
        b, counter, patron = self._keeper(stock=0)
        b._fulfil_shop_order("gimme the noirs", patron)
        counter.purchase_item.assert_not_called()
        self.assertIn("Out of that", b.execute_cmd.call_args.args[0])

    def test_broke_patron_refused(self):
        b, counter, patron = self._keeper(tokens=2)
        b._fulfil_shop_order("gimme the noirs", patron)
        counter.purchase_item.assert_not_called()
        self.assertIn("That's 6", b.execute_cmd.call_args.args[0])


@override_settings(PROTOTYPE_MODULES=["world.prototypes"])
class TestPurchaseHandDelivery(BaseEvenniaTest):
    """Base ShopContainer: the item lands in a free hand and the till is
    credited when a register exists."""

    def test_hand_delivery_and_till(self):
        from evennia import create_object
        counter = create_object("typeclasses.shopkeeper.ShopContainer",
                                key="test counter", location=self.room1)
        counter.db.is_infinite = True
        counter.db.prototype_inventory = {"cigarette_pack_noir": 6}
        counter.db.register = 100
        buyer = create_object("typeclasses.characters.Character",
                              key="buyer", location=self.room1)
        buyer.tokens = 50
        ok, item = counter.purchase_item(buyer, "cigarette_pack_noir")
        self.assertTrue(ok)
        self.assertEqual(item.location, buyer)
        held = [v for v in (buyer.hands or {}).values() if v]
        self.assertIn(item, held)                     # in hand, not just bag
        self.assertEqual(buyer.tokens, 44)
        self.assertEqual(counter.db.register, 106)    # till credited

    def test_no_register_no_credit_no_crash(self):
        from evennia import create_object
        counter = create_object("typeclasses.shopkeeper.ShopContainer",
                                key="bare counter", location=self.room1)
        counter.db.is_infinite = True
        counter.db.prototype_inventory = {"cigarette_pack_noir": 6}
        buyer = self.char1
        buyer.tokens = 20
        ok, _ = counter.purchase_item(buyer, "cigarette_pack_noir")
        self.assertTrue(ok)
        self.assertIsNone(counter.db.register)


class TestBuyRoutesThroughKeeper(TestCase):
    """The buy command: a keeper minding the counter serves the sale in
    person; unmanned counters stay self-service."""

    def _cmd(self, room_contents):
        from commands.shop import CmdBuy
        cmd = CmdBuy()
        buyer = MagicMock()
        buyer.location.contents = room_contents
        return cmd, buyer

    def _keeper(self, counter, merchant=True):
        keeper = MagicMock()
        keeper.is_merchant = merchant
        keeper._find_counter = lambda: counter
        return keeper

    def test_keeper_at_this_counter_found(self):
        counter = MagicMock()
        keeper = self._keeper(counter)
        cmd, buyer = self._cmd([keeper, counter])
        self.assertIs(cmd._find_keeper(buyer, counter), keeper)

    def test_strangers_counter_not_served(self):
        counter, other = MagicMock(), MagicMock()
        keeper = self._keeper(other)          # minds a different fixture
        cmd, buyer = self._cmd([keeper, counter])
        self.assertIsNone(cmd._find_keeper(buyer, counter))

    def test_non_merchant_ignored(self):
        counter = MagicMock()
        bystander = self._keeper(counter, merchant=False)
        cmd, buyer = self._cmd([bystander, counter])
        self.assertIsNone(cmd._find_keeper(buyer, counter))

    def test_serve_purchase_emote(self):
        b = MagicMock()
        b._address_handle = lambda p: "the lean man"
        item = MagicMock(); item.key = "syringe of guttervenom"
        shopmod.Shopkeeper.serve_purchase.__get__(
            b, shopmod.Shopkeeper)(MagicMock(), item, 15)
        emote = b.execute_cmd.call_args.args[0]
        self.assertIn("presses it into the lean man's hand", emote)
        self.assertIn("sweeps 15 into the till", emote)


class TestShelfGrounding(TestCase):
    def test_shelf_rendered_with_anti_invention(self):
        from world.llm.prompt import render_persona
        card = render_persona({
            "persona_seed": {"archetype": "merchant", "name": "Bellows"},
            "shop_menu": ["pack of Noir cigarettes (6 tokens)"]})
        self.assertIn("On your shelf RIGHT NOW", card)
        self.assertIn("never invent goods", card)
        self.assertIn("TOKENS", card)

    def test_empty_shelf_explicit(self):
        from world.llm.prompt import render_persona
        card = render_persona({
            "persona_seed": {"archetype": "merchant", "name": "B"},
            "shop_menu": []})
        self.assertIn("EMPTY", card)

    def test_merchant_grants_check_stock(self):
        from world.llm.prompt import tool_names
        self.assertIn("check_stock",
                      tool_names({"persona_seed": {"archetype": "merchant"}}))
