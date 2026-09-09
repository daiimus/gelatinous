"""The remote detonator's four commands get a regression net (#1512).

#1512: *"a device that destroys things at a distance and it has no
regression net"* -- `scan`, `detonate`, `detonate/list` and `clear`.
Since then `test_hooks_that_are_really_hooks` and
`test_explosions_have_one_resolver` have covered the TYPECLASS side (the
delete hooks that clear dangling references, the capacity report, the
early-detonation delegation). The COMMANDS themselves were still
untouched.

This covers the guards rather than the blast. Detonation itself already
has a resolver test; what had no net at all was everything that decides
whether a signature gets into a detonator's memory in the first place --
and those are refusals, which fail silently by doing nothing visible.

Deliberately NOT asserted here: the damage numbers, the 30%
early-detonation path, and the room messaging. Those belong to the
explosion tests that already exist, and duplicating them here would put
two doors on one decision.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdExplosives import (
    CmdClearDetonator,
    CmdDetonateList,
    CmdScan,
)


class _DetonatorCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.det = create_object("typeclasses.items.RemoteDetonator",
                                 key="a detonator", location=self.char1)
        self.charge = create_object("typeclasses.items.Item",
                                    key="a charge", location=self.char1)
        self.charge.db.is_explosive = True
        # A detonator has to be IN HAND to use, so put it there through
        # the real wield path rather than by writing the slot.
        self.char1.wield_item(self.det, "left_hand")

    def scanned(self):
        return list(self.det.db.scanned_explosives or [])


class TestScanRefusesWhatItShould(_DetonatorCase):

    def test_it_scans_a_real_explosive(self):
        """Control first: the refusals below prove nothing if scanning
        never works at all."""
        self.call(CmdScan(), "charge with detonator")
        self.assertEqual(self.scanned(), [self.charge.id])

    def test_a_non_explosive_is_refused(self):
        plain = create_object("typeclasses.items.Item", key="a rock",
                              location=self.char1)
        out = self.call(CmdScan(), "rock with detonator")
        self.assertIn("not an explosive", out)
        self.assertEqual(self.scanned(), [])
        self.assertTrue(plain.pk)

    def test_a_non_detonator_is_refused(self):
        create_object("typeclasses.items.Item", key="a brick",
                      location=self.char1)
        out = self.call(CmdScan(), "charge with brick")
        self.assertIn("not a remote detonator", out)
        self.assertEqual(self.scanned(), [])

    def test_the_usage_line_is_given_without_the_word_with(self):
        out = self.call(CmdScan(), "charge detonator")
        self.assertIn("Usage: scan", out)
        self.assertEqual(self.scanned(), [])


class TestTheListAndClearDoors(_DetonatorCase):

    def test_the_list_names_a_scanned_charge(self):
        self.call(CmdScan(), "charge with detonator")
        # "list with <detonator>", not "<detonator>" -- the command's
        # own usage line said so and my first version ignored it.
        out = self.call(CmdDetonateList(), "list with detonator")
        self.assertIn("charge", out.lower())

    def test_clear_empties_the_memory(self):
        self.call(CmdScan(), "charge with detonator")
        self.assertEqual(self.scanned(), [self.charge.id])
        self.call(CmdClearDetonator(), "detonator")
        self.assertEqual(self.scanned(), [])

    def test_clearing_does_not_destroy_the_explosive(self):
        """Forgetting a charge is not defusing it -- the thing is still
        sitting wherever it was left."""
        self.call(CmdScan(), "charge with detonator")
        self.call(CmdClearDetonator(), "detonator")
        self.assertTrue(self.charge.pk)
        self.assertIsNone(self.charge.db.scanned_by_detonator)
