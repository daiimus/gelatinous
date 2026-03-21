"""
Shop commands for Gelatinous shop system.

Provides buy command for purchasing from shops.
"""

from evennia import Command
from evennia.utils import logger


class CmdBuy(Command):
    """
    Purchase an item from a shop container.
    
    Usage:
        buy <item> from <container>
        
    Examples:
        buy rusty sword from shelf
        buy stale bread from counter
        buy bandage from crate
        
    Purchases an item from a shop container by prototype key or item name.
    Deducts tokens from your account and gives you the spawned item.
    """
    
    key = "buy"
    aliases = ["purchase"]
    locks = "cmd:all()"
    help_category = "Shopping"
    
    def func(self):
        """Execute buy command"""
        caller = self.caller
        
        # Parse args: buy <item> from <container>
        if not self.args or " from " not in self.args:
            caller.msg("Usage: buy <item> from <container>")
            return
        
        # Split using rsplit to handle edge cases like "letter from mother from shelf"
        # rsplit with maxsplit=1 splits from the right, so only the last "from" is used
        try:
            item_name, container_name = self.args.rsplit(" from ", 1)
            item_name = item_name.strip()
            container_name = container_name.strip()
        except ValueError:
            caller.msg("Usage: buy <item> from <container>")
            return
        
        if not item_name or not container_name:
            caller.msg("Usage: buy <item> from <container>")
            return
        
        # Find the shop container
        container = caller.search(container_name, location=caller.location)
        if not container:
            return
        
        # Verify it's a ShopContainer
        from typeclasses.shopkeeper import ShopContainer
        if not isinstance(container, ShopContainer):
            caller.msg(f"{container.get_display_name(caller)} is not a shop container.")
            return
        
        # Try to find item by prototype key or name
        prototype_key = self._find_prototype_key(container, item_name)
        if not prototype_key:
            caller.msg(f"'{item_name}' is not available at {container.get_display_name(caller)}.")
            return
        
        # Attempt purchase
        success, result = container.purchase_item(caller, prototype_key)
        
        if not success:
            # result is error message
            caller.msg(result)
            return
        
        # result is the spawned item
        item = result
        
        # Get price for messaging
        price = container.get_price(prototype_key)
        from world.shop.utils import format_currency
        
        # Give item to buyer using proper hands integration
        self._give_item_to_buyer(caller, item)
        
        # Get custom messages from shop or use defaults
        msg_buyer = container.db.purchase_msg_buyer or "You purchase {item} for {price}."
        msg_room = container.db.purchase_msg_room or "{buyer} purchases {item} from {shop}."
        
        # Format messages with placeholders
        format_data = {
            "buyer": caller.get_display_name(caller),
            "item": item.get_display_name(caller),
            "price": format_currency(price),
            "shop": container.get_display_name(caller)
        }
        
        # Success messages
        caller.msg(msg_buyer.format(**format_data))
        caller.location.msg_contents(
            msg_room.format(**format_data),
            exclude=caller
        )
        
        # Optional: merchant transaction message if merchant present
        self._notify_merchant(caller, item, price, container)
    
    def _find_prototype_key(self, container, item_name):
        """
        Find prototype key by number, exact match, or fuzzy name match.
        
        Args:
            container: ShopContainer to search
            item_name: Name or number to search for (supports: "#2", "002", "2")
            
        Returns:
            str or None: Matching prototype key, or None if not found
        """
        from evennia.prototypes.prototypes import search_prototype
        
        # Check if item_name is a number (with or without # prefix)
        # Handle: "2", "002", "#2", "#002"
        search_term = item_name.lstrip('#').strip()
        if search_term.isdigit():
            item_number = int(search_term)
            # Check if container has item number mapping (from recent look)
            if hasattr(container.ndb, 'item_number_map') and container.ndb.item_number_map:
                prototype_key = container.ndb.item_number_map.get(item_number)
                if prototype_key:
                    return prototype_key
        
        # Get available prototypes
        available_keys = container.db.prototype_inventory.keys()
        
        # Try exact match on prototype key first
        if item_name in available_keys:
            return item_name
        
        # Try fuzzy match on display names (handles cans and other dynamic names)
        item_name_lower = item_name.lower()
        for proto_key in available_keys:
            # Get prototype to check its display name
            prototype = search_prototype(proto_key)
            if not prototype:
                continue
            prototype = prototype[0]
            
            # Use container's display name method to handle dynamic names
            display_name = container.get_display_name_for_prototype(proto_key, prototype).lower()
            
            # Match if search term is in display name or vice versa
            if item_name_lower in display_name or display_name in item_name_lower:
                return proto_key
        
        return None
    
    def _give_item_to_buyer(self, buyer, item):
        """
        Give purchased item to buyer, using wield if hands available.
        
        Args:
            buyer: Character who bought the item
            item: Item to give
        """
        # Item location is set to buyer in purchase_item
        # Try to wield in right hand first, then left
        hands = buyer.hands
        
        if hands.get('right') is None:
            # Right hand empty - wield there
            buyer.wield_item(item, hand='right')
        elif hands.get('left') is None:
            # Left hand empty - wield there
            buyer.wield_item(item, hand='left')
        # else: both hands full, item stays in inventory
    
    def _notify_merchant(self, buyer, item, price, container):
        """
        Send transaction message to merchant if present.
        
        Args:
            buyer: Character who made purchase
            item: Item purchased
            price: Price paid
            container: Shop container
        """
        # Check for merchant NPCs in the room
        for obj in buyer.location.contents:
            if hasattr(obj, 'db') and obj.db.is_merchant:
                # Found a merchant - send them a message
                from world.shop.utils import format_currency
                obj.msg(f"{buyer.get_display_name(obj)} purchases {item.get_display_name(obj)} for {format_currency(price)}.")
                break

