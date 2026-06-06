"""
Severed wound descriptions.

These render on a corpse where a limb has been removed (PR #198), AND
on living characters at the cut point after an amputation — the
synthetic ``injury_type="severed"`` cut-point wound emitted by
:func:`world.medical.wounds.wound_descriptions.get_character_wounds`
on a freshly-amputated body routes through this module so the live
view and the eventual corpse view share prose.

Stages:
    fresh:             Just cut.  Raw stump.  Default on a living
                       body until the suture verb runs, and on a
                       fresh corpse spawned by
                       :func:`commands.forensics._apply_sever_to_corpse`.
    treated_success:   Sutured cleanly.  Picked when the roll
                       outcome was ``"success"``.
    treated_partial:   Sutured but the seam is rough.  Picked when
                       the outcome was ``"partial"``.
    treated_failure:   Botched suture — dirty seam, infection seeded
                       by ``_resolve_suture``.  Picked when the
                       outcome was ``"failure"``.
    treated:           Generic-treated fallback — covers legacy
                       ``sutured_stumps`` entries stored as a flat
                       list (no outcome recorded) and any other
                       caller that lands here without a flavour.
    healing:           Sutures dissolving, new tissue knitting over.
                       Stocked now; time-based progression to come.
    scarred:           Long-healed.  Terminal stage of progression.
    old:               Corpse-preserved variant.  Frozen at death.
                       Renders the dried / desiccated stump on
                       long-dead corpses.
    destroyed:         Catastrophic mangling (e.g. blast amputation
                       that didn't leave a clean cut).

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
    "treated_success": [
        "|rThe {location} stump has been carefully sutured shut, the dressing clean|n",
        "{skintone}neat rows of stitches close the {location} stump, the bandage still fresh|n",
        "{skintone}a {severity} sutured stump where the {location} used to be, the cut held closed|n",
        "{skintone}the {location} stump is bound in clean gauze, the suture line straight and tight|n",
    ],
    "treated_partial": [
        "|rThe {location} stump has been sutured shut, the line of stitches uneven but holding|n",
        "{skintone}the {location} stump shows a rough seam, the bandage stained but secure|n",
        "{skintone}a {severity} stump where the {location} once was, the suture line ragged but closed|n",
        "{skintone}the {location} stump is closed with stitches that wander, the dressing patchy|n",
    ],
    "treated_failure": [
        "|rThe stump where the {location} used to be has been crudely bandaged, the seam pulling dirty|n",
        "{skintone}the {location} stump is closed with uneven stitches and the dressing is already weeping|n",
        "{skintone}a {severity} stump at the {location} site, the suture line dirty and the bandage stained|n",
        "{skintone}the {location} stump has been hastily bound, the wound clearly leaking under the gauze|n",
    ],
    # Backward-compat fallback for legacy ``sutured_stumps`` list-shaped
    # entries (no recorded outcome) — mirrors the success variants
    # since that's the implicit flavour the older code path produced.
    "treated": [
        "|rThe {location} stump has been carefully sutured shut, the dressing clean|n",
        "{skintone}neat rows of stitches close the {location} stump, the bandage still fresh|n",
        "{skintone}a {severity} sutured stump where the {location} used to be, the cut held closed|n",
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
