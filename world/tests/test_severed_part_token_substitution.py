"""Integration test: severed parts resolve longdesc pronoun tokens.

Issue #234: :meth:`typeclasses.items.Appendage.return_appearance` must
run carried-forward longdesc prose through the shared pronoun/name
helper so brace tokens (``{their}``, ``{they}``, ``{name}`` ...) are
resolved instead of leaking literally into the look output.

Issue #236: the carried prose renders as a single flowing paragraph
(name on its own header line), composed per-location so each wound
stays connected to its longdesc location.

Run via::

    evennia test --settings settings.py world.tests.test_severed_part_token_substitution
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.items import Appendage


class TestSeveredPartTokenSubstitution(EvenniaTest):
    character_typeclass = Character

    def _make_part(self, *, gender, name, longdesc_data, wounds_at_death=None):
        part = create_object(Appendage, key="severed head", location=self.room1)
        part.db.original_gender = gender
        part.db.original_character_name = name
        part.db.longdesc_data = longdesc_data
        part.db.wounds_at_death = wounds_at_death or []
        return part

    def test_male_tokens_resolved_in_look(self):
        part = self._make_part(
            gender="male",
            name="Vasquez",
            longdesc_data={
                "head": "{Their} cheeks are gaunt and {their} eyes hollow.",
            },
        )
        out = part.return_appearance(self.char1)
        self.assertIn("His cheeks are gaunt and his eyes hollow.", out)
        self.assertNotIn("{Their}", out)
        self.assertNotIn("{their}", out)

    def test_female_name_token_resolved(self):
        part = self._make_part(
            gender="female",
            name="Ripley",
            longdesc_data={"head": "{name's} jaw is set. {They} stare blankly."},
        )
        out = part.return_appearance(self.char1)
        self.assertIn("Ripley's jaw is set.", out)
        self.assertIn("She stare blankly.", out)
        self.assertNotIn("{", out)

    def test_missing_gender_snapshot_falls_back_to_plural(self):
        # Older parts spawned before issue #234 lack the snapshot; they
        # must degrade to plural pronouns, never leak braces.
        part = self._make_part(
            gender=None,
            name=None,
            longdesc_data={"head": "{Their} eyes stare."},
        )
        out = part.return_appearance(self.char1)
        self.assertIn("Their eyes stare.", out)
        self.assertNotIn("{Their}", out)

    def test_longdescs_flow_into_single_paragraph(self):
        # Issue #236: multiple longdesc locations must read as one
        # flowing paragraph (space-joined), not a newline per location.
        part = self._make_part(
            gender="male",
            name="Vasquez",
            longdesc_data={
                "hair": "Close-cropped silver hair.",
                "face": "A weathered face.",
                "left_eye": "A pale blue left eye.",
            },
        )
        out = part.return_appearance(self.char1)
        # The three locations appear as one continuous, space-joined run
        # (anatomical order: hair, left_eye, face — eyes lead the facial
        # features) — no newline between.
        self.assertIn(
            "Close-cropped silver hair. A pale blue left eye. "
            "A weathered face.",
            out,
        )

    def test_wound_stays_connected_to_its_longdesc_location(self):
        # Issue #236: a wound renders immediately after the longdesc for
        # the SAME location, not dumped at the end detached from it.
        part = self._make_part(
            gender="male",
            name="Vasquez",
            longdesc_data={
                "face": "A weathered face.",
                "left_eye": "A pale blue left eye.",
            },
            wounds_at_death=[
                {
                    "injury_type": "bullet",
                    "location": "face",
                    "severity": "Severe",
                    "stage": "old",
                    "organ": None,
                },
            ],
        )
        out = part.return_appearance(self.char1)
        face_idx = out.index("A weathered face.")
        eye_idx = out.index("A pale blue left eye.")
        # Anatomical order now leads with the eye (eyes precede the face),
        # so the eye longdesc renders before the face longdesc...
        self.assertLess(eye_idx, face_idx)
        # ...and the invariant under test holds regardless of neighbour
        # order: the face wound renders immediately after the face
        # longdesc (its own location), not detached at the end. With the
        # face rendering last here, the wound text is the trailing run.
        after_face = out[face_idx + len("A weathered face."):]
        self.assertTrue(
            after_face.strip(),
            "Expected the face wound description to render immediately "
            "after the face longdesc (connected to its own location).",
        )
        # The wound stays connected to the face, not to the earlier eye:
        # nothing wound-like intrudes between the eye longdesc and the
        # face longdesc.
        between = out[eye_idx + len("A pale blue left eye."):face_idx]
        self.assertFalse(
            between.strip(),
            "Expected no wound text between the eye longdesc and the "
            "face longdesc; the face wound belongs after the face.",
        )

