"""Tests for :meth:`typeclasses.objects.BloodPool.add_bleeding_incident`.

PR-E adds two forward-only data-prep arguments (``signature`` and
``apparent_uid``) to the bleeding-incident dict so the Forensic
Recognition Engine has fully populated subjects to consume once a
blood-pool command surface lands.

Coverage:

* Modern call path stores both new fields on the incident.
* Legacy call path (only ``character_name`` / ``severity`` /
  ``sleeve_uid``) still works and leaves the new fields as ``None`` so
  forensic consumers can ``.get("signature")`` without raising.
* The engine extractor (:func:`world.forensics.extract_subject_from_blood_pool_incident`)
  consumes both shapes correctly, closing the data-prep loop.

Run via::

    evennia test world.tests.test_blood_pool_incident
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.forensics import extract_subject_from_blood_pool_incident


class _DB:
    """Bare attribute holder mimicking ``obj.db``."""


def _make_pool():
    """Construct a stand-in BloodPool object that exercises the
    incident-list append path without booting Evennia.

    We bind the real
    :meth:`typeclasses.objects.BloodPool.add_bleeding_incident` to a
    bare object that supplies the attributes the method touches:
    ``db.bleeding_incidents``, ``db.total_volume``, ``db.last_updated``,
    and ``_update_description``.
    """
    from typeclasses.objects import BloodPool

    pool = MagicMock()
    pool.db = _DB()
    pool.db.bleeding_incidents = None
    pool.db.total_volume = 0
    pool.db.last_updated = None
    pool._update_description = MagicMock()
    # Bind the unbound method so it operates on our stand-in.
    pool.add_bleeding_incident = (
        BloodPool.add_bleeding_incident.__get__(pool, type(pool))
    )
    return pool


class TestAddBleedingIncidentModern(TestCase):
    def test_signature_and_apparent_uid_stored(self):
        pool = _make_pool()
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava",))
        with patch("typeclasses.objects.gametime") as fake_time:
            fake_time.gametime.return_value = 1000.0
            pool.add_bleeding_incident(
                character_name="Jorge",
                severity=5,
                sleeve_uid="sleeve-1",
                signature=sig,
                apparent_uid="abc123",
            )
        incidents = pool.db.bleeding_incidents
        self.assertEqual(len(incidents), 1)
        entry = incidents[0]
        self.assertEqual(entry["signature"], sig)
        self.assertEqual(entry["apparent_uid"], "abc123")
        self.assertEqual(entry["sleeve_uid"], "sleeve-1")
        self.assertEqual(entry["severity"], 5)
        self.assertEqual(entry["character"], "Jorge")


class TestAddBleedingIncidentLegacy(TestCase):
    def test_legacy_call_leaves_new_fields_none(self):
        pool = _make_pool()
        with patch("typeclasses.objects.gametime") as fake_time:
            fake_time.gametime.return_value = 1000.0
            pool.add_bleeding_incident(
                character_name="Jorge",
                severity=3,
                sleeve_uid="sleeve-1",
            )
        entry = pool.db.bleeding_incidents[0]
        self.assertIsNone(entry["signature"])
        self.assertIsNone(entry["apparent_uid"])


class TestForensicExtractorClosesTheLoop(TestCase):
    """Verify the extractor consumes both call shapes."""

    def test_modern_incident_round_trips_through_extractor(self):
        pool = _make_pool()
        sig = ("sleeve-1", "tall", "lean", "hooded", ("balaclava",))
        with patch("typeclasses.objects.gametime") as fake_time:
            fake_time.gametime.return_value = 1000.0
            pool.add_bleeding_incident(
                character_name="Jorge", severity=5,
                sleeve_uid="sleeve-1", signature=sig, apparent_uid="abc123",
            )
        subject = extract_subject_from_blood_pool_incident(
            pool, pool.db.bleeding_incidents[0],
        )
        self.assertEqual(subject.signature, sig)
        self.assertEqual(subject.apparent_uid_at_death, "abc123")
        self.assertEqual(subject.essential_item_type_ids, ("balaclava",))
        self.assertEqual(subject.source_kind, "blood_pool")

    def test_legacy_incident_round_trips_as_unknown_signature(self):
        pool = _make_pool()
        with patch("typeclasses.objects.gametime") as fake_time:
            fake_time.gametime.return_value = 1000.0
            pool.add_bleeding_incident(
                character_name="Jorge", severity=3, sleeve_uid="sleeve-1",
            )
        subject = extract_subject_from_blood_pool_incident(
            pool, pool.db.bleeding_incidents[0],
        )
        self.assertIsNone(subject.signature)
        self.assertIsNone(subject.apparent_uid_at_death)
        self.assertEqual(subject.essential_item_type_ids, ())
