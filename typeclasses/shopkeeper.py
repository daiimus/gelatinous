"""
Shop container and merchant typeclass for Gelatinous shop system.

This module contains the ShopContainer class for managing shop inventory
and the merchant character integration.
"""

from evennia import DefaultObject
from evennia.utils import logger
from evennia.utils.create import create_object
from evennia.prototypes.spawner import spawn
from world.shop.utils import get_prototype_value, format_currency, calculate_shop_price


class ShopContainer(DefaultObject):
    """
    A container that manages shop inventory using prototypes.
    
    Can operate in two modes:
    1. Infinite inventory: Spawns items from prototypes on demand
    2. Limited inventory: Tracks physical item quantities
    
    Attributes:
        db.prototype_inventory (dict): {prototype_key: price} for infinite mode
        db.item_inventory (dict): {prototype_key: quantity} for limited mode
        db.is_infinite (bool): Whether shop has unlimited stock
        db.markup_percent (int): Price markup percentage (default 0)
        db.shop_name (str): Display name for the shop
        db.container_type (str): "shelf", "rack", "counter", "crate", etc.
    """
    
    def at_object_creation(self):
        """Initialize shop container attributes."""
        self.db.prototype_inventory = {}
        self.db.item_inventory = {}
        self.db.is_infinite = True
        self.db.markup_percent = 0
        self.db.shop_name = "Shop"
        self.db.container_type = "shelf"
        
        # Purchase messages (support {buyer}, {item}, {price}, {shop} placeholders)
        self.db.purchase_msg_buyer = "You purchase {item} for {price}."
        self.db.purchase_msg_room = "{buyer} purchases {item} from {shop}."
        
        # Lock down the container
        self.locks.add("get:false()")  # Can't pick up the container itself
        
    def add_prototype(self, prototype_key, price=None, quantity=None):
        """
        Add a prototype to the shop inventory.
        
        Args:
            prototype_key (str): Key of the prototype to sell
            price (int, optional): Override price. If None, calculates from prototype value
            quantity (int, optional): For limited inventory. If None, uses infinite mode
            
        Returns:
            bool: True if added successfully
        """
        # Get prototype to validate it exists and extract base value
        from evennia.prototypes.prototypes import search_prototype
        prototype = search_prototype(prototype_key)
        
        if not prototype or len(prototype) == 0:
            logger.log_err(f"ShopContainer: Prototype '{prototype_key}' not found")
            return False
        
        prototype = prototype[0]  # search_prototype returns a list
        
        # Calculate price
        if price is None:
            base_value = get_prototype_value(prototype, "value", 10)
            price = calculate_shop_price(base_value, self.db.markup_percent)
        
        # Add to inventory
        self.db.prototype_inventory[prototype_key] = price
        
        if quantity is not None:
            self.db.is_infinite = False
            self.db.item_inventory[prototype_key] = quantity
        
        return True
    
    def remove_prototype(self, prototype_key):
        """
        Remove a prototype from shop inventory.
        
        Args:
            prototype_key (str): Key of prototype to remove
        """
        if prototype_key in self.db.prototype_inventory:
            del self.db.prototype_inventory[prototype_key]
        if prototype_key in self.db.item_inventory:
            del self.db.item_inventory[prototype_key]
    
    def get_price(self, prototype_key):
        """
        Get the price of an item by prototype key.
        
        Args:
            prototype_key (str): Prototype key
            
        Returns:
            int or None: Price in tokens, or None if not in inventory
        """
        return self.db.prototype_inventory.get(prototype_key)
    
    def is_in_stock(self, prototype_key):
        """
        Check if item is available for purchase.
        
        Args:
            prototype_key (str): Prototype key
            
        Returns:
            bool: True if item is available
        """
        if prototype_key not in self.db.prototype_inventory:
            return False
        
        if self.db.is_infinite:
            return True
        
        quantity = self.db.item_inventory.get(prototype_key, 0)
        return quantity > 0
    
    def purchase_item(self, buyer, prototype_key):
        """
        Process a purchase, spawning the item and handling inventory.
        
        Args:
            buyer: Character purchasing the item
            prototype_key (str): Key of prototype to purchase
            
        Returns:
            tuple: (success, item_or_error_msg)
                - (True, item_obj) on success
                - (False, error_message) on failure
        """
        # Check if item exists in shop
        if prototype_key not in self.db.prototype_inventory:
            return False, "That item isn't sold here."
        
        # Check stock for limited inventory
        if not self.is_in_stock(prototype_key):
            return False, "That item is out of stock."
        
        # Get price
        price = self.get_price(prototype_key)
        
        # Verify buyer has enough tokens (tokens AttributeProperty defaults to 0)
        if buyer.tokens < price:
            shortage = price - buyer.tokens
            return False, f"You need {format_currency(shortage)} more to afford that."
        
        # Spawn the item
        try:
            spawned = spawn(prototype_key)
            if not spawned or len(spawned) == 0:
                logger.log_err(f"ShopContainer: Failed to spawn '{prototype_key}'")
                return False, "The item couldn't be retrieved. Contact an admin."
            
            item = spawned[0]
            # Move item to buyer's inventory
            item.move_to(buyer, quiet=True)
        except Exception as e:
            logger.log_err(f"ShopContainer: Error spawning '{prototype_key}': {e}")
            return False, "Something went wrong. Contact an admin."
        
        # Deduct tokens
        buyer.tokens -= price
        
        # Update inventory for limited stock
        if not self.db.is_infinite:
            self.db.item_inventory[prototype_key] -= 1
        
        return True, item
    
    def get_display_name_for_prototype(self, prototype_key, prototype):
        """
        Get display name for a prototype without spawning objects.
        
        Args:
            prototype_key (str): The prototype key
            prototype (dict): The prototype definition
            
        Returns:
            str: Display name for the item
        """
        # Special handling for aerosol cans (spray/solvent)
        # Check if prototype has aerosol_contents attribute
        attrs = prototype.get("attrs", [])
        for attr in attrs:
            if isinstance(attr, tuple) and len(attr) >= 2:
                attr_name, attr_value = attr[0], attr[1]
                if attr_name == "aerosol_contents":
                    # Build name from contents: "can of spraypaint", "can of solvent"
                    return f"can of {attr_value}"
        
        # For most items, just use the key from prototype
        return prototype.get("key", prototype_key)
    
    def get_browse_display(self, viewer):
        """
        Generate formatted inventory display for browsing.
        
        Args:
            viewer: Character viewing the inventory
            
        Returns:
            str: Formatted inventory listing
        """
        if not self.db.prototype_inventory:
            return f"The {self.db.container_type} is empty."
        
        from evennia.prototypes.prototypes import search_prototype
        
        lines = []
        
        # Sort items by price
        items = sorted(self.db.prototype_inventory.items(), key=lambda x: x[1])
        
        # Build number-to-prototype mapping for purchase by number
        # Store as ndb (non-persistent) since it's regenerated on each look
        item_map = {}
        item_number = 1
        
        for prototype_key, price in items:
            # Skip out-of-stock items in limited inventory mode
            if not self.db.is_infinite:
                quantity = self.db.item_inventory.get(prototype_key, 0)
                if quantity <= 0:
                    continue
            
            # Get prototype for display info
            prototype = search_prototype(prototype_key)
            if not prototype:
                continue
            prototype = prototype[0]
            
            # Get display name efficiently
            item_name = self.get_display_name_for_prototype(prototype_key, prototype)
            
            # Add to item map
            item_map[item_number] = prototype_key
            
            # Format line with 3-digit number prefix
            lines.append(f"  [{item_number:03d}] {item_name:40s} {format_currency(price):>8s}")
            item_number += 1
        
        # If no items were added (all out of stock), show empty message
        if not item_map:
            return f"The {self.db.container_type} is empty."
        
        # Store the item map for use by buy command
        self.ndb.item_number_map = item_map
        
        # TODO: Reimplement when newbie flag system is added
        # Footer instruction for new players:
        # lines.append(f"\nUse |wbuy <item> from {self.key}|n to purchase.")
        
        return "\n".join(lines)
    
    def return_appearance(self, looker, **kwargs):
        """
        Override appearance to show shop inventory when looked at.
        
        Args:
            looker: Character looking at the container
            
        Returns:
            str: Description including inventory
        """
        # Get base description
        desc = self.db.desc or f"A {self.db.container_type} displaying items for sale."
        
        # Add inventory display
        inventory_display = self.get_browse_display(looker)
        
        return f"{desc}\n\n{inventory_display}"
