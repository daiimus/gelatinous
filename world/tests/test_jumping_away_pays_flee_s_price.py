"""Jumping away in a fight pays flee's price -- and then goes (#3583).

Owner ruling, 2026-09-16. `flee` is refused at the edge, so the edge has
to stay a way out for the person who MEANS it. Leaving a fight by
stepping off a roof or leaping a gap costs exactly what fleeing costs --
BOTH halves of it (#3591):

* the AIM contest against whoever has you in their aim
  (``ndb.aimed_at_by``), and their opportunity attack if you lose it;
* the DISENGAGE roll against the best-Motorics opponent actually
  attacking you in the handler, and theirs if you lose that.

Either loss is paid in blood and neither is a refusal.

Two things separate it from `flee`, and both are the ruling:

* **the bold-move bonus.** The jumper adds ``JUMP_AWAY_BONUS`` to their
  roll -- *"the difficulty should be half or there should be a bonus.
  It's a bold move."* The knob is in the ledger; the number is not
  hardcoded here, so a balance pass moves it in one place.
* **the jump goes REGARDLESS.** A lost contest is not a refusal. You
  take the attack and you still go over. The only thing that stops the
  jump is that attack leaving you dead or unconscious -- and then it is
  the body that failed, not the verb.

So `flee` and `jump` share the contest and disagree about what a loss
means, which is why the contest is one module-level function
(``commands.combat.movement.break_aim_lock``) that both doors call,
rather than a second copy inside the jump verb (#3530, and the Two Doors
reference).

The helper is imported INSIDE each test rather than at module scope: a
module-level import of a name production has not grown yet turns one
red test into a collection error that hides the rest of the file.
``delay`` is patched to QUEUE its callbacks and drained after the
command returns, reproducing production order (the command finishes,
then the reactor fires the tick) -- the shim from
``test_a_leap_is_not_a_fall.py``.
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

import world.gravity as gravity
from world.combat import constants
from world.combat.constants import (
    NDB_AIMED_AT_BY,
    NDB_AIMING_AT,
    NDB_COMBAT_HANDLER,
    NDB_SKIP_ROUND,
)


def _break_aim_lock(caller, **kwargs):
    """Imported here, not at module scope -- see the module docstring."""
    from commands.combat.movement import break_aim_lock
    return break_aim_lock(caller, **kwargs)


def _roll_to_disengage(caller, handler, **kwargs):
    """The second half of flee's price, imported the same way."""
    from commands.combat.movement import roll_to_disengage
    return roll_to_disengage(caller, handler, **kwargs)


def _queue(mocked):
    """Collect scheduled callbacks instead of running them."""
    pending = []
    mocked.side_effect = (
        lambda _seconds, callback, *a, **kw: pending.append((callback, a, kw)))
    return pending


def _drain(pending, limit=40):
    """Fire the queue in order, the way a reactor would."""
    fired = 0
    while pending and fired < limit:
        callback, args, kwargs = pending.pop(0)
        callback(*args, **kwargs)
        fired += 1
    return fired


# ---------------------------------------------------------------------
# 1. the contest itself
# ---------------------------------------------------------------------


class _AimLockCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.runner = self.char1
        self.aimer = self.char2
        self.runner.location = self.room1
        self.aimer.location = self.room1
        self.said = []
        self.runner.msg = lambda text=None, **kw: self.said.append(str(text))

    def lock(self):
        setattr(self.runner.ndb, NDB_AIMED_AT_BY, self.aimer)
        setattr(self.aimer.ndb, NDB_AIMING_AT, self.runner)

    def aimed_at_by(self):
        return getattr(self.runner.ndb, NDB_AIMED_AT_BY, None)

    def aiming_at(self):
        return getattr(self.aimer.ndb, NDB_AIMING_AT, None)

    def contest(self, *, caller_rolls, aimer_rolls, bonus=0):
        """``standard_roll`` is imported into BOTH
        ``commands.combat.movement`` and ``world.combat.utils``; the
        contest reads the one in the movement module, so that is the
        name patched. Side effects are consumed in call order: the
        caller's roll first, then the aimer's."""
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(caller_rolls, 0, 0),
                                     (aimer_rolls, 0, 0)]) as rolled, \
             mock.patch("commands.combat.core_actions.CmdAttack.func") as hit:
            freed = _break_aim_lock(self.runner, bonus=bonus)
        self.rolled = rolled
        self.attacked = hit
        return freed

    def said_text(self):
        return " ".join(self.said)


class TestNobodyHasYouInTheirAim(_AimLockCase):
    def test_you_are_free_to_go(self):
        with mock.patch("commands.combat.movement.standard_roll") as rolled:
            self.assertTrue(_break_aim_lock(self.runner))
        self.assertEqual(rolled.call_count, 0, "rolled against nobody")

    def test_a_bonus_changes_nothing_when_there_is_no_contest(self):
        with mock.patch("commands.combat.movement.standard_roll") as rolled:
            self.assertTrue(_break_aim_lock(self.runner, bonus=20))
        self.assertEqual(rolled.call_count, 0)


class TestAStaleLockIsNoLock(_AimLockCase):
    """The aimer walked out of the room and nothing cleaned up after
    them. An ndb lock outlives the situation that made it, so the
    contest has to notice rather than roll against an absence."""

    def setUp(self):
        super().setUp()
        self.lock()
        self.aimer.location = self.room2

    def test_you_are_free_to_go(self):
        with mock.patch("commands.combat.movement.standard_roll") as rolled:
            self.assertTrue(_break_aim_lock(self.runner))
        self.assertEqual(rolled.call_count, 0, "rolled against a stale lock")

    def test_the_lock_is_cleared_on_the_runner(self):
        _break_aim_lock(self.runner)
        self.assertIsNone(self.aimed_at_by())

    def test_and_on_the_aimer(self):
        """Both halves, or the next thing to read the aimer's side sees
        a lock on somebody who is no longer there."""
        _break_aim_lock(self.runner)
        self.assertIsNone(self.aiming_at())


class TestTheBoldMoveBonusDecidesIt(_AimLockCase):
    """The decisive pair: identical rolls, and the bonus is the only
    difference between getting away and eating an attack."""

    def setUp(self):
        super().setUp()
        self.lock()

    def test_the_bonus_wins_a_roll_that_would_have_lost(self):
        self.assertTrue(self.contest(caller_rolls=10, aimer_rolls=25,
                                     bonus=20))

    def test_and_the_aimer_loses_their_lock(self):
        self.contest(caller_rolls=10, aimer_rolls=25, bonus=20)
        self.assertIsNone(self.aiming_at())

    def test_and_nobody_gets_a_free_shot(self):
        self.contest(caller_rolls=10, aimer_rolls=25, bonus=20)
        self.attacked.assert_not_called()

    def test_without_it_the_same_roll_loses(self):
        """The control."""
        self.assertFalse(self.contest(caller_rolls=10, aimer_rolls=25,
                                      bonus=0))

    def test_and_the_aimer_takes_their_shot(self):
        self.contest(caller_rolls=10, aimer_rolls=25, bonus=0)
        self.attacked.assert_called_once()

    def test_and_the_runner_is_told_they_are_still_pinned(self):
        self.contest(caller_rolls=10, aimer_rolls=25, bonus=0)
        self.assertIn("pinned", self.said_text())

    def test_the_lock_survives_a_loss(self):
        self.contest(caller_rolls=10, aimer_rolls=25, bonus=0)
        self.assertIs(self.aiming_at(), self.runner)


class TestTheContestIsStillAContest(_AimLockCase):
    """The bonus is an edge, not a licence."""

    def setUp(self):
        super().setUp()
        self.lock()

    def test_a_big_enough_roll_beats_the_bonus(self):
        self.assertFalse(self.contest(caller_rolls=1, aimer_rolls=999,
                                      bonus=20))

    def test_a_win_without_any_bonus_still_frees_you(self):
        self.assertTrue(self.contest(caller_rolls=99, aimer_rolls=1,
                                     bonus=0))

    def test_ties_favour_the_one_holding_the_aim(self):
        """`flee`'s own rule (`flee_roll > resist_roll`), unchanged."""
        self.assertFalse(self.contest(caller_rolls=5, aimer_rolls=25,
                                      bonus=20))


# ---------------------------------------------------------------------
# 2. what the jump verb pays
# ---------------------------------------------------------------------


class _PriceCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.aimer = self.char2
        self.jumper.location = self.room1
        self.aimer.location = self.room1
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))

    def price(self):
        """``pay_the_price_of_leaving()`` takes NO arguments. The price
        is owed to whoever is aiming; a combat handler is neither
        necessary nor sufficient, and passing one in was a seam."""
        from commands.combat.jump import CmdJump

        cmd = CmdJump()
        cmd.caller = self.jumper
        return cmd.pay_the_price_of_leaving()

    def said_text(self):
        return " ".join(self.said)

    def charged(self, *, freed=True):
        return mock.patch("commands.combat.movement.break_aim_lock",
                          return_value=freed)

    def handler(self, *others, targeting=()):
        """A handler shaped like the real one: `combatants` is a list of
        entries and `get_target_obj` answers who each one is attacking.
        A bare MagicMock lies here -- every attribute of one is truthy,
        so a fight nobody is fighting reads as a fight."""
        entries = [{"char": self.jumper}] + [{"char": o} for o in others]
        h = mock.MagicMock()
        h.db.combatants = entries
        h.get_target_obj.side_effect = lambda e: (
            self.jumper if e["char"] in targeting else None)
        h.get_grappled_by_obj.return_value = None
        h.get_grappling_obj.return_value = None
        return h


class TestOnlyAnAimLockCostsAnything(_PriceCase):
    def test_no_fight_and_no_aim_costs_nothing(self):
        with mock.patch("commands.combat.movement.break_aim_lock") as broke:
            self.assertTrue(self.price())
        broke.assert_not_called()

    def test_an_aim_lock_alone_is_enough_to_charge_you(self):
        """You need not be enrolled in a fight -- somebody sighting on
        you is the situation the price exists for."""
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)
        with self.charged() as broke:
            self.assertTrue(self.price())
        broke.assert_called_once()

    def test_a_fight_nobody_is_fighting_you_in_costs_nothing(self):
        """Being enrolled in a fight is NOT the trigger. Nobody has the
        jumper sighted and nobody is attacking them, so neither half of
        the price has anything to charge: no aim contest, no disengage
        roll, and the jump is free."""
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER,
                self.handler(self.aimer))          # present, on nobody
        with mock.patch("commands.combat.movement.break_aim_lock") as broke, \
             mock.patch("commands.combat.movement.standard_roll") as rolled:
            self.assertTrue(self.price())
        broke.assert_not_called()
        self.assertEqual(rolled.call_count, 0, "rolled against nobody")

    def test_but_somebody_attacking_you_is_charged(self):
        """The twin, and the control for it: the same fight with the
        same opponent, now on the jumper, DOES cost a disengage roll."""
        self.aimer.motorics = 30
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER,
                self.handler(self.aimer, targeting=(self.aimer,)))
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(999, 0, 0), (1, 0, 0)]) as rolled:
            self.assertTrue(self.price())
        self.assertEqual(rolled.call_count, 2)


class TestThePriceIsFleesPricePlusTheBonus(_PriceCase):
    def setUp(self):
        super().setUp()
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)

    def test_the_jumper_is_the_one_contesting(self):
        with self.charged() as broke:
            self.price()
        self.assertIs(broke.call_args.args[0], self.jumper)

    def test_the_bold_move_bonus_is_applied(self):
        with self.charged() as broke:
            self.price()
        self.assertEqual(broke.call_args.kwargs.get("bonus"),
                         constants.JUMP_AWAY_BONUS)

    def test_the_bonus_is_read_from_the_ledgered_knob_not_a_literal(self):
        """Behavioural, not a grep: the constant is imported INSIDE the
        method, so moving the knob moves what gets passed. A hardcoded
        20 beside a ledger row saying 20 would satisfy the assertion
        above and fail this one -- which is the whole drift (#2425)."""
        with mock.patch.object(constants, "JUMP_AWAY_BONUS", 1234):
            with self.charged() as broke:
                self.price()
        self.assertEqual(broke.call_args.kwargs.get("bonus"), 1234)

    def test_the_aim_half_is_resolved_on_the_spot(self):
        """The jumper is gone before the handler's next round, so the
        aimer's shot has to be thrown here or not at all (#3593)."""
        with self.charged() as broke:
            self.price()
        self.assertIs(broke.call_args.kwargs.get("immediate_attack"), True)

    def test_the_door_is_named_on_splattercast(self):
        """Combat is reviewed on one channel, so a jump contest must not
        read as a flee contest there."""
        with self.charged() as broke:
            self.price()
        self.assertEqual(broke.call_args.kwargs.get("label"), "JUMP_AWAY")


class TestALostContestDoesNotStopTheJump(_PriceCase):
    """The ruling's sharpest edge: never refused."""

    def setUp(self):
        super().setUp()
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)

    def lost(self):
        return self.charged(freed=False)

    def test_they_go_anyway(self):
        with self.lost():
            self.assertTrue(self.price())

    def test_and_are_told_so(self):
        with self.lost():
            self.price()
        self.assertIn("regardless", self.said_text())

    def test_a_won_contest_says_nothing_extra(self):
        """The control: winning is quiet, so "regardless" means the
        attack actually happened."""
        with self.charged():
            self.price()
        self.assertNotIn("regardless", self.said_text())


class TestOnlyTheBodyStopsTheJump(_PriceCase):
    """What a lost contest CAN do is kill you. A corpse does not leap."""

    def setUp(self):
        super().setUp()
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)

    def lost(self):
        return self.charged(freed=False)

    def test_the_attack_that_kills_them_stops_the_jump(self):
        with self.lost(), mock.patch.object(type(self.jumper), "is_dead",
                                            return_value=True):
            self.assertFalse(self.price())

    def test_the_attack_that_knocks_them_out_stops_the_jump(self):
        with self.lost(), \
             mock.patch.object(type(self.jumper), "is_dead",
                               return_value=False), \
             mock.patch.object(type(self.jumper), "is_unconscious",
                               return_value=True):
            self.assertFalse(self.price())

    def test_a_body_that_is_merely_hurt_still_jumps(self):
        """The control for both."""
        with self.lost(), \
             mock.patch.object(type(self.jumper), "is_dead",
                               return_value=False), \
             mock.patch.object(type(self.jumper), "is_unconscious",
                               return_value=False):
            self.assertTrue(self.price())


# ---------------------------------------------------------------------
# 3. WHEN the price is paid -- the ordering the verb owes the player
# ---------------------------------------------------------------------


class _OrderingCase(EvenniaTest):
    """The price is real: a lost contest feeds the aimer a free shot.
    So it must be charged only once the jump is REAL -- after the exit
    resolves and after it is the right kind of exit. Charged earlier, a
    typo'd direction is an attack on yourself.
    """

    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.aimer = self.char2
        self.jumper.location = self.room1
        self.aimer.location = self.room1
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)
        setattr(self.aimer.ndb, NDB_AIMING_AT, self.jumper)
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))

    def said_text(self):
        return " ".join(self.said)

    def descend(self, direction="south"):
        """``jump off <dir> edge`` against the real room fixture, with
        no `find_edge_exit` patch -- the point is what happens when the
        exit does NOT resolve."""
        from commands.combat.jump import CmdJump

        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = direction
        with ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            broke = stack.enter_context(
                mock.patch("commands.combat.movement.break_aim_lock",
                           return_value=True))
            cmd.handle_edge_descent()
        return broke


class TestAMisfiredJumpIsNeverCharged(_OrderingCase):
    def test_a_direction_with_no_exit_costs_nothing(self):
        self.exit.key = "south"
        self.exit.db.is_edge = True
        broke = self.descend(direction="nowhere")
        broke.assert_not_called()
        self.assertIs(self.jumper.location, self.room1)

    def test_an_exit_that_is_not_an_edge_costs_nothing(self):
        self.exit.key = "south"
        broke = self.descend()
        broke.assert_not_called()
        self.assertIn("not an edge", self.said_text())

    def test_an_unspecced_edge_flag_costs_nothing_either(self):
        """The jump verb reads the flag as strictly as `can_leave_by`
        does: `1` is not an edge, so this is a typo'd jump too."""
        self.exit.key = "south"
        self.exit.db.is_edge = 1
        broke = self.descend()
        broke.assert_not_called()

    def test_a_real_edge_is_charged(self):
        """The control. Without it every assertion above passes on a
        verb that never charges anybody."""
        self.exit.key = "south"
        self.exit.db.is_edge = True
        broke = self.descend()
        broke.assert_called_once()


class TestAnAbortedGapJumpKeepsItsGrip(_OrderingCase):
    """A grappler who leaps a gap lets go to do it -- but only once the
    leap is real. The price is paid first, and a price that leaves the
    jumper on the roof must leave the hold exactly as it was: a jumper
    dropped by the aimer's opportunity attack should not also have
    handed their victim a free release.
    """

    def setUp(self):
        super().setUp()
        self.victim = self.obj1
        handler = mock.MagicMock()
        handler.db.combatants = [{"char": self.jumper}]
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, handler)
        self.gap = self.exit
        self.gap.key = "east"
        self.gap.db.is_gap = True
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.gap.db.gap_destination = self.far

    def leap(self, *, downed):
        from commands.combat.jump import CmdJump

        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "east"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(mock.patch(
                "world.combat.grappling.get_grappled_by", return_value=None))
            stack.enter_context(mock.patch(
                "world.combat.grappling.get_grappling_target",
                return_value=self.victim))
            released = stack.enter_context(
                mock.patch("world.combat.grappling.break_grapple"))
            stack.enter_context(mock.patch(
                "commands.combat.jump.standard_roll",
                return_value=(999, 999, 999)))
            stack.enter_context(mock.patch(
                "commands.combat.movement.break_aim_lock",
                return_value=False))
            stack.enter_context(mock.patch.object(
                type(self.jumper), "is_dead", return_value=downed))
            stack.enter_context(mock.patch.object(
                type(self.jumper), "is_unconscious", return_value=False))
            cmd.handle_gap_jump()
        return released

    def test_a_jumper_the_attack_downs_keeps_hold_of_their_victim(self):
        released = self.leap(downed=True)
        released.assert_not_called()

    def test_and_the_victim_is_never_told_they_were_let_go(self):
        self.leap(downed=True)
        self.assertNotIn("release your grip", self.said_text())

    def test_and_the_jumper_never_leaves_the_roof(self):
        self.leap(downed=True)
        self.assertIs(self.jumper.location, self.room1)

    def test_a_jumper_who_survives_the_shot_does_let_go(self):
        """The control: losing the contest is not what keeps the grip,
        being DOWNED is."""
        released = self.leap(downed=False)
        released.assert_called_once()


# ---------------------------------------------------------------------
# 4. end to end, off a real roof
# ---------------------------------------------------------------------


class _JumpAwayCase(EvenniaCommandTest):
    """A roof with one south edge into an air cell, one cell down to the
    street, and somebody on the roof sighting on the jumper."""

    def setUp(self):
        super().setUp()
        self.roof = self.room1
        self.roof.key = "Test Roof"
        self.street = create_object("typeclasses.rooms.Room",
                                    key="Test Street")
        self.air = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air, destination=self.street,
                      aliases=["d"])
        self.edge = create_object("typeclasses.exits.Exit", key="south",
                                  location=self.roof, destination=self.air)
        self.edge.db.is_edge = True
        self.jumper = self.char1
        self.aimer = self.char2
        self.jumper.location = self.roof
        self.aimer.location = self.roof
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.aimer)
        setattr(self.aimer.ndb, NDB_AIMING_AT, self.jumper)

    def jump(self, *, win):
        """The real verb, from the typed string down."""
        from commands.combat.jump import CmdJump

        rolls = ([(999, 0, 0), (1, 0, 0)] if win
                 else [(1, 0, 0), (999, 0, 0)])
        cmd = CmdJump()
        with ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.combat.movement.msg_room_identity",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity,
                                                  "msg_room_identity"))
            self.attacked = stack.enter_context(
                mock.patch("commands.combat.core_actions.CmdAttack.func"))
            stack.enter_context(
                mock.patch("commands.combat.movement.standard_roll",
                           side_effect=rolls))
            stack.enter_context(
                mock.patch.object(type(cmd), "find_edge_exit",
                                  return_value=self.edge))
            self.delayed = stack.enter_context(
                mock.patch.object(gravity, "delay"))
            pending = _queue(self.delayed)
            out = self.call(cmd, "off south edge", caller=self.jumper)
            _drain(pending)
        return out


class TestLosingTheContestCostsAnAttackNotTheJump(_JumpAwayCase):
    def test_the_aimer_gets_their_shot(self):
        self.jump(win=False)
        self.attacked.assert_called_once()

    def test_the_jumper_is_told_they_go_regardless(self):
        self.assertIn("regardless", self.jump(win=False))

    def test_they_leave_the_roof(self):
        self.jump(win=False)
        self.assertIsNot(self.jumper.location, self.roof)

    def test_they_ride_the_column_to_the_street(self):
        self.jump(win=False)
        self.assertIs(self.jumper.location, self.street)

    def test_the_fall_was_a_real_fall_not_a_teleport(self):
        """The cell WALKED them down the column -- one scheduled tick
        through gravity's own step -- rather than the verb depositing
        them at the bottom. Without this the street assertion above
        would also be satisfied by a teleport."""
        self.jump(win=False)
        self.assertEqual(self.delayed.call_count, 1)
        self.assertIs(self.delayed.call_args[0][1], gravity._fall_step)

    def test_and_it_finished(self):
        self.jump(win=False)
        self.assertFalse(self.jumper.db.falling, "still falling")


class TestWinningTheContestIsJustAJump(_JumpAwayCase):
    """The control."""

    def test_nobody_gets_a_free_shot(self):
        self.jump(win=True)
        self.attacked.assert_not_called()

    def test_nothing_is_said_about_going_regardless(self):
        self.assertNotIn("regardless", self.jump(win=True))

    def test_the_aim_lock_is_broken(self):
        self.jump(win=True)
        self.assertIsNone(getattr(self.aimer.ndb, NDB_AIMING_AT, None))

    def test_they_still_end_up_in_the_street(self):
        self.jump(win=True)
        self.assertIs(self.jumper.location, self.street)


# ---------------------------------------------------------------------
# 5. the other half of the price: the disengage roll
# ---------------------------------------------------------------------


class _DisengageCase(EvenniaTest):
    """A fight whose opponents' targets can be steered.

    What holds you is somebody ATTACKING you, not somebody merely
    enrolled in the same fight -- the distinction
    ``test_you_cannot_stroll_out_of_a_fight.py`` draws on the advance
    door, drawn again here.
    """

    def setUp(self):
        super().setUp()
        self.runner = self.char1
        self.blocker = self.char2
        self.runner.location = self.room1
        self.blocker.location = self.room1
        self.runner.motorics = 10
        self.blocker.motorics = 30
        self.said = []
        self.runner.msg = lambda text=None, **kw: self.said.append(str(text))

    def handler(self, *others, targeting=()):
        entries = [{"char": self.runner}] + [{"char": o} for o in others]
        h = mock.MagicMock()
        h.db.combatants = entries
        h.get_target_obj.side_effect = lambda e: (
            self.runner if e["char"] in targeting else None)
        h.get_grappled_by_obj.return_value = None
        h.get_grappling_obj.return_value = None
        return h

    def disengage(self, handler, *, runner_rolls=1, blocker_rolls=1, bonus=0):
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(runner_rolls, 0, 0),
                                     (blocker_rolls, 0, 0)]) as rolled:
            out = _roll_to_disengage(self.runner, handler, bonus=bonus)
        self.rolled = rolled
        return out


class TestNobodyIsHoldingTheDoor(_DisengageCase):
    def test_an_empty_fight_costs_nothing(self):
        won, blocker, opponents = self.disengage(self.handler())
        self.assertTrue(won)
        self.assertIsNone(blocker)
        self.assertEqual(opponents, [])
        self.assertEqual(self.rolled.call_count, 0, "rolled against nobody")

    def test_an_opponent_fighting_someone_else_does_not_hold_you(self):
        """Enrolled, in the room, and no claim on where you go."""
        won, blocker, opponents = self.disengage(self.handler(self.blocker))
        self.assertTrue(won)
        self.assertIsNone(blocker)
        self.assertEqual(opponents, [])
        self.assertEqual(self.rolled.call_count, 0)


class TestTheDisengageRollTakesTheBonusToo(_DisengageCase):
    """The decisive pair again, on the second contest: same rolls, and
    the bold-move bonus is the only difference."""

    def setUp(self):
        super().setUp()
        self.fight = self.handler(self.blocker, targeting=(self.blocker,))

    def test_the_bonus_wins_a_roll_that_would_have_lost(self):
        won, blocker, opponents = self.disengage(
            self.fight, runner_rolls=10, blocker_rolls=25, bonus=20)
        self.assertTrue(won)
        self.assertIs(blocker, self.blocker)
        self.assertEqual(opponents, [self.blocker])

    def test_without_it_the_same_roll_loses(self):
        won, blocker, _ = self.disengage(
            self.fight, runner_rolls=10, blocker_rolls=25, bonus=0)
        self.assertFalse(won)
        self.assertIs(blocker, self.blocker)

    def test_a_tie_goes_to_the_one_holding_on(self):
        won, _, _ = self.disengage(
            self.fight, runner_rolls=25, blocker_rolls=25)
        self.assertFalse(won)

    def test_a_big_enough_roll_still_beats_the_bonus(self):
        won, _, _ = self.disengage(
            self.fight, runner_rolls=1, blocker_rolls=999, bonus=20)
        self.assertFalse(won)


class TestTheBestOpponentHoldsTheDoor(_DisengageCase):
    """One roll, against the hardest of them -- not one roll each."""

    def setUp(self):
        super().setUp()
        self.weak = create_object("typeclasses.characters.Character",
                                  key="Weakling", location=self.room1)
        self.weak.motorics = 3
        self.blocker.motorics = 30
        self.fight = self.handler(self.weak, self.blocker,
                                  targeting=(self.weak, self.blocker))

    def test_the_hardest_opponent_is_the_blocker(self):
        _, blocker, opponents = self.disengage(self.fight)
        self.assertIs(blocker, self.blocker)
        self.assertEqual(len(opponents), 2)

    def test_the_roll_is_against_that_opponents_motorics(self):
        """The control on the line above: naming the blocker is only
        worth anything if the dice are rolled against their number."""
        self.disengage(self.fight)
        self.assertEqual(self.rolled.call_count, 2)
        self.assertEqual(self.rolled.call_args_list[0].args[0], 10)
        self.assertEqual(self.rolled.call_args_list[1].args[0], 30)


class TestTheDisengageHalfIsPaidByTheJumper(_PriceCase):
    """`pay_the_price_of_leaving` with nobody aiming and somebody
    attacking: the second half on its own."""

    def setUp(self):
        super().setUp()
        self.blocker = self.aimer          # same body, different role
        self.blocker.motorics = 30
        self.jumper.motorics = 10
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER,
                self.handler(self.blocker, targeting=(self.blocker,)))

    def pay(self, *, win, downed=False):
        rolls = ([(999, 0, 0), (1, 0, 0)] if win
                 else [(1, 0, 0), (999, 0, 0)])
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=rolls), \
             mock.patch("commands.combat.movement.opportunity_attack") as hit, \
             mock.patch.object(type(self.jumper), "is_dead",
                               return_value=downed), \
             mock.patch.object(type(self.jumper), "is_unconscious",
                               return_value=False):
            out = self.price()
        self.attacked = hit
        return out

    def test_a_lost_roll_hands_the_blocker_a_shot(self):
        self.pay(win=False)
        self.attacked.assert_called_once_with(
            self.blocker, self.jumper, immediate=True)

    def test_and_the_jumper_is_told_who_caught_them(self):
        self.pay(win=False)
        self.assertIn("catches you", self.said_text())

    def test_and_they_go_over_anyway(self):
        self.assertTrue(self.pay(win=False))
        self.assertIn("regardless", self.said_text())

    def test_a_won_roll_costs_nothing(self):
        """The control."""
        self.assertTrue(self.pay(win=True))
        self.attacked.assert_not_called()
        self.assertNotIn("regardless", self.said_text())

    def test_a_blocker_who_downs_them_stops_the_jump(self):
        self.assertFalse(self.pay(win=False, downed=True))


class TestTheAimHalfAttacksThroughTheSharedHelper(_AimLockCase):
    """#3591 pulled the CmdAttack construction out into
    `opportunity_attack`, shared by both contests. The aim half must
    still reach it -- an extraction that quietly drops one caller is the
    whole risk."""

    def setUp(self):
        super().setUp()
        self.lock()

    def shot(self, *, caller_rolls, aimer_rolls):
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(caller_rolls, 0, 0),
                                     (aimer_rolls, 0, 0)]), \
             mock.patch("commands.combat.movement.opportunity_attack") as hit:
            freed = _break_aim_lock(self.runner)
        return freed, hit

    def test_a_lost_aim_contest_fires_one_shot(self):
        """Called plainly -- the way `flee` calls it -- the shot is
        enrolled for the next round, not resolved here."""
        freed, hit = self.shot(caller_rolls=10, aimer_rolls=25)
        self.assertFalse(freed)
        hit.assert_called_once_with(self.aimer, self.runner, immediate=False)

    def test_the_flag_is_forwarded_when_it_is_asked_for(self):
        """And the jump verbs ask for it."""
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(10, 0, 0), (25, 0, 0)]), \
             mock.patch("commands.combat.movement.opportunity_attack") as hit:
            _break_aim_lock(self.runner, immediate_attack=True)
        hit.assert_called_once_with(self.aimer, self.runner, immediate=True)

    def test_a_won_aim_contest_fires_none(self):
        freed, hit = self.shot(caller_rolls=99, aimer_rolls=1)
        self.assertTrue(freed)
        hit.assert_not_called()


# ---------------------------------------------------------------------
# 6. flee still behaves exactly as it did (a behaviour-preserving lift)
# ---------------------------------------------------------------------


class _FleeDisengageCase(EvenniaTest):
    """`CmdFlee` Part 2 now calls the extracted `roll_to_disengage`. The
    extraction is only safe if flee's own consequence for a loss is
    unchanged: blocked, told so, a round skipped, and NOT moved."""

    def setUp(self):
        super().setUp()
        self.runner = self.char1
        self.blocker = self.char2
        self.runner.location = self.room1
        self.blocker.location = self.room1
        self.runner.motorics = 10
        self.blocker.motorics = 30
        self.said = []
        self.runner.msg = lambda text=None, **kw: self.said.append(str(text))
        h = mock.MagicMock()
        h.db.combatants = [{"char": self.runner}, {"char": self.blocker}]
        h.db.combat_is_running = True
        h.get_target_obj.side_effect = lambda e: (
            self.runner if e["char"] is self.blocker else None)
        h.get_grappled_by_obj.return_value = None
        h.get_grappling_obj.return_value = None
        self.fight = h
        setattr(self.runner.ndb, NDB_COMBAT_HANDLER, h)

    def flee(self, *, win=True):
        from commands.combat.movement import CmdFlee

        rolls = ([(999, 0, 0), (1, 0, 0)] if win
                 else [(1, 0, 0), (999, 0, 0)])
        cmd = CmdFlee()
        cmd.caller = self.runner
        cmd.args = ""
        cmd.obj = self.runner
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=rolls), \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            cmd.func()
        return " ".join(self.said)

    def skipping(self):
        return bool(getattr(self.runner.ndb, NDB_SKIP_ROUND, False))


class TestALostDisengageStillBlocksTheFlee(_FleeDisengageCase):
    def test_they_do_not_move(self):
        self.flee(win=False)
        self.assertIs(self.runner.location, self.room1)

    def test_they_are_told_who_blocked_them(self):
        self.assertIn("block your escape", self.flee(win=False))

    def test_and_they_skip_a_round_for_it(self):
        self.flee(win=False)
        self.assertTrue(self.skipping())

    def test_a_won_disengage_still_gets_them_out(self):
        """The control."""
        out = self.flee(win=True)
        self.assertIs(self.runner.location, self.room2)
        self.assertIn("successfully flee", out)

    def test_and_costs_no_skipped_round(self):
        self.flee(win=True)
        self.assertFalse(self.skipping())


class TestFleeingIsStillNotABoldMove(_FleeDisengageCase):
    def test_flee_passes_no_bonus_to_the_disengage_roll(self):
        """The bonus belongs to the jump. Flee asks the same function
        and must ask it plainly, or `flee` silently became the better
        escape the moment the helper was shared."""
        with mock.patch("commands.combat.movement.roll_to_disengage",
                        return_value=(True, None, [])) as rolled, \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            from commands.combat.movement import CmdFlee
            cmd = CmdFlee()
            cmd.caller = self.runner
            cmd.args = ""
            cmd.obj = self.runner
            cmd.func()
        rolled.assert_called_once()
        self.assertFalse(rolled.call_args.kwargs.get("bonus"))
        self.assertFalse(rolled.call_args.kwargs.get("label"))


# ---------------------------------------------------------------------
# 7. and the gap verb pays it as well
# ---------------------------------------------------------------------


class TestAGapJumpPaysTheDisengageHalf(EvenniaTest):
    """`jump across` and `jump off` share one price, so the second half
    has to be charged on both doors -- the Two Doors problem, which is
    what put `pay_the_price_of_leaving` on the command in the first
    place."""

    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.blocker = self.char2
        self.jumper.location = self.room1
        self.blocker.location = self.room1
        self.jumper.motorics = 10
        self.blocker.motorics = 30
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.gap = self.exit
        self.gap.key = "east"
        self.gap.db.is_gap = True
        self.gap.db.gap_destination = self.far
        h = mock.MagicMock()
        h.db.combatants = [{"char": self.jumper}, {"char": self.blocker}]
        h.get_target_obj.side_effect = lambda e: (
            self.jumper if e["char"] is self.blocker else None)
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, h)

    def leap(self, *, win):
        from commands.combat.jump import CmdJump

        rolls = ([(999, 0, 0), (1, 0, 0)] if win
                 else [(1, 0, 0), (999, 0, 0)])
        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "east"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(mock.patch(
                "world.combat.grappling.get_grappled_by", return_value=None))
            stack.enter_context(mock.patch(
                "world.combat.grappling.get_grappling_target",
                return_value=None))
            stack.enter_context(mock.patch(
                "commands.combat.jump.standard_roll",
                return_value=(999, 999, 999)))
            stack.enter_context(mock.patch(
                "commands.combat.movement.standard_roll", side_effect=rolls))
            self.attacked = stack.enter_context(mock.patch(
                "commands.combat.movement.opportunity_attack"))
            cmd.handle_gap_jump()
        return " ".join(self.said)

    def test_a_lost_roll_hands_the_blocker_a_shot(self):
        """Resolved on the spot: the leaper is off the roof inside this
        same command, so a shot left for the next round is no shot."""
        self.leap(win=False)
        self.attacked.assert_called_once_with(
            self.blocker, self.jumper, immediate=True)

    def test_and_the_leap_still_happens(self):
        """Never refused -- the ruling holds on this door too."""
        out = self.leap(win=False)
        self.assertIn("regardless", out)
        self.assertIs(self.jumper.location, self.far)

    def test_a_won_roll_costs_nothing(self):
        """The control."""
        out = self.leap(win=True)
        self.attacked.assert_not_called()
        self.assertNotIn("regardless", out)
        self.assertIs(self.jumper.location, self.far)


# ---------------------------------------------------------------------
# 8. the shot has to actually go off (#3593)
# ---------------------------------------------------------------------
#
# Owner, watching it in play: *"It doesn't look like EdgeAimer actually
# fired a shot though..."* -- and they were right. `opportunity_attack`
# ran the real `attack` command, which ENROLS: it puts the attacker in
# the handler with the target and prints the weapon's initiate line
# ("levels the pistol"). The shot itself is resolved by the handler on
# its next round.
#
# For a blocked fleer that is fine; they are still standing there when
# the round fires. For a jumper it is nothing at all: they are out of
# the handler and off the roof inside the same command, so the round
# that would have resolved the shot never finds them. The price was
# announced, the attack was "made", and no dice were ever thrown.
#
# So the jump verbs pass `immediate=True` and the shot is resolved on
# the spot -- once, before they leave. Flee keeps the enrolling
# behaviour it always had.


class _ShotCase(EvenniaTest):
    """An attacker holding a real-shaped handler with their own entry in
    it, which is what the immediate resolution needs to find."""

    def setUp(self):
        super().setUp()
        self.attacker = self.char1
        self.target = self.char2
        self.attacker.location = self.room1
        self.target.location = self.room1
        self.entry = {"char": self.attacker}
        self.fight = mock.MagicMock()
        self.fight.db.combatants = [self.entry, {"char": self.target}]
        setattr(self.attacker.ndb, NDB_COMBAT_HANDLER, self.fight)

    def fire(self, **kwargs):
        """Watches the SHOT -- `process_attack`, the function that
        actually throws dice. `resolve_bonus_attack` calls it, so this
        catches the whole chain and answers the owner's question ("did
        a shot go off?") rather than "was a helper called?"."""
        from commands.combat.movement import opportunity_attack

        with mock.patch("commands.combat.core_actions.CmdAttack.func") as enrol, \
             mock.patch("world.combat.attack.process_attack") as resolved:
            opportunity_attack(self.attacker, self.target, **kwargs)
        self.enrolled = enrol
        return resolved

    def fire_watching_the_helper(self, **kwargs):
        """Watches the DELEGATION instead -- one rung higher up."""
        from commands.combat.movement import opportunity_attack

        with mock.patch("commands.combat.core_actions.CmdAttack.func"), \
             mock.patch("world.combat.utils.resolve_bonus_attack") as bonus:
            opportunity_attack(self.attacker, self.target, **kwargs)
        return bonus


class TestAnImmediateShotIsActuallyResolved(_ShotCase):
    def test_it_resolves_exactly_once(self):
        resolved = self.fire(immediate=True)
        resolved.assert_called_once_with(
            self.fight, self.attacker, self.target, self.entry,
            self.fight.db.combatants)

    def test_it_still_enrols_first(self):
        """The enrolment is what puts the attacker in the handler and
        prints the initiate line; resolving replaces the WAIT, not the
        command."""
        self.fire(immediate=True)
        self.enrolled.assert_called_once()

    def test_without_the_flag_nothing_is_resolved(self):
        """The control, and flee's behaviour: enrol and let the round
        fire it."""
        resolved = self.fire()
        resolved.assert_not_called()
        self.enrolled.assert_called_once()

    def test_it_goes_through_the_bonus_attack_helper_that_already_existed(self):
        """One implementation, two doors: this is the same immediate
        attack a ranged defender already gets when an advance or charge
        at them fails. A private second copy of the entry lookup and the
        `process_attack` call is exactly how two doors drift (#3530)."""
        bonus = self.fire_watching_the_helper(immediate=True)
        bonus.assert_called_once_with(self.fight, self.attacker, self.target)

    def test_and_not_when_the_flag_is_absent(self):
        self.fire_watching_the_helper().assert_not_called()


class TestAnImmediateShotWithNowhereToResolveIsQuiet(_ShotCase):
    """`process_attack` needs the attacker's own combat entry. If the
    enrolment did not produce one, the honest answer is no shot -- not
    a traceback in the middle of somebody's jump."""

    def test_no_entry_for_the_attacker_fires_nothing(self):
        self.fight.db.combatants = [{"char": self.target}]
        resolved = self.fire(immediate=True)
        resolved.assert_not_called()

    def test_no_handler_at_all_fires_nothing(self):
        setattr(self.attacker.ndb, NDB_COMBAT_HANDLER, None)
        resolved = self.fire(immediate=True)
        resolved.assert_not_called()

    def test_an_empty_handler_fires_nothing(self):
        self.fight.db.combatants = None
        resolved = self.fire(immediate=True)
        resolved.assert_not_called()

    def test_no_handler_does_not_even_reach_the_helper(self):
        setattr(self.attacker.ndb, NDB_COMBAT_HANDLER, None)
        self.fire_watching_the_helper(immediate=True).assert_not_called()

    def test_a_resolution_that_blows_up_does_not_blow_up_the_jump(self):
        """The price was already announced and the jumper is mid-leap;
        a traceback out of here would abort a jump that the ruling says
        is never refused."""
        from commands.combat.movement import opportunity_attack

        with mock.patch("commands.combat.core_actions.CmdAttack.func"), \
             mock.patch("world.combat.utils.resolve_bonus_attack",
                        side_effect=RuntimeError("boom")):
            opportunity_attack(self.attacker, self.target, immediate=True)


class _JumperUnderFireCase(EvenniaTest):
    """A roof, an edge into an air cell with a street under it, and one
    opponent who is both able to aim and able to block."""

    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.opponent = self.char2
        self.roof = self.room1
        self.roof.key = "Test Roof"
        self.jumper.location = self.roof
        self.opponent.location = self.roof
        self.jumper.motorics = 10
        self.opponent.motorics = 30
        self.street = create_object("typeclasses.rooms.Room",
                                    key="Test Street")
        self.air = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air, destination=self.street,
                      aliases=["d"])
        self.edge = create_object("typeclasses.exits.Exit", key="south",
                                  location=self.roof, destination=self.air)
        self.edge.db.is_edge = True
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))

        self.opponent_entry = {"char": self.opponent}
        self.fight = mock.MagicMock()
        self.fight.db.combatants = [{"char": self.jumper},
                                    self.opponent_entry]
        self.fight.get_target_obj.side_effect = lambda e: None
        setattr(self.opponent.ndb, NDB_COMBAT_HANDLER, self.fight)

    def aim_at_the_jumper(self):
        setattr(self.jumper.ndb, NDB_AIMED_AT_BY, self.opponent)
        setattr(self.opponent.ndb, NDB_AIMING_AT, self.jumper)

    def attack_the_jumper(self):
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, self.fight)
        self.fight.get_target_obj.side_effect = lambda e: (
            self.jumper if e["char"] is self.opponent else None)

    def descend(self, *, win):
        """`jump off south edge`, with the shot's resolution recorded
        ALONG WITH where the jumper was standing when it fired."""
        from commands.combat.jump import CmdJump

        rolls = ([(999, 0, 0), (1, 0, 0)] if win
                 else [(1, 0, 0), (999, 0, 0)])
        self.fired_from = []
        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "south"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.combat.core_actions.CmdAttack.func",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            delayed = stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(mock.patch(
                "commands.combat.movement.standard_roll", side_effect=rolls))
            stack.enter_context(mock.patch.object(
                type(cmd), "find_edge_exit", return_value=self.edge))
            self.resolved = stack.enter_context(
                mock.patch("world.combat.attack.process_attack"))
            self.resolved.side_effect = (
                lambda *a, **kw: self.fired_from.append(self.jumper.location))
            pending = _queue(delayed)
            cmd.handle_edge_descent()
            _drain(pending)
        return " ".join(self.said)


class TestTheAimersShotGoesOffBeforeTheyLeave(_JumperUnderFireCase):
    def setUp(self):
        super().setUp()
        self.aim_at_the_jumper()

    def test_one_shot_is_resolved(self):
        self.descend(win=False)
        self.resolved.assert_called_once()

    def test_the_jumper_is_the_one_shot_at(self):
        self.descend(win=False)
        self.assertIs(self.resolved.call_args.args[2], self.jumper)

    def test_and_it_fires_while_they_are_still_on_the_roof(self):
        """The whole finding. A shot resolved after the move is a shot
        at an empty rooftop."""
        self.descend(win=False)
        self.assertEqual(self.fired_from, [self.roof])

    def test_they_still_go_over(self):
        self.descend(win=False)
        self.assertIs(self.jumper.location, self.street)

    def test_a_won_contest_resolves_nothing(self):
        """The control."""
        self.descend(win=True)
        self.resolved.assert_not_called()
        self.assertIs(self.jumper.location, self.street)


class TestTheBlockersShotGoesOffBeforeTheyLeave(_JumperUnderFireCase):
    """The other half of the price, same requirement."""

    def setUp(self):
        super().setUp()
        self.attack_the_jumper()

    def test_one_shot_is_resolved(self):
        self.descend(win=False)
        self.resolved.assert_called_once()

    def test_the_jumper_is_the_one_shot_at(self):
        self.descend(win=False)
        self.assertIs(self.resolved.call_args.args[2], self.jumper)

    def test_and_it_fires_while_they_are_still_on_the_roof(self):
        self.descend(win=False)
        self.assertEqual(self.fired_from, [self.roof])

    def test_they_still_go_over(self):
        out = self.descend(win=False)
        self.assertIn("regardless", out)
        self.assertIs(self.jumper.location, self.street)

    def test_a_won_roll_resolves_nothing(self):
        """The control."""
        self.descend(win=True)
        self.resolved.assert_not_called()
        self.assertIs(self.jumper.location, self.street)


class TestFleeStillWaitsForTheRound(EvenniaTest):
    """Flee's loss leaves the fleer standing in the room, so the
    handler's next round is a perfectly good time to resolve the shot.
    Nothing about #3593 changes that -- and an immediate resolution here
    would be a second shot the round is also going to fire.
    """

    def setUp(self):
        super().setUp()
        self.runner = self.char1
        self.opponent = self.char2
        self.runner.location = self.room1
        self.opponent.location = self.room1
        self.runner.motorics = 10
        self.opponent.motorics = 30
        self.said = []
        self.runner.msg = lambda text=None, **kw: self.said.append(str(text))
        self.fight = mock.MagicMock()
        self.fight.db.combatants = [{"char": self.runner},
                                    {"char": self.opponent}]
        self.fight.db.combat_is_running = True
        self.fight.get_grappled_by_obj.return_value = None
        self.fight.get_grappling_obj.return_value = None
        self.fight.get_target_obj.side_effect = lambda e: None

    def flee(self):
        from commands.combat.movement import CmdFlee

        cmd = CmdFlee()
        cmd.caller = self.runner
        cmd.args = ""
        cmd.obj = self.runner
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=[(1, 0, 0), (999, 0, 0)]), \
             mock.patch("commands.combat.core_actions.CmdAttack.func"), \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch("world.combat.attack.process_attack") as resolved:
            cmd.func()
        return resolved

    def test_a_lost_aim_contest_resolves_nothing_on_the_spot(self):
        setattr(self.runner.ndb, NDB_AIMED_AT_BY, self.opponent)
        setattr(self.opponent.ndb, NDB_AIMING_AT, self.runner)
        resolved = self.flee()
        self.assertIs(self.runner.location, self.room1)
        resolved.assert_not_called()

    def test_flee_never_asks_the_aim_half_to_resolve_on_the_spot(self):
        setattr(self.runner.ndb, NDB_AIMED_AT_BY, self.opponent)
        setattr(self.opponent.ndb, NDB_AIMING_AT, self.runner)
        with mock.patch("commands.combat.movement.break_aim_lock",
                        return_value=False) as broke, \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            from commands.combat.movement import CmdFlee
            cmd = CmdFlee()
            cmd.caller = self.runner
            cmd.args = ""
            cmd.obj = self.runner
            cmd.func()
        broke.assert_called_once()
        self.assertFalse(broke.call_args.kwargs.get("immediate_attack"))

    def test_a_lost_disengage_roll_resolves_nothing_on_the_spot(self):
        setattr(self.runner.ndb, NDB_COMBAT_HANDLER, self.fight)
        self.fight.get_target_obj.side_effect = lambda e: (
            self.runner if e["char"] is self.opponent else None)
        resolved = self.flee()
        self.assertIs(self.runner.location, self.room1)
        resolved.assert_not_called()
