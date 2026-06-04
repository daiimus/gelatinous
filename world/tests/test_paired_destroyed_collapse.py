"""Tests for the paired destruction collapse (issue #350 / PR-C).

When both sides of a symmetric pair (eyes, ears, ...) carry destroyed
wounds AND share an injury type, the renderer collapses the two
per-side destruction lines into a single pluralized line keyed by the
``DESTROYED_BY_PAIR`` overlay on the injury-type message module.

Tests cover:

* Each shipped injury-type module declares the overlay for eyes and
  ears with at least 3 variants per cell.
* ``get_paired_destroyed_description`` returns a pair line when both
  sides destroyed by same mechanism.
* Returns ``None`` when sides diverge (different injury types) —
  per-side rendering takes over rather than lying about a unified
  cause.
* Returns ``None`` when only one side is destroyed.
* Pronoun tokens resolve against the character's gender.
* Generic fallback fires when the per-injury-type module has no
  overlay for the pair key.
* Corpse path: helper threads the preserved wound snapshot through
  the ``wounds`` override and renders the same way.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.wounds import (
    get_paired_destroyed_description,
)
from world.medical.wounds import messages


PAIR_KEYS_WITH_OVERLAY = ("eyes", "ears")
INJURY_TYPES_WITH_OVERLAY = (
    "cut", "stab", "bullet", "blunt", "laceration", "generic",
)


def _char(gender="male", species="human"):
    return SimpleNamespace(
        gender=gender,
        db=SimpleNamespace(
            original_gender=gender,
            species=species,
            skintone=None,
        ),
    )


def _wound(location, injury_type="cut", severity="Critical",
           stage="destroyed", organ=None):
    return {
        "injury_type": injury_type,
        "location": location,
        "severity": severity,
        "stage": stage,
        "organ": organ or location,
    }


class OverlayDeclaredOnEveryModule(TestCase):

    def test_every_module_declares_pair_overlay(self):
        for itype in INJURY_TYPES_WITH_OVERLAY:
            with self.subTest(itype=itype):
                module = getattr(messages, itype)
                overlay = getattr(module, "DESTROYED_BY_PAIR", None)
                self.assertIsNotNone(
                    overlay,
                    f"{itype}.py must declare DESTROYED_BY_PAIR",
                )

    def test_every_module_covers_eyes_and_ears(self):
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            overlay = module.DESTROYED_BY_PAIR
            for pair_key in PAIR_KEYS_WITH_OVERLAY:
                with self.subTest(itype=itype, pair_key=pair_key):
                    self.assertIn(pair_key, overlay)
                    self.assertGreaterEqual(
                        len(overlay[pair_key]), 3,
                        f"{itype}.{pair_key} needs ≥3 variants",
                    )


class CollapseFiresWhenBothSidesSameMechanism(TestCase):

    def test_both_eyes_cut_yields_pair_line(self):
        char = _char()
        wounds = [
            _wound("left_eye", injury_type="cut"),
            _wound("right_eye", injury_type="cut"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertIsNotNone(out)
        # Pair-collapsed prose uses "both" or "their eyes" — assert the
        # line reads at plural register, not at per-side singular.
        self.assertNotIn("left eye", out.lower())
        self.assertNotIn("right eye", out.lower())
        # Pronoun was resolved.
        self.assertNotIn("{Their}", out)

    def test_both_ears_blunt_yields_pair_line(self):
        char = _char(gender="female")
        wounds = [
            _wound("left_ear", injury_type="blunt"),
            _wound("right_ear", injury_type="blunt"),
        ]
        out = get_paired_destroyed_description(
            char, "ears", "left_ear", "right_ear", wounds=wounds,
        )
        self.assertIsNotNone(out)
        self.assertNotIn("left ear", out.lower())
        self.assertNotIn("right ear", out.lower())


class CollapseRejectsMismatchedMechanism(TestCase):

    def test_eyes_split_mechanisms_returns_none(self):
        # Left eye cut, right eye shot — per-side rendering wins.
        char = _char()
        wounds = [
            _wound("left_eye", injury_type="cut"),
            _wound("right_eye", injury_type="bullet"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertIsNone(out)

    def test_one_eye_only_returns_none(self):
        # Only left eye destroyed; right intact.
        char = _char()
        wounds = [_wound("left_eye", injury_type="cut")]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertIsNone(out)

    def test_no_destroyed_wounds_returns_none(self):
        char = _char()
        wounds = [
            _wound("left_eye", injury_type="cut", stage="fresh"),
            _wound("right_eye", injury_type="cut", stage="fresh"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertIsNone(out)


class PronounSubstitution(TestCase):

    def test_male_renders_his(self):
        char = _char(gender="male")
        wounds = [
            _wound("left_eye", injury_type="cut"),
            _wound("right_eye", injury_type="cut"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        # "Their" → "His" (male possessive). _format_wound_grammar may
        # capitalise at the start, so check both forms.
        self.assertTrue("His" in out or "his" in out)

    def test_female_renders_her(self):
        char = _char(gender="female")
        wounds = [
            _wound("left_eye", injury_type="cut"),
            _wound("right_eye", injury_type="cut"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertTrue("Her" in out or "her" in out)


class GenericFallback(TestCase):
    """When the per-injury-type module lacks a pair overlay for a given
    pair key, the renderer falls through to the generic overlay."""

    def test_unknown_injury_type_falls_through_to_generic(self):
        # "harvested" module exists but has no DESTROYED_BY_PAIR.
        # Result: collapse fires using generic prose.
        char = _char()
        wounds = [
            _wound("left_eye", injury_type="harvested"),
            _wound("right_eye", injury_type="harvested"),
        ]
        out = get_paired_destroyed_description(
            char, "eyes", "left_eye", "right_eye", wounds=wounds,
        )
        self.assertIsNotNone(out)


class CorpsePathUsesWoundOverride(TestCase):
    """A corpse calls the helper with ``wounds=db.wounds_at_death`` so
    the preserved snapshot drives the collapse without a live medical
    state lookup."""

    def test_corpse_with_preserved_destroyed_wounds(self):
        # Simulate a corpse: same shape as a character but the wounds
        # arrive via the explicit ``wounds`` parameter rather than
        # ``get_character_wounds``.
        corpse = _char(species="human")
        snapshot = [
            _wound("left_ear", injury_type="cut"),
            _wound("right_ear", injury_type="cut"),
        ]
        out = get_paired_destroyed_description(
            corpse, "ears", "left_ear", "right_ear", wounds=snapshot,
        )
        self.assertIsNotNone(out)
        self.assertNotIn("{", out, "leaked brace in corpse pair line")


class VariantRendering(TestCase):
    """Every variant in every overlay cell must render without leaking
    braces or raising."""

    def test_every_variant_renders_clean(self):
        import random
        char = _char()
        wounds = [
            _wound("left_eye", injury_type="cut"),
            _wound("right_eye", injury_type="cut"),
        ]
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            for pair_key, variants in module.DESTROYED_BY_PAIR.items():
                left = f"left_{pair_key[:-1] if pair_key.endswith('s') else pair_key}"
                right = f"right_{pair_key[:-1] if pair_key.endswith('s') else pair_key}"
                for variant in variants:
                    with self.subTest(itype=itype, pair_key=pair_key):
                        original = random.choice
                        random.choice = lambda seq, _v=variant: _v
                        try:
                            out = get_paired_destroyed_description(
                                char, pair_key, left, right,
                                wounds=[
                                    _wound(left, injury_type=itype),
                                    _wound(right, injury_type=itype),
                                ],
                            )
                        finally:
                            random.choice = original
                        self.assertTrue(out)
                        self.assertNotIn("{", out, f"leaked brace in {out!r}")
                        self.assertNotIn("}", out)
