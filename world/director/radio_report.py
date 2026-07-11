"""Player radio reports become REAL dispatches (2026-07-11, user call:
"they acknowledge but don't do anything").

The witness pipeline proved the machinery: an event raised at a room
rolls actual security units through tracked assignments. This module
gives PLAYER traffic on the emergency band the same teeth. The console
hears a transmission, a structured civic-lane verdict classifies it
(constrained decoding — the reply physically cannot fail to parse), and
the DETERMINISTIC layer does everything that matters: both verdict
signals must agree, the named location resolves against real room names
in plain code, the scene debounces, and ``raise_event`` dispatches.
The model reports what was SAID, never what is true.

Consequences kept on purpose:

* **The caller is unverified.** A false report rolls real units —
  swatting is a mechanic, not a bug: drain the pool, draw units off a
  target. The finite pool and the on-air "no units available" make the
  cost audible.
* **Failure is silence.** Refusal, timeout, nonsense, no location,
  debounce — no dispatch. The voice lane's acknowledgment is flavour;
  only this lane moves steel, and the deterministic ack ("Dispatch
  copies — an assault at <room>. 2 units responding.") is the honest
  receipt that it did.
* **NPC traffic never re-dispatches.** Witness reports raise their
  event directly (world/director/witness.py); classifying their own
  air-traffic would double-roll the same incident.
"""

from __future__ import annotations

import re
import time

#: One radio dispatch per (room, event type) inside this window — the
#: same scene debounce discipline as the witness pipeline.
RADIO_REPORT_DEBOUNCE = 120.0

_RECENT: dict = {}

#: Model verdict category -> (WorldEvent type, severity). Unverified
#: phone-ins run one notch softer than witnessed crimes: a voice on the
#: band is cheaper evidence than an NPC who saw it.
REPORTED_EVENTS = {
    "assault": ("assault", 2),
    "disturbance": ("disturbance", 1),
    "fire": ("fire", 2),
    "medical": ("disturbance", 1),   # wellness check — no medic role yet
    "theft": ("crime", 1),
}

#: The classifier contract (proven end-to-end 2026-07-11): constrained
#: decoding via the standard OpenAI response_format — enums held,
#: booleans real, json.loads safe by construction. ``x-order`` steers a
#: small model's field-by-field reasoning.
DISPATCH_VERDICT_SCHEMA = {
    "title": "DispatchVerdict",
    "type": "object",
    "x-order": ["is_incident_report", "incident_type", "location_text"],
    # location_text REQUIRED (2026-07-11 probe): optional fields get
    # skipped under constrained decoding ~1-in-3; forcing the field
    # makes extraction 3/3, and a parroted/placeless value just fails
    # resolution into the caller-room fallback. Gate discards the rest.
    "required": ["is_incident_report", "incident_type", "location_text"],
    "properties": {
        "is_incident_report": {
            "type": "boolean",
            "description": ("True only if the caller is reporting a "
                            "crime, fight, fire, injury, or emergency "
                            "happening somewhere."),
        },
        "incident_type": {
            "type": "string",
            "enum": ["assault", "disturbance", "fire", "medical",
                     "theft", "none"],
            "description": ("The category of the reported incident; "
                            "none if not a report."),
        },
        "location_text": {
            "type": "string",
            "description": ("The place the caller names for the "
                            "incident, exactly as they said it. Empty "
                            "string if no place is named."),
        },
    },
}

CLASSIFY_INSTRUCTIONS = (
    "You classify radio traffic for a dispatcher in a fictional "
    "cyberpunk roleplaying game. Decide whether the caller is reporting "
    "a real incident and extract the category and any location they "
    "name. Chatter, jokes, questions, and requests for goods are not "
    "incident reports. Figurative language, wordplay, and hypotheticals "
    "are not incidents — only a concrete event happening somewhere "
    "right now counts (a 'fire' that boils tea is not a fire)."
)

#: Words that carry no place information.
_STOPWORDS = frozenset(
    "the a an in at on of and by near to inside outside".split())


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", str(text or "").lower())
            if t not in _STOPWORDS]


def _candidate_rooms():
    """Every room in the world (typeclass-path scoped query)."""
    from evennia.objects.models import ObjectDB
    return list(ObjectDB.objects.filter(
        db_typeclass_path__startswith="typeclasses.rooms"))


def resolve_location(location_text, rooms):
    """The room the caller named, or None — plain token matching, no
    model. Coverage = how much of what the caller said appears in a
    room's name; the best room must cover more than half. Ties break
    toward the tightest name, then the lowest id (deterministic)."""
    loc = set(_tokens(location_text))
    if not loc:
        return None
    best = None
    for room in rooms:
        name = set(_tokens(getattr(room, "key", "")))
        if not name:
            continue
        hit = loc & name
        coverage = len(hit) / len(loc)
        precision = len(hit) / len(name)
        score = (coverage, precision, -(getattr(room, "id", 0) or 0))
        if coverage > 0.5 and (best is None or score > best[0]):
            best = (score, room)
    return best[1] if best else None


def consider_radio_report(console, speaker, speech, on_result=None):
    """Classify player traffic; a confirmed report raises a real event.
    Not gated by the voice lane's answer cooldown — a second report
    inside ten seconds still rolls units even when the operator stays
    silent. Silence on every failure.

    Returns True when a classification is IN FLIGHT — ``on_result
    (verdict, dispatched)`` will fire exactly once on the reactor
    (``(None, None)`` on failure), letting the voice lane speak GROUNDED
    in what dispatch actually did. False = this lane declined (NPC
    traffic, lane disabled); the caller proceeds ungrounded."""
    try:
        from world.llm.client import civic_enabled, request_civic_verdict
        if not civic_enabled():
            return False
        if speaker is None or not speech:
            return False
        db = getattr(speaker, "db", None)
        if (getattr(db, "is_npc", None) is True
                or getattr(db, "llm_driven", None) is True
                or getattr(db, "is_base_station", None) is True):
            return False

        def _report(verdict, dispatched):
            if callable(on_result):
                try:
                    on_result(verdict, dispatched)
                except Exception:  # noqa: BLE001 — voice never breaks units
                    pass

        def on_verdict(verdict):
            dispatched = apply_verdict(verdict, speaker, speech)
            _report(verdict, dispatched)

        request_civic_verdict(
            CLASSIFY_INSTRUCTIONS, f'Radio traffic: "{speech}"',
            DISPATCH_VERDICT_SCHEMA, on_verdict,
            lambda: _report(None, None))
        return True
    except Exception:  # noqa: BLE001 — the report lane never breaks radio
        return False


def apply_verdict(verdict, speaker, speech):
    """The deterministic half: gate, resolve, debounce, dispatch.
    Runs on the reactor (run_async at_return). Returns the dispatched
    list, or None when nothing rolled."""
    try:
        if not isinstance(verdict, dict):
            return None
        # BOTH signals must agree — a small model emits contradictory
        # fields ("report=true, type=none"); either alone rolls nothing.
        if verdict.get("is_incident_report") is not True:
            return None
        mapped = REPORTED_EVENTS.get(verdict.get("incident_type"))
        if mapped is None:
            return None
        event_type, severity = mapped
        room = resolve_location(verdict.get("location_text"),
                                _candidate_rooms())
        if room is None:
            # people report what's in front of them (the witness
            # precedent) — an unresolvable or unnamed place falls back
            # to the caller's own room
            room = getattr(speaker, "location", None)
        if room is None:
            return None
        key = (getattr(room, "id", None) or id(room), event_type)
        now = time.monotonic()
        last = _RECENT.get(key)
        if last is not None and (now - last) < RADIO_REPORT_DEBOUNCE:
            return None
        _RECENT[key] = now
        from world.director.dispatch import WorldEvent, raise_event
        event = WorldEvent(
            type=event_type,
            location=room,
            severity=severity,
            source=speaker,
            payload={"radio_report": True, "traffic": str(speech)[:200],
                     "location_text": verdict.get("location_text")},
        )
        return raise_event(event)
    except Exception:  # noqa: BLE001 — silence
        return None
