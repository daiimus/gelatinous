"""Look-place fragments for spawned rats.

Each string is consumed as ``mob.look_place`` and rendered by the
room appearance system as ``<Name> is <look_place>`` (e.g. "A
wiry sleek rat is perched on a low ledge.").  Entries should:

* Begin with the verb phrase or adjective phrase — *not* a leading
  "It is" / "It [verb]", which the renderer supplies the copula
  for and otherwise produces "A rat is It is sniffing...".
* End with a period.
* Read as something a small rodent would plausibly be doing in
  any room of the colony.

Mirrors the contract in ``look_places.py`` for human mobs.
"""

from __future__ import annotations

LOOK_PLACES_RAT: list[str] = [
    "perched on a low ledge with its tail curled around its body.",
    "crouched in the shadow at the base of the wall, nose twitching.",
    "skittering along the baseboard with quick small bursts of motion.",
    "sitting up on its hindlegs and watching with bright unblinking attention.",
    "sniffing at something invisible on the ground, whiskers fanning.",
    "darting a short distance and freezing again, head cocked.",
    "washing one forepaw with quick precise licks, never breaking eye contact.",
    "grooming its whiskers with both forepaws, ears swiveling at every sound.",
    "half-hidden behind something, only its bright eyes catching the light.",
    "moving in cautious arcs through the room, never quite committing to a path.",
    "resting on all fours with its head low, ready to spring in any direction.",
    "pausing mid-step with one forepaw raised, listening.",
]
