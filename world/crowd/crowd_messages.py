"""
Crowd system message pools (parallels the weather system architecture).

Ambient, perception-gated observations about the people sharing a room. The
guiding principle is to OFFER something to observe -- never to tell the player
how to feel about it. But "observe" doesn't mean bland: these are the colony's
streets, and things HAPPEN on them. A dog's bark cut short, feral kids stripping
a wage-hand and gone before he can shout, a deal souring in the press. The grit
and the menace live in the events themselves, concretely shown; the player draws
their own conclusions. No "reality warps," no "you feel dread" -- but no empty
wallpaper either.

Voice: the colony's own texture -- shift crews in stained coveralls, synthetics,
corpsec drones, ripperdoc touts, chit-hustlers, haulers, feral kids, the channel,
the prefab sprawl, the processor's hum. Kept generic to the whole colony (no
named districts); a line should read true on any of its streets.

Lines may run to two short sentences; the renderer capitalises only the first
letter, so interior sentence capitals survive.
"""

# Crowd level intensity mapping
CROWD_INTENSITY = {
    0: 'none',      # No crowd messages
    1: 'sparse',    # A few people, room to move -- and room for things to happen
    2: 'moderate',  # A working crowd, transactions and steady motion
    3: 'heavy',     # Dense, a slow press of bodies and a wall of noise
    4: 'packed',    # A crush; the crowd moves as one mass
}

CROWD_MESSAGES = {
    'default': {
        'sparse': {
            'visual': [
                "down the quiet stretch a dog barks once, yelps, and goes silent. The few people out don't break stride",
                "a pack of feral kids swarms a stumbling wage-hand by the prefabs, strips him to his undershirt, and scatters into the gaps before he can shout",
                "a synthetic stands too long at a dead junction box, head cocked, listening to a frequency no one else hears",
                "two figures trade something hand-to-hand in a doorway and split off in opposite directions without a word",
                "a chit-hustler works an empty doorway, running the patter to no one out of habit",
                "a drunk argues with his own reflection in a dark viewport, and loses",
                "someone in stained coveralls counts a thin fold of chits twice, pockets it, and moves on fast",
                "a beggar with a dead chrome arm rattles a cup at the few who pass, and they pass",
                "a figure checks over one shoulder, then the other, then ducks into an unlit service gap",
                "a lone corpsec drone drifts down the empty street at head height, lens swivelling, and moves on",
                "someone sleeps in a doorway under a sheet of packing foam, one boot missing",
                "a synth sweeps the same patch of grating it already swept, patient and unhurried",
                "a kid watches you from a stairwell, and is gone the moment you look back",
                "two old shift-hands share a cigarette in the lee of a parked hauler, saying nothing",
                "a figure works a maglock with the wrong tool and too much patience",
            ],
            'auditory': [
                "a dog barks somewhere close, then yelps, then nothing",
                "footsteps fall in behind you, keep your pace exactly, and peel off at the corner",
                "a chit-hustler's patter rises and dies away down the empty street",
                "glass breaks two blocks over, and no alarm follows",
                "someone counts under their breath in a language you don't know",
                "a handpad chimes in a dark doorway, answered by a low, quick voice",
                "a cough racks somebody in a doorway, wet and long, and settles",
                "boots scuff grit close behind, then stop, then nothing",
                "a corpsec drone whines past overhead, its lens clicking as it tracks",
                "somewhere a baby cries, briefly, through a prefab wall",
                "a shutter rattles down and a bolt throws home",
                "a voice argues a price with no one, and trails off",
            ],
            'atmospheric': [
                "the street is empty enough that the processor's hum carries",
                "most of the doorways are dark, and the lit ones look worse",
                "a bundle of foam and rags in the nearest doorway doesn't move",
                "the few out keep to the walls and leave the middle of the street to no one",
                "fresh blood, not yet browned, streaks the grating by a kicked-over cup",
                "a corpsec drone's lens tracks you the length of the block",
                "scorch marks fan up one wall where something burned and was put out",
                "chalked gang-marks layer the shutters, the newest still bright",
                "dropped chits glint in the gutter and nobody has stopped for them",
                "the quiet has the feel of a street that cleared in a hurry",
            ],
        },
        'moderate': {
            'visual': [
                "the flow thins to a steady file of clean suits and synthetic faces, none of them meeting your eye",
                "a ripperdoc's tout works the crowd, flashing a tray of secondhand chrome still tacky at the contacts",
                "a hauler crew shoulders through with a slung crate and scatters the slower foot traffic to the gutters",
                "two people trade a folded packet mid-stride and never break step",
                "a vendor and a shift-hand haggle hard over a crate of channel fish on melting ice",
                "a synth waves the foot traffic around a body that two men are still arguing over",
                "a pickpocket drifts the crowd, hands easy, eyes on the belt-pouches",
                "a corpsec pair moves through the flow and the crowd opens and closes around them like water",
                "a kid runs a three-cup hustle on an upturned crate, faster than the marks can follow",
                "a drunk weaves the wrong way through the flow, shedding apologies he doesn't mean",
                "someone counts a fat roll of chits in plain sight, too new to the street to know better",
                "two synths pass close, exchange a burst of clicks, and part without slowing",
                "a hauler idles half across the street while its crew argues over a manifest",
            ],
            'auditory': [
                "a dozen conversations braid into a low, steady churn",
                "a vendor calls the same price over and over until it stops meaning anything",
                "a deal sours somewhere in the press; voices climb, then drop, then the crowd closes over it",
                "haggling spikes and settles a few stalls down",
                "a hauler's horn blares and the crowd-noise barely flinches",
                "a hustler's three-cup patter rattles fast over an upturned crate",
                "snatches of four languages cross in a single breath",
                "a synth's voice cuts in flat and clear, giving directions no one asked for",
                "somewhere a bottle breaks and a laugh goes up",
                "corpsec barks an order and the murmur drops a notch, then recovers",
            ],
            'atmospheric': [
                "the crowd flows steady, everyone with somewhere to be and no reason to look up",
                "stalls and crates pinch the street down to a single moving channel",
                "handpad screens light faces here and there in the churn",
                "spilled produce and trampled wrappers mark where the flow runs heaviest",
                "a corpsec pair watches the flow from a doorway, saying nothing",
                "foot traffic has worn the grating to a polished track down the middle",
                "a beggar holds a patch of wall that the crowd flows around without seeing",
            ],
        },
        'heavy': {
            'visual': [
                "honking and a yelled trade of insults from a stalled hauler chokes the flow to a standstill while everyone cranes to see it",
                "a pickpocket's hand comes out of a stranger's coat and is three bodies away before the mark even turns",
                "the crowd jams solid around a fight nobody can see, only hear",
                "someone goes down in the press and the flow closes over the gap",
                "a hauler noses into the crush, horn blaring, and the bodies grudge it an inch at a time",
                "a preacher bellows about the processor from a crate; the crowd parts around him and ignores every word",
                "a synth seizes mid-step in the crush, twitching, and the crowd flows around it like water around a post",
                "hands rise above the heads holding crates, chits, and handpads clear of the grind",
                "two crews square off across the flow and the space between them empties fast",
                "a kid worms through the forest of legs at waist height and is gone",
            ],
            'auditory': [
                "the noise is a solid wall of voices with no gaps in it",
                "a hauler leans on its horn and the crowd-roar barely gives",
                "a scream cuts through somewhere ahead, then the churn swallows it",
                "shouts pile on shouts until none of them mean anything",
                "the shuffle of hundreds of feet drowns everything closer than your own voice",
                "a vendor's amped pitch claws through the din and loses",
                "glass shatters in the press and a cheer goes up",
                "an alarm starts somewhere and folds into the general roar",
            ],
            'atmospheric': [
                "the press of bodies turns the air close and warm and used",
                "there's no clear grating left, just a floor of moving people",
                "breath and steam hang visible over the packed street",
                "the crowd has filled every gap the stalls left",
                "a corpsec drone hangs over the crush, its lens working the faces",
                "trampled goods and worse cover the grating underfoot",
                "the heat of the crowd is its own weather in here",
            ],
        },
        'packed': {
            'visual': [
                "a scream goes up somewhere in the crush, short and sharp, and the mass swallows it without a ripple",
                "the crowd locks solid; pinned shoulder to shoulder, you move when it moves and not before",
                "a child rides overhead hand to hand above the crush, wide-eyed and silent, toward the edge",
                "someone goes down underfoot and the mass grinds on over the gap",
                "your arms stay pinned to your sides; whatever your hands held, they hold now",
                "faces press close enough to count and impossible to get clear of",
                "a hand works your pockets in the crush, and there's no room to turn and catch it",
                "the whole mass lurches a step as one and carries everyone with it",
            ],
            'auditory': [
                "the roar is total, every voice drowned in every other",
                "sound presses from all sides with no direction left in it",
                "you can't pick your own voice out of the crush",
                "a scream is indistinguishable from the rest of the din",
                "the noise is so complete it starts to feel like silence",
                "nothing carries; every sound dies in the press of bodies",
            ],
            'atmospheric': [
                "the heat and breath of the crowd fog the air",
                "there is no grating and no walls, only packed bodies in every direction",
                "the air is thick, warm, and short",
                "the crush leaves no room to lift your arms or turn around",
                "the mass shifts as one and takes you with it",
                "the bodies on every side block out the light",
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
