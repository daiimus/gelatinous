"""Carrying trousers is not a reason to stay shirtless (#2329).

Found in the souls audit log: Bianca Morgan faulting
`blue_jeans_won't_go_on` every thirty minutes for hours.

She was already WEARING jeans. She had bought a second identical pair,
needed a chest layer, and the planner kept returning "wear" because she
was carrying something wearable — so she never went shopping, and the
wear step kept resolving "jeans" to the pair she already had on.

The shop branch already chose garments by what was still uncovered
("buying a jacket while bare-legged is how a soul ends up naked in a
coat"). The carried-clothes branch above it did not, and short-circuited
before the shop branch could ever run.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions


def _wardrobe_branch():
    """The carried-clothes branch, isolated from the shop branch."""
    import inspect
    src = inspect.getsource(actions.plan_for)
    branch = src[src.index('goal_need == "wardrobe"'):]
    return branch[:branch.index("for score, fixture, room")]


class TestSpareTrousersDoNotDress(EvenniaCommandTest):
    def test_the_carried_branch_consults_missing_coverage(self):
        """The whole fix: it must ask what is still bare before
        deciding she is sorted."""
        self.assertIn("_uncovered(soul)", _wardrobe_branch())

    def test_it_filters_on_the_intersection(self):
        """Not merely 'is it wearable' — does it cover something that
        is currently uncovered."""
        branch = _wardrobe_branch()
        self.assertIn("still_bare", branch)
        self.assertIn("coverage", branch)

    def test_nothing_bare_still_allows_wearing(self):
        """When nothing is missing, any wearable still counts — that is
        the upgrade case (swapping paper issue for real clothes), and
        it must not be broken by the fix."""
        self.assertIn("not still_bare", _wardrobe_branch())

    def test_the_shop_branch_is_untouched(self):
        """The half that was already right must stay right."""
        import inspect
        src = inspect.getsource(actions.plan_for)
        self.assertIn("naked in a coat", src)
        self.assertIn("_uncovered(soul)", src)


class TestUncoveredIsTheRealQuestion(EvenniaCommandTest):
    def test_a_dressed_soul_has_nothing_bare(self):
        soul = self.char1
        for key, cov in (("a shirt", ["chest"]),
                         ("trousers", ["groin"])):
            g = create_object("typeclasses.items.Item", key=key,
                              location=soul)
            g.db.coverage = list(cov)
            g.db.layer = 1
            g.db.worn_desc = key
            soul.wear_item(g)
        self.assertEqual(actions._uncovered(soul), set())

    def test_a_shirtless_soul_is_missing_a_chest(self):
        soul = self.char1
        g = create_object("typeclasses.items.Item", key="trousers",
                          location=soul)
        g.db.coverage = ["groin"]
        g.db.layer = 1
        g.db.worn_desc = "trousers"
        soul.wear_item(g)
        self.assertIn("chest", actions._uncovered(soul))
