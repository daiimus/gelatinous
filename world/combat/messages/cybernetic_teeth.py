"""Cybernetic teeth (Jawz) combat messages — the bite of alloy fangs.

Natural-weapon message set for the `cybernetic_teeth` weapon type
(#525).  Fired when a character with deployed Jawz fangs attacks.
The fangs are never held — combat resolves them via natural-weapon
precedence — so prose treats the mouth itself as the weapon.

Phases mirror the house structure: initiate / hit / miss / kill,
each a list of ``{attacker_msg, victim_msg, observer_msg}`` dicts.
"""

MESSAGES = {
    "initiate": [
        {
            'attacker_msg': "Your jaw flexes and the alloy fangs slide down with a wet click. You bare them at {target_name}.",
            'victim_msg': "{attacker_name}'s jaw flexes and alloy fangs slide down with a wet click, bared at you.",
            'observer_msg': "{attacker_name}'s jaw flexes and alloy fangs slide down with a wet click, bared at {target_name}."
        },
        {
            'attacker_msg': "You roll your shoulders, drop your chin, and let {target_name} get a good look at what's in your mouth now.",
            'victim_msg': "{attacker_name} drops their chin and gives you a good look at what's in their mouth now.",
            'observer_msg': "{attacker_name} drops their chin and shows {target_name} what's in their mouth now."
        },
        {
            'attacker_msg': "A thread of saliva strings between the fangs as you grin wide and wrong at {target_name}.",
            'victim_msg': "A thread of saliva strings between {attacker_name}'s fangs as they grin wide and wrong at you.",
            'observer_msg': "A thread of saliva strings between {attacker_name}'s fangs as they grin wide and wrong at {target_name}."
        },
        {
            'attacker_msg': "Servos hum along your jaw as it sets wider than a jaw should. You stalk toward {target_name}, mouth first.",
            'victim_msg': "Servos hum as {attacker_name}'s jaw sets wider than a jaw should. They come at you mouth first.",
            'observer_msg': "Servos hum as {attacker_name}'s jaw sets too wide, and they stalk toward {target_name} mouth first."
        },
        {
            'attacker_msg': "You snap the fangs together once — a hard metal clack — just so {target_name} knows the sound.",
            'victim_msg': "{attacker_name} snaps their fangs together once, a hard metal clack, just so you know the sound.",
            'observer_msg': "{attacker_name} snaps their fangs together once, a hard metal clack, for {target_name}'s benefit."
        },
        {
            'attacker_msg': "No knife, no fists. You just open your mouth at {target_name} and let the implication land.",
            'victim_msg': "No knife, no fists. {attacker_name} just opens their mouth at you and lets the implication land.",
            'observer_msg': "No knife, no fists — {attacker_name} just opens their mouth at {target_name} and lets it land."
        },
        {
            'attacker_msg': "You lower your head, fangs catching the light, and close the distance to {target_name} like something that hunts.",
            'victim_msg': "{attacker_name} lowers their head, fangs catching the light, and closes on you like something that hunts.",
            'observer_msg': "{attacker_name} lowers their head, fangs catching the light, and closes on {target_name} like something that hunts."
        },
        {
            'attacker_msg': "Your tongue runs along the alloy edges. You decide where on {target_name} you want to start.",
            'victim_msg': "{attacker_name}'s tongue runs along the alloy edges as they decide where on you to start.",
            'observer_msg': "{attacker_name}'s tongue runs along the alloy edges as they size {target_name} up."
        },
        {
            'attacker_msg': "The fangs lock into firing position with a tiny ratchet. You smile at {target_name} without any warmth in it.",
            'victim_msg': "Something ratchets in {attacker_name}'s jaw. They smile at you with no warmth in it at all.",
            'observer_msg': "Something ratchets in {attacker_name}'s jaw and they smile at {target_name} with no warmth in it."
        },
        {
            'attacker_msg': "You breathe out slow through bared fangs, fogging the air, and fix {target_name} with a predator's patience.",
            'victim_msg': "{attacker_name} breathes out slow through bared fangs and fixes you with a predator's patience.",
            'observer_msg': "{attacker_name} breathes out slow through bared fangs and fixes {target_name} with a predator's patience."
        },
        {
            'attacker_msg': "You crack your neck, and the fangs ride the motion, gleaming. {target_name} is close enough to bite.",
            'victim_msg': "{attacker_name} cracks their neck, fangs gleaming with the motion. You're close enough to bite.",
            'observer_msg': "{attacker_name} cracks their neck, fangs gleaming, close enough to bite {target_name}."
        },
        {
            'attacker_msg': "Your mouth opens too far, jaw unhinging on its actuators, and you aim all of it at {target_name}.",
            'victim_msg': "{attacker_name}'s mouth opens too far, jaw unhinging on its actuators, all of it aimed at you.",
            'observer_msg': "{attacker_name}'s mouth opens too far, jaw unhinging, all of it aimed at {target_name}."
        },
        {
            'attacker_msg': "You let {target_name} hear the soft whine of the gum-line motors before you ever move.",
            'victim_msg': "{attacker_name} lets you hear the soft whine of gum-line motors before they ever move.",
            'observer_msg': "{attacker_name} lets {target_name} hear the soft whine of gum-line motors before moving."
        },
        {
            'attacker_msg': "You spread your arms wide and your mouth wider, inviting {target_name} into range.",
            'victim_msg': "{attacker_name} spreads their arms wide and their mouth wider, inviting you into range.",
            'observer_msg': "{attacker_name} spreads their arms wide and their mouth wider, inviting {target_name} in."
        },
        {
            'attacker_msg': "There's nothing clever about it. You're going to bite {target_name}, and you let them watch you decide it.",
            'victim_msg': "There's nothing clever about it. {attacker_name} is going to bite you, and they let you watch them decide.",
            'observer_msg': "There's nothing clever about it. {attacker_name} means to bite {target_name}, and lets them watch the decision."
        },
    ],
    "hit": [
        {
            'attacker_msg': "You lunge and clamp down on {target_name}'s {hit_location}, fangs punching through to lock, and you *pull*.",
            'victim_msg': "{attacker_name} lunges and clamps onto your {hit_location}, fangs punching through to lock, and pulls.",
            'observer_msg': "{attacker_name} lunges and clamps onto {target_name}'s {hit_location}, fangs locking, and pulls."
        },
        {
            'attacker_msg': "Your jaw closes on {target_name}'s {hit_location} with a hydraulic crunch; the fangs meet somewhere they shouldn't.",
            'victim_msg': "{attacker_name}'s jaw closes on your {hit_location} with a hydraulic crunch, fangs meeting somewhere they shouldn't.",
            'observer_msg': "{attacker_name}'s jaw closes on {target_name}'s {hit_location} with a hydraulic crunch."
        },
        {
            'attacker_msg': "You tear a mouthful from {target_name}'s {hit_location} and spit the rest aside, fangs slick to the gum.",
            'victim_msg': "{attacker_name} tears a mouthful from your {hit_location} and spits the rest aside.",
            'observer_msg': "{attacker_name} tears a mouthful from {target_name}'s {hit_location} and spits the rest aside."
        },
        {
            'attacker_msg': "The fangs sink into {target_name}'s {hit_location} and grind; you feel them scrape something hard underneath.",
            'victim_msg': "{attacker_name}'s fangs sink into your {hit_location} and grind against something hard underneath.",
            'observer_msg': "{attacker_name}'s fangs sink into {target_name}'s {hit_location} and grind audibly."
        },
        {
            'attacker_msg': "You snap forward, catch {target_name}'s {hit_location}, and worry it like a dog with a sleeve until it gives.",
            'victim_msg': "{attacker_name} snaps forward, catches your {hit_location}, and worries it like a dog with a sleeve.",
            'observer_msg': "{attacker_name} snaps forward, catches {target_name}'s {hit_location}, and worries it until it gives."
        },
        {
            'attacker_msg': "Fang meets {target_name}'s {hit_location} and your jaw motors whine as they bite past resistance into wet.",
            'victim_msg': "Fangs meet your {hit_location} and {attacker_name}'s jaw motors whine, biting past resistance into wet.",
            'observer_msg': "Fangs meet {target_name}'s {hit_location} and {attacker_name}'s jaw motors whine biting through."
        },
        {
            'attacker_msg': "You drive in chin-first and the alloy points stitch a ragged crescent across {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name} drives in chin-first and alloy points stitch a ragged crescent across your {hit_location}.",
            'observer_msg': "{attacker_name} drives in chin-first, stitching a ragged crescent across {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Your bite lands on {target_name}'s {hit_location} and locks; the more they pull, the deeper the fangs set.",
            'victim_msg': "{attacker_name}'s bite lands on your {hit_location} and locks — the more you pull, the deeper it sets.",
            'observer_msg': "{attacker_name}'s bite locks on {target_name}'s {hit_location}; their struggling only sets it deeper."
        },
        {
            'attacker_msg': "You shake your head hard with {target_name}'s {hit_location} between your fangs, and something tears loose.",
            'victim_msg': "{attacker_name} shakes their head hard with your {hit_location} between their fangs, and something tears loose.",
            'observer_msg': "{attacker_name} shakes their head hard with {target_name}'s {hit_location} between the fangs; something tears loose."
        },
        {
            'attacker_msg': "The fangs punch twin rows of holes into {target_name}'s {hit_location} and drag down before they pull free.",
            'victim_msg': "{attacker_name}'s fangs punch twin rows of holes into your {hit_location} and drag down before pulling free.",
            'observer_msg': "{attacker_name}'s fangs punch twin rows into {target_name}'s {hit_location} and drag before pulling free."
        },
        {
            'attacker_msg': "You bite, the jaw actuators max out, and {target_name}'s {hit_location} crunches in your mouth like gristle.",
            'victim_msg': "{attacker_name} bites, jaw actuators maxing out, and your {hit_location} crunches in their mouth like gristle.",
            'observer_msg': "{attacker_name} bites, jaw actuators maxing, and {target_name}'s {hit_location} crunches like gristle."
        },
        {
            'attacker_msg': "Blood sheets down your chin as you wrench your fangs out of {target_name}'s {hit_location}, taking a ribbon with them.",
            'victim_msg': "Blood sheets down {attacker_name}'s chin as they wrench their fangs out of your {hit_location}, taking a ribbon along.",
            'observer_msg': "Blood sheets down {attacker_name}'s chin as they wrench their fangs from {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "You catch {target_name}'s {hit_location} in a quick snapping bite, fangs clicking shut a hair from the bone.",
            'victim_msg': "{attacker_name} catches your {hit_location} in a quick snapping bite, fangs clicking shut near the bone.",
            'observer_msg': "{attacker_name} catches {target_name}'s {hit_location} in a quick snapping bite, fangs clicking shut."
        },
        {
            'attacker_msg': "Your fangs rake across {target_name}'s {hit_location} and leave four parallel furrows welling dark.",
            'victim_msg': "{attacker_name}'s fangs rake across your {hit_location} and leave four parallel furrows welling dark.",
            'observer_msg': "{attacker_name}'s fangs rake across {target_name}'s {hit_location}, leaving four furrows welling dark."
        },
        {
            'attacker_msg': "You clamp on and don't let go; {target_name}'s {hit_location} is yours until you decide otherwise.",
            'victim_msg': "{attacker_name} clamps on and doesn't let go; your {hit_location} is theirs until they decide otherwise.",
            'observer_msg': "{attacker_name} clamps on and doesn't let go; {target_name}'s {hit_location} is theirs to keep."
        },
    ],
    "miss": [
        {
            'attacker_msg': "Your fangs snap shut on the air a hand's width from {target_name}, the clack loud and hollow.",
            'victim_msg': "{attacker_name}'s fangs snap shut a hand's width from you, the clack loud and hollow.",
            'observer_msg': "{attacker_name}'s fangs snap shut a hand's width from {target_name}, loud and hollow."
        },
        {
            'attacker_msg': "{target_name} jerks back and your bite closes on nothing but the memory of where they were.",
            'victim_msg': "You jerk back and {attacker_name}'s bite closes on nothing but where you were.",
            'observer_msg': "{target_name} jerks back and {attacker_name}'s bite closes on empty air."
        },
        {
            'attacker_msg': "You lunge too far, overbalance on the unhinged jaw, and {target_name} slips the snap entirely.",
            'victim_msg': "{attacker_name} lunges too far, overbalances on that unhinged jaw, and you slip the snap.",
            'observer_msg': "{attacker_name} lunges too far, overbalances, and {target_name} slips the snap."
        },
        {
            'attacker_msg': "The fangs scrape down {target_name}'s sleeve without finding skin, shedding sparks off a stud.",
            'victim_msg': "{attacker_name}'s fangs scrape down your sleeve without finding skin, shedding sparks off a stud.",
            'observer_msg': "{attacker_name}'s fangs scrape down {target_name}'s sleeve, shedding sparks off a stud."
        },
        {
            'attacker_msg': "You snap at {target_name}'s throat and get a fistful of jacket collar instead, alloy tearing fabric.",
            'victim_msg': "{attacker_name} snaps at your throat and gets your collar instead, alloy tearing fabric.",
            'observer_msg': "{attacker_name} snaps at {target_name}'s throat and gets a mouthful of collar, fabric tearing."
        },
        {
            'attacker_msg': "Your jaw motors whine to full clamp and shut on nothing; {target_name} is already two steps gone.",
            'victim_msg': "{attacker_name}'s jaw motors whine to full clamp on nothing; you're already two steps gone.",
            'observer_msg': "{attacker_name}'s jaw clamps on nothing; {target_name} is already two steps gone."
        },
        {
            'attacker_msg': "You bite where {target_name}'s arm should be and find only the wind of their dodge.",
            'victim_msg': "{attacker_name} bites where your arm should be and finds only the wind of your dodge.",
            'observer_msg': "{attacker_name} bites where {target_name}'s arm was and finds only wind."
        },
        {
            'attacker_msg': "Saliva flies as your fangs snap and miss; {target_name} grimaces and steps off the line.",
            'victim_msg': "Saliva flies as {attacker_name}'s fangs snap and miss; you grimace and step off the line.",
            'observer_msg': "Saliva flies as {attacker_name}'s fangs snap and miss; {target_name} steps off the line."
        },
        {
            'attacker_msg': "You overcommit the lunge and clack your fangs off your own shoulder reaching for {target_name}.",
            'victim_msg': "{attacker_name} overcommits and clacks their fangs off their own shoulder reaching for you.",
            'observer_msg': "{attacker_name} overcommits and clacks their fangs off their own shoulder reaching for {target_name}."
        },
        {
            'attacker_msg': "The bite goes high. Your fangs whistle past {target_name}'s ear close enough to part hair.",
            'victim_msg': "The bite goes high. {attacker_name}'s fangs whistle past your ear close enough to part hair.",
            'observer_msg': "The bite goes high — {attacker_name}'s fangs whistle past {target_name}'s ear."
        },
        {
            'attacker_msg': "{target_name} shoves your forehead back one-handed and your jaw clamps shut on empty space.",
            'victim_msg': "You shove {attacker_name}'s forehead back one-handed and their jaw clamps shut on empty space.",
            'observer_msg': "{target_name} shoves {attacker_name}'s forehead back and the jaw clamps on empty space."
        },
        {
            'attacker_msg': "You snap, miss, and the recoil of the empty bite rocks your whole head back.",
            'victim_msg': "{attacker_name} snaps, misses, and the recoil of the empty bite rocks their whole head back.",
            'observer_msg': "{attacker_name} snaps, misses, and the empty bite rocks their head back."
        },
        {
            'attacker_msg': "Your fangs gouge a chunk out of the wall behind where {target_name} just stood.",
            'victim_msg': "{attacker_name}'s fangs gouge a chunk out of the wall behind where you just stood.",
            'observer_msg': "{attacker_name}'s fangs gouge a chunk out of the wall behind {target_name}."
        },
        {
            'attacker_msg': "You go for the bite and {target_name} pivots inside it, leaving your fangs to close on the dark.",
            'victim_msg': "{attacker_name} goes for the bite and you pivot inside it, leaving the fangs to close on dark.",
            'observer_msg': "{attacker_name} goes for the bite and {target_name} pivots inside it; the fangs close on dark."
        },
        {
            'attacker_msg': "The snap is fast but {target_name} is faster; your fangs meet each other with a frustrated clack.",
            'victim_msg': "The snap is fast but you're faster; {attacker_name}'s fangs meet each other with a frustrated clack.",
            'observer_msg': "The snap is fast but {target_name} is faster; {attacker_name}'s fangs clack on nothing."
        },
    ],
    "kill": [
        {
            'attacker_msg': "You clamp onto {target_name}'s throat and don't let go until the thrashing stops and the weight goes slack.",
            'victim_msg': "{attacker_name} clamps onto your throat and the thrashing is the last thing you do.",
            'observer_msg': "{attacker_name} clamps onto {target_name}'s throat and holds until the thrashing stops and the weight goes slack."
        },
        {
            'attacker_msg': "Your fangs find {target_name}'s {hit_location} and tear it open; they're gone before they hit the ground, and you're still chewing.",
            'victim_msg': "{attacker_name}'s fangs tear your {hit_location} open, and the ground comes up before anything else can.",
            'observer_msg': "{attacker_name}'s fangs tear {target_name}'s {hit_location} open; they're gone before they land, and {attacker_name} is still chewing."
        },
        {
            'attacker_msg': "One bite, jaw to the bone, and you take enough of {target_name}'s neck that the rest of them simply stops.",
            'victim_msg': "One bite, jaw to the bone, and enough of your neck is gone that the rest of you simply stops.",
            'observer_msg': "One bite, jaw to the bone, and {attacker_name} takes enough of {target_name}'s neck that the rest stops."
        },
        {
            'attacker_msg': "You bite down and wrench, and {target_name} comes apart at the {hit_location} in a way that ends the fight forever.",
            'victim_msg': "{attacker_name} bites down and wrenches, and you come apart at the {hit_location} in a way that ends everything.",
            'observer_msg': "{attacker_name} bites down and wrenches; {target_name} comes apart at the {hit_location} for good."
        },
        {
            'attacker_msg': "The fangs lock on {target_name}'s {hit_location} and your jaw motors do the rest, grinding until they go limp.",
            'victim_msg': "The fangs lock on your {hit_location} and {attacker_name}'s jaw motors grind until you go limp.",
            'observer_msg': "The fangs lock on {target_name}'s {hit_location} and {attacker_name}'s jaw grinds until they go limp."
        },
        {
            'attacker_msg': "You drag {target_name} down by the bite and pin them with your mouth until the struggling becomes nothing.",
            'victim_msg': "{attacker_name} drags you down by the bite and pins you with their mouth until the struggling becomes nothing.",
            'observer_msg': "{attacker_name} drags {target_name} down by the bite and pins them until the struggling stops."
        },
        {
            'attacker_msg': "Your bite crushes {target_name}'s windpipe flat. They mouth something with no air behind it and fold.",
            'victim_msg': "{attacker_name}'s bite crushes your windpipe flat. You mouth something with no air behind it and fold.",
            'observer_msg': "{attacker_name}'s bite crushes {target_name}'s windpipe flat; they mouth nothing and fold."
        },
        {
            'attacker_msg': "You open {target_name}'s {hit_location} with a single savage bite and let them spill out onto the floor.",
            'victim_msg': "{attacker_name} opens your {hit_location} with a single savage bite and lets you spill onto the floor.",
            'observer_msg': "{attacker_name} opens {target_name}'s {hit_location} with one savage bite and lets them spill out."
        },
        {
            'attacker_msg': "The last thing you take from {target_name} is between your fangs. You spit it out next to the body.",
            'victim_msg': "The last thing {attacker_name} takes from you is between their fangs. The dark comes after.",
            'observer_msg': "{attacker_name} spits the last of {target_name} out beside the body."
        },
        {
            'attacker_msg': "You bite through to whatever holds {target_name} together, and it stops holding. They drop like cut strings.",
            'victim_msg': "{attacker_name} bites through whatever holds you together, and it stops holding. You drop like cut strings.",
            'observer_msg': "{attacker_name} bites through whatever held {target_name} together; they drop like cut strings."
        },
        {
            'attacker_msg': "Your fangs meet in the middle of {target_name}'s throat. There is a wet finality to the sound, and then quiet.",
            'victim_msg': "{attacker_name}'s fangs meet in the middle of your throat. There's a wet finality, and then quiet.",
            'observer_msg': "{attacker_name}'s fangs meet in the middle of {target_name}'s throat — a wet finality, then quiet."
        },
        {
            'attacker_msg': "You shake {target_name} by the {hit_location} one final time and let the limp weight fall where it will.",
            'victim_msg': "{attacker_name} shakes you by the {hit_location} one final time and lets the limp weight fall.",
            'observer_msg': "{attacker_name} shakes {target_name} by the {hit_location} a final time and lets the weight fall."
        },
        {
            'attacker_msg': "Jaw locked, you ride {target_name} to the ground and stay clamped until long after it matters.",
            'victim_msg': "Jaw locked, {attacker_name} rides you to the ground and stays clamped until long after it matters.",
            'observer_msg': "Jaw locked, {attacker_name} rides {target_name} to the ground and stays clamped long after it matters."
        },
        {
            'attacker_msg': "You bite once, deep and certain, and {target_name}'s eyes go to the middle distance and stay there.",
            'victim_msg': "{attacker_name} bites once, deep and certain, and the middle distance is the last thing you find.",
            'observer_msg': "{attacker_name} bites once, deep and certain, and {target_name}'s eyes go to the middle distance and stay."
        },
        {
            'attacker_msg': "Blood to the eyes, you lift your head off {target_name}'s ruined {hit_location} and let them slide off your fangs.",
            'victim_msg': "Blood everywhere, {attacker_name} lifts their head off your ruined {hit_location} and lets you slide off the fangs.",
            'observer_msg': "Blood to the eyes, {attacker_name} lifts their head off {target_name}'s ruined {hit_location} and lets them slide free."
        },
    ],
}
