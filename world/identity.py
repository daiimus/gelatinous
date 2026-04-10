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

from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger

from world.grammar import get_article

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
