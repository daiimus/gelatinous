# SHOP SYSTEM SPECIFICATION

> **📋 SPECIFICATION STATUS:**
> 
> This document has been updated to reflect the **actual Phase 1 implementation** (completed December 2024).
> 
> - **Sections marked "ACTUAL IMPLEMENTATION"**: Production code, tested and working
> - **Sections marked "NOT IMPLEMENTED"**: Original spec ideas that were simplified or deferred
> 
> The actual implementation is **simpler and more direct** than the original specification:
> - ✅ Container-based shops (not room-based)
> - ✅ Regular prototypes for merchants (no MerchantTemplate system)
> - ✅ AttributeProperty currency (no CurrencyMixin)
> - ✅ Direct attribute inspection for dynamic names (no complex template system)

## Overview

This specification defines a container-based shop system for the G.R.I.M. MUD with two merchant types and a foundation for dynamic economies.

### Phase 1: Fixed Shops (Current Implementation)
- **Prototype-Based Architecture**: ShopContainers store prototype inventories and pricing
- **Physical Containers**: ShopContainers (shelves, displays) are physical objects with inventories
- **Holographic Merchants**: NPCs with `is_holographic` and `is_merchant` AttributeProperties - combat-protected
- **Simple Pricing**: Fixed prices per prototype, stored in container
- **Buy-Only**: Players can only purchase items. Selling is Phase 2 marketplace feature
- **Token Currency**: Characters have `tokens` AttributeProperty (default: 0)
- **Customizable Messages**: Purchase messages configurable per shop via container attributes

### Phase 2: Dynamic Marketplaces (Future)
- **Procedural Mazes**: Marketplace rooms that reconfigure on timers
- **Haggling System**: Price negotiation for both buying AND selling (selling only available in marketplaces)
- **Dynamic Pricing**: Supply/demand based on database queries and rarity
- **Grid Integration**: Marketplaces auto-connect to key anchor points
- **Two-Way Economy**: Unlike Phase 1 shops (buy-only), marketplaces support selling items

### Phase 3+: Advanced Features (Deferred)
- Player-owned shops
- Crafting commissions
- Economic simulation
- Broker systems

## Design Philosophy

1. **Container-Based Architecture**: ShopContainers are standalone objects that manage their own inventory and pricing. No room configuration needed.

2. **Prototype Inventory**: Items stored as prototype keys, spawned on purchase to prevent database bloat.

3. **Holographic Merchants**: NPCs protected via `validate_attack_target()` method and AttributeProperties (`is_merchant`, `is_holographic`).

4. **Infinite Inventory Mode**: Shops operate in infinite mode by default - items never run out.

5. **AttributeProperty Currency**: All characters have `tokens` AttributeProperty (autocreate, default 0).

6. **Customizable Messaging**: Purchase messages stored on container with placeholder support ({buyer}, {item}, {price}, {shop}).

7. **Data-Driven Display**: Can names derived from `aerosol_contents` attribute - extensible for future dynamic items.

8. **Phase 1 is Buy-Only**: Fixed shops only support purchasing. Selling is Phase 2 with haggling.

9. **Self-Service Shops**: Merchants are decorative/atmospheric. Shops function without merchant presence (no attendance check).

10. **Builder-Friendly**: Simple @py commands to set up shops.

11. **Traditional Commands**: No EvMenu - players use `buy <item> from <container>` and `look <container>`.

## System Architecture

```
world/shop/
├── __init__.py
├── utils.py                  # get_prototype_value, format_currency, etc.

typeclasses/
├── shopkeeper.py             # ShopContainer - prototype inventory manager
├── characters.py             # Character with tokens AttributeProperty, holographic support

commands/
├── shop.py                   # CmdBuy with fuzzy matching and customizable messages
└── default_cmdsets.py        # CharacterCmdSet includes CmdBuy

world/prototypes.py           # Merchant prototypes (HOLOGRAPHIC_MERCHANT, etc.)
```

## Core Components - Phase 1 (ACTUAL IMPLEMENTATION)

### 1. ShopContainer Typeclass

**Location:** `typeclasses/shopkeeper.py`

**Purpose:** Physical container object that manages prototype-based shop inventory with infinite stock mode.

**Key Attributes:**
```python
self.db.prototype_inventory = {}  # {prototype_key: price}
self.db.item_inventory = {}       # For future limited stock mode
self.db.is_infinite = True        # Infinite stock enabled
self.db.shop_name = "Shop"        # Display name
self.db.container_type = "shelf"   # Container type
self.db.purchase_msg_buyer = "You purchase {item} for {price}."
self.db.purchase_msg_room = "{buyer} purchases {item} from {shop}."
```

**Key Methods:**
- `add_prototype(prototype_key, price)` - Add item to inventory
- `get_price(prototype_key)` - Get price for item
- `is_in_stock(prototype_key)` - Check availability (always True in infinite mode)
- `purchase_item(buyer, prototype_key)` - Process purchase, spawn item, deduct tokens
- `get_display_name_for_prototype(prototype_key, prototype)` - Get display name (handles cans via aerosol_contents)
- `get_browse_display(viewer)` - Generate inventory listing
- `return_appearance(looker)` - Override look to show inventory

**Purchase Flow:**
1. Validate prototype exists in inventory
2. Check if in stock (infinite mode always True)
3. Get price from inventory dict
4. Verify buyer has enough tokens
5. Spawn item from prototype
6. Set `item.location = buyer`
7. Deduct tokens: `buyer.tokens -= price`
8. Return success and item

### 2. Character Currency System

**Location:** `typeclasses/characters.py`

**Implementation:**
```python
# AttributeProperty for automatic initialization
tokens = AttributeProperty(0, category="shop", autocreate=True)
```

**Benefits:**
- All characters automatically have tokens attribute
- Defaults to 0 for new and existing characters
- No manual initialization needed
- Persistent across restarts

### 3. Holographic Merchant Protection

**Location:** `typeclasses/characters.py`

**AttributeProperties:**
```python
is_merchant = AttributeProperty(False, category="shop", autocreate=True)
is_holographic = AttributeProperty(False, category="shop", autocreate=True)
```

**Combat Integration:**
```python
def validate_attack_target(self, attacker):
    """Check if character can be attacked (holographic protection)."""
    if self.is_holographic:
        # Show glitch messages
        attacker.msg(f"|cYour attack passes through {self.key}'s holographic form!|n")
        # ... observer messages ...
        return (False, None)  # Prevent attack
    return (True, None)  # Allow attack
```

**CmdAttack Integration** (`commands/combat/core_actions.py`):
```python
# After target resolution
if hasattr(target, 'validate_attack_target'):
    can_attack, error_msg = target.validate_attack_target(caller)
    if not can_attack:
        if error_msg:
            caller.msg(error_msg)
        return
```

### 4. Buy Command

**Location:** `commands/shop.py`

**Features:**
- Fuzzy matching by item name
- Matches by display name (handles cans via `get_display_name_for_prototype`)
- Customizable purchase messages via container attributes
- Auto-wields items in hands if available

**Syntax:**
```
buy <item> from <container>
buy spraypaint from shop
buy solvent from shop
```

**Purchase Flow:**
1. Parse `buy <item> from <container>` syntax
2. Find container in room
3. Call `container._find_prototype_key(item_name)` - uses display names
4. Call `container.purchase_item(caller, prototype_key)`
5. Call `_give_item_to_buyer(buyer, item)` - wields if hands empty
6. Send customizable messages from container.db.purchase_msg_*
7. Notify merchant if present via `_notify_merchant()`

**Display Name Matching:**
```python
def _find_prototype_key(self, container, item_name):
    # Get display name using container's method (handles cans)
    display_name = container.get_display_name_for_prototype(proto_key, prototype).lower()
    
    # Match if search term in display name
    if item_name_lower in display_name or display_name in item_name_lower:
        return proto_key
```

### 5. Dynamic Item Names

**Problem:** Items like cans have dynamic names ("can of spraypaint" vs "can of solvent")

**Solution:** Data-driven display names via prototype attributes

**Implementation:**
```python
# In ShopContainer.get_display_name_for_prototype()
attrs = prototype.get("attrs", [])
for attr in attrs:
    if isinstance(attr, tuple) and attr[0] == "aerosol_contents":
        return f"can of {attr[1]}"  # e.g., "can of spraypaint"
return prototype.get("key", prototype_key)
```

**Benefits:**
- No hardcoded item names
- Extensible for future dynamic items
- Works with any attribute pattern

### 6. Merchant Prototypes

**Location:** `world/prototypes.py`

**Base Holographic Merchant:**
```python
HOLOGRAPHIC_MERCHANT = {
    "prototype_parent": "BASE_NPC",
    "key": "holographic merchant",
    "typeclass": "typeclasses.characters.Character",
    "attrs": [
        ("is_merchant", True),
        ("is_holographic", True),
    ],
}
```

**Specific Merchants (inherit from HOLOGRAPHIC_MERCHANT):**
- `ARMORY_MERCHANT` - Gunther Steele (weapons)
- `GENERAL_MERCHANT` - Sal Mendoza (supplies)
- `MEDIC_MERCHANT` - Dr. Cassandra Voss (medical)
- `CORNERSTORE_MERCHANT` - Juan Sanchez (corner market)

**Usage:**
```python
@spawn CORNERSTORE_MERCHANT
```

**Current Behavior:**
- Merchants are **purely decorative/atmospheric** in Phase 1
- Shops function without merchant presence (self-service)
- Merchants receive transaction notifications but don't interact
- No greeting, dialogue, or attendance requirement
- Future phases may add merchant interactions and attendance checks

### 7. Utility Functions

**Location:** `world/shop/utils.py`

**Key Functions:**
```python
def get_prototype_value(prototype):
    """Extract 'value' attribute from prototype attrs list."""
    for attr in prototype.get("attrs", []):
        if isinstance(attr, tuple) and attr[0] == "value":
            return int(attr[1])
    return 10  # Default

def format_currency(amount):
    """Format tokens as '150₮' or '0₮' for free items."""
    return f"{amount}₮"

def parse_currency(text):
    """Parse '150₮' back to integer 150."""
    # Implementation...
```

### 8. Customizable Purchase Messages

**Container Attributes:**
```python
self.db.purchase_msg_buyer = "You purchase {item} for {price}."
self.db.purchase_msg_room = "{buyer} purchases {item} from {shop}."
```

**Available Placeholders:**
- `{buyer}` - Buyer's display name
- `{item}` - Item's display name
- `{price}` - Formatted price (e.g., "50₮")
- `{shop}` - Shop container's display name

**Customization Example:**
```python
@py shop = me.search("shop")
@py shop.db.purchase_msg_buyer = "|gAh, excellent choice!|n You purchase {item} for {price}."
@py shop.db.purchase_msg_room = "{buyer} haggles with Juan before purchasing {item}."
```

**Implementation** (`commands/shop.py`):
```python
msg_buyer = container.db.purchase_msg_buyer or "You purchase {item} for {price}."
msg_room = container.db.purchase_msg_room or "{buyer} purchases {item} from {shop}."

format_data = {
    "buyer": caller.get_display_name(caller),
    "item": item.get_display_name(caller),
    "price": format_currency(price),
    "shop": container.get_display_name(caller)
}

caller.msg(msg_buyer.format(**format_data))
caller.location.msg_contents(msg_room.format(**format_data), exclude=caller)
```

## Core Components - Phase 1 (ORIGINAL SPEC - NOT IMPLEMENTED)

### 1. Currency System (ACTUAL IMPLEMENTATION)

**Character Attribute:**

```python
# typeclasses/characters.py

class Character(LivingMixin, DefaultCharacter):
    # AttributeProperty for automatic initialization
    tokens = AttributeProperty(0, category="shop", autocreate=True)
```

**Benefits:**
- All characters automatically have `tokens` attribute
- Defaults to 0 for both new and existing characters
- No manual initialization in `at_object_creation()` required
- Persists across server restarts (stored in database)
- Direct access: `char.tokens = 100` or `char.tokens -= 50`

**Utility Functions:**

```python
# world/shop/utils.py

def format_currency(amount):
    """
    Format tokens for display.
    
    Args:
        amount (int): Token amount
        
    Returns:
        str: Formatted string like "150₮" or "0₮"
        
    Example:
        >>> format_currency(150)
        '150₮'
        >>> format_currency(0)
        '0₮'
    """
    return f"{amount}₮"

def parse_currency(text):
    """
    Parse currency string back to integer.
    
    Args:
        text (str): Currency string like "150₮"
        
    Returns:
        int: Token amount
        
    Example:
        >>> parse_currency("150₮")
        150
    """
    return int(text.rstrip("₮"))

def get_prototype_value(prototype):
    """
    Extract 'value' attribute from prototype attrs list.
    
    Evennia prototypes store attributes in 'attrs' as tuples.
    This handles the list format and provides safe fallback.
    
    Args:
        prototype (dict): Prototype dictionary
        
    Returns:
        int: Value attribute, or 10 as default
        
    Example:
        >>> proto = {"attrs": [("value", 50), ("weight", 2)]}
        >>> get_prototype_value(proto)
        50
    """
    for attr in prototype.get("attrs", []):
        if isinstance(attr, (list, tuple)) and len(attr) >= 2:
            if attr[0] == "value":
                return int(attr[1])
    return 10  # Default fallback
```

**Usage Examples:**

```python
# Give tokens to player
char.tokens = 100

# Check if can afford
if char.tokens >= price:
    char.tokens -= price
    
# Display current tokens
char.msg(f"You have {format_currency(char.tokens)}")
# Output: "You have 150₮"

# Get item value from prototype
from evennia.prototypes.prototypes import search_prototype
proto = search_prototype("SPRAYPAINT_CAN")[0]
value = get_prototype_value(proto)
# value = 50 (from proto's attrs)
```

**Currency Lore:**

The **Token (₮)** is standard colonial scrip used throughout Gelatinous. Street slang includes "ticks," "tabs," and "kennys," but the system currently displays the official ₮ symbol
- **"Tabs"** - From "running a tab," implies debt and company store economics
- **"Kennys"** - Origin unknown, possibly from a famous debtor or colonial administrator

Example NPC dialogue:
```
"That medkit? 150 ticks, no haggling."
"I need at least 30 tabs for this junk."
"You got the kennys for it, or you just window shopping?"
for future dynamic pricing phases.

---

## ⚠️ NOT IMPLEMENTED IN PHASE 1 ⚠️

The following sections describe features from the original specification that were **NOT implemented** in Phase 1. They remain here for reference and potential future development.

---

### 2. Merchant Template System (NOT IMPLEMENTED)

**Note:** The actual Phase 1 implementation uses regular Evennia prototypes (HOLOGRAPHIC_MERCHANT, ARMORY_MERCHANT, etc.) instead of a dedicated MerchantTemplate system. Merchants are spawned with `@spawn PROTOTYPE_NAME` and have `is_merchant` and `is_holographic` AttributeProperties.

**Original Spec:**

**What is a MerchantTemplate?**

A **MerchantTemplate** is a reusable "blueprint" for spawning shop NPCs. Think of it as a **character sleeve** or **prototype** that defines:
- Physical appearance (name, description, gender)
- Personality traits (greetings, dialogue, attitude)
- Stats (G.R.I.M. values for future haggling mechanics)
- Shop behavior (which room they work in)

**Why Templates?**

Templates solve two key problems:
1. **Respawning**: When a merchant dies, the room can spawn an identical replacement
2. **Consistency**: Multiple shops can use the same merchant "archetype" (weapons dealer, medic, etc.)

**How It Works:**

```
1. Builder creates MerchantTemplate("weapons_dealer") with name, stats, personality
2. Room stores template_key in shop_config: {"merchant_template": "weapons_dealer"}
3. Room spawns Character from template → regular Character with merchant flags
4. Character dies → Room waits 5 minutes → spawns new Character from same template
5. New NPC looks/acts identical to the dead one (it's the "same person" narratively)
```

**Implementation:**

```python
# world/economy/shops/templates.py

from evennia.utils.create import create_object

class MerchantTemplate:
    """
    Blueprint for spawning/respawning shop merchant NPCs.
    Defines appearance, personality, and stats for consistency.
    """
    
    def __init__(self, template_key):
        """
        Args:
            template_key (str): Unique identifier (e.g., "weapons_dealer", "medic")
        """
        self.template_key = template_key
        
        # Physical appearance
        self.name = "Generic Merchant"
        self.desc = "A merchant stands here."
        self.gender = "neutral"
        
        # Personality/dialogue
        self.greeting = "Welcome to my shop!"
        self.farewell = "Come back soon!"
        self.combat_taunt = "You'll regret that!"
        
        # Stats (for future haggling system)
        self.grit = 1
        self.resonance = 1
        self.intellect = 2  # Merchants tend to be clever
        self.motorics = 1
        
        # Holographic flag
        self.is_holographic = False
    
    def spawn_merchant(self, shop_room):
        """
        Spawn a Character from this template in the shop room.
        
        Args:
            shop_room (Room): The room with shop_config
            
        Returns:
            Character: Newly spawned merchant NPC
        """
        from typeclasses.characters import Character
        
        # Create regular Character
        merchant = create_object(
            typeclass=Character,
            key=self.name,
            location=shop_room
        )
        
        # Apply template appearance
        merchant.db.desc = self.desc
        merchant.db.gender = self.gender
        
        # Apply template stats
        merchant.db.grit = self.grit
        merchant.db.resonance = self.resonance
        merchant.db.intellect = self.intellect
        merchant.db.motorics = self.motorics
        
        # Apply template personality
        merchant.db.greeting = self.greeting
        merchant.db.farewell = self.farewell
        merchant.db.combat_taunt = self.combat_taunt
        
        # Mark as merchant
        merchant.db.is_merchant = True
        merchant.db.shop_room = shop_room
        merchant.db.template_key = self.template_key
        
        # Holographic flag (affects combat interaction)
        merchant.db.is_holographic = self.is_holographic
        
        return merchant


# Pre-defined merchant templates
MERCHANT_TEMPLATES = {}

# Weapons Dealer
weapons_dealer = MerchantTemplate("weapons_dealer")
weapons_dealer.name = "Jaxxon Vale"
weapons_dealer.desc = "A grizzled weapons dealer with cybernetic eyes and scarred hands."
weapons_dealer.gender = "male"
weapons_dealer.intellect = 2
weapons_dealer.greeting = "Looking for something with stopping power?"
weapons_dealer.farewell = "Stay dangerous out there."
MERCHANT_TEMPLATES["weapons_dealer"] = weapons_dealer

# General Store Clerk
general_store = MerchantTemplate("general_store")
general_store.name = "Mira Chen"
general_store.desc = "A friendly shopkeeper with a warm smile and quick wit."
general_store.gender = "female"
general_store.resonance = 2
general_store.greeting = "Welcome! Looking for supplies?"
general_store.farewell = "Come back anytime!"
MERCHANT_TEMPLATES["general_store"] = general_store

# Armor Smith (Holographic)
armor_smith = MerchantTemplate("armor_smith")
armor_smith.name = "Forge-Pattern Delta"
armor_smith.desc = "A holographic construct resembling a heavily armored smith. Pixels flicker at the edges."
armor_smith.gender = "neutral"
armor_smith.intellect = 2
armor_smith.is_holographic = True  # This merchant is invulnerable
armor_smith.greeting = "PROTECTION PROTOCOLS AVAILABLE."
armor_smith.farewell = "STAY SHIELDED."
MERCHANT_TEMPLATES["armor_smith"] = armor_smith


def get_merchant_template(template_key):
    """
    Get a merchant template by key.
    
    Args:
        template_key (str): Template identifier
        
    Returns:
        MerchantTemplate or None
    """
    return MERCHANT_TEMPLATES.get(template_key)
```

### 3. Room-Based Shop System

**Design Philosophy:**

The **Room itself is the shop**. All shop data lives on the Room's database attributes, not on merchant NPCs. Merchants are just regular Characters standing in the shop - they can be killed, swapped out, or absent entirely.

**Benefits:**
- Shop persists even when merchant is dead/missing
- Multiple merchants can work the same shop
- Player shops use the same system (no merchant needed)
- Easy to swap merchants for events, day/night cycles, etc.
- Simpler code - no merchant subclasses needed

**Implementation:**

```python
# In typeclasses/rooms.py

class Room(DefaultRoom):
    """
    Room with optional shop configuration.
    """
    
    def at_object_creation(self):
        """Initialize room."""
        super().at_object_creation()
        
        # Shop configuration (None if not a shop)
        self.db.shop_config = None
    
    def setup_as_shop(self, prototype_inventory, merchant_template_key, **kwargs):
        """
        Configure this room as a shop.
        
        Args:
            prototype_inventory (list): Prototype keys for items sold here
            merchant_template_key (str): Template for spawning merchants
            **kwargs: Additional shop config
        """
        self.db.shop_config = {
            # Inventory
            "prototype_inventory": prototype_inventory,
            
            # Pricing
            "upsell_factor": kwargs.get("upsell_factor", 1.2),
            
            # Merchant management
            "merchant_template": merchant_template_key,
            "merchant_respawn_delay": kwargs.get("respawn_delay", 300),  # 5 minutes
            "current_merchant": None,  # Reference to spawned merchant
            "allows_unmanned_sales": kwargs.get("allows_unmanned_sales", False),  # Self-service mode
            
            # Shop metadata
            "shop_name": kwargs.get("shop_name", f"{self.key} Shop"),
            "greeting": kwargs.get("greeting", "Welcome!"),
        }
        
        # Tag as shop
        self.tags.add("shop", category="shop_system")
    
    def spawn_merchant(self):
        """
        Spawn merchant from template for this shop.
        
        Returns:
            Character: Newly spawned merchant, or None if template invalid
        """
        if not self.db.shop_config:
            return None
        
        template_key = self.db.shop_config["merchant_template"]
        from world.economy.shops.templates import get_merchant_template
        
        template = get_merchant_template(template_key)
        if not template:
            return None
        
        merchant = template.spawn_merchant(self)
        self.db.shop_config["current_merchant"] = merchant
        
        return merchant
    
    def handle_merchant_death(self, merchant):
        """
        Called when shop merchant dies. Schedules respawn.
        
        Args:
            merchant (Character): The merchant who died
        """
        if not self.db.shop_config:
            return
        
        # Clear current merchant reference
        self.db.shop_config["current_merchant"] = None
        
        # Schedule respawn
        delay = self.db.shop_config.get("merchant_respawn_delay", 300)
        from evennia.utils import delay as evennia_delay
        evennia_delay(delay, self.spawn_merchant)
        
        # Notify room
        self.msg_contents(
            f"|y{merchant.key} has fallen! Another will arrive in {delay//60} minutes...|n"
        )
    
    def is_shop(self):
        """Check if this room is configured as a shop."""
        return self.db.shop_config is not None
    
    def get_shop_inventory(self):
        """
        Get list of items available for purchase in this shop.
        
        Returns:
            list: Prototype keys
        """
        if not self.db.shop_config:
            return []
        return self.db.shop_config.get("prototype_inventory", [])
    
    def get_upsell_factor(self):
        """Get price markup for selling to players."""
        if not self.db.shop_config:
            return 1.0
        return self.db.shop_config.get("upsell_factor", 1.2)
```

### 4. Character Merchant Flags

**Implementation:**

```python
# In typeclasses/characters.py

class Character(DefaultCharacter):
    """
    Character with merchant and holographic support.
    """
    
    def at_object_creation(self):
        """Initialize character."""
        super().at_object_creation()
        
        # Merchant flags
        self.db.is_merchant = False
        self.db.shop_room = None  # Reference to shop room
        self.db.template_key = None  # For respawning
        
        # Holographic flag (affects combat)
        self.db.is_holographic = False
    
    def validate_attack_target(self, attacker):
        """
        Validate if this character can be attacked.
        Called by CmdAttack before combat initiation.
        
        Holographic merchants cannot be attacked - show glitch effect instead.
        
        Returns:
            tuple: (can_attack: bool, message: str or None)
        """
        if self.db.is_holographic:
            # Show glitch effect
            attacker.msg(
                f"|cYour attack passes through {self.key}'s holographic form with a crackle of static!|n"
            )
            self.location.msg_contents(
                f"|c{attacker.key}'s attack disrupts {self.key}'s projection, causing visible glitches.|n",
                exclude=[attacker, self]
            )
            
            # Merchant reacts
            responses = [
                "Violence is so... analog. Can I interest you in a purchase instead?",
                "I'm incorporeal. You're wasting your energy.",
                "My projection is backed up. This is futile.",
                "Cute. Now, about those prices..."
            ]
            from random import choice
            # Send merchant response directly to attacker
            attacker.msg(f"{self.key} says, \"{choice(responses)}\"")
            
            # Prevent attack
            return (False, None)  # Message already sent
        
        return (True, None)  # Allow attack
    
    def at_death(self):
        """
        Handle character death.
        
        For merchant NPCs, notify the shop room for respawn handling.
        """
        super().at_death()
        
        # If this is a shop merchant, notify the room
        if self.db.is_merchant and self.db.shop_room:
            shop_room = self.db.shop_room
            if shop_room and hasattr(shop_room, 'handle_merchant_death'):
                shop_room.handle_merchant_death(self)
```

**CmdAttack Integration:**

To make holographic merchants work, add this validation in `CmdAttack.func()` after target resolution:

```python
# In commands/combat/core_actions.py, CmdAttack.func()
# After: target = potential_targets[0]
# Add:
if hasattr(target, 'validate_attack_target'):
    can_attack, error_msg = target.validate_attack_target(caller)
    if not can_attack:
        if error_msg:
            caller.msg(error_msg)
        return  # Attack cancelled
```

### 5. Shop Container System

**Design Goals:**
- Physical containers (shelves, displays, racks) hold shop inventory
- Containers store **prototype keys**, not physical objects
- Items spawn on purchase from prototypes
- Vending machines are specialized containers
- Syntax: `look shelf`, `buy grenade from shelf`

**Implementation:**

```python
# typeclasses/shopkeeper.py

from evennia import DefaultObject
from evennia.prototypes.spawner import spawn
from evennia.prototypes.prototypes import search_prototype

class ShopContainer(DefaultObject):
    """
    Physical container that displays items for sale.
    Stores prototype keys, spawns items on purchase.
    
    Examples: shelf, display case, rack, barrel, weapons wall
    """
    
    def at_object_creation(self):
        """Initialize container."""
        self.locks.add("get:false()")  # Can't pick up the container
        
        # Container configuration
        self.db.container_type = "shelf"
        self.db.desc = f"A {self.db.container_type} displaying wares for sale."
        
        # Prototype inventory - list of prototype keys
        self.db.prototype_inventory = []  # e.g., ["FRAG_GRENADE", "KEVLAR_VEST", "SWORD"]
    
    def return_appearance(self, looker, **kwargs):
        """
        Show container and items for sale with prices.
        """
        text = self.db.desc or f"A {self.db.container_type} with items for sale."
        
        if not self.db.prototype_inventory:
            text += f"\n\nThe {self.db.container_type} is empty."
            return text
        
        # Build item list from prototypes
        text += f"\n\n|wItems for sale:|n"
        
        from evennia.utils.evtable import EvTable
        from world.economy.constants import format_currency
        from evennia.prototypes.prototypes import search_prototype
        
        table = EvTable("Item", "Price", "Description", border="cells")
        
        # Get room's upsell factor
        room = self.location
        upsell = room.get_upsell_factor() if room and room.is_shop() else 1.2
        
        table = EvTable("Item", "Price", "Description", border="cells", width=70)
        
        for proto_key in self.db.prototype_inventory:
            # Look up prototype
            proto_list = search_prototype(key=proto_key)
            if not proto_list:
                continue
            
            proto = proto_list[0]
            
            # Extract info
            name = proto.get("key", "Unknown")
            desc = proto.get("desc", "")[:50] + "..." if len(proto.get("desc", "")) > 50 else proto.get("desc", "")
            
            # Get base value using utility function
            from world.economy.utils import get_prototype_value
            base_value = get_prototype_value(proto)
            
            # Calculate price using room's upsell factor
            price = int(base_value * upsell)
            
            table.add_row(name, format_currency(price), desc)
        
        text += "\n" + str(table)
        text += f"\n\nUse |wbuy <item> from {self.key}|n to purchase."
        
        return text
    
    def get_prototype_by_name(self, item_name):
        """
        Find a prototype in inventory by name.
        
        Args:
            item_name (str): Name to search for
            
        Returns:
            dict or None: Prototype dict if found
        """
        item_name_lower = item_name.lower()
        
        for proto_key in self.db.prototype_inventory:
            proto_list = search_prototype(key=proto_key)
            if not proto_list:
                continue
            
            proto = proto_list[0]
            key = proto.get("key", "").lower()
            aliases = [a.lower() for a in proto.get("aliases", [])]
            
            # Check exact match
            if key == item_name_lower or item_name_lower in aliases:
                return proto
            
            # Check partial match
            if item_name_lower in key:
                return proto
        
        return None
    
    def purchase_item(self, buyer, item_name):
        """
        Handle purchase from this container.
        
        Args:
            buyer (Character): Who is buying
            item_name (str): What they want
            
        Returns:
            tuple: (success, message, spawned_item or None)
        """
        # Find prototype
        proto = self.get_prototype_by_name(item_name)
        if not proto:
            return False, f"'{item_name}' is not available in the {self.key}.", None
        
        # Calculate price using room's upsell factor
        room = self.location
        if not room or not room.is_shop():
            return False, "This container is not in a functioning shop.", None
        
        from world.economy.utils import get_prototype_value
        base_value = get_prototype_value(proto)
        
        upsell = room.get_upsell_factor()
        price = int(base_value * upsell)
        
        # Check funds
        if not buyer.can_afford(price):
            from world.economy.constants import format_currency
            return False, f"You need {format_currency(price)} but only have {buyer.get_currency_display()}.", None
        
        # Spawn item
        try:
            spawned = spawn(proto)
            if not spawned:
                return False, "Item spawning failed. Contact an administrator.", None
            item = spawned[0]
        except Exception as e:
            return False, f"Purchase error: {e}", None
        
        # Deduct currency
        buyer.pay_credits(price)
        
        # Give item to buyer
        self._give_item_to_buyer(buyer, item)
        
        # Success message
        from world.economy.constants import format_currency
        return True, f"You buy {item.key} for {format_currency(price)}.", item
    
    def _give_item_to_buyer(self, buyer, item):
        """Put item in buyer's hands or inventory using the hands system."""
        # Use the wield_item method if available (proper hands integration)
        if hasattr(buyer, 'wield_item'):
            # Try right hand first, then left
            for hand in ['right', 'left']:
                result = buyer.wield_item(item, hand=hand)
                if not isinstance(result, str) or "already holding" not in result.lower():
                    # Successfully wielded
                    return
            
            # Both hands full - fall back to inventory
            item.location = buyer
            buyer.msg(f"|yYour hands are full. {item.key} goes to your inventory.|n")
        else:
            # Fallback for characters without hands system
            item.location = buyer
            buyer.msg(f"{item.key} goes to your inventory.")


# Room integration example for builders:
# @create/drop weapons_shelf:typeclasses.shopkeeper.ShopContainer
# @set weapons_shelf/container_type = "weapons rack"
# @desc weapons_shelf = A sturdy rack displaying various weapons.
# @py weapons_shelf.db.prototype_inventory = ["FRAG_GRENADE", "SWORD", "KEVLAR_VEST"]
```

### 6. Vending Machine (Automated ShopContainer)

**What is a Vending Machine?**

A **VendingMachine** is a specialized ShopContainer that operates completely autonomously - no merchant NPC required. Think of it like real-world vending machines: insert money, press button, get item.

**Key Features:**
- **Slot-based interface**: Items organized in slots (A1, B2, C3, etc.)
- **Fixed pricing**: Price multiplier applied to base item values
- **Stock management**: Optional limited quantities or unlimited stock
- **Machine states**: Operational, out-of-order, sold out slots
- **No merchant needed**: Fully automated transactions
- **Perfect for**: Medical supplies, ammo, quick consumables

**Use Cases:**
- Street corners with basic supplies (bandages, stimpaks)
- Safe zones with emergency gear
- High-tech areas with automated kiosks
- Locations where merchants would be impractical

**Design Goals:**
- Specialized ShopContainer subclass
- No merchant required - fully automated
- Slot-based display (A1, B2, C3, etc.)
- Fixed prices, instant transactions
- Perfect for unattended sales

**Implementation:**

```python
# typeclasses/shopkeeper.py (continued)

class VendingMachine(ShopContainer):
    """
    Automated vending machine - ShopContainer with slot-based interface.
    No merchant required.
    
    Example setup:
        machine = create_object(VendingMachine, key="MedStation Alpha")
        machine.db.slot_inventory = {
            "A1": "BANDAGE",
            "A2": "PAINKILLER", 
            "B1": "BLOOD_BAG"
        }
        machine.db.price_multiplier = 1.5  # 50% markup
    """
    
    def at_object_creation(self):
        """Initialize vending machine."""
        super().at_object_creation()
        
        self.db.container_type = "vending machine"
        self.db.desc = "An automated vending machine with a digital display."
        
        # Slot configuration - maps slot codes to prototype keys
        # Example: {"A1": "FRAG_GRENADE", "A2": "BANDAGE", "B1": "STIMPAK"}
        self.db.slot_inventory = {}
        
        # Stock tracking (optional - for limited quantity)
        # If unlimited_stock=True, these are ignored
        # Example: {"A1": 5, "A2": 10, "B1": 3}
        self.db.stock_quantities = {}
        self.db.unlimited_stock = True  # Set False for limited stock
        
        # Machine state
        self.db.is_operational = True
        self.db.out_of_order_msg = "** OUT OF ORDER - CONTACT MAINTENANCE **"
        
        # Pricing
        # Items sold at: base_value * price_multiplier
        # Example: BANDAGE worth 10 credits → sells for 15 at 1.5 multiplier
        self.db.price_multiplier = 1.5
        
        # Visual theming (optional)
        self.db.brand_name = None  # "MediCorp", "AutoVend", etc.
        self.db.interface_color = "blue"  # Color of display in descriptions
    
    def return_appearance(self, looker, **kwargs):
        """
        Show vending machine interface with slots, items, prices.
        
        Example output:
            An automated vending machine with a glowing blue display.
            
            Available Items:
            ┌──────┬─────────────┬────────┬────────┐
            │ Slot │ Item        │ Price  │ Stock  │
            ├──────┼─────────────┼────────┼────────┤
            │ A1   │ Bandage     │ 15₮    │ ∞      │
            │ A2   │ Painkiller  │ 30₮    │ 5      │
            │ B1   │ Blood Bag   │ 50₮    │ SOLD   │
            └──────┴─────────────┴────────┴────────┘
            
            Use 'buy <slot> from machine' (e.g., 'buy A1 from machine')
        """
        if not self.db.is_operational:
            return f"|r{self.db.out_of_order_msg}|n"
        
        # Build header
        text = self.db.desc
        
        if self.db.brand_name:
            color_code = f"|{self.db.interface_color[0]}" if self.db.interface_color else "|w"
            text += f"\n{color_code}[ {self.db.brand_name} ]|n"
        
        text += "\n\n|wAvailable Items:|n\n"
        
        from evennia.utils.evtable import EvTable
        from evennia.prototypes.prototypes import search_prototype
        from world.economy.constants import format_currency
        
        table = EvTable("Slot", "Item", "Price", "Stock", border="cells")
        
        # Sort slots alphabetically (A1, A2, B1, B2, etc.)
        for slot in sorted(self.db.slot_inventory.keys()):
            proto_key = self.db.slot_inventory[slot]
            
            # Look up prototype
            proto_list = search_prototype(key=proto_key)
            if not proto_list:
                # Prototype not found - skip or show error
                table.add_row(slot, "|rERROR|n", "-", "-")
                continue
            
            proto = proto_list[0]
            name = proto.get("key", "Unknown")
            
            # Get base value using utility function
            from world.economy.utils import get_prototype_value
            base_value = get_prototype_value(proto)
            
            # Calculate vending price
            price = int(base_value * self.db.price_multiplier)
            
            # Stock display
            if self.db.unlimited_stock:
                stock = "∞"
            else:
                qty = self.db.stock_quantities.get(slot, 0)
                if qty > 0:
                    stock = str(qty)
                else:
                    stock = "|rSOLD OUT|n"
            
            table.add_row(slot, name, format_currency(price), stock)
        
        text += "\n" + str(table)
        text += "\n\nUse |wbuy <slot> from <machine>|n (e.g., 'buy A1 from machine')"
        
        return text
    
    def get_prototype_by_name(self, item_name):
        """
        Override to handle slot-based lookup.
        Supports both slot codes (A1) and item names (bandage).
        
        Args:
            item_name (str): Slot code or item name
            
        Returns:
            dict: Prototype dict, or None
        """
        from evennia.prototypes.prototypes import search_prototype
        
        item_name_upper = item_name.upper()
        
        # Try slot code first (A1, B2, etc.)
        if item_name_upper in self.db.slot_inventory:
            proto_key = self.db.slot_inventory[item_name_upper]
            proto_list = search_prototype(key=proto_key)
            if proto_list:
                return proto_list[0]
        
        # Fall back to name search (search all slots for matching item name)
        for slot, proto_key in self.db.slot_inventory.items():
            proto_list = search_prototype(key=proto_key)
            if proto_list:
                proto = proto_list[0]
                if proto.get("key", "").lower() == item_name.lower():
                    return proto
        
        return None
    
    def purchase_item(self, buyer, item_name):
        """
        Vending machine purchase - handles stock and machine state.
        """
        if not self.db.is_operational:
            return False, f"|r{self.db.out_of_order_msg}|n", None
        
        # Find slot/prototype
        item_name_upper = item_name.upper()
        slot = None
        proto_key = None
        
        # Check if it's a slot code
        if item_name_upper in self.db.slot_inventory:
            slot = item_name_upper
            proto_key = self.db.slot_inventory[slot]
        else:
            # Search by name
            proto = self.get_prototype_by_name(item_name)
            if proto:
                # Find which slot has this prototype
                for s, pk in self.db.slot_inventory.items():
                    if pk == proto.get("prototype_key", proto.get("key")):
                        slot = s
                        proto_key = pk
                        break
        
        if not proto_key:
            return False, f"'{item_name}' is not available in this machine.", None
        
        # Check stock
        if not self.db.unlimited_stock:
            qty = self.db.stock_quantities.get(slot, 0)
            if qty < 1:
                return False, f"Slot {slot} is sold out.", None
        
        # Get prototype and calculate price
        from evennia.prototypes.prototypes import search_prototype
        from world.economy.utils import get_prototype_value
        
        proto_list = search_prototype(key=proto_key)
        if not proto_list:
            return False, "Item not found in database.", None
        
        proto = proto_list[0]
        base_value = get_prototype_value(proto)
        price = int(base_value * self.db.price_multiplier)
        
        # Check funds
        if not buyer.can_afford(price):
            from world.economy.constants import format_currency
            return False, f"Insufficient funds. Need {format_currency(price)}, have {buyer.get_currency_display()}.", None
        
        # Spawn item
        from evennia.prototypes.spawner import spawn
        try:
            spawned = spawn(proto)
            if not spawned:
                return False, "Vending error. Contact an administrator.", None
            item = spawned[0]
        except Exception as e:
            return False, f"Vending error: {e}", None
        
        # Process transaction
        buyer.pay_credits(price)
        
        # Update stock
        if not self.db.unlimited_stock:
            self.db.stock_quantities[slot] -= 1
        
        # Give item
        self._give_item_to_buyer(buyer, item)
        
        from world.economy.constants import format_currency
        return True, f"You insert {format_currency(price)}. {item.key} drops from slot {slot}.", item
    
    def restock_slot(self, slot, quantity):
        """
        Restock a specific slot (for builder/admin use).
        
        Args:
            slot (str): Slot code (A1, B2, etc.)
            quantity (int): Amount to add
            
        Returns:
            tuple: (success, message)
        """
        if slot not in self.db.slot_inventory:
            return False, f"Slot {slot} does not exist."
        
        if self.db.unlimited_stock:
            return True, "Machine has unlimited stock - restocking not needed."
        
        current = self.db.stock_quantities.get(slot, 0)
        self.db.stock_quantities[slot] = current + quantity
        
        return True, f"Slot {slot} restocked: {current} → {current + quantity}"
    
    def set_operational(self, is_operational, message=None):
        """
        Set machine operational status (for events, maintenance, etc.).
        
        Args:
            is_operational (bool): True = working, False = broken
            message (str): Optional custom out-of-order message
        """
        self.db.is_operational = is_operational
        
        if not is_operational and message:
            self.db.out_of_order_msg = message
        
        # Notify anyone in room
        if self.location:
            if is_operational:
                self.location.msg_contents(f"|g{self.key} hums back to life.|n")
            else:
                self.location.msg_contents(f"|r{self.key} displays: {self.db.out_of_order_msg}|n")
```

**Vending Machine Examples:**

```python
# Medical Supply Vending Machine
@create/drop medstation:typeclasses.shopkeeper.VendingMachine
@desc medstation = A white vending machine with a red cross logo.
@py medstation.db.brand_name = "MediCorp AutoVend"
@py medstation.db.interface_color = "red"
@py medstation.db.slot_inventory = {
    "A1": "BANDAGE",
    "A2": "PAINKILLER",
    "A3": "BLOOD_BAG",
    "B1": "SPLINT",
    "B2": "STIMPAK"
}
@py medstation.db.unlimited_stock = False
@py medstation.db.stock_quantities = {"A1": 10, "A2": 15, "A3": 5, "B1": 8, "B2": 3}
@py medstation.db.price_multiplier = 1.3  # 30% markup

# Ammo Vending Machine (unlimited stock)
@create/drop ammodispenser:typeclasses.shopkeeper.VendingMachine
@desc ammodispenser = A reinforced military-grade ammunition dispenser.
@py ammodispenser.db.brand_name = "ArmaStock 3000"
@py ammodispenser.db.interface_color = "yellow"
@py ammodispenser.db.slot_inventory = {
    "A1": "PISTOL_AMMO",
    "A2": "RIFLE_AMMO",
    "B1": "SHOTGUN_SHELLS",
    "B2": "FRAG_GRENADE"
}
@py ammodispenser.db.unlimited_stock = True  # Never runs out
@py ammodispenser.db.price_multiplier = 2.0  # Expensive but convenient

# Food/Drink Vending Machine
@create/drop snackmachine:typeclasses.shopkeeper.VendingMachine
@desc snackmachine = A colorful vending machine filled with snacks and drinks.
@py snackmachine.db.brand_name = "Snack-O-Matic"
@py snackmachine.db.interface_color = "cyan"
@py snackmachine.db.slot_inventory = {
    "A1": "ENERGY_BAR",
    "A2": "PROTEIN_SHAKE",
    "A3": "SODA",
    "B1": "CHIPS",
    "B2": "CANDY"
}
@py snackmachine.db.price_multiplier = 1.1  # Cheap convenience items

# Builder commands for maintenance
@py medstation.set_operational(False, "MAINTENANCE IN PROGRESS")
@py medstation.restock_slot("A3", 10)  # Add 10 blood bags to A3
@py medstation.set_operational(True)
```


## Command Implementation - Phase 1

### Shop Interaction Pattern

**Phase 1 Fixed Shops**: Players use standard `look` command to interact with shop inventory:
- `look` - See room and all containers
- `look at shelf` - See items in a specific ShopContainer
- `look at machine` - See items in a vending machine
- `buy <item>` or `buy <item> from <container>` - Purchase items

**Phase 2 Marketplaces**: Adds `browse` and `sell` commands:
- `browse` - Explore marketplace stalls and vendors
- `browse <category>` - Search for specific item types
- `sell <item>` - Sell items to vendors (with haggling)
- All Phase 1 commands still work once you find a stall

**Why No Sell in Phase 1?**: Fixed shops are simple "buy-only" vendors. Selling is a Phase 2 marketplace feature that integrates with haggling mechanics and dynamic pricing.

### Buy Command

```python
# commands/economy/shop_commands.py

from evennia import Command

class CmdBuy(Command):
    """
    Purchase an item from a shop container or vending machine.
    
    Usage:
        buy <item>
        buy <item> from <container>
    
    Examples:
        buy grenade
        buy grenade from shelf
        buy A1 from machine
    """
    
    key = "buy"
    aliases = ["purchase"]
    locks = "cmd:all()"
    help_category = "Economy"
    
    def parse(self):
        """Parse 'buy <item> [from <source>]' syntax."""
        self.item_name = ""
        self.source_name = ""
        
        args = self.args.strip()
        
        # Use rsplit to handle item names containing "from"
        # e.g., "buy letter from mother from shelf" → ["buy letter from mother", "shelf"]
        if " from " in args:
            parts = args.rsplit(" from ", 1)
            self.item_name = parts[0].strip()
            self.source_name = parts[1].strip() if len(parts) > 1 else ""
        else:
            self.item_name = args
    
    def func(self):
        caller = self.caller
        
        if not self.item_name:
            caller.msg("Usage: buy <item> [from <container>]")
            return
        
        # Resolve the source container first if specified
        source = None
        if self.source_name:
            source = caller.search(self.source_name, location=caller.location)
            if not source:
                return
        
        # Check if buying from a vending machine (bypasses all shop checks)
        from world.economy.shops.containers import VendingMachine
        if source and isinstance(source, VendingMachine):
            self.buy_from_container(caller, self.item_name, source)
            return
        
        # For non-vending containers, check shop requirements
        location = caller.location
        if not location.is_shop():
            caller.msg("You need to be in a shop to buy items.")
            return
        
        # Check for merchant presence (unless shop allows unmanned sales)
        shop_config = location.db.shop_config
        allows_unmanned = shop_config.get("allows_unmanned_sales", False)
        
        if not allows_unmanned:
            # Find any merchant in room
            merchants = [obj for obj in location.contents 
                        if hasattr(obj.db, 'is_merchant') and obj.db.is_merchant]
            
            if not merchants:
                caller.msg("The shop appears to be closed. No merchant is present.")
                return
        
        if source:
            # Buy from specific container
            self.buy_from_container(caller, self.item_name, source)
        else:
            # Search all containers in room
            self.buy_from_room(caller, self.item_name)
    
    def buy_from_container(self, caller, item_name, container):
        """Buy from specific container."""
        from typeclasses.shopkeeper import ShopContainer
        
        if not isinstance(container, ShopContainer):
            caller.msg(f"{container.key} is not a shop container.")
            return
        
        # Use container's purchase method
        success, msg, item = container.purchase_item(caller, item_name)
        caller.msg(msg)
        
        if success:
            # Announce to room
            caller.location.msg_contents(
                f"{caller.key} purchases {item.key} from the {container.key}.",
                exclude=caller
            )
    
    def buy_from_room(self, caller, item_name):
        """Search all containers in room."""
        from typeclasses.shopkeeper import ShopContainer
        
        containers = [obj for obj in caller.location.contents 
                     if isinstance(obj, ShopContainer)]
        
        if not containers:
            caller.msg("There are no shops here.")
            return
        
        # Try each container
        for container in containers:
            proto = container.get_prototype_by_name(item_name)
            if proto:
                self.buy_from_container(caller, item_name, container)
                return
        
        caller.msg(f"'{item_name}' is not for sale here.")


### Sell Command (Phase 2 Only)

**Selling items is NOT available in Phase 1 fixed shops.** This feature is reserved for Phase 2 marketplaces where it will be integrated with the haggling system.

```python
# Phase 2 marketplace feature - not implemented in Phase 1
class CmdSell(Command):
    """
    Sell an item at a marketplace vendor.
    
    Usage:
        sell <item>
        sell <item> to <vendor>
        
    Note: Only works in marketplaces, not fixed shops.
    Includes haggling mechanics based on Intellect stat.
    """
    key = "sell"
    locks = "cmd:all()"
    help_category = "Economy"
    
    # Implementation deferred to Phase 2
```

## Phase 2: Marketplace System (Architecture Only)

### Procedural Marketplace Design

**NOT IMPLEMENTED YET** - This section documents the planned architecture for dynamic marketplaces in Phase 2.

```python
# world/economy/marketplaces/rooms.py (FUTURE)

class MarketplaceRoom(Room):
    """
    Special room type that reconfigures on a timer.
    Part of procedural marketplace maze.
    """
    
    def at_object_creation(self):
        """Initialize marketplace room."""
        super().at_object_creation()
        
        # Marketplace configuration
        self.db.is_marketplace = True
        self.db.marketplace_zone = "central_bazaar"  # Which marketplace this belongs to
        self.db.anchor_point = False  # True if this connects to main grid
        
        # Vendor configuration
        self.db.vendor_prototypes = []  # List of vendor templates that can spawn here
        self.db.item_prototypes = []    # List of item prototypes available in this zone
        
        # Reconfiguration
        self.db.reconfigure_interval = 3600  # 1 hour
        self.db.last_reconfigure = None
        
        # Haggling enabled
        self.db.haggling_enabled = True
        self.db.base_haggle_difficulty = 15  # Intellect check difficulty


class MarketplaceMaze:
    """
    Manager for procedurally generated marketplace layouts.
    Handles maze generation, reconfiguration, and grid anchoring.
    """
    
    # PHASE 2 - Full implementation deferred
    pass


# commands/economy/marketplace_commands.py (FUTURE)

class CmdHaggle(Command):
    """
    Negotiate price with a marketplace vendor.
    
    Usage:
        haggle <item> from <vendor>
        haggle <price> for <item> from <vendor>
    
    Uses Intellect vs vendor's Intellect in opposed roll.
    """
    
    key = "haggle"
    locks = "cmd:all()"
    help_category = "Economy"
    
    # PHASE 2 - Full implementation deferred
```

## Error Handling & Edge Cases

### Economic Constants

```python
# world/economy/constants.py

# Transaction Limits
MAX_SINGLE_PURCHASE = 1000000  # Maximum credits in single transaction
MIN_ITEM_VALUE = 1              # Minimum item value (can't be worthless)
MAX_STACK_SIZE = 999            # Maximum stackable item quantity

# Shop Configuration Limits
MAX_CONTAINERS_PER_SHOP = 20    # Prevent container spam
MAX_ITEMS_PER_CONTAINER = 100   # Prevent prototype list bloat
MIN_UPSELL_FACTOR = 0.01        # Can't sell for less than 1% of value
MAX_UPSELL_FACTOR = 100.0       # Can't charge more than 100x value

# Merchant Respawn
MIN_RESPAWN_DELAY = 60          # Minimum seconds before respawn (1 minute)
MAX_RESPAWN_DELAY = 86400       # Maximum seconds before respawn (24 hours)
DEFAULT_RESPAWN_DELAY = 300     # Default respawn delay (5 minutes)

# Vending Machine
MAX_VENDING_SLOTS = 100         # Maximum slots in vending machine (A1-J10)
```

### Error Scenarios

#### Invalid Prototype Key
```python
# In CmdBuy when spawning item
try:
    item = spawn(prototype_key)[0]
except KeyError:
    caller.msg(f"|rError: Item prototype '{prototype_key}' not found. Please report this to staff.|n")
    # Log the error
    from evennia.utils import logger
    logger.log_err(f"Shop container has invalid prototype: {prototype_key}")
    return
```

#### Corrupted MerchantTemplate
```python
# In Room.spawn_merchant()
template_key = self.db.shop_config.get("merchant_template")
if not template_key:
    from evennia.utils import logger
    logger.log_warn(f"Shop {self} has no merchant_template configured")
    return None

try:
    merchant = spawn(template_key)[0]
except KeyError:
    logger.log_err(f"Shop {self} has invalid merchant_template: {template_key}")
    return None
```

#### Multiple Merchants in Same Shop
```python
# In Room.spawn_merchant()
existing_merchants = [obj for obj in self.contents 
                     if hasattr(obj.db, 'is_merchant') and obj.db.is_merchant]

if existing_merchants:
    from evennia.utils import logger
    logger.log_warn(f"Shop {self} already has merchant(s): {existing_merchants}")
    # Delete duplicate merchants
    for merchant in existing_merchants[1:]:
        merchant.delete()
    return existing_merchants[0]
```

#### Player Has Insufficient Credits
```python
# In CmdBuy
if not caller.can_afford(final_price):
    from world.economy.constants import format_currency
    caller.msg(f"You can't afford that. You need {format_currency(final_price)} but only have {format_currency(caller.credits)}.")
    return
```

#### Item Won't Fit in Hands
```python
# In CmdBuy after spawning
hands = getattr(caller, 'hands', {})
if not hands:
    # No hands system - put in inventory
    item.move_to(caller, quiet=True)
else:
    # Try to put in empty hand
    empty_hand = None
    for hand, held in hands.items():
        if held is None:
            empty_hand = hand
            break
    
    if empty_hand:
        hands[empty_hand] = item
        item.move_to(caller, quiet=True)
    else:
        # Hands full - put in inventory
        item.move_to(caller, quiet=True)
        caller.msg(f"|yYour hands are full. {item.key} is in your inventory.|n")
```

#### Container Deleted While Shop Active
```python
# In ShopContainer.at_object_delete()
def at_object_delete(self):
    """Clean up shop references when container is deleted."""
    location = self.location
    if location and location.is_shop():
        from evennia.utils import logger
        logger.log_warn(f"ShopContainer {self} deleted from shop {location}")
        # Shop remains functional with other containers
```

#### Merchant Death During Transaction
```python
# In CmdBuy
# This is actually fine - transaction completes anyway
# Buy command doesn't require merchant, only the container

# In CmdSell
# Also fine - we check for merchant presence and adjust messaging
if merchant:
    # Normal transaction with merchant
    pass
else:
    # Transaction with absent merchant (leave item on counter)
    pass
```

#### Holographic Merchant Attack
```python
# In Character.validate_attack_target() for holographic merchants
# Called by CmdAttack before combat initiation
def validate_attack_target(self):
    """Prevent attacks on holographic merchants."""
    if getattr(self.db, 'is_holographic', False):
        return "A holographic merchant cannot be attacked - target validation failed"
    return None  # None means valid target

# In CmdAttack.func() after target resolution:
# validation_error = target.validate_attack_target()
# if validation_error:
#     caller.msg(f"|yYour attack passes through {target.key}'s holographic form with a shimmer of static.|n")
#     target.location.msg_contents(
#         f"|y{caller.key}'s attack passes through {target.key}'s flickering projection.|n",
#         exclude=[caller, target]
#     )
#     return  # Abort attack before combat handler involvement
```

### Validation Helpers

```python
# world/economy/shops/validation.py

from world.economy.constants import (
    MIN_UPSELL_FACTOR, MAX_UPSELL_FACTOR,
    MIN_RESPAWN_DELAY, MAX_RESPAWN_DELAY
)

def validate_shop_config(config):
    """Validate shop configuration dictionary."""
    errors = []
    
    # Check required fields
    if 'shop_name' not in config:
        errors.append("Missing required field: shop_name")
    
    # Validate upsell factor
    upsell = config.get('upsell_factor', 1.0)
    if not (MIN_UPSELL_FACTOR <= upsell <= MAX_UPSELL_FACTOR):
        errors.append(f"upsell_factor must be between {MIN_UPSELL_FACTOR} and {MAX_UPSELL_FACTOR}")
    
    # Validate respawn delay
    if 'merchant_respawn_delay' in config:
        delay = config['merchant_respawn_delay']
        if not (MIN_RESPAWN_DELAY <= delay <= MAX_RESPAWN_DELAY):
            errors.append(f"merchant_respawn_delay must be between {MIN_RESPAWN_DELAY} and {MAX_RESPAWN_DELAY}")
    
    return errors

def validate_container_inventory(prototype_list):
    """Validate container's prototype inventory list."""
    from world.economy.constants import MAX_ITEMS_PER_CONTAINER
    from evennia.prototypes.prototypes import search_prototype
    
    if len(prototype_list) > MAX_ITEMS_PER_CONTAINER:
        return [f"Container has {len(prototype_list)} items (max {MAX_ITEMS_PER_CONTAINER})"]
    
    errors = []
    for prototype_key in prototype_list:
        # Check if prototype exists
        result = search_prototype(prototype_key)
        if not result:
            errors.append(f"Invalid prototype key: {prototype_key}")
    
    return errors
```

## Builder Workflow - Phase 1 (ACTUAL IMPLEMENTATION)

### Setting Up a Shop

**Step 1: Create ShopContainer**

```python
# Create a shop container (not room-based)
@create/drop shop:typeclasses.shopkeeper.ShopContainer

# Set description
@desc shop = A well-stocked shop shelf displaying various items.

# Set shop name (for purchase messages)
@py shop.db.shop_name = "Juan's Corner Market"
```

**Step 2: Add Items to Inventory**

```python
# Add items using their prototype keys
@py shop.add_prototype("SPRAYPAINT_CAN", 50)
@py shop.add_prototype("SPRAY_SOLVENT", 30)
@py shop.add_prototype("MACHETE", 150)
@py shop.add_prototype("FRAG_GRENADE", 200)

# Check what's in stock
@py shop.db.prototype_inventory
# Output: {"SPRAYPAINT_CAN": 50, "SPRAY_SOLVENT": 30, "MACHETE": 150, "FRAG_GRENADE": 200}
```

**Step 3: (Optional) Customize Purchase Messages**

```python
# Customize buyer message
@py shop.db.purchase_msg_buyer = "|gExcellent choice!|n You purchase {item} for {price}."

# Customize room message
@py shop.db.purchase_msg_room = "{buyer} haggles with Juan before purchasing {item}."

# Available placeholders: {buyer}, {item}, {price}, {shop}
```

**Step 4: Spawn Merchant (Optional)**

```python
# Spawn a holographic merchant from prototypes
@spawn CORNERSTORE_MERCHANT

# Or spawn directly with attributes
@spawn {"prototype_parent": "BASE_NPC", "key": "Juan Sanchez", "typeclass": "typeclasses.characters.Character", "attrs": [("is_merchant", True), ("is_holographic", True)]}

# Merchant will be invulnerable to attacks (holographic protection)
```

**Step 5: Give Players Tokens**

```python
# Give tokens to a player
@py me.tokens = 500

# Check current tokens
@py me.tokens
# Output: 500
```

### Complete Shop Setup Example

```python
# Create cornerstore in current room
@create/drop shop:typeclasses.shopkeeper.ShopContainer
@desc shop = A worn wooden shelf stocked with everyday necessities.
@py shop.db.shop_name = "Juan's Corner Market"
@py shop.db.container_type = "shelf"

# Stock the shop
@py shop.add_prototype("SPRAYPAINT_CAN", 50)
@py shop.add_prototype("SPRAY_SOLVENT", 30) 
@py shop.add_prototype("MACHETE", 100)
@py shop.add_prototype("KEVLAR_VEST", 300)

# Customize messages
@py shop.db.purchase_msg_buyer = "|gGracias, amigo!|n You purchase {item} for {price}."
@py shop.db.purchase_msg_room = "{buyer} buys {item} from Juan's shop."

# Spawn merchant
@spawn CORNERSTORE_MERCHANT

# Give yourself tokens to test
@py me.tokens = 1000

# Test the shop
look shop
buy spraypaint from shop
```

### Quick Reference Commands

```python
# View shop inventory
look shop

# Buy item (fuzzy matching)
buy spraypaint from shop
buy can of spraypaint from shop
buy solvent from shop

# Check your tokens
@py me.tokens

# Give tokens
@py me.tokens += 500

# Remove tokens
@py me.tokens -= 100

# Check if you can afford something
@py me.tokens >= 50  # Returns True/False
```

### Holographic Merchant Testing

```python
# Spawn holographic merchant
@spawn HOLOGRAPHIC_MERCHANT

# Try to attack it (will fail with glitch message)
attack merchant

# Output: Your attack passes through merchant's holographic form!
```

## Integration with Existing Systems (ACTUAL)

### Character Integration

```python
# typeclasses/characters.py

class Character(LivingMixin, DefaultCharacter):
    """Character with shop/currency support."""
    
    # AttributeProperties for automatic initialization
    tokens = AttributeProperty(0, category="shop", autocreate=True)
    is_merchant = AttributeProperty(False, category="shop", autocreate=True)
    is_holographic = AttributeProperty(False, category="shop", autocreate=True)
    
    def validate_attack_target(self, attacker):
        """Check if character can be attacked (holographic protection)."""
        if self.is_holographic:
            attacker.msg(f"|cYour attack passes through {self.key}'s holographic form!|n")
            attacker.location.msg_contents(
                f"|c{attacker.key}'s attack phases harmlessly through {self.key}!|n",
                exclude=[attacker]
            )
            return (False, None)
        return (True, None)
```

### Prototype Integration

All items in `world/prototypes.py` can be sold in shops:

```python
# Example: Items with value attributes
SPRAYPAINT_CAN = {
    "key": "can of spraypaint",
    "typeclass": "typeclasses.items.AerosolCan",
    "attrs": [
        ("value", 50),           # Used for shop pricing
        ("aerosol_contents", "spraypaint"),  # Used for display name
        ("spray_range", 10),
        ("spray_duration", 5)
    ]
}

# Shop references by prototype key
shop.add_prototype("SPRAYPAINT_CAN", 50)  # Sell for 50₮
```

### Combat Integration

Holographic merchants are protected via `validate_attack_target()`:

```python
# In CmdAttack (commands/combat/core_actions.py)
if hasattr(target, 'validate_attack_target'):
    can_attack, error_msg = target.validate_attack_target(caller)
    if not can_attack:
        if error_msg:
            caller.msg(error_msg)
        return  # Attack prevented
```

### Hands System Integration

Purchased items auto-wield in hands if available:

```python
# In CmdBuy._give_item_to_buyer()
if hasattr(buyer, 'wield_item'):
    buyer.wield_item(item)  # Automatically equips in hands
else:
    # Fallback if no hands system
    item.location = buyer
```

## Testing Checklist - Phase 1 (ACTUAL)

### Core Functionality
- [x] Currency system works (tokens AttributeProperty with default 0)
- [x] ShopContainer displays prototype inventory correctly
- [x] Items spawn correctly from prototypes on purchase
- [x] Pricing uses prototype value attributes
- [x] Buy command works with fuzzy item name matching
- [x] Dynamic display names work (cans use aerosol_contents)
- [x] Purchased items appear in hands system
- [x] Purchase messages are customizable per container
- [x] Token deduction works correctly

### Merchant System
- [x] Holographic merchants are invulnerable (attacks pass through)
- [x] Merchants spawn from regular prototypes (@spawn HOLOGRAPHIC_MERCHANT)
- [x] is_merchant and is_holographic flags work via AttributeProperties
- [x] Combat system respects holographic protection

### Builder Workflow
- [x] Can create shops with @create and @py commands
- [x] Can add items with shop.add_prototype(key, price)
- [x] Can customize purchase messages
- [x] Can spawn merchants with @spawn
- [x] Can give tokens with char.tokens = amount
- [x] Look at shop shows formatted inventory

### Edge Cases
- [x] Handles None vs 0 tokens correctly (AttributeProperty default)
- [x] Items spawn to correct location (explicit item.location = buyer)
- [x] Wield integration works correctly
- [x] Multiple items with same base name distinguished (cans)
- [x] Free items (0₮) display correctly

### NOT Implemented in Phase 1
- [ ] Room-based shop configuration (original spec)
- [ ] MerchantTemplate system (original spec)
- [ ] Merchant respawning (original spec)
- [ ] Merchant attendance requirement (shops are self-service)
- [ ] Merchant interactions (greetings, dialogue, reactions)
- [ ] Merchant AI/personality scripts
- [ ] Vending machines (original spec)
- [ ] Limited stock mode (infinite only)
- [ ] Dynamic pricing/haggling
- [ ] Marketplace mazes
- [ ] Player-owned shops

## Future Phases (NOT IMPLEMENTED)

### Phase 2 - Marketplaces (Future)
- [ ] Marketplace rooms reconfigure on timers
- [ ] Maze generation connects to grid anchor points
- [ ] Haggling system with Intellect checks
- [ ] Browse command for marketplace exploration
- [ ] Sell command for selling items to vendors (marketplace-only feature)
- [ ] Dynamic pricing based on rarity queries
- [ ] Vendor spawning in marketplace zones

## Future Enhancements (Phase 3+)

1. **Player-Owned Shops**: Lease systems, revenue collection
2. **Economic Simulation**: Supply/demand tracking, price volatility
3. **Crafting Integration**: Merchants can craft custom items
4. **Shop Upgrades**: Expand inventory, improve prices
5. **Shop Events**: Sales, limited-time items
6. **Black Market**: Illegal items with risk mechanics
7. **Reputation System**: Discounts for loyal customers
8. **Auction Houses**: Timed bidding on rare items

---

*This specification provides the foundation for a container-based shop system with template-driven merchants and clear paths for future expansion into dynamic marketplaces and player ownership.*
