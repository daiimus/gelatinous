"""Unit tests for the ``harvested`` injury type (PR #200 / PR-F).

Synthesized by :func:`world.medical.procedures._mark_organ_removed`
after a successful ``harvest`` procedure verb (PR #380 / #307) and
rendered through the standard
:func:`world.medical.wounds.get_wound_description` pipeline so the
same templates flow to corpse autopsies and (via PR-D's overlay) to
severed-item ``return_appearance`` output when the harvested organ's
container is subsequently severed.

Run via::

    evennia test world.tests.test_wound_descriptions_harvested
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.medical.wounds import get_wound_description
from world.medical.wounds.messages.harvested import WOUND_DESCRIPTIONS

# Vocabulary every harvested-stage template must contain to read as
# extraction prose.  The contract is enforced exhaustively (every
# template, not random-sample) — see ``test_every_template_uses_extraction_vocab``.
EXTRACTION_KEYWORDS = (
    "incision", "extracted", "excised", "removed",
    "extraction", "lifted", "puckered",
)


class HarvestedWoundRenderingTests(TestCase):

    def test_every_template_uses_extraction_vocab(self):
        """Issue #219: every harvested template must read as extraction prose.

        Earlier coverage random-sampled ``get_wound_description`` and
        asserted vocabulary on the sampled output, which flaked when
        the renderer picked the one template lacking an extraction
        keyword (~25% rate).  This assertion enforces the contract
        exhaustively across every template and stage so future template
        additions can't reintroduce the regression.
        """
        for stage, templates in WOUND_DESCRIPTIONS.items():
            for idx, template in enumerate(templates):
                lowered = template.lower()
                self.assertTrue(
                    any(kw in lowered for kw in EXTRACTION_KEYWORDS),
                    f"Stage {stage!r} template #{idx} lacks extraction "
                    f"vocabulary: {template!r}",
                )

    def test_eye_harvest_old_stage_renders_extraction_prose(self):
        """Deterministic regression guard against the original flake.

        Patches ``random.choice`` to walk every old-stage template in
        order rather than sampling, so a single broken template
        introduced by a future PR will fail this test reliably rather
        than 1-in-N times.
        """
        old_templates = WOUND_DESCRIPTIONS["old"]
        for template in old_templates:
            with patch(
                "world.medical.wounds.wound_descriptions.random.choice",
                return_value=template,
            ):
                out = get_wound_description(
                    injury_type="harvested",
                    location="head",
                    severity="Critical",
                    stage="old",
                    organ="left_eye",
                )
            lowered = out.lower()
            self.assertIn("head", lowered)
            self.assertIn("left eye", lowered)
            self.assertTrue(
                any(kw in lowered for kw in EXTRACTION_KEYWORDS),
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
