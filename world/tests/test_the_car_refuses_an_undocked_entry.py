"""The elevator gate lives on the car, and stash carries drop's guards
(#2610, #2611).

## #2610 — eight ungated doors into a moving room

The doors-are-shut rule lived **only** in
`ElevatorDoorExit.at_traverse`, so any exit into the car with a
different typeclass was an ungated door. Verified live across all 14
Brackett floors:

```
floors 2-7    elevator exit typeclass = ElevatorDoorExit
floors 8-15   elevator exit typeclass = Exit          <- no gate
```

Walking `elevator` from those eight landings put the player inside the
car **wherever it currently was**. The build script that made them used
the generic exit typeclass; the earlier floors were fixed afterwards and
these were missed.

Two halves:

* **the world** — `scripts/builds/151_…` retypeclassed the eight
  (`converted: 8`, `ungated remaining: 0`, against a fresh DB backup)
* **the code** — `ElevatorCar.at_pre_object_receive` now refuses anyone
  stepping in from a landing the car is not docked at, so the gate is on
  the thing being entered rather than on each door built onto it

The backstop is deliberately narrow: it refuses only when the source is
a landing **of this shaft** and the car is not there. Staff teleports,
spawns, script placements and — importantly — occupants riding the car
are untouched, since the room moves around them and they never re-enter.

## #2611 — stash skipped two of drop's guards

`LockerBank.stash` resolves against `caller.contents`, which includes
worn garments and integrated cyberware, and neither was refused: you
could file the coat you had on, or a bolted-in limb, into a locker
across town.

**One third of that report is out of date.** It lists the hand-slot
write-back as missing; that was fixed in #2457, and `stash` already
calls `release_slots` explicitly with a comment saying why
`move_hooks=False` makes it necessary. Only the two refusals were
genuinely absent.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _ShaftCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.car = create_object("typeclasses.elevator.ElevatorCar",
                                 key="a lift car")
        self.landing_a = self.room1
        self.landing_b = self.room2
        self.car.db.floors = [[self.landing_a, "1"], [self.landing_b, "2"]]
        self.car.db.current_floor = 0
        self.car.db.moving = False
        self.char1.location = self.landing_a

    def docked_at(self, landing):
        from typeclasses.elevator import car_docked
        return car_docked(self.car, landing)


class TestTheCarIsTheGate(_ShaftCase):
    def test_the_fixture_is_docked_at_the_first_landing(self):
        self.assertTrue(self.docked_at(self.landing_a))
        self.assertFalse(self.docked_at(self.landing_b))

    def test_entering_from_the_docked_landing_works(self):
        self.assertTrue(self.char1.move_to(self.car, quiet=True))
        self.assertEqual(self.char1.location, self.car)

    def test_entering_from_another_landing_is_refused(self):
        """The bug, expressed without any exit at all: even a bare
        `move_to` from an undocked landing must not get you in."""
        self.char1.location = self.landing_b
        self.char1.move_to(self.car, quiet=True)
        self.assertEqual(self.char1.location, self.landing_b)

    def test_a_plain_ungated_exit_no_longer_works(self):
        """Exactly the eight Brackett doors: a `typeclasses.exits.Exit`
        pointing at the car."""
        self.char1.location = self.landing_b
        ungated = create_object("typeclasses.exits.Exit", key="elevator",
                                location=self.landing_b,
                                destination=self.car)
        ungated.at_traverse(self.char1, self.car)
        self.assertEqual(self.char1.location, self.landing_b)

    def test_an_arrival_from_somewhere_else_is_untouched(self):
        """Narrow by design — only landings OF THIS SHAFT are gated, so
        teleports and spawns still work."""
        elsewhere = create_object("typeclasses.rooms.Room", key="a street")
        self.char1.location = elsewhere
        self.assertTrue(self.char1.move_to(self.car, quiet=True))
        self.assertEqual(self.char1.location, self.car)

    def test_a_car_with_no_floors_gates_nothing(self):
        self.car.db.floors = []
        self.char1.location = self.landing_b
        self.assertTrue(self.char1.move_to(self.car, quiet=True))


class TestTheDoorStillGatesToo(_ShaftCase):
    """Belt and braces: the exit typeclass keeps its own check."""

    def test_the_door_refuses_when_undocked(self):
        self.char1.location = self.landing_b
        door = create_object("typeclasses.elevator.ElevatorDoorExit",
                             key="elevator", location=self.landing_b,
                             destination=self.car)
        door.at_traverse(self.char1, self.car)
        self.assertEqual(self.char1.location, self.landing_b)

    def test_the_door_lets_you_through_when_docked(self):
        door = create_object("typeclasses.elevator.ElevatorDoorExit",
                             key="elevator", location=self.landing_a,
                             destination=self.car)
        door.at_traverse(self.char1, self.car)
        self.assertEqual(self.char1.location, self.car)


class TestStashCarriesDropsGuards(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.bank = create_object("typeclasses.lockers.LockerBank",
                                  key="a locker bank", location=self.room1)
        self.char1.location = self.room1
        # `stash` refuses before anything else unless you hold a lease
        # (`_can_use`), so without this the guards under test are
        # unreachable and every assertion below is about the lease.
        # `rent` also charges tokens, so fund it first.
        from typeclasses.lockers import RENT
        self.char1.tokens = RENT * 2
        self.bank.rent(self.char1)
        assert self.bank._leased(self.char1), "fixture holds no lease"
        # ...and `_can_use` also wants the door open. Three preconditions
        # sit above the guards under test; miss any one and the
        # assertions below are about the precondition, not the guard.
        self.bank.set_open(self.char1, True)

    def garment(self):
        obj = create_object("typeclasses.items.Item", key="a coat",
                            location=self.char1)
        obj.coverage = ["chest"]
        obj.worn_desc = "a coat"
        return obj

    def said(self):
        out = []
        self.char1.msg = lambda *a, **k: out.append(str(a[0] if a else ""))
        return out

    def test_a_worn_garment_is_refused(self):
        coat = self.garment()
        self.assertTrue(self.char1.wear_item(coat)[0])
        out = self.said()
        self.bank.stash(self.char1, "coat")
        self.assertEqual(coat.location, self.char1)
        self.assertTrue(any("wearing" in s for s in out), out)

    def test_integrated_cyberware_is_refused(self):
        limb = create_object("typeclasses.items.Item", key="an arm",
                             location=self.char1)
        limb.db.integrated = True
        out = self.said()
        self.bank.stash(self.char1, "arm")
        self.assertEqual(limb.location, self.char1)
        self.assertTrue(any("part of your body" in s for s in out), out)

    def test_the_source_carries_both_refusals(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "lockers.py").read_text(
            errors="ignore")
        start = body.index("def stash")
        end = body.index("def retrieve", start)
        self.assertIn("item.db.integrated", body[start:end])
        self.assertIn("is_item_worn(item)", body[start:end])

    def test_the_hand_release_was_already_there(self):
        """#2611 lists this as missing; #2457 had already fixed it."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "lockers.py").read_text(
            errors="ignore")
        start = body.index("def stash")
        end = body.index("def retrieve", start)
        self.assertIn("release_slots", body[start:end])
