"""Tests for the surgical procedure pipeline (#307 follow-up).

Covers:

* ``world.medical.procedures`` — the dispatch module that the four
  procedure verbs route through.
* Multi-source organ accessor (``get_organ_snapshot``) — works on
  living, corpse, severed.
* Incision state lifecycle (open / close / multi-incision / lookup).
* Skill roll formula (intellect * 0.75 + motorics * 0.25) and
  difficulty modifiers for consciousness state.
* Resolver outcomes for each verb (success / partial / failure
  branches) including failure consequences (collateral damage,
  infection seed).

The procedure verbs use ``evennia.utils.delay`` to stage resolution
asynchronously.  Tests substitute a synchronous shim so the
resolver runs in-line and side effects are observable immediately.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.procedures import (
    ANESTHETIZED_DIFFICULTY_BONUS,
    CONSCIOUS_PATIENT_DIFFICULTY,
    PROCEDURE_BASE_DIFFICULTY,
    calculate_procedure_difficulty,
    calculate_procedure_skill,
    close_all_incisions,
    close_incision,
    get_organ_snapshot,
    has_incision,
    open_incision,
    open_incision_locations,
    organs_at_location,
    roll_procedure,
    seed_infection,
    seed_pain,
)
from world.medical.core import MedicalState


def _human_character(intellect=2, motorics=2, conscious=True):
    """Plain-Python stub character with the surfaces the procedure
    pipeline touches.

    The ``intellect`` / ``motorics`` values land on the bare object
    (not ``db``) because that's where ``calculate_procedure_skill``
    reads them — matching the AttributeProperty access pattern on
    real Characters.
    """
    char = SimpleNamespace()
    char.intellect = intellect
    char.motorics = motorics
    char.is_unconscious = lambda: not conscious
    # ``db.surgical_state`` is touched by the state helpers; provide
    # the slot.  ``db.archived`` for MedicalState init paths.
    char.db = SimpleNamespace(
        species="human", archived=False, surgical_state=None,
        removed_organs=None, severed_locations=None,
    )
    char.key = "TestSubject"
    char.medical_state = MedicalState(char)
    return char


def _corpse_target():
    """Minimal corpse-shaped stub exposing get_medical_snapshot."""
    snapshot = {
        "organs": {
            "heart": {
                "container": "chest", "current_hp": 15, "max_hp": 15,
                "conditions": [],
            },
            "left_lung": {
                "container": "chest", "current_hp": 20, "max_hp": 20,
                "conditions": [],
            },
            "left_humerus": {
                "container": "left_arm", "current_hp": 25, "max_hp": 25,
                "conditions": [],
            },
        },
    }
    corpse = SimpleNamespace()
    corpse.get_medical_snapshot = lambda: snapshot
    corpse.db = SimpleNamespace(
        surgical_state=None,
        removed_organs=None, severed_locations=None,
        species="human",
    )
    corpse.key = "the corpse"
    return corpse


# ---------------------------------------------------------------------
# Organ snapshot accessor
# ---------------------------------------------------------------------


class GetOrganSnapshot(TestCase):

    def test_living_character_snapshot(self):
        char = _human_character()
        snap = get_organ_snapshot(char)
        organs = snap.get("organs") or {}
        # Spot-check a few human organs.
        for must in ("brain", "heart", "left_lung", "left_humerus"):
            with self.subTest(organ=must):
                self.assertIn(must, organs)

    def test_corpse_snapshot(self):
        corpse = _corpse_target()
        snap = get_organ_snapshot(corpse)
        organs = snap.get("organs") or {}
        self.assertIn("heart", organs)

    def test_object_with_no_snapshot_returns_empty(self):
        # A plain object with neither medical_state nor get_medical_snapshot.
        target = SimpleNamespace()
        self.assertEqual(get_organ_snapshot(target), {})


class OrgansAtLocation(TestCase):

    def test_living_chest_organs(self):
        char = _human_character()
        results = organs_at_location(char, "chest")
        names = [n for n, _ in results]
        self.assertIn("heart", names)
        self.assertIn("left_lung", names)
        # Brain is NOT at chest.
        self.assertNotIn("brain", names)

    def test_sensory_organ_at_display_location(self):
        # left_eye has container="head" and display_location="left_eye"
        # — the helper should match both.
        char = _human_character()
        at_eye = [n for n, _ in organs_at_location(char, "left_eye")]
        self.assertIn("left_eye", at_eye)
        at_head = [n for n, _ in organs_at_location(char, "head")]
        # left_eye container is head → also matches "head" lookup.
        self.assertIn("left_eye", at_head)


# ---------------------------------------------------------------------
# Incision state
# ---------------------------------------------------------------------


class IncisionLifecycle(TestCase):

    def test_open_then_check(self):
        char = _human_character()
        open_incision(char, "chest", surgeon=char)
        self.assertTrue(has_incision(char, "chest"))

    def test_close_clears(self):
        char = _human_character()
        open_incision(char, "chest", surgeon=char)
        closed = close_incision(char, "chest")
        self.assertTrue(closed)
        self.assertFalse(has_incision(char, "chest"))

    def test_close_nothing_returns_false(self):
        char = _human_character()
        self.assertFalse(close_incision(char, "chest"))

    def test_multiple_incisions_allowed(self):
        char = _human_character()
        open_incision(char, "chest", surgeon=char)
        open_incision(char, "abdomen", surgeon=char)
        locs = open_incision_locations(char)
        self.assertEqual(set(locs), {"chest", "abdomen"})

    def test_close_all_returns_list(self):
        char = _human_character()
        open_incision(char, "chest", surgeon=char)
        open_incision(char, "abdomen", surgeon=char)
        closed = close_all_incisions(char)
        self.assertEqual(set(closed), {"chest", "abdomen"})
        self.assertEqual(open_incision_locations(char), [])


# ---------------------------------------------------------------------
# Skill formula (spec line 1434)
# ---------------------------------------------------------------------


class SkillRoll(TestCase):

    def test_skill_formula(self):
        actor = _human_character(intellect=4, motorics=2)
        # 4*0.75 + 2*0.25 = 3.0 + 0.5 = 3.5
        self.assertAlmostEqual(calculate_procedure_skill(actor), 3.5)

    def test_default_when_stats_missing(self):
        actor = SimpleNamespace()  # no intellect / motorics
        # Both default to 1; 1*0.75 + 1*0.25 = 1.0
        self.assertAlmostEqual(calculate_procedure_skill(actor), 1.0)


class Difficulty(TestCase):

    def test_conscious_patient_harder(self):
        char = _human_character(conscious=True)
        diff = calculate_procedure_difficulty(char)
        self.assertEqual(
            diff, PROCEDURE_BASE_DIFFICULTY + CONSCIOUS_PATIENT_DIFFICULTY,
        )

    def test_unconscious_patient_easier(self):
        char = _human_character(conscious=False)
        diff = calculate_procedure_difficulty(char)
        self.assertEqual(
            diff, PROCEDURE_BASE_DIFFICULTY - ANESTHETIZED_DIFFICULTY_BONUS,
        )

    def test_conscious_modifier_off(self):
        char = _human_character(conscious=True)
        diff = calculate_procedure_difficulty(char, conscious_modifier=False)
        self.assertEqual(diff, PROCEDURE_BASE_DIFFICULTY)


# ---------------------------------------------------------------------
# Roll mechanics — patches RNG so outcomes are deterministic
# ---------------------------------------------------------------------


class RollOutcomes(TestCase):

    def setUp(self):
        # Unconscious target → difficulty = 12 - 3 = 9.
        # Skill = (3*0.75) + (1*0.25) = 2.5.
        # So total = roll + 2.5; need roll ≥ 11.5 for partial, ≥ 16.5 for success.
        self.actor = _human_character(intellect=3, motorics=1)
        self.target = _human_character(conscious=False)

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_high_roll_is_success(self, _r):
        # roll = 6+6+6 = 18, total = 20.5, difficulty = 9, ≥ 14 → success
        result = roll_procedure(self.actor, self.target)
        self.assertEqual(result["outcome"], "success")

    @patch("world.medical.procedures.random.randint", return_value=3)
    def test_mid_roll_is_partial(self, _r):
        # roll = 9, total = 11.5, difficulty = 9, < 14 but ≥ 9 → partial
        result = roll_procedure(self.actor, self.target)
        self.assertEqual(result["outcome"], "partial")

    @patch("world.medical.procedures.random.randint", return_value=1)
    def test_low_roll_is_failure(self, _r):
        # roll = 3, total = 5.5, < 9 → failure
        result = roll_procedure(self.actor, self.target)
        self.assertEqual(result["outcome"], "failure")


# ---------------------------------------------------------------------
# Failure consequence helpers
# ---------------------------------------------------------------------


class SeedInfection(TestCase):

    def test_seeds_location_bound_infection_on_living(self):
        char = _human_character()
        seed_infection(char, "chest", severity=3)
        from world.medical.conditions import InfectionCondition
        infections = [
            c for c in char.medical_state.conditions
            if isinstance(c, InfectionCondition)
        ]
        self.assertEqual(len(infections), 1)
        self.assertEqual(infections[0].location, "chest")
        self.assertEqual(infections[0].severity, 3)

    def test_no_op_on_corpse(self):
        corpse = _corpse_target()
        # Corpses don't have medical_state.conditions; should no-op.
        seed_infection(corpse, "chest", severity=3)
        # No exceptions; no state changed.


class SeedPain(TestCase):

    def test_conscious_patient_gets_pain(self):
        char = _human_character(conscious=True)
        seed_pain(char, "chest", severity=4)
        from world.medical.conditions import PainCondition
        pains = [
            c for c in char.medical_state.conditions
            if isinstance(c, PainCondition)
        ]
        self.assertEqual(len(pains), 1)
        self.assertEqual(pains[0].severity, 4)

    def test_unconscious_patient_no_pain(self):
        char = _human_character(conscious=False)
        seed_pain(char, "chest", severity=4)
        from world.medical.conditions import PainCondition
        pains = [
            c for c in char.medical_state.conditions
            if isinstance(c, PainCondition)
        ]
        self.assertEqual(pains, [])


# ---------------------------------------------------------------------
# INTERNAL_CONTAINERS contract
# ---------------------------------------------------------------------


class IncisionRequiredHelper(TestCase):
    """Contract for ``CmdSurgical._incision_required``: organs with a
    distinct ``display_location`` are surface-accessible (no incision
    needed); organs whose display_location falls back to their
    container live inside and need it opened first.

    This is the canonical rule settled in the #307 design pass —
    eyes / ears / nose / tongue / jaw on humans bypass; brain /
    heart / kidneys / etc. require incision.  Applies symmetrically
    to harvest and install via the same helper.
    """

    def _organ_data(self, container, display_location=None):
        """Build a snapshot-shaped organ entry."""
        return {
            "container": container,
            "display_location": display_location or container,
        }

    def test_surface_organ_with_distinct_display_skips_incision(self):
        from commands.CmdSurgical import _incision_required
        # left_eye: container=head, display_location=left_eye → distinct.
        eye = self._organ_data("head", "left_eye")
        self.assertFalse(_incision_required(eye))

    def test_face_organ_skips_incision(self):
        """tongue / jaw / nose share display_location=face on humans."""
        from commands.CmdSurgical import _incision_required
        for organ in ("tongue", "jaw", "nose"):
            with self.subTest(organ=organ):
                data = self._organ_data("head", "face")
                self.assertFalse(_incision_required(data))

    def test_buried_organ_requires_incision(self):
        from commands.CmdSurgical import _incision_required
        # brain: container=head, no distinct display_location.
        brain = self._organ_data("head")
        self.assertTrue(_incision_required(brain))

    def test_chest_organ_requires_incision(self):
        from commands.CmdSurgical import _incision_required
        heart = self._organ_data("chest")
        self.assertTrue(_incision_required(heart))

    def test_limb_bone_requires_incision(self):
        """Limbs are not internal-cavity but their bones are still
        buried inside the limb — incision required to harvest the
        humerus from inside an arm, attached or severed."""
        from commands.CmdSurgical import _incision_required
        humerus = self._organ_data("left_arm")
        self.assertTrue(_incision_required(humerus))

    def test_explicit_display_equal_to_container_still_requires(self):
        """Defensive: even if the snapshot redundantly stores
        display_location equal to container, the rule still
        requires incision (matches the Organ default behaviour)."""
        from commands.CmdSurgical import _incision_required
        data = {"container": "chest", "display_location": "chest"}
        self.assertTrue(_incision_required(data))

    def test_missing_display_falls_back_to_container(self):
        """Snapshot without display_location key at all → fall back
        to container → incision required (safe default)."""
        from commands.CmdSurgical import _incision_required
        data = {"container": "abdomen"}
        self.assertTrue(_incision_required(data))


# ---------------------------------------------------------------------
# Verb resolvers (in-process via _resolve_procedure_callback shim)
# ---------------------------------------------------------------------


class ResolveIncise(TestCase):
    """Tests for the ``_resolve_incise`` resolver (success / partial
    / failure branches) — calls the resolver directly rather than
    routing through the delay system, so outcomes are observable
    synchronously."""

    def setUp(self):
        # Skill 3 (int 3, mot 3) → 3.0; unconscious target → diff 9.
        # Roll outcomes:
        #  roll = 18 (6+6+6) → total 21 → success
        #  roll = 9  (3+3+3) → total 12 → partial
        #  roll = 3  (1+1+1) → total 6  → failure
        self.actor = _human_character(intellect=3, motorics=3)
        self.target = _human_character(conscious=False)
        self.actor.location = None
        self.target.location = None
        # ``location_utils`` calls need both to have ``msg``; stubs.
        self.actor.msg = lambda *a, **k: None
        self.target.msg = lambda *a, **k: None

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_success_opens_incision(self, _r):
        from world.medical.procedures import _resolve_incise
        _resolve_incise(self.actor, self.target, location="chest")
        self.assertTrue(has_incision(self.target, "chest"))

    @patch("world.medical.procedures.random.randint", return_value=3)
    def test_partial_opens_incision_with_collateral(self, _r):
        from world.medical.procedures import _resolve_incise
        heart_hp_before = self.target.medical_state.organs["heart"].current_hp
        _resolve_incise(self.actor, self.target, location="chest")
        self.assertTrue(has_incision(self.target, "chest"))
        heart_hp_after = self.target.medical_state.organs["heart"].current_hp
        # Collateral damage applied to at least one chest organ.
        chest_organs_damaged = any(
            self.target.medical_state.organs[name].current_hp < self.target.medical_state.organs[name].max_hp
            for name in ("heart", "left_lung", "right_lung")
        )
        self.assertTrue(chest_organs_damaged)

    @patch("world.medical.procedures.random.randint", return_value=1)
    def test_failure_seeds_infection_no_incision(self, _r):
        from world.medical.procedures import _resolve_incise
        _resolve_incise(self.actor, self.target, location="chest")
        self.assertFalse(has_incision(self.target, "chest"))
        # Infection seeded.
        from world.medical.conditions import InfectionCondition
        infections = [
            c for c in self.target.medical_state.conditions
            if isinstance(c, InfectionCondition) and c.location == "chest"
        ]
        self.assertEqual(len(infections), 1)


class ResolveSuture(TestCase):
    """Tests for ``_resolve_suture``: must consume existing incisions
    and produce per-outcome side effects."""

    def setUp(self):
        self.actor = _human_character(intellect=3, motorics=3)
        self.target = _human_character(conscious=False)
        self.actor.location = None
        self.target.location = None
        self.actor.msg = lambda *a, **k: None
        self.target.msg = lambda *a, **k: None

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_success_closes_all_incisions(self, _r):
        from world.medical.procedures import _resolve_suture
        open_incision(self.target, "chest", surgeon=self.actor)
        open_incision(self.target, "abdomen", surgeon=self.actor)
        _resolve_suture(self.actor, self.target)
        self.assertEqual(open_incision_locations(self.target), [])

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_success_with_location_closes_one(self, _r):
        from world.medical.procedures import _resolve_suture
        open_incision(self.target, "chest", surgeon=self.actor)
        open_incision(self.target, "abdomen", surgeon=self.actor)
        _resolve_suture(self.actor, self.target, location="chest")
        self.assertEqual(open_incision_locations(self.target), ["abdomen"])

    @patch("world.medical.procedures.random.randint", return_value=1)
    def test_failure_seeds_infection_but_still_closes(self, _r):
        # Per design: botched suture closes but seeds infection.  The
        # wound is "closed" but dirty.
        from world.medical.procedures import _resolve_suture
        open_incision(self.target, "chest", surgeon=self.actor)
        _resolve_suture(self.actor, self.target)
        self.assertEqual(open_incision_locations(self.target), [])
        from world.medical.conditions import InfectionCondition
        infections = [
            c for c in self.target.medical_state.conditions
            if isinstance(c, InfectionCondition) and c.location == "chest"
        ]
        self.assertEqual(len(infections), 1)


# ---------------------------------------------------------------------
# _mark_organ_removed — wounds_at_death synthesis (legacy CmdHarvest
# behavior ported here when the forensics command was retired).  The
# wound-at-death entry is what test_sever_overlay and test_wound_
# descriptions_harvested rely on for the ``harvested`` injury type.
# ---------------------------------------------------------------------


class MarkOrganRemovedWoundSynthesis(TestCase):

    def _corpse_with_death_state(self):
        snapshot = {
            "organs": {
                "heart": {
                    "container": "chest", "current_hp": 15, "max_hp": 15,
                    "conditions": [],
                },
                "left_eye": {
                    "container": "head", "current_hp": 5, "max_hp": 5,
                    "conditions": [],
                },
            },
        }
        corpse = SimpleNamespace()
        corpse.get_medical_snapshot = lambda: snapshot
        corpse.db = SimpleNamespace(
            surgical_state=None,
            removed_organs=None, severed_locations=None,
            species="human",
            medical_state_at_death=snapshot,
            wounds_at_death=None,
        )
        corpse.key = "the corpse"
        return corpse

    def test_corpse_gets_harvested_wound_at_container(self):
        from world.medical.procedures import _mark_organ_removed
        corpse = self._corpse_with_death_state()
        _mark_organ_removed(corpse, "heart")
        wounds = corpse.db.wounds_at_death or []
        self.assertEqual(len(wounds), 1)
        wound = wounds[0]
        self.assertEqual(wound["injury_type"], "harvested")
        self.assertEqual(wound["location"], "chest")
        self.assertEqual(wound["organ"], "heart")
        self.assertEqual(wound["stage"], "old")

    def test_eye_harvest_locates_wound_at_head_container(self):
        # Eye container is head — wound rides on the head so PR #200's
        # sever-overlay carries it onto a severed head.
        from world.medical.procedures import _mark_organ_removed
        corpse = self._corpse_with_death_state()
        _mark_organ_removed(corpse, "left_eye")
        wound = (corpse.db.wounds_at_death or [])[0]
        self.assertEqual(wound["location"], "head")
        self.assertEqual(wound["organ"], "left_eye")

    def test_living_target_skips_wounds_at_death(self):
        char = _human_character()
        # No medical_state_at_death on the live char.
        from world.medical.procedures import _mark_organ_removed
        _mark_organ_removed(char, "left_kidney")
        # Living characters don't carry wounds_at_death.
        self.assertFalse(
            getattr(char.db, "wounds_at_death", None),
            "Living target should not receive a wounds_at_death entry.",
        )

    def test_preserves_existing_wounds_at_death(self):
        from world.medical.procedures import _mark_organ_removed
        corpse = self._corpse_with_death_state()
        corpse.db.wounds_at_death = [
            {"injury_type": "blunt", "location": "chest", "severity": "Minor"},
        ]
        _mark_organ_removed(corpse, "heart")
        wounds = corpse.db.wounds_at_death or []
        self.assertEqual(len(wounds), 2)
        self.assertEqual(wounds[0]["injury_type"], "blunt")
        self.assertEqual(wounds[1]["injury_type"], "harvested")
