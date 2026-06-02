"""Unit tests for the ``describe`` longdesc helpers and editor nodes.

Covers slot construction (pair collapse, asymmetric sides, extended anatomy,
anatomical ordering), slot-value reporting (matching vs diverged pairs),
pair expansion, the rendered preview (plural + singular + stray-token
warning), and the menu node goto-callables (top-level routing and entry
application, including ``clear``/``back``/length-guard paths).

Run via::

    evennia test world.tests.test_longdesc_menu
"""

from __future__ import annotations

from unittest import TestCase

from typeclasses.appearance_mixin import AppearanceMixin
from commands.CmdCharacter import (
    _build_longdesc_slots,
    _expand_longdesc_pair,
    _longdesc_slot_value,
    _node_longdesc_entry,
    _node_longdesc_exit,
    _process_describe_choice,
    _process_longdesc_entry,
    _render_longdesc_preview,
)
from world.combat.constants import (
    DEFAULT_LONGDESC_LOCATIONS,
    MAX_DESCRIPTION_LENGTH,
)


class _DB:
    skintone = None
    desc = ""


class _NDB:
    pass


class FakeChar(AppearanceMixin):
    """Lightweight host implementing the longdesc surface + real renderer."""

    gender = "neutral"
    sdesc_keyword = None

    def __init__(self, locations):
        self._longdesc = dict(locations)
        self.db = _DB()
        self.ndb = _NDB()
        self.messages = []

    # --- longdesc storage surface -------------------------------------
    def get_available_locations(self):
        return list(self._longdesc.keys())

    def has_location(self, loc):
        return loc in self._longdesc

    def get_longdesc(self, loc):
        return self._longdesc.get(loc)

    def set_longdesc(self, loc, desc):
        if loc not in self._longdesc:
            return False
        self._longdesc[loc] = desc
        return True

    # --- identity surface ---------------------------------------------
    def get_display_name(self, looker):
        return "Vasquez"

    def get_sdesc(self):
        return f"a {self.sdesc_keyword or 'person'}"

    def msg(self, text):
        self.messages.append(text)


def _full_body():
    return FakeChar(DEFAULT_LONGDESC_LOCATIONS)


class BuildSlotsTests(TestCase):

    def test_symmetric_pairs_collapse_to_shorthand(self):
        slots = _build_longdesc_slots(_full_body())
        self.assertIn("eyes", slots)
        self.assertIn("hands", slots)
        self.assertNotIn("left_eye", slots)
        self.assertNotIn("right_eye", slots)

    def test_non_pair_locations_present(self):
        slots = _build_longdesc_slots(_full_body())
        for loc in ("hair", "head", "face", "neck", "chest", "back", "groin"):
            self.assertIn(loc, slots)

    def test_anatomical_ordering(self):
        slots = _build_longdesc_slots(_full_body())
        # hair leads; eyes shorthand sits where the eyes do; feet trails.
        self.assertEqual(slots[0], "hair")
        self.assertLess(slots.index("eyes"), slots.index("chest"))
        self.assertLess(slots.index("chest"), slots.index("feet"))

    def test_asymmetric_pair_shows_single_side(self):
        char = FakeChar({"left_eye": None, "head": None})
        slots = _build_longdesc_slots(char)
        self.assertIn("left_eye", slots)
        self.assertNotIn("eyes", slots)

    def test_extended_anatomy_appended(self):
        char = FakeChar({"head": None, "tail": None, "left_wing": None})
        slots = _build_longdesc_slots(char)
        self.assertIn("tail", slots)
        self.assertIn("left_wing", slots)
        # Extended anatomy comes after known anatomical-order entries.
        self.assertLess(slots.index("head"), slots.index("tail"))


class SlotValueTests(TestCase):

    def test_matching_pair_collapses(self):
        char = FakeChar({"left_eye": "brown eye", "right_eye": "brown eye"})
        value, diverged = _longdesc_slot_value(char, "eyes")
        self.assertEqual(value, "brown eye")
        self.assertFalse(diverged)

    def test_diverged_pair_flagged(self):
        char = FakeChar({"left_eye": "brown eye", "right_eye": "blue eye"})
        value, diverged = _longdesc_slot_value(char, "eyes")
        self.assertTrue(diverged)
        self.assertIn(value, ("brown eye", "blue eye"))

    def test_single_location(self):
        char = FakeChar({"face": "a scarred face"})
        value, diverged = _longdesc_slot_value(char, "face")
        self.assertEqual(value, "a scarred face")
        self.assertFalse(diverged)


class ExpandPairTests(TestCase):

    def test_symmetric_pair_expands(self):
        char = _full_body()
        self.assertEqual(
            _expand_longdesc_pair(char, "eyes"), ["left_eye", "right_eye"]
        )

    def test_single_location(self):
        char = _full_body()
        self.assertEqual(_expand_longdesc_pair(char, "face"), ["face"])

    def test_invalid_location(self):
        char = _full_body()
        self.assertIsNone(_expand_longdesc_pair(char, "antenna"))

    def test_asymmetric_pair_rejected(self):
        char = FakeChar({"left_eye": None})
        self.assertIsNone(_expand_longdesc_pair(char, "eyes"))


class PreviewTests(TestCase):

    def test_pair_shows_plural_and_singular(self):
        char = _full_body()
        lines = _render_longdesc_preview(
            char, char, "eyes", ["left_eye", "right_eye"],
            "{Their} bright brown {eyes} {accent} {their} skin.",
        )
        joined = "\n".join(lines)
        self.assertIn("brown eyes accent", joined)
        self.assertIn("brown eye accents", joined)

    def test_single_location_singular_only(self):
        char = _full_body()
        lines = _render_longdesc_preview(
            char, char, "face", ["face"], "a weathered {face}",
        )
        # "face" is not a pair noun -> treated as verb-ish flex, but render
        # must succeed and show exactly one preview body line.
        body_lines = [ln for ln in lines if not ln.startswith("|WPreview")]
        self.assertEqual(len(body_lines), 1)

    def test_unrecognized_token_warned(self):
        # The token engine verb-flexes unknown *single* words, so only a
        # genuinely-literal token (multi-word, non-article) survives in braces
        # and triggers the explicit warning.
        char = _full_body()
        lines = _render_longdesc_preview(
            char, char, "face", ["face"], "a face shaped by {the old days}",
        )
        joined = "\n".join(lines)
        self.assertIn("Unrecognized token", joined)
        self.assertIn("{the old days}", joined)

    def test_clean_prose_no_warning(self):
        char = _full_body()
        lines = _render_longdesc_preview(
            char, char, "face", ["face"], "a weathered face",
        )
        joined = "\n".join(lines)
        self.assertNotIn("Unrecognized token", joined)


class SlotSelectionTests(TestCase):

    def _char_with_slots(self):
        char = _full_body()
        char.ndb._longdesc_slots = _build_longdesc_slots(char)
        return char

    def test_short_description_choice_routes_to_short_node(self):
        char = self._char_with_slots()
        result = _process_describe_choice(char, "1")
        self.assertEqual(result, "node_describe_short")

    def test_keyword_choice_routes_to_keyword_node(self):
        char = self._char_with_slots()
        result = _process_describe_choice(char, "2")
        self.assertEqual(result, "node_describe_keyword")

    def test_valid_number_targets_slot(self):
        char = self._char_with_slots()
        # Slots begin at 3 (1=short desc, 2=keyword).
        result = _process_describe_choice(char, "3")
        self.assertEqual(result, "node_longdesc_entry")
        self.assertEqual(char.ndb._longdesc_active_slot, char.ndb._longdesc_slots[0])

    def test_out_of_range_redisplays(self):
        char = self._char_with_slots()
        result = _process_describe_choice(char, "999")
        self.assertIsNone(result)
        self.assertTrue(any("Invalid number" in m for m in char.messages))

    def test_non_numeric_redisplays(self):
        char = self._char_with_slots()
        result = _process_describe_choice(char, "eyes")
        self.assertIsNone(result)

    def test_exit_choice_routes_to_end_node(self):
        char = self._char_with_slots()
        result = _process_describe_choice(char, "x")
        self.assertEqual(result, "node_longdesc_exit")
        self.assertFalse(hasattr(char.ndb, "_longdesc_active_slot"))

    def test_exit_node_has_no_options(self):
        # A node returning None options makes EvMenu close without re-display.
        char = self._char_with_slots()
        text, options = _node_longdesc_exit(char, "")
        self.assertIsNone(options)


class EntryApplicationTests(TestCase):

    def _char_editing(self, slot):
        char = _full_body()
        char.ndb._longdesc_slots = _build_longdesc_slots(char)
        char.ndb._longdesc_active_slot = slot
        return char

    def test_set_fans_out_to_both_sides(self):
        char = self._char_editing("eyes")
        result = _process_longdesc_entry(char, "brown {eyes}")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.get_longdesc("left_eye"), "brown {eyes}")
        self.assertEqual(char.get_longdesc("right_eye"), "brown {eyes}")
        self.assertTrue(any("Preview" in m for m in char.messages))

    def test_clear_removes_both_sides(self):
        char = self._char_editing("eyes")
        char.set_longdesc("left_eye", "x")
        char.set_longdesc("right_eye", "x")
        result = _process_longdesc_entry(char, "clear")
        self.assertEqual(result, "node_describe_list")
        self.assertIsNone(char.get_longdesc("left_eye"))
        self.assertIsNone(char.get_longdesc("right_eye"))

    def test_back_returns_unchanged(self):
        char = self._char_editing("face")
        char.set_longdesc("face", "original")
        result = _process_longdesc_entry(char, "back")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.get_longdesc("face"), "original")

    def test_blank_returns_unchanged(self):
        char = self._char_editing("face")
        char.set_longdesc("face", "original")
        result = _process_longdesc_entry(char, "   ")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.get_longdesc("face"), "original")

    def test_too_long_redisplays_entry(self):
        char = self._char_editing("face")
        result = _process_longdesc_entry(char, "x" * (MAX_DESCRIPTION_LENGTH + 1))
        self.assertIsNone(result)
        self.assertTrue(any("too long" in m.lower() for m in char.messages))
        self.assertIsNone(char.get_longdesc("face"))

    def test_entry_node_returns_to_list_without_slot(self):
        char = _full_body()
        char.ndb._longdesc_slots = _build_longdesc_slots(char)
        # No active slot set: node falls back to rendering the list.
        text, options = _node_longdesc_entry(char, "")
        self.assertIn("Select a number to edit", text)
