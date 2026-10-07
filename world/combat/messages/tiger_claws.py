"""Tiger claws, one glove (MULTI_WEAPON_COMBAT_SPEC §5, §7; owner ruling §14
#10: each weapon has its own pair of banks). The hand-neutral entries of
`tiger_claws_akimbo` plus lines of its own; nothing here assumes a second
glove. Reached by the TIGER_CLAWS prototype's `weapon_type`.
"""
MESSAGES = {
    'initiate': [
        {
            'attacker_msg': "You flex your fingers inside the glove and the hooked blades fan open.",
            'victim_msg': "{attacker_name} flexes their fingers inside the glove and the hooked blades fan open.",
            'observer_msg': "{attacker_name} flexes their fingers inside the glove and the hooked blades fan open."
        },
        {
            'attacker_msg': "The buckle clicks home at your wrist. The blades were already sharp.",
            'victim_msg': "The buckle clicks home at {attacker_name}'s wrist. The blades were already sharp.",
            'observer_msg': "The buckle clicks home at {attacker_name}'s wrist. The blades were already sharp."
        },
        {
            'attacker_msg': "You roll your shoulders. The claws catch the light like they were made to.",
            'victim_msg': "{attacker_name} rolls their shoulders. The claws catch the light like they were made to.",
            'observer_msg': "{attacker_name} rolls their shoulders. The claws catch the light like they were made to."
        },
        {
            'attacker_msg': "Four curved blades, stamped steel, a brand name on the strap. You raise them.",
            'victim_msg': "Four curved blades, stamped steel, a brand name on the strap. {attacker_name} raises them.",
            'observer_msg': "Four curved blades, stamped steel, a brand name on the strap. {attacker_name} raises them."
        },
        {
            'attacker_msg': "The glove creaks as your fist closes. The blades do not creak. They wait.",
            'victim_msg': "The glove creaks as {attacker_name}'s fist closes. The blades do not creak. They wait.",
            'observer_msg': "The glove creaks as {attacker_name}'s fist closes. The blades do not creak. They wait."
        },
        {
            'attacker_msg': "You drag one blade along the wall as you come. A thin bright line follows you.",
            'victim_msg': "{attacker_name} drags one blade along the wall as they come. A thin bright line follows them.",
            'observer_msg': "{attacker_name} drags one blade along the wall as they come. A thin bright line follows them."
        },
        {
            'attacker_msg': "You spread your fingers and the claws spread with them, wider than any hand should be.",
            'victim_msg': "{attacker_name} spreads their fingers and the claws spread with them, wider than any hand should be.",
            'observer_msg': "{attacker_name} spreads their fingers and the claws spread with them, wider than any hand should be."
        },
        {
            'attacker_msg': "The leather is dark where someone else's blood dried into it. You add {target_name} to the list.",
            'victim_msg': "The leather of {attacker_name}'s glove is dark where someone else's blood dried into it. You are next on the list.",
            'observer_msg': "The leather of {attacker_name}'s glove is dark where someone else's blood dried into it. {target_name} is next on the list."
        },
        {
            'attacker_msg': "A low stance, claws low. You are not fencing. You are gutting.",
            'victim_msg': "A low stance, claws low. {attacker_name} is not fencing. {attacker_name} is gutting.",
            'observer_msg': "A low stance, claws low. {attacker_name} is not fencing. {attacker_name} is gutting."
        },
        {
            'attacker_msg': "You tap the blades against your thigh, counting nothing. Then you stop counting.",
            'victim_msg': "{attacker_name} taps the blades against their thigh, counting nothing. Then they stop counting.",
            'observer_msg': "{attacker_name} taps the blades against their thigh, counting nothing. Then they stop counting."
        },
        {
            'attacker_msg': "The {item_name} sits snug on your fist, blades forward. Nothing about it is for show.",
            'victim_msg': "The {item_name} sits snug on {attacker_name}'s fist, blades forward. Nothing about it is for show.",
            'observer_msg': "The {item_name} sits snug on {attacker_name}'s fist, blades forward. Nothing about it is for show."
        },
        {
            'attacker_msg': "Blade tips trace small circles in the air. You are warming up. It will not take long.",
            'victim_msg': "Blade tips trace small circles in the air. {attacker_name} is warming up. It will not take long.",
            'observer_msg': "Blade tips trace small circles in the air. {attacker_name} is warming up. It will not take long."
        },
        {
            'attacker_msg': "You take one step and the claws come alive, hooks turning toward {target_name}.",
            'victim_msg': "{attacker_name} takes one step and the claws come alive, hooks turning toward you.",
            'observer_msg': "{attacker_name} takes one step and the claws come alive, hooks turning toward {target_name}."
        },
        {
            'attacker_msg': "Your breathing slows. The hooks don't need you calm, but it helps.",
            'victim_msg': "{attacker_name}'s breathing slows. The hooks don't need them calm, but it helps.",
            'observer_msg': "{attacker_name}'s breathing slows. The hooks don't need them calm, but it helps."
        },
        {
            'attacker_msg': "The claws come up under your chin as you settle, like someone smelling their own blades.",
            'victim_msg': "The claws come up under {attacker_name}'s chin as they settle, like someone smelling their own blades.",
            'observer_msg': "The claws come up under {attacker_name}'s chin as they settle, like someone smelling their own blades."
        },
        {
            'attacker_msg': "One glove, four blades. It is enough.",
            'victim_msg': "One glove, four blades. It is enough.",
            'observer_msg': "One glove, four blades. It is enough."
        },
        {
            'attacker_msg': "You buckle the single claw tight and let the hooks hang at your side.",
            'victim_msg': "{attacker_name} buckles the single claw tight and lets the hooks hang at their side.",
            'observer_msg': "{attacker_name} buckles the single claw tight and lets the hooks hang at their side."
        },
        {
            'attacker_msg': "A lone {item_name}, strap cinched, hooks forward. You lead with it.",
            'victim_msg': "A lone {item_name}, strap cinched, hooks forward. {attacker_name} leads with it.",
            'observer_msg': "A lone {item_name}, strap cinched, hooks forward. {attacker_name} leads with it."
        },
        {
            'attacker_msg': "The claw hand comes up. The rest of you follows.",
            'victim_msg': "The claw hand comes up. The rest of {attacker_name} follows.",
            'observer_msg': "The claw hand comes up. The rest of {attacker_name} follows."
        },
    ],
    'hit': [
        {
            'attacker_msg': "The hooks catch in {target_name}'s {hit_location} and you pull. Cloth and skin come with them.",
            'victim_msg': "The hooks catch in your {hit_location} and {attacker_name} pulls. Cloth and skin come with them.",
            'observer_msg': "The hooks catch in {target_name}'s {hit_location} and {attacker_name} pulls. Cloth and skin come with them."
        },
        {
            'attacker_msg': "A short jab buries the claw tips in the {hit_location}. {target_name} feels every one.",
            'victim_msg': "A short jab buries the claw tips in your {hit_location}. You feel every one.",
            'observer_msg': "A short jab buries the claw tips in {target_name}'s {hit_location}. They feel every one."
        },
        {
            'attacker_msg': "Steel knuckles land first, blades second. {target_name}'s {hit_location} takes it all.",
            'victim_msg': "Steel knuckles land first, blades second. Your {hit_location} takes it all.",
            'observer_msg': "Steel knuckles land first, blades second. {target_name}'s {hit_location} takes it all."
        },
        {
            'attacker_msg': "A rising slash across the {hit_location}. {Blood} runs down the blades to the strap.",
            'victim_msg': "A rising slash across your {hit_location}. {Blood} runs down the blades to the strap.",
            'observer_msg': "A rising slash across {target_name}'s {hit_location}. {Blood} runs down the blades to the strap."
        },
        {
            'attacker_msg': "You drag the hooks across {target_name}'s {hit_location}, slow enough to count the blades.",
            'victim_msg': "{attacker_name} drags the hooks across your {hit_location}, slow enough to count the blades.",
            'observer_msg': "{attacker_name} drags the hooks across {target_name}'s {hit_location}, slow enough to count the blades."
        },
        {
            'attacker_msg': "A hammer blow with the knuckle plate, and the blades follow through the {hit_location}.",
            'victim_msg': "A hammer blow with the knuckle plate, and the blades follow through your {hit_location}.",
            'observer_msg': "A hammer blow with the knuckle plate, and the blades follow through {target_name}'s {hit_location}."
        },
        {
            'attacker_msg': "The {item_name} bites the {hit_location} and holds a heartbeat too long. {target_name} screams into it.",
            'victim_msg': "The {item_name} bites your {hit_location} and holds a heartbeat too long. You scream into it.",
            'observer_msg': "The {item_name} bites {target_name}'s {hit_location} and holds a heartbeat too long. They scream into it."
        },
        {
            'attacker_msg': "A flick of the wrist and the hook tips kiss the {hit_location}. Shallow, red, deliberate.",
            'victim_msg': "A flick of the wrist and the hook tips kiss your {hit_location}. Shallow, red, deliberate.",
            'observer_msg': "A flick of the wrist and the hook tips kiss {target_name}'s {hit_location}. Shallow, red, deliberate."
        },
        {
            'attacker_msg': "You punch through {target_name}'s guard and the claws punch through the {hit_location} behind it.",
            'victim_msg': "{attacker_name} punches through your guard and the claws punch through the {hit_location} behind it.",
            'observer_msg': "{attacker_name} punches through {target_name}'s guard and the claws punch through the {hit_location} behind it."
        },
        {
            'attacker_msg': "The blades skate off bone in {target_name}'s {hit_location} and find softer ground beside it.",
            'victim_msg': "The blades skate off bone in your {hit_location} and find softer ground beside it.",
            'observer_msg': "The blades skate off bone in {target_name}'s {hit_location} and find softer ground beside it."
        },
        {
            'attacker_msg': "A downward rip across the {hit_location}. The glove comes away wet to the buckle.",
            'victim_msg': "A downward rip across your {hit_location}. The glove comes away wet to the buckle.",
            'observer_msg': "A downward rip across {target_name}'s {hit_location}. The glove comes away wet to the buckle."
        },
        {
            'attacker_msg': "Four points enter the {hit_location} as one and leave as one. {target_name} folds around the gap.",
            'victim_msg': "Four points enter your {hit_location} as one and leave as one. You fold around the gap.",
            'observer_msg': "Four points enter {target_name}'s {hit_location} as one and leave as one. They fold around the gap."
        },
        {
            'attacker_msg': "A short hooking punch. The {hit_location} opens like a bad seam.",
            'victim_msg': "A short hooking punch. Your {hit_location} opens like a bad seam.",
            'observer_msg': "A short hooking punch. {target_name}'s {hit_location} opens like a bad seam."
        },
        {
            'attacker_msg': "The claws rake {target_name}'s {hit_location} on the way in and again on the way out.",
            'victim_msg': "The claws rake your {hit_location} on the way in and again on the way out.",
            'observer_msg': "The claws rake {target_name}'s {hit_location} on the way in and again on the way out."
        },
        {
            'attacker_msg': "You lead with the knuckle plate and finish with the hooks. {target_name}'s {hit_location} remembers each.",
            'victim_msg': "{attacker_name} leads with the knuckle plate and finishes with the hooks. Your {hit_location} remembers each.",
            'observer_msg': "{attacker_name} leads with the knuckle plate and finishes with the hooks. {target_name}'s {hit_location} remembers each."
        },
        {
            'attacker_msg': "The hooks snag in the {hit_location}. You twist before you pull free.",
            'victim_msg': "The hooks snag in your {hit_location}. {attacker_name} twists before pulling free.",
            'observer_msg': "The hooks snag in {target_name}'s {hit_location}. {attacker_name} twists before pulling free."
        },
        {
            'attacker_msg': "A slap with an open claw lays the {hit_location} open to the wrist strap.",
            'victim_msg': "A slap with an open claw lays your {hit_location} open to the wrist strap.",
            'observer_msg': "A slap with an open claw lays {target_name}'s {hit_location} open to the wrist strap."
        },
        {
            'attacker_msg': "A single rake across {target_name}'s {hit_location}. Four lines, evenly spaced, filling in red.",
            'victim_msg': "A single rake across your {hit_location}. Four lines, evenly spaced, filling in red.",
            'observer_msg': "A single rake across {target_name}'s {hit_location}. Four lines, evenly spaced, filling in red."
        },
        {
            'attacker_msg': "The lone claw hooks the {hit_location} and you lean your weight on it.",
            'victim_msg': "The lone claw hooks your {hit_location} and {attacker_name} leans their weight on it.",
            'observer_msg': "The lone claw hooks {target_name}'s {hit_location} and {attacker_name} leans their weight on it."
        },
        {
            'attacker_msg': "One glove, one swing, one {hit_location} laid open to the strap.",
            'victim_msg': "One glove, one swing, your {hit_location} laid open to the strap.",
            'observer_msg': "One glove, one swing, {target_name}'s {hit_location} laid open to the strap."
        },
        {
            'attacker_msg': "The {item_name} catches {target_name}'s {hit_location} on the backswing. You weren't even aiming.",
            'victim_msg': "The {item_name} catches your {hit_location} on the backswing. {attacker_name} wasn't even aiming.",
            'observer_msg': "The {item_name} catches {target_name}'s {hit_location} on the backswing. {attacker_name} wasn't even aiming."
        },
    ],
    'miss': [
        {
            'attacker_msg': "The hooks whistle past {target_name}'s face. Close enough to part hair.",
            'victim_msg': "The hooks whistle past your face. Close enough to part hair.",
            'observer_msg': "The hooks whistle past {target_name}'s face. Close enough to part hair."
        },
        {
            'attacker_msg': "Your claw rakes the wall where {target_name} was standing. Four grooves in the plaster.",
            'victim_msg': "{attacker_name}'s claw rakes the wall where you were standing. Four grooves in the plaster.",
            'observer_msg': "{attacker_name}'s claw rakes the wall where {target_name} was standing. Four grooves in the plaster."
        },
        {
            'attacker_msg': "A wild swipe and the blades catch nothing but {target_name}'s sleeve. Cloth parts; skin doesn't.",
            'victim_msg': "A wild swipe and the blades catch nothing but your sleeve. Cloth parts; skin doesn't.",
            'observer_msg': "A wild swipe and the blades catch nothing but {target_name}'s sleeve. Cloth parts; skin doesn't."
        },
        {
            'attacker_msg': "The knuckle plate clips a pipe. The ring hangs in the air longer than it should.",
            'victim_msg': "{attacker_name}'s knuckle plate clips a pipe. The ring hangs in the air longer than it should.",
            'observer_msg': "{attacker_name}'s knuckle plate clips a pipe. The ring hangs in the air longer than it should."
        },
        {
            'attacker_msg': "You overreach and the hooks bite a doorframe instead. Splinters, not blood.",
            'victim_msg': "{attacker_name} overreaches and the hooks bite a doorframe instead. Splinters, not blood.",
            'observer_msg': "{attacker_name} overreaches and the hooks bite a doorframe instead. Splinters, not blood."
        },
        {
            'attacker_msg': "{target_name} sways back and the claw tips stop a finger's width from the throat.",
            'victim_msg': "You sway back and the claw tips stop a finger's width from your throat.",
            'observer_msg': "{target_name} sways back and the claw tips stop a finger's width from their throat."
        },
        {
            'attacker_msg': "The strap slips a notch mid-swing. You lose the line and {target_name} gains a step.",
            'victim_msg': "{attacker_name}'s strap slips a notch mid-swing. They lose the line and you gain a step.",
            'observer_msg': "{attacker_name}'s strap slips a notch mid-swing. They lose the line and {target_name} gains a step."
        },
        {
            'attacker_msg': "Your hook catches a hanging cable and tears it down. Sparks, no screaming.",
            'victim_msg': "{attacker_name}'s hook catches a hanging cable and tears it down. Sparks, no screaming.",
            'observer_msg': "{attacker_name}'s hook catches a hanging cable and tears it down. Sparks, no screaming."
        },
        {
            'attacker_msg': "A low rake meant for the belly finds {target_name}'s belt buckle. Steel on steel.",
            'victim_msg': "A low rake meant for your belly finds your belt buckle. Steel on steel.",
            'observer_msg': "A low rake meant for the belly finds {target_name}'s belt buckle. Steel on steel."
        },
        {
            'attacker_msg': "You lunge and {target_name} is simply elsewhere. The claws close on nothing.",
            'victim_msg': "{attacker_name} lunges and you are simply elsewhere. The claws close on nothing.",
            'observer_msg': "{attacker_name} lunges and {target_name} is simply elsewhere. The claws close on nothing."
        },
        {
            'attacker_msg': "The blades skid across a tabletop and leave it scarred. {target_name} is already past it.",
            'victim_msg': "The blades skid across a tabletop and leave it scarred. You are already past it.",
            'observer_msg': "The blades skid across a tabletop and leave it scarred. {target_name} is already past it."
        },
        {
            'attacker_msg': "A feint from {target_name} draws the swipe early. The hooks tear a poster off the wall.",
            'victim_msg': "Your feint draws the swipe early. The hooks tear a poster off the wall.",
            'observer_msg': "A feint from {target_name} draws the swipe early. The hooks tear a poster off the wall."
        },
        {
            'attacker_msg': "Your backhand sails high. The claws comb {target_name}'s hair and nothing else.",
            'victim_msg': "{attacker_name}'s backhand sails high. The claws comb your hair and nothing else.",
            'observer_msg': "{attacker_name}'s backhand sails high. The claws comb {target_name}'s hair and nothing else."
        },
        {
            'attacker_msg': "The {item_name} glances off something hard under {target_name}'s coat. Steel squeals.",
            'victim_msg': "The {item_name} glances off something hard under your coat. Steel squeals.",
            'observer_msg': "The {item_name} glances off something hard under {target_name}'s coat. Steel squeals."
        },
        {
            'attacker_msg': "You step in and {target_name} steps out. The claws finish the swing alone.",
            'victim_msg': "{attacker_name} steps in and you step out. The claws finish the swing alone.",
            'observer_msg': "{attacker_name} steps in and {target_name} steps out. The claws finish the swing alone."
        },
        {
            'attacker_msg': "The hooks snag your own coat on the follow-through. You tear free, a beat late.",
            'victim_msg': "The hooks snag {attacker_name}'s own coat on the follow-through. They tear free, a beat late.",
            'observer_msg': "The hooks snag {attacker_name}'s own coat on the follow-through. They tear free, a beat late."
        },
        {
            'attacker_msg': "A stab with the claw tips stops in a chair back. The chair takes it badly.",
            'victim_msg': "{attacker_name}'s stab with the claw tips stops in a chair back. The chair takes it badly.",
            'observer_msg': "{attacker_name}'s stab with the claw tips stops in a chair back. The chair takes it badly."
        },
        {
            'attacker_msg': "You swing wide and the strap creaks under the pull. {target_name} is a half-step outside the arc.",
            'victim_msg': "{attacker_name} swings wide and the strap creaks under the pull. You are a half-step outside the arc.",
            'observer_msg': "{attacker_name} swings wide and the strap creaks under the pull. {target_name} is a half-step outside the arc."
        },
        {
            'attacker_msg': "A hooking jab, and the blades drag a line through the dust on the wall. Not through {target_name}.",
            'victim_msg': "A hooking jab, and the blades drag a line through the dust on the wall. Not through you.",
            'observer_msg': "A hooking jab, and the blades drag a line through the dust on the wall. Not through {target_name}."
        },
        {
            'attacker_msg': "The single claw sweeps wide and {target_name} ducks under the arc.",
            'victim_msg': "The single claw sweeps wide and you duck under the arc.",
            'observer_msg': "The single claw sweeps wide and {target_name} ducks under the arc."
        },
        {
            'attacker_msg': "You swing the lone glove and hit the one thing in the room that isn't {target_name}.",
            'victim_msg': "{attacker_name} swings the lone glove and hits the one thing in the room that isn't you.",
            'observer_msg': "{attacker_name} swings the lone glove and hits the one thing in the room that isn't {target_name}."
        },
        {
            'attacker_msg': "The hooks catch on your own sleeve mid-swing. {target_name} is gone by the time they're free.",
            'victim_msg': "The hooks catch on {attacker_name}'s own sleeve mid-swing. You are gone by the time they're free.",
            'observer_msg': "The hooks catch on {attacker_name}'s own sleeve mid-swing. {target_name} is gone by the time they're free."
        },
        {
            'attacker_msg': "A one-handed rake that finds the wall instead of {target_name}. Plaster dust, no blood.",
            'victim_msg': "A one-handed rake that finds the wall instead of you. Plaster dust, no blood.",
            'observer_msg': "A one-handed rake that finds the wall instead of {target_name}. Plaster dust, no blood."
        },
    ],
    'kill': [
        {
            'attacker_msg': "The hooks go into {target_name}'s {hit_location} and come out with the life attached. They drop.",
            'victim_msg': "The hooks go into your {hit_location} and come out with your life attached. You drop.",
            'observer_msg': "The hooks go into {target_name}'s {hit_location} and come out with the life attached. They drop."
        },
        {
            'attacker_msg': "A rising rip through the {hit_location}. {target_name} looks down at it, then stops looking at anything.",
            'victim_msg': "A rising rip through your {hit_location}. You look down at it, then stop looking at anything.",
            'observer_msg': "A rising rip through {target_name}'s {hit_location}. They look down at it, then stop looking at anything."
        },
        {
            'attacker_msg': "The claw hooks the {hit_location} and you tear. {Blood} hits the ceiling before {target_name} hits the floor.",
            'victim_msg': "The claw hooks your {hit_location} and {attacker_name} tears. {Blood} hits the ceiling before you hit the floor.",
            'observer_msg': "The claw hooks {target_name}'s {hit_location} and {attacker_name} tears. {Blood} hits the ceiling before they hit the floor."
        },
        {
            'attacker_msg': "Four blades through the {hit_location}, a twist, and {target_name} goes quiet in the middle of a word.",
            'victim_msg': "Four blades through your {hit_location}, a twist, and you go quiet in the middle of a word.",
            'observer_msg': "Four blades through {target_name}'s {hit_location}, a twist, and they go quiet in the middle of a word."
        },
        {
            'attacker_msg': "A knuckle-plate blow stuns and the hooks finish. {target_name}'s {hit_location} is the last thing they own.",
            'victim_msg': "A knuckle-plate blow stuns and the hooks finish. Your {hit_location} is the last thing you own.",
            'observer_msg': "A knuckle-plate blow stuns and the hooks finish. {target_name}'s {hit_location} is the last thing they own."
        },
        {
            'attacker_msg': "The {item_name} goes into the {hit_location} up to the strap. When it comes out, {target_name} is already somewhere else.",
            'victim_msg': "The {item_name} goes into your {hit_location} up to the strap. When it comes out, you are already somewhere else.",
            'observer_msg': "The {item_name} goes into {target_name}'s {hit_location} up to the strap. When it comes out, {target_name} is already somewhere else."
        },
        {
            'attacker_msg': "A hooking rip across the {hit_location} and the floor gets everything {target_name} was keeping inside.",
            'victim_msg': "A hooking rip across your {hit_location} and the floor gets everything you were keeping inside.",
            'observer_msg': "A hooking rip across {target_name}'s {hit_location} and the floor gets everything they were keeping inside."
        },
        {
            'attacker_msg': "You rake the {hit_location} open and step back to let gravity finish the argument.",
            'victim_msg': "{attacker_name} rakes your {hit_location} open and steps back to let gravity finish the argument.",
            'observer_msg': "{attacker_name} rakes {target_name}'s {hit_location} open and steps back to let gravity finish the argument."
        },
        {
            'attacker_msg': "A downward rip from the {hit_location}. {target_name} sits down carefully and does not get up.",
            'victim_msg': "A downward rip from your {hit_location}. You sit down carefully and do not get up.",
            'observer_msg': "A downward rip from {target_name}'s {hit_location}. They sit down carefully and do not get up."
        },
        {
            'attacker_msg': "The claws catch the {hit_location} and you walk through {target_name}. They stay where they were, in pieces.",
            'victim_msg': "The claws catch your {hit_location} and {attacker_name} walks through you. You stay where you were, in pieces.",
            'observer_msg': "The claws catch {target_name}'s {hit_location} and {attacker_name} walks through them. They stay where they were, in pieces."
        },
        {
            'attacker_msg': "A jab, a hook, a pull. {target_name}'s {hit_location} comes apart in that order.",
            'victim_msg': "A jab, a hook, a pull. Your {hit_location} comes apart in that order.",
            'observer_msg': "A jab, a hook, a pull. {target_name}'s {hit_location} comes apart in that order."
        },
        {
            'attacker_msg': "The hooks open the {hit_location} and {blood} follows them out, all of it, all at once.",
            'victim_msg': "The hooks open your {hit_location} and {blood} follows them out, all of it, all at once.",
            'observer_msg': "The hooks open {target_name}'s {hit_location} and {blood} follows them out, all of it, all at once."
        },
        {
            'attacker_msg': "A last rake through the {hit_location}. {target_name} folds over the blades and slides off them.",
            'victim_msg': "A last rake through your {hit_location}. You fold over the blades and slide off them.",
            'observer_msg': "A last rake through {target_name}'s {hit_location}. They fold over the blades and slide off them."
        },
        {
            'attacker_msg': "The knuckle plate breaks the {hit_location}. The blades make sure. {target_name} is finished twice.",
            'victim_msg': "The knuckle plate breaks your {hit_location}. The blades make sure. You are finished twice.",
            'observer_msg': "The knuckle plate breaks {target_name}'s {hit_location}. The blades make sure. {target_name} is finished twice."
        },
        {
            'attacker_msg': "The claws leave the {hit_location} and {target_name} leaves with them, a dead weight sliding to the floor.",
            'victim_msg': "The claws leave your {hit_location} and you leave with them, a dead weight sliding to the floor.",
            'observer_msg': "The claws leave {target_name}'s {hit_location} and {target_name} leaves with them, a dead weight sliding to the floor."
        },
        {
            'attacker_msg': "A straight punch, blades first, into the {hit_location}. {target_name} stands for one more breath out of habit.",
            'victim_msg': "A straight punch, blades first, into your {hit_location}. You stand for one more breath out of habit.",
            'observer_msg': "A straight punch, blades first, into {target_name}'s {hit_location}. They stand for one more breath out of habit."
        },
        {
            'attacker_msg': "The hooks tear through the {hit_location} and the glove is red to the buckle. {target_name} is red everywhere else.",
            'victim_msg': "The hooks tear through your {hit_location} and the glove is red to the buckle. You are red everywhere else.",
            'observer_msg': "The hooks tear through {target_name}'s {hit_location} and the glove is red to the buckle. {target_name} is red everywhere else."
        },
        {
            'attacker_msg': "A slow pull with the claws set deep in the {hit_location}. {target_name}'s eyes go first; the rest follows.",
            'victim_msg': "A slow pull with the claws set deep in your {hit_location}. Your eyes go first; the rest follows.",
            'observer_msg': "A slow pull with the claws set deep in {target_name}'s {hit_location}. Their eyes go first; the rest follows."
        },
        {
            'attacker_msg': "One claw is enough. It goes into {target_name}'s {hit_location} and the rest is gravity.",
            'victim_msg': "One claw is enough. It goes into your {hit_location} and the rest is gravity.",
            'observer_msg': "One claw is enough. It goes into {target_name}'s {hit_location} and the rest is gravity."
        },
        {
            'attacker_msg': "The lone glove hooks the {hit_location} and tears it open. {target_name} is still for the first time all day.",
            'victim_msg': "The lone glove hooks your {hit_location} and tears it open. You are still for the first time all day.",
            'observer_msg': "The lone glove hooks {target_name}'s {hit_location} and tears it open. {target_name} is still for the first time all day."
        },
        {
            'attacker_msg': "A single rake, deep, through the {hit_location}. {target_name} drops before the strap stops creaking.",
            'victim_msg': "A single rake, deep, through your {hit_location}. You drop before the strap stops creaking.",
            'observer_msg': "A single rake, deep, through {target_name}'s {hit_location}. They drop before the strap stops creaking."
        },
        {
            'attacker_msg': "The {item_name} opens the {hit_location} with one pull. {target_name} empties onto the floor.",
            'victim_msg': "The {item_name} opens your {hit_location} with one pull. You empty onto the floor.",
            'observer_msg': "The {item_name} opens {target_name}'s {hit_location} with one pull. They empty onto the floor."
        },
    ],
}
