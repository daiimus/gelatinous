"""Unit tests for symmetric left/right longdesc collapse (selection model).

The render path never rewrites authored prose; it only *selects* which stored
string represents a symmetric pair:

* an authored merged key (e.g. ``eyes``) stands in for both sides when both
  are visible;
* failing that, two identical side longdescs render once, verbatim;
* a pair severed on both sides collapses to one paired stump line;
* any divergence (asymmetric coverage, one side severed, differing prose with
  no merged key) falls back to separate, per-side rendering.

Run via::

    evennia test world.tests.test_paired_longdesc_collapse
"""

from __future__ import annotations

from unittest import TestCase, mock

from typeclasses.appearance_mixin import AppearanceMixin

WOUNDS = "world.medical.wounds"


class _Bare(AppearanceMixin):
    """Mixin host with no overrides, for testing the real helper methods."""


class _Body(AppearanceMixin):
    """Mixin host that stubs the cross-cutting deps the collapse logic uses."""

    def __init__(self, severed=None):
        self._severed = set(severed or ())

    def _process_description_variables(self, desc, looker, **kwargs):
        # Passthrough so tests can assert on the selected text directly.
        return desc

    def _get_severed_locations(self):
        return set(self._severed)


class _Render(AppearanceMixin):
    """Full-render host: stubs clothing, skintone processing and severance."""

    def __init__(self, longdescs, severed=None):
        self._longdescs = dict(longdescs)
        self._severed = set(severed or ())

    @property
    def longdesc(self):
        return self._longdescs

    def _build_clothing_coverage_map(self):
        return {}

    def _process_description_variables(self, desc, looker, **kwargs):
        return desc

    def _get_severed_locations(self):
        return set(self._severed)


class GetSeveredLocationsTests(TestCase):

    def setUp(self):
        self.obj = _Bare()

    def test_location_with_all_severed_wounds_is_severed(self):
        wounds = [
            {"location": "left_hand", "stage": "severed"},
            {"location": "left_hand", "stage": "severed"},
            {"location": "chest", "stage": "fresh"},
        ]
        with mock.patch(f"{WOUNDS}.get_character_wounds", return_value=wounds):
            self.assertEqual(self.obj._get_severed_locations(), {"left_hand"})

    def test_mixed_stage_location_is_not_severed(self):
        wounds = [
            {"location": "left_hand", "stage": "severed"},
            {"location": "left_hand", "stage": "fresh"},
        ]
        with mock.patch(f"{WOUNDS}.get_character_wounds", return_value=wounds):
            self.assertEqual(self.obj._get_severed_locations(), set())

    def test_no_wounds_no_severed(self):
        with mock.patch(f"{WOUNDS}.get_character_wounds", return_value=[]):
            self.assertEqual(self.obj._get_severed_locations(), set())


class BuildPairedCollapseTests(TestCase):

    def setUp(self):
        self.obj = _Body()

    def _build(self, longdescs, coverage_map=None):
        return self.obj._build_paired_longdesc_collapse(
            None, longdescs, coverage_map or {}
        )

    def test_identical_pair_collapses_verbatim(self):
        # No pluralization — the authored line is shown exactly as written.
        longdescs = {
            "left_hand": "A calloused hand.",
            "right_hand": "A calloused hand.",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertIn("left_hand", collapse_map)
        self.assertIn("right_hand", skip)
        self.assertEqual(collapse_map["left_hand"], "A calloused hand.")

    def test_merged_key_stands_in_for_both_sides(self):
        # Write-1: only the merged key is set; both sides default-empty.
        longdescs = {"eyes": "{Their} eyes gleam an unsettling silver."}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertEqual(
            collapse_map["left_eye"],
            "{Their} eyes gleam an unsettling silver.",
        )
        self.assertIn("right_eye", skip)

    def test_merged_key_wins_over_differing_sides(self):
        # Write-3: merged key is authoritative while both sides are visible.
        longdescs = {
            "eyes": "{Their} eyes gleam an unsettling silver.",
            "left_eye": "a silver left eye",
            "right_eye": "a silver right eye",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertEqual(
            collapse_map["left_eye"],
            "{Their} eyes gleam an unsettling silver.",
        )
        self.assertIn("right_eye", skip)

    def test_wound_on_one_side_stays_merged(self):
        longdescs = {
            "left_hand": "A calloused hand.",
            "right_hand": "A calloused hand.",
        }

        def _wound(_self, location, _looker):
            if location == "right_hand":
                return "A fresh laceration crosses the right hand."
            return ""

        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", side_effect=_wound
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertEqual(
            collapse_map["left_hand"],
            "A calloused hand. A fresh laceration crosses the right hand.",
        )
        self.assertIn("right_hand", skip)

    def test_asymmetric_coverage_does_not_collapse(self):
        longdescs = {
            "left_hand": "A calloused hand.",
            "right_hand": "A calloused hand.",
        }
        coverage = {"left_hand": object()}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs, coverage)
        self.assertEqual(collapse_map, {})
        self.assertEqual(skip, set())

    def test_covered_side_ignores_merged_key(self):
        # One eye covered: the pair does not collapse and the merged key must
        # not stand in — the visible side renders on its own elsewhere.
        longdescs = {
            "eyes": "{Their} eyes gleam an unsettling silver.",
            "left_eye": "a silver left eye",
            "right_eye": "a silver right eye",
        }
        coverage = {"left_eye": object()}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs, coverage)
        self.assertEqual(collapse_map, {})
        self.assertEqual(skip, set())

    def test_differing_prose_without_merged_key_does_not_collapse(self):
        longdescs = {
            "left_hand": "A calloused hand.",
            "right_hand": "A scarred hand.",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, _skip = self._build(longdescs)
        self.assertEqual(collapse_map, {})

    def test_only_one_side_described_does_not_collapse(self):
        longdescs = {"left_hand": "A calloused hand."}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, _skip = self._build(longdescs)
        self.assertEqual(collapse_map, {})

    def test_both_severed_collapses_to_paired_stump(self):
        self.obj = _Body(severed={"left_hand", "right_hand"})
        with mock.patch(
            f"{WOUNDS}.get_paired_severed_description",
            return_value="Both hands have been cleanly amputated.",
        ):
            collapse_map, skip = self._build({})
        self.assertEqual(
            collapse_map["left_hand"],
            "Both hands have been cleanly amputated.",
        )
        self.assertIn("right_hand", skip)

    def test_one_side_severed_does_not_collapse(self):
        self.obj = _Body(severed={"left_hand"})
        longdescs = {"right_hand": "A calloused hand."}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, _skip = self._build(longdescs)
        self.assertEqual(collapse_map, {})

    def test_one_side_severed_with_merged_key_does_not_collapse(self):
        # Write-1 + one side lost: the merged key must not stand in; the
        # survivor falls back to its own (default) rendering elsewhere.
        self.obj = _Body(severed={"left_eye"})
        longdescs = {"eyes": "{Their} eyes gleam an unsettling silver."}
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, _skip = self._build(longdescs)
        self.assertEqual(collapse_map, {})

    def test_custom_longdesc_pair_collapses_verbatim(self):
        # A non-registered symmetric pair still collapses on identical prose.
        longdescs = {
            "left_wing": "A feathered wing.",
            "right_wing": "A feathered wing.",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertEqual(collapse_map["left_wing"], "A feathered wing.")
        self.assertIn("right_wing", skip)


class VisibleBodyDescriptionsTests(TestCase):
    """End-to-end selection through ``_get_visible_body_descriptions``."""

    def _render(self, host):
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ), mock.patch(
            f"{WOUNDS}.append_wounds_to_longdesc",
            side_effect=lambda desc, *a, **k: desc,
        ):
            return host._get_visible_body_descriptions(None)

    def test_merged_key_renders_at_anchor_not_standalone(self):
        host = _Render({"eyes": "{Their} eyes gleam silver."})
        result = dict(self._render(host))
        self.assertEqual(result.get("left_eye"), "{Their} eyes gleam silver.")
        self.assertNotIn("right_eye", result)
        # The merged key itself never renders as its own line.
        self.assertNotIn("eyes", result)

    def test_identical_sides_render_once(self):
        host = _Render(
            {"left_hand": "A calloused hand.", "right_hand": "A calloused hand."}
        )
        result = dict(self._render(host))
        self.assertEqual(result.get("left_hand"), "A calloused hand.")
        self.assertNotIn("right_hand", result)

    def test_differing_sides_render_separately(self):
        host = _Render(
            {"left_hand": "A calloused hand.", "right_hand": "A scarred hand."}
        )
        result = dict(self._render(host))
        self.assertEqual(result.get("left_hand"), "A calloused hand.")
        self.assertEqual(result.get("right_hand"), "A scarred hand.")


class PairedSeveredDescriptionTests(TestCase):
    """The wound-module helper that renders the merged stump line."""

    def test_both_severed_returns_plural_stump(self):
        from world.medical.wounds import get_paired_severed_description

        wounds = [
            {"location": "left_hand", "stage": "severed"},
            {"location": "right_hand", "stage": "severed"},
        ]
        with mock.patch(
            "world.medical.wounds.longdesc_hooks.get_character_wounds",
            return_value=wounds,
        ):
            out = get_paired_severed_description(None, "left_hand", "right_hand")
        self.assertIsInstance(out, str)
        self.assertIn("hands", out.lower())
        # Capitalized and terminated by the grammar formatter.
        self.assertTrue(out[0].isupper())
        self.assertTrue(out.rstrip().endswith((".", ".|n")))

    def test_not_both_severed_returns_none(self):
        from world.medical.wounds import get_paired_severed_description

        wounds = [{"location": "left_hand", "stage": "severed"}]
        with mock.patch(
            "world.medical.wounds.longdesc_hooks.get_character_wounds",
            return_value=wounds,
        ):
            out = get_paired_severed_description(None, "left_hand", "right_hand")
        self.assertIsNone(out)
