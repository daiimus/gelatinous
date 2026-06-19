# Capacity Consumers & Perception Spec

> **Status: 📋 PROPOSAL — design-of-record, not implemented.** Captures an
> in-progress design conversation. Built in layers (see §8). The four core
> capacities — `sight`, `hearing`/voice, `manipulation`, `moving` — are
> designed below; the remaining capacities are blocked on absent systems
> (§2). Magnitudes and balance numbers are illustrative, not final.

## 0 · Purpose

The body-capacity system (`world/medical/core.py` → `calculate_body_capacity`,
species `body_capacities` tables) computes a rich set of `0.0–1.0` capacity
floors from organ health — but today only the **lethal** capacities
(`blood_pumping`/`breathing`/`digestion`/`neck_integrity`) and `consciousness`
are *consumed* (death + unconscious gates). The "performance" capacities
(`sight`, `hearing`, `moving`, `manipulation`, `talking`, `eating`,
`blood_filtration`) are computed but **inert** — a wrecked arm aims as well as
a healthy one, a blown leg doesn't slow you, blinded eyes don't hurt ranged.

This spec defines how those capacities drive gameplay — the "graduated
consequence layer" between *fine* and *dead/unconscious*.

## 1 · Core model (decided)

- **Multiplicative, not flat.** A capacity *modifies the GRIM-derived result*
  (e.g. ranged precision = `motorics×0.7 + intellect×0.3`, then `× sight`),
  so injury scales a character down from *their own* baseline rather than
  applying everyone the same flat penalty. "You're at 60% of your normal self."
- **Suppressible effect registry — the integration seam.** Each capacity→effect
  mapping is a **named effect** that a condition or augment ability can
  *suppress or modify independently*. The consumer reads the capacity + the
  effect registry; cyberware/biotech reach in and modify *the effect*, never
  the capacity. (Example: a blindsight augment nulls the `sight→melee_penalty`
  effect without touching ranged.) This is the home for the
  cyberware/biotech/condition integration; it rides the existing condition
  system (conditions already contribute pain/blood/consciousness via
  `get_*_contribution` — an effect-suppression contribution is the same shape).
- **Hybrid curve.** Graduated (smooth scaling with the capacity value) *with
  hard floors* at incapacitation thresholds (e.g. `moving < 0.15` = can't move).
  Smooth degradation everywhere, dramatic cliffs only where the body table
  declares an incapacitation threshold.
- **Steeper-than-linear where redundancy exists.** Paired/multiple organs
  (two eyes, two ears, future extra appendages) mean losing the *second* of a
  pair should hurt more than the first (one eye = depth-perception loss, worse
  for ranged than a flat `0.5`). Future-proofs characters with *more* than the
  baseline (extra eyes/ears/arms).
- **One capacity, many consumers.** A capacity is an *input* feeding multiple
  independent consumer systems (combat, identity recognition, the LOOK
  renderer). "It's all connected."
- **Setting-agnostic, cyberpunk-themed.** Crippling injury is remediated by a
  **chrome augment OR a harvested-organ transplant** — both RipperDoc work,
  chrome and wetwork side by side (a cyber kidney *and* a donor kidney both
  restore `blood_filtration`). Capacity-loss and cyberware/biotech/transplant
  are **separate systems that integrate**, not one baked into the other. A
  grimdark reskin would relabel the flavor, not the mechanics.

## 2 · Wireable now vs blocked

A capacity effect only lands if a *consumer system* exists.

| Capacity | Real consumers (this spec) | Status |
|---|---|---|
| `sight` | combat (ranged/melee), identity recognition, LOOK visual layer | wireable now |
| `hearing` | LOOK auditory layer, **voice recognition**, acoustic/flashbang conditions | wireable now |
| `manipulation` | weapon handling (per-effector resolver) | now — needs resolver (§6) |
| `moving` | movement / flee / future jump-athletics (per-effector resolver) | now — needs resolver (§6) |
| `talking` | **voice production** (the voice triangle, §4); social/negotiation (resonance-gated) | production now; social **system-blocked, NOT skill-blocked** |
| `blood_filtration` | infection resistance (existing `InfectionCondition`) | wireable now |
| `eating` | **consumption benefit** (existing consume pipeline; buff model, no hunger) | wireable once the food/drink buff exists; rides delivery tags |
| `hearing`→trade, `*`→work_speed | trade price, crafting/work | blocked (no trade/work system); **drop the `hearing→trade` vestige** |

### 2.1 · Blocked-capacity shapes (pin the shape so future system-builders snap in correctly)

- **`talking` → social.** Voice *production* is designed (§4): jaw/tongue damage
  garbles output and the garble is legible on the voice channel. The blocked
  piece is the *social consumer* — and it is **NOT skill-blocked**. It rides
  **resonance** (the R in GRIM, which exists) the way aim rides motorics:
  a future `persuade`/`negotiate`/`intimidate` action declares `talking` as a
  consumed capacity → `resonance × talking → social result`. Skills, if/when
  they land, only *refine* this. Blocked solely on the **social-action system**
  (the verbs + the gig/favor/rep loop).
- **`eating` → consumption benefit.** **Not blocked** — it rides the *existing*
  consumption pipeline (`CmdConsumption`, delivery-method tags). **No hunger /
  no deprivation penalty** (a hunger grind cuts against the favor+gear+rep,
  squishy-by-design direction). Instead a **buff model**: consuming food/drink
  confers a positive effect; not consuming is merely neutral. The `eating`
  capacity (jaw/tongue/teeth/gut) **scales the magnitude of that benefit** and
  **gates delivery**: a wrecked mouth falls back solid → liquid → IV — exactly
  the delivery-tag seam the CmdConsumption migration already wants. Remediation:
  feeding tube / cyber-stomach / IV. Buildable once the food/drink buff itself
  exists; the capacity hook is trivial on top of it.
- **`*` → work_speed.** Declared on `sight` + `manipulation`. Genuinely blocked
  on a general crafting/work system. *Natural first hook when we do wire it:* the
  **operate/surgery** flow (it is already a "work" action) — a one-eyed,
  low-`manipulation` surgeon is measurably worse (slower, higher complication
  chance). Noted, not built; surgery stays unscaled until we choose to open this.
- **`hearing` → trade.** A RimWorld seed vestige ("hearing affects haggling").
  Thematically weak; hearing's real consumers are perception (§5), voice-recog
  (§4), and acoustic hazards. **Drop / re-scope** rather than honor. If anything
  ever gates negotiation it is `talking`, not `hearing`.

## 3 · Sight (worked example — decided)

**Organs:** `left_eye` + `right_eye`, 0.5 each → `1.0` (both) / `0.5` (one eye)
/ `0.0` (blind). It is **whole-body** — you don't *wield* eyes — so it dodges
the effector resolver and is the clean first slice to prove the model.

**Consumers:**
- **Combat — ranged (the big one):** multiplicative, **steeper-than-linear**
  falloff. Both eyes = no penalty; one eye ≈ `0.6–0.7` effective (depth
  perception gone — worse than linear `0.5`); blind ≈ point-blank-or-nothing.
- **Combat — melee (light):** small penalty only when fully blind (you can
  still grab and swing); zero with one eye.
- **Identity recognition:** low sight gates *visual* recognition; losing it
  shifts recognition to the **voice channel** (§4), not to anonymity.
- **LOOK renderer:** gates the *visual* sensory category (§5); losing it drops
  visual and **enriches** the remaining senses (compensatory).

**Augment hook:** a cyber sense-enhancer is a single suppress-modifier across
*all* layers at once — nulls the melee penalty, restores visual-ID (or grants
a chrome-recognition channel), tells the renderer "treat visual as present."
One augment, coherent everywhere — the integration paying off.

## 4 · Hearing & Voice (decided)

**Organs:** `left_ear` + `right_ear`, 0.5 each → both / one-ear (`0.5`, mono)
/ deaf (`0.0`). A **perception + identity** capacity, not a combat one. (The
species table's only declared `affects` is `trade_price` — blocked — so it's a
placeholder; the real consumers are below.)

### 4.1 Consumers
- **LOOK auditory layer:** `hearing` gates whether you receive the auditory
  sensory category; deaf → it drops, others enrich.
- **Voice recognition (the centerpiece):** a parallel identity channel — hear a
  *known voice* → recognize the speaker even when you can't see them.
- **Acoustic / flashbang:** not the combat loop. A **flashbang → temporary
  deafness condition** is buildable now (grenades + condition system → a
  time-limited hearing-suppression condition). The broader acoustic-event layer
  (gunshots/explosions/shouting experienced differently by the deaf) is future.

### 4.2 Voice mirrors the visual identity stack
| Visual (exists) | Voice (new, parallel) |
|---|---|
| sdesc | **vocal description + ending** |
| apparent UID (visual signature) | **voice signature** |
| recognition memory → assign a name | **voice memory** → assign a name |
| `describe keyword` | **`@voice`** (+ expanded `describe` menu) |
| visual disguise / mask | **voice modulator** (cyber) |

Reuses the IDENTITY_RECOGNITION pipeline as a *second axis* — not a new system.

### 4.3 The `@voice` system
A player assigns their **vocal description** (the color: "gravelly baritone")
plus an **ending** (the grammatical cap: drawl / rasp / lilt / cadence / …) —
both **curated** (a bounded vocabulary, like visual keywords; not free garbage).
Set via an expanded `describe` menu *and* a fast `@voice` path. That pair *is*
the voice signature others silently remember and name.

### 4.4 Speech rendering
`Bob says, *speaking Common, in a gravelly baritone drawl* "My name's Robert."`
- `*…*` = voice flavor; `<language>` slot present-but-always-`Common` (languages
  are future, the slot is future-proofed).

### 4.5 The resolution chain (core mechanic)
"Who said it" resolves by channel, gated by the *listener's* capacities:
1. **Can see the speaker** (`sight`) → name if known, else visual sdesc.
2. **Can't see, can hear** (`hearing`) → name if the *voice* is known, else the
   voice descriptor ("A gravelly baritone drawl says…").
3. **Neither** → "someone."

A mask defeats channel 1, not 2; a voice modulator defeats channel 2; blindness
drops you to 2; deafness removes 2. This chain is the payoff of the whole
sight+hearing design.

### 4.6 Rendering heuristic (decided — "polite, contextual")
The voice cue renders when it carries **attribution value**, with a light
**flavor** sprinkle otherwise. Per listener per utterance:
- **Can't see + 2+ distinct unseen voices in earshot** → **always** render
  (mandatory disambiguation — attribution beats politeness under ambiguity).
- **Can't see + a new/unestablished voice** → render (introduce it).
- **Can't see + single, already-established voice** → relaxed (occasional
  reinforcement; "introduce once then ambient", per-listener scene-memory that
  decays on scene change).
- **Can see the speaker** → **sporadic, low-frequency flavor only** (keeps
  voices alive for everyone, not just the blind; reads as flavor, not noise).

Driven by two inputs: `sight` (can the listener see the speaker) and the
**count of distinct unseen voices currently in earshot**.

### 4.7 The talking ↔ hearing ↔ identity triangle
Voice recognition needs both ends, tying three capacities + three augments:
- **Speaker's `talking`** (jaw/tongue) → can they produce a recognizable voice
  at all (wrecked jaw → no usable signature). Restored by **CYBER_JAW** (built).
- **Listener's `hearing`** → can they receive it (cyber ears restore).
- **Voice modulator** → disguises the signature (anonymize v1; *mimic a specific
  voice* later, integrated with the existing `impersonate` disguise command).
- Three sides, three chrome answers. This wires `talking` (otherwise blocked on
  social) into something concrete now.

### 4.8 Deferred
- **One-ear directionality** (mono = can't localize) is a steeper-than-linear
  hook reserved for when the **proximity** system lands; no directional consumer
  in v1.

## 5 · Perception & the five-senses framework (anchor, don't reinvent)

`LOOK_COMMAND_SPEC.md` → **"Sensory Category Framework"** already defines the
categories (**Visual / Auditory / Olfactory / Tactile / Atmospheric**), graceful
degradation ("categories with no content simply don't display"), and explicitly:
*"Medical Condition Support: By design — players with sensory limitations see
reduced content."* Weather + crowd contributions already ship as
sense-categorized message pools. **The framework was built to consume sensory
limitation; this spec supplies the input.**

- **Capacities are the input.** The renderer reads the looker's `sight`/`hearing`
  capacities to decide which categories they receive and at what richness.
- **Compensatory enrichment (decided):** lose a sense and the others get
  *dynamically richer* (the renderer re-weights / a blind person's sound-desc
  carries more detail) — an *enhancement* on top of the existing graceful
  degradation, chosen for storytelling and to support the deliberately
  squishy/vulnerable player.
- **Graceful start:** current single-blob room descs stay valid as the *visual*
  layer; other-sense components are additive. Full **base-desc sense
  decomposition** is the future authoring lift, not a prerequisite.

## 6 · Manipulation & Moving — the per-effector resolver (decided)

Unlike `sight`/`hearing` (whole-body), these route through a shared
**effector resolver** — `resolve_effectors(character, action)` → returns
**(a) the effective capacity for the action** and **(b) meta-bonuses from
surplus effectors**, both measured against the **species baseline** derived
*dynamically* from anatomy (§6.3). An action declares the effectors it needs
(weapon `hands_required`; locomotion; future jump/athletics → legs).

### 6.1 Manipulation — two distinct outputs

Damage/loss of arm-hand anatomy answers two *separate* questions; conflating
them into one body-wide number is wrong.

- **(Q1) Handling — from the *specific gripping effector(s)* only.** Weapon
  accuracy depends on the hand(s) actually holding it, NOT a body average. A
  one-armed character with a pistol in their good hand fights at **full**
  accuracy — the missing arm is irrelevant to that weapon. (Body-wide
  manipulation ≈ `0.5` for one arm would wrongly halve it.)
- **(Q2) Breadth / readiness — from the *count of functional manipulators vs
  baseline*.** Buys breadth, not accuracy: **initiative + hard-to-fully-disarm
  + loadout-readiness** (a grenade *and* a 2H melee *and* a pistol all ready at
  once). NOT extra attacks or raw damage (combat-balance guardrail). *Which*
  readied option to bring to bear when is a future combat revision.

So: one-armed → full per-weapon accuracy, reduced breadth; four-armed → same
per-weapon accuracy, large breadth (multiple weapons up, near-undisarmable,
faster initiative).

**Minimum requirements + scaled penalty.** A weapon's `hands_required` is a
*minimum*; the gripping effectors must meet it. **Under-gripping** (2H weapon
held one-handed, no free second hand) is a **scaled** handling penalty, not a
flat tier. Combining multiple gripping hands on one weapon scales handling
(the weaker hand drags it — exact min-vs-blend TBD, §10).

**Effector targeting already exists.** `wield <item> in <hand>` is implemented
and matches the slot by name (`wield baton in left`); since the `hands` view
*is* the grasping-slot set (prehensile tail included), `wield pistol in tail`
works the moment the slot exists. Switching/choosing weapon effectors is
already supported — no new command needed.

### 6.2 Moving — aggregate, species-normalized

You don't *pick a leg* to move with, so `moving` is the **whole locomotion
apparatus**, normalized to species baseline (human losing 1 of 2 legs ≫ rat
losing 1 of 4 — already species-aware via `get_species_body_capacities`).
Drives: **dodge** (combat defense), **flee**, **movement speed**, and **future
jump/athletics**. Hard floor at the table's `0.15` incapacitation_threshold =
can't locomote (drag yourself).

### 6.3 The combat capacity stack (multiplicative)

Capacities *modify* the GRIM-derived result. Offense rides arms+eyes; defense
rides legs:

| Action | Stack |
|---|---|
| Ranged hit | `motorics-precision × sight × manipulation(trigger hand)` |
| Melee hit | `motorics-precision × manipulation(wielding hand) × light-sight` |
| Dodge / evasion | `motorics × moving` |

### 6.4 Dynamic baseline derivation

Baseline effector counts come straight from anatomy — count **grasping
organs** (manipulation) / **locomotion organs** (moving) per species. New
species, extra appendages, and cyberware are auto-counted; nothing hardcoded.
Builds on existing pieces: weapon `hands_required`, the `hands` grasping-slot
system, species anatomy tables.

## 7 · Blood filtration & condition-driven appearance (chronic/metabolic)

**Organs:** `left_kidney` + `right_kidney`, 0.5 each. The first consumer that's
neither combat nor perception — it modifies a **chronic condition over time**,
proving the model spans the medical sim too.

### 7.1 Infection resistance (v1 — wireable now)
`blood_filtration` is a **physiological multiplier parallel to
`InfectionCondition.environmental_modifier`** — failing kidneys make an
infection you *already have* worsen faster and clear slower:
- worsen-hazard `×` filtration factor (low filtration → faster progression),
- treated-heal rate `×` filtration (low filtration → it lingers despite treatment).

**Not acquisition** — kidneys don't stop you *catching* an infection (wound care
+ the environmental modifier do that); they govern how your body *fights one
off*. `disease_resistance` = "how you process an infection," not "whether you
catch one." Slots straight into the existing multiplier.

### 7.2 Renal failure (buildable on the chronic-conditions substrate)
Total kidney loss (filtration `0`) → a **RenalFailure** chronic condition,
realizing the table's declared-but-unenforced `total_loss_fatal` *and* the
`blood_filtration → consciousness` modifier that `update_vital_signs` doesn't
apply today. Effects: consciousness suppression + slow death, **and its
signature — a visible skin-pigment shift** (sallow / uremic / ashen). Rides the
chronic-conditions substrate (parallel to the parked ischemia clock).

### 7.3 Condition-driven appearance symptoms (cross-cutting hook)
Renal failure's pigment shift generalizes: **conditions can carry visible
symptoms** that tint the rendered skintone / appearance (layered on the existing
skintone system), legible to `look`, diagnosis, observers, *and* other systems.
The body's state becomes **legible at a glance** — a RipperDoc reads you across
the room; players see the sick one without a `diagnose`. The same hook yields
**cyanosis** (low `breathing` → blue lips), **jaundice** (liver), **pallor**
(blood loss). And conditions are **first-class signals other systems extrapolate
from**: a toxin substance can trigger/worsen renal failure, diagnosis surfaces
it, another condition compounds it.

### 7.4 Remediation = chrome OR transplant (RipperDoc)
Per §1: a **cyber kidney** *and* a **transplanted donor kidney** (harvested
organ, canonical name → capacity auto-restores) both fix filtration — the
general remediation principle for *any* capacity-restoring augment, not kidney-
specific. A dialysis implant/consumable is the future non-chrome, non-transplant
stopgap.

## 8 · Capacity → consumer matrix (summary)

See §2. Build cost ascends: combat hooks (cheap, multiplicative) → identity/voice
(reuse pipeline) → perception render (framework exists; base-desc decomposition
is the content lift) → per-effector resolver (manipulation/moving).

## 9 · Build sequencing (layered)

1. **Combat consumers** (`sight`→ranged/melee) — proves multiplicative +
   suppressible-effect pattern on a whole-body capacity. **✅ SHIPPED** —
   `world/combat/capacity.py` `sight_hit_factor()` multiplies the attacker's
   motorics term in `world/combat/attack.py` `process_attack`; piecewise curves
   (ranged steep, melee light), `sight_override` condition suppresses the
   penalty (the chrome seam — augment not built yet). Tests:
   `world/tests/test_combat_capacity_sight.py`.
2. **Identity / voice** — `@voice` + voice signature + the resolution chain +
   rendering heuristic; gates visual recognition on `sight`, voice on `hearing`.
   **✅ CORE SHIPPED (2a/2b/2c/2d).** Deferred: voice-descriptor-as-identity +
   §4.6 multi-voice disambiguation.
   - **2d ✅ SHIPPED — deaf audio gating.** Hearing gates speech *content*, not
     just attribution. `say`: a deaf+sighted listener sees "{name} says
     something you can't make out"; deaf+blind is suppressed entirely.
     Poses/emotes: `world/emote.py` `process_speech` redacts quoted speech to
     `"..."` for a deaf observer (both `render_dot_pose` and the traditional
     `render_emote` now route through it); the visible action still shows
     (visual gating is layer 3). Whisper to a deaf target is redacted too. The
     speaker always reads their own words. Tests in `test_emote.py`.
   - **2a ✅ SHIPPED — voice signature foundation.** `world/voice.py`: curated
     description+ending vocabulary (config-overridable), composer
     (`voice_phrase`), and the **`talking`-capacity garble gate** (§4.7 — first
     consumer of the otherwise-blocked `talking` capacity: wrecked jaw →
     `garbled_voice_phrase`). `@voice` command (`commands/CmdCharacter.py`,
     set/view/list/clear). `say` renders flavour: garble always, otherwise the
     §4.6 "can-see → sporadic sprinkle" branch (the only branch reachable until
     2c). Tests: `world/tests/test_voice_identity.py`.
   - **2b ✅ SHIPPED — voice memory + recognition.** The apparent-UID /
     `recognition_memory` parallel in `world/voice.py`: `get_voice_signature`
     (salted on `sleeve_uid`, so everyone has a stable recognisable voice + a
     `voice_modulator_active` slot that, like a mask, changes the UID),
     `get_apparent_voice_uid`, and a `voice_memory` AttributeProperty on the
     Character with `remember_voice`/`forget_voice`/`get_assigned_voice_name`.
     `remember <target>`/`forget <target>` now teach/clear the voice alongside
     the face (skipping garbled speakers). Tests in `test_voice_identity.py`.
     *Not yet consumed by display* — that's 2c.
   - **2c ✅ SHIPPED — the resolution chain.** `resolve_speaker_attribution`
     (`world/voice.py`) gates speech attribution on the *listener's* capacities:
     **can-see → display name; can't-see-but-hear → voice discernment; neither →
     "someone."** `can_see`/`can_hear` read `sight`/`hearing` (override-condition
     seams for chrome eyes/ears). **Discerning a voice is always a determination**
     mirroring disguise piercing: `attempt_voice_discern` runs opposed
     Intellect-vs-Resonance, familiarity buff, modulator penalty, **weighted by
     the listener's `hearing` capacity** (the consumer — `hearing` finally lands),
     cached per presentation; forget invalidates it. **Decided simplification:**
     an unrecognised/undiscerned voice is *not* attributed (no descriptor) — it
     renders as "someone"; the voice-descriptor-as-identity ("a gravelly drawl
     says…") and the §4.6 multi-voice disambiguation are **deferred**. Wired into
     `say` (per-observer; 2a flavour now confined to the can-see branch). Tests in
     `test_voice_identity.py`. **Headline payoff live: a blind listener recognises
     a known voice; a stranger's stays "someone."**
3. **Perception render** — capacities gate LOOK sensory categories + compensatory
   enrichment. **✅ CORE SHIPPED.** `world/perception.py` (`blocked_senses` /
   `can_perceive_sense` / `has_reduced_perception`) reads `sight`→visual,
   `hearing`→auditory from the voice-layer primitives (chrome override seams
   honoured); olfactory/tactile/atmospheric never gated. The weather + crowd
   ambient pools (`get_sensory_messages`, `get_crowd_contributions`) now drop
   content the looker can't perceive (blind → no visual weather/crowd; deaf →
   no auditory), and a sense-reduced looker gets a **+1 compensatory** ambient
   message. Tests: `world/tests/test_perception.py`. **Deferred (spec §5,
   accepted):** base single-blob room-desc sense decomposition — the visual
   layer stays whole for now; gating the additive pools is the buildable slice.
4. **Per-effector resolver** — `manipulation`/`moving` (and the multi-appendage
   future). **✅ CORE SHIPPED (4a/4b).** Deferred: Q2 breadth meta-bonuses
   (surplus-appendage initiative / disarm-resist / loadout) — a future combat
   revision.
   - **4a ✅ SHIPPED — `moving` → dodge (defensive half).** `world/combat/
     capacity.py` `moving_dodge_factor` multiplies the *target's* motorics in
     `attack.py` (dodge = motorics × moving). Whole-body, species-normalized
     (§6.2 — you don't pick a leg); hard floor at the table's 0.15
     incapacitation_threshold collapses evasion to a flail; `moving_override`
     chrome-legs seam. Tests in `test_combat_capacity_sight.py`.
   - **4b ✅ SHIPPED — `manipulation` → hit (per-effector, offensive half).**
     `MedicalState.calculate_capacity_scoped(capacity, containers)` computes a
     capacity from only one limb's organs (the contribution math is extracted
     into `_resolve_capacity_contribution`, shared with the body-wide method).
     `world/combat/capacity.py` `manipulation_hit_factor(attacker, weapon)` finds
     the gripping slot(s) from `attacker.hands`, inverts `limb_downstream_chain`
     to the hand's limb organs, and scopes manipulation there — so a one-armed
     shooter with a good hand fights at **full** accuracy (Q1 isolation, tested).
     Two-handed grips take the weaker hand (`min`; exact blend TBD §10);
     unarmed/natural-weapon falls back to body-wide; `manipulation_override`
     chrome-arm seam. Multiplied into the attacker's motorics in `attack.py`,
     completing the stack (ranged: motorics × sight × manipulation; melee:
     motorics × manipulation × light-sight; dodge: motorics × moving). Breadth
     meta-bonuses (Q2: initiative/disarm-resist/loadout) remain a future combat
     revision. Tests: `test_combat_manipulation_resolver.py`.

Each layer ships standalone value. The five-senses *description model* (§5) is
the one piece worth pinning early so earlier layers don't contradict it.

## 10 · Cross-references

- `LOOK_COMMAND_SPEC.md` — Sensory Category Framework (the render consumer).
- `IDENTITY_RECOGNITION_SPEC.md` — the recognition pipeline voice mirrors;
  disguise / `impersonate` (voice modulator integration).
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` + `world/anatomy/species.py` —
  capacity definitions and `affects` declarations.
- The condition system (`world/medical/conditions.py`) — home for suppressible
  effect-modifiers (blindsight, flashbang-deafness) and contribution methods.

## 11 · Open / undecided

- Two-handed combination rule (weaker hand caps vs blend) and the
  under-gripping penalty curve (§6.1).
- Effect magnitudes / balance numbers (illustrative here).
- Languages (the `<language>` slot is future-proofed; only Common exists).
- Proximity-dependent hearing (directionality) — waits on the proximity system.
- Blocked-capacity shapes are pinned in §2.1. Remaining true blocks:
  `talking`→social (social-action system), `*`→work_speed (general work system;
  surgery is the natural first hook). `eating` is *not* blocked — it rides the
  consumption pipeline (buff model, no hunger). `hearing`→trade is to be dropped.
