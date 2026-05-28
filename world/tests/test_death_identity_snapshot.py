"""
Integration tests for the death-time identity snapshot + override-clear
hygiene (Issue #182, Phase 3 closure).

Verifies that :meth:`typeclasses.death_progression.DeathProgressionScript
._create_corpse_from_character`:

1. Snapshots the full identity-signature tuple (``signature_at_death``)
   alongside the existing ``apparent_uid_at_death`` hash, so forensic
   consumers (spec L1000 / L1015 / L1020) can reconstruct component
   axes — the hash alone is one-way.
2. Clears all live overrides on the dead Character object **after** the
   snapshot has been captured (spec L1597). Ordering matters: the
   snapshot must reflect the death-moment disguise.
3. Preserves the corpse-local override axes that drive live re-derivation
   of the corpse's Apparent UID (existing recognition path unchanged).

Run via::

    evennia test --settings settings.py world.tests.test_death_identity_snapshot
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript
from world.identity import get_apparent_uid, get_identity_signature


class TestDeathIdentitySnapshot(EvenniaTest):
    """Drive ``_create_corpse_from_character`` against a real Character.

    EvenniaTest spins up ``self.char1`` / ``self.char2`` / ``self.room1``.
    We only need one character here; we instantiate the death-progression
    script directly so the test does not have to drive the full
    medical/curtain/teleport pipeline.
    """

    character_typeclass = Character

    def setUp(self) -> None:
        super().setUp()
        self.victim = self.char1
        self.victim.sleeve_uid = "sleeve-victim-001"
        # Apply a disguise so the snapshot has non-trivial overrides to
        # capture (and the clear-step has something to wipe).
        self.victim.db.height_override = "tall"
        self.victim.db.build_override = "lean"
        self.victim.db.keyword_override = "hooded"
        self.victim.db.active_persona = "the hooded stranger"

        # Detached script — we only need the helper methods, not the
        # full death-progression lifecycle.
        self.script = DeathProgressionScript()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_corpse(self):
        """Drive the production code path under test."""
        return self.script._create_corpse_from_character(self.victim)

    # ------------------------------------------------------------------
    # Snapshot fidelity
    # ------------------------------------------------------------------

    def test_signature_at_death_captures_full_tuple(self) -> None:
        """Corpse stores the same 5-tuple ``get_identity_signature``
        would have returned for the live victim *before* the clear."""
        # Capture what the signature should look like for the live victim
        # before we drive the death snapshot — this is the contract.
        expected = get_identity_signature(self.victim)
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.db.signature_at_death, expected)
        finally:
            corpse.delete()

    def test_apparent_uid_at_death_matches_pre_death_live_uid(self) -> None:
        """The hash snapshot still works — preserves existing behaviour."""
        expected_uid = get_apparent_uid(self.victim)
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.db.apparent_uid_at_death, expected_uid)
            self.assertIsNotNone(corpse.db.apparent_uid_at_death)
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Override clear hygiene (spec L1597)
    # ------------------------------------------------------------------

    def test_live_overrides_cleared_after_death(self) -> None:
        """All four override-state attrs on the live Character are
        nulled post-snapshot."""
        corpse = self._make_corpse()
        try:
            self.assertIsNone(self.victim.db.height_override)
            self.assertIsNone(self.victim.db.build_override)
            self.assertIsNone(self.victim.db.keyword_override)
            self.assertIsNone(self.victim.db.active_persona)
        finally:
            corpse.delete()

    def test_snapshot_precedes_clear(self) -> None:
        """The corpse snapshot reflects the death-moment disguise even
        though the live victim has been wiped clean by the same call."""
        corpse = self._make_corpse()
        try:
            # Snapshot still carries the death-moment overrides...
            sig = corpse.db.signature_at_death
            self.assertEqual(sig[1], "tall")  # height_override
            self.assertEqual(sig[2], "lean")  # build_override
            self.assertEqual(sig[3], "hooded")  # keyword_override
            # ...while the live character has them cleared.
            self.assertIsNone(self.victim.db.height_override)
            self.assertIsNone(self.victim.db.build_override)
            self.assertIsNone(self.victim.db.keyword_override)
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Corpse-local override preservation (existing recognition path)
    # ------------------------------------------------------------------

    def test_corpse_local_overrides_preserved(self) -> None:
        """The corpse's own override axes (used by live UID re-derivation
        on the corpse) still carry the death-moment disguise. Looting
        will reset them; this just confirms the death copy ran."""
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.db.height_override, "tall")
            self.assertEqual(corpse.db.build_override, "lean")
            self.assertEqual(corpse.db.keyword_override, "hooded")
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_undisguised_victim_snapshots_bare_signature(self) -> None:
        """A character with no disguise active still gets a valid
        snapshot — None overrides round-trip cleanly."""
        bare_victim = create_object(
            Character, key="Bare", location=self.room1
        )
        bare_victim.sleeve_uid = "sleeve-bare-002"
        try:
            expected = get_identity_signature(bare_victim)
            corpse = self.script._create_corpse_from_character(bare_victim)
            try:
                self.assertEqual(corpse.db.signature_at_death, expected)
                self.assertIsNone(corpse.db.signature_at_death[1])
                self.assertIsNone(corpse.db.signature_at_death[2])
                self.assertIsNone(corpse.db.signature_at_death[3])
            finally:
                corpse.delete()
        finally:
            bare_victim.delete()
