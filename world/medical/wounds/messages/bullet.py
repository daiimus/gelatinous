"""
Bullet wound descriptions following weapon message pattern.

Multiple description variants for each healing stage.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} bullet hole punched through the {location}|n",
        "|Ra {severity} gunshot wound in the {location} with ragged edges|n",
        "|Ra {severity} bullet wound on the {location}, still oozing blood|n",
        "|Ra {severity} entry wound in the {location} surrounded by powder burns|n",
        "|Ra {severity} ballistic injury to the {location} with torn flesh|n",
        "|Ra {severity} projectile wound in the {location}, bleeding freely|n",
        "|Ra {severity} bullet puncture on the {location} with blackened edges|n"
    ],
    
    "treated": [
        "{skintone}a {severity} bandaged bullet wound on the {location}|n",
        "{skintone}a {severity} gunshot wound in the {location} wrapped in {bandage_color}clean gauze|n",
        "{skintone}a {severity} treated bullet hole in the {location} with {medical_tape_color}surgical dressing|n",
        "{skintone}a {severity} bullet wound on the {location} secured with {bandage_color}medical tape|n",
        "{skintone}a {severity} patched gunshot wound in the {location}|n",
        "{skintone}a {severity} dressed ballistic injury on the {location}|n",
        "{skintone}a {severity} bullet wound in the {location} covered by {bandage_color}field dressing|n"
    ],
    
    "healing": [
        "{skintone}a {severity} healing bullet wound on the {location} with fresh scab|n",
        "{skintone}a {severity} gunshot wound in the {location} showing pink new tissue|n",
        "{skintone}a {severity} mending bullet hole in the {location} with reduced swelling|n",
        "{skintone}a {severity} recovering ballistic injury on the {location}|n",
        "{skintone}a {severity} bullet wound in the {location} with healthy granulation|n",
        "{skintone}a {severity} healing gunshot wound on the {location}, less tender|n",
        "{skintone}a {severity} improving bullet puncture in the {location}|n"
    ],
    
    "destroyed": [
        "|Ra {severity} devastating bullet wound has mangled the {location} beyond recognition|n",
        "|Ra {severity} ballistic trauma has left the {location} a bloody, shattered mess|n",
        "|Ra {severity} gunshot has reduced the {location} to pulverized tissue and bone|n",
        "|Ra {severity} bullet has torn the {location} apart in a spray of blood and gore|n",
        "|Ra {severity} projectile damage has left the {location} hanging by sinew and skin|n",
        "|Ra {severity} explosive impact has turned the {location} into a mangled ruin|n",
        "|Ra {severity} high-caliber wound has obliterated the {location} in a mess of trauma|n"
    ],
    
    "severed": [
        "A clean surgical amputation where the {location} once was, properly bandaged|n",
        "The {location} has been medically severed with neat surgical dressing|n",
        "A professionally treated amputation site where the {location} was removed|n",
        "The {location} has been cleanly amputated with proper medical closure|n",
        "A sterile amputation site with surgical sutures where the {location} once was|n",
        "The {location} has been surgically removed with clinical precision|n",
        "A medically treated severance where the {location} was cleanly amputated|n"
    ],
    
    "scarred": [
        "{skintone}a {severity} bullet wound scar on the {location}|n",
        "{skintone}a {severity} gunshot scar in the {location} with puckered edges|n", 
        "{skintone}a {severity} ballistic scar on the {location}, permanently marking the flesh|n",
        "{skintone}a {severity} bullet hole scar in the {location} with radiating lines|n",
        "{skintone}a {severity} old gunshot wound mark on the {location}|n",
        "{skintone}a {severity} faded bullet scar in the {location}|n",
        "{skintone}a {severity} healed projectile wound scar on the {location}|n"
    ]
}


# Compound descriptions: two or more wounds at one location, worst-first.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} bullet wound and {others_phrase} riddle the {location}|n",
        "|Ra {severity} gunshot wound joins {others_phrase} across the {location}|n",
        "|Rthe {location} is torn by a {severity} bullet wound alongside {others_phrase}|n",
        "|Ra {severity} bullet wound and {others_phrase} pepper the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} bandaged bullet wound and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} patched gunshot wound among {others_phrase}|n",
    ],

    "healing": [
        "{skintone}a {severity} healing bullet wound and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} mending gunshot wound among {others_phrase}|n",
    ],

    "destroyed": [
        "|Ra {severity} gunshot has shattered the {location}, joined by {others_phrase}|n",
        "|Rthe {location} is a pulped ruin of a {severity} bullet wound and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} bullet scar and {others_phrase} pock the {location}|n",
        "{skintone}the {location} is stippled by a {severity} gunshot scar among {others_phrase}|n",
    ],
}
