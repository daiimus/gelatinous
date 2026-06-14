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


# Chrome bank (#525): the human CYBERNETIC_TAIL sheared at the spine
# mount.  Rats keep the organic MESSAGES above; the human tail is
# chrome-only, so its severance is a counterweight actuator going dead.
CHROME_MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade catches {target_name}'s {hit_location} at the spine mount and the chrome length whips loose, counterweight actuator dead, ringing off the floor.",
                "victim_msg": "{attacker_name}'s blade catches your {hit_location} at the spine mount. The chrome length whips loose, the counterweight gone dead, and rings off the floor.",
                "observer_msg": "{attacker_name}'s blade catches {target_name}'s {hit_location} at the spine mount and the chrome length whips loose, counterweight actuator dead, ringing off the floor.",
            },
            {
                "attacker_msg": "The cut shears the {hit_location} off at the base coupling. {target_name}'s body lurches as the dead counterweight clatters away in a fizz of sparks.",
                "victim_msg": "{attacker_name}'s cut shears your {hit_location} off at the base coupling. Your body lurches as the dead counterweight clatters away in a fizz of sparks.",
                "observer_msg": "The cut shears the {hit_location} off at the base coupling. {target_name}'s body lurches as the dead counterweight clatters away in a fizz of sparks.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A clean stroke parts the {hit_location} at the spine coupling and the dead chrome length drops away, neat as a part pulled for service.",
                "victim_msg": "{attacker_name}'s clean stroke parts your {hit_location} at the spine coupling and the dead chrome length drops away.",
                "observer_msg": "A clean stroke parts {target_name}'s {hit_location} at the spine coupling and the dead chrome length drops away, neat as a part pulled for service.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point into the {hit_location} base junction and twist; the coupling lets go and the dead chrome length sags off the spine mount.",
                "victim_msg": "{attacker_name} drives the point into your {hit_location} base junction and twists. The coupling lets go and the dead chrome length sags off the spine mount.",
                "observer_msg": "{attacker_name} drives the point into {target_name}'s {hit_location} base junction and twists; the coupling lets go and the dead chrome length sags off the spine mount.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "Your point finds the gap at the base and {target_name}'s {hit_location} pops loose from the spine mount, sliding free.",
                "victim_msg": "{attacker_name}'s point finds the gap at your base and your {hit_location} pops loose from the spine mount, sliding free.",
                "observer_msg": "{attacker_name}'s point finds the gap at the base and {target_name}'s {hit_location} pops loose from the spine mount, sliding free.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "You saw through the base until the last cable parts; {target_name}'s {hit_location} swings free on a thread of wire and falls, sparking.",
                "victim_msg": "{attacker_name} saws through your base until the last cable parts; your {hit_location} swings free on a thread of wire and falls, sparking.",
                "observer_msg": "{attacker_name} saws through the base until the last cable parts; {target_name}'s {hit_location} swings free on a thread of wire and falls, sparking.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "A short, tearing stroke severs the {hit_location} cable bundle at the base and the dead chrome length sags away.",
                "victim_msg": "{attacker_name}'s tearing stroke severs your {hit_location} cable bundle at the base and the dead chrome length sags away.",
                "observer_msg": "A short, tearing stroke severs {target_name}'s {hit_location} cable bundle at the base and the dead chrome length sags away.",
            },
        ],
    },
}
