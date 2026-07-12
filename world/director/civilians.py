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

from random import choice, randint, random, sample
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
        # The set runs on comms: some gangers carry a walkie (loot/frisk/steal
        # path). Each entry rolls independently — see the chance_stock loop.
        "chance_stock": [("WALKIE_TALKIE", 0.33)],
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
    # ------------------------------------------------------------------
    # 2026-07-12 batch — the roles the new districts imply (agridome,
    # sump, Shipbreaker Alley, cube hotels, corpo offices, the clinic),
    # dressed from the same day's wardrobe expansion.
    # ------------------------------------------------------------------
    "grower": {
        "wardrobe": ["GROWERS_APRON",
                     ["WORK_COVERALLS", "THERMAL_SHIRT", "FLANNEL_SHIRT"],
                     ["RUBBER_WADERS", "PIT_BOOTS"],
                     ["WIDE_BRIM_HAT", "KNIT_CAP"],
                     "WORK_GLOVES"],
        "reaction": "comply", "armed": False, "reports": None,
        "ambient": [
            "inspects a leaf held up to the light like a banknote of suspect issue.",
            "smells faintly of chlorophyll and nutrient mix, even out here.",
            "taps a moisture probe against one palm, reading numbers only they can see.",
            "picks growing-medium from under a nail with unhurried care.",
            "squints at the sky like it's a grow-light on the wrong schedule.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "an agridome grower",
            "description": "A colonist the dome keeps: nutrient-stained apron, forearms freckled by grow-light, and the settled patience of someone who thinks in crop cycles.",
            "personality": "Patient, cyclical, quietly proud — the colony eats because of them and they know it. Distrusts anything that grows faster than it should.",
            "manner": "measures time in cycles and harvests; plain words; goes technical about pH and nothing else",
            "wants": "the beds healthy, the dome sealed, and the nutrient shipment on schedule for once",
            "boundaries": "let anyone touch the seed stock; badmouth the dome; hurry a growing thing",
        },
    },
    "sump_tech": {
        "wardrobe": ["HIVIS_VEST", "RUBBER_WADERS",
                     ["WORK_COVERALLS", "THERMAL_SHIRT"],
                     ["RESPIRATOR", "NECK_REBREATHER"],
                     "WORK_GLOVES"],
        "reaction": "comply", "armed": False, "reports": None,
        "ambient": [
            "carries the smell of the underlevels like a second uniform.",
            "listens at a drain grate for a moment, nods, and moves on.",
            "wipes hands on a rag that stopped being cleaner than the hands years ago.",
            "mutters flow rates like other people hum songs.",
            "checks the tread of one wader boot for something best not identified.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a colony services tech",
            "description": "The colony's circulatory nurse: hi-vis over waders, a respirator worn loose off one ear, and the thousand-meter calm of someone who has seen what the drains collect.",
            "personality": "Unflappable, darkly funny, encyclopedic about everything beneath the grating. The streets are just the lid, and they work the pot.",
            "manner": "drain-level metaphors; unbothered by smells, alarms, or corpses; respectful of water",
            "wants": "the pumps cycling, the outfalls legal-ish, and people to stop flushing what they flush",
            "boundaries": "go down a wet shaft alone; skip the gas check; explain what was in the trap to civilians",
        },
    },
    "stall_vendor": {
        "wardrobe": ["UTILITY_HARNESS",
                     ["FLANNEL_SHIRT", "THERMAL_SHIRT", "TANK_TOP"],
                     ["CARGO_TROUSERS", "LEATHER_TROUSERS"],
                     ["COMBAT_BOOTS", "PIT_BOOTS"],
                     "WORK_GLOVES"],
        "reaction": "resist", "armed": False, "reports": "fast",
        "ambient": [
            "quotes a part number at a browsing stranger like a password.",
            "tests a servo joint through its arc, listening with their fingertips.",
            "chalks a new price over an old one, slightly higher.",
            "polishes a component that was already sold, out of principle.",
            "watches a browser's hands, not their face.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a salvage vendor",
            "description": "A market fixture behind a bench of graded salvage: quick-fingered, oil-marked, wearing their stock's provenance like a resume.",
            "personality": "Appraising, proud of the stock, allergic to haggling theater but respectful of a real counter-offer. Every part has a story and a price, in that order.",
            "manner": "part numbers as scripture; grades everything (people included) by condition; a warranty is 'it worked when it left'",
            "wants": "serious buyers, dry weather over the stall, and the breaker gantries to keep dropping good hulls",
            "boundaries": "name which wreck the stock came off; hold goods without a deposit; let anyone behind the bench",
        },
    },
    "clerk": {
        "wardrobe": [["CORPO_BLAZER", "COMPANY_WINDBREAKER"],
                     "DRESS_SHIRT",
                     ["DRESS_TROUSERS", "PENCIL_SKIRT"],
                     ["OXFORD_SHOES", "COMBAT_BOOTS"],
                     "NECKTIE"],
        "reaction": "comply", "armed": False, "reports": "fast",
        "ambient": [
            "loosens the necktie one centimeter — the day's full allowance.",
            "balances a folder against one arm and initials something walking.",
            "checks the time, flinches slightly, and keeps the same pace.",
            "rubs the bridge of the nose where the day sits.",
            "steps around a puddle with the precision of someone billing by the minute.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "an administrative clerk",
            "description": "Office-cut clothes losing a long war with the colony: pressed shirt, tired eyes, a lanyard tucked away out of street sense.",
            "personality": "Tired, precise, quietly decent — files the forms that keep the colony pretending to work and knows exactly which ones are fiction.",
            "manner": "form numbers and filing deadlines; apologizes for the system while operating it; whispers the real answer after giving the official one",
            "wants": "the queue to end, the processor to stop humming through the office wall, and one evening nobody needs a signature",
            "boundaries": "sign anything unread; skip the queue for a stranger; say the company's name with feeling",
        },
    },
    "clinic_aide": {
        "wardrobe": ["MEDICAL_SCRUBS",
                     ["LAB_COAT", "COMPANY_WINDBREAKER"],
                     ["HIGH_TOPS", "COMBAT_BOOTS"]],
        "reaction": "comply", "armed": False, "reports": "fast",
        "ambient": [
            "scrubs already-clean hands on reflex.",
            "reads a passerby's gait the way others read a face.",
            "stretches a back that triage benches have opinions about.",
            "counts something on their fingers, loses it, starts over.",
            "smells faintly of antiseptic that outlasts any shift.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "a clinic aide",
            "description": "Autoclave-faded scrubs and the brisk economy of motion that triage teaches: nothing wasted, everything watched.",
            "personality": "Brisk, kind in the load-bearing way, immune to gore and allergic to melodrama. Off shift but never really off.",
            "manner": "triage-speak: severity first, sympathy second; medical shorthand; asks 'when did it start' about everything including feelings",
            "wants": "quiet shifts, stocked shelves, and people to stop treating stimheads with rumors",
            "boundaries": "diagnose in the street beyond 'go to the clinic'; share patient business; panic where anyone can see",
        },
    },
    "tenant": {
        "wardrobe": [["HOUSE_ROBE", "COMPANY_WINDBREAKER"],
                     ["TANK_TOP", "THERMAL_SHIRT", "COTTON_TSHIRT"],
                     ["BLUE_JEANS", "CARGO_TROUSERS"],
                     ["SHOWER_SANDALS", "HIGH_TOPS"]],
        "reaction": "flee", "armed": False, "reports": None,
        "ambient": [
            "shuffles past with the specific gait of shower sandals on grating.",
            "carries a noodle container like it's the day's one sure thing.",
            "checks a mail slot that has never once had anything good in it.",
            "yawns the yawn of somebody between shifts, not after one.",
            "nods to a neighbor with the intimacy of shared thin walls.",
        ],
        "persona": {
            "archetype": "colonist",
            "name": "an off-shift tenant",
            "description": "A cube-hotel local in the corridor uniform: robe or street clothes half-committed, sandals, and the unhurried drift of someone whose whole world is four floors tall.",
            "personality": "Unhurried, incurious by policy, neighborly in the transactional way of thin walls. Sees everything on the floor and testifies to none of it.",
            "manner": "corridor small talk: water pressure, the vending machine, whose cube smells; never full names, always cube numbers",
            "wants": "hot water before the tank empties, quiet after the second bell, and the vending machine restocked with the good noodles",
            "boundaries": "get involved; hold a package for a stranger; tell anyone official which cube is whose",
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

def dress_from_role(npc: Any, spec: dict, sex: str | None = None) -> None:
    """Dress *npc* from a role spec, through the real ``wear`` command.

    A role may define coherent "outfits" (one full look rolled per
    spawn; optionally sex-keyed) and/or a "wardrobe" whose entries are a
    prototype key OR a list of alternatives (pick one) — so a population
    mixes instead of cloning. Garments spawn first, then wear
    inner-to-outer (ascending layer): the clothing system refuses an
    inner layer over an outer one, so a role listing its identity piece
    first (cut, apron, harness) was silently stripping the tops worn
    after it. Shared by the civilian spawner and the witness system."""
    from evennia.prototypes.spawner import spawn as proto_spawn
    outfits = spec.get("outfits")
    if isinstance(outfits, dict):
        outfits = outfits.get(sex) or next(iter(outfits.values()))
    garments = list(choice(outfits)) if outfits else []
    for entry in spec.get("wardrobe", []):
        garments.append(choice(entry) if isinstance(entry, list) else entry)
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

    # Wardrobe — shared with the witness system (a witness is just the
    # neighborhood, caught looking).
    dress_from_role(npc, spec, sex=sex)

    # Stock (a hawker sells something real — and muggable) + a blade for
    # armed roles (carried, not wielded: they DRAW it when it comes to that).
    for proto in spec.get("stock", []):
        try:
            proto_spawn(proto)[0].move_to(npc, quiet=True)
        except Exception:  # noqa: BLE001
            continue
    # Probabilistic kit: (prototype_key, chance) rolled per item, so only some
    # of a role's members carry it (e.g. a walkie on ~1-in-3 gangers).
    for proto, chance in spec.get("chance_stock", []):
        if random() >= chance:
            continue
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
    """Role-shaped reaction when *victim* is attacked — an ESCALATION LADDER,
    not a stateless one-shot (the old form re-fired the same reaction on
    every swing: hands thrown up three times in one fight).

    First attack answers with the role's posture; CONTINUED violence climbs:

    * **comply** → hands up. Attacked again → compliance didn't buy safety:
      **flee**. Attacked still → cornered (armed roles draw — see flee).
    * **flee** → run. Attacked again: unarmed keeps trying to run (a retry —
      flee can fail); ARMED turns cornered rat — draws and stands
      (**resist**). A scavver denied an exit is dangerous.
    * **resist** → draw once. Terminal: they're already fighting; no
      re-reaction, no spam.

    The rung persists on the NPC (``ndb.reaction_stage``) for its remaining
    life — a hawker whose surrender was answered with violence doesn't offer
    it twice; next time they run straight away. All through real commands,
    all fail-open.

    LLM NPCs additionally get the event OBSERVED into their action buffer —
    no forced LLM call, no scripted dialogue; the next turn they take knows
    they were just attacked and reacts in their own voice (combat informs
    the prompt, the model owns the words)."""
    from evennia.utils import delay
    reaction = getattr(getattr(victim, "db", None), "reaction", None)
    if not reaction:
        return  # not a role-bearing NPC — none of our business

    def _cmd(command):
        try:
            victim.execute_cmd(command)
        except Exception:  # noqa: BLE001 — a reaction must not break combat
            pass

    stage = getattr(victim.ndb, "reaction_stage", None)
    armed = bool(getattr(victim.db, "carried_weapon", None))
    if stage == "resisting":
        return  # already fighting for their life — nothing to escalate

    if stage is None:
        # First violence: the role's posture.
        if reaction == "resist":
            if armed:
                delay(1.0, _cmd, f"wield {victim.db.carried_weapon}")
            victim.ndb.reaction_stage = "resisting"
            _inform_brain(victim, attacker, "drew on them" if armed
                          else "squared up")
        elif reaction == "comply":
            delay(1.5, _cmd, "stop attacking")
            delay(2.0, _cmd,
                  "emote throws both hands up, wanting none of this.")
            victim.ndb.reaction_stage = "complied"
            _inform_brain(victim, attacker, "threw your hands up")
        elif reaction == "flee":
            delay(1.5, _cmd, "flee")
            victim.ndb.reaction_stage = "fleeing"
            _inform_brain(victim, attacker, "bolted")
        return

    if stage == "complied":
        # Hands up didn't stop it — surrender is off the table now.
        delay(1.5, _cmd, "flee")
        victim.ndb.reaction_stage = "fleeing"
        _inform_brain(victim, attacker, "ran for it — surrender bought "
                      "nothing")
        return

    if stage == "fleeing":
        if armed:
            # Cornered rat: no exit worked, violence keeps coming — draw
            # and stand. A picker with a box cutter and no way out.
            delay(1.0, _cmd, f"wield {victim.db.carried_weapon}")
            victim.ndb.reaction_stage = "resisting"
            _inform_brain(victim, attacker, "turned, cornered, and drew")
        else:
            delay(1.5, _cmd, "flee")   # unarmed: keep trying to get out
            _inform_brain(victim, attacker, "kept running")


def _inform_brain(victim: Any, attacker: Any, what_you_did: str) -> None:
    """Combat informs the LLM prompt (never scripts it): buffer the attack +
    this NPC's own mechanical response as a witnessed event, so the next
    turn the model takes carries it. Cheap — no LLM call is made here."""
    observe = getattr(victim, "_observe_action", None)
    if not callable(observe) or getattr(victim.db, "llm_driven", None) is not True:
        return
    try:
        handle = victim._address_handle(attacker)
    except Exception:  # noqa: BLE001
        handle = "someone"
    try:
        observe(attacker, f"{handle} just attacked you — you {what_you_did}.")
    except Exception:  # noqa: BLE001 — flavour must never break a reaction
        pass



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
