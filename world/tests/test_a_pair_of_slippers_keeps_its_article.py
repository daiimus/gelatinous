"""`with_article` and `is_pluralia_tantum` on the shapes that broke them
(#2643, #2648).

Four defects in one function pair:

* **Partitive.** `is_pluralia_tantum` had no partitive break, so a key
  beginning "pair of" was judged on the noun AFTER "of" and the article
  suppressed. Live on one object — the clinic's `pair of
  Thawn-Harrison slippers`, which announced itself, was picked up and
  was worn with no article at all.
* **Markup.** It was the one decision in the module reading the RAW
  string rather than going through `_visible()`, and `with_article`
  hands it the raw key. So the same item answered differently coloured
  and uncoloured, which made the partitive defect look intermittent.
* **Tuple order.** The docstring promises the FIRST prepositional
  break; the loop tested `" in "` first wherever it sat, so a trailing
  prepositional phrase cut the phrase at the wrong point and deleted
  the article from the wearer.
* **Empty string.** `inflect` raises `TypeCheckError` on `""`, which
  `pluralize_noun` guards and the other two entry points did not.

The suppression itself is right and must stay: a bare pluralia tantum
takes no indefinite article, which is what the function was written for
and what it gets correct on 516 live garment objects.
"""
from evennia.utils.test_resources import EvenniaTest

from world.grammar import (
    conjugate_third_person, is_pluralia_tantum, with_article,
)


class TestTheSuppressionStillWorks(EvenniaTest):
    """Control. Every assertion below is about NOT suppressing the
    article; if suppression were simply broken they would all pass and
    mean nothing."""

    def test_a_bare_pluralia_tantum_takes_no_article(self):
        self.assertEqual(with_article("blue jeans"), "blue jeans")
        self.assertEqual(with_article("scissors"), "scissors")

    def test_an_ordinary_noun_takes_one(self):
        self.assertEqual(with_article("knife"), "a knife")
        self.assertEqual(with_article("axe"), "an axe")

    def test_a_wearer_is_judged_on_the_wearer(self):
        self.assertEqual(with_article("stocky droog in blue jeans"),
                         "a stocky droog in blue jeans")


class TestThePartitiveIsSingular(EvenniaTest):

    def test_a_pair_is_a_pair(self):
        self.assertFalse(is_pluralia_tantum("pair of slippers"))
        self.assertEqual(with_article("pair of slippers"),
                         "a pair of slippers")

    def test_the_live_item(self):
        self.assertEqual(
            with_article("pair of Thawn-Harrison slippers"),
            "a pair of Thawn-Harrison slippers")

    def test_and_the_other_partitives(self):
        self.assertEqual(with_article("pair of boots"), "a pair of boots")
        self.assertEqual(with_article("pair of scissors"),
                         "a pair of scissors")
        self.assertEqual(with_article("pack of cigarettes"),
                         "a pack of cigarettes")


class TestMarkupDoesNotChangeTheAnswer(EvenniaTest):

    def test_colour_does_not_flip_the_number(self):
        for phrase in ("pair of slippers", "blue jeans", "knife"):
            plain = with_article(phrase)
            coloured = with_article(f"|w{phrase}|n")
            self.assertEqual(
                coloured, plain.replace(phrase, f"|w{phrase}|n"),
                f"{phrase!r} answers differently once it is coloured")

    def test_hex_markup_too(self):
        """The hex branch of `_ANSI_TOKEN` shipped under #2805; this
        pins that `is_pluralia_tantum` benefits from it."""
        self.assertFalse(is_pluralia_tantum("|#FF0000pair of slippers|n"))
        self.assertTrue(is_pluralia_tantum("|#FF0000blue jeans|n"))


class TestTheBreakIsPositional(EvenniaTest):

    def test_a_trailing_phrase_does_not_delete_the_article(self):
        self.assertEqual(
            with_article("stocky droog wearing jeans in the alley"),
            "a stocky droog wearing jeans in the alley",
            "the phrase was cut at the tuple's first entry, not the "
            "string's first break")

    def test_the_plausible_content_case(self):
        """`_PLURALIA_TANTUM_NOUNS` holds several wieldable items."""
        self.assertEqual(
            with_article(
                "lanky man wielding knuckles in an armored jacket"),
            "a lanky man wielding knuckles in an armored jacket")

    def test_a_single_break_still_works(self):
        """Control: the shape that always worked."""
        self.assertEqual(with_article("stocky droog wearing jeans"),
                         "a stocky droog wearing jeans")


class TestTheEmptyStringDoesNotRaise(EvenniaTest):
    """These two report as ERRORS against the unfixed tree rather than
    failures, because the unfixed code raises `TypeCheckError` out of
    `inflect` — the raise IS the defect, so the error is the finding
    and not a broken instrument."""


    def test_with_article(self):
        self.assertEqual(with_article(""), "")

    def test_conjugate_third_person(self):
        self.assertEqual(conjugate_third_person(""), "")
