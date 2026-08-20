# Skills & the Pre-Planetfall Designation

> **Status:** 📋 **PROPOSAL — owner review pending.** Department,
> rank, and vessel names (§4), the skill vocabulary (§5), and the
> named-NPC designations (§9) all await the red pen. Builds on the
> G.R.I.M. stats that already live on every Character
> (DESCRIPTIVE_STAT_SYSTEM_SPEC — descriptor layer unbuilt) and on
> the traits spec (NPC_TRAITS_SPEC §11's background seam — this is
> its first tenant).

## 1. The fiction (why this designation exists)

Every colonist came to Domino's Gambit in cryo aboard a slowboat.
The manifest assigned each sleeper a **vessel, department, and
rating** — the org chart of the colony that was supposed to happen.
Then the gateway died, the terraform curdled, and the chart never
stood up. Sixty-one years later, every resident still carries a dead
uniform's designation: **assigned, slept through, never once used —
and still the truest surviving record of who they were.**

The colony's real hierarchy (tills, gigs, favors, rep) grew in the
ruins of the paper one. Some people salute the old chart anyway.
Most don't. Both reactions are content.

Design consequences, each load-bearing:

- **Identity-level, not sleeve-level.** The designation survives
  resleeving untouched — it's a record about the *person*, held in
  the manifest, not in the meat. Even a memory-distorted resleeve
  can look themselves up. (Deliberate interaction with the owner's
  pending distortion conversation: the manifest is the one mirror
  that never lies about who you were — only about who you are.)
- **The Manifest is a file** (DECKING_MATRIX "everything is a
  file"): designations are readable at terminals today and become
  verifiable/forgeable when decking lands — a forged Command
  designation is social engineering, the wanted-record precedent.
- **The snapshot is the skill system's spine** (§2): what you were
  rated for pre-planetfall is what you know at decant.

## 2. Skills philosophy — a snapshot, not a ladder

Settled growth direction: progression in this game is favor + gear +
rep, **not stat leveling**. Skills therefore are:

- **A pre-planetfall snapshot**, seeded by designation at creation
  (PC and NPC identically) and essentially flat thereafter. No XP,
  no grind, no counters ticking per use.
- **Descriptive tiers, never numbers** (the descriptive-stat
  philosophy): `Green → Rated → Seasoned → Master`. "Rated" is the
  ship's word: the manifest says you may touch the machine.
- **Modifiers over G.R.I.M., never replacements.** Every check keeps
  its stat as substrate; the skill tier adds a flat modifier. A
  Master medic with ruined Motorics still shakes.
- **Growth is diegetic and rare** — an owner-granted or
  gig-capstone event ("the Ripper taught you something no manifest
  would print"), never automatic.

## 3. Storage

```python
char.db.designation = {
    "vessel": "SBL-0117",          # registry key; display adds the name
    "dept": "life_systems",
    "rank": "chief",
}
char.db.skills = {"agronomy": "seasoned", "fabrication": "rated"}
```

Both identity-level: written at decant/generation, copied through
resleeve estate untouched. Absent keys read as Green — a soul or
sleeve predating this spec is simply unrated at everything until
backfilled (build script).

## 4. The chart (OWNER RED PEN — all names)

**Vessels** (slowboat registry; the Halcyon building is the wreck of
the first — established canon):

| Registry | Name | Note |
|---|---|---|
| SBL-0117 | *Halcyon Days* | established (the Halcyon, reclaimed hull) |
| SBL-0092 | *Perpetual Noon* | proposed |
| SBL-0104 | *Golden Hour* | proposed |

**Departments** (8):

| Key | Department | Flavor |
|---|---|---|
| `command` | Command | the chart's apex; rarest |
| `flight_ops` | Flight & Orbital Ops | the ships still up there |
| `engineering` | Engineering & Fabrication | hulls, machines, power |
| `life_systems` | Life Systems | hydroponics, atmos, water — the solarpunk heart |
| `medical` | Medical & Cryogenics | the ones who watched everyone sleep |
| `security` | Security & Marshal Service | the chart's fist |
| `logistics` | Logistics & Stores | manifests, holds, trade |
| `signals` | Signals & Survey | comms, sensors, charts — the decking affinity |

**Ranks** (5, weighted): Crewman (common) → Specialist (common) →
Chief (uncommon) → Officer (rare) → Commander (named characters
only; the generator never rolls one).

## 5. Skill vocabulary v1 (10 — OWNER RED PEN)

| Key | Skill | Substrate stat | First mechanical home |
|---|---|---|---|
| `medicine` | Medicine | Intellect | `calculate_treatment_success` + medical `stat_requirement` gates (both exist today) |
| `agronomy` | Agronomy | Intellect | Greenhaus tending quality (future pump/water hooks) |
| `culinary` | Culinary | Motorics | cook/butcher output quality (world/food.py seam) |
| `fabrication` | Fabrication | Motorics | repair/craft checks (future) |
| `systems` | Systems | Intellect | the decking palette gate (DECKING_MATRIX: joins Intellect when built) |
| `signals` | Signals | Intellect | radio/console procedures; dispatch craft |
| `rigging` | Rigging | Motorics | heavy machinery (the crane's precedent) |
| `close_protection` | Close Protection | Grit | security procedures; weapon-handling flavor (combat math untouched in v1) |
| `quartermastery` | Quartermastery | Resonance | appraisal/haggling (pawn/shop seams) |
| `survey` | Survey | Intellect | navigation/mapping (the chart spec's future player-mapping hooks) |

Department seed packages: each department grants its two core skills
at Rated (Chiefs: one at Seasoned; Officers: both) plus one weighted
random off-department skill at Rated — nobody is only their job.

**v1 mechanical scope is deliberately thin**: wire ONLY the check
sites that already exist (medicine's two, and skill display). The
rest of the column is a promissory table — it grows as systems
allot, the owner's phrase, same law as traits.

## 6. Creation flows

- **Player decant** (New Game Experience): the Thawn-Harrison sleeve
  envelope — already the chargen's branded artifact — now prints the
  designation. Assigned by weighted roll, Starfleet-Command-esque:
  you wake up already being someone. (Whether players get one
  reroll is an owner call; propose: no — the manifest doesn't
  negotiate.)
- **NPC generation**: shuttle arrivals roll designation first;
  department then weights the trait roll (NPC_TRAITS_SPEC §7):
  Security leans Plate-Nerved, Life Systems leans Greenhaus-Handed /
  Sunfollower, Signals leans Faraday-Souled, Logistics leans
  Rivet-Tight. Personality correlates with vocation without being
  determined by it.
- **Backfill**: one build script rolls designations + skills for
  every existing soul and PC sleeve-holder, department-weighted by
  their current role where one exists (Vance rolls Medical, not
  randomly).

## 7. Where it shows

- **`score`/sheet**: one line — `Chief, Life Systems — SBL-0117
  Halcyon Days`.
- **LLM persona**: the designation joins the trait voice fragments
  (a Signals officer talks like one); STATE untouched.
- **`@soul`**: designation on the individual card.
- **Terminals**: the Manifest as a readable file — look anyone up by
  name. (Forgery arrives with decking, not before.)
- **Social truth**: no mechanical deference in v1. Whether the
  constabulary salutes a Security designation, whether a Command
  officer can requisition anything at all — future content, owner's
  call, and the ambiguity is the point.

## 8. Explicitly out of scope (v1)

- Any XP/use-based skill growth (against settled direction).
- Combat math changes (close_protection is flavor + procedures only).
- Department factions/pay/privileges (WSIS-adjacent — owner-pending).
- Manifest forgery (decking-gated).

## 9. Named-NPC designations (PROPOSED — owner approves each)

| NPC | Designation | Why |
|---|---|---|
| Vance | Officer, Medical & Cryogenics | the doctor; watched the sleepers |
| Petra | Chief, Signals & Survey | dispatch is the old comms watch |
| The Rook | Officer, Signals & Survey | the voice of the ship, still broadcasting |
| Ossie | Specialist, Engineering & Fabrication | the crane was almost his rating |
| Bellows | Specialist, Logistics & Stores | knows what a shelf is worth |
| Marta | Chief, Logistics & Stores | the pawn counter is a cargo hold |
| Sable | Crewman, Life Systems | stewarding was the closest the chart came to bartending |
| Sully | Crewman, Engineering & Fabrication | hull-slab bar, hull-rated hands |
| Lin | Crewman, Life Systems | galley rating; the cart is the galley |
| Ottilie | Specialist, Life Systems | butcher's rating, galley track |
| Del | Crewman, Signals & Survey | night watch then, night bar now |
| Vesper | — (no designation) | synthetic; never on a manifest — its OWN kind of record (Thawn-Harrison provenance), future seam |

## 10. Phasing

- **P1**: storage + chart data + decant/generator/backfill rolls +
  display (score/@soul/persona). Zero check-site changes — the
  designation exists and speaks before it does anything.
- **P2**: medicine wired to its two existing check sites; skill line
  in `score`.
- **P3+**: each future system (decking, kitchens, mapping) claims
  its skill column entry when it builds — never before.
