"""Generic LLM-driven NPC — the engagement loop + agentic tool loop, factored
out of the bartender so any archetype (Companion, …) can think.

The NPC's *job* is its persona archetype (``world/llm/prompt.ARCHETYPES``); this
class is just the **brain**. Subclasses add job mechanics through small hooks:

* ``_handle_directed_speech`` — intercept addressed/special speech before the LLM
  layer (e.g. a bartender's orders / gratitude). Return True if fully handled.
* ``_run_context_tool`` — extend the read-only tools (``look`` is built in here).
* ``_handle_action_tool`` — route an archetype's *action* tool to a real command.
* ``_name_aliases`` — extra words that count as naming this NPC.

Reactor-safety mirrors ``CmdBug``: persona is built on the reactor, the blocking
POST runs off-reactor (``world/llm/client``), and the callbacks orchestrate the
agentic loop back on the reactor. See ``LLM_GAMEMASTER_SPEC`` Phase 1.
"""

import json
import random
import re
from functools import partial
from time import monotonic

from evennia.utils.utils import delay

from typeclasses.characters import Character
from evennia.utils.dbserialize import deserialize

from typeclasses.llm_persona import build_persona
from world.llm import memory as mem
from world.llm.client import llm_enabled, request_embedding, request_turn
from world.llm.prompt import (
    CONTEXT_TOOLS, build_messages, is_echo, parse_turn, schema_for, tool_names,
)

LLM_DIRECTED_COOLDOWN = 4.0    # min seconds between replies to direct address/name
LLM_ENGAGE_HOLD = 600.0        # conversation hold: an engaged NPC defers its
                               # routine (patrol/drift) until the model calls
                               # the `release` tool or this inactivity window
                               # lapses (failsafe for walked-away-from NPCs).
                               # Generous: a long RP pose takes minutes to type.
LLM_AMBIENT_COOLDOWN = 45.0    # rarely volunteers into overheard chatter
LLM_AMBIENT_CHANCE = 0.35      # ...and not every eligible time
LLM_HISTORY_TURNS = 6          # recent turns kept per interlocutor (anti-repetition)
LLM_MAX_TOOL_ROUNDS = 3        # cap the agentic loop so it can't spin forever
LLM_MEMORY_TOPK = 3            # long-term memories recalled into a turn (Phase 2)
LLM_ACTION_BUFFER = 6          # room actions observed (no LLM) → next reply (§8.4)


class LLMNpcMixin:
    """The reusable LLM brain. Mix into a Character (before it in the MRO)."""

    # --- engagement entrypoint -------------------------------------------
    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """React to heard speech. Job-specific handlers get first crack; the
        LLM layer only runs when both gates (per-NPC + deployment) are on, so a
        scripted NPC is byte-identical with the LLM off."""
        speaker = from_obj
        if speaker is None or speaker is self:
            return True
        # §8.4 ambient action-awareness: a pure pose/emote (an *action*, not
        # words) is OBSERVED cheaply into a buffer — NO LLM call — and consumed
        # on the next reply. This is what keeps the single-threaded model from
        # saturating: poses cost nothing until they ride a turn we're making.
        speech = kwargs.get("speech")
        if kwargs.get("type") == "pose" and not speech:
            if self.db.llm_driven:
                self._observe_action(speaker, text)
                # A wordless pose aimed AT this NPC warrants a reaction (like
                # directed speech). Ambient poses (not aimed at us) stay
                # observe-only, so the model never saturates on room chatter.
                if (kwargs.get("addressed") and llm_enabled()
                        and not self._is_npc_speaker(speaker)):
                    delay(1.5, self._try_llm_reply, text, speaker, "action")
            return True
        if not speech:
            return True
        if self._handle_directed_speech(speech, speaker, kwargs):
            return True
        if self.db.llm_driven and llm_enabled():
            kind = self._classify_speech(speech, speaker)
            if kind == "directed":
                delay(1.5, self._try_llm_reply, speech, speaker, "directed")
            elif kind == "ambient":
                delay(1.0, self._try_llm_reply, speech, speaker, "ambient")
        return True

    def _handle_directed_speech(self, speech, speaker, kwargs):
        """Hook: a subclass intercepts addressed/special speech before the LLM
        layer (a bartender's orders/gratitude). Return True if fully handled."""
        return False

    # --- classification --------------------------------------------------
    def _is_npc_speaker(self, speaker):
        """Loop guard: another NPC, so we never react (speech or pose) and two
        LLM-driven NPCs can't ping-pong."""
        return bool(getattr(speaker.db, "is_npc", False)
                    or getattr(speaker.db, "is_bartender_npc", False)
                    or getattr(speaker.db, "llm_driven", False))

    def _classify_speech(self, speech, speaker):
        """Cheap reactor-side gate: ``directed`` | ``ambient`` | ``ignore``."""
        if self._is_npc_speaker(speaker):
            return "ignore"
        # Mid-conversation, the engaged partner doesn't have to keep naming
        # this NPC — their lines stay directed (else a busy room demotes them
        # to ambient and the NPC goes near-mute mid-scene).
        if self._is_engaged_with(speaker):
            return "directed"
        if self._mentions_self(speech) or self._is_alone_with(speaker):
            return "directed"
        return "ambient"

    def _is_engaged_with(self, speaker):
        """Whether the conversation hold is active AND held for this speaker."""
        until = self.ndb.llm_engaged_until
        return bool(until and monotonic() < until
                    and self.ndb.llm_engaged_with == self._hist_key(speaker))

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
        """Whether a line names this NPC (key, keyword, or role aliases)."""
        low = (speech or "").lower()
        names = [self.key.lower()]
        if self.sdesc_keyword:
            names.append(self.sdesc_keyword.lower())
        names += self._name_aliases()
        return any(n and n in low for n in names)

    def _name_aliases(self):
        """Hook: extra words that count as naming this NPC (role words)."""
        return []

    # --- request orchestration -------------------------------------------
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
        if mode in ("ambient", "arrival"):
            # Volunteering into the room (overheard chatter or someone walking
            # in) is rate-limited and probabilistic so the NPC doesn't pounce.
            if now - last < LLM_AMBIENT_COOLDOWN:
                return True  # throttled: stay silent rather than spam
            if random.random() > LLM_AMBIENT_CHANCE:
                return True  # eligible, but didn't bite this time
        elif now - last < LLM_DIRECTED_COOLDOWN:
            return True
        self.ndb.last_llm = now
        if mode in ("directed", "action"):
            # Conversation hold: don't wander off mid-exchange. Rolling —
            # refreshed every directed turn AND every pose aimed at us (an RP
            # scene is mostly poses); the model releases it early via the
            # `release` tool. Keyed to the partner so their lines stay
            # directed without re-naming us each turn.
            self.ndb.llm_engaged_until = now + LLM_ENGAGE_HOLD
            self.ndb.llm_engaged_with = self._hist_key(patron)

        # Capture everything reactor-side BEFORE threading (SQLite/Evennia-thread
        # contract). The agentic loop re-calls from the reactor-side callback.
        persona = build_persona(self)
        speaker_name = self._address_handle(patron)
        perception = self._perceive(patron)
        history = self._recent_history(patron)
        subject = self._memory_subject(patron)
        relationship = self._relationship_line(subject, patron)
        events = self._drain_actions()  # what we've witnessed since last reply
        present = self._present_others(patron)  # who else is in the room now
        on_fail = on_fail or self._llm_silent

        def _go(memories):
            messages = build_messages(persona, speaker_name, line or "", mode,
                                      perception, history, memories=memories,
                                      relationship=relationship, events=events,
                                      present=present)
            self._agentic_round(messages, persona, patron, line or "",
                                speaker_name, on_fail, rounds=0)

        def _with_query_vec(vec):
            # reactor-side: score this NPC's memories against the line, inject.
            try:
                hits = mem.retrieve(vec, self._load_memories(),
                                    k=LLM_MEMORY_TOPK, subject=subject)
                _go(mem.memory_texts(hits))
            except Exception:  # noqa: BLE001 — memory is best-effort
                _go(None)

        # Phase 2: recall before generating. Skip the embed round-trip entirely
        # when there's nothing to recall (first-ever interactions add no latency);
        # any embed failure degrades to a memoryless reply.
        if line and self._load_memories():
            request_embedding(line, on_done=_with_query_vec,
                              on_fail=lambda: _go(None))
        else:
            _go(None)
        return True

    # --- long-term memory (Phase 2) --------------------------------------

    def _memory_subject(self, patron):
        """The recognition identity to scope memory by — the *perceived*
        identity (apparent_uid), so memory rides the same spine as recognition
        and a disguise reads as a stranger (NPC_MEMORY_AND_IDENTITY_SPEC §1).
        Falls back to object id for pre-chargen shells with no apparent_uid."""
        try:
            from world.identity import get_apparent_uid
            return get_apparent_uid(patron) or self._hist_key(patron)
        except Exception:  # noqa: BLE001 — never break a reply over keying
            return self._hist_key(patron)

    def _load_memories(self):
        """This NPC's stored memory records as plain dicts (deserialized)."""
        return deserialize(self.db.llm_memories) or []

    # --- room presence: who's here, who comes and goes -------------------

    def _address_handle(self, target):
        """The handle the model should use to REFER to ``target``: a name this NPC
        has assigned it, else the clothing-free CORE sdesc ("a stocky droog") —
        NOT the full sdesc, whose garment clause ("...in an armored leather
        jacket") makes the model point at, and paraphrase, clothing. The char-ref
        matcher resolves the short form; the render restores the full per-observer
        identity for onlookers."""
        from world.identity import get_assigned_name, get_short_sdesc
        try:
            return get_assigned_name(self, target) or get_short_sdesc(target)
        except Exception:  # noqa: BLE001 — fall back to the standard display name
            return target.get_display_name(self)

    def _present_others(self, patron=None):
        """The characters sharing this NPC's room right now, each by the handle
        THIS NPC would address them by (so the model can reference them and the
        world renders per-observer). The current speaker is excluded — they're
        already in PERCEPTION — and other NPCs are kept (they're really here).
        Capped to keep the prompt bounded in a crowded room."""
        loc = self.location
        if not loc:
            return []
        names = []
        for obj in loc.contents:
            if obj is self or obj is patron:
                continue
            if not hasattr(obj, "get_sdesc"):
                continue
            name = self._address_handle(obj)
            if name:
                names.append(name)
        return names[:8]

    def notice_presence_change(self, mover, entered):
        """The room tells us a character entered (``entered=True``) or left.

        We BUFFER it cheaply as a witnessed event (no LLM) — it rides the next
        reply via ``[RECENTLY]`` — so the NPC's sense of the room stays current.
        A non-NPC ARRIVAL may additionally provoke a gated, probabilistic
        reaction (a greeting/acknowledgement), throttled like ambient chatter so
        the NPC notices newcomers without pouncing on everyone who walks by.
        Departures and other NPCs' comings/goings are observe-only."""
        if not self.db.llm_driven or mover is self:
            return
        try:
            name = mover.get_display_name(self)
        except Exception:  # noqa: BLE001
            return
        self._observe_action(mover, f"{name} {'arrives' if entered else 'leaves'}.")
        if (entered and llm_enabled() and not self._is_npc_speaker(mover)):
            delay(1.5, self._try_llm_reply, None, mover, "arrival")

    # --- ambient action-awareness (§8.4) ---------------------------------

    def _observe_action(self, actor, text):
        """Buffer a witnessed room action — reactor-side, NO LLM. Already
        rendered from this NPC's POV (names resolved), so just keep the text."""
        if not text:
            return
        from evennia.utils.ansi import strip_ansi
        clean = " ".join(strip_ansi(text).split())[:200]
        if not clean:
            return
        buf = list(self.ndb.action_buffer or [])
        buf.append(clean)
        self.ndb.action_buffer = buf[-LLM_ACTION_BUFFER:]

    def _drain_actions(self):
        """Recent witnessed actions, consumed (cleared) for this turn."""
        buf = list(self.ndb.action_buffer or [])
        self.ndb.action_buffer = []
        return buf

    # --- per-identity dossier: aliases + affective read (§8.3) ------------

    def _dossiers(self):
        """Per-identity dossiers (apparent_uid -> {aliases, valence}). Plain,
        deserialized, GM-readable (NPC_MEMORY_AND_IDENTITY_SPEC §2/§3)."""
        return deserialize(self.db.llm_dossiers) or {}

    def _relationship_line(self, subject, patron):
        """A one-line WHO summary for the prompt — the names this NPC knows the
        person by + its read on them. ``None`` for a clean stranger."""
        d = self._dossiers().get(subject) or {}
        aliases = [a for a in (d.get("aliases") or []) if a]
        valence = d.get("valence") or "neutral"
        if not aliases and valence == "neutral":
            return None
        parts = []
        if len(aliases) == 1:
            parts.append(f"you know them as '{aliases[0]}'")
        elif aliases:
            parts.append("you've known them as "
                         + ", ".join(f"'{a}'" for a in aliases))
        if valence != "neutral":
            parts.append(f"your read on them: {valence}")
        return ("; ".join(parts) + ".") if parts else None

    def _note_alias(self, subject, name):
        """Record a name in this person's alias history (capped, deduped)."""
        d = self._dossiers()
        entry = dict(d.get(subject) or {"aliases": [], "valence": "neutral"})
        aliases = [a for a in (entry.get("aliases") or []) if a]
        if name not in aliases:
            aliases.append(name)
        entry["aliases"] = aliases[-8:]
        d[subject] = entry
        self.db.llm_dossiers = d

    def _set_valence(self, subject, valence):
        """Update the NPC's private read on a person (§8.5 behaviour-driven).
        Surfaces in the WHO block next turn; consulted by trust/consent later."""
        valence = " ".join(str(valence).split())[:40]
        if not valence:
            return
        d = self._dossiers()
        entry = dict(d.get(subject) or {"aliases": [], "valence": "neutral"})
        entry["valence"] = valence
        d[subject] = entry
        self.db.llm_dossiers = d

    def _store_memory(self, patron, speaker_name, line, speech):
        """Remember this exchange: embed it off-reactor, then write a record
        (scoped to the interlocutor) and prune. Fire-and-forget — runs after the
        reply has already rendered, so it never delays the NPC."""
        if not line:
            return
        text = f'{speaker_name} said: "{line}"'
        if speech:
            text += f' — I answered: "{speech}"'
        subject = self._memory_subject(patron)

        def _save(vec):
            recs = self._load_memories()
            recs.append(mem.make_record(text, vec, subject=subject))
            self.db.llm_memories = mem.prune(recs)

        request_embedding(text, on_done=_save, on_fail=self._llm_silent)

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
            schema=schema_for(persona),  # tool enum scoped to the archetype
        )

    def _on_turn(self, messages, persona, patron, line, speaker_name, on_fail,
                 rounds, raw):
        turn = parse_turn(raw, persona, tool_names(persona))
        # Echo guard: a pose aimed at the NPC sometimes comes straight back
        # as its "own" action (or speech). Parroting reads broken — drop it.
        for field in ("action", "speech"):
            if turn[field] and is_echo(turn[field], line):
                turn[field] = None
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
        # Terminal: render speech/action/thought, route any action tool, remember.
        self._render_llm_reply(turn["speech"], turn["action"], turn["thought"],
                               patron)
        self._handle_action_tool(tool, arg, patron)
        self._remember_turn(patron, line, speaker_name, turn["speech"],
                            turn["action"], turn["thought"])
        # Long-term memory: persist what was learned (async, post-render).
        self._store_memory(patron, speaker_name, line, turn["speech"])

    def _run_context_tool(self, tool, arg, patron):
        """Run a read-only context tool and return its result for the model.
        ``look`` is built in; subclasses extend (then call super)."""
        if tool == "look":
            return self._perceive(patron) or "nothing remarkable"
        return ""

    def _handle_action_tool(self, tool, arg, patron):
        """Route an action tool to a real command. ``remember``/``feel``/
        ``release`` are universal; subclasses extend then call super."""
        if tool == "remember" and arg and patron and self.location:
            self._remember_person(patron, arg)
        elif tool == "feel" and arg and patron:
            self._set_valence(self._memory_subject(patron), arg)
        elif tool == "style" and arg:
            # Adjust own clothing through the REAL zip/rollup/remove/wear
            # commands — the fiction and the worn state stay in agreement.
            # The model writes the argument in natural register ("take off
            # her mesh top (unzipped)"), so normalise onto the command
            # grammar rather than silently dropping the call.
            arg = " ".join(str(arg).split())
            low = arg.lower()
            if low.startswith("take off "):
                arg = "remove " + arg[9:]
            elif low.startswith("put on "):
                arg = "wear " + arg[7:]
            parts = arg.split(None, 1)
            verb = parts[0].lower() if parts else ""
            verb = {"strip": "remove", "doff": "remove",
                    "shed": "remove", "don": "wear"}.get(verb, verb)
            garment = parts[1] if len(parts) > 1 else ""
            # bare item key only: no possessive/article lead, no copied
            # style-state parenthetical from the wardrobe card
            garment = re.sub(r"^(?:her|his|their|its|my|the|a|an)\s+",
                             "", garment, flags=re.I)
            garment = re.sub(r"\s*\([^)]*\)\s*$", "", garment).strip()
            if verb in ("zip", "unzip", "button", "unbutton",
                        "rollup", "unroll", "remove", "wear") and garment:
                self.execute_cmd(f"{verb} {garment}")
        elif tool == "release":
            # The character has decided the exchange is over: drop the
            # conversation hold so the routine (patrol/drift) resumes on
            # the next heartbeat. The goodbye itself rides the normal
            # speech/action channels of this same turn.
            self.ndb.llm_engaged_until = None
            self.ndb.llm_engaged_with = None

    def _remember_person(self, patron, name):
        """Privately name/nickname the interlocutor via the REAL ``remember``
        command (NPC_MEMORY_AND_IDENTITY_SPEC §4) — keyed on their apparent_uid
        in this NPC's recognition memory. Skips a no-op re-name so the LLM can't
        churn the same nickname every turn."""
        name = " ".join(str(name).split())[:40]
        if not name or " as " in name.lower():
            return
        try:
            from world.identity import get_assigned_name
            if get_assigned_name(self, patron) == name:
                return  # already known by this name
            target = patron.get_display_name(self)
            self.execute_cmd(f"remember {target} as {name}")
            self._note_alias(self._memory_subject(patron), name)
        except Exception:  # noqa: BLE001 — naming is best-effort
            pass

    def _remember_turn(self, patron, line, speaker_name, speech, action,
                       thought=None):
        """Append the rendered turn to short-term memory (anti-repetition)."""
        reply = self._reconstruct_reply(speech, action, thought)
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
    def _reconstruct_reply(speech, action, thought=None):
        """Re-form the model's own reply for the history (so it sees its prior
        gestures, phrasing, AND interiority, in the format it produces)."""
        parts = []
        if action:
            parts.append(f"*{action}*")
        if speech:
            parts.append(f'"{speech}"')
        if thought:
            parts.append(f"( {thought} )")
        return " ".join(parts)

    def _render_llm_reply(self, speech, action, thought=None, patron=None):
        """Render the sidecar reply through the REAL roleplay commands players
        use — one channel per field, no bespoke rendering.

        The model writes ``action`` as a third-person predicate ("wipes down the
        bar, eyeing the lean man") — exactly the register an RP model is fluent
        in. We hand it to ``execute_cmd('emote <action>')``: ``CmdEmote`` prepends
        the NPC's per-observer name, resolves each referenced character as the
        watcher knows them, and rides the hearing-gated speech rails — and does NO
        verb conjugation, so the model's natural prose renders as-is. The spoken
        line rides along as an embedded quote (one beat); speech with no action
        falls back to a bare ``say``. ``thought`` (private interiority) goes to
        ``execute_cmd('think <thought>')`` — perceived only by the actor and a
        mind-reader, so it never leaks onto the visible stage."""
        if not self.location:
            return
        speech = speech.strip().strip('"').strip() if speech else None
        action = action.strip() if action else None
        thought = thought.strip() if thought else None
        if action:
            body = action
            if speech and '"' not in body:
                # Weave the line in as a quote so it reads as one beat and still
                # rides the say/hearing rails (render_emote extracts it). If the
                # action already carries a quote, that one rides — don't double.
                sep = "" if body[-1] in ",.!?…" else ","
                body = f'{body}{sep} "{speech}"'
            self.execute_cmd(f"emote {body}")
        elif speech:
            self.execute_cmd(f"say {speech}")
        if thought:
            self.execute_cmd(f"think {thought}")

    def _llm_silent(self):
        """Sidecar failed or declined on conversation: stay quiet."""
        return None


class LLMNpc(LLMNpcMixin, Character):
    """A generic LLM-driven social NPC. The persona's ``archetype`` is its job;
    the typeclass is only the brain. Opt in per-NPC via ``db.llm_driven`` (and
    the deployment-wide ``LLM_GM_ENABLED``)."""

    def at_object_creation(self):
        super().at_object_creation()
        # Identity safety-net: a Character with no height/build composes no sdesc
        # and falls back to its *key* — leaking the NPC's real name. Seed a
        # baseline so it always renders through the identity system.
        if not self.height:
            self.height = "average"
        if not self.build:
            self.build = "average"
        self.db.llm_driven = False
