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
from unittest import mock
from unittest.mock import patch

import world.food as food

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



class TestCookYieldsAlwaysTerminates(TestCase):
    """`cook_yields`' greedy loop has no progress guarantee. Termination
    rests entirely on every recipe declaring at least one ingredient at a
    POSITIVE quantity, and nothing validates that.

    This is worse than an ordinary infinite loop: it runs synchronously
    inside a Twisted reactor callback (process_corpse -> stock_cuts ->
    here, scheduled via `delay`), so it does not hang one player's
    command -- it wedges the whole server. No ticks, no other players'
    input, no shutdown, and `dishes` growing without bound.

    #2810 fixed the empty-ingredients shape. The zero-quantity shape
    survived it (#2686): `needs` is non-empty so that guard never fired,
    and `all(remaining >= 0)` stays true while subtracting nothing.
    Measured before the fix: 2,000,000 iterations, zero progress.

    Each case runs on a worker thread with a join timeout, so a
    regression FAILS the suite instead of hanging it.
    """

    def _cook(self, counts, timeout=5.0):
        import threading
        box = {}

        def run():
            try:
                box["out"] = food.cook_yields(counts)
            except Exception as err:      # noqa: BLE001 — reported below
                box["err"] = err

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            self.fail("cook_yields did not terminate within "
                      f"{timeout}s — the reactor would be wedged")
        if "err" in box:
            raise box["err"]
        return box["out"]

    def test_a_zero_quantity_recipe_does_not_spin(self):
        with mock.patch.dict(food.FOOD_RECIPES,
                             {"stub": {"ingredients": {"rat_tail": 0}}},
                             clear=True):
            self.assertEqual(self._cook({"rat_tail": 1}), {})

    def test_a_negative_quantity_recipe_does_not_spin(self):
        with mock.patch.dict(food.FOOD_RECIPES,
                             {"stub": {"ingredients": {"rat_tail": -1}}},
                             clear=True):
            self.assertEqual(self._cook({"rat_tail": 1}), {})

    def test_an_ingredientless_recipe_does_not_spin(self):
        """The #2810 case, kept so it cannot regress."""
        with mock.patch.dict(food.FOOD_RECIPES,
                             {"stub": {"ingredients": {}}}, clear=True):
            self.assertEqual(self._cook({"rat_tail": 1}), {})

    def test_one_bad_recipe_does_not_stop_the_good_ones(self):
        """The pin: skipping an uncookable recipe must not skip the rest."""
        with mock.patch.dict(food.FOOD_RECIPES, {
                "stub": {"ingredients": {"rat_tail": 0}},
                "real": {"ingredients": {"rat_tail": 1}}}, clear=True):
            self.assertEqual(self._cook({"rat_tail": 3}), {"real": 3})

    def test_a_normal_recipe_still_cooks(self):
        with mock.patch.dict(food.FOOD_RECIPES,
                             {"real": {"ingredients": {"rat_tail": 2}}},
                             clear=True):
            self.assertEqual(self._cook({"rat_tail": 5}), {"real": 2})

    def test_every_shipped_recipe_is_cookable(self):
        """The live table, so a stub entry added later is caught here
        rather than by the server stopping."""
        for rid, recipe in FOOD_RECIPES.items():
            needs = recipe["ingredients"]
            self.assertTrue(needs, f"{rid} declares no ingredients")
            for k, q in needs.items():
                self.assertGreater(q, 0, f"{rid}.{k} is not positive")
