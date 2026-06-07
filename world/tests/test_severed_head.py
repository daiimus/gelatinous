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
        # PR #208: face-side body identity; populated by overlay.
        self.db.sleeve_uid = None
        # PR-G: species drives decay-aware naming via the anatomy
        # registry; stub defaults to human to match production behaviour.
        self.db.source_species = "human"


class _FakeCorpse:
    def __init__(
        self,
        *,
        signature=("sleeve-9", "tall", "lean", "hooded", ("balaclava",)),
        apparent_uid="hash-xyz",
        sleeve_uid="sleeve-9",
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
        # PR #208: source face-side identity for sever-head propagation.
        self.db.sleeve_uid = sleeve_uid
        # PR #208: overlay sets ``head_severed = True`` on the corpse;
        # tests can assert against this.
        self.db.head_severed = False
        self.db.creation_time = creation_time or (time.time() - 100)
        self.db.death_time = death_time or self.db.creation_time
        self.db.death_cause = death_cause
        self.db.medical_state_at_death = snapshot
        self.db.removed_organs = list(removed_organs or ())
        # For ``apply_sever_to_corpse`` invocation in propagation tests.
        self.db.longdesc_data = {}
        self.db.wounds_at_death = []

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

    # Trimmed-snapshot / removed_organs assertions moved out of this
    # file when ``apply_severed_head_overlay`` stopped writing the
    # snapshot itself (the base ``Appendage.configure_from_sever`` now
    # owns that via ``apply_organ_snapshot_overlay`` with chain=("head",)).
    # Equivalent coverage lives in ``test_sever_overlay.py``'s
    # ``ApplyOrganSnapshotOverlayTests`` — container filter, blanked
    # body-wide fields, ``None`` source handling, shallow-copy
    # independence, and removed_organs filtering all pinned there
    # against the helper that actually writes the snapshot now.

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


# ---------------------------------------------------------------------
# PR #208 — sleeve_uid propagation + head_severed flag
# ---------------------------------------------------------------------


class SeveredHeadIdentityPropagationTests(TestCase):
    """Overlay copies ``sleeve_uid`` and marks the corpse headless."""

    def setUp(self):
        self.head = _FakeHead()
        self.corpse = _FakeCorpse(snapshot=_full_snapshot())

    def test_sleeve_uid_copied_to_head(self):
        apply_severed_head_overlay(self.head, self.corpse)
        self.assertEqual(self.head.db.sleeve_uid, self.corpse.db.sleeve_uid)
        self.assertEqual(self.head.db.sleeve_uid, "sleeve-9")

    def test_overlay_marks_corpse_head_severed(self):
        """``apply_sever_to_corpse(location='head')`` flips the
        ``head_severed`` gate that
        :meth:`typeclasses.corpse.Corpse.get_display_name` reads."""
        from typeclasses.items import apply_sever_to_corpse
        self.assertFalse(self.corpse.db.head_severed)
        apply_sever_to_corpse(self.corpse, "head")
        self.assertTrue(self.corpse.db.head_severed)

    def test_limb_sever_does_not_mark_corpse_head_severed(self):
        """Non-head sever leaves ``head_severed`` unchanged."""
        from typeclasses.items import apply_sever_to_corpse
        apply_sever_to_corpse(self.corpse, "left_arm")
        self.assertFalse(self.corpse.db.head_severed)

    def test_overlay_preserves_corpse_identity_for_autopsy(self):
        """Identity is duplicated, not transferred — corpse keeps snapshot."""
        sig_before = self.corpse.db.signature_at_death
        uid_before = self.corpse.db.apparent_uid_at_death
        sleeve_before = self.corpse.db.sleeve_uid
        apply_severed_head_overlay(self.head, self.corpse)
        self.assertEqual(self.corpse.db.signature_at_death, sig_before)
        self.assertEqual(self.corpse.db.apparent_uid_at_death, uid_before)
        self.assertEqual(self.corpse.db.sleeve_uid, sleeve_before)

    def test_sleeve_uid_property_reads_db_attr(self):
        """The property surface matches Corpse.sleeve_uid for the identity pipeline."""
        self.head.db.sleeve_uid = "sleeve-test"
        # Bound-method-style call against the production property.
        # ``SeveredHead.sleeve_uid`` is a property descriptor; resolve
        # via the fget so we can call it against the stub directly.
        self.assertEqual(
            SeveredHead.sleeve_uid.fget(self.head), "sleeve-test",
        )

