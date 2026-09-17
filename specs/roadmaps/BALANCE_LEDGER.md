# Balance Ledger

> **Status:** 🛣 Roadmap reference — the register of every tunable constant, paired with the `# BALANCE:` tags in the constants files; the balance pass's worklist.

No system in this game has been balance-tuned yet. Numbers were chosen so
the mechanic could ship and be *played*, not because anything was sized
against anything else. This document exists so that when the balance pass
finally happens it starts from a list rather than a grep — and so that a
contributor who is about to build a consumer on top of one of these
numbers can see, in one line, that the number is provisional.

The register is the counterpart of the `#: BALANCE:` doc-comments in the
constants files. The comment says *why this number*, next to the number.
The row here says *what to watch when it is wrong*, in one place.

---

## How to use this document

- **Adding a tunable constant?** Declare it with a `#: BALANCE:`
  doc-comment at its declaration site and add exactly one row here. One
  constant, one row — no grouped rows, no "and friends".
- **The two lists are pinned to each other.**
  `world/tests/test_every_balance_knob_is_in_the_ledger.py` reads the
  `#: BALANCE:` declarations out of the constants files and the constant
  names out of this table and fails if either list has an entry the other
  does not. A knob added without a row breaks the suite, which is the
  point.
- **Removing a constant?** Its row leaves the ledger in the **same PR**
  that removes it from the code. A row for a constant that no longer
  exists is the same failure as a constant with no row.
- **"Tuned?" is No** until the balance pass actually visits the number
  and someone records what it was sized against. Shipping a number is not
  tuning it; neither is changing it once because it felt wrong in play.
- **Reading a row before building on it?** Take "Tuned? No" literally.
  Don't wire a new consumer onto an untuned number without recording the
  dependency and the prerequisite in that system's own spec.

---

## Gravity & falling (#3579)

All eleven are declared in `world/combat/constants.py`, section
**GRAVITY & FALLING (#3579)**, and consumed by `world/gravity.py` (the
fall, the landing, the sweep) and `commands/combat/jump.py` (the takeoff
roll, the direct drop, the slip in place).

| Constant (declaration site) | Value | What it tunes | Set by | Tuned? | What to watch in play |
|---|---|---|---|---|---|
| `FALL_SECONDS_PER_CELL` (`world/combat/constants.py`) | `1.0` | Seconds a falling body or object spends in each air cell before the next step down the column. Also the leap's one tick in the air. | #3579 owner ruling 2026-09-16 | No | Whether a watcher in the cell (or on a roof beside it) actually reads the pass-by line before the body is gone, and whether a 12-storey drop feels like a fall or like a lift. Owner: 0.5 s "is faster than any beat in the game" — combat rounds are 6 s. |
| `FALL_DAMAGE_PER_STORY` (`world/combat/constants.py`) | `5` | Blunt damage charged per cell actually passed, applied at the bottom. | #3579 owner ruling 2026-09-16 | No | The storey count at which a fall stops crippling and starts killing. The owner's target shape is "more likely to survive a long fall but leaving them crippled" — if long falls kill outright, this is the number, not the placement. |
| `FALL_LANDING_ABSORBED_CELLS` (`world/combat/constants.py`) | `2` | Storeys a **made** landing roll subtracts before damage is computed. Skill shortens the fall rather than dividing the damage. | #3579 owner ruling 2026-09-16 | No | Whether a two-storey drop landed well being *entirely* free reads as competence or as a free ride, and whether high falls stay unsurvivable-by-skill-alone. |
| `FALL_EDGE_DIFFICULTY_DEFAULT` (`world/combat/constants.py`) | `8` | Base landing difficulty on an edge exit that authors no `edge_difficulty`. | #3579 owner ruling 2026-09-16 | No | This is what most of the colony rolls against — every `@airfill` edge is bare. Watch the make-rate of ordinary roof descents at low Motorics. |
| `FALL_LANDING_DIFFICULTY_PER_CELL` (`world/combat/constants.py`) | `2` | Landing difficulty added per storey fallen (Motorics vs `edge_difficulty` + this × cells). | #3579 owner ruling 2026-09-16 | No | The altitude at which the landing roll becomes unmakeable. This is the only place altitude is allowed to enter the difficulty — see the note in `PARKOUR_TEMPLATE_LIBRARY.md` §1 invariant 2 about not double-counting it in `gap_difficulty`. |
| `GAP_DIFFICULTY_DEFAULT` (`world/combat/constants.py`) | `10` | Base takeoff difficulty for `jump across` on a gap exit that authors no `gap_difficulty`. | #3579 owner ruling 2026-09-16 | No | The failure rate of the span-1 crossing the roof city is built on. A gap missed is a full fall, so this number sets how punishing the second city is to learn. |
| `FALL_MAX_CELLS` (`world/combat/constants.py`) | `30` | Cells one fall may traverse before it stops cleanly where it is. A runaway-column guard, not a design number. | #3579 owner ruling 2026-09-16 | No | Only that it stays above the tallest real column (the crane is 17 storeys). If a legitimate fall ever hits this, the guard is too low, not the world too tall. |
| `FALL_BODYSHIELD_MADE_VICTIM` (`world/combat/constants.py`) | `0.75` | Share of the fall's damage the dragged victim takes when the grappler lands **well** on them. | #3579 owner ruling 2026-09-16 | No | Whether dragging someone off a roof is a reliable execution. Shipped behaviour preserved as a constant; never sized against anything. |
| `FALL_BODYSHIELD_MADE_GRAPPLER` (`world/combat/constants.py`) | `0.25` | Share the grappler takes when they land **well** on a dragged victim. | #3579 owner ruling 2026-09-16 | No | The cost of the tactic to the person choosing it. Paired with the row above — tune the pair, not one side. |
| `FALL_BODYSHIELD_FAILED_VICTIM` (`world/combat/constants.py`) | `1.5` | Share the dragged victim takes when the grappler lands **badly** — more than the whole fall, crushed on impact. | #3579 owner ruling 2026-09-16 | No | Whether a botched drag-off is lethal to the victim at heights where the grappler walks away. |
| `FALL_BODYSHIELD_FAILED_GRAPPLER` (`world/combat/constants.py`) | `0.5` | Share the grappler takes when they land **badly** on a dragged victim. | #3579 owner ruling 2026-09-16 | No | Paired with the row above. Together the failed split charges 2× the fall across two bodies; that was the shipped behaviour, not a decision. |

**Changed on the way (#3579, 2026-09-16):** the direct-drop bodyshield
split used to charge the victim 9 and the grappler 2 — 1.2 and 0.3 of a
per-exit `fall_damage` whose default was 8 — and now charges 3 and 1
(0.75 and 0.25 of one storey at `FALL_DAMAGE_PER_STORY` = 5), by ruling.
The ratios in the four rows above are the shipped transit-fall splits
preserved verbatim; it is the *base* they multiply that moved.

### Pending knobs

Not rows yet, because the constants do not exist yet:

- The jump-away bonus from #3583 joins this table when it ships. It is a
  gravity-adjacent number (it modifies a leap's odds, and a missed leap is
  a fall), so it belongs in the same section rather than in a table of its
  own.

---

## Gaps the ledger is NOT sized against

The rows above say what each number tunes. None of them says what it was
balanced *against*, because the things they would have to be balanced
against are themselves untuned or unbuilt. Recorded here so nobody reads
a "Value" column as a considered answer:

- **Bleeding is untuned.** Every chunk of fall damage that lands adds
  pain and, at ≥10 damage to a container, a bleeding condition. Bleeding
  rates have never been through a balance pass, so the real lethality of
  a fall is the damage-per-storey number *plus an unknown*. Tuning the
  damage number alone will not settle how many falls kill.
- **Container HP is wildly uneven.** The chest is ~22 points; the legs
  the fall fills first are ~150 points across both. That is a ~7× spread
  between "where a fall puts its damage" and "where damage kills", and it
  is the single largest reason a long fall cripples instead of killing.
  It is anatomy data, not a balance knob — no row here can fix it, and
  changing the damage numbers to compensate would be tuning the wrong
  dial.
- **Pulped legs do not stop anyone walking.** The `moving` capacity's
  only consumer today is dodge, so the crippling the placement model
  produces is presently cosmetic outside combat. Until a movement-policing
  substrate exists (`MEDICAL_SUBSTRATE_READINESS.md`, Phase 7), "leaving
  them crippled" is a description of the medical readout, not of what the
  character can do.

---

## See Also

- `world/combat/constants.py` — section **GRAVITY & FALLING (#3579)**; the
  `#: BALANCE:` doc-comments are the other half of this register.
- `world/gravity.py` and `commands/combat/jump.py` — the consumers of the
  eleven rows above.
- `specs/JUMP_COMMAND_SPEC.md` — the verbs that start a fall.
- `specs/PARKOUR_TEMPLATE_LIBRARY.md` §0 — the owner-ruled movement
  kernel the damage-per-storey number comes from.
- `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md` — the movement-policing
  substrate the third gap above is waiting on.
