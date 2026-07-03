"""Civilians — the ambient population layer.

The dispatch spec's §3/§4 made concrete for ordinary people: a civilian
is a **role** (data-authored below) wearing real clothes, drifting
between a few **haunts** at a stroll (the same beat machinery as
security, at a slower ``patrol_cadence``), carrying **100–500 tokens**
(§5.2 — a person is also a mugging target), with a **persona** so the
LLM can puppet them the moment a player intersects them, and a
role-flavored **ambient beat** on every waypoint arrival (the seed of
the §6 deterministic vocabulary).

Everything is tagged ``("civilian", "director")`` so the population can
be listed, updated, and **purged on the fly** (`@civilians`) while the
layer is being refined — refinement is the point right now.
"""

from __future__ import annotations

from random import choice, randint, sample
from typing import Any

#: Management tag — every spawned civilian carries it; purge is scoped to it.
CIV_TAG = "civilian"
CIV_TAG_CATEGORY = "director"

#: Civilians act every Nth heartbeat (45s) — a drift, not a march.
CADENCE_RANGE = (3, 6)
#: How many haunts a civilian drifts between.
HAUNTS_RANGE = (2, 4)
#: How far from their anchor haunts may be sampled (straight-line rooms).
HAUNT_RADIUS = 6
#: §5.2 pockets: worth mugging, not worth farming.
TOKEN_RANGE = (100, 500)


# --------------------------------------------------------------------------
# Roles (data-authored; add a dict, get a population)
# --------------------------------------------------------------------------

CIVILIAN_ROLES: dict[str, dict] = {
    "laborer": {
        "wardrobe": ["TACTICAL_JUMPSUIT", "COMBAT_BOOTS"],
        "ambient": [
            "rolls a shoulder that clearly hasn't forgiven the last shift.",
            "checks a chit against a pocket ledger, lips moving.",
            "scrapes grey colony grit off a boot heel against the curb.",
            "stretches until something in their back gives with a pop.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a shift laborer",
            "description": "A worked-down colonist in a company jumpsuit, hands past the point where gloves would matter.",
            "personality": "Tired, plainspoken, allergic to wasted words. Counts hours the way other people count money.",
            "manner": "short declaratives; work slang; talks to strangers like they might be from payroll",
            "wants": "the shift to end, the chit to clear, and nobody to make today interesting",
            "boundaries": "gossip about the company where a stranger can hear; volunteer for anything",
        },
    },
    "vendor": {
        "wardrobe": ["COTTON_TSHIRT", "BLUE_JEANS"],
        "ambient": [
            "recounts a fold of grubby chits, twice, frowning both times.",
            "calls a price at a passerby, then halves it under their breath.",
            "rearranges a battered tray of goods with surprising tenderness.",
            "scans the street the way only someone with unlicensed stock does.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a street vendor",
            "description": "A wiry fixture of the street with a tray of odds and ends, eyes that price you on approach.",
            "personality": "Quick, transactional, friendlier the closer you stand to buying. Knows the street's rhythms cold.",
            "manner": "patter and price-talk; compliments that cost nothing; goes vague when questions get official",
            "wants": "foot traffic, dry weather, and security staying on the far side of the bridge",
            "boundaries": "name suppliers; hold anything for anyone; leave the tray unattended",
        },
    },
    "drifter": {
        "wardrobe": ["COTTON_TSHIRT", "BLUE_JEANS"],
        "ambient": [
            "reads the street signs like they've stopped meaning anything.",
            "warms both hands on a cup that has plainly been empty a while.",
            "picks something off the pavement, considers it, pockets it.",
            "watches the security patrol pass with a very practiced blankness.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a drifter",
            "description": "Someone the colony stopped scheduling: layered clothes gone one shade too uniform, a bag that is everything they own.",
            "personality": "Watchful, unhurried, oddly well-informed — the street is a full-time occupation. Pride intact, thin as it's worn.",
            "manner": "oblique answers; streetwise fatalism; warms up only if treated like a person",
            "wants": "a dry doorway, a token nobody misses, one day without being moved along",
            "boundaries": "beg outright; say where they sleep; touch anyone first",
        },
    },
    "clerk": {
        "wardrobe": ["COTTON_TSHIRT", "BLUE_JEANS", "COMBAT_BOOTS"],
        "ambient": [
            "thumbs through a dogeared manifest, sighing at page two.",
            "mutters a running total that keeps coming out wrong.",
            "checks the time against two different devices, trusting neither.",
            "straightens their collar as if the depot could see them from here.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a depot clerk",
            "description": "A neat-adjacent colonist with ledger-cramped hands and the posture of someone perpetually five minutes late.",
            "personality": "Fussy, precise, quietly overwhelmed. Finds comfort in numbers and none in people.",
            "manner": "over-explains small things; cites procedure; flusters under direct questions",
            "wants": "columns that balance, a supervisor who stays upstairs, lunch uninterrupted",
            "boundaries": "discuss the depot's inventory or schedules; sign anything; be hurried",
        },
    },
}


def ambient_beat(npc: Any) -> str | None:
    """A role-flavored idle line for the waypoint hook, or ``None``."""
    role = getattr(getattr(npc, "db", None), "role", None)
    spec = CIVILIAN_ROLES.get(role or "")
    if not spec:
        return None
    return choice(spec["ambient"])


# --------------------------------------------------------------------------
# Spawning
# --------------------------------------------------------------------------

def spawn_civilian(role: str, anchor: Any) -> Any | None:
    """Materialize one *role* civilian anchored at *anchor*: full human
    identity + flavor, dressed from the role wardrobe (worn via the real
    ``wear`` command), tokens in pocket, persona seeded for the LLM,
    haunts sampled around the anchor, on a slow drift cadence. Returns
    the civilian (or ``None`` on a bad role/anchor)."""
    spec = CIVILIAN_ROLES.get(role)
    if spec is None or anchor is None:
        return None
    from random import randint as _randint
    from evennia import create_object
    from evennia.prototypes.spawner import spawn as proto_spawn
    from world.identity import BUILDS, HAIR_COLORS, HAIR_STYLES, HEIGHTS
    from world.mob_flavor import apply_random_flavor
    from world.namebank import (
        FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE, FIRST_NAMES_MALE, LAST_NAMES,
    )
    from world.spatial import rooms_within

    sex = choice(["male", "female", "ambiguous"])
    first = {"male": FIRST_NAMES_MALE, "female": FIRST_NAMES_FEMALE,
             "ambiguous": FIRST_NAMES_AMBIGUOUS}[sex]
    npc = create_object(
        typeclass="typeclasses.llm_npc.LLMNpc",
        key=f"{choice(first)} {choice(LAST_NAMES)}",
        location=anchor, home=anchor,
    )
    npc.sex = sex
    npc.height = choice(HEIGHTS)
    npc.build = choice(BUILDS)
    if randint(1, 5) > 1:
        npc.hair_color = choice(HAIR_COLORS)
        npc.hair_style = choice(HAIR_STYLES)
    npc.grit = _randint(1, 3)
    npc.resonance = _randint(1, 3)
    npc.intellect = _randint(1, 3)
    npc.motorics = _randint(1, 3)
    apply_random_flavor(npc)   # sdesc + @longdescs + look_place

    # Role, management tag, pockets, LLM persona.
    npc.db.role = role
    npc.tags.add(CIV_TAG, category=CIV_TAG_CATEGORY)
    npc.db.tokens = randint(*TOKEN_RANGE)
    npc.db.llm_persona = dict(spec["persona"])
    npc.db.llm_driven = True

    # Wardrobe — spawned into inventory, worn through the real command.
    for proto in spec["wardrobe"]:
        try:
            item = proto_spawn(proto)[0]
            item.move_to(npc, quiet=True)
            npc.execute_cmd(f"wear {item.key}")
        except Exception:  # noqa: BLE001 — a missing garment isn't fatal
            continue

    # Haunts: a few nearby rooms, drifted between at a stroll.
    npc.db.post = anchor
    try:
        nearby = rooms_within(anchor, HAUNT_RADIUS)
    except Exception:  # noqa: BLE001
        nearby = []
    if nearby:
        count = min(randint(*HAUNTS_RANGE), len(nearby))
        npc.db.patrol_beat = sample(nearby, count)
    npc.db.patrol_cadence = randint(*CADENCE_RANGE)
    return npc


# --------------------------------------------------------------------------
# Management (the refine-on-the-fly surface)
# --------------------------------------------------------------------------

def all_civilians() -> list:
    """Every live civilian (tag-scoped — nothing else can be caught)."""
    from evennia.objects.models import ObjectDB
    return list(ObjectDB.objects.filter(
        db_tags__db_key=CIV_TAG, db_tags__db_category=CIV_TAG_CATEGORY))


def purge_civilians(role: str | None = None) -> int:
    """Delete civilians (optionally one *role* only). Safe by
    construction: only the ``civilian:director`` tag population is
    touched — PCs and working NPCs can never carry it. Inventories
    (their clothes) go with them."""
    n = 0
    for npc in all_civilians():
        if role and getattr(npc.db, "role", None) != role:
            continue
        try:
            for item in list(npc.contents):
                item.delete()
            npc.delete()
            n += 1
        except Exception:  # noqa: BLE001 — one bad row must not stop a purge
            continue
    return n
