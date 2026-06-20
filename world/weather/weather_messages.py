"""
Weather Message Pools

Ambient, perception-gated weather observations for outdoor rooms. The weather
system shows a couple of lines drawn from DISTINCT senses (a visual + a smell,
say -- see weather_system.get_weather_contributions), so two shown lines never
echo each other. Each line is still written to stand alone and read cleanly
beside any other.

Principles (shared with room and crowd authoring):

  * OFFER concrete observation; don't narrate how to feel. Ground it in the
    colony's texture (prefab sprawl, the grating, gutters, eaves, viewports,
    the channel, the crater rim, the processor's hum).
  * AMBIENCE, NOT ACTION ON THE PLAYER. Describe the weather and what it does to
    the street and air, not things done to the character. Plain sensation
    ("the cold bites", "sand stings") is fine; weather touches everyone.
  * NAME THE SUBJECT, and DON'T REPEAT YOURSELF. Within a weather type no two
    lines should lean on the same crutch phrase or describe the same object the
    same way; each should bring its own image, opening, and verb.

Five sense layers, matching the room model: visual / auditory / olfactory /
tactile / atmospheric. The system gates visual on sight and auditory on
hearing; olfactory, tactile and atmospheric always show.

The WEATHER_MESSAGES dict (every weather type x time-of-day x sense) is built
deterministically at import from:

  * WEATHER_POOLS -- per weather type, observational lines per sense category.
  * TIME_LIGHT / TIME_ACTIVITY -- diurnal light-level and street-activity lines,
    each with several variants per period; the builder picks a variant by
    weather type so different weathers wear different time-lines, and rotates
    the weather pools by time index for per-hour variation.
"""

# Weather intensity levels (used elsewhere for message length/impact tuning).
WEATHER_INTENSITY = {
    # Mild weather
    'clear': 'mild',
    'overcast': 'mild',
    'windy': 'mild',

    # Moderate weather
    'fog': 'moderate',
    'rain': 'moderate',
    'soft_snow': 'moderate',
    'foggy_rain': 'moderate',
    'light_rain': 'moderate',

    # Intense weather
    'dry_thunderstorm': 'intense',
    'rainy_thunderstorm': 'intense',
    'hard_snow': 'intense',
    'blizzard': 'intense',
    'gray_pall': 'intense',
    'tox_rain': 'intense',
    'sandstorm': 'intense',
    'blind_fog': 'intense',
    'heavy_fog': 'intense',

    # Extreme weather
    'flashstorm': 'extreme',
    'torrential_rain': 'extreme',
}

# Canonical time-of-day periods (from time_system.TIME_PERIODS).
TIME_PERIODS = [
    'pre_dawn', 'dawn', 'early_morning', 'late_morning', 'midday',
    'early_afternoon', 'late_afternoon', 'dusk', 'early_evening',
    'late_evening', 'night', 'late_night',
]

# Ambient light level by time of day -- several variants per period. Phrased in
# terms of brightness and the streetlamps, so each holds under any weather.
TIME_LIGHT = {
    'pre_dawn': [
        "the streetlamps still hold against the dark before dawn",
        "it's the dead hour before dawn, lit only by the lamps",
        "the last of the night lingers, the lamps still burning",
    ],
    'dawn': [
        "the light comes up thin and grey",
        "first light is just bleeding into the dark",
        "a pale, watery dawn seeps into the street",
    ],
    'early_morning': [
        "the early light strengthens, low and pale",
        "morning light is coming up but hasn't found its strength",
        "the day is young and the light still soft",
    ],
    'late_morning': [
        "the light has filled out into full day",
        "full morning light lies across the street now",
        "the day has brightened to its working light",
    ],
    'midday': [
        "the light sits flat and full overhead",
        "it's the bright, shadowless middle of the day",
        "midday light lies hard and even on everything",
    ],
    'early_afternoon': [
        "the afternoon light holds steady",
        "the day sits at its long, level afternoon",
        "the light has settled into the afternoon",
    ],
    'late_afternoon': [
        "the light dims and lengthens toward evening",
        "the day is going, the light thinning toward dusk",
        "late light slants long and tired across the street",
    ],
    'dusk': [
        "the light drains toward dusk and the lamps flicker on",
        "dusk settles in as the streetlamps wake",
        "the day fails and the lamps take over",
    ],
    'early_evening': [
        "the streetlamps carry the early evening",
        "evening has come and the lamps own the street",
        "the early evening runs on lamplight now",
    ],
    'late_evening': [
        "the late lamps pool yellow on the grating",
        "it's full evening, lit yellow and low",
        "the late hour glows under the streetlamps",
    ],
    'night': [
        "the dark sits heavy between the streetlamps",
        "night has the street, broken only by the lamps",
        "deep dark fills the gaps the lamps can't reach",
    ],
    'late_night': [
        "the streetlamps burn alone in the late hours",
        "it's the small hours, the street given over to lamplight",
        "the dead of night holds, lit cold by the lamps",
    ],
}

# Street activity by time of day -- several variants per period, weather-agnostic.
TIME_ACTIVITY = {
    'pre_dawn': [
        "almost no one is out at this hour",
        "the street belongs to the few who never sleep",
        "barely a soul moves this early",
    ],
    'dawn': [
        "the first-shift traffic begins to stir",
        "the earliest workers are starting to move",
        "the street wakes slow with the first shift",
    ],
    'early_morning': [
        "the morning crowd thickens on the grating",
        "the early rush is building",
        "more bodies fill the street as the morning gets going",
    ],
    'late_morning': [
        "the street runs at its working pace",
        "the day's traffic has hit its stride",
        "the street moves at full working bustle",
    ],
    'midday': [
        "midday traffic crosses steadily",
        "the lunch crowd works through the street",
        "the street stays busy through the middle of the day",
    ],
    'early_afternoon': [
        "the afternoon foot traffic holds steady",
        "a steady afternoon flow works the street",
        "the street keeps its afternoon pace",
    ],
    'late_afternoon': [
        "the shift change crowds the street",
        "the late-day rush builds toward shift change",
        "workers pour out as the shift turns over",
    ],
    'dusk': [
        "the evening crowd starts to fill the street",
        "the street thickens as the day winds down",
        "people drift out into the failing light",
    ],
    'early_evening': [
        "the street is busy with people off shift",
        "the evening crowd is out in force",
        "off-shift bodies fill the street",
    ],
    'late_evening': [
        "the late crowd thins toward the bars and cubes",
        "the street empties slowly toward the night spots",
        "the evening crowd is drifting off to drink or sleep",
    ],
    'night': [
        "the street has emptied to the night people",
        "only the night crowd is left out now",
        "the day's traffic is gone, the night's taking over",
    ],
    'late_night': [
        "the street is all but deserted",
        "next to no one is out in the small hours",
        "the street lies empty but for the odd figure",
    ],
}

# Per-weather observational pools. Lines are time-agnostic weather facts; the
# diurnal light/activity lines above carry the time of day.
WEATHER_POOLS = {
    'clear': {
        'visual': [
            "the sky stands open and cloudless over the prefab roofs",
            "the crater rim cuts a hard, clean line in the distance",
            "the grating is bone-dry, the gutters empty and idle",
            "heat-shimmer wavers up off the bare composite",
            "a thin haze of dust drifts where nothing disturbs it",
            "long unbroken light lays the street out plain and sharp",
            "the channel glints flat and far between the buildings",
            "not a cloud breaks the wide, washed-out sky",
        ],
        'auditory': [
            "voices and footsteps carry a long way with nothing to muffle them",
            "a loose panel ticks somewhere in the heat",
            "the processor's hum stands alone under the open sky",
            "a hauler's engine grinds faint from blocks off",
            "the street's chatter rings sharp and distinct",
            "somewhere a vendor's call travels half the block",
            "the quiet is brittle, every sound its own",
        ],
        'olfactory': [
            "warm composite and dust settle over the grating",
            "a thread of machine oil drifts from an open bay",
            "the faint ozone of the processor reaches even here",
            "sun-baked metal gives off a flat mineral note",
            "fried oil and smoke drift over from a food cart",
            "the heat draws a scorched, dusty edge from the street",
            "nothing wet and nothing green, just hot stone and steel",
        ],
        'tactile': [
            "the heat lies heavy and unmoving",
            "warmth radiates back up off the baked grating",
            "not a breath of wind stirs the close air",
            "the day's heat has soaked into every surface",
            "the parched air pulls the moisture off everything",
            "a faint warmth still rises from the sun-struck walls",
        ],
        'atmospheric': [
            "the dry spell has people out and in no hurry",
            "the gutters and drains sit idle and cracked-dry",
            "hard light throws the street's grime into relief",
            "dust gathers undisturbed in the corners and seams",
            "the heat keeps the pace slow and the tempers short",
            "the cloudless calm leaves the street nowhere to hide",
        ],
    },
    'overcast': {
        'visual': [
            "a flat grey lid of cloud seals the sky from rim to rim",
            "the overcast hangs low and featureless above the roofs",
            "the light filters down even and shadowless",
            "the crater rim has dissolved into the low grey",
            "everything reads dull and washed of colour",
            "the sky is one unbroken sheet of pewter",
            "the gutters wait dark and dry beneath the heavy cloud",
        ],
        'auditory': [
            "noise sits close and blunted beneath the cloud",
            "the overcast presses the street's clamour to a murmur",
            "far-off sounds arrive small and flattened",
            "everything seems to come from nearer than it is",
            "the processor's drone carries thick through the damp",
            "a hauler's horn flattens and dies under the grey",
            "the heavy air files the edge off every sound",
        ],
        'olfactory': [
            "moisture hangs held in the air, mineral and flat",
            "the street smells of rain that hasn't broken yet",
            "damp composite and cool steel weigh on the breath",
            "a stale, penned-in odour collects under the cloud",
            "the low sky traps yesterday's smells against the grating",
            "a faint mildew creeps out of the shaded corners",
        ],
        'tactile': [
            "the air sits heavy and tepid, neither warm nor cold",
            "a clammy stillness lies over the street",
            "the close air weighs down without a breath of wind",
            "a faint damp clings without ever quite settling",
            "the cloud seems to press on the shoulders",
            "every surface feels slightly tacky with held moisture",
        ],
        'atmospheric': [
            "the flat light bleeds the colour out of the whole street",
            "the street idles under the low, waiting cloud",
            "nothing throws a shadow in the even grey",
            "the drains sit ready and the sky withholds",
            "the grey stretches the day into one long pause",
            "the cloud lid leaves the street boxed and shut in",
        ],
    },
    'windy': {
        'visual': [
            "wind chases grit and torn wrappers down the open street",
            "gusts worry at coats and slap the hung signs about",
            "a sheet of loose panelling bangs somewhere out of sight",
            "dust spins up in brief whirls and scatters flat",
            "strung laundry cracks and bellies between the prefabs",
            "rooftop antennas bow and shiver in the blow",
            "a vendor's tarp tears half-free and flogs at its ties",
        ],
        'auditory': [
            "the wind moans long through the gaps between buildings",
            "loose metal clatters and bangs somewhere overhead",
            "the blow drags far voices in and buries the near ones",
            "a steady rushing fills the whole street",
            "signs creak and swing complaining on their mounts",
            "the gusts find the grating and whistle up through it",
            "something untied flaps in ragged, irregular snaps",
        ],
        'olfactory': [
            "the wind drags in smells from somewhere far and gone again",
            "grit and grime tumble past on every gust",
            "a cold mineral tang comes down off the crater",
            "each blow carries the scent of a different block",
            "ozone and dust ride the moving air",
            "the wind scours the street's own smells clean away",
            "a whiff of fried oil arrives sideways and vanishes",
        ],
        'tactile': [
            "the wind shoves cold and insistent down the street",
            "gusts fling grit at anything left in the open",
            "the moving air pulls the warmth off every surface",
            "the blow buffets and tugs with no steady rhythm",
            "wind-driven grit stings any bare skin it finds",
            "the cold airstream cuts through gaps and seams",
        ],
        'atmospheric': [
            "the wind has pushed most people into the building lee",
            "grit drifts and piles deep in the windward corners",
            "loose trash travels the whole length of the block",
            "banners and laundry never stop their snapping",
            "the open stretches belong wholly to the wind",
            "everything not tied down has shifted downwind",
        ],
    },
    'fog': {
        'visual': [
            "fog blurs the street to grey shapes and ringed lamps",
            "the far end of the block dissolves into murk",
            "each lamp wears a damp, glowing halo",
            "beads of fog stand on every rail and wire",
            "figures loom up close and melt away again",
            "the channel is a rumour somewhere out in the grey",
            "the mist closes the world down to a few wet metres",
        ],
        'auditory': [
            "the fog packs sound down to a near, padded hush",
            "footsteps seem to come from every direction at once",
            "water drips steadily from edges lost in the grey",
            "voices reach you with no body attached to them",
            "the murk turns sound around and flattens it",
            "the processor's hum comes adrift, with no source",
            "a cough somewhere close sounds oddly smothered",
        ],
        'olfactory': [
            "the fog tastes faintly of cold stone and rust",
            "wet metal and standing water hang on the still air",
            "a raw, mineral damp fills each breath",
            "the mist carries the flat smell of a dripping cellar",
            "old composite and corrosion thicken in the wet",
            "the cold has a clean, waterlogged edge",
            "the smell of the channel creeps in under the fog",
        ],
        'tactile': [
            "the fog hangs cold and wet against the face",
            "a clammy chill settles over the whole street",
            "wet beads gather and run on every cold surface",
            "the damp works in past collar and cuff",
            "the air feels thick and waterlogged to move through",
            "cold moisture films the rails and the grating",
        ],
        'atmospheric': [
            "fog runs in slow beads down every upright surface",
            "the lamps are reduced to soft, floating smears",
            "the street gives out into grey a dozen paces off",
            "the wet has made the grating slick and dark",
            "the mist drifts and pools between the buildings",
            "distance has stopped meaning much in the murk",
        ],
    },
    'rain': {
        'visual': [
            "rain falls straight and steady, pocking the puddles",
            "water spills off the eaves and sheets down the prefab faces",
            "the grating lies black and shining under the wet",
            "rain runs the lit signs to coloured smears",
            "puddles spread and link across the low ground",
            "the downpour softens the far buildings to grey",
            "runoff threads bright lines toward the channel grates",
        ],
        'auditory': [
            "rain drums an even rhythm on the roofs and eaves",
            "water chuckles and gulps down the choked drains",
            "a steady hiss of rain lies under everything",
            "drips rattle in uneven time from a hundred ledges",
            "the gutters run loud and full along the kerbs",
            "the patter rises and falls as the rain shifts",
            "somewhere a downpipe gargles and overflows",
        ],
        'olfactory': [
            "the rain raises a clean, washed smell off the grating",
            "wet composite and rust sharpen in the cool",
            "the dust is gone, and cold stone takes its place",
            "petrichor lifts from ground that was dry an hour ago",
            "rinsed metal and wet concrete fill the breath",
            "a faint reek of stirred-up drains rides the wet",
            "the cooled air comes scrubbed and faintly green",
        ],
        'tactile': [
            "the rain comes down cold and unhurried",
            "a wet chill soaks slowly into every surface",
            "the cold of it seeps into walls and grating alike",
            "everything in the open is running with water",
            "the rain beads cold and rolls off in steady lines",
            "the damp finds its way through to the skin",
        ],
        'atmospheric': [
            "the rain has driven off everyone but the hurried",
            "wide puddles stand across the low grating",
            "water gets everywhere, hunting for the drains",
            "the gutters run brimming and noisy",
            "the dripping outlasts the worst of the fall by a long way",
            "the street has gone slick and dark end to end",
        ],
    },
    'light_rain': {
        'visual': [
            "a fine rain freckles the puddles and beads the rails",
            "the drizzle drifts more than it falls",
            "a thin wet sheen darkens the grating",
            "the light rain hazes the glow of the signs",
            "scattered drops dent the standing water",
            "the far end of the street goes soft and grey",
            "wet spots spread slow across the dusty walls",
        ],
        'auditory': [
            "the drizzle whispers across the eaves",
            "a soft patter comes and goes on the roofs",
            "drips tick at long, irregular intervals",
            "the rain barely rises over the street's hum",
            "a faint hiss touches the grating now and then",
            "the gutters trickle where they'd usually run",
            "the rain is more felt than heard",
        ],
        'olfactory': [
            "the drizzle wakes a faint clean note from the composite",
            "the dust is dampened but not washed away",
            "a thread of petrichor laces the cool air",
            "the faint smell of rinsed metal drifts up",
            "wet dust and cool stone mingle on the breath",
            "a thin green freshness edges into the street",
            "the air carries the first hint of real rain",
        ],
        'tactile': [
            "a fine, cool damp settles out of the drizzle",
            "the light rain leaves a thin film on every surface",
            "the wet barely chills the grating, but it chills it",
            "a slow dampness gathers on rail and wall",
            "the mist of it clings light on the skin",
            "cool moisture beads without ever quite running",
        ],
        'atmospheric': [
            "the drizzle has slowed the street, not cleared it",
            "thin films of water shine on the low grating",
            "the drains take the trickle without filling",
            "damp creeps slowly across every surface",
            "people loiter under the eaves in no real hurry",
            "the light wet leaves the street muted and soft",
        ],
    },
    'soft_snow': {
        'visual': [
            "soft snow drifts down in slow, fat flakes",
            "white settles along the rails and dark ledges",
            "flakes wheel and tumble in the still air",
            "an even coat of white lies thin on the grating",
            "the snow blurs the hard lines of the prefabs",
            "flakes melt away into the dark standing puddles",
            "the streetlamps catch the falling snow in soft cones",
        ],
        'auditory': [
            "the snow lays a soft, padded quiet over the street",
            "sound drops dead and close underfoot",
            "boots crunch faint in the new fall",
            "the street has gone hushed beneath the drift",
            "even the processor's hum comes blanketed",
            "the snowfall swallows the nearer noises whole",
            "the quiet has a muffled, woollen weight",
        ],
        'olfactory': [
            "the air comes clean and cold, scrubbed by the snow",
            "the snow carries a sterile chill and little else",
            "a sharp, mineral cold edges each breath",
            "the falling white strips the street of its smells",
            "cold iron and clean ice are all that reach the nose",
            "the chilled air smells of almost nothing at all",
            "the faint tang of the channel is frozen out",
        ],
        'tactile': [
            "the cold bites dry and clean",
            "a still, deep chill comes down with the snow",
            "the cold sits unmoving over the whitening street",
            "the chill works slow into every surface",
            "flakes land and melt cold against the skin",
            "the air has a crisp, settled coldness",
        ],
        'atmospheric': [
            "snow gathers untouched in the quiet corners",
            "the new coat takes the print of every footstep",
            "the street lies slow and hushed under the white",
            "snow banks soft against the windward walls",
            "the cold has thinned the crowd to a few dark figures",
            "everything looks briefly cleaner under the fresh fall",
        ],
    },
    'hard_snow': {
        'visual': [
            "snow drives down thick and fast, heaping on every ledge",
            "the heavy fall greys the far prefabs to ghosts",
            "drifts bank deep along the bases of the walls",
            "snow blows across the grating in low sheets",
            "the white deepens visibly by the minute",
            "fresh tracks fill almost before they're made",
            "the lamps struggle, haloed and dim, through the fall",
        ],
        'auditory': [
            "the heavy snow muffles the street to a deep hush",
            "wind drives the fall with a low, steady rush",
            "footfalls vanish into the smothering snow",
            "sound dies fast in the thick of it",
            "the processor's hum is buried under the fall",
            "the snowfall deadens everything within reach",
            "a branch of wind whines past, then is gone",
        ],
        'olfactory': [
            "the cold comes sharp and scentless off the snow",
            "hard ice and iron bite at every breath",
            "the driving fall strips warmth and smell alike",
            "nothing reaches the nose but bitter cold",
            "the air carries only frozen metal and snow",
            "the deep chill numbs the street's odours away",
            "even the processor's reek is frozen out",
        ],
        'tactile': [
            "the cold drives hard at the back of the snow",
            "wind-blown snow piles cold against every wall",
            "the chill sinks fast into anything exposed",
            "the deep cold of the fall settles bone-deep",
            "snow stings where the wind flings it",
            "the cold finds every gap in collar or cuff",
        ],
        'atmospheric': [
            "drifts climb the windward walls and bury the low rails",
            "the heavy fall has emptied the street to a few",
            "snow piles deep enough to drown the grating",
            "the white shuts off the far end of the block",
            "every track and print fills in behind",
            "the street is fast disappearing under the fall",
        ],
    },
    'blizzard': {
        'visual': [
            "the blizzard drives snow flat and sidelong down the street",
            "the white-out shuts sight down to arm's length",
            "snow tears past in blinding, ragged sheets",
            "the prefabs across the way are simply gone",
            "drifts pile fast and deep in the screaming wind",
            "the storm scrubs the street out to blank white",
            "the lamps are lost, swallowed whole in the blow",
        ],
        'auditory': [
            "the blizzard roars and drowns out all else",
            "wind shrieks through every gap and around every corner",
            "snow and wind fill the street with one long howl",
            "nothing carries through the storm's bellow",
            "ice and grit crack and rattle past on the gale",
            "the wind's howl swells and sinks but never quits",
            "a deep moan runs under the shriek of the storm",
        ],
        'olfactory': [
            "the storm scours the air to a bitter, empty cold",
            "driving ice stings the inside of each breath",
            "nothing rides the gale but the cold itself",
            "the blizzard tears every smell away",
            "only hard ice and frozen steel reach the nose",
            "the freezing blast numbs the senses to anything",
            "the air is wiped clean and dead of scent",
        ],
        'tactile': [
            "the wind tears bitter cold straight down the street",
            "the driving cold knifes through every seam",
            "there is no still air to escape the gale's bite",
            "wind packs snow and cold into anything it strikes",
            "the storm flays exposed skin in seconds",
            "the cold is total, brutal, and everywhere at once",
        ],
        'atmospheric': [
            "the blizzard has scoured the street empty",
            "drifts heap fast behind anything that breaks the wind",
            "the white-out eats everything past a reaching arm",
            "the gale crams snow into every crack and corner",
            "nothing holds still anywhere in the storm",
            "the street has become one howling field of white",
        ],
    },
    'dry_thunderstorm': {
        'visual': [
            "lightning forks across the cloud and not a drop falls",
            "the dry storm strobes the street stark and white",
            "thunderheads stack black and heavy over the rim",
            "the storm's wind kicks dust racing down the block",
            "each flash freezes the street hard-edged for an instant",
            "the black cloud churns and roils without breaking",
            "distant strikes flicker along the crater's edge",
        ],
        'auditory': [
            "thunder rolls and cracks across the parched sky",
            "the air hums faintly an instant before each strike",
            "thunder booms and slaps flat off the prefab walls",
            "the wind rattles grit along the grating",
            "a sharp crack splits the heavy quiet",
            "long peals fade out and then return",
            "the storm grumbles, building, somewhere overhead",
        ],
        'olfactory': [
            "ozone bites the air after every strike",
            "the storm leaves a scorched, metallic edge on the wind",
            "dust and ozone tumble together on the gusts",
            "a burnt, electric smell hangs over the street",
            "hot grit and lightning sharpen the breath",
            "the parched air carries the reek of struck metal",
            "a charred tang settles in after the loudest cracks",
        ],
        'tactile': [
            "the air hangs hot, parched, and charged",
            "the storm's wind drives warm grit down the street",
            "a dry heat sits heavy under the churning cloud",
            "the air feels tight and electric between the peals",
            "the hair lifts faintly as the charge builds",
            "warm gusts shove past, dry as a furnace",
        ],
        'atmospheric': [
            "the dry storm has people eyeing the sky and the doors",
            "each flash throws hard shadows the length of the grating",
            "dust streams down the street on the storm's breath",
            "the air pulls taut in the gaps between thunder",
            "the cloud grinds overhead and refuses to break",
            "the whole street waits for a rain that won't come",
        ],
    },
    'rainy_thunderstorm': {
        'visual': [
            "lightning lights the falling rain in sheets of white",
            "the downpour drives hard beneath cracking thunder",
            "each flash freezes the rain dead in mid-fall",
            "rain sheets off every eave as the storm breaks open",
            "the grating runs deep and quick with storm-water",
            "the far buildings vanish behind the driving rain",
            "strikes light the churning cloud from within",
        ],
        'auditory': [
            "thunder booms over the roar of the driving rain",
            "rain hammers the roofs under long rolls of thunder",
            "water-noise and thunderclap fill the whole street",
            "a sharp crack splits the steady roar of the rain",
            "runoff rushes loud and brown through the channels",
            "the downpour and thunder bury everything else",
            "each peal rolls away and the rain swells to fill it",
        ],
        'olfactory': [
            "ozone and rain mix sharp and cold on the wind",
            "the storm churns up wet stone and struck metal",
            "lightning leaves the wet air electric and raw",
            "cold rain and ozone sting the breath together",
            "the downpour rinses the air to mineral and charge",
            "wet composite and a burnt edge ride the gusts",
            "the flooded drains push up a sour, stirred reek",
        ],
        'tactile': [
            "the rain drives down cold and hard from every angle",
            "the cold downpour pools and soaks across the grating",
            "the storm's wind throws the rain sidelong",
            "the wet chill drives deep into every surface",
            "the rain hits hard enough to feel through cloth",
            "cold water and cold air bite together",
        ],
        'atmospheric': [
            "the storm has cleared the street of all but the desperate",
            "runoff floods the low grating and races the drains",
            "each flash throws the drenched street into hard relief",
            "water stands deep where the drains have fallen behind",
            "the storm pounds the street without a pause",
            "the gutters can't take it, and the water spreads",
        ],
    },
    'gray_pall': {
        'visual': [
            "a thick grey pall hangs over the street, dimming the lamps",
            "the haze blurs the near prefabs to soft grey blocks",
            "a film of particulate greys over every surface",
            "the light fights down weak through the heavy murk",
            "the pall lowers the sky to a dirty, close ceiling",
            "the crater rim is gone entirely behind the haze",
            "ash sifts down slow and settles pale on the dark",
        ],
        'auditory': [
            "sound comes blunted and flat through the heavy pall",
            "the murk smothers the street's noise",
            "far-off sounds reach you dulled and close",
            "the processor's hum flattens to a buried drone",
            "everything seems muffled under a held breath",
            "noise drags thick and slow through the haze",
            "a cough carries oddly far in the smothered air",
        ],
        'olfactory': [
            "the pall is acrid, catching at the back of the throat",
            "the haze tastes of ash and scorched industry",
            "a chemical grit settles bitter on the tongue",
            "soot and burnt residue weigh down each breath",
            "the murk carries the flavour of the smokestacks",
            "a sharp, throat-scraping reek hangs everywhere",
            "the air leaves a metallic, burnt aftertaste",
        ],
        'tactile': [
            "the air sits warm, thick, and grit-laden",
            "fine ash settles dry on every surface",
            "the heavy pall hangs close and motionless",
            "the gritty air leaves a film on whatever it touches",
            "particulate prickles dry at the eyes and throat",
            "the warm murk feels used and unclean",
        ],
        'atmospheric': [
            "the pall coats every surface in a skin of grey grit",
            "people cross the murk with their mouths covered",
            "the haze dulls the signs to faint, smeared glows",
            "grey ash settles slow and even over everything",
            "the heavy air lies low and refuses to move",
            "the whole street wears a dull, soot-dimmed cast",
        ],
    },
    'tox_rain': {
        'visual': [
            "a dismal acid drizzle beads up oily and hissing on warm metal",
            "the tox rain leaves a slick, off-colour film over everything",
            "runoff carries threads of unnatural colour to the drains",
            "discoloured water pools in iridescent skins on the grating",
            "the rain bleaches pale streaks down every surface it crosses",
            "the toxic fall hazes the street a sickly yellow-grey",
            "where it pools, the water eats faint pits in the metal",
        ],
        'auditory': [
            "the tox rain hisses and spits with a chemical fizz",
            "the corrosive drops pop and sizzle on warm metal",
            "a warning chime repeats, ignored, from a far speaker",
            "the rain ticks and fizzes against the eaves",
            "runoff gurgles thick and sluggish down the drains",
            "the fall lands with an oily weight, heavier than water",
            "a faint, constant sizzle underlies the patter",
        ],
        'olfactory': [
            "the air stings, sharp with chemical reek",
            "the tox rain burns at the nose and the back of the throat",
            "acrid fumes lift from every pooling drop",
            "a caustic bite rides each breath",
            "chemical sting and rot hang together in the wet",
            "the rain leaves a taste of solvent and slow decay",
            "a sweetish, poisonous note edges the damp",
        ],
        'tactile': [
            "the wet air carries a faint chemical sting",
            "the acid drizzle eats slick wherever it gathers",
            "a low chemical burn rides the damp",
            "the corrosive wet clings to everything in the open",
            "the rain prickles caustic on any bare skin",
            "the air feels greasy and faintly raw",
        ],
        'atmospheric': [
            "the tox rain has driven everyone under cover or indoors",
            "discoloured water pools where the drains run slow",
            "an oily sheen slicks every exposed surface",
            "the few still out keep skin and mouth well covered",
            "the rain pits and stains whatever it can't dissolve",
            "the street empties fast under the burning fall",
        ],
    },
    'sandstorm': {
        'visual': [
            "grit drives down the street in stinging brown sheets",
            "blown sand shuts visibility down to a few paces",
            "the storm hazes the whole street to swirling ochre",
            "sand streams low and thick across the grating",
            "the far prefabs vanish behind the flying grit",
            "fine sand heaps in the lee of every wall",
            "the lamps are dim brown smears in the blowing dust",
        ],
        'auditory': [
            "the sandstorm hisses and roars with driven grit",
            "sand rattles hard against metal and dark glass",
            "the wind drives a steady, abrasive rush",
            "grit scours every surface with a dry, ceaseless hiss",
            "the storm's roar buries the nearer sounds",
            "blown sand ticks and patters across the signs",
            "a high whine rides the wind through the gaps",
        ],
        'olfactory': [
            "the air is thick with dry dust and hot mineral grit",
            "blown sand coats the mouth with a dry, chalky film",
            "every breath comes loaded with fine grit",
            "dust and sun-baked stone choke the driving air",
            "the dry air rasps with powdered mineral",
            "grit settles dry and metallic on the tongue",
            "a scorched, gritty heat fills the lungs",
        ],
        'tactile': [
            "the wind drives hot grit that scours every surface",
            "blown sand abrades anything left in the open",
            "the gritty wind sandblasts walls and signs alike",
            "the hot, abrasive air leaves nothing untouched",
            "sand stings hard against any bare skin",
            "the heat and the grit ride the wind together",
        ],
        'atmospheric': [
            "the sandstorm has cleared the street to the desperate few",
            "fine sand works into every seam and crack",
            "grit piles deep against the windward walls",
            "the blown sand scours and dulls every surface",
            "drifts of sand fill the low grating",
            "the whole street is lost in driving ochre",
        ],
    },
    'blind_fog': {
        'visual': [
            "the blind fog shuts sight down to less than arm's length",
            "the grating itself vanishes underfoot in the white",
            "nothing shows through the dense murk but the nearest shapes",
            "even close lamps drown to faint, formless smears",
            "the fog wipes the street out to blank grey",
            "a shape a single pace off looms and is gone",
            "the white presses up against the eyes like a wall",
        ],
        'auditory': [
            "the dense fog turns every sound around and flattens it",
            "footsteps arrive from impossible directions",
            "sound is muffled to the point of seeming to come from nowhere",
            "voices reach you close and bodiless out of the white",
            "the murk strips the direction from every noise",
            "only the drip of water carries clear",
            "your own footfalls sound oddly distant",
        ],
        'olfactory': [
            "the fog is thick and wet, heavy with cold mineral",
            "each breath draws in cold, suspended water",
            "the dense damp coats the mouth and nose",
            "wet stone and rust hang heavy on the dead air",
            "the saturated air tastes of cold metal",
            "the murk holds the street's smells thick and close",
            "a raw, waterlogged chill fills the lungs",
        ],
        'tactile': [
            "the dense fog hangs cold and soaking against the face",
            "a heavy wet cold presses in from the white",
            "the saturated murk beads and runs off everything",
            "the damp is thick enough to feel as you move through it",
            "cold moisture works in past every seam",
            "the wet chill clings and won't be shrugged off",
        ],
        'atmospheric': [
            "the blind fog has all but stopped movement on the street",
            "moisture sheets down every upright surface",
            "the lamps disappear completely a few paces off",
            "the dense white has slicked the grating treacherous",
            "the fog stands so thick it seems to push inward",
            "the street has shrunk to the few feet you can see",
        ],
    },
    'heavy_fog': {
        'visual': [
            "heavy fog closes the street to grey shapes within a few paces",
            "thick fog swallows the prefabs whole",
            "the lamps show only as drowned, floating haloes",
            "the fog beads heavy and runs off every edge",
            "shapes resolve only when they're nearly upon you",
            "the far half of the block has simply ceased to exist",
            "the murk thickens and thins but never lifts",
        ],
        'auditory': [
            "the heavy fog packs the street down to a padded hush",
            "sound arrives turned-around and bodiless",
            "footsteps approach out of nowhere in the thick of it",
            "the fog flattens the processor's hum to a drone",
            "voices carry oddly close and placeless",
            "the steady drip of water is the clearest sound left",
            "a far-off call comes muffled and strange",
        ],
        'olfactory': [
            "the heavy fog is cold and wet, dense with mineral damp",
            "saturated air condenses on every cold surface",
            "wet stone and old metal lie heavy on the breath",
            "the cold damp coats the mouth and throat",
            "the murk holds the street's smells suspended and close",
            "rust and standing water thicken each breath",
            "a deep, cellar-cold dampness fills the air",
        ],
        'tactile': [
            "the heavy fog hangs cold and soaking wet",
            "a clammy chill stands beaded on every surface",
            "the wet cold works deep into everything",
            "moisture sheets cold off rail and grating",
            "the damp settles heavy on the shoulders",
            "the cold wet clings to cloth and skin alike",
        ],
        'atmospheric': [
            "the heavy fog has slowed the street to a crawl",
            "moisture runs in sheets down every upright face",
            "the murk drowns the lamps a few paces off",
            "the slick fog beads cold on rail and grating",
            "the thick grey pools and drifts between the prefabs",
            "the whole street has gone close and shut-in",
        ],
    },
    'flashstorm': {
        'visual': [
            "the flashstorm strobes the street in rapid white stutters",
            "discharge forks across the sky faster than the eye can hold",
            "each burst freezes the street and leaves it burned on the eye",
            "the storm flickers like a failing tube, all white and black",
            "lightning chains across the cloud in unbroken bursts",
            "the flashes come too fast to count, blanking everything white",
            "the whole sky seethes with stuttering light",
        ],
        'auditory': [
            "thunder runs together into one continuous, tearing roar",
            "the air cracks and buzzes between the rapid strikes",
            "overlapping thunder fills the street wall to wall",
            "each flash lands with a near-instant, splitting crack",
            "the rolling concussion never fades before the next",
            "the discharge sizzles and snaps in the charged air",
            "the noise is a single unending barrage",
        ],
        'olfactory': [
            "ozone saturates the air, sharp enough to taste",
            "the charged air reeks of lightning and scorched metal",
            "each strike thickens the ozone bite on the breath",
            "a burnt, electric stink hangs over everything",
            "a hard metallic tang coats the mouth",
            "ozone and seared dust lie heavy on the air",
            "the reek of struck metal builds with every burst",
        ],
        'tactile': [
            "the charged air prickles and crackles",
            "the air hangs hot and electric between the bursts",
            "each strike leaves the air taut and humming",
            "a static charge stands heavy over the whole street",
            "the hair lifts and the skin prickles in the field",
            "the heat of the discharge rolls past in waves",
        ],
        'atmospheric': [
            "the flashstorm has driven everyone off the open street",
            "each burst throws the street into hard white relief",
            "the strobing leaves everything flickering black and white",
            "the storm hammers the sky without a pause",
            "the lamps are lost under the storm's white stutter",
            "the charged air keeps the whole street on edge",
        ],
    },
    'torrential_rain': {
        'visual': [
            "the torrential rain falls in solid grey sheets",
            "water comes down hard enough to blur the nearest prefabs",
            "the downpour overwhelms the drains and floods the grating",
            "rain sheets off every eave in unbroken curtains",
            "standing water spreads deep and fast across the street",
            "the deluge greys out everything past a few paces",
            "the channel grates vanish under racing brown water",
        ],
        'auditory': [
            "the torrential rain roars on the roofs and the grating",
            "the downpour drowns every other sound beneath its hammering",
            "water thunders down the drains and overruns them",
            "the deluge fills the street with one unbroken roar",
            "runoff rushes deep and loud through every channel",
            "the rain comes down too loud to speak over",
            "a hard, flat drumming fills the whole block",
        ],
        'olfactory': [
            "the deluge floods the air with wet stone and cold mineral",
            "the rain rinses everything to a cold, clean damp",
            "wet composite and runoff drown out every other smell",
            "the downpour leaves nothing on the breath but cold rain",
            "the overrun drains push up a sour reek of wet rot",
            "the soaked air hangs thick with mineral chill",
            "the smell of the swollen channel rides the flood",
        ],
        'tactile': [
            "the rain hammers down cold and heavy",
            "the deluge drives cold runoff across the grating",
            "the downpour soaks everything in the open in seconds",
            "the cold weight of the rain pounds at every surface",
            "the rain hits hard enough to sting",
            "cold water sheets off every edge in a steady flood",
        ],
        'atmospheric': [
            "the torrential rain has emptied the street completely",
            "floodwater stands deep where the drains have given up",
            "runoff races the grating and overruns the channels",
            "the deluge pours off every roof in solid curtains",
            "water finds every low point and pools deep",
            "the whole street has become a shallow, racing river",
        ],
    },
    'foggy_rain': {
        'visual': [
            "rain falls through a clinging fog, doubling the grey",
            "fog and rain together close the street to a few paces",
            "the wet murk drowns the lamps to faint haloes",
            "rain pocks the puddles beneath a low ceiling of fog",
            "the fogged rain softens everything to vague shapes",
            "drizzle and mist merge into a single wet wall",
            "the far buildings are lost in a streaming grey blur",
        ],
        'auditory': [
            "the fog packs the patter of rain down to a hush",
            "dripping and soft rain blur together in the murk",
            "sound arrives flattened and turned around in the wet fog",
            "the rain whispers under the fog's padded quiet",
            "runoff trickles unseen somewhere in the grey",
            "the processor's hum comes drowned and directionless",
            "every sound is wrapped and muffled in the wet",
        ],
        'olfactory': [
            "the air is doubly wet, cold with fog and rain at once",
            "wet stone and cold mineral hang thick in the saturated air",
            "each breath draws in cold, suspended water",
            "the fogged rain smells of rust and standing water",
            "a cold, mineral damp coats the mouth",
            "the murk holds the street's smells thick and wet",
            "a raw, waterlogged chill fills every breath",
        ],
        'tactile': [
            "the air hangs cold, wet, and clinging",
            "a soaking chill settles out of the fogged rain",
            "the doubled damp works cold into everything",
            "moisture clings cold to every surface at once",
            "the wet murk beads and runs down rail and wall",
            "the chill soaks in past collar and cuff",
        ],
        'atmospheric': [
            "the fogged rain has slowed the street to almost nothing",
            "moisture sheets and beads on every surface at once",
            "the lamps drown to faint haloes in the wet grey",
            "fog and runoff have slicked the grating treacherous",
            "the wet murk pools and drifts between the prefabs",
            "the street has gone close, grey, and dripping",
        ],
    },
}


def _rotate(pool, start, count):
    """Take `count` distinct items from `pool` beginning at offset `start`."""
    n = len(pool)
    return [pool[(start + k) % n] for k in range(min(count, n))]


def _build_weather_messages():
    """Compose the full weather x time-of-day x sense message dict.

    Deterministic (no randomness at import). Each weather type picks its own
    variant of the diurnal light/activity lines (by weather index), and the
    weather pools rotate by time index, so adjacent hours and neighbouring
    weather types draw different lines while every line stays standalone.
    """
    region = {}
    for w_i, (weather, pools) in enumerate(WEATHER_POOLS.items()):
        for i, period in enumerate(TIME_PERIODS):
            key = f"{weather}_{period}"
            light = TIME_LIGHT[period][w_i % len(TIME_LIGHT[period])]
            activity = TIME_ACTIVITY[period][w_i % len(TIME_ACTIVITY[period])]
            region[key] = {
                'visual': [light] + _rotate(pools['visual'], i, 2),
                'auditory': _rotate(pools['auditory'], i, 3),
                'olfactory': _rotate(pools['olfactory'], i, 3),
                'tactile': _rotate(pools['tactile'], i, 2),
                'atmospheric': [activity] + _rotate(pools['atmospheric'], i * 2, 2),
            }
    return region


# Regional weather message pools (future: 'mars_desert', 'orbital_station', ...).
WEATHER_MESSAGES = {
    'default': _build_weather_messages(),
}
