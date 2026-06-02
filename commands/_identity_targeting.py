"""
Identity-aware character target resolution for commands.

Centralises the two non-trivial targeting patterns that the
identity-recognition system imposes on commands:

1. **Same-room character lookup** with proper identity filtering and
   Builder-by-key fallback within the candidate scope.  Use
   :func:`resolve_character_target`.

2. **Cross-room scan** across an explicit list of rooms (typically a
   combat handler's ``managed_rooms``).  Use
   :func:`resolve_character_in_rooms`.

3. **Admin dual-path** — local identity match first, then a global
   key-based search as fallback so staff retain cross-room reach.  Use
   :func:`resolve_admin_target`.

This module is the canonical entry point referenced by
``specs/IDENTITY_RECOGNITION_SPEC.md`` §Command Authoring Rule.  New
commands SHOULD prefer these helpers over hand-rolled substring loops
or ``caller.search(name, location=..., candidates=...)`` patterns,
both of which bypass the identity filter (see
``typeclasses/characters.py:1201–1206``).

All helpers handle the magic ``me`` / ``self`` / ``myself`` tokens by
returning the caller directly when ``allow_self=True``; otherwise they
return ``None`` so the calling command can emit a cannot-target-self
message in its own voice.
"""

from __future__ import annotations

from typing import Iterable, Optional

from evennia.utils.utils import inherits_from  # noqa: F401  (kept for future)

from world.combat.constants import PERM_BUILDER
from world.search import identity_match_characters

_CHARACTER_PATH = "typeclasses.characters.Character"
_SELF_TOKENS = frozenset({"me", "self", "myself"})


def _is_character(obj) -> bool:
    """Duck-type check: anything exposing ``get_sdesc`` participates in
    the identity system and is treated as a character for targeting
    purposes.  Matches the convention used by ``world.search._has_identity``
    and keeps the helper compatible with both production typeclasses
    and the ``MagicMock(spec=Character)`` fixtures used by the test
    suite (where ``inherits_from`` cannot resolve a real MRO).
    """
    get_sdesc = getattr(obj, "get_sdesc", None)
    return callable(get_sdesc)


def _is_self_token(query: str) -> bool:
    return query.strip().lower() in _SELF_TOKENS


def _builder_key_matches(caller, query: str, candidates: Iterable) -> list:
    """Return characters in *candidates* whose ``.key`` or aliases
    substring-match *query*.

    Only intended as a Builder-tier fallback when the identity pipeline
    finds no matches.  Real-key matching for ordinary players would
    defeat the recognition system, so callers must gate this on a
    Builder permission check.
    """
    needle = query.strip().lower()
    matches: list = []
    for obj in candidates:
        if obj is caller:
            continue
        if not _is_character(obj):
            continue
        if needle in obj.key.lower():
            matches.append(obj)
            continue
        aliases = obj.aliases.all() if hasattr(obj.aliases, "all") else []
        if any(needle in alias.lower() for alias in aliases):
            matches.append(obj)
    return matches


def resolve_character_target(
    caller,
    query: str,
    candidates: Optional[Iterable] = None,
    *,
    allow_self: bool = False,
) -> Optional[object]:
    """Resolve a character target via the identity pipeline.

    Args:
        caller: The searching character.
        query: Raw player input (the target string).
        candidates: Iterable of objects to search.  Defaults to
            ``caller.location.contents`` when ``None``.
        allow_self: When ``True``, the magic tokens ``me`` / ``self``
            / ``myself`` resolve to *caller*; otherwise they yield
            ``None``.

    Returns:
        - A single character on a unique match.
        - ``None`` when no match is found, the query is empty, or
          (with ``allow_self=False``) the caller is the only match.
        - ``None`` on ambiguity (multiple matches) **after sending a
          disambiguation message to caller**.  Callers should treat
          ``None`` as "stop processing" and return immediately.

    The Builder-by-key fallback only fires when the identity pipeline
    returns no matches AND the caller has Builder+ permission.  This
    preserves staff ergonomics without exposing real keys to ordinary
    players.
    """
    if not query:
        return None

    stripped = query.strip()
    if not stripped:
        return None

    if _is_self_token(stripped):
        return caller if allow_self else None

    if candidates is None:
        location = caller.location
        candidates = list(location.contents) if location else []
    else:
        candidates = list(candidates)

    matches = identity_match_characters(caller, stripped, candidates)

    if not matches and caller.check_permstring(PERM_BUILDER):
        matches = _builder_key_matches(caller, stripped, candidates)

    if not matches:
        return None

    if len(matches) > 1:
        caller.msg(
            f"Multiple targets match '{stripped}'. Please be more specific."
        )
        return None

    return matches[0]


def resolve_character_in_rooms(
    caller,
    query: str,
    rooms: Iterable,
    *,
    allow_self: bool = False,
) -> Optional[object]:
    """Resolve a character target across an explicit list of rooms.

    Searches each room in order, returning the first room that yields
    a unique match.  Used by cross-room combat commands (advance,
    charge) that scan a handler's ``managed_rooms``.

    Args:
        caller: The searching character.
        query: Raw player input.
        rooms: Iterable of room objects to scan.  Order matters — the
            caller's own room should typically come first.
        allow_self: See :func:`resolve_character_target`.

    Returns:
        First unique character match across *rooms*, or ``None``.  On
        ambiguity within a room, sends the disambiguation message and
        returns ``None`` (does not fall through to subsequent rooms).
    """
    if not query:
        return None

    stripped = query.strip()
    if not stripped:
        return None

    if _is_self_token(stripped):
        return caller if allow_self else None

    is_builder = caller.check_permstring(PERM_BUILDER)

    for room in rooms:
        if not room:
            continue
        candidates = list(room.contents)
        matches = identity_match_characters(caller, stripped, candidates)
        if not matches and is_builder:
            matches = _builder_key_matches(caller, stripped, candidates)
        if not matches:
            continue
        if len(matches) > 1:
            caller.msg(
                f"Multiple targets match '{stripped}' in "
                f"{room.key}. Please be more specific."
            )
            return None
        return matches[0]

    return None


def resolve_admin_target(caller, query: str) -> Optional[object]:
    """Dual-path character resolution for admin commands.

    Phase 1: identity match in the caller's current room (so disguised
    or sdesc-referenced neighbours resolve naturally).

    Phase 2: global key search via :func:`evennia.search_object`,
    filtered to Character instances.  Provides cross-room reach for
    staff tooling (``@heal``, ``describe``, ``@testdeath``, etc.).

    Args:
        caller: The staff character issuing the command.
        query: Raw input string.

    Returns:
        First match, or ``None`` if nothing resolves.  On ambiguity in
        the global phase, sends a disambiguation message and returns
        ``None``.
    """
    if not query:
        return None

    stripped = query.strip()
    if not stripped:
        return None

    if _is_self_token(stripped):
        return caller

    # Phase 1: local identity match (includes Builder-by-key fallback).
    local = resolve_character_target(caller, stripped)
    if local is not None:
        return local

    # Phase 2: global key search.
    from evennia import search_object

    results = [obj for obj in search_object(stripped) if _is_character(obj)]

    if not results:
        return None

    if len(results) > 1:
        caller.msg(
            f"Multiple characters match '{stripped}' globally. "
            f"Please be more specific (e.g. use a dbref)."
        )
        return None

    return results[0]
