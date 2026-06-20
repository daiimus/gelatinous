"""
Weather Message Pools

Ambient, perception-gated weather observations for outdoor rooms. The weather
system flattens the perceivable-sense lines for the current weather+time into
one pool and shows a couple at random, so every line is written as a single
standalone observation that reads cleanly beside any other.

Principles (shared with the room and crowd authoring):

  * OFFER concrete observation, don't narrate how to feel. Ground it in the
    colony's own texture (prefab sprawl, the grating, the channel, the crater
    rim, the processor's hum).
  * AMBIENCE, NOT ACTION ON THE PLAYER. Describe the weather and what it does to
    the street and the air, not things done to the character. Plain sensation
    ("the cold bites", "the air stings") is fine; it doesn't demand a reaction
    the text can't deliver.
  * NAME THE SUBJECT. The wind's howl, the crowd, the storm -- keep referents
    concrete.

Five sense layers, matching the room model: visual / auditory / olfactory /
tactile / atmospheric. The system gates visual on sight and auditory on
hearing; olfactory, tactile and atmospheric always show.

The big WEATHER_MESSAGES dict (every weather type x time-of-day x sense) is
built deterministically at import from:

  * WEATHER_POOLS -- per weather type, observational lines per sense category.
  * TIME_LIGHT / TIME_ACTIVITY -- diurnal light-level and street-activity lines,
    phrased to hold true under any weather (ambient light and foot traffic,
    never clear-sky or long-distance visibility).

Rotating each pool by the time index gives per-time variation without random
churn at import.
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

# Ambient light level by time of day. Phrased in terms of brightness and the
# streetlamps, so each line holds true under clear sky OR thick fog/storm.
TIME_LIGHT = {
    'pre_dawn': "the streetlamps still hold against the dark before dawn",
    'dawn': "the light comes up thin and grey",
    'early_morning': "the early light strengthens, low and pale",
    'late_morning': "the light has filled out into full day",
    'midday': "the light sits flat and full overhead",
    'early_afternoon': "the afternoon light holds steady",
    'late_afternoon': "the light dims and lengthens toward evening",
    'dusk': "the light drains toward dusk and the lamps flicker on",
    'early_evening': "the streetlamps carry the early evening",
    'late_evening': "the late lamps pool yellow on the grating",
    'night': "the dark sits heavy between the streetlamps",
    'late_night': "the streetlamps burn alone in the late hours",
}

# Street activity by time of day -- observational, weather-agnostic.
TIME_ACTIVITY = {
    'pre_dawn': "almost no one is out at this hour",
    'dawn': "the first-shift traffic begins to stir",
    'early_morning': "the morning crowd thickens on the grating",
    'late_morning': "the street runs at its working pace",
    'midday': "midday traffic crosses steadily",
    'early_afternoon': "the afternoon foot traffic holds steady",
    'late_afternoon': "the shift change crowds the street",
    'dusk': "the evening crowd starts to fill the street",
    'early_evening': "the street is busy with people off shift",
    'late_evening': "the late crowd thins toward the bars and cubes",
    'night': "the street has emptied to the night people",
    'late_night': "the street is all but deserted",
}

# Per-weather observational pools. Lines are time-agnostic weather facts; the
# diurnal light/activity lines above carry the time of day.
WEATHER_POOLS = {
    'clear': {
        'visual': [
            "the sky is open and clear, the crater rim a hard line in the distance",
            "the grating is bone-dry and the gutters sit empty",
            "dust hangs lazily in the still, clear air",
            "the open sky stretches unbroken over the prefab roofs",
            "heat-shimmer rises off the dry grating",
            "nothing moves in the still air but drifting dust",
        ],
        'auditory': [
            "sounds carry clean and far in the still air",
            "the street's noise stands out sharp with no weather to muffle it",
            "a loose panel ticks somewhere in the dry stillness",
            "footsteps and voices travel a long way in the calm",
            "the processor's hum is the only constant on the still air",
            "a hauler's engine carries from blocks away",
        ],
        'olfactory': [
            "the dry air carries dust and warm metal",
            "ozone and machine oil ride the dry air",
            "warm grating gives off a faint smell of heated composite",
            "the still air pools the street's own smells close",
            "a dry mineral edge rides the clear air off the crater",
            "there's nothing on the air but dust and the distant processor",
        ],
        'tactile': [
            "the dry air sits warm and unmoving",
            "heat radiates up off the bone-dry grating",
            "the still air holds the day's warmth close to the ground",
            "nothing stirs the warm, dry air",
        ],
        'atmospheric': [
            "the dry weather has people out and unhurried",
            "the gutters and drains sit dry and idle",
            "the clear light leaves the street's grime in sharp relief",
            "dust collects undisturbed in the corners",
            "without weather, the street is just itself, and no better for it",
        ],
    },
    'overcast': {
        'visual': [
            "a flat grey overcast seals the sky from rim to rim",
            "the cloud lid sits low and featureless over the prefab roofs",
            "the light comes through grey and even, and nothing casts a shadow",
            "the crater rim is lost in the low grey",
            "the overcast presses the light down flat and colourless",
            "no break shows anywhere in the grey",
        ],
        'auditory': [
            "sound sits close and flat under the heavy cloud",
            "the overcast deadens the street's noise to a murmur",
            "distant sounds come muffled through the grey",
            "everything sounds nearer than it is",
            "the processor's hum carries dull through the damp air",
            "a hauler's horn flattens out under the cloud",
        ],
        'olfactory': [
            "the air is damp and still, heavy with held moisture",
            "a flat mineral damp hangs under the cloud",
            "the still air smells of rain that hasn't come",
            "damp composite and cold metal ride the heavy air",
            "the overcast traps the street's smells low and close",
            "moisture sits in the air without falling",
        ],
        'tactile': [
            "the air hangs damp and heavy, neither warm nor cold",
            "a clammy stillness sits over the street",
            "the heavy air presses close without a breath of wind",
            "the damp settles cool and unmoving over everything",
        ],
        'atmospheric': [
            "the flat grey light drains the colour out of everything",
            "the street waits under the low cloud",
            "no shadows fall under the even grey light",
            "the drains sit ready but dry",
            "the grey holds the day in a kind of pause",
        ],
    },
    'windy': {
        'visual': [
            "wind drives grit and torn paper down the street in fits",
            "gusts snatch at coats and tug at the hung signage",
            "a loose panel bangs somewhere out of sight in the wind",
            "dust devils spin up off the grating and scatter",
            "laundry and banners snap taut between the prefabs",
            "the wind whips a vendor's tarp half off its frame",
        ],
        'auditory': [
            "the wind moans through the gaps between the buildings",
            "loose metal rattles and bangs somewhere in the gusts",
            "the wind buries the near sounds and carries the far ones",
            "a steady rush of wind fills the street",
            "signage creaks and swings on its mounts",
            "the gusts whistle up through the grating underfoot",
        ],
        'olfactory': [
            "the wind carries smells from blocks away and gone again",
            "grit and dust ride the moving air",
            "the wind brings a cold mineral edge down off the crater",
            "each gust smells of somewhere else",
            "dust and ozone ride the driving air",
            "the moving air strips the street of its settled smells",
        ],
        'tactile': [
            "the wind shoves cold and steady down the street",
            "the gusts fling grit and buffet everything left in the open",
            "the moving air strips the warmth off every surface",
            "the wind worries at every loose edge and seam",
        ],
        'atmospheric': [
            "the wind has driven most people into the lee of the buildings",
            "grit collects deep in every windward corner",
            "loose trash travels the whole length of the street",
            "the gusts keep the laundry and banners in constant motion",
            "the wind owns the open stretches",
        ],
    },
    'fog': {
        'visual': [
            "fog softens the street to grey shapes and haloed lamps",
            "the far end of the street is lost in fog",
            "the lamps wear damp halos in the murk",
            "fog beads cold on every rail and surface",
            "shapes loom up and fade in the drifting grey",
            "a light mist hangs in the air, softening the prefabs down the street to grey outlines",
        ],
        'auditory': [
            "the fog muffles sound to a close, padded quiet",
            "footsteps come from nowhere and everywhere in the murk",
            "dripping carries from edges you can't see",
            "voices arrive disembodied through the fog",
            "sound comes flattened and turned around by the fog",
            "the processor's hum comes muffled and directionless",
        ],
        'olfactory': [
            "the fog is wet and cold, tasting of mineral and metal",
            "damp condenses cold on every surface",
            "the heavy wet air holds the street's smells suspended",
            "cold moisture and rust ride every breath",
            "the fog smells of standing water and cold stone",
            "wet composite and old metal thicken the air",
        ],
        'tactile': [
            "the fog hangs cold and wet, beading on every surface",
            "a clammy damp settles over the street",
            "the wet cold of the fog works into everything",
            "moisture gathers cold on rail and grating alike",
        ],
        'atmospheric': [
            "the fog beads and runs down every vertical surface",
            "the lamps show only as soft haloes in the murk",
            "the street fades to grey a dozen paces off",
            "moisture slicks the grating and the rails",
            "the fog drifts and eddies between the prefabs",
        ],
    },
    'rain': {
        'visual': [
            "rain falls steady and straight, dimpling the puddles",
            "rain sheets off the prefab eaves and runs the gutters brown with the day's dust",
            "the grating shines black and wet under the rain",
            "rain streaks the lit signage and runs the dark viewports",
            "puddles spread and join across the low grating",
            "the rain greys out the far end of the street",
        ],
        'auditory': [
            "rain drums steady on the eaves and roofs",
            "water gurgles down the drains and overruns the gutters",
            "the hiss of rain fills the street",
            "drips rattle from a hundred ledges and edges",
            "the downpour eases to a steady patter",
            "runoff rushes along the channel grates",
        ],
        'olfactory': [
            "the rain brings up the clean wet smell of washed grating",
            "wet composite and rust ride the rain-cooled air",
            "the rain cuts the dust and leaves cold mineral damp",
            "petrichor rises off the long-dry surfaces",
            "the air smells of rain and rinsed metal",
            "cold wet stone and runoff ride every breath",
        ],
        'tactile': [
            "the rain falls cold and steady over everything",
            "a wet chill settles into every surface",
            "the cold of the rain seeps into the grating and the walls",
            "everything left in the open runs with cold water",
        ],
        'atmospheric': [
            "the rain has cleared the street of all but the hurried",
            "puddles spread wide across the low grating",
            "water runs everywhere, finding the drains",
            "the gutters run full and loud",
            "everything keeps dripping long after the heaviest passes",
        ],
    },
    'light_rain': {
        'visual': [
            "a light rain stipples the puddles and beads the rails",
            "fine rain drifts more than it falls",
            "the grating darkens and shines under the drizzle",
            "thin rain hazes the lit signage",
            "scattered drops dimple the standing water",
            "a soft drizzle blurs the far end of the street",
        ],
        'auditory': [
            "the light rain whispers on the eaves",
            "a soft patter comes and goes on the roofs",
            "drips tick irregular from the ledges",
            "the drizzle barely lifts above the street's hum",
            "fine rain hisses faintly on the grating",
            "the gutters trickle rather than run",
        ],
        'olfactory': [
            "the drizzle raises a faint clean smell of damp composite",
            "light rain cuts the dust without washing it away",
            "cool damp and a thread of petrichor ride the air",
            "the air smells faintly of rinsed metal",
            "wet dust and cool mineral ride the soft rain",
            "a light wet edge rides the air",
        ],
        'tactile': [
            "a fine cold damp settles out of the drizzle",
            "the light rain leaves a cool film on every surface",
            "the drizzle barely wets the grating, just enough to chill it",
            "a cool dampness gathers slowly on everything",
        ],
        'atmospheric': [
            "the light rain hasn't cleared the street, only slowed it",
            "thin films of water shine on the grating",
            "the drains take the drizzle without filling",
            "damp gathers slowly on every surface",
            "people move under the eaves without real hurry",
        ],
    },
    'soft_snow': {
        'visual': [
            "soft snow drifts down in slow, fat flakes",
            "snow settles white on the rails and the dark ledges",
            "flakes turn and drift in the still air",
            "the grating wears a thin even coat of white",
            "snow softens the hard edges of the prefabs",
            "fresh flakes vanish into the dark puddles",
        ],
        'auditory': [
            "the snow brings a soft, padded quiet to the street",
            "sound falls dead and close under the snow",
            "footsteps crunch faintly in the fresh fall",
            "the street is hushed beneath the drifting snow",
            "even the processor's hum comes muffled",
            "the snow swallows the nearer sounds",
        ],
        'olfactory': [
            "the air is cold and clean, scrubbed by the snow",
            "the snow carries a sharp, sterile cold and no smell of its own",
            "the cold air bites clean and mineral",
            "the falling snow strips the street of its smells",
            "cold metal and clean ice ride every breath",
            "the chilled air smells of nothing but cold",
        ],
        'tactile': [
            "the air bites cold and dry",
            "a still, deep cold settles in with the snow",
            "the cold sits heavy and unmoving over the white street",
            "the chill creeps into every surface under the snow",
        ],
        'atmospheric': [
            "snow settles undisturbed in the quiet corners",
            "the fresh white coat takes every footprint",
            "the street lies hushed and slow under the snow",
            "snow banks soft against the windward walls",
            "the cold has thinned the street to a few figures",
        ],
    },
    'hard_snow': {
        'visual': [
            "snow drives down thick and fast, piling on every ledge",
            "the heavy fall greys out the far prefabs",
            "drifts bank deep against the walls",
            "snow blows in sheets across the grating",
            "the white coat deepens by the minute",
            "tracks fill almost as fast as they're made",
        ],
        'auditory': [
            "the heavy snow muffles the street to a deep hush",
            "wind drives the snow with a low steady rush",
            "footsteps are lost in the muffling fall",
            "sound dies fast in the thick snowfall",
            "the processor's hum is buried under the snow",
            "the heavy fall deadens everything close",
        ],
        'olfactory': [
            "the cold is sharp and scentless, scrubbed by driving snow",
            "hard cold and clean ice bite at every breath",
            "the driving snow strips all warmth and smell from the air",
            "nothing rides the air but bitter cold",
            "the air smells only of cold metal and ice",
            "the deep cold numbs the smell of the street",
        ],
        'tactile': [
            "the cold drives hard behind the heavy snow",
            "the wind-driven snow piles cold against every wall",
            "the deep cold works fast into everything exposed",
            "the chill of the heavy fall settles bone-deep over the street",
        ],
        'atmospheric': [
            "drifts climb the windward walls and bury the low rails",
            "the heavy fall has driven the street near empty",
            "snow piles deep enough to swallow the grating",
            "the white closes off the far end of the street",
            "fresh snow fills every print and track",
        ],
    },
    'blizzard': {
        'visual': [
            "the blizzard drives snow flat and horizontal down the street",
            "the white-out closes visibility to arm's length",
            "snow tears past in blinding sheets",
            "the far prefabs are gone, swallowed in white",
            "drifts build fast and deep in the howling wind",
            "the blizzard erases the street into blank white",
        ],
        'auditory': [
            "the blizzard roars and drowns every other sound",
            "the wind shrieks through the gaps and around the corners",
            "snow and wind fill the street with a constant howl",
            "nothing carries through the storm's roar",
            "ice and grit crack past on the wind",
            "the wind's howl rises and falls but never stops",
        ],
        'olfactory': [
            "the storm scours the air to bitter, scentless cold",
            "driving ice bites at every exposed breath",
            "nothing survives on the air but the cold",
            "the blizzard strips away every smell",
            "hard cold and clean ice are all the air carries",
            "the freezing wind numbs the nose to anything",
        ],
        'tactile': [
            "the wind tears bitter cold down the street",
            "the driving cold cuts through every gap and seam",
            "the blizzard's cold is brutal and total, with no still air to escape it",
            "the wind packs cold and snow into anything that breaks it",
        ],
        'atmospheric': [
            "the blizzard has emptied the street entirely",
            "drifts climb fast against anything that breaks the wind",
            "the white-out swallows everything past arm's reach",
            "the wind packs snow into every gap and corner",
            "nothing holds still in the driving storm",
        ],
    },
    'dry_thunderstorm': {
        'visual': [
            "lightning forks across the cloud without a drop falling",
            "the dry storm strobes the street in stark white flashes",
            "thunderheads pile black and heavy over the crater rim",
            "dust kicks up and races down the street on the storm's wind",
            "each flash freezes the street for an instant, hard-edged and white",
            "the dark cloud churns overhead without breaking",
        ],
        'auditory': [
            "thunder rolls and cracks across the dry sky",
            "the air buzzes faint just before each strike",
            "thunder booms and echoes flat off the prefabs",
            "the storm's wind drives grit rattling along the grating",
            "sharp cracks split the heavy air",
            "long rolls of thunder fade and return",
        ],
        'olfactory': [
            "ozone sharpens the dry air after every strike",
            "the storm leaves a metallic bite on the wind",
            "dust and ozone ride the gusting air",
            "the dry air carries the burnt smell of lightning",
            "a sharp electric tang hangs over the street",
            "hot dust and ozone ride every breath",
        ],
        'tactile': [
            "the air hangs hot, dry, and charged",
            "the storm's wind drives warm grit down the street",
            "the dry heat sits heavy under the churning cloud",
            "the air feels tight and electric between the thunderclaps",
        ],
        'atmospheric': [
            "the dry storm has people watching the sky and the doorways",
            "each flash throws hard shadows the length of the grating",
            "dust travels the street on the storm's wind",
            "the air holds taut between the thunderclaps",
            "the storm churns overhead and won't break",
        ],
    },
    'rainy_thunderstorm': {
        'visual': [
            "lightning lights the falling rain in sheets of white",
            "the downpour drives hard under cracking thunder",
            "each flash freezes the rain dead in the air",
            "rain sheets off every eave as the storm breaks",
            "the grating runs deep and fast with storm runoff",
            "the storm greys out everything past the near prefabs",
        ],
        'auditory': [
            "thunder booms over the roar of driving rain",
            "rain hammers the roofs under rolling thunder",
            "the storm fills the street with water-noise and thunder",
            "sharp cracks split the steady roar of rain",
            "runoff rushes loud and brown through every channel",
            "the downpour and the thunder drown out all else",
        ],
        'olfactory': [
            "ozone and rain mix sharp on the storm air",
            "the storm brings up wet stone and a metallic tang",
            "rain and lightning leave the air electric and wet",
            "cold rain and ozone ride every breath",
            "the downpour rinses the air to wet mineral and ozone",
            "wet composite and the burnt bite of lightning ride the air",
        ],
        'tactile': [
            "the rain drives down cold and hard over everything",
            "the cold downpour pools and soaks across the grating",
            "the storm's wind drives the cold rain sidelong",
            "the wet chill of the storm settles into every surface",
        ],
        'atmospheric': [
            "the storm has cleared the street of everyone unhurried",
            "runoff floods the low grating and races the drains",
            "each flash throws the drenched street into hard relief",
            "water stands deep where the drains can't keep up",
            "the storm hammers the street without let-up",
        ],
    },
    'gray_pall': {
        'visual': [
            "a thick grey pall hangs over the street, dimming the lamps",
            "the pall blurs the far prefabs into grey",
            "particulate haze settles a grey film over every surface",
            "the light struggles down through the heavy murk",
            "the pall closes the sky into a low, dirty ceiling",
            "haze greys out the crater rim entirely",
        ],
        'auditory': [
            "sound comes muffled and flat through the heavy pall",
            "the murk deadens the street's noise",
            "distant sounds arrive dulled and close",
            "the pall flattens the processor's hum to a drone",
            "everything sounds smothered under the haze",
            "noise carries thick and slow through the murk",
        ],
        'olfactory': [
            "the pall is acrid, catching at the back of the throat",
            "the haze tastes of ash and burnt industry",
            "a chemical grit settles on the tongue",
            "the heavy air smells of soot and scorched residue",
            "acrid particulate coats every breath",
            "the murk carries the taste of the smokestacks",
        ],
        'tactile': [
            "the air sits warm, thick, and gritty",
            "a fine chemical grit settles over every surface",
            "the heavy pall hangs close and unmoving",
            "the gritty air leaves a film on everything it touches",
        ],
        'atmospheric': [
            "the pall films every surface with grey grit",
            "people move through the murk with their mouths covered",
            "the haze dims the signage to dull smears",
            "grey particulate settles slow over everything",
            "the heavy air hangs low and unmoving",
        ],
    },
    'tox_rain': {
        'visual': [
            "a dismal acid drizzle beads up oily on the grating, hissing where it pools on warm metal",
            "tox rain leaves a slick, off-colour film on every surface",
            "the runoff carries streaks of unnatural colour to the drains",
            "discoloured water pools and beads on the grating",
            "the rain stains pale every surface it runs across",
            "the toxic downpour hazes the street in sickly colour",
        ],
        'auditory': [
            "the tox rain hisses and spatters with a faint chemical fizz",
            "the corrosive rain pops and sizzles where it hits warm metal",
            "a warning tone repeats, ignored, from a distant speaker",
            "the rain ticks and fizzes against the eaves",
            "runoff gurgles thick and slow down the drains",
            "the rain falls with an oily, heavier sound than water",
        ],
        'olfactory': [
            "the air stings, sharp with chemical reek",
            "the tox rain burns at the nose and the throat",
            "acrid fumes rise where the rain pools and eats",
            "the corrosive air bites at every breath",
            "chemical sting and rot ride the wet air",
            "the rain leaves a taste of solvent and decay",
        ],
        'tactile': [
            "the air hangs warm and damp with a chemical sting",
            "the acid drizzle eats slick at every surface it pools on",
            "a faint chemical burn rides the wet air",
            "the corrosive damp clings to everything in the open",
        ],
        'atmospheric': [
            "the tox rain has driven everyone under cover or indoors",
            "discoloured water pools where the drains run slow",
            "a chemical sheen slicks every exposed surface",
            "the few still out keep their skin and mouths covered",
            "the rain pits and stains whatever it touches",
        ],
    },
    'sandstorm': {
        'visual': [
            "grit drives down the street in stinging brown sheets and banks fine drifts against the prefab walls",
            "blown sand closes visibility to a few paces",
            "the storm hazes the street into swirling brown",
            "sand streams thick and low across the grating",
            "the far prefabs vanish behind the blown grit",
            "fine sand sifts and piles in every lee",
        ],
        'auditory': [
            "the sandstorm hisses and roars with driven grit",
            "sand rattles hard against metal and dark glass",
            "the wind drives a steady abrasive rush down the street",
            "grit scours every surface with a dry, ceaseless hiss",
            "the storm's roar drowns the nearer sounds",
            "blown sand ticks and patters against the signage",
        ],
        'olfactory': [
            "the air is thick with dry dust and hot mineral grit",
            "blown sand coats the mouth with dry mineral",
            "the storm packs every breath with fine grit",
            "dust and hot stone choke the driving air",
            "the dry air rasps with mineral dust",
            "grit settles dry and metallic on the tongue",
        ],
        'tactile': [
            "the wind drives hot grit that scours every surface",
            "blown sand abrades everything left in the open",
            "the gritty wind sandblasts walls and signage alike",
            "the hot, abrasive air leaves nothing untouched",
        ],
        'atmospheric': [
            "the sandstorm has cleared the street of all but the desperate",
            "fine sand sifts into every seam and corner",
            "grit piles deep against the windward walls",
            "the blown sand scours and dulls every surface",
            "drifts of sand fill the low grating",
        ],
    },
    'blind_fog': {
        'visual': [
            "the blind fog closes visibility to less than arm's length",
            "the fog is so thick the grating vanishes underfoot",
            "nothing shows through the dense white but the nearest shapes",
            "even close lamps are swallowed to faint smears",
            "the fog erases the street into blank grey",
            "shapes a pace away loom and are gone",
        ],
        'auditory': [
            "the dense fog turns every sound around and flattens it",
            "footsteps come from impossible directions in the murk",
            "sound is muffled enough to seem to come from nowhere at all",
            "voices arrive close and bodiless out of the white",
            "the fog swallows the direction out of every noise",
            "dripping is the only sound that carries clear",
        ],
        'olfactory': [
            "the fog is thick and wet, heavy with cold mineral",
            "every breath draws in cold suspended water",
            "the dense damp coats the mouth and the nose",
            "wet stone and rust hang heavy on the still air",
            "the saturated air tastes of cold metal",
            "the fog holds the street's smells thick and close",
        ],
        'tactile': [
            "the dense fog hangs cold and soaking",
            "a heavy wet cold presses out of the white",
            "the saturated fog beads and runs off every surface",
            "the cold damp is thick enough to feel against the face",
        ],
        'atmospheric': [
            "the blind fog has all but stopped movement on the street",
            "moisture runs in sheets down every surface",
            "the lamps vanish entirely a few paces off",
            "the dense white slicks the grating treacherous",
            "the fog stands so thick it seems to press inward",
        ],
    },
    'heavy_fog': {
        'visual': [
            "heavy fog closes the street to grey shapes within a few paces",
            "thick fog swallows the prefabs whole",
            "the lamps show only as drowned haloes in the murk",
            "the heavy fog beads and runs off every edge",
            "shapes resolve only when they're nearly on top of you",
            "the far half of the street is simply gone",
        ],
        'auditory': [
            "the heavy fog muffles the street to a close, padded hush",
            "sound comes turned around and disembodied through the murk",
            "footsteps approach from nowhere in the thick fog",
            "the fog flattens the processor's hum to a drone",
            "voices carry oddly close and placeless",
            "dripping is the clearest sound in the murk",
        ],
        'olfactory': [
            "the heavy fog is cold and wet, thick with mineral damp",
            "saturated air condenses on every cold surface",
            "wet stone and old metal hang dense on the air",
            "the cold damp coats the mouth and the throat",
            "the fog holds the street's smells suspended and close",
            "rust and standing water thicken every breath",
        ],
        'tactile': [
            "the heavy fog hangs cold and soaking wet",
            "a clammy chill beads on every surface",
            "the wet cold of the fog works deep into everything",
            "moisture sheets cold off rail and grating",
        ],
        'atmospheric': [
            "the heavy fog has slowed the street to a crawl",
            "moisture sheets down every vertical surface",
            "the murk swallows the lamps a few paces off",
            "the slick fog beads cold on rail and grating",
            "the thick grey drifts and pools between the prefabs",
        ],
    },
    'flashstorm': {
        'visual': [
            "the flashstorm strobes the street in rapid white stutters",
            "discharge forks across the sky faster than the eye can hold",
            "each burst freezes the street and leaves an afterimage",
            "the storm flickers like a failing light, all white and black",
            "lightning chains across the cloud in continuous bursts",
            "the flashes come too fast to count, blanking the street white",
        ],
        'auditory': [
            "thunder runs together into a continuous tearing roar",
            "the air cracks and buzzes between the rapid strikes",
            "the storm fills the street with overlapping thunder",
            "each flash lands with a near-instant crack",
            "the rolling concussion never fully fades before the next",
            "the discharge sizzles and snaps in the charged air",
        ],
        'olfactory': [
            "ozone saturates the air, sharp enough to taste",
            "the charged air reeks of lightning and hot metal",
            "each strike thickens the ozone bite on every breath",
            "the air carries the burnt smell of charge",
            "a hard electric tang coats the mouth",
            "ozone and scorched dust hang heavy on the air",
        ],
        'tactile': [
            "the charged air prickles and crackles",
            "the air hangs hot and electric between the bursts",
            "each strike leaves the air tight and charged",
            "a static charge hangs heavy over the whole street",
        ],
        'atmospheric': [
            "the flashstorm has driven everyone off the open street",
            "each burst throws the street into hard white relief",
            "the strobing leaves the street flickering black and white",
            "the storm hammers the sky without pause",
            "the lamps are lost under the storm's white stutter",
        ],
    },
    'torrential_rain': {
        'visual': [
            "the torrential rain falls in solid grey sheets",
            "water comes down hard enough to blur the near prefabs",
            "the downpour overwhelms the drains and floods the grating",
            "rain sheets off every eave in continuous curtains",
            "standing water spreads deep and fast across the street",
            "the deluge greys out everything past a few paces",
        ],
        'auditory': [
            "the torrential rain roars on the roofs and the grating",
            "the downpour drowns every other sound under its hammering",
            "water thunders down the drains and overruns them",
            "the deluge fills the street with one continuous roar",
            "runoff rushes deep and loud through every channel",
            "the rain hammers too loud to speak over",
        ],
        'olfactory': [
            "the deluge floods the air with wet stone and cold mineral",
            "the torrential rain rinses the air to cold, clean damp",
            "wet composite and runoff overwhelm every other smell",
            "the downpour leaves only cold rain on every breath",
            "the flooded drains push up a smell of wet rot and runoff",
            "the rain-soaked air is thick with cold mineral",
        ],
        'tactile': [
            "the rain hammers down cold and heavy",
            "the deluge drives cold runoff across the grating",
            "the downpour soaks everything in the open in seconds",
            "the cold weight of the rain pounds every surface",
        ],
        'atmospheric': [
            "the torrential rain has emptied the street completely",
            "floodwater stands deep where the drains have given up",
            "runoff races the grating and overruns the channels",
            "the deluge sheets off every roof in solid curtains",
            "water finds every low point and pools deep",
        ],
    },
    'foggy_rain': {
        'visual': [
            "rain falls through a clinging fog, doubling the grey",
            "fog and rain together close the street to a few paces",
            "the wet murk blurs the lamps to drowned haloes",
            "rain stipples the puddles under a low ceiling of fog",
            "the fogged rain greys everything down to soft shapes",
            "drizzle and fog merge into a single wet wall",
        ],
        'auditory': [
            "the fog muffles the patter of rain to a close hush",
            "dripping and soft rain blend in the muffling murk",
            "sound comes flattened and turned around through the wet fog",
            "the rain whispers under the fog's padded quiet",
            "runoff trickles unseen through the grey",
            "the processor's hum comes drowned and directionless",
        ],
        'olfactory': [
            "the air is doubly wet, cold with fog and rain together",
            "wet stone and cold mineral hang thick on the saturated air",
            "every breath draws cold suspended water",
            "the fogged rain smells of rust and standing water",
            "cold damp coats the mouth, mineral and metallic",
            "the saturated air holds the street's smells thick and wet",
        ],
        'tactile': [
            "the air hangs cold, wet, and clinging",
            "a soaking chill settles out of the fogged rain",
            "the doubled damp works cold into everything",
            "moisture clings cold to every surface at once",
        ],
        'atmospheric': [
            "the fogged rain has slowed the street to almost nothing",
            "moisture sheets and beads on every surface at once",
            "the lamps drown to faint haloes in the wet grey",
            "fog and runoff slick the grating treacherous",
            "the wet murk pools and drifts between the prefabs",
        ],
    },
}


def _rotate(pool, start, count):
    """Take `count` distinct items from `pool` beginning at offset `start`."""
    n = len(pool)
    return [pool[(start + k) % n] for k in range(min(count, n))]


def _build_weather_messages():
    """Compose the full weather x time-of-day x sense message dict.

    Deterministic (no randomness at import): the time index rotates each
    weather pool so adjacent times of day draw different lines, while every
    line stays a clean standalone observation.
    """
    region = {}
    for weather, pools in WEATHER_POOLS.items():
        for i, period in enumerate(TIME_PERIODS):
            key = f"{weather}_{period}"
            region[key] = {
                'visual': [TIME_LIGHT[period]] + _rotate(pools['visual'], i, 2),
                'auditory': _rotate(pools['auditory'], i, 3),
                'olfactory': _rotate(pools['olfactory'], i, 3),
                'tactile': _rotate(pools['tactile'], i, 2),
                'atmospheric': (
                    [TIME_ACTIVITY[period]] + _rotate(pools['atmospheric'], i * 2, 2)
                ),
            }
    return region


# Regional weather message pools (future: 'mars_desert', 'orbital_station', ...).
WEATHER_MESSAGES = {
    'default': _build_weather_messages(),
}
