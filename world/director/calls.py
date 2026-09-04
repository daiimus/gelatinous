"""The call — what somebody phoned in, kept where everyone can read it.

A report used to be a MOMENT. `raise_event` fired, units walked to a
room, and the thing itself was gone: `WorldEvent` is a dataclass held
alive only by the assignment referencing it. There was no object
anywhere representing "the incident phoned in at 17:48". You could not
point at it, query it, or close it.

So every participant held one fragment and none could see the others'.
A witnessed crime handed responders a BOLO to match against; a
phoned-in report handed them nothing, and the caller's own words sat
unread in the event payload while the robot swept the scene and emoted
"finds nothing that matches its report" — honestly, because it had no
report. Meanwhile the dispatcher's grounding was an ndb blob that
lived exactly one turn, so a model asked about a call thirty seconds
old had to invent an answer.

A call is the shared record they all read and write: the ticket rather
than an order shouted across a kitchen.

Stored the way `director_incidents` already stores its rolling log —
`ServerConfig`, capped, pruned on write, holding ROOM IDS rather than
room objects so a global never pins live objects. Persistent across
reloads, which a call should be and a stimulus should not: an incident
outlives the moment it was reported, and one day decking will want to
read (and forge) exactly this file.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

#: The ledger, and how much of it we keep. A call is small; fifty is
#: several busy nights and bounds the attribute either way.
_CALLS_KEY = "director_calls"
MAX_CALLS = 50

#: How long a call stays answerable before it is stale history.
CALL_WINDOW = 3600.0

#: What a caller's words say about a silhouette. `build_bolo` snapshots
#: a real body's `height`/`build`; a voice on the radio can only offer
#: the same axes in ordinary words, which is the honest fidelity — a
#: description gets you a "low"-confidence match, never a positive ID.
#: Nobody phones in a presentation hash.
_BUILD_WORDS = {
    "slight": ("slight", "slim", "svelte", "skinny", "scrawny", "waifish",
               "wiry", "thin", "bony"),
    "lean": ("lean", "lanky", "rangy", "spare", "narrow"),
    "athletic": ("athletic", "built", "fit", "muscular", "broad-shouldered"),
    "average": ("average", "ordinary", "normal", "medium"),
    "stocky": ("stocky", "thickset", "burly", "square", "solid", "chunky"),
    "heavyset": ("heavyset", "heavy", "big", "large", "fat", "huge",
                 "enormous", "massive"),
}
_HEIGHT_WORDS = {
    "short": ("short", "little", "small", "tiny", "stumpy"),
    "below-average": ("shortish", "smallish"),
    "above-average": ("tallish", "biggish"),
    "tall": ("tall", "towering", "lofty", "long", "giant"),
}

#: Garments a caller might name, and the colours they come in. What
#: people ACTUALLY lead with — "a guy in a black trenchcoat" — and what
#: a BOLO had nowhere to put, so the most useful sentence anybody says
#: was discarded on arrival (#2250).
#:
#: Matched as (colour, noun) against what the person is really wearing,
#: coarse on purpose: two black coats read the same across a street.
_GARMENTS = (
    "trenchcoat", "coat", "jacket", "windbreaker", "parka", "poncho",
    "cardigan", "sweater", "hoodie", "shirt", "vest", "suit", "dress",
    "skirt", "trousers", "pants", "jeans", "boots", "shoes", "hat",
    "cap", "helmet", "mask", "goggles", "scarf", "gloves", "overalls",
    "apron", "robe", "uniform",
)
_COLOURS = (
    "black", "white", "grey", "gray", "red", "blue", "green", "yellow",
    "orange", "purple", "brown", "tan", "charcoal", "navy", "olive",
    "crimson", "scarlet", "silver", "gold", "pink", "beige", "khaki",
)

#: Words that mean "I saw a person but can tell you nothing about them".
#: Distinguishing these from silence matters: "someone" is a report with
#: no description, and a unit can act on knowing that.
_ANONYMOUS = ("someone", "somebody", "some guy", "a guy", "a man",
              "a woman", "a person", "people", "they", "a dude",
              "a fella", "a bloke")


def _garments_named(low: str) -> set:
    """Colour+garment pairs the caller mentioned.

    A colour only counts when it is attached to a garment — "black" on
    its own is a mood, a night, or a joke, and only "black coat" is a
    description. An unqualified garment still counts with no colour,
    because "he had a helmet on" is worth something.
    """
    found = set()
    for noun in _GARMENTS:
        for m in re.finditer(rf"\b{noun}s?\b", low):
            head = low[max(0, m.start() - 24):m.start()]
            colour = ""
            for word in _COLOURS:
                if re.search(rf"\b{word}\b", head):
                    colour = "grey" if word == "gray" else word
            found.add((colour, noun))
    return found


#: Words that establish a PERSON is what is being described. The height
#: and build vocabularies are ordinary English — `heavy`, `big`, `little`,
#: `long`, `short`, `solid` — so an axis word alone is not evidence anyone
#: was described at all: "a little help here" is not a short suspect
#: (#2807). Naming what somebody WORE counts too, and is handled beside
#: this in `describe_suspect`.
_PERSON_WORDS = frozenset("""
guy guys man men woman women person people someone somebody anyone anybody
he she they him her them his hers their kid kids girl boy lady gent dude
fella bloke stranger colonist suspect perp perpetrator attacker assailant
victim
""".split())


def _names_a_person(words) -> bool:
    """True when the caller referred to a person at all."""
    return any(re.search(rf"\b{re.escape(w)}\b", words) for w in _PERSON_WORDS)


def _match_axis(words, table) -> Optional[str]:
    for axis, vocab in table.items():
        for word in vocab:
            if re.search(rf"\b{re.escape(word)}\b", words):
                return axis
    return None


def describe_suspect(speech: str) -> dict:
    """What the caller told us about the person, if anything.

    Returns ``{"bolo": {...}|None, "text": str, "anonymous": bool}``.

    * ``bolo`` is the silhouette a responder can match on — height
      and/or build, never a uid. `match_bolo` reads it as "low"
      confidence, which is exactly right for hearsay.
    * ``text`` is the caller's own phrasing, kept verbatim so the
      dispatcher can repeat what she was actually told instead of
      inventing a description (#2240 — she once put "white male inside
      welfare gate" on the air, unprompted).
    * ``anonymous`` means a person was reported with nothing to go on.
      That is a FACT, not a blank: the unit is hoping to catch them at
      it, and should be told so.
    """
    low = " ".join(str(speech or "").lower().split())
    if not low:
        return {"bolo": None, "text": "", "anonymous": False}

    build = _match_axis(low, _BUILD_WORDS)
    height = _match_axis(low, _HEIGHT_WORDS)
    worn = _garments_named(low)
    anonymous = any(re.search(rf"\b{re.escape(w)}\b", low)
                    for w in _ANONYMOUS)

    bolo = None
    # An axis word is only a silhouette if somebody was being described.
    # A person-noun establishes that; so does naming a garment, but a
    # garment ALONE ("my jacket got stolen") describes no one, so it
    # needs an axis beside it (#2807).
    describes_a_person = (
        (_names_a_person(low) and (height or build or worn))
        or ((height or build) and worn)
    )
    if describes_a_person:
        # the same shape `build_bolo` produces, on the channel that can
        # carry the least: a voice on the radio, which may also be
        # vague, mistaken, or lying
        bolo = {"uid": None, "height": height, "build": build,
                "worn": worn, "via": "radio", "by": None}

    return {"bolo": bolo, "text": str(speech or "").strip()[:200],
            "anonymous": anonymous and bolo is None}


# ------------------------------------------------------------- the ledger

def _load() -> list:
    from evennia.server.models import ServerConfig
    return list(ServerConfig.objects.conf(_CALLS_KEY) or [])


def _save(calls) -> None:
    from evennia.server.models import ServerConfig
    ServerConfig.objects.conf(_CALLS_KEY, calls[-MAX_CALLS:])


def open_call(*, said: str, kind: str, room: Any, operator: Any = None,
              caller: Any = None, suspect: dict = None,
              now: float = None) -> dict:
    """Log a call and return it. Never raises — a ledger that fails
    must not stop units rolling."""
    try:
        now = time.time() if now is None else now
        calls = _load()
        call = {
            "id": (calls[-1]["id"] + 1) if calls else 1,
            "t": now,
            "said": str(said or "")[:200],
            "kind": kind,
            "room": getattr(room, "id", None),
            "where": getattr(room, "key", None),
            "operator": getattr(operator, "key", None),
            "voice": _voice_of(caller),
            "suspect": suspect or {"bolo": None, "text": "",
                                   "anonymous": False},
            "units": [],
            "status": "open",
        }
        calls.append(call)
        _save(calls)
        return call
    except Exception:  # noqa: BLE001 — the ledger is never load-bearing
        return {}


def record_dispatch(call_id: int, units) -> None:
    """Note which units went, so the call can be closed against them."""
    try:
        calls = _load()
        for call in calls:
            if call.get("id") == call_id:
                call["units"] = [getattr(u, "id", None) for u in (units or ())]
                call["status"] = "rolling" if call["units"] else "no units"
                _save(calls)
                return
    except Exception:  # noqa: BLE001
        pass


def close_call(call_id: int, outcome: str, by: Any = None) -> Optional[dict]:
    """Settle a call: ``handled``, ``unfounded``, whatever the scene was.

    This is the half that never existed. A responder finding nothing had
    nowhere to say so, so a false report cost the colony two units and
    left no trace — nothing to answer for, nothing to hold against a
    caller, nothing for a dispatcher to put on the air.
    """
    try:
        calls = _load()
        for call in calls:
            if call.get("id") == call_id:
                call["status"] = str(outcome)
                call["closed_t"] = time.time()
                call["closed_by"] = getattr(by, "key", None)
                _save(calls)
                return call
    except Exception:  # noqa: BLE001
        pass
    return None


def get_call(call_id: int) -> Optional[dict]:
    for call in _load():
        if call.get("id") == call_id:
            return call
    return None


def open_calls(window: float = CALL_WINDOW) -> list:
    """Calls still live enough to be asked about."""
    now = time.time()
    return [c for c in _load()
            if now - float(c.get("t", 0)) < window
            and c.get("status") in ("open", "rolling", "no units")]


def _voice_of(caller: Any) -> Optional[str]:
    """The caller by VOICE, never by face — dispatch never saw them."""
    if caller is None:
        return None
    try:
        from world.voice import get_apparent_voice_uid
        return get_apparent_voice_uid(caller)
    except Exception:  # noqa: BLE001
        return None
