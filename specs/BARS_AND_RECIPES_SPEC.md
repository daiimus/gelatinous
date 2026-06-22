# Bars & Recipes Spec

> **Status: ✅ v1 SHIPPED & LIVE** (drafted 2026-06-20; v1 built & deployed
> 2026-06-21/22 at the Hub & Howl). All 14 locked decisions (§1.1) are
> implemented, plus several pieces beyond the original v1 line (cocktail
> recognition, prep methods, bottomless house stock, chug/devour). Remaining
> work is the deferred seams (§11): supplier-NPC ingredient economy, the
> register/`manage`/`clear`/`deposit` owner tooling, faction ownership, and the
> general crafting-station framework. See **§0.1 · Implementation status** for
> the shipped/deferred breakdown. Builds directly on the consumption pipeline
> (`SUBSTANCES_AND_DELIVERY_SPEC.md`, `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`) —
> recipes produce ordinary consumables, no new effect engine.

## 0.1 · Implementation status (2026-06-22)

**Shipped & live (PRs #639–#689):**
- `BarCounter` — an `@integrate` room fixture (folds into the room desc,
  `get:false`), a served-drink surface (counted `On the bar:` listing), its own
  `db.desc`, the menu (`₮` currency + operate-orange, column-aligned), and the
  `read menu on <bar>` verb. Wired end-to-end at the Hub & Howl.
- **NPC bartender** (Sully) — takes orders diegetically via the unified speech
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
  *plus* a cocktail role + spirit type. ~44-ingredient seeded catalog
  (`@ingredient <key>` spawns them for testing, pending the supplier economy).
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
- **Role gating** — `is_bartender` allows owner/staff and any Builder+ staff.
- **Pricing** — currency is the `₮` token (shop-consistent); Hub prices **zeroed
  for now** by request (re-pricing restores the spoken-price/payment path).

**Deferred (designed-for, not built — see §11):** supplier-NPC ingredient
economy (#6); register + `manage`/`clear`/`deposit` owner tooling (§9); cyber-
brain recipe files / portability + trade (#11); faction-integrated ownership
(§8); the reusable crafting-station framework (§2.1); prep-method *mechanics*
(shipped as flavour-only); per-spin authored tastes.

## 0 · Purpose

Bars exist as *rooms* today (the Hub & Howl, Helix Lounge, Queen of Cups) — set
dressing, no mechanics. This makes them **functional social and economic hubs**:
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

## 2 · The bar object

A new typeclass (working name `BarCounter`, a `Furniture`/`Object` subtype)
placed in a bar room. It is examinable and exposes role-gated verbs. The Hub &
Howl's "bent slab of starship hull" becomes a real instance; Helix Lounge and the
Queen of Cups lobby get their own.

**State (AttributeProperties):**

- `menu` — recipes this bar serves (list of saved recipe refs + per-bar price).
- `loaded` — ingredients (or a container of them) loaded in as the crafting input.
- `surface` — finished drinks rest here for the patron to `get`.
- `register` — chit balance held by the bar.
- `owner` — character (or faction, later) who owns it.
- `staff` — allowlist of characters permitted to bartend/manage.
- `snacks` — free ambiance snacks offered (§10).
- `stock` is **not** a concept — ingredients are real items in someone's hands
  (decision #6), so "being stocked" means having ingredient items on/behind the bar.

**The four pillars** (from the reference `examine bar`, reframed around the bar
as a *crafting station*):

1. **Menu / craft** — `read menu`, and the prepare action: **`use <bar>`**
   (decision #10) — a menu in the style of medical surgery's `operate`, but its own
   command to avoid confusion. Load ingredients, pick or save a recipe, mix.
2. **Load + serve surface** — the bar is *loaded* with ingredients (or a container
   of them) as the crafting input (decision #10, §2.1); finished drinks rest on it
   for the patron to `get`. `put`/`get`/`clear` move ingredients in and drinks out;
   `clear` tidies abandoned items.
3. **Register** — `deposit $`; the bar is an economic actor (§7).
4. **Manage** — owner config: menu, prices, staff, recipe management (§8).

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
ingredient prototype, e.g. ROTGUT_BASE:
  db.ingredient = True
  db.contributions = {"alcohol": 3}            # effect-type → magnitude
  db.flavour = "raw, paint-stripping"           # for derived drink descriptions
  db.consumed_per_use = 1                        # units a mix consumes
```

- **Effect types** reuse the substance registry (alcohol, stim, pain_relief,
  sedation, …) so derived drinks need no new effect engine.
- **A "garnish"** is just an ingredient with empty/flavour-only contributions —
  it changes the drink's name/description, not its punch.
- **Sourcing (v1):** ingredients are bought from **supplier NPC vendors** — a
  chem supplier, a food/produce vendor, an Earth-imports dealer. Real items,
  real cost; their price is the economic floor under a drink.
- **Sourcing (later):** harvesting/fishing/synthesis. Per decision #6 these are
  *the same items* acquired via an **extended `harvest` command** (the medical
  harvest verb already exists) — ice from the mines, channel-fish, synth-vats.
  No migration: v1 ingredients already are real items.

## 4 · Mixing & effect derivation

**The flow (decision #10):** load ingredient items (or a container of them) into
the bar, then `use <bar>` — a menu in the style of medical surgery's `operate` — to
mix the loaded inputs into a drink. The drink's effect profile is the **additive sum of
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
  secret — an emergent economy atop the ingredient economy. (v1: a recipe is a
  datum the bar and/or a character holds; the richer file/trading UX rides the
  cyber-brain-files pass — §12.)

## 6 · The output consumable

A made drink is an ordinary **consumable item** carrying the derived effect
profile mapped onto the existing consumption model:

- `medical_type` / delivery tags = drink (the `drink` verb path).
- substance effects = the capped contribution profile → rides `apply_substance`,
  so **alcohol cap, tolerance, and addiction already apply** with zero new code.
- name + description = the recipe's brand (owner-authored) over the mechanical
  profile.
- **uses** = the drink is **one item with N consumption uses** (sips), exactly
  like a cigarette's drags (decision #13). Each `drink` spends one use and delivers
  a dose until the glass is empty — riding the existing multi-use/dose bookkeeping
  (`db.substance_doses`), so it lines up with the consumption model exactly.

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
- **Theming is a content call:** polished cocktails suit an upscale venue; the Hub
  & Howl's menu is scuzzier. All drink names, descriptions, and prose are authored
  fresh for the colony — nothing lifted.

## 7 · Economy

- **Register:** the bar holds chits. Serving a menu drink for a price moves chits
  patron → register; the owner withdraws profit via `manage`. `deposit $` covers
  the bartender ringing up a sale.
- **Pricing:** per-bar, per-recipe (set in `manage`). Floor = ingredient cost;
  margin = the owner's call.
- **Player-run bars become real economic nodes** — the hook into the favor/gear/
  rep loop. v1 keeps money handling clean and simple; the faction/favor layer
  (§8, §11) builds on it later.

### 7.1 · Ordering — by talking to the bartender

There is **no `order`/`buy` verb.** A patron orders the way they would in life: by
**addressing the bartender** — directed speech (`to <bartender> …`, which rides
`say` aimed at one person) or a pose. This unifies player and NPC bartenders —
both simply respond to a spoken request.

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
individual; e.g. `Bob [to William]: …`). If `to` isn't built yet it's a prerequisite
for NPC ordering (pose works in the meantime). NPC intent-parsing beyond a menu-name
match is a tuning concern, not a v1 blocker.

## 8 · Ownership & staffing

- `owner` — who owns the bar; full rights (manage, set menu/prices, withdraw,
  edit staff).
- `staff` — an allowlist of characters permitted to bartend (`load`/`use`,
  serve, `deposit`) but not manage.
- **Role resolution:** a verb checks the actor against owner/staff/neither →
  owner / bartender / patron tier.
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
- *to order:* **address the bartender** — `to <bartender> …` (directed speech) or a
  pose. No `order`/`buy` verb; ordering is social (§7.1).
- `eat <snack> from <bar>` — free snacks (§10).
- `get <drink> from <bar>` — take a drink served onto the bar.

**Bartender** (owner or staff)
- `load <ingredients> into <bar>` (`put … in <bar>`) — load ingredient items, or a
  container of them, as the crafting input (decision #10).
- `use <bar>` — opens the crafting menu (in the style of medical `operate`, but
  its own command): mix the loaded inputs free-form or via a known recipe,
  optionally save/brand the result; the drink lands on the bar for the patron.
- `clear <bar>` — clear abandoned loads/drinks off the bar.
- `deposit <$> in <bar>` — ring a sale into the register.

**Owner**
- `manage <bar>` — menu (add/remove recipes), pricing, staff allowlist, register
  withdrawal, save/rename/brand recipes.

(Both player and NPC bartenders work the same way — the patron *says* what they
want (`to <bartender>` / pose) and the bartender makes it: a player loads and
`use`s the bar, an NPC parses and fulfils from its menu. No `order`/`buy` verb —
ordering is social, per §7.1.)

## 10 · Free snacks

Pure ambiance, near-zero cost: a bar offers a fixed snack list (`db.snacks`),
`eat <snack> from <bar>` yields a trivial no-effect (or tiny-effect) consumable.
Colony flavour instead of peanuts/pretzels/pickles: e.g. **brine pods**, **synth-
jerky**, **ration crackers**. Optional for v1; cheap to add.

## 11 · Build phases

**v1 — ✅ SHIPPED (2026-06-21/22):**
- ✅ `BarCounter` object + the four pillars + role gating (owner + staff + Builder+).
- ✅ Ingredients as real items with contribution profiles (+ cocktail identity).
      Supplier-NPC vendors **deferred** — a seeded catalog + `@ingredient` spawn
      tool stands in for now.
- ✅ Free-mix → additive-capped drinks → consumption pipeline.
- ✅ Save/name/brand recipes; menu. **Pricing** present (zeroed by request);
      **register** deferred.
- ✅ One reference bar wired end-to-end (the Hub & Howl).

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
- **Non-drink consumables** — the same engine makes food/drugs, not just drinks.

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
3. ✅ **Ingredient contributions** — assigned across the seeded catalog (§3).
4. **Effect/balance tuning** — `MIX_EFFECT_CAP` and per-sip dose scaling (esp.
   `chug` stacking) are first-pass; "drunk is just a condition," tune in play.
5. **Owner tooling** — `manage`/`clear`/`deposit` and the register are the main
   unbuilt v1 commands (§9); spec'd, not yet built.
6. **Supplier economy** — the ingredient vendor loop (#6) is the biggest deferred
   piece gating "real" scarcity-driven balance.
