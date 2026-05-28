"""Tests for the death-time medical-state snapshot (PR #186).

Verifies that :meth:`typeclasses.death_progression.DeathProgressionScript
._create_corpse_from_character` captures the live character's full
:class:`world.medical.core.MedicalState` via ``to_dict()`` and persists
it on ``corpse.db.medical_state_at_death`` so the upcoming surgical
commands (autopsy / harvest / sever) all have a single source of
truth for the death-moment organ inventory.

Also exercises :meth:`typeclasses.corpse.Corpse.get_medical_snapshot`
as the canonical accessor — consumers must route through the helper
rather than reading the raw ``db`` attribute so the contract is
re-checkable in one place.

Run via::

    evennia test --settings settings.py world.tests.test_corpse_medical_snapshot
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript


class TestCorpseMedicalSnapshot(EvenniaTest):
    """Snapshot write + round-trip via ``get_medical_snapshot``."""

    character_typeclass = Character

    def setUp(self) -> None:
        super().setUp()
        self.victim = self.char1
        self.victim.sleeve_uid = "sleeve-medical-001"
        # Touch the medical state so the lazy initializer runs and
        # populates the default organ set.  Reading the property is
        # sufficient — :class:`world.medical.core.MedicalState`'s
        # constructor wires the default organ table.
        _ = self.victim.medical_state

        self.script = DeathProgressionScript()

    def _make_corpse(self):
        return self.script._create_corpse_from_character(self.victim)

    # ------------------------------------------------------------------
    # Snapshot is written at corpse creation
    # ------------------------------------------------------------------

    def test_snapshot_persisted_on_corpse(self) -> None:
        corpse = self._make_corpse()
        try:
            snapshot = corpse.db.medical_state_at_death
            # Evennia wraps persisted dicts in ``_SaverDict``; the
            # surface is dict-compatible but not a plain ``dict``
            # subclass, so test the mapping protocol instead of the
            # concrete type.
            self.assertIsNotNone(snapshot)
            self.assertIn("organs", snapshot)
            self.assertGreater(len(snapshot["organs"]), 0)
        finally:
            corpse.delete()

    def test_get_medical_snapshot_returns_persisted_dict(self) -> None:
        """The accessor must surface the same data the db attribute holds."""
        corpse = self._make_corpse()
        try:
            via_helper = corpse.get_medical_snapshot()
            via_db = corpse.db.medical_state_at_death
            self.assertIsNotNone(via_helper)
            # ``_SaverDict`` instances compare equal field-by-field via
            # the mapping protocol; identity is not guaranteed across
            # repeated attribute reads.
            self.assertEqual(dict(via_helper), dict(via_db))
        finally:
            corpse.delete()

    def test_snapshot_matches_live_to_dict_at_death(self) -> None:
        """The captured dict equals what the live ``to_dict`` returned."""
        expected = self.victim.medical_state.to_dict()
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.db.medical_state_at_death, expected)
        finally:
            corpse.delete()

    def test_sibling_lists_initialised_empty(self) -> None:
        """Surgical-state lists must exist as empty containers so the
        upcoming harvest / sever commands can append without guards."""
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.db.removed_organs, [])
            self.assertEqual(corpse.db.severed_locations, [])
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_bare_character_still_yields_organ_inventory(self) -> None:
        """A pristine character (no overrides applied) snapshots a
        complete default organ table — the snapshot does not depend on
        disguise state."""
        bare = create_object(Character, key="Bare", location=self.room1)
        bare.sleeve_uid = "sleeve-bare-medical-002"
        _ = bare.medical_state
        try:
            corpse = self.script._create_corpse_from_character(bare)
            try:
                snapshot = corpse.get_medical_snapshot()
                self.assertIsNotNone(snapshot)
                self.assertIn("heart", snapshot["organs"])
            finally:
                corpse.delete()
        finally:
            bare.delete()
