"""The half-open breaker admits exactly one probe (#2769).

Both comments promise it: *"before one probe is let through"* and *"let
the next call through"*. Knocking `fails` down to `BREAKER_TRIP - 1` did
not deliver that — the leading `fails < BREAKER_TRIP` check then
short-circuited for every subsequent call, so the lane read healthy until
a failure was RECORDED. Failures are recorded on the errback, a full
`LLM_GM_TIMEOUT` later, so every beat firing in that window was dispatched
at a sidecar still down.
"""

from __future__ import annotations

from unittest import TestCase

from world.llm import client


class TestHalfOpenAdmitsOneProbe(TestCase):
    def setUp(self):
        client._breaker.clear()

    tearDown = setUp

    def _trip(self, lane="gm"):
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure(lane)

    def test_a_tripped_lane_is_down(self):
        self._trip()
        self.assertTrue(client._lane_down("gm"))

    def test_only_one_call_passes_after_the_cooldown(self):
        self._trip()
        client._breaker["gm"]["until"] = 0.0        # cooldown elapsed
        self.assertFalse(client._lane_down("gm"), "the probe should pass")
        # everything behind it must still be held
        for _ in range(5):
            self.assertTrue(client._lane_down("gm"),
                            "a second call slipped through the half-open")

    def test_a_failed_probe_re_arms_the_next_one(self):
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        client._lane_down("gm")                     # probe goes out
        client.note_transport_failure("gm")         # ...and fails
        client._breaker["gm"]["until"] = 0.0        # next cooldown elapsed
        self.assertFalse(client._lane_down("gm"),
                         "a later probe should be allowed")

    def test_a_successful_probe_reopens_the_lane(self):
        self._trip()
        client._breaker["gm"]["until"] = 0.0
        client._lane_down("gm")
        client.note_transport_success("gm")
        self.assertFalse(client._lane_down("gm"))
