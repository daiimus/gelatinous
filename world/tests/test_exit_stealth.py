"""Concealment must survive a directional glance (#1506)."""

from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class TestExitLookRespectsPerception(EvenniaTest):
    """
    rooms.get_adjacent_character_sightings gated through can_perceive;
    exits._get_exit_character_display did not, so looking at the exit
    named people who were hidden from the room.
    """

    def test_hidden_character_is_not_named_through_the_exit(self):
        self.char2.location = self.room2          # next door
        with mock.patch("world.perception.can_perceive", return_value=False):
            shown = self.exit._get_exit_character_display(self.char1)
        self.assertNotIn(self.char2.key, shown or "")

    def test_visible_character_still_shows(self):
        self.char2.location = self.room2
        with mock.patch("world.perception.can_perceive", return_value=True):
            shown = self.exit._get_exit_character_display(self.char1)
        self.assertTrue(shown)

    def test_empty_destination_is_silent(self):
        for obj in list(self.room2.contents):
            if obj.is_typeclass("typeclasses.characters.Character"):
                obj.location = self.room1
        with mock.patch("world.perception.can_perceive", return_value=True):
            self.assertEqual(self.exit._get_exit_character_display(self.char1), "")
