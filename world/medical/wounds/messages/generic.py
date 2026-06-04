"""
Generic wound descriptions following weapon message pattern.

Fallback descriptions for unknown injury types.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} wound on the {location}|n",
        "|Ra {severity} injury to the {location} showing damage|n",
        "|Ra {severity} trauma on the {location} with visible harm|n",
        "|Ra {severity} wound in the {location} requiring attention|n",
        "|Ra {severity} injury on the {location} showing signs of damage|n",
        "|Ra {severity} traumatic wound in the {location}|n",
        "|Ra {severity} damaged area on the {location}|n"
    ],
    
    "treated": [
        "{skintone}a {severity} treated wound on the {location}|n",
        "{skintone}a {severity} bandaged injury in the {location}|n",
        "{skintone}a {severity} dressed wound on the {location} with {bandage_color}medical care|n",
        "{skintone}a {severity} treated trauma in the {location}|n",
        "{skintone}a {severity} medically attended injury on the {location}|n",
        "{skintone}a {severity} cared-for wound in the {location}|n",
        "{skintone}a {severity} treated damaged area on the {location}|n"
    ],
    
    "healing": [
        "{skintone}a {severity} healing wound on the {location}|n",
        "{skintone}a {severity} mending injury in the {location} showing recovery|n",
        "{skintone}a {severity} improving wound on the {location}|n",
        "{skintone}a {severity} healing trauma in the {location}|n",
        "{skintone}a {severity} recovering injury on the {location}|n",
        "{skintone}a {severity} mending wound in the {location} with progress|n",
        "{skintone}a {severity} healing damaged area on the {location}|n"
    ],
    
    "destroyed": [
        "|Ra {severity} catastrophic trauma has mangled the {location} beyond recognition|n",
        "|Ra {severity} devastating injury has left the {location} a bloody, ruined mess|n",
        "|Ra {severity} massive damage has reduced the {location} to torn tissue and gore|n",
        "|Ra {severity} horrific trauma has turned the {location} into unrecognizable wreckage|n",
        "|Ra {severity} catastrophic injury has left the {location} hanging by shreds|n",
        "|Ra {severity} devastating damage has obliterated the {location} in a spray of blood|n",
        "|Ra {severity} massive trauma has destroyed the {location} beyond repair|n"
    ],
    
    "severed": [
        "|RThe {location} has been severed at the joint, leaving a ragged stump|n",
        "|RWhere the {location} once attached, only a raw wound and bare bone remain|n",
        "|RA single brutal moment took the {location} away, the wound still weeping|n",
        "|RThe {location} is gone — severed cleanly, the stump bright with fresh blood|n",
        "|RA visceral amputation marks where the {location} once was, the wound raw|n",
        "|RThe {location} has been taken off the body, leaving a ragged, weeping wound|n",
        "|RBlood pools beneath the stump where the {location} used to be|n"
    ],
    
    "scarred": [
        "{skintone}a {severity} wound scar on the {location}|n",
        "{skintone}a {severity} injury scar in the {location} permanently marked|n",
        "{skintone}a {severity} trauma scar on the {location}|n",
        "{skintone}a {severity} old wound mark in the {location}|n",
        "{skintone}a {severity} healed injury scar on the {location}|n",
        "{skintone}a {severity} permanent wound mark in the {location}|n",
        "{skintone}a {severity} scar from old trauma on the {location}|n"
    ]
}


# Compound descriptions collapse two or more wounds at one location into a
# single concise line. The worst wound drives {severity}; {others_phrase}
# renders the remaining count ("another wound" / "several other wounds").
# Generic is the fallback set for any injury type lacking its own.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} wound and {others_phrase} mark the {location}|n",
        "|Ra {severity} wound joins {others_phrase} across the {location}|n",
        "|Rthe {location} bears a {severity} wound alongside {others_phrase}|n",
        "|Ra {severity} wound and {others_phrase} cover the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} treated wound and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} bandaged wound among {others_phrase}|n",
        "{skintone}a {severity} tended wound joins {others_phrase} on the {location}|n",
    ],

    "healing": [
        "{skintone}a {severity} healing wound and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} healing wound among {others_phrase}|n",
        "{skintone}a {severity} mending wound joins {others_phrase} on the {location}|n",
    ],

    "destroyed": [
        "|Ra {severity} ruinous wound and {others_phrase} have wrecked the {location}|n",
        "|Rthe {location} is a mangled ruin of a {severity} wound and {others_phrase}|n",
    ],

    "severed": [
        "|Ra {severity} wound and {others_phrase} surround the ruined {location}|n",
        "|Rthe ruined {location} is ringed by a {severity} wound and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} scar and {others_phrase} crisscross the {location}|n",
        "{skintone}the {location} is marked by a {severity} scar among {others_phrase}|n",
        "{skintone}a {severity} old scar joins {others_phrase} on the {location}|n",
    ],
}


# Paired-severance descriptions collapse a symmetric left/right pair that has
# been *cleanly amputated on both sides* into one plural stump line. The
# ``{location}`` slot receives a plural body-part phrase (e.g. "both hands").
# Severance prose is type-agnostic, so this single generic set serves every
# injury type. Rendered through ``_format_wound_grammar`` (capitalized and
# terminated), so templates need no leading capital or trailing period.
PAIRED_SEVERED_DESCRIPTIONS = [
    "a pair of clean surgical amputations where {location} once were, "
    "properly treated|n",
    "{location} have been medically severed with sterile bandaging|n",
    "a professionally treated pair of amputation sites where {location} "
    "were removed|n",
    "{location} have been cleanly amputated with proper medical closure|n",
    "a sterile pair of severances with surgical care where {location} "
    "once were|n",
    "{location} have been surgically removed with clinical precision|n",
]
