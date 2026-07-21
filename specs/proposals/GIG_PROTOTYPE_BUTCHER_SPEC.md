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
  → Butcher [DETERMINISTIC]: reads the corpse's organs → grinds →
       destroys the corpse, spawns N "ground mystery meat", pays the player tokens
  → Butcher [LLM]: voices the exchange and remembers the supplier
  → repeat — her demand is standing
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
2. **Enumerate organs** — read the corpse's organ manifest minus `removed_organs`.
3. **Payout** = Σ(organ value from the §3.4 table) × a condition/decay modifier.
   An empty or fully-harvested carcass → a token payout + a dry line.
4. **Produce** — spawn N `ground mystery meat` (N scaled to organ mass) onto the
   block / into her stock.
5. **Destroy** the corpse (it has been rendered).
6. **Pay** — `giver.tokens += payout`; account it against `block.db.register`.
7. **Render** — `execute_cmd("emote …")` for the grind gesture + the tokens
   handed over; the LLM voices it on the same beat.

### 3.3 `ground mystery meat` (item)
- One food/consumable item (reuse the substance/snack pattern from `world/bar.py`
  `DEFAULT_BAR_SNACKS` / the substances system). Vaguely unsettling flavor;
  edible. For the prototype it simply exists / stocks her counter — circulation
  into the food economy is deferred (§5).

### 3.4 Animal-organ → value table
- A small species-scoped dict (`rat` now): organ name → token value (a heart or
  liver worth more than a minor organ), plus a decay modifier. Extend per animal
  as fauna grows.

### 3.5 The `butcher` LLM archetype (`world/llm/prompt.py`)
- **Duties:** she runs the block — buys animal carcasses, grinds them, sells the
  mystery meat. Grim, unbothered, transactional. She does **not** touch people or
  chrome (people-organs are the Ripper's trade; scrap isn't food).
- **Tools:** base `remember` / `feel` (+ maybe `release`). The buy/grind/pay
  transaction is **deterministic, not a tool** — exactly like the bartender's
  orders. Per the tool-reliability lesson, the few-shot **demonstrates**
  `remember`/`feel` (tag a regular supplier, sour on a time-waster) + a restraint
  `none`.
- A `ButcherBlock` fixture (register holder + setting), sibling of `BarCounter`.

## 4 · Design decisions (locked with the owner, 2026-07-20)

- **Payout = per-organ** — rewards fresh, intact, un-harvested carcasses.
- **Animal corpses only** (rat now). Human / synthetic / robot → **refused**; the
  **Ripper** (later gig) handles sapient organs.
- **Mystery meat is produced** (edible / stock); food-economy integration deferred.
- **Rep for the prototype = she remembers the supplier** (the existing dossier).
  Rep-scaled rates and bonus asks are the favor-loop snap-on, deferred.
- **Rat supply = `@spawnmob/rat`** (staff) for now; ambient sewer-spawn when the
  sewers exist.

## 5 · Phasing

- **Prototype (this spec):** the Butcher — `at_object_receive` accept → grind →
  pay, the mystery-meat item, the rat-organ value table, the `butcher` archetype +
  block. Rats staff-spawned.
- **Next (small):** ambient rat vermin in the sewers/grimy rooms — self-serve
  supply. The first bite of the ecosystem/world-state thread.
- **Later (the capstone thread):** rep-scaled rates + a bonus ask ("bring me
  something bigger"); the food economy (mystery meat circulates, sold as snacks);
  the **Ripper** sibling gig (sapient organs — black-market, cyberware-grade,
  same corpse-in machinery, different clientele + legality).

## 6 · Open questions

- **Decay:** does a rotting rat pay less / get refused? (Lean: a decay modifier;
  refuse a fully-rotted carcass.)
- **Placement:** which room is the butcher's shop? (Content, owner's call.)
- **Finite till:** does she pay from a seeded `register` that can run dry
  (economic pressure, a hook for the economy layer) or an infinite purse? (Lean:
  finite/seeded.)
- **Yield:** one corpse → how many meat units? (Scale to organ mass; tune in play.)
