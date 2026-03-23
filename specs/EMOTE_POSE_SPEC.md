# Emote, Pose & Communication System Specification

## Overview

This specification defines the emote, pose, and communication command system for Gelatinous. It covers:

- **Dot-pose (`.`)** — LambdaMOO-style first-person natural emoting with automatic perspective transformation
- **Traditional emote (`emote`)** — Third-person emoting with identity-aware character references
- **Say (`say`)** — Speech with per-observer speaker attribution
- **Whisper (`whisper`)** — Directed speech with per-observer attribution for speaker and target
- **Grammar engine (`world/grammar.py`)** — Shared infrastructure for verb conjugation, pronoun transformation, and article handling

This system is the **communication counterpart** to the Identity & Recognition System (see `IDENTITY_RECOGNITION_SPEC.md`). The identity spec defines *how characters are perceived*; this spec defines *how that perception is expressed in communication*. The grammar engine defined here is the canonical implementation referenced by both specs.

### Relationship to Existing Systems

- **Supersedes**: `NATURAL_POSING_AND_PRONOUN_FIXES_SPEC.md` (deleted — its `$pron()`/`$conj()` approach is incompatible with per-observer identity rendering)
- **Depends on**: Identity & Recognition System Phase 1 (sdesc, `get_display_name` override, recognition memory)
- **Provides**: Grammar engine referenced by the identity spec's article handling, possessive forms, and subject-verb agreement

### Design Principles

1. **First-person natural writing** — Players write as their characters think: "I lean back." The system handles perspective transformation for all observers.
2. **Per-observer truth** — Every observer may know every character by a different name. Communication renders uniquely per observer.
3. **Speech as structured data** — Quoted speech is tokenized separately from action text, enabling future language systems to process speech independently.
4. **Grammar engine as shared infrastructure** — Verb conjugation, article handling, and pronoun transformation live in a standalone module usable by any system.
5. **Explicit over implicit** — Verb markers (`.verb`) are explicit player annotations. The system does not attempt NLP-based verb detection.
6. **Graceful degradation** — Commands work before the identity system is fully implemented, falling back to `.key` for character names.

---

## Why Not Evennia's `$pron()`/`$conj()`

Evennia's FuncParser system (`$pron()`, `$conj()`, `$You()`) sends a single template string to `msg_contents()` with `from_obj=actor`. The FuncParser resolves it for two audiences:

- **Actor** (`from_obj`): sees "You" and base-form verbs
- **Everyone else**: sees `actor.key` and conjugated verbs

This is a **binary model**. The identity system requires **N-way resolution** — each observer may know the actor by a different name based on their recognition memory. FuncParser resolves the actor's name from `.key`, bypassing `get_display_name(observer)` entirely. There is no hook to inject per-observer name resolution into FuncParser.

Additionally, the codebase has **zero existing uses** of `$pron()`, `$conj()`, or `$You()` in any `.py` file. Adopting FuncParser would require retrofitting all 234 `msg_contents()` calls — the same refactoring scope as a custom pipeline, but with the fundamental limitation of binary-only resolution.

Therefore, this spec defines a custom rendering pipeline that produces **one unique string per observer**, with full control over name resolution, pronoun transformation, and verb conjugation.

---

## Commands

### Dot-Pose (`.`)

First-person natural emoting with automatic perspective transformation.

**Syntax:**

```
.<verb> <text> [.verb] [text] ["speech"] [I .verb] [text]
```

**Command class:**

```python
class CmdDotPose(Command):
    key = "."
    locks = "cmd:all()"
    help_category = "Social"
```

**Examples:**

| Input | Actor Sees | Observer Who Knows Actor (male) | Observer Who Doesn't Know Actor |
|---|---|---|---|
| `.lean back.` | You lean back. | Jorge leans back. | A lanky man leans back. |
| `.scratch at the stubble on my jaw, "What day is it?" I .ask.` | You scratch at the stubble on your jaw, "What day is it?" you ask. | Jorge scratches at the stubble on his jaw, "What day is it?" he asks. | A lanky man scratches at the stubble on his jaw, "What day is it?" he asks. |
| `"Get down!" I .shout, .diving behind cover.` | "Get down!" you shout, diving behind cover. | "Get down!" Jorge shouts, diving behind cover. | "Get down!" a lanky man shouts, diving behind cover. |
| `.nod at Jorge` | You nod at Jorge. | Jorge nods at Maria. | A lanky man nods at a compact woman. |
| `"Hey," I .say, .waving my hand. "Over here!"` | "Hey," you say, waving your hand. "Over here!" | "Hey," Jorge says, waving his hand. "Over here!" | "Hey," a lanky man says, waving his hand. "Over here!" |
| `.fold my arms and .lean against the wall.` | You fold your arms and lean against the wall. | Jorge folds his arms and leans against the wall. | A lanky man folds his arms and leans against the wall. |

### Traditional Emote (`emote`)

Third-person emoting with identity-aware character references. The player writes in third person; the system prepends the actor's per-observer display name.

**Syntax:**

```
emote <third-person action text>
```

**Command class:**

```python
class CmdEmote(Command):
    key = "emote"
    aliases = [":", "pose"]
    locks = "cmd:all()"
    help_category = "Social"
```

**Examples:**

| Input | Actor Sees | Observer Who Knows Actor | Observer Who Doesn't |
|---|---|---|---|
| `emote leans back against the wall.` | Jorge leans back against the wall. | Jorge leans back against the wall. | A lanky man leans back against the wall. |
| `emote nods at Jorge.` | Jorge nods at Maria. | Jorge nods at Maria. | A lanky man nods at a compact woman. |

**Self-view for `emote`:** The actor sees their own `.key` (real name), NOT "You". The player wrote in third person — "You leans" would be broken grammar, and deconjugating verbs is fragile and error-prone. See Appendix C for the full architectural rationale.

**No verb or pronoun transformation** is performed for `emote`. The player is responsible for their own grammar. The only processing is character reference resolution and per-observer name rendering.

### Say (`say`)

Speech with per-observer speaker attribution.

**Syntax:**

```
say <message>
"<message>
```

**Command class:**

```python
class CmdSay(Command):
    key = "say"
    aliases = ['"']
    locks = "cmd:all()"
    help_category = "Social"
```

**Examples:**

| Input | Actor Sees | Observer Who Knows Speaker | Observer Who Doesn't |
|---|---|---|---|
| `say Hello there.` | You say, "Hello there." | Jorge says, "Hello there." | A lanky man says, "Hello there." |

Speech content passes through unchanged — no pronoun or verb transformation.

### Whisper (`whisper`)

Directed speech with per-observer attribution for both speaker and target. Three audiences receive different messages.

**Syntax:**

```
whisper <target> = <message>
```

**Command class:**

```python
class CmdWhisper(Command):
    key = "whisper"
    locks = "cmd:all()"
    help_category = "Social"
```

**Examples** (actor whispers to a character they know as "Jorge"):

| Audience | Sees |
|---|---|
| Actor | You whisper to Jorge, "Meet me later." |
| Target | A compact woman whispers to you, "Meet me later." |
| Room observer who knows both | Jorge whispers something to Maria. |
| Room observer who knows neither | A lanky man whispers something to a compact woman. |

**Visibility rule:** Room observers see that a whisper occurred and between whom, but NOT the speech content. Only the speaker and target receive the content.

---

## First-Person Pose Syntax

### Command Structure

The `.` command accepts two starting patterns:

- **Verb-first:** `.lean back` — the first word after `.` is the first verb
- **Speech-first:** `"Get down!" I .shout` — starts with quoted speech; the actor reference comes from a subsequent `I` pronoun

### Verb Markers

The `.` prefix marks a word as a verb requiring conjugation:

- **First verb:** Always the first word after the `.` command trigger (no additional `.` prefix needed on it)
- **Subsequent verbs:** Marked with `.` prefix anywhere in the text: `I .murmur`, `.diving behind cover`

**Disambiguation rule:** `.` followed by a letter (`[a-zA-Z]`) is a verb marker. `.` followed by whitespace, punctuation, end-of-string, or a digit is literal punctuation.

```
.lean back.                    → "lean" = verb, final "." = punctuation
.lean back, "Hello." I .say.   → "lean" = verb, "." inside quotes = speech,
                                  ".say" = verb, final "." = punctuation
.lean back...                  → "lean" = verb, "..." = punctuation
```

**Only mark words that need conjugation.** Participles like `taking` and `diving` don't change form between first and third person — they don't need markers. The system trusts the player's explicit markers. If a non-verb is marked (e.g., `.the`), it gets conjugated anyway ("thes") — that's the player's error.

### Pronoun Detection

First-person pronouns outside of quoted speech are detected and transformed:

| Pronoun | Case | Actor View | Observer (male) | Observer (female) | Observer (neutral) |
|---|---|---|---|---|---|
| I | subject | you | he | she | they |
| me | object | you | him | her | them |
| my | possessive adj. | your | his | her | their |
| mine | possessive pro. | yours | his | hers | theirs |
| myself | reflexive | yourself | himself | herself | themselves |

**Detection rules:**

- Case-insensitive matching: `I`, `My`, `my` all match
- Only matched **outside** quoted speech blocks
- **Word-boundary matching**: `"mine"` inside `"undermine"` does NOT match
- `I` is only matched as a standalone capital letter at a word boundary

### Speech Blocks

Text enclosed in double quotes (`"..."`) is treated as a speech block:

- **Never scanned** for pronouns, verb markers, or character references
- **Preserved verbatim** in the output for the speaker and for observers who share the language
- **Tokenized as distinct SPEECH tokens** with speaker metadata, enabling future language system processing (see Speech Token System)

Unmatched quotes (opening `"` with no closing `"`) treat the rest of the input as speech. Nested quotes are not supported — the parser matches the first `"` to the next `"`.

### Character References

Other characters mentioned in the emote are resolved using **bare name matching**:

1. Get all visible characters in the room (excluding the actor)
2. For each character, collect names the actor might use:
   - Assigned name from actor's recognition memory
   - Character's current sdesc (as perceived by the actor)
   - Character's `.key`
3. Sort candidates by string length, descending (longest match first)
4. Scan emote text (excluding quoted speech) for case-insensitive matches
5. Replace matches with character-reference tokens

**Only scanned outside quoted speech.** If your character says someone's name in dialogue, that's speech content, not a game-object reference.

**Ambiguity:** If multiple characters match the same string, the ordinal system applies: `2nd tall man` resolves to the second matching character (using the existing `get_search_query_replacement` ordinal system from `typeclasses/objects.py:41-76`).

**No match:** If a name doesn't match any room occupant, it's treated as plain text — not an error. This handles references to absent characters, objects, or abstract concepts naturally.

---

## Token Model

The parser converts input text into a stream of typed tokens. Each token type has defined rendering behavior that varies per observer.

### Token Types

```python
@dataclass
class TextToken:
    """Literal text passed through unchanged."""
    text: str

@dataclass
class VerbToken:
    """A marked verb requiring conjugation."""
    base_form: str          # "lean", "ask", "scratch"

@dataclass
class PronounToken:
    """A first-person pronoun requiring perspective transformation."""
    original: str           # "I", "my", "me", "mine", "myself"
    case: str               # "subject", "object", "possessive_adj",
                            # "possessive_pro", "reflexive"

@dataclass
class SpeechToken:
    """Quoted speech content, preserved as structured data."""
    text: str               # Content without enclosing quotes
    speaker: Character      # Who is speaking (usually the actor)
    language: str | None     # Language identifier (None = common/default)

@dataclass
class CharRefToken:
    """Reference to another character, resolved per-observer."""
    character: Character    # The resolved game object
    original_text: str      # What the actor typed ("Jorge", "the tall man")
```

### Parsing Pipeline

```
Input: .scratch at the stubble on my jaw, "What day is it?" I .ask.

Step 1 — Extract speech blocks:
  "What day is it?" → SpeechToken("What day is it?", actor, None)

Step 2 — Identify verb markers:
  First word "scratch" → VerbToken("scratch")
  ".ask" → VerbToken("ask")
  Final "." → literal punctuation (. + end-of-string)

Step 3 — Identify pronouns (outside speech):
  "my" → PronounToken("my", "possessive_adj")
  "I"  → PronounToken("I", "subject")

Step 4 — Identify character references (outside speech):
  (scan remaining text against room occupant names — none found here)

Step 5 — Everything else → TextToken

Result token stream:
  [VerbToken("scratch"),
   TextToken(" at the stubble on "),
   PronounToken("my", "possessive_adj"),
   TextToken(" jaw, "),
   SpeechToken("What day is it?", actor, None),
   TextToken(" "),
   PronounToken("I", "subject"),
   TextToken(" "),
   VerbToken("ask"),
   TextToken(".")]
```

### Speech-First Example

```
Input: "Get down!" I .shout, .diving behind cover.

Token stream:
  [SpeechToken("Get down!", actor, None),
   TextToken(" "),
   PronounToken("I", "subject"),
   TextToken(" "),
   VerbToken("shout"),
   TextToken(", "),
   VerbToken("diving"),
   TextToken(" behind cover.")]
```

The first actor reference comes from `PronounToken("I")`, not from an implicit verb-subject. The first-mention rule (see Per-Observer Rendering) applies: the first `I` resolves to the full display name.

### Multi-Speech Example

```
Input: "Hey," I .say, .waving my hand. "Over here!"

Token stream:
  [SpeechToken("Hey,", actor, None),
   TextToken(" "),
   PronounToken("I", "subject"),
   TextToken(" "),
   VerbToken("say"),
   TextToken(", "),
   VerbToken("waving"),
   TextToken(" "),
   PronounToken("my", "possessive_adj"),
   TextToken(" hand. "),
   SpeechToken("Over here!", actor, None)]
```

Multiple speech blocks are each tokenized independently. The language system hook (future) processes each speech token separately.

---

## Grammar Engine (`world/grammar.py`)

A standalone utility module with no Evennia dependencies in its core functions. Imported by the emote system, the identity system, and any future system that needs English grammar processing.

### Verb Conjugation

Converts base-form verbs to third-person singular present tense.

```python
def conjugate_third_person(verb: str) -> str:
    """Convert base-form verb to third-person singular present.

    Args:
        verb: Base form ("lean", "catch", "try").

    Returns:
        Conjugated form ("leans", "catches", "tries").
    """
```

**Irregular table** (checked first):

| Base Form | Third Person |
|---|---|
| be | is |
| have | has |

**Regular rules** (applied in order after irregular table check):

| # | Rule | Pattern | Example |
|---|---|---|---|
| 1 | Sibilant | Ends in -s, -sh, -ch, -x, -z | pass → passes, push → pushes, catch → catches, fix → fixes, buzz → buzzes |
| 2 | -O ending | Ends in -o | go → goes, do → does, echo → echoes |
| 3 | Consonant + Y | Ends in [consonant] + y | try → tries, carry → carries, fly → flies |
| 4 | Default | Everything else | lean → leans, run → runs, play → plays, say → says |

The function checks the irregular table first, then applies regular rules in order. Unknown words always receive regular treatment — the system never refuses to conjugate.

The irregular table is intentionally minimal. English third-person singular present tense is remarkably regular — only `be` and `have` are truly irregular for this conjugation. The table is easily extensible if edge cases emerge.

### Article Handling

Uses the `inflect` library for phoneme-aware article selection:

```python
import inflect

_engine = inflect.engine()

def get_article(noun_phrase: str, definite: bool = False) -> str:
    """Get the appropriate article for a noun phrase.

    Args:
        noun_phrase: The noun phrase ("lanky man", "athletic dame").
        definite: If True, return "the". If False, return "a"/"an".

    Returns:
        Article string: "a", "an", or "the".
    """
    if definite:
        return "the"
    result = _engine.a(noun_phrase)  # Returns "a lanky man" or "an athletic dame"
    return result.split(" ", 1)[0]   # Extract just the article
```

**Context rules** (applied by the rendering pipeline, not the grammar engine):

- **Indefinite** (default for sdescs): `"a lanky man"`, `"an athletic dame"`
- **Definite** (for targeting / repeated reference): `"the lanky man"`
- **None** (for assigned names and "You"): `"Jorge"` — no article

### Pronoun Transformation

```python
def transform_pronoun(
    pronoun: str,
    target_person: str,
    gender: str = "neutral",
) -> str:
    """Transform a first-person pronoun to the target perspective.

    Args:
        pronoun: First-person pronoun ("I", "me", "my", "mine", "myself").
        target_person: "second" (actor self-view) or "third" (observer view).
        gender: "male", "female", or "neutral". Only used for third person.

    Returns:
        Transformed pronoun string.
    """
```

**Gender mapping** from character `sex` attribute:

```python
GENDER_MAP = {
    "male": "male",
    "female": "female",
    "ambiguous": "neutral",
    "neutral": "neutral",
    "nonbinary": "neutral",
    "other": "neutral",
}
```

See Appendix B for the complete transformation tables.

### Possessive and Objective Forms

For display names used by the identity system and emote rendering:

```python
def possessive(name: str) -> str:
    """Form the possessive of a name or noun phrase.

    Args:
        name: "Jorge", "a lanky man", "you".

    Returns:
        "Jorge's", "a lanky man's", "your".
    """
```

| Input | Output | Notes |
|---|---|---|
| `"Jorge"` | `"Jorge's"` | Standard possessive |
| `"a lanky man"` | `"a lanky man's"` | Sdesc possessive |
| `"you"` | `"your"` | Pronoun — lookup table |
| `"he"` | `"his"` | Pronoun — lookup table |
| `"she"` | `"her"` | Pronoun — lookup table |
| `"they"` | `"their"` | Pronoun — lookup table |

Pronoun possessives are handled by a lookup table. All other inputs receive `'s` appended.

### Subject-Verb Agreement

The conjugation function pairs with the subject reference:

| Subject | Verb Form | Example |
|---|---|---|
| "You" (actor self-view) | Base form | "You lean back." |
| Named character | Third-person singular | "Jorge leans back." |
| Sdesc (singular) | Third-person singular | "A lanky man leans back." |

The rendering pipeline handles this: if the observer is the actor, use the base form; otherwise, use `conjugate_third_person()`.

---

## Per-Observer Rendering Pipeline

### Rendering Algorithm

```python
def render_dot_pose(token_stream, actor, location, exclude=None):
    """Render a dot-pose emote for all observers in a room.

    Args:
        token_stream: List of parsed tokens.
        actor: Character performing the emote.
        location: Room to broadcast in.
        exclude: Characters to exclude from receiving the message.
    """
    for observer in location.contents_get(exclude=exclude):
        if not hasattr(observer, "msg"):
            continue
        rendered = render_for_observer(token_stream, actor, observer)
        observer.msg(rendered)
```

### Actor Self-View

When `observer == actor`:

| Token Type | Rendering |
|---|---|
| TextToken | Unchanged |
| VerbToken | Base form (no conjugation): "lean", "ask" |
| PronounToken | Second-person form: I→you, my→your, me→you, mine→yours, myself→yourself |
| SpeechToken | `process_speech(text, speaker, observer)` (default: verbatim in quotes) |
| CharRefToken | `get_display_name(actor)` for the referenced character |

The actor's own reference (implicit from first verb, or explicit `I`) renders as **"You"** (capitalized if sentence-initial, lowercase otherwise).

### Observer View

When `observer != actor`:

| Token Type | Rendering |
|---|---|
| TextToken | Unchanged |
| VerbToken | `conjugate_third_person(base_form)`: lean→leans, ask→asks |
| PronounToken | Third-person, gender-matched: I→he/she/they, my→his/her/their |
| SpeechToken | `process_speech(text, speaker, observer)` |
| CharRefToken | `get_display_name(observer)` for the referenced character |

The actor's name renders as `get_display_name(observer)` — "Jorge", "a lanky man", etc.

### First-Mention vs. Subsequent-Mention

The actor may be referenced multiple times in a single emote. The renderer tracks whether the actor has been named:

**First reference** to the actor (implicit from first verb, or first `I` pronoun):

- Actor self-view: "You" (capitalized)
- Observer: Full display name via `get_display_name(observer)` — "Jorge" or "A lanky man"

**Subsequent references** to the actor (`I` pronoun tokens after the first reference):

- Actor self-view: "you" (lowercase)
- Observer: Gender-matched subject pronoun — "he", "she", "they"

**Possessive, objective, and reflexive pronouns** (`my`, `me`, `mine`, `myself`) are **always** rendered as pronouns regardless of first/subsequent position:

- Actor: "your", "you", "yours", "yourself"
- Observer: "his"/"her"/"their", "him"/"her"/"them", etc.

**Character references** (other characters in the emote) **always** render as full display names via `get_display_name(observer)`. No pronoun substitution for non-actor characters.

### Rendering Trace

Input: `.lean back and .sigh. "What a day," I .mutter.`

Token stream:

```
[VERB(lean), TEXT( back and ), VERB(sigh), TEXT(. ),
 SPEECH(What a day,), TEXT( ), PRONOUN_SUBJ(I), TEXT( ),
 VERB(mutter), TEXT(.)]
```

**Observer who knows actor as "Jorge" (male):**

```
actor_named = False

VERB(lean) → first verb, actor not yet named:
  prepend actor name: "Jorge" (actor_named = True)
  conjugate: "leans"
  → "Jorge leans"
TEXT( back and ) → " back and "
VERB(sigh) → conjugate: "sighs"
TEXT(. ) → ". "
SPEECH(What a day,) → '"What a day,"'
TEXT( ) → " "
PRONOUN_SUBJ(I) → actor_named is True → pronoun: "he"
TEXT( ) → " "
VERB(mutter) → conjugate: "mutters"
TEXT(.) → "."

Final: Jorge leans back and sighs. "What a day," he mutters.
```

**Actor self-view:**

```
actor_named = False

VERB(lean) → first verb, actor not yet named:
  use "You" (actor_named = True)
  base form: "lean"
  → "You lean"
TEXT( back and ) → " back and "
VERB(sigh) → base form: "sigh"
TEXT(. ) → ". "
SPEECH(What a day,) → '"What a day,"'
TEXT( ) → " "
PRONOUN_SUBJ(I) → actor_named is True → "you"
TEXT( ) → " "
VERB(mutter) → base form: "mutter"
TEXT(.) → "."

Final: You lean back and sigh. "What a day," you mutter.
```

### Capitalization and Punctuation

**Capitalization:**

The first character of the final rendered string is capitalized. Specific cases:

- Named actors: "Jorge leans back." — already capitalized
- Sdescs: "a lanky man leans back." → "A lanky man leans back." — article capitalized
- Self-view: "You lean back." — already capitalized
- Speech-first: `"Get down!" Jorge shouts.` — opening quote is first character; the letter inside is already capitalized

When a display name (sdesc with article) appears at the start of a clause after speech, the article is also capitalized: `"Get down!" A lanky man shouts.`

**Auto-punctuation:**

If the rendered emote doesn't end with terminal punctuation (`.`, `!`, `?`, `"`, or `)`), a period is appended automatically.

### Performance

Per-observer rendering produces N strings for N observers. For a room with 20 observers and an emote referencing 2 characters:

- 20 token stream traversals
- 20 x 2 = 40 `get_display_name` lookups (dict lookups in recognition memory)
- 20 string concatenations

This is trivial — microsecond-scale work per emote. The same performance profile as `msg_room_identity` from the identity spec.

---

## Identity System Integration

### Self-Perception Resolution

**Architectural decision:** `get_display_name(self)` returns the character's `.key` (their own real name), NOT "You".

This avoids breaking third-person sentence construction throughout the codebase. "You is standing here" or "You leans back against the wall" would occur anywhere `get_display_name(self)` is used in a third-person template.

Self-perception "You" is applied by the **rendering pipeline**, not by `get_display_name`:

- The **dot-pose** pipeline checks `if observer == actor` and uses "You" + second-person verb forms
- The **traditional emote** uses `get_display_name(self)` (returns `.key`) — third person throughout
- **System messages** that need "You" handle it explicitly with `if observer == actor` checks
- The existing `_process_description_variables()` system for `look` descriptions already handles self-perception separately from `get_display_name`

This resolves the open architectural concern from the identity spec (self-perception in `get_display_name`). See Appendix C for the full rationale. The identity spec's Self-Perception section should be updated to reflect this decision.

### Character Reference Resolution

When a player types a character name in an emote, the parser resolves it to a game object using the identity spec's targeting priority:

1. **Assigned names** — Check the actor's recognition memory for any room occupant whose assigned name matches
2. **Sdescs** — Match against visible characters' sdescs as perceived by the actor (partial, case-insensitive)
3. **Real keys** — Fall through to `.key` matching
4. **Ordinals** — `"2nd tall man"` uses the existing ordinal system

The resolved game object is stored in a `CharRefToken`. At render time, each observer sees that character via `get_display_name(observer)` — which may be completely different from what the actor typed.

### Disguise Interaction

If the actor is disguised (via `appear`), their display name changes per-observer as expected. The emote rendering pipeline doesn't need to know about disguise mechanics — it calls `get_display_name(observer)` and the identity system handles the rest.

Similarly, if a *referenced* character is disguised, observers who see through the disguise see the real identity while others see the disguised sdesc.

---

## Speech Token System

### Token Structure

```python
@dataclass
class SpeechToken:
    text: str                    # Speech content without enclosing quotes
    speaker: Character           # The character speaking (usually the actor)
    language: str | None = None  # Language identifier (None = common/default)
```

Speech tokens carry metadata about who is speaking and in what language. This enables future systems to process speech content per-observer without modifying the emote parser.

### Language System Hook

The rendering pipeline calls a pluggable speech processor:

```python
def process_speech(
    text: str,
    speaker: Character,
    observer: Character,
    language: str | None = None,
) -> str:
    """Process speech content for a specific observer.

    Default implementation returns text unchanged, wrapped in quotes.
    Future language system overrides this to apply comprehension
    filtering based on speaker's language and observer's skills.

    Args:
        text: Raw speech content.
        speaker: Character speaking.
        observer: Character hearing.
        language: Language identifier or None for common/default.

    Returns:
        Rendered speech string including quotes.
    """
    return f'"{text}"'
```

### Default Behavior

Until a language system is implemented, `process_speech` returns the text verbatim in quotes. The speech token infrastructure exists so that implementing languages later requires **zero changes to the emote parser** — only implementing the `process_speech` hook.

### Future Language System Interaction

When a language system is added:

- Speaker's `say` or dot-pose sets the `language` field on speech tokens based on the character's active language
- `process_speech` checks observer's language comprehension
- Full comprehension: verbatim text
- Partial comprehension: garbled/fragmented text
- No comprehension: generic description (e.g., `"[speaks in an unfamiliar language]"`)

This is out of scope for this spec but the data model is ready.

---

## Say Command Override

### Per-Observer Rendering

```python
def render_say(actor, message, location):
    """Render say command for all observers."""
    # Actor sees their own message
    actor.msg(f'You say, "{message}"')

    # Each observer sees per-observer speaker name
    for observer in location.contents_get(exclude=[actor]):
        if not hasattr(observer, "msg"):
            continue
        speaker_name = actor.get_display_name(observer)
        # Capitalize sdesc article if sentence-initial
        observer.msg(f'{capitalize_first(speaker_name)} says, "{message}"')
```

Speech content passes through unchanged for `say`. The only transformation is per-observer speaker attribution.

### Death Filter Compatibility

The existing death filter (`characters.py:137-205`) intercepts social messages to dead characters by checking message type metadata. Custom commands must pass compatible type information so the filter can intercept:

```python
observer.msg(text=rendered_message, type="say")
```

Implementation must verify compatibility with the existing filter pattern. If the filter checks `options={"type": "say"}` or inspects `from_obj`, the custom commands must provide equivalent metadata.

---

## Whisper Command Override

### Three-Audience Rendering

Whisper renders differently for three audiences:

| Audience | Template | Character References |
|---|---|---|
| Actor (speaker) | `You whisper to {target}, "{message}"` | Target = `get_display_name(actor)` |
| Target | `{actor} whispers to you, "{message}"` | Actor = `get_display_name(target)` |
| Room observers | `{actor} whispers something to {target}.` | Both = `get_display_name(observer)` |

Room observers do **not** see the message content.

### Target Resolution

The whisper target is resolved using the identity spec's targeting priority:

1. Assigned names from the actor's recognition memory
2. Sdescs of visible room occupants
3. Character `.key` values
4. Ordinals for ambiguous matches

If no target is found, the actor receives an error message. If multiple targets match without an ordinal, the actor is prompted to clarify.

### Death Filter Compatibility

Same consideration as `say` — pass `type="whisper"` metadata.

---

## Pre-Built Emote Templates

Optional convenience shortcuts for common social emotes. **Phase 5 polish** items.

### Template Format

```python
EMOTE_TEMPLATES = {
    "nod": {
        "solo": "{actor} nods.",
        "targeted": "{actor} nods at {target}.",
    },
    "shrug": {
        "solo": "{actor} shrugs.",
        "targeted": "{actor} shrugs at {target}.",
    },
    "laugh": {
        "solo": "{actor} laughs.",
        "targeted": "{actor} laughs at {target}.",
    },
    "sigh": {
        "solo": "{actor} sighs.",
    },
    "smile": {
        "solo": "{actor} smiles.",
        "targeted": "{actor} smiles at {target}.",
    },
    "wave": {
        "solo": "{actor} waves.",
        "targeted": "{actor} waves at {target}.",
    },
    "bow": {
        "solo": "{actor} bows.",
        "targeted": "{actor} bows respectfully to {target}.",
    },
    "frown": {
        "solo": "{actor} frowns.",
        "targeted": "{actor} frowns at {target}.",
    },
}
```

### Usage

```
nod             → "Jorge nods."          / "A lanky man nods."
nod jorge       → "Jorge nods at Maria." / "A lanky man nods at a compact woman."
shrug           → "Jorge shrugs."
```

Templates use `{actor}` and `{target}` placeholders resolved via `get_display_name(observer)`, following the same per-observer pattern as all other communication commands.

---

## Edge Cases

### Empty Input

`.` with no text after it: Display usage help message.

### Malformed Verb Markers

`.` followed by nothing at end of text: Treated as literal period (disambiguation rule: `.` + end-of-string = punctuation).

A `.` marker on a non-verb word (e.g., `.the`): The system conjugates it anyway ("thes"). The system trusts explicit markers — this is the player's error. Help text should be clear that only verbs should be marked.

### Missing Targets

Character reference text that matches no room occupant: Treated as plain text, not an error. The player may be referring to someone absent, an object, or an abstract concept.

### Ambiguous References

Multiple characters match the same name: The ordinal system applies (`2nd tall man`). If no ordinal and multiple matches, the first match is taken (consistent with Evennia's default search behavior).

### Self-Reference

Actor types their own name as a character reference in an emote: The system resolves it to the actor's character object. At render time, it renders via `get_display_name(observer)` for the actor object. For dot-pose self-view, this would produce the actor's own name (from `get_display_name(self)` returning `.key`). Technically valid but unusual.

### Combat Context

All communication commands work during combat. They have no mechanical effects and the combat handler does not interfere with social commands. Emotes, say, and whisper are pure roleplay actions that coexist with tactical combat.

### Auto-Punctuation Details

Terminal punctuation check examines the last non-whitespace character. If it is not `.`, `!`, `?`, `"`, or `)`, a period is appended. This prevents double-punctuation while ensuring clean sentence endings.

### Very Long Emotes

No explicit length limit imposed by the emote system. Server-side limits (Evennia's input length cap) apply naturally.

---

## Impact on Existing Systems

### Files Created

| File | Purpose |
|---|---|
| `world/grammar.py` | Grammar engine: conjugation, articles, pronouns |
| `commands/CmdCommunication.py` | Custom say, whisper, emote, dot-pose commands |

### Files Modified

| File | Change |
|---|---|
| `commands/default_cmdsets.py` | Add `CmdDotPose`, `CmdSay`, `CmdWhisper`, `CmdEmote` to `CharacterCmdSet` |
| `specs/IDENTITY_RECOGNITION_SPEC.md` | Update self-perception section; add cross-references to this spec |

### External Dependencies

| Package | Purpose | Used By |
|---|---|---|
| `inflect` | Phoneme-aware article selection (a/an) | `world/grammar.py` |

### Interaction with Identity Spec Phases

| Identity Phase | Emote System Behavior |
|---|---|
| Before Phase 1 | Commands work. All names fall back to `.key`. Grammar engine fully functional. |
| After Phase 1 | Full per-observer name resolution active. All commands identity-aware. |
| After Phase 2 | Target resolution uses assigned names and sdescs. Character references in emotes resolve via recognition memory. |

---

## Implementation Phases

### Phase 1 — Grammar Engine Foundation

**Scope:** Create `world/grammar.py` as a standalone module with no Evennia dependencies in its core functions.

**Deliverables:**

- `conjugate_third_person(verb)` — regular rules + irregular table
- `get_article(noun_phrase, definite)` — via `inflect`
- `transform_pronoun(pronoun, target_person, gender)` — lookup tables
- `possessive(name)` — for names, noun phrases, and pronouns
- `capitalize_first(text)` — capitalization helper

**Testing:** Pure unit tests, no Evennia dependency required. Run via `evennia test world.grammar` or standalone `python3 -m pytest`.

**Depends on:** Nothing. Can be implemented immediately, before the identity system.

### Phase 2 — Dot-Pose Command

**Scope:** Implement the `.` command with full first-person parsing and per-observer rendering.

**Deliverables:**

- `CmdDotPose` command class with `key = "."`
- Tokenizer: speech block extraction, verb marker detection, pronoun detection, character reference resolution
- Token dataclasses: `TextToken`, `VerbToken`, `PronounToken`, `SpeechToken`, `CharRefToken`
- `render_for_observer()` — per-observer token stream traversal with first-mention tracking
- `render_dot_pose()` — room broadcast loop
- `process_speech()` hook with default verbatim implementation

**Depends on:** Grammar Engine (Phase 1) + Identity Phase 1 (`get_display_name` override).

### Phase 3 — Traditional Emote Override

**Scope:** Override Evennia's default `emote` command with identity-aware rendering.

**Deliverables:**

- `CmdEmote` with `key = "emote"`, `aliases = [":", "pose"]`
- Character reference resolution (same bare name matching as dot-pose)
- Per-observer actor name prepending via `get_display_name(observer)`
- Speech block detection (character references inside quotes are not resolved)

**Depends on:** Grammar Engine (Phase 1) + Identity Phase 1.

### Phase 4 — Say/Whisper Overrides

**Scope:** Override Evennia's default `say` and `whisper` commands.

**Deliverables:**

- `CmdSay` with `key = "say"`, `aliases = ['"']` — per-observer speaker attribution
- `CmdWhisper` with `key = "whisper"` — three-audience rendering (speaker, target, observers)
- Target resolution for whisper using identity spec targeting priority
- Death filter compatibility verification

**Depends on:** Identity Phase 1.

### Phase 5 — Polish & Templates

**Scope:** Pre-built emote templates and integration with existing placement commands.

**Deliverables:**

- Pre-built emote template dictionary (nod, shrug, laugh, wave, etc.)
- Template command class with solo/targeted variants
- `@look_place` / `@temp_place` integration with pronoun-aware descriptions
- Comprehensive help text for all four commands
- Error messages and usage hints

**Depends on:** Phases 2-4.

---

## Testing Strategy

### Grammar Engine Unit Tests

```python
class TestVerbConjugation(TestCase):
    def test_regular_s(self):
        assert conjugate_third_person("lean") == "leans"
        assert conjugate_third_person("run") == "runs"

    def test_sibilant_es(self):
        assert conjugate_third_person("catch") == "catches"
        assert conjugate_third_person("push") == "pushes"
        assert conjugate_third_person("pass") == "passes"

    def test_o_ending(self):
        assert conjugate_third_person("go") == "goes"
        assert conjugate_third_person("do") == "does"

    def test_consonant_y(self):
        assert conjugate_third_person("try") == "tries"
        assert conjugate_third_person("carry") == "carries"

    def test_vowel_y(self):
        assert conjugate_third_person("play") == "plays"
        assert conjugate_third_person("say") == "says"

    def test_irregular(self):
        assert conjugate_third_person("be") == "is"
        assert conjugate_third_person("have") == "has"


class TestArticles(TestCase):
    def test_indefinite(self):
        assert get_article("lanky man") == "a"
        assert get_article("athletic dame") == "an"

    def test_definite(self):
        assert get_article("lanky man", definite=True) == "the"


class TestPronounTransformation(TestCase):
    def test_first_to_second(self):
        assert transform_pronoun("I", "second") == "you"
        assert transform_pronoun("my", "second") == "your"
        assert transform_pronoun("myself", "second") == "yourself"

    def test_first_to_third_male(self):
        assert transform_pronoun("I", "third", "male") == "he"
        assert transform_pronoun("my", "third", "male") == "his"
        assert transform_pronoun("myself", "third", "male") == "himself"

    def test_first_to_third_female(self):
        assert transform_pronoun("I", "third", "female") == "she"
        assert transform_pronoun("my", "third", "female") == "her"

    def test_first_to_third_neutral(self):
        assert transform_pronoun("I", "third", "neutral") == "they"
        assert transform_pronoun("my", "third", "neutral") == "their"
```

### Command Integration Tests

```python
class TestDotPose(EvenniaTest):
    def test_simple_pose(self):
        """'.lean back.' → Actor: 'You lean back.' Observer: 'X leans back.'"""

    def test_pose_with_speech(self):
        """Speech blocks preserved verbatim, pronouns transformed."""

    def test_speech_first_pose(self):
        """Emote starting with quoted speech uses I pronoun for actor ref."""

    def test_pose_with_character_reference(self):
        """Character names resolved per-observer."""

    def test_multiple_verbs(self):
        """Multiple .verb markers all conjugated correctly."""

    def test_multiple_speech_blocks(self):
        """Each speech block tokenized independently."""

    def test_first_mention_subsequent(self):
        """First I → display name, subsequent I → pronoun."""


class TestEmoteCommand(EvenniaTest):
    def test_per_observer_actor_name(self):
        """Actor name prepended per-observer."""

    def test_character_reference_in_emote(self):
        """Other character names resolved per-observer."""

    def test_speech_in_emote_not_scanned(self):
        """Character names inside quotes are not resolved."""


class TestSayCommand(EvenniaTest):
    def test_per_observer_attribution(self):
        """Each observer sees speaker by their recognized name."""


class TestWhisperCommand(EvenniaTest):
    def test_three_audience_rendering(self):
        """Speaker, target, and observers see different messages."""

    def test_content_privacy(self):
        """Room observers don't see whisper content."""

    def test_target_resolution(self):
        """Whisper target resolved via identity targeting priority."""
```

### Per-Observer Rendering Tests

Tests with 3+ observers having different recognition states:

- Observer A knows actor by assigned name "Jorge"
- Observer B doesn't know actor (sees sdesc "a lanky man")
- Observer C knows actor by a different assigned name "Jackie"
- Actor sees "You" + second-person forms

Each test verifies all four observers receive a unique, correct rendering.

---

## Appendix A: Verb Conjugation Rules Reference

### Irregular Table

| Base | Third Person |
|---|---|
| be | is |
| have | has |

### Regular Rules (Applied in Order)

```
1. IF verb ends in -s, -sh, -ch, -x, or -z:
     → append "es"
     pass → passes, push → pushes, catch → catches

2. IF verb ends in -o:
     → append "es"
     go → goes, do → does, echo → echoes

3. IF verb ends in [consonant] + y:
     → drop "y", append "ies"
     try → tries, carry → carries, fly → flies

4. ELSE:
     → append "s"
     lean → leans, run → runs, play → plays
```

**Vowels** for rule 3: a, e, i, o, u. All other letters are consonants.

**Extending the table:** If a verb produces an incorrect conjugation via the regular rules, add it to the irregular table. The table is checked first and takes absolute precedence.

---

## Appendix B: Pronoun Transformation Tables

### Table B.1 — First-Person to Second-Person (Actor Self-View)

| First Person | Second Person |
|---|---|
| I | you |
| me | you |
| my | your |
| mine | yours |
| myself | yourself |

### Table B.2 — First-Person to Third-Person (Observer View)

| First Person | Male | Female | Neutral |
|---|---|---|---|
| I | he | she | they |
| me | him | her | them |
| my | his | her | their |
| mine | his | hers | theirs |
| myself | himself | herself | themselves |

### Table B.3 — Gender Mapping

| Character `sex` Attribute | Gender Category |
|---|---|
| `"male"` | male |
| `"female"` | female |
| `"ambiguous"` | neutral |
| `"neutral"` | neutral |
| `"nonbinary"` | neutral |
| `"other"` | neutral |

---

## Appendix C: Architectural Decision — Self-Perception in `get_display_name`

### The Problem

The identity spec (lines 363-369) originally specified that `get_display_name(self)` returns `"You"`. This causes grammatical errors in any third-person context:

- Room description: "You is standing here." (should be "Jorge is standing here.")
- Traditional emote: "You leans back." (should be "Jorge leans back.")
- Combat message: "You attacks the bandit." (should be "Jorge attacks the bandit.")

The existing `_process_description_variables()` system for `look` descriptions already handles self-perception separately from `get_display_name`, so there's working precedent for this separation.

### The Resolution

`get_display_name(self)` returns `self.key` — the character's own real name. It is always safe to use in third-person sentence construction.

Self-perception "You" is handled by the **communication/rendering layer**:

| Context | Self-Perception Mechanism |
|---|---|
| Dot-pose (`.`) | Rendering pipeline checks `observer == actor`, uses "You" + base-form verbs |
| Traditional emote | Uses `get_display_name(self)` → `.key`. No "You" needed (player wrote 3rd person) |
| `say` / `whisper` | Hardcoded "You say" / "You whisper" template for actor |
| Room descriptions | `_process_description_variables()` handles self-view (existing system) |
| System messages | Explicit `if observer == actor` check in message templates |

### Impact on Identity Spec

The identity spec's Self-Perception section (lines 363-369) should be updated:

**Remove:**

```
get_display_name(self) → "You"
Possessive: "your"
Objective: "you"
Subject: "you"
```

**Replace with:**

```
get_display_name(self) → self.key (character's own real name)
Self-perception "You" is handled by the communication/rendering layer,
not by get_display_name. See EMOTE_POSE_SPEC.md Appendix C.
```

This ensures `get_display_name` is safe for use in any grammatical context without special-casing.
