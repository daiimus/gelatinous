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
    derived from the name (+ recipe keywords) so the bare display name stays
    targetable.

    The item *key* carries no leading article (house convention — display sites
    prepend "a"/"an"/"the"), so a stray "a " in a recipe name is stripped here
    to avoid the double-article ("A a mug of rotgut...") render.
    """
    from world.search import strip_leading_article

    name = strip_leading_article((name or "").strip())
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
# Free snacks (BARS_AND_RECIPES_SPEC §10) — bottomless colony ambiance, no
# cost, nothing enters inventory. A bar's db.snacks is a fixed list; patrons
# `eat <snack> [from <bar>]` to nibble in place. Original content.
# ---------------------------------------------------------------------------
DEFAULT_BAR_SNACKS = [
    {
        "name": "brine pods",
        "order_keywords": ("brine", "pods", "pod"),
        "desc": "a chipped bowl of pale, rubbery brine pods, set out free for the taking",
        "taste": "Salt-slick and faintly chemical, they squeak against your teeth and leave a briny sting at the back of the throat.",
    },
    {
        "name": "synth-jerky",
        "order_keywords": ("jerky", "synth-jerky", "synth", "meat"),
        "desc": "a rack of dark, twisted synth-jerky strips, free for the taking",
        "taste": "Tough, smoky, and aggressively over-salted — more chew than flavour, which is the point: it keeps you drinking.",
    },
    {
        "name": "ration crackers",
        "order_keywords": ("crackers", "cracker", "ration", "rations"),
        "desc": "an open tin of dry ration crackers, free for the taking",
        "taste": "Dry, bland, and faintly of cardboard — they soak up whatever you've been pouring down your neck.",
    },
]


# ---------------------------------------------------------------------------
# Ingredients & mixing (BARS_AND_RECIPES_SPEC §3/§4)
#
# An ingredient is an ordinary item carrying a substance-contribution profile —
# DOSES of real registered substances (world/substances/registry.py), summed
# additively at mix time and capped. A garnish is a flavour-only ingredient
# (empty contributions). v1 has no supplier economy, so this catalog seeds a
# few spawnable ingredients to make crafting exercisable now.
# ---------------------------------------------------------------------------

#: Per-substance dose ceiling on a single mix — the light safety-net cap
#: (decision #12) so stacking one ingredient can't overshoot. Tuned in play.
MIX_EFFECT_CAP = 4

#: Cocktail component roles (the identity layer — orthogonal to the substance
#: contributions that drive effects). A spirit also carries a `spirit` type.
ROLE_SPIRIT = "spirit"

#: Each ingredient: substance `contributions` (DOSES → effects), a cocktail
#: `role`, an optional `spirit` type (role == spirit only), and `flavour` prose.
#: Spirits are alcohol 2, modifiers alcohol 1, garnishes/mixers flavour-only.
#: Earth-import classics sit beside scuzzy colony spirits; loose role-matching
#: (below) means a colony spirit makes a grimy spin of a classic.
INGREDIENT_CATALOG = {
    # ---- Earth-import spirits ------------------------------------------
    "gin": {"name": "bottle of gin", "role": ROLE_SPIRIT, "spirit": "gin",
            "contributions": {"alcohol": 2}, "flavour": "juniper-sharp and botanical",
            "desc": "an Earth-import bottle of gin, label half scoured away", "keywords": ("gin",)},
    "whiskey": {"name": "bottle of whiskey", "role": ROLE_SPIRIT, "spirit": "whiskey",
            "contributions": {"alcohol": 2}, "flavour": "oaky and caramel-warm",
            "desc": "a squat Earth-import bottle of amber whiskey", "keywords": ("whiskey", "whisky")},
    "rum": {"name": "bottle of white rum", "role": ROLE_SPIRIT, "spirit": "rum",
            "contributions": {"alcohol": 2}, "flavour": "light and sugarcane-sweet",
            "desc": "a clear Earth-import bottle of white rum", "keywords": ("rum",)},
    "mezcal": {"name": "bottle of mezcal", "role": ROLE_SPIRIT, "spirit": "mezcal",
            "contributions": {"alcohol": 2}, "flavour": "smoky roasted agave",
            "desc": "a hand-labelled Earth-import bottle of mezcal", "keywords": ("mezcal",)},
    "tequila": {"name": "bottle of tequila", "role": ROLE_SPIRIT, "spirit": "tequila",
            "contributions": {"alcohol": 2}, "flavour": "bright and peppery agave",
            "desc": "an Earth-import bottle of silver tequila", "keywords": ("tequila",)},
    "vodka": {"name": "bottle of vodka", "role": ROLE_SPIRIT, "spirit": "vodka",
            "contributions": {"alcohol": 2}, "flavour": "clean and near-flavourless",
            "desc": "a frosted Earth-import bottle of vodka", "keywords": ("vodka",)},
    # ---- Scuzzy colony spirits (grimy spins of the classics) -----------
    "grain_mash": {"name": "jar of grain mash", "role": ROLE_SPIRIT, "spirit": "grain mash",
            "contributions": {"alcohol": 1}, "flavour": "raw, paint-stripping grain spirit",
            "desc": "a sealed jar of cloudy fermented grain mash — the colony's base spirit", "keywords": ("grain", "mash")},
    "reactor_cut": {"name": "flask of reactor cut", "role": ROLE_SPIRIT, "spirit": "reactor cut",
            "contributions": {"alcohol": 2}, "flavour": "harsh chemical heat",
            "desc": "a scratched flask of high-proof reactor cut, distilled too close to the coolant lines", "keywords": ("reactor", "cut", "proof")},
    # ---- Colony additives / mixers (no cocktail role) ------------------
    "poppy_tincture": {"name": "vial of poppy tincture", "role": None,
            "contributions": {"opium": 1}, "flavour": "bitter brine-and-poppy",
            "desc": "a dropper vial of dark poppy tincture, cut with channel brine", "keywords": ("poppy", "tincture", "opium")},
    "channel_cordial": {"name": "bottle of channel cordial", "role": None, "contributions": {},
            "flavour": "milky, grey-green, faintly sweet",
            "desc": "a bottle of milky grey-green cordial pressed from channel kelp", "keywords": ("channel", "cordial", "kelp")},
    "caf": {"name": "jug of reclaimed caf", "role": None, "contributions": {},
            "flavour": "bitter, scalding reclaimed caf",
            "desc": "a battered jug of black reclaimed caf", "keywords": ("caf", "coffee", "recyc")},
    # ---- Modifiers (alcohol 1) -----------------------------------------
    "bitter_aperitivo": {"name": "bottle of bitter aperitivo", "role": "bitter_aperitivo",
            "contributions": {"alcohol": 1}, "flavour": "bitter blood-orange",
            "desc": "a vivid red bottle of bitter aperitivo", "keywords": ("aperitivo", "bitter", "red")},
    "sweet_vermouth": {"name": "bottle of sweet vermouth", "role": "sweet_vermouth",
            "contributions": {"alcohol": 1}, "flavour": "herbal and sweet",
            "desc": "a dark bottle of sweet red vermouth", "keywords": ("sweet", "vermouth")},
    "dry_vermouth": {"name": "bottle of dry vermouth", "role": "dry_vermouth",
            "contributions": {"alcohol": 1}, "flavour": "dry and grassy",
            "desc": "a pale bottle of dry vermouth", "keywords": ("dry", "vermouth")},
    "maraschino": {"name": "bottle of maraschino liqueur", "role": "maraschino",
            "contributions": {"alcohol": 1}, "flavour": "nutty cherry",
            "desc": "a square bottle of clear maraschino liqueur", "keywords": ("maraschino", "cherry")},
    "herbal_liqueur": {"name": "bottle of green herbal liqueur", "role": "herbal_liqueur",
            "contributions": {"alcohol": 1}, "flavour": "green, alpine, and herbal",
            "desc": "a heavy bottle of green herbal liqueur, faintly medicinal", "keywords": ("herbal", "green", "chartreuse")},
    "orange_liqueur": {"name": "bottle of orange liqueur", "role": "orange_liqueur",
            "contributions": {"alcohol": 1}, "flavour": "sweet orange peel",
            "desc": "a clear bottle of orange liqueur", "keywords": ("orange", "triple", "sec", "curacao")},
    # ---- Non-alcoholic (flavour / structure only) ----------------------
    "lime": {"name": "lime", "role": "citrus", "contributions": {},
            "flavour": "sharp, sour citrus", "desc": "a precious Earth-import lime", "keywords": ("lime",)},
    "lemon": {"name": "lemon", "role": "citrus", "contributions": {},
            "flavour": "bright, sour citrus", "desc": "a precious Earth-import lemon", "keywords": ("lemon",)},
    "sugar_syrup": {"name": "flask of sugar syrup", "role": "sweetener", "contributions": {},
            "flavour": "plain sweetness", "desc": "a sticky flask of sugar syrup", "keywords": ("sugar", "syrup", "simple")},
    "bitters": {"name": "dasher of aromatic bitters", "role": "bitters", "contributions": {},
            "flavour": "spiced, concentrated bitterness", "desc": "a small dasher bottle of aromatic bitters", "keywords": ("bitters", "aromatic", "dasher")},
    # ---- More spirits --------------------------------------------------
    "brandy": {"name": "bottle of brandy", "role": ROLE_SPIRIT, "spirit": "brandy",
            "contributions": {"alcohol": 2}, "flavour": "raisined and warm",
            "desc": "a dusty Earth-import bottle of brandy", "keywords": ("brandy", "cognac")},
    # ---- More liqueurs (alcohol 1) -------------------------------------
    "coffee_liqueur": {"name": "bottle of coffee liqueur", "role": "coffee_liqueur",
            "contributions": {"alcohol": 1}, "flavour": "dark roasted coffee and sugar",
            "desc": "a sticky bottle of coffee liqueur", "keywords": ("coffee", "liqueur")},
    "amaretto": {"name": "bottle of amaretto", "role": "amaretto",
            "contributions": {"alcohol": 1}, "flavour": "sweet toasted almond",
            "desc": "a bottle of amber amaretto", "keywords": ("amaretto", "almond")},
    "elderflower": {"name": "bottle of elderflower liqueur", "role": "elderflower",
            "contributions": {"alcohol": 1}, "flavour": "floral elderflower",
            "desc": "a pale bottle of elderflower liqueur", "keywords": ("elderflower",)},
    "cassis": {"name": "bottle of cassis", "role": "cassis",
            "contributions": {"alcohol": 1}, "flavour": "dark blackcurrant",
            "desc": "a deep purple bottle of crème de cassis", "keywords": ("cassis", "blackcurrant")},
    # ---- Wine / sparkling / fortified (alcohol 1) ----------------------
    "sparkling_wine": {"name": "bottle of sparkling wine", "role": "sparkling_wine",
            "contributions": {"alcohol": 1}, "flavour": "dry, bright effervescence",
            "desc": "a foil-necked Earth-import bottle of sparkling wine", "keywords": ("sparkling", "champagne", "prosecco", "wine")},
    "sherry": {"name": "bottle of dry sherry", "role": "sherry",
            "contributions": {"alcohol": 1}, "flavour": "nutty, saline, oxidised",
            "desc": "a slim bottle of dry sherry", "keywords": ("sherry",)},
    # ---- Mixers (non-alcoholic) ----------------------------------------
    "soda": {"name": "siphon of soda water", "role": "soda", "contributions": {},
            "flavour": "clean fizz", "desc": "a battered soda siphon", "keywords": ("soda", "seltzer")},
    "tonic": {"name": "bottle of tonic water", "role": "tonic", "contributions": {},
            "flavour": "bittersweet quinine fizz", "desc": "a bottle of tonic water", "keywords": ("tonic",)},
    "ginger_beer": {"name": "bottle of ginger beer", "role": "ginger_beer", "contributions": {},
            "flavour": "spicy ginger bite", "desc": "a cloudy bottle of ginger beer", "keywords": ("ginger",)},
    "cola": {"name": "bottle of cola", "role": "cola", "contributions": {},
            "flavour": "sweet caramel fizz", "desc": "a scuffed bottle of flat-looking cola", "keywords": ("cola", "coke")},
    # ---- Juices --------------------------------------------------------
    "orange_juice": {"name": "jug of orange juice", "role": "orange_juice", "contributions": {},
            "flavour": "sweet-tart orange", "desc": "a jug of cloudy orange juice", "keywords": ("orange", "juice", "oj")},
    "cranberry": {"name": "carton of cranberry juice", "role": "cranberry", "contributions": {},
            "flavour": "tart cranberry", "desc": "a carton of deep red cranberry juice", "keywords": ("cranberry",)},
    "pineapple": {"name": "tin of pineapple juice", "role": "pineapple", "contributions": {},
            "flavour": "sweet tropical pineapple", "desc": "a dented tin of pineapple juice", "keywords": ("pineapple",)},
    "grapefruit": {"name": "jug of grapefruit juice", "role": "grapefruit", "contributions": {},
            "flavour": "bittersweet grapefruit", "desc": "a jug of pink grapefruit juice", "keywords": ("grapefruit",)},
    # ---- Dairy / protein / coffee --------------------------------------
    "cream": {"name": "carton of cream", "role": "cream", "contributions": {},
            "flavour": "rich, heavy cream", "desc": "a carton of thick cream", "keywords": ("cream",)},
    "coconut": {"name": "tin of coconut cream", "role": "coconut", "contributions": {},
            "flavour": "sweet coconut", "desc": "a tin of thick coconut cream", "keywords": ("coconut",)},
    "egg_white": {"name": "egg white", "role": "egg_white", "contributions": {},
            "flavour": "silky foam", "desc": "a single egg white in a cup", "keywords": ("egg",)},
    "coffee": {"name": "shot of espresso", "role": "coffee", "contributions": {},
            "flavour": "bitter, concentrated coffee", "desc": "a hot shot of pulled espresso", "keywords": ("espresso", "coffee", "shot")},
    # ---- Sweeteners / syrups -------------------------------------------
    "grenadine": {"name": "flask of grenadine", "role": "grenadine", "contributions": {},
            "flavour": "sweet pomegranate red", "desc": "a flask of deep red grenadine", "keywords": ("grenadine", "pomegranate")},
    "orgeat": {"name": "flask of orgeat", "role": "orgeat", "contributions": {},
            "flavour": "sweet almond-orange", "desc": "a flask of milky orgeat syrup", "keywords": ("orgeat",)},
    "honey_syrup": {"name": "flask of honey syrup", "role": "honey", "contributions": {},
            "flavour": "floral honey", "desc": "a sticky flask of honey syrup", "keywords": ("honey",)},
    "mint": {"name": "sprig of mint", "role": "mint", "contributions": {},
            "flavour": "cool fresh mint", "desc": "a bruised sprig of hydroponic mint", "keywords": ("mint",)},
    # ---- Garnishes (flavour / presence only — never role-defining) -----
    "olive": {"name": "olive", "role": "garnish", "contributions": {},
            "flavour": "briny olive", "desc": "a single brined olive on a pick", "keywords": ("olive",)},
    "cherry": {"name": "cocktail cherry", "role": "garnish", "contributions": {},
            "flavour": "syrupy cherry", "desc": "a lurid red cocktail cherry", "keywords": ("cherry",)},
    "salt": {"name": "pinch of salt", "role": "garnish", "contributions": {},
            "flavour": "a saline rim", "desc": "a small dish of coarse salt", "keywords": ("salt",)},
}


def make_ingredient(catalog_key, *, location=None):
    """Spawn a catalog ingredient as a real item (effects + cocktail identity)."""
    from world.search import strip_leading_article

    proto = INGREDIENT_CATALOG[catalog_key]
    name = strip_leading_article((proto["name"] or "").strip())
    ing = create_object(DRINK_TYPECLASS, key=name, location=location)
    ing.db.desc = proto.get("desc", name)
    ing.db.is_ingredient = True
    ing.db.contributions = dict(proto.get("contributions", {}))
    ing.db.flavour = proto.get("flavour", "")
    ing.db.consumed_per_use = int(proto.get("consumed_per_use", 1) or 1)
    ing.db.role = proto.get("role")            # cocktail component role
    ing.db.spirit = proto.get("spirit")        # spirit type (role == spirit)
    aliases = _drink_aliases(name, proto.get("keywords", ()))
    if aliases:
        ing.aliases.add(aliases)
    return ing


def compose_flavour(ingredients):
    """Join the loaded ingredients' flavour notes into one description.

    Order-preserving and de-duplicated, so two pours of gin read once. Used as
    the free-mix drink's taste until a save/brand authors its own prose.
    """
    notes = []
    for ing in ingredients:
        f = getattr(ing.db, "flavour", "") or ""
        if f and f not in notes:
            notes.append(f)
    return "; ".join(notes)


# ---------------------------------------------------------------------------
# Classic cocktails (the hidden recognition layer). A template names a set of
# required component roles; loose matching (decision: roles present, ratios and
# extra garnishes ignored) recognizes the classic and, on a swapped spirit, the
# spin ("Mezcal Negroni"). Cocktail names are generic/public-domain; nothing is
# matched on brand names. `spin` formats non-canonical spirits; `spirit_names`
# overrides specific spirits where the family name differs (rum sour = Daiquiri).
# ---------------------------------------------------------------------------
#: A template names a skeleton of required component roles (the spirit role is
#: implied for spirit-keyed templates and tracked separately for naming). Where
#: several classics share a skeleton, one template carries the family with
#: `spirit_names` overrides (rum sour = Daiquiri, whiskey = Whiskey Sour; gin
#: Negroni vs whiskey Boulevardier). `spirit_keyed: False` = a spirit-less
#: classic (Mimosa, Spritz). Order matters only for equal-specificity ties.
COCKTAILS = [
    # --- spirit-keyed, most specific first ---
    {"name": "Mojito", "canonical": "rum", "spin": "{spirit} Mojito",
     "roles": {"citrus", "sweetener", "mint", "soda"}},
    {"name": "Cosmopolitan", "canonical": "vodka", "spin": "{spirit} Cosmopolitan",
     "roles": {"orange_liqueur", "cranberry", "citrus"}},
    {"name": "Last Word", "canonical": "gin", "spin": "{spirit} Last Word",
     "roles": {"herbal_liqueur", "maraschino", "citrus"}},
    {"name": "Mai Tai", "canonical": "rum", "spin": "{spirit} Mai Tai",
     "roles": {"orange_liqueur", "orgeat", "citrus"}},
    {"name": "French 75", "canonical": "gin", "spin": "{spirit} 75",
     "roles": {"citrus", "sweetener", "sparkling_wine"}},
    {"name": "Tom Collins", "canonical": "gin", "spin": "{spirit} Collins",
     "roles": {"citrus", "sweetener", "soda"}},
    {"name": "Margarita", "canonical": "tequila", "spin": "{spirit} Margarita",
     "spirit_names": {"brandy": "Sidecar"},
     "roles": {"orange_liqueur", "citrus"}},
    {"name": "Negroni", "canonical": "gin", "spin": "{spirit} Negroni",
     "spirit_names": {"whiskey": "Boulevardier"},
     "roles": {"bitter_aperitivo", "sweet_vermouth"}},
    {"name": "Manhattan", "canonical": "whiskey", "spin": "{spirit} Manhattan",
     "roles": {"sweet_vermouth", "bitters"}},
    {"name": "Old Fashioned", "canonical": "whiskey", "spin": "{spirit} Old Fashioned",
     "roles": {"sweetener", "bitters"}},
    {"name": "Espresso Martini", "canonical": "vodka", "spin": "{spirit} Espresso Martini",
     "roles": {"coffee_liqueur", "coffee"}},
    {"name": "White Russian", "canonical": "vodka", "spin": "{spirit} White Russian",
     "roles": {"coffee_liqueur", "cream"}},
    {"name": "Pina Colada", "canonical": "rum", "spin": "{spirit} Colada",
     "roles": {"pineapple", "coconut"}},
    {"name": "Moscow Mule", "canonical": "vodka", "spin": "{spirit} Mule",
     "roles": {"ginger_beer", "citrus"}},
    {"name": "Paloma", "canonical": "tequila", "spin": "{spirit} Paloma",
     "roles": {"grapefruit", "soda"}},
    {"name": "Daiquiri", "canonical": "rum", "spin": "{spirit} Sour",
     "spirit_names": {"whiskey": "Whiskey Sour", "gin": "Gin Sour",
                      "brandy": "Brandy Sour"},
     "roles": {"citrus", "sweetener"}},
    {"name": "Martini", "canonical": "gin", "spin": "{spirit} Martini",
     "roles": {"dry_vermouth"}},
    {"name": "Gin & Tonic", "canonical": "gin", "spin": "{spirit} & Tonic",
     "roles": {"tonic"}},
    # --- spirit-less ---
    {"name": "Mimosa", "spirit_keyed": False,
     "roles": {"sparkling_wine", "orange_juice"}},
    {"name": "Spritz", "spirit_keyed": False,
     "roles": {"bitter_aperitivo", "sparkling_wine"}},
]


#: Traditional preparation method per classic — a *suggestion* surfaced in the
#: mixing menu, never enforced (loose ethos). Keyed by the template base name.
COCKTAIL_METHOD = {
    "Mojito": "muddle", "Cosmopolitan": "shake", "Last Word": "shake",
    "Mai Tai": "shake", "French 75": "shake", "Tom Collins": "build",
    "Margarita": "shake", "Negroni": "stir", "Manhattan": "stir",
    "Old Fashioned": "stir", "Espresso Martini": "shake",
    "White Russian": "build", "Pina Colada": "blend", "Moscow Mule": "build",
    "Paloma": "build", "Daiquiri": "shake", "Martini": "stir",
    "Gin & Tonic": "build", "Mimosa": "build", "Spritz": "build",
}


def _spirit_display(spirit):
    """Title-case a spirit type for spin names ('mezcal' -> 'Mezcal')."""
    return " ".join(w.capitalize() for w in (spirit or "").split())


def name_cocktail(template, spirit):
    """Name a recognized cocktail for the spirit used (canonical or a spin)."""
    if not template.get("spirit_keyed", True):
        return template["name"]
    if spirit == template["canonical"]:
        return template["name"]
    overrides = template.get("spirit_names", {})
    if spirit in overrides:
        return overrides[spirit]
    spin = template.get("spin", "{spirit} {base}")
    return spin.format(spirit=_spirit_display(spirit), base=template["name"])


def _best_template(ingredients):
    """The most-specific matching cocktail template + the naming spirit.

    Loose match: a template fires when all its required roles are present (plus
    a spirit, for spirit-keyed templates); extra roles/garnishes are ignored.
    Most required components wins. Returns ``(template, spirit)`` or ``(None, None)``.
    """
    roles_present = set()
    spirit = None
    for ing in ingredients:
        role = getattr(ing.db, "role", None)
        if role:
            roles_present.add(role)
        if role == ROLE_SPIRIT and spirit is None:
            spirit = getattr(ing.db, "spirit", None)

    best = None
    best_score = -1
    for template in COCKTAILS:
        needs_spirit = template.get("spirit_keyed", True)
        if needs_spirit and spirit is None:
            continue
        if not template["roles"] <= roles_present:
            continue
        score = len(template["roles"]) + (1 if needs_spirit else 0)
        if score > best_score:
            best, best_score = template, score
    return (best, spirit) if best else (None, None)


def recognize_cocktail(ingredients):
    """Recognized classic / spin name for a mix, or ``None`` for a free-mix."""
    template, spirit = _best_template(ingredients)
    return name_cocktail(template, spirit) if template else None


_VESSEL_RE = re.compile(r"^\w+ of (.+)$")


def _ingredient_essence(ingredient):
    """An ingredient's bare substance name, minus its container — a spirit's
    type if it has one, else the name with any '<vessel> of ' prefix stripped
    ('bottle of gin' -> 'gin', 'sprig of mint' -> 'mint')."""
    spirit = getattr(ingredient.db, "spirit", None)
    if spirit:
        return spirit
    name = ingredient.key or ""
    m = _VESSEL_RE.match(name)
    return m.group(1) if m else name


def default_drink_name(ingredients, cocktail):
    """The drink's default name: the recognized classic, else 'glass of <X>' for
    a single-ingredient pour (a neat gin is just a glass of gin), else 'house
    mix' for an unrecognized blend."""
    if cocktail:
        return cocktail
    if ingredients and len({i.key for i in ingredients}) == 1:
        return f"glass of {_ingredient_essence(ingredients[0])}"
    return "house mix"


def project_mix(ingredients):
    """Project what the loaded ingredients would make, without making it.

    Returns ``{"effects", "flavour", "capped", "cocktail", "method"}``: the
    additive substance sum (each clamped to MIX_EFFECT_CAP), the composed
    flavour, any substances the cap trimmed (for UI feedback), the recognized
    classic / spin name (or ``None``), and the suggested preparation method
    (or ``None`` for a free-mix).
    """
    raw = mix_effects(ingredients)
    effects = {sid: min(d, MIX_EFFECT_CAP) for sid, d in raw.items()}
    capped = {sid: d for sid, d in raw.items() if d > MIX_EFFECT_CAP}
    template, spirit = _best_template(ingredients)
    cocktail = name_cocktail(template, spirit) if template else None
    return {
        "effects": effects,
        "flavour": compose_flavour(ingredients),
        "capped": capped,
        "cocktail": cocktail,
        "name": default_drink_name(ingredients, cocktail),
        "method": COCKTAIL_METHOD.get(template["name"]) if template else None,
    }


#: Structural non-alcoholic basics every bar keeps on hand, so even a scuzzy
#: bar can build sours/highballs from its own spirits — the seed of riffs (§5).
BASE_BAR_PANTRY = ("lime", "lemon", "sugar_syrup", "bitters", "soda")


def derive_bar_stock(menu):
    """The bottomless ingredient stock for a bar (decision: auto from the menu).

    The base pantry plus every ingredient the bar's menu drinks call for, so a
    bartender can always re-make and riff on what's on offer. Returns catalog
    keys in catalog order (spirits, modifiers, structure…).
    """
    keys = set(BASE_BAR_PANTRY)
    for recipe in (menu or []):
        for k in recipe.get("ingredients", ()):
            keys.add(k)
    return [k for k in INGREDIENT_CATALOG if k in keys]


def match_snack(text, snacks):
    """Find the first snack whose keywords appear in `text`. Returns dict/None."""
    if not text or not snacks:
        return None
    low = text.lower()
    for snack in snacks:
        for kw in snack.get("order_keywords", (snack.get("name", ""),)):
            if kw and kw.lower() in low:
                return snack
    return None


def find_room_bar_snack(location, text):
    """Resolve an ``eat <snack> [from <bar>]`` request against bars in a room.

    Strips a trailing ``from <bar>`` disambiguator, then matches the remaining
    words against each bar's ``db.snacks``. Bars are duck-typed (an object with
    an ``is_bartender`` method) to avoid importing the typeclass here. Returns
    ``(bar, snack_dict)`` or ``None``.
    """
    if not location or not text:
        return None
    snack_text = re.split(r"\bfrom\b", text.strip(), maxsplit=1)[0].strip()
    if not snack_text:
        return None
    for obj in getattr(location, "contents", ()):
        if not callable(getattr(obj, "is_bartender", None)):
            continue
        snack = match_snack(snack_text, obj.db.snacks or [])
        if snack:
            return obj, snack
    return None


# ---------------------------------------------------------------------------
# A starter menu for the Hub & Howl — scuzzy colony drinks. Original content.
# Effects use real substance ids (see world/substances/registry.py): `alcohol`
# (sedation cap 4), `opium` (strong). Flavour-only drinks carry no effects.
# ---------------------------------------------------------------------------
HUB_AND_HOWL_MENU = [
    {
        "name": "mug of rotgut",
        "order_keywords": ("rotgut", "grain", "spirit", "cheap"),
        "ingredients": ("grain_mash",),
        "price": 0,
        "sips": 3,
        "effects": {"alcohol": 1},
        "desc": "a dented tin mug of cloudy grain spirit, the colony's cheapest way to lose a shift",
        "taste": "It scours the throat like coolant — paint-thinner heat and a sour, metallic finish.",
        "craft": "reaches under the slab for an unlabelled jug and sloshes out a measure of cloudy grain spirit",
    },
    {
        "name": "glass of reactor wash",
        "order_keywords": ("reactor", "wash", "strong", "stiff"),
        "ingredients": ("reactor_cut",),
        "price": 0,
        "sips": 3,
        "effects": {"alcohol": 2},
        "desc": "a smudged glass of something amber and oily that catches the light wrong",
        "taste": "It hits like a dropped tool — hot, chemical, and gone numb before you swallow.",
        "craft": "free-pours two fingers of something amber and oily that catches the light wrong",
    },
    {
        "name": "cup of channel fog",
        "order_keywords": ("fog", "channel", "milky", "smooth"),
        "ingredients": ("reactor_cut", "poppy_tincture", "channel_cordial"),
        "price": 0,
        "sips": 4,
        "effects": {"alcohol": 1, "opium": 1},
        "desc": "a chipped ceramic cup of a milky, grey-green liquor that smells faintly of brine and poppy",
        "taste": "Smooth and cold going down, with a slow warmth that closes over you like the channel fog it's named for.",
        "craft": "measures out a milky, grey-green liquor with the care of someone who knows what's in it",
    },
    {
        "name": "mug of black recyc",
        "order_keywords": ("recyc", "black", "coffee", "caf", "sober"),
        "ingredients": ("caf",),
        "price": 0,
        "sips": 4,
        "effects": {},
        "desc": "a scalding mug of reclaimed caf, black as the inside of a vent and twice as bitter",
        "taste": "Bitter, scalding, and faintly of the recycler — but it's hot, and it's not alcohol.",
        "craft": "draws a scalding measure straight from the battered caf urn",
    },
]
