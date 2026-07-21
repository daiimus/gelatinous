# Gig Prototype — The Butcher

> **Status:** 📋 PROPOSAL (2026-07-20) — design only, nothing built. The **first
> gig**: a prototype fetch-quest that proves the loop the faction/favor/rep
> capstone will hang off — *an NPC wants something → a player delivers it → the
> NPC pays*. Deliberately minimal and self-contained. It builds **entirely on
> shipped systems** (corpse/anatomy, the LLM NPC brain, tokens, `give`); the only
> new code is the Butcher herself. Sibling gig — the **Ripper** (sapient organs,
> black-market) — is a later doc; this one is **animal meat only**. Ties into
> `LLM_GAMEMASTER_SPEC` (the NPC brain + the deterministic-transaction pattern),
> `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC` (corpses/organs/substances), and
> `NPC_MEMORY_AND_IDENTITY_SPEC` (she remembers her suppliers).

---

## 0 · Purpose & the capstone connection

The world is a rich sandbox with no *pull* — nobody wants anything from the
player, nobody remembers if they came through. This gig is the smallest possible
brick that adds that pull: a standing demand + a payout + a memory. It is the
"snap-on-later" WSIS philosophy in miniature — **one connectable piece** (a favor
loop keyed to a payout), not the faction/economy/world-state machine. Factions,
reputation rates, and a food economy grow around it later; the brick stands alone
and is playable the moment it ships.

## 1 · The loop

```
@spawnmob/rat  (staff, for now) → a rat is in the world → player kills it
  → a rat corpse (carries the rat organ manifest)
  → player: `give corpse to butcher`  (or drops it on her block)
  → Butcher [DETERMINISTIC]: breaks it down via the butchery table — named cuts
       (rat tail, chops, haunch, offal) gated by each part's CONDITION, the rest
       ground to mystery meat → destroys the corpse → pays the player by YIELD VALUE
  → Butcher [LLM]: voices the exchange and remembers the supplier
  → repeat — her demand is standing

A clean, fresh kill breaks down into good cuts and pays well; a shot-up or rotting
one collapses into cheap mystery meat. How you kill it and how fast you bring it in
both matter.
```

The split is the one this project already committed to (`LLM_GAMEMASTER_SPEC`
tool-reliability note): **the transaction is deterministic code; the model is
voice + memory.** A real payout never rides a model tool-roll.

## 2 · What it reuses (no new code)

- **Supply — the rat creature:** `@spawnmob/rat` (`commands/CmdSpawnMob.py`) makes
  a complete, anatomically-real rat — `species="rat"`, rat organs in its medical
  state, rat flavor/longdescs, a composed sdesc ("a wiry brown rat"). Killed, it
  drops a corpse whose snapshot carries the rat organ manifest. **Staff-spawned
  for the prototype;** ambient sewer-spawn is deferred (owner builds the sewers).
- **Valuation — the corpse:** `typeclasses/corpse.py` — `get_medical_snapshot()` /
  `db.medical_state_at_death` (the organ manifest) minus `db.removed_organs` (so a
  pre-harvested carcass is worth less, for free).
- **Transaction/payment:** the bartender pattern — `tokens` on the payer, a
  `register` on the butcher's block, `world.shop.utils.format_currency`. The
  handler is modeled on `Bartender._fulfil_order`.
- **Hand-over:** the `give` command → the butcher's `at_object_receive` room hook
  detects the corpse (the same arrival-hook shape the bar uses).
- **Voice + memory:** the LLM NPC brain (`LLMNpcMixin`) + a new `butcher`
  archetype. She remembers suppliers via the shipped dossier/valence layer
  (`NPC_MEMORY_AND_IDENTITY_SPEC` §8).

## 3 · The build (the Butcher only)

### 3.1 `Butcher` typeclass (`typeclasses/butcher.py`, sibling of `Bartender`/`Doctor`)
- `LLMNpcMixin, Character`; `db.is_butcher_npc = True` (loop-guard marker);
  `db.llm_driven` opt-in (off by default, like the others).
- `_find_block()` → the `ButcherBlock` fixture (the register holder), mirroring
  `_find_bar`.
- `at_object_receive(obj, **kw)` → if `obj` is a `Corpse` **and** an accepted
  animal species → `_process_corpse(obj, giver)`. A human/synthetic/robot corpse
  is **refused** (not destroyed): leave/return it + a line ("I don't grind
  people" / "that's chrome, not meat — take it to someone who deals in that").
- `_name_aliases()` → `["butcher", "meatpacker", "grinder"]`.

### 3.2 `_process_corpse(corpse, giver)` — the deterministic core
1. **Species guard** — accept only non-sapient animal species (`rat`, plus future
   fauna); reject human / `synthetic_humanoid` / `robot` with a line, no
   destruction.
2. **Butcher it** — walk the species BUTCHERY TABLE (§3.4). Each entry maps an
   anatomical part → a named ingredient, and its **yield is gated by that part's
   condition** on this corpse:
   - a part in `severed_locations` / `removed_organs` (or `head_severed`) →
     **0** of its ingredient (it's gone — shot off, already harvested);
   - per-location wound severity from the medical snapshot scales the cut down
     (a shotgun-shredded trunk yields few or no chops);
   - `get_decay_factor()` scales EVERYTHING down (a rotting rat → little usable,
     mostly waste; a fully-rotted one → refused with a line).
3. **Produce the named cuts** — spawn each surviving ingredient (a rat tail, rat
   chops, a rat haunch, rat offal…) onto the block / into her stock. 2–4 named
   products from a clean carcass.
4. **Sweep the remainder into `ground mystery meat`** — the head, trim, damaged
   bits, and anything below cut grade → N units of mystery meat (the catch-all).
5. **Payout** = Σ(value of everything produced) — named cuts worth more than
   mystery meat — so **a clean, fresh, intact kill pays well and a mangled or
   rotting one pays scraps.** Empty/harvested carcass → a token payout + a dry line.
6. **Destroy** the corpse (rendered), **pay** (`giver.tokens += payout`; account
   against `block.db.register`), and **render** the grind gesture via
   `execute_cmd("emote …")`; the LLM voices it on the same beat.

### 3.3 The butchery products (several named ingredients + mystery meat)
Every product is built **ingredient-grade** (per the §7 pathway): an item carrying
`db.contributions` (`{substance_id: doses}`) + a `role`/`flavour`, and an `("eat",
delivery_method)` tag — so it is edible *today* through `world/consumables.py` and
a *menu ingredient* the moment a food recipe references it, no rework. The rat
yields (from §3.4): **a rat tail**, **rat chops** (center cut), **a rat haunch**,
**rat offal**, and **ground mystery meat** (the remainder). Mystery meat is the
grimy catch-all; the named cuts are the good stuff. See §7 for how these feed menus.

### 3.4 The butchery table (`rat`)
A species-scoped dict mapping a source part → `(ingredient, base_yield,
condition_source)`. Base yields are tuning knobs; the condition source is the
corpse field that gates it:

| Source part | → Ingredient | Base | Gated by |
|---|---|---|---|
| `tail` | a rat tail | 1 | `severed_locations` |
| trunk / center cut | rat chops | 2–3 | trunk wound severity |
| hindlegs | a rat haunch | 1–2 | `severed_locations` |
| heart/liver/kidney | rat offal | 1 | `removed_organs` |
| (everything else) | ground mystery meat | N | overall decay/condition |

`get_decay_factor()` multiplies the whole table. Extend per animal as fauna grows;
each new species ships its own table + its cuts' recipes.

### 3.5 The `butcher` LLM archetype (`world/llm/prompt.py`)
- **Duties:** she runs the block — buys animal carcasses, breaks them down into
  cuts (tails, chops, haunches, offal) and grinds the rest to mystery meat. She
  prices by what a carcass yields and says so ("clean kill, that one — good
  chops"; "you dragged this halfway across the colony, it's mince now"). Grim,
  unbothered, transactional. She does **not** touch people or chrome (people-organs
  are the Ripper's trade; scrap isn't food).
- **Tools:** base `remember` / `feel` (+ maybe `release`). The buy/grind/pay
  transaction is **deterministic, not a tool** — exactly like the bartender's
  orders. Per the tool-reliability lesson, the few-shot **demonstrates**
  `remember`/`feel` (tag a regular supplier, sour on a time-waster) + a restraint
  `none`.
- A `ButcherBlock` fixture (register holder + setting), sibling of `BarCounter`.

## 4 · Design decisions (locked with the owner, 2026-07-20)

- **Payout = yield value** — the corpse is broken down via the §3.4 butchery
  table; named cuts (tail/chops/haunch/offal) are worth more than ground mystery
  meat, and each cut's yield is gated by that part's condition. So a clean, fresh,
  intact kill pays well; a mangled or rotting one pays scraps. **This makes how you
  kill it and how fast you deliver it matter** — combat quality + freshness feed the
  reward.
- **Products are ingredient-grade from day one** — every cut + the mystery meat
  carries `db.contributions` + an eat-delivery tag, so the food/menu economy (§7)
  snaps on without reworking the items. Only the cook/menu LAYER is deferred.
- **Animal corpses only** (rat now). Human / synthetic / robot → **refused**; the
  **Ripper** (later gig) handles sapient organs.
- **Rep for the prototype = she remembers the supplier** (the existing dossier).
  Rep-scaled rates and bonus asks are the favor-loop snap-on, deferred.
- **Rat supply = `@spawnmob/rat`** (staff) for now; ambient sewer-spawn when the
  sewers exist.

## 5 · Phasing

- **Prototype (this spec):** the Butcher — `at_object_receive` accept → butcher →
  pay, the §3.4 butchery table + its named ingredient-grade products (cuts +
  mystery meat), the `butcher` archetype + block. Rats staff-spawned.
- **Next (small):** ambient rat vermin in the sewers/grimy rooms — self-serve
  supply. The first bite of the ecosystem/world-state thread.
- **Then (the food economy, §7):** the cook/menu LAYER — food recipes that consume
  the cuts (rat tail → rat tail stew, rat chops → grilled chops) on the existing
  bar/recipe engine; the cuts circulate as tradable ingredients.
- **Later (the capstone thread):** rep-scaled rates + a bonus ask ("bring me
  something bigger"); corpse-provenance flowing into the meat (a toxic-sump rat, or
  a drugged/chromed body → tainted `contributions` — §7 tier 3); the **Ripper**
  sibling gig (sapient organs — black-market, cyberware-grade, same corpse-in
  machinery, different clientele + legality).

## 6 · Open questions

- **Decay:** does a rotting rat pay less / get refused? (Lean: a decay modifier;
  refuse a fully-rotted carcass.)
- **Placement:** which room is the butcher's shop? (Content, owner's call.)
- **Finite till:** does she pay from a seeded `register` that can run dry
  (economic pressure, a hook for the economy layer) or an infinite purse? (Lean:
  finite/seeded.)
- **Yield tuning:** the §3.4 base yields + the wound/decay curves — how punishing
  should a messy kill or a stale corpse be? (Tune in play.)
- **Cut identity:** are cuts fungible ("rat chops" ×N stack) or individually
  tracked? (Lean: fungible stackable items keyed by cut type — simpler, and the
  recipe engine matches by keyword.)

---

## 7 · Ingredient & menu pathway

The whole point of the butchery table (§3.4) is that its outputs are **real
ingredients**, not flavor props. The game's consumption model is one general
pipeline — `item → db.contributions {substance_id: doses} → delivery method
(eat/drink/inject) → effect` — and a bar "ingredient" is just an item with that
profile. The butcher's cuts join it in three tiers:

- **Tier 1 — consumable (built in the prototype).** Every cut + mystery meat ships
  with `db.contributions` (sustenance / grimy-protein) and an `("eat",
  delivery_method)` tag, so it's edible today via `world/consumables.py`. No menu
  needed.
- **Tier 2 — ingredient → menu item (the "then" phase).** A menu item is a recipe:
  `order_keywords` + ingredients (whose contributions the engine sums) + a price —
  the *same* machinery the bar drinks use (`world/bar.py` `project_mix` /
  `make_drink_from_recipe`, generalized to food). A **cook/kitchen** (or the bar)
  turns `[a rat tail + …]` → **rat tail stew**, `[rat chops + …]` → **grilled rat
  chops**. Ordering rides the deterministic order parser (`_is_conversational_order`)
  exactly as drinks do. The butcher supplies the key ingredient; the food economy is
  butcher (cuts) → cook (dishes) → patrons (eat).
- **Tier 3 — provenance in the meat (emergent, later).** Organs don't yet carry
  substance profiles, but the substance system exists. When they can, a corpse's
  origin flows into its cuts' `contributions`: a toxic-sump rat, or (via the Ripper)
  a drugged/chromed body, yields meat that's usually cheap protein but sometimes
  carries heavy-metal traces or a drug residue that *hits* when eaten. "Mystery
  meat" becomes a genuine gamble, and *where the corpse came from* matters.

**Build implication (already reflected in §3.3/§4):** the *items* are
ingredient-grade from day one; only the *cook/menu layer* is deferred. That is the
connective tissue between this gig and the bar/food side that already exists.
