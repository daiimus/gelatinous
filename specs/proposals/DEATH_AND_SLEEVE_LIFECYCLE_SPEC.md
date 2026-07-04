# Death & Sleeve Lifecycle Spec

> **Status:** 📋 **CONSOLIDATION + PROPOSAL (2026-07-04).** §1–§7 **document
> shipped behavior** (traced from `typeclasses/death_progression.py`,
> `typeclasses/characters.py`, `typeclasses/corpse.py`, `typeclasses/accounts.py`,
> `commands/charcreate.py`) — this is the first single-source map of the
> end-to-end loop, which until now lived scattered across
> [`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md) (animation + timer),
> [`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`](../HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md)
> (corpse/forensics), and
> [`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
> (decant/sleeve). §8 (rough edges) and §9 (**optimization proposal — the
> DeathRecord spine**) are NOT yet built. **Recent change folded in:** dead NPCs
> are now **deleted**, not archived (#1022) — see §4.

---

## 0 · Why this exists

Two loops fire at the moment of death and have always been documented as if they
were unrelated:

- **The mortal loop** — die → corpse → decay → remains persist as world-state
  until a *cleanup gig* hauls them off. Physical, forensic, world-facing.
- **The sleeve loop** — die → archive the character → decant a new sleeve → play
  on. Account-facing, permanent, reviewable on the website (nostalgia).

They touch at exactly one point (`_handle_corpse_creation_and_transition`) and
then diverge. Because no document owned the whole path, the **PC-vs-NPC fork** and
the **"archived sleeves are permanent review records"** intent were unwritten —
which is how a corrupted DB index (#4590) and an NPC-ghost leak went undiagnosed
for a while. This spec makes the spine explicit so future work has one place to
reason about it.

---

## 1 · Death trigger — `Character.at_death()`

`typeclasses/characters.py:613`.

- **Idempotency:** guarded by the persistent flag `db.death_processed`. Set to
  `True` immediately (survives reload) so a character can never be processed
  twice, even under combat race conditions. (`ndb.death_processed` mirrors it for
  legacy checks.)
- **`death_count` is NOT touched here** — it increments exactly once, later, at
  the definitive point of permanent death (§5), so repeated `at_death()` calls
  can't inflate the Roman numeral.
- Sets `override_place = "lying motionless and deceased."` (the persistent visual
  tell), breaks stealth (`world.stealth.break_stealth`), and emits the death
  analysis to the `splattercast` audit channel.
- **Combat deferral:** if the dier is in active combat
  (`ndb.combat_handler`), the death curtain is deferred (flag
  `ndb.death_curtain_pending`) so the kill message lands first; a 5-second
  `delay()` fallback fires the curtain if combat doesn't. Otherwise the curtain
  shows immediately.
- Applies the death command-set restrictions (`apply_death_state`).

## 2 · Death curtain + progression timer (the revival window)

Animation: [`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md)
(`curtain_of_death.py`). On completion it calls `start_death_progression()`,
creating the **`death_progression` script** on the character
(`typeclasses/death_progression.py`).

Timing constants (`world/combat/constants.py`):

| Constant | Value | Meaning |
|---|---|---|
| `DEATH_PROGRESSION_DURATION` | 90s | total time from death to *permanent* death |
| `DEATH_PROGRESSION_CHECK_INTERVAL` | 30s | tick cadence (`at_repeat`) |
| `DEATH_PROGRESSION_MESSAGE_COUNT` | 11 | progression messages spread across the window |

- `at_script_creation` seeds `total_duration`, evenly-spaced `message_intervals`,
  `can_be_revived = True`, and `start_time`.
- **`at_repeat` (every 30s)** is the heart of the window:
  1. `_check_medical_revival_conditions` — **if `medical_state.is_dead()` has
     become False** (someone treated the fatal condition), call
     `_handle_medical_revival()` and abort the death. This is the *only* way back:
     the medical window is real, not cosmetic.
  2. Otherwise send any due progression messages.
  3. When `elapsed >= total_duration`, call `_complete_death_progression()`.

**Revival = medical, not chosen.** A dier comes back only if their vitals stop
reading as dead within the 90s window (blood/organ treatment). Past the window,
death is permanent.

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
  gender/skintone, and the medical snapshot (cause, conditions, blood type). Worn
  items transfer to the corpse via normal drop hooks.
- The whole method is wrapped in a deliberate guard (#469): a corpse-forge failure
  is logged loudly but never re-raises, so the progression always terminates
  (worst case: "archived without a corpse", never a per-tick retry storm).

## 4 · Character disposal — the PC / NPC fork

`_transition_character_to_death()`. After stopping/deleting the character's
medical scripts:

- **NPC (`account is None`) → DELETE.** (#1022) The corpse (§3) already holds the
  full forensic record, so the character husk is deleted outright and the method
  returns. Without this, every dead NPC used to pile up in Limbo forever as a
  nameless ghost (the #4590-era leak — some husks were ~12 days old).
- **PC (has an account) → ARCHIVE.** Move to Limbo (`#2`, `move_hooks=False`),
  unpuppet the session, then `archive_character(reason="death")`.

> The fork guards on `account is None` — only player characters ever carry an
> account — so it can never delete a PC.

## 5 · Archiving — `archive_character()` + the sleeve data model

`typeclasses/characters.py:456`. This is the **sleeve loop's** persistence step,
PC-only:

- `account.db.last_character = self` — seeds the respawn/decant flow.
- **`death_count += 1`** — the single authoritative increment; drives the Roman
  numeral suffix (`build_name_from_death_count`, `commands/charcreate.py:128` —
  `Jorge → Jorge II → Jorge III …`).
- Sets `db.archived = True`, `db.archived_reason`, `db.archived_date`.
- Moves to Limbo (`#2`) and disconnects sessions with *"Sleeve has been archived.
  Please reconnect to continue."*

**Sleeve attributes (canonical list):**

| Attribute | Where set | Purpose |
|---|---|---|
| `death_count` (AttributeProperty, cat `mortality`, default 1) | `archive_character` | Roman numeral suffix |
| `db.archived` | `archive_character` | the sleeve is retired |
| `db.archived_reason` / `db.archived_date` | `archive_character` | audit / sort |
| `db.current_sleeve_birth` | charcreate | sleeve age (web "Decant" page) |
| `db.death_processed` | `at_death` (persistent) | idempotency guard |

## 6 · Respawn / decant — closing the sleeve loop

[`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
+ telnet `commands/charcreate.py`. With an archived `last_character`, the account
decants a new sleeve: **3 random templates** or a **flash clone** (inherits stats,
appearance, sex from the archived sleeve). `death_count` sets the numeral.

**Archived sleeves are permanent, reviewable records — BY DESIGN.** They live on
in Limbo; `accounts.py` counts only *non-archived* characters against
`MAX_NR_CHARACTERS`, and the website surfaces past sleeves ("Decant Sleeve /
Manage Sleeves") for review. **Archived PC husks in Limbo are NOT garbage** — do
not "clean up" Limbo indiscriminately (this is the trap that the #4590 cleanup had
to carefully avoid: NPCs are ghosts, PC sleeves are history).

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

1. **Limbo is a junk drawer.** Archived sleeves *and* (formerly) NPC ghosts share
   `#2`; every "list my sleeves" / character-limit check is an O(n) scan filtering
   `db.archived`. No index, no dedicated store, no tag.
2. **Corpse↔sleeve link is one-way and stringly-typed.** The corpse stores
   `original_character_dbref` as a string; the archived sleeve has no
   back-reference. Reconstructing "which sleeve, died where, of what" means a
   manual join across three objects (character, corpse, medical snapshot).
3. **The permanent record dies with the body.** All death detail lives on the
   corpse. Because cleanup is a *gig* (§7) — a physical actor hauls the body away —
   once the corpse is removed, the death's history is gone. That's fine for
   in-game forensics (no body, no evidence — correct), but it means a PC's
   **nostalgic sleeve history has no home that survives corpse removal**.
4. **NPC deaths still spawn a full corpse + do a teleport dance** even though the
   husk is immediately deleted (§4). Fine at current scale; worth noting.

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

The fix: one small, immutable **DeathRecord**, written at permanent death (§3),
that marks the death's *existence* — nothing more. **It carries neither cause of
death nor location.** The player isn't owed an explanation, and a location is
actionable intelligence ("go check where I died"); the record is a **tribute**,
not a report. This sleeve was, and ended — a name and a date.

```
DeathRecord {                     # tiny, permanent; survives corpse removal
    id                            # stable key
    sleeve / account              # who died (null account = NPC → skip for web)
    when                          # death_time — a date on a memorial, nothing more
    corpse_ref                    # -> Corpse while it exists; null once a gig
                                  #   hauls the body away (internal key, never
                                  #   surfaced on the web view)
}
```

**Deliberate split — three layers, three lifetimes:**

| Consumer | Reads | Character | Surface |
|---|---|---|---|
| **Web "Manage Sleeves" / memorial** | DeathRecord (existence facts) + archived sleeve | **OOC** — a rare, deliberate exception to the everything-is-IC rule; a tribute to the player | light, sentimental, permanent |
| **In-game `autopsy` / forensics** | the **corpse** (organ inventory, wounds, medical snapshot) | IC | investigative — detailed, physical, disappears with the body |
| **Morgue records** *(future)* | an **IC database/file** a morgue populates with cause of death — readable AND **manipulable by players** (falsify a cause, erase an entry) | IC | the "everything is a file" layer; where cause-of-death *actually* lives once it exists anywhere |

Web review does **not** touch the autopsy layer, and cause of death never reaches
the OOC record at all — if a player wants to know *how* a sleeve died, that's an
in-game question with an in-game (and gameable) answer. The corpse does **not**
depend on the DeathRecord; they meet only at `corpse_ref`, which is allowed to go
null.

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
  a real two-way key via `corpse_ref` + the record id on the sleeve.
- **Sleeve listing stops scanning Limbo.** Tag archived sleeves (`sleeve:archived`)
  and/or index by account so listing is a tag/FK query, not an O(n) `db.archived`
  scan of the whole junk drawer (rough edge 1). Limbo stays *storage*, not the
  *query surface*.

**The cleanup gig (§7) pairs with this, built later with the gig system:**
disposal/sanitation contracts remove the physical corpse; the DeathRecord and (for
PCs) the archived sleeve are untouched. Until the gig layer exists, remains simply
persist — which is the desired behavior now, and doubles as free playtesting of the
"remains as tells" idea.

**Suggested build order (each shippable alone, additive, low-risk):**

1. **DeathRecord object** — write it in `_create_corpse_from_character`; stamp its
   id onto the corpse (`corpse_ref` back on it) and, for PCs, the archived sleeve.
   Purely additive; changes nothing play-facing.
2. **Web nostalgia review** — point "Manage Sleeves" at the DeathRecord's
   existence facts (who/when only — no cause, no location, no autopsy coupling).
3. **Tag/index archived sleeves** — convert the account/website sleeve listing off
   the Limbo scan.
4. **Corpse cleanup gig** — *deferred*, built atop the NPC-faction gig/freelancer
   loop. Removal nulls `corpse_ref`; the record persists. Until then, remains are
   intentional world-tells.
5. **Morgue IC records** — *deferred, further out*: a morgue actor populates an
   in-character database/file with cause of death as bodies come through;
   player-manipulable (falsify, erase) per the everything-is-a-file direction.
   This is where cause-of-death lives — never on the OOC record.
6. (Optional) **Skip the corpse teleport dance for NPCs** — spawn the corpse and
   delete the husk without the intermediate Limbo hop (§4/§8.4).

Step 1 is the whole spine; steps 2–3 are the near-term nostalgia + query wins;
steps 4–5 wait on the gig economy and the file/records layer respectively.

---

## 10 · Cross-references

- [`DEATH_CURTAIN_SPEC`](../DEATH_CURTAIN_SPEC.md) — animation + progression timer (§2)
- [`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`](../HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md) — corpse creation, autopsy, organ harvest, decay (§3, §7)
- [`WEB_RESPAWN_CHARACTER_CREATION_SPEC`](../WEB_RESPAWN_CHARACTER_CREATION_SPEC.md) + [`WEB_CHARACTER_CREATION_ALIGNMENT`](../WEB_CHARACTER_CREATION_ALIGNMENT.md) — decant flow + sleeve data model (§5, §6)
- [`IDENTITY_RECOGNITION_SPEC`](../IDENTITY_RECOGNITION_SPEC.md) — sleeve_uid, apparent_uid, signature snapshot at death (§3)
