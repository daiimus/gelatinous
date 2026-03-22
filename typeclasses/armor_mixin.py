"""
Armor Mixin

Provides armor damage reduction, plate carrier expansion, armor effectiveness
calculations, and armor degradation logic for Character objects.

Extracted from typeclasses/characters.py in Phase 4 refactoring.
"""


class ArmorMixin:
    """
    Mixin class providing armor and damage reduction methods.

    Methods:
        take_damage: Apply damage to a specific body location with injury type.
        _calculate_armor_damage_reduction: Calculate damage reduction from stacked armor.
        _expand_plate_carrier_layers: Expand plate carrier into multiple armor layers.
        _get_total_armor_rating: Get total armor rating including installed plates.
        _get_armor_effectiveness: Calculate armor effectiveness vs injury type.
        _degrade_armor: Degrade armor durability based on damage absorbed.

    Cross-cutting concerns:
        - Reads ``self.worn_items`` from ClothingMixin via MRO.
        - Calls ``self.save_medical_state()``, ``self.is_dead()``,
          ``self.is_unconscious()`` from Character core.
    """

    def take_damage(self, amount, location="chest", injury_type="generic", target_organ=None):
        """
        Apply damage to a specific body location with injury type.

        This is the primary damage method using the pure medical system.
        Replaces the old dual HP/medical approach.

        Args:
            amount (int): Damage amount
            location (str): Body location (head, chest, left_arm, etc.)
            injury_type (str): Type of injury (cut, blunt, bullet, etc.)
            target_organ (str): If specified, target this specific organ

        Returns:
            tuple: (died: bool, actual_damage: int) - Whether character died
                and actual damage applied after armor
        """
        if not isinstance(amount, int) or amount <= 0:
            return (False, 0)

        # Check for armor before applying damage
        final_damage = self._calculate_armor_damage_reduction(amount, location, injury_type)

        # Debug log damage before and after armor
        try:
            from world.combat.utils import debug_broadcast
            if final_damage < amount:
                damage_absorbed = amount - final_damage
                debug_broadcast(
                    f"{self.key} took {amount} raw damage → armor absorbed "
                    f"{damage_absorbed} → {final_damage} damage applied",
                    "DAMAGE", "ARMOR_CALC",
                )
            else:
                debug_broadcast(
                    f"{self.key} took {amount} raw damage (no armor protection)",
                    "DAMAGE", "NO_ARMOR",
                )
        except ImportError:
            pass

        # Apply anatomical damage through medical system
        from world.medical.utils import apply_anatomical_damage
        damage_results = apply_anatomical_damage(
            self, final_damage, location, injury_type, target_organ
        )

        # Save medical state after damage
        self.save_medical_state()

        # Debug broadcast damage application
        try:
            from world.combat.utils import debug_broadcast
            debug_broadcast(
                f"Applied {final_damage} {injury_type} damage to {self.key}'s {location}",
                "DAMAGE", "SUCCESS",
            )
        except ImportError:
            pass  # debug_broadcast not available

        # Handle death/unconsciousness state changes
        died = self.is_dead()
        unconscious = self.is_unconscious()

        if died:
            self.at_death()  # Direct call to main death handler
        elif unconscious:
            self._handle_unconsciousness()

        # Return death status and actual damage applied (after armor) for combat system
        return (died, final_damage)

    def _calculate_armor_damage_reduction(self, damage, location, injury_type):
        """
        Calculate damage reduction from stacked armor at the specified location.

        Integrates with clothing system - processes all armor layers for
        cumulative protection.

        Args:
            damage (int): Original damage amount
            location (str): Body location being hit
            injury_type (str): Type of damage (bullet, cut, stab, blunt, etc.)

        Returns:
            int: Final damage after armor reduction from all layers
        """
        # If no clothing system available, no armor protection
        if not hasattr(self, 'worn_items') or not self.worn_items:
            return damage

        # Find all armor covering this location, sorted by layer (outermost first)
        armor_layers = []
        # Cache coverage calculations and track seen items to avoid duplicates
        coverage_cache = {}
        seen_items = set()

        for loc, items in self.worn_items.items():
            for item in items:
                # Skip if we've already processed this item
                if id(item) in seen_items:
                    continue
                seen_items.add(id(item))

                # Check if this item covers the hit location and has armor rating
                # Use cached coverage to avoid repeated function calls
                if item not in coverage_cache:
                    coverage_cache[item] = getattr(
                        item, 'get_current_coverage',
                        lambda: getattr(item, 'coverage', []),
                    )()
                current_coverage = coverage_cache[item]

                if location in current_coverage:
                    # Check if this is a plate carrier - needs special handling
                    if (hasattr(item, 'is_plate_carrier') and
                            getattr(item, 'is_plate_carrier', False)):
                        # DEBUG: Log plate carrier detection
                        try:
                            from world.combat.utils import debug_broadcast
                            installed = getattr(item, 'installed_plates', {})
                            debug_broadcast(
                                f"PLATE_CARRIER detected: {item.key} for {location}, "
                                f"installed_plates={list(installed.keys())}",
                                "ARMOR_CALC", "DEBUG",
                            )
                        except Exception:
                            pass
                        # Expand plate carrier into multiple sequential layers
                        carrier_layers = self._expand_plate_carrier_layers(item, location)
                        # DEBUG: Log expansion results
                        try:
                            from world.combat.utils import debug_broadcast
                            debug_broadcast(
                                f"PLATE_EXPAND: {len(carrier_layers)} layers created "
                                f"from {item.key}",
                                "ARMOR_CALC", "DEBUG",
                            )
                            for layer in carrier_layers:
                                debug_broadcast(
                                    f"  Layer {layer['layer']}: {layer['item'].key} "
                                    f"({layer['armor_type']}, "
                                    f"rating={layer['armor_rating']})",
                                    "ARMOR_CALC", "DEBUG",
                                )
                        except Exception:
                            pass
                        armor_layers.extend(carrier_layers)
                    else:
                        # Regular armor - single layer
                        armor_rating = getattr(item, 'armor_rating', 0)
                        if armor_rating > 0:
                            armor_layers.append({
                                'item': item,
                                'layer': getattr(item, 'layer', 2),
                                'armor_rating': armor_rating,
                                'armor_type': getattr(item, 'armor_type', 'generic'),
                            })

        if not armor_layers:
            return damage  # No armor at this location

        # Sort by layer (outermost first) - higher layer numbers are outer
        armor_layers.sort(key=lambda x: x['layer'], reverse=True)

        # Apply armor layers sequentially (outer to inner)
        remaining_damage = damage
        total_damage_reduction = 0
        armor_debug_info = []

        for armor_layer in armor_layers:
            if remaining_damage <= 0:
                break  # No damage left to absorb

            item = armor_layer['item']
            # Safety check: ensure item still exists (edge case: deleted mid-combat)
            if not item or not hasattr(item, 'pk') or not item.pk:
                continue

            armor_rating = armor_layer['armor_rating']
            armor_type = armor_layer['armor_type']

            # Calculate this layer's damage reduction
            base_reduction_percent = self._get_armor_effectiveness(
                armor_type, injury_type, armor_rating
            )

            # Apply weakness exploitation if present
            weakness_penalty = armor_layer.get('weakness_exploited', 0.0)
            final_reduction_percent = max(0.0, base_reduction_percent - weakness_penalty)

            # Use round() instead of int() to avoid losing effectiveness on low damage
            layer_damage_reduction = round(remaining_damage * final_reduction_percent)

            # Apply the reduction
            remaining_damage = max(0, remaining_damage - layer_damage_reduction)
            total_damage_reduction += layer_damage_reduction

            # Degrade this armor layer
            self._degrade_armor(item, layer_damage_reduction)

            # Track for debug output
            if layer_damage_reduction > 0:
                effectiveness_display = f"{final_reduction_percent * 100:.0f}%"
                if weakness_penalty > 0:
                    effectiveness_display += f"(-{weakness_penalty * 100:.0f}%)"
                armor_debug_info.append(
                    f"{item.key}({effectiveness_display}={layer_damage_reduction}dmg)"
                )

        # Debug broadcast armor effectiveness
        try:
            from world.combat.utils import debug_broadcast
            if total_damage_reduction > 0:
                debug_info = " + ".join(armor_debug_info)
                debug_broadcast(
                    f"Armor absorbed {total_damage_reduction} damage: "
                    f"{debug_info} for {self.key}",
                    "ARMOR", "SUCCESS",
                )
        except ImportError:
            pass

        return int(remaining_damage)  # Ensure return type is always int

    def _expand_plate_carrier_layers(self, carrier, location):
        """
        Expand a plate carrier into multiple armor layers for the specified location.

        Each layer (base carrier + each applicable plate) gets processed separately
        with its own armor type and effectiveness calculation.

        Args:
            carrier: The plate carrier item
            location (str): Hit location (e.g., "chest", "back", "abdomen")

        Returns:
            list: List of armor layer dicts, each with item, layer,
                armor_rating, armor_type
        """
        layers = []
        base_layer_number = getattr(carrier, 'layer', 2)

        # Plates are outer layers (higher number = processed first)
        plate_layer_number = base_layer_number + 1

        # Layer 1: Base carrier (always present if carrier has rating)
        base_rating = getattr(carrier, 'armor_rating', 0)
        if base_rating > 0:
            layers.append({
                'item': carrier,
                'layer': base_layer_number,  # Inner layer
                'armor_rating': base_rating,
                'armor_type': getattr(carrier, 'armor_type', 'generic'),
            })

        # Layer 2+: Installed plates that protect this location
        if hasattr(carrier, 'installed_plates'):
            installed_plates = carrier.db.installed_plates or {}
            slot_coverage = carrier.db.plate_slot_coverage or {}

            # DEBUG: Log what we're working with
            try:
                from world.combat.utils import debug_broadcast
                debug_broadcast(
                    f"PLATE_LOOP: Processing {len(installed_plates)} slots "
                    f"for {location}",
                    "ARMOR_CALC", "DEBUG",
                )
                debug_broadcast(
                    f"PLATE_LOOP: installed_plates type={type(installed_plates)}, "
                    f"value={installed_plates}",
                    "ARMOR_CALC", "DEBUG",
                )
                debug_broadcast(
                    f"PLATE_LOOP: slot_coverage={slot_coverage}",
                    "ARMOR_CALC", "DEBUG",
                )
            except Exception:
                pass

            for slot_name, plate in installed_plates.items():
                # DEBUG: Log each slot
                try:
                    from world.combat.utils import debug_broadcast
                    plate_type = type(plate).__name__ if plate else "None"
                    plate_key = plate.key if plate and hasattr(plate, 'key') else "N/A"
                    plate_layer = (
                        getattr(plate, 'layer', 'MISSING') if plate else "N/A"
                    )
                    debug_broadcast(
                        f"PLATE_SLOT: slot={slot_name}, type={plate_type}, "
                        f"key={plate_key}, layer={plate_layer}, "
                        f"has_rating="
                        f"{hasattr(plate, 'armor_rating') if plate else False}",
                        "ARMOR_CALC", "DEBUG",
                    )
                except Exception as e:
                    from world.combat.utils import debug_broadcast
                    debug_broadcast(
                        f"PLATE_SLOT_ERROR: {e}", "ARMOR_CALC", "ERROR"
                    )
                    pass

                if not plate or not hasattr(plate, 'armor_rating'):
                    continue

                # Check if this plate protects the hit location
                protected_locations = slot_coverage.get(slot_name, [])
                # DEBUG: Log coverage check
                try:
                    from world.combat.utils import debug_broadcast
                    debug_broadcast(
                        f"PLATE_COVERAGE: slot={slot_name}, "
                        f"protects={protected_locations}, location={location}, "
                        f"match={location in protected_locations}",
                        "ARMOR_CALC", "DEBUG",
                    )
                except Exception:
                    pass
                if location not in protected_locations:
                    continue

                # Get plate's armor properties
                plate_rating = getattr(plate, 'armor_rating', 0)
                plate_type = getattr(plate, 'armor_type', 'generic')

                # For abdomen with 2 side plates, each contributes half its rating
                # This is because side plates are angled and only partially cover abdomen
                if location == "abdomen" and slot_name in ["left_side", "right_side"]:
                    plate_rating = plate_rating // 2

                if plate_rating > 0:
                    layers.append({
                        'item': plate,  # Reference the plate itself for degradation
                        'layer': plate_layer_number,  # Outer layer - processed before carrier
                        'armor_rating': plate_rating,
                        'armor_type': plate_type,  # Use plate's material, not carrier's
                    })

        return layers

    def _get_total_armor_rating(self, item, location=None):
        """
        Get total armor rating for an item, including installed plates for carriers.

        For plate carriers, only counts plates in slots that protect the
        specified location.

        Args:
            item: The armor item to evaluate
            location (str): Hit location to check (e.g., "chest", "back", "torso")

        Returns:
            int: Total armor rating (base item + installed plates)
        """
        base_rating = getattr(item, 'armor_rating', 0)

        # Check if this is a plate carrier with installed plates
        if (hasattr(item, 'is_plate_carrier') and
                getattr(item, 'is_plate_carrier', False) and
                hasattr(item, 'installed_plates')):

            installed_plates = getattr(item, 'installed_plates', {})
            plate_rating_bonus = 0

            # Get slot-to-location mapping (if available)
            slot_coverage = getattr(item, 'plate_slot_coverage', {})

            for slot_name, plate in installed_plates.items():
                if plate and hasattr(plate, 'armor_rating'):
                    # If location is specified and we have slot coverage mapping,
                    # only count plates that protect this location
                    if location and slot_coverage:
                        protected_locations = slot_coverage.get(slot_name, [])
                        if location not in protected_locations:
                            continue  # This plate doesn't protect this location

                    plate_rating_bonus += getattr(plate, 'armor_rating', 0)

            return base_rating + plate_rating_bonus

        return base_rating

    def _get_armor_effectiveness(self, armor_type, injury_type, armor_rating):
        """
        Calculate armor effectiveness percentage based on armor type vs injury type.

        Args:
            armor_type (str): Type of armor (kevlar, steel, leather, etc.)
            injury_type (str): Type of incoming damage
            armor_rating (int): Armor rating (1-10 scale)

        Returns:
            float: Damage reduction percentage (0.0 to 0.95)
        """
        from world.combat.constants import ARMOR_EFFECTIVENESS_MATRIX

        # Get base effectiveness from centralized matrix
        base_effectiveness = ARMOR_EFFECTIVENESS_MATRIX.get(
            armor_type,
            ARMOR_EFFECTIVENESS_MATRIX['generic'],
        )
        effectiveness = base_effectiveness.get(
            injury_type, 0.2
        )  # Default 20% for unknown damage types

        # Scale by armor rating (1-10 becomes 0.1-1.0 multiplier)
        rating_multiplier = min(1.0, armor_rating / 10.0)
        final_effectiveness = effectiveness * rating_multiplier

        # Cap at 95% damage reduction to prevent invulnerability
        return min(0.95, final_effectiveness)

    def _degrade_armor(self, armor_item, damage_absorbed):
        """
        Degrade armor durability based on damage absorbed.

        Args:
            armor_item: The armor item that absorbed damage
            damage_absorbed (int): Amount of damage the armor absorbed
        """
        if not hasattr(armor_item, 'armor_durability'):
            # Initialize durability if not set
            max_durability = getattr(armor_item, 'armor_rating', 5) * 20
            armor_item.armor_durability = max_durability
            armor_item.max_armor_durability = max_durability

        # Reduce durability
        armor_item.armor_durability = max(
            0, armor_item.armor_durability - damage_absorbed
        )

        # Calculate current effectiveness
        durability_percent = (
            armor_item.armor_durability / armor_item.max_armor_durability
        )
        original_rating = getattr(
            armor_item, 'base_armor_rating', armor_item.armor_rating
        )

        # Degrade armor rating based on durability
        armor_item.armor_rating = max(1, int(original_rating * durability_percent))

        # Store original rating if not already stored
        if not hasattr(armor_item, 'base_armor_rating'):
            armor_item.base_armor_rating = original_rating
