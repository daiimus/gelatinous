# Clothing Types & Style Motifs

> **Status:** 📋 **PROPOSAL — §4 style vocabulary RULED 2026-08-20**
> (seven keywords, revealing derived, style-states as a tell, brands
> carrying style). Still wanting the red pen: the type vocabulary
> (§2) and the layer reconciliation (§3).
>
> **⚠ STATUS STALE — checked against code 2026-09-11. §2, §3 and §4 have
> all SHIPPED.** §2 is `world/style.py` `RUNGS` + `derive_rung`, read
> through the `Item.layer` property in `typeclasses/items.py` (#2126,
> closed). §3 was settled as option (a) and executed by
> `scripts/builds/090_one_ladder.py` (#2112, closed). §4/§4.3 are
> `world/style.py` `STYLES`/`BRAND_STYLES`/`derive_style`/`affinity` and
> `PRESENTATIONS`/`derive_presentation`, rolled onto every arrival in
> `world/souls/population.py` and authored onto the cast by
> `scripts/builds/095_colony_style.py` (#2122, closed). Of §8's phases,
> P1 and P2 are shipped and P3 is largely shipped; only P4 (weather) is
> untouched. §9 is done (#2110, closed). Per-section notes below.
>
> Builds on the shipped
> clothing system (coverage/layer/worn_desc, `is_wearable`), the
> Wardrobe need (#2104/#2106), blueprint wardrobes, and the identity
> system. Traits (NPC_TRAITS_SPEC) and designation
> (SKILLS_AND_DESIGNATION_SPEC) are its natural feeders.

## 1. The idea

Two keyword vocabularies, both carried by the *garment* and read by
everything else:

- **TYPE** — what a garment *is* (coat, boots, apron, respirator).
  Derived from the item's NAME, so naming a thing correctly is what
  makes it behave correctly. Type determines **layer** and a default
  **coverage**.
- **STYLE** — what register a garment is *in* (salvage, clinical,
  lounge…). A character carries style keywords too, so **an outfit is
  a lookup, not an authored list**: match the person's style against
  the garment's.

This is the same shape the substances layer already uses — declare on
the item, match on the consumer — and it means a generated resident
can have coherent taste without anyone hand-writing their wardrobe.

## 2. Type keywords → layer (OWNER RED PEN)

> **SHIPPED — note added 2026-09-11.** This table is live as `RUNGS` in
> `world/style.py`, reached through `derive_rung` and the `Item.layer`
> property in `typeclasses/items.py` (#2126). The shipped ladder
> differs from the table below in four places settled after this was
> written: `goggles` sits on rung 5 (not 2), `slicker` on rung 3 (not
> 4), `poncho` on rung 4 (not 3), and `watch`/`chrono` (#2433) and
> `scrubs` (#3088) were moved down to rung 1. The shipped table also
> carries words this one never listed — `top`, `suit`, `wig`,
> `carrier`, `lenses`, `rebreather`.

A garment's name is scanned for the first matching type keyword; that
type fixes its layer and supplies default coverage when the prototype
doesn't override. Names are checked longest-first so "trenchcoat"
beats "coat" and "labcoat" beats "coat". (Note 2026-09-11: in the
shipped `derive_rung` the `labcoat` half holds, but the `trenchcoat`
half does not. The matcher anchors a word boundary at **both** ends
(#2478/#2657), so a closed compound matches nothing and `trenchcoat`
and `longcoat` both fall to the default base rung. Neither word is in
the shipped `RUNGS` table, although `world/style.py`'s own docstring
says a compound the table should know belongs in the table — so this
is a gap in the code, not a change of intent here.)

| Layer | Register | Type keywords |
|---|---|---|
| **0 — skin** | worn under everything | bra, briefs, boxers, panties, thong, underwear, undershirt, socks, stockings, tights |
| **1 — base** | the default; anything unlisted lands here | shirt, tee, t-shirt, blouse, henley, tank, trousers, pants, jeans, skirt, dress, jumpsuit, coveralls, scrubs, leggings |
| **2 — mid** | over the base, under outerwear | vest, waistcoat, sweater, jumper, hoodie, cardigan, glasses, goggles, mask, respirator, balaclava |
| **3 — shell** | jackets and the like | jacket, windbreaker, blazer, poncho, cut, harness, hood |
| **4 — outer** | the big coats and the working over-layers | coat, longcoat, trenchcoat, overcoat, topcoat, greatcoat, duster, labcoat, slicker, apron, robe, bathrobe, coverall, parka |
| **5 — carried & fastened** | accessories, worn over everything | belt, tie, necktie, scarf, shawl, bandana, armband, badge, choker, boots, shoes, slippers, clogs, gloves, hat, cap, helmet |

Two rules make the convention enforceable rather than advisory:

1. **Naming a garment names its layer.** Any object whose key
   contains a type keyword takes that layer unless its prototype
   states one explicitly. Player-made and generated clothing get
   correct layering for free.
2. **Unknown = layer 1.** No name match means base layer, so an
   unnamed scrap of cloth can never accidentally outrank a coat.

## 3. The layer reconciliation (the real integration cost)

> **DONE — note added 2026-09-11. The owner picked (a) and the
> migration ran.** `scripts/builds/090_one_ladder.py` (#2112, closed)
> moved every spawned garment onto the settled ladder, and #2741/#2464
> later dragged the prototypes after it. **The "what's actually there
> today" table below is now a pre-migration snapshot:** boots are rung
> 5 (not 3), the plate carrier and the hi-vis vest are rung 2 (not 4),
> the tox-sealed slicker is rung 3 (not 4), and rung 0 is no longer
> armour alone — `CODER_SOCKS` sits there. What did *not* happen is the
> second half of the recommendation: the plates stayed on `layer` 0
> instead of moving to their own scale, on build 090's reasoning that
> they were never on the ladder at all (they live in a carrier's
> `plate_slots`). The three options below are spent.

The shipped layer scale is **already 0–5 but means something else**,
and this is the one part of the spec that costs migration work:

| Layer | What's actually there today |
|---|---|
| 0 | **armour inserts** (trauma plate, ceramic plates) — not underwear |
| 1 | base clothing (t-shirt, jumpsuit, tactical pants) ✅ matches |
| 2 | hoodies AND face gear (balaclava, surgical mask, respirator) |
| 3 | **boots**, hoods, ponchos, harnesses, sleeveless cuts |
| 4 | plate carrier, hi-vis vest, long coat, tox-sealed slicker |
| 5 | plate mail |

So today boots are layer 3, masks share a layer with hoodies, and
layer 0 is spoken for by armour. Three ways out, owner's call:

- **(a) Migrate to §2.** One build script rewrites `layer` on every
  clothing prototype and every spawned garment; armour inserts move
  to their own scale (or a negative/none layer, since they are worn
  *inside* carriers rather than competing with cloth). Cleanest end
  state, one disruptive pass.
- **(b) Parallel scale.** Leave `layer` alone; add `garment_layer`
  derived from type and use it only for the new outfit logic. No
  migration, two scales to keep straight forever — I'd avoid it.
- **(c) Adopt current usage.** Rewrite §2's table to match what's
  already there (boots at 3, no skin layer). Cheapest, but the colony
  never gets an underwear layer and the naming convention inherits
  today's inconsistencies.

Recommendation: **(a)**, done once, with armour separated from cloth —
they are different problems that have been sharing a number.

## 4. Style motifs (OWNER-RULED 2026-08-20)

Style is a small keyword set, carried by garments as
`db.style = ["salvage", "workwear"]` and by characters the same way.
**A garment may carry several** — clothing is versatile, and a
Longhaul slicker is honestly `workwear` and `sealed` at once.

| Keyword | Reads as | Where it lives |
|---|---|---|
| `salvage` | scavenged, mended, mismatched | the Boot, the scrapyards, Kaspar |
| `workwear` | kit you do a job in | Longhaul, the crane, the Heat Works — **and** Greenhaus canvas, aprons, growing and food work |
| `clinical` | medical and cryogenic whites | Maxwell, Kaspar UC, Thawn-Harrison |
| `uniform` | the dead chart's leftovers, service dress | constabulary, dispatch, old ship kit |
| `shine` | going-out clothes, made to be seen | the Helix, the bars, the Rook's listeners |
| `street` | everyday colony wear | Pessoa, the Brackett, most residents |
| `sealed` | weatherproofed, respirators, slickers | the toe breach, the hull-top, tox work |

Rulings folded in:

- **`growers` is gone; growing work is `workwear`.** The difference
  between a Greenhaus apron and a Longhaul coverall is real, but it
  is carried by the **brand**, not by a second keyword.
- **Brands carry style** (the branding law earns its keep): a garment
  takes its brand's style unless it states otherwise, so every future
  branded item is pre-sorted at authoring time.
- **`street` is a real style**, not the absence of one — most
  residents wear it, and it still sorts against `shine` and `uniform`
  when a soul chooses what to put on.
- **Parked, deliberately**: a **money** register (no visible wealthy
  class yet) and **crew colors** (gang/faction identity — WSIS's
  business when it arrives). Both are good touch points; neither is
  ready.

### 4.1 Revealing is DERIVED, never declared

"Revealing" is not a keyword. Coverage is already computed, so how
much skin an outfit leaves is **measurable** — and that makes it
relative, which is truer than a label: the same halter is revealing
on one body and unremarkable under a coat.

A character carries a coverage *preference* alongside their modesty
floor. A Companion has a low floor **and** a preference for the
minimum above it; a Flinch-Coded shut-in has a high floor and prefers
more. Nobody is tagged "revealing"; they simply choose that way.

### 4.3 Presentation — the second axis (RULED 2026-08-20)

Style says which world a garment comes from; **presentation** says
which line it cuts. Orthogonal, so `shine` + femme is the slit skirt
and `shine` unmarked is the Rook's black silk.

Three rules, and they are the design:

1. It describes the **garment**, never the wearer. No table anywhere
   says what a body may put on.
2. It **never gates**. Anyone wears anything; the axis only shapes
   what a soul reaches for first.
3. A character's leaning is its **own attribute, rolled
   independently of `sex`**. Deriving it from sex would build exactly
   the stereotype machine this design exists to avoid — so a
   male-sexed arrival may lean femme, and the game dresses him that
   way without comment.

All three readings are **first-class and derive on their own terms**
— a necktie and a pair of boxers read masc exactly as a shawl and a
pair of panties read femme, and a character may lean any of the three.

The DATA will skew femme/neutral, because most masc-coded silhouettes
are already carried by their register (an evening suit reads `shine`,
heavy boots `workwear`), so only garments whose cut is the marked
thing land there. That is an observation about this colony's
wardrobe, not a property of the system. Measured live: 392 neutral,
18 femme, 3 masc.

It is a **reading, not an essence** — how this colony sees a garment,
which is culture, and culture may differ elsewhere.

### 4.2 Style-states are a tell

The clothing system already supports per-garment states (rollup /
unroll, zip / unzip). A character carries a **preferred state**, so
two souls in identical clothes read differently: sleeves permanently
shoved back past the elbow (Lin's entire silhouette), a collar up, a
jacket that is never once zipped. One attribute, applied when
dressing, and it gives PCs a habit worth mirroring.

## 5. Where a character's style comes from

- **Essential Personnel**: authored beside their blueprint wardrobe
  (Sable is `shine`, Bellows `street`+`salvage`, Nikolai/Marta
  `clinical`, Lin `workwear`+`street`). Their existing hand-written wardrobes
  stay exactly as they are — style only governs what they acquire
  *later*, so nobody's signature look is regenerated out from under
  them.
- **Generated residents**: rolled from **department** (the manifest's
  register — Life Systems leans `workwear`, Security `uniform`) and
  nudged by **traits** (Rivet-Tight prefers `salvage`, Open-Valve
  `shine`). Personality and past pick your clothes, which is exactly
  how it works for people.

  *(2026-09-11: shipped, but rolled off **role**, not department —
  `world/style.py` `ROLE_STYLES` + `roll_style`, called at arrival in
  `world/souls/population.py`. `world/manifest.py` now carries
  `DEPARTMENTS` and `department_of`, so the department signal this
  bullet describes exists and is simply not wired to style yet; the
  trait nudge is not wired either.)*
- **Players**: unset by default; a future `style` preference could
  feed shop filtering, but nothing is ever forced.

## 6. Outfit selection (how a soul dresses)

The Wardrobe need supplies the trigger; this supplies the taste.

```
1. FLOOR   — cover db.modesty. Anything wearable will do; this is the
             emergency path that already exists (the paper jumpsuit).
2. SHAPE   — fill the layer ladder: one garment per (layer, region),
             base upward, skipping layers you own nothing for.
3. TASTE   — among candidates for a slot, prefer the garment whose
             style intersects the wearer's; break ties by what they
             already own, then by cheapest.
4. WEATHER — (future) `sealed` outranks taste outdoors in bad
             weather; the toe breach and the hull-top already argue
             for this.
```

Buying follows the same order: a soul replacing the Thawn-Harrison
issue buys the cheapest garment in their own style that fills their
emptiest slot.

## 7. What this unlocks elsewhere

- **Identity**: descriptions already name people by what they wear;
  coherent style makes "the one in Boiler Run gear" a real, matchable
  handle rather than a coincidence.
- **Resleeving**: a principal in paper is *visibly not themselves*
  until they re-dress — the story beat is free once style exists.
- **Traits/designation**: both gain a visible surface. A Shift-Hound
  in `workwear` reads at a glance.
- **Tailoring / player-made clothing**: the type-keyword convention
  is precisely what makes player-authored garments safe — name it a
  coat, it layers like a coat. If a tailoring rating is ever wanted,
  it slots into the skill board then, not now.

## 8. Phasing

> **Progress note, 2026-09-11.** P1 ✅ shipped — `world/style.py`
> `RUNGS`/`derive_rung` plus `Item.layer` (#2126), with the §3
> migration run as build 090 (#2112). P2 ✅ shipped — `db.style` and
> `db.presents` derived on garments and rolled onto arrivals (#2122),
> the cast authored by build 095. P3 🔶 largely shipped — taste drives
> arrival dressing (`population.outfit_for`) and buying
> (`actions._proto_affinity`), but the wardrobe planner's own `wear`
> step in `world/souls/jobs.py` still ranks candidates by bare coverage
> then rung, with no style affinity. P4 📋 not built.

- **P1 — types**: the keyword→layer table + derivation helper, and
  the §3 migration the owner picks. No behavior change beyond correct
  layering.
- **P2 — style data**: `db.style` on garments (brand-seeded) and on
  characters (authored for Essential Personnel, rolled for generated).
- **P3 — selection**: outfit logic in the Wardrobe planner (§6 steps
  2–3), replacing "wear whatever is carried."
- **P4 — weather**: `sealed` outranking taste outdoors, once the
  weather layer wants it.

## 9. Immediate, unrelated to phasing

> **✅ DONE — note added 2026-09-11 (#2110, closed).** `vendor_lin`'s
> blueprint in `world/npcs/blueprints.py` now carries a full wardrobe
> (faded indigo work shirt, dark cotton trousers, the canvas apron and
> more), and `scripts/builds/089_dress_lin.py` put it on the woman
> already standing at the cart and cleared her wardrobe errand. The
> paragraph below describes the state before that build.

Auntie Lin's blueprint dresses her in a canvas apron and nothing else,
so she reads as undressed to the Wardrobe need and is currently
walking to Cryogenics for a paper jumpsuit. She wants clothes under
the apron regardless of which way this spec goes.
