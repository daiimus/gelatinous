"""Unit tests for standalone / compound wound longdesc rendering (#258).

Covers the shared summarizer that collapses multiple wounds at one body
location into a single concise line, and the two render paths that consume
it: :func:`get_standalone_wound_description` (locations with no longdesc) and
:func:`append_wounds_to_longdesc` (locations that already have one).

Run via::

    evennia test world.tests.test_standalone_wounds
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

from world.medical.wounds.longdesc_hooks import (
    _summarize_location_wounds,
    _compound_phrase,
    get_standalone_wound_description,
    append_wounds_to_longdesc,
)

HOOKS = "world.medical.wounds.longdesc_hooks.get_character_wounds"


def _fake_character(species="human", skintone=None):
    """Minimal stand-in exposing the ``db`` attributes the renderers read."""
    return SimpleNamespace(db=SimpleNamespace(species=species, skintone=skintone))


def _wound(injury_type="cut", location="left_arm", severity="Moderate",
           stage="fresh", organ=None):
    return {
        "injury_type": injury_type,
        "location": location,
        "severity": severity,
        "stage": stage,
        "organ": organ,
    }


class SummarizeLocationWoundsTests(TestCase):

    def test_no_wounds_returns_empty(self):
        self.assertEqual(_summarize_location_wounds([]), "")

    def test_single_wound_renders_full_description(self):
        out = _summarize_location_wounds([_wound(stage="fresh")])
        lowered = out.lower()
        self.assertIn("left arm", lowered)
        # A single wound is not summarized as a compound count.
        self.assertNotIn("another wound", lowered)
        self.assertNotIn("several other wounds", lowered)

    def test_two_wounds_collapse_to_single_compound_line(self):
        wounds = [
            _wound(severity="Critical", stage="fresh"),
            _wound(severity="Light", stage="fresh"),
        ]
        out = _summarize_location_wounds(wounds)
        lowered = out.lower()
        self.assertIn("another wound", lowered)
        self.assertIn("left arm", lowered)
        # Worst wound (Critical) drives the lead severity word.
        self.assertIn("grievous", lowered)
        # Concise: one summary clause, not two concatenated descriptions.
        self.assertEqual(lowered.count("mark the"), 1)
        self.assertLessEqual(out.count("|R"), 1)

    def test_three_plus_wounds_use_several_other(self):
        wounds = [
            _wound(severity="Severe", stage="fresh"),
            _wound(severity="Light", stage="fresh"),
            _wound(severity="Moderate", stage="fresh"),
        ]
        out = _summarize_location_wounds(wounds).lower()
        self.assertIn("several other wounds", out)
        self.assertNotIn("another wound", out)
        self.assertIn("serious", out)  # Severe -> "serious"

    def test_compound_is_single_terminated_sentence(self):
        wounds = [_wound(severity="Critical"), _wound(severity="Moderate")]
        out = _summarize_location_wounds(wounds)
        self.assertTrue(out.rstrip().endswith((".", ".|n")))


class CompoundPhraseTests(TestCase):

    def test_healed_mix_renders_calm_old_wounds(self):
        worst = _wound(severity="Moderate", stage="scarred")
        out = _compound_phrase(worst, others_count=2).lower()
        self.assertIn("multiple old wounds", out)
        self.assertIn("left arm", out)
        # Healed summaries are not flagged with fresh-wound red.
        self.assertNotIn("|r", _compound_phrase(worst, 2))

    def test_generic_type_omits_redundant_type_word(self):
        worst = _wound(injury_type="generic", severity="Critical", stage="fresh")
        out = _compound_phrase(worst, others_count=1).lower()
        self.assertIn("grievous wound", out)
        self.assertNotIn("generic", out)

    def test_typed_wound_includes_type_word(self):
        worst = _wound(injury_type="stab", severity="Severe", stage="fresh")
        out = _compound_phrase(worst, others_count=1).lower()
        self.assertIn("stab wound", out)


class StandaloneWoundDescriptionTests(TestCase):

    def test_no_wounds_returns_empty(self):
        with mock.patch(HOOKS, return_value=[]):
            self.assertEqual(
                get_standalone_wound_description(_fake_character(), "left_arm"), ""
            )

    def test_wounds_at_other_location_ignored(self):
        with mock.patch(HOOKS, return_value=[_wound(location="head")]):
            self.assertEqual(
                get_standalone_wound_description(_fake_character(), "left_arm"), ""
            )

    def test_single_wound_returns_summary(self):
        with mock.patch(HOOKS, return_value=[_wound()]):
            out = get_standalone_wound_description(_fake_character(), "left_arm")
        self.assertIn("left arm", out.lower())

    def test_multiple_wounds_return_compound_summary(self):
        wounds = [_wound(severity="Critical"), _wound(severity="Light")]
        with mock.patch(HOOKS, return_value=wounds):
            out = get_standalone_wound_description(_fake_character(), "left_arm")
        self.assertIn("another wound", out.lower())


class AppendWoundsToLongdescTests(TestCase):

    def test_no_wounds_returns_original_unchanged(self):
        original = "A broad, muscular chest"
        with mock.patch(HOOKS, return_value=[]):
            out = append_wounds_to_longdesc(original, _fake_character(), "chest")
        self.assertEqual(out, original)

    def test_appends_compound_clause_with_clean_termination(self):
        original = "A broad, muscular chest"
        wounds = [
            _wound(location="chest", severity="Critical"),
            _wound(location="chest", severity="Light"),
        ]
        with mock.patch(HOOKS, return_value=wounds):
            out = append_wounds_to_longdesc(original, _fake_character(), "chest")
        self.assertTrue(out.startswith(original))
        self.assertIn("another wound", out.lower())
        # Terminated exactly once, color reset preserved at the end.
        self.assertTrue(out.endswith(".|n"))
        self.assertFalse(out.endswith("..|n"))
