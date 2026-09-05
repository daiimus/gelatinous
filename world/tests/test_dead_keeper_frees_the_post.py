"""A dead keeper does not hold their post forever (#2706).

Three defects converged to disable succession for all 24 blueprinted
keepers:

1. Essential personnel are ARCHIVED to Limbo rather than deleted
   (#2128) -- deliberate and good, since the insurance restores the
   person instead of rebuilding a copy. But it leaves the corpse with a
   truthy `pk`.
2. `_slot_held` had no aliveness test. Its three checks -- `pk`, the
   soul tag (`desoul()` has no callers), and `soul_post` (never cleared
   on death) -- are all unchanged by dying.
3. The resleeve guard read `keeper.db.is_dead`, an attribute row ZERO
   objects in the database carry, so it was always True and the resleeve
   was unreachable.

The slot read HELD forever: no vacancy stamp, no `post_vacant` signal,
no succession, no resleeve, and the venue reporting closed with nothing
to say why.

Owner ruling 2026-09-05: a job is not left empty, consistently across
posts.
"""
from types import SimpleNamespace
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import posts as postsmod


class TestTheAlivenessPredicate(EvenniaCommandTest):
    """`_is_dead` centralises the check the module got wrong in three
    separate places."""

    def test_a_living_character_is_not_dead(self):
        self.assertFalse(postsmod._is_dead(self.char1))

    def test_a_dead_character_is_dead(self):
        with mock.patch.object(type(self.char1), "is_dead",
                               return_value=True):
            self.assertTrue(postsmod._is_dead(self.char1))

    def test_the_phantom_attribute_is_not_consulted(self):
        """The old spelling. Writing it must have no effect, or the bug
        is merely relocated."""
        self.char1.db.is_dead = True
        self.assertFalse(postsmod._is_dead(self.char1))

    def test_something_with_no_medical_system_reads_alive(self):
        """Fails ALIVE by design: reading a fixture or a non-character
        as a corpse would vacate posts that are actually staffed."""
        self.assertFalse(postsmod._is_dead(SimpleNamespace()))
        self.assertFalse(postsmod._is_dead(None))

    def test_a_body_that_raises_reads_alive(self):
        boom = mock.MagicMock()
        boom.is_dead.side_effect = RuntimeError("no medical state")
        self.assertFalse(postsmod._is_dead(boom))


class TestASlotIsNotHeldByACorpse(EvenniaCommandTest):
    def _slot(self, keeper):
        return {"keeper": keeper, "vacant_since": None}

    def _post(self):
        post = mock.MagicMock()
        post.db = SimpleNamespace(post_slots={}, post_policy="resleave")
        return post

    def _souled_keeper(self):
        """A keeper that the UNFIXED `_slot_held` reads as holding the
        slot — souled, posted, on shift. Death must be the only thing
        that changes the answer, or the test proves nothing."""
        keeper = self.char2
        keeper.db.soul_post = self.room1
        keeper.db.soul_schedule = "day"
        from world.souls import engine
        keeper.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        return keeper

    def test_the_fixture_holds_the_slot_while_alive(self):
        """Guard on the test itself: if this were False, the death case
        below would pass for the wrong reason."""
        keeper = self._souled_keeper()
        with mock.patch.object(postsmod, "_post_room",
                               return_value=self.room1):
            self.assertTrue(
                postsmod._slot_held(self._post(), "day", self._slot(keeper)))

    def test_a_dead_keeper_does_not_hold_the_slot(self):
        keeper = self._souled_keeper()
        with mock.patch.object(postsmod, "_post_room",
                               return_value=self.room1), \
             mock.patch.object(type(keeper), "is_dead", return_value=True):
            self.assertFalse(
                postsmod._slot_held(self._post(), "day", self._slot(keeper)),
                "a corpse in Limbo still held the post")

    def test_a_living_keeper_still_holds_it(self):
        """The pin: this must not vacate staffed posts."""
        keeper = self.char2
        keeper.db.soul_post = self.room1
        keeper.db.soul_schedule = "day"
        from world.souls import engine
        keeper.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        with mock.patch.object(postsmod, "_post_room",
                               return_value=self.room1):
            self.assertTrue(
                postsmod._slot_held(self._post(), "day", self._slot(keeper)))

    def test_no_keeper_is_not_held(self):
        self.assertFalse(
            postsmod._slot_held(self._post(), "day", self._slot(None)))


class TestARestoredKeeperIsActuallyAlive(EvenniaCommandTest):
    """The trap in fixing this: adding an aliveness test WITHOUT a real
    revival converts a permanently-held slot into a permanently-churning
    one -- restored, read dead, vacated, resleeved, forever.

    The old code set `db.is_dead = None`, which cleared an attribute
    nothing carries, so the body arrived at its post still medically
    dead.
    """

    def test_resetting_the_body_clears_death(self):
        from world.medical.procedures import reset_body_preserving_augments
        char = self.char2
        # a real, working body reads alive after a factory reset
        reset_body_preserving_augments(char)
        self.assertFalse(char.is_dead(),
                         "a freshly sleeved body still reads dead")

    def test_it_survives_a_body_with_no_medical_system(self):
        from world.medical.procedures import reset_body_preserving_augments
        # must not raise — the resleeve path runs over fixtures too
        reset_body_preserving_augments(SimpleNamespace(
            db=SimpleNamespace(species=None, medical_state=None)))
