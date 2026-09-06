"""An edge that leads nowhere refuses instead of stranding you (#2441).

`handle_edge_descent`'s fallback branch — taken when an `is_edge` exit
has no `db.sky_room` — moves the jumper to the exit's `destination`,
applies landing damage, and says "you land safely". That is correct for
the nine such exits whose destination is a street.

It is catastrophic for the one whose destination is an air cell. Exit
**#8054**, the Colonial Constabulary rooftop's south edge, drops into
**#7876 "In the Air"** — which has **no exits at all**. Live, **81 of
the colony's 155 sky rooms are exitless**: they are transit, meant to be
passed through by the fall machinery, never stood in. A character put
there is unrecoverable by anything but `@tel`.

With no `sky_room` configured *and* no `down` exit on the air cell, there
is nothing honest to schedule — nobody knows where the jumper should
land. So the branch refuses and leaves them on the roof.

Nobody is currently stranded; this is preventive.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class _EdgeCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.roof = self.room1
        self.jumper.location = self.roof
        self.air = self.room2

    def descend(self, *, sky_room, dest_is_sky):
        """`handle_edge_descent(self)` takes no arguments — it reads the
        direction off the command and resolves the exit itself, so the
        fixture has to configure the real exit rather than pass one in."""
        from commands.combat.jump import CmdJump

        exit_obj = self.exit                 # room1 -> room2, from EvenniaTest
        exit_obj.key = "south"
        exit_obj.db.is_edge = True
        exit_obj.db.sky_room = sky_room
        exit_obj.destination.db.is_sky_room = dest_is_sky
        if dest_is_sky:
            exit_obj.destination.key = "In the Air"

        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "south"
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))

        with mock.patch("commands.combat.jump.clear_aim_state"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch.object(type(cmd), "find_edge_exit",
                               return_value=exit_obj):
            cmd.handle_edge_descent()
        return " ".join(self.said)


class TestAnEdgeIntoAnExitlessAirCellRefuses(_EdgeCase):
    def test_the_jumper_stays_on_the_roof(self):
        self.descend(sky_room=None, dest_is_sky=True)
        self.assertIs(self.jumper.location, self.roof)

    def test_they_are_told_why(self):
        said = self.descend(sky_room=None, dest_is_sky=True)
        self.assertIn("nothing to land on", said)

    def test_they_are_not_told_they_landed_safely(self):
        said = self.descend(sky_room=None, dest_is_sky=True)
        self.assertNotIn("land safely", said)

    def test_they_take_no_fall_damage_for_a_jump_they_did_not_make(self):
        before = self.jumper.medical_state.blood_level
        self.descend(sky_room=None, dest_is_sky=True)
        self.assertEqual(self.jumper.medical_state.blood_level, before)


class TestTheBenignFallbackStillWorks(_EdgeCase):
    """Nine `is_edge` exits have no sky_room and target a STREET. Those
    must keep working exactly as before — the refusal is scoped to a
    destination that is itself air."""

    def test_a_street_destination_still_lands_you(self):
        self.descend(sky_room=None, dest_is_sky=False)
        self.assertIs(self.jumper.location, self.room2)

    def test_and_says_so(self):
        said = self.descend(sky_room=None, dest_is_sky=False)
        self.assertIn("land safely", said)
