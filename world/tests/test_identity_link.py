"""Memories follow the identity chain (#2410).

Memory is keyed on the PERCEIVED identity, which is correct — a disguise
should read as a stranger. But once an NPC has connected two presentations,
whether by piercing a disguise or by being shown papers, what it was told
under one face has to be recallable under the other.

`retrieve` filtered on a single exact uid, so the `linked_to` chain existed
and nothing consulted it: you could pierce someone's disguise and still not
recall what they had told you an hour earlier wearing it.

The paper route to the same conclusion is deliberately narrow — two sets of
VERIFIED COLONY papers agreeing on a name. Linking asserts "these are one
person" and merges what you recall about them; names are nowhere near unique
enough for a weaker rule.
"""
from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world import identity
from world.llm import memory as mem


class TestRecallSpansTheChain(BaseEvenniaTest):

    def _rec(self, subject, text):
        return mem.make_record(text, [1.0, 0.0, 0.0], subject=subject)

    def test_a_single_subject_still_filters(self):
        records = [self._rec("face-a", "told me about the crane"),
                   self._rec("face-b", "something else entirely")]
        hits = mem.retrieve([1.0, 0.0, 0.0], records, k=5, subject="face-a")
        self.assertEqual([h["text"] for h in hits],
                         ["told me about the crane"])

    def test_a_chain_reaches_both_faces(self):
        """The point: what they told you wearing the mask."""
        records = [self._rec("face-a", "told me about the crane"),
                   self._rec("face-b", "asked after the Rook")]
        hits = mem.retrieve([1.0, 0.0, 0.0], records, k=5,
                            subject=["face-a", "face-b"])
        self.assertEqual(len(hits), 2)

    def test_general_memories_stay_visible(self):
        records = [self._rec("", "the bar floods on Tuesdays")]
        hits = mem.retrieve([1.0, 0.0, 0.0], records, k=5,
                            subject=["face-a", "face-b"])
        self.assertEqual(len(hits), 1)

    def test_an_unrelated_face_is_still_excluded(self):
        records = [self._rec("stranger", "nothing to do with them")]
        hits = mem.retrieve([1.0, 0.0, 0.0], records, k=5,
                            subject=["face-a", "face-b"])
        self.assertEqual(hits, [])


class TestPapersLinkFaces(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.obs = create_object("typeclasses.characters.Character",
                                 key="obs", location=self.room1)
        mem_ = {}
        for uid in ("face-a", "face-b"):
            mem_[uid] = {"assigned_name": "", "attested": [],
                         "times_seen": 1, "linked_to": None}
        self.obs.recognition_memory = mem_

    def _papers(self, uid, name, authority="colony", verified=True):
        return identity.attest(self.obs, uid, name, issuer="Registry",
                               authority=authority, verified=verified)

    def test_two_sets_of_official_papers_connect_the_faces(self):
        self._papers("face-a", "Robert Paulson")
        self._papers("face-b", "Robert Paulson")
        chain = identity.walk_linked_chain(self.obs.recognition_memory,
                                           "face-b")
        self.assertIn("face-a", chain)

    def test_a_club_card_is_not_enough(self):
        """Commercial papers attest honestly but do not identify a person."""
        self._papers("face-a", "Blade", authority="commercial")
        self._papers("face-b", "Blade", authority="commercial")
        self.assertIsNone(
            self.obs.recognition_memory["face-b"].get("linked_to"))

    def test_a_broken_seal_links_nothing(self):
        self._papers("face-a", "Robert Paulson")
        self._papers("face-b", "Robert Paulson", verified=False)
        self.assertIsNone(
            self.obs.recognition_memory["face-b"].get("linked_to"))

    def test_different_names_are_left_apart(self):
        self._papers("face-a", "Robert Paulson")
        self._papers("face-b", "Ilse Vandermeer")
        self.assertIsNone(
            self.obs.recognition_memory["face-b"].get("linked_to"))

    def test_an_existing_link_is_not_rewritten(self):
        """Never re-point a chain somebody or something else established."""
        m = self.obs.recognition_memory
        m["face-b"]["linked_to"] = "face-z"
        self.obs.recognition_memory = m
        self._papers("face-a", "Robert Paulson")
        self._papers("face-b", "Robert Paulson")
        self.assertEqual(
            self.obs.recognition_memory["face-b"]["linked_to"], "face-z")


class TestTheFamilyIsSymmetric(BaseEvenniaTest):
    """`walk_linked_chain` follows `linked_to` forward, which is right for
    history. Recall needs both directions: which face you happen to be
    looking at must not decide whether you can remember somebody."""

    def _mem(self):
        return {
            "face-a": {"linked_to": None, "attested": []},
            "face-b": {"linked_to": "face-a", "attested": []},
            "face-c": {"linked_to": "face-b", "attested": []},
            "stranger": {"linked_to": None, "attested": []},
        }

    def test_forward_still_works(self):
        fam = identity.linked_family(self._mem(), "face-c")
        self.assertEqual(set(fam), {"face-a", "face-b", "face-c"})

    def test_backward_reaches_the_others(self):
        """The gap: A is pointed AT by B, and a forward walk from A finds
        nothing."""
        self.assertEqual(identity.walk_linked_chain(self._mem(), "face-a"),
                         ["face-a"])
        fam = identity.linked_family(self._mem(), "face-a")
        self.assertEqual(set(fam), {"face-a", "face-b", "face-c"})

    def test_an_unconnected_face_stays_alone(self):
        self.assertEqual(identity.linked_family(self._mem(), "stranger"),
                         ["stranger"])

    def test_an_unknown_uid_is_returned_as_itself(self):
        self.assertEqual(identity.linked_family(self._mem(), "nobody"),
                         ["nobody"])

    def test_a_cycle_terminates(self):
        m = {"a": {"linked_to": "b"}, "b": {"linked_to": "a"}}
        self.assertEqual(set(identity.linked_family(m, "a")), {"a", "b"})
