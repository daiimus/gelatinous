"""
Tests for issue #230: corpse ``look`` must be a pure read.

Pre-#230 behaviour: :meth:`typeclasses.corpse.Corpse.return_appearance`
called ``_update_decay_descriptions`` which wrote ``self.key``,
``self.aliases``, and ``self.db.desc`` on every look — a pure read
with persistent side effects.

Post-#230:

* All decay-stage aliases are pre-seeded at creation by
  :meth:`Corpse._seed_decay_aliases_and_key` so search/targeting works
  at t=0 regardless of which stage is current.
* ``self.key`` advances on stage transitions via
  :meth:`Corpse._refresh_decay_key_if_changed`, which is invoked from
  :meth:`typeclasses.rooms.Room._check_corpse_decay` on character entry
  — a lifecycle event, NOT from ``look``.
* The staged decay paragraph is computed on the fly by
  :meth:`Corpse._build_decay_desc_paragraph` and inlined into the
  ``return_appearance`` output without persisting.
* The death-time ``db.desc`` snapshot
  (``death_progression.py:682``) survives untouched (Option α).

Run via::

    evennia test --settings settings.py world.tests.test_corpse_pure_look
"""

from __future__ import annotations

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.corpse import Corpse
from typeclasses.death_progression import DeathProgressionScript


class TestCorpseLookIsPure(EvenniaTest):
    """``look`` must not mutate ``db.desc``, ``key``, or aliases."""

    character_typeclass = Character

    def setUp(self) -> None:
        super().setUp()
        self.victim = self.char1
        self.victim.sleeve_uid = "sleeve-pure-look-001"
        _ = self.victim.medical_state  # trigger lazy init
        self.script = DeathProgressionScript()

    def _make_corpse(self):
        return self.script._create_corpse_from_character(self.victim)

    # ------------------------------------------------------------------
    # Pre-seeded aliases / key (creation-time)
    # ------------------------------------------------------------------

    def test_all_decay_aliases_present_at_creation(self) -> None:
        """Every stage's display name + universal aliases exist at t=0."""
        corpse = self._make_corpse()
        try:
            aliases = set(corpse.aliases.all())
            for required in (
                "corpse", "remains", "body",
                "human corpse", "rotting corpse", "skeletal remains",
            ):
                self.assertIn(
                    required,
                    aliases,
                    f"alias {required!r} missing at corpse creation",
                )
        finally:
            corpse.delete()

    def test_initial_key_is_fresh_stage(self) -> None:
        """Newly created corpse's key is the fresh-stage display name."""
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.key, "human corpse")
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Look is pure
    # ------------------------------------------------------------------

    def test_look_does_not_mutate_db_desc(self) -> None:
        """``return_appearance`` must not write ``db.desc``."""
        corpse = self._make_corpse()
        try:
            before = corpse.db.desc
            corpse.return_appearance(self.char2)
            after = corpse.db.desc
            self.assertEqual(before, after)
        finally:
            corpse.delete()

    def test_look_does_not_mutate_key(self) -> None:
        """``return_appearance`` must not write ``self.key``."""
        corpse = self._make_corpse()
        try:
            before = corpse.key
            corpse.return_appearance(self.char2)
            after = corpse.key
            self.assertEqual(before, after)
        finally:
            corpse.delete()

    def test_look_does_not_mutate_aliases(self) -> None:
        """``return_appearance`` must not add/remove aliases."""
        corpse = self._make_corpse()
        try:
            before = set(corpse.aliases.all())
            corpse.return_appearance(self.char2)
            after = set(corpse.aliases.all())
            self.assertEqual(before, after)
        finally:
            corpse.delete()

    def test_death_time_desc_survives_look(self) -> None:
        """A custom death-time ``db.desc`` must survive multiple looks (Option α)."""
        corpse = self._make_corpse()
        try:
            custom = "The lifeless body of a tall human. They wore scars like armor."
            corpse.db.desc = custom
            for _ in range(3):
                corpse.return_appearance(self.char2)
            self.assertEqual(corpse.db.desc, custom)
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Staged paragraph rendering (pure compute)
    # ------------------------------------------------------------------

    def test_staged_paragraph_contains_stage_keyword(self) -> None:
        """The computed paragraph must mention each stage's signature word."""
        corpse = self._make_corpse()
        try:
            expectations = {
                "fresh": "fresh",
                "early": "pale",
                "moderate": "Decomposing",
                "advanced": "Putrid",
                "skeletal": "Skeletal",
            }
            for stage, keyword in expectations.items():
                paragraph = corpse._build_decay_desc_paragraph(stage)
                self.assertIn(
                    keyword,
                    paragraph,
                    f"stage {stage!r} paragraph missing keyword {keyword!r}",
                )
        finally:
            corpse.delete()

    def test_return_appearance_includes_stage_paragraph(self) -> None:
        """``return_appearance`` output includes the staged paragraph for current stage."""
        corpse = self._make_corpse()
        try:
            with patch.object(corpse, "get_decay_stage", return_value="moderate"):
                output = corpse.return_appearance(self.char2)
            self.assertIsNotNone(output)
            self.assertIn("Decomposing", output)
        finally:
            corpse.delete()

    # ------------------------------------------------------------------
    # Key refresh on stage transition
    # ------------------------------------------------------------------

    def test_refresh_key_updates_on_stage_change(self) -> None:
        """``_refresh_decay_key_if_changed`` advances key when stage changed."""
        corpse = self._make_corpse()
        try:
            self.assertEqual(corpse.key, "human corpse")
            with patch.object(corpse, "get_decay_stage", return_value="moderate"):
                corpse._refresh_decay_key_if_changed()
            self.assertEqual(corpse.key, "rotting corpse")
            with patch.object(corpse, "get_decay_stage", return_value="skeletal"):
                corpse._refresh_decay_key_if_changed()
            self.assertEqual(corpse.key, "skeletal remains")
        finally:
            corpse.delete()

    def test_refresh_key_noop_when_stage_unchanged(self) -> None:
        """Repeated refresh at the same stage leaves the key untouched."""
        corpse = self._make_corpse()
        try:
            initial = corpse.key
            for _ in range(3):
                corpse._refresh_decay_key_if_changed()
            self.assertEqual(corpse.key, initial)
        finally:
            corpse.delete()

    def test_room_entry_triggers_key_refresh(self) -> None:
        """Character entering a room with a decayed corpse refreshes its key."""
        corpse = self._make_corpse()
        try:
            # Force corpse into an advanced-decay stage without touching
            # creation_time directly (the room hook calls into
            # _check_corpse_decay → _refresh_decay_key_if_changed).
            with patch.object(
                Corpse, "get_decay_stage", return_value="advanced"
            ):
                # Move char2 into char1's room to trigger
                # ``Room.at_object_receive`` → ``_check_corpse_decay``.
                # Both chars start in self.room1 in EvenniaTest, so move
                # char2 out and back to trigger the receive hook.
                self.char2.move_to(self.room2, quiet=True)
                self.char2.move_to(self.room1, quiet=True)
            self.assertEqual(corpse.key, "rotting corpse")
        finally:
            corpse.delete()


if __name__ == "__main__":
    import unittest
    unittest.main()
