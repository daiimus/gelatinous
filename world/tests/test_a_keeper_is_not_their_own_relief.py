"""A keeper cannot relieve themselves (#3800).

Owner ruling 2026-11-13, on being shown why the stay-until-relieved rule
(#2434) was not holding: *"The rule is borked then. A keeper cannot
relieve themselves..."*

Live, the colony night of 2026-11-12: four counters lost their keeper
minutes before the 22:00 change. The outgoing keeper of each had a
personal clock running EARLY. "Has my shift ended?" is asked of that
clock; "has my relief arrived?" was asked of the colony's, which still
named the outgoing keeper's own shift, so the relief it found at the
post was the keeper asking. At the post they were released; away from
it they were called back; one flip a think until the colony clock
turned. The noodle cart and the shell counter were both unattended
while five souls looked for food.

`test_a_keeper_covers_until_relieved` patches the relief check in every
`on_duty` case, which is how this stood for two months. Nothing here
patches it: real slots, a real counter, and the colony clock set by
hand. The keeper's own hour is passed in as the colony's plus an
offset, which is all the jitter is.
"""
import datetime
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls import engine, posts


def colony(hour, minute):
    """Set the colony clock, which is what names the running shift."""
    return mock.patch(
        "world.gametime.colony_now",
        return_value=datetime.datetime(2026, 11, 12, hour, minute))


def own_hour(hour, minute, early):
    """The same moment on a clock running `early` minutes ahead."""
    return (hour + minute / 60.0 + early / 60.0) % 24.0


class _HandoverCase(EvenniaTest):
    """A counter going from swing (14..22) to night (22..6). The swing
    keeper stands at it; the night keeper has not come yet."""

    EARLY = 7      # the cart's swing keeper, live: seven minutes ahead

    def setUp(self):
        super().setUp()
        self.counter = create_object(
            "typeclasses.objects.Object", key="the counter",
            location=self.room1)
        self.outgoing = self.keeper("Outgoing", "swing", self.room1)
        self.incoming = self.keeper("Incoming", "night", self.room2)
        self.counter.db.post_slots = {
            "swing": {"keeper": self.outgoing},
            "night": {"keeper": self.incoming}}

    def keeper(self, key, schedule, where):
        npc = create_object(
            "typeclasses.characters.Character", key=key, location=where)
        npc.db.soul_schedule = schedule
        npc.db.soul_post = self.room1
        return npc

    def on_duty(self, hour, minute, early=None):
        """Is the outgoing keeper working, at this colony time?"""
        early = self.EARLY if early is None else early
        with colony(hour, minute):
            return engine.on_duty(
                self.outgoing, own_hour(hour, minute, early))


class TestBeforeTheColonyClockTurns(_HandoverCase):
    """21:53 to 22:00: over by the keeper's clock, running by the
    colony's. This is the window they walked off in."""

    def test_mid_shift_they_are_working(self):
        """The control: nothing here is about an ordinary hour."""
        self.assertTrue(self.on_duty(20, 0))

    def test_they_stay_when_only_their_own_clock_says_it_is_over(self):
        self.assertTrue(
            self.on_duty(21, 55),
            "the keeper counted as their own relief and left")

    def test_they_stay_through_the_very_minute_it_ends(self):
        """The heartbeat's hour has minute resolution, so the keeper's
        clock reads EXACTLY the end of the shift for a whole minute."""
        self.assertEqual(own_hour(21, 53, self.EARLY), 22.0)
        self.assertTrue(self.on_duty(21, 53))

    def test_the_answer_is_the_same_wherever_they_stand(self):
        """The flip itself: released at the post, called back from
        anywhere else."""
        at_post = self.on_duty(21, 55)
        self.outgoing.location = self.room2
        away = self.on_duty(21, 55)
        self.assertEqual(at_post, away)

    def test_the_planner_keeps_them_on_duty(self):
        # "wardrobe" outranks duty on purpose and a bare test character
        # is naked (see test_a_keeper_covers_until_relieved).
        with colony(21, 55):
            _band, goal = engine._desired_goal(
                self.outgoing, own_hour(21, 55, self.EARLY),
                exclude={"wardrobe"})
        self.assertEqual(goal, "duty")

    def test_somebody_early_for_the_next_shift_does_not_end_this_one(self):
        """The colony clock still names the swing shift, so its keeper
        is working it, whoever else has turned up."""
        self.incoming.location = self.room1
        self.assertTrue(self.on_duty(21, 55))

    def test_the_counter_was_never_the_one_that_closed(self):
        """The control on the other side: while the keeper stands
        there the counter answers with them. It went dark because
        they left."""
        with colony(21, 55):
            self.assertEqual(posts.keeper_on_duty(self.counter),
                             self.outgoing)


class TestTheShiftIsNotDroppedMidThink(_HandoverCase):
    """`engine.think` ends a duty job, pays the shift out and steps
    the keeper away from the counter the moment `on_duty` says no."""

    def working(self):
        self.outgoing.db.soul_job = {
            "goal": "duty", "band": 2, "at": 0, "steps": [{"do": "work"}]}

    def think(self, hour, minute, wants):
        with colony(hour, minute), \
                mock.patch.object(engine, "_desired_goal",
                                  return_value=wants), \
                mock.patch.object(engine.jobs, "step_job") as stepped, \
                mock.patch.object(engine.economy, "pay_wage",
                                  return_value=0) as paid:
            engine.think(self.outgoing, own_hour(hour, minute, self.EARLY))
        return stepped, paid

    def test_the_shift_goes_on(self):
        self.working()
        stepped, paid = self.think(21, 55, (2, "duty"))
        paid.assert_not_called()
        self.assertEqual(self.outgoing.db.soul_job.get("goal"), "duty")
        stepped.assert_called_once_with(self.outgoing)

    def test_it_ends_once_the_relief_is_standing_there(self):
        """The control: the payday branch still runs, once, when the
        night keeper has really taken over."""
        self.working()
        self.incoming.location = self.room1
        stepped, paid = self.think(22, 5, (4, None))
        paid.assert_called_once_with(self.outgoing)
        self.assertIsNone(self.outgoing.db.soul_job)
        stepped.assert_not_called()


class TestAfterTheColonyClockTurns(_HandoverCase):
    """From 22:00 the running shift is somebody else's, and the rule
    worked as written. All controls: none of this may change."""

    def test_they_cover_while_the_relief_is_still_on_the_way(self):
        self.assertTrue(self.on_duty(22, 5))

    def test_they_are_released_once_the_relief_stands_at_the_post(self):
        self.incoming.location = self.room1
        self.assertFalse(self.on_duty(22, 5))

    def test_a_relief_that_never_comes_is_given_up_on(self):
        late = 22 + engine.HOLDOVER_HOURS + 0.25
        with colony(23, 20):
            self.assertFalse(engine.on_duty(self.outgoing, late))

    def test_a_keeper_whose_clock_runs_late_hands_over_as_before(self):
        """Ten minutes behind, like the cart's other two keepers: still
        inside their own block at 22:05, released at 22:15."""
        self.assertTrue(self.on_duty(22, 5, early=-10))
        self.incoming.location = self.room1
        self.assertFalse(self.on_duty(22, 15, early=-10))


class TestTheReliefCheckItself(_HandoverCase):
    def test_the_keeper_of_the_running_shift_is_not_their_own_relief(self):
        with colony(21, 55):
            self.assertFalse(
                posts.relief_has_arrived(self.counter, self.outgoing))

    def test_the_same_keeper_is_a_relief_to_anybody_else(self):
        """Only the one asking is set aside."""
        with colony(21, 55):
            self.assertTrue(
                posts.relief_has_arrived(self.counter, self.incoming))

    def test_it_reads_the_room_the_way_it_reads_the_fixture(self):
        """The engine holds `soul_post` as the room."""
        with colony(21, 55):
            self.assertFalse(
                posts.relief_has_arrived(self.room1, self.outgoing))
        self.incoming.location = self.room1
        with colony(22, 5):
            self.assertTrue(
                posts.relief_has_arrived(self.room1, self.outgoing))
