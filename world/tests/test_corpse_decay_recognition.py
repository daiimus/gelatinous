"""
Tests for Phase 3.6 PR B — decay-aware corpse recognition.

Verifies the two-pass recognition flow on
:meth:`typeclasses.corpse.Corpse.get_display_name`:

1. **Decay-degraded UID path** — at ``moderate`` and ``advanced`` decay
   stages, :func:`world.identity.get_apparent_uid_for_decay` blanks the
   ``sleeve_uid`` axis, producing a UID that no fresh-keyed memory entry
   matches.  At ``fresh`` and ``early`` the degraded UID equals the
   fresh UID (natural recognition keeps working through light decay).
2. **Forensic recovery path** — when the degraded lookup misses but the
   fresh UID is in memory, an Intellect roll against the stage DC may
   recover the assigned name.  The roll outcome is cached permanently
   per ``(looker.dbref, corpse)`` so a single careful examination
   determines the verdict for that observer.
3. **Skeletal hard cutoff** — the skeletal stage suppresses both
   recognition paths in the display name (programmatic
   ``sleeve_uid`` queries continue to work for forensic tooling).
4. **Worn-item disguise persistence** — items in ``corpse.contents``
   keep contributing to the signature at non-skeletal stages, so a
   recognizable jacket still anchors recognition through decay; a fresh
   memory keyed to ``(sleeve_uid + jacket)`` only resurfaces via
   forensic recovery once the body itself is no longer readable.
5. **Living-character regression guard** —
   :func:`world.identity.get_apparent_uid` is unchanged for living
   characters (the new helper is additive).

Run via::

    docker exec gelatinous evennia test --settings settings.py \\
        world.tests.test_corpse_decay_recognition

These are pure unit tests built on lightweight fakes that bind the
production :class:`typeclasses.corpse.Corpse` methods to a duck-typed
instance — no Evennia database is required.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from typeclasses.corpse import Corpse
from world.identity import (
    get_apparent_uid,
    get_apparent_uid_for_decay,
)
from world.tests.test_identity import _FakeDisguiseItem


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeDecayCorpse:
    """Duck-typed corpse that binds production ``Corpse`` methods.

    Holds the minimum ``db`` / ``contents`` / ``ndb`` surface that the
    production :meth:`Corpse.get_display_name` and
    :meth:`Corpse._attempt_forensic_recognition` touch, plus a
    test-controlled ``_stage`` so we can pin the decay stage without
    juggling ``creation_time`` arithmetic.
    """

    # Bind production methods so tests exercise the real implementation.
    get_display_name = Corpse.get_display_name
    _is_headless = Corpse._is_headless
    _attempt_forensic_recognition = Corpse._attempt_forensic_recognition
    _FORENSIC_RECOGNITION_DC = Corpse._FORENSIC_RECOGNITION_DC

    def __init__(
        self,
        *,
        sleeve_uid: str | None = "uid-jorge",
        height_override: str | None = None,
        build_override: str | None = None,
        keyword_override: str | None = None,
        contents: list | None = None,
        stage: str = "fresh",
    ) -> None:
        class _DB:
            pass

        self.db = _DB()
        self.db.sleeve_uid = sleeve_uid
        self.db.height_override = height_override
        self.db.build_override = build_override
        self.db.keyword_override = keyword_override
        self.db.apparent_uid_at_death = None
        self.db.signature_at_death = None
        self.db.forensic_recognition_cache = None
        # PR #208: default to head-intact; tests that exercise the
        # head-severed look-suppression flip this to True.
        self.db.head_severed = False
        # Durable severance record — the corpse-build bug strands
        # ``head_severed`` False while this still records the head came
        # off, so ``_is_headless`` also reads here.
        self.db.severed_locations = []
        self.contents = list(contents or [])
        self.ndb = type("_NDB", (), {})()
        self._stage = stage
        # PR-G: match the species-aware vocabulary produced by
        # ``world.anatomy.get_species_corpse_name(species="human", ...)``.
        self._decay_names = {
            "fresh": "human corpse",
            "early": "human corpse",
            "moderate": "rotting corpse",
            "advanced": "rotting corpse",
            "skeletal": "skeletal remains",
        }

    @property
    def sleeve_uid(self):
        return self.db.sleeve_uid

    def get_worn_items(self, location=None):
        del location
        return [
            item
            for item in self.contents
            if getattr(item, "disguise_essential", False)
        ]

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
# Decay-degraded UID helper (world.identity.get_apparent_uid_for_decay)
# ---------------------------------------------------------------------


class TestGetApparentUidForDecay(TestCase):
    """The new helper degrades the UID per stage, no roll involved."""

    def test_fresh_stage_matches_fresh_uid(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge")
        self.assertEqual(
            get_apparent_uid_for_decay(corpse, "fresh"),
            get_apparent_uid(corpse),
        )

    def test_early_stage_matches_fresh_uid(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge")
        self.assertEqual(
            get_apparent_uid_for_decay(corpse, "early"),
            get_apparent_uid(corpse),
        )

    def test_moderate_stage_differs_from_fresh_uid(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge")
        self.assertNotEqual(
            get_apparent_uid_for_decay(corpse, "moderate"),
            get_apparent_uid(corpse),
        )

    def test_advanced_stage_differs_from_fresh_uid(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge")
        self.assertNotEqual(
            get_apparent_uid_for_decay(corpse, "advanced"),
            get_apparent_uid(corpse),
        )

    def test_returns_none_when_sleeve_uid_missing(self):
        corpse = _FakeDecayCorpse(sleeve_uid=None)
        self.assertIsNone(get_apparent_uid_for_decay(corpse, "moderate"))

    def test_worn_items_still_affect_degraded_uid(self):
        balaclava = _FakeDisguiseItem(
            disguise_essential=True, disguise_type_id="balaclava",
        )
        bare = _FakeDecayCorpse(sleeve_uid="uid-jorge")
        clothed = _FakeDecayCorpse(
            sleeve_uid="uid-jorge", contents=[balaclava],
        )
        self.assertNotEqual(
            get_apparent_uid_for_decay(bare, "moderate"),
            get_apparent_uid_for_decay(clothed, "moderate"),
        )


# ---------------------------------------------------------------------
# Skeletal hard cutoff
# ---------------------------------------------------------------------


class TestSkeletalHardCutoff(TestCase):
    """Skeletal corpses never surface a recognised name."""

    def test_skeletal_blocks_natural_recognition(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="skeletal")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "skeletal remains",
        )

    def test_skeletal_blocks_forensic_recovery(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="skeletal")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
            intellect=99,
        )
        # Even with a guaranteed-pass roll, skeletal short-circuits
        # before forensic recovery is attempted.
        with patch(
            "world.combat.dice.roll_stat", return_value=99,
        ):
            self.assertEqual(
                corpse.get_display_name(observer), "skeletal remains",
            )

    def test_sleeve_uid_still_queryable_on_skeleton(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="skeletal")
        # Programmatic forensic queries still see the sleeve UID; only
        # the *display name* path is blocked.
        self.assertEqual(corpse.sleeve_uid, "uid-jorge")
        self.assertIsNotNone(get_apparent_uid(corpse))


# ---------------------------------------------------------------------
# Natural recognition through light decay
# ---------------------------------------------------------------------


class TestNaturalRecognitionLightDecay(TestCase):
    """Fresh and early stages keep ordinary recognition working."""

    def test_fresh_recognition_returns_assigned_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="fresh")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse (Jorge)"
        )

    def test_early_recognition_returns_assigned_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="early")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse (Jorge)"
        )

    def test_none_looker_returns_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        self.assertEqual(
            corpse.get_display_name(None), "rotting corpse",
        )

    def test_stranger_sees_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        observer = _FakeObserver(memory={})
        self.assertEqual(
            corpse.get_display_name(observer), "rotting corpse",
        )


# ---------------------------------------------------------------------
# Forensic recovery (Intellect roll vs stage DC, with caching)
# ---------------------------------------------------------------------


class TestForensicRecovery(TestCase):
    """Moderate / advanced require an Intellect roll to recover identity."""

    def test_moderate_pass_returns_assigned_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # DC 3 for moderate; force a passing roll.
        with patch("world.combat.dice.roll_stat", return_value=3):
            self.assertEqual(corpse.get_display_name(observer), "rotting corpse (Jorge)")

    def test_moderate_fail_returns_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # DC 3 for moderate; force a failing roll.
        with patch("world.combat.dice.roll_stat", return_value=2):
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )

    def test_advanced_pass_returns_assigned_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="advanced")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # DC 5 for advanced.
        with patch("world.combat.dice.roll_stat", return_value=5):
            self.assertEqual(corpse.get_display_name(observer), "rotting corpse (Jorge)")

    def test_advanced_fail_returns_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="advanced")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch("world.combat.dice.roll_stat", return_value=4):
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )


# ---------------------------------------------------------------------
# Forensic cache stickiness
# ---------------------------------------------------------------------


class TestForensicCache(TestCase):
    """Roll outcome is cached permanently per (looker.dbref, corpse)."""

    def test_failure_sticks_across_rerolls(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # First look: forced failure.
        with patch("world.combat.dice.roll_stat", return_value=1):
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )
        # Second look: even a guaranteed-pass roll must not re-roll —
        # the cached failure persists.
        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )
            mocked.assert_not_called()

    def test_success_sticks_across_rerolls(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch("world.combat.dice.roll_stat", return_value=10):
            self.assertEqual(corpse.get_display_name(observer), "rotting corpse (Jorge)")
        # Cached success: a forced-fail roll must not be consulted.
        with patch("world.combat.dice.roll_stat", return_value=1) as mocked:
            self.assertEqual(corpse.get_display_name(observer), "rotting corpse (Jorge)")
            mocked.assert_not_called()

    def test_cache_is_keyed_by_dbref(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        memory = {fresh_uid: {"assigned_name": "Jorge"}}
        observer_a = _FakeObserver(memory=memory, dbref="#42")
        observer_b = _FakeObserver(memory=memory, dbref="#43")

        # A fails, locked in.
        with patch("world.combat.dice.roll_stat", return_value=1):
            self.assertEqual(
                corpse.get_display_name(observer_a),
                "rotting corpse",
            )
        # B independently passes (different dbref → fresh roll).
        with patch("world.combat.dice.roll_stat", return_value=99):
            self.assertEqual(corpse.get_display_name(observer_b), "rotting corpse (Jorge)")

    def test_anonymous_looker_rerolls_each_call(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        fresh_uid = get_apparent_uid(corpse)
        # No dbref → must not be cached.
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
            dbref=None,
        )
        with patch("world.combat.dice.roll_stat", return_value=1):
            self.assertEqual(
                corpse.get_display_name(observer),
                "rotting corpse",
            )
        # Re-roll happens because nothing was stored.
        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            self.assertEqual(corpse.get_display_name(observer), "rotting corpse (Jorge)")
            mocked.assert_called_once()


# ---------------------------------------------------------------------
# Worn-item disguise interaction with decay
# ---------------------------------------------------------------------


class TestWornItemDisguiseThroughDecay(TestCase):
    """Disguise items keep contributing to the UID through decay stages."""

    def test_jacket_does_not_resurface_past_skeletal(self):
        balaclava = _FakeDisguiseItem(
            disguise_essential=True, disguise_type_id="balaclava",
        )
        corpse = _FakeDecayCorpse(
            sleeve_uid="uid-jorge",
            contents=[balaclava],
            stage="skeletal",
        )
        # Memory keyed to the live-disguise (sleeve + balaclava) UID.
        disguised_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={disguised_uid: {"assigned_name": "BalaclavaDude"}},
            intellect=99,
        )
        with patch("world.combat.dice.roll_stat", return_value=99):
            self.assertEqual(
                corpse.get_display_name(observer), "skeletal remains",
            )

    def test_jacket_recovers_via_forensics_at_advanced(self):
        balaclava = _FakeDisguiseItem(
            disguise_essential=True, disguise_type_id="balaclava",
        )
        corpse = _FakeDecayCorpse(
            sleeve_uid="uid-jorge",
            contents=[balaclava],
            stage="advanced",
        )
        disguised_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={disguised_uid: {"assigned_name": "BalaclavaDude"}},
        )
        # Advanced DC = 5; pass.
        with patch("world.combat.dice.roll_stat", return_value=5):
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse (BalaclavaDude)",
            )


# ---------------------------------------------------------------------
# Living-character regression guard
# ---------------------------------------------------------------------


class TestLivingCharacterRegressionGuard(TestCase):
    """``get_apparent_uid`` is unchanged for living characters."""

    def test_living_uid_matches_freshly_dead_corpse_uid(self):
        from world.tests.test_identity import _SignatureMockCharacter

        living = _SignatureMockCharacter(
            sleeve_uid="uid-jorge",
            height_override=None,
            build_override=None,
            keyword_override=None,
            worn_items=[],
        )
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="fresh")
        self.assertEqual(get_apparent_uid(living), get_apparent_uid(corpse))

    def test_living_uid_unaffected_by_decay_helper(self):
        from world.tests.test_identity import _SignatureMockCharacter

        living = _SignatureMockCharacter(
            sleeve_uid="uid-jorge",
            height_override=None,
            build_override=None,
            keyword_override=None,
            worn_items=[],
        )
        # The decay helper would degrade *if* invoked on a living
        # character with an "advanced" stage — but the production path
        # only invokes it for corpses, and the standard helper stays
        # intact.
        self.assertIsNotNone(get_apparent_uid(living))
        self.assertNotEqual(
            get_apparent_uid(living),
            get_apparent_uid_for_decay(living, "advanced"),
        )


# ---------------------------------------------------------------------
# PR #208 — headless-corpse recognition suppression
# ---------------------------------------------------------------------


class TestHeadSeveredSuppression(TestCase):
    """A corpse with ``db.head_severed`` blocks both recognition paths.

    Identity-bearing snapshot fields stay populated so the autopsy
    flow keeps working; only the look-time tertiary recognition is
    suppressed.  Pass 1 (natural / degraded UID) and Pass 2
    (forensic-recovery Intellect roll) both short-circuit to the
    decay-stage fallback before the mixin's recognition pipeline runs.
    """

    def test_headless_blocks_natural_recognition_fresh(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="fresh")
        corpse.db.head_severed = True
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse",
        )

    def test_severed_locations_head_anonymizes_without_flag(self):
        """Regression (live carcass #2696): the corpse-build handshake
        can strand ``head_severed=False`` while ``severed_locations``
        still records the head came off (the living-decapitation
        propagation skipped by a reload mid-progression / an NPC corpse
        path).  ``_is_headless`` reads the durable list too, so such a
        corpse still anonymises — and shipping it self-heals the
        already-stranded corpses on deploy."""
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="fresh")
        corpse.db.head_severed = False
        corpse.db.severed_locations = ["head"]
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse",
        )

    def test_headless_blocks_natural_recognition_early(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="early")
        corpse.db.head_severed = True
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse",
        )

    def test_headless_blocks_forensic_recovery_at_moderate(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        corpse.db.head_severed = True
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        # Even with a guaranteed-pass roll, head-severed short-circuits
        # before forensic recovery is attempted.
        with patch(
            "world.combat.dice.roll_stat", return_value=99,
        ) as mocked:
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )
            mocked.assert_not_called()

    def test_headless_blocks_forensic_recovery_at_advanced(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="advanced")
        corpse.db.head_severed = True
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        with patch(
            "world.combat.dice.roll_stat", return_value=99,
        ) as mocked:
            self.assertEqual(
                corpse.get_display_name(observer), "rotting corpse",
            )
            mocked.assert_not_called()

    def test_head_intact_preserves_natural_recognition(self):
        """Regression guard — head-severed defaults False; recognition still flows."""
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="fresh")
        # corpse.db.head_severed is False by default.
        fresh_uid = get_apparent_uid(corpse)
        observer = _FakeObserver(
            memory={fresh_uid: {"assigned_name": "Jorge"}},
        )
        self.assertEqual(
            corpse.get_display_name(observer), "human corpse (Jorge)",
        )

    def test_headless_none_looker_still_returns_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="moderate")
        corpse.db.head_severed = True
        self.assertEqual(
            corpse.get_display_name(None), "rotting corpse",
        )

    def test_headless_skeletal_still_returns_decay_name(self):
        corpse = _FakeDecayCorpse(sleeve_uid="uid-jorge", stage="skeletal")
        corpse.db.head_severed = True
        self.assertEqual(
            corpse.get_display_name(None), "skeletal remains",
        )

