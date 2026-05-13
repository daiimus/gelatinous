"""
Tests for Identity Phase 1c commands: ``@shortdesc`` and the memory
verb cluster (``remember``, ``forget``, ``recall``, ``memory``).

Tests the command logic and helper functions using mocks.
Run via::

    evennia test world.tests.test_identity_commands

All test cases match the specification in
``specs/IDENTITY_RECOGNITION_SPEC.md``.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch, call

from world.tests._identity_helpers import (
    apparent_uid_for,
    prepare_mock_for_apparent_uid,
)


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

    # get_worn_items: empty by default so get_essential_item_type_ids()
    # produces an empty tuple.  Tests that need essentials override
    # this via _equip_essential_items() below.
    char.get_worn_items = MagicMock(return_value=[])

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

    prepare_mock_for_apparent_uid(char)
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
        """Non-alpha keyword produces error and does not change attribute."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, "cyber2punk")
        # Should still be "man"
        self.assertEqual(char.sdesc_keyword, "man")
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("not a valid keyword", msg_text)

    def test_gender_gated_keyword(self):
        """Male character cannot use a feminine-only keyword."""
        from commands.CmdCharacter import CmdShortdesc
        from world.identity import (
            _DEFAULT_FEMININE_KEYWORDS,
            _DEFAULT_NEUTRAL_KEYWORDS,
        )

        # Pick a keyword that's feminine-only (not in neutral)
        feminine_only = _DEFAULT_FEMININE_KEYWORDS - _DEFAULT_NEUTRAL_KEYWORDS
        kw = sorted(feminine_only)[0]

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, kw)
        # Should still be "man"
        self.assertEqual(char.sdesc_keyword, "man")
        char.msg.assert_called()
        msg_text = char.msg.call_args[0][0]
        self.assertIn("not available", msg_text)

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
# remember command
# ===================================================================


class TestRememberCommand(TestCase):
    """Test the remember command's internal logic."""

    def test_remember_target_creates_memory(self):
        """Remembering someone creates a recognition memory entry."""
        from commands.CmdCharacter import CmdRemember

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)

        cmd = CmdRemember()
        cmd.caller = caller
        cmd._remember_target(caller, target, target_uid, "Big J")

        memory = caller.recognition_memory
        self.assertIn(target_uid, memory)
        self.assertEqual(memory[target_uid]["assigned_name"], "Big J")
        self.assertEqual(memory[target_uid]["times_seen"], 1)

    def test_display_name_changes_after_remember(self):
        """After remembering, get_display_name returns the chosen name."""
        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)

        # Before — stranger
        self.assertEqual(target.get_display_name(caller), "a gaunt man")

        # Manually set recognition memory (simulating what remember does)
        caller.recognition_memory = {
            target_uid: {"assigned_name": "Big J"},
        }
        self.assertEqual(target.get_display_name(caller), "Big J")

    def test_re_remember_updates_name(self):
        """Re-remembering updates the name and increments times_seen."""
        from commands.CmdCharacter import CmdRemember

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                target_uid: {
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
                    "lost_contact": False,
                },
            },
        )

        cmd = CmdRemember()
        cmd.caller = caller
        cmd._remember_target(caller, target, target_uid, "Jorge")

        memory = caller.recognition_memory
        self.assertEqual(memory[target_uid]["assigned_name"], "Jorge")
        self.assertEqual(memory[target_uid]["times_seen"], 4)

    def test_remember_preserves_existing_fields(self):
        """Re-remembering preserves notes, tags, etc."""
        from commands.CmdCharacter import CmdRemember

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                target_uid: {
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
                    "lost_contact": False,
                },
            },
        )

        cmd = CmdRemember()
        cmd.caller = caller
        cmd._remember_target(caller, target, target_uid, "J-Dog")

        memory = caller.recognition_memory
        entry = memory[target_uid]
        self.assertEqual(entry["assigned_name"], "J-Dog")
        self.assertEqual(entry["notes"], "Seems dangerous")
        self.assertEqual(entry["tags"], ["ally"])
        self.assertEqual(entry["confidence"], 0.8)
        self.assertEqual(entry["relationship_valence"], "friendly")
        self.assertEqual(entry["first_seen"], "2026-01-01T00:00:00")


# ===================================================================
# forget command
# ===================================================================


def _seed_memory(uid="uid-target", name="Big J"):
    """Build a populated recognition_memory dict for a single target."""
    return {
        uid: {
            "assigned_name": name,
            "first_seen": "2026-01-01T00:00:00",
            "last_seen": "2026-01-01T00:00:00",
            "times_seen": 2,
            "location_first_seen": "The Grit",
            "location_last_seen": "Back Alley",
            "locations_seen": ["The Grit", "Back Alley"],
            "sdesc_at_first_encounter": "a gaunt man",
            "sdesc_at_last_encounter": "a gaunt man in a hood",
            "notes": "",
            "tags": [],
            "confidence": 1.0,
            "relationship_valence": "neutral",
            "recent_interactions": [],
            "lost_contact": False,
        },
    }


class TestForgetCommand(TestCase):
    """Test the forget command."""

    def test_forget_visible_target_clears_name(self):
        """forget <visible target> blanks assigned_name, preserves entry."""
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=_seed_memory(uid=target_uid),
        )

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, target_uid)

        memory = caller.recognition_memory
        self.assertIn(target_uid, memory)
        self.assertEqual(memory[target_uid]["assigned_name"], "")
        # History preserved
        self.assertEqual(memory[target_uid]["times_seen"], 2)
        self.assertEqual(
            memory[target_uid]["sdesc_at_first_encounter"], "a gaunt man"
        )

    def test_forget_remembered_name_when_target_absent(self):
        """forget <remembered name> works without target object."""
        from commands.CmdCharacter import CmdForget, _find_remembered_uid_by_name

        # Build a target only to derive its apparent UID for seeding.
        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=_seed_memory(uid=target_uid),
        )

        sleeve_uid, entry = _find_remembered_uid_by_name(caller, "big j")
        self.assertEqual(sleeve_uid, target_uid)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_remembered(caller, sleeve_uid, entry)

        memory = caller.recognition_memory
        self.assertEqual(memory[target_uid]["assigned_name"], "")
        # Output message references snapshot data
        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Big J", msg_text)
        self.assertIn("Back Alley", msg_text)

    def test_forget_unknown_name(self):
        """forget <unknown name> with empty memory rejects gracefully."""
        from commands.CmdCharacter import _find_remembered_uid_by_name

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        sleeve_uid, entry = _find_remembered_uid_by_name(caller, "ghost")
        self.assertIsNone(sleeve_uid)
        self.assertIsNone(entry)

    def test_forget_visible_with_no_assigned_name(self):
        """forget on someone with a blank assigned_name reports correctly."""
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        memory = _seed_memory(uid=target_uid)
        memory[target_uid]["assigned_name"] = ""
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, target_uid)

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("don't have a name", msg_text)


# ===================================================================
# recall command
# ===================================================================


class TestRecallCommand(TestCase):
    """Test the recall command."""

    def test_recall_renders_full_entry(self):
        """recall outputs assigned name, first sdesc, location, when, count."""
        from commands.CmdCharacter import CmdRecall

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=_seed_memory(),
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(caller, caller.recognition_memory["uid-target"])

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Big J", msg_text)
        self.assertIn("a gaunt man", msg_text)
        self.assertIn("The Grit", msg_text)
        self.assertIn("seen 2 times", msg_text)

    def test_recall_blank_assigned_name_shows_unnamed_message(self):
        """Entry with blank assigned_name renders the 'no name' header."""
        from commands.CmdCharacter import CmdRecall

        memory = _seed_memory()
        memory["uid-target"]["assigned_name"] = ""
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(caller, memory["uid-target"])

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("don't have a name", msg_text)
        # Snapshot still rendered
        self.assertIn("a gaunt man", msg_text)

    def test_recall_singular_seen_count(self):
        """times_seen of 1 renders 'time' (singular), not 'times'."""
        from commands.CmdCharacter import CmdRecall

        memory = _seed_memory()
        memory["uid-target"]["times_seen"] = 1
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(caller, memory["uid-target"])

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("seen 1 time", msg_text)
        self.assertNotIn("seen 1 times", msg_text)


# ===================================================================
# memory command
# ===================================================================


class TestMemoryCommand(TestCase):
    """Test the memory command."""

    def test_memory_empty(self):
        """memory with no entries reports the empty state."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("don't remember anyone", msg_text)

    def test_memory_lists_named_entries(self):
        """memory lists each entry with a non-blank assigned_name."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-a": {
                    "assigned_name": "Alice",
                    "last_seen": "2026-05-10T00:00:00",
                    "sdesc_at_last_encounter": "a tall woman",
                    "location_last_seen": "Bar",
                },
                "uid-b": {
                    "assigned_name": "Bob",
                    "last_seen": "2026-05-12T00:00:00",
                    "sdesc_at_last_encounter": "a short man",
                    "location_last_seen": "Alley",
                },
            },
        )
        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Alice", msg_text)
        self.assertIn("Bob", msg_text)

    def test_memory_excludes_blank_names(self):
        """Entries with blank assigned_name are excluded from listing."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-a": {
                    "assigned_name": "Alice",
                    "last_seen": "2026-05-10T00:00:00",
                    "sdesc_at_last_encounter": "a tall woman",
                    "location_last_seen": "Bar",
                },
                "uid-b": {
                    "assigned_name": "",  # forgotten
                    "last_seen": "2026-05-12T00:00:00",
                    "sdesc_at_last_encounter": "a short man",
                    "location_last_seen": "Alley",
                },
            },
        )
        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Alice", msg_text)
        self.assertNotIn("a short man", msg_text)

    def test_memory_recency_sort(self):
        """Entries sort by last_seen descending."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-old": {
                    "assigned_name": "Older",
                    "last_seen": "2026-01-01T00:00:00",
                    "sdesc_at_last_encounter": "x",
                    "location_last_seen": "y",
                },
                "uid-new": {
                    "assigned_name": "Newer",
                    "last_seen": "2026-12-01T00:00:00",
                    "sdesc_at_last_encounter": "x",
                    "location_last_seen": "y",
                },
            },
        )
        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        # Newer should appear before Older in the rendered table
        self.assertLess(msg_text.index("Newer"), msg_text.index("Older"))

    def test_memory_rejects_arguments(self):
        """memory with args returns a usage hint."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = "something"
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Usage: memory", msg_text)


# ===================================================================
# @shortdesc — custom keyword acceptance
# ===================================================================


class TestShortdescCustomKeyword(TestCase):
    """Test that @shortdesc accepts arbitrary valid custom keywords."""

    def test_custom_keyword_accepted(self):
        """A novel alpha-only word is accepted as a custom keyword."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        with patch("world.identity.log_custom_keyword") as mock_log:
            cmd._set_keyword(char, "ronin")
        self.assertEqual(char.sdesc_keyword, "ronin")
        mock_log.assert_called_once_with(
            "ronin", char.key, account=char.account,
        )

    def test_custom_keyword_not_logged_for_approved(self):
        """Approved keywords bypass the catalog entirely."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        with patch("world.identity.log_custom_keyword") as mock_log:
            cmd._set_keyword(char, "dude")
        self.assertEqual(char.sdesc_keyword, "dude")
        mock_log.assert_not_called()

    def test_custom_keyword_rejected_with_digits(self):
        """Keywords containing digits are rejected."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, "r0nin")
        self.assertEqual(char.sdesc_keyword, "man")
        msg_text = char.msg.call_args[0][0]
        self.assertIn("letters", msg_text)

    def test_custom_keyword_rejected_too_short(self):
        """Single-character keyword is rejected."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(sex="male", sdesc_keyword="man")
        cmd = CmdShortdesc()
        cmd.caller = char
        cmd._set_keyword(char, "x")
        self.assertEqual(char.sdesc_keyword, "man")

    def test_custom_keyword_shows_sdesc(self):
        """Confirmation message includes updated sdesc."""
        from commands.CmdCharacter import CmdShortdesc

        char = _make_character(
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        cmd = CmdShortdesc()
        cmd.caller = char
        with patch("world.identity.log_custom_keyword"):
            cmd._set_keyword(char, "samurai")
        # sdesc_keyword should be updated
        self.assertEqual(char.sdesc_keyword, "samurai")
        msg_text = char.msg.call_args[0][0]
        self.assertIn("samurai", msg_text)


# ===================================================================
# Custom keyword catalog — log_custom_keyword
# ===================================================================


class TestLogCustomKeyword(TestCase):
    """Test event logging via :func:`log_custom_keyword`."""

    def _mock_keyword_event(self):
        """Return a mock ``world.models`` module with KeywordEvent stub.

        ``world.models`` can't be imported during default-settings tests
        (``world`` isn't in INSTALLED_APPS for the test runner).  We
        inject a fake module into ``sys.modules`` instead.
        """
        mock_module = MagicMock()
        mock_create = mock_module.KeywordEvent.objects.create
        return mock_module, mock_create

    def test_custom_keyword_logged(self):
        """Novel keyword creates a KeywordEvent record."""
        from world.identity import log_custom_keyword

        mock_module, mock_create = self._mock_keyword_event()

        with patch.dict("sys.modules", {"world.models": mock_module}):
            with patch(
                "world.identity.get_all_keywords", return_value=frozenset()
            ):
                log_custom_keyword("ronin", "Alice")

        mock_create.assert_called_once_with(
            event_type="custom_set",
            keyword="ronin",
            character_name="Alice",
            account_name="",
        )

    def test_custom_keyword_logged_with_account(self):
        """Account name is included when account is provided."""
        from world.identity import log_custom_keyword

        mock_module, mock_create = self._mock_keyword_event()

        account = MagicMock()
        account.key = "player1"

        with patch.dict("sys.modules", {"world.models": mock_module}):
            with patch(
                "world.identity.get_all_keywords", return_value=frozenset()
            ):
                log_custom_keyword("ronin", "Alice", account=account)

        mock_create.assert_called_once_with(
            event_type="custom_set",
            keyword="ronin",
            character_name="Alice",
            account_name="player1",
        )

    def test_approved_keyword_not_logged(self):
        """Keywords from the approved lists are silently ignored."""
        from world.identity import log_custom_keyword

        mock_module, mock_create = self._mock_keyword_event()

        with patch.dict("sys.modules", {"world.models": mock_module}):
            with patch(
                "world.identity.get_all_keywords",
                return_value=frozenset({"man"}),
            ):
                log_custom_keyword("man", "Alice")

        mock_create.assert_not_called()

    def test_multiple_keywords_each_logged(self):
        """Multiple distinct keywords each create their own event."""
        from world.identity import log_custom_keyword

        mock_module, mock_create = self._mock_keyword_event()

        with patch.dict("sys.modules", {"world.models": mock_module}):
            with patch(
                "world.identity.get_all_keywords", return_value=frozenset()
            ):
                log_custom_keyword("ronin", "Alice")
                log_custom_keyword("wraith", "Bob")

        self.assertEqual(mock_create.call_count, 2)


# ===================================================================
# Disguise — appear / persona cluster helpers
# ===================================================================


def _make_disguise_character(**overrides):
    """``_make_character`` plus pre-zeroed disguise/persona ``db`` attrs.

    The new commands rely on ``caller.db.height_override is None`` style
    checks; bare ``MagicMock`` access would yield a child mock instead
    of ``None``.  We seed the relevant ``db`` slots and the ``personas``
    dict so each test starts from a clean baseline.
    """
    db_overrides = overrides.pop("db_attrs", {})
    char = _make_character(**overrides)

    # Persona/override storage attrs default to None / empty dict.
    defaults = {
        "height_override": None,
        "build_override": None,
        "keyword_override": None,
        "active_persona": None,
        "personas": None,
    }
    defaults.update(db_overrides)
    for attr, value in defaults.items():
        setattr(char.db, attr, value)
    return char


def _equip_essential_items(char, type_ids):
    """Make ``char.get_worn_items()`` return mocks for the given type IDs.

    Each fake worn item has ``disguise_essential = True`` and a
    ``disguise_type_id`` from the list.  Pass an empty list to reset.
    """
    items = []
    for type_id in type_ids:
        item = MagicMock()
        item.disguise_essential = True
        item.disguise_type_id = type_id
        items.append(item)
    char.get_worn_items = MagicMock(return_value=items)
    return char


# ===================================================================
# CmdAppear — bare status display
# ===================================================================


class TestCmdAppearStatus(TestCase):
    """``appear`` with no args renders current overrides + persona."""

    def _run(self, caller):
        from commands.CmdCharacter import CmdAppear

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()
        return caller.msg.call_args[0][0]

    def test_no_overrides_reports_clean_state(self):
        caller = _make_disguise_character(
            height="tall", build="lean", sdesc_keyword="man"
        )
        msg = self._run(caller)
        self.assertIn("tall", msg)
        self.assertIn("lean", msg)
        self.assertIn("man", msg)
        self.assertIn("No presentation overrides active", msg)

    def test_active_persona_appears_in_status(self):
        caller = _make_disguise_character(
            height="tall", build="lean", sdesc_keyword="man",
            db_attrs={
                "height_override": "average",
                "active_persona": "Hooded Wanderer",
            },
        )
        msg = self._run(caller)
        self.assertIn("average", msg)
        self.assertIn("Hooded Wanderer", msg)
        self.assertIn("real:", msg)


# ===================================================================
# CmdAppear — axis nudges
# ===================================================================


class TestCmdAppearAxes(TestCase):
    """``appear taller/shorter/thinner/fatter`` step the axis."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdAppear

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = args
        cmd.func()

    def test_taller_steps_height_up(self):
        from world.identity import HEIGHTS

        caller = _make_disguise_character(height="average")
        self._run(caller, "taller")
        expected = HEIGHTS[HEIGHTS.index("average") + 1]
        self.assertEqual(caller.db.height_override, expected)

    def test_shorter_steps_height_down(self):
        from world.identity import HEIGHTS

        caller = _make_disguise_character(height="average")
        self._run(caller, "shorter")
        expected = HEIGHTS[HEIGHTS.index("average") - 1]
        self.assertEqual(caller.db.height_override, expected)

    def test_taller_at_max_refuses(self):
        from world.identity import HEIGHTS

        caller = _make_disguise_character(height=HEIGHTS[-1])
        self._run(caller, "taller")
        self.assertIsNone(caller.db.height_override)
        msg = caller.msg.call_args[0][0]
        self.assertIn("can't appear any taller", msg)

    def test_fatter_steps_build_up(self):
        from world.identity import BUILDS

        caller = _make_disguise_character(build="average")
        self._run(caller, "fatter")
        expected = BUILDS[BUILDS.index("average") + 1]
        self.assertEqual(caller.db.build_override, expected)

    def test_thinner_steps_build_down(self):
        from world.identity import BUILDS

        caller = _make_disguise_character(build="average")
        self._run(caller, "thinner")
        expected = BUILDS[BUILDS.index("average") - 1]
        self.assertEqual(caller.db.build_override, expected)


# ===================================================================
# CmdAppear — keyword override
# ===================================================================


class TestCmdAppearKeyword(TestCase):
    """``appear <keyword>`` validates against the catalog."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdAppear

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = args
        cmd.func()

    def test_valid_keyword_sets_override(self):
        caller = _make_disguise_character()
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"man", "droog", "person"}),
        ):
            self._run(caller, "droog")
        self.assertEqual(caller.db.keyword_override, "droog")

    def test_unknown_keyword_rejected(self):
        caller = _make_disguise_character()
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"man", "person"}),
        ):
            self._run(caller, "wraith")
        self.assertIsNone(caller.db.keyword_override)
        msg = caller.msg.call_args[0][0]
        self.assertIn("isn't a recognized keyword", msg)
        self.assertIn("@shortdesc", msg)


# ===================================================================
# CmdAppear — persona resolution
# ===================================================================


class TestCmdAppearPersona(TestCase):
    """``appear <persona name>`` adopts a saved snapshot."""

    def test_persona_overrides_keyword_resolution(self):
        from commands.CmdCharacter import CmdAppear

        persona_entry = {
            "name": "Hooded Wanderer",
            "height_override": "tall",
            "build_override": None,
            "keyword_override": "wanderer",
            "saved_at": 1000.0,
            "saved_in": "Bar",
            "essential_item_types": [],
            "notes": "",
        }
        caller = _make_disguise_character(
            db_attrs={"personas": {"Hooded Wanderer": persona_entry}},
        )

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = "hooded wanderer"  # case-insensitive
        cmd.func()

        self.assertEqual(caller.db.height_override, "tall")
        self.assertIsNone(caller.db.build_override)
        self.assertEqual(caller.db.keyword_override, "wanderer")
        self.assertEqual(caller.db.active_persona, "Hooded Wanderer")

    def test_persona_adoption_clears_unset_axes(self):
        """Adoption is a clean swap, not a merge."""
        from commands.CmdCharacter import CmdAppear

        persona_entry = {
            "name": "Plain",
            "height_override": None,
            "build_override": None,
            "keyword_override": None,
            "saved_at": 1000.0,
            "saved_in": "Bar",
            "essential_item_types": [],
            "notes": "",
        }
        caller = _make_disguise_character(
            db_attrs={
                "height_override": "tall",
                "build_override": "fat",
                "keyword_override": "droog",
                "personas": {"Plain": persona_entry},
            },
        )

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = "Plain"
        cmd.func()

        self.assertIsNone(caller.db.height_override)
        self.assertIsNone(caller.db.build_override)
        self.assertIsNone(caller.db.keyword_override)
        self.assertEqual(caller.db.active_persona, "Plain")


# ===================================================================
# CmdAppear — manual change clears active persona
# ===================================================================


class TestCmdAppearManualClearsPersona(TestCase):
    """Manual axis change after adoption dissociates from the persona."""

    def test_height_nudge_clears_active_persona(self):
        from commands.CmdCharacter import CmdAppear

        caller = _make_disguise_character(
            height="average",
            db_attrs={"active_persona": "Hooded Wanderer"},
        )
        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = "taller"
        cmd.func()

        self.assertIsNone(caller.db.active_persona)
        # Two msgs sent: persona-break and confirmation.
        all_msgs = " ".join(
            call_args[0][0] for call_args in caller.msg.call_args_list
        )
        self.assertIn("Hooded Wanderer", all_msgs)
        self.assertIn("Manual change", all_msgs)

    def test_keyword_override_clears_active_persona(self):
        from commands.CmdCharacter import CmdAppear

        caller = _make_disguise_character(
            db_attrs={"active_persona": "Hooded Wanderer"},
        )
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"droog"}),
        ):
            cmd = CmdAppear()
            cmd.caller = caller
            cmd.args = "droog"
            cmd.func()

        self.assertIsNone(caller.db.active_persona)
        self.assertEqual(caller.db.keyword_override, "droog")


# ===================================================================
# CmdStopAppearing
# ===================================================================


class TestCmdStopAppearing(TestCase):
    """``stop appearing`` clears overrides and persona pointer."""

    def _run(self, caller):
        from commands.CmdCharacter import CmdStopAppearing

        cmd = CmdStopAppearing()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

    def test_clears_all_axes(self):
        caller = _make_disguise_character(
            db_attrs={
                "height_override": "tall",
                "build_override": "fat",
                "keyword_override": "droog",
                "active_persona": "Hooded Wanderer",
            },
        )
        self._run(caller)
        self.assertIsNone(caller.db.height_override)
        self.assertIsNone(caller.db.build_override)
        self.assertIsNone(caller.db.keyword_override)
        self.assertIsNone(caller.db.active_persona)

    def test_no_overrides_reports_no_op(self):
        caller = _make_disguise_character()
        self._run(caller)
        msg = caller.msg.call_args[0][0]
        self.assertIn("aren't presenting", msg)


# ===================================================================
# CmdPersonas — list view
# ===================================================================


class TestCmdPersonas(TestCase):
    """``personas`` lists saved personas, recency-sorted."""

    def _run(self, caller, args=""):
        from commands.CmdCharacter import CmdPersonas

        cmd = CmdPersonas()
        cmd.caller = caller
        cmd.args = args
        cmd.func()
        return caller.msg.call_args[0][0]

    def test_empty_state_explains_remember_me_as(self):
        caller = _make_disguise_character()
        msg = self._run(caller)
        self.assertIn("haven't saved any personas", msg)
        self.assertIn("remember me as", msg)

    def test_lists_personas_recency_sorted(self):
        caller = _make_disguise_character(
            db_attrs={
                "personas": {
                    "Old": {
                        "name": "Old",
                        "height_override": "tall",
                        "build_override": None,
                        "keyword_override": None,
                        "saved_at": 100.0,
                        "saved_in": "X",
                    },
                    "New": {
                        "name": "New",
                        "height_override": "short",
                        "build_override": None,
                        "keyword_override": None,
                        "saved_at": 2000.0,
                        "saved_in": "Y",
                    },
                },
            },
        )
        msg = self._run(caller)
        self.assertIn("Old", msg)
        self.assertIn("New", msg)
        self.assertLess(msg.index("New"), msg.index("Old"))

    def test_active_persona_marked_with_asterisk(self):
        caller = _make_disguise_character(
            db_attrs={
                "active_persona": "Hooded",
                "personas": {
                    "Hooded": {
                        "name": "Hooded",
                        "height_override": None,
                        "build_override": None,
                        "keyword_override": "wanderer",
                        "saved_at": 100.0,
                        "saved_in": "Bar",
                    },
                },
            },
        )
        msg = self._run(caller)
        self.assertIn("*", msg)
        self.assertIn("Hooded", msg)

    def test_rejects_arguments(self):
        caller = _make_disguise_character()
        msg = self._run(caller, args="something")
        self.assertIn("Usage: personas", msg)


# ===================================================================
# CmdPersona — single inspect
# ===================================================================


class TestCmdPersona(TestCase):
    """``persona <name>`` inspects one saved persona."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdPersona

        cmd = CmdPersona()
        cmd.caller = caller
        cmd.args = args
        cmd.func()
        return caller.msg.call_args[0][0]

    def test_no_args_shows_usage(self):
        caller = _make_disguise_character()
        msg = self._run(caller, "")
        self.assertIn("Usage: persona", msg)

    def test_unknown_persona_rejected(self):
        caller = _make_disguise_character()
        msg = self._run(caller, "Ghost")
        self.assertIn("don't have a persona named 'Ghost'", msg)

    def test_known_persona_renders(self):
        caller = _make_disguise_character(
            db_attrs={
                "personas": {
                    "Hooded Wanderer": {
                        "name": "Hooded Wanderer",
                        "height_override": "tall",
                        "build_override": None,
                        "keyword_override": "wanderer",
                        "saved_at": 100.0,
                        "saved_in": "The Grit",
                    },
                },
            },
        )
        msg = self._run(caller, "hooded wanderer")  # case-insensitive
        self.assertIn("Hooded Wanderer", msg)
        self.assertIn("tall", msg)
        self.assertIn("wanderer", msg)
        self.assertIn("The Grit", msg)


# ===================================================================
# CmdRemember — `me as <name>` persona snapshot
# ===================================================================


class TestCmdRememberMeAs(TestCase):
    """``remember me as <name>`` saves a persona snapshot."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdRemember

        cmd = CmdRemember()
        cmd.caller = caller
        cmd.args = args
        cmd.func()

    def test_saves_snapshot_of_current_overrides(self):
        caller = _make_disguise_character(
            db_attrs={
                "height_override": "tall",
                "keyword_override": "wanderer",
            },
        )
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"man", "wanderer"}),
        ):
            self._run(caller, "me as Hooded Wanderer")

        personas = caller.db.personas
        self.assertIn("Hooded Wanderer", personas)
        entry = personas["Hooded Wanderer"]
        self.assertEqual(entry["height_override"], "tall")
        self.assertEqual(entry["keyword_override"], "wanderer")
        self.assertIsNone(entry["build_override"])
        self.assertIn("essential_item_types", entry)
        self.assertEqual(entry["essential_item_types"], [])

    def test_allowed_with_no_active_overrides(self):
        """Per locked decision: allowed even with no axes set."""
        caller = _make_disguise_character()
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"man"}),
        ):
            self._run(caller, "me as Empty")
        self.assertIn("Empty", caller.db.personas)

    def test_collides_with_keyword_rejected(self):
        caller = _make_disguise_character()
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"droog"}),
        ):
            self._run(caller, "me as droog")
        self.assertTrue(
            caller.db.personas is None or "droog" not in (caller.db.personas or {})
        )
        msg = caller.msg.call_args[0][0]
        self.assertIn("reserved keyword", msg)

    def test_collides_with_existing_persona_rejected(self):
        caller = _make_disguise_character(
            db_attrs={
                "personas": {
                    "Hooded": {
                        "name": "Hooded",
                        "height_override": None,
                        "build_override": None,
                        "keyword_override": None,
                        "saved_at": 100.0,
                        "saved_in": "X",
                    },
                },
            },
        )
        with patch(
            "world.identity.get_all_keywords", return_value=frozenset()
        ):
            self._run(caller, "me as hooded")
        # Still only the original entry.
        self.assertEqual(len(caller.db.personas), 1)
        msg = caller.msg.call_args[0][0]
        self.assertIn("already have a persona", msg)

    def test_captures_essential_item_types_when_equipped(self):
        """Saving with essentials worn populates essential_item_types."""
        caller = _make_disguise_character(
            db_attrs={"keyword_override": "wanderer"},
        )
        _equip_essential_items(caller, ["balaclava", "trenchcoat"])
        with patch(
            "world.identity.get_all_keywords",
            return_value=frozenset({"man", "wanderer"}),
        ):
            self._run(caller, "me as Hooded Wanderer")

        entry = caller.db.personas["Hooded Wanderer"]
        # Sorted, deduplicated.
        self.assertEqual(
            entry["essential_item_types"], ["balaclava", "trenchcoat"]
        )

    def test_dedupes_duplicate_essential_item_types(self):
        """Two balaclavas collapse to one entry in the snapshot."""
        caller = _make_disguise_character()
        _equip_essential_items(
            caller, ["balaclava", "balaclava", "trenchcoat"]
        )
        with patch(
            "world.identity.get_all_keywords", return_value=frozenset({"man"})
        ):
            self._run(caller, "me as Dupes")

        entry = caller.db.personas["Dupes"]
        self.assertEqual(
            entry["essential_item_types"], ["balaclava", "trenchcoat"]
        )

    def test_empty_essential_items_yields_empty_list(self):
        """No essentials → empty list (existing behavior preserved)."""
        caller = _make_disguise_character()
        with patch(
            "world.identity.get_all_keywords", return_value=frozenset({"man"})
        ):
            self._run(caller, "me as Bare")
        self.assertEqual(caller.db.personas["Bare"]["essential_item_types"], [])


# ===================================================================
# CmdAppear — persona adoption essential-item advisory
# ===================================================================


class TestCmdAppearPersonaEssentialAdvisory(TestCase):
    """``appear <persona>`` warns when essential item composition diverges."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdAppear

        cmd = CmdAppear()
        cmd.caller = caller
        cmd.args = args
        cmd.func()

    def _persona(self, name, essential_item_types):
        return {
            "name": name,
            "height_override": None,
            "build_override": None,
            "keyword_override": None,
            "saved_at": 1000.0,
            "saved_in": "Bar",
            "essential_item_types": list(essential_item_types),
            "notes": "",
        }

    def test_warns_on_missing_items(self):
        persona = self._persona("Hooded", ["balaclava", "trenchcoat"])
        caller = _make_disguise_character(
            db_attrs={"personas": {"Hooded": persona}},
        )
        # Strip everything — both items missing.
        _equip_essential_items(caller, [])

        self._run(caller, "Hooded")

        all_msgs = " ".join(
            ca[0][0] for ca in caller.msg.call_args_list
        )
        self.assertIn("Heads up", all_msgs)
        self.assertIn("Missing", all_msgs)
        self.assertIn("balaclava", all_msgs)
        self.assertIn("trenchcoat", all_msgs)
        # Adoption proceeded anyway.
        self.assertEqual(caller.db.active_persona, "Hooded")

    def test_warns_on_extra_items(self):
        persona = self._persona("Plain", [])
        caller = _make_disguise_character(
            db_attrs={"personas": {"Plain": persona}},
        )
        # Wearing a balaclava the persona didn't have.
        _equip_essential_items(caller, ["balaclava"])

        self._run(caller, "Plain")

        all_msgs = " ".join(
            ca[0][0] for ca in caller.msg.call_args_list
        )
        self.assertIn("Heads up", all_msgs)
        self.assertIn("Extra", all_msgs)
        self.assertIn("balaclava", all_msgs)
        self.assertEqual(caller.db.active_persona, "Plain")

    def test_no_warning_on_exact_match(self):
        persona = self._persona("Hooded", ["balaclava"])
        caller = _make_disguise_character(
            db_attrs={"personas": {"Hooded": persona}},
        )
        _equip_essential_items(caller, ["balaclava"])

        self._run(caller, "Hooded")

        all_msgs = " ".join(
            ca[0][0] for ca in caller.msg.call_args_list
        )
        self.assertNotIn("Heads up", all_msgs)
        self.assertNotIn("Missing", all_msgs)
        self.assertNotIn("Extra", all_msgs)
        self.assertEqual(caller.db.active_persona, "Hooded")

    def test_no_warning_when_both_empty(self):
        """No essentials saved, none worn → silent adoption."""
        persona = self._persona("Plain", [])
        caller = _make_disguise_character(
            db_attrs={"personas": {"Plain": persona}},
        )

        self._run(caller, "Plain")

        all_msgs = " ".join(
            ca[0][0] for ca in caller.msg.call_args_list
        )
        self.assertNotIn("Heads up", all_msgs)


# ===================================================================
# CmdForget — persona fallback
# ===================================================================


class TestCmdForgetPersona(TestCase):
    """``forget <persona name>`` deletes a persona; clears overrides if active."""

    def _run(self, caller, args):
        from commands.CmdCharacter import CmdForget

        cmd = CmdForget()
        cmd.caller = caller
        cmd.args = args
        # caller.search returns nothing so we fall through to persona path.
        caller.search = MagicMock(return_value=None)
        cmd.func()

    def test_inactive_persona_deleted(self):
        caller = _make_disguise_character(
            db_attrs={
                "personas": {
                    "Hooded": {
                        "name": "Hooded",
                        "height_override": "tall",
                        "build_override": None,
                        "keyword_override": None,
                        "saved_at": 100.0,
                        "saved_in": "X",
                    },
                },
            },
        )
        self._run(caller, "Hooded")
        self.assertEqual(caller.db.personas, {})
        # Overrides were never set on caller; nothing to clear.
        self.assertIsNone(caller.db.height_override)
        msg = caller.msg.call_args[0][0]
        self.assertIn("Forgot persona", msg)

    def test_active_persona_clears_overrides(self):
        caller = _make_disguise_character(
            db_attrs={
                "active_persona": "Hooded",
                "height_override": "tall",
                "keyword_override": "wanderer",
                "personas": {
                    "Hooded": {
                        "name": "Hooded",
                        "height_override": "tall",
                        "build_override": None,
                        "keyword_override": "wanderer",
                        "saved_at": 100.0,
                        "saved_in": "X",
                    },
                },
            },
        )
        self._run(caller, "Hooded")
        self.assertEqual(caller.db.personas, {})
        self.assertIsNone(caller.db.height_override)
        self.assertIsNone(caller.db.keyword_override)
        self.assertIsNone(caller.db.active_persona)
        msg = caller.msg.call_args[0][0]
        self.assertIn("It was active", msg)

    def test_unknown_name_falls_through_to_error(self):
        caller = _make_disguise_character()
        self._run(caller, "Nobody")
        msg = caller.msg.call_args[0][0]
        self.assertIn("don't remember anyone", msg)
