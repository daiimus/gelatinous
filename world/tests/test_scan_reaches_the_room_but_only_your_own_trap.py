"""scan reaches the room, and a rigged trap answers only to its rigger (#3351).

`scan <explosive> with <detonator>` searched the caller's own contents only.
Rigging moves the grenade onto the exit in the room, so a trap could be
scanned only BEFORE it was set, and a charge on the floor never. Owner
ruling 2026-09-18: room reach like `defuse`, but a rigged trap is refused
to anyone but the character who rigged it (a new detonator overrides the
old link, so a stranger scanning your trap would own its trigger).
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdExplosives import CmdScan


class ScanReachTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.detonator = create_object("typeclasses.items.RemoteDetonator",
                                       key="VECTOR UEM-3 detonator", location=self.char1)
        self.char1.wield_item(self.detonator, hand="right")

    def _grenade(self, key, location):
        g = create_object("typeclasses.items.Item", key=key, location=location)
        g.db.is_explosive = True
        return g

    def _scanned(self):
        return list(self.detonator.db.scanned_explosives or [])

    def test_control_a_grenade_in_your_pocket_scans(self):
        g = self._grenade("pocket grenade", self.char1)
        self.call(CmdScan(), "pocket grenade with detonator")
        self.assertIn(g.id, self._scanned())

    def test_a_grenade_on_the_floor_scans(self):
        g = self._grenade("floor grenade", self.room1)
        self.call(CmdScan(), "floor grenade with detonator")
        self.assertIn(g.id, self._scanned(), "a grenade in the room was out of reach")

    def test_your_own_rigged_trap_scans(self):
        g = self._grenade("frag grenade", self.room1)
        g.db.rigged_to_exit = self.exit
        g.db.rigged_by = self.char1
        self.call(CmdScan(), "frag grenade with detonator")
        self.assertIn(g.id, self._scanned(), "the rigger could not scan their own trap")

    def test_someone_elses_trap_is_refused(self):
        g = self._grenade("tactical grenade", self.room1)
        g.db.rigged_to_exit = self.exit
        g.db.rigged_by = self.char2
        out = self.call(CmdScan(), "tactical grenade with detonator")
        self.assertNotIn(g.id, self._scanned(), "a stranger took over the trap's trigger")
        self.assertIn("someone else's trap", out or "")

    def test_the_room_reach_does_not_leak_a_strangers_key(self):
        # char1 is a Developer in the harness and bypasses the identity gate,
        # so the searcher here is char2 (a plain player) and the stranger is
        # char1, given an appearance so their sdesc is not their key. An
        # explicit candidate list bypassed the gate and answered "<real key>
        # is not an explosive device."; the default search keeps the gate.
        self.char1.sex = "male"; self.char1.height = "tall"; self.char1.build = "lean"
        seen_as = self.char1.get_display_name(self.char2)
        self.assertNotIn(self.char1.key, seen_as, "fixture: stranger's sdesc still shows their key: %r" % seen_as)
        det = create_object("typeclasses.items.RemoteDetonator", key="VECTOR UEM-3 detonator", location=self.char2)
        self.char2.wield_item(det, hand="right")
        out = self.call(CmdScan(), f"{self.char1.key} with detonator", caller=self.char2) or ""
        self.assertNotIn(f"{self.char1.key} is not an explosive device", out,
                         "scan confirmed a stranger by their real key: %r" % out)
