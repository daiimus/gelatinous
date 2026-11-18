# Sleeve Insurance Spec — a personal policy, bought in advance

A sleeve policy is a record a living person buys, ahead of time, at a
Thawn-Harrison terminal in the cloning center's lobby. When that person dies,
the policy pays for one return: an NPC keeper is revived or rebuilt into their
post, and a player's dead character comes back as a flash clone. No policy, no
return: the NPC's post goes to a successor if the post allows strangers
(`post_policy` `successor`; see §3), and the player's dead character stays
dead (the account can still start a fresh character). Staff
can grant a standing policy with `@insure`. Tracks #3667 (its three slices,
A: the terminal and the record, B: the NPC return, C: the player gate and
`@insure`).

Owner's framing (#3667): "We're going to have to revamp this whole thing at
some point but for now we just want the intro framework to expand on." This
is that framework, not the final shape.

**What this replaced.** `NPC_POSTS_AND_REINCARNATION_SPEC.md` §3 recorded
employer-paid insurance, and its §2 as-built premium notes a premium paid at
a return; a 2026-08-22 ruling (`BACKUPS_AND_MEMORY_FORGERY_SPEC.md` §8.2)
let players resleeve free. This spec (#3667, rulings of 2026-09-25)
supersedes that payment model and that ruling.

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

The standing (`@insure`) ruling is in §2, the six design questions in §7.

## 2 · The model

* **A sleeve policy is an off-body record**, one per sleeve uid, held by
  Thawn-Harrison. Off-body because bodies are deleted (non-essential NPCs)
  or archived (PCs, essential NPCs) at death; a flag on the body dies with
  it. One per uid because a lineage shares its uid (`create_flash_clone`
  copies it, `imprint.restore` writes it back), so stacking records would
  stack lives: a second press answers "already on file".
* **Bought at the terminal by the living presser only.** Key on
  `sleeve_uid_of(presser)`, refuse `None` (the rental precedent,
  `world/rental.py` `assign_cube`), refuse a dead, dying, archived or
  unconscious presser. The terminal never samples a held object: a corpse
  and a severed head carry the uid too. A body with no uid can never hold a
  record (no record can exist for uid `None`), so uid-less bodies drop out
  on their own; nothing is backfilled and nothing is excluded by hand.
* **Redeemed only by the body that bought it.** The record stores
  `buyer_dbref`; a payout requires the dead body's id to match. Every
  archived husk in a PC lineage carries the same uid, so uid alone would
  let an old husk spend a living body's policy (the web archive view
  refuses to archive an already-archived body, so it cannot make an old
  husk `last_character`). The mirror rule at the terminal: "already on
  file" only when the record's buyer is the presser; a record whose buyer
  is a dead or archived body of the same lineage is void, and the
  presser's purchase replaces it. Otherwise a return that did not consume
  the record would leave a row the living body can neither redeem nor
  replace.
* **Taken atomically before the body is built, put back if the build
  fails.** Django runs under Twisted's thread pool; the web POST and the
  telnet menu can both read a record before either consumes it. With one
  store row per uid, a take (`take_policy`, buyer-scoped) reads the row for
  the uid, checks that `buyer_dbref` is the dead body, then deletes that
  same row by its pk (`filter(pk=row.pk).delete()`), requiring a count of
  1, so a door holding a stale read cannot consume a record re-issued under
  the same key; the loser gets a clean refusal, never a body. A purchase is
  one INSERT, in one place: `_insert` builds the row with the pickled value
  and saves it inside the try, because `ServerConfig.value`'s setter saves
  on assignment; an `IntegrityError` is "already on file". The payout is a
  **sequence of steps, each with its own undo**, never a database
  transaction (the web door runs on a pool thread; on SQLite
  `transaction.atomic` across the build would hold the write lock against
  the game loop, and the idmapper cache does not roll back). Verify per
  path: an NPC body is alive, unarchived, in the decant room, with the
  keeper installed; a PC clone is created, unarchived, not dead, and
  carries the record's uid (the callers move it out of Limbo afterwards, so
  location is not checked inside `create_flash_clone`). On failure: restore
  the row; delete a freshly built body (rebuild, flash clone); for a
  revived archived NPC, which is the person's only copy, move the body back
  to Limbo and restore the archived attribute and tag directly, so it is
  exactly as it was (dead, archived, `death_processed`); never delete it and
  never re-archive through `archive_character` (that bumps `death_count`).
* **Redeemed for a death only** (Q3). The source body must be archived with
  `reason="death"`; a shelved living body (`reason="manual"`) never
  redeems, and the shelve page says so. Never redeemed while the source
  body can still be revived: refuse while it carries a `death_progression`
  script or is `death_processed` but not yet archived. Do not rely on
  timing; the web archive view also refuses a dying body
  (`CharacterArchiveView`).
* **Payout is keyed to the person who died, not to the post.**
  `_try_resleave` revives the slot's own dead keeper (the keeper reference,
  else the `dead_id` stamped when the slot went dark) and restores that
  body's own imprint, never the shift's last snapshot, which belongs to
  whoever last died on that shift, a hired successor included. A slot
  stamped with a body that is gone never falls back to a namesake. Only a
  slot that went dark before the stamp existed falls back to the newest
  archived body of the blueprint (`_archived_body`), and the policy record
  must still name that exact body (§3).
* **Nothing else pays.** A return debits no till and credits no clinic;
  there is no premium.

### Record shape

```
sleeve_policy:<uid> = {
    "uid": <sleeve uid>,          # the sample
    "bought_at": <epoch>,
    "buyer_key": <display key at purchase>,
    "buyer_dbref": <int>,         # the only body that can redeem it
    "blueprint_key": <str|None>,  # NPC cast
    "account_id": <int|None>,     # PC
    "perpetual": True,            # staff grant only: see below
    "granted_by": <str>,          #   who granted it
    "renewed_at": <epoch>,        #   last re-issue after a return
}
```

**A standing (perpetual) record** (owner ruling 2026-09-25, Slice C: "a
way to make a character perpetually insured. Usable for play testing,
staff, etc.") is the same row flagged `perpetual`, written only by the
staff verb `@insure` (Admin lock, `commands/CmdInsure.py`: `@insure
<character>`, `@insure/revoke <character>`, `@insure/status <character>`;
revoke removes only a standing record, never a player's ordinary
purchase). It is TAKEN like any other record, so two returns racing for it
still get one body and one refusal, and once the return is verified the
payer re-issues it in the new body's name (`renew_perpetual`; a flash
clone is a new object with a new id, and a record left pointing at the
dead body would pay for exactly one death). A forfeit (Q5) or
`@insure/revoke` removes it; the terminal also replaces a dead holder's
leftover when a living body of the lineage buys, as for any record. Every
take and forfeit is a compare-and-delete on the row that was read (by pk),
so a door holding a stale read cannot consume a record re-issued under the
same key. It may be granted to a dead, archived body: that is how a
playtester who died uninsured is brought back (grant, then respawn). The
grant refuses a shelved body (it could never pay) and an older husk whose
lineage's record is held by a body that is alive, dying, or dead and still
redeemable (it would strip that body's cover for a record the doors can
never reach); the revoke acts only through the body that holds the record
and reports a record that changed hands in between.

**Storage: one `ServerConfig` row per uid** (`db_key` is unique and 50 chars
fits), the store the house already moved durable data to. Not a
`GLOBAL_SCRIPTS` entry: Evennia recreates a managed global script whenever
its settings entry changes, and the WSIS ring was moved off one for exactly
that reason (#2672, `world/wsis.py` `_STORE_KEY`). Not on the lobby fixture
(a re-run build or a deleted terminal would wipe every policy, the #3565
class). Not on an attribute named `register` (`economy._reconcile_till_tags`
adopts any such object as a tithed till). Only in-process code writes it
(the terminal, the payout, an in-game staff verb); never a build script.
The store is read directly; a cache comes only after a measurement.

## 3 · Where the gate goes

**Who the dead keeper is.** The sweep stamps a vacancy when a slot's keeper
is dead (`world/souls/posts.py` `sweep`); at that moment it also records the
keeper's `sleeve_uid` and `id` into the slot (the `dead_id` stamp), before a
deleted reference reads back as `None`. `imprint.capture` records
`blueprint_key` and `dbref` (`restore` ignores them). Then:

| Return path | Body | Gate + take | Notes |
|---|---|---|---|
| Archived NPC (essential) | `slot["keeper"]` itself, when it is archived and its `blueprint_key` matches the shift's | in `_try_resleave`, take before the revive, verify after | restore from the body's own `db.imprint`, never the post snapshot; the blueprint-keyed lookup `_archived_body` is used only for a slot that went dark before the dead-keeper stamp existed, with the policy record as the identity check |
| Blueprint rebuild (keeper deleted) | `build_npc(bp_key)` | same call | only when the shift snapshot's `blueprint_key` matches the shift's and its `dbref` matches the stamped keeper (the `dead_id`, where one exists); otherwise the outcome is successor and the record is left unspent |
| PC, telnet respawn | `create_flash_clone` | inside the function, take before `account.create_character`, verify after the full build | `[4]` is offered only when `flash_clone_refusal` returns None; the menu's choice handler (`_respawn_process_choice`) asks again and re-displays the menu on a refusal |
| PC, web respawn | same function | same | the POST reads the source through `respawn_candidate()` like the GET; enforcement lives in the function, and the POST catches `PolicyRefused` and redirects to the sleeve choice |

**The legacy `post_memory_snapshot`** (written by the removed
`snapshot_keeper_memory`, with no `sleeve_uid`, `blueprint_key` or `dbref`)
is never a payout source, and nothing writes the key (#3424).

**The sweep's owned branch** (`world/souls/posts.py` `sweep`) has three
outcomes, which `_try_resleave` answers as RESLEEVED / HOLD / SUCCESSOR:

* *resleeve*: a policy the dead keeper can redeem.
* *successor*: no policy, a blueprint that raises, or `RETURN_ATTEMPTS` (3)
  failed returns on one vacancy (the record is left unspent).
* *hold*, for transient states: the keeper is alive elsewhere, dying or not
  yet archived, or a return failed and may be retried. A dead body not yet
  archived (progression running, or a wedged death) is HOLD, never rebuilt.

On SUCCESSOR, `sweep` clears the shift's ownership, `post_blueprints[shift]`
(`_disown_shift`), and falls through to the successor offer, so the shift
never stays dark forever (the #3565 shape, when every `False` hit
`continue`). There is no `post.db.post_blueprint` fallback. The archived
body is left in Limbo as others are. An archived body never holds a slot
(`_slot_held`).

**`post_policy` has no `resleave` value.** The post does not decide who
comes back; the person's record does. A post decides only whether strangers
may be hired: `successor` or `None`. The Rook's chair is `successor` like
the rest (Q2 accepted that it goes dark after his death) and stays dark only
because nobody can reach it. Build 098 recorded the Rook's chair as
"resleeve-only: no stranger is ever seated"; that is overturned by ruling 5;
the chair stays dark for another reason (§7 Q2).

**Two more places or the gate leaks:**

* Nothing respawns "Petra" by name on server start or reload, policy or
  not: there is no `ensure_dispatch_operator` or `spawn_dispatch_operator`
  in `world/director/population.py`, and `world/director/routines.py`
  neither imports nor calls them (`ensure_comms_fitted` and
  `ensure_base_station` stay). The 2026-09-05 ruling (#2762) asks that the
  desk follow "the same rule every other post follows"; the dispatch desk
  follows ruling 5 like every other post, and the 2026-08-22 ruling still
  holds (an empty desk answers in the automation voice).
* `account.db.last_character` is written at death even for a player who
  was offline, because unpuppet clears `character.account` first:
  `archive_character` resolves the owner with
  `world.ownership.owning_account(character)` (the playable-characters
  record first, which survives logout, then the live puppet, then a puppet
  lock; unresolved claims skipped), not a capture taken while puppeted,
  which is `None` for a player who disconnected mid-death. A caller may
  pass a verified `owner=` instead (the web shelve passes `request.user`).
  So `last_character` and the tombstone are written at a death the player
  was offline for. Without it a web-only player would see no clone card at
  all. The corpse stamp in `death_progression.py` falls back the same way
  when no puppet was captured. The web archive view does not write
  `last_character` itself.

## 4 · How an NPC goes to buy

* A derived need, `insurance`, in `PROFILES["human"]` and `["synth"]` with
  its own planner shape and `plan_for` branch, and a branch in both
  `pressures()` and `pressure()` (the wardrobe pattern); the robot and
  recluse profiles are left out. Pressure 0.0 when this body can redeem a
  record (uid on file **and** `buyer_dbref` is this body), or when the body
  has no sleeve uid at all (it could never buy, and a need it can never meet
  would fault every 15 minutes); else `INSURANCE_PRESSURE`, which is exactly
  SOFT (0.55). Band 3 breaks ties by profile order, so any need that has
  actually risen, a meal included, wins over insurance; it is elected in the
  soul's own time (band 3), never over a shift.
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

## 5 · The terminal and the player gate

**The terminal.** `InsuranceTerminal` (`typeclasses/terminals.py`),
branded Thawn-Harrison, stands in the lobby, room #1986 (build 167,
terminal #26167). The record logic is `world/insurance.py`. The price is
`POLICY_PRICE = 0`, in one place.

* Buy with `press insure`, or `renew`, `sample`, `policy`, `buy`, `cover`.
* Read with `press status` or `info`, or a press that names the terminal
  itself.
* On a purchase the room sees "The policy terminal takes a sample from
  <actor> and chimes once."

**The player gate.** Both doors (the telnet respawn menu and the web
respawn) ask ONE question, `insurance.flash_clone_refusal(old_body)`:
archived with reason `death`, else `NOT_A_DEATH`; the record must be this
body's own, else `NO_POLICY`. `create_flash_clone` asks it again, plus
`STILL_ON_THE_TABLE` (a `death_progression` script still attached; checked
only at build time, because at a live death the menu's first render happens
while the script is still attached). Then, in order:

1. the take (`take_policy`, buyer-scoped; `create_flash_clone` never voids
   a lineage's record by uid alone);
2. the whole build inside one undo (a fresh body that never verified is
   removed from the account and deleted, the record restored);
3. the verify (unarchived, not dead, wearing the record's uid);
4. `renew_perpetual`.

The refusal is `PolicyRefused`. The telnet menu refuses `[4]` at the
goto-callable (re-display); the node's own catch returns
`respawn_welcome(...)` as a node (a bare string would close the menu, the
nine-place defect `EVMENU_PATTERNS_SPEC` records). The web POST catches it
before its generic handler and redirects to the sleeve choice with the same
text.

**Shelving.** `CharacterArchiveView` refuses an already-archived body and a
dying one, and its message says a shelve is not a death.

**A fresh character after a death.** Both template finalizers (telnet and
web) call `forfeit_policy(dead_body)`, buyer-scoped (Q5; a standing record
is forfeited too).

**Players learn before it matters**, since every existing player character
starts uninsured and an uninsured death is permanent:

* `help insurance`;
* a `SLEEVE POLICY:` line on every telnet envelope
  (`insurance.envelope_line`);
* a pod-lid card in `at_post_puppet`'s decant branch, the one line every
  creation door reaches, web included.

## 6 · Deferred, on purpose

* `📋 UNBUILT (no issue)` The price, and where it goes (the terminal then
  earns into a Thawn-Harrison register, which becomes a tithed till).
* `📋 UNBUILT (no issue)` Moving the terminal outside Thawn-Harrison
  (ruling 3).
* `📋 UNBUILT (no issue)` Returns for people who have no rebuild path
  today: hired successors, generated residents, civilians (deleted at
  death), and essential cast with no blueprint (Ossie, Nonna). A
  person-keyed rebuild from the imprint is the prerequisite.
* `📋 UNBUILT (no issue)` Un-shelving a living sleeve (see §7 Q3).
* `📋 UNBUILT (no issue)` Records as decking files (ruling 7).
* **Synths and the fiction of return.** Vesper,
  the Rook and Bellows are `synthetic_humanoid`. Today they return through
  the same code and the same "sleeve envelope" decant scene as humans;
  nothing synth-specific exists (owner asked 2026-09-25 whether synths even
  clone out: they do, identically). The open question is in §9.

## 7 · The six design questions (all ruled 2026-09-25)

1. **Who gets the urge to buy?** Ruled 2026-09-25: every human and synth
   soul (option 2), even where a policy cannot yet pay out.
2. **The Rook.** Ruled 2026-09-25: "1. We accept for now." He cannot leave
   the seal, stays uninsured, and after his death the chair goes dark (no
   policy; no successor can reach the seal). The recluse's cost, for now; a
   way to the terminal is a later build if ever wanted.
3. **Shelving a living character.** Ruled 2026-09-25: "1 for now is fine."
   A policy pays for a death only: redemption requires the source body
   archived with `reason="death"`. Shelving (the web archive of a living
   body) never spends a policy, and a shelved living body cannot be
   flash-cloned back; the shelve page warns. Un-shelving stays in §6.
4. **Maxwell's "a Thawn-Harrison billing terminal."** On it the owner
   first said only: "No idea why it ended up in the clinic. That's really
   weird." Ruled 2026-09-25: "1." Keep it and re-brand it as Maxwell's; the
   till, the `treatment` advertiser and the `medic` post stay. The key
   keeps "billing terminal" (build 074's finder matches on that substring;
   a re-run would otherwise create a second terminal and a second medic
   post).
5. **Template after an insured death.** Ruled 2026-09-25: "1". Picking a
   fresh character after an insured death spends the policy: both template
   finalizers (telnet and web) void the dead lineage's record, so no
   orphaned row can revive an abandoned self later. This is
   `forfeit_policy(dead_body)`, buyer-scoped, so an older husk's fresh
   start never drops a living lineage-mate's cover; a standing record is
   forfeited too (staff re-grants if wanted).
6. **Delay on fallthrough.** Ruled 2026-09-25: "Default behavior makes
   sense." Each post keeps its own `post_delay` (census 2026-09-09, the
   comment in `world/souls/posts.py` `sweep`: 72 h on ten posts, 6 h on
   five, 24 h on two, 600 s on two) before a successor is offered; a
   balance-pass number, untouched.

## 8 · Holes the design closes

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

## 9 · Not decided

* Whether a synth is grown at Thawn-Harrison at all, or comes back some
  other way, is unasked (§6).

## 10 · Related documents

* `NPC_POSTS_AND_REINCARNATION_SPEC.md` — posts, shifts and the sweep; its
  §2 premium notes and §3 payment model are replaced by this spec.
* `proposals/BACKUPS_AND_MEMORY_FORGERY_SPEC.md` — §8.2's free-resleeve
  ruling is superseded by this spec.
* `EVMENU_PATTERNS_SPEC.md` — the bare-string defect the respawn node avoids.
* Specs that describe the flash clone: `WEB_RESPAWN_CHARACTER_CREATION_SPEC`,
  `EVMENU_PATTERNS_SPEC`, `NEW_PLAYER_EXPERIENCE_SPEC`,
  `WEB_CHARACTER_CREATION_ALIGNMENT`.
