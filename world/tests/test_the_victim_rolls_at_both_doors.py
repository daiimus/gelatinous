"""A grappled victim gets a resistance roll on BOTH drag doors.

Regression pin for #2602. There are two ways to drag a grappled victim
through an exit, and only one gave the victim a contest.

* the WALK door (`typeclasses/exits.py`) rolls victim grit against
  grappler grit; a win breaks the grapple and cancels the move;
* the ADVANCE door (`world/combat/movement_resolution.py`) rolled
  advancer motorics against the ADVANCE TARGET's -- the grappled
  victim's stats appeared nowhere in the function.

So a victim who would break free by being walked through a doorway was
carried along by `advance` with no contest at all. In a fight, `advance`
is the door a grappler actually uses: the victim's one defence existed
only on the door least likely to be taken.

NOT FIXED HERE, deliberately: the two "targeted by others" predicates
have also drifted, and the advance door's is the more permissive
(it excludes the advance target, and requires the same room). Making
them agree is a combat-balance change either way, so it is recorded on
the issue for the owner rather than decided here.
"""

import inspect
from unittest import TestCase

import world.combat.movement_resolution as advance_door
import typeclasses.exits as walk_door


class TestTheVictimRollsAtBothDoors(TestCase):

    def test_the_advance_door_reads_the_victim_grit(self):
        src = inspect.getsource(advance_door)
        self.assertIn("victim_grit", src)
        self.assertIn("grappled_victim", src)

    def test_both_doors_use_the_same_contest(self):
        """Grit against grit — not motorics, which is the advance
        door's own separate charge roll."""
        for mod in (advance_door, walk_door):
            with self.subTest(mod.__name__):
                src = inspect.getsource(mod)
                self.assertIn("victim_grit", src)
                self.assertIn("grappler_grit", src)

    def test_a_successful_resist_breaks_the_grapple(self):
        """The walk door's consequence, matched."""
        src = inspect.getsource(advance_door)
        self.assertIn("_break_grapple", src)

    def test_the_break_clears_both_sides(self):
        """Half a grapple is worse than none — the next tick would read
        two different answers to 'is this a grapple'.

        Bound off the module: on an unfixed tree the helper does not
        exist and `inspect.getsource` raises, which reads like a broken
        harness rather than a missing grapple-break.
        """
        helper = getattr(advance_door, "_break_grapple", None)
        self.assertIsNotNone(
            helper, "the advance door has no grapple-break, so a "
                    "successful resist leaves the pair half-grappled")
        src = inspect.getsource(helper)
        self.assertIn("DB_GRAPPLING_DBREF", src)
        self.assertIn("DB_GRAPPLED_BY_DBREF", src)

    def test_the_advance_charge_roll_is_still_motorics(self):
        """The control — the drag contest is additional to the charge
        contest, not a replacement for it."""
        src = inspect.getsource(advance_door)
        self.assertIn("target_motorics", src)
