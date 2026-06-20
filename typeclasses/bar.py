"""
Bars (BARS_AND_RECIPES_SPEC) — the crafting station and its bartender.

``BarCounter`` is the interactive counter object: a container that holds loaded
ingredients and served drinks, carries the menu/register/ownership, and exposes
the `menu` / `use` verbs. ``Bartender`` is an NPC that responds to a patron
talking to it (the `to` command's structured directed speech) by making a drink
from its menu, serving it on the bar, and charging on order.

v1 is intentionally lenient where the spec defers detail (ownership gating,
recipe-saving UX) so the loop is testable; those are later slices.
"""

from evennia import CmdSet
from evennia.commands.command import Command
from evennia.utils import delay

from typeclasses.objects import Object
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
    Read the bar's menu.

    Usage:
        menu
    """

    key = "menu"
    aliases = ["read menu"]
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        bar = self.obj
        menu = bar.db.menu or []
        if not menu:
            self.caller.msg(f"{bar.get_display_name(self.caller)} has nothing on offer.")
            return
        lines = [f"|w{bar.get_display_name(self.caller)} — menu|n"]
        for r in menu:
            price = r.get("price", 0)
            lines.append(f"  {r['name']}  |y({price})|n")
        self.caller.msg("\n".join(lines))


class CmdBarUse(Command):
    """
    Work the bar: mix whatever ingredients are loaded into it.

    Usage:
        use <bar>

    Load ingredients first (``put <ingredient> in <bar>``), then ``use`` the
    bar to mix them into a drink. The drink lands on the bar.
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
        ingredients = [
            o for o in bar.contents
            if getattr(o.db, "is_ingredient", False)
        ]
        if not ingredients:
            caller.msg(
                f"Nothing's loaded to mix. Put ingredients in "
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
            location=bar,
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
# The bar counter
# ---------------------------------------------------------------------------
class BarCounter(Object):
    """An interactive bar counter — the first crafting station."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.menu = []
        self.db.register = 0
        self.db.owner = None
        self.db.staff = []
        self.locks.add("get:false()")  # the bar itself isn't pocketable
        self.cmdset.add(BarCmdSet, persistent=True)

    def is_bartender(self, char):
        """True if `char` may work this bar (owner, staff, or — v1 — anyone
        if no ownership is set yet)."""
        owner = self.db.owner
        staff = self.db.staff or []
        if owner is None and not staff:
            return True  # lenient until ownership is configured
        return char is owner or char in staff

    def return_appearance(self, looker, **kwargs):
        base = super().return_appearance(looker, **kwargs)
        guide = (
            "\n\n|wFor patrons|n\n"
            "  |cmenu|n                 — read what's on offer\n"
            "  |corder ... |n / |cto <bartender> ...|n — ask the bartender for a drink\n"
            "  |cget <drink> from " + self.key + "|n — take a drink served to you\n"
            "  |cdrink <drink>|n        — sip it\n"
            "\n|wFor bartenders|n\n"
            "  |cput <ingredient> in " + self.key + "|n — load ingredients\n"
            "  |cuse " + self.key + "|n            — mix the loaded ingredients"
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
            # A small beat, then fulfil — feels natural and avoids reentrancy.
            delay(1.5, self._fulfil_order, order, speaker)
        return True

    def _fulfil_order(self, order_text, patron):
        if not self.location:
            return
        if getattr(patron, "location", None) is not self.location:
            return  # patron wandered off
        bar = self._find_bar()
        menu = (bar.db.menu if bar else None) or self.db.menu or []
        recipe = match_recipe(order_text, menu)
        if not recipe:
            self.location.msg_contents(
                f'{self.key} shakes their head. "Don\'t serve that here."'
            )
            return
        price = int(recipe.get("price", 0) or 0)
        have = int(getattr(patron, "tokens", 0) or 0)
        if price and have < price:
            self.location.msg_contents(
                f'{self.key} looks {patron.key} over. '
                f'"That\'s {price}. Come back when you\'ve got it."'
            )
            return
        loc = bar if bar else self.location
        drink = make_drink_from_recipe(recipe, location=loc)
        if price:
            patron.tokens = have - price
            if bar:
                bar.db.register = int(bar.db.register or 0) + price
        craft = recipe.get("craft", "fixes the drink")
        where = bar.key if bar else "the bar"
        self.location.msg_contents(
            f"{self.key} {craft}, then sets {drink.key} on {where}."
        )
        if price:
            patron.msg(f"|y(That's {price} tokens.)|n")
