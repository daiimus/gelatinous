"""Contract tests for :class:`typeclasses.identity_bearer.IdentityBearerMixin`.

Exercises the mixin in isolation via a minimal stand-in typeclass
``_FakeBearer`` that satisfies the duck-typed contract:

* ``self.db.signature_at_death`` / ``self.db.apparent_uid_at_death``
* ``get_decay_stage()``
* ``_decay_display_name()``

Validates the recognition pipeline end-to-end without dragging in
:class:`typeclasses.corpse.Corpse`'s clothing / account / decay
infrastructure.  The full corpse integration is covered by
``test_corpse_decay_recognition`` and stays green as the regression
guard for the mixin's behaviour in production.

Run via::

    docker exec gelatinous evennia test --settings settings.py \\
        world.tests.test_identity_bearer_mixin
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from typeclasses.identity_bearer import IdentityBearerMixin


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeDB:
    """Tiny attribute bag stand-in for ``obj.db``."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeBearer(IdentityBearerMixin):
    """Minimal mixin host.

    Holds just enough state for the recognition pipeline; subclasses /
    callers control the decay stage explicitly via ``stage``.
    """

    def __init__(
        self,
        *,
        signature=("uid-A", None, None, None, ()),
        apparent_uid="uid-A",
        stage: str = "fresh",
        decay_label: str = "fresh bearer",
    ):
        self.db = _FakeDB(
            signature_at_death=signature,
            apparent_uid_at_death=apparent_uid,
        )
        self._stage = stage
        self._decay_label = decay_label

    def get_decay_stage(self) -> str:
        return self._stage

    def _decay_display_name(self) -> str:
        return self._decay_label


class _FakeLooker:
    """Recognition-memory bag with a deterministic dbref."""

    def __init__(self, *, memory: dict | None = None, dbref: str = "#42"):
        self.recognition_memory = memory or {}
        self.dbref = dbref


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


class TestIdentityBearerMixin(TestCase):
    """End-to-end recognition contract enforcement."""

    def test_system_looker_returns_decay_name(self):
        """``looker is None`` short-circuits to the decay fallback."""
        bearer = _FakeBearer(decay_label="fresh thing")
        self.assertEqual(bearer.get_display_name(None), "fresh thing")

    def test_skeletal_is_hard_cutoff(self):
        """Skeletal stage suppresses recognition unconditionally."""
        bearer = _FakeBearer(
            stage="skeletal", decay_label="skeletal thing",
        )
        looker = _FakeLooker(
            memory={"uid-A": {"assigned_name": "Alice"}},
        )
        self.assertEqual(
            bearer.get_display_name(looker), "skeletal thing",
        )

    def test_looker_without_memory_returns_decay_name(self):
        """No ``recognition_memory`` → decay fallback."""
        bearer = _FakeBearer(decay_label="fresh thing")
        looker = _FakeLooker(memory=None)
        self.assertEqual(
            bearer.get_display_name(looker), "fresh thing",
        )

    def test_natural_recognition_through_fresh_stage(self):
        """Fresh stage: degraded UID equals fresh UID; memory hits."""
        bearer = _FakeBearer()
        looker = _FakeLooker(
            memory={"uid-A": {"assigned_name": "Alice"}},
        )
        with patch(
            "world.identity.get_apparent_uid_for_decay",
            return_value="uid-A",
        ), patch(
            "world.identity.get_apparent_uid", return_value="uid-A",
        ):
            self.assertEqual(
                bearer.get_display_name(looker), "fresh bearer (Alice)"
            )

    def test_forensic_recovery_on_pass(self):
        """Degraded UID misses, fresh UID hits, Intellect roll passes."""
        bearer = _FakeBearer(
            stage="moderate", decay_label="moderate thing",
        )
        looker = _FakeLooker(
            memory={"uid-A": {"assigned_name": "Alice"}},
        )
        with patch(
            "world.identity.get_apparent_uid_for_decay",
            return_value="uid-degraded",
        ), patch(
            "world.identity.get_apparent_uid", return_value="uid-A",
        ), patch(
            "typeclasses.identity_bearer.IdentityBearerMixin"
            "._attempt_forensic_recognition",
            return_value=True,
        ):
            self.assertEqual(
                bearer.get_display_name(looker), "moderate thing (Alice)"
            )

    def test_forensic_recovery_on_fail(self):
        """Degraded UID misses, fresh UID hits, Intellect roll fails."""
        bearer = _FakeBearer(
            stage="moderate", decay_label="moderate thing",
        )
        looker = _FakeLooker(
            memory={"uid-A": {"assigned_name": "Alice"}},
        )
        with patch(
            "world.identity.get_apparent_uid_for_decay",
            return_value="uid-degraded",
        ), patch(
            "world.identity.get_apparent_uid", return_value="uid-A",
        ), patch(
            "typeclasses.identity_bearer.IdentityBearerMixin"
            "._attempt_forensic_recognition",
            return_value=False,
        ):
            self.assertEqual(
                bearer.get_display_name(looker), "moderate thing",
            )

    def test_forensic_dc_table_skips_undefined_stages(self):
        """Stages absent from ``_FORENSIC_RECOGNITION_DC`` never roll.

        ``fresh`` and ``early`` are deliberately omitted from the DC
        table because the degraded UID still equals the fresh UID at
        those stages — natural recognition handles them.  If forensic
        recovery is somehow reached at those stages it must return
        ``False`` without consulting the forensics engine.
        """
        bearer = _FakeBearer(stage="early")
        looker = _FakeLooker()
        # ``early`` is intentionally missing from the DC table.
        self.assertNotIn("early", bearer._FORENSIC_RECOGNITION_DC)
        with patch(
            "world.forensics.attempt_forensic_recognition",
        ) as engine:
            result = bearer._attempt_forensic_recognition(looker, "early")
        self.assertFalse(result)
        engine.assert_not_called()

    def test_apparent_uid_helper_exception_falls_through(self):
        """Helper exceptions degrade gracefully to the decay fallback.

        Mirrors the production guard against malformed signatures in
        the legacy DB — bearer rendering must never raise into the
        room broadcast pipeline.
        """
        bearer = _FakeBearer(decay_label="fresh thing")
        looker = _FakeLooker(
            memory={"uid-A": {"assigned_name": "Alice"}},
        )
        with patch(
            "world.identity.get_apparent_uid_for_decay",
            side_effect=TypeError("malformed"),
        ), patch(
            "world.identity.get_apparent_uid",
            side_effect=ValueError("malformed"),
        ):
            self.assertEqual(
                bearer.get_display_name(looker), "fresh thing",
            )
