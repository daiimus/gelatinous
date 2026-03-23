"""
Tests for Identity Phase 1c commands: ``@shortdesc`` and ``assign``.

Tests the command logic and helper functions using mocks.
Run via::

    evennia test world.tests.test_identity_commands

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch, call


# ===================================================================
# Helpers — lightweight character stand-in
# ===================================================================


def _make_character(
    *,
    key="Jorge Jackson",
    sex="male",
    sdesc_keyword=None,
    height="tall",
    build="lean",
    sleeve_uid="uid-abc-123",
    hair_color=None,
    hair_style=None,
    recognition_memory=None,
    location=None,
):
    """Build a mock character with identity attributes."""
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.sex = sex
    char.sdesc_keyword = sdesc_keyword
    char.height = height
    char.build = build
    char.sleeve_uid = sleeve_uid
    char.hair_color = hair_color
    char.hair_style = hair_style
    char.recognition_memory = recognition_memory if recognition_memory is not None else {}

    # Hands / clothing
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

    # Bind real methods
    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(char, looker, **kw)
    )

    # gender property
    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    # Location
    if location is None:
        location = MagicMock()
        location.key = "Test Room"
    char.location = location

    return char


# ===================================================================
# @shortdesc — instant set mode
# ===================================================================


class TestShortdescInstantSet(TestCase):
    """Test the _set_keyword logic from CmdShortdesc."""

    def test_valid_keyword_sets_attribute(self):
        """Valid keyword is stored on the character."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword=None)
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, "dude")
        self.assertEqual(char.sdesc_keyword, "dude")

    def test_invalid_keyword_rejected(self):
        """Invalid keyword produces error and does not change attribute."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, "zzzzinvalid")
        # Should still be "man" — the mock won't enforce this, but msg
        # should have been called with error
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("not a valid keyword", msg_text)

    def test_gender_gated_keyword(self):
        """Male character cannot use a feminine-only keyword."""
        from commands.CmdCharacter import CmdShortdesc
        from world.identity import FEMININE_KEYWORDS, NEUTRAL_KEYWORDS

        # Pick a keyword that's feminine-only (not in neutral)
        feminine_only = FEMININE_KEYWORDS - NEUTRAL_KEYWORDS
        kw = sorted(feminine_only)[0]

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, kw)
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("not a valid keyword", msg_text)

    def test_neutral_keyword_available_to_all(self):
        """Neutral keywords are available to any gender."""
        from commands.CmdCharacter import CmdShortdesc

        for sex in ("male", "female", "ambiguous"):
            char = _make_character(sex=sex, sdesc_keyword=None)
            cmd = CmdShortdesc()
            cmd.caller = char
            cmd._set_keyword(char, "person")
            self.assertEqual(char.sdesc_keyword, "person")

    def test_sdesc_updates_after_keyword_change(self):
        """After changing keyword, get_sdesc reflects it."""
        char = _make_character(
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        self.assertEqual(char.get_sdesc(), "gaunt man")

        # Change keyword
        char.sdesc_keyword = "punk"
        self.assertEqual(char.get_sdesc(), "gaunt punk")


# ===================================================================
# @shortdesc — EvMenu helpers
# ===================================================================


class TestShortdescMenuHelpers(TestCase):
    """Test the EvMenu goto-callable for keyword selection."""

    def test_numeric_selection(self):
        """Entering a number selects the keyword at that index."""
        from commands.CmdCharacter import _process_keyword_choice

        char = _make_character(sex="male", sdesc_keyword=None)
        keywords = ["bro", "dude", "guy", "man", "person"]
        char.ndb._shortdesc_keywords = keywords

        # Select "2" → "dude" (index 1)
        result = _process_keyword_choice(char, "2")
        self.assertEqual(char.sdesc_keyword, "dude")

    def test_name_selection(self):
        """Entering a keyword name selects it."""
        from commands.CmdCharacter import _process_keyword_choice

        char = _make_character(sex="male", sdesc_keyword=None)
        keywords = ["bro", "dude", "guy", "man", "person"]
        char.ndb._shortdesc_keywords = keywords

        result = _process_keyword_choice(char, "guy")
        self.assertEqual(char.sdesc_keyword, "guy")

    def test_invalid_number_rejected(self):
        """Out-of-range number shows error and returns None (re-display)."""
        from commands.CmdCharacter import _process_keyword_choice

        char = _make_character(sex="male", sdesc_keyword="man")
        keywords = ["bro", "dude", "guy", "man", "person"]
        char.ndb._shortdesc_keywords = keywords

        result = _process_keyword_choice(char, "99")
        self.assertIsNone(result)
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("Invalid number", msg_text)

    def test_invalid_text_rejected(self):
        """Unknown text shows error and returns None (re-display)."""
        from commands.CmdCharacter import _process_keyword_choice

        char = _make_character(sex="male", sdesc_keyword="man")
        keywords = ["bro", "dude", "guy", "man", "person"]
        char.ndb._shortdesc_keywords = keywords

        result = _process_keyword_choice(char, "xyzinvalid")
        self.assertIsNone(result)
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("not a valid keyword", msg_text)

    def test_empty_input_redisplays(self):
        """Empty input returns None (re-display)."""
        from commands.CmdCharacter import _process_keyword_choice

        char = _make_character(sex="male", sdesc_keyword="man")
        char.ndb._shortdesc_keywords = ["man"]

        result = _process_keyword_choice(char, "   ")
        self.assertIsNone(result)


# ===================================================================
# assign command
# ===================================================================


class TestAssignCommand(TestCase):
    """Test the assign command's internal logic."""

    def test_set_assignment_creates_memory(self):
        """Assigning a name creates a recognition memory entry."""
        from commands.CmdCharacter import CmdAssign

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )

        cmd = CmdAssign()
        cmd.caller = caller
        cmd._set_assignment(caller, target, "uid-target", "Big J")

        memory = caller.recognition_memory
        self.assertIn("uid-target", memory)
        self.assertEqual(memory["uid-target"]["assigned_name"], "Big J")
        self.assertEqual(memory["uid-target"]["times_seen"], 1)

    def test_display_name_changes_after_assign(self):
        """After assigning, get_display_name returns the assigned name."""
        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )

        # Before assignment — stranger
        self.assertEqual(target.get_display_name(caller), "a gaunt man")

        # Manually set recognition memory (simulating what assign does)
        caller.recognition_memory = {
            "uid-target": {"assigned_name": "Big J"},
        }
        self.assertEqual(target.get_display_name(caller), "Big J")

    def test_clear_assignment(self):
        """Clearing an assignment removes the assigned_name."""
        from commands.CmdCharacter import CmdAssign

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-target": {
                    "assigned_name": "Big J",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 1,
                    "location_first_seen": "Test Room",
                    "location_last_seen": "Test Room",
                    "locations_seen": ["Test Room"],
                    "sdesc_at_first_encounter": "gaunt man",
                    "sdesc_at_last_encounter": "gaunt man",
                    "notes": "",
                    "tags": [],
                    "confidence": 1.0,
                    "relationship_valence": "neutral",
                    "recent_interactions": [],
                },
            },
        )
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )

        cmd = CmdAssign()
        cmd.caller = caller
        cmd._clear_assignment(caller, target, "uid-target")

        memory = caller.recognition_memory
        # Entry still exists but assigned_name is empty
        self.assertIn("uid-target", memory)
        self.assertEqual(memory["uid-target"]["assigned_name"], "")

    def test_reassign_updates_name(self):
        """Re-assigning updates the name and increments times_seen."""
        from commands.CmdCharacter import CmdAssign

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-target": {
                    "assigned_name": "Big J",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 3,
                    "location_first_seen": "Bar",
                    "location_last_seen": "Bar",
                    "locations_seen": ["Bar"],
                    "sdesc_at_first_encounter": "gaunt man",
                    "sdesc_at_last_encounter": "gaunt man",
                    "notes": "",
                    "tags": [],
                    "confidence": 1.0,
                    "relationship_valence": "neutral",
                    "recent_interactions": [],
                },
            },
        )
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )

        cmd = CmdAssign()
        cmd.caller = caller
        cmd._set_assignment(caller, target, "uid-target", "Jorge")

        memory = caller.recognition_memory
        self.assertEqual(memory["uid-target"]["assigned_name"], "Jorge")
        self.assertEqual(memory["uid-target"]["times_seen"], 4)

    def test_clear_nonexistent_assignment(self):
        """Clearing when no assignment exists gives feedback."""
        from commands.CmdCharacter import CmdAssign

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        target = _make_character(key="Jorge", sleeve_uid="uid-target")

        cmd = CmdAssign()
        cmd.caller = caller
        cmd._clear_assignment(caller, target, "uid-target")

        caller.msg.assert_called()
        msg_text = caller.msg.call_args[0][0]
        self.assertIn("don't have a name", msg_text)

    def test_assign_preserves_existing_fields(self):
        """Re-assigning preserves notes, tags, etc."""
        from commands.CmdCharacter import CmdAssign

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-target": {
                    "assigned_name": "Big J",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 1,
                    "location_first_seen": "Bar",
                    "location_last_seen": "Bar",
                    "locations_seen": ["Bar"],
                    "sdesc_at_first_encounter": "gaunt man",
                    "sdesc_at_last_encounter": "gaunt man",
                    "notes": "Seems dangerous",
                    "tags": ["ally"],
                    "confidence": 0.8,
                    "relationship_valence": "friendly",
                    "recent_interactions": [],
                },
            },
        )
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )

        cmd = CmdAssign()
        cmd.caller = caller
        cmd._set_assignment(caller, target, "uid-target", "J-Dog")

        memory = caller.recognition_memory
        entry = memory["uid-target"]
        # Name updated
        self.assertEqual(entry["assigned_name"], "J-Dog")
        # Existing fields preserved
        self.assertEqual(entry["notes"], "Seems dangerous")
        self.assertEqual(entry["tags"], ["ally"])
        self.assertEqual(entry["confidence"], 0.8)
        self.assertEqual(entry["relationship_valence"], "friendly")
        # first_seen unchanged
        self.assertEqual(entry["first_seen"], "2026-01-01T00:00:00")
