"""
Throw flight / landing / deflection engine (issue #471 step 2).

Extracted from ``commands/CmdThrow.py`` so the command owns parsing,
validation, and announcements while the physics — flight timers,
landing resolution, proximity assignment, grenade deflection — live
here, importable by anything that launches objects (the throw
command, rigged-grenade triggers in ``commands/explosion_utils.py``,
future launchers).

Behavioral contract: ``world/tests/test_throw_characterization.py``.
The extraction is verbatim except for two deliberate changes:

* **The dead weapon-flight path is gone.**  ``CmdThrow.func`` returns
  for every ``is_throwing_weapon`` object (redirecting targeted
  throws to ``attack``), so the old ``is_weapon=True`` plumbing was
  unreachable.  ``resolve_weapon_hit`` remains — it is the sticky
  grenade's stick/bounce/damage resolver, reached via
  ``handle_landing``.  (When ammo tracking arrives for guns and
  throwing weapons, a real weapon-flight path can be wired back
  against the characterization suite.)
* **No broad excepts** (#469).  The engine lets failures surface:
  inside the flight-timer callback Twisted logs the traceback, and
  ``complete_flight`` guarantees flight-state cleanup via ``finally``
  so a mid-landing bug can never strand an object in the "flying"
  state.  The only guards kept are narrow ones with a named, expected
  failure (timer double-cancellation).
"""

import random

from evennia import utils

from twisted.internet.error import AlreadyCalled, AlreadyCancelled

from world.combat.debug import get_splattercast
from world.combat.constants import (
    DB_CHAR,
    DB_GRAPPLED_BY_DBREF,
    DB_GRAPPLING_DBREF,
    DEBUG_PREFIX_THROW,
    MSG_THROW_ARRIVAL,
    MSG_THROW_ARRIVAL_TARGETED,
    MSG_THROW_ARRIVAL_TARGETED_VICTIM,
    MSG_THROW_FLIGHT_SAMEROOM_GENERAL,
    MSG_THROW_FLIGHT_SAMEROOM_TARGET,
    MSG_THROW_FLIGHT_SAMEROOM_TARGET_VICTIM,
    MSG_THROW_LANDING_PROXIMITY,
    MSG_THROW_LANDING_ROOM,
    MSG_THROW_UTILITY_BOUNCE,
    MSG_THROW_UTILITY_BOUNCE_VICTIM,
    MSG_THROW_WEAPON_HIT,
    MSG_THROW_WEAPON_HIT_VICTIM,
    MSG_THROW_WEAPON_MISS,
    MSG_THROW_WEAPON_MISS_VICTIM,
    NDB_COMBAT_HANDLER,
    NDB_FLYING_OBJECTS,
    NDB_PROXIMITY,
    NDB_PROXIMITY_UNIVERSAL,
    THROW_FLIGHT_TIME,
)
from world.combat.utils import get_display_name_safe
from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity


# ===================================================================
# Object classification helpers
# ===================================================================


def is_explosive(obj):
    """Check if object is explosive."""
    return bool(obj.db.is_explosive)


def is_melee_weapon(obj):
    """Check if object is a melee weapon suitable for deflection."""
    # Melee weapons are those that are NOT ranged (default is melee)
    return not bool(obj.db.is_ranged)


# ===================================================================
# Target selection
# ===================================================================


def select_random_target_in_room(room, exclude=None):
    """Select random character in room for proximity assignment."""
    if not room:
        return None

    # Use typeclass check to distinguish characters (PCs and NPCs)
    # from other objects
    from typeclasses.characters import Character

    characters = [
        obj for obj in room.contents
        if isinstance(obj, Character) and obj != exclude
    ]
    if characters:
        return random.choice(characters)
    return None


def select_most_magnetic_target_in_room(room, grenade, exclude=None):
    """
    Select the most magnetic character in room for sticky grenade
    targeting.

    For sticky grenades thrown without a specific target, this finds
    the character with the highest magnetic armor to stick to.

    Args:
        room: The room to search
        grenade: The sticky grenade being thrown (for magnetic
            strength)
        exclude: Character to skip (typically the thrower)

    Returns:
        Character with highest magnetic armor, or None if no valid
        targets
    """
    if not room:
        return None

    from typeclasses.characters import Character
    from world.combat.utils import get_outermost_armor_at_location

    splattercast = get_splattercast()

    # Get all characters except the excluded one (thrower / triggerer)
    characters = [
        obj for obj in room.contents
        if isinstance(obj, Character) and obj != exclude
    ]
    if not characters:
        return None

    # Get grenade magnetic strength for threshold checks
    magnetic_strength = grenade.db.magnetic_strength if grenade.db.magnetic_strength is not None else 5
    magnetic_threshold = magnetic_strength - 3
    metal_threshold = magnetic_strength - 5

    # Find character with highest magnetic armor that meets thresholds
    best_target = None
    best_magnetic_score = 0

    for char in characters:
        # Check armor at chest (primary target location)
        armor = get_outermost_armor_at_location(char, "chest")

        if not armor:
            continue

        # Get armor properties (including plate carrier check)
        metal_level = armor.db.metal_level or 0
        magnetic_level = armor.db.magnetic_level or 0

        # Check if plate carrier - use installed plates' values
        if bool(armor.db.is_plate_carrier):
            installed_plates = armor.db.installed_plates or {}
            for slot, plate_ref in installed_plates.items():
                if plate_ref:
                    plate_metal = plate_ref.db.metal_level or 0
                    plate_magnetic = plate_ref.db.magnetic_level or 0
                    metal_level = max(metal_level, plate_metal)
                    magnetic_level = max(magnetic_level, plate_magnetic)

        # Check if meets thresholds
        if magnetic_level >= magnetic_threshold and metal_level >= metal_threshold:
            # This target is viable - use magnetic level as score
            if magnetic_level > best_magnetic_score:
                best_magnetic_score = magnetic_level
                best_target = char
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: {char.key} viable with magnetic={magnetic_level}, metal={metal_level}")

    if best_target:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: Selected {best_target.key} (magnetic={best_magnetic_score})")
    else:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: No viable magnetic targets in {room.key}")

    return best_target


# ===================================================================
# Flight lifecycle
# ===================================================================


def start_flight(thrower, obj, destination, target):
    """Stage flight state and start the landing timer.

    The caller (command) is responsible for any origin-room
    announcement and for removing the object from the thrower's
    hands before launch.
    """
    origin = thrower.location

    # Add to room's flying objects - ensure we have a proper list
    flying_objects = getattr(origin.ndb, NDB_FLYING_OBJECTS, None)
    if not isinstance(flying_objects, list):
        flying_objects = []
        setattr(origin.ndb, NDB_FLYING_OBJECTS, flying_objects)
    flying_objects.append(obj)

    # Store flight data on object
    obj.ndb.flight_destination = destination
    obj.ndb.flight_target = target
    obj.ndb.flight_origin = origin
    obj.ndb.flight_thrower = thrower

    # Start flight timer and store reference for potential cancellation
    obj.ndb.flight_timer = utils.delay(THROW_FLIGHT_TIME, complete_flight, obj)

    splattercast = get_splattercast()
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {thrower} started flight for {obj} to {destination}(#{getattr(destination, 'id', '?')})")


def cancel_flight(obj):
    """Clear flight state and cancel the pending landing timer.

    Used by ``catch`` so a caught object doesn't "arrive" (or
    explode) at its old destination after being plucked from the
    air.
    """
    timer = obj.ndb.flight_timer
    if timer is not None:
        try:
            timer.cancel()
        except (AlreadyCalled, AlreadyCancelled):
            pass  # Timer fired or was cancelled in the same tick.
    _clear_flight_state(obj)


def _clear_flight_state(obj):
    """Remove all flight bookkeeping from the object."""
    ndb = getattr(obj, "ndb", None)
    if ndb is None:
        return
    for field in (
        "flight_destination",
        "flight_target",
        "flight_origin",
        "flight_thrower",
        "flight_timer",
    ):
        if getattr(ndb, field, None) is not None:
            delattr(ndb, field)


def get_arrival_direction(origin, destination):
    """Determine arrival direction for announcement."""
    # Simple implementation - would need room connection mapping for
    # accuracy
    return "somewhere"


def complete_flight(obj):
    """Complete the flight and handle landing.

    Runs as a delayed timer callback.  Flight-state cleanup is
    guaranteed via ``finally`` — a bug anywhere in landing resolution
    surfaces in the server log but can never strand the object in
    the "flying" state.
    """
    splattercast = get_splattercast()
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Starting complete_flight for {obj}")

    # Deleted objects lose their ndb handler; caught objects have had
    # their flight state cleared (reads return None).
    if not obj or getattr(obj, "ndb", None) is None:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Object {obj} is None or missing ndb, skipping complete_flight")
        return

    destination = obj.ndb.flight_destination
    target = obj.ndb.flight_target
    origin = obj.ndb.flight_origin
    thrower = obj.ndb.flight_thrower

    if destination is None:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Object {obj} has no flight destination (caught?), skipping complete_flight")
        return

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Flight data - destination: {destination}, target: {target}, origin: {origin}")

    # A successful deflection re-stages flight state for the new
    # trajectory; the finally-cleanup below must not wipe it.
    deflected = False
    try:
        # Clean up origin room flying objects
        if origin is not None and getattr(origin, "ndb", None) is not None:
            origin_flying_objects = getattr(origin.ndb, NDB_FLYING_OBJECTS, None)
            if origin_flying_objects and obj in origin_flying_objects:
                origin_flying_objects.remove(obj)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Removed {obj} from origin flying objects")

        # Move object to destination
        obj.move_to(destination, quiet=True)  # quiet suppresses auto-messages

        # Announce arrival based on room relationship
        if destination != origin:
            # Cross-room throw - announce arrival
            arrival_dir = get_arrival_direction(origin, destination)
            if target and target.location == destination:
                # Send personal message to victim
                target.msg(MSG_THROW_ARRIVAL_TARGETED_VICTIM.format(object=obj.key, direction=arrival_dir))
                # Send observer message to everyone else
                msg_room_identity(
                    location=destination,
                    template=MSG_THROW_ARRIVAL_TARGETED.format(
                        object=obj.key, direction=arrival_dir, target="{target_char}"
                    ),
                    char_refs={"target_char": target},
                    exclude=[target],
                )
            else:
                destination.msg_contents(MSG_THROW_ARRIVAL.format(object=obj.key, direction=arrival_dir))
        else:
            # Same-room throw - show flight message
            if target:
                # Send personal message to victim
                target.msg(MSG_THROW_FLIGHT_SAMEROOM_TARGET_VICTIM.format(object=obj.key))
                # Send observer message to everyone else
                msg_room_identity(
                    location=destination,
                    template=MSG_THROW_FLIGHT_SAMEROOM_TARGET.format(
                        object=obj.key, target="{target_char}"
                    ),
                    char_refs={"target_char": target},
                    exclude=[thrower, target],
                )
            else:
                destination.msg_contents(MSG_THROW_FLIGHT_SAMEROOM_GENERAL.format(object=obj.key), exclude=[thrower])

        # Check for grenade deflection before landing
        if is_explosive(obj):
            if check_grenade_deflection(obj, destination, thrower):
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade was deflected, skipping normal landing")
                deflected = True
                return

        # Handle landing and proximity
        handle_landing(obj, destination, target, thrower)

        # Apply gravity if item landed in a sky room (lazy import —
        # commands package cross-import, resolved at call time)
        from commands.combat.movement import apply_gravity_to_items
        apply_gravity_to_items(destination)
    finally:
        if not deflected:
            _clear_flight_state(obj)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Cleaned up flight data for {obj}")


# ===================================================================
# Landing resolution
# ===================================================================


def handle_landing(obj, destination, target, thrower):
    """Handle object landing and proximity assignment."""
    splattercast = get_splattercast()
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_landing called - obj: {obj}, destination: {destination}, target: {target}")

    # Track whether we've shown a target interaction message
    showed_interaction = False

    # Sticky grenade resolution — the stick/bounce/damage resolver.
    if target and obj.db.is_sticky:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Sticky grenade landing - routing to hit resolution")
        resolve_weapon_hit(obj, target, thrower)
        showed_interaction = True  # Stick/bounce shows its own message

    # Utility object bounce
    elif target:
        # Send personal message to victim
        target.msg(MSG_THROW_UTILITY_BOUNCE_VICTIM.format(object=obj.key))
        # Send observer message to room
        msg_room_identity(
            location=target.location,
            template=MSG_THROW_UTILITY_BOUNCE.format(
                object=obj.key, target="{target_char}"
            ),
            char_refs={"target_char": target},
            exclude=[target],
        )
        showed_interaction = True  # Bounce message already shown

    # Assign proximity for universal proximity system
    assign_landing_proximity(obj, target, thrower)

    # Handle grenade-specific landing
    if is_explosive(obj):
        handle_grenade_landing(obj, target, thrower)

    # General landing announcement - only if no target interaction
    # was shown
    if not showed_interaction:
        if target:
            msg_room_identity(
                location=destination,
                template=MSG_THROW_LANDING_PROXIMITY.format(
                    object=obj.key, target="{target_char}"
                ),
                char_refs={"target_char": target},
            )
        else:
            destination.msg_contents(MSG_THROW_LANDING_ROOM.format(object=obj.key))

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_landing completed")


def resolve_weapon_hit(weapon, target, thrower):
    """Resolve thrown-object hit/miss, stick attempts, and damage.

    Reached via the sticky-grenade landing route (and rigged sticky
    grenades in ``explosion_utils``).
    """
    # Simple hit resolution - could be enhanced with accuracy system
    hit_chance = 0.7  # 70% base hit chance

    if random.random() <= hit_chance:
        # STICKY GRENADE CHECK - Check for stick before damage
        from world.combat.utils import (
            calculate_stick_chance, establish_stick,
            get_outermost_armor_at_location,
        )

        is_sticky = bool(weapon.db.is_sticky)
        hit_location = "chest"  # Default hit location for throws

        if is_sticky:
            splattercast = get_splattercast()
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY: Sticky grenade {weapon.key} hit {target.key}")

            # Get outermost armor at hit location
            armor = get_outermost_armor_at_location(target, hit_location)

            if armor:
                # Calculate stick chance
                stick_chance = calculate_stick_chance(weapon, armor)
                roll = random.randint(1, 100)

                if roll <= stick_chance:
                    # SUCCESS - Grenade sticks to armor
                    if establish_stick(weapon, armor, hit_location):
                        # Send stick messages - Spider-themed with telescoping legs
                        target.msg(f"|rThe {weapon.key}'s articulated legs extend with mechanical precision, their electromagnetic tips skittering across your {armor.key} before *CLAMPING* tight with magnetic fury!|n")
                        thrower.msg(f"Your {weapon.key}'s spider-legs deploy and latch onto {get_display_name_safe(target, thrower)}'s {armor.key} with a satisfying *CLACK-CLACK-CLACK* of magnetic adhesion!")
                        msg_room_identity(
                            location=target.location,
                            template=f"The {weapon.key}'s eight legs telescope outward in a blur of motion, seeking metal across {{target_char}}'s {armor.key} before *SNAPPING* into electromagnetic lock!",
                            char_refs={"target_char": target},
                            exclude=[thrower, target],
                        )

                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_SUCCESS: {weapon.key} stuck to {armor.key} (roll {roll} <= {stick_chance})")

                        # Skip normal landing - grenade is stuck to armor now
                        return
                    else:
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_ERROR: establish_stick failed")
                else:
                    # FAIL - Grenade bounces off
                    target.msg(f"The {weapon.key}'s legs extend and scrabble frantically across your {armor.key}, but the magnetic field is too weak - it bounces away with a frustrated clatter!")
                    thrower.msg(f"Your {weapon.key}'s spider-legs fail to find purchase on {get_display_name_safe(target, thrower)}'s {armor.key}, bouncing off ineffectively!")
                    msg_room_identity(
                        location=target.location,
                        template=f"The {weapon.key}'s articulated legs scrape and skitter across {{target_char}}'s {armor.key} before losing grip and clattering away!",
                        char_refs={"target_char": target},
                        exclude=[thrower, target],
                    )

                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_FAIL: {weapon.key} bounce (roll {roll} > {stick_chance})")
                    # Continue to normal landing
            else:
                # No armor at hit location - bounce off
                target.msg(f"The {weapon.key} strikes your {hit_location} and its legs extend desperately, seeking metal that isn't there - it bounces away with a frustrated whir of servos!")
                thrower.msg(f"Your {weapon.key}'s electromagnetic sensors find no ferrous surface on {get_display_name_safe(target, thrower)}'s {hit_location} - the spider-legs retract as it falls away!")
                msg_room_identity(
                    location=target.location,
                    template=f"The {weapon.key}'s articulated legs extend and search frantically across {{target_char}}'s {hit_location} before retracting in defeat!",
                    char_refs={"target_char": target},
                    exclude=[thrower, target],
                )

                splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_FAIL: No armor at {hit_location}")
                # Continue to normal landing

        # Hit - apply damage (only for non-sticky or failed-stick weapons)
        base_damage = weapon.db.damage if weapon.db.damage is not None else 1
        total_damage = random.randint(1, 6) + base_damage
        damage_type = weapon.db.damage_type if weapon.db.damage_type is not None else 'blunt'

        target.take_damage(total_damage, location="chest", injury_type=damage_type)

        # Send personal message to victim
        target.msg(MSG_THROW_WEAPON_HIT_VICTIM.format(
            thrower=capitalize_first(get_display_name_safe(thrower, target)), weapon=weapon.key))
        # Send personal message to thrower
        thrower.msg(MSG_THROW_WEAPON_HIT.format(weapon=weapon.key, target=get_display_name_safe(target, thrower)))
        # Observer message (everyone else in room)
        msg_room_identity(
            location=target.location,
            template=f"{{actor}}'s {weapon.key} strikes {{target_char}}!",
            char_refs={"actor": thrower, "target_char": target},
            exclude=[thrower, target],
        )

        # Establish proximity if hit (safe pattern)
        proximity_list = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        if not isinstance(proximity_list, list):
            proximity_list = []
            setattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, proximity_list)

        if thrower and thrower not in proximity_list:
            proximity_list.append(thrower)

    else:
        # Miss - send personal message to victim
        target.msg(MSG_THROW_WEAPON_MISS_VICTIM.format(
            thrower=capitalize_first(get_display_name_safe(thrower, target)), weapon=weapon.key))
        # Send personal message to thrower
        thrower.msg(MSG_THROW_WEAPON_MISS.format(weapon=weapon.key, target=get_display_name_safe(target, thrower)))
        # Observer message (everyone else in room)
        msg_room_identity(
            location=target.location,
            template=f"{{actor}}'s {weapon.key} narrowly misses {{target_char}} and clatters to the ground.",
            char_refs={"actor": thrower, "target_char": target},
            exclude=[thrower, target],
        )


def assign_landing_proximity(obj, target, thrower=None):
    """Assign proximity for universal proximity system."""
    splattercast = get_splattercast()
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: assign_landing_proximity called - obj: {obj}, target: {target}, thrower: {thrower}")

    # Ensure object has proximity list (use same pattern as drop command)
    proximity_list = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, None)
    if not isinstance(proximity_list, list):
        proximity_list = []
        setattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, proximity_list)

    if target:
        # Add target to object proximity
        if target not in proximity_list:
            proximity_list.append(target)

        # Inherit target's existing proximity relationships, but
        # exclude the thrower - they shouldn't be in proximity to
        # their own thrown object.  Check both proximity systems:

        # 1. Object proximity system (NDB_PROXIMITY_UNIVERSAL)
        target_proximity = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        if isinstance(target_proximity, list):
            for character in target_proximity:
                if character and character not in proximity_list and character != thrower:
                    proximity_list.append(character)

        # 2. Character proximity system (in_proximity_with)
        character_proximity = getattr(target.ndb, NDB_PROXIMITY, None)
        if character_proximity:
            # Convert set to list for consistent handling
            character_list = list(character_proximity) if hasattr(character_proximity, '__iter__') else []
            for character in character_list:
                if character and character not in proximity_list and character != thrower:
                    proximity_list.append(character)

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: assign_landing_proximity completed: {proximity_list}")


def handle_grenade_landing(grenade, target, thrower=None):
    """Handle grenade-specific landing mechanics."""
    splattercast = get_splattercast()

    # If grenade lands near someone, everyone in their proximity gets
    # added
    target_proximity = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None) if target else None

    if isinstance(target_proximity, list):
        grenade_proximity = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if not isinstance(grenade_proximity, list):
            grenade_proximity = []

        for character in target_proximity:
            # Filter out the thrower - they shouldn't be in proximity
            # to their own thrown grenade
            if character and character not in grenade_proximity and character != thrower:
                grenade_proximity.append(character)

        setattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, grenade_proximity)

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Grenade {grenade} landed with proximity: {getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])}")


# ===================================================================
# Grenade deflection
# ===================================================================


def check_grenade_deflection(grenade, destination, thrower):
    """Check if the specific target can deflect the incoming grenade
    with a melee weapon."""
    splattercast = get_splattercast()

    # Future-proofing: Skip deflection for impact grenades (explode
    # on contact)
    if grenade.db.impact_detonation:
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Impact grenade {grenade} cannot be deflected")
        return False

    # Get the specific target from flight data
    target = getattr(grenade.ndb, 'flight_target', None)
    if not target:
        return False

    # Check if target is in the destination room
    if target.location != destination:
        return False

    # Check if target is grappled or grappling (cannot deflect while
    # restricted)
    handler = getattr(target.ndb, NDB_COMBAT_HANDLER, None)
    if handler:
        combatants_list = handler.db.combatants or []
        combat_entry = next((e for e in combatants_list if e.get(DB_CHAR) == target), None)
        if combat_entry:
            grappled_by = combat_entry.get(DB_GRAPPLED_BY_DBREF)
            grappling = combat_entry.get(DB_GRAPPLING_DBREF)
            if grappled_by or grappling:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Target {target} cannot deflect - grappled_by: {grappled_by}, grappling: {grappling}")
                return False

    # Check if target has hands and a melee weapon
    target_hands = getattr(target, 'hands', None)
    if not target_hands:
        return False

    # Find melee weapon in target's hands
    melee_weapon = None
    for hand, wielded_obj in target_hands.items():
        if wielded_obj and is_melee_weapon(wielded_obj):
            melee_weapon = wielded_obj
            break

    if not melee_weapon:
        return False

    # Perform Motorics skill check for deflection
    from world.combat.utils import roll_stat

    # Roll Motorics skill
    motorics_roll = roll_stat(target, 'motorics')

    # Base difficulty threshold (higher = easier)
    base_threshold = 10  # Moderate difficulty
    weapon_bonus = melee_weapon.db.deflection_bonus if melee_weapon.db.deflection_bonus is not None else 0.0

    # Convert weapon bonus to threshold modifier (0.30 bonus = +6 to
    # threshold)
    threshold_modifier = int(weapon_bonus * 20)
    final_threshold = base_threshold + threshold_modifier

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: {target} Motorics deflection: rolled {motorics_roll} vs threshold {final_threshold}")

    if motorics_roll >= final_threshold:
        # Successful deflection!
        return perform_grenade_deflection(grenade, target, melee_weapon, thrower, destination)
    else:
        # Failed deflection attempt
        target.msg(f"You attempt to deflect the {grenade.key} with your {melee_weapon.key}, but your reflexes aren't quick enough!")
        msg_room_identity(
            location=destination,
            template=f"{{target_char}} swings their {melee_weapon.key} at the incoming {grenade.key} but fails to connect!",
            char_refs={"target_char": target},
            exclude=[target],
        )
        return False


def perform_grenade_deflection(grenade, deflector, weapon, original_thrower, current_location):
    """Perform the actual grenade deflection."""
    splattercast = get_splattercast()

    # Announce successful deflection
    deflector.msg(f"|yYou successfully bat the {grenade.key} away with your {weapon.key}!|n")
    msg_room_identity(
        location=current_location,
        template=f"|y{{actor}} deflects the incoming {grenade.key} with their {weapon.key}!|n",
        char_refs={"actor": deflector},
        exclude=[deflector],
    )

    # Determine deflection target and destination
    if determine_deflection_target(grenade, deflector, original_thrower, current_location):
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade deflection successful, new flight initiated")
        return True

    # Deflection hit but grenade lands in same room
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflection hit but grenade stays in same room")
    handle_landing(grenade, current_location, None, original_thrower)
    return True


def determine_deflection_target(grenade, deflector, original_thrower, current_location):
    """Determine where the deflected grenade goes."""
    splattercast = get_splattercast()

    # Get grenade's original flight data
    origin = getattr(grenade.ndb, 'flight_origin', None)

    # 60% chance to deflect back toward origin/thrower if possible
    # 40% chance to deflect in random direction
    deflect_back_chance = 0.6

    if random.random() <= deflect_back_chance and origin and origin != current_location:
        # Try to deflect back to origin room
        new_destination = origin
        new_target = original_thrower if original_thrower and original_thrower.location == origin else None
        deflection_type = "back toward origin"

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflecting back to origin {origin}")

    else:
        # Deflect in random direction
        available_exits = [obj for obj in current_location.contents
                           if hasattr(obj, 'destination') and obj.destination
                           and obj.destination != current_location]

        if available_exits:
            random_exit = random.choice(available_exits)
            new_destination = random_exit.destination
            new_target = select_random_target_in_room(
                new_destination, exclude=original_thrower
            )
            deflection_type = f"toward {random_exit.key}"

            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflecting to random direction {random_exit.key}")
        else:
            # No exits available, grenade lands in current room
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: No exits available for deflection")
            return False

    # Announce deflection direction
    current_location.msg_contents(
        f"The {grenade.key} ricochets {deflection_type}!"
    )

    # Update flight data and restart flight
    grenade.ndb.flight_destination = new_destination
    grenade.ndb.flight_target = new_target
    grenade.ndb.flight_origin = current_location
    grenade.ndb.flight_thrower = deflector  # Deflector becomes new "thrower"

    # Start new flight with shorter timer (already partially through
    # flight)
    reduced_flight_time = max(1, THROW_FLIGHT_TIME - 1)  # At least 1 second
    grenade.ndb.flight_timer = utils.delay(reduced_flight_time, complete_flight, grenade)

    # Add to current room's flying objects temporarily
    flying_objects = getattr(current_location.ndb, NDB_FLYING_OBJECTS, None)
    if not isinstance(flying_objects, list):
        flying_objects = []
        setattr(current_location.ndb, NDB_FLYING_OBJECTS, flying_objects)
    if grenade not in flying_objects:
        flying_objects.append(grenade)

    splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Deflected {grenade} from {deflector} to {new_destination}")
    return True
