# NPC Posts & Reincarnation Spec

> **Status:** ✅ §P1 + §P2 SHIPPED. §P3 (memory snapshot/restore at death
> for re-sleeve) PARTLY built — the snapshot is written and read, but see
> the drift note below.
>
> **CORRECTED 2026-09-08 (#2437).** This banner previously said "§P1 + §P2
> + §P3 SHIPPED — the full ladder" in one sentence and "§P3 … not built"
> in another, six lines apart. Four further claims were checked against
> the code and were stale:
>
> * **The watcher does NOT live in `world/npcs/posts.py`.** That module is
>   a 64-line retired stub; its own docstring explains that it once carried
>   a second post watcher which disagreed with `world/souls/posts.py` about
>   which fixture owned a post, so both acted and the bodies it rebuilt
>   were never ensouled (#2132). There is one registry now, and the sweep
>   rides the SOULS heartbeat.
> * **Re-sleeve restores but does NOT consume.** `_try_resleave` reads
>   `post_memory_snapshots[shift]` and never clears it. "Restores-and-
>   consumes" describes an intent, not the code.
> * **Vacancy is NOT visible.** `vacant_desc`, `arrival_successor` and
>   `arrival_resleave` exist in blueprint fixture data with no reader
>   anywhere; the desc-swap helpers were deleted. Owner ruling 2026-09-08:
>   this stays UNBUILT on purpose — *"I view this as unwired. Eventually,
>   we'll have an employment computer system and it'll have something to
>   connect to."* The fixtures are kept for that system to connect to. Do
>   not wire it before then, and do not delete the strings.
> * **"Murder deletes social capital" is not what the code does** — see
>   the drift note immediately below.
>
> **Owner-decided values (unchanged):** successor 24h / re-sleeve 8h; the
> till/stock are the POST's (successors inherit); Del + Sully are
> INSTITUTIONS (re-sleeve).

## Succession: the drift since this spec was written (#2437)

This spec sells a pillar — *"the new butcher doesn't know you're the
ratcatcher… murder deletes social capital"* — implemented by
`build_successor` rebuilding a stranger from the blueprint with empty
dossiers. **`build_successor` has no production caller and never has.**
What runs instead offers the vacant slot to the nearest idle SOUL.

The souls layer arrived after this spec and changed the ground under it.
Measured live 2026-09-08: 78 souls, 49 holding posts, 29 idle. Three
replacement tiers now exist, and they match the owner's stated ideal —
*"NPCs have a history/story with souls… souls occasionally generated to
cover losses… some might be resleeves and be consistent"*:

1. **Re-sleeve** — the same person returns, memories intact
   (`_try_resleave`). Healthy.
2. **Succession** — an idle soul takes the post (`_eligible_candidates`
   → `do_claim`). Works mechanically.
3. **Generation** — `world/souls/population.sweep` seeds new residents.
   Exists.

**Three gaps between that architecture and the ideal**, each tracked as
its own issue rather than assumed:

* **History barely accumulates, and only with players.** There are
  exactly two writers of opinion in the tree: being attacked
  (`react_to_attack`) and being spoken to by a player (`llm_npc`). Souls
  never form opinions about EACH OTHER. Measured: 4 of 49 posted souls
  have a single acquaintance; 0 of 29 idle souls have any. This is the
  largest gap and it is independent of succession.
* **The idle pool is the colony, not a labour reserve.** Those 29 are
  gangers, scavvers, salarymen, hawkers, an addict, a DJ, a grower —
  all with homes, one blueprinted. `_eligible_candidates` filters only
  on has-no-post / not-mid-survival-task / not-a-robot and then sorts by
  DISTANCE, so the butcher's block can go to a ganger.
* **The generation loop cannot see that.** `SEED_TARGET_UNEMPLOYED = 2`
  against an `unemployed_count` of 29, so it never fires — while the
  labour reserve in the sense that matters is roughly zero. One counter
  carries two meanings of "unemployed".

**`build_successor` must not simply be wired.** It builds a genuine
stranger (random name and face from the pools, same trade, empty
dossiers) but never ENSOULS it — no soul tag, no needs, no schedule, no
wage. Wiring it as-is reproduces #2132, where posts stood staffed by
mannequins.

The pillar is currently satisfied by accident: every idle soul happens
to have zero acquaintances, so today's replacement IS a stranger. It
breaks silently the first time a soul with history returns to the pool.

> Originally: Named NPCs
> (Ottilie, Del, Marta, Vesper…) currently die **permanently and
> unreproducibly**: death → corpse → the character object is deleted (#1022),
> dossiers and memories with it, and the NPC was hand-built in a shell session
> with no recipe to remake them. The colony's one working respawn loop — the
> security complement (`world/director/population.py`: base + complement +
> heartbeat + `spawn_secbot` factory) — works precisely because those units are
> **factory-made from blueprints**. This spec generalizes that loop to every
> staffed NPC via three pieces: **BLUEPRINTS** (a build recipe per named NPC),
> **POSTS** (the staffed fixture that survives its keeper), and a
> **reincarnation POLICY** per post: **re-sleeve** (institutions come back as
> themselves), **successor** (street vendors are replaced by a stranger), or
> **none** (a death that is a world event). Decided with the owner 2026-07-24:
> the re-sleeve/succession mix is the model — *"some NPCs will be institutions;
> others will be forgettable."* Ties into `DEATH_AND_SLEEVE_LIFECYCLE_SPEC`
> (the sleeve fiction NPCs inherit), `NPC_DISPATCH_AND_SIMULATION_SPEC` (the
> director heartbeat that watches posts), `NPC_MEMORY_AND_IDENTITY_SPEC` (what
> a successor forgets), and `GIG_PROTOTYPE_BUTCHER_SPEC` (the first post).

---

## 0 · Purpose

Killing a named NPC should be **consequential, not catastrophic — and never
cheap**. Today it is catastrophic for the world (the butcher gig dies with
Ottilie, forever, until a builder hand-remakes her) and cheap for the killer
(no interesting consequence — the service just vanishes). The sleeve lifecycle
already answers "what does death mean here" for PCs; this spec extends the
same worldview to NPCs, with the colony's class system baked in:

- **Institutions re-sleeve.** An NPC with backing — a Helix VIP companion, a
  clinic doctor — carries sleeve insurance like a PC. They come back *as
  themselves*, after a delay. Killing them buys time, not erasure.
- **The street gets successors.** Kill a cart vendor and days later *someone
  else* claims the stall — new face, new name, same trade, **an empty book**.
  You can't erase the service, but you permanently erase the relationships:
  the new butcher doesn't know you're the ratcatcher, owes you nothing, and
  prices you like a stranger. Murder deletes *social capital*, not commerce.
- **Some deaths are stories.** A post with policy `none` stays dark. Reserved
  for NPCs whose loss should reshape a district.

## 1 · The three pieces

### 1.1 Blueprints — the build recipe (needed regardless of reincarnation)

A **blueprint** is a data + builder pair that can construct a complete named
NPC from nothing: typeclass, identity axes (sex/height/build/skintone —
validated against the identity vocab; invalid values are the known
server-killer), wardrobe kit (garment specs incl. `worn_desc`/coverage/layer/
color), longdescs, voice, persona seed (archetype + name + description +
personality + scenario), `llm_driven`, stats, placement line, and **post
binding**. The `spawn_secbot` / `spawn_civilian(role, anchor)` factories are
the proven shape; this extends it from role-generic to person-specific.

- Lives in `world/npcs/blueprints.py` (one registry, one builder), or one
  module per district if it grows.
- **Dual-mode identity:** a blueprint carries either a FIXED identity (used by
  re-sleeve — Ottilie is Ottilie) or a GENERATOR (used by successor — roll a
  new name from the namebanks, new face/build from the identity pools, new
  flavor from `mob_flavor`; the trade-specific kit and archetype stay). The
  civilian spawner's `dress_from_role` wardrobe-pool pattern is the precedent
  for successor wardrobe variety.
- **Side benefit (why this ships first):** blueprints make the existing roster
  *reproducible* — today Ottilie/Del/Marta exist only as live DB state from
  imperative shell sessions. A blueprint is also a backup, a test fixture,
  and cheap content for the next market NPC.

### 1.2 Posts — the thing that survives its keeper

A **post** is the staffed workplace: the food cart, the chain-hoist bar, the
clinic + AutoDoc, the pawn counter. Posts already exist physically; this spec
makes them *administrative*:

- The post fixture carries: `db.post_blueprint` (registry key),
  `db.post_policy` (`resleave` | `successor` | `none`),
  `db.post_delay` (seconds of vacancy before reincarnation),
  `db.post_keeper` (the current NPC), and `db.post_vacant_since`.
  > **SUPERSEDED by shift slots (owner rulings 2026-08-20).** A venue runs
  > 24/7 in eight-hour shifts, so the keeper and the vacancy stamp are now
  > PER SHIFT: `db.post_slots` holds `{shift: {"keeper": …,
  > "vacant_since": …}}`, and `db.post_blueprints[shift]` names the person
  > who owns that shift (`db.post_blueprint` survives as the post-wide
  > fallback). `register_post` also writes `db.post_role` and
  > `db.post_wage_rate`, and `_try_resleave` reads `db.post_insurer` where
  > the post's own till is not the payer. `db.post_policy` and
  > `db.post_delay` stay post-wide.
  >
  > `db.post_keeper` survives as a single-value LEGACY MIRROR, rewritten by
  > `register_post`, `_install_keeper` and `do_claim` every time a keeper is
  > installed. `db.post_vacant_since` is only ever cleared by `do_claim`, so
  > on a slots post it is stale rather than wrong — nothing reads it once
  > `post_slots` exists. Neither key is dead: the shop/bar gate
  > (`world/service.py`, `typeclasses/shopkeeper.py`, `typeclasses/bar.py`,
  > `world/souls/actions.py`), `keeper_on_duty`'s last-resort fallback,
  > `world/npcs/posts.snapshot_keeper_memory`, and `sweep`'s one-time
  > adoption of a pre-slots post all still read `post_keeper`. Ask the slots
  > first.
- **The post persists through death.** The cart keeps its stock, till, and
  prices while unstaffed — commerce pauses, property remains. (Deterministic
  transactions gate on the keeper being present: no butcher, no grinding.)
- **Vacancy is visible.** While unstaffed, the post swaps to a vacant
  `integration_desc` ("The food cart stands cold, its burner ring dark, a
  chain through its wheels.") — the room tells the story without a keeper.
  > **NOT BUILT, on purpose** — see the banner's owner ruling of 2026-09-08.
  > The desc-swap helpers were deleted; `vacant_desc`, `arrival_successor`
  > and `arrival_resleave` are still authored in `world/npcs/blueprints.py`
  > with no reader anywhere in the tree. What a dark slot emits today is a
  > signal, not prose: `wsis.emit("post_vacant", …)` from
  > `world/souls/posts.sweep`, plus a counter that answers closed while
  > nobody stands the running shift. Keep the strings — the employment
  > computer system is what they are waiting for.

#### 1.2.1 What a role must supply to stand a post

The post fixture is half the contract; the other half is the **job**,
registered with `world.service.register(role, handler, ...)`. Until #2824
this existed only as convention plus one inline comment, so the
requirements are stated here.

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

### 1.3 The watcher — a generalized complement loop

> **AS BUILT — the sweep rides the SOULS heartbeat, not the director's.**
> `world/souls/engine` calls `world/souls/posts.sweep()` once every
> `SWEEP_EVERY_BEATS` (10) beats, on beat 3. The shape below is right;
> the ownership is not. See the banner for why there is only one
> registry (#2132).

The director heartbeat (the same `GLOBAL_SCRIPTS` loop that runs patrol beats
and the security complement) gains a **posts sweep**:

1. For each registered post: is `db.post_keeper` alive, intact, and at (or
   near) the post? A deleted/dead keeper stamps `post_vacant_since` and swaps
   the vacant desc.
   > **As built:** the question is asked per SLOT, by `_slot_held`, and the
   > rule is holding by ASSIGNMENT, not by attendance — alive (`is_dead()`
   > over `medical_state`, never a `db` flag — #2706) and still matched by
   > `soul_post`/`soul_schedule` — so a keeper who steps out for a meal does
   > not vacate the slot (#2371). One exception, and it is deliberate: a
   > souled keeper with no `soul_post` recorded holds the slot by standing
   > in it, or the Rook's own booth reads dark forever (#2178). An unsouled
   > keeper holds nothing; that is a build error now, not a case. The stamp
   > lands on that slot's `vacant_since` and emits `post_vacant`. No desc
   > swap.
2. When `now - post_vacant_since > post_delay`, run the policy:
   - **`resleave`** → rebuild from the blueprint's FIXED identity; restore
     the memory snapshot (§2); arrival renders as a return ("the butcher is
     back at her cart, moving like the week never happened").
   - **`successor`** → rebuild with the GENERATOR identity; dossiers start
     **empty**; arrival renders as a claim ("someone new has the cart —
     younger, warier, the same cleaver").
   - **`none`** → do nothing, forever. The vacancy *is* the content.
3. Same de-confliction rules as the security loop: one replacement per sweep,
   never while combat is live at the post.

## 2 · Memory across death

Dossiers (`db.llm_dossiers`) and episodic memory (`db.llm_memories`) live on
the NPC object and die with it. The policy decides what should survive:

- **Snapshot at death:** the corpse-creation hook (or the watcher's vacancy
  stamp) copies the keeper's dossiers + memories onto the POST
  (`db.post_memory_snapshot`). Cheap, point-in-time, no periodic churn.
  > **As built:** keyed by SHIFT. `world/souls/posts.snapshot_imprint`,
  > called from `typeclasses/death_progression`, writes
  > `db.post_memory_snapshots[shift]` and captures more than this line
  > promises — thoughts, opinions, and the people known by face and by
  > voice, as well as dossiers and episodic memory — because it shares
  > `world/imprint.py` with the player's flash clone and so cannot drift
  > from it. The singular `db.post_memory_snapshot` remains the fallback
  > for a post with no slots: `snapshot_imprint` itself writes it when the
  > deceased matches only the legacy mirror, and the older
  > `world/npcs/posts.snapshot_keeper_memory` still writes it from the
  > NPC-deletion branch of the same death path. Two writers, one key, on
  > purpose — don't delete either half.
- **`resleave` restores it** — continuity of self is the product the
  insurance pays for. Optional flavor: a configurable "gap" (the last N hours
  missing) if the death/sleeve fiction wants re-sleeve trauma to show.
  > **The gap shipped**, and so did a price. The gap is not optional and not
  > local to this system: `world/imprint.GAP` (5400s, ~90 minutes) sets the
  > backup's `taken_at`, and `restore` drops every memory, thought, opinion
  > and newly-met face from inside it — so murder stays a mystery for the
  > player's flash clone and the NPC keeper alike, through one code path.
  > (`RESLEAVE_PREMIUM`'s neighbour `RESLEAVE_GAP` in `world/souls/posts.py`
  > is a leftover constant nothing reads; `world/imprint.GAP` is the live
  > one.) The premium is real: debited from the post's own till — or
  > `db.post_insurer` where the post has none — and credited to the clinic's
  > Thawn-Harrison billing terminal, with the balance re-read at the write
  > so the credit only happens if the debit did. A till that cannot afford
  > it simply keeps earning: the cart sells noodles toward its own keeper's
  > resurrection. `_try_resleave` restores the snapshot and does NOT clear
  > it; per the bullet below, that is the intended disposal, not an
  > omission.
- **`successor` discards it** — the empty book is the point. The snapshot is
  retained on the post (GM-readable archaeology: what the old butcher knew)
  but never loaded into the new keeper.
- **`none`** — the snapshot is the NPC's estate; nothing consumes it.

## 3 · The sleeve fiction (why this is coherent, not gamey)

PCs die and flash-clone back (`DEATH_AND_SLEEVE_LIFECYCLE_SPEC`); the world
already accepts that death is a financial event. NPC policy is just the
class-stratified version of the same truth: sleeve insurance is *expensive*.
Helix insures its companions; the clinic insures its doctors (Marta re-sleeves
on her own table — the AutoDoc that patches players regrows its owner); a
cart vendor at the Toe of a scrapped mech leg was never going to afford it.
Nobody needs a new metaphysics — only a premium they can or can't pay.

## 4 · Initial roster & policy assignments (owner's call per row)

| NPC | Post | Lean | Rationale |
|---|---|---|---|
| Ottilie Krug #5222 | food cart, the Toe | **successor** | street vendor; the empty-book consequence is the gig's teeth |
| Ezra Vantomme #5161 | Kaspar Pawn & Salvage | **successor** | street commerce; a pawn shop outlives any pawnbroker |
| Del Marchetti #5151 | the Last Shift | owner's call | a proprietor with a name on the wall — successor is grimmer, re-sleeve says the leather bar protects its own |
| Marta Okoye #5134 / Nikolai #3164 | clinics | **resleave** | institution-backed; re-sleeves on her own AutoDoc |
| Sable #3070 / Vesper #3109 | Helix lounge | **resleave** | corporate VIP assets; Helix absolutely insures them |
| Sully | Hub & Howl | owner's call | — |

## 5 · Phasing

1. **§P1 — Blueprints for the existing roster.** Pure data + builder, no
   behavior change. Immediately buys reproducibility/backup for the six-plus
   hand-built NPCs. Verify: delete-and-rebuild a test copy matches the live
   original (identity, kit, persona, card).
2. **§P2 — Posts + watcher + `successor`.** The cart is the pilot post
   (delay: a few real days). Vacant desc, stock/till persistence, generator
   identity, empty book. This alone makes NPC murder *playable content*.
3. **§P3 — `resleave` + the memory snapshot/restore.** Clinic + Helix roster.
   Optional re-sleeve gap flavor.
4. **Later:** succession as WSIS fodder — rumor lines in the crowd pools
   ("heard the old butcher got ground into her own stock"), successor pricing
   grudges (starts with a `feel` against the killer's *description* if a
   witness dossier survived on the post), vacancy crime (an unstaffed till
   invites a heist).

## 6 · Open questions

- **Delays:** hours or days? (Lean: successor = days — absence should be felt;
  re-sleeve = shorter — insurance is efficient.)
- **Does a successor inherit the till?** (Lean: yes — the cart's property, not
  the keeper's; robbing the till is a separate crime with its own spec-less
  charm.)
- **Witnessed murder:** does the post snapshot let a successor *know* who
  killed their predecessor (a seeded `feel: wary` against the killer's
  apparent identity), or is a truly blank book cleaner? (Lean: blank for P2;
  the grudge is a delicious later.)
- **PC-adjacent NPCs** (Companions with client books): does Helix re-sleeve
  restore client dossiers wholesale, or is a partial gap a story hook?
- ~~**Who registers posts**~~ **DECIDED (owner, 2026-07-24): data-driven, no
  builder command.** The post binding, policy, and delay are FIELDS of the
  blueprint; the watcher iterates the blueprint registry, and registration is
  the deploy cycle. Owner's standing principle: builder tooling will
  eventually be designed as an extensive, comprehensive suite — one deliberate
  project. Until then, ad-hoc builder commands are tech debt (each one is a
  future migration), so content-adjacent config stays in data.
