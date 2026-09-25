# Sleeve Insurance Spec — a personal policy, bought in advance

> **Status: PROPOSAL (2026-09-25, revised the same day after a 48-agent
> read-only critique), not built.** Tracks #3667. Supersedes the payment
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
  alone would let an old husk spend a living body's policy.
* **Taken atomically before the body is built, put back if the build
  fails.** Django runs under Twisted's thread pool; the web POST and the
  telnet menu can both read a record before either consumes it. With one
  store row per uid, "take" is a delete that returns 1 exactly once; the
  loser gets a clean refusal, never a body. The whole payout is one
  transaction: take, build, verify (body alive, not archived, not in Limbo,
  keeper installed or clone fully built), and on any failure restore the row
  and delete a half-built body.
* **Never redeemed while the source body can still be revived.** Refuse while
  the dead body carries a `death_progression` script or is `death_processed`
  but not yet archived with `reason="death"`. Do not rely on timing: the web
  archive view can archive a dying body today.
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

**The sweep's owned branch** (`posts.py:446-459`) gets three outcomes:
*resleeve* (a policy the dead keeper can redeem), *successor* (no policy, or
a permanent failure such as a blueprint that raises), and *hold* only for
transient states (the keeper is dying or not yet archived). Today every
`False` hits `continue`, the #3565 "dark forever" shape. An uninsured
fallthrough clears the shift's ownership: `post_blueprints[shift]` **and**
the legacy `post.db.post_blueprint` fallback (`posts.py:446-447, 539-540`),
which builds 076/077 still set. The archived body is left in Limbo as
others are.

**`post_policy` loses its `resleave` value.** The post no longer decides who
comes back; the person's record does. A post decides only whether strangers
may be hired: `successor` or `None`. The eleven blueprint `'policy':
'resleave'` entries, build 098's writes, `posts.py:464`, the NPC_POSTS §4
column and `test_no_policy_means_the_slot_stays_dark` change in the same PR.
Build 098's "resleeve-only: no stranger is ever seated" for the Rook's chair
is overturned by ruling 5; the chair stays dark for another reason (§7 Q2).

**Two more places or the gate leaks:**

* `ensure_dispatch_operator` respawns "Petra" on every server start and
  reload, policy or not (`world/director/population.py:322-375`), by the
  2026-09-05 ruling (#2762) that "a dead operator is a vacancy and the desk
  staffs itself again". Ruling 5 supersedes that: the desk is a post like any
  other. Retire it, `spawn_dispatch_operator`, the `routines.py:468-474`
  call, and census any blueprint-less Petra it already made.
* `account.db.last_character` is not written at death: the account is
  cleared by unpuppet before `archive_character` runs
  (`death_progression.py:1059-1071`). A web-only player then sees no clone
  card at all. Write it from the account captured at
  `death_progression.py:946`, so both doors key on the same body.

## 4 · How an NPC goes to buy

* A derived need, `insurance`: pressure 0.0 when the soul's uid has a
  record, else a constant just above SOFT (0.60, the provisional-clothing
  analogue), so it is elected in the soul's own time (band 3), never over a
  shift. `_goal_band["insurance"] = 3`.
* **Who gets the need** is §7 Q1. Until ruled, pressure is 0.0 unless the
  soul has a `blueprint_key` **and** holds a slot whose `post_blueprints
  [shift]` names it: the only souls a payout can restore today. `essential`
  is not the test (Ossie and Nonna are essential with no blueprint).
* Plan: `[travel → lobby, press <button> on <terminal>]`, the clinic-visit
  shape. The terminal is a souls advertiser (`advertises={"insurance":
  1.0}`) found **without** the default radius cap of 30: the lobby may fall
  outside it depending on where the soul is standing and on z.
* The press step must name the button (`press insure on terminal`, which
  `_press_named_pressable` handles) and must check the result: an unchanged
  registry after the press is a fault, or the need re-fires every think.
  The button name is one constant on the terminal (`InsuranceTerminal.
  BUTTONS`, as `SleeveDispenser.BUTTONS`), read by the planner.
* Robots never elect a band-3 need (always on duty) and are replaced by
  chassis. Pinned souls never think and stay uninsured until unpinned. The
  Rook has the `recluse` profile and cannot leave the seal (§7 Q2).

## 5 · Phase 1, in slices that ship one at a time

**Slice A — the terminal and the record.** `InsuranceTerminal`
(`typeclasses/terminals.py`; `press insure`, `press status`), branded
Thawn-Harrison, built in room #1986 by a build script; `POLICY_PRICE = 0`
in one place; the `ServerConfig` registry with take/put-back; the census of
null `sleeve_uid` characters, backfilled in-process before any gate ships.
Play: Iver buys, is refused twice, reads his status.

**Slice B — NPC return.** The dead-keeper stamp in the slot; `imprint.
capture` gains `blueprint_key`/`dbref`; `_try_resleave` keyed to the person
with take-before-build; the three sweep outcomes with ownership cleared on
fallthrough; `post_policy` loses `resleave`; the `insurance` need,
advertiser and named press step; `ensure_dispatch_operator` retired. **Old
model deleted in the same PR, repo-wide grep to zero:** `RESLEAVE_PREMIUM`,
`post_insurer` (code, build 098:65, a data build to strip the attribute
rows), the `resleeve_premium` audit line, `search_object("a Thawn-Harrison
billing terminal")`, `_archived_keeper`, `spawn_dispatch_operator`, and the
stale prose in `posts.py` (docstring line 14, line 27, line 459, the
`_try_resleave` docstring). **Tests that pin the old rule and must change:**
`test_an_owned_shift_still_waits_for_its_own_person` (test_shift_fallthrough),
`test_a_broke_till_cannot_pay_the_premium` and the `post_insurer`/`register`
fixtures (test_souls_posts), `test_the_money_leaves_a_record.py:43` (pins
the literal `resleeve_premium`), the `_try_resleave` source pin in
`test_death_survives_a_reload_and_a_resleeve.py:162`, `test_no_duplicate_
keepers`, `test_no_policy_means_the_slot_stays_dark`, `test_dispatch_
operator_upkeep`, `test_director_population.py:269`.

**Slice C — the player gate, last.** `create_flash_clone` gate with
take-before-build and restore-on-failure; one refusal constant used by both
doors; the web POST catches it; `last_character` written at death;
`CharacterArchiveView` refuses a sleeve that is already archived; and,
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

## 7 · Open questions for the owner (one at a time)

1. **Who gets the urge to buy?** Only souls a payout can restore today
   (named keepers with a blueprint holding their own shift), or every human
   and synth soul, buying records that cannot yet pay out. Recommended: the
   former, until §6's rebuild exists.
2. **The Rook.** He has the recluse profile and cannot leave the sealed
   studio, so under ruling 5 he stays uninsured. After his death the chair
   goes dark because no successor can reach the seal (`_offer` refuses an
   unreachable post), which is the recluse story's cost. Accept that, or do
   you want a way out of the seal?
3. **Shelving a living character** (the web "archive" of a live body). With
   the gate, a player who shelves an uninsured character cannot flash-clone
   it back, and no un-shelve path exists. Accept; or warn/refuse at the
   shelve step when there is no policy; or build un-shelving later (§6).
4. **Maxwell's "a Thawn-Harrison billing terminal."** It is the clinic's
   till, its `treatment` advertiser and its `medic` post (build 074). Keep
   it and re-brand it as Maxwell's (keeping "billing terminal" in the key,
   which build 074's finder matches on), or remove it and re-home those three
   roles.
5. **Template after an insured death.** Does picking a fresh character void
   the dead lineage's policy? Recommended yes: a policy pays for one death,
   and an orphaned record could otherwise revive an abandoned self through
   the archive view.
6. **Delay on fallthrough.** Live `post_delay` values: 72 h on ten posts, 6 h
   on five (the Rook's chair and Vesper's chaise among them), 24 h on two,
   600 s on two. A `resleave` post that now falls to a successor rehires on
   its own `post_delay` unless the fallthrough gets its own value. Keep
   `post_delay`, or one successor delay for every fallthrough?

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
