"""
Jump Combat Command Module

Contains the jump command and the item-landing pipeline:
- CmdJump: Heroic explosive sacrifice, tactical edge descent, and gap jumping
- drop_to_room: the canonical "item lands on the floor" pipeline

The FALL itself is not here. Gravity is a property of the room
(world/gravity.py, #3579): a jump puts you in an air cell and the cell
takes you down the column one cell per tick, rolls the landing, and
charges the damage. This module only decides how you leave the roof.

CmdJump handles three distinct sub-systems:
  1. Explosive sacrifice (jump on <explosive>)
  2. Edge descent with bodyshield mechanics (jump off <direction> edge)
  3. Gap jumping with skill checks (jump across <direction> edge)
"""

from evennia import Command, search_object
from twisted.internet.error import AlreadyCalled, AlreadyCancelled
from evennia.utils.utils import delay

from world.combat.constants import (
    DB_FALLING,
    FALL_BODYSHIELD_MADE_GRAPPLER,
    FALL_BODYSHIELD_MADE_VICTIM,
    FALL_DAMAGE_PER_STORY,
    FALL_EDGE_DIFFICULTY_DEFAULT,
    GAP_DIFFICULTY_DEFAULT,
    NDB_AIRBORNE_TOKEN,
    NDB_COMBAT_HANDLER,
    NDB_COUNTDOWN_REMAINING,
    NDB_GRENADE_TIMER,
    NDB_PROXIMITY_UNIVERSAL,
    NDB_SKIP_ROUND,
)
from world.combat.utils import (
    clear_aim_state,
    get_numeric_stat,
    standard_roll,
    get_display_name_safe,
)
from world.grammar import capitalize_first
from world.gravity import (
    DIRECTION_OPPOSITES,
    NDB_FALL_INTENT,
    NDB_LEAP,
    apply_fall_damage,
    is_sky,
)
from world.identity_utils import msg_room_identity

from world.combat.debug import get_splattercast


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
        splattercast = get_splattercast()
        
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
        # Name the OBJECT to the room, never the string the player typed:
        # `jump on gren` used to broadcast "leaping onto gren!" (#3354).
        from world.grammar import capitalize_first, with_article
        explosive_label = with_article(explosive.key, definite=True)
        Explosive_label = capitalize_first(explosive_label)
        
        # Validate it's an explosive
        if not explosive.db.is_explosive:
            self.caller.msg(f"{explosive.key} is not an explosive device.")
            return
        
        # Check if someone is already jumping on this grenade
        if getattr(explosive.ndb, "sacrifice_in_progress", False):
            # `or`, not a getattr default -- an ndb miss returns None
            # (#2548), which would have put the literal "None" in the line.
            current_hero = (getattr(explosive.ndb, "current_hero", None)
                            or "someone")
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
                    except (AlreadyCalled, AlreadyCancelled):
                        splattercast.msg(f"JUMP_SACRIFICE: Original grenade timer on {explosive.key} already fired/cancelled")
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
                    f"onto {explosive_label} while still holding "
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
                    f"onto {explosive_label}!|n"
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
                
                # Get everyone currently in proximity to the explosive.
                #
                # TWO defects in one line (#2453). It read NDB_PROXIMITY
                # ("in_proximity_with", the COMBAT relationship) while a
                # grenade's blast list lives on NDB_PROXIMITY_UNIVERSAL
                # ("proximity") — two systems with confusingly similar
                # names. And `getattr(obj.ndb, key, default)` NEVER
                # returns the default: Evennia's DbHolder answers None
                # for a missing key, so the `set()` was decoration and
                # the truthiness test below always failed.
                #
                # Net effect: the hero's documented proximity
                # inheritance — the whole point of throwing yourself on
                # a grenade — was a silent no-op every time.
                from world.combat.constants import NDB_PROXIMITY_UNIVERSAL
                explosive_proximity = (
                    getattr(explosive.ndb, NDB_PROXIMITY_UNIVERSAL, None)
                    or [])
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
                            f"|R{Explosive_label} explodes with a "
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
                            f"|R{Explosive_label} explodes with a "
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
                    f"|y...but {explosive_label} makes only a small 'click' sound. It was a dud or the timer expired.|n"
                )
                splattercast.msg(f"JUMP_SACRIFICE_DUD: {self.caller.key} jumped on expired/dud {explosive.key}")
                
            else:
                # Not armed - false heroics
                self.caller.location.msg_contents(
                    f"|y...but nothing happens. {Explosive_label} wasn't even armed.|n"
                )
                splattercast.msg(f"JUMP_SACRIFICE_FALSE: {self.caller.key} jumped on unarmed {explosive.key} - false heroics")
        
        # Schedule the revelation with calculated timing
        delay(revelation_delay, reveal_outcome)
    
    def handle_edge_descent(self):
        """``jump off <dir> edge``. Stepping off always succeeds; what
        happens next is the ROOM's business (#3579): air below and the
        cell's gravity walks you down the column, rolling for the
        landing; solid ground below (a direct drop, no column) and you
        land at once for one storey with no roll."""
        splattercast = get_splattercast()

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

        edge_difficulty = (exit_obj.db.edge_difficulty
                           if exit_obj.db.edge_difficulty is not None
                           else FALL_EDGE_DIFFICULTY_DEFAULT)

        # Captured BEFORE the move -- see #2424: the broadcast below used
        # `previous_location`, which nothing in the repo assigns, so the
        # only line the room they leapt from would have seen never
        # printed. The move is `quiet=True`, so it was silent.
        old_location = self.caller.location

        if not is_sky(destination):
            # DIRECT DROP: no column beneath this edge (clearing an
            # oversailing plate onto the street). One storey, no roll,
            # no traversal. A refused move narrates nothing (#3353).
            # `move_to` answers False on a refused move (escort, channel).
            # The location is NOT re-checked: the cell's hook may already
            # have carried the body onward, and that is not a refusal.
            moved = self.caller.move_to(destination, quiet=True)
            if not moved:
                splattercast.msg(f"JUMP_EDGE_REFUSED_MOVE: {self.caller.key} could not leave {old_location.key}")
                return
            if grappled_victim:
                grappled_victim.move_to(destination, quiet=True)
                grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} drags you off the {self.direction} edge!|n")
                victim_damage, _ = apply_fall_damage(
                    grappled_victim, int(FALL_DAMAGE_PER_STORY * FALL_BODYSHIELD_MADE_VICTIM))
                grappler_damage, _ = apply_fall_damage(
                    self.caller, int(FALL_DAMAGE_PER_STORY * FALL_BODYSHIELD_MADE_GRAPPLER))
                self.caller.msg(f"|gYou use {get_display_name_safe(grappled_victim, self.caller)} to cushion your fall! You take {grappler_damage} damage while they absorb the impact.|n")
                grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} uses you as a bodyshield during the fall! You take {victim_damage} damage!|n")
                splattercast.msg(f"JUMP_EDGE_BODYSHIELD_DIRECT: {self.caller.key} used {grappled_victim.key} as bodyshield in direct fall - victim took {victim_damage}, grappler took {grappler_damage}")
            else:
                dealt, _ = apply_fall_damage(self.caller, FALL_DAMAGE_PER_STORY)
                if dealt > 0:
                    self.caller.msg(f"|rYou land hard and take {dealt} damage from the fall!|n")

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
            if old_location and old_location is not destination:
                msg_room_identity(
                    location=old_location,
                    template=f"|y{{actor}} leaps off the {self.direction} edge!|n",
                    char_refs={"actor": self.caller},
                )
            splattercast.msg(f"JUMP_EDGE_SUCCESS: {self.caller.key} successfully descended via {self.direction} edge to {destination.key}")
            return

        # TRANSIT: hand the air cell's hook the flight plan, then step off.
        # The hook (world.gravity.on_enter_air) starts the fall. A dragged
        # victim goes in FIRST wearing the companion marker, so the cell's
        # hook ignores their arrival (hooks stay ON: posture, followers
        # and presence rosters update as they did before), and rides the
        # leader's record as its companion; if the leader's own move is
        # then refused, the victim is put back on the roof.
        if grappled_victim:
            setattr(grappled_victim.db, DB_FALLING, {"led_by": self.caller})
            if not grappled_victim.move_to(destination, quiet=True):
                grappled_victim.attributes.remove(DB_FALLING)
                grappled_victim = None
        setattr(self.caller.ndb, NDB_FALL_INTENT, {
            "edge_difficulty": edge_difficulty,
            "roll": True,
            "companion": grappled_victim,
        })
        moved = self.caller.move_to(destination, quiet=True)
        if not moved:
            try:
                delattr(self.caller.ndb, NDB_FALL_INTENT)
            except AttributeError:
                pass
            if grappled_victim:
                grappled_victim.attributes.remove(DB_FALLING)
                grappled_victim.move_to(old_location, quiet=True)
            splattercast.msg(f"JUMP_EDGE_REFUSED_MOVE: {self.caller.key} could not leave {old_location.key}")
            return
        if grappled_victim:
            grappled_victim.msg(f"|r{capitalize_first(get_display_name_safe(self.caller, grappled_victim))} drags you off the {self.direction} edge!|n")
            splattercast.msg(f"JUMP_EDGE_BODYSHIELD: {grappled_victim.key} rides {self.caller.key}'s fall")

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
        if old_location and old_location is not destination:
            msg_room_identity(
                location=old_location,
                template=f"|y{{actor}} leaps off the {self.direction} edge!|n",
                char_refs={"actor": self.caller},
            )

        splattercast.msg(f"JUMP_EDGE_AIRBORNE: {self.caller.key} jumped off {self.direction} edge into {destination.key}")

    def handle_gap_jump(self):
        """``jump across <dir> edge``. The roll happens at takeoff. A made
        roll carries a one-tick stay-up token into the air cell and lands
        on the far perch next tick (#3579); a failed roll enters the cell
        with no token and the cell's gravity takes over. A gap whose far
        perch no longer exists is refused on the roof (#3559)."""
        splattercast = get_splattercast()

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

        # The far perch. A raw dbref that no longer resolves is REFUSED
        # here rather than silently swapped for the air cell (#3559).
        destination = self.resolve_gap_destination(exit_obj)
        if destination is None:
            self.caller.msg(f"The {self.direction} gap doesn't lead anywhere safe to land.")
            splattercast.msg(f"JUMP_GAP_NO_PERCH: exit #{exit_obj.id} gap_destination={exit_obj.db.gap_destination!r} does not resolve")
            return

        # Gap jumping requires Motorics check vs gap difficulty
        caller_motorics = get_numeric_stat(self.caller, "motorics")
        gap_difficulty = (exit_obj.db.gap_difficulty
                          if exit_obj.db.gap_difficulty is not None
                          else GAP_DIFFICULTY_DEFAULT)

        motorics_roll, _, _ = standard_roll(caller_motorics)
        success = motorics_roll >= gap_difficulty

        splattercast.msg(f"JUMP_GAP: {self.caller.key} motorics:{motorics_roll} vs difficulty:{gap_difficulty}, success:{success}")

        old_location = self.caller.location      # before the move (#2424)
        air = exit_obj.destination

        if not is_sky(air):
            # No air between the two surfaces (a direct step across):
            # a make walks straight to the perch, a miss slips in place.
            if success:
                moved = self.caller.move_to(destination, quiet=True)
                if not moved:
                    return
                self.finalize_successful_gap_jump(destination, old_location)
            else:
                self.handle_fall_failure(exit_obj, destination, "gap jump")
            return

        if success:
            setattr(self.caller.ndb, NDB_AIRBORNE_TOKEN, 1)
            setattr(self.caller.ndb, NDB_LEAP, {
                "destination": destination,
                "finish": lambda perch: self.finalize_successful_gap_jump(perch, old_location),
            })
            moved = self.caller.move_to(air, quiet=True)
            if not moved:
                for key in (NDB_AIRBORNE_TOKEN, NDB_LEAP):
                    try:
                        delattr(self.caller.ndb, key)
                    except AttributeError:
                        pass
                return
            if handler:
                handler.remove_combatant(self.caller)
            clear_aim_state(self.caller)
            if old_location:
                msg_room_identity(
                    location=old_location,
                    template=f"|y{{actor}} leaps across the {self.direction} gap!|n",
                    char_refs={"actor": self.caller},
                )
            self.caller.msg(f"|CYou soar through the air across the {self.direction} gap...|n")
            return

        # Failed jump: no token, the cell's gravity takes over.
        setattr(self.caller.ndb, NDB_FALL_INTENT, {"roll": False})
        moved = self.caller.move_to(air, quiet=True)
        if not moved:
            try:
                delattr(self.caller.ndb, NDB_FALL_INTENT)
            except AttributeError:
                pass
            return
        if handler:
            handler.remove_combatant(self.caller)
        clear_aim_state(self.caller)
        if old_location and old_location is not air:
            msg_room_identity(
                location=old_location,
                template=f"|r{{actor}} attempts to leap across the {self.direction} gap but falls short!|n",
                char_refs={"actor": self.caller},
            )
        self.caller.msg(f"|rYou leap for the {self.direction} gap but don't make it far enough... you're falling!|n")
        splattercast.msg(f"JUMP_GAP_FAIL: {self.caller.key} fell short into {air.key}")

    @staticmethod
    def resolve_gap_destination(exit_obj):
        """The room a made leap lands on: ``gap_destination`` (a dbref or
        an object), else the exit's own destination when that is not air.
        ``None`` when nothing usable exists."""
        raw = exit_obj.db.gap_destination
        if raw:
            if isinstance(raw, (str, int)):
                found = search_object(f"#{raw}")
                room = found[0] if found else None
            else:
                room = raw if getattr(raw, "pk", None) else None
            return room if room is not None and not is_sky(room) else None
        dest = exit_obj.destination
        if dest is not None and not is_sky(dest):
            return dest
        return None

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

    def finalize_successful_gap_jump(self, destination, origin_room):
        """Finalize successful gap jump with cleanup and messaging."""
        splattercast = get_splattercast()

        # Clear combat state if fleeing via gap
        handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER, None)
        if handler:
            handler.remove_combatant(self.caller)

        # Clear aim states
        clear_aim_state(self.caller)

        # Find the return edge from destination back to origin and check for rigged grenades
        if origin_room:
            # For gap jumps, the return edge is the one keyed the opposite way
            opposite_direction = self.get_opposite_direction(self.direction)
            for obj in destination.contents:
                if not (hasattr(obj, 'key') and hasattr(obj, 'destination') and obj.db.is_edge):
                    continue
                key_matches = obj.key.lower() == opposite_direction
                aliases_match = False
                if hasattr(obj, 'aliases') and obj.aliases:
                    aliases_match = any(alias.lower() == opposite_direction for alias in obj.aliases.all())
                if key_matches or aliases_match:
                    # Found return edge - check for rigged grenades
                    from commands.explosion_utils import check_rigged_grenade
                    check_rigged_grenade(self.caller, obj)
                    break
        else:
            splattercast.msg("JUMP_GAP_DEBUG: no origin room found for this gap")

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
        return DIRECTION_OPPOSITES.get(direction.lower(), direction)

    def handle_fall_failure(self, exit_obj, destination, fall_type, grappled_victim=None):
        """A missed leap with no air between the surfaces: slip and crash
        back down where you stood, one storey's worth."""
        splattercast = get_splattercast()

        dealt, _ = apply_fall_damage(self.caller, FALL_DAMAGE_PER_STORY)

        # Skip turn due to failed attempt
        setattr(self.caller.ndb, NDB_SKIP_ROUND, True)

        # Failure messages
        self.caller.msg(f"|rYou slip during your {fall_type} attempt and take {dealt} damage from the awkward landing!|n")
        msg_room_identity(
            location=self.caller.location,
            template=f"|r{{actor}} slips during a {fall_type} attempt and crashes back down!|n",
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )

        splattercast.msg(f"JUMP_FALL_FAIL: {self.caller.key} failed {fall_type}, took {dealt} damage, remained in {self.caller.location.key}")


def drop_to_room(item, room):
    """Canonical "item lands on the ground" pipeline.

    Performs the two physical effects that should happen whenever an
    item ends up on the floor of a room, regardless of *why*:

    1. Physical relocation via ``item.move_to(room, quiet=True)`` with
       hooks ON -- if ``room`` is an air cell, the cell's own gravity
       (:func:`world.gravity.on_enter_air`, #3579) takes the item down
       the column one cell at a time from there.
    2. Proximity tracking via ``NDB_PROXIMITY_UNIVERSAL`` so the item
       participates correctly in combat / throw / grappling distance
       checks at its resting location (a fall resets it per cell).

    This helper deliberately does **not** emit player-facing messages.
    Each caller has its own narrative context -- a player ``drop``
    command says "you drop the shiv", a sever pipeline says "the
    shiv slips from her severed hand", a thrown-grenade resolution
    says "the grenade clatters to the floor".  Centralising the
    physics here lets each call site own the prose.

    Args:
        item: The object that should end up in ``room``.
        room: The destination room (typically the actor's current
            ``location``).
    """
    item.move_to(room, quiet=True)

    # Universal proximity assignment so the item participates in
    # combat / throw / grappling proximity checks at its new
    # resting location.  Mirrors the assignment block previously
    # inlined in CmdDrop.
    proximity_list = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
    if proximity_list is None:
        proximity_list = []
        setattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, proximity_list)
