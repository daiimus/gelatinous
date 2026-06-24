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
from typeclasses.llm_npc import LLMNpcMixin
from world.grammar import capitalize_first, with_article
from world.shop.utils import format_currency
from world.bar import (
    DEFAULT_BAR_SNACKS,
    bar_stock,
    make_drink_from_recipe,
    match_recipe,
    resolve_drink,
    stockable_cocktails,
)

#: Price colour on the menu — the same burnt orange (XTERM-256 |520) the
#: operate menu uses for parenthetical/secondary info, for cross-UI consistency.
MENU_PRICE_COLOR = "|520"

#: Seats a bar comes stocked with (FURNITURE_AND_POSTURE).
BAR_STOOL_COUNT = 10


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
        # Open the operate-style mixing menu (load ingredients, see the
        # projected effects + recognized classic, pour / save-brand / make).
        from commands.bar_menu import start_bar_menu
        start_bar_menu(caller, bar)


class CmdBarPrepare(Command):
    """
    Prepare a known drink from the bar's menu, on the fly.

    Usage:
        prepare <drink>

    A shortcut past the mixing menu: matches the bar's menu and makes the drink
    straight onto the bar (no ingredients to load — like the bartender pouring a
    known recipe). For bartenders.

    Example:
        prepare recyc
    """

    key = "prepare"
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        import re
        bar = self.obj
        caller = self.caller
        if not bar.is_bartender(caller):
            caller.msg("You aren't working this bar.")
            return
        # Tolerate a trailing "on <bar>" — the command is already bound to a bar.
        query = re.split(r"\bon\b", (self.args or "").strip(), maxsplit=1)[0].strip()
        if not query:
            caller.msg("Prepare what? (try the menu to see what's on offer.)")
            return
        recipe, _offmenu = resolve_drink(query, bar)
        if not recipe:
            caller.msg(
                f"That's not on {bar.get_display_name(caller)}'s menu, and you "
                f"can't make it from what's in stock."
            )
            return
        drink = make_drink_from_recipe(recipe, location=bar)
        craft = recipe.get("craft", "builds the drink")
        caller.execute_cmd(
            f"emote {craft}, and sets {with_article(drink.key)} on {bar.key}."
        )


class CmdBarClear(Command):
    """
    Clean abandoned drinks and loose ingredients off the bar.

    Usage:
        clean <bar>
        wipe <bar>

    Wipes the bar surface down — served drinks nobody took and any ingredients
    left loaded. Keeps the counter tidy between rounds. For bartenders.

    (``clean`` rather than ``clear`` — ``clear`` is taken by the detonator.)
    """

    key = "clean"
    aliases = ["wipe"]
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        from world.identity_utils import msg_room_identity

        bar = self.obj
        caller = self.caller
        if not bar.is_bartender(caller):
            caller.msg("You aren't working this bar.")
            return
        clutter = [
            o for o in bar.contents
            if getattr(o.db, "is_drink", False) or getattr(o.db, "is_ingredient", False)
        ]
        if not clutter:
            caller.msg(f"{bar.get_display_name(caller)} is already clean.")
            return
        for o in clutter:
            o.delete()
        caller.msg(
            f"You wipe down {bar.get_display_name(caller)}, clearing away the "
            f"empties and abandoned glasses with a practiced sweep."
        )
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} wipes down {bar.key}, clearing away the empties.",
            char_refs={"actor": caller},
            exclude=[caller],
        )


class BarCmdSet(CmdSet):
    key = "bar_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdBarMenu())
        self.add(CmdBarUse())
        self.add(CmdBarPrepare())
        self.add(CmdBarClear())


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
        # Stock (what the bar carries → what it can mix off-menu) is derived from
        # the menu + base pantry by default (see world.bar.bar_stock); a builder
        # may set an explicit db.stock to widen/narrow it.
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
        # Seating: a bar comes with stools (FURNITURE_AND_POSTURE). Idempotent,
        # and safe if the counter has no room yet. Existing bars are backfilled
        # once at the DB level (`for b in BarCounter.objects.all(): b.stock_stools()`).
        self.stock_stools()

    def stock_stools(self, count=BAR_STOOL_COUNT):
        """Spawn this bar's seating into its room — once (guarded by a flag).
        Returns how many stools were added."""
        if self.db.stools_spawned:
            return 0
        room = self.location
        if not room:
            return 0
        from evennia.prototypes.spawner import spawn
        from world.prototypes import BAR_STOOL
        added = 0
        for _ in range(count):
            try:
                stool = spawn(BAR_STOOL)[0]
                stool.move_to(room, quiet=True, move_hooks=False)
                added += 1
            except Exception:  # noqa: BLE001 — never let seating break bar setup
                break
        self.db.stools_spawned = bool(added)
        return added

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


class Bartender(LLMNpcMixin, Character):
    """An NPC that takes drink orders by being spoken to (the `to` command).

    Bartending mechanics on top of the shared LLM brain (``LLMNpcMixin``):
    orders/gratitude intercept speech before the LLM layer, and the
    ``check_stock`` / ``prepare_drink`` tools route to the bar.
    """

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
        # LLM-driven dialogue is opt-in per NPC (and also gated by the
        # deployment-wide LLM_GM_ENABLED). Builders flip this on the NPCs that
        # should think; everyone else stays fully scripted.
        self.db.llm_driven = False

    def _find_bar(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, BarCounter):
                return obj
        return None

    def _handle_directed_speech(self, speech, speaker, kwargs):
        """Bartender intercept (before the LLM layer): gratitude → a small
        non-verbal nod (checked first so "thanks for the rotgut" reads as a
        thank-you, not a re-order); an *addressed* line → a menu order. Returns
        True when handled, so conversation only reaches the LLM otherwise.
        """
        if self._is_gratitude(speech):
            self._acknowledge()
            return True
        if kwargs.get("addressed"):
            delay(1.5, self._fulfil_order, speech, speaker)
            return True
        return False

    def _name_aliases(self):
        return ["bartender", "barkeep", "barkeeper"]

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
        # MENU first, then off-menu from STOCK — a classic the bar carries the
        # makings for is served even if it's not on the board.
        recipe, _offmenu = resolve_drink(order_text, bar) if bar else (
            match_recipe(order_text, self.db.menu or []), False)
        if not recipe:
            # An addressed line that isn't an order becomes conversation when the
            # LLM is driving her; otherwise the curt scripted line still stands.
            if not self._try_llm_reply(order_text, patron, "directed",
                                       on_fail=self._llm_fallback):
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

    # --- bartender tool routing (over the shared LLM brain) ------------------

    def _run_context_tool(self, tool, arg, patron):
        """Extend the read-only tools with ``check_stock`` (``look`` is the
        mixin's). Reads only — the action tool goes through a real command."""
        if tool == "check_stock":
            bar = self._find_bar()
            menu = (bar.db.menu if bar else None) or self.db.menu or []
            names = [r.get("name") for r in menu if r.get("name")]
            parts = [("Board: " + ", ".join(names)) if names else "nothing on the board"]
            # Surface the off-menu capability so she can offer a classic she
            # stocks the makings for even when it isn't on the board.
            off = stockable_cocktails(bar_stock(bar)) if bar else []
            if off:
                shown = ", ".join(off[:8])
                parts.append("Off the board, can mix from stock: " + shown
                             + (", and more" if len(off) > 8 else ""))
            return ". ".join(parts) + "."
        return super()._run_context_tool(tool, arg, patron)

    def _handle_action_tool(self, tool, arg, patron):
        """Route ``prepare_drink`` to the real ``prepare`` command (the bar makes
        the drink for real); delegate the rest (e.g. ``remember``) to the mixin."""
        if tool == "prepare_drink" and arg and self.location:
            self.execute_cmd(f"prepare {arg}")
            return
        LLMNpcMixin._handle_action_tool(self, tool, arg, patron)

    def _llm_fallback(self):
        """Sidecar failed on an addressed non-order: the curt scripted line."""
        if self.location:
            self.execute_cmd("say Don't serve that here.")
