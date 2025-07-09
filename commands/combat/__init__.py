"""
Combat Commands Package

This package contains all combat-related commands organized into logical modules
following Python best practices and Evennia conventions. Commands are split
by functionality for better maintainability and testing.

Module Organization:
- core_actions.py: attack, defend, yield, stop commands
- movement.py: flee, retreat, advance, charge commands
- special_actions.py: grapple, disarm, aim commands
- info_commands.py: look (combat-specific behavior)

All commands maintain backward compatibility while providing improved
organization and readability.
"""

# Import all commands for backward compatibility
from .core_actions import CmdAttack, CmdStop
from .movement import CmdFlee, CmdRetreat, CmdAdvance, CmdCharge
from .special_actions import CmdGrapple, CmdEscapeGrapple, CmdReleaseGrapple, CmdDisarm, CmdAim
from .info_commands import CmdLook

__all__ = [
    # Core actions
    "CmdAttack", "CmdStop",
    # Movement
    "CmdFlee", "CmdRetreat", "CmdAdvance", "CmdCharge", 
    # Special actions
    "CmdGrapple", "CmdEscapeGrapple", "CmdReleaseGrapple", "CmdDisarm", "CmdAim",
    # Info
    "CmdLook"
]
