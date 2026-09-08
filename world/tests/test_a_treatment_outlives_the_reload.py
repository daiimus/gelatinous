"""A treatment is written down, and a drug acts through the model
(#2503, #2505).

## #2503 — treatment was the asymmetric half

Nothing `apply_medical_effects` did was ever written to the database. It
mutates condition severities, `treated` flags, `organ.stabilized`,
`organ.dressing_rate` and blood level — all on the in-memory
`MedicalState` — and never called `save_medical_state`. Neither did its
callers, nor `remove_condition`, nor the medical script's tick.

**Combat damage does save.** `armor_mixin.take_damage` calls
`save_medical_state` right after `apply_anatomical_damage`. So damage
persisted and treatment did not: bandage a bleed from severity 6 down to
2, reload before anything else medical happens, and the character comes
back at 6 with `treated = False` — the treatment and the item spent on
it both gone.

It closed only opportunistically. The next `add_condition` or
organ-damage save writes the whole current `to_dict()`, so a player who
happened to get shot afterwards inadvertently persisted their earlier
bandaging. Whether a treatment survived a reload depended on whether
something unrelated hurt you in the meantime.

## #2505 — the drugs wrote to a whiteboard that gets wiped

Nine writes across seven branches set `pain_level` and `consciousness`
directly. Those are **derived aggregates**. `update_vital_signs` does
not adjust them, it rebuilds them:

```python
self.pain_level = self.calculate_total_pain()      # a pure sum over conditions
self.consciousness = max(0.0, base - pain - blood - suppression)
```

Neither expression has any memory of a prior value, so every offset a
drug wrote was discarded on the next tick — or immediately, if the
patient took a hit, because `apply_anatomical_damage` calls
`update_vital_signs` too.

The consequence that matters beyond flavour: **an anesthetic produced
one message and no sedation.** `procedures.py` gives conscious patients
a difficulty modifier and accumulates pain during procedures, so
"anaesthetise the patient first" is a play the system advertises and did
not support.

Both channels already existed. The `pain_relief` branch reduces pain
*conditions*, which is exactly what `calculate_total_pain` sums, and
`ConsciousnessSuppressionCondition.get_consciousness_penalty()` is
explicitly summed by `update_vital_signs`.

**The numbers carry over unchanged.**
`PainCondition.get_pain_contribution()` returns `self.severity` exactly,
so a point of pain is a point of severity and no new balance was
invented here. The sedation depth is the one judgement call: the old
write was −0.10 consciousness and the condition's penalty is
`severity * 0.15`, so severity 1 is the nearest supported value.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import (BleedingCondition,
                                      ConsciousnessSuppressionCondition,
                                      PainCondition)
from world.medical.utils import apply_medical_effects


class _DrugCase(EvenniaTest):
    def med(self, medical_type, key=None):
        item = create_object("typeclasses.items.Item",
                             key=key or f"a {medical_type}",
                             location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.attributes.add("medical_type", medical_type)
        item.attributes.add("uses_left", 5)
        return item

    def state(self):
        return self.char2.medical_state

    def pain(self, severity, location="chest"):
        condition = PainCondition(severity, location)
        self.state().add_condition(condition)
        return condition

    def apply(self, item):
        return apply_medical_effects(item, self.char1, self.char2)

    def tick(self):
        """What erased the old offsets: a plain vitals rebuild."""
        self.state().update_vital_signs()


class TestAnAnaestheticSurvivesTheTick(_DrugCase):
    def test_the_pain_relief_survives_repeated_rebuilds(self):
        """`pain_level` starts at 0.0 until something computes it, so
        the baseline has to be taken AFTER the first rebuild — reading
        it before compares against an uninitialised aggregate."""
        self.pain(30)
        self.apply(self.med("anesthetic"))
        self.tick()
        after_one = self.state().pain_level
        self.tick()
        self.tick()
        self.assertEqual(self.state().pain_level, after_one)

    def test_it_actually_relieved_pain(self):
        self.pain(30)
        self.apply(self.med("anesthetic"))
        self.tick()
        self.assertEqual(self.state().pain_level, 5)

    def test_the_sedation_survives(self):
        self.pain(10)
        self.apply(self.med("anesthetic"))
        self.tick()
        awake = self.state().consciousness
        self.assertLess(awake, 1.0, "the patient was not sedated at all")

    def test_the_sedation_is_a_condition_that_can_wear_off(self):
        self.apply(self.med("anesthetic"))
        kinds = [getattr(c, "condition_type", None)
                 for c in self.state().conditions]
        self.assertIn("consciousness_suppression", kinds)

    def test_it_does_not_relieve_pain_it_cannot_reach(self):
        """A bleed contributes pain too, but an analgesic does not close
        a wound."""
        bleed = BleedingCondition(8, "chest")
        self.state().add_condition(bleed)
        self.apply(self.med("anesthetic"))
        self.assertEqual(bleed.severity, 8)


class TestTheOtherDrugsToo(_DrugCase):
    def test_a_medicinal_herb_relieves_pain_that_sticks(self):
        self.pain(20)
        self.apply(self.med("herb"))
        self.tick()
        self.assertEqual(self.state().pain_level, 5)

    def test_a_cigarette_relieves_less(self):
        self.pain(20)
        self.apply(self.med("cigarette"))
        self.tick()
        self.assertEqual(self.state().pain_level, 12)

    def test_a_vapor_relieves_ten(self):
        self.pain(20)
        self.apply(self.med("vapor"))
        self.tick()
        self.assertEqual(self.state().pain_level, 10)

    def test_dried_medicine_relieves_twelve(self):
        self.pain(20)
        self.apply(self.med("dried_medicine"))
        self.tick()
        self.assertEqual(self.state().pain_level, 8)

    def test_relief_cannot_go_below_zero(self):
        self.pain(3)
        self.apply(self.med("anesthetic"))
        self.tick()
        self.assertEqual(self.state().pain_level, 0)

    def test_a_patient_with_no_pain_is_not_harmed(self):
        self.apply(self.med("herb"))     # must not raise
        self.tick()
        self.assertEqual(self.state().pain_level, 0)


class TestOxygenLiftsWhatItCanLift(_DrugCase):
    def test_oxygen_eases_sedation(self):
        self.state().add_condition(
            ConsciousnessSuppressionCondition(3, suppression_type="anesthesia"))
        self.tick()
        under = self.state().consciousness
        self.apply(self.med("oxygen"))
        self.tick()
        self.assertGreater(self.state().consciousness, under)

    def test_and_the_lift_survives_the_tick(self):
        self.state().add_condition(
            ConsciousnessSuppressionCondition(3, suppression_type="anesthesia"))
        self.apply(self.med("oxygen"))
        self.tick()
        first = self.state().consciousness
        self.tick()
        self.assertEqual(self.state().consciousness, first)

    def test_an_unsuppressed_patient_is_unchanged(self):
        """Consciousness is derived; there is no "boost" term, and
        inventing one would be new balance."""
        self.tick()
        before = self.state().consciousness
        self.apply(self.med("oxygen"))
        self.tick()
        self.assertEqual(self.state().consciousness, before)


class TestNoBranchWritesTheAggregates(EvenniaTest):
    def test_the_derived_values_are_never_assigned(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "world" / "medical" / "utils.py").read_text(
            errors="ignore")
        self.assertNotIn("medical_state.pain_level = ", body)
        self.assertNotIn("medical_state.consciousness = ", body)


class TestTheTreatmentIsWrittenDown(_DrugCase):
    def bandage(self):
        item = self.med("wound_care", key="a bandage")
        item.attributes.add("quality", "basic")
        return item

    def stored_conditions(self):
        raw = self.char2.attributes.get("medical_state") or {}
        return raw.get("conditions") or []

    def test_a_bandaged_bleed_reaches_the_database(self):
        bleed = BleedingCondition(6, "left_arm")
        self.state().add_condition(bleed)
        with mock.patch("world.medical.utils.calculate_treatment_success",
                        return_value={"success_level": "partial_success"}):
            self.apply(self.bandage())
        stored = [c for c in self.stored_conditions()
                  if c.get("condition_type") == "bleeding"]
        self.assertEqual(stored[0]["severity"], bleed.severity)
        self.assertLess(stored[0]["severity"], 6)

    def test_the_treated_flag_reaches_the_database(self):
        self.state().add_condition(BleedingCondition(6, "left_arm"))
        with mock.patch("world.medical.utils.calculate_treatment_success",
                        return_value={"success_level": "partial_success"}):
            self.apply(self.bandage())
        stored = [c for c in self.stored_conditions()
                  if c.get("condition_type") == "bleeding"]
        self.assertTrue(stored[0].get("treated"))

    def test_a_splint_reaches_the_database(self):
        bone = next(o for o in self.state().organs.values()
                    if o.data.get("bone_type"))
        bone.current_hp = max(1, bone.max_hp - 5)
        self.char2.save_medical_state()
        self.apply(self.med("fracture_treatment", key="a splint"))
        raw = self.char2.attributes.get("medical_state") or {}
        stored = {o.get("name"): o for o in (raw.get("organs") or {}).values()}
        self.assertTrue(stored[bone.name].get("stabilized"),
                        "the splint lived in memory only")

    def test_the_anaesthetic_reaches_the_database(self):
        self.pain(30)
        self.apply(self.med("anesthetic"))
        kinds = [c.get("condition_type") for c in self.stored_conditions()]
        self.assertIn("consciousness_suppression", kinds)
