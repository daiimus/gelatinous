"""Tests for the surgical chart data layer (#307, PR-OP1).

The chart data layer (``world.medical.charts``) is a pure-function
surface over the ``target.db.medical_chart`` dict.  Tests here pin
the chart lifecycle, step authoring, and the rendering helpers the
``operate`` menu uses.

The EvMenu UI surface (CmdOperate.py) is tested via the live suite
since it involves Evennia's session machinery.

Run via::

    evennia test world.tests.test_operate_charts
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical import charts


def _surgeon(dbref="#42"):
    return SimpleNamespace(dbref=dbref, key="Vance")


def _target():
    """Stub target with a writable db.medical_chart slot."""
    target = SimpleNamespace()
    target.db = SimpleNamespace(medical_chart=None)
    return target


# ===================================================================
# Lifecycle
# ===================================================================


class NewChart(TestCase):

    def test_new_chart_has_canonical_fields(self):
        chart = charts.new_chart(_surgeon())
        for key in ("version", "authored_by", "authored_at",
                    "last_modified_at", "status", "next_step_id",
                    "steps"):
            with self.subTest(key=key):
                self.assertIn(key, chart)

    def test_new_chart_starts_in_draft(self):
        chart = charts.new_chart(_surgeon())
        self.assertEqual(chart["status"], charts.DRAFT)

    def test_new_chart_has_empty_steps(self):
        self.assertEqual(charts.new_chart(_surgeon())["steps"], [])

    def test_new_chart_captures_surgeon_dbref(self):
        chart = charts.new_chart(_surgeon(dbref="#99"))
        self.assertEqual(chart["authored_by"], "#99")

    def test_new_chart_step_id_starts_at_one(self):
        self.assertEqual(charts.new_chart(_surgeon())["next_step_id"], 1)


class ChartPersistence(TestCase):

    def test_save_and_get_round_trip(self):
        target = _target()
        chart = charts.new_chart(_surgeon())
        charts.save_chart(target, chart)
        restored = charts.get_chart(target)
        self.assertEqual(restored["status"], charts.DRAFT)
        self.assertEqual(restored["authored_by"], "#42")

    def test_get_chart_none_when_absent(self):
        self.assertIsNone(charts.get_chart(_target()))

    def test_save_updates_last_modified(self):
        target = _target()
        chart = charts.new_chart(_surgeon())
        original = chart["last_modified_at"]
        chart["status"] = charts.IN_PROGRESS
        # Bump the timestamp to a later value so the assertion is
        # robust against same-second saves.
        chart["last_modified_at"] = original - 1
        charts.save_chart(target, chart)
        self.assertGreater(
            charts.get_chart(target)["last_modified_at"], original - 1
        )

    def test_discard_removes_chart(self):
        target = _target()
        charts.save_chart(target, charts.new_chart(_surgeon()))
        charts.discard_chart(target)
        self.assertIsNone(charts.get_chart(target))


# ===================================================================
# Step authoring
# ===================================================================


class AddStep(TestCase):

    def _chart(self):
        return charts.new_chart(_surgeon())

    def test_appends_incise_step(self):
        chart = self._chart()
        step = charts.add_step(chart, "incise", {"location": "chest"})
        self.assertEqual(step["verb"], "incise")
        self.assertEqual(step["args"]["location"], "chest")
        self.assertEqual(step["status"], charts.PENDING)
        self.assertEqual(len(chart["steps"]), 1)

    def test_assigns_sequential_step_ids(self):
        chart = self._chart()
        s1 = charts.add_step(chart, "incise", {"location": "chest"})
        s2 = charts.add_step(chart, "harvest", {"organ_name": "heart"})
        self.assertEqual(s1["id"], 1)
        self.assertEqual(s2["id"], 2)

    def test_next_step_id_advances(self):
        chart = self._chart()
        charts.add_step(chart, "incise", {"location": "chest"})
        self.assertEqual(chart["next_step_id"], 2)

    def test_unknown_verb_raises(self):
        chart = self._chart()
        with self.assertRaises(ValueError):
            charts.add_step(chart, "nonsense", {})

    def test_missing_required_arg_raises(self):
        chart = self._chart()
        with self.assertRaises(ValueError):
            charts.add_step(chart, "incise", {})

    def test_install_requires_both_args(self):
        chart = self._chart()
        with self.assertRaises(ValueError):
            charts.add_step(chart, "install", {"location": "chest"})
        with self.assertRaises(ValueError):
            charts.add_step(chart, "install",
                            {"organ_item_key": "heart"})

    def test_suture_has_no_required_args(self):
        chart = self._chart()
        step = charts.add_step(chart, "suture", {})
        self.assertEqual(step["verb"], "suture")
        self.assertEqual(step["args"], {})


class RemoveStep(TestCase):

    def _chart_with_two(self):
        chart = charts.new_chart(_surgeon())
        charts.add_step(chart, "incise", {"location": "chest"})
        charts.add_step(chart, "harvest", {"organ_name": "heart"})
        return chart

    def test_remove_by_id(self):
        chart = self._chart_with_two()
        self.assertTrue(charts.remove_step(chart, 1))
        ids = [s["id"] for s in chart["steps"]]
        self.assertEqual(ids, [2])

    def test_remove_unknown_id_returns_false(self):
        chart = self._chart_with_two()
        self.assertFalse(charts.remove_step(chart, 999))
        self.assertEqual(len(chart["steps"]), 2)

    def test_next_step_id_not_rewound_after_remove(self):
        """Removing the last step doesn't decrement next_step_id —
        prevents id collisions if a step is re-added."""
        chart = self._chart_with_two()
        original_next = chart["next_step_id"]
        charts.remove_step(chart, 2)
        self.assertEqual(chart["next_step_id"], original_next)


class FindStep(TestCase):

    def test_find_existing(self):
        chart = charts.new_chart(_surgeon())
        added = charts.add_step(chart, "suture", {})
        found = charts.find_step(chart, added["id"])
        self.assertIs(found, added)

    def test_find_missing_returns_none(self):
        self.assertIsNone(
            charts.find_step(charts.new_chart(_surgeon()), 99)
        )


# ===================================================================
# Summary helpers
# ===================================================================


class PendingSteps(TestCase):

    def test_only_pending_returned(self):
        chart = charts.new_chart(_surgeon())
        s1 = charts.add_step(chart, "incise", {"location": "chest"})
        s2 = charts.add_step(chart, "harvest", {"organ_name": "heart"})
        s3 = charts.add_step(chart, "suture", {})
        s1["status"] = charts.DONE
        s2["status"] = charts.FAILED
        pending = charts.pending_steps(chart)
        self.assertEqual(pending, [s3])

    def test_empty_chart_empty_pending(self):
        self.assertEqual(
            charts.pending_steps(charts.new_chart(_surgeon())),
            [],
        )


class IsChartComplete(TestCase):

    def _chart_with_step_at(self, status):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "incise", {"location": "chest"})
        step["status"] = status
        return chart

    def test_empty_chart_is_complete(self):
        # No steps → vacuously complete.
        self.assertTrue(
            charts.is_chart_complete(charts.new_chart(_surgeon()))
        )

    def test_done_step_complete(self):
        self.assertTrue(
            charts.is_chart_complete(self._chart_with_step_at(charts.DONE))
        )

    def test_pending_step_incomplete(self):
        self.assertFalse(
            charts.is_chart_complete(
                self._chart_with_step_at(charts.PENDING)
            )
        )

    def test_mixed_failed_and_done_complete(self):
        chart = charts.new_chart(_surgeon())
        s1 = charts.add_step(chart, "incise", {"location": "chest"})
        s2 = charts.add_step(chart, "harvest", {"organ_name": "heart"})
        s1["status"] = charts.DONE
        s2["status"] = charts.FAILED
        self.assertTrue(charts.is_chart_complete(chart))


# ===================================================================
# Step rendering
# ===================================================================


class RenderStepSummary(TestCase):

    def test_incise_renders_location(self):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "incise", {"location": "chest"})
        self.assertEqual(charts.render_step_summary(step), "incise chest")

    def test_harvest_humanizes_organ(self):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "harvest",
                               {"organ_name": "left_lung"})
        self.assertEqual(
            charts.render_step_summary(step), "harvest left lung"
        )

    def test_install_renders_organ_and_location(self):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "install",
                               {"organ_item_key": "donor heart",
                                "location": "chest"})
        self.assertEqual(
            charts.render_step_summary(step),
            "install donor heart in chest",
        )

    def test_suture_without_location_says_all(self):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "suture", {})
        self.assertEqual(charts.render_step_summary(step), "suture all")

    def test_suture_with_location(self):
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "suture", {"location": "chest"})
        self.assertEqual(
            charts.render_step_summary(step), "suture chest"
        )


# ===================================================================
# Roman numeral helper (used by the UI render)
# ===================================================================


class RomanHelper(TestCase):
    """The renderer's Roman-numeral helper is imported from
    CmdOperate; pin a few key conversions so cosmetic regressions
    surface."""

    def test_basic_conversions(self):
        from commands.CmdOperate import _roman
        for n, r in [
            (1, "I"), (2, "II"), (3, "III"), (4, "IV"), (5, "V"),
            (6, "VI"), (9, "IX"), (10, "X"), (14, "XIV"), (50, "L"),
        ]:
            with self.subTest(n=n):
                self.assertEqual(_roman(n), r)


# ===================================================================
# commence_chart runner — auto-chain pending steps
# ===================================================================


class CommenceChartRunner(TestCase):
    """The chart runner dispatches the first pending step via
    ``start_procedure`` with an ``on_complete`` hook that advances
    to the next step.  Tests stub ``start_procedure`` so the
    procedure dispatch isn't exercised — we just verify the chain
    bookkeeping."""

    def _chart_target_with_steps(self, *verb_args):
        target = _target()
        # Stub a snapshot so harvest args can resolve cleanly —
        # ``_resolve_step_args`` reads it to find each organ's
        # container.  Heart at chest is enough to cover the
        # tests in this class.
        target.get_medical_snapshot = lambda: {
            "organs": {
                "heart": {
                    "container": "chest", "display_location": "chest",
                },
            },
        }
        chart = charts.new_chart(_surgeon())
        for verb, args in verb_args:
            charts.add_step(chart, verb, args)
        charts.save_chart(target, chart)
        return target

    def _patch_start(self, calls):
        """Patch start_procedure to capture calls and remember the
        on_complete hook for manual invocation."""
        from unittest.mock import patch

        def _fake(target, *, verb, actor, on_complete=None, **kwargs):
            calls.append({
                "target": target, "verb": verb, "actor": actor,
                "on_complete": on_complete, "kwargs": kwargs,
            })
        return patch("world.medical.procedures.start_procedure", _fake)

    def test_empty_chart_returns_none(self):
        target = _target()
        charts.save_chart(target, charts.new_chart(_surgeon()))
        self.assertIsNone(charts.commence_chart(target, _surgeon()))

    def test_no_chart_returns_none(self):
        target = _target()
        self.assertIsNone(charts.commence_chart(target, _surgeon()))

    def test_dispatches_first_pending_step(self):
        target = self._chart_target_with_steps(
            ("incise", {"location": "chest"}),
            ("harvest", {"organ_name": "heart"}),
        )
        calls = []
        with self._patch_start(calls):
            step = charts.commence_chart(target, _surgeon())
        self.assertEqual(step["verb"], "incise")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["verb"], "incise")
        self.assertEqual(calls[0]["kwargs"], {"location": "chest"})

    def test_dispatched_step_marked_running(self):
        target = self._chart_target_with_steps(
            ("incise", {"location": "chest"}),
        )
        calls = []
        with self._patch_start(calls):
            charts.commence_chart(target, _surgeon())
        chart = charts.get_chart(target)
        self.assertEqual(chart["steps"][0]["status"], charts.RUNNING)
        self.assertEqual(chart["status"], charts.IN_PROGRESS)

    def test_on_complete_advances_to_next_step(self):
        target = self._chart_target_with_steps(
            ("incise", {"location": "chest"}),
            ("harvest", {"organ_name": "heart"}),
        )
        calls = []
        with self._patch_start(calls):
            charts.commence_chart(target, _surgeon())
            # Simulate the procedure finishing — invoke the hook.
            hook = calls[0]["on_complete"]
            self.assertIsNotNone(hook)
            hook(target, _surgeon())

        # First step done; second step dispatched.
        chart = charts.get_chart(target)
        self.assertEqual(chart["steps"][0]["status"], charts.DONE)
        self.assertEqual(chart["steps"][1]["status"], charts.RUNNING)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["verb"], "harvest")

    def test_chain_completes_chart_after_last_step(self):
        target = self._chart_target_with_steps(
            ("incise", {"location": "chest"}),
        )
        calls = []
        with self._patch_start(calls):
            charts.commence_chart(target, _surgeon())
            calls[0]["on_complete"](target, _surgeon())

        chart = charts.get_chart(target)
        self.assertEqual(chart["status"], charts.COMPLETED)
        self.assertEqual(chart["steps"][0]["status"], charts.DONE)

    def test_treatment_verbs_skip_and_advance(self):
        """``apply`` / ``inject`` aren't dispatchable yet — the
        runner skips them and continues to the next step."""
        target = _target()
        chart = charts.new_chart(_surgeon())
        charts.add_step(chart, "apply",
                        {"item_key": "gauze", "location": "chest"})
        charts.add_step(chart, "incise", {"location": "chest"})
        charts.save_chart(target, chart)
        calls = []
        with self._patch_start(calls):
            step = charts.commence_chart(target, _surgeon())

        # The treatment step is skipped; incise is dispatched.
        chart = charts.get_chart(target)
        self.assertEqual(chart["steps"][0]["status"], charts.SKIPPED)
        self.assertEqual(chart["steps"][1]["status"], charts.RUNNING)
        self.assertEqual(step["verb"], "incise")
        self.assertEqual(len(calls), 1)


# ===================================================================
# Interrupt path
# ===================================================================


class ResolveStepArgs(TestCase):
    """The chart stores user-typed intent (e.g.
    ``{"organ_name": "heart"}``) but the resolvers want richer
    kwargs (``organ_name`` + ``location`` for harvest, an actual
    item object for install).  ``_resolve_step_args`` translates
    chart args to resolver kwargs at dispatch time.

    This was the failure mode that broke auto-chaining in the
    initial PR-OP1.1 ship — without the translation, harvest's
    resolver raised TypeError ('missing required keyword argument
    location') inside the procedure callback, the exception killed
    the callback before the on_complete hook fired, and the chain
    died silently.
    """

    def test_incise_passes_location_through(self):
        from world.medical.charts import _resolve_step_args
        result = _resolve_step_args(
            "incise", {"location": "chest"}, target=None, actor=None,
        )
        self.assertEqual(result, {"location": "chest"})

    def test_harvest_resolves_container_from_snapshot(self):
        from world.medical.charts import _resolve_step_args
        target = SimpleNamespace()
        target.get_medical_snapshot = lambda: {
            "organs": {
                "heart": {
                    "container": "chest",
                    "display_location": "chest",
                },
            },
        }
        result = _resolve_step_args(
            "harvest", {"organ_name": "heart"},
            target=target, actor=None,
        )
        self.assertEqual(
            result, {"organ_name": "heart", "location": "chest"}
        )

    def test_harvest_missing_organ_raises(self):
        from world.medical.charts import (
            _resolve_step_args, _StepResolutionError,
        )
        target = SimpleNamespace()
        target.get_medical_snapshot = lambda: {"organs": {}}
        with self.assertRaises(_StepResolutionError):
            _resolve_step_args(
                "harvest", {"organ_name": "ghost_organ"},
                target=target, actor=None,
            )

    def test_install_finds_organ_item_in_actor_inventory(self):
        from world.medical.charts import _resolve_step_args
        donor = SimpleNamespace(key="donor heart")
        actor = SimpleNamespace(contents=[donor])
        result = _resolve_step_args(
            "install",
            {"organ_item_key": "heart", "location": "chest"},
            target=None, actor=actor,
        )
        self.assertEqual(result["location"], "chest")
        self.assertIs(result["organ_item"], donor)

    def test_install_missing_donor_raises(self):
        from world.medical.charts import (
            _resolve_step_args, _StepResolutionError,
        )
        actor = SimpleNamespace(contents=[])
        with self.assertRaises(_StepResolutionError):
            _resolve_step_args(
                "install",
                {"organ_item_key": "heart", "location": "chest"},
                target=None, actor=actor,
            )

    def test_suture_with_location_passes_through(self):
        from world.medical.charts import _resolve_step_args
        result = _resolve_step_args(
            "suture", {"location": "chest"},
            target=None, actor=None,
        )
        self.assertEqual(result, {"location": "chest"})

    def test_suture_without_location_returns_empty(self):
        from world.medical.charts import _resolve_step_args
        result = _resolve_step_args(
            "suture", {}, target=None, actor=None,
        )
        self.assertEqual(result, {})


class InterruptMarksRunningStepFailed(TestCase):
    """``interrupt_procedure`` should mark any RUNNING chart step
    as FAILED with outcome ``"interrupted"`` so the surgeon can
    see why the chain halted on re-entry to ``operate``."""

    def test_interrupt_marks_running_step_failed(self):
        from world.medical.procedures import interrupt_procedure

        target = _target()
        target.dbref = "#5000"
        target.db.surgical_state = {
            "active_procedure": {
                "verb": "incise",
                "actor_dbref": "#42",
                "started_at": 0.0,
                "duration_s": 6,
                "kwargs": {"location": "chest"},
            },
            "incisions": [],
        }
        chart = charts.new_chart(_surgeon())
        step = charts.add_step(chart, "incise", {"location": "chest"})
        step["status"] = charts.RUNNING
        chart["status"] = charts.IN_PROGRESS
        charts.save_chart(target, chart)

        interrupt_procedure(target, reason="combat")

        latest = charts.get_chart(target)
        self.assertEqual(latest["steps"][0]["status"], charts.FAILED)
        self.assertIn("interrupted", latest["steps"][0]["outcome"])
        self.assertEqual(latest["status"], charts.ABORTED)

    def test_interrupt_no_chart_doesnt_explode(self):
        from world.medical.procedures import interrupt_procedure
        target = _target()
        target.dbref = "#5001"
        target.db.surgical_state = {
            "active_procedure": None,
            "incisions": [],
        }
        # No chart on target — should no-op cleanly.
        interrupt_procedure(target, reason="combat")
