"""
Shop commands for Gelatinous shop system.

Provides buy command for purchasing from shops.
"""

from evennia import Command
from evennia.utils import logger
from world.identity_utils import msg_room_identity


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

        # Hand placement happens inside purchase_item (or the shop's own
        # override — bars/carts land items on the counter/board instead).

        # A keeper minding THIS counter serves the sale in person — the
        # self-service messages below are for unmanned shelves only.
        keeper = self._find_keeper(caller, container)
        if keeper:
            caller.msg(f"You pay {format_currency(price)}.")
            # The keeper's own gesture when they have one; else the job's.
            serve = getattr(keeper, "serve_purchase", None)
            if callable(serve):
                serve(caller, item, price)
            else:
                from world.shop.service import hand_over
                hand_over(keeper, caller, item, price)
            self._notify_merchant(caller, item, price, container)
            return

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
        # Per-observer broadcast: pre-interpolate non-character placeholders
        # (item/price/shop are rendered from caller's perspective for the
        # baked-in token; the {buyer} placeholder is resolved per observer).
        room_template = msg_room.format(
            buyer="{buyer}",
            item=item.get_display_name(caller),
            price=format_currency(price),
            shop=container.get_display_name(caller),
        )
        msg_room_identity(
            location=caller.location,
            template=room_template,
            char_refs={"buyer": caller},
            exclude=[caller],
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
        prototype_inventory = container.db.prototype_inventory
        if not prototype_inventory:
            return None
        available_keys = prototype_inventory.keys()
        
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
    
    def _find_keeper(self, buyer, container):
        """Whoever is minding this counter, if anyone — the on-duty keeper
        of the post, which is the same reading the till, the planner and
        the counter all use.

        This used to duck-type on `is_merchant` + `serve_purchase` +
        `_find_counter`, i.e. on the buyer's counterpart being a
        `Shopkeeper`. A generated successor is a plain `LLMNpc`, so a
        manned shop silently fell through to SELF-SERVICE while somebody
        stood right there (#2352)."""
        from world.souls.posts import keeper_on_duty
        try:
            keeper = keeper_on_duty(container)
        except Exception:  # noqa: BLE001 — an odd post can't break a sale
            return None
        if keeper is None or keeper.location is not buyer.location:
            return None
        return keeper

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
            if getattr(obj, 'is_merchant', False):
                from world.shop.utils import format_currency
                line = (f"{buyer.get_display_name(obj)} bought "
                        f"{item.get_display_name(obj)} off the shelf for "
                        f"{format_currency(price)}.")
                # An LLM keeper OBSERVES the self-serve sale (rides the
                # action buffer into their next turn); others get the
                # plain message as before.
                observe = getattr(obj, "_observe_action", None)
                if callable(observe) and getattr(obj.db, "llm_driven", False):
                    observe(buyer, line)
                else:
                    obj.msg(line)
                break

