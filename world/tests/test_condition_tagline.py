"""Tests for the condition-sentence helper (issue #221 / #223).

Covers :mod:`world.anatomy.conditions` — the small helper module that
formats the plain freshness sentence prepended to a harvested organ
or severed appendage's ``look`` output.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    format_condition_tagline,
    prepend_condition_to_desc,
)


class TestFormatConditionTagline(TestCase):
    """Sentence rendering for each recognised condition."""

    def test_pristine_sentence(self):
        self.assertEqual(
            format_condition_tagline("pristine"),
            "It is a pristine specimen.",
        )

    def test_damaged_sentence(self):
        self.assertEqual(
            format_condition_tagline("damaged"),
            "It is a damaged specimen.",
        )

    def test_putrid_sentence(self):
        self.assertEqual(
            format_condition_tagline("putrid"),
            "It is a putrid specimen.",
        )

    def test_desiccated_sentence(self):
        self.assertEqual(
            format_condition_tagline("desiccated"),
            "It is a desiccated specimen.",
        )

    def test_refuse_renders_empty(self):
        # ``refuse`` is the gameplay-internal skeletal-stage harvest
        # condition; leaking the term in look output would be a UX bug.
        self.assertEqual(format_condition_tagline("refuse"), "")

    def test_none_renders_empty(self):
        self.assertEqual(format_condition_tagline(None), "")

    def test_empty_string_renders_empty(self):
        self.assertEqual(format_condition_tagline(""), "")

    def test_unknown_condition_renders_empty(self):
        self.assertEqual(format_condition_tagline("phlegmatic"), "")

    def test_no_ansi_colour_codes(self):
        # Issue #223 regression guard: the original #221 cut wrapped
        # the tagline in |g / |y / |r / |R colour codes which read as
        # a separate UI block.  The plain-sentence form must stay
        # free of ANSI escapes so it blends into the description.
        for condition in ("pristine", "damaged", "putrid", "desiccated"):
            with self.subTest(condition=condition):
                self.assertNotIn("|", format_condition_tagline(condition))


class TestPrependConditionToDesc(TestCase):
    """Composition rules for ``{sentence}\\n{desc}`` (no blank-line gap)."""

    def test_sentence_and_desc_compose_with_single_newline(self):
        result = prepend_condition_to_desc(
            "pristine", "A fresh human heart, glistening."
        )
        self.assertEqual(
            result,
            "It is a pristine specimen.\nA fresh human heart, glistening.",
        )

    def test_no_blank_line_between_sentence_and_prose(self):
        # Issue #223 regression guard: the original #221 cut used
        # ``\n\n`` which rendered as a visual paragraph break.
        result = prepend_condition_to_desc("damaged", "Some prose.")
        self.assertNotIn("\n\n", result)

    def test_sentence_only_when_desc_empty(self):
        self.assertEqual(
            prepend_condition_to_desc("damaged", ""),
            "It is a damaged specimen.",
        )

    def test_sentence_only_when_desc_none(self):
        self.assertEqual(
            prepend_condition_to_desc("damaged", None),
            "It is a damaged specimen.",
        )

    def test_desc_only_when_condition_has_no_sentence(self):
        # ``refuse`` / unknown conditions yield no sentence — caller's
        # prose passes through unchanged.
        self.assertEqual(
            prepend_condition_to_desc("refuse", "A withered remnant."),
            "A withered remnant.",
        )

    def test_empty_when_both_inputs_empty(self):
        self.assertEqual(prepend_condition_to_desc("refuse", ""), "")
        self.assertEqual(prepend_condition_to_desc(None, None), "")
        self.assertEqual(prepend_condition_to_desc("", ""), "")

    def test_all_four_conditions_round_trip(self):
        # Exhaustive contract: every recognised condition produces a
        # non-empty composed result when paired with prose, with the
        # sentence leading and the prose following on the next line.
        for condition in ("pristine", "damaged", "putrid", "desiccated"):
            with self.subTest(condition=condition):
                result = prepend_condition_to_desc(condition, "Body part.")
                self.assertIn("Body part.", result)
                self.assertTrue(result.startswith("It is a "))
                self.assertIn(" specimen.\n", result)
