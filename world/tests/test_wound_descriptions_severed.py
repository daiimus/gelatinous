"""Unit tests for the ``severed`` injury type (PR #198).

Synthesized by :func:`typeclasses.items.apply_sever_to_corpse` after
a successful sever, and rendered through the standard
:func:`world.medical.wounds.get_wound_description` pipeline so the
same templates flow to corpse autopsies and to severed-item
``return_appearance`` output.

Run via::

    evennia test world.tests.test_wound_descriptions_severed
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.wounds import get_wound_description


class SeveredWoundRenderingTests(TestCase):

    def test_limb_severed_old_stage_renders_stump(self):
        out = get_wound_description(
            injury_type="severed",
            location="left_arm",
            severity="Critical",
            stage="old",
        )
        lowered = out.lower()
        self.assertIn("left arm", lowered)
        # Templates evoke stump / severed / missing / ragged-tissue prose.
        self.assertTrue(
            any(
                token in lowered
                for token in ("stump", "severed", "missing", "ragged", "once attached")
            ),
            f"Expected stump/severed prose; got {out!r}",
        )

    def test_head_severed_renders_head_in_prose(self):
        out = get_wound_description(
            injury_type="severed",
            location="head",
            severity="Critical",
            stage="old",
        )
        self.assertIn("head", out.lower())

    def test_fresh_stage_also_renders(self):
        out = get_wound_description(
            injury_type="severed",
            location="right_thigh",
            severity="Critical",
            stage="fresh",
        )
        self.assertIn("right thigh", out.lower())

    def test_unknown_location_falls_back_to_raw_token(self):
        """No crash + raw token survives the format pipeline."""
        out = get_wound_description(
            injury_type="severed",
            location="tail",  # not in default mappings
            severity="Critical",
            stage="old",
        )
        # ``get_location_display_name`` returns the raw key if unmapped.
        self.assertIn("tail", out.lower())
