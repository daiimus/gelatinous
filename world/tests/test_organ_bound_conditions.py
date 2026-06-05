"""Tests for the organ-bound condition tier (#307 follow-up).

The #307 scaffolding shipped the body / location-bound tier
(``MedicalState.conditions`` filtered by location).  This module
covers the third tier: **organ-bound** conditions that live on the
organ itself (``Organ.conditions``) and travel with it through
harvest / install / serialization without sync logic.

Three-tier model recap:

1. **Body-bound** — no location; affects whole body (sepsis,
   blood loss).  Stays on the body when an organ is swapped.
2. **Location-bound** — location field set; affects every organ
   at that container / display_location (chest-wall abscess).
   Stays on the body when an organ is swapped.
3. **Organ-bound** — lives on ``Organ.conditions``; affects this
   organ specifically (endocarditis, kidney stones).  **Travels
   with the organ** through harvest / swap.

Together with the scan in ``Organ._iter_relevant_conditions``, the
three tiers compound their modifiers — an inflamed heart in a body
also leaking with sepsis takes both penalties multiplicatively.

Specific architectural guarantees this module pins down:

* Organ-bound conditions modify functionality the same way
  body/location-bound do (no special-case rendering math).
* Round-trip through ``to_dict`` / ``from_dict`` preserves
  organ-bound conditions cleanly (via the
  ``deserialize_condition`` factory).
* Body-bound conditions do NOT travel through serialization onto
  individual organs (negative control — that would break the
  cyberware swap semantics from the #307 PR).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.conditions import (
    InfectionCondition,
    MedicalCondition,
    deserialize_condition,
)
from world.medical.core import MedicalState, Organ


def _human_character():
    return SimpleNamespace(
        db=SimpleNamespace(species="human", archived=False),
        key="TestSubject",
    )


# ---------------------------------------------------------------------
# Scan picks up organ-bound conditions
# ---------------------------------------------------------------------


class OrganBoundConditionAffectsOrgan(TestCase):

    def test_organ_bound_infection_reduces_functionality(self):
        state = MedicalState(_human_character())
        heart = state.organs["heart"]
        # Organ-bound (lives on the organ, no medical_state filter).
        heart.conditions.append(InfectionCondition(severity=5))
        # Severity 5 → moderate ladder → 0.75 modifier.
        self.assertAlmostEqual(heart.get_functionality_percentage(), 0.75)

    def test_organ_bound_at_severity_10_disables(self):
        state = MedicalState(_human_character())
        heart = state.organs["heart"]
        heart.conditions.append(InfectionCondition(severity=10))
        self.assertFalse(heart.is_functional())


class TiersCompound(TestCase):
    """Body-bound + organ-bound conditions stack multiplicatively
    (the scan yields both, and ``get_functionality_percentage``
    products all modifiers)."""

    def test_chest_infection_plus_endocarditis_compound(self):
        state = MedicalState(_human_character())
        heart = state.organs["heart"]
        # Body/location-bound: severity 3 (chest tissue) → 0.9
        state.conditions.append(
            InfectionCondition(severity=3, location="chest")
        )
        # Organ-bound: severity 3 (endocarditis) → 0.9
        heart.conditions.append(InfectionCondition(severity=3))
        # 0.9 × 0.9 = 0.81
        self.assertAlmostEqual(heart.get_functionality_percentage(), 0.81)

    def test_body_wide_no_location_compounds_too(self):
        state = MedicalState(_human_character())
        heart = state.organs["heart"]
        # No-location condition — base modifier 1.0; doesn't penalize
        # but confirms the no-effect path coexists with organ-bound.
        state.conditions.append(MedicalCondition("phantom_pain", severity=5))
        heart.conditions.append(InfectionCondition(severity=5))
        # 1.0 × 0.75 = 0.75
        self.assertAlmostEqual(heart.get_functionality_percentage(), 0.75)


# ---------------------------------------------------------------------
# Persistence: organ-bound conditions round-trip cleanly
# ---------------------------------------------------------------------


class SerializationRoundTrip(TestCase):

    def test_to_dict_serializes_conditions_as_dicts(self):
        organ = Organ("heart")
        organ.conditions.append(InfectionCondition(severity=5))
        snap = organ.to_dict()
        # Conditions stored as list of dicts, not pickled instances.
        self.assertEqual(len(snap["conditions"]), 1)
        condition_dict = snap["conditions"][0]
        self.assertIsInstance(condition_dict, dict)
        self.assertEqual(condition_dict["condition_type"], "infection")
        self.assertEqual(condition_dict["severity"], 5)

    def test_from_dict_restores_organ_bound_conditions(self):
        organ = Organ("heart")
        organ.conditions.append(InfectionCondition(severity=5))
        snap = organ.to_dict()
        restored = Organ.from_dict(snap)
        self.assertEqual(len(restored.conditions), 1)
        c = restored.conditions[0]
        self.assertIsInstance(c, InfectionCondition)
        self.assertEqual(c.severity, 5)

    def test_round_trip_preserves_functionality(self):
        # End-to-end: restored organ's functionality matches the
        # pre-serialization value.
        state = MedicalState(_human_character())
        heart = state.organs["heart"]
        heart.conditions.append(InfectionCondition(severity=5))
        before = heart.get_functionality_percentage()
        snap = heart.to_dict()
        restored = Organ.from_dict(snap)
        self.assertAlmostEqual(restored.get_functionality_percentage(),
                               before)

    def test_legacy_instance_in_list_survives(self):
        # Pre-#307 snapshots stored MedicalCondition instances
        # directly (pickled by Evennia's attribute layer).  The
        # ``from_dict`` factory accepts both shapes so old data
        # round-trips without crashing.
        instance = InfectionCondition(severity=3)
        organ = Organ.from_dict({
            "name": "heart",
            "current_hp": 10, "max_hp": 15,
            "conditions": [instance],  # legacy pickled instance
            "wound_stage": None,
            "injury_type": None,
            "wound_timestamp": None,
        })
        self.assertEqual(len(organ.conditions), 1)
        self.assertIs(organ.conditions[0], instance)

    def test_invalid_entries_skipped(self):
        # Defensive: malformed entries don't break the restore.
        organ = Organ.from_dict({
            "name": "heart",
            "current_hp": 10, "max_hp": 15,
            "conditions": ["not a condition", 42, None],
            "wound_stage": None,
            "injury_type": None,
            "wound_timestamp": None,
        })
        self.assertEqual(organ.conditions, [])


# ---------------------------------------------------------------------
# Body-bound conditions do NOT migrate onto organs at serialization
# ---------------------------------------------------------------------


class BodyBoundStaysOnBody(TestCase):
    """Negative control — confirms the cyberware swap semantics from
    the #307 PR.  A chest infection on the body is in
    ``MedicalState.conditions``, not ``Organ.conditions``; it must
    not leak into an organ's serialized list during snapshot.
    """

    def test_body_bound_chest_infection_not_in_heart_snapshot(self):
        state = MedicalState(_human_character())
        state.conditions.append(
            InfectionCondition(severity=5, location="chest")
        )
        heart = state.organs["heart"]
        snap = heart.to_dict()
        self.assertEqual(snap["conditions"], [])

    def test_body_bound_stays_on_state_round_trip(self):
        state = MedicalState(_human_character())
        state.conditions.append(
            InfectionCondition(severity=5, location="chest")
        )
        snap = state.to_dict()
        restored = MedicalState.from_dict(snap)
        # Body-wide list preserves the condition.
        self.assertEqual(len(restored.conditions), 1)
        # Organ-bound list on the heart stays empty.
        self.assertEqual(restored.organs["heart"].conditions, [])


# ---------------------------------------------------------------------
# Harvest pipeline preserves organ-bound conditions
# ---------------------------------------------------------------------


class _FakeCorpse:
    """Minimal corpse stub for ``Organ.configure_from_harvest``.

    Carries a medical snapshot with organ-bound conditions on the
    targeted organ.  Identity / decay fields are stubbed enough that
    the configure call doesn't crash.
    """

    def __init__(self, organ_name, organ_conditions=None,
                 species="human"):
        snapshot = {
            "organs": {
                organ_name: {
                    "container": "chest",
                    "display_location": "chest",
                    "conditions": list(organ_conditions or []),
                },
            },
        }
        self.db = SimpleNamespace(
            signature_at_death=None,
            apparent_uid_at_death=None,
            species=species,
            medical_state_at_death=snapshot,
        )
        self.dbref = "#testcorpse"

    def get_medical_snapshot(self):
        return self.db.medical_state_at_death

    def get_decay_stage(self):
        return "fresh"


class HarvestPipelinePreservesOrganConditions(TestCase):
    """``Organ.configure_from_harvest`` on the harvested-item Organ
    typeclass pulls the source organ's conditions from the corpse
    snapshot and stores them on the item's db for future install
    integration (Phase 3.2 cybernetics)."""

    def _make_harvested_item(self):
        # Avoid the full Evennia typeclass dance for a unit test —
        # exercise ``configure_from_harvest`` directly against a
        # plain-Python stub that mimics the db namespace it touches.
        from typeclasses.items import Organ as HarvestedOrgan

        class _ItemStub:
            db = SimpleNamespace()
            key = ""

        stub = _ItemStub()
        # Bind the unbound method so it runs against our stub.
        stub.configure_from_harvest = (
            HarvestedOrgan.configure_from_harvest.__get__(stub)
        )
        return stub

    def test_organ_bound_conditions_copied_to_harvested_item(self):
        condition_dict = InfectionCondition(severity=4).to_dict()
        corpse = _FakeCorpse(
            organ_name="heart",
            organ_conditions=[condition_dict],
        )
        item = self._make_harvested_item()
        item.configure_from_harvest(
            organ_name="heart",
            condition="pristine",
            corpse=corpse,
        )
        self.assertEqual(len(item.db.organ_conditions), 1)
        # Serialized form preserved verbatim — install pipeline
        # (Phase 3.2) will reconstruct condition objects from these
        # dicts via ``deserialize_condition``.
        self.assertEqual(
            item.db.organ_conditions[0]["condition_type"], "infection",
        )

    def test_no_conditions_on_organ_yields_empty_list(self):
        corpse = _FakeCorpse(organ_name="heart", organ_conditions=[])
        item = self._make_harvested_item()
        item.configure_from_harvest(
            organ_name="heart",
            condition="pristine",
            corpse=corpse,
        )
        self.assertEqual(item.db.organ_conditions, [])

    def test_missing_snapshot_handled_gracefully(self):
        # Corpse with no ``get_medical_snapshot`` (test stubs that
        # predate the snapshot layer).  Defensive empty list.
        class _BareCorpse:
            db = SimpleNamespace(
                signature_at_death=None,
                apparent_uid_at_death=None,
                species="human",
            )
            dbref = "#bare"

            def get_decay_stage(self):
                return "fresh"

        item = self._make_harvested_item()
        item.configure_from_harvest(
            organ_name="heart",
            condition="pristine",
            corpse=_BareCorpse(),
        )
        self.assertEqual(item.db.organ_conditions, [])


# ---------------------------------------------------------------------
# Factory dispatch
# ---------------------------------------------------------------------


class DeserializeConditionFactory(TestCase):

    def test_infection_dispatches_correctly(self):
        original = InfectionCondition(severity=5, location="chest")
        snap = original.to_dict()
        restored = deserialize_condition(snap)
        self.assertIsInstance(restored, InfectionCondition)
        self.assertEqual(restored.severity, 5)
        self.assertEqual(restored.location, "chest")

    def test_unknown_type_falls_through_to_base(self):
        restored = deserialize_condition({
            "condition_type": "future_condition_not_yet_classed",
            "severity": 7,
        })
        self.assertIsInstance(restored, MedicalCondition)
        self.assertEqual(restored.severity, 7)
