"""Tests for nose / jaw / tongue destruction → face longdesc surface
(issue #355).

After #346 routed wounds at the organ's ``display_location``, and
after #347 added per-injury-type destroyed-stage overlays, this
issue closes the authoring gap for face-surface organs: nose, jaw,
and tongue all surface their destruction at the ``face`` longdesc
line via the ``{organ}`` token in shared face templates.

Tests verify:

* Human declares nose / jaw / tongue with ``display_location: \"face\"``.
* Each shipped injury-type module declares a ``face`` entry in
  ``DESTROYED_BY_LOCATION`` with at least 3 variants.
* Templates use ``{organ}`` so each organ's destruction renders with
  its own name.
* A destroyed-jaw wound at the face surface picks the face overlay,
  not the generic destroyed limb prose.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.anatomy import get_organ_spec
from world.medical.wounds import messages
from world.medical.wounds.wound_descriptions import get_wound_description


FACE_ORGANS = ("nose", "jaw", "tongue")
INJURY_TYPES_WITH_OVERLAY = (
    "cut", "stab", "bullet", "blunt", "laceration", "generic",
)


def _char(gender="male"):
    return SimpleNamespace(
        gender=gender,
        db=SimpleNamespace(
            original_gender=gender,
            species="human",
            skintone=None,
        ),
    )


class FaceOrgansRouteToFaceSurface(TestCase):

    def test_nose_display_location_is_face(self):
        spec = get_organ_spec("nose", "human")
        self.assertEqual(spec.get("display_location"), "face")
        self.assertEqual(spec.get("container"), "head")

    def test_jaw_display_location_is_face(self):
        spec = get_organ_spec("jaw", "human")
        self.assertEqual(spec.get("display_location"), "face")

    def test_tongue_display_location_is_face(self):
        spec = get_organ_spec("tongue", "human")
        self.assertEqual(spec.get("display_location"), "face")


class FaceOverlayDeclaredOnEveryModule(TestCase):

    def test_every_module_declares_face_overlay(self):
        for itype in INJURY_TYPES_WITH_OVERLAY:
            with self.subTest(itype=itype):
                module = getattr(messages, itype)
                overlay = getattr(module, "DESTROYED_BY_LOCATION", {})
                self.assertIn("face", overlay,
                              f"{itype}.py needs a face entry")
                self.assertGreaterEqual(
                    len(overlay["face"]), 3,
                    f"{itype}.face needs at least 3 variants",
                )

    def test_face_templates_use_organ_token(self):
        # Each face template should use {organ} so the rendered prose
        # names which specific face-surface organ was destroyed.
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            overlay = module.DESTROYED_BY_LOCATION
            for variant in overlay["face"]:
                with self.subTest(itype=itype):
                    self.assertIn(
                        "{organ}", variant,
                        f"{itype}.face variant missing {{organ}}: {variant!r}",
                    )


class DestructionRenderingByOrgan(TestCase):
    """A destroyed-jaw wound at the face location should render with
    'jaw' in the prose; a destroyed-nose wound at face should render
    with 'nose'.  Same template, different organ token."""

    def test_destroyed_jaw_renders_jaw_at_face(self):
        out = get_wound_description(
            injury_type="cut", location="face",
            severity="Critical", stage="destroyed",
            organ="jaw", character=_char(),
        )
        self.assertIn("jaw", out.lower())
        # And uses the face template family, not the limb one.
        self.assertNotIn("ribbons of flesh", out)
        self.assertNotIn("hanging by threads", out)

    def test_destroyed_nose_renders_nose_at_face(self):
        out = get_wound_description(
            injury_type="bullet", location="face",
            severity="Critical", stage="destroyed",
            organ="nose", character=_char(),
        )
        self.assertIn("nose", out.lower())
        self.assertNotIn("ribbons of flesh", out)

    def test_destroyed_tongue_renders_tongue_at_face(self):
        out = get_wound_description(
            injury_type="laceration", location="face",
            severity="Critical", stage="destroyed",
            organ="tongue", character=_char(),
        )
        self.assertIn("tongue", out.lower())


class FaceVariantsRenderWithoutLeakedBraces(TestCase):

    def test_every_face_variant_renders_clean(self):
        import random
        char = _char()
        for itype in INJURY_TYPES_WITH_OVERLAY:
            module = getattr(messages, itype)
            for variant in module.DESTROYED_BY_LOCATION["face"]:
                for organ in FACE_ORGANS:
                    with self.subTest(itype=itype, organ=organ):
                        original = random.choice
                        random.choice = lambda seq, _v=variant: _v
                        try:
                            out = get_wound_description(
                                injury_type=itype,
                                location="face",
                                severity="Critical",
                                stage="destroyed",
                                organ=organ,
                                character=char,
                            )
                        finally:
                            random.choice = original
                        self.assertTrue(out)
                        self.assertNotIn("{", out,
                                         f"leaked brace in {out!r}")
                        self.assertNotIn("}", out)
                        self.assertIn(organ, out.lower())
