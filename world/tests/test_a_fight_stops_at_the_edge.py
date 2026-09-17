"""Combat movement is refused at the edge (#3583).

Owner ruling, 2026-09-16: *"refused at the edge"*. `flee`, `advance` and
`charge` never take an edge exit, a gap exit, or an exit into an air
room -- for anyone who cannot stay up. A roof whose only ways off are
edges is a tactical spot, not a place you can be chased out of by a bad
roll, and a fight there is a fight with nowhere to go.

**Why the predicate exists at all.** Walking already refuses these at
``Exit.at_traverse``. Combat movement does not traverse: `flee`,
`_do_advance_move` and the cross-room charge all relocate with a direct
``move_to``, so the exit's own refusal is never reached and each door
has to ask for itself. ``world.gravity.can_leave_by`` is the one
predicate all three ask, so the three doors cannot drift apart -- the
#3530 lesson, and the Two Doors reference's whole subject.

``db.stays_aloft is True`` is the exemption and the ONLY one: a flier,
a hovering vehicle, a future capability. Strict, because truthiness
lied once already (``world/spatial/pathfind.py:180-185``) and a builder
who types ``1`` means something different from a flag the system set.

The layers here, cheapest first:

1. the predicate itself, on doubles -- no DB, no harness;
2. `flee` on a real room whose only exit is an edge;
3. cross-room `advance` and `charge`, driven the way
   ``test_you_cannot_stroll_out_of_a_fight.py`` drives them.

The refusals are not silent. Each names the edge and says what the
right verb would have been -- "that is a jump, not an advance" -- which
is the difference between a rule and a bug.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import (
    DB_CHAR,
    DB_COMBAT_ACTION_TARGET,
    NDB_AIMED_AT_BY,
    NDB_AIMING_AT,
)
import world.gravity as gravity
from world.gravity import can_leave_by


# ---------------------------------------------------------------------
# 1. the predicate
# ---------------------------------------------------------------------


class _DB(SimpleNamespace):
    """A ``db`` handler, which answers None for anything unset.

    A bare SimpleNamespace raises instead, which makes it a STRICTER
    object than the thing it stands in for (test_build_tools.py:74).
    """

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return None


def _room(**flags):
    return SimpleNamespace(db=_DB(**flags), key="a room")


def _way_out(destination=None, **flags):
    return SimpleNamespace(db=_DB(**flags), destination=destination,
                           key="south")


def _body(**flags):
    return SimpleNamespace(db=_DB(**flags), key="a body")


class TestWhatCountsAsAWayOut(TestCase):
    """``can_leave_by(mover, exit)`` -- pure, DB-free."""

    def test_a_plain_exit_is_a_way_out(self):
        self.assertTrue(can_leave_by(_body(), _way_out(_room())))

    def test_a_plain_exit_with_no_destination_at_all_is_still_walkable(self):
        """The predicate answers "would this drop you", not "does this
        go anywhere" -- the callers already check the destination."""
        self.assertTrue(can_leave_by(_body(), _way_out(None)))

    def test_no_exit_at_all_is_not_a_way_out(self):
        self.assertFalse(can_leave_by(_body(), None))

    def test_an_edge_is_not_a_way_out(self):
        self.assertFalse(
            can_leave_by(_body(), _way_out(_room(), is_edge=True)))

    def test_a_gap_is_not_a_way_out(self):
        self.assertFalse(
            can_leave_by(_body(), _way_out(_room(), is_gap=True)))

    def test_an_exit_into_air_is_not_a_way_out(self):
        self.assertFalse(
            can_leave_by(_body(), _way_out(_room(is_sky_room=True))))


class TestOnlyAFlierIsExempt(TestCase):
    def test_a_flier_may_leave_by_an_edge(self):
        self.assertTrue(can_leave_by(_body(stays_aloft=True),
                                     _way_out(_room(), is_edge=True)))

    def test_a_flier_may_leave_by_a_gap(self):
        self.assertTrue(can_leave_by(_body(stays_aloft=True),
                                     _way_out(_room(), is_gap=True)))

    def test_a_flier_may_leave_into_air(self):
        self.assertTrue(can_leave_by(_body(stays_aloft=True),
                                     _way_out(_room(is_sky_room=True))))

    def test_a_flier_is_not_stopped_by_a_plain_exit_either(self):
        self.assertTrue(can_leave_by(_body(stays_aloft=True),
                                     _way_out(_room())))


class TestEveryFlagIsStrict(TestCase):
    """Truthiness lied once already. ``1`` is not ``True``."""

    def test_is_edge_one_is_not_an_edge(self):
        self.assertTrue(can_leave_by(_body(), _way_out(_room(), is_edge=1)))

    def test_is_gap_one_is_not_a_gap(self):
        self.assertTrue(can_leave_by(_body(), _way_out(_room(), is_gap=1)))

    def test_is_sky_room_one_is_not_air(self):
        self.assertTrue(can_leave_by(_body(), _way_out(_room(is_sky_room=1))))

    def test_stays_aloft_one_does_not_exempt_you(self):
        """The exemption is the strictest flag of the four -- a loose
        one here is somebody walking off a roof."""
        self.assertFalse(can_leave_by(_body(stays_aloft=1),
                                      _way_out(_room(), is_edge=True)))


# ---------------------------------------------------------------------
# 2. flee
# ---------------------------------------------------------------------


class _FleeCase(EvenniaTest):
    """room1 -- one exit -- room2, and somebody holding an aim lock.

    An aim lock is the cheapest way to give `flee` something to flee
    FROM without standing up a whole combat handler: it drives the
    aim-break contest and then the move.
    """

    def setUp(self):
        super().setUp()
        self.runner = self.char1
        self.aimer = self.char2
        self.runner.location = self.room1
        self.aimer.location = self.room1
        setattr(self.runner.ndb, NDB_AIMED_AT_BY, self.aimer)
        setattr(self.aimer.ndb, NDB_AIMING_AT, self.runner)
        self.said = []
        self.runner.msg = lambda text=None, **kw: self.said.append(str(text))

    def test_the_fixture_has_exactly_one_way_out(self):
        """Every case below turns on the ONLY exit being unusable. A
        second exit from the harness would make them all pass for the
        wrong reason."""
        self.assertEqual(list(self.room1.exits), [self.exit])

    def flee(self, *, win=True, rolls=None):
        """The real command. The aim contest defaults to a WIN so the
        only thing that can keep them in the room is the exit pool.
        `rolls` overrides the pair outright, caller's roll first."""
        from commands.combat.movement import CmdFlee

        rolls = rolls or ([(999, 999, 999), (1, 1, 1)] if win
                          else [(1, 1, 1), (999, 999, 999)])
        cmd = CmdFlee()
        cmd.caller = self.runner
        cmd.args = ""
        cmd.obj = self.runner
        with mock.patch("commands.combat.movement.standard_roll",
                        side_effect=rolls) as rolled, \
             mock.patch("commands.combat.core_actions.CmdAttack.func") as hit, \
             mock.patch("commands.combat.movement.msg_room_identity"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            cmd.func()
        self.rolled = rolled
        self.attacked = hit
        return " ".join(self.said)


class TestFleeingIsNotAWayOffARoof(_FleeCase):
    def test_an_edge_is_not_an_escape_route(self):
        self.exit.db.is_edge = True
        out = self.flee()
        self.assertIs(self.runner.location, self.room1)
        self.assertNotIn("successfully flee", out)

    def test_and_they_are_told_they_are_stuck(self):
        self.exit.db.is_edge = True
        self.assertIn("pinned", self.flee())

    def test_a_gap_is_not_an_escape_route(self):
        self.exit.db.is_gap = True
        self.flee()
        self.assertIs(self.runner.location, self.room1)

    def test_an_exit_into_air_is_not_an_escape_route(self):
        """A regression pin: the sky-room filter predates #3583 and is
        now expressed through the shared predicate. It must still bite."""
        self.room2.db.is_sky_room = True
        self.flee()
        self.assertIs(self.runner.location, self.room1)

    def test_a_plain_exit_still_gets_them_out(self):
        """The control. Identical rolls, ordinary doorway."""
        out = self.flee()
        self.assertIs(self.runner.location, self.room2)
        self.assertIn("successfully flee", out)


class TestAFlierFleesOffTheEdge(_FleeCase):
    """The exemption, through the whole command."""

    def test_they_leave_by_the_edge(self):
        self.runner.db.stays_aloft = True
        self.exit.db.is_edge = True
        self.flee()
        self.assertIs(self.runner.location, self.room2)

    def test_and_are_told_they_got_away(self):
        self.runner.db.stays_aloft = True
        self.exit.db.is_edge = True
        self.assertIn("successfully flee", self.flee())


class TestFleeIsWiredToTheSharedContest(_FleeCase):
    """#3583 lifted the aim contest out of `CmdFlee` into the shared
    `break_aim_lock`. Flee's answer to a LOST contest is the opposite of
    the jump verbs' -- they go regardless, flee stops dead -- and both
    now call the same function, so this is the seam to watch.
    """

    def test_a_lost_contest_keeps_them_in_the_room(self):
        out = self.flee(win=False)
        self.assertIs(self.runner.location, self.room1)
        self.assertNotIn("successfully flee", out)

    def test_and_hands_the_aimer_a_free_shot(self):
        self.flee(win=False)
        self.attacked.assert_called_once()

    def test_and_says_who_kept_them(self):
        self.assertIn("pinned", self.flee(win=False))

    def test_a_won_contest_costs_no_free_shot(self):
        """The control."""
        self.flee(win=True)
        self.attacked.assert_not_called()

    def test_fleeing_is_not_a_bold_move_and_earns_no_bonus(self):
        """Decisive: 10 against 25 is a loss for a fleer and a WIN for a
        jumper, because only the jump verbs pass `JUMP_AWAY_BONUS`. If
        flee ever starts passing it, this is what notices."""
        self.flee(rolls=[(10, 0, 0), (25, 0, 0)])
        self.assertIs(self.runner.location, self.room1)
        self.attacked.assert_called_once()


class TestAStaleLockIsNoObstacleToFleeing(_FleeCase):
    """The aimer left the room and nothing cleaned up after them. An
    ndb lock outlives the situation that made it, so flee must release
    it rather than roll against somebody who is not there."""

    def setUp(self):
        super().setUp()
        self.aimer.location = self.room2

    def test_they_get_out(self):
        self.flee()
        self.assertIs(self.runner.location, self.room2)

    def test_without_rolling_for_it(self):
        self.flee()
        self.assertEqual(self.rolled.call_count, 0,
                         "rolled against a stale lock")

    def test_and_nobody_takes_a_shot_at_them(self):
        self.flee()
        self.attacked.assert_not_called()


# ---------------------------------------------------------------------
# 3. advance and charge
# ---------------------------------------------------------------------


class _CrossRoomCase(EvenniaTest):
    """The mover in room1, the quarry next door in room2, one exit
    between them. Nobody is in melee proximity, so the break-away
    contest (#3158) is not in play and the only contest is the
    crossing -- pinned to a WIN, so a mover who stays in the room
    stayed because the exit refused them.

    Shaped after ``test_you_cannot_stroll_out_of_a_fight.py``.
    """

    def setUp(self):
        super().setUp()
        self.mover = self.char1
        self.quarry = self.char2
        self.mover.location = self.room1
        self.quarry.location = self.room2
        self.mover.motorics = 20
        self.quarry.motorics = 3
        self.said = []
        self.mover.msg = lambda text=None, **kw: self.said.append(str(text))

    def handler(self):
        h = MagicMock()
        h.db.combatants = [
            {DB_CHAR: self.mover, DB_COMBAT_ACTION_TARGET: self.quarry},
            {DB_CHAR: self.quarry},
        ]
        h.db.managed_rooms = [self.room1, self.room2]
        h.get_grappling_obj.return_value = None
        h.get_target_obj.return_value = None
        return h

    def entry(self):
        return {DB_CHAR: self.mover, DB_COMBAT_ACTION_TARGET: self.quarry}

    def advance(self):
        from world.combat.movement_resolution import resolve_advance

        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi), \
             patch("commands.explosion_utils.check_rigged_grenade"), \
             patch("commands.explosion_utils.check_auto_defuse"):
            resolve_advance(self.handler(), self.mover, self.entry())
        return " ".join(self.said)

    def charge(self):
        """Charge rolls through the dice helpers rather than ``randint``,
        so the crossing and the break-away are patched separately -- the
        crossing pinned to succeed."""
        from world.combat.movement_resolution import resolve_charge

        h = self.handler()
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi), \
             patch("world.combat.movement_resolution.roll_with_disadvantage",
                   return_value=(99, 99, 99)), \
             patch("world.combat.movement_resolution.standard_roll",
                   return_value=(1, 1, 1)), \
             patch("commands.explosion_utils.check_rigged_grenade"), \
             patch("commands.explosion_utils.check_auto_defuse"):
            resolve_charge(h, self.mover, self.entry(), h.db.combatants)
        return " ".join(self.said)


class TestAdvanceIsRefusedAtTheEdge(_CrossRoomCase):
    def test_the_advancer_stays_on_the_roof(self):
        self.exit.db.is_edge = True
        self.advance()
        self.assertIs(self.mover.location, self.room1)

    def test_and_is_told_it_is_a_jump_not_an_advance(self):
        self.exit.db.is_edge = True
        out = self.advance()
        self.assertIn("edge", out)
        self.assertIn("jump", out)

    def test_a_gap_is_refused_the_same_way(self):
        self.exit.db.is_gap = True
        self.advance()
        self.assertIs(self.mover.location, self.room1)

    def test_an_advance_into_air_is_refused(self):
        self.room2.db.is_sky_room = True
        self.advance()
        self.assertIs(self.mover.location, self.room1)

    def test_a_plain_doorway_still_crosses(self):
        """The control: identical rolls, ordinary doorway."""
        self.advance()
        self.assertIs(self.mover.location, self.room2)

    def test_a_flier_advances_over_the_edge(self):
        self.mover.db.stays_aloft = True
        self.exit.db.is_edge = True
        self.advance()
        self.assertIs(self.mover.location, self.room2)


class TestChargeIsRefusedAtTheEdge(_CrossRoomCase):
    """The other cross-room door. Same predicate, its own message."""

    def test_the_charger_stays_on_the_roof(self):
        self.exit.db.is_edge = True
        self.charge()
        self.assertIs(self.mover.location, self.room1)

    def test_and_is_told_it_is_a_jump_not_a_charge(self):
        self.exit.db.is_edge = True
        out = self.charge()
        self.assertIn("edge", out)
        self.assertIn("jump", out)

    def test_a_gap_is_refused_the_same_way(self):
        self.exit.db.is_gap = True
        self.charge()
        self.assertIs(self.mover.location, self.room1)

    def test_a_charge_into_air_is_refused(self):
        self.room2.db.is_sky_room = True
        self.charge()
        self.assertIs(self.mover.location, self.room1)

    def test_a_plain_doorway_still_crosses(self):
        """The control: identical rolls, ordinary doorway."""
        self.charge()
        self.assertIs(self.mover.location, self.room2)

    def test_a_flier_charges_over_the_edge(self):
        self.mover.db.stays_aloft = True
        self.exit.db.is_edge = True
        self.charge()
        self.assertIs(self.mover.location, self.room2)


class TestARefusedAdvanceRollsNothingAtAll(_CrossRoomCase):
    """The refusal comes FIRST -- before the grapple drag-resist.

    A grappler advancing on someone next door makes their victim roll to
    break free. If the edge refusal were checked after that roll, an
    advance that was never going to happen would still spend the
    victim's contest, and a victim who won it would be freed by a move
    the room refused -- a grapple broken by a typo. The order is the
    fix, so the order is what is pinned.
    """

    def setUp(self):
        super().setUp()
        self.victim = self.obj1

    def advance_dragging(self):
        from world.combat.constants import DB_IS_YIELDING
        from world.combat.movement_resolution import resolve_advance

        h = self.handler()
        h.get_grappling_obj.return_value = self.victim
        entry = {DB_CHAR: self.mover, DB_COMBAT_ACTION_TARGET: self.quarry,
                 DB_IS_YIELDING: True}
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi) as rolled, \
             patch("world.combat.movement_resolution._break_grapple") as broke, \
             patch("commands.explosion_utils.check_rigged_grenade"), \
             patch("commands.explosion_utils.check_auto_defuse"):
            resolve_advance(h, self.mover, entry)
        return rolled, broke

    def test_an_advance_refused_at_the_edge_rolls_no_dice(self):
        self.exit.db.is_edge = True
        rolled, _ = self.advance_dragging()
        self.assertEqual(rolled.call_count, 0)

    def test_and_does_not_break_the_grapple(self):
        self.exit.db.is_edge = True
        _, broke = self.advance_dragging()
        broke.assert_not_called()

    def test_and_leaves_the_advancer_where_they_were(self):
        self.exit.db.is_edge = True
        self.advance_dragging()
        self.assertIs(self.mover.location, self.room1)

    def test_a_plain_doorway_does_roll_the_drag_contest(self):
        """The control. Without it the assertions above are satisfied by
        an advance that rolls nothing under any circumstances."""
        rolled, _ = self.advance_dragging()
        self.assertGreater(rolled.call_count, 0)


# ---------------------------------------------------------------------
# 4. one rule, not four copies of it
# ---------------------------------------------------------------------


def _watch_the_predicate():
    """Patch ``world.gravity.can_leave_by`` with a spy that DELEGATES.

    Every door imports it inside the function, so the name is resolved
    off the module at call time and one patch catches all of them.

    A spy rather than a source scan: `assertIn("can_leave_by", source)`
    passes on a module that only MENTIONS the predicate in a comment,
    which is exactly what `commands/combat/movement.py` does a few lines
    above its real call. That assertion cannot fail for the right
    reason, so it is not a test.
    """
    seen = []
    real = gravity.can_leave_by

    def watcher(mover, exit_obj):
        seen.append((mover, exit_obj))
        return real(mover, exit_obj)

    return mock.patch.object(gravity, "can_leave_by", watcher), seen


class TestFleeAsksTheOnePredicate(_FleeCase):
    def test_it_is_asked_about_the_exit(self):
        watch, seen = _watch_the_predicate()
        with watch:
            self.flee()
        self.assertIn((self.runner, self.exit), seen)


class TestAdvanceAndChargeAskTheOnePredicate(_CrossRoomCase):
    def test_advance_asks_about_the_exit(self):
        watch, seen = _watch_the_predicate()
        with watch:
            self.advance()
        self.assertIn((self.mover, self.exit), seen)

    def test_charge_asks_about_the_exit(self):
        watch, seen = _watch_the_predicate()
        with watch:
            self.charge()
        self.assertIn((self.mover, self.exit), seen)


class TestASoulNeverFleesOverAnEdge(EvenniaTest):
    """The fourth door, and the one most likely to be forgotten: souls
    run `flee` as a JOB STEP (``world/souls/jobs.py``), picking an exit
    themselves rather than through `CmdFlee`. A soul that walked off a
    roof every time it panicked would be the same defect wearing a
    different hat -- and unlike a player, it would do it all night.
    """

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.location = self.room1
        self.soul.db.soul_job = {"goal": "safety", "at": 0,
                                 "steps": [{"do": "flee"}]}
        self.soul.execute_cmd = MagicMock()

    def flee(self):
        from world.souls import jobs

        with patch.object(jobs, "fault") as faulted, \
             patch.object(jobs, "needs_mod"), \
             patch("world.souls.thoughts.add_thought"):
            jobs.step_job(self.soul)
        return faulted

    def test_a_roof_with_only_an_edge_leaves_the_soul_cornered(self):
        self.exit.db.is_edge = True
        faulted = self.flee()
        self.soul.execute_cmd.assert_not_called()
        self.assertIn("cornered", str(faulted.call_args))

    def test_a_gap_corners_it_too(self):
        self.exit.db.is_gap = True
        self.flee()
        self.soul.execute_cmd.assert_not_called()

    def test_a_plain_exit_is_still_a_way_out(self):
        """The control."""
        faulted = self.flee()
        self.soul.execute_cmd.assert_called_once_with(self.exit.key)
        faulted.assert_not_called()

    def test_a_flying_soul_takes_the_edge(self):
        self.soul.db.stays_aloft = True
        self.exit.db.is_edge = True
        self.flee()
        self.soul.execute_cmd.assert_called_once_with(self.exit.key)


# ---------------------------------------------------------------------
# 5. the walk door reads the flags just as strictly
# ---------------------------------------------------------------------


class TestWalkingReadsTheFlagsJustAsStrictly(EvenniaTest):
    """``Exit.at_traverse`` is where walking is refused. It used to read
    the flags truthily while `can_leave_by` read them strictly, so an
    exit flagged ``is_edge = 1`` refused a walker and allowed a fleer --
    two doors disagreeing about what an edge IS, which is worse than
    either answer (#3583).
    """

    def setUp(self):
        super().setUp()
        self.walker = self.char1
        self.walker.location = self.room1
        self.said = []
        self.walker.msg = lambda text=None, **kw: self.said.append(str(text))

    def walk(self):
        self.exit.at_traverse(self.walker, self.room2)
        return self.walker.location

    def test_an_edge_refuses_a_walker(self):
        self.exit.db.is_edge = True
        self.assertIs(self.walk(), self.room1)
        self.assertIn("it's an edge", " ".join(self.said))

    def test_a_gap_refuses_a_walker(self):
        self.exit.db.is_gap = True
        self.assertIs(self.walk(), self.room1)

    def test_an_unspecced_edge_flag_does_not(self):
        """``1`` is not ``True`` here either."""
        self.exit.db.is_edge = 1
        self.assertIs(self.walk(), self.room2)

    def test_an_unspecced_gap_flag_does_not(self):
        self.exit.db.is_gap = 1
        self.assertIs(self.walk(), self.room2)

    def test_a_plain_exit_is_walkable(self):
        """The control."""
        self.assertIs(self.walk(), self.room2)
