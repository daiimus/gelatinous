"""
Medical Commands

Commands for interacting with the medical system, including diagnosis,
status checking, and basic medical actions.
"""

from evennia import Command
from evennia.utils.evtable import EvTable

from world.medical.constants import BODY_CAPACITIES
from world.medical.utils import get_medical_status_summary


class CmdMedical(Command):
    """
    Check your medical status or diagnose others.
    
    Usage:
        medical
        medical <character>
        medical me
        diagnose <character>
    
    Shows detailed information about medical conditions, organ health,
    and vital signs. Can be used on yourself or others (if you have
    medical training).
    """
    
    key = "medical"
    aliases = ["diagnose", "medstat", "health"]
    help_category = "Medical"
    
    def func(self):
        """Execute the medical command."""
        caller = self.caller
        args = self.args.strip()
        
        # Determine target
        if not args or args.lower() == "me":
            target = caller
            is_self = True
        else:
            target = caller.search(args)
            if not target:
                return
            is_self = (target == caller)
            
        # Check if target has medical state
        try:
            medical_state = target.medical_state
            if medical_state is None:
                caller.msg(f"{target.get_display_name(caller)} has no medical information available.")
                return
        except AttributeError:
            caller.msg(f"{target.get_display_name(caller)} has no medical information available.")
            return
            
        # Get medical status
        status = get_medical_status_summary(target)
        
        # Format output
        if is_self:
            caller.msg(f"|cYour Medical Status:|n\n{status}")
        else:
            caller.msg(f"|c{target.get_display_name(caller)}'s Medical Status:|n\n{status}")


class CmdDamageTest(Command):
    """
    Test command for applying anatomical damage.
    
    Usage:
        damagetest <amount> [location] [injury_type]
    
    Examples:
        damagetest 10
        damagetest 15 chest cut
        damagetest 8 left_arm blunt
    
    This command is for testing the medical system during development.
    """
    
    key = "damagetest"
    help_category = "Medical"
    locks = "cmd:perm(Builder)"
    
    def func(self):
        """Execute the damage test command."""
        caller = self.caller
        
        if not self.args:
            caller.msg("Usage: damagetest <amount> [location] [injury_type]")
            return
            
        args = self.args.strip().split()
        
        try:
            damage_amount = int(args[0])
        except (ValueError, IndexError):
            caller.msg("Please provide a valid damage amount.")
            return
            
        location = args[1] if len(args) > 1 else "chest"
        injury_type = args[2] if len(args) > 2 else "generic"
        
        # Apply damage and check result - take_damage returns (died, actual_damage)
        target_died, actual_damage = caller.take_damage(damage_amount, location, injury_type)
        
        # Show damage message with armor info if applicable
        if actual_damage < damage_amount:
            armor_absorbed = damage_amount - actual_damage
            caller.msg(f"|rYou take {damage_amount} {injury_type} damage to your {location}!|n")
            caller.msg(f"|gArmor absorbed {armor_absorbed} damage - {actual_damage} damage applied.|n")
        else:
            caller.msg(f"|rYou take {damage_amount} {injury_type} damage to your {location}!|n")
        
        # Show medical status after damage
        medical_state = caller.medical_state  # Use property that loads from db
        if medical_state:
            # Show current wounds
            total_wounds = sum(len(wounds) for wounds in medical_state.to_dict().get('wounds', {}).values())
            if total_wounds > 0:
                caller.msg(f"|yYou now have {total_wounds} total wounds.|n")
            
            # Show organ damage - organs are now Organ objects, not dicts
            damaged_organs = []
            for organ_name, organ in medical_state.organs.items():
                if organ.current_hp < organ.max_hp:
                    damage_taken = organ.max_hp - organ.current_hp
                    damaged_organs.append(f"{organ_name} ({damage_taken} damage)")
            
            if damaged_organs:
                caller.msg("|yDamaged organs:|n")
                for organ_info in damaged_organs:
                    caller.msg(f"  - {organ_info}")
        
        # Check for critical status - death and unconsciousness are handled by medical system
        # but we show explicit test feedback here
        if target_died:
            # Death progression script will handle actual death messages
            caller.msg("|R[TEST] Death triggered - medical death progression active.|n")
        elif caller.is_unconscious():
            caller.msg("|Y[TEST] Unconsciousness triggered.|n")


class CmdMedicalInfo(Command):
    """
    Display detailed information about the medical system.
    
    Usage:
        medinfo [target]
        medinfo [target] organs
        medinfo [target] conditions
        medinfo [target] capacities
    
    Shows information about organ health, body capacities, and medical conditions.
    If no target is specified, shows your own medical information.
    """
    
    key = "medinfo"
    help_category = "Medical"
    
    def func(self):
        """Execute the medical info command."""
        caller = self.caller
        args = self.args.strip()
        
        # Parse arguments to separate target from info type
        if not args:
            target = caller
            info_type = "summary"
        else:
            # Split arguments
            parts = args.split()
            if len(parts) == 1:
                # Could be either target or info type
                search_result = caller.search(parts[0], quiet=True)
                if search_result and len(search_result) == 1:
                    target = search_result[0]
                    info_type = "summary"
                else:
                    # Not a valid target, treat as info type
                    target = caller
                    info_type = parts[0].lower()
            else:
                # Two parts: target and info type
                target = caller.search(parts[0])
                if not target:
                    return
                # Handle case where search returns a list (multiple matches)
                if isinstance(target, list):
                    caller.msg(f"Multiple matches for '{parts[0]}'. Please be more specific.")
                    return
                info_type = parts[1].lower()
        
        # Additional safety check to ensure target is not a list
        if isinstance(target, list):
            caller.msg("Target search returned multiple results. Please be more specific.")
            return
        
        # Check if target has medical state
        try:
            medical_state = target.medical_state
            if medical_state is None:
                caller.msg(f"{target.get_display_name(caller)} has no medical information available.")
                return
        except AttributeError:
            caller.msg(f"{target.get_display_name(caller)} has no medical information available.")
            return
            
        # Show appropriate information
        if not info_type or info_type == "summary":
            self._show_summary(caller, target, medical_state)
        elif info_type == "organs":
            self._show_organs(caller, target, medical_state)
        elif info_type == "conditions":
            self._show_conditions(caller, target, medical_state)
        elif info_type == "capacities":
            self._show_capacities(caller, target, medical_state)
        else:
            caller.msg("Available options: summary, organs, conditions, capacities")
            
    def _show_summary(self, caller, target, medical_state):
        """Show summary view."""
        table = EvTable("Status", "Value", border="cells")
        
        # Basic status
        status = "DEAD" if medical_state.is_dead() else ("UNCONSCIOUS" if medical_state.is_unconscious() else "CONSCIOUS")
        table.add_row("Overall Status", f"|{'r' if status == 'DEAD' else 'y' if status == 'UNCONSCIOUS' else 'g'}{status}|n")
        
        # Vital signs
        table.add_row("Blood Level", f"{medical_state.blood_level:.1f}%")
        table.add_row("Pain Level", f"{medical_state.pain_level:.1f}")
        table.add_row("Consciousness", f"{medical_state.consciousness * 100:.1f}%")
        
        # Counts
        damaged_organs = sum(1 for organ in medical_state.organs.values() if organ.current_hp < organ.max_hp)
        table.add_row("Damaged Organs", str(damaged_organs))
        table.add_row("Active Conditions", str(len(medical_state.conditions)))
        
        # Show whose information this is
        target_name = "Your" if target == caller else f"{target.get_display_name(caller)}'s"
        caller.msg(f"|c{target_name} Medical Summary:|n\n{table}")
        
    def _show_organs(self, caller, target, medical_state):
        """Show detailed organ information."""
        table = EvTable("Organ", "HP", "Status", "Location", border="cells")
        
        for organ_name, organ in medical_state.organs.items():
            hp_str = f"{organ.current_hp}/{organ.max_hp}"
            
            if organ.current_hp == organ.max_hp:
                status = "|gHealthy|n"
            elif organ.current_hp > organ.max_hp * 0.5:
                status = "|yDamaged|n"
            elif organ.current_hp > 0:
                status = "|rSeverely Damaged|n"
            else:
                status = "|RDestroyed|n"
                
            table.add_row(organ_name.replace('_', ' ').title(), hp_str, status, organ.container)
            
        target_name = "Your" if target == caller else f"{target.get_display_name(caller)}'s"
        caller.msg(f"|c{target_name} Organ Status:|n\n{table}")
        
    def _show_conditions(self, caller, target, medical_state):
        """Show detailed condition information."""
        if not medical_state.conditions:
            target_name = "You have" if target == caller else f"{target.get_display_name(caller)} has"
            caller.msg(f"{target_name} no active medical conditions.")
            return
            
        table = EvTable("Condition", "Location", "Severity", "Treated", border="cells")
        
        for condition in medical_state.conditions:
            location_str = condition.location or "General"
            treated_str = "|gYes|n" if condition.treated else "|rNo|n"
            
            # Handle both numeric and string severities
            if isinstance(condition.severity, (int, float)):
                # Convert numeric severity to descriptive string
                if condition.severity >= 20:
                    severity_str = "Critical"
                elif condition.severity >= 10:
                    severity_str = "Severe"
                elif condition.severity >= 5:
                    severity_str = "Moderate"
                elif condition.severity >= 1:
                    severity_str = "Minor"
                else:
                    severity_str = "Negligible"
            else:
                # String severity - just title case it
                severity_str = str(condition.severity).title()
            
            table.add_row(
                condition.type.title(),
                location_str,
                severity_str,
                treated_str
            )
            
        target_name = "Your" if target == caller else f"{target.get_display_name(caller)}'s"  
        caller.msg(f"|c{target_name} Active Conditions:|n\n{table}")
        
    def _show_capacities(self, caller, target, medical_state):
        """Show body capacity information."""
        table = EvTable("Capacity", "Level", "Status", border="cells")
        
        for capacity_name in BODY_CAPACITIES.keys():
            level = medical_state.calculate_body_capacity(capacity_name)
            level_percent = level * 100
            
            if level >= 0.8:
                status = "|gGood|n"
            elif level >= 0.5:
                status = "|yImpaired|n" 
            elif level > 0:
                status = "|rSeverely Impaired|n"
            else:
                status = "|RNon-functional|n"
                
            table.add_row(
                capacity_name.replace('_', ' ').title(),
                f"{level_percent:.1f}%",
                status
            )
            
        target_name = "Your" if target == caller else f"{target.get_display_name(caller)}'s"
        caller.msg(f"|c{target_name} Body Capacities:|n\n{table}")


# Add commands to default command set
from evennia import default_cmds

class MedicalCmdSet(default_cmds.CharacterCmdSet):
    """
    Command set containing medical system commands.
    """
    
    key = "MedicalCmdSet"
    
    def at_cmdset_creation(self):
        """Populate the cmdset."""
        super().at_cmdset_creation()
        self.add(CmdMedical())
        self.add(CmdDamageTest())
        self.add(CmdMedicalInfo())
