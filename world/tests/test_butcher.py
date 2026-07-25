"""The Butcher gig (GIG_PROTOTYPE_BUTCHER_SPEC): the deterministic
buy → break-down → pay transaction, condition-gated yields, species guard,
and the butcher archetype's tool scoping.

Methods bound to MagicMock stand-ins (the test_llm_npc pattern) with a fake
medical snapshot — no Evennia boot for the yield logic; routing tests patch
delay/create_object at the module seam.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.butcher as butchmod
from typeclasses.butcher import (
    ACCEPTED_BUTCHER_SPECIES, BUTCHER_DECAY_REFUSAL, RAT_PRODUCTS,
)


def _organ(container, hp=10, max_hp=10):
    return {"current_hp": hp, "max_hp": max_hp, "data": {"container": container}}


def _rat_snapshot(**overrides):
    """A full healthy rat snapshot; override per-organ to model damage."""
    organs = {
        "tail_vertebrae": _organ("tail"),
        "heart": _organ("chest"), "left_lung": _organ("chest"),
        "right_lung": _organ("chest"), "liver": _organ("abdomen"),
        "stomach": _organ("abdomen"), "left_kidney": _organ("abdomen"),
        "right_kidney": _organ("abdomen"),
        "left_hindleg_bone": _organ("left_hindleg"),
        "right_hindleg_bone": _organ("right_hindleg"),
        "brain": _organ("head"),
    }
    organs.update(overrides)
    return {"organs": organs}


def _corpse(snapshot=None, species="rat", severed=(), removed=(), decay=0.0):
    c = MagicMock()
    c.pk = 1
    c.db.species = species
    c.db.severed_locations = list(severed)
    c.db.removed_organs = list(removed)
    c.get_medical_snapshot = lambda: snapshot
    c.get_decay_factor = lambda: decay
    return c


def _butcher():
    b = MagicMock()
    b.location = "room"
    for name in ("_butcher_yields", "_process_corpse", "_refuse",
                 "_drop_from_hands"):
        setattr(b, name,
                getattr(butchmod.Butcher, name).__get__(b, butchmod.Butcher))
    # staticmethods: already plain functions off the class — do NOT re-bind
    # (a __get__ would inject a spurious self argument)
    b._refusal_line = butchmod.Butcher._refusal_line
    b._render_cuts = butchmod.Butcher._render_cuts
    b.hands = {}
    return b


class TestButcherYields(TestCase):
    """The condition-gated butchery table."""

    def _yields(self, corpse, decay=0.0):
        return dict(_butcher()._butcher_yields(corpse, decay))

    def test_clean_fresh_rat_full_cuts(self):
        y = self._yields(_corpse(_rat_snapshot()))
        self.assertEqual(y["rat_tail"], 1)
        self.assertEqual(y["rat_chops"], 3)
        self.assertEqual(y["rat_haunch"], 2)
        self.assertEqual(y["rat_offal"], 1)
        self.assertEqual(y["ground_mystery_meat"], 3)

    def test_severed_tail_no_tail(self):
        y = self._yields(_corpse(_rat_snapshot(), severed=["tail"]))
        self.assertNotIn("rat_tail", y)

    def test_shredded_trunk_no_chops(self):
        snap = _rat_snapshot(
            heart=_organ("chest", hp=0), left_lung=_organ("chest", hp=0),
            right_lung=_organ("chest", hp=0), liver=_organ("abdomen", hp=0),
            stomach=_organ("abdomen", hp=0), left_kidney=_organ("abdomen", hp=0),
            right_kidney=_organ("abdomen", hp=0))
        y = self._yields(_corpse(snap))
        self.assertNotIn("rat_chops", y)
        self.assertNotIn("rat_offal", y)   # shredded organs are no delicacy
        self.assertEqual(y["rat_haunch"], 2)  # legs untouched

    def test_harvested_organs_no_offal(self):
        y = self._yields(_corpse(_rat_snapshot(),
                                 removed=["heart", "liver", "left_kidney"]))
        self.assertNotIn("rat_offal", y)

    def test_decay_scales_meat_mass(self):
        fresh = self._yields(_corpse(_rat_snapshot()), decay=0.0)
        stale = self._yields(_corpse(_rat_snapshot()), decay=0.5)
        self.assertLess(stale["rat_chops"], fresh["rat_chops"])
        self.assertGreaterEqual(stale["ground_mystery_meat"], 1)

    def test_empty_snapshot_still_minces_something(self):
        y = self._yields(_corpse(None))
        self.assertEqual(list(y), ["ground_mystery_meat"])


class TestProcessCorpse(TestCase):
    """Guards + the transaction: species, decay, till, pay, destroy."""

    def _run(self, corpse, till=500):
        b = _butcher()
        block = MagicMock()
        block.db.register = till
        b._find_block = lambda: block
        giver = MagicMock()
        giver.pk = 1
        giver.tokens = 0
        with patch.object(butchmod, "spawn") as sp:
            sp.return_value = [MagicMock()]
            b._process_corpse(corpse, giver)
        return b, block, giver

    def test_human_corpse_refused_not_destroyed(self):
        corpse = _corpse(_rat_snapshot(), species="human")
        b, block, giver = self._run(corpse)
        corpse.delete.assert_not_called()
        corpse.move_to.assert_called()          # handed back to the floor
        self.assertEqual(giver.tokens, 0)
        say = b.execute_cmd.call_args.args[0]
        self.assertIn("say I don't grind people", say)

    def test_robot_corpse_refused(self):
        corpse = _corpse(_rat_snapshot(), species="robot")
        b, _, _ = self._run(corpse)
        corpse.delete.assert_not_called()
        self.assertIn("chrome and coolant", b.execute_cmd.call_args.args[0])

    def test_rotted_corpse_refused(self):
        corpse = _corpse(_rat_snapshot(), decay=BUTCHER_DECAY_REFUSAL + 0.1)
        b, _, giver = self._run(corpse)
        corpse.delete.assert_not_called()
        self.assertEqual(giver.tokens, 0)

    def test_dry_till_refuses_before_grinding(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=2)
        corpse.delete.assert_not_called()
        self.assertEqual(block.db.register, 2)
        self.assertIn("Till's dry", b.execute_cmd.call_args.args[0])

    def test_clean_rat_pays_and_destroys(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=500)
        corpse.delete.assert_called_once()
        # tail5 + 3 chops*3 + 2 haunch*3 + offal3 + 3 meat*1 = 26
        self.assertEqual(giver.tokens, 26)
        self.assertEqual(block.db.register, 500 - 26)
        emote = b.execute_cmd.call_args.args[0]
        self.assertTrue(emote.startswith("emote breaks the carcass down"))
        block.stock_cuts.assert_called_once()
        self.assertIn("counts 26 across the steel", emote)

    def test_payout_capped_by_till(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=10)
        self.assertEqual(giver.tokens, 10)
        self.assertEqual(block.db.register, 0)


class TestButcherArchetype(TestCase):
    """Tool scoping + the few-shot demonstrates the memory tools
    (tuning lesson: a 12B copies the few-shot, not the tool prose)."""

    def test_registered_and_scoped(self):
        from world.llm.prompt import ARCHETYPES, tool_names
        self.assertIn("butcher", ARCHETYPES)
        persona = {"persona_seed": {"archetype": "butcher"}}
        self.assertEqual(tool_names(persona),
                         ["look", "remember", "feel", "release"])

    def test_fewshot_demonstrates_memory_tools(self):
        from world.llm.prompt import ARCHETYPES
        tools = [e["assistant"]["tool"]
                 for e in ARCHETYPES["butcher"]["fewshot"]]
        self.assertIn("remember", tools)
        self.assertIn("feel", tools)
        self.assertEqual(tools[-1], "none")   # ends on restraint

    def test_duties_draw_the_ripper_line(self):
        from world.llm.prompt import ARCHETYPES
        duties = ARCHETYPES["butcher"]["duties"]
        self.assertIn("ripper", duties.lower())
        self.assertIn("chrome isn't food", duties)


class TestRatAccepted(TestCase):
    def test_species_set(self):
        self.assertIn("rat", ACCEPTED_BUTCHER_SPECIES)
        for banned in ("human", "synthetic_humanoid", "robot"):
            self.assertNotIn(banned, ACCEPTED_BUTCHER_SPECIES)

    def test_dishes_priced_with_margin(self):
        # every dish sells above the buy cost of its ingredients — the
        # cooked margin is what keeps the till solvent
        from world.food import FOOD_RECIPES
        for rid, recipe in FOOD_RECIPES.items():
            cost = sum(RAT_PRODUCTS[i]["buy"] * q
                       for i, q in recipe["ingredients"].items())
            self.assertGreater(recipe["price"], cost, rid)

    def test_prototypes_exist_and_are_edible(self):
        from evennia.prototypes.prototypes import search_prototype
        for key in RAT_PRODUCTS:
            protos = search_prototype(key)
            self.assertTrue(protos, f"prototype missing: {key}")
            proto = protos[0]
            tags = [tuple(t[:2]) for t in proto.get("tags", [])]
            self.assertIn(("eat", "delivery_method"), tags)


class TestBlockShop(TestCase):
    """The sell side: the block is a limited shop stocked by the grind, and
    sales credit the till (closing the buy/sell economy loop). Uses real
    Evennia objects for the purchase path."""

    def test_stock_and_purchase_cycle(self):
        from evennia.utils.test_resources import BaseEvenniaTest
        # run inside an Evennia test body for object creation
        class _T(BaseEvenniaTest):
            def runTest(self):
                from evennia import create_object
                block = create_object("typeclasses.butcher.FoodCart",
                                      key="test cart", location=self.room1)
                block.db.register = 100
                # raw cuts in -> COOKED DISHES on the menu (world.food recipes)
                block.stock_cuts({"rat_chops": 2, "rat_tail": 1})
                self.assertEqual(block.db.item_inventory["grilled_rat_chops"], 2)
                self.assertEqual(block.db.item_inventory["rat_tail_stew"], 1)
                self.assertEqual(block.db.prototype_inventory["grilled_rat_chops"], 8)
                self.assertEqual(block.db.prototype_inventory["rat_tail_stew"], 12)
                self.assertNotIn("rat_chops", block.db.item_inventory)  # raw not sold
                buyer = self.char1
                buyer.tokens = 50
                ok, item = block.purchase_item(buyer, "grilled_rat_chops")
                self.assertTrue(ok)
                self.assertEqual(item.location, buyer)
                self.assertEqual(buyer.tokens, 42)               # paid 8
                self.assertEqual(block.db.register, 108)          # till credited
                self.assertEqual(block.db.item_inventory["grilled_rat_chops"], 1)
                # the spawned cut is edible, ingredient-grade
                self.assertTrue(item.tags.has("eat", category="delivery_method"))
                self.assertEqual(item.db.uses_left, 2)   # a plated dish is two bites
                # drain the stock: second buy ok, third refused
                ok, _ = block.purchase_item(buyer, "grilled_rat_chops")
                self.assertTrue(ok)
                ok, msg = block.purchase_item(buyer, "grilled_rat_chops")
                self.assertFalse(ok)
        t = _T("runTest"); t.setUp()
        try:
            t.runTest()
        finally:
            t.tearDown()


class TestFoodLayer(TestCase):
    """world/food.py: the ingredient catalog + recipes are coherent, and the
    cook step maps cuts to dishes."""

    def test_recipes_reference_real_ingredients(self):
        from world.food import FOOD_INGREDIENT_CATALOG, FOOD_RECIPES
        for rid, recipe in FOOD_RECIPES.items():
            for ing in recipe["ingredients"]:
                self.assertIn(ing, FOOD_INGREDIENT_CATALOG, f"{rid} -> {ing}")
            self.assertGreater(recipe["price"], 0)

    def test_dish_prototypes_exist_and_are_edible(self):
        from evennia.prototypes.prototypes import search_prototype
        from world.food import FOOD_RECIPES
        for rid, recipe in FOOD_RECIPES.items():
            protos = search_prototype(recipe["prototype"])
            self.assertTrue(protos, f"dish prototype missing: {rid}")
            tags = [tuple(t[:2]) for t in protos[0].get("tags", [])]
            self.assertIn(("eat", "delivery_method"), tags)

    def test_cook_yields_full_grind(self):
        from world.food import cook_yields
        dishes = cook_yields({"rat_tail": 1, "rat_chops": 3, "rat_haunch": 2,
                              "rat_offal": 1, "ground_mystery_meat": 3})
        self.assertEqual(dishes, {"rat_tail_stew": 1, "grilled_rat_chops": 3,
                                  "roast_rat_haunch": 2, "butchers_breakfast": 1,
                                  "mystery_skewer": 3})

    def test_cook_yields_ignores_unknown(self):
        from world.food import cook_yields
        self.assertEqual(cook_yields({"mystery_gland": 4}), {})

    def test_contributions_seam(self):
        # empty today, but the summation seam works (spec §7 tier 3)
        from world.food import dish_contributions
        self.assertEqual(dish_contributions("rat_tail_stew"), {})


class TestCartSeating(TestCase):
    """The cart is its own seating (BarCounter pattern): `sit cart` resolves
    because FoodCart carries the Seating mixin + posture config."""

    def test_cart_is_seating_with_slots(self):
        from typeclasses.furniture import Seating
        self.assertTrue(issubclass(butchmod.FoodCart, Seating))

    def test_seating_defaults(self):
        from unittest.mock import MagicMock
        cart = MagicMock()
        cart.db.postures = ("sitting",)
        cart.db.capacity = 4
        allows = butchmod.FoodCart.allows.__get__(cart, butchmod.FoodCart)
        self.assertTrue(allows("sitting"))
        self.assertFalse(allows("lying"))
