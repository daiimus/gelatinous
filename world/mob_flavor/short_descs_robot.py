"""Short-description templates for randomly-spawned robots.

Whole-body impressions of a humanoid machine. Per-part anatomy lives in
``longdescs_robot.py``. Same token conventions as the human module —
pronoun substitutions resolve per-observer, braced verbs flex for
number/gender (robots spawn neutral, so ``{They}``/``{their}`` render as
they/their).
"""

from __future__ import annotations

SHORT_DESCS_ROBOT: list[str] = [
    "{They} {are} a humanoid machine, joints articulating with a faint servo whine at every shift of weight.",
    "{Their} chassis is scuffed and work-worn, the painted designation long since rubbed to bare alloy.",
    "There is a deliberate, unhurried economy to the way {they} {move} — nothing wasted, nothing rushed.",
    "A row of status indicators glows along {their} collar line, pulsing in slow patient sequence.",
    "{They} {hold} {themselves} with the motionless poise of something that does not tire and does not fidget.",
    "{Their} optics track movement in small mechanical increments, the lenses refocusing with a faint click.",
    "Coolant lines trace visible conduits beneath {their} plating, ticking softly as the frame sheds its heat.",
    "{They} {stand} squarely balanced, the low hydraulic hiss of {their} frame the only sign {they} {are} powered.",
    "{Their} movements carry the slight latency of a machine thinking a half-second before it acts.",
    "Servos compensate audibly as {they} {shift} stance, the whole frame settling with mechanical precision.",
    "{They} {are} built broad and functional, every panel seam and fastener left honestly exposed.",
    "A faint ozone smell hangs around {them}, the signature of hardworked actuators and warm circuitry.",
    "{They} {regard} the room with the flat unblinking attention of a sensor suite that never looks away.",
    "{Their} frame bears the dents and weld-scars of long service, repaired more than once and never prettily.",
    "{They} {move} with the heavy certainty of something that outmasses most of what shares the room with it.",
]
