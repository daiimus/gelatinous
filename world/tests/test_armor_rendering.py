"""
Tests for Phase 2 per-observer rendering in CmdSlot / CmdUnslot.

Verifies the plate install / unslot flows route their
room broadcasts through :func:`msg_room_identity` so each observer sees
the actor rendered according to their own recognition memory.

Tool-degradation broadcasts in ``CmdArmorRepair`` are intentionally
*not* converted: those strings reference only the tool's ``.key`` (no
character) and add no value under per-observer rendering.

Run via::

    evennia test world.tests.test_armor_rendering

Aligns with ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
Consistency" Conversion Status.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from world.tests._identity_helpers import (
    apparent_uid_for,
    prepare_mock_for_apparent_uid,
)


# ===================================================================
# Mock builders
# ===================================================================


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


def _make_carrier(key="plate carrier", slots=("front", "back"), location=None):
    carrier = MagicMock(spec=["key", "is_plate_carrier", "plate_slots",
                              "installed_plates", "location"])
    carrier.key = key
    carrier.is_plate_carrier = True
    carrier.plate_slots = list(slots)
    carrier.installed_plates = {}
    carrier.location = location   # the doors read it for "your" vs "the" (#3619)
    return carrier


def _make_plate(key="ceramic plate"):
    plate = MagicMock(spec=["key", "aliases", "is_armor_plate", "move_to"])
    plate.key = key
    plate.is_armor_plate = True
    plate.aliases = MagicMock()
    plate.aliases.all = lambda: []
    plate.move_to = MagicMock()
    return plate


# ===================================================================
# Helpers
# ===================================================================


def _observer_text(observer):
    if not observer.msg.call_args:
        return ""
    args = observer.msg.call_args
    return args.kwargs.get("text") or (args.args[0] if args.args else "")


# ===================================================================
# Tests
# ===================================================================


class TestArmorPerObserverRendering(TestCase):
    """CmdSlot / CmdUnslot broadcasts render per-observer."""

    def setUp(self):
        self.actor = _make_character(
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
                apparent_uid_for(self.actor): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

        self.room = _make_room([self.actor, self.knower, self.stranger])
        self.actor.location = self.room

        self.carrier = _make_carrier(key="plate carrier", location=self.actor)
        self.plate = _make_plate(key="ceramic plate")

    # ---- install --------------------------------------------------

    def test_install_plate_broadcast(self):
        from commands.CmdArmor import install_plate_from_hand

        self.actor.hands = {"left": self.plate, "right": None}
        install_plate_from_hand(self.actor, self.plate, self.carrier, None)

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("plate carrier", ktext)
        self.assertIn("installs", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("plate carrier", stext)

    # ---- unslot ---------------------------------------------------

    def test_unslot_broadcast(self):
        from commands.CmdArmor import pull_plate_into_hand

        self.carrier.installed_plates = {"front": self.plate}
        pull_plate_into_hand(self.actor, self.plate, self.carrier, "front")

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("plate carrier", ktext)
        self.assertIn("pulls", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)

    # ---- caller exclusion ----------------------------------------

    def test_actor_excluded_from_broadcast(self):
        """Actor receives only first-person msgs, not the room broadcast."""
        from commands.CmdArmor import pull_plate_into_hand

        self.carrier.installed_plates = {"front": self.plate}
        pull_plate_into_hand(self.actor, self.plate, self.carrier, "front")

        actor_texts = [
            (c.args[0] if c.args else c.kwargs.get("text", ""))
            for c in self.actor.msg.call_args_list
        ]
        # Actor's first-person message uses "You pull"
        self.assertTrue(
            any("You pull" in t for t in actor_texts),
            f"Actor missing first-person remove msg: {actor_texts}",
        )
        # Actor must NOT receive the third-person broadcast
        self.assertFalse(
            any("Jorge Jackson pulls a plate" in t for t in actor_texts),
            f"Actor unexpectedly received broadcast: {actor_texts}",
        )
