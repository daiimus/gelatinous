"""
Longdesc Integration for Wound Descriptions

This module provides the hooks the appearance system uses to weave wound
descriptions into a character's longdesc. Two render paths share a single
summarizer so multi-wound output is concise and consistent:

- ``append_wounds_to_longdesc`` — for a body location that already has a
  longdesc string, appends the wound summary onto it.
- ``get_standalone_wound_description`` — for a location with wounds but no
  longdesc set, returns a standalone sentence.

Both delegate to ``_summarize_location_wounds``: a single wound renders via
the type/stage-specific ``get_wound_description``; two or more collapse into
one concise compound line rather than a concatenation of every wound.
"""

from .wound_descriptions import (
    get_character_wounds,
    get_wound_description,
    _format_wound_grammar,
)
from .constants import get_location_display_name, INJURY_SEVERITY_MAP


def append_wounds_to_longdesc(original_desc, character, location, looker=None):
    """
    Append a wound summary to an existing longdesc for a body location.

    Args:
        original_desc (str): Original longdesc for this location.
        character: Character object.
        location (str): Body location.
        looker: Character looking (reserved for future permission checks).

    Returns:
        str: Original description with the wound summary appended, or the
            original unchanged if there are no visible wounds here.
    """
    wounds = get_character_wounds(character)
    location_wounds = [w for w in wounds if w['location'] == location]
    if not location_wounds:
        return original_desc

    summary = _summarize_location_wounds(location_wounds, character)
    if not summary:
        return original_desc

    # Merge the summary as an additional clause on the existing description.
    # Strip the summary's own terminal period (preserving any trailing color
    # reset) so the combined sentence flows, then re-terminate.
    clean = summary
    has_reset = clean.endswith('|n')
    if clean.endswith('.|n'):
        clean = clean[:-3]
    elif clean.endswith('.'):
        clean = clean[:-1]

    if has_reset and not clean.endswith('|n'):
        return f"{original_desc} {clean}.|n"
    return f"{original_desc} {clean}."


def get_standalone_wound_description(character, location, looker=None):
    """
    Build a standalone wound sentence for a location with no longdesc set.

    Used by the appearance system for body locations the player never
    described but which carry visible wounds.

    Args:
        character: Character object.
        location (str): Body location.
        looker: Character looking (reserved for future permission checks).

    Returns:
        str: A formatted wound sentence, or "" if no visible wounds here.
    """
    wounds = get_character_wounds(character)
    location_wounds = [w for w in wounds if w['location'] == location]
    if not location_wounds:
        return ""
    return _summarize_location_wounds(location_wounds, character)


def _summarize_location_wounds(location_wounds, character=None):
    """
    Return a single formatted sentence describing all wounds at one location.

    One wound renders via the type/stage-specific ``get_wound_description``.
    Two or more collapse into one concise compound line (the worst wound plus
    a count of the rest) rather than a concatenation of every description.

    Args:
        location_wounds (list): Wound dicts, all for the same location.
        character: Character object (for skintone / species naming).

    Returns:
        str: Formatted wound sentence (capitalized, terminated), or "".
    """
    if not location_wounds:
        return ""

    prioritized = _prioritize_wounds_for_display(location_wounds)

    if len(prioritized) == 1:
        wound = prioritized[0]
        return get_wound_description(
            injury_type=wound['injury_type'],
            location=wound['location'],
            severity=wound['severity'],
            stage=wound['stage'],
            organ=wound.get('organ'),
            character=character,
        )

    return _compound_phrase(prioritized[0], len(prioritized) - 1, character)


def _compound_phrase(worst_wound, others_count, character=None):
    """
    Concise single-line summary for two or more wounds at one location.

    FUTURE (not implemented this pass): per-injury-type compound templates,
    mirroring the single-wound ``messages.<type>.WOUND_DESCRIPTIONS`` dicts.
    A later pass can look up ``messages.<worst_type>.COMPOUND_DESCRIPTIONS``,
    ``random.choice`` a variant, and fall back to ``messages.generic`` then to
    the generic phrasing below — exactly how ``get_wound_description`` resolves
    single wounds. The type message modules are intentionally left untouched
    until that feature lands.

    Args:
        worst_wound (dict): Highest-priority wound at this location.
        others_count (int): Number of additional wounds beyond the worst.
        character: Character object (for skintone / species naming).

    Returns:
        str: A formatted, single-sentence compound summary.
    """
    location_display = get_location_display_name(worst_wound['location'], character)
    others_phrase = "another wound" if others_count == 1 else "several other wounds"

    # No fresh/raw wound in the mix: render a calm, skintone-colored summary.
    if worst_wound['stage'] in ("treated", "healing", "scarred"):
        skintone_color = _skintone_color(character)
        phrase = (f"{skintone_color}multiple old wounds mark the "
                  f"{location_display}|n")
        return _format_wound_grammar(phrase)

    severity = INJURY_SEVERITY_MAP.get(
        worst_wound['severity'], worst_wound['severity'].lower()
    )
    injury_type = worst_wound['injury_type']
    type_word = "" if injury_type == "generic" else f"{injury_type} "
    phrase = (f"|Ra {severity} {type_word}wound and {others_phrase} "
              f"mark the {location_display}|n")
    return _format_wound_grammar(phrase)


def _skintone_color(character):
    """Return the character's skintone color code, or "" if unavailable."""
    if not character:
        return ""
    skintone = character.db.skintone
    if not skintone:
        return ""
    try:
        from world.combat.constants import SKINTONE_PALETTE
        return SKINTONE_PALETTE.get(skintone, "")
    except ImportError:
        return ""


def _prioritize_wounds_for_display(wounds):
    """Sort wounds by display priority (most significant first)."""
    severity_order = {"Critical": 4, "Severe": 3, "Moderate": 2, "Light": 1}
    stage_order = {
        "fresh": 6, "treated": 5, "healing": 4,
        "destroyed": 3, "severed": 2, "scarred": 1,
    }

    def wound_priority(wound):
        severity_score = severity_order.get(wound['severity'], 0)
        stage_score = stage_order.get(wound['stage'], 0)
        return (severity_score, stage_score)

    return sorted(wounds, key=wound_priority, reverse=True)
