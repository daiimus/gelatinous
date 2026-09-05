"""The memory loop was dead in BOTH directions (#2707, #2728).

Writing: `thoughts._feed_rag` called `make_record` and `prune` -- the
two helpers `remember` wraps -- and skipped the DEDUPLICATION in the
middle. Every thought was appended as a new record whether or not that
sentence was already stored. 79% of 2,170 live records were duplicates.

Not merely wasted rows: `prune` enforces a per-subject cap, so
duplicates EVICT real memories. A soul that keeps having the same
thought spends its whole recollection budget on one sentence and
genuinely forgets everything else -- precisely the damage build 118 was
written to repair, fully returned.

Reading: `retrieve` bumps `last_seen`/`uses` on the records it returns,
but the call site passed a DESERIALIZED copy and never wrote it back.
2,172 of 2,193 live records had `uses == 0`. `prune` ranks by
`salience`, which reads exactly those two fields -- so which memories an
NPC kept was decided by everything except how often they were recalled.

Fixing either alone leaves the loop dead: dedup without persisted recall
still ranks on a frozen signal, and persisted recall without dedup still
spends the budget on copies.
"""
from unittest import TestCase

from world.llm import memory as mem


def _vec(*xs):
    return list(xs)


class TestTheWriteDeduplicates(TestCase):
    def test_the_same_thought_twice_is_one_record(self):
        recs = []
        for _ in range(2):
            recs = mem.remember(recs, "I remember: nothing to eat.",
                                _vec(1.0, 0.0), subject="")
        self.assertEqual(len(recs), 1)

    def test_the_repeat_strengthens_instead_of_duplicating(self):
        """The designed behaviour: a repeated experience becomes a
        STRONG memory rather than a crowd of weak identical ones.

        `make_record` starts `uses` at 0, so N writes give N-1 bumps —
        the first one creates the record rather than recalling it.
        """
        recs = []
        for _ in range(4):
            recs = mem.remember(recs, "I remember: nothing to eat.",
                                _vec(1.0, 0.0), subject="")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["uses"], 3)

    def test_a_different_thought_is_its_own_record(self):
        """The pin: dedup must not collapse distinct memories."""
        recs = mem.remember([], "I remember: A.", _vec(1.0, 0.0), subject="")
        recs = mem.remember(recs, "I remember: B.", _vec(0.0, 1.0), subject="")
        self.assertEqual(len(recs), 2)

    def test_the_thoughts_path_goes_through_remember(self):
        """Structural — the bypass is the defect, and `make_record` +
        `prune` sitting next to each other is what it looks like."""
        import inspect

        import world.souls.thoughts as th
        src = inspect.getsource(th._feed_rag)
        self.assertIn("mem.remember(recs, text, vec", src)
        self.assertNotIn("recs.append(mem.make_record(", src)


class TestRecallIsPersisted(TestCase):
    def test_retrieve_bumps_the_records_it_is_given(self):
        rec = mem.make_record("a thing", _vec(1.0, 0.0), subject="")
        rec["uses"] = 0
        records = [rec]
        hits = mem.retrieve(_vec(1.0, 0.0), records, k=3, subject="")
        self.assertTrue(hits)
        self.assertEqual(records[0]["uses"], 1,
                         "the bump did not land on the caller's list")

    def test_the_bump_is_on_the_same_object_not_a_copy(self):
        """What makes the call-site write-back sufficient: `retrieve`
        mutates the dicts IN the list it was handed, so assigning that
        list back persists the bump."""
        rec = mem.make_record("a thing", _vec(1.0, 0.0), subject="")
        records = [rec]
        hits = mem.retrieve(_vec(1.0, 0.0), records, k=3, subject="")
        self.assertIs(hits[0], records[0])

    def test_a_miss_bumps_nothing(self):
        rec = mem.make_record("a thing", _vec(1.0, 0.0), subject="")
        rec["uses"] = 0
        records = [rec]
        mem.retrieve(_vec(-1.0, 0.0), records, k=3, subject="")
        self.assertEqual(records[0]["uses"], 0)

    def test_the_call_site_writes_the_records_back(self):
        import inspect

        import typeclasses.llm_npc as npc_mod
        src = inspect.getsource(npc_mod)
        self.assertIn("self.db.llm_memories = records", src)


class TestSalienceActuallyVaries(TestCase):
    """Why the loop matters: `prune` ranks on `salience`, which reads
    `uses` and `last_seen`. With `uses` frozen at 0 for every record it
    never varied."""

    def test_a_recalled_memory_outranks_an_unrecalled_one(self):
        old = mem.make_record("unused", _vec(1.0, 0.0), subject="")
        hot = mem.make_record("recalled", _vec(1.0, 0.0), subject="")
        records = [old, hot]
        for _ in range(5):
            mem.retrieve(_vec(1.0, 0.0), [hot], k=1, subject="")
        self.assertGreater(mem.salience(hot), mem.salience(old))
