"""#3757 -- the stair rooms are `stairwell`, a type the code already knew.

Owner, 2026-10-23/24, on the #3755 footer in the Brackett stairwells and
the Greenhaus stair cores: "the room type will need to be changed from
tenement or farm to stairwell/straiway - right?" / "stairwell should be
fine." Build 170 retyped the 50 live stair rooms (17 Brackett, 33
Greenhaus) and renamed the 30 "Stair Core" rooms "Stairway".

What the word means, pinned here because the retype rides on it:

- an interior for the glance (`room_type_is_open_air` is False), so the
  Greenhaus stairways stop being glanced into from the platforms;
- residential for the crowd prose, since the Brackett stairwells were
  `tenement` and their crowd lines must not switch to the street pool;
- the footer reads the stairs as a building of their own, two sentences
  in the order the exits were built: "There is a tenement to the
  southeast (se). The stairwell continues down (d) and up (u)."

Also already true of the word, and so part of the retype: crowd modifier
+0.1 (`crowd_system.room_type_modifiers`), witness role `tenant`
(`world/director/witness.py`), route cost 1.2 (`world/spatial/pathfind.py`).
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from world.crowd.crowd_messages import (RESIDENTIAL_ROOM_TYPES,
                                        room_type_is_open_air)


class TestTheWord(EvenniaTest):

    def test_a_stairwell_is_not_open_air(self):
        self.assertFalse(room_type_is_open_air("stairwell"))

    def test_a_stairwell_is_residential_like_the_tenement_it_serves(self):
        self.assertIn("stairwell", RESIDENTIAL_ROOM_TYPES)
        self.assertIn("tenement", RESIDENTIAL_ROOM_TYPES)


class TestTheFooterInAStairwell(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room2
        self.exit.locks.add("view:false()")
        self.room1.db.type = "stairwell"

    def room(self, room_type, key):
        room = create.create_object("typeclasses.rooms.Room", key=key)
        room.db.type = room_type
        return room

    def hang(self, key, destination, alias):
        exit_obj = create.create_object(
            "typeclasses.exits.Exit", key=key, location=self.room1,
            destination=destination)
        exit_obj.aliases.add(alias)
        return exit_obj

    def test_a_brackett_stairwell(self):
        self.hang("southeast", self.room("tenement", "North Hall"), "se")
        self.hang("down", self.room("stairwell", "Stairwell below"), "d")
        self.hang("up", self.room("stairwell", "Stairwell above"), "u")
        self.assertEqual(
            self.room1.get_custom_exit_display(self.char1),
            "There is a tenement to the southeast (se). "
            "The stairwell continues down (d) and up (u).")

    def test_a_greenhaus_stairway(self):
        self.hang("north", self.room("farm", "North Platform"), "n")
        self.hang("south", self.room("farm", "South Platform"), "s")
        self.hang("down", self.room("stairwell", "Stairway below"), "d")
        self.hang("up", self.room("stairwell", "Stairway above"), "u")
        self.assertEqual(
            self.room1.get_custom_exit_display(self.char1),
            "There are farms to the north (n) and south (s). "
            "The stairwell continues down (d) and up (u).")

    def test_a_landing_sees_a_stairwell(self):
        self.room1.db.type = "tenement"
        self.hang("west", self.room("stairwell", "Stairwell"), "w")
        self.assertEqual(self.room1.get_custom_exit_display(self.char1),
                         "There is a stairwell to the west (w).")

    def test_the_glance_does_not_look_into_a_stairwell(self):
        self.room1.db.type = "farm"
        stair = self.room("stairwell", "Stairway")
        self.hang("south", stair, "s")
        neighbour = create.create_object("typeclasses.characters.Character",
                                         key="a grower", location=stair)
        neighbour.msg = lambda text=None, **kw: None
        self.assertNotIn("lone figure", self.room1.return_appearance(self.char1))
