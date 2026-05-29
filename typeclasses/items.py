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

    def configure_from_sever(self, *, location_name, condition, corpse):
        """Populate forensic-chain fields immediately after spawn.

        Args:
            location_name (str): Canonical body-location identifier.
            condition (str): Freshness descriptor.
            corpse: The source :class:`typeclasses.corpse.Corpse`.
        """
        from world.anatomy import get_species_part_name

        self.db.location_name = location_name
        self.db.condition = condition
        self.db.source_signature = corpse.db.signature_at_death
        self.db.source_apparent_uid = corpse.db.apparent_uid_at_death
        self.db.source_corpse_dbref = corpse.dbref
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
        from world.anatomy import get_severed_part_description, prepend_condition_to_desc
        prose = get_severed_part_description(species, location_name, condition)
        composed = prepend_condition_to_desc(condition, prose)
        if composed:
            self.db.desc = composed
        # PR #198: pull this location's wound + longdesc prose off the
        # corpse onto ourselves.  The corpse-side mutation
        # (delete-from-source + synthesized stump wound) is handled by
        # :func:`commands.forensics._apply_sever_to_corpse` so this
        # helper stays a pure copy and is independently unit-testable.
        apply_wound_and_longdesc_overlay(self, corpse, (location_name,))

    def return_appearance(self, looker, **kwargs):
        """Compose appearance from base desc + carried longdesc + wounds.

        PR #198: severed limbs and heads carry forward the source
        corpse's per-location longdesc prose and wound records.  We
        render them after the base ``return_appearance`` output so the
        condition-keyed line (e.g. ``"fresh left arm"``) still leads.

        Longdesc text is shown verbatim — the ``condition`` prefix in
        the key already conveys decay state, so we deliberately skip
        the decay-modulation pass that
        :class:`typeclasses.corpse.Corpse` applies to its preserved
        longdescs.  Wound descriptions render at ``stage="old"`` to
        match the corpse's own preserved-wound contract.
        """
        base = super().return_appearance(looker, **kwargs)
        parts = [base] if base else []

        longdescs = self.db.longdesc_data or {}
        if longdescs:
            try:
                from world.combat.constants import ANATOMICAL_DISPLAY_ORDER
            except ImportError:
                ANATOMICAL_DISPLAY_ORDER = list(longdescs.keys())
            seen = set()
            for loc in ANATOMICAL_DISPLAY_ORDER:
                text = longdescs.get(loc)
                if text and loc not in seen:
                    parts.append(text)
                    seen.add(loc)
            # Any longdesc locations not in the canonical order
            # (defensive — preserves prose for nonstandard anatomy).
            for loc, text in longdescs.items():
                if text and loc not in seen:
                    parts.append(text)
                    seen.add(loc)

        wounds = self.db.wounds_at_death or []
        if wounds:
            try:
                from world.medical.wounds import get_wound_description
            except ImportError:
                get_wound_description = None
            if get_wound_description is not None:
                for wound in wounds:
                    try:
                        rendered = get_wound_description(
                            injury_type=wound.get("injury_type", "generic"),
                            location=wound.get(
                                "location", self.db.location_name or ""
                            ),
                            severity=wound.get("severity", "Moderate"),
                            stage="old",
                            organ=wound.get("organ"),
                            character=self,
                        )
                    except (KeyError, ValueError, AttributeError):
                        continue
                    if rendered:
                        parts.append(rendered)

        return "\n".join(p for p in parts if p)


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
        from world.combat.constants import SEVERED_HEAD_LOCATIONS
        head_locations = SEVERED_HEAD_LOCATIONS

    if location_arg == "head":
        locs = frozenset(head_locations)
    else:
        locs = frozenset({location_arg})

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
    # location, regardless of head-cluster size.
    remaining.append({
        "injury_type": "severed",
        "location": location_arg,
        "severity": "Critical",
        "stage": "old",
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


def apply_severed_head_overlay(head, corpse):
    """Copy identity / decay / trimmed snapshot from ``corpse`` onto ``head``.

    Extracted from :meth:`SeveredHead.configure_from_sever` so unit
    tests can exercise the overlay logic against plain-Python stubs
    without instantiating an Evennia typeclass (whose metaclass would
    bind ``super()`` to the concrete class and reject duck-typed
    ``self`` substitutes).

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
    * ``medical_state_at_death`` = trimmed snapshot — only organs whose
      ``container == "head"``; body-wide fields (conditions, blood,
      pain, consciousness) blanked because they describe the whole
      body and would lie if reported off a disembodied head.  Organs
      are deep-copied to prevent aliasing with the corpse snapshot.
    * ``removed_organs`` filtered to the head-container subset of the
      corpse's removed-organ list (so pre-sever harvests stay visible).

    Side-effect on ``corpse.db``:

    * ``head_severed`` is set to ``True``.  Identity is *duplicated*
      across head and corpse (the corpse retains
      ``signature_at_death`` / ``apparent_uid_at_death`` /
      ``sleeve_uid`` so :func:`world.forensics.extract_subject_from_corpse`
      and the ``autopsy`` command keep working) — but the corpse's
      look-time tertiary recognition is suppressed by
      :meth:`typeclasses.corpse.Corpse.get_display_name` reading
      this flag.  Game-mechanic justification: the face is the
      dominant unaided-recognition cue; without it, only an explicit
      autopsy can resolve the body's identity.
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

    # Trimmed head-container medical snapshot.
    corpse_snapshot = corpse.get_medical_snapshot() or {}
    organs = corpse_snapshot.get("organs") or {}
    head_organs = {
        name: dict(data)
        for name, data in organs.items()
        if (data.get("container") or "") == "head"
    }
    head.db.medical_state_at_death = {
        "organs": head_organs,
        "conditions": [],
        "blood_level": None,
        "pain_level": None,
        "consciousness": None,
    }

    # Head-container subset of removed_organs.
    corpse_removed = corpse.db.removed_organs or ()
    head.db.removed_organs = [
        name for name in corpse_removed if name in head_organs
    ]

    # Corpse-side ``head_severed`` flag is set by
    # :func:`apply_sever_to_corpse`, which runs in the command path
    # after this overlay.  Identity is *duplicated* across head and
    # corpse: the head carries face-side recognition (sleeve_uid +
    # forensic chain), while the corpse keeps its snapshot for
    # autopsy.  See issue #208.


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
        # with the head.
        from world.combat.constants import SEVERED_HEAD_LOCATIONS
        apply_wound_and_longdesc_overlay(
            self, corpse, SEVERED_HEAD_LOCATIONS,
        )

