"""Rat forepaw severance templates — left or right forepaw shorn off.

Fires when an edged hit destroys the small forepaw bones on a rat.
The ``{hit_location}`` resolves to ``"left forepaw"`` / ``"right forepaw"``.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade shears {target_name}'s {hit_location} off at the wrist. The small paw with its dark claws drops away.",
                "victim_msg": "{attacker_name}'s blade shears your {hit_location} off at the wrist. The paw drops away.",
                "observer_msg": "{attacker_name}'s blade shears {target_name}'s {hit_location} off at the wrist. The small paw drops away.",
            },
            {
                "attacker_msg": "The cut takes {target_name}'s {hit_location} cleanly through the joint. The paw lands fingers-up, claws still gripping.",
                "victim_msg": "{attacker_name}'s cut takes your {hit_location} cleanly through the joint.",
                "observer_msg": "{attacker_name}'s cut takes {target_name}'s {hit_location} cleanly through the joint. The paw lands fingers-up.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A neat stroke parts {target_name}'s {hit_location} at the wrist.",
                "victim_msg": "{attacker_name}'s neat stroke parts your {hit_location} at the wrist.",
                "observer_msg": "{attacker_name}'s neat stroke parts {target_name}'s {hit_location} at the wrist.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point in at {target_name}'s {hit_location} and twist. The small paw pops free at the joint.",
                "victim_msg": "{attacker_name} drives the point in at your {hit_location} and twists. The paw pops free.",
                "observer_msg": "{attacker_name} drives the point in at {target_name}'s {hit_location} and twists. The small paw pops free at the joint.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A controlled thrust takes {target_name}'s {hit_location} off cleanly at the wrist.",
                "victim_msg": "{attacker_name}'s controlled thrust takes your {hit_location} off cleanly at the wrist.",
                "observer_msg": "{attacker_name}'s controlled thrust takes {target_name}'s {hit_location} off cleanly at the wrist.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The torn blow rips {target_name}'s {hit_location} away in a small spray of red.",
                "victim_msg": "{attacker_name}'s torn blow rips your {hit_location} away in a small spray of red.",
                "observer_msg": "{attacker_name}'s torn blow rips {target_name}'s {hit_location} away in a small spray of red.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A ragged tear takes {target_name}'s {hit_location} off at the wrist.",
                "victim_msg": "{attacker_name}'s ragged tear takes your {hit_location} off at the wrist.",
                "observer_msg": "{attacker_name}'s ragged tear takes {target_name}'s {hit_location} off at the wrist.",
            },
        ],
    },
}
