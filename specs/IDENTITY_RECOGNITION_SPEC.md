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

A per-character memory mapping stored on the brain organ: "I know the person with this Apparent UID as [name], and here's everything I remember about them." When you see someone whose current Apparent UID is in your memory, you see the name you assigned. When you don't recognize them, you see their sdesc. Because the Apparent UID is derived from the target's full identity signature (real sleeve, active overrides, essential items), the same physical body can produce different recognition entries under different disguises — see §Memory Data Model.

### Apparent Identity

What the recognition pipeline actually resolves against. Three distinct concepts work together:

1. **Identity Signature** — a tuple of all observable identity inputs: real `sleeve_uid` (the body's salt), active presentation overrides (height, build, keyword), and the sorted set of equipped essential disguise item types. The signature is recomputed on access from current state.
2. **Apparent UID** — a deterministic 16-character hex digest of the identity signature (`blake2b(signature_bytes, digest_size=8).hexdigest()`). This is the **key** that recognition memory is stored under. Same signature → same UID → auto-recognition; any signature change → new UID → observers see a stranger.
3. **Persona** — a player-private label for a remembered combination of overrides. Personas do **not** generate UIDs themselves; they are pure recall ergonomics. Adopting a persona restores its captured overrides, which then flow through the signature → UID pipeline like any other state.

The sdesc is overridable through `appear`, but the distinguishing feature always reflects actual visible state — true disguise requires changing your clothes (or destroying / acquiring essential items).

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

Items will need a `sdesc` or `worn_sdesc_short` attribute for this purpose — a brief, recognizable description suitable for the sdesc clause.

#### Hair-based Feature

If no clothing provides a distinguishing feature (nude, very minimal clothing), the system falls back to hair.

Format: `"with {color} {style}"` — e.g., `"with red dreadlocks"`, `"with cropped white hair"`, `"with long black braids"`

If the character is bald or has no hair attribute set, this is skipped.

If a head covering (hood, helmet, hat) is worn, hair is hidden and not used even as fallback.

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
    D --> E[Get looker's brain organ]
    E --> F{Apparent UID in recognition_memory?}
    F -->|Yes, has assigned_name| G[Return stored assigned_name]
    F -->|Yes, no assigned_name<br/>(forgotten entry)| H[Return target's sdesc]
    F -->|No| H
    G --> I{Staff cyberware active?}
    H --> I
    I -->|Yes| J["Append ' [real_name]'"]
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
        "last_seen": str,               # ISO timestamp of most recent encounter
        "times_seen": int,              # Total encounter count

        # Spatial context
        "location_first_seen": str,     # Room name/key where first encountered
        "location_last_seen": str,      # Room name/key where last seen
        "locations_seen": [str],        # All locations where encountered

        # Appearance snapshot
        "sdesc_at_first_encounter": str,  # What they looked like initially
        "sdesc_at_last_encounter": str,   # What they looked like most recently

        # Player-authored
        "notes": str,                   # Free-text notes (player-written)
        "tags": [str],                  # Player-assigned tags ("dangerous", "merchant", "ally")

        # System-derived
        "confidence": float,            # 0.0-1.0, Resonance-influenced recognition certainty
        "relationship_valence": str,    # "hostile", "neutral", "friendly", "unknown"
        "lost_contact": bool,           # True once the entry's UID has not matched any
                                        # observable character for an extended period;
                                        # entry remains visible in `memory` and `recall`
                                        # but is annotated as out of contact.

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

This is stored as a db attribute on the brain organ, keyed by **Apparent UID**. The `recent_interactions` list should be capped (e.g., last 20 interactions per entry) to prevent unbounded growth, with older interactions eligible for summarization or archival.

**One-time wipe (engine PR rollout):** Existing `recognition_memory` dicts (keyed on real `sleeve_uid` from prior phases) are wiped at engine-PR deployment. There is no migration recompute; players rebuild recognition organically under the new keying. This is acceptable because no production characters depend on the prior memory schema for ongoing play, and the schema change is total (key shape, value shape).

**Orphaned entries (`lost_contact`):** A recognition entry whose Apparent UID has not matched any observable character within a configurable window (deferred to balance pass; provisional default: 30 in-game days) is marked `lost_contact = True`. The entry stays visible in `memory` and `recall` (player-authored notes are valuable lore even when the trail goes cold) and is rendered with a "(lost contact)" annotation. A future player command may allow explicit pruning of lost-contact entries; auto-pruning is intentionally **not** done.

### Remembering Names

**`remember` command:**

```
remember <target> as <name>
```

Stores the name in the rememberer's brain recognition memory under the target's current **Apparent UID**. Any name is valid — false names are always possible. Re-remembering overwrites. Names are validated against the cross-namespace uniqueness rule (see §Personas — *Cross-namespace uniqueness*): the assigned name must not collide with the keyword catalog, the caller's persona names, or any existing recognition `assigned_name` on a different Apparent UID.

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

### Organic Memory (Brain Organ)

Recognition data lives on the brain organ object (`world/medical/constants.py` defines the brain organ with `container: "head"`, `vital: True`, `capacity: "consciousness"`).

**Storage:** A new db attribute on the brain organ: `db.recognition_memory` (dict).

**Properties:**
- Populated by explicit player action (`remember` command)
- Future: auto-populated by Resonance-driven proximity detection
- Lost if the brain is destroyed (brain destruction = death, so this is moot for the current character, but matters for brain transplant scenarios)
- Brain damage (non-fatal) carries a risk of partial memory loss — individual entries can be degraded or lost. This is a future enhancement once the memory pool is rich enough to make partial loss meaningful.
- Flash clones get a new brain — they start with empty recognition memory. The clone is a stranger who happens to look like someone others remember.

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
- **Disguise perception** — Higher Resonance → better chance of seeing through disguises (opposed Resonance check: disguiser vs. observer).
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

Each override is a **skill-based performance** — using the `appear` verb triggers a Resonance check for that axis. The check is a stub in the foundation cut (always succeeds) but the call point exists in code for future tuning. Per-axis difficulty modeling is deferred.

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

1. If the character has an active `keyword_override`, look the override up in the runtime keyword catalog (`KeywordManager` script's `db.feminine_keywords` / `db.masculine_keywords` / `db.neutral_keywords`, falling back to the `_DEFAULT_FEMININE_KEYWORDS` / `_DEFAULT_MASCULINE_KEYWORDS` / `_DEFAULT_NEUTRAL_KEYWORDS` frozensets in `world/identity.py` when the script is unavailable).
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

> **Status (current PR — `appear-persona-cluster`):** The surface verbs (`appear`, `stop appearing`, `personas`, `persona`, `remember me as <name>`, `forget <persona>`) and the persona storage schema are shipped. The signature engine, Apparent UID derivation, essential-item integration, pronoun derivation under disguise, and `get_sdesc()` consumption of overrides land in the follow-up engine PR. Until that lands, override axes are written to character DB but do not yet affect what observers perceive.

**A persona stores:**
- A **player-chosen name** (case-insensitive lookup, case-preserving display, player-private — never visible to other characters)
- The **override values** active at save time (height, build, keyword) — `None` for axes that were unset
- The **types of essential disguise items** equipped at save time *(reserved field, populated when the engine PR lands; written empty in the foundation cut)*
- A **freeform notes field** for player annotations *(reserved field, currently always empty)*
- A **created-at timestamp** and the **room name** where it was saved

**Pronouns are not stored separately.** Restoring a persona restores its `keyword_override`, and pronouns derive from that keyword via the rule in §Pronouns Under Disguise. A persona that captured a feminine keyword automatically restores feminine pronouns when adopted; a persona that captured a custom keyword automatically restores neutral pronouns. No persona field is needed for gender.

**Personas do NOT generate identities.** They are pure recall aids. When a player adopts a persona, the system applies the captured overrides as a **clean swap** — overwriting all three axes including any unset axes (so adoption produces an exact replay of the saved state, never a merge). The resulting Apparent UID, once the engine PR lands, will be derived from the restored state, not from the persona itself. Two personas with identical overrides + item-type composition will yield the same Apparent UID — they are just labels in the player's memory.

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

Examples:
- **Essential**: balaclava, full mask, cowl, wig, contacts, prosthetic face, voice modulator (when voice integration lands)
- **Non-essential**: gloves, scarf, signature jacket, distinguishing hat

The item taxonomy itself (which items exist, their categories, quality tiers) is designed in **Phase 3.5**, a separate cut after the foundation lands. The foundation only needs the two flags to function correctly with zero defined disguise items.

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

### Impersonation

Impersonation is **emergent**, not mechanical. The system does not detect or prevent it.

Two characters can create overrides + ensembles with identical descriptors, keywords, and similar clothing — they will look the same in the sdesc but have different Apparent UIDs (different salts). This means:

- **Strangers** seeing both at different times would have no way to distinguish them visually. A character who met "Natasha" on Monday and meets a different `short woman in a black cape` on Friday would naturally assume it's the same person — until they `remember` them by a name and discover the recognition system creates a *new* entry instead of matching the old one.
- **People who tagged the original signature** are not fooled by a visual look-alike — the UIDs don't match. The impostor appears as a stranger who happens to look similar.
- **Investigation gameplay** emerges naturally: if a witness meets two different UIDs with matching sdescs, that's a clue that one of them is an impostor. Which one is "real" requires further investigation.

Building a reputation — having many people tag a recognized signature — is itself a form of identity security. The more people who "know" a signature, the harder it is for a visual impostor to operate in those social circles.

> **Design note:** No mechanical impersonation detection in the foundation cut. Active detection (e.g., "this person reminds you of someone...") is deferred to Phase 5 alongside other Resonance-based perception mechanics.

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
- **Perception checks (Phase 5)**: Opposed Resonance rolls to see through disguise. Disguise items add to disguiser's roll. Familiarity bonus for observers who know the real identity well.
- **Active impersonation detection (Phase 5)**: Resonance-based hints when a disguised signature closely matches a known identity (e.g., *"this person reminds you of someone..."*).
- **Forcible item removal via grapple**: Requires grapple-system integration for stripping equipment from a grappled character.
- **Pharmaceutical / biomod items**: Consumable or implanted modifications that override `@longdesc` and contribute to the identity signature (extending the signature function with body-mod inputs). Closes the last gap: with body mods, even direct `look` reveals a different person. Pharmaceuticals would be temporary (wears off over time), potentially expensive/rare, and could carry side effects (stat penalties, addiction).
- **Photos / identity artifacts**: Captured signature snapshots usable as recipes (own personas) or investigation tools (others'). Salt-acquisition mechanics enable true impersonation gameplay. Ties into Phase 4 (cybernetics) where digital identity data becomes hackable and forgeable.
- **Voice modulation**: Integration with say/whisper/communication so voice becomes part of the identity signature for observers who can hear but not see (or in addition to visual identification).
- **Web UI integration**: Personas designed to mirror the planned identity/contact archive system; eventual web UI surface for managing personas, photos, and contact memory in one place.
- **Salt-acquisition mechanics for true impersonation**: Stolen contact cards, hacked digital identities, and other adversarial means by which an impostor can acquire the original's salt and become auto-recognized as them.
- **Explicit `gender_override` axis**: Phase 3 derives pronouns from `keyword_override` against the catalog's gender lists, so a player who wants gendered pronouns picks a gendered keyword. A future explicit override axis would let a player pair a custom (`@shortdesc`) keyword with a chosen pronoun set without forcing them through a catalog keyword. Deferred until a real player need surfaces.
- **Forensic linking of multiple Apparent UIDs to one real identity**: Investigation gameplay where a sufficiently-resourced investigator can correlate multiple recognition entries (different Apparent UIDs) and infer they refer to the same underlying `sleeve_uid`. Requires evidence-system integration (Phase 5+).
- **Player-initiated lost-contact pruning**: A `forget --lost` (or similar) command letting players explicitly drop entries the system has marked `lost_contact`. Auto-pruning is deliberately not done; this gives the player the choice.

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
def msg_room_identity(location, template, char_refs, exclude=None):
    """Send identity-aware message to all observers in a room.

    Args:
        location: Room to broadcast in.
        template: Message string with {placeholder} tokens for characters.
        char_refs: Dict mapping placeholder names to Character objects.
            e.g., {"actor": attacker_obj, "target": target_obj}
        exclude: Characters to exclude from receiving the message.
    """
    for observer in location.contents_get(exclude=exclude):
        if not hasattr(observer, "msg"):
            continue
        resolved = template
        for placeholder, char in char_refs.items():
            display_name = char.get_display_name(observer)
            resolved = resolved.replace(f"{{{placeholder}}}", display_name)
        observer.msg(resolved)
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

---

## Target Resolution

Currently, players type character names to target them. With the recognition system, targeting must work with assigned names, sdescs, and ordinals.

### Targeting Priority

When a player types a targeting string (e.g., `attack jorge` or `attack tall man`):

1. **Assigned names** — Check the player's recognition memory for any character in the room whose assigned name matches the input
2. **sdescs** — Match against visible characters' sdescs (partial matching, case-insensitive)
3. **Ordinals** — `"2nd tall man"` uses the existing ordinal system (`get_search_query_replacement`)
4. **Real keys** — Fall through to standard Evennia search (matches `.key` and aliases)

### Implementation Approach

Override `Character.get_search_candidates()` (already exists at `characters.py:515-556`) to inject recognition-aware search results for the searching character. Alternatively, add a custom search hook that checks the searcher's recognition memory.

The existing `CmdAttack` manual substring search (`core_actions.py:110-120`) must be updated to search against assigned names and sdescs, not just `.key`.

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
- Add `sleeve_uid` to corpse forensic data
- Looking at a corpse: investigator sees recognized name or sdesc based on their memory
- Corpse decay interacts with recognition: at advanced decay, the physical features become unrecognizable (already described in existing decay stage text)

### Evidence and Investigation (Future)

When forensic investigation commands are built:
- Evidence sources (fingerprints, DNA, etc.) link to `sleeve_uid`
- Investigators see recognized names or sdescs when examining evidence
- Creates detective gameplay: "The blood at the crime scene belongs to that tall man I saw earlier"

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

### On Brain Organ

| Attribute | Type | Default |
|---|---|---|
| `db.recognition_memory` | dict | `{}` |

### On Items (for sdesc feature derivation)

| Attribute | Type | Purpose |
|---|---|---|
| `db.sdesc_short` | str or None | Brief recognizable description for sdesc feature clause (e.g., "leather jacket", "red power armor") |

---

## Impact on Existing Systems

All locations that currently use `.key` directly or bypass `get_display_name` need refactoring:

| System | File(s) | Current Issue | Required Change |
|---|---|---|---|
| Combat message templates | `world/combat/messages/__init__.py` | Uses `.key` for `attacker_name` / `target_name` | Use `get_display_name` with per-observer rendering |
| Attack processing errors | `world/combat/attack.py:310, 329` | Uses `.key` in messages | Route through `get_display_name` |
| Shield messages | `world/combat/attack.py:231-269` | Uses `get_display_name_safe()` | Already partially correct — verify observer is passed |
| Normal movement | Evennia defaults | `announce_move_from/to` use `.key` | Override with custom per-observer announcements |
| Communication (say/whisper/emote) | Evennia defaults | All use `.key` | Custom command overrides required (see `EMOTE_POSE_SPEC.md`) |
| Death filtering | `typeclasses/characters.py:137-205` | Pattern-matches `.key` in message strings | Refactor to use structured message data |
| CmdAttack target resolution | `commands/combat/core_actions.py:110-120` | Manual substring match on `.key` | Add recognition-aware search |
| Exit drag messages | `typeclasses/exits.py:317-340` | Uses `.key` directly | Route through `get_display_name` |
| Room character listing | `typeclasses/rooms.py:410` | Uses `get_display_name(looker)` | Already correct |
| Combat movement messages | `commands/combat/movement.py` | Uses `get_display_name(observer)` | Already correct |
| Look command / appearance | `typeclasses/appearance_mixin.py` | Uses `get_display_name(looker)` | Already correct |

### Systems Already Correct

Several systems already route through `get_display_name(looker)` and will work automatically once the override is in place:
- Room character listings (`rooms.py:410`)
- Combat movement messages (`commands/combat/movement.py`, ~25 uses)
- Look / appearance rendering (`appearance_mixin.py:363, 397-419`)
- Exit character previews (`exits.py:673`)
- Medical commands (`commands/CmdMedical.py`)
- Clothing commands (`commands/CmdClothing.py`)
- Most inventory/interaction commands

---

## Character Creation Updates

Character creation (both in-game `create` and web-based) must be updated to include identity attribute selection:

### New Chargen Steps

1. **Height selection** — short, below-average, average, above-average, tall
2. **Build selection** — slight, lean, athletic, average, stocky, heavyset
3. **Hair color selection** — from approved list, or bald/none
4. **Hair style selection** — from approved list (contextual based on color choice), or bald/none
5. **Keyword selection** — gender-gated list from the keyword table
6. **Preview** — Show the assembled sdesc: `"You will appear as 'a lanky man with red dreadlocks' to strangers."`

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
5. Initialize empty `recognition_memory` on all brain organs
6. Staff can run `@fixchar/all` to batch-process

Players should be prompted to customize their sdesc on next login if defaults were applied.

---

## Phased Implementation

### Phase 1 — Foundation

**Scope:** sdesc system, recognition storage, manual assignment, `get_display_name` override, chargen updates.

- New attributes: `sleeve_uid`, `height`, `build`, `hair_color`, `hair_style`, `sdesc_keyword`
- Physical descriptor table in constants
- Keyword list in constants
- Sdesc composition logic
- `recognition_memory` on brain organ
- `Character.get_display_name(looker)` override
- `@shortdesc` command
- `remember` / `forget` / `recall` / `memory` commands
- Grammar engine (articles, possessive, objective, self-perception)
- Chargen updates
- Flash clone `sleeve_uid` inheritance
- `@fixchar` migration
- Staff identity overlay (permission-based stopgap)

### Phase 2 — Consistency

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

### Phase 3 — Disguise (Foundation)

**Scope:** Identity signature engine, the `appear` / persona verb cluster (per-axis overrides + persona snapshots), disguise item flags, and lifecycle integration. Shipped incrementally across multiple PRs.

**Build in Phase 3:**
- Identity signature tuple: `(real_sleeve_uid, height_override, build_override, keyword_override, sorted(essential_item_type_ids))` *(engine PR)*
- Apparent UID derivation: `hashlib.blake2b(repr(signature).encode("utf-8"), digest_size=8).hexdigest()` — deterministic 16-char hex, recomputed on access (no caching in foundation cut) *(engine PR)*
- Per-axis `appear` command grammar — **shipped (`appear-persona-cluster`)**:
  - `appear` (status), `appear taller | shorter`, `appear thinner | fatter | bulkier | leaner`, `appear <keyword>`, `appear <persona name>`
  - `stop appearing` (clears all overrides + active-persona pointer)
- Sdesc descriptor recomposition via existing `get_physical_descriptor(height, build)` table *(engine PR — wire into `get_sdesc()`)*
- Pronoun derivation under disguise via `get_apparent_gender(char)` helper consulting `keyword_override` against `KeywordManager` gender lists; consumers (`world/emote.py`, `world/grammar.py`'s `transform_pronoun()`, longdesc/sdesc renderers, social templates) redirected through this helper *(engine PR)*
- Resonance check stub on each axis override (always succeeds; call point exists for Phase 5 tuning)
- DB attributes for active overrides on character — **shipped**: `db.height_override`, `db.build_override`, `db.keyword_override`, `db.active_persona`, `db.personas`
- `db.disguise_essential` flag on items — contributes to identity signature when worn *(engine PR — flag schema + signature wiring; concrete item prototypes ship in Phase 3.5)*
- `db.is_disguise_item` flag on items — Phase 5 perception bonus hook (defined but inert in Phase 3) *(engine PR — flag schema only)*
- Hook `get_sdesc()` / `get_display_name()` to consume override axes and Apparent UID *(engine PR)*
- Recognition memory re-keyed on Apparent UID; one-time wipe of existing `recognition_memory` dicts at engine-PR deployment (no migration recompute) *(engine PR)*
- Orphaned-entry handling: `lost_contact` boolean flag + render annotation in `memory` / `recall`; never auto-pruned *(engine PR — flag + render; inactivity threshold itself is a balance-pass tuning value)*
- Full keyword catalog available regardless of character gender (override bypasses gender filter) — **shipped via `appear <keyword>` validation**
- Available to **all characters** (no access level restriction)
- Persona layer (player-private ergonomics) — **shipped (`appear-persona-cluster`)**:
  - `remember me as <name>` — capture current overrides as a persona (verb-symmetric with `remember <target> as <name>`)
  - `appear <persona name>` — adopt a persona (clean swap; overwrites all axes including unset ones)
  - `personas` — list saved personas, recency-sorted; active persona marked with `*`
  - `persona <name>` — inspect a single persona
  - `forget <persona name>` — delete a persona; clears overrides and `db.active_persona` if it was active
  - Cross-namespace uniqueness enforced (keyword catalog ∩ recognition names ∩ persona names)
  - No cap (deferred to engine PR / balance pass)
- Lifecycle integration *(engine PR)*:
  - Death: clears overrides; corpse stores `real_sleeve_uid` + `last_active_signature` snapshot
  - Sleeve swap (flash clone / resleeving): salt is `real_sleeve_uid`, so personas don't carry across bodies; persona records remain on the player
  - Item destruction: removing/destroying essential item changes signature → Apparent UID changes → observers see stranger
- No observer-side disguise metadata — recognition system stays transparent to disguise mechanics
- No auto-equip / auto-remove on persona swap — disguise emerges from observable state

**Stub / defer to later phases:**
- Apparent UID caching + perf optimization (measure first; add only if needed)
- Per-axis Resonance difficulty tuning (Phase 5)
- Clothing coverage gating (no coverage requirement for now)
- Perception checks to see through disguise (Phase 5)
- Active impersonation detection (Phase 5)
- Disguise item quality tiers (Phase 3.5 / 5)
- Forcible strip via grapple (needs grapple system integration)
- Photo / recording mechanic (capture full signature for later impersonation; future phase)
- Pharma / voice-modulation override axes (future phase)
- `appear edit <persona>` (deferred — players currently delete + re-save)
- Web-UI maximal persona capture (deferred)

### Phase 3.5 — Disguise Item Taxonomy

**Scope:** Concrete disguise item catalog and prototypes built atop the Phase 3 foundation.

- Specific essential-item prototypes (balaclava, hood, cowl, mask, etc.) with appropriate `disguise_essential` and `is_disguise_item` flags
- Tagging conventions for "same type" matching (so a replacement balaclava restores signature)
- Distinguishing-feature interaction with disguise items (which items suppress which features)
- Item-driven sdesc fragment contributions (cohesion with `sdesc_short` from Phase 2)
- Pharmaceutical / biomod items for `@longdesc` override
- Photos / identity artifacts

### Phase 4 — Cybernetics

**Scope:** Digital memory and identity exchange.

- Cyberbrain organ/implant (depends on cyberware system)
- Digital memory storage (same data model as organic)
- Digital ID exchange command
- Memory backup/restore mechanics
- Hackable/forgeable contact entries
- Staff identity overlay migrated from permission check to cyberware

### Phase 5 — Resonance Mechanics

**Scope:** Give Resonance full mechanical integration.

- Memory decay curves (low Resonance → memory loss over time)
- Auto-recognition from proximity + time + high Resonance
- Disguise perception checks (opposed Resonance rolls)
- Confidence display (uncertain recognition at low confidence)
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

Both need `sleeve_uid` added to their forensic data for integration with the recognition system.

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

Each character's brain maintains its own recognition memory dict (source of truth). The vector index is a **read-through cache** built from these dicts:

```
Brain organ (db.recognition_memory)  ←  source of truth
         ↓ on write
ChromaDB collection (per-character)  ←  vector index
         ↑ on query
Semantic search results              →  returned to caller
```

- **Writes**: When a recognition entry is created or updated, the corresponding document in the vector index is upserted
- **Reads**: Exact lookups (by `sleeve_uid`) hit the dict directly — no vector search needed. Semantic queries hit the vector index.
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
