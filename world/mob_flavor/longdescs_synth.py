"""Longdesc templates for spawned synthetic humanoids.

Per-location prose seeded into ``mob.longdesc[location]``, humanoid slot
set (synths share human anatomy). The register throughout: **passes for
human — but if you know, you know.** Every line reads as a person first;
the tell is in the finish. Companion-grade engineering is present but
kept in the same key as the rest of the game's body prose.

Same token conventions as the human module: pair-keyed nouns braced
(``{eyes}``/``{arms}``…) with braced verbs; singular slots use pronoun
tokens.
"""

from __future__ import annotations

LONGDESCS_SYNTH: dict[str, list[str]] = {
    "hair": [
        "{Their} hair falls with a rooted, even density no scalp grows on its own — beautiful, and beautiful identically every day.",
        "{Their} hair carries a uniform lustre from root to tip, as if each strand were drawn to spec.",
        "{Their} hairline is flawless in the way only deliberate design manages — no cowlick, no drift, no history.",
        "{Their} hair never quite tangles; it falls back into its intended shape the moment the wind lets go.",
        "{Their} hair has the weight and swing of the real thing, and a part so clean it looks ruled.",
    ],
    "head": [
        "{Their} skull sits in perfect proportion to the frame — the golden-mean geometry no one is actually born with.",
        "The set of {their} head is level to the degree; it turns smoothly and stops without the little human overshoot.",
        "{Their} head carries no asymmetries to memorize — the kind of face-shape that's hard to describe to security.",
        "There's a poise to {their} head, always balanced, never quite hanging tired on the neck.",
    ],
    "face": [
        "{Their} face is symmetrical past the point where symmetry flatters — mirror-halves that agree completely.",
        "{Their} expressions arrive fully formed and leave the same way, with none of the small weather between.",
        "{Their} skin is smooth at a distance and smoother up close, where pores should start winning the argument.",
        "{Their} face does warmth beautifully — a half-beat after whatever should have caused it.",
        "In direct light {their} face has a finish rather than a texture, matte and even as good casting.",
        "{Their} smile is excellent — practiced to the exact width that reads as genuine, and held one moment past it.",
    ],
    "neck": [
        "{Their} neck is smooth-columned and unlined, the skin showing no pulse until you look for one — and then, obligingly, there it is.",
        "The tendons of {their} neck surface only when needed, like features called up from memory.",
        "{Their} throat moves in a swallow now and then, evenly spaced, a habit kept for company.",
        "Under the jaw, where a razor would nick anyone else, {their} skin runs unbroken and faintly seamless.",
    ],
    "chest": {
        "female": [
            "{Their} breasts are full and flawlessly matched, riding high with an engineered defiance of gravity, the skin smooth and even to the last inch.",
            "{Their} breasts carry a soft, deliberate weight — shaped by intention rather than chance, and shaped well.",
            "{Their} chest is a study in designed curves: breasts symmetrical to the millimetre, dark-tipped and unweathered, warm in a way that invites belief.",
            "{Their} breasts rise and settle with each courteous breath, perfect in the way that makes a second look feel like the point.",
        ],
        "male": [
            "{Their} chest is broad and cleanly muscled, pectorals cut to the anatomy charts' best day and finished smooth.",
            "{Their} chest carries sculpted, even muscle beneath poreless skin — built the way sketches promise and bodies rarely deliver.",
            "{Their} chest is warm, hard-planed, and utterly unscarred, a landscape of deliberate muscle with a heartbeat kept precisely where expected.",
            "The lines of {their} chest descend in engineered relief, each muscle in agreement with the next — designed to be admired at close range.",
        ],
        "any": [
            "{Their} chest rises and falls in perfect, unlabored time — breath as a courtesy rather than a need.",
            "The skin of {their} chest is even-toned everywhere, unfreckled, unscarred, unweathered — a history of nothing.",
        ],
    },
    "back": [
        "{Their} back is a clean map of muscle laid exactly where the textbook wants it, no side favored.",
        "{Their} spine draws one true line — none of the lean and list a body earns by carrying things badly.",
        "The skin of {their} back is unmarked from shoulder to waist, as if nothing had ever happened to it. Nothing has.",
    ],
    "abdomen": [
        "{Their} abdomen is even and smooth, the navel present, correct, and — if you're the type to notice — purely ornamental.",
        "{Their} midsection carries the taut economy of a body that has never overeaten, gone hungry, or aged.",
        "The muscle of {their} stomach shows in a soft, symmetric relief, less earned than specified.",
    ],
    "groin": {
        "female": [
            "{Their} hips flare in a deliberate, generous curve, and what they frame is fully, warmly human in every way that matters — decided, not inherited, and decided well.",
            "Between the smooth sweep of {their} hips, {they} {are} anatomically complete and companion-fluent — soft where softness persuades, and made to be discovered.",
            "{Their} sex is as finished as the rest of the design: correct, inviting, and warm past the point where engineering usually stops.",
            "{Their} lower body moves with a rolling, unhurried promise — hips built for the eye, and everything they carry built for more than that.",
        ],
        "male": [
            "{Their} hips are lean and level, and {they} {are} generously, unambiguously male — anatomy specified rather than inherited, and specified with confidence.",
            "{They} {are} complete and companion-fluent below the waist: correct in every particular, substantial by design, warm past where engineering usually stops.",
            "The cut of {their} lower body draws the eye downward on purpose — deliberate lines converging on anatomy that was clearly nobody's afterthought.",
            "{Their} sex is as considered as the rest of the build — fully human in form and function, sized to reassure, made to be found.",
        ],
        "any": [
            "{Their} hips move with an easy, level roll, engineered where a person is merely built.",
            "Everything about {their} lower body reads fully human; the difference is that it was decided, not inherited.",
        ],
    },
    "eyes": [
        "{Their} {eyes} {are} beautifully made — the irises patterned a shade too regularly, like guilloché under glass.",
        "{Their} {eyes} {adjust} to the light in one smooth sweep, none of the flutter of a living pupil finding its level.",
        "{Their} {eyes} {hold} contact without effort or challenge, and blink on a schedule that is almost right.",
        "{Their} {eyes} {catch} the light with a wet brightness that never needs to blink it away.",
        "{Their} {eyes} {track} movement in clean arcs, arriving exactly on target with nothing to correct.",
    ],
    "ears": [
        "{Their} {ears} {are} a matched pair to the millimetre — the one symmetry no human face ever gets.",
        "{Their} {ears} {sit} flush and identical, whorled like shells from the same mold. They were.",
        "{Their} {ears} {are} finely made and faintly translucent at the rim, without the asymmetries of grown cartilage.",
    ],
    "arms": [
        "{Their} {arms} {carry} smooth, deliberate muscle that never trembles at the end of a long hold.",
        "{Their} {arms} {hang} in perfect repose when idle — no drum of fingers, no restless shift.",
        "{Their} {arms} {are} unblemished from shoulder to wrist: no vaccination ghost, no scar, no story.",
        "{Their} {arms} {move} with an economy that spends nothing on the way to what they're doing.",
    ],
    "hands": [
        "{Their} {hands} {are} elegant and exact, the nails uniform as a set of samples.",
        "{Their} {hands} {rest} utterly still when unoccupied — no idle rubbing, no fidget, no habit.",
        "{Their} {hands} {are} warm, dry, and steady, with fingerprints — fine, regular ones, drawn rather than grown.",
        "{Their} {hands} {handle} things with a calibrated gentleness, pressure metered to the object.",
        "The knuckles of {their} {hands} {are} smooth and unscarred, hands that have touched much and hit nothing.",
    ],
    "thighs": [
        "{Their} {thighs} {carry} long, even muscle laid to specification, matched left to right.",
        "{Their} {thighs} {move} with a level, unhurried power that never seems to tire of standing.",
        "The skin of {their} {thighs} {is} smooth and uniform, unmarked by the ordinary friction of a life.",
    ],
    "shins": [
        "{Their} {shins} {are} straight-boned and unscuffed — no childhood ever barked them on anything.",
        "{Their} {shins} {taper} cleanly to the ankle, symmetric as lathework.",
        "{Their} {shins} {carry} a fine, even down of hair, distributed a touch too evenly.",
    ],
    "feet": [
        "{Their} {feet} {are} well-formed and uncalloused, arches out of a textbook, toes in descending order like a demonstration.",
        "{Their} {feet} {plant} squarely with each step, wearing shoes evenly where a person wears them down on one side.",
        "{Their} {feet} {are} smooth-soled and unhurried, feet that have walked far and suffered none of it.",
    ],
}
