"""Species-aware medical / death prose lookup helpers.

Centralises the room-visible tick prose for bleeding tiers and the
cause-specific death-curtain observer templates so non-human species
can override the humanoid-leaning entries (a rat "clutches their
chest one last time" reads as nonsense).

Falls back to human prose for any species without a registered
override — works for the broad case where the prose is generic
enough ("draws their final breath and grows still") and lets us
ship rat-specific overrides sparsely, only where they're needed.
"""

from __future__ import annotations


# Bleeding tier → species → room template.
# Tiers cap at four severity bands matching the legacy if-cascade in
# ``world.medical.script.MedicalScript._send_medical_messages``.
BLEEDING_ROOM_BY_SPECIES: dict[str, dict[str, str]] = {
    # Tier keys: "minor" (1-3), "moderate" (4-7), "severe" (8-12),
    # "grievous" (13+).  Templates use the ``{actor}`` identity-aware
    # token consumed by ``msg_room_identity``.
    "human": {
        "minor":    "Small droplets of blood fall from {actor}'s wounds.",
        "moderate": "Blood steadily drips from {actor}, forming dark stains.",
        "severe":   "Crimson flows freely from {actor}'s wounds, pooling on the ground.",
        "grievous": "{actor} leaves a trail of blood, their wounds gushing freely.",
    },
    "rat": {
        # Smaller-body imagery: thin trails, small dark spots, etc.
        "minor":    "Small dark spots of blood mark the ground beneath {actor}.",
        "moderate": "{actor} drags a thin trail of blood as they move.",
        "severe":   "Blood weeps freely from {actor}, soaking into the fur.",
        "grievous": "{actor} leaves a slick of blood, fur matted with it.",
    },
}


# Death-cause keyword → species → observer template.
# Keyword lookup is substring-based (matches the legacy
# ``'heart failure' in death_cause.lower()`` cascade).  Order
# matters for the lookup — first key whose token appears in the
# cause string wins.  ``_DEATH_KEYWORD_ORDER`` enforces it.
_DEATH_KEYWORD_ORDER = (
    "blood loss",
    "heart failure",
    "head",
    "brain",
    "poison",
    "fire",
    "burn",
    "stab",
    "slash",
)

DEATH_CAUSE_TEMPLATES_BY_SPECIES: dict[str, dict[str, str]] = {
    "human": {
        "blood loss":    "|R{actor}'s lifeblood pools crimson around their still form.|n",
        "heart failure": "|R{actor} clutches their chest one last time before going still.|n",
        "head":          "|R{actor}'s eyes lose focus as they collapse, unmoving.|n",
        "brain":         "|R{actor}'s eyes lose focus as they collapse, unmoving.|n",
        "poison":        "|R{actor} convulses violently before falling silent.|n",
        "fire":          "|R{actor}'s charred form crumples to the ground.|n",
        "burn":          "|R{actor}'s charred form crumples to the ground.|n",
        "stab":          "|R{actor} gasps once, crimson flowing, then goes still.|n",
        "slash":         "|R{actor} gasps once, crimson flowing, then goes still.|n",
    },
    "rat": {
        # Rat-flavored overrides only where the human prose breaks.
        # Missing keys fall through to the human default — most prose
        # ("eyes lose focus", "charred form", "convulses violently")
        # works for any small mammal.
        "heart failure": "|R{actor} stiffens, twitches once, then goes still.|n",
        "stab":          "|R{actor} squeaks once, body shuddering, then goes limp.|n",
        "slash":         "|R{actor} squeaks once, body shuddering, then goes limp.|n",
    },
}

# Generic fallback when no cause matches.
_GENERIC_DEATH_BY_SPECIES: dict[str, str] = {
    "human": "|R{actor} draws their final breath and grows still.|n",
    "rat":   "|R{actor}'s small body falls still.|n",
}


def get_bleeding_room_message(severity: int, species: str | None = None) -> str:
    """Return the room-visible bleeding template for a tier and species.

    Args:
        severity: Numeric bleeding severity (1-3 / 4-7 / 8-12 / 13+).
        species: Species identifier; ``None`` / unknown falls back to
            ``"human"``.

    Returns:
        Template string with the ``{actor}`` token unsubstituted, for
        ``msg_room_identity`` to render per-observer.
    """
    if severity <= 3:
        tier = "minor"
    elif severity <= 7:
        tier = "moderate"
    elif severity <= 12:
        tier = "severe"
    else:
        tier = "grievous"
    by_species = BLEEDING_ROOM_BY_SPECIES.get(species)
    if by_species is None:
        by_species = BLEEDING_ROOM_BY_SPECIES["human"]
    return by_species.get(tier) or BLEEDING_ROOM_BY_SPECIES["human"][tier]


def get_death_cause_template(death_cause: str | None,
                             species: str | None = None) -> str:
    """Return the room-visible death-curtain template for a cause + species.

    Looks for known cause keywords (``"blood loss"``, ``"heart
    failure"``, ``"head"`` / ``"brain"``, ``"poison"``, ``"fire"`` /
    ``"burn"``, ``"stab"`` / ``"slash"``) as substrings in
    ``death_cause`` (case-insensitive).  Falls back per axis:

    * Species without an entry uses human's table.
    * Species without an entry for THAT cause falls back to human's
      entry for the same cause.
    * Cause that doesn't match any keyword falls back to a generic
      template (which is also species-keyed).

    Args:
        death_cause: Free-text death cause string (e.g.
            ``"blood loss"`` / ``"head trauma"``).
        species: Species identifier.

    Returns:
        Observer template string with ``{actor}`` token unsubstituted.
    """
    if death_cause:
        cause_lower = death_cause.lower()
        species_table = DEATH_CAUSE_TEMPLATES_BY_SPECIES.get(species) or {}
        human_table = DEATH_CAUSE_TEMPLATES_BY_SPECIES["human"]
        for keyword in _DEATH_KEYWORD_ORDER:
            if keyword in cause_lower:
                # Per-species, then human fallback for that cause.
                return (
                    species_table.get(keyword)
                    or human_table.get(keyword)
                    or _GENERIC_DEATH_BY_SPECIES.get(species, "")
                    or _GENERIC_DEATH_BY_SPECIES["human"]
                )

    # No cause matched / no cause given → species-keyed generic.
    return (
        _GENERIC_DEATH_BY_SPECIES.get(species)
        or _GENERIC_DEATH_BY_SPECIES["human"]
    )
