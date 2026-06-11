from evennia import DefaultObject, AttributeProperty
from world.combat.constants import DEFAULT_CLOTHING_LAYER
from .identity_bearer import IdentityBearerMixin

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

    # ===================================================================
    # DISGUISE SYSTEM ATTRIBUTES
    # ===================================================================
    #
    # Two-flag taxonomy for the Phase 3 disguise system. See
    # ``specs/IDENTITY_RECOGNITION_SPEC.md`` §Disguise Items for the
    # design rationale.
    #
    # ``is_disguise_item`` marks an item as belonging to the disguise
    # taxonomy at all (carries a future Phase 5 perception-roll bonus).
    # ``disguise_essential`` is the stronger flag: an essential item
    # contributes to the wearer's identity signature, so equipping or
    # removing it shifts their Apparent UID and produces a distinct
    # recognition entry.  Non-essential disguise items contribute only
    # visually through the existing distinguishing-feature derivation.
    #
    # ``disguise_type_id`` is the stable per-item-type identifier hashed
    # into the signature.  Two balaclavas with the same
    # ``disguise_type_id`` produce the same signature contribution, so
    # the same physical disguise produces the same Apparent UID across
    # different item instances.  Authors set this explicitly per
    # essential item (e.g. ``"balaclava"``, ``"mask_full"``, ``"wig"``);
    # leaving it empty on an essential item suppresses its signature
    # contribution and emits a startup warning via the wearer's
    # signature query path.

    # Marks an item as part of the disguise taxonomy (perception-roll
    # bonus in Phase 5; no behavioural effect today).
    is_disguise_item = AttributeProperty(False, autocreate=True)

    # Marks an essential disguise item: when worn, contributes its
    # ``disguise_type_id`` to the wearer's identity signature.
    disguise_essential = AttributeProperty(False, autocreate=True)

    # Stable per-item-type identifier fed into the identity signature
    # for essential disguise items.  Empty string means "no
    # contribution"; treated as a soft warning when paired with
    # ``disguise_essential = True``.
    disguise_type_id = AttributeProperty("", autocreate=True)

    # Per-item pierce-penalty weight.  Counts as this many disguise
    # vectors when worn (and ``disguise_essential = True``) in
    # :func:`world.identity._count_disguise_vectors`.  Default ``1``
    # preserves the original flat-1-per-essential-item contract; bump
    # higher for heavy concealment (a full prosthetic mask, an
    # all-covering hooded robe) and drop to ``0`` for cosmetic
    # essentials that should still pin the identity signature but
    # shouldn't make piercing harder.  No effect on non-essential
    # items.
    disguise_weight = AttributeProperty(1, autocreate=True)

    # ``disguise_adjective`` is the visible "red flag" — when an item
    # flagged ``is_disguise_item = True`` is worn, this adjective is
    # injected into the wearer's sdesc between the physical descriptor
    # and the keyword (e.g. ``"a tall lean masked droog"``).  Empty
    # string means no contribution.  Authors set per item type
    # (``"masked"``, ``"hooded"``, ``"helmeted"``, etc.).  Adjectives
    # not in :data:`world.identity._DISGUISE_ADJECTIVE_PRIORITY` are
    # admitted at the lowest priority rank, so new disguise types ship
    # via item attribute alone without a code edit.  Honoured only when
    # ``is_disguise_item`` is also ``True`` (red-flag style standard);
    # otherwise skipped with a soft warning.
    disguise_adjective = AttributeProperty("", autocreate=True)

    # Brief noun phrase used by the distinguishing-feature clothing
    # selector (e.g. ``"black balaclava"`` → ``"in a black balaclava"``).
    # Empty string falls back to the item's ``key``.  See
    # ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Distinguishing Feature
    # Derivation".
    worn_sdesc_short = AttributeProperty("", autocreate=True)

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


class Organ(Item):
    """A harvested organ extracted from a corpse via ``harvest``.

    Surfaces the forensic-chain provenance (source corpse signature)
    so downstream gameplay — implantation, black-market trade,
    investigation — can reason about origin without re-querying the
    source corpse (which may have decayed away by the time the organ
    changes hands).

    Attributes (``self.db``):
        organ_name: Canonical organ identifier from
            :data:`world.medical.constants.ORGANS`
            (e.g. ``"heart"``, ``"liver"``).
        condition: Freshness descriptor at extraction time, derived
            from the source corpse's decay stage via
            :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`.
        source_signature: Copy of the source corpse's
            ``signature_at_death`` tuple (forensic chain).
        source_apparent_uid: Copy of the source corpse's
            ``apparent_uid_at_death`` (forensic chain).
        source_corpse_dbref: ``#NNN`` ref of the source corpse, for
            audit / debugging — not guaranteed resolvable (the corpse
            may have decayed and been deleted).

    The display name renders as ``"<species> <organ>"`` for fresh /
    early corpses (e.g. ``"human heart"``), drops to ``"rotting
    <organ>"`` at moderate / advanced decay, and to ``"desiccated
    <organ>"`` at the skeletal tier — mirroring the
    :class:`Appendage` decay-tier contract.  Condition (pristine /
    damaged / putrid) is conveyed via ``self.db.desc`` and surfaces
    at ``look`` time; callers that need the raw organ identifier
    should read ``db.organ_name``.
    """

    def at_object_creation(self):
        super().at_object_creation()
        # Defaults — the harvest command overwrites these immediately
        # after spawn via ``configure_from_harvest``.
        self.db.organ_name = ""
        self.db.condition = "pristine"
        self.db.source_signature = None
        self.db.source_apparent_uid = None
        self.db.source_corpse_dbref = None
        # PR-G: species provenance, used to render condition-aware
        # default descriptions and (in future) species-specific organ
        # variants.  Defaults to ``"human"`` so direct-spawned organs
        # without ``configure_from_harvest`` still look sensible.
        self.db.source_species = "human"

    def configure_from_harvest(self, *, organ_name, condition, corpse):
        """Populate forensic-chain fields immediately after spawn.

        Args:
            organ_name (str): Canonical organ identifier.
            condition (str): Freshness descriptor.
            corpse: The source :class:`typeclasses.corpse.Corpse`.

        Sets the display key via
        :func:`world.anatomy.species.get_species_organ_name`, which
        renders decay-modulated species-aware names (``"human heart"``
        → ``"rotting heart"`` → ``"desiccated heart"``) matching the
        appendage naming contract.  Issue #212.

        PR #204: also seeds ``self.db.desc`` from the condition-keyed
        default description so the Evennia-standard ``return_appearance``
        renderer slots it into the look output naturally — no custom
        ``return_appearance`` override required.  Organs without a
        registered description (or with the ``refuse`` condition, which
        the harvest command gate refuses upstream anyway) leave
        ``db.desc`` untouched so the engine default applies.
        """
        from world.anatomy import (
            get_organ_default_description,
            get_species_organ_name,
            prepend_condition_to_desc,
        )

        self.db.organ_name = organ_name
        self.db.condition = condition
        self.db.source_signature = corpse.db.signature_at_death
        self.db.source_apparent_uid = corpse.db.apparent_uid_at_death
        self.db.source_corpse_dbref = corpse.dbref
        # PR-G: species inheritance for condition-aware prose.
        species = corpse.db.species or "human"
        self.db.source_species = species
        # Issue #212: read decay stage off the corpse for species-aware
        # key composition.  Mirrors the Appendage pattern below.  Fake
        # corpses in unit tests may lack ``get_decay_stage`` — fall back
        # to ``fresh`` (the species-revealing tier) for those paths.
        if hasattr(corpse, "get_decay_stage"):
            decay_stage = corpse.get_decay_stage()
        else:
            decay_stage = "fresh"
        self.key = get_species_organ_name(species, organ_name, decay_stage)
        # PR #204: populate db.desc the Evennia-standard way so the
        # engine renderer handles it (rather than overriding
        # return_appearance to prepend prose).
        #
        # Issue #221: prepend a colour-coded condition tagline so the
        # look output explicitly surfaces the freshness state the key
        # intentionally dropped in issue #212.  ``prepend_condition_to_desc``
        # composes a final desc that blends the tagline above the prose;
        # when neither tagline nor prose is registered (e.g. ``refuse``
        # condition with no registered prose) the helper returns ``""``
        # and we leave the engine default in place.
        prose = get_organ_default_description(organ_name, condition)
        composed = prepend_condition_to_desc(condition, prose)
        if composed:
            self.db.desc = composed

        # Carry organ-bound conditions from the source corpse onto
        # the harvested item (#307 three-tier model).  The corpse's
        # medical snapshot stores each organ's ``conditions`` list
        # in serialized-dict form via ``Organ.to_dict``; we copy it
        # verbatim onto the harvested item so a future install
        # pipeline (Phase 3.2 cybernetics in the spec) can re-attach
        # the conditions to the recipient's organ slot.  Body-bound
        # and location-bound conditions stay on the source corpse —
        # only organ-bound state travels with the harvest.
        try:
            snapshot = corpse.get_medical_snapshot() or {}
            organs = snapshot.get("organs") or {}
            organ_data = organs.get(organ_name) or {}
            self.db.organ_conditions = list(organ_data.get("conditions") or [])
        except (AttributeError, TypeError):
            self.db.organ_conditions = []


class Appendage(Item):
    """A severed limb (or head) detached from a corpse via ``sever``.

    Sibling typeclass to :class:`Organ`; carries the same
    forensic-chain provenance fields so investigators (and future
    black-market gameplay) can trace a found appendage back to its
    source corpse signature without re-querying the corpse.

    Attributes (``self.db``):
        location_name: Canonical body-location identifier
            (e.g. ``"left_arm"``, ``"head"``) — matches the
            ``container`` keys used in
            :data:`world.medical.constants.ORGANS`.
        condition: Freshness descriptor at severance, derived from
            the source corpse's decay stage via
            :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`.
        source_signature: Copy of source corpse's
            ``signature_at_death``.
        source_apparent_uid: Copy of source corpse's
            ``apparent_uid_at_death``.
        source_corpse_dbref: Audit pointer to the source corpse;
            not guaranteed resolvable after decay.

    The display name renders as ``"<condition> <location>"``
    (underscores → spaces), e.g. ``"pristine left arm"``.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.location_name = ""
        self.db.condition = "pristine"
        self.db.source_signature = None
        self.db.source_apparent_uid = None
        self.db.source_corpse_dbref = None
        # PR-G: species provenance for decay-aware naming.  Defaults to
        # ``"human"`` so legacy code paths and tests that spawn a bare
        # Appendage without going through ``configure_from_sever`` still
        # render a sensible key.
        self.db.source_species = "human"
        # PR #198 wound + longdesc carry-forward: populated by
        # ``configure_from_sever`` via ``apply_wound_and_longdesc_overlay``.
        # Default to empty containers so renderer code paths can iterate
        # without ``None`` checks.
        self.db.wounds_at_death = []
        self.db.longdesc_data = {}
        # Trimmed organ snapshot — populated by ``configure_from_sever`` /
        # ``configure_from_living_sever`` via ``apply_organ_snapshot_overlay``.
        # Shape matches the corpse / head contract so ``get_organ_snapshot``
        # can route harvest / autopsy uniformly across every severed part.
        self.db.medical_state_at_death = None
        # Subset of the source's ``removed_organs`` whose organs ended up
        # in this appendage's chain — feeds repeat-harvest gating + autopsy.
        self.db.removed_organs = []
        # #307 PR-H3: worn-items carry-forward.  Severed appendages
        # remember which items were worn on which body location at
        # the moment of severance.  Structure mirrors
        # ``Character.worn_items``:
        #
        #     {"left_hand": [glove_obj], "left_arm": [bracer_obj]}
        #
        # Populated by ``detach_items_to_appendage`` for any worn
        # item whose coverage was fully contained in the severed
        # cluster.  Read by ``return_appearance`` (forensic prose)
        # and the third-party ``undress`` verb.
        self.db.worn_items = {}

    def configure_from_sever(self, *, location_name, condition, corpse):
        """Populate forensic-chain fields immediately after spawn.

        Issue #339: corpse-side limb severance now also carries the
        downstream limb chain — severing a thigh from a corpse takes
        the shin and foot, just like the living-character path. The
        Appendage is named with the compound anatomical key
        (``"human left leg"`` rather than ``"human left thigh"``).
        The head path is untouched — it has its own downstream cluster
        (:data:`world.combat.constants.SEVERED_HEAD_LOCATIONS`) handled
        by :class:`SeveredHead.configure_from_sever`.

        Args:
            location_name (str): Canonical body-location identifier
                (the cut point).
            condition (str): Freshness descriptor.
            corpse: The source :class:`typeclasses.corpse.Corpse`.
        """
        from world.anatomy import (
            get_severed_part_description,
            get_species_limb_downstream_chain,
            get_species_part_name,
            get_species_severed_chain_name,
            prepend_condition_to_desc,
        )

        # Issue #356 Phase 2: species-aware downstream chain.
        chain_map = get_species_limb_downstream_chain(
            getattr(getattr(corpse, "db", None), "species", None)
        )
        chain = chain_map.get(location_name, (location_name,))
        self.db.location_name = location_name
        self.db.chain = chain
        self.db.condition = condition
        self.db.source_signature = corpse.db.signature_at_death
        self.db.source_apparent_uid = corpse.db.apparent_uid_at_death
        self.db.source_corpse_dbref = corpse.dbref
        # Issue #234: snapshot the preserved gender + name so carried
        # longdesc prose can have its {their}/{they}/{name} tokens
        # resolved at render time (the living-character renderer is no
        # longer in play).  Parts spawned before this field existed fall
        # back to plural pronouns in return_appearance.
        self.db.original_gender = corpse.db.original_gender
        self.db.original_character_name = corpse.db.original_character_name
        # PR-G: inherit species from corpse so the appendage's
        # decay-modulated key matches its origin anatomy.
        species = corpse.db.species or "human"
        self.db.source_species = species
        # Read the corpse's current decay stage for naming.  The
        # ``condition`` parameter is the organ-condition mapping
        # (pristine / damaged / putrid / refuse) — useful for harvest
        # bookkeeping but coarser than the underlying decay tier.
        if hasattr(corpse, "get_decay_stage"):
            decay_stage = corpse.get_decay_stage()
        else:
            decay_stage = "fresh"
        # Compound name when the chain has downstream parts (#339).
        if len(chain) > 1:
            self.key = get_species_severed_chain_name(
                species, location_name, decay_stage
            )
        else:
            self.key = get_species_part_name(species, location_name, decay_stage)
        # PR #204: populate db.desc the Evennia-standard way so the
        # engine renderer handles it.  ``Appendage.return_appearance``
        # still composes wound + longdesc carry-forward dynamically on
        # top of the engine-rendered base (which now includes our
        # seeded desc), so both surfaces coexist cleanly.
        #
        # Issue #221: prepend a colour-coded condition tagline so the
        # look output explicitly surfaces the freshness state.  The
        # tagline travels in ``db.desc`` so the dynamic wound /
        # longdesc composition below still rides on top cleanly.
        prose = get_severed_part_description(species, location_name, condition)
        composed = prepend_condition_to_desc(condition, prose)
        if composed:
            self.db.desc = composed
        # PR #198: pull this location's wound + longdesc prose off the
        # corpse onto ourselves.  The corpse-side mutation
        # (delete-from-source + synthesized stump wound) is handled by
        # :func:`commands.forensics._apply_sever_to_corpse` so this
        # helper stays a pure copy and is independently unit-testable.
        # Chain support: carry data for every chain location.
        apply_wound_and_longdesc_overlay(self, corpse, chain)

        # Trimmed organ snapshot — generalization of the head-only
        # pattern in ``apply_severed_head_overlay`` to every severed
        # appendage.  Lets harvest / autopsy find organs on a severed
        # arm or forepaw the same way they find them on a severed head.
        corpse_snapshot = None
        if hasattr(corpse, "get_medical_snapshot"):
            try:
                corpse_snapshot = corpse.get_medical_snapshot()
            except (AttributeError, TypeError):
                corpse_snapshot = None
        apply_organ_snapshot_overlay(
            self,
            source_snapshot=corpse_snapshot,
            containers=chain,
            source_removed_organs=getattr(corpse.db, "removed_organs", None),
        )

    def configure_from_living_sever(self, *, character, location_name,
                                    injury_type="cut", chain=None):
        """Populate provenance + prose from a *living* character on sever.

        Living-character counterpart to :meth:`configure_from_sever`.
        Where the corpse path inherits a decay stage and death-snapshot
        identity, a limb cut from the living is always **pristine /
        fresh** (no decay clock yet) and reads identity straight off the
        live character.  The forensic-chain fields mirror what the corpse
        captures at death so a found living-severed limb is traceable the
        same way (:func:`world.identity.get_identity_signature` /
        :func:`world.identity.get_apparent_uid`).

        Issue #339: ``chain`` carries the full downstream limb chain so
        the Appendage's name and carried prose reflect the multi-
        location item (severed thigh + shin + foot reads as
        ``"human left leg"``).

        Args:
            character: The living character losing the limb.
            location_name (str): Canonical primary severed-limb location
                (the cut point).
            injury_type (str): Edged injury that caused the cut.
            chain (tuple | None): Full chain of locations travelling
                with the cut. ``None`` → single-location legacy path
                (chain becomes ``(location_name,)``).
        """
        from world.anatomy import (
            get_severed_part_description,
            get_species_part_name,
            get_species_severed_chain_name,
            prepend_condition_to_desc,
        )

        if chain is None:
            chain = (location_name,)
        else:
            chain = tuple(chain)

        condition = "pristine"
        self.db.location_name = location_name
        self.db.chain = chain  # Preserve for downstream consumers.
        self.db.condition = condition
        # No source corpse exists for a living sever.
        self.db.source_corpse_dbref = None

        # Forensic-chain identity read live off the character (mirrors the
        # corpse death-snapshot capture in death_progression).
        try:
            from world.identity import get_apparent_uid, get_identity_signature
            self.db.source_signature = get_identity_signature(character)
            self.db.source_apparent_uid = get_apparent_uid(character)
        except (AttributeError, TypeError, ValueError):
            self.db.source_signature = None
            self.db.source_apparent_uid = None

        # Snapshot gender + name so carried longdesc pronoun / name tokens
        # resolve at render time (parity with configure_from_sever #234).
        self.db.original_gender = character.gender
        self.db.original_character_name = character.key

        species = character.db.species or "human"
        self.db.source_species = species
        # Living sever → always the freshest naming tier. When the chain
        # has more than just the primary container, use the compound
        # anatomical name (#339).
        if len(chain) > 1:
            self.key = get_species_severed_chain_name(
                species, location_name, "fresh"
            )
        else:
            self.key = get_species_part_name(species, location_name, "fresh")

        prose = get_severed_part_description(species, location_name, condition)
        composed = prepend_condition_to_desc(condition, prose)
        if composed:
            self.db.desc = composed

        # Carry this location's longdesc prose + visible wounds onto the
        # part.  Read BEFORE the caller mutates the body so the source
        # prose / wounds are still intact. With chain support, the
        # overlay carries data for every location in the chain.
        from world.medical.wounds import get_character_wounds

        longdescs = dict(character.longdesc or {})
        try:
            wounds = get_character_wounds(character) or []
        except (AttributeError, TypeError, ValueError):
            wounds = []
        apply_living_sever_overlay(
            self,
            longdescs=longdescs,
            wounds=wounds,
            locations=chain,
        )

        # Trimmed organ snapshot — read live medical state *before* the
        # caller (apply_sever_to_character) mutates the body.  Mirrors
        # the head living-sever path (apply_severed_head_overlay_from_living)
        # so harvest / autopsy find organs on every severed appendage.
        try:
            live_snapshot = character.medical_state.to_dict() or {}
        except (AttributeError, TypeError, ValueError):
            live_snapshot = {}
        live_removed = getattr(
            getattr(character, "db", None), "removed_organs", None,
        )
        apply_organ_snapshot_overlay(
            self,
            source_snapshot=live_snapshot,
            containers=chain,
            source_removed_organs=live_removed,
        )

    def get_medical_snapshot(self):
        """Return the trimmed organ snapshot carried at severance.

        Same contract as :meth:`typeclasses.corpse.Corpse.get_medical_snapshot`
        and :meth:`SeveredHead.get_medical_snapshot`.  Consumed by
        :func:`world.medical.procedures.get_organ_snapshot` so harvest /
        autopsy route uniformly against any severed part regardless of
        whether it's a head, an arm, or a forepaw — the snapshot is
        populated at severance by
        :func:`apply_organ_snapshot_overlay`.
        """
        return self.db.medical_state_at_death

    def return_appearance(self, looker, **kwargs):
        """Compose appearance from base desc + carried longdesc + wounds.

        PR #198: severed limbs and heads carry forward the source
        corpse's per-location longdesc prose and wound records.

        Issue #236: the carried prose renders as a single flowing
        paragraph appended to the base ``return_appearance`` output (the
        name stays on its own header line via ``base``).  Composition is
        **per location**, in anatomical order: each location's longdesc
        is immediately followed by that location's wound description(s),
        so a wound stays connected to the body part it belongs to —
        mirroring :meth:`typeclasses.corpse.Corpse` rendering.

        Longdesc text is shown verbatim (decay-modulated only by the
        condition prefix already baked into the key).  Pronoun / name
        brace tokens are resolved against the snapshotted character data
        (issue #234); a missing snapshot degrades to plural pronouns.
        Wound descriptions render at ``stage="old"`` to match the
        corpse's preserved-wound contract.
        """
        base = super().return_appearance(looker, **kwargs)

        from world.anatomy import substitute_pronoun_tokens

        longdescs = self.db.longdesc_data or {}
        wounds = self.db.wounds_at_death or []
        gender = self.db.original_gender
        name = self.db.original_character_name or "the corpse"
        # Issue #350 / PR-A: thread species through so the body-noun
        # flex pass consults the species pair table.  ``source_species``
        # was captured at sever time; falls back to "human" when absent.
        species = self.db.source_species or "human"

        # Issue #350 follow-up: suppress the authored longdesc at any
        # display location whose organ was destroyed at sever time.
        # The carried wound list (``wounds_at_death``) is rewritten to
        # ``stage="old"`` at sever overlay so a wound-list check would
        # miss destroyed-stage entries; we read the preserved organ
        # snapshot directly instead.  Without this, a head decapitated
        # after an eye was pulped renders "His left eye is brown"
        # alongside the carried eye wound (issue #350 PR-B parity).
        try:
            from world.medical.wounds import (
                get_destroyed_locations_from_snapshot,
            )
            destroyed_locs = get_destroyed_locations_from_snapshot(
                self.db.medical_state_at_death
            )
        except ImportError:
            destroyed_locs = set()

        try:
            # Issue #356 Phase 3: species-aware display order.
            # ``source_species`` was captured at sever time.
            from world.anatomy import get_species_anatomical_display_order
            ANATOMICAL_DISPLAY_ORDER = get_species_anatomical_display_order(species)
        except ImportError:
            ANATOMICAL_DISPLAY_ORDER = list(longdescs.keys())

        try:
            from world.medical.wounds import get_wound_description
        except ImportError:
            get_wound_description = None

        def _render_wound(wound):
            """Render one preserved wound; None on failure / no renderer."""
            if get_wound_description is None:
                return None
            try:
                return get_wound_description(
                    injury_type=wound.get("injury_type", "generic"),
                    location=wound.get("location")
                    or self.db.location_name
                    or "",
                    severity=wound.get("severity", "Moderate"),
                    stage="old",
                    organ=wound.get("organ"),
                    character=self,
                )
            except (KeyError, ValueError, AttributeError):
                return None

        def _wound_location(wound):
            return wound.get("location") or self.db.location_name or ""

        # Compose one chunk per location: longdesc first, then any
        # wounds at that location, so they stay connected.
        chunks = []
        seen_locs = set()
        handled_wounds = set()

        def _build_location_chunk(loc):
            pieces = []
            text = longdescs.get(loc)
            if text and loc not in destroyed_locs:
                # Suppression rule mirrors the living-character /
                # corpse paths (PR-B): a destroyed organ surfaces its
                # destruction through the wound layer, so the authored
                # body-part prose is dropped to avoid contradicting it.
                pieces.append(
                    substitute_pronoun_tokens(
                        text, gender=gender, name=name, species=species,
                    )
                )
            for idx, wound in enumerate(wounds):
                if idx in handled_wounds or _wound_location(wound) != loc:
                    continue
                rendered = _render_wound(wound)
                handled_wounds.add(idx)
                if rendered:
                    pieces.append(rendered)
            return " ".join(pieces)

        for loc in ANATOMICAL_DISPLAY_ORDER:
            if loc in seen_locs:
                continue
            seen_locs.add(loc)
            chunk = _build_location_chunk(loc)
            if chunk:
                chunks.append(chunk)

        # Longdesc locations outside the canonical order (defensive —
        # preserves prose + connected wounds for nonstandard anatomy).
        for loc in longdescs:
            if loc in seen_locs:
                continue
            seen_locs.add(loc)
            chunk = _build_location_chunk(loc)
            if chunk:
                chunks.append(chunk)

        # Any wounds whose location had no longdesc chunk above — render
        # them so forensic detail is never silently dropped.
        for idx, wound in enumerate(wounds):
            if idx in handled_wounds:
                continue
            handled_wounds.add(idx)
            rendered = _render_wound(wound)
            if rendered:
                chunks.append(rendered)

        body = " ".join(chunks)

        # PR-H3 (#307): worn-items carry-forward.  Severed appendages
        # remember the clothing that travelled with them and surface
        # it in forensic prose ("the severed hand still wears a
        # bloodstained glove").  Skip when nothing's there.
        worn_line = self._build_worn_items_line(looker)
        if worn_line:
            body = f"{body} {worn_line}" if body else worn_line

        if not body:
            return base
        return f"{base} {body}" if base else body

    def _build_worn_items_line(self, looker):
        """Build the "still wearing ..." sentence for forensic prose.

        Returns the empty string when no items are worn on the
        appendage — keeps the calling renderer's whitespace handling
        clean.
        """
        worn = self.db.worn_items or {}
        # Collect each unique item once, preserving first-seen order
        # (location iteration order, then within-list order).  A
        # multi-location worn item (e.g. coat) wouldn't reach here in
        # PR-H3 since the sever pipeline only registers items whose
        # coverage was fully contained in the severed cluster, but
        # the dedup is defensive for future expansion.
        seen = []
        for loc_items in worn.values():
            for item in (loc_items or []):
                if item not in seen:
                    seen.append(item)
        if not seen:
            return ""
        if len(seen) == 1:
            name = seen[0].get_display_name(looker)
            return f"It still wears {name}."
        names = [item.get_display_name(looker) for item in seen]
        joined = ", ".join(names[:-1]) + f", and {names[-1]}"
        return f"It still wears {joined}."


def apply_wound_and_longdesc_overlay(appendage, corpse, locations):
    """Copy wounds + longdesc prose for ``locations`` from corpse → appendage.

    Extracted as a module-level helper (matching the
    :func:`apply_severed_head_overlay` pattern) so unit tests can
    exercise the overlay against plain-Python stubs without
    instantiating an Evennia typeclass.

    The overlay is a **pure copy** — the caller (:func:`commands.forensics._apply_sever_to_corpse`)
    is responsible for the symmetric corpse-side delete + stump-wound
    synthesis.  Wound dict entries are shallow-copied (one level) to
    prevent the appendage and corpse from sharing list/dict identity
    on subsequent mutations.

    Args:
        appendage: Object whose ``db`` should receive ``wounds_at_death``
            and ``longdesc_data`` for the given locations.
        corpse: Source :class:`typeclasses.corpse.Corpse`-like object
            whose ``db.wounds_at_death`` and ``db.longdesc_data`` are
            read.
        locations: Iterable of body-location names.  Wounds whose
            ``location`` field is in this set are copied; longdesc
            entries whose key is in this set are copied.
    """
    locs = frozenset(locations)

    src_wounds = corpse.db.wounds_at_death or []
    appendage.db.wounds_at_death = [
        dict(wound) for wound in src_wounds
        if wound.get("location") in locs
    ]

    src_longdescs = corpse.db.longdesc_data or {}
    appendage.db.longdesc_data = {
        loc: text for loc, text in src_longdescs.items() if loc in locs
    }


def apply_organ_snapshot_overlay(appendage, *, source_snapshot,
                                  containers, source_removed_organs=None):
    """Copy a trimmed organ snapshot from a corpse / character → appendage.

    Generalization of the head-only pattern in
    :func:`apply_severed_head_overlay`: any severed appendage carries
    forward the subset of organs whose ``container`` falls inside the
    severed chain.  Same dict shape as the corpse / head snapshot so
    :func:`world.medical.procedures.get_organ_snapshot` can route
    harvest / autopsy uniformly against any severed part.

    Body-wide fields (conditions, blood, pain, consciousness) are
    blanked because they describe the whole body and would lie if
    reported off a disembodied limb — matching the head contract.
    Organ entries are shallow-copied to prevent aliasing with the
    source snapshot on subsequent mutations.

    Args:
        appendage: Object whose ``db`` receives ``medical_state_at_death``
            and (optionally) ``removed_organs``.
        source_snapshot: A medical-state snapshot dict (the shape
            returned by ``MedicalState.to_dict()`` or
            ``Corpse.get_medical_snapshot()``).  ``None`` → empty
            snapshot written.
        containers: Iterable of canonical container names — organs
            whose ``container`` is in this set are carried forward.
            For limbs this is the severed chain; for the head pipeline
            it's the head-cluster container set.
        source_removed_organs: Optional iterable of organ names removed
            from the source prior to severance.  When provided, the
            appendage's ``removed_organs`` is filtered to organs that
            actually carried forward into this part — gates repeat
            harvest + feeds autopsy.
    """
    locs = frozenset(containers)
    organs = (source_snapshot or {}).get("organs") or {}
    trimmed = {}
    for name, data in organs.items():
        # Duck-type: _SaverDict isn't a dict subclass but supports .get.
        if not hasattr(data, "get"):
            continue
        if (data.get("container") or "") in locs:
            trimmed[name] = dict(data)
    appendage.db.medical_state_at_death = {
        "organs": trimmed,
        "conditions": [],
        "blood_level": None,
        "pain_level": None,
        "consciousness": None,
    }
    if source_removed_organs is not None:
        appendage.db.removed_organs = [
            name for name in (source_removed_organs or ())
            if name in trimmed
        ]


def apply_sever_to_corpse(corpse, location_arg, *, head_locations=None):
    """Mutate ``corpse`` to reflect a successful sever at ``location_arg``.

    Symmetric counterpart to :func:`apply_wound_and_longdesc_overlay`:
    where the overlay copies prose onto the severed item, this helper
    removes that prose from the source corpse and synthesizes a stump
    wound at the canonical severed location.

    For ``location_arg == "head"`` the full
    :data:`world.combat.constants.SEVERED_HEAD_LOCATIONS` cluster is
    cleared from the corpse's ``longdesc_data`` and ``wounds_at_death``
    (face, neck, eyes, ears all visually leave with the head).  For
    any other limb, only that single location is cleared.  In every
    case exactly one synthesized ``severed``-type wound is appended at
    ``location_arg`` so the corpse renders, e.g., *"the left shoulder
    ends in a ragged stump"*.

    Args:
        corpse: The source corpse to mutate in place.
        location_arg: Canonical severed-location identifier
            (member of :data:`world.combat.constants.SEVERABLE_CONTAINERS`).
        head_locations: Override for the head-cluster set; defaults to
            :data:`world.combat.constants.SEVERED_HEAD_LOCATIONS`.
            Exposed for test injection.
    """
    if head_locations is None:
        # Issue #356 Phase 2: species-aware head cluster (defaults to
        # human when no species attribute is present on the corpse).
        from world.anatomy import get_species_severed_head_locations
        head_locations = get_species_severed_head_locations(
            getattr(getattr(corpse, "db", None), "species", None)
        )

    # Idempotency guard: if a synthetic stump wound at ``location_arg``
    # already exists in ``wounds_at_death``, a previous invocation
    # already ran this mutation.  Re-running would duplicate the stump
    # wound and re-clear longdescs that aren't there.  Bail cleanly.
    src_wounds_for_check = corpse.db.wounds_at_death or ()
    for existing in src_wounds_for_check:
        if (existing.get("injury_type") == "severed"
                and existing.get("location") == location_arg
                and existing.get("organ") is None):
            return

    if location_arg == "head":
        locs = frozenset(head_locations)
    else:
        # Issue #339: limb severance on a corpse should also clear the
        # downstream chain (severing a thigh on a corpse takes the
        # shin and foot). Mirrors the living-character chain semantics.
        # Issue #356 Phase 2: chain map is species-aware.
        from world.anatomy import get_species_limb_downstream_chain
        chain_map = get_species_limb_downstream_chain(
            getattr(getattr(corpse, "db", None), "species", None)
        )
        chain = chain_map.get(location_arg, (location_arg,))
        locs = frozenset(chain)

    # Drop longdesc prose for the cleared locations.
    src_longdescs = corpse.db.longdesc_data or {}
    if src_longdescs:
        corpse.db.longdesc_data = {
            loc: text for loc, text in src_longdescs.items()
            if loc not in locs
        }

    # Wounds at the cleared locations move to the severed item; drop
    # them from the corpse to avoid double-counting in autopsy.
    src_wounds = corpse.db.wounds_at_death or []
    remaining = [
        wound for wound in src_wounds
        if wound.get("location") not in locs
    ]
    # Synthesized stump wound — single entry at the canonical sever
    # location, regardless of head-cluster size.  Stage at this
    # moment is captured as a sever-time snapshot (useful for any
    # forensics consumer that wants "what did this look like when
    # severed"), but the corpse renderer ignores this stored stage
    # for severance wounds and recomputes JIT via
    # :func:`world.medical.severance.stump_stage_for_corpse` — so a
    # fresh-then-decayed corpse renders the correct tier on each
    # look without write-back.  Sutured stumps override at render
    # time via ``sutured_stumps`` (see
    # ``Corpse.get_wound_descriptions_for_location``).
    from world.medical.severance import stump_stage_for_corpse
    remaining.append({
        "injury_type": "severed",
        "location": location_arg,
        "severity": "Critical",
        "stage": stump_stage_for_corpse(corpse),
        "organ": None,
        "organ_damage": {
            "current_hp": 0,
            "max_hp": 0,
            "container": location_arg,
        },
    })
    corpse.db.wounds_at_death = remaining

    # Mark the corpse as headless on head sever.  Identity is
    # *duplicated* (the corpse keeps its
    # ``signature_at_death`` / ``apparent_uid_at_death`` / ``sleeve_uid``
    # so autopsy and forensic-chain lookups continue to work) but
    # :meth:`typeclasses.corpse.Corpse.get_display_name` short-circuits
    # to the decay-stage fallback when this flag is set, suppressing
    # unaided look-time recognition.  See issue #208 and
    # ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Sever-Head Identity
    # Surface" for the rationale.
    if location_arg == "head":
        corpse.db.head_severed = True


def spawn_severed_part_from_corpse(corpse, location_arg):
    """Spawn + configure a severed appendage from a corpse.

    Generalises the head-only ``spawn_severed_head_for_corpse`` to any
    severable location.  Pattern mirrors :class:`commands.forensics.CmdSever`
    inline:

    1. Idempotency check — if ``location_arg`` is already in
       ``corpse.db.severed_locations``, return ``None``.
    2. Choose typeclass: ``SeveredHead`` for ``"head"``,
       ``Appendage`` for anything else.
    3. ``create_object`` with a species-aware decay-flavoured key.
    4. ``configure_from_sever`` to copy provenance / decay / wounds
       / longdescs / snapshot off the corpse.
    5. Record the sever in ``corpse.db.severed_locations``.
    6. ``apply_sever_to_corpse`` to mutate the corpse (drop cluster
       longdescs / wounds, synthesise the stump wound, flip
       ``head_severed`` on head).

    Used by:

    * ``commands.forensics.CmdSever`` — manual weapon-driven severance.
    * ``world.medical.procedures._resolve_amputate`` (corpse branch) —
      chart-driven amputation on a corpse.
    * ``spawn_severed_head_for_corpse`` (legacy alias, head-only) —
      death-progression combat decapitation.

    Args:
        corpse: Source corpse.
        location_arg: Canonical severable container name
            (member of ``get_species_severable_containers(corpse.db.species)``).

    Returns:
        The spawned :class:`Appendage` / :class:`SeveredHead`, or
        ``None`` if the corpse has no room or the location was already
        severed.
    """
    from evennia import create_object
    from world.combat.constants import ORGAN_CONDITION_BY_DECAY
    from world.anatomy import get_species_part_name

    room = corpse.location
    if room is None:
        return None
    if location_arg in (corpse.db.severed_locations or ()):
        return None

    get_decay_stage = getattr(corpse, "get_decay_stage", None)
    decay_stage = get_decay_stage() if callable(get_decay_stage) else "fresh"
    condition = ORGAN_CONDITION_BY_DECAY.get(decay_stage, "damaged")
    species = (
        getattr(getattr(corpse, "db", None), "species", None) or "human"
    )

    if location_arg == "head":
        typeclass = "typeclasses.items.SeveredHead"
        readable_name = "head"
    else:
        typeclass = "typeclasses.items.Appendage"
        # Species-aware readable name for the item key.
        try:
            readable_name = get_species_part_name(
                species, location_arg, decay_stage,
            ) or location_arg.replace("_", " ")
        except Exception:
            readable_name = location_arg.replace("_", " ")

    appendage = create_object(
        typeclass,
        key=f"{condition} {readable_name}",
        location=room,
    )
    appendage.configure_from_sever(
        location_name=location_arg, condition=condition, corpse=corpse,
    )

    severed_list = list(corpse.db.severed_locations or ())
    if location_arg not in severed_list:
        severed_list.append(location_arg)
        corpse.db.severed_locations = severed_list

    apply_sever_to_corpse(corpse, location_arg)

    return appendage


def spawn_severed_head_for_corpse(corpse):
    """Legacy alias — head-only wrapper around
    :func:`spawn_severed_part_from_corpse`.

    Combat-driven decapitation (Phase C, issue #245 follow-up) cannot
    reach the corpse synchronously: a lethal edged neck hit flags the
    dying character, the asynchronous death pipeline builds the corpse,
    and this helper is invoked at the tail of
    :meth:`typeclasses.death_progression.DeathProgressionScript._create_corpse_from_character`
    once the corpse is fully populated.

    Returns:
        The spawned :class:`SeveredHead`, or ``None`` if the corpse has
        no location or the head was already severed.
    """
    return spawn_severed_part_from_corpse(corpse, "head")


def spawn_severed_head_for_living(character, *, injury_type="cut"):
    """Spawn + configure a :class:`SeveredHead` at the moment of decapitation.

    Living counterpart to :func:`spawn_severed_head_for_corpse`: the
    head item appears in the room synchronously with the killing blow
    (issue #343), rather than ~90s later when death progression builds
    the corpse.  The character then continues through the normal death
    pipeline, but now visibly headless — the corpse-side spawn becomes
    a no-op via the existing idempotency check on
    ``corpse.db.severed_locations``.

    Steps:

    1. Spawn a :class:`SeveredHead` in the character's room.
    2. Populate identity / decay / prose / trimmed snapshot via
       :meth:`SeveredHead.configure_from_living_decap` (which reads
       prose + wounds BEFORE the body is mutated).
    3. Strip the head-cluster prose + organ wound stages from the
       character via :func:`sever_character_body`, persist medical
       state, and recompute vital signs so the headless body is
       reflected immediately.
    4. Set ``character.db.head_severed_at_decap = True`` so the
       death-progression hook in
       :meth:`death_progression.DeathProgressionScript._create_corpse_from_character`
       knows to propagate the severed-head bookkeeping onto the corpse
       (and skip the redundant corpse-side spawn).

    Idempotent: if the character is already flagged as
    ``head_severed_at_decap`` the call returns ``None`` without
    re-spawning.

    Args:
        character: The character whose cervical spine just collapsed.
        injury_type: Edged injury that caused the cut (default ``"cut"``).
            Preserved for future use; the item itself is condition-tagged
            ``"pristine"`` regardless.

    Returns:
        The spawned :class:`SeveredHead`, or ``None`` if the character
        has no location to drop it into or the head has already been
        severed.
    """
    from evennia import create_object
    from world.anatomy import get_species_severed_head_locations

    room = character.location
    if room is None:
        return None
    if character.db.head_severed_at_decap:
        return None

    # Issue #356 Phase 2: species-aware head cluster.  Rats route
    # ``snout`` / ``fur`` here in place of ``face`` / ``hair``.
    severed_head_locations = get_species_severed_head_locations(
        getattr(getattr(character, "db", None), "species", None)
    )

    head = create_object(
        "typeclasses.items.SeveredHead",
        key="severed head",
        location=room,
    )
    head.configure_from_living_decap(
        character=character, injury_type=injury_type,
    )

    # Strip the head-cluster from the living body. ``sever_character_body``
    # drops the longdesc entries and sets head-container organs to
    # ``wound_stage="severed"`` / ``current_hp=0`` — matching the limb
    # pathway. Vital-sign recomputation lets capacity loss take effect
    # so blood / consciousness reflect the headless state.
    sever_character_body(character, severed_head_locations)
    medical_state = character.medical_state
    update_vital_signs = getattr(medical_state, "update_vital_signs", None)
    if callable(update_vital_signs):
        update_vital_signs()
    character.save_medical_state()

    character.db.head_severed_at_decap = True
    # The death-progression hook in
    # ``DeathProgressionScript._create_corpse_from_character`` gates
    # corpse-side cleanup (head-cluster prose / wound removal +
    # synthesised neck stump) on ``decapitation_pending``.  Combat sets
    # this flag *before* calling us, but chart-driven amputation goes
    # straight through this function — without the flag the corpse
    # would render wounds at every head-cluster location even though
    # those organs left with the severed head.  Owning both flags here
    # makes "head severed off a living body" a single coherent state
    # change regardless of caller.
    character.db.decapitation_pending = True

    # Severance leaves an open stump at the cut point.  Recording it
    # in ``surgical_state["incisions"]`` makes the suture verb work
    # uniformly across combat-driven decap (which goes through here)
    # and chart-driven amputation (which double-records via
    # ``_resolve_amputate`` — second call overwrites with the
    # surgeon as ``opened_by``, the right semantic).  Attacker
    # attribution is forensic-only; ``opened_by`` is write-only state.
    try:
        from world.medical.procedures import open_incision
        attacker = getattr(character.ndb, "_last_damage_attacker", None)
        open_incision(character, "head", surgeon=attacker)
    except Exception:
        # Deliberate (#469): incision recording is forensic-only —
        # never block the severance over its bookkeeping.
        pass

    return head


# ---------------------------------------------------------------------
# Living-character severance (PR Phase B, issue #245)
# ---------------------------------------------------------------------
#
# Where the corpse-side helpers above move prose / wounds off a *dead*
# body, these move a single limb off a *living* character: the limb
# becomes an :class:`Appendage` item, the character keeps living
# (capacity loss only — never a death trigger; decapitation routes
# through death → corpse, not through this path), and worn / wielded
# items that belong to the severed limb travel with it.
#
# All three are pure module-level helpers (no ``create_object`` /
# ``msg`` side effects) so they unit-test against plain-Python stubs.
# The orchestrator :func:`apply_sever_to_character` wires them together
# with the Evennia spawn + broadcast.


def apply_living_sever_overlay(appendage, *, longdescs, wounds, locations):
    """Copy a live character's prose + wounds for ``locations`` → appendage.

    Living-character analog of :func:`apply_wound_and_longdesc_overlay`.
    Where the corpse overlay reads ``corpse.db.{longdesc_data,
    wounds_at_death}``, the living data has different sources — the
    longdesc dict (``character.longdesc``) and the *visible* wound list
    (:func:`world.medical.wounds.get_character_wounds`) — so the caller
    snapshots both **before** any body mutation and passes them in.
    Keeping this a pure function over plain data makes it independently
    testable and decouples it from the medical / clothing machinery.

    The appendage receives ``db.longdesc_data`` and ``db.wounds_at_death``
    in the exact shape :meth:`Appendage.return_appearance` consumes, so
    a living-severed limb renders identically to a corpse-severed one.

    Args:
        appendage: Object whose ``db`` receives ``longdesc_data`` and
            ``wounds_at_death``.
        longdescs: Snapshot of ``character.longdesc`` (``{location: text}``).
            ``None`` is treated as empty.
        wounds: Snapshot of ``get_character_wounds(character)`` — a list
            of wound dicts (keys: ``injury_type``, ``location``,
            ``severity``, ``organ``, ``organ_obj``).  ``None`` → empty.
        locations: Iterable of body-location names to carry forward.
    """
    locs = frozenset(locations)

    appendage.db.longdesc_data = {
        loc: text
        for loc, text in (longdescs or {}).items()
        if loc in locs and text
    }

    carried = []
    for wound in wounds or []:
        if wound.get("location") not in locs:
            continue
        organ_obj = wound.get("organ_obj")
        # Read live HP *before* the caller mutates the body — mirrors
        # the corpse-side death snapshot in
        # ``death_progression._create_corpse_from_character`` which
        # captures ``organ_obj.current_hp`` at the instant of death.
        # Hardcoding zero here destroyed every carried organ on
        # severance, breaking parity with the corpse-sever contract
        # the comment below claims.
        current_hp = getattr(organ_obj, "current_hp", 0) if organ_obj else 0
        max_hp = getattr(organ_obj, "max_hp", 0) if organ_obj else 0
        carried.append({
            "injury_type": wound.get("injury_type", "generic"),
            "location": wound.get("location"),
            "severity": wound.get("severity", "Moderate"),
            # Wounds on a detached part render at the preserved-wound
            # stage, matching the corpse-severed contract.
            "stage": "old",
            "organ": wound.get("organ"),
            "organ_damage": {
                "current_hp": current_hp,
                "max_hp": max_hp,
                "container": wound.get("location"),
            },
        })
    appendage.db.wounds_at_death = carried


def sever_character_body(character, containers):
    """Mutate a living ``character`` to reflect a limb chain severed.

    Symmetric counterpart to :func:`apply_living_sever_overlay`: the
    overlay copies prose onto the detached limb, this strips the matching
    state from the source character.

    Issue #339: this helper accepts an iterable of containers so that
    downstream limb parts travel with the cut. Severing a shin takes
    the foot; severing a thigh takes the shin and foot. The caller
    (:func:`apply_sever_to_character`) resolves the chain via
    :data:`world.combat.constants.LIMB_DOWNSTREAM_CHAIN`. A single
    container is still accepted as a string for backwards-compat with
    older call sites and tests.

    For every container in the chain:

    * The longdesc prose is dropped (the limb is no longer part of the
      body to describe) — reassigned, not mutated in place, so the
      ``AttributeProperty`` persists the change.
    * Every organ whose ``container`` matches is set to
      ``current_hp = 0`` with ``wound_stage = 'severed'`` (a clean
      amputation, distinct from the ``'destroyed'`` mangling of
      in-place combat damage). The
      :func:`world.medical.wounds.get_character_wounds` renderer's
      cut-point filter (#339) suppresses downstream severance wounds
      so the body shows ONE wound at the cut point, not one per chain
      location.

    Persisting the medical state and recomputing vital signs is left to
    the caller so this stays a pure, stub-testable mutation with no
    Evennia side effects.

    Args:
        character: The living character losing the limb.
        containers: Canonical severed-limb locations. Either a single
            container string (e.g. ``"left_arm"``) for the legacy
            single-container path, or an iterable of containers for
            the chain path (e.g. ``("left_shin", "left_foot")``).
    """
    # Accept both legacy single-string and new iterable signatures.
    if isinstance(containers, str):
        chain = (containers,)
    else:
        chain = tuple(containers)
    chain_set = set(chain)

    longdescs = character.longdesc
    if longdescs:
        remaining = {
            loc: text
            for loc, text in dict(longdescs).items()
            if loc not in chain_set
        }
        if remaining != dict(longdescs):
            character.longdesc = remaining

    medical_state = character.medical_state
    for organ in medical_state.organs.values():
        if organ.container in chain_set:
            organ.current_hp = 0
            organ.wound_stage = "severed"


def detach_items_to_appendage(character, appendage, containers):
    """Move worn / wielded items belonging to the severed chain onto ``appendage``.

    Item-retention rule (issue #245), extended for the limb downstream
    chain (issue #339):

    * A **worn** item travels onto the appendage if **all** of the body
      locations it is currently worn at are within the severed cluster
      (the full chain — e.g. for a severed shin, ``{left_shin,
      left_foot}``). A glove worn solely at ``left_hand`` follows a
      severed left arm; a boot worn solely at ``left_foot`` follows a
      severed left shin; a jacket spanning chest + both arms stays on
      the character when one arm is severed.
    * A **wielded** weapon in *any* hand whose container is in the
      severed chain (via :data:`world.combat.constants.SEVER_HAND_BY_CONTAINER`)
      **drops to the ground** at the character's current location
      (PR-H0, #307). Severance loosens the dead hand's grip; the weapon
      lands separately from the severed limb. Uses
      :func:`commands.combat.jump.drop_to_room` so gravity / sky-room /
      proximity tracking apply uniformly with the player ``drop``
      command. Prior behaviour (weapon carried on the appendage) was
      surprising during salvage — players couldn't pick up the sword
      without first interacting with the severed arm.

    Bookkeeping (``worn_items`` / ``hands`` dicts) is updated purely and
    reassigned so the ``AttributeProperty`` persists.  The physical
    relocation uses ``item.move_to`` when available; it is guarded so the
    pure bookkeeping remains exercisable against plain-Python stubs.

    Args:
        character: The living character losing the limb.
        appendage: Destination :class:`Appendage` item.
        containers: Canonical severed-limb locations. Either a single
            container string for the legacy single-container path, or
            an iterable of containers for the chain path.

    Returns:
        list: Items moved onto the appendage (worn first, then wielded).
    """
    # Issue #356 Phase 2: species-aware hand-side mapping.
    from world.anatomy import get_species_sever_hand_by_container
    sever_hand_by_container = get_species_sever_hand_by_container(
        getattr(getattr(character, "db", None), "species", None)
    )

    # Accept legacy single-string + new iterable signatures.
    if isinstance(containers, str):
        chain = (containers,)
    else:
        chain = tuple(containers)
    severed_locs = set(chain)
    moved = []

    # --- Worn items fully contained within the severed cluster --------
    worn = character.worn_items or {}
    item_locations = {}
    for loc, items in worn.items():
        for item in items or []:
            item_locations.setdefault(item, set()).add(loc)

    items_to_move = [
        item for item, locs in item_locations.items()
        if locs <= severed_locs
    ]

    if items_to_move:
        new_worn = {}
        for loc, items in worn.items():
            kept = [it for it in (items or []) if it not in items_to_move]
            if kept:
                new_worn[loc] = kept
        character.worn_items = new_worn

        # PR-H3 (#307): register the moved items in the appendage's
        # own worn_items dict so they remain structurally "worn at
        # location X of this severed part" rather than degrading to
        # generic contents.  Each item lands at every location it
        # was worn at on the original body (a glove worn solely at
        # left_hand registers at left_hand on the appendage; a coat
        # spanning chest+arms wouldn't reach this branch because its
        # coverage isn't ⊆ severed_locs).
        #
        # Test stubs that don't carry a ``db`` surface skip the
        # carry-forward bookkeeping; physical relocation still
        # happens so the basic sever contract is preserved.
        appendage_db = getattr(appendage, "db", None)
        appendage_worn = None
        if appendage_db is not None:
            appendage_worn = dict(
                getattr(appendage_db, 'worn_items', None) or {}
            )
        for item in items_to_move:
            _relocate_item(item, appendage)
            moved.append(item)
            if appendage_worn is not None:
                for loc in item_locations.get(item, ()):
                    appendage_worn.setdefault(loc, []).append(item)
        if appendage_db is not None:
            appendage_db.worn_items = appendage_worn

    # --- Wielded weapons in any chain-hand --------------------------
    hands_to_clear = set()
    for chain_loc in chain:
        hand = sever_hand_by_container.get(chain_loc)
        if hand:
            hands_to_clear.add(hand)

    if hands_to_clear:
        hands = character.hands or {}
        new_hands = dict(hands)
        # PR-H0: held items drop to the character's current location
        # rather than relocating onto the severed appendage.  The
        # severed limb is bookkept as "had a weapon in it before the
        # cut", but the weapon itself falls free.  Use the canonical
        # drop-to-room pipeline for gravity / proximity parity with
        # the player ``drop`` command.
        drop_room = getattr(character, "location", None)
        for hand in hands_to_clear:
            held = new_hands.get(hand)
            if held:
                new_hands[hand] = None
                if drop_room is not None:
                    # Deferred import — ``commands.combat.jump`` pulls
                    # in evennia.commands.Command which we don't want
                    # at module load time for this typeclasses file.
                    from commands.combat.jump import drop_to_room as _drop
                    _drop(held, drop_room)
                else:
                    # Fall back to the legacy relocation if the
                    # character has no location (test stubs, edge
                    # cases) — keeps the dropped item somewhere
                    # findable rather than orphaning it.
                    _relocate_item(held, appendage)
                # ``moved`` historically tracked items that travelled
                # WITH the appendage.  Held weapons no longer travel
                # there, so they are intentionally not appended.
        character.hands = new_hands

    return moved


def _relocate_item(item, destination):
    """Best-effort physical move of ``item`` into ``destination``.

    Guarded so the surrounding pure bookkeeping in
    :func:`detach_items_to_appendage` stays testable against stubs that
    lack Evennia's ``move_to``.
    """
    move_to = getattr(item, "move_to", None)
    if callable(move_to):
        move_to(destination, quiet=True)


def apply_sever_to_character(character, container, *, injury_type="cut"):
    """Sever ``container`` from a living ``character`` into a new Appendage.

    Orchestrator that wires the pure helpers together with the Evennia
    spawn + per-observer broadcast:

    1. Snapshot is taken implicitly by configuring the appendage
       *before* the body is mutated (the overlay reads the still-intact
       character prose + wounds).
    2. Spawn an :class:`Appendage` in the character's room and populate
       its provenance / prose via
       :meth:`Appendage.configure_from_living_sever`.
    3. Strip the limb from the character's body
       (:func:`sever_character_body`) and recompute vital signs so the
       capacity loss takes effect; persist the medical state.
    4. Move worn / wielded items belonging to the limb onto the
       appendage (:func:`detach_items_to_appendage`).
    5. Broadcast the severance per-observer.

    Decapitation is **not** handled here — a lethal neck hit routes
    through the normal death → corpse pipeline (where the existing
    :func:`apply_sever_to_corpse` head path and :class:`SeveredHead`
    take over).  This path is for survivable limb loss only.

    Args:
        character: The living character losing the limb.
        container: Canonical severed-limb location (member of
            :data:`world.combat.constants.SEVERABLE_CONTAINERS`, minus
            ``"head"``).
        injury_type: Edged injury that caused the cut (default ``"cut"``).

    Returns:
        The spawned :class:`Appendage`, or ``None`` if the character has
        no location to drop it into.
    """
    from evennia import create_object
    from world.anatomy import get_species_limb_downstream_chain

    room = character.location
    if room is None:
        return None

    # Issue #339: resolve the downstream limb chain. Severing at a
    # thigh takes shin + foot; at a shin takes the foot; at a hand or
    # foot takes only itself. Containers not in the chain map fall
    # back to the single-container path for backwards compatibility
    # (and for the head, which routes through its own pipeline).
    # Issue #356 Phase 2: chain map is species-aware — rats have a
    # two-segment fore/hindlimb chain, not the three-segment
    # thigh→shin→foot.
    chain_map = get_species_limb_downstream_chain(
        getattr(getattr(character, "db", None), "species", None)
    )
    chain = chain_map.get(container, (container,))

    appendage = create_object(
        "typeclasses.items.Appendage",
        key="severed limb",
        location=room,
    )
    appendage.configure_from_living_sever(
        character=character,
        location_name=container,
        injury_type=injury_type,
        chain=chain,
    )

    sever_character_body(character, chain)
    medical_state = character.medical_state
    update_vital_signs = getattr(medical_state, "update_vital_signs", None)
    if callable(update_vital_signs):
        update_vital_signs()
    character.save_medical_state()

    # Severance leaves an open stump at the cut point.  Recording the
    # incision here means the suture verb finds the same open wound
    # whether the severance came from combat (which calls us
    # directly via ``ArmorMixin.take_damage``) or from chart-driven
    # amputation (``_resolve_amputate`` calls us, then double-records
    # via its own ``open_incision`` to attribute the surgeon as
    # ``opened_by``).  Attacker attribution is forensic-only here.
    try:
        from world.medical.procedures import open_incision
        attacker = getattr(character.ndb, "_last_damage_attacker", None)
        open_incision(character, container, surgeon=attacker)
    except Exception:
        # Deliberate (#469): incision recording is forensic-only —
        # never block the severance over its bookkeeping.
        pass

    detach_items_to_appendage(character, appendage, chain)

    # Severance narrative — issue #332. Replaces the previous inline
    # template with a library lookup so each (location, injury_type,
    # severity) cell gets variant prose. Falls back gracefully to the
    # old inline pattern if anything goes wrong.
    attacker = getattr(character.ndb, "_last_damage_attacker", None)
    weapon = getattr(character.ndb, "_last_damage_weapon", None)
    try:
        from world.combat.messages.severance import get_severance_message
        from world.identity_utils import msg_room_identity

        msgs = get_severance_message(
            location=container,
            injury_type=injury_type,
            attacker=attacker,
            target=character,
            item=weapon,
            severity="grievous",
            hit_location=container,
        )
        if attacker is not None:
            attacker.msg(msgs["attacker_msg"])
        character.msg(msgs["victim_msg"])
        exclude = [character]
        if attacker is not None:
            exclude.append(attacker)
        msg_room_identity(
            location=room,
            template=msgs["observer_template"],
            char_refs=msgs["observer_char_refs"],
            exclude=exclude,
        )
    except Exception:
        # Library lookup hiccup — fall back to the legacy inline beat
        # so we never silently swallow a severance moment.
        from world.identity_utils import msg_room_identity

        part_name = appendage.key
        msg_room_identity(
            location=room,
            template=(
                f"{{actor}}'s {part_name} is severed in a spray of blood "
                f"and falls to the ground!"
            ),
            char_refs={"actor": character},
            exclude=[],
        )

    return appendage


def apply_severed_head_overlay(head, corpse):
    """Copy identity + decay-clock fields from ``corpse`` onto ``head``.

    Extracted from :meth:`SeveredHead.configure_from_sever` so unit
    tests can exercise the overlay logic against plain-Python stubs
    without instantiating an Evennia typeclass.

    Contract — after this call ``head.db`` has:

    * ``signature_at_death`` / ``apparent_uid_at_death`` copied verbatim
      from the source corpse (IdentityBearerMixin contract).
    * ``sleeve_uid`` copied from the source corpse.  This is the
      face-side identity axis — the only one that survives
      decapitation.  Surfaced via :attr:`SeveredHead.sleeve_uid` so
      :func:`world.identity.get_identity_signature` produces a
      recognisable signature for the head and the mixin's natural- /
      forensic-recognition passes can match looker memory.
    * ``creation_time`` / ``death_time`` / ``death_cause`` shared with
      the corpse so the head ages on the same decay clock.

    The ``medical_state_at_death`` snapshot and ``removed_organs``
    subset are NOT written here — :meth:`Appendage.configure_from_sever`
    (the super-call that runs before this overlay) already lays them
    down via :func:`apply_organ_snapshot_overlay` filtered to the
    head chain.  This used to be a double-write that produced the
    same data twice; collapsing to one keeps the head contract
    identical without the redundant pass.

    Identity is *duplicated* across head and corpse: the head carries
    face-side recognition (sleeve_uid + forensic chain), the corpse
    keeps its snapshot for autopsy.  Corpse-side ``head_severed`` is
    set by :func:`apply_sever_to_corpse`, which runs in the command
    path after this overlay.  See issue #208.
    """
    # IdentityBearerMixin contract — copy snapshotted identity.
    head.db.signature_at_death = corpse.db.signature_at_death
    head.db.apparent_uid_at_death = corpse.db.apparent_uid_at_death
    # Face-side body identity — surfaced via SeveredHead.sleeve_uid so
    # the live-signature derivation in world.identity matches.
    head.db.sleeve_uid = corpse.db.sleeve_uid

    # Shared decay clock — head ages with the corpse.
    head.db.creation_time = corpse.db.creation_time
    head.db.death_time = corpse.db.death_time
    head.db.death_cause = corpse.db.death_cause


def apply_severed_head_overlay_from_living(head, character):
    """Copy identity / decay / trimmed snapshot from a *living* character.

    Living counterpart to :func:`apply_severed_head_overlay` (which reads
    from a corpse).  Used by :func:`spawn_severed_head_for_living` so the
    head item spawned the moment the cervical spine is destroyed carries
    the same identity / recognition / trimmed-snapshot surface a
    corpse-spawned head would (issue #343).

    The head's decay clock starts *now* — there is no shared corpse clock
    yet because the death-progression window has not begun.  When the
    corpse is built ~90s later, both the corpse and the head will age on
    their own clocks; in practice the head is slightly fresher than the
    corpse by the length of the progression window, which is the right
    storytelling: the head was detached first.

    Contract — after this call ``head.db`` has:

    * ``signature_at_death`` / ``apparent_uid_at_death`` derived from the
      live character via :mod:`world.identity` (mirrors the corpse
      snapshot in :meth:`death_progression.DeathProgressionScript._create_corpse_from_character`).
    * ``sleeve_uid`` copied from ``character.sleeve_uid`` (the
      ``AttributeProperty`` on :class:`typeclasses.characters.Character`).
    * ``creation_time`` / ``death_time`` = ``time.time()``;
      ``death_cause`` derived from ``character.get_death_cause()`` when
      available, else ``"decapitation"``.
    * ``medical_state_at_death`` = trimmed snapshot of head-container
      organs from ``character.medical_state.to_dict()``; body-wide
      fields blanked.
    * ``removed_organs`` filtered to the head-container subset (no
      living-character removed-organ list exists; defaults to empty).
    """
    import time

    # Identity snapshot — same axes the corpse captures at death.
    try:
        from world.identity import get_apparent_uid, get_identity_signature
        head.db.signature_at_death = get_identity_signature(character)
        head.db.apparent_uid_at_death = get_apparent_uid(character)
    except (AttributeError, TypeError, ValueError):
        head.db.signature_at_death = None
        head.db.apparent_uid_at_death = None

    # ``sleeve_uid`` lives on a category="identity" AttributeProperty;
    # reading the property (not ``db.sleeve_uid``) is required.
    head.db.sleeve_uid = getattr(character, "sleeve_uid", None)

    now = time.time()
    head.db.creation_time = now
    head.db.death_time = now
    try:
        cause = character.get_death_cause()
    except (AttributeError, TypeError):
        cause = None
    head.db.death_cause = cause or "decapitation"

    # Trimmed head-container medical snapshot — same shape the corpse
    # path produces, so harvest / autopsy code consumes it identically.
    head_organs = {}
    try:
        snapshot = character.medical_state.to_dict() or {}
    except (AttributeError, TypeError):
        snapshot = {}
    organs = snapshot.get("organs") or {}
    for name, data in organs.items():
        if (data.get("container") or "") == "head":
            head_organs[name] = dict(data)

    head.db.medical_state_at_death = {
        "organs": head_organs,
        "conditions": [],
        "blood_level": None,
        "pain_level": None,
        "consciousness": None,
    }
    head.db.removed_organs = []


class SeveredHead(IdentityBearerMixin, Appendage):
    """A severed head — super-item spawned by ``sever head from <corpse>``.

    Sibling of :class:`Appendage` but additionally inherits
    :class:`typeclasses.identity_bearer.IdentityBearerMixin` so the
    head carries the same two-pass recognition + forensic-recovery
    surface as a :class:`typeclasses.corpse.Corpse`.  Investigators
    can autopsy the head, harvest brain/eyes from it, and recognise
    its identity through decay exactly as they could the source
    corpse — within the limits of the head-container partition.

    Decay clock is shared with the source corpse: ``creation_time``
    is copied at severance, so a head that left a moderate-decay
    corpse is itself moderate-decay.  ``death_time`` is likewise
    copied so the autopsy "time since death" reads consistently.

    Attributes (``self.db``):
        Inherited from :class:`Appendage` —
            ``location_name`` (always ``"head"``), ``condition``,
            ``source_signature``, ``source_apparent_uid``,
            ``source_corpse_dbref``.
        IdentityBearerMixin contract —
            ``signature_at_death``, ``apparent_uid_at_death``.
        Decay clock —
            ``creation_time``, ``death_time``, ``death_cause``.
        Trimmed snapshot —
            ``medical_state_at_death`` (head-container organs only,
            other fields blanked) and ``removed_organs`` (head-
            container subset of the source corpse's removals).

    Severing a SeveredHead is refused at the :class:`commands.forensics.CmdSever`
    gate (Corpse-only ``isinstance`` check) — heads are terminal.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.location_name = "head"
        # IdentityBearerMixin contract — populated by configure_from_sever.
        self.db.signature_at_death = None
        self.db.apparent_uid_at_death = None
        # Face-side body identity — copied from source corpse at sever
        # time by :func:`apply_severed_head_overlay`.  Exposed via the
        # :attr:`sleeve_uid` property so ``world.identity.get_identity_signature``
        # picks it up the same way it picks up a Corpse's sleeve_uid.
        # Override axes (height/build/keyword) and worn essential items
        # are intentionally NOT carried: those are body-side and stay
        # with the corpse.  The head presents face only.
        self.db.sleeve_uid = None
        # Decay clock — copied from source corpse at severance so the
        # head and corpse age together.  Default to creation time of
        # this object until configure_from_sever overwrites.
        import time
        self.db.creation_time = time.time()
        self.db.death_time = time.time()
        self.db.death_cause = "unknown"
        # Trimmed head-container medical snapshot — set by
        # configure_from_sever.  Conformant with the dict shape
        # :meth:`typeclasses.corpse.Corpse.get_medical_snapshot`
        # returns so harvest / autopsy code can consume both via
        # ``get_medical_snapshot``.
        self.db.medical_state_at_death = None
        self.db.removed_organs = []
        # ``severed_locations`` is unused on a head (you cannot sever
        # the head off a head), but harvest/autopsy code paths may
        # read it defensively — keep it present and empty.
        self.db.severed_locations = []

    # ------------------------------------------------------------------
    # IdentityBearerMixin contract — decay surface
    # ------------------------------------------------------------------

    # Decay tier thresholds, in seconds since ``creation_time``.  Same
    # ladder the corpse uses (see ``world/combat/constants.py``
    # ``CORPSE_DECAY_*``).  Copied locally so we don't need a Corpse
    # instance to consult.
    _DECAY_STAGES = (
        ("fresh", 3600),
        ("early", 86400),
        ("moderate", 259200),
        ("advanced", 604800),
    )

    @property
    def sleeve_uid(self):
        """Expose the deceased's sleeve UID via the property surface.

        :func:`world.identity.get_identity_signature` reads
        ``getattr(char, "sleeve_uid", None)``; mirroring
        :attr:`typeclasses.corpse.Corpse.sleeve_uid` here lets the
        severed head flow through the same identity pipeline so the
        IdentityBearerMixin recognition path can match looker memory.

        The sleeve UID is the face-side identity axis — the only one
        that survives decapitation.  Body-side axes (height / build /
        keyword overrides, worn essential items) stay with the corpse;
        :meth:`get_worn_items` returns ``[]`` on a head so the
        essential-items axis collapses to an empty tuple naturally.
        """
        return self.db.sleeve_uid

    def get_decay_stage(self):
        """Return the current decay tier; mirrors Corpse semantics."""
        import time
        elapsed = time.time() - (self.db.creation_time or time.time())
        for stage, threshold in self._DECAY_STAGES:
            if elapsed < threshold:
                return stage
        return "skeletal"

    def _decay_display_name(self):
        """Fallback display when no recognition memory matches.

        PR-G: delegates to the species registry so head names drift
        through the decay tiers in lockstep with the rest of the
        species-aware naming surface (corpse, severed limbs, organs).
        Skeletal heads render as "skeletal head" rather than a bespoke
        "skull" — gameplay-consistent with the unified vocabulary —
        though the species table can override this later if a "skull"
        alias is wanted as a search keyword.
        """
        from world.anatomy import get_species_part_name

        species = self.db.source_species or "human"
        stage = self.get_decay_stage()
        return get_species_part_name(species, "head", stage)

    def get_medical_snapshot(self):
        """Return the trimmed head-container medical snapshot, if any.

        Same contract as :meth:`typeclasses.corpse.Corpse.get_medical_snapshot`;
        consumed by :class:`commands.forensics.CmdHarvest` and
        :class:`commands.forensics.CmdAutopsy` once PR-C widens their
        isinstance gates.
        """
        return self.db.medical_state_at_death

    def get_worn_items(self, location=None):
        """Heads carry no worn clothing — return ``[]``.

        Renderer compatibility shim for any code path that calls
        :func:`world.identity.get_essential_item_type_ids` against a
        severed head (the identity signature is the snapshotted one,
        not a re-derived live signature).
        """
        del location  # parity with ClothingMixin.get_worn_items signature
        return []

    # ------------------------------------------------------------------
    # Sever-time configuration
    # ------------------------------------------------------------------

    def configure_from_sever(self, *, location_name, condition, corpse):
        """Populate identity + decay + trimmed snapshot fields at sever.

        Overrides :meth:`Appendage.configure_from_sever` to additionally
        copy the corpse's identity / death / decay state and to build
        the trimmed head-container medical snapshot.

        ``location_name`` is expected to be ``"head"`` — the caller
        (:class:`commands.forensics.CmdSever`) routes only heads here.
        We don't assert it, to keep the surface duck-typed and to leave
        future container types (severed face? severed neck?) the door
        open.
        """
        # Inherited bookkeeping: location_name, condition, source_*
        # provenance, display key.  The Appendage super-call also
        # invokes :func:`apply_wound_and_longdesc_overlay` for the
        # single ``"head"`` location; we re-invoke it below with the
        # full head-cluster set so face / neck / eyes / ears prose
        # also follows the severed head.
        super().configure_from_sever(
            location_name=location_name, condition=condition, corpse=corpse,
        )
        # Identity / decay / trimmed snapshot overlay (unit-testable).
        apply_severed_head_overlay(self, corpse)
        # Re-apply wound + longdesc overlay across the full head-cluster
        # (overrides the head-only set the Appendage super-call laid
        # down).  Per PR #198: face, neck, eyes, ears all visually leave
        # with the head.  Issue #356 Phase 2: species-aware cluster.
        from world.anatomy import get_species_severed_head_locations
        apply_wound_and_longdesc_overlay(
            self, corpse,
            get_species_severed_head_locations(corpse.db.species),
        )

    def configure_from_living_decap(self, *, character, injury_type="cut"):
        """Populate head fields from a *living* decapitated character.

        Living counterpart to :meth:`configure_from_sever` — invoked by
        :func:`spawn_severed_head_for_living` the instant the cervical
        spine is destroyed.  Sets provenance, condition, prose, identity,
        decay, and the trimmed head-container snapshot directly off the
        live character, without going through the death-progression
        corpse pipeline (issue #343).

        Bookkeeping mirrors :meth:`Appendage.configure_from_living_sever`:

        * ``location_name`` is always ``"head"``.
        * ``condition`` is always ``"pristine"`` (a fresh living sever
          has no decay; the head ages from this moment forward).
        * ``key`` is the species-aware fresh-tier head name.
        * ``desc`` is the species-aware severed-part description.
        * Longdesc + visible wounds for the head cluster are overlaid
          via :func:`apply_living_sever_overlay`.
        * Identity / decay / snapshot are overlaid via
          :func:`apply_severed_head_overlay_from_living`.
        """
        # Issue #356 Phase 2: species-aware head cluster.
        from world.anatomy import (
            get_severed_part_description,
            get_species_part_name,
            get_species_severed_head_locations,
            prepend_condition_to_desc,
        )

        condition = "pristine"
        self.db.location_name = "head"
        self.db.condition = condition
        self.db.source_corpse_dbref = None

        # Snapshot gender + name so carried longdesc pronoun / name tokens
        # resolve at render time (parity with the limb living-sever path).
        self.db.original_gender = character.gender
        self.db.original_character_name = character.key

        species = character.db.species or "human"
        self.db.source_species = species
        self.key = get_species_part_name(species, "head", "fresh")

        prose = get_severed_part_description(species, "head", condition)
        composed = prepend_condition_to_desc(condition, prose)
        if composed:
            self.db.desc = composed

        # Forensic-chain provenance — also stamped by
        # ``apply_severed_head_overlay_from_living`` as
        # ``signature_at_death`` / ``apparent_uid_at_death``; the
        # Appendage-layer ``source_*`` fields are kept in lockstep so
        # the manual ``CmdSever`` and combat paths read the same.
        try:
            from world.identity import get_apparent_uid, get_identity_signature
            self.db.source_signature = get_identity_signature(character)
            self.db.source_apparent_uid = get_apparent_uid(character)
        except (AttributeError, TypeError, ValueError):
            self.db.source_signature = None
            self.db.source_apparent_uid = None

        # Carry the full head-cluster prose + wounds onto the head.
        # Read BEFORE the caller mutates the body via
        # ``sever_character_body`` so the source data is still intact.
        from world.medical.wounds import get_character_wounds

        longdescs = dict(character.longdesc or {})
        try:
            wounds = get_character_wounds(character) or []
        except (AttributeError, TypeError, ValueError):
            wounds = []
        apply_living_sever_overlay(
            self,
            longdescs=longdescs,
            wounds=wounds,
            locations=get_species_severed_head_locations(species),
        )

        # Identity / decay / trimmed head-container snapshot.
        apply_severed_head_overlay_from_living(self, character)

