"""The crane car keeps its four doors and points them per level (#3560).

Owner ruling (2026-09-21): "the exit should always exist as an edge
working for jump off and only sometimes work for jump across." Before
this the car deleted and rebuilt every exit on every ride, so anything
tied to a door -- a grenade rigged across it -- was orphaned: the room
kept rendering a trip wire on a door that no longer existed and `defuse`
called it "not armed". The car now has two permanent doors and each
roof has one, found by key (#2626) and never deleted; `move_to_level`
sets destination, edge flags and locks. Asserts on STATE.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import CraneContainer
from world.gravity import can_leave_by, gap_destination, is_sky
from world.spatial import set_xyz

C = CraneContainer


def _room(tc, key, xyz, sky=False):
    r = create_object(tc, key=key)
    set_xyz(r, *xyz)
    if sky:
        r.db.is_sky_room = True
    return r


def door(room, key):
    return next((e for e in room.exits if e.key == key), None)


class _CraneWorld(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.uc = _room("typeclasses.rooms.Room", "Kaspar Urgent Care - Rooftop (North)", C.UC_ROOF)
        self.qoc = _room("typeclasses.rooms.Room", "Queen of Cups - Rack Roof Southeast", C.QOC_ROOF)
        self.sky = _room("typeclasses.rooms.SkyRoom", "In the Air", C.SKY, sky=True)
        self.shaft = {z: _room("typeclasses.rooms.SkyRoom", "In the Air", (C.COL[0], C.COL[1], z), sky=True)
                      for z in range(C.MIN_Z, C.MAX_Z + 1)}
        self.dig = _room("typeclasses.rooms.Room", "The Marlowe Lot - Foundation", (C.COL[0], C.COL[1], 0))
        self.car = create_object("typeclasses.rooms.CraneContainer", key="Longhaul Container (Crane)")
        self.car.move_to_level(C.MIN_Z, announce=False)

    def _ids(self):
        return {name: d.id for name, d in (
            ("west", door(self.car, "west")), ("north", door(self.car, "north")),
            ("east", door(self.uc, "east")), ("south", door(self.qoc, "south"))) if d is not None}


class TheDoorsAreBornOnceAndNeverDie(_CraneWorld):

    def test_four_doors_survive_every_ride(self):
        born = self._ids()
        self.assertEqual(set(born), {"west", "north", "east", "south"}, born)
        for z in (C.QOC_Z, 5, C.MAX_Z, C.MIN_Z, 7):
            self.car.move_to_level(z, announce=False)
            self.assertEqual(self._ids(), born, f"a door was rebuilt at z{z}")
        self.assertEqual(len(self.car.exits), 2, [e.key for e in self.car.exits])

    def test_the_car_keeps_no_ledger_of_exit_ids(self):
        self.car.move_to_level(C.QOC_Z, announce=False)
        self.assertFalse(self.car.attributes.has("crane_exits"))

    def test_the_shaft_cell_is_the_air_not_the_car(self):
        self.car.move_to_level(C.QOC_Z, announce=False)
        self.assertIs(self.car._shaft_cell(C.QOC_Z), self.shaft[C.QOC_Z])


class DockedAtTheSecondFloor(_CraneWorld):

    def test_west_is_the_walk_off(self):
        west = door(self.car, "west")
        self.assertIs(west.destination, self.uc)
        self.assertIs(west.db.is_edge, False)
        self.assertTrue(west.access(self.char2, "traverse"))
        self.assertIn(west, self.car._visible_exits(self.char2))

    def test_north_is_a_wall(self):
        north = door(self.car, "north")
        self.assertFalse(north.access(self.char2, "view"))
        self.assertFalse(north.access(self.char2, "traverse"))
        self.assertNotIn(north, self.car._visible_exits(self.char2))
        self.assertIn("rack", north.db.err_traverse)
        self.assertIs(north.db.is_edge, False)
        # Behind a shut door is the shaft's air, so a mover that relocates
        # without asking the lock (combat advance/charge) is refused too.
        self.assertTrue(is_sky(north.destination))
        self.assertFalse(can_leave_by(self.char2, north))
        # `jump off north edge` resolves the exit through search: not found.
        self.char2.location = self.car
        self.assertFalse(self.char2.search("north", location=self.car, quiet=True))

    def test_the_urgent_care_roof_walks_onto_the_car(self):
        east = door(self.uc, "east")
        self.assertIs(east.destination, self.car)
        self.assertIs(east.db.is_edge, False)
        self.assertIs(east.db.is_gap, False)

    def test_the_queens_roof_is_an_edge_with_nothing_to_land_on(self):
        south = door(self.qoc, "south")
        self.assertIs(south.db.is_edge, True)
        self.assertIs(south.db.is_gap, True)
        self.assertIs(south.destination, self.shaft[C.QOC_Z])
        self.assertIsNone(south.db.gap_destination)
        self.assertIsNone(gap_destination(south), "a leap should be refused while the car is docked")
        self.assertTrue(south.access(self.char2, "view"))


class LevelWithTheQueensRoof(_CraneWorld):

    def setUp(self):
        super().setUp()
        self.car.move_to_level(C.QOC_Z, announce=False)

    def test_north_is_the_easy_leap(self):
        north = door(self.car, "north")
        self.assertIs(north.destination, self.sky)
        self.assertIs(north.db.is_edge, True)
        self.assertIs(north.db.is_gap, True)
        self.assertEqual(north.db.gap_difficulty, 8)
        self.assertIs(gap_destination(north), self.qoc)
        self.assertTrue(north.access(self.char2, "view"))

    def test_south_hops_back_onto_the_car(self):
        south = door(self.qoc, "south")
        self.assertIs(south.destination, self.car)
        self.assertEqual(south.db.gap_difficulty, 8)
        self.assertIs(gap_destination(south), self.car)

    def test_west_is_chained_across_air(self):
        west = door(self.car, "west")
        self.assertFalse(west.access(self.char2, "view"))
        self.assertFalse(west.access(self.char2, "traverse"))
        self.assertIn("drop", west.db.err_traverse)
        self.assertIs(west.destination, self.shaft[C.QOC_Z], "behind the chained doors is the shaft")
        self.assertFalse(can_leave_by(self.char2, west), "advance/charge could still step out")

    def test_the_urgent_care_roof_has_an_edge_over_the_shaft(self):
        east = door(self.uc, "east")
        self.assertIs(east.destination, self.shaft[C.MIN_Z])
        self.assertIs(east.db.is_edge, True)
        self.assertIs(east.db.is_gap, True)
        self.assertIs(gap_destination(east), self.car)
        self.assertEqual(east.db.gap_difficulty, 8 + 2 * (C.QOC_Z - C.MIN_Z))


class AloftOffLevel(_CraneWorld):

    def test_every_leap_scales_with_the_storeys(self):
        self.car.move_to_level(5, announce=False)
        off = C.QOC_Z - 5
        north = door(self.car, "north")
        south = door(self.qoc, "south")
        east = door(self.uc, "east")
        self.assertEqual(north.db.gap_difficulty, 8 + 2 * off)
        self.assertIs(gap_destination(north), self.qoc)
        self.assertIs(south.destination, self.shaft[C.QOC_Z])
        self.assertEqual(south.db.gap_difficulty, 8 + 2 * off)
        self.assertIs(gap_destination(south), self.car)
        self.assertEqual(east.db.gap_difficulty, 8 + 2 * (5 - C.MIN_Z))
        self.assertIs(gap_destination(east), self.car)
        # Only the LEAP scales. The drop behind each door is what it is
        # wherever the car is parked, so the landing roll never moves.
        for d in (north, south, east):
            self.assertEqual(d.db.edge_difficulty, C.DESCENT_DIFFICULTY, d.key)
        self.car.move_to_level(C.MAX_Z, announce=False)
        self.assertEqual(door(self.uc, "east").db.edge_difficulty, C.DESCENT_DIFFICULTY)
        self.assertEqual(door(self.uc, "east").db.gap_difficulty, 8 + 2 * (C.MAX_Z - C.MIN_Z))

    def test_coming_back_to_the_dock_shuts_and_opens_the_right_doors(self):
        self.car.move_to_level(9, announce=False)
        self.car.move_to_level(C.MIN_Z, announce=False)
        self.assertTrue(door(self.car, "west").access(self.char2, "traverse"))
        self.assertFalse(door(self.car, "north").access(self.char2, "view"))
        self.assertIs(door(self.uc, "east").destination, self.car)
        self.assertIsNone(door(self.qoc, "south").db.gap_destination)


class ATrapRidesTheCar(_CraneWorld):
    """The defect: a grenade rigged to the car's door used to be orphaned
    the moment the car moved, because the door was deleted under it."""

    def _rig(self, exit_obj, return_exit, room):
        g = create_object("typeclasses.items.Item", key="frag grenade", location=room)
        g.db.is_explosive = True
        g.db.rigged_to_exit = exit_obj
        g.db.rigged_by = self.char1
        exit_obj.db.rigged_grenade = g
        return_exit.db.rigged_grenade = g
        g.db.original_integrate = False
        g.db.integrate = True
        g.db.integration_desc = f"A frag grenade is rigged to the {exit_obj.key} exit with a barely visible trip wire."
        g.db.integration_priority = 3
        return g

    def test_a_trap_on_the_car_door_survives_the_ride(self):
        west, east = door(self.car, "west"), door(self.uc, "east")
        g = self._rig(west, east, self.car)
        self.car.move_to_level(C.QOC_Z, announce=False)
        self.car.move_to_level(C.MIN_Z, announce=False)
        self.assertIs(door(self.car, "west"), west)
        self.assertIs(west.db.rigged_grenade, g)
        self.assertIs(east.db.rigged_grenade, g)
        self.assertIs(g.db.rigged_to_exit, west)
        self.assertIs(g.db.integrate, True)
        self.assertIn("west exit", g.db.integration_desc)

    def test_a_trap_on_the_roof_door_waits_for_the_car(self):
        east, west = door(self.uc, "east"), door(self.car, "west")
        g = self._rig(east, west, self.uc)
        self.car.move_to_level(C.MAX_Z, announce=False)
        self.assertIs(door(self.uc, "east"), east)
        self.assertIs(east.db.rigged_grenade, g)
        self.assertIs(g.db.rigged_to_exit, east)
        self.car.move_to_level(C.MIN_Z, announce=False)
        self.assertIs(east.destination, self.car)
        self.assertIs(east.db.rigged_grenade, g)
