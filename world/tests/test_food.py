"""The cook step must terminate (#2810).

`cook_yields` loops `while all(remaining >= needed)`, and `all()` over an
empty mapping is vacuously True while the loop body consumes nothing — so
a recipe declaring no ingredients spins forever and grows its dish count
without bound. Everything in Evennia runs on the single reactor thread,
so that is not a slow cook, it is a hung server.

No shipped recipe is ingredient-less; a placeholder stub is the obvious
way to write one, which is why this is pinned rather than left to review.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.food import FOOD_INGREDIENT_CATALOG, FOOD_RECIPES, cook_yields


class TestCookYieldsTerminates(TestCase):
    def test_an_ingredientless_recipe_does_not_hang(self):
        stub = {"placeholder": {"ingredients": {}, "prototype": "X", "price": 1}}
        with patch.dict(FOOD_RECIPES, stub, clear=False):
            # would never return before the guard
            self.assertNotIn("placeholder", cook_yields({"rat_tail": 3}))

    def test_normal_recipes_still_cook(self):
        self.assertEqual(cook_yields({"rat_tail": 2}).get("rat_tail_stew"), 2)

    def test_nothing_in_nothing_out(self):
        self.assertEqual(cook_yields({}), {})
        self.assertEqual(cook_yields(None), {})


class TestEveryCutHasARecipe(TestCase):
    """A cut no recipe consumes is silently destroyed after the butcher
    has paid for it — `cook_yields` drops leftovers by design. The 1:1
    mapping is what keeps that harmless, so it is worth holding."""

    def test_no_orphan_ingredients(self):
        wanted = set()
        for recipe in FOOD_RECIPES.values():
            wanted |= set(recipe["ingredients"])
        orphans = sorted(set(FOOD_INGREDIENT_CATALOG) - wanted)
        self.assertEqual(orphans, [],
                         f"cuts no recipe consumes (paid for, then dropped): {orphans}")
