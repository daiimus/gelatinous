"""Look-place fragments for spawned robots.

Each string is consumed as ``mob.look_place`` and rendered by the room
appearance system as ``<Name> is <look_place>`` (e.g. "A battered
security robot is standing sentry against the wall.").  Entries should:

* Begin with the verb/adjective phrase — *not* a leading "It is" / "It
  [verb]", which the renderer supplies the copula for.
* End with a period.
* Read as something a humanoid machine would plausibly be doing in any
  room of the colony.

Mirrors the contract in ``look_places.py`` for human mobs.
"""

from __future__ import annotations

LOOK_PLACES_ROBOT: list[str] = [
    "standing sentry against the wall, optics sweeping the room in slow arcs.",
    "powered down to an idle, status lights pulsing a slow amber.",
    "rotating its head in measured increments to track every movement.",
    "planted squarely in the open, servos ticking as it holds position.",
    "running a slow diagnostic, panel lights cascading along its forearm.",
    "standing motionless, the faint hiss of its coolant cycle the only sound.",
    "scanning the room with a thin sweep of sensor light.",
    "shifting its weight from one foot to the other with a soft hydraulic sigh.",
    "waiting with the flat patience of a machine left on standby.",
    "tracking a passerby, lenses refocusing with a series of faint clicks.",
    "holding a corner with its back to the wall, arms loose at its sides.",
    "venting a thin wisp of heat from a grille along its spine.",
]
