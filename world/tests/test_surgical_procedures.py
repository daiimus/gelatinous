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

    def test_corpse_with_empty_live_state_falls_through_to_snapshot(self):
        """Regression: a corpse can expose ``medical_state`` through
        Evennia's attribute resolution but with an empty ``organs``
        dict (the live state was transferred to
        ``medical_state_at_death`` at death time).  Without the
        ``getattr(..., "organs", None)`` truthiness guard, the live
        branch returned ``{"organs": {}}`` and the procedure verbs
        saw a corpse as having no anatomy.

        Reproduces the 2026-06-05 playtest report where
        ``incise corpse at abdomen`` rejected with "nothing at
        abdomen" despite the autopsy showing intact liver/kidney/
        stomach in the snapshot.
        """
        # Build a corpse stub that surfaces BOTH paths: an empty
        # live medical_state AND a populated death-time snapshot.
        snapshot = {
            "organs": {
                "liver": {
                    "container": "abdomen",
                    "display_location": "abdomen",
                    "current_hp": 20, "max_hp": 20, "conditions": [],
                },
            },
        }
        corpse = SimpleNamespace()
        empty_state = SimpleNamespace(organs={})
        corpse.medical_state = empty_state
        corpse.get_medical_snapshot = lambda: snapshot
        snap = get_organ_snapshot(corpse)
        self.assertIn("liver", snap.get("organs") or {})

    def test_living_with_populated_state_takes_live_path(self):
        """Counter-test: a living character with populated organs
        still uses the live medical_state path (not the
        get_medical_snapshot fallback).  Pins the gate condition."""
        char = _human_character()
        # Sentinel snapshot that would shadow the live path if it
        # ran — assert the live organs win.
        sentinel_snapshot = {
            "organs": {"sentinel_organ": {"container": "nowhere"}},
        }
        char.get_medical_snapshot = lambda: sentinel_snapshot
        snap = get_organ_snapshot(char)
        organs = snap.get("organs") or {}
        self.assertIn("heart", organs)
        self.assertNotIn("sentinel_organ", organs)


class _SaverDictLike(dict):
    """Subclass of ``dict`` used to model Evennia's ``_SaverDict``.

    The real ``_SaverDict`` (``evennia.utils.dbserialize._SaverDict``)
    is NOT a dict subclass — it wraps a persisted attribute and
    routes mutations back to the DB.  ``isinstance(saverdict, dict)``
    returns False for the real thing.  We can't easily import it in
    a unit test without setting up Evennia's full storage layer, so
    we model the surface that matters: dict-like access via ``.get``
    /``__getitem__``/``__setitem__``, but the isinstance check fails.
    """

    def __class__(self_cls):  # noqa: N804 — only used for the isinstance trick
        # Reporting a sentinel class makes isinstance(x, dict) False
        # even though we're factually a dict subclass.  This is the
        # smallest stand-in I can build that catches the production
        # bug; if real _SaverDict ever stops being dict-like, this
        # test wouldn't catch a real regression but the surface
        # contract (.get + __setitem__) would still be the right
        # gate.
        return _SaverDictLike


class OrgansAtLocationDuckTyping(TestCase):
    """Regression pin for #391-follow-up: ``organs_at_location`` must
    duck-type rather than ``isinstance(data, dict)`` because Evennia's
    persisted snapshots wrap nested dicts in ``_SaverDict`` (not a
    dict subclass).  Pre-fix, every corpse-targeted procedure verb
    rejected with "nothing at <location>" because every organ failed
    the isinstance gate.
    """

    def test_dict_like_non_dict_entries_match(self):
        """An organ entry that quacks like a dict (has ``.get``) but
        isn't a ``dict`` instance must still match container/display
        lookups."""
        # Build a minimal dict-like object that behaves like
        # _SaverDict for the surfaces ``organs_at_location`` touches.
        class _NotADict:
            def __init__(self, data):
                self._data = data

            def get(self, key, default=None):
                return self._data.get(key, default)

            def items(self):
                return self._data.items()

        heart_like = _NotADict({
            "container": "chest", "display_location": "chest",
            "current_hp": 15, "max_hp": 15,
        })
        target = SimpleNamespace()
        target.get_medical_snapshot = lambda: {
            "organs": {"heart": heart_like},
        }
        results = organs_at_location(target, "chest")
        names = [n for n, _ in results]
        self.assertIn(
            "heart", names,
            "Duck-typed organ data must match container lookup.",
        )

    def test_truly_non_dict_entries_skipped(self):
        """Defensive: ``None`` or primitive values must still be
        filtered out (no AttributeError, no false positives)."""
        target = SimpleNamespace()
        target.get_medical_snapshot = lambda: {
            "organs": {
                "garbage_string": "not a dict",
                "garbage_none": None,
                "garbage_int": 42,
            },
        }
        # Should not raise, should return empty list.
        results = organs_at_location(target, "chest")
        self.assertEqual(results, [])


# ---------------------------------------------------------------------
# apply_vital_consequences (#393 follow-up — death detection on
# vital-organ removal when the medical script isn't running)
# ---------------------------------------------------------------------


class ApplyVitalConsequences(TestCase):
    """Pin the contract that ``apply_vital_consequences`` fires the
    death pipeline immediately after a structural change, rather
    than depending on a medical-script tick that may not be running.
    """

    def _target(self, dead=False, organs_truthy=True):
        """Build a target stub exposing the surfaces the helper reads."""
        calls = []

        class _State:
            def __init__(self):
                self.organs = {} if not organs_truthy else {"sentinel": object()}

            def update_vital_signs(self):
                calls.append("update_vital_signs")

            def is_dead(self):
                calls.append("is_dead")
                return dead

        target = SimpleNamespace()
        target.medical_state = _State()
        target.ndb = SimpleNamespace()
        target.scripts = SimpleNamespace()

        def _save():
            calls.append("save_medical_state")

        def _at_death():
            calls.append("at_death")
            target.ndb.death_processed = True

        target.save_medical_state = _save
        target.at_death = _at_death
        target._calls = calls
        return target

    def test_living_with_vitals_intact_does_not_trigger_death(self):
        from world.medical.procedures import apply_vital_consequences
        target = self._target(dead=False)
        died = apply_vital_consequences(target)
        self.assertFalse(died)
        self.assertIn("update_vital_signs", target._calls)
        self.assertIn("save_medical_state", target._calls)
        self.assertIn("is_dead", target._calls)
        self.assertNotIn("at_death", target._calls)

    def test_living_with_dead_state_triggers_at_death(self):
        from world.medical.procedures import apply_vital_consequences
        target = self._target(dead=True)
        died = apply_vital_consequences(target)
        self.assertTrue(died)
        self.assertIn("at_death", target._calls)
        # Order matters: update -> save -> is_dead -> at_death.
        idx = target._calls.index
        self.assertLess(idx("update_vital_signs"), idx("at_death"))
        self.assertLess(idx("save_medical_state"), idx("at_death"))

    def test_double_call_does_not_double_trigger_at_death(self):
        """The ndb.death_processed guard prevents at_death from firing
        twice if a follow-up structural change calls the helper
        again after death already fired."""
        from world.medical.procedures import apply_vital_consequences
        target = self._target(dead=True)
        apply_vital_consequences(target)
        # Second call — at_death should not fire again.
        target._calls.clear()
        apply_vital_consequences(target)
        self.assertNotIn("at_death", target._calls)

    def test_no_medical_state_is_no_op(self):
        from world.medical.procedures import apply_vital_consequences
        target = SimpleNamespace()
        # No medical_state surface.
        died = apply_vital_consequences(target)
        self.assertFalse(died)

    def test_missing_save_method_does_not_raise(self):
        from world.medical.procedures import apply_vital_consequences
        target = self._target(dead=False)
        del target.save_medical_state
        # Should not raise.
        apply_vital_consequences(target)
        self.assertIn("update_vital_signs", target._calls)


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

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_suture_at_stump_records_sutured_stump(self, _r):
        # Suture closing an incision at a location whose organs are
        # all severed (wound_stage="severed") records the location in
        # ``target.db.sutured_stumps`` so the wound renderer
        # transitions the synthetic cut-point wound from ``fresh`` to
        # ``treated``.  Mirrors the harvested-organ ``fresh→treated``
        # transition the same verb already does — same idea applied
        # to the stump-prose progression.
        from world.medical.procedures import _resolve_suture
        # Mark every organ in the left_arm container as severed,
        # mimicking what ``sever_character_body`` does post-amputation.
        for organ in self.target.medical_state.organs.values():
            if organ.container == "left_arm":
                organ.current_hp = 0
                organ.wound_stage = "severed"
        open_incision(self.target, "left_arm", surgeon=self.actor)
        _resolve_suture(self.actor, self.target, location="left_arm")
        sutured = self.target.db.sutured_stumps or []
        self.assertIn("left_arm", sutured)

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_suture_all_treats_unincised_stumps(self, _r):
        # Combat-driven amputation bypasses the ``open_incision`` call
        # that ``_resolve_amputate`` makes — so the body carries
        # severed organs with no surgical state to match.  The verb
        # must still treat those stumps when ``suture all`` is run,
        # not bail with "nothing to suture."
        from world.medical.procedures import _resolve_suture
        # Mark left_arm organs severed but DON'T open an incision.
        for organ in self.target.medical_state.organs.values():
            if organ.container == "left_arm":
                organ.current_hp = 0
                organ.wound_stage = "severed"
        _resolve_suture(self.actor, self.target)  # location=None
        sutured = self.target.db.sutured_stumps or []
        self.assertIn("left_arm", sutured)

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_suture_specific_unincised_stump_treats_it(self, _r):
        # Same scenario but the surgeon names the stump explicitly.
        from world.medical.procedures import _resolve_suture
        for organ in self.target.medical_state.organs.values():
            if organ.container == "left_arm":
                organ.current_hp = 0
                organ.wound_stage = "severed"
        _resolve_suture(self.actor, self.target, location="left_arm")
        sutured = self.target.db.sutured_stumps or []
        self.assertIn("left_arm", sutured)

    @patch("world.medical.procedures.random.randint", return_value=6)
    def test_suture_at_unsevered_location_does_not_mark_stump(self, _r):
        # Closing an incision at a location with intact organs (the
        # normal surgical case — opened for harvest / install) must
        # not pollute ``sutured_stumps`` with locations that aren't
        # actually amputation sites.  Only locations whose organs are
        # ``wound_stage="severed"`` qualify.
        from world.medical.procedures import _resolve_suture
        open_incision(self.target, "chest", surgeon=self.actor)
        _resolve_suture(self.actor, self.target, location="chest")
        sutured = getattr(self.target.db, "sutured_stumps", None) or []
        self.assertNotIn("chest", sutured)

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
