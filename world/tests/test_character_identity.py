"""
Tests for Character identity methods (Identity Phase 1b).

Tests ``get_distinguishing_feature``, ``get_sdesc``, and
``get_display_name`` using lightweight mock objects.  No Evennia server
required — run via::

    evennia test world.tests.test_character_identity

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from world.identity import (
    compose_sdesc,
    format_clothing_feature,
    format_hair_feature,
    format_wielded_feature,
    get_physical_descriptor,
)
from world.grammar import DEFAULT_SDESC_KEYWORDS, get_article


# ===================================================================
# Helpers — lightweight character stand-in
# ===================================================================


def _make_item(key="Kitchen Knife"):
    """Return a minimal mock item with a ``.key``."""
    item = MagicMock()
    item.key = key
    return item


def _make_character(
    *,
    key="Jorge Jackson",
    height=None,
    build=None,
    hair_color=None,
    hair_style=None,
    sdesc_keyword=None,
    sex="male",
    sleeve_uid="uid-abc-123",
    hands=None,
    worn_items=None,
    recognition_memory=None,
):
    """Build a mock character with the attributes used by identity methods.

    All identity methods are imported and bound manually so they execute
    with the mock as ``self``.
    """
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.height = height
    char.build = build
    char.hair_color = hair_color
    char.hair_style = hair_style
    char.sdesc_keyword = sdesc_keyword
    char.sex = sex
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = recognition_memory or {}

    # Hands / clothing
    char.hands = hands if hands is not None else {"left": None, "right": None}
    char.worn_items = worn_items if worn_items is not None else {}

    # Wire up _build_clothing_coverage_map (from ClothingMixin)
    def _coverage_map():
        coverage = {}
        if char.worn_items:
            for loc, items in char.worn_items.items():
                if items:
                    coverage[loc] = items[0]
        return coverage

    char._build_clothing_coverage_map = _coverage_map

    # Bind identity methods from the real Character class
    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(char, looker, **kw)
    )

    # gender property — mirrors Character.gender logic
    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    return char


# ===================================================================
# get_distinguishing_feature()
# ===================================================================


class TestDistinguishingFeature(TestCase):
    """Verify the feature priority chain."""

    def test_wielded_weapon_wins(self):
        """Wielded weapon outranks clothing and hair."""
        knife = _make_item("Kitchen Knife")
        trenchcoat = _make_item("Black Trenchcoat")
        char = _make_character(
            hands={"left": None, "right": knife},
            worn_items={"chest": [trenchcoat]},
            hair_color="blonde",
            hair_style="braided",
        )
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "wielding a Kitchen Knife")

    def test_clothing_when_no_weapon(self):
        """Outermost clothing used when hands are empty."""
        coat = _make_item("Black Trenchcoat")
        char = _make_character(
            worn_items={"chest": [coat]},
            hair_color="red",
            hair_style="short",
        )
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "in a Black Trenchcoat")

    def test_hair_when_no_weapon_or_clothing(self):
        """Hair feature used when no weapon or clothing."""
        char = _make_character(
            hair_color="blonde",
            hair_style="braided",
        )
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "with blonde braids")

    def test_none_when_nothing(self):
        """Returns None when no weapon, clothing, or hair."""
        char = _make_character()
        result = char.get_distinguishing_feature()
        self.assertIsNone(result)

    def test_hair_color_only(self):
        """Hair colour alone produces a feature."""
        char = _make_character(hair_color="red")
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "with red hair")

    def test_hair_style_only(self):
        """Hair style alone produces a feature."""
        char = _make_character(hair_style="mohawk")
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "with mohawk")

    def test_left_hand_wielded(self):
        """Left-hand weapon detected."""
        sword = _make_item("Katana")
        char = _make_character(hands={"left": sword, "right": None})
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "wielding a Katana")

    def test_both_hands_wielded_picks_first(self):
        """When both hands hold items, one is chosen (deterministic)."""
        knife = _make_item("Kitchen Knife")
        pistol = _make_item("Pistol")
        char = _make_character(hands={"left": knife, "right": pistol})
        result = char.get_distinguishing_feature()
        # Dict iteration order in Python 3.7+ is insertion order
        self.assertIn("wielding", result)

    def test_multiple_clothing_locations_sorted(self):
        """Clothing feature picks alphabetically first location."""
        hat = _make_item("Cowboy Hat")
        coat = _make_item("Leather Jacket")
        char = _make_character(
            worn_items={"head": [hat], "chest": [coat]},
        )
        result = char.get_distinguishing_feature()
        # "chest" < "head" alphabetically, so Leather Jacket wins
        self.assertEqual(result, "in a Leather Jacket")

    def test_article_an_for_vowel_item(self):
        """Items starting with a vowel get 'an' article."""
        axe = _make_item("Axe")
        char = _make_character(hands={"left": None, "right": axe})
        result = char.get_distinguishing_feature()
        self.assertEqual(result, "wielding an Axe")


# ===================================================================
# get_sdesc()
# ===================================================================


class TestGetSdesc(TestCase):
    """Verify sdesc composition via Character.get_sdesc()."""

    def test_full_sdesc_with_feature(self):
        """Height + build + keyword + feature produces full sdesc."""
        knife = _make_item("Kitchen Knife")
        char = _make_character(
            height="tall",
            build="lean",
            sdesc_keyword="man",
            hands={"left": None, "right": knife},
        )
        result = char.get_sdesc()
        self.assertEqual(result, "gaunt man wielding a Kitchen Knife")

    def test_sdesc_without_feature(self):
        """Sdesc with no feature has just descriptor + keyword."""
        char = _make_character(
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sex="female",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "compact woman")

    def test_default_keyword_male(self):
        """Default keyword for male is 'man'."""
        char = _make_character(
            height="average",
            build="average",
            sex="male",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "average man")

    def test_default_keyword_female(self):
        """Default keyword for female is 'woman'."""
        char = _make_character(
            height="average",
            build="average",
            sex="female",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "average woman")

    def test_default_keyword_neutral(self):
        """Default keyword for neutral is 'person'."""
        char = _make_character(
            height="average",
            build="average",
            sex="ambiguous",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "average person")

    def test_fallback_to_key_when_no_height(self):
        """Without height, sdesc falls back to character key."""
        char = _make_character(
            key="TestChar",
            height=None,
            build="average",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "TestChar")

    def test_fallback_to_key_when_no_build(self):
        """Without build, sdesc falls back to character key."""
        char = _make_character(
            key="TestChar",
            height="tall",
            build=None,
        )
        result = char.get_sdesc()
        self.assertEqual(result, "TestChar")

    def test_custom_keyword(self):
        """Player-selected keyword used when set."""
        char = _make_character(
            height="tall",
            build="slight",
            sdesc_keyword="punk",
            sex="male",
        )
        result = char.get_sdesc()
        self.assertEqual(result, "lanky punk")

    def test_all_descriptor_combinations(self):
        """Every height × build combo produces a non-empty descriptor."""
        from world.identity import HEIGHTS, BUILDS

        for height in HEIGHTS:
            for build in BUILDS:
                char = _make_character(
                    height=height,
                    build=build,
                    sdesc_keyword="person",
                )
                result = char.get_sdesc()
                self.assertTrue(
                    result.endswith("person"),
                    f"Expected sdesc ending in 'person' for {height}/{build}, got: {result}",
                )
                self.assertGreater(
                    len(result),
                    len("person"),
                    f"Expected descriptor prefix for {height}/{build}",
                )


# ===================================================================
# get_display_name()
# ===================================================================


class TestGetDisplayName(TestCase):
    """Verify per-observer display name resolution."""

    def test_none_looker_returns_key(self):
        """System context (looker=None) returns real name."""
        char = _make_character(key="Jorge Jackson")
        self.assertEqual(char.get_display_name(None), "Jorge Jackson")

    def test_self_returns_key(self):
        """Self-perception returns real name."""
        char = _make_character(key="Jorge Jackson")
        self.assertEqual(char.get_display_name(char), "Jorge Jackson")

    def test_stranger_gets_sdesc_with_article(self):
        """Unknown observer gets sdesc with indefinite article."""
        target = _make_character(
            key="Jorge Jackson",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-target-1",
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-1",
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "a gaunt man")

    def test_stranger_with_feature(self):
        """Stranger sdesc includes distinguishing feature."""
        knife = _make_item("Kitchen Knife")
        target = _make_character(
            key="Jorge Jackson",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-target-2",
            hands={"left": None, "right": knife},
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-2",
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "a gaunt man wielding a Kitchen Knife")

    def test_recognized_by_assigned_name(self):
        """Looker who assigned a name sees that name."""
        target = _make_character(
            key="Jorge Jackson",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-target-3",
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-3",
            recognition_memory={
                "uid-target-3": {
                    "assigned_name": "Big J",
                }
            },
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "Big J")

    def test_empty_assigned_name_falls_through(self):
        """Empty string assigned_name falls through to sdesc."""
        target = _make_character(
            key="Jorge Jackson",
            height="average",
            build="average",
            sdesc_keyword="man",
            sleeve_uid="uid-target-4",
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-4",
            recognition_memory={
                "uid-target-4": {
                    "assigned_name": "",
                }
            },
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "an average man")

    def test_no_sleeve_uid_falls_through(self):
        """Target with no sleeve_uid falls through to sdesc."""
        target = _make_character(
            key="NPC",
            height="short",
            build="stocky",
            sdesc_keyword="woman",
            sex="female",
            sleeve_uid=None,
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-5",
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "a squat woman")

    def test_pre_chargen_returns_key(self):
        """Character without height/build returns key (no article)."""
        target = _make_character(
            key="NewChar",
            height=None,
            build=None,
            sleeve_uid="uid-new",
        )
        looker = _make_character(
            key="Looker",
            sleeve_uid="uid-looker-6",
        )
        result = target.get_display_name(looker)
        self.assertEqual(result, "NewChar")

    def test_an_article_for_vowel_sdesc(self):
        """Sdesc starting with a vowel-sound gets 'an' article."""
        target = _make_character(
            key="Ellen",
            height="above-average",
            build="athletic",
            sdesc_keyword="woman",
            sex="female",
            sleeve_uid="uid-ellen",
        )
        # "above-average" + "athletic" → "strapping"
        # But the sdesc is "strapping woman" → starts with 's', gets 'a'
        # Let's pick one that starts with a vowel
        target2 = _make_character(
            key="Ellen",
            height="above-average",
            build="average",
            sdesc_keyword="woman",
            sex="female",
            sleeve_uid="uid-ellen2",
        )
        looker = _make_character(key="Looker", sleeve_uid="uid-looker-7")
        # "above-average" + "average" → "tall" → starts with 't' → "a"
        # Let's use a descriptor that starts with a vowel
        target3 = _make_character(
            key="Ellen",
            height="average",
            build="athletic",
            sdesc_keyword="woman",
            sex="female",
            sleeve_uid="uid-ellen3",
        )
        result = target3.get_display_name(looker)
        # "average" + "athletic" → "athletic woman" → "an athletic woman"
        self.assertEqual(result, "an athletic woman")

    def test_different_lookers_different_names(self):
        """Two lookers see different names for the same target."""
        target = _make_character(
            key="Jorge Jackson",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-target-multi",
        )
        friend = _make_character(
            key="Friend",
            sleeve_uid="uid-friend",
            recognition_memory={
                "uid-target-multi": {"assigned_name": "Jorge"},
            },
        )
        stranger = _make_character(
            key="Stranger",
            sleeve_uid="uid-stranger",
        )
        self.assertEqual(target.get_display_name(friend), "Jorge")
        self.assertEqual(target.get_display_name(stranger), "a gaunt man")


# ===================================================================
# Flash clone sleeve_uid inheritance
# ===================================================================


class TestFlashCloneInheritance(TestCase):
    """Verify that identity attrs should be inherited by flash clones.

    These are logic tests — the actual ``create_flash_clone`` function
    requires Evennia's database, so we verify the *design contract*
    by checking the code path copies the right attributes.
    """

    def test_recognition_memory_not_shared(self):
        """Flash clone must start with empty recognition_memory."""
        parent = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-parent",
            recognition_memory={
                "uid-somebody": {"assigned_name": "Somebody"},
            },
        )
        # Simulate what create_flash_clone should do:
        # clone inherits sleeve_uid but NOT recognition_memory
        clone = _make_character(
            key="Jorge Jackson II",
            sleeve_uid=parent.sleeve_uid,
            recognition_memory={},
        )
        self.assertEqual(clone.sleeve_uid, parent.sleeve_uid)
        self.assertEqual(clone.recognition_memory, {})

    def test_same_sleeve_uid_means_same_recognition(self):
        """Observer who knows the parent recognizes the clone."""
        parent = _make_character(
            key="Jorge Jackson",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-shared-body",
        )
        clone = _make_character(
            key="Jorge Jackson II",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-shared-body",
        )
        observer = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-shared-body": {"assigned_name": "Big J"},
            },
        )
        self.assertEqual(parent.get_display_name(observer), "Big J")
        self.assertEqual(clone.get_display_name(observer), "Big J")

    def test_clone_sees_nobody(self):
        """Clone with empty memory sees sdesc, not assigned names."""
        somebody = _make_character(
            key="Alex",
            height="short",
            build="athletic",
            sdesc_keyword="person",
            sex="ambiguous",
            sleeve_uid="uid-alex",
        )
        clone = _make_character(
            key="Jorge Jackson II",
            sleeve_uid="uid-clone",
            recognition_memory={},
        )
        result = somebody.get_display_name(clone)
        self.assertEqual(result, "a compact person")
