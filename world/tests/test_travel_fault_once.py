"""One fault per travel failure, not two (#2720).

`travel_to` signals a no-route through BOTH channels -- it invokes
`on_fail` and returns False -- and the souls caller acted on both, so
every no-route event faulted twice.

That is not only log noise. `fault()` appends to `soul_faults`, which
keeps only the last few entries per soul, so one failure consumed two
slots and the fault history held half the real information it appeared
to. The audit log showed the pairing exactly: 137 `travel_to_..._failed`
against 136 `no_path_to_...` for one unreachable apartment.

The `travel_to` contract itself is authored and tested elsewhere
(`test_director_dispatch` asserts it returns False AND calls on_fail),
so the fix belongs in the caller.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import jobs


class TestOneFaultPerFailure(EvenniaCommandTest):
    def _run_travel_step(self, travel_returns, calls_on_fail):
        """Drive the 'travel' branch of step_job with a stubbed
        travel_to, and count the faults it produces."""
        soul = self.char1
        room = self.room2
        soul.db.soul_job = {
            "goal": "test", "at": 0,
            "steps": [{"do": "travel", "room": room.id}],
        }

        def fake_travel(npc, dest, on_arrive=None, on_fail=None,
                        step_delay=None):
            if calls_on_fail and on_fail:
                npc.ndb.travel_fail_why = "no route from Somewhere at all"
                on_fail(npc)
            return travel_returns

        with mock.patch.object(jobs, "travel_to", side_effect=fake_travel), \
             mock.patch.object(jobs, "is_travelling", return_value=False), \
             mock.patch.object(jobs, "fault") as fault:
            jobs.step_job(soul)
        return fault

    def test_a_no_route_failure_faults_once(self):
        """travel_to invoked on_fail AND returned False; both were acted
        on. This is the shape that produced the duplicate log pairs."""
        fault = self._run_travel_step(travel_returns=False,
                                      calls_on_fail=True)
        self.assertEqual(fault.call_count, 1,
                         f"faulted {fault.call_count}x for one failure")

    def test_the_surviving_fault_carries_the_real_reason(self):
        """Of the two messages, the on_fail one names what travel
        actually found; the caller's generic one does not. The right one
        has to be the survivor (#2321)."""
        fault = self._run_travel_step(travel_returns=False,
                                      calls_on_fail=True)
        msg = fault.call_args.args[1]
        self.assertIn("no route from", msg)

    def test_a_failure_with_no_callback_is_still_recorded(self):
        """The pin: travel_to also returns False WITHOUT calling on_fail
        (a None argument). Deleting the caller's fault outright would
        have made that case silent."""
        fault = self._run_travel_step(travel_returns=False,
                                      calls_on_fail=False)
        self.assertEqual(fault.call_count, 1,
                         "a silent failure went unrecorded")

    def test_a_successful_departure_does_not_fault(self):
        fault = self._run_travel_step(travel_returns=True,
                                      calls_on_fail=False)
        self.assertEqual(fault.call_count, 0)
