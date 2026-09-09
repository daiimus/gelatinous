"""The dry run reports its EFFECT, not just its own consistency (#2755).

`@coordseed` is presented as a safe, re-runnable seeding pass. It is
not. `seed_coordinates` reports CONTRADICTIONS -- the same walk reaching
one room two ways with different answers -- and never compares its
result against what is on disk. So `/check` printed:

    Would seed 750 room(s) ... 11 geometry contradiction(s)

while, measured against the live world, the run underneath it would
relocate 27 rooms and land 18 of them on a cell another room already
holds. The safety mechanism reported on the walk's internal consistency,
not on the walk's effect.

Two rooms in one cell is not cosmetic: `distance()` returns 0 and
`bearing()` returns "here" between places that are not the same place,
so signal range, dispatch facing and every other proximity check reads
them as co-located. One of the measured collisions puts Hammett's Boot -
Shin Plate inside the Boot's own sealed hull mass.

The walk is not wrong. It is one of THREE writers of `db.xyz` -- itself,
`@coordset`, and ~40 build scripts placing vertical geometry by hand --
and the only one that behaves as though it were alone. Which of them
OWNS the attribute is an owner call and is deliberately NOT made here.
This makes the effect visible before it happens, and refuses the write
when rooms would stack.

MOVING ROOMS are called out separately rather than counted as drift. An
elevator car and the crane container rewrite their own coordinate as
they travel, so their `xyz` is only true at the instant it is read --
seeding one stamps a fixed answer onto something that moves. Measured
live: 3 such rooms on-grid, the walk reaches 1, and it would relocate 0
today.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import CmdCoordSeed as mod


class _Grid(EvenniaTest):
    def _room(self, key, xyz=None):
        room = create_object("typeclasses.rooms.Room", key=key)
        if xyz is not None:
            mod.set_xyz(room, *xyz)
        return room


class TestThePlanDiffSeesWhatTheWalkWouldDo(_Grid):

    def test_an_unchanged_assignment_is_not_reported(self):
        """Control: a room the walk confirms in place is not a move, or
        every run would look catastrophic."""
        room = self._room("Same", (1, 1, 0))
        with mock.patch.object(mod, "all_coordinate_rooms",
                               return_value=[room]):
            moved, collisions = mod.plan_diff({room: (1, 1, 0)})
        self.assertEqual(moved, [])
        self.assertEqual(collisions, [])

    def test_a_relocation_is_reported(self):
        room = self._room("Mover", (1, 1, 0))
        with mock.patch.object(mod, "all_coordinate_rooms",
                               return_value=[room]):
            moved, _c = mod.plan_diff({room: (2, 1, 0)})
        self.assertEqual([(room, (1, 1, 0), (2, 1, 0))], moved)

    def test_landing_on_an_occupied_cell_is_a_collision(self):
        mover = self._room("Mover", (1, 1, 0))
        sitting = self._room("Sitting", (2, 1, 0))
        with mock.patch.object(mod, "all_coordinate_rooms",
                               return_value=[mover, sitting]):
            _m, collisions = mod.plan_diff({mover: (2, 1, 0)})
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0][0], mover)
        self.assertIn(sitting, collisions[0][3])

    def test_moving_into_a_cell_it_already_owns_is_not_a_collision(self):
        """A room does not collide with itself."""
        room = self._room("Solo", (1, 1, 0))
        with mock.patch.object(mod, "all_coordinate_rooms",
                               return_value=[room]):
            _m, collisions = mod.plan_diff({room: (1, 1, 0)})
        self.assertEqual(collisions, [])

    def test_a_room_with_no_coordinate_yet_is_not_a_relocation(self):
        """Newly assigned is not moved -- nothing is being overwritten."""
        room = self._room("Fresh")
        with mock.patch.object(mod, "all_coordinate_rooms",
                               return_value=[room]):
            moved, _c = mod.plan_diff({room: (3, 3, 0)})
        self.assertEqual(moved, [])


class TestMovingRoomsAreNamed(_Grid):

    def test_an_ordinary_room_is_not_a_mover(self):
        self.assertEqual(mod.moving_rooms([self._room("Street")]), [])

    def test_an_elevator_car_is(self):
        car = create_object("typeclasses.elevator.ElevatorCar", key="Car")
        self.assertEqual(mod.moving_rooms([car]), [car])


class TestItRefusesToStackRooms(EvenniaTest):
    """The refusal is the safety feature, so it gets its own test.

    A dry run that merely PRINTS the collisions still lets the next
    operator run the command without `/check`. Landing 18 rooms on
    occupied cells should take an explicit `/force`.
    """

    def _run(self, switches):
        from commands.CmdCoordSeed import CmdCoordSeed
        cmd = CmdCoordSeed()
        cmd.caller = self.char1
        cmd.switches = list(switches)
        cmd.args = ""
        cmd.msg = lambda text=None, **kw: self.said.append(str(text))
        self.char1.msg = cmd.msg
        cmd.func()

    def setUp(self):
        super().setUp()
        self.said = []
        self.wrote = []
        a = create_object("typeclasses.rooms.Room", key="A")
        b = create_object("typeclasses.rooms.Room", key="B")
        mod.set_xyz(a, 1, 1, 0)
        mod.set_xyz(b, 2, 1, 0)
        self.a, self.b = a, b
        self.patches = [
            mock.patch.object(mod, "pinned_origin", return_value=a),
            mock.patch.object(mod, "seed_coordinates",
                              return_value=({a: (2, 1, 0)}, [])),
            mock.patch.object(mod, "all_coordinate_rooms",
                              return_value=[a, b]),
            mock.patch.object(mod, "set_xyz",
                              side_effect=lambda r, *c: self.wrote.append(r)),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_a_colliding_run_writes_nothing(self):
        self._run([])
        self.assertEqual(self.wrote, [],
                         "it seeded rooms on top of each other")
        self.assertIn("Refusing to seed", " ".join(self.said))

    def test_force_lets_it_through(self):
        """The operator can still do it -- deliberately, and by saying
        so. A guard with no override becomes a reason to edit the guard."""
        self._run(["force"])
        self.assertEqual(self.wrote, [self.a])

    def test_a_dry_run_never_writes_and_still_reports(self):
        self._run(["check"])
        self.assertEqual(self.wrote, [])
        said = " ".join(self.said)
        self.assertIn("would change coordinate", said)
        self.assertIn("OCCUPIED", said)
