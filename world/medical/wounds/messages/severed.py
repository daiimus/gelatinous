"""
Severed wound descriptions.

These render on a corpse where a limb has been removed (PR #198), AND
on living characters at the cut point after an amputation — the
synthetic ``injury_type="severed"`` cut-point wound emitted by
:func:`world.medical.wounds.wound_descriptions.get_character_wounds`
on a freshly-amputated body routes through this module so the live
view and the eventual corpse view share prose.

Stages:
    fresh:   Just cut.  Raw stump.  Default on a living body until
             the suture verb runs, and on a fresh corpse spawned by
             :func:`commands.forensics._apply_sever_to_corpse`.
    treated: Recently sutured.  Bandaged stump, stitches visible.
             Lives only on a living body — transitioned from ``fresh``
             by ``_resolve_suture`` via ``character.db.sutured_stumps``.
    healing: Sutures dissolving, new tissue knitting over.  Future
             use — slotted for the time-based progression tick.
    scarred: Long-healed.  Future use — terminal stage of progression.
    old:     Corpse-preserved variant.  Frozen at death.  Renders the
             dried / desiccated stump on long-dead corpses.
    destroyed: Catastrophic mangling (e.g. blast amputation that
             didn't leave a clean cut).

All templates expect the ``{location}`` token; the
``{skintone}`` / ``{severity}`` / ``{organ}`` / ``{injury_type}``
tokens are also available.  The renderer
(:func:`world.medical.wounds.wound_descriptions.get_wound_description`)
auto-prepends a skintone colour code for ``treated`` / ``healing`` /
``scarred`` stages when a character context is supplied.
"""

WOUND_DESCRIPTIONS = {
    "fresh": [
        "|RThe {location} has been severed, leaving a ragged, weeping stump|n",
        "|RWhere the {location} once attached, only a wet, raw stump remains|n",
        "|RThe {location} is gone — cleaved away at the joint, the wound still glistening|n",
        "|RA crude amputation has removed the {location}, leaving torn flesh exposed|n",
    ],
    "old": [
        "|rThe {location} has been severed, leaving a darkened, crusted stump|n",
        "|rWhere the {location} once attached, only dried, ragged tissue remains|n",
        "|rThe {location} is missing — the stump long since congealed and stiff|n",
        "|rA stump marks where the {location} used to be, the wound long dry|n",
    ],
    "treated": [
        "|rThe {location} stump has been carefully sutured shut, the dressing clean|n",
        "{skintone}neat rows of stitches close the {location} stump, the bandage still fresh|n",
        "{skintone}a {severity} sutured stump where the {location} used to be, the cut held closed|n",
        "|rThe stump where the {location} used to be has been crudely bandaged|n",
    ],
    "healing": [
        "{skintone}the {location} stump shows pink new tissue knitting over the closed wound|n",
        "{skintone}healing flesh covers the {location} stump, the sutures long since dissolved|n",
        "{skintone}the {location} stump is closing well, the scar still pink and tight|n",
        "{skintone}callused, knotted tissue forms the {location} stump, the wound nearly closed|n",
    ],
    "scarred": [
        "{skintone}a smooth, pale scar marks where the {location} was lost long ago|n",
        "{skintone}a faded, ridged scar tells of the {location} severed years past|n",
        "{skintone}the {location} ends in a smooth healed stump, the flesh long since closed|n",
        "{skintone}a pale, knotted scar caps the old severance site at the {location}|n",
    ],
    "destroyed": [
        "|RThe {location} has been violently torn away, leaving a mangled, ruined stump|n",
    ],
}
