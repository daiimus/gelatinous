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
        ``True`` if the searcher's assigned name for *target*'s sleeve
        matches *query*.
    """
    sleeve_uid = getattr(target, "sleeve_uid", None)
    if sleeve_uid is None:
        return False

    memory = getattr(searcher, "recognition_memory", None)
    if not memory or sleeve_uid not in memory:
        return False

    assigned = memory[sleeve_uid].get("assigned_name", "")
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

    # If sdesc is just the key (NPC fallback), allow prefix matching
    target_key = getattr(target, "key", "")
    if sdesc == target_key:
        return target_key.lower().startswith(query_lower)

    # Word-boundary match: every word in the query must appear as a
    # complete word in the sdesc.
    sdesc_words = sdesc_lower.split()
    query_words = query_lower.split()
    if query_words and all(qw in sdesc_words for qw in query_words):
        return True

    # Also try matching against just the keyword if set
    keyword = getattr(target, "sdesc_keyword", None)
    if keyword and query_lower == keyword.lower():
        return True

    return False


# =========================================================================
# Main Matching API
# =========================================================================

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
        List of matching identity-enabled objects, ordered as they
        appear in *candidates*.  Empty list if nothing matched.
    """
    if not query or not candidates:
        return []

    # Parse ordinal
    ordinal, base_query = parse_ordinal(query)

    # Strip leading article
    base_query = strip_leading_article(base_query)

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

    _ordinal, base_query = parse_ordinal(query)
    base_query = strip_leading_article(base_query)

    if not base_query:
        return False

    return (
        _match_assigned_name(searcher, target, base_query)
        or _match_sdesc(target, base_query)
    )
