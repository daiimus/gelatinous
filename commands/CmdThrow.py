"""
Throw Command Implementation

Command surface for the throwing system:
- ``throw`` — parsing, validation, origin announcements
- ``pull`` — grenade pin pulling
- ``catch`` — intercepting flying objects

The physics — flight timers, landing resolution, proximity
assignment, grenade deflection — live in ``world/combat/throwing.py``
(issue #471 step 2).  Behavioral contract:
``world/tests/test_throw_characterization.py``.

Part of the G.R.I.M. Combat System.
"""

import random
from evennia import Command
from world.combat.debug import get_splattercast
from world.combat.constants import (
    DB_CHAR,
    DB_GRAPPLED_BY_DBREF,
    DEBUG_PREFIX_THROW,
    MSG_CATCH_FAILED,
    MSG_CATCH_FAILED_ROOM,
    MSG_CATCH_NO_FREE_HANDS,
    MSG_CATCH_NO_HANDS_AT_ALL,
    MSG_CATCH_OBJECT_NOT_FOUND,
    MSG_CATCH_SUCCESS,
    MSG_CATCH_SUCCESS_ROOM,
    MSG_CATCH_WHAT,
    MSG_PULL_ALREADY_PULLED,
    MSG_PULL_INVALID_SYNTAX,
    MSG_PULL_NO_HANDS,
    MSG_PULL_NO_PIN_REQUIRED,
    MSG_PULL_NOT_EXPLOSIVE,
    MSG_PULL_OBJECT_NOT_FOUND,
    MSG_PULL_OBJECT_NOT_WIELDED,
    MSG_PULL_SUCCESS,
    MSG_PULL_SUCCESS_ROOM,
    MSG_PULL_TIMER_WARNING,
    MSG_PULL_WHAT,
    MSG_THROW_GRAPPLED,
    MSG_THROW_INVALID_DIRECTION,
    MSG_THROW_NO_AIM_CROSS_ROOM,
    MSG_THROW_NO_HANDS,
    MSG_THROW_NOTHING_WIELDED,
    MSG_THROW_OBJECT_NOT_FOUND,
    MSG_THROW_OBJECT_NOT_WIELDED,
    MSG_THROW_ORIGIN_DIRECTIONAL,
    MSG_THROW_ORIGIN_FALLBACK,
    MSG_THROW_ORIGIN_HERE,
    MSG_THROW_ORIGIN_TARGETED_CROSS,
    MSG_THROW_ORIGIN_TARGETED_SAME,
    MSG_THROW_SUGGEST_AT_SYNTAX,
    MSG_THROW_TARGET_NOT_FOUND,
    MSG_THROW_TIMER_EXPIRED,
    NDB_AIMING_DIRECTION,
    NDB_COMBAT_HANDLER,
    NDB_COUNTDOWN_REMAINING,
    NDB_FLYING_OBJECTS,
)
from world.combat.throwing import (
    cancel_flight,
    is_explosive,
    select_most_magnetic_target_in_room,
    select_random_target_in_room,
    start_flight,
)
from world.identity_utils import msg_room_identity
from commands._identity_targeting import resolve_character_target


class CmdThrow(Command):
    """
    Throw objects at targets or in directions.

    Usage:
        throw <object>                    # Throw randomly in current room or aimed direction
        throw <object> at <target>        # Throw at specific target (requires aim for cross-room)
        throw <object> to <direction>     # Throw to adjacent room in specified direction
        throw <object> to here            # Throw randomly in current room

    Examples:
        throw knife at bob               # Target Bob in current room or aimed room
        throw grenade to north           # Throw grenade north to adjacent room
        throw keys to here               # Throw keys randomly in current room
        throw rock                       # Throw rock in aimed direction or current room

    The throw command serves dual purposes: utility object transfer and combat weapon
    deployment. Objects with the 'is_throwing_weapon' property are combat weapons —
    targeted throws route through the 'attack' command rather than the utility flight
    path, so weapon throws use full combat resolution.

    Thrown objects have a 2-second flight time and appear in room descriptions during
    flight. Landing creates proximity relationships for grenade mechanics and chain
    reactions.

    Special mechanics:
    - Grenades can be deflected by the TARGET if they're wielding a melee weapon (Motorics skill check)
    - Deflected grenades may bounce back to the thrower or ricochet in random directions
    - Melee weapons with 'deflection_bonus' property modify the deflection difficulty threshold
    - Impact grenades (future feature) cannot be deflected
    """

    key = "throw"
    aliases = ["toss", "hurl"]
    locks = "cmd:all()"
    help_category = "Combat"

    def parse(self):
        """Parse throw command with intelligent syntax detection."""
        self.args = self.args.strip()

        # Initialize parsing results
        self.object_name = None
        self.target_name = None
        self.direction = None
        self.throw_type = None  # 'at_target', 'to_direction', 'to_here', 'fallback'

        if not self.args:
            return

        # Parse for "at" keyword - targeted throwing
        if " at " in self.args:
            parts = self.args.split(" at ", 1)
            if len(parts) == 2:
                self.object_name = parts[0].strip()
                target_part = parts[1].strip()

                # Handle "throw knife at here" -> convert to "throw knife to here"
                if target_part.lower() == "here":
                    self.throw_type = "to_here"
                else:
                    self.target_name = target_part
                    self.throw_type = "at_target"
                return

        # Parse for "to" keyword - directional or here throwing
        if " to " in self.args:
            parts = self.args.split(" to ", 1)
            if len(parts) == 2:
                self.object_name = parts[0].strip()
                target_part = parts[1].strip()

                if target_part.lower() == "here":
                    self.throw_type = "to_here"
                else:
                    # Check if it's a direction or character name
                    self.direction = target_part
                    self.throw_type = "to_direction"
                return

        # Fallback - single object name
        self.object_name = self.args
        self.throw_type = "fallback"

    def func(self):
        """Execute the throw command."""
        if not self.args:
            self.caller.msg("Throw what? Use 'throw <object>' or 'throw <object> at <target>'.")
            return

        # Validate and get the object to throw
        obj = self.get_object_to_throw()
        if not obj:
            return

        # Store object as instance variable for use in determine_destination
        self.obj_to_throw = obj

        # Dedicated throwing weapons use full combat resolution via the
        # attack command — they never take the utility flight path.
        # (Ammo/recovery tracking for thrown weapons is a future
        # feature, alongside gun ammo.)
        if obj.db.is_throwing_weapon:
            if self.target_name:
                self.caller.msg(f"You ready your {obj.key} to attack...")
                # Execute the attack command with the target
                self.caller.execute_cmd(f"attack {self.target_name}")
            else:
                self.caller.msg("Throwing weapons are designed for combat. Use 'attack <target>' to fight, or 'throw <weapon> to <direction/here>' to discard it.")
            return

        # Determine destination and target based on throw type
        destination, target = self.determine_destination()
        if destination is None:
            return

        self.handle_utility_throw(obj, destination, target)

    def get_object_to_throw(self):
        """Validate and return the object to throw."""
        if not self.object_name:
            self.caller.msg(MSG_THROW_NOTHING_WIELDED)
            return None

        # Check if caller has hands (AttributeProperty compatible)
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None:
            self.caller.msg(MSG_THROW_NOTHING_WIELDED)
            return None

        # Check for empty hands dict (no hands at all)
        if not caller_hands:
            self.caller.msg(MSG_THROW_NO_HANDS)
            return None

        # Find object in hands
        obj = None
        for hand, wielded_obj in caller_hands.items():
            if wielded_obj and self.object_name.lower() in wielded_obj.key.lower():
                obj = wielded_obj
                break

        if not obj:
            # Check if object exists but not wielded
            search_obj = self.caller.search(self.object_name, location=self.caller, quiet=True)
            if search_obj:
                self.caller.msg(MSG_THROW_OBJECT_NOT_WIELDED.format(object=self.object_name))
                return None
            else:
                self.caller.msg(MSG_THROW_OBJECT_NOT_FOUND.format(object=self.object_name))
                return None

        # Check for special grenade validation
        if is_explosive(obj):
            if not self.validate_grenade_throw(obj):
                return None

        # Check if caller is grappled
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            combatants_list = handler.db.combatants or []
            combat_entry = next((e for e in combatants_list if e.get(DB_CHAR) == self.caller), None)
            if combat_entry and combat_entry.get(DB_GRAPPLED_BY_DBREF):
                self.caller.msg(MSG_THROW_GRAPPLED)
                return None

        return obj

    def validate_grenade_throw(self, obj):
        """Validate grenade-specific throwing requirements."""
        # Allow unpinned grenades to be thrown as inert objects
        # Players should be able to make tactical mistakes or intentional choices

        # Only check if grenade timer has expired (explosion in hands)
        remaining = getattr(obj.ndb, NDB_COUNTDOWN_REMAINING, None)
        if remaining is not None and remaining <= 0:
            self.caller.msg(MSG_THROW_TIMER_EXPIRED)
            # Apply damage to caller using medical system
            blast_damage = obj.db.blast_damage if obj.db.blast_damage is not None else 10
            damage_type = obj.db.damage_type if obj.db.damage_type is not None else 'blast'
            self.caller.take_damage(blast_damage, location="chest", injury_type=damage_type)
            obj.delete()
            return False

        return True

    def determine_destination(self):
        """Determine destination room and target based on throw type."""
        if self.throw_type == "to_here":
            # Just throw in current room with no specific target
            return self.caller.location, None

        elif self.throw_type == "at_target":
            # Find target in current room or aimed room
            target = self.find_target()
            if not target:
                return None, None
            return target.location, target

        elif self.throw_type == "to_direction":
            # Validate direction and get destination room
            destination = self.get_destination_room(self.direction)
            if not destination:
                return None, None
            return destination, self._pick_room_target(destination)

        elif self.throw_type == "fallback":
            # Use aim state or current room
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, None)
            if aim_direction:
                destination = self.get_destination_room(aim_direction)
                if destination:
                    return destination, self._pick_room_target(destination)

            # Fallback to current room
            return self.caller.location, self._pick_room_target(self.caller.location)

        return None, None

    def _pick_room_target(self, room):
        """Pick the landing target for an untargeted throw.

        Sticky grenades prefer the most magnetic character in the
        room; everything else (and sticky with no viable magnetic
        target) lands near a random occupant.
        """
        obj = getattr(self, "obj_to_throw", None)
        if obj is not None and obj.db.is_sticky:
            target = select_most_magnetic_target_in_room(
                room, obj, exclude=self.caller
            )
            if target:
                return target
        return select_random_target_in_room(room, exclude=self.caller)

    def find_target(self):
        """Find target for 'at' syntax throwing."""
        splattercast = get_splattercast()

        if not self.target_name:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: find_target: No target_name provided")
            return None

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: find_target: Looking for target '{self.target_name}' in {self.caller.location}(#{self.caller.location.id})")

        # First check current room (identity-aware character resolution)
        target = resolve_character_target(self.caller, self.target_name)
        target_hands = getattr(target, 'hands', None) if target else None

        if target and target_hands is not None:  # Is a character with hands attribute
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: find_target: Found valid character target: {target}")
            return target

        # Check aimed room for cross-room targeting
        aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, None)

        if aim_direction:
            destination = self.get_destination_room(aim_direction)
            if destination:
                target = resolve_character_target(
                    self.caller,
                    self.target_name,
                    candidates=destination.contents,
                )
                target_hands = getattr(target, 'hands', None) if target else None
                if target and target_hands is not None:
                    return target
        else:
            # No aim for cross-room targeting
            if not target:
                self.caller.msg(MSG_THROW_NO_AIM_CROSS_ROOM)
                return None

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_FAIL: find_target: No valid target found for '{self.target_name}'")
        self.caller.msg(MSG_THROW_TARGET_NOT_FOUND.format(target=self.target_name))
        return None

    def get_destination_room(self, direction):
        """Get destination room for directional throwing."""
        splattercast = get_splattercast()

        if not direction:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: get_destination_room: No direction provided")
            return None

        # Find exit in current room using standard Evennia patterns
        exit_search = self.caller.search(direction, location=self.caller.location, quiet=True)

        # Handle search result - could be list or single object
        exit_obj = exit_search[0] if exit_search else None

        # Check if we got a valid exit with destination (standard Evennia way)
        if exit_obj and hasattr(exit_obj, 'destination') and exit_obj.destination:
            current_room = self.caller.location
            destination_room = exit_obj.destination

            if current_room == destination_room:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: get_destination_room: Exit {exit_obj} destination points back to same room!")
                self.caller.msg(f"The exit '{direction}' seems to loop back to this room. Cannot throw that way.")
                return None

            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: get_destination_room: Found valid exit {exit_obj} -> {exit_obj.destination}(#{exit_obj.destination.id})")
            return exit_obj.destination

        # If not found or invalid, check if it might be a character name mistaken for direction
        if exit_obj:
            # Use typeclass check to distinguish characters from other objects
            from typeclasses.characters import Character
            if isinstance(exit_obj, Character):
                self.caller.msg(MSG_THROW_SUGGEST_AT_SYNTAX.format(
                    object=self.object_name, target=direction))
                return None

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_FAIL: get_destination_room: Invalid direction '{direction}'")
        self.caller.msg(MSG_THROW_INVALID_DIRECTION.format(direction=direction))
        return None

    def handle_utility_throw(self, obj, destination, target):
        """Launch a utility throw: unhand, announce, start flight."""
        self.remove_from_hand(obj)
        self.announce_throw_origin(obj, destination, target)
        start_flight(self.caller, obj, destination, target)

    def remove_from_hand(self, obj):
        """Remove object from caller's hand.

        PR-H2: ``caller.hands`` is a derived view; mutate a
        snapshot then assign through the setter to persist via
        the held_items backing store.
        """
        caller_hands = dict(getattr(self.caller, 'hands', {}))
        for hand_name, wielded_obj in caller_hands.items():
            if wielded_obj == obj:
                caller_hands[hand_name] = None
                self.caller.hands = caller_hands
                break

    def announce_throw_origin(self, obj, destination, target):
        """Announce throw in origin room."""
        object_name = obj.key
        char_refs = {"actor": self.caller}

        # Determine announcement based on throw type
        if self.throw_type == "to_direction":
            direction = self.direction
            template = MSG_THROW_ORIGIN_DIRECTIONAL.format(
                thrower="{actor}", object=object_name, direction=direction)

        elif self.throw_type == "at_target" and target and target.location == self.caller.location:
            template = MSG_THROW_ORIGIN_TARGETED_SAME.format(
                thrower="{actor}", object=object_name, target="{target_char}")
            char_refs["target_char"] = target

        elif self.throw_type == "at_target" and target:
            # Cross-room targeting
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, "that direction")
            template = MSG_THROW_ORIGIN_TARGETED_CROSS.format(
                thrower="{actor}", object=object_name, direction=aim_direction)

        elif self.throw_type == "to_here":
            template = MSG_THROW_ORIGIN_HERE.format(
                thrower="{actor}", object=object_name)

        else:  # fallback
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, "nearby")
            if aim_direction == "nearby":
                template = MSG_THROW_ORIGIN_HERE.format(
                    thrower="{actor}", object=object_name)
            else:
                template = MSG_THROW_ORIGIN_FALLBACK.format(
                    thrower="{actor}", object=object_name, direction=aim_direction)

        # Broadcast to room using per-observer identity resolution
        msg_room_identity(
            location=self.caller.location,
            template=template,
            char_refs=char_refs,
            exclude=[self.caller],
        )
        self.caller.msg(f"You throw a {object_name}.")


class CmdPull(Command):
    """
    Pull pins on grenades to arm them.

    Usage:
        pull pin on <grenade>

    Examples:
        pull pin on grenade
        pull pin on flashbang

    Pulling the pin on a grenade starts its countdown timer. The grenade must be
    thrown or dropped before the timer expires, or it will explode in your hands.
    """

    key = "pull"
    locks = "cmd:all()"
    help_category = "Combat"

    def parse(self):
        """Parse pull command syntax."""
        self.args = self.args.strip()

        # Expected syntax: "pin on <grenade>"
        if self.args.startswith("pin on "):
            self.grenade_name = self.args[7:].strip()
        else:
            self.grenade_name = None

    def func(self):
        """Execute pull command."""
        if not self.args:
            self.caller.msg(MSG_PULL_WHAT)
            return

        if not self.grenade_name:
            self.caller.msg(MSG_PULL_INVALID_SYNTAX)
            return

        # Check for hands at all
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None or not caller_hands:
            self.caller.msg(MSG_PULL_NO_HANDS)
            return

        # Find grenade in hands
        grenade = None
        for hand, wielded_obj in caller_hands.items():
            if wielded_obj and self.grenade_name.lower() in wielded_obj.key.lower():
                grenade = wielded_obj
                break

        if not grenade:
            # Check if exists but not wielded
            search_obj = self.caller.search(self.grenade_name, location=self.caller, quiet=True)
            if search_obj:
                self.caller.msg(MSG_PULL_OBJECT_NOT_WIELDED.format(object=self.grenade_name))
                return
            else:
                self.caller.msg(MSG_PULL_OBJECT_NOT_FOUND.format(object=self.grenade_name))
                return

        # Validate explosive
        if not grenade.db.is_explosive:
            self.caller.msg(MSG_PULL_NOT_EXPLOSIVE.format(object=grenade.key))
            return

        # Check if requires pin
        requires_pin = grenade.db.requires_pin if grenade.db.requires_pin is not None else True
        if not requires_pin:
            self.caller.msg(MSG_PULL_NO_PIN_REQUIRED.format(object=grenade.key))
            return

        # Check if already pulled
        if grenade.db.pin_pulled:
            self.caller.msg(MSG_PULL_ALREADY_PULLED.format(object=grenade.key))
            return

        # Pull pin and start timer
        self.pull_pin(grenade)

    def pull_pin(self, grenade):
        """Pull the pin and start countdown."""
        # Set pin pulled flag
        grenade.db.pin_pulled = True

        # Get fuse time
        fuse_time = grenade.db.fuse_time if grenade.db.fuse_time is not None else 8

        # Start countdown with the sticky-aware grenade ticker (lives
        # next to the explosion machinery; lazy import preserves the
        # historical commands-module import graph)
        setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)
        from commands.explosion_utils import start_grenade_ticker
        start_grenade_ticker(grenade)

        # Announce
        self.caller.msg(MSG_PULL_SUCCESS.format(object=grenade.key))
        msg_room_identity(
            location=self.caller.location,
            template=MSG_PULL_SUCCESS_ROOM.format(
                puller="{actor}", object=grenade.key
            ),
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )

        # Timer warning
        self.caller.msg(MSG_PULL_TIMER_WARNING.format(object=grenade.key, time=fuse_time))

        splattercast = get_splattercast()
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} pulled pin on {grenade}, timer: {fuse_time}s")


class CmdCatch(Command):
    """
    Catch thrown objects out of the air.

    Usage:
        catch <object>

    Examples:
        catch grenade
        catch knife

    Attempt to catch objects that are currently flying through the air.
    Requires at least one free hand. Useful for catching and re-throwing
    live grenades or intercepting thrown weapons.
    """

    key = "catch"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        """Execute catch command."""
        if not self.args:
            self.caller.msg(MSG_CATCH_WHAT)
            return

        object_name = self.args.strip()

        # Check for hands at all
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None or not caller_hands:
            self.caller.msg(MSG_CATCH_NO_HANDS_AT_ALL)
            return

        # Check for free hands
        free_hand = None
        for hand_name, wielded_obj in caller_hands.items():
            if wielded_obj is None:
                free_hand = hand_name
                break

        if not free_hand:
            self.caller.msg(MSG_CATCH_NO_FREE_HANDS)
            return

        # Find flying object in current room
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, None)
        if not isinstance(flying_objects, list):
            flying_objects = []

        target_obj = None
        for obj in flying_objects:
            if object_name.lower() in obj.key.lower():
                target_obj = obj
                break

        if not target_obj:
            self.caller.msg(MSG_CATCH_OBJECT_NOT_FOUND.format(object=object_name))
            return

        # Attempt catch (simple success/fail)
        catch_chance = 0.6  # 60% base catch chance

        if random.random() <= catch_chance:
            # Success - catch object
            self.catch_object(target_obj, free_hand)
        else:
            # Failure - object continues flight
            self.caller.msg(MSG_CATCH_FAILED.format(object=target_obj.key))
            msg_room_identity(
                location=self.caller.location,
                template=MSG_CATCH_FAILED_ROOM.format(
                    catcher="{actor}", object=target_obj.key
                ),
                char_refs={"actor": self.caller},
                exclude=[self.caller],
            )

    def catch_object(self, obj, hand_name):
        """Successfully catch the object."""
        # Remove from flying objects
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, [])
        if isinstance(flying_objects, list) and obj in flying_objects:
            flying_objects.remove(obj)

        # Move to caller and wield.
        # PR-H2: snapshot + mutate + setter so the held_items
        # backing store persists.
        obj.move_to(self.caller)
        caller_hands = dict(getattr(self.caller, 'hands', {}))
        caller_hands[hand_name] = obj
        self.caller.hands = caller_hands

        # Announce success
        self.caller.msg(MSG_CATCH_SUCCESS.format(object=obj.key))
        observer_template = MSG_CATCH_SUCCESS_ROOM.format(
            catcher="{actor}", object=obj.key
        )
        msg_room_identity(
            location=self.caller.location,
            template=observer_template,
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )

        # Cancel the pending flight timer and clear flight state so
        # the object doesn't "arrive" or explode after being caught
        cancel_flight(obj)

        splattercast = get_splattercast()
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} caught {obj} mid-flight")


# ---------------------------------------------------------------------------
# Backward-compatible re-exports
# ---------------------------------------------------------------------------
# These names were originally defined here but have been extracted to focused
# modules.  Re-exporting them keeps existing ``from commands.CmdThrow import …``
# statements working while consumers are gradually migrated.

from commands.CmdExplosives import (  # noqa: F401 – re-export
    CmdRig,
    CmdDefuse,
    CmdScan,
    CmdDetonate,
    CmdDetonateList,
    CmdClearDetonator,
)

from commands.explosion_utils import (  # noqa: F401 – re-export
    notify_adjacent_rooms_of_explosion,
    check_rigged_grenade,
    start_standalone_grenade_ticker,
    get_unified_explosion_proximity,
    explode_standalone_grenade,
    check_auto_defuse,
    attempt_auto_defuse,
    handle_auto_defuse_success,
    handle_auto_defuse_failure,
    trigger_auto_defuse_explosion,
)
