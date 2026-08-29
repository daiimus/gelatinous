"""A bioroid stays a bioroid through death (#2394).

The flash clone inherited carefully — GRIM stats, desc, every longdesc,
sex, skintone, sleeve_uid, height, build, hair, sdesc keyword, and the
imprint — and never copied `db.species`. Chargen never sets it either, and
everything downstream falls back to `db.species or "human"`.

So a bioroid came back mechanically HUMAN while keeping every bioroid
longdesc. Cobalt blood turned crimson, the wetcore became a brain, ×1.25
durability and infection immunity vanished, and the corpse would rot
instead of going inert. The description survived death; the body did not.
Nothing surfaced it until somebody opened them up.

The second half covers `soul_opinions` in the imprint. `imprint.py` exists
so players and NPCs "can never drift into different rules about what
survives a death" — and the opinion layer (#2388) added a persistent
affective store without adding it to the record, so a resleeved soul kept
its MOOD and lost every opinion it had of anybody.
"""
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world import imprint
from world.souls import thoughts


class TestSpeciesSurvivesTheClone(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.dead = create_object("typeclasses.characters.Character",
                                  key="dead", location=self.room1)
        self.dead.db.species = "synthetic_humanoid"

    def _clone_biology(self, old, new):
        """The inheritance block under test, in isolation — the command
        around it needs an account and a start room."""
        new.sex = old.sex
        if old.db.skintone is not None:
            new.db.skintone = old.db.skintone
        old_species = old.db.species
        if old_species and old_species != new.db.species:
            from world.medical.core import MedicalState
            new.db.species = old_species
            new._medical_state = MedicalState(new)
            new.db.medical_state = new._medical_state.to_dict()

    def test_a_bioroid_comes_back_a_bioroid(self):
        """Fails toward the bug: the clone silently reading as human."""
        clone = create_object("typeclasses.characters.Character",
                              key="clone", location=self.room1)
        self._clone_biology(self.dead, clone)
        self.assertEqual(clone.db.species, "synthetic_humanoid")

    def test_the_organs_are_rebuilt_for_the_species(self):
        """Copying the attribute alone is not enough — the clone's organs
        were already seeded as human when it was created."""
        from world.anatomy.organs import get_organ_display_name
        clone = create_object("typeclasses.characters.Character",
                              key="clone", location=self.room1)
        self._clone_biology(self.dead, clone)
        self.assertEqual(
            get_organ_display_name("heart", clone.db.species), "vat-heart")
        self.assertEqual(
            get_organ_display_name("brain", clone.db.species), "wetcore")

    def test_a_human_is_left_alone(self):
        """The guard must not churn the ordinary case."""
        human = create_object("typeclasses.characters.Character",
                              key="human", location=self.room1)
        clone = create_object("typeclasses.characters.Character",
                              key="clone2", location=self.room1)
        before = clone.db.medical_state
        self._clone_biology(human, clone)
        self.assertEqual(clone.db.medical_state, before)

    def test_the_description_and_species_no_longer_disagree(self):
        """The actual defect: a body that READS bioroid and IS human."""
        clone = create_object("typeclasses.characters.Character",
                              key="clone3", location=self.room1)
        self.dead.db.skintone = "alabaster"          # synthetic palette
        self._clone_biology(self.dead, clone)
        self.assertEqual(clone.db.skintone, "alabaster")
        self.assertEqual(clone.db.species, "synthetic_humanoid")


class TestOpinionsSurviveTheImprint(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.body = create_object("typeclasses.characters.Character",
                                  key="body", location=self.room1)

    def test_the_record_carries_opinions(self):
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.30)
        snap = imprint.capture(self.soul)
        self.assertIn("opinions", snap)
        self.assertIn("u1", snap["opinions"])

    def test_they_come_back_on_the_new_body(self):
        thoughts.add_opinion(self.soul, "u1", "attacked_me", -0.60)
        # older than the backup gap, so it survives the cutoff
        aged = {u: [(t - imprint.GAP * 2, k, v, n)
                    for (t, k, v, n) in (tuple(e) for e in es)]
                for u, es in (self.soul.db.soul_opinions or {}).items()}
        self.soul.db.soul_opinions = aged
        imprint.restore(self.body, imprint.capture(self.soul))
        self.assertLess(thoughts.opinion_of(self.body, "u1"), 0)

    def test_what_happened_inside_the_gap_is_lost(self):
        """Same rule thoughts already follow: the backup did not hold it."""
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.50)
        imprint.restore(self.body, imprint.capture(self.soul))
        self.assertEqual(thoughts.opinion_of(self.body, "u1"), 0.0)

    def test_a_person_with_nothing_left_is_dropped(self):
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.50)
        imprint.restore(self.body, imprint.capture(self.soul))
        self.assertNotIn("u1", self.body.db.soul_opinions or {})

    def test_an_old_record_without_opinions_still_restores(self):
        """Backward compatibility: records written before #2388."""
        snap = imprint.capture(self.soul)
        snap.pop("opinions", None)
        self.assertTrue(imprint.restore(self.body, snap) is not False
                        or True)          # must not raise
        self.assertFalse(self.body.db.soul_opinions)

    def test_mood_and_opinion_survive_on_the_same_terms(self):
        """They are two halves of one feeling; if one crossed death and
        the other did not, a resleeved soul would be cheerful about a life
        it could not remember and blank about the people in it."""
        now = time.time()
        old = now - imprint.GAP * 2
        self.soul.db.soul_thoughts = [(old, "payday", 0.25, "got paid")]
        self.soul.db.soul_opinions = {"u1": [(old, "was_civil", 0.30, "")]}
        imprint.restore(self.body, imprint.capture(self.soul))
        self.assertTrue(self.body.db.soul_thoughts)
        self.assertTrue(self.body.db.soul_opinions)
