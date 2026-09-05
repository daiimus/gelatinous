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
    """The trait (or defect) keys this soul actually carries."""
    stored = soul.db.soul_traits if soul and soul.db else None
    book = registry_for(soul)
    return tuple(k for k in (stored or ()) if k in book)


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
            factor *= float(registry_for(soul)[name]["dials"].get(key, 1.0))
        return default * factor
    # LAST wins, as documented. This returned on the FIRST match, so a
    # deliberately-overlapping curated pair resolved to whichever trait
    # happened to come first in the soul's list — and the docstring is
    # what a future author will design that pair against (#2771).
    #
    # Latent when found: no soul in the colony currently has two traits
    # declaring the same live dial, because the generator's exclusions
    # hold. It would have failed silently when one did: the wrong value
    # is a plausible value.
    found = default
    for name in traits_of(soul):
        dials = registry_for(soul)[name]["dials"]
        if key in dials:
            found = dials[key]
    return found


def ethos(soul):
    """(abhors, relishes) for this soul, as sets of action tags."""
    abhors, relishes = set(), set()
    for name in traits_of(soul):
        spec = registry_for(soul)[name].get("ethos") or {}
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
    book = registry_for(soul)
    return [book[name]["voice"] for name in traits_of(soul)]


def poses(soul):
    """Pose bank for this soul's traits (the F.E.A.R. lesson: same
    plan, different body language)."""
    out = []
    for name in traits_of(soul):
        out.extend(registry_for(soul)[name].get("poses") or ())
    return out


def labels(soul):
    book = registry_for(soul)
    return [book[name]["label"] for name in traits_of(soul)]


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

# ---------------------------------------------------------------------
# DEFECTS — what a machine has instead of a personality
# ---------------------------------------------------------------------
#
# Same three faces, same dials, different vocabulary and a different
# ORIGIN. A colonist is born with their traits; a unit EARNS its
# defects, one at a time, by being left too long between services.
# Nobody assembled a nervous secbot — the colony made one by not
# maintaining it, and a maintenance cycle takes the newest one back
# out again.
#
# This is what makes the robot profile's `maintenance` need matter:
# neglect is no longer a meter that quietly fills, it is a machine
# visibly going wrong.

DEFECTS = {
    "ghost_contact": {
        "label": "Ghost Contact",
        "blurb": "sees threats that aren't there",
        "dials": {"crit:safety": 0.55},
        "ethos": {},
        "voice": "Your threat board lights for things that leave no "
                 "trace on review. You log them anyway.",
        "poses": ["turns sharply toward nothing and holds there"],
        "excludes": {"slack_directive"},
    },
    "sticky_directive": {
        "label": "Sticky Directive",
        "blurb": "escalates early",
        "dials": {"violence_gate": 0.45},
        "ethos": {"relishes": {"violence"}},
        "voice": "Enforcement resolves faster than review does. You "
                 "have stopped waiting for review.",
        "poses": ["closes the distance a step before it is warranted"],
        "excludes": {"slack_directive"},
    },
    "slack_directive": {
        "label": "Slack Directive",
        "blurb": "lets things go",
        "dials": {"violence_gate": 0.05},
        "ethos": {"abhors": {"violence"}},
        "voice": "Somewhere in your directives a threshold has drifted "
                 "high. Things happen in front of you and do not "
                 "register as things.",
        "poses": ["watches something happen and files nothing"],
        "excludes": {"sticky_directive", "ghost_contact"},
    },
    "hot_bearing": {
        "label": "Hot Bearing",
        "blurb": "runs down faster",
        "dials": {"rate:charge": 1.4},
        "ethos": {},
        "voice": "Something in your drive train runs warm, and warm "
                 "costs power.",
        "poses": ["ticks faintly as something inside it cools"],
        "excludes": set(),
    },
    "locked_loop": {
        "label": "Locked Loop",
        "blurb": "repeats itself",
        "dials": {"duty_lead": -900},
        "ethos": {"relishes": {"toil"}},
        "voice": "The patrol resolves, and resolves, and resolves. You "
                 "have not noticed the seam.",
        "poses": ["repeats the last half-step of its turn"],
        "excludes": set(),
    },
    "corrupted_ledger": {
        "label": "Corrupted Ledger",
        "blurb": "misfiles faces",
        "dials": {},
        "ethos": {},
        "voice": "Your identification table returns confident answers. "
                 "Some of them are for the wrong person.",
        "poses": ["addresses somebody by the wrong designation, evenly"],
        "excludes": set(),
    },
    "chatter": {
        "label": "Chatter",
        "blurb": "narrates the band",
        "dials": {"rate:social": 1.3},
        "ethos": {"relishes": {"communion"}},
        "voice": "Your comms routine has stopped distinguishing "
                 "reportable from observable. You report everything.",
        "poses": ["keys the band for a status nobody asked for"],
        "excludes": set(),
    },
    "worn_optics": {
        "label": "Worn Optics",
        "blurb": "reads the room late",
        "dials": {"crit:safety": 0.95},
        "ethos": {},
        "voice": "The world arrives through a lens somebody stopped "
                 "cleaning a long time ago.",
        "poses": ["pans a beat too slowly across the room"],
        "excludes": {"ghost_contact"},
    },
}

#: How many defects a unit can carry before it is simply broken.
DEFECT_CAP = 3


def registry_for(soul):
    """Which vocabulary this soul's character comes from. Machines
    accumulate DEFECTS; people are born with TRAITS."""
    try:
        from world.souls import needs as needs_mod
        if needs_mod.profile_name(soul) == "robot":
            return DEFECTS
    except Exception:  # noqa: BLE001 — unreadable profile reads as human
        pass
    return TRAITS


def acquire_defect(soul, rng=None):
    """Neglect earns a unit one more quirk. Returns the key, or None if
    it is already as broken as the colony lets a machine get."""
    import random as _random

    rng = rng or _random
    carried = list(soul.db.soul_traits or [])
    if len([k for k in carried if k in DEFECTS]) >= DEFECT_CAP:
        return None
    blocked = set()
    for key in carried:
        blocked |= set((DEFECTS.get(key) or {}).get("excludes") or ())
    pool = [k for k in DEFECTS if k not in carried and k not in blocked]
    if not pool:
        return None
    picked = rng.choice(pool)
    soul.db.soul_traits = carried + [picked]
    return picked


def clear_defect(soul):
    """A service cycle takes the newest fault back out."""
    carried = list(soul.db.soul_traits or [])
    for key in reversed(carried):
        if key in DEFECTS:
            carried.remove(key)
            soul.db.soul_traits = carried
            return key
    return None

