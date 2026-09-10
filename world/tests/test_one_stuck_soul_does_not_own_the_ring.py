"""No single repeating signal owns the world-state ring (#2671).

Eviction was purely by age, so the ring's window was set by its noisiest
emitter. Measured live:

    400 / 400 rows      span 15.46 h      25.9 emits/h
    plan_faulted   341   (85%)
      ... 127  a chrome-trimmed security robot: no plan satisfies …
      ...  89  a scorched security robot: no plan satisfies …
      ...  43  a dented security robot: no plan satisfies …
    went_hungry     37
    travel_stalled  15
    till_empty       7

259 of the 400 rows were three robots failing the same unplannable goal
over and over (#2696), while the signals that actually describe colony
state were being pushed out. The ring is the colony's capacity to notice
itself, and it was noticing one stuck loop.

A repeat is not new information: twenty rows of "this keeps happening"
say what two hundred say, at a twentieth of the window. The loop stays
represented AND stays current — its newest occurrence replaces its own
oldest, never somebody else's.
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from world import wsis

#: The INTENDED share is the default, not a permissive one: with a
#: fallback of 1.0 the cap assertions would pass against the unfixed
#: tree by asserting a cap of the whole ring, which is exactly the
#: behaviour being fixed.
CAP = max(1, int(wsis.RING * getattr(wsis, "SIGNATURE_SHARE", 0.05)))


class _Ring(EvenniaTest):
    """Drives the module's in-process ring directly; `_checkpoint` is
    stubbed so nothing reaches the live heartbeat script."""

    def setUp(self):
        super().setUp()
        self._saved = wsis._ring
        wsis._ring = []
        patcher = patch.object(wsis, "_checkpoint")
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        wsis._ring = self._saved
        super().tearDown()

    def kinds(self):
        from collections import Counter
        return Counter(row[1] for row in wsis._ring)

    def notes(self):
        from collections import Counter
        return Counter(row[5] for row in wsis._ring)


class TestARepeatIsCapped(_Ring):

    def test_the_ring_records_at_all(self):
        """Control: an emit that never lands would make every cap
        assertion below pass for the wrong reason."""
        wsis.emit("went_hungry", note="somebody")
        self.assertEqual(len(wsis._ring), 1)

    def test_one_signature_cannot_exceed_its_share(self):
        for _ in range(wsis.RING * 2):
            wsis.emit("plan_faulted", note="a dented robot: no plan")
        self.assertLessEqual(len(wsis._ring), CAP)

    def test_and_it_keeps_the_NEWEST_of_them(self):
        """Represented and current: a loop that is still happening must
        still read as still happening."""
        for i in range(wsis.RING * 2):
            with patch.object(wsis.time, "time", return_value=1000.0 + i):
                wsis.emit("plan_faulted", note="a dented robot: no plan")
        stamps = [row[0] for row in wsis._ring]
        self.assertEqual(max(stamps), 1000.0 + wsis.RING * 2 - 1)

    def test_two_different_notes_are_two_stories(self):
        for _ in range(wsis.RING):
            wsis.emit("plan_faulted", note="a dented robot: no plan")
            wsis.emit("plan_faulted", note="a scorched robot: no plan")
        self.assertEqual(len(self.notes()), 2)
        for count in self.notes().values():
            self.assertLessEqual(count, CAP)


class TestTheQuietSignalsSurvive(_Ring):
    """The point of the whole thing."""

    def test_a_loop_does_not_evict_the_signals_it_drowns(self):
        wsis.emit("till_empty", note="the Helix till is empty")
        wsis.emit("went_hungry", note="somebody went hungry")
        for _ in range(wsis.RING * 3):
            wsis.emit("plan_faulted", note="a dented robot: no plan")
        self.assertEqual(self.kinds()["till_empty"], 1,
                         "a stuck loop evicted a till_empty signal")
        self.assertEqual(self.kinds()["went_hungry"], 1)

    def test_the_ring_still_has_a_hard_ceiling(self):
        """The share is a ceiling on one voice, not a floor under it —
        the global cap must still apply."""
        for i in range(wsis.RING * 2):
            wsis.emit("went_hungry", note=f"hungry number {i}")
        self.assertLessEqual(len(wsis._ring), wsis.RING)

    def test_distinct_signals_still_age_out_normally(self):
        for i in range(wsis.RING + 50):
            wsis.emit("went_hungry", note=f"hungry number {i}")
        oldest = wsis._ring[0][5]
        self.assertNotEqual(oldest, "hungry number 0",
                            "nothing aged out at all")
