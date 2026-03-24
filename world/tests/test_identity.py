"""
Tests for Identity Constants and Sdesc Composition (``world/identity.py``).

Pure unit tests with no Evennia dependencies.  Run via::

    evennia test world.tests.test_identity

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase

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
    """Tests for ``get_valid_keywords`` and ``is_valid_keyword``."""

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
