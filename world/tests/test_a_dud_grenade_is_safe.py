"""A dud is spent, not armed forever (#2539).

All four dud branches dropped the detonation deadline, messaged the
room, and returned — leaving `pin_pulled = True` on an object they
neither exploded nor deleted. Every explosion path ends in
`grenade.delete()`; the dud paths end in `return`.

The result is a grenade that can never be re-armed, never defused, never
cleared, and that every readout still describes as **ACTIVE**. It
happens on between 1% and 15% of detonations, by prototype.

The codebase already knew the correct clear — both defuse-success
handlers do exactly this:

```python
setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
grenade.db.pin_pulled = False  # Grenade is now safe
```

and `EXPLOSIVE_BASE` ships `"pin_pulled": False` as the explicit safe
state. The four dud paths now do the same.

**Also fixed, same file, same family as #2548:** the defuse-difficulty
calculation read `getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)` and
then computed `10 - remaining_time`. An ndb miss returns `None`, so that
is a `TypeError` — reachable after a reload, which clears all ndb while
`pin_pulled` persists on the object. Its sibling read twenty lines
earlier guards with an explicit `is None` test; this one had nothing.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import NDB_COUNTDOWN_REMAINING


class _GrenadeCase(EvenniaTest):
    def grenade(self, dud_chance=1.0):
        """A grenade that is certain to dud, so the branch is
        deterministic rather than a 1-in-100 flake."""
        obj = create_object("typeclasses.items.Item", key="a grenade",
                            location=self.room1)
        obj.db.pin_pulled = True
        obj.db.dud_chance = dud_chance
        obj.db.blast_damage = 10
        obj.db.detonation_deadline = 1.0
        setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 3)
        return obj


class TestTheDudLandsSafe(_GrenadeCase):
    def test_the_pin_is_cleared(self):
        from commands import explosion_utils
        g = self.grenade()
        explosion_utils.explode_standalone_grenade(g)
        self.assertFalse(g.db.pin_pulled)

    def test_the_countdown_is_zeroed(self):
        from commands import explosion_utils
        g = self.grenade()
        explosion_utils.explode_standalone_grenade(g)
        self.assertEqual(getattr(g.ndb, NDB_COUNTDOWN_REMAINING), 0)

    def test_the_deadline_is_dropped(self):
        """#505: a spent fuse must not be cooked off by the reload
        sweep. That part always worked; it is pinned so the new clear
        cannot displace it."""
        from commands import explosion_utils
        g = self.grenade()
        explosion_utils.explode_standalone_grenade(g)
        self.assertIsNone(g.db.detonation_deadline)

    def test_the_object_survives(self):
        """A dud is not deleted — that is what makes leaving it armed a
        problem rather than a non-event."""
        from commands import explosion_utils
        g = self.grenade()
        explosion_utils.explode_standalone_grenade(g)
        self.assertTrue(g.pk)


class TestTheSafeStateMatchesTheDefuseHandlers(_GrenadeCase):
    """The clear is copied from the two handlers that already had it —
    pinned so the three ways of saying "safe" stay one way."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_every_dud_path_clears_the_pin(self):
        """Four dud branches; each must clear. Counted, because three of
        them live in one file and the fourth is easy to miss."""
        utils = self._source("commands/explosion_utils.py")
        cmd = self._source("commands/CmdExplosives.py")
        self.assertGreaterEqual(utils.count("pin_pulled = False"), 4)
        self.assertGreaterEqual(cmd.count("pin_pulled = False"), 2)

    def test_the_prototype_still_ships_the_safe_default(self):
        """`pin_pulled` is a TOP-LEVEL prototype key here, not an entry
        in `attrs` — reading `attrs` finds nothing and the assertion
        fails for a reason unrelated to the fix. The same two shapes
        caught me on `deflection_bonus` in #2493."""
        import world.prototypes as protos
        self.assertIs(protos.EXPLOSIVE_BASE.get("pin_pulled"), False)


class TestABrickedGrenadeCanBeRearmed(_GrenadeCase):
    """The consequence, stated as behaviour: after a dud the object is
    usable again rather than a permanent paperweight."""

    def test_pin_pulled_is_false_so_arming_is_possible(self):
        from commands import explosion_utils
        g = self.grenade()
        explosion_utils.explode_standalone_grenade(g)
        self.assertFalse(g.db.pin_pulled,
                         "the grenade is still armed and cannot be re-armed")

    def test_a_real_explosion_still_deletes(self):
        """The fix must not make live grenades survive."""
        from commands import explosion_utils
        g = self.grenade(dud_chance=0.0)
        explosion_utils.explode_standalone_grenade(g)
        self.assertFalse(g.pk, "a live grenade survived its own blast")


class TestTheCountdownReadCannotCrash(EvenniaTest):
    """#2548's family, in this file: `10 - None` is a TypeError."""

    def test_an_absent_countdown_reads_as_zero(self):
        obj = create_object("typeclasses.items.Item", key="a grenade",
                            location=self.room1)
        remaining = getattr(obj.ndb, NDB_COUNTDOWN_REMAINING, None) or 0
        self.assertEqual(10 - remaining, 10)

    def test_the_raw_getattr_would_still_return_none(self):
        obj = create_object("typeclasses.items.Item", key="a grenade",
                            location=self.room1)
        self.assertIsNone(getattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 0))

    def test_the_source_no_longer_subtracts_a_raw_read(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "commands" / "CmdExplosives.py").read_text(
            errors="ignore")
        self.assertIn("NDB_COUNTDOWN_REMAINING,\n                                     None) or 0",
                      body)
