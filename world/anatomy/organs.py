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

* **Tiered conditions** — soft-tissue organs carry three conditions
  (``pristine`` / ``damaged`` / ``putrid``) matching the
  :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY` map.
  Bones (see :data:`BONE_ORGANS`) carry a fourth ``desiccated``
  tier (issue #213) for mineralized-tissue narrative when a future
  harvest-gate relaxation (issue #227) allows skeletal-stage bone
  harvest.  The ``refuse`` condition (current skeletal-stage soft-
  tissue gate) is intentionally absent: skeletal corpses refuse
  soft-tissue harvest at the command gate, so no Organ instance
  ever reaches that condition with registered prose.

* **Bone vs. soft-tissue vocabulary** (issue #213): bones decay by
  drying, staining, and cracking — not by weeping serum or
  dissolving into pulp.  Bone prose deliberately avoids the soft-
  tissue register (``weeping``, ``slurry``, ``pulp``, ``slough``,
  ``serum``, ``frothy``, ``slime``) and reaches for mineralized-
  tissue language (``ivory``, ``periosteum``, ``hairline``,
  ``marrow``, ``chalk``, ``bleached``).  An exhaustive test in
  :mod:`world.tests.test_organ_display` enforces the split.

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


#: Canonical bone-organ identifiers.  Bones carry a four-tier
#: ``default_descriptions`` block (pristine / damaged / putrid /
#: desiccated) and use mineralized-tissue vocabulary throughout.
#: Issue #213.  Frozenset so callers can't accidentally mutate the
#: registry.
BONE_ORGANS = frozenset({
    "jaw",
    "thoracolumbar_spine",
    "pelvis",
    "left_humerus",
    "right_humerus",
    "left_metacarpals",
    "right_metacarpals",
    "left_femur",
    "right_femur",
    "left_tibia",
    "right_tibia",
    "left_metatarsals",
    "right_metatarsals",
})


#: Organ display registry.  Keys: canonical organ identifier
#: (matching :data:`world.medical.constants.ORGANS`) →
#: ``{"display_name": str, "default_descriptions": {condition: prose}}``.
#:
#: Soft-tissue entries carry three conditions; bone entries (per
#: :data:`BONE_ORGANS`) carry four (the extra ``desiccated`` tier
#: lands at issue #213 ahead of the gate relaxation in issue #227).
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
    "nose": {
        "display_name": "nose",
        "default_descriptions": {
            "pristine": "A neatly excised nose, the cartilage springy and the skin still naturally toned.",
            "damaged": "A discoloured nose, the cartilage stiffening and the nostrils crusted dark.",
            "putrid": "A blackening nose, the cartilage slumping inward and the tissue beginning to slough.",
        },
    },
    "jaw": {
        "display_name": "jaw",
        "default_descriptions": {
            "pristine": "A clean ivory jawbone, its teeth seated firmly in their sockets and the hinge surfaces faintly glossy.",
            "damaged": "A dulled jawbone, several teeth loosened in their sockets and hairline cracks fanning across the ramus.",
            "putrid": "A stained jawbone, the gum-line long shed and dark mineral discolouration creeping along the alveolar margin.",
            "desiccated": "A chalk-pale jawbone, bone-dry and brittle, the teeth rattling loose in their parched sockets.",
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
    "thoracolumbar_spine": {
        "display_name": "thoracolumbar spine",
        "default_descriptions": {
            "pristine": "A clean length of thoracolumbar spine, its vertebrae articulated and the intervertebral discs firm between glossy ivory bone.",
            "damaged": "A dulled thoracolumbar spine, the discs flattened and hairline cracks tracing the lateral processes of several vertebrae.",
            "putrid": "A stained thoracolumbar spine, the canal fouled with dark mineral residue and the vertebrae beginning to loosen from one another.",
            "desiccated": "A bone-dry thoracolumbar spine, chalk-pale and brittle, the vertebrae held together only by parchment-thin remnants of ligament.",
        },
    },
    "left_humerus": {
        "display_name": "left humerus",
        "default_descriptions": {
            "pristine": "A clean left humerus, its shaft ivory-pale and the cartilage caps at each end still faintly glossy.",
            "damaged": "A dulled left humerus, the cartilage caps cracking and hairline fractures spidering across the upper shaft.",
            "putrid": "A stained left humerus, dark mineral discolouration creeping along the shaft and the marrow cavity rimmed with residue.",
            "desiccated": "A chalk-pale left humerus, bone-dry and lightweight, hairline cracks fanning the length of the bleached shaft.",
        },
    },
    "right_humerus": {
        "display_name": "right humerus",
        "default_descriptions": {
            "pristine": "A clean right humerus, its shaft ivory-pale and the cartilage caps at each end still faintly glossy.",
            "damaged": "A dulled right humerus, the cartilage caps cracking and hairline fractures spidering across the upper shaft.",
            "putrid": "A stained right humerus, dark mineral discolouration creeping along the shaft and the marrow cavity rimmed with residue.",
            "desiccated": "A chalk-pale right humerus, bone-dry and lightweight, hairline cracks fanning the length of the bleached shaft.",
        },
    },
    "left_metacarpals": {
        "display_name": "left metacarpals",
        "default_descriptions": {
            "pristine": "A neat cluster of left metacarpals, still articulated and the joint surfaces a pearly ivory white.",
            "damaged": "A loosened set of left metacarpals, several bones disarticulated and dulled grey along their shafts.",
            "putrid": "A stained cluster of left metacarpals, mineral residue darkening the joint surfaces and several bones cracked.",
            "desiccated": "A chalk-pale fan of left metacarpals, bone-dry and brittle, the bones rattling apart at the slightest touch.",
        },
    },
    "right_metacarpals": {
        "display_name": "right metacarpals",
        "default_descriptions": {
            "pristine": "A neat cluster of right metacarpals, still articulated and the joint surfaces a pearly ivory white.",
            "damaged": "A loosened set of right metacarpals, several bones disarticulated and dulled grey along their shafts.",
            "putrid": "A stained cluster of right metacarpals, mineral residue darkening the joint surfaces and several bones cracked.",
            "desiccated": "A chalk-pale fan of right metacarpals, bone-dry and brittle, the bones rattling apart at the slightest touch.",
        },
    },
    "left_femur": {
        "display_name": "left femur",
        "default_descriptions": {
            "pristine": "A heavy left femur, its shaft smooth ivory and the femoral head a perfect glistening sphere.",
            "damaged": "A dulled left femur, hairline fractures spidering the shaft and the joint caps cracking at their edges.",
            "putrid": "A stained left femur, the marrow cavity rimmed with dark mineral residue and the shaft mottled with discolouration.",
            "desiccated": "A chalk-pale left femur, bone-dry and notably lighter than it should be, the shaft sun-bleached and brittle.",
        },
    },
    "right_femur": {
        "display_name": "right femur",
        "default_descriptions": {
            "pristine": "A heavy right femur, its shaft smooth ivory and the femoral head a perfect glistening sphere.",
            "damaged": "A dulled right femur, hairline fractures spidering the shaft and the joint caps cracking at their edges.",
            "putrid": "A stained right femur, the marrow cavity rimmed with dark mineral residue and the shaft mottled with discolouration.",
            "desiccated": "A chalk-pale right femur, bone-dry and notably lighter than it should be, the shaft sun-bleached and brittle.",
        },
    },
    "left_tibia": {
        "display_name": "left tibia",
        "default_descriptions": {
            "pristine": "A long, clean left tibia, its anterior crest sharp and the periosteum still faintly glossy.",
            "damaged": "A dulled left tibia, the periosteum stripped in patches and the bone discoloured to a greyish ivory.",
            "putrid": "A stained left tibia, the marrow cavity rimmed dark and mineral residue creeping along the cracked shaft.",
            "desiccated": "A chalk-pale left tibia, bone-dry and brittle, its anterior crest crumbling and the shaft hairline-cracked.",
        },
    },
    "right_tibia": {
        "display_name": "right tibia",
        "default_descriptions": {
            "pristine": "A long, clean right tibia, its anterior crest sharp and the periosteum still faintly glossy.",
            "damaged": "A dulled right tibia, the periosteum stripped in patches and the bone discoloured to a greyish ivory.",
            "putrid": "A stained right tibia, the marrow cavity rimmed dark and mineral residue creeping along the cracked shaft.",
            "desiccated": "A chalk-pale right tibia, bone-dry and brittle, its anterior crest crumbling and the shaft hairline-cracked.",
        },
    },
    "left_metatarsals": {
        "display_name": "left metatarsals",
        "default_descriptions": {
            "pristine": "A neat row of left metatarsals, still articulated and the joint surfaces gleaming ivory.",
            "damaged": "A loosened set of left metatarsals, several bones disarticulated and dulled grey along their shafts.",
            "putrid": "A stained row of left metatarsals, mineral residue darkening the joint surfaces and the shafts hairline-cracked.",
            "desiccated": "A chalk-pale row of left metatarsals, bone-dry and brittle, the bones rattling loose from one another.",
        },
    },
    "right_metatarsals": {
        "display_name": "right metatarsals",
        "default_descriptions": {
            "pristine": "A neat row of right metatarsals, still articulated and the joint surfaces gleaming ivory.",
            "damaged": "A loosened set of right metatarsals, several bones disarticulated and dulled grey along their shafts.",
            "putrid": "A stained row of right metatarsals, mineral residue darkening the joint surfaces and the shafts hairline-cracked.",
            "desiccated": "A chalk-pale row of right metatarsals, bone-dry and brittle, the bones rattling loose from one another.",
        },
    },
    "pelvis": {
        "display_name": "pelvis",
        "default_descriptions": {
            "pristine": "A broad, intact pelvis, its iliac wings flared and the joint surfaces still smooth ivory.",
            "damaged": "A dulled pelvis, the sacroiliac joints loosened and hairline cracks tracing the iliac wings.",
            "putrid": "A stained pelvis, dark mineral residue fouling the joint surfaces and the bone discoloured along its margins.",
            "desiccated": "A chalk-pale pelvis, bone-dry and brittle, the iliac wings cracked and the joints crumbling at a touch.",
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
    or the condition isn't one of pristine / damaged / putrid (or,
    for bones, ``desiccated`` — issue #213).  Callers should treat
    empty as "render nothing" rather than asserting.
    """
    entry = ORGAN_DISPLAY.get(organ_name)
    if not entry:
        return ""
    descs = entry.get("default_descriptions") or {}
    return descs.get(condition, "")
