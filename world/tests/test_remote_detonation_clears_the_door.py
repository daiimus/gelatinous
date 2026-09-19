"""Every door a trap goes off through erases its registration from BOTH exits (#3388).

A rigged trap goes off three ways. `defuse` cleared the rigged exit's
`rigged_grenade` record and the return exit's; the tripwire's inline copy
cleared only the exit that was walked (its return-exit match ran post-move
against the wrong room), so the other side of the doorway stayed armed for
the fuse second; the remote detonator cleared nothing, leaving both exits
naming a grenade about to be deleted (played: it read back as None). One
eraser, `clear_exit_rigging`, now serves all three doors.
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdExplosives import CmdDefuse, CmdDetonate


class RemoteDetonationClearsTheDoorTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        # self.exit: room1 -> room2. Add the return exit the rig command would also mark.
        self.back = create_object("typeclasses.exits.Exit", key="back", location=self.room2, destination=self.room1)
        self.detonator = create_object("typeclasses.items.RemoteDetonator",
                                       key="VECTOR UEM-3 detonator", location=self.char1)
        self.char1.wield_item(self.detonator, hand="right")

    def _rigged_grenade(self, key="frag grenade"):
        g = create_object("typeclasses.items.Item", key=key, location=self.room1)
        g.db.is_explosive = True
        g.db.rigged_to_exit = self.exit
        g.db.rigged_by = self.char1
        self.exit.db.rigged_grenade = g
        self.back.db.rigged_grenade = g
        self.detonator.db.scanned_explosives = list(self.detonator.db.scanned_explosives or []) + [g.id]
        return g

    def _both_clear(self, why):
        self.assertIsNone(self.exit.db.rigged_grenade, "the rigged exit still names the grenade: " + why)
        self.assertIsNone(self.back.db.rigged_grenade, "the return exit still names the grenade: " + why)

    # --- the eraser itself --------------------------------------------------

    def test_control_the_eraser_clears_both_exits_and_only_its_own_grenade(self):
        g = self._rigged_grenade()
        # A second return exit on the same doorway carrying a DIFFERENT
        # grenade: the scan must match on the grenade, not on the doorway.
        other = create_object("typeclasses.exits.Exit", key="side", location=self.room2, destination=self.room1)
        bystander = create_object("typeclasses.items.Item", key="other grenade", location=self.room1)
        other.db.rigged_grenade = bystander
        # imported here so the module loads on a tree without the helper
        from commands.explosion_utils import clear_exit_rigging
        cleared = clear_exit_rigging(g)
        self.assertEqual(set(cleared), {self.exit, self.back})
        self._both_clear("eraser")
        self.assertEqual(other.db.rigged_grenade, bystander, "another grenade's record was erased")
        self.assertEqual(g.db.rigged_to_exit, self.exit, "defuse and scan still read rigged_to_exit")

    # --- the remote doors (the defect) ----------------------------------------

    def test_detonate_single_erases_the_door(self):
        g = self._rigged_grenade()
        self.call(CmdDetonate(), f"e-{g.id} with detonator")
        self.assertTrue(g.db.pin_pulled, "the remote door did not fire")
        self._both_clear("detonate e-<id>")
        self.assertIsNotNone(g.pk, "fuse should still be running; the grenade is not deleted yet")

    def test_detonate_all_erases_the_door(self):
        g = self._rigged_grenade()
        self.call(CmdDetonate(), "all with detonator")
        self.assertTrue(g.db.pin_pulled)
        self._both_clear("detonate all")

    # --- the tripwire door: both exits, whichever side was walked -------------

    def test_tripwire_forward_erases_both_exits(self):
        g = self._rigged_grenade()
        from commands.explosion_utils import check_rigged_grenade
        self.char2.move_to(self.room2, quiet=True)          # walked room1 -> room2
        self.assertTrue(check_rigged_grenade(self.char2, self.exit))
        self._both_clear("tripwire, forward")

    def test_tripwire_return_erases_both_exits(self):
        g = self._rigged_grenade()
        from commands.explosion_utils import check_rigged_grenade
        self.char2.move_to(self.room2, quiet=True)
        self.char2.move_to(self.room1, quiet=True)          # walked room2 -> room1 through the return exit
        self.assertTrue(check_rigged_grenade(self.char2, self.back))
        self._both_clear("tripwire, return")

    # --- the defuse door still completes (a review caught a NameError here) ---

    def test_defuse_of_a_rigged_trap_completes(self):
        g = self._rigged_grenade()
        cmd = CmdDefuse(); cmd.caller = self.char1
        cmd.handle_defuse_success(g)      # the roll is not under test; the cleanup tail is
        self._both_clear("defuse")
        self.assertIsNone(g.db.rigged_to_exit, "defuse owns clearing rigged_to_exit")
        self.assertIsNone(g.db.rigged_by)
        self.assertFalse(g.db.pin_pulled)
