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

import inflect

# ---------------------------------------------------------------------------
# Inflect engine (singleton)
# ---------------------------------------------------------------------------

_engine = inflect.engine()

# ---------------------------------------------------------------------------
# Verb Conjugation
# ---------------------------------------------------------------------------

#: Irregular verbs for third-person singular present tense.
#: Checked before regular rules. Intentionally minimal — English 3rd-person
#: singular is remarkably regular.  Extend this table if edge cases emerge.
IRREGULAR_VERBS: dict[str, str] = {
    "be": "is",
    "have": "has",
}

#: Vowels used by the consonant-y rule.
_VOWELS = frozenset("aeiou")


def conjugate_third_person(verb: str) -> str:
    """Convert a base-form verb to third-person singular present tense.

    Applies the irregular table first, then four ordered regular rules:

    1. Sibilant endings (-s, -sh, -ch, -x, -z) → append "es"
    2. -O ending → append "es"
    3. Consonant + y → drop "y", append "ies"
    4. Default → append "s"

    Args:
        verb: Base form of the verb (e.g. "lean", "catch", "try").

    Returns:
        Conjugated third-person singular form (e.g. "leans", "catches",
        "tries").
    """
    lower = verb.lower()

    # Irregular table takes absolute precedence.
    if lower in IRREGULAR_VERBS:
        conjugated = IRREGULAR_VERBS[lower]
        # Preserve original capitalisation pattern.
        if verb[0].isupper():
            return conjugated.capitalize()
        return conjugated

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

#: Closed table of irregular verb forms keyed by *any* recognised form.
#: Maps to ``(third_person_singular, plural_or_base)``. Lets a braced verb be
#: authored in either number and re-rendered to the needed one.
_IRREGULAR_VERB_FORMS: dict[str, tuple[str, str]] = {
    "is": ("is", "are"), "are": ("is", "are"), "be": ("is", "are"),
    "was": ("was", "were"), "were": ("was", "were"),
    "has": ("has", "have"), "have": ("has", "have"),
    "does": ("does", "do"), "do": ("does", "do"),
}

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
    lower = noun_phrase.strip().lower()
    for prep in _PREP_BREAKS:
        idx = lower.find(prep)
        if idx >= 0:
            lower = lower[:idx]
            break
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
#: ``@shortdesc``.  Keyed by the grammar gender (output of ``GENDER_MAP``),
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
    for i, char in enumerate(text):
        if char.isalpha():
            return text[:i] + char.upper() + text[i + 1:]
    return text
