# Grammar Engine Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02; 131 tests.

## Overview

The Grammar Engine (`world/grammar.py`) is a standalone utility module providing
English grammar processing — verb conjugation, article handling, pronoun
transformation, possessive formation, and capitalization.

It has **no Evennia dependencies in its core functions**. It is imported by
the emote system, the identity system, the clothing system, the combat
system, and any future system that needs English grammar processing.

This spec is the canonical reference for the engine. The Emote/Pose,
Identity/Recognition, and Clothing specs all delegate grammar concerns here.

> **2026-09-11 — one of those three delegations does not exist.**
> `CLOTHING_SYSTEM_SPEC.md:29` and `EMOTE_POSE_SPEC.md:409` do point here, and
> `EMOTE_POSE_SPEC.md:1082` now names this document canonical and its own
> Appendix A/B a pre-extraction leftover. `IDENTITY_RECOGNITION_SPEC.md` never
> got the rewrite: it names **`EMOTE_POSE_SPEC.md`** as "the canonical grammar
> engine specification" three times (`:16`, `:508`, `:547`), so a reader
> following that spec is sent to a section that now forwards back here. The
> code side of the claim is sound — `world/grammar.py` is imported by
> `world/emote.py`, `world/identity.py` / `world/identity_utils.py`,
> `typeclasses/clothing_mixin.py` and eight `world/combat/*` modules.

---

## Colour Markup

Almost every string handed to this module has already been coloured —
item keys, sdescs, longdescs, combat lines carry Evennia markup
(`|555`, `|=lblack`, `|n`) *inside* the text.

**Markup is not text.** Any rule that inspects "the first character" or
asks "does this begin with a vowel" must look past it. Three functions
did not, and all three were wrong in production:

| function | was | now |
|---|---|---|
| `capitalize_first` | `\|rblood` → `\|Rblood` — uppercased the colour code, changing red to bright red, and left the word lowercase | capitalises the first *visible* letter, markup untouched |
| `get_article` / `with_article` | `\|555interior` → `"a interior"` | reads the visible text, so `"an"` |
| `pluralize_noun` | `boots` → `bootss` | already-plural nouns are returned unchanged |

`_visible()` strips markup for **decisions only** — the original string
is always what gets returned, so colour survives.

Deliberately a local pattern rather than `evennia.utils.ansi`: this
module is documented as having no Evennia dependency in its core
functions, and that contract is worth more than sharing one regex.

---

## Verb Conjugation

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

| Form | Third Person |
|---|---|
| be, is, are | is |
| was, were | was |
| have, has | has |
| do, does | does |

Keyed by *any* recognised form rather than the base alone, so an
already-conjugated input returns itself instead of falling through to
Rule 1 as "ises" or "hases". This table is derived from
`_IRREGULAR_VERB_FORMS`, the same table `flex_verb` reads, so the two
views cannot drift apart.

**Modals** (`could`, `would`, `should`, `might`, `must`, `can`, `will`,
`shall`, `may`, `ought`, `need`, `dare`) are returned unchanged — they
take no -s in any person.

**Regular rules** (applied in order after irregular table check):

| # | Rule | Pattern | Example |
|---|---|---|---|
| 1 | Sibilant | Ends in -s, -sh, -ch, -x, -z | pass → passes, push → pushes, catch → catches, fix → fixes, buzz → buzzes |
| 2 | -O ending | Ends in -o | go → goes, do → does, echo → echoes |
| 3 | Consonant + Y | Ends in [consonant] + y | try → tries, carry → carries, fly → flies |
| 4 | Default | Everything else | lean → leans, run → runs, play → plays, say → says |

The function checks modals, then the irregular table, then normalises an
already-conjugated form back to its base, then applies the regular rules
in order. Unknown words always receive regular treatment — the system never
refuses to conjugate.

**Conjugation is idempotent**: `conjugate_third_person("stands")` returns
`"stands"`, not `"standses"`. The documented input is the base form, but
the emote renderer passes verbs typed by players and `.stands back` is an
ordinary thing to type, so a conjugated form must survive the round trip.

The irregular table is intentionally minimal. English third-person singular
present tense is remarkably regular — only `be`, `have` and `do` are truly
irregular for this conjugation. The table is easily extensible if edge
cases emerge.

---

## Noun Number

```python
def pluralize_noun(noun: str) -> str:
    """Singular → plural ("hand" → "hands", "foot" → "feet")."""

def singularize_noun(noun: str) -> str:
    """Plural → singular ("eyes" → "eye", "feet" → "foot").

    Returns the input unchanged when it is already singular (``inflect``
    reports ``False``). First-letter capitalization is preserved.
    """
```

Both wrap the `inflect` singleton and preserve leading capitalization. Note
`inflect.plural_noun` mangles an already-plural input (`"eyes"` → `"eyess"`),
so number-flexing first normalizes to the singular base.

---

## Number-Flexing Tokens

Consumed by the paired-longdesc collapse (see `LONGDESC_SYSTEM_SPEC.md`).
Authors write paired body-part prose in the plural and wrap the
number-flexible words in `{braces}`; the renderer re-renders those braced
words to a target **number** — `"plural"` for a collapsed both-sides pair,
`"singular"` for a lone survivor or single side. Tokens are opt-in: untouched
words render verbatim (the engine never rewrites un-braced prose).

```python
def flex_noun(body: str, number: str) -> str:
    """Render a noun token ("eye", "eyes", "an eye") to *number*.

    Input-form-agnostic. On a plural render a leading indefinite article is
    dropped and the noun pluralised; on a singular render the noun is
    singularised and the article re-agreed (a/an). Leading case preserved.
    """

def flex_verb(word: str, number: str) -> str:
    """Render a verb token ("accents", "accent", "is", "are") to *number*.

    Plural → base/plural form ("accent", "are"); singular → third-person
    singular ("accents", "is"). Irregulars (be/have/do/was) use a closed
    bidirectional table; regulars normalise via ``inflect.plural_verb`` then
    re-conjugate. Leading case preserved.
    """
```

**Noun-vs-verb autodetect (deterministic, closed-set rule)** — performed by
the caller (`AppearanceMixin._substitute_longdesc_tokens`), not by POS
tagging: a braced word is a **noun** iff its singular is in the flex-noun
vocabulary — the pair base nouns (`eye`, `ear`, `arm`, `hand`, `thigh`,
`shin`, `foot`, derived from `world.combat.constants.PAIR_MERGE_KEYS`) plus the
curated `world.combat.constants.LONGDESC_FLEX_NOUNS` body-noun set (`leg`,
`shoulder`, `hip`, `knee`, …) — optionally preceded by `a`/`an`. Any other
braced **single** word is a **verb**. A multi-word token that is not an
article+noun is left literal and logged.

> **2026-09-11 — the vocabulary is species-derived, one multi-word token is
> resolved, and this rule has two doors.** The caller builds the set from the
> species registry — `get_species_longdesc_flex_nouns` and
> `get_species_pair_keys` (`typeclasses/appearance_mixin.py:950-979`,
> #350/#356); the two `world.combat.constants` names above are now derived
> legacy views of the human table, kept for callers with no species context
> (`world/combat/constants.py:82-115`). `{they <verb>}` is resolved rather than
> left literal: head `they` plus a verb tail agrees with the **person's**
> number, not the body part's (`appearance_mixin.py:1041-1054`, plumbed via
> `person_number` at `:982` and `:1249`), which is what `{they are}` /
> `{they turn}` in the shipped rat and synth longdescs rely on
> (`world/mob_flavor/longdescs_rat.py:43`). Other multi-word braces are still
> left literal and logged. Singular flex is also side-aware: with `side` set, a
> pair-keyed noun renders `"right arm"`, and `{an arm}` becomes
> `"a right arm"` (`appearance_mixin.py:1062-1073`, #341). The corpse and
> severed-part renderer mirrors all of this in a second implementation,
> `world/anatomy/longdesc_tokens.py:_flex_body_tokens` (`:200`, with the
> person-verb mirror at `:159-178`), which adds a reserved-token set
> `_UPSTREAM_TOKENS` (`:197`, #2722) the living path lacks — a change to the
> rule has to land in both.

**Scope** — only brace words whose grammatical number tracks the body part
(the part noun and verbs whose subject **is** that part). A main-clause verb
agreeing with the person-pronoun ("They have …") is a gender/pronoun concern,
not a pair concern, and is left un-braced.

---

## Article Handling

The engine exposes two article-related helpers:

- `get_article(noun_phrase, definite=False)` — returns just the article
  string (`"a"`, `"an"`, or `"the"`).
- `with_article(noun_phrase, definite=False)` — returns the noun phrase
  prefixed with its article, or bare for indefinite pluralia tantum.

`with_article` is the canonical helper for callers that want a complete
noun phrase. `get_article` remains for callers that need just the article
token.

### Phoneme-aware article selection

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
    result = _engine.a(noun_phrase)  # "a lanky man" or "an athletic dame"
    return result.split(" ", 1)[0]   # Extract just the article
```

**Context rules** (applied by callers, not the grammar engine):

- **Indefinite** (default for sdescs): `"a lanky man"`, `"an athletic dame"`
- **Definite** (for targeting / repeated reference): `"the lanky man"`
- **None** (for assigned names and "You"): `"Jorge"` — no article

### Pluralia tantum

Some English nouns exist only — or idiomatically, in sdesc context — in
plural form and reject the indefinite article: `"blue jeans"` is
grammatical, `"*a blue jeans"` is not. The engine maintains a curated
frozenset of such nouns and exposes a detector:

```python
def is_pluralia_tantum(noun_phrase: str) -> bool:
    """Return True if the head noun of *noun_phrase* is pluralia tantum."""
```

**Categories covered:**

| Category | Examples |
|---|---|
| True pluralia tantum garments | jeans, pants, trousers, shorts, leggings, overalls |
| Paired-noun garments (idiomatic plural) | boots, shoes, gloves, socks, sneakers |
| Eyewear | glasses, goggles, sunglasses, binoculars |
| Two-bladed/handled tools | scissors, pliers, tweezers, tongs, shears |
| Garment sets / uniforms | scrubs, fatigues |
| Paired weapons | knuckles |
| Other | trunks |

> **2026-09-11 —** this table has never been complete. `_PLURALIA_TANTUM_NOUNS`
> already carried an `# other` group (`trunks`) and `clippers` in the same
> commit that created this document, so those two rows document day-one
> behaviour rather than later drift; the *garment sets / uniforms* and *paired
> weapons* groups were added afterwards by #1212/#1213. The frozenset now holds
> 50 entries across seven categories (`world/grammar.py:488-508`), and the
> module's own category comment (`:482-487`) still lists only four.

**Head-noun rule.** Detection inspects only the *head* of the noun
phrase — the last token before the first prepositional break (`" in "`,
`" with "`, `" wielding "`, `" wearing "`, `" holding "`). This means
sdesc-style phrases such as `"stocky droog in blue jeans"` are judged
on the wearer (`"droog"`), not the garment (`"jeans"`), so the wearer
still correctly receives `"a"`.

**Why not `inflect.singular_noun`?** The `inflect` library's plural
detection is unreliable for pluralia tantum: it returns `"jean"` for
`"jeans"`. An explicit curated set is the only correct approach.

### Article composition

```python
def with_article(noun_phrase: str, definite: bool = False) -> str:
    """Return *noun_phrase* prefixed with the appropriate article.

    Pluralia-tantum nouns receive no indefinite article — "blue jeans"
    is returned bare, never "*a blue jeans". The definite article "the"
    is grammatical with both singular and plural nouns and is applied
    uniformly when *definite* is True.
    """
```

| Input | `definite=False` | `definite=True` |
|---|---|---|
| `"Black Trenchcoat"` | `"a Black Trenchcoat"` | `"the Black Trenchcoat"` |
| `"Orange Jumpsuit"` | `"an Orange Jumpsuit"` | `"the Orange Jumpsuit"` |
| `"blue jeans"` | `"blue jeans"` | `"the blue jeans"` |
| `"black leather combat boots"` | `"black leather combat boots"` | `"the black leather combat boots"` |
| `"stocky droog in blue jeans"` | `"a stocky droog in blue jeans"` | `"the stocky droog in blue jeans"` |

### Per-item override (deferred)

A future enhancement could allow individual prototypes to override
pluralia-tantum classification via an item attribute (e.g. for an
ironic singular `"Pair O' Jeans"` artifact). This is **deferred** until
a real one-off case demands it; the centralized set is sufficient for
all current prototypes.

---

## Pronoun Transformation

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

See `EMOTE_POSE_SPEC.md` Appendix B for the complete transformation tables.

---

## Possessive Forms

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

Pronoun possessives are handled by a lookup table. All other inputs
receive `'s` appended.

---

## Subject-Verb Agreement

The conjugation function pairs with the subject reference:

| Subject | Verb Form | Example |
|---|---|---|
| "You" (actor self-view) | Base form | "You lean back." |
| Named character | Third-person singular | "Jorge leans back." |
| Sdesc (singular) | Third-person singular | "A lanky man leans back." |

The rendering pipeline handles this: if the observer is the actor, use
the base form; otherwise, use `conjugate_third_person()`.

> **2026-09-11 — the code no longer does this, and the change reverses an
> owner ruling. OWNER DECISION NEEDED — treat neither half as settled.**
> The actor branch now runs the typed verb through `conjugate_second_person`
> (`world/emote.py:890` and `:908`; `world/grammar.py:243`), which normalises
> an `-s` form down to the plural/second-person form (`leans` → `lean`,
> `is` → `are`) and passes modals and irregular past straight through; both
> branches are gated by `_should_conjugate` (`world/emote.py:205`) so `-ing`
> participles are untouched. It landed as #3197 (2026-09-10) on the reasoning
> that a player who types `.leans` reads "You leans" while the room reads
> correctly.
>
> **The same change already landed once and was reverted the same day.**
> `to_base_form` (#2210, 2026-08-21) did exactly this and was removed hours
> later by owner ruling — #2211 *"Revert #2210: I invented the input, then
> changed the engine to accept it"*, #2212 *"Nobody types '.stands'"*. The
> ruling: `.` is first-person authoring, so the verb a player types is always
> a base form; the third-person input was invented by a probe and read back as
> a live bug; and normalising it makes `.stands` and `.stand` render
> identically, erasing the signal that the author reached for the wrong
> command. #3197 cites none of those three and reaches its evidence the same
> way (typing `.leans` on a testbed). `conjugate_second_person("stands")` is
> `"stand"` today, so the collapse #2212 objected to is back.
>
> The sentence above is therefore what the last owner ruling **restored** —
> the spec and the code disagree and the code is the half that moved. Read it
> as: the spec states the ruled behaviour; the code currently conjugates. One
> accepted wart of the shipped path, recorded in #3197 so it is not
> rediscovered: `inflect` normalises `focuses` to `focuse`.

---

## Capitalization

```python
def capitalize_first(text: str) -> str:
    """Capitalise the first alphabetic character of a string."""
```

Unlike `str.capitalize()`, this preserves the case of all subsequent
characters and handles leading non-alpha characters (e.g. opening
quotes). Used by the emote pipeline for sentence-initial rendering.

---

## Default Sdesc Keywords

```python
DEFAULT_SDESC_KEYWORDS = {
    "male": "man",
    "female": "woman",
    "neutral": "person",
}
```

Fallback keyword assigned to new characters based on grammar gender,
when no explicit keyword has been chosen via `describe keyword`. Keyed by the
output of `GENDER_MAP`, not the raw `sex` attribute.

---

## Testing

All grammar functions are unit-tested in `world/tests/test_grammar.py`
with no Evennia dependencies. Run via:

```
evennia test world.tests.test_grammar
```

Test classes: `TestVerbConjugation`, `TestArticles`,
`TestIsPluraliaTantum`, `TestWithArticle`,
`TestPronounTransformation`, `TestPossessive`, `TestCapitalizeFirst`.
