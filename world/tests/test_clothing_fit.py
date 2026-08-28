"""One rule for "will this go on", asked instead of guessed (#2337).

The layering rule lived only inside `wear_item`, so the only way to
ask whether a garment could be worn was to TRY it and read the
refusal. The souls layer did exactly that: the wardrobe planner picked
a layer-0 garment, the wear step issued the command, the command
refused, and it looped.

Noel Dudnik and Jordan Esparza spent days trying to put rainbow coding
socks on over their Thawn-Harrison slippers. They were never going to
succeed, and nothing in the planning path could tell.

Now `clothing_mixin` answers the question and the souls layer consults
it before choosing — the same shape as every other fix this week:
where two components serve one decision, they must share the rule.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions


class TestBlockingGarments(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def _g(self, key, coverage, layer):
        g = create_object("typeclasses.items.Item", key=key,
                          location=self.soul)
        g.db.coverage = list(coverage)
        g.db.layer = layer
        g.db.worn_desc = key
        return g

    def test_nothing_worn_means_anything_fits(self):
        socks = self._g("socks", ["left_foot"], 0)
        self.assertTrue(self.soul.can_wear_now(socks))
        self.assertEqual(self.soul.blocking_garments(socks), [])

    def test_an_inner_layer_cannot_go_under_an_outer_one(self):
        """You do not put socks on over your shoes."""
        shoes = self._g("slippers", ["left_foot"], 2)
        self.soul.wear_item(shoes)
        socks = self._g("socks", ["left_foot"], 0)
        self.assertFalse(self.soul.can_wear_now(socks))
        self.assertIn(shoes, self.soul.blocking_garments(socks))

    def test_same_layer_same_place_collides(self):
        a = self._g("a shirt", ["chest"], 1)
        self.soul.wear_item(a)
        b = self._g("another shirt", ["chest"], 1)
        self.assertFalse(self.soul.can_wear_now(b))

    def test_an_outer_layer_goes_on_over(self):
        shirt = self._g("a shirt", ["chest"], 1)
        self.soul.wear_item(shirt)
        coat = self._g("a coat", ["chest"], 2)
        self.assertTrue(self.soul.can_wear_now(coat))

    def test_different_places_do_not_collide(self):
        socks = self._g("socks", ["left_foot"], 0)
        self.soul.wear_item(socks)
        hat = self._g("a hat", ["head"], 0)
        self.assertTrue(self.soul.can_wear_now(hat))

    def test_an_unreadable_item_simply_does_not_fit(self):
        class _Odd:
            def get_current_coverage(self):
                raise RuntimeError("no coverage")
        self.assertFalse(self.soul.can_wear_now(_Odd()))


class TestSoulsAskBeforeChoosing(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def _g(self, key, coverage, layer):
        g = create_object("typeclasses.items.Item", key=key,
                          location=self.soul)
        g.db.coverage = list(coverage)
        g.db.layer = layer
        g.db.worn_desc = key
        return g

    def test_an_unwearable_garment_is_not_counted_as_clothes(self):
        """The bug: holding socks you can never put on made the planner
        think you were sorted, so you never went shopping."""
        shoes = self._g("slippers", ["left_foot"], 2)
        self.soul.wear_item(shoes)
        socks = self._g("socks", ["left_foot"], 0)
        self.assertFalse(actions._wearable(self.soul, socks))

    def test_a_wearable_one_still_counts(self):
        coat = self._g("a coat", ["chest"], 2)
        self.assertTrue(actions._wearable(self.soul, coat))

    def test_something_already_on_never_counts(self):
        shirt = self._g("a shirt", ["chest"], 1)
        self.soul.wear_item(shirt)
        self.assertFalse(actions._wearable(self.soul, shirt))

    def test_the_souls_layer_does_not_re_derive_the_rule(self):
        """One rule, one place. A second copy is how this family of bug
        happens — five instances this week."""
        import inspect
        src = inspect.getsource(actions._wearable)
        # Code only -- the comment above the call names the layer rule
        # precisely to explain why this function must NOT implement it.
        code = "\n".join(ln for ln in src.split("\n")
                         if not ln.strip().startswith("#")
                         and '"""' not in ln)
        self.assertIn("can_wear_now", code)
        self.assertNotIn("layer", code)


class TestWearItemStillEnforcesIt(EvenniaCommandTest):
    """Extracting the question must not weaken the answer."""

    def _g(self, key, coverage, layer):
        g = create_object("typeclasses.items.Item", key=key,
                          location=self.char1)
        g.db.coverage = list(coverage)
        g.db.layer = layer
        g.db.worn_desc = key
        return g

    def test_wearing_under_an_outer_layer_is_still_refused(self):
        shoes = self._g("slippers", ["left_foot"], 2)
        self.char1.wear_item(shoes)
        socks = self._g("socks", ["left_foot"], 0)
        ok, msg = self.char1.wear_item(socks)
        self.assertFalse(ok)
        self.assertIn("cannot wear", msg)
