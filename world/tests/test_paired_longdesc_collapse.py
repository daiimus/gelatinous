"""Unit tests for symmetric left/right longdesc collapse.

A matched ``left_*``/``right_*`` pair with identical longdescs renders as one
line (the prose rendered once at plural number); a wound sits on its own side
without splitting the pair; a pair severed on both sides collapses to one
plural stump line; and any divergence (coverage, severance of one side,
differing prose) falls back to separate rendering. Token rendering
(``{eye}``/``{accents}`` number-flexing) is covered by ``TokenRenderTests``.

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
        # Passthrough so tests can assert which pairs collapse without
        # exercising the token renderer (covered separately).
        return desc

    def _get_severed_locations(self):
        return set(self._severed)


class _Render(AppearanceMixin):
    """Minimal host for exercising the real token renderer."""

    gender = "neutral"

    class _DB:
        skintone = None

    db = _DB()

    def get_display_name(self, looker):
        return "Vasquez"

    def render(self, desc, number):
        return self._process_description_variables(
            desc, looker=object(), force_third_person=True, number=number,
        )


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

    def test_identical_pair_collapses(self):
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
        # Rendered once, verbatim (the passthrough stub bypasses token flex).
        self.assertEqual(collapse_map["left_hand"], "A calloused hand.")

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

    def test_differing_prose_does_not_collapse(self):
        longdescs = {
            "left_hand": "A calloused hand.",
            "right_hand": "A scarred hand.",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, _skip = self._build(longdescs)
        self.assertEqual(collapse_map, {})

    def test_untokenized_identical_pair_collapses_verbatim(self):
        # Identity, not the presence of an anatomical noun, drives collapse:
        # untokenized prose renders once, verbatim.
        longdescs = {
            "left_hand": "a sleek prosthetic appendage",
            "right_hand": "a sleek prosthetic appendage",
        }
        with mock.patch(
            f"{WOUNDS}.get_standalone_wound_description", return_value=""
        ):
            collapse_map, skip = self._build(longdescs)
        self.assertEqual(
            collapse_map["left_hand"], "a sleek prosthetic appendage"
        )
        self.assertIn("right_hand", skip)

    def test_both_severed_collapses_to_plural_stump(self):
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

    def test_custom_longdesc_pair_collapses(self):
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


class TokenRenderTests(TestCase):
    """The real token renderer: pronoun tokens plus number-flexing."""

    def setUp(self):
        self.obj = _Render()

    def test_pronoun_token_unaffected_by_number(self):
        # Pronoun number tracks gender, not the body-part render number.
        self.assertEqual(
            self.obj.render("{Their} gaze.", "plural"), "Their gaze."
        )
        self.assertEqual(
            self.obj.render("{Their} gaze.", "singular"), "Their gaze."
        )

    def test_pair_renders_plural(self):
        out = self.obj.render(
            "deep brown {eyes} that {accent} {their} skin", "plural"
        )
        self.assertEqual(out, "deep brown eyes that accent their skin")

    def test_survivor_renders_singular(self):
        out = self.obj.render(
            "deep brown {eyes} that {accent} {their} skin", "singular"
        )
        self.assertEqual(out, "deep brown eye that accents their skin")

    def test_article_noun_token_plural_drops_article(self):
        out = self.obj.render("{An eye} {gleams} coldly.", "plural")
        self.assertEqual(out, "Eyes gleam coldly.")

    def test_article_noun_token_singular_keeps_article(self):
        out = self.obj.render("{An eye} {gleams} coldly.", "singular")
        self.assertEqual(out, "An eye gleams coldly.")

    def test_irregular_pair_noun(self):
        self.assertEqual(
            self.obj.render("scarred {feet}", "plural"), "scarred feet"
        )
        self.assertEqual(
            self.obj.render("scarred {feet}", "singular"), "scarred foot"
        )

    def test_noun_vs_verb_autodetect(self):
        # "arm" is a pair noun; "flex" is not, so it conjugates as a verb.
        out = self.obj.render("{arms} that {flex}", "singular")
        self.assertEqual(out, "arm that flexes")

    def test_untokenized_prose_verbatim(self):
        text = "a milky white orb, unseeing."
        self.assertEqual(self.obj.render(text, "plural"), text)

    def test_unknown_multiword_token_left_literal(self):
        out = self.obj.render("a strange {foo bar} thing", "plural")
        self.assertEqual(out, "a strange {foo bar} thing")


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
