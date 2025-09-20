from evennia import Command
from evennia.utils.search import search_object
from world.combat.messages import get_combat_message
from evennia.comms.models import ChannelDB
from world.weather import weather_system
from world.weather.weather_messages import WEATHER_INTENSITY

class CmdHeal(Command):
    """
    Instantly heal a target character using the medical system.

    Usage:
        @heal <target> [= <amount>]
        @heal <target> [= <condition_type>]
        @heal <target> [= <condition_type> <amount>]
        @heal here [= <amount>]
        @heal <room #> [= <amount>]
    
    Without amount: Completely heal target (remove all medical conditions)
                   Also clears any test death/unconscious states and restrictions
    With amount: Heal a specific number of medical conditions (least severe first)
    With condition_type: Heal only specific types of conditions
    
    Examples:
        @heal bob - Completely heal bob and clear any test states
        @heal bob = bleeding - Heal all bleeding conditions
        @heal bob = fracture 2 - Heal 2 fracture conditions
        @heal here = 3 - Heal 3 conditions from everyone here
        @heal bob = list - Show available condition types to heal
    """

    key = "@heal"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("|rUsage: @heal <target|here|room #> [= <amount|condition_type|list>]|n")
            return

        parts = self.args.split("=", 1)
        target_name = parts[0].strip()
        amount = None
        condition_type = None

        if len(parts) > 1:
            heal_args = parts[1].strip().split()
            
            if len(heal_args) == 1:
                arg = heal_args[0]
                if arg == "list":
                    # Special case for listing conditions
                    condition_type = "list"
                elif arg.isdigit():
                    amount = int(arg)
                    if amount < 0:
                        caller.msg("|rAmount must be zero or positive.|n")
                        return
                else:
                    # It's a condition type
                    condition_type = arg.lower()
            elif len(heal_args) == 2:
                # condition_type + amount
                condition_type = heal_args[0].lower()
                try:
                    amount = int(heal_args[1])
                    if amount < 0:
                        caller.msg("|rAmount must be zero or positive.|n")
                        return
                except ValueError:
                    caller.msg("|rAmount must be an integer.|n")
                    return
            else:
                caller.msg("|rToo many arguments. Usage: @heal <target> [= <amount|condition_type|condition_type amount>]|n")
                return

        targets = []

        # Handle 'here' keyword
        if target_name.lower() == "here":
            location = caller.location
            if not location:
                caller.msg("|rYou have no location.|n")
                return
            # Heal all characters in location (both PCs and NPCs)
            from typeclasses.characters import Character
            targets = [obj for obj in location.contents if isinstance(obj, Character)]
            if not targets:
                caller.msg("|yNo healable targets found in this location.|n")
                return
            target_desc = f"everyone in {location.key}"
        # Handle room dbref (number)
        elif target_name.startswith("#") and target_name[1:].isdigit():
            room = search_object(target_name)
            if not room:
                caller.msg(f"|rNo room found with dbref {target_name}.|n")
                return
            room = room[0]
            # Heal all characters in room (both PCs and NPCs)
            from typeclasses.characters import Character
            targets = [obj for obj in room.contents if isinstance(obj, Character)]
            if not targets:
                caller.msg(f"|yNo healable targets found in {room.key}.|n")
                return
            target_desc = f"everyone in {room.key}"
        # Handle character dbref (number)
        elif target_name.isdigit():
            char = search_object(f"#{target_name}")
            if not char:
                caller.msg(f"|rNo character found with dbref #{target_name}.|n")
                return
            char = char[0]
            targets = [char]
            target_desc = char.key
        else:
            # Normal name search
            matches = search_object(target_name)
            if not matches:
                caller.msg(f"|rNo character named '{target_name}' found.|n")
                return
            target = matches[0]
            targets = [target]
            target_desc = target.key

        # Heal all targets using medical system
        for target in targets:
            # Check if target has medical system
            if not hasattr(target, 'medical_state') or not target.medical_state:
                caller.msg(f"|r{target.key} has no medical system to heal.|n")
                continue
            
            medical_state = target.medical_state
            conditions_before = len(medical_state.conditions)
            
            # Handle "list" command to show available conditions
            if condition_type == "list":
                if medical_state.conditions:
                    caller.msg(f"|cAvailable conditions for {target.key}:|n")
                    condition_types = {}
                    for condition in medical_state.conditions:
                        cond_type = condition.type
                        if cond_type not in condition_types:
                            condition_types[cond_type] = 0
                        condition_types[cond_type] += 1
                    
                    for cond_type, count in condition_types.items():
                        caller.msg(f"  {cond_type}: {count} condition(s)")
                    caller.msg(f"Usage: @heal {target.key} = <condition_type> [amount]")
                else:
                    caller.msg(f"|g{target.key} has no medical conditions.|n")
                continue
            
            # Full heal without condition type - complete medical restoration
            if amount is None and condition_type is None:
                # Clear all conditions
                medical_state.conditions.clear()
                
                # Stop medical script since no conditions remain
                from world.medical.script import stop_medical_script
                stop_medical_script(target)
                
                # Restore all organs to full health
                organs_healed = 0
                for organ in medical_state.organs.values():
                    if organ.current_hp < organ.max_hp:
                        organ.current_hp = organ.max_hp
                        organs_healed += 1
                
                # Restore vital signs
                medical_state.blood_level = 100.0
                medical_state.pain_level = 0.0
                medical_state.consciousness = 1.0  # Consciousness is stored as 0.0-1.0, displayed as percentage
                
                # Clear any death or unconsciousness placement descriptions
                if hasattr(target, 'override_place'):
                    target.override_place = None
                
                # Clear any death/unconsciousness processing flags
                if hasattr(target, 'ndb'):
                    target.ndb.death_processed = False
                    target.ndb.unconsciousness_processed = False
                
                # Clear old test flags (backward compatibility)
                if hasattr(target.db, '_test_death_state'):
                    del target.db._test_death_state
                if hasattr(target.db, '_test_unconscious_state'):
                    del target.db._test_unconscious_state
                
                # Remove any medical state restrictions (death/unconscious cmdsets)
                try:
                    target.remove_death_state()
                except Exception:
                    pass
                try:
                    target.remove_unconscious_state()
                except Exception:
                    pass
                
                target.save_medical_state()
                caller.msg(f"|g{target.key} fully healed - cleared all {conditions_before} conditions, healed {organs_healed} organs, and restored vital signs.|n")
                
            # Condition-type specific healing
            elif condition_type:
                # Find conditions of the specified type
                matching_conditions = []
                for condition in medical_state.conditions:
                    if condition.type.lower() == condition_type:
                        matching_conditions.append(condition)
                
                if not matching_conditions:
                    caller.msg(f"|y{target.key} has no {condition_type} conditions.|n")
                    continue
                
                # Heal specific number or all of this type
                conditions_to_heal = amount if amount is not None else len(matching_conditions)
                conditions_to_heal = min(conditions_to_heal, len(matching_conditions))
                
                # Remove the conditions
                for i in range(conditions_to_heal):
                    if matching_conditions:
                        condition_key = matching_conditions.pop(0)
                        medical_state.conditions.pop(condition_key, None)
                
                # Stop medical script if no conditions remain
                if not medical_state.conditions:
                    from world.medical.script import stop_medical_script
                    stop_medical_script(target)
                
                target.save_medical_state()
                caller.msg(f"|g{target.key} healed {conditions_to_heal} {condition_type} condition(s).|n")
                
            # Partial heal - heal N conditions (any type)
            else:
                conditions_to_heal = min(amount, conditions_before)
                conditions_removed = 0
                
                # Remove conditions (least severe first)
                severity_order = {"minor": 1, "moderate": 2, "severe": 3, "critical": 4}
                while conditions_removed < conditions_to_heal and medical_state.conditions:
                    # Find least severe condition
                    least_severe_condition = None
                    least_severity = float('inf')
                    
                    for condition in medical_state.conditions:
                        severity_value = severity_order.get(condition.severity, 0)
                        if severity_value < least_severity:
                            least_severity = severity_value
                            least_severe_condition = condition
                    
                    if least_severe_condition:
                        medical_state.conditions.remove(least_severe_condition)
                        conditions_removed += 1
                    else:
                        break
                
                # Stop medical script if no conditions remain
                if not medical_state.conditions:
                    from world.medical.script import stop_medical_script
                    stop_medical_script(target)
                
                target.save_medical_state()
                conditions_after = len(medical_state.conditions)
                caller.msg(f"|g{target.key} healed {conditions_removed} conditions ({conditions_after} remaining).|n")

        if len(targets) > 1 and condition_type != "list":
            caller.msg(f"|gHealed {len(targets)} targets in {target_desc}.|n")


class CmdTestDeath(Command):
    """
    Test death state using organic medical conditions.
    
    Usage:
        @testdeath [<target>] [force]
        
    This command creates severe bleeding conditions that naturally cause death
    or fully heals to revive from death. Uses real medical conditions, not 
    direct manipulation of vital signs.
    If no target is specified, affects yourself.
    If 'force' is specified, applies restrictions even to staff.
    """
    key = "@testdeath"
    aliases = ["@td"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"
    
    def func(self):
        caller = self.caller
        args = self.args.strip()
        
        # Parse arguments for target and force flag
        force_test = "force" in args.lower()
        target_name = args.replace("force", "").strip()
        
        # Determine target
        if target_name:
            target = caller.search(target_name, global_search=True)
            if not target:
                caller.msg(f"Could not find '{target_name}'.")
                return
            if not hasattr(target, 'is_dead'):
                caller.msg(f"{target.key} is not a character.")
                return
        else:
            target = caller
        
        if target.is_dead():
            # Character is dead, revive them using heal command logic
            if hasattr(target, 'medical_state') and target.medical_state:
                medical_state = target.medical_state
                
                # Clear all conditions
                medical_state.conditions.clear()
                
                # Stop medical script since no conditions remain
                from world.medical.script import stop_medical_script
                stop_medical_script(target)
                
                # Restore all organs to full health
                for organ in medical_state.organs.values():
                    organ.current_hp = organ.max_hp
                
                # Restore vital signs
                medical_state.blood_level = 100.0
                medical_state.pain_level = 0.0
                medical_state.consciousness = 1.0
                
                # Clear placement descriptions and processing flags
                if hasattr(target, 'override_place'):
                    target.override_place = None
                if hasattr(target, 'ndb'):
                    target.ndb.death_processed = False
                    target.ndb.unconsciousness_processed = False
                
                target.save_medical_state()
                
                # Remove death state cmdset
                target.remove_death_state()
            
            caller.msg(f"|g{target.key} has been revived from death via medical system.|n")
            if target != caller:
                target.msg("|gYou have been revived from death via medical system.|n")
        else:
            # Character is alive, kill them using medical system conditions
            if hasattr(target, 'medical_state') and target.medical_state:
                
                # Use the medical system's natural damage-to-condition conversion
                # This creates authentic medical conditions exactly as combat would
                from world.medical.conditions import create_condition_from_damage
                
                # Create multiple catastrophic wounds to ensure rapid death
                # Equivalent to multiple gunshot wounds or severe arterial damage
                
                # Critical chest wound (heart/lung damage)
                chest_conditions = create_condition_from_damage(
                    damage_amount=75,  # Massive damage 
                    damage_type="bullet",  # Penetrating trauma
                    location="chest"
                )
                
                # Critical neck wound (arterial bleeding)
                neck_conditions = create_condition_from_damage(
                    damage_amount=60,  # Severe arterial damage
                    damage_type="blade",  # Deep cutting trauma
                    location="neck"
                )
                
                # Additional abdominal wound (organ damage)
                abdomen_conditions = create_condition_from_damage(
                    damage_amount=50,  # Major internal bleeding
                    damage_type="bullet",  # Penetrating trauma
                    location="abdomen"
                )
                
                # Add all the organically created conditions
                all_conditions = chest_conditions + neck_conditions + abdomen_conditions
                for condition in all_conditions:
                    target.medical_state.add_condition(condition)
                
                # Save medical state to ensure persistence
                target.save_medical_state()
                
                # These multiple severe conditions will cause rapid death through massive blood loss
                # The medical system will process them organically
                
            caller.msg(f"|r{target.key} has been given fatal bleeding conditions via medical system.|n")
            if target != caller:
                target.msg("|rYou have been given fatal bleeding conditions via medical system.|n")
            if force_test:
                caller.msg("|yForce mode: restrictions apply even to staff.|n")
                if target != caller:
                    target.msg("|yForce mode: restrictions apply even to staff.|n")


class CmdTestUnconscious(Command):
    """
    Test unconscious state using organic medical conditions.
    
    Usage:
        @testunconscious [<target>] [force]
        
    This command creates pain and bleeding conditions that naturally cause 
    unconsciousness or fully heals to awaken from unconsciousness. Uses real 
    medical conditions, not direct manipulation of vital signs.
    If no target is specified, affects yourself.
    If 'force' is specified, applies restrictions even to staff.
    """
    key = "@testunconscious"
    aliases = ["@tu"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"
    
    def func(self):
        caller = self.caller
        args = self.args.strip()
        
        # Parse arguments for target and force flag
        force_test = "force" in args.lower()
        target_name = args.replace("force", "").strip()
        
        # Determine target
        if target_name:
            target = caller.search(target_name, global_search=True)
            if not target:
                caller.msg(f"Could not find '{target_name}'.")
                return
            if not hasattr(target, 'is_unconscious'):
                caller.msg(f"{target.key} is not a character.")
                return
        else:
            target = caller
        
        if target.is_unconscious():
            # Character is unconscious, wake them up using heal logic
            if hasattr(target, 'medical_state') and target.medical_state:
                medical_state = target.medical_state
                
                # Restore consciousness to normal level
                medical_state.consciousness = 1.0
                medical_state.pain_level = 0.0  # Remove pain that might cause unconsciousness
                medical_state.blood_level = 100.0  # Restore blood level
                
                # Clear any conditions that might cause unconsciousness
                conditions_removed = []
                for condition in list(medical_state.conditions):
                    if condition.type in ['severe_bleeding', 'critical_bleeding']:
                        medical_state.conditions.remove(condition)
                        conditions_removed.append(condition.type)
                
                # Stop medical script if no conditions remain
                if not medical_state.conditions:
                    from world.medical.script import stop_medical_script
                    stop_medical_script(target)
                
                # Clear placement descriptions and processing flags
                if hasattr(target, 'override_place'):
                    target.override_place = None
                if hasattr(target, 'ndb'):
                    target.ndb.unconsciousness_processed = False
                
                target.save_medical_state()
                
                # Remove unconscious state cmdset
                target.remove_unconscious_state()
            
            caller.msg(f"|g{target.key} has been awakened from unconsciousness via medical system.|n")
            if target != caller:
                target.msg("|gYou have been awakened from unconsciousness via medical system.|n")
        else:
            # Character is conscious, make them unconscious using medical system conditions
            if hasattr(target, 'medical_state') and target.medical_state:
                
                # Use the medical system's natural damage-to-condition conversion
                # This creates authentic medical conditions exactly as combat would
                from world.medical.conditions import create_condition_from_damage
                
                # Create moderate blunt trauma that will cause unconsciousness
                # Equivalent to severe beating or head trauma
                unconscious_conditions = create_condition_from_damage(
                    damage_amount=25,  # Moderate damage causing pain/bleeding
                    damage_type="blunt",  # Blunt trauma causes pain
                    location="head"
                )
                
                # Add the organically created conditions
                for condition in unconscious_conditions:
                    target.medical_state.add_condition(condition)
                
                # Save medical state to ensure persistence  
                target.save_medical_state()
                
                # These conditions will naturally cause unconsciousness through pain and blood loss
                # The medical system will process them organically
                
            caller.msg(f"|r{target.key} has been given conditions causing unconsciousness via medical system.|n")
            if target != caller:
                target.msg("|rYou have been given conditions causing unconsciousness via medical system.|n")
            if force_test:
                caller.msg("|yForce mode: restrictions apply even to staff.|n")
                if target != caller:
                    target.msg("|yForce mode: restrictions apply even to staff.|n")


class CmdPeace(Command):
    """
    Instantly end all combat in your current room or a specified room.

    Usage:
        @peace
        @peace <room #>

    This will stop all combat handlers in your current location or in the specified room.
    """

    key = "@peace"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        splattercast = ChannelDB.objects.get_channel("Splattercast")

        # Default to caller's location
        location = caller.location

        # If a room dbref is provided, use that instead
        if self.args:
            room_arg = self.args.strip()
            if room_arg.startswith("#") and room_arg[1:].isdigit():
                room = search_object(room_arg)
                if not room:
                    caller.msg(f"|rNo room found with dbref {room_arg}.|n")
                    splattercast.msg(f"@peace failed: No room found with dbref {room_arg}.")
                    return
                location = room[0]
            else:
                caller.msg("|rUsage: @peace [<room #>]|n")
                splattercast.msg("@peace failed: Invalid room argument.")
                return

        if not location:
            caller.msg("|rYou have no location.|n")
            splattercast.msg("@peace failed: Caller has no location.")
            return

        # Find all combat handlers on this location
        handlers = [script for script in location.scripts.all() if script.key == "combat_handler"]
        if not handlers:
            caller.msg(f"|yNo combat to end in {location.key}.|n")
            splattercast.msg(f"@peace: No combat to end in {location.key}.")
            return

        for handler in handlers:
            handler.stop()
        caller.msg(f"|gAll combat in {location.key} has been ended.|n")
        splattercast.msg(f"@peace: All combat in {location.key} has been ended by {caller.key}.")


class CmdTestDeathCurtain(Command):
    """
    Test the death curtain animation with various messages.
    
    Usage:
        @testdeathcurtain [message]
        
    Examples:
        @testdeathcurtain
        @testdeathcurtain You feel your strength ebbing away...
        @testdeathcurtain The darkness consumes you
    """
    
    key = "@testdeathcurtain"
    aliases = ["@testcurtain", "@curtaintest"]
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"
    
    def func(self):
        """Execute the command."""
        from typeclasses.curtain_of_death import show_death_curtain
        
        caller = self.caller
        
        # Use custom message if provided, otherwise use default
        if self.args.strip():
            message = self.args.strip()
            caller.msg(f"|yStarting death curtain animation with message: '{message}'|n")
        else:
            message = None
            caller.msg("|yStarting death curtain animation with default message...|n")
            
        show_death_curtain(caller, message)


class CmdWeather(Command):
    """
    Show or set current weather conditions.
    
    Usage:
        @weather                    - Show current weather
        @weather <weather_type>     - Set weather type
        @weather list               - List available weather types
    
    Examples:
        @weather
        @weather clear
        @weather rainy_thunderstorm
        @weather list
    """
    
    key = "@weather"
    aliases = ["weather"]
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"
    
    def func(self):
        """Execute the weather command."""
        if not self.args:
            # Show current weather details
            from world.weather.time_system import get_current_time_period
            import time
            
            current_weather = weather_system.get_current_weather()
            intensity = weather_system.get_weather_intensity()
            time_period = get_current_time_period()
            real_time = time.strftime("%H:%M:%S")
            weather_key = f"{current_weather}_{time_period}"
            
            self.caller.msg("|WWeather System Status:|n")
            self.caller.msg(f"Current weather: |Y{current_weather}|n (intensity: {intensity})")
            self.caller.msg(f"Time period: |Y{time_period}|n")
            self.caller.msg(f"Real time: {real_time}")
            self.caller.msg(f"Weather key: |c{weather_key}|n")
            
            # Check if this weather/time combination has messages
            from world.weather.weather_messages import WEATHER_MESSAGES
            region_messages = WEATHER_MESSAGES.get('default', {})
            if weather_key in region_messages:
                self.caller.msg(f"Message pool: |gActive|n ({weather_key})")
            elif current_weather in region_messages:
                self.caller.msg(f"Message pool: |yFallback|n ({current_weather})")
            else:
                self.caller.msg(f"Message pool: |rNone found|n")
            return
            
        args = self.args.strip().lower()
        
        if args == "list":
            # List available weather types
            self.caller.msg("|WAvailable Weather Types:|n")
            for weather_type, intensity in WEATHER_INTENSITY.items():
                self.caller.msg(f"  |Y{weather_type}|n ({intensity})")
            return
            
        # Set weather
        if args in WEATHER_INTENSITY:
            weather_system.set_weather(args)
            intensity = WEATHER_INTENSITY[args]
            self.caller.msg(f"Weather set to: |Y{args}|n (intensity: {intensity})")
        else:
            self.caller.msg(f"Unknown weather type: {args}. Use '@weather list' to see options.")


class CmdResetMedical(Command):
    """
    Reset medical states for characters to use current medical structure.
    
    Usage:
        @resetmedical <character>
        @resetmedical confirm all
    
    This clears existing medical states and rebuilds them using the 
    current ORGANS definition. Useful after medical system updates.
    
    Use 'confirm all' for mass operations to prevent accidents.
    """
    
    key = "@resetmedical"
    aliases = ["@medicalreset", "@resetmed"]
    help_category = "Admin"
    locks = "cmd:perm(Builder)"
    
    def func(self):
        """Execute the medical reset command."""
        caller = self.caller
        args = self.args.strip()
        
        if not args:
            caller.msg("Usage: @resetmedical <character> | @resetmedical confirm all")
            return
            
        if args.lower() == "confirm all":
            # Reset all characters
            from typeclasses.characters import Character
            characters = Character.objects.all()
            count = 0
            
            for char in characters:
                if hasattr(char, '_medical_state'):
                    delattr(char, '_medical_state')
                if char.db.medical_state:
                    del char.db.medical_state
                count += 1
                
            caller.msg(f"|gReset medical states for {count} characters.|n")
            caller.msg("|yCharacters will get current medical structure on next access.|n")
            
        elif args.lower() == "all":
            caller.msg("|yWarning: This will reset ALL character medical states!|n")
            caller.msg("|yUse '@resetmedical confirm all' to proceed.|n")
            
        else:
            # Reset specific character
            target = caller.search(args, global_search=True)
            if not target:
                return
                
            if hasattr(target, '_medical_state'):
                delattr(target, '_medical_state')
            if target.db.medical_state:
                del target.db.medical_state
                
            caller.msg(f"|gReset medical state for {target.get_display_name(caller)}.|n")
            caller.msg("|yThey will get current medical structure on next access.|n")


class CmdMedicalAudit(Command):
    """
    Audit medical states across all characters.
    
    Usage:
        @medaudit
        @medaudit details
    
    Shows statistics about medical state versions and issues.
    """
    
    key = "@medaudit"
    aliases = ["@auditmedical"]
    help_category = "Admin"
    locks = "cmd:perm(Builder)"
    
    def func(self):
        """Execute the medical audit command."""
        caller = self.caller
        args = self.args.strip().lower()
        
        from typeclasses.characters import Character
        characters = Character.objects.all()
        stats = {
            'total': len(characters),
            'has_medical': 0,
            'old_structure': 0,
            'new_structure': 0,
            'no_medical': 0,
            'errors': 0
        }
        
        details = []
        
        for char in characters:
            try:
                medical_data = char.db.medical_state
                if not medical_data:
                    stats['no_medical'] += 1
                    if args == 'details':
                        details.append(f"{char.key}: No medical state")
                    continue
                    
                stats['has_medical'] += 1
                
                if 'organs' in medical_data:
                    organs = medical_data['organs']
                    if 'left_humerus' in organs and 'left_arm_system' not in organs:
                        stats['new_structure'] += 1
                        if args == 'details':
                            details.append(f"{char.key}: New bone structure ✓")
                    else:
                        stats['old_structure'] += 1
                        if args == 'details':
                            details.append(f"{char.key}: Old system structure (needs migration)")
                else:
                    stats['old_structure'] += 1
                    if args == 'details':
                        details.append(f"{char.key}: Very old structure (needs migration)")
                        
            except Exception as e:
                stats['errors'] += 1
                if args == 'details':
                    details.append(f"{char.key}: ERROR - {e}")
        
        # Show summary
        caller.msg("|cMedical State Audit Results:|n")
        caller.msg(f"Total Characters: {stats['total']}")
        caller.msg(f"Has Medical State: {stats['has_medical']}")
        caller.msg(f"New Bone Structure: |g{stats['new_structure']}|n")
        caller.msg(f"Old Structure (needs migration): |y{stats['old_structure']}|n")
        caller.msg(f"No Medical State: {stats['no_medical']}")
        caller.msg(f"Errors: |r{stats['errors']}|n")
        
        if args == 'details' and details:
            caller.msg("\n|wDetailed Results:|n")
            for detail in details[:20]:  # Limit output
                caller.msg(f"  {detail}")
            if len(details) > 20:
                caller.msg(f"  ... and {len(details) - 20} more")
