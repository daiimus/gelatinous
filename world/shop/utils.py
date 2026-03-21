"""
Utility functions for the shop system.

Includes prototype value extraction and currency formatting helpers.
"""


def get_prototype_value(prototype, attr_name, default=None):
    """
    Extract attribute value from prototype's attrs list.
    
    Evennia prototypes store attributes in an attrs list like:
    [("value", 50), ("weight", 2), ...]
    
    This helper safely extracts values from that structure.
    
    Args:
        prototype (dict): Prototype dictionary with 'attrs' key
        attr_name (str): Name of attribute to extract
        default: Default value if attribute not found
        
    Returns:
        The attribute value, or default if not found
        
    Example:
        >>> proto = spawner.spawn("rusty_sword")[0].prototype
        >>> value = get_prototype_value(proto, "value", 0)
        >>> # Returns 50 if prototype has ("value", 50) in attrs
    """
    attrs = prototype.get("attrs", [])
    for attr_tuple in attrs:
        if len(attr_tuple) >= 2 and attr_tuple[0] == attr_name:
            return attr_tuple[1]
    return default


def format_currency(amount):
    """
    Format currency amount with token symbol.
    
    Args:
        amount (int): Number of tokens
        
    Returns:
        str: Formatted currency string like "50₮" or "1₮"
        
    Example:
        >>> format_currency(50)
        '50₮'
        >>> format_currency(1)
        '1₮'
    """
    return f"{amount}₮"


def parse_currency(text):
    """
    Parse currency amount from text.
    
    Accepts formats:
    - "50" -> 50
    - "50₮" -> 50
    - "50 tokens" -> 50
    - "50 ticks" -> 50
    
    Args:
        text (str): Text containing currency amount
        
    Returns:
        int: Parsed amount, or None if invalid
        
    Example:
        >>> parse_currency("50₮")
        50
        >>> parse_currency("100 tokens")
        100
        >>> parse_currency("invalid")
        None
    """
    if not text:
        return None
        
    # Remove common currency terms
    text = text.lower().strip()
    for term in ["₮", "tokens", "token", "ticks", "tick", "tabs", "tab", "kennys", "kenny"]:
        text = text.replace(term, "").strip()
    
    # Try to parse as integer
    try:
        return int(text)
    except ValueError:
        return None


def calculate_shop_price(base_value, markup_percent=0):
    """
    Calculate shop price with markup.
    
    Args:
        base_value (int): Base item value from prototype
        markup_percent (int): Markup percentage (0-100+)
        
    Returns:
        int: Final price after markup
        
    Example:
        >>> calculate_shop_price(100, 20)  # 20% markup
        120
        >>> calculate_shop_price(50, 0)    # No markup
        50
    """
    markup = int(base_value * (markup_percent / 100.0))
    return base_value + markup


def validate_purchase(buyer, price):
    """
    Validate if buyer can afford purchase.
    
    Args:
        buyer: Character object with db.tokens
        price (int): Cost of item
        
    Returns:
        tuple: (bool, str) - (success, error_message)
        
    Example:
        >>> success, msg = validate_purchase(character, 50)
        >>> if not success:
        ...     character.msg(msg)
        ...     return
    """
    buyer_tokens = buyer.db.tokens if buyer.db.tokens is not None else 0
    
    if buyer_tokens < price:
        shortage = price - buyer_tokens
        return False, f"You need {format_currency(shortage)} more to afford that."
    
    return True, ""


def deduct_tokens(character, amount):
    """
    Safely deduct tokens from character.
    
    Args:
        character: Character object
        amount (int): Amount to deduct
        
    Returns:
        bool: True if successful, False if insufficient funds
    """
    current = character.db.tokens if character.db.tokens is not None else 0
    if current < amount:
        return False
    character.db.tokens = current - amount
    return True


def add_tokens(character, amount):
    """
    Safely add tokens to character.
    
    Args:
        character: Character object
        amount (int): Amount to add
    """
    current = character.db.tokens if character.db.tokens is not None else 0
    character.db.tokens = current + amount
