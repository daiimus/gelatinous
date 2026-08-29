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
from typeclasses.furniture import Seating
from typeclasses.llm_npc import LLMNpcMixin
from world.grammar import capitalize_first, with_article
from world.shop.utils import format_currency
from world.bar import (
    DEFAULT_BAR_SNACKS,
    bar_stock,
    make_drink_from_recipe,
    match_recipe,
    plate_or_mix,
    resolve_drink,
    stockable_cocktails,
    tender_at,
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


class CmdOrder(Command):
    """
    Order something from whoever is working the counter.

    Usage:
        order <thing>

    Says it aloud to the person behind the counter — the same as speaking
    to them directly, without having to know their name. They make it,
    set it down on the counter, and take the payment out of the gesture;
    pick it up when it lands.

    ``menu`` shows what's on the board. A counter with nobody working it
    doesn't take orders.
    """

    key = "order"
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        caller = self.caller
        bar = self.obj              # the counter this cmdset is attached to
        speech = (self.args or "").strip()
        if not speech:
            caller.msg("Order what?")
            return
        location = caller.location
        if location is None or bar.location is not location:
            caller.msg("You aren't at the counter.")
            return
        tender = tender_at(bar)
        if tender is None:
            name = bar.get_display_name(caller)
            caller.msg(f"There's nobody working {name}.")
            return
        # Ordering is just DIRECTED SPEECH with the targeting done for you.
        # It rides the shared speech backbone rather than a private channel,
        # so the room hears the order, perception applies as it does to any
        # other spoken line, and the whole serve path — menu, off-menu
        # mixing, price, till, emote — is reached exactly the way a patron
        # who knew the tender's name would reach it (#2342).
        from world.speech import broadcast_speech
        caller.msg(f'You say to {tender.get_display_name(caller)}, "{speech}"')
        broadcast_speech(caller, speech, location, target=tender)


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


class CmdBarTill(Command):
    """
    Take the day's earnings out of the bar.

    Usage:
        till <bar>
        till <bar> = <amount>

    Counts what the register holds, and hands it over. With an amount, takes
    only that much and leaves the rest. For the owner and their staff.

    Money went INTO the register on every sale and had no way back out — the
    bar accumulated a number nobody could spend. The butcher's block already
    closed this loop (payouts drain its till); this is the same door on the
    other side of the counter.
    """

    key = "till"
    locks = "cmd:all()"
    help_category = "Bar"

    def func(self):
        from world.identity_utils import msg_room_identity

        bar = self.obj
        caller = self.caller

        owner = bar.db.owner
        staff = bar.db.staff or []
        if owner is not None and caller != owner and caller not in staff:
            caller.msg("That's not your register.")
            return

        held = int(bar.db.register or 0)
        if held <= 0:
            caller.msg("The register's empty.")
            return

        # NB: this is evennia.commands.command.Command, not MuxCommand — there
        # is no self.rhs. Parse the "= <amount>" half by hand.
        take = held
        amount = ""
        if "=" in (self.args or ""):
            amount = self.args.split("=", 1)[1].strip()
        if amount:
            try:
                take = int(amount)
            except (TypeError, ValueError):
                caller.msg("Take how much?")
                return
            if take <= 0:
                caller.msg("Take how much?")
                return
            take = min(take, held)

        bar.db.register = held - take
        caller.tokens = int(getattr(caller, "tokens", 0) or 0) + take

        left = bar.db.register
        caller.msg(
            f"You count {take} out of the register"
            + (f", leaving {left}." if left else " and leave it empty.")
        )
        msg_room_identity(
            location=caller.location,
            template="{actor} counts the register out and pockets the take.",
            char_refs={"actor": caller},
            exclude=[caller],
        )


class BarCmdSet(CmdSet):
    key = "bar_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdBarMenu())
        self.add(CmdOrder())
        self.add(CmdBarUse())
        self.add(CmdBarPrepare())
        self.add(CmdBarClear())
        self.add(CmdBarTill())


# ---------------------------------------------------------------------------
# The bar counter — an @integrate room fixture with a surface
# ---------------------------------------------------------------------------
class BarCounter(Seating, Item):
    """An interactive bar counter — the first crafting station, and its own
    seating (FURNITURE_AND_POSTURE).

    An ``Item`` (so the @integrate room display recognises it) but a fixed
    fixture: ``db.integrate`` folds it into the room description rather than the
    loose-object list, and a ``get:false()`` lock keeps it from being picked up.
    Served drinks rest in its ``contents`` (the surface). The stools are part of
    the bar — ``sit at bar`` takes one of its ``capacity`` slots, not a loose
    object (``Seating`` provides the occupancy API).
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
        # A counter declares its own JOB. `register_post` may rename it (the
        # Snailery calls the same work "snailer") and adds the shift slots;
        # until then this is what says a bar is a thing somebody tends, and
        # it is what `world/service.py` keys the serve handler on (#2350).
        self.db.post_role = "bartender"
        self.locks.add("get:false()")     # stuck — can't be pocketed
        self.cmdset.add(BarCmdSet, persistent=True)
        # Seating: the stools ARE the bar — `sit at bar` fills one of these slots.
        self.db.postures = ("sitting",)
        self.db.capacity = BAR_STOOL_COUNT   # ten stools' worth
        self.db.preposition = "at"
        # @integrate weaves the counter into the room description (the stools are
        # described as part of it, so players see them without a loose listing).
        self.db.integration_fallback = (
            "A salvaged |cbar|n runs along one side of the room, its surface "
            "scarred by years of set-down glasses, a row of mismatched stools "
            "bolted along its base."
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


# `Bartender` is gone (#2378). An NPC is a `LLMNpc` whose
# capabilities come from the POST it stands and the SOUL it
# carries — the typeclass says what a body IS, never what it
# can do (NPC_PLATFORM_SPEC §3, law 5).
