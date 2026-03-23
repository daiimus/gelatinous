"""
Jump Combat Command Module

Contains the jump command and gravity utilities for tactical movement:
- CmdJump: Heroic explosive sacrifice, tactical edge descent, and gap jumping
- apply_gravity_to_items: Gravity system for items in sky rooms

Extracted from movement.py as part of Phase 5 decomposition.
CmdJump handles three distinct sub-systems:
  1. Explosive sacrifice (jump on <explosive>)
  2. Edge descent with bodyshield mechanics (jump off <direction> edge)
  3. Gap jumping with skill checks (jump across <direction> edge)
"""

from evennia import Command, search_object
from evennia.utils.utils import delay
from evennia.comms.models import ChannelDB

from world.combat.constants import (
    NDB_COMBAT_HANDLER,
    NDB_COUNTDOWN_REMAINING,
    NDB_GRENADE_TIMER,
    SPLATTERCAST_CHANNEL,
    NDB_PROXIMITY,
    NDB_SKIP_ROUND,
)
from world.combat.utils import (
    clear_aim_state,
    get_numeric_stat,
    standard_roll,
    get_display_name_safe,
)
from world.combat.handler import get_or_create_combat
from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity

# Module-level cache for the Splattercast debug channel
_splattercast_cache = None


def _get_splattercast():
    """Return the cached Splattercast channel, fetching once from DB."""
    global _splattercast_cache
    if _splattercast_cache is None:
        _splattercast_cache = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    return _splattercast_cache


class CmdJump(Command):
    """
    Perform heroic explosive sacrifice or tactical descent/gap jumping.

    Usage:
      jump on <explosive>           # Heroic sacrifice - absorb explosive damage
      jump off <direction> edge     # Tactical descent from elevated position  
      jump across <direction> edge  # Horizontal leap across gaps at same level

    Examples:
      jump on grenade              # Absorb grenade blast to protect others
      jump off north edge          # Descend from rooftop/balcony to north
      jump across east edge        # Leap across gap to the east

    The jump command serves heroic and tactical functions. Jumping on explosives
    provides complete protection to others in proximity at the cost of taking all
    damage yourself. Edge jumping allows vertical descent from elevated positions
    or horizontal gap crossing with risk/reward mechanics.

    All edge jumps require Motorics skill checks and may result in falling if failed.
    Explosive sacrifice is instant and always succeeds but consumes your life for others.
    """
    
    key = "jump"
    locks = "cmd:all()"
    help_category = "Combat"

    DIRECTION_OPPOSITES = {
        "north": "south", "n": "s",
        "south": "north", "s": "n",
        "east": "west", "e": "w",
        "west": "east", "w": "e",
        "northeast": "southwest", "ne": "sw",
        "northwest": "southeast", "nw": "se",
        "southeast": "northwest", "se": "nw",
        "southwest": "northeast", "sw": "ne",
        "up": "down", "u": "d",
        "down": "up", "d": "u",
    }
    
    def parse(self):
        """Parse jump command with syntax detection."""
        self.args = self.args.strip()
        
        # Initialize parsing results
        self.explosive_name = None
        self.direction = None
        self.jump_type = None  # 'on_explosive', 'off_edge', 'across_gap'
        
        if not self.args:
            return
        
        # Parse for "on" keyword - explosive sacrifice
        if self.args.startswith("on "):
            parts = self.args.split(" ", 1)
            if len(parts) == 2:
                self.explosive_name = parts[1].strip()
                self.jump_type = "on_explosive"
                return
        
        # Parse for "off" keyword - tactical descent
        if self.args.startswith("off "):
            parts = self.args.split(" ", 1)
            if len(parts) == 2:
                direction_part = parts[1].strip()
                if direction_part.endswith(" edge"):
                    self.direction = direction_part[:-5].strip()  # Remove " edge"
                    self.jump_type = "off_edge"
                    return
        
        # Parse for "across" keyword - gap jumping
        if self.args.startswith("across "):
            parts = self.args.split(" ", 1)
            if len(parts) == 2:
                direction_part = parts[1].strip()
                if direction_part.endswith(" edge"):
                    self.direction = direction_part[:-5].strip()  # Remove " edge"
                    self.jump_type = "across_gap"
                    return
    
    def func(self):
        """Execute the jump command."""
        if not self.args:
            self.caller.msg("Jump how? Use 'jump on <explosive>', 'jump off <direction> edge', or 'jump across <direction> edge'.")
            return
        
        if self.jump_type == "on_explosive":
            self.handle_explosive_sacrifice()
        elif self.jump_type == "off_edge":
            self.handle_edge_descent()
        elif self.jump_type == "across_gap":
            self.handle_gap_jump()
        else:
            self.caller.msg("Invalid jump syntax. Use 'jump on <explosive>', 'jump off <direction> edge', or 'jump across <direction> edge'.")
    
    def handle_explosive_sacrifice(self):
        """Handle jumping on explosive for heroic sacrifice."""
        splattercast = _get_splattercast()
        
        # Check if caller is being grappled (can't sacrifice while restrained)
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            combatants_list = handler.db.combatants or []
            caller_entry = next((e for e in combatants_list if e.get("char") == self.caller), None)
            if caller_entry:
                from world.combat.grappling import get_grappled_by
                grappler = get_grappled_by(handler, caller_entry)
                if grappler:
                    self.caller.msg(f"|rYou cannot perform heroic sacrifices while being grappled by {get_display_name_safe(grappler, self.caller)}!|n")
                    splattercast.msg(f"JUMP_SACRIFICE_BLOCKED: {self.caller.key} attempted sacrifice while grappled by {grappler.key}")
                    return
        
        if not self.explosive_name:
            self.caller.msg("Jump on what explosive?")
            return
        
        # Find explosive in current room
        explosive = self.caller.search(self.explosive_name, location=self.caller.location, quiet=True)
        if not explosive:
            self.caller.msg(f"You don't see '{self.explosive_name}' here.")
            return
        
        explosive = explosive[0]  # Take first match
        
        # Validate it's an explosive
        if not explosive.db.is_explosive:
            self.caller.msg(f"{explosive.key} is not an explosive device.")
            return
        
        # Check if someone is already jumping on this grenade
        if getattr(explosive.ndb, "sacrifice_in_progress", False):
            current_hero = getattr(explosive.ndb, "current_hero", "someone")
            if hasattr(current_hero, 'key'):
                hero_name = get_display_name_safe(current_hero, self.caller)
            else:
                hero_name = str(current_hero)
            self.caller.msg(f"{explosive.key} is already being heroically tackled by {hero_name}!")
            return
        
        # Claim the grenade for this hero
        explosive.ndb.sacrifice_in_progress = True
        explosive.ndb.current_hero = self.caller
        
        # Determine explosive state for delayed revelation
        is_armed = explosive.db.pin_pulled
        remaining_time = getattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, None)
        has_active_countdown = remaining_time is not None and remaining_time > 0
        
        # Always allow the heroic leap - false heroics are part of the drama!
        
        splattercast.msg(f"JUMP_SACRIFICE: {self.caller.key} attempting heroic sacrifice on {explosive.key} (armed:{is_armed}, countdown:{remaining_time}).")
        
        # Calculate revelation timing - hybrid approach
        if is_armed and has_active_countdown:
            # For real grenades, use remaining time but ensure dramatic minimum
            if remaining_time <= 2.5:
                revelation_delay = max(remaining_time - 0.3, 0.5)  # Beat the timer with safety margin
                splattercast.msg(f"JUMP_SACRIFICE: Using urgent timing: {revelation_delay}s (grenade: {remaining_time}s)")
            else:
                revelation_delay = 2.5  # Full dramatic timing for longer fuses
                splattercast.msg(f"JUMP_SACRIFICE: Using dramatic timing: {revelation_delay}s (grenade: {remaining_time}s)")
        else:
            # For false heroics/duds, always use full dramatic timing
            revelation_delay = 2.5
            splattercast.msg(f"JUMP_SACRIFICE: Using dramatic timing for non-live explosive: {revelation_delay}s")
        
        # Stop the grenade timer immediately to prevent race conditions
        if is_armed and has_active_countdown:
            # Cancel delay timers stored in NDB (prevent original timer from firing)
            if hasattr(explosive.ndb, NDB_GRENADE_TIMER):
                timer = getattr(explosive.ndb, NDB_GRENADE_TIMER, None)
                if timer:
                    try:
                        timer.cancel()  # Cancel the utils.delay timer
                        splattercast.msg(f"JUMP_SACRIFICE: Cancelled original grenade timer on {explosive.key}")
                    except Exception:
                        splattercast.msg(f"JUMP_SACRIFICE: Failed to cancel original grenade timer on {explosive.key}")
                delattr(explosive.ndb, NDB_GRENADE_TIMER)
            
            # Stop any timer scripts
            for script in explosive.scripts.all():
                if "timer" in script.key.lower() or "countdown" in script.key.lower() or "grenade" in script.key.lower():
                    script.stop()
                    splattercast.msg(f"JUMP_SACRIFICE: Stopped timer script {script.key} on {explosive.key}")
        
        # Mark the hero as performing sacrifice (for movement restrictions)
        self.caller.ndb.performing_sacrifice = True
        
        # Check if hero is grappling someone for initial messaging
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        grappled_victim_preview = None
        if handler:
            combatants_list = handler.db.combatants or []
            caller_entry = next((e for e in combatants_list if e.get("char") == self.caller), None)
            if caller_entry:
                from world.combat.grappling import get_grappling_target
                grappled_victim_preview = get_grappling_target(handler, caller_entry)
        
        # Immediate dramatic messaging - hint at the grappling situation
        if grappled_victim_preview and grappled_victim_preview.location == self.caller.location:
            msg_room_identity(
                location=self.caller.location,
                template=(
                    "|R{actor} makes the ultimate sacrifice, leaping "
                    f"onto {self.explosive_name} while still holding "
                    "{victim}!|n"
                ),
                char_refs={
                    "actor": self.caller,
                    "victim": grappled_victim_preview,
                },
            )
        else:
            msg_room_identity(
                location=self.caller.location,
                template=(
                    "|R{actor} makes the ultimate sacrifice, leaping "
                    f"onto {self.explosive_name}!|n"
                ),
                char_refs={"actor": self.caller},
            )
        
        # Get blast damage for real explosions
        blast_damage = explosive.db.blast_damage if explosive.db.blast_damage is not None else 10
        
        # Delayed revelation function
        def reveal_outcome():
            # Clear the sacrifice lock and hero state first (important for error cases)
            if hasattr(explosive.ndb, "sacrifice_in_progress"):
                delattr(explosive.ndb, "sacrifice_in_progress")
            if hasattr(explosive.ndb, "current_hero"):
                delattr(explosive.ndb, "current_hero")
            if hasattr(self.caller.ndb, "performing_sacrifice"):
                delattr(self.caller.ndb, "performing_sacrifice")
            
            if is_armed and has_active_countdown:
                # REAL HEROIC SACRIFICE WITH CRUEL GRAPPLING MECHANICS
                
                # Check if hero is grappling someone - implement human shield mechanics
                handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
                grappled_victim = None
                shield_used = False
                
                if handler:
                    combatants_list = handler.db.combatants or []
                    caller_entry = next((e for e in combatants_list if e.get("char") == self.caller), None)
                    if caller_entry:
                        from world.combat.grappling import get_grappling_target
                        grappled_victim = get_grappling_target(handler, caller_entry)
                
                if grappled_victim and grappled_victim.location == self.caller.location:
                    # CRUEL REALISM: Hero uses grappled victim as blast shield
                    shield_used = True
                    
                    # Send cruel shield messages
                    self.caller.msg(f"|RYou instinctively use {get_display_name_safe(grappled_victim, self.caller)} to shield yourself from the blast!|n")
                    grappled_victim.msg(f"|RYou are forced between {capitalize_first(get_display_name_safe(self.caller, grappled_victim))} and the explosion!|n")
                    msg_room_identity(
                        location=self.caller.location,
                        template=(
                            "|R{actor} uses {victim} as a human shield "
                            "against their own 'heroic' sacrifice!|n"
                        ),
                        char_refs={
                            "actor": self.caller,
                            "victim": grappled_victim,
                        },
                        exclude=[self.caller, grappled_victim],
                    )
                    
                    # Cruel damage distribution using medical system
                    victim_alive_before = not grappled_victim.is_dead()
                    explosive_damage_type = explosive.db.damage_type if explosive.db.damage_type is not None else "blast"
                    grappled_victim.take_damage(blast_damage * 2, location="chest", injury_type=explosive_damage_type)  # Victim takes double damage from shrapnel
                    victim_alive_after = not grappled_victim.is_dead()
                    
                    # Hero damage - currently set to 0 for maximum cruelty (adjustable)
                    hero_damage_multiplier = 0.0  # Change this to increase hero damage if desired
                    hero_damage = int(blast_damage * hero_damage_multiplier)
                    if hero_damage > 0:
                        self.caller.take_damage(hero_damage, location="chest", injury_type=explosive_damage_type)
                    
                    # Check if victim died and add guilt messaging
                    if not victim_alive_after and victim_alive_before:
                        self.caller.msg(f"|RYour 'heroic' sacrifice just killed {get_display_name_safe(grappled_victim, self.caller)}... some hero you are.|n")
                        splattercast.msg(f"JUMP_SACRIFICE_VICTIM_DEATH: {grappled_victim.key} died from blast shield damage caused by {self.caller.key}")
                    
                    splattercast.msg(f"JUMP_SACRIFICE_CRUEL: {self.caller.key} used {grappled_victim.key} as blast shield - victim took {blast_damage * 2}, hero took {hero_damage}")
                else:
                    # Standard heroic sacrifice: hero takes ALL damage, others protected
                    explosive_damage_type = explosive.db.damage_type if explosive.db.damage_type is not None else "blast"
                    self.caller.take_damage(blast_damage, location="chest", injury_type=explosive_damage_type)
                    splattercast.msg(f"JUMP_SACRIFICE_HEROIC: {self.caller.key} absorbed {blast_damage} damage, protecting all others")
                
                # Move caller to explosive's location and inherit ALL its proximity relationships
                from world.combat.proximity import establish_proximity
                
                # Get everyone currently in proximity to the explosive
                explosive_proximity = getattr(explosive.ndb, NDB_PROXIMITY, set())
                if explosive_proximity:
                    for char in list(explosive_proximity):
                        if char != self.caller and hasattr(char, 'location') and char.location:
                            establish_proximity(self.caller, char)
                            splattercast.msg(f"JUMP_SACRIFICE_PROXIMITY: Established proximity between {self.caller.key} and {char.key}")
                
                # Timer cleanup (any remaining scripts/attributes)
                timer_scripts_stopped = 0
                for script in explosive.scripts.all():
                    if "timer" in script.key.lower() or "countdown" in script.key.lower() or "grenade" in script.key.lower():
                        script.stop()
                        timer_scripts_stopped += 1
                        splattercast.msg(f"JUMP_SACRIFICE: Stopped remaining timer script {script.key} on {explosive.key}")
                
                # Clear explosive's timer attributes
                if hasattr(explosive.ndb, NDB_COUNTDOWN_REMAINING):
                    delattr(explosive.ndb, NDB_COUNTDOWN_REMAINING)
                
                splattercast.msg(f"JUMP_SACRIFICE: Final cleanup - stopped {timer_scripts_stopped} remaining scripts, cleared countdown attributes")
                
                # Prevent chain reactions - explosive is absorbed/explodes
                explosive.delete()
                
                # Revelation message - varies based on whether shield was used
                if shield_used:
                    msg_room_identity(
                        location=self.caller.location,
                        template=(
                            f"|R{self.explosive_name} explodes with a "
                            "deafening blast - {victim} bore the brunt "
                            "while {actor} used them as a shield!|n"
                        ),
                        char_refs={
                            "actor": self.caller,
                            "victim": grappled_victim,
                        },
                    )
                    splattercast.msg(f"JUMP_SACRIFICE_SUCCESS: {self.caller.key} used {grappled_victim.key} as blast shield - victim took {blast_damage * 2}, hero took {hero_damage} (completely shielded)")
                    
                    # Break the grapple after blast (trauma, shock, possible unconsciousness)
                    if handler and grappled_victim:
                        from world.combat.grappling import break_grapple
                        break_grapple(handler, grappler=self.caller, victim=grappled_victim)
                        grappled_victim.msg("|yThe blast throws you clear of your captor's grasp!|n")
                        self.caller.msg("|yThe explosion breaks your hold!|n")
                        splattercast.msg(f"JUMP_SACRIFICE_GRAPPLE_BREAK: Blast broke grapple between {self.caller.key} and {grappled_victim.key}")
                else:
                    msg_room_identity(
                        location=self.caller.location,
                        template=(
                            f"|R{self.explosive_name} explodes with a "
                            "muffled blast - {actor} absorbed the full "
                            "force to protect everyone!|n"
                        ),
                        char_refs={"actor": self.caller},
                    )
                    splattercast.msg(f"JUMP_SACRIFICE_SUCCESS: {self.caller.key} absorbed {blast_damage} damage from {explosive.key}, protecting all others in proximity.")
                
                # Skip turn if in combat (heroic actions have consequences)
                setattr(self.caller.ndb, NDB_SKIP_ROUND, True)
                
            elif is_armed and not has_active_countdown:
                # Armed but expired/dud
                self.caller.location.msg_contents(
                    f"|y...but {self.explosive_name} makes only a small 'click' sound. It was a dud or the timer expired.|n"
                )
                splattercast.msg(f"JUMP_SACRIFICE_DUD: {self.caller.key} jumped on expired/dud {explosive.key}")
                
            else:
                # Not armed - false heroics
                self.caller.location.msg_contents(
                    f"|y...but nothing happens. {self.explosive_name} wasn't even armed.|n"
                )
                splattercast.msg(f"JUMP_SACRIFICE_FALSE: {self.caller.key} jumped on unarmed {explosive.key} - false heroics")
        
        # Schedule the revelation with calculated timing
        delay(revelation_delay, reveal_outcome)
    
    def handle_edge_descent(self):
        """Handle jumping off edge for tactical descent."""
        splattercast = _get_splattercast()
        
        # Initialize grappled_victim variable
        grappled_victim = None
        
        # Check if caller is being grappled (can't jump while restrained)
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            combatants_list = handler.db.combatants or []
            caller_entry = next((e for e in combatants_list if e.get("char") == self.caller), None)
            if caller_entry:
                from world.combat.grappling import get_grappled_by, get_grappling_target
                grappler = get_grappled_by(handler, caller_entry)
                if grappler:
                    self.caller.msg(f"|rYou cannot jump while being grappled by {get_display_name_safe(grappler, self.caller)}!|n")
                    splattercast.msg(f"JUMP_EDGE_BLOCKED: {self.caller.key} attempted edge jump while grappled by {grappler.key}")
                    return
                
                # Check if caller is grappling someone - take them along for the ride
                grappled_victim = get_grappling_target(handler, caller_entry)
                if grappled_victim:
                    self.caller.msg(f"|yYou leap from the {self.direction} edge while dragging {get_display_name_safe(grappled_victim, self.caller)} with you!|n")
                    splattercast.msg(f"JUMP_EDGE_WITH_VICTIM: {self.caller.key} edge jumping while grappling {grappled_victim.key}")
        
        if not self.direction:
            self.caller.msg("Jump off which direction?")
            return
        
        # Find exit in the specified direction
        exit_obj = self.find_edge_exit(self.direction)
        if not exit_obj:
            return
        
        # Validate it's an edge
        if not exit_obj.db.is_edge:
            self.caller.msg(f"The {self.direction} exit is not an edge you can jump from.")
            return
        
        destination = exit_obj.destination
        if not destination:
            self.caller.msg(f"The {self.direction} edge doesn't lead anywhere safe to land.")
            return
        
        # Edge jumping always succeeds at getting off the edge - you're committed!
        # The skill check happens during the fall/landing phase
        
        # Get sky room for the fall transit
        sky_room_id = exit_obj.db.sky_room
        sky_room = None
        
        if sky_room_id:
            # Use global search to find sky room by dbref
            search_results = search_object(f"#{sky_room_id}")
            if search_results:
                sky_room = search_results[0]
                splattercast.msg(f"JUMP_EDGE_SKY: Found sky room {sky_room.key} (#{sky_room_id})")
            else:
                splattercast.msg(f"JUMP_EDGE_NO_SKY: Could not find sky room #{sky_room_id}")
        
        if not sky_room:
            # No sky room configured - direct movement (fallback)
            # Still need to apply fall damage but skip the sky room transit
            self.caller.move_to(destination, quiet=True)
            
            # Move grappled victim along if any and apply bodyshield mechanics
            if grappled_victim:
                grappled_victim.move_to(destination, quiet=True)
                grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} drags you off the {self.direction} edge!|n")
                
                # Apply bodyshield damage even without sky room using medical system
                base_damage = exit_obj.db.fall_damage if exit_obj.db.fall_damage is not None else 8
                victim_damage = max(1, int(base_damage * 1.2))  # Victim takes 120% damage
                grappler_damage = max(1, int(base_damage * 0.3))  # Grappler takes 30% due to bodyshield
                
                grappled_victim.take_damage(victim_damage, location="chest", injury_type="blunt")
                self.caller.take_damage(grappler_damage, location="chest", injury_type="blunt")
                
                self.caller.msg(f"|gYou use {get_display_name_safe(grappled_victim, self.caller)} to cushion your fall! You take {grappler_damage} damage while they absorb the impact.|n")
                grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} uses you as a bodyshield during the fall! You take {victim_damage} damage!|n")
                splattercast.msg(f"JUMP_EDGE_BODYSHIELD_DIRECT: {self.caller.key} used {grappled_victim.key} as bodyshield in direct fall - victim took {victim_damage}, grappler took {grappler_damage}")
            else:
                # Normal fall damage without bodyshield using medical system
                base_damage = exit_obj.db.fall_damage if exit_obj.db.fall_damage is not None else 8
                self.caller.take_damage(base_damage, location="chest", injury_type="blunt")
                self.caller.msg(f"|rYou land hard and take {base_damage} damage from the fall!|n")
            
            # Clear combat state if fleeing via edge
            if handler:
                handler.remove_combatant(self.caller)
                if grappled_victim:
                    handler.remove_combatant(grappled_victim)
            
            # Clear aim states
            clear_aim_state(self.caller)
            
            # Check for rigged grenades at destination
            from commands.explosion_utils import check_rigged_grenade, check_auto_defuse
            check_rigged_grenade(self.caller, exit_obj)
            check_auto_defuse(self.caller)
            
            self.caller.msg(f"|gYou successfully leap from the {self.direction} edge and land safely in {destination.key}!|n")
            splattercast.msg(f"JUMP_EDGE_SUCCESS: {self.caller.key} successfully descended via {self.direction} edge to {destination.key}")
            return
        
        # Jumping off always succeeds - you're airborne now!
        # Allow jump system to move through sky rooms
        self.caller.ndb.jump_movement_allowed = True
        self.caller.move_to(sky_room, quiet=True)
        if hasattr(self.caller.ndb, "jump_movement_allowed"):
            del self.caller.ndb.jump_movement_allowed
        
        # Move grappled victim along if any, but preserve the grapple relationship
        # for bodyshield mechanics during the fall
        if grappled_victim:
            grappled_victim.ndb.jump_movement_allowed = True
            grappled_victim.move_to(sky_room, quiet=True)
            if hasattr(grappled_victim.ndb, "jump_movement_allowed"):
                del grappled_victim.ndb.jump_movement_allowed
            grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} drags you off the {self.direction} edge!|n")
            # Store bodyshield state to survive combat handler cleanup
            self.caller.ndb.bodyshield_victim = grappled_victim
            grappled_victim.ndb.bodyshield_grappler = self.caller
            splattercast.msg(f"JUMP_EDGE_BODYSHIELD: Preserving grapple relationship for bodyshield mechanics during fall")
        
        # Clear combat state immediately (can't fight while falling)
        if handler:
            handler.remove_combatant(self.caller)
            if grappled_victim:
                handler.remove_combatant(grappled_victim)
        
        # Clear aim states
        clear_aim_state(self.caller)
        
        # Auto-defuse check in sky room
        from commands.explosion_utils import check_auto_defuse
        check_auto_defuse(self.caller)
        
        # Initial jump message - you always make it off the edge
        self.caller.msg(f"|yYou leap from the {self.direction} edge and are now falling through the air!|n")
        
        # Message the room they left
        if hasattr(self.caller, 'previous_location') and self.caller.previous_location:
            msg_room_identity(
                location=self.caller.previous_location,
                template=f"|y{{actor}} leaps off the {self.direction} edge!|n",
                char_refs={"actor": self.caller},
            )
        
        splattercast.msg(f"JUMP_EDGE_AIRBORNE: {self.caller.key} successfully jumped off {self.direction} edge, now falling in {sky_room.key}")
        
        # Now handle the fall and landing mechanics
        self.handle_edge_fall_and_landing(exit_obj, destination, grappled_victim)
    
    def handle_gap_jump(self):
        """Handle jumping across gap between same-level areas."""
        splattercast = _get_splattercast()
        
        # Check if caller is being grappled (can't jump while restrained)
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            combatants_list = handler.db.combatants or []
            caller_entry = next((e for e in combatants_list if e.get("char") == self.caller), None)
            if caller_entry:
                from world.combat.grappling import get_grappled_by, get_grappling_target
                grappler = get_grappled_by(handler, caller_entry)
                if grappler:
                    self.caller.msg(f"|rYou cannot jump while being grappled by {get_display_name_safe(grappler, self.caller)}!|n")
                    splattercast.msg(f"JUMP_GAP_BLOCKED: {self.caller.key} attempted gap jump while grappled by {grappler.key}")
                    return
                
                # Check if caller is grappling someone - break grapple for gap jump
                grappled_victim = get_grappling_target(handler, caller_entry)
                if grappled_victim:
                    from world.combat.grappling import break_grapple
                    break_grapple(handler, grappler=self.caller, victim=grappled_victim)
                    self.caller.msg(f"|yYou release your grip on {get_display_name_safe(grappled_victim, self.caller)} to focus on the gap jump!|n")
                    grappled_victim.msg(f"|g{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} releases their grip on you to attempt a gap jump!|n")
                    splattercast.msg(f"JUMP_GAP_GRAPPLE_BREAK: {self.caller.key} broke grapple with {grappled_victim.key} for gap jump")
                    grappled_victim = None
                else:
                    grappled_victim = None
        
        if not self.direction:
            self.caller.msg("Jump across which direction?")
            return
        
        # Find exit in the specified direction
        exit_obj = self.find_edge_exit(self.direction)
        if not exit_obj:
            return
        
        # Validate it's a gap
        if not exit_obj.db.is_gap:
            self.caller.msg(f"The {self.direction} exit is not a gap you can jump across.")
            return
        
        # Determine destination - use gap_destination if set, otherwise use exit destination
        gap_destination_id = exit_obj.db.gap_destination
        if gap_destination_id:
            # Convert gap_destination ID to actual room object
            if isinstance(gap_destination_id, (str, int)):
                gap_dest_rooms = search_object(f"#{gap_destination_id}")
                destination = gap_dest_rooms[0] if gap_dest_rooms else exit_obj.destination
            else:
                destination = gap_destination_id  # Already an object
        else:
            destination = exit_obj.destination
            
        if not destination:
            self.caller.msg(f"The {self.direction} gap doesn't lead anywhere safe to land.")
            return
        
        # Gap jumping requires Motorics check vs gap difficulty
        caller_motorics = get_numeric_stat(self.caller, "motorics")
        gap_difficulty = exit_obj.db.gap_difficulty if exit_obj.db.gap_difficulty is not None else 10  # Default hard difficulty
        
        motorics_roll, _, _ = standard_roll(caller_motorics)
        success = motorics_roll >= gap_difficulty
        
        splattercast.msg(f"JUMP_GAP: {self.caller.key} motorics:{motorics_roll} vs difficulty:{gap_difficulty}, success:{success}")
        
        if success:
            # Successful gap jump
            self.execute_successful_gap_jump(exit_obj, destination)
        else:
            # Failed gap jump - create sky room for transit and fall
            self.handle_gap_jump_failure(exit_obj, destination)
    
    def find_edge_exit(self, direction):
        """Find and validate an exit in the specified direction."""
        # Search for exit by direction name
        exit_obj = self.caller.search(direction, location=self.caller.location, quiet=True)
        
        if not exit_obj:
            self.caller.msg(f"There is no exit to the {direction}.")
            return None
        
        exit_obj = exit_obj[0]  # Take first match
        
        # Verify it's actually an exit with a destination
        if not hasattr(exit_obj, 'destination') or not exit_obj.destination:
            self.caller.msg(f"The {direction} exit doesn't lead anywhere.")
            return None
        
        return exit_obj
    
    def execute_successful_gap_jump(self, exit_obj, destination):
        """Execute a successful gap jump with sky room transit."""
        splattercast = _get_splattercast()
        
        # Get sky room directly from the exit object
        sky_room_id = exit_obj.db.sky_room
        sky_room = None
        
        if sky_room_id:
            # Convert sky_room ID to actual room object
            if isinstance(sky_room_id, (str, int)):
                # Use Evennia's search_object to find by dbref
                sky_rooms = search_object(f"#{sky_room_id}")
                sky_room = sky_rooms[0] if sky_rooms else None
            else:
                sky_room = sky_room_id  # Already an object
        
        if not sky_room:
            # Fallback: direct movement if no sky room configured
            origin_room = self.caller.location
            splattercast.msg(f"JUMP_GAP_NO_SKY: No sky room configured for {self.caller.location.key} -> {destination.key}, using direct movement")
            self.caller.move_to(destination, quiet=True)
            self.finalize_successful_gap_jump(destination, origin_room)
            return
        
        # Store origin room before movement
        origin_room = self.caller.location
        
        # Move to sky room first (transit phase)
        # Allow jump system to move through sky rooms
        self.caller.ndb.jump_movement_allowed = True
        self.caller.move_to(sky_room, quiet=True)
        if hasattr(self.caller.ndb, "jump_movement_allowed"):
            del self.caller.ndb.jump_movement_allowed
        
        # Message the origin room
        if origin_room:
            msg_room_identity(
                location=origin_room,
                template=f"|y{{actor}} leaps across the {self.direction} gap!|n",
                char_refs={"actor": self.caller},
            )
        
        # Brief sky room experience
        self.caller.msg(f"|CYou soar through the air across the {self.direction} gap...|n")
        
        # Delay before landing (simulate transit time)
        def land_successfully():
            if self.caller.location == sky_room:
                # Allow jump system to move out of sky rooms
                self.caller.ndb.jump_movement_allowed = True
                self.caller.move_to(destination, quiet=True)
                if hasattr(self.caller.ndb, "jump_movement_allowed"):
                    del self.caller.ndb.jump_movement_allowed
                self.finalize_successful_gap_jump(destination, origin_room)
        
        # Schedule landing
        delay(2, land_successfully)
    
    def finalize_successful_gap_jump(self, destination, origin_room):
        """Finalize successful gap jump with cleanup and messaging."""
        splattercast = _get_splattercast()
        
        # Clear combat state if fleeing via gap
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            handler.remove_combatant(self.caller)
        
        # Clear aim states
        clear_aim_state(self.caller)
        
        # Find the return edge from destination back to origin and check for rigged grenades
        splattercast.msg(f"JUMP_GAP_DEBUG: Origin room: {origin_room}, destination: {destination}")
        if origin_room:
            # Look for return edge in destination that would lead back toward origin
            # For gap jumps, we need to find the edge that has the opposite direction
            opposite_direction = self.get_opposite_direction(self.direction)
            splattercast.msg(f"JUMP_GAP_DEBUG: Looking for return edge in direction: {opposite_direction}")
            
            # Look for edge with the opposite direction
            for obj in destination.contents:
                splattercast.msg(f"JUMP_GAP_DEBUG: Checking object {obj} with key '{obj.key}' for direction match")
                if hasattr(obj, 'key') and hasattr(obj, 'destination'):
                    # Check if the object's key or any of its aliases match the direction
                    key_matches = obj.key.lower() == opposite_direction
                    aliases_match = False
                    if hasattr(obj, 'aliases') and obj.aliases:
                        aliases_match = any(alias.lower() == opposite_direction for alias in obj.aliases.all())
                    direction_matches = key_matches or aliases_match
                    splattercast.msg(f"JUMP_GAP_DEBUG: Object {obj} direction matches check: {direction_matches} (key: {key_matches}, aliases: {aliases_match})")
                    if obj.db.is_edge is not None:
                        splattercast.msg(f"JUMP_GAP_DEBUG: Object {obj} is_edge: {obj.db.is_edge}")
                if (hasattr(obj, 'key') and hasattr(obj, 'destination') and
                    obj.db.is_edge):
                    # Check if direction matches
                    key_matches = obj.key.lower() == opposite_direction
                    aliases_match = False
                    if hasattr(obj, 'aliases') and obj.aliases:
                        aliases_match = any(alias.lower() == opposite_direction for alias in obj.aliases.all())
                    
                    if key_matches or aliases_match:
                        # Found return edge - check for rigged grenades
                        splattercast.msg(f"JUMP_GAP_DEBUG: Found return edge {obj}, checking for rigged grenades")
                        from commands.explosion_utils import check_rigged_grenade
                        check_rigged_grenade(self.caller, obj)
                        break
        else:
            splattercast.msg(f"JUMP_GAP_DEBUG: No origin room found, previous_location not set")
        
        # Check for auto-defuse opportunities in destination room
        from commands.explosion_utils import check_auto_defuse
        check_auto_defuse(self.caller)
        
        # Success messages
        self.caller.msg(f"|gYou successfully leap across the gap and land safely in {destination.key}!|n")
        msg_room_identity(
            location=self.caller.location,
            template="|y{actor} arrives with a spectacular leap from across the gap.|n",
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )
        
        splattercast.msg(f"JUMP_GAP_SUCCESS: {self.caller.key} successfully crossed gap to {destination.key}")
    
    def get_opposite_direction(self, direction):
        """Get the opposite direction for finding return edges."""
        return self.DIRECTION_OPPOSITES.get(direction.lower(), direction)
    
    def handle_gap_jump_failure(self, exit_obj, destination):
        """Handle failed gap jump with fall consequences."""
        splattercast = _get_splattercast()
        
        # Find or use existing sky room for this gap
        sky_room = self.get_sky_room_for_gap(self.caller.location, destination, self.direction)
        if not sky_room:
            # Fallback: apply damage in current room if no sky room configured
            splattercast.msg(f"JUMP_GAP_FAIL_NO_SKY: No sky room configured for {self.caller.location.key} -> {destination.key}, applying damage in place")
            self.handle_fall_failure(exit_obj, destination, "gap jump")
            return
        
        # Move to sky room first (failed transit)
        # Allow jump system to move through sky rooms
        self.caller.ndb.jump_movement_allowed = True
        self.caller.move_to(sky_room, quiet=True)
        if hasattr(self.caller.ndb, "jump_movement_allowed"):
            del self.caller.ndb.jump_movement_allowed
        
        # Message the origin room
        if hasattr(self.caller, 'previous_location') and self.caller.previous_location:
            msg_room_identity(
                location=self.caller.previous_location,
                template=f"|r{{actor}} attempts to leap across the {self.direction} gap but falls short!|n",
                char_refs={"actor": self.caller},
            )
        
        # Failed jump experience
        self.caller.msg(f"|rYou leap for the {self.direction} gap but don't make it far enough... you're falling!|n")
        
        # Calculate fall damage
        fall_distance = exit_obj.db.fall_distance
        if fall_distance is None:
            # If no fall_distance configured, use gravity system's result
            fall_distance = 1  # Default fallback, will be updated by gravity system
        fall_damage = fall_distance * 5  # 5 damage per room fallen
        
        def handle_fall_landing():
            if self.caller.location == sky_room:
                # Use gravity to find ground level instead of specific fall room
                ground_room, actual_fall_distance = CmdJump.follow_gravity_to_ground(sky_room)
                
                # Update fall damage based on actual distance fallen
                actual_fall_damage = actual_fall_distance * 5  # 5 damage per room fallen
                
                # Move to ground level
                # Allow jump system to move out of sky rooms during gravity fall
                self.caller.ndb.jump_movement_allowed = True
                self.caller.move_to(ground_room, quiet=True)
                if hasattr(self.caller.ndb, "jump_movement_allowed"):
                    del self.caller.ndb.jump_movement_allowed
                
                # Apply fall damage using medical system
                self.caller.take_damage(actual_fall_damage, location="chest", injury_type="blunt")
                
                # Clear combat state (fell out of combat)
                handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
                if handler:
                    handler.remove_combatant(self.caller)
                
                # Clear aim states
                clear_aim_state(self.caller)
                
                # Failure messages
                self.caller.msg(f"|rYou fall {actual_fall_distance} stories and crash into {ground_room.key}, taking {actual_fall_damage} damage!|n")
                msg_room_identity(
                    location=self.caller.location,
                    template="|r{actor} crashes down from above, having failed a gap jump!|n",
                    char_refs={"actor": self.caller},
                    exclude=[self.caller],
                )
                
                splattercast.msg(f"JUMP_GAP_FAIL: {self.caller.key} fell {actual_fall_distance} rooms, took {actual_fall_damage} damage, landed in {ground_room.key}")
        
        # Schedule fall landing
        delay(2, handle_fall_landing)
    
    def handle_fall_failure(self, exit_obj, destination, fall_type, grappled_victim=None):
        """Handle general fall failure (for edge descent failures)."""
        splattercast = _get_splattercast()
        
        # For edge descent failure, apply damage but stay in current room
        fall_damage = exit_obj.db.fall_damage if exit_obj.db.fall_damage is not None else 8  # Default moderate damage
        
        self.caller.take_damage(fall_damage, location="chest", injury_type="blunt")
        
        # Skip turn due to failed attempt
        setattr(self.caller.ndb, NDB_SKIP_ROUND, True)
        
        # Failure messages
        self.caller.msg(f"|rYou slip during your {fall_type} attempt and take {fall_damage} damage from the awkward landing!|n")
        msg_room_identity(
            location=self.caller.location,
            template=f"|r{{actor}} slips during a {fall_type} attempt and crashes back down!|n",
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )
        
        splattercast.msg(f"JUMP_FALL_FAIL: {self.caller.key} failed {fall_type}, took {fall_damage} damage, remained in {self.caller.location.key}")
    
    def get_sky_room_for_gap(self, origin, destination, direction):
        """Get the sky room associated with this gap, checking both directions."""
        splattercast = _get_splattercast()
        
        # First try: look for sky room on the exit from origin
        exit_obj = origin.search(direction, quiet=True)
        splattercast.msg(f"SKY_ROOM_DEBUG: Looking for exit '{direction}' from {origin.key}, found: {exit_obj}")
        
        if exit_obj:
            sky_room_id = exit_obj[0].db.sky_room
            splattercast.msg(f"SKY_ROOM_DEBUG: Exit {exit_obj[0].key} has sky_room: {sky_room_id}")
            
            if sky_room_id:
                # Convert string/int ID to actual room object
                if isinstance(sky_room_id, (str, int)):
                    # Use evennia.search_object to find room by ID
                    sky_room_results = search_object(f"#{sky_room_id}")
                    splattercast.msg(f"SKY_ROOM_DEBUG: Searched for #{sky_room_id}, found: {sky_room_results}")
                    if sky_room_results:
                        sky_room = sky_room_results[0]
                        splattercast.msg(f"SKY_ROOM_DEBUG: Found sky room by ID {sky_room_id}: {sky_room.key} (#{sky_room.id})")
                        return sky_room
                    else:
                        splattercast.msg(f"SKY_ROOM_DEBUG: No sky room found with ID {sky_room_id}")
                else:
                    splattercast.msg(f"SKY_ROOM_DEBUG: Sky room ID is already an object: {sky_room_id}")
                    return sky_room_id  # Already an object
        
        # Second try: check the reverse direction from destination
        reverse_direction = self.DIRECTION_OPPOSITES.get(direction)
        splattercast.msg(f"SKY_ROOM_DEBUG: Trying reverse direction '{reverse_direction}' from {destination.key}")
        
        if reverse_direction:
            reverse_exit = destination.search(reverse_direction, quiet=True)
            splattercast.msg(f"SKY_ROOM_DEBUG: Found reverse exit: {reverse_exit}")
            
            if reverse_exit:
                sky_room_id = reverse_exit[0].db.sky_room
                splattercast.msg(f"SKY_ROOM_DEBUG: Reverse exit {reverse_exit[0].key} has sky_room: {sky_room_id}")
                
                if sky_room_id:
                    # Convert string/int ID to actual room object
                    if isinstance(sky_room_id, (str, int)):
                        # Use evennia.search_object to find room by ID
                        sky_room_results = search_object(f"#{sky_room_id}")
                        splattercast.msg(f"SKY_ROOM_DEBUG: Reverse search for #{sky_room_id}, found: {sky_room_results}")
                        if sky_room_results:
                            sky_room = sky_room_results[0]
                            splattercast.msg(f"SKY_ROOM_DEBUG: Returning reverse sky room {sky_room.key} (#{sky_room.id})")
                            return sky_room
                        else:
                            splattercast.msg(f"SKY_ROOM_DEBUG: No reverse sky room found with ID {sky_room_id}")
                    else:
                        splattercast.msg(f"SKY_ROOM_DEBUG: Reverse sky room ID is already an object: {sky_room_id}")
                        return sky_room_id
        
        splattercast.msg(f"SKY_ROOM_DEBUG: No sky room found for {origin.key} -> {destination.key} direction {direction}")
        return None
    
    def get_fall_room_for_gap(self, intended_destination, exit_obj):
        """Get the fall room for a failed gap jump."""
        # Check if exit specifies a fall room
        fall_room_id = exit_obj.db.fall_room
        if fall_room_id:
            # Convert string/int ID to actual room object
            if isinstance(fall_room_id, (str, int)):
                # Convert to string with # prefix for search
                search_id = f"#{fall_room_id}" if not str(fall_room_id).startswith("#") else str(fall_room_id)
                # Use exit object to search for the room by dbref
                fall_room = exit_obj.search(search_id, global_search=True, quiet=True)
                return fall_room[0] if fall_room else intended_destination
            else:
                return fall_room_id  # Already an object
        
        # Fallback: Use intended destination (soft landing)
        return intended_destination

    def handle_edge_fall_and_landing(self, exit_obj, destination, grappled_victim=None):
        """Handle fall mechanics and landing after jumping off an edge."""
        splattercast = _get_splattercast()
        
        # Check for preserved bodyshield relationship
        bodyshield_victim = getattr(self.caller.ndb, "bodyshield_victim", None)
        if bodyshield_victim and not grappled_victim:
            grappled_victim = bodyshield_victim
            splattercast.msg(f"JUMP_EDGE_BODYSHIELD_RESTORE: Restored bodyshield victim {grappled_victim.key} for fall damage calculation")
        
        # Get fall distance for story counting (stories = fall difficulty multiplier)
        fall_distance = exit_obj.db.fall_distance
        if fall_distance is None:
            # If no fall_distance configured, use default
            fall_distance = 1  # Default 1 story
        base_edge_difficulty = exit_obj.db.edge_difficulty if exit_obj.db.edge_difficulty is not None else 8  # Base difficulty
        
        # Calculate landing difficulty based on fall distance
        # Each story adds difficulty - falling farther = harder to land safely
        landing_difficulty = base_edge_difficulty + (fall_distance * 2)  # +2 per story
        
        # Get fall damage (scaled by fall distance)
        base_fall_damage = exit_obj.db.fall_damage if exit_obj.db.fall_damage is not None else 8  # Base damage
        fall_damage = base_fall_damage * fall_distance  # Scale with distance
        
        splattercast.msg(f"JUMP_EDGE_FALL: {self.caller.key} falling {fall_distance} stories, landing difficulty:{landing_difficulty}, potential damage:{fall_damage}")
        
        # Short delay for fall time (more dramatic with distance)
        fall_time = max(1, fall_distance * 0.5)  # 0.5 seconds per story
        
        def handle_landing():
            # Check for preserved bodyshield relationship at landing time
            bodyshield_victim = getattr(self.caller.ndb, "bodyshield_victim", None)
            actual_grappled_victim = grappled_victim or bodyshield_victim
            
            # Debug: Check what we found
            splattercast.msg(f"JUMP_EDGE_DEBUG: grappled_victim={grappled_victim.key if grappled_victim else 'None'}, bodyshield_victim={bodyshield_victim.key if bodyshield_victim else 'None'}, actual_grappled_victim={actual_grappled_victim.key if actual_grappled_victim else 'None'}")
            
            if bodyshield_victim and not grappled_victim:
                splattercast.msg(f"JUMP_EDGE_BODYSHIELD_RESTORE: Restored bodyshield victim {bodyshield_victim.key} for landing damage and grapple restoration")
            
            # Landing skill check - Motorics vs scaled difficulty
            caller_motorics = get_numeric_stat(self.caller, "motorics")
            motorics_roll, _, _ = standard_roll(caller_motorics)
            success = motorics_roll >= landing_difficulty
            
            splattercast.msg(f"JUMP_EDGE_LANDING: {self.caller.key} motorics:{motorics_roll} vs difficulty:{landing_difficulty}, success:{success}")
            
            # Follow gravity down from sky room to find ground level
            final_destination, actual_fall_distance = CmdJump.follow_gravity_to_ground(destination)
            
            # Update fall damage based on actual distance fallen
            actual_fall_damage = base_fall_damage * actual_fall_distance
            if not success:
                fall_room_id = exit_obj.db.fall_room
                if fall_room_id:
                    if isinstance(fall_room_id, (str, int)):
                        fall_rooms = search_object(f"#{fall_room_id}")
                        if fall_rooms:
                            final_destination = fall_rooms[0]
                            splattercast.msg(f"JUMP_EDGE_FALL_ROOM: {self.caller.key} falling to designated fall room {final_destination.key}")
            
            # Move to final destination
            # Allow jump system to move out of sky rooms during edge descent
            self.caller.ndb.jump_movement_allowed = True
            self.caller.move_to(final_destination, quiet=True)
            if hasattr(self.caller.ndb, "jump_movement_allowed"):
                del self.caller.ndb.jump_movement_allowed
            
            # Move grappled victim too if any
            if actual_grappled_victim:
                actual_grappled_victim.ndb.jump_movement_allowed = True
                actual_grappled_victim.move_to(final_destination, quiet=True)
                if hasattr(actual_grappled_victim.ndb, "jump_movement_allowed"):
                    del actual_grappled_victim.ndb.jump_movement_allowed
            
            # Apply bodyshield damage mechanics if victim present
            if actual_grappled_victim:
                # Bodyshield mechanics: victim takes most damage, grappler gets protection
                if success:
                    # Successful landing - victim still takes more damage due to being used as cushion
                    victim_damage = max(1, int(actual_fall_damage * 0.75))  # Victim takes 75% of damage
                    grappler_damage = max(1, int(actual_fall_damage * 0.25))  # Grappler takes 25% due to bodyshield
                    
                    actual_grappled_victim.take_damage(victim_damage, location="chest", injury_type="blunt")
                    self.caller.take_damage(grappler_damage, location="chest", injury_type="blunt")
                    
                    self.caller.msg(f"|gYou use {get_display_name_safe(actual_grappled_victim, self.caller)} to cushion your landing! You take {grappler_damage} damage while they absorb most of the impact.|n")
                    actual_grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, actual_grappled_victim))} uses you as a bodyshield during the landing! You take {victim_damage} damage from being crushed beneath them!|n")
                    splattercast.msg(f"JUMP_EDGE_BODYSHIELD_SUCCESS: {self.caller.key} used {actual_grappled_victim.key} as bodyshield - victim took {victim_damage}, grappler took {grappler_damage}")
                else:
                    # Failed landing - even worse for victim, grappler still gets some protection
                    victim_damage = int(actual_fall_damage * 1.5)  # Victim takes 150% damage (crushed on impact)
                    grappler_damage = max(1, int(actual_fall_damage * 0.5))  # Grappler takes 50% due to bodyshield
                    
                    actual_grappled_victim.take_damage(victim_damage, location="chest", injury_type="blunt")
                    self.caller.take_damage(grappler_damage, location="chest", injury_type="blunt")
                    
                    self.caller.msg(f"|rYou crash hard but {get_display_name_safe(actual_grappled_victim, self.caller)} cushions your impact! You take {grappler_damage} damage while they are crushed beneath you!|n")
                    actual_grappled_victim.msg(f"|R{capitalize_first(get_display_name_safe(self.caller, actual_grappled_victim))} uses you as a human cushion during the devastating crash! You take {victim_damage} damage from being crushed!|n")
                    splattercast.msg(f"JUMP_EDGE_BODYSHIELD_CRASH: {self.caller.key} used {actual_grappled_victim.key} as bodyshield in crash - victim took {victim_damage}, grappler took {grappler_damage}")
                
                # Clean up bodyshield state
                if hasattr(self.caller.ndb, "bodyshield_victim"):
                    del self.caller.ndb.bodyshield_victim
                if hasattr(actual_grappled_victim.ndb, "bodyshield_grappler"):
                    del actual_grappled_victim.ndb.bodyshield_grappler
                
                # Handle grapple relationship after fall
                victim_alive = not actual_grappled_victim.is_dead()
                grappler_alive = not self.caller.is_dead()
                
                victim_status = "dead" if actual_grappled_victim.is_dead() else "unconscious" if hasattr(actual_grappled_victim, 'medical_state') and actual_grappled_victim.medical_state and actual_grappled_victim.medical_state.is_unconscious() else "alive"
                grappler_status = "dead" if self.caller.is_dead() else "unconscious" if hasattr(self.caller, 'medical_state') and self.caller.medical_state and self.caller.medical_state.is_unconscious() else "alive"
                
                splattercast.msg(f"JUMP_EDGE_SURVIVAL_CHECK: {self.caller.key} status={grappler_status} alive={grappler_alive}, {actual_grappled_victim.key} status={victim_status} alive={victim_alive}")
                
                if victim_alive and grappler_alive:
                    try:
                        splattercast.msg(f"JUMP_EDGE_ATTEMPTING_RESTORATION: Both {self.caller.key} and {actual_grappled_victim.key} survived, restoring grapple")
                        # Both survived - restore grapple relationship in new combat handler
                        
                        # Create new combat handler at landing location (use standalone function, not class method)
                        splattercast.msg(f"JUMP_EDGE_RESTORE_STEP1: Creating new combat handler at {final_destination}")
                        new_handler = get_or_create_combat(final_destination)
                        splattercast.msg(f"JUMP_EDGE_RESTORE_STEP2: Got handler {new_handler}")
                        
                        # Add both characters to combat with initial grapple state (like room traversal)
                        splattercast.msg(f"JUMP_EDGE_RESTORE_STEP3: Adding {self.caller.key} to combat with initial_grappling={actual_grappled_victim.key}")
                        new_handler.add_combatant(
                            self.caller,
                            target=None,  # Grappler is yielding after fall
                            initial_grappling=actual_grappled_victim,  # Set grapple state directly
                            initial_grappled_by=None,
                            initial_is_yielding=True  # Restraint mode after fall
                        )
                        
                        splattercast.msg(f"JUMP_EDGE_RESTORE_STEP4: Adding {actual_grappled_victim.key} to combat with initial_grappled_by={self.caller.key}")
                        new_handler.add_combatant(
                            actual_grappled_victim,
                            target=None,  # Victim has no offensive target after fall
                            initial_grappling=None,
                            initial_grappled_by=self.caller,  # Set grappled state directly
                            initial_is_yielding=False  # Victim can still struggle
                        )
                        
                        splattercast.msg(f"JUMP_EDGE_RESTORE_STEP5: Combat entries created with grapple state")
                        
                        self.caller.msg(f"|yYou maintain your grip on {get_display_name_safe(actual_grappled_victim, self.caller)} after the fall!|n")
                        actual_grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, actual_grappled_victim))} still has you in their grip after that brutal fall!|n")
                        splattercast.msg(f"JUMP_EDGE_GRAPPLE_RESTORED: {self.caller.key} maintains grapple on {actual_grappled_victim.key} after fall survival")
                    except Exception as e:
                        splattercast.msg(f"JUMP_EDGE_RESTORE_ERROR: Failed to restore grapple - {e}")
                        self.caller.msg(f"|rYour grip on {get_display_name_safe(actual_grappled_victim, self.caller)} was lost during the fall!|n")
                    
                elif not victim_alive and grappler_alive:
                    # Victim died from fall - grappler is holding a corpse
                    self.caller.msg(f"|RYou feel {get_display_name_safe(actual_grappled_victim, self.caller)}'s body go limp in your grip - they didn't survive the fall!|n")
                    splattercast.msg(f"JUMP_EDGE_VICTIM_DEATH: {actual_grappled_victim.key} died from bodyshield fall damage - grapple relationship ended")
                    
                elif not grappler_alive and victim_alive:
                    # Grappler died (somehow) - victim is free
                    actual_grappled_victim.msg(f"|gYou feel {get_display_name_safe(self.caller, actual_grappled_victim)}'s grip loosen as they succumb to their injuries!|n")
                    splattercast.msg(f"JUMP_EDGE_GRAPPLER_DEATH: {self.caller.key} died from fall damage - grapple relationship ended")
                    
                else:
                    # Both died - tragic
                    splattercast.msg(f"JUMP_EDGE_DOUBLE_DEATH: Both {self.caller.key} and {actual_grappled_victim.key} died from fall damage")
            else:
                # No bodyshield - normal damage calculation
                if success:
                    # Successful landing - reduced damage
                    reduced_damage = max(1, actual_fall_damage // 3)  # Much less damage on success
                    if reduced_damage > 1:
                        self.caller.take_damage(reduced_damage, location="chest", injury_type="blunt")
                        self.caller.msg(f"|gYou land gracefully but still feel the impact! You take {reduced_damage} damage from the controlled landing.|n")
                        splattercast.msg(f"JUMP_EDGE_SUCCESS_DAMAGE: {self.caller.key} landed successfully, took {reduced_damage} controlled fall damage")
                    else:
                        self.caller.msg(f"|gYou execute a perfect landing with minimal impact!|n")
                        splattercast.msg(f"JUMP_EDGE_PERFECT: {self.caller.key} executed perfect landing, no damage")
                else:
                    # Failed landing - full damage
                    self.caller.take_damage(actual_fall_damage, location="chest", injury_type="blunt")
                    self.caller.msg(f"|rYou crash hard into the ground after falling {actual_fall_distance} {'story' if actual_fall_distance == 1 else 'stories'}! You take {actual_fall_damage} damage!|n")
                    splattercast.msg(f"JUMP_EDGE_CRASH: {self.caller.key} crashed after {actual_fall_distance} story fall, took {actual_fall_damage} damage")
            
            # Arrival messages
            if actual_grappled_victim:
                if success:
                    msg_room_identity(
                        location=self.caller.location,
                        template="|g{actor} lands with {victim} crushed beneath them!|n",
                        char_refs={"actor": self.caller, "victim": actual_grappled_victim},
                        exclude=[self.caller, actual_grappled_victim],
                    )
                else:
                    msg_room_identity(
                        location=self.caller.location,
                        template="|r{actor} crashes down from above with {victim} taking the brunt of the impact!|n",
                        char_refs={"actor": self.caller, "victim": actual_grappled_victim},
                        exclude=[self.caller, actual_grappled_victim],
                    )
            else:
                if success:
                    msg_room_identity(
                        location=self.caller.location,
                        template="|g{actor} lands with athletic grace from above!|n",
                        char_refs={"actor": self.caller},
                        exclude=[self.caller],
                    )
                else:
                    msg_room_identity(
                        location=self.caller.location,
                        template="|r{actor} crashes down from above with a bone-jarring impact!|n",
                        char_refs={"actor": self.caller},
                        exclude=[self.caller],
                    )
            
            # Skip turn due to fall recovery
            setattr(self.caller.ndb, NDB_SKIP_ROUND, True)
            if actual_grappled_victim:
                setattr(actual_grappled_victim.ndb, NDB_SKIP_ROUND, True)
            
            splattercast.msg(f"JUMP_EDGE_COMPLETE: {self.caller.key} completed {actual_fall_distance}-story edge jump to {final_destination.key}")
        
        # Schedule the landing after fall time
        delay(fall_time, handle_landing)

    @staticmethod
    def follow_gravity_to_ground(start_room):
        """
        Follow gravity down from a sky room until hitting ground level.
        Traverses downward exits until finding a room without a down exit,
        or a room marked as ground level.
        
        Args:
            start_room: The room to start falling from.
        
        Returns:
            tuple: (final_room, rooms_fallen)
        """
        splattercast = _get_splattercast()
        current_room = start_room
        rooms_fallen = 0
        max_depth = 10  # Safety limit to prevent infinite loops
        visited = set()
        
        splattercast.msg(f"GRAVITY_FOLLOW: Starting gravity fall from {current_room.key} (#{current_room.id})")
        
        while rooms_fallen < max_depth:
            # Check if this room is marked as ground level
            if current_room.db.is_ground:
                splattercast.msg(f"GRAVITY_GROUND: Found ground room {current_room.key} after {rooms_fallen} rooms")
                return current_room, rooms_fallen
            
            # Track visited rooms to detect any cycle
            visited.add(current_room)
            
            # Look for a down exit
            down_exit = current_room.search("down", quiet=True)
            if not down_exit:
                down_exit = current_room.search("d", quiet=True)
            
            if not down_exit:
                # No down exit found - this is ground level
                splattercast.msg(f"GRAVITY_BOTTOM: No down exit from {current_room.key}, treating as ground after {rooms_fallen} rooms")
                return current_room, rooms_fallen
            
            # Get the destination of the down exit
            next_room = down_exit[0].destination
            if not next_room:
                splattercast.msg(f"GRAVITY_DEAD_END: Down exit from {current_room.key} has no destination, stopping fall")
                return current_room, rooms_fallen
            
            # Check if we've already visited this room (cycle detection)
            if next_room in visited:
                splattercast.msg(f"GRAVITY_LOOP: Detected loop to already-visited {next_room.key}, stopping at {current_room.key}")
                return current_room, rooms_fallen
            
            # Move down one level
            current_room = next_room
            rooms_fallen += 1
            splattercast.msg(f"GRAVITY_FALL: Falling to {current_room.key} (#{current_room.id}), depth: {rooms_fallen}")
        
        # Safety limit reached
        splattercast.msg(f"GRAVITY_LIMIT: Hit max depth limit at {current_room.key}, treating as ground")
        return current_room, rooms_fallen


def apply_gravity_to_items(room):
    """
    Apply gravity to all items in a sky room, causing them to fall to ground level.
    This function can be called from various systems (throw, drop, etc.) to ensure
    items don't remain suspended in sky rooms.
    
    Args:
        room: The room to check for items that need to fall
    """
    splattercast = _get_splattercast()
    
    # Check if this is a sky room
    is_sky_room = room.db.is_sky_room
    if not is_sky_room:
        splattercast.msg(f"GRAVITY_ITEMS: {room.key} is not a sky room, skipping gravity check")
        return  # Nothing to do if not a sky room
    
    splattercast.msg(f"GRAVITY_ITEMS: Checking items in sky room {room.key}")
    
    # Get all items in the room (exclude characters)
    all_objects = list(room.contents)
    splattercast.msg(f"GRAVITY_ITEMS: Found {len(all_objects)} total objects in room")
    
    from typeclasses.items import Item
    from typeclasses.characters import Character
    
    items = []
    for obj in all_objects:
        is_item = isinstance(obj, Item)
        is_character = isinstance(obj, Character)
        splattercast.msg(f"GRAVITY_ITEMS: Object {obj.key} - is_item: {is_item}, is_character: {is_character}")
        
        if is_item and not is_character:
            items.append(obj)
    
    splattercast.msg(f"GRAVITY_ITEMS: Found {len(items)} items to check for gravity")
    
    if not items:
        splattercast.msg(f"GRAVITY_ITEMS: No items found in {room.key}")
        return  # No items to process
    
    # Use the same gravity logic as characters (static method, no instance needed)
    try:
        ground_room, fall_distance = CmdJump.follow_gravity_to_ground(room)
        splattercast.msg(f"GRAVITY_ITEMS: Gravity check result - ground_room: {ground_room.key if ground_room else None}, fall_distance: {fall_distance}")
    except Exception as e:
        splattercast.msg(f"GRAVITY_ITEMS_ERROR: Failed to calculate gravity path: {e}")
        return
    
    if ground_room == room:
        splattercast.msg(f"GRAVITY_ITEMS: {room.key} is already at ground level")
        return
    
    if not ground_room:
        splattercast.msg(f"GRAVITY_ITEMS_ERROR: No ground room found for {room.key}")
        return
    
    # Move each item to ground level
    for item in items:
        try:
            splattercast.msg(f"GRAVITY_ITEMS: Moving {item.key} from {room.key} to {ground_room.key} (fell {fall_distance} levels)")
            item.move_to(ground_room, quiet=True)
            
            # Announce the item falling to the ground room
            ground_room.msg_contents(f"A {item.key} falls from above and lands with a clatter.")
            splattercast.msg(f"GRAVITY_ITEMS: Successfully moved {item.key} to {ground_room.key}")
            
        except Exception as e:
            splattercast.msg(f"GRAVITY_ITEMS_ERROR: Failed to move {item.key}: {e}")
            # Continue with other items even if one fails
