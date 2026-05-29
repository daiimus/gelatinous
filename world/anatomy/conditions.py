"""Freshness-condition presentation helpers (issue #221, #223).

Centralises the condition sentence prepended to an item's
``db.desc`` so the ``look`` output explicitly conveys the freshness
state (``pristine`` / ``damaged`` / ``putrid`` / ``desiccated``).

Design notes
============

* **Single source of truth**: both :class:`typeclasses.items.Organ`
  and :class:`typeclasses.items.Appendage` consume this helper at
  ``configure_from_harvest`` / ``configure_from_sever`` time so the
  sentence travels in ``self.db.desc`` and the engine renderer slots
  it in naturally (AGENTS.md "populate ``db.desc`` the Evennia-
  standard way" contract; cf. PR #204).

* **Decoupled from key composition**: the condition word was removed
  from the item key in issue #212 (keys now carry species + decay
  tier).  This helper surfaces the condition information that the
  key intentionally dropped.

* **Plain sentence form** (issue #223): the original #221 cut used a
  colour-coded standalone tagline (``|gPristine.|n``) separated from
  the prose by a blank line.  In practice that read as two distinct
  blocks rather than one description.  The replacement is a single
  uniform sentence (``"It is a pristine specimen."``) joined to the
  prose with a single space (issue #225) so the whole description
  flows as one paragraph rather than two visible lines.

* **Defensive empty for unknown / refuse**: callers prepend the
  helper's output unconditionally; an empty string means "no
  sentence" and the engine renderer falls through to the prose
  alone.  ``refuse`` is the gameplay-internal condition for
  skeletal-stage harvest (refused at the command gate), so leaking
  the term would be a UX bug.
"""

from __future__ import annotations

#: Set of condition identifiers the helper recognises.  Any other
#: value (``None``, ``""``, ``"refuse"``, ``"phlegmatic"``, ...)
#: yields an empty sentence.  Kept as a frozenset rather than an
#: explicit per-condition mapping because the rendered sentence is
#: now purely formulaic — ``"It is a {condition} specimen."`` — so a
#: dict would just duplicate the keys.
_RECOGNISED_CONDITIONS = frozenset(
    {"pristine", "damaged", "putrid", "desiccated"}
)


def format_condition_tagline(condition: str | None) -> str:
    """Return a plain condition sentence for the given freshness state.

    Args:
        condition: One of ``pristine`` / ``damaged`` / ``putrid`` /
            ``desiccated``.  ``None``, empty, ``refuse``, or any
            unregistered condition returns an empty string so callers
            can prepend the output unconditionally without leaking
            internal vocabulary.

    Returns:
        The sentence (e.g. ``"It is a pristine specimen."``) or ``""``.
    """
    if not condition or condition not in _RECOGNISED_CONDITIONS:
        return ""
    return f"It is a {condition} specimen."


def prepend_condition_to_desc(condition: str | None, desc: str | None) -> str:
    """Compose a final ``db.desc`` value with a condition sentence prefix.

    Centralised so both :class:`typeclasses.items.Organ` and
    :class:`typeclasses.items.Appendage` produce identical formatting:
    sentence joined to the prose with a single space so the whole
    description renders as one continuous paragraph on a single line
    (issue #225 — the prior ``"\\n"`` join broke onto two visible
    lines, which read as two separate blocks).

    Args:
        condition: Freshness condition identifier.
        desc: The base prose description, typically from
            :func:`world.anatomy.organs.get_organ_default_description`
            or :func:`world.anatomy.severed_parts.get_severed_part_description`.
            May be empty / ``None`` when no prose is registered.

    Returns:
        ``"{sentence} {desc}"`` when both are present; ``sentence``
        alone when prose is empty; ``desc`` alone when the condition
        has no sentence; ``""`` when both are empty.
    """
    sentence = format_condition_tagline(condition)
    body = desc or ""
    if sentence and body:
        return f"{sentence} {body}"
    if sentence:
        return sentence
    return body
