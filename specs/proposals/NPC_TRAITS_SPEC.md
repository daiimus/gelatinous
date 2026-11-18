# NPC Traits — personality as a cost structure

Every soul runs the same engine. A personality is two or three traits, and a
trait only reprices decisions the engine already makes. Traits live in
`world/souls/traits.py`. Their mechanics ride existing systems only: needs
(#1961), thoughts/mood (#1995), craving (#2076) and the consumption law
(#2074).

The trait names were approved by the owner on 2026-08-19: "grow these as
systems allot". The vocabulary grows over time; it is not frozen.

## 1. The idea

A **personality** is two or three traits, and a trait is nothing but a
*repricing* of decisions the engine already makes — no behavior trees, no
per-NPC code. The design steals three things and refuses their machinery:

- **RimWorld**: traits as small multipliers/gates over shared dials.
  (Refused: scripted mental breaks — ours emerge from mood, crime, and the
  bottle, with causes you can autopsy in `@soul`.)
- **CK3**: multi-trait personalities, and *stress when acting against your
  nature*. (Refused: the schemes engine.) Our stress meter is mood; guilt is
  just a heavy thought.
- **F.E.A.R.**: legibility — the same plan should *look different* on
  different souls. (Refused: nothing; poses are cheap.)

One trait is one data object with three faces, authored together so they can
never drift apart:

| Face | Consumed by | Answers |
|---|---|---|
| **dials** | planner / band tree | *when and what do I choose?* |
| **ethos** | conscience (duress rule + thoughts) | *what does it cost me?* |
| **voice** | LLM prompts + pose banks | *what do I feel like to meet?* |

## 2. Trait anatomy

The shape of one entry in the `TRAITS` registry:

```python
TRAITS = {
    "rustgut": {
        "label": "Rustgut",
        "blurb": "reaches for the bottle early",
        "dials": {"misery_pull": 0.45},
        "ethos": {"relishes": {"indulgence"}},
        "voice": ("Drink is maintenance, not weakness; you measure "
                  "days in what it takes to stay level."),
        "poses": ["turns the empty cup slowly, reading the bottom",
                  "checks the shelf behind the bar out of habit"],
        "excludes": {"dry_circuit"},
    },
}
```

A curated singleton also carries `"curated_only": True` (§6b).

Storage: `soul.db.soul_traits = ["rustgut", "dark_adapted"]` — a list of keys
into the registry. Everything else derives on read (zero-write law). A soul
with no traits has every dial at its default. **Traits are strictly
deviations from the median colonist.**

## 3. Dial vocabulary

Every key maps to a dial that already exists.

| Dial key | Existing surface | Example |
|---|---|---|
| `rate:<need>` | PROFILES rate multiplier | Ration-Burner hungers ×1.3 |
| `soft:<need>` / `crit:<need>` | SOFT/CRITICAL per-need override | Flinch-Coded safety trips at 0.70 |
| `misery_pull` | needs.MISERY_PULL override | Dry Circuit zeroes it |
| `violence_gate` | the mood gate on mug/fight plans (0.25 by default) | Hot Solder at 0.40 |
| `price_ceiling` | ware selection: `min(price)` by default | Open-Valve buys best affordable instead of cheapest |
| `schedule_affinity` | generator schedule roll weight + mood tax/glow on off-affinity shifts (📋 UNBUILT, #2771) | Dark-Adapted at night |
| `duty_lead` | shift jitter bias (early/late to post) (📋 UNBUILT, #2771) | Shift-Hound early, Clock-Ghost late |
| `venue_bias` | advertiser scoring bonus per venue tag (📋 UNBUILT, #2771) | Choir-wired souls drift shrineward |

**Resolution** (`traits.dial`): `rate:*` dials compound multiplicatively; for
every other dial the last trait in the soul's list to declare it wins. The
proposal had read override-toward-extreme for thresholds and gates; #2885
made the code match `dial()`'s own docstring, last-trait-wins, instead.

**Who reads the dials.** `actions.py` reads `price_ceiling` and
`violence_gate`; `needs.py` reads `misery_pull`, `soft:`, `crit:` and
`rate:`. The surfaces for the other three exist, but none is wired to its
dial (📋 UNBUILT, #2771): `schedule_affinity` and `duty_lead` are declared on
four traits and read by no `dial()` call site, and `venue_bias` is declared on
no trait (Greenhaus-Handed and Wire-Loved have `"dials": {}`).

## 4. Ethos — the conscience

Actions declare what they ARE: a small fixed tag vocabulary on plan branches
(data on the plan dict, not code). Traits declare `abhors` / `relishes` sets
over these tags.

| Tag | Carried by |
|---|---|
| `violence` | grapple/rob/attack steps, fight-back |
| `theft` | rob/pickpocket |
| `indulgence` | the vice run |
| `toil` | a worked shift |
| `care` | treat/restock, farm tending |
| `communion` | shrine/solace visits |
| `revelry` | lingering in a crowded venue |
| `solitude` | dwelling alone |

**Which plans carry a tag in their `ethos` key.** Six tags reach a plan:
`violence` and `theft` (the two rob plans), `revelry` (linger), `care` (the
clinic treat), `solitude` (dwell) and `toil` (the worked shift). The clinic
treat, dwell and the worked shift reach their tags by calling
`jobs._conscience` (#2708/#2904). `communion`
appears nowhere in the engine. `indulgence` is only a duress tag: the vice run
calls `_permits(soul, "craving", ("indulgence",))`, so Dry Circuit's
abhorrence gates her off the shelf until craving is CRITICAL. That branch's
plan dict declares no `ethos`, so no thought is filed for it: Rustgut's and
Open-Valve's relish never warms them, and Dry Circuit never registers the
refusal. Whether to attach these two tags or drop them is not decided (see
Not decided).

**The duress rule (one sentence):** *a plan branch whose ethos intersects the
soul's abhors set is only selectable when the driving need is CRITICAL, not
merely soft — and non-abhorred alternatives are always preferred first.*
(`actions._permits`.) A Soft-Handed soul who is hungry faults and goes to bed
hungry; the same soul *starving* finally pulls the knife. The gap between
soft and critical **is** the personality. The lawless flag is the binary
ancestor of this rule and remains the hard outer gate — traits grade
conscience *within* the lawless.

**The wound:** executing an abhorred act files a guilt thought
(`against_my_nature`) — heavy (`GUILT_WEIGHT`, −0.35) and slow-decaying (a
"wound"-class thought, half-life in days where ordinary thoughts fade in
hours), with the deed in the note ("what I did on Pessoa Street"). Relished
acts file small warm thoughts (`RELISH_WEIGHT`, +0.08, ordinary decay). Every
guilt weighs `GUILT_WEIGHT` and every relish weighs `RELISH_WEIGHT`; there
are no "mild" or "heavy" grades. No new meter: guilt flows into mood, and mood
already opens the bottle, opens the knife, and colors every LLM line. The CK3
stress-coping loop assembles itself from existing parts: *gentle soul forced
to rob → guilt → grim → misery drink (#2076) → doses accrue → addiction →
broke → the knife again* — a conscience-driven spiral, every link
inspectable in `@soul`.

## 5. Voice — the vibe (why prompting gets easier)

Each trait's `voice` is a one-sentence second-person fragment and its `poses`
a small bank of expression lines. `traits.voice_fragments(soul)` and
`traits.poses(soul)` read them; nothing calls either (📋 UNBUILT, P2, no
issue). Composition:

- **Generated souls** (📋 UNBUILT, P2, no issue): persona = joined voice
  fragments of their traits. Two or three sentences of coherent vibe, free,
  for every shuttle arrival — the generated population has no persona
  otherwise.
- **Named NPCs** (📋 UNBUILT, P2, no issue): trait fragments layer UNDER the
  bespoke persona (bespoke prose always wins conflicts); traits ground the
  planner and poses so the voice and the behavior agree (two-brain law).
- **STATE line**: unchanged shape (mood + where-and-what). Guilt reaches the
  voice two ways: it lowers the mood band the STATE line carries, and, for an
  LLM-driven NPC, it is written as a general memory ("I remember: what I did
  at <place>.") that is recalled when it is similar to the line being
  answered. The deed is not named in STATE.
- Fragments are static system-prompt material — cache-friendly, no per-turn
  cost.
- **Pose banks** (📋 UNBUILT, P2, no issue): job steps that pose (dwell,
  linger, work idle) draw from the soul's trait pose banks before the generic
  defaults — the F.E.A.R. lesson: same plan, different body language.

## 6. Trait vocabulary v1 (18 rollable + 1 curated singleton, §6b)

Register: colony slang, rust and garden both. All names are data. Names are
owner territory.

| Key | Label | Dials | Ethos | Voice (fragment) |
|---|---|---|---|---|
| `ration_burner` | Ration-Burner | hunger ×1.3, soft:hunger 0.45 | relishes toil | "Food is the one honest pleasure left; you notice everyone's plate." |
| `drip_fed` | Drip-Fed | hunger ×0.7 | — | "Eating is refueling; you stopped tasting it years ago." |
| `dark_adapted` | Dark-Adapted | night affinity, day mood tax (📋 UNBUILT, #2771: declared, read by nothing) | — | "The colony makes sense after 22:00; daylight is for other people." |
| `sunfollower` | Sunfollower | day affinity, daylight mood glow (📋 UNBUILT, #2771: declared, read by nothing) | — | "You still orient by the sun like the terraform brochures promised." |
| `dry_circuit` | Dry Circuit | misery_pull 0 | abhors indulgence | "You watched the bottle finish somebody; you drink water and remember." |
| `rustgut` | Rustgut | misery_pull 0.45 | relishes indulgence | "Drink is maintenance, not weakness; you measure days in what it takes to stay level." |
| `hot_solder` | Hot Solder | violence_gate 0.40 | relishes violence (no "mild" grade: every relish weighs `RELISH_WEIGHT`) | "Your temper arrives before your reasons do, and it usually wins." |
| `flinch_coded` | Flinch-Coded | crit:safety 0.70 | abhors violence | "You survived by leaving early; you're not ashamed of the math." |
| `plate_nerved` | Plate-Nerved | crit:safety 0.95 | — | "Panic is a luxury; you've stood in worse rooms than this one." |
| `soft_handed` | Soft-Handed | — | abhors violence + theft (no "heavy" grade: every guilt weighs `GUILT_WEIGHT`) | "You have never hurt anyone and carry that like the last clean thing." |
| `grudge_etched` | Grudge-Etched | (grudge decay slow — revenge seam) | — | "You forgive nothing; you file it, dated, and keep the file." |
| `faraday_souled` | Faraday-Souled | social ×0.7 | relishes solitude | "Crowds read you like static; alone, the signal finally clears." |
| `antenna_up` | Antenna-Up | social ×1.3 | relishes revelry | "You need the room's noise the way other people need the meal." |
| `greenhaus_handed` | Greenhaus-Handed | venue_bias farm/clinic (📋 UNBUILT, #2771: not declared, `dials` is empty) | relishes care + toil | "Things grow under your hands, and you judge the colony by what it wastes." |
| `rivet_tight` | Rivet-Tight | price_ceiling 0.5 (has no effect: the default already buys the cheapest, and only a value above 1.0 changes anything) | — | "Every token has a job; you count the till twice and trust it once." |
| `open_valve` | Open-Valve | price_ceiling: best affordable | relishes indulgence (no "mild" grade: every relish weighs `RELISH_WEIGHT`) | "Money is for spending before the colony finds a way to take it." |
| `shift_hound` | Shift-Hound | duty_lead early (📋 UNBUILT, #2771: declared, read by nothing) | relishes toil; guilt on missed shift (📋 UNBUILT, no issue) | "The shift is the spine of the day; everything else hangs off it." |
| `clock_ghost` | Clock-Ghost | duty_lead late (📋 UNBUILT, #2771: declared, read by nothing) | — (no shame in a lapse); mood tax while working (📋 UNBUILT, no issue) | "Work is a tax on being alive; you pay late and tip nothing." |

Exclusion pairs (generator-roll logic ONLY — never asserted anywhere else in
code; a soul's stored trait list is always taken as-is):
`ration_burner`×`drip_fed`, `dry_circuit`×`rustgut`, `dark_adapted`×`sunfollower`,
`flinch_coded`×`plate_nerved`, `soft_handed`×`hot_solder`,
`rivet_tight`×`open_valve`, `shift_hound`×`clock_ghost`,
`faraday_souled`×`antenna_up`.

### 6b. Curated singletons (the review fix)

Bespoke paradoxes are NOT rule-breaks — they are first-class traits with
`curated_only: True`, which the generator never rolls. No invariant is ever
violated, so no code path can trip over one.

An exception for curated exclusion pairs was proposed first; review flagged it
as a code issue waiting to happen, and curated-only singletons replaced it.
The founding example replaces the Rook's forbidden pair:

| Key | Label | Dials | Ethos | Voice |
|---|---|---|---|---|
| `wire_loved` | Wire-Loved | none (proposed: social ×1.0, satisfied only via mediated fixtures — the airwaves advertise to it) | relishes solitude and communion (no plan carries `communion`, §4, so only solitude is felt) | "You love the whole colony at once and cannot bear it one person at a time." |

The vocabulary grows this way: when a character needs a contradiction, author
the contradiction as its own trait.

### 6c. Defects: a machine's traits

A machine does not roll traits (#2136). `registry_for` gives it a separate
vocabulary, `DEFECTS` (eight, in `world/souls/traits.py`), with the same three
faces. A unit earns a defect when its `maintenance` need comes due: one per
overdue service (`engine._wear_and_tear`, through `traits.acquire_defect`), up
to `DEFECT_CAP` (3). A service takes the newest one back out
(`traits.clear_defect`, from the dwell step in `jobs.py` when the need is
`maintenance`). Build 099 (`scripts/builds/099_traits.py`) clears any human
traits from a machine.

## 7. Generator integration

Every shuttle arrival rolls **two or three traits** (two three times as
often), never a curated one, uniform over the vocabulary minus exclusions of
already-rolled traits (`traits.roll`). Rolls seed identity, not story: the
arrival's schedule preference, first venue, and voice all fall out of the
same roll (📋 UNBUILT: schedule and venue #2771; voice is P2, §10, no issue).
Existing generated souls get a one-time backfill roll (build script).

## 8. Engine integration points

- `world/souls/traits.py`: the registry, and derive-on-read readers —
  `traits_of`, `dial(soul, key, default)`, `ethos`, `abhors`, `relishes`,
  `voice_fragments`, `poses`, `labels`, `roll`; for machines `registry_for`,
  `acquire_defect`, `clear_defect`.
- `needs.py`: rate/threshold lookups consult `traits.dial`.
- `actions.py`: duress rule at abhorred branches (`_permits`); price_ceiling
  in ware selection; venue_bias in advertiser scoring (📋 UNBUILT, #2771).
- `jobs.py`: guilt/relish thoughts on tagged step completion
  (`_conscience`); trait pose banks before generic poses (📋 UNBUILT, P2, no
  issue).
- `engine.py`: schedule affinity mood tax/glow (one thought-class)
  (📋 UNBUILT, #2771).
- `llm_npc.py` / `prompt.py`: persona composition per §5 (📋 UNBUILT, P2, no
  issue).
- `CmdSoul`: traits on the individual card; dashboard counts unchanged.

## 9. Named-NPC assignments (PROPOSED — owner approves each)

`scripts/builds/099_traits.py` applies these rows, except Ossie's.

| NPC | Proposed traits | Why |
|---|---|---|
| Bellows | Rivet-Tight + Plate-Nerved | counts the vice till, unbothered by the clientele |
| Sable | Antenna-Up + Dry Circuit | needs the room, never touches the shelf |
| Sully | Rustgut + Open-Valve | the hull-slab bar runs on his own custom |
| Del | Dark-Adapted + Faraday-Souled | night bar, few words |
| Lin | Shift-Hound + Rivet-Tight | day-only cart, exact change |
| Ottilie | Ration-Burner + Shift-Hound | the butcher eats her own cooking |
| Nikolai | Greenhaus-Handed + Plate-Nerved | steady hands, judges waste |
| Petra | Plate-Nerved + Dark-Adapted | dispatch nights don't rattle her |
| Marta | Greenhaus-Handed + Dark-Adapted | the urgent-care doctor who takes the quiet shift |
| Ezra | Rivet-Tight + Grudge-Etched | the pawn counter's memory — remembers every face that tried it on |
| Ossie | Hot Solder + Shift-Hound | crane radio manners |
| The Rook | Wire-Loved (curated singleton, §6b) | loves the crowd through the wire, can't stand the room — the paradox is authored as its own trait, not a rule-break |

## 10. Phasing

- **P2 — the vibe** (📋 UNBUILT, no issue): voice composition into
  generated-soul personas + named-NPC layering; trait pose banks on
  dwell/linger/work. `traits.voice_fragments()` and `traits.poses()` have no
  caller, so no trait voice reaches a persona and no trait pose reaches the
  dwell/linger/work steps.
- **P3 — curation**: any vocabulary additions the first live week suggests.

## 11. Deferred seams (deliberate)

- **Background/history** (owner: "can come in time"): a future `origin`
  layer — where the sleeve came from, what the shuttle manifest said —
  composing into voice the same way traits do. The trait object's shape
  (dials/ethos/voice) is the template for it. The pre-planetfall designation
  (SKILLS_AND_DESIGNATION_SPEC) is the first tenant of this seam.
- **Relationships/ties**: per-pair weights (Sims/CK3 opinion) — the substrate
  revenge and grief want; sequenced after the owner's memory-distortion
  conversation. Per-person opinion exists (§12, #2388); NPC-to-NPC ties and
  trait repricing of opinion stay deferred (§13).
- **Grudge-Etched's dial** is a forward reference to that revenge work; the
  trait is voice and pose only (its `ethos` is empty).

## 12. Opinion — the same feeling, pointed at a person

Mechanism only (#2388). Nothing gates on it yet, deliberately — see the
balance note below.

Mood is what a soul thinks of its life. **Opinion is what it thinks of
*you*.** Both are the clamped, half-life-decayed sum of things that actually
happened, derived on read, and both run through one decay rule
(`thoughts._weight`) so a grudge and a bad mood cannot age at different rates.

In `world/souls/thoughts.py`: `opinion_of(soul, uid)` is a value from −1.0 to
+1.0, derived, never stored; `opinion_band(value)` names it warm / friendly /
neutral / wary / hostile; `opinion_note(soul, uid)` is the strongest surviving
REASON, for a voice to cite. `add_opinion` records an event.

**Why its own attribute** (`soul_opinions`, not the shared `soul_thoughts`):
that log is capped at 20 entries for the soul's *own* life, and `STACK_CAP`
dedupes on event key alone. Sharing it meant a bartender who met a dozen
patrons in a night would evict her own payday and hunger to make room for
acquaintances — sociability would quietly degrade mood — and person A being
"generous" would evict person B being generous. Per-person storage fixes both.
Caps: 3 per key per person, 6 entries per person, 24 acquaintances, evicting
the least-recently-*felt-about* rather than the oldest.

**A memory wipe takes it** (owner ruling 2026-11-16, #3851): an NPC made to
forget somebody loses its read on them, whatever its traits. `grudge_etched`
is a voice line and a pose today; the slower fade the §6 table proposes for it
is not built, and would be about fading, not about a wipe. The mood share
below stays. See `NPC_MEMORY_AND_IDENTITY_SPEC.md` §5b.

**Mood coupling** (owner ruling 2026-08-29): an interpersonal event moves
opinion at full weight and mood at `MOOD_SHARE` of it. Being robbed at
knifepoint should dent your day, not merely your view of the robber. Pass
`mood_share=0` for something genuinely only about that person.

**No `feel` tool.** The engine scores the relationship and the voice is
*handed* the answer, reasons included, so an NPC narrates the grievance it
actually has. The read on a person is never free text the MODEL writes and the
game stores and reads back: that inverts platform law 4, and a real mechanic
(trust/consent) consulting it would depend on a model's word choice. Existing
`llm_dossiers[uid]["valence"]` strings are inert, left in place as a readable
record of the transition.

**Traits reprice it.** A trait modulates how far a given event moves opinion —
the same repricing idea as §1, pointed at relationships instead of tasks. Not
built yet; the seam is `add_opinion`'s valence argument.

### Balance prerequisite — READ BEFORE WIRING A CONSUMER

Opinion is something souls **have** before it is something that **decides**
anything. Producers only: courtesy (`+0.08`) and being attacked (`-0.60`, a
wound). No system in the colony has been balance-tuned, and gating service,
prices, trust grants or dialogue on an untuned score is how you get a colony
that hates everybody. **Tune the producers against real play first**, then
wire consumers one at a time.

## 13. The gap: these traits are mechanics, not personality

Owner observation, 2026-08-29: *"the traits we have are neat and inform
mechanics but not really personality."* Correct, and the vocabulary shows it.
Every dial the 19 traits turn is needs-facing: `rate:hunger`, `soft:hunger`,
`schedule_affinity`, `misery_pull`, `crit:safety`, `rate:social`,
`price_ceiling`, `duty_lead`, `violence_gate`.

Nine dials, and **not one points at another person.** They tune appetite,
timetable and spending — what a soul consumes and when, never how it treats
anybody. The ethos tags come closer, but they fire only *reflexively*, on the
soul's own deeds via `against_my_nature`: Soft-Handed feels guilt when SHE
hurts someone and forms no stronger view of a stranger who does it in front of
her.

The tell is in §6. **Grudge-Etched is the only real personality trait in the
list, and its dial is not implemented** — `(grudge decay slow — revenge
seam)`, parenthesised. (It is not the only unwired dial: `schedule_affinity`,
`duty_lead` and `venue_bias` are not wired either, #2771; §3.) It had nowhere
to land, because the thing it needed to modify did not exist. It exists now
(§12). The missing piece is a **temperament axis** whose dials point at
people:

1. **Trait weights the event** — Callous discounts courtesy; Grudge-Etched
   slows decay on slights (that is `_weight`'s wound half-life, made
   per-trait). One argument in `add_opinion`.
2. **Trait meets trait** — two souls whose ethos opposes seed a standing
   opinion on sight. This is what makes NPC-to-NPC society legible with no
   authoring.
3. **Acting against nature** — exists: the guilt thought of §4.

Vocabulary gaps to name when it is drafted: honesty, warmth/cruelty,
generosity *toward others* (Open-Valve is about spending on yourself), pride,
and trust/suspicion. Forgiveness is half-covered by Grudge-Etched having no
opposite.

**Blocked on §12's balance prerequisite**, not on design: temperament traits
are consumers of opinion, and opinion has two untuned producers and no play
data behind them. Names are owner territory (§6 convention) — draft as
placeholders expecting the red pen.

## Unbuilt

Each item is described where it stands:

- `schedule_affinity`, `duty_lead`, `venue_bias` wired to their surfaces
  (📋 UNBUILT, #2771) — §3, §6, §7, §8.
- Guilt on a missed shift for Shift-Hound; mood tax while working for
  Clock-Ghost (📋 UNBUILT, no issue) — §6.
- P2, the vibe: trait voice into personas, trait pose banks (📋 UNBUILT, P2,
  no issue) — §5, §8, §10.

## Not decided

- **`communion` and `indulgence` as plan ethos tags.** No plan carries
  `communion`, and the vice run carries `indulgence` only as a duress tag, so
  neither files a thought (§4). The fix for #2708 left both explicitly
  undecided — "attach them or drop them from the vocabulary" — and nothing
  open tracks it.

## Related

- `NPC_MEMORY_AND_IDENTITY_SPEC.md` §5b — the memory wipe and opinion.
- `SKILLS_AND_DESIGNATION_SPEC` — the pre-planetfall designation, the first
  tenant of the §11 background seam.
