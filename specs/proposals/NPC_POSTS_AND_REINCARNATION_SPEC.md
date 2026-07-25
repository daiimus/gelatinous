# NPC Posts & Reincarnation Spec

> **Status:** 📋 PROPOSAL (2026-07-24) — design only, nothing built. Named NPCs
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
- **The post persists through death.** The cart keeps its stock, till, and
  prices while unstaffed — commerce pauses, property remains. (Deterministic
  transactions gate on the keeper being present: no butcher, no grinding.)
- **Vacancy is visible.** While unstaffed, the post swaps to a vacant
  `integration_desc` ("The food cart stands cold, its burner ring dark, a
  chain through its wheels.") — the room tells the story without a keeper.

### 1.3 The watcher — a generalized complement loop

The director heartbeat (the same `GLOBAL_SCRIPTS` loop that runs patrol beats
and the security complement) gains a **posts sweep**:

1. For each registered post: is `db.post_keeper` alive, intact, and at (or
   near) the post? A deleted/dead keeper stamps `post_vacant_since` and swaps
   the vacant desc.
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
- **`resleave` restores it** — continuity of self is the product the
  insurance pays for. Optional flavor: a configurable "gap" (the last N hours
  missing) if the death/sleeve fiction wants re-sleeve trauma to show.
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
- **Who registers posts:** builder command (`@post cart = butcher_ottilie,
  successor, 3d`) vs. blueprint self-registration at spawn. (Lean: builder
  command — posts are content decisions.)
