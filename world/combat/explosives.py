"""
Explosive & Grenade Utilities

Functions for sticky-grenade adhesion mechanics, human-shield logic
during explosions, and helpers for traversing the location hierarchy
to find the blast room.

Extracted from ``world/combat/utils.py`` during Phase 2 refactoring.

Functions:
    check_grenade_human_shield — grapple-based shield damage modifiers
    send_grenade_shield_messages — notify participants of shield event
    calculate_stick_chance — magnetic adhesion probability
    get_explosion_room — resolve room through item/character hierarchy
    establish_stick — create bidirectional grenade↔armor bond
    get_stuck_grenades_on_character — find all stuck grenades on worn items
    get_outermost_armor_at_location — highest-layer armor at body slot
    break_stick — sever grenade↔armor magnetic bond
"""

from __future__ import annotations

from .constants import (
    DB_CHAR,
    DB_COMBATANTS,
    DB_GRAPPLING_DBREF,
    NDB_COMBAT_HANDLER,
)
from .debug import debug_broadcast, get_splattercast


# ------------------------------------------------------------------
# Human-shield mechanics
# ------------------------------------------------------------------

def check_grenade_human_shield(proximity_list, combat_handler=None):
    """
    Check for human-shield mechanics in grenade explosions.

    For characters in *proximity_list* who are grappling someone,
    implement simplified human-shield mechanics:

    * Grappler automatically uses victim as blast shield → no damage.
    * Victim takes double damage.

    Args:
        proximity_list: List of characters in blast radius.
        combat_handler: Optional combat handler for grapple state
            checking.

    Returns:
        ``dict`` of ``{char: damage_multiplier}`` where multiplier is
        ``0.0`` for grapplers and ``2.0`` for victims.
    """
    from .utils import get_character_by_dbref  # lazy to avoid circular import

    splattercast = get_splattercast()
    damage_modifiers: dict = {}

    # If no combat handler provided, try to find one from the characters
    if not combat_handler and proximity_list:
        for char in proximity_list:
            if hasattr(char.ndb, NDB_COMBAT_HANDLER):
                combat_handler = getattr(char.ndb, NDB_COMBAT_HANDLER)
                break

    if not combat_handler:
        splattercast.msg(
            "GRENADE_SHIELD: No combat handler found, skipping human shield checks"
        )
        return damage_modifiers

    # Get current combatants list for grapple state checking
    combatants_list = combat_handler.db.combatants or []

    for char in proximity_list:
        # Find this character's combat entry
        char_entry = next(
            (e for e in combatants_list if e.get(DB_CHAR) == char), None
        )
        if not char_entry:
            continue

        # Check if this character is grappling someone
        grappling_dbref = char_entry.get(DB_GRAPPLING_DBREF)
        if grappling_dbref:
            victim = get_character_by_dbref(grappling_dbref)
            if victim and victim in proximity_list:
                # Both grappler and victim are in blast radius
                damage_modifiers[char] = 0.0   # Grappler takes no damage
                damage_modifiers[victim] = 2.0  # Victim takes double damage

                # Send human shield messages
                send_grenade_shield_messages(char, victim)

                splattercast.msg(
                    f"GRENADE_SHIELD: {char.key} using {victim.key} as blast shield"
                )

    return damage_modifiers


def send_grenade_shield_messages(grappler, victim) -> None:
    """
    Send human-shield messages specific to grenade explosions.

    Args:
        grappler: The character using *victim* as shield.
        victim: The character being used as shield.
    """
    from .utils import get_display_name_safe  # lazy to avoid circular import

    grappler_msg = (
        f"|yYou instinctively position {get_display_name_safe(victim)} "
        f"between yourself and the explosion!|n"
    )
    victim_msg = (
        f"|RYou are forced to absorb the full blast as "
        f"{get_display_name_safe(grappler)} uses you as a shield!|n"
    )
    observer_msg = (
        f"|y{get_display_name_safe(grappler)} uses "
        f"{get_display_name_safe(victim)} as a human shield against "
        f"the explosion!|n"
    )

    grappler.msg(grappler_msg)
    victim.msg(victim_msg)

    # Send to observers in the same location
    if grappler.location:
        grappler.location.msg_contents(
            observer_msg, exclude=[grappler, victim]
        )


# ------------------------------------------------------------------
# Sticky-grenade adhesion
# ------------------------------------------------------------------

def calculate_stick_chance(grenade, armor) -> int:
    """
    Calculate the chance that a sticky grenade will adhere to armor.

    Stick criteria:

    1. Check armor base metal / magnetic levels.
    2. If armor is a plate carrier, check installed plates for highest
       values.
    3. Threshold check: ``magnetic_level >= (grenade_strength - 3)``
       AND ``metal_level >= (grenade_strength - 5)``.
    4. If threshold met: ``chance = 40 + (metal_level * 5) +
       (magnetic_level * 5)``.
    5. Maximum 95 % (always a 5 % chance to fail).

    Args:
        grenade: The sticky grenade object with ``magnetic_strength``.
        armor: The armor ``Item`` with ``metal_level`` and
            ``magnetic_level``.

    Returns:
        Percentage chance to stick (0–95), or 0 if thresholds not met.
    """
    from typeclasses.items import Item

    # Validate inputs
    if not grenade or not armor:
        return 0

    # Get grenade magnetic strength (default 5 if not set)
    magnetic_strength = (
        grenade.db.magnetic_strength
        if grenade.db.magnetic_strength is not None
        else 5
    )

    # Get armor base properties (default 0 if not set)
    metal_level = (
        armor.db.metal_level if armor.db.metal_level is not None else 0
    )
    magnetic_level = (
        armor.db.magnetic_level if armor.db.magnetic_level is not None else 0
    )

    # PLATE CARRIER CHECK: If this is a plate carrier, check installed plates
    is_plate_carrier = armor.db.is_plate_carrier
    if is_plate_carrier:
        installed_plates = armor.db.installed_plates or {}

        # Check all installed plates and use highest metal/magnetic values
        for slot, plate_ref in installed_plates.items():
            if plate_ref:
                plate_metal = (
                    plate_ref.db.metal_level
                    if plate_ref.db.metal_level is not None
                    else 0
                )
                plate_magnetic = (
                    plate_ref.db.magnetic_level
                    if plate_ref.db.magnetic_level is not None
                    else 0
                )

                metal_level = max(metal_level, plate_metal)
                magnetic_level = max(magnetic_level, plate_magnetic)

                debug_broadcast(
                    f"Plate carrier check: {armor.key} slot {slot} has "
                    f"{plate_ref.key} (metal={plate_metal}, "
                    f"magnetic={plate_magnetic})",
                    prefix="STICKY_GRENADE",
                    status="PLATE_CHECK",
                )

        debug_broadcast(
            f"Plate carrier final values: metal={metal_level}, "
            f"magnetic={magnetic_level}",
            prefix="STICKY_GRENADE",
            status="PLATE_FINAL",
        )

    # Calculate thresholds
    magnetic_threshold = magnetic_strength - 3
    metal_threshold = magnetic_strength - 5

    # Check if thresholds are met
    if magnetic_level < magnetic_threshold or metal_level < metal_threshold:
        debug_broadcast(
            f"Stick failed threshold: {grenade.key} vs {armor.key} "
            f"(magnetic {magnetic_level}/{magnetic_threshold}, "
            f"metal {metal_level}/{metal_threshold})",
            prefix="STICKY_GRENADE",
            status="THRESHOLD_FAIL",
        )
        return 0

    # Calculate base chance
    chance = 40 + (metal_level * 5) + (magnetic_level * 5)

    # Cap at 95% (always 5% failure chance)
    chance = min(chance, 95)

    debug_broadcast(
        f"Stick chance: {grenade.key} vs {armor.key} = {chance}% "
        f"(metal={metal_level}, magnetic={magnetic_level}, "
        f"strength={magnetic_strength})",
        prefix="STICKY_GRENADE",
        status="CALC",
    )

    return chance


def get_explosion_room(grenade):
    """
    Get the room where a grenade will explode, handling armor hierarchy.

    Traverses the location hierarchy to find the room:

    * ``grenade.location = armor`` → ``armor.location = character/room``
    * ``grenade.location = character`` → ``character.location = room``
    * ``grenade.location = room`` → room itself

    Args:
        grenade: The grenade object.

    Returns:
        Room object or ``None`` if grenade has no valid explosion
        location.
    """
    from typeclasses.characters import Character
    from typeclasses.items import Item
    from typeclasses.rooms import Room

    if not grenade or not grenade.location:
        debug_broadcast(
            "Explosion room lookup failed: grenade has no location",
            prefix="STICKY_GRENADE",
            status="ERROR",
        )
        return None

    location = grenade.location

    # If grenade is in/on an Item (armor), go up one level
    if isinstance(location, Item):
        debug_broadcast(
            f"Grenade {grenade.key} stuck to armor {location.key}, "
            f"checking armor location",
            prefix="STICKY_GRENADE",
            status="HIERARCHY",
        )
        location = location.location

    # If we're now at a Character, go up one more level to room
    if isinstance(location, Character):
        debug_broadcast(
            f"Grenade on character {location.key}, getting their room",
            prefix="STICKY_GRENADE",
            status="HIERARCHY",
        )
        location = location.location

    # Validate we have a room
    if isinstance(location, Room):
        debug_broadcast(
            f"Explosion room for {grenade.key}: {location.key}",
            prefix="STICKY_GRENADE",
            status="SUCCESS",
        )
        return location

    debug_broadcast(
        f"Explosion room lookup failed: final location is "
        f"{type(location).__name__}",
        prefix="STICKY_GRENADE",
        status="ERROR",
    )
    return None


def establish_stick(grenade, armor, hit_location: str) -> bool:
    """
    Establish bidirectional sticky-grenade relationship.

    Sets up the magnetic bond between grenade and armor:

    * ``grenade.location = armor`` (physical containment)
    * ``grenade.db.stuck_to_armor = armor`` (reference)
    * ``grenade.db.stuck_to_location = hit_location`` (body part)
    * ``armor.db.stuck_grenade = grenade`` (bidirectional reference)

    Args:
        grenade: The sticky grenade object.
        armor: The armor ``Item`` object.
        hit_location: Body location string (e.g. ``"chest"``).

    Returns:
        ``True`` if stick established successfully.
    """
    from typeclasses.items import Item

    # Validate inputs
    if not grenade or not armor or not isinstance(armor, Item):
        debug_broadcast(
            "Stick establishment failed: invalid inputs",
            prefix="STICKY_GRENADE",
            status="ERROR",
        )
        return False

    # Break any existing stick first
    if grenade.db.stuck_to_armor:
        old_armor = grenade.db.stuck_to_armor
        if old_armor and old_armor.db.stuck_grenade is not None:
            old_armor.db.stuck_grenade = None

    # Establish new stick — grenade moves to armor
    grenade.location = armor

    # Set grenade attributes
    grenade.db.stuck_to_armor = armor
    grenade.db.stuck_to_location = hit_location

    # Set armor attribute (bidirectional reference)
    armor.db.stuck_grenade = grenade

    debug_broadcast(
        f"Stick established: {grenade.key} -> {armor.key} at "
        f"{hit_location}",
        prefix="STICKY_GRENADE",
        status="SUCCESS",
    )

    return True


def get_stuck_grenades_on_character(character) -> list[tuple]:
    """
    Get all sticky grenades currently stuck to a character's armor.

    Searches all worn items for stuck grenades.

    Args:
        character: The ``Character`` object to check.

    Returns:
        List of ``(grenade, armor, location)`` tuples for each stuck
        grenade.
    """
    from typeclasses.characters import Character
    from typeclasses.items import Item

    if not isinstance(character, Character):
        return []

    stuck_grenades: list[tuple] = []

    # Check all items in character's inventory
    for item in character.contents:
        if not isinstance(item, Item):
            continue

        # Check if this item has a stuck grenade
        if item.db.stuck_grenade:
            grenade = item.db.stuck_grenade
            location = (
                grenade.db.stuck_to_location
                if grenade.db.stuck_to_location is not None
                else "unknown"
            )
            stuck_grenades.append((grenade, item, location))

            debug_broadcast(
                f"Found stuck grenade: {grenade.key} on {item.key} "
                f"({location})",
                prefix="STICKY_GRENADE",
                status="FOUND",
            )

    return stuck_grenades


def get_outermost_armor_at_location(character, hit_location: str):
    """
    Get the outermost armor piece at a specific body location.

    Searches worn items for highest layer number at the hit location.

    Args:
        character: The ``Character`` object.
        hit_location: Body location string (e.g. ``"chest"``).

    Returns:
        The outermost armor ``Item`` at that location, or ``None`` if
        no armor covers it.
    """
    from typeclasses.characters import Character
    from typeclasses.items import Item

    if not isinstance(character, Character):
        return None

    outermost_armor = None
    highest_layer = -1

    # Check all worn items
    for item in character.contents:
        if not isinstance(item, Item):
            continue

        # Check if item covers this location
        coverage = item.db.coverage or []
        if not coverage or hit_location not in coverage:
            continue

        # Check layer
        layer = item.db.layer if item.db.layer is not None else 0
        if layer > highest_layer:
            highest_layer = layer
            outermost_armor = item

    if outermost_armor:
        debug_broadcast(
            f"Outermost armor at {hit_location}: {outermost_armor.key} "
            f"(layer {highest_layer})",
            prefix="STICKY_GRENADE",
            status="FOUND",
        )
    else:
        debug_broadcast(
            f"No armor found at {hit_location}",
            prefix="STICKY_GRENADE",
            status="NOT_FOUND",
        )

    return outermost_armor


def break_stick(grenade) -> bool:
    """
    Break the magnetic bond between grenade and armor.

    Cleans up all bidirectional references.  The grenade's location is
    **not** changed — the caller must handle that separately.

    Args:
        grenade: The sticky grenade object.

    Returns:
        ``True`` if stick was broken, ``False`` if no stick existed.
    """
    if not grenade:
        return False

    # Check if grenade is stuck
    if not grenade.db.stuck_to_armor:
        return False

    armor = grenade.db.stuck_to_armor
    location = (
        grenade.db.stuck_to_location
        if grenade.db.stuck_to_location is not None
        else "unknown"
    )

    # Clear armor's reference to grenade
    if armor and armor.db.stuck_grenade is not None:
        armor.db.stuck_grenade = None

    # Clear grenade's references
    grenade.db.stuck_to_armor = None
    grenade.db.stuck_to_location = None

    debug_broadcast(
        f"Stick broken: {grenade.key} from "
        f"{armor.key if armor else 'unknown'} at {location}",
        prefix="STICKY_GRENADE",
        status="BREAK",
    )

    return True
