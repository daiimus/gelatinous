"""The constabulary room type: one type for the whole building (user
call 2026-07-10) — institutional crowd flavour, 'the building
continues' exit prose, and locale-aware secbot sweeps."""

from unittest import TestCase

from world.crowd.crowd_messages import (
    CROWD_MESSAGES, crowd_profile_for_room_type, get_crowd_messages)
from world.crowd.crowd_system import CrowdSystem
from world.director.routines import _sweep_locale
from typeclasses.rooms import TYPE_PLURALS


class _Room:
    def __init__(self, rtype):
        from types import SimpleNamespace
        self.db = SimpleNamespace(type=rtype)


class TestConstabularyCrowd(TestCase):
    def test_type_maps_to_its_own_profile(self):
        self.assertEqual(crowd_profile_for_room_type("constabulary"),
                         "constabulary")
        self.assertEqual(crowd_profile_for_room_type("street"), "default")
        self.assertEqual(crowd_profile_for_room_type("bar"), "interior")

    def test_pools_cover_every_tier_and_sense(self):
        pools = CROWD_MESSAGES["constabulary"]
        for tier in ("sparse", "moderate", "heavy", "packed"):
            for sense in ("visual", "auditory", "olfactory",
                          "tactile", "atmospheric"):
                self.assertTrue(pools[tier][sense],
                                f"empty pool: {tier}/{sense}")

    def test_get_messages_serves_the_profile(self):
        msgs = get_crowd_messages(2, "visual", profile="constabulary")
        self.assertTrue(any("queue" in m or "counter" in m or "docket" in m
                            or "parolee" in m or "grille" in m
                            for m in msgs))

    def test_type_modifier_registered(self):
        self.assertIn("constabulary", CrowdSystem().room_type_modifiers)


class TestSweepLocale(TestCase):
    def test_room_type_drives_the_sweep(self):
        self.assertEqual(_sweep_locale(_Room("street")),
                         "across the street")
        self.assertEqual(_sweep_locale(_Room("constabulary")),
                         "across the floor")
        self.assertEqual(_sweep_locale(_Room("corridor")),
                         "down the corridor")

    def test_unknown_type_stays_ambiguous(self):
        self.assertEqual(_sweep_locale(_Room("bathysphere")),
                         "across its surroundings")
        self.assertEqual(_sweep_locale(None), "across its surroundings")


class TestExitProse(TestCase):
    def test_irregular_plural_registered(self):
        self.assertEqual(TYPE_PLURALS.get("constabulary"),
                         "constabularies")


class TestSecretExits(TestCase):
    """View-locked exits stay out of the exit prose (the standard
    Evennia secret-door mechanism; first consumer: the rooftop hatch)."""

    def test_view_locked_exit_is_filtered(self):
        from unittest.mock import MagicMock
        from typeclasses.rooms import Room
        room = MagicMock()
        room._visible_exits = Room._visible_exits.__get__(room, Room)
        visible = MagicMock()
        visible.access.return_value = True
        hidden = MagicMock()
        hidden.access.return_value = False
        room.exits = [visible, hidden]
        looker = MagicMock()
        result = room._visible_exits(looker)
        self.assertIn(visible, result)
        self.assertNotIn(hidden, result)
        hidden.access.assert_called_with(looker, "view")

    def test_broken_lock_stays_visible(self):
        from unittest.mock import MagicMock
        from typeclasses.rooms import Room
        room = MagicMock()
        room._visible_exits = Room._visible_exits.__get__(room, Room)
        cursed = MagicMock()
        cursed.access.side_effect = RuntimeError("lock exploded")
        room.exits = [cursed]
        self.assertEqual(room._visible_exits(MagicMock()), [cursed])
