"""The edge drag breaks the victim's acts, and acts only on a move that
happened (#3668).

`jump off <edge>` while grappling took the victim along with hooks ON and
never checked the result. A grappled victim can still start a channel
(`spray`, `sabotage` have no grapple gate), and `at_pre_move` refuses a
channeling mover -- so on a direct drop the victim stayed on the roof,
was told they fell, took the bodyshield damage and left combat while the
jumper landed below; in transit the channel simply excused them from the
ride, the grapple immunity #2774 rejected for the door drags.

Now the direct drop moves the JUMPER first, so a refused jump touches the
victim not at all, and only then breaks the victim's acts (procedure,
then channel, the door drags' own breaker, and their escort, gravity's
rule) before moving them; transit, which needs the companion in the cell
first, asks the jumper's own gates without moving and leaves the victim
alone when the jumper would be refused, then breaks the acts the same
way. A move still refused opens the hold: the pairing is broken and the
beat is spoken to the roof.

Controls: an undisturbed drag lands both; a refused jumper leaves both
on the roof with nothing said and the victim's act intact.
"""
from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.channeled import begin_channel, channel_of
from world.consent import grant_trust
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

    def grapple_refs(self):
        entries = self.handler.db.combatants
        return (entries[0].get(DB_GRAPPLING_DBREF), entries[1].get(DB_GRAPPLED_BY_DBREF))


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
        # Refused even with the acts broken (a refuser nothing here knows
        # of): the victim stays, unhurt, still in the fight; the jumper
        # goes over alone at the full storey; both hear the hold open, the
        # roof hears it too, and the pairing is gone.
        self.victim.move_to = lambda *a, **kw: False
        self.descend(dest_is_sky=False)
        self.assertIs(self.victim.location, self.roof)
        self.assertIs(self.jumper.location, self.below)
        self.assertFalse(any("drags you off" in t for t in self.heard), self.heard)
        self.assertFalse(any("bodyshield" in t for t in self.heard), self.heard)
        self.assertEqual(self.hurt(self.victim), 0)
        self.assertEqual(self.hurt(self.jumper), FALL_DAMAGE_PER_STORY)
        self.assertFalse(any("cushion" in t for t in self.said), self.said)
        self.assertTrue(any("gives at the edge" in t or "opens at the lip" in t for t in self.said), self.said)
        self.assertTrue(any("gives at the edge" in t or "opens at the lip" in t for t in self.heard), self.heard)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof,
                         "the roof, not the street the jumper landed in, hears the hold open")
        self.assertEqual(self.grapple_refs(), (None, None), "the pairing outlived the hold")
        self.assertNotIn(self.victim, self.removed_from_combat())
        self.assertIn(self.jumper, self.removed_from_combat())

    def test_control_a_refused_jumper_leaves_both_on_the_roof_saying_nothing(self):
        # The jumper's own channel refuses THEIR move (the real gate). The
        # victim, who goes second, is never touched: still channeling,
        # nothing heard, not even an arrival look.
        self.channeling(self.jumper)
        self.channeling(self.victim)
        self.descend(dest_is_sky=False)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(self.victim.location, self.roof)
        self.assertEqual(self.said, ["You're busy spraying — 'stop' first."], self.said)
        self.assertEqual(self.heard, [], self.heard)
        self.assertTrue(channel_of(self.victim), "a refused jump cost the victim their act")
        self.assertEqual(self.hurt(self.victim), 0)

    def test_an_escorting_victim_is_dragged_off_all_the_same(self):
        # With hooks on, an escort would refuse the move; a body hauled
        # off a roof escorts nobody (gravity's rule for every companion).
        other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        grant_trust(other, self.victim, "escort")     # a real escort, not one consent ends
        self.victim.db.escorting = other
        self.descend(dest_is_sky=False)
        self.assertIs(self.victim.location, self.below)
        self.assertFalse(self.victim.db.escorting)
        self.assertFalse(any("no longer follows" in t or "refuses them" in t for t in self.heard),
                         self.heard)


class TheTransit(_EdgeDrag):

    def test_a_channeling_victim_rides_the_fall(self):
        self.channeling(self.victim)
        self.descend(dest_is_sky=True)
        self.assertIs(self.victim.location, self.below, "the channel excused them from the ride")
        self.assertFalse(channel_of(self.victim))
        self.assertEqual(getattr(self.victim.db, DB_FALLING, {}).get("led_by"), self.jumper)
        self.assertTrue(any("drags you off" in t for t in self.heard), self.heard)
        # broken before the move, never tried first: no "you're busy"
        # before being hauled anyway
        self.assertFalse(any("busy" in t for t in self.heard), self.heard)

    def test_an_escorting_victim_rides_the_fall_and_nobody_is_sent_at_the_edge(self):
        other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        told_other = []
        other.msg = lambda text=None, **kw: told_other.append(str(text))
        grant_trust(other, self.victim, "escort")
        self.victim.db.escorting = other
        self.descend(dest_is_sky=True)
        self.assertIs(self.victim.location, self.below)
        self.assertIs(other.location, self.roof)
        self.assertFalse(self.victim.db.escorting)
        self.assertEqual(told_other, [], told_other)
        self.assertFalse(any("refuses them" in t for t in self.heard), self.heard)

    def test_a_hold_that_still_opens_is_spoken_on_the_roof(self):
        self.victim.move_to = lambda *a, **kw: False
        self.descend(dest_is_sky=True)
        self.assertIs(self.victim.location, self.roof)
        self.assertIs(self.jumper.location, self.below)
        self.assertFalse(getattr(self.victim.db, DB_FALLING, None))
        self.assertTrue(any("gives at the edge" in t or "opens at the lip" in t for t in self.heard), self.heard)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof)
        self.assertEqual(self.grapple_refs(), (None, None), "the pairing outlived the hold")
        self.assertNotIn(self.victim, self.removed_from_combat())

    def test_a_procedure_on_the_victim_ends_with_the_surgeon_told(self):
        # A victim neither channeling nor escorting still has a surgeon's
        # channel timing a procedure on them; the ride ends it too.
        with mock.patch("world.medical.procedures.take_patient_away") as taken:
            self.descend(dest_is_sky=True)
        taken.assert_called_once()
        self.assertIs(taken.call_args.args[0], self.victim)
        self.assertIs(self.victim.location, self.below)

    def test_control_a_gated_jumper_leaves_the_victim_alone(self):
        # The jumper's own channel would refuse them; the victim, who has
        # to go first, is not touched at all and keeps their act.
        self.channeling(self.jumper)
        self.channeling(self.victim)
        self.descend(dest_is_sky=True)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(self.victim.location, self.roof)
        self.assertTrue(channel_of(self.victim), "a refused jump cost the victim their act")
        self.assertEqual(self.heard, [], self.heard)
        self.assertFalse(getattr(self.victim.db, DB_FALLING, None))
        self.assertEqual(self.delayed.call_count, 0, "a fall was scheduled for a refused jump")
        self.assertEqual(self.said, ["You're busy spraying — 'stop' first."], self.said)

    def escorted_by_jumper(self):
        other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        other.msg = lambda text=None, **kw: self.told_other.append(str(text))
        self.told_other = []
        grant_trust(other, self.jumper, "escort")
        self.jumper.db.escorting = other
        return other

    def test_control_a_jumper_with_a_live_escort_is_refused_and_the_victim_left_alone(self):
        # The usher walks the escortee ahead; an edge refuses a walker, so
        # the jumper is refused by the real gate. The victim keeps their act.
        other = self.escorted_by_jumper()
        self.channeling(self.victim)
        self.descend(dest_is_sky=True)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(self.victim.location, self.roof)
        self.assertIs(other.location, self.roof)
        self.assertTrue(channel_of(self.victim), "a refused jump cost the victim their act")
        self.assertEqual(self.heard, [], self.heard)
        self.assertTrue(any("cannot" in t for t in self.told_other), self.told_other)

    def test_a_jumper_with_a_stale_escort_still_drags_the_victim(self):
        # An unconscious escortee is released by the usher and the leader
        # walks on: predicting a refusal here would excuse the victim and
        # break the hold without a word.
        self.escorted_by_jumper()
        with mock.patch("world.consent.is_conscious", return_value=False):
            self.descend(dest_is_sky=True)
        self.assertIs(self.jumper.location, self.below)
        self.assertIs(self.victim.location, self.below, "a stale escort excused the victim")
        self.assertFalse(self.jumper.db.escorting)
        self.assertTrue(any("drags you off" in t for t in self.heard), self.heard)


class TheWalkDecidesTheRefusal(_EdgeDrag):
    """A live escort refuses the leader only when the escortee's walk
    would bounce; a plain door beside the edge is simply walked."""

    def setUp(self):
        super().setUp()
        self.other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        grant_trust(self.other, self.jumper, "escort")
        self.jumper.db.escorting = self.other
        from commands.combat.jump import CmdJump
        self.cmd = CmdJump()
        self.cmd.caller = self.jumper

    def test_a_walk_through_a_plain_door_is_not_a_refusal(self):
        self.assertFalse(self.cmd.would_refuse_a_hooked_move(self.jumper, self.exit.destination))

    def test_a_walk_at_an_edge_is(self):
        self.exit.db.is_edge = True
        self.assertTrue(self.cmd.would_refuse_a_hooked_move(self.jumper, self.exit.destination))

    def test_a_walk_into_air_is(self):
        self.exit.destination.db.is_sky_room = True
        self.assertTrue(self.cmd.would_refuse_a_hooked_move(self.jumper, self.exit.destination))

    def test_no_exit_at_all_is_not(self):
        self.assertFalse(self.cmd.would_refuse_a_hooked_move(self.jumper, self.street))


class TheGatesAgree(_EdgeDrag):
    """`live_escortee` must answer exactly where `usher_escortee` would
    walk the escortee ahead; the edge drag predicts the jumper's refusal
    from it."""

    def setUp(self):
        super().setUp()
        from world.movement_coupling import live_escortee, usher_escortee
        self.live, self.usher = live_escortee, usher_escortee
        self.other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        grant_trust(self.other, self.jumper, "escort")
        self.jumper.db.escorting = self.other
        self.jumper.msg = lambda text=None, **kw: None

    def test_a_live_escort_is_the_escortee_and_the_usher_walks_them(self):
        self.assertIs(self.live(self.jumper, self.exit.destination), self.other)
        # walked ahead through a plain exit: the leader may proceed and the link holds
        self.assertTrue(self.usher(self.jumper, self.exit.destination))
        self.assertIs(self.other.location, self.exit.destination)
        self.assertIs(self.jumper.db.escorting, self.other)

    def test_a_separated_escort_is_none_and_the_usher_releases(self):
        self.other.location = self.street
        self.assertIsNone(self.live(self.jumper, self.exit.destination))
        self.assertTrue(self.usher(self.jumper, self.exit.destination))
        self.assertFalse(self.jumper.db.escorting)

    def test_an_unconscious_escort_is_none_and_the_usher_releases(self):
        with mock.patch("world.consent.is_conscious", return_value=False):
            self.assertIsNone(self.live(self.jumper, self.exit.destination))
            self.assertTrue(self.usher(self.jumper, self.exit.destination))
        self.assertFalse(self.jumper.db.escorting)

    def test_a_withdrawn_consent_is_none_and_the_usher_releases(self):
        with mock.patch("world.consent.check_consent", return_value=False):
            self.assertIsNone(self.live(self.jumper, self.exit.destination))
            self.assertTrue(self.usher(self.jumper, self.exit.destination))
        self.assertFalse(self.jumper.db.escorting)

    def test_no_exit_to_the_destination_is_none_and_the_usher_steps_aside(self):
        nowhere_near = create_object("typeclasses.rooms.Room", key="Far Perch")
        self.assertIsNone(self.live(self.jumper, nowhere_near))
        self.assertTrue(self.usher(self.jumper, nowhere_near))
        self.assertIs(self.jumper.db.escorting, self.other, "the usher keeps the link when it steps aside")
        self.assertIs(self.other.location, self.roof)

    def test_a_deleted_escort_is_none_and_the_usher_releases(self):
        self.other.delete()
        self.assertIsNone(self.live(self.jumper, self.exit.destination))
        self.assertTrue(self.usher(self.jumper, self.exit.destination))
        self.assertFalse(self.jumper.db.escorting)
