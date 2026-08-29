"""Two souls, one shift (#2371).

The population merge put forty new unemployed souls into a colony with
twelve dark shifts, and the job market has no reservation: the same slot
is offered to whoever is nearest, repeatedly, until somebody claims it.
That was survivable while the claim verified the slot. It did not.

It checked `post.db.post_keeper` — the legacy SINGLE mirror, which
cannot tell one shift from another — and only refused if that person was
standing in the room. Souls leave their post constantly, because a
band-1 need outranks duty. So a keeper who stepped out to eat was
quietly displaced, and both souls went on believing they held the job:

    the backlit bar   day  claimed by Jerry, then overwritten by Camille
    Maxwell clinic    swing claimed by Candice, then by Cindy
"""
from types import SimpleNamespace
from unittest import mock

from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import engine, posts as postsmod


class TestSlotContention(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        # A post keeper is a SOUL — the invariant from #2362. `_slot_held`
        # reads an unsouled keeper as holding nothing, so a fixture that
        # skips the tag tests the wrong thing entirely.
        for char in (self.char1, self.char2):
            char.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])

    def _post(self, keeper=None, shift="day"):
        slots = {shift: {"keeper": keeper, "vacant_since": None}}
        return SimpleNamespace(
            db=SimpleNamespace(post_slots=slots, post_keeper=keeper),
            location=self.room1)

    def test_a_free_slot_is_free(self):
        post = self._post(keeper=None)
        self.assertFalse(postsmod.slot_is_taken(post, "day", by=self.char1))

    def test_a_held_slot_is_taken(self):
        self.char2.db.soul_post = self.room1
        self.char2.db.soul_schedule = "day"
        post = self._post(keeper=self.char2)
        self.assertTrue(postsmod.slot_is_taken(post, "day", by=self.char1))

    def test_a_keeper_who_stepped_out_still_holds_it(self):
        """THE bug. Off eating is not off the job — and the old guard
        required physical presence, so lunch cost people their shift."""
        self.char2.db.soul_post = self.room1
        self.char2.db.soul_schedule = "day"
        self.char2.location = self.room2          # gone to eat
        post = self._post(keeper=self.char2)
        self.assertTrue(postsmod.slot_is_taken(post, "day", by=self.char1))

    def test_another_shift_is_not_this_one(self):
        """The legacy mirror could not express this: a post has three
        shifts, and holding one says nothing about the others."""
        self.char2.db.soul_post = self.room1
        self.char2.db.soul_schedule = "day"
        post = SimpleNamespace(
            db=SimpleNamespace(
                post_slots={"day": {"keeper": self.char2},
                            "night": {"keeper": None}},
                post_keeper=self.char2),
            location=self.room1)
        self.assertTrue(postsmod.slot_is_taken(post, "day", by=self.char1))
        self.assertFalse(postsmod.slot_is_taken(post, "night", by=self.char1))

    def test_re_claiming_your_own_shift_is_allowed(self):
        self.char1.db.soul_post = self.room1
        self.char1.db.soul_schedule = "day"
        post = self._post(keeper=self.char1)
        self.assertFalse(postsmod.slot_is_taken(post, "day", by=self.char1))

    def test_a_keeper_who_quit_frees_it(self):
        """`_slot_held` is the shared reading: reassigned means gone."""
        self.char2.db.soul_post = self.room2      # works somewhere else now
        self.char2.db.soul_schedule = "day"
        post = self._post(keeper=self.char2)
        self.assertFalse(postsmod.slot_is_taken(post, "day", by=self.char1))
