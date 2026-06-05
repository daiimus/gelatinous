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
from .constants import (
    get_location_display_name,
    INJURY_SEVERITY_MAP,
    MEDICAL_COLORS,
)
from . import messages

import random


def get_destroyed_locations_from_snapshot(snapshot):
    """Return the set of display locations with destroyed-stage organs
    in a preserved medical-state snapshot.

    Used by severed-part renderers (``Appendage.return_appearance``,
    including ``SeveredHead``) to drive the destroyed-organ longdesc
    suppression (issue #350 follow-up).  These items can't use
    :func:`get_destroyed_display_locations` because their carried
    wound list (``db.wounds_at_death``) is rewritten to
    ``stage="old"`` at sever time — the destroyed-stage signal lives
    only in the preserved organ snapshot.

    Snapshot shape (the dict produced by
    :meth:`world.medical.core.MedicalState.to_dict`):

    .. code-block:: python

        {
            "organs": {
                "left_eye": {
                    "container": "head",
                    "display_location": "left_eye",
                    "wound_stage": "destroyed",
                    ...
                },
                ...
            },
            ...
        }

    Falls back to ``container`` when a snapshot entry omits
    ``display_location`` (legacy snapshots pre-#346).

    Args:
        snapshot: ``dict`` produced by ``MedicalState.to_dict``, or
            ``None``.

    Returns:
        ``set[str]`` of display-location names.
    """
    organs = (snapshot or {}).get("organs") or {}
    locs = set()
    for data in organs.values():
        if data.get("wound_stage") != "destroyed":
            continue
        loc = data.get("display_location") or data.get("container")
        if loc:
            locs.add(loc)
    return locs


def get_destroyed_display_locations(wounds):
    """Return the set of display locations with destroyed-stage wounds.

    Issue #350 / PR-B: the longdesc renderer consults this set per
    location and suppresses the authored longdesc whenever a destroyed
    organ surfaces there.  The destruction wound is the canonical
    description at a destroyed location; the authored prose
    (``"His left eye is brown"``) would otherwise lie alongside it.

    Universal — operates on the wound list shape produced by both
    living characters (``get_character_wounds``) and corpses
    (``db.wounds_at_death``).  No species knowledge is needed: organ
    routing to a display location was handled by #346 and is already
    baked into the wound dict's ``location`` field.

    Coverage interaction: ``get_character_wounds`` filters by
    clothing coverage at the visibility gate, so a destroyed organ
    hidden under armor produces no wound in the input list, which
    means the longdesc at that location is NOT suppressed — the
    authored prose remains as a fallback when no destruction would
    otherwise render.

    Args:
        wounds: Iterable of wound dicts with ``location`` and
            ``stage`` fields.  ``None`` / empty → empty set.

    Returns:
        ``set[str]`` of display-location names.
    """
    return {
        w["location"]
        for w in (wounds or [])
        if w.get("stage") == "destroyed" and w.get("location")
    }


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

    Per-injury-type compound templates mirror the single-wound
    ``messages.<type>.WOUND_DESCRIPTIONS`` dicts: the worst wound's
    ``injury_type`` selects a ``messages.<type>.COMPOUND_DESCRIPTIONS``
    set (falling back to ``messages.generic``), keyed by the worst
    wound's healing ``stage``. A random variant is chosen and formatted
    with the worst wound's severity, the location name, and an
    ``{others_phrase}`` count of the remaining wounds — exactly how
    ``get_wound_description`` resolves a single wound.

    When no template set resolves (e.g. an injury type with no compound
    dict and a missing generic fallback), the legacy inline phrasing
    below is used so the summarizer always returns a sentence.

    Args:
        worst_wound (dict): Highest-priority wound at this location.
        others_count (int): Number of additional wounds beyond the worst.
        character: Character object (for skintone / species naming).

    Returns:
        str: A formatted, single-sentence compound summary.
    """
    location_display = get_location_display_name(
        worst_wound['location'], character
    )
    others_phrase = (
        "another wound" if others_count == 1 else "several other wounds"
    )
    stage = worst_wound['stage']
    injury_type = worst_wound['injury_type']
    severity = INJURY_SEVERITY_MAP.get(
        worst_wound['severity'], worst_wound['severity'].lower()
    )

    template = _resolve_compound_template(injury_type, stage)
    if template:
        format_vars = {
            'severity': severity,
            'location': location_display,
            'others_phrase': others_phrase,
            'skintone': _skintone_color(character),
        }
        format_vars.update(MEDICAL_COLORS)
        return _format_wound_grammar(template.format(**format_vars))

    # Ultimate fallback: legacy inline phrasing (no template set available).
    # No fresh/raw wound in the mix: render a calm, skintone-colored summary.
    if stage in ("treated", "healing", "scarred"):
        skintone_color = _skintone_color(character)
        phrase = (f"{skintone_color}multiple old wounds mark the "
                  f"{location_display}|n")
        return _format_wound_grammar(phrase)

    type_word = "" if injury_type == "generic" else f"{injury_type} "
    phrase = (f"|Ra {severity} {type_word}wound and {others_phrase} "
              f"mark the {location_display}|n")
    return _format_wound_grammar(phrase)


def get_paired_severed_description(character, left_location, right_location,
                                  looker=None):
    """
    Render one plural stump line for a symmetric pair severed on both sides.

    When both members of a ``left_*``/``right_*`` pair have been cleanly
    amputated, their individual stump descriptions are collapsed into a
    single plural sentence (e.g. "Both hands have been cleanly amputated...")
    so the body description reads naturally instead of repeating two nearly
    identical amputation lines.

    Args:
        character: Character object (reserved for future species naming).
        left_location (str): The ``left_*`` member of the pair.
        right_location (str): The ``right_*`` member of the pair.
        looker: Character looking (reserved for future permission checks).

    Returns:
        str | None: A formatted plural stump sentence when both sides are
            severed, else ``None``.
    """
    if not (_location_is_severed(character, left_location)
            and _location_is_severed(character, right_location)):
        return None

    from world.grammar import pluralize_noun

    base_noun = _pair_base_noun(left_location)
    plural = pluralize_noun(base_noun)
    location_display = f"both {plural}"

    templates = getattr(messages.generic, 'PAIRED_SEVERED_DESCRIPTIONS', None)
    if not templates:
        return None
    template = random.choice(templates)
    return _format_wound_grammar(template.format(location=location_display))


def get_paired_destroyed_description(character, pair_key,
                                     left_location, right_location,
                                     looker=None, wounds=None):
    """Render one plural destruction line for both sides destroyed by
    the same injury type (issue #350 / PR-C).

    When both members of a ``left_*``/``right_*`` pair carry destroyed
    wounds AND those wounds share an injury type, the per-side
    destruction lines are collapsed into a single pair line keyed by
    the pair shorthand (``"eyes"``, ``"ears"``, ...) on the injury-
    type module's ``DESTROYED_BY_PAIR`` overlay.  Falls through to
    ``messages.generic.DESTROYED_BY_PAIR`` when the per-injury-type
    overlay has no entry; returns ``None`` when the generic also
    lacks a template (caller then renders each side independently).

    Mismatched mechanisms (e.g., left eye cut, right eye shot) do NOT
    collapse — the per-side render reads more honestly than a
    paper-thin \"both eyes destroyed\" generalization that hides which
    mechanism took which.

    Args:
        character: Character / corpse object.  Used for gender /
            species lookup (falls back across ``.gender`` and
            ``.db.original_gender`` so both live characters and
            corpses work) and for skintone if a template needs it.
        pair_key (str): Pair shorthand from the species pair table
            (``"eyes"``, ``"ears"``, ``"arms"``, ...).
        left_location (str): The ``left_*`` member.
        right_location (str): The ``right_*`` member.
        looker: Reserved for future permission checks.
        wounds: Optional wound-list override.  When ``None`` (the
            living-character default) we call ``get_character_wounds``
            which filters by clothing visibility.  Corpses pass
            ``self.db.wounds_at_death`` so the preserved snapshot
            drives the collapse decision without a live medical-state
            lookup.

    Returns:
        str | None: A formatted pair-destruction sentence when both
            sides are destroyed by a common injury type and an
            overlay template exists, else ``None``.
    """
    if wounds is None:
        wounds = get_character_wounds(character)
    left_destroyed = [
        w for w in wounds
        if w["location"] == left_location and w.get("stage") == "destroyed"
    ]
    right_destroyed = [
        w for w in wounds
        if w["location"] == right_location and w.get("stage") == "destroyed"
    ]
    if not left_destroyed or not right_destroyed:
        return None

    # Common injury type: both sides destroyed by the same mechanism.
    # Mismatched mechanisms fall through to per-side rendering — that
    # reads more honestly than collapsing two different causes into
    # one pair line.
    left_types = {w["injury_type"] for w in left_destroyed}
    right_types = {w["injury_type"] for w in right_destroyed}
    common = left_types & right_types
    if not common:
        return None
    # When more than one injury type matches both sides (e.g., both
    # eyes carried cut AND blunt wounds, both destroyed), pick the
    # alphabetical first for determinism — the variation between
    # cells is mostly cosmetic and the per-side fallback is fine if
    # this isn't a great match.
    injury_type = sorted(common)[0]

    # Overlay lookup: per-injury-type → generic fallback → None.
    try:
        message_module = getattr(messages, injury_type)
    except AttributeError:
        message_module = messages.generic
    overlay = getattr(message_module, "DESTROYED_BY_PAIR", None) or {}
    variants = overlay.get(pair_key)
    if not variants:
        generic_overlay = getattr(messages.generic, "DESTROYED_BY_PAIR", None) or {}
        variants = generic_overlay.get(pair_key)
    if not variants:
        return None

    template = random.choice(variants)

    # Severity drive from the worst left+right wound (Critical wins).
    severity_order = ("Light", "Moderate", "Severe", "Critical")
    worst = max(
        left_destroyed + right_destroyed,
        key=lambda w: severity_order.index(w.get("severity", "Moderate"))
        if w.get("severity") in severity_order else 1,
    )

    location_display = ""  # Pair templates address the body directly via
    # pronouns / explicit pair noun; the {location} token is available if
    # an author wants the species-routed pair noun.
    try:
        from world.grammar import pluralize_noun
        # Pair shorthand IS already plural ("eyes", "ears"), but some
        # authors may have built it from a singular stem. Be defensive.
        location_display = pluralize_noun(
            pair_key[:-1] if pair_key.endswith("s") else pair_key
        )
    except ImportError:
        location_display = pair_key

    format_vars = {
        "severity": INJURY_SEVERITY_MAP.get(
            worst.get("severity", "Moderate"),
            worst.get("severity", "Moderate").lower(),
        ),
        "location": location_display,
        "injury_type": injury_type,
        "skintone": "",
    }
    format_vars.update(MEDICAL_COLORS)

    class _PreserveMissing(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    rendered = template.format_map(_PreserveMissing(format_vars))

    # Pronoun pass — pair-collapsed prose typically uses ``{Their}``,
    # ``{their}``, ``{them}`` to read naturally.  Plural number so
    # body-noun flex stays at the pair-shorthand level (``"eyes"``
    # not ``"eye"``).
    try:
        from world.anatomy import substitute_pronoun_tokens
        gender = (
            getattr(character, "gender", None)
            or character.db.original_gender
        )
        species = getattr(character.db, "species", None) or "human"
        rendered = substitute_pronoun_tokens(
            rendered, gender=gender, number="plural", species=species,
        )
    except (AttributeError, ImportError):
        pass

    return _format_wound_grammar(rendered)


def _location_is_severed(character, location):
    """Return True if every wound at ``location`` is a clean severance."""
    location_wounds = [
        w for w in get_character_wounds(character)
        if w['location'] == location
    ]
    if not location_wounds:
        return False
    return all(w.get('stage') == 'severed' for w in location_wounds)


def _pair_base_noun(location):
    """Strip a ``left_``/``right_`` prefix to the bare body-part noun."""
    for prefix in ("left_", "right_"):
        if location.startswith(prefix):
            return location[len(prefix):].replace("_", " ")
    return location.replace("_", " ")


def _resolve_compound_template(injury_type, stage):
    """
    Resolve a random compound template for an injury type and stage.

    Mirrors ``get_wound_description`` resolution: look up the injury
    type's ``COMPOUND_DESCRIPTIONS`` module dict, fall back to
    ``messages.generic`` when the type has none, then key by ``stage``
    with a ``"fresh"`` default.

    Args:
        injury_type (str): Worst wound's injury type (bullet, cut, ...).
        stage (str): Worst wound's healing stage.

    Returns:
        str | None: A chosen template string, or ``None`` when no
            template set is available (caller falls back to inline prose).
    """
    compound = None
    # Defensive: ``getattr`` requires a string attribute name.  Earlier
    # callers occasionally produced a ``None`` ``injury_type`` for
    # severed organs whose ``injury_type`` field was never populated
    # (sever_character_body sets current_hp/wound_stage but not
    # injury_type).  Fall through to the generic compound table when
    # the injury type is missing or non-string.
    module = (
        getattr(messages, injury_type, None)
        if isinstance(injury_type, str)
        else None
    )
    if module is not None:
        compound = getattr(module, 'COMPOUND_DESCRIPTIONS', None)
    if not compound:
        compound = getattr(messages.generic, 'COMPOUND_DESCRIPTIONS', None)
    if not compound:
        return None

    variants = compound.get(stage) or compound.get('fresh')
    if not variants:
        return None
    return random.choice(variants)



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
