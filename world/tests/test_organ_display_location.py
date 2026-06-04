"""Tests for the organ ``display_location`` routing (issue #346).

Pre-fix, ``get_character_wounds`` filed every wound at ``organ.container``.
Sensory organs (``left_eye``, ``right_eye``, ``left_ear``, ``right_ear``)
have ``container = "head"``, which has no authored longdesc surface in
the human anatomy registry — so destruction at those organs went
visually nowhere. The fix routes wounds through ``organ.display_location``
(defaulting to ``container`` when absent), so eye / ear destruction
surfaces at the right anatomical line while limb / torso wounds keep
filing under their bulk container.

Coverage gates (visibility) still consult the bulk container — clothing
covers the head bulk, so eye wounds hide behind a hood the same way.

Run via::

    evennia test world.tests.test_organ_display_location
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.core import Organ
from world.medical.constants import ORGANS
from world.medical.wounds import get_character_wounds


class OrganDisplayLocationFieldTests(TestCase):
    """The Organ class exposes display_location read from the spec."""

    def test_sensory_organs_declare_display_location(self):
        for name in ("left_eye", "right_eye", "left_ear", "right_ear"):
            with self.subTest(name=name):
                organ = Organ(name)
                self.assertEqual(organ.display_location, name)
                # Sensory organs still belong to the head container —
                # the display_location is a routing override, not a
                # relocation.
                self.assertEqual(organ.container, "head")

    def test_internal_organs_fall_back_to_container(self):
        # Heart, lungs, liver, brain etc. have no display_location
        # override; they should default to their container.
        for name in ("heart", "left_lung", "liver", "brain"):
            with self.subTest(name=name):
                organ = Organ(name)
                self.assertEqual(organ.display_location, organ.container)

    def test_round_trip_through_dict(self):
        # to_dict / from_dict preserves the display_location field.
        organ = Organ("left_eye")
        organ.current_hp = 0
        organ.wound_stage = "destroyed"
        organ.injury_type = "cut"
        snap = organ.to_dict()
        self.assertEqual(snap["display_location"], "left_eye")

        restored = Organ.from_dict(snap)
        self.assertEqual(restored.display_location, "left_eye")

    def test_legacy_snapshot_without_display_location_uses_spec(self):
        # Snapshots written before this PR don't carry display_location;
        # the from_dict path must fall back to the spec default rather
        # than leaving the field as the container.
        snap = {
            "name": "left_eye",
            "current_hp": 0,
            "max_hp": 10,
            "conditions": [],
            "wound_stage": "destroyed",
            "injury_type": "cut",
            "wound_timestamp": None,
            # display_location intentionally absent
        }
        restored = Organ.from_dict(snap)
        self.assertEqual(restored.display_location, "left_eye")


class OrgansRegistryShape(TestCase):
    """The ORGANS constants table declares display_location for sensory
    organs but leaves it absent for internal / limb organs."""

    def test_sensory_organs_have_display_location(self):
        for name in ("left_eye", "right_eye", "left_ear", "right_ear"):
            with self.subTest(name=name):
                self.assertIn("display_location", ORGANS[name])
                self.assertEqual(
                    ORGANS[name]["display_location"], name,
                    f"{name} should route to its own longdesc surface",
                )

    def test_non_sensory_organs_absent_or_match_container(self):
        # Heart / liver / brain / etc. either have no display_location
        # override or it matches the container — both produce the
        # correct fallback behavior.
        for name in ("brain", "heart", "liver", "left_humerus"):
            with self.subTest(name=name):
                spec = ORGANS[name]
                override = spec.get("display_location")
                if override is not None:
                    self.assertEqual(override, spec["container"])


# ---------------------------------------------------------------------
# get_character_wounds routing
# ---------------------------------------------------------------------


class _FakeMedicalState:
    def __init__(self, organs):
        self.organs = organs


class _FakeCharacter:
    """Minimal stand-in for the wound-rendering pipeline."""

    def __init__(self, organs, *, covered_locations=None):
        self.medical_state = _FakeMedicalState(organs)
        self._covered = set(covered_locations or ())
        self.db = SimpleNamespace(species="human", skintone=None)

    def is_location_covered(self, location):
        return location in self._covered


def _damaged(name, *, current_hp=0, wound_stage="destroyed",
             injury_type="cut"):
    organ = Organ(name)
    organ.current_hp = current_hp
    organ.wound_stage = wound_stage
    organ.injury_type = injury_type
    return organ


class GetCharacterWoundsRoutingTests(TestCase):
    """Wounds file at organ.display_location, not container."""

    def test_destroyed_eye_files_at_eye_not_head(self):
        organs = {"left_eye": _damaged("left_eye")}
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        self.assertEqual(len(wounds), 1)
        self.assertEqual(wounds[0]["location"], "left_eye")
        self.assertEqual(wounds[0]["organ"], "left_eye")

    def test_destroyed_ear_files_at_ear_not_head(self):
        organs = {"right_ear": _damaged("right_ear")}
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        self.assertEqual(wounds[0]["location"], "right_ear")

    def test_destroyed_heart_still_files_at_chest(self):
        # Negative control: organs WITHOUT a display_location override
        # continue to file at their container exactly as before.
        organs = {"heart": _damaged("heart")}
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        self.assertEqual(wounds[0]["location"], "chest")

    def test_destroyed_brain_still_files_at_head(self):
        # Brain has no specific longdesc surface — destruction stays
        # filed under "head" (and the longdesc renderer's head
        # surfaces show nothing, which is correct: a destroyed brain
        # has no external longdesc signature).
        organs = {"brain": _damaged("brain")}
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        self.assertEqual(wounds[0]["location"], "head")

    def test_destroyed_limb_files_at_limb(self):
        # Limb organ (humerus) — container IS the longdesc surface, so
        # no routing change; the wound files at "left_arm" as before.
        organs = {"left_humerus": _damaged("left_humerus")}
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        self.assertEqual(wounds[0]["location"], "left_arm")

    def test_multiple_destroyed_organs_one_container_split_by_surface(self):
        # Both eyes + brain destroyed: brain stays at "head", eyes split
        # to their respective surfaces. Three wounds, three distinct
        # locations.
        organs = {
            "brain": _damaged("brain"),
            "left_eye": _damaged("left_eye"),
            "right_eye": _damaged("right_eye"),
        }
        char = _FakeCharacter(organs)
        wounds = get_character_wounds(char)
        locations = sorted(w["location"] for w in wounds)
        self.assertEqual(locations, ["head", "left_eye", "right_eye"])


class CoverageGateUsesContainer(TestCase):
    """Visibility check consults the bulk container, not the display
    surface — clothing covers the head bulk, so an eye wound is hidden
    by a hood the same way a brain wound would be (issue #346
    explicitly preserves this routing)."""

    def test_eye_wound_hidden_when_head_covered(self):
        organs = {"left_eye": _damaged("left_eye")}

        bare = _FakeCharacter(organs)
        self.assertEqual(len(get_character_wounds(bare)), 1)

        # Coverage at the bulk container ("head") hides the eye wound
        # even though its display surface is "left_eye". This is the
        # invariant: visibility consults container, location consults
        # display surface.
        covered = _FakeCharacter(organs, covered_locations=("head",))
        self.assertEqual(len(get_character_wounds(covered)), 0)

    def test_eye_wound_shows_when_only_eye_surface_covered(self):
        # Inverse: covering "left_eye" alone (e.g., an eyepatch
        # registered as covering only that display surface) does NOT
        # hide the wound, because visibility checks the container.
        # This is intentional — the existing clothing system covers
        # by container, and #346 preserves that semantics.
        organs = {"left_eye": _damaged("left_eye")}
        covered = _FakeCharacter(organs, covered_locations=("left_eye",))
        # Container "head" is not in the covered set → wound visible.
        self.assertEqual(len(get_character_wounds(covered)), 1)
