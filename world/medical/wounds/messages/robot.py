"""
Robot wound descriptions — the species pack (SPECIES_AUTHORING §wounds).

A robot doesn't bleed, bruise, or scar: it tears, dents, shears, sparks, and
weeps amber hydraulic fluid (the species ``blood_color``: amber ``|y``, dried
tar-black). "Treated" is field repair — welds, epoxy, clamped lines; "healing"
is sealant curing and welds dulling; "scarred" is the permanent record of old
repairs — mismatched plate, buffed-out gouges, weld seams.

This pack is COMPLETE across every stage so a robot never falls through to
human flesh prose. Vocabulary matches ``world/anatomy/organ_descriptions.py``
(amber hydraulic fluid, coolant, servos) so organ and surface damage read as
one machine.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|ya {severity} gouge torn through the plating of the {location}, weeping amber hydraulic fluid|n",
        "|ya {severity} shear across the {location}, the metal peeled back in bright curls|n",
        "|ya {severity} rupture in the {location} housing, servos stuttering beneath|n",
        "|ya {severity} breach in the {location}, hydraulic lines glistening amber in the gap|n",
        "|ya {severity} dent crumpling the {location}, its panel seams sprung|n",
        "|ya {severity} tear in the {location} chassis, loose contacts sparking intermittently|n",
        "|ya {severity} scorch across the {location}, the plating blued and buckled|n",
    ],

    "treated": [
        "a {severity} breach in the {location}, clamped and sealed with a fresh weld bead",
        "a {severity} gouge in the {location} packed with epoxy, the patch still tacky",
        "a {severity} rupture in the {location} strapped under a bolted service plate",
        "a {severity} tear in the {location}, its severed lines crimped off and taped",
        "a {severity} dent in the {location} hammered roughly true, the seam resealed",
    ],

    "healing": [
        "a {severity} weld line along the {location}, its bead still bright from the torch",
        "a {severity} patch on the {location}, sealant cured to a dull amber rind",
        "a {severity} repair in the {location}, new plate sitting proud of the old",
        "a {severity} resealed seam in the {location}, dried fluid staining it tar-black",
    ],

    "scarred": [
        "an old weld seam across the {location}, ground smooth but never flush",
        "a mismatched replacement plate on the {location}, its finish a shade off",
        "a buffed-out gouge in the {location}, visible only where the light catches",
        "a lattice of old repair marks on the {location}, story of a working chassis",
    ],

    "destroyed": [
        "the {location} is a crushed ruin of plate and servo, tar-black fluid long since bled out",
        "the {location} has been mangled into scrap, actuators shorn and lines burst",
        "the {location} is burnt out entirely, its housing slagged and dead",
    ],
}

# Sensory surfaces get bespoke destruction prose — optics and acoustic
# arrays, not eyes and ears (mirrors the human modules' overlay shape).
DESTROYED_BY_LOCATION = {
    "left_eye": [
        "{Their} left optic is a shattered socket, lens glass glittering in the housing",
        "{Their} left optic assembly is caved in, its aperture dark and dead",
    ],
    "right_eye": [
        "{Their} right optic is a shattered socket, lens glass glittering in the housing",
        "{Their} right optic assembly is caved in, its aperture dark and dead",
    ],
    "left_ear": [
        "{Their} left acoustic array is sheared away, wiring fanned from the mount",
    ],
    "right_ear": [
        "{Their} right acoustic array is sheared away, wiring fanned from the mount",
    ],
}

COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|ya {severity} gouge in the {location}, one of several fresh rents weeping amber|n",
        "|ythe {location} torn open in more than one place, hydraulic fluid tracking down the plate|n",
    ],
    "treated": [
        "a cluster of patched breaches on the {location}, welds and epoxy shoulder to shoulder",
    ],
    "healing": [
        "a run of curing repairs along the {location}, sealant rinds in every seam",
    ],
    "scarred": [
        "a constellation of old damage on the {location} — dents, weld seams, mismatched plate",
    ],
}

#: Per-injury vocabulary (#3512): preferred over WOUND_DESCRIPTIONS /
#: COMPOUND_DESCRIPTIONS by injury type; those tables remain the fallback.
BY_INJURY = {'blunt': {'fresh': ['|ya {severity} dent set into the plating of the {location}, the finish '
                     'crazed pale around its rim|n',
                     '|ya {severity} crumple in the {location}, the panel folded down onto the '
                     'housing beneath|n',
                     '|ya {severity} impact hollow in the {location}, its dented fold pushing '
                     'amber hydraulic fluid out along the seam|n',
                     '|ya {severity} dished panel on the {location}, the light pooling where it '
                     'was driven in|n',
                     '|ya {severity} inward crease along the {location}, its fold following the '
                     'line of the panel|n',
                     '|ya {severity} buckle across the {location}, rivets popped and the seam '
                     'standing open|n',
                     '|ya {severity} dent pushed into the {location}, its panel standing out of '
                     'line with its neighbours|n'],
           'treated': ['a {severity} dent in the {location} hammered roughly true, the sprung seam '
                       'bolted shut|n',
                       'a {severity} dented housing on the {location} braced under a bolted '
                       'service plate|n',
                       'a {severity} crumpled panel on the {location} drawn straight on a slide '
                       'hammer and tacked at the fold|n',
                       'a {severity} buckled seam in the {location} pushed back down and pinched '
                       'flat between screwed batten strips|n',
                       'a {severity} crease in the {location}, its sprung rivets replaced and the '
                       'seam faired flush|n'],
           'healing': ['a {severity} hammered dent in the {location}, its resealed seam curing '
                       'stiff and losing its shine|n',
                       'a {severity} crumple in the {location} pulled straight, the panel '
                       're-seating as the sealant sets|n',
                       'a {severity} creased housing on the {location} braced from within, the '
                       "brace's weld losing its colour along the fold|n",
                       "a {severity} drawn-out dent in the {location}, the puller's clamp marks "
                       'still bright on the plate around it|n'],
           'scarred': ['an old dent in the {location}, beaten flat and buffed until only the light '
                       'finds it|n',
                       'a ripple of hammer marks across the {location} where a dent was worked '
                       'back out|n',
                       'a permanent dish in the {location} where the plating took a blow and '
                       'stayed pushed in|n',
                       'a flattened crease along the {location} that has never sat true since the '
                       'plate was driven in|n']},
 'bullet': {'fresh': ['|ya {severity} hole punched into the plating of the {location}, bright burr '
                      'standing up around its rim|n',
                      '|ya {severity} entry in the {location}, the metal curled inward around a '
                      'ragged rim|n',
                      '|ya {severity} round hole in the {location} jetting amber hydraulic fluid '
                      'in thin pulses|n',
                      '|ya {severity} ballistic puncture in the {location}, amber already '
                      'trickling down the plate|n',
                      '|ya {severity} perforation in the {location}, its rim curled inward all the '
                      'way round|n',
                      '|ya {severity} exit hole in the {location}, its rim petalled outward where '
                      'the round went on through|n',
                      '|ya {severity} bullet hole in the {location}, powder-blacked at the rim and '
                      'weeping amber|n'],
            'treated': ['a {severity} punched hole in the {location} plugged and run over with a '
                        'weld bead|n',
                        'a {severity} perforation in the {location} capped with a bolted patch '
                        'plate|n',
                        'a {severity} entry hole in the {location} rammed full of epoxy putty, the '
                        'excess thumbed flat over its rim|n',
                        'a {severity} shot hole in the {location}, its curled rim beaten flat and '
                        'strapped over with {medical_tape_color}field tape|n pending a plug weld|n',
                        'a {severity} ballistic puncture in the {location} wiped clear of swarf '
                        'and sealed under a riveted cap|n'],
            'healing': ['a {severity} plugged hole in the {location}, its weld bead dulled off to '
                        'a flat grey|n',
                        'a {severity} patched perforation on the {location}, its sealant gone hard '
                        'and dull in the dish of the rim|n',
                        'a {severity} capped entry in the {location}, dried fluid gone tar-black '
                        'around the plate|n',
                        'a {severity} sealed bullet hole in the {location}, its plug ground down '
                        'flush with the plate|n'],
            'scarred': ['a plug weld filling a hole in the {location}, ground flat but a shade '
                        'brighter than the plate around it|n',
                        'an old bullet hole in the {location}, filled with braze and still dished '
                        'a little at its centre|n',
                        'a ring of pitting on the {location}, the rim of a hole long since '
                        'filled|n',
                        'an old filled hole in the {location}, its plug set off-round in the plate '
                        'and never refinished|n']},
 'stab': {'fresh': ['|ya {severity} narrow slot driven into the {location}, dark and '
                    'straight-sided where the point went in|n',
                    '|ya {severity} puncture in the {location} housing, amber welling slow from '
                    'the slit|n',
                    '|ya {severity} pierced panel on the {location}, the opening no wider than the '
                    'blade that made it|n',
                    '|ya {severity} thrust hole in the {location}, amber pulsing out of it in time '
                    'with the pumps|n',
                    '|ya {severity} stab hole in the {location}, the plate dimpled inward around a '
                    'clean slot|n',
                    '|ya {severity} spike hole in the {location}, amber tracking down the seam '
                    'beneath it|n',
                    '|ya {severity} slit punched through the {location}, dark down its length and '
                    'rimmed with bright burr|n'],
          'treated': ['a {severity} slotted puncture in the {location} closed with a single bead '
                      'of weld|n',
                      'a {severity} pierced housing on the {location} sealed with epoxy and '
                      'clamped shut|n',
                      'a {severity} thrust hole in the {location}, its rim crimped down and '
                      'clamped|n',
                      'a {severity} stab puncture in the {location} bound off under a '
                      '{medical_tape_color}wrap of pipe tape|n and pressure-checked|n',
                      'a {severity} narrow breach in the {location} swabbed out and plugged with a '
                      'driven pin|n'],
          'healing': ['a {severity} welded slot in the {location}, its narrow bead losing the last '
                      "of the torch's colour|n",
                      'a {severity} sealed stab hole in the {location}, epoxy curing amber down '
                      'the blade-width gap|n',
                      "a {severity} plugged puncture in the {location}, the driven pin's head "
                      'weathering to match the plate|n',
                      'a {severity} closed slit in the {location}, fresh sealant setting proud of '
                      'the plate|n'],
          'scarred': ['a narrow filled slot in the {location}, closed with weld and dressed down '
                      'to a short bright line|n',
                      'an old puncture in the {location}, filled and ground but still catching a '
                      'fingernail|n',
                      'a braze-filled slot in the {location}, its fill standing out pale against '
                      'the plate it was run into|n',
                      'a blade-width slot in the {location}, pinned shut long ago and still '
                      'legible as a slot|n']},
 'cut': {'fresh': ['|ya {severity} blade line scored across the {location}, the finish curling '
                   'away on either side of it|n',
                   '|ya {severity} cut across the {location}, its edges square and bright where '
                   'the plate parted|n',
                   '|ya {severity} slice through the {location} panel, amber beading along the '
                   'whole length of it|n',
                   '|ya {severity} scored seam in the {location}, the metal laid open in one '
                   'straight pass|n',
                   '|ya {severity} clean incision across the {location}, no burr on either lip of '
                   'it|n',
                   '|ya {severity} blade cut in the {location}, amber running out of it in a '
                   'single thin line|n',
                   '|ya {severity} draw-cut across the {location}, the plating parted clean and '
                   'contacts winking in the gap|n'],
         'treated': ['a {severity} cut on the {location} drawn shut and run with a fine weld '
                     'bead|n',
                     'a {severity} scored seam in the {location} clamped closed and sealed with '
                     'epoxy|n',
                     'a {severity} sliced panel on the {location} pulled together with '
                     '{medical_staple_color}rivet clamps|n along the line|n',
                     'a {severity} incision in the {location} faired over with filler and rubbed '
                     'flat|n',
                     'a {severity} blade line on the {location} taped off with '
                     '{medical_tape_color}sealing tape|n until it can be welded|n'],
         'healing': ['a {severity} welded cut on the {location}, its bead dulling to grey along a '
                     'dead-straight line|n',
                     'a {severity} closed slice in the {location}, filler curing hard and level '
                     'with the plate|n',
                     'a {severity} sealed blade line across the {location}, amber crust drying '
                     'tar-black at either end|n',
                     'a {severity} riveted cut on the {location}, the parted edges drawn back '
                     'true|n'],
         'scarred': ['a hairline weld running dead straight across the {location}, the mark of one '
                     'clean stroke|n',
                     'an old blade line in the {location}, filled and buffed but still ruling the '
                     'panel corner to corner|n',
                     'a bright scored line across the {location}, closed long ago and never quite '
                     'hidden|n',
                     'a straight braze track on the {location}, its ends tapering the way the '
                     'blade left off|n']},
 'laceration': {'fresh': ['|ya {severity} shear raked across the {location}, plating peeled up in '
                          'bright curls|n',
                          '|ya {severity} ragged tear in the {location}, exposed contacts arcing '
                          'where the plate parted|n',
                          '|ya {severity} gouge chewed through the {location}, amber running out '
                          'along the furrow|n',
                          '|ya {severity} rip opened across the {location}, loom cabling laid bare '
                          'and fraying|n',
                          '|ya {severity} sawn rent in the {location}, swarf caked in amber all '
                          'along the tear|n',
                          '|ya {severity} torn strip of plating lifted off the {location}, its '
                          'edge curled back on itself|n',
                          '|ya {severity} furrow raked across the {location}, its edges burred and '
                          'turned outward|n'],
                'treated': ['a {severity} sheared panel on the {location} folded back down and '
                            'tacked with weld|n',
                            'a {severity} torn section of the {location} pressed back over its '
                            'loom and laced shut with {medical_staple_color}tie wire|n through '
                            'drilled tabs|n',
                            'a {severity} ripped seam in the {location} hauled together with a '
                            'banding strap, its lifted lips pinched flat beneath|n',
                            'a {severity} chewed furrow in the {location} packed with epoxy and '
                            'faired over|n',
                            'a {severity} peeled curl of plating on the {location}, rolled flat '
                            'over its loom, the bared cabling taped off in '
                            '{medical_tape_color}insulating wrap|n'],
                'healing': ['a {severity} tacked shear on the {location}, its weld beads dulling '
                            'along the curl line|n',
                            'a {severity} faired furrow in the {location}, epoxy cured to a hard '
                            'amber ridge|n',
                            'a {severity} clamped tear on the {location}, the plate drawing back '
                            'flat as it seats|n',
                            'a {severity} laid-down shear in the {location}, the curled plate '
                            'pressed back over its retaped loom|n'],
                'scarred': ['a raked seam across the {location} where lifted plate was pressed '
                            'back over its loom, the cover strip still a shade off|n',
                            'a buffed-out gouge in the {location}, showing only where the light '
                            'rakes across it|n',
                            'an old tear line across the {location}, its peeled curls beaten back '
                            'down and dressed flush|n',
                            'a row of old rivet heads on the {location}, standing proud where a '
                            'peeled tear was pulled shut|n']},
 'burn': {'fresh': ['|ya {severity} burn seared into the {location}, the plating blued and rippled '
                    'where it buckled|n',
                    '|ya {severity} charred patch on the {location}, insulation melted back off '
                    'bare contacts|n',
                    '|ya {severity} run of melted plating on the {location}, its edge gone soft '
                    'and set again|n',
                    '|ya {severity} scorch mark on the {location}, its soot feathering out along '
                    'the panel seams|n',
                    '|ya {severity} heat pit in the {location}, its finish blistered off to bare '
                    'alloy|n',
                    '|ya {severity} heat bloom on the {location}, the plating gone straw at its '
                    'rim and blue at its heart|n',
                    '|ya {severity} thermal split in the {location}, the seam parted where the '
                    'plate warped|n'],
          'treated': ['a {severity} burn on the {location} scraped back to clean alloy and '
                      'sealed|n',
                      'a {severity} charred patch on the {location}, its blistered finish cut away '
                      'and a stock panel bolted down over the bare alloy|n',
                      'a {severity} blistered panel on the {location}, its bared alloy lagged over '
                      'in {medical_tape_color}heat tape|n',
                      'a {severity} scorched seam in the {location} wire-brushed back to bare '
                      'metal and re-sealed|n',
                      'a {severity} melted edge on the {location} ground back and capped with '
                      'epoxy|n',
                      'a {severity} heat-buckled plate on the {location} clamped flat while the '
                      'sealant takes|n'],
          'healing': ['a {severity} sealed burn on the {location}, its epoxy curing to a matte '
                      'amber crust|n',
                      'a {severity} scorched patch on the {location}, the panel bolted over it '
                      'settling flush as its fasteners dull|n',
                      'a {severity} cooled melt-run on the {location}, its rippled surface '
                      'hardened matte grey|n',
                      'a {severity} dressed scorch on the {location}, the blued metal greying back '
                      'toward the plate around it|n'],
          'scarred': ['a permanent blueing across the {location} where the heat went in and '
                      'stayed|n',
                      'an old burn shadow on the {location}, its finish never brought back to the '
                      'same colour|n',
                      'a rippled stretch of the {location} where the plating cooled out of true, '
                      'its colour run from straw to grey|n',
                      'a heat-discoloured halo on the {location}, ringing a pit that was filled '
                      'and never took paint again|n']}}


#: Per-injury vocabulary (#3512): preferred over WOUND_DESCRIPTIONS /
#: COMPOUND_DESCRIPTIONS by injury type; those tables remain the fallback.
COMPOUND_BY_INJURY = {'blunt': {'fresh': ['|ya {severity} dent and {others_phrase} beaten into the plating of the '
                     '{location}|n',
                     '|ya {severity} crumple and {others_phrase} driven into the panels of the '
                     '{location}|n'],
           'treated': ['a {severity} hammered dent and {others_phrase} on the {location}, every '
                       'sprung seam closed under weld|n',
                       'a {severity} dished panel and {others_phrase} on the {location}, each '
                       'jacked back out and clamped while its epoxy sets|n'],
           'healing': ['a {severity} trued dent and {others_phrase} on the {location}, the hammer '
                       'marks still bright around each|n',
                       'a {severity} pulled-out crumple and {others_phrase} on the {location}, '
                       'each drawn near true as its sealant hardens|n'],
           'scarred': ['an old dent and {others_phrase} across the {location}, the plating beaten '
                       'flat but never quite true|n',
                       'an old dish in the {location} with {others_phrase} around it, blows the '
                       'plating never gave back|n']},
 'bullet': {'fresh': ['|ya {severity} hole and {others_phrase} punched through the plating of the '
                      '{location}, amber jetting from the worst of them|n',
                      '|ya {severity} bullet hole and {others_phrase} in the {location}, every rim '
                      'blacked with powder|n'],
            'treated': ['a {severity} plugged hole and {others_phrase} on the {location}, each '
                        'weld bead set proud of the plate|n',
                        'a {severity} capped entry and {others_phrase} on the {location}, each '
                        'packed with epoxy|n'],
            'healing': ['a {severity} sealed bullet hole and {others_phrase} on the {location}, '
                        'every plug cured hard and dry|n',
                        'a {severity} patched perforation and {others_phrase} on the {location}, '
                        'their rinds gone tar-black|n'],
            'scarred': ['an old filled hole and {others_phrase} on the {location}, falling in no '
                        'order at all and each ground flat|n',
                        'a pitted ring on the {location} with {others_phrase} around it, every one '
                        'the rim of a hole punched straight through|n']},
 'stab': {'fresh': ['|ya {severity} slot and {others_phrase} driven through the {location}, amber '
                    'welling from each in turn|n',
                    '|ya {severity} thrust hole and {others_phrase} in the {location}, the plate '
                    'dimpled inward at every one|n'],
          'treated': ['a {severity} welded slot and {others_phrase} in the {location}, each bead '
                      'no longer than the slot it fills|n',
                      'a {severity} plugged puncture and {others_phrase} on the {location}, each '
                      'pinned and clamped shut|n'],
          'healing': ['a {severity} sealed slot and {others_phrase} along the {location}, epoxy '
                      'curing amber in each narrow gap|n',
                      'a {severity} closed slit and {others_phrase} in the {location}, each narrow '
                      'fill hardening in place|n'],
          'scarred': ['an old blade-width slot and {others_phrase} along the {location}, pinned '
                      'shut and still legible as slots|n',
                      'a braze-plugged slot in the {location} with {others_phrase} beside it, each '
                      'one a narrow puncture filled and dressed down|n']},
 'cut': {'fresh': ['|ya {severity} blade line and {others_phrase} laid across the {location}, each '
                   'one ruled straight through the finish|n',
                   '|ya {severity} clean cut and {others_phrase} on the {location}, amber beading '
                   'the length of every one|n'],
         'treated': ['a {severity} welded cut and {others_phrase} on the {location}, their beads '
                     'running dead straight|n',
                     'a {severity} clamped slice and {others_phrase} on the {location}, each drawn '
                     'shut and filled|n'],
         'healing': ['a {severity} closed blade line and {others_phrase} on the {location}, filler '
                     'curing level with the plate|n',
                     'a {severity} riveted cut and {others_phrase} on the {location}, their parted '
                     'edges drawn back true|n'],
         'scarred': ['a hairline weld ruling the {location} with {others_phrase} crossing it, each '
                     'the mark of one clean stroke|n',
                     'an old blade line and {others_phrase} across the {location}, straight as '
                     'rules and buffed near flat|n']},
 'laceration': {'fresh': ['|ya {severity} shear and {others_phrase} raked across the {location}, '
                          'plating peeled up in curls at every pass|n',
                          '|ya {severity} ragged tear and {others_phrase} in the {location}, loom '
                          'laid bare and contacts arcing|n'],
                'treated': ['a {severity} tacked shear and {others_phrase} on the {location}, weld '
                            'and epoxy shoulder to shoulder|n',
                            'a {severity} clamped tear and {others_phrase} on the {location}, '
                            'every curl of plate rolled back flat|n'],
                'healing': ['a {severity} laid-down shear and {others_phrase} across the '
                            '{location}, each plate seating back in step|n',
                            'a {severity} faired furrow and {others_phrase} on the {location}, '
                            'epoxy cured to hard amber ridges|n'],
                'scarred': ['an old weld seam raking the {location} with {others_phrase} beside '
                            'it, where torn plate was pulled back down|n',
                            'an old flattened tear and {others_phrase} on the {location}, curl on '
                            'curl where the plating was peeled up and beaten back|n']},
 'burn': {'fresh': ['|ya {severity} scorch and {others_phrase} burned across the panels of the '
                    '{location}, insulation smoking off all of them|n',
                    '|ya {severity} charred patch and {others_phrase} on the {location}, the '
                    'plating blued between them|n'],
          'treated': ['a {severity} dressed burn and {others_phrase} on the {location}, cut back '
                      'to bare alloy and capped panel by panel|n',
                      'a {severity} scorch and {others_phrase} on the {location}, each one bolted '
                      'over with stock panel against the blued plate|n'],
          'healing': ['a {severity} sealed scorch and {others_phrase} on the {location}, the '
                      'blueing greying out together|n',
                      'a {severity} cooled melt-run and {others_phrase} on the {location}, each '
                      'hardened matte and dull|n'],
          'scarred': ['an old burn shadow and {others_phrase} across the {location}, the finish '
                      'never brought back to one colour|n',
                      'a heat-rippled stretch of the {location} with {others_phrase} beyond it, '
                      'plating frozen where it ran|n']}}
