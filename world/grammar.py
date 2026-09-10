"""
Grammar Engine

Shared infrastructure for English grammar processing: verb conjugation,
pronoun transformation, article handling, possessive formation, and
capitalization.

This is a standalone utility module with no Evennia dependencies in its
core functions. It is imported by the emote system, the identity system,
and any future system that needs English grammar processing.

See specs/GRAMMAR_ENGINE_SPEC.md for the full specification.
"""

from __future__ import annotations

import re
from functools import lru_cache

import inflect

# ---------------------------------------------------------------------------
# Inflect engine (singleton)
# ---------------------------------------------------------------------------

_engine = inflect.engine()

# ---------------------------------------------------------------------------
# Colour markup
# ---------------------------------------------------------------------------
#
# Almost everything this module is handed has already been coloured —
# item keys, sdescs, longdescs, combat lines. Markup is not text, and
# any rule that looks at "the first character" or "does it start with a
# vowel" has to see past it (#2207).
#
# Deliberately a local pattern rather than ``evennia.utils.ansi``: this
# module is documented as having no Evennia dependency in its core
# functions, and that is worth more than sharing one regex.
_ANSI_TOKEN = re.compile(
    r"\|\|"                                   # escaped literal pipe
    # hex truecolour, fg and bg — Evennia 6.1 renders |#rrggbb via
    # HexColors. Must precede the single-letter branch, which would
    # otherwise never see a '#' and leave 8 characters of markup
    # counted as visible text (#2805).
    r"|\|\[?#[0-9a-fA-F]{6}"
    r"|\|\[?(?:=[a-zA-Z]|[0-5]{3}|[a-zA-Z*/\-_^])"
)


def _visible(text: str) -> str:
    """*text* with colour markup removed — what a reader actually sees."""
    return _ANSI_TOKEN.sub("", text) if text else text

# ---------------------------------------------------------------------------
# Verb Conjugation
# ---------------------------------------------------------------------------

#: Closed table of irregular verb forms keyed by *any* recognised form.
#: Maps to ``(third_person_singular, plural_or_base)``. Lets a braced verb be
#: authored in either number and re-rendered to the needed one.
#:
#: This is the single source of truth for irregular verbs. ``flex_verb``
#: reads it directly and ``IRREGULAR_VERBS`` is derived from it, so the
#: two views cannot drift apart.
_IRREGULAR_VERB_FORMS: dict[str, tuple[str, str]] = {
    "is": ("is", "are"), "are": ("is", "are"), "be": ("is", "are"),
    "was": ("was", "were"), "were": ("was", "were"),
    "has": ("has", "have"), "have": ("has", "have"),
    "does": ("does", "do"), "do": ("does", "do"),
}

#: Irregular verbs for third-person singular present tense, checked before
#: the regular rules. Keyed by any recognised form rather than the base
#: alone, so an already-conjugated input ("is", "has") returns itself
#: instead of falling through to the sibilant rule as "ises" / "hases".
IRREGULAR_VERBS: dict[str, str] = {
    form: singular for form, (singular, _plural) in
    _IRREGULAR_VERB_FORMS.items()
}

#: Modal verbs, which never take an -s. Without this the default rule
#: below renders "could" as "coulds" and "can" as "cans" — and modals
#: are exactly what an author reaches for when the subject is a person
#: rather than a body part, so they arrive here often.
MODALS: frozenset[str] = frozenset((
    "could", "would", "should", "might", "must", "can", "will",
    "shall", "may", "ought", "need", "dare",
))

#: Irregular PAST-tense forms, which never take an -s: "she went",
#: "she said". English past tense is invariant across person and number,
#: so these need conjugating exactly as much as a modal does — which is
#: to say not at all.
#:
#: Regular past tense (`-ed`) was already safe; it is the irregular
#: forms that end in d, t and e and read like base verbs, so the append
#: rules claimed them: `went` -> `wents`, `said` -> `saids`, `took` ->
#: `tooks`, in front of every observer while the actor's own view stayed
#: correct (#2642).
#:
#: THE EXCLUSION RULE, which matters more than the list: a form is only
#: here if it is NOT also a present-tense verb. English has a pile of
#: invariant verbs whose past and present are spelled the same —
#: `set`, `put`, `cut`, `hit`, `let`, `cost`, `hurt`, `shut`, `spread`,
#: `read`, `bet`, `quit`, `shed` — and adding any of them would break
#: the ordinary present-tense pose (".set the glass down" wants "sets").
#: Same for forms that double as another verb's base: `saw` (to saw),
#: `lay` (to place), `bore` (to drill), `ground` (to grind), `wound`
#: (to injure), `founded`/`found`. When in doubt, leave it out: the
#: cost of omission is one mangled word, and the cost of a wrong
#: inclusion is every present-tense use of a common verb.
IRREGULAR_PAST: frozenset[str] = frozenset((
    # be / go / come / do
    "went", "came", "became", "did",
    # speech and thought
    "said", "told", "spoke", "swore", "thought", "knew", "meant",
    "understood", "taught",
    # motion
    "ran", "rose", "fell", "flew", "drove", "rode", "swam", "leapt",
    "crept", "fled", "slid", "strode", "trod", "sprang", "sank", "swung",
    "clung", "hung", "stood", "sat",
    # hands
    "took", "gave", "made", "held", "threw", "caught", "brought",
    "bought", "sold", "paid", "kept", "left", "lost", "sent",
    "spent", "built", "broke", "chose", "stole", "struck", "shook",
    "drew", "tore", "wore", "wove", "wrung", "dug", "flung", "bent",
    "lent", "bound",
    # body and sense
    "felt", "heard", "ate", "drank", "slept", "woke", "bled",
    "wept", "bit", "hid", "shone", "grew", "blew", "froze", "sang",
    "rang", "shot", "got", "forgot", "wrote", "met", "won", "began",
    "fought", "sought", "dealt", "fed", "led", "sped", "swept", "spun",
    "stuck", "stank", "shrank", "knelt", "spat", "forgave", "mistook",
))

#: Vowels used by the consonant-y rule.
_VOWELS = frozenset("aeiou")


def conjugate_third_person(verb: str) -> str:
    """Convert a base-form verb to third-person singular present tense.

    Applies the irregular table first, then four ordered regular rules:

    1. Sibilant endings (-s, -sh, -ch, -x, -z) → append "es"
    2. -O ending → append "es"
    3. Consonant + y → drop "y", append "ies"
    4. Default → append "s"

    An already-conjugated form is idempotent rather than doubled:
    "stands" returns "stands", not "standses". The emote renderer feeds
    this function verbs typed by players, and ``.stands back`` is an
    ordinary thing to type.

    Args:
        verb: Base form of the verb (e.g. "lean", "catch", "try"). An
            already-conjugated form is accepted and normalised.

    Returns:
        Conjugated third-person singular form (e.g. "leans", "catches",
        "tries").
    """
    # Same guard as `with_article`: `inflect` raises TypeCheckError on
    # an empty string where `pluralize_noun` returns "" cleanly, and
    # this function is fed verbs typed by players (#2643).
    if not verb:
        return verb
    lower = verb.lower()

    # A modal is already correct for every person and number.
    if lower in MODALS:
        return verb

    # Irregular table takes absolute precedence. Keyed by any form, so
    # "is" and "has" short-circuit here rather than reaching Rule 1.
    if lower in IRREGULAR_VERBS:
        conjugated = IRREGULAR_VERBS[lower]
        # Preserve original capitalisation pattern.
        if verb[0].isupper():
            return conjugated.capitalize()
        return conjugated

    # Normalise a third-person form back to its base before applying the
    # rules, so the sibilant rule cannot fire on an -s that is already a
    # conjugation. inflect leaves true base forms ("pass", "cross")
    # alone and reduces conjugated ones ("stands" → "stand").
    # PAST TENSE IS ALREADY CORRECT FOR EVERY PERSON. "she went", "she
    # said" — nothing to conjugate, exactly like a modal. The table
    # above holds nine forms, all of them be/do/have, so every other
    # irregular past came out with an -s stapled on: `went` -> `wents`,
    # `said` -> `saids`, `took` -> `tooks` (#2642).
    #
    # Regular past tense was already safe by accident — `-ed` normalises
    # or takes Rule 4 harmlessly at the render sites, and the LLM path
    # filters `endswith("ed")` explicitly. It is the irregular forms
    # that end in d, t and e and look like base verbs.
    if lower in IRREGULAR_PAST:
        return verb

    base = _engine.plural_verb(lower) or lower
    if base != lower:
        verb = _match_leading_case(base, verb)
        lower = base
        # RE-CONSULT THE TABLE. The docstring says it "takes absolute
        # precedence" and is "keyed by any form", and it was checked
        # only against the RAW input — so a form that normalises INTO a
        # table key still fell through to the append rules. `am` is the
        # one `be` form the table forgot; it normalises toward `are` and
        # then took Rule 4, giving `ares` (#2642).
        if lower in IRREGULAR_VERBS:
            conjugated = IRREGULAR_VERBS[lower]
            return (conjugated.capitalize() if verb[:1].isupper()
                    else conjugated)

    # Rule 1: Sibilant endings → +es
    if (
        lower.endswith("s")
        or lower.endswith("sh")
        or lower.endswith("ch")
        or lower.endswith("x")
        or lower.endswith("z")
    ):
        return verb + "es"

    # Rule 2: -O ending → +es
    if lower.endswith("o"):
        return verb + "es"

    # Rule 3: Consonant + y → drop y, add ies
    if lower.endswith("y") and len(lower) >= 2 and lower[-2] not in _VOWELS:
        return verb[:-1] + "ies"

    # Rule 4: Default → +s
    return verb + "s"


# ---------------------------------------------------------------------------
# Noun Pluralization
# ---------------------------------------------------------------------------


def conjugate_second_person(verb: str) -> str:
    """The form that follows "you" — the mirror of
    :func:`conjugate_third_person`.

    English second person takes the plural form, which is what
    `inflect`'s ``plural_verb`` gives: "leans" -> "lean", "is" -> "are",
    "has" -> "have", "was" -> "were".

    The actor's own pose line printed the typed verb VERBATIM while the
    observer line conjugated it, so `.leans on the bar` showed the
    player "You leans on the bar" and the room "…leans on the bar"
    (#3197). One side of the renderer had already decided that typing
    the `-s` form is ordinary — `conjugate_third_person`'s docstring
    says ".stands back is an ordinary thing to type" — and the other
    side never got the matching treatment.

    Modals and irregular past tense pass through, exactly as they do for
    the third person: "You could", "You went".

    KNOWN WART, stated so it is not rediscovered as a new defect:
    `inflect` normalises "focuses" to "focuse" rather than "focus". That
    is pre-existing — `conjugate_third_person` runs the same
    normalisation — but invisible there, because it re-appends an `s`
    and lands back on the right string. Here it would show. It fires
    only when a player types the `-es` form of a verb whose base ends in
    `s`; the base form itself is unaffected, and checked against 40
    candidate base forms nothing else is altered.
    """
    if not verb:
        return verb
    lower = verb.lower()
    if lower in MODALS or lower in IRREGULAR_PAST:
        return verb
    base = _engine.plural_verb(lower) or lower
    if base == lower:
        return verb
    return _match_leading_case(base, verb)


def pluralize_noun(noun: str) -> str:
    """Return the plural form of a singular noun.

    Thin wrapper over the ``inflect`` engine so callers do not reach into
    the singleton directly. Handles regular and irregular plurals
    ("hand" → "hands", "foot" → "feet", "eye" → "eyes") and preserves the
    leading capitalization of the input.

    Args:
        noun: A singular noun (a single word, e.g. "hand").

    Returns:
        The plural form, capitalized to match ``noun``'s first letter.
    """
    if not noun:
        return noun

    # Already plural? ``singular_noun`` is truthy only for plurals, and
    # without this "boots" became "bootss" and "glasses" "glassess"
    # (#2207). The pluralia-tantum list caught trousers and scissors and
    # nothing else.
    if _engine.singular_noun(noun):
        return noun

    plural = _engine.plural_noun(noun)
    # ``plural_noun`` can return False on unexpected input; fall back safely.
    if not plural:
        return noun

    if noun[0].isupper():
        return plural[0].upper() + plural[1:]
    return plural


def singularize_noun(noun: str) -> str:
    """Return the singular form of a (possibly already-singular) noun.

    Thin wrapper over the ``inflect`` engine. ``inflect.singular_noun``
    returns ``False`` for a noun that is already singular, so this helper
    normalises that to "return the input unchanged". Capitalization of the
    first letter is preserved ("Eyes" → "Eye", "feet" → "foot").

    Args:
        noun: A noun, singular or plural (a single word, e.g. "eyes").

    Returns:
        The singular form, capitalized to match ``noun``'s first letter.
    """
    if not noun:
        return noun

    singular = _engine.singular_noun(noun)
    # ``singular_noun`` returns False when the input is already singular.
    if not singular:
        return noun

    if noun[0].isupper():
        return singular[0].upper() + singular[1:]
    return singular


# ---------------------------------------------------------------------------
# Number-Flexing Tokens (paired-longdesc collapse)
# ---------------------------------------------------------------------------
#
# Authors write paired body-part prose in the plural and wrap the
# number-flexible words in ``{braces}``. The engine re-renders those braced
# words to match a render *number* — ``"plural"`` for a collapsed, both-sides
# pair; ``"singular"`` for a lone survivor or a single side. Number tokens are
# OPT-IN: untouched words render verbatim.
#
# Only words whose grammatical number tracks the body part itself should be
# braced (the part noun and any verb whose subject *is* that part). A main
# clause verb that agrees with the person-pronoun ("They have ...") is left
# un-braced — its agreement is a gender/pronoun concern, not a pair concern.

#: ``_IRREGULAR_VERB_FORMS`` (and the ``IRREGULAR_VERBS`` view derived
#: from it) live at the top of the module, with the conjugator.

#: Matches an indefinite article immediately leading a noun-token body, e.g.
#: ``"an eye"`` or ``"A eye"``. The article is dropped on a plural render and
#: re-agreed (a/an) on a singular render.
_ARTICLE_NOUN_RE = re.compile(r"^(a|an)\s+(.+)$", re.IGNORECASE)


def _match_leading_case(word: str, like: str) -> str:
    """Capitalise *word*'s first letter iff *like*'s first letter is upper."""
    if like[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


def flex_noun(body: str, number: str) -> str:
    """Render a noun token to the requested grammatical *number*.

    Input-form-agnostic: the noun may be authored singular or plural, with
    or without a leading indefinite article. On a plural render the article
    (if any) is dropped and the noun pluralised; on a singular render the
    noun is singularised and the article re-agreed (``a``/``an``).

    Args:
        body: The token body, e.g. ``"eye"``, ``"eyes"``, ``"an eye"``.
        number: ``"plural"`` or ``"singular"``.

    Returns:
        The flexed noun phrase, first-letter case matched to *body*.
    """
    match = _ARTICLE_NOUN_RE.match(body)
    article = match.group(1) if match else None
    word = match.group(2) if match else body

    singular = singularize_noun(word)

    if number == "plural":
        # Plural drops the indefinite article entirely.
        return _match_leading_case(pluralize_noun(singular), body)

    if article:
        agreed = get_article(singular)
        agreed = _match_leading_case(agreed, body)
        return f"{agreed} {singular}"
    return _match_leading_case(singular, body)


def flex_verb(word: str, number: str) -> str:
    """Render a verb token to agree with the requested *number*.

    Input-form-agnostic: ``{accents}`` and ``{accent}`` both work. A plural
    render yields the base/plural form ("accent", "are"); a singular render
    yields the third-person singular form ("accents", "is").

    Args:
        word: The single-word verb token body, e.g. ``"accents"``, ``"are"``.
        number: ``"plural"`` or ``"singular"``.

    Returns:
        The flexed verb, first-letter case matched to *word*.
    """
    lower = word.lower()

    # A modal has one form. Sending it through inflect's plural_verb
    # and back is at best a no-op and at worst "coulds".
    if lower in MODALS:
        return word

    if lower in _IRREGULAR_VERB_FORMS:
        singular_form, plural_form = _IRREGULAR_VERB_FORMS[lower]
        out = plural_form if number == "plural" else singular_form
        return _match_leading_case(out, word)

    # Regular verb: normalise to the base/plural form via inflect, then
    # conjugate back down for the singular render.
    base = _engine.plural_verb(lower) or lower
    if number == "plural":
        return _match_leading_case(base, word)
    return _match_leading_case(conjugate_third_person(base), word)


# ---------------------------------------------------------------------------
# Article Handling
# ---------------------------------------------------------------------------


def get_article(noun_phrase: str, definite: bool = False) -> str:
    """Get the appropriate article for a noun phrase.

    Uses the ``inflect`` library for phoneme-aware indefinite article
    selection (a / an).

    Args:
        noun_phrase: The noun phrase (e.g. "lanky man", "athletic dame").
        definite: If ``True``, return "the".  If ``False``, return
            "a" or "an" based on phonetics.

    Returns:
        Article string: ``"a"``, ``"an"``, or ``"the"``.
    """
    if definite:
        return "the"
    # markup is not a letter: "|555interior" must still take "an"
    return _indefinite_article(_visible(noun_phrase))


@lru_cache(maxsize=4096)
def _indefinite_article(noun_phrase: str) -> str:
    """Phoneme-aware "a"/"an" for ``noun_phrase``, memoized.

    ``inflect``'s ``a()`` was profiled at ~84µs per call — roughly a
    fifth of the per-observer display-name path — and the inputs are
    a small, hot set (sdescs and item short descriptions), so the
    cache pays for itself immediately (issue #462).
    """
    result = _engine.a(noun_phrase)  # e.g. "a lanky man" or "an athletic dame"
    return result.split(" ", 1)[0]   # Extract just the article


#: Pluralia-tantum nouns: English nouns that exist only (or idiomatically)
#: in plural form and therefore reject the indefinite article "a/an".
#: A bare noun phrase ("blue jeans") is grammatical; "*a blue jeans" is not.
#:
#: Categories:
#:   - True pluralia tantum garments (jeans, trousers, ...)
#:   - Paired-noun garments idiomatically referenced as plurals in sdescs
#:     (boots, gloves, ...)
#:   - Eyewear (glasses, goggles, ...)
#:   - Two-bladed/handled tools (scissors, pliers, ...)
_PLURALIA_TANTUM_NOUNS: frozenset[str] = frozenset({
    # garments (true pluralia tantum)
    "jeans", "pants", "trousers", "shorts", "briefs", "leggings",
    "tights", "overalls", "pyjamas", "pajamas", "knickers",
    "bloomers", "slacks", "chaps", "dungarees", "coveralls",
    # paired-noun garments
    "boots", "shoes", "gloves", "socks", "sneakers", "sandals",
    "slippers", "heels", "loafers", "moccasins", "mittens",
    "oxfords", "waders", "clogs", "cleats", "galoshes",
    # garment sets / uniforms
    "scrubs", "fatigues",
    # paired weapons
    "knuckles",
    # eyewear
    "glasses", "goggles", "spectacles", "binoculars",
    "sunglasses", "shades", "contacts", "mirrorshades",
    # tools
    "scissors", "pliers", "tweezers", "tongs", "shears", "clippers",
    # other
    "trunks",
})

#: Prepositions that introduce a non-head modifier in a noun phrase.
#: When detecting whether a noun phrase is pluralia tantum we only
#: inspect the head phrase preceding the first such break — so
#: ``"stocky droog in blue jeans"`` is judged on ``"stocky droog"``.
_PREP_BREAKS: tuple[str, ...] = (
    " in ", " with ", " wielding ", " wearing ", " holding ",
    # PARTITIVE. "pair of slippers" is a PAIR — singular — and without
    # this the head noun was read as "slippers", the phrase judged
    # pluralia tantum, and the article suppressed: the clinic slippers
    # announced themselves, were picked up and were worn with no
    # article at all (#2643). Every other partitive key in the game
    # ("a bowl of hand-pulled noodles", "pack of cigarettes") already
    # carries its own article and so never reached this decision, which
    # is why one item showed the defect and nothing else did.
    " of ",
)


def is_pluralia_tantum(noun_phrase: str) -> bool:
    """Return ``True`` if the head noun of *noun_phrase* is pluralia tantum.

    The head noun is the last token of the phrase preceding the first
    prepositional break (``" in "``, ``" with "``, etc.).  This means
    sdesc-style phrases such as ``"stocky droog in blue jeans"`` are
    judged on the wearer ("droog"), not on the garment ("jeans").

    Args:
        noun_phrase: A noun phrase such as ``"blue jeans"``,
            ``"Black Trenchcoat"``, or ``"stocky droog in blue jeans"``.

    Returns:
        ``True`` if the head noun is in :data:`_PLURALIA_TANTUM_NOUNS`,
        ``False`` otherwise.
    """
    # THROUGH `_visible`, like every other decision in this module. This
    # was the one that read the raw string, and `with_article` hands it
    # the raw key, so the same item answered differently depending on
    # whether it carried colour markup — `pair of slippers` came back
    # bare and `|wpair of slippers|n` came back with an article. That
    # made the partitive defect above look intermittent rather than
    # deterministic. `capitalize_first` and `get_article` were brought
    # onto `_visible` in #2207; this call site was not (#2643).
    lower = _visible(noun_phrase).strip().lower()

    # EARLIEST occurrence in the string, not the first entry in the
    # tuple. The docstring says "the first prepositional break" and the
    # loop tested `" in "` first wherever it sat, so a trailing
    # prepositional phrase cut the phrase at the wrong point: "stocky
    # droog wearing jeans in the alley" was cut after "wearing jeans",
    # the head noun read as "jeans", and the article deleted from the
    # DROOG (#2648).
    breaks = [i for i in (lower.find(prep) for prep in _PREP_BREAKS)
              if i >= 0]
    if breaks:
        lower = lower[:min(breaks)]

    tokens = lower.split()
    return bool(tokens) and tokens[-1] in _PLURALIA_TANTUM_NOUNS


def with_article(noun_phrase: str, definite: bool = False) -> str:
    """Return *noun_phrase* prefixed with the appropriate article.

    Pluralia-tantum nouns receive no indefinite article — ``"blue jeans"``
    is returned bare, never ``"*a blue jeans"``.  The definite article
    ``"the"`` is grammatical with both singular and plural nouns and is
    applied uniformly when *definite* is ``True``.

    Args:
        noun_phrase: A noun phrase to which an article should be
            prepended (e.g. ``"Black Trenchcoat"``, ``"blue jeans"``).
        definite: If ``True``, prepend ``"the"``.  If ``False``,
            prepend ``"a"``/``"an"`` for singular nouns and nothing for
            pluralia tantum.

    Returns:
        The noun phrase with its article (or bare, for indefinite
        pluralia tantum).
    """
    # Some item keys carry their own article — "a bowl of hand-pulled
    # noodles", "the free rail" — and prefixing another produced "a a
    # bowl of...". A phrase that already begins with an article keeps
    # the one it has.
    # `inflect` raises TypeCheckError on an empty string, where
    # `pluralize_noun` guards and returns "". This module takes strings
    # from item keys and player-adjacent text; one of its three entry
    # points guarding is not a policy (#2643).
    if not noun_phrase:
        return noun_phrase
    visible = _visible(noun_phrase)
    first = visible.strip().split(" ", 1)[0].lower() if visible else ""
    if first in ("a", "an", "the"):
        if definite and first != "the":
            rest = noun_phrase.strip().split(" ", 1)[1:]
            return "the " + (rest[0] if rest else "")
        return noun_phrase
    if definite:
        return f"the {noun_phrase}"
    if is_pluralia_tantum(noun_phrase):
        return noun_phrase
    return f"{get_article(noun_phrase)} {noun_phrase}"


# ---------------------------------------------------------------------------
# Pronoun Transformation
# ---------------------------------------------------------------------------

#: Maps character ``sex`` attribute values to grammar gender categories.
GENDER_MAP: dict[str, str] = {
    "male": "male",
    "female": "female",
    "ambiguous": "neutral",
    "neutral": "neutral",
    "nonbinary": "neutral",
    "other": "neutral",
}

#: Default sdesc keyword assigned to new characters based on grammar gender.
#: Used as a fallback when no keyword has been explicitly chosen via
#: ``describe keyword``.  Keyed by the grammar gender (output of ``GENDER_MAP``),
#: not the raw ``sex`` attribute.
DEFAULT_SDESC_KEYWORDS: dict[str, str] = {
    "male": "man",
    "female": "woman",
    "neutral": "person",
}

#: First-person → second-person pronoun table (actor self-view).
_FIRST_TO_SECOND: dict[str, str] = {
    "i": "you",
    "me": "you",
    "my": "your",
    "mine": "yours",
    "myself": "yourself",
}

#: First-person → third-person pronoun tables, keyed by gender.
_FIRST_TO_THIRD: dict[str, dict[str, str]] = {
    "male": {
        "i": "he",
        "me": "him",
        "my": "his",
        "mine": "his",
        "myself": "himself",
    },
    "female": {
        "i": "she",
        "me": "her",
        "my": "her",
        "mine": "hers",
        "myself": "herself",
    },
    "neutral": {
        "i": "they",
        "me": "them",
        "my": "their",
        "mine": "theirs",
        "myself": "themselves",
    },
}


def transform_pronoun(
    pronoun: str,
    target_person: str,
    gender: str = "neutral",
) -> str:
    """Transform a first-person pronoun to the target perspective.

    Args:
        pronoun: First-person pronoun ("I", "me", "my", "mine",
            "myself").  Case-insensitive.
        target_person: ``"second"`` for actor self-view or ``"third"``
            for observer view.
        gender: ``"male"``, ``"female"``, or ``"neutral"``.  Only used
            when *target_person* is ``"third"``.

    Returns:
        Transformed pronoun string (always lowercase).

    Raises:
        ValueError: If *target_person* is not ``"second"`` or
            ``"third"``.
    """
    key = pronoun.lower()

    if target_person == "second":
        return _FIRST_TO_SECOND.get(key, pronoun.lower())

    if target_person == "third":
        gender_table = _FIRST_TO_THIRD.get(gender, _FIRST_TO_THIRD["neutral"])
        return gender_table.get(key, pronoun.lower())

    raise ValueError(
        f"target_person must be 'second' or 'third', got {target_person!r}"
    )


# ---------------------------------------------------------------------------
# Possessive Forms
# ---------------------------------------------------------------------------

#: Pronoun possessive lookup table.  Keys are lowercase pronouns that
#: have irregular possessive forms (i.e. *not* formed by appending "'s").
_PRONOUN_POSSESSIVES: dict[str, str] = {
    "you": "your",
    "he": "his",
    "she": "her",
    "they": "their",
    "it": "its",
    "i": "my",
    "we": "our",
}


def possessive(name: str) -> str:
    """Form the possessive of a name or noun phrase.

    Pronouns are handled by a lookup table.  All other inputs receive
    ``'s`` appended.

    Args:
        name: A name, noun phrase, or pronoun (e.g. "Jorge",
            "a lanky man", "you", "he").

    Returns:
        Possessive form (e.g. "Jorge's", "a lanky man's", "your",
        "his").
    """
    lower = name.lower()
    if lower in _PRONOUN_POSSESSIVES:
        result = _PRONOUN_POSSESSIVES[lower]
        # Preserve capitalisation of first character.
        if name[0].isupper():
            return result.capitalize()
        return result
    return f"{name}'s"


# ---------------------------------------------------------------------------
# Capitalisation
# ---------------------------------------------------------------------------


def capitalize_first(text: str) -> str:
    """Capitalise the first alphabetic character of a string.

    Unlike ``str.capitalize()``, this preserves the case of all
    subsequent characters and handles leading non-alpha characters
    (e.g. opening quotes).

    Args:
        text: The string to capitalise (e.g. ``"a lanky man leans."``
            or ``'"Get down!" he shouts.'``).

    Returns:
        The string with its first alphabetic character uppercased.
        Returns *text* unchanged if it contains no alphabetic
        characters.
    """
    if not text:
        return text
    i = 0
    while i < len(text):
        # Skip colour markup: the "first alphabetic character" of
        # "|rblood" is the r of the colour code, and uppercasing it
        # changes red to bright red while leaving the word lowercase
        # (#2207). 84 callers, most of them handed coloured strings.
        token = _ANSI_TOKEN.match(text, i)
        if token:
            i = token.end()
            continue
        if text[i].isalpha():
            return text[:i] + text[i].upper() + text[i + 1:]
        i += 1
    return text


def placement_clause(raw_input: str) -> str:
    """Reduce a placement to the CLAUSE the room renderer expects.

    `Room.get_display_characters` supplies the verb itself --
    `f"{name} is {placement}"`, and `"{a} and {b} are {placement}"` for
    two -- so a placement is authored as "standing here.", never "is
    standing here."

    This is the single door onto that decision. It was the player
    command's private helper (`@temp_place`, which is why it also takes
    "me is ..." and quotes); the souls layer wrote placements without
    it and never noticed, because those writes landed on a row nothing
    rendered (#2465). Both callers come through here now.
    """
    if not raw_input:
        # the souls layer asks about posts that may declare nothing
        return raw_input
    text = raw_input.strip()

    # Remove outer quotes if present
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]

    # Handle "me is ..." / "me are ..." patterns
    if text.lower().startswith('me is '):
        text = text[6:].strip()
        # Remove inner quotes if present after "me is"
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
    elif text.lower().startswith('me are '):
        text = text[7:].strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]

    # Handle "is ..." / "are ..." patterns (without "me")
    elif text.lower().startswith('is '):
        text = text[3:].strip()
    elif text.lower().startswith('are '):
        text = text[4:].strip()

    # Clean up redundant "is"/"are" at the beginning
    # Handle cases like "me is \"is standing here\""
    if text.lower().startswith('is '):
        text = text[3:].strip()
    elif text.lower().startswith('are '):
        text = text[4:].strip()

    text = text.strip()

    # Terminate it. The renderer concatenates placements into a
    # paragraph, so a clause without a full stop runs into whoever is
    # described next: "... sleeves turned back A lithe woman in a black
    # mesh halter is ...". Every other placement in the game terminates;
    # the eight `post_work_place` fixtures do not, because they were
    # authored against a row that never rendered (#2913).
    #
    # This half of the rule used to live in `@temp_place` while the
    # copula strip above lived here -- one decision behind two doors,
    # which is what #2465 was about in the first place.
    if text and not text.endswith((".", "!", "?", '"', "'")):
        text += "."
    return text


def ordinal(number: int) -> str:
    """``3`` -> ``"3rd"``.

    The crane's radio voice and the container's own prose both wrote
    ``f"the {floor}th"`` unconditionally, so the two lowest floors on the
    Boiler Run mast announced themselves as *"the 2th"* and *"the 3th"*
    — including in the read-back that asks a caller to confirm a move
    with people standing in the car (#2472, #2446).

    Teens are the whole difficulty: 11, 12 and 13 take ``th`` despite
    ending in 1, 2 and 3, and 111/112/113 do too.
    """
    n = int(number)
    if 10 <= abs(n) % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(abs(n) % 10, "th")
    return f"{n}{suffix}"
