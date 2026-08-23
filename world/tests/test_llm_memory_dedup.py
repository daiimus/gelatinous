"""A repeat is one memory remembered twice, not two memories (#2242).

Found live. The dispatcher's memory held 35 records, of which 29 were
byte-identical copies of "I remember: nothing to eat I could reach or
afford" — spilled by a travel fault that retried every three minutes.
`DEFAULT_CAP_PER_SUBJECT` is 30, so prune was spending almost its whole
budget on one sentence and genuinely forgetting everything else to keep
it.

Worse, the same append-blindly path stored an NPC's own fabricated
line, which retrieval then fed back as a template — so a hallucination
became canon and re-stored itself on every repetition.
"""
import time

from evennia.utils.test_resources import EvenniaCommandTest

from world.llm import memory as mem


class TestRememberingTwice(EvenniaCommandTest):
    def _vec(self, n=1.0):
        return [n, 0.0, 0.0]

    def test_the_same_thing_twice_is_one_memory(self):
        recs = []
        recs = mem.remember(recs, "the till came up short", self._vec())
        recs = mem.remember(recs, "the till came up short", self._vec())
        self.assertEqual(len(recs), 1)

    def test_but_it_is_remembered_harder(self):
        """Recall is what `salience` rewards, so a thing that keeps
        happening becomes strong rather than numerous."""
        recs = mem.remember([], "the till came up short", self._vec())
        first = dict(recs[0])
        recs = mem.remember(recs, "the till came up short", self._vec(),
                            now=time.time() + 60)
        self.assertEqual(recs[0]["uses"], first["uses"] + 1)
        self.assertGreater(recs[0]["last_seen"], first["last_seen"])

    def test_whitespace_does_not_make_it_a_new_memory(self):
        recs = mem.remember([], "the till   came up short", self._vec())
        recs = mem.remember(recs, "the till came up  short", self._vec())
        self.assertEqual(len(recs), 1)

    def test_different_things_are_different_memories(self):
        recs = mem.remember([], "the till came up short", self._vec())
        recs = mem.remember(recs, "a night behind my own door", self._vec())
        self.assertEqual(len(recs), 2)

    def test_the_same_words_about_different_people_are_separate(self):
        """Subject scoping is how "what I recall about THIS person"
        works — two people can both have been rude to me."""
        recs = mem.remember([], "they were rude", self._vec(), subject="a")
        recs = mem.remember(recs, "they were rude", self._vec(), subject="b")
        self.assertEqual(len(recs), 2)

    def test_a_flood_cannot_crowd_out_a_real_memory(self):
        """The live failure: 29 copies of one line inside a cap of 30."""
        recs = mem.remember([], "a night behind my own door", self._vec(2.0))
        for _ in range(60):
            recs = mem.remember(recs, "nothing to eat I could reach",
                                self._vec())
        texts = [r["text"] for r in recs]
        self.assertIn("a night behind my own door", texts)
        self.assertEqual(len(recs), 2)
