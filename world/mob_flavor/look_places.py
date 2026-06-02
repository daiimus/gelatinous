"""Look-place templates for randomly-spawned mobs.

Each string is consumed as ``look_place`` and rendered by the room appearance
system as ``<Name> <look_place>`` (e.g. "Vasquez is leaning against the wall.").
Entries should:

* Begin with the verb phrase (no leading "is" — the renderer supplies the
  copula via the existing ``standing here.`` convention).
* End with a period.
* Avoid naming specific scenery the room may not have (no "leaning on the
  bar" — that breaks in a cargo bay).
* Read as a neutral *posture or activity* a stranger could be doing in any
  room of the colony.
"""

from __future__ import annotations

LOOK_PLACES: list[str] = [
    "standing here.",
    "standing with arms folded.",
    "standing slightly off to one side.",
    "standing with hands clasped behind the back.",
    "standing with weight shifted onto one leg.",
    "loitering with no apparent purpose.",
    "leaning against the nearest wall.",
    "leaning back, hands jammed against their hips.",
    "leaning forward, watching everything at once.",
    "slouching against a flat surface.",
    "rocking slowly on the balls of their feet.",
    "shifting weight from foot to foot, restless.",
    "pacing in a slow, narrow circuit.",
    "pacing the perimeter without seeming to notice.",
    "walking the edges of the room.",
    "standing dead still, eyes tracking the room.",
    "standing motionless, breath shallow.",
    "sitting on the nearest available surface.",
    "sitting hunched forward, elbows on knees.",
    "sitting cross-legged on the floor.",
    "sitting with legs sprawled out, unbothered.",
    "perched on the corner of something solid.",
    "crouched low, eyes scanning.",
    "crouched, idly drawing patterns on the floor.",
    "squatting on their heels, patient.",
    "kneeling on one knee, half-watching the room.",
    "lying flat on the floor, staring at the ceiling.",
    "stretched out, arms behind their head.",
    "lounging in whatever counts for comfort here.",
    "draped over the nearest surface like a question mark.",
    "hunkered down with their back to a wall.",
    "tucked into a corner, half in shadow.",
    "hovering near the exits, not quite committed.",
    "lingering by the door with no clear intent.",
    "blocking the doorway without meaning to.",
    "standing too close to the threshold to be casual.",
    "standing in the middle of the room like furniture.",
    "rooted in place, refusing to move.",
    "shuffling in slow circles, talking to nobody.",
    "standing with one hand braced on something nearby.",
    "balanced on the edge of moving and not moving.",
    "watching the room with practiced disinterest.",
    "scanning the room with eyes that do not stop.",
    "appearing to study the floor with serious intent.",
    "appearing to count the ceiling tiles.",
    "muttering at something only they can see.",
    "humming quietly to no one in particular.",
    "wiping their hands on their thighs, over and over.",
    "running fingers through their hair, distracted.",
    "cracking their knuckles, one at a time.",
    "stretching their neck in slow, deliberate rolls.",
    "rolling their shoulders as if working out a knot.",
    "rubbing the bridge of their nose, tired.",
    "running a thumb absently across the opposite palm.",
    "scratching idly at the inside of one wrist.",
    "picking at something on the back of their own hand.",
    "drumming fingers on whatever is nearest.",
    "tapping a slow, irregular rhythm with one foot.",
    "yawning into the back of their hand.",
    "swaying gently, as though half-asleep.",
    "blinking very slowly at the middle distance.",
    "staring at nothing in particular for too long.",
    "watching the air as though it might do something.",
]
