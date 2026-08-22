"""Conjugating a conjugated verb (#2164).

``conjugate_third_person`` documented base-form input and applied its
sibilant rule to anything unrecognised, so any already-conjugated form
grew a second ending: "stands" became "standses", "is" became "ises",
"has" became "hases", "tries" became "trieses".

The base-form contract is fine on paper, but the emote renderer feeds
this function verbs typed by players, and `.stands back` is an
ordinary thing to type.

Two irregular tables also existed independently — one keyed by base
form, one by any form — agreeing on be/have/do by hand. One is now
derived from the other so they cannot drift.
"""
from unittest import TestCase

from world.grammar import (
    IRREGULAR_VERBS,
    _IRREGULAR_VERB_FORMS,
    conjugate_third_person,
    flex_verb,
)
from world.emote import render_for_observer, tokenize_dot_pose
from world.tests.test_emote import _make_character


class TestConjugationIsIdempotent(TestCase):
    def test_regular_verbs_do_not_double(self):
        for already in ("stands", "leans", "walks", "tries", "goes",
                        "passes", "catches", "crosses"):
            self.assertEqual(conjugate_third_person(already), already)

    def test_irregular_forms_do_not_double(self):
        self.assertEqual(conjugate_third_person("is"), "is")
        self.assertEqual(conjugate_third_person("has"), "has")
        self.assertEqual(conjugate_third_person("does"), "does")

    def test_base_forms_still_conjugate(self):
        self.assertEqual(conjugate_third_person("lean"), "leans")
        self.assertEqual(conjugate_third_person("pass"), "passes")
        self.assertEqual(conjugate_third_person("catch"), "catches")
        self.assertEqual(conjugate_third_person("try"), "tries")
        self.assertEqual(conjugate_third_person("go"), "goes")
        self.assertEqual(conjugate_third_person("be"), "is")
        self.assertEqual(conjugate_third_person("have"), "has")
        self.assertEqual(conjugate_third_person("do"), "does")

    def test_past_tense_of_be_picks_the_right_person(self):
        self.assertEqual(conjugate_third_person("were"), "was")
        self.assertEqual(conjugate_third_person("was"), "was")

    def test_case_survives_normalisation(self):
        self.assertEqual(conjugate_third_person("Stands"), "Stands")
        self.assertEqual(conjugate_third_person("Lean"), "Leans")

    def test_conjugating_twice_changes_nothing(self):
        for verb in ("lean", "pass", "try", "go", "have", "be", "stand"):
            once = conjugate_third_person(verb)
            self.assertEqual(conjugate_third_person(once), once)


class TestOneTableNotTwo(TestCase):
    def test_the_views_cannot_disagree(self):
        for form, (singular, _plural) in _IRREGULAR_VERB_FORMS.items():
            self.assertEqual(IRREGULAR_VERBS[form], singular)

    def test_the_documented_rows_survive(self):
        """GRAMMAR_ENGINE_SPEC lists these two by name."""
        self.assertEqual(IRREGULAR_VERBS["be"], "is")
        self.assertEqual(IRREGULAR_VERBS["have"], "has")

    def test_flex_verb_agrees_with_the_conjugator(self):
        for form in _IRREGULAR_VERB_FORMS:
            self.assertEqual(flex_verb(form, "singular"),
                             conjugate_third_person(form))


class TestAtTheSurfacePlayersTouch(TestCase):
    def test_a_player_typing_a_conjugated_verb_reads_correctly(self):
        actor = _make_character(key="Jorge Jackson", sex="male")
        observer = _make_character(key="Someone Else", sex="female",
                                   sleeve_uid="uid-observer")
        out = render_for_observer(
            tokenize_dot_pose("stands back.", actor), actor, observer)
        self.assertNotIn("standses", out)
        self.assertIn("stands back", out)
