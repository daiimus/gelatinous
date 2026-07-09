"""Fuzzy candidate matching — a deliberately NARROW, swappable facade.

One job: resolve a free-register phrase (an LLM tool argument — "take off
her mesh top (unzipped)", "a mug of rotgut", "pain killer") against a SMALL
list of real candidates (the worn wardrobe, the menu, the supply table) and
return the best match or nothing. Stdlib ``difflib`` inside; if its
word-order weakness ever bites in play, swap the internals here for
RapidFuzz (a derived-image dependency decision) without touching consumers.

Hard boundaries, by design:

* NEVER in the identity/recognition lattice — voice discernment, disguise
  piercing, and the radio mutter fragments are deliberately lossy opposed
  checks; no system may fuzzy-"repair" them.
* NEVER auto-resolving player commands — a typo must not fuzzy-target an
  ``attack``. Player-side search stays Evennia's exact/prefix/alias model.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Callable, Iterable, Optional


def _norm(text: Any) -> str:
    return " ".join(str(text).lower().split())


def score(query: Any, candidate: Any) -> float:
    """Similarity 0.0–1.0 between a free phrase and a candidate string.
    Exact = 1.0; containment either way = 0.95 ("rotgut" names "mug of
    rotgut"); otherwise the better of a character ratio and a sorted-token
    ratio (so word order costs little)."""
    q, c = _norm(query), _norm(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.95
    full = SequenceMatcher(None, q, c).ratio()
    tokens = SequenceMatcher(
        None, " ".join(sorted(q.split())), " ".join(sorted(c.split()))
    ).ratio()
    return max(full, tokens)


def best_match(query: Any, candidates: Iterable[Any], *,
               key: Optional[Callable[[Any], Any]] = None,
               floor: float = 0.6) -> Optional[tuple[Any, float]]:
    """The best-scoring candidate for *query*, as ``(candidate, score)``,
    or None when nothing clears *floor* — a below-floor guess is worse
    than honestly failing (the consumer keeps its own fallback). ``key``
    extracts the comparable string from a candidate object."""
    best, best_score = None, float(floor)
    for cand in candidates or ():
        text = key(cand) if key else cand
        s = score(query, text)
        if s >= best_score and (best is None or s > best_score):
            best, best_score = cand, s
    return (best, best_score) if best is not None else None
