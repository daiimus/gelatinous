"""
Shop container and merchant typeclass for Gelatinous shop system.

This module contains the ShopContainer class for managing shop inventory
and the merchant character integration.
"""

from evennia import DefaultObject
from evennia.utils import logger
from evennia.utils.utils import delay

from typeclasses.characters import Character
from typeclasses.llm_npc import LLMNpcMixin
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
        # indexed lookup for the souls economy's tithe sweep (tags are
        # the fast path; a typeclass-path scan is not)
        self.tags.add("till", category="souls")
        
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
        # A counter bound to a post only sells while a keeper is minding
        # it — 24/7 venues staff shifts (souls posts), so the question is
        # "is ANYONE'S shift-holder standing here", not "is THE keeper".
        # An unstaffed slot reads as a tired counter, not a closed shop —
        # unless every slot is dark. Counters with no binding vend
        # freely: that IS the vending-machine tier.
        if self.db.post_slots or self.db.post_keeper is not None:
            from world.souls.posts import any_keeper_present
            if not any_keeper_present(self):
                return False, (self.db.post_closed_msg
                               or "Nobody's minding the counter. No coin "
                                  "changes hands here until somebody's "
                                  "back behind it.")

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
            # Into the buyer's FREE HAND when one exists (Mr. Hands — a
            # purchase is a handover, not a teleport); inventory fallback.
            item.move_to(buyer, quiet=True)
            try:
                hands = getattr(buyer, "hands", None) or {}
                free = next((h for h, held in hands.items() if held is None),
                            None)
                if free:
                    buyer.wield_item(item, free)
            except Exception:  # noqa: BLE001 — hand placement is best-effort
                pass
        except Exception as e:
            logger.log_err(f"ShopContainer: Error spawning '{prototype_key}': {e}")
            return False, "Something went wrong. Contact an admin."
        
        # Deduct tokens
        buyer.tokens -= price
        # ...and credit the shop's till when it keeps one — sale proceeds
        # must not vanish from the economy (the FoodCart lesson, promoted).
        if self.db.register is not None:
            self.db.register = int(self.db.register or 0) + int(price)
        
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



class Shopkeeper(LLMNpcMixin, Character):
    """An LLM-voiced shopkeeper whose SALES are deterministic code.

    The bartender/butcher split, third verse: a spoken order ("a pack of
    Noirs, please") resolves against the counter's REAL inventory and runs
    the counter's own purchase path — stock, tokens, till — with the item
    pressed into the buyer's hand; the model supplies voice and memory,
    never prices. Non-orders fall through to conversation."""

    def at_object_creation(self):
        super().at_object_creation()
        if not self.height:
            self.height = "average"
        if not self.build:
            self.build = "average"
        self.db.llm_driven = False
        self.db.is_npc = True
        self.is_merchant = True   # the buy command's notify hook finds us

    def _name_aliases(self):
        return ["shopkeeper", "shopkeep", "merchant", "clerk"]

    def _find_counter(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, ShopContainer):
                return obj
        return None

    # --- deterministic spoken orders ---------------------------------
    def _handle_directed_speech(self, speech, speaker, kwargs):
        from typeclasses.bar import GRATITUDE_TRIGGERS
        low = (speech or "").lower()
        if any(t in low for t in GRATITUDE_TRIGGERS):
            self._acknowledge()
            return True
        if kwargs.get("addressed"):
            delay(1.5, self._fulfil_shop_order, speech, speaker)
            return True
        if (self._match_shop_order(speech) is not None
                and self._classify_speech(speech, speaker) == "directed"):
            delay(1.5, self._fulfil_shop_order, speech, speaker)
            return True
        return False

    def _acknowledge(self):
        from random import choice
        from time import monotonic
        now = monotonic()
        if now - (self.ndb.last_ack or 0) < 6.0:
            return
        self.ndb.last_ack = now
        delay(1.0, self.execute_cmd, "emote " + choice((
            "tips two fingers off the counter in acknowledgement.",
            "gives a small nod, already re-facing the stock.",
            "waves it off with the practiced ease of a thousand thank-yous.",
        )))

    def _shelf(self):
        """The counter's real sellable list: [(proto_key, display, words)]."""
        import re
        from evennia.prototypes.prototypes import search_prototype
        counter = self._find_counter()
        if not counter:
            return []
        entries = []
        for proto_key in (counter.db.prototype_inventory or {}):
            protos = search_prototype(proto_key)
            if not protos:
                continue
            display = protos[0].get("key") or proto_key
            words = set(re.findall(r"[a-z']+", display.lower()))
            for alias in protos[0].get("aliases") or ():
                words.update(re.findall(r"[a-z']+", str(alias).lower()))
            entries.append((proto_key, display, words))
        return entries

    def _match_shop_order(self, speech):
        """Resolve speech to a shelf item — conservative (an order cue or a
        bare order; a cue-less question is conversation) with best-overlap
        scoring. Returns the prototype key, or the string "ambiguous" when
        two items tie (the keeper asks which)."""
        import re
        from typeclasses.bar import ORDER_CUES, ORDER_FILLER
        low = " ".join((speech or "").lower().split())
        if not low:
            return None
        words = re.findall(r"[a-z']+", low)
        has_cue = any(cue in low for cue in ORDER_CUES)
        if "?" in low and not has_cue:
            return None
        scored = []
        for proto_key, display, item_words in self._shelf():
            overlap = sum(1 for w in words
                          if w in item_words or w.rstrip("s") in item_words)
            if overlap:
                scored.append((overlap, proto_key, item_words))
        if not scored:
            return None
        scored.sort(reverse=True)
        best = scored[0]
        if len(scored) > 1 and scored[1][0] == best[0]:
            return "ambiguous"
        if has_cue:
            return best[1]
        remainder = [w for w in words
                     if w not in best[2] and w.rstrip("s") not in best[2]
                     and w not in ORDER_FILLER]
        return best[1] if not remainder else None

    def _fulfil_shop_order(self, order_text, patron):
        from world.grammar import with_article
        if not self.location or getattr(patron, "location", None) is not self.location:
            return
        counter = self._find_counter()
        match = self._match_shop_order(order_text)
        if match == "ambiguous":
            self.execute_cmd("say You'll have to be more particular — the "
                             "shelf carries more than one of those.")
            return
        if not match or counter is None:
            if not self._try_llm_reply(order_text, patron, "directed",
                                       on_fail=self._llm_fallback):
                self.execute_cmd("say Shelf's all labeled. It says what "
                                 "I sell.")
            return
        stock = counter.db.item_inventory or {}
        if not counter.db.is_infinite and int(stock.get(match, 0) or 0) <= 0:
            self.execute_cmd("say Out of that until the next delivery.")
            return
        price = int(counter.get_price(match) or 0)
        have = int(getattr(patron, "tokens", 0) or 0)
        if price and have < price:
            self.execute_cmd(f"say That's {price}. Come back when you've "
                             "got it.")
            return
        ok, item = counter.purchase_item(patron, match)
        if not ok:
            self.execute_cmd("say Counter says no. Take it up with the "
                             "counter.")
            return
        self.serve_purchase(patron, item, price)

    def serve_purchase(self, patron, item, price):
        """The handover — the keeper physically presses the purchase into
        the buyer's hand. Fired after a spoken order, and by the ``buy``
        command whenever this keeper is minding the counter (a manned shop
        is never self-service)."""
        from world.grammar import with_article
        handle = None
        try:
            handle = self._address_handle(patron)
        except Exception:  # noqa: BLE001
            pass
        target = handle or "the customer"
        self.execute_cmd(
            f"emote plucks {with_article(item.key)} from the shelf, presses "
            f"it into {target}'s hand, and sweeps {price} into the till."
        )

    def _run_context_tool(self, tool, arg, patron):
        """``check_stock`` reads the real counter (the bar analogue)."""
        if tool == "check_stock":
            counter = self._find_counter()
            if not counter:
                return "no counter to check"
            names = [display for _, display, _ in self._shelf()]
            return ("On the shelf: " + ", ".join(names) + ".") if names \
                else "The shelf is empty."
        return super()._run_context_tool(tool, arg, patron)

    def _llm_fallback(self):
        self.execute_cmd("say Shelf's all labeled. It says what I sell.")
