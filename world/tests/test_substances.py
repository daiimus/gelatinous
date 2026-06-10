"""Tests for the substance registry + effect pipeline (issue #458).

Pure-function coverage against fakes — no Evennia DB.  Pins:

* Registry lookups (known / unknown / None).
* ``pain_relief`` shaves PainCondition severity, bottoms at zero,
  no-ops on a pain-free consumer.
* ``sedation`` adds a sedative ConsciousnessSuppressionCondition,
  stacks onto an existing one, and respects the per-substance cap
  (including across repeated doses — the chain-smoking case).
* Dose bookkeeping increments ``db.substance_doses``.
* Vitals refresh + medical-state flush fire after application.
* ``CmdSmoke`` integration: a puff applies one dose and renders
  the feedback line only when an effect landed.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.substances import (
    SUBSTANCES,
    apply_substance,
    get_substance_entry,
)


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeCondition(SimpleNamespace):
    """Duck-typed condition — only the attributes the pipeline reads."""


def _pain(severity, location=None):
    return _FakeCondition(
        condition_type="pain", severity=severity, location=location,
    )


def _sedative(severity):
    return _FakeCondition(
        condition_type="consciousness_suppression",
        suppression_type="sedative",
        severity=severity,
        consciousness_penalty=min(1.0, severity * 0.15),
    )


class _FakeMedicalState:
    def __init__(self, conditions=None):
        self.conditions = list(conditions or [])
        self.vitals_updated = 0

    def add_condition(self, condition):
        self.conditions.append(condition)

    def update_vital_signs(self):
        self.vitals_updated += 1


class _FakeDB(SimpleNamespace):
    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return None


class _FakeConsumer:
    def __init__(self, conditions=None):
        self.medical_state = _FakeMedicalState(conditions)
        self.db = _FakeDB()
        self.saves = 0

    def save_medical_state(self):
        self.saves += 1


# ---------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------


class TestRegistry(TestCase):
    def test_known_substances_resolve(self):
        self.assertIsNotNone(get_substance_entry("tobacco_neutral"))
        self.assertIsNotNone(get_substance_entry("tobacco_noir"))

    def test_unknown_substance_returns_none(self):
        self.assertIsNone(get_substance_entry("unobtainium"))

    def test_none_returns_none(self):
        self.assertIsNone(get_substance_entry(None))
        self.assertIsNone(get_substance_entry(""))

    def test_entries_carry_flavor_bank_keys(self):
        for substance_id, entry in SUBSTANCES.items():
            self.assertEqual(entry.id, substance_id)
            self.assertTrue(entry.flavor_bank_key)


# ---------------------------------------------------------------------
# pain_relief
# ---------------------------------------------------------------------


class TestPainRelief(TestCase):
    def test_shaves_pain_severity(self):
        consumer = _FakeConsumer(conditions=[_pain(5)])
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(result["applied"], {"pain_relief": 1})
        self.assertEqual(consumer.medical_state.conditions[0].severity, 4)

    def test_no_ops_when_pain_free(self):
        consumer = _FakeConsumer()
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(result["applied"], {})
        self.assertEqual(result["feedback"], [])

    def test_bottoms_out_at_zero(self):
        consumer = _FakeConsumer(conditions=[_pain(1)])
        apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(consumer.medical_state.conditions[0].severity, 0)
        # Second dose has nothing to relieve.
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(result["applied"], {})

    def test_feedback_line_present_when_landed(self):
        consumer = _FakeConsumer(conditions=[_pain(3)])
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertTrue(result["feedback"])


# ---------------------------------------------------------------------
# sedation
# ---------------------------------------------------------------------


class TestSedation(TestCase):
    def test_first_dose_adds_sedative_condition(self):
        consumer = _FakeConsumer()
        result = apply_substance(consumer, "tobacco_noir")
        self.assertEqual(result["applied"].get("sedation"), 1)
        sedatives = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None)
            == "consciousness_suppression"
        ]
        self.assertEqual(len(sedatives), 1)
        self.assertEqual(sedatives[0].severity, 1)
        self.assertEqual(sedatives[0].suppression_type, "sedative")

    def test_second_dose_stacks_onto_existing(self):
        consumer = _FakeConsumer()
        apply_substance(consumer, "tobacco_noir")
        apply_substance(consumer, "tobacco_noir")
        sedatives = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None)
            == "consciousness_suppression"
        ]
        # Stacked in place — still one condition, severity 2.
        self.assertEqual(len(sedatives), 1)
        self.assertEqual(sedatives[0].severity, 2)

    def test_cap_blocks_third_dose(self):
        """tobacco_noir's sedation max_stack is 2 — the chain-
        smoking case.  Third puff relieves pain (if any) but adds
        no further sedation."""
        consumer = _FakeConsumer()
        apply_substance(consumer, "tobacco_noir")
        apply_substance(consumer, "tobacco_noir")
        result = apply_substance(consumer, "tobacco_noir")
        self.assertNotIn("sedation", result["applied"])
        sedatives = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None)
            == "consciousness_suppression"
        ]
        self.assertEqual(sedatives[0].severity, 2)

    def test_cap_shared_with_preexisting_sedatives(self):
        """The cap counts ALL sedative-typed suppression — a
        consumer already sedated to the cap gets nothing more."""
        consumer = _FakeConsumer(conditions=[_sedative(2)])
        result = apply_substance(consumer, "tobacco_noir")
        self.assertNotIn("sedation", result["applied"])

    def test_penalty_kept_in_sync_on_stack(self):
        consumer = _FakeConsumer()
        apply_substance(consumer, "tobacco_noir")
        apply_substance(consumer, "tobacco_noir")
        sedative = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None)
            == "consciousness_suppression"
        ][0]
        self.assertAlmostEqual(sedative.consciousness_penalty, 0.30)


# ---------------------------------------------------------------------
# Bookkeeping + lifecycle
# ---------------------------------------------------------------------


class TestBookkeeping(TestCase):
    def test_dose_counter_increments(self):
        consumer = _FakeConsumer()
        apply_substance(consumer, "tobacco_neutral")
        apply_substance(consumer, "tobacco_neutral")
        apply_substance(consumer, "tobacco_noir")
        self.assertEqual(
            consumer.db.substance_doses,
            {"tobacco_neutral": 2, "tobacco_noir": 1},
        )

    def test_vitals_and_save_fire_per_application(self):
        consumer = _FakeConsumer(conditions=[_pain(3)])
        apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(consumer.medical_state.vitals_updated, 1)
        self.assertEqual(consumer.saves, 1)

    def test_unknown_substance_no_ops_cleanly(self):
        consumer = _FakeConsumer(conditions=[_pain(3)])
        result = apply_substance(consumer, "unobtainium")
        self.assertFalse(result["known"])
        self.assertEqual(result["applied"], {})
        # No mutation, no save.
        self.assertEqual(consumer.medical_state.conditions[0].severity, 3)
        self.assertEqual(consumer.saves, 0)

    def test_consumer_without_medical_state_no_ops(self):
        consumer = SimpleNamespace(medical_state=None, db=_FakeDB())
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertTrue(result["known"])
        self.assertEqual(result["applied"], {})


# ---------------------------------------------------------------------
# CmdSmoke integration
# ---------------------------------------------------------------------


class TestCmdSmokeIntegration(TestCase):
    def _run_smoke(self, caller, args):
        from commands.CmdSmoke import CmdSmoke
        cmd = CmdSmoke()
        cmd.caller = caller
        cmd.args = " " + args
        with patch("commands.CmdSmoke.msg_room_identity"):
            cmd.func()

    def _smoking_caller(self, *, substance, conditions=None):
        from world import smoke as sm

        class _Tags:
            def __init__(self):
                self._t = set()

            def has(self, key, category=None):
                return (key, category) in self._t

            def add(self, key, category=None):
                self._t.add((key, category))

            def remove(self, key, category=None):
                self._t.discard((key, category))

        cig = SimpleNamespace(
            key="cigarette",
            aliases=[],
            tags=_Tags(),
            db=_FakeDB(substance=substance),
            attributes=SimpleNamespace(
                get=lambda k, d=None, _v={"uses_left": 6, "max_uses": 6}:
                    _v.get(k, d),
                add=lambda k, v: None,
            ),
        )
        cig.tags.add(sm.SMOKE_DELIVERY, category=sm.DELIVERY_METHOD_CATEGORY)
        cig.tags.add(sm.LIT_TAG, category=sm.CIGARETTE_STATE_CATEGORY)

        caller = _FakeConsumer(conditions=conditions)
        caller.location = SimpleNamespace(contents=[])
        caller.hands = {"left_hand": cig}
        caller.msgs = []
        caller.msg = lambda text: caller.msgs.append(text)
        caller.get_display_name = lambda looker=None: "Tester"
        return caller

    def test_puff_applies_dose_and_renders_feedback(self):
        caller = self._smoking_caller(
            substance="tobacco_neutral", conditions=[_pain(4)],
        )
        self._run_smoke(caller, "cigarette")
        # Pain shaved by one.
        self.assertEqual(caller.medical_state.conditions[0].severity, 3)
        # Dose recorded.
        self.assertEqual(
            caller.db.substance_doses, {"tobacco_neutral": 1},
        )
        # Feedback line rendered (colour-wrapped).
        joined = "\n".join(caller.msgs)
        self.assertIn("ache dulls", joined)

    def test_pain_free_puff_renders_no_feedback(self):
        caller = self._smoking_caller(substance="tobacco_neutral")
        self._run_smoke(caller, "cigarette")
        joined = "\n".join(caller.msgs)
        self.assertNotIn("ache dulls", joined)
        # Flavor message still arrived (something got rendered).
        self.assertTrue(caller.msgs)
