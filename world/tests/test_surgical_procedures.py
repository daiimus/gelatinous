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
    INTERNAL_CONTAINERS,
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


class InternalContainersSet(TestCase):
    """Internal containers require incision before deep procedures
    can target organs housed there.  This pins the membership."""

    def test_known_internal(self):
        for loc in ("head", "chest", "abdomen", "back", "neck", "groin"):
            with self.subTest(loc=loc):
                self.assertIn(loc, INTERNAL_CONTAINERS)

    def test_limbs_external(self):
        for loc in ("left_arm", "right_arm", "left_hand", "right_hand",
                    "left_thigh", "left_shin", "left_foot"):
            with self.subTest(loc=loc):
                self.assertNotIn(loc, INTERNAL_CONTAINERS)


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
