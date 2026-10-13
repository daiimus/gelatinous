"""A shut door is in plain sight; the room beyond it is not (#3750).

`Room.get_adjacent_character_sightings` ("You see a lone figure to the
north.") walked every visible exit and counted the far room's people
with no thought for door state, while `look north` at the same door
said only that it was closed. Played on live: in the Constabulary Secure
Corridor with Tuck present, closing the north door to Dispatch, `look`
still reported Kiro beyond it. (A shell call of the glance method is not
that evidence: the room's characters section returns early when nobody
else visible stands with the looker, so the glance renders only with
company.) Both renderers now ask one predicate, `Exit.blocks_sight()`:
an ordinary exit never blocks, a `DoorExit` answers from `is_open()` (a
broken door hangs open), the elevator's doors from docking.

Real objects throughout, through the room's own look and the door's own
look, with a real `ElevatorCar` for the elevator. The open-door class is
the vacuity guard: it proves the neighbour IS reported when the door is
open, so the closed-door assertions cannot pass for free.
"""
from unittest import TestCase

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _DoorCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        # A THIRD room reachable only through the door: the harness links
        # room1 -> room2 by an ordinary exit, which would report the
        # neighbour whatever the door did.
        self.beyond = create_object("typeclasses.rooms.Room", key="a flat")
        self.door = create_object("typeclasses.doors.DoorExit", key="south",
                                  location=self.room1, destination=self.beyond)
        self.neighbour = create_object("typeclasses.characters.Character",
                                       key="a neighbour", location=self.beyond)
        self.neighbour.msg = lambda text=None, **kw: None

    def room_glance(self):
        return self.room1.get_adjacent_character_sightings(self.char1) or ""

    def room_look(self):
        return self.room1.return_appearance(self.char1) or ""

    def door_look(self):
        return self.door.return_appearance(self.char1) or ""


class TestTheOpenDoorStillShowsTheNeighbour(_DoorCase):
    """Vacuity guards: the feature must still work through an open door."""

    def setUp(self):
        super().setUp()
        self.door.db.door_closed = False

    def test_the_door_is_open_and_does_not_block(self):
        self.assertTrue(self.door.is_open())
        self.assertFalse(self.door.blocks_sight())

    def test_the_room_glance_reports_them(self):
        self.assertIn("lone figure to the south", self.room_glance())

    def test_the_room_look_carries_it(self):
        # The characters section renders the glance only when someone
        # else visible stands with the looker: `get_display_characters`
        # returns early with the crowd line otherwise (rooms.py, `if not
        # characters`). The harness puts char2 in room1, which is what
        # lets this assertion see the section at all. Whether the glance
        # should render in an empty room is an open ruling (#3750).
        self.assertEqual(self.char2.location, self.room1)
        self.assertIn("lone figure to the south", self.room_look())

    def test_the_door_look_shows_the_far_room(self):
        self.assertIn("To the south you", self.door_look())
        self.assertNotIn("It is closed.", self.door_look())


class TestAClosedDoorHidesTheNeighbour(_DoorCase):
    def test_a_freshly_hung_door_is_shut_and_blocks(self):
        self.assertIs(self.door.db.door_closed, True)
        self.assertTrue(self.door.blocks_sight())

    def test_the_room_glance_is_silent(self):
        self.assertEqual(self.room_glance(), "")

    def test_the_room_look_does_not_mention_them(self):
        look = self.room_look()
        self.assertNotIn("lone figure", look)
        self.assertNotIn("group of people", look)

    def test_a_locked_door_is_silent_too(self):
        self.door.db.door_locked = True
        self.assertEqual(self.room_glance(), "")

    def test_the_door_look_still_describes_the_door_only(self):
        look = self.door_look()
        self.assertIn("It is closed.", look)
        self.assertNotIn("To the south you", look)

    def test_a_broken_door_hangs_open(self):
        self.door.db.door_broken = True
        self.assertFalse(self.door.blocks_sight())
        self.assertIn("lone figure to the south", self.room_glance())

    def test_an_ordinary_exit_never_blocks(self):
        plain = create_object("typeclasses.exits.Exit", key="north",
                              location=self.room1, destination=self.beyond)
        self.assertFalse(plain.blocks_sight())
        glance = self.room_glance()
        self.assertIn("lone figure to the north", glance)
        self.assertNotIn("south", glance)


class TestShutElevatorDoorsHideTheCar(EvenniaTest):
    """A landing's elevator door leads to the car wherever the car is.
    With the car elsewhere the doors are shut, and the glance and the
    exit look must keep the riders to themselves. A real `ElevatorCar`
    (the fixture of test_the_car_refuses_an_undocked_entry): it docks at
    room1 by `db.current_floor`, so the predicate's argument order is
    under test, not mocked around."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.car = create_object("typeclasses.elevator.ElevatorCar",
                                 key="a lift car")
        self.car.db.floors = [[self.room1, "1"], [self.room2, "2"]]
        self.car.db.current_floor = 0
        self.car.db.moving = False
        self.doors = create_object("typeclasses.elevator.ElevatorDoorExit",
                                   key="elevator", location=self.room1,
                                   destination=self.car)
        self.rider = create_object("typeclasses.characters.Character",
                                   key="a rider", location=self.car)
        self.rider.msg = lambda text=None, **kw: None

    def glance(self):
        return self.room1.get_adjacent_character_sightings(self.char1) or ""

    def rider_name(self):
        return self.rider.get_display_name(self.char1)

    def test_the_fixture_docks_the_car_here(self):
        from typeclasses.elevator import car_docked
        self.assertTrue(car_docked(self.car, self.room1))
        self.assertFalse(car_docked(self.room1, self.car))   # order matters

    def test_the_car_docked_here_shows_the_rider(self):
        self.assertFalse(self.doors.blocks_sight())
        self.assertIn("lone figure", self.glance())
        self.assertIn(self.rider_name(),
                      self.doors.return_appearance(self.char1) or "")

    def test_the_car_at_another_floor_blocks_sight(self):
        self.car.db.current_floor = 1
        self.assertTrue(self.doors.blocks_sight())
        self.assertEqual(self.glance(), "")
        self.assertNotIn(self.rider_name(),
                         self.doors.return_appearance(self.char1) or "")

    def test_the_car_in_motion_blocks_sight(self):
        self.car.db.moving = True
        self.assertTrue(self.doors.blocks_sight())
        self.assertEqual(self.glance(), "")

    def test_the_moving_car_sees_nothing_out(self):
        out = self.car._out_exit() or create_object(
            "typeclasses.elevator.ElevatorCarExit", key="out",
            location=self.car, destination=self.room1)
        out.destination = self.room1
        self.assertFalse(out.blocks_sight())
        # control: docked and still, the rider sees the landing's people
        self.assertTrue(self.car.get_adjacent_character_sightings(self.rider))
        self.car.db.moving = True
        self.assertTrue(out.blocks_sight())
        self.assertEqual(self.car.get_adjacent_character_sightings(self.rider), "")
        self.car.db.moving = False
        out.destination = None
        self.assertTrue(out.blocks_sight())


class TestBothRenderersAskTheSamePredicate(TestCase):
    """Source pin, in the style of the secret-door test: the corridor
    glance and the exit look must ask one question about one door."""

    def _method(self, path, name):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / path).read_text(errors="ignore")
        start = body.index(f"def {name}")
        end = body.index("\n    def ", start + 10)
        return body[start:end]

    def test_the_room_glance_asks(self):
        self.assertIn("blocks_sight()", self._method(
            "typeclasses/rooms.py", "get_adjacent_character_sightings"))

    def test_the_exit_look_asks(self):
        self.assertIn("blocks_sight()", self._method(
            "typeclasses/exits.py", "get_display_desc"))
