# Trust & Consent Spec

> **Status: ✅ PHASE 1 SHIPPED (2026-07-03) — §9 P2/P3 pending.** The gate
> (`world/consent.py`: `can_contest` / `is_restrained` / `check_consent`),
> the grant store, the `trust`/`distrust` commands (§4), and the Phase-1
> consumers — third-party clothing (`dress` class) and the full medical
> suite (`heal` class: treat items via `check_medical_requirements`,
> operate/incise/harvest/install/suture via the shared surgical target
> resolver) — are live. The §7 recommendations were implemented as written
> (duress grants stand; per-command gate check; shared `is_restrained`
> unifying grapple + `db.restraining` furniture with a legacy-AutoDoc
> fallback; strict consciousness binary; presence-required grants /
> memory-based revokes). Remaining: §9 P2 (`frisk`) and P3 (escort +
> dispatch coercive seam). Design history: 2026-06-26 core pass;
> 2026-07-02 deep-dig (`dress` class, NPC self-action only, §7/§9).

## 0 · Purpose

Many in-game actions are **third-party** — one character acting *on* another:
medical treatment, surgery, harvesting organs, frisking, restraining, escorting.
Without a consent layer, every such command has to decide ad-hoc whether the
target can refuse. This spec defines **when consent is required, how it's
granted, and how it binds to perceived identity**, so the behaviour is
consistent and not painted into a corner.

## 1 · Core stance — consent is the *conscious, unrestrained* path

**A target can refuse an invasive third-party action only when it can contest —
i.e. when it is conscious *and* unrestrained.** Otherwise the action lands
freely.

```
can_contest(target) = is_conscious(target) and not is_restrained(target)
```

* **Unconscious / dead** → cannot contest → **free action** (the existing gate).
* **Restrained** → cannot contest → **free action**. Restraint comes from a
  **grapple** *or* from a **restraint device** — e.g. being strapped into a
  healing pod or a restraint chair. A grappled or pod-bound patient cannot
  contest healing or search/frisk; the action simply proceeds.
* **Conscious *and* unrestrained** → **can contest** → the action requires
  **pre-granted trust** from the target (§2). Without it, the action is blocked;
  to proceed, the actor must first **restrain** the target (grapple them, get
  them into a pod), after which the free-action path applies.

Rationale: fits the deliberately dangerous, squishy world. You can do anything
to someone you've **subdued or strapped down**; you can't grief someone who is
**awake, free, and unwilling** — unless they've **trusted** you. This is not
"always require consent" (kills the danger) and not "never" (open griefing). It
**generalizes the existing workaround**: invasive commands already gate to
unconscious/dead; trust is the missing *conscious-and-willing* path, and
restraint devices are the missing *conscious-but-subdued* path.

### Build around restraint, not around NPC consent

In practice the world is built around **restraint devices**, not around NPCs
granting trust. The **healing pod** is the canonical example: it establishes the
restrained state, and *that* is what authorizes the AutoDoc (or a doctor) to
operate — no trust grant needed. NPCs are character objects and *can* hold trust
grants like anyone (§6), but it will be rare; the structural systems (pods,
chairs, restraints) do most of the consent work.

## 2 · Trust binds to *perceived identity*, not to the person

The defining requirement: **trusting "batman" must not mean trusting "bruce
wayne."** This rides entirely on the existing identity machinery — no new
identity logic.

* **Key = `get_apparent_uid(actor)`** (`world/identity.py`). It hashes the
  identity signature
  `(sleeve_uid, height_override, build_override, keyword_override,
  essential_disguise_item_type_ids)`:
  * Bruce doffs the cowl → an **essential disguise item** leaves the signature →
    his apparent UID flips from the batman UID to the bruce-wayne UID → a grant
    made to "batman" **no longer matches**. Exactly the requirement.
  * `sleeve_uid` is a per-character salt → an **impostor** in an identical
    batman getup produces a *different* UID. Trust can't be spoofed by copying
    an outfit.
  * The worn-item axis is **only essential disguise items**, not all clothing →
    swapping a non-essential jacket does **not** change the UID, so trust does
    not silently lapse over a wardrobe tweak — only over a real identity change.
* **Re-sleeve lapses trust.** If the trusted person re-sleeves into a new body
  (new `sleeve_uid`), their UID changes and the grant lapses. You trusted *that
  body/presentation*, not an abstract soul.

### Storage

Grants live on the **grantor** (the potential target), e.g.
`db.consent_grants = { apparent_uid: set(action_classes) }`, plus a snapshot
display label per UID for the listing. Grants survive logout until revoked.

## 3 · Action classes

Trust is granted per **action class** (a class maps to a set of gated commands;
not all commands exist yet):

| Class | Covers | Notes |
|---|---|---|
| `escort` / `follow` | movement-coupling (lead/drag the target's movement) | |
| `grab` / `grapple` | consensual restraint (let them grab/restrain you uncontested) | the "strap me in willingly" path |
| `heal` | **all** medical commands — treat, bandage, inject, install, **operate, harvest** | **deliberately blanket** (§3.1) |
| `search` / `frisk` | frisk / search / loot the target — **identifies the items on their person** (worn, carried, **and concealed**) | the active counter to organic concealment (§3.2) |
| `dress` | dress / undress (strip) the target's clothing | the class `CmdClothing`'s third-party paths defer to today via their "requires the trust/consent system" placeholder (§3.3) |

### 3.1 · `heal` is intentionally all-medical — betrayal included

`heal` is **one blanket class covering every medical command**, by design. It is
a deep level of trust: granting it lets the holder do anything medical to you
while you're awake — including malpractice and **harvesting your organs**. The
betrayal affordance (you trusted your ripperdoc; they cut out your kidney) is a
**feature**, not a footgun. We do *not* split benevolent treatment from invasive
surgery in the trust layer — the danger is the point.

### 3.2 · `frisk` — what it reveals

`frisk <target>` **identifies the items on a person: worn, carried, and the
concealed holdout the sdesc normally hides.** It is a *reveal*, not a contest —
so it rides the standard consent gate (consent, or an unconscious / restrained /
dead target). It is the lawful/forceful inspection: a security bot frisks a
subdued suspect, a medic frisks a willing patient, you frisk a corpse. It is the
information step that precedes confiscation or theft. Contrast **theft**
(`steal`/`pickpocket`), which is the *nonconsensual contest* version and lives in
`STEALTH_AND_DETECTION_SPEC` §6.2 — frisk asks, theft takes.

### 3.3 · `dress` — narrow by design (2026-07-02)

`dress` covers **third-party clothing manipulation only** — dressing someone,
undressing/stripping them. It is deliberately **narrow**, not a broader
"intimacy" class: intimacy in this game is expressed through free-form poses,
which stay ungated social fiction, and no further mechanical contact verbs are
foreseen (the ones that exist — frisk, grapple, heal, escort — are already
classed). If a new contact verb ever appears it gets its own class by the same
pattern. Note the companion case does NOT ride this class in practice: an LLM
companion wears/removes her own clothing via the `style` tool (self-action,
§6), so the player's request is answered by *her* act, no grant needed.

## 4 · Command surface

| Command | Effect |
|---|---|
| `trust <person> to <action>` | grant one action class to that person's *current apparent identity* |
| `trust <person> to all` | grant every action class (blanket) |
| `trust` | list who you trust and with what (rendered via recognition names, §5) |
| `trust <person>` | show that person's grants (**not** a blanket — blanket is `to all`) |
| `distrust` / `untrust <person> [to <action>]` | revoke one class, or all of that person's grants when `to <action>` is omitted |
| `distrust all` / `trust no one` | wipe every grant |

## 5 · Listing & perception

`trust` (and per-person `trust <person>`) renders each stored UID back through
recognition — `get_assigned_name(observer=you, uid)` — so the list reads in
*your* terms: "You trust **batman** to heal you; **the lean droog** to escort
you." A UID you've since forgotten falls back to the display-label snapshot taken
at grant time. You always see trust the way you *perceive* the trusted party —
consistent with how the rest of the identity system renders.

## 6 · NPC participation — **self-action only** (resolved 2026-07-02)

NPCs are character objects and the `db.consent_grants` store works on them like
anyone — but **NPCs do not grant trust in practice**. The decided stance:

* **NPC as grantor** — **no.** No LLM `trust` tool is planned; an NPC never
  hands a player standing consent. Where an NPC *cooperates*, it acts on
  ITSELF through its own real commands — the canonical case is the LLM
  companion wearing/removing her own clothing via the `style` tool. The
  player asks; the NPC does. This keeps consent as an in-fiction act every
  time rather than a stored permission, and players can never mechanically
  act on a conscious NPC's body (the restrain/unconscious paths aside).
  (A RipperDoc-style standing `heal` grant remains *technically possible*
  via the shared store if a future design wants it — nothing structural
  forbids it — but it is out of scope and off the roadmap.)
* **NPC as actor on a player** — a security bot cannot heal/search a *conscious,
  unrestrained, untrusting* player; it must lawfully **restrain** them first
  (grapple / cuffs / pod). This is the dispatch spec's reserved seam
  (`NPC_DISPATCH_AND_SIMULATION_SPEC` §6) — sequence coercive authority content
  *after* this gate exists.

## 7 · Open edge cases — recommended resolutions (2026-07-02 dig)

The model is resolved; recommended resolutions below were presented in the
2026-07-02 deep-dig and not contested — confirm-or-veto at build time:

1. **Consent under duress** — trust granted while grappled/threatened.
   **Recommend: valid-but-revocable.** Bargaining your way out of a grapple is
   world-appropriate; a grant is a grant, and it can be revoked the moment
   you're free.
2. **Revoke mid-procedure** — **recommend: no special machinery.** Multi-step
   surgery is multiple commands; the gate is checked per command invocation,
   so revocation naturally takes effect at the next step. The in-flight step
   completes; nothing aborts mid-swing.
3. **Restraint detection** — **recommend:** one shared helper in
   `world/consent.py` unifying the grapple state
   (`world/combat/grappling.py`) with a `restraining` property on furniture
   (healing pod / restraint chair, clinic furniture system). Both sources
   exist today; pure plumbing.
4. **Consciousness threshold** — **recommend: strict binary** on the runtime
   `consciousness` value, no groggy middle band. Groggy-but-awake contests.
5. **Command parse / target resolution** — **recommend: presence-asymmetric.**
   Granting requires the person PRESENT (you trust who you can see; UID
   captured at grant time). Revoking works from your trust list by remembered
   name/snapshot label. Matches how perception gates everything else.

## 8 · Cross-references

- [[project-gelatinous-trust-consent]] — standing project note + decided stance.
- `IDENTITY_RECOGNITION_SPEC` — `get_apparent_uid` / `get_identity_signature` /
  `get_assigned_name` / `recognition_memory`; the entire identity key (§2).
- Grapple / restrain (`world/combat/grappling.py`) — one source of the
  restrained state (§1, §7.3).
- Clinic furniture / AutoDoc (`project-gelatinous-clinic`) — the restraint-device
  source (healing pod) and the primary `heal` consumer.
- `world/medical` operate/harvest/install — invasive consumers that gate on the
  free-action path today and defer the conscious path here.
- `NPC_DISPATCH_AND_SIMULATION_SPEC` §6 — NPC-on-player actions defer to this gate.
- `PHASE_LAYER_SPEC` §5.3 — a **jacked-in decker's body** (left in meatspace
  while its owner is in the net) reads as unable-to-resist, so the contest
  predicate makes it a **free-action target** — frisk/move/harm the slumped body.
  Emergent from §1, no special case. (Acting *across* phases is impossible —
  perception windows are perceive-only — so consent never spans phases.)

## 9 · Build sequencing (proposed, 2026-07-02)

When the build is cleared:

* **Phase 1 — the gate + existing consumers.** `world/consent.py`
  (`can_contest`, `is_restrained`, `check_consent(actor, target,
  action_class)`), the `db.consent_grants` store, the `trust`/`distrust`
  command surface (§4), and retrofit of the two consumer families that exist
  today: third-party clothing (`CmdClothing` dress/undress — retiring its
  placeholder message) and the medical suite (treat/operate/install/harvest).
  This alone retires the alpha roadblock for player↔player play.
* **Phase 2 — `frisk`.** New command per §3.2; the information step the
  stealth spec's theft contest contrasts against.
* **Phase 3 — escort/movement-coupling + the dispatch coercive-authority
  seam** (`NPC_DISPATCH_AND_SIMULATION_SPEC` §6): lawful restrain-then-act
  for security NPCs.
