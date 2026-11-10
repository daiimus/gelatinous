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
  the feedback line only when an effect landed.  That one class runs
  on real objects (a real character and cigarette), since the command
  names the cigarette through ``caller.search`` (#3783).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

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

    def test_entries_are_keyed_by_their_own_id(self):
        for substance_id, entry in SUBSTANCES.items():
            self.assertEqual(entry.id, substance_id)

    def test_there_is_no_flavor_bank_key(self):
        """It was set by all seven substances and read by nothing. Every
        value was IDENTICAL to the substance's own id, and three of the
        seven named a bank that does not exist -- so editing it did
        nothing, invisibly. The pickers key off the id (#2767)."""
        for entry in SUBSTANCES.values():
            self.assertFalse(hasattr(entry, "flavor_bank_key"))


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


class TestCmdSmokeIntegration(EvenniaCommandTest):
    """A real lit cigarette in a real hand, puffed through the real
    ``smoke`` command: the dose lands on the smoker's own medical state.
    Rebuilt on real objects for #3783: the command now names the
    cigarette through ``caller.search``, which a fake caller lacks."""

    def setUp(self):
        super().setUp()
        patcher = patch("commands.CmdSmoke.msg_room_identity")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _smoke(self, args):
        from commands.CmdSmoke import CmdSmoke
        return self.call(CmdSmoke(), args, caller=self.char1)

    def _lit_cigarette(self, *, substance):
        from evennia import create_object
        from world import smoke as sm

        cig = create_object("typeclasses.items.Item", key="cigarette",
                            location=self.char1)
        cig.tags.add(sm.SMOKE_DELIVERY, category=sm.DELIVERY_METHOD_CATEGORY)
        cig.db.substance = substance
        cig.db.uses_left = 6
        cig.db.max_uses = 6
        sm.set_lit(cig, True)
        self.char1.wield_item(cig, hand="left")
        self.assertIs(self.char1.hands["left_hand"], cig)
        return cig

    def _pains(self):
        return [c for c in self.char1.medical_state.conditions
                if c.condition_type == "pain"]

    def test_puff_applies_dose_and_renders_feedback(self):
        from world.medical.conditions import PainCondition

        self._lit_cigarette(substance="tobacco_neutral")
        self.char1.medical_state.add_condition(PainCondition(4, location=None))
        out = self._smoke("cigarette")
        # Pain shaved by one.
        self.assertEqual([c.severity for c in self._pains()], [3])
        # Dose recorded.
        self.assertEqual(
            dict(self.char1.db.substance_doses), {"tobacco_neutral": 1},
        )
        # Feedback line rendered (colour stripped by self.call).
        self.assertIn("ache dulls", out)

    def test_pain_free_puff_renders_no_feedback(self):
        self._lit_cigarette(substance="tobacco_neutral")
        self.assertEqual(self._pains(), [])
        out = self._smoke("cigarette")
        self.assertNotIn("ache dulls", out)
        # Flavor message still arrived (something got rendered).
        self.assertTrue(out.strip())


# ---------------------------------------------------------------------
# Tolerance (#485) — lazy-decay points shave per-dose magnitude
# ---------------------------------------------------------------------


class TestTolerance(TestCase):
    def _hooked_consumer(self, points, updated_offset_hours=0.0):
        import time as _time
        consumer = _FakeConsumer(conditions=[_pain(5)])
        consumer.db.substance_tolerance = {
            "tobacco_neutral": {
                "points": points,
                "updated": _time.time() - updated_offset_hours * 3600,
            },
        }
        return consumer

    def test_fresh_consumer_gets_full_effect(self):
        consumer = _FakeConsumer(conditions=[_pain(5)])
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(result["applied"].get("pain_relief"), 1)

    def test_tolerance_level_blunts_effect_with_feedback(self):
        """15+ standing points = level 1 = tobacco's magnitude-1
        pain relief reduced to zero, with the 'doesn't hit like it
        used to' line."""
        from world.substances.registry import TOLERANCE_FEEDBACK

        consumer = self._hooked_consumer(points=20.0)
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertNotIn("pain_relief", result["applied"])
        self.assertIn(TOLERANCE_FEEDBACK, result["feedback"])
        # Pain untouched.
        self.assertEqual(consumer.medical_state.conditions[0].severity, 5)

    def test_tolerance_decays_with_time(self):
        """20 points last updated 40 hours ago at 0.5/hour decay →
        0 standing points → full effect again."""
        consumer = self._hooked_consumer(points=20.0, updated_offset_hours=40)
        result = apply_substance(consumer, "tobacco_neutral")
        self.assertEqual(result["applied"].get("pain_relief"), 1)

    def test_doses_accrue_tolerance_points(self):
        consumer = _FakeConsumer(conditions=[_pain(5)])
        apply_substance(consumer, "tobacco_neutral")
        apply_substance(consumer, "tobacco_neutral")
        entry = consumer.db.substance_tolerance["tobacco_neutral"]
        # Two points minus the sliver of lazy decay between doses.
        self.assertGreater(entry["points"], 1.9)


# ---------------------------------------------------------------------
# Addiction (#485, flavor-first)
# ---------------------------------------------------------------------


class TestAddiction(TestCase):
    def _consumer_with_history(self, lifetime):
        consumer = _FakeConsumer(conditions=[_pain(3)])
        consumer.db.substance_doses = {"tobacco_neutral": lifetime}
        return consumer

    def test_below_threshold_no_condition(self):
        consumer = self._consumer_with_history(5)
        apply_substance(consumer, "tobacco_neutral")
        kinds = [
            getattr(c, "condition_type", None)
            for c in consumer.medical_state.conditions
        ]
        self.assertNotIn("addiction", kinds)

    def test_crossing_threshold_forms_addiction_once(self):
        from world.substances.registry import ADDICTION_ONSET_FEEDBACK

        consumer = self._consumer_with_history(29)  # threshold 30
        result = apply_substance(consumer, "tobacco_neutral")
        addictions = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "addiction"
        ]
        self.assertEqual(len(addictions), 1)
        self.assertEqual(addictions[0].substance_id, "tobacco_neutral")
        self.assertEqual(addictions[0].prose_key, "tobacco")
        self.assertIn(ADDICTION_ONSET_FEEDBACK, result["feedback"])

        # Dosing again refreshes the habit instead of stacking a
        # second condition.
        before = addictions[0].last_dose_time
        import time as _time
        addictions[0].last_dose_time = before - 999
        apply_substance(consumer, "tobacco_neutral")
        addictions_after = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "addiction"
        ]
        self.assertEqual(len(addictions_after), 1)
        self.assertGreater(addictions_after[0].last_dose_time, before - 999)


class TestAddictionCondition(TestCase):
    def _overdue(self, condition):
        condition.last_dose_time -= condition.craving_after + 1

    def test_dormant_while_fed(self):
        from world.medical.conditions import AddictionCondition

        condition = AddictionCondition("tobacco_neutral", prose_key="tobacco")
        self.assertFalse(condition.is_craving())
        self.assertEqual(condition.get_pain_contribution(), 0)
        self.assertFalse(condition.should_end())

    def test_overdue_craving_aches_and_speaks(self):
        from unittest.mock import MagicMock
        from world.medical.conditions import AddictionCondition

        condition = AddictionCondition("tobacco_neutral", prose_key="tobacco")
        self._overdue(condition)
        self.assertEqual(condition.get_pain_contribution(), 1)

        character = MagicMock()
        condition.tick_effect(character)  # first overdue tick → prose
        character.msg.assert_called_once()
        character.msg.reset_mock()
        condition.tick_effect(character)  # tick 2 of 5 → quiet
        character.msg.assert_not_called()

    def test_dose_resets_craving(self):
        from world.medical.conditions import AddictionCondition

        condition = AddictionCondition("tobacco_neutral")
        self._overdue(condition)
        condition.record_dose()
        self.assertFalse(condition.is_craving())
        self.assertEqual(condition.get_pain_contribution(), 0)

    def test_serialization_round_trip(self):
        from world.medical.conditions import (
            AddictionCondition, deserialize_condition,
        )

        condition = AddictionCondition(
            "tobacco_noir", prose_key="tobacco", craving_after=1234,
        )
        condition.last_dose_time = 1000.0
        restored = deserialize_condition(condition.to_dict())
        self.assertIsInstance(restored, AddictionCondition)
        self.assertEqual(restored.substance_id, "tobacco_noir")
        self.assertEqual(restored.craving_after, 1234)
        self.assertEqual(restored.last_dose_time, 1000.0)
        self.assertFalse(restored.should_end())


# ---------------------------------------------------------------------
# Cannabis / alcohol / opium (#487)
# ---------------------------------------------------------------------


class TestNewSubstances(TestCase):
    def test_entries_resolve_with_specs(self):
        for sid in ("cannabis", "alcohol", "opium"):
            entry = get_substance_entry(sid)
            self.assertIsNotNone(entry, sid)
            self.assertIsNotNone(entry.tolerance, sid)
            self.assertIsNotNone(entry.addiction, sid)
            # Every addiction prose key has a craving bank.
            from world.substances.registry import CRAVING_PROSE
            self.assertIn(entry.addiction.prose_key, CRAVING_PROSE)

    def test_opium_is_the_serious_analgesic(self):
        consumer = _FakeConsumer(conditions=[_pain(5)])
        result = apply_substance(consumer, "opium")
        self.assertEqual(result["applied"]["pain_relief"], 3)
        self.assertEqual(consumer.medical_state.conditions[0].severity, 2)
        self.assertEqual(result["applied"]["sedation"], 2)

    def test_alcohol_sedation_caps_at_properly_drunk(self):
        """Six shots: sedative severity climbs to the cap of 4
        (0.60 consciousness penalty — drunk, standing) and stops."""
        consumer = _FakeConsumer()
        for _ in range(6):
            apply_substance(consumer, "alcohol")
        sedatives = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "consciousness_suppression"
        ]
        total = sum(int(c.severity) for c in sedatives)
        self.assertEqual(total, 4)

    def test_opium_hooks_fast(self):
        """Ten doses is all it takes."""
        consumer = _FakeConsumer(conditions=[_pain(3)])
        consumer.db.substance_doses = {"opium": 9}
        apply_substance(consumer, "opium")
        addictions = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "addiction"
        ]
        self.assertEqual(len(addictions), 1)
        self.assertEqual(addictions[0].prose_key, "opium")


# ---------------------------------------------------------------------
# Delivery wiring (#487): eat/drink/inhale carry pharmacology
# ---------------------------------------------------------------------


class TestDeliveryWiring(TestCase):
    def _drink_cmd(self, item, target):
        from unittest.mock import MagicMock
        from commands.CmdConsumption import CmdDrink

        cmd = CmdDrink()
        cmd.caller = MagicMock()
        cmd.caller.location = MagicMock()
        cmd.args = "rotgut"
        parse_result = {
            "item": item, "target": target,
            "body_location": None, "errors": [],
        }
        return cmd, parse_result

    def test_drink_applies_dose_and_spends_a_use(self):
        from unittest.mock import MagicMock, patch

        item = MagicMock()
        item.db = _FakeDB(substance="alcohol")
        item.key = "bottle of rotgut"
        item.get_display_name = lambda looker=None: "bottle of rotgut"
        target = MagicMock()
        cmd, parse_result = self._drink_cmd(item, target)
        # Drinking yourself: target is the caller.
        target = cmd.caller
        parse_result["target"] = target

        with patch.object(cmd, "get_item_and_target",
                          return_value=parse_result), \
             patch("commands.CmdConsumption.supports_delivery",
                   return_value=True), \
             patch("commands.CmdConsumption.is_medical_item",
                   return_value=False), \
             patch("commands.CmdConsumption.msg_room_identity"), \
             patch("world.substances.apply_substance",
                   return_value={"feedback": ["The room tilts agreeably."]}
                   ) as mock_dose, \
             patch("world.consumables.consume_use",
                   return_value={"success": True, "destroyed": False}
                   ) as mock_use:
            cmd.func()

        mock_dose.assert_called_once_with(target, "alcohol")
        mock_use.assert_called_once_with(item)
        item.delete.assert_not_called()
        sent = " ".join(
            str(c.args[0]) for c in target.msg.call_args_list if c.args
        )
        self.assertIn("The room tilts agreeably.", sent)

    def test_untracked_item_consumed_whole(self):
        """Items without uses_left tracking fall back to full
        deletion (legacy regular-food behavior preserved)."""
        from unittest.mock import MagicMock, patch

        item = MagicMock()
        item.db = _FakeDB()  # no substance, no uses
        item.key = "mystery snack"
        item.get_display_name = lambda looker=None: "mystery snack"
        cmd, parse_result = self._drink_cmd(item, None)
        parse_result["target"] = cmd.caller

        with patch.object(cmd, "get_item_and_target",
                          return_value=parse_result), \
             patch("commands.CmdConsumption.supports_delivery",
                   return_value=True), \
             patch("commands.CmdConsumption.is_medical_item",
                   return_value=False), \
             patch("commands.CmdConsumption.msg_room_identity"), \
             patch("world.consumables.consume_use",
                   return_value={"success": False, "destroyed": False}):
            cmd.func()

        item.delete.assert_called_once()


# ---------------------------------------------------------------------
# Guttervenom + pain_inflict (#498) — the first harmful substance
# ---------------------------------------------------------------------


class TestGuttervenom(TestCase):
    def test_entry_is_weapon_not_habit(self):
        entry = get_substance_entry("guttervenom")
        self.assertIsNotNone(entry)
        self.assertIsNone(entry.tolerance)
        self.assertIsNone(entry.addiction)

    def test_dose_inflicts_pain_and_dims(self):
        consumer = _FakeConsumer()
        result = apply_substance(consumer, "guttervenom")
        self.assertEqual(result["applied"]["pain_inflict"], 3)
        self.assertEqual(result["applied"]["sedation"], 1)
        pains = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "pain"
        ]
        self.assertEqual(len(pains), 1)
        self.assertEqual(pains[0].severity, 3)
        self.assertIn(
            "Fire spreads outward from the injection site.",
            result["feedback"],
        )

    def test_repeat_doses_stack_pain_but_cap_sedation(self):
        consumer = _FakeConsumer()
        for _ in range(4):
            apply_substance(consumer, "guttervenom")
        pains = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "pain"
        ]
        self.assertEqual(sum(c.severity for c in pains), 12)
        sedatives = [
            c for c in consumer.medical_state.conditions
            if getattr(c, "condition_type", None) == "consciousness_suppression"
        ]
        self.assertEqual(sum(int(c.severity) for c in sedatives), 3)


class TestInjectDeliveryWiring(TestCase):
    """#498 completes the #488 wiring: inject carries pharmacology
    and accepts tag-gated non-medical syringes."""

    def test_inject_applies_dose_and_spends_a_use(self):
        from unittest.mock import MagicMock, patch
        from commands.CmdConsumption import CmdInject

        item = MagicMock()
        item.db = _FakeDB(substance="guttervenom")
        item.get_display_name = lambda looker=None: "syringe of guttervenom"
        cmd = CmdInject()
        cmd.caller = MagicMock()
        cmd.caller.location = MagicMock()
        cmd.args = "guttervenom"
        target = cmd.caller
        parse_result = {
            "item": item, "target": target,
            "body_location": None, "errors": [],
        }
        with patch.object(cmd, "get_item_and_target",
                          return_value=parse_result) as mock_parse, \
             patch("commands.CmdConsumption.supports_delivery",
                   return_value=True), \
             patch("commands.CmdConsumption.is_medical_item",
                   return_value=False), \
             patch("commands.CmdConsumption.msg_room_identity"), \
             patch("world.substances.apply_substance",
                   return_value={"feedback": ["Fire."]}) as mock_dose, \
             patch("world.consumables.consume_use",
                   return_value={"success": True, "destroyed": True}
                   ) as mock_use:
            cmd.func()

        # Tag-gated: the parser no longer demands a medical item.
        self.assertFalse(mock_parse.call_args.kwargs.get("require_medical", True))
        mock_dose.assert_called_once_with(target, "guttervenom")
        mock_use.assert_called_once_with(item)
