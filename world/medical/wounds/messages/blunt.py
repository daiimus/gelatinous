"""
Blunt trauma wound descriptions following weapon message pattern.

Multiple description variants for each healing stage.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} bruise on the {location} with dark discoloration|n",
        "|Ra {severity} contusion in the {location} swollen and tender|n",
        "|Ra {severity} impact wound on the {location} with split skin|n",
        "|Ra {severity} blunt trauma to the {location} showing purple marks|n",
        "|Ra {severity} crushing injury on the {location} with broken capillaries|n",
        "|Ra {severity} bludgeoning wound in the {location} deeply bruised|n",
        "|Ra {severity} impact bruise on the {location} with spreading hematoma|n"
    ],
    
    "treated": [
        "{skintone}a {severity} treated bruise on the {location} with {ice_pack_color}ice pack marks|n",
        "{skintone}a {severity} bandaged contusion in the {location}|n",
        "{skintone}a {severity} wrapped blunt trauma on the {location} with {compression_wrap_color}compression|n",
        "{skintone}a {severity} treated impact wound in the {location}|n",
        "{skintone}a {severity} compressed crushing injury on the {location}|n",
        "{skintone}a {severity} dressed bludgeoning wound in the {location}|n",
        "{skintone}a {severity} treated impact bruise on the {location} with {compression_wrap_color}support wrap|n"
    ],
    
    "healing": [
        "{skintone}a {severity} healing bruise on the {location} changing to yellow-green|n",
        "{skintone}a {severity} fading contusion in the {location} with reduced swelling|n",
        "{skintone}a {severity} improving blunt trauma on the {location}|n",
        "{skintone}a {severity} mending impact wound in the {location} less tender|n",
        "{skintone}a {severity} healing crushing injury on the {location}|n",
        "{skintone}a {severity} recovering bludgeoning wound in the {location}|n",
        "{skintone}a {severity} healing impact bruise on the {location} with normal color returning|n"
    ],
    
    "destroyed": [
        "|Ra {severity} devastating blunt trauma has mangled the {location} into pulp|n",
        "|Ra {severity} massive impact has left the {location} a crushed, bloody mess|n",
        "|Ra {severity} crushing force has reduced the {location} to shattered bone and gore|n",
        "|Ra {severity} brutal bludgeoning has turned the {location} into unrecognizable wreckage|n",
        "|Ra {severity} catastrophic impact has left the {location} hanging by mangled tissue|n",
        "|Ra {severity} horrific crushing has obliterated the {location} in a spray of blood|n",
        "|Ra {severity} devastating blunt force has pulverized the {location} beyond repair|n"
    ],
    
    "severed": [
        "|RThe {location} has been pulped off the body, the stump shattered and ragged|n",
        "|RWhere the {location} once attached, only a mangled mess of crushed tissue and splintered bone remains|n",
        "|RBlunt force took the {location} away, the wound a ruin of crushed bone and pulped meat|n",
        "|RThe {location} is gone — pounded loose from the joint, the stump torn and ragged|n",
        "|RA crushing severance marks where the {location} once was, the bone end pulverized|n",
        "|RThe {location} has been beaten off the body, the wound a brutal pulp|n",
        "|RHeavy impact tore the {location} away, leaving a wreck of crushed bone and torn skin|n"
    ],
    
    "scarred": [
        "{skintone}a {severity} faded bruise mark on the {location}|n",
        "{skintone}a {severity} old contusion scar in the {location} barely visible|n",
        "{skintone}a {severity} healed blunt trauma mark on the {location}|n",
        "{skintone}a {severity} impact scar in the {location} with slight discoloration|n",
        "{skintone}a {severity} old crushing injury mark on the {location}|n",
        "{skintone}a {severity} bludgeoning scar in the {location} permanently marking|n",
        "{skintone}a {severity} healed impact wound scar on the {location}|n"
    ]
}


# Compound descriptions: two or more wounds at one location, worst-first.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} contusion and {others_phrase} mottle the {location}|n",
        "|Ra {severity} impact wound joins {others_phrase} across the {location}|n",
        "|Rthe {location} is battered by a {severity} contusion alongside {others_phrase}|n",
        "|Ra {severity} contusion and {others_phrase} bruise the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} wrapped contusion and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} compressed impact wound among {others_phrase}|n",
    ],

    "healing": [
        "{skintone}a {severity} fading contusion and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} healing impact wound among {others_phrase}|n",
    ],

    "destroyed": [
        "|Ra {severity} crushing blow has pulped the {location}, joined by {others_phrase}|n",
        "|Rthe {location} is a shattered ruin of a {severity} contusion and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} impact scar and {others_phrase} discolor the {location}|n",
        "{skintone}the {location} is mottled by a {severity} contusion scar among {others_phrase}|n",
    ],
}


# Issue #347: destroyed-stage overlay keyed by location.
DESTROYED_BY_LOCATION = {
    "left_eye": [
        "|R{Their} left eye is pulped in its socket, the lid swollen black around the ruin|n",
        "|RA crushing impact has burst {their} left eye, fluid weeping over the bruised cheek|n",
        "|R{Their} left eye is collapsed inward, the socket caved and weeping|n",
        "|RWhat was {their} left eye is a sunken pulp, the orbital bone pressed flat around it|n",
    ],
    "right_eye": [
        "|R{Their} right eye is pulped in its socket, the lid swollen black around the ruin|n",
        "|RA crushing impact has burst {their} right eye, fluid weeping over the bruised cheek|n",
        "|R{Their} right eye is collapsed inward, the socket caved and weeping|n",
        "|RWhat was {their} right eye is a sunken pulp, the orbital bone pressed flat around it|n",
    ],
    "left_ear": [
        "|R{Their} left ear is mashed flat against the skull, the cartilage crushed and weeping|n",
        "|RA heavy blow has pulped {their} left ear into the side of {their} head|n",
        "|R{Their} left ear is reduced to a swollen lump of bruised tissue|n",
        "|RWhat is left of {their} left ear is a flattened ruin, dark with bruise and blood|n",
    ],
    "right_ear": [
        "|R{Their} right ear is mashed flat against the skull, the cartilage crushed and weeping|n",
        "|RA heavy blow has pulped {their} right ear into the side of {their} head|n",
        "|R{Their} right ear is reduced to a swollen lump of bruised tissue|n",
        "|RWhat is left of {their} right ear is a flattened ruin, dark with bruise and blood|n",
    ],
    # Face — issue #355.
    "face": [
        "|R{Their} {organ} is pulped, the flesh swollen black around the ruin|n",
        "|RA crushing impact has burst {their} {organ}, fluid weeping down the bruised cheek|n",
        "|R{Their} {organ} is collapsed inward, the bone caved beneath the impact|n",
        "|RWhat was {their} {organ} is a sunken pulp, the surrounding flesh pressed flat|n",
    ],
}


# Issue #350 / PR-C: paired destruction overlay (blunt).
DESTROYED_BY_PAIR = {
    "eyes": [
        "|RBoth of {their} eyes are pulped in their sockets, the lids swollen black around the twin ruins|n",
        "|RCrushing impacts have burst both of {their} eyes, fluid weeping over the bruised cheeks|n",
        "|R{Their} eyes are collapsed inward on both sides, the sockets caved and weeping|n",
        "|RWhat was {their} eyes are sunken pulps, the orbital bones pressed flat around them|n",
    ],
    "ears": [
        "|RBoth of {their} ears are mashed flat against the skull, the cartilage crushed and weeping|n",
        "|RHeavy blows have pulped both of {their} ears into the sides of {their} head|n",
        "|R{Their} ears are reduced to swollen lumps of bruised tissue on both sides|n",
        "|RWhat is left of {their} ears are flattened ruins, dark with bruise and blood|n",
    ],
}
