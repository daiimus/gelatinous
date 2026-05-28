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

    def test_new_entry_auto_links_to_prior_presentation(self):
        """Remembering a new presentation auto-links to a prior one.

        Closes the pierce-then-remember loop: if the looker has any
        other recognition entry for the same underlying sleeve, the
        freshly-created entry's ``linked_to`` points at that prior
        presentation so ``recall`` / ``memory`` render the aka-line
        correctly without requiring a witnessed unmasking moment.
        """
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
                "uid-bare-face": {
                    "assigned_name": "Jorge",
                    "real_sleeve_uid": "uid-target",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 5,
                    "location_first_seen": "Bar",
                    "location_last_seen": "Bar",
                    "locations_seen": ["Bar"],
                    "sdesc_at_first_encounter": "tall man",
                    "sdesc_at_last_encounter": "tall man",
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
        cmd._remember_target(caller, target, target_uid, "the cloaked one")

        entry = caller.recognition_memory[target_uid]
        self.assertEqual(entry["linked_to"], "uid-bare-face")

    def test_new_entry_does_not_link_when_no_prior_presentation(self):
        """First-ever encounter has nothing to link to."""
        from commands.CmdCharacter import CmdRemember

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        caller = _make_character(key="Observer", sleeve_uid="uid-observer")

        cmd = CmdRemember()
        cmd.caller = caller
        cmd._remember_target(caller, target, target_uid, "Jorge")

        entry = caller.recognition_memory[target_uid]
        # Either absent or explicitly None — both are valid "no link".
        self.assertIsNone(entry.get("linked_to"))

    def test_new_entry_does_not_self_link(self):
        """Auto-link must skip the just-created entry's own UID.

        Defensive against a future refactor that pre-populates the
        memory slot before computing the link.
        """
        from commands.CmdCharacter import CmdRemember

        target = _make_character(
            key="Jorge",
            sleeve_uid="uid-target",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target_uid = apparent_uid_for(target)
        # Pre-seed an entry with the *same* UID and matching sleeve;
        # _remember_target's "existing entry" branch runs, so
        # `linked_to` should not be set at all.
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                target_uid: {
                    "assigned_name": "old name",
                    "real_sleeve_uid": "uid-target",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 1,
                    "location_first_seen": "Bar",
                    "location_last_seen": "Bar",
                    "locations_seen": ["Bar"],
                    "sdesc_at_first_encounter": "x",
                    "sdesc_at_last_encounter": "x",
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
        cmd._remember_target(caller, target, target_uid, "new name")

        entry = caller.recognition_memory[target_uid]
        self.assertIsNone(entry.get("linked_to"))

    def test_new_entry_preserves_existing_link(self):
        """A pre-existing linked_to (e.g. from unmasking) is not overwritten."""
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
                "uid-original": {
                    "assigned_name": "Jorge",
                    "real_sleeve_uid": "uid-target",
                    "first_seen": "2026-01-01T00:00:00",
                    "last_seen": "2026-01-01T00:00:00",
                    "times_seen": 1,
                    "location_first_seen": "Bar",
                    "location_last_seen": "Bar",
                    "locations_seen": ["Bar"],
                    "sdesc_at_first_encounter": "x",
                    "sdesc_at_last_encounter": "x",
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
        # Existing entry already has a non-None linked_to; remember
        # must not clobber it.  We test the *new-entry* path, so the
        # entry must not pre-exist; build a fresh entry that the
        # builder will short-circuit through the if-branch (the entry
        # is created with no linked_to, then auto-link runs).  This is
        # the realistic flow: the only way a brand-new entry gets a
        # link is via the auto-link logic, so this test confirms the
        # link points to the original presentation as expected.
        cmd._remember_target(caller, target, target_uid, "the cloaked one")

        entry = caller.recognition_memory[target_uid]
        self.assertEqual(entry["linked_to"], "uid-original")


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
# forget — pierce-cache invalidation (issue #210)
# ===================================================================


def _seed_memory_with_sleeve(
    *, uid="uid-target", name="Big J", real_sleeve_uid="sleeve-jorge"
):
    """``_seed_memory`` variant that populates ``real_sleeve_uid``.

    Mirrors entries written by the post-schema ``_remember_target``
    builder.  Tests for pierce-cache invalidation rely on the
    backfilled sleeve field to drive
    :func:`world.identity.find_entries_by_real_sleeve_uid`.
    """
    memory = _seed_memory(uid=uid, name=name)
    memory[uid]["real_sleeve_uid"] = real_sleeve_uid
    return memory


class TestForgetInvalidatesPierceCache(TestCase):
    """``forget`` drops cached pierce verdicts for the target's sleeve.

    Regression coverage for issue #210: a cached ``True`` in
    ``observer.db.disguise_pierce_cache`` survived ``forget`` and
    ``attempt_disguise_pierce`` short-circuited on it, leaving
    forgotten targets perpetually recognized through any disguise.

    Scope: sleeve-wide.  Every cached ``apparent_uid`` belonging to
    the forgotten target's sleeve drops, not just the current
    presentation.
    """

    def _make_caller_with_cache(self, *, memory, cache):
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )
        caller.db.disguise_pierce_cache = cache
        return caller

    def test_forget_visible_drops_pierce_cache_for_target_sleeve(self):
        """All cached presentations for the forgotten sleeve are removed."""
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="sleeve-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target.dbref = "#101"
        bare_uid = apparent_uid_for(target)
        memory = _seed_memory_with_sleeve(
            uid=bare_uid, real_sleeve_uid="sleeve-jorge"
        )
        # A second masked presentation for the same sleeve.
        memory["uid-jorge-masked"] = {
            "assigned_name": "",
            "real_sleeve_uid": "sleeve-jorge",
            "first_seen": "2026-01-02T00:00:00",
            "last_seen": "2026-01-02T00:00:00",
            "times_seen": 1,
            "linked_to": bare_uid,
        }
        cache = {
            ("#101", bare_uid): True,
            ("#101", "uid-jorge-masked"): True,
        }
        caller = self._make_caller_with_cache(memory=memory, cache=cache)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, bare_uid)

        self.assertEqual(caller.db.disguise_pierce_cache, {})

    def test_forget_visible_preserves_other_sleeve_cache(self):
        """Forgetting one sleeve must not touch unrelated cached pierces."""
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="sleeve-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target.dbref = "#101"
        bare_uid = apparent_uid_for(target)
        memory = _seed_memory_with_sleeve(
            uid=bare_uid, real_sleeve_uid="sleeve-jorge"
        )
        # Unrelated second sleeve in memory + cache.
        memory["uid-other-bare"] = {
            "assigned_name": "Maria",
            "real_sleeve_uid": "sleeve-maria",
            "first_seen": "2026-01-03T00:00:00",
            "last_seen": "2026-01-03T00:00:00",
            "times_seen": 1,
        }
        cache = {
            ("#101", bare_uid): True,
            ("#202", "uid-other-bare"): True,
        }
        caller = self._make_caller_with_cache(memory=memory, cache=cache)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, bare_uid)

        self.assertEqual(
            caller.db.disguise_pierce_cache,
            {("#202", "uid-other-bare"): True},
        )

    def test_forget_remembered_clears_cache_via_entry_sleeve(self):
        """Absent-target path uses ``entry['real_sleeve_uid']`` for scope."""
        from commands.CmdCharacter import (
            CmdForget,
            _find_remembered_uid_by_name,
        )

        # Build a target only to derive its apparent UID for seeding.
        target = _make_character(
            key="Jorge",
            sleeve_uid="sleeve-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        bare_uid = apparent_uid_for(target)
        memory = _seed_memory_with_sleeve(
            uid=bare_uid, real_sleeve_uid="sleeve-jorge"
        )
        memory["uid-jorge-masked"] = {
            "assigned_name": "",
            "real_sleeve_uid": "sleeve-jorge",
            "first_seen": "2026-01-02T00:00:00",
            "last_seen": "2026-01-02T00:00:00",
            "times_seen": 1,
        }
        cache = {
            ("#101", bare_uid): True,
            ("#101", "uid-jorge-masked"): True,
        }
        caller = self._make_caller_with_cache(memory=memory, cache=cache)

        sleeve_uid, entry = _find_remembered_uid_by_name(caller, "big j")
        self.assertEqual(sleeve_uid, bare_uid)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_remembered(caller, sleeve_uid, entry)

        self.assertEqual(caller.db.disguise_pierce_cache, {})

    def test_forget_remembered_pre_schema_entry_skips_invalidation(self):
        """Entry without ``real_sleeve_uid`` leaves cache untouched.

        Pre-schema memory entries cannot be reverse-keyed by sleeve, so
        invalidation has no anchor.  Forget still succeeds (clears the
        assigned_name) — the pierce candidate filter in
        :func:`world.identity.attempt_display_pierce` guards rendering
        correctness in that case (it requires a truthy
        ``assigned_name``, which the forget just cleared).
        """
        from commands.CmdCharacter import CmdForget

        bare_uid = "uid-jorge-bare"
        memory = _seed_memory(uid=bare_uid)
        # Pre-schema entry — no real_sleeve_uid.
        cache = {("#101", bare_uid): True}
        caller = self._make_caller_with_cache(memory=memory, cache=cache)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_remembered(caller, bare_uid, memory[bare_uid])

        # Cache untouched; assigned_name cleared.
        self.assertEqual(
            caller.db.disguise_pierce_cache, {("#101", bare_uid): True}
        )
        self.assertEqual(memory[bare_uid]["assigned_name"], "")

    def test_forget_visible_falls_back_to_live_sleeve_for_pre_schema_entry(self):
        """Visible-target path can still invalidate via ``target.sleeve_uid``.

        Even when the memory entry pre-dates the ``real_sleeve_uid``
        schema, the visible target itself exposes its sleeve and the
        invalidator can run.
        """
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="sleeve-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        target.dbref = "#101"
        bare_uid = apparent_uid_for(target)
        memory = _seed_memory(uid=bare_uid)  # no real_sleeve_uid
        # Add a second presentation that HAS the field — so the
        # invalidator has something to find via reverse lookup.
        memory["uid-jorge-masked"] = {
            "assigned_name": "",
            "real_sleeve_uid": "sleeve-jorge",
            "first_seen": "2026-01-02T00:00:00",
            "last_seen": "2026-01-02T00:00:00",
            "times_seen": 1,
        }
        cache = {("#101", "uid-jorge-masked"): True}
        caller = self._make_caller_with_cache(memory=memory, cache=cache)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, bare_uid)

        self.assertEqual(caller.db.disguise_pierce_cache, {})

    def test_forget_with_empty_cache_no_crash(self):
        """No cache present is a no-op (not an error)."""
        from commands.CmdCharacter import CmdForget

        target = _make_character(
            key="Jorge",
            sleeve_uid="sleeve-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        bare_uid = apparent_uid_for(target)
        memory = _seed_memory_with_sleeve(
            uid=bare_uid, real_sleeve_uid="sleeve-jorge"
        )
        caller = self._make_caller_with_cache(memory=memory, cache=None)

        cmd = CmdForget()
        cmd.caller = caller
        cmd._forget_visible(caller, target, bare_uid)

        self.assertIsNone(caller.db.disguise_pierce_cache)


# ===================================================================
# invalidate_pierce_cache_for_sleeve — direct unit coverage
# ===================================================================


class TestInvalidatePierceCacheForSleeve(TestCase):
    """Direct unit coverage for the helper."""

    def _make_observer(self, *, memory, cache):
        observer = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )
        observer.db.disguise_pierce_cache = cache
        return observer

    def test_returns_zero_for_empty_sleeve_uid(self):
        from world.identity import invalidate_pierce_cache_for_sleeve

        observer = self._make_observer(memory={}, cache={})
        self.assertEqual(
            invalidate_pierce_cache_for_sleeve(observer, ""), 0
        )
        self.assertEqual(
            invalidate_pierce_cache_for_sleeve(observer, None), 0
        )

    def test_returns_zero_for_empty_cache(self):
        from world.identity import invalidate_pierce_cache_for_sleeve

        observer = self._make_observer(memory={}, cache=None)
        self.assertEqual(
            invalidate_pierce_cache_for_sleeve(observer, "sleeve-x"), 0
        )

    def test_returns_zero_when_sleeve_has_no_memory_entries(self):
        from world.identity import invalidate_pierce_cache_for_sleeve

        cache = {("#101", "uid-other"): True}
        observer = self._make_observer(memory={}, cache=cache)
        self.assertEqual(
            invalidate_pierce_cache_for_sleeve(observer, "sleeve-x"), 0
        )
        # Cache untouched.
        self.assertEqual(
            observer.db.disguise_pierce_cache,
            {("#101", "uid-other"): True},
        )

    def test_drops_matching_keys_and_returns_count(self):
        from world.identity import invalidate_pierce_cache_for_sleeve

        memory = {
            "uid-a": {"real_sleeve_uid": "sleeve-x", "assigned_name": "A"},
            "uid-b": {"real_sleeve_uid": "sleeve-x", "assigned_name": ""},
            "uid-c": {"real_sleeve_uid": "sleeve-y", "assigned_name": "C"},
        }
        cache = {
            ("#10", "uid-a"): True,
            ("#10", "uid-b"): False,
            ("#11", "uid-c"): True,
        }
        observer = self._make_observer(memory=memory, cache=cache)
        dropped = invalidate_pierce_cache_for_sleeve(observer, "sleeve-x")
        self.assertEqual(dropped, 2)
        self.assertEqual(
            observer.db.disguise_pierce_cache,
            {("#11", "uid-c"): True},
        )


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
# lost_contact render annotation
# ===================================================================


class TestLostContactRenderAnnotation(TestCase):
    """Verify ``(lost contact)`` annotation appears in memory/recall.

    The flip itself is exercised by
    :class:`world.tests.test_identity.TestMarkLostContactEntries`;
    these tests only assert the render layer surfaces the flag.
    """

    def test_recall_annotates_lost_contact_named_entry(self):
        """recall on a stale named entry surfaces the |y(lost contact)|n tag."""
        from commands.CmdCharacter import CmdRecall

        memory = _seed_memory()
        memory["uid-target"]["lost_contact"] = True
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(caller, memory["uid-target"])

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Big J", msg_text)
        self.assertIn("(lost contact)", msg_text)

    def test_recall_annotates_lost_contact_unnamed_entry(self):
        """The 'no name' header also gains the annotation when stale."""
        from commands.CmdCharacter import CmdRecall

        memory = _seed_memory()
        memory["uid-target"]["assigned_name"] = ""
        memory["uid-target"]["lost_contact"] = True
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
        self.assertIn("(lost contact)", msg_text)

    def test_recall_no_annotation_when_flag_false(self):
        """Fresh entries do not gain the annotation."""
        from commands.CmdCharacter import CmdRecall

        memory = _seed_memory()
        # lost_contact already False from _seed_memory
        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=memory,
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(caller, memory["uid-target"])

        msg_text = caller.msg.call_args[0][0]
        self.assertNotIn("(lost contact)", msg_text)

    def test_memory_annotates_lost_contact_entry(self):
        """memory table appends the tag to the |wName|n cell for stale rows."""
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory={
                "uid-stale": {
                    "assigned_name": "Ghost",
                    "last_seen": "2026-01-01T00:00:00",
                    "sdesc_at_last_encounter": "a faded face",
                    "location_last_seen": "Old Bar",
                    "lost_contact": True,
                },
                "uid-fresh": {
                    "assigned_name": "Pal",
                    "last_seen": "2026-05-12T00:00:00",
                    "sdesc_at_last_encounter": "a friend",
                    "location_last_seen": "Bar",
                    "lost_contact": False,
                },
            },
        )
        # Suppress _refresh_lost_contact's room scan — we want to assert
        # the render annotation in isolation, with flags as seeded.
        with patch(
            "commands.CmdCharacter._refresh_lost_contact",
            lambda _caller: None,
        ):
            cmd = CmdMemory()
            cmd.caller = caller
            cmd.args = ""
            cmd.func()

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Ghost", msg_text)
        # EvTable inserts ANSI codes / line wraps inside the cell, so the
        # literal "(lost contact)" substring won't be contiguous.  Assert
        # both tokens land in the Ghost row but neither in the Pal row.
        ghost_line = next(
            line for line in msg_text.splitlines() if "Ghost" in line
        )
        self.assertIn("lost", ghost_line)
        self.assertIn("contact)", ghost_line)
        for line in msg_text.splitlines():
            if "Pal" in line and "Ghost" not in line:
                self.assertNotIn("lost", line)
                self.assertNotIn("contact)", line)


# ===================================================================
# @shortdesc — custom keyword acceptance
# ===================================================================


class TestAlsoKnownAsRendering(TestCase):
    """``recall`` and ``memory`` surface linked-chain aliases (PR 3)."""

    def _seed_linked_pair(self, observer):
        """Seed two linked entries on *observer*'s memory.

        ``uid-hood`` (named "The Hood") links back to ``uid-jorge``
        (named "Jorge") — the shape produced by Cell D / Cell B of the
        unmasking broadcast.
        """
        observer.recognition_memory = {
            "uid-jorge": {
                "assigned_name": "Jorge",
                "first_seen": "2026-01-01T00:00:00",
                "last_seen": "2026-01-01T00:00:00",
                "times_seen": 3,
                "location_first_seen": "Plaza",
                "location_last_seen": "Plaza",
                "locations_seen": ["Plaza"],
                "sdesc_at_first_encounter": "a tall lean man",
                "sdesc_at_last_encounter": "a tall lean man",
                "notes": "",
                "tags": [],
                "confidence": 1.0,
                "relationship_valence": "neutral",
                "recent_interactions": [],
                "lost_contact": True,
                "linked_to": None,
            },
            "uid-hood": {
                "assigned_name": "The Hood",
                "first_seen": "2026-01-02T00:00:00",
                "last_seen": "2026-01-02T00:00:00",
                "times_seen": 1,
                "location_first_seen": "Alley",
                "location_last_seen": "Alley",
                "locations_seen": ["Alley"],
                "sdesc_at_first_encounter": "a hooded figure",
                "sdesc_at_last_encounter": "a hooded figure",
                "notes": "",
                "tags": [],
                "confidence": 1.0,
                "relationship_valence": "neutral",
                "recent_interactions": [],
                "lost_contact": False,
                "linked_to": "uid-jorge",
            },
        }

    def test_recall_renders_also_known_as_for_linked_entry(self):
        from commands.CmdCharacter import CmdRecall

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        self._seed_linked_pair(caller)

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(
            caller, caller.recognition_memory["uid-hood"], "uid-hood"
        )

        msg_text = caller.msg.call_args[0][0]
        self.assertIn("Also known as", msg_text)
        self.assertIn("Jorge", msg_text)

    def test_recall_omits_also_known_as_when_no_chain(self):
        from commands.CmdCharacter import CmdRecall

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
            recognition_memory=_seed_memory(),
        )

        cmd = CmdRecall()
        cmd.caller = caller
        cmd._render_entry(
            caller, caller.recognition_memory["uid-target"], "uid-target"
        )

        msg_text = caller.msg.call_args[0][0]
        self.assertNotIn("Also known as", msg_text)

    def test_memory_table_shows_aka_for_linked_entries(self):
        from commands.CmdCharacter import CmdMemory

        caller = _make_character(key="Observer", sleeve_uid="uid-observer")
        self._seed_linked_pair(caller)

        cmd = CmdMemory()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()

        msg_text = caller.msg.call_args[0][0]
        # The Hood row should annotate Jorge as a linked alias.  The
        # table cell wraps "(aka Jorge)" across whitespace, so assert
        # on both fragments independently rather than the joined string.
        self.assertIn("aka", msg_text)
        self.assertIn("Jorge", msg_text)
        # And the Hood entry itself should still be present.
        self.assertIn("The Hood", msg_text)



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


# ===================================================================
# Passive recognition recency on room entry
# ===================================================================


class TestPassiveRecencyOnMove(TestCase):
    """Walking into a room with a known target refreshes recency.

    Exercises ``Character._refresh_recognition_recency`` end-to-end:
    iterates the room's contents, computes Apparent UIDs, and calls
    :func:`world.identity.bump_recognition_recency` for known UIDs.
    """

    def _bind_refresh(self, observer):
        """Bind the real _refresh_recognition_recency to a mock character."""
        from typeclasses.characters import Character

        observer._refresh_recognition_recency = (
            lambda: Character._refresh_recognition_recency(observer)
        )

    def _make_room(self, contents):
        """Build a stand-in location with the given contents list."""
        room = MagicMock()
        room.key = "Plaza"
        room.contents = contents
        return room

    def test_entry_with_known_target_bumps_recency(self):
        """Known UID in room → last_seen advances after refresh."""
        from datetime import datetime, timedelta
        from world.identity import RECOGNITION_BUMP_THROTTLE_SECONDS

        target = _make_character(
            key="Jorge", sleeve_uid="uid-jorge"
        )
        target_uid = apparent_uid_for(target)

        stale = datetime.utcnow() - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        stale_iso = stale.strftime("%Y-%m-%dT%H:%M:%S")
        memory = {
            target_uid: {
                "assigned_name": "Jorge",
                "last_seen": stale_iso,
                "times_seen": 1,
                "location_last_seen": "OldRoom",
                "sdesc_at_last_encounter": "old sdesc",
                "lost_contact": False,
            },
        }
        observer = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory=memory,
        )
        observer.location = self._make_room([observer, target])
        self._bind_refresh(observer)

        observer._refresh_recognition_recency()

        self.assertNotEqual(memory[target_uid]["last_seen"], stale_iso)
        self.assertEqual(memory[target_uid]["location_last_seen"], "Plaza")
        # times_seen unchanged — this is passive perception, not remember.
        self.assertEqual(memory[target_uid]["times_seen"], 1)

    def test_entry_with_unknown_target_does_not_create_memory(self):
        """Stranger in room → memory dict unchanged."""
        target = _make_character(
            key="Stranger", sleeve_uid="uid-stranger"
        )
        observer = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory={},
        )
        observer.location = self._make_room([observer, target])
        self._bind_refresh(observer)

        observer._refresh_recognition_recency()

        self.assertEqual(observer.recognition_memory, {})

    def test_disguised_target_does_not_bump_stale_uid(self):
        """Target whose Apparent UID changed → no bump on the old UID."""
        from datetime import datetime, timedelta
        from world.identity import RECOGNITION_BUMP_THROTTLE_SECONDS

        # We remember the target under an old UID, but their current
        # Apparent UID is different (e.g. they put on a hood).
        target = _make_character(
            key="Jorge", sleeve_uid="uid-jorge"
        )
        current_uid = apparent_uid_for(target)
        old_uid = "uid-jorge-undisguised-different"
        self.assertNotEqual(current_uid, old_uid)

        stale = datetime.utcnow() - timedelta(
            seconds=RECOGNITION_BUMP_THROTTLE_SECONDS + 60
        )
        stale_iso = stale.strftime("%Y-%m-%dT%H:%M:%S")
        memory = {
            old_uid: {
                "assigned_name": "Jorge",
                "last_seen": stale_iso,
                "times_seen": 1,
                "location_last_seen": "OldRoom",
                "sdesc_at_last_encounter": "old sdesc",
                "lost_contact": False,
            },
        }
        observer = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory=memory,
        )
        observer.location = self._make_room([observer, target])
        self._bind_refresh(observer)

        observer._refresh_recognition_recency()

        # Old UID untouched — current sighting doesn't match it.
        self.assertEqual(memory[old_uid]["last_seen"], stale_iso)
        # Current UID was not added — helper never creates entries.
        self.assertNotIn(current_uid, memory)


class TestGetLookHeader(TestCase):
    """``Character.get_look_header`` enriches the appearance header line.

    Adds a ``"({article} {sdesc})"`` parenthetical when the looker has a
    name to attach to it (own real name when looking at self, or an
    assigned recognition name for the target's Apparent UID).  Strangers
    delegate to ``get_display_name`` to avoid duplication.
    """

    def _bind_look_header(self, char):
        """Bind the real ``get_look_header`` to a mock character."""
        from typeclasses.characters import Character

        char.get_look_header = (
            lambda looker=None, **kw: Character.get_look_header(
                char, looker, **kw
            )
        )

    def test_no_looker_returns_key(self):
        char = _make_character(key="Jorge", sleeve_uid="uid-jorge")
        self._bind_look_header(char)
        self.assertEqual(char.get_look_header(None), "Jorge")

    def test_self_look_includes_own_sdesc(self):
        char = _make_character(
            key="Daiimus",
            sex="male",
            sleeve_uid="uid-d",
            height="tall",
            build="lean",
        )
        self._bind_look_header(char)
        header = char.get_look_header(char)
        self.assertTrue(header.startswith("Daiimus ("))
        self.assertTrue(header.endswith(")"))
        # Sdesc body should appear inside the parens.
        sdesc = char.get_sdesc()
        self.assertIn(sdesc, header)

    def test_self_look_falls_back_when_sdesc_is_key(self):
        """Pre-chargen (no height/build) → no parenthetical."""
        char = _make_character(
            key="Newbie",
            sleeve_uid="uid-newbie",
            height=None,
            build=None,
        )
        self._bind_look_header(char)
        # Sanity: get_sdesc collapses to key here.
        self.assertEqual(char.get_sdesc(), "Newbie")
        self.assertEqual(char.get_look_header(char), "Newbie")

    def test_recognized_target_includes_assigned_name_and_sdesc(self):
        target = _make_character(
            key="Jorge Jackson",
            sex="male",
            sleeve_uid="uid-jorge",
            height="tall",
            build="lean",
        )
        self._bind_look_header(target)
        target_uid = apparent_uid_for(target)
        memory = {
            target_uid: {
                "assigned_name": "Batman",
                "last_seen": "2025-01-01T00:00:00",
                "times_seen": 1,
                "location_last_seen": "Cave",
                "sdesc_at_last_encounter": "tall man",
                "lost_contact": False,
            },
        }
        looker = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory=memory,
        )
        header = target.get_look_header(looker)
        self.assertTrue(header.startswith("Batman ("))
        self.assertTrue(header.endswith(")"))
        self.assertIn(target.get_sdesc(), header)

    def test_unrecognized_target_returns_plain_sdesc(self):
        """Stranger → exact same string as ``get_display_name``."""
        target = _make_character(
            key="Stranger",
            sex="male",
            sleeve_uid="uid-stranger",
            height="tall",
            build="lean",
        )
        self._bind_look_header(target)
        looker = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory={},
        )
        self.assertEqual(
            target.get_look_header(looker),
            target.get_display_name(looker),
        )
        # And no parenthetical was tacked on.
        self.assertNotIn("(", target.get_look_header(looker))

    def test_recognized_target_omits_parenthetical_when_sdesc_is_key(self):
        """Recognized but pre-chargen target → just the assigned name."""
        target = _make_character(
            key="Newbie",
            sleeve_uid="uid-newbie",
            height=None,
            build=None,
        )
        self._bind_look_header(target)
        target_uid = apparent_uid_for(target)
        memory = {
            target_uid: {
                "assigned_name": "Friend",
                "last_seen": "2025-01-01T00:00:00",
                "times_seen": 1,
                "location_last_seen": "Plaza",
                "sdesc_at_last_encounter": "Newbie",
                "lost_contact": False,
            },
        }
        looker = _make_character(
            key="Watcher",
            sleeve_uid="uid-watcher",
            recognition_memory=memory,
        )
        # Sanity: sdesc collapses to key.
        self.assertEqual(target.get_sdesc(), "Newbie")
        self.assertEqual(target.get_look_header(looker), "Friend")


# ===================================================================
# Magic-keyword regressions: forget me / recall me
# ===================================================================


class TestForgetRecallMeAreHarmless(TestCase):
    """Regression tests for the ``me``/``self``/``here`` shortcut.

    After the shortcut, ``caller.search('me', quiet=True)`` returns
    ``[caller]`` instead of ``[]`` — which routes ``forget me`` and
    ``recall me`` into the visible-Character branch of those commands
    where they previously fell through to the remembered-name path.

    Both endpoints must remain harmless: no state mutation, a sensible
    user-facing message, no exception.

    See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §Target Resolution
    (Magic Keywords).
    """

    def _bind_search(self, char):
        """Wire ``char.search`` to call the real Character.search."""
        from typeclasses.characters import Character

        char.search = lambda *a, **kw: Character.search(char, *a, **kw)
        char.check_permstring = MagicMock(return_value=False)

    def test_forget_me_is_harmless(self):
        """``forget me`` reports no-name-remembered, mutates nothing."""
        from commands.CmdCharacter import CmdForget

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
        )
        self._bind_search(caller)

        before = dict(caller.recognition_memory)

        cmd = CmdForget()
        cmd.caller = caller
        cmd.args = "me"
        cmd.func()

        # No state corruption
        self.assertEqual(caller.recognition_memory, before)
        # Some message was emitted (no exception)
        caller.msg.assert_called()

    def test_recall_me_is_harmless(self):
        """``recall me`` emits a 'don't recognize' message, no exception."""
        from commands.CmdCharacter import CmdRecall

        caller = _make_character(
            key="Observer",
            sleeve_uid="uid-observer",
        )
        self._bind_search(caller)

        cmd = CmdRecall()
        cmd.caller = caller
        cmd.args = "me"
        cmd.func()

        caller.msg.assert_called()
        msg_text = caller.msg.call_args[0][0]
        # Either "don't recognize" (entry None branch) or
        # "can't recall anything" (None apparent_uid branch).
        # Both are acceptable harmless outcomes.
        self.assertTrue(
            "don't recognize" in msg_text
            or "can't recall" in msg_text,
            f"Unexpected message: {msg_text!r}",
        )


# ===================================================================
# Timezone-correctness: writer / reader contract
# ===================================================================


class FormatRelativeTimeTests(TestCase):
    """``_format_relative_time`` must interpret stored ISO strings as UTC.

    Regression coverage for the bug where the renderer parsed naive UTC
    timestamps then called ``datetime.timestamp()``, which treats the
    naive datetime as **local** time — yielding a "X ago" value off by
    the server's UTC offset (e.g. 7 hours on a PDT host).

    The fix routes both the writer and the reader through the
    ``_recognition_*`` helpers in :mod:`world.identity`, which use
    naive UTC throughout.
    """

    def test_round_trip_is_recent(self):
        """Writing now + reading immediately yields a sub-minute delta."""
        from commands.CmdCharacter import _format_relative_time
        from world.identity import _recognition_now_iso

        rendered = _format_relative_time(_recognition_now_iso())
        # Must be either "just now" or "Xs ago" — never hours/days off.
        self.assertTrue(
            rendered == "just now" or rendered.endswith("s ago"),
            f"Round-trip should be sub-minute, got {rendered!r}",
        )

    def test_one_hour_old_renders_as_hour(self):
        """An entry stamped 1h ago must render with 'h' (hours) units."""
        from datetime import timedelta

        from commands.CmdCharacter import _format_relative_time
        from world.identity import (
            _RECOGNITION_TIMESTAMP_FMT,
            _recognition_utcnow,
        )

        one_hour_ago = _recognition_utcnow() - timedelta(hours=1)
        iso = one_hour_ago.strftime(_RECOGNITION_TIMESTAMP_FMT)
        rendered = _format_relative_time(iso)
        # Should mention an hour, not a different unit; this is the
        # tightest assertion we can make without coupling to the exact
        # phrasing of evennia.utils.time_format.
        self.assertIn("h", rendered)
        self.assertTrue(rendered.endswith("ago"))

    def test_empty_input_returns_unknown(self):
        from commands.CmdCharacter import _format_relative_time

        self.assertEqual(_format_relative_time(""), "unknown")
        self.assertEqual(_format_relative_time(None), "unknown")

    def test_malformed_input_returns_raw(self):
        from commands.CmdCharacter import _format_relative_time

        self.assertEqual(
            _format_relative_time("not-an-iso-timestamp"),
            "not-an-iso-timestamp",
        )


class RecognitionTimestampHelperTests(TestCase):
    """The canonical recognition-timestamp helpers must agree with each other.

    ``_recognition_now_iso`` and ``_parse_recognition_timestamp`` form a
    round-trip; ``_recognition_utcnow`` is the naive-UTC "now" both
    sides share for elapsed-delta math.  Any drift here re-introduces
    the local-vs-UTC bug.
    """

    def test_round_trip_preserves_seconds(self):
        from world.identity import (
            _parse_recognition_timestamp,
            _recognition_now_iso,
        )

        iso = _recognition_now_iso()
        parsed = _parse_recognition_timestamp(iso)
        # Re-format must yield the original string (no precision loss).
        from world.identity import _RECOGNITION_TIMESTAMP_FMT

        self.assertEqual(parsed.strftime(_RECOGNITION_TIMESTAMP_FMT), iso)

    def test_now_helper_returns_naive_datetime(self):
        from world.identity import _recognition_utcnow

        now = _recognition_utcnow()
        # Contract: stored timestamps are naive — comparisons against
        # tz-aware datetimes raise TypeError.  We require naive.
        self.assertIsNone(now.tzinfo)

    def test_helper_matches_utc_within_one_second(self):
        """The helper must return UTC, not local time."""
        from datetime import datetime, timezone

        from world.identity import _recognition_utcnow

        helper_now = _recognition_utcnow()
        aware_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        delta_seconds = abs((aware_utc - helper_now).total_seconds())
        self.assertLess(
            delta_seconds,
            2,
            "Recognition 'now' helper diverges from UTC; "
            "local-vs-UTC bug has regressed.",
        )

    def test_malformed_parse_raises_valueerror(self):
        from world.identity import _parse_recognition_timestamp

        with self.assertRaises(ValueError):
            _parse_recognition_timestamp("nope")
