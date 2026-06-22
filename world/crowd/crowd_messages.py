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
    },
    # ------------------------------------------------------------------
    # Interior profile — bars, venues, and other enclosed rooms. The street
    # 'default' pool is all open-air crush (haulers, drones, gutters); indoors
    # the crowd is the room's own patrons, so it reads smaller and closer. Same
    # five sense layers, smaller pools, no weather/traffic imagery. Selected by
    # room.type via get_crowd_messages(profile=...).
    # ------------------------------------------------------------------
    'interior': {
        'sparse': {
            'visual': [
                "a lone drinker nurses something at the far end of the counter, in no hurry to finish it",
                "two regulars hunch over a table, talking low, and don't look up",
                "someone sits alone in a booth with their back to the wall and their eyes on the door",
                "a barfly counts out chits one at a time, weighing another round against the walk home",
                "a synth wipes down an already-clean table with slow, even strokes",
                "someone dozes against the wall in the corner, drink forgotten on the floor",
            ],
            'auditory': [
                "a single low conversation murmurs somewhere behind you and goes quiet",
                "a glass sets down on wood, and the room is quiet enough to hear it",
                "a stool scrapes back, and bootsteps cross to the door and out",
                "somewhere a handpad chimes and a voice answers it in a mutter",
                "the slow drip of a tap counts off the quiet",
            ],
            'olfactory': [
                "spilled liquor and old smoke have soaked into the wood over years",
                "stale beer and somebody's cheap cigarette hang in the still air",
                "the close smell of a near-empty room: damp coats, ash, and cold grease",
            ],
            'tactile': [
                "the near-empty room holds the warmth of its few bodies and little else",
                "the quiet leaves the air still and close around the tables",
            ],
            'atmospheric': [
                "half the seats are empty and the lights over them have been left low",
                "the room has the settled hush of a place between its busy hours",
                "rings from a hundred glasses ghost the bartop where the light catches it",
            ],
        },
        'moderate': {
            'visual': [
                "a working crowd fills the tables, drinks moving and chits changing hands",
                "two crews share a booth, voices easy, eyes still tracking the room",
                "someone works the floor table to table, selling something held close to the chest",
                "a knot of regulars props up the counter, trading the same complaints they always do",
                "a synth ferries empties back two-handed and never spills",
                "a hand of cards goes round a corner table, the pot a small heap of chits",
            ],
            'auditory': [
                "a dozen overlapping conversations fill the room with a steady warm churn",
                "laughter goes up at one table and turns a few heads",
                "glasses clink and a stool scrapes under the talk",
                "someone calls an order across the room and gets a grunt back",
                "a low argument simmers at the bar and settles before it boils",
            ],
            'olfactory': [
                "warm bodies, spilled beer, and cigarette smoke thicken the air",
                "the smells of a working bar: liquor, sweat, and something frying out back",
                "smoke hangs in a flat layer at head height over the tables",
            ],
            'tactile': [
                "the room's warm with bodies now, the chill of the door long gone",
                "the heat of a full house takes the edge off the night",
            ],
            'atmospheric': [
                "the tables are mostly full and the talk runs steady over them",
                "the floor's gone tacky underfoot where the night's spills have dried",
                "smoke and low light blur the far end of the room together",
            ],
        },
        'heavy': {
            'visual': [
                "the room's packed shoulder to shoulder, every table taken and the bar three deep",
                "people stand wherever they can find floor, drinks held high out of the crush",
                "a scuffle breaks out near the bar and folds back into the press before it goes anywhere",
                "the line at the counter has stopped being a line and become a wall of backs and elbows",
            ],
            'auditory': [
                "the noise blurs into one solid wall of sound off the low ceiling",
                "you can't hear the person beside you without putting your mouth to their ear",
                "a glass shatters somewhere in the press and a cheer goes up after it",
                "shouted orders pile on top of each other at the bar and lose all meaning",
            ],
            'olfactory': [
                "the packed room reeks of sweat, smoke, and spilled drink",
                "body heat pushes a thick stink of bodies and stale beer through the close air",
                "the smoke hangs so thick under the lights now it stings the eyes",
            ],
            'tactile': [
                "the heat of the packed room presses in close and damp from every side",
                "there's no still air left between the walls, just the warm push of the crowd",
            ],
            'atmospheric': [
                "there's no clear floor left, just a room full of shifting backs under the lights",
                "breath and smoke fog the air under the low lights",
                "the heat of the crowd has become its own weather, trapped under the roof",
            ],
        },
        'packed': {
            'visual': [
                "the crush is total, jammed too tight for anyone to do more than inch toward the bar",
                "drinks ride overhead hand to hand because there's no room to carry them any other way",
                "the floor has vanished under wall-to-wall bodies, packed to the back of the room",
                "a fight breaks out somewhere in the pack, has nowhere to go, and folds back into the crowd",
            ],
            'auditory': [
                "the roar of the room blurs into one wall of sound with no gaps in it",
                "the din off the walls is so complete it starts to feel like silence",
                "not even a shout carries past the next body",
            ],
            'olfactory': [
                "the packed room stinks of close bodies, sweat, smoke, and spilled drink",
                "there's no clean air left between the walls, only the thick reek of the crowd",
            ],
            'tactile': [
                "the packed room radiates a smothering, damp heat from every side at once",
                "the press holds everyone upright whether they like it or not",
            ],
            'atmospheric': [
                "there's no floor and no gaps, just packed bodies wall to wall under the lights",
                "the air between the walls is thick, warm, and short",
                "the crowd has jammed solid, packed to the back wall and the bar",
            ],
        },
    },
    # ------------------------------------------------------------------
    # Nightclub profile — the dance floor, not the bar. Bass you feel in the
    # chest, strobes and lasers and fog, a crowd locked to the beat, the decks,
    # the drop. Deliberately a different world from the 'interior' bar pool: no
    # counters or stools or drink orders — it's all floor, light, and sound.
    # Selected by room.type (nightclub/club) via crowd_profile_for_room_type.
    # ------------------------------------------------------------------
    'nightclub': {
        'sparse': {
            'visual': [
                "a lone figure moves on the empty floor, lost in a track no one else is feeling yet",
                "two people share a pill in the dark at the floor's edge and drift apart",
                "the DJ works the decks for a handful of early bodies, building something slow",
                "a dancer runs the same eight-count over and over under the lights, alone",
                "someone is folded into a corner banquette, gone somewhere the music can't reach",
                "a bouncer leans in the doorway, arms crossed, reading the thin early crowd",
                "glowsticks crack and flare in a knot of kids who came too early and too eager",
            ],
            'auditory': [
                "the bass thuds through a near-empty room, more felt than heard",
                "a track builds toward a drop that lands on no one",
                "a single whoop goes up off the floor and dies in the dark",
                "feedback whines off the rig and a voice curses at the board",
                "the music swallows a shouted name before it reaches anyone",
            ],
            'olfactory': [
                "dry-ice fog and old sweat hang flat over the empty floor",
                "synth-smoke and spilled energy drink sweeten the cold early air",
                "the sharp chemical reek of fresh fog drifts from the machines",
            ],
            'tactile': [
                "the bass comes up through the grating into the soles of your feet",
                "the floor is tacky underfoot where last night never quite got cleaned",
                "fog rolls cold and damp across the open floor",
            ],
            'atmospheric': [
                "the lights sweep an empty floor, throwing strobes across no one",
                "lasers cut the fog over a dance floor that hasn't filled yet",
                "the screens loop their fractured static to a near-empty room",
                "the room waits, lit and loud and almost empty, for the night to land",
            ],
        },
        'moderate': {
            'visual': [
                "the floor's filling out, a loose crowd moving in and out of time with the beat",
                "a circle opens around someone who can actually dance, and closes again",
                "a dealer works the floor's edge, palm to palm, never breaking stride",
                "the DJ reads the room and pushes the tempo, and the floor answers",
                "a pair grind together in the strobe, oblivious to the bodies around them",
                "someone films the floor on a cracked handpad, a small cold square in the dark",
            ],
            'auditory': [
                "the bass has found its weight now, and the floor moves with it",
                "a cheer rolls across the room as the track breaks open",
                "whoops and voices braid through the music without rising above it",
                "someone screams the hook back at the booth, off-key and delighted",
            ],
            'olfactory': [
                "sweat, fog, and synth-smoke thicken over the moving floor",
                "a sweet chemical haze of vape and dry-ice rolls off the crowd",
                "the metallic tang of someone's stim-sweat cuts through the fog",
            ],
            'tactile': [
                "the bass is a steady pressure in the chest now, climbing with the track",
                "the floor's warm with bodies, the air stirred by a hundred moving arms",
                "heat rolls off the dancers in waves, fog clinging to damp skin",
            ],
            'atmospheric': [
                "strobes chop the moving crowd into stop-motion under the rig",
                "lasers rake the fog over a floor that's finally moving",
                "the screens' static washes the dancers in cold, broken light",
                "the whole room pulses with the track, lit and loud and starting to cook",
            ],
        },
        'heavy': {
            'visual': [
                "the floor is a single moving mass, every body locked to the same beat",
                "hands go up across the whole floor on the build, reaching for the drop",
                "a dancer crowd-surfs the packed floor a few seconds before going down laughing",
                "lasers sweep a sea of upraised arms and the floor roars back",
                "someone goes down in the crush and friends haul them up, still dancing",
            ],
            'auditory': [
                "the bass is total now, a physical thing driving the whole floor",
                "the drop hits and the room detonates into one massive roar",
                "the track and the crowd's roar have become the same sound",
                "the speakers on their chains rattle with every kick",
            ],
            'olfactory': [
                "the packed floor reeks of hot sweat, fog, and chemical smoke",
                "a wall of sweat-and-fog heat hits you at the edge of the floor",
                "the air is thick with vape, body heat, and the sweet rot of spilled drink",
            ],
            'tactile': [
                "the bass hammers in the chest and up through the grating into the legs",
                "the packed floor throws off a wet, rolling heat from every side",
                "there's no still air left over the floor, just the warm churn of bodies",
            ],
            'atmospheric': [
                "strobes freeze the heaving floor a frame at a time, all of it raised arms",
                "fog and laserlight hang in solid sheets over the packed floor",
                "the heat of the floor fogs the air and runs in beads down the walls",
                "the whole room moves as one body, hammering on the beat",
            ],
        },
        'packed': {
            'visual': [
                "the floor is jammed solid, everyone moving because there's no room not to",
                "the crowd surges as one on the drop and you go where it goes",
                "arms stay up across the floor, locked there by the press as much as the beat",
                "lasers cut a packed floor with no gap and no edge anywhere in it",
            ],
            'auditory': [
                "the bass and the roar are total, one sound with no room left in it",
                "the rig is so loud the air itself feels solid",
                "the drop lands and the roar is so complete it loops back into silence",
            ],
            'olfactory': [
                "the crush stinks of hot sweat, chemical fog, and breath gone close and stale",
                "there's no clean air over the floor, only the wet reek of the packed crowd",
            ],
            'tactile': [
                "the bass is inside the chest now, indistinguishable from a heartbeat",
                "the packed floor radiates a smothering, soaking heat from every side at once",
                "the crush holds everyone upright, moving them whether they choose to or not",
            ],
            'atmospheric': [
                "there's no floor and no edge, just packed bodies under the strobes wall to wall",
                "the air over the floor is thick, hot, and shaking with the bass",
                "the crowd has stopped being people and become one heaving thing, lit in strobe",
                "fog, heat, and laserlight have closed over the floor into its own dark weather",
            ],
        },
    },
}

#: Dance-venue room types — the 'nightclub' pool (floor/bass/lights), a world
#: apart from the bar-counter 'interior' pool.
NIGHTCLUB_ROOM_TYPES = {'nightclub', 'club'}

#: Enclosed bar/venue room types that draw on the 'interior' crowd pool rather
#: than the open-air street 'default'. Anything unlisted falls back to 'default'.
INTERIOR_ROOM_TYPES = {
    'bar', 'interior', 'venue', 'cantina', 'lounge',
}


def crowd_profile_for_room_type(room_type):
    """Map a ``room.type`` to a crowd profile ('default'|'interior'|'nightclub')."""
    t = str(room_type or "").lower()
    if t in NIGHTCLUB_ROOM_TYPES:
        return 'nightclub'
    if t in INTERIOR_ROOM_TYPES:
        return 'interior'
    return 'default'


def get_crowd_messages(crowd_level, message_category='all', profile='default'):
    """
    Get crowd messages for specified level and category.

    Args:
        crowd_level (int): Crowd level (0-4+)
        message_category (str): 'visual', 'auditory', 'olfactory', 'tactile',
            'atmospheric', or 'all'
        profile (str): Which message pool to draw from ('default' street crush
            vs. 'interior' enclosed venues). Unknown profiles fall back to
            'default'.

    Returns:
        dict or list: Message pools for the crowd level
    """
    intensity = CROWD_INTENSITY.get(crowd_level, 'packed')

    if intensity == 'none':
        return {} if message_category == 'all' else []

    pool = CROWD_MESSAGES.get(profile) or CROWD_MESSAGES['default']

    if intensity not in pool:
        intensity = 'packed'  # Fallback for very high crowd levels

    crowd_pool = pool[intensity]

    if message_category == 'all':
        return crowd_pool
    elif message_category in crowd_pool:
        return crowd_pool[message_category]
    else:
        return []
