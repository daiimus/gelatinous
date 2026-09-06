"""Blood stains stop being fresh (#2595).

`BloodPool._update_description` writes the age ladder ONCE, at bleed
time, and its only other caller is a partial solvent clean. Nothing
re-evaluated it as time passed, so every pool froze at age ~0.

Live when this was written: **31 of 38 pools were 179 hours old and
still reading "Fresh crimson stains glisten wetly"** — the line the room
prints on every `look`. `get_age_hours()` was computing the age
correctly the whole time; nothing asked it again.

Recomputed at the READ rather than on a ticker. A stain is a prop that
only matters when somebody is in the room to see it, and the ladder is
four buckets, so re-deriving costs less than scheduling would. It writes
only when the band actually changes, so a room full of old stains is a
comparison and no database write.

This mirrors `Corpse._refresh_decay_key_if_changed`, which the room
already calls for exactly the same reason — a derived line that has to
follow the clock.
"""
import time

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _PoolCase(EvenniaTest):
    def _pool(self, age_hours):
        pool = create_object("typeclasses.objects.BloodPool",
                             key="blood stains", location=self.room1)
        pool.db.bleeding_incidents = [{
            "character": "someone",
            "severity": 5,
            "timestamp": time.time() - age_hours * 3600,
            "sleeve_uid": "sleeve-1",
        }]
        pool._update_description()
        return pool

    def line(self, pool):
        return str(pool.db.integration_desc or "")


class TestTheLadderFollowsTheClock(_PoolCase):
    def test_a_fresh_pool_reads_fresh(self):
        pool = self._pool(0.1)
        self.assertIn("Fresh", self.line(pool))

    def test_an_old_pool_stops_reading_fresh(self):
        """The reported symptom: 179 hours old, still 'glisten wetly'."""
        pool = self._pool(0.1)
        pool.db.bleeding_incidents = [dict(
            pool.db.bleeding_incidents[0],
            timestamp=time.time() - 179 * 3600)]
        pool.refresh_integration_desc()
        self.assertNotIn("Fresh", self.line(pool))

    def test_it_reaches_the_oldest_band(self):
        pool = self._pool(0.1)
        pool.db.bleeding_incidents = [dict(
            pool.db.bleeding_incidents[0],
            timestamp=time.time() - 179 * 3600)]
        pool.refresh_integration_desc()
        self.assertIn("Faint", self.line(pool))

    def test_the_middle_bands_are_reachable(self):
        for hours, word in ((3, "Dark"), (12, "Dried")):
            pool = self._pool(hours)
            self.assertIn(word, self.line(pool),
                          f"{hours}h should read {word}")


class TestItOnlyWritesWhenTheBandMoves(_PoolCase):
    def test_a_refresh_that_changes_nothing_reports_false(self):
        pool = self._pool(0.1)
        self.assertFalse(pool.refresh_integration_desc())

    def test_a_refresh_that_ages_it_reports_true(self):
        pool = self._pool(0.1)
        pool.db.bleeding_incidents = [dict(
            pool.db.bleeding_incidents[0],
            timestamp=time.time() - 179 * 3600)]
        self.assertTrue(pool.refresh_integration_desc())

    def test_an_empty_pool_is_not_touched(self):
        """`_update_description` DELETES a pool with no incidents. The
        refresh must not trigger that on a read."""
        pool = self._pool(1)
        pool.db.bleeding_incidents = []
        pool.refresh_integration_desc()
        self.assertTrue(pool.pk, "reading a room deleted the blood pool")


class TestTheRoomAsksForIt(_PoolCase):
    def test_the_room_render_re_ages_a_stale_pool(self):
        pool = self._pool(0.1)
        pool.db.bleeding_incidents = [dict(
            pool.db.bleeding_incidents[0],
            timestamp=time.time() - 179 * 3600)]
        pool.db.integrate = True
        self.room1.get_object_integration_content(pool, self.char1)
        self.assertNotIn("Fresh", self.line(pool))

    def test_an_object_without_the_hook_is_fine(self):
        plain = create_object("typeclasses.objects.Object", key="a crate",
                              location=self.room1)
        plain.db.integration_desc = "A crate sits here."
        out = self.room1.get_object_integration_content(plain, self.char1)
        self.assertIn("crate", str(out))
