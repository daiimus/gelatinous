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

    def test_multiword_braces_left_untouched(self):
        # Multi-word braces aren't candidates for noun/verb flex, so the
        # helper leaves them literal — useful for in-prose emphasis or
        # future substitutions an upstream layer claims.
        out = substitute_pronoun_tokens(
            "A {patch of red} on {their} jaw.", gender="female"
        )
        self.assertEqual(out, "A {patch of red} on her jaw.")

    def test_empty_string_passthrough(self):
        self.assertEqual(substitute_pronoun_tokens("", gender="male"), "")

    def test_none_text_passthrough(self):
        self.assertIsNone(substitute_pronoun_tokens(None, gender="male"))


class TestBodyNounFlex(TestCase):
    """Pair-noun and verb flexing — issue #319.

    Body-noun tokens like ``{eyes}`` / ``{ears}`` and braced verbs like
    ``{accent}`` / ``{move}`` resolve to the requested grammatical
    *number*.  Pre-#319 the helper handled only pronouns and left these
    literal, which leaked braces into corpse / Appendage prose.

    Note on ``{color}``: the helper now flexes any single-word brace
    that isn't a known body noun as a verb (mirroring the living
    renderer).  Consumers that use ``{color}`` as a placeholder (corpse,
    Appendage) substitute it BEFORE calling this helper.
    """

    def test_plural_body_noun_flexes(self):
        out = substitute_pronoun_tokens(
            "{Their} bright brown {eyes}.", gender="female", number="plural"
        )
        self.assertEqual(out, "Her bright brown eyes.")

    def test_singular_body_noun_flexes(self):
        out = substitute_pronoun_tokens(
            "{Their} bright brown {eyes}.", gender="female", number="singular"
        )
        self.assertEqual(out, "Her bright brown eye.")

    def test_braced_verb_flexes_plural(self):
        out = substitute_pronoun_tokens(
            "{Their} {hands} {move}.", gender="male", number="plural"
        )
        self.assertEqual(out, "His hands move.")

    def test_braced_verb_flexes_singular(self):
        out = substitute_pronoun_tokens(
            "{Their} {hands} {move}.", gender="male", number="singular"
        )
        self.assertEqual(out, "His hand moves.")

    def test_irregular_verb_are_to_is(self):
        out = substitute_pronoun_tokens(
            "{Their} {eyes} {are} bright.", gender="female",
            number="singular",
        )
        self.assertEqual(out, "Her eye is bright.")

    def test_number_default_is_singular(self):
        # Existing callers (Appendage) don't pass ``number``; default
        # must be singular to match their single-side semantics.
        out = substitute_pronoun_tokens(
            "{Their} {eyes}.", gender="female"
        )
        self.assertEqual(out, "Her eye.")

    def test_all_pair_keys_flex_plural(self):
        # Every PAIR_MERGE_KEYS noun must flex correctly so mob_flavor
        # entries render across all paired locations.
        for noun in ("eyes", "ears", "arms", "hands", "thighs", "shins",
                     "feet"):
            with self.subTest(noun=noun):
                out = substitute_pronoun_tokens(
                    f"{{Their}} {{{noun}}}.", gender="male", number="plural"
                )
                self.assertEqual(out, f"His {noun}.")
