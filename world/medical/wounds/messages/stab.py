"""
Stabbing wound descriptions following weapon message pattern.

Multiple description variants for each healing stage.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} stab wound in the {location} with narrow opening|n",
        "|Ra {severity} puncture wound on the {location}, deep and bleeding|n",
        "|Ra {severity} thrust wound in the {location} with dark entrance|n",
        "|Ra {severity} piercing injury to the {location} penetrating deeply|n", 
        "|Ra {severity} stab hole in the {location} with jagged edges|n",
        "|Ra {severity} penetrating wound on the {location} seeping blood|n",
        "|Ra {severity} thrust puncture in the {location} with torn entry|n"
    ],
    
    "treated": [
        "{skintone}a {severity} packed stab wound in the {location}|n",
        "{skintone}a {severity} bandaged puncture wound on the {location}|n",
        "{skintone}a {severity} treated stab hole in the {location} with {bandage_color}pressure dressing|n",
        "{skintone}a {severity} packed thrust wound in the {location}|n",
        "{skintone}a {severity} dressed piercing injury on the {location}|n",
        "{skintone}a {severity} secured stab wound in the {location} with {bandage_color}gauze packing|n",
        "{skintone}a {severity} treated puncture in the {location} under {bandage_color}medical wrap|n"
    ],
    
    "healing": [
        "{skintone}a {severity} healing stab wound in the {location} with closing entry|n",
        "{skintone}a {severity} mending puncture wound on the {location}|n",
        "{skintone}a {severity} recovering stab hole in the {location} showing improvement|n",
        "{skintone}a {severity} healing thrust wound in the {location} with new tissue|n",
        "{skintone}a {severity} closing piercing injury on the {location}|n",
        "{skintone}a {severity} improving stab wound in the {location} less tender|n",
        "{skintone}a {severity} healing puncture on the {location} with reduced depth|n"
    ],
    
    "destroyed": [
        "|Ra {severity} catastrophic stab wound has mangled the {location} into a bloody mess|n",
        "|Ra {severity} massive puncture has left the {location} hanging by torn tissue|n",
        "|Ra {severity} devastating thrust has reduced the {location} to shredded remains|n",
        "|Ra {severity} piercing trauma has turned the {location} into a gory ruin|n",
        "|Ra {severity} brutal stabbing has left the {location} barely attached|n",
        "|Ra {severity} savage puncture has destroyed the {location} in a tangle of gore|n",
        "|Ra {severity} massive piercing has obliterated the {location} beyond recognition|n"
    ],
    
    "severed": [
        "A clean surgical amputation where the {location} once was, properly sutured|n",
        "The {location} has been medically severed with sterile bandaging|n",
        "A professionally treated amputation site where the {location} was removed|n",
        "The {location} has been cleanly amputated with surgical closure|n",
        "A sterile severance with medical sutures where the {location} once was|n",
        "The {location} has been surgically removed with proper wound care|n",
        "A medically treated amputation site where the {location} was cleanly severed|n"
    ],
    
    "scarred": [
        "{skintone}a {severity} stab wound scar in the {location}|n",
        "{skintone}a {severity} puncture scar on the {location} with small depression|n",
        "{skintone}a {severity} thrust wound scar in the {location} barely visible|n",
        "{skintone}a {severity} old piercing injury mark on the {location}|n",
        "{skintone}a {severity} stab scar in the {location} with puckered center|n",
        "{skintone}a {severity} healed puncture wound mark on the {location}|n",
        "{skintone}a {severity} faded stab scar in the {location}|n"
    ]
}
