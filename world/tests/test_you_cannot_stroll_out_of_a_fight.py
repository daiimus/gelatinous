"""Leaving a room mid-fight costs a contest against whoever is holding
you — and holding means ATTACKING you, not merely standing close.

The game documents three ways out of melee, and they did not cost the
same thing:

* `retreat` — breaks melee but **stays in the room**; opposed roll
  against "those in proximity".
* `flee` — leaves the room; aim-break contest, cannot flee toward a
  ranged threat, once per round.
* cross-room `advance` / `charge` — leaves the room for a single roll
  against **the person being closed on**, who is by definition in the
  room you are going *to*.

So the cheapest way out of a bad melee was to advance on someone
harmless next door. That was true before proximity was cleared on these
paths (#2490); clearing it only made the exit tidy instead of leaving
phantom cross-room melee links behind.

Cross-room advance and charge now pay the same contest `retreat`
charges — highest motorics among those holding you.

**Intent, not just range.** Someone standing in melee proximity who is
fighting a third party has no claim on where you go. What pins you is
that they are attacking *you*, which lives on the combat entry as their
target. The same test already gates the grapple-drag path a few lines
up, where a grappler is refused a cross-room drag because "others are
targeting you".

A grappled victim is excluded: you are holding them, they are not
holding you — the carve-out `resolve_retreat` already makes.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import DB_CHAR, DB_COMBAT_ACTION_TARGET
from world.combat.movement_resolution import (
    resolve_advance, resolve_charge,
)
from world.combat.proximity import establish_proximity


class _AdvanceCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.a = self.char1              # the one trying to leave
        self.b = self.char2              # in the room with A
        self.a.location = self.room1
        self.b.location = self.room1
        self.c = create_object("typeclasses.characters.Character",
                               key="Cee", location=self.room2)   # next door
        self.a.motorics = 3
        self.b.motorics = 20
        self.c.motorics = 3
        self.exit = create_object("typeclasses.exits.Exit", key="east",
                                  location=self.room1,
                                  destination=self.room2)

    def handler(self, b_targets=None):
        """`b_targets` is who B is attacking — the intent axis."""
        entries = [
            {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c},
            {DB_CHAR: self.b},
            {DB_CHAR: self.c},
        ]
        h = MagicMock()
        h.db.combatants = entries
        h.db.managed_rooms = [self.room1, self.room2]
        h.get_grappling_obj.return_value = None
        h.get_target_obj.side_effect = lambda e: (
            b_targets if e.get(DB_CHAR) is self.b else None)
        return h

    def advance(self, handler, rolls):
        """`rolls` is consumed in order by each opposed roll."""
        seq = list(rolls)
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: seq.pop(0)):
            resolve_advance(handler, self.a, entry)
        return seq


class TestSomeoneAttackingYouCanHoldYou(_AdvanceCase):
    def setUp(self):
        super().setUp()
        establish_proximity(self.a, self.b)

    def test_a_failed_break_away_keeps_you_in_the_room(self):
        handler = self.handler(b_targets=self.a)
        self.advance(handler, [1, 20])          # A loses the break-away
        self.assertIs(self.a.location, self.room1)

    def test_it_says_who_held_you(self):
        handler = self.handler(b_targets=self.a)
        said = []
        self.a.msg = lambda text=None, **kw: said.append(str(text))
        self.advance(handler, [1, 20])
        self.assertIn("engaged", "\n".join(said))

    def test_a_successful_break_away_lets_you_go(self):
        handler = self.handler(b_targets=self.a)
        self.advance(handler, [20, 1, 20, 1])   # break away, then cross
        self.assertIs(self.a.location, self.room2)

    def test_a_holder_stops_a_crossing_that_would_otherwise_succeed(self):
        """The decisive one.

        A fixed roll SEQUENCE cannot distinguish the two versions here:
        the unfixed code reads rolls 1-2 as the crossing, the fixed code
        reads them as the break-away, and any sequence that makes one
        fail makes the other fail too. So this pins the roll to each
        character's own maximum instead — A(3) beats C(2) at the
        crossing every time, and only B(20) can stop them.

        Unfixed: A crosses. Fixed: B holds them.
        """
        self.c.motorics = 2
        handler = self.handler(b_targets=self.a)
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi):
            resolve_advance(handler, self.a, entry)
        self.assertIs(self.a.location, self.room1,
                      "walked out of a fight somebody had hold of")

    def test_and_the_same_crossing_succeeds_when_nobody_holds_them(self):
        """The control: identical rolls, B simply is not on A."""
        self.c.motorics = 2
        handler = self.handler(b_targets=self.c)
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi):
            resolve_advance(handler, self.a, entry)
        self.assertIs(self.a.location, self.room2)

    def test_the_break_away_comes_before_the_crossing_roll(self):
        """A failed break-away must not spend the crossing roll."""
        handler = self.handler(b_targets=self.a)
        left = self.advance(handler, [1, 20, 999, 999])
        self.assertEqual(left, [999, 999], "the crossing roll was rolled")


class TestIntentNotJustRange(_AdvanceCase):
    """The distinction that matters: proximity alone is not a hold."""

    def test_someone_fighting_a_third_party_does_not_hold_you(self):
        establish_proximity(self.a, self.b)
        handler = self.handler(b_targets=self.c)     # B is on C, not A
        self.advance(handler, [20, 1])               # crossing roll only
        self.assertIs(self.a.location, self.room2)

    def test_someone_targeting_nobody_does_not_hold_you(self):
        establish_proximity(self.a, self.b)
        handler = self.handler(b_targets=None)
        self.advance(handler, [20, 1])
        self.assertIs(self.a.location, self.room2)

    def test_someone_attacking_you_from_across_the_room_does_not(self):
        """Intent without range is not a hold either — no proximity."""
        handler = self.handler(b_targets=self.a)     # no establish_proximity
        self.advance(handler, [20, 1])
        self.assertIs(self.a.location, self.room2)

    def test_both_together_do(self):
        establish_proximity(self.a, self.b)
        handler = self.handler(b_targets=self.a)
        self.advance(handler, [1, 20])
        self.assertIs(self.a.location, self.room1)


class TestTheContestUsesTheRightNumbers(_AdvanceCase):
    def test_it_rolls_against_the_holder_not_the_target(self):
        establish_proximity(self.a, self.b)
        handler = self.handler(b_targets=self.a)
        maxima = []
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}

        def spy(lo, hi):
            maxima.append(hi)
            return 1        # everyone rolls 1 → A loses the tie
        with patch("world.combat.movement_resolution.randint", spy):
            resolve_advance(handler, self.a, entry)
        # A(3) vs B(20) — the person holding them, not C(3) next door.
        self.assertEqual(maxima, [3, 20])

    def test_ties_favour_the_person_holding_on(self):
        establish_proximity(self.a, self.b)
        handler = self.handler(b_targets=self.a)
        self.advance(handler, [5, 5])
        self.assertIs(self.a.location, self.room1)


class TestNobodyHoldingYouChangesNothing(_AdvanceCase):
    def test_an_unengaged_advance_still_costs_one_roll(self):
        handler = self.handler(b_targets=None)
        maxima = []
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}

        def spy(lo, hi):
            maxima.append(hi)
            return hi if len(maxima) == 1 else lo
        with patch("world.combat.movement_resolution.randint", spy):
            resolve_advance(handler, self.a, entry)
        self.assertEqual(maxima, [3, 3])     # A vs C only
        self.assertIs(self.a.location, self.room2)


class TestChargeIsTheSameDoor(_AdvanceCase):
    """Charge is the other cross-room exit and had the identical gap.

    Its own crossing roll goes through `roll_with_disadvantage` /
    `standard_roll` rather than `randint`, so the two rolls are patched
    separately here: `randint` drives the break-away, the dice helpers
    drive the crossing. The crossing is pinned to SUCCEED in both tests,
    so the only thing that can keep A in the room is the break-away.
    """

    def charge(self, handler):
        entry = {DB_CHAR: self.a, DB_COMBAT_ACTION_TARGET: self.c}
        with patch("world.combat.movement_resolution.randint",
                   side_effect=lambda lo, hi: hi), \
             patch("world.combat.movement_resolution.roll_with_disadvantage",
                   return_value=(99, 99, 99)), \
             patch("world.combat.movement_resolution.standard_roll",
                   return_value=(1, 1, 1)):
            resolve_charge(handler, self.a, entry, handler.db.combatants)

    def test_a_holder_stops_a_charge_that_would_otherwise_land(self):
        establish_proximity(self.a, self.b)
        self.charge(self.handler(b_targets=self.a))
        self.assertIs(self.a.location, self.room1,
                      "charged out of a fight somebody had hold of")

    def test_and_the_same_charge_lands_when_nobody_holds_them(self):
        """The control: identical rolls, B simply is not on A."""
        establish_proximity(self.a, self.b)
        self.charge(self.handler(b_targets=self.c))
        self.assertIs(self.a.location, self.room2)
