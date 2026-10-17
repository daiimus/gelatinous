"""#3753 -- the neighbour glance ("You see a lone figure to the north.")
renders when the looker is alone, and never into somebody's home.

Two faults, one renderer. `Room.get_display_characters` returned early
for an empty room before it reached the glance, so the one case the
glance was written for -- you alone, someone beyond the open doorway --
never showed it. And the glance had no notion of what kind of room it
looked into, so a rented unit with its door standing open was reported
from the landing. Owner, 2026-10-15: "Streets, sure. Cubes? Not so much."
/ "I think it makes more sense for us to have room types...which I think
we already do. It's a very standard mud design."

Everything here goes through `return_appearance` (what `look` prints)
unless the test is about a helper itself. Fixture: a third room beyond an
exit of our own, because the harness already links room1 -> room2 by
"out"; that exit is view-locked so it stays out of the prose, and char2
is parked in room2 so the looker is alone.
"""
import inspect
from unittest import TestCase

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from world import rental
from world.crowd.crowd_messages import room_type_is_residential

LONE = "You see a lone figure to the north."
GROUP = "You see a group of people standing to the north."


class _Alone(EvenniaTest):
    """char1 alone in room1; a neighbour stands in `beyond`, to the north."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room2
        self.exit.locks.add("view:false()")
        self.beyond = create.create_object("typeclasses.rooms.Room", key="beyond")
        self.north = self.make_exit()
        self.neighbour = create.create_object(
            "typeclasses.characters.Character", key="a neighbour",
            location=self.beyond)
        self.neighbour.msg = lambda text=None, **kw: None

    def make_exit(self):
        return create.create_object("typeclasses.exits.Exit", key="north",
                                    location=self.room1, destination=self.beyond)

    def look(self):
        return self.room1.return_appearance(self.char1) or ""

    def others_here(self):
        return [o for o in self.room1.contents
                if o.is_typeclass("typeclasses.characters.Character", exact=False)
                and o != self.char1]


class TestTheGlanceRendersWhenAlone(_Alone):

    def test_the_premise_the_looker_is_alone(self):
        self.assertEqual(self.others_here(), [])

    def test_the_room_look_names_the_direction(self):
        self.assertIn(LONE, self.look())

    def test_two_neighbours_read_as_a_group(self):
        self.char2.location = self.beyond
        self.assertIn(GROUP, self.look())

    def test_the_control_with_company_still_renders_it(self):
        self.char2.location = self.room1
        self.assertIn(LONE, self.look())

    def test_an_empty_room_beyond_says_nothing(self):
        self.neighbour.location = self.room2
        self.assertNotIn("lone figure", self.look())
        self.assertNotIn("group of people", self.look())

    def test_the_glance_sits_before_the_empty_room_return(self):
        """The fault was placement; pin the order so it cannot drift back."""
        from typeclasses.rooms import Room
        body = inspect.getsource(Room.get_display_characters)
        call = "self.get_adjacent_character_sightings(looker)"
        self.assertEqual(body.count(call), 1)
        self.assertLess(body.index(call), body.index("if not characters:"))


class TestAloneTheDoorStillDecides(_Alone):
    """#3750's gate holds for a looker alone: the owner's first condition,
    "make sure this doesn't work between closed doors"."""

    def make_exit(self):
        return create.create_object("typeclasses.doors.DoorExit", key="north",
                                    location=self.room1, destination=self.beyond)

    def test_a_freshly_hung_door_is_shut(self):
        self.assertFalse(self.north.is_open())
        self.assertTrue(self.north.blocks_sight())

    def test_shut_the_room_says_nothing(self):
        self.assertNotIn("lone figure", self.look())

    def test_open_the_room_names_the_direction(self):
        self.north.db.door_closed = False
        self.assertIn(LONE, self.look())

    def test_shut_again_it_goes_quiet(self):
        self.north.db.door_closed = False
        self.assertIn(LONE, self.look())
        self.north.db.door_closed = True
        self.assertNotIn("lone figure", self.look())


class TestHomesAreNotGlancedInto(_Alone):

    def make_exit(self):
        door = create.create_object("typeclasses.doors.DoorExit", key="north",
                                    location=self.room1, destination=self.beyond)
        door.db.door_closed = False
        return door

    def test_the_control_an_untyped_room_is_glanced_into(self):
        self.assertIsNone(self.beyond.db.type)
        self.assertIn(LONE, self.look())

    def test_a_street_is_glanced_into(self):
        self.beyond.db.type = "street"
        self.assertIn(LONE, self.look())

    def test_a_cube_hotel_unit_is_not(self):
        self.beyond.db.type = "cube hotel"
        self.assertNotIn("lone figure", self.look())
        self.assertNotIn("group of people", self.look())

    def test_a_tenement_flat_is_not(self):
        self.beyond.db.type = "tenement"
        self.assertNotIn("lone figure", self.look())

    def test_nor_with_company_in_the_corridor(self):
        self.char2.location = self.room1
        self.beyond.db.type = "tenement"
        self.assertNotIn("lone figure", self.look())

    def test_the_open_door_itself_still_shows_who_is_inside(self):
        """Only the automatic sentence goes; `look north` through an open
        door is a look through an open door."""
        self.beyond.db.type = "tenement"
        shown = self.north.return_appearance(self.char1) or ""
        self.assertIn(self.neighbour.get_display_name(self.char1), shown)

    def test_the_rule_reads_the_room_glanced_into(self):
        """From a residential corridor into a street the glance speaks;
        from the street back into the corridor it does not."""
        back = create.create_object("typeclasses.exits.Exit", key="south",
                                    location=self.beyond, destination=self.room1)
        self.room1.db.type = "tenement"
        self.beyond.db.type = "street"
        self.assertIn(LONE, self.look())
        seen = self.beyond.return_appearance(self.neighbour) or ""
        self.assertNotIn("lone figure to the south", seen)
        self.room1.db.type = "street"
        self.assertIn("You see a lone figure to the south.",
                      self.beyond.return_appearance(self.neighbour) or "")


class TestThePredicate(TestCase):

    def test_the_crowd_layers_residential_words(self):
        for word in ("cube hotel", "tenement", "Cube Hotel", "TENEMENT"):
            self.assertTrue(room_type_is_residential(word), word)

    def test_everything_else_is_not_a_home(self):
        for word in ("street", "alley", "market", "interior", "corridor",
                     "stairwell", "constabulary", "", None):
            self.assertFalse(room_type_is_residential(word), repr(word))


class TestABuildStampsTheType(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.hall = create.create_object(
            "typeclasses.rooms.Room", key="The Brackett Arms - Floor 3 Landing")
        self.hall.db.type = "tenement"
        self.unit = create.create_object(
            "typeclasses.rooms.Room", key="The Brackett Arms - Unit 3B")
        self.door = create.create_object("typeclasses.doors.DoorExit", key="3B",
                                         location=self.hall, destination=self.unit)

    def test_register_writes_the_markers_and_the_type(self):
        rental.register_residence(self.unit, self.door, "The Brackett Arms",
                                  origin="Bhavani Corridor")
        self.assertEqual(rental.cube_door(self.unit), self.door)
        self.assertEqual(self.unit.db.residence_building, "The Brackett Arms")
        self.assertEqual(self.unit.db.residence_origin, "Bhavani Corridor")
        self.assertEqual(self.unit.db.type, "tenement")

    def test_a_typed_unit_keeps_its_own_word(self):
        self.unit.db.type = "cube hotel"
        rental.register_residence(self.unit, self.door, "Queen of Cups")
        self.assertEqual(self.unit.db.type, "cube hotel")

    def test_no_origin_leaves_the_origin_alone(self):
        self.unit.db.residence_origin = "Kaspar Street"
        rental.register_residence(self.unit, self.door, "The Halcyon")
        self.assertEqual(self.unit.db.residence_origin, "Kaspar Street")

    def test_a_corridor_that_is_not_residential_stamps_nothing(self):
        self.hall.db.type = "street"
        rental.register_residence(self.unit, self.door, "Somewhere")
        self.assertIsNone(self.unit.db.type)

    def test_the_stamped_unit_is_a_home_to_the_glance(self):
        rental.register_residence(self.unit, self.door, "The Brackett Arms")
        self.assertTrue(room_type_is_residential(self.unit.db.type))


class TestTheBackfill(EvenniaTest):

    def unit(self, key, hall_type, unit_type=None):
        hall = create.create_object("typeclasses.rooms.Room", key=f"{key} hall")
        hall.db.type = hall_type
        room = create.create_object("typeclasses.rooms.Room", key=key)
        door = create.create_object("typeclasses.doors.DoorExit", key="in",
                                    location=hall, destination=room)
        room.db.cube_door = door
        room.db.residence_building = key.split(" - ")[0]
        if unit_type:
            room.db.type = unit_type
        return room

    def setUp(self):
        super().setUp()
        self.blank = self.unit("The Brackett Arms - Unit 3B", "tenement")
        self.cabin = self.unit("The Halcyon - Cabin 2A", "tenement")
        self.typed = self.unit("Queen of Cups - R1-01", "cube hotel",
                               unit_type="cube hotel")
        self.odd = self.unit("Odd - Unit 1", "street")
        # Carries the attribute name but no door: not a unit.
        self.stray = create.create_object("typeclasses.rooms.Room", key="stray")
        self.stray.db.cube_door = None

    def test_the_dry_run_counts_and_writes_nothing(self):
        report = rental.backfill_residence_types()
        self.assertFalse(report["apply"])
        self.assertEqual(report["units"], 4)
        self.assertEqual(report["typed"], 1)
        self.assertEqual(report["stamped"], {"The Brackett Arms": {"tenement": 1},
                                             "The Halcyon": {"tenement": 1}})
        self.assertEqual([k for k, _ in report["skipped"]], ["Odd - Unit 1"])
        self.assertIsNone(self.blank.db.type)
        self.assertIsNone(self.cabin.db.type)

    def test_apply_writes_and_a_second_run_finds_nothing_to_do(self):
        rental.backfill_residence_types(apply=True)
        self.assertEqual(self.blank.db.type, "tenement")
        self.assertEqual(self.cabin.db.type, "tenement")
        self.assertEqual(self.typed.db.type, "cube hotel")
        self.assertIsNone(self.odd.db.type)
        self.assertIsNone(self.stray.db.type)
        again = rental.backfill_residence_types()
        self.assertEqual(again["stamped"], {})
        self.assertEqual(again["typed"], 3)
        self.assertEqual(again["units"], 4)
