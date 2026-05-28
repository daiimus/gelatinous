"""Unit tests for :class:`typeclasses.items.SeveredHead` (PR #194).

The SeveredHead super-item carries identity / decay / trimmed
snapshot state forward from the source corpse so PR-C's widened
autopsy and harvest gates can treat it as a forensic peer of the
corpse.  These tests lock the sever-time overlay contract and the
decay surface without spinning up a full Evennia typeclass instance.

The overlay body lives in :func:`typeclasses.items.apply_severed_head_overlay`
(a module-level helper) so the test can drive it against a plain stub
``self``; the ``SeveredHead.configure_from_sever`` method is a thin
wrapper that chains ``super().configure_from_sever`` then delegates
to that helper.  Decay-stage methods are class-attribute lookups
plus pure arithmetic, so they're exercised via
``SeveredHead.<method>.__func__(stub)`` calls where ``stub`` owns the
required ``db`` shape plus a borrowed ``_DECAY_STAGES`` class attribute.

Run via::

    evennia test world.tests.test_severed_head
"""

from __future__ import annotations

import time
from unittest import TestCase

from typeclasses.items import SeveredHead, apply_severed_head_overlay


class _DB:
    pass


class _FakeHead:
    """Stub stand-in for a ``SeveredHead`` instance.

    Carries the ``db`` shape and the borrowed ``_DECAY_STAGES`` class
    attribute that the unbound decay methods need.  ``configure_from_sever``
    is intentionally absent — overlay tests drive
    :func:`apply_severed_head_overlay` directly.
    """

    _DECAY_STAGES = SeveredHead._DECAY_STAGES
    # Bind the unbound function so ``self.get_decay_stage()`` works
    # (needed because ``_decay_display_name`` does a bound call).
    get_decay_stage = SeveredHead.get_decay_stage

    def __init__(self):
        self.db = _DB()
        self.db.creation_time = time.time()
        self.db.death_time = time.time()
        self.db.death_cause = "unknown"
        self.db.medical_state_at_death = None
        self.db.removed_organs = []
        self.db.signature_at_death = None
        self.db.apparent_uid_at_death = None
        # PR-G: species drives decay-aware naming via the anatomy
        # registry; stub defaults to human to match production behaviour.
        self.db.source_species = "human"


class _FakeCorpse:
    def __init__(
        self,
        *,
        signature=("sleeve-9", "tall", "lean", "hooded", ("balaclava",)),
        apparent_uid="hash-xyz",
        creation_time=None,
        death_time=None,
        death_cause="gunshot",
        snapshot=None,
        removed_organs=None,
        dbref="#777",
    ):
        self.dbref = dbref
        self.db = _DB()
        self.db.signature_at_death = signature
        self.db.apparent_uid_at_death = apparent_uid
        self.db.creation_time = creation_time or (time.time() - 100)
        self.db.death_time = death_time or self.db.creation_time
        self.db.death_cause = death_cause
        self.db.medical_state_at_death = snapshot
        self.db.removed_organs = list(removed_organs or ())

    def get_medical_snapshot(self):
        return self.db.medical_state_at_death


def _full_snapshot():
    def org(hp, container):
        return {"current_hp": hp, "max_hp": hp, "container": container}
    return {
        "organs": {
            "brain": org(10, "head"),
            "left_eye": org(10, "head"),
            "right_eye": org(10, "head"),
            "heart": org(15, "chest"),
            "liver": org(20, "abdomen"),
            "left_humerus": org(25, "left_arm"),
        },
        "conditions": ["shock"],
        "blood_level": 3500,
        "pain_level": 9,
        "consciousness": False,
    }


class SeveredHeadOverlayTests(TestCase):
    """Drive :func:`apply_severed_head_overlay` against a stub head."""

    def setUp(self):
        self.head = _FakeHead()
        self.corpse = _FakeCorpse(snapshot=_full_snapshot())

    def _overlay(self):
        apply_severed_head_overlay(self.head, self.corpse)

    def test_identity_snapshot_copied(self):
        self._overlay()
        self.assertEqual(
            self.head.db.signature_at_death,
            self.corpse.db.signature_at_death,
        )
        self.assertEqual(
            self.head.db.apparent_uid_at_death,
            self.corpse.db.apparent_uid_at_death,
        )

    def test_decay_clock_shared_with_corpse(self):
        self._overlay()
        self.assertEqual(
            self.head.db.creation_time, self.corpse.db.creation_time
        )
        self.assertEqual(
            self.head.db.death_time, self.corpse.db.death_time
        )
        self.assertEqual(
            self.head.db.death_cause, self.corpse.db.death_cause
        )

    def test_trimmed_snapshot_filters_to_head_container(self):
        self._overlay()
        organs = self.head.db.medical_state_at_death["organs"]
        self.assertEqual(
            set(organs.keys()), {"brain", "left_eye", "right_eye"}
        )

    def test_trimmed_snapshot_blanks_body_wide_fields(self):
        self._overlay()
        snap = self.head.db.medical_state_at_death
        self.assertEqual(snap["conditions"], [])
        self.assertIsNone(snap["blood_level"])
        self.assertIsNone(snap["pain_level"])
        self.assertIsNone(snap["consciousness"])

    def test_removed_organs_carries_head_subset_only(self):
        self.corpse.db.removed_organs = ["left_eye", "heart"]
        self._overlay()
        self.assertEqual(self.head.db.removed_organs, ["left_eye"])

    def test_snapshot_organs_are_independent_copies(self):
        """Mutating the head's snapshot must not bleed into the corpse."""
        self._overlay()
        self.head.db.medical_state_at_death["organs"]["brain"][
            "current_hp"
        ] = 0
        self.assertEqual(
            self.corpse.db.medical_state_at_death["organs"]["brain"][
                "current_hp"
            ],
            10,
        )

    def test_no_corpse_snapshot_yields_empty_organs(self):
        self.corpse.db.medical_state_at_death = None
        self._overlay()
        snap = self.head.db.medical_state_at_death
        self.assertEqual(snap["organs"], {})

    def test_get_medical_snapshot_returns_trimmed_dict(self):
        """The accessor is a thin ``self.db.medical_state_at_death`` read."""
        self._overlay()
        result = SeveredHead.get_medical_snapshot(self.head)
        self.assertIs(result, self.head.db.medical_state_at_death)

    def test_non_head_organs_excluded_even_if_missing_container(self):
        """Organs with no ``container`` key are excluded (defensive)."""
        snapshot = _full_snapshot()
        snapshot["organs"]["mystery_organ"] = {"current_hp": 1, "max_hp": 1}
        self.corpse.db.medical_state_at_death = snapshot
        self._overlay()
        organs = self.head.db.medical_state_at_death["organs"]
        self.assertNotIn("mystery_organ", organs)

    def test_overlay_preserves_corpse_snapshot_keys(self):
        """Sanity: the overlay shouldn't mutate the corpse snapshot dict."""
        original_keys = set(
            self.corpse.db.medical_state_at_death["organs"].keys()
        )
        self._overlay()
        self.assertEqual(
            set(self.corpse.db.medical_state_at_death["organs"].keys()),
            original_keys,
        )


class SeveredHeadDecayContractTests(TestCase):
    """Spot-check the decay surface used by IdentityBearerMixin."""

    def _make_head_at_age(self, age_seconds):
        head = _FakeHead()
        head.db.creation_time = time.time() - age_seconds
        return head

    def test_fresh_under_hour(self):
        head = self._make_head_at_age(60)
        self.assertEqual(SeveredHead.get_decay_stage(head), "fresh")

    def test_early_under_day(self):
        head = self._make_head_at_age(7200)
        self.assertEqual(SeveredHead.get_decay_stage(head), "early")

    def test_skeletal_after_advanced_threshold(self):
        # 604800s = advanced cap; bump past it.
        head = self._make_head_at_age(604800 + 10)
        self.assertEqual(SeveredHead.get_decay_stage(head), "skeletal")

    def test_decay_display_name_per_stage(self):
        head = self._make_head_at_age(60)
        self.assertEqual(
            SeveredHead._decay_display_name(head), "human head"
        )
        head.db.creation_time = time.time() - (604800 + 10)
        self.assertEqual(SeveredHead._decay_display_name(head), "skeletal head")

    def test_get_worn_items_is_empty(self):
        head = _FakeHead()
        self.assertEqual(SeveredHead.get_worn_items(head), [])
        self.assertEqual(
            SeveredHead.get_worn_items(head, location="head"), []
        )
