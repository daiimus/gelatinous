"""
Crowd system message pools (parallels the weather system architecture).

These are ambient, perception-gated observations about the people sharing a
room. The guiding principle is to OFFER something to observe, not to tell the
player how to feel about it: concrete behaviour, sound, and the physical facts
of a crowd, left open enough that the player draws their own conclusions. A
packet passing between two figures, a conversation that stops when footsteps
approach -- the menace is in the fact, not in the narrator naming it.
"""

# Crowd level intensity mapping
CROWD_INTENSITY = {
    0: 'none',      # No crowd messages
    1: 'sparse',    # A few people, room to move, quiet enough to notice them
    2: 'moderate',  # A working crowd, transactions and steady motion
    3: 'heavy',     # Dense, a slow press of bodies and a wall of noise
    4: 'packed',    # A crush; the crowd moves as one mass
}

CROWD_MESSAGES = {
    'default': {
        'sparse': {
            'visual': [
                "a lone figure waits in a doorway, watching nothing in particular",
                "someone leans against the wall, taking in the street without fixing on anyone",
                "a worker passes in stained coveralls, eyes down, moving fast",
                "someone counts a thin handful of chits, then pockets them",
                "a figure pauses at the corner, checks both directions, and moves on",
                "two people talk low and stop when footsteps come near",
                "someone shifts a bag higher on their shoulder and keeps walking",
                "a vendor sits behind a half-empty cart, in no hurry for custom",
                "a figure lingers under a dead light fixture, face in shadow",
                "someone steps wide around a patch of grating they clearly know to avoid",
                "two workers share a cigarette they don't seem to enjoy",
                "a person stops to scrape something off the sole of a boot",
                "someone watches a doorway across the street longer than idle interest explains",
                "a figure checks a handpad, frowns at it, and puts it away",
                "someone keeps to the wall and leaves the middle of the street empty",
                "two synthetics pass each other without a glance",
                "someone pockets a folded packet and walks the other way",
            ],
            'auditory': [
                "footsteps echo and fade, then echo again from somewhere else",
                "a door opens and shuts somewhere down the block",
                "a vent rattles loose in its housing overhead",
                "a low conversation cuts off as you come into earshot",
                "water drips steadily from a fixture above",
                "a handpad chimes once, unanswered",
                "distant machinery cycles through a rhythm you stop noticing",
                "someone coughs, deep and wet, and spits",
                "a cart wheel squeaks past and recedes",
                "a boot scrapes grit close behind, then nothing",
                "a vendor calls a price once and gets no answer",
                "static crackles from a speaker with nothing to say",
                "a metal shutter rolls down out of sight",
                "a snatch of music leaks from a doorway and is gone",
            ],
            'atmospheric': [
                "the street is quiet enough that footsteps carry",
                "most of the doorways here are dark",
                "the few people out keep their distance from each other",
                "a flickering sign throws uneven light across the empty grating",
                "litter shifts in the draft and settles again",
                "the open street leaves a lot of room and nobody using it",
                "shutters are down on most of the frontage",
                "steam curls up from a grate and thins out",
                "the lighting runs to dead fixtures and cold pools of glow",
                "a half-finished drink sits abandoned on a ledge",
                "scraps of paper drift against the wall and stay there",
            ],
        },
        'moderate': {
            'visual': [
                "people move with somewhere to be, weaving past each other without touching",
                "a short queue has formed at a vendor's cart",
                "two figures shake hands and something passes between them",
                "a worker shoulders through, calling an apology back over their shoulder",
                "someone hands over a folded packet and leaves quickly",
                "a knot of people parts around a stalled cart and closes again",
                "a courier cuts through the crowd at a near-run",
                "someone scans the faces in the crowd like they're looking for one",
                "two people argue quietly off to the side without breaking the flow",
                "vendors and buyers haggle over upturned crates",
                "a synthetic waves foot traffic around a wet patch of grating",
                "someone pockets a handpad after a long, careful look at the crowd",
                "a child threads between legs and is gone",
                "two workers compare something cupped in their palms",
                "a figure steps out of the flow to let a hauler trolley pass",
                "someone counts a stack of chits without slowing down",
            ],
            'auditory': [
                "a dozen conversations overlap into a low, steady murmur",
                "a vendor calls prices over the noise, again and again",
                "footsteps and cart wheels braid together into constant motion",
                "someone laughs, sharp, and the crowd swallows it",
                "a handpad chimes nearby and a voice answers it",
                "haggling rises and falls a few stalls over",
                "a hauler trolley grinds through and scatters the noise around it",
                "snatches of three languages cross in the same breath",
                "a shutter rolls up and a fresh wave of voices spills out",
                "someone's music leaks tinny from an earpiece in passing",
                "a raised voice cuts through, then drops back into the murmur",
                "the shuffle and scuff of the moving crowd never quite stops",
            ],
            'atmospheric': [
                "the street is busy without being crowded, everyone in motion",
                "vendor stalls narrow the way to a single moving channel",
                "steam and cooking smoke hang over the stalls",
                "handpad screens light faces here and there in the press",
                "foot traffic has worn clean tracks across the grating",
                "trampled wrappers and spilled goods mark where the crowd flows heaviest",
                "the crowd thins and thickens in waves with no obvious cause",
                "light from the storefronts pools across the moving crowd",
            ],
        },
        'heavy': {
            'visual': [
                "bodies press close and progress drops to a shuffle",
                "the crowd moves as one slow mass, individuals lost in it",
                "someone forces a path through, shoulder-first",
                "elbows and bags jostle from every side",
                "faces blur past too fast to fix on any one",
                "a vendor's stall is mobbed three deep",
                "someone stumbles and the press carries them upright",
                "hands rise above the crowd holding goods, chits, handpads",
                "the flow stalls, then lurches forward again",
                "a hand withdraws from a stranger's pocket and vanishes into the crush",
                "two people shout at each other over the heads between them",
                "someone hauls a crate overhead to keep it from being crushed",
            ],
            'auditory': [
                "the noise is a solid wall of voices with no gaps in it",
                "shouts and calls pile on each other, none of them distinct",
                "the shuffle of hundreds of feet drowns out everything close",
                "a vendor's amplified pitch barely cuts through the din",
                "an argument somewhere is lost in the general roar",
                "handpad chimes and alarms layer under the voices",
                "the crowd-noise rises and falls but never stops",
                "a whistle blows somewhere and the roar swallows it",
            ],
            'atmospheric': [
                "the press of bodies leaves the air close and warm",
                "there's no clear ground left, just a floor of moving people",
                "steam and breath hang visible over the packed street",
                "the crowd has filled every gap between the stalls",
                "trampled goods cover the grating underfoot",
                "the heat of the crowd is its own weather here",
                "light reaches the street only in patches between heads",
                "the smell of bodies and cooking and machine oil sits thick",
            ],
        },
        'packed': {
            'visual': [
                "the crush is total, movement measured in inches",
                "bodies pack shoulder to shoulder with no space between",
                "the crowd has stopped being people and become a single mass",
                "arms stay pinned; whatever your hands held, they still hold",
                "faces are close enough to count and impossible to get clear of",
                "someone goes down and the crowd closes over the gap",
                "the only motion is the slow grind of the whole mass shifting",
                "goods pass overhead because there's no room at chest height",
                "a child is lifted up out of the crush underfoot",
                "the press carries you a step whether you meant to take it or not",
            ],
            'auditory': [
                "the roar is constant and total, every voice lost in it",
                "sound presses in from all sides with no direction to it",
                "you can't pick out your own voice over the crowd",
                "the noise has no edges, just one overwhelming wall",
                "a shout somewhere is indistinguishable from the rest",
                "the din is so complete it starts to feel like silence",
                "nothing carries; every sound dies in the mass of bodies",
            ],
            'atmospheric': [
                "the heat and breath of the crowd fog the air",
                "there is no floor and no walls, only packed bodies in every direction",
                "the air is thick, warm, and short",
                "the crush leaves no room to lift your arms or turn around",
                "the mass shifts as one and takes you with it",
                "the bodies on every side block out the light",
                "the smell of the packed crowd is overpowering and inescapable",
            ],
        },
    }
}

def get_crowd_messages(crowd_level, message_category='all'):
    """
    Get crowd messages for specified level and category.

    Args:
        crowd_level (int): Crowd level (0-4+)
        message_category (str): 'visual', 'auditory', 'atmospheric', or 'all'

    Returns:
        dict or list: Message pools for the crowd level
    """
    intensity = CROWD_INTENSITY.get(crowd_level, 'packed')

    if intensity == 'none':
        return {} if message_category == 'all' else []

    if intensity not in CROWD_MESSAGES['default']:
        intensity = 'packed'  # Fallback for very high crowd levels

    crowd_pool = CROWD_MESSAGES['default'][intensity]

    if message_category == 'all':
        return crowd_pool
    elif message_category in crowd_pool:
        return crowd_pool[message_category]
    else:
        return []
