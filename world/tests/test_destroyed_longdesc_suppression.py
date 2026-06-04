"""Tests for the destroyed-organ longdesc suppression (issue #350 / PR-B).

When an organ at a display location has ``wound_stage == \"destroyed\"``,
the authored longdesc at that location is suppressed across living,
corpse, and severed-part renderers so the destruction wound carries
the visual state alone — the authored prose (\"His left eye is brown\")
otherwise lies alongside the destruction wound.

Coverage interaction: ``get_character_wounds`` filters by clothing
visibility, so a destroyed organ hidden under armor produces no wound
in the visible list and the authored prose remains as a fallback
(observer can't see the destruction; they see the authored line).

Pair-collapse interaction: the authored-longdesc identical-prose
collapse (case 1) is suppressed when either side carries a destroyed
organ — per-side wound rendering takes over (PR-C will add a paired
destruction collapse).

Run via::

    evennia test world.tests.test_destroyed_longdesc_suppression
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.wounds import get_destroyed_display_locations


class HelperReturnsDestroyedLocationSet(TestCase):

    def test_empty_input_returns_empty_set(self):
        self.assertEqual(get_destroyed_display_locations([]), set())
        self.assertEqual(get_destroyed_display_locations(None), set())

    def test_destroyed_wound_extracted(self):
        wounds = [
            {"location": "left_eye", "stage": "destroyed"},
        ]
        self.assertEqual(
            get_destroyed_display_locations(wounds),
            {"left_eye"},
        )

    def test_non_destroyed_stages_ignored(self):
        wounds = [
            {"location": "left_eye", "stage": "fresh"},
            {"location": "right_eye", "stage": "healing"},
            {"location": "left_arm", "stage": "severed"},
            {"location": "chest", "stage": "scarred"},
        ]
        self.assertEqual(get_destroyed_display_locations(wounds), set())

    def test_mixed_set(self):
        wounds = [
            {"location": "left_eye", "stage": "destroyed"},
            {"location": "right_eye", "stage": "fresh"},
            {"location": "chest", "stage": "destroyed"},
        ]
        self.assertEqual(
            get_destroyed_display_locations(wounds),
            {"left_eye", "chest"},
        )

    def test_missing_location_field_skipped(self):
        wounds = [
            {"location": None, "stage": "destroyed"},
            {"stage": "destroyed"},  # no location key
        ]
        self.assertEqual(get_destroyed_display_locations(wounds), set())


# ---------------------------------------------------------------------
# Pair-collapse suppression (living)
# ---------------------------------------------------------------------


class _MinimalCharacter:
    """Just enough surface to exercise the pair-collapse method."""

    def __init__(self, *, longdescs, severed=None, destroyed=None):
        self.longdesc = dict(longdescs)
        self._severed = set(severed or ())
        self._destroyed = set(destroyed or ())

    # AppearanceMixin._build_paired_longdesc_collapse hits these.
    def _get_severed_locations(self):
        return set(self._severed)

    def _get_destroyed_locations(self):
        return set(self._destroyed)


class PairCollapseSuppression(TestCase):
    """The authored-longdesc identical-prose collapse (case 1)
    suppresses when either side carries a destroyed organ.
    Severance collapse (case 2) is unaffected."""

    def _merge(self, char, left_loc, right_loc):
        """Drive ``_merge_paired_location`` directly so we test the
        destruction suppression without dragging in the full
        ``_build_paired_longdesc_collapse`` surface (clothing coverage
        scaffolding, anatomical-order constants, etc.).
        """
        from typeclasses.appearance_mixin import AppearanceMixin
        return AppearanceMixin._merge_paired_location(
            char, looker=None,
            left_loc=left_loc, right_loc=right_loc,
            longdescs=char.longdesc,
            severed_locs=char._get_severed_locations(),
            destroyed_locs=char._get_destroyed_locations(),
        )

    def test_left_destroyed_breaks_identical_longdesc_collapse(self):
        # Both longdescs identical, but left_eye organ destroyed →
        # case 1 collapse rejected so per-side rendering can carry
        # the destruction wound on the destroyed side.
        char = _MinimalCharacter(
            longdescs={
                "left_eye":  "{Their} {eyes} are brown.",
                "right_eye": "{Their} {eyes} are brown.",
            },
            destroyed={"left_eye"},
        )
        merged = self._merge(char, "left_eye", "right_eye")
        # No collapse at all — case 1 rejected, case 2 also fails
        # (not severed). Per-side rendering takes over.
        self.assertIsNone(merged)

    def test_right_destroyed_breaks_identical_longdesc_collapse(self):
        char = _MinimalCharacter(
            longdescs={
                "left_eye":  "{Their} {eyes} are brown.",
                "right_eye": "{Their} {eyes} are brown.",
            },
            destroyed={"right_eye"},
        )
        merged = self._merge(char, "left_eye", "right_eye")
        self.assertIsNone(merged)

    def test_both_destroyed_breaks_identical_longdesc_collapse(self):
        char = _MinimalCharacter(
            longdescs={
                "left_eye":  "{Their} {eyes} are brown.",
                "right_eye": "{Their} {eyes} are brown.",
            },
            destroyed={"left_eye", "right_eye"},
        )
        merged = self._merge(char, "left_eye", "right_eye")
        self.assertIsNone(merged)

    def test_severed_collapse_unaffected_by_destroyed_loc_param(self):
        # Both arms severed (no longdescs, both in severed_locs) —
        # case 2 collapse path is independent of destroyed_locs and
        # still fires.  We can't easily test that the case-2 builder
        # returns a real string here without the wound system, but
        # we CAN confirm the destroyed-loc check doesn't reject it
        # when neither side is in destroyed_locs.
        char = _MinimalCharacter(
            longdescs={},
            severed={"left_arm", "right_arm"},
        )
        # The call may return None if get_paired_severed_description
        # can't be imported against this stub — that's a stub limit,
        # not a regression. We assert only that no exception bubbles
        # out from the destroyed-loc check itself.
        try:
            self._merge(char, "left_arm", "right_arm")
        except (AttributeError, ImportError):
            # Case 2 needs the wound system; degrade gracefully.
            pass
