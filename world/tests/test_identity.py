"""
Tests for Identity Constants and Sdesc Composition (``world/identity.py``).

Pure unit tests with no Evennia dependencies.  Run via::

    evennia test world.tests.test_identity

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

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

    The getter functions read from :class:`ServerConfig` when set.  We
    patch ``ServerConfig.objects.conf`` to return ``None`` (the
    unset-key path) so the getters fall back to code-level
    ``_DEFAULT_*`` frozensets, keeping these routing tests independent
    of live DB state.
    """

    def setUp(self) -> None:
        patcher = patch(
            "world.identity.ServerConfig.objects.conf",
            return_value=None,
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
    """Verify that keyword getters handle all ``ServerConfig`` states.

    Each getter has two code paths:

    1. Key is set in :class:`ServerConfig` → return the stored data
       (coerced to ``frozenset``).
    2. Key is unset (``ServerConfig.objects.conf`` returns ``None``) →
       fall back to the module-level ``_DEFAULT_*`` frozenset.
    """

    # -- Happy path: ServerConfig provides keywords --------------------

    def test_feminine_returns_serverconfig_keywords(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value={"queen", "duchess"},
        ):
            result = get_feminine_keywords()
        self.assertEqual(result, frozenset({"queen", "duchess"}))

    def test_masculine_returns_serverconfig_keywords(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value={"king", "duke"},
        ):
            result = get_masculine_keywords()
        self.assertEqual(result, frozenset({"king", "duke"}))

    def test_neutral_returns_serverconfig_keywords(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value={"citizen", "clone"},
        ):
            result = get_neutral_keywords()
        self.assertEqual(result, frozenset({"citizen", "clone"}))

    # -- Unset key: fallback to defaults -------------------------------

    def test_feminine_falls_back_when_unset(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value=None,
        ):
            self.assertEqual(get_feminine_keywords(), _DEFAULT_FEMININE_KEYWORDS)

    def test_masculine_falls_back_when_unset(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value=None,
        ):
            self.assertEqual(get_masculine_keywords(), _DEFAULT_MASCULINE_KEYWORDS)

    def test_neutral_falls_back_when_unset(self) -> None:
        with patch(
            "world.identity.ServerConfig.objects.conf",
            return_value=None,
        ):
            self.assertEqual(get_neutral_keywords(), _DEFAULT_NEUTRAL_KEYWORDS)

    # -- Per-key routing: only the right key is read -------------------

    def test_getters_pass_distinct_serverconfig_keys(self) -> None:
        """Each getter must query its own gender-specific key."""
        captured: list[str] = []

        def fake_conf(key, *args, **kwargs):
            captured.append(key)
            return None

        with patch(
            "world.identity.ServerConfig.objects.conf",
            side_effect=fake_conf,
        ):
            get_feminine_keywords()
            get_masculine_keywords()
            get_neutral_keywords()

        self.assertEqual(
            captured,
            [
                "identity.feminine_keywords",
                "identity.masculine_keywords",
                "identity.neutral_keywords",
            ],
        )

    # -- Unset path does NOT log ---------------------------------------

    def test_unset_path_does_not_log(self) -> None:
        """The unset path is the normal fresh-install state and silent."""
        with (
            patch(
                "world.identity.ServerConfig.objects.conf",
                return_value=None,
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

    def test_pluralia_tantum_scissors(self) -> None:
        """Pluralia-tantum tools wield bare, no indefinite article."""
        self.assertEqual(
            format_wielded_feature("scissors"),
            "wielding scissors",
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

    def test_pluralia_tantum_jeans(self) -> None:
        """Pluralia-tantum garments worn bare, no indefinite article."""
        self.assertEqual(
            format_clothing_feature("blue jeans"),
            "in blue jeans",
        )

    def test_pluralia_tantum_boots(self) -> None:
        self.assertEqual(
            format_clothing_feature("black leather combat boots"),
            "in black leather combat boots",
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
    ``worn_sdesc_short`` / ``coverage`` / ``key`` (distinguishing
    feature; ``"hair"`` in ``coverage`` suppresses hair fallback,
    replacing the legacy ``covers_hair`` boolean — see #176).
    """

    def __init__(
        self,
        *,
        disguise_essential: bool = False,
        disguise_type_id: str = "",
        is_disguise_item: bool = False,
        disguise_adjective: str = "",
        worn_sdesc_short: str = "",
        coverage: list | None = None,
        key: str = "fake item",
        disguise_weight: int = 1,
        disguise_silent_feature: bool = False,
    ) -> None:
        self.disguise_essential = disguise_essential
        self.disguise_type_id = disguise_type_id
        self.is_disguise_item = is_disguise_item
        self.disguise_adjective = disguise_adjective
        self.worn_sdesc_short = worn_sdesc_short
        self.coverage = list(coverage) if coverage else []
        self.key = key
        self.disguise_weight = disguise_weight
        self.disguise_silent_feature = disguise_silent_feature

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

    def test_silent_feature_item_still_contributes_type_id(self) -> None:
        """``disguise_silent_feature`` only suppresses the feature clause —
        UID / signature contribution is preserved so swap detection
        and recognition memory still work."""
        from world.identity import get_essential_item_type_ids

        char = _SignatureMockCharacter(
            worn_items=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="contacts",
                    disguise_silent_feature=True,
                ),
            ]
        )
        self.assertEqual(get_essential_item_type_ids(char), ("contacts",))


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



# ===================================================================
# mark_lost_contact_entries — lazy orphan marking
# ===================================================================


class TestMarkLostContactEntries(TestCase):
    """Stale recognition entries get ``lost_contact = True`` lazily."""

    def _make_observer(self, memory):
        """Build a stand-in observer with a ``recognition_memory`` dict."""
        observer = MagicMock()
        observer.recognition_memory = memory
        return observer

    def _entry(self, *, last_seen, lost_contact=False):
        """Minimal recognition entry shaped like production writes."""
        return {
            "assigned_name": "Spartacus",
            "last_seen": last_seen,
            "lost_contact": lost_contact,
        }

    def test_flips_stale_entry_not_in_room(self):
        """UID not visible + last_seen older than threshold → flipped."""
        from datetime import datetime, timedelta
        from world.identity import (
            LOST_CONTACT_THRESHOLD_SECONDS,
            mark_lost_contact_entries,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(seconds=LOST_CONTACT_THRESHOLD_SECONDS + 60)
        memory = {
            "uid-stale": self._entry(
                last_seen=stale.strftime("%Y-%m-%dT%H:%M:%S")
            ),
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(observer, set(), now=now)

        self.assertEqual(flipped, 1)
        self.assertTrue(memory["uid-stale"]["lost_contact"])

    def test_does_not_flip_recent_entry(self):
        """Entry within threshold → no flip even when not visible."""
        from datetime import datetime, timedelta
        from world.identity import (
            LOST_CONTACT_THRESHOLD_SECONDS,
            mark_lost_contact_entries,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        fresh = now - timedelta(seconds=LOST_CONTACT_THRESHOLD_SECONDS - 60)
        memory = {
            "uid-fresh": self._entry(
                last_seen=fresh.strftime("%Y-%m-%dT%H:%M:%S")
            ),
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(observer, set(), now=now)

        self.assertEqual(flipped, 0)
        self.assertFalse(memory["uid-fresh"]["lost_contact"])

    def test_does_not_flip_visible_entry(self):
        """Even an ancient entry stays unflagged when its UID is visible."""
        from datetime import datetime, timedelta
        from world.identity import (
            LOST_CONTACT_THRESHOLD_SECONDS,
            mark_lost_contact_entries,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        ancient = now - timedelta(
            seconds=LOST_CONTACT_THRESHOLD_SECONDS * 10
        )
        memory = {
            "uid-here": self._entry(
                last_seen=ancient.strftime("%Y-%m-%dT%H:%M:%S")
            ),
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(
            observer, {"uid-here"}, now=now
        )

        self.assertEqual(flipped, 0)
        self.assertFalse(memory["uid-here"]["lost_contact"])

    def test_already_flagged_entry_not_double_counted(self):
        """Re-running on a flagged entry is a no-op return value."""
        from datetime import datetime, timedelta
        from world.identity import (
            LOST_CONTACT_THRESHOLD_SECONDS,
            mark_lost_contact_entries,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(seconds=LOST_CONTACT_THRESHOLD_SECONDS + 60)
        memory = {
            "uid-already": self._entry(
                last_seen=stale.strftime("%Y-%m-%dT%H:%M:%S"),
                lost_contact=True,
            ),
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(observer, set(), now=now)

        self.assertEqual(flipped, 0)
        # State preserved.
        self.assertTrue(memory["uid-already"]["lost_contact"])

    def test_empty_memory_returns_zero(self):
        from world.identity import mark_lost_contact_entries

        observer = self._make_observer({})
        self.assertEqual(mark_lost_contact_entries(observer, set()), 0)

    def test_observer_without_memory_attr_returns_zero(self):
        from world.identity import mark_lost_contact_entries

        observer = MagicMock()
        observer.recognition_memory = None
        self.assertEqual(mark_lost_contact_entries(observer, set()), 0)

    def test_unparseable_timestamp_skipped(self):
        """Malformed last_seen is skipped, not flipped."""
        from world.identity import mark_lost_contact_entries

        memory = {
            "uid-bad": self._entry(last_seen="not-a-timestamp"),
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(observer, set())

        self.assertEqual(flipped, 0)
        self.assertFalse(memory["uid-bad"]["lost_contact"])

    def test_missing_last_seen_skipped(self):
        from world.identity import mark_lost_contact_entries

        memory = {
            "uid-empty": {"assigned_name": "X", "lost_contact": False},
        }
        observer = self._make_observer(memory)

        flipped = mark_lost_contact_entries(observer, set())

        self.assertEqual(flipped, 0)
        self.assertFalse(memory["uid-empty"]["lost_contact"])


# ===================================================================
# bump_recognition_recency — passive perception recency refresh
# ===================================================================


class TestBumpRecognitionRecency(TestCase):
    """Passive perception updates recency fields on existing entries."""

    TS_FMT = "%Y-%m-%dT%H:%M:%S"

    def _make_observer(self, memory, *, location_key="Plaza"):
        observer = MagicMock()
        observer.recognition_memory = memory
        observer.location.key = location_key
        return observer

    def _make_target(self, *, sdesc="a tall lean droog"):
        target = MagicMock()
        target.get_sdesc.return_value = sdesc
        return target

    def _entry(self, *, last_seen, lost_contact=False, sdesc="old sdesc"):
        return {
            "assigned_name": "Spartacus",
            "last_seen": last_seen,
            "times_seen": 3,
            "location_last_seen": "OldRoom",
            "sdesc_at_last_encounter": sdesc,
            "lost_contact": lost_contact,
        }

    def test_bump_updates_recency_fields(self):
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-known": self._entry(last_seen=stale.strftime(self.TS_FMT)),
        }
        observer = self._make_observer(memory, location_key="NewRoom")
        target = self._make_target(sdesc="a tall lean masked droog")

        result = bump_recognition_recency(
            observer, target, "uid-known", now=now
        )

        self.assertTrue(result)
        entry = memory["uid-known"]
        self.assertEqual(entry["last_seen"], now.strftime(self.TS_FMT))
        self.assertEqual(entry["location_last_seen"], "NewRoom")
        self.assertEqual(
            entry["sdesc_at_last_encounter"], "a tall lean masked droog"
        )
        self.assertFalse(entry["lost_contact"])

    def test_bump_clears_lost_contact_flag(self):
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-lost": self._entry(
                last_seen=stale.strftime(self.TS_FMT), lost_contact=True
            ),
        }
        observer = self._make_observer(memory)
        target = self._make_target()

        bump_recognition_recency(observer, target, "uid-lost", now=now)

        self.assertFalse(memory["uid-lost"]["lost_contact"])

    def test_bump_does_not_increment_times_seen(self):
        """times_seen counts explicit `remember`, not perceptions."""
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-known": self._entry(last_seen=stale.strftime(self.TS_FMT)),
        }
        observer = self._make_observer(memory)
        target = self._make_target()

        bump_recognition_recency(observer, target, "uid-known", now=now)

        self.assertEqual(memory["uid-known"]["times_seen"], 3)

    def test_throttle_blocks_recent_bump(self):
        """Bump within throttle window is a no-op."""
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        recent = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS - 60
        )
        recent_iso = recent.strftime(self.TS_FMT)
        memory = {
            "uid-known": self._entry(last_seen=recent_iso),
        }
        observer = self._make_observer(memory, location_key="NewRoom")
        target = self._make_target(sdesc="changed sdesc")

        result = bump_recognition_recency(
            observer, target, "uid-known", now=now
        )

        self.assertFalse(result)
        # Fields preserved exactly.
        self.assertEqual(memory["uid-known"]["last_seen"], recent_iso)
        self.assertEqual(memory["uid-known"]["location_last_seen"], "OldRoom")
        self.assertEqual(
            memory["uid-known"]["sdesc_at_last_encounter"], "old sdesc"
        )

    def test_unknown_uid_is_noop_and_does_not_create_entry(self):
        """Helper never creates entries — guards against retroactive memory."""
        from datetime import datetime
        from world.identity import bump_recognition_recency

        memory = {"uid-known": self._entry(last_seen="2025-01-01T00:00:00")}
        before = dict(memory)
        observer = self._make_observer(memory)
        target = self._make_target()

        result = bump_recognition_recency(
            observer,
            target,
            "uid-stranger",
            now=datetime(2026, 1, 1, 12, 0, 0),
        )

        self.assertFalse(result)
        self.assertEqual(memory, before)
        self.assertNotIn("uid-stranger", memory)

    def test_empty_memory_is_noop(self):
        from datetime import datetime
        from world.identity import bump_recognition_recency

        observer = MagicMock()
        observer.recognition_memory = {}
        target = self._make_target()

        result = bump_recognition_recency(
            observer, target, "uid-anything", now=datetime(2026, 1, 1)
        )

        self.assertFalse(result)
        self.assertEqual(observer.recognition_memory, {})

    def test_observer_without_memory_attr_is_noop(self):
        from datetime import datetime
        from world.identity import bump_recognition_recency

        observer = MagicMock()
        observer.recognition_memory = None
        target = self._make_target()

        result = bump_recognition_recency(
            observer, target, "uid-anything", now=datetime(2026, 1, 1)
        )

        self.assertFalse(result)

    def test_missing_last_seen_bumps_immediately(self):
        """No prior timestamp → treat as stale, bump now."""
        from datetime import datetime
        from world.identity import bump_recognition_recency

        now = datetime(2026, 1, 1, 12, 0, 0)
        memory = {
            "uid-known": {
                "assigned_name": "X",
                "times_seen": 1,
                "lost_contact": False,
            },
        }
        observer = self._make_observer(memory)
        target = self._make_target()

        result = bump_recognition_recency(
            observer, target, "uid-known", now=now
        )

        self.assertTrue(result)
        self.assertEqual(
            memory["uid-known"]["last_seen"], now.strftime(self.TS_FMT)
        )

    def test_malformed_last_seen_logs_warning_and_bumps(self):
        from datetime import datetime
        from world.identity import bump_recognition_recency

        now = datetime(2026, 1, 1, 12, 0, 0)
        memory = {
            "uid-bad": self._entry(last_seen="not-a-timestamp"),
        }
        observer = self._make_observer(memory)
        target = self._make_target()

        with patch("world.identity.logger") as mock_logger:
            result = bump_recognition_recency(
                observer, target, "uid-bad", now=now
            )

        self.assertTrue(result)
        self.assertEqual(
            memory["uid-bad"]["last_seen"], now.strftime(self.TS_FMT)
        )
        mock_logger.log_warn.assert_called_once()

    def test_observer_without_location_uses_unknown(self):
        from datetime import datetime
        from world.identity import bump_recognition_recency

        now = datetime(2026, 1, 1, 12, 0, 0)
        memory = {
            "uid-known": {
                "assigned_name": "X",
                "times_seen": 1,
                "lost_contact": False,
            },
        }
        observer = MagicMock()
        observer.recognition_memory = memory
        observer.location = None
        target = self._make_target()

        bump_recognition_recency(observer, target, "uid-known", now=now)

        self.assertEqual(memory["uid-known"]["location_last_seen"], "unknown")

    def test_bump_backfills_real_sleeve_uid_when_missing(self):
        """Bump path backfills `real_sleeve_uid` on legacy entries.

        Pre-schema entries (written before PR-X2) lack the
        ``real_sleeve_uid`` field; the bump path opportunistically
        backfills it from ``target.sleeve_uid`` so the entry becomes
        eligible for disguise-piercing reverse lookup.
        """
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-known": self._entry(
                last_seen=stale.strftime(self.TS_FMT)
            ),
        }
        # Note: legacy entry has no `real_sleeve_uid` key.
        self.assertNotIn("real_sleeve_uid", memory["uid-known"])

        observer = self._make_observer(memory)
        target = self._make_target()
        target.sleeve_uid = "sleeve-jorge-123"

        bumped = bump_recognition_recency(
            observer, target, "uid-known", now=now
        )

        self.assertTrue(bumped)
        self.assertEqual(
            memory["uid-known"]["real_sleeve_uid"], "sleeve-jorge-123"
        )

    def test_bump_preserves_existing_real_sleeve_uid(self):
        """Bump must not overwrite an already-set `real_sleeve_uid`."""
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-known": {
                **self._entry(last_seen=stale.strftime(self.TS_FMT)),
                "real_sleeve_uid": "sleeve-original",
            },
        }
        observer = self._make_observer(memory)
        target = self._make_target()
        # Even if target reports a different sleeve_uid, the stored
        # field must not change (it never changes for a given body).
        target.sleeve_uid = "sleeve-different-somehow"

        bump_recognition_recency(observer, target, "uid-known", now=now)

        self.assertEqual(
            memory["uid-known"]["real_sleeve_uid"], "sleeve-original"
        )

    def test_bump_handles_missing_target_sleeve_uid(self):
        """No backfill when target has no sleeve_uid (pre-chargen)."""
        from datetime import datetime, timedelta
        from world.identity import (
            RECOGNITION_BUMP_THROTTLE_SECONDS,
            bump_recognition_recency,
        )

        now = datetime(2026, 1, 1, 12, 0, 0)
        stale = now - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        memory = {
            "uid-known": self._entry(
                last_seen=stale.strftime(self.TS_FMT)
            ),
        }
        observer = self._make_observer(memory)
        target = self._make_target()
        target.sleeve_uid = None

        bump_recognition_recency(observer, target, "uid-known", now=now)

        # No real_sleeve_uid added because target has none.
        self.assertIsNone(memory["uid-known"].get("real_sleeve_uid"))


class TestFindEntriesByRealSleeveUid(TestCase):
    """Reverse-lookup helper used by disguise-piercing recognition.

    Walks ``observer.recognition_memory`` and returns every entry
    whose ``real_sleeve_uid`` matches.  Multiple matches are expected
    in the disguise-piercing case (one body, many presentations).
    Pre-schema entries (no field set) are silently skipped.
    """

    def test_returns_all_matching_entries(self):
        from world.identity import find_entries_by_real_sleeve_uid

        memory = {
            "uid-bare": {
                "assigned_name": "Bruce Wayne",
                "real_sleeve_uid": "sleeve-bruce",
            },
            "uid-cape": {
                "assigned_name": "the Bat",
                "real_sleeve_uid": "sleeve-bruce",
            },
            "uid-shades": {
                "assigned_name": "creep in shades",
                "real_sleeve_uid": "sleeve-bruce",
            },
            "uid-other": {
                "assigned_name": "Alfred",
                "real_sleeve_uid": "sleeve-alfred",
            },
        }
        observer = MagicMock()
        observer.recognition_memory = memory

        matches = find_entries_by_real_sleeve_uid(observer, "sleeve-bruce")

        self.assertEqual(len(matches), 3)
        uids = {uid for uid, _ in matches}
        self.assertEqual(uids, {"uid-bare", "uid-cape", "uid-shades"})

    def test_returns_empty_when_no_match(self):
        from world.identity import find_entries_by_real_sleeve_uid

        observer = MagicMock()
        observer.recognition_memory = {
            "uid-a": {"real_sleeve_uid": "sleeve-other"},
        }

        self.assertEqual(
            find_entries_by_real_sleeve_uid(observer, "sleeve-missing"),
            [],
        )

    def test_skips_entries_without_real_sleeve_uid(self):
        """Legacy entries (pre-schema) are silently ignored."""
        from world.identity import find_entries_by_real_sleeve_uid

        observer = MagicMock()
        observer.recognition_memory = {
            "uid-legacy": {"assigned_name": "Old Entry"},  # no field
            "uid-fresh": {
                "assigned_name": "New Entry",
                "real_sleeve_uid": "sleeve-bruce",
            },
        }

        matches = find_entries_by_real_sleeve_uid(observer, "sleeve-bruce")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], "uid-fresh")

    def test_empty_real_sleeve_uid_returns_empty(self):
        """Empty/None lookup keys short-circuit immediately."""
        from world.identity import find_entries_by_real_sleeve_uid

        observer = MagicMock()
        observer.recognition_memory = {
            "uid-a": {"real_sleeve_uid": ""},
        }

        self.assertEqual(find_entries_by_real_sleeve_uid(observer, ""), [])
        self.assertEqual(
            find_entries_by_real_sleeve_uid(observer, None), []
        )

    def test_observer_without_memory_returns_empty(self):
        from world.identity import find_entries_by_real_sleeve_uid

        observer = MagicMock()
        observer.recognition_memory = None

        self.assertEqual(
            find_entries_by_real_sleeve_uid(observer, "sleeve-x"), []
        )

    def test_does_not_match_on_apparent_uid(self):
        """Match must be against `real_sleeve_uid` field, not the dict key."""
        from world.identity import find_entries_by_real_sleeve_uid

        observer = MagicMock()
        observer.recognition_memory = {
            "sleeve-bruce": {"real_sleeve_uid": "sleeve-other"},
        }

        # The dict key happens to equal what we're looking for, but the
        # field value doesn't — must not match.
        self.assertEqual(
            find_entries_by_real_sleeve_uid(observer, "sleeve-bruce"), []
        )


class TestAttemptDisguisePierce(TestCase):
    """Opposed Intellect-vs-Resonance roll with cache.

    The cache is keyed on ``(target.dbref, apparent_uid)`` and stored
    on ``observer.db.disguise_pierce_cache``.  Cached outcomes short-
    circuit before the dice are touched.
    """

    def _make_observer(self):
        observer = MagicMock()
        observer.dbref = "#10"
        observer.db.disguise_pierce_cache = None
        return observer

    def _make_target(self, with_overrides=False, worn_items=None):
        target = MagicMock()
        target.dbref = "#20"
        target.db.height_override = "tall" if with_overrides else None
        target.db.build_override = None
        target.db.keyword_override = None
        target.get_worn_items = MagicMock(return_value=worn_items or [])
        return target

    def test_cache_hit_true_short_circuits(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        target = self._make_target()
        observer.db.disguise_pierce_cache = {("#20", "uid-cape"): True}
        bare = {"times_seen": 0}

        with patch("world.combat.dice.opposed_roll") as roll:
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertTrue(result)
        roll.assert_not_called()

    def test_cache_hit_false_short_circuits(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        target = self._make_target()
        observer.db.disguise_pierce_cache = {("#20", "uid-cape"): False}
        bare = {"times_seen": 99}

        with patch("world.combat.dice.opposed_roll") as roll:
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertFalse(result)
        roll.assert_not_called()

    def test_success_caches_outcome(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        target = self._make_target()
        bare = {"times_seen": 0}

        with patch(
            "world.combat.dice.opposed_roll", return_value=(10, 1, True)
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertTrue(result)
        self.assertEqual(
            observer.db.disguise_pierce_cache, {("#20", "uid-cape"): True}
        )

    def test_failure_caches_outcome(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        target = self._make_target()
        bare = {"times_seen": 0}

        with patch(
            "world.combat.dice.opposed_roll", return_value=(1, 10, False)
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertFalse(result)
        self.assertEqual(
            observer.db.disguise_pierce_cache, {("#20", "uid-cape"): False}
        )

    def test_familiarity_bonus_lets_observer_win(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        target = self._make_target()
        # Tie on raw rolls — observer's familiarity bonus should
        # push them over the top.
        bare = {"times_seen": 3}

        with patch(
            "world.combat.dice.opposed_roll", return_value=(5, 5, False)
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertTrue(result)

    def test_disguise_vectors_penalise_observer(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        item = MagicMock()
        item.disguise_essential = True
        target = self._make_target(with_overrides=True, worn_items=[item])
        # Observer rolls 4, target rolls 2; vectors=2 (override + item)
        # penalises observer's effective total to 2 vs target's 4. Fail.
        bare = {"times_seen": 0}

        with patch(
            "world.combat.dice.opposed_roll", return_value=(4, 2, True)
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertFalse(result)

    def test_uncacheable_when_observer_lacks_dbref(self):
        from world.identity import attempt_disguise_pierce

        observer = self._make_observer()
        observer.dbref = None
        target = self._make_target()
        bare = {"times_seen": 0}

        with patch(
            "world.combat.dice.opposed_roll", return_value=(10, 1, True)
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertTrue(result)
        # Cache must not have been written.
        self.assertIsNone(observer.db.disguise_pierce_cache)

    def test_familiarity_bonus_capped(self):
        from world.identity import (
            DISGUISE_PIERCE_FAMILIARITY_CAP,
            attempt_disguise_pierce,
        )

        observer = self._make_observer()
        target = self._make_target()
        # Times_seen far above the cap — bonus must clip.  Set target's
        # roll just above (observer_roll + CAP) so the observer fails
        # even with bonus saturated.
        bare = {"times_seen": 999}

        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(1, 1 + DISGUISE_PIERCE_FAMILIARITY_CAP + 1, False),
        ):
            result = attempt_disguise_pierce(observer, target, "uid-cape", bare)

        self.assertFalse(result)


class TestAttemptDisplayPierce(TestCase):
    """End-to-end pierce wrapper used by Character.get_display_name."""

    def _make_observer(self, memory=None):
        observer = MagicMock()
        observer.dbref = "#10"
        observer.recognition_memory = memory or {}
        observer.db.disguise_pierce_cache = None
        return observer

    def _make_target(self, sleeve_uid="sleeve-bruce"):
        target = MagicMock()
        target.dbref = "#20"
        target.sleeve_uid = sleeve_uid
        target.db.height_override = None
        target.db.build_override = None
        target.db.keyword_override = None
        target.get_worn_items = MagicMock(return_value=[])
        return target

    def test_returns_none_when_looker_is_target(self):
        from world.identity import attempt_display_pierce

        target = self._make_target()
        self.assertIsNone(attempt_display_pierce(target, target, "uid-cape"))

    def test_returns_none_when_apparent_uid_missing(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer()
        target = self._make_target()
        self.assertIsNone(attempt_display_pierce(observer, target, None))

    def test_returns_none_when_memory_empty(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer()
        target = self._make_target()
        self.assertIsNone(
            attempt_display_pierce(observer, target, "uid-cape")
        )

    def test_returns_none_when_target_has_no_sleeve(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer(
            memory={
                "uid-bare": {
                    "assigned_name": "Bruce",
                    "real_sleeve_uid": "sleeve-bruce",
                }
            }
        )
        target = self._make_target(sleeve_uid=None)
        self.assertIsNone(
            attempt_display_pierce(observer, target, "uid-cape")
        )

    def test_returns_none_when_no_other_presentation_known(self):
        from world.identity import attempt_display_pierce

        # Only entry the looker has for this sleeve IS the current
        # apparent_uid — nothing to pierce against.
        observer = self._make_observer(
            memory={
                "uid-cape": {
                    "assigned_name": "the Bat",
                    "real_sleeve_uid": "sleeve-bruce",
                }
            }
        )
        target = self._make_target()
        self.assertIsNone(
            attempt_display_pierce(observer, target, "uid-cape")
        )

    def test_success_returns_bare_face_name(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer(
            memory={
                "uid-bare": {
                    "assigned_name": "Bruce",
                    "real_sleeve_uid": "sleeve-bruce",
                    "times_seen": 3,
                }
            }
        )
        target = self._make_target()
        with patch(
            "world.combat.dice.opposed_roll", return_value=(10, 1, True)
        ):
            result = attempt_display_pierce(observer, target, "uid-cape")
        self.assertEqual(result, "Bruce")

    def test_failure_returns_none(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer(
            memory={
                "uid-bare": {
                    "assigned_name": "Bruce",
                    "real_sleeve_uid": "sleeve-bruce",
                    "times_seen": 0,
                }
            }
        )
        target = self._make_target()
        with patch(
            "world.combat.dice.opposed_roll", return_value=(1, 10, False)
        ):
            result = attempt_display_pierce(observer, target, "uid-cape")
        self.assertIsNone(result)

    def test_picks_first_candidate_when_multiple_match(self):
        from world.identity import attempt_display_pierce

        # Dict insertion order preserved by Python 3.7+; bare-face
        # entry comes first.
        observer = self._make_observer(
            memory={
                "uid-bare": {
                    "assigned_name": "Bruce",
                    "real_sleeve_uid": "sleeve-bruce",
                    "times_seen": 1,
                },
                "uid-shades": {
                    "assigned_name": "creep in shades",
                    "real_sleeve_uid": "sleeve-bruce",
                    "times_seen": 1,
                },
            }
        )
        target = self._make_target()
        with patch(
            "world.combat.dice.opposed_roll", return_value=(10, 1, True)
        ):
            result = attempt_display_pierce(observer, target, "uid-cape")
        self.assertEqual(result, "Bruce")

    def test_skips_candidates_without_assigned_name(self):
        from world.identity import attempt_display_pierce

        observer = self._make_observer(
            memory={
                "uid-anon": {
                    "assigned_name": None,
                    "real_sleeve_uid": "sleeve-bruce",
                },
                "uid-bare": {
                    "assigned_name": "Bruce",
                    "real_sleeve_uid": "sleeve-bruce",
                    "times_seen": 1,
                },
            }
        )
        target = self._make_target()
        with patch(
            "world.combat.dice.opposed_roll", return_value=(10, 1, True)
        ):
            result = attempt_display_pierce(observer, target, "uid-cape")
        self.assertEqual(result, "Bruce")


# =========================================================================
# _count_disguise_vectors — per-item disguise_weight support
# =========================================================================


class TestCountDisguiseVectors(TestCase):
    """The pierce penalty weights each essential item by its
    ``disguise_weight`` (default ``1``).  Non-essential items and
    overrides are unaffected.  Backward-compatible: any item or fake
    that omits the attribute behaves exactly as before.
    """

    def _make_target(self, worn=(), **overrides):
        target = _SignatureMockCharacter(worn_items=list(worn))
        # _SignatureMockCharacter ships with db.*_override = None; only
        # set what the caller asks for so the no-override baseline is
        # clean.
        for field, value in overrides.items():
            setattr(target.db, field, value)
        return target

    def test_no_essential_items_returns_zero(self) -> None:
        from world.identity import _count_disguise_vectors

        target = self._make_target()
        self.assertEqual(_count_disguise_vectors(target), 0)

    def test_default_weight_essential_items_count_one_each(self) -> None:
        """Items with no explicit ``disguise_weight`` use the default
        ``1`` — preserving the original contract."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="balaclava"
                ),
                _FakeDisguiseItem(
                    disguise_essential=True, disguise_type_id="trenchcoat"
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 2)

    def test_explicit_default_weight_matches_implicit(self) -> None:
        """Setting ``disguise_weight=1`` explicitly is a no-op."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="balaclava",
                    disguise_weight=1,
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 1)

    def test_heavy_concealment_weight_scales_penalty(self) -> None:
        """A full prosthetic mask weighted at 3 contributes 3 vectors."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="prosthetic_mask",
                    disguise_weight=3,
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 3)

    def test_zero_weight_essential_item_pins_signature_without_penalty(
        self,
    ) -> None:
        """Weight ``0`` lets an essential item still pin the identity
        signature elsewhere while contributing no pierce penalty."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="signature_pendant",
                    disguise_weight=0,
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 0)

    def test_non_essential_item_weight_is_ignored(self) -> None:
        """``disguise_weight`` on a non-essential item is ignored."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=False,
                    disguise_type_id="shirt",
                    disguise_weight=5,
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 0)

    def test_negative_weight_clamps_to_zero(self) -> None:
        """A negative weight is clamped to ``0`` rather than reducing
        other items' contributions or going below zero."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="oddity",
                    disguise_weight=-7,
                ),
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="balaclava",
                    disguise_weight=1,
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 1)

    def test_non_numeric_weight_falls_back_to_one(self) -> None:
        """A malformed weight ('heavy', None) falls back to ``1`` —
        never silently zero, so a bad attribute doesn't accidentally
        let a disguise through unpenalised."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="oddity",
                    disguise_weight="heavy",  # type: ignore[arg-type]
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 1)

    def test_mixed_weights_sum_correctly(self) -> None:
        """Multiple items with varying weights sum their contributions."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="prosthetic_mask",
                    disguise_weight=3,
                ),
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="signature_pendant",
                    disguise_weight=0,
                ),
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="trenchcoat",
                    # default weight 1
                ),
            ]
        )
        self.assertEqual(_count_disguise_vectors(target), 4)

    def test_overrides_add_one_each_regardless_of_item_weight(self) -> None:
        """The three string overrides each contribute exactly ``1``,
        independent of any item weights."""
        from world.identity import _count_disguise_vectors

        target = self._make_target(
            worn=[
                _FakeDisguiseItem(
                    disguise_essential=True,
                    disguise_type_id="prosthetic_mask",
                    disguise_weight=3,
                ),
            ],
            height_override="tall",
            build_override="slight",
            keyword_override="stranger",
        )
        # 3 (mask) + 1 + 1 + 1 (overrides) = 6
        self.assertEqual(_count_disguise_vectors(target), 6)
