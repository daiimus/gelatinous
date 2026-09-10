"""
Identity-Aware Search Utilities

Pure utility functions for matching player input against the identity
system (assigned names, short descriptions, ordinals).  These are called
by the ``Character.search()`` override to resolve targets without
exposing real character keys to unrecognized observers.

Coordinate with the existing ordinal system in
``typeclasses.objects.ObjectParent.get_search_query_replacement``
which converts ``"2nd sword"`` → ``"sword-2"`` for Evennia's built-in
multi-match format.  The functions here handle ordinals for *identity*
matching only (characters matched by sdesc/assigned name); items and
exits still go through the default Evennia ordinal pipeline.

See specs/IDENTITY_RECOGNITION_SPEC.md §Target Resolution for the
full specification.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typeclasses.characters import Character

# =========================================================================
# Leading Article Stripping
# =========================================================================

#: Articles that may prefix a targeting string (e.g. "the tall man").
_ARTICLES = frozenset({"a", "an", "the"})


def strip_leading_article(query: str) -> str:
    """Strip a leading English article from a query string.

    Args:
        query: The raw targeting string, e.g. ``"the tall man"``.

    Returns:
        The query with a leading ``a``/``an``/``the`` removed, or the
        original string if no article is found.  Always stripped of
        surrounding whitespace.

    Examples:
        >>> strip_leading_article("the tall man")
        'tall man'
        >>> strip_leading_article("a lanky woman")
        'lanky woman'
        >>> strip_leading_article("knife")
        'knife'
    """
    query = query.strip()
    parts = query.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in _ARTICLES:
        return parts[1]
    return query


# =========================================================================
# Ordinal Parsing
# =========================================================================

#: Matches ``"2nd tall man"`` style ordinals at the start of a string.
_ORDINAL_REGEX = re.compile(
    r"^(?P<number>\d+)(?:st|nd|rd|th)\s+(?P<rest>.+)$", re.IGNORECASE
)

#: Matches Evennia-native ``"1.man"`` ordinal format.
_EVENNIA_ORDINAL_REGEX = re.compile(
    r"^(?P<number>\d+)\.(?P<rest>.+)$"
)

#: Word-based ordinals.
_ORDINAL_WORDS: dict[str, int] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
    "7th": 7, "8th": 8, "9th": 9, "10th": 10,
}


def parse_ordinal(query: str) -> tuple[int | None, str]:
    """Extract an optional ordinal prefix from a query string.

    Handles numeric (``"2nd tall man"``), word-based (``"second tall
    man"``), and Evennia-native (``"1.man"``) ordinals.

    This runs *before* identity matching.  The existing
    ``get_search_query_replacement`` on ``ObjectParent`` handles ordinals
    for the default Evennia search path (items/exits); this function
    handles ordinals within our identity matching pipeline so ordinals
    are not double-processed.

    Args:
        query: The targeting string, possibly starting with an ordinal.

    Returns:
        Tuple of ``(ordinal, base_query)``.  ``ordinal`` is ``None``
        when no ordinal was found; otherwise it is a 1-based int.
        ``base_query`` is the remainder of the string with the ordinal
        stripped.

    Examples:
        >>> parse_ordinal("2nd tall man")
        (2, 'tall man')
        >>> parse_ordinal("second tall man")
        (2, 'tall man')
        >>> parse_ordinal("1.man")
        (1, 'man')
        >>> parse_ordinal("tall man")
        (None, 'tall man')
    """
    query = query.strip()

    # Try numeric ordinal first: "2nd tall man"
    match = _ORDINAL_REGEX.match(query)
    if match:
        number = int(match.group("number"))
        if number > 0:
            return (number, match.group("rest").strip())

    # Try Evennia-native format: "1.man"
    match = _EVENNIA_ORDINAL_REGEX.match(query)
    if match:
        number = int(match.group("number"))
        if number > 0:
            return (number, match.group("rest").strip())

    # Try word ordinal: "second tall man"
    parts = query.split(None, 1)
    if len(parts) == 2:
        first_word = parts[0].lower()
        if first_word in _ORDINAL_WORDS:
            return (_ORDINAL_WORDS[first_word], parts[1].strip())

    return (None, query)


# =========================================================================
# Identity Matching Helpers
# =========================================================================

def _has_identity(obj: object) -> bool:
    """Check whether *obj* participates in the identity system.

    Uses duck typing (``get_sdesc`` method presence) to avoid importing
    the Character typeclass and risking circular imports.
    """
    return callable(getattr(obj, "get_sdesc", None))


def _match_assigned_name(
    searcher: "Character", target: object, query: str
) -> bool:
    """Return ``True`` if *searcher* has assigned a name to *target*
    that matches *query* (case-insensitive substring match).

    Args:
        searcher: The character doing the search.
        target: The potential match (must be identity-enabled).
        query: The normalized query string.

    Returns:
        ``True`` if the searcher's assigned name for *target*'s current
        Apparent UID matches *query*.
    """
    from world.identity import get_assigned_name

    assigned = get_assigned_name(searcher, target)
    if not assigned:
        return False

    return query.lower() in assigned.lower()


def _match_sdesc(target: object, query: str) -> bool:
    """Return ``True`` if *query* matches *target*'s sdesc.

    Matching rules:
    - Case-insensitive.
    - All query words must appear as complete words in the sdesc
      (word-boundary matching).  ``"man"`` matches ``"lanky man"``
      but NOT ``"woman"``.
    - Single-word queries also match the keyword attribute directly.
    - For NPC fallback sdescs (sdesc == key), the query is matched
      as a prefix of the key.

    Args:
        target: The potential match (must have ``get_sdesc``).
        query: The normalized query string.

    Returns:
        ``True`` if *query* matches.
    """
    sdesc = target.get_sdesc()
    if not sdesc:
        return False

    query_lower = query.lower()
    sdesc_lower = sdesc.lower()

    # NPC fallback (sdesc defaults to key): try prefix first — covers
    # "tom" → "Tom Hanks".  Fall through to the word-boundary check
    # below if prefix doesn't fire, so "rat" still matches a mob
    # whose key is "a scrawny ragged rat" (the leading article on
    # the key would otherwise defeat the prefix path).  Before this
    # fall-through the NPC-fallback path early-returned False on a
    # prefix miss, so identity-based commands like ``operate rat``
    # silently couldn't reach mobs whose sdesc/key starts with an
    # article — even though the body was clearly in the room.
    target_key = getattr(target, "key", "")
    if sdesc == target_key:
        if target_key.lower().startswith(query_lower):
            return True

    # Word-boundary match: every word in the query must appear as a
    # complete word in the sdesc.
    sdesc_words = sdesc_lower.split()
    query_words = query_lower.split()
    if query_words and all(qw in sdesc_words for qw in query_words):
        return True

    # Also try matching against just the keyword if set — the APPARENT
    # one (#2451). This read the raw `sdesc_keyword`, which `appear`
    # never touches: Viktor runs `appear woman`, presents as "brawny
    # woman in a black trenchcoat" with the word "droog" nowhere in
    # sight, and `look droog` still landed on him. Anyone who met him
    # undisguised could confirm the disguised figure was the same person
    # by trying his old keyword, with no pierce roll spent.
    #
    # Note this clause is DEAD WEIGHT when no override is active — the
    # real keyword is already a word of the sdesc, so the word-boundary
    # test above has matched. Its only live effect was the disguised
    # case, i.e. the one case it had to get right.
    from world.identity import apparent_axes
    keyword = apparent_axes(target)[2]
    if keyword and query_lower == keyword.lower():
        return True

    return False


# =========================================================================
# Main Matching API
# =========================================================================

def parse_target_query(query: str) -> tuple[int | None, str]:
    """Split a targeting string into ``(ordinal, base_query)``.

    Article FIRST, then ordinal. Both call sites used to do it the other
    way round, and in that order the first step cancels the second:
    `parse_ordinal("the 2nd man")` sees no LEADING ordinal, returns the
    string untouched, and the article strip then yields `"2nd man"` —
    matched against sdescs as a description, which no character has. So
    `look the 2nd man` found nothing, and `Character.search` fell
    through to the default Evennia search and produced a generic
    not-found for someone standing in front of the player (#2661).

    Writing "the" before a disambiguator is the natural phrasing, which
    made this the form players were most likely to reach for in exactly
    the situation ordinals exist to resolve.

    Both steps existed and both worked; only the order was wrong. They
    live in one function now so the two call sites cannot disagree about
    it again.

    Examples:
        >>> parse_target_query("2nd man")
        (2, 'man')
        >>> parse_target_query("the 2nd man")
        (2, 'man')
        >>> parse_target_query("a third woman")
        (3, 'woman')
        >>> parse_target_query("the tall man")
        (None, 'tall man')
    """
    return parse_ordinal(strip_leading_article(query))


def identity_match_characters(
    searcher: "Character",
    query: str,
    candidates: list[object],
) -> list[object]:
    """Find characters in *candidates* matching *query* via identity.

    Resolution order (per the spec):
      1. **Assigned names** in *searcher*'s recognition memory
      2. **Sdescs** — partial / substring / keyword match

    If an ordinal is present in the query (e.g. ``"2nd tall man"``),
    it is parsed and applied to the matched results: the Nth match is
    returned (or an empty list if there are fewer than N matches).

    Leading articles (a/an/the) are stripped before matching.

    Only candidates that participate in the identity system (i.e. have
    ``get_sdesc``) are considered.

    Args:
        searcher: The character performing the search.
        query: The player's raw targeting string.
        candidates: Objects to search among (typically room contents).

    Returns:
        List of matching identity-enabled objects, in RESOLUTION-PRIORITY
        order: every assigned-name match first, then every sdesc match,
        candidate order preserved *within* each group. Empty list if
        nothing matched.

        This line used to read "ordered as they appear in *candidates*",
        which contradicted the resolution order stated twelve lines above
        it and the code between them (#2820). The spec settles which half
        was wrong -- IDENTITY_RECOGNITION_SPEC, "Targeting Priority":
        assigned names are step 2, sdescs step 3, and ordinals step 4,
        applied to the result. So the buckets are the contract and this
        sentence was the error.

        WORTH KNOWING, because it is a real consequence rather than a
        bug: an ordinal therefore indexes the PRIORITY order, not the
        order the player can see. With two men present and one of them
        remembered by name, the remembered one is always ``1.man`` and
        the stranger always ``2.man``, whoever walked in first. Whether
        ordinals should index visible order instead is a design question
        against the spec, not a defect in this function.
    """
    if not query or not candidates:
        return []

    # Article, then ordinal — see `parse_target_query` (#2661).
    ordinal, base_query = parse_target_query(query)

    if not base_query:
        return []

    # Phase 1: assigned name matches
    assigned_matches: list[object] = []
    for obj in candidates:
        if not _has_identity(obj):
            continue
        if obj is searcher:
            continue
        if _match_assigned_name(searcher, obj, base_query):
            assigned_matches.append(obj)

    # Phase 2: sdesc matches (only add objects not already matched)
    sdesc_matches: list[object] = []
    assigned_set = set(id(o) for o in assigned_matches)
    for obj in candidates:
        if not _has_identity(obj):
            continue
        if obj is searcher:
            continue
        if id(obj) in assigned_set:
            continue
        if _match_sdesc(obj, base_query):
            sdesc_matches.append(obj)

    # Combine: assigned name matches first, then sdesc matches
    all_matches = assigned_matches + sdesc_matches

    # Apply ordinal
    if ordinal is not None:
        if ordinal <= len(all_matches):
            return [all_matches[ordinal - 1]]
        return []

    return all_matches


def held_by_others(looker, query: str) -> list:
    """Items in the HANDS of other characters in the room, matching *query*.

    `caller.search()` reaches your inventory, the room, and the people in it —
    but not what those people are holding, because that lives inside their
    contents. Showing somebody a photo by holding it up is a real interaction
    (owner, 2026-08-29) and it needs a target you can actually name.

    HANDS ONLY, deliberately. `character.hands` is what is on display; the
    rest of their contents is pockets, and a search that reached those would
    quietly turn `look` into a frisk.
    """
    out = []
    location = getattr(looker, "location", None)
    if location is None or not query:
        return out
    q = strip_leading_article(str(query).strip().lower())
    for other in (location.contents or []):
        if other is looker or not hasattr(other, "hands"):
            continue
        for held in (getattr(other, "hands", None) or {}).values():
            if held is None or held in out:
                continue
            names = [getattr(held, "key", "") or ""]
            names += list(getattr(held, "aliases", None).all()
                          if hasattr(getattr(held, "aliases", None), "all")
                          else [])
            if any(q in str(n).lower() for n in names if n):
                out.append(held)
    return out


def is_identity_match(
    searcher: "Character", target: object, query: str
) -> bool:
    """Check whether *target* matches *query* via identity for *searcher*.

    This is a convenience wrapper used to determine whether a character
    found by Evennia's default ``.key`` search should be allowed through
    or blocked.

    Args:
        searcher: The character performing the search.
        target: A character found by the default search.
        query: The player's raw targeting string.

    Returns:
        ``True`` if *target* is reachable via identity matching for
        *searcher*.
    """
    if not _has_identity(target):
        # Not an identity-enabled object — always allow (items, exits)
        return True

    _ordinal, base_query = parse_target_query(query)

    if not base_query:
        return False

    return (
        _match_assigned_name(searcher, target, base_query)
        or _match_sdesc(target, base_query)
    )
