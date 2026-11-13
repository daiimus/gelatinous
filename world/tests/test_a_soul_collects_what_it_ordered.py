"""A soul collects what it ordered before it turns to anything else (#3796).

Live, 2026-11-13: sixty bowls of kuro-nikomi stew stood on the shell
counter at the Escallier Snailery. Souls take the oldest bowl first, so
the pile never looked old: it was a standing backlog that every later
order rotated through and none reduced, and the only thing that clears
a counter is a person running `clean`.

A bowl is stranded when the engine replaces a job between its `order`
and its `pickup`. `engine.think` dropped the running job for any
strictly higher band, whichever step it stood on, and the job market
overwrote a leisure job outright. Both now ask `jobs.order_outstanding`
first.

Real objects, the real `get ... from ...` and the real `think`: what is
under test is where the bowl ends up, and a mocked step cannot show
that. Only the goal arbitration is stood in for, because the band is
the input here and not the thing being judged.
"""
import time as _time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import engine, jobs

STEW = "a bowl of kuro-nikomi stew"
NOON = 12.0


class _AtTheCounterBase(BaseEvenniaTest):
    """A soul standing at a tended counter with a hunger job planned at
    the elevated band, which is the band a shift or a bed outranks."""

    def setUp(self):
        super().setUp()
        self.yard = create_object("typeclasses.rooms.Room", key="yard")
        self.counter = create_object(
            "typeclasses.bar.BarCounter", key="the test counter",
            location=self.yard)
        self.soul = create_object(
            "typeclasses.characters.Character", key="TestSoul",
            location=self.yard)
        self.soul.cmdset.add(
            "commands.default_cmdsets.CharacterCmdSet", persistent=False)
        self.soul.tags.add("soul", category="npc_role")
        self.soul.db.soul_needs = {"hunger": 0.7, "_at": _time.time()}
        # What the planner would have built next, had it been asked. The
        # mock is the witness: `think` only plans once the old job is
        # gone, so "was it called" is "was the soul interrupted".
        self.plan = mock.patch(
            "world.souls.actions.plan_for",
            side_effect=lambda soul, goal: {
                "goal": goal, "at": 0,
                "steps": [{"do": "travel", "room": self.yard.id}]})
        self.planned = self.plan.start()
        self.addCleanup(self.plan.stop)

    def serve(self):
        """What the keeper sets down a beat after the order."""
        bowl = create_object(
            "typeclasses.items.Item", key=STEW, location=self.counter)
        bowl.tags.add("eat", category="delivery_method")
        bowl.db.drink_effects = {"nutrition": 1}
        bowl.db.uses_left = 3
        return bowl

    def order_placed(self, band=3):
        """The job as it stands once `order` has spoken: on `pickup`."""
        self.soul.db.soul_job = {
            "goal": "hunger", "band": band, "at": 1, "steps": [
                {"do": "order", "counter": self.counter.id,
                 "tender": self.soul.id, "word": "kuro",
                 "want": "bowl of kuro-nikomi"},
                {"do": "pickup", "counter": self.counter.id, "verb": "eat",
                 "want": "bowl of kuro-nikomi"},
                {"do": "eat"}]}

    def think(self, band, goal):
        """One think with the band tree answering `(band, goal)`."""
        with mock.patch.object(
                engine, "_desired_goal", return_value=(band, goal)):
            engine.think(self.soul, NOON)

    def carried(self):
        return [o.key for o in self.soul.contents]

    def on_the_counter(self):
        return [o.key for o in self.counter.contents]

    def interrupted_for(self):
        """The goals `think` has planned so far, in order."""
        return [call.args[1] for call in self.planned.call_args_list]


class TestAnOrderIsCollectedFirst(_AtTheCounterBase):
    def test_a_job_with_nothing_on_the_counter_yields_at_once(self):
        """The control: the same soul and the same shift bell, with the
        bowl already in hand. Nothing here is waiting on a counter, so
        the engine interrupts on this think as it always did. Without
        this, 'the shift waited' below would also be true of an engine
        that had stopped interrupting anything."""
        bowl = self.serve()
        bowl.move_to(self.soul, quiet=True)
        self.soul.db.soul_job = {
            "goal": "hunger", "band": 3, "at": 0, "steps": [{"do": "eat"}]}
        self.think(2, "duty")
        self.assertEqual(self.interrupted_for(), ["duty"])
        self.assertEqual(self.soul.db.soul_job.get("goal"), "duty")

    def test_the_bowl_is_lifted_before_the_shift_is_answered(self):
        self.serve()
        self.order_placed()
        self.think(2, "duty")
        self.assertEqual(self.on_the_counter(), [],
                         "the order was left on the counter")
        self.assertEqual(self.carried(), [STEW])
        self.assertEqual(self.interrupted_for(), [],
                         "the soul left before it had its order")
        self.assertEqual(self.soul.db.soul_job.get("goal"), "hunger")

    def test_the_shift_is_answered_on_the_next_think(self):
        """One step of grace, not a meal's worth: the soul goes to work
        with the bowl in its pocket."""
        self.serve()
        self.order_placed()
        self.think(2, "duty")
        self.think(2, "duty")
        self.assertEqual(self.interrupted_for(), ["duty"])
        self.assertEqual(self.soul.db.soul_job.get("goal"), "duty")
        self.assertEqual(self.carried(), [STEW])
        self.assertEqual(self.on_the_counter(), [])

    def test_what_it_carried_away_is_its_next_meal(self):
        """The other half of 'nothing an NPC orders is left behind': the
        real planner, asked about hunger afterwards, plans the bowl in
        the pocket and no new purchase (#3793)."""
        bowl = self.serve()
        self.order_placed()
        self.think(2, "duty")
        self.think(2, "duty")
        self.plan.stop()
        try:
            from world.souls import actions
            job = actions.plan_for(self.soul, "hunger")
        finally:
            self.plan.start()
        self.assertEqual(job["steps"], [{"do": "eat", "item": bowl.id}])

    def test_a_critical_need_waits_one_step_too(self):
        """Exhaustion at band 1 is not fleeing. It was one of the five
        dropped orders in the live log (`goal=rest`)."""
        self.serve()
        self.order_placed()
        self.think(1, "rest")
        self.assertEqual(self.carried(), [STEW])
        self.assertEqual(self.interrupted_for(), [])


class TestWhatDoesNotWait(_AtTheCounterBase):
    def test_a_soul_fleeing_leaves_the_bowl(self):
        """Band 0 is the one thing no order holds up."""
        self.serve()
        self.order_placed()
        self.think(engine.SURVIVAL_BAND, "safety")
        self.assertEqual(self.interrupted_for(), ["safety"])
        self.assertEqual(self.on_the_counter(), [STEW])
        self.assertEqual(self.carried(), [])

    def test_an_order_that_never_comes_does_not_hold_the_soul(self):
        """The grace is bounded by the pickup's own patience. Nothing
        was set down: three rounds of waiting, a fault on the fourth,
        and the shift is answered on the think after."""
        self.order_placed()
        for _ in range(3):
            self.think(2, "duty")
        self.assertEqual(self.interrupted_for(), [],
                         "the soul gave up before the keeper had a chance")
        self.think(2, "duty")
        self.assertIsNone(self.soul.db.soul_job)
        faults = self.soul.db.soul_faults or []
        self.assertIn("nothing came", faults[-1][1])
        self.think(2, "duty")
        self.assertEqual(self.interrupted_for(), ["duty"])

    def test_a_weaker_want_never_interrupted_and_still_does_not(self):
        """Unchanged: a goal of the same or a lower band waits for the
        whole job, order or no order."""
        self.serve()
        self.order_placed(band=1)
        self.think(2, "duty")
        self.assertEqual(self.interrupted_for(), [])
        self.assertEqual(self.carried(), [STEW])


class TestTheJobMarketWaitsForTheGlass(_AtTheCounterBase):
    """`_offer` overwrites the job it finds, and a soul out drinking is
    a candidate ("leisure never blocks a job offer")."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            engine, "get_souls", return_value=[self.soul])
        patcher.start()
        self.addCleanup(patcher.stop)

    def candidates(self):
        from world.souls import posts
        return posts._eligible_candidates(self.yard)

    def craving_job(self, at):
        self.soul.db.soul_job = {"goal": "craving", "band": 3, "at": at,
                                 "steps": [
                                     {"do": "order", "counter": self.counter.id,
                                      "tender": self.soul.id, "word": "rotgut",
                                      "want": "mug of rotgut"},
                                     {"do": "pickup", "counter": self.counter.id,
                                      "verb": "drink", "want": "mug of rotgut"},
                                     {"do": "consume", "verb": "drink"}]}

    def test_a_soul_out_drinking_is_a_candidate(self):
        """The control: on any other step the offer still reaches it."""
        self.craving_job(at=2)
        self.assertEqual(self.candidates(), [self.soul])

    def test_a_soul_with_no_job_is_a_candidate(self):
        self.soul.db.soul_job = None
        self.assertEqual(self.candidates(), [self.soul])

    def test_a_soul_waiting_on_its_order_is_passed_over(self):
        self.craving_job(at=1)
        self.assertEqual(self.candidates(), [])


class TestOrderOutstanding(BaseEvenniaTest):
    PICKUP = {"do": "pickup", "counter": 1, "verb": "eat"}

    def test_a_job_on_its_pickup_step(self):
        job = {"goal": "hunger", "at": 1,
               "steps": [{"do": "order"}, self.PICKUP, {"do": "eat"}]}
        self.assertTrue(jobs.order_outstanding(job))

    def test_before_the_order_and_after_the_pickup(self):
        for at in (0, 2):
            job = {"goal": "hunger", "at": at,
                   "steps": [{"do": "order"}, self.PICKUP, {"do": "eat"}]}
            self.assertFalse(jobs.order_outstanding(job), f"step {at}")

    def test_a_finished_job_and_no_job(self):
        done = {"goal": "hunger", "at": 3,
                "steps": [{"do": "order"}, self.PICKUP, {"do": "eat"}]}
        for job in (done, None, {}, {"goal": "patrol", "at": 0, "steps": []}):
            self.assertFalse(jobs.order_outstanding(job), repr(job))

    def test_a_step_number_that_is_not_one(self):
        for at in (None, "1", True, -1):
            job = {"goal": "hunger", "at": at, "steps": [self.PICKUP, self.PICKUP]}
            self.assertFalse(jobs.order_outstanding(job), repr(at))

    def test_a_job_read_back_from_the_database(self):
        """A stored job is a `_SaverDict`, not a dict: the helper must
        read it, or it answers False for every real job (#2701)."""
        self.char1.db.soul_job = {
            "goal": "hunger", "at": 0, "steps": [dict(self.PICKUP)]}
        stored = self.char1.db.soul_job
        self.assertNotIsInstance(stored, dict)
        self.assertTrue(jobs.order_outstanding(stored))
