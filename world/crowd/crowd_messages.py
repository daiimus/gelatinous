"""
Crowd system message pools (parallels the weather system architecture).

Ambient, perception-gated observations about the people sharing a room. Three
rules, learned the hard way:

  1. OFFER something to observe, don't narrate how to feel. The grit lives in
     the concrete event (a dog's bark cut short, feral kids stripping a wage-hand
     and gone), shown plainly; the player draws their own conclusions.

  2. AMBIENCE, NOT ACTION ON THE PLAYER. Never describe something happening TO
     the character that they'd want to react to but can't -- no hand in *your*
     pocket, no shove that moves *you*, no pinning *your* arms. Those imply a
     game action the text can't deliver. Redirect to other people or the scene.
     Plain sensory perception ("you hear a dog bark", "the cold air bites") is
     fine -- that's how senses work; it just doesn't act on the character.

  3. NAME THE SUBJECT, AND DON'T REPEAT YOURSELF. "The roar is total" begs:
     roar of what? Keep referents concrete (the roar of the crowd). Within a
     tier no two lines should lean on the same crutch ("the press", "every
     side") -- vary the image, the opening, and the verb.

Voice: the colony's own texture -- shift crews, synthetics, corpsec drones,
ripperdoc touts, chit-hustlers, haulers, feral kids, the channel, the prefab
sprawl, the processor's hum. Generic to the whole colony (no named districts).

Five sense layers, matching the room model: visual / auditory / olfactory /
tactile / atmospheric. The renderer gates visual on sight and auditory on
hearing; olfactory, tactile and atmospheric always show. Lines may run to two
short sentences; the renderer capitalises only the first letter, so interior
capitals survive.
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
                "a synthetic stands too long at a dead junction box, head cocked, listening to a frequency no one else can hear",
                "two figures trade something hand-to-hand in a doorway, then split off in opposite directions without a word",
                "a chit-hustler works an empty doorway, running the patter to no one out of pure habit",
                "a drunk argues with his own reflection in a dark viewport, and loses",
                "someone in oil-stained coveralls counts a thin fold of chits twice, pockets it, and moves on fast",
                "a beggar with a dead chrome arm rattles a cup at the few who pass, and they pass",
                "a lone corpsec drone drifts down the street at head height, its lens swivelling as it goes",
                "someone sleeps in a doorway under a sheet of packing foam, one boot gone",
                "a synth sweeps the same patch of grating it already swept, patient and unhurried",
                "two old shift-hands share a cigarette in the lee of a parked hauler, saying nothing",
                "a kid watches from a stairwell, and is gone at a second glance",
                "a figure works a maglock with the wrong tool and far too much patience",
                "a courier on a battered board kicks past and is gone around the corner",
                "an old woman picks through a refuse bin with slow, practiced thoroughness",
                "someone tapes a hand-printed notice to a shutter and slips off before anyone reads it",
                "a one-eyed dog trots the gutter nose-down, ignoring the few who pass",
            ],
            'auditory': [
                "somewhere close a dog barks, then yelps, then nothing",
                "down the empty street a chit-hustler's patter rises and dies away",
                "glass breaks two blocks over, and no alarm follows it",
                "someone nearby counts under their breath in a language you don't know",
                "a handpad chimes in a dark doorway, and a low, quick voice answers it",
                "a wet, racking cough goes on too long in a doorway, then settles",
                "footsteps scuff the grit somewhere behind, slow, then stop",
                "a corpsec drone whines past overhead, its lens clicking as it sweeps the street",
                "through a prefab wall a baby cries, briefly, and is hushed",
                "a shutter rattles down somewhere and a bolt throws home",
                "a voice haggles a price with no one, and trails off",
                "a board's wheels clatter past and fade around the corner",
                "two voices murmur low in a doorway and cut off as you come near",
                "a loose cable taps a slow rhythm against a pole",
            ],
            'olfactory': [
                "the thin air carries little but cold metal and a thread of someone's smoke",
                "a faint reek of piss and damp drifts out of the dark doorways",
                "stale cigarette smoke hangs where the last few bodies passed",
                "machine oil and cold grating are about all the empty street offers the nose",
                "somewhere close, fried protein and cheap oil cut through the cold air",
                "the sour smell of a sleeper's doorway carries on the still air",
                "a whiff of solvent leaks from a shuttered workshop",
                "spilled liquor and old smoke linger outside a dark bar",
                "the cold air holds the faint rot of a bin nobody's emptied",
            ],
            'tactile': [
                "with so few people about, no one's warmth carries, and the air stays cold",
                "the rare shoulder brushing past is the only contact the empty street offers",
                "the thin foot traffic leaves the air cold and unstirred",
                "the cold of the empty street settles in, undisturbed by any crowd",
                "with nothing moving, there's nothing to warm the air between the buildings",
                "the chill of the open street has plenty of room to settle",
                "the odd passing body stirs the cold air and is gone",
            ],
            'atmospheric': [
                "the street is empty enough that the processor's hum carries",
                "most of the doorways are dark, and the lit ones look worse",
                "a bundle of foam and rags in the nearest doorway doesn't move",
                "the few people out keep to the walls and leave the middle of the street to no one",
                "fresh blood, not yet browned, streaks the grating beside a kicked-over cup",
                "scorch marks fan up one wall where something burned and was put out",
                "chalked gang-marks layer the shutters, the newest still bright",
                "dropped chits glint in the gutter, and no one has stopped for them",
                "the quiet has the feel of a street that cleared in a hurry",
                "a single shoe sits in the middle of the grating, going nowhere",
                "a security shutter hangs half-down over a dark, gutted shopfront",
                "the lamps buzz over a street with almost no one to light",
            ],
        },
        'moderate': {
            'visual': [
                "the flow thins to a steady file of clean suits and synthetic faces, none of them meeting an eye",
                "a ripperdoc's tout works the crowd, flashing a tray of secondhand chrome still tacky at the contacts",
                "a hauler crew shoulders through with a slung crate, scattering the slower foot traffic to the gutters",
                "two people trade a folded packet mid-stride and never break step",
                "a vendor and a shift-hand haggle hard over a crate of channel fish on melting ice",
                "a synth waves the foot traffic around a body two men are still arguing over",
                "a pickpocket drifts the edge of the crowd, hands easy, eyes on the belt-pouches of strangers",
                "a corpsec pair wades through the flow, and the crowd opens and closes around them like water",
                "a kid runs a three-cup hustle on an upturned crate, faster than the marks can follow",
                "a drunk weaves the wrong way through the flow, shedding apologies he doesn't mean",
                "someone counts a fat roll of chits in plain sight, too new to the street to know better",
                "two synths pass close, trade a quick burst of clicks, and part without slowing",
                "a hauler idles half across the street while its crew argues over a manifest",
                "a busker saws at a battered string-rig for the coins in an upturned cap",
                "a courier threads the gaps at a dead run, satchel clutched to the chest",
                "a vendor flips fried dough in a spitting pan and calls the price at everyone",
                "two crews eye each other across the flow and keep moving, for now",
            ],
            'auditory': [
                "a dozen overlapping conversations braid into a low, steady churn",
                "a vendor calls the same price over and over until it stops meaning anything",
                "somewhere in the flow a deal sours; voices climb, then drop, then the crowd closes over it",
                "haggling spikes and settles again a few stalls down",
                "a hauler's horn blares and the churn barely flinches",
                "a hustler's three-cup patter rattles fast over an upturned crate",
                "snatches of four languages cross in a single breath",
                "a synth's voice cuts in flat and clear, giving directions no one asked for",
                "somewhere a bottle breaks and a laugh goes up after it",
                "corpsec barks an order and the murmur drops a notch, then recovers",
                "a busker's string-rig saws on under the chatter",
                "a child's voice pipes a question and is shushed",
                "frying oil spits and hisses at a food cart",
            ],
            'olfactory': [
                "the moving crowd carries its smells with it: sweat, fried protein, cheap synth-cologne",
                "cooking smoke and body heat thicken the air over the flow",
                "machine oil, coolant, and unwashed coveralls ride the moving crowd",
                "the brine of a fish-vendor's crate cuts through the warmer smells",
                "fried dough and hot oil drift from a spitting pan",
                "a waft of antiseptic and hot solder trails the ripperdoc's tout",
                "tobacco and spilled beer hang outside an open bar",
                "the sweetish reek of cheap cologne lingers in someone's wake",
                "char and spice rise from a grill working at full tilt",
            ],
            'tactile': [
                "the moving crowd stirs a warmth into the air, the press of it light but constant",
                "shoulders and elbows brush in passing as the flow threads itself together",
                "the foot traffic keeps the air moving, warm with bodies and breath",
                "the crowd's heat takes the edge off the street's chill",
                "the steady passage of bodies leaves no still air to stand in",
                "warmth and movement fill the street, close but not yet crowding",
                "the odd hurried shoulder clips past in the steady flow",
            ],
            'atmospheric': [
                "the crowd flows steady, everyone with somewhere to be and no reason to look up",
                "stalls and crates pinch the street down to a single moving channel",
                "handpad screens light faces here and there across the churn",
                "spilled produce and trampled wrappers mark where the flow runs heaviest",
                "a corpsec pair watches the flow from a doorway, saying nothing",
                "foot traffic has worn the grating to a polished track down the middle",
                "a beggar holds a patch of wall that the crowd flows around without seeing",
                "vendors' strung bulbs sway over the moving heads",
                "the smells and noise of a dozen trades overlap down the street",
                "the steady churn never quite stops and never quite crowds",
            ],
        },
        'heavy': {
            'visual': [
                "honking and a yelled trade of insults from a stalled hauler chokes the flow to a standstill while everyone cranes to see the fight",
                "a pickpocket's hand slips out of a stranger's coat and is three bodies away before the mark even turns",
                "the crowd jams solid around a fight nobody can see, only hear",
                "someone goes down in the press, and the flow closes over the gap",
                "a hauler noses into the crush, horn blaring, and the bodies grudge it an inch at a time",
                "a preacher bellows about the processor from a crate; the crowd parts around him and ignores every word",
                "a synth seizes mid-step in the crush, twitching, and the crowd flows around it like water around a post",
                "hands rise above the heads, holding crates and chits and handpads clear of the grind",
                "two crews square off across the flow, and the space between them empties fast",
                "a kid worms through the forest of legs at waist height and is gone",
                "a vendor's stall goes over in the surge and the goods vanish in seconds",
                "a corpsec squad drives a wedge through the bodies, batons up",
                "a shout for help rises over the heads and gets no answer",
            ],
            'auditory': [
                "the noise of the crowd is a solid wall of voices with no gaps in it",
                "a hauler leans on its horn, and the crowd's roar barely gives",
                "a scream cuts through from somewhere ahead, then the churn swallows it",
                "shouts pile on shouts until none of them mean anything",
                "the shuffle of hundreds of feet drowns out everything nearer than a raised voice",
                "a vendor's amped pitch claws through the crowd's din and loses",
                "glass shatters somewhere in the press and a cheer goes up",
                "an alarm starts up somewhere and folds straight into the general roar",
                "a whistle shrills over the crowd, twice, then is lost",
                "a chant starts up in one corner and breaks apart in the noise",
                "an overturned stall clatters down, barely heard in the din",
            ],
            'olfactory': [
                "the packed crowd reeks of sweat, smoke, and fried street food",
                "body heat pushes up a thick stink of bodies, machine oil, and cheap cologne",
                "the air goes heavy with breath, sweat, and the sweet rot of trampled food",
                "smoke and sweat and coolant blend into one thick crowd-stink",
                "the warm reek of too many bodies sits over the whole street",
                "spilled beer and grill-smoke hang in the dense air",
                "the sourness of unwashed crowds thickens with the heat",
                "a tang of ozone and hot chrome rides the close air",
            ],
            'tactile': [
                "the packed bodies throw off a steady heat, and the press of them comes from every side",
                "shoulder grinds against shoulder in the slow, constant shuffle",
                "the crowd's heat thickens the air, close and damp with breath",
                "there's no still air left in the press, just the warm push of the crowd",
                "the jostle of the crowd never quite lets up",
                "the heat of so many bodies turns the air thick and humid",
                "the slow grind of the crowd presses in, eases, and presses again",
            ],
            'atmospheric': [
                "the press of bodies leaves the air close, warm, and used",
                "there's no clear grating left, just a floor of moving people",
                "breath and steam hang visible over the packed street",
                "the crowd has filled every gap the stalls left",
                "a corpsec drone hangs over the crush, its lens working the faces",
                "trampled goods and worse cover the grating underfoot",
                "the heat of the crowd is its own weather in here",
                "strung bulbs sway wildly over the heaving heads",
                "the whole street has become one slow, grinding mass",
                "there's nowhere to stand that isn't shoulder to shoulder",
            ],
        },
        'packed': {
            'visual': [
                "a scream goes up somewhere in the crush, short and sharp, and the mass swallows it without a ripple",
                "the crowd locks up solid, jammed too tight for anyone to do more than inch forward",
                "a child rides overhead hand to hand above the crush, wide-eyed and silent, toward the edge",
                "someone goes down underfoot and the mass grinds on over the gap",
                "arms stay pinned in the crush, hands locked on whatever they were holding",
                "faces press close enough to count on every side",
                "a pickpocket works the crush, where the marks have no room to turn",
                "the whole mass lurches a step as one, and everyone in it goes along",
                "a fight breaks out somewhere in the pack, has nowhere to go, and folds back into the press",
                "a thin gap opens for a heartbeat and a dozen people fight into it at once",
                "a dropped bundle is trampled under before anyone can stoop for it",
                "the crush funnels solid into a choke point and stalls there",
            ],
            'auditory': [
                "the roar of the packed crowd is total, every voice drowned in every other",
                "the crowd's noise presses in from all sides with no direction left in it",
                "the din of the crush is so complete it starts to feel like silence",
                "not even a shout carries far in the packed roar",
                "nothing carries; every sound dies in the press of bodies",
                "a scream somewhere is indistinguishable from the rest of the crowd's din",
                "the crush is loud enough to feel in the chest",
                "voices, horns, and alarms all blur into one wall of sound",
                "a panicked yell goes up and vanishes into the roar",
            ],
            'olfactory': [
                "the crush stinks of close-packed bodies, sweat, and breath gone stale",
                "the reek is overpowering: sweat, smoke, coolant, and unwashed skin",
                "there's no clean air left, only the thick stink of the packed crowd",
                "body heat cooks the smell of sweat and oil into something solid",
                "the stench of the crush hangs hot and unmoving",
                "every breath comes thick with the smell of too many bodies",
                "sweat and breath and smoke clot into one heavy reek",
            ],
            'tactile': [
                "the crush radiates a smothering heat from every side at once",
                "packed this tight, there's no air that isn't warm with someone's breath",
                "the press is total, a solid wall of heat and contact on all sides",
                "the heat of the packed bodies is close, damp, and inescapable",
                "the crush holds everyone upright whether they like it or not",
                "the warmth of the mass is suffocating and total",
            ],
            'atmospheric': [
                "the heat and breath of the crowd fog the air",
                "there is no grating and no walls, only packed bodies in every direction",
                "the air is thick, warm, and short",
                "the crush leaves no room to lift an arm or turn around",
                "the whole mass sways and shifts as one",
                "the bodies on every side block out the light",
                "the pack has filled the street wall to wall",
                "the crowd has stopped being people and become one solid thing",
                "there's no telling where one body ends and the next begins",
            ],
        },
    }
}

def get_crowd_messages(crowd_level, message_category='all'):
    """
    Get crowd messages for specified level and category.

    Args:
        crowd_level (int): Crowd level (0-4+)
        message_category (str): 'visual', 'auditory', 'olfactory', 'tactile',
            'atmospheric', or 'all'

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
