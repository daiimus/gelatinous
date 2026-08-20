# Skills & the Pre-Planetfall Designation

> **Status:** 📋 **PROPOSAL — skill board RULED FINAL 2026-08-19**
> (the thirteen ratings, §5; check model §2). Still awaiting red
> pen: vessel names (§4, two proposed), department/rank names (§4),
> named-NPC designations (§9), and per-skill A–Z word lists (with
> the display layer). Builds on the
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
  What dice roll against the check value is an explicitly open
  future consideration; this spec defines the value, not the throw.
- **Skills modify, never replace**: a Master medic with ruined
  Motorics still shakes.
- **Wiring is deferred wholesale** (owner: "we'll wire them into
  everything when we're ready — for now, spec it out"). The
  first-consumer column in §5 is a promissory map, not a work order.
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
char.db.skills = {"biosystems": 78, "foodworks": 44}   # 0-150, A-Z displayed
```

Both identity-level: written at decant/generation, copied through
resleeve estate untouched. Absent keys read as 0 (Z — unrated, and
unprinted on score) — a soul or sleeve predating this spec is simply
unrated at everything until backfilled (build script).

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

## 5. The thirteen ratings (OWNER-RULED 2026-08-19)

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
| `biosystems` | Biosystems | the towers, fungary, snailery, husbandry — and the queued biology: cisterns, pump/water systems, waste-recycling, the terraform's leavings | Intellect |
| `foodworks` | Foodworks | butchery, cooking, mixing — the whole loop from carcass to counter, stills and ration-lines included | Motorics |
| `athletics` | Athletics | climbing, the jump edges, parkour ascents | Motorics + Grit |
| `stealth` | Stealth | moving unseen | Motorics |
| `subterfuge` | Subterfuge | lifting, locks, forgery-to-come | Motorics + Intellect |

**Deliberately absent: any social skill.** The LLM is the social
resolution system and trust/consent is the mechanical one; Resonance
carries innate presence. A social skill would fight both. If one
ever exists it arrives with a system that needs it, not before.

Department seed packages (two core ratings at creation; Chiefs take
one a band higher, Officers both; plus one weighted random
off-department rating — nobody is only their job):

| Department | Core ratings |
|---|---|
| Command | Piloting + Systems |
| Flight & Orbital Ops | Piloting + Engineering |
| Engineering & Fabrication | Engineering + Systems |
| Life Systems | Biosystems + Foodworks |
| Medical & Cryogenics | Medicine + Biosystems |
| Security & Marshal Service | Firearms + Unarmed |
| Logistics & Stores | Systems + Athletics |
| Signals & Survey | Systems + Piloting |

Security's weighted off-picks lean Melee/Demolitions; Engineering's
lean Demolitions; Life Systems' lean Athletics (tower work).

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

- The XP system (owner: it WILL come, for skills and stats both —
  but chargen is destiny until it does; nothing here ticks per use).
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
- **P2+ (owner-gated)**: wiring, when the owner calls it ready —
  medicine's two existing check sites are the natural first, then
  each future system (decking, kitchens, mapping, breaching) claims
  its rating when it builds — never before.
