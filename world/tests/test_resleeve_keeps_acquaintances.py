"""Resleeving keeps the faces you knew (#2676).

`remembered_before` guards each entry on `isinstance(entry, dict)`, and
entries loaded from the database are `_SaverDict` — not a `dict`
subclass. Every real acquaintance took the `continue` branch.

Executed against live data before the fix: a cutoff of **positive
infinity**, which should keep everything, kept **0 of 72 entries across
13 bodies**. So resleeving zeroed every face and every voice a character
knew — the whole point of the function inverted.

The fix follows `world/stealth.py:_records`, which already does it
correctly: `deserialize()` first, and the `isinstance` below is then
sound. Converting once at the top is preferred to duck-typing each entry
— it makes every check true-to-shape instead of leaving a second trap.

**Sixth appearance of this shape** — #2701 bleeding conditions, #2465
placement rows, #2468 worn layers, #2438 severance, #2582 legacy hands,
and here. The distinguishing feature of this one is that the loss is
*silent and total*: nothing faults, you simply come back not knowing
anyone.
"""
from datetime import datetime, timedelta

from evennia.utils.test_resources import EvenniaTest

from world.imprint import remembered_before


def _iso(days_ago):
    return (datetime.now() - timedelta(days=days_ago)).isoformat()


class _MemoryCase(EvenniaTest):
    def stored(self, mapping):
        """Round-trip through the database so entries come back as
        `_SaverDict`, which is the whole point of the test."""
        self.char1.recognition_memory = mapping
        return self.char1.recognition_memory


class TestTheStoredShapeIsNotADict(_MemoryCase):
    def test_entries_come_back_as_savers(self):
        m = self.stored({"uid-1": {"name": "Sully",
                                   "first_seen": _iso(10)}})
        entry = list(m.values())[0]
        self.assertFalse(isinstance(entry, dict))

    def test_but_they_are_mapping_shaped(self):
        m = self.stored({"uid-1": {"name": "Sully",
                                   "first_seen": _iso(10)}})
        self.assertTrue(hasattr(list(m.values())[0], "get"))


class TestAKeepEverythingCutoffKeepsEverything(_MemoryCase):
    def test_infinite_cutoff_keeps_all(self):
        m = self.stored({
            "uid-1": {"name": "Sully", "first_seen": _iso(10)},
            "uid-2": {"name": "Vesper", "first_seen": _iso(3)},
        })
        self.assertEqual(len(remembered_before(m, float("inf"))), 2)

    def test_it_keeps_the_actual_entries(self):
        m = self.stored({"uid-1": {"name": "Sully",
                                   "first_seen": _iso(10)}})
        kept = remembered_before(m, float("inf"))
        self.assertEqual(kept["uid-1"]["name"], "Sully")


class TestTheCutoffStillCuts(_MemoryCase):
    """The function's real job: somebody first met INSIDE the gap was
    never in the backup, so they come back a stranger."""

    def test_someone_met_before_the_backup_is_kept(self):
        m = self.stored({"old": {"first_seen": _iso(30)}})
        cutoff = (datetime.now() - timedelta(days=10)).timestamp()
        self.assertIn("old", remembered_before(m, cutoff))

    def test_someone_met_after_the_backup_is_dropped(self):
        m = self.stored({"new": {"first_seen": _iso(2)}})
        cutoff = (datetime.now() - timedelta(days=10)).timestamp()
        self.assertNotIn("new", remembered_before(m, cutoff))

    def test_a_mixed_memory_splits_correctly(self):
        m = self.stored({
            "old": {"first_seen": _iso(30)},
            "new": {"first_seen": _iso(2)},
        })
        cutoff = (datetime.now() - timedelta(days=10)).timestamp()
        kept = remembered_before(m, cutoff)
        self.assertEqual(set(kept), {"old"})


class TestMalformedEntriesAreKept(_MemoryCase):
    """"An entry with no readable `first_seen` is KEPT: losing a
    relationship to a malformed field costs more than it protects." """

    def test_an_unreadable_date_survives(self):
        m = self.stored({"weird": {"first_seen": "not a date"}})
        cutoff = (datetime.now() - timedelta(days=10)).timestamp()
        self.assertIn("weird", remembered_before(m, cutoff))

    def test_a_missing_date_survives(self):
        m = self.stored({"weird": {"name": "no date at all"}})
        cutoff = (datetime.now() - timedelta(days=10)).timestamp()
        self.assertIn("weird", remembered_before(m, cutoff))


class TestEmptyInputIsSafe(_MemoryCase):
    def test_none_returns_empty(self):
        self.assertEqual(remembered_before(None, float("inf")), {})

    def test_empty_returns_empty(self):
        self.assertEqual(remembered_before({}, float("inf")), {})
