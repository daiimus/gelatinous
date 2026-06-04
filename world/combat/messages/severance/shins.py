"""Shin severance templates — left or right shin detached at the knee.

Fires when an edged hit destroys a left_shin or right_shin tibia. The
``{hit_location}`` kwarg resolves to ``"left shin"`` or ``"right shin"``.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade cleaves through {target_name}'s knee. The {hit_location} cartwheels away in a spray of red, and the body crashes to the deck without the leg to catch it.",
                "victim_msg": "{attacker_name}'s blade cleaves through your knee. Your {hit_location} cartwheels away in a spray of red.",
                "observer_msg": "{attacker_name}'s blade cleaves through {target_name}'s knee. The {hit_location} cartwheels away in a spray of red, and the body crashes to the deck without the leg to catch it.",
            },
            {
                "attacker_msg": "The tibia parts under your edge with a deep, satisfying crack. {target_name}'s {hit_location} drops away and the body topples in a slow, terrible arc.",
                "victim_msg": "Your tibia parts under {attacker_name}'s edge with a deep crack. Your {hit_location} drops away and you topple.",
                "observer_msg": "{target_name}'s tibia parts under {attacker_name}'s edge with a deep crack. The {hit_location} drops away and the body topples in a slow, terrible arc.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off at the knee in a single hard stroke. The leg falls, the body kneels, and blood floods the deck around the wound.",
                "victim_msg": "{attacker_name} takes your {hit_location} off at the knee in a single hard stroke. Your leg falls, you kneel.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off at the knee in a single hard stroke. The leg falls, the body kneels, and blood floods the deck.",
            },
            {
                "attacker_msg": "Your chop catches just below the kneecap and continues through. {target_name}'s {hit_location} flies free, blood arcing high behind it.",
                "victim_msg": "{attacker_name}'s chop catches just below your kneecap and continues through. Your {hit_location} flies free.",
                "observer_msg": "{attacker_name}'s chop catches just below {target_name}'s kneecap and continues through. The {hit_location} flies free, blood arcing high behind it.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A clean stroke at the knee joint and {target_name}'s {hit_location} separates from the leg in a moment of surgical precision.",
                "victim_msg": "{attacker_name}'s clean stroke at your knee joint and your {hit_location} separates from your leg.",
                "observer_msg": "{attacker_name}'s clean stroke at the knee joint and {target_name}'s {hit_location} separates from the leg in a moment of surgical precision.",
            },
            {
                "attacker_msg": "The edge finds the gap between femur and tibia and parts {target_name}'s {hit_location} away cleanly.",
                "victim_msg": "{attacker_name}'s edge finds the gap between your femur and tibia and parts your {hit_location} away cleanly.",
                "observer_msg": "{attacker_name}'s edge finds the gap between femur and tibia and parts {target_name}'s {hit_location} away cleanly.",
            },
            {
                "attacker_msg": "Your blade passes through the knee joint without complaint. {target_name}'s {hit_location} falls free, the cut so neat it could be admired.",
                "victim_msg": "{attacker_name}'s blade passes through your knee joint without complaint. Your {hit_location} falls free.",
                "observer_msg": "{attacker_name}'s blade passes through the knee joint without complaint. {target_name}'s {hit_location} falls free, the cut so neat it could be admired.",
            },
            {
                "attacker_msg": "One stroke, exactly placed at the joint. {target_name}'s {hit_location} comes away with no struggle and the body kneels with strange grace.",
                "victim_msg": "{attacker_name}'s one stroke, exactly placed. Your {hit_location} comes away with no struggle.",
                "observer_msg": "{attacker_name}'s one stroke, exactly placed at the joint. {target_name}'s {hit_location} comes away with no struggle and the body kneels with strange grace.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into the knee joint and *twist*. The patella shatters, the joint pries apart, and {target_name}'s {hit_location} hangs loose before it falls.",
                "victim_msg": "{attacker_name} drives the point into your knee joint and *twists*. Your patella shatters, your {hit_location} hangs loose.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s knee joint and *twists*. The patella shatters, the joint pries apart, and the {hit_location} hangs loose before it falls.",
            },
            {
                "attacker_msg": "Your thrust tears through the joint capsule. {target_name}'s {hit_location} comes loose in a wet, brutal moment, the leg flopping away from the knee.",
                "victim_msg": "{attacker_name}'s thrust tears through your joint capsule. Your {hit_location} comes loose in a wet, brutal moment.",
                "observer_msg": "{attacker_name}'s thrust tears through the joint capsule. {target_name}'s {hit_location} comes loose in a wet, brutal moment, the leg flopping away from the knee.",
            },
            {
                "attacker_msg": "The point goes deep and levers downward. {target_name}'s {hit_location} tears free at the knee, dragging tendons behind it like reins.",
                "victim_msg": "{attacker_name}'s point goes deep and levers downward. Your {hit_location} tears free at the knee.",
                "observer_msg": "{attacker_name}'s point goes deep and levers downward. {target_name}'s {hit_location} tears free at the knee, dragging tendons behind it like reins.",
            },
            {
                "attacker_msg": "You shove the blade through the patella and *grind*. The joint disintegrates and {target_name}'s {hit_location} drops away in a spray of bone and meat.",
                "victim_msg": "{attacker_name} shoves the blade through your patella and *grinds*. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name} shoves the blade through {target_name}'s patella and *grinds*. The joint disintegrates and the {hit_location} drops away in a spray of bone and meat.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slips into the knee joint with surgical precision and {target_name}'s {hit_location} separates from the leg in a single clean motion.",
                "victim_msg": "{attacker_name}'s point slips into your knee joint with surgical precision and your {hit_location} separates from your leg.",
                "observer_msg": "{attacker_name}'s point slips into the knee joint with surgical precision and {target_name}'s {hit_location} separates from the leg in a single clean motion.",
            },
            {
                "attacker_msg": "A precise thrust at the joint and {target_name}'s {hit_location} comes loose. The body finds the floor with surprising grace.",
                "victim_msg": "{attacker_name}'s precise thrust at your joint and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s precise thrust at the joint and {target_name}'s {hit_location} comes loose. The body finds the floor with surprising grace.",
            },
            {
                "attacker_msg": "Your blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops away.",
                "victim_msg": "{attacker_name}'s blade finds your joint capsule and parts it without violence. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name}'s blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops away.",
            },
            {
                "attacker_msg": "The thrust is economical and exact. {target_name}'s {hit_location} comes free from the knee with no fanfare.",
                "victim_msg": "{attacker_name}'s thrust is economical and exact. Your {hit_location} comes free from your knee with no fanfare.",
                "observer_msg": "{attacker_name}'s thrust is economical and exact. {target_name}'s {hit_location} comes free from the knee with no fanfare.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s knee in a wet grinding chorus. The {hit_location} drops away in pieces, leaving the leg ending at a shredded stump.",
                "victim_msg": "Chain teeth chew through your knee in a wet grinding chorus. Your {hit_location} drops away in pieces.",
                "observer_msg": "Chain teeth chew through {target_name}'s knee in a wet grinding chorus. The {hit_location} drops away in pieces, leaving the leg ending at a shredded stump.",
            },
            {
                "attacker_msg": "You saw through {target_name}'s knee and the tibia splinters under the chain. The {hit_location} comes apart in a slurry of bone and muscle.",
                "victim_msg": "{attacker_name} saws through your knee and your tibia splinters. Your {hit_location} comes apart.",
                "observer_msg": "{attacker_name} saws through {target_name}'s knee and the tibia splinters under the chain. The {hit_location} comes apart in a slurry of bone and muscle.",
            },
            {
                "attacker_msg": "Your blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood pooling instantly.",
                "victim_msg": "{attacker_name}'s blade catches and *grinds*. Your {hit_location} tears free.",
                "observer_msg": "{attacker_name}'s blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood pooling instantly.",
            },
            {
                "attacker_msg": "The chain rips through {target_name}'s knee, dragging skin and tendon and bone shards. The {hit_location} comes off ragged but undeniable.",
                "victim_msg": "{attacker_name}'s chain rips through your knee. Your {hit_location} comes off ragged but undeniable.",
                "observer_msg": "{attacker_name}'s chain rips through {target_name}'s knee, dragging skin and tendon and bone shards. The {hit_location} comes off ragged but undeniable.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but the knee gives way. {target_name}'s {hit_location} parts from the leg in a moment that's more tear than slice.",
                "victim_msg": "{attacker_name}'s cut is rough but your knee gives way. Your {hit_location} parts from your leg.",
                "observer_msg": "{attacker_name}'s cut is rough but the knee gives way. {target_name}'s {hit_location} parts from the leg in a moment that's more tear than slice.",
            },
            {
                "attacker_msg": "Serrated edge bites through the knee and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
                "victim_msg": "{attacker_name}'s serrated edge bites through your knee and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s serrated edge bites through the knee and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
            },
            {
                "attacker_msg": "You drag the blade through {target_name}'s knee and the {hit_location} parts free, the cut ragged but the result clear.",
                "victim_msg": "{attacker_name} drags the blade through your knee and your {hit_location} parts free.",
                "observer_msg": "{attacker_name} drags the blade through {target_name}'s knee and the {hit_location} parts free, the cut ragged but the result clear.",
            },
            {
                "attacker_msg": "The tear is uneven but the tibia surrenders. {target_name}'s {hit_location} drops away in a wash of red.",
                "victim_msg": "{attacker_name}'s tear is uneven but your tibia surrenders. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name}'s tear is uneven but the tibia surrenders. {target_name}'s {hit_location} drops away in a wash of red.",
            },
        ],
    },
}
