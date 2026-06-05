MESSAGES = {
    # --- Grapple Maneuver Messages ---
    "hit": [  # Action: Successful grapple INITIATION (attacker initiates, target is victim)
        {
            "attacker_msg": "You lunge, wrapping {target_name} in a crushing embrace!",
            "victim_msg": "{attacker_name} lunges, wrapping you in a crushing embrace!",
            "observer_msg": "{attacker_name} lunges, wrapping {target_name} in a crushing embrace."
        },
        {
            "attacker_msg": "You shoot in, locking your {hit_location}s around {target_name}'s {hit_location}!",
            "victim_msg": "{attacker_name} shoots in, locking their arms around your {hit_location}!",
            "observer_msg": "{attacker_name} shoots in, locking their arms around {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "You make {target_name} stumble as you tie them up in a powerful grapple!",
            "victim_msg": "You stumble as {attacker_name} ties you up in a powerful grapple!",
            "observer_msg": "{target_name} stumbles as {attacker_name} ties them up in a powerful grapple."
        },
        {
            "attacker_msg": "You close the distance, snaring {target_name} in a tight hold!",
            "victim_msg": "{attacker_name} closes the distance, snaring you in a tight hold!",
            "observer_msg": "{attacker_name} closes the distance, snaring {target_name} in a tight hold."
        },
        {
            "attacker_msg": "With a grunt, you get a firm grip on {target_name}, immobilizing them!",
            "victim_msg": "With a grunt, {attacker_name} gets a firm grip on you, immobilizing you!",
            "observer_msg": "With a grunt, {attacker_name} gets a firm grip on {target_name}, immobilizing them."
        },
        {
            "attacker_msg": "You dive and clinch {target_name}, muscles straining!",
            "victim_msg": "{attacker_name} dives and clinches you, muscles straining!",
            "observer_msg": "{attacker_name} dives and clinches {target_name}, muscles straining."
        },
        {
            "attacker_msg": "You catch {target_name} off guard, latching on with an iron grip!",
            "victim_msg": "You are caught off guard as {attacker_name} latches on with an iron grip!",
            "observer_msg": "{target_name} is caught off guard as {attacker_name} latches on with an iron grip."
        },
        {
            "attacker_msg": "You smother {target_name}, initiating a close-quarters struggle!",
            "victim_msg": "{attacker_name} smothers you, initiating a close-quarters struggle!",
            "observer_msg": "{attacker_name} smothers {target_name}, initiating a close-quarters struggle."
        },
        {
            "attacker_msg": "You take the fight to the ground, tackling and grappling {target_name}!",
            "victim_msg": "The fight goes to the ground as {attacker_name} tackles and grapples you!",
            "observer_msg": "The fight goes to the ground as {attacker_name} tackles and grapples {target_name}."
        },
        {
            "attacker_msg": "You expertly maneuver into a controlling grapple on {target_name}!",
            "victim_msg": "{attacker_name} expertly maneuvers into a controlling grapple on you!",
            "observer_msg": "{attacker_name} expertly maneuvers into a controlling grapple on {target_name}."
        },
        {
            "attacker_msg": "You make {target_name} flail as you secure a dominant grappling position!",
            "victim_msg": "You flail as {attacker_name} secures a dominant grappling position!",
            "observer_msg": "{target_name} flails as {attacker_name} secures a dominant grappling position."
        },
        {
            "attacker_msg": "You bind {target_name} up, like a predator coiling around its prey!",
            "victim_msg": "{attacker_name} binds you up, like a predator coiling around its prey!",
            "observer_msg": "{attacker_name} binds {target_name} up, a predator coiling around its prey."
        },
        {
            "attacker_msg": "You explode forward, entangling {target_name} before they can react!",
            "victim_msg": "{attacker_name} explodes forward, entangling you before you can react!",
            "observer_msg": "{attacker_name} explodes forward, entangling {target_name} before they can react."
        },
        {
            "attacker_msg": "Like a vise, your {hit_location}s clamp around {target_name}!",
            "victim_msg": "Like a vise, {attacker_name}'s {hit_location}s clamp around you!",
            "observer_msg": "Like a vise, {attacker_name}'s {hit_location}s clamp around {target_name}."
        },
        {
            "attacker_msg": "You drag {target_name} into a messy, desperate clinch!",
            "victim_msg": "{attacker_name} drags you into a messy, desperate clinch!",
            "observer_msg": "{attacker_name} drags {target_name} into a messy, desperate clinch."
        },
        {
            "attacker_msg": "You make {target_name} gasp as you overpower them into a grapple!",
            "victim_msg": "You gasp as {attacker_name} overpowers you into a grapple!",
            "observer_msg": "{target_name} gasps as {attacker_name} overpowers them into a grapple."
        },
        {
            "attacker_msg": "You use sheer force to bring {target_name} into a suffocating hold!",
            "victim_msg": "{attacker_name} uses sheer force to bring you into a suffocating hold!",
            "observer_msg": "{attacker_name} uses sheer force to bring {target_name} into a suffocating hold."
        },
        {
            "attacker_msg": "The world shrinks for {target_name} as you lock them in a grapple!",
            "victim_msg": "The world shrinks for you as {attacker_name} locks you in a grapple!",
            "observer_msg": "The world shrinks for {target_name} as {attacker_name} locks them in a grapple."
        },
        {
            "attacker_msg": "You weave through {target_name}'s defenses and establish a grapple!",
            "victim_msg": "{attacker_name} weaves through your defenses and establishes a grapple!",
            "observer_msg": "{attacker_name} weaves through {target_name}'s defenses and establishes a grapple."
        },
        {
            "attacker_msg": "With surprising speed, you close in and grapple {target_name}!",
            "victim_msg": "With surprising speed, {attacker_name} closes in and grapples you!",
            "observer_msg": "With surprising speed, {attacker_name} closes in and grapples {target_name}."
        },
        {
            "attacker_msg": "You get under {target_name}'s guard, initiating a tight grapple!",
            "victim_msg": "{attacker_name} gets under your guard, initiating a tight grapple!",
            "observer_msg": "{attacker_name} gets under {target_name}'s guard, initiating a tight grapple."
        },
        {
            "attacker_msg": "You ensnare {target_name} with your relentless grappling advance!",
            "victim_msg": "You are ensnared by {attacker_name}'s relentless grappling advance!",
            "observer_msg": "{target_name} is ensnared by {attacker_name}'s relentless grappling advance."
        },
        {
            "attacker_msg": "You muscle {target_name} into a disadvantageous grappling position!",
            "victim_msg": "{attacker_name} muscles you into a disadvantageous grappling position!",
            "observer_msg": "{attacker_name} muscles {target_name} into a disadvantageous grappling position."
        },
        {
            "attacker_msg": "A sudden shift, and you have {target_name} all tied up!",
            "victim_msg": "A sudden shift, and {attacker_name} has you all tied up!",
            "observer_msg": "A sudden shift, and {attacker_name} has {target_name} all tied up."
        },
        {
            "attacker_msg": "You grab hold of {target_name}, a look of grim determination on your {hit_location}!",
            "victim_msg": "{attacker_name} grabs hold of you, a look of grim determination on their face!",
            "observer_msg": "{attacker_name} grabs hold of {target_name}, a look of grim determination on their {hit_location}."
        },
        {
            "attacker_msg": "{target_name} finds themselves trapped in your unyielding grapple!",
            "victim_msg": "You find yourself trapped in {attacker_name}'s unyielding grapple!",
            "observer_msg": "{target_name} finds themselves trapped in {attacker_name}'s unyielding grapple."
        },
        {
            "attacker_msg": "You initiate a grapple, turning the fight with {target_name} into a test of strength!",
            "victim_msg": "{attacker_name} initiates a grapple, turning the fight with you into a test of strength!",
            "observer_msg": "{attacker_name} initiates a grapple, turning the fight with {target_name} into a test of strength."
        },
        {
            "attacker_msg": "The space between you and {target_name} vanishes as you grapple them!",
            "victim_msg": "The space between you and {attacker_name} vanishes as they grapple you!",
            "observer_msg": "The space between {attacker_name} and {target_name} vanishes as they grapple."
        },
        {
            "attacker_msg": "You secure a hold on {target_name}, and the real fight begins!",
            "victim_msg": "{attacker_name} secures a hold on you, and the real fight begins!",
            "observer_msg": "{attacker_name} secures a hold on {target_name}, and the real fight begins."
        },
        {
            "attacker_msg": "With a roar, you charge and lock {target_name} in a powerful grapple!",
            "victim_msg": "With a roar, {attacker_name} charges and locks you in a powerful grapple!",
            "observer_msg": "With a roar, {attacker_name} charges and locks {target_name} in a powerful grapple."
        },
    ],
    "miss": [  # Action: Failed grapple INITIATION (attacker attempts, target is victim)
        {
            "attacker_msg": "You attempt to grapple {target_name}, but they slip away!",
            "victim_msg": "{attacker_name} tries to grapple you, but you manage to evade their grasp!",
            "observer_msg": "{attacker_name} attempts to grapple {target_name}, but {target_name} slips away."
        },
        {
            "attacker_msg": "Your lunge for {target_name} misses, leaving you off balance.",
            "victim_msg": "{attacker_name}'s lunge misses you, leaving them off balance.",
            "observer_msg": "{attacker_name}'s lunge for {target_name} misses, leaving them off balance."
        },
        {
            "attacker_msg": "{target_name} sidesteps your grapple attempt easily.",
            "victim_msg": "You sidestep {attacker_name}'s grapple attempt easily.",
            "observer_msg": "{target_name} sidesteps {attacker_name}'s grapple attempt easily."
        },
        # ... (add more variations for failed grapple initiation as needed)
    ],
    "escape_hit": [  # Action: Successfully ESCAPING a grapple (attacker=escaper, target=grappler)
        {
            "attacker_msg": "You wrench yourself free from {target_name}'s hold!",
            "victim_msg": "{attacker_name} wrenches themselves free from your hold!",
            "observer_msg": "{attacker_name} wrenches themselves free from {target_name}'s hold."
        },
        {
            "attacker_msg": "With a burst of effort, you shove {target_name} away and break the grapple!",
            "victim_msg": "{attacker_name} shoves you with a burst of effort, breaking your grapple!",
            "observer_msg": "{attacker_name} shoves {target_name} away, breaking the grapple."
        },
        # ... (add more variations)
    ],
    "escape_miss": [  # Action: Failing to ESCAPE a grapple (attacker=escaper, target=grappler)
        {
            "attacker_msg": "You struggle, but {target_name} maintains their tight grip on you.",
            "victim_msg": "{attacker_name} struggles, but you maintain your tight grip on them.",
            "observer_msg": "{attacker_name} struggles, but {target_name} maintains their tight grip."
        },
        {
            "attacker_msg": "Your attempt to break {target_name}'s hold is futile; they're too strong.",
            "victim_msg": "{attacker_name} tries to break your hold, but you are too strong.",
            "observer_msg": "{attacker_name} fails to break {target_name}'s hold."
        },
        # ... (add more variations)
    ],
    "release": [  # Action: Voluntarily RELEASING a grapple (attacker=releaser, target=released)
        {
            "attacker_msg": "You decide to release your hold on {target_name}.",
            "victim_msg": "{attacker_name} releases their hold on you. You are free!",
            "observer_msg": "{attacker_name} releases their hold on {target_name}."
        },
        {
            "attacker_msg": "You shove {target_name} away, ending the grapple.",
            "victim_msg": "{attacker_name} shoves you away, ending the grapple.",
            "observer_msg": "{attacker_name} shoves {target_name} away, ending their grapple."
        },
        # ... (add more variations)
    ],

    # --- Messages for ATTACKS/DAMAGE while ALREADY grappling ---
    "grapple_damage_hit": [  # Action: Successfully damaging a grappled opponent
        {
            "attacker_msg": "You squeeze the air from {target_name}'s {hit_location} in the grapple.",
            "victim_msg": "{attacker_name} squeezes the air from your {hit_location} in the grapple!",
            "observer_msg": "{attacker_name} squeezes the air from {target_name}'s {hit_location} in the grapple."
        },
        {
            "attacker_msg": "Locked tight, you drive a knee into {target_name}'s {hit_location}.",
            "victim_msg": "Locked tight, {attacker_name} drives a knee into your {hit_location}!",
            "observer_msg": "Locked tight, {attacker_name} drives a knee into {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "You grind your {hit_location} across {target_name}'s {hit_location}.",
            "victim_msg": "{attacker_name} grinds their forearm across your {hit_location}!",
            "observer_msg": "{attacker_name} grinds their forearm across {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "While grappling, you land a series of short, brutal punches to {target_name}'s side.",
            "victim_msg": "While grappling, {attacker_name} lands a series of short, brutal punches to your side!",
            "observer_msg": "While grappling, {attacker_name} lands a series of short, brutal punches to {target_name}'s side."
        },
        {
            "attacker_msg": "You twist {target_name}'s limb at an unnatural angle, causing a pained yelp.",
            "victim_msg": "{attacker_name} twists your limb at an unnatural angle, causing you to yelp in pain!",
            "observer_msg": "{attacker_name} twists {target_name}'s limb at an unnatural angle, causing a pained yelp."
        },
        {
            "attacker_msg": "Pinning {target_name}, you deliver a vicious headbutt.",
            "victim_msg": "Pinned by {attacker_name}, you suffer a vicious headbutt!",
            "observer_msg": "Pinning {target_name}, {attacker_name} delivers a vicious headbutt."
        },
        {
            "attacker_msg": "You choke {target_name}, who claws desperately at your arms.",
            "victim_msg": "{attacker_name} chokes you; you claw desperately at their arms!",
            "observer_msg": "{attacker_name} chokes {target_name}, who claws desperately at their arms."
        },
        {
            "attacker_msg": "In the clinch, you slam an elbow into {target_name}'s {hit_location}.",
            "victim_msg": "In the clinch, {attacker_name} slams an elbow into your {hit_location}!",
            "observer_msg": "In the clinch, {attacker_name} slams an elbow into {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "You use your leverage to crush {target_name} against the ground.",
            "victim_msg": "{attacker_name} uses their leverage to crush you against the ground!",
            "observer_msg": "{attacker_name} uses their leverage to crush {target_name} against the ground."
        },
        {
            "attacker_msg": "A sickening crunch is heard as you apply pressure to {target_name}'s joint.",
            "victim_msg": "A sickening crunch is heard as {attacker_name} applies pressure to your joint!",
            "observer_msg": "A sickening crunch is heard as {attacker_name} applies pressure to {target_name}'s joint."
        },
        {
            "attacker_msg": "You bite down hard on {target_name} amidst the struggle.",
            "victim_msg": "{attacker_name} bites down hard on you amidst the struggle!",
            "observer_msg": "{attacker_name} bites down hard on {target_name} amidst the struggle."
        },
        {
            "attacker_msg": "You smash {target_name}'s {hit_location} into the pavement while maintaining the hold.",
            "victim_msg": "{attacker_name} smashes your {hit_location} into the pavement while maintaining the hold!",
            "observer_msg": "{attacker_name} smashes {target_name}'s {hit_location} into the pavement while maintaining the hold."
        },
        {
            "attacker_msg": "Trapped in the grapple, {target_name} takes a nasty shot to the kidney from you.",
            "victim_msg": "Trapped in the grapple, you take a nasty shot to the kidney from {attacker_name}!",
            "observer_msg": "Trapped in the grapple, {target_name} takes a nasty shot to the kidney from {attacker_name}."
        },
        {
            "attacker_msg": "You wrench {target_name}'s {hit_location}, drawing a choked cry.",
            "victim_msg": "{attacker_name} wrenches your {hit_location}, drawing a choked cry from you!",
            "observer_msg": "{attacker_name} wrenches {target_name}'s {hit_location}, drawing a choked cry."
        },
        {
            "attacker_msg": "With {target_name} immobilized, you land a precise, painful strike.",
            "victim_msg": "Immobilized by {attacker_name}, you suffer a precise, painful strike!",
            "observer_msg": "With {target_name} immobilized, {attacker_name} lands a precise, painful strike."
        },
        {
            "attacker_msg": "You dig your knuckles into a pressure point on {target_name}.",
            "victim_msg": "{attacker_name} digs their knuckles into a pressure point on you!",
            "observer_msg": "{attacker_name} digs their knuckles into a pressure point on {target_name}."
        },
        {
            "attacker_msg": "A short, sharp elbow from you cracks against {target_name}'s {hit_location}.",
            "victim_msg": "A short, sharp elbow from {attacker_name} cracks against your {hit_location}!",
            "observer_msg": "A short, sharp elbow from {attacker_name} cracks against {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "You use the grapple to slam {target_name} into a nearby object.",
            "victim_msg": "{attacker_name} uses the grapple to slam you into a nearby object!",
            "observer_msg": "{attacker_name} uses the grapple to slam {target_name} into a nearby object."
        },
        {
            "attacker_msg": "{target_name} groans as you apply a painful submission hold.",
            "victim_msg": "You groan as {attacker_name} applies a painful submission hold!",
            "observer_msg": "{target_name} groans as {attacker_name} applies a painful submission hold."
        },
        {
            "attacker_msg": "You drive your {hit_location} repeatedly into {target_name}'s {hit_location}.",
            "victim_msg": "{attacker_name} drives their shoulder repeatedly into your {hit_location}!",
            "observer_msg": "{attacker_name} drives their shoulder repeatedly into {target_name}'s {hit_location}."
        },
        {
            "attacker_msg": "In the tight confines of the grapple, you gouge at {target_name}'s eyes.",
            "victim_msg": "In the tight confines of the grapple, {attacker_name} gouges at your eyes!",
            "observer_msg": "In the tight confines of the grapple, {attacker_name} gouges at {target_name}'s eyes."
        },
        {
            "attacker_msg": "You pull {target_name}'s hair, yanking their head into a knee strike.",
            "victim_msg": "{attacker_name} pulls your hair, yanking your {hit_location} into a knee strike!",
            "observer_msg": "{attacker_name} pulls {target_name}'s hair, yanking their head into a knee strike."
        },
        {
            "attacker_msg": "A brutal fist from you finds {target_name}'s exposed liver.",
            "victim_msg": "A brutal fist from {attacker_name} finds your exposed liver!",
            "observer_msg": "A brutal fist from {attacker_name} finds {target_name}'s exposed liver."
        },
        {
            "attacker_msg": "You systematically break down {target_name}'s defense in the grapple.",
            "victim_msg": "{attacker_name} systematically breaks down your defense in the grapple!",
            "observer_msg": "{attacker_name} systematically breaks down {target_name}'s defense in the grapple."
        },
        {
            "attacker_msg": "The pressure from your hold intensifies, causing {target_name} to cry out.",
            "victim_msg": "The pressure from {attacker_name}'s hold intensifies, causing you to cry out!",
            "observer_msg": "The pressure from {attacker_name}'s hold intensifies, causing {target_name} to cry out."
        },
        {
            "attacker_msg": "You land a flurry of body blows while maintaining control of {target_name}.",
            "victim_msg": "{attacker_name} lands a flurry of body blows on you while maintaining control!",
            "observer_msg": "{attacker_name} lands a flurry of body blows on {target_name} while maintaining control."
        },
        {
            "attacker_msg": "{target_name}'s vision blurs as you apply a blood choke.",
            "victim_msg": "Your vision blurs as {attacker_name} applies a blood choke!",
            "observer_msg": "{target_name}'s vision blurs as {attacker_name} applies a blood choke."
        },
        {
            "attacker_msg": "You use your weight to smother and strike {target_name}.",
            "victim_msg": "{attacker_name} uses their weight to smother and strike you!",
            "observer_msg": "{attacker_name} uses their weight to smother and strike {target_name}."
        },
        {
            "attacker_msg": "A well-placed strike from you nearly makes {target_name} pass out.",
            "victim_msg": "A well-placed strike from {attacker_name} nearly makes you pass out!",
            "observer_msg": "A well-placed strike from {attacker_name} nearly makes {target_name} pass out."
        },
        {
            "attacker_msg": "You whisper a threat to {target_name} before delivering another painful blow.",
            "victim_msg": "{attacker_name} whispers a threat to you before delivering another painful blow!",
            "observer_msg": "{attacker_name} whispers a threat to {target_name} before delivering another painful blow."
        },
    ],
    "grapple_damage_miss": [  # Action: Failing to damage, or target defends while grappled
        {
            "attacker_msg": "You try to land a blow, but {target_name} squirms, preventing a clean hit in the grapple.",
            "victim_msg": "You squirm, preventing {attacker_name} from landing a clean blow on you in the grapple.",
            "observer_msg": "{target_name} squirms, preventing {attacker_name} from landing a clean blow in the grapple."
        },
        {
            "attacker_msg": "You struggle to improve your position, but {target_name} defends fiercely.",
            "victim_msg": "{attacker_name} struggles to improve their position, but you defend fiercely.",
            "observer_msg": "{attacker_name} struggles to improve their position, while {target_name} defends fiercely."
        },
        {
            "attacker_msg": "Your choke attempt slips as {target_name} bucks wildly.",
            "victim_msg": "You buck wildly, causing {attacker_name}'s choke attempt to slip.",
            "observer_msg": "{target_name} bucks wildly, causing {attacker_name}'s choke attempt to slip."
        },
        {
            "attacker_msg": "Despite your hold, {target_name} manages to block your strike.",
            "victim_msg": "Despite the hold, you manage to block {attacker_name}'s strike.",
            "observer_msg": "Despite the hold, {target_name} manages to block {attacker_name}'s strike."
        },
        {
            "attacker_msg": "You try to apply a submission, but {target_name} wriggles free of the worst of it.",
            "victim_msg": "{attacker_name} tries to apply a submission, but you wriggle free of the worst of it.",
            "observer_msg": "{attacker_name} tries to apply a submission, but {target_name} wriggles free of the worst of it."
        },
        # ... (Continue converting the rest of your "miss" messages here)
    ],
    "grapple_damage_kill": [ # Action: Defeating/killing a target while grappling
        {
            "attacker_msg": "You choke the life out of {target_name}, who goes limp in your grasp.",
            "victim_msg": "{attacker_name} chokes the life out of you! Everything fades to black...",
            "observer_msg": "{attacker_name} chokes the life out of {target_name}, who goes limp in their grasp."
        },
        {
            "attacker_msg": "With a final, brutal twist, you snap something vital and {target_name} stops moving.",
            "victim_msg": "With a final, brutal twist, {attacker_name} snaps something vital... you feel your life fade.",
            "observer_msg": "With a final, brutal twist, {attacker_name} snaps something vital and {target_name} stops moving."
        },
        # ... (Continue converting the rest of your "kill" messages here)
    ]
}