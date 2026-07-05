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
