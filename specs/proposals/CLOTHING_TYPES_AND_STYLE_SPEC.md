# Clothing Types & Style Motifs

> **Status:** 📋 **PROPOSAL — owner review pending.** The type
> vocabulary (§2), the layer reconciliation (§3), and the style
> vocabulary (§4) all want the red pen. Builds on the shipped
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

A garment's name is scanned for the first matching type keyword; that
type fixes its layer and supplies default coverage when the prototype
doesn't override. Names are checked longest-first so "trenchcoat"
beats "coat" and "labcoat" beats "coat".

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

## 4. Style motifs (OWNER RED PEN)

Style is a small keyword set, carried by garments as
`db.style = ["salvage", "workwear"]` and by characters the same way.
Drawn from what the colony actually looks like:

| Keyword | Register | Reads as |
|---|---|---|
| `salvage` | scavenged, mended, mismatched | the Boot, the scrapyards, Kaspar |
| `workwear` | branded industrial kit | Longhaul, the crane, the Heat Works |
| `clinical` | medical and cryogenic whites | Maxwell, Kaspar UC, Thawn-Harrison |
| `uniform` | the chart's leftovers, service dress | constabulary, dispatch, old ship kit |
| `lounge` | going-out clothes, neon and shine | Helix, the Rook's listeners |
| `street` | everyday colony wear | Pessoa, the Brackett, most residents |
| `growers` | canvas, aprons, boots, dirt | Greenhaus, the snailery, Lin's cart |
| `sealed` | weatherproofed, respirators, slickers | the toe breach, outdoors, tox work |

Rules:

- A garment may carry **several** style keywords; a character carries
  **one or two**.
- **Brands are style carriers** (the branding law): a Longhaul
  garment is `workwear` by default, a Greenhaus one `growers`.
  Authoring a brand once gives every item under it a register.
- Style never gates *wearing* — anyone can put on anything. It only
  drives **choice**: what a soul buys, and what it puts on first.

## 5. Where a character's style comes from

- **Essential Personnel**: authored beside their blueprint wardrobe
  (Sable is `lounge`, Bellows `street`+`salvage`, Vance/Nikolai
  `clinical`, Lin `growers`). Their existing hand-written wardrobes
  stay exactly as they are — style only governs what they acquire
  *later*, so nobody's signature look is regenerated out from under
  them.
- **Generated residents**: rolled from **department** (the manifest's
  register — Life Systems leans `growers`, Security `uniform`) and
  nudged by **traits** (Rivet-Tight prefers `salvage`, Open-Valve
  `lounge`). Personality and past pick your clothes, which is exactly
  how it works for people.
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

Auntie Lin's blueprint dresses her in a canvas apron and nothing else,
so she reads as undressed to the Wardrobe need and is currently
walking to Cryogenics for a paper jumpsuit. She wants clothes under
the apron regardless of which way this spec goes.
