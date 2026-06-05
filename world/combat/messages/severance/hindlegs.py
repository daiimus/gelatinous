"""Rat hindleg severance templates — left or right hindleg detached.

Fires when an edged hit destroys a hindleg bone on a rat. The
``{hit_location}`` kwarg resolves to ``"left hindleg"`` or
``"right hindleg"``.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade takes {target_name}'s {hit_location} off at the hip in a single arc. The limb kicks once and falls still.",
                "victim_msg": "{attacker_name}'s blade takes your {hit_location} off at the hip. The limb kicks once and falls still.",
                "observer_msg": "{attacker_name}'s blade takes {target_name}'s {hit_location} off at the hip in a single arc. The limb kicks once and falls still.",
            },
            {
                "attacker_msg": "The chop parts {target_name}'s {hit_location} from the body. The small frame collapses sideways, no longer balanced.",
                "victim_msg": "{attacker_name}'s chop parts your {hit_location} from your body. You collapse sideways.",
                "observer_msg": "{attacker_name}'s chop parts {target_name}'s {hit_location} from the body. The small frame collapses sideways.",
            },
            {
                "attacker_msg": "You cleave {target_name}'s {hit_location} off and the bone snaps cleanly through the long muscle.",
                "victim_msg": "{attacker_name} cleaves your {hit_location} off and the bone snaps cleanly through the muscle.",
                "observer_msg": "{attacker_name} cleaves {target_name}'s {hit_location} off and the bone snaps cleanly through the long muscle.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A clean stroke separates {target_name}'s {hit_location} at the hip joint.",
                "victim_msg": "{attacker_name}'s clean stroke separates your {hit_location} at the hip joint.",
                "observer_msg": "{attacker_name}'s clean stroke separates {target_name}'s {hit_location} at the hip joint.",
            },
            {
                "attacker_msg": "The edge finds the joint and {target_name}'s {hit_location} comes away with little resistance.",
                "victim_msg": "{attacker_name}'s edge finds the joint and your {hit_location} comes away.",
                "observer_msg": "{attacker_name}'s edge finds the joint and {target_name}'s {hit_location} comes away.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point in at the hip and lever. {target_name}'s {hit_location} tears free along snapping ligaments.",
                "victim_msg": "{attacker_name} drives the point in at your hip and levers. Your {hit_location} tears free.",
                "observer_msg": "{attacker_name} drives the point in at {target_name}'s hip and levers. The {hit_location} tears free along snapping ligaments.",
            },
            {
                "attacker_msg": "A thrust under {target_name}'s {hit_location} pries the limb loose with a wet, popping sound.",
                "victim_msg": "{attacker_name}'s thrust under your {hit_location} pries the limb loose.",
                "observer_msg": "{attacker_name}'s thrust under {target_name}'s {hit_location} pries the limb loose.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A precise thrust pops {target_name}'s {hit_location} free at the hip socket.",
                "victim_msg": "{attacker_name}'s precise thrust pops your {hit_location} free at the hip socket.",
                "observer_msg": "{attacker_name}'s precise thrust pops {target_name}'s {hit_location} free at the hip socket.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The torn blow rips {target_name}'s {hit_location} away through muscle and skin.",
                "victim_msg": "{attacker_name}'s torn blow rips your {hit_location} away through muscle and skin.",
                "observer_msg": "{attacker_name}'s torn blow rips {target_name}'s {hit_location} away through muscle and skin.",
            },
            {
                "attacker_msg": "You tear {target_name}'s {hit_location} loose with a ragged pull, fur and bone parting together.",
                "victim_msg": "{attacker_name} tears your {hit_location} loose with a ragged pull.",
                "observer_msg": "{attacker_name} tears {target_name}'s {hit_location} loose with a ragged pull.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A ragged tear takes {target_name}'s {hit_location} off at the hip.",
                "victim_msg": "{attacker_name}'s ragged tear takes your {hit_location} off at the hip.",
                "observer_msg": "{attacker_name}'s ragged tear takes {target_name}'s {hit_location} off at the hip.",
            },
        ],
    },
}
