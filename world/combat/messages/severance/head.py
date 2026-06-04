"""Head severance templates — decapitation narrative for combat.

Fires when an edged hit (cut / stab / laceration) destroys the cervical
spine, flagging ``decapitation_pending``. Narrative focuses on the head
parting from the body, not on the neck wound itself.

See ``world/combat/messages/severance/__init__.py`` for the loader and
``MESSAGES`` schema.
"""

MESSAGES = {
    "cut": {
        "grievous": [
            {
                "attacker_msg": "Your blade carves through {target_name}'s neck in a single brutal arc. Their head spins free, eyes still tracking nothing, and meets the deck with a wet crack.",
                "victim_msg": "{attacker_name}'s blade carves through your neck in a single brutal arc. Your head spins free, eyes still tracking nothing.",
                "observer_msg": "{attacker_name}'s blade carves through {target_name}'s neck in a single brutal arc. Their head spins free, eyes still tracking nothing, and meets the deck with a wet crack.",
            },
            {
                "attacker_msg": "The cut is too deep, too fast. {target_name}'s head topples backward before the body knows it has lost its anchor — blood plumes in a wide red column.",
                "victim_msg": "The cut is too deep, too fast. Your head topples backward before the body knows it has lost its anchor.",
                "observer_msg": "The cut is too deep, too fast. {target_name}'s head topples backward before the body knows it has lost its anchor — blood plumes in a wide red column.",
            },
            {
                "attacker_msg": "You hew through {target_name}'s neck and feel the resistance vanish mid-stroke. Their head drops to the ground, mouth open in a question that will never close.",
                "victim_msg": "{attacker_name} hews through your neck and the resistance vanishes mid-stroke. Your head drops, mouth open in a question that will never close.",
                "observer_msg": "{attacker_name} hews through {target_name}'s neck and the resistance vanishes mid-stroke. The head drops to the ground, mouth open in a question that will never close.",
            },
            {
                "attacker_msg": "Bone parts like wet wood. {target_name}'s head sails free, trailing a slow rope of red, and hits the floor before the body has begun to fall.",
                "victim_msg": "Bone parts like wet wood. Your head sails free, trailing a slow rope of red.",
                "observer_msg": "Bone parts like wet wood. {target_name}'s head sails free, trailing a slow rope of red, and hits the floor before the body has begun to fall.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "One stroke. {target_name}'s head leaves the body in something almost ceremonial, and the cut is so clean it might have been mistaken for an act of mercy.",
                "victim_msg": "One stroke. Your head leaves your body in something almost ceremonial.",
                "observer_msg": "One stroke. {target_name}'s head leaves the body in something almost ceremonial, and the cut is so clean it might have been mistaken for an act of mercy.",
            },
            {
                "attacker_msg": "The edge passes through {target_name}'s neck without protest. The head settles to the floor with the soft weight of an offering.",
                "victim_msg": "The edge passes through your neck without protest. Your head settles to the floor with the soft weight of an offering.",
                "observer_msg": "The edge passes through {target_name}'s neck without protest. The head settles to the floor with the soft weight of an offering.",
            },
            {
                "attacker_msg": "A clean line opens beneath {target_name}'s jaw and the head simply detaches, gravity claiming what's no longer held.",
                "victim_msg": "A clean line opens beneath your jaw and your head simply detaches, gravity claiming what's no longer held.",
                "observer_msg": "A clean line opens beneath {target_name}'s jaw and the head simply detaches, gravity claiming what's no longer held.",
            },
            {
                "attacker_msg": "Your blade finds the joint between vertebrae and the head parts from the body without a single ragged fibre — surgical, almost respectful.",
                "victim_msg": "{attacker_name}'s blade finds the joint between your vertebrae and your head parts from your body without a single ragged fibre.",
                "observer_msg": "{attacker_name}'s blade finds the joint between {target_name}'s vertebrae and the head parts from the body without a single ragged fibre — surgical, almost respectful.",
            },
        ],
    },
    "stab": {
        "grievous": [
            {
                "attacker_msg": "You drive the point through {target_name}'s throat and *twist*. The neck gives up its structure all at once, and the head sags loose, then falls.",
                "victim_msg": "{attacker_name} drives the point through your throat and *twists*. The neck gives up its structure all at once.",
                "observer_msg": "{attacker_name} drives the point through {target_name}'s throat and *twists*. The neck gives up its structure all at once, and the head sags loose, then falls.",
            },
            {
                "attacker_msg": "The point goes deep and keeps going, tearing through bone and sinew until {target_name}'s head hangs by a flap of skin. Then that gives too.",
                "victim_msg": "{attacker_name}'s point goes deep and keeps going, tearing through bone and sinew until your head hangs by a flap of skin. Then that gives too.",
                "observer_msg": "{attacker_name}'s point goes deep and keeps going, tearing through bone and sinew until {target_name}'s head hangs by a flap of skin. Then that gives too.",
            },
            {
                "attacker_msg": "Impalement becomes amputation. {target_name}'s head jerks once on the blade, then slides free, leaving the body to discover its absence.",
                "victim_msg": "Impalement becomes amputation. Your head jerks once on the blade, then slides free.",
                "observer_msg": "Impalement becomes amputation. {target_name}'s head jerks once on the blade, then slides free, leaving the body to discover its absence.",
            },
            {
                "attacker_msg": "You shove the point up under {target_name}'s jaw and *pull*. Vertebrae splinter outward and the head comes loose, dangling on rags of tissue, then dropping.",
                "victim_msg": "{attacker_name} shoves the point up under your jaw and *pulls*. Vertebrae splinter outward and your head comes loose.",
                "observer_msg": "{attacker_name} shoves the point up under {target_name}'s jaw and *pulls*. Vertebrae splinter outward and the head comes loose, dangling on rags of tissue, then dropping.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The point slips between vertebrae and the head detaches as cleanly as plucking fruit. {target_name} never had time to register the betrayal.",
                "victim_msg": "The point slips between your vertebrae and your head detaches as cleanly as plucking fruit.",
                "observer_msg": "The point slips between {target_name}'s vertebrae and the head detaches as cleanly as plucking fruit. They never had time to register the betrayal.",
            },
            {
                "attacker_msg": "A surgical thrust through the precise gap. {target_name}'s head separates and you ease it down with something approaching tenderness.",
                "victim_msg": "{attacker_name}'s surgical thrust finds the precise gap. Your head separates and is eased down with something approaching tenderness.",
                "observer_msg": "{attacker_name}'s surgical thrust finds the precise gap. {target_name}'s head separates and is eased down with something approaching tenderness.",
            },
            {
                "attacker_msg": "The blade enters where it must and exits with the head no longer attached — a single moment of mechanical perfection.",
                "victim_msg": "{attacker_name}'s blade enters where it must and exits with your head no longer attached — a single moment of mechanical perfection.",
                "observer_msg": "{attacker_name}'s blade enters where it must and exits with {target_name}'s head no longer attached — a single moment of mechanical perfection.",
            },
            {
                "attacker_msg": "You find the joint without looking, slide through, and {target_name}'s head leaves the body without complaint or spectacle.",
                "victim_msg": "{attacker_name} finds the joint without looking, slides through, and your head leaves your body without complaint or spectacle.",
                "observer_msg": "{attacker_name} finds the joint without looking, slides through, and {target_name}'s head leaves the body without complaint or spectacle.",
            },
        ],
    },
    "laceration": {
        "grievous": [
            {
                "attacker_msg": "Teeth and torque take {target_name}'s head off in pieces. Bone fragments and tissue spray outward while the engine's note doesn't change.",
                "victim_msg": "Teeth and torque take your head off in pieces. Bone and tissue spray outward.",
                "observer_msg": "Teeth and torque take {target_name}'s head off in pieces. Bone fragments and tissue spray outward while the engine's note doesn't change.",
            },
            {
                "attacker_msg": "The blade catches, drags, and *grinds*. {target_name}'s head comes apart at the neck in a slurry of red, and what's left of it lands separately.",
                "victim_msg": "{attacker_name}'s blade catches, drags, and *grinds*. Your head comes apart at the neck in a slurry of red.",
                "observer_msg": "{attacker_name}'s blade catches, drags, and *grinds*. {target_name}'s head comes apart at the neck in a slurry of red, and what's left of it lands separately.",
            },
            {
                "attacker_msg": "You saw, you tear, you *rip*. {target_name}'s head leaves the body in a single ragged motion, ribbons of meat trailing after it like banners.",
                "victim_msg": "{attacker_name} saws, tears, *rips*. Your head leaves your body in a single ragged motion.",
                "observer_msg": "{attacker_name} saws, tears, *rips*. {target_name}'s head leaves the body in a single ragged motion, ribbons of meat trailing after it like banners.",
            },
            {
                "attacker_msg": "Chain teeth chew through {target_name}'s neck in a wet, mechanical lullaby. The head spins free, hair clogging the bar, and the body keeps standing for one heartbeat too long.",
                "victim_msg": "Chain teeth chew through your neck in a wet, mechanical lullaby. The head spins free.",
                "observer_msg": "Chain teeth chew through {target_name}'s neck in a wet, mechanical lullaby. The head spins free, hair clogging the bar, and the body keeps standing for one heartbeat too long.",
            },
        ],
        "minor": [
            {
                "attacker_msg": "The cut is rough but final. {target_name}'s head comes free in a single tearing pull, the wound ragged but undeniable.",
                "victim_msg": "{attacker_name}'s cut is rough but final. Your head comes free in a single tearing pull.",
                "observer_msg": "{attacker_name}'s cut is rough but final. {target_name}'s head comes free in a single tearing pull, the wound ragged but undeniable.",
            },
            {
                "attacker_msg": "Serrated edge catches, then breaks through. {target_name}'s head is off in a moment that's neither clean nor uncertain.",
                "victim_msg": "{attacker_name}'s serrated edge catches, then breaks through. Your head is off in a moment that's neither clean nor uncertain.",
                "observer_msg": "{attacker_name}'s serrated edge catches, then breaks through. {target_name}'s head is off in a moment that's neither clean nor uncertain.",
            },
            {
                "attacker_msg": "You drag the blade across {target_name}'s neck and feel the connection give in a series of small surrenders, the head loosening, then detaching.",
                "victim_msg": "{attacker_name} drags the blade across your neck and the connection gives in a series of small surrenders.",
                "observer_msg": "{attacker_name} drags the blade across {target_name}'s neck and the connection gives in a series of small surrenders, the head loosening, then detaching.",
            },
            {
                "attacker_msg": "The tear is uneven but complete. {target_name}'s head leaves the body in a moment that asks for no witnesses but gets them anyway.",
                "victim_msg": "The tear is uneven but complete. Your head leaves your body in a moment that asks for no witnesses.",
                "observer_msg": "The tear is uneven but complete. {target_name}'s head leaves the body in a moment that asks for no witnesses but gets them anyway.",
            },
        ],
    },
}
