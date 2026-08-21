"""Personality as a cost structure (NPC_TRAITS_SPEC).

Every soul runs the same engine. A personality is two or three traits,
and a trait is nothing but a REPRICING of decisions the planner
already makes — no behaviour trees, no per-NPC code.

One trait is one object with three faces, authored together so they
cannot drift apart:

    dials   — consulted by needs/planner/engine: WHEN and WHAT
    ethos   — abhors/relishes over action tags: what it COSTS
    voice   — a prompt fragment and pose bank: what it FEELS like

The conscience is one sentence (§4): a plan whose ethos touches what a
soul abhors is only reachable when the driving need is CRITICAL, never
merely soft. A gentle soul who is hungry goes to bed hungry; the same
soul STARVING finally pulls the knife, and the gap between those two
thresholds is the whole personality. Acting against your nature files
a wound-class thought, so guilt is mood, and mood already opens the
bottle and the knife.
"""

#: Action tags. Plans declare what they ARE; traits declare how a soul
#: feels about that. Deliberately few.
ETHOS_TAGS = ("violence", "theft", "indulgence", "toil", "care",
              "communion", "revelry", "solitude")

#: A wound is heavier than an ordinary thought and fades far slower —
#: this is the CK3 lesson, that acting against yourself should cost.
GUILT_WEIGHT = -0.35
RELISH_WEIGHT = 0.08

TRAITS = {
    "ration_burner": {
        "label": "Ration-Burner",
        "blurb": "a big appetite in a lean colony",
        "dials": {"rate:hunger": 1.3, "soft:hunger": 0.45},
        "ethos": {"relishes": {"toil"}},
        "voice": "Food is the one honest pleasure left; you notice "
                 "everyone's plate.",
        "poses": ["eyes the room's plates without meaning to"],
        "excludes": {"drip_fed"},
    },
    "drip_fed": {
        "label": "Drip-Fed",
        "blurb": "eats like refuelling",
        "dials": {"rate:hunger": 0.7},
        "ethos": {},
        "voice": "Eating is refuelling; you stopped tasting it years ago.",
        "poses": ["finishes without looking at what it was"],
        "excludes": {"ration_burner"},
    },
    "dark_adapted": {
        "label": "Dark-Adapted",
        "blurb": "a night creature",
        "dials": {"schedule_affinity": "night"},
        "ethos": {},
        "voice": "The colony makes sense after 22:00; daylight is for "
                 "other people.",
        "poses": ["squints at the light like it owes money"],
        "excludes": {"sunfollower"},
    },
    "sunfollower": {
        "label": "Sunfollower",
        "blurb": "still orients by the sun",
        "dials": {"schedule_affinity": "day"},
        "ethos": {},
        "voice": "You still orient by the sun like the terraform "
                 "brochures promised.",
        "poses": ["turns their face up out of habit"],
        "excludes": {"dark_adapted"},
    },
    "dry_circuit": {
        "label": "Dry Circuit",
        "blurb": "watched the bottle finish somebody",
        "dials": {"misery_pull": 0.0},
        "ethos": {"abhors": {"indulgence"}},
        "voice": "You watched the bottle finish somebody; you drink "
                 "water and remember.",
        "poses": ["turns their glass a quarter turn and leaves it"],
        "excludes": {"rustgut"},
    },
    "rustgut": {
        "label": "Rustgut",
        "blurb": "reaches for it early",
        "dials": {"misery_pull": 0.45},
        "ethos": {"relishes": {"indulgence"}},
        "voice": "Drink is maintenance, not weakness; you measure days "
                 "in what it takes to stay level.",
        "poses": ["turns the empty cup slowly, reading the bottom"],
        "excludes": {"dry_circuit"},
    },
    "hot_solder": {
        "label": "Hot Solder",
        "blurb": "temper arrives first",
        "dials": {"violence_gate": 0.40},
        "ethos": {"relishes": {"violence"}},
        "voice": "Your temper arrives before your reasons do, and it "
                 "usually wins.",
        "poses": ["sets their jaw and doesn't look away"],
        "excludes": {"soft_handed"},
    },
    "flinch_coded": {
        "label": "Flinch-Coded",
        "blurb": "survived by leaving early",
        "dials": {"crit:safety": 0.70},
        "ethos": {"abhors": {"violence"}},
        "voice": "You survived by leaving early; you're not ashamed of "
                 "the math.",
        "poses": ["checks the exit without seeming to"],
        "excludes": {"plate_nerved"},
    },
    "plate_nerved": {
        "label": "Plate-Nerved",
        "blurb": "panic is a luxury",
        "dials": {"crit:safety": 0.95},
        "ethos": {},
        "voice": "Panic is a luxury; you've stood in worse rooms than "
                 "this one.",
        "poses": ["doesn't move when the noise starts"],
        "excludes": {"flinch_coded"},
    },
    "soft_handed": {
        "label": "Soft-Handed",
        "blurb": "has never hurt anyone",
        "dials": {},
        "ethos": {"abhors": {"violence", "theft"}},
        "voice": "You have never hurt anyone and you carry that like "
                 "the last clean thing you own.",
        "poses": ["keeps their hands where everyone can see them"],
        "excludes": {"hot_solder"},
    },
    "grudge_etched": {
        "label": "Grudge-Etched",
        "blurb": "forgives nothing",
        "dials": {},
        "ethos": {},
        "voice": "You forgive nothing; you file it, dated, and keep "
                 "the file.",
        "poses": ["looks at somebody a beat too long, and remembers it"],
        "excludes": set(),
    },
    "faraday_souled": {
        "label": "Faraday-Souled",
        "blurb": "clear signal alone",
        "dials": {"rate:social": 0.7},
        "ethos": {"relishes": {"solitude"}},
        "voice": "Crowds read you like static; alone, the signal "
                 "finally clears.",
        "poses": ["drifts to the edge of the room without deciding to"],
        "excludes": {"antenna_up"},
    },
    "antenna_up": {
        "label": "Antenna-Up",
        "blurb": "needs the room's noise",
        "dials": {"rate:social": 1.3},
        "ethos": {"relishes": {"revelry"}},
        "voice": "You need the room's noise the way other people need "
                 "the meal.",
        "poses": ["finds the loudest corner and settles into it"],
        "excludes": {"faraday_souled"},
    },
    "greenhaus_handed": {
        "label": "Greenhaus-Handed",
        "blurb": "things grow under their hands",
        "dials": {},
        "ethos": {"relishes": {"care", "toil"}},
        "voice": "Things grow under your hands, and you judge the "
                 "colony by what it wastes.",
        "poses": ["straightens something nobody else noticed"],
        "excludes": set(),
    },
    "rivet_tight": {
        "label": "Rivet-Tight",
        "blurb": "every token has a job",
        "dials": {"price_ceiling": 0.5},
        "ethos": {},
        "voice": "Every token has a job; you count the till twice and "
                 "trust it once.",
        "poses": ["counts it again, quietly"],
        "excludes": {"open_valve"},
    },
    "open_valve": {
        "label": "Open-Valve",
        "blurb": "spends before the colony takes it",
        "dials": {"price_ceiling": 2.0},
        "ethos": {"relishes": {"indulgence"}},
        "voice": "Money is for spending before the colony finds a way "
                 "to take it.",
        "poses": ["waves off the change"],
        "excludes": {"rivet_tight"},
    },
    "shift_hound": {
        "label": "Shift-Hound",
        "blurb": "the shift is the spine of the day",
        "dials": {"duty_lead": -1800},
        "ethos": {"relishes": {"toil"}},
        "voice": "The shift is the spine of the day; everything else "
                 "hangs off it.",
        "poses": ["is already at the post, doing something small"],
        "excludes": {"clock_ghost"},
    },
    "clock_ghost": {
        "label": "Clock-Ghost",
        "blurb": "work is a tax on being alive",
        "dials": {"duty_lead": 1800},
        "ethos": {},
        "voice": "Work is a tax on being alive; you pay late and tip "
                 "nothing.",
        "poses": ["arrives like the shift started without permission"],
        "excludes": {"shift_hound"},
    },
    # --- curated singletons: the generator never rolls these (§6b) ---
    "wire_loved": {
        "label": "Wire-Loved",
        "blurb": "loves the colony at a distance",
        "dials": {},
        "ethos": {"relishes": {"solitude", "communion"}},
        "voice": "You love the whole colony at once and cannot bear it "
                 "one person at a time.",
        "poses": ["speaks to a room that isn't there, and means it"],
        "excludes": set(),
        "curated_only": True,
    },
}


def traits_of(soul):
    """The trait keys this soul actually carries."""
    stored = soul.db.soul_traits if soul and soul.db else None
    return tuple(k for k in (stored or ()) if k in TRAITS)


def dial(soul, key, default):
    """The soul's value for a dial, or `default`.

    Multiplicative for rate:* (they compound); for everything else the
    LAST trait to declare it wins, which only matters when a curated
    pair deliberately overlaps — the generator's exclusions keep rolled
    souls from contradicting themselves.
    """
    if key.startswith("rate:"):
        factor = 1.0
        for name in traits_of(soul):
            factor *= float(TRAITS[name]["dials"].get(key, 1.0))
        return default * factor
    for name in traits_of(soul):
        if key in TRAITS[name]["dials"]:
            return TRAITS[name]["dials"][key]
    return default


def ethos(soul):
    """(abhors, relishes) for this soul, as sets of action tags."""
    abhors, relishes = set(), set()
    for name in traits_of(soul):
        spec = TRAITS[name].get("ethos") or {}
        abhors |= set(spec.get("abhors") or ())
        relishes |= set(spec.get("relishes") or ())
    return abhors, relishes


def abhors(soul, tags):
    """Does this soul recoil from an action carrying `tags`?"""
    if not tags:
        return False
    return bool(set(tags) & ethos(soul)[0])


def relishes(soul, tags):
    if not tags:
        return False
    return bool(set(tags) & ethos(soul)[1])


def voice_fragments(soul):
    """Prompt material — one sentence per trait, in carry order."""
    return [TRAITS[name]["voice"] for name in traits_of(soul)]


def poses(soul):
    """Pose bank for this soul's traits (the F.E.A.R. lesson: same
    plan, different body language)."""
    out = []
    for name in traits_of(soul):
        out.extend(TRAITS[name].get("poses") or ())
    return out


def labels(soul):
    return [TRAITS[name]["label"] for name in traits_of(soul)]


def roll(count=None, rng=None):
    """Two or three traits for somebody nobody authored, honouring the
    exclusion pairs so a rolled soul never contradicts itself. Curated
    singletons are never rolled."""
    import random as _random

    rng = rng or _random
    pool = [k for k, spec in TRAITS.items() if not spec.get("curated_only")]
    rng.shuffle(pool)
    want = count or rng.choices((2, 3), weights=(3, 1))[0]
    picked, blocked = [], set()
    for key in pool:
        if len(picked) >= want:
            break
        if key in blocked:
            continue
        picked.append(key)
        blocked |= set(TRAITS[key].get("excludes") or ())
    return tuple(picked)
