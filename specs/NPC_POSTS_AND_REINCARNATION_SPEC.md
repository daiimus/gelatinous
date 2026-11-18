# NPC Posts & Reincarnation Spec

A named NPC who staffs a workplace can die without the workplace dying
with them. Three pieces make that work: **BLUEPRINTS** (a build recipe
per named NPC), **POSTS** (the staffed fixture that survives its keeper),
and a **policy** that decides who stands the post next. The model is the
colony's security complement (`world/director/population.py`: base +
complement + heartbeat + `spawn_secbot` factory), whose respawn works
because its units are **factory-made from blueprints**; this spec
generalizes that loop to every staffed NPC. Without it, a named NPC
(Ottilie, Del, Marta, Vesper…) hand-built in a shell session would die
**permanently and unreproducibly**: death → corpse → the character
object is deleted (#1022), dossiers and memories with it, and no recipe
to remake them.

Decided with the owner 2026-07-24: the re-sleeve/succession mix is the
model — *"some NPCs will be institutions; others will be forgettable."*

Today a post fills a dark shift in one of two ways: the same person
returns, if their own sleeve policy pays (#3667, see §3), or an existing
idle soul is hired into it. A third loop seeds new residents (§1.4).

---

## 0 · Purpose

Killing a named NPC should be **consequential, not catastrophic — and never
cheap**. Without posts it would be catastrophic for the world (the butcher gig would
die with its keeper, forever, until a builder hand-remade her) and cheap for
the killer (no interesting consequence — the service would just vanish). The sleeve lifecycle
already answers "what does death mean here" for PCs; this spec extends the
same worldview to NPCs:

- **Some come back as themselves.** A keeper who returns comes back *as
  themselves*, after a delay. Killing them buys time, not erasure. Whether
  a keeper returns is the person's own sleeve policy, bought alive at the
  Thawn-Harrison terminal (#3667, see §3).
- **The street gets successors.** Kill a cart vendor and days later *someone
  else* claims the stall — new face, new name (📋 UNBUILT, see §5), same
  trade, **an empty book**. You can't erase the service, but you
  permanently erase the relationships: the new butcher doesn't know you're
  the ratcatcher, owes you nothing, and prices you like a stranger. Murder
  deletes *social capital*, not commerce. (How far the code delivers this
  today: §1.4.)
- **Some deaths are stories.** A post that hires no stranger stays dark.
  Reserved for NPCs whose loss should reshape a district.

## 1 · The three pieces

### 1.1 Blueprints — the build recipe

A **blueprint** is a data + builder pair that can construct a complete named
NPC from nothing: typeclass, identity axes (sex/height/build/skintone —
validated against the identity vocab; invalid values are the known
server-killer), wardrobe kit (garment specs incl. `worn_desc`/coverage/layer/
color), longdescs, voice, persona seed (archetype + name + description +
personality + scenario), `llm_driven`, stats, placement line, and **post
binding**. The `spawn_secbot` / `spawn_civilian(role, anchor)` factories are
the proven shape; a blueprint extends it from role-generic to person-specific.

- Lives in `world/npcs/blueprints.py`: the `BLUEPRINTS` registry, `build_npc`
  (the builder in use), `build_successor` (no caller), and `verify_blueprint`.
- **Every blueprint has a FIXED identity** — Ottilie is Ottilie. A returning
  keeper is rebuilt or revived as themselves.
- **Why blueprints matter on their own:** they make the roster
  *reproducible* — without one, a named NPC exists only as live DB state from
  imperative shell sessions. A blueprint is also a backup, a test fixture,
  and cheap content for the next market NPC.
- The `post` fields inside each blueprint (binding, policy, delay) and its
  `delay_hours` fields are not read. Where they differ from the fixture,
  the fixture is what runs (§1.2).

**`build_successor` must not simply be wired.** It builds a genuine
stranger (random name and face from the pools, same trade, empty
dossiers) but never ENSOULS it — no soul tag, no needs, no schedule, no
wage. Wiring it as-is reproduces #2132, where posts stood staffed by
mannequins. The generator identity it would serve is unbuilt (§5).

### 1.2 Posts — the thing that survives its keeper

A **post** is the staffed workplace: the food cart, the chain-hoist bar, the
clinic + AutoDoc, the pawn counter. The post is a fixture in the room, made
*administrative* by what it carries.

**Registration.** A post is registered by `world/souls/posts.register_post`
in a numbered build script, which writes the policy and delay onto the
fixture and tags it; the sweep iterates the tagged fixtures.
**DECIDED (owner, 2026-07-24): data-driven, no builder command** —
registration is the deploy cycle. Owner's standing principle: builder
tooling will eventually be designed as an extensive, comprehensive suite —
one deliberate project. Until then, ad-hoc builder commands are tech debt
(each one is a future migration), so content-adjacent config stays in data.
(The ruling had the post binding, policy and delay as FIELDS of the
blueprint, with the watcher iterating the blueprint registry; what runs is
the fixture written by the build script, as above.)

**What the fixture carries.** A venue runs 24/7 in eight-hour shifts
(owner rulings 2026-08-20), so the keeper and the vacancy stamp are PER
SHIFT:

- `db.post_slots` — `{shift: {"keeper": …, "vacant_since": …}}`. A slot
  that goes dark also stamps `dead_uid` / `dead_id`, the body whose policy
  may bring them back, and counts failed returns as `return_failures`.
- `db.post_blueprints[shift]` — the blueprint name of the person who owns
  that shift.
- `db.post_role` and `db.post_wage_rate`, written by `register_post`.
- `db.post_policy` — post-wide: `successor` | `None`. A post decides only
  whether strangers may be hired. There is no post-wide `post_blueprint`
  and no `post_insurer`. Overturned 2026-09-25 (#3667): a post's policy
  once had a `resleave` value (institutions come back as themselves);
  whether a keeper returns is now the person's own sleeve policy.
- `db.post_delay` — post-wide, seconds of vacancy before the post acts
  (§1.3).
- `db.post_keeper` — a single-value LEGACY MIRROR, rewritten by
  `register_post`, `_install_keeper` and `do_claim` every time a keeper is
  installed. It is still read by `world/souls/posts.is_bound` (the one "is
  this counter bound?" question, asked by `world/service.py`,
  `typeclasses/shopkeeper.py`, `typeclasses/bar.py`,
  `world/souls/actions.py` and `world/bar.tender_at`; it reads the STORED
  row, so a deleted keeper still counts as assigned, #3573), by
  `keeper_on_duty`'s last-resort fallback, and by `sweep`'s one-time
  adoption of a pre-slots post. Ask the slots first.
- `db.post_vacant_since` — only ever cleared by `do_claim`; on a slots post
  it is stale rather than wrong, and nothing reads it once `post_slots`
  exists.

**The post persists through death.** The cart keeps its stock, till, and
prices while unstaffed — commerce pauses, property remains. (Deterministic
transactions gate on the keeper being present: no butcher, no grinding.)
The till and stock are the POST's, and successors inherit (owner-decided):
the till is the fixture's `db.register`, and `do_claim` makes the fixture
the new keeper's venue.

**Delays.** Owner-decided values: successor 24h / re-sleeve 8h. What runs:
one delay per post, `db.post_delay`, gates the return and the succession
alike; with none set, `DEFAULT_DELAY` (6 h) applies, and 0 means at once.
Each post keeps its own `post_delay` (72 h on most named counters, census
2026-09-09). (Whether delays should be hours or days is listed under §6.)

**What a dark slot shows.** A signal, not prose: `wsis.emit("post_vacant", …)`
from `world/souls/posts.sweep`, plus a counter that answers closed while
nobody stands the running shift. There is no vacant description; see
"Vacancy is visible" in §5.

**The shift change (#2434, #3800).** Each keeper works to a personal
clock up to fifteen minutes off the colony's
(`engine.shift_jitter_hours`), while the slot that is "running" is
read from the colony clock. A keeper whose own shift has ended covers
until somebody ELSE holds the running slot at the post, and gives up
after `HOLDOVER_HOURS` (`engine.on_duty`,
`posts.relief_has_arrived(post, outgoing)`). A keeper is never their
own relief (owner ruling 2026-11-13): one whose clock runs early stays
through the minutes in which the colony clock still names their own
shift, wherever they are standing. A post with a single slot has no
relief at all, so its keeper covers the whole of `HOLDOVER_HOURS`.
`HOLDOVER_HOURS` is one hour, a provisional value until the balance
pass.

#### 1.2.1 What a role must supply to stand a post

The post fixture is half the contract; the other half is the **job**,
registered with `world.service.register(role, handler, ...)` (#2824).

- **`handler(post, speech, patron, by, addressed) -> bool`** — the job
  itself. Returns True when the post CLAIMED the line, which obliges the
  caller to stay quiet: the order has been taken. The signature is
  checked at registration and a mismatch is logged, because a handler
  that cannot be called simply never claims anything and the venue reads
  as a keeper who never takes an order (#2797).
- **`aliases`** — what the job answers to ("bartender", "barkeep").
- **`fallback`** — what the job says when addressed with no voice
  available to improvise. **Silence is a permitted choice, and it must be
  an explicit one:** pass `service.SILENT`. A doctor asked something odd
  stays quiet on purpose. Omitting `fallback` gets the same runtime
  behaviour and a startup warning, because otherwise a forgotten line is
  indistinguishable from a chosen silence and surfaces as a mute NPC the
  first time a player stands at that counter with the sidecar down
  (#2824).
- **`archetype`** — the `world/llm/prompt.ARCHETYPES` key for the
  register the job talks in.
- **`tools`** — what the job can DO when the model calls one. The
  archetype GRANTS a tool; this is what runs it, and the two must come
  from the same place or a successor is handed `check_stock` and gets an
  empty string back (#2352).
- **`on_receive(post, obj, giver, by) -> bool`** — optional; the job's
  answer to something being HANDED to whoever stands it. Receiving is the
  one venue act that happens to a PERSON rather than at a counter.

Handlers register in the module that owns the state they read — bar
service lives in `world/bar.py` — so nothing accumulates in
`world/service.py`.

### 1.3 The watcher — the posts sweep

The sweep rides the SOULS heartbeat: `world/souls/engine` calls
`world/souls/posts.sweep()` once every `SWEEP_EVERY_BEATS` (10) beats, on
beat 3. There is one post registry and one watcher; a second watcher that
disagreed about which fixture owned a post meant both acted, and the
bodies it rebuilt were never ensouled (#2132). Each sweep:

0. Before the posts, the sweep writes `soul_fixture` onto any keeper that
   lacks it (`stamp_fixtures`), and releases any keeper whose post fixture
   or post room has been deleted (`release_the_orphaned`, #3563): their
   post, venue, fixture and wage are cleared and their role falls back to
   their civic role, so they count as unemployed and can be hired again.
1. For each registered post, each SLOT is asked whether it is held
   (`_slot_held`). The rule is holding by ASSIGNMENT, not by attendance —
   alive (`is_dead()` over `medical_state`, never a `db` flag — #2706) and
   still matched by `soul_post`/`soul_schedule` — so a keeper who steps out
   for a meal does not vacate the slot (#2371). One exception, and it is
   deliberate: a souled keeper with no `soul_post` recorded holds the slot
   by standing in it, or the Rook's own booth reads dark forever (#2178).
   An unsouled keeper holds nothing; that is a build error, not a case. A
   newly dark slot gets its `vacant_since` stamped and emits `post_vacant`.
2. When the slot's `vacant_since` is older than `post_delay`, and the shift
   carries a blueprint name (`db.post_blueprints[shift]`) whose namesake is
   not alive anywhere outside Limbo, ask the dead keeper's own sleeve policy
   (`_try_resleave`, #3667). A shift with no blueprint name skips this step:
   `do_claim` writes none, so a soul hired through succession does not come
   back to the post, policy or not, and the shift is offered as below. When
   asked, the policy answers one of three:
   - **RESLEEVED** → the archived body is revived on a record that names
     that exact body, and restored from its own imprint; a keeper who was
     never archived is rebuilt from the blueprint only from a snapshot that
     is this namesake's own. The body wakes in the Thawn-Harrison
     Decantation Chamber, not at the post (the code cites owner ruling
     2026-08-20), and walks back to work. The return gives the keeper a
     "resleeved" thought (the last hours before the dark are gone) and
     plays the emote "is back at the post, moving like the week never
     happened.", which is seen in the chamber.
   - **HOLD** → the body is still on the table (death progression running,
     or dead but not yet archived), or a return failed and may be tried
     again; the next sweep asks again. If the shift's namesake is alive
     somewhere else, the sweep does not ask the policy at all: a
     `successor` post offers the shift to a stranger.
   - **SUCCESSOR** → no policy, a blueprint that cannot build, a keeper
     who was never archived and has no per-shift snapshot naming this
     blueprint and this body, or `RETURN_ATTEMPTS` (3) failed returns on
     one vacancy (each failed attempt puts the policy back on file, and the
     count is kept on the slot as `return_failures`): the shift stops
     carrying the dead keeper's name, and a `successor` post offers it down
     the list of idle souls (§1.4), nearest first, skipping any who cannot
     walk there. The soul who takes it walks to the post (`_offer` gives it
     a claim job), dossiers **empty** (by accident, see §1.4), and on
     arrival poses "steps in behind the post, taking stock of the work left
     undone." A `None` post does nothing, forever. The vacancy *is*
     the content.
3. Same de-confliction rules as the security loop: one replacement per sweep,
   never while combat is live at the post.

### 1.4 Who replaces a keeper, and the gaps (#2437)

`build_successor` has no production caller and never has. What runs
instead offers the vacant slot to the nearest idle SOUL who can walk
there. There are three replacement tiers, and they match the owner's
stated ideal — *"NPCs have a history/story with souls… souls occasionally
generated to cover losses… some might be resleeves and be consistent"*:

1. **Re-sleeve** — the same person returns, memories intact
   (`_try_resleave`), **when their own sleeve policy pays** (#3667), and only
   on a shift that carries their blueprint name.
2. **Succession** — an idle soul takes the post (`_eligible_candidates`
   → `do_claim`).
3. **Generation** — `world/souls/population.sweep` seeds new residents.

**Who is eligible.** `_eligible_candidates` takes souls with no post and a
location, not pinned in time, not on a hunger/safety/claim/treat job,
without an order waiting on a counter, and not robots, sorted nearest
first; the sweep offers down that list and skips anyone who cannot walk
there.

**The empty book holds by accident.** Every idle soul happens to have zero
acquaintances, so today's replacement IS a stranger. That breaks silently
the first time a soul with history returns to the pool.

**Three gaps between that architecture and the ideal**, each tracked as
its own issue rather than assumed. Measured live 2026-09-08: 78 souls, 49
holding posts, 29 idle.

* **History barely accumulates, and only with players.** There are
  exactly two writers of opinion in the tree: being attacked
  (`react_to_attack`) and being spoken to by a player (`llm_npc`). Souls
  never form opinions about EACH OTHER. Measured: 4 of 49 posted souls
  have a single acquaintance; 0 of 29 idle souls have any. This is the
  largest gap and it is independent of succession.
* **The idle pool is the colony, not a labour reserve.** Those 29 are
  gangers, scavvers, salarymen, hawkers, an addict, a DJ, a grower —
  all with homes, one blueprinted. So the butcher's block can still go
  to a ganger.
* **The generation loop cannot see that.** `SEED_TARGET_UNEMPLOYED = 2`
  against an `unemployed_count` of 29, so it never fires — while the
  labour reserve in the sense that matters is roughly zero. One counter
  carries two meanings of "unemployed". `unemployed_count` also leaves out
  lawless and pinned souls; the hiring list leaves out pinned souls but not
  lawless ones.

## 2 · Memory across death

Dossiers (`db.llm_dossiers`) and episodic memory (`db.llm_memories`) live on
the NPC object. A blueprinted (essential) keeper's body is archived to Limbo
at death, not deleted, and keeps its own imprint (`db.imprint`), which a
return restores; a body that is deleted loses them, apart from the
per-shift copy on the post.

- **Snapshot at death.** `world/souls/posts.snapshot_imprint`, called from
  `typeclasses/death_progression`, writes `db.post_memory_snapshots[shift]`.
  It captures thoughts, opinions, and the people known by face and by
  voice, as well as dossiers and episodic memory, because it shares
  `world/imprint.py` with the player's flash clone and so cannot drift
  from it. Cheap, point-in-time, no periodic churn. The singular
  `db.post_memory_snapshot` is not written and nothing in the running game
  reads it (#3424, #3672); the one-time build
  `scripts/builds/085_restore_the_cast.py` still falls back to it, and two
  live fixtures still carry an inert copy from 2026-08-20.
- **A return restores it.** Continuity of self is what the person's own
  sleeve policy pays for (#3667). An archived body is restored from its
  OWN `db.imprint`; the per-shift snapshot rebuilds only its own namesake
  (it carries `blueprint_key` and `dbref`). `_try_resleave` reads
  `post_memory_snapshots[shift]` and never clears it: the snapshot is not
  consumed. The policy record is: it is taken before the body is built
  and put back if the build fails. A standing policy granted by staff is
  not spent: the return re-issues it in the returned body's name
  (`world/insurance.renew_perpetual`).
- **The gap.** Not optional and not local to this system:
  `world/imprint.GAP` (5400s, ~90 minutes) sets the backup's `taken_at`,
  and `restore` drops every memory, thought, opinion and newly-met face
  from inside it — so murder stays a mystery for the player's flash clone
  and the NPC keeper alike, through one code path. Dossiers, the service
  record (`designation`) and `skills` are not cut by the gap; they come
  back whole. The record also carries the body's `sleeve_uid`, and
  `restore` writes it back onto the new body. `world/imprint.GAP` is the
  only home for this number; `scripts/builds/085_restore_the_cast.py`
  calls `imprint.cutoff_of()`.
- **Payment.** The return is paid by the person's own policy (#3667, see
  `SLEEVE_INSURANCE_SPEC.md`). This section once carried a premium debited
  from the post's own till (or `db.post_insurer` where the post had none)
  and credited to the clinic's Thawn-Harrison billing terminal, so that a
  poor cart sold noodles toward its own keeper's resurrection; that model
  was superseded 2026-09-25 (#3667): the premium, the till and the clinic
  credit go.
- **Succession discards it** — the empty book is the point. The per-shift
  record stays on the post but is never loaded into the new keeper.
  `examine` on the fixture shows the per-shift record.
- **`None` (no policy)** — no stranger is hired, and the slot stays dark.
  A named keeper with their own sleeve policy still returns to a shift
  that carries their blueprint name. The snapshot stays on the post.

## 3 · The sleeve fiction

Sleeve insurance is a **personal** policy bought in advance at a
Thawn-Harrison terminal, keyed to the buyer's sample, and consumed at
payout. See `specs/SLEEVE_INSURANCE_SPEC.md`. Since #3673 a PC also needs
a personal policy to come back; it costs 0 tokens
(`world/insurance.POLICY_PRICE`). PCs die and flash-clone back
(`DEATH_AND_SLEEVE_LIFECYCLE_SPEC`); the world already accepts that death
is a financial event.

**Overturned 2026-09-25 (owner rulings, #3667).** This section held that
NPC policy was the class-stratified version of the PC's: employers insure
from a post's till, the premium paid to the clinic, "like a PC" — Helix
insures its companions, the clinic insures its doctors (Marta re-sleeving
on her own AutoDoc), a cart vendor at the Toe never could. That was wrong:
PCs resleeved free at the time, and the owner called this section "likely
hallucinated".

## 4 · Initial roster

**Overturned 2026-09-25 (#3667).** The roster recorded a lean per post for
who the post insured: **successor** for street commerce — Ottilie Krug
#5222 (food cart, the Toe; the empty-book consequence is the gig's teeth)
and Ezra Vantomme #5161 (Kaspar Pawn & Salvage; a pawn shop outlives any
pawnbroker); **resleave** for the institution-backed — Marta Okoye #5134 /
Nikolai #3164 (clinics) and Sable #3070 / Vesper #3109 (Helix lounge,
corporate VIP assets); and the owner's call for Del Marchetti #5151 (the
Last Shift) and Sully (Hub & Howl), whom the owner then decided are
INSTITUTIONS (re-sleeve). Now nobody is seeded; every human and synth
soul buys their own policy at the lobby terminal, and the Rook, who
cannot leave his seal, stays uninsured by ruling.

## 5 · Phasing

The parts of this spec go by these names (cited from code and other
specs):

1. **§P1 — Blueprints for the existing roster** (§1.1). Pure data +
   builder, no behavior change. Verify: delete-and-rebuild a test copy
   matches the live original (identity, kit, persona, card).
2. **§P2 — Posts + watcher + succession** (§1.2, §1.3, §1.4): stock/till
   persistence and the empty book. This alone makes NPC murder *playable
   content*.
3. **§P3 — the return + the memory snapshot/restore** (§2), for the clinic
   and Helix roster, with the re-sleeve gap; paid by the person's own
   policy (#3667).

### Unbuilt

- **Vacancy is visible.** 📋 UNBUILT (no issue) — on purpose. While
  unstaffed, the post would swap to a vacant `integration_desc` ("The food
  cart stands cold, its burner ring dark, a chain through its wheels.") —
  the room tells the story without a keeper. `vacant_desc`,
  `arrival_successor` and `arrival_resleave` are authored in
  `world/npcs/blueprints.py` with no reader anywhere in the tree. Owner
  ruling 2026-09-08: this stays UNBUILT on purpose — *"I view this as
  unwired. Eventually, we'll have an employment computer system and it'll
  have something to connect to."* The fixtures are kept for that system to
  connect to. Do not wire it before then, and do not delete the strings.
- **Generator identity for successors.** 📋 UNBUILT (deferred to P4b in
  `NPC_NEEDS_AND_GOALS_SPEC`). A successor would roll a new name from the namebanks, new face/build from
  the identity pools, new flavor from `mob_flavor`; the trade-specific kit
  and archetype stay. The civilian spawner's `dress_from_role`
  wardrobe-pool pattern is the precedent for successor wardrobe variety.
  `build_successor` is this mode, unensouled; it must not be wired as-is
  (§1.1).
- **Succession as WSIS fodder.** 📋 UNBUILT (no issue). Rumor lines in the
  crowd pools ("heard the old butcher got ground into her own stock"),
  successor pricing grudges (starts with a `feel` against the killer's
  *description* if a witness dossier survived on the post), vacancy crime
  (an unstaffed till invites a heist).

## 6 · Not decided

- **Delays:** hours or days? (Lean: successor = days — absence should be felt;
  re-sleeve = shorter — insurance is efficient.) (The owner-decided values
  and what runs are in §1.2.)
- **Witnessed murder:** does the post snapshot let a successor *know* who
  killed their predecessor (a seeded `feel: wary` against the killer's
  apparent identity), or is a truly blank book cleaner? (Lean: blank for P2;
  the grudge is a delicious later.)
- **PC-adjacent NPCs** (Companions with client books): does Helix re-sleeve
  restore client dossiers wholesale, or is a partial gap a story hook?
- **Who returns:** should a hired soul who bought a sleeve policy come back
  to their post, or is a return only for the named cast whose blueprint name
  the shift carries?
- **One delay or two:** does the recorded successor 24h / re-sleeve 8h still
  stand, which would need a separate return delay, or is one per-post
  `post_delay` for return and succession alike the rule?
- **§P3:** is any part of it still unbuilt; in particular, is the per-shift
  memory snapshot meant to be kept after a return rather than consumed by it?

## 7 · Related documents

- `DEATH_AND_SLEEVE_LIFECYCLE_SPEC` — the sleeve fiction NPCs inherit.
- `SLEEVE_INSURANCE_SPEC.md` — the personal policy that pays for a return.
- `NPC_DISPATCH_AND_SIMULATION_SPEC` — the director heartbeat.
- `NPC_MEMORY_AND_IDENTITY_SPEC` — what a successor forgets.
- `GIG_PROTOTYPE_BUTCHER_SPEC` — the first post.
