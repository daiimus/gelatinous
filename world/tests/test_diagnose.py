"""Unit tests for :mod:`world.medical.diagnose` — the diagnose
pane that surfaces in the operate chart's PATIENT block.

Covers:

* :func:`classify_condition_rung` — bucket boundaries across
  blood / consciousness / pain / bleeders.
* :func:`wound_obfuscation_dc` — internal-cavity modifier applies
  to internal organs, skips surface organs.
* :func:`clinical_phrase` — injury-type + organ + stage combine
  into clinical noun phrases.
* :func:`perform_diagnose` — Intellect rolls, per-physician cache,
  TTL hit/miss, wound-signature invalidation.
* :func:`render_diagnose_lines` — renders rung + findings; only
  detected wounds appear.
"""
from __future__ import annotations

import time
from unittest import TestCase
from unittest.mock import patch

from world.medical import diagnose as dx


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------

class _DB:
    """Bare attribute holder mimicking ``obj.db``."""


class _FakeOrgan:
    def __init__(self, *, name, container, display_location=None,
                 wound_stage=None, injury_type=None):
        self.name = name
        self.container = container
        self.display_location = display_location or container
        self.wound_stage = wound_stage
        self.injury_type = injury_type


class _FakeCondition:
    def __init__(self, *, condition_type, location=None):
        self.condition_type = condition_type
        self.location = location


class _FakeState:
    def __init__(self, *, blood_level=100.0, consciousness=1.0,
                 pain_level=0.0, conditions=None, organs=None,
                 dead=False):
        self.blood_level = blood_level
        self.consciousness = consciousness
        self.pain_level = pain_level
        self.conditions = conditions or []
        self.organs = organs or {}
        self._dead = dead

    def is_dead(self):
        return self._dead


class _FakePatient:
    def __init__(self, *, state=None):
        self.medical_state = state
        self.db = _DB()


class _FakePhysician:
    def __init__(self, *, intellect=10, sleeve_uid="phys-1", obj_id=99):
        self.intellect = intellect
        self.db = _DB()
        self.db.sleeve_uid = sleeve_uid
        self.id = obj_id


# ---------------------------------------------------------------------
# Condition rung classifier
# ---------------------------------------------------------------------

class TestClassifyConditionRung(TestCase):
    def test_no_state_defaults_stable(self):
        patient = _FakePatient(state=None)
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_STABLE)

    def test_corpse_with_death_time_reports_deceased(self):
        """Corpses lack a ``medical_state`` but stamp ``death_time``
        on ``.db`` at creation — the classifier reads that as
        deceased rather than defaulting to stable."""
        patient = _FakePatient(state=None)
        patient.db.death_time = time.time() - 60
        self.assertEqual(
            dx.classify_condition_rung(patient), dx.RUNG_DECEASED,
        )

    def test_dead_short_circuits(self):
        patient = _FakePatient(state=_FakeState(dead=True))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_DECEASED)

    def test_healthy_baseline_stable(self):
        patient = _FakePatient(state=_FakeState())
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_STABLE)

    def test_minor_pain_tenuous(self):
        patient = _FakePatient(state=_FakeState(pain_level=20.0))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_TENUOUS)

    def test_blood_loss_serious(self):
        patient = _FakePatient(state=_FakeState(blood_level=70.0))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_SERIOUS)

    def test_single_bleeder_serious(self):
        patient = _FakePatient(state=_FakeState(conditions=[
            _FakeCondition(condition_type="minor_bleeding"),
        ]))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_SERIOUS)

    def test_two_bleeders_critical(self):
        patient = _FakePatient(state=_FakeState(conditions=[
            _FakeCondition(condition_type="minor_bleeding"),
            _FakeCondition(condition_type="minor_bleeding"),
        ]))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_CRITICAL)

    def test_severe_blood_loss_critical(self):
        patient = _FakePatient(state=_FakeState(blood_level=40.0))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_CRITICAL)

    def test_three_bleeders_moribund(self):
        patient = _FakePatient(state=_FakeState(conditions=[
            _FakeCondition(condition_type="minor_bleeding"),
            _FakeCondition(condition_type="minor_bleeding"),
            _FakeCondition(condition_type="minor_bleeding"),
        ]))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_MORIBUND)

    def test_consciousness_collapse_moribund(self):
        patient = _FakePatient(state=_FakeState(consciousness=0.1))
        self.assertEqual(dx.classify_condition_rung(patient), dx.RUNG_MORIBUND)


# ---------------------------------------------------------------------
# Obfuscation DC
# ---------------------------------------------------------------------

class TestWoundObfuscationDC(TestCase):
    def test_surface_organ_keeps_baseline(self):
        # Eye has display_location != container, so it's external.
        eye = _FakeOrgan(
            name="left_eye", container="head",
            display_location="left_eye",
            wound_stage="fresh", injury_type="cut",
        )
        self.assertEqual(dx.wound_obfuscation_dc(eye), 2)

    def test_internal_organ_bumps_dc(self):
        heart = _FakeOrgan(
            name="heart", container="chest",
            wound_stage="fresh", injury_type="bullet",
        )
        # bullet baseline 3 + internal mod 5 = 8.
        self.assertEqual(dx.wound_obfuscation_dc(heart), 8)

    def test_severance_auto_detects(self):
        limb = _FakeOrgan(
            name="left_arm", container="left_arm",
            wound_stage="severed", injury_type="severance",
        )
        # left_arm container not in internal containers → no bump.
        self.assertEqual(dx.wound_obfuscation_dc(limb), 0)

    def test_blunt_to_brain_high_dc(self):
        brain = _FakeOrgan(
            name="brain", container="head",
            wound_stage="fresh", injury_type="blunt",
        )
        # blunt 5 + internal 5 = 10.
        self.assertEqual(dx.wound_obfuscation_dc(brain), 10)


# ---------------------------------------------------------------------
# Clinical phrasing
# ---------------------------------------------------------------------

class TestClinicalPhrase(TestCase):
    def test_organ_specific_name_wins(self):
        heart = _FakeOrgan(
            name="heart", container="chest",
            wound_stage="fresh", injury_type="bullet",
        )
        phrase = dx.clinical_phrase(heart)
        self.assertIn("cardiac", phrase)
        self.assertIn("ballistic", phrase)
        self.assertIn("active", phrase)

    def test_container_region_fallback(self):
        # Bare-container injury (no specific-organ name match).
        shin = _FakeOrgan(
            name="left_tibia", container="left_shin",
            wound_stage="fresh", injury_type="laceration",
        )
        phrase = dx.clinical_phrase(shin)
        self.assertIn("left tibial", phrase)
        self.assertIn("laceration", phrase)

    def test_severance_reads_as_amputation(self):
        limb = _FakeOrgan(
            name="right_arm", container="right_arm",
            wound_stage="severed", injury_type="severance",
        )
        phrase = dx.clinical_phrase(limb)
        self.assertIn("amputation", phrase)

    def test_treated_prefix_applied(self):
        liver = _FakeOrgan(
            name="liver", container="abdomen",
            wound_stage="treated", injury_type="stab",
        )
        phrase = dx.clinical_phrase(liver)
        self.assertIn("stabilised", phrase)
        self.assertIn("hepatic", phrase)


# ---------------------------------------------------------------------
# perform_diagnose — roll + cache
# ---------------------------------------------------------------------

class TestPerformDiagnose(TestCase):
    def _patient_with_wounds(self):
        organs = {
            "heart": _FakeOrgan(
                name="heart", container="chest",
                wound_stage="fresh", injury_type="bullet",
            ),
            "left_eye": _FakeOrgan(
                name="left_eye", container="head",
                display_location="left_eye",
                wound_stage="fresh", injury_type="cut",
            ),
        }
        return _FakePatient(state=_FakeState(organs=organs))

    def test_all_rolls_succeed_with_high_intellect(self):
        patient = self._patient_with_wounds()
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            result = dx.perform_diagnose(physician, patient)
        self.assertFalse(result["from_cache"])
        self.assertEqual(
            set(result["detected_wounds"]), {"organ:heart", "organ:left_eye"},
        )

    def test_low_rolls_hide_internal_wound(self):
        patient = self._patient_with_wounds()
        physician = _FakePhysician()
        # Roll = 3 → beats cut DC 2 but loses to heart DC 8.
        with patch.object(dx, "roll_stat", return_value=3):
            result = dx.perform_diagnose(physician, patient)
        self.assertIn("organ:left_eye", result["detected_wounds"])
        self.assertNotIn("organ:heart", result["detected_wounds"])

    def test_cache_hit_within_ttl(self):
        patient = self._patient_with_wounds()
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            first = dx.perform_diagnose(physician, patient)
        with patch.object(dx, "roll_stat") as mocked:
            second = dx.perform_diagnose(physician, patient)
            mocked.assert_not_called()
        self.assertTrue(second["from_cache"])
        self.assertEqual(
            set(second["detected_wounds"]), set(first["detected_wounds"]),
        )

    def test_wound_signature_change_invalidates_cache(self):
        patient = self._patient_with_wounds()
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            first = dx.perform_diagnose(physician, patient)
        # New wound appears between calls.
        patient.medical_state.organs["liver"] = _FakeOrgan(
            name="liver", container="abdomen",
            wound_stage="fresh", injury_type="stab",
        )
        with patch.object(dx, "roll_stat", return_value=100):
            second = dx.perform_diagnose(physician, patient)
        self.assertFalse(second["from_cache"])
        self.assertIn("organ:liver", second["detected_wounds"])
        del first  # explicitly unused — clarifies intent

    def test_ttl_expiry_reroll(self):
        patient = self._patient_with_wounds()
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            dx.perform_diagnose(physician, patient)
        # Backdate the cache entry past TTL.
        cache_key = dx._physician_cache_key(physician)
        cache = patient.db.diagnose_cache
        entry = cache[cache_key]
        entry["timestamp"] = time.time() - dx.DIAGNOSE_CACHE_TTL_SECONDS - 1
        cache[cache_key] = entry
        with patch.object(dx, "roll_stat", return_value=100):
            second = dx.perform_diagnose(physician, patient)
        self.assertFalse(second["from_cache"])

    def test_separate_physicians_have_independent_cache(self):
        patient = self._patient_with_wounds()
        good = _FakePhysician(sleeve_uid="senior")
        novice = _FakePhysician(sleeve_uid="newbie")
        with patch.object(dx, "roll_stat", return_value=100):
            senior_result = dx.perform_diagnose(good, patient)
        # Novice's first call must trigger its own roll regardless.
        with patch.object(dx, "roll_stat", return_value=1) as mocked:
            novice_result = dx.perform_diagnose(novice, patient)
            self.assertTrue(mocked.called)
        self.assertFalse(novice_result["from_cache"])
        # Novice misses internal heart even though senior caught it.
        self.assertNotIn("organ:heart", novice_result["detected_wounds"])
        self.assertIn("organ:heart", senior_result["detected_wounds"])


# ---------------------------------------------------------------------
# render_diagnose_lines
# ---------------------------------------------------------------------

class TestRenderDiagnoseLines(TestCase):
    def test_renders_rung_and_findings(self):
        organs = {
            "heart": _FakeOrgan(
                name="heart", container="chest",
                wound_stage="fresh", injury_type="bullet",
            ),
        }
        patient = _FakePatient(state=_FakeState(
            blood_level=50.0, organs=organs,
        ))
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("critical", joined)   # blood_level 50 → critical
        self.assertIn("cardiac", joined)
        self.assertIn("ballistic", joined)

    def test_undetected_wound_hidden_in_render(self):
        organs = {
            "heart": _FakeOrgan(
                name="heart", container="chest",
                wound_stage="fresh", injury_type="bullet",
            ),
        }
        patient = _FakePatient(state=_FakeState(organs=organs))
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=1):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("no abnormalities detected", joined)
        self.assertNotIn("cardiac", joined)

    def test_render_without_cache_just_shows_rung(self):
        # No perform_diagnose call → renderer falls back to
        # rung-only output, doesn't crash.
        patient = _FakePatient(state=_FakeState())
        physician = _FakePhysician()
        lines = dx.render_diagnose_lines(physician, patient)
        self.assertTrue(any("condition" in l for l in lines))


# ---------------------------------------------------------------------
# Condition rendering
# ---------------------------------------------------------------------

class TestCorpseAndSeveredParts(TestCase):
    """Subjects without a live ``medical_state`` (corpses, severed
    heads, appendages) still surface a diagnose pane sourced from
    ``db.wounds_at_death``."""

    def _make_corpse(self, wounds):
        patient = _FakePatient(state=None)
        patient.db.death_time = time.time() - 60
        patient.db.wounds_at_death = wounds
        return patient

    def test_corpse_wounds_render_clinically(self):
        wounds = [
            {"injury_type": "bullet", "location": "chest",
             "stage": "old", "organ": "heart",
             "severity": "Critical", "organ_damage": {}},
            {"injury_type": "severance", "location": "neck",
             "stage": "old", "severity": "Critical"},
        ]
        patient = self._make_corpse(wounds)
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("deceased", joined)
        self.assertIn("cardiac", joined)
        self.assertIn("amputation", joined)

    def test_severed_head_with_brain_damage(self):
        """SeveredHead carries a trimmed wounds_at_death scoped to
        head-container findings."""
        wounds = [
            {"injury_type": "blunt", "location": "head",
             "stage": "old", "organ": "brain",
             "severity": "Critical", "organ_damage": {}},
        ]
        patient = self._make_corpse(wounds)
        physician = _FakePhysician(intellect=20)
        with patch.object(dx, "roll_stat", return_value=100):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("intracranial", joined)
        self.assertIn("blunt-force", joined)

    def test_low_roll_hides_corpse_finding(self):
        wounds = [
            {"injury_type": "bullet", "location": "chest",
             "stage": "old", "organ": "heart",
             "severity": "Critical", "organ_damage": {}},
        ]
        patient = self._make_corpse(wounds)
        physician = _FakePhysician()
        # Roll = 1 → loses to internal organ DC (3 + 5 = 8).
        with patch.object(dx, "roll_stat", return_value=1):
            result = dx.perform_diagnose(physician, patient)
        self.assertEqual(result["detected_wounds"], [])

    def test_harvested_organ_auto_detected(self):
        wounds = [
            {"injury_type": "harvested", "location": "heart",
             "stage": "old", "organ": "heart",
             "severity": "Critical", "organ_damage": {}},
        ]
        patient = self._make_corpse(wounds)
        physician = _FakePhysician()
        # DC 0 → any roll passes.
        with patch.object(dx, "roll_stat", return_value=1):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("surgical extraction", joined)


class TestConditionRendering(TestCase):
    def test_bleeding_condition_renders_clinically(self):
        patient = _FakePatient(state=_FakeState(
            conditions=[_FakeCondition(
                condition_type="minor_bleeding", location="chest",
            )],
        ))
        physician = _FakePhysician()
        with patch.object(dx, "roll_stat", return_value=100):
            dx.perform_diagnose(physician, patient)
        lines = dx.render_diagnose_lines(physician, patient)
        joined = "\n".join(lines)
        self.assertIn("haemorrhage", joined)
        self.assertIn("thoracic", joined)
