"""Deleting a seat stands its occupants up (#3570).

`sit` / `lie` write three things: `db.furniture` (occupancy is derived
from it, so it degrades on its own once the seat is gone), and two plain
strings, `db.posture` and the `temp_place` placement line, that outlived
the seat. The room went on describing someone "sitting on a stool" that
no longer existed. `Seating.at_object_delete` runs `_clear_posture` on
every occupant, and must hand on super()'s value, or the delete is vetoed.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdFurniture import CmdLie, CmdSit


class _Seats(EvenniaCommandTest):

    def seat(self, typeclass, key):
        return create_object(typeclass, key=key, location=self.room1)

    def room_text(self):
        return self.room1.return_appearance(self.char2) or ""

    def assertStanding(self, char):
        self.assertEqual(char.db.posture, "standing")
        self.assertIsNone(char.db.furniture)
        self.assertFalse(char.temp_place)


class AStool(_Seats):

    def setUp(self):
        super().setUp()
        self.stool = self.seat("typeclasses.furniture.Furniture", "stool")
        self.call(CmdSit(), "stool", caller=self.char1)

    def test_control_the_room_says_they_are_sitting(self):
        self.assertEqual(self.char1.db.posture, "sitting")
        self.assertIn("sitting on", self.room_text())

    def test_deleting_it_stands_the_sitter_up(self):
        self.assertTrue(self.stool.delete())
        self.assertStanding(self.char1)

    def test_the_room_stops_saying_so(self):
        self.stool.delete()
        self.assertNotIn("sitting on", self.room_text())

    def test_someone_on_another_seat_keeps_sitting(self):
        other = self.seat("typeclasses.furniture.Furniture", "bench")
        self.call(CmdSit(), "bench", caller=self.char2)
        self.stool.delete()
        self.assertEqual(self.char2.db.posture, "sitting")
        self.assertEqual(self.char2.db.furniture, other)


class AnAutoDoc(_Seats):

    def test_deleting_it_gets_the_patient_up(self):
        pod = self.seat("typeclasses.furniture.AutoDoc", "autodoc")
        self.call(CmdLie(), "autodoc", caller=self.char1)
        self.assertEqual(self.char1.db.posture, "lying")
        self.assertTrue(pod.delete())
        self.assertStanding(self.char1)


class ABarCounter(_Seats):
    """`BarCounter(Seating, Item)`: the mixin's hook runs first and must
    hand on to Item's, and let the delete through."""

    def test_deleting_it_stands_the_drinker_and_really_deletes(self):
        bar = self.seat("typeclasses.bar.BarCounter", "bar")
        self.call(CmdSit(), "bar", caller=self.char1)
        self.assertEqual(self.char1.db.furniture, bar)
        self.assertTrue(bar.delete())
        self.assertIsNone(bar.pk)
        self.assertStanding(self.char1)
