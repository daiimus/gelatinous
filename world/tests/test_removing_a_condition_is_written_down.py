"""Removing a condition persists, like adding one (#2739).

`add_condition` ends with an explicit save and an explicit comment:

    # Save medical state after adding condition to ensure persistence
    if self.character:
        self.character.save_medical_state()

`remove_condition` -- its twin, twenty lines below -- removed the
condition from the list, invalidated derived state, stopped the ticker,
and returned. Nothing wrote it down. So a condition cleared in memory
reappeared on the next reload from whatever the last save happened to
hold, and this project reloads often.

TWO OF #2739's THREE CLAIMS WERE ALREADY FIXED, checked rather than
assumed before touching anything:

  * `apply_wound_care` DOES persist -- #2418 added the save, with the
    scar attached: "damage was lost on the next reload and the bleeding
    resumed unbraked". Its two early returns skip the save correctly:
    they are no-op paths (no wound, already stabilized) with nothing to
    write.
  * the MEDICAL TICK persists -- #2937 added it, and the comment records
    what the gap cost: "a reload HEALED bleeding".

So the treatment/dressing asymmetry the issue leads with is gone. The
asymmetric twin is what was left.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition


class TestRemoveConditionPersists(EvenniaTest):

    def _state(self):
        return self.char1.medical_state

    def _condition(self):
        return BleedingCondition(severity=3, location="chest")

    def test_adding_saves(self):
        """Control: the behaviour being mirrored. If `add_condition`
        stopped saving, the assertion below would pass for the wrong
        reason."""
        state = self._state()
        with mock.patch.object(type(self.char1), "save_medical_state") as save:
            state.add_condition(self._condition())
        self.assertTrue(save.called)

    def test_removing_saves_too(self):
        state = self._state()
        condition = self._condition()
        state.add_condition(condition)
        with mock.patch.object(type(self.char1), "save_medical_state") as save:
            state.remove_condition(condition)
        self.assertTrue(
            save.called,
            "a condition cleared in memory is not written down, so a "
            "reload brings it back")

    def test_removing_something_absent_does_not_save(self):
        """No mutation, no write -- a no-op must not churn the DB on
        every miss."""
        state = self._state()
        with mock.patch.object(type(self.char1), "save_medical_state") as save:
            state.remove_condition(self._condition())
        self.assertFalse(save.called)

    def test_the_condition_is_actually_gone(self):
        """The removal still works -- persistence was added, not
        substituted for the behaviour."""
        state = self._state()
        condition = self._condition()
        state.add_condition(condition)
        state.remove_condition(condition)
        self.assertNotIn(condition, state.conditions)
