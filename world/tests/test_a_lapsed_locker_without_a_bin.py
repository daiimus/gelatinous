"""A lapsed locker with no lost-property bin empties onto the floor (#3567).

Owner ruling (2026-09-25): when the bank has no bin, a lapsed tenant's
things go on the floor of the room the lockers stand in. Before, the
items stayed in the compartment, the compartment was deleted, and Evennia
sent them to their home, which for a created or spawned item is
DEFAULT_HOME: Limbo, silently. Repossession now logs a warning when a bank has no bin, and the
lapse notice says where the things will go.

Repossession is lazy: it runs whenever anyone uses the bank, so these
tests trigger it through the real `locker` verb run by a different
player, the way it happens in play.
"""
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.lockers import GRACE, CmdLocker

LAPSED_UID = "sleeve-of-a-lapsed-tenant"


class _Lapsed(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.bank = create_object("typeclasses.lockers.LockerBank",
                                  key="bank of lockers", location=self.room1)
        store = self.bank._store(LAPSED_UID, create=True)
        self.boots = create_object("typeclasses.items.Item",
                                   key="pair of boots", location=store)
        self.boots.db.locker_owner = LAPSED_UID
        self.bank.db.leases = {LAPSED_UID: time.time() - GRACE - 60}

    def someone_checks_their_locker(self):
        with mock.patch("evennia.utils.logger.log_warn") as warn:
            self.call(CmdLocker(), "", caller=self.char2, obj=self.bank)
        return warn

    def compartments(self):
        return [o for o in self.bank.contents if o.db.locker_owner]


class WithABin(_Lapsed):
    """Control: the designed path is untouched."""

    def test_the_things_go_into_lost_property(self):
        binx = create_object("typeclasses.items.Item", key="lost-property bin",
                             location=self.room1)
        self.bank.db.forfeit_bin = binx
        warn = self.someone_checks_their_locker()
        self.assertEqual(self.boots.location, binx)
        self.assertFalse(warn.called)
        self.assertEqual(self.compartments(), [])


class WithNoBin(_Lapsed):

    def test_the_things_land_on_the_floor(self):
        self.someone_checks_their_locker()
        self.assertEqual(self.boots.location, self.room1)
        self.assertIsNone(self.boots.db.locker_owner)

    def test_the_compartment_and_the_lease_are_gone(self):
        self.someone_checks_their_locker()
        self.assertEqual(self.compartments(), [])
        self.assertNotIn(LAPSED_UID, self.bank.db.leases or {})

    def test_the_missing_bin_is_logged(self):
        warn = self.someone_checks_their_locker()
        self.assertTrue(warn.called)
        self.assertIn("no lost-property bin", warn.call_args[0][0])

    def test_a_deleted_bin_is_no_bin(self):
        binx = create_object("typeclasses.items.Item", key="lost-property bin",
                             location=self.room1)
        self.bank.db.forfeit_bin = binx
        binx.delete()
        self.someone_checks_their_locker()
        self.assertEqual(self.boots.location, self.room1)


class TheLapseNotice(_Lapsed):
    """Inside the grace window, the tenant is told where things will go."""

    def setUp(self):
        super().setUp()
        self.char1.sleeve_uid = LAPSED_UID
        self.bank.db.leases = {LAPSED_UID: time.time() - 60}   # lapsed, in grace

    def notice(self):
        return self.call(CmdLocker(), "", caller=self.char1, obj=self.bank) or ""

    def test_with_no_bin_it_says_the_floor(self):
        self.assertIn("onto the floor", self.notice())

    def test_control_with_a_bin_it_says_lost_property(self):
        self.bank.db.forfeit_bin = create_object(
            "typeclasses.items.Item", key="lost-property bin", location=self.room1)
        self.assertIn("into lost property", self.notice())


class ABankThatIsNowhere(_Lapsed):
    """Unreachable in play, but it must not lose the lease: with no room to
    drop into, everything stays as it was so a later prune retries."""

    def test_nothing_moves_and_the_lease_survives(self):
        self.bank.location = None
        with mock.patch("evennia.utils.logger.log_warn") as warn:
            self.bank._prune()
        self.assertEqual(len(self.compartments()), 1)
        self.assertIn(LAPSED_UID, self.bank.db.leases)
        self.assertNotIn("emptied", warn.call_args[0][0])
        self.assertIn("left as it was", warn.call_args[0][0])
