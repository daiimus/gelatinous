"""
Armor inspection and management commands.

Commands for checking armor condition, effectiveness, and coverage.
"""

from evennia import Command
from random import randint
from world.utils.boxtable import BoxTable, get_terminal_width
from world.combat.constants import (
    COLOR_SUCCESS,
    COLOR_NORMAL,
    COVERAGE_INHERITANCE,
    ARMOR_EFFECTIVENESS_MATRIX,
)
from world.identity_utils import msg_room_identity


def _get_center_headers(caller):
    """
    Get whether to center armor display headers.

    Args:
        caller: The character checking armor.

    Returns:
        bool: True if headers should be centered (default), False otherwise.
    """
    pref = caller.db.center_armor_headers
    return pref if pref is not None else True


def plate_layers_at(carrier, location):
    """The plate slots that cover *location* on this carrier, as
    ``[(slot, plate_or_None), ...]`` in declared slot order, read from the
    carrier's ``plate_slot_coverage`` -- the same declaration combat reads
    (#3366). Two slots covering one location (the side slots share the
    abdomen) means a hit there meets ONE of them, so the display lists
    them as alternatives and never sums them.
    """
    coverage = carrier.plate_slot_coverage or {}
    installed = carrier.installed_plates or {}
    slots = [s for s in (carrier.plate_slots or []) if location in (coverage.get(s) or [])]
    return [(s, installed.get(s)) for s in slots]


def describe_plate_layers(layers):
    """One bracket for the coverage rows: ``front: standard plate (7)``, or
    ``one of left side: standard plate (7) | right side: empty``."""
    parts = []
    for slot, plate in layers:
        label = slot.replace("_", " ")
        parts.append(f"{label}: {plate.key} ({plate.armor_rating})" if plate else f"{label}: empty")
    if len(parts) > 1:
        return "one of " + " | ".join(parts)
    return parts[0] if parts else ""





class CmdArmor(Command):
    """
    Inspect worn armor condition and coverage.

    Usage:
        armor                    - List all worn armor
        armor <item>            - Detailed info on specific armor piece
        armor coverage          - Show body coverage map
        armor effectiveness     - Show armor vs damage type matrix
        armor comprehensive     - Show detailed layered view by body location

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
        elif args.lower() == "comprehensive":
            # Show comprehensive layered view
            self._show_comprehensive_view(caller)
        else:
            # Show specific item details
            self._show_item_details(caller, args, worn_armor)

    def _get_worn_armor(self, character):
        """Get all worn items that have armor properties."""
        armor_items = []
        seen_items = set()  # Track items we've already added

        if not character.worn_items:
            return armor_items

        for location, items in character.worn_items.items():
            for item in items:
                # Only add each unique item once
                if item.id not in seen_items and item.armor_rating > 0:
                    armor_items.append(item)
                    seen_items.add(item.id)

        return armor_items

    def _list_armor(self, caller, worn_armor):
        """List all worn armor with basic stats."""
        if not worn_armor:
            caller.msg("You are not wearing any armor.")
            return

        center_headers = _get_center_headers(caller)

        # Create armor status table with box-drawing characters
        table = BoxTable("Item", "Type", "Rating", "Durability", "Coverage")

        for armor in worn_armor:
            # Get armor stats
            armor_type = armor.armor_type or "generic"

            # Calculate rating (handle plate carriers specially)
            if armor.is_plate_carrier:
                # The carrier's own rating; the plates a hit meets are per
                # location and listed by `armor coverage` (#3366).
                plates = sum(1 for p in (armor.installed_plates or {}).values() if p)
                # no "+": BoxTable redraws a plus as a box junction
                rating_display = f"{armor.armor_rating}/10" + (f" ({plates} plate{'s' if plates != 1 else ''})" if plates else "")
            else:
                rating_display = f"{armor.armor_rating}/10"

            durability = armor.armor_durability
            max_durability = armor.max_armor_durability

            # Get coverage
            coverage = armor.get_current_coverage()
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
                bar = (
                    bar_color
                    + "▓" * filled
                    + "░" * (bar_length - filled)
                    + "|n"
                )
                durability_str = f"{bar} {durability}/{max_durability}"
            else:
                durability_str = "N/A"

            table.add_row(
                armor.key,
                armor_type.title(),
                rating_display,
                durability_str,
                coverage_str,
            )

        # Add centered header using BoxTable's built-in functionality
        table.add_header("ARMOR STATUS", center=center_headers)

        # Center the entire table on screen if caller has a session
        sessions = caller.sessions.all()
        if sessions:
            centered_output = table.center_on_screen(session=sessions[0])
            caller.msg(f"\n{centered_output}")
        else:
            caller.msg(f"\n{table}")

    def _show_coverage_map(self, caller, worn_armor):
        """Show which body locations are protected by armor."""
        if not worn_armor:
            caller.msg("You are not wearing any armor.")
            return

        # Helper function to check if armor covers a location (with inheritance)
        def armor_covers_location(armor_coverage, target_location):
            """Check if armor coverage list covers target location,
            including inherited coverage."""
            if target_location in armor_coverage:
                return True

            # Check if any parent location in armor coverage covers this target
            for parent_loc in armor_coverage:
                children = COVERAGE_INHERITANCE.get(parent_loc, [])
                if target_location in children:
                    return True

            return False

        # Build coverage map - stores list of armor pieces per location
        coverage_map = {}

        # Get all possible body locations from character — species-
        # aware per #356 follow-up so non-human anatomies (rats with
        # forelegs/hindlegs/tail, etc.) iterate their own location set
        # instead of the humanoid default.
        from world.anatomy import get_species_anatomical_display_order
        species_order = get_species_anatomical_display_order(
            getattr(caller.db, "species", None)
        )
        if caller.longdesc:
            all_locations = [
                loc for loc in species_order if loc in caller.longdesc
            ]
        else:
            all_locations = species_order

        for armor in worn_armor:
            coverage = armor.get_current_coverage()

            # For plate carriers, calculate location-specific ratings
            if armor.is_plate_carrier:
                # Check each possible body location
                for location in all_locations:
                    # Skip if armor doesn't cover this location (with inheritance)
                    if not armor_covers_location(coverage, location):
                        continue

                    if location not in coverage_map:
                        coverage_map[location] = []

                    # The layers a hit here meets: the carrier, then the
                    # plate of the slot the hit lands on, in full (#3366).
                    location_rating = armor.armor_rating
                    detail = describe_plate_layers(plate_layers_at(armor, location))
                    armor_desc = armor.key + (f" [{detail}]" if detail else "")

                    coverage_map[location].append(
                        {
                            "armor": armor,
                            "description": armor_desc,
                            "rating": location_rating,
                            "type": armor.armor_type or "generic",
                        }
                    )
            else:
                # Regular armor uses standard rating for all covered locations
                rating = armor.armor_rating

                # Check each possible body location
                for location in all_locations:
                    # Skip if armor doesn't cover this location (with inheritance)
                    if not armor_covers_location(coverage, location):
                        continue

                    if location not in coverage_map:
                        coverage_map[location] = []

                    coverage_map[location].append(
                        {
                            "armor": armor,
                            "description": armor.key,
                            "rating": rating,
                            "type": armor.armor_type or "generic",
                        }
                    )

        center_headers = _get_center_headers(caller)

        # Create coverage table with box-drawing characters
        table = BoxTable("Body Location", "Protected By", "Type", "Rating")

        # Use the all_locations list we already built above
        for location in all_locations:
            if location in coverage_map:
                armor_list = coverage_map[location]
                # Sort by rating, highest first
                armor_list.sort(key=lambda x: x["rating"], reverse=True)

                # Add each armor piece as a row
                for i, armor_info in enumerate(armor_list):
                    location_name = (
                        location.replace("_", " ").title() if i == 0 else ""
                    )
                    table.add_row(
                        location_name,
                        armor_info["description"],
                        armor_info["type"].title(),
                        f"{armor_info['rating']}/10",
                    )
            else:
                table.add_row(
                    location.replace("_", " ").title(),
                    "|rUnprotected|n",
                    "-",
                    "0/10",
                )

        # Add centered header
        table.add_header("ARMOR COVERAGE MAP", center=center_headers)

        # Center the table on screen
        sessions = caller.sessions.all()
        session = sessions[0] if sessions else None
        centered_table = table.center_on_screen(session=session)

        caller.msg(f"\n{centered_table}")

    def _show_effectiveness_matrix(self, caller):
        """Show armor effectiveness vs damage types."""
        center_headers = _get_center_headers(caller)

        # Convert to percentage display format
        effectiveness_display = {}
        for armor_type, damage_types in ARMOR_EFFECTIVENESS_MATRIX.items():
            if armor_type == "generic":
                continue  # Skip generic in display
            effectiveness_display[armor_type] = {
                damage_type: f"{int(effectiveness * 100)}%"
                for damage_type, effectiveness in damage_types.items()
            }

        # Create effectiveness matrix table with box-drawing characters
        table = BoxTable(
            "Armor Type", "Bullet", "Stab", "Cut", "Blunt", "Laceration", "Burn"
        )

        # Every row the matrix carries, bar the `generic` fallback skipped
        # above. Not a literal list: that went stale the moment a material
        # was added, and `synthetic` never printed (#3440).
        for armor_key, effectiveness in effectiveness_display.items():
            table.add_row(
                armor_key.title(),
                effectiveness.get("bullet", "N/A"),
                effectiveness.get("stab", "N/A"),
                effectiveness.get("cut", "N/A"),
                effectiveness.get("blunt", "N/A"),
                effectiveness.get("laceration", "N/A"),
                effectiveness.get("burn", "N/A"),
            )

        # Add centered header
        table.add_header("ARMOR EFFECTIVENESS MATRIX", center=center_headers)

        # Center the table on screen
        sessions = caller.sessions.all()
        session = sessions[0] if sessions else None
        centered_table = table.center_on_screen(session=session)

        caller.msg(f"\n{centered_table}")
        caller.msg(
            "\n|xNote: Final effectiveness = Base % × (Armor Rating / 10)|n"
        )

    def _show_item_details(self, caller, item_name, worn_armor):
        """Show detailed information about a specific armor piece."""
        # Find the armor item
        target_armor = None
        for armor in worn_armor:
            armor_aliases = armor.aliases.all()
            if item_name.lower() in armor.key.lower() or item_name.lower() in [
                alias.lower() for alias in armor_aliases
            ]:
                target_armor = armor
                break

        if not target_armor:
            caller.msg(f"You are not wearing any armor matching '{item_name}'.")
            return

        # Get all armor stats
        armor_type = target_armor.armor_type or "generic"
        rating = target_armor.armor_rating
        base_rating = target_armor.base_armor_rating or rating
        durability = target_armor.armor_durability
        max_durability = target_armor.max_armor_durability
        material = target_armor.material or "unknown"

        # Get coverage
        coverage = target_armor.get_current_coverage()

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
        caller.msg(f"|xDescription:|n {target_armor.db.desc or ''}")
        caller.msg(f"\n|xArmor Statistics:|n")
        caller.msg(f"  Type: {armor_type.title()}")
        caller.msg(f"  Material: {material.title()}")
        caller.msg(f"  Current Rating: {rating}/10")
        if degradation > 0:
            caller.msg(
                f"  |rDegradation: -{degradation} from original {base_rating}/10|n"
            )
        caller.msg(
            f"  Condition: {condition} ({durability}/{max_durability})"
        )
        caller.msg(f"\n|xProtected Locations:|n")
        caller.msg(
            f"  {', '.join([loc.replace('_', ' ').title() for loc in coverage])}"
        )

    def _show_comprehensive_view(self, caller):
        """Show detailed layered view of all worn items by body location
        with interconnected boxes."""
        center_headers = _get_center_headers(caller)

        # Roman numeral conversion
        def to_roman(num):
            """Convert number to Roman numerals."""
            if num <= 0:
                return "0"
            val = [10, 9, 5, 4, 1]
            syms = ["X", "IX", "V", "IV", "I"]
            roman_num = ""
            i = 0
            while num > 0:
                for _ in range(num // val[i]):
                    roman_num += syms[i]
                    num -= val[i]
                i += 1
            return roman_num

        # Get all worn items organized by location
        worn_by_location = {}
        if caller.worn_items:
            worn_by_location = dict(caller.worn_items)

        # Get character's valid locations from longdesc — species-
        # aware per #356 follow-up.
        from world.anatomy import get_species_anatomical_display_order
        species_order = get_species_anatomical_display_order(
            getattr(caller.db, "species", None)
        )
        if caller.longdesc:
            # longdesc is a dict of {location: description}, check the keys
            valid_locations = [
                loc for loc in species_order if loc in caller.longdesc
            ]
        else:
            valid_locations = species_order

        # Fixed widths for consistent box sizes
        LOCATION_BOX_WIDTH = 15
        RATING_WIDTH = 8  # Width reserved for rating display
        NULL_CHAR = "∅"  # Null character for zero/missing ratings

        # FIRST PASS: Collect all item entries to determine max equipment name length
        all_item_entries = []
        locations_to_display = []

        for location in valid_locations:
            items_here = worn_by_location.get(location, [])
            items_sorted = sorted(
                items_here, key=lambda x: x.layer
            )

            # Skip locations with no items
            if not items_sorted:
                continue

            location_display = location.replace("_", " ").title()
            item_entries = []

            for item in items_sorted:
                armor_type = item.armor_type or "generic"
                armor_rating = item.armor_rating

                # Handle plate carriers specially
                if item.is_plate_carrier:
                    item_entries.append(
                        {
                            "name": item.key,
                            "rating": 0,  # Will be set per-location below
                            "type": armor_type,
                            "is_carrier": True,
                        }
                    )

                    # Calculate location-specific rating and get affecting plates
                    # The carrier's own rating, then each slot that covers
                    # this location as a sub-row; two slots on one location
                    # are alternatives a hit lands on, not a sum (#3366).
                    item_entries[-1]["rating"] = item.armor_rating
                    layers = plate_layers_at(item, location)
                    one_of = " (one of)" if len(layers) > 1 else ""
                    for slot, plate in layers:
                        label = slot.replace("_", " ")
                        item_entries.append(
                            {
                                "name": f"  └─ {label}: {plate.key if plate else 'empty'}{one_of}",
                                "rating": plate.armor_rating if plate else 0,
                                "type": (plate.armor_type or "generic") if plate else "-",
                                "is_plate": True,
                            }
                        )
                else:
                    item_entries.append(
                        {
                            "name": item.key,
                            "rating": armor_rating,
                            "type": armor_type,
                            "is_carrier": False,
                        }
                    )

            if item_entries:
                all_item_entries.extend(item_entries)
                locations_to_display.append(
                    {
                        "location": location,
                        "location_display": location_display,
                        "item_entries": item_entries,
                    }
                )

        # Calculate max equipment name length
        max_equip_name_len = max(
            (len(entry["name"]) for entry in all_item_entries), default=20
        )
        # Build output lines
        output_lines = []

        # Create header with proper alignment
        location_label = "Location"
        equipment_label = "EQUIPMENT"
        rating_label = "Rating"

        # Calculate actual column positions and widths
        # Box = 17 chars (╔ + 15 + ╗), stem = 7 chars ("──────" + " ")
        location_column_width = 17  # Width of the box including borders
        stem_width = 7  # "──────" (6) + " " (1)
        equipment_column_width = max_equip_name_len

        # Position labels to align with actual visual centers
        loc_label_padding_left = (
            location_column_width - len(location_label)
        ) // 2
        loc_label_padding_right = (
            location_column_width
            - len(location_label)
            - loc_label_padding_left
        )

        equip_label_padding_left = (
            equipment_column_width - len(equipment_label)
        ) // 2
        equip_label_padding_right = (
            equipment_column_width
            - len(equipment_label)
            - equip_label_padding_left
        )

        rating_label_padding_left = 2 + RATING_WIDTH - 1 - 2

        # Build header line
        header_parts = []
        header_parts.append(
            " " * loc_label_padding_left
            + location_label
            + " " * loc_label_padding_right
        )
        header_parts.append(" " * stem_width)  # Space for stem
        header_parts.append(
            " " * equip_label_padding_left
            + equipment_label
            + " " * equip_label_padding_right
        )
        header_parts.append(" " * rating_label_padding_left + rating_label)
        header_line = "".join(header_parts)

        if center_headers:
            sessions = caller.sessions.all()
            session = sessions[0] if sessions else None
            screen_width = get_terminal_width(session)
            header_width = len(header_line)
            padding = (screen_width - header_width) // 2
            header_line = " " * padding + header_line
            # Store padding for use on data lines
            line_padding = " " * padding
        else:
            line_padding = ""

        output_lines.append(header_line)
        output_lines.append("")  # Blank line after header

        # SECOND PASS: Build display with padded equipment names
        for loc_data in locations_to_display:
            location_display = loc_data["location_display"]
            item_entries = loc_data["item_entries"]

            # Create the location box (left side) with centered text
            loc_padding_left = (
                LOCATION_BOX_WIDTH - len(location_display)
            ) // 2
            loc_padding_right = (
                LOCATION_BOX_WIDTH
                - len(location_display)
                - loc_padding_left
            )
            loc_text = (
                " " * loc_padding_left
                + location_display
                + " " * loc_padding_right
            )

            loc_box_top = "╔" + "═" * LOCATION_BOX_WIDTH + "╗"
            loc_box_mid = "║" + loc_text + "║"
            loc_box_bot = "╚" + "═" * LOCATION_BOX_WIDTH + "╝"

            # Create the item lines (right side, tree structure - NO BOXES)
            if len(item_entries) == 1:
                # Single item - simple stem connection
                entry = item_entries[0]

                # Format item text with aligned rating (no "- " prefix)
                if entry["rating"] > 0:
                    rating_text = to_roman(entry["rating"])
                else:
                    rating_text = NULL_CHAR

                # Pad equipment name to max length, then add rating
                equip_name_padded = entry["name"].ljust(max_equip_name_len)
                item_text = (
                    f"{equip_name_padded}  {rating_text.rjust(RATING_WIDTH)}"
                )

                # Simple horizontal stem to item
                stem = "──────"

                output_lines.append(line_padding + loc_box_top)
                output_lines.append(
                    line_padding + loc_box_mid + stem + " " + item_text
                )
                output_lines.append(line_padding + loc_box_bot)

            else:
                # Multiple items - tree structure with branches
                blank_space = " " * (LOCATION_BOX_WIDTH + 2)

                # Find the last non-plate item for proper tree structure
                last_non_plate_idx = -1
                for i in range(len(item_entries) - 1, -1, -1):
                    if not item_entries[i].get("is_plate", False):
                        last_non_plate_idx = i
                        break

                for idx, entry in enumerate(item_entries):
                    is_first = idx == 0
                    # An item is "last" if it's the last non-plate item
                    is_last = idx == last_non_plate_idx

                    # Format item text with aligned rating
                    if entry["rating"] > 0:
                        rating_text = to_roman(entry["rating"])
                    else:
                        rating_text = NULL_CHAR

                    # Pad equipment name to max length, then add rating
                    equip_name_padded = entry["name"].ljust(
                        max_equip_name_len
                    )
                    item_text = f"{equip_name_padded}  {rating_text.rjust(RATING_WIDTH)}"

                    # Check if this is a plate (already has tree formatting)
                    is_plate = entry.get("is_plate", False)

                    if is_first:
                        # First item - show location box with stem and branch
                        output_lines.append(line_padding + loc_box_top)
                        output_lines.append(
                            line_padding
                            + loc_box_mid
                            + "──┬──"
                            + "  "
                            + item_text
                        )
                        output_lines.append(
                            line_padding + loc_box_bot + "  │"
                        )
                    elif is_plate:
                        # Plate sub-item - already has tree chars
                        output_lines.append(
                            line_padding
                            + blank_space
                            + "       "
                            + item_text
                        )
                    elif is_last:
                        # Last item - final branch with └──
                        output_lines.append(
                            line_padding
                            + blank_space
                            + "  └──"
                            + "  "
                            + item_text
                        )
                    else:
                        # Middle item - branch with ├──
                        output_lines.append(
                            line_padding
                            + blank_space
                            + "  ├──"
                            + "  "
                            + item_text
                        )
                        # Only add continuation bar if next item is not a plate
                        if idx + 1 < len(item_entries) and not item_entries[
                            idx + 1
                        ].get("is_plate", False):
                            output_lines.append(
                                line_padding + blank_space + "  │"
                            )

            # Blank line after each location
            output_lines.append("")

        # Remove trailing blank line
        if output_lines and output_lines[-1] == "":
            output_lines.pop()

        # Send to player
        caller.msg("\n".join(output_lines))


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
            caller.msg(
                "Repair what? Usage: repair <armor> [with <tool>]"
                " or repair <armor> [field/full]"
            )
            return

        # Breachable infrastructure shares the verb (a mast is repaired,
        # not worn) — that branch claims the command only when something
        # breachable in the room matches; armor flow is untouched.
        from commands.CmdBreach import try_repair_structure
        if try_repair_structure(caller, self.args.strip()):
            return

        armor_name, repair_type, tool_name = self.parse_repair_args(args)
        if not armor_name:
            caller.msg(
                "Repair what? Usage: repair <armor> [with <tool>]"
                " or repair <armor> [field/full]"
            )
            return

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

    @staticmethod
    def parse_repair_args(args):
        """``["plate", "carrier", "full"]`` -> ``("plate carrier", "full", None)``.

        Read from the END, not from ``args[1]`` (#2521). The modifier
        used to be looked for at ``args[1]`` only, and every piece of
        armour the game ships has a MULTI-WORD name — "plate carrier",
        "ceramic trauma plates", "black leather combat boots". So
        ``args[1]`` was the second word of the armour NAME:

        * ``repair plate carrier full`` silently degraded to a standard
          repair — 25% restoration instead of 60%, with no hint that
          "full" had been dropped.
        * ``repair plate carrier with sewing kit`` never set
          ``tool_name``, so the tool bonus of up to +12 went unapplied —
          and on failure the player was told *"perhaps you need better
          tools"* while holding the right one.

        ``armor_name`` also used to be ``args[0]``, so the lookup was
        partial-matching a single token while the rest of the phrase was
        being mined for a modifier that was not there.

        Returns ``(armor_name, repair_type, tool_name)``.
        """
        parts = list(args)
        repair_type = "standard"  # standard, field, or full
        tool_name = None

        # "... with <tool>" — after the LAST "with", so an armour named
        # "vest with straps" survives.
        lowered = [w.lower() for w in parts]
        if "with" in lowered:
            idx = len(lowered) - 1 - lowered[::-1].index("with")
            if idx + 1 < len(parts):
                tool_name = " ".join(parts[idx + 1:])
                parts = parts[:idx]

        # A TRAILING "field"/"full" is the repair type, so a "field
        # jacket" keeps its name.
        if parts and parts[-1].lower() in ("field", "full"):
            repair_type = parts[-1].lower()
            parts = parts[:-1]

        return " ".join(parts).strip(), repair_type, tool_name

    def _find_repairable_armor(self, caller, armor_name):
        """Find armor item that can be repaired."""
        # Check worn armor first
        if caller.worn_items:
            for location, items in caller.worn_items.items():
                for item in items:
                    item_aliases = item.aliases.all()
                    if item.armor_rating > 0 and (
                        armor_name.lower() in item.key.lower()
                        or armor_name.lower()
                        in [alias.lower() for alias in item_aliases]
                    ):
                        return item

        # Check inventory
        for item in caller.contents:
            item_aliases = item.aliases.all()
            if item.armor_rating > 0 and (
                armor_name.lower() in item.key.lower()
                or armor_name.lower()
                in [alias.lower() for alias in item_aliases]
            ):
                return item

        caller.msg(f"You don't have any armor matching '{armor_name}'.")
        return None

    def _find_repair_tool(self, caller, tool_name):
        """Find repair tool in inventory."""
        for item in caller.contents:
            item_aliases = item.aliases.all()
            if item.db.repair_tool_type is not None and (
                tool_name.lower() in item.key.lower()
                or tool_name.lower()
                in [alias.lower() for alias in item_aliases]
            ):
                return item

        caller.msg(f"You don't have a repair tool matching '{tool_name}'.")
        return None

    def _attempt_repair(self, caller, armor_item, repair_type, repair_tool):
        """Attempt to repair the armor based on type and tools."""
        # Check if armor needs repair
        current_durability = armor_item.armor_durability
        max_durability = armor_item.max_armor_durability

        if current_durability >= max_durability:
            caller.msg(
                f"The {armor_item.key} is already in perfect condition."
            )
            return

        # Check for full repair requirements
        if repair_type == "full" and not self._has_workshop_access(caller):
            caller.msg(
                "Full repairs require access to a proper workshop"
                " with an armor workbench."
            )
            return

        # Calculate repair parameters
        armor_type = armor_item.armor_type or "generic"
        repair_difficulty = self._get_repair_difficulty(armor_type, repair_type)
        tool_bonus = (
            self._get_tool_bonus(repair_tool, armor_type) if repair_tool else 0
        )

        # Get caller's technical skill (Intellect-based)
        from world.combat.utils import roll_stat

        skill_roll = roll_stat(caller, "intellect", 1)

        # Calculate success
        total_skill = skill_roll + tool_bonus
        success = total_skill >= repair_difficulty

        # Determine repair amount based on success margin
        if success:
            success_margin = total_skill - repair_difficulty
            repair_amount = self._calculate_repair_amount(
                repair_type, success_margin, max_durability
            )

            # Apply repair
            new_durability = min(
                max_durability, current_durability + repair_amount
            )
            armor_item.armor_durability = new_durability

            # Recalculate armor rating based on new durability
            durability_percent = new_durability / max_durability
            base_rating = armor_item.base_armor_rating or armor_item.armor_rating
            armor_item.armor_rating = max(
                1, int(base_rating * durability_percent)
            )

            # Success messages
            self._send_repair_success_messages(
                caller, armor_item, repair_type, repair_amount, repair_tool
            )

            # Degrade tool if used
            if repair_tool:
                self._degrade_repair_tool(repair_tool)

        else:
            # Failure messages
            self._send_repair_failure_messages(
                caller, armor_item, repair_type, repair_tool
            )

            # Possible tool damage on critical failure
            if repair_tool and total_skill < repair_difficulty - 5:
                self._damage_repair_tool(repair_tool)

    def _get_repair_difficulty(self, armor_type, repair_type):
        """Get base difficulty for repairing this armor type."""
        base_difficulties = {
            "leather": 8,  # Easiest to repair
            "kevlar": 12,  # Moderate - requires understanding of ballistic fibers
            "steel": 15,  # Hard - requires metalworking
            "ceramic": 20,  # Very hard - specialized knowledge
            "generic": 10,
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

        tool_type = repair_tool.db.repair_tool_type or "generic_tools"

        # Tool effectiveness matrix
        tool_bonuses = {
            "sewing_kit": {
                "leather": 6,
                "kevlar": 3,
                "steel": 0,
                "ceramic": 0,
            },
            "metalwork_tools": {
                "leather": 2,
                "kevlar": 2,
                "steel": 8,
                "ceramic": 2,
            },
            "ballistic_repair_kit": {
                "leather": 2,
                "kevlar": 10,
                "steel": 1,
                "ceramic": 4,
            },
            "ceramic_repair_compound": {
                "leather": 0,
                "kevlar": 2,
                "steel": 1,
                "ceramic": 12,
            },
            "generic_tools": {
                "leather": 2,
                "kevlar": 2,
                "steel": 2,
                "ceramic": 2,
            },
        }

        return tool_bonuses.get(tool_type, tool_bonuses["generic_tools"]).get(
            armor_type, 2
        )

    def _calculate_repair_amount(
        self, repair_type, success_margin, max_durability
    ):
        """Calculate how much durability to restore."""
        base_repair = {
            "field": max_durability * 0.15,  # 15% restoration (temporary)
            "standard": max_durability * 0.25,  # 25% restoration
            "full": max_durability * 0.60,  # 60% restoration (workshop repair)
        }

        # Add bonus for exceptional success
        bonus_multiplier = 1.0 + (
            success_margin * 0.05
        )  # 5% per point over difficulty

        return int(
            base_repair.get(repair_type, base_repair["standard"])
            * bonus_multiplier
        )

    def _send_repair_success_messages(
        self, caller, armor_item, repair_type, repair_amount, repair_tool
    ):
        """Send appropriate success messages."""
        tool_desc = (
            f" using the {repair_tool.key}"
            if repair_tool
            else " with improvised materials"
        )

        if repair_type == "field":
            caller.msg(
                f"|gYou patch up the {armor_item.key} with a quick field"
                f" repair{tool_desc}. It's not perfect, but it'll hold"
                " for now.|n"
            )
        elif repair_type == "full":
            caller.msg(
                f"|GYou meticulously restore the {armor_item.key}{tool_desc},"
                " bringing it as close to original condition as possible.|n"
            )
        else:
            caller.msg(
                f"|gYou successfully repair the {armor_item.key}{tool_desc},"
                " restoring some of its protective capability.|n"
            )

        # Show durability improvement
        current_durability = armor_item.armor_durability
        max_durability = armor_item.max_armor_durability
        durability_percent = int(
            (current_durability / max_durability) * 100
        )

        caller.msg(
            f"Durability improved by {repair_amount} points."
            f" Current condition: {durability_percent}%"
        )

        # Send to location
        if caller.location:
            from world.identity_utils import msg_room_identity
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} works on repairing {armor_item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )

    def _send_repair_failure_messages(
        self, caller, armor_item, repair_type, repair_tool
    ):
        """Send appropriate failure messages."""
        armor_type = armor_item.armor_type or "generic"

        failure_messages = {
            "leather": (
                "You struggle with the leather working techniques needed"
                f" for the {armor_item.key}."
            ),
            "kevlar": (
                f"The ballistic fibers of the {armor_item.key} prove too"
                " complex for your current skill level."
            ),
            "steel": (
                "You lack the metalworking expertise to properly repair"
                f" the {armor_item.key}."
            ),
            "ceramic": (
                f"The specialized ceramic compounds in the {armor_item.key}"
                " are beyond your technical knowledge."
            ),
            "generic": (
                "You're unable to figure out how to properly repair"
                f" the {armor_item.key}."
            ),
        }

        caller.msg(
            f"|r{failure_messages.get(armor_type, failure_messages['generic'])}|n"
        )

        if repair_tool:
            caller.msg(
                f"Even with the {repair_tool.key}, the repair proves"
                " too challenging."
            )
        else:
            caller.msg(
                "Perhaps you need better tools or more technical knowledge."
            )

    def _degrade_repair_tool(self, repair_tool):
        """Degrade tool durability from successful use."""
        if repair_tool.db.tool_durability is not None:
            repair_tool.db.tool_durability = max(
                0, repair_tool.db.tool_durability - 1
            )

            if repair_tool.db.tool_durability <= 0:
                repair_tool.location.msg_contents(
                    f"The {repair_tool.key} breaks from overuse"
                    " and crumbles to pieces."
                )
                repair_tool.delete()

    def _damage_repair_tool(self, repair_tool):
        """Damage tool from critical failure."""
        if repair_tool.db.tool_durability is not None:
            damage = randint(2, 5)
            repair_tool.db.tool_durability = max(
                0, repair_tool.db.tool_durability - damage
            )

            repair_tool.location.msg_contents(
                f"The {repair_tool.key} is damaged from the failed"
                " repair attempt!"
            )

            if repair_tool.db.tool_durability <= 0:
                repair_tool.location.msg_contents(
                    f"The {repair_tool.key} breaks completely"
                    " and is destroyed."
                )
                repair_tool.delete()

    def _has_workshop_access(self, caller):
        """Check if caller has access to a workshop for full repairs."""
        # Check current location for workshop tools
        if caller.location:
            for item in caller.location.contents:
                if item.db.repair_tool_type == "workshop_bench":
                    return True

        # Check caller's inventory for portable workshop tools
        for item in caller.contents:
            if item.db.workshop_tool:
                return True

        return False


PLATE_SLOT_NAMES = ("front", "back", "left_side", "right_side")


def parse_slot_args(words):
    """``["standard","plate","in","plate","carrier","front"]``
    -> ``("standard plate", "plate carrier", "front")``.

    Read from the END and split on the LAST ``in`` (#3365, the same shape
    as ``parse_repair_args`` / #2521). The old parser took ``args[0]`` as
    the plate and ``args[1]`` as the carrier, and every plate and carrier
    the game ships has a MULTI-WORD name -- "plate carrier", "standard
    plate", "trauma plate" -- so ``slot standard plate in plate carrier``
    parsed as plate="standard", carrier="plate", slot="in", and the
    command's own docstring example failed the same way.

    A trailing slot name (``front``/``back``/``left_side``/``right_side``,
    also written ``left side``) is peeled first, so a carrier keeps its
    whole name. Without an ``in``, returns ``(phrase, None, slot)`` and
    the caller decides how to split the phrase.

    Returns ``(plate_name, carrier_name_or_None, slot_or_None)``.
    """
    parts = list(words)
    lowered = [w.lower().replace("-", "_") for w in parts]
    slot = None
    if lowered and lowered[-1] in PLATE_SLOT_NAMES:
        slot = lowered[-1]; parts = parts[:-1]; lowered = lowered[:-1]
    elif len(lowered) >= 2 and lowered[-1] == "side" and lowered[-2] in ("left", "right"):
        slot = f"{lowered[-2]}_side"; parts = parts[:-2]; lowered = lowered[:-2]
    if "in" in lowered:
        idx = len(lowered) - 1 - lowered[::-1].index("in")
        return " ".join(parts[:idx]).strip(), " ".join(parts[idx + 1:]).strip(), slot
    return " ".join(parts).strip(), None, slot


def parse_unslot_args(words):
    """``["standard","plate","from","plate","carrier"]``
    -> ``("standard plate", "plate carrier")``; no ``from`` -> whole
    phrase is the plate (or slot) name and carrier is ``None`` (#3365).
    Splits on the LAST ``from`` so an item whose name contains the word
    survives. Returns ``(item_name, carrier_name_or_None)``.
    """
    parts = list(words)
    lowered = [w.lower() for w in parts]
    if "from" in lowered:
        idx = len(lowered) - 1 - lowered[::-1].index("from")
        return " ".join(parts[:idx]).strip(), " ".join(parts[idx + 1:]).strip()
    return " ".join(parts).strip(), None


def hand_holding(character, item):
    """The hand (canonical key) holding *item*, or None. The Mr. Hands
    ledger is the truth: an item loose in the pack is not held."""
    for hand, held in (character.hands or {}).items():
        if held == item:
            return hand
    return None


def free_hand(character):
    """A free hand (canonical key), or None. Severed hands are not in
    the view at all, so limb loss is felt here: one hand means one
    thing at a time, none means nothing."""
    for hand, held in (character.hands or {}).items():
        if held is None:
            return hand
    return None


def has_hands(character):
    """False when the hands view is empty: both severed, or a species
    with no grasping containers. A different refusal from "hands full"
    (the #2456 convention in CmdInventory): there is nothing to free."""
    return bool(dict(character.hands or {}))


def worn_by(character):
    """Everything on *character*'s body, as a set."""
    worn = set()
    for items in (character.worn_items or {}).values():
        worn.update(items or [])
    return worn


def pull_plate_into_hand(caller, plate, carrier, slot_name):
    """Take *plate* out of *slot_name* of *carrier* and into a free hand,
    or leave it where it is (#3463, the Mr. Hands rule: a plate comes
    out into a hand, and no free hand means it stays put). Returns True
    when the plate came out. Shared by every unslot door."""
    if not has_hands(caller):
        caller.msg(f"You have no hands to take the {plate.key} out with.")
        return False
    hand = free_hand(caller)
    if hand is None:
        caller.msg(f"Your hands are full. Free one to take the {plate.key} out.")
        return False
    installed_plates = carrier.installed_plates
    installed_plates[slot_name] = None
    carrier.installed_plates = installed_plates
    plate.move_to(caller, quiet=True)
    caller.wield_item(plate, hand=hand)
    caller.msg(
        f"You pull the {plate.key} out of the {slot_name}"
        f" slot of your {carrier.key} and hold it."
    )
    if caller.location:
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} pulls a plate out of their {carrier.key}.",
            char_refs={"actor": caller},
            exclude=[caller],
        )
    return True


class CmdSlot(Command):
    """
    Install armor plates into plate carriers.

    Usage:
        slot <plate> in <carrier> [<slot>]     - Install plate in carrier
        slot <plate> <carrier> [<slot>]        - Same, if the names are unambiguous
        slot list [<carrier>]                  - Show a carrier's plate slots
        slot                                   - List all your plate carriers

    Plates and carriers have multi-word names; write them out in full.
    Put 'in' between the plate and the carrier. Slots are front, back,
    left side and right side. If you name no slot, the best free one is
    chosen. You must be holding the plate to slot it; wield it first.

    Examples:
        slot standard plate in plate carrier
        slot trauma plate in plate carrier front
        slot lightweight plate in plate carrier left side
        slot list plate carrier
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
        elif args[0].lower() == "list":
            # "slot list" / "slot list <carrier words>" -- the carrier's
            # whole name, not its first word (#3365).
            carrier_name = " ".join(args[1:]).strip()
            if carrier_name:
                self._show_carrier_details(caller, carrier_name)
            else:
                self._list_plate_carriers(caller)
        else:
            self._parse_install_command(caller, args)

    def _parse_install_command(self, caller, args):
        """Parse the install syntaxes with multi-word names (#3365)."""
        plate_name, carrier_name, slot_name = parse_slot_args(args)

        if carrier_name is not None:
            # slot <plate words> in <carrier words> [<slot>]
            if not plate_name or not carrier_name:
                caller.msg(self._usage())
                return
            self._install_plate(caller, plate_name, carrier_name, slot_name)
            return

        # No "in": try every split of the phrase into <plate> <carrier>
        # and take the first where both halves resolve to the right kind
        # of object. Searches are quiet so a miss prints nothing.
        words = plate_name.split()
        for k in range(1, len(words)):
            left, right = " ".join(words[:k]), " ".join(words[k:])
            if self._resolves(caller, left, carrier=False) and self._resolves(caller, right, carrier=True):
                self._install_plate(caller, left, right, slot_name)
                return

        # Not an install. A bare carrier name shows that carrier.
        if slot_name is None and self._resolves(caller, plate_name, carrier=True):
            self._show_carrier_details(caller, plate_name)
            return

        caller.msg(self._usage())

    @staticmethod
    def _usage():
        return ("Usage: slot <plate> in <carrier> [<slot>]"
                " | slot list [<carrier>]"
                " -- write the full names, e.g. 'slot standard plate in plate carrier'")

    @staticmethod
    def _resolves(caller, name, carrier):
        """Does `name` quietly find exactly the kind of thing we want in inventory?"""
        if not name:
            return False
        found = caller.search(name, location=caller, quiet=True)
        if not found:
            return False
        obj = found[0] if isinstance(found, (list, tuple)) else found
        is_carrier = bool(getattr(obj, "plate_slots", None))
        return is_carrier if carrier else not is_carrier

    def _list_plate_carriers(self, caller):
        """List all available plate carriers and their configurations."""
        carriers = self._find_plate_carriers(caller)

        if not carriers:
            caller.msg("You don't have any plate carriers.")
            return

        caller.msg("|wYour Plate Carriers:|n")
        for carrier in carriers:
            carrier_name = carrier.key
            installed_plates = carrier.installed_plates
            plate_slots = carrier.plate_slots


            # Calculate total weight
            carrier_weight = carrier.weight
            plate_weight = sum(
                plate.weight
                for plate in installed_plates.values()
                if plate
            )
            total_weight = carrier_weight + plate_weight

            caller.msg(
                f"\n|c{carrier_name}|n (Base Protection: {carrier.armor_rating}/10,"
                f" Weight: {total_weight:.1f} lbs)"
            )

            for slot in plate_slots:
                if slot in installed_plates and installed_plates[slot]:
                    plate = installed_plates[slot]
                    plate_info = (
                        f"|g{plate.key}|n (Rating: {plate.armor_rating},"
                        f" Weight: {plate.weight:.1f} lbs)"
                    )
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
        caller.msg(f"|xDescription:|n {carrier.db.desc or ''}")

        # Configuration
        base_rating = carrier.armor_rating
        installed_plates = carrier.installed_plates
        plate_slots = carrier.plate_slots


        carrier_weight = carrier.weight
        plate_weight = sum(
            plate.weight
            for plate in installed_plates.values()
            if plate
        )
        total_weight = carrier_weight + plate_weight

        caller.msg(f"\n|xCarrier Statistics:|n")
        caller.msg(f"  Base Protection: {base_rating}/10")
        caller.msg(f"  Carrier Weight: {carrier_weight:.1f} lbs")
        caller.msg(f"  Plate Weight: {plate_weight:.1f} lbs")
        caller.msg(f"  Total Weight: {total_weight:.1f} lbs")

        caller.msg(f"\n|xPlate Configuration:|n")
        for slot in plate_slots:
            if slot in installed_plates and installed_plates[slot]:
                plate = installed_plates[slot]
                condition = self._get_condition_color(plate)
                caller.msg(f"  {slot.title()}: |g{plate.key}|n ({plate.armor_rating}/10) {condition}")
            else:
                caller.msg(f"  {slot.title()}: |r[Empty Slot]|n")

    def _install_plate(self, caller, plate_name, carrier_name, slot_name):
        """Install a plate in a carrier."""
        # Find the plate
        plate = self._find_plate_by_name(caller, plate_name)
        if not plate:
            return
        # In your HAND (#3463, owner: use the Mr. Hands system so limb
        # loss is meaningful). A plate loose in the pack is not being
        # handled; the move into the carrier releases the hand.
        if not has_hands(caller):
            caller.msg(f"You have no hands to slot the {plate.key} with.")
            return
        if hand_holding(caller, plate) is None:
            caller.msg(f"You need to be holding the {plate.key} to slot it.")
            return

        # Find the carrier
        carrier = self._find_carrier_by_name(caller, carrier_name)
        if not carrier:
            return

        # Validate carrier can accept plates
        if not carrier.is_plate_carrier:
            caller.msg(f"The {carrier.key} is not a plate carrier system.")
            return

        plate_slots = carrier.plate_slots
        if not plate_slots:
            caller.msg(f"The {carrier.key} doesn't have any plate slots.")
            return

        # Determine slot
        if slot_name:
            if slot_name.lower() not in [slot.lower() for slot in plate_slots]:
                caller.msg(
                    f"The {carrier.key} doesn't have a '{slot_name}' slot."
                )
                caller.msg(f"Available slots: {', '.join(plate_slots)}")
                return
            target_slot = slot_name.lower()
        else:
            # Auto-assign to first empty slot
            installed_plates = carrier.installed_plates
            empty_slots = [
                slot
                for slot in plate_slots
                if slot not in installed_plates or not installed_plates[slot]
            ]
            if not empty_slots:
                caller.msg(f"The {carrier.key} has no empty slots.")
                return
            target_slot = empty_slots[0]

        # Check if slot is already occupied
        installed_plates = carrier.installed_plates
        if target_slot in installed_plates and installed_plates[target_slot]:
            existing_plate = installed_plates[target_slot]
            caller.msg(
                f"The {target_slot} slot already contains"
                f" {existing_plate.key}."
            )
            caller.msg(
                f"Use 'unslot {existing_plate.key}"
                f" from {carrier.key}' first."
            )
            return

        # Validate plate compatibility
        if not plate.is_armor_plate:
            caller.msg(f"The {plate.key} is not an armor plate.")
            return

        # Install the plate
        carrier.installed_plates[target_slot] = plate

        # Move plate to carrier (it's now "installed", not carried separately)
        plate.move_to(carrier, quiet=True)

        # Success messages
        caller.msg(
            f"|gYou install the {plate.key} into the {target_slot} slot"
            f" of your {carrier.key}.|n"
        )


        # Location message
        if caller.location:
            msg_room_identity(
                location=caller.location,
                template=(
                    f"{{actor}} installs an armor plate into"
                    f" their {carrier.key}."
                ),
                char_refs={"actor": caller},
                exclude=[caller],
            )



    def _find_plate_carriers(self, caller):
        """Find all plate carriers (worn or carried)."""
        carriers = []

        # Check worn items
        if caller.worn_items:
            for location, items in caller.worn_items.items():
                for item in items:
                    if item.is_plate_carrier:
                        carriers.append(item)

        # Check inventory
        for item in caller.contents:
            if item.is_plate_carrier:
                carriers.append(item)

        return carriers

    def _find_carrier_by_name(self, caller, carrier_name):
        """Find a specific carrier by name."""
        # Use Evennia's search to handle numbered objects
        candidates = caller.search(
            carrier_name, location=caller, quiet=True
        )

        if not candidates:
            caller.msg(
                "You don't have a plate carrier matching"
                f" '{carrier_name}'."
            )
            return None

        # If multiple matches, return first one
        if isinstance(candidates, list):
            candidates = candidates[0]

        # Check if it's actually a plate carrier
        if not candidates.is_plate_carrier:
            caller.msg(f"The {candidates.key} is not a plate carrier.")
            return None

        return candidates

    def _find_plate_by_name(self, caller, plate_name):
        """Find an armor plate by name in inventory."""
        # Use Evennia's search to handle numbered objects
        candidates = caller.search(
            plate_name, location=caller, quiet=True
        )

        # If search failed, return None
        if not candidates:
            caller.msg(
                f"You don't have an armor plate matching '{plate_name}'."
            )
            return None

        # If multiple matches, return first one
        if isinstance(candidates, list):
            candidates = candidates[0]

        # Check if the found item is actually an armor plate
        if not candidates.is_armor_plate:
            caller.msg(f"The {candidates.key} is not an armor plate.")
            return None

        return candidates


    def _get_condition_color(self, item):
        """Get color-coded condition indicator."""
        durability = item.armor_durability
        max_durability = item.max_armor_durability

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
        unslot <plate>                      - Remove plate from a carrier you wear
        unslot <plate> from <carrier>       - Remove plate from a carrier you carry
        unslot <slot> from <carrier>        - Empty a specific slot

    Plates and carriers have multi-word names; write them out in full.
    Slots are front, back, left_side and right_side. On its own, unslot
    looks in the carriers you are wearing; name the carrier with 'from'
    to reach one you are carrying. The plate comes out into a free hand,
    so free one first.

    Examples:
        unslot standard plate
        unslot trauma plate from plate carrier
        unslot front from plate carrier
    """

    key = "unslot"
    aliases = []
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()

        if not args:
            caller.msg(
                "Usage: unslot <plate> [from <carrier>]"
                " | unslot <slot> from <carrier>"
            )
            return

        # Whole names, split on the LAST "from" (#3365). "unslot standard
        # plate" used to print usage because it had three tokens and the
        # second was not "from" -- there was no way to unslot a shipped
        # plate by its real name.
        item_name, carrier_name = parse_unslot_args(args)
        if not item_name:
            caller.msg(
                "Usage: unslot <plate> [from <carrier>]"
                " | unslot <slot> from <carrier>"
            )
            return
        if carrier_name is None:
            self._remove_plate_by_name(caller, item_name)
        elif carrier_name:
            self._remove_from_carrier(caller, item_name, carrier_name)
        else:
            caller.msg(
                "Usage: unslot <plate> [from <carrier>]"
                " | unslot <slot> from <carrier>"
            )

    def _remove_plate_by_name(self, caller, plate_name):
        """Remove a plate by name from any carrier the player is wearing."""
        all_worn = worn_by(caller)
        carriers = [item for item in caller.contents if item.is_plate_carrier]
        worn_carriers = [c for c in carriers if c in all_worn]
        carried_carriers = [c for c in carriers if c not in all_worn]

        # Two doors on purpose (#3463, owner ruling): `unslot <plate>`
        # alone means a carrier you are WEARING; a carrier in your pack
        # is reached by `unslot <plate> from <carrier>`.
        for carrier in worn_carriers:
            for slot_name, plate in carrier.installed_plates.items():
                if plate and plate_name.lower() in plate.key.lower():
                    pull_plate_into_hand(caller, plate, carrier, slot_name)
                    return
        for carrier in carried_carriers:
            for slot_name, plate in carrier.installed_plates.items():
                if plate and plate_name.lower() in plate.key.lower():
                    caller.msg(
                        f"The {plate.key} is in your {carrier.key}, which"
                        " you're carrying, not wearing. Use: unslot"
                        f" {plate.key} from {carrier.key}"
                    )
                    return

        if not worn_carriers:
            caller.msg("You are not wearing any plate carriers.")
            return
        caller.msg(
            f"You don't have any plate matching '{plate_name}'"
            " installed in the carriers you're wearing."
        )

    def _remove_from_carrier(self, caller, item_name, carrier_name):
        """Remove plate from specific carrier, by plate name or slot name."""
        # Find the carrier
        carrier = None
        for item in caller.contents:
            if (
                carrier_name.lower() in item.key.lower()
                and item.is_plate_carrier
            ):
                carrier = item
                break

        if not carrier:
            caller.msg(
                "You don't have a plate carrier matching"
                f" '{carrier_name}'."
            )
            return

        installed_plates = carrier.installed_plates

        # Try as slot name first
        if item_name.lower() in installed_plates:
            slot_name = item_name.lower()
            plate = installed_plates[slot_name]
            if plate:
                pull_plate_into_hand(caller, plate, carrier, slot_name)
                return
            else:
                caller.msg(f"The {slot_name} slot is already empty.")
                return

        # Try as plate name
        for slot_name, plate in installed_plates.items():
            if plate and item_name.lower() in plate.key.lower():
                pull_plate_into_hand(caller, plate, carrier, slot_name)
                return

        caller.msg(
            f"No plate or slot matching '{item_name}'"
            f" found in {carrier.key}."
        )
