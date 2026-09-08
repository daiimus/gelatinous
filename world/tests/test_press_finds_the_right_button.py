"""`press rent` claims a cube, and a dispenser answers to its own
buttons (#2608, #2616).

## #2608 — the verb lost to the name

`_press_pressable` matched the object's name/aliases **first**, and that
match accepted a substring:

```python
if low in names or any(low in name for name in names):
    return bool(obj.at_press(self.caller, None))     # arg dropped
```

All three live kiosks are keyed `rental terminal`, and `"rent" in
"rental terminal"` is True. So the documented `press rent` resolved as
*press the kiosk itself*, arrived at `at_press(presser, None)`, and read
**status** instead of claiming a cube — while `press confirm` and
`press rent 3b` routed correctly, because neither substring-matches the
key. Only the exact phrasing the class docstring advertises was broken.

Three tiers now, in order: an **exact** name or alias, then the
machine's own **buttons**, then a **partial** name. `press kiosk` still
presses the terminal, `press rental` still works, and `press rent`
reaches the claim path.

## #2616 — a machine that always said yes

The house contract is that `at_press` returns False for a label that is
not one of its buttons — `RentalTerminal` ends
`return False  # not one of this machine's buttons`, the elevator car
"only answers to its own name", and `CmdPress` walks the room's
pressables relying on exactly that to know when to try the next one.

`SleeveDispenser.at_press` never referenced `arg` and returned True on
every path. In the Decantation Chamber — the new-character spawn room,
where it is the only pressable — any `press <typo>` dispensed a kit and
reported success, swallowing the usage message a bad press should
produce.

The two are coupled: the middle tier of `_press_pressable` is only
trustworthy if machines honour that contract, so the reorder would have
been unsafe on its own.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdGraffiti import CmdPress


class _PressCase(EvenniaCommandTest):
    def kiosk(self):
        k = create_object("typeclasses.terminals.RentalTerminal",
                          key="rental terminal", location=self.room1)
        cube = create_object("typeclasses.rooms.Room",
                             key="The Brackett Arms - Unit 9B")
        door = create_object("typeclasses.doors.DoorExit", key="door",
                             location=self.room1, destination=cube)
        cube.db.cube_door = door
        k.db.cubes = [cube]
        return k

    def press(self, arg):
        return self.call(CmdPress(), arg, caller=self.char1)


class TestPressRentClaims(_PressCase):
    def test_press_rent_reaches_the_claim_path(self):
        self.kiosk()
        out = self.press("rent")
        self.assertNotIn("Vacancies here", out,
                         "'press rent' read the status board")

    def test_and_actually_registers(self):
        self.kiosk()
        self.press("rent")
        self.assertIsNotNone(self.char1.db.residence)

    def test_pressing_the_kiosk_by_name_still_reads_status(self):
        self.kiosk()
        out = self.press("kiosk")
        self.assertIn("Vacancies here", out)

    def test_the_full_key_still_reads_status(self):
        self.kiosk()
        out = self.press("rental terminal")
        self.assertIn("Vacancies here", out)

    def test_a_partial_name_still_works(self):
        """Tier 3 keeps the forgiveness the substring match provided."""
        self.kiosk()
        out = self.press("rental")
        self.assertIn("Vacancies here", out)

    def test_a_named_unit_still_routes(self):
        """This one was never broken — it does not substring-match."""
        self.kiosk()
        self.press("rent 9b")
        self.assertIsNotNone(self.char1.db.residence)


class TestTheDispenserAnswersItsOwnButtons(EvenniaCommandTest):
    def dispenser(self):
        return create_object("typeclasses.terminals.SleeveDispenser",
                             key="sleeve dispenser", location=self.room1)

    def held(self):
        return [i.key for i in self.char1.contents]

    def test_a_typo_does_not_dispense(self):
        self.dispenser()
        before = self.held()
        self.call(CmdPress(), "wrgbl", caller=self.char1)
        self.assertEqual(self.held(), before)

    def test_a_typo_reports_the_usage(self):
        self.dispenser()
        out = self.call(CmdPress(), "wrgbl", caller=self.char1)
        self.assertIn("Usage", out)

    def test_pressing_it_by_name_still_dispenses(self):
        self.dispenser()
        self.call(CmdPress(), "dispenser", caller=self.char1)
        self.assertTrue(self.held())

    def test_a_real_button_still_dispenses(self):
        self.dispenser()
        self.call(CmdPress(), "issue", caller=self.char1)
        self.assertTrue(self.held())

    def test_it_returns_false_for_a_foreign_label(self):
        """The contract `CmdPress` relies on to try the next machine."""
        d = self.dispenser()
        self.assertFalse(d.at_press(self.char1, "wrgbl"))

    def test_and_true_for_its_own(self):
        d = self.dispenser()
        self.assertTrue(d.at_press(self.char1, "issue"))

    def test_a_bare_press_still_works(self):
        d = self.dispenser()
        self.assertTrue(d.at_press(self.char1, None))


class TestTwoMachinesInOneRoom(_PressCase):
    """The reorder only helps if an unrecognised label falls through to
    the next machine — which is what #2616 was breaking."""

    def test_a_kiosk_verb_is_not_eaten_by_the_dispenser(self):
        create_object("typeclasses.terminals.SleeveDispenser",
                      key="sleeve dispenser", location=self.room1)
        self.kiosk()
        self.press("rent")
        self.assertIsNotNone(self.char1.db.residence)
