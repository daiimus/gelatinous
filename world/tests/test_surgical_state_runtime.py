"""Tests for the surgical-state runtime tier and chart batching.

After PR #451 the four recognition caches moved off the descriptor
hot path.  This PR extends the same idea to two more surfaces:

1. ``active_procedure`` no longer rides ``target.db.surgical_state``.
   It lives on a plain ``_runtime_active_procedure`` attribute since
   its lifetime is bounded by an in-process ``evennia_delay``
   callback that doesn't survive restart anyway.

2. Chart-runner writes batch through ``batch_chart_writes`` —
   ``commence_chart`` produces one descriptor write per step
   transition instead of three.

These tests pin both contracts against stubs (no Evennia DB).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical import charts
from world.medical import procedures as proc


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _make_target():
    """Stub target with the minimum surface the procedure / chart
    modules need: a writable ``db`` slot, a ``dbref``."""
    target = SimpleNamespace()
    target.dbref = "#42"
    target.db = SimpleNamespace(
        surgical_state=None,
        medical_chart=None,
    )
    return target


# ---------------------------------------------------------------------
# active_procedure runtime tier
# ---------------------------------------------------------------------


class TestActiveProcedureRuntime(TestCase):
    def test_get_active_procedure_defaults_to_none(self):
        target = _make_target()
        self.assertIsNone(proc.get_active_procedure(target))
        self.assertFalse(proc.is_procedure_active(target))

    def test_set_and_get_round_trips(self):
        target = _make_target()
        record = {"verb": "incise", "actor_dbref": "#1"}
        proc._set_active_procedure(target, record)
        self.assertEqual(proc.get_active_procedure(target), record)
        self.assertTrue(proc.is_procedure_active(target))

    def test_clear_removes_record(self):
        target = _make_target()
        proc._set_active_procedure(target, {"verb": "harvest"})
        proc._set_active_procedure(target, None)
        self.assertIsNone(proc.get_active_procedure(target))

    def test_surgical_state_dict_does_not_carry_active_procedure(self):
        """After the runtime move, ``surgical_state`` should NOT
        include an ``active_procedure`` key — the field lives off
        the descriptor path entirely."""
        target = _make_target()
        proc._set_active_procedure(target, {"verb": "incise"})
        state = proc._state(target)
        self.assertNotIn("active_procedure", state)


# ---------------------------------------------------------------------
# Chart write batching
# ---------------------------------------------------------------------


class TestChartBatchWrites(TestCase):
    def test_batch_collapses_multiple_writes_to_one(self):
        target = _make_target()
        chart = {"version": 1, "steps": [], "status": "draft"}

        # Spy on the underlying descriptor write — count assignments
        # to target.db.medical_chart.
        writes = []
        original_db = target.db

        class _SpyDB:
            def __getattr__(self, name):
                return getattr(original_db, name)

            def __setattr__(self, name, value):
                if name == "medical_chart":
                    writes.append(value)
                setattr(original_db, name, value)

        target.db = _SpyDB()

        with charts.batch_chart_writes(target):
            charts.save_chart(target, chart)
            chart["status"] = "in_progress"
            charts.save_chart(target, chart)
            chart["status"] = "completed"
            charts.save_chart(target, chart)

        # Three saves, one descriptor write.
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["status"], "completed")

    def test_batch_writes_outside_context_persist_immediately(self):
        target = _make_target()
        chart = {"version": 1, "steps": [], "status": "draft"}
        charts.save_chart(target, chart)
        self.assertEqual(target.db.medical_chart["status"], "draft")
        chart["status"] = "in_progress"
        charts.save_chart(target, chart)
        self.assertEqual(
            target.db.medical_chart["status"], "in_progress",
        )

    def test_nested_batches_outer_owns_flush(self):
        target = _make_target()
        chart = {"version": 1, "steps": [], "status": "draft"}
        writes = []
        original_db = target.db

        class _SpyDB:
            def __getattr__(self, name):
                return getattr(original_db, name)

            def __setattr__(self, name, value):
                if name == "medical_chart":
                    writes.append(value)
                setattr(original_db, name, value)

        target.db = _SpyDB()

        with charts.batch_chart_writes(target):
            charts.save_chart(target, chart)
            with charts.batch_chart_writes(target):
                chart["status"] = "in_progress"
                charts.save_chart(target, chart)
            # Inner context exit must not have flushed.
            self.assertEqual(len(writes), 0)
            chart["status"] = "completed"
            charts.save_chart(target, chart)
        # Outer context exit flushes once.
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["status"], "completed")

    def test_batch_target_without_dbref_falls_through(self):
        """Targets without a ``dbref`` bypass the batch path so the
        write still lands somewhere."""
        target = SimpleNamespace(
            dbref=None,
            db=SimpleNamespace(medical_chart=None),
        )
        chart = {"version": 1, "steps": [], "status": "draft"}
        with charts.batch_chart_writes(target):
            charts.save_chart(target, chart)
        # Write landed even without a batch.
        self.assertEqual(
            target.db.medical_chart["status"], "draft",
        )
