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


def substitute_pronoun_tokens(text, *, gender, name="the corpse"):
    """Replace ``{pronoun}`` / ``{name}`` tokens in preserved prose.

    Always third-person (the subject is an inanimate corpse or severed
    part).  Unknown or ``None`` gender falls back to plural pronouns.

    Args:
        text (str): Longdesc prose, possibly containing brace tokens.
        gender (str | None): Preserved character gender (e.g. ``"male"``,
            ``"female"``, ``"neutral"``, ``"nonbinary"``, ``"other"``).
        name (str): Display name substituted for ``{name}`` /
            ``{name's}``.  Defaults to ``"the corpse"``.

    Returns:
        str: ``text`` with pronoun and name tokens resolved.  Tokens
        this helper does not recognise (e.g. ``{color}``) are left
        untouched for an upstream layer to handle.
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

    return processed
