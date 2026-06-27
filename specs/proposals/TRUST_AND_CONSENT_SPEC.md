# Trust & Consent Spec

> **Status: 🚧 DESIGN RESOLVED — NOT YET CLEARED FOR BUILD.** The core model is
> now settled (2026-06-26 design pass); what remains is build sequencing and a
> short list of edge cases (§7). The user has flagged this as **"SUPER
> IMPORTANT"** and decides when implementation starts — do not build ahead of
> that call. This doc exists so the decisions survive and so new third-party
> commands have a clean gate to defer to rather than inventing one-off logic.

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
| `search` / `frisk` | frisk / search / loot the target | |

### 3.1 · `heal` is intentionally all-medical — betrayal included

`heal` is **one blanket class covering every medical command**, by design. It is
a deep level of trust: granting it lets the holder do anything medical to you
while you're awake — including malpractice and **harvesting your organs**. The
betrayal affordance (you trusted your ripperdoc; they cut out your kidney) is a
**feature**, not a footgun. We do *not* split benevolent treatment from invasive
surgery in the trust layer — the danger is the point.

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

## 6 · NPC participation

NPCs are character objects and use the same `db.consent_grants` store, so an NPC
*can* grant or hold trust — but it will be **rare**. Two relevant cases:

* **NPC as grantor** — a paid RipperDoc with standing `heal` consent; betrayal
  carries rep cost (ties to the gig/favor loop, growth direction). AI decides.
* **NPC as actor on a player** — a security bot cannot heal/search a *conscious,
  unrestrained, untrusting* player; it must lawfully **restrain** them first
  (grapple / cuffs / pod). This is the dispatch spec's reserved seam
  (`NPC_DISPATCH_AND_SIMULATION_SPEC` §6) — sequence coercive authority content
  *after* this gate exists.

## 7 · Open edge cases (remaining)

The model is resolved; these are the corners to settle during build:

1. **Consent under duress** — trust granted while grappled/threatened. Probably
   valid-but-revocable; confirm.
2. **Revoke mid-procedure** — distrusting someone partway through a multi-step
   medical/surgical action. Does the in-flight action complete or abort?
3. **Restraint detection** — the exact predicate for `is_restrained` must unify
   the grapple state (`world/combat/grappling.py`) with restraint-device state
   (healing pod / chair furniture, clinic furniture system). One shared helper.
4. **Consciousness threshold** — does a groggy-but-awake target (low
   `consciousness`) still `can_contest`, or is there a middle band? Lean: strict
   conscious/unconscious line via the runtime `consciousness` value.
5. **Command parse / target resolution** — resolving `<person>` to an apparent
   UID when the target is present vs. only in recognition memory vs. disguised.

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
