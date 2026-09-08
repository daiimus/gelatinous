"""A chart step nothing is running goes back in the queue (#2510), and
the clinic still carries the side (#2511).

## #2510 — RUNNING was a one-way door

A step goes RUNNING when it is dispatched and leaves RUNNING only when
its procedure resolves, fails, or is interrupted. The procedure timer is
**not** persistent — `start_procedure` says so — and there is no medical
sweep at server start, so a reload mid-step left the step RUNNING with
nothing left to finish it.

`pending_steps` only ever returned PENDING:

```python
return [s for s in chart.get("steps", []) if s.get("status") == PENDING]
```

so the stranded step was invisible to the resume path and could never be
re-run. The surgeon re-commenced onto the step *after* it — silently
skipping, say, the incision the harvest depended on.

The second half compounds it. `_advance` identified "the step that just
finished" by scanning for the **first** RUNNING step, never consulting
`step["id"]` sitting in its own enclosing scope. That is correct only
while exactly one step is ever RUNNING, and the module's own comment
describes what makes a second one. So the stranded step absorbed the
next step's result and was marked DONE, while the step that actually ran
stayed RUNNING — and the corruption walked forward one step per reload.

Re-queued by reading the live procedure slot rather than by a boot
sweep, for the same reason `is_procedure_active` reads its deadline
against the clock (#2419): no startup hook, no migration, and a chart
wedged by a past reload frees itself the next time anyone opens it.

## #2511 — already fixed, pinned

`build_install_chart` resolved `side`, used it to compute the anchor and
then dropped it from the step. The dispatcher's only source is
`(args or {}).get("side")`, so the resolver refused every side-agnostic
chassis — including the cyber arm, the most likely thing anyone asks a
ripperdoc for — *after* the incise step had already opened the patient.
Fixed under #2692; pinned here because it is one dict key and the other
chart author (`CmdOperate`) has always passed it.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical import charts as C


class _ChartCase(EvenniaTest):
    def chart(self):
        chart = C.new_chart(self.char1)
        C.add_step(chart, "incise", {"location": "chest"})
        C.add_step(chart, "harvest",
                   {"location": "chest", "organ_name": "heart"})
        C.save_chart(self.char2, chart)
        return C.get_chart(self.char2)

    def statuses(self, chart=None):
        chart = chart or C.get_chart(self.char2)
        return [s.get("status") for s in chart.get("steps") or []]

    def strand(self, chart, index=0):
        """What a reload leaves: RUNNING, with no live procedure."""
        chart["steps"][index]["status"] = C.RUNNING
        C.save_chart(self.char2, chart)
        state = dict(getattr(self.char2.db, "surgical_state", None) or {})
        state["active_procedure"] = None
        self.char2.db.surgical_state = state
        return C.get_chart(self.char2)


class TestAStrandedStepIsRequeued(_ChartCase):
    def test_it_goes_back_to_pending(self):
        chart = self.strand(self.chart())
        C.requeue_stranded_steps(self.char2, chart)
        self.assertEqual(chart["steps"][0]["status"], C.PENDING)

    def test_it_reports_that_it_changed_something(self):
        chart = self.strand(self.chart())
        self.assertTrue(C.requeue_stranded_steps(self.char2, chart))

    def test_the_resume_path_can_see_it_again(self):
        chart = self.strand(self.chart())
        # Step 2 is still PENDING, which is the whole problem: the queue
        # was not empty, it just no longer contained the incision, so
        # `commence` resumed onto the harvest that depended on it.
        self.assertEqual([s["verb"] for s in C.pending_steps(chart)],
                         ["harvest"])
        C.requeue_stranded_steps(self.char2, chart)
        self.assertEqual([s["verb"] for s in C.pending_steps(chart)],
                         ["incise", "harvest"])

    def test_an_aborted_chart_is_live_again(self):
        chart = self.strand(self.chart())
        chart["status"] = C.ABORTED
        C.requeue_stranded_steps(self.char2, chart)
        self.assertEqual(chart["status"], C.IN_PROGRESS)

    def test_a_chart_with_nothing_running_is_untouched(self):
        chart = self.chart()
        self.assertFalse(C.requeue_stranded_steps(self.char2, chart))
        self.assertEqual(self.statuses(chart), [C.PENDING, C.PENDING])

    def test_a_done_step_is_not_resurrected(self):
        chart = self.chart()
        chart["steps"][0]["status"] = C.DONE
        self.strand(chart, index=1)
        C.requeue_stranded_steps(self.char2, chart)
        self.assertEqual(chart["steps"][0]["status"], C.DONE)

    def test_a_failed_step_is_not_resurrected(self):
        chart = self.chart()
        chart["steps"][0]["status"] = C.FAILED
        self.strand(chart, index=1)
        C.requeue_stranded_steps(self.char2, chart)
        self.assertEqual(chart["steps"][0]["status"], C.FAILED)


class TestALiveProcedureIsLeftAlone(_ChartCase):
    """The step that is genuinely running right now must not be pulled
    out from under its own timer."""

    def test_a_running_procedure_holds_its_step(self):
        import time
        chart = self.chart()
        chart["steps"][0]["status"] = C.RUNNING
        C.save_chart(self.char2, chart)
        self.char2.db.surgical_state = {
            "incisions": {},
            "active_procedure": {"verb": "incise",
                                 "started_at": time.time(),
                                 "duration_s": 600},
        }
        self.assertFalse(C.requeue_stranded_steps(self.char2, chart))
        self.assertEqual(chart["steps"][0]["status"], C.RUNNING)

    def test_an_expired_procedure_does_not(self):
        """The deadline is the same clock `is_procedure_active` reads."""
        import time
        chart = self.chart()
        chart["steps"][0]["status"] = C.RUNNING
        C.save_chart(self.char2, chart)
        self.char2.db.surgical_state = {
            "incisions": {},
            "active_procedure": {"verb": "incise",
                                 "started_at": time.time() - 9999,
                                 "duration_s": 6},
        }
        self.assertTrue(C.requeue_stranded_steps(self.char2, chart))


class TestCommenceHealsTheChartItOpens(_ChartCase):
    def test_commence_re_runs_the_stranded_step(self):
        from unittest import mock
        chart = self.strand(self.chart())
        with mock.patch("world.medical.procedures.start_procedure") as sp:
            step = C.commence_chart(self.char2, self.char1)
        self.assertIsNotNone(step)
        self.assertEqual(step.get("verb"), "incise",
                         "commence skipped the stranded incise")

    def test_it_does_not_jump_to_the_harvest(self):
        from unittest import mock
        self.strand(self.chart())
        with mock.patch("world.medical.procedures.start_procedure"):
            step = C.commence_chart(self.char2, self.char1)
        self.assertNotEqual(step.get("verb"), "harvest")


class TestTheCompletionHookClosesItsOwnStep(_ChartCase):
    """`_advance` took the FIRST running step, so with two of them the
    stranded one absorbed the live one's result."""

    def test_advance_closes_by_id_not_by_position(self):
        import inspect
        body = inspect.getsource(C.commence_chart)
        self.assertIn('step_id = step.get("id")', body)
        self.assertIn('s.get("id") != step_id', body)

    def test_steps_carry_a_stable_id(self):
        chart = self.chart()
        ids = [s.get("id") for s in chart["steps"]]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertNotIn(None, ids)


class TestTheClinicStillCarriesTheSide(EvenniaTest):
    """#2511, fixed under #2692 — one dict key, and the resolver refuses
    every side-agnostic chassis without it, AFTER the incise step has
    already opened the patient."""

    def test_the_builder_records_a_side(self):
        import inspect
        from world import clinic
        body = inspect.getsource(clinic.build_install_chart)
        self.assertIn('"side": side', body)

    def test_the_dispatcher_still_reads_it_from_args(self):
        import inspect
        body = inspect.getsource(C.commence_chart)
        self.assertIn('(args or {}).get("side")', body)
