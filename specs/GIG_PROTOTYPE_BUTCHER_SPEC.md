# Gig Prototype — The Butcher

> **Status:** ✅ SHIPPED & LIVE (built 2026-07-24; spec'd #1242/#1244; built
> #1247/#1249/#1251/#1253/#1255). **As built, the design EVOLVED past this doc:**
> the block became a **hull-plate FOOD CART** (`typeclasses/butcher.py FoodCart` —
> ShopContainer + Seating: limited-inventory shop, till-crediting sales, 4 stool
> slots, `sit at cart`); the sell side is **COOKED DISHES**, not raw cuts — the
> grind's cuts are consumed as `world/food.py` catalog ingredients through
> `FOOD_RECIPES` (rat tail stew 12₮ … mystery skewer 3₮), so the §7 tier-2
> cook/menu layer shipped WITH the prototype. The buy side is exactly §3: give a
> corpse → condition-gated butchery table → payout by yield from the finite till;
> dish sales refill the till (closed economy loop). Live: **Ottilie Krug #5222**
> + cart #5221 at the Toe of Hammett's Boot (#5203); rats via `@spawnmob/rat`
> (ambient sewer spawn still deferred). Her persona grounds the cart's LIVE board
> + what she buys (anti-invention), and spoken DISH ORDERS serve deterministically
> off the cart (the bartender's #1235 pattern; since #2350/#2378 the matcher and
> the serve are the SHARED shelf code rather than methods on a butcher class —
> `world/shop/service.py` `serve_from_board_cart` → `serve_from_shelf` →
> `match_from_shelf` → `_fulfil_from_shelf` → the cart's `purchase_item`, scoring
> the cart's live `prototype_inventory` names and aliases; the `keywords` tuples
> in `world/food.py` are no longer what resolves an order; LLM never serves or
> quotes prices). Remaining from §5: ambient rat supply, rep-
> scaled rates, tier-3 provenance, the Ripper.

---


> **Owner ruling 2026-09-13 (#3375):** the cart is the **bar model** -- dishes are bought by speaking to whoever is working it (deterministic shelf match onto the board); the typed `buy` is refused at the cart (`FoodCart.TAKES_BUY = False`). Stores keep `buy`.

> **Owner ruling 2026-09-18 (#3413) — serve prose moved off the cart.**
> `FoodCart.at_object_creation` used to seed `purchase_msg_buyer` /
> `purchase_msg_room` ("You count out {price}, and the butcher sets {item} on
> the board."). Those attributes are **retired everywhere** — dead on any
> manned counter, and doubly dead here, since the cart refuses the typed
> `buy` at all. Owner: *"custom serve messages are awesome, but should
> probably live on the food/drink/consumable not the counter"*; *"retirement
> makes sense. We should standardize"*.
>
> **Nothing replaces them on the cart's dishes.** None of the five in
> `world.food.FOOD_RECIPES` — `rat_tail_stew`, `grilled_rat_chops`,
> `roast_rat_haunch`, `butchers_breakfast`, `mystery_skewer` — carries a
> `serve_line`, so all five are handed over with the BOARD style's gesture
> from `world/shop/service.py` (`STYLES["board"]`): *"sets {item} on the
> board and sweeps {price} into the till."* That is already the sentence a
> per-dish board line would have written, and taking it for the whole board
> keeps the cart speaking with one voice — no split where some dishes have
> authored prose and the rest fall back. `hand_over` prefers an item's
> `serve_line` over the counter style's gesture when a dish has one; here
> none does, so the spoken order through `serve_from_board_cart` prints the
> board gesture for every dish (raw cuts are never on the board). The retired attributes are
> stripped from the live objects by build 165
> (`scripts/builds/165_retire_counter_purchase_lines.py`, run once on the
> live DB after the merge, 2026-09-18). Full reasoning:
> `SHOP_SYSTEM_SPEC.md` §8 + the 2026-09-18 addendum.

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
  → player: `give corpse to butcher`  (handing it over is the only way in;
       dropping it on the cart does nothing — 📋 UNBUILT (not decided))
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
- **Transaction/payment:** the bartender pattern — `tokens` on the payer and a
  `register` on the cart; the grind emote states the payout as a plain number. The
  handler is modeled on `Bartender._fulfil_order` — which is no longer a
  typeclass method either: since #2350/#2378 service is keyed by `post_role` in
  `world/service.py`'s registry, bar service lives in `world/bar.py` and the
  cart's half in `world/shop/service.py`.
- **Hand-over:** the `give` command → the NPC's own `at_object_receive`
  (`typeclasses/llm_npc.py`) → `world.service.receive` → the post's `on_receive`
  detects the corpse. Both the buy and dish orders follow the post's shift:
  whoever is on duty at the cart (`world/service.py` `post_for`) buys and
  serves, and off shift the same body takes nothing. A cart nobody was ever
  assigned to is worked by whoever stands there; a cart whose keeper was
  deleted stays closed.
- **Voice + memory:** the LLM NPC brain (`LLMNpcMixin`) + a new `butcher`
  archetype. She remembers suppliers via the shipped dossier/valence layer
  (`NPC_MEMORY_AND_IDENTITY_SPEC` §8).

## 3 · The build (the Butcher only)

### 3.1 `Butcher` typeclass (`typeclasses/butcher.py`, sibling of `Bartender`/`Doctor`)

> **⚠️ SUPERSEDED (#2378) — the class is gone; the job stayed.** There is no
> `Butcher` typeclass, and no `Bartender`/`Shopkeeper`/`Doctor` either: every
> body is `LLMNpc` and what it can DO comes from the post it stands
> (`NPC_PLATFORM_SPEC` §3, law 5 — "no capability rides a typeclass").
> Everything below still happens; what changed is its address, so that whoever
> stands the block can work it:
>
> | §3.1 as written | where it lives now |
> |---|---|
> | `db.is_butcher_npc` (loop-guard marker) | gone — being the butcher IS standing a `butcher` post; the registry entry in `world/shop/service.py` (role, aliases, fallback, archetype, tools, `on_receive`) is the whole declaration |
> | `_find_block()` | `world.service.post_for()` — the post owns the cart |
> | `at_object_receive(obj, **kw)` | generic on `LLMNpc` (`typeclasses/llm_npc.py`) → `world.service.receive` → the registry's `on_receive` hook |
> | `_process_corpse(corpse, giver)` | `world.butchery.process_corpse` (reached via `world.butchery.on_receive`) |
> | `_name_aliases()` | still a method on `LLMNpc`, but it no longer HOLDS the words — it returns `world.service.aliases_for()`, the aliases of the post being stood, so a successor inherits the name for the job |
>
> **One line did not ship as written:** those aliases are `("butcher", "cook")`
> in the registry, not `["butcher", "meatpacker", "grinder"]` — "meatpacker" and
> "grinder" address nobody, and "cook" was added. Flagged, not reconciled:
> whether the registry list is the intended one is an owner call.
>
> `typeclasses/butcher.py` now holds only the `FoodCart` fixture, with
> `ButcherBlock` kept as a back-compat alias for objects created before the cart
> redesign.
- `LLMNpcMixin, Character`; `db.is_butcher_npc = True` (loop-guard marker);
  `db.llm_driven` opt-in (off by default, like the others).
- `_find_block()` → the `ButcherBlock` fixture (the register holder), mirroring
  `_find_bar`.
- `at_object_receive(obj, **kw)` → if `obj` is a `Corpse` **and** an accepted
  animal species → `_process_corpse(obj, giver)`. A human/synthetic/robot corpse
  is **refused** (not destroyed): she sets it on the floor and says one of:
  people → "I don't grind people. Ripper trade's not mine — take it elsewhere.";
  robot → "That's chrome and coolant, not meat."; any other species → "I don't
  know what that is, and I don't grind what I can't name." A corpse with no
  species recorded counts as human.
- `_name_aliases()` → `["butcher", "meatpacker", "grinder"]`.

### 3.2 `_process_corpse(corpse, giver)` — the deterministic core
1. **Species guard** — accept only non-sapient animal species (`rat`, plus future
   fauna); reject human / `synthetic_humanoid` / `robot` with a line, no
   destruction.
2. **Butcher it** — walk the species BUTCHERY TABLE (§3.4). Each entry maps an
   anatomical part → a named ingredient, and its **yield is gated by that part's
   condition** on this corpse:
   - a cut is **0** if its organ is missing, harvested (`removed_organs`), in a
     severed location (`severed_locations`), or at 0 HP (it's gone — shot off,
     already harvested);
   - chops scale by the trunk organs' average HP fraction (a shotgun-shredded
     trunk yields few or no chops); offal needs at least two of heart, liver and
     kidneys sound; haunch is one per sound hind leg;
   - `get_decay_factor()` scales EVERYTHING down (a rotting rat → little usable,
     mostly waste; a fully-rotted one → refused with a line).
     **As built (#1247), decay scales only the MEAT-MASS cuts.** In
     `world/butchery.py` `_butcher_yields`, `freshness = 1.0 - decay`
     multiplies exactly two products — rat chops and ground mystery meat — and
     nothing else; tail, haunch and offal are all-or-nothing per part (present
     and sound, or gone), gated by `severed_locations` / `removed_organs` /
     organ HP alone. Decay's other lever is the refusal gate, and it bites well
     before "fully-rotted": `BUTCHER_DECAY_REFUSAL = 0.6` on a curve where 1.0
     is one week, so ≈4 days in she says "That's past even my standards. Bury
     it." A corpse whose decay cannot be read is treated as fresh. How punishing rot should be across the rest of the table is §6's open
     yield-tuning question, still untuned.
3. **Cook the cuts** — the bought cuts go to the cart's `FoodCart.stock_cuts`,
   which cooks each one 1:1 into its dish and adds the dish to the cart's finite
   stock. No raw cut item is spawned. Only when she stands no post (`post` is
   None) are the raw cuts spawned loose where she stands. 2–4 named products
   from a clean carcass.
4. **Sweep the remainder into `ground mystery meat`** — the head, trim, damaged
   bits, and anything below cut grade → N units of mystery meat (the catch-all).
5. **Payout** = Σ(value of everything produced) — named cuts worth more than
   mystery meat — so **a clean, fresh, intact kill pays well and a mangled or
   rotting one pays scraps.** An empty or harvested carcass still grinds to at
   least one handful of mystery meat and pays 1 token, with the ordinary grind
   emote; no special line exists.
6. **Destroy** the corpse (rendered), **pay** (`giver.tokens += payout`; account
   against `block.db.register`), and **render** the grind gesture via
   `execute_cmd("emote …")`; the LLM voices it on the same beat.
7. **The till is finite.** Below 5 tokens (`BUTCHER_TILL_FLOOR`) she refuses
   the carcass: "Till's dry. Come back when it's been fed." Otherwise she buys,
   cheapest cut first, only what the till can pay for (`_affordable`), pays
   exactly that, and emotes that she "sets a few cuts aside, unpaid for — the
   till won't stretch to the whole animal today." The unpaid cuts are not
   stocked. If the giver is gone when the cleaver falls (1.5 s after the
   hand-over), nobody is paid and the till is not debited.

### 3.3 The butchery products (several named ingredients + mystery meat)
Every product is built **ingredient-grade** (per the §7 pathway). Its prototype
(`world/prototypes.py`) carries an `("eat", "delivery_method")` tag and its
nourishment as `drink_effects {"nutrition": N}`, so it is edible through
`world/consumables.py`. Its ingredient side (`role`, `flavour`, and an empty
`contributions` slot for §7 tier 3) lives in `world/food.py`
`FOOD_INGREDIENT_CATALOG`, not on the item, and the cart's recipes consume it
from there. The rat
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
| trunk / center cut | rat chops | 3 | trunk organ HP + decay |
| hindlegs | a rat haunch | 1–2 | `severed_locations` |
| heart/liver/kidney | rat offal | 1 | `removed_organs` + organ HP (≥2 of 4) |
| (everything else) | ground mystery meat | N | overall decay/condition |

`get_decay_factor()` multiplies the chops and mystery-meat rows only; at 0.6 or
more the carcass is refused. Extend per animal as fauna grows;
each new species ships its own table + its cuts' recipes.

> **As built (#1247) — decay multiplies two of these five rows: chops and
> mystery meat.** In `world/butchery.py` `_butcher_yields`, rat chops are
> `round(3 * trunk_frac * freshness)` and ground mystery meat is
> `max(1, round(3 * freshness))` — the `max` is a floor, so a carcass never
> grinds to literally nothing. Tail, haunch and offal carry no decay term at
> all. Two corrections to the chops row while you're here: its Base is **3**,
> not 2–3, and its "Gated by" is trunk wound severity **and** decay — the
> mystery-meat row already names decay, so chops is the only row whose "Gated
> by" cell omits a term it actually carries.

### 3.5 The `butcher` LLM archetype (`world/llm/prompt.py`)
- **Duties:** she runs the block — buys animal carcasses, breaks them down into
  cuts (tails, chops, haunches, offal) and grinds the rest to mystery meat. She
  prices by what a carcass yields and says so ("clean kill, that one — good
  chops"; "you dragged this halfway across the colony, it's mince now"). Grim,
  unbothered, transactional. She does **not** touch people or chrome (people-organs
  are the Ripper's trade; scrap isn't food).
- **Tools:** `look` and `remember` (base), plus `release` and `check_stock`, which
  reads the cart's live board and lists only dishes in stock
  (`world/shop/service.py` `_check_stock_board`). There is no `feel` tool. The
  buy/grind/pay transaction is **deterministic, not a tool** — exactly like the
  bartender's orders. Per the tool-reliability lesson, the few-shot
  **demonstrates** `remember` (tag a regular supplier), a thought that sours on
  a time-waster with no tool, and a restraint `none`.
- The fixture is `FoodCart` (`typeclasses/butcher.py`): a finite shop that is also
  4-seat seating; `ButcherBlock` survives only as an alias for objects created
  before the cart redesign.

## 4 · Design decisions (locked with the owner, 2026-07-20)

- **Payout = yield value** — the corpse is broken down via the §3.4 butchery
  table; named cuts (tail/chops/haunch/offal) are worth more than ground mystery
  meat, and each cut's yield is gated by that part's condition. So a clean, fresh,
  intact kill pays well; a mangled or rotting one pays scraps. **This makes how you
  kill it and how fast you deliver it matter** — combat quality + freshness feed the
  reward.
- **Products are ingredient-grade from day one** — every cut + the mystery meat
  is edible (an `("eat", "delivery_method")` tag and `drink_effects` nutrition on
  its prototype), and its ingredient side (role, flavour, an empty
  `contributions` slot) lives in `world/food.py` `FOOD_INGREDIENT_CATALOG`, so
  the food/menu economy (§7) snaps on without reworking the items. The cook/menu
  layer is not deferred: the cart cooks each cut 1:1 into its dish
  (`world/food.py` `cook_yields`) and sells only dishes.
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
- **Then (the food economy, §7):** the cuts circulate as tradable ingredients
  (player kitchens, grocery) — 📋 UNBUILT (no issue). The cook/menu layer is not
  part of this phase: the cart already cooks each cut into its dish
  (`world/food.py` `FOOD_RECIPES` / `cook_yields`) when a carcass is stocked.
- **Later (the capstone thread):** rep-scaled rates + a bonus ask ("bring me
  something bigger"); corpse-provenance flowing into the meat (a toxic-sump rat, or
  a drugged/chromed body → tainted `contributions` — §7 tier 3); the **Ripper**
  sibling gig (sapient organs — black-market, cyberware-grade, same corpse-in
  machinery, different clientele + legality).

## 6 · Open questions

- **Decay:** does a rotting rat pay less / get refused? (Lean: a decay modifier;
  refuse a fully-rotted carcass.) As built, not ruled: decay scales chops and
  mystery meat, and a carcass at decay 0.6 or more is refused
  (`world/butchery.py` `BUTCHER_DECAY_REFUSAL`).
- **Placement:** which room is the butcher's shop? (Content, owner's call.) As
  built, not ruled: the cart stands at the Toe of Hammett's Boot
  (`scripts/builds/083_ottilie_cart_advertises.py`).
- **Finite till:** does she pay from a seeded `register` that can run dry
  (economic pressure, a hook for the economy layer) or an infinite purse? (Lean:
  finite/seeded.) As built, not ruled: the register starts at 0
  (`FoodCart.at_object_creation`), dish sales credit it, and below 5 tokens
  (`BUTCHER_TILL_FLOOR`) she refuses carcasses.
- **Yield tuning:** the §3.4 base yields + the wound/decay curves — how punishing
  should a messy kill or a stale corpse be? (Tune in play.)
- **Cut identity:** are cuts fungible ("rat chops" ×N stack) or individually
  tracked? (Lean: fungible stackable items keyed by cut type — simpler, and the
  recipe engine matches by keyword.) As built, not ruled: at a cart no cut
  becomes an item; cuts are counted by type and cooked straight into dish
  counts in the cart's `db.item_inventory` (`FoodCart.stock_cuts`).

---

## 7 · Ingredient & menu pathway

The whole point of the butchery table (§3.4) is that its outputs are **real
ingredients**, not flavor props. The game's consumption model is one general
pipeline — `item → db.contributions {substance_id: doses} → delivery method
(eat/drink/inject) → effect` — and a bar "ingredient" is just an item with that
profile. The butcher's cuts join it in three tiers:

- **Tier 1 — consumable (built in the prototype).** Every cut + mystery meat
  carries an `("eat", "delivery_method")` tag and `drink_effects {"nutrition": 2}`
  on its prototype, so it's edible via `world/consumables.py`. Its
  `contributions` slot lives in `world/food.py` `FOOD_INGREDIENT_CATALOG` and is
  empty. No menu needed.
- **Tier 2 — ingredient → menu item.** A menu item is a recipe in `world/food.py`
  `FOOD_RECIPES`: the ingredients it consumes + a price. It is shaped like the
  bar's recipes but run by its own `cook_yields`; the bar's `project_mix` /
  `make_drink_from_recipe` are not used, and what an eater absorbs comes from the
  dish prototype's own `drink_effects`. There is no separate cook: the cart
  cooks when a carcass is stocked (`FoodCart.stock_cuts`) — rat tail → rat tail
  stew, rat chops → grilled rat chops, rat haunch → roast rat haunch, rat offal →
  butcher's breakfast, ground mystery meat → mystery skewer. Ordering rides the
  shared shelf matcher (`world/shop/service.py` `match_from_shelf`, using the
  bar's `ORDER_CUES` / `ORDER_FILLER`), scored against the dish prototypes' names
  and aliases. The food economy is butcher (cuts) → her cart (dishes) → patrons
  (eat).
- **Tier 3 — provenance in the meat (emergent, later).** Organs don't yet carry
  substance profiles, but the substance system exists. When they can, a corpse's
  origin flows into its cuts' `contributions`: a toxic-sump rat, or (via the Ripper)
  a drugged/chromed body, yields meat that's usually cheap protein but sometimes
  carries heavy-metal traces or a drug residue that *hits* when eaten. "Mystery
  meat" becomes a genuine gamble, and *where the corpse came from* matters.

**Build implication (already reflected in §3.3/§4):** the raw cuts are
ingredients the cart consumes: it cooks them into dishes and sells only the
dishes. Raw cuts circulating as tradable ingredients (player kitchens, grocery)
is 📋 UNBUILT (no issue). That is the
connective tissue between this gig and the bar/food side that already exists.
