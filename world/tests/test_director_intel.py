"""Tests for hybrid security intel (crime slice 4): per-bot sightings,
the base sync, and the force-wide wanted record — including the latency
window (nothing goes force-wide until the bot is back at its post)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.director.intel import (
    clear_wanted_record,
    get_wanted_record,
    is_wanted,
    log_local_sighting,
    sync_bot_intel,
)


def _bot():
    return SimpleNamespace(db=SimpleNamespace(role="security"))


class TestIntel(TestCase):
    def setUp(self):
        clear_wanted_record()

    def tearDown(self):
        clear_wanted_record()

    def test_local_sighting_accumulates_on_bot_only(self):
        bot = _bot()
        log_local_sighting(bot, "FACE1", "assault")
        log_local_sighting(bot, "FACE1", "assault")
        self.assertEqual(bot.db.local_sightings["FACE1"]["count"], 2)
        # THE LATENCY WINDOW: the force record knows nothing yet.
        self.assertIsNone(is_wanted("FACE1"))

    def test_none_uid_never_logged(self):
        bot = _bot()
        log_local_sighting(bot, None, "assault")
        self.assertFalse(getattr(bot.db, "local_sightings", None))

    def test_sync_goes_force_wide_and_clears_local(self):
        bot = _bot()
        log_local_sighting(bot, "FACE1", "assault")
        self.assertEqual(sync_bot_intel(bot), 1)
        entry = is_wanted("FACE1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["count"], 1)
        self.assertEqual(entry["last_crime"], "assault")
        self.assertEqual(bot.db.local_sightings, {})
        # nothing left to sync
        self.assertEqual(sync_bot_intel(bot), 0)

    def test_repeat_offender_count_accumulates_across_syncs(self):
        bot_a, bot_b = _bot(), _bot()
        log_local_sighting(bot_a, "FACE1", "assault")
        sync_bot_intel(bot_a)
        log_local_sighting(bot_b, "FACE1", "robbery")
        sync_bot_intel(bot_b)
        entry = is_wanted("FACE1")
        self.assertEqual(entry["count"], 2)
        self.assertEqual(entry["last_crime"], "robbery")

    def test_downed_bot_never_syncs(self):
        # A bot that never runs sync (killed on the walk home) leaves the
        # record untouched — its knowledge dies with it.
        bot = _bot()
        log_local_sighting(bot, "FACE1", "murder")
        self.assertIsNone(is_wanted("FACE1"))
        self.assertEqual(get_wanted_record(), {})

    def test_is_wanted_none_uid(self):
        self.assertIsNone(is_wanted(None))
