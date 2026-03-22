"""
Clothing Mixin

Provides clothing/armor wearing, removal, layer conflict detection,
coverage queries, and the clothing coverage map builder for Character objects.

Extracted from typeclasses/characters.py in Phase 4 refactoring.
"""


class ClothingMixin:
    """
    Mixin class providing clothing and wearable-item management methods.

    Methods:
        wear_item: Wear a clothing item, handling layer conflicts and coverage.
        remove_item: Remove worn clothing, checking for blocking outer layers.
        is_item_worn: Check if a specific item is currently worn.
        get_worn_items: Get worn items, optionally filtered by location.
        is_location_covered: Check if a body location is covered by clothing.
        get_coverage_description: Get outermost clothing description for a location.
        _build_clothing_coverage_map: Map each body location to outermost item.

    Cross-cutting concerns:
        - Reads/writes ``self.worn_items`` (AttributeProperty on Character).
        - Reads ``self.hands`` (AttributeProperty on Character) during wear_item.
    """

    def wear_item(self, item):
        """
        Wear a clothing item, handling layer conflicts and coverage.

        Args:
            item: The item to wear.

        Returns:
            tuple: (success: bool, message: str)
        """
        # Validate item is wearable
        if not item.is_wearable():
            return False, "That item can't be worn."

        # Auto-unwield if currently held (move to inventory)
        hands = getattr(self, 'hands', {})
        for hand, held_item in hands.items():
            if held_item == item:
                hands[hand] = None
                item.move_to(self, quiet=True)  # Move to inventory
                self.hands = hands    # Save updated hands
                break

        # Validate item is in inventory (now that we've unwielded if needed)
        if item.location != self:
            return False, "You're not carrying that item."

        # Get item's current coverage (accounting for style states)
        item_coverage = item.get_current_coverage()
        item_layer = getattr(item, 'layer', 2)

        # Check for layer conflicts before wearing
        if not self.worn_items:
            self.worn_items = {}

        # Detect layer conflicts
        conflicts = []
        for location in item_coverage:
            if location in self.worn_items:
                for worn_item in self.worn_items[location]:
                    worn_layer = getattr(worn_item, 'layer', 2)

                    # CONFLICT 1: Trying to wear same layer at same location
                    if worn_layer == item_layer:
                        conflicts.append({
                            'type': 'same_layer',
                            'location': location,
                            'item': worn_item,
                            'message': (
                                f"You're already wearing {worn_item.key} on your "
                                f"{location.replace('_', ' ')} (both layer {item_layer})."
                            ),
                        })

                    # CONFLICT 2: Trying to wear inner layer over outer layer
                    elif item_layer < worn_layer:
                        conflicts.append({
                            'type': 'under_outer',
                            'location': location,
                            'item': worn_item,
                            'message': (
                                f"You can't wear {item.key} (layer {item_layer}) under "
                                f"{worn_item.key} (layer {worn_layer}) - remove the "
                                f"outer layer first."
                            ),
                        })

        # If conflicts found, report them concisely in natural language
        if conflicts:
            # Group conflicts by item (not by location) to reduce spam
            conflicts_by_item = {}
            for conflict in conflicts:
                conflicting_item = conflict['item']
                if conflicting_item not in conflicts_by_item:
                    conflicts_by_item[conflicting_item] = {
                        'type': conflict['type'],
                        'locations': [],
                        'layer': getattr(conflicting_item, 'layer', 2),
                    }
                conflicts_by_item[conflicting_item]['locations'].append(
                    conflict['location']
                )

            # Separate by conflict type
            same_layer_items = [
                k for k, v in conflicts_by_item.items() if v['type'] == 'same_layer'
            ]
            under_outer_items = [
                k for k, v in conflicts_by_item.items() if v['type'] == 'under_outer'
            ]

            # Build natural language error message with proper grammar
            if same_layer_items and under_outer_items:
                # Both types of conflicts
                if len(same_layer_items) == 1:
                    same_part = f"the {same_layer_items[0].key}"
                else:
                    same_names = [f"the {i.key}" for i in same_layer_items]
                    if len(same_names) == 2:
                        same_part = f"{same_names[0]} and {same_names[1]}"
                    else:
                        same_part = (
                            ", ".join(same_names[:-1]) + f", and {same_names[-1]}"
                        )

                if len(under_outer_items) == 1:
                    under_part = f"the {under_outer_items[0].key}"
                else:
                    under_names = [f"the {i.key}" for i in under_outer_items]
                    if len(under_names) == 2:
                        under_part = f"{under_names[0]} and {under_names[1]}"
                    else:
                        under_part = (
                            ", ".join(under_names[:-1]) + f", and {under_names[-1]}"
                        )

                error_msg = (
                    f"You cannot wear the {item.key} over {same_part}, and you "
                    f"would need to wear it under {under_part}."
                )
            elif same_layer_items:
                # Only same-layer conflicts
                if len(same_layer_items) == 1:
                    error_msg = (
                        f"You cannot wear the {item.key} over the "
                        f"{same_layer_items[0].key} you are already wearing."
                    )
                elif len(same_layer_items) == 2:
                    error_msg = (
                        f"You cannot wear the {item.key} over the "
                        f"{same_layer_items[0].key} and the "
                        f"{same_layer_items[1].key} you are already wearing."
                    )
                else:
                    names = [f"the {i.key}" for i in same_layer_items]
                    item_list = ", ".join(names[:-1]) + f", and {names[-1]}"
                    error_msg = (
                        f"You cannot wear the {item.key} over {item_list} "
                        f"you are already wearing."
                    )
            else:
                # Only under-outer conflicts
                if len(under_outer_items) == 1:
                    error_msg = (
                        f"You cannot wear the {item.key} under the "
                        f"{under_outer_items[0].key} - remove it first."
                    )
                elif len(under_outer_items) == 2:
                    error_msg = (
                        f"You cannot wear the {item.key} under the "
                        f"{under_outer_items[0].key} and the "
                        f"{under_outer_items[1].key} - remove them first."
                    )
                else:
                    names = [f"the {i.key}" for i in under_outer_items]
                    item_list = ", ".join(names[:-1]) + f", and {names[-1]}"
                    error_msg = (
                        f"You cannot wear the {item.key} under {item_list} "
                        f"- remove them first."
                    )

            return False, error_msg

        # No conflicts - proceed with wearing
        for location in item_coverage:
            if location not in self.worn_items:
                self.worn_items[location] = []

            # Add item to location, maintaining layer order (outer first)
            location_items = self.worn_items[location]

            # Find insertion point based on layer
            insert_index = 0
            for i, worn_item in enumerate(location_items):
                if item.layer <= worn_item.layer:
                    insert_index = i + 1
                else:
                    break

            location_items.insert(insert_index, item)

        return True, f"You put on {item.key}."

    def remove_item(self, item):
        """
        Remove worn clothing item, checking for outer layers blocking removal.

        Args:
            item: The item to remove.

        Returns:
            tuple: (success: bool, message: str)
        """
        # Validate item is worn
        if not self.is_item_worn(item):
            return False, "You're not wearing that item."

        # Check if any outer layers are blocking removal
        item_layer = getattr(item, 'layer', 2)
        item_coverage = getattr(
            item, 'get_current_coverage',
            lambda: getattr(item, 'coverage', []),
        )()

        blocking_items = []
        if self.worn_items:
            for location in item_coverage:
                if location in self.worn_items:
                    for worn_item in self.worn_items[location]:
                        if worn_item == item:
                            continue
                        worn_layer = getattr(worn_item, 'layer', 2)

                        # Outer layers (higher numbers) block removal of inner layers
                        if worn_layer > item_layer:
                            blocking_items.append({
                                'item': worn_item,
                                'location': location,
                                'layer': worn_layer,
                            })

        # If blocked, report it in natural language
        if blocking_items:
            # Get unique items (may block at multiple locations)
            unique_blockers = {}
            for block in blocking_items:
                blocker = block['item']
                if blocker not in unique_blockers:
                    unique_blockers[blocker] = {
                        'layer': block['layer'],
                        'locations': [],
                    }
                unique_blockers[blocker]['locations'].append(block['location'])

            # Natural language, single-sentence response
            if len(unique_blockers) == 1:
                blocker = list(unique_blockers.keys())[0]
                error_msg = f"Remove the {blocker.key} first."
            elif len(unique_blockers) == 2:
                blocker1, blocker2 = list(unique_blockers.keys())
                error_msg = (
                    f"Remove the {blocker1.key} and the {blocker2.key} first."
                )
            else:
                # 3+ blockers
                names = [f"the {b.key}" for b in unique_blockers.keys()]
                item_list = ", ".join(names[:-1]) + f", and {names[-1]}"
                error_msg = f"Remove {item_list} first."

            return False, error_msg

        # No blocking - proceed with removal
        if self.worn_items:
            for location, items in list(self.worn_items.items()):
                if item in items:
                    items.remove(item)
                    # Clean up empty lists
                    if not items:
                        del self.worn_items[location]

        return True, f"You remove {item.key}."

    def is_item_worn(self, item):
        """
        Check if a specific item is currently worn.

        Args:
            item: The item to check.

        Returns:
            bool: True if item is worn.
        """
        if not self.worn_items:
            return False

        for items in self.worn_items.values():
            if item in items:
                return True
        return False

    def get_worn_items(self, location=None):
        """
        Get worn items, optionally filtered by location.

        Args:
            location (str, optional): Body location to filter by.

        Returns:
            list: Worn items (deduplicated when no location filter).
        """
        if not self.worn_items:
            return []

        if location:
            return self.worn_items.get(location, [])

        # Return all worn items (deduplicated since items can cover multiple locations)
        seen_items = set()
        all_items = []
        for items in self.worn_items.values():
            for item in items:
                if item not in seen_items:
                    seen_items.add(item)
                    all_items.append(item)
        return all_items

    def is_location_covered(self, location):
        """
        Check if body location is covered by clothing.

        Args:
            location (str): Body location to check.

        Returns:
            bool: True if location is covered.
        """
        if not self.worn_items:
            return False

        return bool(self.worn_items.get(location, []))

    def get_coverage_description(self, location):
        """
        Get clothing description for covered location.

        Args:
            location (str): Body location to describe.

        Returns:
            str or None: Outermost item's worn description, or None.
        """
        if not self.worn_items or location not in self.worn_items:
            return None

        # Get outermost (first) item for this location
        items = self.worn_items[location]
        if not items:
            return None

        outermost_item = items[0]
        return outermost_item.get_current_worn_desc()

    def _build_clothing_coverage_map(self):
        """
        Map each body location to outermost covering clothing item.

        Returns:
            dict: Mapping of location str to outermost clothing item.
        """
        coverage = {}
        if not self.worn_items:
            return coverage

        for location, items in self.worn_items.items():
            if items:
                # First item is outermost due to layer ordering
                coverage[location] = items[0]

        return coverage
