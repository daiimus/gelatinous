"""
Tests for Identity-Aware Search (Identity Phase 2a).

Tests the pure utility functions in ``world.search`` and the
``Character.search()`` override that intercepts character targeting.

Run via::

    evennia test world.tests.test_identity_search

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md`` §Target Resolution.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from world.search import (
    identity_match_characters,
    is_identity_match,
    parse_ordinal,
    strip_leading_article,
)


# ===================================================================
# Helpers — lightweight character / object stand-in
# ===================================================================


def _make_character(
    *,
    key="Jorge Jackson",
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword=None,
    hair_color=None,
    hair_style=None,
    sleeve_uid="uid-abc-123",
    recognition_memory=None,
):
    """Build a mock character with identity attributes and bound methods."""
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.sex = sex
    char.height = height
    char.build = build
    char.sdesc_keyword = sdesc_keyword
    char.hair_color = hair_color
    char.hair_style = hair_style
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = (
        recognition_memory if recognition_memory is not None else {}
    )

    # Hands / clothing — defaults for sdesc composition
    char.hands = {"left": None, "right": None}
    char.worn_items = {}

    def _coverage_map():
        coverage = {}
        if char.worn_items:
            for loc, items in char.worn_items.items():
                if items:
                    coverage[loc] = items[0]
        return coverage

    char._build_clothing_coverage_map = _coverage_map

    # Bind real methods from Character class
    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(
            char, looker, **kw
        )
    )

    # gender property
    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    return char


def _make_item(key="Kitchen Knife"):
    """Return a minimal mock item without identity methods."""
    item = MagicMock()
    item.key = key
    # Items do NOT have get_sdesc — must not pass _has_identity()
    if hasattr(item, "get_sdesc"):
        del item.get_sdesc
    # Explicitly ensure no get_sdesc attribute
    item.get_sdesc = None  # Will make callable(getattr(...)) return False
    return item


def _make_plain_item(key="Kitchen Knife"):
    """Return a plain object that definitely has no get_sdesc."""
    item = MagicMock(spec=[])  # Empty spec — no attributes
    item.key = key
    return item


# ===================================================================
# Tests: strip_leading_article
# ===================================================================


class TestStripLeadingArticle(TestCase):
    """Tests for strip_leading_article()."""

    def test_strip_the(self):
        self.assertEqual(strip_leading_article("the tall man"), "tall man")

    def test_strip_a(self):
        self.assertEqual(strip_leading_article("a lanky woman"), "lanky woman")

    def test_strip_an(self):
        self.assertEqual(strip_leading_article("an athletic dame"), "athletic dame")

    def test_no_article(self):
        self.assertEqual(strip_leading_article("knife"), "knife")

    def test_the_only(self):
        # "the" alone — no remainder, returns original stripped
        self.assertEqual(strip_leading_article("the"), "the")

    def test_case_insensitive(self):
        self.assertEqual(strip_leading_article("The Tall Man"), "Tall Man")

    def test_whitespace(self):
        self.assertEqual(strip_leading_article("  a   lanky man  "), "lanky man")

    def test_empty(self):
        self.assertEqual(strip_leading_article(""), "")

    def test_article_in_middle_not_stripped(self):
        self.assertEqual(strip_leading_article("man in a coat"), "man in a coat")


# ===================================================================
# Tests: parse_ordinal
# ===================================================================


class TestParseOrdinal(TestCase):
    """Tests for parse_ordinal()."""

    def test_numeric_2nd(self):
        self.assertEqual(parse_ordinal("2nd tall man"), (2, "tall man"))

    def test_numeric_1st(self):
        self.assertEqual(parse_ordinal("1st man"), (1, "man"))

    def test_numeric_3rd(self):
        self.assertEqual(parse_ordinal("3rd woman"), (3, "woman"))

    def test_numeric_10th(self):
        self.assertEqual(parse_ordinal("10th person"), (10, "person"))

    def test_word_second(self):
        self.assertEqual(parse_ordinal("second tall man"), (2, "tall man"))

    def test_word_first(self):
        self.assertEqual(parse_ordinal("first man"), (1, "man"))

    def test_word_third(self):
        self.assertEqual(parse_ordinal("third person"), (3, "person"))

    def test_no_ordinal(self):
        self.assertEqual(parse_ordinal("tall man"), (None, "tall man"))

    def test_single_word_no_ordinal(self):
        self.assertEqual(parse_ordinal("man"), (None, "man"))

    def test_empty(self):
        self.assertEqual(parse_ordinal(""), (None, ""))

    def test_ordinal_zero_rejected(self):
        # 0th should not match (must be > 0)
        self.assertEqual(parse_ordinal("0th man"), (None, "0th man"))

    def test_whitespace(self):
        self.assertEqual(parse_ordinal("  2nd  man  "), (2, "man"))


# ===================================================================
# Tests: identity_match_characters
# ===================================================================


class TestIdentityMatchCharacters(TestCase):
    """Tests for identity_match_characters()."""

    def setUp(self):
        """Set up common test characters."""
        self.searcher = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-searcher",
        )

        # Jorge: tall lean man — sdesc "gaunt man"
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

        # Maria: short athletic woman — sdesc "compact woman"
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )

        # Viktor: above-average stocky droog — sdesc "brawny droog"
        self.viktor = _make_character(
            key="Viktor Kozlov",
            sex="male",
            height="above-average",
            build="stocky",
            sdesc_keyword="droog",
            sleeve_uid="uid-viktor",
        )

        self.candidates = [self.searcher, self.jorge, self.maria, self.viktor]

    def test_match_by_keyword(self):
        """'man' matches Jorge's sdesc keyword."""
        result = identity_match_characters(
            self.searcher, "man", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_match_by_partial_sdesc(self):
        """'gaunt' matches Jorge's physical descriptor."""
        result = identity_match_characters(
            self.searcher, "gaunt", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_match_by_full_sdesc(self):
        """'gaunt man' matches Jorge's full sdesc."""
        result = identity_match_characters(
            self.searcher, "gaunt man", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_match_by_assigned_name(self):
        """Assigned name 'Jorge' matches."""
        self.searcher.recognition_memory = {
            "uid-jorge": {"assigned_name": "Jorge"},
        }
        result = identity_match_characters(
            self.searcher, "jorge", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_assigned_name_takes_priority(self):
        """Assigned name matches come before sdesc matches."""
        self.searcher.recognition_memory = {
            "uid-jorge": {"assigned_name": "Big Guy"},
        }
        # "Big" would not match Jorge's sdesc, but matches assigned name
        result = identity_match_characters(
            self.searcher, "big guy", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_no_match(self):
        """Non-matching query returns empty list."""
        result = identity_match_characters(
            self.searcher, "zephyr", self.candidates
        )
        self.assertEqual(result, [])

    def test_searcher_excluded_from_results(self):
        """The searcher should never match themselves."""
        # Searcher's sdesc contains "compact" and "woman"
        self.searcher.sdesc_keyword = "woman"
        result = identity_match_characters(
            self.searcher, "compact woman", self.candidates
        )
        # Only Maria should match, not the searcher
        self.assertEqual(result, [self.maria])

    def test_multiple_matches(self):
        """Two characters with 'man' keyword both match."""
        # Viktor also uses "man" keyword
        self.viktor.sdesc_keyword = "man"
        result = identity_match_characters(
            self.searcher, "man", self.candidates
        )
        self.assertEqual(len(result), 2)
        self.assertIn(self.jorge, result)
        self.assertIn(self.viktor, result)

    def test_ordinal_selects_nth_match(self):
        """'2nd man' returns only the second matching character."""
        self.viktor.sdesc_keyword = "man"
        result = identity_match_characters(
            self.searcher, "2nd man", self.candidates
        )
        self.assertEqual(len(result), 1)
        # Jorge is first in candidates, Viktor second
        self.assertEqual(result[0], self.viktor)

    def test_ordinal_out_of_range(self):
        """'3rd man' with only 2 matches returns empty."""
        self.viktor.sdesc_keyword = "man"
        result = identity_match_characters(
            self.searcher, "3rd man", self.candidates
        )
        self.assertEqual(result, [])

    def test_leading_article_stripped(self):
        """'the man' matches after stripping 'the'."""
        result = identity_match_characters(
            self.searcher, "the man", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        result = identity_match_characters(
            self.searcher, "MAN", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_empty_query(self):
        result = identity_match_characters(
            self.searcher, "", self.candidates
        )
        self.assertEqual(result, [])

    def test_empty_candidates(self):
        result = identity_match_characters(
            self.searcher, "man", []
        )
        self.assertEqual(result, [])

    def test_items_ignored(self):
        """Non-identity objects (items) are skipped entirely."""
        item = _make_plain_item("Knife")
        candidates = [self.searcher, self.jorge, item]
        result = identity_match_characters(
            self.searcher, "knife", candidates
        )
        # Item should not appear in identity results
        self.assertEqual(result, [])

    def test_npc_without_identity_attrs_matches_via_sdesc_fallback(self):
        """An NPC without height/build falls back to .key as sdesc."""
        npc = _make_character(
            key="Bob",
            height=None,
            build=None,
            sleeve_uid="uid-npc-bob",
        )
        candidates = [self.searcher, npc]
        result = identity_match_characters(
            self.searcher, "bob", candidates
        )
        # get_sdesc() returns self.key when height/build missing
        self.assertEqual(result, [npc])

    def test_match_droog_keyword(self):
        """Setting-specific keyword 'droog' matches Viktor."""
        result = identity_match_characters(
            self.searcher, "droog", self.candidates
        )
        self.assertEqual(result, [self.viktor])

    def test_assigned_name_partial_match(self):
        """Partial assigned name match works (substring)."""
        self.searcher.recognition_memory = {
            "uid-jorge": {"assigned_name": "Jorge Jackson"},
        }
        result = identity_match_characters(
            self.searcher, "jorge", self.candidates
        )
        self.assertEqual(result, [self.jorge])

    def test_assigned_name_no_double_count(self):
        """A character matched by assigned name is not also added by sdesc."""
        self.searcher.recognition_memory = {
            "uid-jorge": {"assigned_name": "gaunt man"},
        }
        # "gaunt man" matches both assigned name AND sdesc —
        # should only appear once
        result = identity_match_characters(
            self.searcher, "gaunt man", self.candidates
        )
        self.assertEqual(result, [self.jorge])
        self.assertEqual(len(result), 1)


# ===================================================================
# Tests: is_identity_match
# ===================================================================


class TestIsIdentityMatch(TestCase):
    """Tests for is_identity_match()."""

    def setUp(self):
        self.searcher = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-searcher",
        )
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

    def test_sdesc_match_returns_true(self):
        self.assertTrue(
            is_identity_match(self.searcher, self.jorge, "man")
        )

    def test_assigned_name_match_returns_true(self):
        self.searcher.recognition_memory = {
            "uid-jorge": {"assigned_name": "Jorge"},
        }
        self.assertTrue(
            is_identity_match(self.searcher, self.jorge, "jorge")
        )

    def test_no_match_returns_false(self):
        self.assertFalse(
            is_identity_match(self.searcher, self.jorge, "zephyr")
        )

    def test_non_identity_object_always_allowed(self):
        """Items (without get_sdesc) always return True."""
        item = _make_plain_item("Knife")
        self.assertTrue(
            is_identity_match(self.searcher, item, "knife")
        )

    def test_real_key_blocked_without_recognition(self):
        """Targeting by real .key is blocked when not recognized."""
        self.assertFalse(
            is_identity_match(self.searcher, self.jorge, "jorge jackson")
        )

    def test_leading_article_handled(self):
        self.assertTrue(
            is_identity_match(self.searcher, self.jorge, "the man")
        )

    def test_ordinal_stripped_for_matching(self):
        self.assertTrue(
            is_identity_match(self.searcher, self.jorge, "1st man")
        )


# ===================================================================
# Tests: Character.search() override — Builder behaviour
# ===================================================================


class TestCharacterSearchBuilderBypass(TestCase):
    """Verify that Builders can target by sdesc AND .key.

    The identity pipeline must run for Builders (so ``look man`` works),
    but the fallback filter must allow ``.key`` results through (so
    ``look Jorge Jackson`` also works).

    Non-Builders must NOT be able to target by ``.key``.
    """

    def setUp(self):
        """Build a mock searcher, a target, and wire up search()."""
        from typeclasses.characters import Character

        self.target = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

        self.searcher = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-searcher",
        )

        # Give the searcher a real location with contents
        room = MagicMock()
        room.contents = [self.searcher, self.target]
        self.searcher.location = room

        # Wire up the real search method (bound to mock)
        self.searcher.search = (
            lambda *a, **kw: Character.search(self.searcher, *a, **kw)
        )

        # Mock msg so we can capture error messages
        self.searcher.msg = MagicMock()

    def _set_builder(self, is_builder: bool):
        """Configure the searcher's permission check."""
        self.searcher.check_permstring = MagicMock(return_value=is_builder)

    def _mock_super_search(self, results):
        """Patch DefaultObject.search to return *results* in quiet mode."""
        return patch(
            "evennia.objects.objects.DefaultObject.search",
            return_value=results,
        )

    # -- Builder can find by sdesc (identity pipeline runs) --

    def test_builder_finds_by_sdesc(self):
        """Builder typing 'look man' finds target via identity matching."""
        self._set_builder(True)
        result = self.searcher.search("man")
        self.assertEqual(result, self.target)

    def test_builder_finds_by_full_sdesc(self):
        """Builder typing 'look gaunt man' finds target via sdesc."""
        self._set_builder(True)
        result = self.searcher.search("gaunt man")
        self.assertEqual(result, self.target)

    # -- Builder can also find by .key (fallback, unfiltered) --

    def test_builder_finds_by_key(self):
        """Builder typing 'look Jorge Jackson' finds via .key fallback."""
        self._set_builder(True)
        with self._mock_super_search([self.target]):
            result = self.searcher.search("Jorge Jackson")
        self.assertEqual(result, self.target)

    # -- Non-builder CANNOT find by .key --

    def test_non_builder_blocked_by_key(self):
        """Normal player typing 'look Jorge Jackson' gets nothing."""
        self._set_builder(False)
        with self._mock_super_search([self.target]):
            result = self.searcher.search("Jorge Jackson")
        self.assertIsNone(result)
        # Should have received "Could not find" message
        self.searcher.msg.assert_called()

    # -- Non-builder CAN find by sdesc --

    def test_non_builder_finds_by_sdesc(self):
        """Normal player typing 'look man' finds target via identity."""
        self._set_builder(False)
        result = self.searcher.search("man")
        self.assertEqual(result, self.target)


# ===================================================================
# Tests: parse_ordinal — Evennia-native N.name format (Bug 3)
# ===================================================================


class TestParseOrdinalEvennia(TestCase):
    """Tests for Evennia-native ``N.name`` ordinal format."""

    def test_1_dot_man(self):
        """'1.man' → (1, 'man')."""
        self.assertEqual(parse_ordinal("1.man"), (1, "man"))

    def test_2_dot_tall_man(self):
        """'2.tall man' → (2, 'tall man')."""
        self.assertEqual(parse_ordinal("2.tall man"), (2, "tall man"))

    def test_3_dot_woman(self):
        """'3.woman' → (3, 'woman')."""
        self.assertEqual(parse_ordinal("3.woman"), (3, "woman"))

    def test_0_dot_man_rejected(self):
        """'0.man' — 0 is not a valid ordinal."""
        self.assertEqual(parse_ordinal("0.man"), (None, "0.man"))

    def test_evennia_ordinal_in_identity_match(self):
        """'1.man' resolves to first matching character."""
        searcher = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-searcher",
        )
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        candidates = [searcher, jorge]
        result = identity_match_characters(
            searcher, "1.man", candidates
        )
        self.assertEqual(result, [jorge])

    def test_evennia_ordinal_2_dot_man(self):
        """'2.man' resolves to second matching character."""
        searcher = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-searcher",
        )
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        viktor = _make_character(
            key="Viktor Kozlov",
            sex="male",
            height="above-average",
            build="stocky",
            sdesc_keyword="man",
            sleeve_uid="uid-viktor",
        )
        candidates = [searcher, jorge, viktor]
        result = identity_match_characters(
            searcher, "2.man", candidates
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], viktor)

    def test_is_identity_match_with_evennia_ordinal(self):
        """is_identity_match handles '1.man' correctly."""
        searcher = _make_character(
            key="Alice Smith",
            sex="female",
            sleeve_uid="uid-searcher",
        )
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.assertTrue(
            is_identity_match(searcher, jorge, "1.man")
        )
