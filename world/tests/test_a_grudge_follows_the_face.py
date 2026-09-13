"""An NPC that has connected two faces reads them as one person (#3371).

Memory retrieval followed the identity chain since #2410, but the WHO
line the model is handed still read a single face: no aliases from the
other face, and a grudge earned as face A read neutral on face B. Verified
papers were surfaced nowhere on the NPC path.

Owner ruling 2026-09-13, option A: connecting faces is a FULL merge --
aliases union, opinion SUMS across the family (a grudge cannot be
laundered by changing faces) -- and papers something vouched for appear,
matching `recall`'s "Papers:" rows.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls import thoughts


class GrudgeFollowsTheFaceTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Sully", location=self.room1)
        self.patron = self.char1
        # Two faces the NPC has met, later CONNECTED (B -> A).
        self.npc.recognition_memory = {
            "faceA": {"linked_to": None, "attested": []},
            "faceB": {"linked_to": "faceA",
                      "attested": [{"name": "Robert Paulson", "issuer": "Colony Registry",
                                    "protocol": "registry", "verified": True}]},
        }
        self.npc.db.llm_dossiers = {"faceA": {"aliases": ["Billy"]},
                                    "faceB": {"aliases": ["Robert"]}}
        # A grudge earned as face A.
        thoughts.add_opinion(self.npc, "faceA", "attacked_me", -0.80, "pulled a knife on me")

    def line(self, face):
        return self.npc._relationship_line(face, self.patron) or ""

    # --- the defect ---------------------------------------------------------

    def test_grudge_on_face_a_reads_on_face_b(self):
        out = self.line("faceB")
        self.assertNotIn("neutral", out)
        self.assertIn("your read on them", out, "face B read as a clean stranger: %r" % out)
        self.assertIn("knife", out, "the reason did not follow the face")

    def test_aliases_union_across_faces(self):
        out = self.line("faceB")
        self.assertIn("Billy", out); self.assertIn("Robert", out)

    def test_papers_are_surfaced(self):
        out = self.line("faceB")
        self.assertIn("Robert Paulson", out); self.assertIn("Colony Registry", out)

    def test_opinion_sums_across_the_family(self):
        thoughts.add_opinion(self.npc, "faceB", "was_rude", -0.30, "sneered at me")
        single = thoughts.opinion_of(self.npc, "faceB")
        merged = thoughts.opinion_over(self.npc, ["faceA", "faceB"])
        self.assertLess(merged, single, "merged opinion is not the sum")
        self.assertGreaterEqual(merged, -1.0)

    # --- controls ------------------------------------------------------------

    def test_an_unlinked_face_is_unchanged(self):
        thoughts.add_opinion(self.npc, "stranger", "was_civil", 0.10)
        self.npc.db.llm_dossiers["stranger"] = {"aliases": ["Ren"]}
        out = self.line("stranger")
        self.assertIn("Ren", out); self.assertNotIn("Billy", out); self.assertNotIn("Robert", out)

    def test_a_clean_stranger_is_still_none(self):
        self.assertIsNone(self.npc._relationship_line("nobody", self.patron))
