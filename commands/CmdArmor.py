"""
Armor inspection and management commands.

Commands for checking armor condition, effectiveness, and coverage.
"""

from evennia import Command
from random import randint
from world.utils.boxtable import BoxTable
from world.combat.constants import (
    COLOR_SUCCESS, COLOR_NORMAL
)


class CmdArmor(Command):
    """
    Inspect worn armor condition and coverage.
    
    Usage:
        armor                    - List all worn armor
        armor <item>            - Detailed info on specific armor piece
        armor coverage          - Show body coverage map
        armor effectiveness     - Show armor vs damage type matrix
    
    This command shows your currently worn armor, its condition,
    protection ratings, and coverage areas.
    """
    
    key = "armor"
    aliases = ["armour"]
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        caller = self.caller
        args = self.args.strip()
        
        # Get all worn armor items
        worn_armor = self._get_worn_armor(caller)
        
        if not args:
            # List all worn armor
            self._list_armor(caller, worn_armor)
        elif args.lower() == "coverage":
            # Show coverage map
            self._show_coverage_map(caller, worn_armor)
        elif args.lower() == "effectiveness":
            # Show effectiveness matrix
            self._show_effectiveness_matrix(caller)
        else:
            # Show specific item details
            self._show_item_details(caller, args, worn_armor)
    
    def _get_worn_armor(self, character):
        """Get all worn items that have armor properties."""
        armor_items = []
        seen_items = set()  # Track items we've already added
        
        if not hasattr(character, 'worn_items') or not character.worn_items:
            return armor_items
            
        for location, items in character.worn_items.items():
            for item in items:
                # Only add each unique item once
                if item.id not in seen_items and hasattr(item, 'armor_rating') and item.armor_rating > 0:
                    armor_items.append(item)
                    seen_items.add(item.id)
        
        return armor_items
    
    def _calculate_total_rating(self, carrier):
        """Calculate total armor rating for carrier including installed plates."""
        base_rating = getattr(carrier, 'armor_rating', 0)
        installed_plates = getattr(carrier, 'installed_plates', {})
        plate_rating = sum(getattr(plate, 'armor_rating', 0) for plate in installed_plates.values() if plate)
        return base_rating + plate_rating
    
    def _list_armor(self, caller, worn_armor):
        """List all worn armor with basic stats."""
        if not worn_armor:
            caller.msg("You are not wearing any armor.")
            return
        
        # Check if caller wants centered headers (default: True)
        center_headers = getattr(caller.db, 'center_armor_headers', True)
        
        # Create armor status table with box-drawing characters
        table = BoxTable("Item", "Type", "Rating", "Durability", "Coverage")
        
        for armor in worn_armor:
            # Get armor stats
            armor_type = getattr(armor, 'armor_type', 'generic')
            
            # Calculate rating (handle plate carriers specially)
            if getattr(armor, 'is_plate_carrier', False):
                base_rating = getattr(armor, 'armor_rating', 0)
                installed_plates = getattr(armor, 'installed_plates', {})
                
                # Calculate min and max protection across body locations
                min_rating = base_rating
                max_rating = base_rating
                
                # Check front plate (chest)
                front_plate = installed_plates.get('front')
                if front_plate:
                    chest_rating = base_rating + getattr(front_plate, 'armor_rating', 0)
                    max_rating = max(max_rating, chest_rating)
                
                # Check back plate
                back_plate = installed_plates.get('back')
                if back_plate:
                    back_rating = base_rating + getattr(back_plate, 'armor_rating', 0)
                    max_rating = max(max_rating, back_rating)
                
                # Check side plates (abdomen protection)
                left_plate = installed_plates.get('left_side')
                right_plate = installed_plates.get('right_side')
                side_protection = 0
                if left_plate:
                    side_protection += getattr(left_plate, 'armor_rating', 0)
                if right_plate:
                    side_protection += getattr(right_plate, 'armor_rating', 0)
                if side_protection > 0:
                    abdomen_rating = base_rating + (side_protection // 2)
                    max_rating = max(max_rating, abdomen_rating)
                
                # Show as range if plates provide different protection levels
                if max_rating > base_rating:
                    rating_display = f"{base_rating}-{max_rating}/10"
                else:
                    rating_display = f"{base_rating}/10"
            else:
                rating = getattr(armor, 'armor_rating', 0)
                rating_display = f"{rating}/10"
            
            durability = getattr(armor, 'armor_durability', 0)
            max_durability = getattr(armor, 'max_armor_durability', 0)
            
            # Get coverage
            coverage = getattr(armor, 'get_current_coverage', lambda: getattr(armor, 'coverage', []))()
            coverage_str = ", ".join(coverage[:3])  # Show first 3 locations
            if len(coverage) > 3:
                coverage_str += f", & {len(coverage)-3} more"
            
            # Format durability with color coding and 2-stripe bar
            if max_durability > 0:
                durability_percent = durability / max_durability
                
                # Create 2-stripe progress bar
                bar_length = 10  # Total characters in bar
                filled = int(durability_percent * bar_length)
                
                # Color based on percentage
                if durability_percent > 0.7:
                    bar_color = "|g"  # Green
                elif durability_percent > 0.3:
                    bar_color = "|y"  # Yellow
                else:
                    bar_color = "|r"  # Red
                
                # Build bar with ▓ for filled and ░ for empty
                bar = bar_color + "▓" * filled + "░" * (bar_length - filled) + "|n"
                durability_str = f"{bar} {durability}/{max_durability}"
            else:
                durability_str = "N/A"
            
            table.add_row(
                armor.key,
                armor_type.title(),
                rating_display,
                durability_str,
                coverage_str
            )
        
        # Add centered header using BoxTable's built-in functionality
        table.add_header("ARMOR STATUS", center=center_headers)
        
        # Center the entire table on screen if caller has a session
        if hasattr(caller, 'sessions') and caller.sessions.all():
            session = caller.sessions.all()[0]
            centered_output = table.center_on_screen(session=session)
            caller.msg(f"\n{centered_output}")
        else:
            caller.msg(f"\n{table}")
    
    def _show_coverage_map(self, caller, worn_armor):
        """Show which body locations are protected by armor."""
        if not worn_armor:
            caller.msg("You are not wearing any armor.")
            return
        
        # Build coverage map - stores list of armor pieces per location
        coverage_map = {}
        
        for armor in worn_armor:
            coverage = getattr(armor, 'get_current_coverage', lambda: getattr(armor, 'coverage', []))()
            
            # For plate carriers, calculate location-specific ratings
            if getattr(armor, 'is_plate_carrier', False):
                base_rating = getattr(armor, 'armor_rating', 0)
                installed_plates = getattr(armor, 'installed_plates', {})
                
                # Calculate protection for each body location
                for location in coverage:
                    if location not in coverage_map:
                        coverage_map[location] = []
                    
                    location_rating = base_rating
                    plate_details = []
                    
                    # Add plates that protect this specific location
                    if location == "chest":
                        # Front plate protects chest
                        front_plate = installed_plates.get('front')
                        if front_plate:
                            plate_rating = getattr(front_plate, 'armor_rating', 0)
                            location_rating += plate_rating
                            plate_details.append(f"{front_plate.key} ({plate_rating})")
                    elif location == "back":
                        # Back plate protects back
                        back_plate = installed_plates.get('back')
                        if back_plate:
                            plate_rating = getattr(back_plate, 'armor_rating', 0)
                            location_rating += plate_rating
                            plate_details.append(f"{back_plate.key} ({plate_rating})")
                    elif location == "abdomen":
                        # Side plates contribute to abdomen (averaged)
                        side_protection = 0
                        left_plate = installed_plates.get('left_side')
                        right_plate = installed_plates.get('right_side')
                        if left_plate:
                            left_rating = getattr(left_plate, 'armor_rating', 0)
                            side_protection += left_rating
                            # Show actual effective contribution
                            plate_details.append(f"{left_plate.key} ({left_rating // 2})")
                        if right_plate:
                            right_rating = getattr(right_plate, 'armor_rating', 0)
                            side_protection += right_rating
                            # Show actual effective contribution
                            plate_details.append(f"{right_plate.key} ({right_rating // 2})")
                        # Average the side plates for abdomen
                        if side_protection > 0:
                            location_rating += side_protection // 2
                    
                    # Build armor description
                    armor_desc = armor.key
                    if plate_details:
                        armor_desc += " [" + ", ".join(plate_details) + "]"
                    
                    coverage_map[location].append({
                        'armor': armor,
                        'description': armor_desc,
                        'rating': location_rating,
                        'type': getattr(armor, 'armor_type', 'generic')
                    })
            else:
                # Regular armor uses standard rating for all covered locations
                rating = getattr(armor, 'armor_rating', 0)
                for location in coverage:
                    if location not in coverage_map:
                        coverage_map[location] = []
                    
                    coverage_map[location].append({
                        'armor': armor,
                        'description': armor.key,
                        'rating': rating,
                        'type': getattr(armor, 'armor_type', 'generic')
                    })
        
        # Check if caller wants centered headers (default: True)
        center_headers = getattr(caller.db, 'center_armor_headers', True)
        
        # Create coverage table with box-drawing characters
        table = BoxTable("Body Location", "Protected By", "Type", "Rating")
        
        # Common body locations for display
        locations = [
            "head", "chest", "back", "abdomen", 
            "left_arm", "right_arm", "left_hand", "right_hand",
            "groin", "left_thigh", "right_thigh", 
            "left_shin", "right_shin", "left_foot", "right_foot"
        ]
        
        for location in locations:
            if location in coverage_map:
                armor_list = coverage_map[location]
                # Sort by rating, highest first
                armor_list.sort(key=lambda x: x['rating'], reverse=True)
                
                # Add each armor piece as a row
                for i, armor_info in enumerate(armor_list):
                    location_name = location.replace('_', ' ').title() if i == 0 else ""
                    table.add_row(
                        location_name,
                        armor_info['description'],
                        armor_info['type'].title(),
                        f"{armor_info['rating']}/10"
                    )
            else:
                table.add_row(
                    location.replace('_', ' ').title(),
                    "|rUnprotected|n",
                    "-",
                    "0/10"
                )
        
        # Add centered header
        table.add_header("|gARMOR COVERAGE MAP|n", center=center_headers)
        
        caller.msg(f"\n{table}")
    
    def _show_effectiveness_matrix(self, caller):
        """Show armor effectiveness vs damage types."""
        from world.combat.constants import ARMOR_EFFECTIVENESS_MATRIX
        
        # Check if caller wants centered headers (default: True)
        center_headers = getattr(caller.db, 'center_armor_headers', True)
        
        # Convert to percentage display format
        effectiveness_display = {}
        for armor_type, damage_types in ARMOR_EFFECTIVENESS_MATRIX.items():
            if armor_type == 'generic':
                continue  # Skip generic in display
            effectiveness_display[armor_type] = {
                damage_type: f"{int(effectiveness * 100)}%"
                for damage_type, effectiveness in damage_types.items()
            }
        
        # Create effectiveness matrix table with box-drawing characters
        table = BoxTable("Armor Type", "Bullet", "Stab", "Cut", "Blunt", "Laceration", "Burn")
        
        for armor_type in ['Kevlar', 'Steel', 'Leather', 'Ceramic']:
            armor_key = armor_type.lower()
            if armor_key in effectiveness_display:
                effectiveness = effectiveness_display[armor_key]
                table.add_row(
                    armor_type,
                    effectiveness.get('bullet', 'N/A'),
                    effectiveness.get('stab', 'N/A'), 
                    effectiveness.get('cut', 'N/A'),
                    effectiveness.get('blunt', 'N/A'),
                    effectiveness.get('laceration', 'N/A'),
                    effectiveness.get('burn', 'N/A')
                )
        
        # Add centered header
        table.add_header("|gARMOR EFFECTIVENESS MATRIX|n", center=center_headers)
        
        caller.msg("\nShows base effectiveness % before armor rating multiplier")
        caller.msg(f"{table}")
        caller.msg("\n|xNote: Final effectiveness = Base % × (Armor Rating / 10)|n")
    
    def _show_item_details(self, caller, item_name, worn_armor):
        """Show detailed information about a specific armor piece."""
        # Find the armor item
        target_armor = None
        for armor in worn_armor:
            armor_aliases = armor.aliases.all() if hasattr(armor, 'aliases') else []
            if item_name.lower() in armor.key.lower() or item_name.lower() in [alias.lower() for alias in armor_aliases]:
                target_armor = armor
                break
        
        if not target_armor:
            caller.msg(f"You are not wearing any armor matching '{item_name}'.")
            return
        
        # Get all armor stats
        armor_type = getattr(target_armor, 'armor_type', 'generic')
        rating = getattr(target_armor, 'armor_rating', 0)
        base_rating = getattr(target_armor, 'base_armor_rating', rating)
        durability = getattr(target_armor, 'armor_durability', 0)
        max_durability = getattr(target_armor, 'max_armor_durability', 0)
        material = getattr(target_armor, 'material', 'unknown')
        
        # Get coverage
        coverage = getattr(target_armor, 'get_current_coverage', lambda: getattr(target_armor, 'coverage', []))()
        
        # Calculate degradation
        if max_durability > 0:
            durability_percent = durability / max_durability
            degradation = base_rating - rating
        else:
            durability_percent = 1.0
            degradation = 0
        
        # Format condition
        if durability_percent > 0.9:
            condition = "|gExcellent|n"
        elif durability_percent > 0.7:
            condition = "|GGood|n"
        elif durability_percent > 0.5:
            condition = "|yFair|n"
        elif durability_percent > 0.3:
            condition = "|YPoor|n"
        else:
            condition = "|rTerrible|n"
        
        # Display detailed info
        caller.msg(f"\n|w=== {target_armor.key.title()} ===|n")
        caller.msg(f"|xDescription:|n {target_armor.desc}")
        caller.msg(f"\n|xArmor Statistics:|n")
        caller.msg(f"  Type: {armor_type.title()}")
        caller.msg(f"  Material: {material.title()}")
        caller.msg(f"  Current Rating: {rating}/10")
        if degradation > 0:
            caller.msg(f"  |rDegradation: -{degradation} from original {base_rating}/10|n")
        caller.msg(f"  Condition: {condition} ({durability}/{max_durability})")
        caller.msg(f"\n|xProtected Locations:|n")
        caller.msg(f"  {', '.join([loc.replace('_', ' ').title() for loc in coverage])}")


class CmdArmorRepair(Command):
    """
    Repair damaged armor using tools and skill.
    
    Usage:
        repair <armor> [with <tool>]    - Repair armor with optional tool
        repair <armor> field            - Quick field repair (temporary)
        repair <armor> full             - Complete restoration (requires workshop)
        
    Repair success is based on your Intellect stat representing technical skill.
    Different armor types require different approaches and tools.
    Field repairs are quick but temporary. Full repairs restore original condition.
    """
    
    key = "repair"
    aliases = ["fix", "mend"]
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        
        if not args:
            caller.msg("Repair what? Usage: repair <armor> [with <tool>] or repair <armor> [field/full]")
            return
        
        # Parse arguments
        armor_name = args[0]
        repair_type = "standard"  # standard, field, or full
        tool_name = None
        
        # Check for repair type modifiers
        if len(args) > 1:
            if args[1].lower() == "field":
                repair_type = "field"
            elif args[1].lower() == "full":
                repair_type = "full"
            elif args[1].lower() == "with" and len(args) > 2:
                tool_name = " ".join(args[2:])
        
        # Find the armor item
        armor_item = self._find_repairable_armor(caller, armor_name)
        if not armor_item:
            return
        
        # Find repair tool if specified
        repair_tool = None
        if tool_name:
            repair_tool = self._find_repair_tool(caller, tool_name)
            if not repair_tool:
                return
        
        # Perform the repair
        self._attempt_repair(caller, armor_item, repair_type, repair_tool)
    
    def _find_repairable_armor(self, caller, armor_name):
        """Find armor item that can be repaired."""
        # Check worn armor first
        if hasattr(caller, 'worn_items') and caller.worn_items:
            for location, items in caller.worn_items.items():
                for item in items:
                    item_aliases = item.aliases.all() if hasattr(item, 'aliases') else []
                    if (hasattr(item, 'armor_rating') and 
                        (armor_name.lower() in item.key.lower() or 
                         armor_name.lower() in [alias.lower() for alias in item_aliases])):
                        return item
        
        # Check inventory
        for item in caller.contents:
            item_aliases = item.aliases.all() if hasattr(item, 'aliases') else []
            if (hasattr(item, 'armor_rating') and 
                (armor_name.lower() in item.key.lower() or 
                 armor_name.lower() in [alias.lower() for alias in item_aliases])):
                return item
        
        caller.msg(f"You don't have any armor matching '{armor_name}'.")
        return None
    
    def _find_repair_tool(self, caller, tool_name):
        """Find repair tool in inventory."""
        for item in caller.contents:
            item_aliases = item.aliases.all() if hasattr(item, 'aliases') else []
            if (hasattr(item, 'repair_tool_type') and 
                (tool_name.lower() in item.key.lower() or 
                 tool_name.lower() in [alias.lower() for alias in item_aliases])):
                return item
        
        caller.msg(f"You don't have a repair tool matching '{tool_name}'.")
        return None
    
    def _attempt_repair(self, caller, armor_item, repair_type, repair_tool):
        """Attempt to repair the armor based on type and tools."""
        # Check if armor needs repair
        current_durability = getattr(armor_item, 'armor_durability', 0)
        max_durability = getattr(armor_item, 'max_armor_durability', 0)
        
        if current_durability >= max_durability:
            caller.msg(f"The {armor_item.key} is already in perfect condition.")
            return
        
        # Check for full repair requirements
        if repair_type == "full" and not self._has_workshop_access(caller):
            caller.msg("Full repairs require access to a proper workshop with an armor workbench.")
            return
        
        # Calculate repair parameters
        armor_type = getattr(armor_item, 'armor_type', 'generic')
        repair_difficulty = self._get_repair_difficulty(armor_type, repair_type)
        tool_bonus = self._get_tool_bonus(repair_tool, armor_type) if repair_tool else 0
        
        # Get caller's technical skill (Intellect-based)
        from world.combat.utils import get_character_stat, roll_stat
        intellect = get_character_stat(caller, "intellect", 1)
        skill_roll = roll_stat(caller, "intellect", 1)
        
        # Calculate success
        total_skill = skill_roll + tool_bonus
        success = total_skill >= repair_difficulty
        
        # Determine repair amount based on success margin
        if success:
            success_margin = total_skill - repair_difficulty
            repair_amount = self._calculate_repair_amount(repair_type, success_margin, max_durability)
            
            # Apply repair
            new_durability = min(max_durability, current_durability + repair_amount)
            armor_item.armor_durability = new_durability
            
            # Recalculate armor rating based on new durability
            durability_percent = new_durability / max_durability
            base_rating = getattr(armor_item, 'base_armor_rating', armor_item.armor_rating)
            armor_item.armor_rating = max(1, int(base_rating * durability_percent))
            
            # Success messages
            self._send_repair_success_messages(caller, armor_item, repair_type, repair_amount, repair_tool)
            
            # Degrade tool if used
            if repair_tool:
                self._degrade_repair_tool(repair_tool)
                
        else:
            # Failure messages
            self._send_repair_failure_messages(caller, armor_item, repair_type, repair_tool)
            
            # Possible tool damage on critical failure
            if repair_tool and total_skill < repair_difficulty - 5:
                self._damage_repair_tool(repair_tool)
    
    def _get_repair_difficulty(self, armor_type, repair_type):
        """Get base difficulty for repairing this armor type."""
        base_difficulties = {
            'leather': 8,    # Easiest to repair
            'kevlar': 12,    # Moderate - requires understanding of ballistic fibers
            'steel': 15,     # Hard - requires metalworking
            'ceramic': 20,   # Very hard - specialized knowledge
            'generic': 10
        }
        
        base_difficulty = base_difficulties.get(armor_type, 10)
        
        # Adjust for repair type
        if repair_type == "field":
            return base_difficulty - 3  # Easier but temporary
        elif repair_type == "full":
            return base_difficulty + 5  # Harder but complete restoration
        
        return base_difficulty  # Standard repair
    
    def _get_tool_bonus(self, repair_tool, armor_type):
        """Calculate bonus from using appropriate tools."""
        if not repair_tool:
            return 0
        
        tool_type = getattr(repair_tool, 'repair_tool_type', 'generic')
        
        # Tool effectiveness matrix
        tool_bonuses = {
            'sewing_kit': {'leather': 6, 'kevlar': 3, 'steel': 0, 'ceramic': 0},
            'metalwork_tools': {'leather': 2, 'kevlar': 2, 'steel': 8, 'ceramic': 2},
            'ballistic_repair_kit': {'leather': 2, 'kevlar': 10, 'steel': 1, 'ceramic': 4},
            'ceramic_repair_compound': {'leather': 0, 'kevlar': 2, 'steel': 1, 'ceramic': 12},
            'generic_tools': {'leather': 2, 'kevlar': 2, 'steel': 2, 'ceramic': 2}
        }
        
        return tool_bonuses.get(tool_type, tool_bonuses['generic_tools']).get(armor_type, 2)
    
    def _calculate_repair_amount(self, repair_type, success_margin, max_durability):
        """Calculate how much durability to restore."""
        base_repair = {
            'field': max_durability * 0.15,     # 15% restoration (temporary)
            'standard': max_durability * 0.25,  # 25% restoration
            'full': max_durability * 0.60       # 60% restoration (workshop repair)
        }
        
        # Add bonus for exceptional success
        bonus_multiplier = 1.0 + (success_margin * 0.05)  # 5% per point over difficulty
        
        return int(base_repair.get(repair_type, base_repair['standard']) * bonus_multiplier)
    
    def _send_repair_success_messages(self, caller, armor_item, repair_type, repair_amount, repair_tool):
        """Send appropriate success messages."""
        tool_desc = f" using the {repair_tool.key}" if repair_tool else " with improvised materials"
        
        if repair_type == "field":
            caller.msg(f"|gYou patch up the {armor_item.key} with a quick field repair{tool_desc}. It's not perfect, but it'll hold for now.|n")
        elif repair_type == "full":
            caller.msg(f"|GYou meticulously restore the {armor_item.key}{tool_desc}, bringing it as close to original condition as possible.|n")
        else:
            caller.msg(f"|gYou successfully repair the {armor_item.key}{tool_desc}, restoring some of its protective capability.|n")
        
        # Show durability improvement
        current_durability = armor_item.armor_durability
        max_durability = armor_item.max_armor_durability
        durability_percent = int((current_durability / max_durability) * 100)
        
        caller.msg(f"Durability improved by {repair_amount} points. Current condition: {durability_percent}%")
        
        # Send to location
        location_msg = f"{caller.key} works on repairing {armor_item.key}."
        if caller.location:
            caller.location.msg_contents(location_msg, exclude=[caller])
    
    def _send_repair_failure_messages(self, caller, armor_item, repair_type, repair_tool):
        """Send appropriate failure messages."""
        armor_type = getattr(armor_item, 'armor_type', 'generic')
        
        failure_messages = {
            'leather': f"You struggle with the leather working techniques needed for the {armor_item.key}.",
            'kevlar': f"The ballistic fibers of the {armor_item.key} prove too complex for your current skill level.",
            'steel': f"You lack the metalworking expertise to properly repair the {armor_item.key}.",
            'ceramic': f"The specialized ceramic compounds in the {armor_item.key} are beyond your technical knowledge.",
            'generic': f"You're unable to figure out how to properly repair the {armor_item.key}."
        }
        
        caller.msg(f"|r{failure_messages.get(armor_type, failure_messages['generic'])}|n")
        
        if repair_tool:
            caller.msg(f"Even with the {repair_tool.key}, the repair proves too challenging.")
        else:
            caller.msg("Perhaps you need better tools or more technical knowledge.")
    
    def _degrade_repair_tool(self, repair_tool):
        """Degrade tool durability from successful use."""
        if hasattr(repair_tool, 'tool_durability'):
            repair_tool.tool_durability = max(0, repair_tool.tool_durability - 1)
            
            if repair_tool.tool_durability <= 0:
                repair_tool.location.msg_contents(f"The {repair_tool.key} breaks from overuse and crumbles to pieces.")
                repair_tool.delete()
    
    def _damage_repair_tool(self, repair_tool):
        """Damage tool from critical failure."""
        if hasattr(repair_tool, 'tool_durability'):
            damage = randint(2, 5)
            repair_tool.tool_durability = max(0, repair_tool.tool_durability - damage)
            
            repair_tool.location.msg_contents(f"The {repair_tool.key} is damaged from the failed repair attempt!")
            
            if repair_tool.tool_durability <= 0:
                repair_tool.location.msg_contents(f"The {repair_tool.key} breaks completely and is destroyed.")
                repair_tool.delete()
    
    def _has_workshop_access(self, caller):
        """Check if caller has access to a workshop for full repairs."""
        # Check current location for workshop tools
        if caller.location:
            for item in caller.location.contents:
                if (hasattr(item, 'repair_tool_type') and 
                    item.repair_tool_type == 'workshop_bench'):
                    return True
        
        # Check caller's inventory for portable workshop tools
        for item in caller.contents:
            if (hasattr(item, 'workshop_tool') and 
                getattr(item, 'workshop_tool', False)):
                return True
        
        return False


class CmdSlot(Command):
    """
    Install armor plates into plate carriers.
    
    Usage:
        slot <plate> <carrier> [<slot>]             - Install plate in carrier
        slot <plate> in <carrier> [<slot>]          - Install plate in carrier  
        slot list [<carrier>]                       - List plate configurations
        slot                                        - List all plate carriers
        
    Install armor plates into modular plate carriers to customize protection.
    Different plate types provide various protection levels and weight trade-offs.
    If no slot is specified, the system will choose the best available slot.
    
    Examples:
        slot ballistic plate carrier
        slot ballistic plate in carrier chest
        slot medium plate in vest back
    """
    
    key = "slot"
    aliases = []
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        
        if not args:
            # List all plate carriers
            self._list_plate_carriers(caller)
        elif len(args) == 1:
            # Show specific carrier details or handle "list"
            if args[0].lower() == "list":
                self._list_plate_carriers(caller)
            else:
                self._show_carrier_details(caller, args[0])
        elif len(args) == 2 and args[0].lower() == "list":
            # Show specific carrier details  
            self._show_carrier_details(caller, args[1])
        elif len(args) >= 2:
            # Parse different syntax patterns
            self._parse_install_command(caller, args)
        else:
            caller.msg("Usage: slot <plate> [in] <carrier> [<slot>] | slot list [<carrier>]")
    
    def _parse_install_command(self, caller, args):
        """Parse various install command syntaxes."""
        # Pattern 1: slot <plate> <carrier> [<slot>]
        # Pattern 2: slot <plate> in <carrier> [<slot>]
        
        if len(args) >= 3 and args[1].lower() == "in":
            # Pattern 2: slot <plate> in <carrier> [<slot>]
            plate_name = args[0]
            carrier_name = args[2]
            slot_name = args[3] if len(args) > 3 else None
            self._install_plate(caller, plate_name, carrier_name, slot_name)
        elif len(args) >= 2:
            # Pattern 1: slot <plate> <carrier> [<slot>]
            plate_name = args[0]
            carrier_name = args[1]
            slot_name = args[2] if len(args) > 2 else None
            self._install_plate(caller, plate_name, carrier_name, slot_name)
        else:
            caller.msg("Usage: slot <plate> [in] <carrier> [<slot>] | slot list [<carrier>]")
    
    def _list_plate_carriers(self, caller):
        """List all available plate carriers and their configurations."""
        carriers = self._find_plate_carriers(caller)
        
        if not carriers:
            caller.msg("You don't have any plate carriers.")
            return
        
        caller.msg("|wYour Plate Carriers:|n")
        for carrier in carriers:
            carrier_name = carrier.key
            installed_plates = getattr(carrier, 'installed_plates', {})
            plate_slots = getattr(carrier, 'plate_slots', [])
            
            # Calculate total protection
            base_rating = getattr(carrier, 'armor_rating', 0)
            plate_rating = sum(getattr(plate, 'armor_rating', 0) for plate in installed_plates.values() if plate)
            total_rating = base_rating + plate_rating
            
            # Calculate total weight
            carrier_weight = getattr(carrier, 'weight', 0)
            plate_weight = sum(getattr(plate, 'weight', 0) for plate in installed_plates.values() if plate)
            total_weight = carrier_weight + plate_weight
            
            caller.msg(f"\n|c{carrier_name}|n (Total Protection: {total_rating}, Weight: {total_weight:.1f} lbs)")
            
            for slot in plate_slots:
                if slot in installed_plates and installed_plates[slot]:
                    plate = installed_plates[slot]
                    plate_info = f"|g{plate.key}|n (Rating: {getattr(plate, 'armor_rating', 0)}, Weight: {getattr(plate, 'weight', 0):.1f} lbs)"
                else:
                    plate_info = "|r[Empty]|n"
                caller.msg(f"  {slot.title()}: {plate_info}")
    
    def _show_carrier_details(self, caller, carrier_name):
        """Show detailed information about a specific carrier."""
        carrier = self._find_carrier_by_name(caller, carrier_name)
        if not carrier:
            return
        
        # Basic info
        caller.msg(f"\n|w=== {carrier.key.title()} ===|n")
        caller.msg(f"|xDescription:|n {carrier.desc}")
        
        # Configuration
        base_rating = getattr(carrier, 'armor_rating', 0)
        installed_plates = getattr(carrier, 'installed_plates', {})
        plate_slots = getattr(carrier, 'plate_slots', [])
        
        plate_rating = sum(getattr(plate, 'armor_rating', 0) for plate in installed_plates.values() if plate)
        total_rating = base_rating + plate_rating
        
        carrier_weight = getattr(carrier, 'weight', 0)
        plate_weight = sum(getattr(plate, 'weight', 0) for plate in installed_plates.values() if plate)
        total_weight = carrier_weight + plate_weight
        
        caller.msg(f"\n|xCarrier Statistics:|n")
        caller.msg(f"  Base Protection: {base_rating}/10")
        caller.msg(f"  Plate Protection: {plate_rating}/10")
        caller.msg(f"  Total Protection: {total_rating}/10")
        caller.msg(f"  Carrier Weight: {carrier_weight:.1f} lbs")
        caller.msg(f"  Plate Weight: {plate_weight:.1f} lbs")
        caller.msg(f"  Total Weight: {total_weight:.1f} lbs")
        
        caller.msg(f"\n|xPlate Configuration:|n")
        for slot in plate_slots:
            if slot in installed_plates and installed_plates[slot]:
                plate = installed_plates[slot]
                condition = self._get_condition_color(plate)
                caller.msg(f"  {slot.title()}: |g{plate.key}|n {condition}")
            else:
                caller.msg(f"  {slot.title()}: |r[Empty Slot]|n")
    
    def _install_plate(self, caller, plate_name, carrier_name, slot_name):
        """Install a plate in a carrier."""
        # Find the plate
        plate = self._find_plate_by_name(caller, plate_name)
        if not plate:
            return
        
        # Find the carrier
        carrier = self._find_carrier_by_name(caller, carrier_name)
        if not carrier:
            return
        
        # Validate carrier can accept plates
        if not getattr(carrier, 'is_plate_carrier', False):
            caller.msg(f"The {carrier.key} is not a plate carrier system.")
            return
        
        plate_slots = getattr(carrier, 'plate_slots', [])
        if not plate_slots:
            caller.msg(f"The {carrier.key} doesn't have any plate slots.")
            return
        
        # Determine slot
        if slot_name:
            if slot_name.lower() not in [slot.lower() for slot in plate_slots]:
                caller.msg(f"The {carrier.key} doesn't have a '{slot_name}' slot.")
                caller.msg(f"Available slots: {', '.join(plate_slots)}")
                return
            target_slot = slot_name.lower()
        else:
            # Auto-assign to first empty slot
            installed_plates = getattr(carrier, 'installed_plates', {})
            empty_slots = [slot for slot in plate_slots if slot not in installed_plates or not installed_plates[slot]]
            if not empty_slots:
                caller.msg(f"The {carrier.key} has no empty slots.")
                return
            target_slot = empty_slots[0]
        
        # Check if slot is already occupied
        installed_plates = getattr(carrier, 'installed_plates', {})
        if target_slot in installed_plates and installed_plates[target_slot]:
            existing_plate = installed_plates[target_slot]
            caller.msg(f"The {target_slot} slot already contains {existing_plate.key}.")
            caller.msg(f"Use 'plate remove {existing_plate.key} from {carrier.key}' first.")
            return
        
        # Validate plate compatibility (future: size checking)
        if not getattr(plate, 'is_armor_plate', False):
            caller.msg(f"The {plate.key} is not an armor plate.")
            return
        
        # Install the plate
        if not hasattr(carrier, 'installed_plates'):
            carrier.installed_plates = {}
        
        carrier.installed_plates[target_slot] = plate
        
        # Move plate to carrier (it's now "installed", not carried separately)
        plate.location = carrier
        
        # Success messages
        caller.msg(f"|gYou install the {plate.key} into the {target_slot} slot of your {carrier.key}.|n")
        
        # Show new rating
        total_rating = self._calculate_total_rating(carrier)
        caller.msg(f"New total protection: {total_rating}")
        
        # Location message
        if caller.location:
            caller.location.msg_contents(f"{caller.key} installs an armor plate into their {carrier.key}.", exclude=[caller])
    
    def _remove_plate(self, caller, plate_name, carrier_name):
        """Remove a plate from a carrier."""
        # Find the carrier
        carrier = self._find_carrier_by_name(caller, carrier_name)
        if not carrier:
            return
        
        # Find the installed plate
        installed_plates = getattr(carrier, 'installed_plates', {})
        target_plate = None
        target_slot = None
        
        for slot, plate in installed_plates.items():
            plate_aliases = plate.aliases.all() if plate and hasattr(plate, 'aliases') else []
            if plate and (plate_name.lower() in plate.key.lower() or 
                         plate_name.lower() in [alias.lower() for alias in plate_aliases]):
                target_plate = plate
                target_slot = slot
                break
        
        if not target_plate:
            caller.msg(f"The {carrier.key} doesn't have a plate matching '{plate_name}'.")
            return
        
        # Remove the plate
        installed_plates[target_slot] = None
        carrier.installed_plates = installed_plates
        
        # Move plate back to caller's inventory
        target_plate.location = caller
        
        # Success messages
        caller.msg(f"|yYou remove the {target_plate.key} from the {target_slot} slot of your {carrier.key}.|n")
        
        # Show new rating
        total_rating = self._calculate_total_rating(carrier)
        caller.msg(f"New total protection: {total_rating}")
        
        # Location message
        if caller.location:
            caller.location.msg_contents(f"{caller.key} removes an armor plate from their {carrier.key}.", exclude=[caller])
    
    def _swap_plates(self, caller, old_plate_name, new_plate_name):
        """Quick swap between plates in carriers."""
        # Find old plate (must be installed)
        old_plate, old_carrier, old_slot = self._find_installed_plate(caller, old_plate_name)
        if not old_plate:
            caller.msg(f"You don't have an installed plate matching '{old_plate_name}'.")
            return
        
        # Find new plate (must be in inventory)
        new_plate = self._find_plate_by_name(caller, new_plate_name)
        if not new_plate:
            return
        
        if not getattr(new_plate, 'is_armor_plate', False):
            caller.msg(f"The {new_plate.key} is not an armor plate.")
            return
        
        # Perform the swap
        installed_plates = getattr(old_carrier, 'installed_plates', {})
        installed_plates[old_slot] = new_plate
        old_carrier.installed_plates = installed_plates
        
        # Move plates
        old_plate.location = caller  # Old plate to inventory
        new_plate.location = old_carrier  # New plate to carrier
        
        # Success messages
        caller.msg(f"|gYou quickly swap the {old_plate.key} for the {new_plate.key} in your {old_carrier.key}.|n")
        
        # Show rating change
        total_rating = self._calculate_total_rating(old_carrier)
        caller.msg(f"New total protection: {total_rating}")
        
        # Location message
        if caller.location:
            caller.location.msg_contents(f"{caller.key} performs a tactical plate swap on their {old_carrier.key}.", exclude=[caller])
    
    def _find_plate_carriers(self, caller):
        """Find all plate carriers (worn or carried)."""
        carriers = []
        
        # Check worn items
        if hasattr(caller, 'worn_items') and caller.worn_items:
            for location, items in caller.worn_items.items():
                for item in items:
                    if getattr(item, 'is_plate_carrier', False):
                        carriers.append(item)
        
        # Check inventory
        for item in caller.contents:
            if getattr(item, 'is_plate_carrier', False):
                carriers.append(item)
        
        return carriers
    
    def _find_carrier_by_name(self, caller, carrier_name):
        """Find a specific carrier by name."""
        # Use Evennia's search to handle numbered objects
        candidates = caller.search(
            carrier_name,
            location=caller,
            quiet=True
        )
        
        if not candidates:
            caller.msg(f"You don't have a plate carrier matching '{carrier_name}'.")
            return None
        
        # If multiple matches, return first one
        if isinstance(candidates, list):
            candidates = candidates[0]
            
        # Check if it's actually a plate carrier
        if not getattr(candidates, 'is_plate_carrier', False):
            caller.msg(f"The {candidates.key} is not a plate carrier.")
            return None
            
        return candidates
    
    def _find_plate_by_name(self, caller, plate_name):
        """Find an armor plate by name in inventory."""
        # Use Evennia's search to handle numbered objects (e.g., "plate-2", "2-plate", "2nd plate")
        candidates = caller.search(
            plate_name,
            location=caller,
            quiet=True
        )
        
        # If search failed, return None
        if not candidates:
            caller.msg(f"You don't have an armor plate matching '{plate_name}'.")
            return None
        
        # If multiple matches, return first one (caller.search handles ordinals automatically)
        if isinstance(candidates, list):
            candidates = candidates[0]
            
        # Check if the found item is actually an armor plate
        if not getattr(candidates, 'is_armor_plate', False):
            caller.msg(f"The {candidates.key} is not an armor plate.")
            return None
            
        return candidates
    
    def _find_installed_plate(self, caller, plate_name):
        """Find an installed plate by name."""
        carriers = self._find_plate_carriers(caller)
        for carrier in carriers:
            installed_plates = getattr(carrier, 'installed_plates', {})
            for slot, plate in installed_plates.items():
                if not plate:
                    continue
                # Check if plate matches the search term
                plate_aliases = plate.aliases.all() if hasattr(plate, 'aliases') else []
                if (plate_name.lower() in plate.key.lower() or
                    plate_name.lower() in [alias.lower() for alias in plate_aliases]):
                    return plate, carrier, slot
        
        return None, None, None
    
    def _calculate_total_rating(self, carrier):
        """Calculate total armor rating for carrier."""
        base_rating = getattr(carrier, 'armor_rating', 0)
        installed_plates = getattr(carrier, 'installed_plates', {})
        plate_rating = sum(getattr(plate, 'armor_rating', 0) for plate in installed_plates.values() if plate)
        return base_rating + plate_rating
    
    def _get_condition_color(self, item):
        """Get color-coded condition indicator."""
        durability = getattr(item, 'armor_durability', 0)
        max_durability = getattr(item, 'max_armor_durability', 0)
        
        if max_durability <= 0:
            return ""
        
        condition_percent = durability / max_durability
        if condition_percent > 0.7:
            return "|g(Good)|n"
        elif condition_percent > 0.3:
            return "|y(Fair)|n"
        else:
            return "|r(Poor)|n"


class CmdUnslot(Command):
    """
    Remove armor plates from plate carriers.
    
    Usage:
        unslot <plate>                      - Remove plate from any carrier
        unslot <plate> from <carrier>       - Remove plate from specific carrier
        unslot <slot> from <carrier>        - Remove plate from specific slot
        
    Remove installed armor plates from modular plate carriers. The plate
    will be added to your inventory if you have space, otherwise it will
    drop to the ground.
    """
    
    key = "unslot" 
    aliases = []
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        
        if not args:
            caller.msg("Usage: unslot <plate> [from <carrier>] | unslot <slot> from <carrier>")
            return
        
        if len(args) == 1:
            # Remove plate from any carrier
            plate_name = args[0]
            self._remove_plate_by_name(caller, plate_name)
        elif len(args) >= 3 and args[1].lower() == "from":
            # Remove from specific carrier or slot
            item_name = args[0]  # Could be plate name or slot name
            carrier_name = args[2]
            self._remove_from_carrier(caller, item_name, carrier_name)
        else:
            caller.msg("Usage: unslot <plate> [from <carrier>] | unslot <slot> from <carrier>")
    
    def _remove_plate_by_name(self, caller, plate_name):
        """Remove a plate by name from any carrier the player is wearing."""
        # Find all worn plate carriers
        worn_carriers = []
        for item in caller.contents:
            if (hasattr(item, 'is_plate_carrier') and 
                getattr(item, 'is_plate_carrier', False) and
                item in getattr(caller, 'worn_items', {}).get('torso', [])):
                worn_carriers.append(item)
        
        if not worn_carriers:
            caller.msg("You are not wearing any plate carriers.")
            return
        
        # Search for the plate in all carriers
        for carrier in worn_carriers:
            installed_plates = getattr(carrier, 'installed_plates', {})
            for slot_name, plate in installed_plates.items():
                if plate and plate_name.lower() in plate.key.lower():
                    return self._do_remove_plate(caller, plate, carrier, slot_name)
        
        caller.msg(f"You don't have any plate matching '{plate_name}' installed in your carriers.")
    
    def _remove_from_carrier(self, caller, item_name, carrier_name):
        """Remove plate from specific carrier, by plate name or slot name."""
        # Find the carrier
        carrier = None
        for item in caller.contents:
            if (carrier_name.lower() in item.key.lower() and
                hasattr(item, 'is_plate_carrier') and 
                getattr(item, 'is_plate_carrier', False)):
                carrier = item
                break
        
        if not carrier:
            caller.msg(f"You don't have a plate carrier matching '{carrier_name}'.")
            return
        
        installed_plates = getattr(carrier, 'installed_plates', {})
        
        # Try as slot name first
        if item_name.lower() in installed_plates:
            slot_name = item_name.lower()
            plate = installed_plates[slot_name]
            if plate:
                return self._do_remove_plate(caller, plate, carrier, slot_name)
            else:
                caller.msg(f"The {slot_name} slot is already empty.")
                return
        
        # Try as plate name
        for slot_name, plate in installed_plates.items():
            if plate and item_name.lower() in plate.key.lower():
                return self._do_remove_plate(caller, plate, carrier, slot_name)
        
        caller.msg(f"No plate or slot matching '{item_name}' found in {carrier.key}.")
    
    def _do_remove_plate(self, caller, plate, carrier, slot_name):
        """Actually perform the plate removal."""
        # Remove from carrier
        installed_plates = getattr(carrier, 'installed_plates', {})
        installed_plates[slot_name] = None
        
        # Add to player inventory
        plate.move_to(caller, quiet=True)
        
        # Success messages
        caller.msg(f"You remove the {plate.key} from the {slot_name} slot of your {carrier.key}.")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} removes a plate from their {carrier.key}.",
                exclude=[caller]
            )