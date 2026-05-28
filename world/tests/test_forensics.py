"""Unit tests for the Forensic Recognition Engine (PR-E).

Covers :mod:`world.forensics`:

* :class:`ForensicSubject` extraction from corpse / blood-pool
  incident; ``NotImplementedError`` for photo stub.
* :func:`attempt_forensic_recognition` — roll, cache hit/miss, cache
  re-roll on UID change, anonymous-looker handling.
* :func:`render_forensic_report` — depth ladder output shape; safe
  None-signature handling; never includes assigned names.
* :func:`link_subjects` — shared-axes detection.

Built on lightweight fakes so no Evennia DB is required.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.forensics import (
    ForensicSubject,
    LinkResult,
    RecognitionResult,
    attempt_forensic_recognition,
    extract_subject_from_blood_pool_incident,
    extract_subject_from_corpse,
    extract_subject_from_photo,
    link_subjects,
    render_forensic_report,
)


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _DB:
    """Bare attribute holder mimicking ``obj.db``."""


class _FakeCorpse:
    """Minimal corpse surface for forensic extraction."""

    def __init__(
        self,
        *,
        signature=None,
        apparent_uid=None,
        sleeve_uid="uid-jorge",
        dbref="#1",
    ) -> None:
        self.db = _DB()
        self.db.signature_at_death = signature
        self.db.apparent_uid_at_death = apparent_uid
        self.db.sleeve_uid = sleeve_uid
        self.db.forensic_recognition_cache = None
        self.db.height_override = signature[1] if signature else None
        self.db.build_override = signature[2] if signature else None
        self.db.keyword_override = signature[3] if signature else None
        self.contents = []
        self.dbref = dbref

    @property
    def sleeve_uid(self):
        return self.db.sleeve_uid

    def get_worn_items(self, location=None):
        del location
        return []


class _FakePool:
    pass


class _FakeObserver:
    def __init__(self, *, dbref="#42", intellect=1, memory=None):
        self.dbref = dbref
        self.intellect = intellect
        self.recognition_memory = memory or {}


# ---------------------------------------------------------------------
# ForensicSubject extraction
# ---------------------------------------------------------------------


class TestExtractFromCorpse(TestCase):
    def test_full_snapshot_propagates(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava",))
        corpse = _FakeCorpse(signature=sig, apparent_uid="abc123")
        subject = extract_subject_from_corpse(corpse)
        self.assertEqual(subject.signature, sig)
        self.assertEqual(subject.apparent_uid_at_death, "abc123")
        self.assertEqual(subject.essential_item_type_ids, ("balaclava",))
        self.assertEqual(subject.source_kind, "corpse")
        self.assertIs(subject.source_ref, corpse)

    def test_missing_snapshot_yields_none_signature(self):
        corpse = _FakeCorpse(signature=None, apparent_uid=None)
        subject = extract_subject_from_corpse(corpse)
        self.assertIsNone(subject.signature)
        self.assertIsNone(subject.apparent_uid_at_death)
        self.assertEqual(subject.essential_item_type_ids, ())

    def test_empty_essentials_tuple(self):
        sig = ("sleeve-1", None, None, None, ())
        corpse = _FakeCorpse(signature=sig)
        subject = extract_subject_from_corpse(corpse)
        self.assertEqual(subject.essential_item_type_ids, ())


class TestExtractFromBloodPoolIncident(TestCase):
    def test_modern_incident_with_signature(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava",))
        incident = {
            "character": "someone",
            "sleeve_uid": "sleeve-1",
            "signature": sig,
            "apparent_uid": "deadbeef",
            "severity": 5,
            "timestamp": 100.0,
        }
        pool = _FakePool()
        subject = extract_subject_from_blood_pool_incident(pool, incident)
        self.assertEqual(subject.signature, sig)
        self.assertEqual(subject.apparent_uid_at_death, "deadbeef")
        self.assertEqual(subject.essential_item_type_ids, ("balaclava",))
        self.assertEqual(subject.source_kind, "blood_pool")

    def test_legacy_incident_without_signature_field(self):
        incident = {
            "character": "someone",
            "sleeve_uid": "sleeve-1",
            "severity": 5,
            "timestamp": 100.0,
        }
        pool = _FakePool()
        subject = extract_subject_from_blood_pool_incident(pool, incident)
        self.assertIsNone(subject.signature)
        self.assertIsNone(subject.apparent_uid_at_death)
        self.assertEqual(subject.essential_item_type_ids, ())


class TestExtractFromPhotoStub(TestCase):
    def test_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            extract_subject_from_photo(object())


# ---------------------------------------------------------------------
# Recognition engine
# ---------------------------------------------------------------------


class TestAttemptForensicRecognition(TestCase):
    def _subject(self, *, apparent_uid="abc123"):
        sig = ("sleeve-1", "tall", "lean", "hooded", ())
        return ForensicSubject(
            signature=sig,
            apparent_uid_at_death=apparent_uid,
            essential_item_type_ids=(),
            source_kind="corpse",
            source_ref=_FakeCorpse(signature=sig, apparent_uid=apparent_uid),
        )

    def test_success_passes_roll(self):
        owner = _FakeCorpse()
        observer = _FakeObserver()
        with patch("world.combat.dice.roll_stat", return_value=5):
            result = attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
        self.assertIsInstance(result, RecognitionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.revealed_uid, "abc123")
        self.assertFalse(result.from_cache)

    def test_failure_at_dc(self):
        owner = _FakeCorpse()
        observer = _FakeObserver()
        with patch("world.combat.dice.roll_stat", return_value=2):
            result = attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
        self.assertFalse(result.success)

    def test_cache_hit_skips_reroll(self):
        owner = _FakeCorpse()
        observer = _FakeObserver()
        with patch("world.combat.dice.roll_stat", return_value=1):
            first = attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            second = attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
            mocked.assert_not_called()
        self.assertFalse(first.success)
        self.assertFalse(second.success)
        self.assertTrue(second.from_cache)

    def test_cache_reroll_when_uid_changes(self):
        """Disguise loss → new apparent UID → fresh cache slot."""
        owner = _FakeCorpse()
        observer = _FakeObserver()
        subject_v1 = self._subject(apparent_uid="uid-v1")
        subject_v2 = self._subject(apparent_uid="uid-v2")
        with patch("world.combat.dice.roll_stat", return_value=1):
            attempt_forensic_recognition(
                observer, subject_v1, dc=3, cache_owner=owner,
            )
        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            result = attempt_forensic_recognition(
                observer, subject_v2, dc=3, cache_owner=owner,
            )
            mocked.assert_called_once()
        self.assertTrue(result.success)
        self.assertFalse(result.from_cache)

    def test_anonymous_looker_does_not_cache(self):
        owner = _FakeCorpse()
        observer = _FakeObserver(dbref=None)
        with patch("world.combat.dice.roll_stat", return_value=1):
            attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
        # Second call must re-roll because nothing was stored.
        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            result = attempt_forensic_recognition(
                observer, self._subject(), dc=3, cache_owner=owner,
            )
            mocked.assert_called_once()
        self.assertTrue(result.success)

    def test_subject_without_uid_short_circuits(self):
        owner = _FakeCorpse()
        observer = _FakeObserver()
        subject = ForensicSubject(
            signature=None,
            apparent_uid_at_death=None,
            essential_item_type_ids=(),
            source_kind="corpse",
            source_ref=None,
        )
        with patch("world.combat.dice.roll_stat") as mocked:
            result = attempt_forensic_recognition(
                observer, subject, dc=3, cache_owner=owner,
            )
            mocked.assert_not_called()
        self.assertFalse(result.success)
        self.assertIsNone(result.revealed_uid)


# ---------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------


class TestRenderForensicReport(TestCase):
    def _subject(self, sig=None, essentials=()):
        return ForensicSubject(
            signature=sig,
            apparent_uid_at_death=None,
            essential_item_type_ids=essentials,
            source_kind="corpse",
            source_ref=None,
        )

    def test_summary_lists_three_axes(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ())
        out = render_forensic_report(
            self._subject(sig=sig), observer=None, depth="summary",
        )
        self.assertIn("tall", out)
        self.assertIn("lean", out)
        self.assertIn("hooded", out)
        self.assertNotIn("Worn essentials", out)

    def test_detailed_includes_essentials(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava", "trenchcoat"))
        out = render_forensic_report(
            self._subject(sig=sig, essentials=("balaclava", "trenchcoat")),
            observer=None, depth="detailed",
        )
        self.assertIn("balaclava", out)
        self.assertIn("trenchcoat", out)

    def test_detailed_with_no_essentials(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ())
        out = render_forensic_report(
            self._subject(sig=sig), observer=None, depth="detailed",
        )
        self.assertIn("none recovered", out)

    def test_none_signature_returns_graceful_message(self):
        out = render_forensic_report(
            self._subject(sig=None), observer=None, depth="summary",
        )
        self.assertIn("no further forensic detail", out)

    def test_invalid_depth_raises(self):
        sig = ("sleeve-1", None, None, None, ())
        with self.assertRaises(ValueError):
            render_forensic_report(
                self._subject(sig=sig), observer=None, depth="bogus",
            )

    def test_indeterminate_axes_rendered(self):
        sig = ("sleeve-1", None, None, None, ())
        out = render_forensic_report(
            self._subject(sig=sig), observer=None, depth="summary",
        )
        self.assertIn("indeterminate", out)

    def test_report_never_contains_assigned_name(self):
        """Recognition contract: renderer must not surface names."""
        sig = ("sleeve-1", "tall", "lean", "hooded", ())
        out = render_forensic_report(
            self._subject(sig=sig), observer=None, depth="detailed",
        )
        # The renderer has no access to recognition memory at all.
        self.assertNotIn("Jorge", out)


# ---------------------------------------------------------------------
# Linking primitive
# ---------------------------------------------------------------------


class TestLinkSubjects(TestCase):
    def _subject(self, sig, apparent_uid=None):
        return ForensicSubject(
            signature=sig,
            apparent_uid_at_death=apparent_uid,
            essential_item_type_ids=tuple(sig[4]) if sig else (),
            source_kind="corpse",
            source_ref=None,
        )

    def test_identical_signatures_share_all_axes(self):
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava",))
        result = link_subjects(self._subject(sig), self._subject(sig))
        self.assertIsInstance(result, LinkResult)
        self.assertTrue(result.shared_sleeve_uid)
        self.assertEqual(len(result.shared_axes), 5)

    def test_same_sleeve_different_disguise(self):
        sig_a = ("sleeve-1", "tall", "lean", "hooded", ())
        sig_b = ("sleeve-1", "short", "wide", "masked", ())
        result = link_subjects(self._subject(sig_a), self._subject(sig_b))
        self.assertTrue(result.shared_sleeve_uid)
        self.assertIn("sleeve_uid", result.shared_axes)

    def test_disjoint_subjects(self):
        sig_a = ("sleeve-1", "tall", None, None, ())
        sig_b = ("sleeve-2", "short", None, None, ())
        result = link_subjects(self._subject(sig_a), self._subject(sig_b))
        self.assertFalse(result.shared_sleeve_uid)
        self.assertNotIn("sleeve_uid", result.shared_axes)

    def test_none_signature_returns_empty_axes(self):
        sig = ("sleeve-1", "tall", None, None, ())
        result = link_subjects(self._subject(None), self._subject(sig))
        self.assertEqual(result.shared_axes, ())
        self.assertFalse(result.shared_sleeve_uid)

    def test_shared_apparent_uid_detected_without_signature(self):
        a = ForensicSubject(
            signature=None, apparent_uid_at_death="abc",
            essential_item_type_ids=(), source_kind="corpse", source_ref=None,
        )
        b = ForensicSubject(
            signature=None, apparent_uid_at_death="abc",
            essential_item_type_ids=(), source_kind="corpse", source_ref=None,
        )
        result = link_subjects(a, b)
        self.assertTrue(result.shared_apparent_uid)
