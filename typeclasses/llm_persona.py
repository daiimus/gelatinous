"""Compose an NPC persona dict from its live object fields, for the LLM sidecar.

Runs on the reactor (reads ``db`` + identity getters) and returns plain,
JSON-safe data handed to the off-reactor sidecar call (``world/llm/client.py``).
The builder-authored **immutable core** (manner / wants / boundaries) lives in
``db.llm_persona``; everything else is derived from the NPC's real identity so the
model voices *this* character — the same sdesc/longdesc/voice the world perceives.

See ``specs/proposals/LLM_GAMEMASTER_SPEC.md`` §5.2 (persona card).
"""

from evennia.utils.dbserialize import deserialize

from world.grammar import transform_pronoun
from world.identity import get_apparent_gender
from world.voice import get_voice_description, get_voice_ending, voice_phrase


def _self_pronouns(npc) -> str:
    """The NPC's own subject/object pronouns ("he/him") from the SAME canonical
    gender derivation the emote/identity engine uses (``get_apparent_gender`` ->
    ``transform_pronoun``), so the persona never disagrees with how the world
    renders this character's gender. Falls back to they/them on any hiccup."""
    try:
        gender = get_apparent_gender(npc)
        return (f"{transform_pronoun('I', 'third', gender)}/"
                f"{transform_pronoun('me', 'third', gender)}")
    except Exception:  # noqa: BLE001 — never break persona-building over pronouns
        return "they/them"


def build_persona(npc) -> dict:
    """Build the persona dict from the NPC's real fields. Defensive throughout.

    Must run on the reactor (reads db + identity getters). The returned dict is
    inert JSON passed to the sidecar thread — no live objects leak across.
    """
    longdescs = {}
    raw = getattr(npc, "longdesc", None) or {}
    for loc in raw:
        desc = npc.get_longdesc(loc)
        if desc:
            longdescs[loc] = desc

    location = None
    if npc.location:
        location = {
            "name": npc.location.key,
            "desc": getattr(npc.location.db, "desc", None),
        }

    # The bar's real menu, so she knows exactly what she serves (and what she
    # doesn't) — and never fakes pouring something off-list.
    menu = None
    find_bar = getattr(npc, "_find_bar", None)
    if callable(find_bar):
        bar = find_bar()
        bar_menu = (bar.db.menu if bar else None) or npc.db.menu or []
        menu = [r.get("name") for r in bar_menu if r.get("name")] or None

    return {
        "sdesc": npc.get_sdesc(),
        "longdescs": longdescs,
        "skintone": getattr(npc.db, "skintone", None),
        "height": npc.height,
        "build": npc.build,
        "sex": npc.sex,
        "pronouns": _self_pronouns(npc),   # canonical self-gender (he/him, …)
        "species": npc.species,
        "voice": voice_phrase(npc),
        "voice_description": get_voice_description(npc),
        "voice_ending": get_voice_ending(npc),
        "location": location,
        "menu": menu,
        # deserialize → plain dict/list (the seed's nested mes_example is a
        # _SaverDict/_SaverList off the DB, which json.dumps can't serialize).
        "persona_seed": deserialize(npc.db.llm_persona) or {},
    }
