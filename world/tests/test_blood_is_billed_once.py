"""Blood is billed once, by the path that honours the brakes (#2417).

`MedicalState.update_vital_signs` subtracted
`calculate_blood_loss_rate()` from `blood_level`. That number is a
PER-MINUTE rate (`CONDITION_CADENCE_SPEC` §5), and the subtraction:

* did not scale by elapsed time — it took a per-minute figure as a flat
  per-call amount;
* consulted neither brake, so a tourniquet spec'd as *"limb-only instant
  full hold at any severity"* merely halved a bleed, and a wound dressing
  spec'd as *"full stop at the location"* did the same;
* ran on every call, and `update_vital_signs` is not only on the tick —
  it runs from `apply_anatomical_damage`, every surgical step, every
  severance and every substance dose. A bleeding character lost a full
  minute of blood on **each incoming hit** inside a 6-second round.

And `MedicalScript.at_repeat` calls `process()` and *then*
`update_vital_signs()`, so every tick was billed twice.

`BleedingCondition.tick_effect` already does it correctly — scales by
elapsed minutes, returns early for a stabilized or tourniqueted location.
That is now the only place blood is subtracted.

**Why the suite was green.** The existing cadence tests call
`condition.process(...)` directly and assert `blood_level == 100.0`. They
never drive `update_vital_signs`, which is the carrier. These tests do.

This makes bleeding **less** lethal than it has been in practice, and
restores the two brakes to the strength their shipped specs describe.
"""
from types import SimpleNamespace
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition
from world.medical.core import MedicalState


def _patient():
    state = MedicalState(character=None)
    target = SimpleNamespace(medical_state=state, key="bleed-test")
    return target, state


class TestUpdatingVitalsDoesNotBillBlood(EvenniaTest):
    """The redundant subtraction, gone."""

    def test_a_bleed_loses_nothing_to_a_vitals_update(self):
        target, state = _patient()
        state.add_condition(BleedingCondition(5, "left_arm"))
        state.update_vital_signs()
        self.assertEqual(state.blood_level, 100.0)

    def test_repeated_updates_still_lose_nothing(self):
        """This is the per-hit case: `take_damage` runs a vitals update
        on every incoming blow."""
        target, state = _patient()
        state.add_condition(BleedingCondition(7, "left_arm"))
        for _ in range(10):
            state.update_vital_signs()
        self.assertEqual(state.blood_level, 100.0)

    def test_vitals_still_update_everything_else(self):
        """Pain and consciousness are this method's actual job."""
        target, state = _patient()
        state.add_condition(BleedingCondition(6, "left_arm"))
        state.update_vital_signs()
        self.assertGreater(state.pain_level, 0.0)


class TestTheTickStillBillsIt(EvenniaTest):
    def test_an_untreated_bleed_loses_blood_over_a_minute(self):
        target, state = _patient()
        cond = BleedingCondition(5, "left_arm")
        state.add_condition(cond)
        cond.last_processed = 1000.0
        with mock.patch("world.medical.conditions.random.random",
                        return_value=0.99):
            cond.process(target, current=1060.0)
        self.assertLess(state.blood_level, 100.0)

    def test_it_is_billed_once_not_twice(self):
        """A tick is `process()` then `update_vital_signs()`. The second
        must add nothing."""
        target, state = _patient()
        cond = BleedingCondition(5, "left_arm")
        state.add_condition(cond)
        cond.last_processed = 1000.0
        with mock.patch("world.medical.conditions.random.random",
                        return_value=0.99):
            cond.process(target, current=1060.0)
        after_process = state.blood_level
        state.update_vital_signs()
        self.assertEqual(state.blood_level, after_process)


class TestTheBrakesHoldCompletely(EvenniaTest):
    """Both are spec'd as full stops, and both were reduced to halving
    because the vitals path ignored them."""

    def test_a_tourniquet_holds_across_a_full_tick(self):
        from world.medical.treatments import apply_tourniquet
        target, state = _patient()
        cond = BleedingCondition(7, "left_arm")
        state.add_condition(cond)
        cond.last_processed = 1000.0
        self.assertTrue(
            apply_tourniquet(None, target, None, "left_arm")["applied"])
        with mock.patch("world.medical.conditions.random.random",
                        return_value=0.99):
            cond.process(target, current=1060.0)
        state.update_vital_signs()
        self.assertEqual(state.blood_level, 100.0)

    def test_a_tourniquet_holds_across_incoming_hits(self):
        """The per-hit path: a tourniqueted limb must not leak when the
        body takes damage elsewhere."""
        from world.medical.treatments import apply_tourniquet
        target, state = _patient()
        state.add_condition(BleedingCondition(7, "left_arm"))
        apply_tourniquet(None, target, None, "left_arm")
        for _ in range(5):
            state.update_vital_signs()
        self.assertEqual(state.blood_level, 100.0)


class TestTheRateHelperIsInformationalOnly(EvenniaTest):
    def test_it_still_reports_the_unattended_rate(self):
        target, state = _patient()
        state.add_condition(BleedingCondition(5, "left_arm"))
        self.assertGreater(state.calculate_blood_loss_rate(), 0.0)

    def test_nothing_subtracts_it(self):
        target, state = _patient()
        state.add_condition(BleedingCondition(5, "left_arm"))
        rate = state.calculate_blood_loss_rate()
        state.update_vital_signs()
        self.assertEqual(state.blood_level, 100.0)
        self.assertGreater(rate, 0.0)
