# Capacity Consumers & Perception Spec

> **Status: 📋 PROPOSAL — design-of-record, not implemented.** Captures an
> in-progress design conversation. Built in layers (see §8). `sight` and
> `hearing`/voice are fully designed below; `manipulation`/`moving` (the
> per-effector resolver) are still being designed (§6). Magnitudes and
> balance numbers are illustrative, not final.

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
- **Setting-agnostic, cyberpunk-themed.** Chrome and harvested organs are the
  general answer to crippling injury, but capacity-loss and cyberware/biotech
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
| `talking` | **voice production** (the voice triangle, §4); social/negotiation | partial — social blocked |
| `blood_filtration` | infection resistance (existing `InfectionCondition`) | wireable now |
| `eating` | nutrition_efficiency | blocked (no nutrition system) |
| `hearing`→trade, `*`→work_speed | trade price, crafting/work | blocked (no economy/work system) |

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

## 6 · Manipulation & Moving — the per-effector resolver (IN DESIGN)

> *To be designed next. Notes from the conversation so far:*

Unlike `sight`/`hearing` (whole-body), these are **per-effector, normalized to
species baseline** — a real subsystem ("effector resolver"), not a body-wide
multiply:
- An **action declares its effectors** (weapon `hands_required`; jump → legs;
  future athletics → whatever).
- Resolve *which* effectors serve it, check *their* functional capacity, and
  compare **available functional effectors vs the species baseline** (human =
  2 hands/2 legs; rat = 4 legs+tail; Doc-Ock = 8 arms — derived from species
  anatomy, not hardcoded).
- **Penalty** when short of the requirement (2-handed weapon, one hand, no free
  second → disadvantage); **bonus** when over baseline — but bonus = **initiative
  + hard-to-fully-disarm + loadout readiness** (grenade *and* 2H melee *and*
  pistol all ready at once), **NOT** extra attacks or raw damage (combat-balance
  guardrail). *Which* readied option to use when is a future combat revision.
- Builds on existing pieces: weapon `hands_required`, the `hands` grasping-slot
  system (prehensile tail = third slot), species anatomy tables.
- **`moving`** drives movement/flee now (hard floor at the `0.15`
  incapacitation_threshold), and **future jump/athletics** (legs).

## 7 · Capacity → consumer matrix (summary)

See §2. Build cost ascends: combat hooks (cheap, multiplicative) → identity/voice
(reuse pipeline) → perception render (framework exists; base-desc decomposition
is the content lift) → per-effector resolver (manipulation/moving).

## 8 · Build sequencing (layered)

1. **Combat consumers** (`sight`→ranged/melee) — proves multiplicative +
   suppressible-effect pattern on a whole-body capacity.
2. **Identity / voice** — `@voice` + voice signature + the resolution chain +
   rendering heuristic; gates visual recognition on `sight`, voice on `hearing`.
3. **Perception render** — capacities gate LOOK sensory categories + compensatory
   enrichment.
4. **Per-effector resolver** — `manipulation`/`moving` (and the multi-appendage
   future).

Each layer ships standalone value. The five-senses *description model* (§5) is
the one piece worth pinning early so earlier layers don't contradict it.

## 9 · Cross-references

- `LOOK_COMMAND_SPEC.md` — Sensory Category Framework (the render consumer).
- `IDENTITY_RECOGNITION_SPEC.md` — the recognition pipeline voice mirrors;
  disguise / `impersonate` (voice modulator integration).
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` + `world/anatomy/species.py` —
  capacity definitions and `affects` declarations.
- The condition system (`world/medical/conditions.py`) — home for suppressible
  effect-modifiers (blindsight, flashbang-deafness) and contribution methods.

## 10 · Open / undecided

- `manipulation`/`moving` per-effector resolver — full design (§6).
- Effect magnitudes / balance numbers (illustrative here).
- Languages (the `<language>` slot is future-proofed; only Common exists).
- Proximity-dependent hearing (directionality) — waits on the proximity system.
- `eating`/nutrition, `talking`→social, `*`→work_speed, `hearing`→trade — all
  blocked on systems that don't exist yet.
