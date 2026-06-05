"""Rat tail severance templates — tail detached at the base.

Fires when an edged hit destroys the tail vertebrae on a rat.
The ``{hit_location}`` resolves to ``"tail"``.  Unique to rat
anatomy; no human equivalent.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade catches {target_name}'s {hit_location} at the base. The long, ringed length whips away across the ground.",
                "victim_msg": "{attacker_name}'s blade catches your {hit_location} at the base. The long length whips away.",
                "observer_msg": "{attacker_name}'s blade catches {target_name}'s {hit_location} at the base. The long, ringed length whips away across the ground.",
            },
            {
                "attacker_msg": "The cut takes {target_name}'s {hit_location} off cleanly at the base. The tail twitches once and lies still.",
                "victim_msg": "{attacker_name}'s cut takes your {hit_location} off cleanly at the base.",
                "observer_msg": "{attacker_name}'s cut takes {target_name}'s {hit_location} off cleanly at the base. The tail twitches once and lies still.",
            },
            {
                "attacker_msg": "You sever {target_name}'s {hit_location} with a single sharp stroke. The body lurches without its counterweight.",
                "victim_msg": "{attacker_name} severs your {hit_location} with a single stroke. The balance goes out from under you.",
                "observer_msg": "{attacker_name} severs {target_name}'s {hit_location} with a single sharp stroke. The body lurches without its counterweight.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A neat stroke takes {target_name}'s {hit_location} off at the base.",
                "victim_msg": "{attacker_name}'s neat stroke takes your {hit_location} off at the base.",
                "observer_msg": "{attacker_name}'s neat stroke takes {target_name}'s {hit_location} off at the base.",
            },
            {
                "attacker_msg": "Your edge finds the joint between vertebrae and {target_name}'s {hit_location} parts cleanly.",
                "victim_msg": "{attacker_name}'s edge finds the joint and your {hit_location} parts cleanly.",
                "observer_msg": "{attacker_name}'s edge finds the joint and {target_name}'s {hit_location} parts cleanly.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point in at the base of {target_name}'s {hit_location} and lever. The tail snaps off through the vertebrae.",
                "victim_msg": "{attacker_name} drives the point in at the base of your {hit_location} and levers. The tail snaps off.",
                "observer_msg": "{attacker_name} drives the point in at the base of {target_name}'s {hit_location} and levers. The tail snaps off through the vertebrae.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A controlled thrust pops {target_name}'s {hit_location} free at a vertebral joint.",
                "victim_msg": "{attacker_name}'s controlled thrust pops your {hit_location} free at a vertebral joint.",
                "observer_msg": "{attacker_name}'s controlled thrust pops {target_name}'s {hit_location} free at a vertebral joint.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The torn blow rips {target_name}'s {hit_location} away with a wet snap. The base of the spine shows in the ruin.",
                "victim_msg": "{attacker_name}'s torn blow rips your {hit_location} away. The base of your spine is exposed.",
                "observer_msg": "{attacker_name}'s torn blow rips {target_name}'s {hit_location} away with a wet snap. The base of the spine shows in the ruin.",
            },
            {
                "attacker_msg": "You tear {target_name}'s {hit_location} loose at the base, hide parting along the ringed scales.",
                "victim_msg": "{attacker_name} tears your {hit_location} loose at the base, hide parting along the rings.",
                "observer_msg": "{attacker_name} tears {target_name}'s {hit_location} loose at the base, hide parting along the ringed scales.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A ragged tear takes {target_name}'s {hit_location} off at the base.",
                "victim_msg": "{attacker_name}'s ragged tear takes your {hit_location} off at the base.",
                "observer_msg": "{attacker_name}'s ragged tear takes {target_name}'s {hit_location} off at the base.",
            },
        ],
    },
}
