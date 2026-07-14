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
        # Radio traffic (RADIO_COMMS_SPEC §7): delivery already enforced the
        # physical gate (powered tuned device / intact comms organ) and the
        # hearing gate (a deaf listener gets no ``speech``). Distinct from
        # room speech — the source is the AIR, not someone beside us.
        if kwargs.get("type") == "radio":
            self._hear_radio(speech, speaker, kwargs)
            return True
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

    # --- radio comprehension (RADIO_COMMS_SPEC §7) ------------------------

    #: Band-wide address forms — "answer whoever's out there". Only the
    #: ELECTED unit answers these (§7.2 de-confliction).
    _RADIO_BROADCAST_PHRASES = ("all units", "any unit", "all stations",
                                "anyone on this band", "anyone copy",
                                "does anyone copy")

    def _hear_radio(self, speech, speaker, kwargs):
        """A transmission reached this NPC's device. Gate exactly like room
        speech so a busy band can't saturate the model (§7.2):

        * named directly → answer (directed cooldown);
        * band-wide broadcast → only the elected receiver answers;
        * NPC-sourced (witness reports, bot chatter) → observe-only, ever —
          the loop guard that keeps two NPCs from ping-ponging on the air;
        * everything else → observe into the buffer + the rare gated
          volunteer, mirroring ambient room chatter."""
        if not self.db.llm_driven or not speech:
            return   # no brain to reach, or deaf (delivery sent no words)
        voice = self._radio_voice_handle(speaker)
        freq = kwargs.get("radio_frequency") or "the air"
        overheard = f'Over the radio ({freq}), {voice} said: "{speech}"'
        if not llm_enabled() or self._is_npc_speaker(speaker):
            self._observe_action(speaker, overheard)
            return
        # The dispatch operator OBSERVES the band, never radio-replies —
        # the console speaks for her on the air (civic lane, her voice);
        # a second brain answering the same call would double-render at
        # the base. The buffer means the traffic still colours her
        # face-to-face turns: she KNOWS what's been on the band tonight.
        if getattr(self.db, "dispatch_operator", None) is True:
            self._observe_action(speaker, overheard)
            return
        low = speech.lower()
        broadcast = any(p in low for p in self._RADIO_BROADCAST_PHRASES)
        if self._mentions_self(speech):
            mode = "radio"                    # named: answer, cooldown-gated
        elif broadcast and kwargs.get("radio_elected"):
            mode = "radio"                    # "all units": we're the answerer
        elif broadcast:
            self._observe_action(speaker, overheard)
            return                            # someone else's call to take
        else:
            # General chatter: buffer it (colours the next turn), and pass
            # through the ambient gates for the rare volunteer.
            self._observe_action(speaker, overheard)
            mode = "radio_ambient"
        delay(1.5, self._try_llm_reply, speech, speaker, mode)

    def _radio_voice_handle(self, speaker):
        """How this NPC knows the voice on the air — voice-only attribution
        (shared with the player echo render; a modulator defeats it)."""
        try:
            from world.radio import radio_voice_handle
            return radio_voice_handle(speaker, self)
        except Exception:  # noqa: BLE001 — attribution is never load-bearing
            return "an unfamiliar voice"

    def _radio_subject(self, patron):
        """Memory scoping for a voice on the air: the VOICE identity, never
        the visual one — over radio this NPC has never SEEN the speaker, so
        dossier/memory must not leak cross-sensory identity."""
        try:
            from world.voice import get_apparent_voice_uid
            uid = get_apparent_voice_uid(patron)
            return f"voice:{uid}" if uid else self._hist_key(patron)
        except Exception:  # noqa: BLE001
            return self._hist_key(patron)

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
        radio = mode in ("radio", "radio_ambient")
        # Radio is the one channel that legitimately crosses rooms — the
        # device is the gate (§7.5), already enforced at delivery. Everything
        # else requires sharing the room.
        if not radio and (
                not self.location
                or getattr(patron, "location", None) is not self.location):
            return False

        now = monotonic()
        last = self.ndb.last_llm or 0
        if mode in ("ambient", "arrival", "radio_ambient"):
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
        # Radio turns attribute by VOICE and carry no visual perception — the
        # speaker isn't in front of us (§7.1); memory scopes to the voice
        # identity so nothing cross-sensory leaks.
        persona = build_persona(self)
        speaker_name = (self._radio_voice_handle(patron) if radio
                        else self._address_handle(patron))
        perception = None if radio else self._perceive(patron)
        history = self._recent_history(patron)
        subject = (self._radio_subject(patron) if radio
                   else self._memory_subject(patron))
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
                                speaker_name, on_fail, rounds=0,
                                subject=subject)

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
        from world.perception import can_perceive
        names = []
        for obj in loc.contents:
            if obj is self or obj is patron:
                continue
            if not hasattr(obj, "get_sdesc"):
                continue
            # Presence gate (stealth spec §7): the model's PRESENT roster
            # only lists people this NPC actually perceives — a hidden
            # character doesn't leak into an NPC brain's context.
            if not can_perceive(self, obj):
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

    def perceive_forced_command(self, raw):
        """An outside will (the admin ``force`` command) just drove this body.

        Let the brain perceive what it did as its OWN act — the GM speaks
        *through* the NPC, so the model carries on owning the line/gesture
        instead of having no memory of it next turn. Buffered like any
        witnessed event; it rides the next reply's [RECENTLY] block."""
        if not self.db.llm_driven or not raw:
            return
        raw = " ".join(str(raw).split())
        parts = raw.split(None, 1)
        verb = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""
        if verb in ("say", "'") and rest:
            text = f'You yourself just said: "{rest}"'
        elif verb in ("pose", "emote", ";", ":") and rest:
            text = f"You yourself just did: {rest}"
        else:
            text = f"You yourself just did this: {raw}"
        self._observe_action(self, text)

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

    def _store_memory(self, patron, speaker_name, line, speech, subject=None):
        """Remember this exchange: embed it off-reactor, then write a record
        (scoped to the interlocutor) and prune. Fire-and-forget — runs after the
        reply has already rendered, so it never delays the NPC. ``subject``
        overrides the scoping identity (voice-scoped on radio turns) so
        storage always matches what retrieval will look under."""
        if not line:
            return
        text = f'{speaker_name} said: "{line}"'
        if speech:
            text += f' — I answered: "{speech}"'
        subject = subject or self._memory_subject(patron)

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
                       on_fail, rounds, subject=None):
        """One constrained generation; the reactor-side callback either runs a
        context tool and loops, or renders the final reply + any action tool.
        ``subject`` is the memory-scoping identity for this turn (voice-scoped
        on radio turns) — threaded through so storage matches retrieval."""
        request_turn(
            messages,
            on_turn=partial(self._on_turn, messages, persona, patron, line,
                            speaker_name, on_fail, rounds, subject),
            on_fail=on_fail,
            schema=schema_for(persona),  # tool enum scoped to the archetype
        )

    def _on_turn(self, messages, persona, patron, line, speaker_name, on_fail,
                 rounds, subject, raw):
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
                {"role": "user", "content": f"TOOL RESULT ({tool}) — {result}"},
            ]
            self._agentic_round(extended, persona, patron, line, speaker_name,
                                on_fail, rounds + 1, subject=subject)
            return
        # Terminal: render speech/action/thought, route any action tool, remember.
        rendered = self._render_llm_reply(turn["speech"], turn["action"],
                                          turn["thought"], patron)
        # Opt-in tuning log: raw model decision beside the final rendered text,
        # so the game-side transform (conjugation/selfify/second-person) is
        # auditable — the sidecar log sees the prompt but not this step.
        from world.llm.decision_log import decision_log_enabled, log_decision
        if decision_log_enabled():
            log_decision(self, speaker_name, line, turn, rendered)
        self._handle_action_tool(tool, arg, patron)
        self._remember_turn(patron, line, speaker_name, turn["speech"],
                            turn["action"], turn["thought"])
        # Long-term memory: persist what was learned (async, post-render).
        self._store_memory(patron, speaker_name, line, turn["speech"],
                           subject=subject)

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
                # Resolve the model's phrasing against the REAL wardrobe
                # (worn + carried) — fuzzy facade (world.fuzzy), so "mesh
                # top" finds "a mesh top" and a typo still lands. No match
                # above the floor = fall through with the cleaned phrase
                # (the command's own search gets its chance).
                try:
                    from world.fuzzy import best_match
                    candidates = list(self.get_worn_items() or [])
                    candidates += [o for o in (self.contents or [])
                                   if o not in candidates]
                    hit = best_match(garment, candidates,
                                     key=lambda o: getattr(o, "key", ""))
                    if hit:
                        garment = hit[0].key
                except Exception:  # noqa: BLE001 — resolution is best-effort
                    pass
                self.execute_cmd(f"{verb} {garment}")
        elif tool == "radio" and arg:
            # Key up for REAL through the transmit command (§7.3) — worn/held
            # walkie first; the command's own fallback covers a built-in comms
            # organ. No device = the command refuses = the NPC stays mute,
            # exactly as it would for a player (§7.5).
            words = " ".join(str(arg).split()).strip().strip('"').strip()
            if words:
                self.execute_cmd(f"xmit {words}")
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
        name = " ".join(str(name).split())[:40].strip(" .,!?;:'\"")
        if not name or " as " in name.lower():
            return
        # A name needs at least one CONTENT word. Pronouns, demonstratives,
        # and generic person-words aren't names — "you", "that guy", "the
        # one" would become the address handle and poison every subsequent
        # pose reference (and their common tokens would spuriously match
        # ordinary prose in the emote matcher).
        from world.emote import _ASSIGNED_NAME_STOPWORDS
        junk = _ASSIGNED_NAME_STOPWORDS | {
            "me", "my", "mine", "us", "we", "who", "someone", "anybody",
        }
        if all(w.lower() in junk for w in name.split()):
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
            return {}
        speech = speech.strip().strip('"').strip() if speech else None
        action = action.strip() if action else None
        thought = thought.strip() if thought else None
        if action:
            # Deterministic pose backstops: the ACTION renders as "<name>
            # <action>" with NO conjugation, so the model must write a
            # third-person predicate. Code — not the model — GUARANTEES two
            # things the charter can only ask for: (1) verb agreement — a
            # base-form verb ("fill an empty pint") renders "Sable fill an
            # empty pint"; conjugate the leading verb of each clause →
            # "fills"; (2) first-person self-refs ("lowering my voice") →
            # the NPC's pronoun. Small RP models (Rocinante) slip on both.
            action = self._conjugate_action(action)
            action = self._selfify_action(action)
            action = self._selfify_reflexive_gesture(action)
        if action and patron:
            action = self._resolve_second_person(action, patron)
        rendered = {"action": None, "speech": None, "thought": thought}
        if action:
            body = action
            if speech and '"' not in body:
                # Weave the line in as a quote so it reads as one beat and still
                # rides the say/hearing rails (render_emote extracts it). If the
                # action already carries a quote, that one rides — don't double.
                sep = "" if body[-1] in ",.!?…" else ","
                body = f'{body}{sep} "{speech}"'
            rendered["action"] = body
            self.execute_cmd(f"emote {body}")
        elif speech:
            rendered["speech"] = speech
            self.execute_cmd(f"say {speech}")
        if thought:
            self.execute_cmd(f"think {thought}")
        return rendered

    #: Words that never START a pose clause as a verb (determiners,
    #: pronouns, prepositions, conjunctions, common adverbs) — skip them
    #: so "the glass", "her eyes", "slowly turns" aren't mis-conjugated.
    _NOT_A_LEADING_VERB = frozenset((
        "the a an this that these those her his their its my your our",
        "one both all some no every each either neither",
        "and then but so or nor as like with without into onto over under",
        "at on in to for from before after through across around",
        "still slowly slow quietly quiet just already almost barely",
    ).__str__().split())

    def _conjugate_action(self, action):
        """Guarantee verb agreement in a pose. The action renders as
        "<name> <action>" with no conjugation, so a base-form verb
        ("fill an empty pint") renders wrong ("Sable fill ..."). Conjugate
        the FIRST word of each clause (split on and/then/comma) to third-
        person singular when it looks like a base verb — skipping words
        already conjugated (-s), participles (-ing), past tense (-ed), and
        non-verb clause-openers. Quoted speech is left alone. Small RP
        models (Rocinante) write base-form pose verbs where a 24B wrote
        '-s' forms; code fixes it either way."""
        from world.grammar import conjugate_third_person

        def _fix_clause(clause):
            m = re.match(r"(\s*)([A-Za-z]+)(.*)$", clause, re.S)
            if not m:
                return clause
            lead, word, rest = m.group(1), m.group(2), m.group(3)
            lw = word.lower()
            if (lw in self._NOT_A_LEADING_VERB
                    or lw.endswith(("s", "ing", "ed"))):
                return clause
            return lead + conjugate_third_person(word) + rest

        def _fix(seg):
            # split on clause boundaries, KEEPING the delimiters
            parts = re.split(r"(\s+and\s+|\s+then\s+|,\s+)", seg)
            parts[0::2] = [_fix_clause(c) for c in parts[0::2]]
            return "".join(parts)

        chunks = action.split('"')
        chunks[0::2] = [_fix(c) for c in chunks[0::2]]
        return '"'.join(chunks)

    def _selfify_action(self, action):
        """Convert first-person SELF references in an action to the NPC's
        third-person pronoun so the pose renders under the name-prepend
        ("lowering my voice" -> "lowering her voice"). Only the possessive/
        object/reflexive forms (my/mine/me/myself) are rewritten — always
        unambiguously the NPC in its own action; a subject 'I' is left alone
        (a well-formed predicate omits it, and 'I'->'she' risks a double
        subject). Quoted speech woven in is skipped."""
        from world.grammar import GENDER_MAP, transform_pronoun
        gender = GENDER_MAP.get(getattr(self, "gender", "neutral"), "neutral")

        def _rewrite(seg):
            return re.sub(
                r"\b(my|mine|me|myself)\b",
                lambda m: transform_pronoun(m.group(0), "third", gender),
                seg, flags=re.I)

        chunks = action.split('"')
        chunks[0::2] = [_rewrite(c) for c in chunks[0::2]]
        return '"'.join(chunks)

    #: Self-gesture verbs + body parts where "<verb> your <part>" is the NPC
    #: moving its OWN body, never handling the patron's. The model reaches for
    #: "your" here because the prompt addresses IT as "you" (observed live:
    #: "cock your head" → the second-person resolver mis-mapped it onto the
    #: patron, so a bystander would read "cocks the patron's head"). DELIBERATELY
    #: CONSERVATIVE: only verbs with no plausible directed reading. Ambiguous
    #: ones (tilt/lower/raise/lift/cup/stroke/take/press) have real patron-
    #: directed uses — a bartender tilting a patron's chin up — and are LEFT to
    #: fall through to _resolve_second_person on purpose.
    _REFLEXIVE_GESTURE_VERBS = ("cock", "crane", "crack", "cant", "bob", "nod",
        "shake", "roll", "scratch", "jerk", "wag", "duck", "incline", "arch")
    _REFLEXIVE_GESTURE_PARTS = ("head", "neck", "chin", "jaw", "brow", "brows",
        "eyebrow", "eyebrows", "shoulder", "shoulders", "temple", "temples",
        "eye", "eyes", "knuckle", "knuckles")

    def _selfify_reflexive_gesture(self, action):
        """Rewrite a reflexive self-gesture the model wrote in the second person
        ("cock your head") to the NPC's own possessive ("cocks his head"), BEFORE
        _resolve_second_person claims that "your" for the patron. Gated on a tight
        verb+part matrix so genuinely patron-directed possessives (which the
        resolver SHOULD map) are untouched. Quoted speech is skipped."""
        from world.grammar import GENDER_MAP
        gender = GENDER_MAP.get(getattr(self, "gender", "neutral"), "neutral")
        poss = {"male": "his", "female": "her"}.get(gender, "their")
        verbs = "|".join(self._REFLEXIVE_GESTURE_VERBS)
        parts = "|".join(self._REFLEXIVE_GESTURE_PARTS)
        # <verb>(s) [one optional adjective] your [one optional adjective] <part>
        pat = re.compile(
            rf"\b((?:{verbs})(?:es|s)?\s+(?:\w+\s+)?)your(\s+(?:\w+\s+)?(?:{parts})\b)",
            re.I)

        def _rewrite(seg):
            return pat.sub(lambda m: m.group(1) + poss + m.group(2), seg)

        chunks = action.split('"')
        chunks[0::2] = [_rewrite(c) for c in chunks[0::2]]
        return '"'.join(chunks)

    def _resolve_second_person(self, action, patron):
        """Resolve the model's second-person slips onto the patron's handle.

        Everything the model reads renders "you" as the NPC itself, so it
        drifts into calling its interlocutor "you"/"your" in its own ACTION.
        A literal "you" in a broadcast pose is wrong for every observer but
        the target (a bystander reads it as themselves). Rewriting it to the
        patron's handle (the PERCEPTION wording) lets the emote engine's
        char-ref matcher resolve it per-observer — the target still reads
        "you"/"your", a bystander reads the name THEY know. Quoted speech is
        dialogue and stays verbatim; contractions (you've) are left alone."""
        try:
            handle = self._address_handle(patron)
        except Exception:  # noqa: BLE001
            return action
        if not handle:
            return action

        def _rewrite(seg):
            seg = re.sub(r"\byours?\b", f"{handle}'s", seg, flags=re.I)
            return re.sub(r"\byou(?:rself)?\b(?!['’])", handle, seg,
                          flags=re.I)

        chunks = action.split('"')
        chunks[0::2] = [_rewrite(c) for c in chunks[0::2]]
        return '"'.join(chunks)

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
