"""Arm severance templates — left or right arm detached at the shoulder.

Fires when an edged hit destroys a left_arm or right_arm humerus. The
``{hit_location}`` kwarg resolves to ``"left arm"`` or ``"right arm"``.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade cleaves {target_name}'s {hit_location} from the shoulder in a single arc. The limb spins to the floor before they have time to look down.",
                "victim_msg": "{attacker_name}'s blade cleaves your {hit_location} from your shoulder in a single arc. The limb hits the floor before you have time to look down.",
                "observer_msg": "{attacker_name}'s blade cleaves {target_name}'s {hit_location} from the shoulder in a single arc. The limb spins to the floor before they have time to look down.",
            },
            {
                "attacker_msg": "Bone parts under the edge with a crunch you feel in your wrist. {target_name}'s {hit_location} detaches and falls, blood arcing from the open socket.",
                "victim_msg": "Bone parts under {attacker_name}'s edge with a crunch you feel through your whole body. Your {hit_location} detaches and falls.",
                "observer_msg": "Bone parts under {attacker_name}'s edge with a crunch. {target_name}'s {hit_location} detaches and falls, blood arcing from the open socket.",
            },
            {
                "attacker_msg": "The chop is too hard, too low. {target_name}'s {hit_location} cartwheels away in a spray of red, fingers still twitching for a weapon that isn't there.",
                "victim_msg": "The chop is too hard, too low. Your {hit_location} cartwheels away in a spray of red, fingers still twitching.",
                "observer_msg": "{attacker_name}'s chop is too hard, too low. {target_name}'s {hit_location} cartwheels away in a spray of red, fingers still twitching for a weapon that isn't there.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off at the joint and the limb goes one way while the body lurches the other, balance lost between heartbeats.",
                "victim_msg": "{attacker_name} takes your {hit_location} off at the joint and the limb goes one way while your body lurches the other.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off at the joint and the limb goes one way while the body lurches the other, balance lost between heartbeats.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A single clean stroke separates {target_name}'s {hit_location} from the shoulder. The cut is so neat the limb almost looks placed.",
                "victim_msg": "{attacker_name}'s single clean stroke separates your {hit_location} from your shoulder. The cut is so neat the limb almost looks placed.",
                "observer_msg": "{attacker_name}'s single clean stroke separates {target_name}'s {hit_location} from the shoulder. The cut is so neat the limb almost looks placed.",
            },
            {
                "attacker_msg": "The edge finds the gap between bones and {target_name}'s {hit_location} falls free as if it were never properly attached.",
                "victim_msg": "{attacker_name}'s edge finds the gap between bones and your {hit_location} falls free.",
                "observer_msg": "{attacker_name}'s edge finds the gap between bones and {target_name}'s {hit_location} falls free as if it were never properly attached.",
            },
            {
                "attacker_msg": "Your blade passes through {target_name}'s shoulder with almost no resistance. The {hit_location} settles to the floor with a soft, final thud.",
                "victim_msg": "{attacker_name}'s blade passes through your shoulder with almost no resistance. Your {hit_location} settles to the floor with a soft, final thud.",
                "observer_msg": "{attacker_name}'s blade passes through {target_name}'s shoulder with almost no resistance. The {hit_location} settles to the floor with a soft, final thud.",
            },
            {
                "attacker_msg": "One stroke, surgically placed. {target_name}'s {hit_location} comes away with no struggle, no flourish — only the small surprise on their face.",
                "victim_msg": "One stroke, surgically placed. Your {hit_location} comes away with no struggle.",
                "observer_msg": "{attacker_name}'s single surgical stroke takes {target_name}'s {hit_location} away with no struggle, no flourish — only the small surprise on their face.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point under {target_name}'s armpit and lever. The {hit_location} tears free at the joint, ligaments snapping like wet rope.",
                "victim_msg": "{attacker_name} drives the point under your armpit and levers. Your {hit_location} tears free at the joint.",
                "observer_msg": "{attacker_name} drives the point under {target_name}'s armpit and levers. The {hit_location} tears free at the joint, ligaments snapping like wet rope.",
            },
            {
                "attacker_msg": "The thrust goes deep and pries the joint apart. {target_name}'s {hit_location} comes loose in a mess of strained sinew and bright arterial spray.",
                "victim_msg": "{attacker_name}'s thrust goes deep and pries your joint apart. Your {hit_location} comes loose in a mess of strained sinew.",
                "observer_msg": "{attacker_name}'s thrust goes deep and pries the joint apart. {target_name}'s {hit_location} comes loose in a mess of strained sinew and bright arterial spray.",
            },
            {
                "attacker_msg": "Your point catches under the ball of the shoulder and rips. {target_name}'s {hit_location} pulls free, dragging ribbons of tissue behind it.",
                "victim_msg": "{attacker_name}'s point catches under the ball of your shoulder and rips. Your {hit_location} pulls free.",
                "observer_msg": "{attacker_name}'s point catches under the ball of {target_name}'s shoulder and rips. The {hit_location} pulls free, dragging ribbons of tissue.",
            },
            {
                "attacker_msg": "You shove the blade in and twist until the shoulder gives. {target_name}'s {hit_location} comes off with a wet crack that echoes off the walls.",
                "victim_msg": "{attacker_name} shoves the blade in and twists until your shoulder gives. Your {hit_location} comes off with a wet crack.",
                "observer_msg": "{attacker_name} shoves the blade in and twists until {target_name}'s shoulder gives. The {hit_location} comes off with a wet crack that echoes off the walls.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slides between bones at the precise angle and {target_name}'s {hit_location} simply detaches, as if it had been waiting for permission.",
                "victim_msg": "{attacker_name}'s point slides between your bones at the precise angle and your {hit_location} simply detaches.",
                "observer_msg": "{attacker_name}'s point slides between bones at the precise angle and {target_name}'s {hit_location} simply detaches, as if it had been waiting for permission.",
            },
            {
                "attacker_msg": "A clean puncture at the joint and {target_name}'s {hit_location} comes free in a single deliberate motion.",
                "victim_msg": "{attacker_name}'s clean puncture at your joint and your {hit_location} comes free in a single deliberate motion.",
                "observer_msg": "{attacker_name}'s clean puncture at the joint and {target_name}'s {hit_location} comes free in a single deliberate motion.",
            },
            {
                "attacker_msg": "Your blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops to the floor with no fanfare.",
                "victim_msg": "{attacker_name}'s blade finds your joint capsule and parts it without violence. Your {hit_location} drops to the floor.",
                "observer_msg": "{attacker_name}'s blade finds the joint capsule and parts it without violence. {target_name}'s {hit_location} drops to the floor with no fanfare.",
            },
            {
                "attacker_msg": "The thrust is precise and economical. {target_name}'s {hit_location} parts from the body the way pages turn in a book.",
                "victim_msg": "{attacker_name}'s thrust is precise and economical. Your {hit_location} parts from your body the way pages turn in a book.",
                "observer_msg": "{attacker_name}'s thrust is precise and economical. {target_name}'s {hit_location} parts from the body the way pages turn in a book.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "The blade grinds through {target_name}'s shoulder in a chorus of breaking bone. The {hit_location} comes free in a single ragged moment, hand still gripping at empty air.",
                "victim_msg": "{attacker_name}'s blade grinds through your shoulder in a chorus of breaking bone. Your {hit_location} comes free in a single ragged moment.",
                "observer_msg": "{attacker_name}'s blade grinds through {target_name}'s shoulder in a chorus of breaking bone. The {hit_location} comes free in a single ragged moment, hand still gripping at empty air.",
            },
            {
                "attacker_msg": "You saw, tear, and *finish*. {target_name}'s {hit_location} comes apart in a slurry of red and gristle, the bone end ragged where it tore.",
                "victim_msg": "{attacker_name} saws, tears, and *finishes*. Your {hit_location} comes apart in a slurry of red and gristle.",
                "observer_msg": "{attacker_name} saws, tears, and *finishes*. {target_name}'s {hit_location} comes apart in a slurry of red and gristle, the bone end ragged where it tore.",
            },
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s shoulder until the {hit_location} drops away, the wound a mess of pulped muscle and shredded skin.",
                "victim_msg": "Chain teeth chew through your shoulder until the {hit_location} drops away.",
                "observer_msg": "Chain teeth chew through {target_name}'s shoulder until the {hit_location} drops away, the wound a mess of pulped muscle and shredded skin.",
            },
            {
                "attacker_msg": "The edge catches and you *pull*. Tendons part with audible snaps, and {target_name}'s {hit_location} tears free, splashing the deck behind it.",
                "victim_msg": "{attacker_name}'s edge catches and they *pull*. Tendons part with audible snaps, and your {hit_location} tears free.",
                "observer_msg": "{attacker_name}'s edge catches and they *pull*. Tendons part with audible snaps, and {target_name}'s {hit_location} tears free, splashing the deck behind it.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but the arm is small. {target_name}'s {hit_location} parts from the shoulder in a moment that's more tear than slice.",
                "victim_msg": "{attacker_name}'s cut is rough but the arm is small. Your {hit_location} parts from your shoulder in a moment that's more tear than slice.",
                "observer_msg": "{attacker_name}'s cut is rough but the arm is small. {target_name}'s {hit_location} parts from the shoulder in a moment that's more tear than slice.",
            },
            {
                "attacker_msg": "Serrated edge bites once, twice, and {target_name}'s {hit_location} comes loose with a sound like wet canvas tearing.",
                "victim_msg": "{attacker_name}'s serrated edge bites once, twice, and your {hit_location} comes loose.",
                "observer_msg": "{attacker_name}'s serrated edge bites once, twice, and {target_name}'s {hit_location} comes loose with a sound like wet canvas tearing.",
            },
            {
                "attacker_msg": "You drag the blade through {target_name}'s shoulder and the {hit_location} parts free, the wound ragged but the result unambiguous.",
                "victim_msg": "{attacker_name} drags the blade through your shoulder and your {hit_location} parts free.",
                "observer_msg": "{attacker_name} drags the blade through {target_name}'s shoulder and the {hit_location} parts free, the wound ragged but the result unambiguous.",
            },
            {
                "attacker_msg": "The tear is uneven, but {target_name}'s {hit_location} drops to the floor anyway, blood already pooling.",
                "victim_msg": "{attacker_name}'s tear is uneven, but your {hit_location} drops to the floor anyway.",
                "observer_msg": "{attacker_name}'s tear is uneven, but {target_name}'s {hit_location} drops to the floor anyway, blood already pooling.",
            },
        ],
    },
}


# Chrome bank (#525): a CYBER_ARM sheared at the shoulder mount.  No
# blood — sheared actuator column, snapped cable looms, dead alloy.
CHROME_MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade shears through {target_name}'s {hit_location} at the shoulder mount. The chrome limb drops dead-weight, cable looms whipping loose, and clangs off the floor.",
                "victim_msg": "{attacker_name}'s blade shears through your {hit_location} at the shoulder mount. The arm goes dead and drops away, cables snapping loose.",
                "observer_msg": "{attacker_name}'s blade shears through {target_name}'s {hit_location} at the shoulder mount. The chrome limb drops dead-weight, cable looms whipping loose, and clangs off the floor.",
            },
            {
                "attacker_msg": "The edge bites into the actuator column with a shriek. {target_name}'s {hit_location} tears off at the shoulder, sparks fizzing from the stripped coupling.",
                "victim_msg": "The edge bites into your {hit_location} actuator column with a shriek. The arm tears off at the shoulder, sparks fizzing from the stripped coupling.",
                "observer_msg": "The edge bites into the actuator column with a shriek. {target_name}'s {hit_location} tears off at the shoulder, sparks fizzing from the stripped coupling.",
            },
            {
                "attacker_msg": "You take {target_name}'s {hit_location} off at the shoulder seam and the dead chrome goes one way while the body lurches the other, balance lost to the missing weight.",
                "victim_msg": "{attacker_name} takes your {hit_location} off at the shoulder seam. The dead chrome goes one way while your body lurches the other.",
                "observer_msg": "{attacker_name} takes {target_name}'s {hit_location} off at the shoulder seam and the dead chrome goes one way while the body lurches the other, balance lost to the missing weight.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A clean stroke parts {target_name}'s {hit_location} at the shoulder coupling. The arm detaches almost gently, hardware gone dark.",
                "victim_msg": "{attacker_name}'s clean stroke parts your {hit_location} at the shoulder coupling. The arm detaches almost gently, hardware gone dark.",
                "observer_msg": "A clean stroke parts {target_name}'s {hit_location} at the shoulder coupling. The arm detaches almost gently, hardware gone dark.",
            },
            {
                "attacker_msg": "Your blade slips through the shoulder joint and {target_name}'s {hit_location} drops free, neat as a part pulled for service.",
                "victim_msg": "{attacker_name}'s blade slips through the joint and your {hit_location} drops free, neat as a part pulled for service.",
                "observer_msg": "{attacker_name}'s blade slips through the shoulder joint and {target_name}'s {hit_location} drops free, neat as a part pulled for service.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into {target_name}'s shoulder junction and twist; the {hit_location} coupling lets go and the dead arm sags off its mounts.",
                "victim_msg": "{attacker_name} drives the point into your shoulder junction and twists. The {hit_location} coupling lets go and the dead arm sags off its mounts.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s shoulder junction and twists; the {hit_location} coupling lets go and the dead arm sags off its mounts.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "Your point finds the gap between shoulder plates and {target_name}'s {hit_location} pops loose, sliding off its frame.",
                "victim_msg": "{attacker_name}'s point finds the gap between your shoulder plates and your {hit_location} pops loose, sliding off its frame.",
                "observer_msg": "{attacker_name}'s point finds the gap between shoulder plates and {target_name}'s {hit_location} pops loose, sliding off its frame.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "You saw the edge through the shoulder until the last cable parts. {target_name}'s {hit_location} swings free on a thread of wire, then falls, sparking.",
                "victim_msg": "{attacker_name} saws the edge through your shoulder until the last cable parts. Your {hit_location} swings free on a thread of wire, then falls, sparking.",
                "observer_msg": "{attacker_name} saws the edge through the shoulder until the last cable parts. {target_name}'s {hit_location} swings free on a thread of wire, then falls, sparking.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A short, tearing stroke severs the {hit_location} cable bundle at the shoulder and the dead arm sags away.",
                "victim_msg": "{attacker_name}'s tearing stroke severs your {hit_location} cable bundle at the shoulder and the dead arm sags away.",
                "observer_msg": "A short, tearing stroke severs {target_name}'s {hit_location} cable bundle at the shoulder and the dead arm sags away.",
            },
        ],
    },
}
