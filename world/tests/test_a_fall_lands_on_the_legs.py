"""What a landing costs (#3579).

Damage is charged ONCE, at the bottom, for the cells actually passed --
not per cell, not at takeoff, and never by the verb. The defects:

* **Skill turns a fall into a SHORTER fall.** Owner ruling
  (2026-09-16): a made landing roll subtracts
  ``FALL_LANDING_ABSORBED_CELLS`` storeys rather than dividing a
  number, so a two-storey drop landed well is free and a twelve-storey
  one is not survivable by skill alone. A multiplier would have made
  both wrong in opposite directions.
* **Only an EDGE descent rolls.** A body that was shoved, dropped,
  thrown or simply found hanging never chose to jump and has nothing to
  land well from; ``record["roll"]`` is what carries the difference
  down the column.
* **Things do not take damage.** A falling shiv lands and is heard
  landing. ``apply_fall_damage`` must not be reached for it at all.
* **The direct drop is not a column** (clearing an oversailing plate
  onto the street): one storey, no roll, no traversal, and it keeps the
  literal "land safely" line the nine street-destination edges have
  always printed.

``standard_roll`` is patched on ``world.combat.utils`` -- ``_land``
imports it at CALL time from there, so patching the name inside
``world.gravity`` would patch nothing that exists.
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.combat.constants import (
    FALL_DAMAGE_PER_STORY,
    FALL_LANDING_ABSORBED_CELLS,
)


def _inline(mocked):
    mocked.side_effect = lambda _seconds, callback, *a, **kw: callback(*a, **kw)
    return mocked


class _LandingCase(EvenniaTest):
    """A two-cell column: roof -> air1 -> air2 -> street."""

    CELLS = 2

    def setUp(self):
        super().setUp()
        self.roof, self.street = self.room1, self.room2
        self.cells = [
            create_object("typeclasses.rooms.SkyRoom", key="In the Air")
            for _ in range(self.CELLS)
        ]
        for index, cell in enumerate(self.cells):
            below = (self.cells[index + 1] if index + 1 < len(self.cells)
                     else self.street)
            create_object("typeclasses.exits.Exit", key="down",
                          location=cell, destination=below, aliases=["d"])
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

    def hp(self, organ):
        return self.char1.medical_state.organs[organ].current_hp

    def leg_damage(self):
        """Total hp missing anywhere on the body."""
        return sum(o.max_hp - o.current_hp
                   for o in self.char1.medical_state.organs.values())

    def fall(self, *, roll=False, rolled=None, mover=None, **kwargs):
        mover = mover or self.char1
        mover.location = self.cells[0]
        with ExitStack() as stack:
            delayed = stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(
                mock.patch.object(gravity, "msg_room_identity"))
            if rolled is not None:
                stack.enter_context(mock.patch(
                    "world.combat.utils.standard_roll",
                    return_value=(rolled, rolled, rolled)))
            _inline(delayed)
            gravity.start_fall(mover, roll=roll, **kwargs)
        return delayed

    def said_text(self):
        return " ".join(self.said)


class TestAnUnrolledTwoStoreyFall(_LandingCase):
    """Nobody chose this one -- shoved, dropped, or simply found in the
    air. No roll, full price."""

    def test_the_damage_lands_in_a_foot(self):
        self.fall()
        self.assertLess(self.hp("right_metatarsals"), 20)

    def test_it_costs_exactly_two_storeys(self):
        self.fall()
        self.assertEqual(self.leg_damage(), FALL_DAMAGE_PER_STORY * 2)

    def test_the_chest_is_untouched(self):
        before = {o.name: o.current_hp
                  for o in self.char1.medical_state.organs.values()
                  if o.container == "chest"}
        self.fall()
        for name, hp in before.items():
            self.assertEqual(self.hp(name), hp)

    def test_the_prose_is_a_crash_not_a_landing(self):
        self.fall()
        self.assertIn("crash hard", self.said_text())

    def test_no_roll_is_made_at_all(self):
        with mock.patch("world.combat.utils.standard_roll") as roll:
            self.fall()
        roll.assert_not_called()


class TestAMadeLandingRoll(_LandingCase):
    """FALL_LANDING_ABSORBED_CELLS is 2, so a made roll makes a
    two-storey drop free."""

    def test_two_absorbed_storeys_leave_nothing_to_pay(self):
        self.assertEqual(FALL_LANDING_ABSORBED_CELLS, 2,
                         "premise: this fixture is sized on the constant")
        self.fall(roll=True, rolled=999)
        self.assertEqual(self.leg_damage(), 0)

    def test_both_feet_are_whole(self):
        self.fall(roll=True, rolled=999)
        self.assertEqual(self.hp("right_metatarsals"), 20)
        self.assertEqual(self.hp("left_metatarsals"), 20)

    def test_the_prose_says_they_walked_it_off(self):
        self.fall(roll=True, rolled=999)
        self.assertIn("walk it off", self.said_text())

    def test_a_failed_roll_charges_the_whole_fall(self):
        self.fall(roll=True, rolled=1)
        self.assertEqual(self.leg_damage(), FALL_DAMAGE_PER_STORY * 2)

    def test_and_says_so(self):
        self.fall(roll=True, rolled=1)
        self.assertIn("crash hard", self.said_text())

    def test_the_roll_is_against_edge_difficulty_plus_altitude(self):
        from world.combat.constants import FALL_LANDING_DIFFICULTY_PER_CELL
        with mock.patch("world.combat.utils.standard_roll",
                        return_value=(5, 5, 5)) as roll:
            self.fall(roll=True, edge_difficulty=11)
        roll.assert_called_once()
        # 11 + 2 per cell x 2 cells = 15; a 5 misses, so full price.
        self.assertEqual(self.leg_damage(), FALL_DAMAGE_PER_STORY * 2)
        self.assertEqual(11 + FALL_LANDING_DIFFICULTY_PER_CELL * 2, 15)

    def test_a_roll_that_exactly_meets_the_difficulty_makes_it(self):
        self.fall(roll=True, rolled=12, edge_difficulty=8)
        self.assertEqual(self.leg_damage(), 0)


class TestALongerFallIsStillExpensiveWhenLandedWell(_LandingCase):
    CELLS = 6

    def test_skill_shortens_the_fall_it_does_not_divide_it(self):
        self.fall(roll=True, rolled=999)
        self.assertEqual(
            self.leg_damage(),
            FALL_DAMAGE_PER_STORY * (6 - FALL_LANDING_ABSORBED_CELLS))

    def test_the_prose_still_admits_the_cost(self):
        self.fall(roll=True, rolled=999)
        self.assertIn("land well", self.said_text())


class TestAThingIsNotHurtByLanding(_LandingCase):
    def test_no_fall_damage_is_applied_to_an_item(self):
        item = create_object("typeclasses.items.Item", key="a steel shiv",
                             location=self.roof)
        with mock.patch.object(gravity, "apply_fall_damage") as damage:
            self.fall(mover=item)
        damage.assert_not_called()
        self.assertIs(item.location, self.street)

    def test_a_body_in_the_same_column_IS_hurt(self):
        """Control: the pin above measures the item branch, not a
        fixture that never lands anything."""
        with mock.patch.object(gravity, "apply_fall_damage",
                               return_value=(0, False)) as damage:
            self.fall()
        damage.assert_called_once()


class TestTheDirectDropOffAnEdge(EvenniaTest):
    """``jump off <dir> edge`` where the destination is NOT air: one
    storey, no roll, no column -- and the literal line the colony's
    street-destination edges have always printed."""

    def setUp(self):
        super().setUp()
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        self.exit.key = "south"
        self.exit.db.is_edge = True
        self.exit.destination.db.is_sky_room = False

    def descend(self):
        from commands.combat.jump import CmdJump
        cmd = CmdJump()
        cmd.caller = self.char1
        cmd.direction = "south"
        with mock.patch("commands.combat.jump.clear_aim_state"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch("commands.combat.jump.msg_room_identity"), \
             mock.patch.object(type(cmd), "find_edge_exit",
                               return_value=self.exit):
            cmd.handle_edge_descent()
        return " ".join(self.said)

    def test_it_lands_you_in_the_room_below(self):
        self.descend()
        self.assertIs(self.char1.location, self.room2)

    def test_it_still_says_land_safely(self):
        self.assertIn("land safely", self.descend())

    def test_it_costs_exactly_one_storey(self):
        self.descend()
        missing = sum(o.max_hp - o.current_hp
                      for o in self.char1.medical_state.organs.values())
        self.assertEqual(missing, FALL_DAMAGE_PER_STORY)

    def test_the_cost_lands_in_a_foot(self):
        self.descend()
        self.assertLess(
            self.char1.medical_state.organs["right_metatarsals"].current_hp,
            20)

    def hurt(self):
        return sum(o.max_hp - o.current_hp
                   for o in self.char1.medical_state.organs.values())

    def test_a_clumsy_body_pays_exactly_one_storey(self):
        """A direct drop is one storey, flat.

        The earlier version of this pin patched ``standard_roll`` and
        asserted it was never called -- which the branch satisfies by
        never rolling, so the patch never applied and the test could not
        have failed. Drive the INPUT a roll would read instead. At
        Motorics 1 every roll misses."""
        self.char1.motorics = 1
        self.descend()
        self.assertEqual(self.hurt(), FALL_DAMAGE_PER_STORY)

    def test_an_athletic_body_pays_exactly_one_storey_too(self):
        """At Motorics 150 every roll makes, and a made landing roll
        absorbs FALL_LANDING_ABSORBED_CELLS storeys -- which on a
        one-storey drop would be the whole bill. Same 5 either way: the
        number is not roll-dependent."""
        self.char1.motorics = 150
        self.descend()
        self.assertEqual(self.hurt(), FALL_DAMAGE_PER_STORY)

    def test_the_column_by_contrast_IS_roll_dependent(self):
        """Control: the same two Motorics values DO move the number when
        the fall goes through a column, so the instrument can tell the
        two regimes apart and the pair above is measuring something."""
        air = create_object("typeclasses.rooms.SkyRoom", key="In the Air")
        below = create_object("typeclasses.rooms.SkyRoom", key="In the Air")
        create_object("typeclasses.exits.Exit", key="down", location=air,
                      destination=below, aliases=["d"])
        create_object("typeclasses.exits.Exit", key="down", location=below,
                      destination=self.room2, aliases=["d"])
        self.char1.location = air
        self.char1.motorics = 150
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            delayed.side_effect = (
                lambda _s, callback, *a, **kw: callback(*a, **kw))
            gravity.start_fall(self.char1, roll=True)
        self.assertEqual(self.hurt(), 0)

    def test_no_fall_record_is_written(self):
        """A direct drop is over the moment it happens."""
        self.descend()
        self.assertFalse(self.char1.db.falling)
