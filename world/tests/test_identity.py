"""
Tests for Identity Constants and Sdesc Composition (``world/identity.py``).

Pure unit tests with no Evennia dependencies.  Run via::

    evennia test world.tests.test_identity

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.exceptions import ObjectDoesNotExist

from world.identity import (
    BUILDS,
    HAIR_COLORS,
    HAIR_STYLES,
    HEIGHTS,
    PHYSICAL_DESCRIPTOR_TABLE,
    _DEFAULT_FEMININE_KEYWORDS,
    _DEFAULT_MASCULINE_KEYWORDS,
    _DEFAULT_NEUTRAL_KEYWORDS,
    compose_sdesc,
    format_clothing_feature,
    format_hair_feature,
    format_wielded_feature,
    get_feminine_keywords,
    get_masculine_keywords,
    get_neutral_keywords,
    get_physical_descriptor,
    get_valid_keywords,
    is_valid_keyword,
    validate_custom_keyword,
)


# ===================================================================
# Physical Descriptor Table
# ===================================================================


class TestPhysicalDescriptorTable(TestCase):
    """Verify the 5×6 descriptor table matches the spec."""

    def test_table_has_all_heights(self) -> None:
        for height in HEIGHTS:
            self.assertIn(height, PHYSICAL_DESCRIPTOR_TABLE)

    def test_each_height_has_all_builds(self) -> None:
        for height in HEIGHTS:
            for build in BUILDS:
                self.assertIn(
                    build,
                    PHYSICAL_DESCRIPTOR_TABLE[height],
                    f"Missing build {build!r} for height {height!r}",
                )

    def test_total_cells(self) -> None:
        """5 heights × 6 builds = 30 cells."""
        count = sum(
            len(builds)
            for builds in PHYSICAL_DESCRIPTOR_TABLE.values()
        )
        self.assertEqual(count, 30)

    def test_all_descriptors_are_non_empty_strings(self) -> None:
        for height in HEIGHTS:
            for build in BUILDS:
                desc = PHYSICAL_DESCRIPTOR_TABLE[height][build]
                self.assertIsInstance(desc, str)
                self.assertTrue(len(desc) > 0)

    # -- Spot-check specific cells from the spec table --

    def test_short_slight(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "slight"), "diminutive")

    def test_short_lean(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "lean"), "wiry")

    def test_short_athletic(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "athletic"), "compact")

    def test_short_average(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "average"), "short")

    def test_short_stocky(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "stocky"), "squat")

    def test_short_heavyset(self) -> None:
        self.assertEqual(get_physical_descriptor("short", "heavyset"), "rotund")

    def test_below_average_slight(self) -> None:
        self.assertEqual(
            get_physical_descriptor("below-average", "slight"), "slight"
        )

    def test_below_average_lean(self) -> None:
        self.assertEqual(
            get_physical_descriptor("below-average", "lean"), "lithe"
        )

    def test_below_average_athletic(self) -> None:
        self.assertEqual(
            get_physical_descriptor("below-average", "athletic"), "spry"
        )

    def test_average_average(self) -> None:
        self.assertEqual(
            get_physical_descriptor("average", "average"), "average"
        )

    def test_average_athletic(self) -> None:
        self.assertEqual(
            get_physical_descriptor("average", "athletic"), "athletic"
        )

    def test_average_slight(self) -> None:
        self.assertEqual(
            get_physical_descriptor("average", "slight"), "slender"
        )

    def test_above_average_lean(self) -> None:
        self.assertEqual(
            get_physical_descriptor("above-average", "lean"), "rangy"
        )

    def test_above_average_athletic(self) -> None:
        self.assertEqual(
            get_physical_descriptor("above-average", "athletic"), "strapping"
        )

    def test_above_average_stocky(self) -> None:
        self.assertEqual(
            get_physical_descriptor("above-average", "stocky"), "brawny"
        )

    def test_above_average_heavyset(self) -> None:
        self.assertEqual(
            get_physical_descriptor("above-average", "heavyset"), "hulking"
        )

    def test_tall_slight(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "slight"), "lanky")

    def test_tall_lean(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "lean"), "gaunt")

    def test_tall_athletic(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "athletic"), "towering")

    def test_tall_average(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "average"), "tall")

    def test_tall_stocky(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "stocky"), "burly")

    def test_tall_heavyset(self) -> None:
        self.assertEqual(get_physical_descriptor("tall", "heavyset"), "massive")

    # -- Error cases --

    def test_invalid_height_raises_key_error(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            get_physical_descriptor("giant", "lean")
        self.assertIn("giant", str(ctx.exception))

    def test_invalid_build_raises_key_error(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            get_physical_descriptor("tall", "muscular")
        self.assertIn("muscular", str(ctx.exception))


# ===================================================================
# Keyword Lists
# ===================================================================


class TestKeywordLists(TestCase):
    """Verify default keyword sets match the spec."""

    def test_feminine_count(self) -> None:
        self.assertEqual(len(_DEFAULT_FEMININE_KEYWORDS), 24)

    def test_masculine_count(self) -> None:
        self.assertEqual(len(_DEFAULT_MASCULINE_KEYWORDS), 23)

    def test_neutral_count(self) -> None:
        self.assertEqual(len(_DEFAULT_NEUTRAL_KEYWORDS), 24)

    def test_all_keywords_is_union(self) -> None:
        all_kws = (
            _DEFAULT_FEMININE_KEYWORDS
            | _DEFAULT_MASCULINE_KEYWORDS
            | _DEFAULT_NEUTRAL_KEYWORDS
        )
        self.assertEqual(
            all_kws,
            _DEFAULT_FEMININE_KEYWORDS
            | _DEFAULT_MASCULINE_KEYWORDS
            | _DEFAULT_NEUTRAL_KEYWORDS,
        )

    def test_no_overlap_feminine_masculine(self) -> None:
        """Feminine and masculine sets should not share keywords."""
        overlap = _DEFAULT_FEMININE_KEYWORDS & _DEFAULT_MASCULINE_KEYWORDS
        self.assertEqual(overlap, set(), f"Unexpected overlap: {overlap}")

    def test_no_overlap_gendered_neutral(self) -> None:
        """Neutral should not overlap with gendered sets."""
        overlap_f = _DEFAULT_FEMININE_KEYWORDS & _DEFAULT_NEUTRAL_KEYWORDS
        overlap_m = _DEFAULT_MASCULINE_KEYWORDS & _DEFAULT_NEUTRAL_KEYWORDS
        self.assertEqual(overlap_f, set(), f"Feminine-neutral overlap: {overlap_f}")
        self.assertEqual(overlap_m, set(), f"Masculine-neutral overlap: {overlap_m}")

    # -- Spot-check representative keywords --

    def test_woman_in_feminine(self) -> None:
        self.assertIn("woman", _DEFAULT_FEMININE_KEYWORDS)

    def test_man_in_masculine(self) -> None:
        self.assertIn("man", _DEFAULT_MASCULINE_KEYWORDS)

    def test_person_in_neutral(self) -> None:
        self.assertIn("person", _DEFAULT_NEUTRAL_KEYWORDS)

    def test_droog_in_masculine(self) -> None:
        self.assertIn("droog", _DEFAULT_MASCULINE_KEYWORDS)

    def test_devotchka_in_feminine(self) -> None:
        self.assertIn("devotchka", _DEFAULT_FEMININE_KEYWORDS)

    def test_androog_in_neutral(self) -> None:
        self.assertIn("androog", _DEFAULT_NEUTRAL_KEYWORDS)

    def test_all_keywords_lowercase(self) -> None:
        all_kws = (
            _DEFAULT_FEMININE_KEYWORDS
            | _DEFAULT_MASCULINE_KEYWORDS
            | _DEFAULT_NEUTRAL_KEYWORDS
        )
        for kw in all_kws:
            self.assertEqual(kw, kw.lower(), f"Keyword not lowercase: {kw!r}")


class TestGetValidKeywords(TestCase):
    """Tests for ``get_valid_keywords`` and ``is_valid_keyword``.

    The getter functions read from the live ``KeywordManager`` script
    when one exists.  We patch ``_get_keyword_manager`` to raise
    ``ObjectDoesNotExist`` (the expected missing-script path) so the
    getters fall back to code-level ``_DEFAULT_*`` frozensets, keeping
    these routing tests independent of live DB state.
    """

    def setUp(self) -> None:
        patcher = patch(
            "world.identity._get_keyword_manager",
            side_effect=ObjectDoesNotExist,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_male_gets_masculine_and_neutral(self) -> None:
        result = get_valid_keywords("male")
        self.assertEqual(
            result,
            _DEFAULT_MASCULINE_KEYWORDS | _DEFAULT_NEUTRAL_KEYWORDS,
        )

    def test_female_gets_feminine_and_neutral(self) -> None:
        result = get_valid_keywords("female")
        self.assertEqual(
            result,
            _DEFAULT_FEMININE_KEYWORDS | _DEFAULT_NEUTRAL_KEYWORDS,
        )

    def test_neutral_gets_all(self) -> None:
        result = get_valid_keywords("neutral")
        all_defaults = (
            _DEFAULT_FEMININE_KEYWORDS
            | _DEFAULT_MASCULINE_KEYWORDS
            | _DEFAULT_NEUTRAL_KEYWORDS
        )
        self.assertEqual(result, all_defaults)

    def test_unknown_gender_gets_all(self) -> None:
        """Unknown gender should be permissive, not restrictive."""
        result = get_valid_keywords("other")
        all_defaults = (
            _DEFAULT_FEMININE_KEYWORDS
            | _DEFAULT_MASCULINE_KEYWORDS
            | _DEFAULT_NEUTRAL_KEYWORDS
        )
        self.assertEqual(result, all_defaults)

    def test_man_valid_for_male(self) -> None:
        self.assertTrue(is_valid_keyword("man", "male"))

    def test_woman_invalid_for_male(self) -> None:
        self.assertFalse(is_valid_keyword("woman", "male"))

    def test_person_valid_for_all_genders(self) -> None:
        for gender in ("male", "female", "neutral"):
            self.assertTrue(
                is_valid_keyword("person", gender),
                f"'person' should be valid for {gender}",
            )

    def test_case_insensitive_validation(self) -> None:
        self.assertTrue(is_valid_keyword("Man", "male"))
        self.assertTrue(is_valid_keyword("WOMAN", "female"))


# ===================================================================
# Keyword Getter Fallback Behaviour
# ===================================================================


class TestKeywordGetterFallback(TestCase):
    """Verify that keyword getters handle all script states correctly.

    Each getter has three code paths:

    1. Script exists and has keywords → return the script's data.
    2. ``ObjectDoesNotExist`` → silent fallback to ``_DEFAULT_*``.
    3. Unexpected error → ``log_trace`` + fallback to ``_DEFAULT_*``.

    A fourth edge case (script exists but ``db`` attribute is ``None``)
    also falls back to defaults without logging.
    """

    # -- Happy path: script provides keywords --------------------------

    def test_feminine_returns_script_keywords(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.feminine_keywords = {"queen", "duchess"}
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            result = get_feminine_keywords()
        self.assertEqual(result, frozenset({"queen", "duchess"}))

    def test_masculine_returns_script_keywords(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.masculine_keywords = {"king", "duke"}
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            result = get_masculine_keywords()
        self.assertEqual(result, frozenset({"king", "duke"}))

    def test_neutral_returns_script_keywords(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.neutral_keywords = {"citizen", "clone"}
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            result = get_neutral_keywords()
        self.assertEqual(result, frozenset({"citizen", "clone"}))

    # -- Missing script: silent fallback to defaults -------------------

    def test_feminine_falls_back_when_script_missing(self) -> None:
        with patch(
            "world.identity._get_keyword_manager",
            side_effect=ObjectDoesNotExist,
        ):
            self.assertEqual(get_feminine_keywords(), _DEFAULT_FEMININE_KEYWORDS)

    def test_masculine_falls_back_when_script_missing(self) -> None:
        with patch(
            "world.identity._get_keyword_manager",
            side_effect=ObjectDoesNotExist,
        ):
            self.assertEqual(get_masculine_keywords(), _DEFAULT_MASCULINE_KEYWORDS)

    def test_neutral_falls_back_when_script_missing(self) -> None:
        with patch(
            "world.identity._get_keyword_manager",
            side_effect=ObjectDoesNotExist,
        ):
            self.assertEqual(get_neutral_keywords(), _DEFAULT_NEUTRAL_KEYWORDS)

    # -- Unexpected error: log + fallback ------------------------------

    def test_feminine_logs_and_falls_back_on_unexpected_error(self) -> None:
        with (
            patch(
                "world.identity._get_keyword_manager",
                side_effect=RuntimeError("connection lost"),
            ),
            patch("world.identity.logger") as mock_logger,
        ):
            result = get_feminine_keywords()
        self.assertEqual(result, _DEFAULT_FEMININE_KEYWORDS)
        mock_logger.log_trace.assert_called_once()

    def test_masculine_logs_and_falls_back_on_unexpected_error(self) -> None:
        with (
            patch(
                "world.identity._get_keyword_manager",
                side_effect=RuntimeError("connection lost"),
            ),
            patch("world.identity.logger") as mock_logger,
        ):
            result = get_masculine_keywords()
        self.assertEqual(result, _DEFAULT_MASCULINE_KEYWORDS)
        mock_logger.log_trace.assert_called_once()

    def test_neutral_logs_and_falls_back_on_unexpected_error(self) -> None:
        with (
            patch(
                "world.identity._get_keyword_manager",
                side_effect=RuntimeError("connection lost"),
            ),
            patch("world.identity.logger") as mock_logger,
        ):
            result = get_neutral_keywords()
        self.assertEqual(result, _DEFAULT_NEUTRAL_KEYWORDS)
        mock_logger.log_trace.assert_called_once()

    # -- None attribute: fallback without logging ----------------------

    def test_feminine_falls_back_when_attribute_is_none(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.feminine_keywords = None
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            self.assertEqual(get_feminine_keywords(), _DEFAULT_FEMININE_KEYWORDS)

    def test_masculine_falls_back_when_attribute_is_none(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.masculine_keywords = None
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            self.assertEqual(get_masculine_keywords(), _DEFAULT_MASCULINE_KEYWORDS)

    def test_neutral_falls_back_when_attribute_is_none(self) -> None:
        mock_mgr = MagicMock()
        mock_mgr.db.neutral_keywords = None
        with patch("world.identity._get_keyword_manager", return_value=mock_mgr):
            self.assertEqual(get_neutral_keywords(), _DEFAULT_NEUTRAL_KEYWORDS)

    # -- Missing-script path does NOT log ------------------------------

    def test_missing_script_does_not_log(self) -> None:
        """ObjectDoesNotExist is expected — should not produce a log entry."""
        with (
            patch(
                "world.identity._get_keyword_manager",
                side_effect=ObjectDoesNotExist,
            ),
            patch("world.identity.logger") as mock_logger,
        ):
            get_feminine_keywords()
            get_masculine_keywords()
            get_neutral_keywords()
        mock_logger.log_trace.assert_not_called()


# ===================================================================
# Hair Options
# ===================================================================


class TestHairOptions(TestCase):
    """Verify hair colour and style constants."""

    def test_hair_colors_not_empty(self) -> None:
        self.assertGreater(len(HAIR_COLORS), 0)

    def test_hair_styles_not_empty(self) -> None:
        self.assertGreater(len(HAIR_STYLES), 0)

    def test_standard_colors_present(self) -> None:
        for color in ("red", "black", "blonde", "brown", "white"):
            self.assertIn(color, HAIR_COLORS)

    def test_standard_styles_present(self) -> None:
        for style in ("cropped", "long", "braided", "mohawk"):
            self.assertIn(style, HAIR_STYLES)

    def test_all_colors_lowercase(self) -> None:
        for color in HAIR_COLORS:
            self.assertEqual(color, color.lower())

    def test_all_styles_lowercase(self) -> None:
        for style in HAIR_STYLES:
            self.assertEqual(style, style.lower())


# ===================================================================
# Distinguishing Feature Formatters
# ===================================================================


class TestFormatWieldedFeature(TestCase):
    """Tests for ``format_wielded_feature``."""

    def test_basic_weapon(self) -> None:
        self.assertEqual(
            format_wielded_feature("Kitchen Knife"),
            "wielding a Kitchen Knife",
        )

    def test_article_an(self) -> None:
        self.assertEqual(
            format_wielded_feature("Assault Rifle"),
            "wielding an Assault Rifle",
        )


class TestFormatClothingFeature(TestCase):
    """Tests for ``format_clothing_feature``."""

    def test_basic_clothing(self) -> None:
        self.assertEqual(
            format_clothing_feature("Black Trenchcoat"),
            "in a Black Trenchcoat",
        )

    def test_article_an(self) -> None:
        self.assertEqual(
            format_clothing_feature("Orange Jumpsuit"),
            "in an Orange Jumpsuit",
        )


class TestFormatHairFeature(TestCase):
    """Tests for ``format_hair_feature``."""

    # -- Both colour and style --

    def test_color_and_noun_style(self) -> None:
        """Styles that read as nouns: 'with blonde braids'."""
        self.assertEqual(
            format_hair_feature("blonde", "braided"),
            "with blonde braids",
        )

    def test_color_and_noun_style_dreaded(self) -> None:
        self.assertEqual(
            format_hair_feature("red", "dreaded"),
            "with red dreadlocks",
        )

    def test_color_and_noun_style_mohawk(self) -> None:
        self.assertEqual(
            format_hair_feature("green", "mohawk"),
            "with green mohawk",
        )

    def test_color_and_noun_style_curly(self) -> None:
        self.assertEqual(
            format_hair_feature("black", "curly"),
            "with black curls",
        )

    def test_color_and_adjective_style(self) -> None:
        """Styles that need 'hair': 'with cropped white hair'."""
        self.assertEqual(
            format_hair_feature("white", "cropped"),
            "with cropped white hair",
        )

    def test_color_and_adjective_style_long(self) -> None:
        self.assertEqual(
            format_hair_feature("black", "long"),
            "with long black hair",
        )

    def test_color_and_adjective_style_slicked(self) -> None:
        self.assertEqual(
            format_hair_feature("silver", "slicked"),
            "with slicked silver hair",
        )

    def test_color_and_adjective_style_straight(self) -> None:
        self.assertEqual(
            format_hair_feature("auburn", "straight"),
            "with straight auburn hair",
        )

    # -- Colour only --

    def test_color_only(self) -> None:
        self.assertEqual(
            format_hair_feature("red"),
            "with red hair",
        )

    def test_color_only_explicit_none_style(self) -> None:
        self.assertEqual(
            format_hair_feature("blonde", None),
            "with blonde hair",
        )

    # -- Style only --

    def test_noun_style_only(self) -> None:
        self.assertEqual(
            format_hair_feature(style="braided"),
            "with braids",
        )

    def test_noun_style_only_ponytail(self) -> None:
        self.assertEqual(
            format_hair_feature(style="ponytail"),
            "with ponytail",
        )

    def test_adjective_style_only(self) -> None:
        self.assertEqual(
            format_hair_feature(style="cropped"),
            "with cropped hair",
        )

    def test_adjective_style_only_matted(self) -> None:
        self.assertEqual(
            format_hair_feature(style="matted"),
            "with matted hair",
        )

    # -- No hair (bald) --

    def test_no_color_no_style_returns_none(self) -> None:
        self.assertIsNone(format_hair_feature())

    def test_explicit_nones_returns_none(self) -> None:
        self.assertIsNone(format_hair_feature(None, None))

    def test_empty_strings_returns_none(self) -> None:
        self.assertIsNone(format_hair_feature("", ""))


# ===================================================================
# Sdesc Composition
# ===================================================================


class TestComposeSdesc(TestCase):
    """Tests for ``compose_sdesc``."""

    def test_descriptor_and_keyword_only(self) -> None:
        self.assertEqual(compose_sdesc("lanky", "man"), "lanky man")

    def test_with_clothing_feature(self) -> None:
        self.assertEqual(
            compose_sdesc("lanky", "man", "in a Black Trenchcoat"),
            "lanky man in a Black Trenchcoat",
        )

    def test_with_wielded_feature(self) -> None:
        self.assertEqual(
            compose_sdesc("compact", "woman", "wielding a Kitchen Knife"),
            "compact woman wielding a Kitchen Knife",
        )

    def test_with_hair_feature(self) -> None:
        self.assertEqual(
            compose_sdesc("athletic", "dame", "with blonde braids"),
            "athletic dame with blonde braids",
        )

    def test_none_feature_ignored(self) -> None:
        self.assertEqual(compose_sdesc("gaunt", "droog", None), "gaunt droog")

    def test_empty_feature_ignored(self) -> None:
        self.assertEqual(compose_sdesc("gaunt", "droog", ""), "gaunt droog")

    # -- Disguise adjective param --

    def test_disguise_adjective_injected_between_descriptor_and_keyword(
        self,
    ) -> None:
        self.assertEqual(
            compose_sdesc(
                "lanky", "man", disguise_adjective="masked"
            ),
            "lanky masked man",
        )

    def test_disguise_adjective_with_feature(self) -> None:
        self.assertEqual(
            compose_sdesc(
                "lanky",
                "man",
                "in a Black Trenchcoat",
                disguise_adjective="masked",
            ),
            "lanky masked man in a Black Trenchcoat",
        )

    def test_none_adjective_unchanged(self) -> None:
        """``None`` adjective preserves the three-arg shape exactly."""
        self.assertEqual(
            compose_sdesc("lanky", "man", "in a Black Trenchcoat", None),
            "lanky man in a Black Trenchcoat",
        )

    def test_empty_adjective_unchanged(self) -> None:
        self.assertEqual(
            compose_sdesc("lanky", "man", disguise_adjective=""),
            "lanky man",
        )

    # -- End-to-end integration: descriptor lookup → compose --

    def test_end_to_end_from_table(self) -> None:
        """Full pipeline: height/build → descriptor → compose."""
        desc = get_physical_descriptor("tall", "slight")
        sdesc = compose_sdesc(desc, "man", "in a Black Trenchcoat")
        self.assertEqual(sdesc, "lanky man in a Black Trenchcoat")

    def test_end_to_end_with_hair(self) -> None:
        desc = get_physical_descriptor("short", "athletic")
        feature = format_hair_feature("blonde", "braided")
        sdesc = compose_sdesc(desc, "woman", feature)
        self.assertEqual(sdesc, "compact woman with blonde braids")

    def test_end_to_end_with_weapon(self) -> None:
        desc = get_physical_descriptor("average", "average")
        feature = format_wielded_feature("Kitchen Knife")
        sdesc = compose_sdesc(desc, "person", feature)
        self.assertEqual(sdesc, "average person wielding a Kitchen Knife")

    def test_end_to_end_no_feature(self) -> None:
        desc = get_physical_descriptor("above-average", "heavyset")
        sdesc = compose_sdesc(desc, "kid")
        self.assertEqual(sdesc, "hulking kid")


# ===================================================================
# Custom Keyword Validation
# ===================================================================


class TestValidateCustomKeyword(TestCase):
    """Tests for :func:`validate_custom_keyword`."""

    def test_valid_simple(self) -> None:
        valid, reason = validate_custom_keyword("ronin")
        self.assertTrue(valid)
        self.assertEqual(reason, "")

    def test_valid_min_length(self) -> None:
        valid, _ = validate_custom_keyword("ab")
        self.assertTrue(valid)

    def test_valid_max_length(self) -> None:
        valid, _ = validate_custom_keyword("a" * 20)
        self.assertTrue(valid)

    def test_reject_single_char(self) -> None:
        valid, reason = validate_custom_keyword("x")
        self.assertFalse(valid)
        self.assertIn("at least", reason)

    def test_reject_too_long(self) -> None:
        valid, reason = validate_custom_keyword("a" * 21)
        self.assertFalse(valid)
        self.assertIn("at most", reason)

    def test_reject_digits(self) -> None:
        valid, reason = validate_custom_keyword("cyber2")
        self.assertFalse(valid)
        self.assertIn("letters", reason)

    def test_reject_hyphen(self) -> None:
        valid, reason = validate_custom_keyword("half-elf")
        self.assertFalse(valid)
        self.assertIn("letters", reason)

    def test_reject_space(self) -> None:
        """Spaces should already be stripped by the caller, but test anyway."""
        valid, reason = validate_custom_keyword("no way")
        self.assertFalse(valid)
        self.assertIn("letters", reason)

    def test_reject_empty(self) -> None:
        valid, reason = validate_custom_keyword("")
        self.assertFalse(valid)


# =====================================================================
# Disguise engine: signature, Apparent UID, gender derivation, wipe
# =====================================================================


class _SignatureMockCharacter:
    """Minimal stand-in for a Character used by signature/UID tests.

    Avoids ``MagicMock`` because its auto-attribute behaviour silently
    produces non-``None`` ``db.*_override`` values that poison the
    signature.  This explicit class makes the unset state obvious and
    makes the tests fail loudly when a new signature input is added.
    """

    def __init__(
        self,
        sleeve_uid: str | None = "uid-jorge",
        height_override: str | None = None,
        build_override: str | None = None,
        keyword_override: str | None = None,
        sex: str = "male",
        gender: str | None = None,
        worn_items: list | None = None,
    ) -> None:
        self.sleeve_uid = sleeve_uid
        self.sex = sex
        self.gender = gender

        class _DB:
            pass

        self.db = _DB()
        self.db.height_override = height_override
        self.db.build_override = build_override
        self.db.keyword_override = keyword_override

        self.recognition_memory: dict = {}
        self.key = "Jorge"
        self._worn_items = worn_items or []

    def get_worn_items(self, location: str | None = None) -> list:
        """Mirror :meth:`ClothingMixin.get_worn_items` for signature tests."""
        return list(self._worn_items)


class _FakeDisguiseItem:
    """Lightweight stand-in for ``typeclasses.items.Item`` in signature tests.

    Mirrors the duck-typed surface read by the engine helpers:
    ``disguise_essential`` / ``disguise_type_id`` (signature),
    ``is_disguise_item`` / ``disguise_adjective`` (sdesc adjective),
    ``worn_sdesc_short`` / ``covers_hair`` / ``key`` (distinguishing
    feature).
    """

    def __init__(
        self,
        *,
        disguise_essential: bool = False,
        disguise_type_id: str = "",
        is_disguise_item: bool = False,
        disguise_adjective: str = "",
        worn_sdesc_short: str = "",
        covers_hair: bool = False,
        key: str = "fake item",
    ) -> None:
        self.disguise_essential = disguise_essential
        self.disguise_type_id = disguise_type_id
        self.is_disguise_item = is_disguise_item
        self.disguise_adjective = disguise_adjective
        self.worn_sdesc_short = worn_sdesc_short
        self.covers_hair = covers_hair
        self.key = key

    def __repr__(self) -> str:
        return f"<_FakeDisguiseItem key={self.key!r}>"


class TestGetEssentialItemTypeIds(TestCase):
    """Essential disguise items contribute their type IDs to the signature."""

    def test_no_worn_items_yields_empty_tuple(self) -> None:
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter()
        self.assertEqual(get_essential_item_type_ids(char), ())

    def test_non_essential_items_are_ignored(self) -> None:
        """A worn item without ``disguise_essential`` contributes nothing."""
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=False, disguise_type_id="balaclava"
                ),
            ]
        )
        self.assertEqual(get_essential_item_type_ids(char), ())

    def test_essential_item_contributes_type_id(self) -> None:
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
            ]
        )
        self.assertEqual(get_essential_item_type_ids(char), ("balaclava",))

    def test_duplicate_type_ids_collapse(self) -> None:
        """Two balaclavas → one signature contribution (set semantics)."""
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
            ]
        )
        self.assertEqual(get_essential_item_type_ids(char), ("balaclava",))

    def test_multiple_distinct_types_are_sorted(self) -> None:
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="wig"
                ),
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="mask_full"
                ),
            ]
        )
        self.assertEqual(
            get_essential_item_type_ids(char),
            ("balaclava", "mask_full", "wig"),
        )

    def test_essential_with_empty_type_id_is_skipped_and_warns(self) -> None:
        """Authoring slip: essential flag set but no type_id → warn + skip."""
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id=""
                ),
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="wig"
                ),
            ]
        )
        with patch("world.identity.logger.log_warn") as mock_warn:
            result = get_essential_item_type_ids(char)
        self.assertEqual(result, ("wig",))
        mock_warn.assert_called_once()

    def test_character_without_get_worn_items_yields_empty_tuple(self) -> None:
        """NPCs that cannot wear clothing must not crash signature derivation."""
        from world.identity import get_essential_item_type_ids

        class _BareChar:
            pass

        self.assertEqual(get_essential_item_type_ids(_BareChar()), ())


class TestEssentialItemsAffectSignatureAndUid(TestCase):
    """Integration: equipping essential items shifts signature + Apparent UID."""

    def test_essential_item_appears_in_signature_tuple(self) -> None:
        from world.identity import get_identity_signature

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
            ]
        )
        sig = get_identity_signature(char)
        self.assertEqual(sig[4], ("balaclava",))

    def test_essential_item_changes_apparent_uid(self) -> None:
        from world.identity import get_apparent_uid

        bare = get_apparent_uid(_SignatureMockCharacter())
        disguised = get_apparent_uid(
            _SignatureMockCharacter(
                worn_items=[
                    _FakeDisguiseItem(
                        disguise_essential=True, disguise_type_id="balaclava"
                    ),
                ]
            )
        )
        self.assertNotEqual(bare, disguised)

    def test_two_balaclavas_hash_identically(self) -> None:
        """Swapping one balaclava for another must not shift the UID."""
        from world.identity import get_apparent_uid

        a = get_apparent_uid(
            _SignatureMockCharacter(
                worn_items=[
                    _FakeDisguiseItem(
                        disguise_essential=True, disguise_type_id="balaclava"
                    ),
                ]
            )
        )
        b = get_apparent_uid(
            _SignatureMockCharacter(
                worn_items=[
                    _FakeDisguiseItem(
                        disguise_essential=True, disguise_type_id="balaclava"
                    ),
                ]
            )
        )
        self.assertEqual(a, b)

    def test_different_essential_types_produce_different_uids(self) -> None:
        from world.identity import get_apparent_uid

        balaclava_uid = get_apparent_uid(
            _SignatureMockCharacter(
                worn_items=[
                    _FakeDisguiseItem(
                        disguise_essential=True, disguise_type_id="balaclava"
                    ),
                ]
            )
        )
        wig_uid = get_apparent_uid(
            _SignatureMockCharacter(
                worn_items=[
                    _FakeDisguiseItem(
                        disguise_essential=True, disguise_type_id="wig"
                    ),
                ]
            )
        )
        self.assertNotEqual(balaclava_uid, wig_uid)


class TestGetDisguiseAdjective(TestCase):
    """``get_disguise_adjective`` resolves the most-prominent worn adjective."""

    def test_no_worn_items_yields_none(self) -> None:
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter()
        self.assertIsNone(get_disguise_adjective(char))

    def test_character_without_get_worn_items_yields_none(self) -> None:
        """Defensive: NPCs/mocks lacking the wear API simply opt out."""
        from world.identity import get_disguise_adjective

        class _Bare:
            pass

        self.assertIsNone(get_disguise_adjective(_Bare()))

    def test_single_disguise_item_returns_its_adjective(self) -> None:
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="masked",
                    key="black balaclava",
                )
            ]
        )
        self.assertEqual(get_disguise_adjective(char), "masked")

    def test_priority_table_lowest_rank_wins(self) -> None:
        """``masked`` (rank 1) outranks ``hooded`` (rank 4)."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="hooded",
                    key="grey hood",
                ),
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="masked",
                    key="black balaclava",
                ),
            ]
        )
        self.assertEqual(get_disguise_adjective(char), "masked")

    def test_unknown_adjective_admitted_at_lowest_rank(self) -> None:
        """Unknown adjectives still ship — they just lose to known ones."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="bedazzled",
                    key="rhinestone visor",
                ),
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="hooded",
                    key="grey hood",
                ),
            ]
        )
        self.assertEqual(get_disguise_adjective(char), "hooded")

    def test_unknown_adjective_alone_wins(self) -> None:
        """A solo unknown adjective should still be picked, not dropped."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="bedazzled",
                    key="rhinestone visor",
                )
            ]
        )
        self.assertEqual(get_disguise_adjective(char), "bedazzled")

    def test_unknown_adjectives_tiebreak_alphabetically(self) -> None:
        """Two unknowns at rank 999 → alphabetical first wins (deterministic)."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="zonked",
                    key="z",
                ),
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="bedazzled",
                    key="b",
                ),
            ]
        )
        self.assertEqual(get_disguise_adjective(char), "bedazzled")

    def test_non_disguise_item_with_adjective_skipped_with_warning(
        self,
    ) -> None:
        """Adjective on non-disguise item is ignored (red-flag standard)."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=False,
                    disguise_adjective="masked",
                    key="ceremonial mask",
                )
            ]
        )
        with patch("world.identity.logger.log_warn") as mock_warn:
            self.assertIsNone(get_disguise_adjective(char))
            mock_warn.assert_called_once()

    def test_empty_adjective_string_ignored(self) -> None:
        """Items without a populated adjective contribute nothing."""
        from world.identity import get_disguise_adjective

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    is_disguise_item=True,
                    disguise_adjective="",
                    key="plain hat",
                )
            ]
        )
        self.assertIsNone(get_disguise_adjective(char))


class TestGetIdentitySignature(TestCase):
    """Signature is the deterministic input tuple for Apparent UID derivation."""

    def test_undisguised_signature_shape(self) -> None:
        """Signature is a 5-tuple ending with an empty essential-items tuple."""
        from world.identity import get_identity_signature

        char = _SignatureMockCharacter()
        sig = get_identity_signature(char)
        self.assertEqual(len(sig), 5)
        self.assertEqual(sig[0], "uid-jorge")
        self.assertIsNone(sig[1])
        self.assertIsNone(sig[2])
        self.assertIsNone(sig[3])
        # Essential-item tuple is empty until PR-C wires the flag.
        self.assertEqual(sig[4], ())

    def test_overrides_change_signature(self) -> None:
        from world.identity import get_identity_signature

        bare = get_identity_signature(_SignatureMockCharacter())
        disguised = get_identity_signature(
            _SignatureMockCharacter(
                height_override="short",
                build_override="stocky",
                keyword_override="woman",
            )
        )
        self.assertNotEqual(bare, disguised)
        self.assertEqual(disguised[1], "short")
        self.assertEqual(disguised[2], "stocky")
        self.assertEqual(disguised[3], "woman")

    def test_signature_is_pure_function_of_state(self) -> None:
        """Two calls on the same state yield the same signature (no caching artefacts)."""
        from world.identity import get_identity_signature

        char = _SignatureMockCharacter(keyword_override="hooded")
        self.assertEqual(get_identity_signature(char), get_identity_signature(char))


class TestGetApparentUid(TestCase):
    """Apparent UID is a deterministic 16-char hex digest of the signature."""

    def test_uid_is_sixteen_hex_chars(self) -> None:
        from world.identity import APPARENT_UID_HEX_LENGTH, get_apparent_uid

        uid = get_apparent_uid(_SignatureMockCharacter())
        self.assertIsNotNone(uid)
        self.assertEqual(len(uid), APPARENT_UID_HEX_LENGTH)
        self.assertEqual(len(uid), 16)
        int(uid, 16)  # Raises ValueError if not valid hex.

    def test_uid_is_deterministic(self) -> None:
        """Same signature → same UID across calls (unlike salted ``hash()``)."""
        from world.identity import get_apparent_uid

        char1 = _SignatureMockCharacter(sleeve_uid="uid-x", keyword_override="man")
        char2 = _SignatureMockCharacter(sleeve_uid="uid-x", keyword_override="man")
        self.assertEqual(get_apparent_uid(char1), get_apparent_uid(char2))

    def test_uid_changes_with_disguise(self) -> None:
        """Adopting any override produces a distinct UID from the bare form."""
        from world.identity import get_apparent_uid

        bare = get_apparent_uid(_SignatureMockCharacter())
        disguised = get_apparent_uid(
            _SignatureMockCharacter(keyword_override="woman")
        )
        self.assertNotEqual(bare, disguised)

    def test_uid_includes_sleeve_salt(self) -> None:
        """Two impostors with identical disguises still get distinct UIDs."""
        from world.identity import get_apparent_uid

        a = _SignatureMockCharacter(sleeve_uid="uid-A", keyword_override="hooded")
        b = _SignatureMockCharacter(sleeve_uid="uid-B", keyword_override="hooded")
        self.assertNotEqual(get_apparent_uid(a), get_apparent_uid(b))

    def test_uid_none_when_no_sleeve(self) -> None:
        """Pre-chargen shells (no sleeve_uid) produce ``None``, never a digest."""
        from world.identity import get_apparent_uid

        self.assertIsNone(
            get_apparent_uid(_SignatureMockCharacter(sleeve_uid=None))
        )


class TestGetApparentGender(TestCase):
    """Gender derivation follows keyword override → real grammar gender."""

    def test_no_override_uses_real_gender(self) -> None:
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(sex="male", gender="male")
        self.assertEqual(get_apparent_gender(char), "male")

    def test_no_override_falls_back_to_sex_when_no_gender(self) -> None:
        """When ``gender`` is unset, fall back through GENDER_MAP[sex]."""
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(sex="female", gender=None)
        self.assertEqual(get_apparent_gender(char), "female")

    def test_feminine_override_returns_female(self) -> None:
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(sex="male", keyword_override="woman")
        self.assertEqual(get_apparent_gender(char), "female")

    def test_masculine_override_returns_male(self) -> None:
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(sex="female", keyword_override="man")
        self.assertEqual(get_apparent_gender(char), "male")

    def test_neutral_keyword_override_returns_neutral(self) -> None:
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(sex="male", keyword_override="figure")
        self.assertEqual(get_apparent_gender(char), "neutral")

    def test_custom_keyword_override_returns_neutral(self) -> None:
        """Custom ``@shortdesc`` keywords carry no gender metadata → neutral."""
        from world.identity import get_apparent_gender

        char = _SignatureMockCharacter(
            sex="male", gender="male", keyword_override="zaibatsu-runner"
        )
        self.assertEqual(get_apparent_gender(char), "neutral")


class TestLegacyRecognitionWipe(TestCase):
    """Idempotent shape-check wipe of pre-engine-PR recognition entries."""

    def _entry(self, **overrides) -> dict:
        base = {
            "assigned_name": "Big J",
            "first_seen": "2025-01-01T00:00:00",
            "last_seen": "2025-01-01T00:00:00",
            "times_seen": 1,
            "lost_contact": False,
        }
        base.update(overrides)
        return base

    def test_legacy_uuid_key_is_wiped(self) -> None:
        """36-char UUID-style keys are pre-engine and must be wiped."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = {
            "12345678-1234-1234-1234-123456789012": self._entry(),
        }
        wiped = wipe_legacy_recognition_memory(char)
        self.assertEqual(wiped, 1)
        self.assertEqual(char.recognition_memory, {})

    def test_missing_lost_contact_field_is_wiped(self) -> None:
        """16-char key but missing ``lost_contact`` field → still legacy."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        # 16-char key, but entry pre-dates the lost_contact field.
        legacy = self._entry()
        del legacy["lost_contact"]
        char.recognition_memory = {"abcdef0123456789": legacy}
        wiped = wipe_legacy_recognition_memory(char)
        self.assertEqual(wiped, 1)
        self.assertEqual(char.recognition_memory, {})

    def test_modern_entry_is_preserved(self) -> None:
        """16-char key + ``lost_contact`` field present → no-op."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = {"abcdef0123456789": self._entry()}
        wiped = wipe_legacy_recognition_memory(char)
        self.assertEqual(wiped, 0)
        self.assertIn("abcdef0123456789", char.recognition_memory)

    def test_wipe_is_idempotent(self) -> None:
        """A second call after a successful wipe is a no-op."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = {
            "12345678-1234-1234-1234-123456789012": self._entry(),
            "abcdef0123456789": self._entry(),
        }
        first = wipe_legacy_recognition_memory(char)
        second = wipe_legacy_recognition_memory(char)
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)

    def test_wipe_handles_empty_memory(self) -> None:
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = {}
        self.assertEqual(wipe_legacy_recognition_memory(char), 0)

    def test_wipe_handles_none_memory(self) -> None:
        """A character with no recognition_memory attribute is handled gracefully."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = None
        self.assertEqual(wipe_legacy_recognition_memory(char), 0)

    def test_non_dict_entry_value_is_wiped(self) -> None:
        """A corrupt non-dict value at a 16-char key is still legacy."""
        from world.identity import wipe_legacy_recognition_memory

        char = _SignatureMockCharacter()
        char.recognition_memory = {"abcdef0123456789": "corrupt-string"}
        self.assertEqual(wipe_legacy_recognition_memory(char), 1)
        self.assertEqual(char.recognition_memory, {})
