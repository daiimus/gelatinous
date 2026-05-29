"""Unit tests for the PR #198 wound + longdesc carry-forward overlay.

Two module-level helpers in :mod:`typeclasses.items` are exercised:

* :func:`apply_wound_and_longdesc_overlay` — copies a corpse's
  wound records and longdesc prose for a given set of body locations
  onto a severed item (Appendage or SeveredHead).
* :func:`apply_sever_to_corpse` — symmetric counterpart: clears the
  same prose off the corpse and synthesizes a ``severed``-type stump
  wound at the canonical severed location.  Handles the head-cluster
  fan-out (``head`` sever also clears face / neck / eyes / ears).

Both helpers are pure: they operate on the duck-typed ``db`` surface
and are independently testable against plain-Python stubs without
instantiating an Evennia typeclass.

Run via::

    evennia test world.tests.test_sever_overlay
"""

from __future__ import annotations

from unittest import TestCase

from typeclasses.items import (
    apply_sever_to_corpse,
    apply_wound_and_longdesc_overlay,
)
from world.combat.constants import SEVERED_HEAD_LOCATIONS


class _DB:
    """Bare attribute container — matches Evennia ``obj.db`` surface."""


class _FakeAppendage:
    def __init__(self):
        self.db = _DB()
        self.db.wounds_at_death = []
        self.db.longdesc_data = {}


class _FakeCorpse:
    def __init__(self, *, wounds=None, longdescs=None):
        self.db = _DB()
        self.db.wounds_at_death = list(wounds or [])
        self.db.longdesc_data = dict(longdescs or {})


def _wound(location, injury_type="bullet", severity="Severe"):
    """Build a wound dict matching the death_progression snapshot shape."""
    return {
        "injury_type": injury_type,
        "location": location,
        "severity": severity,
        "stage": "old",
        "organ": None,
        "organ_damage": {
            "current_hp": 0, "max_hp": 10, "container": location,
        },
    }


# ---------------------------------------------------------------------
# apply_wound_and_longdesc_overlay
# ---------------------------------------------------------------------


class ApplyWoundAndLongdescOverlayTests(TestCase):
    """Pure-copy overlay: corpse → severed item, no source mutation."""

    def test_single_location_wounds_copied(self):
        corpse = _FakeCorpse(wounds=[
            _wound("left_arm"),
            _wound("chest"),
            _wound("left_arm", injury_type="cut"),
        ])
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        locations = [w["location"] for w in appendage.db.wounds_at_death]
        self.assertEqual(locations, ["left_arm", "left_arm"])
        injury_types = [w["injury_type"] for w in appendage.db.wounds_at_death]
        self.assertEqual(injury_types, ["bullet", "cut"])

    def test_single_location_longdesc_copied(self):
        corpse = _FakeCorpse(longdescs={
            "left_arm": "a pale, freckled forearm",
            "chest": "a broad chest with old burn scars",
        })
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        self.assertEqual(
            appendage.db.longdesc_data,
            {"left_arm": "a pale, freckled forearm"},
        )

    def test_head_cluster_locations_all_copied(self):
        corpse = _FakeCorpse(
            wounds=[
                _wound("head"),
                _wound("face"),
                _wound("left_eye"),
                _wound("chest"),  # should NOT carry
            ],
            longdescs={
                "head": "a shaven scalp",
                "face": "sharp angular features",
                "neck": "a thick muscular neck",
                "left_eye": "a milky, blind left eye",
                "chest": "a broad chest",  # should NOT carry
            },
        )
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(
            appendage, corpse, SEVERED_HEAD_LOCATIONS,
        )
        wound_locs = {w["location"] for w in appendage.db.wounds_at_death}
        self.assertEqual(wound_locs, {"head", "face", "left_eye"})
        self.assertEqual(
            set(appendage.db.longdesc_data.keys()),
            {"head", "face", "neck", "left_eye"},
        )

    def test_hair_rides_head_cluster(self):
        # Issue #236: hair frames the head and must follow it on sever.
        corpse = _FakeCorpse(
            wounds=[_wound("hair", injury_type="cut")],
            longdescs={
                "hair": "long silver braids bound with copper wire",
                "chest": "a broad chest",  # should NOT carry
            },
        )
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(
            appendage, corpse, SEVERED_HEAD_LOCATIONS,
        )
        self.assertIn("hair", appendage.db.longdesc_data)
        self.assertEqual(
            appendage.db.longdesc_data["hair"],
            "long silver braids bound with copper wire",
        )
        self.assertEqual(
            {w["location"] for w in appendage.db.wounds_at_death}, {"hair"}
        )

    def test_empty_corpse_state_yields_empty_appendage_state(self):
        corpse = _FakeCorpse()
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        self.assertEqual(appendage.db.wounds_at_death, [])
        self.assertEqual(appendage.db.longdesc_data, {})

    def test_wound_dicts_are_independent_copies(self):
        wound = _wound("left_arm")
        corpse = _FakeCorpse(wounds=[wound])
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        appendage.db.wounds_at_death[0]["severity"] = "MUTATED"
        # Original corpse wound dict must not have been mutated.
        self.assertEqual(corpse.db.wounds_at_death[0]["severity"], "Severe")

    def test_none_db_collections_treated_as_empty(self):
        corpse = _FakeCorpse()
        corpse.db.wounds_at_death = None
        corpse.db.longdesc_data = None
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        self.assertEqual(appendage.db.wounds_at_death, [])
        self.assertEqual(appendage.db.longdesc_data, {})


# ---------------------------------------------------------------------
# apply_sever_to_corpse
# ---------------------------------------------------------------------


class ApplySeverToCorpseTests(TestCase):
    """Symmetric corpse-side mutation after a successful sever."""

    def test_limb_sever_drops_location_longdesc(self):
        corpse = _FakeCorpse(longdescs={
            "left_arm": "a pale arm",
            "chest": "a broad chest",
        })
        apply_sever_to_corpse(corpse, "left_arm")
        self.assertNotIn("left_arm", corpse.db.longdesc_data)
        self.assertIn("chest", corpse.db.longdesc_data)

    def test_limb_sever_drops_location_wounds(self):
        corpse = _FakeCorpse(wounds=[
            _wound("left_arm"),
            _wound("chest"),
        ])
        apply_sever_to_corpse(corpse, "left_arm")
        locations = [w["location"] for w in corpse.db.wounds_at_death]
        # Original left_arm wound gone; chest survives; one new
        # synthesized severed-stump wound at left_arm appended.
        self.assertEqual(locations.count("left_arm"), 1)
        self.assertIn("chest", locations)
        stump = next(
            w for w in corpse.db.wounds_at_death
            if w["location"] == "left_arm"
        )
        self.assertEqual(stump["injury_type"], "severed")

    def test_limb_sever_appends_single_stump_wound(self):
        corpse = _FakeCorpse()
        apply_sever_to_corpse(corpse, "right_thigh")
        stumps = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "severed"
        ]
        self.assertEqual(len(stumps), 1)
        self.assertEqual(stumps[0]["location"], "right_thigh")
        self.assertEqual(stumps[0]["severity"], "Critical")

    def test_head_sever_clears_full_cluster_longdescs(self):
        corpse = _FakeCorpse(longdescs={
            "hair": "long silver braids",
            "head": "a shaven scalp",
            "face": "sharp features",
            "neck": "a thick neck",
            "left_eye": "a milky eye",
            "right_eye": "a clear eye",
            "left_ear": "a torn ear",
            "right_ear": "a normal ear",
            "chest": "a broad chest",  # survives
        })
        apply_sever_to_corpse(corpse, "head")
        self.assertEqual(set(corpse.db.longdesc_data.keys()), {"chest"})

    def test_head_sever_clears_full_cluster_wounds(self):
        corpse = _FakeCorpse(wounds=[
            _wound("head"),
            _wound("face"),
            _wound("left_eye"),
            _wound("neck"),
            _wound("chest"),  # survives
        ])
        apply_sever_to_corpse(corpse, "head")
        # All head-cluster wounds removed; chest survives; ONE
        # synthesized stump wound at "head".
        remaining_originals = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] != "severed"
        ]
        self.assertEqual(
            [w["location"] for w in remaining_originals], ["chest"]
        )
        stumps = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "severed"
        ]
        self.assertEqual(len(stumps), 1)
        self.assertEqual(stumps[0]["location"], "head")

    def test_head_locations_override_accepted(self):
        """Test injection: caller can pass a custom head-cluster set."""
        corpse = _FakeCorpse(longdescs={"head": "a head", "face": "a face"})
        apply_sever_to_corpse(
            corpse, "head", head_locations=frozenset({"head"}),
        )
        # Only "head" cleared, "face" survives.
        self.assertNotIn("head", corpse.db.longdesc_data)
        self.assertIn("face", corpse.db.longdesc_data)

    def test_stump_wound_has_organ_damage_block(self):
        """Forensic shape — autopsy code may read organ_damage defensively."""
        corpse = _FakeCorpse()
        apply_sever_to_corpse(corpse, "left_hand")
        stump = corpse.db.wounds_at_death[-1]
        self.assertEqual(stump["organ_damage"]["container"], "left_hand")
        self.assertEqual(stump["organ_damage"]["current_hp"], 0)

    def test_none_db_collections_handled(self):
        corpse = _FakeCorpse()
        corpse.db.wounds_at_death = None
        corpse.db.longdesc_data = None
        apply_sever_to_corpse(corpse, "left_arm")
        # No crash; stump wound was still appended.
        self.assertEqual(len(corpse.db.wounds_at_death), 1)
        self.assertEqual(
            corpse.db.wounds_at_death[0]["injury_type"], "severed",
        )


# ---------------------------------------------------------------------
# PR-F (#200) — harvested-organ wound carry-forward via PR-D overlay
# ---------------------------------------------------------------------


def _harvested_wound(location, organ):
    """Build a harvested wound dict shaped like CmdHarvest synthesizes."""
    return {
        "injury_type": "harvested",
        "location": location,
        "severity": "Critical",
        "stage": "old",
        "organ": organ,
        "organ_damage": {
            "current_hp": 0, "max_hp": 0, "container": location,
        },
    }


class HarvestedWoundCarryForwardTests(TestCase):
    """Integration: harvested wounds piggyback PR-D's existing overlay.

    The contract verified here is that ``CmdHarvest`` synthesizes
    wounds at the organ's *container* location (PR-F design), so the
    pre-existing PR-D ``apply_wound_and_longdesc_overlay`` and
    ``apply_sever_to_corpse`` helpers move them correctly without
    any harvest-specific code in the overlay layer.
    """

    def test_harvested_hand_wound_moves_to_severed_right_hand(self):
        """harvest right metacarpals → sever right hand → wound rides along."""
        corpse = _FakeCorpse(wounds=[
            _harvested_wound("right_hand", "right_metacarpals"),
            _wound("chest"),  # unrelated
        ])
        appendage = _FakeAppendage()
        # Simulate the configure_from_sever overlay call.
        apply_wound_and_longdesc_overlay(appendage, corpse, ("right_hand",))
        # Then simulate the corpse-side mutation.
        apply_sever_to_corpse(corpse, "right_hand")

        # Severed item carries the harvested wound.
        appendage_wounds = appendage.db.wounds_at_death
        self.assertEqual(len(appendage_wounds), 1)
        self.assertEqual(appendage_wounds[0]["injury_type"], "harvested")
        self.assertEqual(appendage_wounds[0]["organ"], "right_metacarpals")

        # Corpse no longer carries it (moved, not copied).
        corpse_harvested = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "harvested"
        ]
        self.assertEqual(corpse_harvested, [])
        # Stump wound now exists at right_hand on the corpse.
        stumps = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "severed" and w["location"] == "right_hand"
        ]
        self.assertEqual(len(stumps), 1)
        # Unrelated chest wound survives.
        chest_wounds = [
            w for w in corpse.db.wounds_at_death if w["location"] == "chest"
        ]
        self.assertEqual(len(chest_wounds), 1)

    def test_harvested_eye_wound_moves_with_head_cluster(self):
        """harvest left eye → sever head → harvested wound rides cluster."""
        corpse = _FakeCorpse(wounds=[
            _harvested_wound("head", "left_eye"),
            _wound("abdomen"),  # unrelated, unseverable container
        ])
        head_item = _FakeAppendage()
        apply_wound_and_longdesc_overlay(
            head_item, corpse, SEVERED_HEAD_LOCATIONS,
        )
        apply_sever_to_corpse(corpse, "head")

        # Severed head carries the harvested-eye wound.
        head_wounds = head_item.db.wounds_at_death
        harvested = [
            w for w in head_wounds if w["injury_type"] == "harvested"
        ]
        self.assertEqual(len(harvested), 1)
        self.assertEqual(harvested[0]["organ"], "left_eye")

        # Corpse no longer carries the harvested-eye wound.
        corpse_harvested = [
            w for w in corpse.db.wounds_at_death
            if w["injury_type"] == "harvested"
        ]
        self.assertEqual(corpse_harvested, [])
        # Abdomen wound (unseverable container) survives on corpse.
        abd_wounds = [
            w for w in corpse.db.wounds_at_death if w["location"] == "abdomen"
        ]
        self.assertEqual(len(abd_wounds), 1)

    def test_harvested_torso_wound_stays_on_corpse_after_limb_sever(self):
        """A harvested-liver wound at abdomen survives a left-arm sever.

        Demonstrates the design intent: wounds at unseverable
        containers (chest / abdomen / back) remain on the corpse
        permanently — limb severs only move wounds whose location
        matches the severed location.
        """
        corpse = _FakeCorpse(wounds=[
            _harvested_wound("abdomen", "liver"),
            _wound("left_arm"),
        ])
        appendage = _FakeAppendage()
        apply_wound_and_longdesc_overlay(appendage, corpse, ("left_arm",))
        apply_sever_to_corpse(corpse, "left_arm")

        # Severed left arm has only the left_arm bullet wound, no liver.
        appendage_organs = [
            w.get("organ") for w in appendage.db.wounds_at_death
        ]
        self.assertNotIn("liver", appendage_organs)
        # Corpse still has the harvested-liver wound at abdomen.
        liver_wounds = [
            w for w in corpse.db.wounds_at_death
            if w.get("organ") == "liver"
        ]
        self.assertEqual(len(liver_wounds), 1)
        self.assertEqual(liver_wounds[0]["location"], "abdomen")
