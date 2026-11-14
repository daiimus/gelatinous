"""
Tests for combat-command identity targeting (PR \u03b1).

Covers the new ``commands._identity_targeting`` helper module which is
the canonical entry point used by combat commands (attack/kill,
grapple, aim, advance, charge) to resolve character targets via the
identity recognition pipeline.

Tests exercise the helper directly (since the helper IS the conversion)
with mock characters and rooms.  The four cases per command from the
test matrix collapse into helper-level cases:

  - **recognised name match** — assigned_name in recognition_memory
  - **sdesc substring match** — keyword from get_sdesc composition
  - **real-key rejection** — non-Builder cannot target by .key
  - **ambiguity** — multiple matches send disambiguation, return None

Cross-room commands (advance, charge) additionally exercise
``resolve_character_in_rooms``.

Run via::

    evennia test world.tests.test_combat_command_identity
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from commands._identity_targeting import (
    resolve_character_in_rooms,
    resolve_character_target,
)
from world.tests._identity_helpers import (
    apparent_uid_for,
    prepare_mock_for_apparent_uid,
)


# ===================================================================
# Mock factory (mirrors test_identity_search._make_character)
# ===================================================================


def _make_character(
    *,
    key="Jorge Jackson",
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword=None,
    sleeve_uid="uid-default",
    recognition_memory=None,
    is_builder=False,
    aliases=None,
):
    """Build a mock character with identity attributes."""
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.sex = sex
    char.height = height
    char.build = build
    char.sdesc_keyword = sdesc_keyword
    char.hair_color = None
    char.hair_style = None
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = (
        recognition_memory if recognition_memory is not None else {}
    )
    char.hands = {"left": None, "right": None}
    char.worn_items = {}

    def _coverage_map():
        return {}

    char._build_clothing_coverage_map = _coverage_map

    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(
            char, looker, **kw
        )
    )

    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    # aliases mock
    alias_list = aliases or []
    char.aliases = MagicMock()
    char.aliases.all = lambda: alias_list

    # Permission check (Builder gate for the helper's key fallback)
    # The one staff question the doors ask now (#3818): `world.search.may_use_real_names` reads the lock handler.
    char.locks.check_lockstring = lambda obj, lockstring: is_builder

    # msg sink (helpers send disambiguation messages here)
    char.msg = MagicMock()

    prepare_mock_for_apparent_uid(char)
    return char


def _make_room(contents):
    """Build a minimal mock room exposing .contents and .key."""
    room = MagicMock()
    room.contents = contents
    room.key = "Test Room"
    return room


# ===================================================================
# Tests: resolve_character_target — same-room resolution
# ===================================================================


class TestResolveCharacterTarget(TestCase):
    """Same-room identity-aware target resolution."""

    def setUp(self):
        self.caller = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-caller",
        )
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        self.candidates = [self.caller, self.jorge, self.maria]
        self.room = _make_room(self.candidates)
        self.caller.location = self.room

    def test_recognised_name_match(self):
        """Assigned name resolves to the right character."""
        self.caller.recognition_memory = {
            apparent_uid_for(self.jorge): {
                "assigned_name": "Jorge",
                "lost_contact": False,
            },
        }
        result = resolve_character_target(self.caller, "jorge")
        self.assertIs(result, self.jorge)

    def test_sdesc_substring_match(self):
        """Sdesc keyword resolves."""
        result = resolve_character_target(self.caller, "man")
        self.assertIs(result, self.jorge)

    def test_real_key_rejected_for_non_builder(self):
        """Non-builders cannot target by .key."""
        # 'jackson' is in Jorge's .key but not in his sdesc.
        result = resolve_character_target(self.caller, "jackson")
        self.assertIsNone(result)

    def test_real_key_allowed_for_builder(self):
        """Builders fall back to .key matching."""
        self.caller.locks.check_lockstring = lambda obj, lockstring: True
        result = resolve_character_target(self.caller, "jackson")
        self.assertIs(result, self.jorge)

    def test_ambiguity_returns_none_and_messages_caller(self):
        """Multiple matches produce disambiguation message + None."""
        second_man = _make_character(
            key="Bob Brown",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-bob",
        )
        self.room.contents = [self.caller, self.jorge, second_man]
        result = resolve_character_target(
            self.caller, "man", candidates=self.room.contents
        )
        self.assertIsNone(result)
        self.caller.msg.assert_called_once()
        message = self.caller.msg.call_args[0][0]
        self.assertIn("Multiple targets match", message)

    def test_empty_query_returns_none(self):
        self.assertIsNone(resolve_character_target(self.caller, ""))
        self.assertIsNone(resolve_character_target(self.caller, "   "))

    def test_caller_excluded_from_results(self):
        """Caller is never a valid identity match for themselves."""
        # Caller's own sdesc contains 'compact'/'woman'. Without
        # exclusion 'woman' would match both caller and Maria.
        result = resolve_character_target(self.caller, "compact")
        # Only the non-caller match (Maria) survives.
        self.assertIs(result, self.maria)

    def test_self_token_blocked_by_default(self):
        """'me'/'self'/'myself' yield None unless allow_self=True."""
        for token in ("me", "self", "myself", "ME", "Self"):
            self.assertIsNone(resolve_character_target(self.caller, token))

    def test_self_token_resolves_when_allowed(self):
        for token in ("me", "self", "myself"):
            self.assertIs(
                resolve_character_target(self.caller, token, allow_self=True),
                self.caller,
            )

    def test_explicit_candidates_override_location(self):
        """Passing candidates= bypasses location.contents."""
        # Caller's room is empty in this test.
        empty_room = _make_room([])
        self.caller.location = empty_room
        result = resolve_character_target(
            self.caller, "man", candidates=[self.jorge]
        )
        self.assertIs(result, self.jorge)


# ===================================================================
# Tests: resolve_character_in_rooms — cross-room scan (advance/charge)
# ===================================================================


class TestResolveCharacterInRooms(TestCase):
    """Cross-room scan used by advance/charge."""

    def setUp(self):
        self.caller = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sleeve_uid="uid-caller",
        )
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.viktor = _make_character(
            key="Viktor Kozlov",
            sex="male",
            height="above-average",
            build="stocky",
            sdesc_keyword="droog",
            sleeve_uid="uid-viktor",
        )
        self.local_room = _make_room([self.caller])
        self.adjacent_room = _make_room([self.jorge, self.viktor])
        self.caller.location = self.local_room

    def test_finds_target_in_adjacent_room(self):
        """Caller in empty room, target in adjacent — resolves."""
        result = resolve_character_in_rooms(
            self.caller, "man", [self.local_room, self.adjacent_room]
        )
        self.assertIs(result, self.jorge)

    def test_local_room_takes_priority(self):
        """Match in caller's own room is returned before adjacent."""
        local_match = _make_character(
            key="Carl Other",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-carl",
        )
        self.local_room.contents = [self.caller, local_match]
        result = resolve_character_in_rooms(
            self.caller, "man", [self.local_room, self.adjacent_room]
        )
        self.assertIs(result, local_match)

    def test_no_match_in_any_room(self):
        result = resolve_character_in_rooms(
            self.caller, "zephyr", [self.local_room, self.adjacent_room]
        )
        self.assertIsNone(result)

    def test_ambiguity_in_one_room_does_not_fall_through(self):
        """Ambiguous match in a room messages caller and stops scan."""
        second_man = _make_character(
            key="Bob Brown",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-bob",
        )
        self.adjacent_room.contents = [self.jorge, second_man]
        result = resolve_character_in_rooms(
            self.caller, "man", [self.local_room, self.adjacent_room]
        )
        self.assertIsNone(result)
        self.caller.msg.assert_called_once()
        message = self.caller.msg.call_args[0][0]
        self.assertIn("Multiple targets match", message)
        self.assertIn("Test Room", message)

    def test_empty_query_returns_none(self):
        self.assertIsNone(
            resolve_character_in_rooms(
                self.caller, "", [self.local_room, self.adjacent_room]
            )
        )

    def test_skips_falsy_rooms(self):
        """None entries in the room list don't crash."""
        result = resolve_character_in_rooms(
            self.caller, "man", [None, self.adjacent_room]
        )
        self.assertIs(result, self.jorge)

    def test_builder_key_fallback_works_cross_room(self):
        """Builder caller can match by .key in an adjacent room."""
        self.caller.locks.check_lockstring = lambda obj, lockstring: True
        result = resolve_character_in_rooms(
            self.caller, "kozlov", [self.local_room, self.adjacent_room]
        )
        self.assertIs(result, self.viktor)


# ===================================================================
# Tests: integration — Character.search override still feeds helper
# ===================================================================


class TestHelperRespectsIdentityPipeline(TestCase):
    """Sanity: helper produces same answers as direct identity_match_characters."""

    def setUp(self):
        self.caller = _make_character(sleeve_uid="uid-caller", sex="female")
        self.jorge = _make_character(
            key="Jorge",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

    def test_ordinal_query_passes_through(self):
        """Ordinals in queries are handled by identity_match_characters."""
        twin1 = _make_character(
            key="Twin One",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-t1",
        )
        twin2 = _make_character(
            key="Twin Two",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-t2",
        )
        candidates = [self.caller, twin1, twin2]
        room = _make_room(candidates)
        self.caller.location = room
        # '2nd man' yields the second match — should not trigger
        # ambiguity message.
        result = resolve_character_target(self.caller, "2nd man")
        self.assertIs(result, twin2)
        self.caller.msg.assert_not_called()
