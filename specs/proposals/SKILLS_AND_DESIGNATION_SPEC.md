# Skills & the Pre-Planetfall Designation

Every person carries a pre-planetfall **designation** (vessel,
department, rank) and a small set of **skill ratings**, both rolled at
creation and both held by the person, not the body (synthetics, robots
and rats excepted, §3). The chart data, the
rolls and the display live in `world/manifest.py` (#2138). This builds on
the G.R.I.M. stats every Character already has (DESCRIPTIVE_STAT_SYSTEM_SPEC)
and is the first tenant of the traits spec's background seam
(NPC_TRAITS_SPEC §11).

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
  can read their own record on `score`; looking it up anywhere else is
  📋 UNBUILT (no issue), see §7 Terminals. (Deliberate interaction with the owner's
  pending distortion conversation: the manifest is the one mirror
  that never lies about who you were — only about who you are.)
- **The Manifest is a file** (DECKING_MATRIX "everything is a
  file"): in this design, designations are readable at terminals
  (📋 UNBUILT (no issue), §7 Terminals) and become verifiable/forgeable
  when decking lands — a forged Command designation is social
  engineering, the wanted-record precedent. The places a designation
  shows are listed in §7.
- **The snapshot is the skill system's spine** (§2): what you were
  rated for pre-planetfall is what you know at decant.

## 2. Skills philosophy — a snapshot, for now (OWNER-RULED 2026-08-19)

- **A pre-planetfall snapshot at creation** (PC and NPC identically):
  whatever comes out at character generation is what you have. **An
  XP system where skills AND stats increase will eventually exist**
  (owner ruling — revises the earlier no-leveling stance), but not
  yet; nothing in this spec ticks per use.
- **Values on the A–Z descriptive scale** (0–150, 26 tiers), the
  same value language as G.R.I.M. — one system, never numbers
  player-facing. Each skill gets its own A–Z word list
  (DESCRIPTIVE_STAT_SYSTEM_SPEC pattern) when the display layer
  builds.
- **The check model (owner's formula):**

  ```
  check value = skill + (sum of governing stats ÷ their count)
  ```

  Multiple governing stats average so any skill stays balanced
  against any other, and the division can be **canted** when one
  stat should dominate — e.g. Unarmed = skill + (2·Grit + Motorics)/3.
  `world/manifest.py::check_value` computes it, and returns None for a
  rating the character does not hold. What dice roll against the
  check value is open (§11); this spec defines the value, not the
  throw.
- **Skills modify, never replace**: a Master medic with ruined
  Motorics still shakes.
- **Wiring is deferred wholesale** (owner: "we'll wire them into
  everything when we're ready — for now, spec it out"). The
  first-consumer column in §5 is a promissory map, not a work order.
  The designation exists and speaks before it does anything: no check
  site changes until the owner calls wiring ready (§10).
- **Score shows only the skills you know** — rated lines print, the
  wall of Z's doesn't. The sheet reads like the manifest: what the
  chart says you're for.

## 3. Storage

```python
char.db.designation = {
    "vessel": "SBL-0117",          # registry key; display adds the name
    "dept": "life_systems",
    "rank": "chief",
}
char.db.skills = {"agrotech": 96, "provisioning": 78}   # 0-150, A-Z displayed
```

Both identity-level: written at decant/generation and carried across
resleeving. A flash clone inherits its person's record rather than
rolling a new career (#3033):
`ensure_manifest(char, inherit_from=old_character)` in
`commands/charcreate.py::create_flash_clone`. An NPC rebuilt at its
post gets it back from its imprint (`world/imprint.py::restore`). A
new character made from a template rolls its own.
`world/manifest.py::ensure_manifest` leaves an existing record alone.

Absent keys are unrated: score does not print them, and `check_value`
returns None for them rather than 0 — a soul or sleeve predating this
spec is simply unrated at everything until backfilled (build
script).

Only people held a berth (#2670). A body whose species starts with
synth, robot or rat gets no record
(`world/manifest.py::travelled_as_crew`), and an unset species counts
as a person. Builds 100 and 162 apply this rule; `ensure_manifest`
and `roll_person` do not check it.

## 4. The chart (OWNER RED PEN — all names)

The chart data is in `world/manifest.py`: `VESSELS`, `DEPARTMENTS`,
`RANKS`/`RANK_WEIGHTS`.

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
Chief (uncommon) → Officer (rare) → Commander.

`world/manifest.py::roll_designation` picks the vessel evenly, the
department by `DEPARTMENT_WEIGHTS` (Life Systems 6, Engineering 5,
Logistics 5, Security 4, Medical 3, Signals 3, Flight Ops 2) and the
rank by `RANK_WEIGHTS` (Crewman 6, Specialist 5, Chief 2, Officer 1).
It never rolls Command or Commander, even when one is passed in as an
override (#2800).

**Ranks are FLAVOUR, not mechanics** (owner-ruled 2026-08-20). They
exist to lend the theme gravitas — a dead chart still printing titles
— and nothing should ever check one. No authority, no pay band, no
gate. If deference to a designation ever becomes real it arrives as
content, and it arrives asked for.

### 4.1 Command is deliberately empty (owner-ruled 2026-08-20)

Nobody in the colony holds a Command designation, and that absence is
the point: the officers who mattered died, left, or never woke, and
what grew instead runs on tills and favours.

If Command ever enters play it does so as **artifacts, not people** —
ship logs and personal effects rather than a living officer. A locked
case in the Kaspar salvage yard, a log that still plays, a name on
the manifest with nobody attached. Lore that arrives as objects
cannot contradict itself, can be found rather than exposited, and
lands naturally in systems already built or spec'd: the Halcyon's
reclaimed hull, the decking layer's "everything is a file", the
manifest itself. That is the preferred shape if the question is ever
opened.

### 4.2 Vessel names

Three is enough to start. A fuller registry is wanted eventually —
the slowboats are a naming project of their own — but the chart works
with a handful, and every arrival can plausibly have come off one of
them.

## 5. The fourteen ratings (OWNER-RULED 2026-08-19)

The skill board was ruled final on 2026-08-19 and amended the same day
to fourteen: Agrotech in place of Biosystems, Chemistry added, and
Provisioning for the cooking lane. The ratings, their governing stats
and cants are `SKILLS` in `world/manifest.py`.

Broad but meaningful strokes (owner: Firearms, not pistols/rifles/
SMGs). Names read like manifest ratings and colony industry — and
deliberately broad so each rating keeps finding new uses (owner:
"opening them up with broader context is better").

| Key | Rating | Covers | Governing stats |
|---|---|---|---|
| `firearms` | Firearms | every trigger weapon in the armory | Motorics |
| `melee` | Melee | armed striking, bat to katana — **thrown weapons fold in here** (the weapon lives in the same hand) | Motorics + Grit |
| `unarmed` | Unarmed | strikes, holds, escapes, contests — the grapple spine (arrests, muggings, dragging, consent contests) | Grit + Motorics, canted Grit |
| `demolitions` | Demolitions | arming, placement, wiring, disarming, breach-craft (frags, sticky charges, demo charges, remote dets — all already in the armory). **The throw is free; the skill is the fuse.** | Intellect + Motorics, canted Intellect |
| `medicine` | Medicine | field bandage through surgery and autopsy | Intellect + Motorics |
| `systems` | Systems | everything done through a machine's interface: decking, consoles, radio & broadcast procedure, electronic locks (Signals folded in — the department keeps its name; departments ≠ skills) | Intellect |
| `engineering` | Engineering | repair, fabrication, maintenance | Motorics + Intellect |
| `piloting` | Piloting | vehicles, shuttle ops, heavy mobile machinery (the crane), navigation & survey | Motorics + Intellect |
| `agrotech` | Agrotech | the towers, fungary, snailery, husbandry — and the queued biology: cisterns, pump/water systems, waste-recycling, the terraform's leavings. (Named over "Biosystems" to keep clear of future Biotech/Cyberware, which the owner places near Medicine — that name space stays reserved.) | Intellect |
| `chemistry` | Chemistry | compound production — the substances registry's missing supply side: drug synthesis and refinement, reagents, solvents, explosive fillers. Boundary rules: **Medicine administers what Chemistry produces; Demolitions fuses what Chemistry cooks; if you'd serve it at a counter it's Provisioning, if you'd dose it it's Chemistry.** | Intellect |
| `provisioning` | Provisioning | feeding people at scale: butchery, cooking, mixing, preservation, rationing, potable brewing — carcass to counter. (Broadened + renamed from the culinary niche; "Foodworks" stands as the alternate if Provisioning's logistics smell grates.) | Motorics |
| `athletics` | Athletics | climbing, the jump edges, parkour ascents | Motorics + Grit |
| `stealth` | Stealth | moving unseen | Motorics |
| `subterfuge` | Subterfuge | lifting, locks, forgery-to-come | Motorics + Intellect |

**Deliberately absent: any social skill.** The LLM is the social
resolution system and trust/consent is the mechanical one; Resonance
carries innate presence. A social skill would fight both. If one
ever exists it arrives with a system that needs it, not before.

### 5.1 Seeding

Department seed packages (`world/manifest.py::seed_skills`): two
core ratings at creation (`DEPARTMENT_SKILLS`), in the rated band
(66–84 on the 0–150 scale, `BANDS`); a Chief takes the first one
listed below in the seasoned band (90–108), an Officer takes both
there; plus one more rating in the rated band, picked evenly from the
department's affinity list (`DEPARTMENT_AFFINITY`, below), skipping
any it already holds — nobody is only their job. The master band
(120–138) is defined, and nothing seeds it.

| Department | Core ratings |
|---|---|
| Command | Piloting + Systems |
| Flight & Orbital Ops | Piloting + Engineering |
| Engineering & Fabrication | Engineering + Systems |
| Life Systems | Agrotech + Provisioning |
| Medical & Cryogenics | Medicine + Chemistry |
| Security & Marshal Service | Firearms + Unarmed |
| Logistics & Stores | Systems + Athletics |
| Signals & Survey | Systems + Piloting |

Affinity lists (`DEPARTMENT_AFFINITY`):

| Department | Affinity list |
|---|---|
| Command | Firearms, Systems, Subterfuge |
| Flight & Orbital Ops | Athletics, Systems, Engineering |
| Engineering & Fabrication | Demolitions, Systems, Piloting |
| Life Systems | Athletics, Provisioning, Chemistry |
| Medical & Cryogenics | Chemistry, Subterfuge, Athletics |
| Security & Marshal Service | Melee, Demolitions, Athletics |
| Logistics & Stores | Subterfuge, Provisioning, Piloting |
| Signals & Survey | Stealth, Subterfuge, Systems |

## 6. Creation flows

A designation is rolled at every creation door: `commands/charcreate.py`,
`web/website/views/characters.py` and `world/souls/population.py`.
Every PC sleeve gets one (#3033).

- **Player decant** (New Game Experience): the Thawn-Harrison sleeve
  envelope — the chargen's branded artifact — prints the designation
  as its MANIFEST line on a player's first decant
  (`commands/charcreate.py::first_char_finalize`). The envelopes for
  a new sleeve from a template and for a flash clone do not print it.
  Assigned by weighted roll, Starfleet-Command-esque: you wake up
  already being someone. Whether players get one reroll is an owner
  call (§11).
- **NPC generation**: shuttle arrivals and `@spawnmob` people go
  through `world/souls/population.py::roll_person`, which rolls the
  traits first and the designation after, independently of each
  other. 📋 UNBUILT (no issue): roll the designation first and let the
  department weight the trait roll (NPC_TRAITS_SPEC §7):
  Security leans Plate-Nerved, Life Systems leans Greenhaus-Handed /
  Sunfollower, Signals leans Faraday-Souled, Logistics leans
  Rivet-Tight. Personality correlates with vocation without being
  determined by it.
- **Backfill**: build 100 (`scripts/builds/100_the_manifest.py`)
  gives the named cast in its `CAST` list the designations in §9 and
  rolls everyone else's at random. Build 162
  (`scripts/builds/162_strike_the_robot_from_the_manifest.py`) applies
  the berth rule of §3. Build 164
  (`scripts/builds/164_backfill_the_last_sleeves.py`) stamps player
  sleeves through `ensure_manifest`, one roll per person, shared by
  all of that person's sleeves. Nothing weights a roll by a soul's
  current role.

## 7. Where it shows

- **`score`/`@stats`** (`commands/CmdCharacter.py`): two rows,
  `Posting: Chief, Life Systems` and `Vessel:  SBL-0117 Halcyon Days`
  (`world/manifest.py::designation_rows`), then the rated skills best
  first (`rated_skills`; the sheet prints at most six), each as its A–Z
  letter (`letter_for`), or `(no ratings on file)`. Someone with no record
  reads `Designation: NONE ON FILE`. The one-line form
  (`world/manifest.py::designation_line`) is used by `@soul`, the
  decant envelope's MANIFEST stamp and the build-100 roster.
- **`@soul`** (`commands/CmdSoul.py`): designation on the individual
  card.
- 📋 UNBUILT (no issue): **LLM persona**: the designation joins the trait voice fragments
  (a Signals officer talks like one); STATE untouched.
- 📋 UNBUILT (no issue): **Terminals**: the Manifest as a readable
  file — look anyone up by name. (Forgery arrives with decking, not before.)
- **Social truth**: no mechanical deference in v1. Whether the
  constabulary salutes a Security designation, whether a Command
  officer can requisition anything at all — future content, owner's
  call, and the ambiguity is the point.

## 8. Explicitly out of scope (v1)

- The XP system (owner: it WILL come, for skills and stats both —
  but chargen is destiny until it does; nothing here ticks per use).
- Combat math changes.
- Department factions/pay/privileges (WSIS-adjacent — owner-pending).
- Manifest forgery (decking-gated).

## 9. Named-NPC designations (PROPOSED — owner approves each)

Build 100 (`scripts/builds/100_the_manifest.py`, `CAST`) gives these
designations to the named cast in the world. No ruling on them is
recorded on #2138.

| NPC | Designation | Why |
|---|---|---|
| Nikolai | Officer, Medical & Cryogenics | the doctor; watched the sleepers (was listed as Vance, who has since been retired from the world) |
| Petra | Chief, Signals & Survey | dispatch is the old comms watch |
| The Rook | Officer, Signals & Survey | the voice of the ship, still broadcasting |
| Ossie | Specialist, Engineering & Fabrication | the crane was almost his rating |
| Ezra | Chief, Logistics & Stores | the pawn counter IS a cargo hold — he keeps it |
| Bellows | Specialist, Logistics & Stores | knows what a shelf is worth |
| Marta | Chief, Medical & Cryogenics | she is the Kaspar Urgent Care doctor, not the pawn keeper |
| Sable | Crewman, Life Systems | stewarding was the closest the chart came to bartending |
| Sully | Crewman, Engineering & Fabrication | hull-slab bar, hull-rated hands |
| Lin | Crewman, Life Systems | galley rating; the cart is the galley |
| Ottilie | Specialist, Life Systems | butcher's rating, galley track |
| Del | Crewman, Signals & Survey | night watch then, night bar now |
| Vesper | — (no designation) | synthetic; never on a manifest — its OWN kind of record (Thawn-Harrison provenance), future seam |

## 10. Unbuilt

- 📋 UNBUILT (no issue): the LLM-persona fragment (§7). The trait voice
  fragments it joins (`world/souls/traits.py::voice_fragments`) are not
  wired to the LLM either.
- 📋 UNBUILT (no issue): the terminal Manifest lookup (§1, §7).
- 📋 UNBUILT (no issue): designation-first NPC rolls that weight the
  trait roll (§6).
- **P2+ (owner-gated)**: wiring, when the owner calls it ready —
  medicine's two existing check sites are the natural first, then
  each future system (decking, kitchens, mapping, breaching) claims
  its rating when it builds — never before.
- A fuller vessel registry is wanted eventually (§4.2).

## 11. Not decided

Awaiting the owner's red pen:

- Vessel names (§4) — two proposed: *Perpetual Noon*, *Golden Hour*.
- Department and rank names (§4).
- Named-NPC designations (§9).
- Per-skill A–Z word lists (with the display layer, §2).

Open questions:

- What dice roll against the check value (§2) — an explicitly open
  future consideration.
- Whether players get one reroll of their designation at decant (§6) —
  an owner call; propose: no — the manifest doesn't negotiate.
- Social truth (§7): whether the constabulary salutes a Security
  designation, whether a Command officer can requisition anything at
  all — future content, owner's call.
- Department factions/pay/privileges (§8) — WSIS-adjacent,
  owner-pending.

## 12. Related documents

- DESCRIPTIVE_STAT_SYSTEM_SPEC — the G.R.I.M. stats and the A–Z
  descriptor pattern the ratings share.
- NPC_TRAITS_SPEC — §11's background seam (this is its first tenant);
  §7 for the trait roll a department would weight.
- DECKING_MATRIX — "everything is a file"; where manifest
  verification and forgery arrive.
