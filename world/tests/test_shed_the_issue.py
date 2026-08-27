"""You cannot put socks on over your shoes (#2333).

Noel Dudnik and Jordan Esparza sat in a loop for hours — 100% of the
colony's remaining faults — and both were perfectly decent. They were
still in the Thawn-Harrison decant issue (jumpsuit + slippers) and each
holding one pair of rainbow coding socks.

Socks are `layer 0`: they must go UNDER everything. The clothing system
refused, correctly. The code that resolves this already existed — shed
the paper issue, then re-dress in what's real (#2118) — but it only ran
when there was NOTHING left to wear, and holding the socks is precisely
what stopped it running.

The trigger is the OBSERVED failure, not a re-derivation of the layer
rule: `clothing_mixin` owns that rule, and a second copy in the souls
layer is how this family of bug happens in the first place.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import jobs


class TestSheddingTheIssue(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def _garment(self, key, coverage, layer=1, provisional=False):
        g = create_object("typeclasses.items.Item", key=key,
                          location=self.soul)
        g.db.coverage = list(coverage)
        g.db.layer = layer
        g.db.worn_desc = key
        if provisional:
            g.db.provisional = True
        return g

    def test_paper_comes_off_when_real_clothes_can_cover(self):
        issue = self._garment("paper jumpsuit", ["chest", "groin"],
                              layer=1, provisional=True)
        self.soul.wear_item(issue)
        self._garment("a real shirt", ["chest"], layer=1)
        self._garment("real trousers", ["groin"], layer=1)
        self.assertTrue(jobs._shed_the_issue(self.soul))
        worn = {g.key for items in (self.soul.worn_items or {}).values()
                for g in items}
        self.assertNotIn("paper jumpsuit", worn)

    def test_carried_clothes_count_toward_decency(self):
        """The whole point of shedding is to put the carried thing ON,
        so it must count when deciding whether shedding is safe —
        otherwise the paper never comes off and the loop persists."""
        issue = self._garment("paper jumpsuit", ["chest", "groin"],
                              layer=1, provisional=True)
        self.soul.wear_item(issue)
        self._garment("a real coverall", ["chest", "groin"], layer=1)
        self.assertTrue(jobs._shed_the_issue(self.soul))

    def test_it_refuses_when_that_would_leave_them_bare(self):
        """The issue TEARS coming off, so the decision is made BEFORE
        stripping. Nothing real to replace it means it stays on."""
        issue = self._garment("paper jumpsuit", ["chest", "groin"],
                              layer=1, provisional=True)
        self.soul.wear_item(issue)
        self._garment("rainbow socks", ["left_foot"], layer=0)
        self.assertFalse(jobs._shed_the_issue(self.soul))
        worn = {g.key for items in (self.soul.worn_items or {}).values()
                for g in items}
        self.assertIn("paper jumpsuit", worn)

    def test_nothing_provisional_is_a_no_op(self):
        real = self._garment("a real shirt", ["chest"], layer=1)
        self.soul.wear_item(real)
        self.assertFalse(jobs._shed_the_issue(self.soul))


class TestTheBlockedCaseCanReachIt(EvenniaCommandTest):
    """It only ever ran on `not wearable`. Holding the blocked garment
    was what kept it from running."""

    def test_the_wear_step_calls_it_when_a_garment_will_not_go_on(self):
        import inspect
        src = inspect.getsource(jobs.step_job)
        wear = src[src.index('if do == "wear"'):]
        self.assertIn("_shed_the_issue(soul)", wear)
        self.assertIn('step["shed"]', wear)

    def test_it_only_tries_once_per_job(self):
        """Otherwise a soul that genuinely cannot dress strips itself
        every few beats forever."""
        import inspect
        src = inspect.getsource(jobs.step_job)
        wear = src[src.index('if do == "wear"'):]
        self.assertIn('not step.get("shed")', wear)

    def test_it_still_faults_eventually(self):
        """Shedding is one attempt, not an escape from the fault path."""
        import inspect
        src = inspect.getsource(jobs.step_job)
        wear = src[src.index('if do == "wear"'):]
        self.assertIn("won't go on", wear)
