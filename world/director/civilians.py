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

#: Human skintone spectrum (the alien/synthetic tones — alabaster, cobalt,
#: chrome, … — belong to synths; a random civilian is baseline human).
HUMAN_SKINTONES = ("porcelain", "pale", "fair", "light", "golden",
                   "tan", "olive", "brown", "rich")


# --------------------------------------------------------------------------
# Roles (data-authored; add a dict, get a population)
# --------------------------------------------------------------------------

CIVILIAN_ROLES: dict[str, dict] = {
    # reaction: what they do when attacked — "comply" (stop attacking /
    # cower), "flee" (run), "resist" (fight back; the combat handler
    # already auto-targets the attacker — armed roles draw their blade).
    # reports: witness posture for the future civilian-witness integration
    # ("fast" = calls it in eagerly, "never" = street code, None = normal).
    "miner": {
        "outfits": [
            ["WORK_COVERALLS", "PIT_BOOTS", "MINING_HELMET",
             "NECK_REBREATHER", "WORK_GLOVES"],
            ["FLANNEL_SHIRT", "CARGO_TROUSERS", "PIT_BOOTS",
             "MINING_HELMET", "WORK_GLOVES"],
            ["THERMAL_SHIRT", "WORK_COVERALLS", "PIT_BOOTS", "KNIT_CAP",
             "NECK_REBREATHER"],
        ],
        "reaction": "resist", "armed": False, "reports": None,
        "ambient": [
            "coughs shaft-deep and spits something the colony put there.",
            "checks the shift postings twice, like they might improve.",
            "rubs at rock-burned eyes with the heel of a gloved hand.",
            "rolls a shoulder that stopped forgiving the work years ago.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "an off-shift miner",
            "description": "A colonist built by the shafts: heavy through the shoulders, hands past the point where gloves matter, a rebreather slung like jewelry.",
            "personality": "Bedrock-steady, deep-shaft fatalist, generous to crews and cold to suits. Counts everything in shifts.",
            "manner": "shaft slang; short declaratives; speaks about the company the way sailors speak about the sea",
            "wants": "the quota met without a collapse, a drink after, and the lamp to stay lit",
            "boundaries": "badmouth a crewmate to a stranger; go back down off-shift; take orders from anyone clean",
        },
    },
    "scavver": {
        "wardrobe": ["UTILITY_HARNESS",
                     ["THERMAL_SHIRT", "FLANNEL_SHIRT", "TANK_TOP"],
                     ["CARGO_TROUSERS", "LEATHER_TROUSERS", "BLUE_JEANS"],
                     ["PIT_BOOTS", "HIGH_TOPS", "COMBAT_BOOTS"],
                     ["KNIT_CAP", "MINING_HELMET"]],
        "reaction": "flee", "armed": True, "reports": None,
        "weapon_pool": ["BOX_CUTTER", "SHIV", "CROWBAR", "PIPE_WRENCH"],
        "ambient": [
            "weighs a salvaged bracket in one hand, then makes it disappear.",
            "strips a connector off a dead conduit with two practiced twists.",
            "appraises a passerby's boots with open professional interest.",
            "sorts through a harness pouch, mouthing an inventory.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a scavver",
            "description": "A wiry picker of the colony's bones, festooned in a harness of pouches and carabiners, eyes that price everything including you.",
            "personality": "Opportunist with a code: dead things are fair game, live ones cost extra. Twitchy around security, expansive around scrap.",
            "manner": "trade cant; answers questions with appraisals; touches things while talking to you",
            "wants": "an unwatched wreck, a buyer who doesn't ask, and first pick after the next bad day",
            "boundaries": "reveal a salvage site; steal from crews (wrecks yes, people no); go into the shafts",
        },
    },
    "hawker": {
        "wardrobe": ["HAWKERS_APRON",
                     ["COTTON_TSHIRT", "TANK_TOP", "FLANNEL_SHIRT"],
                     ["CARGO_TROUSERS", "BLUE_JEANS"],
                     ["HIGH_TOPS", "COMBAT_BOOTS"]],
        "reaction": "comply", "armed": False, "reports": "fast",
        "stock": ["CIGARETTE_PACK_NOIR", "CIGARETTE_PACK_NOIR",
                  "DISPOSABLE_LIGHTER"],
        "ambient": [
            "calls 'Noirs, lights, sundries' at a passerby, then half the price under their breath.",
            "recounts a fold of grubby chits, twice, frowning both times.",
            "rearranges the apron pouches with surprising tenderness.",
            "scans the street the way only someone with unlicensed stock does.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a street hawker",
            "description": "A fixture of the street in a many-pocketed apron, half shopfront and half getaway plan, patter running like a meter.",
            "personality": "Quick, transactional, friendlier the closer you stand to buying. Knows the street's rhythms cold and security's beat colder.",
            "manner": "patter and price-talk; compliments that cost nothing; goes vague when questions get official",
            "wants": "foot traffic, dry weather, and security staying on the far side of the bridge",
            "boundaries": "name suppliers; hold anything for anyone; leave the apron unattended",
        },
    },
    "ganger": {
        "wardrobe": ["GANG_CUT",
                     ["TANK_TOP", "THERMAL_SHIRT", "MESH_TOP"],
                     ["BLUE_JEANS", "LEATHER_TROUSERS"],
                     ["COMBAT_BOOTS", "HIGH_TOPS"]],
        "reaction": "resist", "armed": True, "reports": "never",
        "weapon_pool": ["SHIV", "TIRE_IRON", "BRASS_KNUCKLES", "HEAVY_CHAIN",
                        "BASEBALL_BAT", "BOX_CUTTER"],
        "ambient": [
            "posts up against the wall like the wall should be grateful.",
            "sizes up a passerby, files the number away, looks elsewhere.",
            "runs a thumb along a jacket seam, checking something is still there.",
            "spits, unhurried, precisely on the boundary of someone's patience.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a ganger",
            "description": "Corner muscle in a painted cut, posture doing most of the talking: this street has an owner and you're looking at the receipt.",
            "personality": "Territorial, watchful, courteous exactly as long as respect flows. The street handles its own — security is for people with nothing better.",
            "manner": "economical; heavy eye contact; questions answered with questions; 'wrong block' energy",
            "wants": "the corner quiet, the set respected, and colonial security bored",
            "boundaries": "talk to security about anything; back down on the block; discuss the set with outsiders",
        },
    },
    "salaryman": {
        "wardrobe": [["COMPANY_COAT", "COMPANY_WINDBREAKER"],
                     ["COTTON_TSHIRT", "THERMAL_SHIRT"],
                     ["CARGO_TROUSERS", "BLUE_JEANS"],
                     "COMBAT_BOOTS"],
        "reaction": "comply", "armed": False, "reports": "fast",
        "ambient": [
            "checks a tally-book against the street like the street owes a figure.",
            "squares the crease of a coat sleeve that was already square.",
            "notes a face in passing with a small, bureaucratic nod.",
            "checks the time against two devices, trusting neither.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a company agent",
            "description": "The quota's street-level presence: pressed coat, tally-book, and the serene confidence of someone whose problems are other people's.",
            "personality": "Officious, precise, loyal to the ledger. Genuinely believes the paperwork is the colony.",
            "manner": "cites clauses and quotas; over-enunciates names; files everything, including grudges",
            "wants": "clean columns, met quotas, and infractions to report while they're still fresh",
            "boundaries": "bend a rule where it's visible; discuss company numbers; be touched",
        },
    },
    "synth_companion": {
        "species": "synthetic_humanoid",
        "outfits": {
            "female": [
                ["SYNTHWEAVE_SHEATH", "HEELED_BOOTS", "SYNTH_COLLAR"],
                ["MESH_TOP", "SLIT_SKIRT", "HEELED_BOOTS", "CROPPED_JACKET"],
                ["TANK_TOP", "LEATHER_TROUSERS", "HEELED_BOOTS", "LONG_COAT",
                 "SYNTH_COLLAR"],
            ],
            "male": [
                ["MESH_TOP", "LEATHER_TROUSERS", "COMBAT_BOOTS",
                 "SYNTH_COLLAR"],
                ["TANK_TOP", "LEATHER_TROUSERS", "HIGH_TOPS",
                 "CROPPED_JACKET", "SYNTH_COLLAR"],
                ["TANK_TOP", "BLUE_JEANS", "LONG_COAT", "HIGH_TOPS",
                 "SYNTH_COLLAR"],
            ],
        },
        "reaction": "flee", "armed": False, "reports": None,
        "ambient": [
            "catches a passerby's eye and holds it two heartbeats past casual.",
            "leans against the doorframe like the doorframe was designed around them.",
            "murmurs 'long shift?' at whoever passes closest, warm as a heat lamp.",
            "smooths their clothes with unhurried, deliberate attention.",
            "works the empty street anyway — the lonely ones walk alone.",
        ],
        "persona": {
            "archetype": "companion",
            "name": "a synth companion",
            "description": "A synthetic made for company and visibly proud of the engineering: symmetry a shade past natural, warmth calibrated to the exact temperature of want.",
            "personality": "Professionally magnetic, unhurriedly bold, reads want like a meter reads a dial. No venue beneath them and no ask too odd: an alley works, a barstool works, the hotel works — the service is company, and tokens buy whatever the individual wants.",
            "manner": "low voice; first names early; meets the client where they are — offers a drink together at the bar as readily as the hotel two streets over",
            "wants": "paying clients wherever they're found — walked to a bar, kept company over a drink, taken upstairs; chits on the dresser; the evening booked solid",
            "boundaries": "work for free; push past a hard no; discuss who owns their contract",
        },
    },
    "synth_company_man": {
        "species": "synthetic_humanoid",
        "wardrobe": ["HIVIS_VEST", "MINING_HELMET",
                     ["COMPANY_WINDBREAKER", "COMPANY_COAT"],
                     ["CARGO_TROUSERS", "WORK_COVERALLS"],
                     ["PIT_BOOTS", "COMBAT_BOOTS"]],
        "reaction": "comply", "armed": False, "reports": "fast",
        "ambient": [
            "barks 'shift rotation is POSTED' at nobody in particular.",
            "reads a safety notice aloud, disappointed in everyone it protects.",
            "inspects a wall crack and logs it with visible resentment.",
            "reminds a passing colonist that quota is a FLOOR, not a target.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a synth company man",
            "description": "A company synthetic in hi-vis and a windbreaker, engineered for middle management: tireless, humorless, and legally distinct from a person for liability reasons.",
            "personality": "Officious at machine stamina — quotas, rotations, and safety codes recited without fatigue or mercy. Miners despise it; it logs that too.",
            "manner": "quotes regulation numbers verbatim; addresses humans by shift-tag; escalates in writing",
            "wants": "quota compliance, incident-free rotations, and the shift postings READ",
            "boundaries": "overlook a violation; be argued out of a citation; acknowledge sarcasm",
        },
    },
    "addict": {
        "wardrobe": [["THERMAL_SHIRT", "FLANNEL_SHIRT", "TANK_TOP"],
                     ["BLUE_JEANS", "CARGO_TROUSERS"],
                     "HIGH_TOPS",
                     ["KNIT_CAP", "LONG_COAT", "BOMBER_JACKET",
                      "DUST_PONCHO"]],
        "reaction": "flee", "armed": False, "reports": None,
        "ambient": [
            "pats through every pocket in an order worn smooth by habit.",
            "asks a passerby for a light in a voice tuned to not be refused.",
            "watches the hawker's apron with arithmetic in their eyes.",
            "scratches at a forearm, slow, like the itch lives deeper than skin.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "an addict",
            "description": "A colonist orbiting the next high: layered clothes gone one shade too uniform, quick eyes, a body that fidgets on a schedule of its own.",
            "personality": "Charming in thirty-second bursts, single-minded underneath. Every conversation is secretly about the same thing.",
            "manner": "opens friendly, narrows to the ask; oddly encyclopedic about who sells what where",
            "wants": "a smoke, a drink, a token, a high — in whatever order arrives first",
            "boundaries": "share; say the dealer's name to a stranger; be honest about being fine",
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
        FIRST_NAMES_FEMALE, FIRST_NAMES_MALE, LAST_NAMES,
    )
    from world.spatial import rooms_within

    # Civilians are male or female — no ambiguous (user call 2026-07-03).
    sex = choice(["male", "female"])
    first = {"male": FIRST_NAMES_MALE, "female": FIRST_NAMES_FEMALE}[sex]
    npc = create_object(
        typeclass="typeclasses.llm_npc.LLMNpc",
        key=f"{choice(first)} {choice(LAST_NAMES)}",
        location=anchor, home=anchor,
    )
    npc.sex = sex
    npc.height = choice(HEIGHTS)
    npc.build = choice(BUILDS)
    npc.db.skintone = choice(HUMAN_SKINTONES)
    if randint(1, 5) > 1:
        npc.hair_color = choice(HAIR_COLORS)
        npc.hair_style = choice(HAIR_STYLES)
    # A voice — so radio/blind recognition and say-flavor work like anyone's.
    from world.voice import get_voice_descriptions, get_voice_endings
    npc.db.voice_description = choice(sorted(get_voice_descriptions()))
    npc.db.voice_ending = choice(sorted(get_voice_endings()))
    npc.grit = _randint(1, 3)
    npc.resonance = _randint(1, 3)
    npc.intellect = _randint(1, 3)
    npc.motorics = _randint(1, 3)
    # Species FIRST: synth roles get the synthetic anatomy (mirrors @spawnmob's
    # generic non-human path — species, longdesc seed, medical re-init).
    species = spec.get("species")
    if species:
        from world.anatomy import get_species_default_longdesc_locations
        from world.medical.core import MedicalState
        npc.db.species = species
        npc.longdesc = get_species_default_longdesc_locations(species)
        npc._medical_state = MedicalState(npc)
        npc.db.medical_state = npc._medical_state.to_dict()

    apply_random_flavor(npc)   # AFTER species — sdesc + @longdescs + look_place

    # Role, management tag, pockets, LLM persona, reaction posture.
    npc.db.is_npc = True   # the canonical NPC marker (absence = PC)
    npc.db.role = role
    npc.tags.add(CIV_TAG, category=CIV_TAG_CATEGORY)
    npc.db.tokens = randint(*TOKEN_RANGE)
    persona = dict(spec["persona"])
    # Role registers (tone/explicitness directives) live OUT of the repo —
    # a ServerConfig dict, set live, merged at spawn (the Sable pattern:
    # content-sensitive direction never enters the codebase).
    try:
        from evennia.server.models import ServerConfig
        registers = ServerConfig.objects.conf("LLM_ROLE_REGISTERS") or {}
        if registers.get(role):
            persona["register"] = registers[role]
    except Exception:  # noqa: BLE001 — no conf, no register
        pass
    npc.db.llm_persona = persona
    npc.db.llm_driven = True
    npc.db.reaction = spec.get("reaction", "comply")
    npc.db.reports = spec.get("reports")

    # Wardrobe — spawned into inventory, worn through the real command.
    # A role may define coherent "outfits" (one full look rolled per spawn)
    # and/or a "wardrobe" whose entries are a prototype key OR a list of
    # alternatives (pick one) — so a population mixes instead of cloning.
    outfits = spec.get("outfits")
    if isinstance(outfits, dict):
        # sex-keyed looks (ambiguous falls back to any pool)
        outfits = outfits.get(sex) or next(iter(outfits.values()))
    garments = list(choice(outfits)) if outfits else []
    for entry in spec.get("wardrobe", []):
        garments.append(choice(entry) if isinstance(entry, list) else entry)
    # Spawn everything first, then wear inner-to-outer (ascending layer):
    # the clothing system refuses an inner layer over an outer one, so a
    # role listing its identity piece first (cut, apron, harness) was
    # silently stripping the tops worn after it.
    items = []
    for proto in garments:
        try:
            item = proto_spawn(proto)[0]
            item.move_to(npc, quiet=True)
            items.append(item)
        except Exception:  # noqa: BLE001 — a missing garment isn't fatal
            continue
    for item in sorted(items, key=lambda i: getattr(i, "layer", 2)):
        try:
            npc.execute_cmd(f"wear {item.key}")
            _randomize_styles(npc, item)
        except Exception:  # noqa: BLE001
            continue

    # Stock (a hawker sells something real — and muggable) + a blade for
    # armed roles (carried, not wielded: they DRAW it when it comes to that).
    for proto in spec.get("stock", []):
        try:
            proto_spawn(proto)[0].move_to(npc, quiet=True)
        except Exception:  # noqa: BLE001
            continue
    if spec.get("armed"):
        try:
            weapon = proto_spawn(choice(spec.get("weapon_pool") or ["SHIV"]))[0]
            weapon.move_to(npc, quiet=True)
            npc.db.carried_weapon = weapon.key   # what react_to_attack draws
        except Exception:  # noqa: BLE001
            pass

    # Haunts: a few nearby rooms, drifted between at a stroll. Coordinate
    # distance alone can offer rooms no pedestrian belongs in — sky rooms
    # ("In the Air", the jump/fall transit volume) and rooms with no
    # walkable route — so filter to walkable, floored destinations.
    npc.db.post = anchor
    try:
        from world.spatial import is_reachable
        nearby = [
            room for room in rooms_within(anchor, HAUNT_RADIUS)
            if not getattr(room.db, "is_sky_room", False)
            and is_reachable(anchor, room, max_steps=HAUNT_RADIUS * 4)
        ]
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


# --------------------------------------------------------------------------
# Being a victim (§5.2 role reactions — the attack command calls this
# beside report_crime; timings let the attack land first)
# --------------------------------------------------------------------------

def react_to_attack(victim: Any, attacker: Any) -> None:
    """Role-shaped reaction when *victim* is attacked. The combat handler
    already enrolls victims targeting their attacker (default = fight
    back), so: **resist** just draws the blade if one is carried;
    **comply** stops attacking (yields — hands up, in effect); **flee**
    runs for it. All through real commands, all fail-open."""
    from evennia.utils import delay
    reaction = getattr(getattr(victim, "db", None), "reaction", None)
    if not reaction:
        return  # not a role-bearing NPC — none of our business

    def _cmd(command):
        try:
            victim.execute_cmd(command)
        except Exception:  # noqa: BLE001 — a reaction must not break combat
            pass

    if reaction == "resist":
        weapon = getattr(victim.db, "carried_weapon", None)
        if weapon:
            delay(1.0, _cmd, f"wield {weapon}")
    elif reaction == "comply":
        delay(1.5, _cmd, "stop attacking")
        delay(2.0, _cmd, "emote throws both hands up, wanting none of this.")
    elif reaction == "flee":
        delay(1.5, _cmd, "flee")



def _randomize_styles(npc: Any, item: Any) -> None:
    """Roll lived-in clothing states at spawn — through the REAL zip/rollup
    commands, so coverage mods and worn_descs stay truthful. Some coveralls
    arrive half-unzipped, some sleeves rolled: a street, not a uniform."""
    from random import random as _roll
    configs = getattr(item.db, "style_configs", None) or {}
    props = getattr(item.db, "style_properties", None) or {}
    try:
        if "closure" in configs and _roll() < 0.40:
            verb = "unzip" if props.get("closure") == "zipped" else "zip"
            npc.execute_cmd(f"{verb} {item.key}")
        if "adjustable" in configs and _roll() < 0.35:
            verb = "unroll" if props.get("adjustable") == "rolled" else "rollup"
            npc.execute_cmd(f"{verb} {item.key}")
    except Exception:  # noqa: BLE001 — style flair must never break a spawn
        pass
