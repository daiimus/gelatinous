"""Phase 1 test contract for CONDITION_CADENCE_SPEC (issue #501).

Pins the guarantees of the elapsed-time rates refactor:

* equivalence — one process() spanning a minute behaves like one
  old-style 60s tick;
* granularity-independence — six 10s samples equal one 60s sample
  for continuous quantities, and hazards share one closed form;
* the downtime cap — a process() after long downtime applies at
  most ELAPSED_CAP_MINUTES of effect;
* restoration — infection runs at its documented pacing, not the
  5x drift;
* persistence — last_processed and dressing_progress round-trip.

Run via::

    evennia test --settings settings.py world.tests.test_condition_cadence
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.conditions import (
    BleedingCondition,
    InfectionCondition,
    PainCondition,
    deserialize_condition,
    hazard_fires,
)
from world.medical.constants import (
    ELAPSED_CAP_MINUTES,
    INFECTION_IMPROVE_HAZARD_PER_MINUTE,
    INFECTION_WORSEN_HAZARD_PER_MINUTE,
)
from world.medical.core import MedicalState


def _patient():
    state = MedicalState(character=None)
    target = SimpleNamespace(medical_state=state, key="cadence-test")
    return target, state


class TestHazardMath(TestCase):
    def test_zero_elapsed_never_fires(self):
        with patch("world.medical.conditions.random.random", return_value=0.0):
            self.assertFalse(hazard_fires(0.5, 0.0))

    def test_closed_form_is_cadence_independent(self):
        """P(fire over 1 min) sampled once == sampled in six 10s
        slices: 1-(1-p)^1 vs 1-((1-p)^(1/6))^6 — identical by
        construction; verify the boundary behavior numerically."""
        p = 0.10
        once = 1 - (1 - p) ** 1.0
        six = 1 - ((1 - p) ** (1 / 6)) ** 6
        self.assertAlmostEqual(once, six, places=12)

    def test_threshold_behavior(self):
        # Just under the fire threshold → fires; just over → doesn't.
        with patch("world.medical.conditions.random.random", return_value=0.0999):
            self.assertTrue(hazard_fires(0.10, 1.0))
        with patch("world.medical.conditions.random.random", return_value=0.1001):
            self.assertFalse(hazard_fires(0.10, 1.0))


class TestBleedingEquivalence(TestCase):
    def test_one_minute_equals_one_old_tick(self):
        """Severity 3 = 1.5 blood per old 60s tick; one process()
        spanning exactly one minute loses exactly that."""
        target, state = _patient()
        condition = BleedingCondition(3, "chest")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1060.0)  # +60s
        self.assertAlmostEqual(state.blood_level, 100.0 - 1.5)

    def test_six_small_samples_equal_one_big_sample(self):
        target_a, state_a = _patient()
        cond_a = BleedingCondition(3, "chest")
        state_a.add_condition(cond_a)
        cond_a.last_processed = 1000.0

        target_b, state_b = _patient()
        cond_b = BleedingCondition(3, "chest")
        state_b.add_condition(cond_b)
        cond_b.last_processed = 1000.0

        with patch("world.medical.conditions.random.random", return_value=0.99):
            cond_a.process(target_a, current=1060.0)
            for i in range(1, 7):
                cond_b.process(target_b, current=1000.0 + i * 10)

        self.assertAlmostEqual(state_a.blood_level, state_b.blood_level)

    # NOTE: the Phase-1 "treated truncation preserved" equivalence
    # test was superseded by the #507 design decision: treated now
    # means SLOWED (layered brakes), pinned by
    # TestBleedingModel.test_bandaged_wound_slows_to_thirty_percent.


class TestDowntimeCap(TestCase):
    def test_long_downtime_bills_at_most_the_cap(self):
        """A 30-minute gap (reload, crash) applies at most
        ELAPSED_CAP_MINUTES of bleeding."""
        target, state = _patient()
        condition = BleedingCondition(3, "chest")  # 1.5/min
        state.add_condition(condition)
        condition.last_processed = 1000.0
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1000.0 + 30 * 60)
        expected_loss = 1.5 * ELAPSED_CAP_MINUTES
        self.assertAlmostEqual(state.blood_level, 100.0 - expected_loss)

    def test_marker_still_advances_past_the_gap(self):
        """After a capped catch-up, the next normal tick is normal —
        the gap isn't re-billed."""
        target, state = _patient()
        condition = BleedingCondition(3, "chest")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1000.0 + 30 * 60)
            after_gap = state.blood_level
            condition.process(target, current=1000.0 + 30 * 60 + 60)
        self.assertAlmostEqual(state.blood_level, after_gap - 1.5)


class TestInfectionRestoration(TestCase):
    def test_documented_pacing_constants(self):
        """Treated ≈ 'improves every ~5 minutes' (30% over 5);
        untreated = the documented ~20-minute progression."""
        five_min = 1 - (1 - INFECTION_IMPROVE_HAZARD_PER_MINUTE) ** 5
        self.assertGreater(five_min, 0.25)
        self.assertLess(five_min, 0.35)
        self.assertAlmostEqual(1 / INFECTION_WORSEN_HAZARD_PER_MINUTE, 20.0)

    def test_environmental_modifier_scales_worsening(self):
        """The sewers lever: env modifier multiplies the hazard."""
        target, state = _patient()
        condition = InfectionCondition(2, "chest")
        condition.set_environmental_modifier(3.0)
        state.add_condition(condition)
        condition.last_processed = 1000.0
        # 0.05 * 3 = 0.15/min; roll just under that fires.
        with patch("world.medical.conditions.random.random", return_value=0.149):
            condition.process(target, current=1060.0)
        self.assertEqual(condition.severity, 3)


class TestPersistence(TestCase):
    def test_last_processed_round_trips(self):
        condition = PainCondition(4, "chest")
        condition.last_processed = 12345.0
        restored = deserialize_condition(condition.to_dict())
        self.assertEqual(restored.last_processed, 12345.0)

    def test_legacy_dict_defaults_to_now(self):
        """Pre-#501 persisted conditions lack last_processed — they
        must not be billed retroactively at upgrade."""
        condition = PainCondition(4, "chest")
        data = condition.to_dict()
        del data["last_processed"]
        before = __import__("time").time()
        restored = deserialize_condition(data)
        self.assertGreaterEqual(restored.last_processed, before - 1)


# ---------------------------------------------------------------------
# Bleeding model (#507): layered brakes, clot cap, live-derived rate
# ---------------------------------------------------------------------


class TestBleedingModel(TestCase):
    def test_bandaged_wound_slows_to_thirty_percent(self):
        """Layered brakes: treated = slowed, not stopped."""
        target, state = _patient()
        condition = BleedingCondition(4, "chest")  # 2.0/min
        condition.treated = True
        state.add_condition(condition)
        condition.last_processed = 1000.0
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1060.0)
        self.assertAlmostEqual(state.blood_level, 100.0 - 2.0 * 0.3)

    def test_arterial_bleeding_never_self_clots(self):
        """Severity 6+ has no natural resolution — intervention or
        death."""
        target, state = _patient()
        condition = BleedingCondition(7, "chest")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        # Roll that would always fire a hazard — but no hazard exists.
        with patch("world.medical.conditions.random.random", return_value=0.0):
            condition.process(target, current=1060.0)
        self.assertEqual(condition.severity, 7)

    def test_moderate_bleeding_can_clot(self):
        target, state = _patient()
        condition = BleedingCondition(5, "chest")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        with patch("world.medical.conditions.random.random", return_value=0.0):
            condition.process(target, current=1060.0)
        self.assertEqual(condition.severity, 4)

    def test_treated_wounds_clot_faster_and_resolve(self):
        """Bandaging doubles the clot hazard — slowed wounds have an
        endpoint, not a permanent leak."""
        target, state = _patient()
        condition = BleedingCondition(2, "chest")
        condition.treated = True
        state.add_condition(condition)
        condition.last_processed = 1000.0
        # 0.19 < 1-(1-0.20)^1 → fires only with the doubled hazard.
        with patch("world.medical.conditions.random.random", return_value=0.19):
            condition.process(target, current=1060.0)
        self.assertEqual(condition.severity, 1)

    def test_rate_follows_severity_not_creation(self):
        """The stale-rate bug: a clotted-down wound bleeds at its
        CURRENT severity's rate."""
        condition = BleedingCondition(5, "chest")  # created at 3.0/min
        condition.severity = 1
        self.assertAlmostEqual(condition.get_blood_loss_rate(), 0.5)

    def test_rename_with_legacy_alias(self):
        condition = BleedingCondition(9, "chest")
        self.assertEqual(condition.condition_type, "bleeding")
        self.assertEqual(condition.display_name, "catastrophic bleeding")
        # Legacy persisted saves load transparently.
        data = condition.to_dict()
        data["condition_type"] = "minor_bleeding"
        restored = deserialize_condition(data)
        self.assertEqual(restored.condition_type, "bleeding")
        self.assertEqual(restored.severity, 9)


# ---------------------------------------------------------------------
# Bandage roll + tourniquets (#509)
# ---------------------------------------------------------------------


class _FakeAttrs:
    """Dict-backed stand-in for Evennia's AttributeHandler."""

    def __init__(self, data):
        self._d = dict(data)

    def get(self, key, default=None):
        return self._d.get(key, default)

    def add(self, key, value):
        self._d[key] = value


class TestBandageRoll(TestCase):
    """#509: bandaging routes through the treatment roll and engages
    the #508 layered brakes (which previously had no caller)."""

    def _bandage(self, severity, success_level):
        from world.medical.utils import apply_medical_effects

        target, state = _patient()
        # The post-treatment revival check walks target.scripts.
        target.scripts = SimpleNamespace(get=lambda *a, **kw: [])
        condition = BleedingCondition(severity, "left_arm")
        state.add_condition(condition)
        item = SimpleNamespace(
            attributes=_FakeAttrs({"medical_type": "wound_care"}),
            key="test bandage",
        )
        user = SimpleNamespace(intellect=3, key="medic")
        with patch(
            "world.medical.utils.calculate_treatment_success",
            return_value={"success_level": success_level},
        ):
            apply_medical_effects(item, user, target)
        return state, condition

    def test_success_sutures_modest_wound_shut(self):
        """'Sutured for all intents and purposes': severity ≤4 closes
        outright and the condition is removed."""
        state, condition = self._bandage(4, "success")
        self.assertEqual(condition.severity, 0)
        self.assertNotIn(condition, state.conditions)

    def test_success_cannot_close_an_artery(self):
        """Heavy wounds (5+) take the -4 cut but stay open — a field
        bandage shrinks the problem, it doesn't shut an artery."""
        state, condition = self._bandage(8, "success")
        self.assertEqual(condition.severity, 4)
        self.assertTrue(condition.treated)
        self.assertIn(condition, state.conditions)

    def test_partial_success_reduces_two_and_treats(self):
        state, condition = self._bandage(5, "partial_success")
        self.assertEqual(condition.severity, 3)
        self.assertTrue(condition.treated)

    def test_failure_still_engages_the_brakes(self):
        """Even clumsy bandaging slows the wound: -1 severity and the
        treated flag (30% flow, doubled clot hazard) both land."""
        state, condition = self._bandage(5, "failure")
        self.assertEqual(condition.severity, 4)
        self.assertTrue(condition.treated)


class TestTourniquets(TestCase):
    """#509: limb-only instant full hold; not a fix."""

    def test_limb_gate(self):
        from world.medical.treatments import is_tourniquetable_location

        self.assertTrue(is_tourniquetable_location("left_arm"))
        self.assertTrue(is_tourniquetable_location("right_shin"))
        self.assertTrue(is_tourniquetable_location("tentacle_3"))
        self.assertFalse(is_tourniquetable_location("chest"))
        self.assertFalse(is_tourniquetable_location("neck"))
        self.assertFalse(is_tourniquetable_location("head"))

    def test_cannot_tourniquet_torso(self):
        from world.medical.treatments import apply_tourniquet

        target, state = _patient()
        outcome = apply_tourniquet(None, target, None, "chest")
        self.assertFalse(outcome["applied"])

    def test_holds_arterial_bleeding_completely(self):
        """The design point: a tourniquet stops ANY severity at a
        limb — the bleed that nothing else can touch in the field."""
        from world.medical.treatments import apply_tourniquet

        target, state = _patient()
        condition = BleedingCondition(7, "left_arm")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        outcome = apply_tourniquet(None, target, None, "left_arm")
        self.assertTrue(outcome["applied"])
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1060.0)
        self.assertEqual(state.blood_level, 100.0)
        self.assertEqual(condition.severity, 7)

    def test_no_clotting_under_a_tourniquet(self):
        """Flow is stopped, so nothing clots — severity is frozen,
        not improving.  Remove it untreated and the wound is exactly
        as bad as it was."""
        from world.medical.treatments import apply_tourniquet

        target, state = _patient()
        condition = BleedingCondition(3, "left_arm")
        state.add_condition(condition)
        condition.last_processed = 1000.0
        apply_tourniquet(None, target, None, "left_arm")
        # Roll 0.0 would clot a severity-3 wound — but not under the band.
        with patch("world.medical.conditions.random.random", return_value=0.0):
            condition.process(target, current=1060.0)
        self.assertEqual(condition.severity, 3)
        self.assertEqual(state.blood_level, 100.0)

    def test_removal_resumes_bleeding(self):
        from world.medical.treatments import apply_tourniquet, clear_tourniquet

        target, state = _patient()
        condition = BleedingCondition(4, "left_arm")  # 2.0/min
        state.add_condition(condition)
        condition.last_processed = 1000.0
        apply_tourniquet(None, target, None, "left_arm")
        with patch("world.medical.conditions.random.random", return_value=0.99):
            condition.process(target, current=1060.0)
            self.assertEqual(state.blood_level, 100.0)
            self.assertTrue(clear_tourniquet(target, "left_arm"))
            condition.process(target, current=1120.0)
        self.assertAlmostEqual(state.blood_level, 100.0 - 2.0)

    def test_dressing_supersedes_tourniquet(self):
        """Proper wound care at the location clears the band — the
        dressing holds the wound, so the tourniquet comes off."""
        from world.medical.treatments import apply_wound_care

        target, state = _patient()
        organ = next(
            o for o in state.organs.values() if o.container == "left_arm"
        )
        organ.current_hp = organ.max_hp - 5
        organ.tourniqueted = True
        actor = SimpleNamespace(intellect=3, motorics=3, key="medic")
        item = SimpleNamespace(
            attributes=_FakeAttrs({"effectiveness": {}, "uses_left": 2}),
            key="dressing",
        )
        outcome = apply_wound_care(
            actor=actor, target=target, item=item, location="left_arm",
        )
        self.assertTrue(outcome["stabilized"])
        self.assertFalse(organ.tourniqueted)
        self.assertTrue(organ.stabilized)

    def test_tourniquet_flag_round_trips(self):
        from world.medical.core import Organ

        organ = Organ("left_humerus")
        organ.tourniqueted = True
        restored = Organ.from_dict(organ.to_dict())
        self.assertTrue(restored.tourniqueted)
        # Legacy snapshots without the field default to False.
        data = organ.to_dict()
        del data["tourniqueted"]
        self.assertFalse(Organ.from_dict(data).tourniqueted)
