"""What you aim at over a parapet is the street, not the air (#3589).

Owner ruling (2026-09-16): *"Aiming at an edge typically means aiming at
the ground area it drops to because of sniping. Rooftop to street for
example."*

Four call sites share the one seam, :func:`world.gravity.room_through`,
and all four are pinned here through the paths a player actually
touches:

* ``Room.return_appearance`` while aiming -- the sniper's view down the
  barrel must show the STREET he can shoot, with its own name and desc,
  not the empty cell the edge exit technically leads into. A column with
  no floor under it has no ground to show, so the render falls back to
  the air cell (``room_through(...) or exit_obj.destination``): you get
  to see the hole you are aiming into rather than nothing at all.
* ``Room.search_for_target`` -- the unified aiming search space must be
  *here plus the street*, so a body standing down there can be named.
* ``CmdAttack``'s directional attack -- the shot is resolved against the
  street's occupants, and over a bare column it is refused in the
  player's own words rather than firing into nowhere.
* ``CmdThrow`` -- the same answer for what you are AIMING at, and a
  deliberately different one for where the object physically goes:
  ``find_target`` reaches the street through ``room_through``, while
  ``get_destination_room`` still returns the exit's own destination, the
  air cell, because gravity carries the object down from there (#3579).
  Two questions, two answers, one exit -- ``find_throw_exit`` is the
  shared reading of that exit.

The fixture is a real, coordinate-seeded column, because ``ground_below``
reads the spatial grid first and a stubbed room is invisible to the
ObjectDB query behind ``coordinate_index``. The street is flagged
``outside`` because an INTERIOR straight below an air cell is an unbuilt
roof in the way and would occlude the shot entirely -- which is its own
test, over in test_a_shot_over_the_edge_finds_the_street. Weather is
silenced so the render is deterministic; that the aimed room composes
its own layers is test_the_aimed_room_composes_like_any_other's job.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses import rooms as rooms_mod
from world.combat.constants import (
    MSG_THROW_TARGET_NOT_FOUND,
    NDB_AIMING_DIRECTION,
)
from world.spatial import set_xyz

STREET_DESC = "Wet asphalt under a dead streetlight."


class _RoofOverAStreet(EvenniaTest):
    """roof (0,0,2) -- east over the edge: air (1,0,2) / air (1,0,1) /
    street (1,0,0). West over the same parapet: a column nobody finished,
    air (-1,0,2) / air (-1,0,1) and no floor at all."""

    def setUp(self):
        super().setUp()
        self.roof = self.room1
        self.roof.key = "Test Roof"
        self.roof.db.type = "rooftop"
        self.roof.db.outside = True
        set_xyz(self.roof, 0, 0, 2)

        self.street = self._room("Test Street", (1, 0, 0), desc=STREET_DESC)
        self.air = self._room("In the Air", (1, 0, 2), sky=True)
        self._room("In the Air", (1, 0, 1), sky=True)

        self.void = self._room("Unfinished Air", (-1, 0, 2), sky=True)
        self._room("Unfinished Air", (-1, 0, 1), sky=True)

        self.east = create_object("typeclasses.exits.Exit", key="east",
                                  aliases=["e"], location=self.roof,
                                  destination=self.air)
        self.east.db.is_edge = True
        self.west = create_object("typeclasses.exits.Exit", key="west",
                                  aliases=["w"], location=self.roof,
                                  destination=self.void)
        self.west.db.is_edge = True

        # The mark down on the street, and a flier hanging in the air cell
        # the shot passes THROUGH -- the discriminator for every "which
        # room did we really reach" assertion below. The flier declares
        # `stays_aloft`, so arriving in air does not start a fall.
        self.char1.location = self.roof
        self.char2.key = "Char2"
        self.char2.location = self.street
        self.flier = create_object("typeclasses.characters.Character",
                                   key="Flier", location=None)
        self.flier.db.stays_aloft = True
        self.flier.location = self.air

        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

        weather = mock.patch.object(rooms_mod.weather_system,
                                    "get_weather_contributions",
                                    return_value="")
        weather.start()
        self.addCleanup(weather.stop)

    def _room(self, key, xyz, sky=False, desc=None):
        room = create_object("typeclasses.rooms.Room", key=key, location=None)
        if sky:
            room.db.is_sky_room = True
        else:
            room.db.outside = True      # a surface, not an unbuilt roof
        if desc:
            room.db.desc = desc
        set_xyz(room, *xyz)
        return room

    def aim(self, direction):
        setattr(self.char1.ndb, NDB_AIMING_DIRECTION, direction)

    def look(self):
        return self.roof.return_appearance(self.char1) or ""


class TestTheAimedLookShowsTheGround(_RoofOverAStreet):

    def test_over_the_edge_you_see_the_street(self):
        self.aim("east")
        out = self.look()
        self.assertIn("Test Street", out,
                      "aiming over the edge did not render the ground below: %r" % out)
        self.assertIn(STREET_DESC, out,
                      "the street rendered without its own description")

    def test_you_do_not_see_the_empty_cell_you_shoot_through(self):
        self.aim("east")
        self.assertNotIn("In the Air", self.look(),
                         "the render stopped at the air cell instead of the ground")

    def test_an_alias_aims_the_same_way(self):
        """Players type 'aim e'; the exit is matched by alias too."""
        self.aim("e")
        self.assertIn("Test Street", self.look())

    def test_a_bare_column_renders_the_air_it_drops_into(self):
        """Nothing down there to show: the fallback renders the hole."""
        self.aim("west")
        out = self.look()
        self.assertIn("Unfinished Air", out,
                      "a floorless column must still render something: %r" % out)
        self.assertNotIn("Test Street", out)

    def test_not_aiming_still_renders_the_room_you_stand_in(self):
        self.aim(None)
        out = self.look()
        self.assertIn("Test Roof", out)
        self.assertNotIn("Test Street", out)


class TestTheAimedSearchReachesTheGround(_RoofOverAStreet):

    def candidates(self):
        return self.roof.search_for_target(self.char1, "char2",
                                           return_candidates_only=True)

    def test_a_body_on_the_street_is_in_the_search_space(self):
        self.aim("east")
        self.assertIn(self.char2, self.candidates(),
                      "the aiming search space did not reach the ground below")

    def test_the_air_cell_is_not_the_search_space(self):
        self.aim("east")
        self.assertNotIn(self.flier, self.candidates(),
                         "the search stopped in the air cell the shot passes through")

    def test_the_looker_is_never_their_own_candidate(self):
        self.aim("east")
        self.assertNotIn(self.char1, self.candidates())

    def test_not_aiming_is_this_room_only(self):
        self.aim(None)
        found = self.candidates()
        self.assertNotIn(self.char2, found)
        self.assertNotIn(self.flier, found)


class TestTheShotReachesTheGround(_RoofOverAStreet):
    """``CmdAttack`` is driven the way the flee tests drive ``CmdFlee``:
    the command object with its caller and args, then ``func()``.
    ``execute_cmd`` is inert under ``evennia test``."""

    def setUp(self):
        super().setUp()
        self.rifle = create_object("typeclasses.items.Item", key="rifle",
                                   location=self.char1)
        self.rifle.db.is_ranged = True
        self.rifle.db.weapon_type = "rifle"
        self.char1.hands = {"left_hand": self.rifle}

    def attack(self, args="char2"):
        from commands.combat.core_actions import CmdAttack
        cmd = CmdAttack()
        cmd.caller = self.char1
        cmd.args = args
        cmd.obj = self.char1
        cmd.func()
        return cmd

    def test_the_shot_is_resolved_against_the_street(self):
        """Pinned at the resolver boundary: the candidate pool handed to
        the identity search IS the far room's characters."""
        self.aim("east")
        seen = {}

        def capture(caller, name, candidates=None, **kwargs):
            seen["candidates"] = list(candidates or [])
            return None

        with mock.patch("commands.combat.core_actions.resolve_character_target",
                        side_effect=capture):
            self.attack()
        self.assertIn(self.char2, seen.get("candidates", []),
                      "the shot was not resolved against the ground below")
        self.assertNotIn(self.flier, seen["candidates"],
                         "the shot was resolved against the air cell it passes through")

    def test_a_bare_column_refuses_the_shot(self):
        self.aim("west")
        with mock.patch("commands.combat.core_actions.resolve_character_target") as resolver:
            self.attack()
        self.assertTrue(
            any("nothing down there to hit" in line for line in self.said),
            "a shot over a floorless column was not refused: %r" % self.said)
        resolver.assert_not_called()

    def test_no_exit_at_all_keeps_its_own_refusal(self):
        """The two refusals are different sentences and must stay so: no
        path out of the room is not the same as a path onto nothing."""
        self.aim("northwest")
        self.attack()
        self.assertTrue(
            any("no clear path to attack through" in line for line in self.said),
            "a direction with no exit should report no path: %r" % self.said)
        self.assertFalse(
            any("nothing down there to hit" in line for line in self.said),
            "the ground-below refusal leaked onto a direction with no exit")

    def test_the_fight_starts_against_the_body_on_the_street(self):
        """End to end: the real identity resolver, the real handler."""
        self.aim("east")
        self.attack()
        self.assertFalse(
            any("You don't see" in line for line in self.said),
            "the target on the street was never found: %r" % self.said)
        handler = getattr(self.char1.ndb, "combat_handler", None)
        self.assertIsNotNone(handler, "no combat handler after the shot: %r" % self.said)
        entry = next((e for e in handler.db.combatants
                      if e["char"] == self.char1), None)
        self.assertIsNotNone(entry, "the shooter never joined the fight")
        self.assertIs(handler.get_target_obj(entry), self.char2,
                      "the shooter is not aimed at the body on the street")


class TestTheThrowReachesTheGround(_RoofOverAStreet):
    """``CmdThrow`` is driven the way the throw characterization tests
    drive it: the command object with the parse results set directly, then
    the method under test."""

    def _cmd(self, target_name="char2"):
        from commands.CmdThrow import CmdThrow
        cmd = CmdThrow()
        cmd.caller = self.char1
        cmd.obj = self.char1
        cmd.args = f"rock at {target_name}"
        cmd.object_name = "rock"
        cmd.target_name = target_name
        cmd.throw_type = "at"
        return cmd

    def test_the_exit_is_read_once_for_both_questions(self):
        self.assertIs(self._cmd().find_throw_exit("east"), self.east)

    def test_you_can_throw_at_a_mark_on_the_street(self):
        self.aim("east")
        self.assertIs(self._cmd().find_target(), self.char2,
                      "the throw did not reach the ground below: %r" % self.said)

    def test_the_object_still_flies_into_the_air_cell(self):
        """Deliberately NOT the street: the object enters the air cell and
        gravity walks it down the column from there (#3579)."""
        self.aim("east")
        self.assertIs(self._cmd().get_destination_room("east"), self.air)

    def test_a_mark_over_a_bare_column_is_not_found(self):
        self.aim("west")
        self.assertIsNone(self._cmd().find_target())
        self.assertTrue(
            any(MSG_THROW_TARGET_NOT_FOUND.format(target="char2") in line
                for line in self.said),
            "a throw over a floorless column was not refused: %r" % self.said)

    def test_the_flier_in_the_way_is_not_the_mark(self):
        """Control: the air cell's occupant is reachable by the object but
        is not who ``throw at`` resolves."""
        self.aim("east")
        self.assertIsNone(self._cmd("flier").find_target())
