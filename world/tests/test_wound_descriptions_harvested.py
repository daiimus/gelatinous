"""Unit tests for the ``harvested`` injury type (PR #200 / PR-F).

Synthesized by :class:`commands.forensics.CmdHarvest` after a
successful organ extraction and rendered through the standard
:func:`world.medical.wounds.get_wound_description` pipeline so the
same templates flow to corpse autopsies and (via PR-D's overlay) to
severed-item ``return_appearance`` output when the harvested organ's
container is subsequently severed.

Run via::

    evennia test world.tests.test_wound_descriptions_harvested
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.wounds import get_wound_description


class HarvestedWoundRenderingTests(TestCase):

    def test_eye_harvest_old_stage_renders_extraction_prose(self):
        out = get_wound_description(
            injury_type="harvested",
            location="head",
            severity="Critical",
            stage="old",
            organ="left_eye",
        )
        lowered = out.lower()
        # Templates evoke surgical / excision / extraction prose at the
        # head location with the organ token present.
        self.assertIn("head", lowered)
        self.assertIn("left eye", lowered)
        self.assertTrue(
            any(
                token in lowered
                for token in (
                    "incision", "extracted", "excised", "removed",
                    "extraction", "lifted", "puckered",
                )
            ),
            f"Expected extraction prose; got {out!r}",
        )

    def test_heart_harvest_chest_location(self):
        out = get_wound_description(
            injury_type="harvested",
            location="chest",
            severity="Critical",
            stage="old",
            organ="heart",
        )
        lowered = out.lower()
        self.assertIn("chest", lowered)
        self.assertIn("heart", lowered)

    def test_fresh_stage_renders(self):
        out = get_wound_description(
            injury_type="harvested",
            location="abdomen",
            severity="Critical",
            stage="fresh",
            organ="liver",
        )
        lowered = out.lower()
        self.assertIn("abdomen", lowered)
        self.assertIn("liver", lowered)

    def test_organ_token_humanized(self):
        """Underscored organ keys (left_eye) render as 'left eye'."""
        out = get_wound_description(
            injury_type="harvested",
            location="head",
            severity="Critical",
            stage="old",
            organ="right_eye",
        )
        # Should NOT contain the raw underscored token.
        self.assertNotIn("right_eye", out)
        # Should contain the humanized form.
        self.assertIn("right eye", out.lower())

    def test_unknown_location_falls_back_to_raw_token(self):
        """No crash + raw token survives the format pipeline."""
        out = get_wound_description(
            injury_type="harvested",
            location="gizzard",  # not in default mappings
            severity="Critical",
            stage="old",
            organ="bezoar",
        )
        self.assertIn("gizzard", out.lower())
        self.assertIn("bezoar", out.lower())
