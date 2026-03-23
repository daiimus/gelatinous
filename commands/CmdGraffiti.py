"""
Spray Commands

Unified spray command for spray painting and solvent cleaning
based on the type of can used and syntax provided.
"""

from evennia import Command, create_object
from evennia.utils import delay
from typeclasses.items import SprayCanItem, SolventCanItem
from typeclasses.objects import GraffitiObject, BloodPool
from world.identity_utils import msg_room_identity
import random

# Map color names to Evennia ANSI color codes
GRAFFITI_COLOR_MAP = {
    'red': 'r', 'blue': 'b', 'green': 'g', 'yellow': 'y',
    'magenta': 'm', 'cyan': 'c', 'white': 'w', 'black': 'x',
    'purple': 'm', 'pink': 'm', 'orange': 'y',
}


class CmdGraffiti(Command):
    """
    Spray paint graffiti or clean with solvent.
    
    Usage:
        spray "<message>" with <spray_can>    - Spray paint graffiti
        spray here with <solvent_can>         - Clean graffiti and blood stains in room
        
    Examples:
        spray "HELLO WORLD" with red_can
        spray "WAKKA WAKKA!" with spray_can
        spray here with solvent_can
        
    Paint cans have finite paint - if you run out mid-message, your graffiti
    will be cut short. Messages are limited to 100 characters.
    
    Solvent cans can clean existing graffiti and blood stains from the current room, 
    removing random characters from graffiti messages and potentially removing blood 
    evidence. Multiple applications may be needed to completely clean surfaces.
    
    To change spray can colors, use: press <color> on <spray_can>
    """
    
    key = "spray"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the spray command."""
        if not self.args:
            self.caller.msg("Usage: spray \"<message>\" with <can> OR spray here with <can>")
            return
        
        # Parse command patterns to determine intent
        args_stripped = self.args.strip()
        args_lower = args_stripped.lower()
        
        if args_lower.startswith("here with "):
            # User wants to clean - get the can name
            can_name = args_stripped[10:].strip()
            intent = "clean"
            message = None
        elif " with " in args_stripped:
            # User wants to spray paint - parse message and can name
            message_part, can_part = args_stripped.rsplit(" with ", 1)
            message = message_part.strip().strip('"\'')  # Remove quotes if present
            can_name = can_part.strip()
            intent = "spraypaint"
        else:
            self.caller.msg("Usage: spray \"<message>\" with <can> OR spray here with <can>")
            return
        
        # Find the can object - search inventory and wielded items using standard search
        # First try inventory
        inventory_candidates = list(self.caller.contents)
        can = None
        if inventory_candidates:
            can = self.caller.search(can_name, candidates=inventory_candidates, quiet=True)
        
        # If not found in inventory, try wielded items (Mr. Hands system)
        if not can and hasattr(self.caller, 'hands'):
            hands = self.caller.hands
            held_items = [item for item in hands.values() if item]
            if held_items:
                can = self.caller.search(can_name, candidates=held_items, quiet=True)
        
        if not can:
            self.caller.msg(f"You don't have a '{can_name}'.")
            return
        
        can = can[0]  # Get first match
        
        # Check what type of aerosol contents the can has
        aerosol_contents = can.db.aerosol_contents
        if not aerosol_contents:
            self.caller.msg(f"You can't use {can.get_display_name(self.caller)} for spraying.")
            return
        
        # Route to appropriate handler based on can contents AND user intent
        if aerosol_contents == "spraypaint":
            if intent == "spraypaint":
                self._handle_spray_paint_with_spraypaint(can, message)
            else:  # intent == "clean"
                self.caller.msg(f"You can't clean with {can.get_display_name(self.caller)} - it contains paint, not solvent.")
        elif aerosol_contents == "solvent":
            if intent == "clean":
                self._handle_clean_with_solvent(can)
            else:  # intent == "spraypaint"
                self.caller.msg(f"You can't spray paint with {can.get_display_name(self.caller)} - it contains solvent, not paint.")
        else:
            self.caller.msg(f"You can't use {can.get_display_name(self.caller)} for spraying - unknown contents: {aerosol_contents}.")
    
    def _handle_spray_paint_with_spraypaint(self, spray_can, message):
        """Handle spray painting with a spray paint can."""
        if not message:
            self.caller.msg("You need to specify a message to spray.")
            return
        
        if len(message) > 100:
            self.caller.msg("Your message is too long! Keep it under 100 characters.")
            return
        
        # Check if spray can has paint
        if spray_can.db.aerosol_level <= 0:
            self.caller.msg(f"{spray_can.get_display_name(self.caller)} is empty!")
            return
        
        # Calculate paint needed (1 paint per character)
        paint_needed = len(message)
        paint_available = spray_can.db.aerosol_level
        
        # Determine actual message length based on available paint
        ran_out_mid_message = False
        if paint_needed > paint_available:
            message = message[:paint_available] + "..."  # Add ellipsis to show it was cut off
            paint_used = paint_available
            ran_out_mid_message = True
        else:
            paint_used = paint_needed
        
        # Get the current color and name before using paint (in case can gets deleted)
        current_color = spray_can.db.current_color or "white"  # Default fallback
        can_name_for_message = spray_can.get_display_name(self.caller)
        
        # Use the paint
        spray_can.use_paint(paint_used)
        
        # Find or create the room's graffiti object
        graffiti_obj = None
        for obj in self.caller.location.contents:
            if isinstance(obj, GraffitiObject):
                graffiti_obj = obj
                break
        
        if not graffiti_obj:
            # Create new graffiti object for this room
            graffiti_obj = create_object(
                typeclass=GraffitiObject,
                key="graffiti",
                location=self.caller.location
            )
        
        # Add the graffiti message to the object
        graffiti_obj.add_graffiti(message, current_color, self.caller)
        
        # Messages - using proper Evennia color formatting
        color_code = GRAFFITI_COLOR_MAP.get(current_color.lower() if current_color else 'white', 'w')
        colored_message = f"|{color_code}{message}|n"
        
        # Create appropriate message based on whether can ran out
        if ran_out_mid_message:
            self.caller.msg(f"You start to spray on the wall with a {can_name_for_message}, but it runs out of paint mid-message! You manage to spray '{colored_message}' before the can crumples up and becomes useless.")
            msg_room_identity(
                location=self.caller.location,
                template=f"{{actor}} starts to spray on the wall, but their can runs out of paint mid-message, managing only '{colored_message}' before tossing the empty can aside.",
                char_refs={"actor": self.caller},
                exclude=[self.caller],
            )
        else:
            self.caller.msg(f"You spray '{colored_message}' on the wall with a {can_name_for_message}.")
            msg_room_identity(
                location=self.caller.location,
                template=f"{{actor}} sprays '{colored_message}' on the wall.",
                char_refs={"actor": self.caller},
                exclude=[self.caller],
            )
    
    def _handle_clean_with_solvent(self, solvent_can):
        """Handle cleaning graffiti and blood stains with a solvent can."""
        
        # Check if solvent can has uses left
        if solvent_can.db.aerosol_level <= 0:
            self.caller.msg(f"{solvent_can.get_display_name(self.caller)} is empty!")
            return
        
        # Find both graffiti and blood pool objects
        graffiti_obj = None
        blood_pools = []
        
        for obj in self.caller.location.contents:
            if isinstance(obj, GraffitiObject):
                graffiti_obj = obj
            elif isinstance(obj, BloodPool) or obj.db.is_blood_pool:
                blood_pools.append(obj)
        
        # Check if there's anything to clean
        has_graffiti = graffiti_obj and graffiti_obj.has_graffiti()
        has_blood = any(pool.db.bleeding_incidents for pool in blood_pools)
        
        if not has_graffiti and not has_blood:
            self.caller.msg("There's nothing here to clean.")
            return
        
        # Use solvent (up to 10 units)
        solvent_used = min(10, solvent_can.db.aerosol_level)
        solvent_can.use_solvent(solvent_used)
        
        # Track what was cleaned
        graffiti_cleaned = False
        blood_cleaned = False
        cleaned_items = []
        
        # Clean graffiti if present
        if has_graffiti:
            chars_affected = graffiti_obj.remove_random_characters(solvent_used)
            if chars_affected > 0:
                graffiti_cleaned = True
                cleaned_items.append("|Cgraffiti|n")
        
        # Clean blood pools if present
        if has_blood:
            for blood_pool in blood_pools:
                if blood_pool.db.bleeding_incidents:
                    # Determine tool quality based on solvent can type
                    tool_quality = "basic"  # Default for spray cans
                    if solvent_can.db.quality is not None:
                        tool_quality = solvent_can.db.quality
                    
                    cleaned_volume, clean_result = blood_pool.clean_with_solvent(self.caller, tool_quality)
                    if cleaned_volume > 0:
                        blood_cleaned = True
                        cleaned_items.append("|Rblood stains|n")
        
        # Generate messages based on what was cleaned
        if graffiti_cleaned or blood_cleaned:
            if len(cleaned_items) == 1:
                item_desc = cleaned_items[0]
            elif len(cleaned_items) == 2:
                item_desc = f"{cleaned_items[0]} and {cleaned_items[1]}"
            else:
                item_desc = "various stains"
            
            # Customize the action description based on what's being cleaned
            if graffiti_cleaned and blood_cleaned:
                action_desc = "watching the colors dissolve and stains break down"
            elif graffiti_cleaned:
                action_desc = "watching the colors dissolve away"
            else:  # blood only
                action_desc = "watching the stains break down and fade"
            
            # Immediate action message
            self.caller.msg(f"You apply solvent to the {item_desc}, {action_desc}.")
            msg_room_identity(
                location=self.caller.location,
                template=f"{{actor}} applies solvent to the {item_desc}, {action_desc}.",
                char_refs={"actor": self.caller},
                exclude=[self.caller],
            )
            
            # Delayed atmospheric message to everyone including the player
            def delayed_message():
                if self.caller.location:  # Make sure location still exists
                    if graffiti_cleaned and blood_cleaned:
                        evaporate_desc = "The colors break down and the solvent evaporates, taking the stains with it."
                    elif graffiti_cleaned:
                        evaporate_desc = f"The colors break down and the solvent evaporates, taking the {item_desc} with it."
                    else:  # blood only
                        evaporate_desc = f"The solvent breaks down the evidence and evaporates, removing the {item_desc}."
                    
                    self.caller.location.msg_contents(evaporate_desc)
            
            delay(3, delayed_message)
            
        else:
            self.caller.msg("The solvent doesn't seem to affect anything here.")
            msg_room_identity(
                location=self.caller.location,
                template="{actor} scrubs at the surfaces with solvent.",
                char_refs={"actor": self.caller},
                exclude=[self.caller],
            )


class CmdPress(Command):
    """
    Press colored buttons on spray cans to change colors.
    
    Usage:
        press <color> on <spray_can>
        
    Examples:
        press blue on spray_can
        press red on my_can
        press cyan on paint_can
        
    Changes the color of paint that comes out of the spray can.
    Available colors depend on the specific spray can.
    """
    
    key = "press"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the press command."""
        if not self.args:
            self.caller.msg("Usage: press <color> on <spray_can>")
            return
        
        if " on " not in self.args:
            self.caller.msg("Usage: press <color> on <spray_can>")
            return
        
        # Split color and can name
        color_part, can_part = self.args.rsplit(" on ", 1)
        new_color = color_part.strip().lower()
        can_name = can_part.strip()
        
        # Validate color name
        if not new_color:
            self.caller.msg("You need to specify a color to press.")
            return
        
        # Find the spray can - check inventory and wielded items
        spray_can = self.caller.search(can_name, candidates=self.caller.contents, quiet=True)
        
        # If not found in inventory, check wielded items (Mr. Hands system)
        if not spray_can and hasattr(self.caller, 'hands'):
            hands = self.caller.hands
            for hand_name, held_item in hands.items():
                if held_item:
                    # Check display name, key, and aliases
                    if (can_name.lower() in held_item.get_display_name(self.caller).lower() or
                        can_name.lower() in held_item.key.lower() or
                        (hasattr(held_item, 'aliases') and held_item.aliases.all() and
                         any(can_name.lower() in alias.lower() for alias in held_item.aliases.all()))):
                        spray_can = [held_item]
                        break
        
        if not spray_can:
            self.caller.msg(f"You don't have a '{can_name}'.")
            return
        
        spray_can = spray_can[0]  # Get first match
        
        # Check if it's an aerosol can with color-changing capability (spraypaint)
        aerosol_contents = spray_can.db.aerosol_contents
        if not aerosol_contents:
            self.caller.msg(f"You can't press colors on {spray_can.get_display_name(self.caller)}.")
            return
        
        # Verify it's a spray can (not solvent)
        if aerosol_contents != "spraypaint":
            self.caller.msg(f"You can't press colors on {spray_can.get_display_name(self.caller)}.")
            return
        
        # Check if color is available
        if not spray_can.set_color(new_color):
            available_colors = spray_can.db.available_colors
            
            # Color mapping for display
            color_map = {
                'red': 'r', 'blue': 'b', 'green': 'g', 'yellow': 'y',
                'magenta': 'm', 'cyan': 'c', 'white': 'w', 'black': 'x'
            }
            
            # Create colored version of each color name
            colored_names = []
            for color in available_colors:
                color_code = color_map.get(color.lower(), 'w')
                colored_names.append(f"|{color_code}{color}|n")
            
            # Format with proper grammar
            if len(colored_names) > 1:
                color_list = ", ".join(colored_names[:-1]) + f", and {colored_names[-1]}"
            else:
                color_list = colored_names[0] if colored_names else "none"
            
            self.caller.msg(f"Available colors: {color_list}.")
            return
        
        # Messages - color was successfully changed by set_color()
        color_code = GRAFFITI_COLOR_MAP.get(new_color.lower(), 'w')
        colored_name = f"|{color_code}{new_color}|n"
        
        self.caller.msg(f"You press the {colored_name} button on {spray_can.get_display_name(self.caller)}.")
        msg_room_identity(
            location=self.caller.location,
            template="{actor} presses a button on their spray can.",
            char_refs={"actor": self.caller},
            exclude=[self.caller],
        )
