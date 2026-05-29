"""Freshness-condition presentation helpers (issue #221).

Centralises the colour-coded tagline that surfaces an item's
freshness condition (``pristine`` / ``damaged`` / ``putrid`` /
``desiccated``) at the top of its ``look`` output.

Design notes
============

* **Single source of truth**: both :class:`typeclasses.items.Organ`
  and :class:`typeclasses.items.Appendage` consume this helper at
  ``configure_from_harvest`` / ``configure_from_sever`` time so the
  tagline travels in ``self.db.desc`` and the engine renderer slots
  it in naturally (AGENTS.md "populate ``db.desc`` the Evennia-
  standard way" contract; cf. PR #204).

* **Decoupled from key composition**: the condition word was removed
  from the item key in issue #212 (keys now carry species + decay
  tier).  This helper surfaces the condition information that the
  key intentionally dropped.

* **Defensive empty for unknown / refuse**: callers prepend the
  helper's output unconditionally; an empty string means "no
  tagline" and the engine renderer falls through to the prose
  alone.  ``refuse`` is the gameplay-internal condition for
  skeletal-stage harvest (refused at the command gate), so leaking
  the term would be a UX bug.
"""

from __future__ import annotations

#: Condition → ANSI-colour-coded capitalised tagline.  Used as a
#: blends-into-description prefix line in ``db.desc``.
_CONDITION_TAGLINES = {
    "pristine": "|gPristine.|n",
    "damaged": "|yDamaged.|n",
    "putrid": "|rPutrid.|n",
    "desiccated": "|RDesiccated.|n",
}


def format_condition_tagline(condition: str | None) -> str:
    """Return a coloured, capitalised tagline for the given condition.

    Args:
        condition: One of ``pristine`` / ``damaged`` / ``putrid`` /
            ``desiccated``.  ``None``, empty, ``refuse``, or any
            unregistered condition returns an empty string so callers
            can prepend the output unconditionally without leaking
            internal vocabulary.

    Returns:
        The coloured tagline (e.g. ``"|gPristine.|n"``) or ``""``.
    """
    if not condition:
        return ""
    return _CONDITION_TAGLINES.get(condition, "")


def prepend_condition_to_desc(condition: str | None, desc: str | None) -> str:
    """Compose a final ``db.desc`` value with a condition tagline prefix.

    Centralised so both :class:`typeclasses.items.Organ` and
    :class:`typeclasses.items.Appendage` produce identical formatting
    (single blank line between tagline and prose, no trailing
    whitespace).

    Args:
        condition: Freshness condition identifier.
        desc: The base prose description, typically from
            :func:`world.anatomy.organs.get_organ_default_description`
            or :func:`world.anatomy.severed_parts.get_severed_part_description`.
            May be empty / ``None`` when no prose is registered.

    Returns:
        ``"{tagline}\\n\\n{desc}"`` when both are present; ``tagline``
        alone when prose is empty; ``desc`` alone when the condition
        has no tagline; ``""`` when both are empty.
    """
    tagline = format_condition_tagline(condition)
    body = desc or ""
    if tagline and body:
        return f"{tagline}\n\n{body}"
    if tagline:
        return tagline
    return body
