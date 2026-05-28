"""Organ display metadata (relocated from world.medical.constants).

Sibling table to :data:`world.anatomy.severed_parts.SEVERED_PART_DESCRIPTIONS`,
keyed by canonical organ identifier.  Consumed by
:meth:`typeclasses.items.Organ.configure_from_harvest` to seed
``self.db.desc`` at harvest-time so the standard Evennia renderer
slots the prose into the look output naturally.

Design notes
============

* **Lives in** :mod:`world.anatomy` rather than
  :mod:`world.medical.constants` — display data is anatomy-side, not
  gameplay-mechanics-side.  Keeps the medical constants module
  focused on ``ORGANS`` (max_hp, vital, capacity, ...) and the
  prose-heavy display block easy to translate or rewrite in
  isolation (mirrors the
  :data:`world.anatomy.severed_parts.SEVERED_PART_DESCRIPTIONS`
  split out of structural anatomy data).

* **Three conditions only** — ``pristine`` / ``damaged`` / ``putrid``,
  matching the :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`
  map.  The ``refuse`` condition (skeletal-stage corpses) is
  intentionally absent: skeletal corpses refuse harvest at the
  command gate, so no Organ instance ever reaches that condition.

* Schema (per organ):

  * ``display_name`` — Player-facing noun phrase (no article).
    Underscored canonical keys (``"left_eye"``) become spaced
    display strings.
  * ``default_descriptions`` — condition → prose mapping.

Default descriptions are short (≤ 1 sentence) and clinical, with
enough physicality to anchor the player's senses.  At harvest time
:meth:`typeclasses.items.Organ.configure_from_harvest` selects the
condition-appropriate entry and writes it into ``self.db.desc`` so
Evennia's standard appearance rendering picks it up.
"""

from __future__ import annotations


#: Organ display registry.  Keys: canonical organ identifier
#: (matching :data:`world.medical.constants.ORGANS`) →
#: ``{"display_name": str, "default_descriptions": {condition: prose}}``.
ORGAN_DISPLAY = {
    "brain": {
        "display_name": "brain",
        "default_descriptions": {
            "pristine": "A glistening pinkish-grey mass, folded into intricate gyri and slick with cerebrospinal fluid.",
            "damaged": "A dulled brain, its folds slack and its tissue weeping a thin pinkish serum where the surface has dried.",
            "putrid": "A swollen, blackening brain, its folds collapsed into a fetid grey-green slurry.",
        },
    },
    "left_eye": {
        "display_name": "left eye",
        "default_descriptions": {
            "pristine": "A clear left eye, its iris sharp and the sclera still wetly bright.",
            "damaged": "A clouded left eye, the cornea milky and the surface beginning to slacken in its socket-cup.",
            "putrid": "A collapsed left eye, gone soft and weeping a dark serum from its ruptured sclera.",
        },
    },
    "right_eye": {
        "display_name": "right eye",
        "default_descriptions": {
            "pristine": "A clear right eye, its iris sharp and the sclera still wetly bright.",
            "damaged": "A clouded right eye, the cornea milky and the surface beginning to slacken in its socket-cup.",
            "putrid": "A collapsed right eye, gone soft and weeping a dark serum from its ruptured sclera.",
        },
    },
    "left_ear": {
        "display_name": "left ear",
        "default_descriptions": {
            "pristine": "A neatly excised left ear, its cartilage springy and the skin still naturally toned.",
            "damaged": "A discoloured left ear, the cartilage gone rubbery and the skin mottled with patches of grey.",
            "putrid": "A blackening left ear, its cartilage slumping inward and the flesh beginning to slough.",
        },
    },
    "right_ear": {
        "display_name": "right ear",
        "default_descriptions": {
            "pristine": "A neatly excised right ear, its cartilage springy and the skin still naturally toned.",
            "damaged": "A discoloured right ear, the cartilage gone rubbery and the skin mottled with patches of grey.",
            "putrid": "A blackening right ear, its cartilage slumping inward and the flesh beginning to slough.",
        },
    },
    "tongue": {
        "display_name": "tongue",
        "default_descriptions": {
            "pristine": "A thick, pink tongue, its surface roughened with taste buds and still glossy with saliva.",
            "damaged": "A greyed tongue, the surface dried into a leathery rasp and the root beginning to split.",
            "putrid": "A blackened tongue, swollen and weeping, its papillae lost to a uniform decaying slime.",
        },
    },
    "jaw": {
        "display_name": "jaw",
        "default_descriptions": {
            "pristine": "A clean jawbone, its teeth seated firmly and the hinge surfaces still slick with synovial fluid.",
            "damaged": "A discoloured jaw, several teeth loosened in their sockets and the bone surface beginning to dull.",
            "putrid": "A foul jaw, the gum-line sloughed away and the bone stained with seeping decay.",
        },
    },
    "heart": {
        "display_name": "heart",
        "default_descriptions": {
            "pristine": "A dense, dark-red heart, its muscle firm and the great vessels stumped cleanly above.",
            "damaged": "A slackened heart, its chambers flaccid and the surface beginning to discolour to a dull brown.",
            "putrid": "A swollen, greenish heart, its chambers ruptured and weeping a foul dark fluid.",
        },
    },
    "left_lung": {
        "display_name": "left lung",
        "default_descriptions": {
            "pristine": "A spongy, pink left lung, its surface marbled with fine vasculature and still elastic to the touch.",
            "damaged": "A mottled left lung, gone purplish and limp, its alveoli collapsed into a doughy mass.",
            "putrid": "A blackening left lung, its tissue dissolving into a frothy, fetid pulp.",
        },
    },
    "right_lung": {
        "display_name": "right lung",
        "default_descriptions": {
            "pristine": "A spongy, pink right lung, its surface marbled with fine vasculature and still elastic to the touch.",
            "damaged": "A mottled right lung, gone purplish and limp, its alveoli collapsed into a doughy mass.",
            "putrid": "A blackening right lung, its tissue dissolving into a frothy, fetid pulp.",
        },
    },
    "liver": {
        "display_name": "liver",
        "default_descriptions": {
            "pristine": "A glossy, mahogany-red liver, dense and faintly warm to the touch.",
            "damaged": "A dulled liver, its lobes gone slack and the surface mottled with greyish patches.",
            "putrid": "A swollen, blackening liver, its capsule split and weeping a viscous brown-green fluid.",
        },
    },
    "left_kidney": {
        "display_name": "left kidney",
        "default_descriptions": {
            "pristine": "A firm, bean-shaped left kidney, its capsule taut and the surface a deep reddish-brown.",
            "damaged": "A softened left kidney, the capsule loose and the cortex beginning to break down into a grainy paste.",
            "putrid": "A foul-smelling left kidney, its tissue dissolving into a dark, weeping mass.",
        },
    },
    "right_kidney": {
        "display_name": "right kidney",
        "default_descriptions": {
            "pristine": "A firm, bean-shaped right kidney, its capsule taut and the surface a deep reddish-brown.",
            "damaged": "A softened right kidney, the capsule loose and the cortex beginning to break down into a grainy paste.",
            "putrid": "A foul-smelling right kidney, its tissue dissolving into a dark, weeping mass.",
        },
    },
    "stomach": {
        "display_name": "stomach",
        "default_descriptions": {
            "pristine": "A pale, muscular stomach, its rugae visible through the thin serosa and a faint acidic tang clinging to it.",
            "damaged": "A slackened stomach, its walls thinned and the lining beginning to slough into the lumen.",
            "putrid": "A bloated, blackening stomach, its walls ruptured and weeping a foul digestive slurry.",
        },
    },
    "spine": {
        "display_name": "spine",
        "default_descriptions": {
            "pristine": "A clean length of spine, its vertebrae articulated and the cord still glistening within the canal.",
            "damaged": "A discoloured spine, the intervertebral discs flattened and the cord gone grey within its sheath.",
            "putrid": "A fouled spine, the cord liquefied and seeping from between the slumping vertebrae.",
        },
    },
    "left_humerus": {
        "display_name": "left humerus",
        "default_descriptions": {
            "pristine": "A clean left humerus, its surface ivory-pale and the joint ends still slick with cartilage.",
            "damaged": "A discoloured left humerus, the cartilage caps cracking and dried tissue clinging to the shaft.",
            "putrid": "A stained left humerus, the marrow weeping from the medullary cavity and the surface fouled with rot.",
        },
    },
    "right_humerus": {
        "display_name": "right humerus",
        "default_descriptions": {
            "pristine": "A clean right humerus, its surface ivory-pale and the joint ends still slick with cartilage.",
            "damaged": "A discoloured right humerus, the cartilage caps cracking and dried tissue clinging to the shaft.",
            "putrid": "A stained right humerus, the marrow weeping from the medullary cavity and the surface fouled with rot.",
        },
    },
    "left_metacarpals": {
        "display_name": "left metacarpals",
        "default_descriptions": {
            "pristine": "A neat cluster of left metacarpals, still articulated and the joint surfaces pearly white.",
            "damaged": "A loosened set of left metacarpals, several bones disarticulated and the cartilage gone leathery.",
            "putrid": "A fouled jumble of left metacarpals, stained dark and stuck together with putrefying tissue.",
        },
    },
    "right_metacarpals": {
        "display_name": "right metacarpals",
        "default_descriptions": {
            "pristine": "A neat cluster of right metacarpals, still articulated and the joint surfaces pearly white.",
            "damaged": "A loosened set of right metacarpals, several bones disarticulated and the cartilage gone leathery.",
            "putrid": "A fouled jumble of right metacarpals, stained dark and stuck together with putrefying tissue.",
        },
    },
    "left_femur": {
        "display_name": "left femur",
        "default_descriptions": {
            "pristine": "A heavy left femur, its shaft smooth and the femoral head a perfect glistening sphere.",
            "damaged": "A discoloured left femur, hairline fractures spidering the shaft and the joint caps cracking.",
            "putrid": "A stained left femur, the marrow weeping from the medullary cavity and the surface slick with rot.",
        },
    },
    "right_femur": {
        "display_name": "right femur",
        "default_descriptions": {
            "pristine": "A heavy right femur, its shaft smooth and the femoral head a perfect glistening sphere.",
            "damaged": "A discoloured right femur, hairline fractures spidering the shaft and the joint caps cracking.",
            "putrid": "A stained right femur, the marrow weeping from the medullary cavity and the surface slick with rot.",
        },
    },
    "left_tibia": {
        "display_name": "left tibia",
        "default_descriptions": {
            "pristine": "A long, clean left tibia, its anterior crest sharp and the periosteum still glossy.",
            "damaged": "A discoloured left tibia, the periosteum stripped in patches and the bone dulled to a greyish ivory.",
            "putrid": "A foul left tibia, the marrow seeping at both ends and the shaft mottled with putrid stains.",
        },
    },
    "right_tibia": {
        "display_name": "right tibia",
        "default_descriptions": {
            "pristine": "A long, clean right tibia, its anterior crest sharp and the periosteum still glossy.",
            "damaged": "A discoloured right tibia, the periosteum stripped in patches and the bone dulled to a greyish ivory.",
            "putrid": "A foul right tibia, the marrow seeping at both ends and the shaft mottled with putrid stains.",
        },
    },
    "left_metatarsals": {
        "display_name": "left metatarsals",
        "default_descriptions": {
            "pristine": "A neat row of left metatarsals, still articulated and the joint surfaces gleaming white.",
            "damaged": "A loosened set of left metatarsals, several bones disarticulated and the cartilage gone leathery.",
            "putrid": "A fouled set of left metatarsals, stained dark and stuck together with putrefying tissue.",
        },
    },
    "right_metatarsals": {
        "display_name": "right metatarsals",
        "default_descriptions": {
            "pristine": "A neat row of right metatarsals, still articulated and the joint surfaces gleaming white.",
            "damaged": "A loosened set of right metatarsals, several bones disarticulated and the cartilage gone leathery.",
            "putrid": "A fouled set of right metatarsals, stained dark and stuck together with putrefying tissue.",
        },
    },
    "pelvis": {
        "display_name": "pelvis",
        "default_descriptions": {
            "pristine": "A broad, intact pelvis, its iliac wings flared and the joint surfaces still smooth.",
            "damaged": "A discoloured pelvis, the sacroiliac joints loosened and the bone surface beginning to dull.",
            "putrid": "A stained pelvis, the bone fouled with seeping decay and the joint surfaces sloughing away.",
        },
    },
}


def get_organ_display_name(organ_name):
    """Return the player-facing display name for an organ.

    Falls back to the underscore-stripped canonical key when the
    organ isn't registered in :data:`ORGAN_DISPLAY` — defensive
    against new organs added to :data:`world.medical.constants.ORGANS`
    before their display metadata lands.
    """
    entry = ORGAN_DISPLAY.get(organ_name)
    if entry and entry.get("display_name"):
        return entry["display_name"]
    return (organ_name or "").replace("_", " ")


def get_organ_default_description(organ_name, condition):
    """Return the default prose for an organ at a given condition.

    Returns an empty string when the organ has no registered prose
    or the condition isn't one of pristine / damaged / putrid (e.g.
    ``refuse``).  Callers should treat empty as "render nothing"
    rather than asserting.
    """
    entry = ORGAN_DISPLAY.get(organ_name)
    if not entry:
        return ""
    descs = entry.get("default_descriptions") or {}
    return descs.get(condition, "")
