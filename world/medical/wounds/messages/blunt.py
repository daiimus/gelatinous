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
        "A clean surgical amputation where the {location} once was, properly bandaged|n",
        "The {location} has been medically severed with sterile wound dressing|n",
        "A professionally treated amputation site where the {location} was removed|n",
        "The {location} has been cleanly amputated with surgical closure|n",
        "A sterile severance with medical sutures where the {location} once was|n",
        "The {location} has been surgically removed with proper medical care|n",
        "A medically treated amputation where the {location} was cleanly severed|n"
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
