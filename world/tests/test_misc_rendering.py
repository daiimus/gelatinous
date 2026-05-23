"""
Tests for Phase 2 Φ₄ (capstone) per-observer rendering.

Covers the three character-naming ``msg_contents`` → ``msg_room_identity``
conversions in:

* ``commands/CmdSpawnMob.py`` — manifest announcement
* ``commands/shop.py`` — purchase room broadcast (with user-customizable
  template that includes ``{buyer}`` plus pre-interpolated
  item/price/shop tokens)
* ``world/combat/explosives.py`` — human-shield grenade broadcast (two
  character refs: grappler + victim)

Item-only ``msg_contents`` sites in ``commands/CmdThrow.py``,
``commands/CmdExplosives.py``, and ``commands/explosion_utils.py`` are
intentionally left raw under the AGENTS.md skip rule for item-only
broadcasts and are not exercised here.

Run via::

    evennia test world.tests.test_misc_rendering

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


class TestSpawnMobPerObserverRendering(TestCase):
    """CmdSpawnMob manifest broadcast renders per-observer."""

    def setUp(self):
        self.mob = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-mob",
        )
        self.spawner = _make_character(
            key="Spawner",
            sex="female",
            sleeve_uid="uid-spawner",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.mob): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_manifest_broadcast_per_observer(self):
        """Room sees per-observer 'flickers into existence'."""
        room = _make_room(
            [self.spawner, self.mob, self.knower, self.stranger]
        )

        msg_room_identity(
            location=room,
            template="{mob} flickers into existence, vacant and twitching.",
            char_refs={"mob": self.mob},
            exclude=[self.spawner],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("flickers into existence", ktext)

        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("flickers into existence", stext)

        # Spawner (caller) excluded
        self.assertEqual(_observer_text(self.spawner), "")

    def test_manifest_capitalized_at_sentence_start(self):
        room = _make_room([self.spawner, self.mob, self.stranger])

        msg_room_identity(
            location=room,
            template="{mob} flickers into existence, vacant and twitching.",
            char_refs={"mob": self.mob},
            exclude=[self.spawner],
        )

        stext = _observer_text(self.stranger)
        # Stranger sees "A gaunt man" (capitalized A)
        self.assertIn("A gaunt man", stext)


class TestShopPurchasePerObserverRendering(TestCase):
    """Shop purchase broadcast renders {buyer} per-observer while keeping
    item/price/shop pre-interpolated from the buyer's perspective."""

    def setUp(self):
        self.buyer = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-buyer",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.buyer): {"assigned_name": "Jorge"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_purchase_broadcast_per_observer(self):
        """Knower and stranger see different rendering of {buyer}."""
        room = _make_room([self.buyer, self.knower, self.stranger])

        # Simulate what shop.py does: pre-interpolate non-character tokens,
        # leave {buyer} as a placeholder for per-observer resolution.
        msg_room = "{buyer} purchases {item} from {shop}."
        room_template = msg_room.format(
            buyer="{buyer}",
            item="a stim",
            price="5cr",
            shop="the vendor",
        )

        msg_room_identity(
            location=room,
            template=room_template,
            char_refs={"buyer": self.buyer},
            exclude=[self.buyer],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("purchases a stim from the vendor", ktext)

        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("purchases a stim from the vendor", stext)

        # Buyer excluded
        self.assertEqual(_observer_text(self.buyer), "")


class TestHumanShieldPerObserverRendering(TestCase):
    """Grenade human-shield observer broadcast uses two character refs."""

    def setUp(self):
        self.grappler = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-grappler",
        )
        self.victim = _make_character(
            key="Victor Victim",
            sleeve_uid="uid-victim",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.grappler): {"assigned_name": "Jorge"},
                apparent_uid_for(self.victim): {"assigned_name": "Victor"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_human_shield_broadcast_per_observer(self):
        """Knower sees assigned names; stranger sees both sdescs."""
        room = _make_room(
            [self.grappler, self.victim, self.knower, self.stranger]
        )

        msg_room_identity(
            location=room,
            template=(
                "|y{grappler} uses {victim} as a human shield against "
                "the explosion!|n"
            ),
            char_refs={
                "grappler": self.grappler,
                "victim": self.victim,
            },
            exclude=[self.grappler, self.victim],
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("Victor", ktext)
        self.assertIn("human shield", ktext)

        stext = _observer_text(self.stranger)
        # Both rendered via sdesc for a stranger
        self.assertIn("gaunt man", stext)
        self.assertIn("human shield", stext)

        # Participants excluded
        self.assertEqual(_observer_text(self.grappler), "")
        self.assertEqual(_observer_text(self.victim), "")

    def test_human_shield_capitalized_at_sentence_start(self):
        room = _make_room([self.grappler, self.victim, self.stranger])

        msg_room_identity(
            location=room,
            template=(
                "|y{grappler} uses {victim} as a human shield against "
                "the explosion!|n"
            ),
            char_refs={
                "grappler": self.grappler,
                "victim": self.victim,
            },
            exclude=[self.grappler, self.victim],
        )

        stext = _observer_text(self.stranger)
        # First placeholder (grappler) should be capitalized after the
        # color code prefix.
        self.assertIn("A gaunt man", stext)
