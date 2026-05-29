"""Tests for the condition-tagline helper (issue #221).

Covers :mod:`world.anatomy.conditions` — the small helper module that
formats the colour-coded freshness tagline shown atop a harvested
organ or severed appendage's ``look`` output.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    format_condition_tagline,
    prepend_condition_to_desc,
)


class TestFormatConditionTagline(TestCase):
    """Tagline rendering for each recognised condition."""

    def test_pristine_renders_green(self):
        self.assertEqual(format_condition_tagline("pristine"), "|gPristine.|n")

    def test_damaged_renders_yellow(self):
        self.assertEqual(format_condition_tagline("damaged"), "|yDamaged.|n")

    def test_putrid_renders_red(self):
        self.assertEqual(format_condition_tagline("putrid"), "|rPutrid.|n")

    def test_desiccated_renders_bright_red(self):
        self.assertEqual(
            format_condition_tagline("desiccated"), "|RDesiccated.|n"
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


class TestPrependConditionToDesc(TestCase):
    """Composition rules for ``{tagline}\\n\\n{desc}``."""

    def test_tagline_and_desc_compose_with_blank_line(self):
        result = prepend_condition_to_desc(
            "pristine", "A fresh human heart, glistening."
        )
        self.assertEqual(
            result, "|gPristine.|n\n\nA fresh human heart, glistening."
        )

    def test_tagline_only_when_desc_empty(self):
        self.assertEqual(
            prepend_condition_to_desc("damaged", ""), "|yDamaged.|n"
        )

    def test_tagline_only_when_desc_none(self):
        self.assertEqual(
            prepend_condition_to_desc("damaged", None), "|yDamaged.|n"
        )

    def test_desc_only_when_condition_has_no_tagline(self):
        # ``refuse`` / unknown conditions yield no tagline — caller's
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
        # non-empty composed result when paired with prose.
        for condition in ("pristine", "damaged", "putrid", "desiccated"):
            with self.subTest(condition=condition):
                result = prepend_condition_to_desc(condition, "Body part.")
                self.assertIn("Body part.", result)
                self.assertTrue(result.startswith("|"))
                self.assertIn("\n\n", result)
