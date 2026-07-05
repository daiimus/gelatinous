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
