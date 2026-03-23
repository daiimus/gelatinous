"""
Tests for the Grammar Engine (``world/grammar.py``).

Pure unit tests with no Evennia dependencies.  Run via::

    evennia test world.tests.test_grammar

All test cases match the specification in ``specs/EMOTE_POSE_SPEC.md``
§Grammar Engine and Appendices A/B.
"""

from unittest import TestCase

from world.grammar import (
    GENDER_MAP,
    capitalize_first,
    conjugate_third_person,
    get_article,
    possessive,
    transform_pronoun,
)


# -----------------------------------------------------------------------
# Verb Conjugation
# -----------------------------------------------------------------------


class TestVerbConjugation(TestCase):
    """Tests for ``conjugate_third_person``."""

    # -- Irregular verbs -------------------------------------------------

    def test_irregular_be(self) -> None:
        self.assertEqual(conjugate_third_person("be"), "is")

    def test_irregular_have(self) -> None:
        self.assertEqual(conjugate_third_person("have"), "has")

    def test_irregular_capitalised(self) -> None:
        """Capitalisation of the input should be preserved."""
        self.assertEqual(conjugate_third_person("Be"), "Is")
        self.assertEqual(conjugate_third_person("Have"), "Has")

    # -- Rule 1: Sibilant endings (+es) ---------------------------------

    def test_sibilant_s(self) -> None:
        self.assertEqual(conjugate_third_person("pass"), "passes")

    def test_sibilant_sh(self) -> None:
        self.assertEqual(conjugate_third_person("push"), "pushes")

    def test_sibilant_ch(self) -> None:
        self.assertEqual(conjugate_third_person("catch"), "catches")

    def test_sibilant_x(self) -> None:
        self.assertEqual(conjugate_third_person("fix"), "fixes")

    def test_sibilant_z(self) -> None:
        self.assertEqual(conjugate_third_person("buzz"), "buzzes")

    # -- Rule 2: -O ending (+es) ----------------------------------------

    def test_o_ending_go(self) -> None:
        self.assertEqual(conjugate_third_person("go"), "goes")

    def test_o_ending_do(self) -> None:
        self.assertEqual(conjugate_third_person("do"), "does")

    def test_o_ending_echo(self) -> None:
        self.assertEqual(conjugate_third_person("echo"), "echoes")

    # -- Rule 3: Consonant + y → ies ------------------------------------

    def test_consonant_y_try(self) -> None:
        self.assertEqual(conjugate_third_person("try"), "tries")

    def test_consonant_y_carry(self) -> None:
        self.assertEqual(conjugate_third_person("carry"), "carries")

    def test_consonant_y_fly(self) -> None:
        self.assertEqual(conjugate_third_person("fly"), "flies")

    def test_consonant_y_cry(self) -> None:
        self.assertEqual(conjugate_third_person("cry"), "cries")

    # -- Rule 3 negative: Vowel + y → just +s ---------------------------

    def test_vowel_y_play(self) -> None:
        self.assertEqual(conjugate_third_person("play"), "plays")

    def test_vowel_y_say(self) -> None:
        self.assertEqual(conjugate_third_person("say"), "says")

    def test_vowel_y_enjoy(self) -> None:
        self.assertEqual(conjugate_third_person("enjoy"), "enjoys")

    def test_vowel_y_stay(self) -> None:
        self.assertEqual(conjugate_third_person("stay"), "stays")

    # -- Rule 4: Default (+s) -------------------------------------------

    def test_default_lean(self) -> None:
        self.assertEqual(conjugate_third_person("lean"), "leans")

    def test_default_run(self) -> None:
        self.assertEqual(conjugate_third_person("run"), "runs")

    def test_default_walk(self) -> None:
        self.assertEqual(conjugate_third_person("walk"), "walks")

    def test_default_nod(self) -> None:
        self.assertEqual(conjugate_third_person("nod"), "nods")

    def test_default_scratch(self) -> None:
        # "scratch" ends in "ch" → actually rule 1 (sibilant)
        self.assertEqual(conjugate_third_person("scratch"), "scratches")

    def test_default_sigh(self) -> None:
        self.assertEqual(conjugate_third_person("sigh"), "sighs")

    def test_default_mutter(self) -> None:
        self.assertEqual(conjugate_third_person("mutter"), "mutters")

    def test_default_shout(self) -> None:
        self.assertEqual(conjugate_third_person("shout"), "shouts")

    def test_default_ask(self) -> None:
        self.assertEqual(conjugate_third_person("ask"), "asks")

    def test_default_wave(self) -> None:
        self.assertEqual(conjugate_third_person("wave"), "waves")

    def test_default_fold(self) -> None:
        self.assertEqual(conjugate_third_person("fold"), "folds")

    def test_default_dive(self) -> None:
        """Participle 'diving' wouldn't be marked, but 'dive' should work."""
        self.assertEqual(conjugate_third_person("dive"), "dives")

    # -- Edge case: already-conjugated input -----------------------------

    def test_nonsense_verb(self) -> None:
        """Unknown words receive regular treatment — never refused."""
        self.assertEqual(conjugate_third_person("zorp"), "zorps")


# -----------------------------------------------------------------------
# Article Handling
# -----------------------------------------------------------------------


class TestArticles(TestCase):
    """Tests for ``get_article``."""

    def test_indefinite_a(self) -> None:
        self.assertEqual(get_article("lanky man"), "a")

    def test_indefinite_an(self) -> None:
        self.assertEqual(get_article("athletic dame"), "an")

    def test_indefinite_an_elegant(self) -> None:
        self.assertEqual(get_article("elegant figure"), "an")

    def test_definite(self) -> None:
        self.assertEqual(get_article("lanky man", definite=True), "the")

    def test_definite_ignores_phonetics(self) -> None:
        self.assertEqual(get_article("athletic dame", definite=True), "the")


# -----------------------------------------------------------------------
# Pronoun Transformation
# -----------------------------------------------------------------------


class TestPronounTransformation(TestCase):
    """Tests for ``transform_pronoun``.

    Tables from spec Appendices B.1 and B.2.
    """

    # -- First → Second person (actor self-view) -------------------------

    def test_first_to_second_I(self) -> None:
        self.assertEqual(transform_pronoun("I", "second"), "you")

    def test_first_to_second_me(self) -> None:
        self.assertEqual(transform_pronoun("me", "second"), "you")

    def test_first_to_second_my(self) -> None:
        self.assertEqual(transform_pronoun("my", "second"), "your")

    def test_first_to_second_mine(self) -> None:
        self.assertEqual(transform_pronoun("mine", "second"), "yours")

    def test_first_to_second_myself(self) -> None:
        self.assertEqual(transform_pronoun("myself", "second"), "yourself")

    # -- First → Third person (male) ------------------------------------

    def test_first_to_third_male_I(self) -> None:
        self.assertEqual(transform_pronoun("I", "third", "male"), "he")

    def test_first_to_third_male_me(self) -> None:
        self.assertEqual(transform_pronoun("me", "third", "male"), "him")

    def test_first_to_third_male_my(self) -> None:
        self.assertEqual(transform_pronoun("my", "third", "male"), "his")

    def test_first_to_third_male_mine(self) -> None:
        self.assertEqual(transform_pronoun("mine", "third", "male"), "his")

    def test_first_to_third_male_myself(self) -> None:
        self.assertEqual(
            transform_pronoun("myself", "third", "male"), "himself"
        )

    # -- First → Third person (female) ----------------------------------

    def test_first_to_third_female_I(self) -> None:
        self.assertEqual(transform_pronoun("I", "third", "female"), "she")

    def test_first_to_third_female_me(self) -> None:
        self.assertEqual(transform_pronoun("me", "third", "female"), "her")

    def test_first_to_third_female_my(self) -> None:
        self.assertEqual(transform_pronoun("my", "third", "female"), "her")

    def test_first_to_third_female_mine(self) -> None:
        self.assertEqual(
            transform_pronoun("mine", "third", "female"), "hers"
        )

    def test_first_to_third_female_myself(self) -> None:
        self.assertEqual(
            transform_pronoun("myself", "third", "female"), "herself"
        )

    # -- First → Third person (neutral / they) --------------------------

    def test_first_to_third_neutral_I(self) -> None:
        self.assertEqual(transform_pronoun("I", "third", "neutral"), "they")

    def test_first_to_third_neutral_me(self) -> None:
        self.assertEqual(transform_pronoun("me", "third", "neutral"), "them")

    def test_first_to_third_neutral_my(self) -> None:
        self.assertEqual(
            transform_pronoun("my", "third", "neutral"), "their"
        )

    def test_first_to_third_neutral_mine(self) -> None:
        self.assertEqual(
            transform_pronoun("mine", "third", "neutral"), "theirs"
        )

    def test_first_to_third_neutral_myself(self) -> None:
        self.assertEqual(
            transform_pronoun("myself", "third", "neutral"), "themselves"
        )

    # -- Case insensitivity ----------------------------------------------

    def test_case_insensitive_I(self) -> None:
        """'I' (uppercase) and 'i' (lowercase) both work."""
        self.assertEqual(transform_pronoun("I", "second"), "you")
        self.assertEqual(transform_pronoun("i", "second"), "you")

    def test_case_insensitive_My(self) -> None:
        self.assertEqual(transform_pronoun("My", "second"), "your")
        self.assertEqual(transform_pronoun("MY", "second"), "your")

    # -- Gender default ---------------------------------------------------

    def test_third_person_default_gender(self) -> None:
        """When gender is not provided, defaults to neutral."""
        self.assertEqual(transform_pronoun("I", "third"), "they")

    # -- Invalid target_person -------------------------------------------

    def test_invalid_target_person_raises(self) -> None:
        with self.assertRaises(ValueError):
            transform_pronoun("I", "first")

    # -- Unknown pronoun fallback ----------------------------------------

    def test_unknown_pronoun_passthrough(self) -> None:
        """Unknown input is lowercased and returned as-is."""
        self.assertEqual(transform_pronoun("foo", "second"), "foo")
        self.assertEqual(transform_pronoun("bar", "third", "male"), "bar")


# -----------------------------------------------------------------------
# Gender Map
# -----------------------------------------------------------------------


class TestGenderMap(TestCase):
    """Tests for ``GENDER_MAP`` constant."""

    def test_male(self) -> None:
        self.assertEqual(GENDER_MAP["male"], "male")

    def test_female(self) -> None:
        self.assertEqual(GENDER_MAP["female"], "female")

    def test_ambiguous(self) -> None:
        self.assertEqual(GENDER_MAP["ambiguous"], "neutral")

    def test_neutral(self) -> None:
        self.assertEqual(GENDER_MAP["neutral"], "neutral")

    def test_nonbinary(self) -> None:
        self.assertEqual(GENDER_MAP["nonbinary"], "neutral")

    def test_other(self) -> None:
        self.assertEqual(GENDER_MAP["other"], "neutral")


# -----------------------------------------------------------------------
# Possessive Forms
# -----------------------------------------------------------------------


class TestPossessive(TestCase):
    """Tests for ``possessive``."""

    # -- Regular names / noun phrases ------------------------------------

    def test_name_jorge(self) -> None:
        self.assertEqual(possessive("Jorge"), "Jorge's")

    def test_sdesc(self) -> None:
        self.assertEqual(possessive("a lanky man"), "a lanky man's")

    def test_name_maria(self) -> None:
        self.assertEqual(possessive("Maria"), "Maria's")

    # -- Pronoun possessives (lookup table) ------------------------------

    def test_pronoun_you(self) -> None:
        self.assertEqual(possessive("you"), "your")

    def test_pronoun_he(self) -> None:
        self.assertEqual(possessive("he"), "his")

    def test_pronoun_she(self) -> None:
        self.assertEqual(possessive("she"), "her")

    def test_pronoun_they(self) -> None:
        self.assertEqual(possessive("they"), "their")

    def test_pronoun_it(self) -> None:
        self.assertEqual(possessive("it"), "its")

    def test_pronoun_i(self) -> None:
        self.assertEqual(possessive("I"), "My")

    def test_pronoun_we(self) -> None:
        self.assertEqual(possessive("we"), "our")

    # -- Capitalisation preservation ------------------------------------

    def test_capitalised_pronoun_You(self) -> None:
        self.assertEqual(possessive("You"), "Your")

    def test_capitalised_pronoun_He(self) -> None:
        self.assertEqual(possessive("He"), "His")

    def test_capitalised_pronoun_She(self) -> None:
        self.assertEqual(possessive("She"), "Her")

    def test_capitalised_pronoun_They(self) -> None:
        self.assertEqual(possessive("They"), "Their")


# -----------------------------------------------------------------------
# Capitalisation
# -----------------------------------------------------------------------


class TestCapitalizeFirst(TestCase):
    """Tests for ``capitalize_first``."""

    def test_lowercase_start(self) -> None:
        self.assertEqual(
            capitalize_first("a lanky man leans back."),
            "A lanky man leans back.",
        )

    def test_already_capitalised(self) -> None:
        self.assertEqual(
            capitalize_first("Jorge leans back."),
            "Jorge leans back.",
        )

    def test_leading_quote(self) -> None:
        """First alpha char is inside quotes — capitalise it."""
        self.assertEqual(
            capitalize_first('"get down!" he shouts.'),
            '"Get down!" he shouts.',
        )

    def test_preserves_subsequent_case(self) -> None:
        """Unlike str.capitalize(), don't lowercase the rest."""
        self.assertEqual(
            capitalize_first("jORGE leans."),
            "JORGE leans.",
        )

    def test_empty_string(self) -> None:
        self.assertEqual(capitalize_first(""), "")

    def test_no_alpha_characters(self) -> None:
        self.assertEqual(capitalize_first("123..."), "123...")

    def test_you_already_capitalised(self) -> None:
        self.assertEqual(
            capitalize_first("You lean back."),
            "You lean back.",
        )

    def test_sdesc_with_article(self) -> None:
        self.assertEqual(
            capitalize_first("a compact woman nods."),
            "A compact woman nods.",
        )
