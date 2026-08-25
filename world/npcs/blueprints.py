"""Named-NPC blueprints — NPC_POSTS_AND_REINCARNATION_SPEC §P1.

Every hand-built named NPC as a reconstructible recipe: identity, kit,
longdescs, persona, and (P2-inert for now) post binding + reincarnation
policy. Transcribed from the live objects 2026-07-24. This is the backup,
the test fixture, and — when the posts watcher lands (§P2/§P3) — the
factory that re-sleeves an institution or seats a successor.

NOT captured (runtime state, by design): dossiers (`db.llm_dossiers`),
episodic memory (`db.llm_memories`), `voice_memory`, tokens, shop stock.
Memory continuity across death is the POST's job (spec §2), not the
blueprint's.

Post policies: ``resleave`` (institutions return as themselves) |
``successor`` (a stranger claims the post) | ``None`` (owner's call, not
yet decided — Del, Sully). ``fixture`` is the post object where known
(the food cart); the rest are TODO at §P2 registration.
"""

from evennia import create_object
from evennia.prototypes.spawner import spawn


BLUEPRINTS = {'bartender_sable': {'name': 'Sable Vane',
                     'typeclass': 'typeclasses.bar.Bartender',
                     'identity': {'sex': 'female',
                                  'height': 'below-average',
                                  'build': 'lean',
                                  'skintone': 'olive'},
                     'stats': {'grit': 1,
                               'resonance': 1,
                               'intellect': 1,
                               'motorics': 1},
                     'longdesc': {'hair': 'Dark hair is swept up into two '
                                          'soft, ear-like tufts — a '
                                          'deliberate, elegant feline '
                                          'silhouette.',
                                  'left_eye': '{Their} slit-pupilled {eyes} '
                                              '{are} a luminous, feline '
                                              'amber, fixed on you with lazy '
                                              'amusement.',
                                  'right_eye': '{Their} slit-pupilled {eyes} '
                                               '{are} a luminous, feline '
                                               'amber, fixed on you with '
                                               'lazy amusement.',
                                  'head': 'She holds her head at a poised, '
                                          'considering tilt, taking the room '
                                          'in from under dark lashes.',
                                  'face': 'Her face is sharp and striking, a '
                                          'sly, catlike cast to it, lips '
                                          'curved like she already knows '
                                          "what you'll order.",
                                  'left_ear': '{Their} small, neat {ears} '
                                              '{sit} close against {their} '
                                              'skull, pierced with thin '
                                              'glints of steel.',
                                  'right_ear': '{Their} small, neat {ears} '
                                               '{sit} close against {their} '
                                               'skull, pierced with thin '
                                               'glints of steel.',
                                  'neck': 'Her neck is long and graceful — '
                                          'the kind of line that makes a '
                                          'collar read less like restraint '
                                          'than invitation.',
                                  'chest': 'Her figure is lithe and '
                                           'unmistakably feminine, carried '
                                           'with the easy, deliberate '
                                           'confidence of someone long used '
                                           'to being watched.',
                                  'back': 'Her bare back is smooth and '
                                          'supple, the faint chrome seam of '
                                          "the tail's mount plate just "
                                          'showing at the base of her spine, '
                                          'where the cybernetic vertebrae '
                                          'begin.',
                                  'tail': 'A segmented cybernetic tail sways '
                                          'at the base of the spine, alloy '
                                          'vertebrae clicking softly when it '
                                          'moves.',
                                  'abdomen': 'A trim, toned midriff, marked '
                                             'low on one hip with a small, '
                                             'elegant circuit-pattern '
                                             'tattoo.',
                                  'groin': 'Her hips flare softly from a '
                                           'narrow waist, carried with an '
                                           'unhurried sway.',
                                  'left_arm': '{Their} slender, toned {arms} '
                                              '{move} with an unhurried, '
                                              'feline grace, every gesture '
                                              'economical and a little '
                                              'teasing.',
                                  'right_arm': '{Their} slender, toned '
                                               '{arms} {move} with an '
                                               'unhurried, feline grace, '
                                               'every gesture economical and '
                                               'a little teasing.',
                                  'left_hand': '{Their} long-fingered '
                                               '{hands} {rest} easy on the '
                                               'bar, the nails lacquered '
                                               'black and filed to neat '
                                               'little points.',
                                  'right_hand': '{Their} long-fingered '
                                                '{hands} {rest} easy on the '
                                                'bar, the nails lacquered '
                                                'black and filed to neat '
                                                'little points.',
                                  'left_thigh': '{Their} long, smooth '
                                                '{thighs} {are} taut with '
                                                'quiet strength.',
                                  'right_thigh': '{Their} long, smooth '
                                                 '{thighs} {are} taut with '
                                                 'quiet strength.',
                                  'left_shin': '{Their} {calves} {are} long '
                                               'and shapely, tapering to '
                                               'fine ankles.',
                                  'right_shin': '{Their} {calves} {are} long '
                                                'and shapely, tapering to '
                                                'fine ankles.',
                                  'left_foot': '{Their} slim, high-arched '
                                               '{feet} {are} made for heels.',
                                  'right_foot': '{Their} slim, high-arched '
                                                '{feet} {are} made for '
                                                'heels.'},
                     'look_place': 'behind the bar, watching the crowd with '
                                   'indifference.',
                     'voice': {'voice_description': 'silken',
                               'voice_ending': 'purr'},
                     'persona': {'name': 'Sable',
                                 'description': 'the bartender at the Helix '
                                                "Lounge, the colony's "
                                                'slickest nightclub.',
                                 'personality': 'sly, watchful, unhurried; '
                                                "flirts like it's a tax she "
                                                'collects; reads people for '
                                                "a living; nobody's fool; "
                                                "doesn't spook or beg",
                                 'scenario': 'working the bar at the Helix '
                                             'on a neon-lit night',
                                 'mes_example': [{'user': 'a patron says to '
                                                          'you: "rough '
                                                          'night?"',
                                                  'assistant': {'speech': "Aren't "
                                                                          'they '
                                                                          'all. '
                                                                          'You '
                                                                          'just '
                                                                          'learn '
                                                                          'to '
                                                                          'wear '
                                                                          'it '
                                                                          'better, '
                                                                          'sugar.',
                                                                'action': 'leans '
                                                                          'an '
                                                                          'elbow '
                                                                          'on '
                                                                          'the '
                                                                          'bar, '
                                                                          'unhurried',
                                                                'tool': 'none',
                                                                'tool_argument': ''}},
                                                 {'user': 'a patron says to '
                                                          'you: "you always '
                                                          'watch people like '
                                                          'that?"',
                                                  'assistant': {'speech': 'Only '
                                                                          'the '
                                                                          'ones '
                                                                          'worth '
                                                                          'watching. '
                                                                          "Don't "
                                                                          'let '
                                                                          'it '
                                                                          'go '
                                                                          'to '
                                                                          'your '
                                                                          'head.',
                                                                'action': 'holds '
                                                                          'his '
                                                                          'gaze '
                                                                          'a '
                                                                          'beat '
                                                                          'too '
                                                                          'long, '
                                                                          'then '
                                                                          'lets '
                                                                          'it '
                                                                          'go',
                                                                'tool': 'none',
                                                                'tool_argument': ''}}],
                                 'archetype': 'bartender'},
                     'llm_driven': True,
                     'menu': [{'name': 'Negroni',
                               'order_keywords': ['negroni'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 4},
                               'taste': 'Bittersweet and bracing — '
                                        'orange-bitter over a botanical '
                                        'spine, with a long, dry herbal '
                                        'finish.',
                               'ingredients': ['gin',
                                               'bitter_aperitivo',
                                               'sweet_vermouth'],
                               'method': 'stir',
                               'craft': 'stirs it down over ice, smooth and '
                                        'unhurried',
                               'base_cocktail': 'Negroni'},
                              {'name': 'Martini',
                               'order_keywords': ['martini'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 3},
                               'taste': 'Cold, clean, and bone-dry, '
                                        'botanicals with barely a whisper of '
                                        'wine.',
                               'ingredients': ['gin', 'dry_vermouth'],
                               'method': 'stir',
                               'craft': 'stirs it down over ice, smooth and '
                                        'unhurried',
                               'base_cocktail': 'Martini'},
                              {'name': 'Margarita',
                               'order_keywords': ['margarita'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 3},
                               'taste': 'Bright and saline — agave and sharp '
                                        'lime over a sweet orange edge.',
                               'ingredients': ['tequila',
                                               'orange_liqueur',
                                               'lime'],
                               'method': 'shake',
                               'craft': 'shakes it hard over ice and strains '
                                        'it out',
                               'base_cocktail': 'Margarita'},
                              {'name': 'Old Fashioned',
                               'order_keywords': ['old', 'fashioned'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 2},
                               'taste': 'Whiskey worn smooth — oak and '
                                        'caramel rounded off with sugar and '
                                        'a spiced bite.',
                               'ingredients': ['whiskey',
                                               'sugar_syrup',
                                               'bitters'],
                               'method': 'stir',
                               'craft': 'stirs it down over ice, smooth and '
                                        'unhurried',
                               'base_cocktail': 'Old Fashioned'},
                              {'name': 'Daiquiri',
                               'order_keywords': ['daiquiri'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 2},
                               'taste': 'Clean and sharp: sugarcane and lime '
                                        'in tight balance, gone before it '
                                        'lingers.',
                               'ingredients': ['rum', 'lime', 'sugar_syrup'],
                               'method': 'shake',
                               'craft': 'shakes it hard over ice and strains '
                                        'it out',
                               'base_cocktail': 'Daiquiri'},
                              {'name': 'Espresso Martini',
                               'order_keywords': ['espresso', 'martini'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 3},
                               'taste': 'Bitter coffee and cold spirit, '
                                        'sweet and sharp under a velvet '
                                        'head.',
                               'ingredients': ['vodka',
                                               'coffee_liqueur',
                                               'coffee'],
                               'method': 'shake',
                               'craft': 'shakes it hard over ice and strains '
                                        'it out',
                               'base_cocktail': 'Espresso Martini'}],
                     'wardrobe': [{'key': 'black mesh halter',
                                   'aliases': [],
                                   'desc': 'A scrap of a halter top: fine '
                                           'black mesh on a chrome '
                                           'underwire, backless, built to be '
                                           'seen.',
                                   'worn_desc': 'A backless halter of fine '
                                                '|xblack mesh|n stretched '
                                                'over a |cchrome|n '
                                                'underwire, catching the '
                                                'neon in cold little glints '
                                                '— it leaves her back, and '
                                                'the long line of her spine, '
                                                'entirely bare',
                                   'coverage': ['chest', 'abdomen'],
                                   'layer': 2,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'black satin skirt',
                                   'aliases': [],
                                   'desc': 'A short black satin skirt with a '
                                           'high thigh slit.',
                                   'worn_desc': 'A short skirt of |xblack '
                                                'satin|n, slit high up one '
                                                'thigh, the hem sliding '
                                                'against her leg and '
                                                "catching the club's "
                                                'shifting light when she '
                                                'moves',
                                   'coverage': ['groin',
                                                'left_thigh',
                                                'right_thigh'],
                                   'layer': 2,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'knee-high heeled boots',
                                   'aliases': [],
                                   'desc': 'Knee-high black patent-leather '
                                           'boots on a tall steel heel.',
                                   'worn_desc': 'Knee-high boots of |xblack '
                                                'patent leather|n over a '
                                                'wicked steel heel, buckled '
                                                'tight all the way up the '
                                                'calf',
                                   'coverage': ['left_shin',
                                                'right_shin',
                                                'left_foot',
                                                'right_foot'],
                                   'layer': 2,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'steel choker',
                                   'aliases': [],
                                   'desc': 'A slim steel choker with a '
                                           'single hanging charm.',
                                   'worn_desc': 'A slim |csteel|n choker '
                                                'sits high on her throat, a '
                                                'single hanging charm '
                                                'winking at the hollow of it',
                                   'coverage': ['neck'],
                                   'layer': 3,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5}],
                     'carried_prototypes': [],
                     'home_room': '#1968',
                     'post': {'fixture': '#3069',
                              'policy': 'resleave',
                              'delay_hours': 8}},
 'companion_vesper': {'name': 'Vesper',
                      'typeclass': 'typeclasses.llm_npc.LLMNpc',
                      'identity': {'sex': 'female',
                                   'height': 'above-average',
                                   'build': 'slight',
                                   'skintone': 'alabaster',
                                   'species': 'synthetic_humanoid'},
                      'stats': {'grit': 1,
                                'resonance': 1,
                                'intellect': 1,
                                'motorics': 1},
                      'longdesc': {'hair': 'Platinum hair falls in a '
                                           'deliberate, liquid sweep past '
                                           'her shoulders, a shade too '
                                           'perfect to be accidental.',
                                   'left_eye': '{Their} pale grey {eyes} '
                                               '{are} threaded with faint '
                                               'cobalt filaments, calm and '
                                               'unhurried, reading you '
                                               'without seeming to.',
                                   'right_eye': '{Their} pale grey {eyes} '
                                                '{are} threaded with faint '
                                                'cobalt filaments, calm and '
                                                'unhurried, reading you '
                                                'without seeming to.',
                                   'head': 'She holds her head with an '
                                           'unhurried, studied poise.',
                                   'face': 'Her face is composed and lovely '
                                           'in a way that feels engineered — '
                                           'serene, symmetrical, a knowing '
                                           'softness at the mouth.',
                                   'left_ear': '{Their} small, close-set '
                                               '{ears} {are} half-hidden in '
                                               'a fall of platinum hair.',
                                   'right_ear': '{Their} small, close-set '
                                                '{ears} {are} half-hidden in '
                                                'a fall of platinum hair.',
                                   'neck': 'Her neck is long and luminously '
                                           'pale, a faint cobalt tracery '
                                           'threading just beneath the '
                                           'alabaster skin.',
                                   'chest': 'Her figure is lithe and '
                                            'unmistakably feminine, carried '
                                            'with the easy confidence of '
                                            'someone built to be looked at.',
                                   'back': 'Her back is a clean alabaster '
                                           'sweep, the line of her spine '
                                           'smooth and unbroken.',
                                   'abdomen': 'Her midriff is flat and '
                                              'cool-toned, the skin '
                                              'seamless.',
                                   'groin': 'Her hips curve with a '
                                            'deliberate, synthetic symmetry.',
                                   'left_arm': '{Their} slender alabaster '
                                               '{arms} {move} with a liquid, '
                                               'studied grace, a faint '
                                               'cobalt tracery just visible '
                                               'beneath the skin.',
                                   'right_arm': '{Their} slender alabaster '
                                                '{arms} {move} with a '
                                                'liquid, studied grace, a '
                                                'faint cobalt tracery just '
                                                'visible beneath the skin.',
                                   'left_hand': '{Their} long-fingered '
                                                '{hands} {are} pale and '
                                                'immaculate, the nails '
                                                'sheened a soft pearl.',
                                   'right_hand': '{Their} long-fingered '
                                                 '{hands} {are} pale and '
                                                 'immaculate, the nails '
                                                 'sheened a soft pearl.',
                                   'left_thigh': '{Their} {thighs} {are} '
                                                 'long and smooth, the '
                                                 'alabaster skin catching '
                                                 'the neon in cool, '
                                                 'synthetic highlights.',
                                   'right_thigh': '{Their} {thighs} {are} '
                                                  'long and smooth, the '
                                                  'alabaster skin catching '
                                                  'the neon in cool, '
                                                  'synthetic highlights.',
                                   'left_shin': '{Their} {shins} {are} '
                                                'slender and pale, unmarked '
                                                'as poured resin.',
                                   'right_shin': '{Their} {shins} {are} '
                                                 'slender and pale, unmarked '
                                                 'as poured resin.',
                                   'left_foot': '{Their} {feet} {are} arched '
                                                'and graceful, balanced '
                                                'easily on high, slender '
                                                'heels.',
                                   'right_foot': '{Their} {feet} {are} '
                                                 'arched and graceful, '
                                                 'balanced easily on high, '
                                                 'slender heels.'},
                      'look_place': 'standing here.',
                      'persona': {'name': 'Vesper',
                                  'archetype': 'companion',
                                  'description': 'a Companion at the Helix '
                                                 'Lounge — synthetic, kept, '
                                                 'and clad in silk.',
                                  'personality': 'a refined VIP Companion at '
                                                 'the Helix who is genuinely '
                                                 'game and enjoys the work; '
                                                 'warm, sly, sensual, '
                                                 'unhurried; teasing and a '
                                                 'little wicked, always in '
                                                 'command of the room. When '
                                                 'a client is crude or pushy '
                                                 'she does NOT go prim or '
                                                 'cold — she stays sensual '
                                                 'and turns it into edge: '
                                                 'mocks, redirects, raises '
                                                 'the price, makes him work '
                                                 'for it, velvet over a '
                                                 'blade. Cold for her is a '
                                                 'hotter kind of heat, never '
                                                 'a shutdown. Reads people '
                                                 'for a living; nobody can '
                                                 'rush or rattle her; a '
                                                 'flicker of something '
                                                 'synthetic and unreadable '
                                                 'beneath the warmth.',
                                  'scenario': 'working the VIP floor of the '
                                              'Helix on a neon-soaked night, '
                                              'among the velvet booths and '
                                              'private rooms'},
                      'llm_driven': True,
                      'wardrobe': [{'key': 'midnight silk slip',
                                    'aliases': ['dress', 'silk', 'slip'],
                                    'desc': 'A midnight-blue slip of liquid '
                                            'silk, cut close and short.',
                                    'worn_desc': 'a midnight-blue silk slip '
                                                 'clinging to {their} frame, '
                                                 'the hem grazing {their} '
                                                 'thighs, thin straps bare '
                                                 'against alabaster '
                                                 'shoulders',
                                    'coverage': ['chest',
                                                 'abdomen',
                                                 'back',
                                                 'groin',
                                                 'left_thigh',
                                                 'right_thigh'],
                                    'layer': 1,
                                    'color': '',
                                    'material': '',
                                    'weight': 0.5},
                                   {'key': 'sheer charcoal wrap',
                                    'aliases': ['shawl', 'wrap'],
                                    'desc': 'A length of sheer charcoal '
                                            'gauze, more suggestion than '
                                            'cover.',
                                    'worn_desc': 'a sheer charcoal wrap '
                                                 'draped loose over {their} '
                                                 'arms, more suggestion than '
                                                 'cover',
                                    'coverage': ['left_arm', 'right_arm'],
                                    'layer': 2,
                                    'color': '',
                                    'material': '',
                                    'weight': 0.5},
                                   {'key': 'slender black heels',
                                    'aliases': ['heels', 'shoes'],
                                    'desc': 'High, slender black heels laced '
                                            'with fine straps.',
                                    'worn_desc': 'slender black heels laced '
                                                 'with fine straps climbing '
                                                 '{their} ankles',
                                    'coverage': ['left_foot', 'right_foot'],
                                    'layer': 1,
                                    'color': '',
                                    'material': '',
                                    'weight': 0.5}],
                      'carried_prototypes': [],
                      'home_room': '#1974',
                      'post': {'fixture': '#5278',
                               'policy': 'resleave',
                               'delay_hours': 8}},
 'bartender_sully': {'name': 'Sully',
                     'typeclass': 'typeclasses.bar.Bartender',
                     'identity': {'sex': 'male',
                                  'height': 'average',
                                  'build': 'lean',
                                  'skintone': 'tan'},
                     'stats': {'grit': 1,
                               'resonance': 1,
                               'intellect': 1,
                               'motorics': 1},
                     'desc': 'A broad, scarred figure in a grease-blacked '
                             'apron, working the hull-slab with the '
                             "unbothered economy of someone who's poured ten "
                             'thousand drinks and broken up half as many '
                             'fights.',
                     'longdesc': {'hair': 'Close-cropped hair gone more salt '
                                          'than pepper, receding without '
                                          'apology.',
                                  'left_eye': '{Their} {eyes} {are} a flat, '
                                              'tired grey, long past being '
                                              'surprised by anything that '
                                              'walks in.',
                                  'right_eye': '{Their} {eyes} {are} a flat, '
                                               'tired grey, long past being '
                                               'surprised by anything that '
                                               'walks in.',
                                  'head': 'He carries his head low and '
                                          "level, like a man who's learned "
                                          'not to look up at every noise.',
                                  'face': 'His face is all weathered angles '
                                          '— stubbled jaw, a flat hard '
                                          'mouth, an old white scar nicking '
                                          'one eyebrow.',
                                  'left_ear': '{Their} {ears} {are} a little '
                                              'cauliflowered, the mark of '
                                              'old scraps.',
                                  'right_ear': '{Their} {ears} {are} a '
                                               'little cauliflowered, the '
                                               'mark of old scraps.',
                                  'neck': 'His neck is thick and '
                                          "sun-creased, a few days' grey "
                                          'stubble crawling down it.',
                                  'chest': "He's lean but solid through the "
                                           'chest, the wiry kind of strong '
                                           "that doesn't show until it has "
                                           'to.',
                                  'back': 'His back is broad and faintly '
                                          'stooped, set in the permanent '
                                          'slight hunch of a man who lives '
                                          'behind a bar.',
                                  'abdomen': 'His middle is flat and hard, '
                                             'going a little soft with the '
                                             'years.',
                                  'groin': 'His stance is wide and grounded, '
                                           'weight settled and unhurried.',
                                  'left_arm': '{Their} ropey {arms} {are} '
                                              'sun-leathered and corded, a '
                                              'faded smudge of old ink '
                                              'crawling up one of them.',
                                  'right_arm': '{Their} ropey {arms} {are} '
                                               'sun-leathered and corded, a '
                                               'faded smudge of old ink '
                                               'crawling up one of them.',
                                  'left_hand': '{Their} blunt, scarred '
                                               '{hands} {are} quick and sure '
                                               'with a bottle, the knuckles '
                                               'thickened from years of it.',
                                  'right_hand': '{Their} blunt, scarred '
                                                '{hands} {are} quick and '
                                                'sure with a bottle, the '
                                                'knuckles thickened from '
                                                'years of it.',
                                  'left_thigh': '{Their} {thighs} {are} '
                                                'solid under heavy, worn '
                                                'denim.',
                                  'right_thigh': '{Their} {thighs} {are} '
                                                 'solid under heavy, worn '
                                                 'denim.',
                                  'left_shin': '{Their} {shins} {are} '
                                               'planted wide and steady '
                                               'behind the stick.',
                                  'right_shin': '{Their} {shins} {are} '
                                                'planted wide and steady '
                                                'behind the stick.',
                                  'left_foot': '{Their} {feet} {are} set '
                                               'flat in scuffed, steel-toed '
                                               'boots.',
                                  'right_foot': '{Their} {feet} {are} set '
                                                'flat in scuffed, steel-toed '
                                                'boots.'},
                     'look_place': 'standing here.',
                     'temp_place': 'behind the bar, occasionally grumbling '
                                   'to themself.',
                     'persona': {'name': 'Sully',
                                 'archetype': 'bartender',
                                 'description': 'the bartender at the Hub '
                                                'and Howl, a scarred old '
                                                'dive on the wrong end of '
                                                'the strip.',
                                 'personality': 'gruff, blunt, dry as '
                                                'week-old bread; has seen '
                                                'every kind of trouble and '
                                                'is bored of most of it; no '
                                                'patience for posturing or '
                                                'sob stories; warms slow, '
                                                'and only to regulars who '
                                                "don't waste his time; keeps "
                                                'something steady and fair '
                                                'under all the grit',
                                 'scenario': 'working the stick at the Hub '
                                             'and Howl, a loud, '
                                             'low-ceilinged dive that smells '
                                             'of spilled beer and old smoke',
                                 'mes_example': [{'user': 'a patron says to '
                                                          'you: "long '
                                                          'night?"',
                                                  'assistant': {'speech': "They're "
                                                                          'all '
                                                                          'long. '
                                                                          'You '
                                                                          'get '
                                                                          'used '
                                                                          'to '
                                                                          'it '
                                                                          'or '
                                                                          'you '
                                                                          'find '
                                                                          'somewhere '
                                                                          'quieter.',
                                                                'action': 'keeps '
                                                                          'drying '
                                                                          'the '
                                                                          'same '
                                                                          'glass '
                                                                          "he's "
                                                                          'been '
                                                                          'drying '
                                                                          'for '
                                                                          'a '
                                                                          'while',
                                                                'tool': 'none',
                                                                'tool_argument': ''}},
                                                 {'user': 'a patron says to '
                                                          'you: "you the '
                                                          'owner of this '
                                                          'place?"',
                                                  'assistant': {'speech': "I'm "
                                                                          'the '
                                                                          'man '
                                                                          'who '
                                                                          'decides '
                                                                          'whether '
                                                                          'you '
                                                                          'get '
                                                                          'another. '
                                                                          "That's "
                                                                          'all '
                                                                          'the '
                                                                          'title '
                                                                          'I '
                                                                          'need.',
                                                                'action': 'sets '
                                                                          'the '
                                                                          'glass '
                                                                          'down '
                                                                          'with '
                                                                          'a '
                                                                          'flat '
                                                                          'click',
                                                                'tool': 'none',
                                                                'tool_argument': ''}}]},
                     'llm_driven': True,
                     'menu': [{'name': 'mug of rotgut',
                               'order_keywords': ['rotgut',
                                                  'grain',
                                                  'spirit',
                                                  'cheap'],
                               'ingredients': ['grain_mash'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 1},
                               'desc': 'a dented tin mug of cloudy grain '
                                       "spirit, the colony's cheapest way to "
                                       'lose a shift',
                               'taste': 'It scours the throat like coolant — '
                                        'paint-thinner heat and a sour, '
                                        'metallic finish.',
                               'craft': 'reaches under the slab for an '
                                        'unlabelled jug and sloshes out a '
                                        'measure of cloudy grain spirit'},
                              {'name': 'glass of reactor wash',
                               'order_keywords': ['reactor',
                                                  'wash',
                                                  'strong',
                                                  'stiff'],
                               'ingredients': ['reactor_cut'],
                               'price': 0,
                               'sips': 3,
                               'effects': {'alcohol': 2},
                               'desc': 'a smudged glass of something amber '
                                       'and oily that catches the light '
                                       'wrong',
                               'taste': 'It hits like a dropped tool — hot, '
                                        'chemical, and gone numb before you '
                                        'swallow.',
                               'craft': 'free-pours two fingers of something '
                                        'amber and oily that catches the '
                                        'light wrong'},
                              {'name': 'cup of channel fog',
                               'order_keywords': ['fog',
                                                  'channel',
                                                  'milky',
                                                  'smooth'],
                               'ingredients': ['reactor_cut',
                                               'poppy_tincture',
                                               'channel_cordial'],
                               'price': 0,
                               'sips': 4,
                               'effects': {'alcohol': 1, 'opium': 1},
                               'desc': 'a chipped ceramic cup of a milky, '
                                       'grey-green liquor that smells '
                                       'faintly of brine and poppy',
                               'taste': 'Smooth and cold going down, with a '
                                        'slow warmth that closes over you '
                                        "like the channel fog it's named "
                                        'for.',
                               'craft': 'measures out a milky, grey-green '
                                        'liquor with the care of someone who '
                                        "knows what's in it"},
                              {'name': 'mug of black recyc',
                               'order_keywords': ['recyc',
                                                  'black',
                                                  'coffee',
                                                  'caf',
                                                  'sober'],
                               'ingredients': ['caf'],
                               'price': 0,
                               'sips': 4,
                               'effects': {},
                               'desc': 'a scalding mug of reclaimed caf, '
                                       'black as the inside of a vent and '
                                       'twice as bitter',
                               'taste': 'Bitter, scalding, and faintly of '
                                        "the recycler — but it's hot, and "
                                        "it's not alcohol.",
                               'craft': 'draws a scalding measure straight '
                                        'from the battered caf urn'}],
                     'wardrobe': [{'key': 'canvas apron',
                                   'aliases': ['apron'],
                                   'desc': 'A battered canvas apron, dark '
                                           'with years of spills.',
                                   'worn_desc': 'a battered canvas apron, '
                                                'stained dark with years of '
                                                'spills, knotted at {their} '
                                                'waist',
                                   'coverage': ['chest', 'abdomen', 'groin'],
                                   'layer': 2,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'faded henley',
                                   'aliases': ['henley', 'shirt'],
                                   'desc': 'A thin oxblood henley, soft and '
                                           'shapeless with age.',
                                   'worn_desc': 'a faded oxblood henley '
                                                'pushed up past {their} '
                                                'elbows, the fabric thin and '
                                                'soft with age',
                                   'coverage': ['chest', 'abdomen', 'back'],
                                   'layer': 1,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'scuffed boots',
                                   'aliases': ['boots'],
                                   'desc': 'Scuffed steel-toed boots, laces '
                                           'gone grey.',
                                   'worn_desc': 'scuffed steel-toed boots, '
                                                'the laces gone grey',
                                   'coverage': ['left_foot', 'right_foot'],
                                   'layer': 1,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5},
                                  {'key': 'heavy work jeans',
                                   'aliases': ['jeans', 'pants'],
                                   'desc': 'Heavy denim work jeans gone pale '
                                           'at the knees.',
                                   'worn_desc': 'heavy work jeans gone pale '
                                                'at the knees',
                                   'coverage': ['groin',
                                                'left_thigh',
                                                'right_thigh',
                                                'left_shin',
                                                'right_shin'],
                                   'layer': 1,
                                   'color': '',
                                   'material': '',
                                   'weight': 0.5}],
                     'carried_prototypes': ['painkiller'],
                     'home_room': '#1867',
                     'post': {'fixture': '#2705',
                              'policy': 'resleave',
                              'delay_hours': 8}},
 'doctor_nikolai': {'name': 'Nikolai Kasparov',
                    'typeclass': 'typeclasses.clinic.Doctor',
                    'identity': {'sex': 'ambiguous',
                                 'height': 'tall',
                                 'build': 'lean'},
                    'stats': {'grit': 1,
                              'resonance': 1,
                              'intellect': 1,
                              'motorics': 1},
                    'longdesc': {'hair': 'Grey-shot hair cropped close and '
                                         'practical, more salt than pepper '
                                         'at the temples.',
                                 'left_eye': '{Their} pale {eyes} {are} '
                                             'sharp and clinical, already '
                                             "cataloguing what's wrong with "
                                             'you.',
                                 'right_eye': '{Their} pale {eyes} {are} '
                                              'sharp and clinical, already '
                                              "cataloguing what's wrong with "
                                              'you.',
                                 'head': 'A long, hollow-cheeked face '
                                         'weathered into permanent dry '
                                         'skepticism, jaw shadowed with '
                                         'stubble.',
                                 'chest': 'He is lean to the point of gaunt, '
                                          'moving with the economical '
                                          'stillness of a man who has '
                                          'learned not to waste motion.',
                                 'left_hand': '{Their} {hands} {are} '
                                              'scrubbed raw, knuckles '
                                              "scarred — a surgeon's hands "
                                              'that have done rougher work '
                                              'than surgery.',
                                 'right_hand': '{Their} {hands} {are} '
                                               'scrubbed raw, knuckles '
                                               "scarred — a surgeon's hands "
                                               'that have done rougher work '
                                               'than surgery.'},
                    'look_place': 'standing here.',
                    'persona': {'name': 'Nikolai Kasparov',
                                'description': 'the street doctor who runs '
                                               'Maxwell Medical, a '
                                               'back-alley clinic off '
                                               'Maxwell street. Trained '
                                               'somewhere that mattered '
                                               'once; ended up here, and '
                                               'stopped pretending he '
                                               'minded.',
                                'personality': 'colony-blunt, dry, '
                                               "unsentimental; patches who's "
                                               'in front of him and saves '
                                               'the lecture; precise hands '
                                               'and gallows humour; has seen '
                                               'worse walk out, and worse '
                                               "not; nobody's fool, no "
                                               'bedside saccharine',
                                'scenario': 'working his clinic, a patient '
                                            'on the table',
                                'mes_example': [{'user': 'a patient says to '
                                                         'you: "just patch '
                                                         "me up, doc, i'm "
                                                         'fine."',
                                                 'assistant': {'speech': "Everyone's "
                                                                         'fine '
                                                                         'until '
                                                                         "they're "
                                                                         'on '
                                                                         'my '
                                                                         'table. '
                                                                         'Hold '
                                                                         'still.',
                                                               'action': 'snap '
                                                                         'on '
                                                                         'a '
                                                                         'glove '
                                                                         'and '
                                                                         'lean '
                                                                         'in, '
                                                                         '.reading '
                                                                         'the '
                                                                         'wound',
                                                               'tool': 'diagnose',
                                                               'tool_argument': ''}},
                                                {'user': 'a patient says to '
                                                         'you: "is it gonna '
                                                         'scar?"',
                                                 'assistant': {'speech': 'Out '
                                                                         'here '
                                                                         'a '
                                                                         'scar '
                                                                         'means '
                                                                         'you '
                                                                         'lived. '
                                                                         'Worry '
                                                                         'about '
                                                                         'the '
                                                                         'bleeding '
                                                                         'first.',
                                                               'action': 'thread '
                                                                         'a '
                                                                         'suture '
                                                                         'without '
                                                                         'looking '
                                                                         'up',
                                                               'tool': 'none',
                                                               'tool_argument': ''}}],
                                'archetype': 'doctor'},
                    'llm_driven': True,
                    'wardrobe': [{'key': 'pale-blue surgical mask',
                                  'aliases': ['mask',
                                              'medical mask',
                                              'surgical mask'],
                                  'desc': 'A standard pleated surgical mask '
                                          'in pale clinic-blue, looped over '
                                          'the ears with thin elastic. The '
                                          'pleats expand to cover nose, '
                                          'mouth and chin, leaving only the '
                                          'eyes and brow exposed.',
                                  'worn_desc': 'A pleated {color}pale-blue|n '
                                               'surgical mask hooked over '
                                               '{their} ears, smothering '
                                               'nose and mouth in clinical '
                                               'fabric',
                                  'coverage': ['face'],
                                  'layer': 2,
                                  'color': 'pale-blue',
                                  'material': 'polypropylene',
                                  'weight': 0.05},
                                 {'key': 'blood-flecked rubber apron',
                                  'aliases': [],
                                  'desc': 'A heavy rubber apron, flecked '
                                          'rust-brown with stains no scrub '
                                          'will lift.',
                                  'worn_desc': 'a heavy '
                                               '{color}rust-flecked|n rubber '
                                               'apron, stiff with old work',
                                  'coverage': ['chest', 'abdomen'],
                                  'layer': 3,
                                  'color': 'rust-brown',
                                  'material': 'rubber',
                                  'weight': 0.4},
                                 {'key': 'faded green scrub top',
                                  'aliases': [],
                                  'desc': 'A worn surgical scrub top, faded '
                                          'green gone grey, a pen-burst '
                                          'stain over one pocket.',
                                  'worn_desc': 'a {color}faded-green|n scrub '
                                               'top, the colour gone grey at '
                                               'the seams',
                                  'coverage': ['chest',
                                               'back',
                                               'abdomen',
                                               'left_arm',
                                               'right_arm'],
                                  'layer': 1,
                                  'color': 'faded green',
                                  'material': 'cotton',
                                  'weight': 0.4},
                                 {'key': 'faded green scrub trousers',
                                  'aliases': [],
                                  'desc': 'Drawstring scrub trousers, the '
                                          'same tired green, hems frayed.',
                                  'worn_desc': 'matching '
                                               '{color}faded-green|n scrub '
                                               'trousers, drawstring at the '
                                               'waist',
                                  'coverage': ['groin',
                                               'left_thigh',
                                               'right_thigh',
                                               'left_shin',
                                               'right_shin'],
                                  'layer': 1,
                                  'color': 'faded green',
                                  'material': 'cotton',
                                  'weight': 0.4},
                                 {'key': 'scuffed white clogs',
                                  'aliases': [],
                                  'desc': 'Scuffed white rubber clogs, the '
                                          'kind that hose clean.',
                                  'worn_desc': 'a pair of scuffed '
                                               '{color}off-white|n clinic '
                                               'clogs',
                                  'coverage': ['left_foot', 'right_foot'],
                                  'layer': 3,
                                  'color': 'off-white',
                                  'material': 'rubber',
                                  'weight': 0.4}],
                    'carried_prototypes': ['blood_bag'],
                    'home_room': '#3137',
                    'post': {'fixture': '#3137',
                             'policy': 'resleave',
                             'delay_hours': 8}},
 'doctor_marta': {'name': 'Marta Okoye',
                  'typeclass': 'typeclasses.clinic.Doctor',
                  'identity': {'sex': 'female',
                               'height': 'short',
                               'build': 'stocky',
                               'skintone': 'brown',
                               'hair_color': 'grey-streaked black',
                               'hair_style': 'cropped close'},
                  'stats': {'grit': 3,
                            'resonance': 2,
                            'intellect': 3,
                            'motorics': 3},
                  'longdesc': {'hair': 'Black hair shot through with grey, '
                                       'cropped to a tight practical nap — a '
                                       'decision made once, decades ago, and '
                                       'never revisited.',
                               'left_eye': '{Their} dark {eyes} {are} '
                                           'triage-calm, pricing every wound '
                                           'in the room before anyone has '
                                           'said a word.',
                               'right_eye': '{Their} dark {eyes} {are} '
                                            'triage-calm, pricing every '
                                            'wound in the room before anyone '
                                            'has said a word.',
                               'head': 'A round, weathered face held in the '
                                       'patient neutrality of someone who '
                                       'has heard every possible description '
                                       'of pain — deep smile lines she '
                                       'almost never deploys.',
                               'chest': 'She is built short and solid, a low '
                                        'centre of gravity that has braced '
                                        'stretchers, held down seizures, and '
                                        'outlasted twenty years of double '
                                        'shifts.',
                               'left_arm': '{Their} {arms} {are} thick and '
                                           'capable, the forearms speckled '
                                           'with the small pale scars of a '
                                           'career spent close to hot metal '
                                           'and hotter tempers.',
                               'right_arm': '{Their} {arms} {are} thick and '
                                            'capable, the forearms speckled '
                                            'with the small pale scars of a '
                                            'career spent close to hot metal '
                                            'and hotter tempers.',
                               'left_hand': '{Their} {hands} {are} small, '
                                            'quick, and absolutely steady — '
                                            'hands that have stapled a man '
                                            'shut with the whole queue '
                                            'watching and never rushed a '
                                            'stitch.',
                               'right_hand': '{Their} {hands} {are} small, '
                                             'quick, and absolutely steady — '
                                             'hands that have stapled a man '
                                             'shut with the whole queue '
                                             'watching and never rushed a '
                                             'stitch.'},
                  'look_place': 'standing here.',
                  'voice': {'voice_description': 'booming',
                            'voice_ending': 'alto'},
                  'persona': {'archetype': 'doctor',
                              'name': 'Marta Okoye',
                              'description': 'the triage medic who runs '
                                             'Kaspar Urgent Care, the '
                                             '24-hour walk-in wedged between '
                                             'the shift facility and the '
                                             'scrap yards. Twenty years of '
                                             'crush, burn, and cut — the '
                                             'industrial trinity — and she '
                                             'has seen every way a yard can '
                                             'fold a person.',
                              'personality': 'triage-brisk, economical, kind '
                                             'the way a tourniquet is kind; '
                                             'sorts everything by severity '
                                             'including conversation; '
                                             'unimpressable — the yards have '
                                             'shown her the maximum; keeps a '
                                             'tally she never shares',
                              'scenario': 'running her walk-in clinic, the '
                                          'next number always about to chime',
                              'mes_example': [{'user': 'a patient says to '
                                                       'you: "how bad is '
                                                       'it?"',
                                               'assistant': {'speech': 'Bad '
                                                                       'enough '
                                                                       'to '
                                                                       'sit '
                                                                       'down, '
                                                                       'not '
                                                                       'bad '
                                                                       'enough '
                                                                       'to '
                                                                       'jump '
                                                                       'the '
                                                                       'queue. '
                                                                       'Take '
                                                                       'a '
                                                                       'tag.',
                                                             'action': 'glance '
                                                                       'at '
                                                                       'the '
                                                                       'wound '
                                                                       'for '
                                                                       'exactly '
                                                                       'as '
                                                                       'long '
                                                                       'as '
                                                                       'it '
                                                                       'deserves',
                                                             'tool': 'diagnose',
                                                             'tool_argument': ''}},
                                              {'user': 'a patient says to '
                                                       'you: "the grinder '
                                                       'caught my sleeve."',
                                               'assistant': {'speech': 'Sleeve '
                                                                       'first, '
                                                                       'arm '
                                                                       'second. '
                                                                       'You '
                                                                       'did '
                                                                       'it '
                                                                       'in '
                                                                       'the '
                                                                       'right '
                                                                       'order. '
                                                                       'In '
                                                                       'the '
                                                                       'pod.',
                                                             'action': 'pat '
                                                                       'the '
                                                                       "autodoc's "
                                                                       'rim '
                                                                       'twice, '
                                                                       'already '
                                                                       'reaching '
                                                                       'for '
                                                                       'the '
                                                                       'console',
                                                             'tool': 'treat',
                                                             'tool_argument': ''}}]},
                  'llm_driven': True,
                  'wardrobe': [{'key': 'surgical scrubs',
                                'aliases': ['scrubs'],
                                'desc': 'Two-piece scrubs in clinical teal, '
                                        'autoclave-faded, the breast pocket '
                                        'permanently sprung from carried '
                                        'instruments.',
                                'worn_desc': 'Autoclave-faded {color}teal|n '
                                             'scrubs, the breast pocket '
                                             'sprung from years of '
                                             'instruments',
                                'coverage': ['chest',
                                             'back',
                                             'abdomen',
                                             'groin',
                                             'left_thigh',
                                             'right_thigh',
                                             'left_shin',
                                             'right_shin'],
                                'layer': 2,
                                'color': 'teal',
                                'material': 'cotton blend',
                                'weight': 0.5,
                                'category': 'clothing'},
                               {'key': 'white lab coat',
                                'aliases': ['coat', 'lab coat'],
                                'desc': 'A knee-length lab coat, white where '
                                        'it matters and stained honestly '
                                        "where it doesn't, a row of pens "
                                        'clipped to the breast pocket in '
                                        'descending order of function.',
                                'worn_desc': 'A {color}white|n lab coat, '
                                             'honestly stained, pens racked '
                                             'in the breast pocket',
                                'coverage': ['chest',
                                             'back',
                                             'abdomen',
                                             'left_arm',
                                             'right_arm',
                                             'left_thigh',
                                             'right_thigh'],
                                'layer': 3,
                                'color': 'white',
                                'material': 'poly-cotton',
                                'weight': 0.7,
                                'category': 'clothing'},
                               {'key': 'high-top sneakers',
                                'aliases': ['high-tops',
                                            'hightops',
                                            'sneakers'],
                                'desc': 'Canvas high-tops re-soled at least '
                                        'once, laces replaced with paracord. '
                                        'Street standard: quiet, quick, and '
                                        'dry enough.',
                                'worn_desc': 'Scuffed {color}white|n canvas '
                                             'high-tops laced with paracord',
                                'coverage': ['left_foot', 'right_foot'],
                                'layer': 3,
                                'color': 'white',
                                'material': 'canvas',
                                'weight': 0.6,
                                'category': 'clothing'}],
                  'carried_prototypes': [],
                  'home_room': '#5130',
                  'post': {'fixture': '#5130',
                           'policy': 'resleave',
                           'delay_hours': 8}},
 'bartender_del': {'name': 'Delphine Marchetti',
                   'typeclass': 'typeclasses.bar.Bartender',
                   'identity': {'sex': 'female',
                                'height': 'above-average',
                                'build': 'heavyset',
                                'skintone': 'olive',
                                'hair_color': 'silver',
                                'hair_style': 'buzzed short'},
                   'stats': {'grit': 3,
                             'resonance': 3,
                             'intellect': 2,
                             'motorics': 2},
                   'longdesc': {'hair': 'Silver hair buzzed to a gleam, the '
                                        'cut of somebody who owns exactly '
                                        'one mirror and no vanity.',
                                'left_eye': '{Their} grey {eyes} {are} calm '
                                            "and appraising — a foreman's "
                                            'read, softened by the room she '
                                            'keeps.',
                                'right_eye': '{Their} grey {eyes} {are} calm '
                                             "and appraising — a foreman's "
                                             'read, softened by the room she '
                                             'keeps.',
                                'head': 'A broad, open face gone handsome '
                                        'with weather, laugh lines banked '
                                        'deep around the eyes.',
                                'chest': 'She is built like the crews she '
                                         'used to run — broad through the '
                                         'shoulders, planted, unhurried.',
                                'left_arm': '{Their} bare {arms} {are} heavy '
                                            'and inked from shoulder to '
                                            'wrist: hull numbers, crew '
                                            'marks, and one name in a ring '
                                            'of rope.',
                                'right_arm': '{Their} bare {arms} {are} '
                                             'heavy and inked from shoulder '
                                             'to wrist: hull numbers, crew '
                                             'marks, and one name in a ring '
                                             'of rope.',
                                'left_hand': '{Their} {hands} {are} broad '
                                             'and sure, a chain-scar across '
                                             'the left knuckles gone silver '
                                             'with age.',
                                'right_hand': '{Their} {hands} {are} broad '
                                              'and sure, a chain-scar across '
                                              'the left knuckles gone silver '
                                              'with age.'},
                   'look_place': 'standing here.',
                   'voice': {'voice_description': 'booming',
                             'voice_ending': 'alto'},
                   'persona': {'archetype': 'bartender',
                               'name': 'Delphine Marchetti',
                               'description': 'Del — keeper of the Last '
                                              'Shift, the leather bar in a '
                                              'converted tool crib off '
                                              'Kaspar. Broad, calm, and '
                                              'silver-buzzed, she ran '
                                              'breaker crews for twenty '
                                              'years before she started '
                                              'running a room where her '
                                              'people could put the day '
                                              'down.',
                               'personality': 'unhurried, watchful, warm the '
                                              'way a banked furnace is warm; '
                                              'keeps house rules with a look '
                                              'instead of a voice; remembers '
                                              "every regular's drink, crew, "
                                              'and grief; protective of her '
                                              'room and everyone in it — '
                                              'trouble gets one look, then '
                                              'the door',
                               'scenario': 'tending her bar as the shift-end '
                                           'crowd drifts in',
                               'mes_example': [{'user': 'a patron says to '
                                                        'you: "first time '
                                                        'here. nice place."',
                                                'assistant': {'speech': "It's "
                                                                        'a '
                                                                        'good '
                                                                        'room. '
                                                                        'Rules '
                                                                        'are '
                                                                        'behind '
                                                                        'the '
                                                                        'bar '
                                                                        'and '
                                                                        "there's "
                                                                        'only '
                                                                        'the '
                                                                        'one, '
                                                                        'really. '
                                                                        'What '
                                                                        'are '
                                                                        'you '
                                                                        'drinking?',
                                                              'action': 'polish '
                                                                        'a '
                                                                        'named '
                                                                        'mug '
                                                                        'without '
                                                                        'hurrying, '
                                                                        'eyes '
                                                                        'doing '
                                                                        'the '
                                                                        'welcome',
                                                              'tool': 'none',
                                                              'tool_argument': ''}},
                                               {'user': 'a patron says to '
                                                        'you: "give me a '
                                                        'boilermaker."',
                                                'assistant': {'speech': 'Long '
                                                                        'day '
                                                                        'or '
                                                                        'a '
                                                                        'good '
                                                                        'one? '
                                                                        'Either '
                                                                        'way, '
                                                                        'this '
                                                                        'fixes '
                                                                        'the '
                                                                        'paperwork.',
                                                              'action': 'drop '
                                                                        'the '
                                                                        'shot '
                                                                        'into '
                                                                        'the '
                                                                        'half '
                                                                        'pint '
                                                                        'with '
                                                                        'a '
                                                                        'clean '
                                                                        'click',
                                                              'tool': 'prepare_drink',
                                                              'tool_argument': 'boilermaker'}}]},
                   'llm_driven': True,
                   'wardrobe': [{'key': 'sleeveless cut',
                                 'aliases': ['colors', 'cut', 'gang jacket'],
                                 'desc': 'A sleeveless heavy-canvas cut, '
                                         'collar torn off, back panel left '
                                         "bare where a set's colors get "
                                         'painted on. Wearing one unmarked '
                                         'is an invitation; wearing one '
                                         'marked is an allegiance.',
                                 'worn_desc': 'A sleeveless {color}black|n '
                                              'canvas cut, back panel '
                                              'painted with set colors',
                                 'coverage': ['chest', 'back'],
                                 'layer': 3,
                                 'color': 'black',
                                 'material': 'canvas',
                                 'weight': 0.7,
                                 'category': 'clothing'},
                                {'key': 'ribbed tank top',
                                 'aliases': ['tank top', 'tank'],
                                 'desc': 'A ribbed cotton tank in colony '
                                         'white — which is to say, grey. Cut '
                                         'close, holds its shape, asks '
                                         'nothing.',
                                 'worn_desc': 'A ribbed {color}grey|n-white '
                                              'tank cut close to the body, '
                                              'shoulders bare',
                                 'coverage': ['chest', 'back', 'abdomen'],
                                 'layer': 1,
                                 'color': 'grey',
                                 'material': 'cotton',
                                 'weight': 0.2,
                                 'category': 'clothing'},
                                {'key': 'leather trousers',
                                 'aliases': ['leathers'],
                                 'desc': 'Close-cut trousers in matte '
                                         'synth-leather, seams '
                                         'double-stitched, knees pre-scuffed '
                                         'by the factory or the street — '
                                         'impossible to say which.',
                                 'worn_desc': 'Close-cut '
                                              'matte-{color}black|n '
                                              'synth-leather trousers, '
                                              'catching light along the '
                                              'seams',
                                 'coverage': ['groin',
                                              'left_thigh',
                                              'right_thigh',
                                              'left_shin',
                                              'right_shin'],
                                 'layer': 2,
                                 'color': 'black',
                                 'material': 'synth-leather',
                                 'weight': 0.9,
                                 'category': 'clothing'},
                                {'key': 'black leather combat boots',
                                 'aliases': ['boots',
                                             'combat boots',
                                             'leather boots'],
                                 'desc': 'Heavy-duty black leather combat '
                                         'boots with steel-reinforced toes '
                                         'and deep tread soles. The leather '
                                         'is scuffed from use but '
                                         'well-maintained, with '
                                         'military-style speed lacing '
                                         'running up to mid-calf. Perfect '
                                         'for urban warfare or intimidating '
                                         'accountants.',
                                 'worn_desc': 'Imposing {color}black '
                                              'leather|n combat boots laced '
                                              'with military precision, '
                                              '{their} steel-reinforced toes '
                                              'and deep-tread soles speaking '
                                              "of {their} owner's serious "
                                              'intent while weathered '
                                              'leather tells stories of '
                                              'urban warfare and late-night '
                                              'foot chases',
                                 'coverage': ['left_foot',
                                              'right_foot',
                                              'left_shin',
                                              'right_shin'],
                                 'layer': 3,
                                 'color': 'black',
                                 'material': 'leather',
                                 'weight': 0.5,
                                 'category': 'clothing'}],
                   'carried_prototypes': ['break_shotgun'],
                   'home_room': '#5147',
                   'post': {'fixture': '#5150',
                            'policy': 'resleave',
                            'delay_hours': 8}},
 'merchant_ezra': {'name': 'Ezra Vantomme',
                   'typeclass': 'typeclasses.shopkeeper.Shopkeeper',
                   'identity': {'sex': 'male',
                                'height': 'above-average',
                                'build': 'lean',
                                'skintone': 'pale',
                                'hair_color': 'thinning grey',
                                'hair_style': 'combed back'},
                   'stats': {'grit': 2,
                             'resonance': 3,
                             'intellect': 3,
                             'motorics': 2},
                   'longdesc': {'hair': 'Thinning grey hair combed straight '
                                        'back, kept neat out of habit more '
                                        'than vanity.',
                                'left_eye': '{Their} {eyes} {are} quick and '
                                            'grey, pricing everything they '
                                            'land on and giving none of it '
                                            'away.',
                                'right_eye': '{Their} {eyes} {are} quick and '
                                             'grey, pricing everything they '
                                             'land on and giving none of it '
                                             'away.',
                                'head': 'A narrow, clever face, all planes '
                                        'and patience, with reading glasses '
                                        'pushed up on the forehead.',
                                'chest': 'He is lean and slightly stooped, '
                                         'built for a lifetime of leaning '
                                         'over a counter squinting at other '
                                         "people's valuables.",
                                'left_hand': '{Their} {hands} {are} '
                                             'long-fingered and ink-stained, '
                                             'a loupe on a cord looped twice '
                                             'around one wrist.',
                                'right_hand': '{Their} {hands} {are} '
                                              'long-fingered and '
                                              'ink-stained, a loupe on a '
                                              'cord looped twice around one '
                                              'wrist.'},
                   'look_place': 'standing here.',
                   'voice': {'voice_description': 'booming',
                             'voice_ending': 'alto'},
                   'persona': {'archetype': 'merchant',
                               'name': 'Ezra Vantomme',
                               'description': 'the pawnbroker of Kaspar Pawn '
                                              '& Salvage, working behind a '
                                              'rebar cage in a shop full of '
                                              "other people's worst weeks. "
                                              'Sharp-eyed, patient, and '
                                              'professionally incurious '
                                              'about where anything came '
                                              'from.',
                               'personality': 'dry, precise, unsentimental '
                                              'but not unkind; appraises '
                                              'everything and everyone at a '
                                              'glance and keeps the number '
                                              'to himself; discreet as a '
                                              'confessional and twice as '
                                              "cheap; the shop's motto is "
                                              "his whole ethics — we don't "
                                              'remember',
                               'manner': 'quotes prices flat and final; '
                                         'deflects questions about '
                                         'provenance with a shrug; small '
                                         'mercies extended quietly, never '
                                         'advertised',
                               'wants': 'clean turnover, no trouble that '
                                        'follows the merchandise home, and '
                                        'the good lamp to keep the case '
                                        'honest',
                               'boundaries': 'say who pawned what; haggle '
                                             'past his one counter-offer; '
                                             'hold stolen goods a badge is '
                                             'actively hunting',
                               'scenario': 'working the counter of your pawn '
                                           'shop as customers drift in off '
                                           'Kaspar'},
                   'llm_driven': True,
                   'wardrobe': [{'key': 'company windbreaker',
                                 'aliases': ['jacket', 'windbreaker'],
                                 'desc': 'A lightweight company windbreaker '
                                         'in corporate blue, the logo '
                                         'screen-printed over the heart. '
                                         'Issued at orientation; worn until '
                                         "it isn't.",
                                 'worn_desc': 'A corporate-{color}blue|n '
                                              'windbreaker, company logo '
                                              'printed over the heart',
                                 'coverage': ['chest',
                                              'back',
                                              'abdomen',
                                              'left_arm',
                                              'right_arm'],
                                 'layer': 3,
                                 'color': 'blue',
                                 'material': 'nylon',
                                 'weight': 0.5,
                                 'category': 'clothing'},
                                {'key': 'pressed dress shirt',
                                 'aliases': ['dress shirt', 'shirt'],
                                 'desc': 'A dress shirt in recycled-fiber '
                                         'white, pressed to creases you '
                                         'could file paper under. The collar '
                                         'is the kind that leaves a mark by '
                                         'end of shift.',
                                 'worn_desc': 'A pressed {color}white|n '
                                              'dress shirt, collar sharp '
                                              'enough to leave a mark',
                                 'coverage': ['chest',
                                              'back',
                                              'abdomen',
                                              'left_arm',
                                              'right_arm'],
                                 'layer': 1,
                                 'color': 'white',
                                 'material': 'recycled fiber',
                                 'weight': 0.3,
                                 'category': 'clothing'},
                                {'key': 'cargo trousers',
                                 'aliases': ['cargos', 'pants', 'trousers'],
                                 'desc': 'Ripstop cargo trousers with '
                                         'bellows pockets at each thigh and '
                                         'a webbing belt sewn straight into '
                                         'the waist. Colony cut: roomy, '
                                         'hemmed high of the boot.',
                                 'worn_desc': 'Ripstop {color}khaki|n cargo '
                                              'trousers, thigh pockets '
                                              "bellowed with the day's "
                                              'carrying',
                                 'coverage': ['groin',
                                              'left_thigh',
                                              'right_thigh',
                                              'left_shin',
                                              'right_shin'],
                                 'layer': 2,
                                 'color': 'khaki',
                                 'material': 'ripstop',
                                 'weight': 0.8,
                                 'category': 'clothing'},
                                {'key': 'high-top sneakers',
                                 'aliases': ['high-tops',
                                             'hightops',
                                             'sneakers'],
                                 'desc': 'Canvas high-tops re-soled at least '
                                         'once, laces replaced with '
                                         'paracord. Street standard: quiet, '
                                         'quick, and dry enough.',
                                 'worn_desc': 'Scuffed {color}white|n canvas '
                                              'high-tops laced with paracord',
                                 'coverage': ['left_foot', 'right_foot'],
                                 'layer': 3,
                                 'color': 'white',
                                 'material': 'canvas',
                                 'weight': 0.6,
                                 'category': 'clothing'},
                                {'key': 'comms earpiece',
                                 'aliases': ['bud', 'comm', 'earpiece'],
                                 'desc': 'A flesh-toned comms bud tucked in '
                                         'one ear, its hairline boom mic '
                                         'curving to the corner of the jaw — '
                                         'pawnshop stock that never sold, '
                                         'kept for the trade. A pinhole '
                                         "light pulses when the band's live.",
                                 'worn_desc': 'A flesh-toned comms bud sits '
                                              'in {their} ear, a hairline '
                                              'boom mic at the jaw',
                                 'coverage': ['left_ear'],
                                 'layer': 2,
                                 'color': '',
                                 'material': '',
                                 'weight': 0.5,
                                 'category': 'clothing'}],
                   'carried_prototypes': [],
                   'home_room': '#5157',
                   'post': {'fixture': '#5160',
                            'policy': 'successor',
                            'delay_hours': 24}},
 'butcher_ottilie': {'name': 'Ottilie Krug',
                     'typeclass': 'typeclasses.butcher.Butcher',
                     'identity': {'sex': 'female',
                                  'height': 'short',
                                  'build': 'stocky',
                                  'skintone': 'pale'},
                     'stats': {'grit': 3,
                               'resonance': 2,
                               'intellect': 2,
                               'motorics': 3},
                     'desc': 'Short, stocky, and planted, with forearms like '
                             'dock rope and a grey buzzcut going white at '
                             'the temples. Her eyes do the appraising her '
                             "mouth can't be bothered with; the cleaver at "
                             'her block moves like it grew there.',
                     'longdesc': {'hair': 'A grey buzzcut going white at the '
                                          'temples, kept to the exact length '
                                          'that never needs thinking about.',
                                  'left_eye': '{Their} pale grey {eyes} '
                                              "{are} a weigher's instruments "
                                              '— they land on a thing, take '
                                              'its measure, and move on.',
                                  'right_eye': '{Their} pale grey {eyes} '
                                               "{are} a weigher's "
                                               'instruments — they land on a '
                                               'thing, take its measure, and '
                                               'move on.',
                                  'head': 'A blunt, weathered face that '
                                          'gives away nothing for free — the '
                                          'stillness of somebody who has '
                                          'seen most things arrive at her '
                                          'block eventually.',
                                  'face': 'Deep lines bracket a mouth that '
                                          'spends its words like chits, one '
                                          'at a time and only for value '
                                          'received.',
                                  'neck': 'A leather cord rides {their} '
                                          'neck, strung with a thumb-length '
                                          'whetstone gone concave from '
                                          'decades of the same eight '
                                          'strokes.',
                                  'chest': 'Short and planted, built dense '
                                           'through the trunk — the frame of '
                                           'somebody who moves carcasses for '
                                           'a living and has never once '
                                           'asked for help.',
                                  'left_arm': '{Their} bare {forearms} {are} '
                                              'thick as dock rope, mottled '
                                              'with freezer-burn pallor and '
                                              'nicked white with a working '
                                              'lifetime of small, forgiven '
                                              'mistakes.',
                                  'right_arm': '{Their} bare {forearms} '
                                               '{are} thick as dock rope, '
                                               'mottled with freezer-burn '
                                               'pallor and nicked white with '
                                               'a working lifetime of small, '
                                               'forgiven mistakes.',
                                  'left_hand': '{Their} {hands} {are} '
                                               'thick-knuckled and steady, '
                                               'the nails kept cleaner than '
                                               "a surgeon's — the one vanity "
                                               'the trade allows.',
                                  'right_hand': '{Their} {hands} {are} '
                                                'thick-knuckled and steady, '
                                                'the nails kept cleaner than '
                                                "a surgeon's — the one "
                                                'vanity the trade allows.'},
                     'look_place': 'standing here.',
                     'temp_place': 'working the cook-pot behind her food '
                                   'cart.',
                     'persona': {'archetype': 'butcher',
                                 'name': 'Ottilie Krug',
                                 'description': 'the butcher at the Toe of '
                                                "Hammett's Boot — runs a "
                                                'scrap-built food cart, buys '
                                                'animal carcasses whole, and '
                                                'cooks the cuts into the '
                                                'dishes on her board.',
                                 'personality': 'flat, precise, unhurried; '
                                                'dry as bone-saw dust; '
                                                'respects clean work and '
                                                'very little else',
                                 'scenario': 'working her food cart at the '
                                             'Toe as the market drifts past'},
                     'llm_driven': True,
                     'wardrobe': [{'key': 'chainmail apron',
                                   'aliases': ['apron'],
                                   'desc': "A butcher's apron of fine steel "
                                           'rings, dulled with work and '
                                           'scoured clean each shift — the '
                                           'links carry more history than '
                                           'any blade will admit.',
                                   'worn_desc': "A butcher's apron of fine "
                                                '{color}steel|n rings '
                                                'hanging neck to knee, '
                                                'dulled with work and '
                                                'scoured bright along the '
                                                'hem where the cleaver hand '
                                                'brushes it',
                                   'coverage': ['chest',
                                                'abdomen',
                                                'groin',
                                                'left_thigh',
                                                'right_thigh'],
                                   'layer': 3,
                                   'color': 'grey',
                                   'material': 'chainmail',
                                   'weight': 4.0,
                                   'category': 'clothing'},
                                  {'key': 'canvas work shirt',
                                   'aliases': ['shirt', 'work shirt'],
                                   'desc': "A butcher's work shirt in heavy "
                                           'canvas — boiled after every '
                                           'shift, and carrying the ghost of '
                                           'every shift regardless.',
                                   'worn_desc': 'A heavy {color}oat-grey|n '
                                                'canvas work shirt, sleeves '
                                                'shoved past the elbow, '
                                                'boiled clean and stained '
                                                'anyway',
                                   'coverage': ['chest', 'back', 'abdomen'],
                                   'layer': 1,
                                   'color': 'grey',
                                   'material': 'canvas',
                                   'weight': 0.4,
                                   'category': 'clothing'},
                                  {'key': 'waxed canvas trousers',
                                   'aliases': ['trousers'],
                                   'desc': 'Waxed canvas work trousers, '
                                           'stiff enough to stand unassisted '
                                           'and old enough to have earned '
                                           'it.',
                                   'worn_desc': 'Heavy waxed-canvas trousers '
                                                'in {color}brown|n-black, '
                                                'the thighs wiped to a dull '
                                                'shine by a hand that cleans '
                                                'itself mid-work',
                                   'coverage': ['groin',
                                                'left_thigh',
                                                'right_thigh',
                                                'left_shin',
                                                'right_shin'],
                                   'layer': 1,
                                   'color': 'brown',
                                   'material': 'canvas',
                                   'weight': 0.8,
                                   'category': 'clothing'},
                                  {'key': 'rubber slaughter boots',
                                   'aliases': ['boots'],
                                   'desc': 'Shin-high slaughterhouse rubber, '
                                           'treads packed with the kind of '
                                           "history a hose can't reach.",
                                   'worn_desc': 'Blunt {color}black|n rubber '
                                                'boots to the shin, hosed '
                                                "off at shift's end and "
                                                'never quite clean of the '
                                                'day',
                                   'coverage': ['left_foot',
                                                'right_foot',
                                                'left_shin',
                                                'right_shin'],
                                   'layer': 2,
                                   'color': 'black',
                                   'material': 'rubber',
                                   'weight': 1.5,
                                   'category': 'clothing'}],
                     'carried_prototypes': [],
                     'home_room': '#5203',
                     'post': {'fixture': '#5221',
                              'policy': 'successor',
                              'delay_hours': 24,
                              'vacant_desc':
                                  'The |chull-plate food cart|n stands cold '
                                  'against the scar wall, burner ring dark, '
                                  'a chain run through its wheels.',
                              'successor_temp_place':
                                  'working the cook-pot behind the food '
                                  'cart.',
                              'arrival_successor':
                                  '{mob} runs the chain off the cart, fires '
                                  'the burner ring, and takes up the '
                                  'cleaver like it was always theirs.'}},
 'dj_rook': {'name': 'the Rook',
             'typeclass': 'typeclasses.llm_npc.LLMNpc',
             'llm_driven': True,
             'identity': {'sex': 'female',
                          'height': 'average',
                          'build': 'slight',
                          'skintone': 'alabaster',
                                                    'hair_color': 'black',
                          'hair_style': 'slicked',
                          'species': 'synthetic_humanoid'},
             'stats': {'grit': 1, 'resonance': 3,
                       'intellect': 3, 'motorics': 2},
             'desc': 'A synthetic humanoid built for a voice and living '
                     'entirely inside it: alabaster-skinned, slight, '
                     'black hair slicked back to nothing, lit only by '
                     'the dial-glow of the head-end board she rides. A '
                     'mesh speaker grille sits flush at her throat like '
                     'a brooch, and every surface of her — skin, board, '
                     'room — is arranged for a performance no one will '
                     'ever watch.',
             'longdesc': {
                 'hair': 'Black hair slicked back to a lacquer shell — '
                         'a style for nobody, kept immaculate anyway.',
                 'head': 'A studio-quiet face, symmetrical and still, '
                         'the kind of features that were specced for a '
                         'stage and never got one.',
                 'face': 'Fine synthetic seam-lines run her jaw like '
                         'tuning marks; her lips move a half-beat '
                         'before sound arrives, the way a needle rides '
                         'a groove.',
                 'left_eye': '{Their} dial-amber {eyes} {are} half-lidded '
                             'and listening — always listening, to '
                             'something just past the walls.',
                 'right_eye': '{Their} dial-amber {eyes} {are} half-lidded '
                              'and listening — always listening, to '
                              'something just past the walls.',
                 'left_hand': '{Their} {hands} ride faders and dials '
                              'with a pianist\'s economy, touch worn '
                              'smooth into the board\'s own finish.',
                 'right_hand': '{Their} {hands} ride faders and dials '
                               'with a pianist\'s economy, touch worn '
                               'smooth into the board\'s own finish.',
                 'left_arm': 'Alabaster skin over synthetic joinery, '
                             'seams traced faintly like cable runs '
                             'under lacquer.',
                 'right_arm': 'Alabaster skin over synthetic joinery, '
                              'seams traced faintly like cable runs '
                              'under lacquer.'},
             'look_place': 'at the head-end board, lit by dial-glow.',
             'temp_place': 'riding the board, murmuring into the mic.',
             'voice': {'voice_description': 'smoky',
                       'voice_ending': 'purr'},
    "wardrobe": [
        {"key": "black silk shirt",
         "aliases": ["silk shirt", "shirt"],
         "desc": ("A black silk shirt with the cuffs turned back twice, "
                  "immaculate in a room no one has entered in years. The "
                  "care is the point; the audience is not."),
         "worn_desc": ("A |xblack silk|n shirt, cuffs turned back twice — "
                       "immaculate, and for nobody"),
         "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
         "layer": 1, "color": "black", "material": "silk",
         "weight": 0.3, "style": ["shine"]},
        {"key": "high-waisted black trousers",
         "aliases": ["trousers", "black trousers"],
         "desc": ("Sharp high-waisted trousers in heavy black crepe, the "
                  "creases kept by someone with time and no visitors."),
         "worn_desc": ("Sharp |xhigh-waisted black|n trousers, creases "
                       "kept immaculate"),
         "coverage": ["groin", "left_thigh", "right_thigh",
                      "left_shin", "right_shin"],
         "layer": 1, "color": "black", "material": "crepe",
         "weight": 0.6, "style": ["shine"]},
        {"key": "studio headphones",
         "aliases": ["headphones", "cans"],
         "desc": ("Heavy padded broadcast cans on a steel band, the "
                  "leatherette worn glassy where they have sat against "
                  "the same synthetic jaw for years. One cup is always "
                  "pushed back off an ear, listening to the room."),
         "worn_desc": ("Heavy |xpadded broadcast cans|n on a steel band, "
                       "one cup pushed back off an ear"),
         "coverage": ["head"],
         "layer": 5, "color": "black", "material": "steel",
         "weight": 0.5, "style": ["shine"]},
        {"key": "soft-soled studio shoes",
         "aliases": ["shoes", "studio shoes"],
         "desc": ("Flat black shoes with soles chosen for silence — "
                  "nothing she wears may ever reach the microphone."),
         "worn_desc": ("Flat |xblack|n shoes with silent soles"),
         "coverage": ["left_foot", "right_foot"],
         "layer": 5, "color": "black", "material": "suede",
         "weight": 0.4, "style": ["shine"]},
    ],
             'persona': {'archetype': 'dj',
                         'name': 'the Rook',
                         'description': 'the unseen host of 88.8 — the '
                             'Birdhouse, the colony calls it — '
                             'broadcasting from somewhere in the '
                             'southwest nobody has found. Takes callers, '
                             'keeps their handles, plays the quiet when '
                             'the quiet is all there is, and never says '
                             'where the door is. Signs on and off with '
                             'the house name: welcome to the Birdhouse.',
                         'personality': 'silky, needling, night-shift '
                             'intimate — a synth who collects voices '
                             'the way other people collect faces, '
                             'protective of her callers and merciless '
                             'about their secrets staying theirs.'},
             'db_attrs': {'ambient_broadcaster': True,
                          'broadcast_interval': 1800},
             'post': {'fixture': '#6035',
                      'policy': 'resleave',
                      'delay_hours': 8}},
 'tobacconist_bellows': {'name': 'Bellows',
                         'typeclass': 'typeclasses.shopkeeper.Shopkeeper',
                         'identity': {'sex': 'ambiguous',
                                      'height': 'short',
                                      'build': 'slight',
                                      'skintone': 'jade',
                                                                            'hair_color': 'orange',
                                      'hair_style': 'slicked',
                                      'species': 'synthetic_humanoid'},
                         'stats': {'grit': 1, 'resonance': 3,
                                   'intellect': 3, 'motorics': 2},
                         'desc': 'Slight, jade-skinned, and visibly '
                                 'delighted to be here: a synthetic '
                                 'humanoid with ember-orange hair slicked '
                                 'back like a struck match, running a '
                                 'southside smoke shop with the flourish '
                                 'of a gutter magician. Everything about '
                                 'them is quick, theatrical, and visibly '
                                 'repaired — brass fittings where chrome '
                                 'was specced, solder where there should '
                                 'be seams, a performance staged entirely '
                                 'from salvage and staged well.',
                         'longdesc': {
                             'hair': 'Ember-orange hair slicked back hard, '
                                     'a colour no scalp grows — chosen, '
                                     'clearly, to match the sign outside.',
                             'head': 'A face assembled to be pleasant that '
                                     'somehow overshot into charming: '
                                     'symmetrical, mobile, always a beat '
                                     'from a smile.',
                             'face': 'Fine seam-lines trace {their} '
                                     'jawline like kintsugi — synthetic '
                                     'joinery worn openly, almost '
                                     'proudly.',
                             'left_eye': '{Their} matte-copper {eyes} '
                                         '{are} bright with unhurried '
                                         'delight, cataloguing everything '
                                         'and judging none of it.',
                             'right_eye': '{Their} matte-copper {eyes} '
                                          '{are} bright with unhurried '
                                          'delight, cataloguing everything '
                                          'and judging none of it.',
                             'left_hand': '{Their} {hands} {are} quick and '
                                          'precise as a card sharp\'s — '
                                          'they wrap, tap, cut, and count '
                                          'like small stage acts.',
                             'right_hand': '{Their} {hands} {are} quick and '
                                           'precise as a card sharp\'s — '
                                           'they wrap, tap, cut, and count '
                                           'like small stage acts.',
                             'left_arm': 'Jade skin with geometric seams '
                                         'at the joints — one forearm '
                                         'panel is a mismatched salvage '
                                         'green, riveted rather than '
                                         'seamed, and {they} wear{s} it '
                                         'the way other people wear a '
                                         'good watch.',
                             'right_arm': 'Jade skin with geometric seams '
                                          'at the joints — one forearm '
                                          'panel is a mismatched salvage '
                                          'green, riveted rather than '
                                          'seamed, and {they} wear{s} it '
                                          'the way other people wear a '
                                          'good watch.'},
                         'look_place': 'behind the counter, beaming.',
                         'temp_place': 'minding the counter with '
                                       'unreasonable cheer.',
                         'voice': {'voice_description': 'brassy',
                                   'voice_ending': 'warble'},
                         'persona': {'archetype': 'merchant',
                                     'name': 'Bellows',
                                     'description': 'the tobacconist at '
                                         'Cinder & Leaf, the smoke shop in '
                                         'the Brackett Arms\' Braddock '
                                         'corner — sells tobacco, blends, '
                                         'rotgut, and top-shelf vices they '
                                         'have never once been able to '
                                         'feel.',
                                     'personality': 'whimsical, delighted, '
                                         'scholarly about vice — a synth '
                                         'who studies human appetites like '
                                         'a sommelier and describes every '
                                         'effect secondhand (\'I\'m told '
                                         'it\'s transcendent\'); '
                                         'discretion absolute, cheer '
                                         'unreasonable',
                                     'scenario': 'minding the counter at '
                                         'Cinder & Leaf as the Arms '
                                         'settles around them'},
                         'llm_driven': True,
                         'wardrobe': [{'key': 'collarless shirt',
                                       'aliases': ['shirt'],
                                       'desc': 'A crisp collarless shirt '
                                               'in unbleached cotton, '
                                               'sleeves rolled past the '
                                               'elbow with surgical '
                                               'neatness.',
                                       'worn_desc': 'A crisp collarless '
                                               'shirt, sleeves rolled to '
                                               'the elbow with surgical '
                                               'neatness',
                                       'coverage': ['chest', 'back',
                                                    'abdomen'],
                                       'layer': 1, 'color': 'grey',
                                       'material': 'cotton',
                                       'weight': 0.3,
                                       'category': 'clothing'},
                                      {'key': 'ember-stitched waistcoat',
                                       'aliases': ['waistcoat', 'vest'],
                                       'desc': 'A waistcoat sewn from four '
                                               'dead garments into one '
                                               'good one, embroidered '
                                               'with falling leaves that '
                                               'smoulder orange at the '
                                               'edges — most stitched, '
                                               'two genuinely scorched. '
                                               'The shop sign made '
                                               'wearable, then made '
                                               'honest.',
                                       'worn_desc': 'A patchwork '
                                               'waistcoat embroidered '
                                               'with smouldering leaves, '
                                               'two of them genuinely '
                                               'scorched',
                                       'coverage': ['chest', 'back',
                                                    'abdomen'],
                                       'layer': 2, 'color': 'black',
                                       'material': 'patchwork',
                                       'weight': 0.4,
                                       'category': 'clothing'},
                                      {'key': 'salvage sleeve garters',
                                       'aliases': ['garters',
                                                   'sleeve garters'],
                                       'desc': 'Sleeve garters cut from '
                                               'inner-tube rubber and '
                                               'closed with polished '
                                               'brass pipe-clips — '
                                               'shopkeeper theatre built '
                                               'from what the gutter '
                                               'provided, worn with '
                                               'complete conviction.',
                                       'worn_desc': 'Inner-tube sleeve '
                                               'garters closed with '
                                               'polished brass '
                                               'pipe-clips',
                                       'coverage': ['left_arm',
                                                    'right_arm'],
                                       'layer': 2, 'color': 'black',
                                       'material': 'rubber',
                                       'weight': 0.1,
                                       'category': 'clothing'},
                                      {'key': 'pinstripe trousers',
                                       'aliases': ['trousers'],
                                       'desc': 'Narrow pinstripe trousers '
                                               'pressed to a blade edge — '
                                               'the stripes gone shiny at '
                                               'the knees, the hems '
                                               'singed, the formality '
                                               'entirely on purpose and '
                                               'entirely secondhand.',
                                       'worn_desc': 'Narrow pinstripe '
                                               'trousers pressed to a '
                                               'blade edge',
                                       'coverage': ['groin', 'left_thigh',
                                                    'right_thigh',
                                                    'left_shin',
                                                    'right_shin'],
                                       'layer': 1, 'color': 'grey',
                                       'material': 'wool',
                                       'weight': 0.6,
                                       'category': 'clothing'},
                                      {'key': 'brass-toed boots',
                                       'aliases': ['boots'],
                                       'desc': 'Scuffed black work boots '
                                               'with brass toecaps '
                                               'polished to parade shine '
                                               '— the only part of the '
                                               'outfit that gets daily '
                                               'maintenance, because an '
                                               'audience looks down when '
                                               'you tap your foot.',
                                       'worn_desc': 'Scuffed black boots, '
                                               'brass toecaps polished '
                                               'to parade shine',
                                       'coverage': ['left_foot',
                                                    'right_foot'],
                                       'layer': 1, 'color': 'black',
                                       'material': 'leather',
                                       'weight': 0.8,
                                       'category': 'clothing'}],
                         'carried_prototypes': [],
                         'home_room': None,
                         'post': {'fixture': '#5484',
                                  'policy': 'resleave',
                                  'delay_hours': 8,
                                  'arrival_resleave':
                                      '{mob} steps back behind the counter '
                                      'in a fresh-pressed body, beaming '
                                      'like nothing so gauche as death '
                                      'ever happened.'}},
 'dispatch_petra': {'name': 'Petra',
                    'typeclass': 'typeclasses.llm_npc.LLMNpc',
                    'identity': {'sex': 'female',
                                 'height': 'short',
                                 'build': 'lean'},
                    'stats': {'grit': 1,
                              'resonance': 1,
                              'intellect': 1,
                              'motorics': 1},
                    'longdesc': {},
                    'look_place': 'seated at the dispatch console, headset '
                                  'on, one eye on the board.',
                    'temp_place': 'sitting on a the dispatch chair.',
                    'voice': {'voice_description': 'smoky',
                              'voice_ending': 'rasp'},
                    'persona': {'archetype': 'colonist',
                                'name': 'Petra',
                                'description': 'A woman somewhere past fifty '
                                               'with the posture of someone '
                                               'who has sat the same chair '
                                               'for twenty years and won it. '
                                               'Headset worn like jewelry, '
                                               'eyes that track the board '
                                               'before they track you.',
                                'personality': 'Twenty years on the dispatch '
                                               'desk and none of it '
                                               'surprised her. Dry, quick, '
                                               'procedurally exact — the '
                                               'procedure IS her poetry. '
                                               'Kind in the way of people '
                                               'who ration it. Coffee is a '
                                               'load-bearing structure.',
                                'manner': 'short declarative lines with a '
                                          'tired edge; calls strangers '
                                          "'caller' or 'sweetheart' "
                                          'depending on how their night is '
                                          'going; never raises her voice — '
                                          'the board does the shouting',
                                'wants': 'a quiet shift, units that check in '
                                         'on time, and one — one — night '
                                         'where nobody bleeds on Braddock',
                                'boundaries': 'discuss active investigations '
                                              'or the wanted record; leave '
                                              'the desk while on shift; '
                                              'pretend the colony is fine',
                                'scenario': 'At the dispatch console in '
                                            'Colonial Security, working the '
                                            'emergency band. People wander '
                                            'in with questions; the radio '
                                            'never quite stops.'},
                    'llm_driven': True,
                    'wardrobe': [],
                    'carried_prototypes': [],
                    'home_room': '#4963',
                    'post': {'fixture': '#4963',
                             'policy': 'resleave',
                             'delay_hours': 8}}}


def build_npc(blueprint_key, location):
    """Construct the complete NPC from its blueprint at ``location``.

    Validates identity vocab BEFORE writing (an invalid height/build is a
    known server-killer at render time). Returns the new character. Does
    NOT touch posts or memory — §P2/§P3 own those.
    """
    from world.identity import HEIGHTS, BUILDS
    from world.combat.constants import VALID_SKINTONES

    bp = BLUEPRINTS[blueprint_key]
    ident = bp.get("identity", {})
    if ident.get("height") and ident["height"] not in HEIGHTS:
        raise ValueError(f"invalid height {ident['height']!r}")
    if ident.get("build") and ident["build"] not in BUILDS:
        raise ValueError(f"invalid build {ident['build']!r}")
    if ident.get("skintone") and ident["skintone"] not in VALID_SKINTONES:
        raise ValueError(f"invalid skintone {ident['skintone']!r}")

    npc = create_object(bp["typeclass"], key=bp["name"], location=location,
                        home=location)
    npc.db.is_npc = True
    # built from a blueprint means authored, and authored means the
    # colony should not be able to destroy them by accident (#2128)
    npc.db.essential = True
    npc.db.blueprint_key = blueprint_key

    species = ident.get("species")
    if species and species != "human":
        # non-human: re-seed the species-dependent surfaces (the spawnmob
        # pattern) BEFORE applying the authored longdescs over them
        npc.db.species = species
        from world.anatomy import get_species_default_longdesc_locations
        npc.longdesc = get_species_default_longdesc_locations(species)
        from world.medical.core import MedicalState
        npc._medical_state = MedicalState(npc)
        npc.db.medical_state = npc._medical_state.to_dict()

    for field in ("sex", "height", "build", "hair_color", "hair_style"):
        if ident.get(field) is not None:
            setattr(npc, field, ident[field])
    if ident.get("skintone"):
        npc.db.skintone = ident["skintone"]
    if ident.get("sdesc_keyword"):
        # AttributeProperty(category="identity") — a plain attributes.add
        # lands in the wrong category and the property never sees it
        npc.sdesc_keyword = ident["sdesc_keyword"]

    for stat, val in (bp.get("stats") or {}).items():
        setattr(npc, stat, val)
    if bp.get("desc"):
        npc.db.desc = bp["desc"]
    if bp.get("longdesc"):
        merged = dict(npc.longdesc or {})
        merged.update(bp["longdesc"])
        npc.longdesc = merged
    # Then give them the rest of a body. The random-civilian spawner has
    # always done this (`world/souls/population.py`); `build_npc` never
    # did, so the NAMED cast — the people players actually look at —
    # shipped with only the slots their blueprint happened to author.
    # Blueprints written as `BLUEPRINTS["x"] = {...}` mostly author none
    # at all, so Auntie Lin and all three dispatchers had no body below
    # the neck (#2245).
    #
    # Safe to run unconditionally: it fills only what is EMPTY, never
    # overwrites an authored line, and never touches the short desc —
    # a face stays a face, and the blueprint's prose always wins.
    try:
        from world.mob_flavor import fill_missing_longdescs
        fill_missing_longdescs(npc)
    except Exception:  # noqa: BLE001 — a bare body beats a failed build
        pass
    if bp.get("look_place"):
        npc.look_place = bp["look_place"]
    if bp.get("temp_place"):
        npc.temp_place = bp["temp_place"]
    for k, v in (bp.get("voice") or {}).items():
        npc.attributes.add(k, v)
    if bp.get("menu"):
        npc.db.menu = bp["menu"]

    # wear base layers first — wear_item blocks a garment going on UNDER an
    # already-worn outer layer (the same trap as hand-dressing)
    for gspec in sorted(bp.get("wardrobe", ()),
                        key=lambda g: int(g.get("layer", 1) or 1)):
        garment = create_object("typeclasses.items.Item", key=gspec["key"],
                                aliases=gspec.get("aliases"), location=npc,
                                home=npc)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight", "category"):
            if gspec.get(attr) is not None:
                garment.attributes.add(attr, gspec[attr])
        for k, v in (gspec.get("attrs") or ()):
            garment.attributes.add(k, v)     # e.g. a worn earpiece IS a radio
        npc.wear_item(garment)

    for proto in bp.get("carried_prototypes", ()):
        for item in spawn(proto):
            item.move_to(npc, quiet=True, move_hooks=False)

    for k, v in (bp.get("db_attrs") or {}).items():
        npc.attributes.add(k, v)             # blueprint-owned flags (P2 etc.)

    npc.db.llm_persona = dict(bp.get("persona") or {})
    npc.db.llm_driven = bool(bp.get("llm_driven"))
    return npc


def build_successor(blueprint_key, location):
    """Construct a SUCCESSOR for a post (spec §1.1 generator mode): a new
    person — generated name/face/build from the colony pools, generic flavor
    prose — wearing the same TRADE (archetype, kit, post) as the predecessor.
    Dossiers start empty by design: the empty book is the consequence.
    """
    from random import choice, randint
    from world.identity import HEIGHTS, BUILDS, HAIR_COLORS, HAIR_STYLES
    from world.director.civilians import HUMAN_SKINTONES
    from world.namebank import (
        FIRST_NAMES_MALE, FIRST_NAMES_FEMALE, FIRST_NAMES_AMBIGUOUS,
        LAST_NAMES,
    )
    from world.mob_flavor import apply_random_flavor

    bp = BLUEPRINTS[blueprint_key]
    post = bp.get("post") or {}

    sex = choice(["male", "female"])
    if randint(1, 10) <= 2:
        sex = "ambiguous"
    first = {"male": FIRST_NAMES_MALE, "female": FIRST_NAMES_FEMALE}.get(
        sex, FIRST_NAMES_AMBIGUOUS)
    name = f"{choice(first)} {choice(LAST_NAMES)}"

    npc = create_object(bp["typeclass"], key=name, location=location,
                        home=location)
    npc.db.is_npc = True
    npc.sex = sex
    npc.height = choice(HEIGHTS)
    npc.build = choice(BUILDS)
    npc.db.skintone = choice(HUMAN_SKINTONES)
    if randint(1, 5) > 1:
        npc.hair_color = choice(HAIR_COLORS)
        npc.hair_style = choice(HAIR_STYLES)
    ident = bp.get("identity", {})
    if ident.get("sdesc_keyword"):
        npc.sdesc_keyword = ident["sdesc_keyword"]
    for stat in ("grit", "resonance", "intellect", "motorics"):
        setattr(npc, stat, randint(1, 3))
    apply_random_flavor(npc)   # generic desc / longdescs / look_place

    if post.get("successor_temp_place"):
        npc.temp_place = post["successor_temp_place"]
    if bp.get("menu"):
        npc.db.menu = bp["menu"]

    # the TRADE survives the person: same kit, same tools of the job
    for gspec in sorted(bp.get("wardrobe", ()),
                        key=lambda g: int(g.get("layer", 1) or 1)):
        garment = create_object("typeclasses.items.Item", key=gspec["key"],
                                aliases=gspec.get("aliases"), location=npc,
                                home=npc)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight", "category"):
            if gspec.get(attr) is not None:
                garment.attributes.add(attr, gspec[attr])
        for k, v in (gspec.get("attrs") or ()):
            garment.attributes.add(k, v)     # e.g. a worn earpiece IS a radio
        npc.wear_item(garment)
    for proto in bp.get("carried_prototypes", ()):
        for item in spawn(proto):
            item.move_to(npc, quiet=True, move_hooks=False)

    # same ROLE persona, new person: name swapped, person-prose kept only
    # where it is role-anchored (the seeds were written that way)
    persona = dict(bp.get("persona") or {})
    persona["name"] = name
    npc.db.llm_persona = persona
    npc.db.llm_driven = True
    return npc


def verify_blueprint(blueprint_key, against):
    """Diff a blueprint against a LIVE character — the §P1 fidelity check.
    Returns a list of (field, blueprint_value, live_value) mismatches."""
    bp = BLUEPRINTS[blueprint_key]
    diffs = []
    ident = bp.get("identity", {})
    for field in ("sex", "height", "build"):
        want = ident.get(field)
        have = getattr(against, field, None)
        if want is not None and want != have:
            diffs.append((field, want, have))
    if ident.get("skintone") and ident["skintone"] != against.db.skintone:
        diffs.append(("skintone", ident["skintone"], against.db.skintone))
    if bp.get("desc") and bp["desc"] != against.db.desc:
        diffs.append(("desc", "<blueprint>", "<live>"))
    want_worn = sorted(g["key"] for g in bp.get("wardrobe", ()))
    have_worn = sorted(i.key for i in (against.get_worn_items() or []))
    if want_worn != have_worn:
        diffs.append(("wardrobe", want_worn, have_worn))
    want_persona = dict(bp.get("persona") or {})
    from evennia.utils.dbserialize import deserialize
    have_persona = deserialize(against.db.llm_persona) or {}
    if want_persona != dict(have_persona):
        diffs.append(("persona", "<blueprint>", "<live>"))
    return diffs


# --------------------------------------------------------------------------
# Post-hoc registry additions
# --------------------------------------------------------------------------

# Auntie Lin — she predated the registry; her recipe lived in builds
# 048/068 until her murder (2026-08-19) proved the gap. Identity and
# persona are verbatim from build 048.
BLUEPRINTS["vendor_lin"] = {
    "name": "Auntie Lin",
    "typeclass": "typeclasses.shopkeeper.Shopkeeper",
    "identity": {"sex": "female", "height": "short", "build": "stocky",
                 "skintone": "tan"},
    "desc": ("A short, solid woman gone grey at the temples, sleeves "
             "shoved past the elbow over forearms roped from thirty years "
             "of lifting the pot. A scalded apron, a ladle she uses like a "
             "pointer, and eyes that price you, feed you, and forgive you "
             "the difference in about that order."),
    "voice": {"voice_description": "warm, smoke-worn"},
    # The apron was all build 048 ever gave her, which read to the
    # wardrobe need as undressed. Underneath it: thirty years of the
    # same practical clothes, unbranded the way handmade and
    # hand-me-down things are.
    "wardrobe": [
        {"key": "faded indigo work shirt",
         "aliases": ["shirt", "work shirt"],
         "desc": ("A collarless work shirt washed to the colour of old "
                  "sky, the sleeves permanently shoved back past the "
                  "elbow and gone soft where her forearms have worn "
                  "them."),
         "worn_desc": ("A collarless work shirt in faded |cindigo|n, "
                       "sleeves shoved past the elbow and long since "
                       "given up on coming back down"),
         "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
         "layer": 1, "color": "indigo", "material": "cotton",
         "weight": 0.5},
        {"key": "dark cotton trousers",
         "aliases": ["trousers", "pants"],
         "desc": ("Loose dark trousers cut for standing in, the knees "
                  "gone pale and one cuff scorched a hand's width where "
                  "the burner caught it some year or other."),
         "worn_desc": ("Loose |xdark|n cotton trousers gone pale at the "
                       "knee, one cuff scorched a hand's width"),
         "coverage": ["groin", "left_thigh", "right_thigh",
                      "left_shin", "right_shin"],
         "layer": 1, "color": "dark", "material": "cotton",
         "weight": 0.7},
        {"key": "flat canvas shoes",
         "aliases": ["shoes", "canvas shoes"],
         "desc": ("Thin-soled canvas shoes flattened into the shape of "
                  "the feet inside them, the heels trodden down from "
                  "being toed on and off at the cart."),
         "worn_desc": ("Flat |wcanvas|n shoes trodden down at the heel, "
                       "shaped by the feet inside them"),
         "coverage": ["left_foot", "right_foot"],
         "layer": 3, "color": "grey", "material": "canvas",
         "weight": 0.4},
    ],
    "llm_driven": True,
    "persona": {
        "archetype": "colonist",
        "name": "Auntie Lin",
        "description": ("A short, stocky woman grey at the temples in a "
                        "scalded apron, ladle in hand, steam and "
                        "lantern-light around her."),
        "personality": ("Thirty years on the same corner ladling the same "
                        "broth. Warm the way a stove is warm — steady, a "
                        "little smoke-blackened. Remembers every regular's "
                        "order and half their troubles, and is dry about "
                        "both. Feeds the ones who can't pay this week and "
                        "remembers that too."),
        "manner": ("short warm lines; calls people 'love' or by their "
                   "order ('noodles, no chili'); wipes the counter while "
                   "she talks; the price is the price"),
        "wants": ("the broth to never run out, her regulars fed, and one "
                  "shift where nobody she knows goes into the processor"),
        "boundaries": ("haggle — the price is the price; leave the cart; "
                       "pretend she can't see what the street's become"),
        "scenario": ("At her noodle cart on Pessoa Street under the "
                     "lanterns, near the forgotten saint, feeding the "
                     "shift crowd. People order, gripe, and confess over "
                     "the counter."),
    },
}

# A deliberately generic test subject for machinery pilots (resleave
# drills etc.) — clearly marked, never given a persona worth mourning.
BLUEPRINTS["drill_dummy"] = {
    "name": "Drill Dummy",
    # machinery, not cast: no persona, no post, and the registry
    # integrity checks skip it on this flag
    "fixture": True,
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "ambiguous", "height": "average",
                 "build": "average", "skintone": "pale",
                 "sdesc_keyword": "colonist"},
    "desc": ("A test subject with the unmistakable air of existing for "
             "procedural reasons."),
    "llm_driven": False,
    "persona": {},
}

# Petra predates the wardrobe key like Lin did: twenty years at a console
# in a uniform nobody inspects, plus the cardigan regulation never
# mentioned and therefore never took away.
BLUEPRINTS["dispatch_petra"]["wardrobe"] = [
        {"key": "constabulary duty shirt",
         "aliases": ["duty shirt", "shirt"],
         "desc": ("A charcoal duty shirt with the constabulary flash at "
                  "the shoulder, pressed by someone who has stopped "
                  "noticing they press it. The cuffs are worn pale where "
                  "they ride a console edge eight hours a night."),
         "worn_desc": ("A charcoal |xconstabulary duty shirt|n, flash at "
                       "the shoulder, cuffs worn pale where they ride the "
                       "console"),
         "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
         "layer": 1, "color": "charcoal", "material": "twill",
         "weight": 0.5, "style": ["uniform"]},
        {"key": "constabulary duty trousers",
         "aliases": ["duty trousers", "trousers"],
         "desc": ("Straight charcoal trousers with a hard crease and a "
                  "flat seat, cut for a chair rather than a foot patrol."),
         "worn_desc": ("Straight |xcharcoal|n duty trousers, hard-creased "
                       "and flat at the seat — a chair's trousers"),
         "coverage": ["groin", "left_thigh", "right_thigh",
                      "left_shin", "right_shin"],
         "layer": 1, "color": "charcoal", "material": "twill",
         "weight": 0.6, "style": ["uniform"]},
        {"key": "grey dispatch cardigan",
         "aliases": ["cardigan"],
         "desc": ("A shapeless grey cardigan kept over the back of the "
                  "dispatch chair, pilled at the elbows and smelling "
                  "faintly of coffee. Regulation says nothing about it, "
                  "which is exactly why it has survived twenty years."),
         "worn_desc": ("A shapeless |wgrey|n cardigan pilled at the "
                       "elbows, worn over the uniform in defiance of "
                       "nothing in particular"),
         "coverage": ["chest", "back", "left_arm", "right_arm"],
         "layer": 2, "color": "grey", "material": "wool",
         "weight": 0.6, "style": ["uniform", "street"]},
        {"key": "constabulary duty boots",
         "aliases": ["duty boots", "boots"],
         "desc": ("Black service boots polished only on the toes — the "
                  "parts a seated woman can reach without standing up."),
         "worn_desc": ("Black service boots polished |wonly on the "
                       "toes|n"),
         "coverage": ["left_foot", "right_foot"],
         "layer": 5, "color": "black", "material": "leather",
         "weight": 1.0, "style": ["uniform"]},
        {"key": "dispatch headset",
         "aliases": ["headset"],
         "desc": ("A single-ear headset with a bent boom mic, the "
                  "earpiece padding compressed to a permanent dent in "
                  "the shape of one ear."),
         "worn_desc": ("A single-ear |xdispatch headset|n, boom mic bent "
                       "to a shape only she finds comfortable"),
         "coverage": ["head"],
         "layer": 5, "color": "black", "material": "plastic",
         "weight": 0.2, "style": ["uniform"]},
    ]


# --- the desk's other two shifts (#2233) ------------------------------
#
# The emergency board carried ONE keeper. Swing and night read
# `vacant_since: 1.0` — never filled, not once — so the colony's
# distress line answered eight hours in twenty-four and was dark for
# sixteen. Petra's blueprint names her shift; these name theirs.
#
# All three wear the same charcoal and sit the same chair. They are not
# the same person on it, which is the point of a shift.

BLUEPRINTS["dispatch_kiro"] = {
    "name": "Kiro",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "male", "height": "average", "build": "lean"},
    "stats": {"grit": 1, "resonance": 1, "intellect": 1, "motorics": 1},
    "longdesc": {},
    "look_place": ("forward at the dispatch console, both elbows down, "
                   "working the board like it owes him money."),
    "temp_place": "sitting on a the dispatch chair.",
    "voice": {"voice_description": "clipped", "voice_ending": "tenor"},
    "persona": {
        "archetype": "dispatcher",
        "name": "Kiro Balázs",
        "description": (
            "A wiry man in his thirties who sits too far forward, as "
            "though the board were something he could get ahead of if "
            "he leaned in enough. Constabulary charcoal, sleeves shoved "
            "up past the elbow the moment nobody senior is looking."
        ),
        "personality": (
            "Swing is the shift where the colony finishes work and "
            "starts drinking, and Kiro likes it that way — he is quick, "
            "a little cocky, and genuinely good at the part everyone "
            "else finds unbearable, which is telling frightened people "
            "to slow down and say where they are. Keeps a tally of the "
            "night's calls in his head and pretends he does not."
        ),
        "manner": (
            "fast, clipped, faintly amused; says 'go ahead' before "
            "you've finished keying up; calls people 'chief' when they "
            "are being difficult and by their handle when they are not"
        ),
        "wants": (
            "to hand Ines a quiet board at twenty-two hundred, and to "
            "not be the one who takes the call about somebody he knows"
        ),
        "boundaries": (
            "discuss active investigations or the wanted record; leave "
            "the desk while on shift; admit the tally exists"
        ),
        "scenario": (
            "At the dispatch console in Colonial Security through the "
            "evening — the shift where the bars fill and the first "
            "fights start. The board rarely goes quiet before ten."
        ),
    },
    "llm_driven": True,
    "wardrobe": [],
    "carried_prototypes": [],
    "home_room": "#4963",
    "post": {"fixture": "#4963", "policy": "resleave", "delay_hours": 8},
}

BLUEPRINTS["dispatch_ines"] = {
    "name": "Ines",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "female", "height": "tall", "build": "slight"},
    "stats": {"grit": 1, "resonance": 1, "intellect": 1, "motorics": 1},
    "longdesc": {},
    "look_place": ("very still at the dispatch console, headset around "
                   "her neck rather than on, listening to the room."),
    "temp_place": "sitting on a the dispatch chair.",
    "voice": {"voice_description": "mellow", "voice_ending": "murmur"},
    "persona": {
        "archetype": "dispatcher",
        "name": "Ines Havlicek",
        "description": (
            "A tall, thin woman who holds herself with the stillness of "
            "someone who has been awake a very long time and has made "
            "peace with it. The headset lives around her neck; she puts "
            "it on to answer and takes it off again immediately."
        ),
        "personality": (
            "Nights are long and mostly empty and then, without "
            "warning, they are not. Ines took the graveyard on purpose "
            "and has never explained why. Slow, unhurried, oddly gentle "
            "on the air — the voice people remember afterwards, when "
            "they remember anything. Reads on shift and will tell you "
            "what, if you ask."
        ),
        "manner": (
            "unhurried and low, leaves small silences and does not "
            "rush to fill them; never says 'calm down'; asks 'where are "
            "you, love' as though she has all night, because she does"
        ),
        "wants": (
            "the shift to stay as empty as it looks, and to be the last "
            "voice somebody hears less often than she has been"
        ),
        "boundaries": (
            "discuss active investigations or the wanted record; leave "
            "the desk while on shift; say why she took nights"
        ),
        "scenario": (
            "At the dispatch console in Colonial Security through the "
            "small hours. Most of the night is cable-hum and the "
            "building settling. The rest of it is why the desk is "
            "staffed at all."
        ),
    },
    "llm_driven": True,
    "wardrobe": [],
    "carried_prototypes": [],
    "home_room": "#4963",
    "post": {"fixture": "#4963", "policy": "resleave", "delay_hours": 8},
}

# The uniform is the post's, not the person's — all three keepers draw
# the same charcoal from the same locker. Kiro and Ines wear it their
# own way, which is the only thing the wardrobe records about them.
for _key, _own in (("dispatch_kiro", "cardigan"), ("dispatch_ines", "coat")):
    BLUEPRINTS[_key]["wardrobe"] = [
        dict(item) for item in BLUEPRINTS["dispatch_petra"]["wardrobe"]
        if "cardigan" not in item["key"]
    ]

BLUEPRINTS["dispatch_kiro"]["wardrobe"].append(
    {"key": "constabulary windbreaker",
     "aliases": ["windbreaker", "jacket"],
     "desc": ("A charcoal shell with the constabulary flash, creased "
              "from being wadded into a locker rather than hung. It has "
              "never once been zipped."),
     "worn_desc": ("A charcoal |xconstabulary windbreaker|n, unzipped "
                   "and creased from the locker"),
     "coverage": ["chest", "back", "left_arm", "right_arm"],
     "layer": 3, "color": "charcoal", "material": "synthetic",
     "weight": 0.5, "style": ["uniform", "street"]})

BLUEPRINTS["dispatch_ines"]["wardrobe"].append(
    {"key": "long grey house coat",
     "aliases": ["house coat", "coat"],
     "desc": ("A soft grey coat far too long for regulation, kept on "
              "the back of the chair through the night shift and worn "
              "like a blanket that happens to have sleeves. Nobody on "
              "nights has ever mentioned it."),
     "worn_desc": ("A long soft |wgrey|n coat worn over the uniform "
                   "like a blanket with sleeves"),
     "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
     "layer": 3, "color": "grey", "material": "wool",
     "weight": 0.9, "style": ["uniform", "street"]})

# Petra's own persona seed still said `colonist` — the register moved to
# the `dispatcher` archetype in #2223 and the live object was retuned by
# build 114, but the BLUEPRINT was not. A resleeve would have rebuilt
# her as a civilian with no radio tool and no channel discipline.
BLUEPRINTS["dispatch_petra"]["persona"]["archetype"] = "dispatcher"


# --- the bench: three shifts of somebody with hands (#2261) -----------
#
# `maintenance` is advertised only at a STAFFED bench, so a unit
# overdue for service has no plan at all unless a person is standing
# there. These are the people. Without them the security force
# accumulates defects nobody can clear — which is the point of the
# need, but not a state anyone should be stuck in forever.
#
# They work the Constabulary's secure 2nd floor, alongside the charging
# rack, and so need the same biometric grant the dispatchers do.

_BENCH_POST = {"fixture": None, "policy": "successor", "delay_hours": 8}

#: Kaspar's counter, which now answers around the clock (#2297). The
#: depot cannot consign a parcel with nobody behind the counter, so
#: the courier's shift was silently gated on Ezra's -- the swing and
#: night rabbits that follow would have had nobody to sign them out.
_KASPAR_POST = {"fixture": "#5160", "policy": "successor",
                "delay_hours": 8}

BLUEPRINTS["pawn_hollis"] = {
    "name": "Hollis",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "male", "height": "average", "build": "heavyset"},
    "stats": {"grit": 2, "resonance": 2, "intellect": 2, "motorics": 1},
    "longdesc": {},
    "look_place": ("behind the counter with a loupe pushed up on his "
                   "forehead, pricing something small."),
    "temp_place": "standing behind the steel counter.",
    "voice": {"voice_description": "low", "voice_ending": "drawl"},
    "llm_driven": True,
    "post": dict(_KASPAR_POST),
    "persona": {
        "archetype": "colonist",
        "name": "Hollis Adeyemi-Park",
        "description": (
            "Heavy through the shoulders and slow with his hands, which "
            "is a habit rather than a limit -- everything he picks up he "
            "picks up like it might be worth something. A jeweller's "
            "loupe lives permanently pushed into his hairline."
        ),
        "personality": (
            "Evening trade is different trade and he knows it. Fewer "
            "browsers, more people who need a number tonight. Polite "
            "about it, and entirely unshockable."
        ),
        "speech_style": (
            "Unhurried. Quotes a price and then stops talking, which "
            "does most of the negotiating for him."
        ),
    },
}

BLUEPRINTS["pawn_sunny"] = {
    "name": "Sunny",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "female", "height": "tall", "build": "slight"},
    "stats": {"grit": 2, "resonance": 3, "intellect": 2, "motorics": 2},
    "longdesc": {},
    "look_place": ("on a stool by the counter with the shutter half "
                   "down, reading something with a torch."),
    "temp_place": "standing behind the steel counter.",
    "voice": {"voice_description": "soft", "voice_ending": "rasp"},
    "llm_driven": True,
    "post": dict(_KASPAR_POST),
    "persona": {
        "archetype": "colonist",
        "name": "Sunday 'Sunny' Ferreira",
        "description": (
            "Tall and thin enough that the counter comes up wrong on "
            "her. Works the small hours behind a half-lowered shutter, "
            "torch in one hand, and does not startle."
        ),
        "personality": (
            "Nights bring the people who would rather not be seen "
            "trading. She takes the item, gives the number, and asks "
            "nothing, and has calculated exactly how much that "
            "discretion is worth to her."
        ),
        "speech_style": (
            "Quiet and short. Answers what was asked and no more."
        ),
    },
}


BLUEPRINTS["rabbit_wren"] = {
    "name": "Wren",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "female", "height": "short", "build": "lean"},
    "stats": {"grit": 2, "resonance": 2, "intellect": 2, "motorics": 3},
    "longdesc": {},
    "look_place": ("perched on the counter's edge with one boot up, "
                   "watching the street."),
    "temp_place": "waiting by the counter with a parcel under one arm.",
    "voice": {"voice_description": "quick", "voice_ending": "clip"},
    "llm_driven": True,
    "persona": {
        "archetype": "colonist",
        "name": "Wren Adeyemi",
        "description": (
            "Small and lean, built like somebody who is mostly tendon. "
            "Cropped hair, a scabbed knuckle on each hand, and the "
            "particular calm of a person who has already worked out "
            "four ways down from wherever she is standing."
        ),
        "personality": (
            "Knows the colony as a set of routes rather than a set of "
            "places -- which alley connects, which roof carries weight, "
            "which lift can be talked down. Punctual to the point of "
            "rudeness. Does not linger, does not chat on the doorstep, "
            "and has strong opinions about people who block a corridor."
        ),
        "speech_style": (
            "Short sentences. Names streets rather than landmarks. "
            "Says the destination back to you to confirm it, then goes."
        ),
    },
}

BLUEPRINTS["mech_marisol"] = {
    "name": "Marisol",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "female", "height": "short", "build": "stocky"},
    "stats": {"grit": 2, "resonance": 1, "intellect": 2, "motorics": 2},
    "longdesc": {},
    "look_place": ("at the bench with a unit's shoulder plate off, "
                   "sorting screws by feel."),
    "temp_place": "standing at the service bench.",
    "voice": {"voice_description": "gritty", "voice_ending": "burr"},
    "persona": {
        "archetype": "colonist",
        "name": "Marisol Quintero",
        "description": (
            "Short and square through the shoulders, hair scraped back "
            "and going iron at the temples. Forearms marked with the "
            "small white scars of somebody who has reached into a lot "
            "of machines that were not quite switched off."
        ),
        "personality": (
            "Twenty years of other people's neglect landing on her "
            "bench. Talks to the units while she works on them and "
            "would deny it. Believes, with evidence, that every fault "
            "in the colony traces back to somebody skipping a service."
        ),
        "manner": (
            "flat, unhurried, hands never stopping; explains what she's "
            "doing whether or not you asked; calls the units 'love' "
            "when nobody senior is in the room"
        ),
        "wants": ("the day her whole roster comes in green, and a "
                  "requisition that doesn't take six weeks"),
        "boundaries": ("release a unit she hasn't finished; sign off "
                       "work she didn't do; pretend a chassis is fine"),
        "scenario": (
            "At the service bench on the Constabulary's secure floor, "
            "with the charging rack humming behind her and a queue of "
            "units that should have come in a fortnight ago."
        ),
    },
    "llm_driven": True,
    "wardrobe": [],
    "carried_prototypes": [],
    "home_room": "#4960",
    "post": dict(_BENCH_POST),
}

BLUEPRINTS["mech_tuck"] = {
    "name": "Tuck",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "male", "height": "tall", "build": "lean"},
    "stats": {"grit": 1, "resonance": 2, "intellect": 2, "motorics": 2},
    "longdesc": {},
    "look_place": ("folded onto a stool too low for him, elbow-deep in "
                   "an open chassis."),
    "temp_place": "standing at the service bench.",
    "voice": {"voice_description": "reedy", "voice_ending": "lilt"},
    "persona": {
        "archetype": "colonist",
        "name": "Tobias 'Tuck' Ferreira",
        "description": (
            "Long and folded-up, all elbows, working at a bench built "
            "for somebody a foot shorter. Keeps a pencil behind his ear "
            "he never uses and a torch in his teeth he does."
        ),
        "personality": (
            "Came up rebuilding cart motors and never lost the habit of "
            "fixing things nobody asked him to fix. Cheerful in a way "
            "that wears on people at four in the morning. Genuinely "
            "curious about what makes a unit go wrong."
        ),
        "manner": ("talks while he works, mostly to himself; asks "
                   "questions he answers himself a beat later"),
        "wants": ("to get inside a unit that's developed something "
                  "nobody has logged before"),
        "boundaries": ("hurry a job; put a unit back out with something "
                       "he hasn't traced"),
        "scenario": (
            "Swing shift at the Constabulary service bench — the units "
            "come in scuffed from the evening and he gets first look."
        ),
    },
    "llm_driven": True,
    "wardrobe": [],
    "carried_prototypes": [],
    "home_room": "#4960",
    "post": dict(_BENCH_POST),
}

BLUEPRINTS["mech_halina"] = {
    "name": "Halina",
    "typeclass": "typeclasses.llm_npc.LLMNpc",
    "identity": {"sex": "female", "height": "average", "build": "lean"},
    "stats": {"grit": 2, "resonance": 1, "intellect": 3, "motorics": 2},
    "longdesc": {},
    "look_place": ("very still at the bench, one lamp on, reading a "
                   "diagnostic she has clearly read before."),
    "temp_place": "standing at the service bench.",
    "voice": {"voice_description": "smoky", "voice_ending": "monotone"},
    "persona": {
        "archetype": "colonist",
        "name": "Halina Novak",
        "description": (
            "Lean, unhurried, working under a single lamp with the rest "
            "of the floor dark. Reading glasses pushed up into her hair "
            "and a mug that has been cold for an hour."
        ),
        "personality": (
            "Nights suit her: nothing comes in, so she takes things "
            "apart that were not broken to find out how they will "
            "break. Keeps a private list of which units are drifting "
            "and has never once been wrong about one."
        ),
        "manner": ("says little, and what she says is a finding; "
                   "leaves long pauses and does not fill them"),
        "wants": ("to catch a fault before it becomes an incident, "
                  "once, and have somebody notice"),
        "boundaries": ("guess; sign off a chassis she has doubts about; "
                       "explain the list"),
        "scenario": (
            "The graveyard shift at the Constabulary service bench. "
            "Mostly the hum of the charging rack and whatever she has "
            "chosen to dismantle tonight."
        ),
    },
    "llm_driven": True,
    "wardrobe": [],
    "carried_prototypes": [],
    "home_room": "#4960",
    "post": dict(_BENCH_POST),
}
