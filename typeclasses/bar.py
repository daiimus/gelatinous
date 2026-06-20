"""
Bars (BARS_AND_RECIPES_SPEC) — the crafting station and its bartender.

``BarCounter`` is the interactive counter: an ``@integrate`` room fixture (folds
into the room description, not listed as a loose object, can't be picked up) that
holds served drinks on its surface, carries the menu/register/ownership, and
exposes the `read menu on <bar>` / `use <bar>` verbs. ``Bartender`` is an NPC that
responds to a patron talking to it (the `to` command's structured directed
speech) by making a drink from its menu, setting it on the bar, and taking
payment diegetically (it says the price; no system text).

v1 is intentionally lenient where the spec defers (ownership gating, recipe-save
UX) so the loop is testable; those are later slices.
"""

from evennia import CmdSet
from evennia.commands.command import Command
from evennia.utils import delay

from typeclasses.items import Item
from typeclasses.characters import Character
from world.bar import (
    make_drink,
    make_drink_from_recipe,
    match_recipe,
    mix_effects,
)


# ---------------------------------------------------------------------------
# Bar verbs (object command set, active when a bar is in the room)
# ---------------------------------------------------------------------------
class CmdBarMenu(Command):
    """
    Read a bar's menu.

    Usage:
        read menu on <bar>
        menu

    Defaults to the bar in the room, so a bare ``menu`` / ``read menu`` works.
    """

    key = "menu"
    aliases = ["read menu"]
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        bar = self.obj   # the bar this cmdset is attached to
        menu = bar.db.menu or []
        name = bar.get_display_name(self.caller)
        if not menu:
            self.caller.msg(f"{name} has nothing on offer.")
            return
        lines = [f"|w{name} — menu|n"]
        for r in menu:
            lines.append(f"  {r['name']}  |y({r.get('price', 0)})|n")
        self.caller.msg("\n".join(lines))


class CmdBarUse(Command):
    """
    Work the bar: mix whatever ingredients are loaded onto it.

    Usage:
        use <bar>

    Load ingredients first (``put <ingredient> on <bar>``), then ``use`` the bar
    to mix them into a drink. The drink lands on the bar.
    """

    key = "use"
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        bar = self.obj
        caller = self.caller
        if not bar.is_bartender(caller):
            caller.msg("You aren't working this bar.")
            return
        ingredients = [o for o in bar.contents if getattr(o.db, "is_ingredient", False)]
        if not ingredients:
            caller.msg(
                f"Nothing's loaded to mix. Put ingredients on "
                f"{bar.get_display_name(caller)} first."
            )
            return
        effects = mix_effects(ingredients)
        names = ", ".join(i.key for i in ingredients)
        drink = make_drink(
            name="a mixed drink",
            desc=f"a freshly-mixed drink, thrown together from {names}",
            effects=effects,
            sips=3,
            taste="A rough, improvised mix — it does the job.",
            location=bar,   # onto the bar surface
        )
        for i in ingredients:
            i.delete()
        caller.location.msg_contents(
            f"{caller.key} mixes {names} into {drink.key} on {bar.key}."
        )


class BarCmdSet(CmdSet):
    key = "bar_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdBarMenu())
        self.add(CmdBarUse())


# ---------------------------------------------------------------------------
# The bar counter — an @integrate room fixture with a surface
# ---------------------------------------------------------------------------
class BarCounter(Item):
    """An interactive bar counter — the first crafting station.

    An ``Item`` (so the @integrate room display recognises it) but a fixed
    fixture: ``db.integrate`` folds it into the room description rather than the
    loose-object list, and a ``get:false()`` lock keeps it from being picked up.
    Served drinks rest in its ``contents`` (the surface).
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.menu = []
        self.db.register = 0
        self.db.owner = None
        self.db.staff = []
        self.db.integrate = True          # part of the room, not a loose object
        self.locks.add("get:false()")     # stuck — can't be pocketed
        self.cmdset.add(BarCmdSet, persistent=True)

    def is_bartender(self, char):
        """True if `char` may work this bar (owner, staff, or — v1 — anyone if
        no ownership is configured yet)."""
        owner = self.db.owner
        staff = self.db.staff or []
        if owner is None and not staff:
            return True
        return char is owner or char in staff

    def return_appearance(self, looker, **kwargs):
        base = super().return_appearance(looker, **kwargs)
        # Show drinks resting on the surface.
        drinks = [o for o in self.contents if getattr(o.db, "is_drink", False)]
        if drinks:
            served = ", ".join(d.get_display_name(looker) for d in drinks)
            base += f"\n\nOn the bar: {served}."
        guide = (
            "\n\n|wFor patrons|n\n"
            "  |cread menu on " + self.key + "|n — see what's on offer\n"
            "  |cto <bartender> ...|n       — ask for a drink\n"
            "  |cget <drink> from " + self.key + "|n — take a drink off the bar\n"
            "  |cdrink <drink>|n            — sip it\n"
            "\n|wFor bartenders|n\n"
            "  |cput <ingredient> on " + self.key + "|n — load ingredients\n"
            "  |cuse " + self.key + "|n             — mix the loaded ingredients"
        )
        return base + guide


# ---------------------------------------------------------------------------
# The bartender NPC
# ---------------------------------------------------------------------------
class Bartender(Character):
    """An NPC that takes drink orders by being spoken to (the `to` command)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_bartender_npc = True

    def _find_bar(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, BarCounter):
                return obj
        return None

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """React to being addressed directly (the `to` command)."""
        order = kwargs.get("to_speech")
        speaker = kwargs.get("to_speaker") or from_obj
        if order and speaker is not None and speaker is not self:
            delay(1.5, self._fulfil_order, order, speaker)
        return True

    def _fulfil_order(self, order_text, patron):
        if not self.location or getattr(patron, "location", None) is not self.location:
            return
        bar = self._find_bar()
        menu = (bar.db.menu if bar else None) or self.db.menu or []
        recipe = match_recipe(order_text, menu)
        if not recipe:
            self.execute_cmd("say Don't serve that here.")
            return
        price = int(recipe.get("price", 0) or 0)
        have = int(getattr(patron, "tokens", 0) or 0)
        if price and have < price:
            self.execute_cmd(f"say That's {price}. Come back when you've got it.")
            return
        # Make it on the bar surface, take the cash as part of the gesture.
        loc = bar if bar else self.location
        drink = make_drink_from_recipe(recipe, location=loc)
        if price:
            patron.tokens = have - price
            if bar:
                bar.db.register = int(bar.db.register or 0) + price
        craft = recipe.get("craft", "fixes the drink")
        where = bar.key if bar else "the bar"
        self.location.msg_contents(
            f"{self.key} {craft}, sets {drink.key} on {where}, and sweeps the "
            f"payment off the slab with a practiced hand."
        )
        if price:
            self.execute_cmd(f"say {price}.")
