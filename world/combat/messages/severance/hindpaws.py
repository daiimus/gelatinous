"""Rat hindpaw severance templates — left or right hindpaw shorn off.

Fires when an edged hit destroys the small hindpaw bones on a rat.
The ``{hit_location}`` resolves to ``"left hindpaw"`` / ``"right hindpaw"``.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade shears {target_name}'s {hit_location} off at the ankle. The long-toed paw drops away.",
                "victim_msg": "{attacker_name}'s blade shears your {hit_location} off at the ankle. The paw drops away.",
                "observer_msg": "{attacker_name}'s blade shears {target_name}'s {hit_location} off at the ankle. The long-toed paw drops away.",
            },
            {
                "attacker_msg": "The cut takes {target_name}'s {hit_location} cleanly off. The body lists hard as the support disappears.",
                "victim_msg": "{attacker_name}'s cut takes your {hit_location} cleanly off. You list hard as the support disappears.",
                "observer_msg": "{attacker_name}'s cut takes {target_name}'s {hit_location} cleanly off. The body lists hard as the support disappears.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A neat stroke parts {target_name}'s {hit_location} at the ankle.",
                "victim_msg": "{attacker_name}'s neat stroke parts your {hit_location} at the ankle.",
                "observer_msg": "{attacker_name}'s neat stroke parts {target_name}'s {hit_location} at the ankle.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point in at {target_name}'s {hit_location} and pry. The paw tears free.",
                "victim_msg": "{attacker_name} drives the point in at your {hit_location} and pries. The paw tears free.",
                "observer_msg": "{attacker_name} drives the point in at {target_name}'s {hit_location} and pries. The paw tears free.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A controlled thrust takes {target_name}'s {hit_location} off at the ankle.",
                "victim_msg": "{attacker_name}'s controlled thrust takes your {hit_location} off at the ankle.",
                "observer_msg": "{attacker_name}'s controlled thrust takes {target_name}'s {hit_location} off at the ankle.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The torn blow rips {target_name}'s {hit_location} away in a spray of red.",
                "victim_msg": "{attacker_name}'s torn blow rips your {hit_location} away in a spray of red.",
                "observer_msg": "{attacker_name}'s torn blow rips {target_name}'s {hit_location} away in a spray of red.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A ragged tear takes {target_name}'s {hit_location} off at the ankle.",
                "victim_msg": "{attacker_name}'s ragged tear takes your {hit_location} off at the ankle.",
                "observer_msg": "{attacker_name}'s ragged tear takes {target_name}'s {hit_location} off at the ankle.",
            },
        ],
    },
}
