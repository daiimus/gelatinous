"""Combat messages for the robot-frame integrated riot gun
(``ROBOT_ARM_GUN``, weapon_type ``robot_riot_gun``).

The attacker is a municipal machine discharging a subsystem. Where the
human ``cybernetic_shotgun`` bank is *my body is a weapon*, this one is
*there is no body and no I* — procedure meeting meat. The horror is the
asymmetry: recoil disappears into stabilizers while the target moves
plenty; the report is thunder and the follow-up is arithmetic.

House conventions: one image per entry, short kinetic sentences,
``{hit_location}`` grounding on hit/kill, three perspectives per entry.
"""

MESSAGES = {
    "initiate": [
        {
            'attacker_msg': "Your stabilizers plant and the riot gun comes up in one servo-smooth arc, {target_name} centering in the solution.",
            'victim_msg': "{attacker_name}'s feet plant with mechanical finality and the riot gun swings up onto you in one smooth arc.",
            'observer_msg': "{attacker_name}'s feet plant and the riot gun swings onto {target_name} in one servo-smooth arc."
        },
        {
            'attacker_msg': "A shell cycles into the frame breech — the *CHUNK* carries through your whole chassis and out into the street.",
            'victim_msg': "A shell cycles into {attacker_name}'s frame with a hydraulic *CHUNK* you feel in your teeth.",
            'observer_msg': "A shell cycles into {attacker_name}'s frame with a hydraulic *CHUNK* that carries across the street."
        },
        {
            'attacker_msg': "Your vocalizer states it once, flat as a stamp — LETHAL FORCE AUTHORIZED — and the barrel stops moving.",
            'victim_msg': "{attacker_name}'s vocalizer states it once, flat as a stamp: LETHAL FORCE AUTHORIZED. Then the barrel stops moving.",
            'observer_msg': "{attacker_name}'s vocalizer, flat as a stamp: LETHAL FORCE AUTHORIZED. The barrel stops moving."
        },
        {
            'attacker_msg': "The gun at the end of your arm holds on {target_name} with a stillness nothing living gets to have.",
            'victim_msg': "The gun at the end of {attacker_name}'s arm holds on you with a stillness nothing living gets to have.",
            'observer_msg': "The gun at the end of {attacker_name}'s arm holds on {target_name}, still as furniture."
        },
        {
            'attacker_msg': "Compensators pressurize along your forearm with a rising hiss. The math is done; the barrel is just waiting.",
            'victim_msg': "Compensators hiss up to pressure along {attacker_name}'s forearm. Whatever math there was is finished.",
            'observer_msg': "Compensators hiss up to pressure along {attacker_name}'s forearm."
        },
        {
            'attacker_msg': "You track {target_name} in tick-tick-tick servo increments, the muzzle arriving everywhere they think of going.",
            'victim_msg': "The muzzle tracks you in tiny ticking increments — it's already everywhere you think of going.",
            'observer_msg': "{attacker_name}'s muzzle tracks {target_name} in small ticking increments, patient as a meter."
        },
        {
            'attacker_msg': "Your optics stop sweeping and narrow to an aperture. {target_name} is the only thing left in the world.",
            'victim_msg': "{attacker_name}'s optics stop sweeping and narrow to pinpoints. You are the only thing left in its world.",
            'observer_msg': "{attacker_name}'s optics stop sweeping and fix on {target_name}, narrowed to pinpoints."
        },
        {
            'attacker_msg': "You level the riot gun at {target_name} the way a meter reads a dial — no anger anywhere in the machinery.",
            'victim_msg': "{attacker_name} levels the riot gun at you the way a meter reads a dial. There's no anger anywhere in it.",
            'observer_msg': "{attacker_name} levels the riot gun at {target_name} the way a meter reads a dial."
        },
        {
            'attacker_msg': "Scuffed municipal plating, a parts-code stencil, and a bore the size of a verdict — all of it pointed at {target_name}.",
            'victim_msg': "{attacker_name} is scuffed plating, a faded parts-code, and a bore the size of a verdict — all of it pointed at you.",
            'observer_msg': "{attacker_name} is scuffed plating and a bore the size of a verdict, all of it pointed at {target_name}."
        },
        {
            'attacker_msg': "Your frame goes rigid, tripod-still, the riot gun committed to {target_name} like a signature.",
            'victim_msg': "{attacker_name}'s frame goes rigid, tripod-still, the riot gun committed to you like a signature.",
            'observer_msg': "{attacker_name}'s frame goes tripod-still, the riot gun committed to {target_name}."
        },
        {
            'attacker_msg': "Somewhere in your torso a compressor spins up. {target_name} hears it too — the sound of a decision being made.",
            'victim_msg': "Somewhere inside {attacker_name} a compressor spins up. It sounds exactly like a decision being made.",
            'observer_msg': "Somewhere inside {attacker_name} a compressor spins up, and the muzzle settles on {target_name}."
        },
        {
            'attacker_msg': "You give {target_name} the barrel and the silence after it, which is all the warning the directive requires.",
            'victim_msg': "{attacker_name} gives you the barrel and then the silence after it — all the warning you're getting.",
            'observer_msg': "{attacker_name} gives {target_name} the barrel, and then the silence after it."
        },
        {
            'attacker_msg': "The firing solution paints {target_name} in your feed and stays painted, steady through everything they do next.",
            'victim_msg': "You can feel the lock settle on you like a hand on the shoulder — and it stays, through everything you do next.",
            'observer_msg': "{attacker_name}'s sensor band settles on {target_name} and stays, steady through everything."
        },
        {
            'attacker_msg': "One shoulder drops two degrees, the elbow locks, and your arm stops being an arm at all.",
            'victim_msg': "{attacker_name}'s shoulder drops, the elbow locks, and its arm stops being an arm at all.",
            'observer_msg': "{attacker_name}'s shoulder drops, the elbow locks, and the arm stops being an arm at all."
        },
    ],
    "hit": [
        {
            'attacker_msg': "The riot gun slams and {target_name}'s {hit_location} takes the pattern square — your side of the recoil just disappears into the stabilizers.",
            'victim_msg': "{attacker_name}'s riot gun slams and your {hit_location} takes the pattern square. The machine doesn't even rock.",
            'observer_msg': "{attacker_name}'s riot gun slams and {target_name}'s {hit_location} takes the pattern. The machine doesn't even rock."
        },
        {
            'attacker_msg': "Thunder off the ferrocrete. {target_name} spins with the spread in their {hit_location}; your barrel is already back on center.",
            'victim_msg': "Thunder off the ferrocrete — the spread takes your {hit_location} and spins you half around.",
            'observer_msg': "Thunder off the ferrocrete. {target_name} spins, {hit_location} bloody; {attacker_name}'s barrel is already back on center."
        },
        {
            'attacker_msg': "You correct two degrees and fire. {target_name}'s {hit_location} opens exactly where the correction said it would.",
            'victim_msg': "The barrel twitches two small degrees, then your {hit_location} opens exactly where it decided.",
            'observer_msg': "{attacker_name}'s barrel twitches two degrees and {target_name}'s {hit_location} opens exactly there."
        },
        {
            'attacker_msg': "The casing rings off the ground, small and bright, while {target_name} is still finding out about their {hit_location}.",
            'victim_msg': "You hear the casing ring off the ground — a small tidy sound — before the pain in your {hit_location} arrives at all.",
            'observer_msg': "A casing rings off the ground at {attacker_name}'s feet while {target_name} is still finding out about their {hit_location}."
        },
        {
            'attacker_msg': "Muzzle flash strobes your plating white. {target_name} folds around the charge in their {hit_location}.",
            'victim_msg': "Muzzle flash strobes {attacker_name}'s plating white and you fold around the charge in your {hit_location}.",
            'observer_msg': "Muzzle flash strobes {attacker_name}'s plating white; {target_name} folds around their {hit_location}."
        },
        {
            'attacker_msg': "The spread chews {target_name}'s {hit_location} ragged. Your breech cycles the next shell without being asked.",
            'victim_msg': "The spread chews your {hit_location} ragged, and you can already hear the next shell seating.",
            'observer_msg': "The spread chews {target_name}'s {hit_location} ragged. {attacker_name}'s breech cycles without pause."
        },
        {
            'attacker_msg': "You fire at conversational distance. {target_name}'s {hit_location} takes the whole sentence.",
            'victim_msg': "{attacker_name} fires at conversational distance. Your {hit_location} takes the whole sentence.",
            'observer_msg': "{attacker_name} fires at conversational distance and {target_name}'s {hit_location} takes all of it."
        },
        {
            'attacker_msg': "The charge takes {target_name} in the {hit_location} like a swung gate. Your stabilizers pass the recoil into the street.",
            'victim_msg': "The charge takes you in the {hit_location} like a swung gate. {attacker_name} just stands there, planted.",
            'observer_msg': "The charge takes {target_name} in the {hit_location} like a swung gate. {attacker_name} doesn't move at all."
        },
        {
            'attacker_msg': "Impact confirmed. {target_name}'s {hit_location} goes from a body part to a problem in one report.",
            'victim_msg': "One report, and your {hit_location} goes from a body part to a problem.",
            'observer_msg': "One report from {attacker_name}, and {target_name}'s {hit_location} goes from a body part to a problem."
        },
        {
            'attacker_msg': "The pattern centers on {target_name}'s {hit_location} and paints the wall behind them in the same instant.",
            'victim_msg': "The pattern centers on your {hit_location}; something of yours reaches the wall before you do.",
            'observer_msg': "{attacker_name}'s pattern centers on {target_name}'s {hit_location} and paints the wall behind them."
        },
        {
            'attacker_msg': "You walk the muzzle onto {target_name} mid-step and fire — their {hit_location} lifts them off their line entirely.",
            'victim_msg': "{attacker_name} walks the muzzle onto you mid-step and fires — your {hit_location} takes you off your feet.",
            'observer_msg': "{attacker_name} walks the muzzle onto {target_name} mid-step and the shot lifts them off their line."
        },
        {
            'attacker_msg': "Servos absorb the kick in one tick. {target_name}'s {hit_location} absorbs everything else.",
            'victim_msg': "The machine's servos absorb the kick in one tick. Your {hit_location} absorbs everything else.",
            'observer_msg': "{attacker_name}'s servos absorb the kick in a tick; {target_name}'s {hit_location} absorbs the rest."
        },
        {
            'attacker_msg': "Heat shimmer climbs off the barrel shroud. {target_name} staggers, one hand going to a {hit_location} that isn't all there.",
            'victim_msg': "Heat shimmers off {attacker_name}'s barrel. Your hand goes to your {hit_location} and finds less than it should.",
            'observer_msg': "Heat shimmers off {attacker_name}'s barrel. {target_name}'s hand goes to a {hit_location} that isn't all there."
        },
        {
            'attacker_msg': "The report caroms down the block. Somewhere under it, {target_name} hits the ground {hit_location}-first.",
            'victim_msg': "The report caroms down the block and takes your legs with it — you go down {hit_location}-first.",
            'observer_msg': "{attacker_name}'s report caroms down the block. Under it, {target_name} goes down {hit_location}-first."
        },
        {
            'attacker_msg': "You log the hit the same instant you make it: {target_name}, {hit_location}, effect confirmed.",
            'victim_msg': "You realize, through the blood in your {hit_location}, that the thing shooting you is also taking notes.",
            'observer_msg': "{attacker_name} fires into {target_name}'s {hit_location} with the unhurried air of something taking notes."
        },
    ],
    "miss": [
        {
            'attacker_msg': "The riot gun roars and the spread shreds the air a hand's width from {target_name}'s head.",
            'victim_msg': "The spread shreds the air a hand's width from your head — heat, grit, and the smell of scorched dust.",
            'observer_msg': "{attacker_name}'s riot gun roars; the spread shreds the air beside {target_name}'s head."
        },
        {
            'attacker_msg': "{target_name} moves inside the discharge frame and your charge chews ferrocrete where they were standing.",
            'victim_msg': "You move as it fires and the charge chews the ferrocrete where you were standing half a heartbeat ago.",
            'observer_msg': "{target_name} twists aside and {attacker_name}'s charge chews the ferrocrete where they stood."
        },
        {
            'attacker_msg': "Miss logged. Your vocalizer doesn't editorialize — RE-ACQUIRING — and the barrel starts walking back.",
            'victim_msg': "The shot goes wide, and the machine's vocalizer says only: RE-ACQUIRING. The barrel starts walking back toward you.",
            'observer_msg': "{attacker_name}'s shot goes wide of {target_name}. Its vocalizer, toneless: RE-ACQUIRING."
        },
        {
            'attacker_msg': "The pattern sparks off a wall in a fan of fragments. {target_name} is faster than the firing table allowed.",
            'victim_msg': "The pattern sparks off the wall beside you in a fan of fragments. Faster. Be faster.",
            'observer_msg': "{attacker_name}'s pattern sparks off the wall in a fan of fragments, missing {target_name}."
        },
        {
            'attacker_msg': "A municipal sign takes the charge meant for {target_name} and becomes ribbons of painted tin.",
            'victim_msg': "The sign above your head takes the charge meant for you — ribbons of painted tin are still falling as you run.",
            'observer_msg': "A sign takes {attacker_name}'s charge meant for {target_name} and becomes ribbons of painted tin."
        },
        {
            'attacker_msg': "The shot passes through where {target_name}'s silhouette was one frame ago. The solution updates without comment.",
            'victim_msg': "The shot passes through where you were one heartbeat ago. You can feel it re-computing you.",
            'observer_msg': "{attacker_name}'s shot passes through where {target_name} was a heartbeat ago."
        },
        {
            'attacker_msg': "Dust and shot-scatter erase the corner {target_name} just took. Your servos swivel you after them, unhurried.",
            'victim_msg': "Dust and shot-scatter erase the corner behind you. You hear its servos swivel — unhurried, which is worse.",
            'observer_msg': "Shot-scatter erases the corner {target_name} took. {attacker_name}'s servos swivel after them, unhurried."
        },
        {
            'attacker_msg': "The recoil goes somewhere tidy; the charge goes somewhere useless. {target_name} is still upright.",
            'victim_msg': "The blast goes wide and something behind you dies instead. You are, for the moment, still upright.",
            'observer_msg': "{attacker_name}'s blast goes wide of {target_name} and something behind them takes it instead."
        },
        {
            'attacker_msg': "You fire through the gap {target_name} was supposed to still occupy. Probability is not a promise.",
            'victim_msg': "It fires through the gap you were supposed to still be in. You make a note to keep disappointing it.",
            'observer_msg': "{attacker_name} fires through a gap {target_name} no longer occupies."
        },
        {
            'attacker_msg': "The muzzle climbs a half-degree off true and the pattern goes high, raining grit off an awning onto {target_name}.",
            'victim_msg': "The pattern goes high and an awning's worth of grit rains down on you — luck, thin and loud.",
            'observer_msg': "{attacker_name}'s pattern goes high, raining awning grit down over {target_name}."
        },
        {
            'attacker_msg': "A civilian shutter slams somewhere. Your shot has made the street very empty and {target_name} very awake.",
            'victim_msg': "The shot misses and every shutter on the street slams at once. You have never been this awake.",
            'observer_msg': "{attacker_name}'s shot misses {target_name}; up and down the street, shutters slam."
        },
        {
            'attacker_msg': "The spread combs {target_name}'s coat and takes cloth instead of {hit_location}. The ledger stays open.",
            'victim_msg': "The spread combs your coat — cloth, not flesh, this once. You feel the wind of the difference.",
            'observer_msg': "The spread combs {target_name}'s coat, taking cloth and nothing else. {attacker_name} re-indexes."
        },
    ],
    "kill": [
        {
            'attacker_msg': "The riot gun speaks once more and {target_name} drops where the solution said they would, {hit_location} ruined. Your vocalizer closes it out: INCIDENT RESOLVED.",
            'victim_msg': "The last of it is the barrel's black circle, your own {hit_location} letting go, and a flat voice filing you as resolved.",
            'observer_msg': "{attacker_name}'s riot gun speaks once more and {target_name} drops, {hit_location} ruined. The vocalizer, flat: INCIDENT RESOLVED."
        },
        {
            'attacker_msg': "{target_name} takes the full charge through the {hit_location} and does not get up. Your breech cycles, tidy as paperwork.",
            'victim_msg': "The full charge takes you through the {hit_location} and the world closes like a file.",
            'observer_msg': "{target_name} takes the full charge through the {hit_location} and does not get up. {attacker_name}'s breech cycles, tidy as paperwork."
        },
        {
            'attacker_msg': "The pattern centers, {target_name}'s {hit_location} gives, and the street goes quiet except for your compensators bleeding off pressure.",
            'victim_msg': "Thunder, your {hit_location}, the pavement. The last sound is compensators hissing somewhere above you.",
            'observer_msg': "The pattern centers and {target_name} goes down for good. The only sound after is {attacker_name}'s compensators bleeding off pressure."
        },
        {
            'attacker_msg': "Final discharge. {target_name} folds over their ruined {hit_location} and stays folded. You lower the barrel by exactly the required degrees.",
            'victim_msg': "You fold over what used to be your {hit_location}, and stay folded, and the last thing is servos lowering a barrel by some exact number of degrees.",
            'observer_msg': "{target_name} folds over their ruined {hit_location} and stays folded. {attacker_name} lowers the barrel by exactly the required degrees."
        },
        {
            'attacker_msg': "The killing casing rings off the ferrocrete at your feet. You do not look down. Cleanup is another department.",
            'victim_msg': "Past the roar, a casing rings off the ferrocrete — small, bright, and the last thing you get.",
            'observer_msg': "The casing from the killing shot rings off the ferrocrete at {attacker_name}'s feet. It does not look down."
        },
        {
            'attacker_msg': "{target_name} goes down with the charge in their {hit_location} and your optics hold on them three procedural seconds before releasing.",
            'victim_msg': "You go down with the charge in your {hit_location}, and the last light is a pair of optics holding on you like a stamp coming down.",
            'observer_msg': "{target_name} goes down and {attacker_name}'s optics hold on them a long three seconds, then release."
        },
        {
            'attacker_msg': "One report. {target_name}'s {hit_location} was between the barrel and the rest of their life, and now neither is anywhere.",
            'victim_msg': "One report, your {hit_location}, and then nothing has ever been this quiet.",
            'observer_msg': "One report from {attacker_name}, and {target_name} is a shape on the ground that used to be going somewhere."
        },
        {
            'attacker_msg': "The spread takes {target_name} off their feet and the ground finishes the sentence. You timestamp the discharge and stand down the solution.",
            'victim_msg': "The spread takes you off your feet. The ground finishes it.",
            'observer_msg': "The spread takes {target_name} off their feet; the ground finishes it. {attacker_name} is already still again."
        },
        {
            'attacker_msg': "{target_name} slides down the wall they were painted against, {hit_location} gone. Your feed marks the silhouette grey.",
            'victim_msg': "The wall catches you, then lowers you, and the machine watches your outline go grey in its feed.",
            'observer_msg': "{target_name} slides down the wall, {hit_location} gone, while {attacker_name} watches with meter-flat patience."
        },
        {
            'attacker_msg': "No follow-up required. {target_name} is face-down over their own {hit_location}, and the street's crowd noise starts filling back in around the silence you made.",
            'victim_msg': "Face-down, your {hit_location} under you, the crowd noise coming back for everyone else.",
            'observer_msg': "{target_name} lies face-down over their own {hit_location}. Around {attacker_name}, the crowd noise slowly fills back in."
        },
        {
            'attacker_msg': "The charge ends the argument mid-syllable. {target_name}'s {hit_location} never gets to finish anything again.",
            'victim_msg': "It ends mid-syllable — yours — with the charge in your {hit_location}.",
            'observer_msg': "The charge from {attacker_name} ends it mid-syllable. {target_name} doesn't finish."
        },
        {
            'attacker_msg': "You fire, {target_name} stops being a subject, and somewhere in your log a field flips from ACTIVE to CLOSED.",
            'victim_msg': "The last thing that happens to you is administrative.",
            'observer_msg': "{attacker_name} fires and {target_name} drops. Whatever the machine records, it records it already moving on."
        },
    ],
}
