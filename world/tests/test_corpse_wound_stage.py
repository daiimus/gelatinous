"""Test corpse wound-stage preservation (issue #335).

Pre-fix, ``Corpse.get_preserved_wound_descriptions`` hardcoded
``stage='old'`` when calling ``get_wound_description``. ``'old'`` doesn't
exist in any wound-message dict, so the renderer fell back to ``'fresh'``
templates for every corpse wound — making severed limbs read as active
injuries instead of stumps.

These tests pin the fix: the renderer must consult ``wound_data['stage']``
so the round trip from ``organ.wound_stage`` → death snapshot → corpse
render preserves the actual state.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest import TestCase

from typeclasses.corpse import Corpse


class _CorpseStub:
    """Minimal stub that re-uses Corpse's bound methods."""

    get_preserved_wound_descriptions = Corpse.get_preserved_wound_descriptions

    def __init__(self, wounds):
        self.db = SimpleNamespace(
            wounds_at_death=wounds,
            skintone=None,
            species="human",
        )


class CorpseWoundStageTests(TestCase):

    def test_severed_stage_renders_severed_prose(self):
        """A preserved severed wound must render the severed-stage
        template, not fall back to fresh."""
        wounds = [
            {
                "injury_type": "laceration",
                "location": "left_hand",
                "severity": "Critical",
                "stage": "severed",
                "organ": "left_metacarpals",
            },
        ]
        corpse = _CorpseStub(wounds)
        descriptions = corpse.get_preserved_wound_descriptions()
        self.assertEqual(len(descriptions), 1)
        text = descriptions[0]
        # The severed-stage templates describe stumps and joint
        # severance. Fresh-stage templates describe active injuries.
        # Markers updated for #337's combat-flavored prose rewrite —
        # the new templates use visceral vocabulary (stump, joint,
        # shredded, severance) rather than the old clinical wording
        # (amputation, surgically removed).
        severed_markers = (
            "stump", "bone", "joint", "tear", "severance", "shredded",
            "amputation", "severed", "amputated",
        )
        fresh_markers = (
            "showing damage", "traumatic wound", "requiring attention",
            "with visible harm",
        )
        self.assertTrue(
            any(marker in text.lower() for marker in severed_markers),
            f"Severed wound rendered without severed markers: {text!r}",
        )
        self.assertFalse(
            any(marker in text.lower() for marker in fresh_markers),
            f"Severed wound rendered with fresh-stage markers: {text!r}",
        )

    def test_destroyed_stage_renders_destroyed_prose(self):
        """A preserved destroyed wound must render the destroyed-stage
        template (organ pulped in place, not severed)."""
        wounds = [
            {
                "injury_type": "blunt",
                "location": "chest",
                "severity": "Critical",
                "stage": "destroyed",
                "organ": "heart",
            },
        ]
        corpse = _CorpseStub(wounds)
        descriptions = corpse.get_preserved_wound_descriptions()
        self.assertEqual(len(descriptions), 1)
        text = descriptions[0]
        # Destroyed-stage prose talks about catastrophic / mangled /
        # pulped / obliterated outcomes; fresh-stage prose talks about
        # active bleeding wounds.
        destroyed_markers = (
            "catastrophic", "mangled", "devastating", "obliterat",
            "pulp", "ruined mess", "shattered", "wreckage",
            "bludgeoning", "crush", "brutal",
        )
        self.assertTrue(
            any(marker in text.lower() for marker in destroyed_markers),
            f"Destroyed wound rendered without destroyed markers: {text!r}",
        )

    def test_unset_stage_falls_back_to_fresh(self):
        """A preserved wound with no recorded stage falls back to fresh
        prose, preserving backwards compatibility with pre-#335 corpses
        in the live DB whose snapshots may lack the ``stage`` field."""
        wounds = [
            {
                "injury_type": "generic",
                "location": "chest",
                "severity": "Moderate",
                # No 'stage' key.
                "organ": None,
            },
        ]
        corpse = _CorpseStub(wounds)
        descriptions = corpse.get_preserved_wound_descriptions()
        self.assertEqual(len(descriptions), 1)
        # Should produce *something* — the fallback should not crash.
        self.assertTrue(len(descriptions[0]) > 0)

    def test_no_wounds_returns_empty_list(self):
        corpse = _CorpseStub([])
        self.assertEqual(corpse.get_preserved_wound_descriptions(), [])

    def test_location_filter_respected(self):
        wounds = [
            {
                "injury_type": "laceration",
                "location": "left_hand",
                "severity": "Critical",
                "stage": "severed",
                "organ": "left_metacarpals",
            },
            {
                "injury_type": "blunt",
                "location": "chest",
                "severity": "Critical",
                "stage": "destroyed",
                "organ": "heart",
            },
        ]
        corpse = _CorpseStub(wounds)
        only_hand = corpse.get_preserved_wound_descriptions(
            location="left_hand"
        )
        self.assertEqual(len(only_hand), 1)
        # The chest wound must not appear in a left_hand-filtered query.
        self.assertNotIn("chest", only_hand[0].lower())
