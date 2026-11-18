# Graffiti System Specification

## Overview

Players tag walls with spray paint and scrub them with solvent. Paint and
solvent are finite, so players tag thoughtfully: paint is spent per
character, which curbs spam without blocking creativity. Each can holds a
fixed supply and deletes itself when empty. Paint comes in seven colours, set with `press`. Tagging and cleaning
are channeled acts that take public time. Both kinds of can work from the
inventory or from the hands (Mr. Hands), and both are also weapons.

All commands live in `commands/CmdGraffiti.py` (`CmdGraffiti`, `CmdPress`).
The cans are `SprayCanItem` and `SolventCanItem` in `typeclasses/items.py`;
the wall is `GraffitiObject` in `typeclasses/objects.py`.

## The cans

### Spray paint can (`SprayCanItem`)

| attribute | value |
|---|---|
| `aerosol_level` | remaining paint, default 256; 1 character = 1 unit |
| `max_aerosol` | starting capacity, 256 |
| `current_color` | the selected ANSI colour |
| `available_colors` | the colours `press <color>` can set |
| `aerosol_contents` | `"spraypaint"` (identifies the can type) |
| `weapon_type` | `"spraycan"` |

- Colours: red, green, yellow, blue, magenta, cyan, white. The palette is
  fixed to these seven.
- `press <color>` sets the colour absolutely (`SprayCanItem.set_color`).
  Nothing cycles the palette. The current colour persists across sessions.
- When the can empties it removes itself from the hands, then deletes itself.

### Solvent can (`SolventCanItem`)

| attribute | value |
|---|---|
| `aerosol_level` | remaining solvent units, default 256; a scrub uses up to 10 |
| `max_aerosol` | starting capacity, 256 |
| `aerosol_contents` | `"solvent"` (identifies the can type) |
| `weapon_type` | `"spraycan"` |

- It mirrors the spray can and uses the same aerosol system.
- `SolventCanItem.use_solvent` deletes the empty can without a word; the
  command is meant to do the narrating (see *Empty cans* below).

Both can types come from the `SPRAYPAINT_CAN` and `SOLVENT_CAN` prototypes in
`world/prototypes.py`, which give them the `aerosol_contents` identifier, the
256-unit capacity and their weapon stats.

### Finding a can

A can is found with the core `caller.search`, limited to what the character
carries, held cans included (inventory first, then the hands). A can answers
to its key, its aliases and an ordinal (`2nd can`). The cans' keys are the
names they show, `can of spraypaint` and `can of solvent`, so a can is found
by what the player sees as well as by its aliases. Carried and wielded cans
work the same.

### Empty cans

Empty cans delete themselves. The intent is that an empty can self-destructs
with narrative flair. Today the player sees a line in only one case: a full
tag that needs more paint than is left (the run-out line, below). These
empty a can with no message:

- a tag that uses exactly the last paint (`_land_tag` tests
  `paint_needed > paint_available`, strictly greater);
- an interrupted tag that empties the can (`_land_tag` takes its
  interrupted branch before the run-out branch);
- every solvent can (`_apply_solvent` has no depletion branch), so each
  solvent can vanishes unannounced on its 26th scrub.

This is a code gap, not a doc correction: the narration is what is wanted.
It is recorded in the audit ledger #2477 (`commands/CmdGraffiti.py` slice:
"Spec-promised empty-can narration never fires on exact exhaustion, on any
interrupted tag, or on solvent at all").

## The wall (`GraffitiObject`)

- One graffiti object per room, created on the first tag. Players examine it with `look graffiti`.
- A wall holds at most **7** entries (`GraffitiObject.db.max_entries`). The
  eighth tag silently erases the oldest one (first in, first out). The player
  gets no warning.
- Each entry reads `"Scrawled in <color> paint: <message>"`, shown in its
  colour. A missing colour falls back to white.
- Entries live in the persistent Attribute `db.graffiti_entries` and survive
  a server restart.
- Solvent replaces random characters with spaces, not deletion ("Wheel of
  Fortune" style), so a message keeps its layout and fades over several
  applications. The object persists through partial cleaning.
- Room description: while the room has graffiti it carries the line "The
  walls have been daubed with colorful graffiti". The line is added with the
  first entry and removed only when the graffiti object is deleted.

## `spray` (`CmdGraffiti`)

**Syntax:**
- `spray "message" with <spray_can>` — paint graffiti
- `spray here with <solvent_can>` — clean

**Routing.** `here with <can>` means clean; any other `<message> with <can>`
means paint (quotes optional). The can's `aerosol_contents` decides which
handler runs. The wrong pairing is refused:

- "You can't clean with [paint can] - it contains paint, not solvent"
- "You can't spray paint with [solvent can] - it contains solvent, not paint"

**Either act.** Both are channeled acts. You cannot move during one, and
violence interrupts it. If the can leaves you mid-act (taken from you, for
example), the act breaks at once and only the letters or units finished so
far land. You cannot `press` anything while tagging or cleaning.

### Painting

1. The can must have paint and the right contents. The message is limited to
   100 characters (the limit keeps room descriptions from bloating).
2. The act starts. The tagger reads "You shake <can>, the rattle sharp, and
   set to work on the wall." (`_handle_spray_paint_with_spraypaint`); the
   room gets its own line through `msg_room_identity`, and the public
   placement tell is "crouched at the wall, spray can hissing."
3. Tagging lasts 3 seconds plus 1 second per letter. The duration is the
   anti-spam rule and also the fiction: a longer tag stands you in public
   longer.
4. On completion `_land_tag` spends paint for the characters sprayed (1 per
   character) and writes the entry in the can's current colour. The tagger
   reads "You spray '<message>' on the wall with a can of spraypaint."
5. If a full tag needs more paint than is left, the message is cut to the
   paint available with an ellipsis, and the tagger reads: "You start to
   spray on the wall with a can of spraypaint, but it runs out of paint
   mid-message! You manage to spray '<truncated>...' before the can crumples
   up and becomes useless."
6. If the act is interrupted, the letters finished so far land with an
   ellipsis and paint is spent pro rata. The tagger reads "Your hand jerks
   away mid-letter…" (`_land_tag`), with its own room line.
7. A tag that lands, full or partial, files a `vandalism` crime report
   (`report_crime` in `world/director/crime.py`), with a crowd-gated
   witness.

### Cleaning

`spray here with <solvent_can>` cleans graffiti *and* blood pools (forensic
evidence), not graffiti alone.

1. Before the act starts, `_handle_clean_with_solvent` checks that the room
   holds a `GraffitiObject` or a `BloodPool` (or an object with
   `db.is_blood_pool`) to clean.
2. The act starts. The cleaner reads "You shake <can> and set to scrubbing.";
   the room gets its own line through `msg_room_identity`, and the public
   placement tell is "scrubbing at the wall, solvent fumes sharp."
3. Cleaning lasts 3 seconds plus 1 second per solvent unit worked in, at most
   10 units (13 seconds) (`CLEAN_SETUP_SECONDS`, `CLEAN_SECONDS_PER_UNIT` on
   `CmdGraffiti`).
4. On completion `_apply_solvent` spends the units and replaces that many
   random characters of graffiti with spaces. It also calls
   `BloodPool.clean_with_solvent` (`typeclasses/objects.py`) with a
   tool-quality roll. The cleaner reads "You apply solvent to the graffiti,
   watching the colors dissolve away".
5. Three seconds later everyone in the room reads "The colors break down and
   the solvent evaporates, taking the graffiti with it". The delayed line
   goes to whatever room the cleaner is in 3 seconds later. If they have
   left, it lands in the room they moved to, not the room that was scrubbed.
6. If the act is interrupted, graffiti is scrubbed pro rata, but blood breaks
   down only on a completed act: the solvent needs dwell time, so bailing
   mid-scrub leaves the evidence (the interrupt handler calls
   `_apply_solvent(..., include_blood=False)`).

Repeated applications are needed to remove a message completely.

## `press` (`CmdPress`)

**Spray-can syntax:** `press <color> on <spray_can>`

- The colour is checked against the can's `available_colors`. An invalid
  colour gets an error that lists the available colours, each shown in its
  own colour. A non-spray item is refused ("You can't press colors on
  <item>.").
- Works on carried or wielded cans.

`CmdPress` is also the game's general button router, in
`commands/CmdGraffiti.py`. The spray-can colour grammar is one branch of it
(`_press_spray_can`).

- `aliases = ["call", "push"]`. Bare `call` presses the local call button by
  name only, deliberately skipping the label tier (#2608).
- `press <button>` resolves against room objects flagged `db.pressable`
  (`_pressables`) in three tiers: exact name, then the machine's own button
  labels, then partial name (`_press_pressable`).
- `press <button> on <machine>` presses a named pressable
  (`_press_named_pressable`).
- Every name goes through the core `Character.search`, scoped with
  `candidates=` (#3783): the room's pressables for machines, the presser's
  contents (held cans included) for the spray can. Exact key or alias first,
  then a partial where each typed word starts a word of the key or an alias.
  A fragment from the middle of a word (`press ntal`, `press blue on pray`)
  names nothing. Ordinals pick among twins (`press 2nd kiosk`,
  `press blue on 2nd can`); with several matches and no ordinal the first is
  pressed.
- Tier 1 is the exact search, tier 3 the partial one, and tier 2 hands the
  raw text to each machine. A machine's own name counts as one of its
  buttons (`press dispenser on machine`), checked by the same search with
  `candidates=[itself]` and `exact=True`.
- Elevators, rental kiosks and the decant issue dispenser ride this router
  and have no spec of their own. The insurance terminal's press is in
  `specs/SLEEVE_INSURANCE_SPEC.md`.

## Combat

- Both can types are weapons, `weapon_type` `"spraycan"`.
- Stats: 2 damage, `burn` damage type (chemical burns), not ranged,
  one-handed (`hands_required` 1, set by the prototypes).
- 114 spraycan-specific combat messages across the initiate, miss, hit and
  kill phases, in the game world's corporate-dystopia tone
  (`world/combat/messages/spraycan.py`).

## Unbuilt

- 📋 UNBUILT (no issue) **Identical tag stacking** — repeated messages get
  consolidated with quantity descriptors.
  - Single: "Scrawled in red paint: WAKKA RULES"
  - Multiple colors: "Scrawled in |rp|ba|gi|yn|mt obsessively: WAKKA RULES"
  - Visual composition using ANSI color codes reflects spraypaint colors used
  - Euphemistic progression: few/several/many/countless/obsessively
    repeated/nearly everywhere
  - Display priority: unique tags first, stacked tags after (de-emphasized)
  - Rewards variety, discourages spam with vague acknowledgment
  - Cleaning interaction: solvent still works character-by-character,
    ignores stacking
  - Case-insensitive matching for consolidation, possibly via the
    `world/fuzzy.py` facade so near-duplicates (typo/variant tags)
    consolidate too (not built)

Further enhancement ideas, not built:

- **Graffiti aging mechanics** — fade over time
- **Gang/faction-specific colors** — restricted color palettes
- **Skill-based quality levels** — novice vs expert graffiti
- **Paint refill system** — economic sustainability
- **Advanced cleaning tools** — pressure washers, paint-over mechanics
- **Graffiti contests/events** — community engagement features

## Not decided

- **Who owns solvent-on-blood.** Owner call pending on whether this spec or a
  forensics/evidence spec should own the blood-cleaning behaviour.
- **The colour-cycling helper.** A cycling palette was specified but never
  wired to a command: `SprayCanItem.get_next_color` has no callers. It is not
  dead code to delete without an owner ruling.

## Related

- `specs/CHANNELED_ACTIONS_SPEC.md` — channeled acts; tagging and cleaning
  are two of its consumers (`begin_channel(... key="cleaning")` in
  `_handle_clean_with_solvent`).
- `specs/SLEEVE_INSURANCE_SPEC.md` — the insurance terminal's press.
- `world/director/crime.py` — `report_crime`, the vandalism report.
- The delayed cleaning line uses `evennia.utils.delay`.
