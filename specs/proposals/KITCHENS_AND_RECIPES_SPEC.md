# Kitchens & Recipes Spec — the food half of the consumable economy

> **Status:** 📋 **Proposal — design only (2026-08-25, owner-prompted).**
> **This spec ELABORATES promises two shipped specs already made; it
> supersedes neither.** Parents: (1)
> [`GIG_PROTOTYPE_BUTCHER_SPEC`](../GIG_PROTOTYPE_BUTCHER_SPEC.md) **§7 —
> the three-tier food roadmap** (tier 1 cuts + tier 2 cook/menu SHIPPED
> in `world/food.py` for Ottilie's cart; tier 2's own words: "a menu
> item is a recipe… `make_drink_from_recipe`, generalized to food… a
> **cook/kitchen** (or the bar)"; tier 3 provenance/tainted cuts
> deferred). (2) [`BARS_AND_RECIPES_SPEC`](../BARS_AND_RECIPES_SPEC.md)
> §2.1 — the promised reusable **crafting-station framework** (the bar
> was named its on-ramp), plus §10's snack scoping. The owner's brief —
> street-food diversity powered by "a recipe system akin to
> bartending" — is exactly those promises, cashed: one engine, the
> kitchen as station #2, and the venue-diversity program neither parent
> scoped. Butcher §7's tier language is adopted wholesale below.

## 0 · Purpose

Kitchens are where raw ingredients become dishes, the way bars are where
they become drinks. One recipe engine, two station families. The design
goal beyond mechanics is **diversity**: the colony's manifest is
many-heritage (Bhavani, Tsiolkovsky, Pessoa, Lin, Escallier, Krug…) and
its tables should read like it — heritage kitchens, a ladder of protein
sources, and venue *types* that shape social play, not just menus.

## 1 · Architecture (mirroring the bar's locked decisions)

```
ingredients (real items; substance contributions + culinary role)
     ↓
  kitchen station (pot / griddle / grill / oven — crafting station #2)
     ↓  cooking → effect profile = ADDITIVE SUM of contributions (capped)
     ↓  dish recognition → template library names the result
  dish recipe (repeatable, brandable, tradeable knowledge)
     ↓
  the plate (consumable: uses_left, composed taste, effects)
```

| # | Decision | Call (inherits the bar's unless noted) |
|---|----------|--------------|
| 1 | Engine | **the bar engine, generalized** — the station framework the bar spec promised (§2.1 there) gets built HERE, and the bar becomes its first client retroactively |
| 2 | Front-ends | both — NPC cooks serve (economy) AND players cook at stations (emergent) |
| 3 | Effects | live on ingredients; additive sum, capped; same substance pipeline `food.py` already uses |
| 4 | Recipe model | free-cook → save as named dish; **recipes are cyber-brain "files"** (same data family as bar recipes/contacts) — which makes heritage recipes *heirlooms*: stealable, tradeable, giftable, hackable when decking lands |
| 5 | Culinary roles | the cocktail-role analog: **protein / starch / aromatic / sauce-fat / garnish** — composition drives recognition |
| 6 | Recognition | a hidden **dish-template library** (the 20-cocktail analog): composition + station type → *soup, skewer, dumpling, congee, curry, flatbread, zakuski plate, stew, pickle plate…* Single-ingredient over heat = *grilled/boiled `<thing>`* |
| 7 | Balance | **ingredient scarcity**, not rule caps — and scarcity is geographic: supply chains are the lever |
| 8 | Stations differ | pot / griddle / grill / oven gate which templates can emerge (no dumplings off a grill); venue character follows from its station |

## 2 · Ingredients — one catalog, many sources

Unify the families that already exist into the bar's two-layer shape:
the butcher's cuts (`world/food.py`), the snailery's stock, bar
perishables where they overlap (citrus, honey), plus new entries. Every
ingredient names its **source in the world** — this is where the
Southside program becomes literal:

- **Greenhaus towers** → greens, herbs, fruit (the Fungary's mushrooms
  are the fungal rung of the protein ladder)
- **Escallier Snailery** → snails (the humble rung)
- **The Butcher (Ottilie)** → cuts (the honest rung)
- **future Rendering Works** → vat-paste (the corporate rung — cheap,
  abundant, flavorless base the artisan street defines itself against)
- **future hatchery** → crickets/grubs (the dry rung)
- imports/scarce goods → spice, tea, real coffee (gig-worthy cargo)

Ingredient scarcity = supplier relationships = delivery gigs = the
favor economy. A kitchen without a snail line buys jars at Nonna's
counter like anyone else.

## 3 · Cooking & the plate

`use <station>` opens the bar-style menu: load ingredients from house
stock (NPC venues get `derive_kitchen_stock`, the bottomless-larder
analog), cook, name or recognize, serve. The output consumable follows
the drink data model: `uses_left`, composed taste sentence from
ingredient flavour notes, derived effects. Prep-method *mechanics*
(ferment, cure, smoke) defer exactly as the bar deferred them — but the
fermentory venue is designed against that future.

## 4 · The venues (the diversity this exists to serve)

Heritage kitchens, each a different table: a **dosa/chaat counter** off
Bhavani; a **dumpling window** (a hatch in a prefab wall, three seats);
a **zakuski cellar** near Tsiolkovsky (samovar, black bread, pickles);
a **bakery** on the Heat Works' steam line when it exists; a
**third-shift congee window** open when everything else is dark (the
`{time}` system's first venue). Venue *types* beyond menus: **tea
house** (lingering, the anti-shift-food), **fermentory** (crocks and
jars; supplies every kitchen above), **spice stall** (one cell, huge
sense radius), and the **vat-protein counter** — Greenhaus or Longhaul
branded, six flavors of slab, the soulless counterpoint that gives every
artisan NPC an opinion. Branding per the world rule; handmade operations
may stand unbranded (the Escallier precedent).

## 5 · Build phases

1. **Engine lift** — build the station framework Bars §2.1 promised:
   extract the bar's station/menu/recognition core; bar and kitchen both
   consume it. `FOOD_RECIPES` in `world/food.py` (Butcher §7 tier 2 as
   shipped) migrates to engine data — Ottilie unaffected at her counter;
   her cook block becomes the framework's first food client. Butcher §7
   tier 3 (provenance/tainted contributions) rides this engine when it
   lands.
2. **Pilot venue** — one heritage kitchen end-to-end on the Lin vendor
   recipe + a station (candidate: the dumpling window — smallest possible
   venue, biggest template payoff).
3. **Player cooking** — public/rentable stations; free-cook + save.
4. **Recipes as files** — trade/theft/inheritance; decking exposure when
   the net lands.
5. **Supplier chains** — stock derives from live world sources;
   delivery gigs close the loop.

## 6 · Integration & conventions

- **`world/prototypes.py` registers prototypes as UPPERCASE module
  variables** — never insert bare dict literals (the snailery lesson,
  #1950). Spawn-test new AND neighboring prototypes.
- Archetype system makes cooks cheap content: entry + palette + seed.
- Time system: opening hours as venue character (the congee window).
- Hunger/need mechanics: **none exist and none are proposed** — food
  remains flavor + substance-effects; this spec adds depth, not chores.

## 7 · Open questions (owner)

1. Dish quality tiers (cook skill?) or flat like the bar's v1? (G.R.I.M.
   stats exist; a Motorics/Intellect dab is possible but unproposed.)
2. Should saved dish recipes be *teachable* NPC→player (Nonna teaches a
   snail dish as a favor reward)?
3. Which pilot venue — dumpling window, or push diversity westward with
   the Bhavani dosa counter first?
4. Does the vat-protein counter belong to Greenhaus (empire-completing)
   or Longhaul (logistics-flavored)?
