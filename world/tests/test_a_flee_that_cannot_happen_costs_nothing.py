"""A flee that cannot happen costs nothing (#3687, the flee half of #3685).

`flee` paid the aim contest (a free attack on a loss) and the disengage
roll before its own move was attempted, and never asked the channel
gate at all; the move's result went unchecked, so a fleer whom
`at_pre_move` refused was told they fled, and in a fight had already
been removed from it, while standing where they were.

Owner (2026-09-29, on #3685): "That makes sense." -- check first, charge
second. The channel gate is asked at the top; a hold and a barred
escortee before either contest; only then is the round's attempt
counted. The move is made before combat is left (the fight lets go in
the room it was in), and a refused move says nothing of a flight that
did not happen. One thing ends before the move, after the price: a
march of the very victim the fleer holds, which the flight gives up.

Controls: a free fleer pays once and goes; the refusal lines the player
reads are the gates' own.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.combat.movement import CmdFlee
from world.channeled import begin_channel, channel_of
from world.combat.constants import NDB_AIMED_AT_BY, NDB_COMBAT_HANDLER
from world.consent import grant_trust

BUSY = "You're busy spraying — 'stop' first."


class _AFleer(EvenniaCommandTest):
    """char1 flees room1 by the one exit to room2; char2 is the aimer or
    the opponent; the two contests are spies."""

    def setUp(self):
        super().setUp()
        self.fleer, self.other = self.char1, self.char2
        self.fleer.location = self.room1
        self.other.location = self.room1
        self.said, self.told_ward = [], []
        self.ward = None
        self._ear()

    def _ear(self):
        self.fleer.msg = lambda text=None, **kw: self.said.append(str(text))
        if self.ward is not None:
            self.ward.msg = lambda text=None, **kw: self.told_ward.append(str(text))

    def refresh(self):
        """Ids are reused after each test's rollback, and a command can
        resolve a row to a cached instance whose attribute cache predates
        this test (a walker read an edge flag the fixture's own instance
        did not have). Drop the cache and re-fetch every object the test
        holds, so the command and the assertions see one instance per row."""
        from evennia.objects.models import ObjectDB
        from evennia.utils.idmapper.models import flush_cache
        ids = {name: getattr(self, name).id for name in ("fleer", "other", "room1", "room2", "exit")
               if getattr(self, name, None) is not None}
        ward_id = self.ward.id if self.ward is not None else None
        channel = getattr(self.fleer.ndb, "channel", None)
        flush_cache()
        for name, pk in ids.items():
            setattr(self, name, ObjectDB.objects.get(id=pk))
        if ward_id is not None:
            self.ward = ObjectDB.objects.get(id=ward_id)
        # The exit's command set is built once and remembered by the row,
        # with the exit instance of that moment inside it; rebuild it
        # against this instance or a walker traverses the old one.
        self.exit.at_cmdset_get(force_init=True)
        self._ear()
        # ndb state lives on the instance: re-arm what the test set up
        if channel is not None:
            self.fleer.ndb.channel = channel
        if getattr(self, "_aimed", False):
            setattr(self.fleer.ndb, NDB_AIMED_AT_BY, self.other)
        if getattr(self, "_fight", None):
            self._arm_fight()
            if getattr(self, "_held", False) and self.ward is not None:
                setattr(self.ward.ndb, NDB_COMBAT_HANDLER, self.handler)
        if getattr(self, "_refuse_moves", False):
            self.fleer.move_to = lambda *a, **kw: False

    def aimed_at(self):
        self._aimed = True

    def in_a_fight(self, *, grappled=False):
        self._fight = dict(grappled=grappled)
        return self._arm_fight()

    def _arm_fight(self):
        """Build the mock handler once; on a refresh only re-attach it (its
        entries, incl. any grapple refs a test added, must survive)."""
        grappled = self._fight["grappled"]
        h = getattr(self, "handler", None)
        if h is None:
            h = mock.MagicMock()
            h.db.combatants = [{"char": self.fleer}, {"char": self.other}]
            h.db.combat_is_running = True
            h.get_target_obj.side_effect = lambda e: self.fleer if e["char"] == self.other else None
            h.get_grappled_by_obj.return_value = self.other if grappled else None
            h.is_active = True
        setattr(self.fleer.ndb, NDB_COMBAT_HANDLER, h)
        self.handler = h
        return h

    def channeling(self):
        ok = begin_channel(self.fleer, 30, "spraying a wall",
                           on_complete=lambda: None, on_interrupt=lambda f: None,
                           key="spraying")
        self.assertTrue(ok, "fixture: the channel did not start")

    def escorting(self, *, live=True):
        self.ward = create_object("typeclasses.characters.Character", key="Ward", location=self.room1)
        self._ear()
        if live:
            grant_trust(self.ward, self.fleer, "escort")
        self.fleer.db.escorting = self.ward
        return self.ward

    def flee(self, *, roll_won=True):
        self.refresh()
        cmd = CmdFlee()
        cmd.caller = self.fleer
        cmd.args = ""
        cmd.obj = self.fleer
        with mock.patch("commands.combat.movement.break_aim_lock", return_value=True) as aim, \
             mock.patch("commands.combat.movement.roll_to_disengage",
                        return_value=(roll_won, None if roll_won else self.other, [self.other])) as roll, \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            cmd.func()
        self.aim, self.roll = aim, roll

    def stayed(self):
        self.assertEqual(self.fleer.location, self.room1, self.said)

    def fled(self):
        self.assertEqual(self.fleer.location, self.room2, self.said)
        self.assertTrue(any("successfully flee" in t for t in self.said), self.said)


class TheChannelGate(_AFleer):

    def test_control_an_aimed_fleer_pays_the_contest_and_goes(self):
        self.aimed_at()
        self.flee()
        self.aim.assert_called_once()
        self.fled()

    def test_control_a_fighting_fleer_rolls_leaves_the_fight_and_goes(self):
        h = self.in_a_fight()
        self.flee()
        self.roll.assert_called_once()
        h.remove_combatant.assert_called_once_with(self.fleer, room=self.room1)
        self.fled()

    def test_a_channeling_aimed_fleer_pays_nothing(self):
        self.aimed_at()
        self.channeling()
        self.flee()
        self.aim.assert_not_called()
        self.stayed()
        self.assertEqual(self.said, [BUSY], self.said)
        self.assertTrue(channel_of(self.fleer))
        self.assertFalse(getattr(self.fleer.ndb, "flee_attempted_this_round", False),
                         "a refused flee counted as the round's attempt")

    def test_a_channeling_fighting_fleer_pays_nothing_and_stays_in_the_fight(self):
        h = self.in_a_fight()
        self.channeling()
        self.flee()
        self.roll.assert_not_called()
        h.remove_combatant.assert_not_called()
        self.stayed()
        self.assertEqual(self.said, [BUSY], self.said)


class TheHoldGate(_AFleer):

    def test_a_held_aimed_fleer_pays_no_aim_contest(self):
        # Before: the aim contest, then "you cannot flee while grappled".
        self.aimed_at()
        self.in_a_fight(grappled=True)
        self.flee()
        self.aim.assert_not_called()
        self.roll.assert_not_called()
        self.stayed()
        self.assertTrue(any("cannot flee while" in t for t in self.said), self.said)
        self.assertFalse(getattr(self.fleer.ndb, "flee_attempted_this_round", False),
                         "a refused flee counted as the round's attempt")

    def holding(self):
        """The fleer grapples the ward, who is a combatant in the same
        fight; the mock handler answers the grapple lookups both ways."""
        from world.combat.constants import DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF
        from world.combat.utils import get_character_dbref
        h = self.in_a_fight()
        h.db.combatants.append({"char": self.ward, DB_GRAPPLED_BY_DBREF: get_character_dbref(self.fleer)})
        h.db.combatants[0][DB_GRAPPLING_DBREF] = get_character_dbref(self.ward)
        h.get_grappling_obj.side_effect = lambda e: self.ward if e["char"] == self.fleer else None
        setattr(self.ward.ndb, NDB_COMBAT_HANDLER, h)
        self._held = True
        return h

    def test_a_march_of_the_held_victim_is_not_a_barred_escort(self):
        # The gate exempts the held victim (the flight ends that march), so
        # even at an exit the ward could never walk the fleer is not
        # refused at the threshold and pays the price as usual.
        self.exit.delete()
        self.exit = create_object("typeclasses.exits.Exit", key="ledge", location=self.room1,
                                  destination=self.room2)
        self.exit.db.is_edge = True
        self.fleer.db.stays_aloft = True
        self.escorting()
        h = self.holding()
        self.flee()
        self.roll.assert_called_once()
        self.fled()
        self.assertFalse(self.fleer.db.escorting)
        self.assertEqual(self.ward.location, self.room1)
        h.remove_combatant.assert_called_once_with(self.fleer, room=self.room1)

    def test_a_fleer_marching_their_own_held_victim_still_flees_and_the_march_ends(self):
        # The fight refuses the held victim's walk at the door, so the
        # usher would refuse the fleer; the march stands on the hold the
        # flight gives up, and ends first -- as it ended on its own when
        # leaving combat came before the move.
        self.escorting()
        h = self.holding()
        self.flee()
        self.roll.assert_called_once()
        self.fled()
        self.assertEqual(self.ward.location, self.room1)
        self.assertFalse(self.fleer.db.escorting)
        self.assertTrue(any("stop leading" in t for t in self.said), self.said)
        self.assertTrue(any("stops leading you" in t for t in self.told_ward), self.told_ward)
        h.remove_combatant.assert_called_once()


class TheEscortGate(_AFleer):

    def test_an_escortee_barred_at_the_only_way_out_costs_nothing(self):
        # A fleer who can stay up keeps an edge in their pool; their
        # escortee cannot walk it. Asked before the contest. The edge is
        # this test's own exit: a flag set on the fixture's shared exit
        # has been seen to outlive the test in a remembered command set.
        self.exit.delete()
        self.exit = create_object("typeclasses.exits.Exit", key="ledge", location=self.room1,
                                  destination=self.room2)
        self.exit.db.is_edge = True
        self.fleer.db.stays_aloft = True
        self.aimed_at()
        self.escorting()
        self.flee()
        self.aim.assert_not_called()
        self.stayed()
        self.assertEqual(self.ward.location, self.room1)
        self.assertTrue(any("cannot" in t for t in self.told_ward), self.told_ward)
        self.assertTrue(any("refuses them" in t for t in self.said), self.said)
        self.assertFalse(getattr(self.fleer.ndb, "flee_attempted_this_round", False),
                         "a refused flee counted as the round's attempt")

    def test_control_an_escortee_walked_through_a_plain_door_goes_along(self):
        self.aimed_at()
        self.escorting()
        self.flee()
        self.aim.assert_called_once()
        self.fled()
        self.assertEqual(self.ward.location, self.room2)
        self.assertEqual(self.fleer.db.escorting, self.ward)


class TheFightLetsGoInItsOwnRoom(EvenniaCommandTest):
    """`remove_combatant(..., room=)`: a fleer who has already left is
    let go of in the room the fight was in."""

    def test_the_exit_line_lands_in_the_room_named(self):
        from world.combat.utils import remove_combatant
        fighter, roof, street = self.char1, self.room1, self.room2
        fighter.location = street                    # already gone
        handler = mock.MagicMock()
        handler._active_combatants_list = None     # a bare Mock here reads as a live round
        handler.db.combatants = [{"char": fighter}]
        with mock.patch("world.combat.utils.msg_room_identity") as room_line, \
             mock.patch("world.combat.utils.cleanup_combatant_state"), \
             mock.patch("world.llm.observation.observe_event") as noticed:
            remove_combatant(handler, fighter, room=roof)
        self.assertEqual(room_line.call_args.kwargs["location"], roof)
        self.assertIn("steps back from the fight", room_line.call_args.kwargs["template"])
        self.assertEqual(noticed.call_args.args[0], roof)

    def test_control_without_a_room_the_line_lands_where_they_stand(self):
        from world.combat.utils import remove_combatant
        fighter = self.char1
        handler = mock.MagicMock()
        handler._active_combatants_list = None
        handler.db.combatants = [{"char": fighter}]
        with mock.patch("world.combat.utils.msg_room_identity") as room_line, \
             mock.patch("world.combat.utils.cleanup_combatant_state"):
            remove_combatant(handler, fighter)
        self.assertEqual(room_line.call_args.kwargs["location"], fighter.location)


class TheMoveIsChecked(_AFleer):
    """A refusal nothing predicts (a door a lock shuts on the escortee) is
    not a flight: the fleer stays in the fight, in the room, untold."""

    def test_a_refused_move_in_a_fight_leaves_the_fleer_in_it_saying_nothing(self):
        # (`move_to` is stubbed to refuse, so the location itself proves
        # nothing here; what is pinned is that combat is not left and no
        # flight is narrated.)
        h = self.in_a_fight()
        self._refuse_moves = True
        self.flee()
        self.roll.assert_called_once()
        h.remove_combatant.assert_not_called()
        self.assertFalse(any("successfully flee" in t for t in self.said), self.said)

    def test_a_refused_move_after_a_broken_aim_is_not_narrated_as_a_flight(self):
        self.aimed_at()
        self._refuse_moves = True
        self.flee()
        self.assertFalse(any("successfully flee" in t for t in self.said), self.said)
