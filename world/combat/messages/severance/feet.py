"""Foot severance templates — left or right foot detached at the ankle.

Fires when an edged hit destroys a left_foot or right_foot metatarsals.
The ``{hit_location}`` kwarg resolves to ``"left foot"`` or ``"right foot"``.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade cleaves through {target_name}'s ankle in a low arc. The {hit_location} stays where it landed, while the leg lurches backward, finding no support.",
                "victim_msg": "{attacker_name}'s blade cleaves through your ankle in a low arc. Your {hit_location} stays where it was, while your leg lurches backward.",
                "observer_msg": "{attacker_name}'s blade cleaves through {target_name}'s ankle in a low arc. The {hit_location} stays where it landed, while the leg lurches backward, finding no support.",
            },
            {
                "attacker_msg": "The metatarsals shatter under your edge. {target_name}'s {hit_location} drops away in a spray of red, the stump beneath it shocked white.",
                "victim_msg": "Your metatarsals shatter under {attacker_name}'s edge. Your {hit_location} drops away in a spray of red.",
                "observer_msg": "{target_name}'s metatarsals shatter under {attacker_name}'s edge. The {hit_location} drops away in a spray of red, the stump beneath it shocked white.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off at the ankle joint and the body lurches forward, balance broken in a way nothing will fix.",
                "victim_msg": "{attacker_name} takes your {hit_location} off at the ankle joint and you lurch forward, balance broken.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off at the ankle joint and the body lurches forward, balance broken in a way nothing will fix.",
            },
            {
                "attacker_msg": "Your chop catches the heel and continues through. {target_name}'s {hit_location} drops away, the wound spurting in time with their racing pulse.",
                "victim_msg": "{attacker_name}'s chop catches your heel and continues through. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name}'s chop catches the heel and continues through. {target_name}'s {hit_location} drops away, the wound spurting in time with their racing pulse.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A surgical cut at the ankle joint and {target_name}'s {hit_location} separates from the leg with minimal fuss.",
                "victim_msg": "{attacker_name}'s surgical cut at your ankle joint and your {hit_location} separates from your leg.",
                "observer_msg": "{attacker_name}'s surgical cut at the ankle joint and {target_name}'s {hit_location} separates from the leg with minimal fuss.",
            },
            {
                "attacker_msg": "The edge finds the gap between tibia and metatarsals and parts {target_name}'s {hit_location} away cleanly.",
                "victim_msg": "{attacker_name}'s edge finds the gap between your tibia and metatarsals and parts your {hit_location} away cleanly.",
                "observer_msg": "{attacker_name}'s edge finds the gap between tibia and metatarsals and parts {target_name}'s {hit_location} away cleanly.",
            },
            {
                "attacker_msg": "Your blade passes through the ankle joint without resistance. {target_name}'s {hit_location} settles to the floor with strange grace.",
                "victim_msg": "{attacker_name}'s blade passes through your ankle joint without resistance. Your {hit_location} settles to the floor.",
                "observer_msg": "{attacker_name}'s blade passes through the ankle joint without resistance. {target_name}'s {hit_location} settles to the floor with strange grace.",
            },
            {
                "attacker_msg": "One stroke, exactly placed. {target_name}'s {hit_location} comes away in a moment that ends as quietly as it began.",
                "victim_msg": "{attacker_name}'s one stroke, exactly placed. Your {hit_location} comes away.",
                "observer_msg": "{attacker_name}'s one stroke, exactly placed. {target_name}'s {hit_location} comes away in a moment that ends as quietly as it began.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into the ankle joint and *lever*. {target_name}'s {hit_location} pries loose with a wet pop and the body crumples forward.",
                "victim_msg": "{attacker_name} drives the point into your ankle joint and *levers*. Your {hit_location} pries loose with a wet pop.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s ankle joint and *levers*. The {hit_location} pries loose with a wet pop and the body crumples forward.",
            },
            {
                "attacker_msg": "Your thrust tears through the joint capsule. {target_name}'s {hit_location} comes loose in a wet, brutal moment, ligaments dangling.",
                "victim_msg": "{attacker_name}'s thrust tears through your joint capsule. Your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s thrust tears through the joint capsule. {target_name}'s {hit_location} comes loose in a wet, brutal moment, ligaments dangling.",
            },
            {
                "attacker_msg": "The point goes deep and levers outward. {target_name}'s {hit_location} tears free at the ankle, the wound a ragged ruin.",
                "victim_msg": "{attacker_name}'s point goes deep and levers outward. Your {hit_location} tears free at the ankle.",
                "observer_msg": "{attacker_name}'s point goes deep and levers outward. {target_name}'s {hit_location} tears free at the ankle, the wound a ragged ruin.",
            },
            {
                "attacker_msg": "You shove the blade into the heel and *grind*. The ankle disintegrates and {target_name}'s {hit_location} drops away in a spray of bone meal.",
                "victim_msg": "{attacker_name} shoves the blade into your heel and *grinds*. Your ankle disintegrates and your {hit_location} drops away.",
                "observer_msg": "{attacker_name} shoves the blade into {target_name}'s heel and *grinds*. The ankle disintegrates and the {hit_location} drops away in a spray of bone meal.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slips into the ankle joint with surgical precision and {target_name}'s {hit_location} separates from the leg in a single clean motion.",
                "victim_msg": "{attacker_name}'s point slips into your ankle joint with surgical precision and your {hit_location} separates from your leg.",
                "observer_msg": "{attacker_name}'s point slips into the ankle joint with surgical precision and {target_name}'s {hit_location} separates from the leg in a single clean motion.",
            },
            {
                "attacker_msg": "A precise thrust at the ankle and {target_name}'s {hit_location} comes loose. The body finds the floor.",
                "victim_msg": "{attacker_name}'s precise thrust at your ankle and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s precise thrust at the ankle and {target_name}'s {hit_location} comes loose. The body finds the floor.",
            },
            {
                "attacker_msg": "Your blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops away.",
                "victim_msg": "{attacker_name}'s blade finds your joint capsule and parts it without violence. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name}'s blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops away.",
            },
            {
                "attacker_msg": "The thrust is economical and exact. {target_name}'s {hit_location} comes free from the ankle with no fanfare.",
                "victim_msg": "{attacker_name}'s thrust is economical and exact. Your {hit_location} comes free from your ankle.",
                "observer_msg": "{attacker_name}'s thrust is economical and exact. {target_name}'s {hit_location} comes free from the ankle with no fanfare.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s ankle in a wet grinding chorus. The {hit_location} drops away in pieces, leaving the leg ending at a shredded stump.",
                "victim_msg": "Chain teeth chew through your ankle. Your {hit_location} drops away in pieces.",
                "observer_msg": "Chain teeth chew through {target_name}'s ankle in a wet grinding chorus. The {hit_location} drops away in pieces, leaving the leg ending at a shredded stump.",
            },
            {
                "attacker_msg": "You saw through {target_name}'s ankle and the metatarsals shatter. The {hit_location} comes apart in a slurry of bone and skin.",
                "victim_msg": "{attacker_name} saws through your ankle and your metatarsals shatter. Your {hit_location} comes apart.",
                "observer_msg": "{attacker_name} saws through {target_name}'s ankle and the metatarsals shatter. The {hit_location} comes apart in a slurry of bone and skin.",
            },
            {
                "attacker_msg": "Your blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood pooling instantly.",
                "victim_msg": "{attacker_name}'s blade catches and *grinds*. Your {hit_location} tears free.",
                "observer_msg": "{attacker_name}'s blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood pooling instantly.",
            },
            {
                "attacker_msg": "The chain rips through {target_name}'s ankle, dragging tendon and bone shards. The {hit_location} comes off ragged but undeniable.",
                "victim_msg": "{attacker_name}'s chain rips through your ankle. Your {hit_location} comes off ragged but undeniable.",
                "observer_msg": "{attacker_name}'s chain rips through {target_name}'s ankle, dragging tendon and bone shards. The {hit_location} comes off ragged but undeniable.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but the ankle is small. {target_name}'s {hit_location} parts from the leg in a moment that's more tear than slice.",
                "victim_msg": "{attacker_name}'s cut is rough but your ankle is small. Your {hit_location} parts from your leg.",
                "observer_msg": "{attacker_name}'s cut is rough but the ankle is small. {target_name}'s {hit_location} parts from the leg in a moment that's more tear than slice.",
            },
            {
                "attacker_msg": "Serrated edge bites through the ankle and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
                "victim_msg": "{attacker_name}'s serrated edge bites through your ankle and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s serrated edge bites through the ankle and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
            },
            {
                "attacker_msg": "You drag the blade through {target_name}'s ankle and the {hit_location} parts free, the cut ragged but the result clear.",
                "victim_msg": "{attacker_name} drags the blade through your ankle and your {hit_location} parts free.",
                "observer_msg": "{attacker_name} drags the blade through {target_name}'s ankle and the {hit_location} parts free, the cut ragged but the result clear.",
            },
            {
                "attacker_msg": "The tear is uneven but the metatarsals surrender. {target_name}'s {hit_location} drops away in a wash of red.",
                "victim_msg": "{attacker_name}'s tear is uneven but your metatarsals surrender. Your {hit_location} drops away.",
                "observer_msg": "{attacker_name}'s tear is uneven but the metatarsals surrender. {target_name}'s {hit_location} drops away in a wash of red.",
            },
        ],
    },
}
