"""Tests for the destroyed-stage prose overlay (issue #347).

After #346 routes wounds to ``left_eye`` / ``right_eye`` / ``left_ear`` /
``right_ear`` (instead of the bulk ``head`` container), the generic
destroyed-stage prose in ``world/medical/wounds/messages/*.py`` reads
wrong for sensory surfaces — \"His left eye has been mangled into
ribbons of flesh\" is limb vocabulary, not eye vocabulary.

This issue adds a ``DESTROYED_BY_LOCATION`` overlay to each injury-type
module so destruction at high-specificity surfaces reads in the right
anatomical register, with fall-through to the existing generic
destroyed list for unmapped locations.

Tests verify:

* Each shipped injury-type module declares the overlay for the four
  sensory locations.
* ``get_wound_description`` consults the overlay before the generic
  destroyed list when ``stage == \"destroyed\"``.
* Pronoun tokens (``{Their}`` / ``{their}``) resolve against the
  character's gender.
* Limb destruction still uses the generic prose (fall-through).
* Non-destroyed stages are unaffected by the overlay.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.wounds import messages
from world.medical.wounds.wound_descriptions import get_wound_description


SENSORY_LOCATIONS = ("left_eye", "right_eye", "left_ear", "right_ear")
INJURY_TYPES_WITH_OVERLAY = (
    "cut", "stab", "bullet", "blunt", "laceration", "generic",
)


def _char(gender="male"):
    """Minimal stub exposing the surfaces ``get_wound_description`` reads."""
    return SimpleNamespace(
        gender=gender,
        db=SimpleNamespace(
            original_gender=gender,
            skintone=None,
            species="human",
        ),
    )


class OverlayDeclaredOnEveryShippedModule(TestCase):
    """Each shipped injury-type module declares the overlay for all
    sensory surfaces with at least 3 variants per cell."""

    def test_every_module_declares_overlay(self):
        for itype in INJURY_TYPES_WITH_OVERLAY:
            with self.subTest(itype=itype):
                module = getattr(messages, itype)
                overlay = getattr(module, "DESTROYED_BY_LOCATION", None)
                self.assertIsNotNone(
                    overlay,
                    f"{itype}.py must declare DESTROYED_BY_LOCATION",
                )

    def test_every_module_covers_all_sensory_locations(self):
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            overlay = module.DESTROYED_BY_LOCATION
            for loc in SENSORY_LOCATIONS:
                with self.subTest(itype=itype, location=loc):
                    self.assertIn(loc, overlay)
                    self.assertGreaterEqual(
                        len(overlay[loc]), 3,
                        f"{itype}.{loc} needs at least 3 variants for "
                        f"non-repetitive rendering",
                    )


class OverlaySwapsAtDestroyedStage(TestCase):
    """``get_wound_description`` consults the overlay for destroyed
    sensory wounds."""

    def test_destroyed_eye_uses_eye_vocabulary(self):
        # We can't assert exact prose (random.choice variance), but we
        # CAN assert the rendered output uses anatomical eye vocabulary
        # and never the limb "mangled / ribbons of flesh" wording from
        # the generic destroyed list.
        out = get_wound_description(
            injury_type="cut", location="left_eye",
            severity="Critical", stage="destroyed",
            organ="left_eye", character=_char(),
        )
        self.assertNotIn("ribbons of flesh", out)
        self.assertNotIn("hanging by threads", out)
        # And reads like an eye line.
        self.assertIn("eye", out.lower())

    def test_destroyed_ear_uses_ear_vocabulary(self):
        out = get_wound_description(
            injury_type="bullet", location="left_ear",
            severity="Critical", stage="destroyed",
            organ="left_ear", character=_char(),
        )
        self.assertNotIn("ribbons of flesh", out)
        self.assertIn("ear", out.lower())

    def test_overlay_runs_through_every_variant(self):
        # Smoke: each variant in every (injury_type, location) overlay
        # cell renders without leaking braces, raising, or producing
        # an empty string.
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            for loc, variants in module.DESTROYED_BY_LOCATION.items():
                for variant in variants:
                    with self.subTest(itype=itype, loc=loc):
                        # We monkeypatch ``random.choice`` to a passthrough
                        # so the variant under test is the one rendered.
                        import random
                        original = random.choice
                        random.choice = lambda seq, _v=variant: _v
                        try:
                            out = get_wound_description(
                                injury_type=itype,
                                location=loc,
                                severity="Critical",
                                stage="destroyed",
                                organ=loc,
                                character=_char(),
                            )
                        finally:
                            random.choice = original
                        self.assertTrue(out)
                        self.assertNotIn("{", out,
                                         f"leaked brace in {out!r}")
                        self.assertNotIn("}", out)


class PronounSubstitution(TestCase):
    """Pronoun tokens resolve against the character's gender."""

    def test_male_renders_his(self):
        # Force a known variant by monkeypatching random.choice.
        import random
        forced = "|R{Their} left eye is gone.|n"
        original = random.choice
        random.choice = lambda seq, _v=forced: _v
        try:
            out = get_wound_description(
                injury_type="generic", location="left_eye",
                severity="Critical", stage="destroyed",
                organ="left_eye", character=_char(gender="male"),
            )
        finally:
            random.choice = original
        # _format_wound_grammar may sentence-cap "His" at the start;
        # we just need the token resolved to the male possessive.
        self.assertIn("His", out)
        self.assertNotIn("{Their}", out)

    def test_female_renders_her(self):
        import random
        forced = "|R{Their} left eye is gone.|n"
        original = random.choice
        random.choice = lambda seq, _v=forced: _v
        try:
            out = get_wound_description(
                injury_type="generic", location="left_eye",
                severity="Critical", stage="destroyed",
                organ="left_eye", character=_char(gender="female"),
            )
        finally:
            random.choice = original
        self.assertIn("Her", out)

    def test_no_character_leaves_tokens_literal(self):
        # No pronoun pass when character is None.  The brace token
        # remains so a downstream renderer (or a developer noticing
        # the leak) can spot the missing context.
        import random
        forced = "|R{Their} left eye is gone.|n"
        original = random.choice
        random.choice = lambda seq, _v=forced: _v
        try:
            out = get_wound_description(
                injury_type="generic", location="left_eye",
                severity="Critical", stage="destroyed",
                organ="left_eye", character=None,
            )
        finally:
            random.choice = original
        self.assertIn("{Their}", out)


class LimbDestructionFallsThrough(TestCase):
    """Limb destruction has no overlay → uses the generic destroyed
    list (limb vocabulary reads correctly for limbs)."""

    def test_destroyed_arm_uses_generic_limb_prose(self):
        out = get_wound_description(
            injury_type="cut", location="left_arm",
            severity="Critical", stage="destroyed",
            organ="left_humerus", character=_char(),
        )
        # The generic destroyed list contains "ribbons of flesh" /
        # "hanging by threads" / "bloody tatters" — at least one of
        # those families is what limb destruction reads as. We assert
        # only that the output does NOT use eye-only vocabulary, to
        # confirm the fall-through path took.
        self.assertNotIn("vitreous fluid", out)
        self.assertNotIn("orb", out)
        self.assertIn("arm", out.lower())


class NonDestroyedStagesUnchanged(TestCase):
    """Overlay is destroyed-stage only — fresh/treated/healing/scarred
    routing is unchanged."""

    def test_fresh_stage_ignores_overlay(self):
        # A "fresh" stage wound at left_eye must NOT pick from the
        # destroyed overlay — it should render through WOUND_DESCRIPTIONS
        # ["fresh"].
        out = get_wound_description(
            injury_type="cut", location="left_eye",
            severity="Light", stage="fresh",
            organ="left_eye", character=_char(),
        )
        # Fresh cut prose mentions cut/laceration/slash vocabulary, not
        # "ruined socket" / "split open" (overlay-only phrases).
        self.assertNotIn("vitreous fluid", out)
        self.assertNotIn("ruined socket", out)

    def test_scarred_stage_ignores_overlay(self):
        out = get_wound_description(
            injury_type="cut", location="left_eye",
            severity="Moderate", stage="scarred",
            organ="left_eye", character=_char(),
        )
        self.assertNotIn("vitreous fluid", out)
        self.assertNotIn("ruined socket", out)
