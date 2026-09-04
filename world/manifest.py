"""The slowboat manifest — who everyone was before planetfall.

Every colonist came down in cryo with a vessel, a department and a
rating assigned: the org chart of the colony that was supposed to
happen. Then the gateway died, the terraform curdled, and the chart
never stood up. Sixty-one years later everyone still carries a dead
uniform's designation — assigned, slept through, never once used, and
still the truest surviving record of who they were.

Design notes that are load-bearing (SKILLS_AND_DESIGNATION_SPEC):

* **Ranks are flavour.** Nothing checks one. No authority, no pay
  band, no gate. They exist to lend the theme gravitas.
* **Command is deliberately empty.** The officers who mattered died,
  left, or never woke. If Command ever enters play it arrives as
  ARTIFACTS — ship logs, personal effects — not as people.
* **Skills are a snapshot**, seeded here at creation and flat
  thereafter. An XP system will come; nothing in this module ticks.
* **Identity-level**: designation and skills survive resleeving,
  because they are records about the person rather than the meat.
"""

from random import choice, choices, randint

#: Slowboat registry. The Halcyon building is SBL-0117's reclaimed
#: hull — established canon. A fuller registry is a naming project of
#: its own; a handful is enough for every arrival to have come off one.
VESSELS = {
    "SBL-0117": "Halcyon Days",
    "SBL-0092": "Perpetual Noon",
    "SBL-0104": "Golden Hour",
}

#: The chart. `command` is present and never rolled (see above).
DEPARTMENTS = {
    "command": "Command",
    "flight_ops": "Flight & Orbital Ops",
    "engineering": "Engineering & Fabrication",
    "life_systems": "Life Systems",
    "medical": "Medical & Cryogenics",
    "security": "Security & Marshal Service",
    "logistics": "Logistics & Stores",
    "signals": "Signals & Survey",
}

#: Departments the shuttle actually delivers, and how common each is.
ROLLABLE = ("engineering", "life_systems", "medical", "security",
            "logistics", "signals", "flight_ops")
DEPARTMENT_WEIGHTS = (5, 6, 3, 4, 5, 3, 2)

#: Rank ladder, common to rare. `commander` is never rolled.
RANKS = ("crewman", "specialist", "chief", "officer", "commander")
RANK_LABELS = {
    "crewman": "Crewman", "specialist": "Specialist", "chief": "Chief",
    "officer": "Officer", "commander": "Commander",
}
ROLLABLE_RANKS = ("crewman", "specialist", "chief", "officer")
RANK_WEIGHTS = (6, 5, 2, 1)

#: The fourteen ratings, with the stats each is checked against.
#: Check value = skill + (governing stats averaged), the average
#: keeping any rating comparable to any other; `cant` weights one stat
#: where it should dominate. What dice go against that value is an
#: open question this module deliberately does not answer.
SKILLS = {
    "firearms": {"label": "Firearms", "stats": ("motorics",)},
    "melee": {"label": "Melee", "stats": ("motorics", "grit")},
    "unarmed": {"label": "Unarmed", "stats": ("grit", "motorics"),
                "cant": {"grit": 2}},
    "demolitions": {"label": "Demolitions",
                    "stats": ("intellect", "motorics"),
                    "cant": {"intellect": 2}},
    "medicine": {"label": "Medicine", "stats": ("intellect", "motorics")},
    "chemistry": {"label": "Chemistry", "stats": ("intellect",)},
    "systems": {"label": "Systems", "stats": ("intellect",)},
    "engineering": {"label": "Engineering",
                    "stats": ("motorics", "intellect")},
    "piloting": {"label": "Piloting", "stats": ("motorics", "intellect")},
    "agrotech": {"label": "Agrotech", "stats": ("intellect",)},
    "provisioning": {"label": "Provisioning", "stats": ("motorics",)},
    "athletics": {"label": "Athletics", "stats": ("motorics", "grit")},
    "stealth": {"label": "Stealth", "stats": ("motorics",)},
    "subterfuge": {"label": "Subterfuge", "stats": ("motorics", "intellect")},
}

#: What each department rated you for.
DEPARTMENT_SKILLS = {
    "command": ("piloting", "systems"),
    "flight_ops": ("piloting", "engineering"),
    "engineering": ("engineering", "systems"),
    "life_systems": ("agrotech", "provisioning"),
    "medical": ("medicine", "chemistry"),
    "security": ("firearms", "unarmed"),
    "logistics": ("systems", "athletics"),
    "signals": ("systems", "piloting"),
}

#: Where each department's spare attention tended to wander.
DEPARTMENT_AFFINITY = {
    "security": ("melee", "demolitions", "athletics"),
    "engineering": ("demolitions", "systems", "piloting"),
    "life_systems": ("athletics", "provisioning", "chemistry"),
    "medical": ("chemistry", "subterfuge", "athletics"),
    "logistics": ("subterfuge", "provisioning", "piloting"),
    "signals": ("stealth", "subterfuge", "systems"),
    "flight_ops": ("athletics", "systems", "engineering"),
    "command": ("firearms", "systems", "subterfuge"),
}

#: Bands on the 0-150 scale the descriptive layer renders as letters.
#: "Rated" sits mid-scale: the manifest saying you may touch the
#: machine, not that you are remarkable at it.
BANDS = {"rated": (66, 84), "seasoned": (90, 108), "master": (120, 138)}


def letter_for(value):
    """The A-Z tier a 0-150 rating falls in — the same value language
    G.R.I.M. speaks. A is apex, Z is nothing at all. Per-skill word
    lists (a fourteen-times-twenty-six writing project) arrive with
    the descriptor layer; until then the letter carries it."""
    v = max(0, min(150, int(value or 0)))
    if v == 0:
        return "Z"
    return chr(ord("Y") - ((v - 1) // 6))


def rank_of(char):
    return ((char.db.designation or {}).get("rank") or "") if char else ""


def department_of(char):
    return ((char.db.designation or {}).get("dept") or "") if char else ""


def roll_designation(dept=None, rank=None):
    """A designation for somebody nobody authored. Never Command, and
    never Commander — both are reserved, and Command is meant to stay
    empty (its story arrives as artifacts, not officers).

    The reservation is enforced by the POOLS -- ROLLABLE omits
    `command`, ROLLABLE_RANKS omits `commander` -- so both overrides
    have to be checked against them too, or `roll_designation(
    dept="command", rank="commander")` returns exactly the thing this
    docstring says never happens. Both call sites pass nothing today;
    this is the door, not the breach (#2800).
    """
    if dept not in ROLLABLE:
        dept = None
    if rank not in ROLLABLE_RANKS:
        rank = None
    return {
        "vessel": choice(list(VESSELS)),
        "dept": dept or choices(ROLLABLE, weights=DEPARTMENT_WEIGHTS)[0],
        "rank": rank or choices(ROLLABLE_RANKS, weights=RANK_WEIGHTS)[0],
    }


def seed_skills(designation):
    """What the chart rated this person for.

    Both core ratings for the department, banded by rank — a Chief
    took one further, an Officer both — plus one rating from wherever
    that department's attention wandered, because nobody is only their
    job.
    """
    dept = (designation or {}).get("dept") or "logistics"
    rank = (designation or {}).get("rank") or "crewman"
    core = DEPARTMENT_SKILLS.get(dept, ())
    out = {}

    def _band(name):
        lo, hi = BANDS[name]
        return randint(lo, hi)

    for i, skill in enumerate(core):
        if rank == "officer" or rank == "commander":
            out[skill] = _band("seasoned")
        elif rank == "chief" and i == 0:
            out[skill] = _band("seasoned")
        else:
            out[skill] = _band("rated")

    spare = [s for s in DEPARTMENT_AFFINITY.get(dept, ()) if s not in out]
    if spare:
        out[choice(spare)] = _band("rated")
    return out


def check_value(char, skill):
    """skill + (governing stats averaged, cantable) — the owner's
    formula. Returns None for a rating this character does not hold;
    unrated is a real answer, not a zero to paper over."""
    spec = SKILLS.get(skill)
    if spec is None:
        return None
    rating = (char.db.skills or {}).get(skill)
    if rating is None:
        return None
    cant = spec.get("cant") or {}
    total = weight = 0.0
    for stat in spec["stats"]:
        w = float(cant.get(stat, 1))
        total += float(getattr(char, stat, 1) or 1) * w
        weight += w
    return float(rating) + (total / weight if weight else 0.0)


def designation_line(char):
    """One line for a sheet: `Chief, Life Systems — SBL-0117 Halcyon
    Days`. Empty string for anyone the manifest never listed, which is
    its own kind of record."""
    des = char.db.designation or {}
    if not des:
        return ""
    rank = RANK_LABELS.get(des.get("rank"), "")
    dept = DEPARTMENTS.get(des.get("dept"), "")
    vessel = des.get("vessel") or ""
    name = VESSELS.get(vessel, "")
    head = ", ".join(p for p in (rank, dept) if p)
    tail = " ".join(p for p in (vessel, name) if p)
    return f"{head} — {tail}" if tail else head


def rated_skills(char):
    """[(label, rating)] for what this character actually holds, best
    first. Only what they know: a sheet full of zeroes tells nobody
    anything."""
    held = char.db.skills or {}
    rows = [(SKILLS[k]["label"], v) for k, v in held.items() if k in SKILLS]
    return sorted(rows, key=lambda r: -r[1])
