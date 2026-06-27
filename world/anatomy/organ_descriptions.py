"""Per-species organ default descriptions for non-organic species.

Sibling override to the organic ``default_descriptions`` in
:data:`world.anatomy.organs.ORGAN_DISPLAY`. A robot's harvested "power
core" should not read as "a glistening, fist-sized muscle" — these tables
give robots and synthetics their own condition prose.

Consumed by :func:`world.anatomy.organs.get_organ_default_description`
(``species`` argument); organs/conditions absent here fall back to the
organic ORGAN_DISPLAY prose.

Condition keys mirror ORGAN_DISPLAY: soft organs use
``pristine`` / ``damaged`` / ``putrid``; bones add ``desiccated``.
Non-rotting species never literally rot — their ``putrid`` (worst) tier
reads as corroded/seized (robot) or inert/discoloured (synth), and
``desiccated`` as a stripped frame.
"""

from __future__ import annotations


def _expand(singles: dict, pairs: dict) -> dict:
    """Build the full organ-keyed table from unpaired organs plus paired
    stems (``"eye"`` → ``left_eye`` / ``right_eye``), substituting the
    ``{side}`` token in each paired description."""
    out = dict(singles)
    for stem, conds in pairs.items():
        for side in ("left", "right"):
            out[f"{side}_{stem}"] = {
                c: t.format(side=side) for c, t in conds.items()
            }
    return out


# =====================================================================
# ROBOT — mechanical. Amber hydraulic fluid; corroded/seized worst-tier.
# =====================================================================
_ROBOT_SINGLES = {
    "brain": {
        "pristine": "A sealed processor core, its housing cool and unmarked, status LEDs cycling a steady green.",
        "damaged": "A cracked processor core, one corner scorched black, its indicators stuttering an error-amber.",
        "putrid": "A dead processor core, the housing split and its boards fused into a blackened slag.",
    },
    "heart": {
        "pristine": "A heavy power core, its casing warm and humming with a steady reciprocating pulse.",
        "damaged": "A breached power core, amber coolant weeping from a hairline split, its hum gone ragged.",
        "putrid": "A burst power core, the cell ruptured and caked with dried amber residue, utterly inert.",
    },
    "tongue": {
        "pristine": "A supple vocal modulator, its diaphragm taut and faintly resonant.",
        "damaged": "A split vocal modulator, the diaphragm torn so its tone would buzz and crack.",
        "putrid": "A dead vocal modulator, the diaphragm gone brittle and flaked half away.",
    },
    "nose": {
        "pristine": "A compact chemical sensor, its intake ports clean and faintly ticking.",
        "damaged": "A fouled chemical sensor, its ports clogged and one membrane ruptured.",
        "putrid": "A dead chemical sensor, its membranes corroded through and ports caked shut.",
    },
    "liver": {
        "pristine": "A dense fluid reclaimer, its filtration matrix clean and faintly amber-tinged.",
        "damaged": "A fractured fluid reclaimer, its matrix clogged and weeping unfiltered coolant.",
        "putrid": "A ruined fluid reclaimer, the matrix collapsed into a caked amber sludge.",
    },
    "stomach": {
        "pristine": "A sealed fuel cell, its casing intact and warm with slow chemical reaction.",
        "damaged": "A breached fuel cell, its casing swollen and venting an acrid amber vapor.",
        "putrid": "A spent fuel cell, ruptured and caked inside with dried reactant scale.",
    },
    "jaw": {
        "pristine": "An intact mandible servo, its actuator clean and the hinge swinging freely.",
        "damaged": "A bent mandible servo, the hinge grinding and one actuator arm snapped.",
        "putrid": "A seized mandible servo, the actuator fused and the hinge welded with corrosion.",
        "desiccated": "A stripped mandible servo, bare alloy frame with all cabling pulled.",
    },
    "thoracolumbar_spine": {
        "pristine": "An intact spinal strut, its segmented links flexing smoothly along bundled cabling.",
        "damaged": "A buckled spinal strut, two links cracked and the cable bundle frayed.",
        "putrid": "A shattered spinal strut, its links sheared and the cabling fused into slag.",
        "desiccated": "A stripped spinal strut, bare segmented alloy with the cabling gone.",
    },
    "pelvis": {
        "pristine": "A broad pelvic frame, its load-bearing struts clean and square.",
        "damaged": "A cracked pelvic frame, one strut sheared and the joint splayed.",
        "putrid": "A shattered pelvic frame, its struts snapped and crusted with corrosion.",
        "desiccated": "A stripped pelvic frame, bare pitted load-bearing alloy.",
    },
}

_ROBOT_PAIRS = {
    "eye": {
        "pristine": "A clear {side} optical sensor, its lens bright and the aperture cycling smoothly.",
        "damaged": "A cracked {side} optical sensor, the lens spider-webbed and its iris servo jammed half-open.",
        "putrid": "A shattered {side} optical sensor, the housing empty but for splinters of coated glass.",
    },
    "ear": {
        "pristine": "A fine {side} audio sensor, its mesh intake clean and unblocked.",
        "damaged": "A dented {side} audio sensor, the intake mesh torn and one pickup hanging loose.",
        "putrid": "A crushed {side} audio sensor, the mesh peeled away and the pickup corroded to powder.",
    },
    "lung": {
        "pristine": "A {side} cooling unit, its fins clean and radiating a faint, even warmth.",
        "damaged": "A {side} cooling unit with bent fins and a cracked manifold, venting a thin amber mist.",
        "putrid": "A {side} cooling unit seized solid, its fins furred with corrosion and its lines burst.",
    },
    "kidney": {
        "pristine": "A {side} coolant filter, its cartridge clean and faintly humming.",
        "damaged": "A {side} coolant filter, its cartridge split and bleeding a slow amber drip.",
        "putrid": "A {side} coolant filter corroded through, its cartridge fused into a hard amber crust.",
    },
    "humerus": {
        "pristine": "A solid {side} upper-arm strut, its load-bearing alloy unmarked.",
        "damaged": "A cracked {side} upper-arm strut, the alloy stress-fractured along its length.",
        "putrid": "A snapped {side} upper-arm strut, the break edges blackened and corroded.",
        "desiccated": "A stripped {side} upper-arm strut, bare pitted alloy.",
    },
    "metacarpals": {
        "pristine": "An intact {side} hand servos, the finger actuators articulating cleanly.",
        "damaged": "A mangled {side} hand servos, two actuators bent and one shorn away.",
        "putrid": "A crushed {side} hand servos, the actuators seized and corroded together.",
        "desiccated": "A stripped {side} hand servos, bare finger frames with no cabling.",
    },
    "femur": {
        "pristine": "A heavy {side} thigh strut, its hydraulic housing clean and intact.",
        "damaged": "A cracked {side} thigh strut, the housing split and weeping amber.",
        "putrid": "A snapped {side} thigh strut, the piston shattered and crusted with dried fluid.",
        "desiccated": "A stripped {side} thigh strut, bare alloy with the piston pulled.",
    },
    "tibia": {
        "pristine": "A reinforced {side} shin strut, its housing scuffed but sound.",
        "damaged": "A buckled {side} shin strut, the housing crumpled along one edge.",
        "putrid": "A snapped {side} shin strut, the break corroded and fluid-caked.",
        "desiccated": "A stripped {side} shin strut, bare pitted alloy.",
    },
    "metatarsals": {
        "pristine": "An intact {side} foot servos, the stabilizer actuators clean.",
        "damaged": "A bent {side} foot servos, two actuators jammed with grit.",
        "putrid": "A crushed {side} foot servos, the actuators corroded into a solid mass.",
        "desiccated": "A stripped {side} foot servos, bare frame plates.",
    },
}

ORGAN_DESCRIPTIONS_ROBOT = _expand(_ROBOT_SINGLES, _ROBOT_PAIRS)


# =====================================================================
# SYNTHETIC HUMANOID — engineered tissue. Cobalt fluid; inert worst-tier.
# =====================================================================
_SYNTH_SINGLES = {
    "brain": {
        "pristine": "A synthetic cortex, its lobes smooth and faintly translucent, threaded with fine cobalt vasculature.",
        "damaged": "A bruised synthetic cortex, its folds slack and weeping a thin cobalt serum.",
        "putrid": "A collapsed synthetic cortex, gone grey and inert, its cobalt fluid dried to a slate crust.",
    },
    "heart": {
        "pristine": "A synthetic heart, its pale chambers pulsing with a slow, even cobalt flow.",
        "damaged": "A torn synthetic heart, one chamber split and pumping cobalt in weak surges.",
        "putrid": "A stilled synthetic heart, its chambers slack and crusted with dried cobalt.",
    },
    "tongue": {
        "pristine": "A synthetic tongue, supple and pale, its surface faintly iridescent.",
        "damaged": "A split synthetic tongue, the engineered tissue frayed and seeping cobalt.",
        "putrid": "A withered synthetic tongue, gone stiff and slate-grey, no longer pliant.",
    },
    "nose": {
        "pristine": "A synthetic nose, its olfactory membranes clean and faintly cool.",
        "damaged": "A crushed synthetic nose, the membranes torn and weeping cobalt.",
        "putrid": "A collapsed synthetic nose, its membranes dried to brittle slate flakes.",
    },
    "liver": {
        "pristine": "A synthetic liver, its dense lobes a uniform pale blue-grey.",
        "damaged": "A lacerated synthetic liver, its lobes split and weeping cobalt.",
        "putrid": "A slackened synthetic liver, gone grey and inert, leaching a dried slate residue.",
    },
    "stomach": {
        "pristine": "A synthetic stomach, its pale sac taut and faintly translucent.",
        "damaged": "A ruptured synthetic stomach, its sac torn and venting cobalt-tinged fluid.",
        "putrid": "A collapsed synthetic stomach, the sac gone slack and crusted slate-grey.",
    },
    "jaw": {
        "pristine": "An intact synthetic jaw, its composite bone pale and smoothly hinged.",
        "damaged": "A fractured synthetic jaw, the composite split and seeping cobalt at the break.",
        "putrid": "A shattered synthetic jaw, the composite gone grey and crusted with dried fluid.",
        "desiccated": "A stripped synthetic jaw, bare pale composite with the tissue dried away.",
    },
    "thoracolumbar_spine": {
        "pristine": "An intact synthetic spine, its pale composite vertebrae stacked smooth and even.",
        "damaged": "A cracked synthetic spine, two vertebrae split and weeping cobalt.",
        "putrid": "A shattered synthetic spine, the vertebrae sheared and crusted slate-grey.",
        "desiccated": "A stripped synthetic spine, bare pale composite vertebrae.",
    },
    "pelvis": {
        "pristine": "A broad synthetic pelvis, its composite girdle pale and unmarked.",
        "damaged": "A cracked synthetic pelvis, the girdle split and seeping cobalt.",
        "putrid": "A shattered synthetic pelvis, the composite snapped and crusted grey.",
        "desiccated": "A stripped synthetic pelvis, bare pale composite girdle.",
    },
}

_SYNTH_PAIRS = {
    "eye": {
        "pristine": "A clear {side} synthetic eye, its iris sharply patterned and the surface wetly bright.",
        "damaged": "A clouded {side} synthetic eye, the lens fogged and weeping a cobalt tear.",
        "putrid": "A collapsed {side} synthetic eye, gone soft and slate-grey in its socket.",
    },
    "ear": {
        "pristine": "A fine {side} synthetic ear, its engineered cartilage springy and pale.",
        "damaged": "A torn {side} synthetic ear, the cartilage split and seeping cobalt.",
        "putrid": "A withered {side} synthetic ear, the cartilage gone stiff and slate-grey.",
    },
    "lung": {
        "pristine": "A {side} synthetic lung, its pale tissue expanding with a smooth, even draw.",
        "damaged": "A punctured {side} synthetic lung, the tissue collapsed and frothing cobalt.",
        "putrid": "A withered {side} synthetic lung, gone grey and stiff, no longer drawing.",
    },
    "kidney": {
        "pristine": "A {side} synthetic kidney, its pale bean-shaped tissue faintly cool.",
        "damaged": "A split {side} synthetic kidney, its tissue torn and weeping cobalt.",
        "putrid": "A slackened {side} synthetic kidney, gone grey and crusted with dried slate.",
    },
    "humerus": {
        "pristine": "A solid {side} synthetic humerus, its pale composite smooth and sound.",
        "damaged": "A cracked {side} synthetic humerus, the composite fractured and seeping cobalt.",
        "putrid": "A snapped {side} synthetic humerus, the break gone grey and crusted.",
        "desiccated": "A stripped {side} synthetic humerus, bare pale composite.",
    },
    "metacarpals": {
        "pristine": "An intact {side} synthetic hand, its slender composite bones smoothly jointed.",
        "damaged": "A mangled {side} synthetic hand, two bones snapped and weeping cobalt.",
        "putrid": "A crushed {side} synthetic hand, the composite splintered and crusted grey.",
        "desiccated": "A stripped {side} synthetic hand, bare pale finger composite.",
    },
    "femur": {
        "pristine": "A heavy {side} synthetic femur, its pale composite shaft smooth and dense.",
        "damaged": "A cracked {side} synthetic femur, the shaft split and seeping cobalt.",
        "putrid": "A snapped {side} synthetic femur, the break gone grey and crusted with dried fluid.",
        "desiccated": "A stripped {side} synthetic femur, bare pale composite shaft.",
    },
    "tibia": {
        "pristine": "A sound {side} synthetic tibia, its composite shaft pale and unmarked.",
        "damaged": "A buckled {side} synthetic tibia, the composite cracked and weeping cobalt.",
        "putrid": "A snapped {side} synthetic tibia, the break gone grey and crusted.",
        "desiccated": "A stripped {side} synthetic tibia, bare pale composite.",
    },
    "metatarsals": {
        "pristine": "An intact {side} synthetic foot, its slender composite bones smoothly set.",
        "damaged": "A mangled {side} synthetic foot, two bones snapped and seeping cobalt.",
        "putrid": "A crushed {side} synthetic foot, the composite splintered and crusted grey.",
        "desiccated": "A stripped {side} synthetic foot, bare pale composite.",
    },
}

ORGAN_DESCRIPTIONS_SYNTH = _expand(_SYNTH_SINGLES, _SYNTH_PAIRS)


# Species → organ-description table. New non-organic species: add here.
ORGAN_DESCRIPTIONS_BY_SPECIES = {
    "robot": ORGAN_DESCRIPTIONS_ROBOT,
    "synthetic_humanoid": ORGAN_DESCRIPTIONS_SYNTH,
}
