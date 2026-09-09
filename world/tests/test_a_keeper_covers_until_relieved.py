"""A keeper covers until relieved, then gives up and goes home (#2434).

Owner ruling 2026-09-08, on being shown three options and rejecting all
of them: *"In real life, someone would just cover until the next shift
showed up, right? Or until they gave up and went home anyway. How do we
mirror that effectively?"*

`world/souls/posts.py` promises "the counter never closes; the faces
change", but souls carry a ±15 min personal schedule jitter while the
counter reads the colony clock raw. Both are deliberate — the jitter
staggers the commute so a shift change is not a synchronised
pathfinding burst, and a shift-staffed counter answering to the shared
clock is what stops a proprietor selling at midnight.

Together they produced two artifacts a real workplace does not have:

* **a venue dark for up to 30 minutes** at each change — the outgoing
  keeper gone early by their own clock, the incoming not yet due by
  theirs, with no overlap between the schedule blocks;
* **a keeper paid to refuse service** — on shift by her own clock, so
  placed behind the counter and accruing wage, while `keeper_on_duty`
  answered None and she verbally denied working. One body giving two
  answers to "am I on shift".

Modelling the human behaviour closes both at once, and closes them for
the same reason rather than by two special cases: the counter stays lit
because somebody is genuinely standing it, and that somebody is
genuinely working, so paying them is correct.

`on_duty` is stated once and consumed by all four callers —
`duty_pressure`, `_desired_goal`, the wage beat, and the goal-drop
check. A holdover only some of them believed in would be worse than
none: she would hold the counter open while the planner sent her home.

**`HOLDOVER_HOURS = 1.0` is PROVISIONAL** — no system here has had its
balance pass. It only has to comfortably exceed the ±15 min jitter,
which is how late a relief can normally be; an hour says "they
genuinely are not coming" rather than "they are running late".
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from world.souls import engine


class _ShiftCase(EvenniaTest):
    """Day shift runs 6..14 in SCHEDULES."""

    def keeper(self, schedule="day"):
        from evennia import create_object
        npc = create_object("typeclasses.characters.Character",
                            key="Keeper", location=self.room1)
        npc.db.soul_schedule = schedule
        npc.db.soul_post = self.room1
        return npc


class TestOnShiftIsUnchanged(_ShiftCase):
    def test_mid_shift_is_on_duty(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertTrue(engine.on_duty(self.keeper(), 10.0))

    def test_deep_off_shift_is_not(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertFalse(engine.on_duty(self.keeper(), 20.0))

    def test_a_soul_with_no_post_is_never_on_duty(self):
        npc = self.keeper()
        npc.db.soul_post = None
        self.assertFalse(engine.on_duty(npc, 10.0))


class TestCoveringUntilRelieved(_ShiftCase):
    def test_she_stays_past_the_end_when_nobody_has_come(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertTrue(engine.on_duty(self.keeper(), 14.5))

    def test_she_leaves_the_moment_the_relief_arrives(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=True):
            self.assertFalse(engine.on_duty(self.keeper(), 14.5))

    def test_she_gives_up_after_the_holdover_window(self):
        """Otherwise a dead successor means somebody works forever."""
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertFalse(
                engine.on_duty(self.keeper(),
                               14.0 + engine.HOLDOVER_HOURS + 0.25))

    def test_the_window_comfortably_exceeds_the_jitter(self):
        """A relief is at most ~15 min late by construction."""
        self.assertGreater(engine.HOLDOVER_HOURS, 0.5)


class TestTheWageFollowsTheWork(_ShiftCase):
    """The second artifact: she was PAID while refusing service. Now she
    is paid because she is genuinely serving."""

    def test_a_covering_keeper_counts_as_on_shift(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertTrue(engine.on_duty(self.keeper(), 14.5))

    def test_a_relieved_keeper_stops_counting(self):
        with patch("world.souls.posts.relief_has_arrived", return_value=True):
            self.assertFalse(engine.on_duty(self.keeper(), 14.5))

    def test_the_beat_reads_the_shared_predicate(self):
        import inspect
        source = inspect.getsource(engine)
        self.assertIn("on_shift = on_duty(soul, shour)", source)


class TestEveryConsumerAgrees(_ShiftCase):
    """A holdover only some callers believed in would be worse than
    none — she would hold the counter open while the planner sent her
    home. Driven, not source-inspected: my first two attempts here
    asserted the SHAPE of the code and broke on the docstring that
    explains them."""

    def test_duty_still_pulls_her_to_the_post_while_covering(self):
        npc = self.keeper()
        npc.location = self.room2          # not at post
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            self.assertGreater(engine.duty_pressure(npc, 14.5), 0.0)

    def test_and_stops_the_moment_she_is_relieved(self):
        npc = self.keeper()
        npc.location = self.room2
        with patch("world.souls.posts.relief_has_arrived", return_value=True):
            self.assertEqual(engine.duty_pressure(npc, 14.5), 0.0)

    def test_the_planner_still_wants_duty_while_she_covers(self):
        # "wardrobe" is excluded because it outranks duty on purpose —
        # you get dressed before you go to work — and a bare test
        # character is naked, so it would win every time.
        npc = self.keeper()
        with patch("world.souls.posts.relief_has_arrived", return_value=False):
            _band, goal = engine._desired_goal(npc, 14.5,
                                               exclude={"wardrobe"})
        self.assertEqual(goal, "duty")

    def test_and_stops_wanting_it_once_relieved(self):
        npc = self.keeper()
        with patch("world.souls.posts.relief_has_arrived", return_value=True):
            _band, goal = engine._desired_goal(npc, 14.5,
                                               exclude={"wardrobe"})
        self.assertNotEqual(goal, "duty")


class TestTheCounterAcceptsACoveringKeeper(EvenniaTest):
    def _counter(self, keeper, shift):
        from evennia import create_object
        fixture = create_object("typeclasses.objects.Object",
                                key="the counter", location=self.room1)
        fixture.db.post_slots = {shift: {"keeper": keeper}}
        return fixture

    def test_the_relief_check_is_not_circular(self):
        """If `relief_has_arrived` asked `keeper_on_duty`, a covering
        keeper would report herself as her own relief and never leave."""
        from evennia import create_object
        from world.souls.posts import relief_has_arrived, current_shift
        covering = create_object("typeclasses.characters.Character",
                                 key="Covering", location=self.room1)
        other = "night" if current_shift() != "night" else "day"
        fixture = self._counter(covering, other)
        self.assertFalse(relief_has_arrived(fixture))

    def test_it_sees_a_real_relief(self):
        from evennia import create_object
        from world.souls.posts import relief_has_arrived, current_shift
        arriving = create_object("typeclasses.characters.Character",
                                 key="Arriving", location=self.room1)
        fixture = self._counter(arriving, current_shift())
        self.assertTrue(relief_has_arrived(fixture))

    def test_an_absent_relief_does_not_count(self):
        from evennia import create_object
        from world.souls.posts import relief_has_arrived, current_shift
        elsewhere = create_object("typeclasses.characters.Character",
                                  key="Elsewhere", location=self.room2)
        fixture = self._counter(elsewhere, current_shift())
        self.assertFalse(relief_has_arrived(fixture))
