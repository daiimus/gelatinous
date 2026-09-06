"""A keeper's persona is grounded in the post they stand (#2427).

Build 143 deleted the `Butcher` and `Shopkeeper` classes and retyped every
body to `LLMNpc`. Two persona-grounding blocks still reached for their
methods:

    typeclasses/llm_persona.py   npc._find_block()    -> the butcher's cart
    typeclasses/llm_persona.py   npc._find_counter()  -> the shop shelf

Both are `None` on every NPC now, and both blocks were gated on
`callable(...)`, so `cart_menu`, `buys` and `shop_menu` were permanently
`None`. Ask Ottilie what she has and the model invents stock and prices --
the exact failure the comments above those blocks say they exist to
prevent -- and she no longer knows she only takes rats.

The asymmetry is what proves it is drift rather than design: the BAR
branch ten lines above was migrated and reads `service.post_for(npc)`
first. `NPC_PLATFORM_SPEC` lists all three of
`_find_bar`/`_find_counter`/`_find_block` as migrations to
`service.post_for()`. One of the three was done, which is why bars ground
correctly and nobody noticed.

The fallback could not compensate either: the `check_stock` tool appears
in tool LISTS but is never demonstrated in a few-shot, and
`LLM_GAMEMASTER_SPEC` records "demonstrate, don't describe" as a lesson
proven three times. That half is noted on the issue rather than fixed
here.

These tests assert the persona CONTENT, not which helper was called --
the point is that the keeper knows their real stock, however it is
fetched.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from typeclasses import llm_persona


class _PersonaCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = self.char1
        self.npc.location = self.room1
        self.post = self.obj1
        self.post.location = self.room1

    def persona(self):
        with mock.patch("world.service.post_for", return_value=self.post):
            return llm_persona.build_persona(self.npc)


class TestTheCartGroundsOnItsPost(_PersonaCase):
    def setUp(self):
        super().setUp()
        self.post.db.item_inventory = {"test_chops": 3}
        self.post.db.prototype_inventory = {"test_chops": 12}
        from evennia.prototypes.prototypes import save_prototype
        save_prototype({"prototype_key": "test_chops",
                        "key": "grilled rat chops",
                        "typeclass": "typeclasses.items.Item"})

    def test_the_real_stock_reaches_the_persona(self):
        text = str(self.persona())
        self.assertIn("grilled rat chops", text)

    def test_so_does_the_price(self):
        self.assertIn("12", str(self.persona()))

    def test_she_knows_what_she_buys(self):
        """"Ottilie also no longer knows she only takes rats." """
        from world.butchery import ACCEPTED_BUTCHER_SPECIES
        text = str(self.persona()).lower()
        self.assertTrue(
            any(sp.lower() in text for sp in ACCEPTED_BUTCHER_SPECIES),
            "the accepted species never reach the persona")


class TestTheShelfGroundsOnItsPost(_PersonaCase):
    def setUp(self):
        super().setUp()
        from evennia.prototypes.prototypes import save_prototype
        save_prototype({"prototype_key": "test_lighter",
                        "key": "zippo lighter",
                        "typeclass": "typeclasses.items.Item"})
        self.post.db.prototype_inventory = {"test_lighter": 25}
        self.post.db.is_infinite = True

    def test_the_shelf_reaches_the_persona(self):
        self.assertIn("zippo lighter", str(self.persona()))

    def test_an_out_of_stock_line_is_not_offered(self):
        self.post.db.is_infinite = False
        self.post.db.item_inventory = {"test_lighter": 0}
        self.assertNotIn("zippo lighter", str(self.persona()))

    def test_a_stocked_line_is(self):
        self.post.db.is_infinite = False
        self.post.db.item_inventory = {"test_lighter": 2}
        self.assertIn("zippo lighter", str(self.persona()))


class TestNoPostIsNotACrash(_PersonaCase):
    """Persona building never breaks on trade -- a body with no post
    still gets a persona, just without a board."""

    def test_a_postless_npc_still_builds(self):
        with mock.patch("world.service.post_for", return_value=None):
            self.assertIsNotNone(llm_persona.build_persona(self.npc))


class TestTheDeletedHelpersAreGone(EvenniaTest):
    """`_find_block` and `_find_counter` exist nowhere but these two
    `getattr` calls and two test monkeypatches. Nothing should depend on
    them being present."""

    def test_a_plain_npc_has_neither(self):
        npc = self.char1
        self.assertIsNone(getattr(npc, "_find_block", None))
        self.assertIsNone(getattr(npc, "_find_counter", None))
