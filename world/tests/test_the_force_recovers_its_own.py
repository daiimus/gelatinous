"""A downed unit gets carried home (#2282).

Nothing recovered a casualty. A destroyed secbot stayed where it fell
— and a unit's weapon is an augment ORGAN, so that wreck is a working
shotgun lying in the street that nobody ever comes for.

Owner ruling 2026-08-24: the force recovers its own. A second unit
leaves its patrol, takes hold and drags it back, which costs the force
a patrol while it runs — a downed unit visibly thins the streets.

The trap this had to dodge: the mugger's `grapple` step guards on
can_contest (conscious AND unrestrained), both false for a wreck. It
would have read an unresisting body as ALREADY HELD and walked home
dragging nothing, successfully, with no fault raised.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import medical
from world.souls import actions


def _unit(char, uid_role="security"):
    char.db.role = uid_role
    char.db.species = "robot"
    return char


class TestWhoRecoversWhom(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.finder = _unit(self.char1)
        self.wreck = _unit(self.char2)
        self.finder.db.soul_post = self.room1

    def _take(self):
        with mock.patch.object(medical, "_cmd", create=True), \
             mock.patch("world.combat.grappling.is_grappled",
                        return_value=False):
            return medical.recover_casualty(self.finder, self.wreck)

    def test_a_unit_recovers_a_unit(self):
        self.assertTrue(self._take())
        self.assertEqual(self.finder.db.soul_job["goal"], "recover")

    def test_it_claims_the_casualty(self):
        self._take()
        self.assertEqual(self.finder.db.soul_recovering, self.wreck.id)

    def test_a_unit_does_not_carry_a_colonist(self):
        """A secbot doesn't sling a bleeding person over its shoulder.
        That's the medic's job, and the radio report is the right
        response to a casualty who is a person."""
        self.wreck.db.species = "human"
        self.wreck.db.role = None
        self.assertFalse(self._take())

    def test_a_colonist_does_not_carry_a_unit(self):
        self.finder.db.role = None
        self.finder.db.species = "human"
        self.assertFalse(self._take())

    def test_two_units_do_not_both_fetch_the_same_wreck(self):
        with mock.patch.object(medical, "_cmd", create=True), \
             mock.patch("world.combat.grappling.is_grappled",
                        return_value=True):
            self.assertFalse(medical.recover_casualty(self.finder,
                                                      self.wreck))

    def test_a_unit_already_on_an_errand_does_not_take_another(self):
        self._take()
        self.assertFalse(self._take())


class TestThePlan(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.unit = _unit(self.char1)
        self.wreck = _unit(self.char2)
        self.unit.db.soul_post = self.room1
        self.unit.db.soul_recovering = self.wreck.id

    def test_hold_then_walk_then_let_go(self):
        job = actions.plan_for(self.unit, "recover")
        self.assertEqual([s["do"] for s in job["steps"]],
                         ["hold", "travel", "deliver"])

    def test_it_takes_hold_before_it_walks(self):
        """Dragging is emergent from hold + movement. Walking first
        would just be leaving."""
        job = actions.plan_for(self.unit, "recover")
        self.assertEqual(job["steps"][0]["do"], "hold")
        self.assertEqual(job["steps"][0]["wreck"], self.wreck.id)

    def test_no_casualty_no_plan(self):
        self.unit.db.soul_recovering = None
        self.assertIsNone(actions.plan_for(self.unit, "recover"))

    def test_a_vanished_casualty_makes_no_plan(self):
        self.unit.db.soul_recovering = 99999999
        self.assertIsNone(actions.plan_for(self.unit, "recover"))

    def test_the_bay_falls_back_to_the_post(self):
        """Tag-driven so a builder can move the precinct, but a unit
        with no tagged bay still takes the wreck somewhere."""
        self.assertIs(actions.recovery_bay(self.unit), self.room1)


class TestTheHoldStep(EvenniaCommandTest):
    """The step exists precisely because the mugger's grapple cannot
    take hold of something that cannot resist."""

    def test_it_does_not_guard_on_can_contest(self):
        """Code only — the comment above the step names can_contest
        precisely to explain why the step must not use it."""
        import inspect
        src = inspect.getsource(__import__(
            "world.souls.jobs", fromlist=["step_job"]))
        hold = src[src.index('if do == "hold":'):src.index('if do == "deliver":')]
        code = "\n".join(ln for ln in hold.split("\n")
                         if not ln.strip().startswith("#"))
        self.assertNotIn("can_contest", code)
        self.assertIn("is_grappled", code)

    def test_it_issues_the_real_command(self):
        import inspect
        src = inspect.getsource(__import__(
            "world.souls.jobs", fromlist=["step_job"]))
        hold = src[src.index('if do == "hold":'):src.index('if do == "deliver":')]
        self.assertIn('execute_cmd(f"grapple', hold)

    def test_a_faulted_errand_releases_its_claim(self):
        """Otherwise one bad recovery strands that unit forever."""
        from world.souls import jobs
        unit = _unit(self.char1)
        unit.db.soul_recovering = 4242
        jobs.fault(unit, "test")
        self.assertIsNone(unit.db.soul_recovering)
