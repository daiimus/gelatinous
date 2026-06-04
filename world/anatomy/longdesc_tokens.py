"""Pronoun / name token substitution for preserved longdesc prose.

Players author body-part longdesc descriptions with brace-style tokens
(``{their}``, ``{they}``, ``{name}`` ...) that are rendered against the
*owner's* gender while they are alive.  When the body becomes a corpse
or a severed limb, the living-character renderer is no longer in play,
so the carried-forward prose must be substituted against *preserved*
character data instead.

This module is the single, pure source of that pronoun + name
substitution.  It is deliberately object-free (no Evennia imports) so
it is trivially unit-testable, and is consumed by both
:class:`typeclasses.corpse.Corpse` and
:class:`typeclasses.items.Appendage`.

Both consumers are inanimate (a corpse, a severed part), so substitution
is always third-person.  The corpse layer keeps its own ``{color}`` /
skintone handling and calls :func:`substitute_pronoun_tokens` for the
pronoun + name pass only.

Scope note: the *living*-character renderer
(:meth:`typeclasses.appearance_mixin.AppearanceMixin._process_description_variables`)
has its own pronoun logic that also handles the first-person ("you")
case.  Consolidating that path onto this helper is out of scope here.
"""

from __future__ import annotations

# Map a stored character gender onto a pronoun bucket.  Unknown / None
# genders collapse to ``plural`` ("they"/"their"), matching the corpse
# layer's historical fallback.
_GENDER_TO_BUCKET = {
    "male": "male",
    "female": "female",
    "neutral": "plural",
    "nonbinary": "plural",
    "other": "plural",
}

# Brace-token -> replacement, keyed by pronoun bucket.  Keys are the
# template names as authored inside braces (case-sensitive so authors
# control capitalisation: ``{Their}`` vs ``{their}``).
_PRONOUN_MAP = {
    "male": {
        "They": "He", "they": "he",
        "Their": "His", "their": "his",
        "Them": "Him", "them": "him",
        "Theirs": "His", "theirs": "his",
        "Themselves": "Himself", "themselves": "himself",
        "Themself": "Himself", "themself": "himself",
    },
    "female": {
        "They": "She", "they": "she",
        "Their": "Her", "their": "her",
        "Them": "Her", "them": "her",
        "Theirs": "Hers", "theirs": "hers",
        "Themselves": "Herself", "themselves": "herself",
        "Themself": "Herself", "themself": "herself",
    },
    "plural": {
        "They": "They", "they": "they",
        "Their": "Their", "their": "their",
        "Them": "Them", "them": "them",
        "Theirs": "Theirs", "theirs": "theirs",
        "Themselves": "Themselves", "themselves": "themselves",
        "Themself": "Themselves", "themself": "themselves",
    },
}


def substitute_pronoun_tokens(text, *, gender, name="the corpse",
                              number="singular", side=None):
    """Replace ``{pronoun}`` / ``{name}`` / body-noun tokens in preserved prose.

    Always third-person (the subject is an inanimate corpse or severed
    part).  Unknown or ``None`` gender falls back to plural pronouns.

    After pronoun + name substitution, a second pass resolves number-
    flexible body-noun tokens (``{eyes}`` / ``{ears}`` / ``{arms}`` ...)
    and braced verbs by delegating to ``world.grammar.flex_noun`` /
    ``flex_verb``.  This mirrors the living-character renderer's
    ``AppearanceMixin._substitute_longdesc_tokens`` so corpse and severed-
    part prose render the same as it would on the living body.  Tokens
    that match neither pronoun-table nor flex-vocabulary are left literal
    so an upstream layer (corpse skintone / ``{color}``) can still claim
    them.

    Side-aware singular flex (issue #341): when ``side`` is provided
    and a paired body-noun token flexes to singular, the side is
    prefixed — ``{arms}`` becomes ``"right arm"`` instead of bare
    ``"arm"``.

    Args:
        text (str): Longdesc prose, possibly containing brace tokens.
        gender (str | None): Preserved character gender (e.g. ``"male"``,
            ``"female"``, ``"neutral"``, ``"nonbinary"``, ``"other"``).
        name (str): Display name substituted for ``{name}`` /
            ``{name's}``.  Defaults to ``"the corpse"``.
        number (str): ``"singular"`` (default) or ``"plural"``.  Drives
            body-noun and verb flexing — ``"plural"`` for a collapsed
            symmetric pair (eyes/ears/...), ``"singular"`` for a lone
            side or a singular location (face/neck/...).
        side (str | None): ``"left"`` / ``"right"`` / ``None``. When
            set with ``number="singular"`` and the token is a pair-
            keyed body noun, the side is prefixed onto the singular
            form (#341).

    Returns:
        str: ``text`` with pronoun, name, and body-noun tokens resolved.
        Anything else (e.g. ``{color}``) is left untouched.
    """
    if not text:
        return text

    bucket = _GENDER_TO_BUCKET.get(gender, "plural")
    pronouns = _PRONOUN_MAP[bucket]

    processed = text
    for template, replacement in pronouns.items():
        token = f"{{{template}}}"
        if token in processed:
            processed = processed.replace(token, replacement)

    # Name tokens.  ``{name's}`` first so the bare ``{name}`` replace
    # below cannot strip the possessive token's leading "{name".
    processed = processed.replace("{name's}", f"{name}'s")
    processed = processed.replace("{name}", name)

    # Body-noun / verb flex pass.  Done after pronouns so an unhandled
    # leftover brace can fall through cleanly.
    processed = _flex_body_tokens(processed, number, side)

    return processed


def _flex_body_tokens(text, number, side=None):
    """Flex remaining braced tokens as body nouns or verbs.

    Mirrors the resolution order of
    ``AppearanceMixin._substitute_longdesc_tokens``: a braced single word
    (optionally with a leading ``a``/``an``) whose singular is in the
    flex-noun vocabulary renders as a noun; any other single-word brace
    renders as a verb.  Multi-word braces are left literal — that's the
    "unknown token" case authors use for emphasis or future substitutions.

    Side-aware singular flex (#341) for pair-keyed nouns is applied
    when ``side`` is provided AND number is singular.
    """
    import re

    from world.combat.constants import LONGDESC_FLEX_NOUNS, PAIR_MERGE_KEYS
    from world.grammar import (
        _match_leading_case,
        flex_noun,
        flex_verb,
        get_article,
        singularize_noun,
    )

    flex_nouns = set(LONGDESC_FLEX_NOUNS)
    pair_singulars = set()
    for left_loc, _right_loc in PAIR_MERGE_KEYS.values():
        # "left_eye" -> "eye"
        singular = left_loc.split("_", 1)[1]
        flex_nouns.add(singular)
        pair_singulars.add(singular)

    article_re = re.compile(r"^(?:a|an)\s+(.+)$", re.IGNORECASE)

    def _resolve(match):
        body = match.group(1)
        art_match = article_re.match(body)
        core = art_match.group(1) if art_match else body
        if " " in core:
            return match.group(0)
        core_base = singularize_noun(core).lower()
        if core_base in flex_nouns:
            # Side-aware singular for pair nouns (#341).
            if (number == "singular" and side
                    and core_base in pair_singulars):
                side_phrase = f"{side} {core_base}"
                if art_match:
                    article = get_article(side_phrase)
                    rendered = f"{article} {side_phrase}"
                else:
                    rendered = side_phrase
                return _match_leading_case(rendered, body)
            return flex_noun(body, number)
        if art_match is None:
            return flex_verb(body, number)
        return match.group(0)

    return re.sub(r"\{([^{}]+)\}", _resolve, text)
