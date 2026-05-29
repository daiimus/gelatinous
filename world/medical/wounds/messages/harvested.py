"""
Harvested-organ wound descriptions.

These render on a corpse where an organ has been surgically extracted
via :class:`commands.forensics.CmdHarvest`.  The wound record is
synthesized by the success branch of ``CmdHarvest.func`` immediately
after the organ is moved off the corpse, with ``injury_type='harvested'``
and the canonical body-location name of the organ's *container*
(e.g. ``head`` for an eye harvest, ``right_hand`` for a metacarpal
harvest, ``chest`` for a heart harvest).

Targeting the **container** rather than the organ name lets PR-D's
existing wound + longdesc carry-forward overlay
(:func:`typeclasses.items.apply_wound_and_longdesc_overlay`) move the
wound onto a subsequently severed limb / head without any extra
plumbing.  Wounds at unseverable containers (chest, abdomen, back)
stay on the corpse permanently.

Stages:
    fresh: Used immediately after harvest (the cut is recent prose-wise).
    old:   Used on long-dead corpses; the excision has dried, sunken.

All templates expect the ``{location}`` and ``{organ}`` tokens, which
resolve through :func:`world.medical.wounds.constants.get_location_display_name`
and the new ``organ_display`` derivation in
:func:`world.medical.wounds.wound_descriptions.get_wound_description`
respectively.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|RA precise incision marks where the {organ} was extracted "
        "from the {location}, the cavity still wet and red|n",
        "|RThe {location} bears a surgical opening where the {organ} "
        "was excised, the edges of the cut still glistening|n",
        "|RWhere the {organ} was lifted free from the {location}, only "
        "a hollow, blood-slick pocket remains|n",
        "|RA careful cut along the {location} has exposed the empty "
        "socket where the {organ} was lifted free|n",
    ],
    "old": [
        "|rA dried incision marks where the {organ} was excised from "
        "the {location}, the cavity sunken and dark|n",
        "|rThe {location} bears a healed-over surgical opening where "
        "the {organ} was removed, the edges crusted brown|n",
        "|rWhere the {organ} was extracted from the {location}, only "
        "a shrunken, empty pocket remains|n",
        "|rA puckered seam along the {location} marks the long-ago "
        "extraction of the {organ}|n",
    ],
    # Aliases so the renderer's defensive stage fallbacks don't fall
    # through to a different injury_type's templates.
    "treated": [
        "|rThe surgical opening on the {location} where the {organ} was "
        "removed has been crudely bandaged|n",
    ],
    "healing": [
        "|rThe extraction site on the {location} shows callused, "
        "knotted scar tissue where the {organ} was lifted free|n",
    ],
    "scarred": [
        "|rA smooth, pale scar runs along the {location}, marking where "
        "the {organ} was excised long ago|n",
    ],
    "destroyed": [
        "|RThe {location} has been torn open, the {organ} ruined and "
        "ripped out in a violent extraction|n",
    ],
}
