"""Unit tests for the unified ``describe`` editor: combined list, short
description, and keyword nodes.

The ``describe`` command merges the former ``@longdesc``, ``@shortdesc``, and
Evennia ``setdesc`` surfaces into one flat EvMenu whose top-level list is::

    1  Short Description   (db.desc)
    2  Keyword             (sdesc_keyword)
    3..N  body-location longdesc slots
    x  Exit

These tests cover the combined-list numbering/rendering, the Short
Description node (set / clear / back / preview and the one-off
``describe short`` path), the Keyword node (numbered + named selection,
return-to-list behaviour, invalid input), and verify that Evennia's default
``setdesc`` is removed from the character cmdset.

Run via::

    evennia test world.tests.test_describe_menu
"""

from __future__ import annotations

from unittest import TestCase

from typeclasses.appearance_mixin import AppearanceMixin
from commands.CmdCharacter import (
    CmdDescribe,
    _build_longdesc_slots,
    _menu_apply_keyword,
    _node_describe_keyword,
    _node_describe_list,
    _node_describe_short,
    _process_describe_keyword,
    _process_describe_short,
)
from world.combat.constants import DEFAULT_LONGDESC_LOCATIONS


class _DB:
    skintone = None
    desc = ""


class _NDB:
    pass


class FakeChar(AppearanceMixin):
    """Lightweight host implementing the describe surface + real renderer.

    Provides the longdesc storage surface (as in ``test_longdesc_menu``) plus
    the short-description (``db.desc``) and keyword (``sdesc_keyword`` /
    ``get_sdesc``) surfaces the unified editor reads and mutates.
    """

    gender = "neutral"

    def __init__(self, locations=None, *, desc="", sdesc_keyword=None):
        self._longdesc = dict(locations or {})
        self.db = _DB()
        self.db.desc = desc
        self.ndb = _NDB()
        self.sdesc_keyword = sdesc_keyword
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


def _full_body(**kwargs):
    return FakeChar(DEFAULT_LONGDESC_LOCATIONS, **kwargs)


# =====================================================================
# Combined top-level list rendering
# =====================================================================


class ListNodeTests(TestCase):

    def test_short_description_is_item_one(self):
        char = _full_body(desc="a lanky figure")
        text, _ = _node_describe_list(char, "")
        self.assertIn("Short Description:", text)
        self.assertIn("a lanky figure", text)
        # The "1" marker precedes the Short Description label.
        self.assertLess(text.index(" 1"), text.index("Short Description:"))

    def test_empty_short_description_shows_placeholder(self):
        char = _full_body(desc="")
        text, _ = _node_describe_list(char, "")
        # Placeholder appears on the Short Description line.
        sd_line = next(
            ln for ln in text.splitlines() if "Short Description:" in ln
        )
        self.assertIn("(empty)", sd_line)

    def test_keyword_is_item_two_with_default_marker(self):
        char = _full_body(sdesc_keyword=None)
        text, _ = _node_describe_list(char, "")
        kw_line = next(ln for ln in text.splitlines() if "Keyword:" in ln)
        self.assertIn(" 2", kw_line)
        self.assertIn("(default)", kw_line)

    def test_keyword_shows_current_value(self):
        char = _full_body(sdesc_keyword="droog")
        text, _ = _node_describe_list(char, "")
        kw_line = next(ln for ln in text.splitlines() if "Keyword:" in ln)
        self.assertIn("droog", kw_line)
        self.assertNotIn("(default)", kw_line)

    def test_body_slots_start_at_three(self):
        char = _full_body()
        slots = _build_longdesc_slots(char)
        text, _ = _node_describe_list(char, "")
        # First body slot is numbered 3 (1=short, 2=keyword).
        first_slot = slots[0]
        slot_line = next(
            ln for ln in text.splitlines() if f"{first_slot}:" in ln
        )
        self.assertIn(" 3", slot_line)

    def test_exit_row_present(self):
        char = _full_body()
        text, _ = _node_describe_list(char, "")
        self.assertIn("Exit", text)
        exit_line = next(ln for ln in text.splitlines() if "Exit" in ln)
        self.assertIn("x", exit_line)


# =====================================================================
# Short Description node
# =====================================================================


class ShortDescNodeTests(TestCase):

    def test_set_stores_desc_and_returns_to_list(self):
        char = _full_body(desc="")
        result = _process_describe_short(char, "a weathered traveller")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.db.desc, "a weathered traveller")
        self.assertTrue(any("Preview" in m for m in char.messages))

    def test_clear_empties_desc(self):
        char = _full_body(desc="something")
        result = _process_describe_short(char, "clear")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.db.desc, "")
        self.assertTrue(any("Cleared" in m for m in char.messages))

    def test_back_returns_unchanged(self):
        char = _full_body(desc="original")
        result = _process_describe_short(char, "back")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.db.desc, "original")

    def test_blank_returns_unchanged(self):
        char = _full_body(desc="original")
        result = _process_describe_short(char, "   ")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.db.desc, "original")

    def test_node_shows_current_and_preview(self):
        char = _full_body(desc="a quiet figure")
        text, _ = _node_describe_short(char, "")
        self.assertIn("Short Description", text)
        self.assertIn("a quiet figure", text)
        self.assertIn("Preview", text)

    def test_one_off_set_short_stores_and_previews(self):
        char = _full_body(desc="")
        cmd = CmdDescribe()
        cmd.caller = char
        cmd._set_short(char, "a grizzled merc")
        self.assertEqual(char.db.desc, "a grizzled merc")
        self.assertTrue(any("Preview" in m for m in char.messages))


# =====================================================================
# Keyword node
# =====================================================================


class KeywordMenuTests(TestCase):

    def _char_with_keywords(self, keywords=("dude", "person", "punk")):
        char = _full_body(sdesc_keyword=None)
        char.ndb._shortdesc_keywords = sorted(keywords)
        char.ndb._shortdesc_gender = "neutral"
        return char

    def test_numbered_selection_applies_and_returns(self):
        char = self._char_with_keywords()
        # sorted -> ["dude", "person", "punk"]; choice "1" => "dude".
        result = _process_describe_keyword(char, "1")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.sdesc_keyword, "dude")

    def test_named_selection_applies(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "punk")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.sdesc_keyword, "punk")

    def test_named_selection_is_case_insensitive(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "PUNK")
        self.assertEqual(result, "node_describe_list")
        self.assertEqual(char.sdesc_keyword, "punk")

    def test_back_returns_to_list_unchanged(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "back")
        self.assertEqual(result, "node_describe_list")
        self.assertIsNone(char.sdesc_keyword)

    def test_out_of_range_number_redisplays(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "99")
        self.assertIsNone(result)
        self.assertIsNone(char.sdesc_keyword)
        self.assertTrue(any("Invalid number" in m for m in char.messages))

    def test_unknown_name_redisplays_with_custom_hint(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "zzyzx")
        self.assertIsNone(result)
        self.assertIsNone(char.sdesc_keyword)
        self.assertTrue(
            any("describe keyword" in m for m in char.messages)
        )

    def test_blank_redisplays(self):
        char = self._char_with_keywords()
        result = _process_describe_keyword(char, "")
        self.assertIsNone(result)

    def test_menu_apply_sets_keyword_and_confirms(self):
        char = _full_body(sdesc_keyword=None)
        _menu_apply_keyword(char, "droog")
        self.assertEqual(char.sdesc_keyword, "droog")
        self.assertTrue(any("droog" in m for m in char.messages))

    def test_menu_apply_reports_unchanged_when_same(self):
        char = _full_body(sdesc_keyword="droog")
        _menu_apply_keyword(char, "droog")
        self.assertEqual(char.sdesc_keyword, "droog")
        self.assertTrue(any("already" in m for m in char.messages))

    def test_node_renders_valid_keyword_catalog(self):
        # Exercises the DB-backed get_valid_keywords path (defaults under the
        # test runner). Neutral gender => all approved keywords available.
        char = _full_body(sdesc_keyword=None)
        text, _ = _node_describe_keyword(char, "")
        self.assertIn("Keyword", text)
        self.assertIsNotNone(getattr(char.ndb, "_shortdesc_keywords", None))
        self.assertTrue(len(char.ndb._shortdesc_keywords) > 0)


# =====================================================================
# Cmdset wiring — Evennia's setdesc is replaced by describe
# =====================================================================


class CmdsetWiringTests(TestCase):

    def test_describe_present_and_setdesc_removed(self):
        from commands.default_cmdsets import CharacterCmdSet

        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {cmd.key for cmd in cmdset.commands}
        self.assertIn("describe", keys)
        self.assertNotIn("setdesc", keys)

    def test_describe_has_no_aliases(self):
        cmd = CmdDescribe()
        self.assertEqual(cmd.key, "describe")
        self.assertEqual(list(cmd.aliases), [])
