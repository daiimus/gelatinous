"""Rental boards and lockers (#2457).

Three findings, one of which fixed itself.

1. THE CONFIRM GATE WAS ASKING THE WRONG MACHINE. `_press_rent` decided
   "is this a relocation?" with `unit_matches(current, unit)` -- does the
   typed label denote the cube you live in -- without first asking
   whether the board you are standing at manages that cube. Brackett
   units and Halcyon cabins share 35 labels (7A-12C, confirmed live), so
   a tenant of "The Brackett Arms - Unit 9B" who typed `press rent 9b` at
   the HALCYON kiosk matched their own Brackett cube, the gate concluded
   "not relocating", and they were relocated across the colony on a
   single keystroke. Not recoverable for 48 hours: the old lease is
   already released into a handover window, so pressing `rent 9B` back at
   the Brackett kiosk answers "is registered or in handover".

   The existing tests passed because both used non-colliding labels.

2. THE BOARD ADVERTISED LABELS ITS OWN PARSER REFUSED. `_unit_short`
   stripped exactly one prefix, "unit ", so the Halcyon printed "Vacant:
   Cabin 1B" and then answered `press rent Cabin 1B` with "no unit
   'CABIN 1B' on this board". All 35 of its cabins, live. The printer and
   the parser now share `world.rental.unit_label`.

3. `LockerBank.stash` left the item in hand. That is #2468's invariant
   and is already fixed; it is covered here because this module had NO
   tests at all, which is why it went unnoticed -- an item that was
   stashed in a locked, leased locker could still be `drop`ped from
   anywhere in the colony.
"""
from evennia.utils.test_resources import EvenniaTest

from typeclasses.terminals import RentalTerminal
from world.rental import unit_label, unit_matches


class _Cube:
    """Just a key — `unit_label`/`unit_matches` read nothing else."""

    def __init__(self, key):
        self.key = key


class TestTheBoardLabelTypesBackIn(EvenniaTest):
    """Whatever a board prints, its parser has to accept."""

    KEYS = (
        "The Brackett Arms - Unit 3B",
        "The Halcyon - Cabin 1B",
        "R0-01",
        "Queen of Cups - R2-02",
    )

    def test_every_printed_label_round_trips(self):
        for key in self.KEYS:
            cube = _Cube(key)
            printed = RentalTerminal._unit_short(cube)
            self.assertTrue(
                unit_matches(cube, printed),
                f"board prints {printed!r} for {key!r} and rejects it")

    def test_the_cabin_prefix_is_dropped_like_unit(self):
        self.assertEqual(unit_label(_Cube("The Halcyon - Cabin 1B")), "1B")

    def test_the_unit_prefix_still_is(self):
        self.assertEqual(
            unit_label(_Cube("The Brackett Arms - Unit 3B")), "3B")

    def test_a_bare_id_is_left_alone(self):
        """"R0-01" has no prefix word to drop."""
        self.assertEqual(unit_label(_Cube("R0-01")), "R0-01")
        self.assertEqual(unit_label(_Cube("Queen of Cups - R2-02")), "R2-02")

    def test_the_long_form_is_still_accepted(self):
        """A player who types back the old advertised form is not
        punished for it."""
        self.assertTrue(unit_matches(_Cube("The Halcyon - Cabin 1B"),
                                     "cabin 1b"))


class TestTheConfirmGateAsksTheRightBoard(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tenant = self.char1
        self.here = self.room1
        self.tenant.location = self.here

        self.brackett_9b = self.room2
        self.brackett_9b.key = "The Brackett Arms - Unit 9B"
        self.halcyon_9b = self.room1
        self.halcyon_9b.key = "The Halcyon - Cabin 9B"

        self.kiosk = self.obj1
        self.kiosk.swap_typeclass("typeclasses.terminals.RentalTerminal",
                                  clean_attributes=False,
                                  run_start_hooks="all")
        self.kiosk.location = self.here
        self.kiosk.db.cubes = [self.halcyon_9b]

        self.said = []
        self.tenant.msg = lambda text=None, **kw: self.said.append(str(text))

    def press(self, unit=None, confirm=False):
        self.said.clear()
        self.kiosk._press_rent(self.tenant, unit=unit, confirm=confirm)
        return " ".join(self.said)

    def _live_at_brackett(self):
        from unittest import mock
        return mock.patch("typeclasses.terminals.residence_of",
                          return_value=self.brackett_9b)

    def test_a_colliding_label_on_another_board_still_asks_to_confirm(self):
        """The whole finding: "9B" names both buildings' units."""
        with self._live_at_brackett():
            out = self.press(unit="9b")
        self.assertIn("relocates you", out)

    def test_it_does_not_relocate_without_the_confirm(self):
        with self._live_at_brackett():
            self.press(unit="9b")
        self.assertIs(self.halcyon_9b.db.resident, None)

    def test_no_unit_named_on_another_board_also_asks(self):
        with self._live_at_brackett():
            out = self.press()
        self.assertIn("relocates you", out)

    def test_claiming_the_unit_you_already_live_in_does_not(self):
        """Not a relocation, so it must not demand a confirm."""
        from unittest import mock
        with mock.patch("typeclasses.terminals.residence_of",
                        return_value=self.halcyon_9b):
            out = self.press(unit="9b")
        self.assertNotIn("relocates you", out)


class TestStashingPutsTheItemDown(EvenniaTest):
    """#2468's invariant, exercised through the locker (this module had
    no tests, which is why the hand kept the item)."""

    def setUp(self):
        super().setUp()
        self.bank = self.obj1
        self.bank.swap_typeclass("typeclasses.lockers.LockerBank",
                                 clean_attributes=False,
                                 run_start_hooks="all")
        self.bank.location = self.room1
        self.tenant = self.char1
        self.tenant.location = self.room1
        self.knife = self.obj2
        self.knife.key = "a bone-handled knife"
        self.knife.location = self.tenant
        self.tenant.held_items = {"right_hand": self.knife}

    def _leased(self):
        from unittest import mock
        return mock.patch.object(type(self.bank), "_can_use",
                                 return_value=True)

    def test_stashing_empties_the_hand(self):
        with self._leased():
            self.bank.stash(self.tenant, "knife")
        self.assertNotIn(self.knife,
                         dict(self.tenant.held_items or {}).values())

    def test_the_item_is_actually_in_the_locker(self):
        with self._leased():
            self.bank.stash(self.tenant, "knife")
        self.assertIsNot(self.knife.location, self.tenant)

    def test_it_is_not_in_the_locker_and_in_hand_at_once(self):
        """A stashed item that stays wielded can be dropped from
        anywhere in the colony, straight out of a locked locker."""
        with self._leased():
            self.bank.stash(self.tenant, "knife")
        in_hand = self.knife in dict(self.tenant.held_items or {}).values()
        self.assertFalse(in_hand)
        self.assertIsNot(self.knife.location, self.tenant)
