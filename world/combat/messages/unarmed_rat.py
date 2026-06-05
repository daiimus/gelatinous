"""Rat unarmed combat messages (issue #356 follow-up).

Loaded by :func:`world.combat.messages.get_combat_message` when the
attacker's species is ``"rat"`` and the weapon_type is ``"unarmed"``.
Falls back to the human-anchored ``unarmed.py`` if any phase is
missing here, so we don't have to author every phase to ship a
species variant.

Vocabulary: chittering, lunging, biting at heels, scrabbling claws,
tail-whips, climbing the target.  Reads as a small rat in combat,
not a humanoid with fists.
"""

MESSAGES = {
    "initiate": [
        {
            "attacker_msg": "You bare your incisors and chitter at {target_name}.",
            "victim_msg": "{attacker_name} bares its incisors and chitters at you.",
            "observer_msg": "{attacker_name} bares its incisors and chitters at {target_name}.",
        },
        {
            "attacker_msg": "You rear up on your hindlegs, whiskers twitching, and watch {target_name}.",
            "victim_msg": "{attacker_name} rears up on its hindlegs, whiskers twitching, watching you.",
            "observer_msg": "{attacker_name} rears up on its hindlegs, whiskers twitching, watching {target_name}.",
        },
        {
            "attacker_msg": "Your tail lashes once across the ground as you fix on {target_name}.",
            "victim_msg": "{attacker_name}'s tail lashes once across the ground as it fixes on you.",
            "observer_msg": "{attacker_name}'s tail lashes once across the ground as it fixes on {target_name}.",
        },
        {
            "attacker_msg": "You flatten your ears and let out a thin, angry squeak at {target_name}.",
            "victim_msg": "{attacker_name} flattens its ears and lets out a thin, angry squeak at you.",
            "observer_msg": "{attacker_name} flattens its ears and lets out a thin, angry squeak at {target_name}.",
        },
        {
            "attacker_msg": "You scurry in a tight circle around {target_name}, claws ticking on the ground.",
            "victim_msg": "{attacker_name} scurries in a tight circle around you, claws ticking on the ground.",
            "observer_msg": "{attacker_name} scurries in a tight circle around {target_name}, claws ticking on the ground.",
        },
        {
            "attacker_msg": "You arch your back and bristle, fur standing on end as you face {target_name}.",
            "victim_msg": "{attacker_name} arches its back and bristles, fur standing on end as it faces you.",
            "observer_msg": "{attacker_name} arches its back and bristles, fur standing on end as it faces {target_name}.",
        },
        {
            "attacker_msg": "You crouch low, haunches gathering, and lock onto {target_name}.",
            "victim_msg": "{attacker_name} crouches low, haunches gathering, and locks onto you.",
            "observer_msg": "{attacker_name} crouches low, haunches gathering, and locks onto {target_name}.",
        },
        {
            "attacker_msg": "Your nose twitches twice and you dart sideways, sizing up {target_name}.",
            "victim_msg": "{attacker_name}'s nose twitches twice and it darts sideways, sizing you up.",
            "observer_msg": "{attacker_name}'s nose twitches twice and it darts sideways, sizing up {target_name}.",
        },
    ],
    "hit": [
        {
            "attacker_msg": "You sink your incisors into {target_name}'s {hit_location} and tear.",
            "victim_msg": "{attacker_name} sinks its incisors into your {hit_location} and tears.",
            "observer_msg": "{attacker_name} sinks its incisors into {target_name}'s {hit_location} and tears.",
        },
        {
            "attacker_msg": "Your claws rake across {target_name}'s {hit_location}, leaving four thin streaks of red.",
            "victim_msg": "{attacker_name}'s claws rake across your {hit_location}, leaving four thin streaks of red.",
            "observer_msg": "{attacker_name}'s claws rake across {target_name}'s {hit_location}, leaving four thin streaks of red.",
        },
        {
            "attacker_msg": "You lunge and snap at {target_name}'s {hit_location}, jaws clamping shut on flesh.",
            "victim_msg": "{attacker_name} lunges and snaps at your {hit_location}, jaws clamping shut on flesh.",
            "observer_msg": "{attacker_name} lunges and snaps at {target_name}'s {hit_location}, jaws clamping shut on flesh.",
        },
        {
            "attacker_msg": "Your tail whips around and cracks against {target_name}'s {hit_location}.",
            "victim_msg": "{attacker_name}'s tail whips around and cracks against your {hit_location}.",
            "observer_msg": "{attacker_name}'s tail whips around and cracks against {target_name}'s {hit_location}.",
        },
        {
            "attacker_msg": "You scrabble up onto {target_name}'s {hit_location}, claws sinking in for purchase.",
            "victim_msg": "{attacker_name} scrabbles up onto your {hit_location}, claws sinking in for purchase.",
            "observer_msg": "{attacker_name} scrabbles up onto {target_name}'s {hit_location}, claws sinking in for purchase.",
        },
        {
            "attacker_msg": "Your forepaws scratch furiously at {target_name}'s {hit_location}.",
            "victim_msg": "{attacker_name}'s forepaws scratch furiously at your {hit_location}.",
            "observer_msg": "{attacker_name}'s forepaws scratch furiously at {target_name}'s {hit_location}.",
        },
        {
            "attacker_msg": "You worry at {target_name}'s {hit_location} with quick, vicious bites.",
            "victim_msg": "{attacker_name} worries at your {hit_location} with quick, vicious bites.",
            "observer_msg": "{attacker_name} worries at {target_name}'s {hit_location} with quick, vicious bites.",
        },
        {
            "attacker_msg": "You dart in, nip {target_name}'s {hit_location}, and skitter back out of reach.",
            "victim_msg": "{attacker_name} darts in, nips your {hit_location}, and skitters back out of reach.",
            "observer_msg": "{attacker_name} darts in, nips {target_name}'s {hit_location}, and skitters back out of reach.",
        },
        {
            "attacker_msg": "Your incisors find {target_name}'s {hit_location} and grind through the flesh.",
            "victim_msg": "{attacker_name}'s incisors find your {hit_location} and grind through the flesh.",
            "observer_msg": "{attacker_name}'s incisors find {target_name}'s {hit_location} and grind through the flesh.",
        },
        {
            "attacker_msg": "You launch off your hindlegs and crash into {target_name}'s {hit_location} claws-first.",
            "victim_msg": "{attacker_name} launches off its hindlegs and crashes into your {hit_location} claws-first.",
            "observer_msg": "{attacker_name} launches off its hindlegs and crashes into {target_name}'s {hit_location} claws-first.",
        },
    ],
    "miss": [
        {
            "attacker_msg": "You snap at {target_name}'s {hit_location} — your teeth click shut on empty air.",
            "victim_msg": "{attacker_name} snaps at your {hit_location} — its teeth click shut on empty air.",
            "observer_msg": "{attacker_name} snaps at {target_name}'s {hit_location} — its teeth click shut on empty air.",
        },
        {
            "attacker_msg": "You lunge for {target_name}'s {hit_location} and skid past, claws scraping on the ground.",
            "victim_msg": "{attacker_name} lunges for your {hit_location} and skids past, claws scraping on the ground.",
            "observer_msg": "{attacker_name} lunges for {target_name}'s {hit_location} and skids past, claws scraping on the ground.",
        },
        {
            "attacker_msg": "Your tail-whip sweeps wide of {target_name}'s {hit_location}.",
            "victim_msg": "{attacker_name}'s tail-whip sweeps wide of your {hit_location}.",
            "observer_msg": "{attacker_name}'s tail-whip sweeps wide of {target_name}'s {hit_location}.",
        },
        {
            "attacker_msg": "You dart in toward {target_name}'s {hit_location} and pull back, hissing.",
            "victim_msg": "{attacker_name} darts in toward your {hit_location} and pulls back, hissing.",
            "observer_msg": "{attacker_name} darts in toward {target_name}'s {hit_location} and pulls back, hissing.",
        },
        {
            "attacker_msg": "Your bite glances off {target_name}'s {hit_location} without sinking in.",
            "victim_msg": "{attacker_name}'s bite glances off your {hit_location} without sinking in.",
            "observer_msg": "{attacker_name}'s bite glances off {target_name}'s {hit_location} without sinking in.",
        },
        {
            "attacker_msg": "You scrabble at {target_name}'s {hit_location} but can't find purchase.",
            "victim_msg": "{attacker_name} scrabbles at your {hit_location} but can't find purchase.",
            "observer_msg": "{attacker_name} scrabbles at {target_name}'s {hit_location} but can't find purchase.",
        },
    ],
    "kill": [
        {
            "attacker_msg": "You sink your incisors into {target_name}'s throat and don't let go — it goes limp in your jaws.",
            "victim_msg": "{attacker_name} sinks its incisors into your throat and doesn't let go — the world dims as you go limp in its jaws.",
            "observer_msg": "{attacker_name} sinks its incisors into {target_name}'s throat and doesn't let go — {target_name} goes limp.",
        },
        {
            "attacker_msg": "You scrabble onto {target_name}'s chest and chew through to something vital — it stops moving.",
            "victim_msg": "{attacker_name} scrabbles onto your chest and chews through to something vital — your vision swims and goes black.",
            "observer_msg": "{attacker_name} scrabbles onto {target_name}'s chest and chews through to something vital — {target_name} stops moving.",
        },
        {
            "attacker_msg": "Your claws and teeth tear at {target_name} until the body stops twitching.",
            "victim_msg": "{attacker_name}'s claws and teeth tear at you until you can't feel them anymore.",
            "observer_msg": "{attacker_name}'s claws and teeth tear at {target_name} until the body stops twitching.",
        },
        {
            "attacker_msg": "You worry at {target_name}'s wound until it bleeds out beneath you.",
            "victim_msg": "{attacker_name} worries at your wound — the last thing you feel is the small weight of it on your chest.",
            "observer_msg": "{attacker_name} worries at {target_name}'s wound until {target_name} bleeds out beneath it.",
        },
    ],
}
