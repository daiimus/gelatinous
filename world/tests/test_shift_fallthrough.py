"""A shift nobody owns can still be staffed (#2192, #3565, #3667).

`sweep()` took the return branch for every shift of a blueprinted post.
`_try_resleave` bailed when that shift had no blueprint, hit
`continue`, and the successor path below was never reached — so those
slots could not be filled by ANY mechanism. Since #3667 the return
answers RESLEEVED, HOLD or SUCCESSOR, and only HOLD keeps a stranger
out: a dead keeper with no sleeve policy is not coming back, and the
shift stops carrying their name.

Live cost when found: 14 of 19 dark slots permanently dark, including
every non-day shift at both clinics and dispatch. That is the
structural reason the colony had no medical cover at night.

A blueprint names a PERSON, and a person works one shift. So a shift
is "owned" only when its blueprint's namesake is not already alive
somewhere — otherwise it is an ordinary vacancy and a stranger may
claim it.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import posts


class TestOwnershipIsPerShift(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.post = self.obj1
        self.post.location = self.room1
        self.post.db.post_policy = "successor"
        self.post.db.post_delay = 0
        # sweep() finds posts BY TAG — an untagged fixture is invisible
        self.post.tags.add(posts.POST_TAG[0], category=posts.POST_TAG[1])

    def _sweep_with_candidate(self, candidate, outcome=None):
        with mock.patch.object(posts, "_eligible_candidates",
                               return_value=[candidate]), \
             mock.patch.object(posts, "_offer") as offer, \
             mock.patch.object(posts, "_try_resleave",
                               return_value=outcome) as returned:
            posts.sweep(now=10 ** 7)
        offer.returned = returned
        return offer

    def test_an_unowned_shift_gets_a_successor(self):
        """The bug: night has no blueprint, so it was skipped forever."""
        self.post.db.post_blueprints = {"day": "merchant_ezra"}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2)
        self.assertTrue(offer.called,
                        "an unowned shift was never offered to anyone")

    def test_a_shift_whose_owner_is_alive_is_not_theirs_to_wait_for(self):
        """Ezra's legacy blueprint covered all three shifts. He can only
        work one, so the others are ordinary vacancies."""
        self.char1.db.blueprint_key = "merchant_ezra"
        self.char1.db.is_npc = True
        self.char1.db.is_dead = None
        self.char1.location = self.room1
        self.post.db.post_blueprints = {"night": "merchant_ezra"}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2)
        self.assertTrue(offer.called)
        offer.returned.assert_not_called()      # not owned: no return tried

    def test_an_owned_shift_is_offered_once_its_person_is_not_coming_back(self):
        """No sleeve policy in the dead keeper's name (#3667): the shift
        is nobody's now. Before, a return that could never succeed hit
        `continue` and the slot stayed dark forever (#3565)."""
        self.post.db.post_blueprints = {"night": "dj_rook"}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2, outcome=posts.SUCCESSOR)
        self.assertTrue(offer.called, "an unreturnable shift stayed dark")
        self.assertNotIn("night", self.post.db.post_blueprints or {},
                         "the shift still carries the dead keeper's name")

    def test_an_owned_shift_waits_while_its_person_may_yet_return(self):
        """HOLD: the keeper is alive elsewhere, or still on the table."""
        self.post.db.post_blueprints = {"night": "dj_rook"}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2, outcome=posts.HOLD)
        self.assertFalse(offer.called, "hired a stranger into somebody's own shift")
        self.assertEqual(self.post.db.post_blueprints, {"night": "dj_rook"})

    def test_a_returned_keeper_ends_the_sweep(self):
        self.post.db.post_blueprints = {"night": "dj_rook"}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2, outcome=posts.RESLEEVED)
        self.assertFalse(offer.called)
        self.assertEqual(self.post.db.post_blueprints, {"night": "dj_rook"})

    def test_no_policy_means_the_slot_stays_dark(self):
        """`None` is the owner's undecided case, not an invitation."""
        self.post.db.post_policy = None
        self.post.db.post_blueprints = {}
        self.post.db.post_slots = {
            "night": {"keeper": None, "vacant_since": 1.0}}
        offer = self._sweep_with_candidate(self.char2)
        self.assertFalse(offer.called)
