"""Longdesc templates for spawned robots.

Per-location prose seeded into ``mob.longdesc[location]``. Same token
conventions as the human module:

* Pair-keyed nouns wrapped in braces (``{eyes}`` / ``{ears}`` /
  ``{arms}`` / ``{hands}`` / ``{thighs}`` / ``{shins}`` / ``{feet}``) so
  the renderer can flex them when one side collapses, with braced verbs
  whose subject is that paired noun.
* Singular locations (``head``, ``face``, ``chest`` ...) use plain prose
  with pronoun tokens.

Slot keys mirror the humanoid set in ``world/anatomy/species.py`` — a
robot is a humanoid chassis, so it uses the human ``pair_keys`` /
``default_longdesc_locations`` (no ``hair`` slot — robots are unhaired,
so that slot stays unseeded).
"""

from __future__ import annotations

LONGDESCS_ROBOT: dict[str, list[str]] = {
    # Head region
    "head": [
        "{Their} head is a smooth alloy casing, seams running clean along the jaw and crown.",
        "{Their} cranial housing is dented above one temple, the impact sealed with a rough weld.",
        "A cluster of sensor ports rings the back of {their} skull, dark glass set flush with the plating.",
        "{Their} head pivots on an exposed servo collar, the joint hissing faintly with each turn.",
        "The crown of {their} head carries a faded designation stencil, half-scrubbed to bare metal.",
    ],
    "face": [
        "{Their} face is a fixed sculpted plate, expressionless but for the glow of an optical band.",
        "A horizontal sensor strip crosses {their} face where eyes would sit, lit a steady amber.",
        "{Their} faceplate is scuffed and micro-scratched, the finish gone matte from years of grit.",
        "Twin grilles flank a blank central plate, venting the faint warmth of internal processors.",
        "{Their} face is featureless armor, the only motion the slow refocus of recessed lenses.",
    ],
    "neck": [
        "{Their} neck is a stacked column of articulated rings, cabling visible between the segments.",
        "Thick coolant lines run the length of {their} neck, ticking faintly as fluid cycles through.",
        "{Their} neck joint rotates with a low servo whine, exposing a band of bare actuator beneath.",
    ],

    # Torso region
    "chest": [
        "{Their} chest is a broad armored plastron, a recessed access panel set over the core.",
        "Status indicators glow in a row across {their} chest, pulsing in slow sequence.",
        "{Their} chest plating is scorched along one edge, the alloy discoloured by old heat.",
        "A faint reciprocating hum comes from deep in {their} chest where the power core sits.",
    ],
    "back": [
        "{Their} back is a ridged heat-sink array, shedding a thin shimmer of warm air.",
        "Cable runs and conduit trace {their} spine beneath a hinged maintenance panel.",
        "{Their} back plating is gouged and re-welded, the repairs left honestly visible.",
    ],
    "abdomen": [
        "{Their} midsection is a flexible segmented band, articulating as the frame bends.",
        "An exposed actuator bundle works at {their} waist, hissing softly with each motion.",
        "{Their} abdominal plating is patched with mismatched alloy, salvaged and bolted in place.",
    ],
    "groin": [
        "{Their} hip assembly is a heavy articulated joint, the servos broad and exposed.",
        "Hydraulic lines converge at {their} pelvis, the fittings beaded with old fluid.",
    ],

    # Arms
    "eyes": [
        "{Their} {eyes} {are} a pair of recessed optical lenses, refocusing with faint mechanical clicks.",
        "{Their} {eyes} {glow} a steady amber, the apertures contracting as they track movement.",
        "{Their} {eyes} {sit} behind scratched protective glass, whirring softly as they adjust.",
        "{Their} {eyes} {are} cold pinpoints of sensor light, unblinking and always moving.",
        "{Their} {eyes} {carry} a faint flicker at the edges — a processor reading the whole room at once.",
    ],
    "ears": [
        "{Their} {ears} {are} flush audio grilles set where a person's would be, swiveling minutely toward sound.",
        "{Their} {ears} {are} fine mesh intakes, filtering the room's noise into something the processor can parse.",
        "{Their} {ears} {sit} as dark recessed ports, attentive to every shift in the ambient hum.",
        "{Their} {ears} {are} paired pickups behind perforated plates, tracking the faintest sound.",
    ],
    "arms": [
        "{Their} {arms} {are} segmented actuator assemblies, cabling visible at every joint.",
        "{Their} {arms} {move} with a smooth servo-driven precision, never quite silent.",
        "{Their} {arms} {are} armored and scuffed, the plating gouged from heavy use.",
        "{Their} {arms} {hang} loose at {their} sides, the elbow servos ticking as they idle.",
        "{Their} {arms} {carry} mismatched plating, one clearly a salvaged replacement.",
    ],
    "hands": [
        "{Their} {hands} {are} three-fingered manipulators, the digits ending in worn grip pads.",
        "{Their} {hands} {flex} with a faint servo whine, each joint articulating independently.",
        "{Their} {hands} {are} heavy alloy graspers, scratched bright at the fingertips.",
        "{Their} {hands} {carry} the scuffs of constant work, the grip surfaces polished smooth.",
        "{Their} {hands} {close} with deliberate mechanical care, precise and unhurried.",
    ],

    # Legs
    "thighs": [
        "{Their} {thighs} {are} broad hydraulic struts, the pistons filmed with a sheen of fluid.",
        "{Their} {thighs} {are} armored load-bearing members, dented along the leading edge.",
        "{Their} {thighs} {flex} with a deep hydraulic sigh as the frame shifts its weight.",
        "{Their} {thighs} {carry} thick bundled cabling beneath scuffed protective plating.",
    ],
    "shins": [
        "{Their} {shins} {are} reinforced strut housings, scarred and scraped from rough ground.",
        "{Their} {shins} {are} bare actuator columns, the servos exposed and ticking.",
        "{Their} {shins} {carry} mismatched plating, one panel clearly a field repair.",
        "{Their} {shins} {are} caked with grime along the lower joints, the alloy showing through.",
    ],
    "feet": [
        "{Their} {feet} {are} broad splayed stabilizers, the soles worn smooth and bright.",
        "{Their} {feet} {are} heavy magnetic pads, clicking faintly against the floor.",
        "{Their} {feet} {carry} the dents of hard use, the toe plates scraped to bare metal.",
        "{Their} {feet} {plant} with a solid mechanical certainty, distributing the frame's mass.",
    ],
}
