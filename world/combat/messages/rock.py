"""
Combat messages for rock weapons.

These messages support three perspectives:
- attacker_msg: Message shown to the person performing the action
- victim_msg: Message shown to the target of the action  
- observer_msg: Message shown to others observing the action

Messages emphasize the rock's primitive brutality, blunt crushing force, and desperate improvised violence.
"""

MESSAGES = {
    "initiate": [
        {
            'attacker_msg': "You heft a jagged rock, its weight a solid promise of pain.",
            'victim_msg': "{attacker_name} hefts a jagged rock, its weight a solid promise of pain.",
            'observer_msg': "{attacker_name} hefts a jagged rock, its weight a solid promise of pain."
        },
        {
            'attacker_msg': "With a grim expression, you select a fist-sized rock, ready to crush and bludgeon.",
            'victim_msg': "With a grim expression, {attacker_name} selects a fist-sized rock, ready to crush and bludgeon.",
            'observer_msg': "With a grim expression, {attacker_name} selects a fist-sized rock, ready to crush and bludgeon."
        },
        {
            'attacker_msg': "Your {hit_location} closes around a rough, heavy rock, its surface gritty and unforgiving.",
            'victim_msg': "{attacker_name}'s hand closes around a rough, heavy rock, its surface gritty and unforgiving.",
            'observer_msg': "{attacker_name}'s hand closes around a rough, heavy rock, its surface gritty and unforgiving."
        },
        {
            'attacker_msg': "A simple rock, plucked from the ground, becomes a deadly bludgeon in your determined grip.",
            'victim_msg': "A simple rock, plucked from the ground, becomes a deadly bludgeon in {attacker_name}'s determined grip.",
            'observer_msg': "A simple rock, plucked from the ground, becomes a deadly bludgeon in {attacker_name}'s determined grip."
        },
        {
            'attacker_msg': "You hold the rock with a fierce intensity, its unyielding mass aimed at {target_name}.",
            'victim_msg': "{attacker_name} holds the rock with a fierce intensity, its unyielding mass aimed at you.",
            'observer_msg': "{attacker_name} holds the rock with a fierce intensity, its unyielding mass aimed at {target_name}."
        },
        {
            'attacker_msg': "The rock is a crude but effective tool, you handling it with brutal focus.",
            'victim_msg': "The rock is a crude but effective tool, {attacker_name} handling it with brutal focus.",
            'observer_msg': "The rock is a crude but effective tool, {attacker_name} handling it with brutal focus."
        },
        {
            'attacker_msg': "You point the heaviest end of the rock towards {target_name}, a clear, primitive threat.",
            'victim_msg': "{attacker_name} points the heaviest end of the rock towards you, a clear, primitive threat.",
            'observer_msg': "{attacker_name} points the heaviest end of the rock towards {target_name}, a clear, primitive threat."
        },
        {
            'attacker_msg': "Dust and grit fall from the rock in your {hit_location} as you prepare to strike.",
            'victim_msg': "Dust and grit fall from the rock in {attacker_name}'s hand as they prepare to strike.",
            'observer_msg': "Dust and grit fall from the rock in {attacker_name}'s hand as they prepare to strike."
        },
        {
            'attacker_msg': "You offer no warning, just the menacing presence of the rock and a brutal glint in your eye.",
            'victim_msg': "{attacker_name} offers no warning, just the menacing presence of the rock and a brutal glint in their eye.",
            'observer_msg': "{attacker_name} offers no warning, just the menacing presence of the rock and a brutal glint in their eye."
        },
        {
            'attacker_msg': "The rock is held tightly, you ready for savage, close-quarters bludgeoning.",
            'victim_msg': "The rock is held tightly, {attacker_name} ready for savage, close-quarters bludgeoning.",
            'observer_msg': "The rock is held tightly, {attacker_name} ready for savage, close-quarters bludgeoning."
        },
        {
            'attacker_msg': "You test the weight of the rock, then fix {target_name} with a predatory stare.",
            'victim_msg': "{attacker_name} tests the weight of the rock, then fixes you with a predatory stare.",
            'observer_msg': "{attacker_name} tests the weight of the rock, then fixes {target_name} with a predatory stare."
        },
        {
            'attacker_msg': "The air around the rock seems to grow heavy with the threat of sudden, crushing impact.",
            'victim_msg': "The air around the rock seems to grow heavy with the threat of sudden, crushing impact.",
            'observer_msg': "The air around the rock seems to grow heavy with the threat of sudden, crushing impact."
        },
        {
            'attacker_msg': "Your eyes are narrowed, sighting along the rock towards {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s eyes are narrowed, sighting along the rock towards your {hit_location}.",
            'observer_msg': "{attacker_name}'s eyes are narrowed, sighting along the rock towards {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The rock feels solid and unforgiving in your {hit_location}, a tool of pure, blunt force.",
            'victim_msg': "The rock feels solid and unforgiving in {attacker_name}'s hand, a tool of pure, blunt force.",
            'observer_msg': "The rock feels solid and unforgiving in {attacker_name}'s hand, a tool of pure, blunt force."
        },
        {
            'attacker_msg': "You shift your weight, the rock poised for a swift, bone-jarring strike or a desperate throw.",
            'victim_msg': "{attacker_name} shifts their weight, the rock poised for a swift, bone-jarring strike or a desperate throw.",
            'observer_msg': "{attacker_name} shifts their weight, the rock poised for a swift, bone-jarring strike or a desperate throw."
        },
        {
            'attacker_msg': "The rough, natural edges of the rock are a testament to its improvised, deadly nature.",
            'victim_msg': "The rough, natural edges of the rock are a testament to its improvised, deadly nature.",
            'observer_msg': "The rough, natural edges of the rock are a testament to its improvised, deadly nature."
        },
        {
            'attacker_msg': "You hold the rock low, ready to bring it crashing down or hurl it with vicious intent.",
            'victim_msg': "{attacker_name} holds the rock low, ready to bring it crashing down or hurl it with vicious intent.",
            'observer_msg': "{attacker_name} holds the rock low, ready to bring it crashing down or hurl it with vicious intent."
        },
        {
            'attacker_msg': "The unyielding surface of the rock offers a surprisingly good grip for you.",
            'victim_msg': "The unyielding surface of the rock offers a surprisingly good grip for {attacker_name}.",
            'observer_msg': "The unyielding surface of the rock offers a surprisingly good grip for {attacker_name}."
        },
        {
            'attacker_msg': "You let the rock thud against your palm, a silent, brutal invitation to {target_name}.",
            'victim_msg': "{attacker_name} lets the rock thud against their palm, a silent, brutal invitation to you.",
            'observer_msg': "{attacker_name} lets the rock thud against their palm, a silent, brutal invitation to {target_name}."
        },
        {
            'attacker_msg': "With a savage cry, you commit to the fight, rock leading the brutal assault.",
            'victim_msg': "With a savage cry, {attacker_name} commits to the fight, rock leading the brutal assault.",
            'observer_msg': "With a savage cry, {attacker_name} commits to the fight, rock leading the brutal assault."
        },
        {
            'attacker_msg': "You present the rock, its mundane nature a stark contrast to the serious wounds it can inflict.",
            'victim_msg': "{attacker_name} presents the rock, its mundane nature a stark contrast to the serious wounds it can inflict.",
            'observer_msg': "{attacker_name} presents the rock, its mundane nature a stark contrast to the serious wounds it can inflict."
        },
        {
            'attacker_msg': "The rock is a tool of raw, untamed violence in your desperate hands.",
            'victim_msg': "The rock is a tool of raw, untamed violence in {attacker_name}'s desperate hands.",
            'observer_msg': "The rock is a tool of raw, untamed violence in {attacker_name}'s desperate hands."
        },
        {
            'attacker_msg': "You present the unyielding mass of the rock, aimed at {target_name}'s most vulnerable points.",
            'victim_msg': "{attacker_name} presents the unyielding mass of the rock, aimed at your most vulnerable points.",
            'observer_msg': "{attacker_name} presents the unyielding mass of the rock, aimed at {target_name}'s most vulnerable points."
        },
        {
            'attacker_msg': "A last resort, a brutal tool; you and the rock are a dangerously primitive pair.",
            'victim_msg': "A last resort, a brutal tool; {attacker_name} and the rock are a dangerously primitive pair.",
            'observer_msg': "A last resort, a brutal tool; {attacker_name} and the rock are a dangerously primitive pair."
        },
        {
            'attacker_msg': "Your knuckles are white, your grip tight on the rock, ready to deliver a crushing blow.",
            'victim_msg': "{attacker_name}'s knuckles are white, their grip tight on the rock, ready to deliver a crushing blow.",
            'observer_msg': "{attacker_name}'s knuckles are white, their grip tight on the rock, ready to deliver a crushing blow."
        },
        {
            'attacker_msg': "The rock makes a faint grating sound as you adjust your grip for a powerful strike.",
            'victim_msg': "The rock makes a faint grating sound as {attacker_name} adjusts their grip for a powerful strike.",
            'observer_msg': "The rock makes a faint grating sound as {attacker_name} adjusts their grip for a powerful strike."
        },
        {
            'attacker_msg': "You seem to draw primal strength from the rock, your expression hardening.",
            'victim_msg': "{attacker_name} seems to draw primal strength from the rock, their expression hardening.",
            'observer_msg': "{attacker_name} seems to draw primal strength from the rock, their expression hardening."
        },
        {
            'attacker_msg': "Silence falls, broken only by your ragged breathing as you clutch the heavy rock.",
            'victim_msg': "Silence falls, broken only by {attacker_name}'s ragged breathing as they clutch the heavy rock.",
            'observer_msg': "Silence falls, broken only by {attacker_name}'s ragged breathing as they clutch the heavy rock."
        },
        {
            'attacker_msg': "The rock is a statement of pure, brutal force, and you wield it with savage focus.",
            'victim_msg': "The rock is a statement of pure, brutal force, and {attacker_name} wields it with savage focus.",
            'observer_msg': "The rock is a statement of pure, brutal force, and {attacker_name} wields it with savage focus."
        },
        {
            'attacker_msg': "You take a ragged breath, the faint, earthy scent of the rock and your own sweat in the air.",
            'victim_msg': "{attacker_name} takes a ragged breath, the faint, earthy scent of the rock and their own sweat in the air.",
            'observer_msg': "{attacker_name} takes a ragged breath, the faint, earthy scent of the rock and their own sweat in the air."
        }
    ],
    "hit": [
        {
            'attacker_msg': "A swift, brutal swing from your rock connects with {target_name}'s {hit_location} with a sickening, dull crack.",
            'victim_msg': "A swift, brutal swing from {attacker_name}'s rock connects with your {hit_location} with a sickening, dull crack.",
            'observer_msg': "A swift, brutal swing from {attacker_name}'s rock connects with {target_name}'s {hit_location} with a sickening, dull crack."
        },
        {
            'attacker_msg': "The rock connects with a heavy thud, your desperate attack finding bone and flesh.",
            'victim_msg': "The rock connects with a heavy thud, {attacker_name}'s desperate attack finding bone and flesh.",
            'observer_msg': "The rock connects with a heavy thud, {attacker_name}'s desperate attack finding bone and flesh."
        },
        {
            'attacker_msg': "Your rock smashes against {target_name}'s {hit_location}, leaving a bloody, pulped mess and a scream of agony.",
            'victim_msg': "{attacker_name}'s rock smashes against your {hit_location}, leaving a bloody, pulped mess and a scream of agony.",
            'observer_msg': "{attacker_name}'s rock smashes against {target_name}'s {hit_location}, leaving a bloody, pulped mess and a scream of agony."
        },
        {
            'attacker_msg': "Hard stone bites deep as your rock connects, {target_name} recoiling from the sudden, intense, crushing pain.",
            'victim_msg': "Hard stone bites deep as {attacker_name}'s rock connects, you recoiling from the sudden, intense, crushing pain.",
            'observer_msg': "Hard stone bites deep as {attacker_name}'s rock connects, {target_name} recoiling from the sudden, intense, crushing pain."
        },
        {
            'attacker_msg': "The jagged edge of the rock slams into {target_name}'s {hit_location}, who howls and stumbles as bone likely breaks.",
            'victim_msg': "The jagged edge of the rock slams into your {hit_location}, you howling and stumbling as bone likely breaks.",
            'observer_msg': "The jagged edge of the rock slams into {target_name}'s {hit_location}, who howls and stumbles as bone likely breaks."
        },
        {
            'attacker_msg': "Your desperate lunge with the rock leaves a nasty, bruising, and bleeding wound on {target_name}.",
            'victim_msg': "{attacker_name}'s desperate lunge with the rock leaves a nasty, bruising, and bleeding wound on you.",
            'observer_msg': "{attacker_name}'s desperate lunge with the rock leaves a nasty, bruising, and bleeding wound on {target_name}."
        },
        {
            'attacker_msg': "A quick, powerful blow, and the rock cracks against {target_name}'s {hit_location}, drawing a choked cry and breaking {hit_location}.",
            'victim_msg': "A quick, powerful blow, and the rock cracks against your {hit_location}, drawing a choked cry and breaking {hit_location}.",
            'observer_msg': "A quick, powerful blow, and the rock cracks against {target_name}'s {hit_location}, drawing a choked cry and breaking {hit_location}."
        },
        {
            'attacker_msg': "The rock's unyielding surface smashes through {target_name}'s defenses and into flesh with brutal efficiency.",
            'victim_msg': "The rock's unyielding surface smashes through your defenses and into flesh with brutal efficiency.",
            'observer_msg': "The rock's unyielding surface smashes through {target_name}'s defenses and into flesh with brutal efficiency."
        },
        {
            'attacker_msg': "Your rock makes a glancing hit, but still cracks against {target_name}'s {hit_location}, sending a jolt of pain.",
            'victim_msg': "{attacker_name}'s rock makes a glancing hit, but still cracks against your {hit_location}, sending a jolt of pain.",
            'observer_msg': "{attacker_name}'s rock makes a glancing hit, but still cracks against {target_name}'s {hit_location}, sending a jolt of pain."
        },
        {
            'attacker_msg': "With a savage push, you drive the rock into {target_name}, who thrashes wildly, trying to escape the crushing agony.",
            'victim_msg': "With a savage push, {attacker_name} drives the rock into you, you thrashing wildly, trying to escape the crushing agony.",
            'observer_msg': "With a savage push, {attacker_name} drives the rock into {target_name}, who thrashes wildly, trying to escape the crushing agony."
        },
        {
            'attacker_msg': "The rock scores a heavy hit on {target_name}'s {hit_location}, the impact shattering small bones.",
            'victim_msg': "The rock scores a heavy hit on your {hit_location}, the impact shattering small bones.",
            'observer_msg': "The rock scores a heavy hit on {target_name}'s {hit_location}, the impact shattering small bones."
        },
        {
            'attacker_msg': "Your well-aimed blow with the rock leaves it impacting {target_name}'s {hit_location} with a sickening crunch.",
            'victim_msg': "{attacker_name}'s well-aimed blow with the rock leaves it impacting your {hit_location} with a sickening crunch.",
            'observer_msg': "{attacker_name}'s well-aimed blow with the rock leaves it impacting {target_name}'s {hit_location} with a sickening crunch."
        },
        {
            'attacker_msg': "A sharp cracking sound and a cry of pain as your rock smashes into {target_name}'s flesh and bone.",
            'victim_msg': "A sharp cracking sound and a cry of pain as {attacker_name}'s rock smashes into your flesh and bone.",
            'observer_msg': "A sharp cracking sound and a cry of pain as {attacker_name}'s rock smashes into {target_name}'s flesh and bone."
        },
        {
            'attacker_msg': "The unyielding weight of your rock leaves a deep, painful bruise and likely broken bones on {target_name}'s {hit_location}.",
            'victim_msg': "The unyielding weight of {attacker_name}'s rock leaves a deep, painful bruise and likely broken bones on your {hit_location}.",
            'observer_msg': "The unyielding weight of {attacker_name}'s rock leaves a deep, painful bruise and likely broken bones on {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Your follow-up attack with the rock catches {target_name} again, adding another grievous, crushing wound.",
            'victim_msg': "{attacker_name}'s follow-up attack with the rock catches you again, adding another grievous, crushing wound.",
            'observer_msg': "{attacker_name}'s follow-up attack with the rock catches {target_name} again, adding another grievous, crushing wound."
        },
        {
            'attacker_msg': "A desperate block by {target_name} is met with the full force of the rock, shattering their {hit_location}.",
            'victim_msg': "A desperate block by you is met with the full force of the rock, shattering your {hit_location}.",
            'observer_msg': "A desperate block by {target_name} is met with the full force of the rock, shattering their {hit_location}."
        },
        {
            'attacker_msg': "The rock makes solid contact with {target_name}'s {hit_location}, the blunt force knocking the wind out of them and cracking {hit_location}.",
            'victim_msg': "The rock makes solid contact with your {hit_location}, the blunt force knocking the wind out of you and cracking {hit_location}.",
            'observer_msg': "The rock makes solid contact with {target_name}'s {hit_location}, the blunt force knocking the wind out of them and cracking {hit_location}."
        },
        {
            'attacker_msg': "Your rock finds purchase, delivering a painful, debilitating blow to {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s rock finds purchase, delivering a painful, debilitating blow to your {hit_location}.",
            'observer_msg': "{attacker_name}'s rock finds purchase, delivering a painful, debilitating blow to {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "Even a glancing blow from the rock leaves {target_name} with a significant, throbbing bruise and ringing ears.",
            'victim_msg': "Even a glancing blow from the rock leaves you with a significant, throbbing bruise and ringing ears.",
            'observer_msg': "Even a glancing blow from the rock leaves {target_name} with a significant, throbbing bruise and ringing ears."
        },
        {
            'attacker_msg': "You press the attack, the rock a constant threat that finally lands, crushing into {target_name}.",
            'victim_msg': "{attacker_name} presses the attack, the rock a constant threat that finally lands, crushing into you.",
            'observer_msg': "{attacker_name} presses the attack, the rock a constant threat that finally lands, crushing into {target_name}."
        },
        {
            'attacker_msg': "The rock's rough surface meets {target_name}'s flesh, and they recoil with a sharp cry from the intense, blunt agony.",
            'victim_msg': "The rock's rough surface meets your flesh, and you recoil with a sharp cry from the intense, blunt agony.",
            'observer_msg': "The rock's rough surface meets {target_name}'s flesh, and they recoil with a sharp cry from the intense, blunt agony."
        },
        {
            'attacker_msg': "Your strike is true, the rock smashing {target_name} squarely and causing immediate, severe trauma.",
            'victim_msg': "{attacker_name}'s strike is true, the rock smashing you squarely and causing immediate, severe trauma.",
            'observer_msg': "{attacker_name}'s strike is true, the rock smashing {target_name} squarely and causing immediate, severe trauma."
        },
        {
            'attacker_msg': "A close-quarters struggle, and you manage to bring the rock down hard on {target_name}'s {hit_location}.",
            'victim_msg': "A close-quarters struggle, and {attacker_name} manages to bring the rock down hard on your {hit_location}.",
            'observer_msg': "A close-quarters struggle, and {attacker_name} manages to bring the rock down hard on {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The rock, though a crude weapon, proves brutally effective as you inflict a horrific injury on {target_name}.",
            'victim_msg': "The rock, though a crude weapon, proves brutally effective as {attacker_name} inflicts a horrific injury on you.",
            'observer_msg': "The rock, though a crude weapon, proves brutally effective as {attacker_name} inflicts a horrific injury on {target_name}."
        },
        {
            'attacker_msg': "Your rock makes contact again, leaving another deep, painful bruise on {target_name}.",
            'victim_msg': "{attacker_name}'s rock makes contact again, leaving another deep, painful bruise on you.",
            'observer_msg': "{attacker_name}'s rock makes contact again, leaving another deep, painful bruise on {target_name}."
        },
        {
            'attacker_msg': "A painful thudding sound as the rock from you smashes into {target_name}'s {hit_location}, making them gasp.",
            'victim_msg': "A painful thudding sound as the rock from {attacker_name} smashes into your {hit_location}, making you gasp.",
            'observer_msg': "A painful thudding sound as the rock from {attacker_name} smashes into {target_name}'s {hit_location}, making them gasp."
        },
        {
            'attacker_msg': "The point of your rock impacts {target_name}'s {hit_location}, the pain and shock overwhelming.",
            'victim_msg': "The point of {attacker_name}'s rock impacts your {hit_location}, the pain and shock overwhelming.",
            'observer_msg': "The point of {attacker_name}'s rock impacts {target_name}'s {hit_location}, the pain and shock overwhelming."
        },
        {
            'attacker_msg': "Your rock delivers another brutal blow to {target_name}'s {hit_location}, the unyielding stone unforgiving.",
            'victim_msg': "{attacker_name}'s rock delivers another brutal blow to your {hit_location}, the unyielding stone unforgiving.",
            'observer_msg': "{attacker_name}'s rock delivers another brutal blow to {target_name}'s {hit_location}, the unyielding stone unforgiving."
        },
        {
            'attacker_msg': "A well-placed strike with the rock leaves {target_name} momentarily stunned, vision blurring from the impact.",
            'victim_msg': "A well-placed strike with the rock leaves you momentarily stunned, vision blurring from the impact.",
            'observer_msg': "A well-placed strike with the rock leaves {target_name} momentarily stunned, vision blurring from the impact."
        },
        {
            'attacker_msg': "The rock, guided by your desperate intent, inflicts a series of telling, painful, crushing injuries upon {target_name}.",
            'victim_msg': "The rock, guided by {attacker_name}'s desperate intent, inflicts a series of telling, painful, crushing injuries upon you.",
            'observer_msg': "The rock, guided by {attacker_name}'s desperate intent, inflicts a series of telling, painful, crushing injuries upon {target_name}."
        }
    ],
    "miss": [
        {
            'attacker_msg': "Your rock whistles through the air, its heavy mass narrowly missing {target_name}'s {hit_location}.",
            'victim_msg': "{attacker_name}'s rock whistles through the air, its heavy mass narrowly missing your {hit_location}.",
            'observer_msg': "{attacker_name}'s rock whistles through the air, its heavy mass narrowly missing {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "{target_name} stumbles back, avoiding the desperate swing of your rock by a hair's breadth.",
            'victim_msg': "You stumble back, avoiding the desperate swing of {attacker_name}'s rock by a hair's breadth.",
            'observer_msg': "{target_name} stumbles back, avoiding the desperate swing of {attacker_name}'s rock by a hair's breadth."
        },
        {
            'attacker_msg': "The rock strikes a nearby tree with a solid thud, its threat ended but missing {target_name}.",
            'victim_msg': "The rock strikes a nearby tree with a solid thud, its threat ended but missing you.",
            'observer_msg': "The rock strikes a nearby tree with a solid thud, its threat ended but missing {target_name}."
        },
        {
            'attacker_msg': "Dust puffs as your rock glances off a stone wall, its trajectory diverted from {target_name}.",
            'victim_msg': "Dust puffs as {attacker_name}'s rock glances off a stone wall, its trajectory diverted from you.",
            'observer_msg': "Dust puffs as {attacker_name}'s rock glances off a stone wall, its trajectory diverted from {target_name}."
        },
        {
            'attacker_msg': "You overextend, the rock slipping slightly in your grip and thudding harmlessly to the ground.",
            'victim_msg': "{attacker_name} overextends, the rock slipping slightly in their grip and thudding harmlessly to the ground.",
            'observer_msg': "{attacker_name} overextends, the rock slipping slightly in their grip and thudding harmlessly to the ground."
        },
        {
            'attacker_msg': "A quick sidestep from {target_name} causes your rock to meet only empty air, you cursing.",
            'victim_msg': "A quick sidestep from you causes {attacker_name}'s rock to meet only empty air, {attacker_name} cursing.",
            'observer_msg': "A quick sidestep from {target_name} causes {attacker_name}'s rock to meet only empty air, {attacker_name} cursing."
        },
        {
            'attacker_msg': "The rock sails through the air with wasted effort as your vicious strike misses its mark.",
            'victim_msg': "The rock sails through the air with wasted effort as {attacker_name}'s vicious strike misses its mark.",
            'observer_msg': "The rock sails through the air with wasted effort as {attacker_name}'s vicious strike misses its mark."
        },
        {
            'attacker_msg': "Your lunge with the rock is parried with difficulty, {target_name} using an object to deflect the heavy stone.",
            'victim_msg': "{attacker_name}'s lunge with the rock is parried with difficulty, you using an object to deflect the heavy stone.",
            'observer_msg': "{attacker_name}'s lunge with the rock is parried with difficulty, {target_name} using an object to deflect the heavy stone."
        },
        {
            'attacker_msg': "{target_name} ducks under the arc of your rock, feeling the air stir from its passage.",
            'victim_msg': "You duck under the arc of {attacker_name}'s rock, feeling the air stir from its passage.",
            'observer_msg': "{target_name} ducks under the arc of {attacker_name}'s rock, feeling the air stir from its passage."
        },
        {
            'attacker_msg': "The rock clatters against a stone floor, perhaps chipping but still intact, well away from {target_name}.",
            'victim_msg': "The rock clatters against a stone floor, perhaps chipping but still intact, well away from you.",
            'observer_msg': "The rock clatters against a stone floor, perhaps chipping but still intact, well away from {target_name}."
        },
        {
            'attacker_msg': "Your rock passes through the space {target_name} desperately vacated, leaving only the sound of its passage.",
            'victim_msg': "{attacker_name}'s rock passes through the space you desperately vacated, leaving only the sound of its passage.",
            'observer_msg': "{attacker_name}'s rock passes through the space {target_name} desperately vacated, leaving only the sound of its passage."
        },
        {
            'attacker_msg': "A quick retreat from {target_name} leaves your rock to impact nothing but air.",
            'victim_msg': "A quick retreat from you leaves {attacker_name}'s rock to impact nothing but air.",
            'observer_msg': "A quick retreat from {target_name} leaves {attacker_name}'s rock to impact nothing but air."
        },
        {
            'attacker_msg': "The rock feels dangerously heavy in your {hit_location} as the intended crushing blow fails to connect.",
            'victim_msg': "The rock feels dangerously heavy in {attacker_name}'s hand as the intended crushing blow fails to connect.",
            'observer_msg': "The rock feels dangerously heavy in {attacker_name}'s hand as the intended crushing blow fails to connect."
        },
        {
            'attacker_msg': "You misjudge the distance, the heavy rock falling short of {target_name} with a dull thud.",
            'victim_msg': "{attacker_name} misjudges the distance, the heavy rock falling short of you with a dull thud.",
            'observer_msg': "{attacker_name} misjudges the distance, the heavy rock falling short of {target_name} with a dull thud."
        },
        {
            'attacker_msg': "{target_name}'s desperate maneuver foils your attack, the rock arcing angrily through empty space.",
            'victim_msg': "Your desperate maneuver foils {attacker_name}'s attack, the rock arcing angrily through empty space.",
            'observer_msg': "{target_name}'s desperate maneuver foils {attacker_name}'s attack, the rock arcing angrily through empty space."
        },
        {
            'attacker_msg': "The heavy thud of the rock hitting the ground is the only result as it misses {target_name} cleanly.",
            'victim_msg': "The heavy thud of the rock hitting the ground is the only result as it misses you cleanly.",
            'observer_msg': "The heavy thud of the rock hitting the ground is the only result as it misses {target_name} cleanly."
        },
        {
            'attacker_msg': "You grunt, the momentum of the missed swing with the rock carrying you slightly off-kilter.",
            'victim_msg': "{attacker_name} grunts, the momentum of the missed swing with the rock carrying them slightly off-kilter.",
            'observer_msg': "{attacker_name} grunts, the momentum of the missed swing with the rock carrying them slightly off-kilter."
        },
        {
            'attacker_msg': "A growl of frustration from you as your rock attack is evaded by a nimble {target_name}.",
            'victim_msg': "A growl of frustration from {attacker_name} as their rock attack is evaded by a nimble you.",
            'observer_msg': "A growl of frustration from {attacker_name} as their rock attack is evaded by a nimble {target_name}."
        },
        {
            'attacker_msg': "The rock kicks up dirt beside {target_name}'s {hit_location}, but draws no blood.",
            'victim_msg': "The rock kicks up dirt beside your {hit_location}, but draws no blood.",
            'observer_msg': "The rock kicks up dirt beside {target_name}'s {hit_location}, but draws no blood."
        },
        {
            'attacker_msg': "Your straightforward attack with the rock is anticipated and dodged by {target_name}, who looks terrified.",
            'victim_msg': "{attacker_name}'s straightforward attack with the rock is anticipated and dodged by you, who looks terrified.",
            'observer_msg': "{attacker_name}'s straightforward attack with the rock is anticipated and dodged by {target_name}, who looks terrified."
        },
        {
            'attacker_msg': "The air parts before the heavy rock, but {target_name} remains untouched by its crushing mass.",
            'victim_msg': "The air parts before the heavy rock, but you remain untouched by its crushing mass.",
            'observer_msg': "The air parts before the heavy rock, but {target_name} remains untouched by its crushing mass."
        },
        {
            'attacker_msg': "Your lunge is too predictable, {target_name} already moving out of the rock's brutal path.",
            'victim_msg': "{attacker_name}'s lunge is too predictable, you already moving out of the rock's brutal path.",
            'observer_msg': "{attacker_name}'s lunge is too predictable, {target_name} already moving out of the rock's brutal path."
        },
        {
            'attacker_msg': "A desperate swipe from {target_name} knocks your rock aside at the very last second, its weight still dangerously close.",
            'victim_msg': "A desperate swipe from you knocks {attacker_name}'s rock aside at the very last second, its weight still dangerously close.",
            'observer_msg': "A desperate swipe from {target_name} knocks {attacker_name}'s rock aside at the very last second, its weight still dangerously close."
        },
        {
            'attacker_msg': "The rock's unyielding surface finds nothing but air as {target_name} scrambles away from the vicious assault.",
            'victim_msg': "The rock's unyielding surface finds nothing but air as you scramble away from the vicious assault.",
            'observer_msg': "The rock's unyielding surface finds nothing but air as {target_name} scrambles away from the vicious assault."
        },
        {
            'attacker_msg': "Your rock throw goes wide, thudding harmlessly against a distant object.",
            'victim_msg': "{attacker_name}'s rock throw goes wide, thudding harmlessly against a distant object.",
            'observer_msg': "{attacker_name}'s rock throw goes wide, thudding harmlessly against a distant object."
        },
        {
            'attacker_msg': "The rock nearly slips from your grasp as you recover from the missed, powerful swing.",
            'victim_msg': "The rock nearly slips from {attacker_name}'s grasp as they recover from the missed, powerful swing.",
            'observer_msg': "The rock nearly slips from {attacker_name}'s grasp as they recover from the missed, powerful swing."
        },
        {
            'attacker_msg': "{target_name} barely manages to avoid the reach of your heavy, jagged rock.",
            'victim_msg': "You barely manage to avoid the reach of {attacker_name}'s heavy, jagged rock.",
            'observer_msg': "{target_name} barely manages to avoid the reach of {attacker_name}'s heavy, jagged rock."
        },
        {
            'attacker_msg': "Your attack is desperate but ultimately futile as the rock misses its mark by inches.",
            'victim_msg': "{attacker_name}'s attack is desperate but ultimately futile as the rock misses its mark by inches.",
            'observer_msg': "{attacker_name}'s attack is desperate but ultimately futile as the rock misses its mark by inches."
        },
        {
            'attacker_msg': "The rock makes a dull whistling sound as it fails to connect with {target_name}.",
            'victim_msg': "The rock makes a dull whistling sound as it fails to connect with you.",
            'observer_msg': "The rock makes a dull whistling sound as it fails to connect with {target_name}."
        },
        {
            'attacker_msg': "A near miss! Your rock grazes {target_name}'s clothing, the impact still jarring.",
            'victim_msg': "A near miss! {attacker_name}'s rock grazes your clothing, the impact still jarring.",
            'observer_msg': "A near miss! {attacker_name}'s rock grazes {target_name}'s clothing, the impact still jarring."
        }
    ],
    "kill": [
        {
            'attacker_msg': "You smash the rock into {target_name}'s {hit_location}; they collapse, skull audibly cracking, succumbing to massive trauma.",
            'victim_msg': "{attacker_name} smashes the rock into your {hit_location}; you collapse, skull audibly cracking, succumbing to massive trauma.",
            'observer_msg': "{attacker_name} smashes the rock into {target_name}'s {hit_location}; they collapse, skull audibly cracking, succumbing to massive trauma."
        },
        {
            'attacker_msg': "The rock, driven deep into {target_name}'s {hit_location}, crushes ribs and pulps organs, and they fall silent, life extinguished.",
            'victim_msg': "The rock, driven deep into your {hit_location}, crushes ribs and pulps organs, and you fall silent, life extinguished.",
            'observer_msg': "The rock, driven deep into {target_name}'s {hit_location}, crushes ribs and pulps organs, and they fall silent, life extinguished."
        },
        {
            'attacker_msg': "With a final, brutal swing, you bring the rock down on {target_name}'s {hit_location}, and they drop, twitching, then still.",
            'victim_msg': "With a final, brutal swing, {attacker_name} brings the rock down on your {hit_location}, and you drop, twitching, then still.",
            'observer_msg': "With a final, brutal swing, {attacker_name} brings the rock down on {target_name}'s {hit_location}, and they drop, twitching, then still."
        },
        {
            'attacker_msg': "The heavy impact of the rock against {target_name}'s {hit_location} crushes their windpipe, causing them to asphyxiate in moments.",
            'victim_msg': "The heavy impact of the rock against your {hit_location} crushes your windpipe, causing you to asphyxiate in moments.",
            'observer_msg': "The heavy impact of the rock against {target_name}'s {hit_location} crushes their windpipe, causing them to asphyxiate in moments."
        },
        {
            'attacker_msg': "You repeatedly bludgeon {target_name} with the rock until they slump, lifeless, in a pool of their own blood and shattered bone.",
            'victim_msg': "{attacker_name} repeatedly bludgeons you with the rock until you slump, lifeless, in a pool of your own blood and shattered bone.",
            'observer_msg': "{attacker_name} repeatedly bludgeons {target_name} with the rock until they slump, lifeless, in a pool of their own blood and shattered bone."
        },
        {
            'attacker_msg': "The rock, a desperate tool of death, delivers a killing blow as {target_name} is overcome by catastrophic, crushing wounds.",
            'victim_msg': "The rock, a desperate tool of death, delivers a killing blow as you are overcome by catastrophic, crushing wounds.",
            'observer_msg': "The rock, a desperate tool of death, delivers a killing blow as {target_name} is overcome by catastrophic, crushing wounds."
        },
        {
            'attacker_msg': "A precise, savage blow with the rock to {target_name}'s {hit_location} ends their life with a sickening crunch.",
            'victim_msg': "A precise, savage blow with the rock to your {hit_location} ends your life with a sickening crunch.",
            'observer_msg': "A precise, savage blow with the rock to {target_name}'s {hit_location} ends their life with a sickening crunch."
        },
        {
            'attacker_msg': "You bring the rock down on {target_name}'s {hit_location} until they stop moving, the features a bloody ruin, life extinguished.",
            'victim_msg': "{attacker_name} brings the rock down on your {hit_location} until you stop moving, the features a bloody ruin, life extinguished.",
            'observer_msg': "{attacker_name} brings the rock down on {target_name}'s {hit_location} until they stop moving, the features a bloody ruin, life extinguished."
        },
        {
            'attacker_msg': "The unyielding weight of the rock shatters something vital in {target_name}, who crumples, unmoving, amidst the spreading bloodstain.",
            'victim_msg': "The unyielding weight of the rock shatters something vital in you, you crumpling, unmoving, amidst the spreading bloodstain.",
            'observer_msg': "The unyielding weight of the rock shatters something vital in {target_name}, who crumples, unmoving, amidst the spreading bloodstain."
        },
        {
            'attacker_msg': "With a final, desperate act, you use the rock to inflict a fatal, crushing wound on {target_name}.",
            'victim_msg': "With a final, desperate act, {attacker_name} uses the rock to inflict a fatal, crushing wound on you.",
            'observer_msg': "With a final, desperate act, {attacker_name} uses the rock to inflict a fatal, crushing wound on {target_name}."
        },
        {
            'attacker_msg': "The rock, wielded with grim intent, turns {target_name} into a broken mess, their struggles quickly ceasing.",
            'victim_msg': "The rock, wielded with grim intent, turns you into a broken mess, your struggles quickly ceasing.",
            'observer_msg': "The rock, wielded with grim intent, turns {target_name} into a broken mess, their struggles quickly ceasing."
        },
        {
            'attacker_msg': "Your rock finds a way to crush a major artery or organ in {target_name}, and they perish rapidly from internal bleeding.",
            'victim_msg': "{attacker_name}'s rock finds a way to crush a major artery or organ in you, and you perish rapidly from internal bleeding.",
            'observer_msg': "{attacker_name}'s rock finds a way to crush a major artery or organ in {target_name}, and they perish rapidly from internal bleeding."
        },
        {
            'attacker_msg': "A merciless, heavy blow with the rock, and {target_name} is no more, overcome by the vicious, blunt trauma.",
            'victim_msg': "A merciless, heavy blow with the rock, and you are no more, overcome by the vicious, blunt trauma.",
            'observer_msg': "A merciless, heavy blow with the rock, and {target_name} is no more, overcome by the vicious, blunt trauma."
        },
        {
            'attacker_msg': "The rock, now slick with gore, drops from your {hit_location} as {target_name} lies lifeless and broken.",
            'victim_msg': "The rock, now slick with gore, drops from {attacker_name}'s hand as you lie lifeless and broken.",
            'observer_msg': "The rock, now slick with gore, drops from {attacker_name}'s hand as {target_name} lies lifeless and broken."
        },
        {
            'attacker_msg': "You ensure {target_name} will not rise by repeatedly smashing their head with the rock until it's unrecognizable.",
            'victim_msg': "{attacker_name} ensures you will not rise by repeatedly smashing your {hit_location} with the rock until it's unrecognizable.",
            'observer_msg': "{attacker_name} ensures {target_name} will not rise by repeatedly smashing their head with the rock until it's unrecognizable."
        },
        {
            'attacker_msg': "Blood and brain matter spray as your rock finds purchase again and again, and they quickly succumb to the horrific injuries.",
            'victim_msg': "Blood and brain matter spray as {attacker_name}'s rock finds purchase again and again, and you quickly succumb to the horrific injuries.",
            'observer_msg': "Blood and brain matter spray as {attacker_name}'s rock finds purchase again and again, and they quickly succumb to the horrific injuries."
        },
        {
            'attacker_msg': "The point of the rock, driven into a vulnerable spot with full force, inflicts fatal internal injuries upon {target_name}.",
            'victim_msg': "The point of the rock, driven into a vulnerable spot with full force, inflicts fatal internal injuries upon you.",
            'observer_msg': "The point of the rock, driven into a vulnerable spot with full force, inflicts fatal internal injuries upon {target_name}."
        },
        {
            'attacker_msg': "You stand over {target_name}'s broken form, the rock still clutched, the victor of a horrific, brutal confrontation.",
            'victim_msg': "{attacker_name} stands over your broken form, the rock still clutched, the victor of a horrific, brutal confrontation.",
            'observer_msg': "{attacker_name} stands over {target_name}'s broken form, the rock still clutched, the victor of a horrific, brutal confrontation."
        },
        {
            'attacker_msg': "A final, desperate struggle sees {target_name} overwhelmed by the rock's relentless blows, their life ending in a bloody, pulped mess.",
            'victim_msg': "A final, desperate struggle sees you overwhelmed by the rock's relentless blows, your life ending in a bloody, pulped mess.",
            'observer_msg': "A final, desperate struggle sees {target_name} overwhelmed by the rock's relentless blows, their life ending in a bloody, pulped mess."
        },
        {
            'attacker_msg': "The rock's bloody work ends as it fatally crushes {target_name}, leaving only a mutilated corpse.",
            'victim_msg': "The rock's bloody work ends as it fatally crushes you, leaving only a mutilated corpse.",
            'observer_msg': "The rock's bloody work ends as it fatally crushes {target_name}, leaving only a mutilated corpse."
        },
        {
            'attacker_msg': "Your perfectly timed attack with the rock inflicts a mortal wound before {target_name} can react.",
            'victim_msg': "{attacker_name}'s perfectly timed attack with the rock inflicts a mortal wound before you can react.",
            'observer_msg': "{attacker_name}'s perfectly timed attack with the rock inflicts a mortal wound before {target_name} can react."
        },
        {
            'attacker_msg': "With cold, brutal efficiency, you use the rock to end {target_name}'s resistance permanently and horrifically.",
            'victim_msg': "With cold, brutal efficiency, {attacker_name} uses the rock to end your resistance permanently and horrifically.",
            'observer_msg': "With cold, brutal efficiency, {attacker_name} uses the rock to end {target_name}'s resistance permanently and horrifically."
        },
        {
            'attacker_msg': "The rock, an instrument of desperate, bloody destruction, claims another victim in {target_name}.",
            'victim_msg': "The rock, an instrument of desperate, bloody destruction, claims another victim in you.",
            'observer_msg': "The rock, an instrument of desperate, bloody destruction, claims another victim in {target_name}."
        },
        {
            'attacker_msg': "{target_name}'s eyes widen in terror as your rock delivers the final, agonizing, crushing blow.",
            'victim_msg': "Your eyes widen in terror as {attacker_name}'s rock delivers the final, agonizing, crushing blow.",
            'observer_msg': "{target_name}'s eyes widen in terror as {attacker_name}'s rock delivers the final, agonizing, crushing blow."
        },
        {
            'attacker_msg': "A sickening crunch echoes as your rock fatally smashes {target_name}'s {hit_location}.",
            'victim_msg': "A sickening crunch echoes as {attacker_name}'s rock fatally smashes your {hit_location}.",
            'observer_msg': "A sickening crunch echoes as {attacker_name}'s rock fatally smashes {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "You discard the bloody rock beside {target_name}'s corpse, a grim testament to its makeshift lethality.",
            'victim_msg': "{attacker_name} discards the bloody rock beside your corpse, a grim testament to its makeshift lethality.",
            'observer_msg': "{attacker_name} discards the bloody rock beside {target_name}'s corpse, a grim testament to its makeshift lethality."
        },
        {
            'attacker_msg': "The battle ends as your rock delivers a fatal, crushing blow to {target_name}, spilling their lifeblood and brains.",
            'victim_msg': "The battle ends as {attacker_name}'s rock delivers a fatal, crushing blow to you, spilling your lifeblood and brains.",
            'observer_msg': "The battle ends as {attacker_name}'s rock delivers a fatal, crushing blow to {target_name}, spilling their lifeblood and brains."
        },
        {
            'attacker_msg': "No mercy in your eyes as the rock completes its grim, bloody task on {target_name}.",
            'victim_msg': "No mercy in {attacker_name}'s eyes as the rock completes its grim, bloody task on you.",
            'observer_msg': "No mercy in {attacker_name}'s eyes as the rock completes its grim, bloody task on {target_name}."
        },
        {
            'attacker_msg': "The rock, once merely stone, is now an agent of death as {target_name} succumbs to its vicious, unstoppable blows.",
            'victim_msg': "The rock, once merely stone, is now an agent of death as you succumb to its vicious, unstoppable blows.",
            'observer_msg': "The rock, once merely stone, is now an agent of death as {target_name} succumbs to its vicious, unstoppable blows."
        },
        {
            'attacker_msg': "You step back from {target_name}'s mutilated remains, the rock perhaps still in hand, a fallen testament to its terrible, makeshift potential.",
            'victim_msg': "{attacker_name} steps back from your mutilated remains, the rock perhaps still in hand, a fallen testament to its terrible, makeshift potential.",
            'observer_msg': "{attacker_name} steps back from {target_name}'s mutilated remains, the rock perhaps still in hand, a fallen testament to its terrible, makeshift potential."
        }
    ]
}
