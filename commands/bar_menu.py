"""
The `use <bar>` mixing menu (BARS_AND_RECIPES_SPEC §4/§5).

An EvMenu in the style of medical ``operate`` — its own command, the same
burnt-orange idiom — where a bartender sees the loaded ingredients, the
projected effect profile, the composed flavour, and the recognized classic
(or spin), then:

  - **Pours** a one-off (named by recognition, or a free-mix),
  - **Saves/brands** the mix as a named recipe on the bar's menu — free-text
    naming, recognized name offered as the default ("Negroni" → "Kyoto
    Negroni"); the recognized base is kept as metadata,
  - **Makes a known recipe** straight from the bar's menu.

State rides ``caller.ndb._bar_menu`` and is cleared on exit.
"""

from collections import defaultdict

from evennia.commands.command import Command
from evennia.utils.evmenu import EvMenu

from world.grammar import with_article
from world.bar import (
    INGREDIENT_CATALOG,
    derive_bar_stock,
    make_drink,
    make_drink_from_recipe,
    make_ingredient,
    project_mix,
)

MUTED = "|520"   # burnt orange — matches the operate menu's secondary text
HEAD = "|w"


# ---------------------------------------------------------------------------
# Menu plumbing
# ---------------------------------------------------------------------------
class _BarMenu(EvMenu):
    """Suppress EvMenu's default decorations; nodes render their own layout."""

    def nodetext_formatter(self, nodetext):
        return nodetext

    def options_formatter(self, optionlist):
        return ""

    def node_formatter(self, nodetext, optionstext):
        return nodetext


def _menu_exit(caller, menu):
    for attr in ("_bar_menu", "_bar_save_name"):
        if hasattr(caller.ndb, attr):
            delattr(caller.ndb, attr)


def start_bar_menu(caller, bar):
    """Open the mixing menu for ``bar``."""
    caller.ndb._bar_menu = bar
    _BarMenu(
        caller,
        {
            "node_top": node_top,
            "node_add_stock": node_add_stock,
            "node_method": node_method,
            "node_save_name": node_save_name,
            "node_save_taste": node_save_taste,
            "node_pick_recipe": node_pick_recipe,
            "node_exit": node_exit,
        },
        startnode="node_top",
        cmd_on_exit=_menu_exit,
        auto_quit=True,
        auto_look=False,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _loaded(bar):
    return [o for o in bar.contents if getattr(o.db, "is_ingredient", False)]


def _bar_stock(bar):
    """The bottomless ingredient keys this bar carries — an explicit db.stock if
    a builder set one, else auto-derived from the menu + base pantry."""
    stock = bar.db.stock
    if stock:
        return [k for k in stock if k in INGREDIENT_CATALOG]
    return derive_bar_stock(bar.db.menu or [])


def _clear_load(caller, bar):
    n = 0
    for o in list(bar.contents):
        if getattr(o.db, "is_ingredient", False):
            o.delete()
            n += 1
    caller.msg(f"Swept {n} ingredient(s) off the bar." if n
               else "Nothing loaded to clear.")


def _effect_summary(effects):
    return ", ".join(f"{sid} {d}" for sid, d in effects.items()) or "none"


def _recipe_keywords(name):
    return tuple(w for w in name.lower().split() if len(w) > 2)


#: Preparation methods — flavour only (decision: no mechanical effect in v1).
#: Phrased without the drink name ("it") so the same craft narration works in
#: the menu pour AND the NPC serve emote.
METHOD_ORDER = ("build", "stir", "shake", "muddle", "blend")
METHOD_LABEL = {"build": "Build", "stir": "Stir", "shake": "Shake",
                "muddle": "Muddle", "blend": "Blend"}
METHOD_ADVERB = {"build": "built", "stir": "stirred", "shake": "shaken",
                 "muddle": "muddled", "blend": "blended"}
METHOD_CRAFT = {
    "build": "builds it in the glass",
    "stir": "stirs it down over ice, smooth and unhurried",
    "shake": "shakes it hard over ice and strains it out",
    "muddle": "muddles the base and churns it together",
    "blend": "blends it into a frozen slurry",
}


def _pour(caller, bar, *, name=None, method=None):
    """Make the loaded mix into a drink on the bar; consume the ingredients.

    ``method`` drives only the craft narration (no mechanical effect); defaults
    to the recognized classic's suggested method, else 'build'.
    """
    ings = _loaded(bar)
    if not ings:
        caller.msg("Nothing's loaded to mix.")
        return None
    proj = project_mix(ings)
    method = method or proj.get("method") or "build"
    drink_name = name or proj["name"]
    taste = proj["flavour"]
    desc = f"a freshly-mixed drink — {taste}" if taste else "a freshly-mixed drink"
    drink = make_drink(
        name=drink_name, desc=desc, effects=proj["effects"], sips=3,
        taste=taste, location=bar,
    )
    for i in ings:
        i.delete()
    caller.execute_cmd(
        f"emote {METHOD_CRAFT[method]}, and sets {with_article(drink.key)} "
        f"on {bar.key}."
    )
    return proj


def _save_recipe(bar, name, *, proj, taste=None, method=None):
    """Append a branded recipe (from the projection) to the bar's menu."""
    method = method or proj.get("method") or "build"
    recipe = {
        "name": name,
        "desc": (f"a house pour — {proj['flavour']}" if proj["flavour"]
                 else "a house pour"),
        "price": 0,
        "sips": 3,
        "effects": dict(proj["effects"]),
        "taste": taste or proj["flavour"],
        "base_cocktail": proj["cocktail"],
        "method": method,
        "order_keywords": _recipe_keywords(name),
        "craft": METHOD_CRAFT.get(method, METHOD_CRAFT["build"]),
    }
    menu = list(bar.db.menu or [])
    menu.append(recipe)
    bar.db.menu = menu
    return recipe


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def node_top(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    if bar is None:
        return "|rThis bar is gone.|n", None

    ings = _loaded(bar)
    lines = [f"{HEAD}{bar.key} — mixing|n", ""]
    if ings:
        groups = defaultdict(int)
        for i in ings:
            groups[i.key] += 1
        loaded = ", ".join(
            f"{n}× {k}" if n > 1 else k for k, n in groups.items()
        )
        proj = project_mix(ings)
        lines.append(f"  Loaded:   {loaded}")
        lines.append(f"  {MUTED}Effect:   {_effect_summary(proj['effects'])}|n")
        if proj["flavour"]:
            lines.append(f"  {MUTED}Flavour:  {proj['flavour']}|n")
        if proj["cocktail"]:
            adverb = METHOD_ADVERB.get(proj.get("method"))
            tail = f" {MUTED}({adverb})|n" if adverb else ""
            lines.append(f"  Reads as: {HEAD}{proj['cocktail']}|n{tail}")
        else:
            lines.append(f"  {MUTED}Reads as: {with_article(proj['name'])}|n")
    else:
        lines.append(
            f"  {MUTED}Nothing loaded. Put ingredients on the bar first "
            f"(put <thing> on {bar.key}).|n"
        )
    lines.append("")
    if _bar_stock(bar):
        lines.append(f"  {MUTED}[a]|n Add an ingredient from the bar stock")
    if ings:
        lines.append(f"  {MUTED}[1]|n Pour it")
        lines.append(f"  {MUTED}[2]|n Save as a recipe")
        lines.append(f"  {MUTED}[c]|n Clear the load")
    if bar.db.menu:
        lines.append(f"  {MUTED}[3]|n Make a known recipe")
    lines.append(f"  {MUTED}[x]|n Step away")

    return "\n".join(lines), ({"key": "_default", "goto": _process_top},)


def _process_top(caller, raw_string, **kwargs):
    choice = raw_string.strip().lower()
    bar = getattr(caller.ndb, "_bar_menu", None)
    if choice in ("x", "exit", "quit", "q", ""):
        return "node_exit" if choice else None
    if choice == "a":
        if _bar_stock(bar):
            return "node_add_stock"
        caller.msg("This bar carries no stock.")
        return None
    if choice == "c":
        _clear_load(caller, bar)
        return "node_top"
    if choice == "1":
        if _loaded(bar):
            return "node_method"
        return "node_top"
    if choice == "2":
        if not _loaded(bar):
            caller.msg("Nothing to save — load ingredients first.")
            return None
        return "node_save_name"
    if choice == "3":
        if bar and bar.db.menu:
            return "node_pick_recipe"
        caller.msg("Nothing on the menu yet.")
        return None
    caller.msg("|rPick an option, or x to step away.|n")
    return None


# ---- add from stock ------------------------------------------------------
def node_add_stock(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    stock = _bar_stock(bar) if bar else []
    lines = [f"{HEAD}Add from the bar stock|n",
             f"  {MUTED}(bottomless — pick as many as you like)|n", ""]
    for idx, key in enumerate(stock, 1):
        lines.append(f"  {MUTED}[{idx}]|n {INGREDIENT_CATALOG[key]['name']}")
    lines.append(f"  {MUTED}[x]|n Back")
    return "\n".join(lines), ({"key": "_default", "goto": _process_add_stock},)


def _process_add_stock(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    choice = raw_string.strip().lower()
    if choice in ("x", "back", ""):
        return "node_top"
    stock = _bar_stock(bar) if bar else []
    if choice.isdigit() and 1 <= int(choice) <= len(stock):
        ing = make_ingredient(stock[int(choice) - 1], location=bar)
        caller.msg(f"Added {ing.key} to the mix.")
        return "node_add_stock"   # stay, to add more
    caller.msg("|rPick a number, or x to go back.|n")
    return None


# ---- prep method ---------------------------------------------------------
def node_method(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    suggested = project_mix(_loaded(bar)).get("method") if bar else None
    lines = [f"{HEAD}How do you make it?|n", ""]
    for idx, m in enumerate(METHOD_ORDER, 1):
        tag = f"  {MUTED}(suggested)|n" if m == suggested else ""
        lines.append(f"  {MUTED}[{idx}]|n {METHOD_LABEL[m]}{tag}")
    lines.append(f"  {MUTED}[x]|n Back")
    return "\n".join(lines), ({"key": "_default", "goto": _process_method},)


def _process_method(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    choice = raw_string.strip().lower()
    if choice in ("x", "back", ""):
        return "node_top"
    if choice.isdigit() and 1 <= int(choice) <= len(METHOD_ORDER):
        _pour(caller, bar, method=METHOD_ORDER[int(choice) - 1])
        return "node_top"
    caller.msg("|rPick a number, or x to go back.|n")
    return None


# ---- save / brand --------------------------------------------------------
def node_save_name(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    proj = project_mix(_loaded(bar))
    default = proj["name"]
    text = (
        f"{HEAD}Name this pour.|n\n"
        f"  {MUTED}It reads as {default}. Press enter to keep that, or type "
        f"your own — e.g. Kyoto Negroni.|n"
    )
    return text, ({"key": "_default", "goto": _process_save_name},)


def _process_save_name(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    proj = project_mix(_loaded(bar))
    name = raw_string.strip() or proj["name"]
    caller.ndb._bar_save_name = name
    return "node_save_taste"


def node_save_taste(caller, raw_string, **kwargs):
    name = getattr(caller.ndb, "_bar_save_name", "house mix")
    text = (
        f"{HEAD}Describe how {name} tastes.|n\n"
        f"  {MUTED}Press enter to use the composed flavour, or write your own "
        f"one-line taste.|n"
    )
    return text, ({"key": "_default", "goto": _process_save_taste},)


def _process_save_taste(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    name = getattr(caller.ndb, "_bar_save_name", "house mix")
    taste = raw_string.strip() or None
    ings = _loaded(bar)
    if not ings:
        caller.msg("The mix is gone; nothing saved.")
        return "node_top"
    proj = project_mix(ings)
    method = proj.get("method") or "build"
    _save_recipe(bar, name, proj=proj, taste=taste, method=method)
    # Branding pours the first one, in the suggested method.
    _pour(caller, bar, name=name, method=method)
    base = f" ({proj['cocktail']})" if proj["cocktail"] else ""
    caller.msg(f"{HEAD}Saved {name}{base} to the menu.|n It's now orderable.")
    return "node_top"


# ---- make a known recipe -------------------------------------------------
def node_pick_recipe(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    menu = (bar.db.menu if bar else None) or []
    lines = [f"{HEAD}Make which recipe?|n", ""]
    for idx, r in enumerate(menu, 1):
        lines.append(f"  {MUTED}[{idx}]|n {r['name']}")
    lines.append(f"  {MUTED}[x]|n Back")
    return "\n".join(lines), ({"key": "_default", "goto": _process_pick},)


def _process_pick(caller, raw_string, **kwargs):
    bar = getattr(caller.ndb, "_bar_menu", None)
    choice = raw_string.strip().lower()
    if choice in ("x", "back", "q", ""):
        return "node_top"
    menu = (bar.db.menu if bar else None) or []
    if choice.isdigit() and 1 <= int(choice) <= len(menu):
        recipe = menu[int(choice) - 1]
        drink = make_drink_from_recipe(recipe, location=bar)
        caller.execute_cmd(
            f"emote {recipe.get('craft', 'builds the drink')}, and sets "
            f"{with_article(drink.key)} on {bar.key}."
        )
        return "node_top"
    caller.msg("|rPick a number, or q to go back.|n")
    return None


def node_exit(caller, raw_string, **kwargs):
    return f"{MUTED}You step back from the bar.|n", None


# ---------------------------------------------------------------------------
# Builder tool — spawn catalog ingredients (no supplier economy yet, §3)
# ---------------------------------------------------------------------------
class CmdSpawnIngredient(Command):
    """
    Spawn a bar ingredient from the catalog (builder testing tool).

    Usage:
        @ingredient <key>
        @ingredient            — list the catalog keys

    The ingredient lands in your inventory; ``put`` it on a bar, then
    ``use`` the bar to mix.
    """

    key = "@ingredient"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        from world.bar import INGREDIENT_CATALOG, make_ingredient

        key = self.args.strip().lower().replace(" ", "_").replace("-", "_")
        if not key or key not in INGREDIENT_CATALOG:
            self.caller.msg(
                "Usage: @ingredient <key>\n  "
                + ", ".join(sorted(INGREDIENT_CATALOG))
            )
            return
        ing = make_ingredient(key, location=self.caller)
        self.caller.msg(f"Spawned {ing.key} into your inventory.")
