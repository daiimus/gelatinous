"""A door that is destroyed takes its trap down with it (#3560).

`Exit` had no delete hook at all, so a destroyed exit left a grenade
rendering a trip wire on a doorway that no longer existed, with `defuse`
refusing it as "not armed". `Exit.at_object_delete` now hands the
grenade to `unrig_grenade`, the one restore door `defuse` also uses.
Asserts on STATE.
"""
import inspect

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _RiggedDoor(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.door = create_object("typeclasses.exits.Exit", key="north",
                                  location=self.room1, destination=self.room2)
        self.back = create_object("typeclasses.exits.Exit", key="south",
                                  location=self.room2, destination=self.room1)
        self.g = create_object("typeclasses.items.Item", key="frag grenade", location=self.room1)
        self.g.db.is_explosive = True
        # What `rig` writes (commands/CmdExplosives.py, CmdRig.rig_grenade).
        self.g.db.rigged_to_exit = self.door
        self.g.db.rigged_by = self.char1
        self.door.db.rigged_grenade = self.g
        self.back.db.rigged_grenade = self.g
        self.g.db.original_integrate = False
        self.g.db.original_integration_desc = None
        self.g.db.original_integration_priority = None
        self.g.db.integrate = True
        self.g.db.integration_desc = "A frag grenade is rigged to the north exit with a barely visible trip wire."
        self.g.db.integration_priority = 3

    def _assert_unrigged(self):
        self.assertIsNone(self.g.db.rigged_to_exit)
        self.assertIsNone(self.g.db.rigged_by)
        self.assertIs(self.g.db.integrate, False, "the room would still render a trip wire")
        self.assertIsNone(self.g.db.integration_desc)
        self.assertIsNone(self.g.db.integration_priority)
        self.assertFalse(self.g.attributes.has("original_integrate"))


class ADestroyedDoorTakesItsTrapDown(_RiggedDoor):

    def test_destroying_the_rigged_door_unrigs_the_grenade(self):
        self.door.delete()
        self._assert_unrigged()
        self.assertIsNone(self.back.db.rigged_grenade, "the far side still names the grenade")
        self.assertEqual(self.g.location, self.room1, "the grenade stays where it lay")

    def test_the_delete_itself_goes_through(self):
        self.door.delete()
        self.assertIsNone(self.door.pk)
        self.assertNotIn("north", [e.key for e in self.room1.exits])

    def test_the_room_hears_the_wire_go_slack(self):
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        self.door.delete()
        self.assertTrue(any("goes slack" in t for t in said), said)

    def test_destroying_the_far_side_leaves_the_trap_on_its_door(self):
        self.back.delete()
        self.assertIs(self.g.db.rigged_to_exit, self.door)
        self.assertIs(self.door.db.rigged_grenade, self.g)
        self.assertIs(self.g.db.integrate, True)
        self.assertIn("north exit", self.g.db.integration_desc)

    def test_a_door_with_no_trap_deletes_quietly(self):
        plain = create_object("typeclasses.exits.Exit", key="east",
                              location=self.room1, destination=self.room2)
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        plain.delete()
        self.assertIsNone(plain.pk)
        self.assertFalse(any("slack" in t for t in said), said)


class DefuseAndTheHookShareOneDoor(_RiggedDoor):

    def test_unrig_grenade_restores_the_same_state(self):
        from commands.explosion_utils import unrig_grenade
        self.assertTrue(unrig_grenade(self.g))
        self._assert_unrigged()
        self.assertIsNone(self.door.db.rigged_grenade)
        self.assertIsNone(self.back.db.rigged_grenade)
        self.assertFalse(unrig_grenade(self.g), "nothing left to take down")

    def test_defuse_goes_through_it(self):
        from commands.CmdExplosives import CmdDefuse
        self.assertIn("unrig_grenade", inspect.getsource(CmdDefuse.cleanup_rigging))

    def test_an_orphan_is_still_put_right(self):
        # The pre-#3560 state: the exit already gone, the pointer reading
        # back as None while the row is still there.
        from commands.explosion_utils import unrig_grenade
        self.door.db.rigged_grenade = None
        self.back.db.rigged_grenade = None
        self.g.attributes.add("rigged_to_exit", None)
        self.assertTrue(unrig_grenade(self.g))
        self._assert_unrigged()

    def test_restores_an_authored_integration(self):
        # A grenade that was already part of the room prose before it was
        # rigged gets its own line back, not a blank.
        self.g.db.original_integrate = True
        self.g.db.original_integration_desc = "A frag grenade sits on the sill."
        self.g.db.original_integration_priority = 5
        self.door.delete()
        self.assertIs(self.g.db.integrate, True)
        self.assertEqual(self.g.db.integration_desc, "A frag grenade sits on the sill.")
        self.assertEqual(self.g.db.integration_priority, 5)
