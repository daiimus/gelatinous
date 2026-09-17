"""A trenchcoat lands on the outerwear rung, not the base layer (#3425).

``derive_rung`` matches whole words with a boundary at both ends, which
#2478 and #2657 bought so that "bra" stops claiming brass knuckles and
"zebra" is not a bra. Closed compounds therefore cannot be found by their
head word: "trenchcoat" contains "coat" and "trench" but names neither
as a whole token. The matcher stays strict; the compounds go in the
table. This pins the two the layer spec's own worked example is about,
and keeps the controls that justify the strictness.
"""

from unittest import TestCase

from world.style import DEFAULT_RUNG, derive_rung


class TestClosedCompoundsAreInTheTable(TestCase):
    def test_a_trenchcoat_is_outerwear(self):
        self.assertEqual(derive_rung("trenchcoat"), 4)
        self.assertEqual(derive_rung("Black Trenchcoat"), 4)
        self.assertEqual(derive_rung("black trenchcoats"), 4)

    def test_a_longcoat_is_outerwear(self):
        self.assertEqual(derive_rung("longcoat"), 4)
        self.assertEqual(derive_rung("oilskin longcoat"), 4)

    def test_the_open_forms_still_work(self):
        self.assertEqual(derive_rung("long coat"), 4)
        self.assertEqual(derive_rung("trench coat"), 4)
        self.assertEqual(derive_rung("overcoat"), 4)

    def test_the_most_specific_word_wins(self):
        # "trenchcoat" (10) beats "coat" (4): the spec's example, now expressible
        self.assertEqual(derive_rung("trenchcoat"), 4)

    def test_the_boundary_is_not_loosened(self):
        # the controls #2478 / #2657 were about: no prefix or suffix claims
        self.assertIsNone(derive_rung("zebra"))
        self.assertIsNone(derive_rung("brass knuckles"))
        self.assertIsNone(derive_rung("nothing here"))
        self.assertEqual(DEFAULT_RUNG, 1)
