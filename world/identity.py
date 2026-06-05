"""
Identity Constants and Sdesc Composition

Data tables and pure functions for the identity and recognition system:
physical descriptor lookup, keyword validation, hair options, distinguishing
feature formatting, and short description (sdesc) composition.

This module has no Evennia dependencies in its core functions (except for
the runtime keyword list storage, which is backed by Evennia's
:class:`~evennia.server.models.ServerConfig`, and
:class:`~world.models.KeywordEvent`, a Django model).

See specs/IDENTITY_RECOGNITION_SPEC.md for the full specification.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from evennia.server.models import ServerConfig
from evennia.utils import logger

from world.grammar import GENDER_MAP, with_article

if TYPE_CHECKING:
    from evennia.accounts.models import AccountDB

# =========================================================================
# Height / Build / Physical Descriptor
# =========================================================================

#: Valid height options, ordered shortest → tallest.
HEIGHTS: tuple[str, ...] = (
    "short",
    "below-average",
    "average",
    "above-average",
    "tall",
)

#: Valid build options, ordered slightest → heaviest.
BUILDS: tuple[str, ...] = (
    "slight",
    "lean",
    "athletic",
    "average",
    "stocky",
    "heavyset",
)


# Rat sdesc descriptors (#356 follow-up).  Rats don't fit the
# HEIGHTS × BUILDS table (humanoid scale doesn't apply to a small
# mammal), so they compose their key from a parallel size × coat
# pool.  ``CmdSpawnMob/rat`` picks one of each and writes the
# composed string ("a wiry brown rat") as the mob's key, which
# Character.get_sdesc falls back to when humanoid identity axes
# (height / build) aren't set.
RAT_SIZES: tuple[str, ...] = (
    "small",
    "thin",
    "lean",
    "scrawny",
    "wiry",
    "stocky",
    "long-bodied",
)

RAT_COATS: tuple[str, ...] = (
    "grey",
    "brown",
    "dusky",
    "ragged",
    "patchy",
    "sleek",
    "matted",
    "scarred",
)

#: Physical descriptor table.  ``PHYSICAL_DESCRIPTOR_TABLE[height][build]``
#: yields a single adjective describing the character's silhouette.
#:
#: 30 unique descriptors from the cross-product of 5 heights × 6 builds.
#: These are setting-neutral and describe observable silhouette only.
PHYSICAL_DESCRIPTOR_TABLE: dict[str, dict[str, str]] = {
    "short": {
        "slight": "diminutive",
        "lean": "wiry",
        "athletic": "compact",
        "average": "short",
        "stocky": "squat",
        "heavyset": "rotund",
    },
    "below-average": {
        "slight": "slight",
        "lean": "lithe",
        "athletic": "spry",
        "average": "unassuming",
        "stocky": "stout",
        "heavyset": "portly",
    },
    "average": {
        "slight": "slender",
        "lean": "lean",
        "athletic": "athletic",
        "average": "average",
        "stocky": "stocky",
        "heavyset": "heavyset",
    },
    "above-average": {
        "slight": "willowy",
        "lean": "rangy",
        "athletic": "strapping",
        "average": "tall",
        "stocky": "brawny",
        "heavyset": "hulking",
    },
    "tall": {
        "slight": "lanky",
        "lean": "gaunt",
        "athletic": "towering",
        "average": "tall",
        "stocky": "burly",
        "heavyset": "massive",
    },
}


def get_physical_descriptor(height: str, build: str) -> str:
    """Look up the physical descriptor for a height/build combination.

    Args:
        height: One of :data:`HEIGHTS`.
        build: One of :data:`BUILDS`.

    Returns:
        A single adjective (e.g. ``"lanky"``, ``"compact"``).

    Raises:
        KeyError: If *height* or *build* is not a valid option.
    """
    try:
        return PHYSICAL_DESCRIPTOR_TABLE[height][build]
    except KeyError:
        # Re-raise with a helpful message identifying which value is bad.
        if height not in PHYSICAL_DESCRIPTOR_TABLE:
            raise KeyError(
                f"Invalid height {height!r}. "
                f"Valid options: {', '.join(HEIGHTS)}"
            ) from None
        raise KeyError(
            f"Invalid build {build!r}. "
            f"Valid options: {', '.join(BUILDS)}"
        ) from None


# =========================================================================
# Keyword Lists
# =========================================================================

#: Default feminine keywords — seeds the ``identity.feminine_keywords``
#: :class:`ServerConfig` entry on first mutation.  At runtime, use
#: :func:`get_feminine_keywords` instead.
_DEFAULT_FEMININE_KEYWORDS: frozenset[str] = frozenset({
    "female", "girl", "lass", "woman", "matron", "grandma", "hag", "granny",
    "madam", "tomboy", "chick", "gal", "chica", "vixen",
    "diva", "dame", "sheila", "mona", "bimbo", "bitch", "lady", "senorita",
    "chola", "devotchka",
})

#: Default masculine keywords — seeds the ``identity.masculine_keywords``
#: :class:`ServerConfig` entry on first mutation.  At runtime, use
#: :func:`get_masculine_keywords` instead.
_DEFAULT_MASCULINE_KEYWORDS: frozenset[str] = frozenset({
    "male", "boy", "lad", "man", "patron", "grandpa", "geezer", "gramps",
    "gentleman", "guy", "fellow", "dude", "playa",
    "pimp", "bloke", "bruce", "mano", "bro", "douche", "stiff", "hombre",
    "cholo", "droog",
})

#: Default neutral keywords — seeds the ``identity.neutral_keywords``
#: :class:`ServerConfig` entry on first mutation.  At runtime, use
#: :func:`get_neutral_keywords` instead.
_DEFAULT_NEUTRAL_KEYWORDS: frozenset[str] = frozenset({
    "person", "kid", "urchin", "human", "citizen", "elder", "fossil",
    "fleshbag", "denizen", "neut", "snack", "walker", "chum",
    "charmer", "star", "mate", "smoker", "meatsicle", "punk", "clone",
    "wageslave", "baka", "androog", "suit",
})


def get_valid_keywords(gender: str) -> frozenset[str]:
    """Return the set of keywords available for a grammar gender.

    Male characters get masculine + neutral keywords.  Female characters
    get feminine + neutral keywords.  Neutral characters get all three
    sets (no restrictions).

    The ``appear`` command (disguise) bypasses this restriction and
    allows any keyword — that logic lives in the command, not here.

    Args:
        gender: Grammar gender (``"male"``, ``"female"``, or
            ``"neutral"``).  This is the output of
            :data:`world.grammar.GENDER_MAP`, not the raw ``sex``
            attribute.

    Returns:
        Frozenset of valid keyword strings.
    """
    if gender == "male":
        return get_masculine_keywords() | get_neutral_keywords()
    if gender == "female":
        return get_feminine_keywords() | get_neutral_keywords()
    # Neutral / unknown: all keywords available.
    return get_all_keywords()


def is_valid_keyword(keyword: str, gender: str) -> bool:
    """Check whether a keyword is valid for a given grammar gender.

    Convenience wrapper around :func:`get_valid_keywords`.

    Args:
        keyword: The keyword to validate (case-insensitive).
        gender: Grammar gender (``"male"``, ``"female"``, or
            ``"neutral"``).

    Returns:
        ``True`` if the keyword is in the valid set for *gender*.
    """
    return keyword.lower() in get_valid_keywords(gender)


# -- Custom keyword validation ----------------------------------------

#: Minimum length for a custom keyword.
CUSTOM_KEYWORD_MIN_LENGTH: int = 2

#: Maximum length for a custom keyword.
CUSTOM_KEYWORD_MAX_LENGTH: int = 20


def validate_custom_keyword(keyword: str) -> tuple[bool, str]:
    """Validate a player-supplied custom keyword.

    Custom keywords must be alphabetic, between
    :data:`CUSTOM_KEYWORD_MIN_LENGTH` and :data:`CUSTOM_KEYWORD_MAX_LENGTH`
    characters, and lowercase.

    Args:
        keyword: The keyword string to validate (should already be
            lowercased by the caller).

    Returns:
        ``(True, "")`` if valid, or ``(False, reason)`` with a
        human-readable rejection reason.
    """
    if not keyword.isalpha():
        return False, "Keywords must contain only letters (a-z)."
    if len(keyword) < CUSTOM_KEYWORD_MIN_LENGTH:
        return (
            False,
            f"Keywords must be at least {CUSTOM_KEYWORD_MIN_LENGTH} "
            f"characters long.",
        )
    if len(keyword) > CUSTOM_KEYWORD_MAX_LENGTH:
        return (
            False,
            f"Keywords must be at most {CUSTOM_KEYWORD_MAX_LENGTH} "
            f"characters long.",
        )
    return True, ""


# =========================================================================
# Approved Keyword Storage  (backed by ServerConfig)
# =========================================================================

#: ServerConfig keys for the three runtime-mutable keyword lists.  Stored
#: as picklable :class:`set` of lowercase strings.  When unset (fresh
#: install, test environment), the getters fall back to the module-level
#: ``_DEFAULT_*`` frozensets.
_SERVERCONFIG_KEY_FEMININE = "identity.feminine_keywords"
_SERVERCONFIG_KEY_MASCULINE = "identity.masculine_keywords"
_SERVERCONFIG_KEY_NEUTRAL = "identity.neutral_keywords"

_GENDER_LIST_TO_KEY: dict[str, str] = {
    "feminine": _SERVERCONFIG_KEY_FEMININE,
    "masculine": _SERVERCONFIG_KEY_MASCULINE,
    "neutral": _SERVERCONFIG_KEY_NEUTRAL,
}


def _read_keyword_set(conf_key: str, default: frozenset[str]) -> frozenset[str]:
    """Read a keyword set from :class:`ServerConfig`, falling back to default.

    Args:
        conf_key: ServerConfig key (see ``_SERVERCONFIG_KEY_*``).
        default: Frozenset returned when the key is unset.

    Returns:
        Frozenset of keyword strings.
    """
    stored = ServerConfig.objects.conf(conf_key)
    if stored is None:
        return default
    return frozenset(stored)


# =========================================================================
# Keyword Getters  (read from ServerConfig, fall back to defaults)
# =========================================================================


def get_feminine_keywords() -> frozenset[str]:
    """Return the current set of approved feminine keywords.

    Reads from :class:`~evennia.server.models.ServerConfig` under key
    ``identity.feminine_keywords``.  Falls back to
    :data:`_DEFAULT_FEMININE_KEYWORDS` when the key is unset (fresh
    install or test environment).

    Returns:
        Frozenset of feminine keyword strings.
    """
    return _read_keyword_set(_SERVERCONFIG_KEY_FEMININE, _DEFAULT_FEMININE_KEYWORDS)


def get_masculine_keywords() -> frozenset[str]:
    """Return the current set of approved masculine keywords.

    Reads from :class:`~evennia.server.models.ServerConfig` under key
    ``identity.masculine_keywords``.  Falls back to
    :data:`_DEFAULT_MASCULINE_KEYWORDS` when the key is unset.

    Returns:
        Frozenset of masculine keyword strings.
    """
    return _read_keyword_set(_SERVERCONFIG_KEY_MASCULINE, _DEFAULT_MASCULINE_KEYWORDS)


def get_neutral_keywords() -> frozenset[str]:
    """Return the current set of approved neutral keywords.

    Reads from :class:`~evennia.server.models.ServerConfig` under key
    ``identity.neutral_keywords``.  Falls back to
    :data:`_DEFAULT_NEUTRAL_KEYWORDS` when the key is unset.

    Returns:
        Frozenset of neutral keyword strings.
    """
    return _read_keyword_set(_SERVERCONFIG_KEY_NEUTRAL, _DEFAULT_NEUTRAL_KEYWORDS)


def get_all_keywords() -> frozenset[str]:
    """Return the union of all approved keyword lists.

    Returns:
        Frozenset of all keyword strings across all genders.
    """
    return get_feminine_keywords() | get_masculine_keywords() | get_neutral_keywords()


# =========================================================================
# Keyword Event Logging & Admin Operations
# =========================================================================


def log_custom_keyword(
    keyword: str,
    character_key: str,
    account: AccountDB | None = None,
) -> None:
    """Record a custom keyword usage as a :class:`~world.models.KeywordEvent`.

    Only logs keywords that are **not** in any approved list.  Safe to
    call for any keyword — approved keywords are silently ignored.

    Args:
        keyword: The keyword being set (lowercase).
        character_key: The ``.key`` of the character using it, for
            attribution.
        account: The player's :class:`~evennia.accounts.models.AccountDB`,
            if available.  Used to record the account name.
    """
    if keyword in get_all_keywords():
        return

    from world.models import KeywordEvent

    account_name = account.key if account is not None else ""
    KeywordEvent.objects.create(
        event_type="custom_set",
        keyword=keyword,
        character_name=character_key,
        account_name=account_name,
    )


def _load_gender_keyword_set(gender_list: str) -> set[str]:
    """Return a fresh mutable :class:`set` of the current keywords for *gender_list*.

    Reads the live :class:`~evennia.server.models.ServerConfig` value, or
    seeds from the module-level defaults when unset.  The returned set is
    a fresh copy — mutating it does not affect storage until written back
    via ``ServerConfig.objects.conf(key, new_set)``.
    """
    defaults = {
        "feminine": _DEFAULT_FEMININE_KEYWORDS,
        "masculine": _DEFAULT_MASCULINE_KEYWORDS,
        "neutral": _DEFAULT_NEUTRAL_KEYWORDS,
    }[gender_list]
    conf_key = _GENDER_LIST_TO_KEY[gender_list]
    stored = ServerConfig.objects.conf(conf_key)
    if stored is None:
        return set(defaults)
    return set(stored)


def add_approved_keyword(
    keyword: str,
    gender_list: str,
    admin_name: str = "",
) -> tuple[bool, str]:
    """Add a keyword to an approved gender list.

    Creates a :class:`~world.models.KeywordEvent` with event type
    ``admin_add`` and persists the updated keyword set via
    :class:`~evennia.server.models.ServerConfig`.

    Args:
        keyword: Keyword to add (lowercase).
        gender_list: One of ``"feminine"``, ``"masculine"``, or
            ``"neutral"``.
        admin_name: Name of the admin performing the action.

    Returns:
        ``(True, "")`` on success, or ``(False, reason)`` on failure.
    """
    if gender_list not in _GENDER_LIST_TO_KEY:
        return False, f"Invalid gender list {gender_list!r}."

    kw_set = _load_gender_keyword_set(gender_list)
    if keyword in kw_set:
        return False, f"'{keyword}' is already in the {gender_list} list."

    kw_set.add(keyword)
    ServerConfig.objects.conf(_GENDER_LIST_TO_KEY[gender_list], kw_set)

    from world.models import KeywordEvent

    KeywordEvent.objects.create(
        event_type="admin_add",
        keyword=keyword,
        gender_list=gender_list,
        account_name=admin_name,
    )
    return True, ""


def remove_approved_keyword(
    keyword: str,
    gender_list: str,
    admin_name: str = "",
) -> tuple[bool, str]:
    """Remove a keyword from an approved gender list.

    Creates a :class:`~world.models.KeywordEvent` with event type
    ``admin_remove`` and persists the updated keyword set via
    :class:`~evennia.server.models.ServerConfig`.

    Args:
        keyword: Keyword to remove (lowercase).
        gender_list: One of ``"feminine"``, ``"masculine"``, or
            ``"neutral"``.
        admin_name: Name of the admin performing the action.

    Returns:
        ``(True, "")`` on success, or ``(False, reason)`` on failure.
    """
    if gender_list not in _GENDER_LIST_TO_KEY:
        return False, f"Invalid gender list {gender_list!r}."

    kw_set = _load_gender_keyword_set(gender_list)
    if keyword not in kw_set:
        return False, f"'{keyword}' is not in the {gender_list} list."

    kw_set.discard(keyword)
    ServerConfig.objects.conf(_GENDER_LIST_TO_KEY[gender_list], kw_set)

    from world.models import KeywordEvent

    KeywordEvent.objects.create(
        event_type="admin_remove",
        keyword=keyword,
        gender_list=gender_list,
        account_name=admin_name,
    )
    return True, ""


# =========================================================================
# Hair Options
# =========================================================================

#: Valid hair colour options.  ``None`` represents bald / no hair.
HAIR_COLORS: tuple[str, ...] = (
    "red",
    "black",
    "blonde",
    "white",
    "brown",
    "gray",
    "blue",
    "green",
    "pink",
    "purple",
    "silver",
    "auburn",
    "orange",
)

#: Valid hair style options.  ``None`` represents bald / no hair.
HAIR_STYLES: tuple[str, ...] = (
    "cropped",
    "short",
    "long",
    "braided",
    "dreaded",
    "mohawk",
    "ponytail",
    "shaved sides",
    "curly",
    "straight",
    "matted",
    "slicked",
)


# =========================================================================
# Distinguishing Feature Formatters
# =========================================================================
#
# Each formatter takes simple string inputs and returns a feature clause
# suitable for appending to an sdesc.  New feature types (cybernetics,
# carried objects, etc.) are added as new ``format_*_feature`` functions.
#
# The actual *selection* of which formatter to call (i.e. the priority
# chain: wielded weapon > clothing > hair > nothing) is handled by the
# Character typeclass in a later phase — not by this module.

def format_wielded_feature(item_name: str) -> str:
    """Format a wielded item as a distinguishing feature clause.

    Args:
        item_name: The item's display name (e.g. ``"Kitchen Knife"``).

    Returns:
        Feature clause, e.g. ``"wielding a Kitchen Knife"``.
    """
    return f"wielding {with_article(item_name)}"


def format_clothing_feature(item_name: str) -> str:
    """Format an outermost clothing item as a distinguishing feature clause.

    Args:
        item_name: The item's display name (e.g. ``"Black Trenchcoat"``).

    Returns:
        Feature clause, e.g. ``"in a Black Trenchcoat"``.
    """
    return f"in {with_article(item_name)}"


def format_hair_feature(
    color: str | None = None,
    style: str | None = None,
) -> str | None:
    """Format hair attributes as a distinguishing feature clause.

    Handles any combination of colour and style.  If both are ``None``
    (bald), returns ``None`` to indicate no feature.

    Args:
        color: Hair colour (e.g. ``"blonde"``), or ``None``.
        style: Hair style (e.g. ``"braided"``), or ``None``.

    Returns:
        Feature clause (e.g. ``"with blonde braids"``,
        ``"with cropped white hair"``, ``"with red hair"``),
        or ``None`` if both inputs are ``None``.
    """
    if not color and not style:
        return None

    if color and style:
        # Certain styles read better as nouns: "blonde braids",
        # "red dreadlocks", "white mohawk".  Others need "hair" appended:
        # "cropped white hair", "straight black hair".
        noun_styles = _NOUN_HAIR_STYLES.get(style)
        if noun_styles:
            return f"with {color} {noun_styles}"
        return f"with {style} {color} hair"

    if color:
        return f"with {color} hair"

    # Style only, no colour.
    noun_styles = _NOUN_HAIR_STYLES.get(style)
    if noun_styles:
        return f"with {noun_styles}"
    return f"with {style} hair"


#: Hair styles that read naturally as standalone nouns (plural form).
#: Styles NOT in this table need ``"hair"`` appended.
#: E.g. ``"braided"`` → ``"braids"``, but ``"cropped"`` → ``"cropped hair"``.
_NOUN_HAIR_STYLES: dict[str, str] = {
    "braided": "braids",
    "dreaded": "dreadlocks",
    "mohawk": "mohawk",
    "ponytail": "ponytail",
    "shaved sides": "shaved sides",
    "curly": "curls",
}


# =========================================================================
# Sdesc Composition
# =========================================================================


def compose_sdesc(
    descriptor: str,
    keyword: str,
    feature: str | None = None,
    disguise_adjective: str | None = None,
) -> str:
    """Assemble a short description string from its components.

    Returns the sdesc **without** a leading article.  The caller is
    responsible for prepending the article via
    :func:`world.grammar.get_article` based on context (indefinite for
    strangers, definite for targeting, none for certain message formats).

    Args:
        descriptor: Physical descriptor (e.g. ``"lanky"``).
        keyword: Player-selected keyword (e.g. ``"man"``).
        feature: Optional distinguishing feature clause (e.g.
            ``"in a Black Trenchcoat"``).  If ``None`` or empty,
            the sdesc has no feature suffix.
        disguise_adjective: Optional disguise adjective injected
            between descriptor and keyword (e.g. ``"masked"`` →
            ``"lanky masked man"``).  If ``None`` or empty, the sdesc
            shape is unchanged from its three-argument form.  See
            :func:`get_disguise_adjective`.

    Returns:
        Composed sdesc, e.g. ``"lanky man in a Black Trenchcoat"``,
        ``"lanky masked man in a Black Trenchcoat"``, or
        ``"compact woman"`` (no article prefix).
    """
    if disguise_adjective:
        base = f"{descriptor} {disguise_adjective} {keyword}"
    else:
        base = f"{descriptor} {keyword}"
    if feature:
        return f"{base} {feature}"
    return base


# =========================================================================
# Disguise Adjective
# =========================================================================
#
# See specs/IDENTITY_RECOGNITION_SPEC.md §"Disguise Adjective" for the
# design rationale.  The adjective is the visible "red flag": when an
# item flagged ``is_disguise_item = True`` is worn, its
# ``disguise_adjective`` is injected into the wearer's sdesc so
# observers can immediately tell someone is disguising themselves.

#: Priority ranks for disguise adjectives, lowest rank wins.  The
#: ranking captures *identity-defining-ness*: a mask hides the face
#: more than a hood, so ``"masked"`` outranks ``"hooded"`` when both
#: are worn.  Adjectives not in this table are admitted at rank 999
#: (alphabetical tiebreak), so authors can ship new disguise types via
#: item attribute alone without editing this table.
_DISGUISE_ADJECTIVE_PRIORITY: dict[str, int] = {
    "masked": 1,
    "helmeted": 2,
    "cowled": 3,
    "hooded": 4,
    "goggled": 5,
    "veiled": 6,
}

#: Sentinel rank for adjectives missing from the priority table.
_DISGUISE_ADJECTIVE_UNKNOWN_RANK: int = 999


def get_disguise_adjective(char: Any) -> str | None:
    """Return the most-prominent disguise adjective for a character.

    Walks the wearer's worn items via
    :meth:`typeclasses.clothing_mixin.ClothingMixin.get_worn_items`,
    collects non-empty ``disguise_adjective`` values from items also
    flagged ``is_disguise_item = True``, and returns the highest-
    priority adjective per :data:`_DISGUISE_ADJECTIVE_PRIORITY`.

    Adjectives missing from the priority table are admitted at
    :data:`_DISGUISE_ADJECTIVE_UNKNOWN_RANK` (alphabetical tiebreak),
    so authors can ship new disguise types via item attribute alone.

    Items with ``disguise_adjective`` set but ``is_disguise_item`` not
    ``True`` are skipped with a soft warning: the adjective is a red-
    flag style standard reserved for the disguise taxonomy.

    Characters without :meth:`get_worn_items` (e.g. mocks, NPCs that
    cannot wear clothing) yield ``None``.

    Args:
        char: The character whose worn items are inspected.

    Returns:
        The winning adjective string (e.g. ``"masked"``), or ``None``
        when no eligible adjective is contributed.
    """
    get_worn = getattr(char, "get_worn_items", None)
    if get_worn is None:
        return None

    candidates: list[str] = []
    for item in get_worn():
        adjective = getattr(item, "disguise_adjective", "") or ""
        if not adjective:
            continue
        if not getattr(item, "is_disguise_item", False):
            logger.log_warn(
                f"Item {item!r} on {char!r} has disguise_adjective="
                f"{adjective!r} but is_disguise_item is not True; "
                f"skipping (disguise adjectives are reserved for the "
                f"disguise taxonomy)."
            )
            continue
        candidates.append(adjective)

    if not candidates:
        return None

    # Sort by (priority rank, adjective) so unknowns tie-break
    # alphabetically and the lowest rank (most identity-defining) wins.
    candidates.sort(
        key=lambda adj: (
            _DISGUISE_ADJECTIVE_PRIORITY.get(
                adj, _DISGUISE_ADJECTIVE_UNKNOWN_RANK
            ),
            adj,
        )
    )
    return candidates[0]



# =========================================================================
# Identity Signature, Apparent UID, Apparent Gender
# =========================================================================
#
# See specs/IDENTITY_RECOGNITION_SPEC.md §"Identity Signature & Apparent
# UID" and §"Pronouns Under Disguise" for the full design rationale.

#: Length in bytes of the blake2b digest backing the Apparent UID.
#: Eight bytes → 16-character lowercase hex string. The 64-bit collision
#: space is comfortable for per-observer recognition memory, where keys
#: are bounded by encounter count.
_APPARENT_UID_DIGEST_BYTES: int = 8

#: Length in characters of an Apparent UID hex string.  Used by the
#: startup wipe migration as a shape check for legacy entries (real
#: ``sleeve_uid`` values are 36-character UUID strings).
APPARENT_UID_HEX_LENGTH: int = _APPARENT_UID_DIGEST_BYTES * 2


def get_essential_item_type_ids(char: Any) -> tuple[str, ...]:
    """Return the sorted tuple of equipped essential disguise item type IDs.

    Walks the character's worn items via
    :meth:`typeclasses.clothing_mixin.ClothingMixin.get_worn_items`,
    selects items flagged ``disguise_essential = True``, and returns
    their ``disguise_type_id`` values as a sorted tuple.  This tuple is
    the fifth element of :func:`get_identity_signature` and so feeds
    directly into the wearer's Apparent UID.

    Two essential items sharing the same ``disguise_type_id`` (e.g. two
    balaclava instances) collapse to a single contribution: the sorted
    tuple deduplicates intentionally so swapping one balaclava for
    another does not shift the wearer's Apparent UID.

    An essential item with an empty ``disguise_type_id`` is *skipped*
    (no contribution) and a soft warning is emitted via
    :func:`evennia.utils.logger.log_warn`; this catches authoring slips
    without breaking recognition for the wearer.

    Characters without :meth:`get_worn_items` (e.g. mocks, NPCs that
    cannot wear clothing) yield an empty tuple.

    Args:
        char: The character whose equipped items are inspected.

    Returns:
        Sorted, deduplicated tuple of ``disguise_type_id`` strings.
    """
    get_worn = getattr(char, "get_worn_items", None)
    if get_worn is None:
        return ()

    type_ids: set[str] = set()
    for item in get_worn():
        if not getattr(item, "disguise_essential", False):
            continue
        type_id = getattr(item, "disguise_type_id", "") or ""
        if not type_id:
            logger.log_warn(
                f"Essential disguise item {item!r} on {char!r} has empty "
                f"disguise_type_id; skipping signature contribution."
            )
            continue
        type_ids.add(type_id)

    return tuple(sorted(type_ids))


def get_identity_signature(char: Any) -> tuple:
    """Compute the identity signature tuple for a character.

    The signature is the input to :func:`get_apparent_uid`.  It captures
    every observable identity input that can shift recognition:

    * The character's real ``sleeve_uid`` (acts as a per-character salt
      — two impostors with identical disguises still produce different
      Apparent UIDs).
    * The active presentation overrides on each axis (height, build,
      keyword), each ``None`` when unset.
    * The sorted tuple of equipped essential disguise item type IDs
      (empty until PR-C lands; see :func:`get_essential_item_type_ids`).

    Re-evaluated on every call from current state — there is no
    cache. Performance optimisation is intentionally deferred.

    Args:
        char: The character whose signature is computed.

    Returns:
        Five-tuple
        ``(sleeve_uid, height_override, build_override, keyword_override,
        essential_item_type_ids)``.
    """
    sleeve_uid = getattr(char, "sleeve_uid", None)
    db = getattr(char, "db", None)
    height_override = db.height_override if db is not None else None
    build_override = db.build_override if db is not None else None
    keyword_override = db.keyword_override if db is not None else None
    return (
        sleeve_uid,
        height_override,
        build_override,
        keyword_override,
        get_essential_item_type_ids(char),
    )


def render_signature_summary(signature: tuple) -> dict:
    """Unpack a stored identity-signature tuple into a labeled dict.

    The 5-tuple returned by :func:`get_identity_signature` is opaque to
    consumers that didn't author it.  This helper provides a stable,
    keyed view for forensic-display callers (corpse autopsy renderers,
    photo-evidence consumers — spec L1000 / L1015 / L1020) so they
    don't index by position.

    The helper is pure: it does not mutate ``signature`` and does not
    touch any character state.  Pass in a tuple previously produced by
    :func:`get_identity_signature` (typically read from
    ``corpse.db.signature_at_death``).

    Args:
        signature: A 5-tuple matching the shape of
            :func:`get_identity_signature`'s return value.

    Returns:
        Dict with keys ``sleeve_uid``, ``height_override``,
        ``build_override``, ``keyword_override``,
        ``essential_item_type_ids``.

    Raises:
        ValueError: If ``signature`` is not a 5-element sequence.
    """
    if signature is None or len(signature) != 5:
        raise ValueError(
            "render_signature_summary expects a 5-element tuple from "
            "get_identity_signature; got: %r" % (signature,)
        )
    return {
        "sleeve_uid": signature[0],
        "height_override": signature[1],
        "build_override": signature[2],
        "keyword_override": signature[3],
        "essential_item_type_ids": signature[4],
    }


def get_apparent_uid(char: Any) -> str | None:
    """Compute the Apparent UID for a character's current presentation.

    Deterministic 16-character lowercase hex digest of the identity
    signature — same signature, same UID, every time, across processes
    (unlike Python's salted builtin ``hash()``).

    Returns ``None`` when the signature has no real ``sleeve_uid``
    (pre-chargen character or other transient state). Callers MUST
    treat ``None`` as "no recognition possible" and skip memory
    lookups; storing entries under ``None`` would conflate distinct
    pre-chargen shells.

    Args:
        char: The character whose Apparent UID is computed.

    Returns:
        16-character hex string, or ``None`` when ``sleeve_uid`` is
        unset.
    """
    signature = get_identity_signature(char)
    if signature[0] is None:
        return None
    signature_bytes = repr(signature).encode("utf-8")
    return hashlib.blake2b(
        signature_bytes, digest_size=_APPARENT_UID_DIGEST_BYTES
    ).hexdigest()


def get_assigned_name(observer: Any, target: Any) -> str | None:
    """Return *observer*'s assigned recognition name for *target*.

    Single source of truth for "what name has the observer chosen to
    remember this character by."  Resolves *target*'s current Apparent
    UID and looks up the matching ``recognition_memory`` entry on
    *observer*, returning its non-empty ``assigned_name``.

    Used by the display-name pipeline (:meth:`Character.get_display_name`),
    identity-aware search (:func:`world.search._match_assigned_name`),
    and the emote/dot-pose target resolver
    (:func:`world.emote.build_char_candidates`) so all three agree on the
    exact name the observer has assigned.

    Note: this returns the assigned name only.  It does NOT attempt
    disguise piercing — callers that need the full display resolution
    (assigned name → pierce → sdesc fallback) should use
    :meth:`Character.get_display_name`.

    Args:
        observer: The character whose recognition memory is consulted.
        target: The character being named.

    Returns:
        The non-empty assigned name string, or ``None`` when the
        observer has no name assigned for *target*'s current
        presentation (including when *target* has no Apparent UID).
    """
    apparent_uid = get_apparent_uid(target)
    if apparent_uid is None:
        return None
    memory = getattr(observer, "recognition_memory", None)
    if not memory or apparent_uid not in memory:
        return None
    assigned = memory[apparent_uid].get("assigned_name") or ""
    return assigned or None


# Decay stages at which a corpse's body-identity axis (``sleeve_uid``) is
# no longer recoverable by an unaided observer.  Stages strictly listed
# here cause :func:`get_apparent_uid_for_decay` to blank the sleeve_uid
# in the signature tuple, producing a UID that no living-character
# memory will match — natural recognition fails, only forensic recovery
# (see :meth:`typeclasses.corpse.Corpse._attempt_forensic_recognition`)
# can restore the original match.
#
# Earlier stages (fresh, early) leave the signature untouched.  The
# ``skeletal`` stage is handled separately as a hard cutoff in
# :meth:`Corpse.get_display_name` — no recognition path returns a name
# for a skeleton, with or without forensics.
_DECAY_SUPPRESS_SLEEVE_UID_STAGES = frozenset({"moderate", "advanced"})


def get_apparent_uid_for_decay(char: Any, stage: str) -> str | None:
    """Compute the Apparent UID a decayed body presents to an unaided observer.

    Same hashing pipeline as :func:`get_apparent_uid`, but with the
    body-identity axis (``sleeve_uid``) blanked when the decay stage is
    advanced enough that an unaided observer cannot resolve the face /
    build / skin signature.  The non-body axes (overrides, worn items)
    are preserved so a recognizable disguise / costume still contributes
    to a partial match — but partial-match UIDs will not collide with
    memory entries written from the fresh, sleeve-keyed presentation.

    Callers compare the result against the observer's recognition memory
    first; if it misses, they may fall back to the un-degraded
    :func:`get_apparent_uid` and gate the recovery on a forensic skill
    check (see :meth:`typeclasses.corpse.Corpse._attempt_forensic_recognition`).

    Args:
        char: The decaying character / corpse.
        stage: One of ``"fresh"``, ``"early"``, ``"moderate"``,
            ``"advanced"``, ``"skeletal"`` (matches
            :meth:`typeclasses.corpse.Corpse.get_decay_stage`).  Unknown
            stages are treated as ``"fresh"`` (no suppression) to fail
            safe toward recognition rather than silently break it.

    Returns:
        16-character hex digest, or ``None`` when the underlying
        signature has no real ``sleeve_uid`` to hash (matching the
        ``None`` semantics of :func:`get_apparent_uid`).
    """
    signature = get_identity_signature(char)
    if signature[0] is None:
        return None
    if stage in _DECAY_SUPPRESS_SLEEVE_UID_STAGES:
        # Blank the sleeve_uid axis; preserve overrides and worn items.
        signature = (None,) + signature[1:]
    signature_bytes = repr(signature).encode("utf-8")
    return hashlib.blake2b(
        signature_bytes, digest_size=_APPARENT_UID_DIGEST_BYTES
    ).hexdigest()


def get_apparent_gender(char: Any) -> str:
    """Return the grammar gender presented by a character's current look.

    Pronouns must follow the disguise: a character presenting as "a
    woman" should be referenced with feminine pronouns by observers
    who do not know the real identity, regardless of the underlying
    ``sex`` attribute.

    Derivation rule:

    1. If the character has an active ``keyword_override``, look it up
       in the runtime keyword catalog (``ServerConfig`` entries, falling
       back to the module-level default frozensets).

       * Match in the feminine list → ``"female"``
       * Match in the masculine list → ``"male"``
       * Match in the neutral list, **or no match anywhere** (custom
         ``describe keyword`` keyword carrying no gender metadata) →
         ``"neutral"``.

    2. Otherwise, fall through to the character's real grammar gender
       via :data:`world.grammar.GENDER_MAP` (no behaviour change for
       undisguised characters).

    There is no explicit ``gender_override`` axis in Phase 3; players
    select pronouns implicitly by choosing a keyword from the desired
    gender list.  Custom keywords always render neutral by design.

    Args:
        char: The character whose apparent gender is computed.

    Returns:
        One of ``"male"``, ``"female"``, ``"neutral"``.
    """
    db = getattr(char, "db", None)
    keyword_override = db.keyword_override if db is not None else None

    if keyword_override:
        keyword_lc = keyword_override.lower()
        if keyword_lc in get_feminine_keywords():
            return "female"
        if keyword_lc in get_masculine_keywords():
            return "male"
        # Neutral list match OR unknown custom keyword → neutral.
        return "neutral"

    # No override → use real grammar gender.
    real_gender = getattr(char, "gender", None)
    if real_gender in ("male", "female", "neutral"):
        return real_gender
    sex_value = getattr(char, "sex", None)
    if sex_value:
        return GENDER_MAP.get(sex_value, "neutral")
    return "neutral"


# ---------------------------------------------------------------------
# Lost-contact orphan marking
# ---------------------------------------------------------------------

#: Inactivity threshold for marking recognition entries as ``lost_contact``.
#: Provisional 30 in-game days; this is a balance-pass tuning value and
#: lives here (the recognition domain) rather than in
#: ``world/combat/constants.py``.
LOST_CONTACT_THRESHOLD_SECONDS: int = 30 * 24 * 60 * 60

#: Format used by ``recognition_memory`` entries for ``first_seen`` /
#: ``last_seen`` timestamps; defined alongside the recognition writers
#: in :mod:`commands.CmdCharacter`.
_RECOGNITION_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S"


def _recognition_utcnow():
    """Return ``datetime.utcnow()``-equivalent as a naive UTC datetime.

    Centralizes the "now in naive UTC" convention used by every
    recognition-memory writer and reader.  Using
    :func:`datetime.datetime.now` with ``tz=timezone.utc`` and then
    stripping the tzinfo preserves the on-disk schema (naive ISO
    strings interpreted as UTC) while sidestepping the
    ``datetime.utcnow()`` deprecation in Python 3.12+.

    Every recognition timestamp in the codebase — writer or reader —
    MUST flow through this helper (or ``_recognition_now_iso``) to
    keep the comparison frame consistent across processes and
    timezones.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _recognition_now_iso() -> str:
    """Return current UTC time formatted per :data:`_RECOGNITION_TIMESTAMP_FMT`.

    Convenience wrapper around :func:`_recognition_utcnow` for
    callers that need the canonical ISO string for storage in a
    ``recognition_memory`` entry.
    """
    return _recognition_utcnow().strftime(_RECOGNITION_TIMESTAMP_FMT)


def _parse_recognition_timestamp(iso_string: str):
    """Parse a stored recognition ISO string back to a naive UTC datetime.

    Symmetric inverse of :func:`_recognition_now_iso`.  Returns the
    naive :class:`datetime.datetime` carrying the same UTC wall time
    that was originally captured; callers that need to compute an
    elapsed delta against "now" should obtain the comparison time
    from :func:`_recognition_utcnow` so both sides share the naive
    UTC frame.

    Raises :class:`ValueError` on malformed input (same contract as
    :meth:`datetime.datetime.strptime`); callers are expected to
    handle that path explicitly rather than swallow it here.
    """
    from datetime import datetime

    return datetime.strptime(iso_string, _RECOGNITION_TIMESTAMP_FMT)


def mark_lost_contact_entries(
    observer: Any,
    current_room_uids: Any,
    *,
    now: Any = None,
) -> int:
    """Flip ``lost_contact`` on stale recognition entries.

    Lazy evaluation pattern: callers invoke this from the
    ``memory`` / ``recall`` command renderers (or any other surface
    that displays recognition data) immediately before iterating
    the observer's ``recognition_memory``.  No background script;
    no per-look hook; the flag only updates when the player would
    notice it.

    Marking rule: an entry is marked ``lost_contact = True`` when

    * its Apparent UID is **not** in ``current_room_uids`` (no one
      currently visible matches that signature), AND
    * its ``last_seen`` timestamp is older than
      :data:`LOST_CONTACT_THRESHOLD_SECONDS` ago.

    The inverse — clearing the flag back to ``False`` on re-meet —
    is handled by the recognition writer in
    :meth:`commands.CmdCharacter.CmdRemember._remember_target`,
    which always writes ``lost_contact = False`` when it updates
    an existing entry.  This helper therefore does not need to
    reset the flag itself; it only flips True.

    Args:
        observer: Character whose ``recognition_memory`` is scanned.
        current_room_uids: Iterable of Apparent UIDs currently visible
            in the observer's room (or any view; the helper is
            indifferent to the source).
        now: Optional :class:`datetime.datetime` for tests; defaults
            to :func:`_recognition_utcnow` (naive UTC) when omitted.

    Returns:
        Number of entries newly flipped to ``True``.  Returns ``0``
        when ``observer`` has no memory or the memory is empty.
    """
    memory = getattr(observer, "recognition_memory", None) or {}
    if not memory:
        return 0

    current = set(current_room_uids or ())
    now = now if now is not None else _recognition_utcnow()
    threshold_seconds = LOST_CONTACT_THRESHOLD_SECONDS

    flipped = 0
    for uid, entry in memory.items():
        # Visible right now → skip; the re-meet path clears the flag.
        if uid in current:
            continue
        # Already flagged → no-op, don't double-count.
        if entry.get("lost_contact", False):
            continue
        last_seen_iso = entry.get("last_seen") or ""
        if not last_seen_iso:
            continue
        try:
            then = _parse_recognition_timestamp(last_seen_iso)
        except ValueError:
            # Malformed timestamp — leave the entry alone, log a hint.
            logger.log_warn(
                f"recognition_memory entry on {observer!r} (uid={uid}) "
                f"has unparseable last_seen={last_seen_iso!r}; skipping "
                f"lost_contact evaluation."
            )
            continue
        if (now - then).total_seconds() > threshold_seconds:
            entry["lost_contact"] = True
            flipped += 1

    return flipped


#: Minimum seconds between passive recency bumps for the same Apparent UID
#: per observer.  Prevents room ping-pong (or extended co-location across
#: many ``at_post_move`` calls) from spamming AttributeProperty writes.
#: 300s = 5 minutes; tunable in a balance pass.
RECOGNITION_BUMP_THROTTLE_SECONDS: int = 300


def bump_recognition_recency(
    observer: Any,
    target: Any,
    apparent_uid: Any,
    *,
    now: Any = None,
) -> bool:
    """Refresh the recency fields on an existing recognition entry.

    Passive perception model: when ``observer`` perceives ``target``
    (currently invoked from ``Character.at_post_move`` for everyone in
    the new room), this helper updates the *recency* fields on the
    matching ``recognition_memory`` entry so ``memory`` / ``recall``
    reflect the latest sighting and so
    :func:`mark_lost_contact_entries` compares against last actual
    sighting rather than last explicit ``remember`` invocation.

    **Strictly opt-in for already-remembered UIDs.**  If
    ``apparent_uid`` is not already a key in
    ``observer.recognition_memory`` this helper is a no-op; it never
    creates entries.  Entry creation remains the exclusive
    responsibility of
    :meth:`commands.CmdCharacter.CmdRemember._remember_target`.  This
    guards against a target whom the observer has never named ever
    appearing in their memory by way of passive perception.

    Throttle: writes are skipped when the existing ``last_seen`` is
    less than :data:`RECOGNITION_BUMP_THROTTLE_SECONDS` ago.  Missing
    or malformed ``last_seen`` is treated as stale and the entry is
    bumped immediately (with a warning logged for the malformed
    case).

    Fields written on a successful bump:

    * ``last_seen`` — current ISO timestamp
    * ``location_last_seen`` — observer's current room key
    * ``sdesc_at_last_encounter`` — fresh snapshot of ``target.get_sdesc()``
    * ``lost_contact`` — cleared to ``False`` (re-sighting clears the flag)

    The ``times_seen`` counter is intentionally **not** incremented;
    it tracks explicit ``remember`` invocations only — see the
    spec's data-model block for the field-by-field semantics.

    Args:
        observer: Character whose ``recognition_memory`` is updated.
        target: Character being perceived; used to snapshot the fresh
            sdesc.
        apparent_uid: Apparent UID computed for ``target`` from the
            observer's vantage point.
        now: Optional :class:`datetime.datetime` for tests; defaults
            to :func:`_recognition_utcnow` (naive UTC) when omitted.

    Returns:
        ``True`` when the entry was bumped; ``False`` when the helper
        was a no-op (UID not in memory, or throttle window not
        elapsed).
    """
    memory = getattr(observer, "recognition_memory", None) or {}
    entry = memory.get(apparent_uid)
    if entry is None:
        return False

    now_dt = now if now is not None else _recognition_utcnow()
    last_seen_iso = entry.get("last_seen") or ""
    if last_seen_iso:
        try:
            then = _parse_recognition_timestamp(last_seen_iso)
        except ValueError:
            logger.log_warn(
                f"recognition_memory entry on {observer!r} "
                f"(uid={apparent_uid}) has unparseable "
                f"last_seen={last_seen_iso!r}; bumping anyway."
            )
        else:
            elapsed = (now_dt - then).total_seconds()
            if elapsed < RECOGNITION_BUMP_THROTTLE_SECONDS:
                return False

    location_name = (
        observer.location.key if observer.location is not None else "unknown"
    )

    entry["last_seen"] = now_dt.strftime(_RECOGNITION_TIMESTAMP_FMT)
    entry["location_last_seen"] = location_name
    entry["sdesc_at_last_encounter"] = target.get_sdesc()
    entry["lost_contact"] = False

    # Lazy backfill of `real_sleeve_uid` for entries that pre-date the
    # schema add (see :func:`_remember_target`).  Bump paths are the
    # primary backfill surface because they run on every visible
    # re-encounter; entries the observer never sees again retain their
    # legacy shape (and are silently ineligible for disguise-piercing
    # reverse lookup, which is acceptable per the pre-alpha decision).
    if entry.get("real_sleeve_uid") is None:
        real_sleeve_uid = getattr(target, "sleeve_uid", None)
        if real_sleeve_uid:
            entry["real_sleeve_uid"] = real_sleeve_uid

    # Reassign so the AttributeProperty persists the in-place mutation.
    observer.recognition_memory = memory
    return True


def find_entries_by_real_sleeve_uid(
    observer: Any, real_sleeve_uid: str
) -> list[tuple[str, dict]]:
    """Return all recognition entries belonging to a given underlying sleeve.

    Reverse lookup over ``observer.recognition_memory``: returns the
    list of ``(apparent_uid, entry)`` pairs whose ``real_sleeve_uid``
    field matches the supplied value.  Used by disguise-piercing
    recognition (PR-X3) to discover "have I previously remembered this
    physical person under any presentation?" without walking every
    entry by-hand at each call site.

    Pre-schema entries (those without a ``real_sleeve_uid`` field —
    see :func:`bump_recognition_recency` lazy backfill) are silently
    skipped: they cannot be reverse-keyed by definition.  This is the
    accepted cost of the lazy-backfill strategy (pre-alpha; legacy
    entries simply remain pierce-ineligible until the observer re-
    encounters the target through any writer path).

    A ``real_sleeve_uid`` of ``None`` or empty string returns ``[]``
    immediately; the caller must have already resolved the target's
    actual sleeve to a non-empty value.

    Args:
        observer: Character whose recognition memory is searched.
        real_sleeve_uid: The underlying sleeve UID to match against.

    Returns:
        List of ``(apparent_uid, entry)`` pairs in insertion order;
        empty when no entries match or the observer has no memory.
    """
    if not real_sleeve_uid:
        return []
    memory = getattr(observer, "recognition_memory", None) or {}
    if not memory:
        return []
    return [
        (uid, entry)
        for uid, entry in memory.items()
        if entry.get("real_sleeve_uid") == real_sleeve_uid
    ]


# =========================================================================
# Disguise Piercing — Opposed recognition roll
# =========================================================================
#
# When an observer looks at a target whose current Apparent UID is not in
# their recognition memory, but the target's underlying ``sleeve_uid``
# matches a *different* presentation they previously remembered (the
# "bare-face entry"), the observer rolls Intellect against the target's
# Resonance to "see through" the disguise.
#
# Modelled on the corpse-forensic-recovery pattern
# (``typeclasses/corpse.py:_attempt_forensic_recognition``):
# permanent per-``(observer, target, apparent_uid)`` cache so a single
# careful look determines the verdict for that specific presentation;
# entering a new disguise rolls again.
#
# Familiarity (``times_seen`` on the bare-face entry) buffs the
# observer's roll; the number of disguise vectors the target is using
# (worn ``disguise_essential`` items + active overrides) penalises it.

#: Per-disguise-vector penalty applied to the observer's roll.
DISGUISE_PIERCE_VECTOR_PENALTY = 1

#: Soft cap on familiarity bonus (``min(times_seen, CAP)``) — keeps a
#: grizzled veteran from auto-piercing every disguise on Earth.
DISGUISE_PIERCE_FAMILIARITY_CAP = 5


def _count_disguise_vectors(target: Any) -> int:
    """Return the count of active disguise vectors on *target*.

    A "vector" is anything that perturbs the Apparent UID away from the
    bare sleeve.  Each of the three string overrides
    (``height_override``, ``build_override``, ``keyword_override``)
    counts once when set.  Each worn ``disguise_essential`` item
    contributes its ``disguise_weight`` (default ``1``) so heavy
    concealment (full prosthetic mask, hooded robe) can scale piercing
    difficulty independently of how many items are involved.  A
    weight of ``0`` lets an essential item still pin the identity
    signature without making piercing harder.  Missing or non-numeric
    weights fall back to ``1``.

    Used by :func:`compute_disguise_pierce` to penalise the observer's
    roll: heavier disguises are harder to see through.
    """
    vectors = 0
    get_worn = getattr(target, "get_worn_items", None)
    if callable(get_worn):
        try:
            worn = get_worn() or []
        except (AttributeError, TypeError):
            worn = []
        for item in worn:
            if not getattr(item, "disguise_essential", False):
                continue
            raw_weight = getattr(item, "disguise_weight", 1)
            try:
                weight = int(raw_weight)
            except (TypeError, ValueError):
                weight = 1
            # Guard against negative or absurd weights; clamp to a
            # non-negative integer so the penalty stays well-defined.
            if weight < 0:
                weight = 0
            vectors += weight
    db = getattr(target, "db", None)
    if db is not None:
        for field in ("height_override", "build_override", "keyword_override"):
            if getattr(db, field, None):
                vectors += 1
    return vectors


def attempt_disguise_pierce(
    observer: Any, target: Any, apparent_uid: str, bare_entry: dict
) -> bool:
    """Resolve (and cache) a disguise-piercing recognition roll.

    Permanent per-``(observer, target, apparent_uid)`` cache stored on
    ``observer.db.disguise_pierce_cache`` as
    ``{(target.dbref, apparent_uid): bool}``.  An observer who fails to
    pierce a specific presentation will keep failing until that
    presentation changes; success sticks for that presentation.  This
    mirrors the corpse forensic-recovery contract: one careful look
    determines the verdict, no re-roll abuse on every ``look``.
    Observers or targets without a ``dbref`` are not cached and re-roll
    on every call (keeps the cache bounded, no junk keys for tooling).
    Anonymous targets (no ``apparent_uid``) are likewise un-cached.

    **dbref recycling and stale entries.**  Cache entries keyed on a
    deleted target's ``dbref`` are dead weight but cannot misfire:
    Evennia / Django uses monotonically-increasing primary keys (no
    reuse), so a future object will never collide with a stale entry's
    key.  No pruning hook is wired at delete time — entries simply
    accumulate at the rate the observer encounters distinct
    presentations, which in practice is bounded by their social
    surface.  If pruning becomes warranted (very long-lived observers
    + churn-heavy NPC populations), the right place to hook it is an
    ``at_object_delete`` on the target side that broadcasts to
    in-room observers, mirroring the unmasking-moment pipeline.

    The roll is opposed ``Intellect`` (observer) vs ``Resonance``
    (target), with:

      * **Familiarity bonus** added to the observer: ``min(times_seen,
        DISGUISE_PIERCE_FAMILIARITY_CAP)`` from the bare-face entry.
      * **Disguise penalty** subtracted from the observer:
        ``DISGUISE_PIERCE_VECTOR_PENALTY * count_of_active_vectors``
        (worn ``disguise_essential`` items + active overrides).

    Ties favour the target (the disguise holds).

    Args:
        observer: Character attempting recognition.
        target: Character being observed (must have a ``sleeve_uid``).
        apparent_uid: The target's *current* Apparent UID — the
            disguised presentation being pierced.  Used as the cache
            key so each new disguise gets a fresh roll.
        bare_entry: The previously-remembered recognition entry for
            this sleeve (from :func:`find_entries_by_real_sleeve_uid`);
            its ``times_seen`` feeds the familiarity bonus.

    Returns:
        ``True`` if the observer pierces the disguise (caller should
        surface the bare entry's ``assigned_name``), ``False`` otherwise.
    """
    from world.combat.dice import opposed_roll

    observer_dbref = getattr(observer, "dbref", None)
    target_dbref = getattr(target, "dbref", None)
    cacheable = (
        observer_dbref is not None
        and target_dbref is not None
        and bool(apparent_uid)
    )

    if cacheable:
        cache = observer.db.disguise_pierce_cache
        if cache is None:
            cache = {}
        key = (target_dbref, apparent_uid)
        if key in cache:
            return bool(cache[key])
    else:
        cache = None
        key = None

    obs_roll, tgt_roll, _ = opposed_roll(
        observer, target, "intellect", "resonance"
    )

    familiarity = min(
        int(bare_entry.get("times_seen", 0) or 0),
        DISGUISE_PIERCE_FAMILIARITY_CAP,
    )
    penalty = _count_disguise_vectors(target) * DISGUISE_PIERCE_VECTOR_PENALTY

    success = (obs_roll + familiarity) > (tgt_roll + penalty)

    if cacheable:
        cache[key] = success
        observer.db.disguise_pierce_cache = cache

    return success


def invalidate_pierce_cache_for_sleeve(
    observer: Any, real_sleeve_uid: str | None
) -> int:
    """Drop pierce-cache entries for every presentation of ``real_sleeve_uid``.

    Walks :attr:`observer.recognition_memory` to collect every
    ``apparent_uid`` belonging to the supplied sleeve (via the
    ``real_sleeve_uid`` field populated by :func:`_remember_target`
    and the unmasking-moments lazy backfill), then removes any
    ``(target_dbref, apparent_uid)`` key from
    ``observer.db.disguise_pierce_cache`` whose ``apparent_uid``
    matches.

    Used by ``CmdForget`` (see ``commands/CmdCharacter.py``) so the
    cognitive act of forgetting a person also discards every cached
    pierce verdict for any disguise that person has worn.  Without
    this invalidation, :func:`attempt_disguise_pierce` short-circuits
    on a cached ``True`` and surfaces the bare-face entry's
    ``assigned_name`` from any *other* (still-named) entry sharing the
    sleeve — leaving forgotten targets perpetually recognized through
    disguises.  See issue #210.

    Sleeve-wide scope matches the semantics of forget: the player is
    declaring "I no longer know this person", not "I no longer know
    this particular presentation".  Per-``apparent_uid`` invalidation
    would leave stale ``True`` verdicts the moment the target swaps
    any signature axis.

    Pre-schema memory entries (missing ``real_sleeve_uid``) are
    silently skipped — same contract as
    :func:`find_entries_by_real_sleeve_uid`.  A missing or empty
    ``real_sleeve_uid`` argument is a no-op.  Missing or empty cache
    is a no-op.

    Args:
        observer: Character whose pierce cache is pruned.
        real_sleeve_uid: The underlying sleeve UID whose
            presentations should be invalidated.

    Returns:
        Count of cache entries removed.
    """
    if not real_sleeve_uid:
        return 0
    cache = observer.db.disguise_pierce_cache
    if not cache:
        return 0

    matching_uids = {
        apparent_uid
        for apparent_uid, _entry in find_entries_by_real_sleeve_uid(
            observer, real_sleeve_uid
        )
    }
    if not matching_uids:
        return 0

    keys_to_drop = [
        key for key in cache
        if isinstance(key, tuple) and len(key) == 2
        and key[1] in matching_uids
    ]
    for key in keys_to_drop:
        del cache[key]

    if keys_to_drop:
        observer.db.disguise_pierce_cache = cache

    return len(keys_to_drop)


def attempt_display_pierce(
    looker: Any, target: Any, apparent_uid: str | None
) -> str | None:
    """High-level pierce wrapper for the display-name pipeline.

    Called from :meth:`Character.get_display_name` and
    :meth:`Character.get_look_header` when the looker does not already
    recognise the target's current Apparent UID.  Finds candidate
    bare-face entries via reverse sleeve lookup, then defers to
    :func:`attempt_disguise_pierce` for the actual opposed roll.

    The first candidate (insertion order) wins; this corresponds to
    "the earliest presentation the looker remembered for this sleeve".
    The current (disguised) presentation is filtered out so we never
    pierce a presentation against itself.

    Args:
        looker: The observer.
        target: The character being looked at.
        apparent_uid: ``target``'s current Apparent UID.

    Returns:
        The pierced ``assigned_name`` on success, or ``None`` when no
        pierce occurs (missing memory, missing sleeve, no candidates,
        or failed roll).
    """
    if looker is None or looker is target or not apparent_uid:
        return None
    memory = getattr(looker, "recognition_memory", None)
    if not memory:
        return None
    real_sleeve = getattr(target, "sleeve_uid", None)
    if not real_sleeve:
        return None

    candidates = [
        (uid, entry)
        for uid, entry in find_entries_by_real_sleeve_uid(looker, real_sleeve)
        if uid != apparent_uid and entry.get("assigned_name")
    ]
    if not candidates:
        return None

    _bare_uid, bare_entry = candidates[0]
    if attempt_disguise_pierce(looker, target, apparent_uid, bare_entry):
        return bare_entry.get("assigned_name")
    return None


# =========================================================================
# Unmasking Moments — Apparent UID transition broadcast
# =========================================================================
#
# The "unmasking moment" is the event of a character's Apparent UID
# shifting (puts on or removes a disguise-essential item, applies an
# override, etc.) while other characters can perceive them.  For each
# in-room conscious observer, the broadcast pipeline updates their
# recognition memory according to a 4-cell matrix keyed on whether
# they previously knew the old UID, the new UID, both, or neither.
#
# See specs/IDENTITY_RECOGNITION_SPEC.md (Unmasking Moments) for the
# end-to-end behavioural contract.

#: Hard cap on link-chain traversal to bound work on malformed data.
#: Linked chains are uncapped per design (no per-chain user-facing
#: limit), but the walker still terminates if it visits this many
#: distinct UIDs without exhausting the chain — a safety net against
#: corrupted entries, not a UX constraint.
_LINKED_CHAIN_MAX_HOPS: int = 64


def _build_link_entry(
    *,
    target: Any,
    observer: Any,
    linked_to: str | None,
    now_iso: str,
    location_name: str,
) -> dict:
    """Build a fresh recognition-memory entry for an auto-linked sighting.

    Mirrors the shape written by
    :meth:`commands.CmdCharacter.CmdRemember._remember_target` but with
    ``assigned_name=""`` (the observer has not chosen to name this
    presentation) and ``linked_to`` pointing at the prior UID we just
    saw transition away from.

    Pulled out as a helper so the broadcast pipeline and the test suite
    agree on entry shape; the field set must stay in lock-step with
    ``_identity_helpers.make_recognition_entry`` and the production
    ``_remember_target``.

    Args:
        target: The character whose UID just transitioned.
        observer: The character whose memory is being updated.
        linked_to: Apparent UID of the prior presentation, or ``None``.
        now_iso: ISO timestamp string to stamp ``first_seen`` /
            ``last_seen``.
        location_name: Room key for ``location_first_seen`` /
            ``location_last_seen``.

    Returns:
        Recognition-memory entry dict ready to be stored under the new
        Apparent UID.
    """
    del observer  # reserved for future per-observer customisation
    sdesc = target.get_sdesc() if hasattr(target, "get_sdesc") else ""
    real_sleeve_uid = getattr(target, "sleeve_uid", None)
    return {
        "assigned_name": "",
        "first_seen": now_iso,
        "last_seen": now_iso,
        "times_seen": 1,
        "location_first_seen": location_name,
        "location_last_seen": location_name,
        "locations_seen": [location_name],
        "sdesc_at_first_encounter": sdesc,
        "sdesc_at_last_encounter": sdesc,
        "notes": "",
        "tags": [],
        "confidence": 1.0,
        "relationship_valence": "neutral",
        "lost_contact": False,
        "recent_interactions": [],
        "linked_to": linked_to,
        "real_sleeve_uid": real_sleeve_uid,
    }


def _collect_unmasking_observers(char: Any) -> list:
    """Return the list of characters eligible to witness an unmasking.

    Filters in this order:

    1. Must share ``char.location`` (visual perception is room-local).
    2. Must not be ``char`` themselves (you don't witness your own
       unmasking through recognition memory — you know who you are).
    3. Must have a ``recognition_memory`` attribute (excludes items,
       exits, mobs without the identity surface).
    4. Must not be unconscious — perception requires awareness.

    Characters lacking :meth:`is_unconscious` are treated as conscious
    (matches the conservative default used elsewhere in the codebase).

    Args:
        char: The character whose unmasking is being broadcast.

    Returns:
        List of observer characters, in iteration order of
        ``char.location.contents`` (stable per Evennia's storage).
    """
    location = getattr(char, "location", None)
    if location is None:
        return []
    contents = getattr(location, "contents", None) or []

    observers: list = []
    for candidate in contents:
        if candidate is char:
            continue
        if not hasattr(candidate, "recognition_memory"):
            continue
        is_unconscious = getattr(candidate, "is_unconscious", None)
        if callable(is_unconscious):
            try:
                if is_unconscious():
                    continue
            except (AttributeError, TypeError, ValueError):
                # Defensive: a broken medical surface should not stop
                # the broadcast for everyone in the room.
                logger.log_trace(
                    f"is_unconscious() raised for {candidate!r}; "
                    f"treating as conscious for unmasking broadcast."
                )
        observers.append(candidate)
    return observers


def _send_unmasking_message(
    observer: Any,
    char: Any,
    cell: str,
    old_uid: str | None = None,
    new_uid: str | None = None,
) -> None:
    """Send per-cell narrative observer message for an unmasking moment.

    Routed as a direct per-observer ``.msg()`` call rather than through
    :func:`world.identity_utils.msg_room_identity`, because the recipient
    list is already narrowed by :func:`_collect_unmasking_observers` and
    the prose is tailored to what *this* observer knew going in.

    Cell semantics (see :func:`_broadcast_unmasking`):

    * **A** — never reaches this hook (short-circuited upstream).
    * **B** (knew old only) — recognition gained: a familiar presentation
      just walked out of view and a new one arrived in its place.
    * **C** (knew new only) — silent.  The observer already knew the new
      presentation; there is nothing to learn from the transition.
    * **D** (knew both) — link discovered: the observer realises that
      two presentations they had been tracking independently belong to
      the same person.

    The cell-B and cell-D prose follow the same noir, recognition-
    centric voice used by the wear/remove emote pipeline.

    Args:
        observer: The character receiving the message.
        char: The character whose apparent UID just changed.
        cell: Matrix cell label (``"B"`` / ``"C"`` / ``"D"``).
        old_uid: Pre-mutation apparent UID, used to look up the old
            presentation's stored sdesc / assigned name.
        new_uid: Post-mutation apparent UID, used to look up the new
            presentation's assigned name (its sdesc is the live one).
    """
    if cell == "C":
        # Silent: the observer already knew the new presentation;
        # the transition carries no new information for them.
        return

    memory = getattr(observer, "recognition_memory", None) or {}

    new_sdesc = char.get_sdesc() if hasattr(char, "get_sdesc") else ""

    old_entry = memory.get(old_uid) if old_uid else None
    old_sdesc = ""
    if old_entry is not None:
        old_sdesc = old_entry.get("sdesc_at_last_encounter") or ""

    if cell == "B":
        # Recognition gained — the familiar face has shifted to a new
        # presentation in front of the observer.
        if not old_sdesc or not new_sdesc:
            # Defensive: missing sdescs would render an ugly message.
            # Skip rather than ship broken prose.
            return
        observer.msg(
            f"{new_sdesc} steps into view where {old_sdesc} "
            f"stood a moment ago."
        )
        return

    if cell == "D":
        # Link discovered — the observer realises two tracked
        # presentations are the same person.
        new_entry = memory.get(new_uid) if new_uid else None
        old_name = (old_entry or {}).get("assigned_name") or ""
        new_name = (new_entry or {}).get("assigned_name") or ""
        if not old_sdesc or not new_sdesc:
            return
        if old_name and new_name:
            observer.msg(
                f"You realize that {old_sdesc}, who you call "
                f"{old_name}, and {new_sdesc}, who you call "
                f"{new_name}, are the same person."
            )
        else:
            # Defensive fallback: cell D should always have both names
            # set, but if a future code path drops one we still emit
            # something coherent.
            observer.msg(
                f"You realize that {old_sdesc} and {new_sdesc} "
                f"are the same person."
            )
        return


def _broadcast_unmasking(
    char: Any,
    old_uid: str | None,
    new_uid: str | None,
    source: str | None = None,
) -> None:
    """Update every eligible observer's recognition memory for a UID flip.

    Implements the 4-cell matrix:

    * **A** (knew neither): no-op.
    * **B** (knew old, not new): old entry → ``lost_contact=True``;
      auto-create new entry with ``linked_to=old_uid``.
    * **C** (not old, knew new): refresh new entry's ``last_seen`` and
      clear ``lost_contact``; no link formed (we never met the old
      presentation, so there's nothing to chain).
    * **D** (knew both): old entry → ``lost_contact=True``; new entry
      refreshed; ``linked_to`` set on the new entry (if not already)
      pointing at ``old_uid``.  Existing ``assigned_name`` on either
      side is preserved untouched.

    ``old_uid`` or ``new_uid`` being ``None`` (pre-chargen, missing
    sleeve_uid) short-circuits the entire broadcast — there is nothing
    meaningful to record.

    Args:
        char: The character whose UID just changed.
        old_uid: Apparent UID before the mutation.
        new_uid: Apparent UID after the mutation.
        source: Free-form provenance tag (``"wear:balaclava"`` etc.)
            forwarded to the flavor-text hook for future use.
    """
    if old_uid is None or new_uid is None:
        return
    if old_uid == new_uid:
        return

    now_iso = _recognition_now_iso()

    for observer in _collect_unmasking_observers(char):
        memory = getattr(observer, "recognition_memory", None)
        if memory is None:
            memory = {}

        knew_old = old_uid in memory
        knew_new = new_uid in memory
        location_name = (
            observer.location.key
            if getattr(observer, "location", None) is not None
            else "unknown"
        )

        if not knew_old and not knew_new:
            # Cell A — stranger remains a stranger.
            continue

        if knew_old and not knew_new:
            # Cell B — old presentation just left view; new presentation
            # arrives as a fresh sighting linked back to the old one.
            memory[old_uid]["lost_contact"] = True
            # Lazy backfill: same contract as cells C and D — touch
            # every entry we mutate so legacy entries become pierce-
            # eligible at the earliest opportunity.
            if memory[old_uid].get("real_sleeve_uid") is None:
                real_sleeve_uid = getattr(char, "sleeve_uid", None)
                if real_sleeve_uid:
                    memory[old_uid]["real_sleeve_uid"] = real_sleeve_uid
            memory[new_uid] = _build_link_entry(
                target=char,
                observer=observer,
                linked_to=old_uid,
                now_iso=now_iso,
                location_name=location_name,
            )
            observer.recognition_memory = memory
            _send_unmasking_message(
                observer, char, "B", old_uid=old_uid, new_uid=new_uid
            )
            continue

        if not knew_old and knew_new:
            # Cell C — we never met the old presentation; just refresh
            # the new one as we would on any re-sighting.
            entry = memory[new_uid]
            entry["last_seen"] = now_iso
            entry["location_last_seen"] = location_name
            entry["lost_contact"] = False
            if hasattr(char, "get_sdesc"):
                entry["sdesc_at_last_encounter"] = char.get_sdesc()
            # Lazy backfill of `real_sleeve_uid` (see _remember_target).
            if entry.get("real_sleeve_uid") is None:
                real_sleeve_uid = getattr(char, "sleeve_uid", None)
                if real_sleeve_uid:
                    entry["real_sleeve_uid"] = real_sleeve_uid
            observer.recognition_memory = memory
            _send_unmasking_message(
                observer, char, "C", old_uid=old_uid, new_uid=new_uid
            )
            continue

        # Cell D — observer knew both presentations independently.
        # Refresh both, link new → old if not already linked, but never
        # rewrite assigned_name (player-authored data is sacrosanct).
        memory[old_uid]["lost_contact"] = True
        new_entry = memory[new_uid]
        new_entry["last_seen"] = now_iso
        new_entry["location_last_seen"] = location_name
        new_entry["lost_contact"] = False
        if hasattr(char, "get_sdesc"):
            new_entry["sdesc_at_last_encounter"] = char.get_sdesc()
        if new_entry.get("linked_to") is None:
            new_entry["linked_to"] = old_uid
        # Lazy backfill of `real_sleeve_uid` on both entries; cell D
        # touches both, so backfill both opportunistically.
        real_sleeve_uid = getattr(char, "sleeve_uid", None)
        if real_sleeve_uid:
            if new_entry.get("real_sleeve_uid") is None:
                new_entry["real_sleeve_uid"] = real_sleeve_uid
            if memory[old_uid].get("real_sleeve_uid") is None:
                memory[old_uid]["real_sleeve_uid"] = real_sleeve_uid
        observer.recognition_memory = memory
        _send_unmasking_message(
            observer, char, "D", old_uid=old_uid, new_uid=new_uid
        )

    del source  # reserved for future debug/flavor routing


class apply_signature_change:
    """Context manager wrapping any mutation of a character's identity signature.

    Captures the Apparent UID on enter, yields to the caller for the
    mutation, then captures the post-mutation UID on exit and fires
    :func:`_broadcast_unmasking` if it changed.

    Use at every site that writes a signature input:

    * ``db.height_override`` / ``db.build_override`` / ``db.keyword_override``
    * Wearing or removing a ``disguise_essential`` item
    * Bulk persona application

    Exceptions raised inside the ``with`` block propagate normally and
    suppress the broadcast — a failed mutation should not pretend the
    UID changed.

    Usage::

        with apply_signature_change(char, source="override:height"):
            char.db.height_override = "tall"

    Args:
        char: The character whose signature is being mutated.
        source: Optional free-form tag describing the mutation, passed
            through to the flavor-text hook (currently unused).
    """

    def __init__(self, char: Any, source: str | None = None) -> None:
        self.char = char
        self.source = source
        self._old_uid: str | None = None

    def __enter__(self) -> "apply_signature_change":
        self._old_uid = get_apparent_uid(self.char)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            # Mutation failed; do not broadcast.
            return False
        new_uid = get_apparent_uid(self.char)
        _broadcast_unmasking(
            self.char, self._old_uid, new_uid, source=self.source
        )
        return False


def walk_linked_chain(
    memory: dict, start_uid: str, max_hops: int = _LINKED_CHAIN_MAX_HOPS
) -> list[str]:
    """Walk a recognition-memory ``linked_to`` chain from ``start_uid``.

    Returns the list of UIDs reachable from (and including)
    ``start_uid``, in traversal order, with cycle detection.  A UID
    encountered twice terminates the walk silently — corrupted data
    must not hang the engine.

    The ``max_hops`` cap is a defensive safety net against pathological
    data only; per design there is no user-facing chain-length limit.

    Args:
        memory: A ``recognition_memory`` dict.
        start_uid: UID to begin the walk from.  Returns ``[]`` if not
            present in ``memory``.
        max_hops: Defensive cap on distinct UIDs visited.

    Returns:
        List of UIDs visited in walk order, starting with ``start_uid``.
    """
    if start_uid not in memory:
        return []
    chain: list[str] = []
    seen: set = set()
    current: str | None = start_uid
    while current is not None and current in memory:
        if current in seen:
            logger.log_warn(
                f"recognition_memory linked_to cycle detected at "
                f"uid={current!r}; truncating chain walk."
            )
            break
        seen.add(current)
        chain.append(current)
        if len(chain) >= max_hops:
            break
        current = memory[current].get("linked_to")
    return chain


def get_linked_aliases(memory: dict, uid: str) -> list[str]:
    """Return assigned names from entries linked to ``uid`` (excluding self).

    Walks the chain via :func:`walk_linked_chain`, skips the starting
    UID, and collects non-blank ``assigned_name`` values from every
    other entry in the chain.

    Used by ``recall`` / ``memory`` to render "Also known as: …" lines
    so the player can see when the engine has observed a body
    transition between two named presentations.

    Args:
        memory: A ``recognition_memory`` dict.
        uid: The starting UID whose chain is inspected.

    Returns:
        List of assigned names found on linked entries (excluding the
        entry at ``uid`` itself), in traversal order.  Blank names are
        omitted.
    """
    aliases: list[str] = []
    for chain_uid in walk_linked_chain(memory, uid):
        if chain_uid == uid:
            continue
        entry = memory.get(chain_uid)
        if entry is None:
            continue
        name = (entry.get("assigned_name") or "").strip()
        if name:
            aliases.append(name)
    return aliases

