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
        ):
            self.assertIn(key, human, f"human species missing '{key}'")

    def test_decay_stages_complete(self):
        """Every decay stage must have prefix + corpse-name templates."""
        human = SPECIES_DEFINITIONS["human"]
        stages = {"fresh", "early", "moderate", "advanced", "skeletal"}
        self.assertEqual(set(human["decay_part_prefixes"].keys()), stages)
        self.assertEqual(set(human["decay_corpse_names"].keys()), stages)
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
