# Capacity Consumers & Perception Spec

The body-capacity system (`world/medical/core.py` → `calculate_body_capacity`,
species `body_capacities` tables) computes `0.0–1.0` capacity floors from
organ health. The **lethal** capacities
(`blood_pumping`/`breathing`/`digestion`/`neck_integrity`) and
`consciousness` drive the death and unconscious gates. This spec covers the
**performance** capacities (`sight`, `hearing`, `smell`, `moving`,
`manipulation`, `talking`, `eating`, `blood_filtration`): how they drive
gameplay as the "graduated consequence layer" between *fine* and
*dead/unconscious*, and how chrome and transplants remediate them.

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
  renderer, and more — see §5). "It's all connected."
- **Setting-agnostic, cyberpunk-themed.** Crippling injury is remediated by a
  **chrome augment OR a harvested-organ transplant** — both RipperDoc work,
  chrome and wetwork side by side (a cyber kidney *and* a donor kidney both
  restore `blood_filtration`). Capacity-loss and cyberware/biotech/transplant
  are **separate systems that integrate**, not one baked into the other. A
  grimdark reskin would relabel the flavor, not the mechanics.

## 2 · Capacity → consumer matrix

A capacity effect only lands if a *consumer system* exists.

| Capacity | Consumers | Not built / blocked |
|---|---|---|
| `sight` | combat (ranged/melee, §3), identity recognition (§4.5), perception: LOOK visual layer and every `can_see` reader (§5) | — |
| `hearing` | perception: LOOK auditory layer and every `can_hear` reader (§5), **voice recognition** (§4.5), deaf gating of speech content (§4.4) | flashbang deafness and the acoustic-event layer (§4.1) |
| `smell` | perception: the olfactory sense category (`can_smell`, §5) | chrome nose; any source of anosmia (§5) |
| `manipulation` | weapon handling (per-hand scoping, §6.1) | — |
| `moving` | dodge (§6.2) | flee, movement speed, jump/athletics, the locomotion floor (§6.2) |
| `talking` | **voice production** (the voice triangle, §4.7: garble) | social/negotiation (resonance-gated) — **system-blocked, NOT skill-blocked** (§2.1) |
| `blood_filtration` | infection course, renal failure (§7) | — |
| `eating` | — | **consumption benefit** (existing consume pipeline; buff model, no hunger) — not blocked: rides the existing consume pipeline (delivery tags) once the food/drink buff exists (§2.1) |
| `hearing`→trade, `*`→work_speed | — | trade price, crafting/work: blocked (no trade/work system); `hearing→trade` is dropped by design (§2.1) |

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
  chance). Surgery stays unscaled until we choose to open this.
- **`hearing` → trade.** A RimWorld seed vestige ("hearing affects haggling").
  Thematically weak; hearing's real consumers are perception (§5), voice-recog
  (§4), and acoustic hazards. **Drop / re-scope** rather than honor. If anything
  ever gates negotiation it is `talking`, not `hearing`. The species table
  (`world/anatomy/species.py`) still declares `"affects":
  ["trade_price_improvement"]` on `hearing`, read by nothing. Deleting that
  declaration belongs to the `modifiers`/`affects` re-audit, **Phase 13** of
  `specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` (Phase 4 there excludes
  `affects` lists, which "wait on substrate-resolution decisions").

## 3 · Sight (worked example — decided)

**Organs:** `left_eye` + `right_eye`, 0.5 each → `1.0` (both) / `0.5` (one eye)
/ `0.0` (blind). It is **whole-body** — you don't *wield* eyes — so it dodges
the effector resolver.

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

**Combat wiring.** `world/combat/capacity.py` `sight_hit_factor()` multiplies
the attacker's motorics term in `world/combat/attack.py` `process_attack`, on
piecewise curves (ranged steep, melee light). The `sight_override` condition
suppresses the penalty (the chrome seam; no augment sets it yet), and so does
combat blindsight (§12).

**Augment hook:** a cyber sense-enhancer is a single suppress-modifier across
*all* layers at once — nulls the melee penalty, restores visual-ID (or grants
a chrome-recognition channel), tells the renderer "treat visual as present."
One augment, coherent everywhere — the integration paying off.

## 4 · Hearing & Voice (decided)

**Organs:** `left_ear` + `right_ear`, 0.5 each → both / one-ear (`0.5`, mono)
/ deaf (`0.0`). A **perception + identity** capacity, not a combat one. (The
species table's only declared `affects` is `trade_price` — dropped by design,
§2.1; the real consumers are below.)

### 4.1 Consumers
- **LOOK auditory layer:** `hearing` gates whether you receive the auditory
  sensory category; deaf → it drops, others enrich (§5).
- **Voice recognition (the centerpiece):** a parallel identity channel — hear a
  *known voice* → recognize the speaker even when you can't see them (§4.5).
- **Speech content:** a deaf listener does not hear the words (§4.4).
- **Acoustic / flashbang:** not the combat loop. A **flashbang → temporary
  deafness condition** is buildable now (grenades + condition system → a
  time-limited hearing-suppression condition); not built. The broader
  acoustic-event layer (gunshots/explosions/shouting experienced differently by
  the deaf) is future.

### 4.2 Voice mirrors the visual identity stack
| Visual | Voice (parallel) |
|---|---|
| sdesc | **vocal description + ending** |
| apparent UID (visual signature) | **voice signature** |
| recognition memory → assign a name | **voice memory** → assign a name |
| `describe keyword` | **`@voice`** (+ expanded `describe` menu: 📋 UNBUILT (no issue)) |
| visual disguise / mask | **voice modulator** (cyber) |

Reuses the IDENTITY_RECOGNITION pipeline as a *second axis* — not a new system.

### 4.3 The `@voice` system and the voice signature
A player assigns their **vocal description** (the color, one word: "gravelly")
plus an **ending** (the grammatical cap: drawl / rasp / lilt / cadence / …) —
both **curated** (a bounded vocabulary, like visual keywords; not free garbage).
The vocabulary lives in `world/voice.py` and is config-overridable;
`voice_phrase` composes the pair.

Set with `@voice` (`commands/CmdCharacter.py`: set / view / list / clear).
📋 UNBUILT (no issue): a voice page in the `describe` menu.

The voice signature (`world/voice.py` `get_voice_signature`) is the body's
`sleeve_uid` plus that pair and whether a modulator is on, so everyone has a
stable, recognisable voice. Changing any of them gives a new voice UID;
`get_apparent_voice_uid` is the voice parallel of the apparent UID. The modulator slot works like a mask: it is
derived from the deployed jaw module, not a character flag (#2484; §12).

**The `talking` garble gate.** A wrecked jaw (low `talking`) replaces the
phrase with `garbled_voice_phrase` ("in a slurred, broken voice") — the
`talking` capacity's consumer (§4.7).

**Voice memory.** The Character carries a `voice_memory` AttributeProperty
(`remember_voice` / `erase_voices_named` / `get_assigned_voice_name`). Others
learn a voice only by `remember <person in front of them> as <name>`, never
by hearing alone. `remember <target>` / `forget <target>` teach / clear the
voice alongside the face, skipping garbled speakers. A deaf character learns
no voice (#2809). A voice is forgotten with the look it was named with, and
the entry goes (#3825; see IDENTITY_RECOGNITION_SPEC, the `forget` command).

### 4.4 Speech rendering
`Bob says, *speaking Common, in a gravelly drawl* "My name's Robert."`
- `*…*` = voice flavor. The `<language>` slot is present but always `Common`
  (the slot is future-proofed; see Not decided).
- The voice phrase is shown only to those who can see Bob, on a 25% roll per
  utterance; a garbled voice shows "in a slurred, broken voice" every time
  (§4.6).

**Hearing gates speech content, not just attribution.**
- `say`: a deaf + sighted listener sees "{name} says something you can't make
  out"; deaf + blind is suppressed entirely.
- Poses / emotes: `world/emote.py` `process_speech` redacts quoted speech to
  `"..."` for a deaf observer (both `render_dot_pose` and the traditional
  `render_emote` route through it); the visible action still shows (visual
  gating is the perception layer, §5).
- Whisper to a deaf target is redacted too.
- The speaker always reads their own words.

### 4.5 The resolution chain (core mechanic)
"Who said it" resolves by channel, gated by the *listener's* capacities
(`world/voice.py` `resolve_speaker_attribution`; `can_see` / `can_hear` read
`sight` / `hearing`, with override-condition seams for chrome eyes/ears):
1. **Can see the speaker** (`sight`) → name if known, else visual sdesc.
2. **Can't see, can hear** (`hearing`) → name if the listener places the
   *voice* (the discern roll below), else "someone". 📋 UNBUILT (no issue): the
   voice descriptor as a stand-in name ("A gravelly drawl says…"). Over radio
   the speaker's voice phrase always follows "A voice", and an NPC brain hears
   "a <description> voice" (RADIO_COMMS_SPEC §2.4).
3. **Neither** → "someone."

**Decided simplification:** an unrecognised / undiscerned voice is *not*
attributed (no descriptor) — it renders as "someone". A blind listener
recognises a known voice; a stranger's stays "someone."

**Placing a voice (the discern roll).** Discerning a voice is always a
determination, mirroring disguise piercing: `attempt_voice_discern` runs
opposed Intellect-vs-Resonance, with a familiarity buff and a modulator
penalty, **weighted by the listener's `hearing` capacity**.
- No roll happens unless the listener has named some voice of that body with
  `remember`.
- The verdict is cached per presentation: stored per body and voice UID and
  never rolled again, so a lost one stands even if the voice is named
  afterwards.
- Familiarity counts how many times the listener has named the voice it
  places by.
- A modulator adds 3 to the speaker's side of the roll.
- `forget` drops a won placement and keeps a lost one (#3817). Forgetting a
  name erases the voices named together with that face and the won placements
  that rested on them (`world/identity.py` `erase_look`); an AI NPC also drops
  what it filed under those voices, including a changed voice it could place
  only by that name (#3861).

**Where the chain applies.** `say`, `to`, `whisper` and the room lines of a
radio transmission (the `xmit` mutter, `to <radio>,`, a comms organ),
per-observer. Radio reception places the voice by the same roll
(`world/radio.py` `_render_radio_line`). A speaker hidden from the observer by
stealth is placed by voice even when the observer can see
(`world/voice.py` `_speaker_concealed`).

A mask defeats channel 1, not 2; a voice modulator does not defeat channel 2
outright (it changes the voice and adds 3 to the speaker's side of the placing
roll, so a listener who named the natural voice may still place it); blindness
drops you to 2; deafness removes 2. This chain is the payoff of the whole
sight+hearing design.

### 4.6 Rendering heuristic (decided — "polite, contextual")
📋 UNBUILT (no issue), except the can-see branch: `world/speech.py`
`visible_voice_flavor` shows the voice phrase on a 25% roll per utterance
(`VOICE_FLAVOR_SPRINKLE_CHANCE`), and a garbled voice every time. Nothing counts
unseen voices or keeps scene memory.

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
  at all (wrecked jaw → no usable signature; garbled). Restored by
  **CYBER_JAW**.
- **Listener's `hearing`** → can they receive it (cyber ears restore).
- **Voice modulator** → disguises the signature (anonymize v1; *mimic a specific
  voice* later, integrated with the existing `impersonate` disguise command:
  📋 UNBUILT (no issue)).
- Three sides, three chrome answers. This wires `talking` (otherwise blocked on
  social) into something concrete.

### 4.8 One ear
**One-ear directionality** (mono = can't localize) is a steeper-than-linear
hook reserved for when the **proximity** system lands; there is no directional
consumer (see Not decided).

## 5 · Perception & the five-senses framework (anchor, don't reinvent)

`LOOK_COMMAND_SPEC.md` → **"Sensory Category Framework"** defines the
categories (**Visual / Auditory / Olfactory / Tactile / Atmospheric**), graceful
degradation ("categories with no content simply don't display"), and explicitly:
*"Medical Condition Support: By design — players with sensory limitations see
reduced content."* Weather + crowd contributions are sense-categorized message
pools. **The framework was built to consume sensory limitation; this spec
supplies the input.**

- **Capacities are the input.** The renderer reads the looker's capacities to
  decide which categories they receive and at what richness.
- **Compensatory enrichment (decided):** lose a sense and the others get
  *dynamically richer* (the renderer re-weights / a blind person's sound-desc
  carries more detail) — an *enhancement* on top of the existing graceful
  degradation, chosen for storytelling and to support the deliberately
  squishy/vulnerable player.

### 5.1 The sense gates (`world/perception.py`)
- `can_see` reads `sight` → **visual**; `can_hear` reads `hearing` →
  **auditory**; `can_smell` reads `smell` (organ `nose`,
  `total_loss_penalty: "anosmia"`) → **olfactory**, against a 0.15
  threshold. Each has an override-condition seam (`sight_override` /
  `hearing_override` / `SMELL_OVERRIDE_CONDITION` = `smell_override`) for
  chrome.
- `blocked_senses` / `can_perceive_sense` / `has_reduced_perception` combine
  them, so `blocked_senses` can return `visual`, `auditory` and `olfactory`.
  Tactile / gustatory / atmospheric are never gated.
- `world.voice` imports `can_see` / `can_hear` from `world/perception.py`.
- The module's *other* export, `can_perceive`, is a different gate — the
  stealth presence check, which reads no capacity — with its own wider
  consumer set; don't conflate the two when changing either.

**Consumers of the sense gates.** `can_see` / `can_hear` /
`can_perceive_sense` are read by `world/stealth.py`, `world/radio.py`,
`world/speech.py`, `world/emote.py`, `world/identity.py`,
`commands/CmdCommunication.py`, `commands/CmdTheft.py`, `typeclasses/exits.py`,
`typeclasses/rooms.py` (base desc + adjacent-room sightings), the director
(`security` / `crime`) and the LLM NPC brains (`world/llm/observation.py`,
`world/llm/reflex.py`).

### 5.2 Ambient pools
The weather + crowd ambient pools (`get_sensory_messages`,
`get_crowd_contributions`) drop content the looker can't perceive (blind → no
visual weather/crowd; deaf → no auditory), and a sense-reduced looker gets a
**+1 compensatory** ambient message (#592).

### 5.3 Base room description by sense layer
`Room.get_display_desc` (`typeclasses/rooms.py`) composes the room description
from only the sense layers the looker can perceive (#623 / #624): the visual
blob (`db.desc`) when sighted, plus authored non-visual layers
(`db.sense_descs`: auditory/olfactory/tactile/atmospheric) for senses they
still have. **A blind looker loses the visual prose but reads the room by
sound/smell/feel; deaf drops the auditory layer.** Layers are opt-in per room:
a single-blob room desc stays valid as the *visual* layer, and a room with no
sense layers renders to a sighted looker exactly as the blob alone. Weather /
crowd still append (also perception-gated).

Sense layers are authored straight onto `room.db.sense_descs` by the build
scripts (`scripts/builds/*.py`); there is no builder command for authoring
them. `@room` (`commands/CmdBuildTools.py` `CmdRoomProfile`) reads them back,
listing the authored layers.

## 6 · Manipulation & Moving — per-effector scoping (decided)

Unlike `sight`/`hearing` (whole-body), these are measured against the
**species baseline** derived *dynamically* from anatomy (§6.4), and an action
declares the effectors it needs (weapon `hands_required`; locomotion; future
jump/athletics → legs). The design is one resolver returning **(a) the
effective capacity for the action** and **(b) meta-bonuses from surplus
effectors**; there is no single `resolve_effectors` function. The two halves
are separate collaborating layers:
- **(a)** `MedicalState.calculate_capacity_scoped(capacity, containers)`
  (`world/medical/core.py`) computes a capacity from only the given
  containers' organs; its contribution math, `_resolve_capacity_contribution`,
  is shared with the body-wide method. Its consumers are
  `manipulation_hit_factor` and `moving_dodge_factor`
  (`world/combat/capacity.py`).
- **(b)** `surplus_limb_initiative_bonus` (`world/combat/utils.py`) and the
  one door `choose_weapon` (`world/combat/weapon_choice.py`), §6.1.

### 6.1 Manipulation — two distinct outputs

Damage/loss of arm-hand anatomy answers two *separate* questions; conflating
them into one body-wide number is wrong.

- **(Q1) Handling — from the *specific gripping effector(s)* only.** Weapon
  accuracy depends on the hand(s) actually holding it, NOT a body average. A
  one-armed character with a pistol in their good hand fights at **full**
  accuracy — the missing arm is irrelevant to that weapon. (Body-wide
  manipulation ≈ `0.5` for one arm would wrongly halve it.)
  `manipulation_hit_factor(attacker, weapon, slots=...)` takes the slots the
  attack occupies (from `choose_weapon`) or else finds the gripping slot(s)
  from `attacker.hands`, inverts `limb_downstream_chain` to the hand's limb
  organs, and scopes manipulation there. Manipulation is the minimum over the
  slots: a natural weapon on a grasping host scopes to that hand, an akimbo
  pair to both. Unarmed and a natural weapon on a non-grasping host (Jawz)
  fall back to body-wide manipulation. `manipulation_override` is the
  chrome-arm seam.
- **(Q2) Breadth / readiness — from the *count of functional manipulators vs
  baseline*.** Buys breadth, not accuracy: **initiative + hard-to-fully-disarm
  + loadout-readiness**. NOT extra attacks or raw damage (combat-balance
  guardrail). Three sub-payoffs, all **decided 2026-06-20**:
  - **Loadout-readiness — the auto-prioritizer.** Rather than a weapon-swap
    action economy, combat *automatically* brings an in-hand weapon to bear
    for the engagement: **range-appropriate first** (only ranged reach at
    range; anything works point-blank). The engagement — not the weapon —
    decides melee vs ranged. The one door `world/combat/weapon_choice.py`
    `choose_weapon` (used by `process_attack` and every other reader of the
    wielded weapon; MULTI_WEAPON_COMBAT_SPEC §4) applies the range filter
    first, THEN natural-weapon precedence, then akimbo grouping, then the
    wheel: one option swings per attack and the next attack takes the next
    option that can reach, in the body's slot order. Single-weapon fighters
    are unaffected. Holding several weapons (multi-armed / cyber tail) is
    what feeds the picker more options. *The wheel (slice 2, owner ruling
    2026-10-06) replaced the earlier "then highest damage" step.*
  - **Disarm — *once per gripping hand* (already satisfied).** `resolve_disarm`
    (`world/combat/actions.py`) knocks out **one** weapon per successful
    attempt, so a multi-weapon fighter needs one disarm *per* gripping hand to
    be fully stripped — exactly the decided behaviour, emergent from the
    existing mechanic. (Edge: a 2H weapon held in two hands disarms as one
    item — fine.)
  - **Initiative — ramp then cap.** `surplus_limb_initiative_bonus`
    (`world/combat/utils.py`) adds to the `d20 + motorics` initiative roll.
    Triangular (accelerating) increments per surplus grasping limb beyond the
    species baseline — the 3rd hand is a small jump, the run to ~6 limbs is
    the reason to chrome up, then it **caps completely** at 4 surplus limbs
    (extra limbs past 6 give nothing). Human: `+0/+1/+3/+6/+10` for 2/3/4/5/6
    hands, flat beyond. Decided 2026-06-20 (magnitudes halved per balance
    pass).

So: one-armed → full per-weapon accuracy, reduced breadth; four-armed → same
per-weapon accuracy, large breadth (the right weapon auto-selected, near-
undisarmable, faster initiative).

**Minimum requirements + scaled penalty.** A weapon's `hands_required` is a
*minimum*; the gripping effectors must meet it. **Under-gripping** (2H weapon
held one-handed, no free second hand) is a **scaled** handling penalty, not a
flat tier: `grip_hit_factor` (GRIP_ENFORCEMENT_SPEC §4). The grip is
implicit, a free second slot counts as the second hand, and the placeholder
is 0.60 for one hand of two. Combining multiple gripping hands on one weapon
scales handling: the weaker hand drags it (`min` for now; exact min-vs-blend
TBD, see Not decided).

**Effector targeting already exists.** `wield <item> in <hand>` matches the
slot by name (`wield baton in left`); since the `hands` view *is* the
grasping-slot set (prehensile tail included), `wield pistol in tail` works the
moment the slot exists. Switching/choosing weapon effectors needs no new
command.

### 6.2 Moving — aggregate, species-normalized

You don't *pick a leg* to move with, so `moving` is the **whole locomotion
apparatus**, normalized to species baseline (human losing 1 of 2 legs ≫ rat
losing 1 of 4 — species-aware via `get_species_body_capacities`).

- **Dodge.** `world/combat/capacity.py` `moving_dodge_factor` multiplies the
  *target's* motorics in `attack.py` (dodge = motorics × moving). Below the
  table's `0.15` incapacitation_threshold evasion collapses to a flail.
  `moving_override` is the chrome-legs seam. This is `moving`'s only runtime
  consumer.
- **Not built:** flee, movement speed and jump/athletics reading `moving`, and
  the hard floor at `0.15` = can't locomote (drag yourself). No `at_pre_move`,
  compass, `flee` or jump check reads the capacity. That gate is the
  movement-policing substrate, Phase 7 of
  `specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md`, which also records
  `incapacitation_threshold: 0.15` on `moving` as an unread flag waiting on
  that substrate.

### 6.3 The combat capacity stack (multiplicative)

Capacities *modify* the GRIM-derived result, each multiplied into the
motorics term in `world/combat/attack.py`. Offense rides arms+eyes; defense
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
Builds on weapon `hands_required`, the `hands` grasping-slot system, and the
species anatomy tables.

## 7 · Blood filtration & condition-driven appearance (chronic/metabolic)

**Organs:** `left_kidney` + `right_kidney`, 0.5 each. The first consumer that's
neither combat nor perception — it modifies a **chronic condition over time**,
proving the model spans the medical sim too.

### 7.1 Infection resistance
`blood_filtration` is a **physiological multiplier parallel to
`InfectionCondition.environmental_modifier`** — failing kidneys make an
infection you *already have* worsen faster and clear slower
(`world/medical/conditions.py` `read_blood_filtration` + the multipliers in
`InfectionCondition.tick_effect`; fail-open):
- worsen-hazard `×(1+slope·(1−filtration))` (low filtration → faster
  progression),
- treated-heal rate `×max(floor, filtration)` (low filtration → it lingers
  despite treatment).

**Not acquisition** — kidneys don't stop you *catching* an infection (wound care
+ the environmental modifier do that); they govern how your body *fights one
off*. `disease_resistance` = "how you process an infection," not "whether you
catch one."

### 7.2 Renal failure
Kidney failure → a **RenalFailure** chronic condition (`RenalFailureCondition`,
`world/medical/conditions.py`), realizing the `blood_filtration →
consciousness` modifier that `update_vital_signs` doesn't apply directly.
`MedicalState._update_renal_failure` (called from `update_vital_signs`)
spawns it at filtration ≤0.05 and clears it at ≥0.4 (hysteresis). Restoring
filtration (cyber/donor kidney, §7.4) clears it. Effects:
- **consciousness suppression** via `get_consciousness_penalty` (reuses the
  existing suppression sum, capped at 0.6);
- **its signature — a visible skin-pigment shift** (sallow / uremic / ashen);
  it shows `uremic` via the §7.3 hook.

It rides the chronic-conditions substrate (parallel to the parked ischemia
clock).

**Not lethal — owner ruling 2026-09-24 (#3402): "Considering how much weaker it makes someone — I think that's tough enough."**
At maximum severity an otherwise healthy patient sits at consciousness 0.4,
ten points above the knockout line: fully able to act, but a little blood
loss, one drink or a knock to the head puts them down, for as long as they
have no kidney. That fragility is the cost. Renal failure drains no blood and
does not kill; the schema carries no `total_loss_fatal` flag for it. If
lethality is ever wanted, the shape is the medical roadmap's
`fatal_at_severity` on chronic conditions, which does not consume the untuned
bleeding numbers. *(Renal failure was originally specified as "suppression +
slow death"; the 2026-09-24 ruling (#3402) made survival the design.)*

### 7.3 Condition-driven appearance symptoms (cross-cutting hook)
**Conditions can carry visible symptoms** that tint the rendered skintone /
appearance, layered on the existing skintone system:
`world/medical/appearance.py` `get_appearance_tint` / `get_active_symptom`
tint the longdesc render via `appearance_mixin`, overriding base skintone.
Priority-ordered, fail-open.
- Capacity/vitals built-ins: `cyanosis` (failing breathing), `pallor` (blood
  loss).
- Condition hook: any condition exposing `appearance_symptom()` (e.g.
  RenalFailure → `uremic`).

The symptoms are legible to `look`, diagnosis, observers, *and* other systems.
The body's state becomes **legible at a glance** — a RipperDoc reads you across
the room; players see the sick one without a `diagnose`. The same hook yields
**cyanosis** (low `breathing` → blue lips), **jaundice** (liver), **pallor**
(blood loss). And conditions are **first-class signals other systems extrapolate
from**: a toxin substance can trigger/worsen renal failure, diagnosis surfaces
it, another condition compounds it. Diagnose reads renal failure as
"uraemia — the kidneys have failed" at DC 4 (#3653).

### 7.4 Remediation = chrome OR transplant (RipperDoc)
`CYBER_LEFT_KIDNEY` / `CYBER_RIGHT_KIDNEY` are single-organ replacements at
the canonical kidney slots, capacity `blood_filtration`. A harvested **donor**
kidney installs the same way (canonical name → capacity auto-restores) with
no new code. Restoring filtration clears RenalFailure (§7.2).

Per §1, a cyber kidney *and* a transplanted donor kidney both fix filtration —
the general remediation principle for *any* capacity-restoring augment, not
kidney-specific. A dialysis implant/consumable is the future non-chrome,
non-transplant stopgap (see Unbuilt).

## 12 · Chrome — the augments that remediate

Crippling injury is remediated by chrome (§1). The augments restore a capacity
the idiomatic way — **capacity-bearing replacement organs at the canonical organ
names** (like `CYBER_ARM`→manipulation, `CYBER_JAW`→talking), so
`calculate_body_capacity` counts them and every consumer sees the sense /
locomotion restored, no special-case needed:

- `CYBER_LEFT_EYE` / `CYBER_RIGHT_EYE` → `sight` (single-organ, head sub-organ).
- `CYBER_LEFT_EAR` / `CYBER_RIGHT_EAR` → `hearing`.
- `CYBER_LEG` → `moving` (side-agnostic `augment_organs` chassis).
- `VOICE_MODULATOR` → a jaw-hardpoint module hosting a `voice_modulator`
  ability (the voice-disguise; shifts the voice UID, so a listener who named
  the natural voice must win the placing roll against a penalty of 3, §4.5).
  `/modulate`. Obtainable only by staff spawn: no clinic, shop or loot table
  carries it. 📋 UNBUILT (no issue). `world/voice.py` `is_voice_modulated`
  reads the deployed state off the organ, so destroying or losing the module
  ends the disguise (#2484).

The `*_override` conditions (`sight_override`/`hearing_override`/`moving_override`/
`manipulation_override`) remain a distinct **enhancer** seam — for an augment that
grants a sense *without* the organ, where replacement doesn't apply.

**Combat blindsight** (decided 2026-06-20: combat-only, "enhance to full
perception later"). The `TARGETING_PROCESSOR` forearm-hardpoint module carries
a toggleable `blindsight` ability (`/blindsight`), which
`world/combat/capacity.py` `sight_hit_factor` honours to restore combat aim
with the eyes gone — read off the organ via `has_deployed_ability`, so a
destroyed module ends it (#2484). **Combat-only by construction:** it's a
separate seam from `sight_override`, so `can_see` (perception/recognition)
stays false — rooms and faces remain dark. A future fuller-sense suite would
set the real `sight_override` to also light up perception.

## 13 · Unbuilt

Items marked `📋 UNBUILT` stand beside their rules above: the voice page in
the `describe` menu (§4.2, §4.3), the voice descriptor as a stand-in name
(§4.5), the rendering heuristic except its can-see branch (§4.6), the
modulator mimicking a specific voice (§4.7), and a source for the voice
modulator (§12). Also not built:

- **Flashbang deafness** — a time-limited hearing-suppression condition from
  grenades; buildable now. The broader **acoustic-event layer** is future
  (§4.1).
- **`moving` beyond dodge** — flee, movement speed, jump/athletics and the
  can't-locomote floor; waits on Phase 7 of the medical substrate roadmap
  (§6.2).
- **`eating` → consumption benefit** — buildable once the food/drink buff
  exists (§2.1).
- **`talking` → social** — blocked on the social-action system (§2.1).
- **`*` → work_speed** — blocked on a general work system; surgery is the
  natural first hook (§2.1).
- **`hearing` → trade** removal — dropped by design; deleting the species
  `affects` declaration is Phase 13 of the medical substrate roadmap (§2.1).
- **Smell remediation and sources** — no chrome nose prototype exists, and
  nothing produces an anosmia condition (§5.1).
- **A `sight_override` augment** — no augment sets it (§3); a fuller-sense
  suite would set it to light up perception as well as combat (§12).
- **Dialysis** — an implant/consumable stopgap for failed kidneys (§7.4).

## 14 · Not decided

- Two-handed combination rule (weaker hand caps vs blend) and the
  under-gripping penalty curve (§6.1).
- Effect magnitudes / balance numbers (illustrative here).
- Languages (the `<language>` slot is future-proofed; only Common exists).
- Proximity-dependent hearing (directionality) — waits on the proximity system
  (§4.8).
- Blocked-capacity shapes are pinned in §2.1; the remaining blocks
  (`talking`→social, `*`→work_speed) are listed under Unbuilt (§13).

## 15 · Cross-references

- `LOOK_COMMAND_SPEC.md` — Sensory Category Framework (the render consumer).
- `IDENTITY_RECOGNITION_SPEC.md` — the recognition pipeline voice mirrors;
  disguise / `impersonate` (voice modulator integration); the `forget` command.
- `RADIO_COMMS_SPEC.md` §2.4 — voice over radio.
- `MULTI_WEAPON_COMBAT_SPEC.md` §4 — the one door `choose_weapon`.
- `GRIP_ENFORCEMENT_SPEC.md` §4 — under-gripping.
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` + `world/anatomy/species.py` —
  capacity definitions and `affects` declarations.
- `specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` — Phase 7 (movement policing),
  Phase 13 (`modifiers`/`affects` re-audit), `fatal_at_severity`.
- The condition system (`world/medical/conditions.py`) — home for suppressible
  effect-modifiers (blindsight, flashbang-deafness) and contribution methods.
