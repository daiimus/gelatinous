"""
Bars & recipes engine (BARS_AND_RECIPES_SPEC).

Ingredients carry canonical-substance contributions; a mix sums them (additive),
and the resulting drink applies them through the existing consumption pipeline
(`apply_substance`), so the per-effect caps (the alcohol cap), tolerance, and
addiction come free. Drinks are multi-use consumables — one sip per use.

All drink/ingredient content authored here is original to the colony.
"""

import re

from evennia import create_object

#: Base typeclass for spawned drinks. Must be an ``Item`` — the custom CmdGet
#: only picks up ``typeclasses.items.Item`` instances.
DRINK_TYPECLASS = "typeclasses.items.Item"

#: Words dropped when deriving searchable aliases from a drink's display name.
_ALIAS_STOPWORDS = {"a", "an", "the", "of", "with", "and", "in", "on", "to"}


def mix_effects(ingredients):
    """Sum the canonical-substance contributions of an iterable of ingredients.

    Each ingredient carries ``db.contributions`` == ``{substance_id: doses}``.
    Returns ``{substance_id: total_doses}``. Per-effect ceilings are enforced
    downstream by ``apply_substance`` at drink time (decision: scarcity + the
    existing caps balance it), not clamped here.
    """
    effects: dict[str, int] = {}
    for ing in ingredients:
        contrib = getattr(ing.db, "contributions", None) or {}
        for sid, doses in contrib.items():
            try:
                effects[sid] = effects.get(sid, 0) + int(doses)
            except (TypeError, ValueError):
                continue
    return {k: v for k, v in effects.items() if v}


def _drink_aliases(name, keywords=()):
    """Searchable aliases for a drink whose display name carries articles/phrases.

    "a mug of rotgut" -> {"mug", "rotgut"} (+ any recipe keywords), so a patron
    can ``drink rotgut`` / ``get rotgut from bar`` without typing the full name.
    """
    words = [
        w for w in re.findall(r"[a-z0-9']+", (name or "").lower())
        if w not in _ALIAS_STOPWORDS and len(w) > 2
    ]
    return list(dict.fromkeys([k.lower() for k in keywords] + words))


def make_drink(*, name, desc, effects, sips=3, taste="", location=None, keywords=()):
    """Create a multi-use drink consumable that plugs into the `drink` verb.

    The drink carries ``db.drink_effects`` (a ``{substance_id: doses}`` map
    applied per sip), ``db.uses_left`` (the number of sips), and the `drink`
    delivery tag so the existing consumption command accepts it. Aliases are
    derived from the name (+ recipe keywords) so the article-prefixed display
    name stays targetable.
    """
    drink = create_object(DRINK_TYPECLASS, key=name, location=location)
    drink.db.desc = desc
    drink.db.uses_left = max(1, int(sips))
    drink.db.drink_effects = dict(effects or {})
    drink.db.drink_taste = taste or ""
    drink.db.is_drink = True
    # Delivery tag — `supports_delivery(item, "drink")` looks for this.
    drink.tags.add("drink", category="delivery_method")
    aliases = _drink_aliases(name, keywords)
    if aliases:
        drink.aliases.add(aliases)
    return drink


def make_drink_from_recipe(recipe, *, location=None):
    """Create a drink from a recipe/menu dict (see HUB_AND_HOWL_MENU)."""
    return make_drink(
        name=recipe["name"],
        desc=recipe.get("desc", recipe["name"]),
        effects=recipe.get("effects", {}),
        sips=recipe.get("sips", 3),
        taste=recipe.get("taste", ""),
        location=location,
        keywords=recipe.get("order_keywords", ()),
    )


def match_recipe(order_text, menu):
    """Find the first menu recipe whose order keywords appear in `order_text`.

    `order_text` is the raw thing a patron said (e.g. "a rotgut, please").
    Returns the recipe dict or ``None``.
    """
    if not order_text or not menu:
        return None
    low = order_text.lower()
    for recipe in menu:
        for kw in recipe.get("order_keywords", (recipe.get("name", ""),)):
            if kw and kw.lower() in low:
                return recipe
    return None


# ---------------------------------------------------------------------------
# A starter menu for the Hub & Howl — scuzzy colony drinks. Original content.
# Effects use real substance ids (see world/substances/registry.py): `alcohol`
# (sedation cap 4), `opium` (strong). Flavour-only drinks carry no effects.
# ---------------------------------------------------------------------------
HUB_AND_HOWL_MENU = [
    {
        "name": "a mug of rotgut",
        "order_keywords": ("rotgut", "grain", "spirit", "cheap"),
        "price": 8,
        "sips": 3,
        "effects": {"alcohol": 1},
        "desc": "a dented tin mug of cloudy grain spirit, the colony's cheapest way to lose a shift",
        "taste": "It scours the throat like coolant — paint-thinner heat and a sour, metallic finish.",
        "craft": "reaches under the slab for an unlabelled jug and sloshes cloudy spirit into a dented tin mug",
    },
    {
        "name": "a glass of reactor wash",
        "order_keywords": ("reactor", "wash", "strong", "stiff"),
        "price": 15,
        "sips": 3,
        "effects": {"alcohol": 2},
        "desc": "a smudged glass of something amber and oily that catches the light wrong",
        "taste": "It hits like a dropped tool — hot, chemical, and gone numb before you swallow.",
        "craft": "pulls a smudged glass, free-pours two fingers of something amber and oily, and slides it over",
    },
    {
        "name": "a cup of channel fog",
        "order_keywords": ("fog", "channel", "milky", "smooth"),
        "price": 20,
        "sips": 4,
        "effects": {"alcohol": 1, "opium": 1},
        "desc": "a chipped ceramic cup of a milky, grey-green liquor that smells faintly of brine and poppy",
        "taste": "Smooth and cold going down, with a slow warmth that closes over you like the channel fog it's named for.",
        "craft": "measures a milky grey-green liquor into a chipped ceramic cup with the care of someone who knows what's in it",
    },
    {
        "name": "a mug of black recyc",
        "order_keywords": ("recyc", "black", "coffee", "caf", "sober"),
        "price": 5,
        "sips": 4,
        "effects": {},
        "desc": "a scalding mug of reclaimed caf, black as the inside of a vent and twice as bitter",
        "taste": "Bitter, scalding, and faintly of the recycler — but it's hot, and it's not alcohol.",
        "craft": "fills a mug from the battered caf urn at the end of the bar, no ceremony to it",
    },
]
