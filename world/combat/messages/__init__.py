import importlib
import random

from world.combat.utils import get_display_name_safe
from world.grammar import capitalize_first


def get_combat_message(weapon_type, phase, attacker=None, target=None, item=None, **kwargs):
    """
    Load the appropriate combat message from a specific weapon_type module.
    Returns a dictionary with "attacker_msg", "victim_msg", "observer_msg",
    plus identity-aware fields for per-observer resolution.

    Args:
        weapon_type (str): e.g., "unarmed", "blade"
        phase (str): One of "initiate", "hit", "miss", "kill", etc.
        attacker (Object): The attacker
        target (Object): The target
        item (Object): The weapon/item used (can be None for unarmed)
        **kwargs: Any extra variables for formatting (e.g., damage)

    Returns:
        dict: A dictionary containing:
            - "attacker_msg": Formatted message for the attacker
            - "victim_msg": Formatted message for the victim
            - "observer_msg": Pre-resolved observer message (legacy, uses .key)
            - "observer_template": Template with {actor}/{target_char}
              placeholders for ``msg_room_identity``
            - "observer_char_refs": Dict mapping placeholder names to
              character objects for ``msg_room_identity``
    """
    # Identity-aware names for attacker_msg (target seen by attacker)
    attacker_sees_target = (
        get_display_name_safe(target, attacker) if target else "someone"
    )
    # Identity-aware names for victim_msg (attacker seen by target)
    target_sees_attacker = (
        capitalize_first(get_display_name_safe(attacker, target))
        if attacker
        else "Someone"
    )

    item_s = item.key if item else "fists"  # Default item name if None

    # Determine verb forms for fallback messages based on phase
    verb_root = phase.lower()
    attacker_verb = verb_root  # For "You verb..."
    third_person_verb = f"{verb_root}s"  # Default for "Someone verbs..."

    if verb_root.endswith("s") or verb_root.endswith("sh") or \
       verb_root.endswith("ch") or verb_root.endswith("x") or \
       verb_root.endswith("z"):
        third_person_verb = f"{verb_root}es"
    elif verb_root.endswith("y") and len(verb_root) > 1 and verb_root[-2].lower() not in "aeiou":
        third_person_verb = f"{verb_root[:-1]}ies"
    
    # Specific overrides for common verbs if needed
    if verb_root == "hit":
        attacker_verb = "hit"
        third_person_verb = "hits"
    elif verb_root == "miss":  # "miss" -> "misses"
        attacker_verb = "miss"  # "You miss"
        third_person_verb = "misses"  # "Someone misses"
    # Add more overrides if other phases require special verb forms

    # Fallback message templates (using placeholders)
    fallback_template_set = {
        "attacker_msg": f"You {attacker_verb} {{target_name}} with {{item_name}}.",
        "victim_msg": f"{{attacker_name}} {third_person_verb} you with {{item_name}}.",
        "observer_msg": f"{{attacker_name}} {third_person_verb} {{target_name}} with {{item_name}}."
    }

    chosen_template_set = None
    try:
        module_path = f"world.combat.messages.{weapon_type}"
        module = importlib.import_module(module_path)
        messages_for_weapon = getattr(module, "MESSAGES", {})
        templates_for_phase = messages_for_weapon.get(phase, [])
        
        if templates_for_phase and isinstance(templates_for_phase, list):
            valid_templates = [t for t in templates_for_phase if isinstance(t, dict)]
            if valid_templates:
                chosen_template_set = random.choice(valid_templates)
    except ModuleNotFoundError:
        pass  # chosen_template_set remains None, will use fallback
    except Exception:
        pass  # chosen_template_set remains None, will use fallback

    # If no specific template was loaded (or error), use the fallback set
    if not chosen_template_set:
        chosen_template_set = fallback_template_set

    # ── Build per-audience format kwargs ────────────────────────────
    # Non-character kwargs shared across all audiences
    shared_kwargs = {
        "item_name": item_s,
        "item": item_s,
        "phase": phase,
        **kwargs,
    }
    # Format hit_location to replace underscores with spaces
    if "hit_location" in shared_kwargs:
        shared_kwargs["hit_location"] = shared_kwargs["hit_location"].replace("_", " ")

    # Attacker sees target via identity system
    attacker_format = {
        **shared_kwargs,
        "attacker_name": "You",
        "target_name": attacker_sees_target,
        "attacker": "You",
        "target": attacker_sees_target,
    }

    # Victim sees attacker via identity system
    victim_format = {
        **shared_kwargs,
        "attacker_name": target_sees_attacker,
        "target_name": "you",
        "attacker": target_sees_attacker,
        "target": "you",
    }

    # Legacy observer format (pre-resolved with .key for backward compat)
    attacker_key = attacker.key if attacker else "Someone"
    target_key = target.key if target else "someone"
    observer_legacy_format = {
        **shared_kwargs,
        "attacker_name": attacker_key,
        "target_name": target_key,
        "attacker": attacker_key,
        "target": target_key,
    }

    # ── Phase coloring ──────────────────────────────────────────────
    successful_hit_phases = [
        "initiate",
        "hit",
        "grapple_damage_hit",
        "kill",
        "grapple_damage_kill",
    ]
    miss_phases = [
        "miss",
        "grapple_damage_miss",
    ]

    def _apply_color(msg: str) -> str:
        """Wrap message in phase-appropriate color codes."""
        if phase in successful_hit_phases:
            if not (msg.startswith("|") and msg.endswith("|n")):
                if phase in ("kill", "grapple_damage_kill"):
                    return f"|r{msg}|n"
                return f"|R{msg}|n"
        elif phase in miss_phases:
            if not (msg.startswith("|") and msg.endswith("|n")):
                return f"|W{msg}|n"
        return msg

    # ── Format each audience message ────────────────────────────────
    final_messages: dict = {}
    format_maps = {
        "attacker_msg": attacker_format,
        "victim_msg": victim_format,
        "observer_msg": observer_legacy_format,
    }

    for msg_key, fmt_kwargs in format_maps.items():
        template_str = chosen_template_set.get(
            msg_key,
            fallback_template_set.get(msg_key, "Error: Message template key missing."),
        )
        try:
            formatted_msg = template_str.format(**fmt_kwargs)
            final_messages[msg_key] = _apply_color(formatted_msg)
        except KeyError as e_key:
            final_messages[msg_key] = (
                f"(Error: Missing placeholder {e_key} in template for '{msg_key}')"
            )
        except Exception as e_fmt:
            final_messages[msg_key] = (
                f"(Error: Formatting issue for '{msg_key}': {e_fmt})"
            )

    # ── Build identity-aware observer template ──────────────────────
    # Replace character-name placeholders with msg_room_identity tokens
    # so callers can send per-observer resolved messages.
    observer_raw = chosen_template_set.get(
        "observer_msg",
        fallback_template_set.get("observer_msg", ""),
    )
    try:
        # Swap character-name placeholders to identity tokens BEFORE
        # formatting, so .format() leaves them as literal {actor} / {target_char}.
        observer_template_str = observer_raw.replace(
            "{attacker_name}", "{actor}"
        ).replace(
            "{target_name}", "{target_char}"
        ).replace(
            "{attacker}", "{actor}"
        ).replace(
            "{target}", "{target_char}"
        )
        # Format only non-character placeholders.  Use format_map with
        # a _PassThrough mapping so unknown keys (actor, target_char)
        # are left as literal {key} in the output.
        observer_template_str = observer_template_str.format_map(
            _PassThrough(shared_kwargs)
        )
        final_messages["observer_template"] = _apply_color(observer_template_str)
    except Exception:
        # Fall back to the pre-resolved legacy observer_msg
        final_messages["observer_template"] = final_messages.get("observer_msg", "")

    final_messages["observer_char_refs"] = {
        "actor": attacker,
        "target_char": target,
    }

    return final_messages


class _PassThrough(dict):
    """A dict subclass that returns ``{key}`` for missing keys.

    Used with :meth:`str.format_map` to partially format a template
    string — known keys are substituted while unknown keys are left as
    literal ``{key}`` placeholders in the output.
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
