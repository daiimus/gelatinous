from evennia import DefaultObject, AttributeProperty
from world.combat.constants import DEFAULT_CLOTHING_LAYER

# ANSI Color definitions for clothing descriptions
COLOR_DEFINITIONS = {
    # Standard colors
    "black": "|=l",       # Black (256-color)
    "red": "|r",          # Red
    "green": "|g",        # Green
    "yellow": "|y",       # Yellow
    "blue": "|b",         # Blue
    "magenta": "|m",      # Magenta
    "cyan": "|c",         # Cyan
    "white": "|w",        # White
    # Bright colors
    "bright_black": "|K", # Dark Gray
    "bright_red": "|R",   # Bright Red
    "bright_green": "|G", # Bright Green
    "bright_yellow": "|Y",# Bright Yellow
    "bright_blue": "|B",  # Bright Blue
    "bright_magenta": "|M", # Bright Magenta
    "bright_cyan": "|C",  # Bright Cyan
    "bright_white": "|W", # Bright White
}

class Item(DefaultObject):
    """
    A general-purpose item. In Gelatinous Monster, all items are
    potential weapons. This typeclass ensures that all objects have
    basic combat-relevant properties.
    
    Items become wearable clothing by setting coverage and worn_desc attributes.
    """
    
    # ===================================================================
    # CLOTHING SYSTEM ATTRIBUTES
    # ===================================================================
    
    # Coverage definition - which body locations this item covers (base state)
    # Empty list = not wearable, populated list = clothing item
    coverage = AttributeProperty([], autocreate=True)
    
    # Clothing-specific description that appears when worn (base state)
    # Empty string = not clothing, populated = worn description
    worn_desc = AttributeProperty("", autocreate=True)
    
    # ANSI color definition for this item
    # Used for atmospheric descriptions and visual immersion
    color = AttributeProperty("", autocreate=True)
    
    # Material type for this item (for future armor/crafting systems)
    # Examples: "leather", "steel", "silk", "kevlar", "titanium"
    material = AttributeProperty("", autocreate=True)
    
    # Weight of item in pounds (for encumbrance system)
    # Examples: t-shirt=0.2, jeans=1.2, kevlar vest=4.5, steel plate=12.0
    weight = AttributeProperty(0.5, autocreate=True)  # Default 0.5 lbs
    
    # Layer priority for stacking items (higher = outer layer)
    layer = AttributeProperty(DEFAULT_CLOTHING_LAYER, autocreate=True)
    
    # ===================================================================
    # ARMOR SYSTEM ATTRIBUTES
    # ===================================================================
    
    # Armor rating (0 = no armor, 10 = maximum protection)
    armor_rating = AttributeProperty(0, autocreate=True)
    
    # Type of armor material (affects damage type effectiveness)
    armor_type = AttributeProperty("", autocreate=True)
    
    # Current armor durability  
    armor_durability = AttributeProperty(0, autocreate=True)
    
    # Maximum armor durability
    max_armor_durability = AttributeProperty(0, autocreate=True)
    
    # Original armor rating (for repair calculations)
    base_armor_rating = AttributeProperty(0, autocreate=True)
    
    # Plate carrier system - can accept armor plates
    is_plate_carrier = AttributeProperty(False, autocreate=True)
    
    # Installed plates for plate carriers (dict of slot_name: plate_object)
    installed_plates = AttributeProperty({}, autocreate=True)
    
    # Available plate slots for carriers (list of slot names)
    plate_slots = AttributeProperty([], autocreate=True)
    
    # Is this item an armor plate that can be installed?
    is_armor_plate = AttributeProperty(False, autocreate=True)
    
    # Plate size compatibility (small, medium, large, extra_large)
    plate_size = AttributeProperty("", autocreate=True)
    
    # Multiple style properties for combination states
    style_properties = AttributeProperty({}, autocreate=True)
    # Structure: {"adjustable": "rolled", "closure": "zipped"}
    
    # Style configurations defining all possible combinations
    style_configs = AttributeProperty({}, autocreate=True)
    # Structure: {
    #     "adjustable": {
    #         "rolled": {"coverage_mod": [...], "desc_mod": "with sleeves rolled up"},
    #         "normal": {"coverage_mod": [], "desc_mod": ""}
    #     },
    #     "closure": {
    #         "zipped": {"coverage_mod": [...], "desc_mod": "zipped tight"},
    #         "unzipped": {"coverage_mod": [...], "desc_mod": "hanging open"}
    #     }
    # }
    
    # ===================================================================
    # STICKY GRENADE SYSTEM ATTRIBUTES
    # ===================================================================
    
    # Metal content level (0-10): Amount of metal in the item
    # 0 = No metal whatsoever
    # 1-3 = Minimal metal (buckles, rivets, small fasteners)
    # 4-6 = Moderate metal (metal plates, reinforcements, chainmail sections)
    # 7-9 = Heavy metal (predominantly metal construction)
    # 10 = Pure metal (entirely metal construction)
    metal_level = AttributeProperty(0, autocreate=True)
    
    # Magnetic responsiveness level (0-10): How magnetic the metal is
    # 0 = Non-magnetic (no ferrous metals - aluminum, titanium, synthetic, cloth, leather)
    # 1-3 = Weakly magnetic (stainless steel, treated/alloyed metals with low iron content)
    # 4-6 = Moderately magnetic (mild steel, some carbon steel)
    # 7-9 = Highly magnetic (carbon steel, most ferrous alloys)
    # 10 = Pure ferrous metal (raw iron, unalloyed steel)
    # NOTE: Titanium and aluminum are NOT magnetic (magnetic_level=0) despite being metal
    magnetic_level = AttributeProperty(0, autocreate=True)
    
    # Reference to sticky grenade attached to this armor (if any)
    stuck_grenade = AttributeProperty(None, autocreate=True)
    
    # ===================================================================
    # CLOTHING SYSTEM METHODS
    # ===================================================================
    
    def is_wearable(self):
        """Check if this item can be worn as clothing"""
        return bool(self.coverage) and bool(self.worn_desc)
    
    def get_current_coverage(self):
        """Get coverage for current combination of style states"""
        coverage = list(self.coverage)  # Start with base coverage
        
        if not self.style_configs or not self.style_properties:
            return coverage
        
        # Apply modifications from each active style property in deterministic order
        for property_name in sorted(self.style_properties.keys()):
            property_state = self.style_properties[property_name]
            
            if property_name in self.style_configs:
                property_config = self.style_configs[property_name]
                if property_state in property_config:
                    state_config = property_config[property_state]
                    coverage_mod = state_config.get("coverage_mod", [])
                    
                    # Apply coverage modifications
                    for mod in coverage_mod:
                        if mod.startswith("+"):
                            # Add location if not already covered
                            location = mod[1:]
                            if location not in coverage:
                                coverage.append(location)
                        elif mod.startswith("-"):
                            # Remove location if currently covered
                            location = mod[1:]
                            if location in coverage:
                                coverage.remove(location)
        
        return coverage
    
    def get_current_worn_desc(self):
        """Get worn description incorporating all active style states"""
        if not self.style_configs or not self.style_properties:
            return f"{self.worn_desc}." if self.worn_desc else ""
        
        # For multi-property items, we need to handle combinations
        # Priority order: check properties in sorted order, use first non-empty desc_mod
        for property_name in sorted(self.style_properties.keys()):
            property_state = self.style_properties[property_name]
            
            if property_name in self.style_configs:
                property_config = self.style_configs[property_name]
                if property_state in property_config:
                    state_config = property_config[property_state]
                    desc_mod = state_config.get("desc_mod", "").strip()
                    if desc_mod:
                        # First non-empty desc_mod wins - this allows for sophisticated combinations
                        return f"{desc_mod}." if not desc_mod.endswith('.') else desc_mod
        
        # No active desc_mod found, use base worn_desc
        return f"{self.worn_desc}." if self.worn_desc else ""
    
    def can_style_property_to(self, property_name, state_name):
        """Check if item can transition specific property to given state"""
        if property_name not in self.style_configs:
            return False
        if state_name not in self.style_configs[property_name]:
            return False
        
        # Always allow transitions to valid states - the validation is structural, not functional
        return True
    
    def set_style_property(self, property_name, state_name):
        """Set specific style property to given state with validation"""
        if not self.can_style_property_to(property_name, state_name):
            return False
        
        if not self.style_properties:
            self.style_properties = {}
        
        self.style_properties[property_name] = state_name
        return True
    
    def get_style_property(self, property_name):
        """Get current state of specific style property"""
        from world.combat.constants import STYLE_STATE_NORMAL
        return self.style_properties.get(property_name, STYLE_STATE_NORMAL)
    
    def get_available_style_properties(self):
        """Get all available style properties and their states"""
        return {prop: list(states.keys()) for prop, states in self.style_configs.items()}
    
    def validate_plate_slot_coverage(self):
        """
        Validate that plate_slot_coverage keys match plate_slots.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not getattr(self, 'is_plate_carrier', False):
            return (True, "")  # Not a plate carrier, no validation needed
            
        plate_slots = getattr(self, 'plate_slots', [])
        slot_coverage = getattr(self, 'plate_slot_coverage', {})
        
        if not slot_coverage:
            return (True, "")  # No coverage mapping, use default behavior
            
        # Check for slots in coverage that don't exist in plate_slots
        invalid_slots = [slot for slot in slot_coverage.keys() if slot not in plate_slots]
        
        if invalid_slots:
            error_msg = f"Invalid slots in plate_slot_coverage: {', '.join(invalid_slots)}. Valid slots: {', '.join(plate_slots)}"
            return (False, error_msg)
            
        return (True, "")

    def get_current_worn_desc_with_perspective(self, looker=None, from_obj=None):
        """
        Get the current worn description with template variable processing and color integration.
        
        Args:
            looker: The character doing the looking (for perspective)
            from_obj: The object being looked at (wearer, for template variable context)
            
        Returns:
            str: Processed description with pronouns and colors
        """
        if not self.worn_desc:
            return ""
            
        # Get current style configuration
        current_desc = self.get_current_worn_desc()
        
        # Process color placeholders
        colored_desc = self._process_color_codes(current_desc)
        
        # Process template variables if we have perspective context
        if looker and from_obj and hasattr(from_obj, '_process_description_variables'):
            return from_obj._process_description_variables(colored_desc, looker, force_third_person=True)
        
        # Fallback: return without template processing
        return colored_desc
    
    def _process_color_codes(self, text):
        """
        Process color placeholder codes in text.
        
        Args:
            text (str): Text with color placeholders like {color}word|n
            
        Returns:
            str: Text with color placeholders replaced with ANSI codes
        """
        if not text:
            return text
            
        # Get color value
        color = self.color or ""
        
        # Replace color placeholder
        if color and "{color}" in text:
            color_code = COLOR_DEFINITIONS.get(color, "")
            processed = text.replace("{color}", color_code)
            return processed
        
        return text

    def at_object_creation(self):
        """
        Called once when the object is created.
        """
        # Core combat attributes
        self.db.damage = 1  # Minimal default damage
        self.db.weapon_type = "melee"  # Most objects default to melee weapons
        self.db.damage_type = "blunt"  # Default medical system injury type

        # Optional future expansion
        self.db.hands_required = 1  # Assume one-handed for now

        # Generic descriptor
        if not self.db.desc:
            self.db.desc = "It's a thing. Heavy enough to hurt if used wrong."

        # Add a boolean attribute `is_ranged` to the `Item` class
        self.db.is_ranged = False

    def return_appearance(self, looker, **kwargs):
        """
        Enhanced appearance method that shows armor information for armor items.
        
        Args:
            looker: Character looking at the item
            **kwargs: Additional appearance arguments
            
        Returns:
            str: The formatted appearance string
        """
        # Get the basic appearance first
        appearance = super().return_appearance(looker, **kwargs)
        
        # Check for stuck grenade (CRITICAL SAFETY WARNING)
        if hasattr(self, 'stuck_grenade') and self.stuck_grenade:
            grenade = self.stuck_grenade
            remaining = getattr(grenade.ndb, 'countdown_remaining', 0) if hasattr(grenade, 'ndb') else 0
            if remaining > 0:
                appearance += f"\n\n|r{'='*60}|n"
                appearance += f"\n|R!!! WARNING: LIVE GRENADE MAGNETICALLY CLAMPED TO THIS ITEM !!!|n"
                appearance += f"\n|r{'='*60}|n"
                appearance += f"\n|REXPLOSION IN {remaining} SECONDS!|n"
                appearance += f"\n|r{'='*60}|n"
            else:
                appearance += f"\n\n|rA {grenade.key} is magnetically clamped to this item.|n"
        
        # Check if this is an armor item and add armor information
        if self._is_armor_item():
            armor_info = self._get_armor_information()
            if armor_info:
                appearance += f"\n\n|w=== Armor Information ===|n\n{armor_info}"
        
        return appearance
    
    def _is_armor_item(self):
        """Check if this item has armor properties."""
        return (hasattr(self, 'armor_rating') and getattr(self, 'armor_rating', 0) > 0) or \
               (hasattr(self, 'is_plate_carrier') and getattr(self, 'is_plate_carrier', False)) or \
               hasattr(self, 'plate_type')
    
    def _get_armor_information(self):
        """Generate armor information display."""
        info_lines = []
        
        # Basic armor stats
        armor_rating = getattr(self, 'armor_rating', 0)
        armor_type = getattr(self, 'armor_type', 'generic')
        weight = getattr(self, 'weight', 0)
        
        if armor_rating > 0:
            rating_desc = self._get_rating_description(armor_rating)
            info_lines.append(f"  Protection Rating: {armor_rating} ({rating_desc})")
        
        # Armor type information
        if armor_type != 'generic':
            type_info = self._get_armor_type_info(armor_type)
            info_lines.append(f"  Armor Type: {armor_type.title()} {type_info}")
        
        # Weight
        if weight > 0:
            info_lines.append(f"  Weight: {weight} kg")
        
        # Plate carrier specific information
        if hasattr(self, 'is_plate_carrier') and getattr(self, 'is_plate_carrier', False):
            carrier_info = self._get_plate_carrier_details()
            if carrier_info:
                info_lines.extend(carrier_info)
        
        # Armor plate specific information  
        elif hasattr(self, 'plate_type'):
            plate_info = self._get_plate_details()
            if plate_info:
                info_lines.extend(plate_info)
        
        # Coverage information
        if hasattr(self, 'get_current_coverage'):
            coverage = self.get_current_coverage()
        else:
            coverage = getattr(self, 'coverage', [])
        
        if coverage:
            coverage_str = ", ".join(coverage)
            info_lines.append(f"  Coverage: {coverage_str}")
        
        # Condition
        condition = self._get_condition_info()
        if condition:
            info_lines.append(f"  Condition: {condition}")
        
        return "\n".join(info_lines)
    
    def _get_rating_description(self, rating):
        """Get descriptive text for armor rating."""
        if rating <= 1:
            return "Minimal"
        elif rating <= 3:
            return "Light"
        elif rating <= 5:
            return "Moderate"
        elif rating <= 7:
            return "Heavy"
        else:
            return "Excellent"
    
    def _get_armor_type_info(self, armor_type):
        """Get information about armor type strengths/weaknesses."""
        type_info = {
            'kevlar': "(Strong vs bullets, weak vs blades)",
            'ceramic': "(Excellent vs bullets, brittle vs blunt force)",
            'steel': "(Good vs cuts/stabs, heavy)",
            'leather': "(Flexible, moderate protection)",
            'synthetic': "(Lightweight, basic protection)"
        }
        return type_info.get(armor_type, "")
    
    def _get_plate_carrier_details(self):
        """Get plate carrier configuration details."""
        info_lines = []
        installed_plates = getattr(self, 'installed_plates', {})
        base_rating = getattr(self, 'armor_rating', 0)
        
        info_lines.append(f"  Base Protection: {base_rating}")
        
        # Show slot configuration
        total_plate_rating = 0
        total_plate_weight = 0
        
        info_lines.append(f"  Current Configuration:")
        for slot_name, plate in installed_plates.items():
            if plate:
                plate_rating = getattr(plate, 'armor_rating', 0)
                plate_weight = getattr(plate, 'weight', 0)
                total_plate_rating += plate_rating
                total_plate_weight += plate_weight
                info_lines.append(f"    {slot_name.title()} Slot: {plate.key} (+{plate_rating} protection, {plate_weight}kg)")
            else:
                info_lines.append(f"    {slot_name.title()} Slot: |y[Empty]|n")
        
        # Totals
        total_protection = base_rating + total_plate_rating
        total_weight = getattr(self, 'weight', 0) + total_plate_weight
        
        info_lines.append(f"")
        info_lines.append(f"  Total Protection: {total_protection} (Base {base_rating} + Plates {total_plate_rating})")
        info_lines.append(f"  Total Weight: {total_weight} kg")
        
        return info_lines
    
    def _get_plate_details(self):
        """Get armor plate specific details."""
        info_lines = []
        plate_type = getattr(self, 'plate_type', 'unknown')
        threat_level = getattr(self, 'threat_level', None)
        
        info_lines.append(f"  Plate Type: {plate_type.title()} plate")
        
        if threat_level:
            info_lines.append(f"  Threat Level: {threat_level}")
        
        info_lines.append(f"  Slot Compatibility: Can be installed in {plate_type} slots of plate carriers.")
        
        return info_lines
    
    def _get_condition_info(self):
        """Get armor condition information."""
        durability = getattr(self, 'armor_durability', None)
        max_durability = getattr(self, 'max_armor_durability', None)
        
        if durability is not None and max_durability is not None and max_durability > 0:
            condition_percent = durability / max_durability
            
            if condition_percent > 0.9:
                return "|gExcellent|n"
            elif condition_percent > 0.7:
                return "|GGood|n"
            elif condition_percent > 0.5:
                return "|yFair|n"
            elif condition_percent > 0.3:
                return "|YPoor|n"
            else:
                return "|rTerrible|n"
        
        return None
    
    def at_delete(self):
        """
        Called when item is deleted/destroyed.
        Handles cleanup for remote detonator explosive tracking.
        """
        # If this item is an explosive scanned by a detonator, remove it from the detonator's list
        if self.db.scanned_by_detonator:
            from evennia.utils.search import search_object
            detonator = search_object(f"#{self.db.scanned_by_detonator}")
            if detonator and len(detonator) > 0:
                detonator_obj = detonator[0]
                if detonator_obj.db.scanned_explosives is not None:
                    try:
                        detonator_obj.db.scanned_explosives.remove(self.id)
                    except ValueError:
                        pass  # Already removed
        
        super().at_delete()


class SprayCanItem(Item):
    """
    Spray paint can for graffiti system.
    Contains finite paint and selectable colors.
    """
    
    def at_object_creation(self):
        """Initialize spray can with paint and color attributes."""
        super().at_object_creation()
        
        # Graffiti-specific attributes
        self.db.aerosol_level = 256  # Default aerosol capacity
        self.db.max_aerosol = 256    # Starting aerosol capacity
        self.db.current_color = "red"  # Default color
        self.db.aerosol_contents = "spraypaint"  # What's inside the can
        
        # Available ANSI colors for cycling
        self.db.available_colors = [
            "red", "green", "yellow", "blue", "magenta", "cyan", "white"
        ]
        
        # Override default description with aerosol level and contents
        if not self.db.desc:
            self.db.desc = f"A can of {self.db.aerosol_contents} with a {self.db.current_color} nozzle. It feels {'heavy' if self.db.aerosol_level > 128 else 'light' if self.db.aerosol_level > 0 else 'empty'} with {self.db.aerosol_contents}."
        
        # Combat properties for spray can as weapon
        self.db.damage = 2  # Slightly better than default item
        self.db.weapon_type = "spraycan"  # Specific weapon type for combat messages
        self.db.damage_type = "burn"  # Chemical burns from spray paint/solvent
        
    def get_display_name(self, looker, **kwargs):
        """
        Display name based on aerosol contents.
        Since cans self-destruct when empty, no need for state indicators.
        """
        aerosol_contents = self.db.aerosol_contents or "spraypaint"
        return f"can of {aerosol_contents}"
    
    def has_paint(self, amount=1):
        """
        Check if spray can has enough aerosol for operation.
        
        Args:
            amount (int): Aerosol amount needed
            
        Returns:
            bool: True if enough aerosol available
        """
        return self.db.aerosol_level >= amount
    
    def use_paint(self, amount):
        """
        Consume aerosol from the can.
        
        Args:
            amount (int): Aerosol amount to consume
            
        Returns:
            int: Actual amount consumed (may be less if running out)
        """
        if amount <= 0:
            return 0
            
        actual_used = min(amount, self.db.aerosol_level)
        self.db.aerosol_level -= actual_used
        
        # Update description based on new aerosol level
        self.db.desc = f"A can of spraypaint with a {self.db.current_color} nozzle. It feels {'heavy' if self.db.aerosol_level > 128 else 'light' if self.db.aerosol_level > 0 else 'empty'} with paint."
        
        # Delete the can if it's empty
        if self.db.aerosol_level <= 0:
            # If wielded, remove from hands first
            if self.location and hasattr(self.location, 'hands'):
                hands = self.location.hands
                for hand_name, held_item in hands.items():
                    if held_item == self:
                        hands[hand_name] = None
                        self.location.hands = hands
                        break
            
            # Delete silently - let calling code handle messaging
            self.delete()
        
        return actual_used
    
    def set_color(self, color):
        """
        Set the spray can's current color.
        
        Args:
            color (str): Color name to set
            
        Returns:
            bool: True if color was valid and set
        """
        if color.lower() in [c.lower() for c in self.db.available_colors]:
            # Find the properly cased version
            for available_color in self.db.available_colors:
                if available_color.lower() == color.lower():
                    self.db.current_color = available_color
                    # Update description with new color
                    self.db.desc = f"A can of spraypaint with a {self.db.current_color} nozzle. It feels {'heavy' if self.db.aerosol_level > 128 else 'light' if self.db.aerosol_level > 0 else 'empty'} with paint."
                    return True
        return False
    
    def get_next_color(self):
        """
        Get the next color in the cycle.
        
        Returns:
            str: Next color name
        """
        try:
            current_index = self.db.available_colors.index(self.db.current_color)
            next_index = (current_index + 1) % len(self.db.available_colors)
            return self.db.available_colors[next_index]
        except ValueError:
            # Current color not in list, return first color
            return self.db.available_colors[0]


class SolventCanItem(Item):
    """
    Solvent can for cleaning graffiti.
    Contains finite solvent for graffiti removal.
    """
    
    def at_object_creation(self):
        """Initialize solvent can with aerosol capacity."""
        super().at_object_creation()
        
        # Aerosol-specific attributes (standardized)
        self.db.aerosol_level = 256  # Default aerosol capacity (matches spray paint)
        self.db.max_aerosol = 256    # Starting aerosol capacity
        self.db.aerosol_contents = "solvent"  # What's inside the can
        
        # Override default description with contents
        if not self.db.desc:
            self.db.desc = f"A can of {self.db.aerosol_contents} for cleaning graffiti. It feels {'heavy' if self.db.aerosol_level > 128 else 'light' if self.db.aerosol_level > 0 else 'empty'} with {self.db.aerosol_contents}."
            
        # Combat properties for solvent can as weapon
        self.db.damage = 2  # Same as spray can
        self.db.weapon_type = "spraycan"  # Same weapon type as spray can
        self.db.damage_type = "burn"  # Chemical burns from solvent
        
    def get_display_name(self, looker, **kwargs):
        """
        Display name based on aerosol contents.
        Since cans self-destruct when empty, no need for state indicators.
        """
        aerosol_contents = self.db.aerosol_contents or "solvent"
        return f"can of {aerosol_contents}"
    
    def has_solvent(self, amount=1):
        """
        Check if solvent can has enough aerosol for operation.
        
        Args:
            amount (int): Aerosol amount needed
            
        Returns:
            bool: True if enough aerosol available
        """
        return self.db.aerosol_level >= amount
    
    def use_solvent(self, amount):
        """
        Consume aerosol from the can.
        
        Args:
            amount (int): Aerosol amount to consume
            
        Returns:
            int: Actual amount consumed (may be less if running out)
        """
        if amount <= 0:
            return 0
            
        actual_used = min(amount, self.db.aerosol_level)
        self.db.aerosol_level -= actual_used
        
        # Update description based on new aerosol level
        self.db.desc = f"A can of solvent for cleaning graffiti. It feels {'heavy' if self.db.aerosol_level > 128 else 'light' if self.db.aerosol_level > 0 else 'empty'} with solvent."
        
        # Delete the can if it's empty
        if self.db.aerosol_level <= 0:
            # If wielded, remove from hands first
            if self.location and hasattr(self.location, 'hands'):
                hands = self.location.hands
                for hand_name, held_item in hands.items():
                    if held_item == self:
                        hands[hand_name] = None
                        self.location.hands = hands
                        break
            
            # Delete silently - let calling code handle messaging
            self.delete()
        
        return actual_used


class RemoteDetonator(Item):
    """
    Remote detonator for explosive devices.
    
    Can scan and remotely trigger up to 20 explosives. Maintains bidirectional
    tracking with explosives - each explosive can only be scanned by one detonator
    at a time, but detonators can manage multiple explosives.
    
    Remote detonation triggers the explosive's normal pin-pull and countdown logic,
    respecting each explosive type's unique behavior (sticky grenade seeking,
    rigged explosive trap mechanics, varied fuse times).
    """
    
    def at_object_creation(self):
        """Initialize remote detonator attributes."""
        super().at_object_creation()
        
        # Scanned explosives tracking (list of dbrefs)
        self.db.scanned_explosives = []
        
        # Maximum capacity
        self.db.max_capacity = 20
        
        # Device type identifier
        self.db.device_type = "remote_detonator"
        
        # Default description if not set
        if not self.db.desc:
            self.db.desc = (
                "A compact military-grade remote detonator with a digital display "
                "showing scanned explosive devices. The device can store up to 20 "
                "explosive signatures and trigger them remotely with the press of a button. "
                "A red safety cover protects the main detonation switch."
            )
    
    def validate_scanned_list(self):
        """
        Clean up invalid explosives from scanned list.
        Removes explosives that no longer exist or are invalid.
        
        Returns:
            int: Number of explosives removed
        """
        if not self.db.scanned_explosives:
            return 0
        
        original_count = len(self.db.scanned_explosives)
        valid_explosives = []
        
        for explosive_dbref in self.db.scanned_explosives:
            from evennia.utils.search import search_object
            explosive = search_object(f"#{explosive_dbref}")
            
            # Keep if explosive exists and is valid
            if explosive and len(explosive) > 0:
                explosive_obj = explosive[0]
                if explosive_obj and hasattr(explosive_obj, 'db'):
                    valid_explosives.append(explosive_dbref)
                    
        self.db.scanned_explosives = valid_explosives
        return original_count - len(valid_explosives)
    
    def add_explosive(self, explosive):
        """
        Add explosive to scanned list with validation.
        Handles capacity limits and bidirectional linking.
        
        Args:
            explosive: Explosive object to add
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Validate capacity
        if len(self.db.scanned_explosives) >= self.db.max_capacity:
            return False, f"Detonator at maximum capacity ({self.db.max_capacity} explosives)."
        
        # Check if already scanned
        if explosive.id in self.db.scanned_explosives:
            return False, f"{explosive.key} is already scanned by this detonator."
        
        # Handle override: remove from previous detonator if any
        if explosive.db.scanned_by_detonator:
            old_detonator_dbref = explosive.db.scanned_by_detonator
            from evennia.utils.search import search_object
            old_detonator = search_object(f"#{old_detonator_dbref}")
            
            if old_detonator and len(old_detonator) > 0:
                old_det = old_detonator[0]
                if old_det.db.scanned_explosives is not None:
                    try:
                        old_det.db.scanned_explosives.remove(explosive.id)
                    except ValueError:
                        pass  # Already removed
        
        # Add to this detonator's list
        self.db.scanned_explosives.append(explosive.id)
        
        # Set bidirectional reference
        explosive.db.scanned_by_detonator = self.id
        
        return True, f"{explosive.key} scanned successfully."
    
    def remove_explosive(self, explosive_dbref):
        """
        Remove explosive from scanned list.
        Breaks bidirectional reference.
        
        Args:
            explosive_dbref: Database ID of explosive to remove
            
        Returns:
            bool: True if removed, False if not in list
        """
        if explosive_dbref not in self.db.scanned_explosives:
            return False
        
        # Remove from list
        self.db.scanned_explosives.remove(explosive_dbref)
        
        # Clear bidirectional reference if explosive still exists
        from evennia.utils.search import search_object
        explosive = search_object(f"#{explosive_dbref}")
        if explosive and len(explosive) > 0:
            explosive_obj = explosive[0]
            if explosive_obj.db.scanned_by_detonator is not None:
                explosive_obj.db.scanned_by_detonator = None
        
        return True
    
    def get_scanned_count(self):
        """
        Get current count of scanned explosives.
        Auto-validates list before counting.
        
        Returns:
            int: Number of valid scanned explosives
        """
        self.validate_scanned_list()
        return len(self.db.scanned_explosives)
    
    def at_delete(self):
        """
        Called when detonator is destroyed.
        Clears scanned_by_detonator reference on all linked explosives.
        """
        if self.db.scanned_explosives:
            from evennia.utils.search import search_object
            
            for explosive_dbref in self.db.scanned_explosives:
                explosive = search_object(f"#{explosive_dbref}")
                if explosive and len(explosive) > 0:
                    explosive_obj = explosive[0]
                    if explosive_obj.db.scanned_by_detonator is not None:
                        explosive_obj.db.scanned_by_detonator = None
        
        super().at_delete()
