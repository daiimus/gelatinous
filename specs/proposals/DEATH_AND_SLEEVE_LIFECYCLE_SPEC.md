# Death & Sleeve Lifecycle Spec

This spec is the single map of what happens from the moment a character dies
to the moment the account plays on. It draws on
[`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md) (animation + timer),
[`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`](../HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md)
(corpse/forensics) and
[`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
(decant/sleeve), and follows the code in `typeclasses/death_progression.py`,
`typeclasses/characters.py`, `typeclasses/corpse.py`, `typeclasses/accounts.py`
and `commands/charcreate.py`. §1–§8 describe the loop; §9 is the DeathRecord
design and the cleanup gig; §10 is the coup de grâce, designed and unbuilt.

---

## 0 · Why this exists

Two loops fire at the moment of death:

- **The mortal loop** — die → corpse → decay → remains persist as world-state
  until a *cleanup gig* hauls them off. Physical, forensic, world-facing.
- **The sleeve loop** — die → archive the character → decant a new sleeve → play
  on. Account-facing, permanent, reviewable on the website (nostalgia).

They touch at exactly one point (`_handle_corpse_creation_and_transition`) and
then diverge. This spec makes the whole path explicit, including the **PC-vs-NPC
fork** (§4) and the rule that **archived sleeves are permanent review records**
(§6), so that work on either loop has one place to reason about it.

---

## 1 · Death trigger — `Character.at_death()`

`Character.at_death` in `typeclasses/characters.py`.

- **Idempotency:** guarded by the persistent flag `db.death_processed`. Set to
  `True` immediately (survives reload) so a character can never be processed
  twice, even under combat race conditions. (`ndb.death_processed` mirrors it for
  legacy checks.)
- **`death_count` is NOT touched here** — it goes up once per archive, in
  `archive_character` (§5): at permanent death, and also when a living sleeve is
  shelved from the web. Repeated `at_death()` calls can't inflate the Roman
  numeral.
- Sets `override_place = "lying motionless and deceased."` (the persistent visual
  tell), breaks stealth (`world.stealth.break_stealth`), and emits the death
  analysis to the `splattercast` audit channel.
- **Combat deferral:** if the dier is in active combat
  (`ndb.combat_handler`), the death curtain is deferred (flag
  `ndb.death_curtain_pending`) so the kill message lands first; a 5-second
  `delay()` fallback fires the curtain if combat doesn't. Otherwise the curtain
  shows immediately.
- Ends any channel the dier was running and any procedure being performed on
  them (#2926), releases any call they were assigned to (#2255), and logs the
  death to the souls audit (#2318).
- Applies the death command-set restrictions (`apply_death_state`).

## 2 · Death curtain + progression timer (the revival window)

> **A destroyed brain is a death with a window**
> ([#3248](https://github.com/daiimus/gelatinous/issues/3248), 2026-09-26):
> `brain_integrity` reaches zero, `is_dead()` turns True and this progression
> starts. Only a brain install inside the window revives it (#3253,
> 2026-09-28).

Animation: [`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md)
(`curtain_of_death.py`). On completion it calls `start_death_progression()`,
creating the **`death_progression` script** on the character
(`typeclasses/death_progression.py`).

Timing constants (`world/combat/constants.py`):

| Constant | Value | Meaning |
|---|---|---|
| `DEATH_PROGRESSION_DURATION` | 90s | total time from death to *permanent* death |
| `DEATH_PROGRESSION_CHECK_INTERVAL` | 4s | tick cadence (`at_repeat`): 60% of the 8s message spacing (90 // 11), rounded down |
| `DEATH_PROGRESSION_MESSAGE_COUNT` | 11 | progression messages spread across the window |

- `at_script_creation` seeds `total_duration`, evenly-spaced `message_intervals`,
  `can_be_revived = True`, and `start_time`.
- **`at_repeat` (every 4s)** is the heart of the window:
  1. `_check_medical_revival_conditions` — **if `medical_state.is_dead()` has
     become False** (someone treated the fatal condition), call
     `_handle_medical_revival()` and abort the death. This is the *only* way back:
     the medical window is real, not cosmetic.
  2. Otherwise send any due progression messages.
  3. When `elapsed >= total_duration`, call `_complete_death_progression()`.
- **A beheading has no window** (#3835, 2026-11-14). The curtain completes the
  death as soon as it has told the room (`complete_a_beheading`). `at_start`
  skips the dying message and `at_repeat` skips the revival check and the
  progression messages; `at_repeat` finishes the death one tick later if the
  curtain's completion never ran.

**Revival = medical, not chosen.** A dier comes back only if their vitals stop
reading as dead within the 90s window (blood/organ treatment). Past the window,
death is permanent.

The window survives a reload (wall-clock `start_time`). After a crash,
`at_server_start` re-arms the timer. A death whose curtain was cut off by a
reload before the progression started is restarted at boot by
`sweep_wedged_deaths`. When the window closes, `_complete_death_progression`
interrupts any procedure still running on the body.

## 3 · Completion → corpse creation

`_complete_death_progression()` → `_handle_corpse_creation_and_transition()`.

- Sets `can_be_revived = False`, tells the room the form "grows utterly still …
  forever" (`msg_room_identity`), applies `apply_final_death_state`.
- `_create_corpse_from_character()` spawns a `typeclasses.corpse.Corpse` at the
  character's location and snapshots the **forensic record** onto it:
  `original_character_name` / `original_character_dbref` /
  `original_account_dbref`, `death_time`, `physical_description`, `sleeve_uid`,
  `sdesc_at_death`, the full identity signature + `apparent_uid_at_death`,
  `height/build/keyword` overrides (captured **then cleared** off the character),
  gender/skintone, and the medical snapshot (cause, conditions, blood type).
  `death_cause` is also mirrored onto the **character** (#1582), so the clone's
  envelope can print it (§6).
  Deployed integrated hardware is parked first and what was actually worn is
  recorded as `corpse.db.worn_at_death`; then everything the character carries
  moves into the corpse (`move_to`, quiet).
- The whole method is wrapped in a deliberate guard (#469): a corpse-forge failure
  is logged loudly but never re-raises, so the progression always terminates
  (worst case: "archived without a corpse", never a per-tick retry storm).
- After the archive (§4, §5), the corpse ref is stamped onto the sleeve's
  tombstone (§9).

## 4 · Character disposal — the PC / NPC fork

`_transition_character_to_death()`. After stopping/deleting the character's
medical scripts:

- **No account → depends on the body.** A generated NPC (`db.is_npc` True, not
  `db.essential`) is DELETED (#1022): the corpse (§3) already holds the full
  forensic record, so the husk is deleted where it lies, with no Limbo hop, and
  the method returns. Archived instead, every dead NPC would pile up in Limbo
  as a nameless ghost. An Essential Personnel NPC (`db.is_npc` and
  `db.essential`) is ARCHIVED to Limbo like a PC, so a resleeve restores the
  person (#2128). An accountless body without `db.is_npc` is archived with a
  `DEATH_TRANSITION_WARN` audit line and is never deleted.
- **PC (has an account) → ARCHIVE.** Move to Limbo (`#2`, `move_hooks=False`),
  unpuppet the session, then `archive_character(reason="death")`.

> The delete needs both `account is None` and `db.is_npc` True (a double guard),
> so a PC that dies with no account attached (an offline death) is archived,
> never deleted.

## 5 · Archiving — `archive_character()` + the sleeve data model

`Character.archive_character` in `typeclasses/characters.py`. This is the
**sleeve loop's** persistence step. It runs for every dead body that is archived
rather than deleted (§4), and for a living sleeve shelved from the web:

- The owning account (the `owner` passed in, else `world.ownership.owning_account`,
  since the body is already unpuppeted, #3667) gets `db.last_character = self`,
  which seeds the respawn/decant flow.
- **`death_count += 1`** — on every archive, including a web shelve of a living
  sleeve (as built); drives the Roman numeral suffix (`build_name_from_death_count`
  in `commands/charcreate.py`; `Jorge → Jorge II → Jorge III …`).
- Sets `db.archived = True`, `db.archived_reason`, `db.archived_date`.
- Adds the `archived` tag (category `sleeve`), the query index.
- Engraves the tombstone (`world.death_records.add_record`, §9); a failure here
  never blocks the archive. **Every archived sleeve gets a tombstone** — death
  or manual retirement alike; `died` is the archive moment.
- Moves to Limbo (`#2`) and disconnects sessions with *"Sleeve has been archived.
  Please reconnect to continue."*

`Character.is_archived` (reads the tag first) and `unarchive_character` (keeps
the attribute and the tag in sync) are the canonical accessors.

**Sleeve attributes (canonical list):**

| Attribute | Where set | Purpose |
|---|---|---|
| `death_count` (AttributeProperty, cat `mortality`, default 1) | `archive_character` | Roman numeral suffix |
| `db.archived` | `archive_character` | the sleeve is retired |
| `db.archived_reason` / `db.archived_date` | `archive_character` | audit / sort |
| `db.current_sleeve_birth` | charcreate | sleeve age (web "Decant" page) |
| `db.death_processed` | `at_death` (persistent) | idempotency guard |
| tag `archived` (cat `sleeve`) | `archive_character` | query index for the active/archived split |
| `db.death_cause` | `_create_corpse_from_character` (fallback in `_transition_character_to_death`) | PRIOR TERMINATION line on the clone's envelope |
| `db.imprint` | `_handle_corpse_creation_and_transition` | who the sleeve knew; restored onto a flash clone |

## 6 · Respawn / decant — closing the sleeve loop

[`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
+ telnet `commands/charcreate.py`. With an archived `last_character`, the account
decants a new sleeve: **3 random templates**, or a **flash clone** only if the
dead sleeve's insurance policy pays for it (#3667, see `SLEEVE_INSURANCE_SPEC.md`);
picking a template after an insured death forfeits the policy. A flash clone
inherits GRIM stats, desc and longdescs, sex, skintone, species, `sleeve_uid`,
height/build/hair, sdesc keyword, stack id, and the imprint of who they knew.
`death_count` sets the numeral.

> **Amendment 2026-09-25 (owner ruling, #3667):** the flash clone is gated on a **sleeve
> insurance policy** bought in advance at the Thawn-Harrison lobby terminal and
> consumed at decant. Die uninsured and that person does not return; the
> account may start a fresh character. See `specs/SLEEVE_INSURANCE_SPEC.md`.

**Decant presentation (#1572–#1591).** The finalize paths move the sleeve to
the spawn room *before* puppeting (no Limbo leak). The respawn/flash finale is
a framed narrative block whose sleeve-envelope label carries the record:
`CONTENTS` name+numeral, `DECANTED` TST date, and for flash clones
`PRIOR TERMINATION` + `DEATH COUNT`. `PRIOR TERMINATION` reads the
`death_cause` mirrored onto the character (§3). Bystanders see the decant as a
tech scene; logout reads as the sleeve going vacant. Conventions:
[`../NEW_PLAYER_EXPERIENCE_SPEC.md`](../NEW_PLAYER_EXPERIENCE_SPEC.md).

**Archived sleeves are permanent, reviewable records — BY DESIGN.** They live on
in Limbo; `accounts.py` counts only *non-archived* characters against
`MAX_NR_CHARACTERS`, and the website surfaces past sleeves ("Decant Sleeve /
Manage Sleeves") for review. **Archived PC husks in Limbo are NOT garbage** — do
not "clean up" Limbo indiscriminately: NPCs are ghosts, PC sleeves are history.

**Residence does not carry across a resleeve, by current design.** A DELETED or ARCHIVED-husk
tenant no longer holds their cube: `_prune_dead_tenancy` in `world/rental.py`
lazily clears the occupancy record and strips the stamped sleeve's grant on the
next market query (`cube.db.resident_sleeve` is stamped at claim so deletion
can't orphan the grant). The new sleeve claims fresh at the kiosk — the credit
follows the person; the grant followed the sleeve.

## 7 · Corpse decay lifecycle (mortal loop tail)

`typeclasses/corpse.py`. Just-in-time decay: `get_decay_stage()` maps elapsed time
to a stage (`fresh → … → skeletal`, ~1 week to full via `decay_stages`), lazily
refreshing the corpse key/aliases. Species-aware naming
(`get_species_corpse_name`; e.g. `human corpse` → `skeletal remains`, synth →
`deactivated synth` → `stripped synth frame`).

**Persistence is intentional — remains are world-state, not garbage (design
decision, 2026-07-04).** There is deliberately **no auto-reaper**. A corpse decays
to `skeletal` and *stays* until something in the world removes it. Two consequences
the design wants:

- **Uncollected remains are environmental storytelling.** A skeleton in a
  dangerous or hard-to-reach room is a tell for whoever comes later — someone died
  here; this place kills. The harder the room is to reach, the longer the story
  persists and the more it says.
- **Cleanup is an economic loop, not a background task.** Body/skeleton disposal is
  an **inevitable gig** — sanitation/removal contracts in the NPC-faction gig
  economy (see [growth direction: gig/freelancer/favor loop]). Removal is a
  *physical act by an actor*, not a timer. See §9 for how this pairs with the
  permanent record.

---

## 8 · Known rough edges

1. **Limbo is the store, not the query surface.** Archived sleeves share `#2`
   with everything else archived there. The `archived` tag (category `sleeve`)
   is the index: `Account._sleeves_split` / `active_sleeves` /
   `archived_sleeves` split an account's characters in ONE tag query, and both
   slot-count paths (`check_available_slots`, `at_character_limit`), the web
   decant view and charcreate read it. A `db.archived=True` without the tag is
   healed into the index on read, so an archived husk can never auto-puppet as
   active. The Sleeve Registry page still lists every sleeve on purpose — it is
   a registry, not a filtered view.
2. **Corpse↔sleeve link is one-way and stringly-typed.** The corpse stores
   `original_character_dbref` as a string; the archived sleeve has no
   back-reference. Reconstructing "which sleeve, died where, of what" means a
   manual join across three objects (character, corpse, medical snapshot).
   The account's tombstone (§9) holds both `sleeve_dbref` and `corpse_dbref`,
   which joins sleeve and corpse; the corpse link goes stale once the body is
   removed.
3. **The permanent record dies with the body.** All death detail lives on the
   corpse. Because cleanup is a *gig* (§7) — a physical actor hauls the body away —
   once the corpse is removed, the death's history is gone. That's fine for
   in-game forensics (no body, no evidence — correct). A PC's **nostalgic sleeve
   history** survives corpse removal only through the tombstone (§9).

   > **Owner ruling 2026-09-14 -- chrome stays on the corpse; you re-sleeve as a flesh bag.** Death costs you your augments: they remain on the body for the parts trade, and the new sleeve starts as stock species anatomy. This is ALREADY the code's behaviour -- the flash clone is created with fresh organs for its species and never copies the old body's organs (`create_flash_clone`, `commands/charcreate.py`) -- so this line records the rule the secondhand-chrome economy is priced on, not a change.
4. **NPC deaths still spawn a full corpse** even though the husk is deleted
   right after (§4). The husk is deleted where it lies, with no Limbo hop. Fine
   at current scale; worth noting.

> Note: corpse *persistence* is **not** on this list — it's a design feature (§7),
> not a defect.

---

## 9 · Optimization proposal — the **DeathRecord spine** (+ cleanup as a gig)

Two concerns share the death moment but want opposite lifetimes:

- **The body** — a *physical, removable* world object. Persists as a tell; a gig
  eventually hauls it off (§7). Carries in-game forensics for `autopsy` **while it
  exists**, and that's correct — remove the body, remove the evidence.
- **The death** — a *permanent fact*. A PC's sleeve history for web **nostalgia**
  must outlive the body (rough edge 3). NPCs need no permanent fact (no player to
  reminisce).

The DeathRecord is one small, immutable record that marks the sleeve's
*existence* — nothing more. **A tombstone: who the sleeve was, born, died.** It
carries neither cause of death nor location — the player isn't owed an
explanation, and a location is actionable intelligence ("go check where I
died"). A tribute, not a report.

`world/death_records.py` writes `{sleeve_dbref, name, born, died, corpse_dbref}`
to a plain attribute list on the owning account (`account.db.death_records`; no
new typeclass — the web view already reads the account). The sleeve's dbref is
its key. It is engraved from `archive_character` (§5), so every archive gets
one; the corpse ref is stamped after the archive in
`_handle_corpse_creation_and_transition`. `born` is the sleeve's
`db.current_sleeve_birth` (set at decant/creation — §5), falling back to the
object's creation date for legacy sleeves. `corpse_dbref` points at the corpse
while it exists; the cleanup gig (step 4) nulls it when it hauls the body away.
It is an internal key, never surfaced on the web view. Name, two dates, nothing else — everything a
headstone says, and everything it doesn't.

**Deliberate split — three layers, three lifetimes:**

| Consumer | Reads | Character | Surface |
|---|---|---|---|
| **Web "Manage Sleeves" / memorial** | DeathRecord (tombstone: name, born, died) + archived sleeve | **OOC** — a rare, deliberate exception to the everything-is-IC rule; a tribute to the player | light, sentimental, permanent |
| **In-game `autopsy` / forensics** | the **corpse** (organ inventory, wounds, medical snapshot) | IC | investigative — detailed, physical, disappears with the body |
| **Morgue records** *(future)* | an **IC database/file** a morgue populates with cause of death — readable AND **manipulable by players** (falsify a cause, erase an entry) | IC | the "everything is a file" layer; where cause-of-death *actually* lives once it exists anywhere |

Web review does **not** touch the autopsy layer, and cause of death never reaches
the OOC record at all — if a player wants to know *how* a sleeve died, that's an
in-game question with an in-game (and gameable) answer. The corpse does **not**
depend on the DeathRecord; they meet only at the corpse ref, which is allowed to
go null.

**The memorial is one surface.** The date of death is a `Retired` column on the
sleeve row of "Manage Sleeves", not a separate table — every death record points
at a sleeve already listed there. The column says "retired" because archiving
covers both a dead sleeve and a living one shelved from the web, and every
archive stamps the date it happened. **Archived does not imply dead** — a living
sleeve's Retired date is the day it was shelved, not a death.

> **On the OOC exception:** the game's flow is relentlessly in-character —
> perceived identities, obscured sources, IC records. The sleeve memorial is a
> **rare sanctioned break** from that: an out-of-character tribute to the person
> behind the account. Keep it minimal precisely so it stays a tribute and never
> becomes an information side-channel into live play.

**What it buys:**

- **The body can be hauled off by a gig without erasing the sleeve's story.** The
  DeathRecord (for PCs) persists in the account's memorial; only the physical
  evidence leaves with the corpse. Resolves rough edge 3 without an auto-reaper.
- **Web nostalgia reads one small object**, not a join across corpse + husk +
  medical snapshot (rough edge 2). The stringly `original_character_dbref` becomes
  a two-way key through the tombstone, which holds both `sleeve_dbref` and
  `corpse_dbref`.
- **Sleeve listing does not scan Limbo.** The `archived` tag is the query index
  (rough edge 1). Limbo stays *storage*, not the *query surface*.

**The cleanup gig (§7) pairs with this, built later with the gig system:**
disposal/sanitation contracts remove the physical corpse; the DeathRecord and (for
PCs) the archived sleeve are untouched. Until the gig layer exists, remains simply
persist — which is the desired behavior now, and doubles as free playtesting of the
"remains as tells" idea.

**The steps (each additive and independent):**

1. **DeathRecord object** — `world/death_records.py`, as described above. This
   is the whole spine.
2. **Web nostalgia review** — "Manage Sleeves" reads the DeathRecord's
   tombstone (name, born, died — no cause, no location, no autopsy coupling).
3. **Tag/index archived sleeves** — the `archived` tag (category `sleeve`) and
   `Account._sleeves_split` (rough edge 1, §5).
4. **Corpse cleanup gig** — 📋 UNBUILT (no issue). Deferred, built atop the
   NPC-faction gig/freelancer loop. Removal nulls the corpse ref; the
   record persists. Until then, remains are intentional world-tells.
5. **Morgue IC records** — 📋 UNBUILT (no issue). Deferred, further out: a
   morgue actor populates an in-character database/file with cause of death as
   bodies come through; player-manipulable (falsify, erase) per the
   everything-is-a-file direction. This is where cause-of-death lives — never on
   the OOC record.

Steps 4–5 wait on the gig economy and the file/records layer respectively.

---

## 10 · Coup de grâce — finishing a downed opponent  📋 **UNBUILT**

📋 UNBUILT ([#3247](https://github.com/daiimus/gelatinous/issues/3247)). Owner
direction, deferred to whenever the death loop is revisited.

### 10.1 · What happens today

After #1584 (a downed character no longer takes a defensive stance), attacking
a body is inert:

```
> attack <body>
You let out a sharp breath and circle <body>.   <- attacker's initiate
                                                <- the body emits nothing
[next tick] Your target has left combat...
[handler dissolves]
```

`process_attack` is **never called** — zero swings resolve, `blood_level` is
unchanged. The sweep ejects the body early in the round and the handler drops
below two combatants and dissolves *before* the attacker's turn arrives.

So "attackable as a body" is nominal: you posture at a corpse, combat
evaporates, and you have **spent a combat round to do nothing**. In a
multi-way fight that is a real tactical cost for a no-op, and it is the
specific unfairness this section exists to remove.

### 10.2 · The design

Two halves, both from the owner:

1. **It is an act, not a fight.** Finishing a downed opponent resolves
   immediately and deterministically — no roll, no initiative, no handler
   enrolment, and **no round cost to the attacker**.
2. **It destroys one vital organ at random**, rather than invoking the corpse
   process directly. *"Kinda a two in the chest, one in the head approach.
   The person could still be revived with an organ transplant but is much
   more unlikely."*

The second half is the important one: death stays **anatomical** rather than
becoming a flag. The victim is not marked unrevivable — they are *injured
past easy repair*, and revival becomes a surgical long shot instead of a
timer. This is consistent with how the rest of the medical layer works and
with the platform direction of removing state flags from bodies.

A coup de grâce is **bloodless by construction**: it destroys an organ
directly, with no accompanying wound.

### 10.3 · Measured organ lethality

Destroying each organ flagged `vital`, alone, after a vital-signs tick:

| organ | result | serves the design? |
|---|---|---|
| `heart` | dead | yes |
| `cervical_spine` | dead | yes |
| `brain` | **dead — a death with a window (#3248, 2026-09-26)** | yes, revivable only by getting the brain back |
| `liver` | survives, fully conscious | no |
| `pelvis` | survives, fully conscious | no |

`liver` does not kill because `digestion` is shared with the stomach, so
zeroing the liver alone does not zero the capacity. `pelvis` contributes to
no lethal capacity at all.

**A uniform random pick across the `vital` flag is therefore mostly a dud** —
the victim ends up awake and talking, which reads as the finishing move
failing. The pick wants weighting toward organs that mean something, not
uniformity across whatever carries the flag.

### 10.4 · Why this was blocked

The feature needs a "revivable but unlikely" state. Before #3248, the brain
looked like that state and was the trap: it was lethal only through the bleed
of the wound that destroyed it, so a bloodless brain-targeted coup de grâce
would have left a permanently unconscious body that never dies, never corpses,
never resleeves, and that `_check_medical_revival_conditions` (which only asks
`not is_dead()`) would hand back **whole** — *more* recoverable than if you had
done nothing.

**#3248 built `brain_integrity` on 2026-09-26** (owner ruling "Death with a
window"): a destroyed brain is a death that starts the progression, and only a
brain install inside the window revives it (#3253, 2026-09-28, closed the
in-place repair route). The "revivable but unlikely" state now exists for the
brain, which unblocked this feature. Full detail in
[#3248](https://github.com/daiimus/gelatinous/issues/3248).

### 10.5 · Undesigned — decide before building

These questions are listed under "Not decided" below.

### 10.6 · Related

- **#330** — decapitated / brain-destroyed characters skipping the
  death-progression window. **Same principle from the other direction:** #330
  is irreversibility arriving by accident of damage; this is a player choosing
  it. Both say the revival window is meaningless for irrevocable states, and
  they would design better together than separately.
  **Both cases are ruled.** A beheading has no window (#3835, 2026-11-14).
  A destroyed brain keeps its window (#3248, 2026-09-26, "Death with a
  window"): a brain transplant passes through it, so that state is not
  irrevocable.
- **#1584** — a downed character no longer takes a defensive stance.

---

## Not decided

Coup de grâce (§10), to decide before building:

- **What counts as "downed"?** Unconscious, dying-inside-the-progression-window,
  and dead-but-not-yet-corpsed are three different states. Mercy, murder and
  desecration are not the same act and would not read the same way.
- **"Unless one had already been destroyed."** Read here as *do not stack* —
  a victim already missing a vital organ is already finished or already in
  the long-shot state. The alternative reading, *pick at random from those
  still intact*, is a different rule once more than one is gone.
- **Does an unrevivable body still resleeve?** Medical revival and sleeve
  continuity are separate questions; this design only speaks to the first.
- **Witnesses.** Executing a downed person in front of people is the kind of
  act the crime and opinion systems would plausibly care about (§ see
  `world/director/civilians.py` reaction hooks).
- **Which organs can be picked, and with what weighting** (§10.3).

---

## 11 · Cross-references

- [`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md) — animation + progression timer (§2)
- [`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`](../HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md) — corpse creation, autopsy, organ harvest, decay (§3, §7)
- [`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md) + [`WEB_CHARACTER_CREATION_ALIGNMENT`](../WEB_CHARACTER_CREATION_ALIGNMENT.md) — decant flow + sleeve data model (§5, §6)
- [`IDENTITY_RECOGNITION_SPEC`](../IDENTITY_RECOGNITION_SPEC.md) — sleeve_uid, apparent_uid, signature snapshot at death (§Forensic Integration)
- [`SLEEVE_INSURANCE_SPEC`](../SLEEVE_INSURANCE_SPEC.md) — the policy that gates a flash clone (§6)
