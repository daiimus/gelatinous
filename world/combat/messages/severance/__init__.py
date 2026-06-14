"""Severance messaging library — narrative for limb / head detachment.

When a bone is destroyed by edged damage (cut / stab / laceration), the
severance pipeline routes through ``_maybe_sever_from_damage`` (head) or
``apply_sever_to_character`` (limbs). Both should broadcast a narrative
beat — distinct from the hit/kill messages — describing the
detachment.

This loader mirrors :func:`world.combat.messages.get_combat_message` so
callers get the same render shape (attacker / victim / observer audiences
plus an identity-aware ``observer_template`` for ``msg_room_identity``).

Templates are stored per-location (``head.py``, ``arms.py``, ``hands.py``,
``thighs.py``, ``shins.py``, ``feet.py``), keyed by injury type
(``cut`` / ``stab`` / ``laceration``) and severity (``grievous`` /
``minor``). Authors extend by appending entries to the appropriate
``MESSAGES`` cell.

Example::

    from world.combat.messages.severance import get_severance_message
    from world.identity_utils import msg_room_identity

    msgs = get_severance_message(
        location="head", injury_type="laceration",
        attacker=attacker, target=target, item=weapon,
        severity="grievous", hit_location="neck",
    )
    attacker.msg(msgs["attacker_msg"])
    target.msg(msgs["victim_msg"])
    msg_room_identity(
        location=attacker.location,
        template=msgs["observer_template"],
        char_refs=msgs["observer_char_refs"],
        exclude=[attacker, target],
    )

See ``specs/MEDICAL_SUBSTRATE_ROADMAP.md`` and issue #332
for the broader design context.
"""

from __future__ import annotations

import importlib
import random

from world.combat.utils import get_display_name_safe
from world.grammar import capitalize_first

# Pair-key shorthands accepted as location aliases for the limb files.
_LIMB_ALIASES = {
    # Human limbs.
    "left_arm": "arms",
    "right_arm": "arms",
    "left_hand": "hands",
    "right_hand": "hands",
    "left_thigh": "thighs",
    "right_thigh": "thighs",
    "left_shin": "shins",
    "right_shin": "shins",
    "left_foot": "feet",
    "right_foot": "feet",
    # The neck container is the routing site for decapitation;
    # narrative lives in head.py (works for any species — head /
    # neck severance prose is generic).
    "neck": "head",
    "head": "head",
    # Rat limbs (#356 follow-up).  Rat severance fires through
    # the same lookup; species-specific module names route the
    # rat anatomy.
    "left_foreleg": "forelegs",
    "right_foreleg": "forelegs",
    "left_forepaw": "forepaws",
    "right_forepaw": "forepaws",
    "left_hindleg": "hindlegs",
    "right_hindleg": "hindlegs",
    "left_hindpaw": "hindpaws",
    "right_hindpaw": "hindpaws",
    "tail": "tail",
}

_VALID_SEVERITIES = ("grievous", "minor")
_VALID_INJURY_TYPES = ("cut", "stab", "laceration")


def _resolve_module_name(location: str) -> str:
    """Map a hit-location key to the severance module that owns it."""
    if location in _LIMB_ALIASES:
        return _LIMB_ALIASES[location]
    # Already a module name (e.g. ``"arms"``) or a singular pair key.
    if location in (
        # Human pair keys.
        "arms", "hands", "thighs", "shins", "feet",
        # Rat pair keys (#356 follow-up).
        "forelegs", "hindlegs", "forepaws", "hindpaws", "tail",
    ):
        return location
    return location  # Caller passed something we don't recognise — fall
                    # through and the importlib lookup below will fail
                    # safely.


class _PassThrough(dict):
    """Dict subclass returning ``{key}`` for missing keys (partial format)."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _pick_variant(
    module_name: str, injury_type: str, severity: str, attr: str
) -> dict | None:
    """Load ``attr`` (``MESSAGES`` / ``CHROME_MESSAGES``) off the
    location module and pick a random variant.

    Returns ``None`` if any lookup step fails — callers fall through to
    the next bank or the generic template.
    """
    try:
        module = importlib.import_module(
            f"world.combat.messages.severance.{module_name}"
        )
    except ModuleNotFoundError:
        return None

    messages = getattr(module, attr, {})
    by_injury = messages.get(injury_type)
    if not isinstance(by_injury, dict):
        return None

    variants = by_injury.get(severity)
    if not isinstance(variants, list) or not variants:
        # Fall back to the other severity if this one isn't populated yet.
        other = "minor" if severity == "grievous" else "grievous"
        variants = by_injury.get(other) or []

    valid = [v for v in variants if isinstance(v, dict)]
    return random.choice(valid) if valid else None


def _select_template(
    location: str, injury_type: str, severity: str, material: str = "flesh"
) -> dict | None:
    """Pick a variant for one (location, injury, severity, material).

    Flesh severances read the location module's ``MESSAGES``.  Chrome
    severances read its ``CHROME_MESSAGES``; a location with no chrome
    bank yet falls back to the generic ``cybernetic`` module so any
    prosthetic limb still narrates as hardware, never meat.  Returns
    ``None`` if every bank is empty — callers fall through to the
    generic (blood-free) fallback template.
    """
    module_name = _resolve_module_name(location)
    if material == "chrome":
        chosen = _pick_variant(
            module_name, injury_type, severity, "CHROME_MESSAGES"
        )
        if chosen is not None:
            return chosen
        # Generic chrome prose — works at any location via {hit_location}.
        return _pick_variant(
            "cybernetic", injury_type, severity, "MESSAGES"
        )
    return _pick_variant(module_name, injury_type, severity, "MESSAGES")


def _fallback_template(location: str) -> dict:
    """Generic severance template when location-specific content is missing."""
    return {
        "attacker_msg": (
            "Your blow severs {target_name}'s {hit_location} clean from "
            "their body."
        ),
        "victim_msg": (
            "{attacker_name}'s blow severs your {hit_location} clean from "
            "your body."
        ),
        "observer_msg": (
            "{attacker_name}'s blow severs {target_name}'s {hit_location} "
            "clean from their body."
        ),
    }


def get_severance_message(
    location: str,
    injury_type: str = "cut",
    attacker=None,
    target=None,
    item=None,
    severity: str = "grievous",
    material: str = "flesh",
    **kwargs,
) -> dict:
    """Render a severance message set for one body location.

    Mirrors :func:`world.combat.messages.get_combat_message`'s return
    shape so callers can plug into the same render path (per-audience
    messages plus identity-aware observer template).

    Args:
        location: Hit-location key (\"head\", \"neck\", \"left_arm\",
            \"right_hand\", ...) or pair-key shorthand (\"arms\", \"hands\",
            ...). Aliases map onto the correct module via
            :data:`_LIMB_ALIASES`.
        injury_type: One of ``"cut"``, ``"stab"``, ``"laceration"``.
            Anything else falls through to the generic fallback.
        attacker: The character making the severing blow.
        target: The character whose body part is being severed.
        item: The weapon used (may be ``None`` for unarmed claws etc.).
        severity: ``"grievous"`` (default, dramatic / brutal) or
            ``"minor"`` (clean / surgical). Falls back to the other
            severity if the chosen cell is empty.
        material: ``"flesh"`` (default) or ``"chrome"``.  Chrome routes
            to the location's ``CHROME_MESSAGES`` bank (then the generic
            ``cybernetic`` module) so a severed prosthetic limb narrates
            as sheared hardware, not bleeding meat.
        **kwargs: Extra format substitutions (``hit_location`` is the
            common one — defaults to the canonical location key with
            underscores replaced by spaces).

    Returns:
        Dict with ``attacker_msg``, ``victim_msg``, ``observer_msg``
        (legacy pre-resolved), ``observer_template`` (identity-aware),
        and ``observer_char_refs`` (mapping for ``msg_room_identity``).
    """
    if injury_type not in _VALID_INJURY_TYPES:
        injury_type = "cut"
    if severity not in _VALID_SEVERITIES:
        severity = "grievous"

    chosen = _select_template(location, injury_type, severity, material) or _fallback_template(location)

    # Identity-aware names.
    attacker_sees_target = (
        get_display_name_safe(target, attacker) if target else "someone"
    )
    target_sees_attacker = (
        capitalize_first(get_display_name_safe(attacker, target))
        if attacker
        else "Someone"
    )

    item_s = item.key if item else "their weapon"

    shared = {
        "item_name": item_s,
        "item": item_s,
        **kwargs,
    }
    if "hit_location" not in shared:
        shared["hit_location"] = location.replace("_", " ")
    elif isinstance(shared["hit_location"], str):
        shared["hit_location"] = shared["hit_location"].replace("_", " ")

    attacker_format = {
        **shared,
        "attacker_name": "You",
        "target_name": attacker_sees_target,
        "attacker": "You",
        "target": attacker_sees_target,
    }
    victim_format = {
        **shared,
        "attacker_name": target_sees_attacker,
        "target_name": "you",
        "attacker": target_sees_attacker,
        "target": "you",
    }
    attacker_key = attacker.key if attacker else "Someone"
    target_key = target.key if target else "someone"
    observer_legacy_format = {
        **shared,
        "attacker_name": attacker_key,
        "target_name": target_key,
        "attacker": attacker_key,
        "target": target_key,
    }

    def _apply_color(msg: str) -> str:
        """Severance is a dramatic positive-strike beat → bright red."""
        if msg.startswith("|") and msg.endswith("|n"):
            return msg
        return f"|r{msg}|n"

    final: dict = {}
    fallback = _fallback_template(location)
    format_maps = {
        "attacker_msg": attacker_format,
        "victim_msg": victim_format,
        "observer_msg": observer_legacy_format,
    }
    for key, fmt in format_maps.items():
        tmpl = chosen.get(key, fallback.get(key, ""))
        try:
            final[key] = _apply_color(tmpl.format(**fmt))
        except KeyError as exc:
            final[key] = f"(Error: Missing placeholder {exc} in '{key}')"
        except Exception as exc:
            final[key] = f"(Error: Formatting issue in '{key}': {exc})"

    # Identity-aware observer template — swap char-name placeholders to
    # the msg_room_identity tokens, then partial-format the rest.
    observer_raw = chosen.get("observer_msg", fallback["observer_msg"])
    observer_template = (
        observer_raw
        .replace("{attacker_name}", "{actor}")
        .replace("{target_name}", "{target_char}")
        .replace("{attacker}", "{actor}")
        .replace("{target}", "{target_char}")
    )
    try:
        observer_template = observer_template.format_map(_PassThrough(shared))
        final["observer_template"] = _apply_color(observer_template)
    except Exception:
        final["observer_template"] = final.get("observer_msg", "")

    final["observer_char_refs"] = {"actor": attacker, "target_char": target}
    return final
