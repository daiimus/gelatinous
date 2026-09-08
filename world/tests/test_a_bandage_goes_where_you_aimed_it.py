"""A bandage treats the wound you named (#2502), and the death verdict
notices (#2504).

## #2502 — the body part was carried to the door and dropped

`bandage <body part> with <item>` resolves a location, prints prose
naming it, tells the room that part was bandaged, and passes the value
down two call layers:

```python
result_msg = self.execute_treatment(item, caller, target,
                                    body_location=self.body_location)
...
result_msg = apply_medical_effects(item, user, target, **kwargs)
```

`apply_medical_effects` accepted `**kwargs` and never read it — the word
appears exactly once in a 300-line function, on the signature. The
wound-care branch then treated whichever bleed was **first in list
order**, wherever on the body it happened to be:

```python
bleeding_conditions = [c for c in medical_state.conditions ...]
for condition in bleeding_conditions[:1]:
```

So a medic bandaging an arterial leg wound was told they had, while the
game quietly dressed a scratch on the arm.

An unmatched location falls back to every bleed rather than to none:
refusing to treat because the phrasing missed is worse than treating the
wrong arm, and the command has already told the player it is bandaging
them.

## #2504 — and the cached death verdict never heard about it

`is_dead()`'s own docstring claims invalidation "rides the
`Organ.current_hp` / `blood_level` setters and condition add/remove,
covering **every** input". Eight sites here removed conditions with a
bare `list.remove()` instead of `MedicalState.remove_condition`, which
is the door that calls `_invalidate_derived_state()` and
`condition.stop_condition()`.

Every severity edit in the function is an in-place mutation on the
condition object, which no setter observes — so nothing invalidated the
cache for the case where treatment *worked* but did not zero the
condition.

Then, forty lines further down, the same function reads the cache it
failed to invalidate. A patient could be treated back over the line and
still answer dead.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition, PainCondition
from world.medical.utils import apply_medical_effects


class _TreatCase(EvenniaTest):
    def bandage(self, quality="basic"):
        item = create_object("typeclasses.items.Item", key="a bandage",
                             location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.attributes.add("medical_type", "wound_care")
        item.attributes.add("uses_left", 5)
        item.attributes.add("quality", quality)
        return item

    def bleed(self, location, severity=6):
        condition = BleedingCondition(severity, location)
        self.char2.medical_state.add_condition(condition)
        return condition

    def treat(self, item, **kwargs):
        # Pin the roll so the assertion is about WHICH wound was
        # treated, not about how well.
        with mock.patch("world.medical.utils.calculate_treatment_success",
                        return_value={"success_level": "partial_success"}):
            return apply_medical_effects(item, self.char1, self.char2,
                                         **kwargs)


class TestTheNamedWoundIsTheOneTreated(_TreatCase):
    def test_the_named_leg_is_treated_not_the_first_arm(self):
        arm = self.bleed("left_arm")
        leg = self.bleed("right_leg")
        self.treat(self.bandage(), body_location="right_leg")
        self.assertEqual(arm.severity, 6, "it treated the wrong wound")
        self.assertLess(leg.severity, 6)

    def test_the_named_arm_is_treated_when_the_leg_is_first(self):
        leg = self.bleed("right_leg")
        arm = self.bleed("left_arm")
        self.treat(self.bandage(), body_location="left_arm")
        self.assertEqual(leg.severity, 6)
        self.assertLess(arm.severity, 6)

    def test_a_spaced_location_still_matches(self):
        """The command layer speaks "left arm"; the condition stores
        "left_arm"."""
        arm = self.bleed("left_arm")
        self.bleed("right_leg")
        self.treat(self.bandage(), body_location="left arm")
        self.assertLess(arm.severity, 6)

    def test_no_location_still_treats_something(self):
        arm = self.bleed("left_arm")
        self.treat(self.bandage())
        self.assertLess(arm.severity, 6)

    def test_an_unmatched_location_falls_back_rather_than_refusing(self):
        """Treating the wrong arm beats refusing over phrasing, and the
        command has already told the player it is bandaging them."""
        arm = self.bleed("left_arm")
        self.treat(self.bandage(), body_location="tail")
        self.assertLess(arm.severity, 6)

    def test_it_marks_the_treated_wound_treated(self):
        arm = self.bleed("left_arm")
        self.bleed("right_leg")
        self.treat(self.bandage(), body_location="left_arm")
        self.assertTrue(getattr(arm, "treated", False))


class TestTheCommandActuallyPassesIt(EvenniaTest):
    """Pinned at the seam: the value was plumbed all the way to the door
    and dropped there, so the plumbing is not the fragile part — the
    read is."""

    def test_the_function_reads_the_kwarg(self):
        import inspect
        from world.medical import utils
        body = inspect.getsource(utils.apply_medical_effects)
        self.assertIn('kwargs.get("body_location")', body)

    def test_the_command_still_sends_it(self):
        import inspect
        from commands import CmdConsumption
        body = inspect.getsource(CmdConsumption)
        self.assertIn("body_location=self.body_location", body)


class TestTheDeathVerdictNotices(_TreatCase):
    """Asserted as "the STALE answer is gone", not as "the cache is
    None": `apply_medical_effects` reads `is_dead()` itself further
    down, so a correct invalidation is immediately followed by a
    correct recompute. Checking for None passes against the bug on one
    path and fails on the other."""

    def state(self):
        return self.char2.medical_state

    def poison_the_cache(self):
        """What a bypassed removal leaves behind: a verdict computed
        before the treatment and never recomputed after it."""
        self.state()._cached_is_dead = True
        self.assertTrue(self.state().is_dead())

    def test_a_stale_dead_verdict_does_not_survive_a_treatment(self):
        self.bleed("left_arm", severity=1)
        self.poison_the_cache()
        self.treat(self.bandage())
        self.assertFalse(self.state().is_dead(),
                         "the patient still reads dead after treatment")

    def test_a_severity_reduction_clears_it_too(self):
        """The edit is an in-place mutation on the condition object,
        which no setter observes."""
        self.bleed("left_arm", severity=20)
        self.poison_the_cache()
        self.treat(self.bandage())
        self.assertFalse(self.state().is_dead())

    def test_pain_relief_clears_it(self):
        item = create_object("typeclasses.items.Item", key="a painkiller",
                             location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.attributes.add("medical_type", "pain_relief")
        item.attributes.add("uses_left", 3)
        self.state().add_condition(PainCondition(5, "left_arm"))
        self.poison_the_cache()
        apply_medical_effects(item, self.char1, self.char2)
        self.assertFalse(self.state().is_dead())

    def test_a_genuinely_dead_patient_still_reads_dead(self):
        """The invalidation must recompute, not just clear to False."""
        self.bleed("left_arm", severity=1)
        self.state().blood_level = 0.0
        self.treat(self.bandage())
        self.assertTrue(self.state().is_dead())

    def test_removal_goes_through_remove_condition(self):
        """The door, not the list. `remove_condition` is where the
        invalidation and the `stop_condition` hook live —
        `MedicalCondition` does not define `stop_condition`, so the
        hook is opt-in per subclass and calling the door is the only
        thing that would ever reach it."""
        self.bleed("left_arm", severity=1)
        with mock.patch.object(type(self.state()), "remove_condition") as rm:
            self.treat(self.bandage())
        rm.assert_called_once()

    def test_the_condition_is_actually_gone(self):
        condition = self.bleed("left_arm", severity=1)
        self.treat(self.bandage())
        self.assertNotIn(condition, self.state().conditions)


class TestNothingBypassesTheDoorAnyMore(EvenniaTest):
    def test_the_only_bare_remove_is_the_helpers_own_fallback(self):
        """Eight call sites went straight to the list. One bare remove
        survives on purpose — inside `_drop_condition`, for a state
        shape that has no `remove_condition` at all."""
        import inspect
        from world.medical import utils
        body = (utils.__file__ and
                open(utils.__file__, errors="ignore").read())
        self.assertEqual(body.count("medical_state.conditions.remove("), 1)
        self.assertIn("medical_state.conditions.remove(",
                      inspect.getsource(utils._drop_condition))
