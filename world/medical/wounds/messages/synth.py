"""
Synthetic-humanoid wound descriptions — the species pack (SPECIES_AUTHORING
§wounds).

A synth wounds like flesh but never quite like OUR flesh: the dermis is too
uniform, the blood runs **cobalt** (the species ``blood_color``: ``|B``,
dried slate), and repair is eerily tidy — wounds knit clean, scars set as
faint pearlescent seams rather than raised tissue. Human mechanics, alien
presentation (the species' whole design).

This pack is COMPLETE across every stage so a synth never falls through to
crimson human prose. ``{skintone}`` still applies — synths carry the alien
skin palette.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ba {severity} cut across the {location}, welling slow cobalt|n",
        "|Ba {severity} gash in the {location}, its edges unnaturally clean, blue-dark inside|n",
        "|Ba {severity} wound on the {location}, cobalt beading along the parted dermis|n",
        "|Ba {severity} tear through the {location}, the layered dermis peeled too evenly|n",
        "|Ba {severity} puncture in the {location}, a thin cobalt line tracking from it|n",
        "|Ba {severity} rent in the {location}, slate-dark where the blue has begun to set|n",
    ],

    "treated": [
        "{skintone}a {severity} sutured wound on the {location}, {suture_color}stitches|n{skintone} laid in machine-even rows|n",
        "{skintone}a {severity} dressed wound on the {location}, slate staining the bandage's edge|n",
        "{skintone}a {severity} sealed cut on the {location}, its margins already fusing smooth|n",
        "{skintone}a {severity} bound wound in the {location}, cobalt dried to slate beneath the wrap|n",
    ],

    "healing": [
        "{skintone}a {severity} knitting wound on the {location}, closing cleaner than flesh should|n",
        "{skintone}a {severity} mending cut across the {location}, its seam paling to pearl|n",
        "{skintone}a {severity} half-healed wound on the {location}, slate flaking from the new dermis|n",
    ],

    "scarred": [
        "{skintone}a faint pearlescent seam across the {location}, too regular to be a natural scar|n",
        "{skintone}an old wound line on the {location}, set smooth and slightly opaline|n",
        "{skintone}a hairline scar on the {location}, catching the light like lacquer|n",
    ],

    "destroyed": [
        "the {location} has been ruined utterly, layered dermis and blue-dark substrate mangled together",
        "the {location} is destroyed, cobalt long since drained to a slate crust",
        "the {location} is a wreck of parted dermis and exposed substrate, past any knitting",
    ],
}

DESTROYED_BY_LOCATION = {
    "left_eye": [
        "{Their} left eye is a ruined socket, its iris-ring dulled to dead glass",
    ],
    "right_eye": [
        "{Their} right eye is a ruined socket, its iris-ring dulled to dead glass",
    ],
}

COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ba {severity} wound on the {location}, the worst of several seeping cobalt|n",
    ],
    "treated": [
        "{skintone}a cluster of dressed wounds on the {location}, slate shadowing each edge|n",
    ],
    "healing": [
        "{skintone}a spread of knitting wounds across the {location}, each seam paling in step|n",
    ],
    "scarred": [
        "{skintone}a scatter of pearlescent seams across the {location}, an even, unnatural record|n",
    ],
}

#: Per-injury vocabulary (#3512): preferred over WOUND_DESCRIPTIONS /
#: COMPOUND_DESCRIPTIONS by injury type; those tables remain the fallback.
BY_INJURY = {'blunt': {'fresh': ['|Ba {severity} impact mark on the {location}, cobalt pooling beneath the '
                     'unbroken dermis|n',
                     '|Ba {severity} dent in the {location}, the dermis standing low and refusing '
                     'to spring true|n',
                     '|Ba {severity} bloom across the {location}, cobalt spreading beneath a '
                     'dermis that will not colour|n',
                     '|Ba {severity} crush mark across the {location}, the layered dermis rippled '
                     'but unparted|n',
                     '|Ba {severity} contusion in the {location}, subdermal cobalt settling in an '
                     'even ring|n',
                     '|Ba {severity} pressure mark on the {location}, blue-dark pooling too neatly '
                     'below the surface|n',
                     '|Ba {severity} hollow struck into the {location}, the dermis slack over a '
                     'cobalt shadow|n'],
           'treated': ['{skintone}a {severity} compressed contusion on the {location}, wrapped in '
                       '{bandage_color}field dressing|n',
                       '{skintone}a {severity} bound impact mark on the {location}, the subdermal '
                       'cobalt pressed flat|n',
                       '{skintone}a {severity} taped dent on the {location}, '
                       '{medical_tape_color}tape|n{skintone} holding the dermis true|n',
                       '{skintone}a {severity} treated crush mark on the {location}, the trapped '
                       'cobalt paling where the wrap bears down|n',
                       '{skintone}a {severity} cold-packed contusion in the {location}, the bloom '
                       'under {ice_pack_color}the compress|n{skintone} drawn back to a tighter '
                       'ring|n'],
           'healing': ['{skintone}a {severity} fading bloom on the {location}, the cobalt thinning '
                       'back toward the dermis tone|n',
                       '{skintone}a {severity} settling dent in the {location}, the surface '
                       'drawing level again|n',
                       '{skintone}a {severity} mending contusion on the {location}, the bloom '
                       'shrinking in even bands|n',
                       '{skintone}a {severity} clearing impact mark across the {location}, pooled '
                       'blue gone pale and orderly|n'],
           'scarred': ['{skintone}a {severity} old dent-print on the {location}, the dermis set a '
                       'hair low and gone pearlescent|n',
                       '{skintone}a {severity} old impact shadow in the {location}, set faintly '
                       'opaline beneath the dermis|n',
                       '{skintone}a {severity} healed crush mark on the {location}, a permanent '
                       'dip smoother than the dermis around it|n']},
 'bullet': {'fresh': ['|Ba {severity} bullet hole punched into the {location}, blue-dark substrate '
                      'showing in the channel|n',
                      '|Ba {severity} entry wound in the {location}, a cobalt track running from '
                      'its lip|n',
                      '|Ba {severity} gunshot wound in the {location}, the layered dermis cratered '
                      'in neat rings|n',
                      '|Ba {severity} ballistic puncture in the {location}, welling cobalt with '
                      'every pulse|n',
                      '|Ba {severity} exit wound on the {location}, its margins peeled back too '
                      'evenly for a tear|n',
                      '|Ba {severity} bullet wound in the {location}, scorch-black at the rim and '
                      'blue-dark in the mouth|n',
                      '|Ba {severity} projectile wound in the {location}, the channel dark and '
                      'going slate at its edge|n'],
            'treated': ['{skintone}a {severity} packed bullet wound on the {location}, '
                        '{bandage_color}gauze|n{skintone} plugging the channel|n',
                        '{skintone}a {severity} dressed gunshot wound in the {location}, cobalt '
                        'blotting through the {bandage_color}field dressing|n{skintone} and drying '
                        'slate at its edge|n',
                        '{skintone}a {severity} sealed entry wound on the {location}, '
                        '{suture_color}sutures|n{skintone} drawn in a tight purse around the '
                        'hole|n',
                        '{skintone}a {severity} taped ballistic puncture in the {location}, '
                        '{medical_tape_color}surgical tape|n{skintone} squared across it|n',
                        '{skintone}a {severity} swabbed exit wound on the {location}, antiseptic '
                        'pooled in the crater|n'],
            'healing': ['{skintone}a {severity} closing bullet channel in the {location}, drawing '
                        'shut cleaner than it should|n',
                        '{skintone}a {severity} mending gunshot wound on the {location}, its rim '
                        'paling toward pearl|n',
                        '{skintone}a {severity} knitting entry wound in the {location}, new dermis '
                        'laying down in rings|n',
                        '{skintone}a {severity} half-filled puncture on the {location}, slate '
                        'flaking from the shrinking mouth|n'],
            'scarred': ['{skintone}a {severity} pearlescent pock on the {location}, a filled '
                        'circle where the round went in|n',
                        '{skintone}a {severity} old exit pock on the {location}, opaline and '
                        'faintly starred at its edges|n',
                        '{skintone}a {severity} healed bullet mark in the {location}, the plugged '
                        'hole smooth as poured lacquer|n']},
 'stab': {'fresh': ['|Ba {severity} stab wound in the {location}, a narrow part in the dermis '
                    'welling dark cobalt|n',
                    '|Ba {severity} puncture driven into the {location}, its lips drawn together '
                    'and blue-dark between|n',
                    '|Ba {severity} thrust wound in the {location}, the layers parted in one clean '
                    'slot|n',
                    '|Ba {severity} piercing injury to the {location}, cobalt brimming at the '
                    'mouth of the slot|n',
                    '|Ba {severity} stab slot in the {location}, the dermis clamped tight along '
                    'its length and beading cobalt|n',
                    '|Ba {severity} stab hole in the {location}, its mouth tight and the cobalt '
                    'already setting slate at the lip|n',
                    '|Ba {severity} penetrating wound on the {location}, pushing cobalt out in '
                    'slow beats|n'],
          'treated': ['{skintone}a {severity} packed stab wound in the {location}, '
                      '{bandage_color}gauze|n{skintone} rolled thin and fed into the slot|n',
                      '{skintone}a {severity} sutured puncture on the {location}, '
                      '{suture_color}stitches|n{skintone} spaced to the millimetre down its '
                      'length|n',
                      '{skintone}a {severity} dressed thrust wound in the {location}, pressure '
                      'holding its narrow lips shut|n',
                      '{skintone}a {severity} cleaned piercing wound on the {location}, antiseptic '
                      'ringing the mouth of it|n',
                      '{skintone}a {severity} taped puncture in the {location}, '
                      '{medical_tape_color}strips|n{skintone} drawing the dermis closed|n'],
          'healing': ['{skintone}a {severity} closing stab wound in the {location}, the slot '
                      'sealing down to a hairline|n',
                      '{skintone}a {severity} mending puncture on the {location}, its slot filling '
                      'in and paling|n',
                      '{skintone}a {severity} knitting thrust wound in the {location}, the parted '
                      'layers finding each other exactly|n',
                      '{skintone}a {severity} shrinking piercing wound on the {location}, slate '
                      'lifting away in clean scales|n'],
          'scarred': ['{skintone}a {severity} pearl puncture seam on the {location}, no wider than '
                      'a needle track|n',
                      '{skintone}a {severity} old stab mark in the {location}, a short opaline '
                      'slot set flush|n',
                      '{skintone}a {severity} healed thrust pock on the {location}, a filled slot '
                      'straight enough to look machined|n']},
 'cut': {'fresh': ['|Ba {severity} cut across the {location}, cobalt beading along one clean '
                   'edge|n',
                   '|Ba {severity} blade line on the {location}, the dermis parted in a single '
                   'unbroken stroke|n',
                   '|Ba {severity} slash on the {location}, its lips tidy and blue-dark between '
                   'them|n',
                   '|Ba {severity} slice through the {location}, its cut faces square and welling '
                   'cobalt|n',
                   '|Ba {severity} knife wound across the {location}, laid open without a ragged '
                   'thread to it|n',
                   '|Ba {severity} incised wound on the {location}, cobalt running the whole '
                   'length of the line|n',
                   '|Ba {severity} razor line down the {location}, beading blue-dark and going '
                   'slate at the ends|n'],
         'treated': ['{skintone}a {severity} sutured cut on the {location}, '
                     '{suture_color}stitches|n{skintone} laid straight down the line of it|n',
                     '{skintone}a {severity} taped slice on the {location}, '
                     '{medical_tape_color}closure strips|n{skintone} drawing the squared edges '
                     'back together|n',
                     '{skintone}a {severity} dressed blade line on the {location}, '
                     '{bandage_color}gauze|n{skintone} folded into a narrow strip along it|n',
                     '{skintone}a {severity} sealed slash in the {location}, adhesive bridging its '
                     'edges in a thin shining line|n',
                     '{skintone}a {severity} cleaned cut across the {location}, antiseptic drying '
                     'in a stripe along the parted dermis|n'],
         'healing': ['{skintone}a {severity} closing cut on the {location}, the blade line '
                     'narrowing to a pale thread|n',
                     '{skintone}a {severity} mending slice in the {location}, its squared edges '
                     'drawing back level|n',
                     '{skintone}a {severity} knitting slash across the {location}, slate lifting '
                     'off a straight new seam|n',
                     '{skintone}a {severity} healing blade wound on the {location}, the parted '
                     'layers meeting edge to edge|n'],
         'scarred': ['{skintone}a {severity} blade scar across the {location}, one pearl line '
                     'drawn ruler-straight and fine as a scored thread|n',
                     '{skintone}a {severity} old cut seam on the {location}, opaline and no wider '
                     'than the edge that made it|n',
                     '{skintone}a {severity} healed slice mark down the {location}, set flush and '
                     'faintly lacquered|n']},
 'laceration': {'fresh': ['|Ba {severity} ragged tear across the {location}, the layers beneath '
                          'separating cleanly all the same|n',
                          '|Ba {severity} jagged laceration on the {location}, cobalt sheeting '
                          'from the torn dermis|n',
                          '|Ba {severity} rent in the {location}, its strata showing in tidy bands '
                          'beneath a jagged rim|n',
                          '|Ba {severity} rip through the {location}, edges frayed above and '
                          'blue-dark beneath|n',
                          '|Ba {severity} gash on the {location}, ragged at the lip and beading '
                          'cobalt along it|n',
                          '|Ba {severity} torn opening in the {location}, dermal bands showing '
                          'blue and orderly inside the fray|n',
                          '|Ba {severity} split across the {location}, its frayed lips parting on '
                          'layers that still separate clean|n'],
                'treated': ['{skintone}a {severity} sutured laceration on the {location}, '
                            '{suture_color}stitches|n{skintone} tracking the tear in even bites|n',
                            '{skintone}a {severity} stapled tear in the {location}, '
                            '{medical_staple_color}staples|n{skintone} bridging the ragged edge|n',
                            '{skintone}a {severity} packed rip on the {location}, '
                            '{bandage_color}gauze|n{skintone} pressed down into the torn bands|n',
                            '{skintone}a {severity} bound tear across the {location}, its torn '
                            'lips pressed back into their layers|n',
                            '{skintone}a {severity} irrigated laceration in the {location}, '
                            'antiseptic beaded in every fray of the rim|n'],
                'healing': ['{skintone}a {severity} knitting tear on the {location}, the ragged '
                            'line pulling straight as it closes|n',
                            '{skintone}a {severity} mending laceration across the {location}, each '
                            'layer sealing in order|n',
                            '{skintone}a {severity} closing rip in the {location}, slate flaking '
                            'off a pale new seam|n',
                            '{skintone}a {severity} healing gash on the {location}, tidier now '
                            'than the tearing deserved|n'],
                'scarred': ['{skintone}a {severity} opaline tear-line across the {location}, its '
                            'ragged path set glass-smooth|n',
                            '{skintone}a {severity} old laceration seam on the {location}, '
                            'pearlescent and unnaturally flat where the tear ran|n',
                            '{skintone}a {severity} healed rip in the {location}, a pale branching '
                            'mark with no raised edge|n']},
 'burn': {'fresh': ['|Ba {severity} burn across the {location}, the dermis glazed and tight where '
                    'the heat sat|n',
                    '|Ba {severity} scorch on the {location}, the dermis gone glassy and '
                    'smoke-dulled|n',
                    '|Ba {severity} sear in the {location}, the dermis gone stiff and matte along '
                    'the run|n',
                    '|Ba {severity} glazed burn on the {location}, the dermis drawn tight and '
                    'shining, never blistering|n',
                    '|Ba {severity} heat mark on the {location}, its rim gone slate where the '
                    'cobalt cooked dry|n',
                    '|Ba {severity} burn mark in the {location}, the dermis crinkled fine and gone '
                    'dull|n',
                    '|Ba {severity} scorch over the {location}, its edges dried tight and weeping '
                    'nothing at all|n'],
          'treated': ['{skintone}a {severity} dressed burn on the {location}, '
                      '{bandage_color}gauze|n{skintone} laid loose over the glazed run|n',
                      '{skintone}a {severity} salved scorch across the {location}, ointment '
                      'standing in a wet shine over it|n',
                      '{skintone}a {severity} covered burn in the {location}, '
                      '{medical_tape_color}tape|n{skintone} anchored on clean dermis well clear of '
                      'the rim|n',
                      '{skintone}a {severity} treated sear on the {location}, the tight dermis '
                      'cooled and left open to the air|n',
                      '{skintone}a {severity} cleaned burn across the {location}, slate flecks '
                      'washed off a dulled patch|n'],
          'healing': ['{skintone}a {severity} healing burn on the {location}, new dermis creeping '
                      'in over the glazed ground|n',
                      '{skintone}a {severity} mending scorch across the {location}, its glaze '
                      'dulling to a pale grain|n',
                      '{skintone}a {severity} closing sear in the {location}, the stiffened dermis '
                      'softening and coming level|n',
                      '{skintone}a {severity} settling burn on the {location}, slate shedding to '
                      'show pearl beneath|n'],
          'scarred': ['{skintone}a {severity} glassy burn scar across the {location}, '
                      'poured-looking and clouded grey where the heat sat|n',
                      '{skintone}a {severity} old scorch mark on the {location}, opaline and '
                      'smoke-darkened along the line the heat took|n',
                      '{skintone}a {severity} healed burn mark in the {location}, faintly rippled '
                      'and discoloured a heat-dulled pearl|n']}}


#: Per-injury vocabulary (#3512): preferred over WOUND_DESCRIPTIONS /
#: COMPOUND_DESCRIPTIONS by injury type; those tables remain the fallback.
COMPOUND_BY_INJURY = {'blunt': {'fresh': ['|Ba {severity} dent-bloom, the worst of several on the {location}, cobalt '
                     'pooling beneath each|n',
                     '|Ba {severity} impact mark and {others_phrase} on the {location}, the dermis '
                     'blue-dark under every one|n'],
           'treated': ['{skintone}a {severity} compressed contusion and {others_phrase} on the '
                       '{location}, all of them under {compression_wrap_color}wrap|n',
                       '{skintone}a {severity} taped impact mark and {others_phrase} on the '
                       '{location}, the subdermal cobalt pressed flat under each|n'],
           'healing': ['{skintone}a {severity} fading bloom and {others_phrase} on the {location}, '
                       'the pooled cobalt paling in step|n',
                       '{skintone}a {severity} settling dent and {others_phrase} on the '
                       '{location}, the surface coming level by degrees|n'],
           'scarred': ['{skintone}a scatter of faint dent-prints on the {location}, their outlines '
                       'too regular to be chance|n',
                       '{skintone}opaline dent-shadows, one beside another across the {location}, '
                       'every dip still set low in the dermis|n']},
 'bullet': {'fresh': ['|Ba {severity} bullet hole, the worst of several punched into the '
                      '{location}, cobalt tracking from each|n',
                      '|Ba {severity} entry wound and {others_phrase} in the {location}, every '
                      'channel dark and welling blue|n'],
            'treated': ['{skintone}a {severity} packed bullet wound and {others_phrase} on the '
                        '{location}, {bandage_color}gauze|n{skintone} plugging every channel|n',
                        '{skintone}a {severity} dressed gunshot wound and {others_phrase} on the '
                        '{location}, cobalt blotting each pad and drying slate at its edge|n'],
            'healing': ['{skintone}a {severity} closing bullet channel and {others_phrase} on the '
                        '{location}, all of them paling toward pearl|n',
                        '{skintone}a {severity} knitting entry wound and {others_phrase} in the '
                        '{location}, new dermis filling every ring|n'],
            'scarred': ['{skintone}a stipple of pearlescent pocks across the {location}, each a '
                        'filled circle where a round went in|n',
                        '{skintone}pearl bullet-plugs in a loose line down the {location}, every '
                        'one a filled hole set flush and lacquer-smooth|n']},
 'stab': {'fresh': ['|Ba {severity} stab wound, the worst of several driven into the {location}, '
                    'cobalt welling from every slot|n',
                    '|Ba {severity} puncture and {others_phrase} in the {location}, each one '
                    'narrow and blue-dark|n'],
          'treated': ['{skintone}a {severity} packed stab wound and {others_phrase} on the '
                      '{location}, {bandage_color}gauze|n{skintone} fed thin into every slot|n',
                      '{skintone}a {severity} sutured puncture and {others_phrase} on the '
                      '{location}, {suture_color}stitches|n{skintone} spaced the same across all '
                      'of them|n'],
          'healing': ['{skintone}a {severity} closing stab wound and {others_phrase} in the '
                      '{location}, each slot narrowing to a hairline|n',
                      '{skintone}a {severity} mending puncture and {others_phrase} on the '
                      '{location}, filling in at the same quiet rate|n'],
          'scarred': ['{skintone}a row of hairline puncture seams on the {location}, pearl and set '
                      'flush with the dermis|n',
                      '{skintone}several short opaline slots in the {location}, each an old '
                      'puncture filled flush and no wider than a needle track|n']},
 'cut': {'fresh': ['|Ba {severity} cut, the worst of several crossing the {location}, cobalt '
                   'beading along each clean edge|n',
                   '|Ba {severity} blade line and {others_phrase} on the {location}, every one '
                   'welling blue-dark|n'],
         'treated': ['{skintone}a {severity} sutured cut and {others_phrase} on the {location}, '
                     '{suture_color}stitches|n{skintone} run straight down each line|n',
                     '{skintone}a {severity} taped blade line and {others_phrase} on the '
                     '{location}, {medical_tape_color}closure strips|n{skintone} drawing every '
                     'squared edge shut|n'],
         'healing': ['{skintone}a {severity} closing cut and {others_phrase} on the {location}, '
                     'every line narrowing to a pale thread|n',
                     '{skintone}a {severity} mending slice and {others_phrase} across the '
                     '{location}, their squared edges coming level in step|n'],
         'scarred': ['{skintone}a stack of hairline blade scars on the {location}, pearl lines '
                     'drawn parallel and ruler-straight|n',
                     '{skintone}several old blade seams crossing the {location}, each a pearl line '
                     'no wider than the edge that made it|n']},
 'laceration': {'fresh': ['|Ba {severity} ragged tear, the worst of several across the {location}, '
                          'every layer beneath parting clean all the same|n',
                          '|Ba {severity} rip and {others_phrase} on the {location}, frayed above '
                          'and blue-dark below|n'],
                'treated': ['{skintone}a {severity} sutured laceration and {others_phrase} on the '
                            '{location}, {suture_color}stitches|n{skintone} tracking each tear in '
                            'even bites|n',
                            '{skintone}a {severity} stapled tear and {others_phrase} on the '
                            '{location}, {medical_staple_color}staples|n{skintone} bridging every '
                            'ragged edge|n'],
                'healing': ['{skintone}a {severity} knitting tear and {others_phrase} across the '
                            '{location}, all of them pulling straight as they close|n',
                            '{skintone}a {severity} mending laceration and {others_phrase} on the '
                            '{location}, slate flaking from each pale seam|n'],
                'scarred': ['{skintone}a fan of opaline tear-lines across the {location}, their '
                            'ragged paths set glass-smooth|n',
                            '{skintone}pearlescent tear-seams branching across the {location}, '
                            'each ragged path set unnaturally flat|n']},
 'burn': {'fresh': ['|Ba {severity} burn, the worst of several across the {location}, the dermis '
                    'glazed and tight between them|n',
                    '|Ba {severity} scorch and {others_phrase} on the {location}, each run glassy '
                    'and smoke-dulled|n'],
          'treated': ['{skintone}a {severity} dressed burn and {others_phrase} on the {location}, '
                      '{bandage_color}gauze|n{skintone} laid loose over every glazed run|n',
                      '{skintone}a {severity} salved scorch and {others_phrase} on the {location}, '
                      'ointment standing wet on each patch|n'],
          'healing': ['{skintone}a {severity} healing burn and {others_phrase} on the {location}, '
                      'new dermis creeping in across the glazed ground|n',
                      '{skintone}a {severity} mending scorch and {others_phrase} across the '
                      '{location}, their glaze dulling to a pale grain|n'],
          'scarred': ['{skintone}a field of glassy burn scars across the {location}, each poured '
                      'smooth and clouded grey|n',
                      '{skintone}smoke-darkened scorch patches over the {location}, each one '
                      'opaline and heat-clouded where the layers ran|n']}}
