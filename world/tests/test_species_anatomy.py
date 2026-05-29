"""Tests for the species anatomy overlay (PR #202 / PR-G).

Covers :mod:`world.anatomy.species` — the data registry and the three
pure-function helpers (``get_species_location_display``,
``get_species_part_name``, ``get_species_corpse_name``).  These helpers
are state-free and consumed by every species-aware rendering path,
so we exercise them directly rather than through the typeclass
integration paths (which have their own targeted suites).
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    SPECIES_DEFINITIONS,
    get_species_corpse_description,
    get_species_corpse_name,
    get_species_location_display,
    get_species_organ_name,
    get_species_part_name,
)


class TestSpeciesRegistry(TestCase):
    """Sanity-check the shape of :data:`SPECIES_DEFINITIONS`."""

    def test_human_species_registered(self):
        self.assertIn("human", SPECIES_DEFINITIONS)

    def test_human_has_required_keys(self):
        human = SPECIES_DEFINITIONS["human"]
        for key in (
            "display_name",
            "location_display",
            "decay_part_prefixes",
            "decay_corpse_names",
            "decay_corpse_descriptions",
        ):
            self.assertIn(key, human, f"human species missing '{key}'")

    def test_decay_stages_complete(self):
        """Every decay stage must have prefix + corpse-name templates."""
        human = SPECIES_DEFINITIONS["human"]
        stages = {"fresh", "early", "moderate", "advanced", "skeletal"}
        self.assertEqual(set(human["decay_part_prefixes"].keys()), stages)
        self.assertEqual(set(human["decay_corpse_names"].keys()), stages)
        # Issue #232: corpse-description prose templates mirror the same
        # five-stage shape as names / part / organ prefixes.
        self.assertEqual(
            set(human["decay_corpse_descriptions"].keys()), stages
        )
        # Issue #212: organ-specific decay prefixes mirror part prefixes
        # in shape but substitute ``desiccated`` for ``skeletal``.
        self.assertEqual(set(human["decay_organ_prefixes"].keys()), stages)


class TestLocationDisplay(TestCase):
    def test_known_location(self):
        self.assertEqual(
            get_species_location_display("human", "left_arm"), "left arm"
        )

    def test_underscore_passthrough_for_unknown_location(self):
        # Defensive — unmapped locations still render readably.
        self.assertEqual(
            get_species_location_display("human", "third_arm"), "third arm"
        )

    def test_unknown_species_falls_back_to_human(self):
        self.assertEqual(
            get_species_location_display("synth", "head"), "head"
        )

    def test_none_species_falls_back_to_human(self):
        self.assertEqual(
            get_species_location_display(None, "chest"), "chest"
        )


class TestPartName(TestCase):
    def test_fresh_includes_species(self):
        self.assertEqual(
            get_species_part_name("human", "left_arm", "fresh"),
            "human left arm",
        )

    def test_early_includes_species(self):
        self.assertEqual(
            get_species_part_name("human", "head", "early"),
            "human head",
        )

    def test_moderate_drops_species(self):
        self.assertEqual(
            get_species_part_name("human", "left_arm", "moderate"),
            "rotting left arm",
        )

    def test_advanced_drops_species(self):
        self.assertEqual(
            get_species_part_name("human", "chest", "advanced"),
            "rotting chest",
        )

    def test_skeletal_uses_skeletal_prefix(self):
        self.assertEqual(
            get_species_part_name("human", "left_femur", "skeletal"),
            "skeletal left femur",
        )

    def test_unknown_stage_falls_back_to_fresh(self):
        # Unknown decay stage → fresh template.
        self.assertEqual(
            get_species_part_name("human", "head", "wibbly"),
            "human head",
        )


class TestCorpseName(TestCase):
    def test_fresh_corpse(self):
        self.assertEqual(
            get_species_corpse_name("human", "fresh"), "human corpse"
        )

    def test_early_corpse(self):
        self.assertEqual(
            get_species_corpse_name("human", "early"), "human corpse"
        )

    def test_moderate_corpse(self):
        self.assertEqual(
            get_species_corpse_name("human", "moderate"), "rotting corpse"
        )

    def test_advanced_corpse(self):
        self.assertEqual(
            get_species_corpse_name("human", "advanced"), "rotting corpse"
        )

    def test_skeletal_corpse_uses_remains_vocabulary(self):
        # Deliberate signal of decay irreversibility — "remains" not
        # "corpse".
        self.assertEqual(
            get_species_corpse_name("human", "skeletal"),
            "skeletal remains",
        )

    def test_unknown_stage_falls_back_to_fresh(self):
        self.assertEqual(
            get_species_corpse_name("human", "wibbly"), "human corpse"
        )

    def test_unknown_species_falls_back_to_human(self):
        self.assertEqual(
            get_species_corpse_name("synth", "fresh"), "human corpse"
        )


class TestOrganName(TestCase):
    """Issue #212: species + decay-tier aware organ naming."""

    def test_fresh_includes_species(self):
        self.assertEqual(
            get_species_organ_name("human", "heart", "fresh"),
            "human heart",
        )

    def test_early_includes_species(self):
        self.assertEqual(
            get_species_organ_name("human", "left_kidney", "early"),
            "human left kidney",
        )

    def test_moderate_drops_species(self):
        self.assertEqual(
            get_species_organ_name("human", "heart", "moderate"),
            "rotting heart",
        )

    def test_advanced_drops_species(self):
        self.assertEqual(
            get_species_organ_name("human", "liver", "advanced"),
            "rotting liver",
        )

    def test_skeletal_uses_desiccated_for_soft_tissue(self):
        # Organs don't skeletonize — they desiccate.  This is the
        # critical divergence from ``get_species_part_name``.
        self.assertEqual(
            get_species_organ_name("human", "heart", "skeletal"),
            "desiccated heart",
        )

    def test_none_stage_falls_back_to_fresh(self):
        self.assertEqual(
            get_species_organ_name("human", "brain", None),
            "human brain",
        )

    def test_unknown_stage_falls_back_to_fresh(self):
        self.assertEqual(
            get_species_organ_name("human", "brain", "wibbly"),
            "human brain",
        )

    def test_unknown_species_drops_species_token(self):
        # Issue #215: unknown species drop the species prefix entirely
        # at fresh / early decay, rendering bare organ names.  Feature,
        # not bug — accidentally-alien organs read as inscrutable.
        self.assertEqual(
            get_species_organ_name("unobtanium_alien", "heart", "fresh"),
            "heart",
        )

    def test_none_species_drops_species_token(self):
        # Issue #215: ``None`` species behaves identically to unknown.
        self.assertEqual(
            get_species_organ_name(None, "liver", "fresh"),
            "liver",
        )

    def test_unknown_species_late_decay_unaffected(self):
        # Late-decay templates already drop the species token, so
        # unknown-species rendering at moderate / skeletal stages
        # matches the known-species output.
        self.assertEqual(
            get_species_organ_name("unobtanium_alien", "heart", "moderate"),
            "rotting heart",
        )
        self.assertEqual(
            get_species_organ_name("unobtanium_alien", "heart", "skeletal"),
            "desiccated heart",
        )

    def test_unknown_organ_falls_back_to_underscore_stripped(self):
        self.assertEqual(
            get_species_organ_name("human", "flux_capacitor", "fresh"),
            "human flux capacitor",
        )


class TestCorpseDescription(TestCase):
    """Issue #232: species + decay-tier aware corpse body prose."""

    BASE = "He has tousled brown hair and a jagged scar."

    def test_fresh_includes_species_and_base_desc(self):
        out = get_species_corpse_description("human", "fresh", self.BASE)
        self.assertTrue(out.startswith("A recently deceased human body."))
        self.assertIn(self.BASE, out)
        self.assertIn("no signs of decomposition yet visible", out)

    def test_early_includes_species_and_base_desc(self):
        out = get_species_corpse_description("human", "early", self.BASE)
        self.assertTrue(out.startswith("A pale human corpse."))
        self.assertIn(self.BASE, out)

    def test_moderate_includes_species_drops_base_desc(self):
        out = get_species_corpse_description("human", "moderate", self.BASE)
        self.assertTrue(out.startswith("Decomposing human remains."))
        # By moderate decay the death-time snapshot no longer applies.
        self.assertNotIn(self.BASE, out)

    def test_advanced_includes_species_drops_base_desc(self):
        out = get_species_corpse_description("human", "advanced", self.BASE)
        self.assertTrue(out.startswith("Putrid human remains."))
        self.assertNotIn(self.BASE, out)

    def test_skeletal_includes_species_drops_base_desc(self):
        out = get_species_corpse_description("human", "skeletal", self.BASE)
        self.assertTrue(out.startswith("Skeletal human remains."))
        self.assertNotIn(self.BASE, out)

    def test_unknown_stage_falls_back_to_fresh(self):
        out = get_species_corpse_description("human", "wibbly", self.BASE)
        self.assertTrue(out.startswith("A recently deceased human body."))

    def test_unknown_species_drops_species_token(self):
        # Issue #215 convention: an unregistered species drops the
        # species word entirely rather than misclaiming "human", and
        # leaves no double space behind.
        out = get_species_corpse_description(
            "unobtanium_alien", "fresh", self.BASE
        )
        self.assertTrue(out.startswith("A recently deceased body."))
        self.assertNotIn("human", out)
        self.assertNotIn("  ", out)

    def test_none_species_drops_species_token(self):
        out = get_species_corpse_description(None, "moderate", self.BASE)
        self.assertTrue(out.startswith("Decomposing remains."))
        self.assertNotIn("human", out)
        self.assertNotIn("  ", out)

    def test_unknown_species_late_decay_no_double_space(self):
        # Every tier templates {species}; the empty token must collapse
        # cleanly at all stages, not just the fresh / early ones.
        for stage in ("fresh", "early", "moderate", "advanced", "skeletal"):
            out = get_species_corpse_description("xeno", stage, self.BASE)
            self.assertNotIn("  ", out, f"double space at stage {stage!r}")
            self.assertNotIn("human", out, f"'human' leaked at {stage!r}")

    def test_default_base_desc_used_when_omitted(self):
        out = get_species_corpse_description("human", "fresh")
        self.assertIn("A lifeless body.", out)

    def test_empty_base_desc_no_double_space(self):
        # An empty base_desc in the fresh template must not leave a
        # double space where {base_desc} was.
        out = get_species_corpse_description("human", "fresh", "")
        self.assertNotIn("  ", out)
