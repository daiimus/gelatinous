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
