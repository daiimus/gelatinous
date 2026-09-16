"""An explosion severs the grenade<->armor magnetic bond (#3412).

`break_stick()` was written to clear `armor.db.stuck_grenade`,
`grenade.db.stuck_to_armor` and `grenade.db.stuck_to_location` -- and
had ZERO callers.  All three explosion terminators went straight to
`grenade.delete()`, leaving the surviving garment holding an Attribute
row that pointed at a dead dbref.

**What that dangling reference actually did: nothing visible.**  Evennia
never caches an Attribute's deserialized value ("we cannot cache here
since it makes certain cases (such as storing a dbobj which is then
deleted elsewhere) out-of-sync" -- `typeclasses/attributes.py`), and
`delete()` flushes the object from the idmapper cache first, so
`unpack_dbobj` falls through to a real query, raises
`ObjectDoesNotExist` and returns `None`.  Every reader of the bond is
truthiness-guarded on that unpacked value -- `CmdRemove.func`
(`commands/CmdClothing.py`), `Item.return_appearance`
(`typeclasses/items.py`), `get_stuck_grenades_on_character`
(`world/combat/explosives.py`) -- so all three correctly skipped.  The
damage was a stale row, not a traceback.

So the assertion that discriminates is NOT `armor.db.stuck_grenade is
None` (that reads None either way -- `test_the_dangling_ref_read_as_None`
below is the control proving it).  It is the RAW stored value,
`Attribute.db_value`, which held the packed `("__packed_dbobj__", ...)`
tuple of the dead grenade before the fix and holds `None` after it.
"""

from unittest.mock import patch

from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

import commands.explosion_utils as xu


def _exists(dbid):
    """Is the object still in the database?  (Django nulls an instance's
    pk on delete, but asking the DB is unambiguous.)"""
    return ObjectDB.objects.filter(id=dbid).exists()


def _raw_bond(armor):
    """The stored (still-packed) value of the armor's `stuck_grenade` row.

    `armor.db.stuck_grenade` would unpickle a dead dbref back to None and
    hide the very residue this issue is about; `db_value` does not.
    """
    attr = armor.attributes.get("stuck_grenade", return_obj=True)
    return attr.db_value if attr else None


class GrenadeArmorBondSeverance(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.armor = create_object("typeclasses.items.Item",
                                   key="plate carrier", location=self.room1)
        self.grenade = create_object("typeclasses.items.Item",
                                     key="sticky grenade", location=self.armor)
        self.grenade.db.dud_chance = 0.0      # never fizzle: we want the blast
        self.grenade.db.blast_damage = 10
        self.gid = self.grenade.id
        self._stick()

    def _stick(self):
        """The bidirectional bond `establish_stick()` creates."""
        if self.grenade.location != self.armor:
            self.grenade.move_to(self.armor, quiet=True)
        self.armor.db.stuck_grenade = self.grenade
        self.grenade.db.stuck_to_armor = self.armor
        self.grenade.db.stuck_to_location = "chest"

    def _quiet_blast(self):
        """Patch out explosion RESOLUTION -- proximity, damage, adjacent
        rooms -- so the test only exercises the cleanup tail."""
        return (
            patch.object(xu, "get_unified_explosion_proximity", return_value=[]),
            patch.object(xu, "notify_adjacent_rooms_of_explosion"),
            patch.object(xu, "msg_room_identity"),
        )

    def _run(self, fn, *args):
        p1, p2, p3 = self._quiet_blast()
        with p1, p2, p3:
            fn(*args)

    # -- precondition -------------------------------------------------

    def test_the_bond_is_really_there_first(self):
        self.assertEqual(self.armor.db.stuck_grenade, self.grenade)
        self.assertEqual(self.grenade.db.stuck_to_armor, self.armor)
        self.assertIsNotNone(_raw_bond(self.armor))

    # -- the three terminators ----------------------------------------

    def test_standalone_explosion_severs_the_bond(self):
        self._run(xu.explode_standalone_grenade, self.grenade)
        self.assertFalse(_exists(self.gid), "grenade should be deleted")
        self.assertIsNone(self.armor.db.stuck_grenade)
        self.assertIsNone(_raw_bond(self.armor),
                          "armor still stores a packed dbref to the dead grenade")

    def test_auto_defuse_explosion_severs_the_bond(self):
        self._run(xu.trigger_auto_defuse_explosion, self.grenade)
        self.assertFalse(_exists(self.gid), "grenade should be deleted")
        self.assertIsNone(self.armor.db.stuck_grenade)
        self.assertIsNone(_raw_bond(self.armor),
                          "armor still stores a packed dbref to the dead grenade")

    def test_rigged_explosion_severs_the_bond(self):
        """`explode_rigged_grenade` is a closure inside
        `check_rigged_grenade`; capture it off the ticker starter and
        fire it directly."""
        captured = []
        self.exit.db.rigged_grenade = self.grenade
        with patch.object(xu, "start_standalone_grenade_ticker",
                          side_effect=lambda g, cb=None: captured.append(cb)), \
                patch.object(xu, "msg_room_identity"):
            xu.check_rigged_grenade(self.char1, self.exit)
        self.assertTrue(captured and captured[0], "closure not captured")

        # Rigging MOVES the grenade to the trigger's room; re-stick it so
        # the closure sees a stuck grenade at detonation time.
        self._stick()
        self._run(captured[0])
        self.assertFalse(_exists(self.gid), "grenade should be deleted")
        self.assertIsNone(self.armor.db.stuck_grenade)
        self.assertIsNone(_raw_bond(self.armor),
                          "armor still stores a packed dbref to the dead grenade")

    # -- controls ------------------------------------------------------

    def test_an_unstuck_grenade_needs_no_severance(self):
        """CONTROL: the unconditional `break_stick()` call is a no-op on a
        loose grenade -- it must not blow up the ordinary blast path."""
        loose = create_object("typeclasses.items.Item",
                              key="frag grenade", location=self.room1)
        loose.db.dud_chance = 0.0
        loose_id = loose.id
        self._run(xu.explode_standalone_grenade, loose)
        self.assertFalse(_exists(loose_id),
                         "loose grenade should still be deleted")
        # The stuck pair nearby is untouched by someone else's explosion.
        self.assertEqual(self.armor.db.stuck_grenade, self.grenade)

    def test_a_plain_delete_severs_the_bond(self):
        """#3552: the severance lives in `Item.at_object_delete`, so ANY
        deletion -- not only the three explosion terminators -- clears the
        garment's side of the bond. A builder's @destroy is this path."""
        self._stick()
        self.grenade.delete()
        self.assertFalse(ObjectDB.objects.filter(id=self.gid).exists())
        self.assertIsNone(self.armor.db.stuck_grenade)
        self.assertIsNone(_raw_bond(self.armor),
                          "the garment still holds a packed reference to the dead grenade")
