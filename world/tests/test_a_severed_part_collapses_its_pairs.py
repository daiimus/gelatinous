"""A severed part reads its paired locations the way the body did (#3578).

Owner ruling (2026-09-16): a part displays "just like it does on a
character". The living body and the corpse collapse two identical
paired longdescs into one plural line -- "His eyes are", not "His eye
is" twice -- and read a lone side with its side. The part rendered each
side separately and unsided. This pins the collapse on a real
:class:`typeclasses.items.Appendage` through ``return_appearance``, the
path a player's ``look`` takes.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

EYE = ("{Their} {eyes} {are} a pale backlit brown, the iris ringed by a "
       "focusing aperture.")
EAR = "{Their} {ears} {sit} close to the skull, moulded rather than grown."


class _Head(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.part = create_object("typeclasses.items.Appendage",
                                  key="human head", location=self.room1)
        self.part.db.desc = "A severed human head."
        self.part.db.location_name = "head"
        self.part.db.original_gender = "male"
        self.part.db.original_character_name = "Iver"
        self.part.db.source_species = "human"
        self.part.db.longdesc_data = {
            "left_eye": EYE, "right_eye": EYE,
            "left_ear": EAR, "right_ear": EAR,
            "neck": "A maker's stamp sits below the collar line.",
        }

    def look(self):
        return self.part.return_appearance(self.char1)


class TestIdenticalPairsCollapse(_Head):
    def test_eyes_and_ears_read_once_in_the_plural(self):
        text = self.look()
        self.assertEqual(text.count("His eyes are a pale backlit brown"), 1, text)
        self.assertEqual(text.count("His ears sit close to the skull"), 1, text)
        self.assertNotIn("His left eye", text)
        self.assertNotIn("His right eye", text)
        self.assertNotIn("His eye is", text)
        self.assertIn("A maker's stamp", text)


class TestDifferentSidesReadWithTheirSide(_Head):
    def test_two_eyes_two_sided_lines(self):
        self.part.db.longdesc_data["right_eye"] = (
            "{Their} {eyes} {are} a dull grey, the aperture seized.")
        text = self.look()
        self.assertIn("His left eye is a pale backlit brown", text)
        self.assertIn("His right eye is a dull grey", text)
        self.assertNotIn("His eyes are", text)


class TestACoveredSideBreaksTheCollapse(_Head):
    def test_monocle_over_the_left_eye(self):
        monocle = create_object("typeclasses.items.Item", key="brass monocle",
                                location=self.part)
        monocle.db.worn_desc = "A brass monocle is screwed into {their} left eye."
        monocle.db.coverage = ["left_eye"]
        self.part.db.worn_items = {"left_eye": [monocle]}
        text = self.look()
        self.assertEqual(text.count("A brass monocle is screwed into his left eye."), 1, text)
        self.assertIn("His right eye is a pale backlit brown", text)
        self.assertNotIn("His eyes are", text)
        self.assertNotIn("His left eye is", text)
        self.assertNotIn("You see", text)
        self.assertNotIn("still wears", text)
        # the ears, untouched, still collapse
        self.assertEqual(text.count("His ears sit close to the skull"), 1, text)
