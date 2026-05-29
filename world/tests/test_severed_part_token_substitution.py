"""Integration test: severed parts resolve longdesc pronoun tokens.

Issue #234: :meth:`typeclasses.items.Appendage.return_appearance` must
run carried-forward longdesc prose through the shared pronoun/name
helper so brace tokens (``{their}``, ``{they}``, ``{name}`` ...) are
resolved instead of leaking literally into the look output.

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

    def _make_part(self, *, gender, name, longdesc_data):
        part = create_object(Appendage, key="severed head", location=self.room1)
        part.db.original_gender = gender
        part.db.original_character_name = name
        part.db.longdesc_data = longdesc_data
        part.db.wounds_at_death = []
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
        self.assertNotIn("{", out.split("\n")[-1])

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
