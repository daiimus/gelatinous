"""Trade grounding belongs to the trade that owns it (#2427 follow-up).

#2427 moved the bar, cart and shelf grounding off deleted typeclass
methods (`_find_bar`/`_find_block`/`_find_counter`) and onto the POST,
so a successor standing the bar is grounded in it too. Right move.

The bar half degrades safely because it reads a bar-shaped attribute:
`post.db.menu` is empty on a non-bar and `menu` ends up None. The cart
and shelf halves do not -- they were written as:

    block   = post
    counter = post

which is true of EVERY post. So every posted NPC in the game picked up
butcher and shopkeeper grounding:

  * `buys` is assigned `sorted(ACCEPTED_BUTCHER_SPECIES)` before any
    stock is read, so it is set for anyone standing anything;
  * `cart_menu` / `shop_menu` come back `[]` rather than None, and `[]`
    is rendered EXPLICITLY -- "Your cart is SOLD OUT", "Your shelf is
    EMPTY".

Measured against the live game, all 49 posted NPCs were affected:

    Sully          bartender  -> buys=['rat'], cart_menu=[], shop_menu=[]
    Petra          dispatcher -> buys=['rat'], cart_menu=[], shop_menu=[]
    Bellows        tobacconist-> buys=['rat'], cart_menu=[]
    Ezra Vantomme  pawnbroker -> his SHOP SHELF rendered as a cart board

So a bartender's system prompt told him he buys animal carcasses and
that his cart was sold out, and a pawnbroker's shelf was described to
him twice, once as a butcher's board.

Gated on the JOB ARCHETYPE, which the service registry already
declares -- `butcher` for the cart, `merchant` for the shelf. That is
the same thing `job_of` means by "an off-duty vendor is not a vendor",
so an off-shift butcher correctly loses cart grounding too.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses import llm_persona


class TestGroundingFollowsTheArchetype(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="Testkeeper", location=self.room1)
        self.post = create_object("typeclasses.items.Item",
                                  key="a post", location=self.room1)
        self.post.db.prototype_inventory = {"SHIV": 5}
        self.post.db.item_inventory = {"SHIV": 2}

    def _persona(self, archetype):
        from world import service
        with mock.patch.object(service, "post_for", return_value=self.post), \
             mock.patch.object(service, "job_of",
                               return_value={"archetype": archetype}):
            return llm_persona.build_persona(self.npc)

    def test_a_bartender_is_not_told_they_buy_carcasses(self):
        p = self._persona("bartender")
        self.assertIsNone(p.get("buys"))

    def test_a_bartender_has_no_cart_and_no_shelf(self):
        """`[]` is not "nothing" -- it renders as SOLD OUT / EMPTY."""
        p = self._persona("bartender")
        self.assertIsNone(p.get("cart_menu"))
        self.assertIsNone(p.get("shop_menu"))

    def test_an_unclassified_post_holder_gets_no_trade_grounding(self):
        """39 of the 49 live posted NPCs have no archetype at all."""
        p = self._persona(None)
        self.assertIsNone(p.get("buys"))
        self.assertIsNone(p.get("cart_menu"))
        self.assertIsNone(p.get("shop_menu"))

    def test_a_merchant_still_gets_their_shelf(self):
        """The other half: this must not become "nobody is grounded"."""
        p = self._persona("merchant")
        self.assertTrue(p.get("shop_menu"))
        self.assertIsNone(p.get("cart_menu"))
        self.assertIsNone(p.get("buys"))

    def test_a_butcher_still_gets_their_cart_and_what_they_buy(self):
        p = self._persona("butcher")
        self.assertIsNotNone(p.get("cart_menu"))
        self.assertTrue(p.get("buys"))
        self.assertIsNone(p.get("shop_menu"))
