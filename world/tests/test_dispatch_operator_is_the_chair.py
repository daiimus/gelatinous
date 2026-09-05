"""The desk answers to whoever holds the chair (#2710).

`get_dispatch_operator` tested `db.dispatch_operator is True` -- an
attribute exactly ONE object in the database carries, set by the spawner
on the day keeper. But the dispatch post is rostered across all three
shifts (day Petra, swing Kiro, night Ines), so for two shifts out of
three the function returned None no matter who was sitting there and the
automation answered.

Its own docstring frames it as a STATE question -- "dead, unconscious,
absent, kidnapped = the automation answers, a difference players can
hear" -- while the code asked an identity question: is this the specific
body the spawner flagged. Two-thirds of every day, the colony had no
dispatcher by definition.

`keeper_on_duty` is the post machinery the shops, bar and clinic gates
already use, and it answers the state question: somebody is here AND it
is their shift.
"""
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.director import population


class TestWhoeverHoldsTheChair(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.desk = self.room1
        patcher = mock.patch.object(population, "get_dispatch_room",
                                    return_value=self.desk)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _keeper(self, key, at_desk=True):
        npc = create_object("typeclasses.characters.Character", key=key,
                            location=self.desk if at_desk else self.room2)
        return npc

    def _roster(self, **shifts):
        self.desk.db.post_slots = {
            shift: {"keeper": keeper} for shift, keeper in shifts.items()
        }

    def test_the_swing_keeper_is_the_operator_on_swing(self):
        """The case that was impossible: Kiro carries no flag, so before
        this he could never be the operator however long he sat there."""
        kiro = self._keeper("Kiro")
        self._roster(day=self._keeper("Petra", at_desk=False), swing=kiro)
        with mock.patch("world.souls.posts.current_shift",
                        return_value="swing"):
            self.assertIs(population.get_dispatch_operator(), kiro)

    def test_the_day_keeper_is_the_operator_on_day(self):
        """The pin: the one shift that already worked must keep working."""
        petra = self._keeper("Petra")
        self._roster(day=petra, swing=self._keeper("Kiro", at_desk=False))
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            self.assertIs(population.get_dispatch_operator(), petra)

    def test_an_off_shift_keeper_at_the_desk_is_not_the_operator(self):
        """Presence alone is not enough — that is the whole point of
        `keeper_on_duty`, and a night keeper lingering after their shift
        should not be answering the radio."""
        ines = self._keeper("Ines")
        self._roster(day=self._keeper("Petra", at_desk=False), night=ines)
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            self.assertIsNone(population.get_dispatch_operator())

    def test_an_absent_keeper_means_the_automation_answers(self):
        petra = self._keeper("Petra", at_desk=False)
        self._roster(day=petra)
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            self.assertIsNone(population.get_dispatch_operator())

    def test_a_dead_operator_means_the_automation_answers(self):
        petra = self._keeper("Petra")
        self._roster(day=petra)
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"), \
             mock.patch.object(type(petra), "is_dead", return_value=True):
            self.assertIsNone(population.get_dispatch_operator())

    def test_an_unconscious_operator_means_the_automation_answers(self):
        petra = self._keeper("Petra")
        self._roster(day=petra)
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"), \
             mock.patch.object(type(petra), "is_unconscious",
                               return_value=True):
            self.assertIsNone(population.get_dispatch_operator())

    def test_the_legacy_flag_still_works_with_no_roster(self):
        """Strictly widens rather than trading one narrow test for
        another: a post with no slots configured still answers."""
        flagged = self._keeper("Solo")
        flagged.db.dispatch_operator = True
        self.desk.db.post_slots = {}
        self.assertIs(population.get_dispatch_operator(), flagged)

    def test_an_empty_desk_is_still_none(self):
        self.desk.db.post_slots = {}
        self.assertIsNone(population.get_dispatch_operator())
