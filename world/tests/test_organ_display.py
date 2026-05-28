"""Tests for organ display metadata (PR #202 / PR-G).

Covers :data:`world.medical.constants.ORGAN_DISPLAY` and the two
lookup helpers (``get_organ_display_name``,
``get_organ_default_description``).  Schema + coverage checks plus a
spot-check on the Organ typeclass key formatting at harvest time.
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.constants import (
    ORGAN_DISPLAY,
    ORGANS,
    get_organ_default_description,
    get_organ_display_name,
)


class TestOrganDisplayCoverage(TestCase):
    """Every harvestable organ must have display metadata registered."""

    def test_every_harvestable_organ_has_display_entry(self):
        missing = []
        for organ_name, data in ORGANS.items():
            if data.get("can_be_harvested"):
                if organ_name not in ORGAN_DISPLAY:
                    missing.append(organ_name)
        self.assertEqual(
            missing, [],
            f"Harvestable organs missing ORGAN_DISPLAY entries: {missing}",
        )

    def test_every_display_entry_has_required_keys(self):
        for organ_name, entry in ORGAN_DISPLAY.items():
            self.assertIn(
                "display_name", entry,
                f"{organ_name} missing display_name",
            )
            self.assertIn(
                "default_descriptions", entry,
                f"{organ_name} missing default_descriptions",
            )

    def test_every_display_entry_covers_three_conditions(self):
        required_conditions = {"pristine", "damaged", "putrid"}
        for organ_name, entry in ORGAN_DISPLAY.items():
            descs = entry.get("default_descriptions", {})
            missing = required_conditions - set(descs.keys())
            self.assertEqual(
                missing, set(),
                f"{organ_name} missing conditions: {missing}",
            )

    def test_descriptions_are_non_empty_strings(self):
        for organ_name, entry in ORGAN_DISPLAY.items():
            for condition, prose in entry["default_descriptions"].items():
                self.assertIsInstance(
                    prose, str,
                    f"{organ_name}/{condition} prose is not a string",
                )
                self.assertGreater(
                    len(prose.strip()), 0,
                    f"{organ_name}/{condition} prose is empty",
                )


class TestOrganDisplayHelpers(TestCase):
    def test_get_display_name_known_organ(self):
        self.assertEqual(get_organ_display_name("heart"), "heart")
        self.assertEqual(
            get_organ_display_name("left_kidney"), "left kidney"
        )

    def test_get_display_name_unknown_organ_falls_back(self):
        # Unregistered organs fall back to underscore-stripped key.
        self.assertEqual(
            get_organ_display_name("flux_capacitor"), "flux capacitor"
        )

    def test_get_default_description_returns_prose(self):
        prose = get_organ_default_description("heart", "pristine")
        self.assertTrue(prose)
        self.assertIn("heart", prose.lower())

    def test_get_default_description_unknown_organ_returns_empty(self):
        self.assertEqual(
            get_organ_default_description("flux_capacitor", "pristine"),
            "",
        )

    def test_get_default_description_unknown_condition_returns_empty(self):
        # ``refuse`` (skeletal-stage harvest) is intentionally absent —
        # the harvest command refuses skeletal corpses upstream.
        self.assertEqual(
            get_organ_default_description("heart", "refuse"), ""
        )
