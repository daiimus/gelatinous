"""slot / unslot accept the multi-word names every plate and carrier has (#3365).

Both verbs split on whitespace and took the FIRST token as the item, so
`slot standard plate in plate carrier` parsed as plate="standard",
carrier="plate", slot="in", and `unslot standard plate` printed usage --
there was no way to unslot a shipped plate by its real name. The same
bug was fixed for `repair` in #2521 (read the keyword from the END, keep
the phrase); this applies that shape to slot/unslot.

Asserts on STATE (carrier.installed_plates, plate.location), not on
captured text -- the command's messages are the wrong thing to pin.
"""
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands import CmdArmor
from commands.CmdArmor import CmdSlot, CmdUnslot
from world.prototypes import PLATE_CARRIER, STANDARD_PLATE, CERAMIC_PLATES

_parse_slot = getattr(CmdArmor, "parse_slot_args", None)
_parse_unslot = getattr(CmdArmor, "parse_unslot_args", None)


class SlotTakesWholeNamesTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.carrier = spawn(PLATE_CARRIER)[0]
        self.plate = spawn(STANDARD_PLATE)[0]
        self.trauma = spawn(CERAMIC_PLATES)[0]
        for o in (self.carrier, self.plate, self.trauma):
            o.move_to(self.char1, quiet=True)

    def _installed(self):
        return {k: v for k, v in (self.carrier.installed_plates or {}).items() if v}

    # --- the defect ---------------------------------------------------------

    def test_slot_with_in_installs_by_full_names(self):
        self.call(CmdSlot(), "standard plate in plate carrier")
        self.assertIn(self.plate, self._installed().values(),
                      "standard plate was not installed; installed=%r" % self._installed())
        self.assertEqual(self.plate.location, self.carrier)

    def test_slot_with_trailing_slot_name(self):
        self.call(CmdSlot(), "trauma plate in plate carrier front")
        self.assertIs(self._installed().get("front"), self.trauma)

    def test_slot_two_word_slot_name(self):
        self.call(CmdSlot(), "trauma plate in plate carrier left side")
        self.assertIs(self._installed().get("left_side"), self.trauma)

    def test_unslot_by_full_plate_name(self):
        # The by-name path searches WORN carriers only (#3463, filed
        # separately); wear it so this test exercises the parse, not that.
        self.char1.wear_item(self.carrier)
        self.call(CmdSlot(), "standard plate in plate carrier")
        assert self.plate in self._installed().values()
        self.call(CmdUnslot(), "standard plate")
        self.assertNotIn(self.plate, self._installed().values(), "plate still installed after unslot")
        self.assertEqual(self.plate.location, self.char1)

    def test_unslot_from_full_carrier_name(self):
        self.call(CmdSlot(), "standard plate in plate carrier front")
        assert self.plate in self._installed().values(), "precondition: install failed"
        self.call(CmdUnslot(), "standard plate from plate carrier")
        self.assertNotIn(self.plate, self._installed().values())

    def test_unslot_slot_from_carrier(self):
        self.call(CmdSlot(), "standard plate in plate carrier back")
        assert self._installed().get("back") is self.plate, "precondition: install failed"
        self.call(CmdUnslot(), "back from plate carrier")
        self.assertIsNone(self._installed().get("back"))

    def test_slot_without_in_resolves_the_split(self):
        # "slot standard plate plate carrier" -- no keyword, still works.
        self.call(CmdSlot(), "standard plate plate carrier")
        self.assertIn(self.plate, self._installed().values())

    # --- parser guards (skip on the unfixed tree; the e2e tests above
    #     are the discriminators) ------------------------------------------

    def test_parse_slot_args(self):
        if _parse_slot is None: self.skipTest("parser absent")
        self.assertEqual(_parse_slot("standard plate in plate carrier".split()),
                         ("standard plate", "plate carrier", None))
        self.assertEqual(_parse_slot("trauma plate in plate carrier front".split()),
                         ("trauma plate", "plate carrier", "front"))
        self.assertEqual(_parse_slot("trauma plate in plate carrier left side".split()),
                         ("trauma plate", "plate carrier", "left_side"))
        self.assertEqual(_parse_slot("plate carrier".split()), ("plate carrier", None, None))

    def test_parse_unslot_args(self):
        if _parse_unslot is None: self.skipTest("parser absent")
        self.assertEqual(_parse_unslot("standard plate".split()), ("standard plate", None))
        self.assertEqual(_parse_unslot("standard plate from plate carrier".split()),
                         ("standard plate", "plate carrier"))
        self.assertEqual(_parse_unslot("front from plate carrier".split()), ("front", "plate carrier"))

    def test_help_examples_use_shipped_names(self):
        # The docstring IS the help; its examples must be runnable.
        for cls, needle in ((CmdSlot, "slot standard plate in plate carrier"),
                            (CmdUnslot, "unslot trauma plate from plate carrier")):
            self.assertIn(needle, cls.__doc__ or "", "%s help lacks a runnable example" % cls.__name__)
