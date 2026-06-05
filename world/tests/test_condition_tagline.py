"""Tests for the condition-sentence helper shims.

Originally (#221 / #223) ``format_condition_tagline`` produced a
literal sentence ("It is a pristine specimen.") that
``prepend_condition_to_desc`` prepended to harvested-organ and
severed-part prose.  In playtest the sentence read as redundant —
the decay-tier prose itself is already self-describing of
freshness — so both helpers are now no-op shims that always return
empty / desc-unchanged.

These tests guard the shim contract so any caller still consuming
the API doesn't break, and so the redundant-sentence regression
doesn't reappear silently.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    format_condition_tagline,
    prepend_condition_to_desc,
)


class TestFormatConditionTaglineReturnsEmpty(TestCase):
    """Every condition returns the empty string now (no-op shim)."""

    def test_pristine_empty(self):
        self.assertEqual(format_condition_tagline("pristine"), "")

    def test_damaged_empty(self):
        self.assertEqual(format_condition_tagline("damaged"), "")

    def test_putrid_empty(self):
        self.assertEqual(format_condition_tagline("putrid"), "")

    def test_desiccated_empty(self):
        self.assertEqual(format_condition_tagline("desiccated"), "")

    def test_none_empty(self):
        self.assertEqual(format_condition_tagline(None), "")

    def test_unknown_empty(self):
        self.assertEqual(format_condition_tagline("phlegmatic"), "")


class TestPrependConditionToDescReturnsDescUntouched(TestCase):
    """The prepend helper now returns the desc verbatim."""

    def test_returns_desc_for_every_condition(self):
        for condition in ("pristine", "damaged", "putrid",
                          "desiccated", "refuse", None, "", "unknown"):
            with self.subTest(condition=condition):
                self.assertEqual(
                    prepend_condition_to_desc(condition, "A clean cut."),
                    "A clean cut.",
                )

    def test_empty_desc_returns_empty(self):
        for condition in ("pristine", "damaged", None):
            with self.subTest(condition=condition):
                self.assertEqual(
                    prepend_condition_to_desc(condition, ""), "",
                )
                self.assertEqual(
                    prepend_condition_to_desc(condition, None), "",
                )

    def test_does_not_prepend_any_sentence(self):
        # Regression guard: previously prepended "It is a pristine
        # specimen." style sentences.  Make sure no condition variant
        # injects that vocabulary back.
        for condition in ("pristine", "damaged", "putrid", "desiccated"):
            with self.subTest(condition=condition):
                out = prepend_condition_to_desc(condition, "Body part.")
                self.assertNotIn("specimen", out)
                self.assertEqual(out, "Body part.")
