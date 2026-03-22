"""
Medical Item Management Commands

Commands for managing medical items using Evennia's built-in systems.
Note: For spawning items, use Evennia's built-in 'spawn' command:
  spawn BLOOD_BAG
  spawn PAINKILLER here
"""

from evennia import Command
from world.medical.utils import (
    is_medical_item, get_medical_item_info, can_be_used,
    get_medical_type,
)


class CmdListMedItems(Command):
    """
    List all medical items in your inventory with their status.
    
    Usage:
        medlist
        listmed
        
    Shows all medical items you're carrying, their remaining uses,
    and their current condition.
    """
    
    key = "medlist"
    aliases = ["listmed", "medinv"]
    help_category = "Medical"
    
    def func(self):
        """Execute the list medical items command."""
        caller = self.caller
        
        medical_items = [item for item in caller.contents 
                        if is_medical_item(item)]
        
        if not medical_items:
            caller.msg("You have no medical items in your inventory.")
            return
            
        caller.msg("Your medical items:")
        caller.msg("-" * 50)
        
        for item in medical_items:
            # Get item details
            uses_left = item.attributes.get("uses_left", "∞")
            max_uses = item.attributes.get("max_uses", "∞")
            medical_type = get_medical_type(item)
            stat_req = item.attributes.get("stat_requirement", 0)
            
            # Build status string
            status_parts = []
            if uses_left != "∞":
                status_parts.append(f"{uses_left}/{max_uses} uses")
            if stat_req > 0:
                status_parts.append(f"Int {stat_req} req")
            if not can_be_used(item):
                status_parts.append("EMPTY")
                
            status_str = f" ({', '.join(status_parts)})" if status_parts else ""
            
            caller.msg(f"  {item.get_display_name(caller)}{status_str}")
            caller.msg(f"    Type: {medical_type.replace('_', ' ').title()}")
            
            # Show item description
            desc = item.db.desc or "No description."
            caller.msg(f"    {desc[:60]}{'...' if len(desc) > 60 else ''}")
            caller.msg("")


class CmdMedItemInfo(Command):
    """
    Get detailed information about a medical item.
    
    Usage:
        medinfo <item>
        iteminfo <item>
        
    Shows detailed stats, effectiveness, and usage information
    for a medical item in your inventory.
    """
    
    key = "mediteminfo"
    aliases = ["iteminfo", "meddetail"]
    help_category = "Medical"
    
    def func(self):
        """Execute the medical item info command."""
        caller = self.caller
        
        if not self.args:
            caller.msg("Usage: mediteminfo <item>")
            return
            
        # Find the item
        item = caller.search(self.args, location=caller, quiet=True)
        if not item:
            caller.msg(f"You don't have '{self.args}'.")
            return
        elif len(item) > 1:
            caller.msg(f"Multiple items match '{self.args}'. Be more specific.")
            return
        item = item[0]
        
        # Check if it's a medical item
        if not is_medical_item(item):
            caller.msg(f"{item.get_display_name(caller)} is not a medical item.")
            return
            
        # Display detailed information using utility function
        info = get_medical_item_info(item, caller)
        caller.msg(info)


class CmdRefillMedItem(Command):
    """
    Refill a medical item to full uses (admin command).
    
    Usage:
        refillmed <item>
        
    Restores a medical item to maximum uses for testing.
    """
    
    key = "refillmed"
    aliases = ["medrefill", "refillmedical"]
    help_category = "Admin"
    locks = "cmd:perm(Admin)"
    
    def func(self):
        """Execute the refill medical item command."""
        caller = self.caller
        
        if not self.args:
            caller.msg("Usage: refillmed <item>")
            return
            
        # Find the item
        item = caller.search(self.args, location=caller, quiet=True)
        if not item:
            caller.msg(f"You don't have '{self.args}'.")
            return
        elif len(item) > 1:
            caller.msg(f"Multiple items match '{self.args}'. Be more specific.")
            return
        item = item[0]
        
        # Check if it's a medical item
        if not is_medical_item(item):
            caller.msg(f"{item.get_display_name(caller)} is not a medical item.")
            return
            
        # Refill the item
        uses_left = item.attributes.get("uses_left", 0)
        max_uses = item.attributes.get("max_uses", 1)
        
        if uses_left < max_uses:
            item.attributes.add("uses_left", max_uses)
            caller.msg(f"Refilled {item.get_display_name(caller)} from {uses_left} to {max_uses} uses.")
        else:
            caller.msg(f"{item.get_display_name(caller)} is already at maximum uses.")
