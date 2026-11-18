# Clothing Types & Style Motifs

Two keyword vocabularies carried by the garment: TYPE, which sets a
garment's layer, and STYLE, which sets the register it is in, with
presentation as a second axis beside style. This builds on the clothing
system (coverage/layer/worn_desc, `is_wearable`), the Wardrobe need
(#2104/#2106), blueprint wardrobes, and the identity system. Traits
(NPC_TRAITS_SPEC) and designation (SKILLS_AND_DESIGNATION_SPEC) are its
natural feeders.

The vocabularies live in `world/style.py`: `RUNGS` and `derive_rung`
(type → layer, read through the `Item.layer` property in
`typeclasses/items.py`), `STYLES`, `BRAND_STYLES`, `derive_style` and
`affinity` (style), and `PRESENTATIONS` and `derive_presentation`
(presentation). `world/style.py` is the source of truth for the word
lists.

## 1. The idea

Two keyword vocabularies, both carried by the *garment* and read by
everything else:

- **TYPE** — what a garment *is* (coat, boots, apron, respirator).
  Derived from the item's NAME, so naming a thing correctly is what
  makes it behave correctly. Type determines **layer** and a default
  **coverage** (📋 UNBUILT (no issue): the default coverage; coverage
  is always authored).
- **STYLE** — what register a garment is *in* (salvage, clinical,
  lounge…). A character carries style keywords too, so **an outfit is
  a lookup, not an authored list**: match the person's style against
  the garment's.

This is the same shape the substances layer already uses — declare on
the item, match on the consumer — and it means a generated resident
can have coherent taste without anyone hand-writing their wardrobe.

## 2. Type keywords → layer

Every type keyword in the name is checked as a whole word (a plain
plural also counts). The matcher anchors a word boundary at **both**
ends (#2478/#2657), so a closed compound matches nothing unless it is
itself in the table: "trenchcoat" and "longcoat" are listed in
`RUNGS[4]` (#3425), while an unlisted compound such as "raincoat"
derives nothing, by design. A compound the table should know belongs
in the table. Names are checked longest-first so "trenchcoat" beats
"coat" and "labcoat" beats "coat". The longest matching keyword
decides the layer; if two of the same length point at different
rungs, the inner rung wins. A `layer` stored on the object (by
prototype, blueprint or builder) always beats the name. 📋 UNBUILT (no
issue): type does not supply a default coverage; coverage is always
authored.

| Layer | Register | Type keywords |
|---|---|---|
| **0 — skin** | worn under everything | bra, briefs, boxers, panties, thong, g-string, underwear, undershirt, sock, socks, stocking, stockings, tights |
| **1 — base** | the default; anything unlisted lands here | shirt, tee, t-shirt, tshirt, blouse, henley, tank, top, trousers, pants, jeans, skirt, dress, jumpsuit, leggings, suit, wig, bodysuit, slip, watch, chrono, scrubs |
| **2 — mid** | over the base, under outerwear | vest, waistcoat, hoodie, sweater, jumper, cardigan, coverall, glasses, sunglasses, shades, mirrorshades, mask, respirator, rebreather, balaclava, carrier, lenses |
| **3 — shell** | jackets and the like | jacket, windbreaker, blazer, harness, hood, slicker, cut |
| **4 — outer** | the big coats and the working over-layers | coat, labcoat, trench, overcoat, topcoat, greatcoat, duster, robe, apron, parka, bathrobe, cloak, poncho, trenchcoat, longcoat |
| **5 — carried & fastened** | accessories, worn over everything | boot, boots, shoe, shoes, sneaker, sneakers, oxford, oxfords, wader, waders, sandal, sandals, loafer, heel, heels, slipper, slippers, clog, clogs, belt, tie, necktie, scarf, shawl, bandana, bandanna, armband, badge, glove, gloves, hat, cap, helmet, choker, garter, garters, wrap, collar, earpiece, goggles |

Single words placed by issue or ruling:

- Watches are on rung 1, by owner ruling (#2433).
- Scrubs are on rung 1 (#3088).
- `coverall` is on rung 2, by the owner's ruling of 2026-09-17
  (#3610): a mid layer over a shirt and under a jacket or coat, which
  is what the `WORK_COVERALLS` prototype had said since July. It had
  been on the outer rung.

Two rules make the convention enforceable rather than advisory:

1. **Naming a garment names its layer.** Any object whose key
   contains a type keyword takes that layer unless its prototype
   states one explicitly. Player-made and generated clothing get
   correct layering for free.
2. **Unknown = layer 1.** No name match means base layer, so an
   unnamed scrap of cloth can never accidentally outrank a coat.

A few prototypes pin a layer that differs from their name's rung.
`KEPT` in `world/tests/test_prototype_layers_match_the_ladder.py`
lists them: the canvas poncho stays on 3, the kevlar vest and the
Hive-Mind Mark VII coverall on 4, and the coloured contact lenses on 1.
The test's comment calls the Hive-Mind coverall a protective over-suit
worn over everything, while `coverall` itself is rung 2 (#3610).

## 3. The layer reconciliation

The layer scale was already 0–5 but meant something else (armour
inserts on 0, boots on 3, masks sharing a layer with hoodies). The
owner picked option (a): migrate every garment onto the §2 ladder
rather than keep a parallel `garment_layer` scale or rewrite §2 to
match the old usage. `scripts/builds/090_one_ladder.py` (#2112) moves
every spawned garment onto the ladder, and the prototypes follow it
(#2741/#2464).

Armour plates were not moved to a scale of their own: they keep
`layer` 0. They are not on the ladder at all — they live in a
carrier's `plate_slots`, worn *inside* carriers rather than competing
with cloth. That was build 090's reasoning, not an owner ruling; the
recommendation had been (a) with armour separated from cloth — they
are different problems that have been sharing a number.

## 4. Style motifs (OWNER-RULED 2026-08-20)

The owner ruled the style vocabulary on 2026-08-20: seven keywords,
revealing derived, style-states as a tell, brands carrying style.

Style is a small keyword set, carried by garments as
`db.style = ["salvage", "workwear"]` and by characters the same way.
**A garment may carry several** — clothing is versatile, and a
Hive-Mind coverall is honestly `workwear` and `sealed` at once. A
garment gets several styles only from a two-style brand (Boiler Run,
Hive-Mind) or from its own `style` attribute. A brand's styles
replace the name's, so a Longhaul slicker reads `workwear` only.

A garment needs no stored style. Its style and presentation are
derived whenever they are read. Unless it carries a `style`
attribute, its brand (spotted in its name or its description)
decides; failing a brand, its name is matched against the style
keywords in the order clinical, sealed, uniform, workwear, shine,
salvage, and the first hit wins; failing that, it reads `street`.
Presentation is a separate attribute: `presentation` on a garment,
`presents` on a character.

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
  when a soul chooses what to put on. A garment in the wearer's own
  style scores 2, a `street` garment scores 1 for anyone, anything
  else 0; a garment whose presentation matches the wearer's leaning
  adds 1 (an unmarked garment matches a neutral leaning, and a wearer
  with no leaning ignores the axis). A character with no style set
  dresses as `street`.
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

📋 UNBUILT (no issue): no character carries a coverage preference;
only the modesty floor (`db.modesty`, read by
`world/souls/needs.py` `modesty_of`) exists.

### 4.2 Style-states are a tell

The clothing system already supports per-garment states (rollup /
unroll, zip / unzip). A character carries a **preferred state**, so
two souls in identical clothes read differently: sleeves permanently
shoved back past the elbow (Lin's entire silhouette), a collar up, a
jacket that is never once zipped. One attribute, applied when
dressing, and it gives PCs a habit worth mirroring.

📋 UNBUILT (no issue): no character carries a preferred garment
state, and nothing applies one when dressing.

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

A character carries `db.presents`, rolled onto every arrival in
`world/souls/population.py` (#2122).

The DATA will skew femme/neutral, because most masc-coded silhouettes
are already carried by their register (an evening suit reads `shine`,
heavy boots `workwear`), so only garments whose cut is the marked
thing land there. That is an observation about this colony's
wardrobe, not a property of the system. Measured live on 2026-08-20:
392 neutral, 18 femme, 3 masc.

It is a **reading, not an essence** — how this colony sees a garment,
which is culture, and culture may differ elsewhere.

## 5. Where a character's style comes from

- **Essential Personnel**: authored by hand, in the `CAST` table of
  `scripts/builds/095_colony_style.py` (the blueprint itself carries no
  style) (Sable is `shine`, Bellows `street`+`salvage`, Nikolai/Marta
  `clinical`, Lin `workwear`+`street`). Their existing hand-written
  wardrobes stay exactly as they are — style only governs what they
  acquire *later*, so nobody's signature look is regenerated out from
  under them. One exception: a named NPC whose blueprint leaves the
  torso, legs or feet bare gets the gap filled from the thrift rail
  (`world/souls/population.py` `ensure_outfit_complete`, #2705). That
  pick is random and ignores style and budget.
- **Generated residents**: rolled from **department** (the manifest's
  register — Life Systems leans `workwear`, Security `uniform`) and
  nudged by **traits** (Rivet-Tight prefers `salvage`, Open-Valve
  `shine`). Personality and past pick your clothes, which is exactly
  how it works for people.

  Today neither department nor traits feed style. An arrival, and a
  body made with `@spawnmob`, gets its style from
  `world/souls/population.py` `roll_person`, which calls
  `world/style.py` `roll_style` with no usable role, so the pick is a
  weighted random draw: street 5, salvage 3, workwear 3, shine 1
  (#2658). `roll_style` takes a role first when it is given one it
  knows (`ROLE_STYLES`); build 095 used that for souls that had no
  style when it ran. `world/manifest.py` `DEPARTMENTS` and
  `department_of` exist, and `roll_person` rolls a designation, but
  style reads neither. 📋 UNBUILT: style from department and the trait
  nudge.
- **Players**: unset by default; a future `style` preference could
  feed shop filtering, but nothing is ever forced.

## 6. Outfit selection (how a soul dresses)

The Wardrobe need supplies the trigger; this supplies the taste.

1. **FLOOR** — cover `db.modesty`. Anything wearable will do; this is
   the emergency path that already exists (the paper jumpsuit).
2. **SHAPE** — fill the layer ladder: one garment per (layer, region),
   base upward, skipping layers you own nothing for.
3. **TASTE** — among candidates for a slot, prefer the garment whose
   style intersects the wearer's; break ties by what they already
   own, then by cheapest.
4. **WEATHER** — (future) `sealed` outranks taste outdoors in bad
   weather; the toe breach and the hull-top already argue for this.

Arrival dressing (`world/souls/population.py` `outfit_for`) fills
three slots, torso, legs and feet, choosing by style match plus
presentation match, then the cheapest, then at random.

The wardrobe planner's own `wear` step in `world/souls/jobs.py` ranks
candidates by bare coverage, then rung, with no style affinity.

Buying works differently: from what it can afford, a soul buys the
garment that covers the most of what is still bare; among equals, the
one closest to its own style (and presentation), scored by
`actions._proto_affinity`; then the cheapest.

📋 UNBUILT (no issue): the per-(layer, region) SHAPE step, the "what
they already own" tie-break, and style in the planner's own `wear`
step (`world/souls/jobs.py`). 📋 UNBUILT (no issue): step 4, WEATHER.

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

The work still to do, in order:

- **P3 — selection**: outfit logic in the Wardrobe planner (§6 steps
  2–3), with style affinity in its `wear` step.
- **P4 — weather**: `sealed` outranking taste outdoors, once the
  weather layer wants it.

## Not decided

- The type vocabulary of §2 was put to the owner for the red pen; no
  ruling on it as a whole is recorded here. Single words have been
  ruled (watches #2433, `coverall` #3610).
