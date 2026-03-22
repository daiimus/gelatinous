"""
Combat System Package

This package contains the refactored combat system for Evennia,
organized following Python best practices while maintaining
Evennia conventions and backward compatibility.

Main modules:
- constants: All combat-related constants and configuration
- utils: Shared utility functions for combat operations
- handler: Main combat handler script (refactored combathandler.py)
- proximity: Proximity management logic
- grappling: Grappling-specific operations
- messages: Combat message system
"""

# Re-export key functions for backward compatibility
from world.combat.handler import get_or_create_combat
from world.combat.constants import COMBAT_SCRIPT_KEY

# Re-export messages for backward compatibility  
from world.combat.messages import get_combat_message

__all__ = [
    "get_or_create_combat",
    "COMBAT_SCRIPT_KEY", 
    "get_combat_message",
]
