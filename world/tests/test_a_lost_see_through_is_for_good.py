"""A lost see-through is for good (#3817).

The spec: the outcome of the see-through roll "is cached permanently ...
one careful look determines the verdict, no re-roll abuse".

`forget` clears stored verdicts about a body so that a recognition the
player disowns does not come back by itself. It cleared LOST verdicts
too, and that was a way to roll again: name the masked figure anything,
forget that name, look. In play a mask that had held was seen through on
the fourth try.

The voice cache had the same flaw through the same `forget`, found in
review, and is held to the same rule here.

Real commands (`remember`, `forget`, `wear`, `look`) on fresh bodies
with the real ski mask. The dice are stood in for to choose a branch,
and then to prove none are thrown.
"""
from world.identity import get_apparent_uid
from world.tests.test_an_eyewitness_keeps_the_name import (
    LOST, WON, _MaskCase,
)


class _TheMaskWentOnOutOfSight(_MaskCase):
    """The viewer calls the bare face Tamsin. The mask goes on in another
    room, Tamsin walks back in under it, and the viewer looks once."""

    FIRST_LOOK = LOST

    def setUp(self):
        super().setUp()
        self.them.move_to(self.room2, quiet=True, move_hooks=False)
        self.them.execute_cmd("wear ski mask")
        self.them.move_to(self.room1, quiet=True, move_hooks=False)
        self.masked = get_apparent_uid(self.them)
        first = self.dice(self.FIRST_LOOK)
        self.seen = self.roster()
        self.assertEqual(first.call_count, 1, "the first look did not roll")

    def verdict(self):
        cache = dict(self.viewer.db.disguise_pierce_cache or {})
        return cache.get((self.them.dbref, self.masked))


class TestTheMaskHeld(_TheMaskWentOnOutOfSight):
    FIRST_LOOK = LOST

    def test_the_setup_is_what_it_says(self):
        self.assertNotIn("Tamsin", self.seen)
        self.assertIs(self.verdict(), False)

    def test_naming_the_mask_and_forgetting_the_name_buys_no_second_roll(
            self):
        self.do("remember masked man as Xq")
        self.assertIn("forget the name", self.do("forget xq"))
        self.assertIs(self.verdict(), False)
        self.no_dice()
        self.assertNotIn("Tamsin", self.roster())

    def test_however_many_times(self):
        for _ in range(4):
            self.do("remember masked man as Xq")
            self.do("forget xq")
        self.no_dice()
        self.assertNotIn("Tamsin", self.roster())
        self.assertIs(self.verdict(), False)

    def test_nor_does_forgetting_the_face(self):
        self.do("forget tamsin")
        self.assertIs(self.verdict(), False)


class TestAVoiceThatWasNotPlaced(_MaskCase):
    """The same rule for the ear. `remember` names the voice along with
    the face, an unseen line rolls once to place it, and `forget`
    reaches the stored placements through the same door."""

    def setUp(self):
        super().setUp()
        from world.voice import get_apparent_voice_uid
        self.voice = get_apparent_voice_uid(self.them)
        self.key = (self.them.dbref, self.voice)

    def placed(self, verdict):
        """A stored placement of his voice, set by hand: the roll itself
        needs a speaker the viewer cannot see."""
        self.viewer.db.voice_discern_cache = {self.key: verdict}

    def stored(self):
        return dict(self.viewer.db.voice_discern_cache or {}).get(self.key)

    def test_the_setup_is_what_it_says(self):
        """`remember man as Tamsin` named his voice."""
        memory = dict(self.viewer.voice_memory or {})
        self.assertEqual(memory[self.voice]["assigned_name"], "Tamsin")

    def test_forgetting_him_keeps_a_lost_placement(self):
        self.placed(False)
        self.assertIn("forget the name", self.do("forget tamsin"))
        self.assertIs(self.stored(), False)

    def test_and_drops_a_won_one(self):
        """The control."""
        self.placed(True)
        self.do("forget tamsin")
        self.assertIsNone(self.stored())


class TestTheMaskWasSeenThrough(_TheMaskWentOnOutOfSight):
    """The control, and the reason `forget` touches verdicts at all."""

    FIRST_LOOK = WON

    def test_the_setup_is_what_it_says(self):
        self.assertIn("Tamsin", self.seen)
        self.assertIs(self.verdict(), True)

    def test_forgetting_them_takes_the_won_verdict_with_it(self):
        self.do("forget tamsin")
        self.assertIsNone(self.verdict())
        self.assertNotIn("Tamsin", self.roster())
