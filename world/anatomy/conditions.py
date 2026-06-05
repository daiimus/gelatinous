"""Freshness-condition presentation helpers.

Originally (#221 / #223) prepended an explicit condition sentence
("It is a pristine specimen.") to every severed / harvested item's
``db.desc``, on the theory that the prose alone wouldn't convey
freshness.  In playtest the sentence read as overbearing — the
decay-tier prose (``pristine`` vs ``damaged`` vs ``putrid`` in
``ORGAN_DISPLAY`` / ``SEVERED_PART_DESCRIPTIONS``) was already
self-describing: "A glistening pinkish-grey mass..." vs "A dulled
brain, its folds slack...".  Prepending "It is a damaged specimen."
on top of "A dulled brain..." just doubled up the signal.

Both helpers are now no-ops: ``format_condition_tagline`` returns
the empty string for every condition, and ``prepend_condition_to_desc``
returns the desc untouched.  The ``condition`` argument is still
the upstream signal that selects which decay-tier prose to fetch
(via ``get_organ_default_description`` / ``get_severed_part_description``);
these helpers used to *also* mention it in player-facing prose,
which was the redundancy.

Kept as no-op shims rather than deleted because four configure-time
call sites (Organ, Appendage corpse / living, SeveredHead) still
import them.  Each can drop the call independently; the helper API
stays stable in the meantime.
"""

from __future__ import annotations


def format_condition_tagline(condition: str | None) -> str:
    """Return ``""`` for every condition (kept as no-op shim).

    Callers used to receive a sentence like ``"It is a pristine
    specimen."`` that they prepended to the item's prose.  The decay-
    tier prose is now the sole vehicle for communicating freshness.
    """
    return ""


def prepend_condition_to_desc(condition: str | None, desc: str | None) -> str:
    """Return ``desc`` untouched (kept as no-op shim).

    The condition is no longer surfaced as a separate sentence — the
    decay-tier prose carries the freshness signal alone.  The
    ``condition`` argument is preserved in the signature because
    callers pass it through other channels (organ name composition,
    key choice); only the prose-prepend behaviour is gone.
    """
    return desc or ""
