"""A rigged trap detonates fast however it is triggered.

Regression pin for #2547. `REMOTE_DETONATOR_SPEC` builds its trap timing
on "rigging process already sets `grenade.db.fuse_time = 1`".

**Nothing ever wrote that.** The tripwire path hardcoded a local `1`;
the remote-detonation door read `db.fuse_time`, which is the PROTOTYPE
value -- 4 to 10 seconds across the catalogue. So a trap set off by
walking through it went almost at once, and the same trap set off by its
detonator gave the target several seconds to walk out of the blast.

One named constant now, read by both doors. A constant rather than the
written attribute the spec imagined, because rigging would otherwise
have to mutate the grenade's own fuse and restore it on un-rig -- and a
grenade left 1-second after being un-rigged is a worse bug than this
one.
"""

from unittest import TestCase

class TestATrapFuseIsShortAtBothDoors(TestCase):

    def test_the_trap_fuse_is_short(self):
        # Bound off the module, not imported — an import of a name the
        # unfixed tree lacks makes this whole FILE fail to load, and
        # every control in it with it.
        import world.combat.constants as consts

        fuse = getattr(consts, "TRAP_FUSE_TIME", None)
        self.assertIsNotNone(
            fuse, "there is no shared trap fuse, so the tripwire and "
                  "remote doors each invent their own")
        self.assertLessEqual(fuse, 2)

    def test_both_doors_read_the_same_constant(self):
        """The defect was two doors disagreeing about one number."""
        import inspect
        import commands.CmdExplosives as remote
        import commands.explosion_utils as tripwire

        for mod in (remote, tripwire):
            with self.subTest(mod.__name__):
                self.assertIn("TRAP_FUSE_TIME", inspect.getsource(mod))

    def test_the_remote_door_keys_on_being_rigged(self):
        """`rigged_to_exit` is the back-reference rigging writes."""
        import inspect
        import commands.CmdExplosives as remote

        src = inspect.getsource(remote)
        self.assertIn("rigged_to_exit", src)

    def test_no_door_hardcodes_a_bare_trap_fuse(self):
        """The shape, not the instance — a third copy of `= 1` would
        drift the same way."""
        import inspect
        import commands.explosion_utils as tripwire

        src = inspect.getsource(tripwire)
        self.assertNotIn("fuse_time = 1  #", src)

    def test_an_unrigged_explosive_still_uses_its_own_fuse(self):
        """The control — a trap fuse for everything would make every
        thrown grenade instant."""
        import inspect
        import commands.CmdExplosives as remote

        src = inspect.getsource(remote)
        self.assertIn("explosive.db.fuse_time", src)
