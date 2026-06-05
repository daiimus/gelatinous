"""Rat foreleg severance templates — left or right foreleg detached.

Fires when an edged hit destroys a foreleg bone on a rat. The
``{hit_location}`` kwarg resolves to ``"left foreleg"`` or
``"right foreleg"``.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade catches {target_name}'s {hit_location} clean at the shoulder. The small limb spins away in a thin red arc.",
                "victim_msg": "{attacker_name}'s blade catches your {hit_location} clean at the shoulder. The limb spins away.",
                "observer_msg": "{attacker_name}'s blade catches {target_name}'s {hit_location} clean at the shoulder. The small limb spins away in a thin red arc.",
            },
            {
                "attacker_msg": "The cut shears through {target_name}'s {hit_location} at the joint and the foreleg falls free, paw still curled.",
                "victim_msg": "{attacker_name}'s cut shears through your {hit_location} at the joint and the foreleg falls free.",
                "observer_msg": "{attacker_name}'s cut shears through {target_name}'s {hit_location} at the joint. The foreleg falls free, paw still curled.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off in a single sweep. The small body lurches sideways, no longer braced on that side.",
                "victim_msg": "{attacker_name} takes your {hit_location} off in a single sweep. Your body lurches sideways.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off in a single sweep. The small body lurches sideways.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A neat stroke parts {target_name}'s {hit_location} at the shoulder. The cut is almost clinical.",
                "victim_msg": "{attacker_name}'s neat stroke parts your {hit_location} at the shoulder.",
                "observer_msg": "{attacker_name}'s neat stroke parts {target_name}'s {hit_location} at the shoulder.",
            },
            {
                "attacker_msg": "The edge finds the gap between bones and {target_name}'s {hit_location} comes away easily.",
                "victim_msg": "{attacker_name}'s edge finds the gap between bones and your {hit_location} comes away.",
                "observer_msg": "{attacker_name}'s edge finds the gap between bones and {target_name}'s {hit_location} comes away.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point in under {target_name}'s {hit_location} and lever. The thin bone snaps and the limb tears free.",
                "victim_msg": "{attacker_name} drives the point in under your {hit_location} and levers. The bone snaps and the limb tears free.",
                "observer_msg": "{attacker_name} drives the point in under {target_name}'s {hit_location} and levers. The thin bone snaps and the limb tears free.",
            },
            {
                "attacker_msg": "A thrust under {target_name}'s {hit_location} pries it loose from the body in one motion.",
                "victim_msg": "{attacker_name}'s thrust under your {hit_location} pries it loose from your body in one motion.",
                "observer_msg": "{attacker_name}'s thrust under {target_name}'s {hit_location} pries it loose from the body.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A controlled thrust pops {target_name}'s {hit_location} free at the joint with minimal mess.",
                "victim_msg": "{attacker_name}'s controlled thrust pops your {hit_location} free at the joint.",
                "observer_msg": "{attacker_name}'s controlled thrust pops {target_name}'s {hit_location} free at the joint.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The torn edge of your blow rips {target_name}'s {hit_location} away in a spray of red and tissue.",
                "victim_msg": "{attacker_name}'s torn blow rips your {hit_location} away in a spray of red and tissue.",
                "observer_msg": "{attacker_name}'s torn blow rips {target_name}'s {hit_location} away in a spray of red and tissue.",
            },
            {
                "attacker_msg": "You tear {target_name}'s {hit_location} loose along a ragged seam, fur and flesh going together.",
                "victim_msg": "{attacker_name} tears your {hit_location} loose along a ragged seam.",
                "observer_msg": "{attacker_name} tears {target_name}'s {hit_location} loose along a ragged seam.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A ragged tear takes {target_name}'s {hit_location} off in pieces.",
                "victim_msg": "{attacker_name}'s ragged tear takes your {hit_location} off in pieces.",
                "observer_msg": "{attacker_name}'s ragged tear takes {target_name}'s {hit_location} off in pieces.",
            },
        ],
    },
}
