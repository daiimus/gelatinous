"""Recognition flow on :class:`typeclasses.items.SeveredHead` (PR #208).

The SeveredHead super-item inherits :class:`typeclasses.identity_bearer.IdentityBearerMixin`,
and PR #208 wires ``self.db.sleeve_uid`` (populated by
:func:`typeclasses.items.apply_severed_head_overlay`) into the same
``world.identity.get_identity_signature`` pipeline the corpse uses.
This file locks the two-pass recognition contract for severed heads:

1. **Natural recognition** through fresh / early stages — the head's
   live-derived apparent UID equals the source corpse's, so a looker
   whose memory contains the matching UID gets the
   ``"<decay name> (<assigned name>)"`` parenthetical.
2. **Moderate / advanced** stages blank the sleeve-UID axis via
   :func:`world.identity.get_apparent_uid_for_decay`, so natural
   recognition stops — but the forensic-recovery Intellect roll can
   restore the parenthetical when the roll passes the stage DC.
3. **Skeletal** is the hard cutoff — no recognition path resurfaces
   the name regardless of memory or rolls.

The test fakes mirror the duck-typed pattern used by
:mod:`world.tests.test_corpse_decay_recognition._FakeDecayCorpse`:
bind production methods onto a minimal stub so we exercise the real
recognition pipeline without instantiating an Evennia typeclass.

Run via::

    docker exec gelatinous evennia test --settings settings.py \
        world.tests.test_severed_head_recognition
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from typeclasses.items import SeveredHead
from world.identity import get_apparent_uid


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeSeveredHead:
    """Duck-typed SeveredHead exercising the production recognition path.

    Binds ``IdentityBearerMixin`` methods (inherited by SeveredHead)
    onto a lightweight stub.  The ``sleeve_uid`` *property* on the
    production class is replaced with a direct attribute here — the
    mixin reads ``getattr(self, "sleeve_uid", None)`` via
    :func:`world.identity.get_identity_signature`, so a plain
    attribute satisfies the contract identically.
    """

    # Bind production methods so tests hit the real implementation.
    get_display_name = SeveredHead.get_display_name
    _attempt_forensic_recognition = SeveredHead._attempt_forensic_recognition
    _FORENSIC_RECOGNITION_DC = SeveredHead._FORENSIC_RECOGNITION_DC

    def __init__(
        self,
        *,
        sleeve_uid: str | None = "uid-jorge",
        stage: str = "fresh",
    ) -> None:
        class _DB:
            pass

        self.db = _DB()
        self.db.sleeve_uid = sleeve_uid
        self.db.signature_at_death = None
        self.db.apparent_uid_at_death = None
        self.db.forensic_recognition_cache = None
        self.db.height_override = None
        self.db.build_override = None
        self.db.keyword_override = None
        self.sleeve_uid = sleeve_uid  # mixin reads via get_identity_signature
        self.ndb = type("_NDB", (), {})()
        self._stage = stage
        # Decay-name table mirrors world.anatomy.get_species_part_name
        # ("human", "head", stage) outputs so we don't need the live
        # registry call here.
        self._decay_names = {
            "fresh": "human head",
            "early": "human head",
            "moderate": "rotting head",
            "advanced": "rotting head",
            "skeletal": "skeletal head",
        }

    def get_worn_items(self, location=None):
        del location
        # SeveredHead always returns [] (heads carry no clothing).
        return []

    def get_decay_stage(self):
        return self._stage

    def _decay_display_name(self):
        return self._decay_names[self._stage]


class _FakeObserver:
    """Minimal observer with ``recognition_memory`` and ``dbref``."""

    def __init__(
        self,
        *,
        memory: dict | None = None,
        dbref: str | None = "#42",
        intellect: int = 1,
    ) -> None:
        self.recognition_memory = memory or {}
        self.dbref = dbref
        self.intellect = intellect


# ---------------------------------------------------------------------
# Natural recognition through light decay
# ---------------------------------------------------------------------


class TestHeadNaturalRecognition(TestCase):
    """Fresh / early stages match the live apparent UID."""

    def test_fresh_renders_parenthetical(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="fresh")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            head.get_display_name(observer), "human head (Jorge)",
        )

    def test_early_renders_parenthetical(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="early")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            head.get_display_name(observer), "human head (Jorge)",
        )

    def test_none_looker_returns_decay_name(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="fresh")
        self.assertEqual(head.get_display_name(None), "human head")

    def test_stranger_sees_decay_name(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="fresh")
        observer = _FakeObserver(memory={})
        self.assertEqual(head.get_display_name(observer), "human head")

    def test_head_with_no_sleeve_uid_falls_back_to_decay_name(self):
        """A head whose source corpse lacked sleeve_uid never recognises."""
        head = _FakeSeveredHead(sleeve_uid=None, stage="fresh")
        # Memory contains *something*, but the head can't produce a UID.
        observer = _FakeObserver(memory={"any-uid": {"assigned_name": "X"}})
        self.assertEqual(head.get_display_name(observer), "human head")


# ---------------------------------------------------------------------
# Forensic recovery at moderate / advanced
# ---------------------------------------------------------------------


class TestHeadForensicRecovery(TestCase):
    """Moderate / advanced require an Intellect roll to recover identity."""

    def test_moderate_natural_blanked_without_roll(self):
        """Without forensic pass, moderate-stage natural recognition fails."""
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # DC 3; force failing roll.
        with patch("world.combat.dice.roll_stat", return_value=2):
            self.assertEqual(
                head.get_display_name(observer), "rotting head",
            )

    def test_moderate_pass_returns_assigned_name(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch("world.combat.dice.roll_stat", return_value=3):
            self.assertEqual(
                head.get_display_name(observer), "rotting head (Jorge)",
            )

    def test_advanced_pass_returns_assigned_name(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="advanced")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch("world.combat.dice.roll_stat", return_value=5):
            self.assertEqual(
                head.get_display_name(observer), "rotting head (Jorge)",
            )

    def test_advanced_fail_returns_decay_name(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="advanced")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch("world.combat.dice.roll_stat", return_value=4):
            self.assertEqual(
                head.get_display_name(observer), "rotting head",
            )


# ---------------------------------------------------------------------
# Skeletal hard cutoff
# ---------------------------------------------------------------------


class TestHeadSkeletalHardCutoff(TestCase):
    """Skeletal heads never surface a recognised name."""

    def test_skeletal_blocks_natural_recognition(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="skeletal")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            head.get_display_name(observer), "skeletal head",
        )

    def test_skeletal_blocks_forensic_recovery(self):
        head = _FakeSeveredHead(sleeve_uid="uid-jorge", stage="skeletal")
        fresh_uid = get_apparent_uid(head)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
            intellect=99,
        )
        with patch("world.combat.dice.roll_stat", return_value=99):
            self.assertEqual(
                head.get_display_name(observer), "skeletal head",
            )
