"""Pain grades consciousness down, and wound care grades against its own
target (#2501, #2500).

## #2501 — a cliff two pain points wide

`PAIN_CONSCIOUSNESS_MODIFIER` is authored on the 0–100 **pain** scale
and was multiplied straight into a 0.0–1.0 **consciousness** value:

```python
pain_penalty = (self.pain_level - PAIN_UNCONSCIOUS_THRESHOLD) * PAIN_CONSCIOUSNESS_MODIFIER
blood_penalty = max(0.0, (100.0 - self.blood_level) / 100.0)     # <- normalises
```

So with a base of 1.0: lucid at pain 80, exactly at the unconsciousness
line at 81.4, floored at 82. Not a curve — a cliff.

Every sibling term in that expression is already 0–1. `blood_penalty`
normalises explicitly on the very next line;
`ConsciousnessSuppressionCondition` defaults to 0.15; renal failure caps
at 0.6 with a comment reading *"can't alone instantly zero
consciousness"*. Pain was the sole outlier, and the one that could zero
it in two points.

Divided at the point of use rather than re-authoring the constant to
0.005 — that keeps the knob's stated meaning ("half of the excess
pain") on the scale it is written in, and puts the conversion where the
sibling conversion already is.

```
pain  80 -> 1.00      pain 140 -> 0.70
pain 100 -> 0.90      pain 180 -> 0.50
```

Whether that magnitude is right is a balance question. The units were
not.

## #2500 — a difficulty computed, threaded, and ignored

`roll_treatment` took `target_difficulty`, compared `total` to two fixed
module constants, and echoed the argument back in the result dict
unread. So the whole wound-care chain — base + severity ladder +
internal-depth modifier — was computed by
`calculate_treatment_difficulty`, threaded through `apply_wound_care`,
passed in, and used for nothing. **Every wound graded at 18**, regardless
of how bad it was or how deep.

`constants.py` states the intended math in its own header:

    target = WOUND_CARE_BASE_DIFFICULTY + severity_modifier + depth_modifier

The partial band keeps the spread the two thresholds already encode
(18 − 12 = 6), so no new number is invented: the relationship comes from
the file, and the file calls the magnitudes *"placeholders for early
playtesting"*.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.medical.constants import (PAIN_CONSCIOUSNESS_MODIFIER,
                                     PAIN_UNCONSCIOUS_THRESHOLD,
                                     WOUND_CARE_BASE_DIFFICULTY,
                                     WOUND_CARE_PARTIAL_THRESHOLD,
                                     WOUND_CARE_SUCCESS_THRESHOLD)
from world.medical.treatments import (calculate_treatment_difficulty,
                                      roll_treatment)


class _PainCase(EvenniaTest):
    def awake_at(self, pain):
        state = self.char2.medical_state
        state.pain_level = pain
        state.update_vital_signs()
        return state.consciousness

    def pain_of(self, level):
        """Set the pain by ADDING conditions, so `update_vital_signs`
        rebuilds to it instead of discarding the value."""
        from world.medical.conditions import PainCondition
        state = self.char2.medical_state
        state.add_condition(PainCondition(level, "chest"))
        state.update_vital_signs()
        return state


class TestPainIsGraded(_PainCase):
    def test_at_the_threshold_you_are_fully_awake(self):
        state = self.pain_of(PAIN_UNCONSCIOUS_THRESHOLD)
        self.assertAlmostEqual(state.consciousness, 1.0)

    def test_two_points_over_does_not_floor_you(self):
        """The cliff: 82 used to be consciousness 0.0."""
        state = self.pain_of(PAIN_UNCONSCIOUS_THRESHOLD + 2)
        self.assertGreater(state.consciousness, 0.9)

    def test_it_declines_monotonically(self):
        """Computed from the expression rather than by re-running
        setUp inside a test — calling setUp again mid-test rebuilds
        fixtures the harness already owns."""
        state = self.char2.medical_state
        seen = []
        for level in (80, 100, 140, 180, 220):
            state.conditions = [c for c in state.conditions
                                if getattr(c, "condition_type", None) != "pain"]
            self.pain_of(level)
            seen.append(state.consciousness)
        self.assertEqual(seen, sorted(seen, reverse=True))
        self.assertLess(seen[-1], seen[0])

    def test_there_is_a_drowsy_band_at_all(self):
        """Awake but impaired — the thing a two-point cliff cannot
        express."""
        state = self.pain_of(140)
        self.assertLess(state.consciousness, 1.0)
        self.assertFalse(state.is_unconscious())

    def test_enough_pain_still_puts_you_under(self):
        state = self.pain_of(300)
        self.assertTrue(state.is_unconscious())

    def test_the_penalty_is_on_the_consciousness_scale(self):
        """Every sibling term in that expression is 0-1."""
        excess = 20
        penalty = excess * PAIN_CONSCIOUSNESS_MODIFIER / 100.0
        self.assertLess(penalty, 1.0)


class TestTheOtherTermsStillWork(_PainCase):
    def test_blood_loss_still_costs_consciousness(self):
        state = self.char2.medical_state
        state.blood_level = 50.0
        state.update_vital_signs()
        self.assertLess(state.consciousness, 1.0)

    def test_a_healthy_body_is_fully_conscious(self):
        state = self.char2.medical_state
        state.update_vital_signs()
        self.assertAlmostEqual(state.consciousness, 1.0)


class TestWoundCareGradesAgainstItsTarget(EvenniaTest):
    def roll(self, difficulty, dice_total, skill=0, rating=0):
        with mock.patch("world.medical.treatments.random.randint",
                        return_value=dice_total // 3), \
             mock.patch("world.medical.treatments.calculate_treatment_skill",
                        return_value=skill):
            return roll_treatment(self.char1, difficulty, rating)

    def test_the_target_is_actually_read(self):
        """15 total against an easy wound succeeds; against a hard one
        it does not. Under the old code both graded at 18."""
        easy = self.roll(12, 15)["outcome"]
        hard = self.roll(26, 15)["outcome"]
        self.assertNotEqual(easy, hard)

    def test_a_minor_external_wound_is_easier_than_flat_eighteen(self):
        self.assertEqual(self.roll(12, 15)["outcome"], "success")

    def test_a_critical_internal_wound_is_harder(self):
        self.assertEqual(self.roll(26, 15)["outcome"], "failure")

    def test_the_partial_band_keeps_the_spread_the_constants_encode(self):
        band = WOUND_CARE_SUCCESS_THRESHOLD - WOUND_CARE_PARTIAL_THRESHOLD
        difficulty = 18
        self.assertEqual(self.roll(difficulty, difficulty - 1)["outcome"],
                         "partial")
        self.assertEqual(
            self.roll(difficulty, difficulty - band - 1)["outcome"],
            "failure")

    def test_the_echoed_target_still_matches_what_was_graded(self):
        result = self.roll(21, 15)
        self.assertEqual(result["target"], 21)

    def test_the_ladder_it_reads_is_the_documented_one(self):
        self.assertEqual(
            calculate_treatment_difficulty(wound_severity="Minor",
                                           item_internal_effective=False,
                                           is_internal_wound=False),
            WOUND_CARE_BASE_DIFFICULTY)
        self.assertGreater(
            calculate_treatment_difficulty(wound_severity="Critical",
                                           item_internal_effective=False,
                                           is_internal_wound=True),
            calculate_treatment_difficulty(wound_severity="Minor",
                                           item_internal_effective=False,
                                           is_internal_wound=False))

    def test_a_station_bonus_still_helps(self):
        plain = self.roll(21, 15)
        self.assertEqual(plain["station_bonus"], 0)
        self.assertEqual(plain["outcome"], "partial")
