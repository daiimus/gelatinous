"""The insurance does not clone the living (#2178).

Two independent holes let `resleave` build a copy of somebody who was
standing right there:

1. `_slot_held` asked a souled keeper for `db.soul_post == room`. A
   keeper whose assignment was never recorded could therefore never
   hold their slot — the Rook sat in his own booth while the sweep
   read the chair as dark.

2. Nothing checked that the keeper was actually dead before paying
   out. That made the failure self-sustaining: the original stays
   alive, so it is never archived to Limbo, so `_archived_keeper`
   finds nobody next sweep and builds *another* copy.

Live evidence when this was found: three Petras, two Marta Okoyes, two
Nikolai Kasparovs, and zero NPCs in Limbo.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import engine, posts


class _Slot(dict):
    pass


class TestASoulInItsChairHoldsIt(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.post = self.obj1
        self.post.location = self.room1
        self.keeper = self.char2
        self.keeper.tags.add(engine.SOUL_TAG[0],
                             category=engine.SOUL_TAG[1])
        self.keeper.location = self.room1

    def _held(self, shift="day"):
        return posts._slot_held(
            self.post, shift, {"keeper": self.keeper, "vacant_since": None})

    def test_unassigned_soul_holds_by_presence(self):
        """The Rook case: in the room, no soul_post recorded."""
        self.keeper.db.soul_post = None
        self.assertTrue(self._held())

    def test_unassigned_soul_elsewhere_does_not_hold(self):
        self.keeper.db.soul_post = None
        self.keeper.location = self.room2
        self.assertFalse(self._held())

    def test_an_assignment_still_wins_when_present(self):
        self.keeper.db.soul_post = self.room1
        self.keeper.db.soul_schedule = "day"
        self.assertTrue(self._held("day"))

    def test_reassignment_still_frees_the_slot(self):
        """The behaviour the soul_post check exists for must survive:
        a soul posted elsewhere does not hold this slot, even standing
        in the room."""
        self.keeper.db.soul_post = self.room2
        self.keeper.db.soul_schedule = "day"
        self.keeper.location = self.room1
        self.assertFalse(self._held("day"))

    def test_wrong_shift_still_frees_the_slot(self):
        self.keeper.db.soul_post = self.room1
        self.keeper.db.soul_schedule = "night"
        self.assertFalse(self._held("day"))


class TestTheInsuranceRefusesTheLiving(EvenniaCommandTest):
    def test_a_living_keeper_is_never_resleaved(self):
        post = self.obj1
        post.location = self.room1
        post.db.post_blueprints = {"day": "doctor_marta"}
        post.db.register = 10 ** 9          # affordability is not the gate
        keeper = self.char2
        keeper.db.is_dead = None
        slot = {"keeper": keeper, "vacant_since": 1.0}
        self.assertFalse(
            posts._try_resleave(post, self.room1, "day", slot, 10 ** 6))
