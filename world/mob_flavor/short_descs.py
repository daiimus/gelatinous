"""Short-description templates for randomly-spawned mobs.

These populate ``mob.db.desc`` — the main paragraph an observer sees on
``look <mob>``, woven into the appearance composition before per-location
longdescs are appended. Each entry should:

* Read as one or two sentences of *whole-body* impression — bearing, gait,
  affect, vibe. Per-part anatomy lives in ``longdescs.py``; don't restate
  it here.
* Use ``{their}`` / ``{they}`` / ``{them}`` / ``{themselves}`` for pronouns
  so the same entry reads correctly for any apparent gender.
* Avoid naming the mob's height/build/hair — those axes are randomized
  separately by the identity system and surfaced via the sdesc.
* Avoid setting-specific scenery so the entry works in any room.
"""

from __future__ import annotations

SHORT_DESCS: list[str] = [
    "A body that has worked, and worked hard. {Their} bearing speaks of long hours, short breaks, and shorter patience.",
    "There is a stillness to {them} — the kind a person practices because the alternative is worse.",
    "{They} carry {themselves} like someone who has learned the cost of being noticed.",
    "Something in the set of {their} shoulders suggests the day already started badly and is in no hurry to improve.",
    "{They} move with the quiet economy of someone who has learned not to waste a step.",
    "There is the look of recent sleeplessness about {them}, partly hidden and partly worn like a badge.",
    "A faint chemical tang clings to {their} skin — solvent, smoke, or something the recyclers cannot quite scrub out.",
    "{They} stand a little crookedly, as though one side of {them} is permanently bracing for impact.",
    "{Their} every motion suggests a person counting their breaths between obligations.",
    "There's a thin film of grit on {their} skin that no shower in the colony seems able to dislodge.",
    "{They} have the alert, narrow attention of someone who has been jumped before and intends to make it the last time.",
    "A persistent low hum of nervous energy comes off {them}, like a wire pulled tight.",
    "{They} carry {themselves} with the practiced indifference of someone who refuses to show what {they} actually think.",
    "{Their} skin has been mended more times than has been washed — scars layered on scars.",
    "There's a smell of recycled air and old sweat about {them}, the colony's perfume.",
    "{Their} hands are never quite still, even when the rest of {them} is.",
    "{They} look like {they} could disappear at any moment and nobody would remember exactly when.",
    "A faint sourness on {their} breath suggests {their} last meal was a long time ago, or a bad one.",
    "{They} stand the way a person stands when they have nowhere in particular to be and nowhere to go back to.",
    "Something in {their} expression has settled — not quite peace, more like a treaty that has held for a while.",
    "{They} move like someone who has been told too many times to stand straighter, and has stopped listening.",
    "A faint sheen of sweat clings to {their} brow that has nothing to do with the room's temperature.",
    "{Their} attention drifts to the corners of the room and stays there, as if checking.",
    "{They} look unfinished, as though parts of {them} are still being decided.",
    "There is a quiet, watchful patience to {them}, the kind cultivated by people who outlast their problems.",
    "The colony has done its work on {them}: nothing dramatic, just a thousand small subtractions.",
    "{They} look at the room the way someone looks at a road they have walked too many times.",
    "Something about {them} suggests {they} have been trying to get clean for a while, and is mostly succeeding.",
    "{Their} bearing is that of someone who has lost an argument with the world and is still drafting their next response.",
    "{They} stand as if listening for a sound only {they} can hear, and not enjoying it.",
    "A slow, deliberate calm rolls off {them}, the kind that has cost something to earn.",
    "{Their} eyes do not quite settle, as though every surface is asking {them} a question.",
    "{They} have the loose, careless posture of someone too tired to perform anything.",
    "There is a softness to {their} face that the rest of {them} seems to be working very hard to contradict.",
    "{They} look freshly sleeved, all the small uncertainties still showing.",
    "{Their} body language belongs to a person who has spent a lot of time being looked at and would prefer to stop.",
    "{They} move in small, considered gestures, as if conserving something difficult to replace.",
    "A faint medicinal smell hangs around {them}, suggesting recent visits to the wrong kind of clinic.",
    "There is a deliberate slowness to {their} reactions, like someone pacing {themselves} through a long shift.",
    "{Their} expression suggests {they} are mid-thought about something {they} would rather not finish.",
    "{They} stand as though the floor might tilt at any moment, weight always slightly forward.",
    "A streak of something dark — grease, ash, blood — runs along the line of {their} jaw, half-noticed.",
    "{They} have the look of someone whose hair was last combed in the dark and has not been told otherwise.",
    "{They} carry the kind of silence that makes other people fill it.",
    "{Their} hands hang at {their} sides as though waiting to be told what to do with {themselves}.",
    "{They} look like {they} have been promising {themselves} a long sit-down for several days.",
    "There is an absent, half-finished look to {them}, like a person walking themselves through a checklist nobody else can see.",
    "{They} carry the weight of someone who has not laughed at anything in a while and is no longer sure {they} remember how.",
    "{They} are watching everything and admitting nothing.",
    "{Their} stillness has the alert quality of an animal that has been startled too often to startle easily.",
    "{They} look as if {they} have been waiting a long time for something to happen — and might wait a great deal longer.",
    "{They} have the air of a person who has been told too many bad jokes today and is no longer pretending.",
    "{They} hold {themselves} as though every joint is reporting a slightly different complaint.",
    "{They} carry the slightly rumpled look of someone who slept somewhere unintended.",
    "The colony's lighting catches {them} unevenly, doing them no favors.",
    "{They} stand as though {they} have not yet decided whether this room counts as a problem.",
]
