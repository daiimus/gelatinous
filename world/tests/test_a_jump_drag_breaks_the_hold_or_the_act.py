"""The edge drag breaks the victim's acts, and acts only on a move that
happened (#3668).

`jump off <edge>` while grappling took the victim along with hooks ON and
never checked the result. A grappled victim can still start a channel
(`spray`, `sabotage` have no grapple gate), and `at_pre_move` refuses a
channeling mover -- so on a direct drop the victim stayed on the roof,
was told they fell, took the bodyshield damage and left combat while the
jumper landed below; in transit the channel simply excused them from the
ride, the grapple immunity #2774 rejected for the door drags.

Now both branches break the victim's acts first (procedure, then channel,
the door drags' own breaker), move the victim before the jumper so a hold
that still opens is spoken of on the roof, and put the victim back when
the jumper's own move is refused.

Controls: an undisturbed drag lands both; a refused jumper leaves both
on the roof with nothing said.
"""
from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.channeled import begin_channel, channel_of
from world.combat.constants import (
    DB_FALLING, DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, FALL_DAMAGE_PER_STORY,
    NDB_COMBAT_HANDLER,
)
from world.combat.utils import get_character_dbref


class _EdgeDrag(EvenniaTest):
    """jumper (char1) holds victim (char2) on the roof (room1); the exit
    is an edge onto room2, a street or an air cell."""

    def setUp(self):
        super().setUp()
        self.jumper, self.victim = self.char1, self.char2
        self.roof = self.room1
        self.victim.location = self.roof
        self.said, self.heard = [], []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        self.victim.msg = lambda text=None, **kw: self.heard.append(str(text))
        self.street = create_object("typeclasses.rooms.Room", key="Test Street")
        self.handler = mock.MagicMock()
        self.handler.db.combatants = [
            {"char": self.jumper, DB_GRAPPLING_DBREF: get_character_dbref(self.victim)},
            {"char": self.victim, DB_GRAPPLED_BY_DBREF: get_character_dbref(self.jumper)},
        ]
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, self.handler)

    def channeling(self, who):
        ok = begin_channel(who, 30, "spraying a wall",
                           on_complete=lambda: None, on_interrupt=lambda f: None,
                           key="spraying")
        self.assertTrue(ok, "fixture: the channel did not start")
        self.assertTrue(channel_of(who))

    def descend(self, *, dest_is_sky):
        from commands.combat.jump import CmdJump
        exit_obj = self.exit
        exit_obj.key = "south"
        exit_obj.db.is_edge = True
        exit_obj.destination.db.is_sky_room = dest_is_sky
        if dest_is_sky:
            exit_obj.destination.key = "In the Air"
            create_object("typeclasses.exits.Exit", key="down",
                          location=exit_obj.destination,
                          destination=self.street, aliases=["d"])
        self.below = exit_obj.destination
        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "south"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.clear_aim_state",
                           "commands.combat.jump.msg_room_identity",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(type(cmd), "find_edge_exit", return_value=exit_obj))
            stack.enter_context(mock.patch.object(type(cmd), "pay_the_price_of_leaving", return_value=True))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            self.room_beat = stack.enter_context(mock.patch("world.combat.grappling.msg_room_identity"))
            self.delayed = stack.enter_context(mock.patch.object(gravity, "delay"))
            cmd.handle_edge_descent()

    def hurt(self, who):
        return sum(o.max_hp - o.current_hp for o in who.medical_state.organs.values())

    def removed_from_combat(self):
        return [c.args[0] for c in self.handler.remove_combatant.call_args_list]


class TheDirectDrop(_EdgeDrag):

    def test_control_an_undisturbed_drag_lands_both(self):
        self.descend(dest_is_sky=False)
        self.assertIs(self.jumper.location, self.below)
        self.assertIs(self.victim.location, self.below)
        self.assertTrue(any("drags you off" in t for t in self.heard), self.heard)
        self.assertIn(self.victim, self.removed_from_combat())

    def test_a_channeling_victim_is_dragged_off_all_the_same(self):
        self.channeling(self.victim)
        self.descend(dest_is_sky=False)
        self.assertIs(self.victim.location, self.below, "the channel excused them from the drop")
        self.assertFalse(channel_of(self.victim), "the channel survived being hauled off a roof")
        self.assertTrue(any("drags you off" in t for t in self.heard), self.heard)
        self.assertGreater(self.hurt(self.victim), 0)

    def test_a_procedure_on_the_victim_ends_with_the_surgeon_told(self):
        with mock.patch("world.medical.procedures.take_patient_away") as taken:
            self.descend(dest_is_sky=False)
        taken.assert_called_once()
        self.assertIs(taken.call_args.args[0], self.victim)

    def test_a_hold_that_still_opens_is_spoken_and_nobody_is_told_they_fell(self):
        # Refused even with the acts broken (an escort, say): the victim
        # stays, unhurt, still in the fight; the jumper goes over alone at
        # the full storey; both hear the hold open, the roof hears it too.
        self.victim.move_to = lambda *a, **kw: False
        self.descend(dest_is_sky=False)
        self.assertIs(self.victim.location, self.roof)
        self.assertIs(self.jumper.location, self.below)
        self.assertFalse(any("drags you off" in t for t in self.heard), self.heard)
        self.assertFalse(any("bodyshield" in t for t in self.heard), self.heard)
        self.assertEqual(self.hurt(self.victim), 0)
        self.assertEqual(self.hurt(self.jumper), FALL_DAMAGE_PER_STORY)
        self.assertFalse(any("cushion" in t for t in self.said), self.said)
        self.assertTrue(any("tears free" in t or "opens at the lip" in t for t in self.said), self.said)
        self.assertTrue(any("tear free" in t or "opens at the lip" in t for t in self.heard), self.heard)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof)
        self.assertNotIn(self.victim, self.removed_from_combat())
        self.assertIn(self.jumper, self.removed_from_combat())

    def test_control_a_refused_jumper_leaves_both_on_the_roof_saying_nothing(self):
        # The jumper's own channel refuses THEIR move (the real gate), after
        # the victim has already been set down below: the victim comes back.
        self.channeling(self.jumper)
        self.descend(dest_is_sky=False)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(self.victim.location, self.roof)
        # Only the gate's own refusal reaches the jumper; no leap, no drag.
        # The victim hears nothing but the auto-look of the hooked move
        # down and back (the transit branch's own put-back pattern).
        self.assertEqual(self.said, ["You're busy spraying — 'stop' first."], self.said)
        narrated = [t for t in self.heard if "'type': 'look'" not in t]
        self.assertEqual(narrated, [], narrated)
        self.assertEqual(self.hurt(self.victim), 0)


class TheTransit(_EdgeDrag):

    def test_a_channeling_victim_rides_the_fall(self):
        self.channeling(self.victim)
        self.descend(dest_is_sky=True)
        self.assertIs(self.victim.location, self.below, "the channel excused them from the ride")
        self.assertFalse(channel_of(self.victim))
        self.assertEqual(getattr(self.victim.db, DB_FALLING, {}).get("led_by"), self.jumper)
        self.assertTrue(any("drags you off" in t for t in self.heard), self.heard)

    def test_a_hold_that_still_opens_is_spoken_on_the_roof(self):
        self.victim.move_to = lambda *a, **kw: False
        self.descend(dest_is_sky=True)
        self.assertIs(self.victim.location, self.roof)
        self.assertIs(self.jumper.location, self.below)
        self.assertFalse(getattr(self.victim.db, DB_FALLING, None))
        self.assertTrue(any("tear free" in t or "opens at the lip" in t for t in self.heard), self.heard)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof)
        self.assertNotIn(self.victim, self.removed_from_combat())
