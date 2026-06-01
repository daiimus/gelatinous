"""
Cutting wound descriptions following weapon message pattern.

Multiple description variants for each healing stage.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} cut across the {location} with clean edges|n",
        "|Ra {severity} slash wound on the {location}, bleeding steadily|n",
        "|Ra {severity} laceration in the {location} with gaping sides|n",
        "|Ra {severity} knife wound on the {location} with sharp borders|n",
        "|Ra {severity} slice through the {location}, deep and precise|n",
        "|Ra {severity} cutting wound in the {location} exposing deeper tissue|n",
        "|Ra {severity} blade mark on the {location} with trickling blood|n"
    ],
    
    "treated": [
        "{skintone}a {severity} sutured cut on the {location} with {suture_color}neat stitches|n",
        "{skintone}a {severity} bandaged slash wound in the {location}|n",
        "{skintone}a {severity} dressed laceration on the {location} with {suture_color}surgical thread|n",
        "{skintone}a {severity} treated knife wound in the {location} held closed|n",
        "{skintone}a {severity} closed cutting wound on the {location} with {medical_staple_color}medical staples|n",
        "{skintone}a {severity} stitched slice in the {location} under {bandage_color}clean dressing|n",
        "{skintone}a {severity} repaired blade wound on the {location}|n"
    ],
    
    "healing": [
        "{skintone}a {severity} healing cut on the {location} with forming scab|n",
        "{skintone}a {severity} mending slash wound in the {location} showing new skin|n",
        "{skintone}a {severity} closing laceration on the {location} with reduced gaping|n",
        "{skintone}a {severity} recovering knife wound in the {location}|n",
        "{skintone}a {severity} healing slice through the {location} with pink edges|n",
        "{skintone}a {severity} improving cutting wound on the {location}|n",
        "{skintone}a {severity} knitting blade wound in the {location}|n"
    ],
    
    "destroyed": [
        "|Ra {severity} devastating cut has mangled the {location} into ribbons of flesh|n",
        "|Ra {severity} massive slash has left the {location} hanging by threads of tissue|n",
        "|Ra {severity} brutal laceration has reduced the {location} to bloody tatters|n",
        "|Ra {severity} savage blade work has shredded the {location} beyond recognition|n",
        "|Ra {severity} catastrophic slicing has turned the {location} into a gory mess|n",
        "|Ra {severity} horrific cutting has left the {location} barely attached|n",
        "|Ra {severity} brutal blade trauma has obliterated the {location} in a spray of gore|n"
    ],
    
    "severed": [
        "A clean surgical amputation where the {location} once was, properly closed|n",
        "The {location} has been medically severed with neat surgical stitching|n",
        "A professionally treated amputation site where the {location} was removed|n",
        "The {location} has been cleanly amputated with sterile dressing|n",
        "A surgical severance with proper closure where the {location} once was|n",
        "The {location} has been surgically removed with clinical care|n",
        "A medically treated amputation where the {location} was cleanly severed|n"
    ],
    
    "scarred": [
        "{skintone}a {severity} cutting scar across the {location}|n",
        "{skintone}a {severity} slash scar on the {location} with thin white line|n",
        "{skintone}a {severity} laceration scar in the {location} barely visible|n",
        "{skintone}a {severity} knife wound scar on the {location} permanently etched|n",
        "{skintone}a {severity} blade scar through the {location} with smooth texture|n",
        "{skintone}a {severity} old cutting wound mark on the {location}|n",
        "{skintone}a {severity} faded slash scar in the {location}|n"
    ]
}


# Compound descriptions: two or more wounds at one location, worst-first.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} laceration and {others_phrase} crisscross the {location}|n",
        "|Ra {severity} gash joins {others_phrase} across the {location}|n",
        "|Rthe {location} is opened by a {severity} cut alongside {others_phrase}|n",
        "|Ra {severity} slash and {others_phrase} score the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} sutured laceration and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} stitched gash among {others_phrase}|n",
    ],

    "healing": [
        "{skintone}a {severity} healing laceration and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} knitting gash among {others_phrase}|n",
    ],

    "destroyed": [
        "|Ra {severity} cut has flayed the {location}, joined by {others_phrase}|n",
        "|Rthe {location} is a shredded ruin of a {severity} laceration and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} slash scar and {others_phrase} line the {location}|n",
        "{skintone}the {location} is etched by a {severity} cutting scar among {others_phrase}|n",
    ],
}
