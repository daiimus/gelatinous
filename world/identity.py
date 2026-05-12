"""
Identity Constants and Sdesc Composition

Data tables and pure functions for the identity and recognition system:
physical descriptor lookup, keyword validation, hair options, distinguishing
feature formatting, and short description (sdesc) composition.

This module has no Evennia dependencies in its core functions (except for
:class:`KeywordManager`, which is an Evennia Script, and
:class:`~world.models.KeywordEvent`, a Django model).

See specs/IDENTITY_RECOGNITION_SPEC.md for the full specification.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ObjectDoesNotExist
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger

from world.grammar import GENDER_MAP, get_article

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

#: Default feminine keywords — seeds for the :class:`KeywordManager` script.
#: At runtime, use :func:`get_feminine_keywords` instead.
_DEFAULT_FEMININE_KEYWORDS: frozenset[str] = frozenset({
    "female", "girl", "lass", "woman", "matron", "grandma", "hag", "granny",
    "madam", "tomboy", "chick", "gal", "chica", "vixen",
    "diva", "dame", "sheila", "mona", "bimbo", "bitch", "lady", "senorita",
    "chola", "devotchka",
})

#: Default masculine keywords — seeds for the :class:`KeywordManager` script.
#: At runtime, use :func:`get_masculine_keywords` instead.
_DEFAULT_MASCULINE_KEYWORDS: frozenset[str] = frozenset({
    "male", "boy", "lad", "man", "patron", "grandpa", "geezer", "gramps",
    "gentleman", "guy", "fellow", "dude", "playa",
    "pimp", "bloke", "bruce", "mano", "bro", "douche", "stiff", "hombre",
    "cholo", "droog",
})

#: Default neutral keywords — seeds for the :class:`KeywordManager` script.
#: At runtime, use :func:`get_neutral_keywords` instead.
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
# KeywordManager Script  (runtime keyword list storage)
# =========================================================================

_KEYWORD_MANAGER_KEY = "keyword_manager"


def _get_keyword_manager() -> "KeywordManager":
    """Return the singleton :class:`KeywordManager` script.

    Looks up the script by key in the database.  Evennia's
    ``GLOBAL_SCRIPTS`` registry (configured in
    ``server/conf/settings.py``) guarantees the script exists at
    server startup and recreates it if it is ever deleted.

    Returns:
        The keyword manager script instance.

    Raises:
        ``ScriptDB.DoesNotExist``: If the script has not been created
            yet (e.g. during unit tests that bypass server startup).
    """
    from evennia.scripts.models import ScriptDB

    return ScriptDB.objects.get(db_key=_KEYWORD_MANAGER_KEY)


class KeywordManager(DefaultScript):
    """Global script that stores the approved keyword lists.

    Managed by Evennia's ``GLOBAL_SCRIPTS`` registry (configured in
    ``server/conf/settings.py``).  Access via :func:`_get_keyword_manager`.
    Stores three mutable sets on ``db`` attributes:

    * ``db.feminine_keywords`` — :class:`set` of feminine keywords
    * ``db.masculine_keywords`` — :class:`set` of masculine keywords
    * ``db.neutral_keywords`` — :class:`set` of neutral keywords

    These are seeded from the module-level ``_DEFAULT_*`` frozensets on
    first creation and may be modified at runtime via
    :func:`add_approved_keyword` / :func:`remove_approved_keyword`.
    """

    def at_script_creation(self) -> None:
        self.key = _KEYWORD_MANAGER_KEY
        self.persistent = True
        self.db.feminine_keywords = set(_DEFAULT_FEMININE_KEYWORDS)  # type: ignore[attr-defined]
        self.db.masculine_keywords = set(_DEFAULT_MASCULINE_KEYWORDS)  # type: ignore[attr-defined]
        self.db.neutral_keywords = set(_DEFAULT_NEUTRAL_KEYWORDS)  # type: ignore[attr-defined]


# =========================================================================
# Keyword Getters  (read from KeywordManager, fall back to defaults)
# =========================================================================


def get_feminine_keywords() -> frozenset[str]:
    """Return the current set of approved feminine keywords.

    Reads from the :class:`KeywordManager` script via
    ``GLOBAL_SCRIPTS``.  Falls back to
    :data:`_DEFAULT_FEMININE_KEYWORDS` during tests or early startup.

    Returns:
        Frozenset of feminine keyword strings.
    """
    try:
        mgr = _get_keyword_manager()
        kws: set[str] | None = mgr.db.feminine_keywords
        if kws is not None:
            return frozenset(kws)
    except ObjectDoesNotExist:
        pass
    except Exception:
        logger.log_trace("Unexpected error reading KeywordManager")
    return _DEFAULT_FEMININE_KEYWORDS


def get_masculine_keywords() -> frozenset[str]:
    """Return the current set of approved masculine keywords.

    Reads from the :class:`KeywordManager` script via
    ``GLOBAL_SCRIPTS``.  Falls back to
    :data:`_DEFAULT_MASCULINE_KEYWORDS` during tests or early startup.

    Returns:
        Frozenset of masculine keyword strings.
    """
    try:
        mgr = _get_keyword_manager()
        kws: set[str] | None = mgr.db.masculine_keywords
        if kws is not None:
            return frozenset(kws)
    except ObjectDoesNotExist:
        pass
    except Exception:
        logger.log_trace("Unexpected error reading KeywordManager")
    return _DEFAULT_MASCULINE_KEYWORDS


def get_neutral_keywords() -> frozenset[str]:
    """Return the current set of approved neutral keywords.

    Reads from the :class:`KeywordManager` script via
    ``GLOBAL_SCRIPTS``.  Falls back to
    :data:`_DEFAULT_NEUTRAL_KEYWORDS` during tests or early startup.

    Returns:
        Frozenset of neutral keyword strings.
    """
    try:
        mgr = _get_keyword_manager()
        kws: set[str] | None = mgr.db.neutral_keywords
        if kws is not None:
            return frozenset(kws)
    except ObjectDoesNotExist:
        pass
    except Exception:
        logger.log_trace("Unexpected error reading KeywordManager")
    return _DEFAULT_NEUTRAL_KEYWORDS


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


def add_approved_keyword(
    keyword: str,
    gender_list: str,
    admin_name: str = "",
) -> tuple[bool, str]:
    """Add a keyword to an approved gender list.

    Creates a :class:`~world.models.KeywordEvent` with event type
    ``admin_add`` and adds the keyword to the :class:`KeywordManager`
    script's set for the given gender list.

    Args:
        keyword: Keyword to add (lowercase).
        gender_list: One of ``"feminine"``, ``"masculine"``, or
            ``"neutral"``.
        admin_name: Name of the admin performing the action.

    Returns:
        ``(True, "")`` on success, or ``(False, reason)`` on failure.
    """
    attr_map = {
        "feminine": "feminine_keywords",
        "masculine": "masculine_keywords",
        "neutral": "neutral_keywords",
    }
    attr_name = attr_map.get(gender_list)
    if attr_name is None:
        return False, f"Invalid gender list {gender_list!r}."

    mgr = _get_keyword_manager()
    kw_set: set[str] | None = getattr(mgr.db, attr_name)
    if kw_set is None:
        kw_set = set()
    if keyword in kw_set:
        return False, f"'{keyword}' is already in the {gender_list} list."

    kw_set.add(keyword)
    setattr(mgr.db, attr_name, kw_set)

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
    ``admin_remove`` and removes the keyword from the
    :class:`KeywordManager` script's set for the given gender list.

    Args:
        keyword: Keyword to remove (lowercase).
        gender_list: One of ``"feminine"``, ``"masculine"``, or
            ``"neutral"``.
        admin_name: Name of the admin performing the action.

    Returns:
        ``(True, "")`` on success, or ``(False, reason)`` on failure.
    """
    attr_map = {
        "feminine": "feminine_keywords",
        "masculine": "masculine_keywords",
        "neutral": "neutral_keywords",
    }
    attr_name = attr_map.get(gender_list)
    if attr_name is None:
        return False, f"Invalid gender list {gender_list!r}."

    mgr = _get_keyword_manager()
    kw_set: set[str] | None = getattr(mgr.db, attr_name)
    if kw_set is None or keyword not in kw_set:
        return False, f"'{keyword}' is not in the {gender_list} list."

    kw_set.discard(keyword)
    setattr(mgr.db, attr_name, kw_set)

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
    article = get_article(item_name)
    return f"wielding {article} {item_name}"


def format_clothing_feature(item_name: str) -> str:
    """Format an outermost clothing item as a distinguishing feature clause.

    Args:
        item_name: The item's display name (e.g. ``"Black Trenchcoat"``).

    Returns:
        Feature clause, e.g. ``"in a Black Trenchcoat"``.
    """
    article = get_article(item_name)
    return f"in {article} {item_name}"


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

    Returns:
        Composed sdesc, e.g. ``"lanky man in a Black Trenchcoat"``
        or ``"compact woman"`` (no article prefix).
    """
    base = f"{descriptor} {keyword}"
    if feature:
        return f"{base} {feature}"
    return base


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


def get_apparent_gender(char: Any) -> str:
    """Return the grammar gender presented by a character's current look.

    Pronouns must follow the disguise: a character presenting as "a
    woman" should be referenced with feminine pronouns by observers
    who do not know the real identity, regardless of the underlying
    ``sex`` attribute.

    Derivation rule:

    1. If the character has an active ``keyword_override``, look it up
       in the runtime keyword catalog (KeywordManager script, falling
       back to the module-level default frozensets).

       * Match in the feminine list → ``"female"``
       * Match in the masculine list → ``"male"``
       * Match in the neutral list, **or no match anywhere** (custom
         ``@shortdesc`` keyword carrying no gender metadata) →
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


# =========================================================================
# Recognition Memory Migration
# =========================================================================


def _is_legacy_recognition_entry(uid: Any, entry: Any) -> bool:
    """Return True if a recognition entry pre-dates the engine PR schema.

    Legacy entries are keyed on real ``sleeve_uid`` (a 36-character
    UUID string) instead of on the new 16-character Apparent UID, or
    are missing the post-engine-PR ``lost_contact`` field.

    Args:
        uid: The dict key from ``recognition_memory``.
        entry: The corresponding value (usually a dict).

    Returns:
        ``True`` if the entry should be wiped.
    """
    if not isinstance(uid, str) or len(uid) != APPARENT_UID_HEX_LENGTH:
        return True
    if not isinstance(entry, dict):
        return True
    if "lost_contact" not in entry:
        return True
    return False


def wipe_legacy_recognition_memory(char: Any) -> int:
    """Wipe legacy recognition_memory entries on a single character.

    Idempotent shape-check: any entry whose key length does not match
    :data:`APPARENT_UID_HEX_LENGTH` or whose value lacks the
    ``lost_contact`` field is removed.  After the engine-PR
    deployment, all surviving entries pass the shape check and this
    function becomes a no-op for that character.

    The spec is explicit (see §"Memory Data Model" — *One-time wipe*)
    that there is no migration recompute — players rebuild recognition
    organically under the new keying.

    .. todo:: Remove this function and its caller after the engine-PR
       deployment is verified clean across all production characters.

    Args:
        char: The character whose ``recognition_memory`` is inspected.

    Returns:
        The number of entries wiped (``0`` if already clean).
    """
    memory = getattr(char, "recognition_memory", None)
    if not memory:
        return 0
    legacy_keys = [
        uid for uid, entry in memory.items()
        if _is_legacy_recognition_entry(uid, entry)
    ]
    if not legacy_keys:
        return 0
    new_memory = {
        uid: entry for uid, entry in memory.items() if uid not in legacy_keys
    }
    char.recognition_memory = new_memory
    logger.log_info(
        f"identity: wiped {len(legacy_keys)} legacy recognition_memory "
        f"entries on {getattr(char, 'key', '<unknown>')}"
    )
    return len(legacy_keys)


def wipe_all_legacy_recognition_memory() -> int:
    """Wipe legacy recognition_memory entries across all Character objects.

    Intended to be called once at server startup as a one-shot
    migration. Idempotent — safe to call repeatedly; subsequent calls
    are no-ops once all entries pass the shape check.

    .. todo:: Remove this function and its server-startup hook after
       the engine-PR deployment is verified clean across all
       production characters.

    Returns:
        Total number of entries wiped across all characters.
    """
    from typeclasses.characters import Character

    total = 0
    for char in Character.objects.all():
        try:
            total += wipe_legacy_recognition_memory(char)
        except Exception:
            logger.log_trace(
                f"identity: failed to wipe recognition_memory on "
                f"{getattr(char, 'key', '<unknown>')}"
            )
    return total
