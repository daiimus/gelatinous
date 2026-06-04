"""
Laceration wound descriptions following weapon message pattern.

Used by weapons with ``damage_type: "laceration"`` — chainsaw, blowtorch,
and other tearing / chewing damage sources. Distinct from clean ``cut``
(blade slice) and impact ``stab`` (puncture): lacerations are ragged,
chewed, sawn wounds with torn edges and irregular shapes.

Multiple description variants for each healing stage. Compound
descriptions handle multiple wounds at the same location.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} jagged laceration across the {location} with torn edges|n",
        "|Ra {severity} ragged tear on the {location} weeping freely|n",
        "|Ra {severity} chewed wound in the {location} with shredded edges|n",
        "|Ra {severity} sawn gash on the {location} where the teeth bit deep|n",
        "|Ra {severity} ripped opening in the {location} exposing torn tissue|n",
        "|Ra {severity} mangled laceration on the {location} with bone visible|n",
        "|Ra {severity} torn wound on the {location} bleeding heavily|n"
    ],

    "treated": [
        "{skintone}a {severity} sutured laceration on the {location} with {suture_color}heavy stitches|n",
        "{skintone}a {severity} bandaged tear in the {location} with extensive dressing|n",
        "{skintone}a {severity} packed wound on the {location} held closed under {bandage_color}gauze|n",
        "{skintone}a {severity} treated rip in the {location} closed with effort|n",
        "{skintone}a {severity} dressed tear on the {location} under thick padding|n",
        "{skintone}a {severity} stapled laceration in the {location} with {medical_staple_color}industrial closure|n",
        "{skintone}a {severity} repaired tear on the {location} with visible stitching|n"
    ],

    "healing": [
        "{skintone}a {severity} healing laceration on the {location} with thick scabbing|n",
        "{skintone}a {severity} mending tear in the {location} drawing slowly closed|n",
        "{skintone}a {severity} knitting rip on the {location} with raised edges|n",
        "{skintone}a {severity} recovering tear in the {location}|n",
        "{skintone}a {severity} closing laceration on the {location} forming new skin|n",
        "{skintone}a {severity} improving rip wound in the {location}|n",
        "{skintone}a {severity} mending shredded wound on the {location}|n"
    ],

    "destroyed": [
        "|Ra {severity} devastating laceration has chewed the {location} into pulped ruin|n",
        "|Ra {severity} massive tearing has rent the {location} apart in ragged sheets|n",
        "|Ra {severity} brutal shredding has left the {location} unrecognizable|n",
        "|Ra {severity} savage chewing has reduced the {location} to ribbons and meat|n",
        "|Ra {severity} catastrophic tearing has obliterated the {location} in a spray of red|n",
        "|Ra {severity} horrific laceration has flayed the {location} to the bone|n",
        "|Ra {severity} brutal sawing has destroyed the {location} in pieces|n"
    ],

    "severed": [
        "|RThe {location} has been chewed off at the joint, the wound a savage ruin|n",
        "|RWhere the {location} once attached, only shredded tissue and splintered bone remain|n",
        "|RTearing teeth took the {location} away, leaving a wound torn and weeping|n",
        "|RThe {location} is gone — sawn off at the joint, the stump ragged and brutal|n",
        "|RA mauling severance marks where the {location} once was, the wound a shredded mess|n",
        "|RThe {location} has been torn loose from the body, leaving wreckage|n",
        "|RChain teeth tore the {location} away, leaving a stump of pulped meat and bone|n"
    ],

    "scarred": [
        "{skintone}a {severity} jagged laceration scar across the {location}|n",
        "{skintone}a {severity} ragged tear scar on the {location} permanently marked|n",
        "{skintone}a {severity} chewed wound scar in the {location} thick and raised|n",
        "{skintone}a {severity} old tearing scar on the {location} with bumpy texture|n",
        "{skintone}a {severity} healed shredded wound mark on the {location}|n",
        "{skintone}a {severity} faded tear scar in the {location} with rough edges|n",
        "{skintone}a {severity} permanent rip mark on the {location}|n"
    ]
}


# Compound descriptions: two or more wounds at one location, worst-first.
COMPOUND_DESCRIPTIONS = {
    "fresh": [
        "|Ra {severity} laceration and {others_phrase} chew across the {location}|n",
        "|Ra {severity} tear joins {others_phrase} ripping into the {location}|n",
        "|Rthe {location} is shredded by a {severity} laceration alongside {others_phrase}|n",
        "|Ra {severity} ragged wound and {others_phrase} score the {location}|n",
    ],

    "treated": [
        "{skintone}a {severity} sutured laceration and {others_phrase} dress the {location}|n",
        "{skintone}the {location} carries a {severity} stapled tear among {others_phrase}|n",
    ],

    "healing": [
        "{skintone}a {severity} healing laceration and {others_phrase} mend across the {location}|n",
        "{skintone}the {location} shows a {severity} knitting tear among {others_phrase}|n",
    ],

    "destroyed": [
        "|Ra {severity} laceration has flayed the {location}, joined by {others_phrase}|n",
        "|Rthe {location} is a shredded ruin of a {severity} tear and {others_phrase}|n",
    ],

    "scarred": [
        "{skintone}a {severity} tear scar and {others_phrase} line the {location}|n",
        "{skintone}the {location} is etched by a {severity} laceration scar among {others_phrase}|n",
    ],
}


# Issue #347: destroyed-stage overlay keyed by location.
DESTROYED_BY_LOCATION = {
    "left_eye": [
        "|R{Their} left eye is a jagged tear across the socket, vitreous fluid leaking through ragged flaps|n",
        "|RA brutal rip has shredded {their} left eye, the lid hanging in torn strips|n",
        "|R{Their} left eye is torn open across its width, the orb collapsed beneath ragged tissue|n",
        "|RWhere {their} left eye sat, a ripped wound leaks fluid down the cheek|n",
    ],
    "right_eye": [
        "|R{Their} right eye is a jagged tear across the socket, vitreous fluid leaking through ragged flaps|n",
        "|RA brutal rip has shredded {their} right eye, the lid hanging in torn strips|n",
        "|R{Their} right eye is torn open across its width, the orb collapsed beneath ragged tissue|n",
        "|RWhere {their} right eye sat, a ripped wound leaks fluid down the cheek|n",
    ],
    "left_ear": [
        "|R{Their} left ear is torn into ragged strips, the cartilage visible through shredded skin|n",
        "|RA brutal rip has torn {their} left ear in two, the upper portion lost|n",
        "|R{Their} left ear hangs in shredded ribbons of skin and cartilage|n",
        "|RWhat is left of {their} left ear is a torn mess of cartilage and skin tags|n",
    ],
    "right_ear": [
        "|R{Their} right ear is torn into ragged strips, the cartilage visible through shredded skin|n",
        "|RA brutal rip has torn {their} right ear in two, the upper portion lost|n",
        "|R{Their} right ear hangs in shredded ribbons of skin and cartilage|n",
        "|RWhat is left of {their} right ear is a torn mess of cartilage and skin tags|n",
    ],
}
