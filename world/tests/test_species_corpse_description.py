"""Integration tests for issue #232: species-aware corpse decay prose.

The unit-level behaviour of
:func:`world.anatomy.species.get_species_corpse_description` is covered
in :mod:`world.tests.test_species_anatomy`.  This module exercises the
typeclass integration path:
:meth:`typeclasses.corpse.Corpse._build_decay_desc_paragraph` delegates
to that helper, so a non-human corpse's ``look`` body prose surfaces the
correct species (or drops the token for unknown species) — and the
delegation preserves the issue #230 pure-look contract (no state
mutation on render).

Run via::

    evennia test --settings settings.py world.tests.test_species_corpse_description
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript


class TestSpeciesAwareCorpseProse(EvenniaTest):
    """Corpse body prose reflects ``db.species`` via the #232 helper."""

    character_typeclass = Character

    def setUp(self) -> None:
        super().setUp()
        self.victim = self.char1
        self.victim.sleeve_uid = "sleeve-species-desc-001"
        _ = self.victim.medical_state  # trigger lazy init
        self.script = DeathProgressionScript()

    def _make_corpse(self):
        return self.script._create_corpse_from_character(self.victim)

    # ------------------------------------------------------------------
    # Species surfaces in the body prose
    # ------------------------------------------------------------------

    def test_human_corpse_prose_mentions_human(self) -> None:
        corpse = self._make_corpse()
        try:
            corpse.db.species = "human"
            paragraph = corpse._build_decay_desc_paragraph("fresh")
            self.assertIn("human", paragraph)
        finally:
            corpse.delete()

    def test_unknown_species_corpse_drops_token(self) -> None:
        """A non-registered species must not be misclaimed as human."""
        corpse = self._make_corpse()
        try:
            corpse.db.species = "unobtanium_alien"
            paragraph = corpse._build_decay_desc_paragraph("fresh")
            self.assertTrue(
                paragraph.startswith("A recently deceased body.")
            )
            self.assertNotIn("human", paragraph)
            self.assertNotIn("  ", paragraph)
        finally:
            corpse.delete()

    def test_none_species_defaults_to_human(self) -> None:
        """``db.species is None`` → corpse-side 'human' default applies."""
        corpse = self._make_corpse()
        try:
            corpse.db.species = None
            paragraph = corpse._build_decay_desc_paragraph("moderate")
            self.assertTrue(paragraph.startswith("Decomposing human remains."))
        finally:
            corpse.delete()

    def test_base_desc_embedded_in_fresh_stage(self) -> None:
        corpse = self._make_corpse()
        try:
            corpse.db.species = "human"
            corpse.db.physical_description = "A jagged scar crosses one cheek."
            paragraph = corpse._build_decay_desc_paragraph("fresh")
            self.assertIn("A jagged scar crosses one cheek.", paragraph)
        finally:
            corpse.delete()

    def test_return_appearance_shows_species_prose(self) -> None:
        corpse = self._make_corpse()
        try:
            corpse.db.species = "human"
            with patch.object(
                corpse, "get_decay_stage", return_value="advanced"
            ):
                output = corpse.return_appearance(self.char2)
            self.assertIsNotNone(output)
            self.assertIn("Putrid human remains.", output)
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Pure-look contract preserved (issue #230 regression guard)
    # ------------------------------------------------------------------

    def test_species_aware_look_does_not_mutate_state(self) -> None:
        """Delegation to the species helper must remain a pure read."""
        corpse = self._make_corpse()
        try:
            corpse.db.species = "unobtanium_alien"
            desc_before = corpse.db.desc
            key_before = corpse.key
            aliases_before = set(corpse.aliases.all())

            for _ in range(3):
                corpse.return_appearance(self.char2)

            self.assertEqual(corpse.db.desc, desc_before)
            self.assertEqual(corpse.key, key_before)
            self.assertEqual(set(corpse.aliases.all()), aliases_before)
        finally:
            corpse.delete()
