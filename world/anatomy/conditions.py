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

``prepend_condition_to_desc`` is now a no-op: it returns the desc
untouched.  The ``condition`` argument is still
the upstream signal that selects which decay-tier prose to fetch
(via ``get_organ_default_description`` / ``get_severed_part_description``);
these helpers used to *also* mention it in player-facing prose,
which was the redundancy.

``prepend_condition_to_desc`` is kept as a no-op shim rather than
deleted because four configure-time call sites (Organ, Appendage corpse
/ living, SeveredHead) still call it.  Each can drop the call
independently; the helper API stays stable in the meantime.

``format_condition_tagline`` was kept on the same grounds and had NO
callers at all — only the package facade re-exporting it — so it has
been removed (#2822).
"""

from __future__ import annotations


def prepend_condition_to_desc(condition: str | None, desc: str | None) -> str:
    """Return ``desc`` untouched (kept as no-op shim).

    The condition is no longer surfaced as a separate sentence — the
    decay-tier prose carries the freshness signal alone.  The
    ``condition`` argument is preserved in the signature because
    callers pass it through other channels (organ name composition,
    key choice); only the prose-prepend behaviour is gone.
    """
    return desc or ""
