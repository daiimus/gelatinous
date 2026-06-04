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
        "|RThe {location} has been pried away at the joint, the wound torn and weeping|n",
        "|RWhere the {location} once attached, only torn ligaments and exposed bone remain|n",
        "|RA driven point levered the {location} off, the wound ragged but undeniable|n",
        "|RThe {location} is gone — wrenched free at the joint, the stump a mess of torn sinew|n",
        "|RA precise thrust pried the {location} away, leaving a wound that shouldn't be possible|n",
        "|RThe {location} has been impaled and torn loose, the wound ragged at the edges|n",
        "|RHard leverage took the {location} away, leaving a wound of torn ligaments and bared bone|n"
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


# Compound descriptions: two or more wounds at one location, worst-first.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} stab wound and {others_phrase} punch the {location}|n",
        "|Ra {severity} puncture joins {others_phrase} across the {location}|n",
        "|Rthe {location} is pierced by a {severity} stab wound alongside {others_phrase}|n",
        "|Ra {severity} stab wound and {others_phrase} riddle the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} packed stab wound and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} bandaged puncture among {others_phrase}|n",
    ],

    "healing": [
        "{skintone}a {severity} healing stab wound and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} closing puncture among {others_phrase}|n",
    ],

    "destroyed": [
        "|Ra {severity} stab wound has mangled the {location}, joined by {others_phrase}|n",
        "|Rthe {location} is a shredded ruin of a {severity} puncture and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} stab scar and {others_phrase} pock the {location}|n",
        "{skintone}the {location} is stippled by a {severity} puncture scar among {others_phrase}|n",
    ],
}


# Issue #347: destroyed-stage overlay keyed by location.
DESTROYED_BY_LOCATION = {
    "left_eye": [
        "|R{Their} left eye is a punctured ruin, fluid leaking from the deep hole through it|n",
        "|RA driven thrust has skewered {their} left eye, the socket bleeding around the puncture|n",
        "|R{Their} left eye is collapsed inward around a deep puncture wound|n",
        "|RWhere {their} left eye sat, a narrow ragged hole weeps fluid and dark blood|n",
    ],
    "right_eye": [
        "|R{Their} right eye is a punctured ruin, fluid leaking from the deep hole through it|n",
        "|RA driven thrust has skewered {their} right eye, the socket bleeding around the puncture|n",
        "|R{Their} right eye is collapsed inward around a deep puncture wound|n",
        "|RWhere {their} right eye sat, a narrow ragged hole weeps fluid and dark blood|n",
    ],
    "left_ear": [
        "|R{Their} left ear is punctured through, a dark hole bored clean across the cartilage|n",
        "|RA thrust has driven through {their} left ear, leaving a torn passage front to back|n",
        "|R{Their} left ear hangs limp around a deep stab hole|n",
        "|RWhat is left of {their} left ear surrounds a punched-through wound seeping blood|n",
    ],
    "right_ear": [
        "|R{Their} right ear is punctured through, a dark hole bored clean across the cartilage|n",
        "|RA thrust has driven through {their} right ear, leaving a torn passage front to back|n",
        "|R{Their} right ear hangs limp around a deep stab hole|n",
        "|RWhat is left of {their} right ear surrounds a punched-through wound seeping blood|n",
    ],
}
