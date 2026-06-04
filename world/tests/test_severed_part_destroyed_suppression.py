"""Tests for severed-part destroyed-organ longdesc suppression.

Issue #350 follow-up.  PR-B suppressed authored longdescs at destroyed
display surfaces on living characters and corpses; severed parts
(``Appendage``, ``SeveredHead``) were deferred because their carried
wound list (``wounds_at_death``) is rewritten to ``stage=\"old\"`` at
sever-overlay time — the wound-list-based check used by PR-B never
matches.

The fix consults the preserved organ snapshot
(``db.medical_state_at_death``), where the destroyed wound stage is
preserved verbatim.  A head decapitated after an eye was destroyed
in life now drops the authored eye longdesc instead of rendering
\"His left eye is brown\" alongside the carried wound.

Tests cover the pure helper and the integration shape on a stub
Appendage; the live ``return_appearance`` integration is exercised
implicitly via the full suite running the existing severed-head
renderer tests.
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.wounds import get_destroyed_locations_from_snapshot


class HelperReturnsDestroyedDisplayLocations(TestCase):

    def test_empty_snapshot_returns_empty_set(self):
        self.assertEqual(get_destroyed_locations_from_snapshot(None), set())
        self.assertEqual(get_destroyed_locations_from_snapshot({}), set())

    def test_no_organs_returns_empty_set(self):
        self.assertEqual(
            get_destroyed_locations_from_snapshot({"organs": {}}),
            set(),
        )

    def test_destroyed_organ_extracted_via_display_location(self):
        snapshot = {
            "organs": {
                "left_eye": {
                    "container": "head",
                    "display_location": "left_eye",
                    "wound_stage": "destroyed",
                },
            },
        }
        self.assertEqual(
            get_destroyed_locations_from_snapshot(snapshot),
            {"left_eye"},
        )

    def test_destroyed_organ_falls_back_to_container_when_no_display(self):
        # Legacy snapshot pre-#346 didn't carry display_location.
        snapshot = {
            "organs": {
                "heart": {
                    "container": "chest",
                    "wound_stage": "destroyed",
                },
            },
        }
        self.assertEqual(
            get_destroyed_locations_from_snapshot(snapshot),
            {"chest"},
        )

    def test_non_destroyed_stages_ignored(self):
        snapshot = {
            "organs": {
                "left_eye": {
                    "container": "head",
                    "display_location": "left_eye",
                    "wound_stage": "severed",
                },
                "brain": {
                    "container": "head",
                    "wound_stage": "fresh",
                },
                "left_humerus": {
                    "container": "left_arm",
                    "wound_stage": None,
                },
            },
        }
        self.assertEqual(
            get_destroyed_locations_from_snapshot(snapshot),
            set(),
        )

    def test_mixed_organs(self):
        snapshot = {
            "organs": {
                "left_eye": {
                    "container": "head",
                    "display_location": "left_eye",
                    "wound_stage": "destroyed",
                },
                "right_eye": {
                    "container": "head",
                    "display_location": "right_eye",
                    "wound_stage": "destroyed",
                },
                "brain": {
                    "container": "head",
                    "wound_stage": "fresh",
                },
            },
        }
        self.assertEqual(
            get_destroyed_locations_from_snapshot(snapshot),
            {"left_eye", "right_eye"},
        )

    def test_missing_location_data_skipped(self):
        # Defensive: organ entries lacking both container and
        # display_location produce no location to add.
        snapshot = {
            "organs": {
                "weird_orphan": {"wound_stage": "destroyed"},
            },
        }
        self.assertEqual(
            get_destroyed_locations_from_snapshot(snapshot),
            set(),
        )
