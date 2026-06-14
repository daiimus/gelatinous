"""Generic chrome-limb severance templates (#525).

The catch-all bank for any PROSTHETIC limb whose location hasn't been
given a bespoke ``CHROME_MESSAGES`` cell yet.  Selected when
``get_severance_message(..., material="chrome")`` finds no per-location
chrome prose; ``{hit_location}`` fills in whichever part came off.

Chrome doesn't bleed — it shears.  Prose here trades the spray of red
for sheared actuators, snapped cable looms, a hiss of coolant, and the
dead-weight clatter of alloy hitting the floor.  Per-location modules
(``arms``, ``hands``, ``tail``, ...) override with limb-specific
hardware; this is the floor everything falls back to.

See ``world/combat/messages/severance/__init__.py`` for the loader.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your edge shears clean through the {hit_location} coupling. {target_name}'s limb drops dead-weight, cable looms whipping loose, and clatters to the floor in a hiss of coolant.",
                "victim_msg": "{attacker_name}'s edge shears through your {hit_location} coupling. The limb goes dead and drops away, cables snapping loose with a hiss of coolant.",
                "observer_msg": "{attacker_name}'s edge shears through {target_name}'s {hit_location} coupling. The limb drops dead-weight, cable looms whipping loose, and clatters to the floor in a hiss of coolant.",
            },
            {
                "attacker_msg": "Alloy parts with a shriek under your blade. {target_name}'s {hit_location} tears free, sparks fizzing from the stub where the servos used to run.",
                "victim_msg": "Your {hit_location} parts with a shriek of metal. It tears free and falls, sparks fizzing from the stub.",
                "observer_msg": "Alloy parts with a shriek under {attacker_name}'s blade. {target_name}'s {hit_location} tears free, sparks fizzing from the stub where the servos used to run.",
            },
            {
                "attacker_msg": "The cut finds the seam in the chassis and {target_name}'s {hit_location} comes away whole, a length of dead chrome trailing severed hydraulic line.",
                "victim_msg": "{attacker_name}'s cut finds the seam in the chassis. Your {hit_location} comes away whole, dead chrome trailing severed hydraulic line.",
                "observer_msg": "{attacker_name}'s cut finds the seam in the chassis and {target_name}'s {hit_location} comes away whole, a length of dead chrome trailing severed hydraulic line.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A single clean stroke parts the {hit_location} mounting bolts. {target_name}'s limb detaches almost gently, hardware gone dark.",
                "victim_msg": "{attacker_name}'s clean stroke parts your {hit_location} mounting. The limb detaches almost gently, hardware gone dark.",
                "observer_msg": "A single clean stroke parts {target_name}'s {hit_location} mounting bolts. The limb detaches almost gently, hardware gone dark.",
            },
            {
                "attacker_msg": "Your blade slips through the actuator joint and {target_name}'s {hit_location} drops free, neat as a part pulled for service.",
                "victim_msg": "{attacker_name}'s blade slips through the joint and your {hit_location} drops free, neat as a part pulled for service.",
                "observer_msg": "{attacker_name}'s blade slips through the actuator joint and {target_name}'s {hit_location} drops free, neat as a part pulled for service.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into the {hit_location} junction and twist; the coupling lets go and the limb sags off its mounts, dead and heavy.",
                "victim_msg": "{attacker_name} drives the point into your {hit_location} junction and twists. The coupling lets go and the limb sags off its mounts, dead and heavy.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s {hit_location} junction and twists; the coupling lets go and the limb sags off its mounts, dead and heavy.",
            },
            {
                "attacker_msg": "The thrust punches clean through the chassis seam. {target_name}'s {hit_location} shudders, servos screaming, then drops in a spray of sparks.",
                "victim_msg": "The thrust punches through your {hit_location} seam. The limb shudders, servos screaming, then drops in a spray of sparks.",
                "observer_msg": "{attacker_name}'s thrust punches clean through the chassis seam. {target_name}'s {hit_location} shudders, servos screaming, then drops in a spray of sparks.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "Your point finds the gap between plates and the {hit_location} coupling pops loose; the limb slides off its frame and clatters down.",
                "victim_msg": "{attacker_name}'s point finds the gap and your {hit_location} coupling pops loose; the limb slides off its frame and clatters down.",
                "observer_msg": "{attacker_name}'s point finds the gap between plates and {target_name}'s {hit_location} coupling pops loose; the limb slides off its frame and clatters down.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "You saw the edge back and forth until the last cable parts. {target_name}'s {hit_location} swings free on a thread of wire, then falls, sparking.",
                "victim_msg": "{attacker_name} saws the edge back and forth until the last cable parts. Your {hit_location} swings free on a thread of wire, then falls, sparking.",
                "observer_msg": "{attacker_name} saws the edge back and forth until the last cable parts. {target_name}'s {hit_location} swings free on a thread of wire, then falls, sparking.",
            },
            {
                "attacker_msg": "The ragged cut tears the chassis open and chews through the wiring. {target_name}'s {hit_location} comes off in a grind of stripped alloy.",
                "victim_msg": "The ragged cut tears your {hit_location} chassis open and chews through the wiring. It comes off in a grind of stripped alloy.",
                "observer_msg": "{attacker_name}'s ragged cut tears the chassis open and chews through the wiring. {target_name}'s {hit_location} comes off in a grind of stripped alloy.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A short, tearing stroke severs the {hit_location} cable bundle and the limb sags away, dark and inert.",
                "victim_msg": "{attacker_name}'s tearing stroke severs your {hit_location} cable bundle and the limb sags away, dark and inert.",
                "observer_msg": "A short, tearing stroke severs {target_name}'s {hit_location} cable bundle and the limb sags away, dark and inert.",
            },
        ],
    },
}
