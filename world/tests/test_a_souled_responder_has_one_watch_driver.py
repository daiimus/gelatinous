"""A watch has one driver, not two (#2384 / #2385 follow-up).

`assign` already branches on who will drive the body:

    if _has_soul(npc):
        npc.db.soul_job = {... {"do": "respond"} ...}
        return True
    # An unsouled responder -- nothing in the colony currently is --
    # still gets driven the old way rather than standing there.
    started = travel_to(npc, event.location, on_arrive=_on_scene, ...)

The souls `respond` step then calls `run_arrival` once and `run_watch`
EVERY BEAT. `watch_once` was deliberately split out of the timer chain
for exactly that -- "so something else can drive it ... The behaviour is
unchanged; only who calls it, and how often, moves."

But `security_arrival` still arms the old chain on its way out:

    delay(WATCH_SECONDS, _watch_tick, npc)      # x2 branches
    delay(INVESTIGATE_SECONDS, resolve, npc)

So a souled responder -- which is every responder in the colony -- gets
BOTH. `watch_once` decrements `assignment.payload["watch_rounds"]`, so
the hold burns down at twice the intended rate, and two independent
paths decide to stand down and walk home: `_watch_tick` calls `resolve`
itself while the souls job separately advances its own step.

The timer is not deleted, because the unsouled door is still wired and
still needs it. It is armed only when nothing else will drive the
watch -- the same question `assign` already asks.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.director import security


class _Event:
    def __init__(self):
        # A real BOLO: the "high confidence" branch reads `bolo["uid"]`,
        # and an empty payload made every case raise AttributeError --
        # an ERROR, which proves nothing about the assertion.
        self.payload = {"bolo": {"uid": "u-test"}}
        self.type = "disturbance"
        self.location = None


class _Assignment:
    def __init__(self):
        self.event = _Event()
        self.payload = {}
        self.state = "on_scene"
        self.post = None


class TestOnlyOneThingDrivesTheWatch(EvenniaTest):

    def _arrive(self, souled):
        npc = self.char1
        npc.db.role = "security"
        assignment = _Assignment()
        with mock.patch.object(security, "delay") as armed, \
             mock.patch.object(security, "_mayday"), \
             mock.patch.object(security, "_cmd"), \
             mock.patch.object(security, "_aim_lock"), \
             mock.patch.object(security, "close_call_for"), \
             mock.patch.object(security, "log_local_sighting"), \
             mock.patch.object(security, "_in_combat", return_value=False), \
             mock.patch.object(security, "_scan",
                               return_value=("high", self.char2)), \
             mock.patch("world.director.assignment._has_soul",
                        return_value=souled):
            security.security_arrival(npc, assignment)
        return armed, assignment

    def test_a_souled_responder_arms_no_timer(self):
        """The souls beat calls `run_watch`; a timer would be a second
        driver burning the same `watch_rounds`."""
        armed, _a = self._arrive(souled=True)
        self.assertFalse(
            armed.called,
            "the old timer chain was armed for a soul-driven responder")

    def test_an_unsouled_responder_still_gets_its_timer(self):
        """The control, and the reason the timer is gated rather than
        deleted: the unsouled door is still wired in `assign`."""
        armed, _a = self._arrive(souled=False)
        self.assertTrue(armed.called,
                        "an unsouled responder was left with no driver")

    def test_the_hold_is_still_set_up_either_way(self):
        """Whoever drives it, the watch itself must be armed."""
        for souled in (True, False):
            _armed, assignment = self._arrive(souled=souled)
            self.assertEqual(assignment.payload.get("watch_rounds"),
                             security.WATCH_ROUNDS, f"souled={souled}")
