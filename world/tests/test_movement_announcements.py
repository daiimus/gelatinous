"""
Tests for Phase 2 Φ₅ per-observer rendering of normal exit-traversal
move announcements.

Covers ``Character.announce_move_from`` and
``Character.announce_move_to`` overrides on
``typeclasses/characters.py``, which take over the default Evennia
broadcast so that observers in source/destination rooms see the
mover's name resolved through their own recognition memory.

Run via::

    evennia test world.tests.test_movement_announcements

Aligns with ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
Consistency" (Φ₅) and §"Impact on Existing Systems".
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from world.tests._identity_helpers import (
    apparent_uid_for,
    prepare_mock_for_apparent_uid,
)


def _make_character(
    *,
    key,
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword="man",
    sleeve_uid,
    recognition_memory=None,
):
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
    char._build_clothing_coverage_map = lambda: {}

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

    prepare_mock_for_apparent_uid(char)
    return char


def _make_room(contents, *, name="a room"):
    room = MagicMock()
    room.contents = contents
    room.get_display_name = lambda looker=None, **kw: name
    return room


def _observer_text(observer):
    if not observer.msg.call_args:
        return ""
    args = observer.msg.call_args
    return args.kwargs.get("text") or (args.args[0] if args.args else "")


class TestAnnounceMoveFromPerObserver(TestCase):
    """``Character.announce_move_from`` renders the mover per-observer."""

    def setUp(self):
        self.mover = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.mover): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        self.origin = _make_room(
            [self.mover, self.knower, self.stranger], name="the bar"
        )
        self.destination = _make_room([], name="the street")
        self.mover.location = self.origin

    def _call(self, **kwargs):
        from typeclasses.characters import Character

        return Character.announce_move_from(
            self.mover, self.destination, **kwargs
        )

    def test_knower_sees_assigned_name(self):
        self._call()
        text = _observer_text(self.knower)
        self.assertIn("Jorge", text)
        self.assertIn("leaving the bar", text)
        self.assertIn("heading for the street", text)

    def test_stranger_sees_sdesc(self):
        self._call()
        text = _observer_text(self.stranger)
        self.assertIn("gaunt man", text)
        self.assertIn("leaving the bar", text)

    def test_mover_is_excluded(self):
        self._call()
        self.assertEqual(_observer_text(self.mover), "")

    def test_sdesc_capitalized_at_sentence_start(self):
        """Stranger sees 'A gaunt man' not 'a gaunt man' at sentence start."""
        # Drop knower so we only examine stranger output cleanly.
        self.origin.contents = [self.mover, self.stranger]
        self._call()
        text = _observer_text(self.stranger)
        self.assertIn("A gaunt man", text)

    def test_caller_msg_delegates_to_super(self):
        """When caller passes ``msg=``, we delegate to super() and skip our path."""
        from typeclasses.characters import Character

        with patch.object(
            Character.__mro__[1], "announce_move_from", create=True
        ) as mock_super:
            Character.announce_move_from(
                self.mover, self.destination, msg="custom"
            )
            mock_super.assert_called_once()
        # Our broadcast should not have fired on any observer.
        self.assertEqual(_observer_text(self.knower), "")
        self.assertEqual(_observer_text(self.stranger), "")

    def test_missing_location_short_circuits(self):
        """No location → silent early-return; no exceptions, no broadcast."""
        self.mover.location = None
        # Should not raise.
        self._call()


class TestAnnounceMoveToPerObserver(TestCase):
    """``Character.announce_move_to`` renders the mover per-observer."""

    def setUp(self):
        self.mover = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.mover): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        self.origin = _make_room([], name="the bar")
        self.destination = _make_room(
            [self.mover, self.knower, self.stranger], name="the street"
        )
        self.mover.location = self.destination

    def _call(self, **kwargs):
        from typeclasses.characters import Character

        return Character.announce_move_to(
            self.mover, self.origin, **kwargs
        )

    def test_knower_sees_assigned_name(self):
        self._call()
        text = _observer_text(self.knower)
        self.assertIn("Jorge", text)
        self.assertIn("arrives to the street", text)
        self.assertIn("from the bar", text)

    def test_stranger_sees_sdesc(self):
        self._call()
        text = _observer_text(self.stranger)
        self.assertIn("gaunt man", text)
        self.assertIn("arrives to the street", text)

    def test_mover_is_excluded(self):
        self._call()
        self.assertEqual(_observer_text(self.mover), "")

    def test_sdesc_capitalized_at_sentence_start(self):
        self.destination.contents = [self.mover, self.stranger]
        self._call()
        text = _observer_text(self.stranger)
        self.assertIn("A gaunt man", text)

    def test_source_location_none_falls_back(self):
        """When source_location is None (fresh spawn), use 'somewhere'."""
        from typeclasses.characters import Character

        Character.announce_move_to(self.mover, None)
        text = _observer_text(self.knower)
        self.assertIn("from somewhere", text)

    def test_caller_mapping_delegates_to_super(self):
        from typeclasses.characters import Character

        with patch.object(
            Character.__mro__[1], "announce_move_to", create=True
        ) as mock_super:
            Character.announce_move_to(
                self.mover, self.origin, mapping={"actor": "x"}
            )
            mock_super.assert_called_once()
        self.assertEqual(_observer_text(self.knower), "")
        self.assertEqual(_observer_text(self.stranger), "")
