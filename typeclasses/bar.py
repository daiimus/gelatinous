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

import json
import random
from functools import partial
from time import monotonic

from evennia import CmdSet
from evennia.commands.command import Command
from evennia.utils import delay

from typeclasses.items import Item
from typeclasses.characters import Character
from typeclasses.llm_persona import build_persona
from world.grammar import capitalize_first, with_article
from world.llm.client import llm_enabled, request_turn
from world.llm.prompt import build_messages, parse_turn
from world.shop.utils import format_currency
from world.bar import (
    DEFAULT_BAR_SNACKS,
    make_drink_from_recipe,
    match_recipe,
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
        recipe = match_recipe(query, bar.db.menu or [])
        if not recipe:
            caller.msg(
                f"That's not on {bar.get_display_name(caller)}'s menu."
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

#: LLM-driven conversational replies (LLM_GAMEMASTER_SPEC Phase 1, #707). Gated
#: by BOTH ``settings.LLM_GM_ENABLED`` (deployment) and ``npc.db.llm_driven``
#: (per-NPC), so a scripted bartender stays byte-identical when the LLM is off.
LLM_DIRECTED_COOLDOWN = 4.0    # min seconds between replies to direct address/name
LLM_AMBIENT_COOLDOWN = 45.0    # she rarely volunteers into overheard chatter
LLM_AMBIENT_CHANCE = 0.35      # ...and not every eligible time
LLM_HISTORY_TURNS = 6          # recent turns kept per interlocutor (anti-repetition)
#: Tools the model may call that *inform* it (read-only) vs *act* (mutate). Context
#: tools loop (run → feed result back → re-ask); action tools route to a command.
CONTEXT_TOOLS = {"look", "check_stock"}
LLM_MAX_TOOL_ROUNDS = 3        # cap the agentic loop so it can't spin forever


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

        # LLM conversational layer — only when both gates are on, so the
        # scripted NPC is byte-identical with the LLM off. Orders and gratitude
        # above are never routed here.
        if self.db.llm_driven and llm_enabled():
            kind = self._classify_speech(speech, speaker)
            if kind == "directed":
                delay(1.5, self._try_llm_reply, speech, speaker, "directed")
            elif kind == "ambient":
                delay(1.0, self._try_llm_reply, speech, speaker, "ambient")
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

    # --- LLM-driven conversation (gated; LLM_GAMEMASTER_SPEC Phase 1) --------

    def _classify_speech(self, speech, speaker):
        """Cheap reactor-side gate: ``directed`` | ``ambient`` | ``ignore``."""
        # Loop guard: never react to another NPC's broadcast speech, so two
        # LLM-driven NPCs can't ping-pong on ambient lines.
        if (getattr(speaker.db, "is_bartender_npc", False)
                or getattr(speaker.db, "llm_driven", False)):
            return "ignore"
        # Named, or effectively alone with the speaker (then any line is plainly
        # for her), counts as directed; otherwise it's overheard chatter.
        if self._mentions_self(speech) or self._is_alone_with(speaker):
            return "directed"
        return "ambient"

    def _is_alone_with(self, speaker):
        """True when no other character shares the room — so the speaker can only
        be talking to this NPC."""
        if not self.location:
            return False
        return not any(
            o is not self and o is not speaker and isinstance(o, Character)
            for o in self.location.contents
        )

    def _mentions_self(self, speech):
        """Whether a line names this bartender (key, keyword, or generic role)."""
        low = (speech or "").lower()
        names = [self.key.lower()]
        if self.sdesc_keyword:
            names.append(self.sdesc_keyword.lower())
        names += ["bartender", "barkeep", "barkeeper"]
        return any(n and n in low for n in names)

    def _try_llm_reply(self, line, patron, mode, on_fail=None):
        """Route a conversational line to the LLM sidecar, off the reactor.

        Returns True if the LLM path was taken (caller suppresses any scripted
        fallback), False if gated/throttled off so the caller can fall back.
        """
        if not self.db.llm_driven or not llm_enabled():
            return False
        if (not self.location
                or getattr(patron, "location", None) is not self.location):
            return False

        now = monotonic()
        last = self.ndb.last_llm or 0
        if mode == "ambient":
            if now - last < LLM_AMBIENT_COOLDOWN:
                return True  # throttled: stay silent rather than spam
            if random.random() > LLM_AMBIENT_CHANCE:
                return True  # eligible, but she didn't bite this time
        elif now - last < LLM_DIRECTED_COOLDOWN:
            return True
        self.ndb.last_llm = now

        # Capture everything reactor-side BEFORE threading (SQLite/Evennia-thread
        # contract). The agentic loop re-calls from the reactor-side callback.
        persona = build_persona(self)
        speaker_name = patron.get_display_name(self)
        perception = self._perceive(patron)
        history = self._recent_history(patron)
        messages = build_messages(persona, speaker_name, line or "", mode,
                                  perception, history)
        self._agentic_round(messages, persona, patron, line or "", speaker_name,
                            on_fail or self._llm_silent, rounds=0)
        return True

    def _perceive(self, patron):
        """What this NPC sees when it looks at the patron — grounds the model's
        description so it can't invent the speaker's appearance. ANSI-stripped,
        identity-gated, trimmed to a sentence-bounded summary (the full
        return_appearance bloats context and truncates mid-word)."""
        try:
            from evennia.utils.ansi import strip_ansi
            raw = patron.return_appearance(self)
            if not raw:
                return None
            text = " ".join(strip_ansi(raw).split())
            if len(text) > 300:
                cut = text[:300]
                for end in (". ", "! ", "? "):
                    i = cut.rfind(end)
                    if i > 120:
                        cut = cut[: i + 1]
                        break
                text = cut.rstrip()
            return text
        except Exception:
            return None

    # --- short-term conversation memory (per interlocutor, ndb/ephemeral) ----

    @staticmethod
    def _hist_key(patron):
        return f"#{patron.id}"

    def _recent_history(self, patron):
        """The recent turns with this interlocutor — fed back into the prompt so
        the model sees what it just said and stops repeating itself."""
        return (self.ndb.llm_history or {}).get(self._hist_key(patron), [])

    # --- the agentic tool loop (constrained turn → context tools → reply) ----

    def _agentic_round(self, messages, persona, patron, line, speaker_name,
                       on_fail, rounds):
        """One constrained generation; the reactor-side callback either runs a
        context tool and loops, or renders the final reply + any action tool."""
        request_turn(
            messages,
            on_turn=partial(self._on_turn, messages, persona, patron, line,
                            speaker_name, on_fail, rounds),
            on_fail=on_fail,
        )

    def _on_turn(self, messages, persona, patron, line, speaker_name, on_fail,
                 rounds, raw):
        turn = parse_turn(raw, persona)
        tool, arg = turn["tool"], turn["tool_argument"]
        # Context tool: run the real read, feed the result back, loop.
        if tool in CONTEXT_TOOLS and rounds < LLM_MAX_TOOL_ROUNDS:
            result = self._run_context_tool(tool, arg, patron)
            extended = messages + [
                {"role": "assistant",
                 "content": raw if isinstance(raw, str) else json.dumps(raw)},
                {"role": "user", "content": f"[tool result · {tool}] {result}"},
            ]
            self._agentic_round(extended, persona, patron, line, speaker_name,
                                on_fail, rounds + 1)
            return
        # Terminal: render speech/action, run the action tool, remember.
        self._render_llm_reply(turn["speech"], turn["action"])
        if tool == "prepare_drink" and arg and self.location:
            self.execute_cmd(f"prepare {arg}")
        self._remember_turn(patron, line, speaker_name, turn["speech"],
                            turn["action"])

    def _run_context_tool(self, tool, arg, patron):
        """Run a read-only context tool via the game's real logic and return its
        result for the model. (Reads only — world-mutating tools go through real
        commands in ``_on_turn``.)"""
        if tool == "look":
            return self._perceive(patron) or "nothing remarkable"
        if tool == "check_stock":
            bar = self._find_bar()
            menu = (bar.db.menu if bar else None) or self.db.menu or []
            names = [r.get("name") for r in menu if r.get("name")]
            return ("Serves: " + ", ".join(names)) if names else "nothing on tap"
        return ""

    def _remember_turn(self, patron, line, speaker_name, speech, action):
        """Append the rendered turn to short-term memory (anti-repetition)."""
        reply = self._reconstruct_reply(speech, action)
        if not reply:
            return
        hist = self.ndb.llm_history or {}
        key = self._hist_key(patron)
        turns = list(hist.get(key, []))
        turns.append({
            "user": f'{speaker_name} says to you: "{line}"',
            "assistant": reply,
        })
        hist[key] = turns[-LLM_HISTORY_TURNS:]
        self.ndb.llm_history = hist

    @staticmethod
    def _reconstruct_reply(speech, action):
        """Re-form the model's own reply for the history (so it sees its prior
        gestures and phrasing, in the same format it produces)."""
        if action and speech:
            return f'*{action}* "{speech}"'
        if action:
            return f"*{action}*"
        if speech:
            return f'"{speech}"'
        return ""

    def _render_llm_reply(self, speech, action):
        """Render the sidecar reply as ONE fluid emote — the MUD-native way to act
        and speak in a single beat. The embedded quote rides the hearing-gated
        speech rails (``tokenize_emote`` → ``SpeechToken``) and character refs in
        the action resolve per-observer. Falls back to a bare pose or say."""
        if not self.location:
            return
        speech = speech.strip().strip('"').strip() if speech else None
        action = action.strip() if action else None
        if action and speech:
            if action[-1] not in ".!?…,":
                action += "."
            self.execute_cmd(f'pose {action} "{speech}"')
        elif action:
            self.execute_cmd(f"pose {action}")
        elif speech:
            self.execute_cmd(f"say {speech}")

    def _llm_fallback(self):
        """Sidecar failed on an addressed non-order: the curt scripted line."""
        if self.location:
            self.execute_cmd("say Don't serve that here.")

    def _llm_silent(self):
        """Sidecar failed or declined on conversation: stay quiet."""
        return None
