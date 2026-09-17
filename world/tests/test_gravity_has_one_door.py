"""Gravity lives in one module and nowhere else (#3579).

Falling used to be re-implemented per verb: the jump command walked a
column, the movement commands had their own item-drop helper, and the
exit typeclass had opinions about who may enter a sky room. Three
implementations, three sets of numbers, three sets of bugs -- and a
"kit" of compat re-exports on top so nobody had to repoint a call site.

The house rule is that a retired name is DELETED, not aliased (#3530):
an alias left behind is a second door onto one decision, and the two
doors drift. These pins are the audit that the old doors are gone:

* ``follow_gravity_to_ground`` -- the per-verb column walk;
* ``apply_gravity_to_items`` -- the per-room item sweep drop callers
  had to remember to fire;
* ``jump_movement_allowed`` -- a movement gate that duplicated the
  room's own flag;
* ``get_sky_room_for_gap`` -- the edge-carried landing room the export
  no longer ships either;
* ``bodyshield_grappler`` -- the grapple landing split, now
  ``world.gravity._land_with_bodyshield``.

And ``commands.combat.CmdJump`` was a backward-compatibility re-export
from the package ``__init__``; the jump command is imported from
``commands.combat.jump``, one door.
"""

from __future__ import annotations

import importlib
import inspect
from unittest import TestCase

#: Every module that used to carry a piece of the fall, or that a
#: caller reached the fall THROUGH. Scanning only the three that
#: defined the old helpers would miss a call site that still names one
#: -- and a call site is exactly where a compat alias gets re-added.
MODULES = (
    "commands.combat.jump",
    "commands.combat.movement",
    "typeclasses.exits",
    "typeclasses.rooms",
    "world.combat.throwing",
    "world.mapping",
    "world.director.travel",
    "commands.CmdInventory",
)


def _code_only(source: str) -> str:
    """Source with whole-line comments stripped.

    Two of these modules discuss the retired names IN A COMMENT, on
    purpose -- ``world/mapping.py`` and ``typeclasses/rooms.py`` both
    record which edge fields #3579 retired and why the export no longer
    ships them. That prose is the opposite of the defect; a raw-text
    scan that failed on it would push a future author into deleting the
    explanation to get the suite green.
    """
    return "\n".join(line for line in source.splitlines()
                      if not line.strip().startswith("#"))

#: Every name the one gravity layer replaced.
RETIRED = (
    "follow_gravity_to_ground",
    "apply_gravity_to_items",
    "jump_movement_allowed",
    "get_sky_room_for_gap",
    "bodyshield_grappler",
)


def _source(name):
    return _code_only(inspect.getsource(importlib.import_module(name)))


class TestTheOldDoorsAreGone(TestCase):
    def test_no_module_still_defines_or_calls_them(self):
        for module in MODULES:
            source = _source(module)
            for name in RETIRED:
                self.assertNotIn(
                    name, source,
                    f"{module} still mentions {name}; the one gravity "
                    f"layer is world/gravity.py",
                )

    def test_the_comment_stripper_does_not_hide_live_code(self):
        """Control on ``_code_only``: it must drop whole-line comments
        and NOTHING else, or every pin above goes quietly vacuous."""
        self.assertEqual(
            _code_only("a = 1\n    # apply_gravity_to_items(room)\nb = 2"),
            "a = 1\nb = 2")
        self.assertIn("apply_gravity_to_items",
                      _code_only("x = apply_gravity_to_items(room)  # old"))

    def test_no_module_still_exports_them(self):
        for module in MODULES:
            imported = importlib.import_module(module)
            for name in RETIRED:
                self.assertFalse(
                    hasattr(imported, name),
                    f"{module}.{name} is still importable",
                )

    def test_the_gravity_module_does_not_carry_them_either(self):
        """Not even as an alias on the new home."""
        import world.gravity as gravity

        for name in RETIRED:
            self.assertFalse(hasattr(gravity, name),
                             f"world.gravity.{name} is a compat alias")

    def test_the_retired_edge_attributes_are_not_read_any_more(self):
        """#3579 retired the edge-carried flight plan: the exit's
        destination IS the air cell and the column is the fall."""
        for module in MODULES:
            source = _source(module)
            self.assertNotIn("fall_distance", source, module)
            self.assertNotIn(".db.sky_room", source, module)
            self.assertNotIn(".db.fall_damage", source, module)


class TestTheModulesStillImport(TestCase):
    """A control. Deleting a name is only a fix if what is left works --
    and a module whose import raises would make every pin above pass by
    never getting as far as the assertion."""

    def test_every_scanned_module_imports(self):
        for module in MODULES:
            self.assertIsNotNone(importlib.import_module(module), module)

    def test_movement_imports(self):
        self.assertIsNotNone(importlib.import_module("commands.combat.movement"))

    def test_jump_imports(self):
        self.assertIsNotNone(importlib.import_module("commands.combat.jump"))

    def test_exits_imports(self):
        self.assertIsNotNone(importlib.import_module("typeclasses.exits"))

    def test_gravity_imports(self):
        self.assertIsNotNone(importlib.import_module("world.gravity"))


class TestThereIsOneDoorOntoTheJumpCommand(TestCase):
    def test_it_is_importable_from_its_own_module(self):
        from commands.combat.jump import CmdJump

        self.assertTrue(callable(CmdJump))

    def test_the_package_re_export_is_gone(self):
        with self.assertRaises(ImportError):
            from commands.combat import CmdJump  # noqa: F401

    def test_the_package_does_not_list_it_either(self):
        import commands.combat as package

        self.assertNotIn("CmdJump", getattr(package, "__all__", ()))


class TestTheRealDoorIsTheRoomHook(TestCase):
    """The positive half: gravity is reached from ONE place, the room's
    arrival hook, so every verb gets it for free."""

    def test_at_object_receive_calls_on_enter_air(self):
        import typeclasses.rooms as rooms

        source = inspect.getsource(rooms.Room.at_object_receive)
        self.assertIn("on_enter_air", source)

    def test_the_jump_verb_no_longer_schedules_a_fall_itself(self):
        source = _source("commands.combat.jump")
        self.assertNotIn("_fall_step", source)
        self.assertNotIn("start_fall", source)
