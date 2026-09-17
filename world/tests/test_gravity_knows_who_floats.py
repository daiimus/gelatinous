"""The gravity layer's pure predicates (#3579).

Every one of these guards a defect that has already cost the colony a
day somewhere else in the tree:

* **Truthiness lied.** ``db.is_sky_room`` and ``db.stays_aloft`` are
  authored attributes, and a builder who types ``1`` or ``"yes"`` means
  something different from a flag the system set. ``world/spatial/
  pathfind.py:180-185`` records what happened the last time a sky test
  was truthy rather than ``is True``. Both predicates are strict.
* **An ndb miss answers None, never the default.** Evennia's DbHolder
  returns ``None`` for a key it does not have, so
  ``getattr(obj.ndb, key, 0)`` yields ``None`` and ``None > 0``
  raises TypeError. ``has_airborne_token`` has to survive a body that
  has never leapt -- which is nearly every body.
* **The down exit is keyed three ways.** ``@airfill`` writes key
  "down" with alias "d"; older build scripts wrote the key "d" alone.
  ``down_exit`` reads ``cell.exits`` (never ``room.search``, which
  needs a searcher) and accepts either, by key or by alias.
* **The rooftop audience is the point.** ``neighbour_surfaces`` is
  what lets a body be seen falling PAST a roof. It must exclude the
  down exit (that is the column, not a neighbour) and any destination
  that is itself air (a watcher there already gets the in-cell line).

The doubles use a ``db`` stand-in that answers ``None`` for anything
unset, copied from test_build_tools.py:74-94 -- a bare SimpleNamespace
raises where a real ``db`` answers None, which makes it a STRICTER
object than the thing it stands in for.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.gravity import (
    can_stay_up,
    down_exit,
    has_airborne_token,
    is_sky,
    is_stranded_aloft,
    neighbour_surfaces,
)


class _DB(SimpleNamespace):
    """A ``db`` handler, which answers None for anything unset."""

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return None


def _room(**flags):
    return SimpleNamespace(db=_DB(**flags), key="a room")


def _exit(key, destination, aliases=()):
    ex = MagicMock()
    ex.key = key
    ex.destination = destination
    ex.aliases.all.return_value = list(aliases)
    return ex


def _cell(*exits, sky=True):
    return SimpleNamespace(db=_DB(is_sky_room=sky or None), key="In the Air",
                           exits=list(exits))


class TestOnlyALiteralTrueIsSky(TestCase):
    def test_the_flag_set(self):
        self.assertTrue(is_sky(_room(is_sky_room=True)))

    def test_an_unflagged_room(self):
        self.assertFalse(is_sky(_room()))

    def test_the_flag_explicitly_false(self):
        self.assertFalse(is_sky(_room(is_sky_room=False)))

    def test_a_truthy_one_is_not_a_flag(self):
        """A builder's ``1`` is not the system's ``True``."""
        self.assertFalse(is_sky(_room(is_sky_room=1)))

    def test_a_truthy_string_is_not_a_flag(self):
        self.assertFalse(is_sky(_room(is_sky_room="yes")))

    def test_none_is_not_a_room(self):
        self.assertFalse(is_sky(None))

    def test_an_object_with_no_db_at_all(self):
        self.assertFalse(is_sky(SimpleNamespace()))


class TestOnlyALiteralTrueStaysUp(TestCase):
    def test_the_flag_set(self):
        self.assertTrue(can_stay_up(_room(stays_aloft=True)))

    def test_unset(self):
        self.assertFalse(can_stay_up(_room()))

    def test_a_truthy_one_is_not_a_flag(self):
        self.assertFalse(can_stay_up(_room(stays_aloft=1)))

    def test_explicitly_false(self):
        self.assertFalse(can_stay_up(_room(stays_aloft=False)))

    def test_none(self):
        self.assertFalse(can_stay_up(None))


class TestTheLeapTokenSurvivesAnNdbMiss(EvenniaTest):
    """The real trap: on a real Evennia object a missing ndb key reads
    ``None``, so any comparison against it raises unless the read is
    coerced. Run against a REAL character, because a SimpleNamespace
    double is exactly the thing that would not reproduce it."""

    def test_a_body_that_has_never_leapt_does_not_raise(self):
        self.assertIs(getattr(self.char1.ndb, "airborne_token", 0), None,
                      "premise: an ndb miss answers None, not the default")
        self.assertFalse(has_airborne_token(self.char1))

    def test_a_spent_token_is_not_a_token(self):
        self.char1.ndb.airborne_token = 0
        self.assertFalse(has_airborne_token(self.char1))

    def test_a_live_token(self):
        self.char1.ndb.airborne_token = 1
        self.assertTrue(has_airborne_token(self.char1))

    def test_an_object_with_no_ndb_at_all(self):
        self.assertFalse(has_airborne_token(SimpleNamespace()))


class TestFindingTheWayDown(TestCase):
    def test_by_key_down(self):
        street = _room()
        ex = _exit("down", street)
        self.assertIs(down_exit(_cell(ex)), ex)

    def test_by_key_d(self):
        ex = _exit("d", _room())
        self.assertIs(down_exit(_cell(ex)), ex)

    def test_by_key_regardless_of_case(self):
        ex = _exit("Down", _room())
        self.assertIs(down_exit(_cell(ex)), ex)

    def test_by_alias_d(self):
        ex = _exit("downward", _room(), aliases=["d"])
        self.assertIs(down_exit(_cell(ex)), ex)

    def test_by_alias_down(self):
        ex = _exit("descend", _room(), aliases=["DOWN"])
        self.assertIs(down_exit(_cell(ex)), ex)

    def test_a_cell_with_only_sideways_exits(self):
        self.assertIsNone(down_exit(_cell(_exit("north", _room()))))

    def test_a_cell_with_no_exits_at_all(self):
        """81 of the colony's 155 sky rooms are exitless."""
        self.assertIsNone(down_exit(_cell()))

    def test_an_exit_whose_aliases_handler_explodes(self):
        """A double without aliases must not take the fall down with it."""
        ex = MagicMock()
        ex.key = "north"
        ex.destination = _room()
        ex.aliases.all.side_effect = RuntimeError("no aliases here")
        self.assertIsNone(down_exit(_cell(ex)))

    def test_no_cell(self):
        self.assertIsNone(down_exit(None))


class TestWhoCanSeeYouFallPast(TestCase):
    def test_the_walkable_neighbour_is_listed_with_its_direction(self):
        roof = _room()
        cell = _cell(_exit("west", roof), _exit("down", _room()))
        self.assertEqual(neighbour_surfaces(cell), [("west", roof)])

    def test_the_down_exit_is_never_a_neighbour(self):
        street = _room()
        cell = _cell(_exit("down", street))
        self.assertEqual(neighbour_surfaces(cell), [])

    def test_the_down_exit_is_excluded_even_when_keyed_d(self):
        street = _room()
        cell = _cell(_exit("d", street))
        self.assertEqual(neighbour_surfaces(cell), [])

    def test_another_air_cell_is_not_a_surface(self):
        cell = _cell(_exit("east", _room(is_sky_room=True)))
        self.assertEqual(neighbour_surfaces(cell), [])

    def test_an_exit_to_nowhere_is_not_a_surface(self):
        cell = _cell(_exit("east", None))
        self.assertEqual(neighbour_surfaces(cell), [])

    def test_several_roofs_all_appear(self):
        north, south = _room(), _room()
        cell = _cell(_exit("north", north), _exit("down", _room()),
                     _exit("south", south), _exit("up", _room(is_sky_room=True)))
        self.assertEqual(neighbour_surfaces(cell), [("north", north),
                                                    ("south", south)])

    def test_a_vertical_neighbour_is_not_beside_you(self):
        """An `up` exit onto a walkable roof is the cell ABOVE, not a
        surface beside it -- telling that roof someone fell past "to the
        down" would be nonsense."""
        above = _room()
        self.assertEqual(neighbour_surfaces(_cell(_exit("up", above))), [])
        self.assertEqual(neighbour_surfaces(_cell(_exit("u", above))), [])

    def test_a_cell_with_no_exits(self):
        self.assertEqual(neighbour_surfaces(_cell()), [])


class TestWhoIsStrandedAloft(EvenniaTest):
    """The boot sweep's cold half. Needs real typeclasses: only bodies
    and things fall, and that gate is an isinstance check.

    A fifth condition joined the predicate with the impasse (#3581):
    there has to be somewhere to fall TO. A body parked in a BARE cell
    by a previous strand is not "stranded" in the sweep's sense -- it is
    already at rest, and a sweep that started it again would re-strand
    it on every single boot, re-sending the message each time."""

    def setUp(self):
        super().setUp()
        self.air = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air, destination=self.room2,
                      aliases=["d"])
        self.bare = create_object("typeclasses.rooms.SkyRoom",
                                  key="In the Air")

    def test_a_body_hanging_in_a_wired_cell(self):
        self.char1.location = self.air
        self.assertTrue(is_stranded_aloft(self.char1))

    def test_a_body_parked_in_a_bare_cell_is_left_alone(self):
        """No `down`: the impasse already stopped them here."""
        self.char1.location = self.bare
        self.assertFalse(is_stranded_aloft(self.char1))

    def test_a_cell_that_lost_the_room_below_is_bare_too(self):
        """The column's floor was deleted out from under it; Evennia
        takes the `down` exit with the room, so the cell is now an
        impasse like any other."""
        below = create_object("typeclasses.rooms.Room", key="Doomed")
        dangling = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=dangling, destination=below, aliases=["d"])
        self.char1.location = dangling
        self.assertTrue(is_stranded_aloft(self.char1),
                        "premise: wired, this cell IS a fall")
        below.delete()
        self.assertFalse(is_stranded_aloft(self.char1))

    def test_a_body_on_the_street_is_not(self):
        self.char1.location = self.room1
        self.assertFalse(is_stranded_aloft(self.char1))

    def test_a_body_already_falling_is_not_stranded(self):
        self.char1.location = self.air
        self.char1.db.falling = {"cells": 1}
        self.assertFalse(is_stranded_aloft(self.char1))

    def test_a_body_that_stays_aloft_is_not_stranded(self):
        self.char1.location = self.air
        self.char1.db.stays_aloft = True
        self.assertFalse(is_stranded_aloft(self.char1))

    def test_an_item_hanging_in_a_wired_cell_is_stranded(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        item.location = self.air
        self.assertTrue(is_stranded_aloft(item))

    def test_an_exit_in_an_air_cell_is_not(self):
        """@airfill creates the column's exits INSIDE the air cells."""
        ex = create_object("typeclasses.exits.Exit", key="down",
                           location=self.air, destination=self.room1)
        self.assertFalse(is_stranded_aloft(ex))

    def test_the_room_itself_is_not(self):
        self.assertFalse(is_stranded_aloft(self.air))
