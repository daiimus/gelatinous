"""Tests for the pronoun / name token helper (issue #234).

Covers :func:`world.anatomy.longdesc_tokens.substitute_pronoun_tokens`,
the single source of brace-token substitution shared by
:class:`typeclasses.corpse.Corpse` and
:class:`typeclasses.items.Appendage`.

Run via::

    evennia test world.tests.test_longdesc_tokens
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import substitute_pronoun_tokens


class TestSubstitutePronounTokens(TestCase):
    def test_male_pronoun_set_exact(self):
        out = substitute_pronoun_tokens(
            "{They}/{they} {Their}/{their} {Them}/{them} "
            "{Theirs}/{theirs} {Themselves}/{themselves} "
            "{Themself}/{themself}",
            gender="male",
        )
        self.assertEqual(
            out,
            "He/he His/his Him/him His/his Himself/himself Himself/himself",
        )

    def test_female_pronoun_set_exact(self):
        out = substitute_pronoun_tokens(
            "{They}/{they} {Their}/{their} {Them}/{them} "
            "{Theirs}/{theirs} {Themselves}/{themselves} "
            "{Themself}/{themself}",
            gender="female",
        )
        self.assertEqual(
            out,
            "She/she Her/her Her/her Hers/hers Herself/herself "
            "Herself/herself",
        )

    def test_plural_pronoun_set_exact(self):
        out = substitute_pronoun_tokens(
            "{They}/{they} {Their}/{their} {Them}/{them} "
            "{Theirs}/{theirs} {Themselves}/{themselves} "
            "{Themself}/{themself}",
            gender="neutral",
        )
        self.assertEqual(
            out,
            "They/they Their/their Them/them Theirs/theirs "
            "Themselves/themselves Themselves/themselves",
        )

    def test_unknown_gender_falls_back_to_plural(self):
        out = substitute_pronoun_tokens("{Their} eyes.", gender="cylon")
        self.assertEqual(out, "Their eyes.")

    def test_none_gender_falls_back_to_plural(self):
        out = substitute_pronoun_tokens("{Their} eyes.", gender=None)
        self.assertEqual(out, "Their eyes.")

    def test_name_token(self):
        out = substitute_pronoun_tokens(
            "{name} stares.", gender="male", name="Vasquez"
        )
        self.assertEqual(out, "Vasquez stares.")

    def test_name_possessive_token(self):
        out = substitute_pronoun_tokens(
            "{name's} cold stare.", gender="male", name="Vasquez"
        )
        self.assertEqual(out, "Vasquez's cold stare.")

    def test_name_and_possessive_together(self):
        out = substitute_pronoun_tokens(
            "{name} flexes {name's} fingers.",
            gender="female",
            name="Ripley",
        )
        self.assertEqual(out, "Ripley flexes Ripley's fingers.")

    def test_default_name_is_the_corpse(self):
        out = substitute_pronoun_tokens("{name} lies still.", gender=None)
        self.assertEqual(out, "the corpse lies still.")

    def test_no_tokens_passthrough(self):
        text = "A weathered scar runs along the jaw."
        self.assertEqual(
            substitute_pronoun_tokens(text, gender="male"), text
        )

    def test_unrecognised_tokens_left_untouched(self):
        # {color} is handled by an upstream corpse/clothing layer, not
        # here — the helper must leave it intact.
        out = substitute_pronoun_tokens(
            "{color}A {their} coat.", gender="female"
        )
        self.assertEqual(out, "{color}A her coat.")

    def test_empty_string_passthrough(self):
        self.assertEqual(substitute_pronoun_tokens("", gender="male"), "")

    def test_none_text_passthrough(self):
        self.assertIsNone(substitute_pronoun_tokens(None, gender="male"))
