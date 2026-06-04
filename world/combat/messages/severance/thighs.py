"""Thigh severance templates — left or right thigh detached at the hip.

Fires when an edged hit destroys a left_thigh or right_thigh femur. The
``{hit_location}`` kwarg resolves to ``"left thigh"`` or ``"right thigh"``.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade cleaves {target_name}'s {hit_location} from the hip in a sweeping arc. The leg crashes to the deck and the body topples after it in a slow, terrible cascade.",
                "victim_msg": "{attacker_name}'s blade cleaves your {hit_location} from your hip in a sweeping arc. Your leg crashes to the deck and you topple after it.",
                "observer_msg": "{attacker_name}'s blade cleaves {target_name}'s {hit_location} from the hip in a sweeping arc. The leg crashes to the deck and the body topples after it in a slow, terrible cascade.",
            },
            {
                "attacker_msg": "The femur parts under your edge with a deep crack. {target_name}'s {hit_location} comes away in a fountain of arterial red, and they go down before they can scream.",
                "victim_msg": "Your femur parts under {attacker_name}'s edge with a deep crack. Your {hit_location} comes away in a fountain of arterial red.",
                "observer_msg": "{target_name}'s femur parts under {attacker_name}'s edge with a deep crack. The {hit_location} comes away in a fountain of arterial red, and they go down before they can scream.",
            },
            {
                "attacker_msg": "Your chop catches at the hip joint and continues through. {target_name}'s {hit_location} cartwheels free, blood arcing high in a final salute.",
                "victim_msg": "{attacker_name}'s chop catches at your hip joint and continues through. Your {hit_location} cartwheels free.",
                "observer_msg": "{attacker_name}'s chop catches at {target_name}'s hip joint and continues through. The {hit_location} cartwheels free, blood arcing high in a final salute.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off above the knee in a single hard stroke. The leg falls, the body collapses, and the deck is suddenly very red.",
                "victim_msg": "{attacker_name} takes your {hit_location} off above the knee in a single hard stroke. Your leg falls, your body collapses.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off above the knee in a single hard stroke. The leg falls, the body collapses, and the deck is suddenly very red.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A surgical stroke at the hip joint and {target_name}'s {hit_location} separates from the body with almost no fuss.",
                "victim_msg": "{attacker_name}'s surgical stroke at your hip joint and your {hit_location} separates from your body with almost no fuss.",
                "observer_msg": "{attacker_name}'s surgical stroke at the hip joint and {target_name}'s {hit_location} separates from the body with almost no fuss.",
            },
            {
                "attacker_msg": "The edge finds the joint capsule and parts it cleanly. {target_name}'s {hit_location} settles to the deck with the soft weight of an offering.",
                "victim_msg": "{attacker_name}'s edge finds your joint capsule and parts it cleanly. Your {hit_location} settles to the deck.",
                "observer_msg": "{attacker_name}'s edge finds the joint capsule and parts it cleanly. {target_name}'s {hit_location} settles to the deck with the soft weight of an offering.",
            },
            {
                "attacker_msg": "Your blade passes through the femoral neck without complaint. {target_name}'s {hit_location} comes free, the cut so neat it could be admired.",
                "victim_msg": "{attacker_name}'s blade passes through your femoral neck without complaint. Your {hit_location} comes free.",
                "observer_msg": "{attacker_name}'s blade passes through the femoral neck without complaint. {target_name}'s {hit_location} comes free, the cut so neat it could be admired.",
            },
            {
                "attacker_msg": "One stroke, exactly placed. {target_name}'s {hit_location} falls away and the body kneels rather than collapsing.",
                "victim_msg": "{attacker_name}'s one stroke, exactly placed. Your {hit_location} falls away.",
                "observer_msg": "{attacker_name}'s one stroke, exactly placed. {target_name}'s {hit_location} falls away and the body kneels rather than collapsing.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into the hip joint and *lever*. {target_name}'s {hit_location} pries loose with a wet crack and the body folds sideways.",
                "victim_msg": "{attacker_name} drives the point into your hip joint and *levers*. Your {hit_location} pries loose with a wet crack.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s hip joint and *levers*. The {hit_location} pries loose with a wet crack and the body folds sideways.",
            },
            {
                "attacker_msg": "Your thrust tears through the femoral head. {target_name}'s {hit_location} hangs by tendons for a moment, then falls away in a spray of red.",
                "victim_msg": "{attacker_name}'s thrust tears through your femoral head. Your {hit_location} hangs by tendons for a moment, then falls.",
                "observer_msg": "{attacker_name}'s thrust tears through {target_name}'s femoral head. The {hit_location} hangs by tendons for a moment, then falls away in a spray of red.",
            },
            {
                "attacker_msg": "The point goes deep and rips through the joint capsule. {target_name}'s {hit_location} tears free, the wound a brutal ruin where the hip used to be.",
                "victim_msg": "{attacker_name}'s point goes deep and rips through your joint capsule. Your {hit_location} tears free.",
                "observer_msg": "{attacker_name}'s point goes deep and rips through the joint capsule. {target_name}'s {hit_location} tears free, the wound a brutal ruin where the hip used to be.",
            },
            {
                "attacker_msg": "You shove the blade in and *grind*. The femur snaps at the neck and {target_name}'s {hit_location} comes away dragging shreds of muscle.",
                "victim_msg": "{attacker_name} shoves the blade in and *grinds*. Your femur snaps at the neck and your {hit_location} comes away.",
                "observer_msg": "{attacker_name} shoves the blade in and *grinds*. {target_name}'s femur snaps at the neck and the {hit_location} comes away dragging shreds of muscle.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slips into the joint with surgical precision and {target_name}'s {hit_location} separates from the body in a single clean motion.",
                "victim_msg": "{attacker_name}'s point slips into your joint with surgical precision and your {hit_location} separates from your body.",
                "observer_msg": "{attacker_name}'s point slips into the joint with surgical precision and {target_name}'s {hit_location} separates from the body in a single clean motion.",
            },
            {
                "attacker_msg": "A precise thrust at the hip and {target_name}'s {hit_location} comes loose, the body finding the floor with surprising grace.",
                "victim_msg": "{attacker_name}'s precise thrust at your hip and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s precise thrust at the hip and {target_name}'s {hit_location} comes loose, the body finding the floor with surprising grace.",
            },
            {
                "attacker_msg": "Your blade finds the joint capsule and parts it without struggle. {target_name}'s {hit_location} drops free.",
                "victim_msg": "{attacker_name}'s blade finds your joint capsule and parts it without struggle. Your {hit_location} drops free.",
                "observer_msg": "{attacker_name}'s blade finds the joint capsule and parts it without struggle. {target_name}'s {hit_location} drops free.",
            },
            {
                "attacker_msg": "The thrust is economical. {target_name}'s {hit_location} comes away from the hip with no fanfare and no waste.",
                "victim_msg": "{attacker_name}'s thrust is economical. Your {hit_location} comes away from your hip with no fanfare.",
                "observer_msg": "{attacker_name}'s thrust is economical. {target_name}'s {hit_location} comes away from the hip with no fanfare and no waste.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s {hit_location} in a wet mechanical chorus. Bone fragments scatter, the leg falls, and the body topples after it.",
                "victim_msg": "Chain teeth chew through your {hit_location} in a wet mechanical chorus. Your leg falls, your body topples.",
                "observer_msg": "Chain teeth chew through {target_name}'s {hit_location} in a wet mechanical chorus. Bone fragments scatter, the leg falls, and the body topples after it.",
            },
            {
                "attacker_msg": "You saw through {target_name}'s thigh and the femur splinters under the chain. The {hit_location} comes apart in a slurry of muscle and bone meal.",
                "victim_msg": "{attacker_name} saws through your thigh and your femur splinters under the chain. Your {hit_location} comes apart.",
                "observer_msg": "{attacker_name} saws through {target_name}'s thigh and the femur splinters under the chain. The {hit_location} comes apart in a slurry of muscle and bone meal.",
            },
            {
                "attacker_msg": "Your blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood flooding the deck around them.",
                "victim_msg": "{attacker_name}'s blade catches and *grinds*. Your {hit_location} tears free in a ragged moment.",
                "observer_msg": "{attacker_name}'s blade catches and *grinds*. {target_name}'s {hit_location} tears free in a ragged moment, blood flooding the deck around them.",
            },
            {
                "attacker_msg": "The chain rips through {target_name}'s thigh, dragging cloth and skin and muscle. The {hit_location} comes off in pieces — but it comes off.",
                "victim_msg": "{attacker_name}'s chain rips through your thigh, dragging cloth and skin and muscle. Your {hit_location} comes off in pieces.",
                "observer_msg": "{attacker_name}'s chain rips through {target_name}'s thigh, dragging cloth and skin and muscle. The {hit_location} comes off in pieces — but it comes off.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but the femur is brittle. {target_name}'s {hit_location} parts from the hip in a moment that's more tear than slice.",
                "victim_msg": "{attacker_name}'s cut is rough but the femur is brittle. Your {hit_location} parts from your hip in a moment that's more tear than slice.",
                "observer_msg": "{attacker_name}'s cut is rough but the femur is brittle. {target_name}'s {hit_location} parts from the hip in a moment that's more tear than slice.",
            },
            {
                "attacker_msg": "Serrated edge bites through the thigh and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
                "victim_msg": "{attacker_name}'s serrated edge bites through your thigh and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s serrated edge bites through the thigh and {target_name}'s {hit_location} comes loose with a wet, tearing sound.",
            },
            {
                "attacker_msg": "You drag the blade through {target_name}'s thigh and the {hit_location} parts free, the cut ragged but the result undeniable.",
                "victim_msg": "{attacker_name} drags the blade through your thigh and your {hit_location} parts free.",
                "observer_msg": "{attacker_name} drags the blade through {target_name}'s thigh and the {hit_location} parts free, the cut ragged but the result undeniable.",
            },
            {
                "attacker_msg": "The tear is uneven but the femur gives. {target_name}'s {hit_location} drops away in a wash of red.",
                "victim_msg": "{attacker_name}'s tear is uneven but your femur gives. Your {hit_location} drops away in a wash of red.",
                "observer_msg": "{attacker_name}'s tear is uneven but the femur gives. {target_name}'s {hit_location} drops away in a wash of red.",
            },
        ],
    },
}
