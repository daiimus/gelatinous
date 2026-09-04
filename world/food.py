"""The food layer — the bar's ingredient pattern applied to eating.

Mirrors ``world/bar.py``: a **FOOD_INGREDIENT_CATALOG** (ingredient id →
role / substance contributions / flavour, the same shape as
``INGREDIENT_CATALOG``) and **FOOD_RECIPES** (dish → the ingredients it
consumes + a price). The butcher's grind produces catalog ingredients; her
block cooks them 1:1 into dishes and sells THOSE (GIG_PROTOTYPE_BUTCHER_SPEC
§7 tier 2). When player kitchens / grocery buying arrive, the raw ingredients
start circulating through this same catalog — the recipes and contributions
are already waiting.

Contributions are empty for now (no nutrition substance is registered yet);
the slots are the point — a future toxin-traced or drugged carcass flows its
substances through the ingredient into the dish (spec §7 tier 3).
"""

#: Food component role (the ``ROLE_SPIRIT`` analogue).
ROLE_PROTEIN = "protein"

#: The butcher's cuts as REAL ingredients (bar-catalog shape). ``prototype``
#: names the spawnable raw-item form (world/prototypes.py).
FOOD_INGREDIENT_CATALOG = {
    "rat_tail": {
        "name": "rat tail", "role": ROLE_PROTEIN, "contributions": {},
        "flavour": "gelatinous slow-cook richness",
        "desc": "a skinned rat tail, coiled and tied with butcher's twine",
        "keywords": ("tail",), "prototype": "rat_tail",
    },
    "rat_chops": {
        "name": "rat chops", "role": ROLE_PROTEIN, "contributions": {},
        "flavour": "lean, mineral-edged meat",
        "desc": "center-cut rat chops, pale and lean on the bone",
        "keywords": ("chops", "chop"), "prototype": "rat_chops",
    },
    "rat_haunch": {
        "name": "rat haunch", "role": ROLE_PROTEIN, "contributions": {},
        "flavour": "dark, gamey roast meat",
        "desc": "a skinned, hock-tied rat hindquarter",
        "keywords": ("haunch",), "prototype": "rat_haunch",
    },
    "rat_offal": {
        "name": "rat offal", "role": ROLE_PROTEIN, "contributions": {},
        "flavour": "iron-rich organ meat",
        "desc": "a waxed-paper twist of sound rat organs",
        "keywords": ("offal",), "prototype": "rat_offal",
    },
    "ground_mystery_meat": {
        "name": "ground mystery meat", "role": ROLE_PROTEIN, "contributions": {},
        "flavour": "salt, fat, and ambiguity",
        "desc": "a dense brick of pale ground meat, wrapper stamped MEAT",
        "keywords": ("meat", "mystery"), "prototype": "ground_mystery_meat",
    },
}

#: Dishes: what a kitchen makes of the catalog. ``ingredients`` maps catalog
#: ids to quantities consumed; ``prototype`` is the servable item
#: (world/prototypes.py); ``price`` is the cooked sell price (the butcher's
#: value-add margin over the raw cut lives here).
FOOD_RECIPES = {
    "rat_tail_stew": {
        "name": "rat tail stew", "ingredients": {"rat_tail": 1},
        "price": 12, "prototype": "rat_tail_stew",
        "keywords": ("stew",),
    },
    "grilled_rat_chops": {
        "name": "grilled rat chops", "ingredients": {"rat_chops": 1},
        "price": 8, "prototype": "grilled_rat_chops",
        "keywords": ("grilled", "chops"),
    },
    "roast_rat_haunch": {
        "name": "roast rat haunch", "ingredients": {"rat_haunch": 1},
        "price": 8, "prototype": "roast_rat_haunch",
        "keywords": ("roast", "haunch"),
    },
    "butchers_breakfast": {
        "name": "butcher's breakfast", "ingredients": {"rat_offal": 1},
        "price": 8, "prototype": "butchers_breakfast",
        "keywords": ("breakfast", "offal", "fry"),
    },
    "mystery_skewer": {
        "name": "mystery skewer", "ingredients": {"ground_mystery_meat": 1},
        "price": 3, "prototype": "mystery_skewer",
        "keywords": ("skewer",),
    },
}


def cook_yields(ingredient_counts):
    """Convert raw-ingredient counts into dish counts, greedily.

    ``{catalog_id: count}`` → ``{recipe_id: count}``. Each recipe consumes its
    declared ingredients; with the current 1:1 recipes every cut becomes its
    dish. Ingredients no recipe wants are left uncooked (dropped)."""
    remaining = dict(ingredient_counts or {})
    dishes = {}
    for recipe_id, recipe in FOOD_RECIPES.items():
        needs = recipe["ingredients"]
        if not needs:
            # `all()` over an empty mapping is vacuously True and the body
            # consumes nothing, so an ingredient-less recipe spins forever
            # and grows `dishes` without bound — on the single reactor
            # thread, which wedges the server (#2810). A recipe that eats
            # nothing cannot be cooked; skip it rather than hang.
            continue
        while all(remaining.get(k, 0) >= q for k, q in needs.items()):
            for k, q in needs.items():
                remaining[k] = remaining.get(k, 0) - q
            dishes[recipe_id] = dishes.get(recipe_id, 0) + 1
    return dishes


def dish_contributions(recipe_id):
    """Sum a dish's substance contributions from its ingredients — the same
    additive model as ``world.bar.project_mix``. Empty today; the seam the
    provenance tier (spec §7 tier 3) flows through."""
    recipe = FOOD_RECIPES.get(recipe_id) or {}
    total = {}
    for ing_id, qty in (recipe.get("ingredients") or {}).items():
        contribs = (FOOD_INGREDIENT_CATALOG.get(ing_id) or {}).get("contributions") or {}
        for substance, doses in contribs.items():
            total[substance] = total.get(substance, 0) + doses * qty
    return total
