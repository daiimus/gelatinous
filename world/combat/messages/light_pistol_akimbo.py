"""Two light pistols, one in each hand: the pair bank (MULTI_WEAPON_COMBAT_SPEC
§5, §7; owner ruling §14 #14: akimbo pairs by weapon type, the item's name
inserted). Any two `light_pistol` items group through the `light_pistol` row
of `AKIMBO_PROFILES_BY_TYPE`; a pair is ONE attack, so a line may describe a
volley but never two rolls. `{item_name}` is the lead pistol's own name.
"""
MESSAGES = {
    'initiate': [
        {
            'attacker_msg': "You draw both pistols in one motion, two slides racking a half-beat apart.",
            'victim_msg': "{attacker_name} draws both pistols in one motion, two slides racking a half-beat apart.",
            'observer_msg': "{attacker_name} draws both pistols in one motion, two slides racking a half-beat apart."
        },
        {
            'attacker_msg': "A pistol in each hand, muzzles low. You bring them up together.",
            'victim_msg': "A pistol in each hand, muzzles low. {attacker_name} brings them up together.",
            'observer_msg': "A pistol in each hand, muzzles low. {attacker_name} brings them up together."
        },
        {
            'attacker_msg': "Two {item_name}s, one grip apiece, no sights to speak of at this range. You don't need them.",
            'victim_msg': "Two {item_name}s, one grip apiece, no sights to speak of at this range. {attacker_name} doesn't need them.",
            'observer_msg': "Two {item_name}s, one grip apiece, no sights to speak of at this range. {attacker_name} doesn't need them."
        },
        {
            'attacker_msg': "You cross your wrists for a moment, pistols kissing, then spread them wide.",
            'victim_msg': "{attacker_name} crosses their wrists for a moment, pistols kissing, then spreads them wide.",
            'observer_msg': "{attacker_name} crosses their wrists for a moment, pistols kissing, then spreads them wide."
        },
        {
            'attacker_msg': "The second pistol comes out as the first comes up. Both are pointed at {target_name} before the holsters stop swinging.",
            'victim_msg': "The second pistol comes out as the first comes up. Both are pointed at you before the holsters stop swinging.",
            'observer_msg': "The second pistol comes out as the first comes up. Both are pointed at {target_name} before the holsters stop swinging."
        },
        {
            'attacker_msg': "Twin muzzles settle on {target_name}, one high, one low. You can't miss with both.",
            'victim_msg': "Twin muzzles settle on you, one high, one low. {attacker_name} can't miss with both.",
            'observer_msg': "Twin muzzles settle on {target_name}, one high, one low. {attacker_name} can't miss with both."
        },
        {
            'attacker_msg': "You thumb both safeties off. Two small clicks that mean the same thing.",
            'victim_msg': "{attacker_name} thumbs both safeties off. Two small clicks that mean the same thing.",
            'observer_msg': "{attacker_name} thumbs both safeties off. Two small clicks that mean the same thing."
        },
        {
            'attacker_msg': "A pistol in each fist, elbows loose. Aim is for people with one gun.",
            'victim_msg': "A pistol in each fist, elbows loose. {attacker_name} aims like someone who has stopped caring about aim.",
            'observer_msg': "A pistol in each fist, elbows loose. {attacker_name} aims like someone who has stopped caring about aim."
        },
        {
            'attacker_msg': "The {item_name} in your lead hand finds {target_name} first. Its twin is a heartbeat behind.",
            'victim_msg': "The {item_name} in {attacker_name}'s lead hand finds you first. Its twin is a heartbeat behind.",
            'observer_msg': "The {item_name} in {attacker_name}'s lead hand finds {target_name} first. Its twin is a heartbeat behind."
        },
        {
            'attacker_msg': "You level both barrels and let your shoulders drop. Twice the lead, half the care.",
            'victim_msg': "{attacker_name} levels both barrels and lets their shoulders drop. Twice the lead, half the care.",
            'observer_msg': "{attacker_name} levels both barrels and lets their shoulders drop. Twice the lead, half the care."
        },
        {
            'attacker_msg': "Two magazines, two triggers, one target. You start counting rounds in pairs.",
            'victim_msg': "Two magazines, two triggers, one target. {attacker_name} starts counting rounds in pairs.",
            'observer_msg': "Two magazines, two triggers, one target. {attacker_name} starts counting rounds in pairs."
        },
        {
            'attacker_msg': "Both pistols come up and the room gets narrower. {target_name} is at the end of it.",
            'victim_msg': "Both pistols come up and the room gets narrower. You are at the end of it.",
            'observer_msg': "Both pistols come up and the room gets narrower. {target_name} is at the end of it."
        },
        {
            'attacker_msg': "You check neither chamber. You know. Both hands tighten.",
            'victim_msg': "{attacker_name} checks neither chamber. They know. Both hands tighten.",
            'observer_msg': "{attacker_name} checks neither chamber. They know. Both hands tighten."
        },
        {
            'attacker_msg': "A pistol in each hand is a bad habit you never broke. You draw them anyway.",
            'victim_msg': "A pistol in each hand is a bad habit {attacker_name} never broke. They draw them anyway.",
            'observer_msg': "A pistol in each hand is a bad habit {attacker_name} never broke. They draw them anyway."
        },
        {
            'attacker_msg': "The pistols rise together, polymer frames light, steel slides catching the light.",
            'victim_msg': "{attacker_name}'s pistols rise together, polymer frames light, steel slides catching the light.",
            'observer_msg': "{attacker_name}'s pistols rise together, polymer frames light, steel slides catching the light."
        },
        {
            'attacker_msg': "Two {item_name}s, held loose. You let {target_name} see both before you use either.",
            'victim_msg': "Two {item_name}s, held loose. {attacker_name} lets you see both before using either.",
            'observer_msg': "Two {item_name}s, held loose. {attacker_name} lets {target_name} see both before using either."
        },
    ],
    'hit': [
        {
            'attacker_msg': "Both pistols bark and {target_name}'s {hit_location} takes two rounds a hand's width apart.",
            'victim_msg': "Both pistols bark and your {hit_location} takes two rounds a hand's width apart.",
            'observer_msg': "Both pistols bark and {target_name}'s {hit_location} takes two rounds a hand's width apart."
        },
        {
            'attacker_msg': "The lead pistol punches {target_name}'s {hit_location}; its twin follows into the hole it made.",
            'victim_msg': "The lead pistol punches your {hit_location}; its twin follows into the hole it made.",
            'observer_msg': "The lead pistol punches {target_name}'s {hit_location}; its twin follows into the hole it made."
        },
        {
            'attacker_msg': "Two cracks, one echo. {target_name}'s {hit_location} blooms twice.",
            'victim_msg': "Two cracks, one echo. Your {hit_location} blooms twice.",
            'observer_msg': "Two cracks, one echo. {target_name}'s {hit_location} blooms twice."
        },
        {
            'attacker_msg': "You fire both {item_name}s together and the {hit_location} stops {target_name} where they stand.",
            'victim_msg': "{attacker_name} fires both {item_name}s together and your {hit_location} stops you where you stand.",
            'observer_msg': "{attacker_name} fires both {item_name}s together and the {hit_location} stops {target_name} where they stand."
        },
        {
            'attacker_msg': "A round from each hand slams into the {hit_location}. Brass rains on both sides of you.",
            'victim_msg': "A round from each hand slams into your {hit_location}. Brass rains on both sides of {attacker_name}.",
            'observer_msg': "A round from each hand slams into {target_name}'s {hit_location}. Brass rains on both sides of {attacker_name}."
        },
        {
            'attacker_msg': "The pistols speak over each other and {target_name}'s {hit_location} hears both.",
            'victim_msg': "The pistols speak over each other and your {hit_location} hears both.",
            'observer_msg': "The pistols speak over each other and {target_name}'s {hit_location} hears both."
        },
        {
            'attacker_msg': "One barrel, then the other, no pause. {target_name} staggers as the {hit_location} takes the pair.",
            'victim_msg': "One barrel, then the other, no pause. You stagger as your {hit_location} takes the pair.",
            'observer_msg': "One barrel, then the other, no pause. {target_name} staggers as their {hit_location} takes the pair."
        },
        {
            'attacker_msg': "You walk the twin muzzles onto {target_name}'s {hit_location} and squeeze both. Cloth tears in two places.",
            'victim_msg': "{attacker_name} walks the twin muzzles onto your {hit_location} and squeezes both. Cloth tears in two places.",
            'observer_msg': "{attacker_name} walks the twin muzzles onto {target_name}'s {hit_location} and squeezes both. Cloth tears in two places."
        },
        {
            'attacker_msg': "A double report and the {hit_location} jerks back. {target_name} finds two holes where there was one shirt.",
            'victim_msg': "A double report and your {hit_location} jerks back. You find two holes where there was one shirt.",
            'observer_msg': "A double report and {target_name}'s {hit_location} jerks back. They find two holes where there was one shirt."
        },
        {
            'attacker_msg': "Both slides cycle as one. {target_name}'s {hit_location} is punched through before the first casing lands.",
            'victim_msg': "Both slides cycle as one. Your {hit_location} is punched through before the first casing lands.",
            'observer_msg': "Both slides cycle as one. {target_name}'s {hit_location} is punched through before the first casing lands."
        },
        {
            'attacker_msg': "The {item_name}s fire a hair apart, and the {hit_location} takes a hair-wide pair of wounds.",
            'victim_msg': "The {item_name}s fire a hair apart, and your {hit_location} takes a hair-wide pair of wounds.",
            'observer_msg': "The {item_name}s fire a hair apart, and {target_name}'s {hit_location} takes a hair-wide pair of wounds."
        },
        {
            'attacker_msg': "You squeeze both triggers and {target_name}'s {hit_location} answers with blood twice over.",
            'victim_msg': "{attacker_name} squeezes both triggers and your {hit_location} answers with blood twice over.",
            'observer_msg': "{attacker_name} squeezes both triggers and {target_name}'s {hit_location} answers with blood twice over."
        },
        {
            'attacker_msg': "A pair of rounds stitch the {hit_location}. Two casings ring on the floor like change.",
            'victim_msg': "A pair of rounds stitch your {hit_location}. Two casings ring on the floor like change.",
            'observer_msg': "A pair of rounds stitch {target_name}'s {hit_location}. Two casings ring on the floor like change."
        },
        {
            'attacker_msg': "One pistol knocks {target_name} off balance, the other finds the {hit_location} on the way down.",
            'victim_msg': "One pistol knocks you off balance, the other finds your {hit_location} on the way down.",
            'observer_msg': "One pistol knocks {target_name} off balance, the other finds their {hit_location} on the way down."
        },
        {
            'attacker_msg': "Two flashes, and the {hit_location} opens. {target_name} is leaking before the smoke clears.",
            'victim_msg': "Two flashes, and your {hit_location} opens. You are leaking before the smoke clears.",
            'observer_msg': "Two flashes, and {target_name}'s {hit_location} opens. They are leaking before the smoke clears."
        },
        {
            'attacker_msg': "You fire from both hips and both rounds find {target_name}'s {hit_location}. Luck, or practice.",
            'victim_msg': "{attacker_name} fires from both hips and both rounds find your {hit_location}. Luck, or practice.",
            'observer_msg': "{attacker_name} fires from both hips and both rounds find {target_name}'s {hit_location}. Luck, or practice."
        },
    ],
    'miss': [
        {
            'attacker_msg': "Both pistols crack and both rounds go wide. {target_name} ducks a volley that was never close.",
            'victim_msg': "Both pistols crack and both rounds go wide. You duck a volley that was never close.",
            'observer_msg': "Both pistols crack and both rounds go wide. {target_name} ducks a volley that was never close."
        },
        {
            'attacker_msg': "Two shots, two puffs of plaster. {target_name} is between them, untouched.",
            'victim_msg': "Two shots, two puffs of plaster. You are between them, untouched.",
            'observer_msg': "Two shots, two puffs of plaster. {target_name} is between them, untouched."
        },
        {
            'attacker_msg': "The pistols buck in opposite directions and neither round finds {target_name}.",
            'victim_msg': "The pistols buck in opposite directions and neither round finds you.",
            'observer_msg': "The pistols buck in opposite directions and neither round finds {target_name}."
        },
        {
            'attacker_msg': "You fire both and the recoil crosses your wrists. The rounds cross too, well behind {target_name}.",
            'victim_msg': "{attacker_name} fires both and the recoil crosses their wrists. The rounds cross too, well behind you.",
            'observer_msg': "{attacker_name} fires both and the recoil crosses their wrists. The rounds cross too, well behind {target_name}."
        },
        {
            'attacker_msg': "A double report that hits only the far wall. Two casings, no blood.",
            'victim_msg': "A double report from {attacker_name} that hits only the far wall. Two casings, no blood.",
            'observer_msg': "A double report from {attacker_name} that hits only the far wall. Two casings, no blood."
        },
        {
            'attacker_msg': "{target_name} drops a shoulder and the paired rounds pass over it, a hand apart.",
            'victim_msg': "You drop a shoulder and the paired rounds pass over it, a hand apart.",
            'observer_msg': "{target_name} drops a shoulder and the paired rounds pass over it, a hand apart."
        },
        {
            'attacker_msg': "The {item_name}s bark together and a lamp dies for it. {target_name} does not.",
            'victim_msg': "The {item_name}s bark together and a lamp dies for it. You do not.",
            'observer_msg': "The {item_name}s bark together and a lamp dies for it. {target_name} does not."
        },
        {
            'attacker_msg': "Two muzzles, two misses. You are reminded why people aim.",
            'victim_msg': "Two muzzles, two misses. {attacker_name} is reminded why people aim.",
            'observer_msg': "Two muzzles, two misses. {attacker_name} is reminded why people aim."
        },
        {
            'attacker_msg': "One pistol fires early, the other late, and {target_name} walks between the two shots.",
            'victim_msg': "One pistol fires early, the other late, and you walk between the two shots.",
            'observer_msg': "One pistol fires early, the other late, and {target_name} walks between the two shots."
        },
        {
            'attacker_msg': "Both rounds spark off a pipe behind {target_name}. The pipe did nothing to deserve it.",
            'victim_msg': "Both rounds spark off a pipe behind you. The pipe did nothing to deserve it.",
            'observer_msg': "Both rounds spark off a pipe behind {target_name}. The pipe did nothing to deserve it."
        },
        {
            'attacker_msg': "You squeeze both triggers and a window somewhere agrees loudly. {target_name} is unhurt.",
            'victim_msg': "{attacker_name} squeezes both triggers and a window somewhere agrees loudly. You are unhurt.",
            'observer_msg': "{attacker_name} squeezes both triggers and a window somewhere agrees loudly. {target_name} is unhurt."
        },
        {
            'attacker_msg': "The paired shots chase {target_name} across the room and arrive late to every place they were.",
            'victim_msg': "The paired shots chase you across the room and arrive late to every place you were.",
            'observer_msg': "The paired shots chase {target_name} across the room and arrive late to every place they were."
        },
        {
            'attacker_msg': "Twin flashes light {target_name}'s face. Twin rounds miss it.",
            'victim_msg': "Twin flashes light your face. Twin rounds miss it.",
            'observer_msg': "Twin flashes light {target_name}'s face. Twin rounds miss it."
        },
        {
            'attacker_msg': "You fire both at once and the pistols fight your hands for it. The shots scatter.",
            'victim_msg': "{attacker_name} fires both at once and the pistols fight their hands for it. The shots scatter.",
            'observer_msg': "{attacker_name} fires both at once and the pistols fight their hands for it. The shots scatter."
        },
        {
            'attacker_msg': "A pair of rounds chew the doorframe beside {target_name}. Splinters, a cough, no wound.",
            'victim_msg': "A pair of rounds chew the doorframe beside you. Splinters, a cough, no wound.",
            'observer_msg': "A pair of rounds chew the doorframe beside {target_name}. Splinters, a cough, no wound."
        },
        {
            'attacker_msg': "The {item_name} in your lead hand misses and its twin copies it faithfully.",
            'victim_msg': "The {item_name} in {attacker_name}'s lead hand misses and its twin copies it faithfully.",
            'observer_msg': "The {item_name} in {attacker_name}'s lead hand misses and its twin copies it faithfully."
        },
    ],
    'kill': [
        {
            'attacker_msg': "Both pistols fire into {target_name}'s {hit_location} and the body drops between the two reports.",
            'victim_msg': "Both pistols fire into your {hit_location} and you drop between the two reports.",
            'observer_msg': "Both pistols fire into {target_name}'s {hit_location} and they drop between the two reports."
        },
        {
            'attacker_msg': "Two rounds through the {hit_location}, a finger apart. {target_name} is dead before the casings land.",
            'victim_msg': "Two rounds through your {hit_location}, a finger apart. You are dead before the casings land.",
            'observer_msg': "Two rounds through {target_name}'s {hit_location}, a finger apart. {target_name} is dead before the casings land."
        },
        {
            'attacker_msg': "The lead pistol drops {target_name}; its twin puts one more into the {hit_location} to be sure.",
            'victim_msg': "The lead pistol drops you; its twin puts one more into your {hit_location} to be sure.",
            'observer_msg': "The lead pistol drops {target_name}; its twin puts one more into their {hit_location} to be sure."
        },
        {
            'attacker_msg': "You fire both {item_name}s into the {hit_location} until {target_name} stops being a person and starts being a shape.",
            'victim_msg': "{attacker_name} fires both {item_name}s into your {hit_location} until you stop being a person and start being a shape.",
            'observer_msg': "{attacker_name} fires both {item_name}s into {target_name}'s {hit_location} until they stop being a person and start being a shape."
        },
        {
            'attacker_msg': "A double tap from both hands. {target_name}'s {hit_location} comes apart and the rest follows it down.",
            'victim_msg': "A double tap from both hands. Your {hit_location} comes apart and the rest follows it down.",
            'observer_msg': "A double tap from both hands. {target_name}'s {hit_location} comes apart and the rest follows it down."
        },
        {
            'attacker_msg': "Two muzzle flashes, one last breath. {target_name} folds with the {hit_location} smoking.",
            'victim_msg': "Two muzzle flashes, one last breath. You fold with your {hit_location} smoking.",
            'observer_msg': "Two muzzle flashes, one last breath. {target_name} folds with their {hit_location} smoking."
        },
        {
            'attacker_msg': "The pistols speak together one final time and {target_name}'s {hit_location} has no answer.",
            'victim_msg': "The pistols speak together one final time and your {hit_location} has no answer.",
            'observer_msg': "The pistols speak together one final time and {target_name}'s {hit_location} has no answer."
        },
        {
            'attacker_msg': "Paired rounds punch through the {hit_location}. {target_name} sits down in their own {blood} and stays.",
            'victim_msg': "Paired rounds punch through your {hit_location}. You sit down in your own {blood} and stay.",
            'observer_msg': "Paired rounds punch through {target_name}'s {hit_location}. They sit down in their own {blood} and stay."
        },
        {
            'attacker_msg': "You put a round from each pistol into the {hit_location}. {target_name} was already falling after the first.",
            'victim_msg': "{attacker_name} puts a round from each pistol into your {hit_location}. You were already falling after the first.",
            'observer_msg': "{attacker_name} puts a round from each pistol into {target_name}'s {hit_location}. They were already falling after the first."
        },
        {
            'attacker_msg': "Both barrels on the {hit_location}, both triggers home. {target_name} ends in the time it takes a casing to fall.",
            'victim_msg': "Both barrels on your {hit_location}, both triggers home. You end in the time it takes a casing to fall.",
            'observer_msg': "Both barrels on {target_name}'s {hit_location}, both triggers home. {target_name} ends in the time it takes a casing to fall."
        },
        {
            'attacker_msg': "The {item_name}s crack as one and {target_name} drops with two holes in the {hit_location} and no more opinions.",
            'victim_msg': "The {item_name}s crack as one and you drop with two holes in your {hit_location} and no more opinions.",
            'observer_msg': "The {item_name}s crack as one and {target_name} drops with two holes in their {hit_location} and no more opinions."
        },
        {
            'attacker_msg': "A pair of shots to the {hit_location}. {target_name} jerks twice, once for each, then not at all.",
            'victim_msg': "A pair of shots to your {hit_location}. You jerk twice, once for each, then not at all.",
            'observer_msg': "A pair of shots to {target_name}'s {hit_location}. They jerk twice, once for each, then not at all."
        },
        {
            'attacker_msg': "Two slides lock forward on the last of {target_name}. The {hit_location} did not survive the pair.",
            'victim_msg': "Two slides lock forward on the last of you. Your {hit_location} did not survive the pair.",
            'observer_msg': "Two slides lock forward on the last of {target_name}. Their {hit_location} did not survive the pair."
        },
        {
            'attacker_msg': "You fire both into the {hit_location} and {target_name}'s knees agree with the verdict.",
            'victim_msg': "{attacker_name} fires both into your {hit_location} and your knees agree with the verdict.",
            'observer_msg': "{attacker_name} fires both into {target_name}'s {hit_location} and their knees agree with the verdict."
        },
        {
            'attacker_msg': "Two reports, one body. {target_name}'s {hit_location} is the last thing to hit the floor.",
            'victim_msg': "Two reports, one body. Your {hit_location} is the last thing to hit the floor.",
            'observer_msg': "Two reports, one body. {target_name}'s {hit_location} is the last thing to hit the floor."
        },
        {
            'attacker_msg': "The twin pistols lower together over what is left of {target_name}. Smoke from both, {blood} from one {hit_location}.",
            'victim_msg': "The twin pistols lower together over what is left of you. Smoke from both, {blood} from your {hit_location}.",
            'observer_msg': "The twin pistols lower together over what is left of {target_name}. Smoke from both, {blood} from one {hit_location}."
        },
    ],
}
