# Grammar Engine Specification

## Overview

The Grammar Engine (`world/grammar.py`) is a standalone utility module providing
English grammar processing — verb conjugation, article handling, pronoun
transformation, possessive formation, and capitalization.

It has **no Evennia dependencies in its core functions**. It is imported
across the game: emote, speech, voice and radio, identity, clothing,
appearance and longdescs, combat, medical, stealth, shops, souls, rooms and
many commands.

This spec is the canonical reference for the engine. `CLOTHING_SYSTEM_SPEC.md`
and `EMOTE_POSE_SPEC.md` delegate grammar concerns here.
`IDENTITY_RECOGNITION_SPEC.md` does not: it names `EMOTE_POSE_SPEC.md` as "the
canonical grammar engine specification" (in its design principles and in its
grammar engine section) and sends readers there for the posing system, and
that section forwards back here.

---

## Colour Markup

Some strings handed to this module arrive already coloured — combat
lines and rendered description fragments carry Evennia markup (`|555`,
`|=lblack`, `|n`) *inside* the text.

**Names never do.** Item keys, sdescs, longdescs and descs are stored
plain by policy: colour belongs to the renderer, not the data, and a
coloured name would subvert the colour schema (owner ruling on #3423).
Measured 2026-09-15: 0 of 4,620 object keys, 0 sdesc/longdesc/desc
attributes and 0 prototype keys in the live world carry markup. So the
one branch here that only ever sees names — the self-articled definite
rewrite in `with_article`, which turns "a bowl of noodles" into "the
bowl of noodles" — is not colour-safe and does not need to be.

**Markup is not text.** Any rule that inspects "the first character" or
asks "does this begin with a vowel" must look past it (#2207):

| function | rule |
|---|---|
| `capitalize_first` | capitalises the first *visible* letter, markup untouched: `\|rblood` keeps its colour code (uppercasing it would turn red into bright red) and the word is capitalised |
| `get_article` / `with_article` | reads the visible text, so `\|555interior` gets `"an"` |
| `is_pluralia_tantum` | reads the visible text, so `\|wpair of slippers\|n` is judged the same as `pair of slippers` (#2643) |

`_visible()` strips markup for **decisions only** — the original string
is always what gets returned, so colour survives. The markup pattern also
covers hex truecolour `|#rrggbb` (#2805).

Deliberately a local pattern rather than `evennia.utils.ansi`: this
module is documented as having no Evennia dependency in its core
functions, and that contract is worth more than sharing one regex.

---

## Verb Conjugation

`conjugate_third_person(verb)` converts a base-form verb to third-person
singular present tense ("lean" → "leans", "catch" → "catches", "try" →
"tries").

**Irregular table** (checked after the modals):

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

Order: empty input is returned as is; modals are returned unchanged; then
the irregular table; then irregular past-tense forms (`IRREGULAR_PAST`:
went, said, took, stood, …) are returned unchanged, because past tense is the
same in every person; then the verb is normalised to its base with
`inflect.plural_verb`, and the irregular table is checked again (so `am`
gives `is`, not `ares`); then the regular rules in order. A past form belongs
in `IRREGULAR_PAST` only if it is not also a present-tense verb: `set`,
`put`, `read`, `saw`, `lay` and `ground` are left out on purpose (#2642).
Unknown words always receive regular treatment — the system never
refuses to conjugate.

**Conjugation is idempotent**: `conjugate_third_person("stands")` returns
`"stands"`, not `"standses"`. The documented input is the base form, but
the emote renderer passes the verb as the player typed it, so a typed `-s`
form must survive the round trip. Whether typing the `-s` form is ordinary
input or a mistake is not decided (see Subject-Verb Agreement).

The irregular table is intentionally minimal. English third-person singular
present tense is remarkably regular — only `be`, `have` and `do` are truly
irregular for this conjugation. The table is easily extensible if edge
cases emerge.

### Second person

`conjugate_second_person(verb)` gives the form that follows "you". It
normalises an `-s` form to the plural with `inflect.plural_verb` (`leans` →
`lean`, `is` → `are`, `has` → `have`, `was` → `were`). Empty input, modals
and irregular past tense pass through unchanged. Known wart: `focuses`
becomes `focuse` (recorded in #3197 so it is not rediscovered). The emote
renderer uses it for the actor's own line (whether it should is not decided,
see Subject-Verb Agreement).

---

## Noun Number

- `pluralize_noun(noun)` — singular → plural ("hand" → "hands", "foot" →
  "feet"). Returns the input unchanged when it is already plural ("boots"
  stays "boots", never "bootss") (#2207).
- `singularize_noun(noun)` — plural → singular ("eyes" → "eye", "feet" →
  "foot"). Returns the input unchanged when it is already singular.

Both wrap the `inflect` singleton and preserve leading capitalization. They
share one test for "already plural": `inflect.singular_noun` is asked in
lowercase, and its candidate counts only if `inflect.plural` turns it back
into the word. This round trip is needed because `inflect` reports `False`
for most singulars but also chops words that merely end in -s — "ass" →
"as", and "as" pluralizes to "a" — so without it "ass" would be left alone
as a plural and singularized to "as", which misses the longdesc vocabulary
and is conjugated as a verb (#2691). Note `inflect.plural_noun` mangles an
already-plural input (`"eyes"` → `"eyess"`), so number-flexing first
normalizes to the singular base.

---

## Number-Flexing Tokens

Consumed by the paired-longdesc collapse (see `LONGDESC_SYSTEM_SPEC.md`).
Authors write paired body-part prose in the plural and wrap the
number-flexible words in `{braces}`; the renderer re-renders those braced
words to a target **number** — `"plural"` for a collapsed both-sides pair,
`"singular"` for a lone survivor or single side. Tokens are opt-in: untouched
words render verbatim (the engine never rewrites un-braced prose).

- `flex_noun(body, number)` renders a noun token ("eye", "eyes", "an eye")
  to *number*, whatever form it is written in. On a plural render a leading
  indefinite article is dropped and the noun pluralised; on a singular render
  the noun is singularised and the article re-agreed (a/an). Leading case
  preserved.
- `flex_verb(word, number)` renders a verb token ("accents", "accent", "is",
  "are") to *number*. Plural → base/plural form ("accent", "are"); singular →
  third-person singular ("accents", "is"). Modals ("could", "can", …) are
  returned unchanged. Irregulars (be/have/do/was) use a closed bidirectional
  table; regulars normalise via `inflect.plural_verb` then re-conjugate.
  Leading case preserved.

**Noun-vs-verb autodetect (deterministic, closed-set rule)** — performed by
the caller (`AppearanceMixin._substitute_longdesc_tokens`), not by POS
tagging: a braced word is a **noun** iff its singular is in the flex-noun
vocabulary — the pair base nouns from the species's pair table (for humans
`eye`, `ear`, `arm`, `hand`, `thigh`, `shin`, `foot`) plus the species's
curated body-noun set (for humans `leg`, `shoulder`, `hip`, `knee`, …) —
optionally preceded by `a`/`an`. Any other braced **single** word is a
**verb**.

The vocabulary comes from the species registry —
`get_species_longdesc_flex_nouns` and `get_species_pair_keys` in
`world/anatomy/species.py`, called from `AppearanceMixin._flex_noun_vocabulary`
(#350/#356). `world.combat.constants.PAIR_MERGE_KEYS` and `LONGDESC_FLEX_NOUNS`
are derived views of the human table, kept for callers with no species
context.

**Multi-word tokens.** `{they <verb>}` is resolved: head `they` plus a verb
tail agrees with the **person's** number, not the body part's (the
`person_number` argument of `AppearanceMixin._substitute_longdesc_tokens`).
`{they are}` / `{they turn}` in the rat and synth longdescs rely on this
(`world/mob_flavor/longdescs_rat.py`). Any other multi-word token that is
neither an article+noun nor `{they <verb …>}` is left literal and logged.

**Side-aware singular.** With `side` set, a pair-keyed noun renders
`"right arm"`, and `{an arm}` becomes `"a right arm"`
(`AppearanceMixin._substitute_longdesc_tokens`, #341).

**Two implementations.** The corpse and severed-part renderer mirrors all of
this in `world/anatomy/longdesc_tokens.py` (`_flex_body_tokens`, with the
person-verb mirror in `_flex_person_verbs`), which adds a reserved-token set
`_UPSTREAM_TOKENS` (#2722) the living path lacks. A change to the rule has to
land in both.

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

`get_article` returns `"the"` when `definite` is True. Otherwise it strips
colour markup and takes `"a"` or `"an"` from `_indefinite_article`, which
asks `inflect`'s `a()` and caches up to 4,096 answers (#462). Examples:
`"lanky man"` → `"a"`, `"athletic dame"` → `"an"`.

**Context rules** (applied by callers, not the grammar engine):

- **Indefinite** (default for sdescs): `"a lanky man"`, `"an athletic dame"`
- **Definite** (for targeting / repeated reference): `"the lanky man"`
- **None** (for assigned names and "You"): `"Jorge"` — no article

### Pluralia tantum

Some English nouns exist only — or idiomatically, in sdesc context — in
plural form and reject the indefinite article: `"blue jeans"` is
grammatical, `"*a blue jeans"` is not. The engine maintains a curated
frozenset of such nouns, `_PLURALIA_TANTUM_NOUNS` in `world/grammar.py`
(50 entries across seven categories), and `is_pluralia_tantum(noun_phrase)`
returns True if the head noun of the phrase is in it. The category comment
above the frozenset in `world/grammar.py` lists only four of them.

**Categories covered:**

| Category | Examples |
|---|---|
| True pluralia tantum garments | jeans, pants, trousers, shorts, leggings, overalls |
| Paired-noun garments (idiomatic plural) | boots, shoes, gloves, socks, sneakers |
| Eyewear | glasses, goggles, sunglasses, binoculars |
| Two-bladed/handled tools | scissors, pliers, tweezers, tongs, shears, clippers |
| Garment sets / uniforms (#1212/#1213) | scrubs, fatigues |
| Paired weapons (#1212/#1213) | knuckles |
| Other | trunks |

**Head-noun rule.** Detection inspects only the *head* of the noun
phrase — the last token before the earliest prepositional break in the
phrase (`" in "`, `" with "`, `" wielding "`, `" wearing "`, `" holding "`,
`" of "`), read with colour markup stripped. `" of "` makes a partitive
singular: `"pair of slippers"` gets `"a"` (#2643). This means
sdesc-style phrases such as `"stocky droog in blue jeans"` are judged
on the wearer (`"droog"`), not the garment (`"jeans"`), so the wearer
still correctly receives `"a"`.

**Why not `inflect.singular_noun`?** The `inflect` library's plural
detection is unreliable for pluralia tantum: it returns `"jean"` for
`"jeans"`. An explicit curated set is the only correct approach.

### Article composition

`with_article(noun_phrase, definite=False)` returns the phrase prefixed with
its article. Pluralia-tantum nouns receive no indefinite article — "blue
jeans" is returned bare, never "*a blue jeans". The definite article "the"
is grammatical with both singular and plural nouns and is applied uniformly
when `definite` is True.

| Input | `definite=False` | `definite=True` |
|---|---|---|
| `"Black Trenchcoat"` | `"a Black Trenchcoat"` | `"the Black Trenchcoat"` |
| `"Orange Jumpsuit"` | `"an Orange Jumpsuit"` | `"the Orange Jumpsuit"` |
| `"blue jeans"` | `"blue jeans"` | `"the blue jeans"` |
| `"black leather combat boots"` | `"black leather combat boots"` | `"the black leather combat boots"` |
| `"stocky droog in blue jeans"` | `"a stocky droog in blue jeans"` | `"the stocky droog in blue jeans"` |
| `"a bowl of noodles"` | `"a bowl of noodles"` | `"the bowl of noodles"` |

A phrase that already begins with `a`, `an` or `the` keeps its own article;
with `definite=True` a leading `a`/`an` becomes `the`. Empty input is
returned as is.

---

## Pronoun Transformation

`transform_pronoun(pronoun, target_person, gender="neutral")` transforms a
first-person pronoun ("I", "me", "my", "mine", "myself") to the target
perspective: `target_person` is `"second"` (actor self-view) or `"third"`
(observer view). `gender` is `"male"`, `"female"` or `"neutral"`, and is used
only for third person.

**Gender mapping** (`GENDER_MAP`) from the character `sex` attribute:

| `sex` | grammar gender |
|---|---|
| `male` | `male` |
| `female` | `female` |
| `ambiguous` | `neutral` |
| `neutral` | `neutral` |
| `nonbinary` | `neutral` |
| `other` | `neutral` |

Output is always lowercase. In the third person an unknown gender uses the
neutral table. A word not in the table is returned lowercased. Any
`target_person` other than `"second"` or `"third"` raises `ValueError`.

See `EMOTE_POSE_SPEC.md` Appendix B for the complete transformation tables.

---

## Possessive Forms

For display names used by the identity system and emote rendering,
`possessive(name)` forms the possessive of a name or noun phrase:

| Input | Output | Notes |
|---|---|---|
| `"Jorge"` | `"Jorge's"` | Standard possessive |
| `"a lanky man"` | `"a lanky man's"` | Sdesc possessive |
| `"you"` | `"your"` | Pronoun — lookup table |
| `"he"` | `"his"` | Pronoun — lookup table |
| `"she"` | `"her"` | Pronoun — lookup table |
| `"they"` | `"their"` | Pronoun — lookup table |
| `"it"` | `"its"` | Pronoun — lookup table |
| `"I"` | `"My"` | Pronoun — lookup table |
| `"we"` | `"our"` | Pronoun — lookup table |

Pronoun possessives are handled by a lookup table, and a capital first
letter is kept (`"You"` → `"Your"`). All other inputs
receive `'s` appended.

---

## Subject-Verb Agreement

The conjugation function pairs with the subject reference:

| Subject | Verb Form | Example |
|---|---|---|
| "You" (actor self-view) | Base form | "You lean back." |
| Named character | Third-person singular | "Jorge leans back." |
| Sdesc (singular) | Third-person singular | "A lanky man leans back." |

In the emote renderer (`render_for_observer` in `world/emote.py`) the actor's
verb goes through `conjugate_second_person()` (`leans` → `lean`, `is` →
`are`; modals and irregular past pass straight through) and the observer's
through `conjugate_third_person()`. Both are skipped for `-ing` participles
(`_should_conjugate` in `world/emote.py`). This came in with #3197
(2026-09-10), on the reasoning that a player who types `.leans` reads "You
leans" while the room reads correctly.

**This reverses an owner ruling. OWNER DECISION NEEDED — treat neither half
as settled.** The same normalisation landed once before as `to_base_form`
(#2210, 2026-08-21) and was removed hours later by owner ruling — #2211
*"Revert #2210: I invented the input, then changed the engine to accept it"*,
#2212 *"Nobody types '.stands'"*. The ruling: `.` is first-person authoring,
so the verb a player types is always a base form; the third-person input was
invented by a probe and read back as a live bug; and normalising it makes
`.stands` and `.stand` render identically, erasing the signal that the author
reached for the wrong command. What the #2211/#2212 revert restored is: the
actor sees the verb exactly as typed, and everyone else sees it through
`conjugate_third_person()`. #3197 cites none of those three and reaches its
evidence the same way (typing `.leans` on a testbed).
`conjugate_second_person("stands")` is `"stand"`, so the collapse #2212
objected to is back. Which of the two the actor's view should do is not
decided (see Not decided).

---

## Capitalization

`capitalize_first(text)` capitalises the first alphabetic character of a
string. Unlike `str.capitalize()`, it preserves the case of all subsequent
characters and handles leading non-alpha characters (e.g. opening quotes).
Used by the emote pipeline for sentence-initial rendering.

---

## Placement Clause

`placement_clause(raw_input)` turns a placement into the clause the room
renderer expects (`Room.get_display_characters` supplies "is"/"are" itself).
It strips outer quotes and a leading `me is`, `me are`, `is` or `are`, and
ends the clause with a full stop when it has no terminal punctuation. Empty
input is returned as is. `@temp_place` (`commands/CmdCharacter.py`) and the
souls layer (`world/souls/jobs.py`) both go through it (#2465, #2913).

---

## Ordinals

`ordinal(number)`: `1` → `"1st"`, `2` → `"2nd"`, `3` → `"3rd"`, `11`–`13` →
`"11th"`–`"13th"`, `111` → `"111th"`. Used by the crane
(`typeclasses/crane.py`) and room prose (`typeclasses/rooms.py`) for floor
numbers (#2472).

---

## Default Sdesc Keywords

`DEFAULT_SDESC_KEYWORDS`:

| grammar gender | keyword |
|---|---|
| `male` | `man` |
| `female` | `woman` |
| `neutral` | `person` |

Used as the keyword when a character has none of its own (none set with
`describe keyword`, no override): looked up by grammar gender each time it
is needed, never stored on the character. Keyed by the
output of `GENDER_MAP`, not the raw `sex` attribute.

---

## Deliberately not built

### Per-item override (deferred)

A future enhancement could allow individual prototypes to override
pluralia-tantum classification via an item attribute (e.g. for an
ironic singular `"Pair O' Jeans"` artifact). This is **deferred** until
a real one-off case demands it; the centralized set is sufficient for
all current prototypes.

---

## Not decided

- **The actor's own verb.** Whether the actor's view should show the verb
  exactly as typed (the #2211/#2212 ruling) or normalise it through
  `conjugate_second_person` (#3197). OWNER DECISION NEEDED — see
  Subject-Verb Agreement.
- **A typed `-s` form.** Whether typing the `-s` form of a verb is ordinary
  input or a mistake (see Verb Conjugation and Subject-Verb Agreement).

---

## Testing

The core tests are in `world/tests/test_grammar.py` (plain `unittest`, no
Evennia): `evennia test world.tests.test_grammar`. Further grammar tests are
under `world/tests/`.

---

## Related documents

- `EMOTE_POSE_SPEC.md` — the emote/pose renderer that uses this engine;
  Appendix B holds the pronoun transformation tables. Its Appendix A
  conjugation table is a pre-extraction leftover; this document is canonical
  for conjugation.
- `IDENTITY_RECOGNITION_SPEC.md` — sdescs, names and recognition.
- `CLOTHING_SYSTEM_SPEC.md` — clothing descriptions.
- `LONGDESC_SYSTEM_SPEC.md` — the paired-longdesc collapse that consumes the
  number-flexing tokens.
