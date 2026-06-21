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

import random
from time import monotonic

from evennia import CmdSet
from evennia.commands.command import Command
from evennia.utils import delay

from typeclasses.items import Item
from typeclasses.characters import Character
from world.grammar import capitalize_first, with_article
from world.shop.utils import format_currency
from world.bar import (
    DEFAULT_BAR_SNACKS,
    make_drink,
    make_drink_from_recipe,
    match_recipe,
    mix_effects,
)

#: Price colour on the menu — the same burnt orange (XTERM-256 |520) the
#: operate menu uses for parenthetical/secondary info, for cross-UI consistency.
MENU_PRICE_COLOR = "|520"


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
        # Pad names to a common width so the price column lines up. Labels are
        # plain (no colour codes), so visible length == len().
        labels = [capitalize_first(r["name"]) for r in menu]
        width = max(len(label) for label in labels)
        lines = [f"|w{name} — menu|n"]
        for label, r in zip(labels, menu):
            price = format_currency(r.get("price", 0))
            lines.append(
                f"  {label.ljust(width)}   {MENU_PRICE_COLOR}({price})|n"
            )
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
            name="mixed drink",
            desc=f"a freshly-mixed drink, thrown together from {names}",
            effects=effects,
            sips=3,
            taste="A rough, improvised mix — it does the job.",
            location=bar,   # onto the bar surface
        )
        for i in ingredients:
            i.delete()
        caller.location.msg_contents(
            f"{caller.key} mixes {names} into {with_article(drink.key)} "
            f"on {bar.key}."
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
        self.db.snacks = list(DEFAULT_BAR_SNACKS)  # free bottomless nibbles (§10)
        self.db.register = 0
        self.db.owner = None
        self.db.staff = []
        self.db.integrate = True          # part of the room, not a loose object
        self.locks.add("get:false()")     # stuck — can't be pocketed
        self.cmdset.add(BarCmdSet, persistent=True)
        # @integrate weaves the counter into the room description via
        # db.sensory_contributions (builders author a per-bar 'visual' line, e.g.
        # `@roomsense`-style data). Until they do, fall back to a plain generic
        # line rather than the bare "<key> is here" the room would otherwise use.
        # Highlight the targetable noun in cyan (house style for things you can
        # interact with), matching the typical 'bar' key word so `look bar`
        # reads as clickable.
        self.db.integration_fallback = (
            "A salvaged |cbar|n runs along one side of the room, its surface "
            "scarred by years of set-down glasses."
        )

    @staticmethod
    def _is_staff(char):
        """True if `char` is game staff (Builder permission or higher).

        Uses the ``perm()`` lock function so the check honours the permission
        hierarchy and the controlling account's permissions, matching how the
        rest of the codebase detects staff (see :mod:`world.emote`).
        """
        try:
            return bool(char.locks.check_lockstring(char, "perm(Builder)"))
        except Exception:
            return False

    def is_bartender(self, char):
        """True if `char` may work and manage this bar.

        Game staff (Builder+) can always work and manage any bar — they keep the
        place running regardless of who owns it. Otherwise: the owner, anyone on
        the staff list, or — while no ownership is configured (v1) — anyone
        present.
        """
        if self._is_staff(char):
            return True
        owner = self.db.owner
        staff = self.db.staff or []
        if owner is None and not staff:
            return True
        return char is owner or char in staff

    def get_display_things(self, looker, **kwargs):
        # The bar's contents (drinks, loaded ingredients) are shown by
        # return_appearance under "On the bar:". Suppress the default
        # "You see:" listing so they aren't rendered twice.
        return ""

    def return_appearance(self, looker, **kwargs):
        # Looking at the bar shows its own description (db.desc) — deliberately
        # distinct from the @integrate line woven into the room — plus what's
        # resting on its surface, stacked by count ("a glass of reactor wash,
        # two mugs of rotgut") via the standard get_numbered_name. No chrome.
        from collections import defaultdict

        from evennia.utils.utils import iter_to_str

        base = super().return_appearance(looker, **kwargs)
        groups = defaultdict(list)
        for o in self.contents:
            if o.access(looker, "view"):
                groups[o.get_display_name(looker)].append(o)
        if groups:
            parts = []
            for objs in groups.values():
                count = len(objs)
                singular, plural = objs[0].get_numbered_name(count, looker)
                parts.append(singular if count == 1 else plural)
            base += f"\n\nOn the bar: {iter_to_str(parts)}."
        # Free bottomless snacks (§10) — pure ambiance, advertised so patrons
        # know they can pick at them (`eat <snack> from <bar>`).
        snacks = self.db.snacks or []
        if snacks:
            names = iter_to_str([s["name"] for s in snacks])
            base += f"\n\nFree to pick at: {names}."
        return base


# ---------------------------------------------------------------------------
# The bartender NPC
# ---------------------------------------------------------------------------
#: Substrings that read as thanks/acknowledgement in something said near the
#: bartender. Matched case-insensitively against the spoken content; 'thank'
#: covers thanks/thank you/thank ya, 'obliged' covers much obliged, etc.
GRATITUDE_TRIGGERS = (
    "thank", "cheers", "obliged", "appreciate", "good look", "nice one",
    "ta for", "much love",
)

#: Non-verbal acknowledgements — Sully's taciturn, so he answers with a gesture
#: rather than words. Phrased as emote actions (the identity system prepends his
#: per-observer name).
ACK_EMOTES = (
    "tips his chin a fraction, not looking up from the taps.",
    "raises two fingers off the slab in a flat, unhurried salute.",
    "grunts once, low, and keeps wiping down a glass.",
    "gives a single slow nod, the kind that's already moved on to the next thing.",
    "knocks two knuckles against the slab and lets that be the answer.",
)

#: Minimum seconds between acknowledgements, so a chatty room doesn't spam them.
ACK_COOLDOWN = 6.0


class Bartender(Character):
    """An NPC that takes drink orders by being spoken to (the `to` command)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_bartender_npc = True
        # Identity safety-net: a Character with no height/build composes no
        # sdesc and falls back to its *key* — which would leak the NPC's real
        # name ("Sully") to every onlooker instead of "a wiry man". Seed a
        # baseline presentation so the NPC always renders through the identity
        # system; builders override per-NPC (height/build/sdesc_keyword/sex).
        if not self.height:
            self.height = "average"
        if not self.build:
            self.build = "average"
        if not self.sdesc_keyword:
            self.sdesc_keyword = "bartender"

    def _find_bar(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, BarCounter):
                return obj
        return None

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """React to speech nearby, via the shared speech backbone.

        Every verb that carries words — ``say``, ``to``, or a pose with an
        embedded quote — delivers the same structured payload (``speech`` =
        the words, ``addressed`` = whether this bartender was the one spoken to),
        and only to listeners who can hear. So a single check handles all three:

          - **Gratitude** (thanks/cheers/much obliged...) from any heard speech —
            answered with a small non-verbal acknowledgement. Checked first so
            "thanks for the rotgut" reads as a thank-you, not a re-order.
          - **A directed order** — speech that was *addressed* to this bartender
            (``to <bartender> ...`` or ``.slide up to <bartender>, "..."``) is
            matched against the menu and made.
        """
        speech = kwargs.get("speech")
        speaker = from_obj
        if not speech or speaker is None or speaker is self:
            return True

        if self._is_gratitude(speech):
            self._acknowledge()
            return True

        if kwargs.get("addressed"):
            delay(1.5, self._fulfil_order, speech, speaker)
        return True

    @staticmethod
    def _is_gratitude(content):
        low = (content or "").lower()
        return any(trigger in low for trigger in GRATITUDE_TRIGGERS)

    def _acknowledge(self):
        """A throttled, non-verbal nod to thanks."""
        now = monotonic()
        last = self.ndb.last_ack or 0
        if now - last < ACK_COOLDOWN:
            return
        self.ndb.last_ack = now
        delay(1.0, self.execute_cmd, f"emote {random.choice(ACK_EMOTES)}")

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
        # The whole transaction is one wordless gesture — make it, set it down,
        # and (when there's a tab) take the cash. Routed through `emote` so the
        # bartender renders by per-observer identity (a stranger sees "a lean
        # man", not "Sully"), and no price is spoken: the swept payment says it.
        # A free drink just gets slid over — no phantom payment.
        craft = recipe.get("craft", "fixes the drink")
        where = bar.key if bar else "the bar"
        closer = (
            "sweeps the payment off the slab with a practiced hand"
            if price else "slides it over"
        )
        self.execute_cmd(
            f"emote {craft}, sets {with_article(drink.key)} on {where}, "
            f"and {closer}."
        )
