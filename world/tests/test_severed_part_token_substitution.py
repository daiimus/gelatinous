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
        # (anatomical order: hair, face, left_eye) — no newline between.
        self.assertIn(
            "Close-cropped silver hair. A weathered face. "
            "A pale blue left eye.",
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
        # Face longdesc precedes the eye longdesc (anatomical order)...
        self.assertLess(face_idx, eye_idx)
        # ...and the face wound text renders in the gap between them,
        # keeping the wound connected to the face location.
        between = out[face_idx + len("A weathered face."):eye_idx]
        self.assertTrue(
            between.strip(),
            "Expected the face wound description to render between the "
            "face longdesc and the eye longdesc.",
        )

