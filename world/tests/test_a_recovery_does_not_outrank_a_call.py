"""A recovery errand respects the band ladder (#2899 follow-up).

`recover_casualty` could never return True before #2899: it called
`is_grappled(character)` with one argument where the function takes
two, so every call raised TypeError and the blanket `except` returned
False -- the same value the success branch returns. Nine days of logs
showed `goal=recover` elected zero times. Fixing the arity was right.

It also made the rest of the function run for the first time, and the
rest of the function does this:

    job = actions.plan_for(soul, "recover")
    soul.db.soul_job = job

unconditionally -- with no reference to the job the soul is already
holding. `notice_casualty` is called from `think()` for every soul that
is not in combat, and it is called BEFORE the engine reads
`soul.db.soul_job` for arbitration.

`recover` sits at band 2. A unit dispatched to a call holds a `respond`
job at BAND 0, precisely so that "a unit does not wander off a call"
(#2384). The engine's own rule is that preemption requires a STRICTLY
lower band:

    if desired and band < job_band:

Writing the job directly walks around that rule, so a unit on its way
to a crime that passed a downed unit dropped the call and carried the
body home instead -- while dispatch still held the assignment.

The fix asks the same question the engine asks, in the same direction.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.director import medical as medmod


class TestRecoveryYieldsToAHigherPriorityJob(EvenniaTest):

    def _unit(self, key):
        unit = create_object("typeclasses.characters.Character",
                             key=key, location=self.room1)
        unit.db.role = "security"
        unit.db.species = "robot"
        return unit

    def setUp(self):
        super().setUp()
        self.soul = self._unit("Unit A")
        self.casualty = self._unit("Unit B")
        # `plan_for` needs to produce something for the errand to be
        # takeable at all; the band question is what is under test.
        self.plan = mock.patch(
            "world.souls.actions.plan_for",
            return_value={"goal": "recover", "at": 0, "steps": []})
        self.plan.start()
        self.addCleanup(self.plan.stop)

    def test_an_idle_unit_takes_the_errand(self):
        """Control. Without this, 'never clobbers' would also be true of
        a function that never takes the errand -- which is exactly the
        state #2899 found it in."""
        self.soul.db.soul_job = None
        self.assertTrue(medmod.recover_casualty(self.soul, self.casualty))
        self.assertIsNotNone(self.soul.db.soul_job)

    def test_it_does_not_drop_a_dispatched_call(self):
        """A `respond` job is band 0 so a unit does not wander off it."""
        call = {"goal": "respond", "band": 0, "at": 0, "steps": []}
        self.soul.db.soul_job = call
        took = medmod.recover_casualty(self.soul, self.casualty)
        self.assertFalse(took, "the recovery outranked a band-0 call")
        self.assertEqual(self.soul.db.soul_job.get("goal"), "respond",
                         "the dispatched call was overwritten")

    def test_it_does_not_leave_the_recovering_marker_behind_on_refusal(self):
        """`soul_recovering` is set before the plan is made; a refusal
        must not strand it, or the unit can never recover anything."""
        self.soul.db.soul_job = {"goal": "respond", "band": 0,
                                 "at": 0, "steps": []}
        medmod.recover_casualty(self.soul, self.casualty)
        self.assertFalse(self.soul.db.soul_recovering)

    def test_it_still_preempts_a_lower_priority_job(self):
        """The other half: a patrol (band 4) SHOULD yield to a recovery
        (band 2), or the fix has just disabled the feature again."""
        self.soul.db.soul_job = {"goal": "patrol", "band": 4,
                                 "at": 0, "steps": []}
        took = medmod.recover_casualty(self.soul, self.casualty)
        self.assertTrue(took, "a recovery could not preempt a patrol")
        self.assertEqual(self.soul.db.soul_job.get("goal"), "recover")
