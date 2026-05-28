"""
Severed wound descriptions.

These render on a corpse where a limb has been removed (PR #198).
The wound record is synthesized by
:func:`commands.forensics._apply_sever_to_corpse` immediately after
``CmdSever`` succeeds, with ``injury_type='severed'`` and the
canonical body-location name (e.g. ``left_arm``, ``head``).

Stages:
    fresh: Used immediately after sever (the cut is recent prose-wise).
    old:   Used on long-dead corpses; the stump is dried / desiccated.

All templates expect the ``{location}`` token, which resolves through
:func:`world.medical.wounds.constants.get_location_display_name` and
yields readable strings like ``"left arm"`` or ``"head"``.
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
    # Aliases so the renderer's defensive stage fallbacks don't fall
    # through to a different injury_type's templates.
    "treated": [
        "|rThe stump where the {location} used to be has been crudely bandaged|n",
    ],
    "healing": [
        "|rThe stump where the {location} used to be shows callused, knotted scar tissue|n",
    ],
    "scarred": [
        "|rA smooth, pale scar marks where the {location} was severed long ago|n",
    ],
    "destroyed": [
        "|RThe {location} has been violently torn away, leaving a mangled, ruined stump|n",
    ],
}
