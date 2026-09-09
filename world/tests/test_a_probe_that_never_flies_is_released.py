"""A claimed breaker probe cannot strand the lane forever (#2849).

#2849 made `_lane_down` let exactly ONE probe through per cooldown, by
claiming it as a side effect of being asked:

    if monotonic() >= state["until"]:
        state["probing"] = True
        return False
    ...
    if state.get("probing"):
        return True              # a probe is already in flight

The claim is only ever released by a TRANSPORT RESULT --
`note_transport_success` or `note_transport_failure`. So the design
assumes every caller that asks goes on to dispatch a request.

Three callers in `typeclasses/llm_npc.py` do not:

    :79   if (kwargs.get("addressed") and llm_enabled()
              and not self._is_npc_speaker(speaker)):
    :87   if self.db.llm_driven and llm_enabled():      # then `_classify_speech`
                                                       # may match neither branch
    :261  if not llm_enabled() or self._is_npc_speaker(speaker):

Python evaluates left to right, so `llm_enabled()` is called -- claiming
the probe -- and the condition then short-circuits on the NEXT term
without anything being sent. NPC-to-NPC speech is constant with 78
souled NPCs, so this is the common case, not the corner.

Nothing then releases the claim. `_lane_down` returns True for every
subsequent call, no further probe is ever allowed, and the lane stays
dark until the server restarts (`_breaker` is module state).

So one transient sidecar blip could take the LLM off for the rest of
the process's life, and the half-open logic that exists to heal it is
what holds it down.

Fixed by giving the claim a DEADLINE rather than by making the callers
promise to dispatch -- a promise the call sites cannot be made to keep,
since `llm_enabled()` is a question and any future caller may ask it
without sending. A probe that has not reported back within the request
timeout is treated as lost and the next one is allowed through, which
preserves #2849's "exactly one in flight" for every probe that really
is in flight.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.llm import client


class TestAStrandedProbeDoesNotHoldTheLaneDown(EvenniaTest):

    def setUp(self):
        super().setUp()
        client._breaker.clear()
        self.addCleanup(client._breaker.clear)

    def _trip(self, lane="gm"):
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure(lane)

    def test_the_breaker_trips(self):
        """Control: without this, every assertion below is vacuous."""
        self._trip()
        self.assertTrue(client._lane_down("gm"))

    def test_one_probe_is_let_through_after_the_cooldown(self):
        """Control: #2849's behaviour, unchanged."""
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        self.assertFalse(client._lane_down("gm"))   # the probe
        self.assertTrue(client._lane_down("gm"))    # and only one

    def test_a_probe_that_never_reports_back_is_eventually_released(self):
        """THE BUG. The probe is claimed by a caller that then does not
        dispatch, so no transport result ever arrives.

        Driven by moving the CLOCK rather than by calling any new
        helper: the first version of this test referenced a function the
        fix had not added yet and raised AttributeError, which is an
        ERROR and proves nothing about the assertion.
        """
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        self.assertFalse(client._lane_down("gm"))   # claimed, never flown

        import time as _time
        real = _time.monotonic
        with mock.patch("time.monotonic", lambda: real() + 3600.0):
            self.assertFalse(
                client._lane_down("gm"),
                "a probe nobody ever flew held the lane down forever")

    def test_a_probe_still_in_flight_is_not_released_early(self):
        """The other half: the deadline must not defeat #2849. No clock
        movement here, so the claim is still fresh."""
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        self.assertFalse(client._lane_down("gm"))
        self.assertTrue(client._lane_down("gm"),
                        "a probe in flight stopped blocking the next one")

    def test_a_real_result_still_clears_the_claim(self):
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        self.assertFalse(client._lane_down("gm"))
        client.note_transport_success("gm")
        self.assertFalse(client._lane_down("gm"))
