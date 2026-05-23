"""
Tests for Phase 2 per-observer rendering in movement commands.

Verifies CmdFlee's three broadcast templates (arrived-after-aimer-flee,
arrived-after-combat-flee, flee-blocked-by-opponents, plus the
left-room flee announcements) render per-observer correctly.

Jump-related ``msg_contents`` sites are item-only (no character refs)
and intentionally left as raw broadcasts.

Run via::

    evennia test world.tests.test_movement_rendering

Aligns with ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
Consistency" Conversion Status.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from world.identity_utils import msg_room_identity
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


def _make_room(contents):
    room = MagicMock()
    room.contents = contents
    return room


def _observer_text(observer):
    if not observer.msg.call_args:
        return ""
    args = observer.msg.call_args
    return args.kwargs.get("text") or (args.args[0] if args.args else "")


class TestMovementPerObserverRendering(TestCase):
    """CmdFlee broadcast templates render per-observer."""

    def setUp(self):
        self.fleer = _make_character(
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
                apparent_uid_for(self.fleer): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    # ---- arrived-after-flee (destination room) ------------------

    def test_arrived_fleeing_aimer_broadcast(self):
        """Destination room sees per-observer 'has arrived, fleeing from an aimer'."""
        dest_room = _make_room([self.fleer, self.knower, self.stranger])

        msg_room_identity(
            location=dest_room,
            template="|y{actor} has arrived, fleeing from an aimer.|n",
            char_refs={"actor": self.fleer},
            exclude=[self.fleer],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("fleeing from an aimer", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("fleeing from an aimer", stext)
        # Fleer themselves excluded
        self.assertEqual(_observer_text(self.fleer), "")

    def test_arrived_fleeing_combat_broadcast(self):
        dest_room = _make_room([self.fleer, self.knower, self.stranger])

        msg_room_identity(
            location=dest_room,
            template="|y{actor} has arrived, fleeing from combat.|n",
            char_refs={"actor": self.fleer},
            exclude=[self.fleer],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("fleeing from combat", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)

    # ---- left-room flee announcement -----------------------------

    def test_flees_via_exit_broadcast(self):
        """Origin room sees per-observer 'flees <exit>' after departure."""
        # Fleer has already moved; not in origin room contents
        origin_room = _make_room([self.knower, self.stranger])

        msg_room_identity(
            location=origin_room,
            template="|y{actor} flees north!|n",
            char_refs={"actor": self.fleer},
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("flees north", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("flees north", stext)

    # ---- flee blocked --------------------------------------------

    def test_flee_blocked_broadcast(self):
        """Room sees per-observer 'tries to flee but is blocked'."""
        # In this scenario the fleer is still in the room.
        room = _make_room([self.fleer, self.knower, self.stranger])

        msg_room_identity(
            location=room,
            template="|y{actor} tries to flee but is blocked by their opponents!|n",
            char_refs={"actor": self.fleer},
            exclude=[self.fleer],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("tries to flee", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("tries to flee", stext)

    # ---- capitalization at sentence start ------------------------

    def test_stranger_sdesc_capitalized_at_sentence_start(self):
        """First placeholder must be capitalized for proper sentence casing."""
        room = _make_room([self.fleer, self.stranger])

        msg_room_identity(
            location=room,
            template="|y{actor} flees north!|n",
            char_refs={"actor": self.fleer},
            exclude=[self.fleer],
        )

        stext = _observer_text(self.stranger)
        # Stranger sees "A gaunt man" (capitalized A), not "a gaunt man"
        self.assertIn("A gaunt man", stext)
