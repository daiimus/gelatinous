"""A dead sidecar must behave like a switched-off one (#2358).

"Enabled but dead" was the worst state the game could be in. Switched
OFF it is clean and instant — every gated path takes its scripted
branch. Switched ON with nothing listening, every path took the LLM
branch, `_try_llm_reply` reported the path as TAKEN so the caller
suppressed its scripted line, and the only thing that ever spoke was the
failure callback, after the full `LLM_GM_TIMEOUT`. Two minutes of a
bartender staring at you, per turn, per NPC.
"""

from unittest import mock

from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest

from world.llm import client


class _BreakerTest(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        client._breaker.clear()

    def tearDown(self):
        client._breaker.clear()
        super().tearDown()


@override_settings(LLM_GM_ENABLED=True, CIVIC_LLM_ENABLED=True)
class TestTheBreaker(_BreakerTest):

    def test_a_healthy_lane_is_enabled(self):
        self.assertTrue(client.llm_enabled())

    def test_one_blip_does_not_trip_it(self):
        """A single timeout is a slow turn, not a dead backend."""
        client.note_transport_failure("gm")
        self.assertTrue(client.llm_enabled())

    def test_repeated_unreachability_reads_as_off(self):
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure("gm")
        self.assertFalse(client.llm_enabled())

    def test_it_half_opens_after_the_cooldown(self):
        """The lane heals itself — nothing has to notice and reset it."""
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure("gm")
        self.assertFalse(client.llm_enabled())
        with mock.patch("time.monotonic",
                        return_value=client._breaker["gm"]["until"] + 1):
            self.assertTrue(client.llm_enabled())

    def test_a_success_clears_it(self):
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure("gm")
        client.note_transport_success("gm")
        self.assertTrue(client.llm_enabled())

    def test_the_lanes_are_independent(self):
        """The civic lane is a different process on a different port; one
        dying must not mute the other."""
        for _ in range(client.BREAKER_TRIP):
            client.note_transport_failure("gm")
        self.assertFalse(client.llm_enabled())
        self.assertTrue(client.civic_enabled())

    def test_an_empty_turn_does_not_trip_it(self):
        """A truncated turn means the backend is ALIVE and the prompt is
        wrong — a different problem, and taking the lane down for it
        would hide the real one."""
        client.note_transport_success("gm")
        self.assertTrue(client.llm_enabled())


@override_settings(LLM_GM_ENABLED=False)
class TestTheSwitchStillWins(_BreakerTest):

    def test_off_is_off_however_healthy(self):
        client.note_transport_success("gm")
        self.assertFalse(client.llm_enabled())
