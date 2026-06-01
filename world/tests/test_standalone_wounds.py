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

from world.medical.wounds import messages
from world.medical.wounds.constants import MEDICAL_COLORS
from world.medical.wounds.longdesc_hooks import (
    _summarize_location_wounds,
    _compound_phrase,
    _resolve_compound_template,
    get_standalone_wound_description,
    append_wounds_to_longdesc,
)

HOOKS = "world.medical.wounds.longdesc_hooks.get_character_wounds"

# Injury-type modules that ship their own compound template sets.
COMPOUND_MODULES = ("bullet", "cut", "stab", "blunt", "generic")
# Stage keys every compound module must define.
REQUIRED_STAGES = ("fresh", "treated", "healing", "destroyed", "scarred")


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
        # Concise: a single compound clause names the remainder exactly once,
        # rather than concatenating one description per wound.
        self.assertEqual(lowered.count("another wound"), 1)
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

    def test_healed_mix_renders_without_fresh_red(self):
        # A scarred worst wound resolves a calm, skintone-keyed compound
        # template — never the bright-red fresh-wound coloring.
        worst = _wound(severity="Moderate", stage="scarred")
        raw = _compound_phrase(worst, others_count=2)
        self.assertIn("left arm", raw.lower())
        self.assertNotIn("|R", raw)
        self.assertNotIn("|r", raw)
        # Still a single concise clause naming the remainder once.
        self.assertEqual(raw.lower().count("several other wounds"), 1)

    def test_generic_type_omits_redundant_type_word(self):
        worst = _wound(injury_type="generic", severity="Critical", stage="fresh")
        out = _compound_phrase(worst, others_count=1).lower()
        self.assertIn("grievous wound", out)
        self.assertNotIn("generic", out)

    def test_typed_wound_lead_severity_and_location(self):
        worst = _wound(injury_type="stab", severity="Severe", stage="fresh")
        out = _compound_phrase(worst, others_count=1).lower()
        # Severe -> "serious"; the location is always named.
        self.assertIn("serious", out)
        self.assertIn("left arm", out)
        self.assertIn("another wound", out)

    def test_inline_fallback_when_no_template_resolves(self):
        # With no compound template set available anywhere, the summarizer
        # still returns a terminated sentence via legacy inline prose.
        worst = _wound(injury_type="cut", severity="Critical", stage="fresh")
        with mock.patch(
            "world.medical.wounds.longdesc_hooks._resolve_compound_template",
            return_value=None,
        ):
            out = _compound_phrase(worst, others_count=1)
        self.assertIn("left arm", out.lower())
        self.assertTrue(out.rstrip().endswith(("|n", ".")))


class ResolveCompoundTemplateTests(TestCase):

    def test_typed_lookup_uses_own_module(self):
        for _ in range(20):
            tmpl = _resolve_compound_template("bullet", "fresh")
            self.assertIn(tmpl, messages.bullet.COMPOUND_DESCRIPTIONS["fresh"])

    def test_unknown_type_falls_back_to_generic(self):
        # ``severed`` is a real injury type with no compound dict of its own.
        for _ in range(20):
            tmpl = _resolve_compound_template("severed", "fresh")
            self.assertIn(tmpl, messages.generic.COMPOUND_DESCRIPTIONS["fresh"])

    def test_unknown_stage_defaults_to_fresh(self):
        for _ in range(20):
            tmpl = _resolve_compound_template("cut", "nonexistent_stage")
            self.assertIn(tmpl, messages.cut.COMPOUND_DESCRIPTIONS["fresh"])

    def test_all_modules_define_required_stages(self):
        for name in COMPOUND_MODULES:
            module = getattr(messages, name)
            compound = module.COMPOUND_DESCRIPTIONS
            for stage in REQUIRED_STAGES:
                self.assertIn(
                    stage, compound,
                    f"{name}.COMPOUND_DESCRIPTIONS missing stage '{stage}'",
                )
                self.assertTrue(
                    compound[stage],
                    f"{name}.COMPOUND_DESCRIPTIONS['{stage}'] is empty",
                )

    def test_every_template_formats_without_keyerror(self):
        format_vars = {
            "severity": "grievous",
            "location": "left arm",
            "others_phrase": "another wound",
            "skintone": "",
            **MEDICAL_COLORS,
        }
        for name in COMPOUND_MODULES:
            compound = getattr(messages, name).COMPOUND_DESCRIPTIONS
            for stage, variants in compound.items():
                for template in variants:
                    try:
                        template.format(**format_vars)
                    except KeyError as exc:  # pragma: no cover - failure path
                        self.fail(
                            f"{name}.{stage} template references unknown "
                            f"variable {exc}: {template!r}"
                        )


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
