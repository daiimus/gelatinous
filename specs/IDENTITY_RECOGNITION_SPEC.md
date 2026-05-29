# Identity & Recognition System Specification

## Overview

Characters in Gelatinous are currently identified everywhere by their `key` (real name). This spec introduces a **sleeve-based recognition system** where characters see strangers by physical description, manually assign names, and store recognition in organic memory (the brain organ). The system is designed so cybernetic memory (cyberbrain, digital ID) can plug in seamlessly later.

This is foundational infrastructure. Identity and recognition form the backbone of future **memory**, **forensics**, **social deception**, **communication**, and **posing** systems. Every NPC is a full participant — all Characters have brains with recognition memory.

### Design Principles

1. **Physical identity** — Recognition is based on the physical sleeve (body), not consciousness. Same body = same recognition across clones.
2. **Unique by default** — The sdesc system uses enough physical traits and visible state to make characters distinguishable most of the time without effort.
3. **Obscurable with effort** — Characters can obscure their identity, but only if they're meticulous. Half-measures leave tells.
4. **Per-observer truth** — Every character in a room may know other characters by different names. Messages must render per-observer.
5. **RAG-ready memory** — Recognition entries are rich documents with temporal, spatial, and contextual metadata, designed for future retrieval-augmented generation.
6. **Generic grammar** — The grammar engine serves identity now and the posing system later. Built generic from day one. See `EMOTE_POSE_SPEC.md` for the canonical grammar engine specification.

---

## Core Concepts

### Sleeve

A physical body. Each sleeve has inherent, observable physical traits (height, build, sex) and a unique `sleeve_uid` (UUID). Flash clones are physically identical and inherit the same `sleeve_uid`. A sleeve's identity is what others see — not what consciousness inhabits it.

### Short Description (sdesc)

What strangers see instead of a name. Composed from observable physical traits:

```
"a {physical_descriptor} {keyword} {distinguishing_feature}"
```

- **Physical descriptor** — auto-derived from height × build (immutable without a new sleeve)
- **Keyword** — player-selected via `@shortdesc`, gender-gated
- **Distinguishing feature** — auto-derived from visible state: clothing > hair > nothing

Skintone is deliberately excluded from the sdesc. It appears only in the longdesc when someone `look`s at the character directly.

### Recognition

A per-character memory mapping (currently stored as an `AttributeProperty` on the Character; brain-organ storage deferred — see §Memory Architecture): "I know the person with this Apparent UID as [name], and here's everything I remember about them." When you see someone whose current Apparent UID is in your memory, you see the name you assigned. When you don't recognize them, you see their sdesc. Because the Apparent UID is derived from the target's full identity signature (real sleeve, active overrides, essential items), the same physical body can produce different recognition entries under different disguises — see §Memory Data Model.

### Apparent Identity

What the recognition pipeline actually resolves against. Three distinct concepts work together:

1. **Identity Signature** — a tuple of all observable identity inputs: real `sleeve_uid` (the body's salt), active presentation overrides (height, build, keyword), and the sorted set of equipped essential disguise item types. The signature is recomputed on access from current state.
2. **Apparent UID** — a deterministic 16-character hex digest of the identity signature (`blake2b(signature_bytes, digest_size=8).hexdigest()`). This is the **key** that recognition memory is stored under. Same signature → same UID → auto-recognition; any signature change → new UID → observers see a stranger.
3. **Persona** — a player-private label for a remembered combination of overrides. Personas do **not** generate UIDs themselves; they are pure recall ergonomics. Adopting a persona restores its captured overrides, which then flow through the signature → UID pipeline like any other state.

The sdesc is overridable through `appear`, but the distinguishing feature always reflects actual visible state — true disguise requires changing your clothes (or destroying / acquiring essential items).

**The full pipeline at a glance.**

```mermaid
graph LR
    Sleeve["Sleeve<br/>(physical body)<br/>+ sleeve_uid"]
    Over["Presentation overrides<br/>(appear command)"]
    Items["Essential disguise items<br/>(worn equipment)"]
    Sig["Identity signature<br/>(tuple)"]
    UID["Apparent UID<br/>(blake2b hex)"]
    Mem["Observer's recognition_memory<br/>{uid: entry}"]
    Name["Displayed name<br/>(assigned_name or sdesc)"]
    Sleeve --> Sig
    Over --> Sig
    Items --> Sig
    Sig -->|hash| UID
    UID -->|lookup| Mem
    Mem -->|hit| Name
    Mem -.->|miss → §Disguise Piercing| Name
```

> **Worked example — Bruce Wayne, two signatures, one observer.** Alfred has been with Bruce for decades; his `recognition_memory` holds two entries for the same `sleeve_uid`:
>
> - Entry A: Apparent UID for *bare Bruce* (no overrides, no essential items) → `assigned_name = "Bruce"`.
> - Entry B: Apparent UID for *Batman* (height='tall', build='stocky', keyword='figure' + cowl/cape/armor) → `assigned_name = "Batman"`, `linked_to = <Entry A uid>` (cell D from a prior unmasking moment).
>
> When Bruce walks into the Batcave in a tux, `get_display_name(Alfred)` hashes the bare signature, hits Entry A, returns `"Bruce"`. When he steps out in the suit, the same code hashes the costumed signature, hits Entry B, returns `"Batman"`. Alfred's `recall` surfaces "Batman, also known as Bruce" via `get_linked_aliases`. A stranger watching the same scene sees `"a tall figure in dark armor"` either way — no entries in their memory, no linkage, the sdesc renderer takes over.

---

## Short Description (sdesc) System

### Composition

The sdesc is assembled from three components:

```
article + physical_descriptor + keyword + distinguishing_feature
```

Examples:
- `"a lanky man in a leather jacket"`
- `"a compact woman with blonde braids"`
- `"a heavyset droog in red power armor"`
- `"a diminutive kid"`
- `"an athletic dame with cropped white hair"`
- `"a towering bloke in a torn lab coat"`

The article (`a` / `an`) is determined by the grammar engine based on the first phoneme of the physical descriptor.

### Physical Descriptor Table

Derived from the cross-product of height and build. Players select height and build at character creation; the descriptor is auto-derived and cannot be directly set.

**Heights**: short, below-average, average, above-average, tall
**Builds**: slight, lean, athletic, average, stocky, heavyset

| | slight | lean | athletic | average | stocky | heavyset |
|---|---|---|---|---|---|---|
| **short** | diminutive | wiry | compact | short | squat | rotund |
| **below-avg** | slight | lithe | spry | unassuming | stout | portly |
| **average** | slender | lean | athletic | average | stocky | heavyset |
| **above-avg** | willowy | rangy | strapping | tall | brawny | hulking |
| **tall** | lanky | gaunt | towering | tall | burly | massive |

30 unique descriptors. These are setting-neutral and describe observable silhouette.

### Keyword List

Players select their keyword via `@shortdesc`. Keywords are gender-gated: feminine-presenting and gender-neutral keywords are available to female characters, masculine-presenting and gender-neutral to male characters. The `appear` command allows selecting **any keyword from the full catalog** regardless of the character's gender — a male character can disguise as a "woman" and vice versa. This is available to all characters, not restricted by access level.

**Feminine-presenting (24):**
female, girl, lass, woman, matron, grandma, hag, granny, madam, tomboy, chick, gal, chica, vixen, diva, dame, sheila, mona, bimbo, bitch, lady, senorita, chola, devotchka

**Masculine-presenting (23):**
male, boy, lad, man, patron, grandpa, geezer, gramps, gentleman, guy, fellow, dude, playa, pimp, bloke, bruce, mano, bro, douche, stiff, hombre, cholo, droog

**Gender-neutral (24):**
person, kid, urchin, human, citizen, elder, fossil, fleshbag, denizen, neut, snack, walker, chum, charmer, star, mate, smoker, meatsicle, punk, clone, wageslave, baka, androog, suit

### Distinguishing Feature Derivation

The distinguishing feature is the final clause of the sdesc. It is **always auto-derived** from the character's actual visible state — players cannot set it directly. This ensures the sdesc is always truthful to what observers can actually see.

**Priority order:** clothing > hair > nothing

#### Clothing-based Feature

The system selects the most visually prominent worn item. Prominence is determined by:
1. Outermost layer (what's on top)
2. Largest coverage area (full-body > torso > head > extremities)
3. If multiple items tie, the most recently equipped takes precedence

Format: `"in {article} {item_sdesc}"` — e.g., `"in a leather jacket"`, `"in red power armor"`, `"in a tattered lab coat"`

Items use a `worn_sdesc_short` attribute for this clause — a brief, recognizable noun phrase. When unset, the selector falls back to the item's `key`.

**Disguise items are deprioritised.** When a wearer has any non-disguise clothing, the feature selector partitions the worn items and prefers the non-disguise pool. The disguise pool is consulted only when nothing else is worn — the *naked-but-masked* carve-out. Without this carve-out, a lone balaclava would yield no feature clause; with it, observers still get `"a tall lean masked droog in a black balaclava"`. When real clothing is added, the feature shifts to that clothing and the balaclava's contribution falls back to the disguise adjective only (see [Disguise Adjective](#disguise-adjective)): `"a tall lean masked droog in a black trenchcoat"`.

#### Hair-based Feature

If no clothing provides a distinguishing feature (nude, very minimal clothing), the system falls back to hair.

Format: `"with {color} {style}"` — e.g., `"with red dreadlocks"`, `"with cropped white hair"`, `"with long black braids"`

If the character is bald or has no hair attribute set, this is skipped.

Head coverings suppress the hair fallback by listing `"hair"` in their `coverage` list — the same clothing-coverage vocabulary that governs longdesc/wound/scar visibility. When `"hair"` appears in the wearer's clothing coverage map, the chain falls through to "no feature" rather than describing hair the observer cannot see. Replaces the legacy `covers_hair` boolean (removed in #176) with a unified suppression mechanism.

#### No Feature

If the character has no visible clothing and no visible hair (bald + nude, or fully concealed), the sdesc has no distinguishing feature clause:

```
"a lanky man"
"a compact woman"
```

This makes the character harder to distinguish — which is realistic.

### Hair Attributes

Two new attributes selected at character creation:

- **`db.hair_color`** — e.g., "red", "black", "blonde", "white", "brown", "gray", "blue", "green", "pink", "purple", "silver", "auburn" (or None/bald)
- **`db.hair_style`** — e.g., "cropped", "short", "long", "braided", "dreaded", "mohawk", "ponytail", "shaved sides", "curly", "straight", "matted", "slicked" (or None/bald)

Combined for display: `"{hair_color} {hair_style} hair"` → `"red dreaded hair"` or shorthand like `"red dreadlocks"`. The exact phrasing can use a small mapping table for natural-sounding combinations (e.g., "dreaded" + color → `"{color} dreadlocks"`).

### `@shortdesc` Command

```
@shortdesc <keyword>
```

Changes the player's keyword component only. Validates against the gender-gated keyword list. The physical descriptor and distinguishing feature cannot be set this way — they reflect reality.

```
> @shortdesc droog
You will now appear as "a lanky droog in a leather jacket" to those who don't know you.
```

---

## Recognition System

### Recognition Pipeline

```mermaid
graph TD
    A["get_display_name(looker)"] --> B{Is looker self?}
    B -->|Yes| C["Return self.key"]
    B -->|No| D["Compute target's Apparent UID<br/>from current identity signature"]
    D --> E[Get looker's recognition_memory]
    E --> F{Apparent UID in recognition_memory?}
    F -->|Yes, has assigned_name| G[Return stored assigned_name]
    F -->|"Yes, no assigned_name (forgotten entry)"| H["Return target's sdesc"]
    F -->|No| H
    G --> I{Staff cyberware active?}
    H --> I
    I -->|Yes| J["Append ' (real_name)'"]
    I -->|No| K[Return as-is]
```

Self-perception (`"You"`) is **not** returned by `get_display_name`; it is handled at the rendering layer (see §Self-Perception below).

### `get_display_name` Override

The central hook. Currently returns `self.key` (Evennia default). Overridden on Character:

```python
def get_display_name(self, looker, **kwargs):
    """Return identity-aware display name based on looker's recognition."""
    if looker == self:
        return self.key  # Self-perception handled at render layer

    # Compute current Apparent UID from identity signature
    apparent_uid = self.get_apparent_uid()

    # Check looker's recognition memory (keyed on Apparent UID)
    recognized_name = looker.recall_name(apparent_uid)

    if recognized_name:
        display = recognized_name
    else:
        display = self.get_sdesc()

    # Staff cyberware overlay
    if looker.has_identity_overlay():
        display = f"{display} [{self.key}]"

    return display
```

### Memory Data Model

Each recognition entry is a rich document, designed for future RAG integration. Entries are **keyed on Apparent UID** (the 16-character hex digest of the target's identity signature at the moment of remembering), not on real `sleeve_uid`. This means a single real character may appear under multiple recognition entries — one per distinct disguise signature the observer has tagged.

```python
recognition_memory = {
    "<apparent_uid>": {              # 16-char hex digest of identity signature
        # Core identity
        "assigned_name": str | None,    # What the rememberer calls them
                                        # (None means entry exists but has been forgotten)

        # Temporal context
        "first_seen": str,              # ISO timestamp of first encounter
        "last_seen": str,               # ISO timestamp of most recent perception.
                                        # Bumped passively on room entry (see
                                        # §Memory Architecture) and on every
                                        # explicit `remember`. Throttled to one
                                        # write per RECOGNITION_BUMP_THROTTLE_SECONDS
                                        # per UID per observer.
        "times_seen": int,              # Count of explicit `remember` invocations
                                        # for this entry. Does NOT track passive
                                        # perception — see `last_seen` for recency.

        # Spatial context
        "location_first_seen": str,     # Room name/key where first encountered
        "location_last_seen": str,      # Room name/key where last perceived
                                        # (passive bump on room entry + explicit `remember`)
        "locations_seen": [str],        # All locations where encountered

        # Appearance snapshot
        "sdesc_at_first_encounter": str,  # What they looked like initially
        "sdesc_at_last_encounter": str,   # What they looked like most recently
                                          # (passive bump on room entry + explicit `remember`)

        # Player-authored
        "notes": str,                   # Free-text notes (player-written)
        "tags": [str],                  # Player-assigned tags ("dangerous", "merchant", "ally")

        # System-derived
        "confidence": float,            # 0.0-1.0, Resonance-influenced recognition certainty
        "relationship_valence": str,    # "hostile", "neutral", "friendly", "unknown"
        "lost_contact": bool,           # True once the entry's UID has not matched any
                                        # observable character for an extended period,
                                        # OR once the observer witnessed the presentation
                                        # transition into a new signature ("unmasking").
                                        # Entry remains visible in `memory` and `recall`
                                        # but is annotated as out of contact.
        "real_sleeve_uid": str | None,  # The target's actual `sleeve_uid` at the
                                        # moment of writing. Written once per entry
                                        # (sleeves don't change) and lazily backfilled
                                        # by `bump_recognition_recency` and the
                                        # unmasking-moments hook when missing. Enables
                                        # `find_entries_by_real_sleeve_uid` reverse
                                        # lookup used by the disguise-piercing
                                        # recognition roll (see §Disguise Piercing).
        "linked_to": str | None,        # Apparent UID of a prior presentation the
                                        # observer witnessed transitioning into this one.
                                        # Populated by the unmasking-moments hook (see
                                        # §Unmasking Moments). Forms a one-direction
                                        # chain new → old; walked by
                                        # `get_linked_aliases` to render the
                                        # "Also known as" line in `recall` and the
                                        # "(aka ...)" annotation in `memory`.

        # Interaction log (capped, rolling window)
        "recent_interactions": [
            {
                "timestamp": str,       # ISO timestamp
                "location": str,        # Where it happened
                "type": str,            # "combat", "trade", "conversation", "observation"
                "summary": str,         # Brief auto-generated description
            }
        ],
    }
}
```

This is stored as a db attribute on the Character (`recognition_memory` AttributeProperty), keyed by **Apparent UID**. See §Memory Architecture for the storage-location rationale and the planned migration to brain-organ storage. The `recent_interactions` list should be capped (e.g., last 20 interactions per entry) to prevent unbounded growth, with older interactions eligible for summarization or archival.

**Orphaned entries (`lost_contact`):** A recognition entry whose Apparent UID has not matched any observable character within a configurable window (deferred to balance pass; provisional default: 30 in-game days, defined as `LOST_CONTACT_THRESHOLD_SECONDS` in `world/identity.py`) is marked `lost_contact = True`. The entry stays visible in `memory` and `recall` (player-authored notes are valuable lore even when the trail goes cold) and is rendered with a "(lost contact)" annotation. The flag has **two writers**:

1. **Lazy staleness scan** — `world/identity.py:mark_lost_contact_entries`, invoked from the `memory` and `recall` commands via `commands/CmdCharacter._refresh_lost_contact` immediately before iterating recognition memory. No background scan; the flag only updates when a surface would render it.
2. **Unmasking-moments hook** — `world/identity.py:_broadcast_unmasking` (cells B and D of the broadcast matrix, see §Unmasking Moments) flips the *old* entry's `lost_contact` to `True` synchronously when an observer witnesses a signature change. This is an eyewitness fact, not an inference: the prior presentation is provably gone from this sleeve.

The flag therefore carries a mild dual semantic — "this presentation hasn't been observed in a long time" *or* "this presentation was directly observed to transition away." Both render the same `|y(lost contact)|n` annotation; the player-facing string is intentionally agnostic.

The inverse — clearing the flag back to `False` on re-meet — is handled by `world/identity.py:bump_recognition_recency` (passive perception path), by the recognition writer in `_remember_target` (explicit `remember` path), and by cells C and D of the unmasking broadcast (refreshing the new entry). A future player command may allow explicit pruning of lost-contact entries; auto-pruning is intentionally **not** done.

**Passive recency on perception:** Recency fields on existing recognition entries (`last_seen`, `location_last_seen`, `sdesc_at_last_encounter`) are refreshed without an explicit `remember` whenever the observer perceives a target whose Apparent UID is already in their memory. This is implemented by `world/identity.py:bump_recognition_recency`, invoked from `Character.at_post_move` via `_refresh_recognition_recency`: on every room entry the observer scans the new room's contents and bumps each known UID. Writes are throttled to one bump per `RECOGNITION_BUMP_THROTTLE_SECONDS` (provisional 300s = 5 minutes) per UID per observer, so extended co-location does not spam AttributeProperty writes. The helper is **strictly opt-in for already-remembered UIDs** — it never creates entries; entry creation remains the exclusive responsibility of the `remember` command. The `times_seen` counter is intentionally **not** incremented by passive perception; it counts explicit `remember` invocations only. Stealth/sneaking/hidden mechanics are a known future delta — when those land, they will need to suppress this hook for hidden targets.

### Remembering Names

**`remember` command:**

```
remember <target> as <name>
```

Stores the name in the rememberer's recognition memory under the target's current **Apparent UID**. Any name is valid — false names are always possible. Re-remembering overwrites. Names are validated against the cross-namespace uniqueness rule (see §Personas — *Cross-namespace uniqueness*): the assigned name must not collide with the keyword catalog, the caller's persona names, or any existing recognition `assigned_name` on a different Apparent UID.

```
> remember tall man as Jorge
You will now recognize a tall lanky man as Jorge.

> remember 2nd lanky dude as Sketchy Pete
You will now recognize a lanky man with a leather jacket as Sketchy Pete.
```

If the target is already remembered under a different name:

```
> remember Jorge as Johnny Twoshoes
You now know Jorge (previously 'Jorge') as Johnny Twoshoes.
```

**`forget` command:**

```
forget <target>
```

Clears the assigned name on a recognition entry. The entry itself is preserved (sdesc snapshots, locations, `times_seen`, etc.) so future `remember` calls extend the existing history rather than starting fresh. Targets resolve against currently-visible characters first, then against previously-remembered names — you can `forget` someone who isn't present.

`forget` additionally invalidates the caller's
`disguise_pierce_cache` entries for the target's sleeve
(PR #211 / issue #210).  Without this, a future encounter under a
previously-seen disguise would short-circuit on the stale cached
verdict instead of re-rolling cleanly against the now-name-less
memory entry.  See §Disguise Piercing → Caching.

**`recall` command:**

```
recall <target>
```

Inspects a single recognition entry: assigned name (if any), what they looked like at first encounter, where, when, and how many times you've seen them. Same target resolution as `forget`.

**`memory` command:**

```
memory
```

Lists every person you've remembered by name, sorted by recency (most recently seen first). Forgotten entries are not listed even though their record is preserved.

**Digital ID exchange (Phase 4 — Cybernetics):**

A character with a cyberbrain can broadcast their digital identity over the air. The receiver's cyberbrain auto-stores the transmitted name and sleeve_uid. This is a certificate-exchange model — fast, impersonal, verifiable within the digital trust framework.

Socially, demanding someone flash their digital ID is a faux pas in most contexts — it implies distrust. This is a social norm enforced by player culture, not game mechanics.

---

## Memory Architecture

### Organic Memory (Character AttributeProperty)

Recognition data lives directly on the Character as an `AttributeProperty` (`typeclasses/characters.py`: `recognition_memory`). The original design located this on the brain organ — that pivot was deferred to keep the engine PR scoped, but the storage location is conceptually still "the character's organic memory" and the migration to brain-organ storage remains tracked under the medical-system rework.

**Storage:** `Character.recognition_memory` (dict, AttributeProperty), keyed by **Apparent UID**.

**Properties:**
- Populated by explicit player action (`remember` command)
- Future: auto-populated by Resonance-driven proximity detection
- Lost on character deletion. When recognition migrates to the brain organ (future medical-system work), it will be lost on brain destruction — moot for the current character (brain destruction = death) but relevant for brain-transplant scenarios.
- Brain damage (non-fatal, future) will carry a risk of partial memory loss — individual entries can be degraded or lost. This is a future enhancement once the memory pool is rich enough to make partial loss meaningful and once recognition lives on the brain organ.
- Flash clones get a new Character record — they start with empty recognition memory. The clone is a stranger who happens to look like someone others remember.

> **Implementation note (engine PR rollout):** The engine PR ships recognition storage on the `Character` typeclass as an `AttributeProperty`, not on the brain organ. Migration to brain-organ storage is a follow-up tracked alongside the medical-system rework. All consumers in this spec that read or write "the brain's recognition memory" should be understood to mean "the character's `recognition_memory` AttributeProperty" until that migration lands. The data shape and semantics are unchanged.

### Digital Memory (Cyberbrain — Phase 4)

Same data model as organic memory, different storage and capabilities:

- Stored on the cyberbrain implant (future cyberware system)
- Backed up, transferable between sleeves
- Hackable, forgeable, wipeable
- Provides a contact-book UI (traditional list interface)
- Survives resleeving if the cyberbrain is preserved or backed up

**Lookup priority:** Cyberbrain first, then organic brain. First match wins. This means a character with both memory types has redundant recognition — harder to fool.

### Memory and Resonance

Resonance ("Social Connection & Empathy", currently 0 mechanical uses) becomes the governing stat for organic memory:

- **Memory persistence** — Higher Resonance → organic memories persist indefinitely. Low Resonance → risk of memory decay over time (entries lose confidence, eventually drop out).
- **Auto-recognition** — Future: at high Resonance, spending extended time in proximity with someone can auto-populate a recognition entry (you develop an intuitive sense of who they are without formal introduction).
- **Disguise perception** — **Shipped.** Disguise piercing uses an opposed Intellect (observer) vs Resonance (target) roll with a familiarity bonus capped at `DISGUISE_PIERCE_FAMILIARITY_CAP` and a per-vector penalty of `DISGUISE_PIERCE_VECTOR_PENALTY` (worn `disguise_essential` items + active overrides). See the [Disguise Piercing](#disguise-piercing) section for the full contract.
- **Confidence** — The `confidence` field in memory entries is influenced by Resonance. Higher confidence means the name displays with certainty; at low confidence, the display could show uncertainty: `"Jorge(?)"` or `"someone who might be Jorge"`.

Exact thresholds and formulas are a tuning concern — the architecture supports Resonance as an input to all these systems.

---

## Grammar Engine

The grammar engine handles article selection, possessive forms, objective forms, and pronoun integration for sdescs and character names. It is designed generically to serve the identity system now and the **posing system** in the future. The canonical grammar engine specification — including verb conjugation rules, the `inflect` integration for articles, and pronoun transformation tables — lives in `EMOTE_POSE_SPEC.md`. This section covers the identity-specific requirements.

### Article Handling

Sdescs always include a grammatically correct article:

- **Indefinite** (default for sdescs): `"a tall man"`, `"an athletic dame"`
- **Definite** (for targeting / objective references): `"the tall man"`, `"the athletic dame"`
- `a` vs `an` determined by phoneme of the following word, not just the letter (e.g., `"an unassuming"` not `"a unassuming"`)

### Possessive Forms

For sdescs:
- `"a tall man's knife"` → article + descriptor + keyword + `'s`
- `"Jorge's knife"` → recognized name + `'s`

For pronouns (self-perception):
- `"your knife"` (when looker is the possessor)

### Objective Forms

When a character is the object of an action:
- `"You attack the tall man."` — definite article for the target
- `"A lanky droog attacks you."` — "you" for self

### Pronoun Integration

The grammar engine interoperates with the existing pronoun system. Template variables like `{they}`, `{them}`, `{their}` resolve based on the character's **apparent gender** — the result of `get_apparent_gender(char)` (see §Pronouns Under Disguise). For an undisguised character this matches `caller.gender`; for a disguised character it derives from the active `keyword_override`. Recognition (i.e. having a name tagged on the observed Apparent UID) changes the *name* observers see, but does not alter the pronoun set; pronouns are a function of the *current* apparent presentation, not of the recognition tag.

### Self-Perception

When `looker == self`:
- `get_display_name(self)` → `self.key` (the character's own real name)
- Self-perception "You" is **not** returned by `get_display_name` — it is handled by the communication/rendering layer (dot-pose, say, whisper, system messages)
- This avoids breaking third-person sentence construction ("You is standing here")
- See `EMOTE_POSE_SPEC.md` Appendix C for the full architectural rationale

### Future: Posing System

The grammar engine is built as a standalone utility module (`world/grammar.py`) that can be imported anywhere. The full posing and communication system — including the dot-pose command, verb conjugation, pronoun transformation, per-observer emote rendering, and custom say/whisper overrides — is specified in `EMOTE_POSE_SPEC.md`.

Example of the grammar engine in action with the posing system:

```
> pose picks up {their} knife and stares at {target}.

Observer who knows both:
→ "Jorge picks up his knife and stares at Maria."

Observer who knows neither:
→ "A lanky man picks up his knife and stares at a compact woman."

Self:
→ "You pick up your knife and stare at a compact woman."
```

The grammar engine must handle:
- Arbitrary noun phrase inflection (articles, possessives, objective case)
- Subject-verb agreement (`"a tall man picks"` vs `"you pick"`)
- Pronoun resolution from character gender
- Definite/indefinite article context (first mention = indefinite, subsequent = definite)

---

## Disguise System

Disguise is a **continuous performance** — a character is always being perceived as whatever combination of presentation overrides and worn items currently apply. There is no "starting" or "stopping" a disguise; identity flows organically from observable state. The system is available to **all characters**.

### Three Architectural Layers

Disguise has three independent layers, each controllable on its own and combining to form the final observable identity:

| Layer | Controlled by | What it affects |
|-------|--------------|-----------------|
| **Presentation overrides** | `appear` command | Per-axis: height, build, keyword, (future) voice |
| **Disguise items** | Equipping/removing tagged clothing | Distinguishing feature + identity signature (when essential) |
| **Body modification** (future) | Pharmaceuticals / cybernetics | `@longdesc` + identity signature |

The **sdesc** is always composed the same way regardless of disguise state:

```
"{physical_descriptor} {keyword} {distinguishing_feature}"
```

- Presentation overrides change the components going into descriptor and keyword
- Items contribute to the distinguishing feature via the existing auto-derivation system (essential items additionally contribute to the identity signature)
- The layers combine into the full observable identity

### Identity Signature & Apparent UID

The recognition system needs a stable identifier for "this disguised person" so observers can tag and re-recognize them across encounters. This identifier is the **Apparent UID**, derived deterministically from an **identity signature** computed from:

1. The character's **real `sleeve_uid`** (acts as a per-character salt — the body's bones, gait, mannerisms, and bearing are part of how the character is perceived)
2. The character's **active presentation overrides** (height, build, keyword)
3. The set of **essential disguise items** currently equipped (by item type, not specific instance)

```python
identity_signature = (
    real_sleeve_uid,            # str (UUID)
    height_override or None,    # str | None — None when no override
    build_override or None,     # str | None
    keyword_override or None,   # str | None
    tuple(sorted(essential_item_type_ids)),  # tuple[str, ...] — stable order
)

signature_bytes = repr(identity_signature).encode("utf-8")
apparent_uid = hashlib.blake2b(signature_bytes, digest_size=8).hexdigest()
# 16-character lowercase hex string, e.g. "a3f1c92b08e4d7f6"
```

**Signature anatomy.**

```mermaid
flowchart TD
    subgraph Inputs["Identity signature inputs (observable state)"]
        Salt["real sleeve_uid<br/>(per-body salt, immutable)"]
        H["height_override<br/>str | None"]
        B["build_override<br/>str | None"]
        K["keyword_override<br/>str | None"]
        Items["sorted tuple of<br/>essential item type IDs"]
    end
    Sig["identity_signature tuple"]
    Bytes["repr().encode('utf-8')"]
    Hash["blake2b digest_size=8"]
    UID["Apparent UID<br/>16-char hex"]
    Salt --> Sig
    H --> Sig
    B --> Sig
    K --> Sig
    Items --> Sig
    Sig --> Bytes --> Hash --> UID
    UID --> Mem["recognition_memory[uid] lookup"]
```

> **Worked example — Peter Parker, two presentations.**
>
> | Input | Bare Peter | Spider-Man |
> |---|---|---|
> | `real_sleeve_uid` | `peter-uuid` | `peter-uuid` (same — same body) |
> | `height_override` | `None` | `None` |
> | `build_override` | `None` | `None` |
> | `keyword_override` | `None` | `"vigilante"` |
> | essential item types | `()` | `("mask-red", "suit-spandex")` |
> | identity_signature | `("peter-uuid", None, None, None, ())` | `("peter-uuid", None, None, "vigilante", ("mask-red","suit-spandex"))` |
> | Apparent UID | `4f2c…a901` | `8b13…7e6d` *(different)* |
>
> Same body, two distinct UIDs — observers tag each independently. The salt (`peter-uuid`) being shared is what later lets the §Disguise Piercing path correlate the two: a familiar observer can pierce *from* the Spider-Man UID *to* the Peter entry because both rows in their `recognition_memory` carry the same `real_sleeve_uid`.

**Hash choice rationale:** `blake2b` with `digest_size=8` is fast, deterministic across processes (unlike Python's builtin `hash()`, which is salted per-process via `PYTHONHASHSEED`), and produces a 16-character hex digest with a 64-bit collision space — comfortable for the per-observer recognition-memory dict, where collisions only matter within a single character's memory and population is bounded by encounter count.

**Key properties:**

- Same character + same overrides + same essential items → **same Apparent UID, every time.** Observers who tagged this combination before will auto-recognize it again. This is the *organic recurring identity* property.
- Change any signature input → **different Apparent UID.** Observers who tagged the prior signature see a stranger. This is the *unmasking* property.
- Two different characters wearing the same overrides + items → **different Apparent UIDs** (different salt). Visual collision but no recognition collision. Impersonation is *visual*, not *systemic*.
- Items reference by **type**, not instance. Replacing a destroyed balaclava with another balaclava of the same type preserves the signature. The exact "type ID" representation is defined by the disguise-item taxonomy in Phase 3.5; the engine consumes a sorted tuple of stable string identifiers.

**Tradecraft as gameplay:**

Because the signature emerges from observable state — not from a player declaration — disguise discipline becomes a real player skill. Always wearing the same balaclava? Always overriding to the same height? Frequenting the same locations in the same look? A persistent observer with a good memory builds a recognition tag on that signature, and a "secret" identity becomes trackable. Mixing up overrides, varying essential items, and avoiding repetition is how a character stays anonymous. **Bad tradecraft is mechanically punished; good tradecraft is mechanically rewarded.**

### `appear` Command — Presentation Overrides

The `appear` command is the player's interface to presentation overrides. Each override is a **per-axis** change applied independently:

```
appear taller / shorter                     — height axis (one step on the HEIGHTS scale)
appear bulkier / fatter                     — build axis, one step heavier
appear thinner / leaner                     — build axis, one step lighter
appear <keyword>                            — keyword axis (full catalog, gender filter
                                              bypassed)
appear <persona name>                       — adopt a saved persona (clean swap)
appear                                       — show current overrides + active persona
stop appearing                               — clear all overrides + active-persona pointer
```

Axis-step verbs refuse at the extremes (an unreachable axis value is itself a tell). The canonical clear verb is `stop appearing`; there is no `appear reset` alias.

Each override is conceptually a **skill-based performance** — using the `appear` verb is intended to trigger a Resonance check for that axis. In the foundation cut, no check is implemented; every axis override succeeds unconditionally. The Resonance check call point will be added alongside Phase 5 perception mechanics, when there is a real consumer (per-axis difficulty modeling, opposed-roll tuning) to justify the wiring. Per-axis difficulty modeling is deferred.

The composed sdesc descriptor (`gaunt`, `burly`, etc.) is recomputed from the overridden height + build values via the existing `get_physical_descriptor(height, build)` table. Players override the **components**; the system composes the descriptor.

**What `appear` overrides change:**
- The signature inputs for the affected axes
- The composed sdesc descriptor and/or keyword visible to observers
- The Apparent UID (since signature inputs changed)
- The full keyword catalog is available regardless of the character's real gender

**What `appear` does NOT change:**
- Distinguishing feature (auto-derived from worn items + hair)
- `@longdesc` (looking directly reveals real physical detail until body-mod layers exist)
- Voice (deferred to future communication-system integration)
- The character's real `sleeve_uid` (the underlying body identity)

### Pronouns Under Disguise

Pronouns must follow the disguise. A character presenting as "a woman" should be referenced with feminine pronouns by observers who do not know the real identity, regardless of the disguiser's underlying `sex` attribute. Failing to do so is an immediate identity tell and a defect of the rendering layer.

**Derivation rule:**

1. If the character has an active `keyword_override`, look the override up in the runtime keyword catalog (`ServerConfig` entries under keys `identity.feminine_keywords` / `identity.masculine_keywords` / `identity.neutral_keywords`, falling back to the `_DEFAULT_FEMININE_KEYWORDS` / `_DEFAULT_MASCULINE_KEYWORDS` / `_DEFAULT_NEUTRAL_KEYWORDS` frozensets in `world/identity.py` when a key is unset).
   - Match in the feminine list → render as `she/her/hers`.
   - Match in the masculine list → render as `he/him/his`.
   - Match in the neutral list, **or no match anywhere** (e.g. a custom `@shortdesc` keyword such as `ronin` or `wraith`, which carries no gender metadata in `KeywordEvent`) → render as `they/them/theirs` (singular they).
2. If the character has **no** active `keyword_override`, pronouns derive from the character's real `gender` property as today (no behavior change for undisguised characters).

**Implementation surface (engine PR):**

A single helper, conceptually `get_apparent_gender(char)`, returns one of `"male" | "female" | "neutral"` and is the only function that consumers (`world/emote.py`, `world/grammar.py`'s `transform_pronoun()`, longdesc/sdesc renderers, social templates) call to determine pronouns. The existing `caller.gender` reads inside emote / pose / template paths are redirected through this helper. The helper internally consults the keyword catalog and falls through to `caller.gender` only when no override is active.

**No explicit `gender_override` axis in Phase 3.** Derivation is sufficient: a player who wants to be referred to with a different pronoun set picks a keyword from the desired gender list (the full catalog is available via `appear <keyword>`, gender filter bypassed). An explicit override axis is noted in Future Hooks for the case where a player wants a custom keyword *and* a non-neutral pronoun set.

**Custom-keyword consequence:** Keywords minted via `@shortdesc` (logged as `KeywordEvent` rows) have no gender field on the model. They will always render neutral under this rule. This is acceptable — custom keywords are deliberately ambiguous, and forcing the player to also pick from the gendered catalog if they want gendered pronouns matches the deliberate-tradecraft theme of the system.

### Personas — Player-Facing Persona Recall

Because the identity engine is purely emergent from current state, players need an ergonomic layer to **remember and restore** disguise combinations they have discovered and want to reuse. Personas fill this role.

A persona is a **player-private snapshot** of presentation overrides, captured at the moment of saving and restorable later. Personas are designed in parallel to the planned identity/contact system — same recall, annotation, and (future) web-UI patterns.

> **Status:** The surface verbs (`appear`, `stop appearing`, `personas`, `persona`, `remember me as <name>`, `forget <persona>`), the persona storage schema, the signature engine, Apparent UID derivation, `get_sdesc()` consumption of overrides, pronoun derivation under disguise via `get_apparent_gender`, recognition-memory keying on Apparent UID, the persona `essential_item_types` snapshot + adoption-time advisory, the `lost_contact` orphan-marking flag with its `memory` / `recall` render annotation, the unmasking-moments hook (`apply_signature_change` + `_broadcast_unmasking` + `linked_to` chains + "Also known as" / "(aka ...)" rendering — see §Unmasking Moments), and corpse apparent-UID propagation are all **shipped**.

**A persona stores:**
- A **player-chosen name** (case-insensitive lookup, case-preserving display, player-private — never visible to other characters)
- The **override values** active at save time (height, build, keyword) — `None` for axes that were unset
- The **types of essential disguise items** equipped at save time, captured via `get_essential_item_type_ids()` (sorted, deduplicated)
- A **freeform notes field** for player annotations *(reserved field, currently always empty)*
- A **created-at timestamp** and the **room name** where it was saved

**Pronouns are not stored separately.** Restoring a persona restores its `keyword_override`, and pronouns derive from that keyword via the rule in §Pronouns Under Disguise. A persona that captured a feminine keyword automatically restores feminine pronouns when adopted; a persona that captured a custom keyword automatically restores neutral pronouns. No persona field is needed for gender.

**Personas do NOT generate identities.** They are pure recall aids. When a player adopts a persona, the system applies the captured overrides as a **clean swap** — overwriting all three axes including any unset axes (so adoption produces an exact replay of the saved state, never a merge). The resulting Apparent UID is derived from the restored state, not from the persona itself. Two personas with identical overrides + item-type composition will yield the same Apparent UID — they are just labels in the player's memory.

**Why personas don't carry identity.**

```mermaid
graph LR
    P["persona 'batman'<br/>(player-private label)"]
    S["captured overrides<br/>height='tall', build='stocky',<br/>keyword='figure'<br/>+ essential item types"]
    Sig["identity_signature<br/>(real_sleeve_uid, overrides, items)"]
    UID["Apparent UID<br/>blake2b digest"]
    Mem["observer recognition_memory<br/>keyed on Apparent UID"]
    P -->|adopt: clean swap| S
    S -->|flow into| Sig
    Sig -->|hash| UID
    UID -->|lookup| Mem
    style P fill:#444,stroke:#888,color:#fff
    style UID fill:#226,stroke:#88f,color:#fff
```

> **Worked example — Bruce's two personas, one batsuit.** Bruce saves `"batman"` (height=tall, build=stocky, keyword=figure, items={cowl, cape, armor}) and `"dark-knight"` with the exact same overrides + items. Adopting either produces the same identity signature, the same Apparent UID, and therefore the same recognition tag on every observer. Alfred sees "Batman" whether Bruce ran `appear batman` or `appear dark-knight` — the label is private to Bruce. Conversely, if Bruce saves `"batman-stealth"` with one item swapped (matte cowl instead of standard cowl), the signature differs, the UID differs, and to Alfred he is a stranger until Alfred re-`remember`s him.

**Adoption-time essential-item advisory.** When the player runs `appear <persona>`, the system diffs the persona's saved `essential_item_types` against the player's currently-equipped essential disguise items and emits a yellow heads-up listing missing and extra type IDs when they diverge. Adoption is **not refused** — the player can choose to proceed and accept the resulting Apparent UID divergence. The advisory exists because unlike real life, it's easy in-game to forget which items pair with which persona; the warning is a recall aid, not a gate. This may be revisited later as the player grows more accustomed to the disguise system.

**Cap:** No cap in the surface PR. The previously-floated `min(Resonance × 2, 10)` gating is held for the engine PR or later balance pass.

**Player surface (current grammar — locked):**
- `appear` — show current overrides + active persona
- `appear taller | shorter` — nudge perceived height one step on the `HEIGHTS` scale; refuses at the extremes (an unreachable axis value is itself a tell)
- `appear thinner | fatter` — same on the `BUILDS` scale
- `appear <keyword>` — present as the given keyword; validated against the full keyword catalog (gender filter does not apply to disguise). New keywords are introduced via `@shortdesc`, not via `appear`.
- `appear <persona name>` — restore a saved persona (clean swap)
- `stop appearing` — clear all overrides and any adopted-persona pointer; the only canonical clear verb (no aliases)
- `remember me as <persona name>` — snapshot current overrides as a persona; allowed even with no axes set (intentional — supports saving a baseline)
- `forget <persona name>` — delete a persona; if it was the currently-adopted persona, also clears all overrides **and** clears `db.active_persona` (the active-persona pointer is invalidated whenever its referent ceases to exist)
- `personas` — list saved personas, recency-sorted (newest first); the active persona, if any, is marked with `*`
- `persona <name>` — inspect a single persona's snapshot

**Resolution order for `appear <arg>`:** persona name → axis nudge keyword (`taller`/`shorter`/`thinner`/`fatter`/`bulkier`/`leaner`) → keyword catalog. Persona names take precedence so a player can always reach their own personas; cross-namespace uniqueness (below) prevents real ambiguity.

**Manual axis change after persona adoption** dissociates the active-persona pointer (with an explicit message) but leaves the persona definition intact. The player can re-adopt it later with `appear <name>`. The `db.active_persona` pointer is also cleared by `stop appearing` and by deleting the active persona via `forget`.

**Cross-namespace uniqueness** is enforced (case-insensitive) when saving a persona name *or* assigning a recognition name via `remember <target> as <name>`. A name is rejected if it collides with:
- the keyword catalog (so `appear <name>` stays unambiguous)
- any of the caller's existing recognition `assigned_name`s (so `forget <name>` stays unambiguous)
- any of the caller's existing persona names

The same rule applies in reverse: assigning a recognition name that collides with a persona name or a catalog keyword is rejected with the offending namespace named in the error message.

### Disguise Items

A disguise item is a clothing/equipment item with two declarative properties:

- **`is_disguise_item`** (`bool`): marks the item as belonging to the disguise taxonomy. Disguise items provide a future Phase 5 perception-roll bonus to the disguiser.
- **`disguise_essential`** (`bool`): marks the item as identity-essential. Essential items contribute to the identity signature (their type is hashed into the Apparent UID); non-essential items contribute only visually through the existing distinguishing-feature derivation.
- **`disguise_weight`** (`int`, default `1`): per-item pierce-penalty weight. When worn (and `disguise_essential = True`), the item counts as this many vectors in the `_count_disguise_vectors` calculation. Heavy concealment (full prosthetic mask, hooded robe) can scale piercing difficulty independently of how many items are involved; `0` lets an essential item pin the identity signature without making piercing harder. Negative values are clamped to `0`; non-numeric values fall back to `1`. No effect on non-essential items.

Examples:
- **Essential**: balaclava, full mask, cowl, wig, contacts, prosthetic face, voice modulator (when voice integration lands)
- **Non-essential**: gloves, scarf, signature jacket, distinguishing hat

The item taxonomy itself (which items exist, their categories, quality tiers) is designed in **Phase 3.5**, a separate cut after the foundation lands. The foundation only needs the two flags to function correctly with zero defined disguise items.

### Disguise Adjective

Disguise items can also flag themselves as a visible **red flag** in the wearer's sdesc through two additional attributes:

- **`disguise_adjective`** (`str`): a single descriptor (`"masked"`, `"hooded"`, `"helmeted"`, …) injected between the physical descriptor and the keyword — e.g., `"a tall lean masked droog"`. Honoured **only** when the same item also has `is_disguise_item = True`; an adjective on a non-disguise item is skipped with a soft warning (red-flag style is reserved for the disguise taxonomy).
- **`coverage`** (`list[str]`): the body locations the item hides when worn. The clothing-coverage system is the single source of truth for what an observer cannot see — it gates longdescs, wounds, scars, **and** the hair fallback in the distinguishing-feature chain. To suppress hair, include `"hair"` in the item's coverage list. Replaces the legacy `covers_hair` boolean (removed in #176).

Adjective selection is implemented in `world/identity.py:get_disguise_adjective` and consumed by `compose_sdesc`. When more than one adjective is contributed, the wearer's sdesc shows the most identity-defining one. Priority ranks (lowest wins):

| Adjective | Rank |
|---|---|
| `masked` | 1 |
| `helmeted` | 2 |
| `cowled` | 3 |
| `hooded` | 4 |
| `goggled` | 5 |
| `veiled` | 6 |

Adjectives missing from the priority table are admitted at rank 999 with an alphabetical tiebreak — authors can ship new disguise types via item attribute alone, without editing the priority table.

The adjective is **a visual-only red flag** and contributes nothing to the identity signature. Whether the wearer is recognised across encounters is governed entirely by the signature inputs (overrides + essential item type IDs); the adjective only governs how observers describe them. A `masked` wearer who removes the mask and dons an `helmeted` one shifts both adjective and signature simultaneously, but the adjective change alone (e.g., spec-future "rigid mask" item with the same `disguise_type_id` as a balaclava) would not affect recognition.

### Disguise Completeness

A disguise's effectiveness scales with the player's investment:

| Effort | Result |
|---|---|
| Override one axis (`appear taller`) | Subtle change; observers may notice the same person looking different |
| Override all axes (height, build, keyword) | Strong visual difference; recognition tags from prior signature don't apply |
| Add one essential item (e.g., balaclava) | Signature changes; "unmasking" possible if removed |
| Full ensemble (all axes + multiple essentials) | Distinct identity; harder for observers to connect to real you |
| All of the above + change non-essential clothing | Visual distinguishing feature also changes |
| All of the above + body mod (future) | `@longdesc` no longer reveals the truth on close inspection |

**Vector math — how completeness translates into pierce penalty.**

```mermaid
graph LR
    subgraph Clark["Clark Kent — minimal disguise"]
        C1["glasses<br/>essential, weight=1"]
        C2["keyword_override<br/>'reporter'"]
        C1 --> CSum["vectors = 1 + 1 = 2"]
        C2 --> CSum
        CSum --> CPen["penalty = 2 × DISGUISE_PIERCE_VECTOR_PENALTY<br/>= +2 to target's roll"]
    end
    subgraph Batman["Batman — heavy concealment"]
        B1["cowl<br/>essential, weight=3"]
        B2["cape<br/>essential, weight=1"]
        B3["body armor<br/>essential, weight=2"]
        B4["height_override 'tall'"]
        B5["build_override 'stocky'"]
        B6["keyword_override 'figure'"]
        B1 --> BSum["vectors = 3+1+2 + 1+1+1 = 9"]
        B2 --> BSum
        B3 --> BSum
        B4 --> BSum
        B5 --> BSum
        B6 --> BSum
        BSum --> BPen["penalty = 9 × DISGUISE_PIERCE_VECTOR_PENALTY<br/>= +9 to target's roll"]
    end
```

> **Worked example — disguise weight scales effort, not items.** Clark's "disguise" is famously thin: glasses (weight 1) plus a single keyword override. Two vectors, +2 to his Resonance side of the pierce roll. Batman's cowl is heavy concealment — `disguise_weight=3` on the cowl item triples its contribution without inflating the visible item count. Combined with cape, body armor, and a full override sweep, Batman's penalty hits +9. A would-be piercer needs to beat that gap *and* have rolled up familiarity through prior encounters; with `DISGUISE_PIERCE_FAMILIARITY_CAP=5`, even a Robin-grade analyst maxes out a +5 bonus.

### Disguise Persistence

Override and persona state lives in DB attributes — persists across server restarts, reloads, and crashes. There is no "session" concept; a character who logs out mid-disguise logs back in still disguised.

Personas persist indefinitely until explicitly deleted, regardless of whether the character is currently using their overrides.

### Breaking and Degrading Disguise

Because disguise is continuous, "breaking" simply means changing signature inputs.

**Voluntary `stop appearing`:** Clears all overrides and any active-persona pointer. If no essential items are equipped, the Apparent UID returns to the real `sleeve_uid` and observers who know the real identity auto-recognize. If essential items are still equipped, the signature still differs from real — only the override contribution is removed.

**Death:** All active overrides clear; the corpse stores both `real_sleeve_uid` and a snapshot of the identity signature active at time of death (for forensic gameplay — investigators can reconstruct what the character looked like when they died).

**Admin / GM strip:** Staff command clears all overrides on a target. Equipped items are unaffected (use existing strip commands for those).

**Essential item removed (voluntary or forcible):** Signature changes → Apparent UID changes → observers who tagged the prior signature see a stranger. The "unmasking" moment is mechanical: the signature change *is* the reveal. Equipping the same item type again restores the signature and the recognition.

**Essential item destroyed:** Same effect as removal. If a unique-instance item is destroyed, the player must acquire another item *of the same type* to recover the signature. (Hence: items hash by type, not dbref — buying a new balaclava restores the "balaclava-wearing" identity.)

**Non-disguise clothing changes:** Affect distinguishing feature visually but NOT the signature. Putting on or removing a regular jacket doesn't change who the character appears to be in the recognition system; it just changes the description text.

> **Design note:** Direct combat damage (e.g., head wounds) does not break disguise on its own. The disguise system is decoupled from the damage system. Combat affects disguise *indirectly* by destroying or removing essential items.

**The "unmasking" scenario in detail:**

A disguised character (overrides: `tall man` + essential cowl + non-essential cape) is in a room. An observer has tagged this signature as "Batman."

1. Someone rips off the cowl (forcible removal).
2. The signature changes: cowl is no longer in the essential-items set.
3. The Apparent UID recomputes to a new value.
4. The observer's recognition no longer auto-resolves: "Batman" was tagged against the *previous* UID. They now see the new sdesc as a stranger — `"a tall man in a black cape"` — and may deduce the connection from context, but the system does not auto-link the two identities.
5. If the cowl is re-equipped, the signature returns to its prior value and the observer's "Batman" tag fires again.
6. If the disguised character then does `stop appearing`, both overrides and the active-persona pointer are cleared — the Apparent UID returns to the real `sleeve_uid` (or wherever the remaining signature inputs lead, modulo any still-equipped essential items). Observers who knew the real identity may now auto-recognize the character.

### Recognition Interactions

- **Stranger meets disguised character:** Observer sees the disguised sdesc; no auto-recognition. Observer can `remember` them by a name, which binds to the current Apparent UID.
- **Observer who knew real identity meets the disguised character:** The observer's recognition entry was keyed on the Apparent UID of the *undisguised* signature (real `sleeve_uid` + no overrides + no essential items). The disguise produces a *different* Apparent UID; no auto-recognition. The observer sees the disguised sdesc as a stranger.
- **Observer meets the same disguised character a second time, same signature:** Auto-recognition fires (same Apparent UID); observer sees the previously-assigned name.
- **Observer meets the same disguised character a second time, different signature** (e.g., one essential item swapped): Different Apparent UID; observer sees a stranger.
- **Two characters wearing identical overrides + items:** Visual collision (sdesc strings match), but Apparent UIDs differ (different salts). Each observer's recognition is per-UID; impersonation is *visual*, not *systemic*. An impostor *looks* the same but does not auto-resolve to the original's assigned name. Successful name-fooling requires either acquiring the original's salt (future adversarial-identity mechanic — e.g., through stolen contact cards) or the observer manually `remember`ing the same name onto the impostor's distinct UID.
- **Observer meets a previously-tagged disguise that has since been abandoned and never re-presented:** The recognition entry is preserved but its Apparent UID never matches anyone in the room. After a configurable inactivity window (deferred to balance pass), the entry is marked `lost_contact = True` and rendered with a "(lost contact)" annotation in `memory` and `recall`. The entry is never auto-pruned — player notes and lore on the entry remain valuable even when the trail has gone cold.

### Unmasking Moments

When a character's identity signature changes in a populated room, the observers in that room are *eyewitnesses* to the transition. The recognition system captures this synchronously through the **unmasking-moments hook**: a single broadcast pass over the room's conscious observers that updates each observer's recognition memory based on what they already knew about the old and new signatures.

This is the bridge that keeps disguise legible after the fact. Without it, a signature change would silently produce a new stranger UID with no link to the prior presentation — observers would have no in-system way to know that "the masked figure" and "the bareheaded woman" are the same body. With it, observers who watched the change get an explicit linkage (`linked_to`) plus a `lost_contact` flag on the prior presentation, and the "Also known as" rendering surfaces the connection in `recall` and `memory`.

**Implementation surface:**

- **`apply_signature_change`** (`world/identity.py`) — a context manager that wraps any mutation that may change the actor's identity signature. Captures observers + old signature *before* the mutation, then dispatches `_broadcast_unmasking` *after*, but only if the signature actually changed.
- **Wrapped mutation sites:**
  - `commands/CmdCharacter.py`: `_clear_all_overrides` (source `stop_appearing`), `_nudge_height` (`override:height`), `_nudge_build` (`override:build`), `_set_keyword_override` (`override:keyword`), `_adopt_persona` (`persona:<name>`).
  - `typeclasses/clothing_mixin.py`: `wear_item` (`wear_item`) and `remove_item` (`remove_item`) — guarded so the wrap is skipped unless the item has `disguise_essential = True`.
- **Observer collection** — `_collect_unmasking_observers` walks the actor's room, filters to `Character` instances excluding the actor, and drops anyone whose `is_unconscious()` returns truthy (defensive `AttributeError` handling treats failure as conscious).

**Broadcast matrix.** For each observer, the hook evaluates whether the observer's recognition memory contains the old UID, the new UID, both, or neither, and writes accordingly:

| Cell | Observer knew old? | Observer knew new? | Action |
|---|---|---|---|
| **A** | No | No | No-op. Observer has no recognition tag for either presentation. |
| **B** | Yes | No | Flip old entry's `lost_contact = True`. Auto-create a new entry under the new UID with `linked_to = old_uid` and a blank `assigned_name` so the observer can later `remember` the new presentation and the link is preserved. |
| **C** | No | Yes | Refresh the new entry's `last_seen` / `location_last_seen` / `sdesc_at_last_encounter`; clear its `lost_contact`. No link formed — the observer never met the old presentation, so there is nothing to chain. |
| **D** | Yes | Yes | Flip old entry's `lost_contact = True`. Refresh the new entry as in cell C. Set `linked_to = old_uid` on the new entry *only if* it is currently `None` (never overwrite an existing chain link). Both `assigned_name` values are preserved. |

**Chain semantics.**

- `linked_to` forms a **one-directional chain** new → old. Walking the chain (`world/identity.py:walk_linked_chain`) terminates on `None`, on a cycle (logged and broken), or on `_LINKED_CHAIN_MAX_HOPS = 64` (defensive guard).
- `get_linked_aliases(memory, current_uid)` walks the chain from `current_uid` and returns the list of non-empty `assigned_name`s from prior presentations. The renderer uses this to emit `Also known as: |w<name1>|n, |w<name2>|n` in `recall` and `\n|x(aka <names>)|n` in the `memory` table.
- The chain is *not* bidirectional — viewing an old entry does not currently surface the new presentation's name. Forward-only walk was chosen for simplicity and is sufficient for the "Also known as" UX. If a future need arises (e.g. "this name was later replaced by..."), the inverse walk can be added without schema change.
- **Forget interaction:** Forgetting the *old* entry leaves the new entry's `linked_to` pointing at a missing UID; `get_linked_aliases` silently terminates the walk via `memory.get(next_uid)`. No dangling-reference error.

**Per-cell narrative flavor.** `_send_unmasking_message` emits per-observer prose, dispatched as a direct `.msg()` call rather than through `msg_room_identity` (the recipient list is already narrowed by `_collect_unmasking_observers`, and the prose is tailored to what *this* observer knew going in). The cell-B and cell-D templates follow the same noir, recognition-centric voice as the wear/remove emote pipeline:

| Cell | Prose |
|------|-------|
| A | (never reaches the hook) |
| B | `"{new_sdesc} steps into view where {old_sdesc} stood a moment ago."` |
| C | silent — the observer already knew the new presentation; nothing to learn |
| D | `"You realize that {old_sdesc}, who you call {old_name}, and {new_sdesc}, who you call {new_name}, are the same person."` |

Cell D falls back to the shorter `"You realize that {old_sdesc} and {new_sdesc} are the same person."` template if either `assigned_name` is blank (defensive — cell D by definition has both, but a future code path that drops one should still produce coherent prose). Cell B suppresses the message entirely if either sdesc is missing, rather than ship a malformed line.

**Unmasking matrix in motion.**

```mermaid
sequenceDiagram
    participant Peter as Peter Parker
    participant CM as apply_signature_change
    participant Coll as _collect_unmasking_observers
    participant Bcast as _broadcast_unmasking
    participant MJ as MJ (knew Spider-Man only)
    participant May as Aunt May (knew Peter only)
    participant Ned as Ned (knew both)

    Peter->>CM: __enter__ → snapshot old_uid (Spider-Man signature)
    Peter->>Peter: remove_item(mask) [essential, disguise_essential=True]
    Peter->>CM: __exit__ → compute new_uid (Peter signature)
    CM->>CM: old_uid != new_uid → proceed
    CM->>Coll: collect observers in room
    Coll-->>CM: [MJ, May, Ned] (conscious, in-room, not self)
    CM->>Bcast: broadcast(old_uid, new_uid, observers)
    par per-observer cell decision
        Bcast->>MJ: knew old(Spider-Man), no new → cell B<br/>flip Spider-Man entry lost_contact=True<br/>auto-create stub for new_uid, linked_to=Spider-Man uid<br/>msg "Peter steps into view where Spider-Man stood..."
    and
        Bcast->>May: no old, knew new(Peter) → cell C<br/>refresh Peter entry last_seen<br/>silent
    and
        Bcast->>Ned: knew old AND new → cell D<br/>flip Spider-Man entry lost_contact=True<br/>refresh Peter entry; set linked_to=Spider-Man uid (only if None)<br/>msg "You realize Spider-Man... and Peter... are the same person."
    end
```

> **Worked example — Peter unmasks in front of three observers.** Peter Parker (real `sleeve_uid = peter-uuid`) has been operating with `keyword_override="vigilante"` plus an essential mask. **MJ** has only ever met "Spider-Man" — she knows the masked Apparent UID. **Aunt May** has only ever met "Peter" — she knows the bare Apparent UID. **Ned** has met both presentations on separate occasions and tagged each. Peter pulls off the mask inside `apply_signature_change`. The old UID (Spider-Man) and new UID (Peter) differ, so `_broadcast_unmasking` walks the room: MJ hits **cell B** (new auto-stub linked to her Spider-Man entry, lost-contact flag on the old, narrative prose), May hits **cell C** (her Peter entry just gets a `last_seen` refresh, no prose), Ned hits **cell D** (both entries refreshed, link forged new→old, prose calling out the realization by name). All three observers now hold a forward chain `Peter UID → Spider-Man UID`, and `get_linked_aliases` will surface "Also known as Spider-Man" in MJ's and Ned's `recall` output.

### Disguise Piercing

When an observer sees a character whose current Apparent UID is **not** in their recognition memory, the display-name pipeline gives them one more chance: if they've previously remembered the same underlying sleeve under a *different* presentation (the "bare-face entry"), an opposed Intellect-vs-Resonance roll decides whether they see through the disguise.

This is the standing complement to the eyewitness Unmasking Moments hook (§Unmasking Moments). Unmasking handles the case where the observer *witnesses* a transition; piercing handles the case where the observer encounters a familiar sleeve already wearing a disguise they did not see go on.

**Trigger.** `Character.get_display_name(looker)` (and its richer sibling `get_look_header`) first try a direct `recognition_memory[apparent_uid]` lookup. On miss, they call `world.identity.attempt_display_pierce(looker, self, apparent_uid)` before falling back to the articled sdesc. The pierce wrapper:

1. Calls `find_entries_by_real_sleeve_uid(looker, self.sleeve_uid)` to gather every entry the looker has for this underlying sleeve.
2. Filters out the current `apparent_uid` (the disguised presentation can't pierce itself) and any candidate without an `assigned_name`.
3. Returns `None` if no candidates remain.
4. Picks the **first** candidate (insertion order — corresponds to the earliest presentation the looker remembered for this sleeve) and defers to `attempt_disguise_pierce` for the roll.

**The roll.** `attempt_disguise_pierce(observer, target, apparent_uid, bare_entry)` rolls opposed `Intellect` (observer) vs `Resonance` (target) via `world.combat.dice.opposed_roll`, with:

- **Familiarity bonus** added to the observer's effective total: `min(bare_entry["times_seen"], DISGUISE_PIERCE_FAMILIARITY_CAP)`. The cap (default 5) keeps a grizzled veteran from auto-piercing every disguise on Earth.
- **Disguise penalty** added to the target's effective total: `DISGUISE_PIERCE_VECTOR_PENALTY * count_of_active_vectors`. Vectors are worn `disguise_essential` items (each contributing its `disguise_weight`, default `1`) plus the three string overrides (`height_override`, `build_override`, `keyword_override`), each contributing `1`. Heavier disguises are harder to see through; an item with `disguise_weight = 3` (e.g. a full prosthetic mask) triples its contribution, while `disguise_weight = 0` lets a cosmetic essential pin the identity signature without affecting the pierce roll.

Success condition: `(observer_roll + familiarity) > (target_roll + penalty)`. Ties favour the target (the disguise holds).

**Caching.** The outcome is cached permanently per `(observer, target, apparent_uid)` triple on `observer.db.disguise_pierce_cache = {(target.dbref, apparent_uid): bool}`. This mirrors the corpse forensic-recovery contract (`typeclasses/corpse.py:_attempt_forensic_recognition`): one careful look determines the verdict, no re-roll abuse on every `look`. The cache key includes `apparent_uid` so changing the disguise (puts on a hat, swaps a coat) re-rolls; the previous presentation's cached outcome is irrelevant to the new one.

Observers or targets without a `dbref` are not cached and re-roll on every call (keeps the cache bounded; no junk keys for tooling that walks characters without a real observer). The cache survives reloads (it's on `db`, not `ndb`) and persists across sessions — by design: a player who has decided "I do not recognise this person" should not be magically reset to undecided on a server restart.

**dbref recycling.** Cache entries for deleted targets are dead weight but cannot misfire: Evennia/Django primary keys are monotonically allocated and never reused, so a freshly-created object will never collide with a stale entry. No prune-on-delete hook is wired; entries accumulate at the rate the observer encounters distinct presentations, bounded in practice by their social surface. If pruning becomes warranted (very long-lived observers + churn-heavy NPC populations), the right place to add it is an `at_object_delete` broadcast on the target side mirroring the unmasking-moment pipeline.

**`forget` invalidation (PR #211, issue #210).** When an observer
runs `forget <target>`, every cache entry on
`observer.db.disguise_pierce_cache` whose target shares the
forgotten entry's `real_sleeve_uid` is dropped — across **all**
apparent UIDs for that sleeve, not just the current presentation.
Rationale: `forget` declares "I no longer claim to know this
person"; a stale `True` verdict from a prior pierce would otherwise
short-circuit future `look`s and silently restore the recognition
the player just disowned.  The clear is scoped to the caller; other
observers' caches are untouched (their verdicts are their own).
Implementation: `commands.CmdCharacter.CmdForget._forget_visible`
reads the entry's stored `real_sleeve_uid` (falling back to the
target's live `sleeve_uid` for pre-schema entries) and calls
`world.identity.invalidate_pierce_cache_for_sleeve(observer,
sleeve_uid)` before clearing the entry's `assigned_name`.  Keying
on `sleeve_uid` rather than dbref ensures the clear covers
backfilled presentations of the same body.

**Tunables.** Recognition/disguise balance constants, all defined in `world/identity.py`:

| Constant | Default | Effect |
|---|---|---|
| `DISGUISE_PIERCE_VECTOR_PENALTY` | `1` | Per-vector roll penalty added to the target's effective total in `attempt_disguise_pierce`. |
| `DISGUISE_PIERCE_FAMILIARITY_CAP` | `5` | Ceiling on the `times_seen` bonus added to the observer's effective total. |
| `LOST_CONTACT_THRESHOLD_SECONDS` | 30 in-game days | Inactivity window before `mark_lost_contact_entries` flips an entry to `lost_contact = True`. |
| `RECOGNITION_BUMP_THROTTLE_SECONDS` | `300` | Per-`(observer, uid)` write throttle on passive recency bumps via `bump_recognition_recency`. |

All four are balance-pass provisional. The pierce constants tune roll difficulty; the recency constants tune memory hygiene.

**Pierce flow at a glance.**

```mermaid
sequenceDiagram
    participant Lois as Lois (observer)
    participant Disp as get_display_name
    participant Pierce as attempt_display_pierce
    participant Roll as attempt_disguise_pierce
    participant Dice as world.combat.dice.opposed_roll

    Lois->>Disp: looks at "a tall man in glasses"
    Disp->>Disp: recognition_memory[apparent_uid] → miss
    Disp->>Pierce: try pierce(looker, target, apparent_uid)
    Pierce->>Pierce: find_entries_by_real_sleeve_uid(Clark.sleeve_uid)
    Note over Pierce: 1 candidate: "Superman" entry<br/>(different apparent_uid)
    Pierce->>Roll: attempt_disguise_pierce(Lois, Clark, uid, bare_entry)
    Roll->>Dice: opposed_roll(Lois.Intellect, Clark.Resonance)
    Dice-->>Roll: observer_total=12, target_total=9
    Note over Roll: +familiarity = min(times_seen, 5) = 4<br/>+penalty = vectors × DISGUISE_PIERCE_VECTOR_PENALTY<br/>vectors: glasses(1) + keyword "reporter"(1) = 2
    Roll-->>Roll: 12+4=16 > 9+2=11 → pierce!
    Roll->>Roll: cache[(Clark.dbref, uid)] = True
    Roll-->>Pierce: "Superman"
    Pierce-->>Disp: "Superman"
    Disp-->>Lois: "Superman (a tall man in glasses)"
```

> **Worked example — Lois Lane scrutinises Clark Kent.** Lois has tagged Clark's *Superman* presentation (no glasses, no "reporter" keyword) and seen him fly four times (`times_seen = 4`). When she runs into "a tall man in glasses" at the Daily Planet, the disguised Apparent UID misses her memory; the pierce path finds her Superman entry as the sole candidate. Opposed roll: Lois rolls **12** on Intellect; Clark rolls **9** on Resonance. Add Lois's familiarity bonus (**+4**, under the cap of 5) and subtract Clark's disguise penalty (**+2** to his side: glasses essential item of weight 1, plus one keyword override). Final: **16 > 11**, pierce succeeds, outcome cached on Lois — she now sees `"Superman (a tall man in glasses)"` and will keep seeing it until Clark changes his signature.

**Surface.** On success, the looker sees the bare-face entry's `assigned_name` in place of the articled sdesc — same surface as ordinary recognition. The `get_look_header` path further attaches the *current* (disguised) sdesc in parentheses, so the looker sees `"Bruce (a tall figure in a black coat)"` rather than the stranger fallback.

**No auto-link.** Piercing surfaces a name but does **not** write `linked_to` on the disguised presentation's entry — there is no entry to link, by definition. If the looker subsequently runs `remember <pierced name>`, the `_remember_target` builder auto-links the freshly-created entry to the first other-presentation entry it finds for the same `real_sleeve_uid` (insertion order, mirroring `attempt_display_pierce`'s candidate selection). The look chain therefore reads new → bare-face, the same shape `recall` / `memory` already render for unmasking-witnessed transitions.

### Impersonation

Impersonation is **emergent**, not mechanical. The system does not detect or prevent it.

Two characters can create overrides + ensembles with identical descriptors, keywords, and similar clothing — they will look the same in the sdesc but have different Apparent UIDs (different salts). This means:

- **Strangers** seeing both at different times would have no way to distinguish them visually. A character who met "Natasha" on Monday and meets a different `short woman in a black cape` on Friday would naturally assume it's the same person — until they `remember` them by a name and discover the recognition system creates a *new* entry instead of matching the old one.
- **People who tagged the original signature** are not fooled by a visual look-alike — the UIDs don't match. The impostor appears as a stranger who happens to look similar.
- **Investigation gameplay** emerges naturally: if a witness meets two different UIDs with matching sdescs, that's a clue that one of them is an impostor. Which one is "real" requires further investigation.

Building a reputation — having many people tag a recognized signature — is itself a form of identity security. The more people who "know" a signature, the harder it is for a visual impostor to operate in those social circles.

> **Design note:** Mechanical disguise piercing **is** implemented (see [Disguise Piercing](#disguise-piercing)). What remains deferred is *active* impersonation detection — surfacing a soft hint like "this person reminds you of someone..." when a fresh signature closely matches a known one *without* a shared `sleeve_uid`. That requires similarity scoring across signatures and is out of scope for the current cut.

### Photos & Forensic Artifacts (Forward Hooks)

The salt-based design makes photos and other identity artifacts naturally expressive in future phases. A photo captures the identity signature at a moment in time, including the subject's real `sleeve_uid`.

- A character finding a photo of *their own* past disguise gets a recipe to rebuild it (overrides + essential item types). Their salt matches → they can become that past signature again.
- A character finding a photo of *someone else's* disguise gets the recipe but not the salt. They can *visually* impersonate but not be auto-recognized as the original.
- An investigator with a photo can compare its signature to a person they meet to verify "is this the person in the photo" — including across disguise changes if essential elements match.

These mechanics are not implemented in the foundation cut; they are noted to confirm the architecture supports them.

### Future Hooks (Not in Foundation Cut)

These are designed into the architecture but not implemented yet:

- **Per-axis Resonance checks on `appear`**: Currently always succeeds. Future: per-axis difficulty, opposed or threshold rolls, with failure meaning the override doesn't take effect or appears unconvincing.
- **Clothing coverage gating**: No coverage requirement for now. Future: certain overrides require minimum body coverage to be plausible (e.g., can't `appear bulkier` while shirtless because there's no padding to sell it). Boots/shoes can sell height changes; bulky clothing can sell build changes.
- **Disguise item quality tiers**: All disguise items equal in foundation. Future: cheap rubber mask vs. high-tech prosthetic affects perception bonuses.
- **Perception checks (shipped)**: See [Disguise Piercing](#disguise-piercing). Opposed Intellect-vs-Resonance with familiarity bonus and per-vector penalty.
- **Active impersonation detection (Phase 5)**: Resonance-based hints when a *fresh* signature (different `sleeve_uid`) closely matches a known identity (e.g., *"this person reminds you of someone..."*).
- **Forcible item removal via grapple**: Requires grapple-system integration for stripping equipment from a grappled character.
- **Pharmaceutical / biomod items**: Consumable or implanted modifications that override `@longdesc` and contribute to the identity signature (extending the signature function with body-mod inputs). Closes the last gap: with body mods, even direct `look` reveals a different person. Pharmaceuticals would be temporary (wears off over time), potentially expensive/rare, and could carry side effects (stat penalties, addiction).
- **Photos / identity artifacts**: Captured signature snapshots usable as recipes (own personas) or investigation tools (others'). Salt-acquisition mechanics enable true impersonation gameplay. Ties into Phase 4 (cybernetics) where digital identity data becomes hackable and forgeable.
- **Voice modulation**: Integration with say/whisper/communication so voice becomes part of the identity signature for observers who can hear but not see (or in addition to visual identification).
- **Web UI integration**: Personas designed to mirror the planned identity/contact archive system; eventual web UI surface for managing personas, photos, and contact memory in one place.
- **Salt-acquisition mechanics for true impersonation**: Stolen contact cards, hacked digital identities, and other adversarial means by which an impostor can acquire the original's salt and become auto-recognized as them.
- **Explicit `gender_override` axis**: Phase 3 derives pronouns from `keyword_override` against the catalog's gender lists, so a player who wants gendered pronouns picks a gendered keyword. A future explicit override axis would let a player pair a custom (`@shortdesc`) keyword with a chosen pronoun set without forcing them through a catalog keyword. Deferred until a real player need surfaces.
- **Forensic linking of multiple Apparent UIDs to one real identity**: Investigation gameplay where a sufficiently-resourced investigator can correlate multiple recognition entries (different Apparent UIDs) and infer they refer to the same underlying `sleeve_uid`. Requires evidence-system integration (Phase 5+).
- **Player-initiated lost-contact pruning**: A `forget --lost` (or similar) command letting players explicitly drop entries the system has marked `lost_contact`. Auto-pruning is deliberately not done; this gives the player the choice.

### Testing Notes

The identity test suite mixes two patterns:

- **Fast unit tests** (`world/tests/test_identity.py`, `test_identity_commands.py`, `test_unmasking.py`, `test_character_identity.py`, `test_corpse_identity.py`) use `unittest.TestCase` with fake observer/target/room objects defined per-module. Most pierce/unmasking/recognition logic is covered this way for speed and isolation. Shared schema helpers live in `world/tests/_identity_helpers.py` (notably `make_recognition_entry`, which keeps fake entries in sync with the production schema).
- **End-to-end integration tests** (`world/tests/test_pierce_integration.py`, `test_unmasking_integration.py`) use `evennia.utils.test_resources.EvenniaTest` with real `Character` typeclasses, real `recognition_memory`, and real persistent attributes. These catch regressions that mock-based suites cannot — typeclass wiring, `AttributeProperty` round-trips, and hooks like `at_post_move` that depend on real Evennia object lifecycle.

**`evennia test` uses the live development database.** Tests that touch the keyword catalog must patch `world.identity.ServerConfig.objects.conf` to return a deterministic value (typically `None` to force the default-frozenset fallback); otherwise they pick up live `KeywordEvent` rows and become non-reproducible. The `attempt_disguise_pierce` path performs a local import of `world.combat.dice.opposed_roll` — patches must target `world.combat.dice.opposed_roll`, not `world.identity.opposed_roll`.

Run a single module:

```
docker exec gelatinous evennia test --settings settings.py \
    world.tests.test_identity
```

Run the full identity surface:

```
docker exec gelatinous evennia test --settings settings.py world.tests
```

---

## Per-Observer Rendering

### The Core Technical Challenge

Every room message referencing a character must render differently for each observer. When "Jorge attacks the bandit":
- Observer A (knows both): `"Jorge attacks Skullface."`
- Observer B (knows neither): `"A lanky man attacks a wiry droog."`
- Observer C (knows Jorge only): `"Jorge attacks a wiry droog."`

This affects every system that sends messages to rooms: combat, movement, communication, emotes, environmental events.

### `msg_room_identity` Helper

A centralized helper replaces direct `msg_contents()` calls for any message referencing characters:

```python
def msg_room_identity(
    location,
    template,
    char_refs,
    exclude=None,
    pre_resolved_refs=None,
    **kwargs,
):
    """Send identity-aware message to all observers in a room.

    Args:
        location: Room to broadcast in.
        template: Message string with {placeholder} tokens for characters.
        char_refs: Dict mapping placeholder names to Character objects.
            e.g., {"actor": attacker_obj, "target": target_obj}
        exclude: Characters to exclude from receiving the message.
        pre_resolved_refs: Optional snapshot mapping of the shape
            ``{placeholder: {observer: display_name}}``.  When set,
            an observer's entry under a placeholder is used verbatim
            instead of calling ``char.get_display_name(observer)``.
            See "Action Broadcast Sdesc Stability" below.
    """
```

Usage:
```python
msg_room_identity(
    location=room,
    template="{actor} attacks {target} with a knife!",
    char_refs={"actor": attacker, "target": target},
    exclude=[attacker, target],
)
```

### Performance Characteristics

For a room with N observers and a message referencing M characters:
- **Dict lookups**: N × M (recognition memory lookups)
- **String operations**: N × M (placeholder replacements)

With 20 observers and 2 character references: 40 dict lookups + 40 string replacements. This is trivial — microsecond-scale work per message.

**NPC memory storage**: An NPC that has encountered 500 unique characters stores a dict with 500 keys. Each entry is ~500 bytes of metadata. Total: ~250KB per well-traveled NPC. Acceptable.

**Scaling concern**: The real cost is not runtime performance but **refactoring scope**. Every `msg_contents()` call and every `.key` reference in message strings across the codebase must be converted to use `msg_room_identity` or route through `get_display_name`. This is a large, methodical effort (Phase 2).

### Action Broadcast Sdesc Stability

A subtle hazard arises whenever the action being broadcast *mutates the
actor's own sdesc inputs*.  The canonical example is a disguise item:

```python
char_refs = {"actor": caller}
caller.wear_item(item)        # mutates worn_items, changing the sdesc
msg_room_identity(
    location=caller.location,
    template=f"{{actor}} puts on {item.key}.",
    char_refs=char_refs,
    exclude=[caller],
)
```

By the time `msg_room_identity` calls `caller.get_display_name(observer)`,
the worn-items mutation has already taken effect.  The actor's sdesc now
includes the disguise's `disguise_adjective` and `worn_sdesc_short`
feature, producing a broadcast like:

> *a lithe masked droog in a black balaclava puts on a black balaclava.*

The action message describes the actor as if the action had already
landed on their appearance — the actor cannot be the subject of the
"puts on a balaclava" sentence while *already wearing* the balaclava.

**Snapshot idiom.**  Capture per-observer display names *before* mutating
state, then pass them via `pre_resolved_refs`:

```python
char_refs = {"actor": caller}
pre_resolved = {
    placeholder: {
        obs: char.get_display_name(obs)
        for obs in caller.location.contents
        if obs is not caller and hasattr(obs, "msg")
    }
    for placeholder, char in char_refs.items()
}
caller.wear_item(item)
msg_room_identity(
    location=caller.location,
    template=f"{{actor}} puts on {item.key}.",
    char_refs=char_refs,
    exclude=[caller],
    pre_resolved_refs=pre_resolved,
)
```

The snapshot is **defensive**: every placeholder in `char_refs` is
captured, not only the one known to mutate today.  This protects future
multi-actor templates (e.g. a forced-equip command with both
`{actor}` and `{victim}`) without requiring per-call audits.

**When to apply the snapshot idiom.**  Any command whose body mutates
attributes that feed into `compose_sdesc` *for an actor referenced by
the broadcast template*:

- `wear` / `remove` (clothing changes feature partition and
  disguise adjective)
- `rollup` / `unroll`, `zip` / `unzip` (style changes can swap
  `worn_sdesc_short`)
- Future: `wield` / `unwield` if weapons ever feed sdesc; `appear`
  command overrides; transformation effects.

Commands that mutate non-broadcast actors (e.g. an admin command
forcing another character's sdesc) need the snapshot for *that*
character, not the caller — `_snapshot_actor_names` snapshots every
placeholder defensively for exactly this reason.

**Article grammar.**  The same neutral-introduction broadcasts that
benefit from the snapshot also need indefinite-article grammar on the
item being acted upon: `"puts on a black balaclava"` not
`"puts on black balaclava"`.  Use `world.grammar.get_article` (or the
`_articled` helper in `commands/CmdClothing.py`) when interpolating an
item key into the template; for lists of items use
`evennia.utils.utils.iter_to_str` over `[_articled(k) for k in keys]`.
Error messages and possessive forms (`"the X"`, `"their X"`) are left
untouched — only neutral introductions need the article fix.

---

## Target Resolution

Currently, players type character names to target them. With the recognition system, targeting must work with assigned names, sdescs, and ordinals.

### Targeting Priority

When a player types a targeting string (e.g., `attack jorge` or `attack tall man`):

1. **Magic keywords** — `me` / `self` resolve to the caller; `here` resolves to the caller's location. These short-circuit *before* the identity filter so they always work, regardless of permissions. (Without this shortcut the identity filter strips the caller from `super().search('me')` results because `is_identity_match(self, self, 'me')` is False, breaking `look me` for non-Builders.)
2. **Assigned names** — Check the player's recognition memory for any character in the room whose assigned name matches the input
3. **sdescs** — Match against visible characters' sdescs (partial matching, case-insensitive)
4. **Ordinals** — `"2nd tall man"` uses the existing ordinal system (`get_search_query_replacement`)
5. **Real keys** — Fall through to standard Evennia search (matches `.key` and aliases)

### Implementation Approach

Override `Character.get_search_candidates()` (already exists at `characters.py:515-556`) to inject recognition-aware search results for the searching character. Alternatively, add a custom search hook that checks the searcher's recognition memory.

The existing `CmdAttack` manual substring search (`core_actions.py:110-120`) must be updated to search against assigned names and sdescs, not just `.key`.

### Command Authoring Rule

When a command resolves a **character** target from player input, it MUST go through the identity pipeline. There are exactly two acceptable paths:

1. **Plain caller search** — `caller.search(name)` with **no** scope-narrowing kwargs (no `global_search=`, no `candidates=`, no `location=`, no `attribute_name=`). The `Character.search` override (`typeclasses/characters.py:1176`) applies the identity filter only on this code path. Any scope kwarg causes Evennia's base `ObjectDB.search` to be called and the filter is bypassed (documented at `characters.py:1201–1206`, bypass at `:1251`).
2. **Explicit identity helper** — `world.search.identity_match_characters(searcher, query, candidates)` when you must pre-narrow the candidate set (e.g. cross-room scans, combat handler-managed rooms, victim resolution within a grapple). Validate a single candidate with `world.search.is_identity_match(searcher, target, query)`.

A thin wrapper, `commands._identity_targeting.resolve_character_target(caller, query, candidates=None)`, encapsulates the common cases (same-room targeting with Builder-by-key fallback, ambiguity messaging) and SHOULD be preferred by new commands.

#### Anti-patterns (forbidden for character targets)

```python
# WRONG — manual key/name substring loops bypass recognition entirely.
for char in caller.location.contents:
    if name.lower() in char.key.lower():
        target = char
        break

# WRONG — passing candidates= or location= bypasses the identity filter.
target = caller.search(name, candidates=caller.location.contents)
target = caller.search(name, location=room)

# WRONG — global_search=True bypasses the filter and exposes real keys.
target = caller.search(name, global_search=True)
```

#### Correct usage

```python
# Same-room character target — plain search runs the identity filter.
target = caller.search(name)

# Pre-narrowed candidate set (e.g. combatants, victims of a grapple).
from world.search import identity_match_characters
matches = identity_match_characters(caller, name, candidates)

# Validate a single known candidate against a query.
from world.search import is_identity_match
if is_identity_match(caller, victim, name):
    ...
```

#### Admin commands

Staff commands that need cross-room reach (`@longdesc`, `@heal`, `@testdeath`, etc.) follow a **dual-path** convention: try `identity_match_characters` against the caller's room first (so disguised neighbors resolve via identity, not real key), then fall back to `evennia.search_object(query)` filtered to characters for global key matching. `commands._identity_targeting.resolve_admin_target(caller, query)` provides this pattern.

Item targets (inventory, weapons, room objects) are out of scope for this rule — items do not participate in the identity system, so `caller.search(name, candidates=inventory)` and `caller.search(name, location=caller)` remain correct for item lookups.

#### Canonical examples

- **Same-room combat**: `commands/combat/core_actions.py` (`CmdAttack`)
- **Same-room inventory exchange**: `commands/CmdInventory.py` (`CmdGive`)
- **Same-room medical**: `commands/CmdConsumption.py` (`CmdInject`)
- **Cross-room combat target**: `commands/combat/movement.py` (`CmdAdvance`, `CmdCharge`)
- **Admin dual-path**: `commands/CmdCharacter.py` (`@longdesc`)

### Ambiguity Resolution

If multiple characters match the same target string:
- Ordinals resolve: `"2nd tall man"` → second matching character
- If no ordinal and multiple matches, prompt the player: `"Which one? There are two tall men here."`
- Assigned names should be unique within a player's recognition memory (reassignment overwrites)

---

## Staff Vision

Staff see real names via a cyberware effect auto-granted to all staff characters. This is not a special-case code path — it's the same cyberware system available to players (future).

### Display Format

```
A lanky man [Jorge Jackson] is standing here.
A compact woman [Maria Santos] attacks a heavyset droog [Viktor Kozlov].
```

The real name appears in brackets after the sdesc or recognized name.

### Implementation

A condition/effect on the character (similar to how medical conditions work) that sets a flag checked by `get_display_name`:

```python
def has_identity_overlay(self):
    """Check if this character has identity-revealing cyberware."""
    # Future: check for actual cyberware
    # For now: check for staff overlay condition
    return self.check_permstring("Builder")  # Temporary until cyberware exists
```

The Phase 1 implementation can use a simple permission check as a stopgap. When the cyberware system is built, this becomes a real implant check.

---

## Flash Clone Interaction

Flash clones inherit physical attributes from the original body, including `sleeve_uid`:

| Attribute | Inherited? | Notes |
|---|---|---|
| `sleeve_uid` | Yes | Same physical body template → same recognition |
| `height` | Yes | Physically identical |
| `build` | Yes | Physically identical |
| `hair_color` | Yes | Physically identical |
| `hair_style` | Yes | Physically identical |
| `sex` | Yes | Physically identical |
| `sdesc_keyword` | Yes | Same player preference |
| Brain organ | New (empty) | Fresh brain → blank recognition memory |
| `key` | Modified | Incremented numeral (Jorge → Jorge II) |
| `stack_id` | Yes | Same consciousness |

### Consequences

- **Others recognize the clone**: Anyone whose recognition entry was tagged against Jorge's undisguised Apparent UID (derived from Jorge's `sleeve_uid` + no overrides + no essential items) auto-recognizes Jorge II in his undisguised state — Jorge II's `sleeve_uid` is inherited, so his undisguised Apparent UID matches Jorge's. Recognition entries tagged against Jorge in disguise transfer the same way: same body + same overrides + same items = same UID.
- **Clone recognizes nobody**: Jorge II starts with an empty brain. Every person is a stranger. This is a significant gameplay consequence of death and resleeving.
- **Digital memory (future)**: If the original backed up their cyberbrain, the clone could restore contacts. Without backup, digital memory is also lost.
- **The clone's system `key` (Jorge Jackson II)** is not what others see — they see whatever name they previously assigned to that sleeve_uid, or the sdesc if they never met the original.

---

## Forensic Integration (Future)

Recognition ties into the existing partial forensic system:

### Blood Pools (`typeclasses/objects.py`)

Blood pools currently store the character's name. With recognition:
- The forensic display routes through the investigator's recognition memory
- If the investigator recognizes the bleeder's sleeve_uid: `"This blood appears to belong to Jorge."`
- If not: `"This blood appears to belong to a lanky man."` (or just `"someone"` if no sdesc data is stored on the blood pool)
- Blood pools should store `sleeve_uid` and `sdesc_at_time` in addition to the existing character name

### Corpses (`typeclasses/corpse.py`)

Corpses already preserve forensic data (original name, dbref, physical description, longdesc, skintone, gender). With recognition:
- `sleeve_uid` is propagated to the corpse — **shipped** (PR #133).
- Looking at a corpse: investigator sees recognized name or sdesc based on their memory — **shipped**. The corpse's `get_display_name` routes through the observer's recognition memory keyed on the corpse's apparent UID (derived from `sleeve_uid` plus whatever the corpse is still wearing).
- Worn-item changes on the corpse re-derive the apparent presentation — **shipped** via `at_object_leave` invalidation, so stripping a body changes its signature exactly like stripping a live character.
- Corpse decay interacts with recognition via the **decay-aware recognition** policy below — **shipped** (PR B).

#### Decay-Aware Recognition

`Corpse.get_display_name` runs a two-pass lookup against the observer's recognition memory, gated by the corpse's current decay stage:

| Stage | Threshold | Body axis (`sleeve_uid`) | Natural recognition | Forensic recovery |
|---|---|---|---|---|
| `fresh` | < 1 h | preserved | Works | n/a |
| `early` | < 1 d | preserved | Works | n/a |
| `moderate` | < 3 d | blanked | Fails | Intellect ≥ 3 |
| `advanced` | < 1 w | blanked | Fails | Intellect ≥ 5 |
| `skeletal` | ≥ 1 w | n/a | Blocked | Blocked |

**Pass 1 — natural recognition.** `world.identity.get_apparent_uid_for_decay(corpse, stage)` mirrors `get_apparent_uid` but blanks the `sleeve_uid` axis at `moderate` and `advanced`. Worn items and override axes are preserved, so a recognizable jacket continues to anchor the signature through light decay; a fresh memory keyed to `(sleeve_uid + jacket)` simply no longer matches once the body axis is blanked. At `fresh` and `early` the degraded UID equals the fresh UID, so ordinary recognition works.

**Pass 2 — forensic recovery.** If the degraded lookup misses but `get_apparent_uid(corpse)` (the fresh-equivalent UID) is in memory, the looker rolls Intellect (`world.combat.dice.roll_stat(looker, "intellect", default=1)`) against the stage DC. On success the assigned name is returned; on failure the decay name is returned. The roll outcome is cached permanently in `corpse.db.forensic_recognition_cache = {looker.dbref: bool}` — a single careful examination per `(observer, corpse)` pair determines the verdict, which prevents re-roll abuse on every `look`. Anonymous lookers (no dbref) are not cached and re-roll on each call.

**Skeletal hard cutoff.** The skeletal stage short-circuits both passes and returns the decay name even with a guaranteed-pass roll. Programmatic `sleeve_uid` queries (admin commands, future forensic tooling) continue to work — only the display-name path is blocked.

**Disguise persistence.** Worn-item axes contribute to the signature at all non-skeletal stages, so looting a disguise-essential item (e.g. a balaclava) silently breaks both recognition paths just as it does for a living character.

#### Identity-Bearer Mixin

The two-pass recognition algorithm above is factored into
`typeclasses.identity_bearer.IdentityBearerMixin` so multiple
typeclasses can share the same recognition surface without
duplicating the implementation.  `Corpse` inherits the mixin
unchanged; the upcoming `SeveredHead` super-item (severed-head v2)
will inherit the same mixin so heads recognise on-sight identically
to corpses.

**Contract** (duck-typed; subclass must supply):

| Member | Contract |
|---|---|
| `self.db.signature_at_death` | 5-tuple identity signature at bodily-separation moment. `None` on legacy objects. |
| `self.db.apparent_uid_at_death` | Hashed apparent UID matching the signature. |
| `get_decay_stage() -> str` | One of `fresh` / `early` / `moderate` / `advanced` / `skeletal`. |
| `_decay_display_name() -> str` | Fallback name when no recognition match (`"fresh corpse"`, `"fresh head"`, …). |

Subclasses may override `_FORENSIC_RECOGNITION_DC` to tune per-stage
DCs.  The default `{"moderate": 3, "advanced": 5}` matches the
original `Corpse` behaviour; `fresh` and `early` are deliberately
absent so forensic-recovery rolls never fire at those stages
(natural recognition covers them via the unchanged degraded UID).

### Evidence and Investigation ✅ (Engine shipped — PR-E)

The Forensic Recognition Engine (`world/forensics.py`) is the canonical
access layer for all forensic evidence surfaces (corpses, blood pools,
photos). It exposes:

- `ForensicSubject` — source-agnostic envelope.
- `attempt_forensic_recognition()` — Intellect roll vs DC with
  permanent per-`(observer, evidence)` cache, mirroring
  `attempt_disguise_pierce` semantics.
- `render_forensic_report()` — single-tier five-section renderer
  (identity axes + fuzzy time-of-death + cause of death + wounds +
  organ inventory + worn essentials) over the preserved signature
  and death-time medical snapshot.  **Never** assigns a name;
  surfacing a name remains the exclusive responsibility of
  recognition-memory lookup.  (The legacy depth ladder
  `summary`/`detailed`/`comparison` was dropped in PR #186.)
- `link_subjects()` — diagnostic primitive comparing two subjects
  axis-by-axis (reserved for future linking gameplay; no command
  exposes it).

**Shipped consumer**: `commands/forensics.py:CmdAutopsy` (single-tier)
routes corpses through the engine.

**Data prep only**: blood pools have the `signature` / `apparent_uid`
fields wired in `BloodPool.add_bleeding_incident` and the medical
script, but no player-facing command consumes them yet.

**Out of scope (deferred)**: photo capture/display (extractor stub
raises `NotImplementedError`), multi-UID linking gameplay,
sleeve-swap awareness (blocked on resleeving system).

See the dedicated §"Forensic Recognition Engine" later in this
document for the full surface, contracts, and DC tuning notes.

---

## Forensic Recognition Engine

**Module**: `world/forensics.py` (PR-E, Issue #184).

The Forensic Recognition Engine is the canonical access layer for
identity recovery from *static evidence* — corpses today, blood
pools and photos in follow-ups.  It complements
`world.identity.attempt_disguise_pierce` (which handles *live*
targets whose disguise an observer might see through) by keeping
the recognition contract — *live UID is the only key that returns
an assigned name* — invariant across evidence types.

### Surface

**Subject envelope**:

- `ForensicSubject(signature, apparent_uid_at_death,
  essential_item_type_ids, source_kind, source_ref)` — frozen
  dataclass; consumers extract one per evidence object.

**Extractors** (one per evidence surface):

- `extract_subject_from_corpse(corpse)` — reads
  `db.signature_at_death` + `db.apparent_uid_at_death`.
- `extract_subject_from_blood_pool_incident(pool, incident)` —
  reads `incident.get("signature")` / `incident.get("apparent_uid")`
  so legacy incidents land as `signature=None` automatically.
- `extract_subject_from_photo(photo)` — stub
  (`NotImplementedError`); wire when photo typeclass lands.

**Recognition (Surface A)**:

- `attempt_forensic_recognition(looker, subject, dc, *,
  cache_owner, cache_attr="forensic_recognition_cache")` —
  returns `RecognitionResult(success, revealed_uid, from_cache)`.
- Rolls `world.combat.dice.roll_stat(looker, "intellect", default=1)`
  vs `dc`.  Cache key is `(looker.dbref, revealed_uid)` so a
  signature change (looted disguise essential) naturally spawns a
  fresh cache slot on the next examine.
- Anonymous lookers (no dbref) re-roll every call; subjects
  without a recoverable UID short-circuit to
  `RecognitionResult(False, None, False)` without rolling.

**Report rendering (Surface B)**:

- `render_forensic_report(subject, *, observer)` — single-tier
  five-section report (PR #186):
  1. Identity axes (height / build / keyword).
  2. Apparent time of death — fuzzy bucket from
     `AUTOPSY_TIME_BUCKETS` (aligned with `CORPSE_DECAY_*`).
  3. Apparent cause of death — `corpse.db.death_cause`.
  4. Wounds — enumerated by body location from
     `corpse.db.wounds_at_death`.
  5. Organ inventory — from `corpse.get_medical_snapshot()`;
     harvested / severed organs render as `absent` per the
     no-surgeon-attribution rule (PR-186 Q3).  Pre-PR-#186
     corpses with no snapshot emit a single "no internal
     examination possible" marker.
  6. Worn essentials — disguise-essential item type IDs folded
     into the unified report (formerly `/deep`-only).
- Pre-PR-#183 subjects (`signature is None`) collapse to a single
  "no further forensic detail" line so identity axes never leak as
  blank fields.
- **Critically never assigns a name.**  Name surfacing remains
  the exclusive responsibility of the recognition-memory lookup
  performed by the consumer command.

**Linking primitive**:

- `link_subjects(a, b)` returns `LinkResult(shared_sleeve_uid,
  shared_apparent_uid, shared_axes)` — diagnostic only, no
  command exposes it yet.

### Consumer: `autopsy` command

`commands/forensics.py:CmdAutopsy` (keyed `autopsy`, no switches,
help category `Forensics`):

- `autopsy <corpse>` — Intellect vs `AUTOPSY_DC_BASIC` → unified
  five-section report (identity axes, fuzzy ToD, cause, wounds,
  organ inventory, worn essentials).
- Skeletal corpses short-circuit with a "too far decomposed" message
  before rolling.
- Pre-roll room broadcast via `msg_room_identity` so observers
  see the investigation regardless of outcome.
- Concatenates the recognized-name header only when the looker
  already holds the revealed UID in `recognition_memory` with an
  `assigned_name` set.

### DC tuning (provisional)

Constants live in `world/combat/constants.py`:

```python
AUTOPSY_DC_BASIC = 3
# AUTOPSY_DC_DEEP_OFFSET removed in PR #186 alongside the /deep tier.
AUTOPSY_TIME_BUCKETS = (
    (CORPSE_DECAY_FRESH,    "recently deceased"),
    (CORPSE_DECAY_EARLY,    "dead for hours"),
    (CORPSE_DECAY_MODERATE, "dead for a day or more"),
    (CORPSE_DECAY_ADVANCED, "dead for several days"),
    (float("inf"),          "long dead"),
)
```

Flagged for balance tuning per the disguise-pierce precedent.
`AUTOPSY_DC_BASIC` is intentionally low for the shipping
basic-Intellect target; raise alongside any future Investigation
skill stat gating.

### Cache strategy

Per `(observer, evidence)` cache stored on the evidence object
(`cache_owner.db.<cache_attr>` — defaults to
`"forensic_recognition_cache"` for backward compatibility with
the pre-PR-E corpse path).  Permanent across server restarts.
A second examination by the same character silently re-renders
the cached outcome rather than rolling again — rewards single
careful examination and prevents Intellect re-roll abuse.

### Recognition contract guarantees

1. The engine never assigns a name on its own.
2. Consumers may concatenate an `assigned_name` from the looker's
   recognition memory **only after** confirming the revealed UID
   is present in that memory.
3. Subjects without a UID (pre-PR-#183 corpses, legacy blood
   incidents) gracefully render "no further forensic detail"
   instead of leaking a `sleeve_uid` or other internal hash.

### Out of scope (deferred)

- Photo capture/display gameplay.
- Blood-pool forensic consumer command (data field is wired so
  future consumers have something to read).
- Multi-UID linking gameplay (`link_subjects` is a primitive).
- Memory decay & active impersonation detection (spec L1668
  Phase 5).
- Sleeve-swap awareness (blocked on resleeving system).
- Skeletal-bone harvest (cracked-bone marrow extraction) — deferred
  past PR-186; skeletal corpses currently refuse autopsy and harvest.
- ~~Severed-head super-item carrying full identity signature~~ —
  ✅ shipped in PR #194 (`SeveredHead`); see "Severed-Head
  Super-Item" subsection below.

---

## Surgical Harvest (PR #188)

`harvest <organ> from <corpse>` extracts a named organ from a
corpse, spawning a :class:`typeclasses.items.Organ` item into the
harvester's inventory.  Builds on the PR-186 death-time medical
snapshot — the snapshot is the single source of truth for organ
state, and the harvest command mutates it in place so subsequent
autopsies render the removed organ as `absent`.

### Command contract

- **Roll**: Motorics vs `HARVEST_DC_BASIC`.  Natural
  `HARVEST_CRIT_FAIL` (= 1) destroys the organ — zeroes
  `current_hp` in the snapshot, no item produced.
- **Ambiguous form** (`harvest <corpse>`) lists currently
  harvestable organ names instead of erroring opaquely.
- **Pre-roll refusals** (no Motorics roll spent):
  - Skeletal corpse — no soft tissue remains.
  - Pre-PR-#186 corpse — `get_medical_snapshot() is None`.
  - Organ not present in the snapshot.
  - Organ flagged `cannot_be_destroyed` (spine).
  - Organ not flagged `can_be_harvested` (lungs, brain, eyes, etc.).
  - Organ already in `corpse.db.removed_organs`.
  - Organ's container in `corpse.db.severed_locations` (PR #189
    sever-limb takes contained organs with it).
  - Organ `current_hp <= 0` ("already destroyed").
- **Pre-roll broadcast**: room sees the extraction attempt via
  `msg_room_identity` regardless of outcome.
- **On success**: append to `removed_organs`, re-save snapshot,
  spawn `Organ` item with `configure_from_harvest`.
- **Organ freshness** tracks the source corpse's decay stage via
  `ORGAN_CONDITION_BY_DECAY`: fresh / early → `pristine`;
  moderate → `damaged`; advanced → `putrid`.  Skeletal is gated
  out at the decay check.

### Organ typeclass

`typeclasses.items.Organ` extends `Item` and carries:

| Attribute | Source |
|---|---|
| `db.organ_name` | Canonical key from `ORGANS` |
| `db.condition` | `ORGAN_CONDITION_BY_DECAY[stage]` at extraction |
| `db.source_signature` | Copy of `corpse.db.signature_at_death` |
| `db.source_apparent_uid` | Copy of `corpse.db.apparent_uid_at_death` |
| `db.source_corpse_dbref` | Audit pointer; not resolution-guaranteed |
| `db.source_species` | Inherited from `corpse.db.species` (PR-G) |

The display key is rendered via `get_species_organ_name(species,
organ_name, decay_stage)` at spawn time by `configure_from_harvest`
(issue #212).  Fresh / early decay produces `"{species} {organ}"`
(e.g. `human heart`); moderate / advanced drops to `"rotting
{organ}"`; the skeletal tier reads `"desiccated {organ}"` —
mirroring the appendage decay-tier contract from
`get_species_part_name` but substituting `desiccated` for `skeletal`
because soft tissue dries out rather than skeletonizing.  The
freshness `condition` (`pristine` / `damaged` / `putrid`) is
conveyed via `db.desc` and surfaces at `look` time, not in the key.

**Unknown-species fallback (issue #215):** unregistered species drop
the species token entirely at fresh / early stages — an organ from
an alien species renders as bare `"heart"`, not `"human heart"`.
This is a deliberate feature: builders who create something truly
alien get inscrutable organ names for free, and the system never
misclaims provenance.  Late-decay tiers already drop species via
their templates, so this fallback only affects fresh / early surface
output.

### DC tuning (provisional)

```python
HARVEST_DC_BASIC = 3
HARVEST_CRIT_FAIL = 1
ORGAN_CONDITION_BY_DECAY = {
    "fresh": "pristine", "early": "pristine",
    "moderate": "damaged", "advanced": "putrid",
    "skeletal": "refuse",
}
```

Flagged for balance review once the black-market organ-trade
gameplay loop lands.  `HARVEST_DC_BASIC` matches `AUTOPSY_DC_BASIC`
intentionally — both are "basic forensic competency" gates.

### Out of scope (deferred to later PRs)

- Sever-limb command (PR #189) — will populate
  `corpse.db.severed_locations` which the harvest gate already
  honours.
- Black-market organ economy / NPC fences.
- Organ implantation / replacement surgery.
- Snapshot persistence across corpse deletion (lost when the
  corpse decays out — `source_corpse_dbref` becomes stale but the
  forensic-chain copy of the signature on the organ item
  survives).

---

## Surgical Sever (PR #190)

`sever <location> from <corpse>` detaches a limb (or the head) from
a corpse, spawning a :class:`typeclasses.items.Appendage` item into
the severer's inventory.  Sibling to PR-188 harvest; shares the
forensic-chain provenance pattern and the death-time medical
snapshot as the single source of truth for what anatomy the corpse
had.

### Command contract

- **Roll**: Motorics vs `SEVER_DC_BASIC`.  Natural `SEVER_CRIT_FAIL`
  (= 1) mangles the cut but leaves state intact — no item, no
  bookkeeping mutation.  Crit-fail is **non-destructive** (unlike
  harvest, which destroys the organ); limbs are coarser anatomy
  and the realistic failure-mode is hacking a mess, not destroying
  the limb beyond recovery.
- **Ambiguous form** (`sever <corpse>`) lists severable locations.
- **Pre-roll refusals** (no Motorics roll spent):
  - Skeletal corpse / pre-PR-#186 corpse.
  - Location not in
    :data:`world.combat.constants.SEVERABLE_CONTAINERS`.
  - Snapshot contains no organs in that container (the corpse
    never had that limb).
  - Location already in `corpse.db.severed_locations`.
- **Pre-roll broadcast** via `msg_room_identity`.
- **On success**: append location to `severed_locations`, spawn
  `Appendage` item with `configure_from_sever`.

### Severable partition

The canonical limb partition from
:meth:`world.medical.core.Organ._is_limb_container` plus `head`:

```python
SEVERABLE_CONTAINERS = frozenset({
    "head",
    "left_arm", "right_arm",
    "left_hand", "right_hand",
    "left_thigh", "right_thigh",
    "left_shin", "right_shin",
    "left_foot", "right_foot",
})
```

`head` is internal anatomy in the medical model but is severable as
a discrete item per the PR-190 contract.  Severed heads are
super-items (`typeclasses.items.SeveredHead`, PR-B/#194) that carry
the full identity signature and can be recognized / autopsied
independently of the source corpse — see "Sever-Head Identity
Surface" below.

### Sever-Head Identity Surface (issue #208)

When `apply_severed_head_overlay` runs (head-sever success path), the
identity surface is **duplicated**, not transferred:

1. **Head carries face-side identity** — the overlay copies
   `corpse.db.sleeve_uid → head.db.sleeve_uid`, in addition to the
   forensic-chain fields (`source_signature`,
   `source_apparent_uid`, `source_corpse_dbref`) already inherited
   from `Appendage`. `SeveredHead.sleeve_uid` is a property
   descriptor reading `db.sleeve_uid`, satisfying
   `world.identity.get_identity_signature`'s 5-tuple
   `(sleeve_uid, height_override, build_override, keyword_override,
   essential_item_type_ids)`. The head's `get_worn_items()` returns
   `[]`, so the essentials axis collapses naturally and the head
   reduces to the face-side signature.
2. **Corpse retains its snapshot** — `signature_at_death`,
   `apparent_uid_at_death`, `sleeve_uid`, `medical_state_at_death`
   are untouched. Autopsy/harvest/forensic-recovery paths still
   resolve the source identity.
3. **Corpse look-time recognition is gated** — the overlay sets
   `corpse.db.head_severed = True`. `Corpse.get_display_name`
   short-circuits to the decay-tier name (e.g. `"a rotting corpse"`)
   when this flag is true, suppressing unaided recognition while
   leaving the forensic surface intact. Autopsy bypasses
   live-derivation entirely (it reads `medical_state_at_death`), so
   forensic identification continues to work on headless corpses.

This split means: a witness who knew the deceased recognizes the
**head** by sight, while the **headless corpse** appears as a
generic decaying body until autopsied — matching real-world
forensic intuition.

Recognition-tier DCs for severed heads mirror live-character tiers
(moderate DC 3, advanced DC 5, skeletal hard-cutoff with no roll
path); decay-name mapping is fresh/early → `"human head"`,
moderate/advanced → `"rotting head"`, skeletal → `"skeletal head"`.

### Appendage typeclass

`typeclasses.items.Appendage` extends `Item`; carries the same
forensic-chain fields as `Organ` (`source_signature`,
`source_apparent_uid`, `source_corpse_dbref`) plus:

| Attribute | Source |
|---|---|
| `db.location_name` | Canonical container key (e.g. `left_arm`) |
| `db.condition` | `ORGAN_CONDITION_BY_DECAY[stage]` at severance |
| `db.source_species` | Inherited from `corpse.db.species` |

The display key is rendered via
`get_species_part_name(species, location, decay_stage)` at spawn
time by `configure_from_sever` (PR #202 / PR-G).  Fresh / early
decay produces `"{species} {location}"` (e.g. `human left arm`);
moderate / advanced drops to `"rotting {location}"`; the skeletal
tier reads `"skeletal {location}"` — limbs *can* skeletonize, so
the appendage contract keeps the `skeletal` prefix (in contrast to
the organ contract, which substitutes `desiccated` because soft
tissue dries rather than skeletonizes — see issue #212).  The
freshness `condition` (`pristine` / `damaged` / `putrid`) is
conveyed via `db.desc` (PR #204) and surfaces at `look` time, not
in the key.

### Harvest interaction

`CmdHarvest` already filters its harvestable-organs list with
`organ_data["container"] not in corpse.db.severed_locations`.  With
PR #190 shipped, severing an arm correctly causes subsequent
harvest attempts on contained organs (e.g. `left_humerus`) to
refuse with "went with the severed left_arm".  V1 does **not**
spawn separate organ items for the anatomy bundled inside the
limb — a future butchery pass may unbundle.

### DC tuning (provisional)

```python
SEVER_DC_BASIC = 3
SEVER_CRIT_FAIL = 1
```

Matches `HARVEST_DC_BASIC` / `AUTOPSY_DC_BASIC` — all three are
basic forensic / surgical competency gates.  Flagged for balance
review alongside the harvest economy work.

### Out of scope (deferred past PR #190)

- Limb-attached worn-item retention (severing an arm with a watch
  on does **not** transfer the watch to the appendage in v1).
- Reattachment / cybernetic limb prosthetics.
- Per-organ unbundling from severed limbs.

### Severed-Head Super-Item ✅ (Shipped — PR #194)

`sever head from <corpse>` produces a `typeclasses.items.SeveredHead`
rather than the generic `Appendage` used for limbs.  `SeveredHead`
inherits `IdentityBearerMixin` (alongside its `Appendage` base) so
the head is a first-class forensic peer of the source corpse:

- **Identity carry-forward**: `db.signature_at_death` and
  `db.apparent_uid_at_death` are copied verbatim from the corpse, so
  the two-pass recognition algorithm (live UID → snapshot UID via
  forensic-recovery roll) works against a disembodied head with the
  same semantics it does against a corpse.
- **Shared decay clock**: `db.creation_time`, `db.death_time`,
  `db.death_cause` are copied so the head ages on the same timeline
  as the corpse it came from.  `get_decay_stage()` maps the elapsed
  time onto `fresh` / `early` / `moderate` / `advanced` / `skeletal`
  using the standard `CORPSE_DECAY_*` thresholds.
- **Trimmed medical snapshot**: `db.medical_state_at_death` retains
  only the organs whose `container == "head"` (brain, eyes, ears,
  etc.); body-wide fields (`conditions`, `blood_level`, `pain_level`,
  `consciousness`) are blanked because reporting them off a
  disembodied head would lie.  Head-container entries from the
  corpse's `removed_organs` list are carried over so pre-sever
  harvests stay visible.
- **Worn-items contract**: `get_worn_items()` returns `[]` — heads
  carry no clothing in v1 (renderer compatibility shim).
- **Severing a SeveredHead is refused**: heads are terminal; the
  `CmdSever` isinstance gate remains `Corpse`-only.

**Accepted targets ✅ (PR #196)**: `CmdAutopsy` and `CmdHarvest`
accept either a `Corpse` or a `SeveredHead` — the isinstance gate
is `(Corpse, SeveredHead)`.  Autopsy on a head renders the standard
five-section report against the trimmed head-container snapshot
(brain / eyes / ears / etc.); harvest extracts head-container organs
honoring the carry-forward `removed_organs` list.  `CmdSever`
remains `Corpse`-only.

**Deferred** (post PR-C): the snapshot represents the
*body's* identity at sever time, not consciousness; sleeve-swap
awareness on the head awaits the resleeving system.

### Wound + Longdesc Carry-Forward (PR-D ✅ — PR #198)

When `CmdSever` succeeds, the severed appendage (or head) inherits
the corpse's per-location wounds and free-form longdesc prose, and
the corpse's matching prose is cleared and replaced with a
synthesized stump wound — keeping a single source of truth for "what
happened to that body part" and letting both autopsy and the severed
item render the same narrative.

**Move semantics** (not copy): pre-existing wounds at the severed
location(s) are removed from the corpse and reassigned to the
severed item. The corpse keeps only the synthesized stump wound at
the sever location. This prevents double-reporting in autopsy.

**Head cluster**: severing the head moves wounds and longdesc for
the entire head cluster — `{head, face, neck, left_eye, right_eye,
left_ear, right_ear}` (see `SEVERED_HEAD_LOCATIONS` in
`world/combat/constants.py`). Limbs use a single-location move.

**Stump wound contract**: synthesized as
`{injury_type: "severed", location: <sever_loc>, severity: "Critical",
stage: "old", organ: None, organ_damage: {current_hp: 0, max_hp: 0,
container: <sever_loc>}}` and appended to `corpse.db.wounds_at_death`.
Rendering flows through the standard
`world.medical.wounds.get_wound_description()` pipeline using new
templates in `world/medical/wounds/messages/severed.py` (fresh / old /
treated / healing / scarred / destroyed stages all defined, with `old`
being the canonical autopsy form).

**Severed-item rendering**: `Appendage.return_appearance` (and the
`SeveredHead` override) renders the base condition prose, then any
carried longdesc verbatim per location (no decay modulation — once
written into death prose, it ages with the host item's overall decay
clock, not its own), then any inherited wounds via
`get_wound_description`. This keeps a severed hand with a tattoo
description on it readable as "a severed left hand — tattoo prose —
old slash wound" regardless of where the hand ends up.

**Helpers** (`typeclasses/items.py`):
- `apply_wound_and_longdesc_overlay(item, corpse, locations)` —
  moves the listed locations' wounds and longdesc from corpse → item.
- `apply_sever_to_corpse(corpse, location)` — wraps the overlay for
  the limb / head-cluster case and stamps the stump wound onto the
  corpse.

**Failure modes**: on a failed sever roll, neither helper is called;
the corpse retains its wounds and longdesc unchanged.

**Deferred**: per-organ wound carry-forward when only an organ
(rather than a whole limb) is harvested; decay-tier modulation of
inherited longdesc prose on the severed item itself.

### Harvested-Organ Wounds (PR-F ✅ — PR #200)

When `CmdHarvest` succeeds, the corpse gains a synthesized
`harvested`-type wound at the organ's **container** location.
Targeting the container (not the organ name) lets the existing
PR-D wound + longdesc carry-forward overlay
(`apply_wound_and_longdesc_overlay`) move the wound onto a severed
limb / head automatically when that container is later severed —
no harvest-specific code is needed in the overlay layer.

**Synthesized wound contract**:
`{injury_type: "harvested", location: <container>, severity: "Critical",
stage: "old", organ: <organ_name>, organ_damage: {current_hp: 0,
max_hp: 0, container: <container>}}`. Appended to
`corpse.db.wounds_at_death` after `removed_organs.append`. Templates
in `world/medical/wounds/messages/harvested.py` (fresh / old / treated
/ healing / scarred / destroyed stages) render via the standard
`get_wound_description` pipeline using `{location}` and `{organ}`
tokens.

**Carry-forward behavior**:
- **Severable container** (head, hands, arms, thighs, shins, feet) —
  harvested wound rides with the severed item when that location is
  later severed. A harvested-eye wound at `head` flows through the
  head-cluster fan-out; a harvested-metacarpal wound at `right_hand`
  moves to the severed right hand.
- **Unseverable container** (chest, abdomen, back) — wound stays on
  the corpse permanently. A harvested-heart wound at `chest` cannot
  travel because no sever operation targets the chest; the autopsy
  forever records the excision.

**Crit-fail behavior**: silent — no wound synthesized. The
`destroyed` organ-status in the autopsy snapshot already conveys
the destruction, and crit-fail is operator error not external
trauma. Successful harvest leaves a clean surgical trace; crit-fail
leaves an internal mess that doesn't manifest as an external wound.

**Rendering helper change**: `world/medical/wounds/wound_descriptions.py`
adds an `organ_display` key to `format_vars` (humanizes `left_eye`
→ `left eye`) so templates using `{organ}` render readable prose.
Cheap str-level transform — no `ORGANS` registry lookup, to keep the
renderer independent of registry growth in subsequent PRs.

**Deferred** (PR-G): species-aware naming for corpses, severed items,
and organs; decay-modulated keys; recognition reveal as parenthetical;
static default descriptions per organ × condition tier.

### Species Anatomy Overlay (PR-G ✅ — PR #202)

PR-G introduces a thin **species registry** at `world/anatomy/species.py`
that owns the player-facing vocabulary for body locations, severed
parts, and whole-corpse names — keyed by species and decay stage.  The
registry is consulted by every species-aware rendering path
(`Corpse`, `Appendage`, `SeveredHead`, `Organ`, wound-display
`get_location_display_name`) so naming conventions stay consistent and
new species can be added by registering a single dict.

**Registry shape** (`SPECIES_DEFINITIONS[species]`):

| Key                    | Purpose                                              |
|------------------------|------------------------------------------------------|
| `display_name`         | Glance-level species tag (e.g. `"human"`).           |
| `location_display`     | Canonical body-location → readable string mapping.   |
| `decay_part_prefixes`  | Decay-stage → severed-part template (`{species} {part}`). |
| `decay_corpse_names`   | Decay-stage → whole-corpse name string.              |

**Three pure-function helpers** (state-free, callable per
`get_display_name` invocation):

```python
get_species_location_display(species, location) -> str
get_species_part_name(species, location, decay_stage) -> str
get_species_corpse_name(species, decay_stage) -> str
```

Unknown species fall back to the `"human"` definition; unknown
locations fall back to underscore-stripped passthrough; unknown decay
stages fall back to the `"fresh"` template.

**Provenance propagation**:

* `Character.at_object_creation` sets `db.species = "human"` (default).
* `_create_corpse_from_character` copies `character.db.species` →
  `corpse.db.species` and seeds the corpse's initial key with
  `get_species_corpse_name(species, "fresh")`.
* `Appendage.configure_from_sever` and `Organ.configure_from_harvest`
  copy `corpse.db.species` → `db.source_species`.
* `SeveredHead` inherits the propagation via its super-call.

### Display-Name Conventions (PR-G ✅)

**Decay-tier vocabulary** — universal across corpses and severed parts:

| Stage     | Part display           | Corpse display       |
|-----------|------------------------|----------------------|
| fresh     | `human <part>`         | `human corpse`       |
| early     | `human <part>`         | `human corpse`       |
| moderate  | `rotting <part>`       | `rotting corpse`     |
| advanced  | `rotting <part>`       | `rotting corpse`     |
| skeletal  | `skeletal <part>`      | `skeletal remains`   |

Fresh / early stages cleanly identify species; moderate / advanced
obscure species (just "rotting"); skeletal abandons species entirely
and the corpse switches from "corpse" to "remains" — a deliberate
vocabulary shift that signals decay irreversibility.

**Recognition-parenthetical format** — `IdentityBearerMixin.get_display_name`:

When an observer's recognition memory matches the bearer's UID (either
natural recognition on the degraded UID or forensic recovery on the
fresh UID), the returned display name is:

```
<decay name> (<assigned name>)
```

Examples: `"human corpse (Jorge)"`, `"rotting corpse (Jorge)"`,
`"rotting head (Mira)"`.  The decay name still leads so the
recognising observer retains glance-level awareness of decay state;
the parenthetical surfaces the remembered identity.  Living
characters are unaffected — they don't pass through
`IdentityBearerMixin`.  Skeletal stage retains its hard cutoff (no
recognition reveal under any circumstance).

### Organ Default Descriptions (PR-G ✅ — corrected in PR #204)

`world/medical/constants.py` ships an `ORGAN_DISPLAY` table sibling
to `ORGANS`, carrying display names and condition-keyed prose for
every harvestable organ (26 entries × 3 conditions: pristine /
damaged / putrid).  The prose is short, clinical, and physically
anchored — enough to ground the player in the organ's current state
without staff ever setting a custom `db.desc`.

`Organ.configure_from_harvest` populates `self.db.desc` from the
condition-keyed prose at harvest time, the Evennia-standard way.  The
engine's default `return_appearance` renderer then slots the prose
into the look output naturally — no custom override required.  A
freshly harvested heart reads:

```
It is a pristine specimen. A dense, dark-red heart, its muscle firm
and the great vessels stumped cleanly above.
```

Issue #221 added the leading condition sentence (`"It is a {pristine
| damaged | putrid | desiccated} specimen."`) that surfaces the
freshness state stripped from the item key in issue #212.  Issue
#223 simplified the original colour-coded standalone tagline
(`|gPristine.|n` + blank line) to the current plain-sentence form,
and issue #225 then switched the sentence-to-prose join from a
newline to a single space so the whole description renders as one
continuous paragraph rather than breaking across two visible lines.
The `format_condition_tagline` / `prepend_condition_to_desc` helpers
live in `world/anatomy/conditions.py` and are shared between
`configure_from_harvest` (organs) and `configure_from_sever`
(appendages, including severed heads) so both surfaces render
identically.  The `refuse` condition (gameplay-internal skeletal-
stage harvest gate) renders empty so the term never leaks to players.

> **Historical note (PR-G → PR #204):** the original PR-G shipped
> with an `Organ.return_appearance` override that prepended prose to
> the engine output. That bypassed Evennia's normal renderer and
> produced a "You see nothing special" line alongside the floating
> prose. PR #204 deleted the override and moved the prose into
> `db.desc` at harvest time, matching the convention used by every
> other Item subclass in `typeclasses/items.py`.

Two lookup helpers (`get_organ_display_name`,
`get_organ_default_description`) provide defensive fallbacks: unknown
organs return the underscore-stripped key; unknown conditions
(`refuse` — skeletal-stage harvest, refused at the command gate)
return empty so `configure_from_harvest` leaves `db.desc` untouched
(engine default applies) rather than overwriting with an empty
string.

### Severed Part Default Descriptions (PR #204 ✅)

Parallel to the organ table, `world/anatomy/severed_parts.py` ships
`SEVERED_PART_DESCRIPTIONS` — a species-keyed prose table for every
entry in `world.combat.constants.SEVERABLE_CONTAINERS` (11 locations
for humans: `head`, both arms / hands / thighs / shins / feet × 3
conditions = 33 prose strings).  Same vocabulary register as the
organ table — short, clinical, physically anchored.

`Appendage.configure_from_sever` populates `self.db.desc` from the
condition-keyed prose at sever-time.  `SeveredHead` inherits this
behaviour via its `super().configure_from_sever(...)` call, so a
severed head also reads with a populated default desc.

`Appendage.return_appearance` is retained: it composes wound +
longdesc carry-forward (PR-D / PR-F) dynamically on top of the
engine-rendered base.  Since `super().return_appearance(...)` now
includes the seeded `db.desc` in its output, both surfaces coexist
cleanly — the default prose anchors the look, and the dynamic prose
(wounds, transferred longdesc) follows.

A single helper (`get_severed_part_description`) provides the same
defensive fallback contract as the organ helper: unknown species fall
back to human; unknown locations / conditions return empty so the
configure step leaves `db.desc` untouched.

---

## New Character Attributes

### On Character (sleeve-level)

| Attribute | Type | Default | Set By | Persists Across Clones |
|---|---|---|---|---|
| `db.sleeve_uid` | UUID (str) | Generated at creation | System | Yes (flash clones inherit) |
| `db.height` | str | Selected at chargen | Chargen | Yes |
| `db.build` | str | Selected at chargen | Chargen | Yes |
| `db.hair_color` | str or None | Selected at chargen | Chargen / `@hair` | Yes |
| `db.hair_style` | str or None | Selected at chargen | Chargen / `@hair` | Yes |
| `db.sdesc_keyword` | str | Selected at chargen | `@shortdesc` | Yes |

`sdesc_physical` is not stored — it is computed on access from `height` and `build` via the descriptor table.

The distinguishing feature is not stored — it is computed on access from worn items and hair attributes.

### On Character (recognition memory)

| Attribute | Type | Default |
|---|---|---|
| `recognition_memory` (`AttributeProperty`) | dict | `{}` |

> Originally specified to live on the brain organ; storage was kept on the Character for the engine PR rollout. See §Memory Architecture for the migration plan.

### On Items (for sdesc feature derivation)

| Attribute | Type | Purpose |
|---|---|---|
| `db.sdesc_short` | str or None | Brief recognizable description for sdesc feature clause (e.g., "leather jacket", "red power armor") |

---

## Impact on Existing Systems

The table below tracks the original Phase 2 audit surface. All rows have been resolved by the Phase 2 sweep (PRs #156, #158, #160, #162, #166) and are kept here with ✅ markers for historical reference.

| System | File(s) | Status | Notes |
|---|---|---|---|
| Combat message templates | `world/combat/messages/__init__.py` | ✅ | Module exposes `observer_template` + `char_refs` for `msg_room_identity`; legacy `observer_msg` retained for back-compat |
| Shield messages | `world/combat/attack.py:232-268` | ✅ | First-person msgs use `get_display_name_safe(target, observer)`; observer broadcast at line 263 uses `msg_room_identity` with three char_refs |
| Normal movement (Evennia defaults) | `typeclasses/characters.py` (`Character.announce_move_from/to`) | ✅ | Per-observer override routes broadcasts through `msg_room_identity`; honors caller `msg=`/`mapping=` by delegating to `super()`. Phase 2 Φ₅, PR #166 |
| Communication (say/whisper/emote) | `commands/CmdCommunication.py` | ✅ | Custom `CmdSay` / `CmdWhisper` / `CmdEmote` overrides ship per-observer rendering |
| Death curtain filter | `typeclasses/characters.py:155-222` | n/a | Uses verb-substring matching (`' says, "'`, `' tells you'`, etc.) in `_is_social_message`, not `.key`. Intentional design; out of per-observer-rendering scope |
| CmdAttack target resolution | `commands/combat/core_actions.py:118` | ✅ | Uses `resolve_character_target(...)` — recognition-aware |
| Exit drag messages | `typeclasses/exits.py:327` | ✅ | Uses `msg_room_identity` with `{grappler}` / `{victim}` char_refs |
| Room character listing | `typeclasses/rooms.py:410` | ✅ | Uses `get_display_name(looker)` |
| Combat movement messages | `commands/combat/movement.py` | ✅ | First-person msgs use `get_display_name(observer)`; room broadcasts converted to `msg_room_identity` in Phase 2 Φ₃ (PR #160) |
| Look command / appearance | `typeclasses/appearance_mixin.py` | ✅ | Uses `get_display_name(looker)` |

### Systems Already Correct

Several systems route through `get_display_name(looker)` or `msg_room_identity` and render per-observer correctly:

- Room character listings (`typeclasses/rooms.py:410`)
- Combat movement (`commands/combat/movement.py`) — first-person via `get_display_name(observer)`, room broadcasts via `msg_room_identity` (Phase 2 Φ₃, PR #160)
- Look / appearance rendering (`typeclasses/appearance_mixin.py:363, 397-419`)
- Exit character previews (`typeclasses/exits.py:673`)
- Exit drag broadcasts (`typeclasses/exits.py:327`, via `msg_room_identity`)
- Communication commands (`commands/CmdCommunication.py`: `CmdSay`, `CmdWhisper`, `CmdEmote`)
- Combat message templates (`world/combat/messages/__init__.py`, via `observer_template` + `char_refs`)
- Shield messages (`world/combat/attack.py:232-268`, via per-observer first-person + `msg_room_identity` observer broadcast)
- Consumption commands (`commands/CmdConsumption.py`) — Phase 2 Φ₁, PR #156
- Armor commands (`commands/CmdArmor.py`) — Phase 2 Φ₂, PR #158
- Spawnmob manifest, shop purchase, human-shield grenade — Phase 2 Φ₄, PR #162
- Normal exit traversal announcements (`Character.announce_move_from/to` in `typeclasses/characters.py`) — Phase 2 Φ₅, PR #166
- Medical commands (`commands/CmdMedical.py`)
- Clothing commands (`commands/CmdClothing.py`)
- Most inventory/interaction commands

---

## Character Creation Updates

Character creation (both in-game `create` and web-based) includes a
short identity-attribute selection block between sex selection and
G.R.I.M. distribution:

### Chargen Identity Steps

1. **Height selection** — short, below-average, average, above-average, tall
2. **Build selection** — slight, lean, athletic, average, stocky, heavyset
3. **Hair color selection** — from approved list, or bald/none
4. **Hair style selection** — from approved list (contextual based on color choice), or bald/none
5. **Preview** — confirmation screen showing the assembled sdesc, e.g. `"You will appear as 'a lanky man with red dreadlocks' to strangers."`

**Sdesc keyword is _not_ chosen during chargen.** New characters get a
gender-appropriate default (`DEFAULT_SDESC_KEYWORDS[gender]` —
`"man"` / `"woman"` / `"person"`) via the lazy fallback in
`Character.get_sdesc()` (`typeclasses/characters.py`). Players
customize their keyword at any time post-chargen via the
`@shortdesc` command, which presents the gender-gated approved list
and accepts custom alpha-only keywords (logged as
`KeywordEvent(event_type="custom_set")`). This keeps the chargen
flow short and defers a writing decision until the player has
context for what a keyword is.

### Sleeve UID Assignment

- New characters: generate a fresh UUID via `uuid.uuid4()`
- Flash clones: inherit `sleeve_uid` from the original character (in `create_flash_clone()` at `commands/charcreate.py:293`)

---

## Migration Strategy

Existing characters need identity attributes backfilled. Use the existing `@fixchar` command pattern:

1. Generate `sleeve_uid` for all existing characters (unique per character)
2. Set default `height` = `"average"`, `build` = `"average"` (or derive from existing descriptive data if possible)
3. Set default `hair_color` and `hair_style` = `None` (forces players to set via `@shortdesc` or `@hair`)
4. Set default `sdesc_keyword` based on existing `sex` attribute (`"man"` for male, `"woman"` for female, `"person"` for ambiguous)
5. Initialize empty `recognition_memory` (Character AttributeProperty; defaults to `{}` automatically)
6. Staff can run `@fixchar/all` to batch-process

Players should be prompted to customize their sdesc on next login if defaults were applied.

---

## Phased Implementation

**Current status (high-level):**

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation (sdesc, recognition, chargen, grammar) | ✅ Shipped |
| 2 | Per-observer rendering consistency | ✅ Shipped — helper + per-surface `msg_contents()` → `msg_room_identity` sweep complete (Φ₁ Consumption, Φ₂ Armor, Φ₃ Movement, Φ₄ Capstone all shipped) |
| 3 | Disguise foundation (signature engine, `appear`, personas, unmasking) | ✅ Shipped |
| 3.5 | Disguise item taxonomy | ✅ Shipped — catalog, taxonomy, suppression cohesion, and sdesc-fragment audit all closed (PRs #132 / #176 / #178 / #179 / #180). Biomod / pharmaceutical items and identity artifacts remain deferred to Future Hooks per scope. |
| 4 | Cybernetics (digital memory, ID exchange) | ⛔ Not started (gated on cyberware system) |
| 5 | Resonance mechanics (decay, perception, social reads) | ⛔ Not started (gated on Phase 4) |

Per-phase detail below.

### Phase 1 — Foundation

**Scope:** sdesc system, recognition storage, manual assignment, `get_display_name` override, chargen updates.

- New attributes: `sleeve_uid`, `height`, `build`, `hair_color`, `hair_style`, `sdesc_keyword`
- Physical descriptor table in constants
- Keyword list in constants
- Sdesc composition logic
- `recognition_memory` AttributeProperty on Character (migration to brain organ deferred — see §Memory Architecture)
- `Character.get_display_name(looker)` override
- `@shortdesc` command
- `remember` / `forget` / `recall` / `memory` commands
- Grammar engine (articles, possessive, objective, self-perception)
- Chargen updates
- Flash clone `sleeve_uid` inheritance
- `@fixchar` migration
- Staff identity overlay (permission-based stopgap)

### Phase 2 — Consistency

**Status: ✅ Shipped (PRs #156, #158, #160, #162, #166).** Helper plus per-surface conversion sweep complete; see Conversion Status table below.

**Scope:** Patch all `.key` usage across the codebase.

- `msg_room_identity` helper function
- Combat message templates → per-observer rendering
- Custom say/whisper/emote command overrides (see `EMOTE_POSE_SPEC.md`)
- Custom movement announcement overrides
- Fix `CmdAttack` target resolution
- Fix drag messages, death filter pattern matching
- Target resolution with sdescs, assigned names, and ordinals
- `sdesc_short` attribute on items
- Distinguishing feature auto-derivation from worn items

**Conversion Status — `msg_contents()` → `msg_room_identity()` sweep:**

The helper and most rendering surfaces shipped in earlier work; a per-surface audit identified 14 command-layer files still emitting raw `msg_contents()` broadcasts with character `.key` references. Conversion is split across four PRs:

| Φ | Scope | Files | Status |
|---|---|---|---|
| Φ₁ | Consumption verbs (inject / apply / bandage / eat / drink / inhale / smoke) | `commands/CmdConsumption.py` (14 sites) | ✅ Shipped |
| Φ₂ | Armor put-on / take-off / repair | `commands/CmdArmor.py` (~7 sites) | ✅ Shipped |
| Φ₃ | Movement flee announcements | `commands/combat/movement.py` (5 sites) | ✅ Shipped |
| Φ₄ | Capstone: spawnmob, shop, human-shield grenade | `commands/CmdSpawnMob.py` (1 site), `commands/shop.py` (1 site), `world/combat/explosives.py` (1 site) | ✅ Shipped |
| Φ₅ | Normal exit traversal announcements | `typeclasses/characters.py` (`announce_move_from/to` overrides) | ✅ Shipped |

Sites that broadcast **only** non-character text (item names, constant prose) are intentionally left as raw `msg_contents` since per-observer rendering adds no value there. `commands/combat/jump.py` was audited during Φ₃ and its 3 `msg_contents` sites (sacrifice dud, false-heroics, gravity item-fall) are all item-only and remain raw under this rule. During Φ₄, the bulk of broadcasts in `commands/CmdThrow.py` (5 sites), `commands/CmdExplosives.py` (7 sites), and `commands/explosion_utils.py` (13 sites) were similarly audited and confirmed item-only (grenade/object names, prose, direction strings) — they remain raw. The 3 character-naming sites (spawnmob manifest, shop purchase, human-shield grenade) shipped in Φ₄ closing the sweep.

### Phase 3 — Disguise (Foundation)

**Scope:** Identity signature engine, the `appear` / persona verb cluster (per-axis overrides + persona snapshots), disguise item flags, and lifecycle integration. Shipped incrementally across multiple PRs.

**Build in Phase 3:**
- Identity signature tuple: `(real_sleeve_uid, height_override, build_override, keyword_override, sorted(essential_item_type_ids))` — **shipped** (`world/identity.py:get_identity_signature`)
- Apparent UID derivation: `hashlib.blake2b(repr(signature).encode("utf-8"), digest_size=8).hexdigest()` — deterministic 16-char hex, recomputed on access (no caching) — **shipped** (`world/identity.py:get_apparent_uid`)
- Per-axis `appear` command grammar — **shipped (`appear-persona-cluster`)**:
  - `appear` (status), `appear taller | shorter`, `appear thinner | fatter | bulkier | leaner`, `appear <keyword>`, `appear <persona name>`
  - `stop appearing` (clears all overrides + active-persona pointer)
- Sdesc descriptor recomposition via existing `get_physical_descriptor(height, build)` table — **shipped** (wired into `typeclasses/characters.py:get_sdesc`)
- Pronoun derivation under disguise via `get_apparent_gender(char)` helper consulting `keyword_override` against the `ServerConfig`-backed gender lists — **shipped** (`world/identity.py:get_apparent_gender`; consumed in `world/emote.py`)
- DB attributes for active overrides on character — **shipped**: `db.height_override`, `db.build_override`, `db.keyword_override`, `db.active_persona`, `db.personas`
- `db.disguise_essential` flag on items — contributes to identity signature when worn — **shipped** (signature wiring in `world/identity.py:get_essential_item_type_ids`; concrete item prototypes ship in Phase 3.5)
- `db.is_disguise_item` flag on items — Phase 5 perception bonus hook (defined but inert in Phase 3) — **shipped (flag schema only)**
- Hook `get_sdesc()` / `get_display_name()` to consume override axes and Apparent UID — **shipped** (`typeclasses/characters.py:946,989`)
- Recognition memory re-keyed on Apparent UID — **shipped**
- Orphaned-entry handling: `lost_contact` boolean flag + render annotation in `memory` / `recall`; never auto-pruned — **shipped**. Lazy evaluation at render time: `world/identity.py:mark_lost_contact_entries` is invoked by `commands/CmdCharacter._refresh_lost_contact` from `CmdMemory.func` and `CmdRecall.func`, flipping `lost_contact = True` for entries whose Apparent UID is not currently visible and whose `last_seen` is older than `LOST_CONTACT_THRESHOLD_SECONDS` (`world/identity.py`; provisional 30 in-game days, balance-pass tuning value). The inverse — clearing back to `False` — is handled by the existing recognition writer in `_remember_target` on re-meet **and** by the passive recency bumper `world/identity.py:bump_recognition_recency` whenever a remembered observer perceives a remembered target. Render annotation `|y(lost contact)|n` appears next to the assigned name in both `memory` (table cell) and `recall` (entry header).
- Passive recognition recency on perception — **shipped**. `world/identity.py:bump_recognition_recency` refreshes `last_seen` / `location_last_seen` / `sdesc_at_last_encounter` (but not `times_seen`) for already-remembered targets, throttled by `RECOGNITION_BUMP_THROTTLE_SECONDS` (300s). Wired into `typeclasses/characters.py:Character.at_post_move` via `_refresh_recognition_recency`, which iterates the new room's `Character` contents and bumps each remembered target. Stealth/sneaking/hidden suppression is a known future-work delta.
- Look-header sdesc enrichment — **shipped**. `typeclasses/characters.py:Character.get_look_header` is consumed by `typeclasses/appearance_mixin.py:return_appearance` to render the first line of `look <character>` as `"{name} ({article} {sdesc})"` whenever the looker has a name to attach: their own real name when looking at self, or an assigned recognition name for the target's Apparent UID. Strangers fall through to the bare articled sdesc (no parenthetical) so the header stays terse. The parenthetical is omitted when `get_sdesc()` collapses to `self.key` (pre-chargen) to avoid `Name (Name)`. Other surfaces (room contents listing, combat / wielding / aiming messages) continue to use `get_display_name` unchanged.
- Full keyword catalog available regardless of character gender (override bypasses gender filter) — **shipped via `appear <keyword>` validation**
- Available to **all characters** (no access level restriction)
- Persona layer (player-private ergonomics) — **shipped (`appear-persona-cluster`)**:
  - `remember me as <name>` — capture current overrides as a persona (verb-symmetric with `remember <target> as <name>`)
  - `appear <persona name>` — adopt a persona (clean swap; overwrites all axes including unset ones)
  - `personas` — list saved personas, recency-sorted; active persona marked with `*`
  - `persona <name>` — inspect a single persona
  - `forget <persona name>` — delete a persona; clears overrides and `db.active_persona` if it was active
  - Cross-namespace uniqueness enforced (keyword catalog ∩ recognition names ∩ persona names)
  - No cap (deferred to balance pass)
  - Persona `essential_item_types` snapshot + adoption-time advisory — **shipped** (`commands/CmdCharacter.py:_build_persona_entry,_adopt_persona`); `_build_persona_entry` captures `get_essential_item_type_ids(caller)` at save time, and `_adopt_persona` emits a yellow advisory when the saved composition diverges from currently-equipped essentials. Adoption proceeds regardless.
- Unmasking-moments hook — **shipped** (PR #134, prose follow-up PR #136). `world/identity.py:apply_signature_change` context manager wraps every mutation that may change the actor's identity signature (`_clear_all_overrides`, `_nudge_height`, `_nudge_build`, `_set_keyword_override`, `_adopt_persona`, and `ClothingMixin.wear_item` / `remove_item` for `disguise_essential` items). When a signature actually changes, `_broadcast_unmasking` walks the room's conscious observers and updates their recognition memory according to the A/B/C/D matrix in §Unmasking Moments — flipping `lost_contact` on prior presentations, refreshing the new presentation's recency, and forming `linked_to` chains. `get_linked_aliases` walks the chain forward and surfaces aliases in `recall` (`Also known as: ...`) and `memory` (`(aka ...)`). Per-cell narrative prose now ships via `_send_unmasking_message` (cell B: recognition-gained, cell D: link-discovered, cell C: silent).
- Corpse apparent-UID propagation — **shipped** (PR #133). `typeclasses/corpse.py` carries `sleeve_uid`, `get_worn_items()`, a recognition-aware `get_display_name`, and `at_object_leave` invalidation so worn-item removal from a corpse re-derives its apparent presentation. Observers who tagged the deceased under a particular signature continue to auto-recognize the body under that same signature; stripping the body changes the signature and breaks the recognition tag, mirroring the live-character semantics.
- Lifecycle integration:
  - Death: clears overrides; corpse stores `real_sleeve_uid` + `last_active_signature` snapshot — **shipped** (PR #133 + Issue #182). Corpse `sleeve_uid` propagation and presentation-aware recognition shipped in PR #133. Issue #182 closed the remaining gaps: `_create_corpse_from_character` now stores the full identity-signature 5-tuple as `corpse.db.signature_at_death` alongside the existing `apparent_uid_at_death` hash (so forensic consumers can reconstruct component axes — the hash alone is one-way), and `_clear_all_overrides(character)` runs after the snapshot to wipe `height_override` / `build_override` / `keyword_override` / `active_persona` on the dead Character (snapshot-before-clear ordering preserves the death-moment disguise). `world.identity.render_signature_summary(signature)` provides a stable keyed view over the 5-tuple for future forensic-reconstruction consumers (cf. Future Hooks: photo evidence, signature snapshots as evidence, multi-UID linking).
  - Sleeve swap (flash clone / resleeving): salt is `real_sleeve_uid`, so personas don't carry across bodies; persona records remain on the player — **🔵 Deferred** until the resleeving system lands. Behavior holds today by virtue of `sleeve_uid` inheritance (`commands/charcreate.py:386-388` — flash clones reuse the dead character's `sleeve_uid`, so bare-faced Apparent UIDs match across the respawn boundary) + persona storage on the Character. No explicit flash-clone-aware code path exists yet; the explicit awareness work is parked pending the resleeving design.
  - Item destruction: removing/destroying essential item changes signature → Apparent UID changes → observers see stranger — **shipped** (covered by the unmasking-moments wiring on `remove_item`; destruction routes through removal).
- No observer-side disguise metadata — recognition system stays transparent to disguise mechanics
- No auto-equip / auto-remove on persona swap — disguise emerges from observable state

**Stub / defer to later phases:**
- Apparent UID caching + perf optimization (measure first; add only if needed)
- Per-axis Resonance difficulty tuning (Phase 5)
- Clothing coverage gating (no coverage requirement for now)
- Active impersonation detection — Resonance-based hints on similar-but-different signatures (Phase 5)
- Disguise item quality tiers (Phase 3.5 / 5)
- Forcible strip via grapple (needs grapple system integration)
- Photo / recording mechanic (capture full signature for later impersonation; future phase)
- Pharma / voice-modulation override axes (future phase)
- `appear edit <persona>` (deferred — players currently delete + re-save)
- Web-UI maximal persona capture (deferred)

### Phase 3.5 — Disguise Item Taxonomy

**Scope:** Concrete disguise item catalog and prototypes built atop the Phase 3 foundation.

**Status:** 🟢 Shipped. Catalog, taxonomy, suppression cohesion, and sdesc-fragment audit are all complete. Biomod / pharmaceutical items and identity artifacts remain deferred to Future Hooks per scope.

- Specific essential-item prototypes (balaclava, hood, cowl, mask, etc.) with appropriate `disguise_essential` and `is_disguise_item` flags — **shipped** (PR #132). BALACLAVA plus 12 Phase 3.5 prototypes in `world/prototypes.py`.
- Tagging conventions for "same type" matching (so a replacement balaclava restores signature) — **shipped** (#178, PR #179): `disguise_type_id` is the keying field consumed by `get_essential_item_type_ids`; per-prototype rationale is recorded inline above each prototype and summarised in the "Taxonomy decisions" subsection below. Lock-in regression tests live in `world/tests/test_disguise_prototypes.py`.
- Distinguishing-feature interaction with disguise items (which items suppress which features) — **shipped** (#176): hair fallback suppression is driven by the unified clothing-coverage system (item lists `"hair"` in `coverage` → fallback skipped). The legacy `covers_hair` boolean has been removed. `"hair"` is now a first-class body location in `DEFAULT_LONGDESC_LOCATIONS` and leads the `ANATOMICAL_DISPLAY_ORDER` head region. Broader suppression conventions (e.g. mask-suppresses-face) follow naturally from coverage lists; no parallel flags required.
- Item-driven sdesc fragment contributions (cohesion with `sdesc_short` from Phase 2) — **shipped** (#180): all 13 disguise prototypes' `worn_sdesc_short` values verified to produce grammatical `format_clothing_feature` clauses. Fixed `mirrorshades` slipping through `_PLURALIA_TANTUM_NOUNS` (would render as `"in a mirrorshades"`); added renderer-cohesion regression test that walks every prototype.
- Sub-visible disguise items (`disguise_silent_feature`) — **shipped** (issue #174). Items flagged `disguise_silent_feature=True` are excluded from the distinguishing-feature partition in `get_distinguishing_feature` (`typeclasses/characters.py:908–925`) while remaining fully participant in the disguise / Apparent UID system (signature, recognition memory, swap detection). Sole current user: `COLORED_CONTACTS` — contacts sit on the eye, so observers register eye colour rather than "person in colored contacts." Extension point for future sub-visible items (dental prosthetics, scent maskers, etc.). Orthogonal to the Class A / Class B `disguise_adjective` axis (sdesc adjective injection) and to the `"hair"` coverage-list entry (hair feature suppression, #176).
- Pharmaceutical / biomod items for `@longdesc` override — **deferred** (depends on body-mod system; tracked under Future Hooks).
- Photos / identity artifacts — **deferred** (tracked under Future Hooks).

#### Taxonomy decisions (`disguise_type_id`)

The 13 Phase 3.5 disguise prototypes in `world/prototypes.py` are grouped by `disguise_type_id` as follows. Items sharing an id are **swap-equivalent** at the Apparent UID layer: an observer who has memorised the wearer in one variant will still recognise them in another of the same id. Items with distinct ids shift the UID on swap, even when they share a coverage slot. The rationale comment above each prototype is the single source of truth; the table below is a navigational summary.

| `disguise_type_id` | Prototypes | Rationale (one-liner) |
| --- | --- | --- |
| `balaclava` | `BALACLAVA`, `SKI_MASK` | Both fully obscure head + hair; silhouette and concealment surface are interchangeable. |
| `face_mask` | `SURGICAL_MASK` | Flat paper rectangle over the lower face; deliberately distinct from `respirator` (different visible signature). |
| `respirator` | `RESPIRATOR` | Twin filter cans and moulded shell are unmistakable; deliberately distinct from `face_mask`. |
| `domino_mask` | `DOMINO_MASK` | Sole occupant; a small upper-face mask has no swap-equivalent peer in the current catalog. |
| `face_bandana` | `FACE_BANDANA` | Sole occupant; knotted fabric over the lower face has no swap-equivalent peer. |
| `hood` | `HOODIE_HOOD_UP` | Sole occupant; a drawn hood casts the face in shadow rather than covering it with fabric. |
| `wig` | `BLACK_WIG`, `BLOND_WIG`, `BROWN_WIG` | All read as "wearing a wig" at observer distance; colour is appearance flavour, not an identity-class distinction. The bare↔wigged UID shift is driven by `disguise_essential`, not the per-colour id. |
| `contacts` | `COLORED_CONTACTS` | Sole occupant; contacts sit on the eye and read only as eye colour. Also flagged `disguise_silent_feature`. |
| `mirrorshades` | `MIRRORSHADES` | Reflective chrome finish is the salient identity feature; deliberately distinct from `sunglasses`. |
| `sunglasses` | `AVIATOR_SUNGLASSES` | Conventional tinted lenses obscure eyes without reflecting; deliberately distinct from `mirrorshades`. |

**Guiding principle.** When two prototypes share a body-coverage slot, the question is whether their *visible signature* differs sharply enough that an observer would notice the swap. If yes (surgical mask ↔ respirator, mirrorshades ↔ aviators), they get distinct ids. If no (two balaclava variants, three wig colours), they collapse to a shared id. Colour alone is not enough to split an id — colour is appearance flavour. The bare↔disguised transition is governed by `disguise_essential`; the same-slot swap-equivalence question is governed by `disguise_type_id`. These axes are orthogonal.

Lock-in regression tests live in `world/tests/test_disguise_prototypes.py` (`TestSameTypeSwapApparentUidStable`, `TestCrossTypeSwapApparentUidShifts`, `TestEssentialTypeIdsFromCatalog`).

### Phase 4 — Cybernetics

**Scope:** Digital memory and identity exchange.

- Cyberbrain organ/implant (depends on cyberware system)
- Digital memory storage (same data model as organic)
- Digital ID exchange command
- Memory backup/restore mechanics
- Hackable/forgeable contact entries
- Staff identity overlay migrated from permission check to cyberware

### Phase 5 — Resonance Mechanics

**Scope:** Give Resonance full mechanical integration. (Disguise piercing landed early — see [Disguise Piercing](#disguise-piercing) — and uses Intellect-vs-Resonance, not opposed-Resonance.)

- Memory decay curves (low Resonance → memory loss over time)
- Auto-recognition from proximity + time + high Resonance
- Confidence display (uncertain recognition at low confidence)
- Active impersonation detection (similar-but-different signatures surface a soft hint)
- Social reads (emotional state, lie detection during introductions)
- Brain damage → partial memory loss (risk scaled to damage severity)

---

## Appendix: Adjacent Room Sightings

The existing adjacent room sighting system (`rooms.py:440-474`) already shows characters in neighboring rooms anonymously: `"You see a lone figure to the north."` or `"You see a group of N people standing to the north."` This is consistent with the recognition model — at distance, you can't make out details. No changes needed to this system.

---

## Appendix: Existing Forensic Data

For reference, the existing forensic data preserved by the system:

**Blood pools** (`typeclasses/objects.py:468+`): character name, severity, timestamp, age progression, forensic descriptions.

**Corpses** (`typeclasses/corpse.py`): original character name/dbref, account dbref, death time, cause of death, medical conditions, wounds at death, physical description, longdesc data, skintone, gender. Decay stages: fresh (<1h), early (<1d), moderate (<3d), advanced (<1w), skeletal (>1w).

`sleeve_uid` has been added to corpse forensic data (PR #133) — corpses participate in the recognition pipeline. PR-E adds a `signature` + `apparent_uid` field to each blood-pool incident (data prep only — no consumer command yet); see §"Forensic Recognition Engine" for the engine surface that will read them once a blood-pool examination command lands.

---

## Appendix: RAG Integration Notes

The recognition memory data model is designed to port into a retrieval-augmented generation (RAG) pipeline when the system matures. This appendix documents the intended architecture and recommended stack so infrastructure decisions align with the data model.

### Why RAG

Recognition memory starts as simple dict lookups by `sleeve_uid`, but future use cases require semantic retrieval:

- **Player recall**: `remember the docks` → find all memories with spatial context matching "docks"
- **NPC behavior**: An NPC needs to assess "have I met this person before, and should I be hostile?" based on past interaction history
- **Contextual reactions**: NPCs referencing past encounters in dialogue ("Last time you were here, you started a fight.")
- **Investigation**: "Who have I seen carrying a knife?" → semantic search over appearance snapshots and interaction logs

These queries don't map to exact key lookups — they require semantic similarity search over the text fields in memory entries.

### Data Model Compatibility

The recognition memory schema is RAG-ready by design:

| Field | RAG Role |
|---|---|
| `assigned_name` | Metadata filter (exact match) |
| `first_seen`, `last_seen` | Metadata filter (temporal range queries) |
| `location_first_seen`, `location_last_seen`, `locations_seen` | Metadata filter (spatial queries) |
| `tags` | Metadata filter (categorical queries) |
| `relationship_valence` | Metadata filter (sentiment queries) |
| `confidence` | Metadata filter (certainty threshold) |
| `notes` | **Embedded content** (free-text, semantic search) |
| `sdesc_at_first_encounter`, `sdesc_at_last_encounter` | **Embedded content** (appearance-based search) |
| `recent_interactions[].summary` | **Embedded content** (event-based search) |

Structured fields become metadata filters for pre-filtering. Text fields are embedded for semantic similarity search. This two-stage retrieval (filter → rank) is the standard RAG pattern.

### Recommended Stack

Evaluated against project constraints: runs alongside MUD server in Docker, no GPU required, tens of thousands of small documents, Python-native.

**Vector store — ChromaDB or LanceDB**

| | ChromaDB | LanceDB |
|---|---|---|
| **Backend** | SQLite | Lance columnar format |
| **Deployment** | Embedded (in-process) or client/server | Embedded (in-process) |
| **Python-native** | Yes | Yes |
| **Metadata filtering** | Yes | Yes |
| **Scale ceiling** | ~1M documents | ~10M documents |
| **Docker-friendly** | Yes (pip install) | Yes (pip install) |

Either works. ChromaDB has a larger community and more documentation. LanceDB has better performance at scale and native support for versioned datasets (useful if memory entries are updated frequently). **ChromaDB is the simpler starting point.**

**Embedding model — sentence-transformers**

| Model | Size | Dimensions | Speed (CPU) | Quality |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 80MB | 384 | Fast | Good |
| `all-mpnet-base-v2` | 420MB | 768 | Moderate | Better |
| `nomic-embed-text-v1.5` | 550MB | 768 | Moderate | Best (local) |

**`all-MiniLM-L6-v2` is recommended for Phase 1** — small footprint, fast on CPU, sufficient quality for short memory documents (100-500 tokens each). Can upgrade to `nomic-embed-text` later if retrieval quality needs improvement.

**LLM synthesis — deferred**

The LLM layer (interpreting retrieved memories into natural language responses) is a separate decision. Options when the time comes:

- **Local**: Ollama + Mistral/Llama (requires more resources, full autonomy)
- **API**: OpenAI / Anthropic (simpler, ongoing cost, latency dependency)
- **Hybrid**: Local embeddings + API for synthesis (balanced)

This decision depends on the MUD server's resource budget and acceptable latency for NPC dialogue generation. It does not affect the storage or embedding layer.

### Indexing Strategy

Each character maintains its own recognition memory dict on the Character itself (source of truth — see §Memory Architecture). The vector index is a **read-through cache** built from these dicts:

```
Character.recognition_memory  ←  source of truth
         ↓ on write
ChromaDB collection (per-character)  ←  vector index
         ↑ on query
Semantic search results              →  returned to caller
```

- **Writes**: When a recognition entry is created or updated, the corresponding document in the vector index is upserted
- **Reads**: Exact lookups (by Apparent UID) hit the dict directly — no vector search needed. Semantic queries hit the vector index.
- **Consistency**: The dict is authoritative. The vector index can be rebuilt from dicts at any time (cold start, migration, corruption recovery).

### Collection Strategy

Two options for organizing the vector store:

**Option A — One collection per character**: Each character's memories are a separate ChromaDB collection. Simple isolation, easy cleanup when a character is deleted. Downside: many small collections if hundreds of NPCs.

**Option B — Single collection with character metadata**: All memories in one collection, with `owner_sleeve_uid` as a metadata field for filtering. Simpler management, better for cross-character queries (e.g., admin searching "who remembers Jorge?"). **Recommended.**

### Document Schema (ChromaDB)

```python
{
    "id": "{owner_uid}_{target_uid}",  # Unique document ID
    "document": "{notes} {interaction_summaries} {sdesc_snapshots}",  # Embedded text
    "metadata": {
        "owner_uid": str,              # Whose memory this is
        "target_uid": str,             # Who is remembered (sleeve_uid)
        "assigned_name": str,          # Name assigned by owner
        "first_seen": str,             # ISO timestamp
        "last_seen": str,              # ISO timestamp
        "times_seen": int,             # Encounter count
        "locations": str,              # Comma-separated location list
        "tags": str,                   # Comma-separated tags
        "relationship_valence": str,   # hostile/neutral/friendly/unknown
        "confidence": float,           # 0.0-1.0
    }
}
```

### Performance Budget

Estimated resource usage for the RAG layer (when implemented):

- **Embedding model in memory**: ~80MB (MiniLM) to ~550MB (nomic)
- **Vector index on disk**: ~50 bytes per dimension per document. At 384 dimensions × 50,000 documents: ~7MB
- **Embedding latency**: ~5ms per document on CPU (MiniLM), batched
- **Query latency**: <10ms for top-K retrieval from 50,000 documents
- **Total additional RAM**: ~100-600MB depending on model choice

This fits comfortably alongside the MUD server in Docker.

### Implementation Timeline

RAG infrastructure is **not needed until Phase 5** (Resonance Mechanics) at the earliest. The recognition system operates on exact dict lookups through Phases 1-4. RAG enables:

- Semantic `remember` command (Phase 5+)
- NPC behavioral memory queries (Phase 5+)
- Investigation system memory searches (future forensics phase)
- Memory decay with semantic importance weighting (Phase 5+)

The data model is ready now. The vector infrastructure plugs in later without schema changes.
