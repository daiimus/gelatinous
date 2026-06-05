"""Look-place fragments for spawned rats.

Where in the room the rat is, paired into ``mob.look_place`` for
``$pron()``-style integration into the appearance composition.
Each entry should be a complete sentence ending in terminal
punctuation. Reads after the short-desc paragraph as positional
detail — "It is here, doing X" — so phrasings should fit that
slot naturally.
"""

from __future__ import annotations

LOOK_PLACES_RAT: list[str] = [
    "It is perched on a low ledge with its tail curled around its body.",
    "It crouches in the shadow at the base of the wall, nose twitching.",
    "It skitters along the baseboard with quick small bursts of motion.",
    "It sits up on its hindlegs and watches with bright unblinking attention.",
    "It is sniffing at something invisible on the ground, whiskers fanning.",
    "It darts a short distance and freezes again, head cocked.",
    "It washes one forepaw with quick precise licks, never breaking eye contact.",
    "It grooms its whiskers with both forepaws, ears swiveling at every sound.",
    "It is half-hidden behind something, only its bright eyes catching the light.",
    "It moves in cautious arcs through the room, never quite committing to a path.",
    "It rests on all fours with its head low, ready to spring in any direction.",
    "It pauses mid-step with one forepaw raised, listening.",
]
