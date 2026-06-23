"""The portable long-term-memory core (world.llm.memory) — pure, no model/Evennia.

Exact cosine top-k retrieval, subject scoping, salience, and pruning.
"""

from unittest import TestCase

from world.llm.memory import (
    cosine, make_record, memory_texts, prune, retrieve, salience,
)


class TestCosine(TestCase):
    def test_identical_vectors(self):
        self.assertAlmostEqual(cosine([1, 0, 0], [1, 0, 0]), 1.0)

    def test_orthogonal(self):
        self.assertAlmostEqual(cosine([1, 0], [0, 1]), 0.0)

    def test_scale_invariant(self):
        self.assertAlmostEqual(cosine([1, 2, 3], [2, 4, 6]), 1.0)

    def test_empty_is_zero(self):
        self.assertEqual(cosine([], [1, 2]), 0.0)


class TestRetrieve(TestCase):
    def _recs(self):
        return [
            make_record("she ordered a negroni", [1, 0, 0], subject="#5", now=100),
            make_record("he flashed a gun", [0, 1, 0], subject="#9", now=100),
            make_record("the lounge was packed", [0, 0, 1], subject="", now=100),
        ]

    def test_top_k_by_similarity(self):
        recs = self._recs()
        hits = retrieve([1, 0, 0], recs, k=1)
        self.assertEqual(hits[0]["text"], "she ordered a negroni")

    def test_subject_scopes_out_other_subjects(self):
        recs = self._recs()
        # scoped to #5, retrieving #5's own record — #9's is never in the pool
        hits = retrieve([1, 0, 0], recs, k=3, subject="#5")
        texts = memory_texts(hits)
        self.assertIn("she ordered a negroni", texts)
        self.assertNotIn("he flashed a gun", texts)        # #9 excluded

    def test_general_memories_visible_to_any_subject(self):
        recs = self._recs()
        hits = retrieve([0, 0, 1], recs, k=3, subject="#5")  # matches general
        self.assertIn("the lounge was packed", memory_texts(hits))

    def test_drops_nonpositive_similarity(self):
        recs = self._recs()
        # a query orthogonal to everything subject #5 can see → no hits
        hits = retrieve([0, 1, 0], [recs[0]], k=3)
        self.assertEqual(hits, [])

    def test_recall_bumps_uses_and_last_seen(self):
        recs = self._recs()
        hit = retrieve([1, 0, 0], recs, k=1, now=500)[0]
        self.assertEqual(hit["uses"], 1)
        self.assertEqual(hit["last_seen"], 500)


class TestSalienceAndPrune(TestCase):
    def test_recency_decays(self):
        from world.llm.memory import RECENCY_HALFLIFE
        rec = make_record("x", [1], now=0)
        fresh = salience(rec, now=0)
        half = salience(rec, now=RECENCY_HALFLIFE)
        self.assertAlmostEqual(half, fresh / 2, places=2)

    def test_uses_raise_salience(self):
        a = make_record("a", [1], now=0)
        b = make_record("b", [1], now=0)
        b["uses"] = 5
        self.assertGreater(salience(b, now=0), salience(a, now=0))

    def test_prune_caps_per_subject_keeping_salient(self):
        now = 1000
        recs = []
        for i in range(5):
            r = make_record(f"m{i}", [1], subject="#5", now=now - i * 10)
            recs.append(r)
        # also another subject, untouched by #5's cap
        recs.append(make_record("other", [1], subject="#9", now=now))
        kept = prune(recs, cap_per_subject=2, now=now)
        subj5 = [r for r in kept if r["subject"] == "#5"]
        self.assertEqual(len(subj5), 2)                 # capped
        self.assertIn("m0", [r["text"] for r in subj5])  # freshest survives
        self.assertEqual(len([r for r in kept if r["subject"] == "#9"]), 1)
