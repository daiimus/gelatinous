"""The combat reflex lane (#954 follow-on, user call 2026-07-11).

The big model plays conversation tempo (17-85s a turn); the civic
lane's small on-device model answers in under a second — the only
model that can honestly play a FLINCH. When a combat beat lands, one
elected bystander LLM NPC may bark a single in-character line seconds
later, through the civic lane and the real ``say`` command.

**Input shaping is the load-bearing wall.** The small model's
guardrails pattern-match graphic PHRASING, not events (probed live
2026-07-11: a murder passed; "bleeding heavily... not moving"
refused). So the reflex prompt never sees the witness-detail beat
lines at all — it gets a fixed, category-mapped, deliberately bloodless
rendition from ``REFLEX_BEATS``. The full-detail lines still go where
they always went: the NPC's action buffer, which only the GM lane
reads. No fidelity is lost anywhere that matters, and the guardrail
has nothing to catch.

**Failure mode is silence**, at every layer: refusal, timeout,
nonsense output, cooldown, no eligible bystander — nothing renders.
An NPC that doesn't comment on a fight is indistinguishable from one
choosing not to.

Discipline ledger: deterministic combat stays authoritative (the
reflex is downstream flavour, exception-contained); output through a
real command; bystanders only (combatants have a deterministic combat
AI and a model can't play 6-second rounds); election = lowest dbref
(the radio precedent — no chorus); one reflex per fight (handler
flag) plus a per-NPC time gate; strict ``is True`` checks throughout.
"""

from __future__ import annotations

import time
from random import uniform

from evennia.utils.utils import delay

#: Guardrail-safe beat renditions — the ONLY text the small model sees.
REFLEX_BEATS = {
    "fight_started": "A fight just broke out nearby between two people.",
    "someone_down": ("Someone just went down hard in the fight and "
                     "isn't getting up."),
    "fight_ended": "The fight nearby just broke off.",
}

#: A single NPC won't reflex again within this many seconds.
REFLEX_NPC_COOLDOWN = 90.0

#: The human beat between the event and the bark.
REFLEX_DELAY_MIN, REFLEX_DELAY_MAX = 1.5, 3.0

REFLEX_INSTRUCTIONS = (
    "You are {name}, {identity} in a gritty fictional cyberpunk "
    "roleplaying game. Something just happened near you. Reply with "
    "the ONE short line your character says out loud, in their own "
    "voice. No narration, no asterisks, no quotation marks, no "
    "examples. If your character would stay silent, reply with "
    "exactly: NOTHING"
    # (No example-noun lists: the 3B model parrots them — a probe
    # literally answered "*Bark*". Small models get plain orders.)
)


def _clean_reflex(text):
    """One spoken line or None: first line, stage directions and quote
    marks stripped, declines honoured, length capped."""
    if not text:
        return None
    line = str(text).splitlines()[0].strip()
    # strip *stage directions* wherever they appear
    while "*" in line:
        head, _, rest = line.partition("*")
        _, _, tail = rest.partition("*")
        line = (head + " " + tail).strip()
    line = line.strip().strip('"').strip()
    if not line or line.upper() in ("NOTHING", "NOTHING."):
        return None
    if line.startswith("[") or line.lower().startswith(("as an ai", "i cannot", "i can't")):
        return None
    return line[:160]


def _combatants_of(handler):
    """Everyone currently in the fight (excluded from reflexing)."""
    out = set()
    try:
        from world.combat.constants import DB_CHAR
        for entry in (handler.db.combatants or []):
            char = entry.get(DB_CHAR)
            if char is not None:
                out.add(char)
    except Exception:  # noqa: BLE001
        pass
    return out


def _elect_bystander(location, excluded):
    """The one LLM-driven, conscious, perceiving bystander who reacts —
    lowest dbref (the radio election precedent), off cooldown."""
    from world.perception import can_hear, can_see
    candidates = []
    try:
        contents = list(getattr(location, "contents", None) or [])
    except Exception:  # noqa: BLE001
        return None
    now = time.time()
    for obj in contents:
        try:
            if obj in excluded:
                continue
            if getattr(getattr(obj, "db", None), "llm_driven",
                       None) is not True:
                continue
            if callable(getattr(obj, "is_dead", None)) and obj.is_dead():
                continue
            if (callable(getattr(obj, "is_unconscious", None))
                    and obj.is_unconscious()):
                continue
            if not (can_see(obj) or can_hear(obj)):
                continue
            last = getattr(obj.ndb, "last_combat_reflex", None) or 0
            if now - float(last) < REFLEX_NPC_COOLDOWN:
                continue
            candidates.append(obj)
        except Exception:  # noqa: BLE001
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda o: getattr(o, "id", 0) or 0)


def fire_combat_reflex(handler, location, category, exclude=()):
    """Maybe bark: one elected bystander, one reflex per fight, the
    guardrail-safe beat only, silence on every failure."""
    try:
        from world.llm.client import civic_enabled, request_civic_line
        if not civic_enabled():
            return
        beat = REFLEX_BEATS.get(category)
        if not beat or location is None:
            return
        if handler is not None:
            if getattr(getattr(handler, "ndb", None), "combat_reflex_done",
                       None) is True:
                return
        excluded = set(exclude) | _combatants_of(handler)
        npc = _elect_bystander(location, excluded)
        if npc is None:
            return
        if handler is not None:
            handler.ndb.combat_reflex_done = True
        npc.ndb.last_combat_reflex = time.time()

        persona = dict(getattr(npc.db, "llm_persona", None) or {})
        instructions = REFLEX_INSTRUCTIONS.format(
            name=persona.get("name") or npc.key,
            identity=(persona.get("description")
                      or "a bystander")[:160])

        def _deliver():
            try:
                # re-check at speak time: downed mid-beat = silence
                if (callable(getattr(npc, "is_dead", None)) and npc.is_dead()) \
                        or (callable(getattr(npc, "is_unconscious", None))
                            and npc.is_unconscious()):
                    return

                def on_reply(text):
                    line = _clean_reflex(text)
                    if line:
                        try:
                            npc.execute_cmd(f"say {line}")
                        except Exception:  # noqa: BLE001
                            pass

                request_civic_line(instructions, beat, on_reply,
                                   lambda: None)
            except Exception:  # noqa: BLE001 — silence
                pass

        delay(uniform(REFLEX_DELAY_MIN, REFLEX_DELAY_MAX), _deliver)
    except Exception:  # noqa: BLE001 — the reflex lane never breaks combat
        pass
