"""Hand severance templates — left or right hand detached at the wrist.

Fires when an edged hit destroys a left_hand or right_hand metacarpals.
The ``{hit_location}`` kwarg resolves to ``"left hand"`` or ``"right hand"``.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade takes {target_name}'s {hit_location} off at the wrist in a single arc. The hand falls still gripping at something it can no longer hold.",
                "victim_msg": "{attacker_name}'s blade takes your {hit_location} off at the wrist in a single arc. The hand falls still gripping at something it can no longer hold.",
                "observer_msg": "{attacker_name}'s blade takes {target_name}'s {hit_location} off at the wrist in a single arc. The hand falls still gripping at something it can no longer hold.",
            },
            {
                "attacker_msg": "A clean horizontal stroke and {target_name}'s {hit_location} is gone — spinning to the floor, fingers curled, the wound spurting red in time with their pulse.",
                "victim_msg": "{attacker_name}'s clean horizontal stroke and your {hit_location} is gone — spinning to the floor, fingers curled.",
                "observer_msg": "{attacker_name}'s clean horizontal stroke and {target_name}'s {hit_location} is gone — spinning to the floor, fingers curled, the wound spurting red.",
            },
            {
                "attacker_msg": "Bone parts at the joint and {target_name}'s {hit_location} drops to the deck with a wet slap, the body recoiling from its sudden incompleteness.",
                "victim_msg": "Bone parts at the joint and your {hit_location} drops to the deck with a wet slap, your body recoiling from its sudden incompleteness.",
                "observer_msg": "Bone parts at the joint and {target_name}'s {hit_location} drops to the deck with a wet slap, the body recoiling from its sudden incompleteness.",
            },
            {
                "attacker_msg": "Your edge passes through {target_name}'s wrist and the {hit_location} falls in a slow, terrible parabola. Blood traces an arc behind it.",
                "victim_msg": "{attacker_name}'s edge passes through your wrist and your {hit_location} falls in a slow, terrible parabola.",
                "observer_msg": "{attacker_name}'s edge passes through {target_name}'s wrist and the {hit_location} falls in a slow, terrible parabola. Blood traces an arc behind it.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A surgical cut at the wrist joint and {target_name}'s {hit_location} comes off as neatly as a glove being removed.",
                "victim_msg": "{attacker_name}'s surgical cut at your wrist joint and your {hit_location} comes off as neatly as a glove being removed.",
                "observer_msg": "{attacker_name}'s surgical cut at the wrist joint and {target_name}'s {hit_location} comes off as neatly as a glove being removed.",
            },
            {
                "attacker_msg": "The blade finds the gap between wrist bones and parts {target_name}'s {hit_location} from the body in a single uncomplicated motion.",
                "victim_msg": "{attacker_name}'s blade finds the gap between your wrist bones and parts your {hit_location} from your body in a single uncomplicated motion.",
                "observer_msg": "{attacker_name}'s blade finds the gap between {target_name}'s wrist bones and parts the {hit_location} from the body in a single uncomplicated motion.",
            },
            {
                "attacker_msg": "One stroke, no spectacle. {target_name}'s {hit_location} settles to the floor like it had been gently placed there.",
                "victim_msg": "{attacker_name}'s one stroke, no spectacle. Your {hit_location} settles to the floor like it had been gently placed there.",
                "observer_msg": "{attacker_name}'s one stroke, no spectacle. {target_name}'s {hit_location} settles to the floor like it had been gently placed there.",
            },
            {
                "attacker_msg": "Your edge finds the bone end and {target_name}'s {hit_location} drops free, the cut so clean it could be admired.",
                "victim_msg": "{attacker_name}'s edge finds your bone end and your {hit_location} drops free, the cut so clean it could be admired.",
                "observer_msg": "{attacker_name}'s edge finds the bone end and {target_name}'s {hit_location} drops free, the cut so clean it could be admired.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point through {target_name}'s wrist and *twist*. Carpal bones scatter, tendons part, the {hit_location} drops away in a mess.",
                "victim_msg": "{attacker_name} drives the point through your wrist and *twists*. Carpal bones scatter, tendons part, your {hit_location} drops away.",
                "observer_msg": "{attacker_name} drives the point through {target_name}'s wrist and *twists*. Carpal bones scatter, tendons part, the {hit_location} drops away in a mess.",
            },
            {
                "attacker_msg": "The thrust splits the wrist apart from the inside out. {target_name}'s {hit_location} hangs by a flap of skin for half a heartbeat, then falls.",
                "victim_msg": "{attacker_name}'s thrust splits your wrist apart from the inside out. Your {hit_location} hangs by a flap of skin, then falls.",
                "observer_msg": "{attacker_name}'s thrust splits the wrist apart from the inside out. {target_name}'s {hit_location} hangs by a flap of skin for half a heartbeat, then falls.",
            },
            {
                "attacker_msg": "Your point goes deep and levers outward. {target_name}'s {hit_location} tears free at the joint, leaving the bone end of the arm exposed and bleeding.",
                "victim_msg": "{attacker_name}'s point goes deep and levers outward. Your {hit_location} tears free at the joint.",
                "observer_msg": "{attacker_name}'s point goes deep and levers outward. {target_name}'s {hit_location} tears free at the joint, leaving the bone end of the arm exposed and bleeding.",
            },
            {
                "attacker_msg": "The blade impales the wrist and rips downward. {target_name}'s {hit_location} comes off in a brutal mechanical motion, blood spurting from severed arteries.",
                "victim_msg": "{attacker_name}'s blade impales your wrist and rips downward. Your {hit_location} comes off in a brutal mechanical motion.",
                "observer_msg": "{attacker_name}'s blade impales the wrist and rips downward. {target_name}'s {hit_location} comes off in a brutal mechanical motion, blood spurting from severed arteries.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slips between carpal bones and {target_name}'s {hit_location} parts from the body in a single small motion.",
                "victim_msg": "{attacker_name}'s point slips between your carpal bones and your {hit_location} parts from your body in a single small motion.",
                "observer_msg": "{attacker_name}'s point slips between carpal bones and {target_name}'s {hit_location} parts from the body in a single small motion.",
            },
            {
                "attacker_msg": "A precise thrust at the wrist joint and {target_name}'s {hit_location} simply comes loose, gravity doing the rest.",
                "victim_msg": "{attacker_name}'s precise thrust at your wrist joint and your {hit_location} simply comes loose.",
                "observer_msg": "{attacker_name}'s precise thrust at the wrist joint and {target_name}'s {hit_location} simply comes loose, gravity doing the rest.",
            },
            {
                "attacker_msg": "Your blade finds the precise gap and {target_name}'s {hit_location} drops away with no struggle, no flourish.",
                "victim_msg": "{attacker_name}'s blade finds the precise gap and your {hit_location} drops away with no struggle.",
                "observer_msg": "{attacker_name}'s blade finds the precise gap and {target_name}'s {hit_location} drops away with no struggle, no flourish.",
            },
            {
                "attacker_msg": "The point enters where it must and {target_name}'s {hit_location} parts from the wrist in a moment of mechanical certainty.",
                "victim_msg": "{attacker_name}'s point enters where it must and your {hit_location} parts from your wrist in a moment of mechanical certainty.",
                "observer_msg": "{attacker_name}'s point enters where it must and {target_name}'s {hit_location} parts from the wrist in a moment of mechanical certainty.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s wrist in a wet grinding chorus. The {hit_location} drops away, fingers still twitching like a question.",
                "victim_msg": "Chain teeth chew through your wrist in a wet grinding chorus. Your {hit_location} drops away, fingers still twitching.",
                "observer_msg": "Chain teeth chew through {target_name}'s wrist in a wet grinding chorus. The {hit_location} drops away, fingers still twitching like a question.",
            },
            {
                "attacker_msg": "You saw and *rip*. {target_name}'s {hit_location} comes apart at the wrist in a slurry of carpal fragments and torn skin.",
                "victim_msg": "{attacker_name} saws and *rips*. Your {hit_location} comes apart at the wrist in a slurry of carpal fragments.",
                "observer_msg": "{attacker_name} saws and *rips*. {target_name}'s {hit_location} comes apart at the wrist in a slurry of carpal fragments and torn skin.",
            },
            {
                "attacker_msg": "The serrated edge catches and drags. {target_name}'s {hit_location} tears free, the wound a ragged mess where the wrist used to be.",
                "victim_msg": "{attacker_name}'s serrated edge catches and drags. Your {hit_location} tears free.",
                "observer_msg": "{attacker_name}'s serrated edge catches and drags. {target_name}'s {hit_location} tears free, the wound a ragged mess where the wrist used to be.",
            },
            {
                "attacker_msg": "Your blade chews through {target_name}'s wrist in a single brutal pass. The {hit_location} comes off in pieces — bones, skin, gristle — but mostly it comes off.",
                "victim_msg": "{attacker_name}'s blade chews through your wrist in a single brutal pass. Your {hit_location} comes off in pieces.",
                "observer_msg": "{attacker_name}'s blade chews through {target_name}'s wrist in a single brutal pass. The {hit_location} comes off in pieces — bones, skin, gristle — but mostly it comes off.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but the wrist is narrow. {target_name}'s {hit_location} parts from the body in a tearing moment that ends quickly.",
                "victim_msg": "{attacker_name}'s cut is rough but your wrist is narrow. Your {hit_location} parts from your body in a tearing moment.",
                "observer_msg": "{attacker_name}'s cut is rough but the wrist is narrow. {target_name}'s {hit_location} parts from the body in a tearing moment that ends quickly.",
            },
            {
                "attacker_msg": "Serrated edge bites through the wrist and {target_name}'s {hit_location} comes loose, ragged but undeniable.",
                "victim_msg": "{attacker_name}'s serrated edge bites through your wrist and your {hit_location} comes loose, ragged but undeniable.",
                "observer_msg": "{attacker_name}'s serrated edge bites through the wrist and {target_name}'s {hit_location} comes loose, ragged but undeniable.",
            },
            {
                "attacker_msg": "You drag the blade across {target_name}'s wrist and the {hit_location} parts free in a small, tearing surrender.",
                "victim_msg": "{attacker_name} drags the blade across your wrist and your {hit_location} parts free.",
                "observer_msg": "{attacker_name} drags the blade across {target_name}'s wrist and the {hit_location} parts free in a small, tearing surrender.",
            },
            {
                "attacker_msg": "The tear is uneven but the result is unambiguous. {target_name}'s {hit_location} falls away, blood already pooling on the deck.",
                "victim_msg": "{attacker_name}'s tear is uneven but the result is unambiguous. Your {hit_location} falls away.",
                "observer_msg": "{attacker_name}'s tear is uneven but the result is unambiguous. {target_name}'s {hit_location} falls away, blood already pooling on the deck.",
            },
        ],
    },
}


# Chrome bank (#525): a CYBER_ARM's hand sheared at the wrist coupling.
# No blood — snapped finger servos, dead manipulator actuators.
CHROME_MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your edge shears through {target_name}'s {hit_location} at the wrist coupling. The chrome hand drops, finger servos still ticking, and clatters across the floor.",
                "victim_msg": "{attacker_name}'s edge shears through your {hit_location} at the wrist coupling. The hand drops, finger servos still ticking, and clatters away.",
                "observer_msg": "{attacker_name}'s edge shears through {target_name}'s {hit_location} at the wrist coupling. The chrome hand drops, finger servos still ticking, and clatters across the floor.",
            },
            {
                "attacker_msg": "Alloy parts with a shriek and {target_name}'s {hit_location} tears off at the wrist, the severed manipulator cables sparking once and going dead.",
                "victim_msg": "Alloy parts with a shriek and your {hit_location} tears off at the wrist, the manipulator cables sparking once and going dead.",
                "observer_msg": "Alloy parts with a shriek and {target_name}'s {hit_location} tears off at the wrist, the severed manipulator cables sparking once and going dead.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A clean stroke parts the wrist coupling and {target_name}'s {hit_location} drops free, fingers frozen mid-curl.",
                "victim_msg": "{attacker_name}'s clean stroke parts your wrist coupling and your {hit_location} drops free, fingers frozen mid-curl.",
                "observer_msg": "A clean stroke parts the wrist coupling and {target_name}'s {hit_location} drops free, fingers frozen mid-curl.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You punch the point through {target_name}'s wrist seam and the {hit_location} sags off its mount, dead alloy and trailing wire.",
                "victim_msg": "{attacker_name} punches the point through your wrist seam and your {hit_location} sags off its mount, dead alloy and trailing wire.",
                "observer_msg": "{attacker_name} punches the point through {target_name}'s wrist seam and the {hit_location} sags off its mount, dead alloy and trailing wire.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "Your point finds the wrist gap and {target_name}'s {hit_location} pops loose, sliding off its coupling.",
                "victim_msg": "{attacker_name}'s point finds your wrist gap and your {hit_location} pops loose, sliding off its coupling.",
                "observer_msg": "{attacker_name}'s point finds the wrist gap and {target_name}'s {hit_location} pops loose, sliding off its coupling.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "You saw through the wrist until the cable bundle parts; {target_name}'s {hit_location} swings free on a thread of wire and falls, sparking.",
                "victim_msg": "{attacker_name} saws through your wrist until the cable bundle parts; your {hit_location} swings free on a thread of wire and falls, sparking.",
                "observer_msg": "{attacker_name} saws through the wrist until the cable bundle parts; {target_name}'s {hit_location} swings free on a thread of wire and falls, sparking.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A short, tearing stroke severs the {hit_location} cable bundle and the dead hand drops away.",
                "victim_msg": "{attacker_name}'s tearing stroke severs your {hit_location} cable bundle and the dead hand drops away.",
                "observer_msg": "A short, tearing stroke severs {target_name}'s {hit_location} cable bundle and the dead hand drops away.",
            },
        ],
    },
}
