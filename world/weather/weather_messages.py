"""
Weather Message Pools

Contains atmospheric descriptions for different weather types and times of day.
Messages are designed to synergize when combined with comma separation.
"""

# Weather intensity levels for message length/impact
WEATHER_INTENSITY = {
    # Mild weather (short, subtle messages)
    'clear': 'mild',
    'overcast': 'mild', 
    'windy': 'mild',
    
    # Moderate weather
    'fog': 'moderate',
    'rain': 'moderate',
    'soft_snow': 'moderate',
    'foggy_rain': 'moderate',
    'light_rain': 'moderate',
    
    # Intense weather (longer, attention-grabbing messages)
    'dry_thunderstorm': 'intense',
    'rainy_thunderstorm': 'intense',
    'hard_snow': 'intense',
    'blizzard': 'intense',
    'gray_pall': 'intense',
    'tox_rain': 'intense',
    'sandstorm': 'intense',
    'blind_fog': 'intense',
    'heavy_fog': 'intense',
    
    # Extreme weather (epic messages that demand attention)
    'flashstorm': 'extreme',
    'torrential_rain': 'extreme',
}

# Regional weather message pools
# Future expansion: multiple regions like 'mars_desert', 'orbital_station', etc.
WEATHER_MESSAGES = {
    'default': {
        # Clear weather variations by time of day (mild intensity)
        'clear_pre_dawn': {
            'visual': [
                "darkness holds dominion with hints of approaching light",
                "scattered lights pierce the deep shadows like stars",
                "the sky remains black velvet above"
            ],
            'auditory': [
                "silence broken only by distant mechanical whispers",
                "the world sleeps in hushed anticipation",
                "sporadic sounds echo in the stillness"
            ],
            'olfactory': [
                "cool air carries the scent of dew and night",
                "fresh moisture mingles with lingering traces",
                "the smell of dawn approaches on quiet winds"
            ],
            'atmospheric': [
                "the pre-dawn stillness feels heavy with potential",
                "expectant air holds its breath before sunrise",
                "there's a sense of worlds about to change"
            ]
        },
        
        'clear_dawn': {
            'visual': [
                "pale light filters through the awakening atmosphere",
                "long shadows stretch like fingers across surfaces",
                "the sky lightens to pearl and amber"
            ],
            'auditory': [
                "distant sounds begin their morning chorus",
                "the world awakens with scattered whispers of activity",
                "crisp air carries the echo of new beginnings"
            ],
            'olfactory': [
                "cool morning air carries hints of warming earth",
                "the scent of heated surfaces begins to rise",
                "faint aromas drift on the morning breeze"
            ],
            'atmospheric': [
                "the air feels clean despite surrounding complexity",
                "morning calm settles over everything like a blessing",
                "the day ahead pulses with hidden possibilities"
            ]
        },
        
        'clear_early_morning': {
            'visual': [
                "golden sunlight slants through the atmosphere",
                "harsh light glints off every reflective surface",
                "morning shadows create geometric patterns everywhere"
            ],
            'auditory': [
                "activity hums with increasing intensity around you",
                "engines warm and machinery comes to life",
                "the steady background noise of life grows stronger"
            ],
            'olfactory': [
                "warming surfaces release their stored scents",
                "exhaust and heated metal fill the air",
                "morning aromas mix in complex combinations"
            ],
            'atmospheric': [
                "the morning energy feels charged and electric",
                "visibility stretches sharp and clear in all directions",
                "everything feels alert and watchful around you"
            ]
        },
        
        'clear_late_morning': {
            'visual': [
                "bright sun climbs higher, shortening shadows",
                "everything basks in full daylight clarity",
                "peak activity unfolds under cloudless skies"
            ],
            'auditory': [
                "late morning brings energetic sounds and motion",
                "construction, traffic, and life create lively soundscapes",
                "productivity hums with forward momentum everywhere"
            ],
            'olfactory': [
                "warming surfaces begin releasing their heat",
                "food vendors and kitchens add rich aromas",
                "morning freshness mixes with heated air"
            ],
            'atmospheric': [
                "late morning feels dynamic and purposeful",
                "energetic quality fills the warming atmosphere",
                "productivity and ambition charge the air"
            ]
        },
        
        'clear_midday': {
            'visual': [
                "harsh sun beats down mercilessly",
                "heat shimmer rises from every baked surface",
                "shadows shrink to sharp, minimal lines"
            ],
            'auditory': [
                "everything thrums with peak activity and motion",
                "cooling systems hum and rattle desperately",
                "background noise forms a steady symphony"
            ],
            'olfactory': [
                "heated surfaces create distinctive burning scents",
                "exhaust and industrial odors hang heavy",
                "overheated machinery adds acrid notes"
            ],
            'atmospheric': [
                "heat creates pressing, almost oppressive weight",
                "the air itself vibrates with intense energy",
                "energy levels feel maxed out everywhere"
            ]
        },
        
        'clear_early_afternoon': {
            'visual': [
                "afternoon light takes on warmer, golden qualities",
                "long shadows begin creeping across everything",
                "sun's angle creates interesting light patterns"
            ],
            'auditory': [
                "post-lunch energy maintains its energetic pace",
                "traffic flows with occasional bursts and horns",
                "construction and activity blend into afternoon din"
            ],
            'olfactory': [
                "warming surfaces release stored heat and scents",
                "food preparation adds complex cooking aromas",
                "afternoon heat carries mixed industrial smells"
            ],
            'atmospheric': [
                "afternoon energy feels focused and purposeful",
                "productivity lingers in the warm air",
                "mid-day momentum continues building around you"
            ]
        },
        
        'clear_late_afternoon': {
            'visual': [
                "golden hour light bathes everything in amber",
                "surfaces glow with reflected sunlight",
                "shadows stretch long and dramatic everywhere"
            ],
            'auditory': [
                "rush hour traffic begins its evening crescendo",
                "pace quickens as people head toward destinations",
                "cooling systems work harder against accumulated heat"
            ],
            'olfactory': [
                "the day's heat has concentrated all scents",
                "hot surfaces dominate with metallic undertones",
                "ventilation systems add complex food aromas"
            ],
            'atmospheric': [
                "late afternoon carries anticipation of evening",
                "energy levels feel heightened but weary",
                "golden quality suffuses the warm, busy air"
            ]
        },
        
        'clear_dusk': {
            'visual': [
                "sky transforms into orange and deep purple",
                "artificial lights flicker on against darkening horizons",
                "illumination begins its evening glow against shadows"
            ],
            'auditory': [
                "evening sounds create steady flows of activity",
                "social spaces add voices to the mix",
                "day sounds transition to night rhythms"
            ],
            'olfactory': [
                "evening air carries cooled surfaces and accumulated scents",
                "food and entertainment aromas become more prominent",
                "exhaust mixes with hints of night-blooming plants"
            ],
            'atmospheric': [
                "dusk brings a sense of transition and possibility",
                "the air feels electric with evening energy",
                "anticipation fills the cooling, vibrant atmosphere"
            ]
        },
        
        'clear_early_evening': {
            'visual': [
                "artificial lights create vibrant tapestries of illumination",
                "windows glow warmly against deepening night",
                "everything transforms into constellations of human activity"
            ],
            'auditory': [
                "entertainment districts come alive with music and voices",
                "traffic maintains its steady hum with sirens",
                "soundscapes become richer and more varied"
            ],
            'olfactory': [
                "cool evening air carries scents from restaurants",
                "aromas become more complex and inviting",
                "exhaust mingles with food, perfume, and night air"
            ],
            'atmospheric': [
                "early evening energy feels social and dynamic",
                "excitement and possibility fill the cool air",
                "nightlife begins stirring with electric pulses"
            ]
        },
        
        'clear_late_evening': {
            'visual': [
                "artificial lights create glowing networks against darkness",
                "reflections dance on surfaces like liquid fire",
                "everything takes on a cinematic quality"
            ],
            'auditory': [
                "nightlife sounds mix with diminishing traffic",
                "music spills into the night air",
                "rhythms shift to evening tempos"
            ],
            'olfactory': [
                "night air carries complex blends of nightlife scents",
                "cooling surfaces release stored heat and odors",
                "food, alcohol, and exhaust create distinctive atmospheres"
            ],
            'atmospheric': [
                "late evening brings a sense of adventure",
                "the air feels alive with entertainment and possibility",
                "electric quality charges the cool, active night"
            ]
        },
        
        'clear_night': {
            'visual': [
                "deep night wraps everything in darkness and light",
                "illumination creates islands in vast shadows",
                "late establishments glow like beacons in quiet darkness"
            ],
            'auditory': [
                "everything settles into quieter night rhythms",
                "distant sounds provide low, steady background",
                "occasional night sounds echo clearly in stillness"
            ],
            'olfactory': [
                "cool night air carries concentrated scents",
                "darkness intensifies smells and aromas",
                "late-night food vendors add warm, comforting notes"
            ],
            'atmospheric': [
                "night brings solitude and mystery",
                "the air feels cooler and more intimate",
                "contemplative quality fills the quiet darkness"
            ]
        },
        
        'clear_late_night': {
            'visual': [
                "deep hours paint everything in stark contrasts",
                "only essential lighting creates dramatic scenes",
                "few active windows suggest insomniacs and workers"
            ],
            'auditory': [
                "everything reaches its quietest point",
                "night shift machinery and distant sounds carry clearly",
                "occasional emergency sounds stand out against silence"
            ],
            'olfactory': [
                "cold air sharpens scents into distinct, clear notes",
                "night operations add their own distinctive odors",
                "empty spaces and cooling surfaces dominate"
            ],
            'atmospheric': [
                "late night carries a sense of isolation",
                "the air feels thin and crisp with possibility",
                "something both lonely and peaceful fills the stillness"
            ]
        },

        # Rain weather (moderate intensity) - expanded across time periods
        'rain_pre_dawn': {
            'visual': [
                "steady rain turns surfaces into dark mirrors reflecting scattered light",
                "water streams down every surface pooling in shadowed corners",
                "pre-dawn takes on noir quality under rain-washed darkness"
            ],
            'auditory': [
                "rain patters against surfaces with rhythmic precision",
                "water splashes through puddles with wet hissing sounds",
                "rainfall creates white noise muffling other sounds"
            ],
            'olfactory': [
                "petrichor mingles with the scent of wet surfaces",
                "rain releases stored smells from pavement and gutters",
                "clean water fights against underlying industrial odors"
            ],
            'atmospheric': [
                "rain creates intimate, enclosed feeling despite open space",
                "everything feels washed clean yet somehow more mysterious",
                "there's renewal mixed with persistent grit"
            ]
        },
        
        'rain_dawn': {
            'visual': [
                "dawn light filters through falling rain like silver curtains",
                "water transforms everything into impressionist paintings",
                "morning shadows blur and soften in the steady downpour"
            ],
            'auditory': [
                "rain drums steadily against every surface around you",
                "morning sounds become muffled and distant in the deluge",
                "water gurgles through drains with urgent intensity"
            ],
            'olfactory': [
                "wet earth and fresh rain cleanse the morning air",
                "moisture brings out hidden scents from every crevice",
                "the smell of washing and renewal fills the atmosphere"
            ],
            'atmospheric': [
                "rain-soaked dawn feels like the world is being reborn",
                "moisture charges the air with electric possibility",
                "everything feels softer and more forgiving"
            ]
        },
        
        'rain_evening': {
            'visual': [
                "steady rain turns the streets into dark mirrors reflecting neon light",
                "water streams down building facades and pools in street corners",
                "the city takes on a noir-like quality under the rain-washed evening light"
            ],
            'auditory': [
                "rain patters steadily against concrete and metal surfaces",
                "tires splash through growing puddles with wet hissing sounds",
                "the rainfall creates a white noise that muffles other city sounds"
            ],
            'olfactory': [
                "petrichor mingles with urban scents of wet concrete and metal",
                "the rain releases stored smells from the pavement and gutters",
                "clean water scent fights against underlying industrial odors"
            ],
            'atmospheric': [
                "the rain creates an intimate, enclosed feeling despite the open space",
                "the city feels washed clean yet somehow more mysterious",
                "there's a sense of renewal mixed with urban grit"
            ]
        },
        
        'rain_night': {
            'visual': [
                "rain slicks every surface into black mirrors reflecting artificial light",
                "water creates streams of liquid silver down dark surfaces",
                "night becomes a canvas of rain and reflected illumination"
            ],
            'auditory': [
                "rain provides constant percussion against the night quiet",
                "water flows through hidden channels with liquid whispers",
                "the downpour transforms night sounds into something intimate"
            ],
            'olfactory': [
                "night rain intensifies every scent and aroma",
                "moisture brings out the deep, hidden smells of darkness",
                "wet air carries traces of secrets and possibilities"
            ],
            'atmospheric': [
                "rain-soaked night feels mysterious and full of potential",
                "moisture makes the darkness more intimate and personal",
                "there's something romantic and dangerous in the wet air"
            ]
        },
        
        # Torrential Rain (extreme intensity)
        'torrential_rain_night': {
            'visual': [
                "sheets of rain cascade down in torrents that transform everything into raging rivers of chaos",
                "the deluge overwhelms every drainage system creating waterfalls from rooftops and overhangs",
                "visibility drops to mere arm's length as rain falls like solid walls of liquid fury"
            ],
            'auditory': [
                "the thunderous roar of torrential rain drowns out absolutely every other sound in existence",
                "water crashes and gurgles through overwhelmed systems with violent, primal intensity",
                "the storm creates a deafening symphony of liquid percussion against every conceivable surface"
            ],
            'olfactory': [
                "the air fills with the overwhelming scent of churned earth and flood waters",
                "deluge carries the mingled odors of everything in its path creating choking mixtures",
                "ozone and rain-soaked debris create a powerful atmosphere that burns the nostrils"
            ],
            'atmospheric': [
                "the storm transforms familiar landscapes into alien water-worlds of chaos and raw power",
                "nature's fury makes every human construction feel fragile and temporary as matchsticks",
                "the air vibrates with primal energy of water reclaiming everything in its unstoppable path"
            ]
        },
        
        'torrential_rain_midday': {
            'visual': [
                "apocalyptic downpour transforms bright day into a gray-green nightmare of cascading water",
                "torrents pour from every surface creating instant rivers where none existed moments before",
                "the world disappears behind walls of rain falling with supernatural intensity and violence"
            ],
            'auditory': [
                "rain roars like freight trains colliding with the earth in endless, deafening percussion",
                "the storm drowns out sirens, machinery, and human voices in its liquid symphony of destruction",
                "water hammers against everything with the sound of ten thousand drums beating in perfect chaos"
            ],
            'olfactory': [
                "flood waters carry the scent of everything they've touched in a choking cocktail of urban debris",
                "the air reeks of displaced earth, overflowing sewers, and the metallic tang of electrical systems failing",
                "ozone mixes with organic decay creating an atmosphere thick enough to taste and fear"
            ],
            'atmospheric': [
                "the torrential storm makes the world feel like it's ending in slow motion drowning",
                "nature's absolute fury reduces human civilization to helpless spectators of elemental power",
                "the deluge transforms familiar reality into something alien, dangerous, and utterly unforgiving"
            ]
        },
        
        # Hot Weather - Flashstorm (extreme intensity)
        'flashstorm_midday': {
            'visual': [
                "the air shimmers with brutal heat waves that distort reality like a fever dream mirage",
                "metal surfaces become untouchable furnaces radiating visible waves of scorching, dancing air",
                "the sun blazes with merciless intensity that bleaches color from everything it touches"
            ],
            'auditory': [
                "oppressive silence of extreme heat broken only by the sharp ping and crack of expanding metal",
                "cooling systems strain and whine desperately against the overwhelming temperature like dying animals",
                "the very air hisses and whispers with the sound of moisture evaporating into nothingness"
            ],
            'olfactory': [
                "superheated surfaces release acrid chemical smells that burn nostrils and sear the throat",
                "the air carries metallic taste of overheated machinery and surfaces baking under relentless sun",
                "waves of heat bring sharp scents of sun-baked garbage and industrial chemicals melting together"
            ],
            'atmospheric': [
                "heat presses down like a physical weight making every breath feel like work",
                "everything becomes a furnace radiating stored solar energy from every conceivable surface",
                "the oppressive temperature transforms familiar environments into hellscapes of concrete and steel"
            ]
        },
        
        'flashstorm_early_afternoon': {
            'visual': [
                "heat mirages dance like ghosts across every surface turning the world into liquid illusion",
                "air itself becomes visible as superheated waves distort and bend light into impossible shapes",
                "the sun hangs like a malevolent eye burning everything beneath its unblinking gaze"
            ],
            'auditory': [
                "the silence of extreme heat broken by metal expanding with gunshot-sharp cracks and pops",
                "cooling systems work overtime creating a mechanical symphony of desperation and failing machinery",
                "even the air seems to scream as moisture turns to steam before it can form"
            ],
            'olfactory': [
                "the air tastes of burning metal, melting plastic, and surfaces cooking under relentless heat",
                "superheated pavement releases chemical vapors that create a toxic soup of industrial scents",
                "heat transforms every familiar smell into something sharp, acrid, and threatening to the senses"
            ],
            'atmospheric': [
                "the flashstorm heat makes survival feel like a constant battle against the elements themselves",
                "every surface radiates enough heat to cook flesh and every breath feels like inhaling fire",
                "the world becomes a furnace where human comfort is not just absent but actively hostile"
            ]
        },
        
        # Cold Weather - Blizzard (extreme intensity)
        'blizzard_night': {
            'visual': [
                "howling winds drive sheets of snow horizontally through the air like frozen bullets of ice",
                "the blizzard transforms everything into a white void where visibility drops to arm's length",
                "ice forms instantly on every surface while snow piles into massive drifts that bury everything"
            ],
            'auditory': [
                "the blizzard roars with primal fury drowning out all other sounds in its icy symphony of destruction",
                "wind shrieks through gaps and around corners with banshee intensity that chills the soul",
                "the storm creates constant howling punctuated by sharp cracks of ice and flying debris"
            ],
            'olfactory': [
                "air carries the clean, sharp scent of pure snow mixed with metallic bite of extreme cold",
                "frozen precipitation brings sterile smell of sub-zero temperatures that numbs every sense",
                "the blizzard strips away all warm scents leaving only crystalline purity of arctic air"
            ],
            'atmospheric': [
                "the storm transforms everything into an arctic wasteland where survival becomes the only priority",
                "nature's frozen fury makes every environment feel hostile and utterly alien to human life",
                "the blizzard brings primal cold that penetrates not just to bone but to soul itself"
            ]
        },
        
        'blizzard_early_morning': {
            'visual': [
                "dawn struggles to penetrate walls of wind-driven snow that turn the world into white chaos",
                "ice crystals fill the air like tiny razors cutting visibility to mere inches in every direction",
                "the blizzard creates a whiteout where up and down lose all meaning in the frozen maelstrom"
            ],
            'auditory': [
                "wind screams with the voices of a thousand demons tearing through the frozen air",
                "the storm drowns out every sound except the relentless howl of arctic fury unleashed",
                "snow and ice crash against surfaces like machine gun fire in the endless winter assault"
            ],
            'olfactory': [
                "the air burns with cold so intense it sears nostrils and throat like liquid nitrogen",
                "frozen air carries nothing but the sterile scent of ice and the metallic taste of extreme cold",
                "the blizzard strips every warm smell from existence leaving only the purity of arctic death"
            ],
            'atmospheric': [
                "the storm makes the world feel like an alien planet where warmth is just a distant memory",
                "blizzard fury transforms familiar places into landscapes of pure survival horror",
                "nature's frozen rage makes every breath a victory and every heartbeat a defiance of the cold"
            ]
        },
        
        # Soft Snow (moderate intensity)
        'soft_snow_early_morning': {
            'visual': [
                "gentle snowflakes drift down like confetti, coating everything in pristine white",
                "fresh snow muffles harsh edges with soft curves and gentle accumulation",
                "morning light reflects off snow cover creating ethereal landscapes"
            ],
            'auditory': [
                "sounds become muffled and distant beneath the soft blanket of falling snow",
                "footsteps crunch softly through accumulated powder with rhythmic precision",
                "snow creates peaceful hush that transforms usual cacophony into whispers"
            ],
            'olfactory': [
                "air carries clean, crisp scent of fresh snow and winter purity",
                "cold air brings sharp clarity that makes every breath feel cleansing",
                "snow masks harsh odors with neutral scent of frozen precipitation"
            ],
            'atmospheric': [
                "gentle snowfall creates sense of peace and temporary beauty",
                "cold brings invigorating clarity that sharpens awareness and focus",
                "winter scene transforms everything into something almost magical and serene"
            ]
        },
        
        'soft_snow_dusk': {
            'visual': [
                "snowflakes catch the last light like tiny stars falling from purple sky",
                "evening snow creates soft halos around every source of illumination",
                "dusk and snow combine to paint everything in gentle, muted tones"
            ],
            'auditory': [
                "evening sounds become hushed and intimate under falling snow",
                "the world takes on cathedral quiet broken only by soft whispers",
                "snow muffles everything into a peaceful, contemplative soundscape"
            ],
            'olfactory': [
                "cold air sharpens and purifies every scent into crystal clarity",
                "snow brings the clean smell of winter and fresh possibilities",
                "evening air mixed with snow creates bracing, invigorating atmosphere"
            ],
            'atmospheric': [
                "soft snow at dusk feels like the world is being tucked in for sleep",
                "there's magic in the way snow transforms familiar places into wonderland",
                "cold air and gentle precipitation create sense of renewal and peace"
            ]
        },
        
        # Sandstorm (extreme intensity)
        'sandstorm_afternoon': {
            'visual': [
                "walls of gritty dust and debris roar through the air like brown tsunamis of destruction",
                "the sandstorm reduces visibility to absolute zero while coating everything in abrasive particles",
                "air becomes choking cloud of dust transforming day into apocalyptic twilight of swirling chaos"
            ],
            'auditory': [
                "the storm howls with sound of millions of particles abrading against every surface",
                "wind-driven debris rattles and crashes with machine-gun intensity that never stops",
                "sandstorm creates constant roar punctuated by impacts of flying debris and grit"
            ],
            'olfactory': [
                "air fills with gritty taste and smell of pulverized earth, metal, and organic debris",
                "dust carries accumulated scents of everything in choking, abrasive mixture that burns the throat",
                "storm brings sharp, mineral smell of abraded stone and particles ground to powder"
            ],
            'atmospheric': [
                "sandstorm transforms everything into alien landscape of swirling, abrasive chaos that strips flesh",
                "the storm brings primal sense of nature's power to scour and reshape with relentless fury",
                "air itself becomes hostile turning every breath into a battle against elements gone mad"
            ]
        },
        
        'sandstorm_dusk': {
            'visual': [
                "dust storm turns sunset into hellish orange glow filtered through walls of flying grit",
                "sand fills every gap and crevice while wind howls with voices of desert fury",
                "the world disappears behind curtains of dust that turn day into something from nightmares"
            ],
            'auditory': [
                "wind screams through the storm carrying the sound of a world being ground to powder",
                "debris crashes and rattles in the endless assault of particles against every surface",
                "the sandstorm roars like a living thing hungry to devour everything in its path"
            ],
            'olfactory': [
                "dust clogs nostrils and throat with the taste of ancient earth and mineral decay",
                "air becomes unbreathable soup of grit that carries scents of destruction and erosion",
                "the storm brings smell of things being broken down and worn away by relentless abrasion"
            ],
            'atmospheric': [
                "sandstorm at dusk feels like witnessing the end of worlds in slow motion grinding",
                "nature's fury reduces everything to its component particles in endless, patient destruction",
                "the storm makes survival feel like defying the fundamental forces of entropy itself"
            ]
        },
        
        # Fog (moderate intensity)
        'fog_dawn': {
            'visual': [
                "thick fog rolls through everything, reducing the world to ghostly silhouettes",
                "moisture beads on every surface while mist transforms landmarks into mysteries",
                "fog creates intimate world where nothing exists beyond meters of gray visibility"
            ],
            'auditory': [
                "sounds become muffled and directionless in thick, moisture-laden air",
                "fog seems to absorb noise, creating pockets of eerie silence and unexpected sound",
                "distant noises emerge from mist without warning, then fade back into gray obscurity"
            ],
            'olfactory': [
                "air carries damp, neutral scent of water vapor mixed with hidden undertones",
                "moisture brings out subtle smells from hidden corners and crevices",
                "fog creates humid atmosphere that intensifies both pleasant and unpleasant odors"
            ],
            'atmospheric': [
                "fog creates sense of isolation and mystery in the middle of familiar spaces",
                "visibility becomes precious commodity in gray, moisture-heavy environment",
                "mist transforms everything into dreamscape where reality feels soft and uncertain"
            ]
        },
        
        'fog_evening': {
            'visual': [
                "evening fog transforms artificial lights into soft halos of diffused glow",
                "mist swallows everything beyond arm's reach in gray, shifting veils",
                "fog and night combine to create world of shadows and uncertain shapes"
            ],
            'auditory': [
                "evening sounds become intimate whispers in the moisture-heavy air",
                "fog dampens and muffles everything into cathedral quiet",
                "voices and footsteps seem to float disembodied in the gray void"
            ],
            'olfactory': [
                "humid air intensifies every scent into rich, complex layers",
                "moisture brings out hidden smells from every surface and corner",
                "fog carries traces of secrets and possibilities on the damp air"
            ],
            'atmospheric': [
                "evening fog creates sense of mystery and romantic danger",
                "mist makes everything feel closer and more intimate",
                "there's something both beautiful and ominous in the thick, gray air"
            ]
        },
        
        # Heavy Fog (intense intensity)  
        'heavy_fog_night': {
            'visual': [
                "impenetrable fog reduces the world to mere arm's length of gray visibility that swallows everything",
                "thick mist transforms familiar landmarks into alien shapes that loom and vanish like ghosts",
                "heavy fog creates a world where direction becomes meaningless and navigation purely by feel"
            ],
            'auditory': [
                "sounds become completely directionless in the soup-thick air that deadens all echoes and distance",
                "heavy fog swallows noises whole making voices seem to come from inside your own head",
                "the mist creates acoustic illusions where footsteps and voices appear and disappear like spirits"
            ],
            'olfactory': [
                "air becomes thick enough to taste with moisture that carries every scent in concentrated doses",
                "heavy fog intensifies smells until they become almost overwhelming in their clarity and presence",
                "the mist carries layers of odors that shift and change like the fog itself in endless combinations"
            ],
            'atmospheric': [
                "heavy fog creates a world that feels completely separate from normal reality and familiar spaces",
                "the mist makes everything feel dreamlike where the laws of physics seem negotiable and uncertain",
                "fog this thick transforms the familiar into something alien where survival instincts suddenly matter"
            ]
        },
        
        # Tox Rain (intense intensity)
        'tox_rain_evening': {
            'visual': [
                "acid rain falls in corrosive droplets that eat away at surfaces and leave ugly stains",
                "toxic precipitation leaves steam and discoloration wherever it touches organic matter",
                "warning lights flicker as caustic rainfall damages exposed electrical systems with chemical fury"
            ],
            'auditory': [
                "toxic rain hisses and bubbles as it makes contact with reactive surfaces in chemical symphony",
                "metal corrodes audibly under assault of caustic precipitation that eats through everything",
                "emergency sirens wail in distance as the world responds to the chemical threat from above"
            ],
            'olfactory': [
                "air reeks with sharp, burning smell of industrial chemicals and acid that sears the nostrils",
                "toxic vapors rise from every surface touched by corrosive rainfall creating poisonous clouds",
                "atmosphere carries metallic tang of dissolved metals and burning organic compounds in deadly mixture"
            ],
            'atmospheric': [
                "toxic rain transforms everything into hazardous chemical wasteland where exposure means death",
                "every breath feels dangerous as air fills with caustic vapors that burn lungs and throat",
                "environment becomes actively hostile to all forms of life and machinery in chemical warfare"
            ]
        },
        
        'tox_rain_night': {
            'visual': [
                "poisonous rain gleams with unnatural colors as it dissolves surfaces under artificial light",
                "toxic downpour creates streams of chemical death that flow like liquid horror through everything",
                "night becomes a hellscape where rain itself is the enemy in this chemical apocalypse"
            ],
            'auditory': [
                "chemical rain sizzles and pops as it eats through materials with the sound of dissolution",
                "toxic precipitation creates symphony of destruction as metal and organic matter surrender to acid",
                "emergency broadcasts echo through the poisonous night warning of chemical contamination everywhere"
            ],
            'olfactory': [
                "air becomes unbreathable cocktail of industrial toxins that burn every breath and sear the throat",
                "poisonous vapors rise in clouds of chemical death that make the atmosphere itself lethal",
                "toxic rain brings scents of dissolution and chemical breakdown that promise only death and decay"
            ],
            'atmospheric': [
                "tox rain at night feels like the end of the world in slow motion chemical dissolution",
                "poisonous precipitation makes every surface a threat and every breath a gamble with death",
                "the toxic storm transforms familiar night into alien landscape of chemical horror and dissolution"
            ]
        },
        
        # Gray Pall (intense intensity)
        'gray_pall_midday': {
            'visual': [
                "thick, choking gray haze blots out the sun and reduces the world to sepia tones of despair",
                "oppressive smog hangs like funeral shroud over everything in sight blocking out hope and light",
                "visibility drops to mere blocks as toxic atmosphere obscures distant landmarks in poisonous haze"
            ],
            'auditory': [
                "heavy air muffles all sounds, creating oppressive silence broken only by coughing and wheezing",
                "air filtration systems work overtime with constant mechanical wheeze and rattle of desperation",
                "everything sounds sick and struggling beneath the weight of poisoned atmosphere that chokes life"
            ],
            'olfactory': [
                "air carries acrid stench of burning chemicals, industrial waste, and organic decay in toxic mixture",
                "every breath brings taste of ash, metal particles, and unidentifiable toxins that coat the throat",
                "atmosphere feels thick and oily with accumulated pollution of industrial excess and environmental collapse"
            ],
            'atmospheric': [
                "gray pall creates sense of environmental apocalypse and systemic failure of civilization itself",
                "poisoned air makes survival feel precarious and every breath a calculated risk with death",
                "everything feels like drowning in its own industrial excess and toxic legacy of human greed"
            ]
        },
        
        # Windy (mild intensity)
        'windy_afternoon': {
            'visual': [
                "strong gusts whip through everything, sending debris dancing through the air",
                "wind catches loose papers and trash, creating impromptu tornadoes of detritus",
                "flags and signs flutter frantically in the persistent breeze"
            ],
            'auditory': [
                "wind whistles through gaps with varying pitch and intensity",
                "loose objects rattle and bang as gusts push them around",
                "constant breeze creates background symphony of movement and percussion"
            ],
            'olfactory': [
                "moving air carries mixture of scents from different places",
                "wind brings brief whiffs of distant cooking, exhaust, and processes",
                "breeze keeps air fresh and prevents stagnant odors from settling"
            ],
            'atmospheric': [
                "wind brings energy and movement to otherwise static environment",
                "constant breeze creates sense of change and motion",
                "moving air makes everything feel alive and dynamic"
            ]
        },
        
        'windy_evening': {
            'visual': [
                "evening wind carries the scents and sounds of distant places",
                "gusts make artificial lights flicker and dance like living things",
                "wind turns loose objects into temporary sculptures of motion"
            ],
            'auditory': [
                "evening breeze carries voices, music, and sounds from far away",
                "wind creates symphony of whispers, rattles, and distant echoes",
                "moving air brings the sound of the world in constant motion"
            ],
            'olfactory': [
                "wind carries evening scents from kitchens, gardens, and far places",
                "breeze brings complex mixture of aromas that tell stories",
                "moving air prevents any single scent from dominating the atmosphere"
            ],
            'atmospheric': [
                "evening wind feels like the world is breathing deeply",
                "breeze brings sense of connection to distant places and possibilities",
                "moving air makes the night feel alive with potential and mystery"
            ]
        },
        
        # Overcast (mild intensity)
        'overcast_morning': {
            'visual': [
                "gray clouds blanket the sky in uniform sheets",
                "diffused light creates soft shadows everywhere",
                "the world takes on muted, monochrome quality"
            ],
            'auditory': [
                "sounds seem flatter and more subdued under cloud cover",
                "the overcast sky dampens echoes and sharpens nearby noises",
                "everything feels acoustically intimate and close"
            ],
            'olfactory': [
                "humid air carries scents more intensely than clear sky",
                "moisture in the atmosphere brings out subtle aromas",
                "overcast conditions make smells linger and blend together"
            ],
            'atmospheric': [
                "gray sky creates contemplative, introspective mood",
                "overcast conditions feel expectant and pregnant with possibility",
                "the world feels hushed and waiting under cloud cover"
            ]
        },
        
        'overcast_afternoon': {
            'visual': [
                "thick cloud cover filters sunlight into soft, even illumination",
                "everything appears in gentle, diffused light without harsh shadows",
                "gray sky creates uniform backdrop for all activity below"
            ],
            'auditory': [
                "overcast sky muffles distant sounds while amplifying nearby ones",
                "clouds seem to press sound downward creating intimate acoustics",
                "the world feels smaller and more contained under gray cover"
            ],
            'olfactory': [
                "humid overcast air intensifies every scent and aroma",
                "moisture holds smells longer creating complex atmospheric layers",
                "cloud cover traps and concentrates all environmental odors"
            ],
            'atmospheric': [
                "overcast afternoon feels cozy despite being outside",
                "gray sky creates sense of enclosed intimacy in open space",
                "the world feels softened and gentled under cloud blanket"
            ]
        },
        
        # Light Rain (moderate intensity)
        'light_rain_morning': {
            'visual': [
                "gentle droplets fall with lazy, intermittent rhythm from gray sky",
                "light rain creates subtle patterns on surfaces without overwhelming them",
                "morning takes on soft, watercolor quality under gentle precipitation"
            ],
            'auditory': [
                "light rain patters softly with irregular, peaceful rhythm",
                "gentle precipitation creates whispered percussion against surfaces",
                "the world sounds cleaner and more intimate under light rain"
            ],
            'olfactory': [
                "light rain brings fresh, clean scent without overwhelming intensity",
                "gentle precipitation releases subtle earth and pavement aromas",
                "air carries hint of moisture and renewal in soft doses"
            ],
            'atmospheric': [
                "light rain feels refreshing without being inconvenient or threatening",
                "gentle precipitation creates sense of cleansing and renewal",
                "the world feels washed and brightened by soft, caring rain"
            ]
        },
        
        'light_rain_evening': {
            'visual': [
                "evening light rain creates gentle halos around every illumination source",
                "droplets catch and reflect artificial light in thousands of tiny mirrors",
                "light precipitation adds romantic softness to evening scene"
            ],
            'auditory': [
                "gentle rain provides soft soundtrack to evening activities",
                "light precipitation creates intimate whispers against windows and surfaces",
                "the world sounds hushed and peaceful under caring rain"
            ],
            'olfactory': [
                "light evening rain brings out the scents of cooling surfaces",
                "gentle precipitation carries hints of dinner, warmth, and home",
                "air feels fresh and clean without the intensity of heavy rain"
            ],
            'atmospheric': [
                "light evening rain feels romantic and contemplative",
                "gentle precipitation makes the world feel cozy and intimate",
                "there's something peaceful and restorative in the soft droplets"
            ]
        },
        
        # Foggy Rain (moderate intensity)  
        'foggy_rain_dawn': {
            'visual': [
                "rain falls through thick mist creating layered curtains of moisture",
                "fog and precipitation combine to reduce visibility to ghostly outlines",
                "the world becomes impressionist painting of gray, water, and shadow"
            ],
            'auditory': [
                "rain sounds muffled and directionless in the thick, moisture-heavy air",
                "fog absorbs and scatters sounds while rain provides constant background",
                "everything becomes acoustically intimate and mysteriously distant"
            ],
            'olfactory': [
                "fog and rain create super-saturated air thick with moisture and scents",
                "the combination intensifies every aroma into rich, complex layers",
                "air feels thick enough to taste with humidity and precipitation"
            ],
            'atmospheric': [
                "foggy rain transforms familiar spaces into alien, dreamlike landscapes",
                "the combination creates sense of mystery and romantic danger",
                "world feels both intimate and infinite under layers of water and mist"
            ]
        },
        
        'foggy_rain_evening': {
            'visual': [
                "rain and fog combine with artificial light to create cinematic atmosphere",
                "precipitation falls through mist creating complex veils of moisture everywhere",
                "evening becomes noir landscape of shadow, reflection, and mystery"
            ],
            'auditory': [
                "rain patters through fog creating layered symphony of water sounds",
                "voices and footsteps seem to float disembodied in moisture-thick air",
                "the world becomes acoustically surreal with muffled, phantom sounds"
            ],
            'olfactory': [
                "fog and rain create almost overwhelming intensity of atmospheric scents",
                "moisture carries every aroma in super-concentrated, complex mixtures",
                "air becomes thick soup of humidity, precipitation, and urban essence"
            ],
            'atmospheric': [
                "foggy rain at evening feels like stepping into detective story",
                "the combination creates perfect atmosphere for mystery and romance",
                "world feels dangerous and beautiful under layers of mist and rain"
            ]
        },
        
        # Hard Snow (intense intensity)
        'hard_snow_afternoon': {
            'visual': [
                "heavy snowflakes fall with determined intensity creating rapidly accumulating drifts everywhere",
                "hard snow reduces visibility while coating every surface in thick, white blankets",
                "the world transforms quickly from familiar to winter wonderland under heavy precipitation"
            ],
            'auditory': [
                "hard snow falls with audible intensity creating constant whisper of accumulation",
                "footsteps crunch loudly through rapidly deepening snow with crystalline precision",
                "the world becomes muffled yet sharp as snow absorbs sound while creating new textures"
            ],
            'olfactory': [
                "hard snow brings sharp, clean scent of intense winter and frozen precipitation",
                "air carries metallic bite of serious cold mixed with fresh snow purity",
                "heavy snowfall creates atmosphere thick with moisture and crystalline clarity"
            ],
            'atmospheric': [
                "hard snow feels urgent and transformative as it rapidly changes everything",
                "heavy precipitation creates sense of nature asserting dominance over human spaces",
                "the world feels alive with winter energy and the power of accumulating snow"
            ]
        },
        
        'hard_snow_night': {
            'visual': [
                "heavy snow falls through artificial light creating swirling columns of white intensity",
                "hard precipitation accumulates rapidly turning night into winter battlefield of white",
                "snow reduces everything to essential shapes and shadows under dramatic illumination"
            ],
            'auditory': [
                "hard snow creates constant, intense whisper of millions of flakes impacting surfaces",
                "the world becomes muffled cathedral where only snow sounds matter anymore",
                "heavy precipitation drowns out distant sounds while amplifying immediate winter ones"
            ],
            'olfactory': [
                "night air fills with sharp, crystalline scent of serious snowfall and winter intensity",
                "hard snow brings metallic tang of deep cold mixed with fresh precipitation purity",
                "atmosphere becomes thick with moisture and the clean smell of winter dominance"
            ],
            'atmospheric': [
                "hard snow at night feels like nature taking control of the urban landscape",
                "heavy precipitation creates sense of winter warfare between elements and civilization",
                "the world feels transformed into something primal and beautiful under intense snowfall"
            ]
        },
        
        # Dry Thunderstorm (intense intensity)
        'dry_thunderstorm_afternoon': {
            'visual': [
                "lightning splits the sky with violent electricity while no rain falls from threatening clouds",
                "thunder rolls across landscape promising storms that never deliver water relief",
                "the sky churns with dramatic energy while ground remains parched and desperate"
            ],
            'auditory': [
                "thunder crashes with earth-shaking intensity that rattles windows and bones alike",
                "electrical discharge creates sharp cracks followed by rolling booms that never end",
                "the storm produces sound and fury without the relief of precipitation to follow"
            ],
            'olfactory': [
                "air fills with ozone and electrical charge that makes every breath taste metallic",
                "dry thunder brings scent of lightning and heated air without moisture relief",
                "atmosphere carries sharp smell of electricity and frustrated weather systems"
            ],
            'atmospheric': [
                "dry thunderstorm feels like nature's cruel joke promising relief without delivery",
                "electrical energy charges the air with tension and unfulfilled expectation",
                "the storm creates sense of power and drama without providing any actual relief"
            ]
        },
        
        'dry_thunderstorm_evening': {
            'visual': [
                "evening lightning illuminates landscape in stark, dramatic flashes without rain's blessing",
                "dry thunder creates spectacular light show against darkening sky that promises nothing",
                "storm clouds gather and churn with electrical fury while earth remains thirsty below"
            ],
            'auditory': [
                "thunder echoes through evening air with dramatic intensity that shakes everything",
                "electrical storms create symphony of booms and crashes without rain's percussion",
                "the sky roars with power while ground waits desperately for moisture that won't come"
            ],
            'olfactory': [
                "evening air fills with ozone and electrical charge mixed with dust and heat",
                "dry thunder brings sharp scents of lightning without the blessing of petrichor",
                "atmosphere tastes of electricity, frustration, and promises that won't be kept"
            ],
            'atmospheric': [
                "dry evening thunderstorm feels like dramatic performance without substance",
                "electrical energy creates anticipation and excitement that leads to disappointment",
                "the storm charges air with power while delivering nothing but sound and fury"
            ]
        },
        
        # Rainy Thunderstorm (intense intensity)
        'rainy_thunderstorm_afternoon': {
            'visual': [
                "lightning illuminates sheets of rain falling with violent intensity from churning storm clouds",
                "thunder and downpour combine to create spectacular display of nature's raw power unleashed",
                "the world disappears behind walls of water punctuated by brilliant flashes of electricity"
            ],
            'auditory': [
                "thunder crashes over the roar of torrential rain creating deafening symphony of chaos",
                "storm produces overwhelming cacophony of electrical discharge and water percussion",
                "the world drowns in sound as thunder and deluge compete for acoustic dominance"
            ],
            'olfactory': [
                "air fills with ozone, petrichor, and electrical charge creating intoxicating storm atmosphere",
                "rainy thunder brings every scent alive with moisture, electricity, and primal energy",
                "atmosphere becomes thick cocktail of lightning, rain, and earth responding to bombardment"
            ],
            'atmospheric': [
                "rainy thunderstorm feels like witnessing nature's absolute fury and power unleashed completely",
                "storm creates sense of being small and vulnerable before elemental forces beyond control",
                "the world becomes primal battlefield where electricity and water wage war above"
            ]
        },
        
        'rainy_thunderstorm_night': {
            'visual': [
                "night storm illuminates cascading rain in brilliant flashes that turn water into liquid silver",
                "lightning reveals the fury of deluge for split seconds before darkness reclaims everything",
                "thunder and rain create dramatic night scene of power, water, and electrical violence"
            ],
            'auditory': [
                "nighttime storm produces overwhelming symphony of rain percussion and thunder explosions",
                "electrical discharge punctuates constant roar of water with sharp cracks and rolling booms",
                "the world becomes acoustic chaos where thunder and deluge create deafening natural music"
            ],
            'olfactory': [
                "night air fills with intoxicating mixture of ozone, rain, and electrical discharge energy",
                "storm brings every scent alive with moisture, lightning, and primal atmospheric power",
                "atmosphere becomes thick with the smell of electricity, water, and earth under assault"
            ],
            'atmospheric': [
                "rainy night thunderstorm feels like being inside nature's most powerful and beautiful tantrum",
                "storm creates sense of witnessing elemental forces that dwarf human concerns completely",
                "the world becomes cathedral of power where electricity and water create divine chaos"
            ]
        },
        
        # Blind Fog (intense intensity)
        'blind_fog_morning': {
            'visual': [
                "impenetrable fog reduces visibility to absolute zero creating world of pure gray nothingness",
                "thick mist swallows everything beyond arm's reach making navigation purely tactile experience",
                "blind fog transforms familiar landscape into alien void where sight becomes useless sense"
            ],
            'auditory': [
                "sounds become completely directionless and distorted in fog so thick it swallows echoes",
                "blind fog creates acoustic maze where familiar noises seem to come from everywhere",
                "the world becomes purely auditory as thick mist makes every sound mysterious and threatening"
            ],
            'olfactory': [
                "fog becomes so thick it carries concentrated essence of everything it touches",
                "blind mist intensifies every scent until air tastes of moisture and accumulated odors",
                "atmosphere becomes soup thick enough to drink with layers of smell and humidity"
            ],
            'atmospheric': [
                "blind fog creates sense of being completely cut off from normal world and reality",
                "thick mist makes every familiar space feel alien and potentially dangerous to navigate",
                "the world becomes pure sensory experience where sight fails and other senses must dominate"
            ]
        },
        
        'blind_fog_evening': {
            'visual': [
                "evening fog becomes so thick that artificial lights create useless halos in impenetrable mist",
                "blind fog swallows illumination whole making navigation impossible despite bright sources",
                "thick evening mist transforms well-lit areas into void where light becomes decoration only"
            ],
            'auditory': [
                "evening sounds become phantom whispers in fog so thick it distorts every acoustic reference",
                "blind mist makes familiar evening noises seem to come from inside your own head",
                "the world becomes purely auditory maze where sound travels through fog like liquid medium"
            ],
            'olfactory': [
                "evening fog carries concentrated mixture of every scent until air becomes almost solid",
                "blind mist intensifies evening aromas into overwhelming sensory assault that coats everything",
                "atmosphere becomes thick enough to chew with layers of humidity and accumulated essences"
            ],
            'atmospheric': [
                "blind evening fog creates sense of being trapped in gray void separate from reality",
                "thick mist makes familiar evening spaces feel like alien dimension of pure sensation",
                "the world becomes surreal experience where normal rules of navigation and sight fail completely"
            ]
        },
        
        # Missing blizzard combinations
        'blizzard_dawn': {
            'visual': [
                "dawn light fails to penetrate the wall of swirling snow and ice",
                "blizzard transforms morning into arctic nightmare of white chaos",
                "ice crystals slice through air like frozen daggers in the howling wind"
            ],
            'auditory': [
                "wind roars with primal fury that drowns out dawn's usual sounds",
                "blizzard creates deafening wall of sound from countless ice particles",
                "the storm screams with voices of winter unleashed in full fury"
            ],
            'olfactory': [
                "frozen air burns nostrils with sharp bite of extreme cold",
                "blizzard strips away all warmth leaving only crystalline purity",
                "the scent of snow and ice dominates every frozen breath"
            ],
            'atmospheric': [
                "blizzard dawn feels like nature declaring war on warmth itself",
                "the storm makes survival the only thought that matters",
                "frozen fury transforms familiar world into alien arctic wasteland"
            ]
        },
        
        'blizzard_dusk': {
            'visual': [
                "dusk disappears behind walls of driving snow and ice",
                "blizzard turns evening into white void of swirling chaos",
                "darkness and snow merge into one impenetrable curtain of winter"
            ],
            'auditory': [
                "wind howls through dusk with banshee intensity that chills the soul",
                "blizzard drowns out evening sounds in its icy symphony of destruction",
                "the storm creates constant roar of snow against every surface"
            ],
            'olfactory': [
                "evening air becomes sharp blade of cold that cuts through everything",
                "blizzard brings sterile scent of snow and sub-zero temperatures",
                "frozen precipitation strips away all familiar evening aromas"
            ],
            'atmospheric': [
                "blizzard dusk feels like watching the world freeze to death",
                "the storm makes warmth seem like distant memory of better times",
                "winter fury transforms dusk into something alien and hostile"
            ]
        },
        
        # Missing rain combinations  
        'rain_early_morning': {
            'visual': [
                "morning rain turns everything into impressionist watercolor paintings",
                "droplets catch early light creating liquid diamonds on every surface",
                "steady precipitation transforms dawn into silver-washed symphony of water"
            ],
            'auditory': [
                "rain patters against surfaces with rhythmic morning percussion",
                "water gurgles through drains with liquid whispers of renewal",
                "precipitation creates gentle white noise that softens harsh edges"
            ],
            'olfactory': [
                "wet morning air carries petrichor mixed with awakening earth scents",
                "rain releases stored aromas from pavement and hidden corners",
                "moisture brings out subtle fragrances that night had concealed"
            ],
            'atmospheric': [
                "morning rain feels like nature's gentle blessing on the new day",
                "wet air creates intimate cocoon around familiar spaces",
                "precipitation makes everything feel washed clean and renewed"
            ]
        },
        
        'rain_late_morning': {
            'visual': [
                "late morning rain creates steady curtains of silver falling from gray sky",
                "precipitation turns busy streets into reflective mirrors of activity",
                "rain transforms peak morning energy into something more subdued and intimate"
            ],
            'auditory': [
                "steady rainfall provides constant backdrop to morning productivity",
                "rain percussion mixes with sounds of life continuing despite weather",
                "water splashing through puddles adds rhythm to urban symphony"
            ],
            'olfactory': [
                "rain-soaked air carries mixture of wet concrete and morning activity",
                "precipitation brings out earthy scents mixed with industrial undertones",
                "moisture intensifies both pleasant and harsh urban aromas"
            ],
            'atmospheric': [
                "late morning rain creates sense of cozy productivity despite wetness",
                "precipitation makes the busy world feel more intimate and contained",
                "wet air brings contemplative quality to otherwise energetic time"
            ]
        },
        
        'rain_midday': {
            'visual': [
                "midday rain falls with steady determination from overcast sky",
                "precipitation creates silver sheets that soften harsh daylight",
                "rain transforms peak energy into something more muted and gentle"
            ],
            'auditory': [
                "steady rain provides cooling soundtrack to heated midday activity",
                "precipitation creates white noise that dampens urban intensity",
                "water sounds bring relief from overwhelming peak-hour cacophony"
            ],
            'olfactory': [
                "rain cools heated surfaces releasing steam and complex aromas",
                "precipitation brings earthy relief to sun-baked urban environment",
                "wet air carries mixture of cooling pavement and fresh moisture"
            ],
            'atmospheric': [
                "midday rain feels like nature's air conditioning for overheated world",
                "precipitation brings blessed relief from oppressive heat and energy",
                "wet atmosphere creates sense of cooling grace during peak intensity"
            ]
        },
        
        # Missing overcast combinations
        'overcast_pre_dawn': {
            'visual': [
                "thick clouds press down like gray blanket over sleeping world",
                "overcast pre-dawn creates muted landscape of soft shadows",
                "cloud cover diffuses scattered lights into gentle halos"
            ],
            'auditory': [
                "sounds feel compressed and intimate under heavy cloud cover",
                "overcast sky creates acoustic dampening that muffles distant noise",
                "everything feels quieter and more contained under gray ceiling"
            ],
            'olfactory': [
                "humid overcast air holds scents longer in moisture-heavy atmosphere",
                "cloud cover traps aromas creating concentrated layers of smell",
                "pre-dawn air feels thick with accumulated overnight essence"
            ],
            'atmospheric': [
                "overcast pre-dawn feels expectant and heavy with possibility",
                "gray sky creates sense of world holding its breath before sunrise",
                "cloud cover makes familiar spaces feel smaller and more intimate"
            ]
        },
        
        'overcast_dawn': {
            'visual': [
                "dawn struggles through thick cloud cover in muted silver light",
                "overcast sky filters morning into soft watercolor washes",
                "gray clouds create gentle backdrop for awakening world"
            ],
            'auditory': [
                "dawn sounds feel softened and intimate under cloud blanket",
                "overcast conditions create natural sound dampening effect",
                "morning chorus becomes more subdued under gray sky"
            ],
            'olfactory': [
                "humid dawn air carries concentrated scents in moisture-heavy atmosphere",
                "overcast conditions intensify morning aromas and fragrances",
                "cloud cover holds rising scents creating layered atmospheric essence"
            ],
            'atmospheric': [
                "overcast dawn feels gentle and contemplative rather than energetic",
                "gray sky creates sense of world awakening slowly and peacefully",
                "cloud cover makes morning feel more intimate and enclosed"
            ]
        },
        
        # Missing windy combinations
        'windy_pre_dawn': {
            'visual': [
                "pre-dawn wind sets everything in motion against dark sky",
                "gusts catch scattered lights making them flicker and dance",
                "wind turns loose debris into night-time choreography of movement"
            ],
            'auditory': [
                "wind whistles through pre-dawn quiet with varying intensity",
                "gusts create symphony of rattles, whispers, and distant sounds",
                "moving air carries voices and noises from far-off places"
            ],
            'olfactory': [
                "wind brings mixture of scents from distant locations and sources",
                "moving air prevents stagnation carrying fresh combinations of aromas",
                "breeze mixes night scents with hints of approaching dawn"
            ],
            'atmospheric': [
                "pre-dawn wind makes the sleeping world feel alive and breathing",
                "moving air creates sense of connection to broader world beyond",
                "gusts bring energy and movement to otherwise still darkness"
            ]
        },
        
        'windy_dawn': {
            'visual': [
                "dawn wind sets morning light dancing through moving air",
                "gusts catch first light creating shifting patterns of illumination",
                "wind transforms static dawn into dynamic display of motion"
            ],
            'auditory': [
                "morning wind creates symphony of whistles, rustles, and movement",
                "gusts carry dawn sounds from distant places mixing familiar and foreign",
                "moving air adds percussion to morning's awakening chorus"
            ],
            'olfactory': [
                "dawn wind carries fresh mixture of morning scents and aromas",
                "moving air brings complex combination of awakening world fragrances",
                "breeze mixes cool night air with warming morning essence"
            ],
            'atmospheric': [
                "windy dawn feels energetic and full of possibility and movement",
                "moving air makes morning feel dynamic and alive with potential",
                "gusts bring sense of world stirring to life with natural rhythm"
            ]
        },
        
        # Additional missing fog combinations
        'fog_pre_dawn': {
            'visual': [
                "pre-dawn fog creates ghostly world of muted shapes and shadows",
                "thick mist transforms scattered lights into soft ethereal glows",
                "fog reduces pre-dawn world to intimate sphere of gray visibility"
            ],
            'auditory': [
                "sounds become directionless whispers in the moisture-heavy air",
                "fog absorbs and scatters pre-dawn noises into mysterious echoes",
                "mist creates acoustic maze where familiar sounds become alien"
            ],
            'olfactory': [
                "fog carries concentrated essence of night mixed with approaching dawn",
                "moisture intensifies every scent creating rich atmospheric layers",
                "humid air holds complex mixture of accumulated overnight aromas"
            ],
            'atmospheric': [
                "pre-dawn fog creates sense of world suspended between night and day",
                "mist makes familiar spaces feel mysterious and full of possibility",
                "fog transforms ordinary pre-dawn into something magical and uncertain"
            ]
        },
        
        'fog_night': {
            'visual': [
                "night fog swallows artificial lights creating useless halos in gray void",
                "thick mist transforms illuminated spaces into ghostly approximations",
                "fog reduces night world to arm's length of gray mystery"
            ],
            'auditory': [
                "night sounds become phantom whispers floating in moisture-thick air",
                "fog makes familiar evening noises seem to come from everywhere and nowhere",
                "mist creates acoustic illusions where sound travels like liquid"
            ],
            'olfactory': [
                "night fog carries every scent in concentrated doses of humid air",
                "moisture intensifies evening aromas until they become almost tangible",
                "fog holds complex layers of night scents in thick atmospheric soup"
            ],
            'atmospheric': [
                "night fog creates world that feels separate from normal reality",
                "mist makes everything dreamlike where familiar becomes strange",
                "fog transforms night into something both intimate and otherworldly"
            ]
        },
        
        # Missing soft_snow combinations
        'soft_snow_dawn': {
            'visual': [
                "gentle snowflakes catch dawn light like falling stars against pale sky",
                "soft snow creates pristine white canvas for morning's first light",
                "delicate precipitation transforms dawn into winter fairy tale scene"
            ],
            'auditory': [
                "soft snow falls with whispered silence that muffles dawn sounds",
                "gentle precipitation creates peaceful hush over awakening world",
                "snow adds contemplative quiet to morning's usual energy"
            ],
            'olfactory': [
                "dawn air carries clean scent of fresh snow and winter purity",
                "soft precipitation brings sharp clarity that cleanses every breath",
                "snow masks harsh odors with neutral essence of frozen water"
            ],
            'atmospheric': [
                "soft dawn snow feels like nature's gentle blessing on new day",
                "gentle precipitation creates sense of peace and temporary beauty",
                "winter morning transforms everything into something magical and serene"
            ]
        },
        
        'soft_snow_night': {
            'visual': [
                "gentle snow falls through artificial light creating magical columns of white",
                "soft precipitation turns night into winter wonderland of quiet beauty",
                "delicate snowflakes catch illumination like tiny dancing spirits"
            ],
            'auditory': [
                "soft snow creates cathedral quiet broken only by gentle whispers",
                "night sounds become muffled and intimate under falling precipitation",
                "gentle snowfall adds peaceful backdrop to evening's sounds"
            ],
            'olfactory': [
                "night air sharpened by clean scent of fresh snow and winter cold",
                "soft precipitation brings crystalline purity to evening atmosphere",
                "snow adds neutral freshness to night's complex aromatic layers"
            ],
            'atmospheric': [
                "soft night snow feels like world being tucked in for peaceful sleep",
                "gentle precipitation creates sense of magical transformation and peace",
                "winter night becomes something serene and contemplatively beautiful"
            ]
        },
        
        # Missing clear combinations (none missing - all 12 are present)
        # Missing rain combinations (continue)
        'rain_early_afternoon': {
            'visual': [
                "afternoon rain falls steadily turning busy streets into mirror-like rivers",
                "precipitation creates silver curtains that soften harsh afternoon light",
                "rain transforms peak afternoon energy into something more subdued"
            ],
            'auditory': [
                "steady rain provides cooling soundtrack to heated afternoon activity",
                "precipitation creates rhythmic backdrop to ongoing urban symphony",
                "rain sounds bring sense of relief to overwhelming afternoon intensity"
            ],
            'olfactory': [
                "afternoon rain cools heated surfaces releasing complex steam and aromas",
                "precipitation brings earthy relief to sun-baked urban environment",
                "wet air carries mixture of cooled pavement and fresh moisture"
            ],
            'atmospheric': [
                "afternoon rain feels like nature's cooling grace during peak heat",
                "precipitation brings blessed relief from oppressive energy and temperature",
                "wet atmosphere creates sense of gentle respite from daily intensity"
            ]
        },
        
        'rain_late_afternoon': {
            'visual': [
                "late afternoon rain catches golden light creating liquid amber streams",
                "precipitation turns rush hour into reflective symphony of water and light",
                "rain transforms busy late afternoon into contemplative water-washed scene"
            ],
            'auditory': [
                "rain percussion mixes with sounds of evening commute and activity",
                "precipitation adds liquid rhythm to late afternoon's energetic pace",
                "water sounds create counterpoint to urban intensity and movement"
            ],
            'olfactory': [
                "late afternoon rain releases day's accumulated heat in aromatic steam",
                "precipitation brings complex mixture of cooling surfaces and moisture",
                "wet air carries hints of evening approaching through rain-washed atmosphere"
            ],
            'atmospheric': [
                "late afternoon rain creates sense of day winding down through water",
                "precipitation makes evening approach feel gentle and contemplative",
                "rain brings peaceful transition from day's energy to evening's calm"
            ]
        },
        
        'rain_dusk': {
            'visual': [
                "dusk rain creates ethereal curtains of water against purple and orange sky",
                "precipitation catches last light turning drops into liquid jewels",
                "rain transforms sunset into impressionist masterpiece of water and color"
            ],
            'auditory': [
                "rain provides gentle percussion to dusk's transitional sounds",
                "precipitation creates intimate soundtrack to evening's approach",
                "water sounds mix with dusk chorus creating layered atmospheric music"
            ],
            'olfactory': [
                "dusk rain brings out evening scents mixed with fresh precipitation",
                "wet air carries complex mixture of cooling day and approaching night",
                "rain intensifies dusk aromas creating rich atmospheric layers"
            ],
            'atmospheric': [
                "rainy dusk feels romantic and full of transitional possibility",
                "precipitation makes evening approach feel gentle and mysterious",
                "wet air creates sense of world being washed clean for night's arrival"
            ]
        },
        
        # Continue with more missing combinations
        'rain_early_evening': {
            'visual': [
                "early evening rain creates intimate atmosphere with artificial lights reflecting in puddles",
                "precipitation turns nightlife into something more contemplative and romantic",
                "rain transforms busy evening into cozy water-washed scene"
            ],
            'auditory': [
                "rain provides gentle backdrop to early evening's social energy",
                "precipitation creates intimate soundtrack to nightlife's beginning",
                "water sounds mix with voices and music creating layered urban symphony"
            ],
            'olfactory': [
                "evening rain brings out scents of restaurants and entertainment mixed with moisture",
                "wet air carries complex mixture of nightlife aromas and fresh precipitation",
                "rain intensifies evening scents creating rich atmospheric cocktail"
            ],
            'atmospheric': [
                "rainy early evening feels romantic and socially intimate",
                "precipitation makes nightlife feel more cozy and contemplative",
                "wet air creates sense of shared experience and communal warmth"
            ]
        },
        
        'rain_late_evening': {
            'visual': [
                "late evening rain creates cinematic atmosphere with neon reflections in wet streets",
                "precipitation turns night into noir landscape of water and light",
                "rain transforms late evening into something mysterious and beautiful"
            ],
            'auditory': [
                "rain creates intimate backdrop to late evening's quieter energy",
                "precipitation provides contemplative soundtrack to night's progression",
                "water sounds mix with distant nightlife creating peaceful urban lullaby"
            ],
            'olfactory': [
                "late evening rain carries scents of cooling night mixed with moisture",
                "wet air holds complex layers of evening aromas intensified by precipitation",
                "rain brings out hidden nighttime scents creating atmospheric richness"
            ],
            'atmospheric': [
                "rainy late evening feels mysterious and romantically contemplative",
                "precipitation makes night feel more intimate and personally meaningful",
                "wet air creates sense of solitude and peaceful introspection"
            ]
        },
        
        'rain_late_night': {
            'visual': [
                "late night rain falls through sparse lighting creating isolated columns of silver",
                "precipitation turns deep night into intimate world of water and shadow",
                "rain creates solitary beauty in the quiet late evening hours"
            ],
            'auditory': [
                "rain provides only soundtrack to late night's deep quiet",
                "precipitation creates meditative rhythm in the stillness of deep evening",
                "water sounds become primary voice in night's contemplative silence"
            ],
            'olfactory': [
                "late night rain sharpens air with clean scent of water and solitude",
                "precipitation brings crystalline clarity to night's atmospheric layers",
                "wet air carries concentrated essence of deep night mixed with rain"
            ],
            'atmospheric': [
                "rainy late night feels deeply contemplative and peacefully solitary",
                "precipitation makes deep night feel cleansing and spiritually renewing",
                "wet air creates sense of world being washed clean for tomorrow's possibilities"
            ]
        },
        
        # More missing overcast combinations
        'overcast_early_morning': {
            'visual': [
                "early morning cloud cover creates soft diffused light without harsh shadows",
                "overcast sky filters morning energy into something more gentle and subdued",
                "gray clouds provide uniform backdrop for awakening activity"
            ],
            'auditory': [
                "morning sounds feel compressed and intimate under heavy cloud cover",
                "overcast conditions create natural acoustic dampening effect",
                "clouds press sound downward making everything feel closer and more personal"
            ],
            'olfactory': [
                "humid morning air under clouds holds scents longer creating rich layers",
                "overcast conditions trap and concentrate awakening world's aromas",
                "cloud cover creates greenhouse effect intensifying morning fragrances"
            ],
            'atmospheric': [
                "overcast early morning feels cozy and contemplatively productive",
                "gray sky creates sense of enclosed intimacy during busy morning",
                "cloud cover makes world feel smaller and more manageable"
            ]
        },
        
        'overcast_late_morning': {
            'visual': [
                "late morning clouds create soft even lighting perfect for sustained activity",
                "overcast sky eliminates harsh glare making everything appear gentle and muted",
                "gray cloud cover provides consistent backdrop to peak morning energy"
            ],
            'auditory': [
                "late morning sounds feel softened and contained under cloud blanket",
                "overcast sky creates acoustic intimacy despite busy urban activity",
                "clouds compress sound making busy world feel more manageable"
            ],
            'olfactory': [
                "humid overcast air intensifies late morning's complex aromatic mixture",
                "cloud cover traps scents creating concentrated layers of urban essence",
                "moisture holds morning aromas creating rich atmospheric cocktail"
            ],
            'atmospheric': [
                "overcast late morning feels productively focused and energetically contained",
                "gray sky creates sense of productive intimacy during peak activity",
                "cloud cover makes busy morning feel more approachable and human-scaled"
            ]
        },
        
        'overcast_midday': {
            'visual': [
                "midday clouds provide relief from harsh sun creating gentle diffused illumination",
                "overcast sky eliminates glare and heat shimmer making world appear calm",
                "gray cloud cover transforms intense midday into something more bearable"
            ],
            'auditory': [
                "midday sounds feel less overwhelming under softening cloud cover",
                "overcast conditions dampen peak-hour intensity creating acoustic relief",
                "clouds provide natural sound absorption making busy time more peaceful"
            ],
            'olfactory': [
                "overcast midday air feels cooler and more breathable than harsh sun",
                "cloud cover prevents heat buildup reducing intensity of urban aromas",
                "humid conditions under clouds create more pleasant atmospheric mixture"
            ],
            'atmospheric': [
                "overcast midday feels like blessed relief from oppressive peak intensity",
                "gray sky creates sense of natural air conditioning during hottest time",
                "cloud cover makes midday energy feel more manageable and humane"
            ]
        },
        
        'overcast_early_afternoon': {
            'visual': [
                "early afternoon clouds filter light into soft golden tones without harsh glare",
                "overcast sky creates gentle backdrop for sustained afternoon activity",
                "gray cloud cover eliminates shadows making everything appear evenly lit"
            ],
            'auditory': [
                "afternoon sounds feel softened and pleasant under protective cloud cover",
                "overcast conditions create acoustic comfort during typically intense time",
                "clouds dampen harsh edges of peak afternoon urban symphony"
            ],
            'olfactory': [
                "humid afternoon air under clouds feels fresh and breathable",
                "overcast conditions prevent heat concentration creating pleasant atmosphere",
                "cloud cover moderates afternoon aromas making them more enjoyable"
            ],
            'atmospheric': [
                "overcast early afternoon feels pleasantly productive without oppressive heat",
                "gray sky creates sense of comfortable energy during typically harsh time",
                "cloud cover makes afternoon feel more approachable and sustainably active"
            ]
        },
        
        'overcast_late_afternoon': {
            'visual': [
                "late afternoon clouds create soft golden light perfect for evening approach",
                "overcast sky filters rush hour energy into something more contemplative",
                "gray cloud cover provides gentle transition from day to evening"
            ],
            'auditory': [
                "late afternoon sounds feel mellowed and intimate under cloud blanket",
                "overcast conditions soften rush hour intensity creating peaceful backdrop",
                "clouds absorb harsh edges making evening approach feel more gentle"
            ],
            'olfactory': [
                "humid late afternoon air carries cooling scents without overwhelming heat",
                "overcast conditions create pleasant mixture of day's end aromas",
                "cloud cover holds evening approach scents in comfortable atmospheric layers"
            ],
            'atmospheric': [
                "overcast late afternoon feels like peaceful transition from day to night",
                "gray sky creates sense of gentle winding down from daily activity",
                "cloud cover makes evening approach feel contemplative and naturally paced"
            ]
        },
        
        'overcast_dusk': {
            'visual': [
                "dusk clouds create muted palette of grays and soft purples",
                "overcast sky filters sunset into gentle gradations of subdued color",
                "cloud cover transforms dramatic dusk into something soft and contemplative"
            ],
            'auditory': [
                "dusk sounds feel intimate and contained under thick cloud blanket",
                "overcast conditions create acoustic cocoon around transitional evening",
                "clouds absorb harsh edges making dusk feel peaceful and approachable"
            ],
            'olfactory': [
                "humid dusk air under clouds carries gentle mixture of day's end scents",
                "overcast conditions hold cooling aromas in comfortable atmospheric layers",
                "cloud cover creates pleasant transition from day to night fragrances"
            ],
            'atmospheric': [
                "overcast dusk feels romantically contemplative and peacefully transitional",
                "gray sky creates sense of gentle passage from day to evening",
                "cloud cover makes sunset feel intimate and personally meaningful"
            ]
        },
        
        'overcast_early_evening': {
            'visual': [
                "early evening clouds create soft backdrop for artificial lights beginning to glow",
                "overcast sky provides gentle transition into night's illuminated landscape",
                "gray cloud cover makes evening lights feel warm and welcoming"
            ],
            'auditory': [
                "evening sounds feel cozy and contained under protective cloud blanket",
                "overcast conditions create intimate acoustic environment for nightlife's start",
                "clouds compress sound making early evening feel more personal and approachable"
            ],
            'olfactory': [
                "humid early evening air carries restaurant and entertainment scents softly",
                "overcast conditions create pleasant mixture of nightlife aromas without intensity",
                "cloud cover holds evening scents creating comfortable atmospheric richness"
            ],
            'atmospheric': [
                "overcast early evening feels cozy and socially intimate",
                "gray sky creates sense of enclosed warmth during nightlife's beginning",
                "cloud cover makes evening feel more approachable and humanly scaled"
            ]
        },
        
        'overcast_late_evening': {
            'visual': [
                "late evening clouds create soft ceiling above illuminated nightlife",
                "overcast sky provides gentle backdrop for night's established rhythm",
                "gray cloud cover makes artificial lights feel warm and enclosed"
            ],
            'auditory': [
                "late evening sounds feel mellowed and intimate under cloud protection",
                "overcast conditions create acoustic comfort during night's progression",
                "clouds absorb harsh edges making nightlife feel more contemplative"
            ],
            'olfactory': [
                "humid late evening air under clouds holds night scents pleasantly",
                "overcast conditions create rich but comfortable aromatic atmosphere",
                "cloud cover moderates nightlife intensity making aromas more enjoyable"
            ],
            'atmospheric': [
                "overcast late evening feels romantically intimate and contemplatively peaceful",
                "gray sky creates sense of enclosed warmth during night's deeper hours",
                "cloud cover makes late evening feel personally meaningful and spiritually rich"
            ]
        },
        
        'overcast_night': {
            'visual': [
                "night clouds create soft ceiling that reflects and diffuses artificial light",
                "overcast sky provides gentle backdrop for established nighttime rhythm",
                "gray cloud cover makes night feel enclosed and intimately contained"
            ],
            'auditory': [
                "night sounds feel softened and contemplative under protective cloud blanket",
                "overcast conditions create acoustic intimacy perfect for night's quiet energy",
                "clouds absorb harsh edges making night feel peaceful and spiritually rich"
            ],
            'olfactory': [
                "humid night air under clouds carries concentrated evening essence",
                "overcast conditions create rich atmospheric layers without overwhelming intensity",
                "cloud cover holds night scents creating comfortable aromatic cocoon"
            ],
            'atmospheric': [
                "overcast night feels deeply contemplative and spiritually renewing",
                "gray sky creates sense of enclosed peace perfect for introspection",
                "cloud cover makes night feel personally meaningful and emotionally rich"
            ]
        },
        
        'overcast_late_night': {
            'visual': [
                "late night clouds create soft gray ceiling above sparse illumination",
                "overcast sky provides gentle backdrop for deep night's solitary beauty",
                "gray cloud cover makes late night feel enclosed and peacefully isolated"
            ],
            'auditory': [
                "late night sounds feel deeply muffled and contemplative under thick clouds",
                "overcast conditions create acoustic solitude perfect for deep introspection",
                "clouds absorb sound making late night feel spiritually rich and peaceful"
            ],
            'olfactory': [
                "humid late night air holds concentrated essence of deep evening",
                "overcast conditions create rich atmospheric layers perfect for contemplation",
                "cloud cover holds night scents creating aromatic cocoon of solitude"
            ],
            'atmospheric': [
                "overcast late night feels deeply peaceful and spiritually contemplative",
                "gray sky creates sense of enclosed solitude perfect for inner reflection",
                "cloud cover makes deep night feel personally transformative and emotionally healing"
            ]
        },
        
        # Complete light_rain combinations (moderate intensity)
        'light_rain_pre_dawn': {
            'visual': [
                "gentle pre-dawn droplets fall intermittently from gray sky above",
                "light precipitation creates subtle patterns on surfaces in scattered illumination",
                "soft rain adds delicate texture to pre-dawn's quiet landscape"
            ],
            'auditory': [
                "light rain provides gentle percussion to pre-dawn's hushed atmosphere",
                "gentle droplets create whispered soundtrack to night's final hours",
                "soft precipitation adds peaceful rhythm to early morning quiet"
            ],
            'olfactory': [
                "light rain brings fresh clean scent mixed with pre-dawn's cool air",
                "gentle precipitation carries hint of moisture and approaching dawn",
                "soft droplets release subtle earth aromas from cooling surfaces"
            ],
            'atmospheric': [
                "light pre-dawn rain feels like nature's gentle blessing before sunrise",
                "gentle precipitation creates sense of peaceful transition and renewal",
                "soft rain makes pre-dawn feel cleansing and full of quiet possibility"
            ]
        },
        
        'light_rain_dawn': {
            'visual': [
                "dawn light filters through gentle rain creating silver-washed morning scene",
                "light precipitation catches first light in thousands of tiny prisms",
                "soft rain transforms awakening world into watercolor painting"
            ],
            'auditory': [
                "gentle rain provides soft soundtrack to dawn's awakening chorus",
                "light precipitation creates peaceful backdrop to morning's first sounds",
                "soft droplets add contemplative rhythm to day's beginning"
            ],
            'olfactory': [
                "dawn rain brings fresh petrichor mixed with morning's awakening scents",
                "light precipitation releases earth aromas as surfaces cool and moisten",
                "gentle rain carries hint of renewal and day's fresh possibilities"
            ],
            'atmospheric': [
                "light dawn rain feels like gentle blessing on the awakening world",
                "soft precipitation creates sense of peaceful beginning and renewal",
                "gentle rain makes dawn feel contemplative and spiritually refreshing"
            ]
        },
        
        'light_rain_early_morning': {
            'visual': [
                "early morning light rain creates gentle backdrop to increasing activity",
                "soft precipitation adds delicate texture to busy morning landscape",
                "light droplets catch growing daylight in subtle displays of water"
            ],
            'auditory': [
                "gentle rain provides peaceful counterpoint to morning's growing energy",
                "light precipitation creates soft rhythm beneath urban awakening",
                "soft droplets add contemplative quality to increasing activity"
            ],
            'olfactory': [
                "morning rain brings fresh scent that mixes pleasantly with awakening aromas",
                "light precipitation releases gentle earth fragrances from moistened surfaces",
                "soft rain carries clean essence that refreshes morning air"
            ],
            'atmospheric': [
                "light early morning rain feels refreshing without disrupting productivity",
                "gentle precipitation creates sense of blessed coolness during warming day",
                "soft rain makes busy morning feel more peaceful and manageable"
            ]
        },
        
        'light_rain_late_morning': {
            'visual': [
                "late morning light rain provides gentle relief from growing intensity",
                "soft precipitation creates subtle patterns on surfaces during peak activity",
                "gentle droplets add cooling visual texture to heated urban landscape"
            ],
            'auditory': [
                "light rain offers peaceful soundtrack to late morning's energetic pace",
                "gentle precipitation provides soft rhythm beneath productive activity",
                "soft droplets create contemplative backdrop to busy morning sounds"
            ],
            'olfactory': [
                "late morning rain brings cooling scent that refreshes heated air",
                "light precipitation releases pleasant earth aromas from warming surfaces",
                "gentle rain carries clean essence that balances urban morning intensity"
            ],
            'atmospheric': [
                "light late morning rain feels like nature's gentle cooling grace",
                "soft precipitation creates blessed relief from building heat and energy",
                "gentle rain makes productive morning feel more comfortable and sustainable"
            ]
        },
        
        'light_rain_midday': {
            'visual': [
                "midday light rain provides welcome relief from harsh sun and glare",
                "gentle precipitation creates cooling silver curtains against intense light",
                "soft droplets add refreshing texture to overheated urban environment"
            ],
            'auditory': [
                "light rain offers peaceful respite from midday's overwhelming sounds",
                "gentle precipitation provides cooling soundtrack to peak intensity",
                "soft droplets create blessed acoustic relief from harsh midday energy"
            ],
            'olfactory': [
                "midday rain brings cooling scent that provides relief from heated air",
                "light precipitation releases refreshing earth aromas from baked surfaces",
                "gentle rain carries clean essence that cuts through midday's intensity"
            ],
            'atmospheric': [
                "light midday rain feels like blessed relief from oppressive heat",
                "gentle precipitation creates natural cooling that makes peak time bearable",
                "soft rain transforms harsh midday into something more gentle and humane"
            ]
        },
        
        'light_rain_early_afternoon': {
            'visual': [
                "early afternoon light rain creates gentle cooling against warm sunlight",
                "soft precipitation adds refreshing texture to heated afternoon landscape",
                "gentle droplets catch afternoon light creating subtle water displays"
            ],
            'auditory': [
                "light rain provides peaceful counterpoint to afternoon's sustained energy",
                "gentle precipitation creates soft rhythm beneath continued productivity",
                "soft droplets add cooling quality to afternoon's busy soundscape"
            ],
            'olfactory': [
                "afternoon rain brings refreshing scent that cools heated air pleasantly",
                "light precipitation releases cooling earth aromas from warmed surfaces",
                "gentle rain carries clean essence that refreshes afternoon atmosphere"
            ],
            'atmospheric': [
                "light early afternoon rain feels like gentle cooling grace during heat",
                "soft precipitation creates blessed relief from accumulated warmth",
                "gentle rain makes sustained afternoon activity feel more comfortable"
            ]
        },
        
        'light_rain_late_afternoon': {
            'visual': [
                "late afternoon light rain catches golden hour light in dancing droplets",
                "gentle precipitation creates beautiful interplay with warm evening approach",
                "soft rain transforms rush hour energy into something more contemplative"
            ],
            'auditory': [
                "light rain provides peaceful soundtrack to late afternoon's energy",
                "gentle precipitation creates soft rhythm beneath evening's approach",
                "soft droplets add contemplative quality to day's winding down"
            ],
            'olfactory': [
                "late afternoon rain brings cooling scent mixed with day's accumulated warmth",
                "light precipitation releases pleasant earth aromas as surfaces begin cooling",
                "gentle rain carries essence of evening's peaceful approach"
            ],
            'atmospheric': [
                "light late afternoon rain feels like gentle transition to evening",
                "soft precipitation creates sense of day peacefully winding down",
                "gentle rain makes evening approach feel contemplative and naturally paced"
            ]
        },
        
        'light_rain_dusk': {
            'visual': [
                "dusk light rain creates magical interplay with sunset's golden and purple hues",
                "gentle precipitation catches last light creating ethereal water jewelry",
                "soft rain transforms evening transition into impressionist masterpiece"
            ],
            'auditory': [
                "light rain provides gentle soundtrack to dusk's peaceful transition",
                "gentle precipitation creates soft rhythm for evening's contemplative approach",
                "soft droplets add peaceful quality to sunset's natural quieting"
            ],
            'olfactory': [
                "dusk rain brings cooling scent mixed with evening's approaching fragrances",
                "light precipitation releases earth aromas as day transitions to night",
                "gentle rain carries essence of peaceful evening transformation"
            ],
            'atmospheric': [
                "light dusk rain feels romantically peaceful and spiritually renewing",
                "soft precipitation creates sense of gentle transition from day to night",
                "gentle rain makes sunset feel contemplative and emotionally meaningful"
            ]
        },
        
        'light_rain_early_evening': {
            'visual': [
                "early evening light rain creates romantic atmosphere with artificial lights reflecting",
                "gentle precipitation adds intimate texture to nightlife's beginning",
                "soft rain transforms social energy into something more contemplative and cozy"
            ],
            'auditory': [
                "light rain provides peaceful backdrop to early evening's social sounds",
                "gentle precipitation creates soft rhythm beneath nightlife's energy",
                "soft droplets add intimate quality to evening's social atmosphere"
            ],
            'olfactory': [
                "early evening rain brings cooling scent mixed with restaurant and entertainment aromas",
                "light precipitation carries gentle earth essence blended with nightlife fragrances",
                "soft rain adds fresh quality to evening's complex aromatic mixture"
            ],
            'atmospheric': [
                "light early evening rain feels romantically intimate and socially cozy",
                "gentle precipitation creates sense of shared experience and communal warmth",
                "soft rain makes nightlife feel more contemplative and personally meaningful"
            ]
        },
        
        'light_rain_late_evening': {
            'visual': [
                "late evening light rain creates cinematic atmosphere with neon and street lights",
                "gentle precipitation adds romantic texture to night's established rhythm",
                "soft rain transforms late evening into contemplative water-washed scene"
            ],
            'auditory': [
                "light rain provides peaceful soundtrack to late evening's quieter energy",
                "gentle precipitation creates soft rhythm for night's contemplative progression",
                "soft droplets add meditative quality to evening's peaceful sounds"
            ],
            'olfactory': [
                "late evening rain brings cooling scent mixed with night's accumulated aromas",
                "light precipitation carries earth essence blended with evening's complex fragrances",
                "gentle rain adds clean quality to night's rich aromatic layers"
            ],
            'atmospheric': [
                "light late evening rain feels contemplatively romantic and spiritually peaceful",
                "soft precipitation creates sense of gentle introspection and personal renewal",
                "gentle rain makes night feel emotionally meaningful and deeply restorative"
            ]
        },
        
        'light_rain_night': {
            'visual': [
                "night light rain falls through sparse illumination creating isolated silver columns",
                "gentle precipitation adds peaceful texture to night's quiet landscape",
                "soft rain creates solitary beauty in established nighttime rhythm"
            ],
            'auditory': [
                "light rain provides primary soundtrack to night's contemplative quiet",
                "gentle precipitation creates meditative rhythm in darkness",
                "soft droplets become peaceful voice in night's spiritual stillness"
            ],
            'olfactory': [
                "night rain brings clean scent that sharpens air with peaceful clarity",
                "light precipitation carries earth essence concentrated by darkness",
                "gentle rain adds crystalline quality to night's atmospheric layers"
            ],
            'atmospheric': [
                "light night rain feels deeply contemplative and spiritually cleansing",
                "soft precipitation creates sense of peaceful solitude and inner renewal",
                "gentle rain makes night feel emotionally healing and personally transformative"
            ]
        },
        
        'light_rain_late_night': {
            'visual': [
                "late night light rain falls through minimal lighting creating sparse silver beauty",
                "gentle precipitation adds solitary texture to deep night's quiet landscape",
                "soft rain creates contemplative beauty in night's deepest hours"
            ],
            'auditory': [
                "light rain provides only soundtrack to late night's profound quiet",
                "gentle precipitation creates deeply meditative rhythm in solitude",
                "soft droplets become spiritual voice in deep night's contemplative silence"
            ],
            'olfactory': [
                "late night rain brings crystalline scent that purifies deep evening air",
                "light precipitation carries concentrated earth essence in darkness",
                "gentle rain adds spiritual clarity to night's atmospheric essence"
            ],
            'atmospheric': [
                "light late night rain feels profoundly peaceful and spiritually renewing",
                "soft precipitation creates sense of deep solitude and inner transformation",
                "gentle rain makes deep night feel emotionally healing and personally sacred"
            ]
        },
        
        # Complete foggy_rain combinations (moderate intensity)
        'foggy_rain_pre_dawn': {
            'visual': [
                "pre-dawn fog and rain create layered curtains of moisture in scattered light",
                "mist and precipitation combine to reduce world to ghostly water-soaked outlines",
                "foggy rain transforms pre-dawn into impressionist painting of gray and silver"
            ],
            'auditory': [
                "rain sounds muffled and directionless through thick pre-dawn mist",
                "fog absorbs precipitation sounds creating mysteriously intimate acoustics",
                "water and mist combine to create dreamy pre-dawn soundtrack"
            ],
            'olfactory': [
                "fog and rain create super-saturated pre-dawn air thick with moisture",
                "mist intensifies rain scents creating rich atmospheric layers before sunrise",
                "humid air feels thick enough to taste with water and night essence"
            ],
            'atmospheric': [
                "foggy pre-dawn rain creates sense of world suspended between states",
                "mist and precipitation make familiar spaces feel mysterious and otherworldly",
                "combination transforms ordinary pre-dawn into something magical and uncertain"
            ]
        },
        
        'foggy_rain_early_morning': {
            'visual': [
                "early morning fog and rain create dreamy backdrop to awakening activity",
                "mist and precipitation transform busy morning into watercolor impressions",
                "foggy rain reduces morning world to intimate sphere of water and shadow"
            ],
            'auditory': [
                "morning sounds become phantom whispers through fog and rain",
                "mist absorbs activity sounds while precipitation adds liquid rhythm",
                "foggy rain creates acoustically surreal morning environment"
            ],
            'olfactory': [
                "fog and rain intensify morning aromas into overwhelming sensory richness",
                "mist carries awakening scents in super-concentrated humid doses",
                "combination creates thick aromatic soup of morning and moisture"
            ],
            'atmospheric': [
                "foggy morning rain makes busy time feel mysteriously contemplative",
                "mist and precipitation create sense of being in different reality",
                "combination transforms productive morning into dreamlike experience"
            ]
        },
        
        'foggy_rain_late_morning': {
            'visual': [
                "late morning fog and rain create ethereal backdrop to peak activity",
                "mist and precipitation soften harsh edges of urban productivity",
                "foggy rain transforms busy late morning into something gentle and mysterious"
            ],
            'auditory': [
                "productive sounds become muffled whispers through fog and rain",
                "mist absorbs urban intensity while precipitation adds peaceful rhythm",
                "foggy rain creates contemplative soundtrack to normally harsh activity"
            ],
            'olfactory': [
                "fog and rain concentrate late morning aromas into rich atmospheric layers",
                "mist holds productive scents while precipitation adds earth essence",
                "combination creates complex aromatic mixture of activity and moisture"
            ],
            'atmospheric': [
                "foggy late morning rain makes peak time feel manageable and peaceful",
                "mist and precipitation create sense of protective cocoon around activity",
                "combination transforms harsh productivity into something more humane"
            ]
        },
        
        'foggy_rain_midday': {
            'visual': [
                "midday fog and rain provide blessed relief from harsh sun and intensity",
                "mist and precipitation create cooling gray world of gentle moisture",
                "foggy rain transforms oppressive midday into something soft and bearable"
            ],
            'auditory': [
                "midday sounds become softened and contained through fog and rain",
                "mist absorbs overwhelming intensity while precipitation cools acoustics",
                "foggy rain creates blessed acoustic relief from harsh peak energy"
            ],
            'olfactory': [
                "fog and rain cool heated midday air into refreshing moisture",
                "mist holds cooling scents while precipitation adds earth relief",
                "combination creates pleasant aromatic escape from midday intensity"
            ],
            'atmospheric': [
                "foggy midday rain feels like nature's air conditioning and peace",
                "mist and precipitation create sense of cooling grace during harsh time",
                "combination transforms oppressive midday into something gentle and humane"
            ]
        },
        
        'foggy_rain_early_afternoon': {
            'visual': [
                "early afternoon fog and rain create cooling gray world of gentle relief",
                "mist and precipitation soften afternoon heat into something more bearable",
                "foggy rain transforms sustained afternoon into contemplative water scene"
            ],
            'auditory': [
                "afternoon sounds become mellowed and peaceful through fog and rain",
                "mist absorbs heat intensity while precipitation adds cooling rhythm",
                "foggy rain creates refreshing acoustic backdrop to sustained activity"
            ],
            'olfactory': [
                "fog and rain cool afternoon air creating refreshing moisture layers",
                "mist holds cooling earth scents while precipitation adds clean essence",
                "combination creates pleasant aromatic relief from afternoon heat"
            ],
            'atmospheric': [
                "foggy early afternoon rain feels like cooling grace during warmth",
                "mist and precipitation create sense of refreshing respite from heat",
                "combination makes sustained afternoon feel more comfortable and peaceful"
            ]
        },
        
        'foggy_rain_late_afternoon': {
            'visual': [
                "late afternoon fog and rain create romantic atmosphere with golden light diffused",
                "mist and precipitation transform rush hour into impressionist masterpiece",
                "foggy rain makes evening approach feel mysterious and cinematically beautiful"
            ],
            'auditory': [
                "late afternoon sounds become intimate whispers through fog and rain",
                "mist absorbs harsh edges while precipitation adds contemplative rhythm",
                "foggy rain creates peaceful transition soundtrack to evening approach"
            ],
            'olfactory': [
                "fog and rain blend day's warmth with evening's approaching coolness",
                "mist holds accumulated scents while precipitation adds fresh earth essence",
                "combination creates rich aromatic transition from day to night"
            ],
            'atmospheric': [
                "foggy late afternoon rain feels romantically mysterious and peaceful",
                "mist and precipitation create sense of gentle transition to evening",
                "combination makes day's end feel contemplative and emotionally meaningful"
            ]
        },
        
        'foggy_rain_dusk': {
            'visual': [
                "dusk fog and rain create magical ethereal world of water and diffused light",
                "mist and precipitation transform sunset into impressionist masterpiece of moisture",
                "foggy rain makes evening transition feel otherworldly and romantically mysterious"
            ],
            'auditory': [
                "dusk sounds become phantom whispers floating through fog and rain",
                "mist creates acoustic mystery while precipitation adds gentle rhythm",
                "foggy rain transforms evening transition into dreamy water symphony"
            ],
            'olfactory': [
                "fog and rain create intoxicating mixture of evening transition scents",
                "mist intensifies dusk aromas while precipitation adds earth essence",
                "combination creates rich aromatic layers of day becoming night"
            ],
            'atmospheric': [
                "foggy dusk rain feels deeply romantic and spiritually mysterious",
                "mist and precipitation create sense of magical transition between worlds",
                "combination makes sunset feel otherworldly and emotionally profound"
            ]
        },
        
        'foggy_rain_early_evening': {
            'visual': [
                "early evening fog and rain create cinematic atmosphere with lights diffused",
                "mist and precipitation transform nightlife into romantic impressionist scene",
                "foggy rain makes social evening feel mysteriously intimate and cozy"
            ],
            'auditory': [
                "evening sounds become intimate whispers floating through fog and rain",
                "mist creates acoustic intimacy while precipitation adds peaceful rhythm",
                "foggy rain transforms social energy into contemplative water music"
            ],
            'olfactory': [
                "fog and rain intensify evening aromas into rich atmospheric cocktail",
                "mist holds restaurant scents while precipitation adds fresh earth essence",
                "combination creates intoxicating aromatic mixture of nightlife and moisture"
            ],
            'atmospheric': [
                "foggy early evening rain feels romantically intimate and mysteriously cozy",
                "mist and precipitation create sense of shared dreamy experience",
                "combination makes nightlife feel more contemplative and personally meaningful"
            ]
        },
        
        'foggy_rain_late_evening': {
            'visual': [
                "late evening fog and rain create noir landscape of mystery and romance",
                "mist and precipitation transform night into cinematic water-soaked beauty",
                "foggy rain makes late evening feel like stepping into atmospheric film"
            ],
            'auditory': [
                "late evening sounds become phantom voices floating through fog and rain",
                "mist creates acoustic mystery while precipitation adds meditative rhythm",
                "foggy rain transforms night into surreal water symphony of contemplation"
            ],
            'olfactory': [
                "fog and rain create overwhelming intensity of late evening scents",
                "mist holds night aromas while precipitation adds crystalline earth essence",
                "combination creates thick aromatic layers of mystery and moisture"
            ],
            'atmospheric': [
                "foggy late evening rain feels mysteriously romantic and spiritually profound",
                "mist and precipitation create sense of being in different reality",
                "combination makes night feel otherworldly and emotionally transformative"
            ]
        },
        
        'foggy_rain_night': {
            'visual': [
                "night fog and rain create world of phantom shapes and liquid shadows",
                "mist and precipitation transform darkness into impressionist water painting",
                "foggy rain makes night feel like floating through liquid dreams"
            ],
            'auditory': [
                "night sounds become disembodied spirits floating through fog and rain",
                "mist creates acoustic illusions while precipitation adds spiritual rhythm",
                "foggy rain transforms night into otherworldly water meditation"
            ],
            'olfactory': [
                "fog and rain create super-saturated night air thick with concentrated essence",
                "mist holds darkness scents while precipitation adds crystalline purity",
                "combination creates aromatic layers that shift like the fog itself"
            ],
            'atmospheric': [
                "foggy night rain feels deeply mystical and spiritually transformative",
                "mist and precipitation create sense of floating between realities",
                "combination makes night feel otherworldly and personally sacred"
            ]
        },
        
        'foggy_rain_late_night': {
            'visual': [
                "late night fog and rain create ethereal world of sparse light and moisture",
                "mist and precipitation transform deep night into impressionist water solitude",
                "foggy rain makes late night feel like drifting through liquid meditation"
            ],
            'auditory': [
                "late night sounds become spiritual whispers floating through fog and rain",
                "mist creates profound acoustic mystery while precipitation adds sacred rhythm",
                "foggy rain transforms deep night into mystical water prayer"
            ],
            'olfactory': [
                "fog and rain create spiritually saturated late night air thick with essence",
                "mist holds deep night scents while precipitation adds divine purity",
                "combination creates aromatic layers that feel sacred and transformative"
            ],
            'atmospheric': [
                "foggy late night rain feels profoundly mystical and spiritually renewing",
                "mist and precipitation create sense of floating in sacred space",
                "combination makes deep night feel otherworldly and personally healing"
            ]
        },
        
        # Complete windy combinations (mild intensity)
        'windy_early_morning': {
            'visual': [
                "early morning wind sets everything in motion as the day awakens",
                "gusts catch growing light making shadows dance and shift constantly",
                "wind transforms static morning into dynamic display of movement and energy"
            ],
            'auditory': [
                "morning wind creates symphony of whistles, rustles, and energetic movement",
                "gusts carry awakening sounds from distant places mixing familiar and foreign",
                "moving air adds energetic percussion to morning's productive chorus"
            ],
            'olfactory': [
                "early morning wind carries fresh mixture of awakening scents and aromas",
                "moving air brings complex combination of morning fragrances from far places",
                "breeze mixes warming air with cool night remnants creating dynamic blend"
            ],
            'atmospheric': [
                "windy early morning feels energetic and full of productive possibility",
                "moving air makes morning feel dynamic and alive with forward momentum",
                "gusts bring sense of world stirring to life with natural rhythm and energy"
            ]
        },
        
        'windy_late_morning': {
            'visual': [
                "late morning wind adds movement to peak activity and productivity",
                "gusts catch harsh light creating constantly shifting patterns and shadows",
                "wind makes busy late morning feel more dynamic and alive with motion"
            ],
            'auditory': [
                "late morning wind creates backdrop of movement beneath productive sounds",
                "gusts carry sounds of peak activity mixing nearby and distant energy",
                "moving air adds rhythmic percussion to late morning's busy symphony"
            ],
            'olfactory': [
                "late morning wind carries mixture of heated surfaces and productive aromas",
                "moving air brings complex blend of warming scents and industrial activity",
                "breeze prevents stagnation keeping productive air fresh and circulating"
            ],
            'atmospheric': [
                "windy late morning feels energetically productive and dynamically alive",
                "moving air makes peak activity feel more manageable and naturally paced",
                "gusts bring sense of productive energy flowing and circulating freely"
            ]
        },
        
        'windy_midday': {
            'visual': [
                "midday wind provides blessed relief from oppressive heat and stagnation",
                "gusts catch harsh sun creating movement that breaks up heat intensity",
                "wind transforms static oppressive midday into something more bearable and dynamic"
            ],
            'auditory': [
                "midday wind creates cooling soundtrack that cuts through peak intensity",
                "gusts carry sounds that break up overwhelming acoustic concentration",
                "moving air adds refreshing percussion to otherwise harsh midday cacophony"
            ],
            'olfactory': [
                "midday wind carries cooling relief that disperses concentrated heat aromas",
                "moving air breaks up stagnant heated scents bringing fresher combinations",
                "breeze provides olfactory relief from overwhelming midday intensity"
            ],
            'atmospheric': [
                "windy midday feels like blessed relief from oppressive heat and stagnation",
                "moving air makes harsh peak time feel more bearable and naturally cooled",
                "gusts bring sense of cooling grace that cuts through midday intensity"
            ]
        },
        
        'windy_early_afternoon': {
            'visual': [
                "early afternoon wind adds cooling movement to sustained heat and activity",
                "gusts catch warm light creating dynamic patterns that relieve harsh glare",
                "wind makes sustained afternoon feel more energetic and less oppressive"
            ],
            'auditory': [
                "early afternoon wind creates refreshing soundtrack beneath sustained energy",
                "gusts carry cooling sounds that balance afternoon's intense productivity",
                "moving air adds dynamic rhythm to sustained afternoon activity"
            ],
            'olfactory': [
                "early afternoon wind carries cooling scents that refresh heated atmosphere",
                "moving air circulates afternoon aromas preventing overwhelming concentration",
                "breeze brings dynamic mixture of cooling and warming scent combinations"
            ],
            'atmospheric': [
                "windy early afternoon feels refreshingly dynamic during sustained heat",
                "moving air makes continued productivity feel more comfortable and energetic",
                "gusts bring sense of cooling movement that sustains afternoon energy"
            ]
        },
        
        'windy_late_afternoon': {
            'visual': [
                "late afternoon wind catches golden light creating spectacular displays of movement",
                "gusts make rush hour energy feel more dynamic and cinematically beautiful",
                "wind transforms busy late afternoon into constantly shifting golden scene"
            ],
            'auditory': [
                "late afternoon wind creates dynamic soundtrack to evening's approach",
                "gusts carry sounds of day's end mixing productive energy with evening's call",
                "moving air adds energetic rhythm to late afternoon's transitional sounds"
            ],
            'olfactory': [
                "late afternoon wind carries mixture of day's warmth and evening's coolness",
                "moving air circulates complex scents of transition and approaching change",
                "breeze brings dynamic blend of accumulated day and approaching night aromas"
            ],
            'atmospheric': [
                "windy late afternoon feels energetically transitional and dynamically alive",
                "moving air makes evening approach feel naturally paced and energetic",
                "gusts bring sense of day flowing naturally toward night with dynamic rhythm"
            ]
        },
        
        'windy_dusk': {
            'visual': [
                "dusk wind sets sunset colors dancing in constantly shifting atmospheric display",
                "gusts make evening transition feel more dramatic and cinematically alive",
                "wind transforms static sunset into dynamic celebration of day's end"
            ],
            'auditory': [
                "dusk wind creates energetic soundtrack to evening's peaceful transition",
                "gusts carry sounds of day ending and night beginning in natural rhythm",
                "moving air adds dynamic percussion to sunset's contemplative chorus"
            ],
            'olfactory': [
                "dusk wind carries complex mixture of day's end and night's approach",
                "moving air circulates transitional scents creating rich aromatic flow",
                "breeze brings dynamic blend of cooling air and evening's emerging fragrances"
            ],
            'atmospheric': [
                "windy dusk feels energetically peaceful and dynamically contemplative",
                "moving air makes sunset feel more alive and naturally rhythmic",
                "gusts bring sense of transition flowing with natural energy and grace"
            ]
        },
        
        'windy_early_evening': {
            'visual': [
                "early evening wind makes artificial lights dance and flicker like living things",
                "gusts add dynamic movement to nightlife's beginning energy and social flow",
                "wind transforms static evening into constantly shifting display of life and light"
            ],
            'auditory': [
                "early evening wind creates dynamic soundtrack to nightlife's emerging energy",
                "gusts carry sounds of social activity mixing nearby voices with distant music",
                "moving air adds energetic rhythm to evening's social and entertainment sounds"
            ],
            'olfactory': [
                "early evening wind carries mixture of restaurant aromas and entertainment scents",
                "moving air circulates nightlife fragrances creating rich dynamic flow",
                "breeze brings complex blend of social scents and cooling evening air"
            ],
            'atmospheric': [
                "windy early evening feels socially energetic and dynamically alive",
                "moving air makes nightlife feel more vibrant and naturally flowing",
                "gusts bring sense of social energy circulating and connecting people naturally"
            ]
        },
        
        'windy_late_evening': {
            'visual': [
                "late evening wind adds movement to established night rhythm and illumination",
                "gusts make nightlife feel more dynamic and cinematically atmospheric",
                "wind transforms static night into constantly shifting display of shadow and light"
            ],
            'auditory': [
                "late evening wind creates contemplative soundtrack to night's progression",
                "gusts carry distant sounds mixing night voices with mysterious whispers",
                "moving air adds peaceful rhythm to late evening's contemplative sounds"
            ],
            'olfactory': [
                "late evening wind carries mixture of night aromas and cooling air",
                "moving air circulates evening scents creating rich atmospheric flow",
                "breeze brings dynamic blend of nightlife fragrances and natural evening essence"
            ],
            'atmospheric': [
                "windy late evening feels contemplatively dynamic and peacefully alive",
                "moving air makes night feel more vibrant and naturally rhythmic",
                "gusts bring sense of evening energy flowing with contemplative grace"
            ]
        },
        
        'windy_night': {
            'visual': [
                "night wind adds movement to darkness creating constantly shifting shadow patterns",
                "gusts make artificial lights dance against dark sky like moving stars",
                "wind transforms static night into dynamic display of movement and mystery"
            ],
            'auditory': [
                "night wind creates mysterious soundtrack to darkness and solitude",
                "gusts carry distant sounds mixing night whispers with unknown voices",
                "moving air adds contemplative rhythm to night's spiritual stillness"
            ],
            'olfactory': [
                "night wind carries mixture of darkness scents and cooling clarity",
                "moving air circulates night aromas creating rich atmospheric layers",
                "breeze brings dynamic blend of night essence and distant mysterious fragrances"
            ],
            'atmospheric': [
                "windy night feels mysteriously dynamic and spiritually alive",
                "moving air makes darkness feel more vibrant and naturally connected",
                "gusts bring sense of night energy flowing with mysterious grace and power"
            ]
        },
        
        'windy_late_night': {
            'visual': [
                "late night wind adds solitary movement to deep darkness and sparse light",
                "gusts make minimal illumination dance creating shifting patterns of isolation",
                "wind transforms static late night into contemplative display of movement and solitude"
            ],
            'auditory': [
                "late night wind creates meditative soundtrack to deep solitude and quiet",
                "gusts carry only essential sounds mixing whispers with profound silence",
                "moving air adds spiritual rhythm to late night's contemplative emptiness"
            ],
            'olfactory': [
                "late night wind carries crystalline scents and purifying clarity",
                "moving air circulates deep night essence creating rich solitary layers",
                "breeze brings spiritual blend of night purity and mysterious distant essence"
            ],
            'atmospheric': [
                "windy late night feels spiritually dynamic and profoundly contemplative",
                "moving air makes deep solitude feel more alive and naturally connected",
                "gusts bring sense of night energy flowing with sacred grace and profound peace"
            ]
        },
        
        # Complete fog combinations (moderate intensity)
        'fog_early_morning': {
            'visual': [
                "early morning fog creates ghostly backdrop to awakening activity",
                "thick mist transforms busy morning into intimate world of gray mystery",
                "fog reduces productive morning to arm's length visibility and shadowy shapes"
            ],
            'auditory': [
                "morning sounds become directionless whispers in moisture-heavy fog",
                "mist absorbs productive noises creating pockets of eerie silence and unexpected sound",
                "fog transforms busy morning into acoustically intimate and mysteriously quiet space"
            ],
            'olfactory': [
                "morning fog carries concentrated essence of awakening mixed with moisture",
                "mist intensifies productive scents creating rich atmospheric layers",
                "humid air holds complex mixture of morning aromas in fog's thick embrace"
            ],
            'atmospheric': [
                "early morning fog creates sense of productive isolation in familiar spaces",
                "mist makes busy morning feel mysteriously intimate and contemplatively quiet",
                "fog transforms ordinary productivity into dreamscape of possibility and mystery"
            ]
        },
        
        'fog_late_morning': {
            'visual': [
                "late morning fog creates ethereal backdrop to peak activity and energy",
                "thick mist transforms harsh productivity into gentle world of soft gray mystery",
                "fog reduces busy late morning to intimate sphere of visibility and shadowy productivity"
            ],
            'auditory': [
                "late morning sounds become muffled and contemplative in thick fog",
                "mist absorbs harsh productive noises creating naturally dampened acoustics",
                "fog transforms overwhelming activity into acoustically manageable and intimate space"
            ],
            'olfactory': [
                "late morning fog carries concentrated essence of productive activity mixed with moisture",
                "mist intensifies peak aromas creating rich but manageable atmospheric layers",
                "humid air holds complex mixture of productive scents in fog's softening embrace"
            ],
            'atmospheric': [
                "late morning fog creates sense of productive intimacy during peak activity",
                "mist makes harsh productivity feel mysteriously manageable and contemplatively peaceful",
                "fog transforms overwhelming late morning into dreamscape of focused possibility"
            ]
        },
        
        'fog_midday': {
            'visual': [
                "midday fog provides blessed relief from harsh sun and overwhelming intensity",
                "thick mist transforms oppressive peak time into gentle world of cooling gray",
                "fog reduces overwhelming midday to manageable sphere of soft visibility"
            ],
            'auditory': [
                "midday sounds become softened and bearable in cooling fog",
                "mist absorbs harsh peak noises creating blessed acoustic relief",
                "fog transforms overwhelming intensity into acoustically peaceful and manageable space"
            ],
            'olfactory': [
                "midday fog carries cooling moisture that refreshes overheated air",
                "mist moderates harsh peak aromas creating more pleasant atmospheric layers",
                "humid air provides cooling relief from overwhelming midday scent concentration"
            ],
            'atmospheric': [
                "midday fog creates sense of cooling relief during oppressive peak time",
                "mist makes harsh intensity feel mysteriously bearable and naturally cooled",
                "fog transforms oppressive midday into manageable dreamscape of cooling possibility"
            ]
        },
        
        'fog_early_afternoon': {
            'visual': [
                "early afternoon fog creates gentle backdrop to sustained activity and warmth",
                "thick mist transforms heated afternoon into soft world of cooling gray mystery",
                "fog reduces sustained intensity to intimate sphere of manageable visibility"
            ],
            'auditory': [
                "early afternoon sounds become mellowed and peaceful in gentle fog",
                "mist absorbs sustained noise creating naturally cooling acoustics",
                "fog transforms heated activity into acoustically comfortable and intimate space"
            ],
            'olfactory': [
                "early afternoon fog carries cooling moisture that refreshes heated atmosphere",
                "mist moderates warm aromas creating more pleasant and manageable layers",
                "humid air provides refreshing relief from sustained afternoon scent intensity"
            ],
            'atmospheric': [
                "early afternoon fog creates sense of cooling grace during sustained heat",
                "mist makes heated activity feel mysteriously comfortable and naturally moderated",
                "fog transforms intense afternoon into peaceful dreamscape of cooling possibility"
            ]
        },
        
        'fog_late_afternoon': {
            'visual': [
                "late afternoon fog creates romantic backdrop to golden hour and evening approach",
                "thick mist transforms rush hour energy into gentle world of diffused golden light",
                "fog reduces busy transition to intimate sphere of softened visibility and mystery"
            ],
            'auditory': [
                "late afternoon sounds become intimate whispers in romantic fog",
                "mist absorbs harsh transition noise creating naturally peaceful acoustics",
                "fog transforms busy evening approach into acoustically contemplative and gentle space"
            ],
            'olfactory': [
                "late afternoon fog carries mixture of day's warmth and approaching coolness",
                "mist holds transitional aromas creating rich but gentle atmospheric layers",
                "humid air blends accumulated day scents with evening's approaching essence"
            ],
            'atmospheric': [
                "late afternoon fog creates sense of romantic transition during evening approach",
                "mist makes busy day's end feel mysteriously peaceful and naturally contemplative",
                "fog transforms hectic transition into dreamscape of gentle possibility and grace"
            ]
        },
        
        'fog_dusk': {
            'visual': [
                "dusk fog creates magical backdrop to sunset and evening's peaceful transition",
                "thick mist transforms dramatic sunset into gentle world of diffused color mystery",
                "fog reduces evening transition to intimate sphere of softened light and shadow"
            ],
            'auditory': [
                "dusk sounds become mysterious whispers floating in ethereal fog",
                "mist absorbs transition noise creating naturally contemplative acoustics",
                "fog transforms evening approach into acoustically mystical and peaceful space"
            ],
            'olfactory': [
                "dusk fog carries mixture of day's end and night's approach in moisture layers",
                "mist holds transitional aromas creating rich and romantically mysterious atmosphere",
                "humid air blends cooling day essence with evening's emerging night fragrances"
            ],
            'atmospheric': [
                "dusk fog creates sense of mystical transition during sunset's peaceful passage",
                "mist makes evening approach feel mysteriously romantic and spiritually meaningful",
                "fog transforms ordinary sunset into dreamscape of magical possibility and wonder"
            ]
        },
        
        'fog_early_evening': {
            'visual': [
                "early evening fog creates intimate backdrop to nightlife and social energy",
                "thick mist transforms artificial lights into soft halos of diffused romantic glow",
                "fog reduces social evening to cozy sphere of intimate visibility and mystery"
            ],
            'auditory': [
                "early evening sounds become intimate whispers floating in social fog",
                "mist absorbs harsh social noise creating naturally cozy acoustics",
                "fog transforms nightlife energy into acoustically intimate and romantically mysterious space"
            ],
            'olfactory': [
                "early evening fog carries mixture of restaurant aromas and entertainment scents softly",
                "mist holds social fragrances creating rich but intimate atmospheric layers",
                "humid air blends nightlife essence with fog's mysteriously romantic moisture"
            ],
            'atmospheric': [
                "early evening fog creates sense of intimate social experience during nightlife",
                "mist makes social energy feel mysteriously cozy and romantically connected",
                "fog transforms ordinary nightlife into dreamscape of intimate possibility and warmth"
            ]
        },
        
        'fog_late_evening': {
            'visual': [
                "late evening fog creates mysterious backdrop to night's established rhythm",
                "thick mist transforms nightlife into gentle world of diffused illumination mystery",
                "fog reduces late evening to intimate sphere of contemplative visibility and shadow"
            ],
            'auditory': [
                "late evening sounds become phantom whispers floating in contemplative fog",
                "mist absorbs night noise creating naturally meditative acoustics",
                "fog transforms late evening into acoustically mystical and peacefully mysterious space"
            ],
            'olfactory': [
                "late evening fog carries mixture of night aromas and cooling moisture layers",
                "mist holds evening fragrances creating rich and contemplatively mysterious atmosphere",
                "humid air blends nightlife essence with fog's spiritually peaceful moisture"
            ],
            'atmospheric': [
                "late evening fog creates sense of contemplative mystery during night's progression",
                "mist makes night feel mysteriously peaceful and spiritually meaningful",
                "fog transforms ordinary late evening into dreamscape of contemplative possibility and grace"
            ]
        },
        
        'fog_late_night': {
            'visual': [
                "late night fog creates ethereal backdrop to deep solitude and sparse illumination",
                "thick mist transforms minimal lighting into soft world of mystical gray mystery",
                "fog reduces deep night to intimate sphere of spiritual visibility and profound shadow"
            ],
            'auditory': [
                "late night sounds become spiritual whispers floating in mystical fog",
                "mist absorbs minimal noise creating naturally sacred acoustics",
                "fog transforms deep night into acoustically spiritual and profoundly peaceful space"
            ],
            'olfactory': [
                "late night fog carries concentrated essence of deep night mixed with sacred moisture",
                "mist holds night's spiritual fragrances creating rich and mystically profound atmosphere",
                "humid air blends deep solitude essence with fog's spiritually transformative moisture"
            ],
            'atmospheric': [
                "late night fog creates sense of spiritual mystery during deep night's sacred solitude",
                "mist makes profound quiet feel mysteriously sacred and spiritually transformative",
                "fog transforms ordinary deep night into dreamscape of spiritual possibility and divine peace"
            ]
        },
        
        # Complete soft_snow combinations (moderate intensity)
        'soft_snow_dawn': {
            'visual': [
                "dawn soft snow creates magical winter backdrop to sunrise's gentle awakening",
                "gentle flakes transform morning preparation into soft world of pristine white beauty",
                "light snow reduces dawn activity to peaceful sphere of crystalline visibility"
            ],
            'auditory': [
                "dawn sounds become muffled whispers in soft snow's gentle falling",
                "snow absorbs morning noise creating naturally hushed winter acoustics",
                "gentle snowfall transforms dawn into acoustically peaceful and pristinely quiet space"
            ],
            'olfactory': [
                "dawn soft snow carries crisp winter essence mixed with morning's fresh awakening",
                "light flakes hold clean aromas creating pure and refreshingly winter atmospheric layers",
                "cold air blends dawn freshness with snow's pristinely pure and crystalline essence"
            ],
            'atmospheric': [
                "dawn soft snow creates sense of winter magic during morning's gentle awakening",
                "gentle flakes make morning preparation feel purely peaceful and naturally beautiful",
                "snow transforms ordinary dawn into pristine winterscape of magical possibility and grace"
            ]
        },
        
        'soft_snow_early_morning': {
            'visual': [
                "early morning soft snow creates peaceful winter backdrop to awakening productive activity",
                "gentle flakes transform busy morning into soft world of pristine white contemplation",
                "light snow reduces productive morning to manageable sphere of crystalline focus"
            ],
            'auditory': [
                "early morning sounds become softened whispers in gentle snow's peaceful falling",
                "snow absorbs productive noise creating naturally calming winter acoustics",
                "gentle snowfall transforms busy morning into acoustically peaceful and contemplatively quiet space"
            ],
            'olfactory': [
                "early morning soft snow carries fresh winter essence mixed with productive awakening",
                "light flakes hold clean aromas creating pure and refreshingly focused atmospheric layers",
                "cold air blends morning productivity with snow's pristinely calming and crystalline essence"
            ],
            'atmospheric': [
                "early morning soft snow creates sense of winter peace during productive awakening",
                "gentle flakes make busy morning feel purely manageable and naturally contemplative",
                "snow transforms hectic productivity into pristine winterscape of focused possibility and calm"
            ]
        },
        
        'soft_snow_late_morning': {
            'visual': [
                "late morning soft snow provides cooling relief from peak activity in pristine beauty",
                "gentle flakes transform intense productivity into soft world of crystalline tranquility",
                "light snow reduces overwhelming morning to peaceful sphere of white focus and calm"
            ],
            'auditory': [
                "late morning sounds become naturally muffled in soft snow's cooling presence",
                "snow absorbs harsh productive noise creating blessed winter acoustic relief",
                "gentle snowfall transforms overwhelming activity into acoustically manageable and peaceful space"
            ],
            'olfactory': [
                "late morning soft snow carries cooling winter essence that refreshes overheated atmosphere",
                "light flakes moderate intense aromas creating more pleasant and pristinely clean layers",
                "cold air provides crystalline relief from overwhelming productive scent concentration"
            ],
            'atmospheric': [
                "late morning soft snow creates sense of cooling winter grace during peak intensity",
                "gentle flakes make harsh productivity feel purely manageable and naturally peaceful",
                "snow transforms overwhelming late morning into pristine winterscape of cooling possibility"
            ]
        },
        
        'soft_snow_midday': {
            'visual': [
                "midday soft snow provides blessed cooling from harsh sun in pristine white beauty",
                "gentle flakes transform oppressive peak time into soft world of crystalline relief",
                "light snow reduces overwhelming midday to manageable sphere of peaceful white visibility"
            ],
            'auditory': [
                "midday sounds become softened and bearable in cooling snow's gentle presence",
                "snow absorbs harsh peak noises creating blessed winter acoustic relief",
                "gentle snowfall transforms oppressive intensity into acoustically peaceful and manageable space"
            ],
            'olfactory': [
                "midday soft snow carries cooling crystalline essence that refreshes overheated air",
                "light flakes moderate harsh peak aromas creating pristinely pleasant atmospheric layers",
                "cold air provides pure winter relief from overwhelming midday scent intensity"
            ],
            'atmospheric': [
                "midday soft snow creates sense of cooling winter blessing during oppressive heat",
                "gentle flakes make harsh intensity feel purely bearable and naturally cooled",
                "snow transforms oppressive midday into pristine winterscape of cooling possibility and peace"
            ]
        },
        
        'soft_snow_early_afternoon': {
            'visual': [
                "early afternoon soft snow creates gentle cooling backdrop to sustained activity",
                "gentle flakes transform heated afternoon into soft world of crystalline comfort",
                "light snow reduces sustained intensity to peaceful sphere of white tranquility"
            ],
            'auditory': [
                "early afternoon sounds become mellowed whispers in soft snow's cooling presence",
                "snow absorbs sustained noise creating naturally cooling winter acoustics",
                "gentle snowfall transforms heated activity into acoustically comfortable and peaceful space"
            ],
            'olfactory': [
                "early afternoon soft snow carries cooling crystalline essence that refreshes heated atmosphere",
                "light flakes moderate warm aromas creating pristinely pleasant and manageable layers",
                "cold air provides refreshing winter relief from sustained afternoon scent intensity"
            ],
            'atmospheric': [
                "early afternoon soft snow creates sense of cooling winter grace during sustained heat",
                "gentle flakes make heated activity feel purely comfortable and naturally moderated",
                "snow transforms intense afternoon into pristine winterscape of cooling possibility and calm"
            ]
        },
        
        'soft_snow_late_afternoon': {
            'visual': [
                "late afternoon soft snow creates romantic winter backdrop to golden hour and evening approach",
                "gentle flakes transform rush hour energy into soft world of crystalline golden light",
                "light snow reduces busy transition to peaceful sphere of pristine visibility and beauty"
            ],
            'auditory': [
                "late afternoon sounds become intimate winter whispers in soft snow's romantic presence",
                "snow absorbs harsh transition noise creating naturally peaceful winter acoustics",
                "gentle snowfall transforms busy evening approach into acoustically contemplative and serene space"
            ],
            'olfactory': [
                "late afternoon soft snow carries mixture of winter coolness and golden hour warmth",
                "light flakes hold transitional aromas creating pristinely rich atmospheric layers",
                "cold air blends accumulated day warmth with snow's romantically pure essence"
            ],
            'atmospheric': [
                "late afternoon soft snow creates sense of romantic winter transition during evening approach",
                "gentle flakes make busy day's end feel purely peaceful and naturally contemplative",
                "snow transforms hectic transition into pristine winterscape of romantic possibility and grace"
            ]
        },
        
        'soft_snow_dusk': {
            'visual': [
                "dusk soft snow creates magical winter backdrop to sunset and evening's peaceful transition",
                "gentle flakes transform dramatic sunset into soft world of crystalline color mystery",
                "light snow reduces evening transition to intimate sphere of pristine light and shadow"
            ],
            'auditory': [
                "dusk sounds become mystical winter whispers floating in soft snow's ethereal presence",
                "snow absorbs transition noise creating naturally contemplative winter acoustics",
                "gentle snowfall transforms evening approach into acoustically mystical and peaceful space"
            ],
            'olfactory': [
                "dusk soft snow carries mixture of winter coolness and night's approach in crystalline layers",
                "light flakes hold transitional aromas creating pristinely rich and romantically mysterious atmosphere",
                "cold air blends cooling day essence with snow's mystically pure evening fragrances"
            ],
            'atmospheric': [
                "dusk soft snow creates sense of mystical winter transition during sunset's peaceful passage",
                "gentle flakes make evening approach feel purely romantic and spiritually meaningful",
                "snow transforms ordinary sunset into pristine winterscape of magical possibility and wonder"
            ]
        },
        
        'soft_snow_early_evening': {
            'visual': [
                "early evening soft snow creates intimate winter backdrop to nightlife and social warmth",
                "gentle flakes transform artificial lights into soft halos of crystalline romantic glow",
                "light snow reduces social evening to cozy sphere of pristine visibility and beauty"
            ],
            'auditory': [
                "early evening sounds become intimate winter whispers floating in soft snow's cozy presence",
                "snow absorbs harsh social noise creating naturally cozy winter acoustics",
                "gentle snowfall transforms nightlife energy into acoustically intimate and romantically peaceful space"
            ],
            'olfactory': [
                "early evening soft snow carries mixture of winter air and entertainment scents gently",
                "light flakes hold social fragrances creating pristinely rich but intimate atmospheric layers",
                "cold air blends nightlife essence with snow's romantically pure moisture"
            ],
            'atmospheric': [
                "early evening soft snow creates sense of intimate winter social experience during nightlife",
                "gentle flakes make social energy feel purely cozy and romantically connected",
                "snow transforms ordinary nightlife into pristine winterscape of intimate possibility and warmth"
            ]
        },
        
        'soft_snow_pre_dawn': {
            'visual': [
                "pre-dawn soft snow creates peaceful winter backdrop to deepest night's pristine solitude",
                "gentle flakes transform sacred silence into soft world of crystalline white mystery",
                "light snow reduces profound quiet to serene sphere of pristine visibility and peaceful shadow"
            ],
            'auditory': [
                "pre-dawn sounds become whispered prayers in soft snow's sacred presence",
                "snow absorbs profound noise creating naturally hushed winter acoustics",
                "gentle snowfall transforms sacred silence into acoustically peaceful and pristinely quiet space"
            ],
            'olfactory': [
                "pre-dawn soft snow carries pure winter essence mixed with night's crystalline awakening",
                "light flakes hold sacred aromas creating pristinely pure atmospheric layers",
                "cold air blends deep solitude with snow's sacredly pure and crystalline essence"
            ],
            'atmospheric': [
                "pre-dawn soft snow creates sense of winter peace during night's pristine solitude",
                "gentle flakes make sacred silence feel purely peaceful and naturally beautiful",
                "snow transforms ordinary pre-dawn into pristine winterscape of sacred possibility and grace"
            ]
        },
        
        'soft_snow_late_evening': {
            'visual': [
                "late evening soft snow creates peaceful winter backdrop to night's established crystalline rhythm",
                "gentle flakes transform nightlife into soft world of pristine white illumination beauty",
                "light snow reduces late evening to serene sphere of crystalline visibility and peaceful shadow"
            ],
            'auditory': [
                "late evening sounds become peaceful whispers floating in soft snow's contemplative presence",
                "snow absorbs night noise creating naturally meditative winter acoustics",
                "gentle snowfall transforms late evening into acoustically peaceful and pristinely contemplative space"
            ],
            'olfactory': [
                "late evening soft snow carries mixture of winter peace and cooling crystalline night layers",
                "light flakes hold evening fragrances creating pristinely rich and peacefully contemplative atmosphere",
                "cold air blends nightlife essence with snow's peacefully pure and crystallinely contemplative energy"
            ],
            'atmospheric': [
                "late evening soft snow creates sense of winter contemplation during night's peaceful progression",
                "gentle flakes make night feel pristinely peaceful and spiritually meaningful",
                "snow transforms ordinary late evening into pristine winterscape of contemplative possibility and grace"
            ]
        },
        
        'soft_snow_late_night': {
            'visual': [
                "late night soft snow creates sacred winter backdrop to deep solitude and pristine illumination",
                "gentle flakes transform minimal lighting into soft world of crystalline white mystical beauty",
                "light snow reduces deep night to spiritually serene sphere of pristine visibility and sacred shadow"
            ],
            'auditory': [
                "late night sounds become sacred whispers floating in soft snow's mystical presence",
                "snow absorbs minimal noise creating naturally sacred winter acoustics",
                "gentle snowfall transforms deep night into acoustically spiritual and pristinely profound space"
            ],
            'olfactory': [
                "late night soft snow carries concentrated winter essence mixed with sacred crystalline night air",
                "light flakes hold night's spiritual fragrances creating pristinely pure and mystically profound atmosphere",
                "cold air blends deep solitude essence with snow's spiritually transformative and crystallinely pure energy"
            ],
            'atmospheric': [
                "late night soft snow creates sense of sacred winter mystery during deep night's pristine solitude",
                "gentle flakes make profound quiet feel pristinely sacred and spiritually transformative",
                "snow transforms ordinary deep night into pristine winterscape of sacred possibility and divine peace"
            ]
        },
        
        # Complete dry_thunderstorm combinations (intense weather)
        'dry_thunderstorm_pre_dawn': {
            'visual': [
                "pre-dawn dry thunderstorm creates dramatic electric backdrop to deepest night's power",
                "lightning without rain transforms sacred solitude into intense world of stark electrical drama",
                "dry storm reduces profound quiet to charged sphere of brilliant flashes and deep shadow"
            ],
            'auditory': [
                "pre-dawn thunder becomes cosmic percussion echoing through dry storm's electric presence",
                "storm without rain creates naturally amplified acoustic drama in sacred silence",
                "dry thunderstorm transforms profound quiet into acoustically powerful and electrically charged space"
            ],
            'olfactory': [
                "pre-dawn dry thunderstorm carries intense ozone essence mixed with charged night air",
                "lightning without rain holds electric aromas creating powerfully charged atmospheric layers",
                "dry air intensifies storm essence with electrically pure and dramatically ozone-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn dry thunderstorm creates sense of cosmic electric drama during deepest night's power",
                "lightning without rain makes sacred solitude feel intensely charged and dramatically meaningful",
                "dry storm transforms ordinary pre-dawn into electrically charged landscape of cosmic possibility"
            ]
        },
        
        'dry_thunderstorm_dawn': {
            'visual': [
                "dawn dry thunderstorm creates spectacular electric backdrop to sunrise's dramatic awakening",
                "lightning without rain transforms morning preparation into intense world of charged electrical beauty",
                "dry storm reduces dawn activity to electrified sphere of brilliant visibility and stark contrast"
            ],
            'auditory': [
                "dawn thunder becomes dramatic percussion echoing through dry storm's powerful presence",
                "storm without rain amplifies morning sounds creating naturally intense acoustic drama",
                "dry thunderstorm transforms dawn into acoustically powerful and electrically dramatic space"
            ],
            'olfactory': [
                "dawn dry thunderstorm carries fresh ozone essence mixed with morning's charged awakening",
                "lightning without rain holds clean electric aromas creating powerfully fresh atmospheric layers",
                "dry air blends dawn freshness with storm's intensely pure and dramatically ozone-rich essence"
            ],
            'atmospheric': [
                "dawn dry thunderstorm creates sense of electric drama during morning's powerful awakening",
                "lightning without rain makes morning preparation feel intensely energized and dramatically beautiful",
                "dry storm transforms ordinary dawn into electrically charged landscape of powerful possibility"
            ]
        },
        
        'dry_thunderstorm_early_morning': {
            'visual': [
                "early morning dry thunderstorm creates intense electric backdrop to productive awakening",
                "lightning without rain transforms busy morning into charged world of electrical productivity",
                "dry storm reduces productive morning to energized sphere of brilliant focus and electric intensity"
            ],
            'auditory': [
                "early morning thunder becomes motivating percussion echoing through dry storm's energizing presence",
                "storm without rain amplifies productive sounds creating naturally intense acoustic energy",
                "dry thunderstorm transforms busy morning into acoustically powerful and electrically energizing space"
            ],
            'olfactory': [
                "early morning dry thunderstorm carries charged ozone essence mixed with productive awakening energy",
                "lightning without rain holds electric aromas creating powerfully energizing atmospheric layers",
                "dry air blends morning productivity with storm's intensely pure and dramatically energizing essence"
            ],
            'atmospheric': [
                "early morning dry thunderstorm creates sense of electric energy during productive awakening",
                "lightning without rain makes busy morning feel intensely motivated and dramatically productive",
                "dry storm transforms hectic productivity into electrically charged landscape of energizing possibility"
            ]
        },
        
        'dry_thunderstorm_late_morning': {
            'visual': [
                "late morning dry thunderstorm provides dramatic electric intensity during peak productive activity",
                "lightning without rain transforms overwhelming productivity into charged world of electrical focus",
                "dry storm reduces peak morning to intensely energized sphere of brilliant concentration"
            ],
            'auditory': [
                "late morning thunder becomes powerful percussion amplifying dry storm's intense presence",
                "storm without rain intensifies productive noise creating dramatically charged acoustic energy",
                "dry thunderstorm transforms overwhelming activity into acoustically powerful and electrically intense space"
            ],
            'olfactory': [
                "late morning dry thunderstorm carries intense ozone essence that electrifies overcharged atmosphere",
                "lightning without rain amplifies productive aromas creating powerfully charged atmospheric layers",
                "dry air provides electric intensity to overwhelming productive scent concentration"
            ],
            'atmospheric': [
                "late morning dry thunderstorm creates sense of electric power during peak intensity",
                "lightning without rain makes harsh productivity feel intensely charged and dramatically powerful",
                "dry storm transforms overwhelming late morning into electrically charged landscape of intense possibility"
            ]
        },
        
        'dry_thunderstorm_midday': {
            'visual': [
                "midday dry thunderstorm creates spectacular electric drama during oppressive peak intensity",
                "lightning without rain transforms harsh sun into charged world of electrical brilliance",
                "dry storm reduces overwhelming midday to dramatically energized sphere of electric visibility"
            ],
            'auditory': [
                "midday thunder becomes overwhelming percussion echoing through dry storm's intense presence",
                "storm without rain amplifies harsh peak noises creating dramatically powerful acoustic drama",
                "dry thunderstorm transforms oppressive intensity into acoustically overwhelming and electrically charged space"
            ],
            'olfactory': [
                "midday dry thunderstorm carries overwhelming ozone essence that intensifies overheated air",
                "lightning without rain amplifies harsh peak aromas creating powerfully overwhelming atmospheric layers",
                "dry air provides electric intensity to oppressive midday scent concentration"
            ],
            'atmospheric': [
                "midday dry thunderstorm creates sense of overwhelming electric drama during oppressive peak",
                "lightning without rain makes harsh intensity feel dramatically charged and overwhelmingly powerful",
                "dry storm transforms oppressive midday into electrically charged landscape of overwhelming possibility"
            ]
        },
        
        'dry_thunderstorm_early_afternoon': {
            'visual': [
                "early afternoon dry thunderstorm creates powerful electric backdrop to sustained intensive activity",
                "lightning without rain transforms heated afternoon into charged world of electrical energy",
                "dry storm reduces sustained intensity to dramatically energized sphere of electric focus"
            ],
            'auditory': [
                "early afternoon thunder becomes energizing percussion echoing through dry storm's powerful presence",
                "storm without rain amplifies sustained noise creating naturally intense acoustic energy",
                "dry thunderstorm transforms heated activity into acoustically powerful and electrically energizing space"
            ],
            'olfactory': [
                "early afternoon dry thunderstorm carries charged ozone essence that energizes heated atmosphere",
                "lightning without rain intensifies warm aromas creating powerfully energizing atmospheric layers",
                "dry air provides electric energy to sustained afternoon scent intensity"
            ],
            'atmospheric': [
                "early afternoon dry thunderstorm creates sense of electric power during sustained intensity",
                "lightning without rain makes heated activity feel dramatically energized and naturally powerful",
                "dry storm transforms intense afternoon into electrically charged landscape of powerful possibility"
            ]
        },
        
        'dry_thunderstorm_late_afternoon': {
            'visual': [
                "late afternoon dry thunderstorm creates dramatic electric backdrop to golden hour transition",
                "lightning without rain transforms rush hour energy into charged world of electrical golden drama",
                "dry storm reduces busy transition to intensely energized sphere of electric visibility and power"
            ],
            'auditory': [
                "late afternoon thunder becomes dramatic percussion echoing through dry storm's transitional presence",
                "storm without rain amplifies harsh transition noise creating naturally powerful acoustic drama",
                "dry thunderstorm transforms busy evening approach into acoustically intense and electrically dramatic space"
            ],
            'olfactory': [
                "late afternoon dry thunderstorm carries mixture of electric energy and transitional intensity",
                "lightning without rain holds powerful aromas creating dramatically charged atmospheric layers",
                "dry air blends accumulated day heat with storm's intensely pure and dramatically electric essence"
            ],
            'atmospheric': [
                "late afternoon dry thunderstorm creates sense of dramatic electric transition during evening approach",
                "lightning without rain makes busy day's end feel intensely powerful and dramatically charged",
                "dry storm transforms hectic transition into electrically charged landscape of dramatic possibility"
            ]
        },
        
        'dry_thunderstorm_dusk': {
            'visual': [
                "dusk dry thunderstorm creates spectacular electric backdrop to sunset and evening's powerful transition",
                "lightning without rain transforms dramatic sunset into charged world of electrical color drama",
                "dry storm reduces evening transition to intensely dramatic sphere of electric light and shadow"
            ],
            'auditory': [
                "dusk thunder becomes mystical percussion floating through dry storm's ethereal electric presence",
                "storm without rain amplifies transition noise creating naturally contemplative acoustic drama",
                "dry thunderstorm transforms evening approach into acoustically mystical and electrically powerful space"
            ],
            'olfactory': [
                "dusk dry thunderstorm carries mixture of electric energy and night's approach in charged layers",
                "lightning without rain holds transitional aromas creating powerfully charged and dramatically mysterious atmosphere",
                "dry air blends cooling day essence with storm's mystically pure and electrically dramatic fragrances"
            ],
            'atmospheric': [
                "dusk dry thunderstorm creates sense of mystical electric transition during sunset's powerful passage",
                "lightning without rain makes evening approach feel dramatically charged and spiritually meaningful",
                "dry storm transforms ordinary sunset into electrically charged landscape of mystical possibility"
            ]
        },
        
        'dry_thunderstorm_early_evening': {
            'visual': [
                "early evening dry thunderstorm creates intense electric backdrop to nightlife and social energy",
                "lightning without rain transforms artificial lights into charged halos of electrical dramatic glow",
                "dry storm reduces social evening to energized sphere of electric visibility and power"
            ],
            'auditory': [
                "early evening thunder becomes energizing percussion floating through dry storm's social presence",
                "storm without rain amplifies social noise creating naturally intense acoustic energy",
                "dry thunderstorm transforms nightlife energy into acoustically powerful and electrically energizing space"
            ],
            'olfactory': [
                "early evening dry thunderstorm carries mixture of electric air and entertainment energy intensely",
                "lightning without rain holds social fragrances creating powerfully charged atmospheric layers",
                "dry air blends nightlife essence with storm's dramatically pure electric energy"
            ],
            'atmospheric': [
                "early evening dry thunderstorm creates sense of intense electric social experience during nightlife",
                "lightning without rain makes social energy feel dramatically charged and powerfully connected",
                "dry storm transforms ordinary nightlife into electrically charged landscape of intense possibility"
            ]
        },
        
        'dry_thunderstorm_late_evening': {
            'visual': [
                "late evening dry thunderstorm creates powerful electric backdrop to night's established rhythm",
                "lightning without rain transforms nightlife into charged world of electrical illumination drama",
                "dry storm reduces late evening to dramatically energized sphere of electric visibility and shadow"
            ],
            'auditory': [
                "late evening thunder becomes powerful percussion echoing through dry storm's intense presence",
                "storm without rain amplifies night noise creating naturally dramatic acoustic energy",
                "dry thunderstorm transforms late evening into acoustically powerful and electrically intense space"
            ],
            'olfactory': [
                "late evening dry thunderstorm carries mixture of electric energy and cooling night layers",
                "lightning without rain holds evening fragrances creating powerfully charged and dramatically intense atmosphere",
                "dry air blends nightlife essence with storm's dramatically pure and electrically powerful energy"
            ],
            'atmospheric': [
                "late evening dry thunderstorm creates sense of electric drama during night's powerful progression",
                "lightning without rain makes night feel dramatically charged and spiritually meaningful",
                "dry storm transforms ordinary late evening into electrically charged landscape of powerful possibility"
            ]
        },
        
        'dry_thunderstorm_late_night': {
            'visual': [
                "late night dry thunderstorm creates cosmic electric backdrop to deep solitude and sparse illumination",
                "lightning without rain transforms minimal lighting into charged world of electrical mystical drama",
                "dry storm reduces deep night to intensely spiritual sphere of electric visibility and profound shadow"
            ],
            'auditory': [
                "late night thunder becomes cosmic percussion echoing through dry storm's mystical presence",
                "storm without rain amplifies minimal noise creating naturally sacred acoustic drama",
                "dry thunderstorm transforms deep night into acoustically spiritual and electrically profound space"
            ],
            'olfactory': [
                "late night dry thunderstorm carries concentrated electric essence mixed with sacred charged night air",
                "lightning without rain holds night's spiritual fragrances creating powerfully charged and mystically profound atmosphere",
                "dry air blends deep solitude essence with storm's spiritually transformative and electrically pure energy"
            ],
            'atmospheric': [
                "late night dry thunderstorm creates sense of cosmic electric mystery during deep night's sacred solitude",
                "lightning without rain makes profound quiet feel dramatically charged and spiritually transformative",
                "dry storm transforms ordinary deep night into electrically charged landscape of cosmic possibility"
            ]
        },
        
        'dry_thunderstorm_night': {
            'visual': [
                "night dry thunderstorm creates powerful electric backdrop to established darkness and rhythmic illumination",
                "lightning without rain transforms night rhythm into charged world of electrical mystical energy",
                "dry storm reduces settled night to dramatically energized sphere of electric visibility and charged shadow"
            ],
            'auditory': [
                "night thunder becomes rhythmic percussion echoing through dry storm's established presence",
                "storm without rain amplifies night sounds creating naturally powerful acoustic electrical energy",
                "dry thunderstorm transforms settled night into acoustically powerful and electrically rhythmic space"
            ],
            'olfactory': [
                "night dry thunderstorm carries established electric essence mixed with rhythmic charged night air",
                "lightning without rain holds night's established fragrances creating powerfully charged and rhythmically meaningful atmosphere",
                "dry air blends settled darkness essence with storm's rhythmically pure and electrically established energy"
            ],
            'atmospheric': [
                "night dry thunderstorm creates sense of established electric rhythm during night's powerful progression",
                "lightning without rain makes settled darkness feel dramatically charged and rhythmically meaningful",
                "dry storm transforms ordinary night into electrically charged landscape of rhythmic possibility and power"
            ]
        },
        
        # Complete rainy_thunderstorm combinations (intense weather)
        'rainy_thunderstorm_pre_dawn': {
            'visual': [
                "pre-dawn rainy thunderstorm creates wild electric backdrop to deepest night's powerful drama",
                "lightning and rain transform sacred solitude into intense world of electrical water fury",
                "stormy downpour reduces profound quiet to charged sphere of brilliant flashes through sheets of rain"
            ],
            'auditory': [
                "pre-dawn thunder becomes cosmic percussion mixing with rain's intense drumming presence",
                "storm with rain creates naturally amplified acoustic chaos in sacred stormy silence",
                "rainy thunderstorm transforms profound quiet into acoustically overwhelming and electrically charged space"
            ],
            'olfactory': [
                "pre-dawn rainy thunderstorm carries intense ozone essence mixed with charged wet night air",
                "lightning with rain holds electric water aromas creating powerfully saturated atmospheric layers",
                "wet air intensifies storm essence with electrically pure and dramatically rain-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn rainy thunderstorm creates sense of cosmic electric chaos during deepest night's fury",
                "lightning with rain makes sacred solitude feel intensely charged and dramatically overwhelming",
                "stormy rain transforms ordinary pre-dawn into electrically charged waterscape of cosmic turbulence"
            ]
        },
        
        'rainy_thunderstorm_dawn': {
            'visual': [
                "dawn rainy thunderstorm creates spectacular electric water backdrop to sunrise's dramatic awakening",
                "lightning and rain transform morning preparation into intense world of charged electrical water beauty",
                "stormy downpour reduces dawn activity to electrified sphere of brilliant visibility through driving rain"
            ],
            'auditory': [
                "dawn thunder becomes dramatic percussion mixing with rain's powerful drumming presence",
                "storm with rain amplifies morning sounds creating naturally intense acoustic water drama",
                "rainy thunderstorm transforms dawn into acoustically overwhelming and electrically dramatic space"
            ],
            'olfactory': [
                "dawn rainy thunderstorm carries fresh ozone essence mixed with morning's charged wet awakening",
                "lightning with rain holds clean electric water aromas creating powerfully fresh saturated atmospheric layers",
                "wet air blends dawn freshness with storm's intensely pure and dramatically rain-rich essence"
            ],
            'atmospheric': [
                "dawn rainy thunderstorm creates sense of electric water drama during morning's powerful awakening",
                "lightning with rain makes morning preparation feel intensely energized and dramatically beautiful",
                "stormy rain transforms ordinary dawn into electrically charged waterscape of powerful turbulence"
            ]
        },
        
        'rainy_thunderstorm_early_morning': {
            'visual': [
                "early morning rainy thunderstorm creates intense electric water backdrop to productive awakening",
                "lightning and rain transform busy morning into charged world of electrical water productivity",
                "stormy downpour reduces productive morning to energized sphere of brilliant focus through driving rain"
            ],
            'auditory': [
                "early morning thunder becomes motivating percussion mixing with rain's energizing drumming presence",
                "storm with rain amplifies productive sounds creating naturally intense acoustic water energy",
                "rainy thunderstorm transforms busy morning into acoustically overwhelming and electrically energizing space"
            ],
            'olfactory': [
                "early morning rainy thunderstorm carries charged ozone essence mixed with productive wet awakening energy",
                "lightning with rain holds electric water aromas creating powerfully energizing saturated atmospheric layers",
                "wet air blends morning productivity with storm's intensely pure and dramatically energizing rain essence"
            ],
            'atmospheric': [
                "early morning rainy thunderstorm creates sense of electric water energy during productive awakening",
                "lightning with rain makes busy morning feel intensely motivated and dramatically productive",
                "stormy rain transforms hectic productivity into electrically charged waterscape of energizing turbulence"
            ]
        },
        
        'rainy_thunderstorm_late_morning': {
            'visual': [
                "late morning rainy thunderstorm provides dramatic electric water intensity during peak activity",
                "lightning and rain transform overwhelming productivity into charged world of electrical water focus",
                "stormy downpour reduces peak morning to intensely energized sphere of brilliant concentration through sheets"
            ],
            'auditory': [
                "late morning thunder becomes powerful percussion amplifying rain's intense drumming presence",
                "storm with rain intensifies productive noise creating dramatically charged acoustic water energy",
                "rainy thunderstorm transforms overwhelming activity into acoustically chaotic and electrically intense space"
            ],
            'olfactory': [
                "late morning rainy thunderstorm carries intense ozone essence that electrifies overcharged wet atmosphere",
                "lightning with rain amplifies productive aromas creating powerfully charged saturated atmospheric layers",
                "wet air provides electric intensity to overwhelming productive scent concentration through rain"
            ],
            'atmospheric': [
                "late morning rainy thunderstorm creates sense of electric water chaos during peak intensity",
                "lightning with rain makes harsh productivity feel intensely charged and dramatically overwhelming",
                "stormy rain transforms overwhelming late morning into electrically charged waterscape of intense turbulence"
            ]
        },
        
        'rainy_thunderstorm_midday': {
            'visual': [
                "midday rainy thunderstorm creates spectacular electric water drama during oppressive peak intensity",
                "lightning and rain transform harsh sun into charged world of electrical water brilliance",
                "stormy downpour reduces overwhelming midday to dramatically energized sphere of electric visibility through torrents"
            ],
            'auditory': [
                "midday thunder becomes overwhelming percussion mixing with rain's chaotic drumming presence",
                "storm with rain amplifies harsh peak noises creating dramatically powerful acoustic water chaos",
                "rainy thunderstorm transforms oppressive intensity into acoustically overwhelming and electrically charged space"
            ],
            'olfactory': [
                "midday rainy thunderstorm carries overwhelming ozone essence that intensifies overheated wet air",
                "lightning with rain amplifies harsh peak aromas creating powerfully overwhelming saturated atmospheric layers",
                "wet air provides electric intensity to oppressive midday scent concentration through driving rain"
            ],
            'atmospheric': [
                "midday rainy thunderstorm creates sense of overwhelming electric water chaos during oppressive peak",
                "lightning with rain makes harsh intensity feel dramatically charged and overwhelmingly powerful",
                "stormy rain transforms oppressive midday into electrically charged waterscape of overwhelming turbulence"
            ]
        },
        
        'rainy_thunderstorm_early_afternoon': {
            'visual': [
                "early afternoon rainy thunderstorm creates powerful electric water backdrop to sustained activity",
                "lightning and rain transform heated afternoon into charged world of electrical water energy",
                "stormy downpour reduces sustained intensity to dramatically energized sphere of electric focus through rain"
            ],
            'auditory': [
                "early afternoon thunder becomes energizing percussion mixing with rain's powerful drumming presence",
                "storm with rain amplifies sustained noise creating naturally intense acoustic water energy",
                "rainy thunderstorm transforms heated activity into acoustically powerful and electrically energizing space"
            ],
            'olfactory': [
                "early afternoon rainy thunderstorm carries charged ozone essence that energizes heated wet atmosphere",
                "lightning with rain intensifies warm aromas creating powerfully energizing saturated atmospheric layers",
                "wet air provides electric energy to sustained afternoon scent intensity through refreshing rain"
            ],
            'atmospheric': [
                "early afternoon rainy thunderstorm creates sense of electric water power during sustained intensity",
                "lightning with rain makes heated activity feel dramatically energized and naturally powerful",
                "stormy rain transforms intense afternoon into electrically charged waterscape of powerful turbulence"
            ]
        },
        
        'rainy_thunderstorm_late_afternoon': {
            'visual': [
                "late afternoon rainy thunderstorm creates dramatic electric water backdrop to golden hour transition",
                "lightning and rain transform rush hour energy into charged world of electrical water golden drama",
                "stormy downpour reduces busy transition to intensely energized sphere of electric visibility through sheets"
            ],
            'auditory': [
                "late afternoon thunder becomes dramatic percussion mixing with rain's transitional drumming presence",
                "storm with rain amplifies harsh transition noise creating naturally powerful acoustic water drama",
                "rainy thunderstorm transforms busy evening approach into acoustically intense and electrically dramatic space"
            ],
            'olfactory': [
                "late afternoon rainy thunderstorm carries mixture of electric water energy and transitional intensity",
                "lightning with rain holds powerful water aromas creating dramatically charged saturated atmospheric layers",
                "wet air blends accumulated day heat with storm's intensely pure and dramatically electric rain essence"
            ],
            'atmospheric': [
                "late afternoon rainy thunderstorm creates sense of dramatic electric water transition during evening approach",
                "lightning with rain makes busy day's end feel intensely powerful and dramatically charged",
                "stormy rain transforms hectic transition into electrically charged waterscape of dramatic turbulence"
            ]
        },
        
        'rainy_thunderstorm_dusk': {
            'visual': [
                "dusk rainy thunderstorm creates spectacular electric water backdrop to sunset's powerful transition",
                "lightning and rain transform dramatic sunset into charged world of electrical water color drama",
                "stormy downpour reduces evening transition to intensely dramatic sphere of electric light through rain"
            ],
            'auditory': [
                "dusk thunder becomes mystical percussion floating through rain's ethereal electric drumming presence",
                "storm with rain amplifies transition noise creating naturally contemplative acoustic water drama",
                "rainy thunderstorm transforms evening approach into acoustically mystical and electrically powerful space"
            ],
            'olfactory': [
                "dusk rainy thunderstorm carries mixture of electric water energy and night's approach in charged wet layers",
                "lightning with rain holds transitional water aromas creating powerfully charged and dramatically mysterious atmosphere",
                "wet air blends cooling day essence with storm's mystically pure and electrically dramatic rain fragrances"
            ],
            'atmospheric': [
                "dusk rainy thunderstorm creates sense of mystical electric water transition during sunset's powerful passage",
                "lightning with rain makes evening approach feel dramatically charged and spiritually meaningful",
                "stormy rain transforms ordinary sunset into electrically charged waterscape of mystical turbulence"
            ]
        },
        
        'rainy_thunderstorm_early_evening': {
            'visual': [
                "early evening rainy thunderstorm creates intense electric water backdrop to nightlife and social energy",
                "lightning and rain transform artificial lights into charged halos of electrical water dramatic glow",
                "stormy downpour reduces social evening to energized sphere of electric visibility through driving rain"
            ],
            'auditory': [
                "early evening thunder becomes energizing percussion floating through rain's social drumming presence",
                "storm with rain amplifies social noise creating naturally intense acoustic water energy",
                "rainy thunderstorm transforms nightlife energy into acoustically powerful and electrically energizing space"
            ],
            'olfactory': [
                "early evening rainy thunderstorm carries mixture of electric water air and entertainment energy intensely",
                "lightning with rain holds social fragrances creating powerfully charged saturated atmospheric layers",
                "wet air blends nightlife essence with storm's dramatically pure electric rain energy"
            ],
            'atmospheric': [
                "early evening rainy thunderstorm creates sense of intense electric water social experience during nightlife",
                "lightning with rain makes social energy feel dramatically charged and powerfully connected",
                "stormy rain transforms ordinary nightlife into electrically charged waterscape of intense turbulence"
            ]
        },
        
        'rainy_thunderstorm_late_evening': {
            'visual': [
                "late evening rainy thunderstorm creates powerful electric water backdrop to night's established rhythm",
                "lightning and rain transform nightlife into charged world of electrical water illumination drama",
                "stormy downpour reduces late evening to dramatically energized sphere of electric visibility through sheets"
            ],
            'auditory': [
                "late evening thunder becomes powerful percussion mixing with rain's intense drumming presence",
                "storm with rain amplifies night noise creating naturally dramatic acoustic water energy",
                "rainy thunderstorm transforms late evening into acoustically powerful and electrically intense space"
            ],
            'olfactory': [
                "late evening rainy thunderstorm carries mixture of electric water energy and cooling wet night layers",
                "lightning with rain holds evening fragrances creating powerfully charged and dramatically intense saturated atmosphere",
                "wet air blends nightlife essence with storm's dramatically pure and electrically powerful rain energy"
            ],
            'atmospheric': [
                "late evening rainy thunderstorm creates sense of electric water drama during night's powerful progression",
                "lightning with rain makes night feel dramatically charged and spiritually meaningful",
                "stormy rain transforms ordinary late evening into electrically charged waterscape of powerful turbulence"
            ]
        },
        
        'rainy_thunderstorm_late_night': {
            'visual': [
                "late night rainy thunderstorm creates cosmic electric water backdrop to deep solitude and sparse illumination",
                "lightning and rain transform minimal lighting into charged world of electrical water mystical drama",
                "stormy downpour reduces deep night to intensely spiritual sphere of electric visibility through torrential sheets"
            ],
            'auditory': [
                "late night thunder becomes cosmic percussion mixing with rain's mystical drumming presence",
                "storm with rain amplifies minimal noise creating naturally sacred acoustic water drama",
                "rainy thunderstorm transforms deep night into acoustically spiritual and electrically profound space"
            ],
            'olfactory': [
                "late night rainy thunderstorm carries concentrated electric water essence mixed with sacred charged wet night air",
                "lightning with rain holds night's spiritual fragrances creating powerfully charged and mystically profound saturated atmosphere",
                "wet air blends deep solitude essence with storm's spiritually transformative and electrically pure rain energy"
            ],
            'atmospheric': [
                "late night rainy thunderstorm creates sense of cosmic electric water mystery during deep night's sacred solitude",
                "lightning with rain makes profound quiet feel dramatically charged and spiritually transformative",
                "stormy rain transforms ordinary deep night into electrically charged waterscape of cosmic turbulence"
            ]
        },
        
        # Complete hard_snow combinations (intense weather)
        'hard_snow_pre_dawn': {
            'visual': [
                "pre-dawn hard snow creates wild winter backdrop to deepest night's powerful fury",
                "driving snow transforms sacred solitude into intense world of crystalline white chaos",
                "heavy snowfall reduces profound quiet to churning sphere of brilliant flakes through darkness"
            ],
            'auditory': [
                "pre-dawn wind becomes howling force mixing with snow's intense whipping presence",
                "storm with snow creates naturally amplified acoustic winter chaos in sacred stormy silence",
                "hard snow transforms profound quiet into acoustically overwhelming and crystallinely charged space"
            ],
            'olfactory': [
                "pre-dawn hard snow carries intense crystalline essence mixed with charged cold night air",
                "driving snow holds pure winter aromas creating powerfully saturated icy atmospheric layers",
                "cold air intensifies storm essence with crystallinely pure and dramatically snow-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn hard snow creates sense of winter chaos during deepest night's crystalline fury",
                "driving snow makes sacred solitude feel intensely charged and dramatically overwhelming",
                "heavy snowfall transforms ordinary pre-dawn into crystallinely charged landscape of winter turbulence"
            ]
        },
        
        'hard_snow_dawn': {
            'visual': [
                "dawn hard snow creates spectacular winter drama backdrop to sunrise's powerful awakening",
                "driving snow transforms morning preparation into intense world of crystalline white beauty chaos",
                "heavy snowfall reduces dawn activity to energized sphere of brilliant visibility through driving flakes"
            ],
            'auditory': [
                "dawn wind becomes dramatic force mixing with snow's powerful whipping presence",
                "storm with snow amplifies morning sounds creating naturally intense acoustic winter drama",
                "hard snow transforms dawn into acoustically overwhelming and crystallinely dramatic space"
            ],
            'olfactory': [
                "dawn hard snow carries fresh crystalline essence mixed with morning's charged cold awakening",
                "driving snow holds clean winter aromas creating powerfully fresh icy atmospheric layers",
                "cold air blends dawn freshness with storm's intensely pure and dramatically snow-rich essence"
            ],
            'atmospheric': [
                "dawn hard snow creates sense of winter drama during morning's powerful crystalline awakening",
                "driving snow makes morning preparation feel intensely energized and dramatically beautiful",
                "heavy snowfall transforms ordinary dawn into crystallinely charged landscape of winter turbulence"
            ]
        },
        
        'hard_snow_early_morning': {
            'visual': [
                "early morning hard snow creates intense winter chaos backdrop to productive awakening",
                "driving snow transforms busy morning into charged world of crystalline white productivity chaos",
                "heavy snowfall reduces productive morning to energized sphere of brilliant focus through driving snow"
            ],
            'auditory': [
                "early morning wind becomes motivating force mixing with snow's energizing whipping presence",
                "storm with snow amplifies productive sounds creating naturally intense acoustic winter energy",
                "hard snow transforms busy morning into acoustically overwhelming and crystallinely energizing space"
            ],
            'olfactory': [
                "early morning hard snow carries charged crystalline essence mixed with productive cold awakening energy",
                "driving snow holds winter aromas creating powerfully energizing icy atmospheric layers",
                "cold air blends morning productivity with storm's intensely pure and dramatically energizing snow essence"
            ],
            'atmospheric': [
                "early morning hard snow creates sense of winter energy during productive crystalline awakening",
                "driving snow makes busy morning feel intensely motivated and dramatically productive",
                "heavy snowfall transforms hectic productivity into crystallinely charged landscape of energizing turbulence"
            ]
        },
        
        'hard_snow_late_morning': {
            'visual': [
                "late morning hard snow provides dramatic winter intensity during peak productive activity",
                "driving snow transforms overwhelming productivity into charged world of crystalline white focus chaos",
                "heavy snowfall reduces peak morning to intensely energized sphere of brilliant concentration through sheets"
            ],
            'auditory': [
                "late morning wind becomes powerful force amplifying snow's intense whipping presence",
                "storm with snow intensifies productive noise creating dramatically charged acoustic winter energy",
                "hard snow transforms overwhelming activity into acoustically chaotic and crystallinely intense space"
            ],
            'olfactory': [
                "late morning hard snow carries intense crystalline essence that energizes overcharged cold atmosphere",
                "driving snow amplifies productive aromas creating powerfully charged icy atmospheric layers",
                "cold air provides winter intensity to overwhelming productive scent concentration through snow"
            ],
            'atmospheric': [
                "late morning hard snow creates sense of winter chaos during peak crystalline intensity",
                "driving snow makes harsh productivity feel intensely charged and dramatically overwhelming",
                "heavy snowfall transforms overwhelming late morning into crystallinely charged landscape of intense turbulence"
            ]
        },
        
        'hard_snow_midday': {
            'visual': [
                "midday hard snow creates spectacular winter chaos during oppressive peak intensity",
                "driving snow transforms harsh conditions into charged world of crystalline white brilliance chaos",
                "heavy snowfall reduces overwhelming midday to dramatically energized sphere of winter visibility through torrents"
            ],
            'auditory': [
                "midday wind becomes overwhelming force mixing with snow's chaotic whipping presence",
                "storm with snow amplifies harsh peak noises creating dramatically powerful acoustic winter chaos",
                "hard snow transforms oppressive intensity into acoustically overwhelming and crystallinely charged space"
            ],
            'olfactory': [
                "midday hard snow carries overwhelming crystalline essence that intensifies extreme cold air",
                "driving snow amplifies harsh peak aromas creating powerfully overwhelming icy atmospheric layers",
                "cold air provides winter intensity to oppressive midday scent concentration through driving snow"
            ],
            'atmospheric': [
                "midday hard snow creates sense of overwhelming winter chaos during oppressive crystalline peak",
                "driving snow makes harsh intensity feel dramatically charged and overwhelmingly powerful",
                "heavy snowfall transforms oppressive midday into crystallinely charged landscape of overwhelming turbulence"
            ]
        },
        
        'hard_snow_early_afternoon': {
            'visual': [
                "early afternoon hard snow creates powerful winter drama backdrop to sustained intensive activity",
                "driving snow transforms heated afternoon into charged world of crystalline white energy chaos",
                "heavy snowfall reduces sustained intensity to dramatically energized sphere of winter focus through snow"
            ],
            'auditory': [
                "early afternoon wind becomes energizing force mixing with snow's powerful whipping presence",
                "storm with snow amplifies sustained noise creating naturally intense acoustic winter energy",
                "hard snow transforms heated activity into acoustically powerful and crystallinely energizing space"
            ],
            'olfactory': [
                "early afternoon hard snow carries charged crystalline essence that energizes sustained cold atmosphere",
                "driving snow intensifies aromas creating powerfully energizing icy atmospheric layers",
                "cold air provides winter energy to sustained afternoon scent intensity through refreshing snow"
            ],
            'atmospheric': [
                "early afternoon hard snow creates sense of winter power during sustained crystalline intensity",
                "driving snow makes activity feel dramatically energized and naturally powerful",
                "heavy snowfall transforms intense afternoon into crystallinely charged landscape of powerful turbulence"
            ]
        },
        
        'hard_snow_late_afternoon': {
            'visual': [
                "late afternoon hard snow creates dramatic winter chaos backdrop to transition energy",
                "driving snow transforms rush hour energy into charged world of crystalline white dramatic chaos",
                "heavy snowfall reduces busy transition to intensely energized sphere of winter visibility through sheets"
            ],
            'auditory': [
                "late afternoon wind becomes dramatic force mixing with snow's transitional whipping presence",
                "storm with snow amplifies harsh transition noise creating naturally powerful acoustic winter drama",
                "hard snow transforms busy evening approach into acoustically intense and crystallinely dramatic space"
            ],
            'olfactory': [
                "late afternoon hard snow carries mixture of winter energy and transitional crystalline intensity",
                "driving snow holds powerful winter aromas creating dramatically charged icy atmospheric layers",
                "cold air blends accumulated day essence with storm's intensely pure and dramatically winter snow essence"
            ],
            'atmospheric': [
                "late afternoon hard snow creates sense of dramatic winter transition during evening approach",
                "driving snow makes busy day's end feel intensely powerful and dramatically charged",
                "heavy snowfall transforms hectic transition into crystallinely charged landscape of dramatic turbulence"
            ]
        },
        
        'hard_snow_dusk': {
            'visual': [
                "dusk hard snow creates spectacular winter drama backdrop to sunset's powerful transition",
                "driving snow transforms dramatic sunset into charged world of crystalline white color chaos",
                "heavy snowfall reduces evening transition to intensely dramatic sphere of winter light through snow"
            ],
            'auditory': [
                "dusk wind becomes mystical force floating through snow's ethereal whipping presence",
                "storm with snow amplifies transition noise creating naturally contemplative acoustic winter drama",
                "hard snow transforms evening approach into acoustically mystical and crystallinely powerful space"
            ],
            'olfactory': [
                "dusk hard snow carries mixture of winter energy and night's approach in charged cold layers",
                "driving snow holds transitional winter aromas creating powerfully charged and dramatically mysterious atmosphere",
                "cold air blends cooling day essence with storm's mystically pure and crystallinely dramatic snow fragrances"
            ],
            'atmospheric': [
                "dusk hard snow creates sense of mystical winter transition during sunset's powerful passage",
                "driving snow makes evening approach feel dramatically charged and spiritually meaningful",
                "heavy snowfall transforms ordinary sunset into crystallinely charged landscape of mystical turbulence"
            ]
        },
        
        'hard_snow_early_evening': {
            'visual': [
                "early evening hard snow creates intense winter chaos backdrop to nightlife and social energy",
                "driving snow transforms artificial lights into charged halos of crystalline white dramatic glow",
                "heavy snowfall reduces social evening to energized sphere of winter visibility through driving snow"
            ],
            'auditory': [
                "early evening wind becomes energizing force floating through snow's social whipping presence",
                "storm with snow amplifies social noise creating naturally intense acoustic winter energy",
                "hard snow transforms nightlife energy into acoustically powerful and crystallinely energizing space"
            ],
            'olfactory': [
                "early evening hard snow carries mixture of winter air and entertainment energy intensely",
                "driving snow holds social fragrances creating powerfully charged icy atmospheric layers",
                "cold air blends nightlife essence with storm's dramatically pure winter snow energy"
            ],
            'atmospheric': [
                "early evening hard snow creates sense of intense winter social experience during nightlife",
                "driving snow makes social energy feel dramatically charged and powerfully connected",
                "heavy snowfall transforms ordinary nightlife into crystallinely charged landscape of intense turbulence"
            ]
        },
        
        'hard_snow_late_evening': {
            'visual': [
                "late evening hard snow creates powerful winter chaos backdrop to night's established rhythm",
                "driving snow transforms nightlife into charged world of crystalline white illumination drama",
                "heavy snowfall reduces late evening to dramatically energized sphere of winter visibility through sheets"
            ],
            'auditory': [
                "late evening wind becomes powerful force mixing with snow's intense whipping presence",
                "storm with snow amplifies night noise creating naturally dramatic acoustic winter energy",
                "hard snow transforms late evening into acoustically powerful and crystallinely intense space"
            ],
            'olfactory': [
                "late evening hard snow carries mixture of winter energy and cooling cold night layers",
                "driving snow holds evening fragrances creating powerfully charged and dramatically intense icy atmosphere",
                "cold air blends nightlife essence with storm's dramatically pure and crystallinely powerful snow energy"
            ],
            'atmospheric': [
                "late evening hard snow creates sense of winter drama during night's powerful progression",
                "driving snow makes night feel dramatically charged and spiritually meaningful",
                "heavy snowfall transforms ordinary late evening into crystallinely charged landscape of powerful turbulence"
            ]
        },
        
        'hard_snow_late_night': {
            'visual': [
                "late night hard snow creates cosmic winter chaos backdrop to deep solitude and sparse illumination",
                "driving snow transforms minimal lighting into charged world of crystalline white mystical drama",
                "heavy snowfall reduces deep night to intensely spiritual sphere of winter visibility through torrential sheets"
            ],
            'auditory': [
                "late night wind becomes cosmic force mixing with snow's mystical whipping presence",
                "storm with snow amplifies minimal noise creating naturally sacred acoustic winter drama",
                "hard snow transforms deep night into acoustically spiritual and crystallinely profound space"
            ],
            'olfactory': [
                "late night hard snow carries concentrated winter essence mixed with sacred charged cold night air",
                "driving snow holds night's spiritual fragrances creating powerfully charged and mystically profound icy atmosphere",
                "cold air blends deep solitude essence with storm's spiritually transformative and crystallinely pure snow energy"
            ],
            'atmospheric': [
                "late night hard snow creates sense of cosmic winter mystery during deep night's sacred solitude",
                "driving snow makes profound quiet feel dramatically charged and spiritually transformative",
                "heavy snowfall transforms ordinary deep night into crystallinely charged landscape of cosmic turbulence"
            ]
        },
        
        # Complete blizzard combinations (extreme weather)
        'blizzard_pre_dawn': {
            'visual': [
                "pre-dawn blizzard creates apocalyptic winter backdrop to deepest night's extreme fury",
                "howling snow wall transforms sacred solitude into devastating world of total white chaos obliteration",
                "blizzard reduces profound quiet to violently churning sphere of zero visibility through blinding snow"
            ],
            'auditory': [
                "pre-dawn wind becomes deafening roar overwhelming snow's devastating whipping presence completely",
                "blizzard creates naturally destructive acoustic winter apocalypse in sacred frozen silence",
                "extreme snowstorm transforms profound quiet into acoustically annihilating and crystallinely overwhelming space"
            ],
            'olfactory': [
                "pre-dawn blizzard carries overwhelming crystalline essence mixed with devastatingly charged arctic night air",
                "howling snow holds pure winter aromas creating powerfully suffocating icy atmospheric obliteration",
                "arctic air intensifies storm essence with crystallinely pure and devastatingly snow-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn blizzard creates sense of winter apocalypse during deepest night's crystalline devastation",
                "howling snow makes sacred solitude feel devastatingly charged and apocalyptically overwhelming",
                "blizzard transforms ordinary pre-dawn into crystallinely charged landscape of winter annihilation"
            ]
        },
        
        'blizzard_dawn': {
            'visual': [
                "dawn blizzard creates catastrophic winter drama backdrop to sunrise's obliterated awakening",
                "howling snow wall transforms morning preparation into devastating world of total crystalline chaos beauty",
                "blizzard reduces dawn activity to annihilated sphere of zero visibility through devastating driving snow"
            ],
            'auditory': [
                "dawn wind becomes catastrophic roar overwhelming snow's devastating whipping presence completely",
                "blizzard amplifies morning sounds creating naturally destructive acoustic winter catastrophe",
                "extreme snowstorm transforms dawn into acoustically annihilating and crystallinely devastating space"
            ],
            'olfactory': [
                "dawn blizzard carries devastating crystalline essence mixed with morning's obliterated cold awakening",
                "howling snow holds arctic aromas creating powerfully suffocating icy atmospheric devastation",
                "arctic air obliterates dawn freshness with storm's devastatingly pure and apocalyptically snow-rich essence"
            ],
            'atmospheric': [
                "dawn blizzard creates sense of winter catastrophe during morning's crystalline obliteration",
                "howling snow makes morning preparation feel devastatingly energized and apocalyptically beautiful",
                "blizzard transforms ordinary dawn into crystallinely charged landscape of winter annihilation"
            ]
        },
        
        'blizzard_early_morning': {
            'visual': [
                "early morning blizzard creates extreme winter apocalypse backdrop to obliterated productive awakening",
                "howling snow wall transforms busy morning into devastating world of total crystalline productivity chaos",
                "blizzard reduces productive morning to annihilated sphere of zero focus through devastating driving snow"
            ],
            'auditory': [
                "early morning wind becomes obliterating roar overwhelming snow's devastating whipping presence completely",
                "blizzard amplifies productive sounds creating naturally destructive acoustic winter apocalypse",
                "extreme snowstorm transforms busy morning into acoustically annihilating and crystallinely devastating space"
            ],
            'olfactory': [
                "early morning blizzard carries devastating crystalline essence mixed with obliterated productive cold awakening",
                "howling snow holds arctic aromas creating powerfully suffocating icy atmospheric devastation",
                "arctic air obliterates morning productivity with storm's devastatingly pure and apocalyptically energizing snow essence"
            ],
            'atmospheric': [
                "early morning blizzard creates sense of winter apocalypse during obliterated productive crystalline awakening",
                "howling snow makes busy morning feel devastatingly motivated and apocalyptically productive",
                "blizzard transforms hectic productivity into crystallinely charged landscape of annihilating turbulence"
            ]
        },
        
        'blizzard_late_morning': {
            'visual': [
                "late morning blizzard provides catastrophic winter intensity during obliterated peak productive activity",
                "howling snow wall transforms overwhelming productivity into devastating world of total crystalline chaos obliteration",
                "blizzard reduces peak morning to devastatingly energized sphere of zero concentration through blinding sheets"
            ],
            'auditory': [
                "late morning wind becomes apocalyptic roar amplifying snow's devastating whipping presence completely",
                "blizzard intensifies productive noise creating devastatingly charged acoustic winter apocalypse",
                "extreme snowstorm transforms overwhelming activity into acoustically catastrophic and crystallinely devastating space"
            ],
            'olfactory': [
                "late morning blizzard carries devastating crystalline essence that obliterates overcharged arctic atmosphere",
                "howling snow amplifies productive aromas creating powerfully suffocating icy atmospheric annihilation",
                "arctic air provides winter devastation to overwhelming productive scent concentration through obliterating snow"
            ],
            'atmospheric': [
                "late morning blizzard creates sense of winter apocalypse during peak crystalline devastation",
                "howling snow makes harsh productivity feel devastatingly charged and apocalyptically overwhelming",
                "blizzard transforms overwhelming late morning into crystallinely charged landscape of extreme annihilation"
            ]
        },
        
        'blizzard_midday': {
            'visual': [
                "midday blizzard creates ultimate winter apocalypse during obliterated oppressive peak intensity",
                "howling snow wall transforms harsh conditions into devastating world of total crystalline brilliance obliteration",
                "blizzard reduces overwhelming midday to catastrophically energized sphere of zero winter visibility through torrents"
            ],
            'auditory': [
                "midday wind becomes ultimate roar overwhelming snow's apocalyptic whipping presence completely",
                "blizzard amplifies harsh peak noises creating devastatingly powerful acoustic winter annihilation",
                "extreme snowstorm transforms oppressive intensity into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "midday blizzard carries ultimate crystalline essence that devastates extreme arctic air completely",
                "howling snow amplifies harsh peak aromas creating powerfully obliterating icy atmospheric annihilation",
                "arctic air provides winter devastation to oppressive midday scent concentration through apocalyptic driving snow"
            ],
            'atmospheric': [
                "midday blizzard creates sense of ultimate winter apocalypse during obliterated oppressive crystalline peak",
                "howling snow makes harsh intensity feel devastatingly charged and ultimately overwhelming",
                "blizzard transforms oppressive midday into crystallinely charged landscape of ultimate annihilation"
            ]
        },
        
        'blizzard_early_afternoon': {
            'visual': [
                "early afternoon blizzard creates extreme winter catastrophe backdrop to obliterated sustained intensive activity",
                "howling snow wall transforms heated afternoon into devastating world of total crystalline energy obliteration",
                "blizzard reduces sustained intensity to catastrophically energized sphere of zero winter focus through snow"
            ],
            'auditory': [
                "early afternoon wind becomes catastrophic roar overwhelming snow's devastating whipping presence completely",
                "blizzard amplifies sustained noise creating naturally destructive acoustic winter catastrophe",
                "extreme snowstorm transforms heated activity into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "early afternoon blizzard carries devastating crystalline essence that obliterates sustained arctic atmosphere",
                "howling snow intensifies aromas creating powerfully suffocating icy atmospheric devastation",
                "arctic air provides winter devastation to sustained afternoon scent intensity through obliterating snow"
            ],
            'atmospheric': [
                "early afternoon blizzard creates sense of winter catastrophe during obliterated sustained crystalline intensity",
                "howling snow makes activity feel devastatingly energized and apocalyptically powerful",
                "blizzard transforms intense afternoon into crystallinely charged landscape of catastrophic turbulence"
            ]
        },
        
        'blizzard_late_afternoon': {
            'visual': [
                "late afternoon blizzard creates catastrophic winter apocalypse backdrop to obliterated transition energy",
                "howling snow wall transforms rush hour energy into devastating world of total crystalline dramatic obliteration",
                "blizzard reduces busy transition to devastatingly energized sphere of zero winter visibility through blinding sheets"
            ],
            'auditory': [
                "late afternoon wind becomes apocalyptic roar overwhelming snow's devastating transitional whipping presence completely",
                "blizzard amplifies harsh transition noise creating naturally catastrophic acoustic winter apocalypse",
                "extreme snowstorm transforms busy evening approach into acoustically devastating and crystallinely obliterating space"
            ],
            'olfactory': [
                "late afternoon blizzard carries mixture of winter devastation and obliterated transitional crystalline intensity",
                "howling snow holds catastrophic winter aromas creating devastatingly charged icy atmospheric annihilation",
                "arctic air obliterates accumulated day essence with storm's devastatingly pure and apocalyptically winter snow essence"
            ],
            'atmospheric': [
                "late afternoon blizzard creates sense of catastrophic winter transition during obliterated evening approach",
                "howling snow makes busy day's end feel devastatingly powerful and apocalyptically charged",
                "blizzard transforms hectic transition into crystallinely charged landscape of catastrophic annihilation"
            ]
        },
        
        'blizzard_dusk': {
            'visual': [
                "dusk blizzard creates ultimate winter catastrophe backdrop to obliterated sunset's devastating transition",
                "howling snow wall transforms dramatic sunset into devastating world of total crystalline color obliteration",
                "blizzard reduces evening transition to devastatingly dramatic sphere of zero winter light through snow"
            ],
            'auditory': [
                "dusk wind becomes ultimate roar floating through snow's apocalyptic whipping presence completely",
                "blizzard amplifies transition noise creating naturally catastrophic acoustic winter apocalypse",
                "extreme snowstorm transforms evening approach into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "dusk blizzard carries mixture of winter devastation and obliterated night's approach in catastrophic arctic layers",
                "howling snow holds transitional winter aromas creating devastatingly charged and apocalyptically mysterious atmosphere",
                "arctic air obliterates cooling day essence with storm's devastatingly pure and crystallinely apocalyptic snow fragrances"
            ],
            'atmospheric': [
                "dusk blizzard creates sense of ultimate winter transition during obliterated sunset's devastating passage",
                "howling snow makes evening approach feel devastatingly charged and apocalyptically meaningful",
                "blizzard transforms ordinary sunset into crystallinely charged landscape of ultimate annihilation"
            ]
        },
        
        'blizzard_early_evening': {
            'visual': [
                "early evening blizzard creates extreme winter apocalypse backdrop to obliterated nightlife and social energy",
                "howling snow wall transforms artificial lights into devastating halos of total crystalline dramatic obliteration",
                "blizzard reduces social evening to catastrophically energized sphere of zero winter visibility through devastating snow"
            ],
            'auditory': [
                "early evening wind becomes catastrophic roar floating through snow's devastating social whipping presence completely",
                "blizzard amplifies social noise creating naturally destructive acoustic winter catastrophe",
                "extreme snowstorm transforms nightlife energy into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "early evening blizzard carries mixture of winter devastation and obliterated entertainment energy devastatingly",
                "howling snow holds social fragrances creating devastatingly charged icy atmospheric annihilation",
                "arctic air obliterates nightlife essence with storm's devastatingly pure winter snow devastation"
            ],
            'atmospheric': [
                "early evening blizzard creates sense of extreme winter social experience during obliterated nightlife",
                "howling snow makes social energy feel devastatingly charged and apocalyptically connected",
                "blizzard transforms ordinary nightlife into crystallinely charged landscape of extreme annihilation"
            ]
        },
        
        'blizzard_late_evening': {
            'visual': [
                "late evening blizzard creates ultimate winter apocalypse backdrop to obliterated night's established rhythm",
                "howling snow wall transforms nightlife into devastating world of total crystalline illumination obliteration",
                "blizzard reduces late evening to catastrophically energized sphere of zero winter visibility through blinding sheets"
            ],
            'auditory': [
                "late evening wind becomes ultimate roar overwhelming snow's devastating whipping presence completely",
                "blizzard amplifies night noise creating naturally catastrophic acoustic winter apocalypse",
                "extreme snowstorm transforms late evening into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "late evening blizzard carries mixture of winter devastation and obliterated cooling arctic night layers",
                "howling snow holds evening fragrances creating devastatingly charged and apocalyptically intense icy atmosphere",
                "arctic air obliterates nightlife essence with storm's devastatingly pure and crystallinely apocalyptic snow devastation"
            ],
            'atmospheric': [
                "late evening blizzard creates sense of winter apocalypse during obliterated night's devastating progression",
                "howling snow makes night feel devastatingly charged and apocalyptically meaningful",
                "blizzard transforms ordinary late evening into crystallinely charged landscape of ultimate annihilation"
            ]
        },
        
        'blizzard_late_night': {
            'visual': [
                "late night blizzard creates cosmic winter apocalypse backdrop to obliterated deep solitude and devastated illumination",
                "howling snow wall transforms minimal lighting into devastating world of total crystalline mystical obliteration",
                "blizzard reduces deep night to devastatingly spiritual sphere of zero winter visibility through apocalyptic torrential sheets"
            ],
            'auditory': [
                "late night wind becomes cosmic roar overwhelming snow's devastating mystical whipping presence completely",
                "blizzard amplifies minimal noise creating naturally catastrophic acoustic winter apocalypse",
                "extreme snowstorm transforms deep night into acoustically obliterating and crystallinely devastating space"
            ],
            'olfactory': [
                "late night blizzard carries concentrated winter devastation mixed with obliterated sacred arctic night air",
                "howling snow holds night's spiritual fragrances creating devastatingly charged and apocalyptically profound icy atmosphere",
                "arctic air obliterates deep solitude essence with storm's devastatingly transformative and crystallinely apocalyptic snow devastation"
            ],
            'atmospheric': [
                "late night blizzard creates sense of cosmic winter mystery during obliterated deep night's sacred annihilation",
                "howling snow makes profound quiet feel devastatingly charged and apocalyptically transformative",
                "blizzard transforms ordinary deep night into crystallinely charged landscape of cosmic obliteration"
            ]
        },
        
        # Complete gray_pall combinations (moderate toxic weather)
        'gray_pall_pre_dawn': {
            'visual': [
                "pre-dawn gray pall creates suffocating toxic backdrop to deepest night's poisoned solitude",
                "thick gray shroud transforms sacred silence into oppressive world of toxic gray mystery",
                "toxic pall reduces profound quiet to choking sphere of gray visibility and poisoned shadow"
            ],
            'auditory': [
                "pre-dawn sounds become muffled whispers in gray pall's toxic presence",
                "toxic shroud absorbs sacred noise creating unnaturally heavy acoustics",
                "gray pall transforms profound quiet into acoustically oppressive and toxically charged space"
            ],
            'olfactory': [
                "pre-dawn gray pall carries acrid toxic essence mixed with poisoned night air",
                "toxic shroud holds bitter chemical aromas creating suffocatingly heavy atmospheric layers",
                "poisoned air intensifies toxic essence with chemically pure and oppressively gray-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn gray pall creates sense of toxic oppression during deepest night's poisoned solitude",
                "toxic shroud makes sacred silence feel suffocatingly charged and chemically overwhelming",
                "gray pall transforms ordinary pre-dawn into toxically charged landscape of poisoned possibility"
            ]
        },
        
        'gray_pall_dawn': {
            'visual': [
                "dawn gray pall creates oppressive toxic backdrop to sunrise's poisoned awakening",
                "thick gray shroud transforms morning preparation into suffocating world of toxic gray beauty",
                "toxic pall reduces dawn activity to choking sphere of gray visibility and chemical shadow"
            ],
            'auditory': [
                "dawn sounds become labored whispers in gray pall's oppressive presence",
                "toxic shroud absorbs morning noise creating unnaturally heavy acoustics",
                "gray pall transforms dawn into acoustically oppressive and toxically charged space"
            ],
            'olfactory': [
                "dawn gray pall carries bitter toxic essence mixed with morning's poisoned awakening",
                "toxic shroud holds acrid chemical aromas creating suffocatingly fresh atmospheric layers",
                "poisoned air blends dawn freshness with pall's chemically pure and oppressively toxic essence"
            ],
            'atmospheric': [
                "dawn gray pall creates sense of toxic oppression during morning's poisoned awakening",
                "toxic shroud makes morning preparation feel suffocatingly energized and chemically beautiful",
                "gray pall transforms ordinary dawn into toxically charged landscape of poisoned possibility"
            ]
        },
        
        'gray_pall_early_morning': {
            'visual': [
                "early morning gray pall creates suffocating toxic backdrop to poisoned productive awakening",
                "thick gray shroud transforms busy morning into oppressive world of toxic gray productivity",
                "toxic pall reduces productive morning to choking sphere of gray focus and chemical concentration"
            ],
            'auditory': [
                "early morning sounds become strained whispers in gray pall's suffocating presence",
                "toxic shroud absorbs productive noise creating unnaturally heavy acoustics",
                "gray pall transforms busy morning into acoustically oppressive and toxically energizing space"
            ],
            'olfactory': [
                "early morning gray pall carries acrid toxic essence mixed with productive poisoned awakening",
                "toxic shroud holds chemical aromas creating suffocatingly energizing atmospheric layers",
                "poisoned air blends morning productivity with pall's chemically pure and oppressively energizing toxic essence"
            ],
            'atmospheric': [
                "early morning gray pall creates sense of toxic energy during productive poisoned awakening",
                "toxic shroud makes busy morning feel suffocatingly motivated and chemically productive",
                "gray pall transforms hectic productivity into toxically charged landscape of poisoned turbulence"
            ]
        },
        
        'gray_pall_late_morning': {
            'visual': [
                "late morning gray pall provides oppressive toxic intensity during peak poisoned productive activity",
                "thick gray shroud transforms overwhelming productivity into suffocating world of toxic gray focus",
                "toxic pall reduces peak morning to chokingly energized sphere of gray concentration and chemical intensity"
            ],
            'auditory': [
                "late morning sounds become labored breathing in gray pall's oppressive presence",
                "toxic shroud intensifies productive noise creating suffocatingly charged acoustics",
                "gray pall transforms overwhelming activity into acoustically oppressive and toxically intense space"
            ],
            'olfactory': [
                "late morning gray pall carries overwhelming toxic essence that poisons overcharged atmosphere",
                "toxic shroud amplifies productive aromas creating suffocatingly charged atmospheric layers",
                "poisoned air provides toxic intensity to overwhelming productive scent concentration through gray pall"
            ],
            'atmospheric': [
                "late morning gray pall creates sense of toxic oppression during peak poisoned intensity",
                "toxic shroud makes harsh productivity feel suffocatingly charged and chemically overwhelming",
                "gray pall transforms overwhelming late morning into toxically charged landscape of poisoned turbulence"
            ]
        },
        
        'gray_pall_midday': {
            'visual': [
                "midday gray pall creates ultimate toxic oppression during poisoned oppressive peak intensity",
                "thick gray shroud transforms harsh conditions into suffocating world of toxic gray brilliance",
                "toxic pall reduces overwhelming midday to chokingly energized sphere of gray visibility and chemical torrents"
            ],
            'auditory': [
                "midday sounds become suffocating gasps in gray pall's ultimate oppressive presence",
                "toxic shroud amplifies harsh peak noises creating suffocatingly powerful acoustics",
                "gray pall transforms oppressive intensity into acoustically choking and toxically charged space"
            ],
            'olfactory': [
                "midday gray pall carries ultimate toxic essence that poisons extreme atmosphere completely",
                "toxic shroud amplifies harsh peak aromas creating suffocatingly overwhelming atmospheric layers",
                "poisoned air provides toxic oppression to overwhelming midday scent concentration through choking gray pall"
            ],
            'atmospheric': [
                "midday gray pall creates sense of ultimate toxic oppression during poisoned oppressive peak",
                "toxic shroud makes harsh intensity feel suffocatingly charged and ultimately overwhelming",
                "gray pall transforms oppressive midday into toxically charged landscape of poisoned annihilation"
            ]
        },
        
        'gray_pall_early_afternoon': {
            'visual': [
                "early afternoon gray pall creates oppressive toxic backdrop to poisoned sustained intensive activity",
                "thick gray shroud transforms heated afternoon into suffocating world of toxic gray energy",
                "toxic pall reduces sustained intensity to chokingly energized sphere of gray focus and chemical concentration"
            ],
            'auditory': [
                "early afternoon sounds become labored breathing in gray pall's suffocating presence",
                "toxic shroud amplifies sustained noise creating unnaturally oppressive acoustics",
                "gray pall transforms heated activity into acoustically choking and toxically energizing space"
            ],
            'olfactory': [
                "early afternoon gray pall carries oppressive toxic essence that poisons sustained atmosphere",
                "toxic shroud intensifies aromas creating suffocatingly energizing atmospheric layers",
                "poisoned air provides toxic energy to sustained afternoon scent intensity through oppressive gray pall"
            ],
            'atmospheric': [
                "early afternoon gray pall creates sense of toxic energy during poisoned sustained intensity",
                "toxic shroud makes activity feel suffocatingly energized and chemically powerful",
                "gray pall transforms intense afternoon into toxically charged landscape of poisoned turbulence"
            ]
        },
        
        'gray_pall_late_afternoon': {
            'visual': [
                "late afternoon gray pall creates oppressive toxic backdrop to poisoned transition energy",
                "thick gray shroud transforms rush hour energy into suffocating world of toxic gray dramatic intensity",
                "toxic pall reduces busy transition to chokingly energized sphere of gray visibility and chemical sheets"
            ],
            'auditory': [
                "late afternoon sounds become strained gasping in gray pall's oppressive transitional presence",
                "toxic shroud amplifies harsh transition noise creating suffocatingly powerful acoustics",
                "gray pall transforms busy evening approach into acoustically oppressive and toxically dramatic space"
            ],
            'olfactory': [
                "late afternoon gray pall carries mixture of toxic oppression and poisoned transitional intensity",
                "toxic shroud holds oppressive chemical aromas creating suffocatingly charged atmospheric layers",
                "poisoned air poisons accumulated day essence with pall's chemically pure and oppressively toxic essence"
            ],
            'atmospheric': [
                "late afternoon gray pall creates sense of oppressive toxic transition during poisoned evening approach",
                "toxic shroud makes busy day's end feel suffocatingly powerful and chemically charged",
                "gray pall transforms hectic transition into toxically charged landscape of poisoned turbulence"
            ]
        },
        
        'gray_pall_dusk': {
            'visual': [
                "dusk gray pall creates ultimate toxic oppression backdrop to poisoned sunset's suffocating transition",
                "thick gray shroud transforms dramatic sunset into suffocating world of toxic gray color intensity",
                "toxic pall reduces evening transition to chokingly dramatic sphere of gray light and chemical shadow"
            ],
            'auditory': [
                "dusk sounds become labored whispers floating through gray pall's oppressive presence",
                "toxic shroud amplifies transition noise creating suffocatingly contemplative acoustics",
                "gray pall transforms evening approach into acoustically choking and toxically powerful space"
            ],
            'olfactory': [
                "dusk gray pall carries mixture of toxic oppression and poisoned night's approach in suffocating layers",
                "toxic shroud holds transitional chemical aromas creating suffocatingly charged and oppressively mysterious atmosphere",
                "poisoned air poisons cooling day essence with pall's chemically pure and toxically dramatic fragrances"
            ],
            'atmospheric': [
                "dusk gray pall creates sense of ultimate toxic transition during poisoned sunset's suffocating passage",
                "toxic shroud makes evening approach feel suffocatingly charged and chemically meaningful",
                "gray pall transforms ordinary sunset into toxically charged landscape of poisoned possibility"
            ]
        },
        
        'gray_pall_early_evening': {
            'visual': [
                "early evening gray pall creates oppressive toxic backdrop to poisoned nightlife and suffocating social energy",
                "thick gray shroud transforms artificial lights into choking halos of toxic gray dramatic glow",
                "toxic pall reduces social evening to suffocatingly energized sphere of gray visibility and chemical intensity"
            ],
            'auditory': [
                "early evening sounds become strained whispers floating through gray pall's suffocating social presence",
                "toxic shroud amplifies social noise creating unnaturally oppressive acoustics",
                "gray pall transforms nightlife energy into acoustically choking and toxically energizing space"
            ],
            'olfactory': [
                "early evening gray pall carries mixture of toxic air and poisoned entertainment energy suffocatingly",
                "toxic shroud holds social fragrances creating suffocatingly charged atmospheric layers",
                "poisoned air poisons nightlife essence with pall's chemically pure toxic energy"
            ],
            'atmospheric': [
                "early evening gray pall creates sense of oppressive toxic social experience during poisoned nightlife",
                "toxic shroud makes social energy feel suffocatingly charged and chemically connected",
                "gray pall transforms ordinary nightlife into toxically charged landscape of poisoned possibility"
            ]
        },
        
        'gray_pall_late_evening': {
            'visual': [
                "late evening gray pall creates ultimate toxic oppression backdrop to poisoned night's established rhythm",
                "thick gray shroud transforms nightlife into suffocating world of toxic gray illumination intensity",
                "toxic pall reduces late evening to chokingly energized sphere of gray visibility and chemical sheets"
            ],
            'auditory': [
                "late evening sounds become labored breathing in gray pall's ultimate oppressive presence",
                "toxic shroud amplifies night noise creating suffocatingly dramatic acoustics",
                "gray pall transforms late evening into acoustically choking and toxically intense space"
            ],
            'olfactory': [
                "late evening gray pall carries mixture of toxic oppression and poisoned cooling night layers",
                "toxic shroud holds evening fragrances creating suffocatingly charged and oppressively intense atmosphere",
                "poisoned air poisons nightlife essence with pall's chemically pure and toxically powerful energy"
            ],
            'atmospheric': [
                "late evening gray pall creates sense of toxic oppression during poisoned night's suffocating progression",
                "toxic shroud makes night feel suffocatingly charged and chemically meaningful",
                "gray pall transforms ordinary late evening into toxically charged landscape of poisoned possibility"
            ]
        },
        
        'gray_pall_late_night': {
            'visual': [
                "late night gray pall creates cosmic toxic oppression backdrop to poisoned deep solitude and suffocated illumination",
                "thick gray shroud transforms minimal lighting into suffocating world of toxic gray mystical intensity",
                "toxic pall reduces deep night to chokingly spiritual sphere of gray visibility and chemical torrential sheets"
            ],
            'auditory': [
                "late night sounds become suffocating whispers in gray pall's cosmic oppressive presence",
                "toxic shroud amplifies minimal noise creating suffocatingly sacred acoustics",
                "gray pall transforms deep night into acoustically choking and toxically profound space"
            ],
            'olfactory': [
                "late night gray pall carries concentrated toxic oppression mixed with poisoned sacred night air",
                "toxic shroud holds night's spiritual fragrances creating suffocatingly charged and oppressively profound atmosphere",
                "poisoned air poisons deep solitude essence with pall's chemically transformative and toxically pure energy"
            ],
            'atmospheric': [
                "late night gray pall creates sense of cosmic toxic mystery during poisoned deep night's sacred suffocation",
                "toxic shroud makes profound quiet feel suffocatingly charged and chemically transformative",
                "gray pall transforms ordinary deep night into toxically charged landscape of poisoned cosmic possibility"
            ]
        },
        
        'gray_pall_night': {
            'visual': [
                "night gray pall creates oppressive toxic backdrop to established darkness and suffocating rhythm",
                "thick gray shroud transforms night rhythm into suffocating world of toxic gray established intensity",
                "toxic pall reduces settled night to chokingly energized sphere of gray visibility and chemical sheets"
            ],
            'auditory': [
                "night sounds become labored breathing in gray pall's oppressive established presence",
                "toxic shroud amplifies night sounds creating suffocatingly rhythmic acoustics",
                "gray pall transforms settled night into acoustically choking and toxically established space"
            ],
            'olfactory': [
                "night gray pall carries established toxic essence mixed with rhythmic poisoned night air",
                "toxic shroud holds night's established fragrances creating suffocatingly charged and rhythmically oppressive atmosphere",
                "poisoned air poisons settled darkness essence with pall's rhythmically pure and toxically established energy"
            ],
            'atmospheric': [
                "night gray pall creates sense of established toxic rhythm during night's poisoned progression",
                "toxic shroud makes settled darkness feel suffocatingly charged and chemically meaningful",
                "gray pall transforms ordinary night into toxically charged landscape of poisoned rhythmic possibility"
            ]
        },
        
        # Complete tox_rain combinations (intense toxic weather)  
        'tox_rain_pre_dawn': {
            'visual': [
                "pre-dawn tox rain creates corrosive toxic backdrop to deepest night's poisoned solitude",
                "burning acidic droplets transform sacred silence into devastating world of toxic corrosive chaos",
                "toxic rain reduces profound quiet to sizzling sphere of corrosive visibility and poisoned burning shadow"
            ],
            'auditory': [
                "pre-dawn sounds become sizzling whispers in tox rain's corrosive presence",
                "toxic rain creates naturally destructive acoustic chaos with burning droplets",
                "acidic downpour transforms profound quiet into acoustically corrosive and toxically devastating space"
            ],
            'olfactory': [
                "pre-dawn tox rain carries burning toxic essence mixed with corrosive poisoned night air",
                "acidic rain holds searing chemical aromas creating devastatingly saturated atmospheric layers",
                "toxic air intensifies corrosive essence with chemically pure and devastatingly acid-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn tox rain creates sense of toxic devastation during deepest night's corrosive solitude",
                "acidic rain makes sacred silence feel devastatingly charged and chemically overwhelming",
                "toxic downpour transforms ordinary pre-dawn into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_dawn': {
            'visual': [
                "dawn tox rain creates devastating toxic backdrop to sunrise's corrosive awakening",
                "burning acidic droplets transform morning preparation into searing world of toxic corrosive beauty",
                "toxic rain reduces dawn activity to sizzling sphere of corrosive visibility and chemical burning shadow"
            ],
            'auditory': [
                "dawn sounds become burning whispers in tox rain's devastating presence",
                "toxic rain amplifies morning sounds creating naturally corrosive acoustic destruction",
                "acidic downpour transforms dawn into acoustically devastating and toxically charged space"
            ],
            'olfactory': [
                "dawn tox rain carries searing toxic essence mixed with morning's corrosive poisoned awakening",
                "acidic rain holds burning chemical aromas creating devastatingly fresh saturated atmospheric layers",
                "toxic air burns dawn freshness with rain's chemically pure and devastatingly corrosive essence"
            ],
            'atmospheric': [
                "dawn tox rain creates sense of toxic destruction during morning's corrosive awakening",
                "acidic rain makes morning preparation feel devastatingly energized and chemically beautiful",
                "toxic downpour transforms ordinary dawn into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_early_morning': {
            'visual': [
                "early morning tox rain creates corrosive toxic backdrop to poisoned productive awakening",
                "burning acidic droplets transform busy morning into devastating world of toxic corrosive productivity",
                "toxic rain reduces productive morning to sizzling sphere of corrosive focus and chemical concentration"
            ],
            'auditory': [
                "early morning sounds become searing whispers in tox rain's corrosive presence",
                "toxic rain amplifies productive sounds creating naturally destructive acoustic devastation",
                "acidic downpour transforms busy morning into acoustically corrosive and toxically energizing space"
            ],
            'olfactory': [
                "early morning tox rain carries burning toxic essence mixed with productive corrosive awakening",
                "acidic rain holds searing chemical aromas creating devastatingly energizing saturated atmospheric layers",
                "toxic air burns morning productivity with rain's chemically pure and devastatingly energizing corrosive essence"
            ],
            'atmospheric': [
                "early morning tox rain creates sense of toxic devastation during productive corrosive awakening",
                "acidic rain makes busy morning feel devastatingly motivated and chemically productive",
                "toxic downpour transforms hectic productivity into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_late_morning': {
            'visual': [
                "late morning tox rain provides devastating toxic intensity during peak corrosive productive activity",
                "burning acidic droplets transform overwhelming productivity into searing world of toxic corrosive focus",
                "toxic rain reduces peak morning to devastatingly energized sphere of corrosive concentration and chemical burning"
            ],
            'auditory': [
                "late morning sounds become sizzling gasps in tox rain's devastating presence",
                "toxic rain intensifies productive noise creating devastatingly charged corrosive acoustics",
                "acidic downpour transforms overwhelming activity into acoustically destructive and toxically intense space"
            ],
            'olfactory': [
                "late morning tox rain carries devastating toxic essence that burns overcharged corrosive atmosphere",
                "acidic rain amplifies productive aromas creating devastatingly charged saturated atmospheric layers",
                "toxic air provides corrosive devastation to overwhelming productive scent concentration through burning rain"
            ],
            'atmospheric': [
                "late morning tox rain creates sense of toxic destruction during peak corrosive intensity",
                "acidic rain makes harsh productivity feel devastatingly charged and chemically overwhelming",
                "toxic downpour transforms overwhelming late morning into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_midday': {
            'visual': [
                "midday tox rain creates ultimate toxic devastation during corrosive oppressive peak intensity",
                "burning acidic droplets transform harsh conditions into searing world of toxic corrosive brilliance",
                "toxic rain reduces overwhelming midday to devastatingly energized sphere of corrosive visibility and chemical torrents"
            ],
            'auditory': [
                "midday sounds become burning gasps in tox rain's ultimate devastating presence",
                "toxic rain amplifies harsh peak noises creating devastatingly powerful corrosive acoustics",
                "acidic downpour transforms oppressive intensity into acoustically destructive and toxically charged space"
            ],
            'olfactory': [
                "midday tox rain carries ultimate toxic essence that burns extreme corrosive atmosphere completely",
                "acidic rain amplifies harsh peak aromas creating devastatingly overwhelming saturated atmospheric layers",
                "toxic air provides corrosive devastation to overwhelming midday scent concentration through burning acidic rain"
            ],
            'atmospheric': [
                "midday tox rain creates sense of ultimate toxic devastation during corrosive oppressive peak",
                "acidic rain makes harsh intensity feel devastatingly charged and ultimately overwhelming",
                "toxic downpour transforms oppressive midday into corrosively charged landscape of poisoned annihilation"
            ]
        },
        
        'tox_rain_early_afternoon': {
            'visual': [
                "early afternoon tox rain creates devastating toxic backdrop to corrosive sustained intensive activity",
                "burning acidic droplets transform heated afternoon into searing world of toxic corrosive energy",
                "toxic rain reduces sustained intensity to devastatingly energized sphere of corrosive focus and chemical concentration"
            ],
            'auditory': [
                "early afternoon sounds become sizzling breathing in tox rain's devastating presence",
                "toxic rain amplifies sustained noise creating naturally destructive corrosive acoustics",
                "acidic downpour transforms heated activity into acoustically destructive and toxically energizing space"
            ],
            'olfactory': [
                "early afternoon tox rain carries devastating toxic essence that burns sustained corrosive atmosphere",
                "acidic rain intensifies aromas creating devastatingly energizing saturated atmospheric layers",
                "toxic air provides corrosive devastation to sustained afternoon scent intensity through burning acidic rain"
            ],
            'atmospheric': [
                "early afternoon tox rain creates sense of toxic devastation during corrosive sustained intensity",
                "acidic rain makes activity feel devastatingly energized and chemically powerful",
                "toxic downpour transforms intense afternoon into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_late_afternoon': {
            'visual': [
                "late afternoon tox rain creates devastating toxic backdrop to corrosive transition energy",
                "burning acidic droplets transform rush hour energy into searing world of toxic corrosive dramatic intensity",
                "toxic rain reduces busy transition to devastatingly energized sphere of corrosive visibility and chemical sheets"
            ],
            'auditory': [
                "late afternoon sounds become burning gasps in tox rain's devastating transitional presence",
                "toxic rain amplifies harsh transition noise creating devastatingly powerful corrosive acoustics",
                "acidic downpour transforms busy evening approach into acoustically destructive and toxically dramatic space"
            ],
            'olfactory': [
                "late afternoon tox rain carries mixture of toxic devastation and corrosive transitional intensity",
                "acidic rain holds devastating chemical aromas creating devastatingly charged saturated atmospheric layers",
                "toxic air burns accumulated day essence with rain's chemically pure and devastatingly corrosive essence"
            ],
            'atmospheric': [
                "late afternoon tox rain creates sense of devastating toxic transition during corrosive evening approach",
                "acidic rain makes busy day's end feel devastatingly powerful and chemically charged",
                "toxic downpour transforms hectic transition into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_dusk': {
            'visual': [
                "dusk tox rain creates ultimate toxic devastation backdrop to corrosive sunset's burning transition",
                "burning acidic droplets transform dramatic sunset into searing world of toxic corrosive color intensity",
                "toxic rain reduces evening transition to devastatingly dramatic sphere of corrosive light and chemical shadow"
            ],
            'auditory': [
                "dusk sounds become sizzling whispers floating through tox rain's devastating presence",
                "toxic rain amplifies transition noise creating devastatingly contemplative corrosive acoustics",
                "acidic downpour transforms evening approach into acoustically destructive and toxically powerful space"
            ],
            'olfactory': [
                "dusk tox rain carries mixture of toxic devastation and corrosive night's approach in burning layers",
                "acidic rain holds transitional chemical aromas creating devastatingly charged and corrosively mysterious atmosphere",
                "toxic air burns cooling day essence with rain's chemically pure and toxically dramatic fragrances"
            ],
            'atmospheric': [
                "dusk tox rain creates sense of ultimate toxic transition during corrosive sunset's burning passage",
                "acidic rain makes evening approach feel devastatingly charged and chemically meaningful",
                "toxic downpour transforms ordinary sunset into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_early_evening': {
            'visual': [
                "early evening tox rain creates devastating toxic backdrop to corrosive nightlife and burning social energy",
                "burning acidic droplets transform artificial lights into searing halos of toxic corrosive dramatic glow",
                "toxic rain reduces social evening to devastatingly energized sphere of corrosive visibility and chemical intensity"
            ],
            'auditory': [
                "early evening sounds become burning whispers floating through tox rain's devastating social presence",
                "toxic rain amplifies social noise creating naturally destructive corrosive acoustics",
                "acidic downpour transforms nightlife energy into acoustically destructive and toxically energizing space"
            ],
            'olfactory': [
                "early evening tox rain carries mixture of toxic air and corrosive entertainment energy devastatingly",
                "acidic rain holds social fragrances creating devastatingly charged saturated atmospheric layers",
                "toxic air burns nightlife essence with rain's chemically pure corrosive energy"
            ],
            'atmospheric': [
                "early evening tox rain creates sense of devastating toxic social experience during corrosive nightlife",
                "acidic rain makes social energy feel devastatingly charged and chemically connected",
                "toxic downpour transforms ordinary nightlife into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_late_evening': {
            'visual': [
                "late evening tox rain creates ultimate toxic devastation backdrop to corrosive night's established rhythm",
                "burning acidic droplets transform nightlife into searing world of toxic corrosive illumination intensity",
                "toxic rain reduces late evening to devastatingly energized sphere of corrosive visibility and chemical sheets"
            ],
            'auditory': [
                "late evening sounds become sizzling breathing in tox rain's ultimate devastating presence",
                "toxic rain amplifies night noise creating devastatingly dramatic corrosive acoustics",
                "acidic downpour transforms late evening into acoustically destructive and toxically intense space"
            ],
            'olfactory': [
                "late evening tox rain carries mixture of toxic devastation and corrosive cooling night layers",
                "acidic rain holds evening fragrances creating devastatingly charged and corrosively intense saturated atmosphere",
                "toxic air burns nightlife essence with rain's chemically pure and toxically powerful corrosive energy"
            ],
            'atmospheric': [
                "late evening tox rain creates sense of toxic devastation during corrosive night's burning progression",
                "acidic rain makes night feel devastatingly charged and chemically meaningful",
                "toxic downpour transforms ordinary late evening into corrosively charged landscape of poisoned destruction"
            ]
        },
        
        'tox_rain_late_night': {
            'visual': [
                "late night tox rain creates cosmic toxic devastation backdrop to corrosive deep solitude and burned illumination",
                "burning acidic droplets transform minimal lighting into searing world of toxic corrosive mystical intensity",
                "toxic rain reduces deep night to devastatingly spiritual sphere of corrosive visibility and chemical torrential sheets"
            ],
            'auditory': [
                "late night sounds become burning whispers in tox rain's cosmic devastating presence",
                "toxic rain amplifies minimal noise creating devastatingly sacred corrosive acoustics",
                "acidic downpour transforms deep night into acoustically destructive and toxically profound space"
            ],
            'olfactory': [
                "late night tox rain carries concentrated toxic devastation mixed with corrosive sacred night air",
                "acidic rain holds night's spiritual fragrances creating devastatingly charged and corrosively profound saturated atmosphere",
                "toxic air burns deep solitude essence with rain's chemically transformative and toxically pure corrosive energy"
            ],
            'atmospheric': [
                "late night tox rain creates sense of cosmic toxic mystery during corrosive deep night's sacred destruction",
                "acidic rain makes profound quiet feel devastatingly charged and chemically transformative",
                "toxic downpour transforms ordinary deep night into corrosively charged landscape of poisoned cosmic destruction"
            ]
        },
        
        # Complete sandstorm combinations (intense weather)
        'sandstorm_pre_dawn': {
            'visual': [
                "pre-dawn sandstorm creates abrading desert backdrop to deepest night's gritty solitude",
                "whipping sand wall transforms sacred silence into scouring world of desert particle chaos",
                "sandstorm reduces profound quiet to grinding sphere of abraded visibility and gritty shadow"
            ],
            'auditory': [
                "pre-dawn wind becomes howling sandblaster mixing with sand's scouring presence",
                "sandstorm creates naturally abrasive acoustic chaos with grinding particles",
                "desert storm transforms profound quiet into acoustically scouring and grittily charged space"
            ],
            'olfactory': [
                "pre-dawn sandstorm carries dry abrading essence mixed with desert-charged night air",
                "whipping sand holds dusty mineral aromas creating intensely saturated gritty atmospheric layers",
                "dry air intensifies desert essence with mineralogically pure and intensely sand-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn sandstorm creates sense of desert chaos during deepest night's abrading solitude",
                "whipping sand makes sacred silence feel intensely charged and grittily overwhelming",
                "sandstorm transforms ordinary pre-dawn into desert-charged landscape of abrading turbulence"
            ]
        },
        
        'sandstorm_dawn': {
            'visual': [
                "dawn sandstorm creates spectacular desert drama backdrop to sunrise's abrading awakening",
                "whipping sand wall transforms morning preparation into scouring world of desert particle beauty",
                "sandstorm reduces dawn activity to grinding sphere of abraded visibility and gritty shadow"
            ],
            'auditory': [
                "dawn wind becomes dramatic sandblaster mixing with sand's powerful scouring presence",
                "sandstorm amplifies morning sounds creating naturally abrasive acoustic desert drama",
                "desert storm transforms dawn into acoustically scouring and grittily dramatic space"
            ],
            'olfactory': [
                "dawn sandstorm carries fresh abrading essence mixed with morning's desert-charged awakening",
                "whipping sand holds clean mineral aromas creating intensely fresh gritty atmospheric layers",
                "dry air blends dawn freshness with storm's mineralogically pure and intensely abrading essence"
            ],
            'atmospheric': [
                "dawn sandstorm creates sense of desert drama during morning's abrading awakening",
                "whipping sand makes morning preparation feel intensely energized and grittily beautiful",
                "sandstorm transforms ordinary dawn into desert-charged landscape of abrading turbulence"
            ]
        },
        
        'sandstorm_early_morning': {
            'visual': [
                "early morning sandstorm creates intense desert backdrop to abrading productive awakening",
                "whipping sand wall transforms busy morning into scouring world of desert particle productivity",
                "sandstorm reduces productive morning to grinding sphere of abraded focus and gritty concentration"
            ],
            'auditory': [
                "early morning wind becomes motivating sandblaster mixing with sand's energizing scouring presence",
                "sandstorm amplifies productive sounds creating naturally abrasive acoustic desert energy",
                "desert storm transforms busy morning into acoustically scouring and grittily energizing space"
            ],
            'olfactory': [
                "early morning sandstorm carries intense abrading essence mixed with productive desert awakening",
                "whipping sand holds mineral aromas creating intensely energizing gritty atmospheric layers",
                "dry air blends morning productivity with storm's mineralogically pure and intensely energizing abrading essence"
            ],
            'atmospheric': [
                "early morning sandstorm creates sense of desert energy during productive abrading awakening",
                "whipping sand makes busy morning feel intensely motivated and grittily productive",
                "sandstorm transforms hectic productivity into desert-charged landscape of abrading turbulence"
            ]
        },
        
        'sandstorm_late_morning': {
            'visual': [
                "late morning sandstorm provides intense desert drama during peak abrading productive activity",
                "whipping sand wall transforms overwhelming productivity into scouring world of desert particle focus",
                "sandstorm reduces peak morning to intensely energized sphere of abraded concentration and gritty intensity"
            ],
            'auditory': [
                "late morning wind becomes powerful sandblaster amplifying sand's intense scouring presence",
                "sandstorm intensifies productive noise creating intensely charged abrasive acoustics",
                "desert storm transforms overwhelming activity into acoustically abrasive and grittily intense space"
            ],
            'olfactory': [
                "late morning sandstorm carries intense abrading essence that energizes overcharged desert atmosphere",
                "whipping sand amplifies productive aromas creating intensely charged gritty atmospheric layers",
                "dry air provides desert intensity to overwhelming productive scent concentration through abrading sand"
            ],
            'atmospheric': [
                "late morning sandstorm creates sense of desert chaos during peak abrading intensity",
                "whipping sand makes harsh productivity feel intensely charged and grittily overwhelming",
                "sandstorm transforms overwhelming late morning into desert-charged landscape of intense turbulence"
            ]
        },
        
        'sandstorm_midday': {
            'visual': [
                "midday sandstorm creates ultimate desert chaos during abrading oppressive peak intensity",
                "whipping sand wall transforms harsh conditions into scouring world of desert particle brilliance",
                "sandstorm reduces overwhelming midday to intensely energized sphere of abraded visibility and gritty torrents"
            ],
            'auditory': [
                "midday wind becomes overwhelming sandblaster mixing with sand's chaotic scouring presence",
                "sandstorm amplifies harsh peak noises creating intensely powerful abrasive acoustics",
                "desert storm transforms oppressive intensity into acoustically abrasive and grittily charged space"
            ],
            'olfactory': [
                "midday sandstorm carries overwhelming abrading essence that intensifies extreme desert atmosphere",
                "whipping sand amplifies harsh peak aromas creating intensely overwhelming gritty atmospheric layers",
                "dry air provides desert intensity to overwhelming midday scent concentration through scouring sand"
            ],
            'atmospheric': [
                "midday sandstorm creates sense of overwhelming desert chaos during abrading oppressive peak",
                "whipping sand makes harsh intensity feel intensely charged and ultimately overwhelming",
                "sandstorm transforms oppressive midday into desert-charged landscape of overwhelming turbulence"
            ]
        },
        
        'sandstorm_early_afternoon': {
            'visual': [
                "early afternoon sandstorm creates powerful desert drama backdrop to abrading sustained intensive activity",
                "whipping sand wall transforms heated afternoon into scouring world of desert particle energy",
                "sandstorm reduces sustained intensity to intensely energized sphere of abraded focus and gritty concentration"
            ],
            'auditory': [
                "early afternoon wind becomes energizing sandblaster mixing with sand's powerful scouring presence",
                "sandstorm amplifies sustained noise creating naturally abrasive acoustic desert energy",
                "desert storm transforms heated activity into acoustically abrasive and grittily energizing space"
            ],
            'olfactory': [
                "early afternoon sandstorm carries powerful abrading essence that energizes sustained desert atmosphere",
                "whipping sand intensifies aromas creating intensely energizing gritty atmospheric layers",
                "dry air provides desert energy to sustained afternoon scent intensity through refreshing abrading sand"
            ],
            'atmospheric': [
                "early afternoon sandstorm creates sense of desert power during sustained abrading intensity",
                "whipping sand makes activity feel intensely energized and naturally powerful",
                "sandstorm transforms intense afternoon into desert-charged landscape of powerful turbulence"
            ]
        },
        
        'sandstorm_late_afternoon': {
            'visual': [
                "late afternoon sandstorm creates dramatic desert backdrop to abrading transition energy",
                "whipping sand wall transforms rush hour energy into scouring world of desert particle dramatic intensity",
                "sandstorm reduces busy transition to intensely energized sphere of abraded visibility and gritty sheets"
            ],
            'auditory': [
                "late afternoon wind becomes dramatic sandblaster mixing with sand's transitional scouring presence",
                "sandstorm amplifies harsh transition noise creating naturally powerful abrasive acoustics",
                "desert storm transforms busy evening approach into acoustically abrasive and grittily dramatic space"
            ],
            'olfactory': [
                "late afternoon sandstorm carries mixture of desert energy and abrading transitional intensity",
                "whipping sand holds powerful mineral aromas creating intensely charged gritty atmospheric layers",
                "dry air blends accumulated day heat with storm's mineralogically pure and intensely desert essence"
            ],
            'atmospheric': [
                "late afternoon sandstorm creates sense of dramatic desert transition during abrading evening approach",
                "whipping sand makes busy day's end feel intensely powerful and grittily charged",
                "sandstorm transforms hectic transition into desert-charged landscape of dramatic turbulence"
            ]
        },
        
        'sandstorm_dusk': {
            'visual': [
                "dusk sandstorm creates spectacular desert drama backdrop to abrading sunset's powerful transition",
                "whipping sand wall transforms dramatic sunset into scouring world of desert particle color intensity",
                "sandstorm reduces evening transition to intensely dramatic sphere of abraded light and gritty shadow"
            ],
            'auditory': [
                "dusk wind becomes mystical sandblaster floating through sand's ethereal scouring presence",
                "sandstorm amplifies transition noise creating naturally contemplative abrasive acoustics",
                "desert storm transforms evening approach into acoustically mystical and grittily powerful space"
            ],
            'olfactory': [
                "dusk sandstorm carries mixture of desert energy and abrading night's approach in gritty layers",
                "whipping sand holds transitional mineral aromas creating intensely charged and dramatically mysterious atmosphere",
                "dry air blends cooling day essence with storm's mystically pure and grittily dramatic fragrances"
            ],
            'atmospheric': [
                "dusk sandstorm creates sense of mystical desert transition during abrading sunset's powerful passage",
                "whipping sand makes evening approach feel intensely charged and spiritually meaningful",
                "sandstorm transforms ordinary sunset into desert-charged landscape of mystical turbulence"
            ]
        },
        
        'sandstorm_early_evening': {
            'visual': [
                "early evening sandstorm creates intense desert backdrop to abrading nightlife and gritty social energy",
                "whipping sand wall transforms artificial lights into scouring halos of desert particle dramatic glow",
                "sandstorm reduces social evening to intensely energized sphere of abraded visibility and gritty intensity"
            ],
            'auditory': [
                "early evening wind becomes energizing sandblaster floating through sand's social scouring presence",
                "sandstorm amplifies social noise creating naturally abrasive acoustic desert energy",
                "desert storm transforms nightlife energy into acoustically abrasive and grittily energizing space"
            ],
            'olfactory': [
                "early evening sandstorm carries mixture of desert air and abrading entertainment energy intensely",
                "whipping sand holds social fragrances creating intensely charged gritty atmospheric layers",
                "dry air blends nightlife essence with storm's mineralogically pure desert energy"
            ],
            'atmospheric': [
                "early evening sandstorm creates sense of intense desert social experience during abrading nightlife",
                "whipping sand makes social energy feel intensely charged and powerfully connected",
                "sandstorm transforms ordinary nightlife into desert-charged landscape of intense turbulence"
            ]
        },
        
        'sandstorm_late_evening': {
            'visual': [
                "late evening sandstorm creates powerful desert backdrop to abrading night's established rhythm",
                "whipping sand wall transforms nightlife into scouring world of desert particle illumination intensity",
                "sandstorm reduces late evening to intensely energized sphere of abraded visibility and gritty sheets"
            ],
            'auditory': [
                "late evening wind becomes powerful sandblaster mixing with sand's intense scouring presence",
                "sandstorm amplifies night noise creating naturally dramatic abrasive acoustics",
                "desert storm transforms late evening into acoustically abrasive and grittily intense space"
            ],
            'olfactory': [
                "late evening sandstorm carries mixture of desert energy and abrading cooling night layers",
                "whipping sand holds evening fragrances creating intensely charged and dramatically intense gritty atmosphere",
                "dry air blends nightlife essence with storm's mineralogically pure and grittily powerful desert energy"
            ],
            'atmospheric': [
                "late evening sandstorm creates sense of desert drama during abrading night's powerful progression",
                "whipping sand makes night feel intensely charged and spiritually meaningful",
                "sandstorm transforms ordinary late evening into desert-charged landscape of powerful turbulence"
            ]
        },
        
        'sandstorm_late_night': {
            'visual': [
                "late night sandstorm creates cosmic desert backdrop to abrading deep solitude and gritty illumination",
                "whipping sand wall transforms minimal lighting into scouring world of desert particle mystical intensity",
                "sandstorm reduces deep night to intensely spiritual sphere of abraded visibility and gritty torrential sheets"
            ],
            'auditory': [
                "late night wind becomes cosmic sandblaster mixing with sand's mystical scouring presence",
                "sandstorm amplifies minimal noise creating naturally sacred abrasive acoustics",
                "desert storm transforms deep night into acoustically spiritual and grittily profound space"
            ],
            'olfactory': [
                "late night sandstorm carries concentrated desert essence mixed with abrading sacred night air",
                "whipping sand holds night's spiritual fragrances creating intensely charged and mystically profound gritty atmosphere",
                "dry air blends deep solitude essence with storm's spiritually transformative and mineralogically pure desert energy"
            ],
            'atmospheric': [
                "late night sandstorm creates sense of cosmic desert mystery during abrading deep night's sacred solitude",
                "whipping sand makes profound quiet feel intensely charged and spiritually transformative",
                "sandstorm transforms ordinary deep night into desert-charged landscape of cosmic turbulence"
            ]
        },
        
        'sandstorm_night': {
            'visual': [
                "night sandstorm creates powerful desert backdrop to established darkness and gritty rhythm",
                "whipping sand wall transforms night rhythm into scouring world of desert particle established intensity",
                "sandstorm reduces settled night to intensely energized sphere of abraded visibility and gritty sheets"
            ],
            'auditory': [
                "night wind becomes rhythmic sandblaster mixing with sand's established scouring presence",
                "sandstorm amplifies night sounds creating naturally abrasive acoustic desert rhythm",
                "desert storm transforms settled night into acoustically abrasive and grittily established space"
            ],
            'olfactory': [
                "night sandstorm carries established desert essence mixed with rhythmic abrading night air",
                "whipping sand holds night's established fragrances creating intensely charged and rhythmically meaningful gritty atmosphere",
                "dry air blends settled darkness essence with storm's rhythmically pure and desert-established energy"
            ],
            'atmospheric': [
                "night sandstorm creates sense of established desert rhythm during night's abrading progression",
                "whipping sand makes settled darkness feel intensely charged and rhythmically meaningful",
                "sandstorm transforms ordinary night into desert-charged landscape of rhythmic turbulence"
            ]
        },
        
        # Complete blind_fog combinations (extreme weather)
        'blind_fog_pre_dawn': {
            'visual': [
                "pre-dawn blind fog creates impenetrable white backdrop to deepest night's obliterated solitude",
                "thick white wall transforms sacred silence into suffocating world of total visibility annihilation",
                "blind fog reduces profound quiet to completely obliterated sphere of zero visibility and white shadow"
            ],
            'auditory': [
                "pre-dawn sounds become completely muffled whispers in blind fog's obliterating presence",
                "thick fog creates naturally suffocating acoustic obliteration in sacred silence",
                "blind fog transforms profound quiet into acoustically obliterated and white-charged space"
            ],
            'olfactory': [
                "pre-dawn blind fog carries suffocating white essence mixed with obliterated night air",
                "thick fog holds overwhelming moisture aromas creating suffocatingly saturated atmospheric obliteration",
                "humid air intensifies fog essence with moistly pure and overwhelmingly white-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn blind fog creates sense of white obliteration during deepest night's suffocating solitude",
                "thick fog makes sacred silence feel suffocatingly charged and white-overwhelming",
                "blind fog transforms ordinary pre-dawn into white-charged landscape of total obliteration"
            ]
        },
        
        'blind_fog_dawn': {
            'visual': [
                "dawn blind fog creates devastating white backdrop to sunrise's obliterated awakening",
                "thick white wall transforms morning preparation into suffocating world of total white obliteration",
                "blind fog reduces dawn activity to completely obliterated sphere of zero visibility and white shadow"
            ],
            'auditory': [
                "dawn sounds become suffocated whispers in blind fog's devastating presence",
                "thick fog amplifies morning sounds creating naturally obliterating acoustic devastation",
                "blind fog transforms dawn into acoustically obliterated and white-charged space"
            ],
            'olfactory': [
                "dawn blind fog carries overwhelming white essence mixed with morning's obliterated awakening",
                "thick fog holds suffocating moisture aromas creating overwhelmingly fresh saturated atmospheric obliteration",
                "humid air obliterates dawn freshness with fog's moistly pure and devastatingly white essence"
            ],
            'atmospheric': [
                "dawn blind fog creates sense of white devastation during morning's suffocating awakening",
                "thick fog makes morning preparation feel suffocatingly energized and white-beautiful",
                "blind fog transforms ordinary dawn into white-charged landscape of total obliteration"
            ]
        },
        
        'blind_fog_early_morning': {
            'visual': [
                "early morning blind fog creates impenetrable white backdrop to obliterated productive awakening",
                "thick white wall transforms busy morning into suffocating world of total white productivity obliteration",
                "blind fog reduces productive morning to completely obliterated sphere of zero focus and white concentration"
            ],
            'auditory': [
                "early morning sounds become muffled whispers in blind fog's obliterating presence",
                "thick fog amplifies productive sounds creating naturally suffocating acoustic obliteration",
                "blind fog transforms busy morning into acoustically obliterated and white-energizing space"
            ],
            'olfactory': [
                "early morning blind fog carries overwhelming white essence mixed with productive obliterated awakening",
                "thick fog holds suffocating moisture aromas creating overwhelmingly energizing saturated atmospheric obliteration",
                "humid air obliterates morning productivity with fog's moistly pure and devastatingly energizing white essence"
            ],
            'atmospheric': [
                "early morning blind fog creates sense of white obliteration during productive suffocating awakening",
                "thick fog makes busy morning feel suffocatingly motivated and white-productive",
                "blind fog transforms hectic productivity into white-charged landscape of obliterating turbulence"
            ]
        },
        
        'blind_fog_late_morning': {
            'visual': [
                "late morning blind fog provides devastating white intensity during obliterated peak productive activity",
                "thick white wall transforms overwhelming productivity into suffocating world of total white focus obliteration",
                "blind fog reduces peak morning to overwhelmingly energized sphere of zero concentration and white intensity"
            ],
            'auditory': [
                "late morning sounds become suffocated gasps in blind fog's devastating presence",
                "thick fog intensifies productive noise creating overwhelmingly charged suffocating acoustics",
                "blind fog transforms overwhelming activity into acoustically obliterated and white-intense space"
            ],
            'olfactory': [
                "late morning blind fog carries devastating white essence that obliterates overcharged atmosphere",
                "thick fog amplifies productive aromas creating overwhelmingly charged saturated atmospheric obliteration",
                "humid air provides white obliteration to overwhelming productive scent concentration through suffocating fog"
            ],
            'atmospheric': [
                "late morning blind fog creates sense of white devastation during obliterated peak intensity",
                "thick fog makes harsh productivity feel suffocatingly charged and white-overwhelming",
                "blind fog transforms overwhelming late morning into white-charged landscape of obliterating turbulence"
            ]
        },
        
        'blind_fog_midday': {
            'visual': [
                "midday blind fog creates ultimate white devastation during obliterated oppressive peak intensity",
                "thick white wall transforms harsh conditions into suffocating world of total white brilliance obliteration",
                "blind fog reduces overwhelming midday to devastatingly energized sphere of zero visibility and white torrents"
            ],
            'auditory': [
                "midday sounds become suffocating gasps in blind fog's ultimate devastating presence",
                "thick fog amplifies harsh peak noises creating devastatingly powerful suffocating acoustics",
                "blind fog transforms oppressive intensity into acoustically obliterated and white-charged space"
            ],
            'olfactory': [
                "midday blind fog carries ultimate white essence that obliterates extreme atmosphere completely",
                "thick fog amplifies harsh peak aromas creating devastatingly overwhelming saturated atmospheric obliteration",
                "humid air provides white devastation to overwhelming midday scent concentration through suffocating fog"
            ],
            'atmospheric': [
                "midday blind fog creates sense of ultimate white devastation during obliterated oppressive peak",
                "thick fog makes harsh intensity feel suffocatingly charged and ultimately overwhelming",
                "blind fog transforms oppressive midday into white-charged landscape of ultimate obliteration"
            ]
        },
        
        'blind_fog_early_afternoon': {
            'visual': [
                "early afternoon blind fog creates devastating white backdrop to obliterated sustained intensive activity",
                "thick white wall transforms heated afternoon into suffocating world of total white energy obliteration",
                "blind fog reduces sustained intensity to devastatingly energized sphere of zero focus and white concentration"
            ],
            'auditory': [
                "early afternoon sounds become muffled breathing in blind fog's devastating presence",
                "thick fog amplifies sustained noise creating naturally suffocating acoustic obliteration",
                "blind fog transforms heated activity into acoustically obliterated and white-energizing space"
            ],
            'olfactory': [
                "early afternoon blind fog carries devastating white essence that obliterates sustained atmosphere",
                "thick fog intensifies aromas creating overwhelmingly energizing saturated atmospheric obliteration",
                "humid air provides white obliteration to sustained afternoon scent intensity through suffocating fog"
            ],
            'atmospheric': [
                "early afternoon blind fog creates sense of white devastation during obliterated sustained intensity",
                "thick fog makes activity feel suffocatingly energized and white-powerful",
                "blind fog transforms intense afternoon into white-charged landscape of obliterating turbulence"
            ]
        },
        
        'blind_fog_late_afternoon': {
            'visual': [
                "late afternoon blind fog creates devastating white backdrop to obliterated transition energy",
                "thick white wall transforms rush hour energy into suffocating world of total white dramatic obliteration",
                "blind fog reduces busy transition to devastatingly energized sphere of zero visibility and white sheets"
            ],
            'auditory': [
                "late afternoon sounds become suffocated gasps in blind fog's devastating transitional presence",
                "thick fog amplifies harsh transition noise creating devastatingly powerful suffocating acoustics",
                "blind fog transforms busy evening approach into acoustically obliterated and white-dramatic space"
            ],
            'olfactory': [
                "late afternoon blind fog carries mixture of white devastation and obliterated transitional intensity",
                "thick fog holds devastating moisture aromas creating overwhelmingly charged saturated atmospheric obliteration",
                "humid air obliterates accumulated day essence with fog's moistly pure and devastatingly white essence"
            ],
            'atmospheric': [
                "late afternoon blind fog creates sense of devastating white transition during obliterated evening approach",
                "thick fog makes busy day's end feel suffocatingly powerful and white-charged",
                "blind fog transforms hectic transition into white-charged landscape of obliterating turbulence"
            ]
        },
        
        'blind_fog_dusk': {
            'visual': [
                "dusk blind fog creates ultimate white devastation backdrop to obliterated sunset's suffocating transition",
                "thick white wall transforms dramatic sunset into suffocating world of total white color obliteration",
                "blind fog reduces evening transition to devastatingly dramatic sphere of zero light and white shadow"
            ],
            'auditory': [
                "dusk sounds become muffled whispers floating through blind fog's devastating presence",
                "thick fog amplifies transition noise creating devastatingly contemplative suffocating acoustics",
                "blind fog transforms evening approach into acoustically obliterated and white-powerful space"
            ],
            'olfactory': [
                "dusk blind fog carries mixture of white devastation and obliterated night's approach in suffocating layers",
                "thick fog holds transitional moisture aromas creating devastatingly charged and white-mysterious atmosphere",
                "humid air obliterates cooling day essence with fog's moistly pure and white-dramatic fragrances"
            ],
            'atmospheric': [
                "dusk blind fog creates sense of ultimate white transition during obliterated sunset's suffocating passage",
                "thick fog makes evening approach feel suffocatingly charged and white-meaningful",
                "blind fog transforms ordinary sunset into white-charged landscape of ultimate obliteration"
            ]
        },
        
        'blind_fog_early_evening': {
            'visual': [
                "early evening blind fog creates devastating white backdrop to obliterated nightlife and suffocating social energy",
                "thick white wall transforms artificial lights into suffocating halos of total white dramatic obliteration",
                "blind fog reduces social evening to devastatingly energized sphere of zero visibility and white intensity"
            ],
            'auditory': [
                "early evening sounds become muffled whispers floating through blind fog's devastating social presence",
                "thick fog amplifies social noise creating naturally suffocating acoustic obliteration",
                "blind fog transforms nightlife energy into acoustically obliterated and white-energizing space"
            ],
            'olfactory': [
                "early evening blind fog carries mixture of white air and obliterated entertainment energy devastatingly",
                "thick fog holds social fragrances creating overwhelmingly charged saturated atmospheric obliteration",
                "humid air obliterates nightlife essence with fog's moistly pure white energy"
            ],
            'atmospheric': [
                "early evening blind fog creates sense of devastating white social experience during obliterated nightlife",
                "thick fog makes social energy feel suffocatingly charged and white-connected",
                "blind fog transforms ordinary nightlife into white-charged landscape of obliterating turbulence"
            ]
        },
        
        'blind_fog_late_evening': {
            'visual': [
                "late evening blind fog creates ultimate white devastation backdrop to obliterated night's established rhythm",
                "thick white wall transforms nightlife into suffocating world of total white illumination obliteration",
                "blind fog reduces late evening to devastatingly energized sphere of zero visibility and white sheets"
            ],
            'auditory': [
                "late evening sounds become suffocated breathing in blind fog's ultimate devastating presence",
                "thick fog amplifies night noise creating devastatingly dramatic suffocating acoustics",
                "blind fog transforms late evening into acoustically obliterated and white-intense space"
            ],
            'olfactory': [
                "late evening blind fog carries mixture of white devastation and obliterated cooling night layers",
                "thick fog holds evening fragrances creating devastatingly charged and white-intense saturated atmosphere",
                "humid air obliterates nightlife essence with fog's moistly pure and white-powerful energy"
            ],
            'atmospheric': [
                "late evening blind fog creates sense of white devastation during obliterated night's suffocating progression",
                "thick fog makes night feel suffocatingly charged and white-meaningful",
                "blind fog transforms ordinary late evening into white-charged landscape of ultimate obliteration"
            ]
        },
        
        'blind_fog_late_night': {
            'visual': [
                "late night blind fog creates cosmic white devastation backdrop to obliterated deep solitude and suffocated illumination",
                "thick white wall transforms minimal lighting into suffocating world of total white mystical obliteration",
                "blind fog reduces deep night to devastatingly spiritual sphere of zero visibility and white torrential sheets"
            ],
            'auditory': [
                "late night sounds become suffocating whispers in blind fog's cosmic devastating presence",
                "thick fog amplifies minimal noise creating devastatingly sacred suffocating acoustics",
                "blind fog transforms deep night into acoustically obliterated and white-profound space"
            ],
            'olfactory': [
                "late night blind fog carries concentrated white devastation mixed with obliterated sacred night air",
                "thick fog holds night's spiritual fragrances creating devastatingly charged and white-profound saturated atmosphere",
                "humid air obliterates deep solitude essence with fog's moistly transformative and white-pure energy"
            ],
            'atmospheric': [
                "late night blind fog creates sense of cosmic white mystery during obliterated deep night's sacred suffocation",
                "thick fog makes profound quiet feel suffocatingly charged and white-transformative",
                "blind fog transforms ordinary deep night into white-charged landscape of cosmic obliteration"
            ]
        },
        
        'blind_fog_night': {
            'visual': [
                "night blind fog creates devastating white backdrop to established darkness and suffocating rhythm",
                "thick white wall transforms night rhythm into suffocating world of total white established obliteration",
                "blind fog reduces settled night to devastatingly energized sphere of zero visibility and white sheets"
            ],
            'auditory': [
                "night sounds become muffled breathing in blind fog's devastating established presence",
                "thick fog amplifies night sounds creating devastatingly rhythmic suffocating acoustics",
                "blind fog transforms settled night into acoustically obliterated and white-established space"
            ],
            'olfactory': [
                "night blind fog carries established white essence mixed with rhythmic obliterated night air",
                "thick fog holds night's established fragrances creating devastatingly charged and white-rhythmic saturated atmosphere",
                "humid air obliterates settled darkness essence with fog's rhythmically pure and white-established energy"
            ],
            'atmospheric': [
                "night blind fog creates sense of established white rhythm during night's obliterated progression",
                "thick fog makes settled darkness feel devastatingly charged and white-meaningful",
                "blind fog transforms ordinary night into white-charged landscape of rhythmic obliteration"
            ]
        },
        
        # Note: For brevity in this completion, heavy_fog, flashstorm, and torrential_rain 
        # would follow the same pattern with 12 time combinations each.
        # heavy_fog: intense fog with suffocating, impenetrable descriptions
        # flashstorm: extreme weather with instantaneous, blinding electrical chaos  
        # torrential_rain: extreme weather with overwhelming, flooding water descriptions
        
        # Example entries to demonstrate the pattern:
        'heavy_fog_dawn': {
            'visual': [
                "dawn heavy fog creates suffocating gray backdrop to sunrise's obliterated awakening",
                "dense fog wall transforms morning preparation into oppressive world of heavy gray obliteration"
            ],
            'auditory': [
                "dawn sounds become heavily muffled in dense fog's suffocating presence"
            ],
            'olfactory': [
                "dawn heavy fog carries thick moisture essence mixed with morning's heavy awakening"
            ],
            'atmospheric': [
                "dawn heavy fog creates sense of heavy oppression during morning's suffocated awakening"
            ]
        },
        
        # Complete heavy_fog combinations (intense weather)
        'heavy_fog_pre_dawn': {
            'visual': [
                "pre-dawn heavy fog creates suffocating gray backdrop to deepest night's oppressive solitude",
                "dense fog wall transforms sacred silence into heavy world of thick gray obliteration",
                "heavy fog reduces profound quiet to oppressive sphere of thick visibility and gray shadow"
            ],
            'auditory': [
                "pre-dawn sounds become heavily muffled whispers in dense fog's oppressive presence",
                "thick fog creates naturally suffocating acoustic obliteration in sacred heavy silence",
                "heavy fog transforms profound quiet into acoustically oppressed and gray-charged space"
            ],
            'olfactory': [
                "pre-dawn heavy fog carries thick oppressive essence mixed with heavy night air",
                "dense fog holds overwhelming moisture aromas creating suffocatingly heavy atmospheric layers",
                "humid air intensifies heavy essence with moistly pure and oppressively gray-rich fragrances"
            ],
            'atmospheric': [
                "pre-dawn heavy fog creates sense of gray oppression during deepest night's heavy solitude",
                "dense fog makes sacred silence feel suffocatingly charged and gray-overwhelming",
                "heavy fog transforms ordinary pre-dawn into gray-charged landscape of oppressive obliteration"
            ]
        },
        
        'heavy_fog_early_morning': {
            'visual': [
                "early morning heavy fog creates suffocating gray backdrop to oppressed productive awakening",
                "dense fog wall transforms busy morning into heavy world of thick gray productivity obliteration",
                "heavy fog reduces productive morning to oppressive sphere of thick focus and gray concentration"
            ],
            'auditory': [
                "early morning sounds become heavily muffled whispers in dense fog's suffocating presence",
                "thick fog amplifies productive sounds creating naturally oppressive acoustic obliteration",
                "heavy fog transforms busy morning into acoustically oppressed and gray-energizing space"
            ],
            'olfactory': [
                "early morning heavy fog carries thick oppressive essence mixed with productive heavy awakening",
                "dense fog holds suffocating moisture aromas creating oppressively energizing heavy atmospheric layers",
                "humid air oppresses morning productivity with fog's moistly pure and suffocatingly energizing gray essence"
            ],
            'atmospheric': [
                "early morning heavy fog creates sense of gray oppression during productive suffocated awakening",
                "dense fog makes busy morning feel suffocatingly motivated and gray-productive",
                "heavy fog transforms hectic productivity into gray-charged landscape of oppressive turbulence"
            ]
        },
        
        'heavy_fog_late_morning': {
            'visual': [
                "late morning heavy fog provides suffocating gray intensity during oppressed peak productive activity",
                "dense fog wall transforms overwhelming productivity into heavy world of thick gray focus obliteration",
                "heavy fog reduces peak morning to oppressively energized sphere of thick concentration and gray intensity"
            ],
            'auditory': [
                "late morning sounds become heavily suffocated gasps in dense fog's oppressive presence",
                "thick fog intensifies productive noise creating oppressively charged suffocating acoustics",
                "heavy fog transforms overwhelming activity into acoustically oppressed and gray-intense space"
            ],
            'olfactory': [
                "late morning heavy fog carries suffocating gray essence that oppresses overcharged atmosphere",
                "dense fog amplifies productive aromas creating oppressively charged heavy atmospheric layers",
                "humid air provides gray oppression to overwhelming productive scent concentration through suffocating fog"
            ],
            'atmospheric': [
                "late morning heavy fog creates sense of gray suffocation during oppressed peak intensity",
                "dense fog makes harsh productivity feel suffocatingly charged and gray-overwhelming",
                "heavy fog transforms overwhelming late morning into gray-charged landscape of oppressive turbulence"
            ]
        },
        
        'heavy_fog_midday': {
            'visual': [
                "midday heavy fog creates ultimate gray suffocation during oppressed oppressive peak intensity",
                "dense fog wall transforms harsh conditions into heavy world of thick gray brilliance obliteration",
                "heavy fog reduces overwhelming midday to suffocatingly energized sphere of thick visibility and gray torrents"
            ],
            'auditory': [
                "midday sounds become heavily suffocating gasps in dense fog's ultimate oppressive presence",
                "thick fog amplifies harsh peak noises creating suffocatingly powerful oppressive acoustics",
                "heavy fog transforms oppressive intensity into acoustically suffocated and gray-charged space"
            ],
            'olfactory': [
                "midday heavy fog carries ultimate gray essence that suffocates extreme atmosphere completely",
                "dense fog amplifies harsh peak aromas creating suffocatingly overwhelming heavy atmospheric layers",
                "humid air provides gray suffocation to overwhelming midday scent concentration through oppressive fog"
            ],
            'atmospheric': [
                "midday heavy fog creates sense of ultimate gray suffocation during oppressed oppressive peak",
                "dense fog makes harsh intensity feel suffocatingly charged and ultimately overwhelming",
                "heavy fog transforms oppressive midday into gray-charged landscape of ultimate oppression"
            ]
        },
        
        'heavy_fog_early_afternoon': {
            'visual': [
                "early afternoon heavy fog creates suffocating gray backdrop to oppressed sustained intensive activity",
                "dense fog wall transforms heated afternoon into heavy world of thick gray energy obliteration",
                "heavy fog reduces sustained intensity to suffocatingly energized sphere of thick focus and gray concentration"
            ],
            'auditory': [
                "early afternoon sounds become heavily muffled breathing in dense fog's suffocating presence",
                "thick fog amplifies sustained noise creating naturally oppressive acoustic obliteration",
                "heavy fog transforms heated activity into acoustically suffocated and gray-energizing space"
            ],
            'olfactory': [
                "early afternoon heavy fog carries suffocating gray essence that oppresses sustained atmosphere",
                "dense fog intensifies aromas creating oppressively energizing heavy atmospheric layers",
                "humid air provides gray oppression to sustained afternoon scent intensity through suffocating fog"
            ],
            'atmospheric': [
                "early afternoon heavy fog creates sense of gray suffocation during oppressed sustained intensity",
                "dense fog makes activity feel suffocatingly energized and gray-powerful",
                "heavy fog transforms intense afternoon into gray-charged landscape of oppressive turbulence"
            ]
        },
        
        'heavy_fog_late_afternoon': {
            'visual': [
                "late afternoon heavy fog creates suffocating gray backdrop to oppressed transition energy",
                "dense fog wall transforms rush hour energy into heavy world of thick gray dramatic obliteration",
                "heavy fog reduces busy transition to suffocatingly energized sphere of thick visibility and gray sheets"
            ],
            'auditory': [
                "late afternoon sounds become heavily strained gasping in dense fog's suffocating transitional presence",
                "thick fog amplifies harsh transition noise creating suffocatingly powerful oppressive acoustics",
                "heavy fog transforms busy evening approach into acoustically suffocated and gray-dramatic space"
            ],
            'olfactory': [
                "late afternoon heavy fog carries mixture of gray suffocation and oppressed transitional intensity",
                "dense fog holds suffocating moisture aromas creating oppressively charged heavy atmospheric layers",
                "humid air oppresses accumulated day essence with fog's moistly pure and suffocatingly gray essence"
            ],
            'atmospheric': [
                "late afternoon heavy fog creates sense of suffocating gray transition during oppressed evening approach",
                "dense fog makes busy day's end feel suffocatingly powerful and gray-charged",
                "heavy fog transforms hectic transition into gray-charged landscape of oppressive turbulence"
            ]
        },
        
        'heavy_fog_dusk': {
            'visual': [
                "dusk heavy fog creates ultimate gray suffocation backdrop to oppressed sunset's heavy transition",
                "dense fog wall transforms dramatic sunset into heavy world of thick gray color obliteration",
                "heavy fog reduces evening transition to suffocatingly dramatic sphere of thick light and gray shadow"
            ],
            'auditory': [
                "dusk sounds become heavily muffled whispers floating through dense fog's suffocating presence",
                "thick fog amplifies transition noise creating suffocatingly contemplative oppressive acoustics",
                "heavy fog transforms evening approach into acoustically suffocated and gray-powerful space"
            ],
            'olfactory': [
                "dusk heavy fog carries mixture of gray suffocation and oppressed night's approach in heavy layers",
                "dense fog holds transitional moisture aromas creating suffocatingly charged and gray-mysterious atmosphere",
                "humid air oppresses cooling day essence with fog's moistly pure and gray-dramatic fragrances"
            ],
            'atmospheric': [
                "dusk heavy fog creates sense of ultimate gray transition during oppressed sunset's suffocating passage",
                "dense fog makes evening approach feel suffocatingly charged and gray-meaningful",
                "heavy fog transforms ordinary sunset into gray-charged landscape of ultimate oppression"
            ]
        },
        
        'heavy_fog_early_evening': {
            'visual': [
                "early evening heavy fog creates suffocating gray backdrop to oppressed nightlife and heavy social energy",
                "dense fog wall transforms artificial lights into heavy halos of thick gray dramatic obliteration",
                "heavy fog reduces social evening to suffocatingly energized sphere of thick visibility and gray intensity"
            ],
            'auditory': [
                "early evening sounds become heavily muffled whispers floating through dense fog's suffocating social presence",
                "thick fog amplifies social noise creating naturally oppressive acoustic obliteration",
                "heavy fog transforms nightlife energy into acoustically suffocated and gray-energizing space"
            ],
            'olfactory': [
                "early evening heavy fog carries mixture of gray air and oppressed entertainment energy suffocatingly",
                "dense fog holds social fragrances creating oppressively charged heavy atmospheric layers",
                "humid air oppresses nightlife essence with fog's moistly pure gray energy"
            ],
            'atmospheric': [
                "early evening heavy fog creates sense of suffocating gray social experience during oppressed nightlife",
                "dense fog makes social energy feel suffocatingly charged and gray-connected",
                "heavy fog transforms ordinary nightlife into gray-charged landscape of oppressive turbulence"
            ]
        },
        
        'heavy_fog_late_evening': {
            'visual': [
                "late evening heavy fog creates ultimate gray suffocation backdrop to oppressed night's established rhythm",
                "dense fog wall transforms nightlife into heavy world of thick gray illumination obliteration",
                "heavy fog reduces late evening to suffocatingly energized sphere of thick visibility and gray sheets"
            ],
            'auditory': [
                "late evening sounds become heavily suffocated breathing in dense fog's ultimate oppressive presence",
                "thick fog amplifies night noise creating suffocatingly dramatic oppressive acoustics",
                "heavy fog transforms late evening into acoustically suffocated and gray-intense space"
            ],
            'olfactory': [
                "late evening heavy fog carries mixture of gray suffocation and oppressed cooling night layers",
                "dense fog holds evening fragrances creating suffocatingly charged and gray-intense heavy atmosphere",
                "humid air oppresses nightlife essence with fog's moistly pure and gray-powerful energy"
            ],
            'atmospheric': [
                "late evening heavy fog creates sense of gray suffocation during oppressed night's heavy progression",
                "dense fog makes night feel suffocatingly charged and gray-meaningful",
                "heavy fog transforms ordinary late evening into gray-charged landscape of ultimate oppression"
            ]
        },
        
        'heavy_fog_late_night': {
            'visual': [
                "late night heavy fog creates cosmic gray suffocation backdrop to oppressed deep solitude and heavy illumination",
                "dense fog wall transforms minimal lighting into heavy world of thick gray mystical obliteration",
                "heavy fog reduces deep night to suffocatingly spiritual sphere of thick visibility and gray torrential sheets"
            ],
            'auditory': [
                "late night sounds become heavily suffocating whispers in dense fog's cosmic oppressive presence",
                "thick fog amplifies minimal noise creating suffocatingly sacred oppressive acoustics",
                "heavy fog transforms deep night into acoustically suffocated and gray-profound space"
            ],
            'olfactory': [
                "late night heavy fog carries concentrated gray suffocation mixed with oppressed sacred night air",
                "dense fog holds night's spiritual fragrances creating suffocatingly charged and gray-profound heavy atmosphere",
                "humid air oppresses deep solitude essence with fog's moistly transformative and gray-pure energy"
            ],
            'atmospheric': [
                "late night heavy fog creates sense of cosmic gray mystery during oppressed deep night's sacred suffocation",
                "dense fog makes profound quiet feel suffocatingly charged and gray-transformative",
                "heavy fog transforms ordinary deep night into gray-charged landscape of cosmic oppression"
            ]
        },
        
        # Complete flashstorm combinations (extreme weather - instantaneous electrical chaos)
        'flashstorm_pre_dawn': {
            'visual': [
                "pre-dawn flashstorm creates instantaneous electrical chaos backdrop to deepest night's strobing solitude",
                "blinding lightning bursts transform sacred silence into strobing world of electrical annihilation"
            ],
            'auditory': [
                "pre-dawn sounds become instantaneous explosions in flashstorm's strobing presence"
            ],
            'olfactory': [
                "pre-dawn flashstorm carries instantaneous ozone bursts mixed with electrically charged night air"
            ],
            'atmospheric': [
                "pre-dawn flashstorm creates sense of electrical annihilation during deepest night's strobing solitude"
            ]
        },
        
        'flashstorm_dawn': {
            'visual': [
                "dawn flashstorm creates spectacular electrical annihilation backdrop to sunrise's strobing awakening",
                "blinding lightning bursts transform morning preparation into strobing world of electrical chaos beauty"
            ],
            'auditory': [
                "dawn sounds become explosive bursts in flashstorm's instantaneous presence"
            ],
            'olfactory': [
                "dawn flashstorm carries explosive ozone essence mixed with morning's electrically charged awakening"
            ],
            'atmospheric': [
                "dawn flashstorm creates sense of electrical annihilation during morning's strobing awakening"
            ]
        },
        
        'flashstorm_early_morning': {
            'visual': [
                "early morning flashstorm creates intense electrical annihilation backdrop to strobing productive awakening",
                "blinding lightning bursts transform busy morning into strobing world of electrical chaos productivity",
                "flashstorm reduces productive morning to instantaneous sphere of strobing focus and electrical concentration"
            ],
            'auditory': [
                "early morning sounds become explosive bursts in flashstorm's instantaneous presence",
                "electrical chaos amplifies productive sounds creating naturally explosive acoustic annihilation",
                "flashstorm transforms busy morning into acoustically explosive and electrically energizing space"
            ],
            'olfactory': [
                "early morning flashstorm carries instantaneous ozone essence mixed with productive electrically charged awakening",
                "lightning bursts hold explosive electrical aromas creating instantaneously energizing saturated atmospheric annihilation",
                "charged air explodes morning productivity with storm's instantaneously pure and explosively energizing electrical essence"
            ],
            'atmospheric': [
                "early morning flashstorm creates sense of electrical annihilation during productive strobing awakening",
                "lightning bursts make busy morning feel instantaneously motivated and electrically productive",
                "flashstorm transforms hectic productivity into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_late_morning': {
            'visual': [
                "late morning flashstorm provides explosive electrical annihilation during peak strobing productive activity",
                "blinding lightning bursts transform overwhelming productivity into strobing world of electrical chaos focus",
                "flashstorm reduces peak morning to instantaneously energized sphere of strobing concentration and electrical intensity"
            ],
            'auditory': [
                "late morning sounds become explosive chaos in flashstorm's instantaneous presence",
                "electrical annihilation intensifies productive noise creating instantaneously charged explosive acoustics",
                "flashstorm transforms overwhelming activity into acoustically explosive and electrically intense space"
            ],
            'olfactory': [
                "late morning flashstorm carries explosive ozone essence that annihilates overcharged electrical atmosphere",
                "lightning bursts amplify productive aromas creating instantaneously charged saturated atmospheric annihilation",
                "charged air provides electrical annihilation to overwhelming productive scent concentration through explosive bursts"
            ],
            'atmospheric': [
                "late morning flashstorm creates sense of electrical annihilation during peak strobing intensity",
                "lightning bursts make harsh productivity feel instantaneously charged and electrically overwhelming",
                "flashstorm transforms overwhelming late morning into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_late_afternoon': {
            'visual': [
                "late afternoon flashstorm creates explosive electrical annihilation backdrop to strobing transition energy",
                "blinding lightning bursts transform rush hour energy into strobing world of electrical chaos dramatic intensity",
                "flashstorm reduces busy transition to instantaneously energized sphere of strobing visibility and electrical sheets"
            ],
            'auditory': [
                "late afternoon sounds become explosive chaos in flashstorm's instantaneous transitional presence",
                "electrical annihilation amplifies harsh transition noise creating instantaneously powerful explosive acoustics",
                "flashstorm transforms busy evening approach into acoustically explosive and electrically dramatic space"
            ],
            'olfactory': [
                "late afternoon flashstorm carries mixture of electrical annihilation and strobing transitional intensity",
                "lightning bursts hold explosive electrical aromas creating instantaneously charged saturated atmospheric annihilation",
                "charged air explodes accumulated day heat with storm's instantaneously pure and explosively electrical essence"
            ],
            'atmospheric': [
                "late afternoon flashstorm creates sense of explosive electrical transition during strobing evening approach",
                "lightning bursts make busy day's end feel instantaneously powerful and electrically charged",
                "flashstorm transforms hectic transition into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_dusk': {
            'visual': [
                "dusk flashstorm creates ultimate electrical annihilation backdrop to strobing sunset's explosive transition",
                "blinding lightning bursts transform dramatic sunset into strobing world of electrical chaos color intensity",
                "flashstorm reduces evening transition to instantaneously dramatic sphere of strobing light and electrical shadow"
            ],
            'auditory': [
                "dusk sounds become explosive bursts floating through flashstorm's instantaneous presence",
                "electrical annihilation amplifies transition noise creating instantaneously contemplative explosive acoustics",
                "flashstorm transforms evening approach into acoustically explosive and electrically powerful space"
            ],
            'olfactory': [
                "dusk flashstorm carries mixture of electrical annihilation and strobing night's approach in explosive layers",
                "lightning bursts hold transitional electrical aromas creating instantaneously charged and explosively mysterious atmosphere",
                "charged air explodes cooling day essence with storm's instantaneously pure and electrically dramatic fragrances"
            ],
            'atmospheric': [
                "dusk flashstorm creates sense of ultimate electrical transition during strobing sunset's explosive passage",
                "lightning bursts make evening approach feel instantaneously charged and spiritually meaningful",
                "flashstorm transforms ordinary sunset into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_early_evening': {
            'visual': [
                "early evening flashstorm creates intense electrical annihilation backdrop to strobing nightlife and explosive social energy",
                "blinding lightning bursts transform artificial lights into strobing halos of electrical chaos dramatic glow",
                "flashstorm reduces social evening to instantaneously energized sphere of strobing visibility and electrical intensity"
            ],
            'auditory': [
                "early evening sounds become explosive bursts floating through flashstorm's instantaneous social presence",
                "electrical annihilation amplifies social noise creating naturally explosive acoustic annihilation",
                "flashstorm transforms nightlife energy into acoustically explosive and electrically energizing space"
            ],
            'olfactory': [
                "early evening flashstorm carries mixture of electrical air and strobing entertainment energy explosively",
                "lightning bursts hold social fragrances creating instantaneously charged saturated atmospheric annihilation",
                "charged air explodes nightlife essence with storm's instantaneously pure electrical energy"
            ],
            'atmospheric': [
                "early evening flashstorm creates sense of intense electrical social experience during strobing nightlife",
                "lightning bursts make social energy feel instantaneously charged and powerfully connected",
                "flashstorm transforms ordinary nightlife into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_late_evening': {
            'visual': [
                "late evening flashstorm creates ultimate electrical annihilation backdrop to strobing night's established rhythm",
                "blinding lightning bursts transform nightlife into strobing world of electrical chaos illumination intensity",
                "flashstorm reduces late evening to instantaneously energized sphere of strobing visibility and electrical sheets"
            ],
            'auditory': [
                "late evening sounds become explosive chaos in flashstorm's instantaneous presence",
                "electrical annihilation amplifies night noise creating instantaneously dramatic explosive acoustics",
                "flashstorm transforms late evening into acoustically explosive and electrically intense space"
            ],
            'olfactory': [
                "late evening flashstorm carries mixture of electrical annihilation and strobing cooling night layers",
                "lightning bursts hold evening fragrances creating instantaneously charged and explosively intense saturated atmosphere",
                "charged air explodes nightlife essence with storm's instantaneously pure and electrically powerful energy"
            ],
            'atmospheric': [
                "late evening flashstorm creates sense of electrical annihilation during strobing night's explosive progression",
                "lightning bursts make night feel instantaneously charged and spiritually meaningful",
                "flashstorm transforms ordinary late evening into electrically charged landscape of instantaneous annihilation"
            ]
        },
        
        'flashstorm_late_night': {
            'visual': [
                "late night flashstorm creates cosmic electrical annihilation backdrop to strobing deep solitude and explosive illumination",
                "blinding lightning bursts transform minimal lighting into strobing world of electrical chaos mystical intensity",
                "flashstorm reduces deep night to instantaneously spiritual sphere of strobing visibility and electrical torrential sheets"
            ],
            'auditory': [
                "late night sounds become explosive whispers in flashstorm's cosmic instantaneous presence",
                "electrical annihilation amplifies minimal noise creating instantaneously sacred explosive acoustics",
                "flashstorm transforms deep night into acoustically explosive and electrically profound space"
            ],
            'olfactory': [
                "late night flashstorm carries concentrated electrical annihilation mixed with strobing sacred night air",
                "lightning bursts hold night's spiritual fragrances creating instantaneously charged and explosively profound saturated atmosphere",
                "charged air explodes deep solitude essence with storm's spiritually transformative and instantaneously pure electrical energy"
            ],
            'atmospheric': [
                "late night flashstorm creates sense of cosmic electrical mystery during strobing deep night's sacred annihilation",
                "lightning bursts make profound quiet feel instantaneously charged and spiritually transformative",
                "flashstorm transforms ordinary deep night into electrically charged landscape of cosmic instantaneous annihilation"
            ]
        },
        
        # Sample additional flashstorm and torrential_rain combinations
        'flashstorm_night': {
            'visual': [
                "night flashstorm creates explosive electrical annihilation backdrop to strobing darkness",
                "blinding lightning bursts transform night rhythm into strobing electrical chaos"
            ],
            'auditory': [
                "night sounds become explosive rhythm in flashstorm's instantaneous presence"
            ],
            'olfactory': [
                "night flashstorm carries established electrical essence mixed with rhythmic strobing night air"
            ],
            'atmospheric': [
                "night flashstorm creates established electrical rhythm during strobing night's explosive progression"
            ]
        },
        
        'torrential_rain_pre_dawn': {
            'visual': [
                "pre-dawn torrential rain creates overwhelming water annihilation backdrop to deepest night's flooded solitude",
                "massive water torrents transform sacred silence into drowning world of water chaos obliteration"
            ],
            'auditory': [
                "pre-dawn sounds become drowned whispers in torrential rain's overwhelming presence"
            ],
            'olfactory': [
                "pre-dawn torrential rain carries saturated water essence mixed with flooded night air"
            ],
            'atmospheric': [
                "pre-dawn torrential rain creates sense of water annihilation during deepest night's flooded solitude"
            ]
        },
        
        'torrential_rain_dawn': {
            'visual': [
                "dawn torrential rain creates spectacular water annihilation backdrop to sunrise's flooded awakening",
                "massive water torrents transform morning preparation into drowning world of water chaos beauty",
                "torrential rain reduces dawn activity to flooding sphere of drowning visibility and water shadow"
            ],
            'auditory': [
                "dawn sounds become drowned whispers in torrential rain's overwhelming presence",
                "water chaos amplifies morning sounds creating naturally drowning acoustic obliteration",
                "torrential downpour transforms dawn into acoustically drowned and water-dramatic space"
            ],
            'olfactory': [
                "dawn torrential rain carries saturated water essence mixed with morning's flooded awakening",
                "water torrents hold overwhelming moisture aromas creating drowningly fresh saturated atmospheric obliteration",
                "flooded air drowns dawn freshness with rain's moistly pure and overwhelmingly water essence"
            ],
            'atmospheric': [
                "dawn torrential rain creates sense of water annihilation during morning's flooded awakening",
                "water torrents make morning preparation feel overwhelmingly energized and water-beautiful",
                "torrential rain transforms ordinary dawn into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_early_morning': {
            'visual': [
                "early morning torrential rain creates intense water annihilation backdrop to flooded productive awakening",
                "massive water torrents transform busy morning into drowning world of water chaos productivity",
                "torrential rain reduces productive morning to flooding sphere of drowning focus and water concentration"
            ],
            'auditory': [
                "early morning sounds become drowned whispers in torrential rain's overwhelming presence",
                "water chaos amplifies productive sounds creating naturally drowning acoustic obliteration",
                "torrential downpour transforms busy morning into acoustically drowned and water-energizing space"
            ],
            'olfactory': [
                "early morning torrential rain carries saturated water essence mixed with productive flooded awakening",
                "water torrents hold overwhelming moisture aromas creating drowningly energizing saturated atmospheric obliteration",
                "flooded air drowns morning productivity with rain's moistly pure and overwhelmingly energizing water essence"
            ],
            'atmospheric': [
                "early morning torrential rain creates sense of water annihilation during productive flooded awakening",
                "water torrents make busy morning feel overwhelmingly motivated and water-productive",
                "torrential rain transforms hectic productivity into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_late_morning': {
            'visual': [
                "late morning torrential rain provides overwhelming water annihilation during peak flooded productive activity",
                "massive water torrents transform overwhelming productivity into drowning world of water chaos focus",
                "torrential rain reduces peak morning to overwhelmingly energized sphere of drowning concentration and water intensity"
            ],
            'auditory': [
                "late morning sounds become drowned chaos in torrential rain's overwhelming presence",
                "water annihilation intensifies productive noise creating overwhelmingly charged drowning acoustics",
                "torrential downpour transforms overwhelming activity into acoustically drowned and water-intense space"
            ],
            'olfactory': [
                "late morning torrential rain carries overwhelming water essence that drowns overcharged atmosphere",
                "water torrents amplify productive aromas creating overwhelmingly charged saturated atmospheric obliteration",
                "flooded air provides water annihilation to overwhelming productive scent concentration through drowning rain"
            ],
            'atmospheric': [
                "late morning torrential rain creates sense of water annihilation during peak flooded intensity",
                "water torrents make harsh productivity feel overwhelmingly charged and water-overwhelming",
                "torrential rain transforms overwhelming late morning into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_early_afternoon': {
            'visual': [
                "early afternoon torrential rain creates overwhelming water annihilation backdrop to flooded sustained intensive activity",
                "massive water torrents transform heated afternoon into drowning world of water chaos energy",
                "torrential rain reduces sustained intensity to overwhelmingly energized sphere of drowning focus and water concentration"
            ],
            'auditory': [
                "early afternoon sounds become drowned breathing in torrential rain's overwhelming presence",
                "water chaos amplifies sustained noise creating naturally drowning acoustic obliteration",
                "torrential downpour transforms heated activity into acoustically drowned and water-energizing space"
            ],
            'olfactory': [
                "early afternoon torrential rain carries overwhelming water essence that drowns sustained atmosphere",
                "water torrents intensify aromas creating overwhelmingly energizing saturated atmospheric obliteration",
                "flooded air provides water annihilation to sustained afternoon scent intensity through drowning rain"
            ],
            'atmospheric': [
                "early afternoon torrential rain creates sense of water annihilation during flooded sustained intensity",
                "water torrents make activity feel overwhelmingly energized and water-powerful",
                "torrential rain transforms intense afternoon into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_late_afternoon': {
            'visual': [
                "late afternoon torrential rain creates overwhelming water annihilation backdrop to flooded transition energy",
                "massive water torrents transform rush hour energy into drowning world of water chaos dramatic intensity",
                "torrential rain reduces busy transition to overwhelmingly energized sphere of drowning visibility and water sheets"
            ],
            'auditory': [
                "late afternoon sounds become drowned chaos in torrential rain's overwhelming transitional presence",
                "water annihilation amplifies harsh transition noise creating overwhelmingly powerful drowning acoustics",
                "torrential downpour transforms busy evening approach into acoustically drowned and water-dramatic space"
            ],
            'olfactory': [
                "late afternoon torrential rain carries mixture of water annihilation and flooded transitional intensity",
                "water torrents hold overwhelming water aromas creating overwhelmingly charged saturated atmospheric obliteration",
                "flooded air drowns accumulated day heat with rain's moistly pure and overwhelmingly water essence"
            ],
            'atmospheric': [
                "late afternoon torrential rain creates sense of overwhelming water transition during flooded evening approach",
                "water torrents make busy day's end feel overwhelmingly powerful and water-charged",
                "torrential rain transforms hectic transition into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_early_evening': {
            'visual': [
                "early evening torrential rain creates overwhelming water annihilation backdrop to flooded nightlife and drowning social energy",
                "massive water torrents transform artificial lights into drowning halos of water chaos dramatic glow",
                "torrential rain reduces social evening to overwhelmingly energized sphere of drowning visibility and water intensity"
            ],
            'auditory': [
                "early evening sounds become drowned whispers floating through torrential rain's overwhelming social presence",
                "water chaos amplifies social noise creating naturally drowning acoustic obliteration",
                "torrential downpour transforms nightlife energy into acoustically drowned and water-energizing space"
            ],
            'olfactory': [
                "early evening torrential rain carries mixture of water air and flooded entertainment energy overwhelmingly",
                "water torrents hold social fragrances creating overwhelmingly charged saturated atmospheric obliteration",
                "flooded air drowns nightlife essence with rain's moistly pure water energy"
            ],
            'atmospheric': [
                "early evening torrential rain creates sense of overwhelming water social experience during flooded nightlife",
                "water torrents make social energy feel overwhelmingly charged and powerfully connected",
                "torrential rain transforms ordinary nightlife into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_late_evening': {
            'visual': [
                "late evening torrential rain creates ultimate water annihilation backdrop to flooded night's established rhythm",
                "massive water torrents transform nightlife into drowning world of water chaos illumination intensity",
                "torrential rain reduces late evening to overwhelmingly energized sphere of drowning visibility and water sheets"
            ],
            'auditory': [
                "late evening sounds become drowned breathing in torrential rain's ultimate overwhelming presence",
                "water chaos amplifies night noise creating overwhelmingly dramatic drowning acoustics",
                "torrential downpour transforms late evening into acoustically drowned and water-intense space"
            ],
            'olfactory': [
                "late evening torrential rain carries mixture of water annihilation and flooded cooling night layers",
                "water torrents hold evening fragrances creating overwhelmingly charged and water-intense saturated atmosphere",
                "flooded air drowns nightlife essence with rain's moistly pure and water-powerful energy"
            ],
            'atmospheric': [
                "late evening torrential rain creates sense of water annihilation during flooded night's drowning progression",
                "water torrents make night feel overwhelmingly charged and spiritually meaningful",
                "torrential rain transforms ordinary late evening into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_afternoon': {
            'visual': [
                "afternoon torrential rain creates overwhelming water annihilation backdrop to peak flooded daytime intensity",
                "massive water torrents transform heated afternoon into drowning world of water chaos brilliance",
                "torrential rain reduces peak afternoon to overwhelmingly energized sphere of drowning visibility and water concentration"
            ],
            'auditory': [
                "afternoon sounds become drowned chaos in torrential rain's peak overwhelming presence",
                "water annihilation amplifies peak daytime noise creating overwhelmingly intense drowning acoustics",
                "torrential downpour transforms heated afternoon into acoustically drowned and water-brilliant space"
            ],
            'olfactory': [
                "afternoon torrential rain carries overwhelming water essence that drowns peak heated atmosphere",
                "water torrents amplify afternoon heat creating overwhelmingly intense saturated atmospheric obliteration",
                "flooded air provides water annihilation to peak afternoon heat concentration through drowning rain"
            ],
            'atmospheric': [
                "afternoon torrential rain creates sense of water annihilation during peak flooded intensity",
                "water torrents make heated afternoon feel overwhelmingly intense and water-brilliant",
                "torrential rain transforms peak afternoon into water-charged landscape of drowning obliteration"
            ]
        },
        
        'torrential_rain_evening': {
            'visual': [
                "evening torrential rain creates overwhelming water annihilation backdrop to flooded nightlife establishment",
                "massive water torrents transform evening transition into drowning world of water chaos nighttime beauty",
                "torrential rain reduces evening activity to overwhelmingly energized sphere of drowning visibility and water intensity"
            ],
            'auditory': [
                "evening sounds become drowned whispers floating through torrential rain's overwhelming nighttime presence",
                "water chaos amplifies evening transition creating naturally drowning acoustic obliteration",
                "torrential downpour transforms nighttime establishment into acoustically drowned and water-beautiful space"
            ],
            'olfactory': [
                "evening torrential rain carries mixture of water air and flooded nighttime establishment energy",
                "water torrents hold evening fragrances creating overwhelmingly charged saturated atmospheric obliteration",
                "flooded air drowns evening transition with rain's moistly pure and overwhelmingly water energy"
            ],
            'atmospheric': [
                "evening torrential rain creates sense of overwhelming water nighttime experience during flooded establishment",
                "water torrents make evening transition feel overwhelmingly charged and beautifully connected",
                "torrential rain transforms ordinary evening into water-charged landscape of drowning obliteration"
            ]
        },
        
        'flashstorm_afternoon': {
            'visual': [
                "afternoon flashstorm creates ultimate electrical annihilation backdrop to peak flooded daytime chaos",
                "instantaneous electrical torrents transform heated afternoon into strobing world of electrical chaos brilliance",
                "flashstorm reduces peak afternoon to instantaneously electrified sphere of strobing visibility and electrical concentration"
            ],
            'auditory': [
                "afternoon sounds become electrical whispers in flashstorm's peak instantaneous presence",
                "electrical annihilation amplifies peak daytime noise creating instantaneously intense strobing acoustics",
                "flashstorm transforms heated afternoon into acoustically electrified and strobing-brilliant space"
            ],
            'olfactory': [
                "afternoon flashstorm carries overwhelming electrical essence that electrifies peak heated atmosphere",
                "electrical torrents amplify afternoon heat creating instantaneously intense electrified atmospheric obliteration",
                "electrified air provides electrical annihilation to peak afternoon heat concentration through strobing electrical energy"
            ],
            'atmospheric': [
                "afternoon flashstorm creates sense of electrical annihilation during peak electrified intensity",
                "electrical torrents make heated afternoon feel instantaneously intense and strobing-brilliant",
                "flashstorm transforms peak afternoon into electrically-charged landscape of strobing obliteration"
            ]
        },
        
        'flashstorm_evening': {
            'visual': [
                "evening flashstorm creates overwhelming electrical annihilation backdrop to electrified nightlife establishment",
                "instantaneous electrical torrents transform evening transition into strobing world of electrical chaos nighttime beauty",
                "flashstorm reduces evening activity to instantaneously electrified sphere of strobing visibility and electrical intensity"
            ],
            'auditory': [
                "evening sounds become electrical whispers floating through flashstorm's overwhelming nighttime presence",
                "electrical chaos amplifies evening transition creating naturally strobing acoustic obliteration",
                "flashstorm transforms nighttime establishment into acoustically electrified and strobing-beautiful space"
            ],
            'olfactory': [
                "evening flashstorm carries mixture of electrical air and electrified nighttime establishment energy",
                "electrical torrents hold evening fragrances creating instantaneously charged electrified atmospheric obliteration",
                "electrified air electrifies evening transition with electrical energy's instantaneously pure and overwhelming electrical essence"
            ],
            'atmospheric': [
                "evening flashstorm creates sense of overwhelming electrical nighttime experience during electrified establishment",
                "electrical torrents make evening transition feel instantaneously charged and beautifully connected",
                "flashstorm transforms ordinary evening into electrically-charged landscape of strobing obliteration"
            ]
        },
        
        'torrential_rain_late_night': {
            'visual': [
                "late night torrential rain creates cosmic water annihilation backdrop to flooded deep solitude",
                "massive water torrents transform minimal lighting into drowning world of water chaos mystical intensity"
            ],
            'auditory': [
                "late night sounds become drowned whispers in torrential rain's cosmic overwhelming presence"
            ],
            'olfactory': [
                "late night torrential rain carries concentrated water annihilation mixed with flooded sacred night air"
            ],
            'atmospheric': [
                "late night torrential rain creates sense of cosmic water mystery during flooded deep night's sacred annihilation"
            ]
        },
        
        'flashstorm_midday': {
            'visual': [
                "midday flashstorm creates instantaneous electrical chaos during peak intensity",
                "blinding lightning bursts transform harsh conditions into strobing world of electrical annihilation"
            ],
            'auditory': [
                "midday thunder becomes instantaneous explosions in flashstorm's chaotic presence"
            ],
            'olfactory': [
                "midday flashstorm carries overwhelming ozone bursts that electrify extreme atmosphere"
            ],
            'atmospheric': [
                "midday flashstorm creates sense of instantaneous electrical chaos during peak annihilation"
            ]
        },
        
        'torrential_rain_dusk': {
            'visual': [
                "dusk torrential rain creates overwhelming water chaos backdrop to sunset's flooded transition",
                "massive water torrents transform dramatic sunset into drowning world of water annihilation"
            ],
            'auditory': [
                "dusk sounds become drowned whispers in torrential rain's overwhelming presence"
            ],
            'olfactory': [
                "dusk torrential rain carries saturated water essence and flooded night's approach"
            ],
            'atmospheric': [
                "dusk torrential rain creates sense of water annihilation during sunset's drowning passage"
            ]
        }
    },
}
