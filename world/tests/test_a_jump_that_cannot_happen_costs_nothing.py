"""A jump that cannot happen costs nothing (#3685).

Jumping off an edge or across a gap in a fight pays flee's price first:
the aim contest and the disengage roll, each with a free attack on a
loss. It was paid BEFORE the jumper's own move was attempted, so a
jumper whom `Character.at_pre_move` then refused (a channel; an escortee
who cannot be walked at the edge) paid in blood and never left the roof.

Owner (2026-09-29): "That makes sense." -- check first, charge second.
`refused_at_the_threshold` runs the two gates for real, so they speak for
themselves, and only then is the price paid.

Controls: a free jumper still pays once and goes; a stale escort is
released by the usher and the jumper pays and goes.
"""
from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.channeled import begin_channel, channel_of
from world.combat.constants import (
    DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, NDB_COMBAT_HANDLER,
)
from world.combat.utils import get_character_dbref
from world.consent import grant_trust


class _AtTheThreshold(EvenniaTest):
    """jumper (char1) on the roof (room1); `south` is the exit to room2,
    flagged an edge or a gap per test; the price of leaving is a spy."""

    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.roof = self.room1
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.way = self.exit
        self.way.key = "south"
        self.other = None

    def refresh(self):
        """Ids are reused after each test's rollback, and a command can
        resolve a row to a cached instance whose attribute cache predates
        this test. Drop the cache and re-fetch every object the test
        holds, so the command and the assertions see one instance per row."""
        from evennia.objects.models import ObjectDB
        from evennia.utils.idmapper.models import flush_cache
        names = [n for n in ("jumper", "roof", "far", "way", "other", "victim") if getattr(self, n, None) is not None]
        ids = {n: getattr(self, n).id for n in names}
        channel = getattr(self.jumper.ndb, "channel", None)
        handler = getattr(self.jumper.ndb, NDB_COMBAT_HANDLER, None)
        flush_cache()
        for n, pk in ids.items():
            setattr(self, n, ObjectDB.objects.get(id=pk))
        # Rebuild the exit's remembered command set against this instance
        # (a walker would otherwise traverse the instance of its making).
        self.way.at_cmdset_get(force_init=True)
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        if getattr(self, "victim", None) is not None:
            self.victim.msg = lambda text=None, **kw: self.heard.append(str(text))
        if self.other is not None:
            self.other.msg = lambda text=None, **kw: self.told_other.append(str(text))
        if channel is not None:
            self.jumper.ndb.channel = channel
        if handler is not None:
            setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, handler)

    def channeling(self, who):
        ok = begin_channel(who, 30, "spraying a wall",
                           on_complete=lambda: None, on_interrupt=lambda f: None,
                           key="spraying")
        self.assertTrue(ok, "fixture: the channel did not start")

    def escorted(self, *, live=True):
        self.other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        self.told_other = []
        self.other.msg = lambda text=None, **kw: self.told_other.append(str(text))
        if live:
            grant_trust(self.other, self.jumper, "escort")
        self.jumper.db.escorting = self.other
        return self.other

    def jump(self, kind, *, sky=False, rolled=999):
        """kind: 'edge' -> handle_edge_descent; 'gap' -> handle_gap_jump."""
        from commands.combat.jump import CmdJump
        if kind == "edge":
            self.way.db.is_edge = True
        else:
            self.way.db.is_gap = True
            if self.way.db.gap_destination is None and self.way.destination is not self.far:
                self.way.db.gap_destination = self.far
        if sky:
            self.way.destination.db.is_sky_room = True
            self.way.destination.key = "In the Air"
            create_object("typeclasses.exits.Exit", key="down", location=self.way.destination,
                          destination=self.far, aliases=["d"])
        self.refresh()
        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "south"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.clear_aim_state",
                           "commands.combat.jump.msg_room_identity",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            self.roll = stack.enter_context(mock.patch("commands.combat.jump.standard_roll",
                                                       return_value=(rolled, rolled, rolled)))
            stack.enter_context(mock.patch.object(type(cmd), "find_edge_exit", return_value=self.way))
            self.price = stack.enter_context(mock.patch.object(type(cmd), "pay_the_price_of_leaving",
                                                               return_value=True))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(mock.patch("world.combat.grappling.msg_room_identity"))
            (cmd.handle_edge_descent if kind == "edge" else cmd.handle_gap_jump)()

    def stayed(self):
        self.assertEqual(self.jumper.location, self.roof)

    def went(self):
        self.assertNotEqual(self.jumper.location, self.roof)


class TheChannelGate(_AtTheThreshold):

    def _free_jumper_pays_once_and_goes(self, kind, sky):
        self.jump(kind, sky=sky)
        self.price.assert_called_once()
        self.went()

    def test_control_a_free_jumper_pays_once_and_goes_off_an_edge(self):
        self._free_jumper_pays_once_and_goes("edge", False)

    def test_control_a_free_jumper_pays_once_and_goes_off_an_edge_into_air(self):
        self._free_jumper_pays_once_and_goes("edge", True)

    def test_control_a_free_jumper_pays_once_and_goes_across_a_gap(self):
        self._free_jumper_pays_once_and_goes("gap", False)

    def test_control_a_free_jumper_pays_once_and_goes_across_a_gap_over_air(self):
        self._free_jumper_pays_once_and_goes("gap", True)

    def _channeling_jumper_pays_nothing(self, kind, sky):
        self.channeling(self.jumper)
        self.jump(kind, sky=sky)
        self.price.assert_not_called()
        self.stayed()
        self.assertEqual(self.said, ["You're busy spraying — 'stop' first."], self.said)
        self.assertTrue(channel_of(self.jumper))

    def test_a_channeling_jumper_pays_nothing_at_an_edge(self):
        self._channeling_jumper_pays_nothing("edge", False)

    def test_a_channeling_jumper_pays_nothing_at_an_edge_into_air(self):
        self._channeling_jumper_pays_nothing("edge", True)

    def test_a_channeling_jumper_pays_nothing_at_a_gap(self):
        self._channeling_jumper_pays_nothing("gap", False)

    def test_a_channeling_jumper_pays_nothing_at_a_gap_over_air(self):
        self._channeling_jumper_pays_nothing("gap", True)

    def test_a_channeling_gap_jumper_never_rolls_and_never_slips(self):
        # Before: the price, then the roll, then a slip in place for a
        # miss -- damage and a skipped round for a jump the gate would
        # have refused had a move been attempted.
        self.channeling(self.jumper)
        self.jump("gap", rolled=-999)
        self.roll.assert_not_called()
        self.stayed()
        self.assertEqual(sum(o.max_hp - o.current_hp for o in self.jumper.medical_state.organs.values()), 0)


class TheEscortGate(_AtTheThreshold):

    def _barred_escortee_costs_nothing(self, kind, sky):
        other = self.escorted()
        self.jump(kind, sky=sky)
        self.price.assert_not_called()
        self.stayed()
        self.assertEqual(self.other.location, self.roof)
        self.assertTrue(any("cannot" in t for t in self.told_other), self.told_other)
        self.assertTrue(any("refuses them" in t for t in self.said), self.said)
        self.assertEqual(self.jumper.db.escorting, self.other, "the usher released a live escort")

    def test_an_escortee_barred_at_the_edge_costs_nothing(self):
        self._barred_escortee_costs_nothing("edge", False)

    def test_an_escortee_barred_at_the_edge_into_air_costs_nothing(self):
        self._barred_escortee_costs_nothing("edge", True)

    def test_an_escortee_barred_at_the_gap_over_air_costs_nothing(self):
        self._barred_escortee_costs_nothing("gap", True)

    def test_an_escortee_barred_at_a_solid_gap_whose_exit_is_the_perch_costs_nothing(self):
        # The usual direct-step gap: the exit's own destination IS the
        # perch, so the gap flag alone bars the walk (no air anywhere).
        other = self.escorted()
        self.way.db.is_gap = True
        self.way.db.gap_destination = None
        self.way.destination = self.far
        self.jump("gap")
        self.price.assert_not_called()
        self.roll.assert_not_called()
        self.stayed()
        self.assertEqual(self.other.location, self.roof)
        self.assertTrue(any("cannot" in t for t in self.told_other), self.told_other)

    def test_control_a_stale_escort_is_released_and_the_jumper_pays_and_goes(self):
        # An unconscious escortee: the usher releases the link and steps
        # aside, so the jump happens and is paid for.
        self.escorted()
        with mock.patch("world.consent.is_conscious", return_value=False):
            self.jump("edge")
        self.price.assert_called_once()
        self.went()
        self.assertFalse(self.jumper.db.escorting)

    def test_control_an_unconsenting_escort_is_released_and_the_jumper_pays_and_goes(self):
        self.escorted(live=False)
        self.jump("edge")
        self.price.assert_called_once()
        self.went()
        self.assertFalse(self.jumper.db.escorting)

    def test_control_a_direct_step_to_a_perch_no_exit_reaches_is_not_barred(self):
        # The gap's own exit leads to solid room2; the perch is the far
        # roof, which no exit reaches: the usher steps aside, the leap
        # happens, the price is paid, the escort stands.
        other = self.escorted()
        self.jump("gap")
        self.price.assert_called_once()
        self.assertEqual(self.jumper.location, self.far)
        self.assertEqual(self.jumper.db.escorting, self.other)


class TheHoldAtTheThreshold(_AtTheThreshold):
    """A grappled victim is not touched by a jump refused at the threshold."""

    def setUp(self):
        super().setUp()
        self.victim = self.char2
        self.victim.location = self.roof
        self.heard = []
        self.victim.msg = lambda text=None, **kw: self.heard.append(str(text))
        self.handler = mock.MagicMock()
        self.handler.db.combatants = [
            {"char": self.jumper, DB_GRAPPLING_DBREF: get_character_dbref(self.victim)},
            {"char": self.victim, DB_GRAPPLED_BY_DBREF: get_character_dbref(self.jumper)},
        ]
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, self.handler)

    def grip(self):
        e = self.handler.db.combatants
        return (e[0].get(DB_GRAPPLING_DBREF), e[1].get(DB_GRAPPLED_BY_DBREF))

    def _refused_jumper_touches_nobody(self, kind, sky):
        self.channeling(self.jumper)
        self.channeling(self.victim)
        self.jump(kind, sky=sky)
        self.price.assert_not_called()
        self.assertEqual(self.heard, [], self.heard)
        self.assertTrue(channel_of(self.victim))
        self.assertEqual(self.grip(), (get_character_dbref(self.victim), get_character_dbref(self.jumper)))
        self.assertEqual(self.victim.location, self.roof)

    def test_a_refused_edge_jumper_touches_nobody(self):
        self._refused_jumper_touches_nobody("edge", False)

    def test_a_refused_edge_jumper_over_air_touches_nobody(self):
        self._refused_jumper_touches_nobody("edge", True)

    def test_a_refused_gap_jumper_touches_nobody(self):
        self._refused_jumper_touches_nobody("gap", False)
