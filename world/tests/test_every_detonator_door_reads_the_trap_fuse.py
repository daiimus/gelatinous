"""Every remote-detonation door, and the list that plans them, reads the
same trap fuse (#3348, #3349).

#2547 ruled that a rigged trap is a trap however it is set off and gave
`detonate e-<id>` the shared ``TRAP_FUSE_TIME``. The other door,
`detonate all`, still armed a rigged trap with its prototype fuse (4-10 s)
and BROADCAST that number to the trap's room -- the walk-out window the
ruling closed -- and `detonate list` printed the same prototype number as
"10s (trap)". One helper, ``armed_fuse``, now answers for all three.

These are behavioural pins, driven through the real methods with stub
objects; the earlier source-string pins in
`test_a_trap_fuse_is_short_at_both_doors.py` were green with the defect.
"""
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import EvenniaTest

from commands import CmdExplosives as xp
from world.combat.constants import TRAP_FUSE_TIME, NDB_COUNTDOWN_REMAINING


def _explosive(test, *, rigged, fuse=10, key="SPDR M9 grenade"):
    """A real Item in the test room, so the command can key dicts on its
    location and read its attributes the way it does in play."""
    from evennia.utils.create import create_object
    e = create_object("typeclasses.items.Item", key=key, location=test.room1)
    e.db.pin_pulled = False
    e.db.fuse_time = fuse
    e.db.rigged_to_exit = test.exit if rigged else None
    e.db.stuck_to_armor = None
    return e


def _detonator(test, *ids):
    from evennia.utils.create import create_object
    d = create_object("typeclasses.items.RemoteDetonator", key="VECTOR UEM-3 detonator", location=test.room1)
    d.db.device_type = "remote_detonator"
    d.db.scanned_explosives = list(ids)
    d.db.max_capacity = 10
    return d


def _caller(detonator, room):
    seen = []
    c = SimpleNamespace(key="Operator", location=room,
                        hands={"right": detonator, "left": None},
                        msg=lambda text=None, **kw: seen.append(str(text)),
                        search=lambda *a, **k: detonator)
    c.seen = seen
    return c


def _capture_room(room):
    seen = []
    def msg_contents(text=None, **kw): seen.append(str(text))
    room.msg_contents = msg_contents
    room.seen = seen
    return room


class TestTheSharedFuseHelper(EvenniaTest):
    def test_a_rigged_trap_gets_the_trap_fuse(self):
        self.assertEqual(xp.armed_fuse(_explosive(self, rigged=True, fuse=10)), TRAP_FUSE_TIME)

    def test_an_unrigged_charge_keeps_its_own_fuse(self):
        self.assertEqual(xp.armed_fuse(_explosive(self, rigged=False, fuse=10)), 10)

    def test_a_charge_with_no_fuse_declared_gets_the_default(self):
        self.assertEqual(xp.armed_fuse(_explosive(self, rigged=False, fuse=None)), 8)


class TestDetonateAllHonoursTheTrapFuse(EvenniaTest):
    def _fire(self, explosive):
        det = _detonator(self, explosive.id); caller = _caller(det, self.room2)
        _capture_room(self.room1)
        cmd = xp.CmdDetonate(); cmd.caller = caller
        with patch("commands.explosion_utils.start_grenade_ticker", lambda g: None), \
             patch.object(xp, "msg_room_identity", lambda **kw: None):
            cmd.detonate_all(caller, det)
        return explosive

    def test_a_rigged_trap_is_armed_at_the_trap_fuse(self):
        e = self._fire(_explosive(self, rigged=True, fuse=10))
        self.assertEqual(getattr(e.ndb, NDB_COUNTDOWN_REMAINING), TRAP_FUSE_TIME)

    def test_the_trap_room_is_told_the_real_number(self):
        e = self._fire(_explosive(self, rigged=True, fuse=10))
        said = strip_ansi(" ".join(e.location.seen))
        self.assertIn(f"{TRAP_FUSE_TIME} second", said, said)
        self.assertNotIn("10 second", said, said)

    def test_an_unrigged_charge_still_uses_its_own_fuse(self):
        e = self._fire(_explosive(self, rigged=False, fuse=10))
        self.assertEqual(getattr(e.ndb, NDB_COUNTDOWN_REMAINING), 10)


class TestDetonateListShowsTheFuseThatWillFire(EvenniaTest):
    def _listing(self, explosive):
        det = _detonator(self, explosive.id); caller = _caller(det, self.room2)
        cmd = xp.CmdDetonateList(); cmd.caller = caller; cmd.cmdstring = "detonate list"
        cmd.args = f" with {det.key}"
        cmd.func()
        return strip_ansi(" ".join(caller.seen))

    def test_a_trap_row_shows_the_trap_fuse(self):
        out = self._listing(_explosive(self, rigged=True, fuse=10))
        self.assertIn(f"{TRAP_FUSE_TIME}s (trap)", out, out)
        self.assertNotIn("10s (trap)", out, out)

    def test_a_ready_row_shows_its_own_fuse(self):
        out = self._listing(_explosive(self, rigged=False, fuse=10))
        self.assertIn("10s", out, out)
