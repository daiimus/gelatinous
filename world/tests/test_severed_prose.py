"""Regression guard for severed-stage wound prose tone (issue #337).

Pre-#337 every injury-type wound file had clinical / medical severed-stage
prose ("clean surgical amputation", "sterile bandaging", "clinical
precision") — appropriate for ``CmdSever`` post-death scalpel work, but
jarringly wrong for combat-driven severance via chainsaw, sword, or axe.

These tests pin the rewrite: no injury-type ``severed``-stage template
contains the clinical vocabulary that was the symptom. Also verifies the
new ``laceration.py`` exists with full stage coverage so chainsaw /
blowtorch wounds get tearing-flavor prose instead of falling back to
``generic.py``.

The ``severed.py`` file (used by ``injury_type='severed'`` for
``CmdSever``) is intentionally NOT covered by these guards — its
clinical / stump-prose mix is appropriate for the post-death scalpel
flow it represents.
"""

from __future__ import annotations

import importlib
from unittest import TestCase


class SeveredStageProseTests(TestCase):
    """Severed-stage templates across injury types must not read clinical."""

    # Templates with these substrings indicate the old medicalised prose
    # that was the symptom in #337. The wording was chosen to avoid
    # false positives — "severance", "amputation", "amputated" are still
    # acceptable so long as they aren't paired with the clinical
    # modifiers below.
    CLINICAL_MARKERS = (
        "surgical",
        "medically",
        "medical",
        "sterile",
        "professionally",
        "clinical",
        "clinically",
    )

    INJURY_TYPES = ("blunt", "bullet", "cut", "generic", "stab",
                    "laceration")

    def _load_severed_templates(self, injury_type):
        module = importlib.import_module(
            f"world.medical.wounds.messages.{injury_type}"
        )
        return module.WOUND_DESCRIPTIONS.get("severed", [])

    def test_severed_stage_has_at_least_seven_variants(self):
        for itype in self.INJURY_TYPES:
            with self.subTest(injury_type=itype):
                templates = self._load_severed_templates(itype)
                self.assertGreaterEqual(
                    len(templates), 7,
                    f"{itype}.py has only {len(templates)} severed-stage "
                    f"variants (expected >= 7)",
                )

    def test_no_clinical_vocabulary_in_severed_templates(self):
        for itype in self.INJURY_TYPES:
            for template in self._load_severed_templates(itype):
                for marker in self.CLINICAL_MARKERS:
                    with self.subTest(injury=itype, marker=marker):
                        self.assertNotIn(
                            marker, template.lower(),
                            f"{itype}.py severed template still contains "
                            f"clinical marker {marker!r}: {template!r}"
                        )


class SeveredStumpProgressionStagesTests(TestCase):
    """``severed.py`` carries the post-amputation stump progression
    (``treated`` / ``healing`` / ``scarred``) — previously single-line
    placeholders, now real prose so suture / healing / time-progressed
    stumps render distinct flavour."""

    def setUp(self):
        import world.medical.wounds.messages.severed as severed
        self.descriptions = severed.WOUND_DESCRIPTIONS

    def test_treated_stage_has_multiple_variants(self):
        # Suture transitions the synthetic cut-point wound from
        # ``fresh`` to ``treated``; the renderer picks one at random
        # — so multiple variants prevent repetitive prose on a body
        # with multiple amputations.
        self.assertGreaterEqual(len(self.descriptions["treated"]), 3)

    def test_healing_stage_has_multiple_variants(self):
        # Slotted for the time-based progression tick (future work).
        # Prose stocked now so the tick has somewhere to land.
        self.assertGreaterEqual(len(self.descriptions["healing"]), 3)

    def test_scarred_stage_has_multiple_variants(self):
        # Terminal stage of stump progression.
        self.assertGreaterEqual(len(self.descriptions["scarred"]), 3)

    def test_progression_templates_reference_location(self):
        # Every stump-progression template must accept the
        # ``{location}`` token — the renderer fills it with the
        # cut-point body part ("left arm", "head") at format time.
        for stage in ("treated", "healing", "scarred"):
            for template in self.descriptions[stage]:
                with self.subTest(stage=stage, template=template):
                    self.assertIn("{location}", template)


class LacerationFileTests(TestCase):
    """The laceration injury type now has its own wound-message file."""

    EXPECTED_STAGES = ("fresh", "treated", "healing", "destroyed",
                       "severed", "scarred")

    def setUp(self):
        # Re-import to pick up newly-added module on first run.
        import world.medical.wounds.messages as messages
        importlib.reload(messages)
        from world.medical.wounds.messages import laceration
        self.lac = laceration

    def test_laceration_module_loads(self):
        self.assertTrue(hasattr(self.lac, "WOUND_DESCRIPTIONS"))

    def test_all_stages_populated(self):
        for stage in self.EXPECTED_STAGES:
            with self.subTest(stage=stage):
                cell = self.lac.WOUND_DESCRIPTIONS.get(stage, [])
                self.assertGreaterEqual(
                    len(cell), 7,
                    f"laceration.{stage} has only {len(cell)} variants",
                )

    def test_compound_descriptions_present(self):
        self.assertTrue(hasattr(self.lac, "COMPOUND_DESCRIPTIONS"))
        compound = self.lac.COMPOUND_DESCRIPTIONS
        # At least the four "always present" compound stages.
        for stage in ("fresh", "treated", "healing", "destroyed"):
            with self.subTest(stage=stage):
                self.assertIn(stage, compound)
                self.assertGreaterEqual(len(compound[stage]), 1)

    def test_get_wound_description_routes_to_laceration(self):
        # End-to-end smoke test — `get_wound_description` with
        # injury_type='laceration' returns laceration-flavor prose, not
        # generic fallback.
        from world.medical.wounds import get_wound_description

        # Sample a fresh wound multiple times to cover variant selection.
        outputs = [
            get_wound_description(
                injury_type="laceration",
                location="left_arm",
                severity="Critical",
                stage="fresh",
            )
            for _ in range(20)
        ]
        joined = " ".join(outputs).lower()
        # At least one of these laceration-flavor markers should appear
        # across 20 samples — confirms the routing worked.
        lac_markers = (
            "jagged", "ragged", "chewed", "sawn", "ripped", "tearing",
            "mangled", "torn", "shredded",
        )
        self.assertTrue(
            any(marker in joined for marker in lac_markers),
            f"laceration routing produced no laceration-flavor markers "
            f"across 20 samples: {outputs[:3]!r}..."
        )
