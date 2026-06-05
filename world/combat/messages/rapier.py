"""
Combat messages for rapier weapons.

These messages support three perspectives:
- attacker_msg: Message shown to the person performing the action
- victim_msg: Message shown to the target of the action  
- observer_msg: Message shown to others observing the action

Messages emphasize the rapier's elegant precision, fencing artistry, and deadly finesse.
"""

MESSAGES = {
    "initiate": [
        {
            'attacker_msg': "You draw the slender rapier, its needle point glinting with deadly promise.",
            'victim_msg': "{attacker_name} draws the slender rapier, its needle point glinting with deadly promise.",
            'observer_msg': "{attacker_name} draws the slender rapier, its needle point glinting with deadly promise."
        },
        {
            'attacker_msg': "With a flick of the wrist, you bring the rapier on guard, its elegant form belying its lethality.",
            'victim_msg': "With a flick of the wrist, {attacker_name} brings the rapier on guard, its elegant form belying its lethality.",
            'observer_msg': "With a flick of the wrist, {attacker_name} brings the rapier on guard, its elegant form belying its lethality."
        },
        {
            'attacker_msg': "You test the rapier's flex, the thin blade quivering, eager for a thrust.",
            'victim_msg': "{attacker_name} tests the rapier's flex, the thin blade quivering, eager for a thrust.",
            'observer_msg': "{attacker_name} tests the rapier's flex, the thin blade quivering, eager for a thrust."
        },
        {
            'attacker_msg': "The rapier flashes in your {hit_location}, a silver sliver ready to dance.",
            'victim_msg': "The rapier flashes in {attacker_name}'s hand, a silver sliver ready to dance.",
            'observer_msg': "The rapier flashes in {attacker_name}'s hand, a silver sliver ready to dance."
        },
        {
            'attacker_msg': "You adopt a fencer's stance, the rapier an extension of your focused will.",
            'victim_msg': "{attacker_name} adopts a fencer's stance, the rapier an extension of their focused will.",
            'observer_msg': "{attacker_name} adopts a fencer's stance, the rapier an extension of their focused will."
        },
        {
            'attacker_msg': "A soft *shing* as the rapier clears its sheath, its polished surface reflecting your intent.",
            'victim_msg': "A soft *shing* as the rapier clears its sheath, its polished surface reflecting {attacker_name}'s intent.",
            'observer_msg': "A soft *shing* as the rapier clears its sheath, its polished surface reflecting {attacker_name}'s intent."
        },
        {
            'attacker_msg': "You trace a quick, almost invisible circle with the rapier's tip, a duelist's greeting.",
            'victim_msg': "{attacker_name} traces a quick, almost invisible circle with the rapier's tip, a duelist's greeting.",
            'observer_msg': "{attacker_name} traces a quick, almost invisible circle with the rapier's tip, a duelist's greeting."
        },
        {
            'attacker_msg': "Light dances along the rapier's narrow blade as you prepare for the engagement.",
            'victim_msg': "Light dances along the rapier's narrow blade as {attacker_name} prepares for the engagement.",
            'observer_msg': "Light dances along the rapier's narrow blade as {attacker_name} prepares for the engagement."
        },
        {
            'attacker_msg': "You offer a precise salute with the rapier, then settle into a poised stance.",
            'victim_msg': "{attacker_name} offers a precise salute with the rapier, then settles into a poised stance.",
            'observer_msg': "{attacker_name} offers a precise salute with the rapier, then settles into a poised stance."
        },
        {
            'attacker_msg': "The rapier is held with a light but firm grip, you ready for swift, darting attacks.",
            'victim_msg': "The rapier is held with a light but firm grip, {attacker_name} ready for swift, darting attacks.",
            'observer_msg': "The rapier is held with a light but firm grip, {attacker_name} ready for swift, darting attacks."
        },
        {
            'attacker_msg': "You make a few practice lunges, the rapier a blur of motion.",
            'victim_msg': "{attacker_name} makes a few practice lunges, the rapier a blur of motion.",
            'observer_msg': "{attacker_name} makes a few practice lunges, the rapier a blur of motion."
        },
        {
            'attacker_msg': "The air around the rapier seems to sharpen as you focus on {target_name}.",
            'victim_msg': "The air around the rapier seems to sharpen as {attacker_name} focuses on you.",
            'observer_msg': "The air around the rapier seems to sharpen as {attacker_name} focuses on {target_name}."
        },
        {
            'attacker_msg': "Your eyes are like chips of ice, sighting down the length of the poised rapier.",
            'victim_msg': "{attacker_name}'s eyes are like chips of ice, sighting down the length of the poised rapier.",
            'observer_msg': "{attacker_name}'s eyes are like chips of ice, sighting down the length of the poised rapier."
        },
        {
            'attacker_msg': "The rapier feels alive in your {hit_location}, a delicate instrument of deadly precision.",
            'victim_msg': "The rapier feels alive in {attacker_name}'s hand, a delicate instrument of deadly precision.",
            'observer_msg': "The rapier feels alive in {attacker_name}'s hand, a delicate instrument of deadly precision."
        },
        {
            'attacker_msg': "You shift your weight, the rapier held ready for an explosive lunge.",
            'victim_msg': "{attacker_name} shifts their weight, the rapier held ready for an explosive lunge.",
            'observer_msg': "{attacker_name} shifts their weight, the rapier held ready for an explosive lunge."
        },
        {
            'attacker_msg': "A subtle glint from the cup-hilt of your rapier is the only warning given.",
            'victim_msg': "A subtle glint from the cup-hilt of {attacker_name}'s rapier is the only warning given.",
            'observer_msg': "A subtle glint from the cup-hilt of {attacker_name}'s rapier is the only warning given."
        },
        {
            'attacker_msg': "You hold the rapier in a high, elegant guard, inviting {target_name} to make the first mistake.",
            'victim_msg': "{attacker_name} holds the rapier in a high, elegant guard, inviting you to make the first mistake.",
            'observer_msg': "{attacker_name} holds the rapier in a high, elegant guard, inviting {target_name} to make the first mistake."
        },
        {
            'attacker_msg': "The ornate pommel of the rapier is cool against your palm, a counterpoint to the blade's heat.",
            'victim_msg': "The ornate pommel of the rapier is cool against {attacker_name}'s palm, a counterpoint to the blade's heat.",
            'observer_msg': "The ornate pommel of the rapier is cool against {attacker_name}'s palm, a counterpoint to the blade's heat."
        },
        {
            'attacker_msg': "You let the rapier's point dip, a subtle invitation to a deadly dance.",
            'victim_msg': "{attacker_name} lets the rapier's point dip, a subtle invitation to a deadly dance.",
            'observer_msg': "{attacker_name} lets the rapier's point dip, a subtle invitation to a deadly dance."
        },
        {
            'attacker_msg': "With a nearly silent breath, you commit, the rapier leading your every move.",
            'victim_msg': "With a nearly silent breath, {attacker_name} commits, the rapier leading their every move.",
            'observer_msg': "With a nearly silent breath, {attacker_name} commits, the rapier leading their every move."
        },
        {
            'attacker_msg': "You slide the rapier free, the sound a barely audible whisper of polished steel.",
            'victim_msg': "{attacker_name} slides the rapier free, the sound a barely audible whisper of polished steel.",
            'observer_msg': "{attacker_name} slides the rapier free, the sound a barely audible whisper of polished steel."
        },
        {
            'attacker_msg': "The rapier is a surgeon's tool in your skilled hand, ready for precise incisions.",
            'victim_msg': "The rapier is a surgeon's tool in {attacker_name}'s skilled hand, ready for precise incisions.",
            'observer_msg': "The rapier is a surgeon's tool in {attacker_name}'s skilled hand, ready for precise incisions."
        },
        {
            'attacker_msg': "You present the rapier, its slender blade aimed directly at {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name} presents the rapier, its slender blade aimed directly at your {hit_location}.",
            'observer_msg': "{attacker_name} presents the rapier, its slender blade aimed directly at {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "A fencer's grace, a killer's intent; you and the rapier are perfectly matched.",
            'victim_msg': "A fencer's grace, a killer's intent; {attacker_name} and the rapier are perfectly matched.",
            'observer_msg': "A fencer's grace, a killer's intent; {attacker_name} and the rapier are perfectly matched."
        },
        {
            'attacker_msg': "Your grip on the rapier's wire-bound hilt is sure and steady.",
            'victim_msg': "{attacker_name}'s grip on the rapier's wire-bound hilt is sure and steady.",
            'observer_msg': "{attacker_name}'s grip on the rapier's wire-bound hilt is sure and steady."
        },
        {
            'attacker_msg': "The rapier cuts a thin, almost invisible line as you prepare your opening.",
            'victim_msg': "The rapier cuts a thin, almost invisible line as {attacker_name} prepares their opening.",
            'observer_msg': "The rapier cuts a thin, almost invisible line as {attacker_name} prepares their opening."
        },
        {
            'attacker_msg': "You seem to glide into position, the rapier an integral part of your fluid motion.",
            'victim_msg': "{attacker_name} seems to glide into position, the rapier an integral part of their fluid motion.",
            'observer_msg': "{attacker_name} seems to glide into position, the rapier an integral part of their fluid motion."
        },
        {
            'attacker_msg': "The silence is punctuated only by the faint *tap-tap* of you adjusting the rapier's point.",
            'victim_msg': "The silence is punctuated only by the faint *tap-tap* of {attacker_name} adjusting the rapier's point.",
            'observer_msg': "The silence is punctuated only by the faint *tap-tap* of {attacker_name} adjusting the rapier's point."
        },
        {
            'attacker_msg': "The rapier is a declaration of skill over brute force, and you wield it with confidence.",
            'victim_msg': "The rapier is a declaration of skill over brute force, and {attacker_name} wields it with confidence.",
            'observer_msg': "The rapier is a declaration of skill over brute force, and {attacker_name} wields it with confidence."
        },
        {
            'attacker_msg': "You take a measured breath, the scent of fine steel and leather from the rapier's fittings.",
            'victim_msg': "{attacker_name} takes a measured breath, the scent of fine steel and leather from the rapier's fittings.",
            'observer_msg': "{attacker_name} takes a measured breath, the scent of fine steel and leather from the rapier's fittings."
        }
    ],
    "hit": [
        {
            'attacker_msg': "A lightning-fast lunge from you, and the rapier's point bites {target_name}'s {hit_location}.",
            'victim_msg': "A lightning-fast lunge from {attacker_name}, and the rapier's point bites your {hit_location}.",
            'observer_msg': "A lightning-fast lunge from {attacker_name}, and the rapier's point bites {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The rapier flashes, your thrust slipping past {target_name}'s guard to score a hit.",
            'victim_msg': "The rapier flashes, {attacker_name}'s thrust slipping past your guard to score a hit.",
            'observer_msg': "The rapier flashes, {attacker_name}'s thrust slipping past {target_name}'s guard to score a hit."
        },
        {
            'attacker_msg': "Your blade darts in, leaving a stinging red line on {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s blade darts in, leaving a stinging red line on your {hit_location}.",
            'observer_msg': "{attacker_name}'s blade darts in, leaving a stinging red line on {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Steel whispers as your rapier parries and ripostes, its tip finding {target_name}'s {hit_location}.",
            'victim_msg': "Steel whispers as {attacker_name}'s rapier parries and ripostes, its tip finding your {hit_location}.",
            'observer_msg': "Steel whispers as {attacker_name}'s rapier parries and ripostes, its tip finding {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The sharp point of the rapier pierces {target_name}'s {hit_location}, making them hiss in pain.",
            'victim_msg': "The sharp point of the rapier pierces your {hit_location}, making you hiss in pain.",
            'observer_msg': "The sharp point of the rapier pierces {target_name}'s {hit_location}, making them hiss in pain."
        },
        {
            'attacker_msg': "Your precise attack connects, the rapier finding an opening in {target_name}'s defense.",
            'victim_msg': "{attacker_name}'s precise attack connects, the rapier finding an opening in your defense.",
            'observer_msg': "{attacker_name}'s precise attack connects, the rapier finding an opening in {target_name}'s defense."
        },
        {
            'attacker_msg': "A well-aimed feint, then your rapier darts out to prick {target_name}'s {hit_location}.",
            'victim_msg': "A well-aimed feint, then {attacker_name}'s rapier darts out to prick your {hit_location}.",
            'observer_msg': "A well-aimed feint, then {attacker_name}'s rapier darts out to prick {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The rapier's needle point finds a chink in {target_name}'s {hit_location}or, leaving a telling mark.",
            'victim_msg': "The rapier's needle point finds a chink in your {hit_location}or, leaving a telling mark.",
            'observer_msg': "The rapier's needle point finds a chink in {target_name}'s {hit_location}or, leaving a telling mark."
        },
        {
            'attacker_msg': "Your blade flickers like a serpent's tongue before striking {target_name}'s exposed {hit_location}.",
            'victim_msg': "{attacker_name}'s blade flickers like a serpent's tongue before striking your exposed {hit_location}.",
            'observer_msg': "{attacker_name}'s blade flickers like a serpent's tongue before striking {target_name}'s exposed {hit_location}."
        },
        {
            'attacker_msg': "With a subtle movement, you guide the rapier to {target_name}, forcing a pained retreat.",
            'victim_msg': "With a subtle movement, {attacker_name} guides the rapier to you, forcing a pained retreat.",
            'observer_msg': "With a subtle movement, {attacker_name} guides the rapier to {target_name}, forcing a pained retreat."
        },
        {
            'attacker_msg': "The rapier scores a hit on {target_name}'s weapon {hit_location}, a disarming touch.",
            'victim_msg': "The rapier scores a hit on your weapon {hit_location}, a disarming touch.",
            'observer_msg': "The rapier scores a hit on {target_name}'s weapon {hit_location}, a disarming touch."
        },
        {
            'attacker_msg': "Your precise thrust opens a small, bleeding wound on {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s precise thrust opens a small, bleeding wound on your {hit_location}.",
            'observer_msg': "{attacker_name}'s precise thrust opens a small, bleeding wound on {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "A sharp *tink* as your rapier finds a gap, the point jarring against {target_name}.",
            'victim_msg': "A sharp *tink* as {attacker_name}'s rapier finds a gap, the point jarring against you.",
            'observer_msg': "A sharp *tink* as {attacker_name}'s rapier finds a gap, the point jarring against {target_name}."
        },
        {
            'attacker_msg': "The keen blade of the rapier leaves a swift, clean cut along {target_name}'s {hit_location}.",
            'victim_msg': "The keen blade of the rapier leaves a swift, clean cut along your {hit_location}.",
            'observer_msg': "The keen blade of the rapier leaves a swift, clean cut along {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Your follow-up lunge with the rapier catches {target_name} as they recoil.",
            'victim_msg': "{attacker_name}'s follow-up lunge with the rapier catches you as you recoil.",
            'observer_msg': "{attacker_name}'s follow-up lunge with the rapier catches {target_name} as they recoil."
        },
        {
            'attacker_msg': "A flick of your {hit_location} sends the rapier's tip into {target_name}'s exposed {hit_location}.",
            'victim_msg': "A flick of {attacker_name}'s {hit_location} sends the rapier's tip into your exposed {hit_location}.",
            'observer_msg': "A flick of {attacker_name}'s {hit_location} sends the rapier's tip into {target_name}'s exposed {hit_location}."
        },
        {
            'attacker_msg': "The rapier sings its deadly tune as it connects with {target_name}, drawing a bead of blood.",
            'victim_msg': "The rapier sings its deadly tune as it connects with you, drawing a bead of blood.",
            'observer_msg': "The rapier sings its deadly tune as it connects with {target_name}, drawing a bead of blood."
        },
        {
            'attacker_msg': "Your blade finds its mark, leaving a painful puncture on {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s blade finds its mark, leaving a painful puncture on your {hit_location}.",
            'observer_msg': "{attacker_name}'s blade finds its mark, leaving a painful puncture on {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "A glancing blow from the rapier still manages to tear fabric and draw blood from {target_name}.",
            'victim_msg': "A glancing blow from the rapier still manages to tear fabric and draw blood from you.",
            'observer_msg': "A glancing blow from the rapier still manages to tear fabric and draw blood from {target_name}."
        },
        {
            'attacker_msg': "You press the advantage, the rapier a continuous, probing threat that finally lands on {target_name}.",
            'victim_msg': "{attacker_name} presses the advantage, the rapier a continuous, probing threat that finally lands on you.",
            'observer_msg': "{attacker_name} presses the advantage, the rapier a continuous, probing threat that finally lands on {target_name}."
        },
        {
            'attacker_msg': "The rapier's edge meets flesh, and {target_name} flinches from the sudden, sharp pain.",
            'victim_msg': "The rapier's edge meets flesh, and you flinch from the sudden, sharp pain.",
            'observer_msg': "The rapier's edge meets flesh, and {target_name} flinches from the sudden, sharp pain."
        },
        {
            'attacker_msg': "Your thrust is perfectly aimed, the rapier's point striking {target_name} with precision.",
            'victim_msg': "{attacker_name}'s thrust is perfectly aimed, the rapier's point striking you with precision.",
            'observer_msg': "{attacker_name}'s thrust is perfectly aimed, the rapier's point striking {target_name} with precision."
        },
        {
            'attacker_msg': "A quick disengage and thrust from your rapier impacts {target_name}'s {hit_location}.",
            'victim_msg': "A quick disengage and thrust from {attacker_name}'s rapier impacts your {hit_location}.",
            'observer_msg': "A quick disengage and thrust from {attacker_name}'s rapier impacts {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The rapier dances in your grip, its point finding an unguarded spot on {target_name}.",
            'victim_msg': "The rapier dances in {attacker_name}'s grip, its point finding an unguarded spot on you.",
            'observer_msg': "The rapier dances in {attacker_name}'s grip, its point finding an unguarded spot on {target_name}."
        },
        {
            'attacker_msg': "Your blade slides past {target_name}'s clumsy defense, leaving a stinging reminder.",
            'victim_msg': "{attacker_name}'s blade slides past your clumsy defense, leaving a stinging reminder.",
            'observer_msg': "{attacker_name}'s blade slides past {target_name}'s clumsy defense, leaving a stinging reminder."
        },
        {
            'attacker_msg': "A swift lunge with the rapier forces {target_name} {hit_location}, a new wound marking their retreat.",
            'victim_msg': "A swift lunge with the rapier forces you {hit_location}, a new wound marking your retreat.",
            'observer_msg': "A swift lunge with the rapier forces {target_name} {hit_location}, a new wound marking their retreat."
        },
        {
            'attacker_msg': "The tip of your rapier darts like a wasp, stinging {target_name}'s {hit_location}.",
            'victim_msg': "The tip of {attacker_name}'s rapier darts like a wasp, stinging your {hit_location}.",
            'observer_msg': "The tip of {attacker_name}'s rapier darts like a wasp, stinging {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Your rapier opens a thin cut on {target_name}'s {hit_location}, the steel cold and sharp.",
            'victim_msg': "{attacker_name}'s rapier opens a thin cut on your {hit_location}, the steel cold and sharp.",
            'observer_msg': "{attacker_name}'s rapier opens a thin cut on {target_name}'s {hit_location}, the steel cold and sharp."
        },
        {
            'attacker_msg': "A well-placed thrust from the rapier leaves {target_name} gasping from the sudden impact.",
            'victim_msg': "A well-placed thrust from the rapier leaves you gasping from the sudden impact.",
            'observer_msg': "A well-placed thrust from the rapier leaves {target_name} gasping from the sudden impact."
        },
        {
            'attacker_msg': "The rapier, guided by your finesse, inflicts a precise wound upon {target_name}.",
            'victim_msg': "The rapier, guided by {attacker_name}'s finesse, inflicts a precise wound upon you.",
            'observer_msg': "The rapier, guided by {attacker_name}'s finesse, inflicts a precise wound upon {target_name}."
        }
    ],
    "miss": [
        {
            'attacker_msg': "Your rapier thrusts past {target_name}'s ear, a hair's breadth from contact.",
            'victim_msg': "{attacker_name}'s rapier thrusts past your ear, a hair's breadth from contact.",
            'observer_msg': "{attacker_name}'s rapier thrusts past {target_name}'s ear, a hair's breadth from contact."
        },
        {
            'attacker_msg': "{target_name} sways aside, narrowly avoiding the lightning-fast lunge of your rapier.",
            'victim_msg': "You sway aside, narrowly avoiding the lightning-fast lunge of {attacker_name}'s rapier.",
            'observer_msg': "{target_name} sways aside, narrowly avoiding the lightning-fast lunge of {attacker_name}'s rapier."
        },
        {
            'attacker_msg': "The rapier's point sparks against a stone as your attack goes slightly awry.",
            'victim_msg': "The rapier's point sparks against a stone as {attacker_name}'s attack goes slightly awry.",
            'observer_msg': "The rapier's point sparks against a stone as {attacker_name}'s attack goes slightly awry."
        },
        {
            'attacker_msg': "A metallic *shriek* as your rapier is deflected by {target_name}'s desperate parry.",
            'victim_msg': "A metallic *shriek* as {attacker_name}'s rapier is deflected by your desperate parry.",
            'observer_msg': "A metallic *shriek* as {attacker_name}'s rapier is deflected by {target_name}'s desperate parry."
        },
        {
            'attacker_msg': "You overextend the lunge, the rapier's tip kissing the air harmlessly.",
            'victim_msg': "{attacker_name} overextends the lunge, the rapier's tip kissing the air harmlessly.",
            'observer_msg': "{attacker_name} overextends the lunge, the rapier's tip kissing the air harmlessly."
        },
        {
            'attacker_msg': "A clever feint from {target_name} makes your rapier thrust into empty space.",
            'victim_msg': "A clever feint from you makes {attacker_name}'s rapier thrust into empty space.",
            'observer_msg': "A clever feint from {target_name} makes {attacker_name}'s rapier thrust into empty space."
        },
        {
            'attacker_msg': "The rapier hums with frustrated energy as your swift attack misses.",
            'victim_msg': "The rapier hums with frustrated energy as {attacker_name}'s swift attack misses.",
            'observer_msg': "The rapier hums with frustrated energy as {attacker_name}'s swift attack misses."
        },
        {
            'attacker_msg': "Your thrust is met by a void as {target_name} nimbly dodges the rapier.",
            'victim_msg': "{attacker_name}'s thrust is met by a void as you nimbly dodge the rapier.",
            'observer_msg': "{attacker_name}'s thrust is met by a void as {target_name} nimbly dodges the rapier."
        },
        {
            'attacker_msg': "{target_name} ducks under the rapier's whistling path, the attack passing overhead.",
            'victim_msg': "You duck under the rapier's whistling path, the attack passing overhead.",
            'observer_msg': "{target_name} ducks under the rapier's whistling path, the attack passing overhead."
        },
        {
            'attacker_msg': "The rapier clatters against a shield, you momentarily losing the rhythm of attack.",
            'victim_msg': "The rapier clatters against a shield, {attacker_name} momentarily losing the rhythm of attack.",
            'observer_msg': "The rapier clatters against a shield, {attacker_name} momentarily losing the rhythm of attack."
        },
        {
            'attacker_msg': "Your blade passes through the afterimage of {target_name}'s swift movement.",
            'victim_msg': "{attacker_name}'s blade passes through the afterimage of your swift movement.",
            'observer_msg': "{attacker_name}'s blade passes through the afterimage of {target_name}'s swift movement."
        },
        {
            'attacker_msg': "A quick retreat from {target_name} leaves your rapier stabbing at nothing.",
            'victim_msg': "A quick retreat from you leaves {attacker_name}'s rapier stabbing at nothing.",
            'observer_msg': "A quick retreat from {target_name} leaves {attacker_name}'s rapier stabbing at nothing."
        },
        {
            'attacker_msg': "The rapier feels momentarily awkward in your grip as the intended blow fails.",
            'victim_msg': "The rapier feels momentarily awkward in {attacker_name}'s grip as the intended blow fails.",
            'observer_msg': "The rapier feels momentarily awkward in {attacker_name}'s grip as the intended blow fails."
        },
        {
            'attacker_msg': "You misjudge the range, the point of the rapier falling just short of {target_name}.",
            'victim_msg': "{attacker_name} misjudges the range, the point of the rapier falling just short of you.",
            'observer_msg': "{attacker_name} misjudges the range, the point of the rapier falling just short of {target_name}."
        },
        {
            'attacker_msg': "{target_name}'s footwork foils your attack, the rapier finding only air.",
            'victim_msg': "Your footwork foils {attacker_name}'s attack, the rapier finding only air.",
            'observer_msg': "{target_name}'s footwork foils {attacker_name}'s attack, the rapier finding only air."
        },
        {
            'attacker_msg': "The polished steel of the rapier reflects only your surprise as it misses.",
            'victim_msg': "The polished steel of the rapier reflects only {attacker_name}'s surprise as it misses.",
            'observer_msg': "The polished steel of the rapier reflects only {attacker_name}'s surprise as it misses."
        },
        {
            'attacker_msg': "You stumble a fraction, the momentum of the missed lunge almost unbalancing you.",
            'victim_msg': "{attacker_name} stumbles a fraction, the momentum of the missed lunge almost unbalancing them.",
            'observer_msg': "{attacker_name} stumbles a fraction, the momentum of the missed lunge almost unbalancing them."
        },
        {
            'attacker_msg': "A soft curse from you as your rapier attack is neatly sidestepped.",
            'victim_msg': "A soft curse from {attacker_name} as their rapier attack is neatly sidestepped.",
            'observer_msg': "A soft curse from {attacker_name} as their rapier attack is neatly sidestepped."
        },
        {
            'attacker_msg': "The rapier scores a thin line in the dirt beside {target_name}'s {hit_location}, but nothing more.",
            'victim_msg': "The rapier scores a thin line in the dirt beside your {hit_location}, but nothing more.",
            'observer_msg': "The rapier scores a thin line in the dirt beside {target_name}'s {hit_location}, but nothing more."
        },
        {
            'attacker_msg': "Your intricate combination with the rapier is read by {target_name}, who evades.",
            'victim_msg': "{attacker_name}'s intricate combination with the rapier is read by you, who evades.",
            'observer_msg': "{attacker_name}'s intricate combination with the rapier is read by {target_name}, who evades."
        },
        {
            'attacker_msg': "The air whispers around the rapier's edge, but {target_name} remains untouched by steel.",
            'victim_msg': "The air whispers around the rapier's edge, but you remain untouched by steel.",
            'observer_msg': "The air whispers around the rapier's edge, but {target_name} remains untouched by steel."
        },
        {
            'attacker_msg': "Your lunge is a fraction too slow, {target_name} already clear of the rapier's reach.",
            'victim_msg': "{attacker_name}'s lunge is a fraction too slow, you already clear of the rapier's reach.",
            'observer_msg': "{attacker_name}'s lunge is a fraction too slow, {target_name} already clear of the rapier's reach."
        },
        {
            'attacker_msg': "A last-second parry from {target_name} sends your rapier skittering wide.",
            'victim_msg': "A last-second parry from you sends {attacker_name}'s rapier skittering wide.",
            'observer_msg': "A last-second parry from {target_name} sends {attacker_name}'s rapier skittering wide."
        },
        {
            'attacker_msg': "The rapier's keen point finds nothing as {target_name} backpedals out of danger.",
            'victim_msg': "The rapier's keen point finds nothing as you backpedal out of danger.",
            'observer_msg': "The rapier's keen point finds nothing as {target_name} backpedals out of danger."
        },
        {
            'attacker_msg': "Your blade slices harmlessly past, a testament to {target_name}'s agility.",
            'victim_msg': "{attacker_name}'s blade slices harmlessly past, a testament to your agility.",
            'observer_msg': "{attacker_name}'s blade slices harmlessly past, a testament to {target_name}'s agility."
        },
        {
            'attacker_msg': "The rapier feels light and ineffective for a moment as you recover from the miss.",
            'victim_msg': "The rapier feels light and ineffective for a moment as {attacker_name} recovers from the miss.",
            'observer_msg': "The rapier feels light and ineffective for a moment as {attacker_name} recovers from the miss."
        },
        {
            'attacker_msg': "{target_name} weaves away from the probing tip of your rapier.",
            'victim_msg': "You weave away from the probing tip of {attacker_name}'s rapier.",
            'observer_msg': "{target_name} weaves away from the probing tip of {attacker_name}'s rapier."
        },
        {
            'attacker_msg': "Your attack is elegant but ultimately misses, the rapier finding no target.",
            'victim_msg': "{attacker_name}'s attack is elegant but ultimately misses, the rapier finding no target.",
            'observer_msg': "{attacker_name}'s attack is elegant but ultimately misses, the rapier finding no target."
        },
        {
            'attacker_msg': "The rapier sings a note of frustration as it fails to connect with {target_name}.",
            'victim_msg': "The rapier sings a note of frustration as it fails to connect with you.",
            'observer_msg': "The rapier sings a note of frustration as it fails to connect with {target_name}."
        },
        {
            'attacker_msg': "So close! Your rapier grazes {target_name}'s sleeve but fails to draw blood.",
            'victim_msg': "So close! {attacker_name}'s rapier grazes your sleeve but fails to draw blood.",
            'observer_msg': "So close! {attacker_name}'s rapier grazes {target_name}'s sleeve but fails to draw blood."
        }
    ],
    "kill": [
        {
            'attacker_msg': "Your rapier finds {target_name}'s {hit_location} with a single, perfect thrust, ending the duel.",
            'victim_msg': "{attacker_name}'s rapier finds your {hit_location} with a single, perfect thrust, ending the duel.",
            'observer_msg': "{attacker_name}'s rapier finds {target_name}'s {hit_location} with a single, perfect thrust, ending the duel."
        },
        {
            'attacker_msg': "A lightning lunge, and the rapier pierces a vital organ; {target_name} collapses, silenced.",
            'victim_msg': "A lightning lunge, and the rapier pierces a vital organ; you collapse, silenced.",
            'observer_msg': "A lightning lunge, and the rapier pierces a vital organ; {target_name} collapses, silenced."
        },
        {
            'attacker_msg': "With cold precision, your rapier delivers a fatal touch, and {target_name} falls.",
            'victim_msg': "With cold precision, {attacker_name}'s rapier delivers a fatal touch, and you fall.",
            'observer_msg': "With cold precision, {attacker_name}'s rapier delivers a fatal touch, and {target_name} falls."
        },
        {
            'attacker_msg': "The slender blade of the rapier slides between {target_name}'s {hit_location}, a swift and deadly conclusion.",
            'victim_msg': "The slender blade of the rapier slides between your {hit_location}, a swift and deadly conclusion.",
            'observer_msg': "The slender blade of the rapier slides between {target_name}'s {hit_location}, a swift and deadly conclusion."
        },
        {
            'attacker_msg': "Your final, perfectly placed thrust with the rapier leaves {target_name} lifeless.",
            'victim_msg': "{attacker_name}'s final, perfectly placed thrust with the rapier leaves you lifeless.",
            'observer_msg': "{attacker_name}'s final, perfectly placed thrust with the rapier leaves {target_name} lifeless."
        },
        {
            'attacker_msg': "The rapier, a silver serpent, strikes true, and {target_name}'s struggles cease.",
            'victim_msg': "The rapier, a silver serpent, strikes true, and your struggles cease.",
            'observer_msg': "The rapier, a silver serpent, strikes true, and {target_name}'s struggles cease."
        },
        {
            'attacker_msg': "A flick of the wrist, a fatal puncture to the throat; your rapier ends it.",
            'victim_msg': "A flick of the wrist, a fatal puncture to the throat; {attacker_name}'s rapier ends it.",
            'observer_msg': "A flick of the wrist, a fatal puncture to the throat; {attacker_name}'s rapier ends it."
        },
        {
            'attacker_msg': "You drive the rapier deep, a duelist's quiet coup de grace for {target_name}.",
            'victim_msg': "{attacker_name} drives the rapier deep, a duelist's quiet coup de grace for you.",
            'observer_msg': "{attacker_name} drives the rapier deep, a duelist's quiet coup de grace for {target_name}."
        },
        {
            'attacker_msg': "The keen point of the rapier finds an artery, and {target_name} bleeds out with shocking speed.",
            'victim_msg': "The keen point of the rapier finds an artery, and you bleed out with shocking speed.",
            'observer_msg': "The keen point of the rapier finds an artery, and {target_name} bleeds out with shocking speed."
        },
        {
            'attacker_msg': "With focused calm, you finish {target_name} with a decisive thrust from the rapier.",
            'victim_msg': "With focused calm, {attacker_name} finishes you with a decisive thrust from the rapier.",
            'observer_msg': "With focused calm, {attacker_name} finishes {target_name} with a decisive thrust from the rapier."
        },
        {
            'attacker_msg': "The rapier runs {target_name} through, a chilling display of your deadly skill.",
            'victim_msg': "The rapier runs you through, a chilling display of {attacker_name}'s deadly skill.",
            'observer_msg': "The rapier runs {target_name} through, a chilling display of {attacker_name}'s deadly skill."
        },
        {
            'attacker_msg': "Your blade finds the smallest opening, and {target_name} falls, the rapier's work complete.",
            'victim_msg': "{attacker_name}'s blade finds the smallest opening, and you fall, the rapier's work complete.",
            'observer_msg': "{attacker_name}'s blade finds the smallest opening, and {target_name} falls, the rapier's work complete."
        },
        {
            'attacker_msg': "A swift, almost invisible movement from the rapier, and {target_name} is no more.",
            'victim_msg': "A swift, almost invisible movement from the rapier, and you are no more.",
            'observer_msg': "A swift, almost invisible movement from the rapier, and {target_name} is no more."
        },
        {
            'attacker_msg': "The rapier, barely stained, is withdrawn as {target_name} breathes their last.",
            'victim_msg': "The rapier, barely stained, is withdrawn as you breathe your last.",
            'observer_msg': "The rapier, barely stained, is withdrawn as {target_name} breathes their last."
        },
        {
            'attacker_msg': "You deliver a precise end with the rapier, ensuring {target_name} troubles you no further.",
            'victim_msg': "{attacker_name} delivers a precise end with the rapier, ensuring you trouble them no further.",
            'observer_msg': "{attacker_name} delivers a precise end with the rapier, ensuring {target_name} troubles them no further."
        },
        {
            'attacker_msg': "Blood blossoms on {target_name}'s {hit_location} as your rapier finds its mark with fatal accuracy.",
            'victim_msg': "Blood blossoms on your {hit_location} as {attacker_name}'s rapier finds its mark with fatal accuracy.",
            'observer_msg': "Blood blossoms on {target_name}'s {hit_location} as {attacker_name}'s rapier finds its mark with fatal accuracy."
        },
        {
            'attacker_msg': "The point of the rapier slips through {target_name}'s guard, delivering a killing wound.",
            'victim_msg': "The point of the rapier slips through your guard, delivering a killing wound.",
            'observer_msg': "The point of the rapier slips through {target_name}'s guard, delivering a killing wound."
        },
        {
            'attacker_msg': "You stand poised, rapier lowered, {target_name} a still form at your feet.",
            'victim_msg': "{attacker_name} stands poised, rapier lowered, you a still form at their feet.",
            'observer_msg': "{attacker_name} stands poised, rapier lowered, {target_name} a still form at their feet."
        },
        {
            'attacker_msg': "A final, desperate defense from {target_name} is bypassed; your rapier is too swift.",
            'victim_msg': "A final, desperate defense from you is bypassed; {attacker_name}'s rapier is too swift.",
            'observer_msg': "A final, desperate defense from {target_name} is bypassed; {attacker_name}'s rapier is too swift."
        },
        {
            'attacker_msg': "The rapier's deadly song concludes as it strikes {target_name} down with lethal grace.",
            'victim_msg': "The rapier's deadly song concludes as it strikes you down with lethal grace.",
            'observer_msg': "The rapier's deadly song concludes as it strikes {target_name} down with lethal grace."
        },
        {
            'attacker_msg': "Your perfectly executed lunge with the rapier leaves {target_name} without a breath.",
            'victim_msg': "{attacker_name}'s perfectly executed lunge with the rapier leaves you without a breath.",
            'observer_msg': "{attacker_name}'s perfectly executed lunge with the rapier leaves {target_name} without a breath."
        },
        {
            'attacker_msg': "With chilling efficiency, you use the rapier to extinguish {target_name}'s life.",
            'victim_msg': "With chilling efficiency, {attacker_name} uses the rapier to extinguish your life.",
            'observer_msg': "With chilling efficiency, {attacker_name} uses the rapier to extinguish {target_name}'s life."
        },
        {
            'attacker_msg': "The rapier, an instrument of elegant death, claims {target_name} with a single, fatal touch.",
            'victim_msg': "The rapier, an instrument of elegant death, claims you with a single, fatal touch.",
            'observer_msg': "The rapier, an instrument of elegant death, claims {target_name} with a single, fatal touch."
        },
        {
            'attacker_msg': "{target_name}'s eyes glaze over as your rapier delivers the final, silent blow.",
            'victim_msg': "Your eyes glaze over as {attacker_name}'s rapier delivers the final, silent blow.",
            'observer_msg': "{target_name}'s eyes glaze over as {attacker_name}'s rapier delivers the final, silent blow."
        },
        {
            'attacker_msg': "A thin line of crimson is the only sign before {target_name} crumples from the rapier's fatal kiss.",
            'victim_msg': "A thin line of crimson is the only sign before you crumple from the rapier's fatal kiss.",
            'observer_msg': "A thin line of crimson is the only sign before {target_name} crumples from the rapier's fatal kiss."
        },
        {
            'attacker_msg': "You withdraw the rapier with a flourish, leaving {target_name} to the silence of death.",
            'victim_msg': "{attacker_name} withdraws the rapier with a flourish, leaving you to the silence of death.",
            'observer_msg': "{attacker_name} withdraws the rapier with a flourish, leaving {target_name} to the silence of death."
        },
        {
            'attacker_msg': "The duel ends as your rapier strikes true, felling {target_name} with deadly precision.",
            'victim_msg': "The duel ends as {attacker_name}'s rapier strikes true, felling you with deadly precision.",
            'observer_msg': "The duel ends as {attacker_name}'s rapier strikes true, felling {target_name} with deadly precision."
        },
        {
            'attacker_msg': "No wasted motion, no hesitation; your rapier completes its grim purpose on {target_name}.",
            'victim_msg': "No wasted motion, no hesitation; {attacker_name}'s rapier completes its grim purpose on you.",
            'observer_msg': "No wasted motion, no hesitation; {attacker_name}'s rapier completes its grim purpose on {target_name}."
        },
        {
            'attacker_msg': "The rapier, once gleaming, now carries a single drop of red as {target_name} succumbs.",
            'victim_msg': "The rapier, once gleaming, now carries a single drop of red as you succumb.",
            'observer_msg': "The rapier, once gleaming, now carries a single drop of red as {target_name} succumbs."
        },
        {
            'attacker_msg': "You lower the rapier, {target_name} a fallen testament to its swift, lethal power.",
            'victim_msg': "{attacker_name} lowers the rapier, you a fallen testament to its swift, lethal power.",
            'observer_msg': "{attacker_name} lowers the rapier, {target_name} a fallen testament to its swift, lethal power."
        }
    ]
}
