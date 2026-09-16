"""Severed body-part default descriptions (PR #204).

Sibling table to :data:`world.anatomy.organs.ORGAN_DISPLAY`, but
keyed by species and severable body-location.  Consumed by
:meth:`typeclasses.items.Appendage.configure_from_sever` (and via
super-call by :class:`typeclasses.items.SeveredHead`) to seed
``self.db.desc`` at sever-time so the standard Evennia renderer
slots the prose into the look output naturally.

Design notes
============

* **Separate file from** :mod:`world.anatomy.species` — that module
  owns the structural species registry (location names, decay
  templates).  Prose belongs in its own file so the structural data
  stays scannable and the prose-heavy block stays easy to translate
  or rewrite in isolation (mirrors the
  :data:`world.anatomy.organs.ORGAN_DISPLAY` separation from
  :data:`world.medical.constants.ORGANS`).

* **Species-keyed** so non-humans register their own anatomy prose
  without crowding the human entries — ``rat``, ``robot`` and
  ``synthetic_humanoid`` each hold their own bank below.  A
  registered species with no bank gets silence rather than somebody
  else's flesh; only an *unknown* species falls back to ``"human"``
  via :func:`get_severed_part_description`.

* **Three conditions only** — ``pristine`` / ``damaged`` / ``putrid``,
  matching the :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`
  map.  The ``refuse`` condition (skeletal-stage corpses) is
  intentionally absent: skeletal corpses refuse severance at the
  command gate, so no Appendage instance ever reaches that condition.

* **Same vocabulary register as** :data:`world.anatomy.organs.ORGAN_DISPLAY`
  — short, clinical, physically anchored, single sentence.  Anchors
  the player's senses without depending on a custom ``db.desc``
  ever being set by a staff member.
"""

from __future__ import annotations


#: Severed-part description registry.  Keys: species identifier (lower-case)
#: → location identifier → condition → prose.  Locations match
#: :data:`world.combat.constants.SEVERABLE_CONTAINERS`.
SEVERED_PART_DESCRIPTIONS = {
    "human": {
        "head": {
            "pristine": (
                "A severed human head, the features still composed and "
                "the stump-cut at the neck clean and weeping a thin "
                "rim of blood."
            ),
            "damaged": (
                "A discoloured severed head, the skin gone waxy and "
                "the stump-cut at the neck dried into a dark, "
                "leathery rim."
            ),
            "putrid": (
                "A bloated severed head, the features distorted and "
                "the flesh sloughing in soft, fetid patches."
            ),
        },
        "left_arm": {
            "pristine": (
                "A severed left arm, the muscle firm and the shoulder "
                "stump cut cleanly through cartilage and bone."
            ),
            "damaged": (
                "A discoloured left arm, the skin mottled and the "
                "shoulder stump dried into a dark, ragged crust."
            ),
            "putrid": (
                "A bloated left arm, the flesh sloughing from the bone "
                "and the shoulder stump weeping a foul dark fluid."
            ),
        },
        "right_arm": {
            "pristine": (
                "A severed right arm, the muscle firm and the shoulder "
                "stump cut cleanly through cartilage and bone."
            ),
            "damaged": (
                "A discoloured right arm, the skin mottled and the "
                "shoulder stump dried into a dark, ragged crust."
            ),
            "putrid": (
                "A bloated right arm, the flesh sloughing from the bone "
                "and the shoulder stump weeping a foul dark fluid."
            ),
        },
        "left_hand": {
            "pristine": (
                "A severed left hand, the fingers still loosely curled "
                "and the wrist-cut clean across the carpal bones."
            ),
            "damaged": (
                "A discoloured left hand, the fingers stiffened into a "
                "claw and the wrist-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated left hand, the skin sloughing from the "
                "fingers and the wrist-cut weeping a foul dark fluid."
            ),
        },
        "right_hand": {
            "pristine": (
                "A severed right hand, the fingers still loosely curled "
                "and the wrist-cut clean across the carpal bones."
            ),
            "damaged": (
                "A discoloured right hand, the fingers stiffened into a "
                "claw and the wrist-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated right hand, the skin sloughing from the "
                "fingers and the wrist-cut weeping a foul dark fluid."
            ),
        },
        "left_thigh": {
            "pristine": (
                "A severed left thigh, the heavy muscle firm and the "
                "hip-cut clean through the femoral head."
            ),
            "damaged": (
                "A discoloured left thigh, the skin gone mottled and the "
                "hip-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated left thigh, the flesh sloughing from the femur "
                "and the hip-cut weeping a foul dark fluid."
            ),
        },
        "right_thigh": {
            "pristine": (
                "A severed right thigh, the heavy muscle firm and the "
                "hip-cut clean through the femoral head."
            ),
            "damaged": (
                "A discoloured right thigh, the skin gone mottled and the "
                "hip-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated right thigh, the flesh sloughing from the femur "
                "and the hip-cut weeping a foul dark fluid."
            ),
        },
        "left_shin": {
            "pristine": (
                "A severed left shin, the calf muscle firm and the "
                "knee-cut clean across the joint surfaces."
            ),
            "damaged": (
                "A discoloured left shin, the skin gone leathery and the "
                "knee-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated left shin, the flesh sloughing from the tibia "
                "and the knee-cut weeping a foul dark fluid."
            ),
        },
        "right_shin": {
            "pristine": (
                "A severed right shin, the calf muscle firm and the "
                "knee-cut clean across the joint surfaces."
            ),
            "damaged": (
                "A discoloured right shin, the skin gone leathery and the "
                "knee-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated right shin, the flesh sloughing from the tibia "
                "and the knee-cut weeping a foul dark fluid."
            ),
        },
        "left_foot": {
            "pristine": (
                "A severed left foot, the toes still loosely splayed and "
                "the ankle-cut clean across the tarsal bones."
            ),
            "damaged": (
                "A discoloured left foot, the toes stiffened and the "
                "ankle-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated left foot, the skin sloughing from the toes and "
                "the ankle-cut weeping a foul dark fluid."
            ),
        },
        "right_foot": {
            "pristine": (
                "A severed right foot, the toes still loosely splayed and "
                "the ankle-cut clean across the tarsal bones."
            ),
            "damaged": (
                "A discoloured right foot, the toes stiffened and the "
                "ankle-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated right foot, the skin sloughing from the toes and "
                "the ankle-cut weeping a foul dark fluid."
            ),
        },
        # Humans grow tails only by augment (ANATOMY_AUGMENTS_SPEC,
        # #511) — the prose assumes the cybernetic article, which is
        # the only human tail that exists.
        "tail": {
            "pristine": (
                "A severed cybernetic tail, alloy vertebrae still "
                "articulating faintly and a torn mount plate trailing "
                "fine cabling at the cut."
            ),
            "damaged": (
                "A scuffed cybernetic tail, its segments seized at odd "
                "angles and the mount-end cabling frayed dark."
            ),
            "putrid": (
                "A grime-caked cybernetic tail, dead servos locked "
                "stiff and the flesh-interface ring at the mount gone "
                "soft and foul."
            ),
        },
    },
}


SEVERED_PART_DESCRIPTIONS.setdefault("rat", {
    "head": {
        "pristine": (
            "A severed rat's head, the snout still twitching as if "
            "ready to sniff and the cut at the neck weeping fresh "
            "blood."
        ),
        "damaged": (
            "A discoloured rat's head, the fur matted and the neck "
            "stump dried into a dark, leathery crust."
        ),
        "putrid": (
            "A bloated rat's head, the features distorted and the "
            "fur sliding off in soft, fetid patches."
        ),
    },
    "left_foreleg": {
        "pristine": (
            "A small severed foreleg, the fur still soft and the "
            "shoulder-cut weeping thin blood."
        ),
        "damaged": (
            "A withered severed foreleg, the fur sparse and the "
            "stump dark with dried matter."
        ),
        "putrid": (
            "A bloated severed foreleg, the flesh going soft and the "
            "fur sloughing in fetid clumps."
        ),
    },
    "right_foreleg": {
        "pristine": (
            "A small severed foreleg, the fur still soft and the "
            "shoulder-cut weeping thin blood."
        ),
        "damaged": (
            "A withered severed foreleg, the fur sparse and the "
            "stump dark with dried matter."
        ),
        "putrid": (
            "A bloated severed foreleg, the flesh going soft and the "
            "fur sloughing in fetid clumps."
        ),
    },
    "left_forepaw": {
        "pristine": (
            "A tiny severed forepaw, the claws still neatly arranged "
            "and the cut at the wrist edged with blood."
        ),
        "damaged": (
            "A shrivelled severed forepaw, the claws curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed forepaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "right_forepaw": {
        "pristine": (
            "A tiny severed forepaw, the claws still neatly arranged "
            "and the cut at the wrist edged with blood."
        ),
        "damaged": (
            "A shrivelled severed forepaw, the claws curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed forepaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "left_hindleg": {
        "pristine": (
            "A small severed hindleg, the long thigh muscle still "
            "twitching and the hip-cut weeping fresh blood."
        ),
        "damaged": (
            "A withered severed hindleg, the muscle gone slack and "
            "the cut dried dark."
        ),
        "putrid": (
            "A bloated severed hindleg, the flesh going soft and "
            "fetid where the cut once was."
        ),
    },
    "right_hindleg": {
        "pristine": (
            "A small severed hindleg, the long thigh muscle still "
            "twitching and the hip-cut weeping fresh blood."
        ),
        "damaged": (
            "A withered severed hindleg, the muscle gone slack and "
            "the cut dried dark."
        ),
        "putrid": (
            "A bloated severed hindleg, the flesh going soft and "
            "fetid where the cut once was."
        ),
    },
    "left_hindpaw": {
        "pristine": (
            "A tiny severed hindpaw, the long toes still spread and "
            "the cut at the ankle weeping."
        ),
        "damaged": (
            "A shrivelled severed hindpaw, the toes curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed hindpaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "right_hindpaw": {
        "pristine": (
            "A tiny severed hindpaw, the long toes still spread and "
            "the cut at the ankle weeping."
        ),
        "damaged": (
            "A shrivelled severed hindpaw, the toes curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed hindpaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "tail": {
        "pristine": (
            "A long, ringed rat tail, severed at the base and "
            "weeping a thin line of blood from the cut."
        ),
        "damaged": (
            "A dried-out rat tail, the rings gone leathery and the "
            "base-cut crusted hard."
        ),
        "putrid": (
            "A swollen rat tail, the rings discoloured and the "
            "flesh sloughing softly off the vertebrae."
        ),
    },
})


#: Severed cybernetic parts (#516 follow-up).  Augment anatomy is
#: chrome, not meat — a severed gun arm must not describe "muscle
#: firm" and "cartilage".  Keyed by location with a ``None`` generic
#: fallback whose ``{part}`` formats to the location name.  Used
#: whenever the severed chain's organs are flagged ``inorganic``.
CYBERNETIC_PART_DESCRIPTIONS = {
    None: {
        "pristine": (
            "A severed cybernetic {part}, composite plating intact "
            "and torn power couplings trailing from the mount-end, "
            "still beaded with sealant gel."
        ),
        "damaged": (
            "A scuffed cybernetic {part}, its plating dented and the "
            "mount-end couplings frayed dark where they tore."
        ),
        "putrid": (
            "A grime-caked cybernetic {part}, servos locked stiff and "
            "the flesh-interface ring at the mount gone soft and foul."
        ),
    },
}


def get_severed_part_description(species, location, condition, inorganic=False):
    """Return condition-keyed prose for a severed body part.

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.
        location: Canonical body-location identifier
            (e.g. ``"left_arm"``).
        condition: Freshness descriptor — ``"pristine"`` /
            ``"damaged"`` / ``"putrid"``.

    Returns:
        Prose string (single sentence, no trailing newline) or an
        empty string when the species / location / condition tuple
        isn't registered.  Callers should treat empty as "no default
        desc available, fall back to whatever Evennia does next"
        rather than asserting.

    When ``inorganic`` is True (the severed chain's organs are
    augment chrome), the cybernetic table answers first — location-
    specific entry, then the generic ``{part}`` template — before
    falling through to the species flesh prose.
    """
    # A species that is inorganic all the way down (robot, synth --
    # `infection_immune` at species level) and has its OWN bank answers
    # from that bank: a robot arm is a robot arm, not a chrome augment.
    # The cybernetic table is for chrome on a flesh body (#516), and it
    # still wins there. (#3362, owner: "each species has a bank, no
    # shortcuts".)
    if inorganic and species in SEVERED_PART_DESCRIPTIONS:
        from world.anatomy.species import get_species_infection_immune
        if get_species_infection_immune(species):
            inorganic = False
    if inorganic:
        cyber_table = (
            CYBERNETIC_PART_DESCRIPTIONS.get(location)
            or CYBERNETIC_PART_DESCRIPTIONS.get(None, {})
        )
        prose = cyber_table.get(condition, "")
        if prose:
            return prose.format(part=(location or "limb").replace("_", " "))

    species_table = SEVERED_PART_DESCRIPTIONS.get(species)
    if species_table is None:
        # A REGISTERED species with no bank gets SILENCE, not somebody
        # else's flesh. Only an unknown species falls back to human.
        #
        # When this guard landed, `SEVERED_PART_DESCRIPTIONS` covered
        # only human and rat while `SPECIES_DEFINITIONS` registered four,
        # so robot and synthetic_humanoid fell to the "unknown species"
        # fallback and a severed robot head described itself as "a severed
        # human head ... weeping a thin rim of blood" (#2725). Both have
        # banks now (#3362); the guard stays for the next species
        # registered before its prose is written.
        #
        # Silence is the lesser wrong here, and it is the contract this
        # function already documents -- "Callers should treat empty as
        # 'no default desc available, fall back to whatever Evennia does
        # next' rather than asserting". A missing sentence is a gap; a
        # robot bleeding is a claim about the world that is false, and
        # players act on prose. The severable limb containers already
        # return "" for every species including human, so an empty
        # answer here is an established shape rather than a new one.
        #
        # The human fallback is KEPT for a genuinely unknown species,
        # where nothing better is available and a body of unknown make
        # is most likely flesh.
        from world.anatomy.species import SPECIES_DEFINITIONS
        if species in SPECIES_DEFINITIONS:
            return ""
        species_table = SEVERED_PART_DESCRIPTIONS.get("human", {})
    location_table = species_table.get(location)
    if not location_table:
        return ""
    return location_table.get(condition, "")

# ---------------------------------------------------------------------
# Robot and synthetic-humanoid banks (#3362). Authored prose in each
# species' own register (see world/medical/wounds/messages/robot.py and
# synth.py); neither species rots, so "damaged"/"putrid" read as
# corroded-wreck and inert respectively. Every severable container is
# covered; test_severed_part_descriptions.py enforces it for all species.
# ---------------------------------------------------------------------
SEVERED_PART_DESCRIPTIONS.setdefault("robot", {
    "head": {
        "pristine": (
            "A severed robot head, its optical sensors still faintly "
            "lit and the neck servo column sheared clean, amber "
            "hydraulic fluid beading along the cut."
        ),
        "damaged": (
            "A dulled severed robot head, its optical sensors gone dark "
            "and the neck-column stump crusted tar-black where the "
            "fluid dried."
        ),
        "putrid": (
            "A wrecked severed robot head, the faceplate pitted with "
            "corrosion and the processor core dead behind a "
            "grime-filmed aperture."
        ),
    },
    "left_arm": {
        "pristine": (
            "A severed left arm, the shoulder mount sheared clean "
            "through and amber hydraulic fluid weeping from the cut "
            "couplings."
        ),
        "damaged": (
            "A scuffed left arm, its plating dented along the upper "
            "strut and the mount-end couplings crusted tar-black."
        ),
        "putrid": (
            "A wrecked left arm, its plating pitted with corrosion and "
            "the shoulder mount packed with grime, nothing inside it "
            "moving."
        ),
    },
    "right_arm": {
        "pristine": (
            "A severed right arm, bright metal showing at the sheared "
            "shoulder mount and its elbow actuator still ticking as it "
            "unloads."
        ),
        "damaged": (
            "A tarnished right arm, the elbow actuator seized "
            "mid-travel and dried fluid staining the panel seams "
            "tar-black."
        ),
        "putrid": (
            "A corroded right arm, the upper plating flaking away and "
            "its shoulder contacts long dead under a pale crust."
        ),
    },
    "left_hand": {
        "pristine": (
            "A severed left hand, its graspers still loosely curled and "
            "the wrist coupling cut clean, amber fluid beading at the "
            "line-ends."
        ),
        "damaged": (
            "A dented left hand, the graspers seized part-closed and "
            "the wrist coupling ringed with dried tar-black fluid."
        ),
        "putrid": (
            "A wrecked left hand, its finger servos locked stiff with "
            "grime and the wrist contacts pitted dead."
        ),
    },
    "right_hand": {
        "pristine": (
            "A severed right hand, its manipulators twitching faintly "
            "on residual charge and the wrist coupling shorn through in "
            "one clean pass."
        ),
        "damaged": (
            "A seized right hand, two graspers bent out of true and the "
            "wrist-cut hydraulic lines frayed and dry."
        ),
        "putrid": (
            "A corroded right hand, its palm plating flaking and the "
            "servo housings crusted shut, nothing articulating."
        ),
    },
    "left_thigh": {
        "pristine": (
            "A severed left thigh, the hip mount cut clean through its "
            "bearing and amber hydraulic fluid welling from the severed "
            "lines."
        ),
        "damaged": (
            "A scuffed left thigh, the heavy plating dulled and the "
            "hip-mount lines crimped shut with dried tar-black fluid."
        ),
        "putrid": (
            "A wrecked left thigh, its thigh strut pitted through in "
            "places and the hip bearing seized under packed grime."
        ),
    },
    "right_thigh": {
        "pristine": (
            "A severed right thigh, its hydraulic ram still pressurised "
            "and beading amber at the sheared hip coupling."
        ),
        "damaged": (
            "A dented right thigh, panel seams sprung along the outer "
            "plate and the coupling-end fluid dried to tar-black scale."
        ),
        "putrid": (
            "A corroded right thigh, the outer plating flaking off in "
            "scabs and its ram bled dry long ago."
        ),
    },
    "left_shin": {
        "pristine": (
            "A severed left shin, the knee joint sheared clean across "
            "its bearing surfaces and amber fluid running from the cut "
            "lines."
        ),
        "damaged": (
            "A tarnished left shin, its knee actuator seized and the "
            "joint-cut ringed with dried tar-black residue."
        ),
        "putrid": (
            "A wrecked left shin, its shin strut pitted with corrosion "
            "and the knee bearing packed solid with grit."
        ),
    },
    "right_shin": {
        "pristine": (
            "A severed right shin, bright metal at the knee shear and "
            "live contacts sparking faintly where the harness tore."
        ),
        "damaged": (
            "A dulled right shin, the forward plating dented inward and "
            "the severed hydraulic lines frayed and crusted dark."
        ),
        "putrid": (
            "A corroded right shin, plating flaking from the strut and "
            "its knee contacts dead under a film of grime."
        ),
    },
    "left_foot": {
        "pristine": (
            "A severed left foot, its toe pads still splayed and the "
            "ankle coupling cut clean, amber fluid running from the "
            "mount."
        ),
        "damaged": (
            "A scuffed left foot, the sole plate worn smooth and the "
            "ankle-cut lines dried tar-black."
        ),
        "putrid": (
            "A wrecked left foot, its foot servos locked under caked "
            "grime and the ankle mount pitted through."
        ),
    },
    "right_foot": {
        "pristine": (
            "A severed right foot, the ankle mount sheared through "
            "cleanly and its toe actuators still flexing in slow, "
            "aimless cycles."
        ),
        "damaged": (
            "A dented right foot, its heel plate crumpled and the ankle "
            "coupling crusted with dried fluid."
        ),
        "putrid": (
            "A corroded right foot, the sole plating flaking to scale "
            "and its toe actuators seized dead."
        ),
    },
    "tail": {
        "pristine": (
            "A severed robot tail, a segmented prehensile assembly "
            "still articulating faintly, amber hydraulic fluid weeping "
            "from the torn base mount."
        ),
        "damaged": (
            "A scuffed robot tail, its segments seized at odd angles "
            "and the base mount crusted tar-black where the lines tore."
        ),
        "putrid": (
            "A wrecked robot tail, its segment joints corroded solid "
            "and the base mount flaking to rust, nothing left live in "
            "it."
        ),
    },
})

SEVERED_PART_DESCRIPTIONS.setdefault("synthetic_humanoid", {
    "head": {
        "pristine": (
            "A severed synth head, the features composed and the "
            "neck-cut unnaturally clean, cobalt welling in a thin even "
            "rim."
        ),
        "damaged": (
            "A dulled severed synth head, the dermis gone waxy and the "
            "neck-cut dried to a slate crust."
        ),
        "putrid": (
            "An inert severed synth head, the dermis slackened and "
            "pearl-dull, its iris-rings dead glass and the neck seam "
            "parted dry."
        ),
    },
    "left_arm": {
        "pristine": (
            "A severed left arm, the shoulder-cut clean through joint "
            "and substrate, cobalt beading along the layered dermis."
        ),
        "damaged": (
            "A slackened left arm, the dermis gone waxy and the "
            "shoulder-cut set to a dry slate rim."
        ),
        "putrid": (
            "An inert left arm, the dermis greyed to pearl-dull and its "
            "shoulder seam parted around a crust of dried cobalt."
        ),
    },
    "right_arm": {
        "pristine": (
            "A severed right arm, its dermal layers showing too evenly "
            "at the shoulder-cut and cobalt running thin from the "
            "substrate."
        ),
        "damaged": (
            "A waxen right arm, the limb gone slack and heavy and its "
            "shoulder-cut margins dulled and dry."
        ),
        "putrid": (
            "An inert right arm, pearlescent seams standing open along "
            "the forearm and the shoulder-cut long set to slate."
        ),
    },
    "left_hand": {
        "pristine": (
            "A severed left hand, the fingers loosely curled and the "
            "wrist-cut machine-even, cobalt welling across it."
        ),
        "damaged": (
            "A waxen left hand, the fingers stiffened part-closed and "
            "the wrist-cut dried to slate."
        ),
        "putrid": (
            "An inert left hand, the dermis greyed and slack over the "
            "knuckles and the wrist seam parted, dry to the substrate."
        ),
    },
    "right_hand": {
        "pristine": (
            "A severed right hand, its palm still warm and the "
            "wrist-cut unnaturally clean, cobalt beading in a neat "
            "line."
        ),
        "damaged": (
            "A slackened right hand, the dermis waxy across the back of "
            "it and the wrist-cut edges gone dull and dry."
        ),
        "putrid": (
            "An inert right hand, its fingers set stiff and pearl-dull "
            "and the wrist-cut crusted over with old slate."
        ),
    },
    "left_thigh": {
        "pristine": (
            "A severed left thigh, the hip-cut clean through the joint "
            "and cobalt welling steadily from the layered dermis."
        ),
        "damaged": (
            "A waxen left thigh, its heavy dermis gone slack and the "
            "hip-cut dried into a flat slate rim."
        ),
        "putrid": (
            "An inert left thigh, the dermis greyed to pearl-dull and "
            "the hip-cut opened dry to the substrate."
        ),
    },
    "right_thigh": {
        "pristine": (
            "A severed right thigh, its dermal layers stacked too "
            "regularly at the unnaturally clean hip-cut, cobalt beading "
            "along them."
        ),
        "damaged": (
            "A slackened right thigh, the surface waxy and cool and its "
            "hip-cut margins set slate-dark."
        ),
        "putrid": (
            "An inert right thigh, pearlescent seams parted down the "
            "length of it and the hip-cut crusted with dried cobalt."
        ),
    },
    "left_shin": {
        "pristine": (
            "A severed left shin, the knee-cut clean across the joint "
            "surfaces and cobalt welling in an even rim."
        ),
        "damaged": (
            "A waxen left shin, the dermis gone slack over the calf and "
            "the knee-cut dried to slate."
        ),
        "putrid": (
            "An inert left shin, its dermis greyed and pearl-dull and "
            "the knee-cut parted dry around the substrate."
        ),
    },
    "right_shin": {
        "pristine": (
            "A severed right shin, its calf firm and the knee-cut "
            "machine-even, cobalt tracking down from it."
        ),
        "damaged": (
            "A slackened right shin, the surface waxy and the knee-cut "
            "margins dulled to a dry slate line."
        ),
        "putrid": (
            "An inert right shin, the dermis drawn tight and opaline "
            "and the knee-cut crusted hard with old cobalt."
        ),
    },
    "left_foot": {
        "pristine": (
            "A severed left foot, the toes loosely splayed and the "
            "ankle-cut unnaturally clean, cobalt beading at the joint."
        ),
        "damaged": (
            "A waxen left foot, the toes stiffened and the ankle-cut "
            "dried into a slate rim."
        ),
        "putrid": (
            "An inert left foot, its dermis greyed and slack and the "
            "ankle seam parted, dry through to the substrate."
        ),
    },
    "right_foot": {
        "pristine": (
            "A severed right foot, its sole pale and unworn and the "
            "ankle-cut clean through the joint, welling cobalt."
        ),
        "damaged": (
            "A slackened right foot, the dermis gone waxy across the "
            "instep and the ankle-cut set dry and dull."
        ),
        "putrid": (
            "An inert right foot, the toes pearl-dull and stiff and the "
            "ankle-cut crusted over with dried slate."
        ),
    },
    "tail": {
        "pristine": (
            "A severed synth tail, a prehensile length of layered "
            "dermis still limp and warm, cobalt welling from the "
            "unnaturally clean base-cut."
        ),
        "damaged": (
            "A waxen synth tail, its length gone slack and rubbery and "
            "the base-cut dried to a slate ring."
        ),
        "putrid": (
            "An inert synth tail, the dermis greyed and pearl-dull "
            "along its length and the base-cut parted dry over the "
            "substrate."
        ),
    },
})
