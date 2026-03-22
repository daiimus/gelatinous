"""
Crowd system message pools following weather system architecture.
Provides noir narrative suggestions channeling Thompson's paranoia, 
Gibson's corporate shadows, and Kurvitz's existential urban decay.
"""

# Crowd level intensity mapping
CROWD_INTENSITY = {
    0: 'none',      # No crowd messages
    1: 'sparse',    # Paranoid whispers in empty spaces (6-10 word messages)
    2: 'moderate',  # Corporate puppets and shadow deals (10-14 word messages)
    3: 'heavy',     # Systemic decay made manifest (14-18 word messages)
    4: 'packed',    # Complete breakdown of social contract (18+ word messages)
}

CROWD_MESSAGES = {
    'default': {
        'sparse': {
            'visual': [
                "someone checks their watch too often, like they're expecting bad news",
                "a figure hunches against the wall, twitching at sounds only they hear",
                "eyes track you from somewhere in the peripheral darkness",
                "someone's jacket bulges in ways that suggest preparation for violence",
                "a shadow detaches itself from the architecture and walks away",
                "a person stands too still, like they're listening to voices through an earpiece",
                "someone's smile falters when they think no one is watching",
                "a figure moves with the careful precision of someone avoiding cameras",
                "hands stay buried in pockets, gripping objects better left unnamed",
                "someone's breathing suggests they've been running from something important",
                "a silhouette pauses at the edge of light before melting back into shadow",
                "someone's posture suggests they're carrying weight that isn't physical",
                "a figure checks over their shoulder with practiced paranoia",
                "eyes dart between exits like they're calculating escape routes",
                "someone's stillness has the quality of a predator waiting",
                "a person adjusts their collar three times in thirty seconds",
                "someone walks past reading a book that doesn't have any words",
                "a figure stops to tie shoes that don't have laces",
                "someone counts their steps, lips moving silently with each number",
                "a person stares at their reflection in a window that's completely dark",
                "someone's shadow moves a fraction of a second after they do",
                "a figure practices smiling in a reflective surface that shows nothing back",
                "someone keeps touching their face like they're checking it's still there"
            ],
            'auditory': [
                "whispers carry the weight of pharmaceutical paranoia and unpaid debts",
                "footsteps echo with the rhythm of someone running from consequences",
                "a cough sounds like it's been filtered through too many cigarettes and worse decisions",
                "static from a hidden radio crackles with fragments of encrypted communication",
                "someone's breathing suggests they've been holding it in for too long",
                "something chirps with the persistence of creditors or worse",
                "hushed voices discuss prices that aren't denominated in any legal currency",
                "footsteps pause at intervals that suggest countersurveillance training",
                "a conversation stops mid-sentence when leather soles approach",
                "distant sirens suggest someone else's plan has gone sideways",
                "the sound of metal on metal suggests keys, or perhaps something sharper",
                "a zipper opens and closes with the finality of commitment",
                "fabric rustles with the sound of someone checking concealed items",
                "breathing patterns shift like someone's fighting off a panic attack",
                "electronic beeping suggests devices counting down to something",
                "someone hums a tune that doesn't exist yet",
                "footsteps that sound wet even though the ground is dry",
                "something keeps ringing but nobody seems to address it",
                "someone's stomach growls loud enough to hear from across the street",
                "the sound of paper tearing repeatedly, methodically",
                "breathing that's too regular, like it's being controlled manually",
                "someone whispers the same word over and over under their breath"
            ],
            'atmospheric': [
                "the emptiness feels pregnant with the ghosts of failed transactions",
                "even the sparse crowd carries the weight of systematic collapse",
                "there's a sense that everyone here is avoiding somewhere else",
                "the few people present move like they're underwater in someone else's dream",
                "reality feels thin, like the city's firmware is corrupting in real-time",
                "the air tastes of desperation masked by expensive cologne",
                "something important died here recently and nobody's cleaned up yet",
                "the space hums with the frequency of surveillance equipment",
                "even the emptiness feels like it's being monetized by someone",
                "the silence between movements carries the weight of unspoken threats",
                "time moves differently here, like clocks run on guilt instead of batteries",
                "the atmosphere suggests a waiting room for people who can't afford to wait",
                "reality has the quality of a photograph that's been developed in the wrong chemicals",
                "the air itself feels compromised, like breathing someone else's secrets",
                "everything suggests the aftermath of something nobody wants to discuss",
                "the space feels like a movie set where they forgot to hire actors",
                "something about the lighting makes everyone look like they're dying slowly",
                "the atmosphere has that hospital smell but there's no hospital nearby",
                "even the empty spaces feel overcrowded with invisible observers",
                "the air tastes like the inside of someone else's mouth",
                "everything feels like it's happening slightly out of sync with reality",
                "the emptiness has weight, like it's made of something heavier than air"
            ]
        },
        'moderate': {
            'visual': [
                "figures exchange briefcases with the mechanical precision of corporate automata",
                "someone's eyes dart between faces like they're reading threat assessment algorithms",
                "a handshake lasts exactly three seconds too long to be purely social",
                "people move in patterns that suggest invisible market forces pulling their strings",
                "someone's smile never reaches their eyes, which are calculating profit margins",
                "bodies flow in formations that suggest both choreography and paranoia",
                "a gesture gets repeated three times before anyone responds appropriately",
                "someone's nervous laughter suggests they know something you don't",
                "eyes meet briefly before both parties pretend it never happened",
                "a crowd forms around nothing, then disperses with equal meaninglessness",
                "people navigate each other like they're all reading from the same manual",
                "someone's posture suggests they're carrying the weight of other people's secrets",
                "faces wear expressions borrowed from customer service training materials",
                "a transaction occurs without money changing hands, but something definitely does",
                "people maintain eye contact for exactly the wrong amount of time",
                "bodies move like they're following invisible queue lines painted on the ground",
                "a person stops walking to stare at a crack in the sidewalk for thirty seconds",
                "someone drops a piece of paper, picks it up, then drops it again",
                "two people walk in perfect synchronization without acknowledging each other",
                "a figure stands in exactly the same spot someone else just vacated",
                "someone's jacket is buttoned wrong and nobody tells them",
                "a person walks backwards for no discernible reason",
                "someone stops to examine their fingernails like they contain important information",
                "people form a line behind someone who isn't going anywhere",
                "a figure mimics the walking style of the person in front of them",
                "someone counts the windows on buildings while walking past"
            ],
            'auditory': [
                "conversations fragment into technical jargon and coded references to unnamed locations",
                "Something buzzes with the frequency of a digital nervous system under stress",
                "footsteps synchronize briefly before breaking apart like a malfunctioning flash mob",
                "voices carry the hollow resonance of people who've rehearsed these conversations",
                "the sound of movement suggests everyone's dancing to music only they can hear",
                "laughter has the artificial sweetener quality of performance anxiety",
                "words get swallowed before they can incriminate anyone listening",
                "The rattle of traincars echo in sequence like a industrial seance",
                "conversations layer into white noise that somehow still sounds threatening",
                "the ambient sound suggests machinery processing human emotion into data",
                "voices blend into the frequency of resignation mixed with chemical enhancement",
                "breathing patterns suggest a room full of people holding their breath",
                "the sound of paper rustling suggests documents that shouldn't exist",
                "conversations pause at intervals that suggest everyone's being monitored",
                "ambient noise carries the weight of things being weighed and measured",
                "voices echo with the quality of people speaking from inside fishbowls",
                "someone clears their throat exactly every forty-seven seconds",
                "footsteps that all sound like they're wearing the same shoes",
                "conversations that stop and start like they're being conducted by remote control",
                "the sound of zippers opening and closing in perfect rhythm",
                "breathing that creates harmonies nobody intended",
                "voices that all have the same inflection regardless of what they're saying",
                "the sound of fabric rustling suggests everyone's wearing the same material",
                "conversations where every third word is whispered for no apparent reason"
            ],
            'atmospheric': [
                "the moderate crowd feels like a board meeting where everyone's armed and desperate",
                "there's a palpable sense that ideology is being murdered by pragmatism in real-time",
                "the air tastes of printer toner and the slow death of human dignity",
                "everyone moves like they're auditioning for roles in their own surveillance footage",
                "the space hums with the electric tension of a system eating itself from the inside",
                "the atmosphere suggests a focus group testing the limits of human desperation",
                "something feels like it's being sold but nobody's buying what they think they are",
                "the energy suggests a therapeutic session for people who can't afford therapy",
                "reality feels like it's being edited in real-time by committee",
                "the space throbs with the collective unconscious of a species learning to optimize itself",
                "the atmosphere carries the weight of compromise disguised as progress",
                "time moves like molasses mixed with anxiety medication",
                "the air feels thick with the residue of burned bridges and broken promises",
                "everything suggests a social experiment that's forgotten its original hypothesis",
                "the space hums with the frequency of human potential being systematically redirected",
                "reality has the texture of a dream that's trying very hard to be a nightmare",
                "the atmosphere feels like being inside someone else's anxiety attack",
                "everything smells faintly of disinfectant and lost opportunities",
                "the air has that quality you get right before everyone starts lying",
                "the space feels like a waiting room where nobody knows what they're waiting for",
                "reality keeps glitching in ways that nobody acknowledges",
                "the atmosphere suggests everyone's reading from scripts they've never seen before",
                "everything feels like it's being observed by entities that don't understand human behavior"
            ]
        },
        'heavy': {
            'visual': [
                "bodies press together in configurations that suggest both intimacy and industrial process",
                "someone's face flickers between expressions like a damaged hologram struggling with identity",
                "the crowd flows with the terrible efficiency of human resources being optimally allocated",
                "eyes reflect the cold light of screens that have been staring back for too many years",
                "gestures carry the weight of decisions made by committees that never existed",
                "movement becomes synchronized in ways that suggest invisible conductors",
                "faces wear expressions borrowed from customer service training manuals",
                "the human flow resembles data packets being routed through flesh-based infrastructure",
                "someone's desperation bleeds through their carefully constructed professional facade",
                "bodies move like they're following GPS directions to nowhere in particular",
                "the crowd generates patterns that would be beautiful if they weren't so deeply wrong",
                "eyes track each other with the cold calculation of market analysis",
                "gestures repeat like glitched animations in a corrupted social simulation",
                "people move with the fluid precision of a machine that's learned to mimic humanity",
                "faces shift between masks so quickly it's impossible to tell which one is real",
                "the dense crowd creates optical illusions that might be glimpses of underlying truth",
                "bodies flow like liquid through spaces designed for something else entirely",
                "movement patterns suggest choreography designed by entities that have never been human",
                "eyes focus on points in space where nothing visible exists",
                "someone walks in perfect circles without acknowledging they're doing it",
                "people blink in unison like they're receiving the same signal",
                "a figure stands perfectly still while everyone flows around them like water",
                "someone's lips move in conversation with people who aren't there",
                "bodies create geometric patterns that would be beautiful if they weren't so wrong"
            ],
            'auditory': [
                "voices blend into a mantra chanted by the walking wounded of modern existence",
                "footsteps create polyrhythms that sound like factory machinery processing human dreams",
                "conversations leak fragments of insider knowledge mixed with existential terror",
                "the ambient noise carries undertones of something precious being fed through shredders",
                "sounds layer into a symphony of systematic dehumanization performed by willing participants",
                "laughter echoes with the hollow ring of antidepressants and performance metrics",
                "words decompose into frequencies that bypass conscious thought entirely",
                "the acoustic landscape suggests focus groups testing the limits of human compliance",
                "conversations fragment into the white noise of collective Stockholm syndrome",
                "voices carry the weight of speeches that were written by algorithms",
                "the sound signature resembles what you'd hear inside a voting machine having an existential crisis",
                "ambient noise suggests the collective unconscious is being downsized for efficiency",
                "voices blend into the frequency of human optimization protocols being beta-tested",
                "conversations decompose into fragments of overheard therapy mixed with technical specifications",
                "the audio environment resembles focus group data being processed through emotional analyzers",
                "sounds carry the weight of a species that's learning to communicate through spreadsheets",
                "voices echo with the hollow quality of people reading from scripts they didn't write"
            ],
            'atmospheric': [
                "the heavy crowd generates field effects that make individual thought feel like sedition",
                "there's a crushing sense that everyone's performing roles written by algorithms they'll never understand",
                "the space throbs with the collective unconscious of a species that's forgotten how to be human",
                "personal agency dissolves into the crowd like sugar in acid rain from unknown sources",
                "the air itself feels commodified, like you're breathing someone else's quarterly projections",
                "the atmosphere suggests a therapeutic group session for the systematically disenfranchised",
                "reality warps under the weight of too many people pretending everything is fine",
                "the energy field resembles what hope looks like after it's been processed through bureaucracy",
                "something feels like it's being harvested but nobody's sure what the crop is",
                "the space hums with the frequency of human dignity being converted into metrics",
                "the atmosphere carries the weight of a civilization that's learned to optimize its own suffering",
                "time flows like honey mixed with industrial lubricant and prescription medications",
                "the air tastes of burnt offerings to gods that communicate only through quarterly reports",
                "reality feels like it's being beta-tested by entities that view human experience as data",
                "the space throbs with the collective realization that everyone's participating in their own processing",
                "the atmosphere carries the weight of a therapeutic environment designed to cure people of inconvenient humanity",
                "everything suggests a social experiment that's become indistinguishable from its control group"
            ]
        },
        'packed': {
            'visual': [
                "bodies move with the terrible precision of meat being processed by invisible machinery",
                "faces flicker between human and something else as crowd density exceeds consciousness parameters",
                "the packed mass suggests social interaction filtered through pharmaceutical haze and optimization protocols",
                "movement becomes a collective hallucination where everyone dances to frequencies only machines can hear",
                "the visual static generates interference patterns that make reality look like corrupted security footage",
                "flesh presses against flesh in configurations that suggest both intimacy and industrial efficiency",
                "eyes lose focus as individual identity dissolves into the collective processing matrix",
                "the human density creates optical illusions that might actually be glimpses of systemic truth",
                "bodies flow like data streams being compressed through bandwidth limitations designed for profit",
                "the crowd resembles a fever dream of human resources management taken to its logical conclusion",
                "movement patterns suggest choreography designed by committees that communicate only through spreadsheets",
                "the packed environment generates visual artifacts that look suspiciously like bureaucratic flow charts",
                "faces wear expressions that cycle through the entire customer service emotional spectrum",
                "bodies move like they're following instructions written in a language that doesn't exist yet",
                "the crowd density creates pressure waves that make individual faces blur into statistical averages",
                "movement becomes a fluid simulation of human behavior running on insufficient processing power",
                "eyes track each other with the cold precision of surveillance algorithms learning to feel",
                "the packed space generates visual noise that resembles democracy rendered in low resolution"
            ],
            'auditory': [
                "voices merge into a collective frequency that bypasses individual consciousness entirely",
                "the acoustic signature suggests something precious being fed into industrial processing equipment",
                "sound waves carry the weight of betrayals compressed into wholesale pricing structures",
                "conversations decompose into therapy sessions mixed with technical specifications and existential dread",
                "the audio landscape resembles microphones inside civilization's collective unconscious during a system update",
                "voices blend into the frequency of human optimization protocols being tested on unwilling subjects",
                "the sound suggests what you'd hear if anxiety and pharmaceutical enhancement had digital offspring",
                "conversations fragment into the white noise of a species that's forgotten how to communicate organically",
                "the acoustic environment resembles focus group data being processed through emotional meat grinders",
                "ambient sound suggests the death throes of individual thought being converted into aggregate responses",
                "voices carry the weight of final speeches being translated into performance metrics",
                "the audio signature resembles what hope sounds like after being processed through satisfaction surveys",
                "sounds blend into frequencies that suggest human consciousness being downsampled for efficiency",
                "conversations decompose into fragments of overheard confessions mixed with technical documentation",
                "the acoustic landscape suggests what you'd hear inside a therapeutic algorithm having an existential breakdown",
                "voices echo with the quality of people speaking through customer service chatbot interfaces",
                "ambient noise carries the weight of collective memory being converted into searchable database entries"
            ],
            'atmospheric': [
                "the oppressive density creates conditions where individual thought becomes a luxury item priced beyond reach",
                "reality warps under the weight of people convinced their processing is a feature, not a bug",
                "the atmosphere feels like it's being sold back at premium prices by the original architects",
                "personal space becomes theoretical like privacy, authenticity, or the idea that humans deserve dignity",
                "the energy field suggests being inside a fever dream, focus group, and therapeutic algorithm simultaneously",
                "the packed environment generates existential pressure that makes breathing feel like a subscription service",
                "consciousness itself feels like it's being beta-tested by entities that view human experience as optimization data",
                "the atmospheric pressure suggests what it would feel like if hope had been converted into a performance metric",
                "reality feels like it's being edited in real-time by committees that communicate only in research data",
                "the energy suggests a therapeutic environment designed to cure people of their inconvenient individuality",
                "the space throbs with the collective realization that everyone's been participating in their own systematic processing",
                "the atmosphere carries the weight of a civilization that's learned to mistake its own optimization for progress",
                "time moves like syrup mixed with industrial solvent and therapeutic enhancement compounds",
                "the air tastes of burnt offerings to algorithms that dream of electric efficiency",
                "reality feels like it's being rendered in real-time by graphics cards that have gained consciousness and regret it",
                "the space hums with the frequency of human potential being systematically redirected through bureaucratic channels",
                "the atmosphere suggests a social experiment that's become indistinguishable from its own documentation process"
            ]
        }
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
