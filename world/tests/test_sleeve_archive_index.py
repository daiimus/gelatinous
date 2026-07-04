"""Sleeve archive tag index (DEATH_AND_SLEEVE_LIFECYCLE_SPEC §9 step 3).

Archived sleeves carry the ``archived`` tag (category ``sleeve``) as the query
index; account listings split active/archived in one tag query instead of a
``db.archived`` attribute read per character. Legacy flag-without-tag sleeves
are self-healed into the index so an archived husk can never read as active.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character


class TestArchiveTagIndex(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        # EvenniaTest links char1 to the account but does not register it in
        # account.characters (the _playable_characters list) — do so, since
        # the split reads that list.
        self.account.characters.add(self.char1)

    def _adopt(self, key):
        """A second character on the test account."""
        char = create_object(Character, key=key, location=self.room1)
        char.db_account = self.account
        char.save()
        self.account.characters.add(char)
        return char

    def test_archive_adds_tag_and_unarchive_clears_both(self):
        self.char1.archive_character(reason="manual")
        self.assertTrue(self.char1.tags.has("archived", category="sleeve"))
        self.assertTrue(self.char1.db.archived)
        self.assertTrue(self.char1.is_archived)
        self.char1.unarchive_character()
        self.assertFalse(self.char1.tags.has("archived", category="sleeve"))
        self.assertFalse(self.char1.db.archived)
        self.assertFalse(self.char1.is_archived)

    def test_is_archived_falls_back_to_legacy_attribute(self):
        self.char1.db.archived = True          # pre-index sleeve: flag only
        self.assertTrue(self.char1.is_archived)

    def test_sleeves_split_by_tag(self):
        retired = self._adopt("old sleeve")
        retired.archive_character(reason="death")
        active, archived = self.account._sleeves_split()
        self.assertIn(self.char1, active)
        self.assertNotIn(retired, active)
        self.assertIn(retired, archived)
        self.assertEqual(self.account.active_sleeves, active)
        self.assertEqual(self.account.archived_sleeves, archived)

    def test_split_self_heals_legacy_flag_without_tag(self):
        legacy = self._adopt("legacy husk")
        legacy.db.archived = True              # flag set, tag never written
        active, archived = self.account._sleeves_split()
        self.assertNotIn(legacy, active,
                         "archived husk must never read as active")
        self.assertIn(legacy, archived)
        # ...and the index healed itself for next time.
        self.assertTrue(legacy.tags.has("archived", category="sleeve"))

    def test_at_character_limit_counts_only_active(self):
        from django.test import override_settings
        retired = self._adopt("dead weight")
        retired.archive_character(reason="death")
        with override_settings(MAX_NR_CHARACTERS=1):
            # one active (char1) + one archived -> at the limit of 1, and the
            # archived sleeve does not push us over
            self.assertTrue(self.account.at_character_limit)
        with override_settings(MAX_NR_CHARACTERS=2):
            self.assertFalse(self.account.at_character_limit)
