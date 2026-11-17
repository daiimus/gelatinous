# Bars & Recipes Spec

> **Status:** 🚧 **PARTIAL** — v1 engine, menu and bartender shipped; §9 owner tooling not built. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 24 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - §9 lists `load <ingredients> into <bar>` as a shipped v1 verb. **No `load` command exists** — bottomless house stock (`derive_bar_stock`) replaced it.
> - §9 lists `clear <bar>`; the shipped verb is `clean` (alias `wipe`).
> - ~~`db.register` is a stub~~ — **wrong**: it *is* credited on every sale (`world/bar.py::_fulfil_from_board`). The real gap was that nothing drained it, so bar income accumulated with no way out. Closed 2026-08-03 by `till <bar>` (owner/staff only), mirroring the butcher's block, which was already a closed loop.

## 0.1 · Implementation status (2026-06-22)

**Shipped & live (PRs #639–#689):**
- `BarCounter` — an `@integrate` room fixture (folds into the room desc,
  `get:false`), a served-drink surface (counted `On the bar:` listing), its own
  `db.desc`, the menu (`₮` currency + operate-orange, column-aligned), and the
  `read menu on <bar>` verb. Wired end-to-end at the Hub & Howl and the Helix
  Lounge.
- **NPC bartender** — any NPC standing a counter's `bartender` (or `snailer`)
  post serves, through `world/bar.py::serve_from_board` (there is no bartender
  typeclass, #2378; Sully at the Hub & Howl was the first). It takes orders diegetically via the unified speech
  backbone (`say`/`to`/pose all route through `world/speech.py`; a pose that
  references the bartender counts as a directed order), makes the drink, takes
  payment as one wordless gesture (no system text), acknowledges thanks
  non-verbally, and renders by per-observer identity.
- **Crafting** — the interactive operate-style `use <bar>` EvMenu
  (`commands/bar_menu.py`): pick ingredients from the **bottomless house stock**
  (auto-derived from the menu + base pantry — no hauling), see the projected
  effects / composed flavour / recognized classic, then **pour** (with a
  build/stir/shake/muddle/blend prep step), **save/brand** as a free-text-named
  recipe (custom names like *Kyoto Negroni*; remembers the base cocktail), or
  **make a known recipe**. `clear` resets the load.
- **Two-layer ingredients** (§3) — substance contributions (doses → effects)
  *plus* a cocktail role + spirit type. 47-ingredient seeded catalog
  (`world/bar.py::INGREDIENT_CATALOG`)
  (the use-bar menu restocks them; the `@ingredient` testing stand-in was removed 2026-10-09, #3728).
- **Cocktail recognition** — a hidden 20-template library recognized at mix time
  by loose role-match (roles present, ratios/garnishes ignored), with
  spirit-swap spins (*Mezcal Negroni*) and same-skeleton families (rum
  sour→*Daiquiri*, whiskey→*Whiskey Sour*; gin *Negroni*/whiskey *Boulevardier*;
  tequila *Margarita*/brandy *Sidecar*) and spirit-less classics (*Mimosa*,
  *Spritz*). A single-ingredient pour is *a glass of `<ingredient>`*.
- **Flavour** — refined ingredient tasting-notes composed into a sentence, with
  authored taste prose for ~23 iconic named drinks; flavour-only drinks (soda,
  recyc) surface their taste too.
- **Consumption** — drinks ride the existing pipeline (sips, alcohol cap,
  tolerance, addiction); `prepare <drink>` is a menu-skip shortcut for a known
  pour; `chug` (drinks) / `devour` (food) consume every remaining use at once
  (medical items guarded out); `drink 2nd mug` ordinals fixed.
- **Free snacks** (§10) — bottomless `eat <snack> from <bar>`.
- **Role gating** — `BarCounter.is_bartender`: Builder+ staff, an explicit
  owner/staff entry, whoever is standing the counter's shift, or anyone present at
  an unbound counter (§8).
- **Pricing** — currency is the `₮` token (shop-consistent); Hub prices **zeroed
  for now** by request (re-pricing restores the spoken-price/payment path).

**Deferred (designed-for, not built — see §11):** supplier-NPC ingredient
economy (#6); `manage`/`deposit` owner tooling, in-game pricing and staff-list editing (§9); cyber-
brain recipe files / portability + trade (#11); faction-integrated ownership
(§8); the reusable crafting-station framework (§2.1); prep-method *mechanics*
(shipped as flavour-only); per-spin authored tastes.

## 0 · Purpose

Bars began as *rooms* — set dressing, no mechanics. This makes them
**functional social and economic hubs**:
places where consumables are mixed, served, bought, and consumed, run by NPCs or
players. It takes the consumption pipeline already built (substances, delivery
verbs, tolerance/addiction) and extends it *upward* into the colony's social and
economic life — the growth direction (functional hubs, emergent player cliques, a
favor/gear/rep economy rather than stat-leveling).

The connective tissue is **recipes**: a recipe is how raw **ingredients** become a
**drink** (a consumable), made and served at a **bar** (an object).

## 1 · Architecture

```
ingredients (real items, carry substance contributions)
        │  combined at a bar
        ▼
   mixing  →  effect profile = ADDITIVE SUM of contributions (capped)
        │  saved + named
        ▼
   recipe (repeatable, brandable, tradeable knowledge)
        │  produces
        ▼
   drink (a consumable item)  →  existing consumption pipeline
                                  (drink verb, alcohol cap, tolerance, addiction)
```

The **bar object** mediates all of it: serving, the staging surface, the money
register, and owner management.

### 1.1 · Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Bar is… | an **interactive furniture object** (a counter), not a room; verbs role-gated |
| 2 | Front-ends | **both** — NPC bartenders serve (economy) AND players mix at the bar (emergent); one recipe engine |
| 3 | Effects live on… | **ingredients**, not owner declaration |
| 4 | Effect derivation | **additive sum of ingredient contributions, capped** (reuses existing caps) |
| 5 | Recipe model | **free-mix → save as named recipe** (repeatable, brandable, tradeable) |
| 6 | Ingredients | **real items**; sourced from **supplier NPCs** in v1; deep sourcing later **extends the harvest command** |
| 7 | Output | a **consumable** that plugs into the existing consumption pipeline |
| 8 | Ownership | **owner + staff allowlist**; faction/favor integration stubbed |
| 9 | Balance lever | **ingredient scarcity**, not rules caps — you can only mix a super-stim if super-stim ingredients exist |
| 10 | Mixing UX | **menu-driven crafting station** — load ingredients (or a container of them) *into* the bar, then **`use`** it: a menu in the *style* of medical `operate`, but its own command to avoid confusion (could merge with `operate` later). The bar is the first **crafting station** and the segue into general crafting/workshop mechanics |
| 11 | Recipe storage | lives **at the bar** (its menu) or **memorized by a character**; a recipe is a **cyber-brain "file"** — same data family as the planned contacts/memory |
| 12 | Effect caps | **light per-effect safety-net**, tuned in play ("drunk is just a condition"); navigate later |
| 13 | Serving size | **one drink item with N consumption uses** (sips) — like a cigarette's drags; rides the existing multi-use/dose model, lines up with consumption exactly |
| 14 | NPC service | NPC bartenders are **fulfil-only**; bar-supply/restock economy **not modeled in v1**. Ordering is **diegetic** — address the bartender via `to`/pose (no `order`/`buy` verb); the NPC matches its menu and fulfils, **pay on order** (§7.1). |

> **What the game does against these decisions.** #6: there are no supplier
> NPCs, 📋 UNBUILT (no issue); a bar mixes from a bottomless stock
> (`world/bar.py::bar_stock`). #10: ingredients are added from that stock
> inside the `use <bar>` menu; loading carried ingredients, or a container of
> them, is 📋 UNBUILT (no issue). #14: an `order <thing>` verb exists (§7.1,
> #2342); there is still no `buy` verb at a bar.

## 2 · The bar object

`typeclasses/bar.py::BarCounter`, a `Seating` + `Item` fixture placed in a bar
room: it folds into the room description, cannot be picked up, seats ten
(`sit at bar`), and declares `db.post_role = "bartender"` so a post can be bound
to it. It is examinable and exposes role-gated verbs. The Hub &
Howl's "bent slab of starship hull" and the Helix Lounge's backlit bar are real
instances today; the Queen of Cups lobby still gets its own.

**State (plain `db` attributes):**

- `menu` — the board: a list of recipe entries, each carrying its own `price`
  (§6.1).
- The load is not an attribute: it is whatever ingredient items
  (`db.is_ingredient`) sit in the counter's contents; the menu's [a] adds them
  from stock. Loading a container of ingredients is 📋 UNBUILT (no issue).
- The surface is not an attribute either: served drinks and dishes are the rest
  of the counter's contents, for the patron to `get`.
- `register` — chit balance held by the bar.
- `owner` — character (or faction, later) who owns it.
- `staff` — allowlist of characters permitted to bartend/manage.
- `snacks` — free ambiance snacks offered (§10).
- `stock` — the ingredient keys the bar carries: `db.stock` if a builder set one,
  else the menu's ingredients plus the base pantry (`world/bar.py::bar_stock`).
  It is bottomless. Decision #6 (real ingredient items from suppliers) is
  📋 UNBUILT (no issue); the stock stands in for it.

**The four pillars** (from the reference `examine bar`, reframed around the bar
as a *crafting station*):

1. **Menu / craft** — `read menu`, and the prepare action: **`use <bar>`**
   (decision #10) — a menu in the style of medical surgery's `operate`, but its own
   command to avoid confusion. Add ingredients from the bar's stock, pick or save
   a recipe, mix.
2. **Load + serve surface** — ingredients are added from the bar's stock inside
   the `use <bar>` menu ([a]); `put` does not load a bar. Finished drinks and
   dishes rest on the counter for the patron to `get`. `clean <bar>` (alias
   `wipe`) clears what was left behind.
3. **Register** — `deposit $`; the bar is an economic actor (§7).
4. **Manage** — owner config: menu, prices, staff, recipe management (§8).

> **Pillar status, 2026-09-11.** Pillar 1 and the surface half of pillar 2 are
> live. The tidy verb is **`clean`** (alias `wipe`), not `clear` — see the header
> correction — and it sweeps plated dishes too, which are marked by tags rather
> than `db.is_drink` (`typeclasses/bar.py::CmdBarClear`, #2459). Pillar 3 is half
> built: the register is credited on a sale and drained by **`till <bar>`**
> (`typeclasses/bar.py::CmdBarTill`, #1515); there is **no `deposit` verb** —
> payment is swept automatically on the serve path with no bartender gesture.
> Pillar 4 (`manage`) is unbuilt: no command with that key exists anywhere.
> Recipe save/name/brand happens inside the `use <bar>` EvMenu instead — but
> **prices** are not editable in play at all: `_save_recipe` writes
> `"price": 0` and only a build script can change it (see §7). Staff-list
> editing has no in-game door either.

### 2.1 · The bar is a crafting station (the workshop on-ramp)

Per decision #10, the bar is the **first crafting station** — and where this
design *diverges from medical and segues into general crafting/workshop
mechanics*. The shape is reusable:

```
load a station with input items (or a container of them)
        │
   use <station>       (menu UX in the style of medical `operate`)
        │  apply a recipe
        ▼
   output item(s)  +  consume the inputs
```

For a bar the station is the counter, the inputs are ingredients, the recipe is a
drink, the output is a consumable. The same pattern later powers other stations
(a chem bench, a fabricator, a galley). Build the bar so the **load → use →
recipe → output** loop is a recognisable, extractable pattern, not bar-specific
plumbing. The `BarCounter` is concrete; the crafting-station behaviour underneath
it is the seam the workshop pass builds on (§11).

## 3 · Ingredients

An ingredient is an ordinary item carrying a **substance contribution profile** —
the effect magnitudes it adds to a mix, keyed to the existing substance effect
vocabulary (`world/substances/registry.py`).

```
catalog ingredient, e.g. "grain_mash" (world/bar.py::INGREDIENT_CATALOG):
  db.is_ingredient = True
  db.contributions = {"alcohol": 1}            # effect-type → magnitude
  db.flavour = "raw, paint-stripping grain"     # for derived drink descriptions
  db.consumed_per_use = 1                        # units a mix consumes
  db.role = "spirit"                             # cocktail role
  db.spirit = "grain mash"                       # spirit type (role == spirit)
```

- **Effect types** reuse the substance registry (alcohol, stim, pain_relief,
  sedation, …) so derived drinks need no new effect engine.
- **A "garnish"** is just an ingredient with empty/flavour-only contributions —
  it changes the drink's name/description, not its punch.
- **Sourcing:** 📋 UNBUILT (no issue) — ingredients are to be bought from
  **supplier NPC vendors** — a chem supplier, a food/produce vendor, an
  Earth-imports dealer. Real items, real cost; their price is the economic floor
  under a drink. Until then a bar's bottomless stock stands in (§2).
- **Sourcing (later):** harvesting/fishing/synthesis. Per decision #6 these are
  *the same items* acquired via an **extended `harvest` command** (the medical
  harvest verb already exists) — ice from the mines, channel-fish, synth-vats.
  No migration: v1 ingredients already are real items.

## 4 · Mixing & effect derivation

**The flow (decision #10):** open `use <bar>` — a menu in the style of medical
surgery's `operate` — add ingredients from the bar's stock ([a]), then pour the
loaded inputs into a drink. The drink's effect profile is the **additive sum of
the inputs' contributions, then capped**.

```
mix( [ROTGUT_BASE ×1, STIM_ROOT ×1, CITRUS_GARNISH ×1] )
  raw  = {"alcohol": 3} + {"stim": 2} + {}        # additive
  drink.effects = cap(raw)                          # reuse existing caps
                = {"alcohol": 3, "stim": 2}
  drink.flavour = compose(flavours)                 # for the description
```

- **Caps** reuse what consumption already enforces (the alcohol cap), plus a
  **light per-effect safety-net cap** (decision #12) so stacking one ingredient
  can't overshoot. A mix can't exceed them — five rotguts don't make a
  five-strength drink. Tuned in play ("drunk is just a condition"); effects
  manifest as conditions, so the cap is really a condition-severity ceiling.
- **Balance is emergent (decision #9):** the only way to a potent drink is potent
  ingredients, and those are gated by sourcing cost/scarcity — not by a recipe
  rule. This is what makes free authoring (decision #5) safe.
- **Method is out of scope for v1** (no distill/filter/dilute transforms) — it's
  a clean later layer (§11) that would multiply/shift contributions before the
  cap. v1 mixing is "combine."

## 5 · Recipes

Mixing is freeform; a **recipe is a saved, named mix** (decision #5).

- **Free-mix:** anyone behind a bar can combine ingredients ad-hoc and get a
  drink. Experimentation *is* discovery — you learn what a combination does by
  trying it.
- **Save:** a successful mix can be saved as a named recipe — `inputs (ingredient
  types × qty) → name + owner description`. The bar (or the character) now knows
  it: it can be re-made on demand, put on the **menu**, priced, and **branded**
  (the Hub & Howl's "Reactor Wash" is mechanically rotgut+stim, but named and
  described its own way — emergent identity for near-zero engineering).
- **Recipe-as-knowledge (decision #11):** a saved recipe lives **at the bar** (in
  its menu) or **memorized by a character** — it is a **cyber-brain "file,"** the
  same data family as the planned contacts and memory systems. Recipes are
  therefore tradeable assets: sold, taught, copied between brains, stolen, kept
  secret — an emergent economy atop the ingredient economy. (Today a saved
  recipe lives only on the bar's menu. A character memorizing a recipe, and
  trading it, is 📋 UNBUILT (no issue) — it rides the cyber-brain-files pass, §12.)

## 6 · The output consumable

A made drink is an ordinary **consumable item** carrying the derived effect
profile mapped onto the existing consumption model:

- the `drink` delivery tag (category `delivery_method`) plus `db.is_drink` (the
  `drink` verb path).
- substance effects = the capped contribution profile → rides `apply_substance`,
  so **alcohol cap, tolerance, and addiction already apply** with zero new code.
- name + description = the recipe's brand (owner-authored) over the mechanical
  profile.
- **uses** = the drink is **one item with N consumption uses** (sips), exactly
  like a cigarette's drags (decision #13). Each `drink` spends one use and delivers
  a dose until the glass is empty — riding the existing multi-use bookkeeping: the
  drink carries `db.uses_left` (sips) and `db.drink_effects` (doses applied per sip
  through `apply_substance`), so it lines up with the consumption model exactly.

This is the payoff of decision #7: recipes don't invent an effect system; they
compose existing substances into a consumable the pipeline already understands.

### 6.1 · Drink definition (data model)

A drink/recipe record. The *structure* — appearance, taste, a per-sip line, a
finishing line, first/third-person craft narration, a price, an ingredient list —
is a sound shape for any consumable craft; the field names and **all content are
ours** (no external names or prose reproduced). Messages use our pose/emote token
format (`world/emote.py`).

| Field | Purpose |
|---|---|
| `name` | the drink's name (colony-authored, e.g. a house special) |
| `desc` | appearance when examined |
| `price` | cost in chits — seeds §7 pricing |
| `ingredients` | the input ingredient types (a spirit base, a mixer, a garnish…) |
| `effects` | **derived (our layer):** additive sum of the ingredients' substance contributions, capped (§4) |
| `taste` | the flavour, surfaced on consumption — gustatory/olfactory |
| `sip_msg` | per-sip line — **one consumption use** (decision #13) |
| `finish_msg` | the final sip, emptying the vessel |
| `craft_msg` / `ocraft_msg` | first- / third-person **craft narration** for `use <bar>` (bartender / onlookers), authored per drink |

Notes:
- **Mechanics are ours.** Ingredients carry substance contributions (§3); the
  drink's `effects` are their capped sum (§4). A garnish is a flavour-only
  ingredient — empty contributions, real presence in the prose.
- **Multi-use:** `sip_msg` = one use, `finish_msg` = the last sip (decision #13).
- **`craft_msg` / `ocraft_msg`** are the authored flavour of `use <bar>` (§2, §4),
  per drink.
- **Field names, checked 2026-09-11.** None of the four message fields in the
  table above exist in the code — `sip_msg`, `finish_msg`, `craft_msg` and
  `ocraft_msg` return nothing repo-wide. A live menu entry carries
  `name` / `order_keywords` / `ingredients` / `price` / `sips` / `effects` /
  `desc` / `taste` / `craft` (see `HUB_AND_HOWL_MENU`), and the drink itself
  carries `db.uses_left` and `db.drink_taste`. The craft narration collapsed to a
  **single `craft` string**, third-person only, because it is spoken through
  `emote` — which renders per-observer identity and derives the first-person view
  itself, so an authored `craft_msg`/`ocraft_msg` pair would have had nothing to
  do. `sips` survives as a count; the per-sip and last-sip *lines* were never
  authored per drink. The shape in the table is still the right shape for a
  future authored pass — it just is not what ships.
- **Theming is a content call:** polished cocktails suit an upscale venue; the Hub
  & Howl's menu is scuzzier. All drink names, descriptions, and prose are authored
  fresh for the colony — nothing lifted.

## 7 · Economy

- **Register:** the bar holds chits. Serving a menu drink for a price moves chits
  patron → register; the owner withdraws profit via `manage`. `deposit $` covers
  the bartender ringing up a sale.
  > **Amended 2026-09-11.** Withdrawal is **`till <bar>`** (`till <bar> = <amount>`
  > for a partial take), gated on `BarCounter.is_bartender` — not `manage`, which
  > was never built. There is no `deposit` verb either: the serve path debits the
  > patron and credits the counter itself, with no bartender gesture in between.
  >
  > A sale debits the patron, writes a `drink` record to the coin audit with the
  > counter as the other party, and credits the counter's `register` if it keeps
  > one (`world/bar.py::_fulfil_from_board`). An audit failure never blocks the
  > credit.
- **Pricing:** per-bar, per-recipe (set in `manage`). Floor = ingredient cost;
  margin = the owner's call.
  > **Not reachable from play, checked 2026-09-11.** The *data* shape held — a
  > price is per-bar and per-recipe, carried on the menu entry and read by the
  > serve path — but there is **no tool that sets one**. `manage` was never
  > built, and the `use <bar>` EvMenu's save step writes `"price": 0` into every
  > recipe it creates (`commands/bar_menu.py::_save_recipe`), with no prompt and
  > no later edit path; a repo-wide search finds no other assignment to a
  > recipe's `price` outside tests. So a player-authored house special is free
  > forever, and re-pricing a board — including the Hub & Howl's zeroed menu
  > (§0.1) — means editing a build script. This is the gap that makes the
  > "margin = the owner's call" half of the sentence aspirational rather than
  > false.
- **Player-run bars become real economic nodes** — the hook into the favor/gear/
  rep loop. v1 keeps money handling clean and simple; the faction/favor layer
  (§8, §11) builds on it later.

### 7.1 · Ordering — by talking to the bartender

A patron orders the way they would in life: by **addressing the bartender** —
directed speech (`to <bartender> …`, which rides `say` aimed at one person) or a
pose. This unifies player and NPC bartenders — both simply respond to a spoken
request.

> **Amended 2026-08-28 (#2342).** This section used to open "There is **no
> `order`/`buy` verb**". The `order` half of that decision has been reversed,
> for a reason the original couldn't have seen: **you cannot address someone
> whose name you don't know.** `to` takes a *single-token* target and identity
> gates the name, so a stranger in a crowded bar resolves `Nonna` to nothing
> and `woman` to five people at once. `menu` showed you a board you had no way
> to act on. Souls hit the same wall permanently — they never learn names, so
> no NPC could order anything from anyone.
>
> **`order <thing>` is a targeting affordance, not a second economy path.** It
> resolves the tender for you and speaks the order at them through the same
> `broadcast_speech` backbone: the room hears it, perception applies, and
> fulfilment runs the identical serve path. The principle above is intact —
> ordering is still *talking to the bartender*. What changed is that you no
> longer have to have been introduced first.
>
> The `buy` half still stands: there is no `buy` verb at a bar. A counter is
> **served**, a shelf is **sold from**, and a venue has exactly one of them.

- **NPC bartender** — listens for directed requests aimed at it, matches the
  request against its **menu** (v1: a drink-name / keyword match), and fulfils:
  makes the drink via the shared recipe→drink engine, sets it on the bar, and
  takes **payment on order** (chits → register). The patron `get`s the drink.
- **Player bartender** — identical social flow: hears the request, `use`s the bar
  to make it (the reference's RP ordering).
- **Fulfilment without supply (decision #14)** — the NPC isn't running a modeled
  ingredient inventory in v1, so it fulfils from a known menu recipe and conjures
  the drink; the *same* recipe→drink engine players use, just without consuming
  real ingredient items yet. Real supply is a later pass.

**Dependency:** directed speech — the **`to` command** (rides `say`, targeted at an
individual; e.g. `Bob [to William]: …`). NPC intent-parsing beyond a menu-name
match is a tuning concern, not a v1 blocker.

### 7.2 · Plated dishes — a board can serve food (#2342)

A menu entry naming a **`proto`** is *plated* rather than mixed: the real
prototype is spawned onto the counter, instead of a drink being composed from
ingredients. Same gesture, same surface, same payment — only the thing that
lands is different.

```python
{"name": "grilled snail skewer", "order_keywords": ("skewer", "escargot"),
 "proto": "snail_skewer", "price": 3, "craft": "lays six on the grill-pan…"}
```

> **Note 2026-09-18 (#3413) — `craft` here, `serve_line` at a shop counter.**
> A plated dish served from a BAR board uses the menu entry's `craft` string
> (`world/bar.py`); it never reaches `world/shop/service.py hand_over`, so an
> item's `serve_line` has no effect on this path. The same prototype sold
> over a SHOP counter (`buy`, or a spoken order at a shelf/board post) does
> reach `hand_over`, which prefers the item's `serve_line` over the counter
> style's gesture. The **snailery is served entirely by the BAR path**:
> build 137 (#2342) turned counter #8119 into a `BarCounter` with no
> prototype inventory, so `snail_skewer`, `snail_jar` and the kuro are
> plated with `SNAILERY_MENU`'s `craft` prose and never reach `hand_over` at
> all. Those dishes carry no `serve_line`, and should not: `serve_line` is a
> shop-counter mechanism and does nothing here — authored on a dish only a
> bar serves, it is dead prose. See `SHOP_SYSTEM_SPEC.md` §8.

This is what makes a **restaurant** expressible. Before it, a bar could pour but
not feed: the serve path always ended in `make_drink_from_recipe`, and the other
half — free `snacks` (§10) — are bottomless, priced at nothing and never enter
inventory. A plated dish inherits everything the item already carries (nutrition,
bites, taste, decay), so a kitchen serves exactly what a shelf sold.

**The three venue models, and the rule.** A venue answers to *one* of these:

| model | fixture | how you're served |
|---|---|---|
| **served** | `BarCounter` with a `menu` | `order <thing>` → tender plates it onto the counter → you `get` it |
| **sold** | `ShopContainer` with `prototype_inventory` | `buy <thing> from <counter>` → pressed into your hand |
| **grazed** | anything with nutritious `snacks` | `eat <thing> from <fixture>` — free, in place, never inventory |

**Give a venue exactly one.** The Snailery carried a shelf *and* was described as
a restaurant, and that split is what produced the bug: two doors at one counter,
only one of which anyone maintained.

**Souls use the same doors.** The planner dispatches on **what the venue is**,
never on what the soul is — see `world/souls/actions.py::_feed_at` /
`_indulge_at`. This was the actual defect behind #2342: the door was chosen by
the soul's *species profile*, so only a `recluse` knew how to be served and only
a shelf would sell to anybody. Sixteen colonists could stand in a restaurant and
starve. A venue that wants NPC custom needs three things — a board, somebody
working it, and the `("advertiser", "souls")` **tag** (an indexed tag, never the
bare attribute).

**The keeper eats from their own board, on the house.** Owner, 2026-11-13
(#3802): "A and their meal should as a result be complimentary." Option A was
the keeper making the meal themselves with `prepare`. A soul working a counter
that serves food prepares the cheapest dish on its board, picks it up and eats
it, unpaid (`world/souls/actions.py::_feed_at`). This covers food only: a
keeper is not served a drink at their own bar.

## 8 · Ownership & staffing

- `owner` — who owns the bar; full rights (manage, set menu/prices, withdraw,
  edit staff).
- `staff` — an allowlist of characters permitted to bartend (`load`/`use`,
  serve, `deposit`) but not manage.
- **Role resolution:** a verb checks the actor against owner/staff/neither →
  owner / bartender / patron tier.
  > **Superseded by the job system, 2026-09-11 (#2597, #2921).** Two of the three
  > verbs named above never shipped (`load`, `deposit`), and the three-tier
  > resolution did not survive: `BarCounter.is_bartender` is a **single boolean**
  > — there is no owner tier distinct from a bartender tier, so "permitted to
  > bartend but not manage" has nothing to express it with. What it answers, in
  > code order: Builder+ staff → an explicit `owner`/`staff` entry → **whoever is
  > standing this counter's shift**, via `world/souls/posts.keeper_on_duty` →
  > and, only for an unbound counter (see *Bound means ever assigned* below),
  > whoever is present. Its docstring records why: no bar in the colony has ever had `owner`
  > set, so the v1 owner-attribute design was never the operative rule anywhere,
  > and the post became the answer instead. The §8 seam did snap on — it just
  > snapped onto posts rather than factions.
  >
  > **Bound means ever assigned (#3573, 2026-09-24).** "Unbound" -- the vending
  > tier -- is now one function, `world/souls/posts.is_bound`, asked by
  > `is_bartender`, `ShopContainer.purchase_item`, the souls planner's
  > `_counter_open`, `world/service.post_for` and `world/bar.tender_at`
  > (five inline copies before, which had drifted). A counter is bound if it
  > has shift slots, or if a keeper, owner or staff entry was **ever** set,
  > **even if that character has since been deleted**: Evennia reads a deleted
  > reference back as `None`, and every copy took that for "never assigned", so
  > a counter whose person was gone fell to the vending tier and anyone present
  > could empty its till. A bound counter with nobody valid present reads
  > closed, the state a vacant shift already produces. Dead owner and staff
  > entries never match anyone.
  >
  > **`owner`/`staff` are legacy, hardened but not extended.** Future player
  > owners and staff are designed separately in #3648: ownership keyed by
  > sleeve uid (as lockers are), shared across bars, shops and carts, with
  > player staff as post slots. Retire these two fields in that change.
- **Faction/favor is a stubbed seam (decision #8):** v1 ownership is a plain
  owner attribute + allowlist. The later pass lets factions own bars, ties staff
  permissions to the favor system, and may lean on the parked **TRUST_AND_CONSENT**
  work (who may act at *your* bar). Design v1 so that seam snaps on — don't
  hardcode "owner is a single character" everywhere.

## 9 · Command reference (v1)

Mapped from the reference `examine bar`, gelatinous-flavoured. `<bar>` is the
counter object.

**Patron**
- `read menu on <bar>` — what's servable, with prices.
- `order <thing>` — ask whoever is working the counter (§7.1). Directed speech
  with the targeting resolved, for when you don't know the tender's name — which
  is most of the time, and always for an NPC.
- *or address the bartender yourself* — `to <bartender> …` or a pose. Identical
  path; ordering is social.
- `eat <snack> from <bar>` — free snacks (§10).
- `get <drink> from <bar>` — take what was served onto the counter.

**Bartender** (whoever `BarCounter.is_bartender` admits — see §8)
- Ingredients are added from the bar's stock inside `use <bar>` ([a]). A `load`
  verb for carried ingredients, or a container of them, is 📋 UNBUILT (no issue);
  `put … in <bar>` answers that the bar can't hold it.
- `use <bar>` — opens the crafting menu (in the style of medical `operate`, but
  its own command): mix the loaded inputs free-form or via a known recipe,
  optionally save/brand the result; the drink lands on the bar for the patron.
- `clean <bar>` (alias `wipe`) — clear abandoned loads, drinks and dishes off the bar.
- `deposit <$> in <bar>` — ring a sale into the register.

**Owner**
- `manage <bar>` — menu (add/remove recipes), pricing, staff allowlist, register
  withdrawal, save/rename/brand recipes.

> **Built / unbuilt, 2026-09-11** (the header correction covers `load` and
> `clear`; this is the rest of the list). **Shipped but missing from the table
> above:** `prepare <drink>` — a menu-skip pour of a known recipe straight onto
> the counter (`typeclasses/bar.py::CmdBarPrepare`); and `till <bar>` /
> `till <bar> = <amount>` — the register drain, gated through `is_bartender`
> (`typeclasses/bar.py::CmdBarTill`, #1515). **Still unbuilt:** `deposit` and
> `manage` — no command with either key exists in the repo. Of `manage`'s five
> promised jobs, one shipped elsewhere (register withdrawal, as `till`), two live
> in the `use <bar>` EvMenu (add a recipe, save/rename/brand it), and two have no
> in-game door at all: the **staff allowlist**, and **pricing** — `_save_recipe`
> writes `"price": 0` and nothing in play can change it (see §7).

(Both player and NPC bartenders work the same way — the patron *says* what they
want (`order <thing>`, `to <bartender>` or a pose) and the bartender makes it: a
player opens `use <bar>` and adds ingredients from stock, an NPC parses and
fulfils from its menu. There is no `buy` verb at a bar. `order <thing>` is
directed speech with the target found for you, per §7.1.)

## 10 · Free snacks

Pure ambiance, near-zero cost: a bar offers a fixed snack list (`db.snacks`),
`eat <snack> from <bar>` eats it in place: bottomless, free, and nothing enters
inventory; any effects a snack carries are applied through `apply_substance`.
Colony flavour instead of peanuts/pretzels/pickles: every counter starts with
`DEFAULT_BAR_SNACKS` (**brine pods**, **synth-jerky**, **ration crackers**), and
any object with `db.snacks` can serve them (#2074).

## 11 · Build phases

**v1 — ✅ SHIPPED (2026-06-21/22):**
- ✅ `BarCounter` object; pillars 1–3 (menu/craft, surface, register via `till`);
  pillar 4 `manage` 📋 UNBUILT (no issue). Role gating is `BarCounter.is_bartender` (§8).
- ✅ Ingredients as real items with contribution profiles (+ cocktail identity).
      Supplier-NPC vendors **deferred** — a seeded catalog stands in for now;
      the `@ingredient` spawn stand-in was removed 2026-10-09, #3728.
- ✅ Free-mix → additive-capped drinks → consumption pipeline.
- ✅ Save/name/brand recipes; menu. Pricing is carried on each menu entry (the
      Hub & Howl board is zeroed by request), but no in-game command sets a
      price (§7). The register is credited on each sale and drained by `till`.
- ✅ Two reference bars wired end-to-end (the Hub & Howl, and the Helix Lounge —
      the latter a fully-stocked free-mix shakedown with NPC bartender Sable Vane).

**Shipped beyond the original v1 line:**
- ✅ Hidden classic-cocktail recognition + spirit-swap spins (loose role-match).
- ✅ Prep methods (build/stir/shake/muddle/blend) — flavour + suggestion only.
- ✅ Bottomless house stock (pick-from-stock in the menu, no hauling).
- ✅ `prepare <drink>` menu-skip shortcut; `chug`/`devour` whole-item consume.
- ✅ Unified `say`/`to`/pose speech backbone (NPC reacts to any of them).

**Deferred seams (designed-for, not built):**
- **General crafting / workshop mechanics** — extract the *load → use →
  recipe → output* station pattern (§2.1) into a reusable crafting framework, so
  the bar is the first of many stations (chem bench, fabricator, galley). The bar
  build should make that pattern recognisable, not bar-specific.
- **Deep ingredient sourcing** — extend `harvest` for ice/fish/synth (decision #6).
- **Prep methods / stations** — distill/filter/dilute transforms before the cap (§4).
- **Cyber-brain files** — recipes join contacts/memory as one file/data layer
  (decision #11); richer copy/teach/sell/steal flows ride that pass.
- **Faction-integrated ownership** — factions own bars, favor-gated staff,
  trust/consent for who-acts-at-your-bar (§8).
- **Non-drink consumables from ingredients** — mixing food or drugs from
  ingredients. A board already serves ready-made dishes (§7.2).

## 12 · Integration points

- **Consumption pipeline** — `world/consumables.py`, `apply_substance`, the
  `drink`/`eat` verbs; the substances registry (`world/substances/registry.py`)
  supplies effect types and caps. Recipes produce items it already handles.
- **Harvest command** — the future sourcing extension point (decision #6).
- **Menu/runner framework** — the crafting UX is built in the *style* of the
  medical `operate` menu (and may share its runner internally) but exposed as
  **`use`** to keep the two distinct (decision #10); the bar is where that pattern
  generalises beyond surgery into crafting stations (§2.1).
- **Cyber-brain files (planned)** — recipes are the same data family as the
  planned contacts/memory "files" (decision #11); built minimally here, unified
  there.
- **Economy / chits** — the register; vendors for ingredient supply.
- **Crowd system** — bars are already crowd hotspots (the Hub & Howl is base 3);
  a busy bar reads packed, which the recipe/serve loop now gives a reason for.
- **Reference venues** — Hub & Howl (hull-slab bar), Helix Lounge, Queen of Cups
  lobby.

## 13 · Open questions

All core decisions are **resolved** (decisions #1–14). The v1 build questions
are settled; what remains is the deferred-seam work (§11) and tuning:

1. ✅ **`to` command** (directed say) — built, and the whole `say`/`to`/pose path
   is unified through `world/speech.py`; the NPC reacts to any of them.
2. ✅ **NPC menu-request parsing** — keyword match against the menu (`match_recipe`).
   *(2026-09-11: `match_recipe` still does the matching, but a bare keyword match
   turned out not to be settleable as a v1 tuning concern — it served drinks off
   ordinary conversation. "the old man sent me" poured an Old Fashioned and "I'll
   take your word for it" poured `the last word` (#2689), and an addressed
   question bought a drink and suppressed the reply (#2779). Parsing is
   `resolve_order`: it finds the drink first with `resolve_drink` (the board,
   then `mix_offmenu` from the bar's stock), then tests intent. An addressed
   line with an order cue (`ORDER_CUES`) passes if what is left after the cue
   is only the drink and filler (`_without_cues`, `_bare_order`); one without a
   cue must have no question mark and be only the drink and filler. An
   overheard line must have no question mark and pass the same
   drink-and-filler test. Still ✅, but the
   ✅ covers three layers, not one.)*
3. ✅ **Ingredient contributions** — assigned across the seeded catalog (§3).
4. **Effect/balance tuning** — `MIX_EFFECT_CAP` and per-sip dose scaling (esp.
   `chug` stacking) are first-pass; "drunk is just a condition," tune in play.
5. **Owner tooling** — `manage` (menu, pricing, staff allowlist) and `deposit`
   are 📋 UNBUILT (no issue) (§9). `clean` and `till` exist, and the serve path
   credits the register itself.
6. **Supplier economy** — the ingredient vendor loop (#6) is the biggest deferred
   piece gating "real" scarcity-driven balance.
