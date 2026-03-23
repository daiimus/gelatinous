# Clothing System Commands
#
# Complete clothing management system including:
# - CmdWear/CmdRemove: Basic wear/remove functionality
# - CmdRollUp/CmdUnroll: Adjustable clothing features
# - CmdZip/CmdUnzip: Closure management
#
from evennia import Command

from world.combat.constants import (
    STYLE_ADJUSTABLE,
    STYLE_CLOSURE,
    STYLE_STATE_NORMAL,
    STYLE_STATE_ROLLED,
    STYLE_STATE_UNZIPPED,
    STYLE_STATE_ZIPPED,
)
from world.identity_utils import msg_room_identity

class CmdWear(Command):
    """
    Wear a clothing item from your inventory.

    Usage:
        wear <item>

    Examples:
        wear jacket
        wear leather boots
        wear 2nd shirt
    """

    key = "wear"
    aliases = []
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Wear what?")
            return
        
        # Find the item in inventory
        item = caller.search(self.args.strip(), location=caller, quiet=True)
        
        # If not found in inventory, check hands (wielded items)
        if not item:
            hands = getattr(caller, 'hands', {})
            for hand, held_item in hands.items():
                if held_item and held_item.key.lower() == self.args.strip().lower():
                    item = held_item
                    break
        
        if not item:
            caller.msg(f"You don't have '{self.args.strip()}'.")
            return
        
        # Use first match if multiple found
        if isinstance(item, list):
            item = item[0]
        
        # Check if item is wearable
        if not item.is_wearable():
            caller.msg(f"You can't wear {item.key}.")
            return
        
        # Check if already worn
        if caller.is_item_worn(item):
            caller.msg(f"You're already wearing {item.key}.")
            return
        
        # Attempt to wear the item
        success, message = caller.wear_item(item)
        caller.msg(message)
        
        if success:
            # Message to room
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} puts on {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )


class CmdRemove(Command):
    """
    Remove a worn clothing item.

    Usage:
        remove <item>
        unwear <item>
        remove all

    Examples:
        remove jacket
        unwear boots
        remove all
    """

    key = "remove"
    aliases = ["unwear"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Remove what?")
            return
        
        args = self.args.strip().lower()
        
        # Handle "remove all"
        if args == "all":
            worn_items = caller.get_worn_items()
            if not worn_items:
                caller.msg("You're not wearing anything.")
                return
            
            removed_items = []
            for item in worn_items:
                success, message = caller.remove_item(item)
                if success:
                    removed_items.append(item.key)
            
            if removed_items:
                caller.msg(f"You remove: {', '.join(removed_items)}")
                msg_room_identity(
                    location=caller.location,
                    template="{actor} removes several items.",
                    char_refs={"actor": caller},
                    exclude=[caller],
                )
            else:
                caller.msg("You couldn't remove anything.")
            return
        
        # Find worn item by name
        worn_items = caller.get_worn_items()
        item = None
        
        # Search through worn items
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # STICKY GRENADE WARNING - Check for stuck grenades before removal
        if item.db.stuck_grenade is not None:
            grenade = item.db.stuck_grenade
            
            # Get remaining countdown time if any
            remaining = getattr(grenade.ndb, 'countdown_remaining', 0)
            stuck_location = grenade.db.stuck_to_location if grenade.db.stuck_to_location is not None else 'unknown'
            
            # Send dramatic warning
            if remaining > 0:
                caller.msg(
                    f"\n|R╔══════════════════════════════════════╗|n\n"
                    f"|R║  ⚠️  CRITICAL WARNING  ⚠️           ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  LIVE {grenade.key.upper()} ATTACHED       ║|n\n"
                    f"|R║  COUNTDOWN: {remaining} SECONDS REMAINING   ║|n\n"
                    f"|R║  MAGNETICALLY CLAMPED AT {stuck_location.upper():^7}  ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  Removing this armor will NOT       ║|n\n"
                    f"|R║  break the magnetic bond!           ║|n\n"
                    f"|R║  Grenade stays stuck to armor!      ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  DROP ARMOR AND FLEE TO SURVIVE!    ║|n\n"
                    f"|R╚══════════════════════════════════════╝|n\n"
                )
            else:
                caller.msg(
                    f"\n|y*** WARNING ***|n\n"
                    f"A {grenade.key} is magnetically clamped to this {item.key}.\n"
                    f"Removing the armor will NOT break the magnetic bond.\n"
                    f"The grenade will remain stuck to the armor.\n"
                )
            
            # Warn the room
            msg_room_identity(
                location=caller.location,
                template=(
                    f"|R{{actor}} carefully removes their {item.key} - "
                    f"the magnetically attached {grenade.key} moves "
                    f"with it!|n"
                ),
                char_refs={"actor": caller},
                exclude=[caller],
            )
        
        # Remove the item
        success, message = caller.remove_item(item)
        caller.msg(message)
        
        if success:
            # Message to room (only if no grenade warning was sent)
            if item.db.stuck_grenade is None:
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} removes {item.key}.",
                    char_refs={"actor": caller},
                    exclude=[caller],
                )


class CmdRollUp(Command):
    """
    Roll up sleeves or similar adjustable clothing features.

    Usage:
        rollup <item>
        unroll <item>

    Examples:
        rollup shirt
        unroll sleeves
        rollup jacket
    """

    key = "rollup"
    aliases = ["unroll"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Roll up what?")
            return
        
        # Find worn item
        worn_items = caller.get_worn_items()
        item = None
        
        args = self.args.strip().lower()
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # Determine target state based on command
        if self.cmdstring.lower() == "rollup":
            target_state = STYLE_STATE_ROLLED
            action = "roll up"
        else:  # unroll
            target_state = STYLE_STATE_NORMAL
            action = "unroll"
        
        # Check if item supports adjustable property
        if STYLE_ADJUSTABLE not in item.style_configs:
            caller.msg(f"The {item.key} doesn't have anything to {action}.")
            return
        
        # Check if already in target state
        current_state = item.get_style_property(STYLE_ADJUSTABLE)
        if current_state == target_state:
            if target_state == STYLE_STATE_ROLLED:
                caller.msg(f"The {item.key} is already rolled up.")
            else:
                caller.msg(f"The {item.key} is already unrolled.")
            return
        
        # Check if transition is valid (has both coverage and desc changes)
        if not item.can_style_property_to(STYLE_ADJUSTABLE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Apply the style change
        success = item.set_style_property(STYLE_ADJUSTABLE, target_state)
        
        if success:
            if target_state == STYLE_STATE_ROLLED:
                caller.msg(f"You roll up the {item.key}.")
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} rolls up {item.key}.",
                    char_refs={"actor": caller},
                    exclude=[caller],
                )
            else:
                caller.msg(f"You unroll the {item.key}.")
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} unrolls {item.key}.",
                    char_refs={"actor": caller},
                    exclude=[caller],
                )
        else:
            caller.msg(f"You can't {action} the {item.key}.")


class CmdZip(Command):
    """
    Zip, unzip, button, or unbutton clothing items with closures.

    Usage:
        zip <item>
        unzip <item>
        button <item>
        unbutton <item>

    Examples:
        zip jacket
        unzip boots
        button shirt
        unbutton coat
        zip up coat
    """

    key = "zip"
    aliases = ["unzip", "button", "unbutton"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Zip what?")
            return
        
        # Find worn item
        worn_items = caller.get_worn_items()
        item = None
        
        args = self.args.strip().lower()
        # Handle "zip up" as just "zip"
        if args.startswith("up "):
            args = args[3:]
        
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # Determine target state based on command
        cmd = self.cmdstring.lower()
        if cmd in ["zip", "button"]:
            target_state = STYLE_STATE_ZIPPED
            action = "zip up" if cmd == "zip" else "button up"
            action_past = "zipped up" if cmd == "zip" else "buttoned up"
        else:  # unzip, unbutton
            target_state = STYLE_STATE_UNZIPPED
            action = "unzip" if cmd == "unzip" else "unbutton"
            action_past = "unzipped" if cmd == "unzip" else "unbuttoned"
        
        # Check if item supports closure property
        if STYLE_CLOSURE not in item.style_configs:
            if cmd in ["zip", "unzip"]:
                caller.msg(f"The {item.key} doesn't have a zipper.")
            else:  # button, unbutton
                caller.msg(f"The {item.key} doesn't have buttons.")
            return
        
        # Check if already in target state
        current_state = item.get_style_property(STYLE_CLOSURE)
        if current_state == target_state:
            if target_state == STYLE_STATE_ZIPPED:
                if cmd == "zip":
                    caller.msg(f"The {item.key} is already zipped up.")
                else:  # button
                    caller.msg(f"The {item.key} is already buttoned up.")
            else:  # UNZIPPED
                if cmd == "unzip":
                    caller.msg(f"The {item.key} is already unzipped.")
                else:  # unbutton
                    caller.msg(f"The {item.key} is already unbuttoned.")
            return
        
        # Check if transition is valid (has both coverage and desc changes)
        if not item.can_style_property_to(STYLE_CLOSURE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Apply the style change
        success = item.set_style_property(STYLE_CLOSURE, target_state)
        
        if success:
            caller.msg(f"You {action} the {item.key}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} {action_past} {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You can't {action} the {item.key}.")
