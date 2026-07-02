"""Combat messages for the robot-frame integrated riot gun
(``ROBOT_ARM_GUN``, weapon_type ``robot_riot_gun``).

The attacker is a machine: a municipal security frame discharging a
subsystem. The register is cold procedure — targeting solutions,
compliance language, recoil compensators, casings ejecting from frame
ports — and the victim/observer lines carry what it is to be shot by
something that files the discharge as paperwork.
"""

MESSAGES = {
    "initiate": [
        {
            'attacker_msg': "Your forearm housing unlocks and the riot gun rotates up, targeting solution painting {target_name} in your feed.",
            'victim_msg': "{attacker_name}'s forearm housing unlocks and a riot gun rotates up — you can feel the targeting solution settle on you like a weight.",
            'observer_msg': "{attacker_name}'s forearm housing unlocks and a riot gun rotates up, its sensor band settling on {target_name}."
        },
        {
            'attacker_msg': "You announce once — LETHAL FORCE AUTHORIZED — and bring the arm-mounted riot gun to bear on {target_name}.",
            'victim_msg': "{attacker_name}'s vocalizer states, flat and even: LETHAL FORCE AUTHORIZED. The riot gun comes to bear on you.",
            'observer_msg': "{attacker_name}'s vocalizer states, flat and even: LETHAL FORCE AUTHORIZED. The riot gun comes to bear on {target_name}."
        },
        {
            'attacker_msg': "A shell cycles into the frame-mounted breech with a hydraulic *CHUNK* you feel through your whole chassis.",
            'victim_msg': "A shell cycles into {attacker_name}'s frame-mounted breech with a hydraulic *CHUNK* — the sound of a machine deciding.",
            'observer_msg': "A shell cycles into {attacker_name}'s frame-mounted breech with a hydraulic *CHUNK*."
        },
        {
            'attacker_msg': "You square your stance, stabilizers planting, and index the riot gun on {target_name} in one servo-smooth arc.",
            'victim_msg': "{attacker_name} squares its stance, feet planting with mechanical finality, and the riot gun swings onto you in one smooth arc.",
            'observer_msg': "{attacker_name} squares its stance and the riot gun swings onto {target_name} in one servo-smooth arc."
        },
        {
            'attacker_msg': "Recoil compensators pressurize along your forearm; the firing solution locks and holds on {target_name}.",
            'victim_msg': "You hear compensators pressurize along {attacker_name}'s forearm — the barrel does not waver, does not breathe, does not blink.",
            'observer_msg': "Compensators pressurize along {attacker_name}'s forearm; the barrel holds on {target_name} with inhuman stillness."
        },
        {
            'attacker_msg': "Your optics narrow to a firing aperture. {target_name} is a silhouette with a probability attached.",
            'victim_msg': "{attacker_name}'s optics narrow to pinpoints. You are being computed.",
            'observer_msg': "{attacker_name}'s optics narrow to pinpoints, fixed on {target_name}."
        },
        {
            'attacker_msg': "You track {target_name} with the riot gun, servos ticking in increments too small to see.",
            'victim_msg': "The riot gun tracks you wherever you move, {attacker_name}'s servos ticking in tiny, patient increments.",
            'observer_msg': "The riot gun tracks {target_name} in tiny servo increments — patient, exact, inevitable."
        },
        {
            'attacker_msg': "Compliance window closed. You commit the riot gun to {target_name} and the frame goes rigid as a tripod.",
            'victim_msg': "Something changes in {attacker_name}'s posture — the whole frame goes rigid as a tripod, and the barrel finds you.",
            'observer_msg': "{attacker_name}'s frame goes rigid as a tripod, the riot gun committed to {target_name}."
        },
    ],
    "hit": [
        {
            'attacker_msg': "The riot gun discharges — the report slams off the ferrocrete and {target_name} takes the spread square.",
            'victim_msg': "{attacker_name}'s riot gun discharges point-blank thunder and the spread takes you square — the world goes white at the edges.",
            'observer_msg': "{attacker_name}'s riot gun discharges — the report slams off the ferrocrete and {target_name} takes the spread square."
        },
        {
            'attacker_msg': "Your arm barely rises with the recoil — compensators drink it — and {target_name} folds around the impact.",
            'victim_msg': "The machine's arm barely moves with the shot. You move plenty — the impact folds you around itself.",
            'observer_msg': "{attacker_name}'s arm barely rises with the shot. {target_name} folds around the impact."
        },
        {
            'attacker_msg': "A spent casing ejects from your frame port, ringing off the ground as {target_name} staggers, hit.",
            'victim_msg': "You're hit — and through the roar you hear the small, tidy sound of the casing ejecting from {attacker_name}'s frame port.",
            'observer_msg': "A spent casing rings off the ground from {attacker_name}'s frame port as {target_name} staggers, hit."
        },
        {
            'attacker_msg': "Muzzle flash strobes across your plating. {target_name} takes the charge and the targeting pip flickers from red toward grey.",
            'victim_msg': "Muzzle flash strobes across {attacker_name}'s plating as the charge takes you — heat, then pressure, then the ground closer than it was.",
            'observer_msg': "Muzzle flash strobes across {attacker_name}'s plating as {target_name} takes the charge."
        },
        {
            'attacker_msg': "You fire on the exhale of a hydraulic cycle. The spread catches {target_name} and paints the wall behind them.",
            'victim_msg': "The shot arrives before the sound does. The spread catches you and something of yours paints the wall behind.",
            'observer_msg': "The spread catches {target_name} and paints the wall behind them; {attacker_name} is already re-indexing."
        },
        {
            'attacker_msg': "Impact registered. {target_name} is down a percentage; your breech cycles the next shell without being asked.",
            'victim_msg': "The hit knocks you a half-step sideways — and you can already hear {attacker_name}'s breech cycling the next shell.",
            'observer_msg': "{target_name} lurches with the hit. {attacker_name}'s breech cycles the next shell without pause."
        },
        {
            'attacker_msg': "You correct two degrees and fire; the charge takes {target_name} where the correction said it would.",
            'victim_msg': "The barrel twitches two precise degrees — then takes you exactly where it decided to.",
            'observer_msg': "{attacker_name}'s barrel twitches two precise degrees and takes {target_name} exactly there."
        },
        {
            'attacker_msg': "The discharge rocks {target_name} backward; your stabilizers absorb the recoil into the ground.",
            'victim_msg': "The discharge rocks you backward. {attacker_name} doesn't move at all — the recoil just disappears into its stance.",
            'observer_msg': "The discharge rocks {target_name} backward; {attacker_name} doesn't move at all."
        },
    ],
    "miss": [
        {
            'attacker_msg': "The riot gun roars and the spread tears the air beside {target_name} — solution stale, re-computing.",
            'victim_msg': "The spread tears the air beside your head — heat and grit — and you hear the machine's servos re-computing.",
            'observer_msg': "{attacker_name}'s riot gun roars; the spread tears the air beside {target_name}."
        },
        {
            'attacker_msg': "{target_name} moves on the discharge frame and your charge chews ferrocrete where they were standing.",
            'victim_msg': "You move as it fires — the charge chews the ferrocrete where you were standing a half-second ago.",
            'observer_msg': "{target_name} twists aside as {attacker_name}'s charge chews the ferrocrete where they stood."
        },
        {
            'attacker_msg': "Miss registered. A casing rings off the ground; your barrel is already walking back onto {target_name}.",
            'victim_msg': "The shot goes wide — but the barrel is already walking back onto you with terrible patience.",
            'observer_msg': "The shot goes wide of {target_name}; {attacker_name}'s barrel is already walking back on target."
        },
        {
            'attacker_msg': "The spread sparks off a wall in a fan of fragments; {target_name} is faster than the firing table said.",
            'victim_msg': "The spread sparks off the wall beside you in a fan of fragments — faster. You need to be faster.",
            'observer_msg': "{attacker_name}'s spread sparks off the wall in a fan of fragments, missing {target_name}."
        },
        {
            'attacker_msg': "Discharge — negative impact. Your vocalizer notes it aloud, toneless: MISS. RE-ACQUIRING.",
            'victim_msg': "The shot misses — and the machine's vocalizer says, toneless as a stamp: MISS. RE-ACQUIRING.",
            'observer_msg': "{attacker_name}'s shot misses {target_name}. Its vocalizer, toneless: MISS. RE-ACQUIRING."
        },
        {
            'attacker_msg': "The charge shreds a sign above {target_name} into ribbons of municipal tin.",
            'victim_msg': "The charge shreds the sign above your head into ribbons — the pieces are still falling as you run.",
            'observer_msg': "{attacker_name}'s charge shreds a sign above {target_name} into ribbons of municipal tin."
        },
    ],
    "kill": [
        {
            'attacker_msg': "The riot gun speaks once more and {target_name} drops where the solution said they would. INCIDENT RESOLVED.",
            'victim_msg': "The last thing is the barrel's black circle, and the flat voice behind it filing you as resolved.",
            'observer_msg': "{attacker_name}'s riot gun speaks once more and {target_name} drops. Its vocalizer, flat: INCIDENT RESOLVED."
        },
        {
            'attacker_msg': "{target_name} takes the full charge and does not get up. Your breech cycles; your log timestamps the discharge.",
            'victim_msg': "The full charge takes you off your feet, and the world closes like a file.",
            'observer_msg': "{target_name} takes the full charge and does not get up. {attacker_name}'s breech cycles, tidy as paperwork."
        },
        {
            'attacker_msg': "The spread puts {target_name} down in a spray; your compensators hiss the recoil away and the street is quiet.",
            'victim_msg': "Thunder, pressure, pavement. The machine's compensators hiss somewhere above you, and then nothing does.",
            'observer_msg': "The spread puts {target_name} down in a spray. {attacker_name}'s compensators hiss the recoil away, and the street is quiet."
        },
        {
            'attacker_msg': "Final discharge. {target_name} folds and stays folded. You lower the riot gun by exactly the required degrees.",
            'victim_msg': "You fold, and stay folded, and the last sound is servos lowering a barrel by some exact number of degrees.",
            'observer_msg': "{target_name} folds and stays folded. {attacker_name} lowers the riot gun by exactly the required degrees."
        },
        {
            'attacker_msg': "The casing from the killing shot rings off the ferrocrete. You log the serial. Cleanup is another department.",
            'victim_msg': "Somewhere past the roar, a casing rings off the ferrocrete — small and bright and the last thing.",
            'observer_msg': "The casing from the killing shot rings off the ferrocrete at {attacker_name}'s feet. It does not look down."
        },
        {
            'attacker_msg': "{target_name} goes down under the charge and your optics hold on them for three procedural seconds before releasing.",
            'victim_msg': "The charge takes you down, and the last light is a pair of optics holding on you like a stamp coming down.",
            'observer_msg': "{target_name} goes down under the charge. {attacker_name}'s optics hold on them a long three seconds, then release."
        },
    ],
}
