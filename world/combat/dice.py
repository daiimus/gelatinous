"""
Combat Dice Rolling & Stat Access

Pure functions for rolling dice against character stats.  These have no
side-effects (no logging, no state mutation) and depend only on
``random`` and ``constants``.

Extracted from ``world/combat/utils.py`` during Phase 2 refactoring.

Functions:
    get_character_stat — safe stat value retrieval with fallback
    roll_stat — single die roll against a character's stat
    opposed_roll — opposed roll between two characters
    roll_with_advantage — roll twice, take higher
    roll_with_disadvantage — roll twice, take lower
    standard_roll — single roll with consistent tuple interface
"""

from __future__ import annotations

from random import randint

from .constants import DEFAULT_MOTORICS, MIN_DICE_VALUE


# ------------------------------------------------------------------
# Stat access
# ------------------------------------------------------------------

def get_character_stat(character, stat_name: str, default: int = 1) -> int:
    """
    Safely get a character's stat value with fallback to *default*.

    Args:
        character: The character object.
        stat_name: Name of the stat (e.g. ``"motorics"``, ``"grit"``).
        default: Default value if stat is missing or invalid.

    Returns:
        The stat value, guaranteed to be a positive integer.
    """
    stat_value = getattr(character, stat_name, default)

    # Ensure it's a valid number
    if not isinstance(stat_value, (int, float)) or stat_value < 1:
        return default

    return int(stat_value)


# ------------------------------------------------------------------
# Rolling
# ------------------------------------------------------------------

def roll_stat(character, stat_name: str, default: int = DEFAULT_MOTORICS) -> int:
    """
    Roll a die based on a character's stat value.

    Args:
        character: The character object.
        stat_name: Name of the stat to roll against.
        default: Default stat value if missing.

    Returns:
        Random value from 1 to *stat_value*.
    """
    stat_value = get_character_stat(character, stat_name, default)
    return randint(MIN_DICE_VALUE, max(MIN_DICE_VALUE, stat_value))


def opposed_roll(
    char1,
    char2,
    stat1: str = "motorics",
    stat2: str = "motorics",
) -> tuple[int, int, bool]:
    """
    Perform an opposed roll between two characters.

    Args:
        char1: First character.
        char2: Second character.
        stat1: Stat name for *char1*.
        stat2: Stat name for *char2*.

    Returns:
        ``(char1_roll, char2_roll, char1_wins)`` — ties favour the
        defender (*char2*).
    """
    roll1 = roll_stat(char1, stat1)
    roll2 = roll_stat(char2, stat2)

    return roll1, roll2, roll1 > roll2


def roll_with_advantage(stat_value: int) -> tuple[int, int, int]:
    """
    Roll with advantage: roll twice, take the higher result.

    Args:
        stat_value: The stat value to roll against.

    Returns:
        ``(final_roll, roll1, roll2)`` for debugging.
    """
    roll1 = randint(1, max(1, stat_value))
    roll2 = randint(1, max(1, stat_value))
    final_roll = max(roll1, roll2)
    return final_roll, roll1, roll2


def roll_with_disadvantage(stat_value: int) -> tuple[int, int, int]:
    """
    Roll with disadvantage: roll twice, take the lower result.

    Args:
        stat_value: The stat value to roll against.

    Returns:
        ``(final_roll, roll1, roll2)`` for debugging.
    """
    roll1 = randint(1, max(1, stat_value))
    roll2 = randint(1, max(1, stat_value))
    final_roll = min(roll1, roll2)
    return final_roll, roll1, roll2


def standard_roll(stat_value: int) -> tuple[int, int, int]:
    """
    Standard single roll.

    Args:
        stat_value: The stat value to roll against.

    Returns:
        ``(final_roll, roll, roll)`` for a consistent interface with
        advantage/disadvantage variants.
    """
    roll = randint(1, max(1, stat_value))
    return roll, roll, roll
