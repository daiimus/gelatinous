# Sleeve Insurance Spec — a personal policy, bought in advance

> **Status: PROPOSAL (2026-09-25, revised the same day after a 48-agent
> read-only critique), not built.** Owner's framing: "We're going to have
> to revamp this whole thing at some point but for now we just want the
> intro framework to expand on." This is that framework, not the final
> shape. Tracks #3667. Supersedes the payment
> model in `NPC_POSTS_AND_REINCARNATION_SPEC.md` §2 (as-built premium notes)
> and §3, and the 2026-08-22 ruling that players resleeve free
> (`BACKUPS_AND_MEMORY_FORGERY_SPEC.md` §8.2). Small steps: §5 is sliced so
> each slice ships and is play-tested on its own; §6 is deferred on purpose.

## 1 · Owner rulings (2026-09-25)

Quoted where the words carry weight; otherwise paraphrased from the
conversation and the comments on #3667.

1. **Who pays: the individual, in advance.** On why a till paid: "Characters
   have token on them. I think this is incorrect. The real issue is if dead —
   the corpse can't pay for a clone, right? So it would be insurance —
   something they buy before hand and re-up if they die again." Asked whether
   to keep employer-paid insurance as spec'd: "No. This spec is wrong and
   likely hallucinated." (That was said of `NPC_POSTS_AND_REINCARNATION_SPEC`
   §3.)
2. **Who gets paid: the cloning center.** "Also, it wouldn't go to the
   clinic... we have the cloning center." Thawn-Harrison, not Maxwell's.
3. **Where: a terminal in the Thawn-Harrison lobby**, room #1986. "A terminal
   makes sense." A press-fixture in the rental-kiosk shape. "Gameplay-wise it
   makes sense to have it outside of Thawn-Harrison but we can address that
   later. For now, the lobby makes sense." **It takes a DNA sample:** "it
   should be taking some kind of DNA sample, right?" The policy is keyed to
   the buyer's biometric, the sleeve uid the lockers already key on.
4. **Price: free for now.** "We haven't balanced the economy at all. So,
   maybe they should be free for now, and we can add a cost later?" One
   constant, set when the balance pass happens; the act of buying stays.
5. **Nobody is seeded on day one.** Asked whether the ~23 named keepers start
   insured, the owner chose "Nobody. Everyone has to walk to the lobby
   first. Until then, a death means the post is simply rehired." ("2 makes
   the most sense. Might as well solidify the loop.") This is a ruling about
   day one, not about who gets the urge to buy (see §7 Q1).
6. **Players are in the loop.** Asked whether players must visit the terminal
   too, with "die uninsured and *that* person doesn't come back; the account
   can still start a fresh character" spelled out: "1, please."
7. **Direction:** "We'll need to expand on the sleeve system and they'll all
   likely be 'files' for decking inevitably but for now small steps." Build
   nothing decking-specific; shape the record so a file view can expose it.

On Maxwell's "a Thawn-Harrison billing terminal" the owner said only: "No
idea why it ended up in the clinic. That's really weird." No ruling was given
on what happens to it (§7 Q4).

## 2 · The model

* **A sleeve policy is an off-body record**, one per sleeve uid, held by
  Thawn-Harrison. Off-body because bodies are deleted (non-essential NPCs)
  or archived (PCs, essential NPCs) at death; a flag on the body dies with
  it. One per uid because a lineage shares its uid (`create_flash_clone`
  copies it, `imprint.restore` writes it back), so stacking records would
  stack lives: a second press answers "already on file".
* **Bought at the terminal by the living presser only.** Key on
  `sleeve_uid_of(presser)`, refuse `None` (the rental precedent,
  `world/rental.py:233`), refuse a dead, dying, archived or unconscious
  presser. The terminal never samples a held object: a corpse and a severed
  head carry the uid too.
* **Redeemed only by the body that bought it.** The record stores
  `buyer_dbref`; a payout requires the dead body's id to match. Every
  archived husk in a PC lineage carries the same uid, and the web archive
  view will re-archive an old husk and make it `last_character`, so uid
  alone would let an old husk spend a living body's policy. The mirror
  rule at the terminal: "already on file" only when the record's buyer is
  the presser; a record whose buyer is a dead or archived body of the same
  lineage is void, and the presser's purchase replaces it. Otherwise a
  return that did not consume the record (a flash clone before Slice C)
  would leave a row the living body can neither redeem nor replace.
* **Taken atomically before the body is built, put back if the build
  fails.** Django runs under Twisted's thread pool; the web POST and the
  telnet menu can both read a record before either consumes it. With one
  store row per uid, "take" is `ServerConfig.objects.filter(db_key=k)
  .delete()` requiring a count of 1; the loser gets a clean refusal, never
  a body. A purchase is a `create()`, and an `IntegrityError` is "already
  on file". The payout is a **sequence of steps, each with its own undo**,
  never a database transaction (the web door runs on a pool thread; on
  SQLite `transaction.atomic` across the build would hold the write lock
  against the game loop, and the idmapper cache does not roll back). Verify
  per path: an NPC body is alive, unarchived, in the decant room, with the
  keeper installed; a PC clone is created, unarchived, not dead, and carries
  the record's uid (the callers move it out of Limbo afterwards, so
  location is not checked inside `create_flash_clone`). On failure: restore
  the row; delete a freshly built body (rebuild, flash clone); for a revived
  archived NPC, which is the person's only copy, move the body back to Limbo
  and restore the archived attribute and tag directly, never delete it and
  never re-archive through `archive_character` (that bumps `death_count`).
* **Redeemed for a death only** (Q3). The source body must be archived with
  `reason="death"`; a shelved living body (`reason="manual"`) never
  redeems, and the shelve page says so. Never redeemed while the source
  body can still be revived: refuse while it carries a `death_progression`
  script or is `death_processed` but not yet archived. Do not rely on
  timing: the web archive view can archive a dying body today.
* **Payout is keyed to the person who died, not to the post.** Today
  `_try_resleave` picks its body by the shift's blueprint (`_archived_keeper`
  takes the newest archived body carrying it) and restores the shift's last
  snapshot, which belongs to whoever last died on that shift, a hired
  successor included. Under this spec the dead keeper is identified
  concretely (§3), and only that person is restored.

### Record shape

```
sleeve_policy:<uid> = {
    "uid": <sleeve uid>,          # the sample
    "bought_at": <epoch>,
    "buyer_key": <display key at purchase>,
    "buyer_dbref": <int>,         # the only body that can redeem it
    "blueprint_key": <str|None>,  # NPC cast
    "account_id": <int|None>,     # PC
}
```

**Storage: one `ServerConfig` row per uid** (`db_key` is unique and 50 chars
fits), the store the house already moved durable data to. Not a
`GLOBAL_SCRIPTS` entry: Evennia recreates a managed global script whenever
its settings entry changes, and the WSIS ring was moved off one for exactly
that reason (#2672, `world/wsis.py:108-116`). Not on the lobby fixture (a
re-run build or a deleted terminal would wipe every policy, the #3565
class). Not on an attribute named `register` (`economy._reconcile_till_tags`
adopts any such object as a tithed till). Only in-process code writes it
(the terminal, the payout, an in-game staff verb); never a build script.
Phase 1 reads the store directly; a cache comes only after a measurement.

## 3 · Where the gate goes (verified against code, 2026-09-25)

**Who the dead keeper is.** The sweep stamps a vacancy when a slot's keeper
is dead (`posts.py:410-412`); at that moment it must also record the
keeper's `sleeve_uid` and `id` into the slot, before a deleted reference
reads back as `None`. `imprint.capture` gains `blueprint_key` and `dbref`
(`restore` ignores them). Then:

| Return path | Body | Gate + take | Notes |
|---|---|---|---|
| Archived NPC (essential) | `slot["keeper"]` itself, when it is archived and its `blueprint_key` matches the shift's | in `_try_resleave`, take before the revive, verify after | restore from the body's own `db.imprint`, never the post snapshot; `_archived_keeper` (blueprint-keyed) is retired |
| Blueprint rebuild (keeper deleted) | `build_npc(bp_key)` | same call | only when the shift snapshot's `blueprint_key` matches the shift's and its `dbref` matches the stamped keeper; otherwise the outcome is successor and the record is left unspent |
| PC, telnet respawn | `create_flash_clone` | inside the function, take before `account.create_character`, verify after the full build | the `[4]` option is display only |
| PC, web respawn | same function | same | the POST reads `account.db.last_character` raw and skips `respawn_candidate()`; enforcement lives in the function, and the POST catches the refusal |

**The legacy `post_memory_snapshot`** (written by `snapshot_keeper_memory`,
`world/npcs/posts.py:28-62`, with no `sleeve_uid`, `blueprint_key` or
`dbref`) is never a payout source; the fallback at `posts.py:660` goes.

**The sweep's owned branch** (`posts.py:446-459`) gets three outcomes:
*resleeve* (a policy the dead keeper can redeem), *successor* (no policy, a
blueprint that raises, or `RETURN_ATTEMPTS` failed returns on one vacancy),
and *hold* for transient states (the keeper is alive elsewhere, dying or not
yet archived, or a return failed and may be retried). Today every
`False` hits `continue`, the #3565 "dark forever" shape. An uninsured
fallthrough clears the shift's ownership, `post_blueprints[shift]`; the
legacy `post.db.post_blueprint` fallback is gone from the code, and build
168 removed its four live rows. The archived body is left in Limbo as
others are.

**`post_policy` loses its `resleave` value.** The post no longer decides who
comes back; the person's record does. A post decides only whether strangers
may be hired: `successor` or `None`. The eleven blueprint `'policy':
'resleave'` entries, build 098's writes, `posts.py:464` and the NPC_POSTS §4
column change in the same PR, **with an in-process data build** that
censuses live `post_policy` values and rewrites `resleave` to `successor`
(the Rook's chair too: Q2 accepted that it goes dark after his death, so
it becomes `successor` like the rest and stays dark only because nobody can
reach it); the build's own census output is the check that no live post
still carries `resleave` (a unit test cannot see the live rows; the source
pin `TheOldModelIsGone` covers the code). Build 098 already wrote `resleave` into
the live rows; editing the reader alone would send every one of those posts
down the fallthrough and then `continue` forever, the #3565 shape. Build
098's "resleeve-only: no stranger is ever seated" for the Rook's chair is
overturned by ruling 5; the chair stays dark for another reason (§7 Q2).

**Two more places or the gate leaks:**

* `ensure_dispatch_operator` respawns "Petra" by name on every server start
  and reload, policy or not (`world/director/population.py:322-375`). The
  2026-09-05 ruling (#2762) it cites asks that the desk follow "the same
  rule every other post follows"; the implementation bypasses that rule
  with a free resleeve. Retiring it makes the desk follow ruling 5 like
  every other post; the 2026-08-22 ruling still holds (an empty desk answers
  in the automation voice). Retire it, `spawn_dispatch_operator`, the import
  at `routines.py:470` and the call at `:474` only (`ensure_comms_fitted`
  and `ensure_base_station` stay), and census any blueprint-less Petra it
  already made.
* `account.db.last_character` is not written at death: the account is
  cleared by unpuppet before `archive_character` runs
  (`death_progression.py:1059-1071`). A web-only player then sees no clone
  card at all. Resolve the owner at death with
  `world.ownership.owning_accounts(character)` (the playable-characters
  record, which survives logout), not a capture taken while puppeted, which
  is `None` for a player who disconnected mid-death. Test the disconnect
  case.

## 4 · How an NPC goes to buy

* A derived need, `insurance`, in `PROFILES["human"]` and `["synth"]` with
  its own planner shape and `plan_for` branch, and a branch in both
  `pressures()` and `pressure()` (the wardrobe pattern); the robot and
  recluse profiles are left out. Pressure 0.0 when this body can redeem a
  record (uid on file **and** `buyer_dbref` is this body), else a constant
  just above SOFT (0.60, the provisional-clothing analogue), so it is
  elected in the soul's own time (band 3), never over a shift.
  `_goal_band["insurance"] = 3`.
* **Who gets the need: every human and synth soul** (owner ruling
  2026-09-25, Q1: "2"). For souls with no rebuild path today (hired
  successors, generated residents, essential cast with no blueprint such as
  Ossie and Nonna) the record is bought but cannot yet pay out; §6 owes them
  a person-keyed rebuild. `essential` is not the test of who can return; a
  `blueprint_key` naming the shift they hold is.
* Plan: `[travel → lobby, press <BUY_BUTTON> on <terminal>, insured]`.
  The terminal is found by its **index tag** (`insurance_terminal` /
  `machines`, the crane's idiom), not through `_advertisers`, whose
  radius cap of 30 can hide the lobby from a soul standing in the
  Brackett; no advertiser data is needed.
* The press step names the button (`press insure on <terminal key>`,
  which `_press_named_pressable` handles), and the `insured` step that
  follows faults unless `insurance.covers(soul)` is now true, or the need
  would re-fire every think. The button is one constant on the terminal
  (`InsuranceTerminal.BUY_BUTTON`), read by the planner.
* Robots never elect a band-3 need (always on duty) and are replaced by
  chassis. Pinned souls never think and stay uninsured until unpinned. The
  Rook has the `recluse` profile and cannot leave the seal (§7 Q2).

## 5 · Phase 1, in slices that ship one at a time

**Slice A — the terminal and the record. SHIPPED 2026-09-25 (PR #3671):**
`world/insurance.py`, `InsuranceTerminal`, build 167 (terminal #26167 in
the lobby), `create_flash_clone` spends the dead body's own record. As
built, two details the review sharpened: the INSERT happens in one place
(`_insert`, the row built with the pickled value and saved inside the
try, because `ServerConfig.value`'s setter saves on assignment), and the
clone hook is `spend_policy(uid, body_id)`, never a void by uid alone.
Null-uid census: 8 of 75 characters, all accountless husks; backfill or
exclusion is Slice C's. `InsuranceTerminal`
(`typeclasses/terminals.py`; `press insure`, `press status`), branded
Thawn-Harrison, built in room #1986 by a build script; `POLICY_PRICE = 0`
in one place; the `ServerConfig` registry with take/put-back; the census of
null `sleeve_uid` characters, backfilled in-process before any gate ships.
Because players can buy from this slice on but the clone gate is Slice C,
`create_flash_clone` **voids the lineage's record from Slice A on** (no
gate yet, only consumption), so no clone ever leaves a row its living body
cannot replace. Play: Iver buys, is refused twice, reads his status.

**Slice B — NPC return. BUILT 2026-09-25 (PR #3672), as below with these
as-built notes:** the return answers RESLEEVED / HOLD / SUCCESSOR; the
dead keeper is the slot's own body (reference, else the `dead_id`
stamp; a slot stamped with a body that is gone never falls back to a
namesake), and only a slot that went dark before the stamp existed uses
the newest archived body of the blueprint, with the policy record as the
identity check; a dead body not yet archived (progression running, or a
wedged death) is HOLD, never rebuilt; a failed revive puts the body back
exactly as it was (dead, archived, `death_processed`), a failed rebuild
deletes the fresh body, both restore the record, and after
`RETURN_ATTEMPTS` (3) failures on one vacancy the outcome is SUCCESSOR
with the record unspent; the rebuild snapshot must match the stamped
`dead_id` where one exists; an archived body never holds a slot
(`_slot_held`); the terminal is found by index tag, not advertiser;
`INSURANCE_PRESSURE` is exactly SOFT so a risen meal always wins; the
legacy `post_blueprint` fallback is gone from code and its four live rows
removed by build 168, which also relabelled 12 posts, stripped 2
`post_insurer` rows and re-keyed Maxwell's register. The dead-keeper
stamp in the slot; `imprint.
capture` gains `blueprint_key`/`dbref`; `_try_resleave` keyed to the person
with take-before-build; the three sweep outcomes with ownership cleared on
fallthrough; `post_policy` loses `resleave`; the `insurance` need,
tag lookup and named press step; `ensure_dispatch_operator` retired; the
`post_policy` data build; the Maxwell terminal re-key (Q4). **Old model deleted in the same PR** (grep runtime
code and tests to zero; historical build scripts and bannered specs are left
as they are): `RESLEAVE_PREMIUM`; `post_insurer` (code, build 098:65, a
data build to strip the attribute rows); the `resleeve_premium` audit line;
the premium debit and the Maxwell credit block in `_try_resleave`
(`posts.py:629-655`, the `provider = next(search_object(...))` block: check
`posts.py` for `provider`, `RESLEAVE_PREMIUM` and `billing "`, since the
literal is split across two lines and a grep for it is already at zero);
`_archived_keeper`; the legacy snapshot fallback at `posts.py:660`;
`spawn_dispatch_operator`; and the stale prose: `posts.py` lines 12, 14,
27, 319-320, 459 and the `_try_resleave` docstring, `world/npcs/posts.py:
28-35` (`snapshot_keeper_memory` still says "resleave restores it"),
`world/npcs/blueprints.py:14`, `death_progression.py:1018-1021`. **Tests
that pin the old rule and must change:** `test_shift_fallthrough` (setUp
sets `post_policy='resleave'` at :29, so `test_an_unowned_shift_gets_a_
successor` and `test_a_shift_whose_owner_is_alive_is_not_theirs_to_wait_
for` break too, plus `test_an_owned_shift_still_waits_for_its_own_person`),
`test_souls_posts` (`test_a_broke_till_cannot_pay_the_premium`, the
`post_insurer`/`register` fixtures, `test_resleeve_restores_the_imprint_
minus_the_gap` which patches `_archived_keeper` and restores from the post
snapshot, the `_sweep` helpers that patch `_try_resleave`,
`test_post_policies_valid` narrowed to `(None, 'successor')`),
`test_the_money_leaves_a_record.py:43` (pins the literal
`resleeve_premium`), the `_try_resleave` source pin in
`test_death_survives_a_reload_and_a_resleeve.py:162`, `test_no_duplicate_
keepers`, `test_dispatch_operator_upkeep`, `test_director_population.py:
269`. `test_no_policy_means_the_slot_stays_dark` passes unchanged.

**Slice C — the player gate, last.** `create_flash_clone` gate with
take-before-build and restore-on-failure; one refusal constant used by both
doors; the web POST catches it; `last_character` resolved at death;
`CharacterArchiveView` refuses a sleeve that is already archived and its
"Stack ID preserved for future respawn." message tells the truth for an
uninsured sleeve; both template finalizers void the dead lineage's record
(Q5); and,
**before the gate can bite, a way for players to know:** a help entry and a
line in the decant scene or on the issue dispenser pointing at the lobby
terminal, since every existing player character starts uninsured and an
uninsured death is permanent. `test_the_card_names_who_you_become.py:80`
calls `create_flash_clone` with no policy and changes. Specs that describe
the flash clone and change with this slice: `WEB_RESPAWN_CHARACTER_CREATION
_SPEC`, `EVMENU_PATTERNS_SPEC`, `NEW_PLAYER_EXPERIENCE_SPEC`,
`WEB_CHARACTER_CREATION_ALIGNMENT`.

Each slice: tests with controls against master, the adversarial review,
played live as Iver, then the spec promoted or amended.

## 6 · Deferred, on purpose

* The price, and where it goes (the terminal then earns into a
  Thawn-Harrison register, which becomes a tithed till).
* Moving the terminal outside Thawn-Harrison.
* Returns for people who have no rebuild path today: hired successors,
  generated residents, civilians (deleted at death), and essential cast with
  no blueprint (Ossie, Nonna). A person-keyed rebuild from the imprint is the
  prerequisite.
* Un-shelving a living sleeve (see §7 Q3).
* Records as decking files.
* **Synths and the fiction of return.** Vesper, the Rook and Bellows are
  `synthetic_humanoid`. Today they return through the same code and the
  same "sleeve envelope" decant scene as humans; nothing synth-specific
  exists (owner asked 2026-09-25 whether synths even clone out: they do,
  identically). Whether a synth is grown at Thawn-Harrison at all, or comes
  back some other way, is unasked.

## 7 · The six design questions (all ruled 2026-09-25)

1. ~~Who gets the urge to buy?~~ **Ruled 2026-09-25: every human and synth
   soul** (option 2), even where a policy cannot yet pay out.
2. ~~The Rook.~~ **Ruled 2026-09-25: "1. We accept for now."** He cannot
   leave the seal, stays uninsured, and after his death the chair goes dark
   (no policy; no successor can reach the seal). The recluse's cost, for
   now; a way to the terminal is a later build if ever wanted.
3. ~~Shelving a living character.~~ **Ruled 2026-09-25: "1 for now is
   fine."** A policy pays for a death only: redemption requires the source
   body archived with `reason="death"`. Shelving (the web archive of a
   living body) never spends a policy, and a shelved living body cannot be
   flash-cloned back; the shelve page warns. Un-shelving stays in §6.
4. ~~Maxwell's "a Thawn-Harrison billing terminal."~~ **Ruled 2026-09-25:
   "1."** Keep it and re-brand it as Maxwell's; the till, the `treatment`
   advertiser and the `medic` post stay. The re-key keeps "billing terminal"
   in the key (build 074's finder matches on that substring; a re-run would
   otherwise create a second terminal and a second medic post). Slice B
   carries the rename as a data build.
5. ~~Template after an insured death.~~ **Ruled 2026-09-25: "1".** Picking
   a fresh character after an insured death spends the policy: both
   template finalizers (telnet and web) void the dead lineage's record, so
   no orphaned row can revive an abandoned self later.
6. ~~Delay on fallthrough.~~ **Ruled 2026-09-25: "Default behavior makes
   sense."** Each post keeps its own `post_delay` (census 2026-09-09,
   `posts.py:421`: 72 h on ten posts, 6 h on five, 24 h on two, 600 s on
   two) before a successor is offered; a balance-pass number, untouched.

## 8 · Holes the design closes (from the 2026-09-25 checks)

* Per-shift snapshots belong to whoever last died on the shift; keying a
  payout on them can spend a successor's policy to rebuild the namesake with
  the successor's memories. Closed by the dead-keeper stamp, the
  `blueprint_key`/`dbref` match, and restoring from the body's own imprint.
* The two respawn doors can both pass a check before either consumes.
  Closed by take-before-build on a unique store row.
* An older husk in the lineage can spend a living body's policy. Closed by
  `buyer_dbref`.
* A dying body can be archived from the web and cloned while its death still
  runs. Closed by refusing while a death progression exists.
* Price 0 plus a registry that appends is stacked lives. Closed by one row
  per uid and "already on file".
