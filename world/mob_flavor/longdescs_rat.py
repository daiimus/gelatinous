"""Longdesc templates for spawned rats.

Per-location prose seeded into ``mob.longdesc[location]``. Same
token conventions as the human module:

* Pair-keyed nouns wrapped in braces (``{eyes}`` / ``{ears}`` /
  ``{forelegs}`` / ``{forepaws}`` / ``{hindlegs}`` / ``{hindpaws}``)
  so the renderer can flex them when one side collapses.
* Verbs whose subject is a paired body noun braced too (e.g.
  ``{Their} {eyes} {are} small`` → ``His left eye is small`` when
  one side is severed).
* Singular locations (``fur``, ``snout``, ``neck``, ``tail`` ...)
  use plain prose with pronoun tokens.

Slot keys mirror ``world/anatomy/species.py``'s rat
``pair_keys`` / ``default_longdesc_locations``.
"""

from __future__ import annotations

LONGDESCS_RAT: dict[str, list[str]] = {
    # Head / face region
    "fur": [
        "{Their} fur is short and slate-grey, slightly oily where it covers the back.",
        "{Their} coat is a patchwork of browns, scuffed at the shoulders and clean at the throat.",
        "{Their} fur is dark and slick with the look of having been recently washed by rain or canal water.",
        "{Their} coat is dusty with the pale residue of colony grit, finer than dust and harder to shed.",
        "{Their} fur is the dull khaki of an animal that has lived on whatever fell to the floor.",
        "{Their} coat is mottled charcoal and rust, the kind of colouring that goes invisible in shadow.",
        "{Their} fur is short and bristly across the back, softer along the belly where it nearly disappears.",
        "{Their} coat carries the faint, persistent smell of damp insulation and old food wrappers.",
    ],
    "snout": [
        "{Their} snout is long and pink-tipped, whiskers fanning at every shift in the air.",
        "{Their} snout twitches constantly, the nostrils flaring at smells too faint for anyone else to register.",
        "{Their} snout carries the faint scar of a recent fight, a thin pale line across the bridge.",
        "{Their} snout is dark and damp, the whiskers white at the tips and very long.",
        "{Their} snout is foreshortened, blunt where most rats taper — a particular kind of breeding showing.",
        "{Their} whiskers stand out from a long, narrow snout, fine as wire and very alert.",
        "{Their} snout is pale and freckled with darker spots, weathered along the bridge.",
    ],
    "neck": [
        "{Their} neck is thin and pliant, the spine working visibly when {they} turn {their} head.",
        "{Their} neck disappears into the shoulders without much in the way of a clear transition.",
        "{Their} neck carries the dark fur in a slightly thicker band, almost a collar marking.",
    ],
    "head": [
        "{Their} skull is small and bullet-shaped, the bone visible under the fur at the temples.",
        "The crown of {their} head is darker than the rest of the coat, almost black in the shadows.",
        "{Their} head sits high on the neck when {they} {are} listening, low when {they} {are} feeding.",
    ],
    "eyes": [
        "{Their} {eyes} {are} small and black, two bright pinpoints catching the light.",
        "{Their} {eyes} {are} the dark wet glint of beads, set wide for almost panoramic sight.",
        "{Their} {eyes} {hold} the constant twitching alertness of something that has never let its guard down.",
        "{Their} {eyes} {are} pink-rimmed and dark-pupiled, faintly weeping in the colony air.",
        "{Their} {eyes} {move} in tiny jumps between sources of motion, never resting long.",
        "{Their} {eyes} {are} ruby-bright where the lighting hits them at the right angle.",
        "{Their} {eyes} {sit} prominently from the sides of {their} head, watchful in every direction.",
        "{Their} {eyes} {carry} the bright dilated quality of a small animal running on adrenaline.",
    ],
    "ears": [
        "{Their} {ears} {are} oversized for the body, almost translucent at the edges.",
        "{Their} {ears} {swivel} independently, tracking sounds from every direction.",
        "{Their} {ears} {are} thin and papery, the veins visible when the light catches them.",
        "{Their} {ears} {are} ragged at the tips, the souvenirs of past fights.",
        "{Their} {ears} {carry} a faint dark fur along the back, almost velvet where it meets the head.",
        "{Their} {ears} {fold} flat against the skull when {they} {are} surprised and spring back upright otherwise.",
        "{Their} {ears} {are} pale and finely-veined, catching every small sound in the room.",
    ],

    # Torso region
    "chest": [
        "{Their} chest is small and barrel-curved, the ribs flexing with every quick breath.",
        "{Their} chest fur is paler than the back, almost cream where it meets the throat.",
        "{Their} chest moves with quick shallow breaths, the rhythm of a small body always slightly anxious.",
    ],
    "back": [
        "{Their} back is arched and sinewy, the spine showing as a faint ridge through the fur.",
        "{Their} back fur is darker than the rest of the coat, almost a stripe down the spine.",
        "{Their} back carries the small scars of past tussles, faint pale lines through the fur.",
    ],
    "abdomen": [
        "{Their} abdomen is pale-furred and soft, the skin showing pink through the thin pelt.",
        "{Their} belly is a paler shade of the body fur, almost cream where it meets the legs.",
        "{Their} abdomen is taut and visibly rising with quick shallow breaths.",
    ],
    "groin": [
        "{Their} hips are narrow and quick-jointed, the muscle bunched for sudden movement.",
        "{Their} groin region is pale-furred, the hindlegs joining at a sharp efficient angle.",
    ],

    # Forelimb region
    "forelegs": [
        "{Their} {forelegs} {are} thin and quick, the small bones visible under the short fur.",
        "{Their} {forelegs} {are} dexterous and constantly busy — washing, gripping, picking at things.",
        "{Their} {forelegs} {are} held close to the body when {they} {are} still, ready to move at the slightest provocation.",
        "{Their} {forelegs} {are} nimble enough to manipulate small objects with disconcerting precision.",
        "{Their} {forelegs} {carry} the same dark fur as the back, ending in paler digits.",
    ],
    "forepaws": [
        "{Their} {forepaws} {are} tiny and pink, the digits ending in small dark claws.",
        "{Their} {forepaws} {grip} things with surprising precision — small fingers in everything but name.",
        "{Their} {forepaws} {are} dexterous and busy, almost never at rest.",
        "{Their} {forepaws} {leave} small star-shaped prints when {they} {move} through dust.",
        "{Their} {forepaws} {are} pale and freckled with darker spots, the digits long for the body's size.",
    ],

    # Hindlimb region
    "hindlegs": [
        "{Their} {hindlegs} {are} bunched with muscle, built for sudden bursts of speed.",
        "{Their} {hindlegs} {fold} under the body when {they} {are} crouched, then spring open for movement.",
        "{Their} {hindlegs} {are} longer than the forelegs, giving the body its forward-leaning poise.",
        "{Their} {hindlegs} {carry} the same patchwork fur as the back, scarred at the joints from past scuffles.",
        "{Their} {hindlegs} {are} thicker and stronger than the forelegs, the muscle clearly defined under the fur.",
    ],
    "hindpaws": [
        "{Their} {hindpaws} {are} long-toed and surprisingly large for the body's size.",
        "{Their} {hindpaws} {are} pale and clean of fur on the pads, with small dark claws at every toe.",
        "{Their} {hindpaws} {leave} elongated star-shaped prints, longer than the forepaw set.",
        "{Their} {hindpaws} {are} efficient launchpads — the body explodes off them when startled.",
        "{Their} {hindpaws} {grip} narrow surfaces with surprising tenacity.",
    ],

    # Tail — rat-unique
    "tail": [
        "{Their} tail is long and ringed, pale and slightly translucent at the tip.",
        "{Their} tail trails behind, scaled and pale, as long as the body again.",
        "{Their} tail is scarred near the base — the legacy of something almost catching it.",
        "{Their} tail is thick and dark, the rings of its hide clearly visible.",
        "{Their} tail is bent slightly halfway down, an old injury that healed off-true.",
        "{Their} tail is in constant slow motion when {they} {are} thinking, a small back-and-forth balance.",
        "{Their} tail is the length of the body itself, used for balance during every quick turn.",
    ],
}
