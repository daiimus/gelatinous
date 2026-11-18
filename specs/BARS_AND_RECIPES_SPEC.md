# Bars & Recipes Spec

## 0 · Purpose

A bar is a **functional social and economic hub**: a place where consumables
are mixed, served, bought and consumed, run by NPCs or players. It takes the
consumption pipeline (substances, delivery verbs, tolerance/addiction) and
extends it *upward* into the colony's social and economic life — the growth
direction (functional hubs, emergent player cliques, a favor/gear/rep economy
rather than stat-leveling).

The connective tissue is **recipes**: a recipe is how raw **ingredients** become
a **drink** (a consumable), made and served at a **bar** (an object).

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
register, and management.

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

**What the game does against these decisions.**

- #6: there are no supplier NPCs, 📋 UNBUILT (no issue). A bar mixes from a
  bottomless stock (`world/bar.py::bar_stock`, §2).
- #8: the owner/staff allowlist survives as a legacy path; who may work a
  counter is decided by `BarCounter.is_bartender` and the job system (§8).
- #10: ingredients are added from that stock inside the `use <bar>` menu.
  Loading carried ingredients, or a container of them, is 📋 UNBUILT (no issue).
- #11: a saved recipe lives only on the bar's menu. A character memorizing a
  recipe, and trading it, is 📋 UNBUILT (no issue) (§5).
- #14: decision #14 recorded "no `order`/`buy` verb". The `order` half was
  reversed on 2026-08-28 (#2342): an `order <thing>` verb exists (§7.1). There
  is still no `buy` verb at a bar.

## 2 · The bar object

`typeclasses/bar.py::BarCounter`, a `Seating` + `Item` fixture placed in a bar
room. It is an `@integrate` fixture that folds into the room description; it
cannot be picked up (`get:false`); it has its own `db.desc`; it seats ten
(`sit at bar`); and it declares `db.post_role = "bartender"` so a post can be
bound to it. It is examinable and exposes role-gated verbs (`BarCmdSet`).

Reference instances: the Hub & Howl's "bent slab of starship hull" and the
Helix Lounge's backlit bar (a fully-stocked free-mix shakedown, with NPC
bartender Sable Vane). Both are wired end-to-end. The Queen of Cups lobby still
gets its own.

**State (plain `db` attributes):**

- `menu` — the board: a list of recipe entries, each carrying its own `price`
  (§6.1).
- The load is not an attribute: it is whatever ingredient items
  (`db.is_ingredient`) sit in the counter's contents; the menu's [a] adds them
  from stock. Loading a container of ingredients is 📋 UNBUILT (no issue).
- The surface is not an attribute either: served drinks and dishes are the rest
  of the counter's contents, for the patron to `get`. The counter lists them as
  a counted `On the bar:` listing.
- `register` — chit balance held by the bar. It is credited on every sale
  (§7) and drained by `till <bar>`.
- `owner` — character (or faction, later) who owns it. Legacy (§8).
- `staff` — allowlist of characters permitted to bartend/manage. Legacy (§8).
- `snacks` — free ambiance snacks offered (§10).
- `stock` — the ingredient keys the bar carries: `db.stock` if a builder set
  one, else the menu's ingredients plus the base pantry
  (`world/bar.py::bar_stock`, which calls `derive_bar_stock`; the base pantry
  is `BASE_BAR_PANTRY`). It is bottomless: no hauling. Decision #6 (real
  ingredient items from suppliers) is 📋 UNBUILT (no issue); the stock stands
  in for it.

**The four pillars** (from the reference `examine bar`, reframed around the bar
as a *crafting station*):

1. **Menu / craft** — `read menu`, and the prepare action: **`use <bar>`**
   (decision #10) — a menu in the style of medical surgery's `operate`, but its
   own command to avoid confusion. Add ingredients from the bar's stock, pick or
   save a recipe, mix (§4, §5).
2. **Load + serve surface** — ingredients are added from the bar's stock inside
   the `use <bar>` menu ([a]); `put` does not load a bar. Finished drinks and
   dishes rest on the counter for the patron to `get`. `clean <bar>` (alias
   `wipe`) clears what was left behind, plated dishes included; dishes are
   recognised by tags, not by `db.is_drink` (`typeclasses/bar.py::CmdBarClear`,
   #2459).
3. **Register** — the bar is an economic actor (§7). The serve path credits the
   register on a sale; `till <bar>` drains it (`typeclasses/bar.py::CmdBarTill`,
   #1515). A `deposit` verb is 📋 UNBUILT (no issue).
4. **Manage** — owner config: menu, prices, staff, recipe management (§8).
   `manage` is 📋 UNBUILT (no issue). Recipe save/name/brand happens inside the
   `use <bar>` menu. **Prices** cannot be edited in play (§7). Staff-list editing
   has no in-game door either.

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

For a bar the station is the counter, the inputs are ingredients, the recipe is
a drink, the output is a consumable. The same pattern later powers other
stations (a chem bench, a fabricator, a galley). Build the bar so the **load →
use → recipe → output** loop is a recognisable, extractable pattern, not
bar-specific plumbing. The `BarCounter` is concrete; the crafting-station
behaviour underneath it is the seam the workshop pass builds on (§14). The
reusable crafting-station framework itself is not built (§14).

## 3 · Ingredients

An ingredient is an ordinary item carrying a **substance contribution profile**
— the effect magnitudes it adds to a mix, keyed to the existing substance
effect vocabulary (`world/substances/registry.py`) — **plus** a cocktail role
and, for a spirit, a spirit type. The seeded catalog is
`world/bar.py::INGREDIENT_CATALOG` (47 ingredients, each with its
contributions assigned); `make_ingredient` creates one. The `use <bar>` menu
restocks them from the bar's stock. There is no `@ingredient` spawn command
(#3728).

The data shape of a catalog ingredient:

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
  Earth-imports dealer. Real items, real cost; their price is the economic
  floor under a drink. Until then a bar's bottomless stock stands in (§2).
- **Sourcing (later):** harvesting/fishing/synthesis. Per decision #6 these are
  *the same items* acquired via an **extended `harvest` command** (the medical
  harvest verb already exists) — ice from the mines, channel-fish, synth-vats.
  No migration: ingredients already are real items.

## 4 · Mixing & effect derivation

**The flow (decision #10):** open `use <bar>` (`commands/bar_menu.py`) — a menu
in the style of medical surgery's `operate`. In it the bartender:

- adds ingredients from the bar's bottomless stock ([a]);
- sees the projected effects, the composed flavour and any recognized classic
  (`world/bar.py::project_mix`);
- **pours** the loaded inputs into a drink, with a build/stir/shake/muddle/blend
  prep step;
- **saves/brands** the mix as a recipe (§5), or **makes a known recipe**;
- clears the load ([c]).

The drink lands on the bar for the patron.

The drink's effect profile is the **additive sum of the inputs' contributions,
then capped**:

```
mix( [ROTGUT_BASE ×1, STIM_ROOT ×1, CITRUS_GARNISH ×1] )
  raw  = {"alcohol": 3} + {"stim": 2} + {}        # additive
  drink.effects = cap(raw)                          # reuse existing caps
                = {"alcohol": 3, "stim": 2}
  drink.flavour = compose(flavours)                 # for the description
```

- **Caps** reuse what consumption already enforces (the alcohol cap), plus a
  **light per-effect safety-net cap** (decision #12, `MIX_EFFECT_CAP`) so
  stacking one ingredient can't overshoot. A mix can't exceed them — five
  rotguts don't make a five-strength drink. Tuned in play ("drunk is just a
  condition"); effects manifest as conditions, so the cap is really a
  condition-severity ceiling.
- **Balance is emergent (decision #9):** the only way to a potent drink is
  potent ingredients, and those are gated by sourcing cost/scarcity — not by a
  recipe rule. This is what makes free authoring (decision #5) safe.
- **Prep method is flavour and suggestion only.** The menu suggests a method
  for a recognized classic; the prep step does not change the drink's effects.
  Method *transforms* (distill/filter/dilute) are out of scope — a clean later
  layer (§14) that would multiply/shift contributions before the cap. Mixing
  is "combine."

**Cocktail recognition.** A hidden 20-template library (`COCKTAILS`) is
recognized at mix time by loose role-match: the roles must be present; ratios
and garnishes are ignored (`recognize_cocktail`). It recognizes spirit-swap
spins (*Mezcal Negroni*), same-skeleton families (rum sour → *Daiquiri*,
whiskey → *Whiskey Sour*; gin *Negroni* / whiskey *Boulevardier*; tequila
*Margarita* / brandy *Sidecar*) and spirit-less classics (*Mimosa*, *Spritz*).
A single-ingredient pour is *a glass of `<ingredient>`*; an unrecognized blend
is a *house mix* (`default_drink_name`).

**Flavour.** Refined ingredient tasting-notes are composed into a sentence
(`compose_flavour`), with authored taste prose for ~23 iconic named drinks
(`COCKTAIL_TASTE`, `compose_taste`). Flavour-only drinks (soda, recyc) surface
their taste too.

## 5 · Recipes

Mixing is freeform; a **recipe is a saved, named mix** (decision #5).

- **Free-mix:** anyone behind a bar can combine ingredients ad-hoc and get a
  drink. Experimentation *is* discovery — you learn what a combination does by
  trying it.
- **Save:** a successful mix can be saved inside `use <bar>` as a named
  recipe — `inputs (ingredient types × qty) → name + owner description`. The
  name is free text (custom names like *Kyoto Negroni*), and the recipe
  remembers its base cocktail. The bar now knows it: it can be re-made on
  demand, sits on the **menu**, and is **branded** (the Hub & Howl's "Reactor
  Wash" is mechanically rotgut+stim, but named and described its own way —
  emergent identity for near-zero engineering). A saved recipe's price is 0
  and cannot be changed in play (§7).
- **Recipe-as-knowledge (decision #11):** a saved recipe lives **at the bar**
  (in its menu) or **memorized by a character** — it is a **cyber-brain
  "file,"** the same data family as the planned contacts and memory systems.
  Recipes are therefore tradeable assets: sold, taught, copied between brains,
  stolen, kept secret — an emergent economy atop the ingredient economy. A
  saved recipe lives only on the bar's menu. A character memorizing a recipe,
  and trading it, is 📋 UNBUILT (no issue) — it rides the cyber-brain-files
  pass, §12.

## 6 · The output consumable

A made drink is an ordinary **consumable item** carrying the derived effect
profile mapped onto the existing consumption model (`world/bar.py::make_drink`,
`make_drink_from_recipe`):

- the `drink` delivery tag (category `delivery_method`) plus `db.is_drink` (the
  `drink` verb path).
- substance effects = the capped contribution profile → rides
  `apply_substance`, so **alcohol cap, tolerance, and addiction already apply**
  with zero new code.
- name + description = the recipe's brand (owner-authored) over the mechanical
  profile. The drink also carries `db.drink_taste`.
- **uses** = the drink is **one item with N consumption uses** (sips), exactly
  like a cigarette's drags (decision #13). Each `drink` spends one use and
  delivers a dose until the glass is empty — riding the existing multi-use
  bookkeeping: the drink carries `db.uses_left` (sips) and `db.drink_effects`
  (doses applied per sip through `apply_substance`), so it lines up with the
  consumption model exactly.

This is the payoff of decision #7: recipes don't invent an effect system; they
compose existing substances into a consumable the pipeline already understands.

**Consumption verbs at a bar.**

- `prepare <drink>` is a menu-skip shortcut: a known recipe poured straight
  onto the counter (`typeclasses/bar.py::CmdBarPrepare`).
- `chug` (drinks) / `devour` (food) consume every remaining use at once;
  medical items are guarded out.
- Ordinals work: `drink 2nd mug`.

### 6.1 · Drink definition (data model)

A drink/recipe record is a menu entry (see `world/bar.py::HUB_AND_HOWL_MENU`).
The field names and **all content are ours** (no external names or prose
reproduced). Messages use our pose/emote token format (`world/emote.py`).

| Field | Purpose |
|---|---|
| `name` | the drink's name (colony-authored, e.g. a house special) |
| `order_keywords` | words an order is matched against (§7.1) |
| `ingredients` | the input ingredient types (a spirit base, a mixer, a garnish…) |
| `price` | cost in chits — seeds §7 pricing |
| `sips` | the number of consumption uses (decision #13) |
| `effects` | **derived (our layer):** additive sum of the ingredients' substance contributions, capped (§4) |
| `desc` | appearance when examined |
| `taste` | the flavour, surfaced on consumption — gustatory/olfactory |
| `craft` | the craft narration, one string, third-person |
| `proto` | only on a plated dish: the prototype served instead of a mixed drink (§7.2) |

Notes:
- **Mechanics are ours.** Ingredients carry substance contributions (§3); the
  drink's `effects` are their capped sum (§4). A garnish is a flavour-only
  ingredient — empty contributions, real presence in the prose.
- **`craft` is a single third-person string** because it is spoken through
  `emote`, which renders per-observer identity and derives the first-person
  view itself. A first-/third-person pair would have nothing to do.
- **Per-sip and last-sip lines are not authored per drink.** `sips` is a count
  only. A future authored pass may add a per-sip line (one consumption use) and
  a finishing line (the final sip, emptying the vessel); that shape — appearance,
  taste, a per-sip line, a finishing line, craft narration, a price, an
  ingredient list — is a sound shape for any consumable craft (§14).
- **Theming is a content call:** polished cocktails suit an upscale venue; the
  Hub & Howl's menu is scuzzier. All drink names, descriptions, and prose are
  authored fresh for the colony — nothing lifted.

## 7 · Economy

- **Currency** is the `₮` token, consistent with shops.
- **Register:** the bar holds chits. A sale (`world/bar.py::_fulfil_from_board`)
  debits the patron, writes a `drink` record to the coin audit with the counter
  as the other party, and credits the counter's `register` if it keeps one. An
  audit failure never blocks the credit. The serve path takes the payment
  itself: there is no `deposit` verb and no separate bartender step; the
  payment shows only inside the bartender's one wordless serve gesture (§7.1).
- **Withdrawal** is **`till <bar>`** (`till <bar> = <amount>` for a partial
  take), gated on `BarCounter.is_bartender` (`typeclasses/bar.py::CmdBarTill`,
  #1515).
- **Pricing:** per-bar, per-recipe. Floor = ingredient cost; margin = the
  owner's call. A price is carried on the menu entry and read by the serve
  path, but **no tool in play sets one**: `manage` is 📋 UNBUILT (no issue), and
  the `use <bar>` save step writes `"price": 0` into every recipe it creates
  (`commands/bar_menu.py::_save_recipe`), with no prompt and no later edit
  path. So a player-authored house special is free, and re-pricing a board
  means editing a build script. "Margin = the owner's call" is therefore not
  yet reachable from play.
- **The Hub & Howl's prices are zeroed for now** by request (re-pricing
  restores the spoken-price/payment path).
- **Player-run bars become real economic nodes** — the hook into the
  favor/gear/rep loop. Money handling stays clean and simple; the
  faction/favor layer (§8, §14) builds on it later.

### 7.1 · Ordering — by talking to the bartender

A patron orders the way they would in life: by **addressing the bartender** —
directed speech (`to <bartender> …`, which rides `say` aimed at one person) or a
pose. This unifies player and NPC bartenders — both simply respond to a spoken
request. `say`, `to` and pose all route through the unified speech backbone
(`world/speech.py`); a pose that references the bartender counts as a directed
order.

**`order <thing>`** (`typeclasses/bar.py::CmdOrder`) is a targeting
affordance, not a second economy path. It resolves the tender for you and
speaks the order at them through the same `broadcast_speech` backbone: the room
hears it, perception applies, and fulfilment runs the identical serve path.
Ordering is still *talking to the bartender*; you no longer have to have been
introduced first.

> **Overturned, 2026-08-28 (#2342).** Decision #14 recorded "no `order`/`buy`
> verb". The `order` half was reversed because **you cannot address someone
> whose name you don't know**: `to` takes a single-token target and identity
> gates the name, so a stranger in a crowded bar resolves `Nonna` to nothing
> and `woman` to five people at once, so `menu` showed a board you had no way
> to act on; and souls never learn names, so no NPC could order anything from
> anyone. The `buy` half stands: there is no `buy` verb at a bar. A counter is
> **served**, a shelf is **sold from**, and a venue has exactly one of them
> (§7.2).

- **NPC bartender** — any NPC standing a counter's `bartender` (or `snailer`)
  post serves, through `world/bar.py::serve_from_board`. There is no bartender
  typeclass (#2378). It listens for requests, matches the request against its
  **menu**, and fulfils: makes the drink via the shared recipe→drink engine,
  sets it on the bar, and takes **payment on order** (chits → register), all as
  one wordless gesture with no system text, rendered by per-observer identity.
  No price is spoken on a sale; a patron who cannot pay hears the price
  ("That's N. Come back when you've got it."). The patron `get`s the drink.
  It acknowledges thanks non-verbally.
- **Player bartender** — identical social flow: hears the request, `use`s the
  bar to make it (the reference's RP ordering).
- **Fulfilment without supply (decision #14)** — the NPC isn't running a
  modeled ingredient inventory, so it fulfils from a known menu recipe and
  conjures the drink; the *same* recipe→drink engine players use, just without
  consuming real ingredient items. Real supply is a later pass.

**How a line becomes an order** (`world/bar.py::resolve_order`). It finds the
drink first with `resolve_drink`: the board (`match_recipe`, a keyword match),
then `mix_offmenu` from the bar's stock. Then it tests intent:

- An addressed line with an order cue (`ORDER_CUES`) passes if what is left
  after the cue is only the drink and filler (`_without_cues`, `_bare_order`).
- An addressed line without a cue must have no question mark and be only the
  drink and filler.
- An overheard line must have no question mark and pass the same
  drink-and-filler test.

The reason: a bare keyword match served drinks off ordinary conversation. "the
old man sent me" poured an Old Fashioned and "I'll take your word for it"
poured `the last word` (#2689), and an addressed question bought a drink and
suppressed the reply (#2779). NPC intent-parsing beyond this is a tuning
concern.

**Dependency:** directed speech — the **`to` command** (rides `say`, targeted at
an individual; e.g. `Bob [to William]: …`).

### 7.2 · Plated dishes — a board can serve food (#2342)

A menu entry naming a **`proto`** is *plated* rather than mixed: the real
prototype is spawned onto the counter, instead of a drink being composed from
ingredients (`world/bar.py::plate_or_mix`). Same gesture, same surface, same
payment — only the thing that lands is different.

```python
{"name": "grilled snail skewer", "order_keywords": ("skewer", "escargot"),
 "proto": "snail_skewer", "price": 3, "craft": "lays six on the grill-pan…"}
```

This is what makes a **restaurant** expressible. Without it the serve path
always ends in `make_drink_from_recipe`, and free `snacks` (§10) are
bottomless, priced at nothing and never enter inventory. A plated dish inherits
everything the item already carries (nutrition, bites, taste, decay), so a
kitchen serves exactly what a shelf sold.

**`craft` here, `serve_line` at a shop counter (#3413).** A plated dish served
from a BAR board uses the menu entry's `craft` string (`world/bar.py`); it never
reaches `world/shop/service.py hand_over`, so an item's `serve_line` has no
effect on this path. The same prototype sold over a SHOP counter (`buy`, or a
spoken order at a shelf/board post) does reach `hand_over`, which prefers the
item's `serve_line` over the counter style's gesture. The **snailery is served
entirely by the BAR path**: its counter (#8119) is a `BarCounter` with no
prototype inventory (#2342), so `snail_skewer`, `snail_jar` and the kuro are
plated with `SNAILERY_MENU`'s `craft` prose and never reach `hand_over` at all.
Those dishes carry no `serve_line`, and should not: `serve_line` is a
shop-counter mechanism and does nothing here — authored on a dish only a bar
serves, it is dead prose. See `SHOP_SYSTEM_SPEC.md` §8.

**The three venue models, and the rule.** A venue answers to *one* of these:

| model | fixture | how you're served |
|---|---|---|
| **served** | `BarCounter` with a `menu` | `order <thing>` → tender plates it onto the counter → you `get` it |
| **sold** | `ShopContainer` with `prototype_inventory` | `buy <thing> from <counter>` → pressed into your hand |
| **grazed** | anything with nutritious `snacks` | `eat <thing> from <fixture>` — free, in place, never inventory |

**Give a venue exactly one.** Two doors at one counter means only one of them
gets maintained: the Snailery carried a shelf *and* was described as a
restaurant, and that split produced the bug.

**Souls use the same doors.** The planner dispatches on **what the venue is**,
never on what the soul is — see `world/souls/actions.py::_feed_at` /
`_indulge_at`. Choosing the door by the soul's *species profile* was the defect
behind #2342: only a `recluse` knew how to be served and only a shelf would sell
to anybody, so sixteen colonists could stand in a restaurant and starve. A
venue that wants NPC custom needs three things — a board, somebody working it,
and the `("advertiser", "souls")` **tag** (an indexed tag, never the bare
attribute).

**The keeper eats from their own board, on the house.** Owner, 2026-11-13
(#3802): "A and their meal should as a result be complimentary." Option A was
the keeper making the meal themselves with `prepare`. A soul working a counter
that serves food prepares the cheapest dish on its board, picks it up and eats
it, unpaid (`world/souls/actions.py::_feed_at`). This covers food only: a
keeper is not served a drink at their own bar.

## 8 · Ownership & staffing

**Who may work a counter** is one boolean, `BarCounter.is_bartender`. In code
order it admits:

1. Builder+ staff;
2. an explicit `owner`/`staff` entry;
3. **whoever is standing this counter's shift**, via
   `world/souls/posts.keeper_on_duty`;
4. only for an unbound counter (below), whoever is present.

There is no owner tier distinct from a bartender tier, so "permitted to bartend
but not manage" has nothing to express it with. The design recorded a
three-tier owner / bartender / patron resolution, with `owner` holding full
rights (manage, set menu/prices, withdraw, edit staff) and `staff` permitted to
bartend but not manage; it was superseded by the job system on 2026-09-11
(#2597, #2921). The reason, from `is_bartender`'s docstring: no bar in the
colony has ever had `owner` set, so the owner attribute was never the operative
rule anywhere, and the post became the answer instead. The §8 seam snapped onto
posts rather than factions.

**Bound means ever assigned (#3573).** "Unbound" — the vending tier — is one
function, `world/souls/posts.is_bound`, asked by `is_bartender`,
`ShopContainer.purchase_item`, the souls planner's `_counter_open`,
`world/service.post_for` and `world/bar.tender_at`. A counter is bound if it has
shift slots, or if a keeper, owner or staff entry was **ever** set, **even if
that character has since been deleted**. Evennia reads a deleted reference back
as `None`; taking that for "never assigned" would drop a counter whose person
was gone to the vending tier, and anyone present could empty its till. A bound
counter with nobody valid present reads closed, the state a vacant shift
already produces. Dead owner and staff entries never match anyone.

**`owner`/`staff` are legacy, hardened but not extended.** Future player owners
and staff are designed separately in #3648: ownership keyed by sleeve uid (as
lockers are), shared across bars, shops and carts, with player staff as post
slots. Retire these two fields in that change.

**Faction/favor is a stubbed seam (decision #8):** the later pass lets factions
own bars, ties staff permissions to the favor system, and may lean on the
parked **TRUST_AND_CONSENT** work (who may act at *your* bar). Design so that
seam snaps on — don't hardcode "owner is a single character" everywhere.

## 9 · Command reference (v1)

Mapped from the reference `examine bar`, gelatinous-flavoured. `<bar>` is the
counter object.

**Patron**
- `read menu on <bar>` (also `menu`) — what's servable, with prices: `₮`
  currency, operate-orange, column-aligned (`typeclasses/bar.py::CmdBarMenu`).
- `order <thing>` — ask whoever is working the counter (§7.1). Directed speech
  with the targeting resolved, for when you don't know the tender's name —
  which is most of the time, and always for an NPC.
- *or address the bartender yourself* — `to <bartender> …` or a pose. Identical
  path; ordering is social.
- `eat <snack> from <bar>` — free snacks (§10).
- `get <drink> from <bar>` — take what was served onto the counter.

**Bartender** (whoever `BarCounter.is_bartender` admits — see §8)
- Ingredients are added from the bar's stock inside `use <bar>` ([a]). A `load`
  verb for carried ingredients, or a container of them, is 📋 UNBUILT (no
  issue); `put … in <bar>` answers that the bar can't hold it.
- `use <bar>` — opens the crafting menu (in the style of medical `operate`, but
  its own command): mix the loaded inputs free-form or via a known recipe,
  optionally save/brand the result; the drink lands on the bar for the patron
  (§4).
- `prepare <drink>` — a menu-skip pour of a known recipe straight onto the
  counter (`typeclasses/bar.py::CmdBarPrepare`).
- `clean <bar>` (alias `wipe`) — clear abandoned loads, drinks and dishes off
  the bar.
- `till <bar>` / `till <bar> = <amount>` — drain the register (§7).
- `deposit <$> in <bar>` — ring a sale into the register. 📋 UNBUILT (no
  issue); the serve path credits the register itself (§7).

**Owner**
- `manage <bar>` — menu (add/remove recipes), pricing, staff allowlist,
  register withdrawal, save/rename/brand recipes. 📋 UNBUILT (no issue). Of
  these jobs, register withdrawal is `till`, and adding a recipe and
  saving/renaming/branding it live in the `use <bar>` menu. The **staff
  allowlist** and **pricing** have no in-game door at all (§7).

Both player and NPC bartenders work the same way — the patron *says* what they
want (`order <thing>`, `to <bartender>` or a pose) and the bartender makes it: a
player opens `use <bar>` and adds ingredients from stock, an NPC parses and
fulfils from its menu. There is no `buy` verb at a bar. `order <thing>` is
directed speech with the target found for you, per §7.1.

## 10 · Free snacks

Pure ambiance, near-zero cost: a bar offers a fixed snack list (`db.snacks`).
`eat <snack> from <bar>` eats it in place: bottomless, free, and nothing enters
inventory; any effects a snack carries are applied through `apply_substance`.
Colony flavour instead of peanuts/pretzels/pickles: every counter starts with
`DEFAULT_BAR_SNACKS` (**brine pods**, **synth-jerky**, **ration crackers**), and
any object with `db.snacks` can serve them (#2074).

## 12 · Integration points

- **Consumption pipeline** — `world/consumables.py`, `apply_substance`, the
  `drink`/`eat` verbs; the substances registry (`world/substances/registry.py`)
  supplies effect types and caps. Recipes produce items it already handles.
- **Harvest command** — the future sourcing extension point (decision #6).
- **Menu/runner framework** — the crafting UX is built in the *style* of the
  medical `operate` menu (and may share its runner internally) but exposed as
  **`use`** to keep the two distinct (decision #10); the bar is where that
  pattern generalises beyond surgery into crafting stations (§2.1).
- **Cyber-brain files (planned)** — recipes are the same data family as the
  planned contacts/memory "files" (decision #11); built minimally here, unified
  there.
- **Speech** — `world/speech.py` (`say`/`to`/pose); the NPC reacts to any of
  them (§7.1).
- **Economy / chits** — the register; vendors for ingredient supply.
- **Crowd system** — bars are already crowd hotspots (the Hub & Howl is base
  3); a busy bar reads packed, which the recipe/serve loop now gives a reason
  for.
- **Shops** — `SHOP_SYSTEM_SPEC.md` §8 (`serve_line` vs a bar board's `craft`,
  §7.2).
- **Reference venues** — Hub & Howl (hull-slab bar), Helix Lounge, Queen of Cups
  lobby.

## 14 · Unbuilt

Wanted, not built. Items marked in place above are repeated here.

- **Supplier-NPC ingredient economy** (decision #6) — 📋 UNBUILT (no issue).
  Ingredient vendors whose prices are the floor under a drink (§3). This is the
  biggest deferred piece gating "real" scarcity-driven balance.
- **Loading carried ingredients, or a container of them, into a bar** (a `load`
  verb, decision #10) — 📋 UNBUILT (no issue) (§2, §9).
- **Owner tooling** — `manage` (menu, pricing, staff allowlist) and `deposit`
  are 📋 UNBUILT (no issue) (§9). `clean` and `till` exist, and the serve path
  credits the register itself. In-game pricing and staff-list editing have no
  door until then.
- **Cyber-brain files** — recipes join contacts/memory as one file/data layer
  (decision #11); a character memorizing a recipe, and trading it, is
  📋 UNBUILT (no issue). Richer copy/teach/sell/steal flows ride that pass.
- **General crafting / workshop mechanics** — extract the *load → use →
  recipe → output* station pattern (§2.1) into a reusable crafting framework,
  so the bar is the first of many stations (chem bench, fabricator, galley).
  The bar build should make that pattern recognisable, not bar-specific.
- **Deep ingredient sourcing** — extend `harvest` for ice/fish/synth
  (decision #6).
- **Prep methods / stations** — distill/filter/dilute transforms before the
  cap (§4). Prep methods today are flavour only.
- **Faction-integrated ownership** — factions own bars, favor-gated staff,
  trust/consent for who-acts-at-your-bar (§8).
- **Non-drink consumables from ingredients** — mixing food or drugs from
  ingredients. A board already serves ready-made dishes (§7.2).
- **Per-spin authored tastes** — authored taste prose for spirit-swap spins.
- **Authored per-sip and finishing lines** per drink (§6.1).
- **The Queen of Cups lobby's own bar** (§2).

## 15 · Not decided

1. **Effect/balance tuning** — `MIX_EFFECT_CAP` and per-sip dose scaling (esp.
   `chug` stacking) are first-pass; "drunk is just a condition," tune in play.
