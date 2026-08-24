"""Phase 3: a call gets settled (#2256).

A responder finding nothing had nowhere to say so. A false report cost
the colony two units and left NO trace — nothing to answer for, nothing
to hold against a caller, and nothing for a dispatcher to know about an
hour later when somebody asked.

Calls could be opened and rolled since #2246; closing them is the half
that gives a bad call a consequence.

Units already announce themselves when they roll, so they announce the
finding too — deterministic, in the unit's own voice, through the real
verb. That is the play-by-play.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import calls as calls_mod
from world.director.security import close_call_for


class _Assignment:
    def __init__(self, event):
        self.event = event
        self.payload = {}


class _Event:
    def __init__(self, call_id, location):
        self.payload = {"call_id": call_id} if call_id else {}
        self.location = location


class TestSettlingACall(EvenniaCommandTest):
    def _call(self):
        return calls_mod.open_call(said="a tall guy is stabbing someone",
                                   kind="assault", room=self.room1,
                                   caller=self.char1)

    def test_finding_nothing_marks_it_unfounded(self):
        """The first consequence a false report has ever had."""
        call = self._call()
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd"):
            close_call_for(a, "unfounded", self.char2)
        self.assertEqual(calls_mod.get_call(call["id"])["status"],
                         "unfounded")

    def test_a_hold_marks_it_detained(self):
        call = self._call()
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd"):
            close_call_for(a, "detained", self.char2)
        self.assertEqual(calls_mod.get_call(call["id"])["status"],
                         "detained")

    def test_a_closed_call_leaves_the_open_list(self):
        call = self._call()
        self.assertIn(call["id"], [c["id"] for c in calls_mod.open_calls()])
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd"):
            close_call_for(a, "unfounded", self.char2)
        self.assertNotIn(call["id"],
                         [c["id"] for c in calls_mod.open_calls()])

    def test_it_records_who_settled_it(self):
        call = self._call()
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd"):
            close_call_for(a, "unfounded", self.char2)
        self.assertEqual(calls_mod.get_call(call["id"])["closed_by"],
                         self.char2.key)


class TestThePlayByPlay(EvenniaCommandTest):
    def test_the_unit_reports_the_finding_on_the_band(self):
        call = calls_mod.open_call(said="help", kind="assault",
                                   room=self.room1)
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd") as ran:
            close_call_for(a, "unfounded", self.char2)
        said = " ".join(str(c) for c in ran.call_args_list)
        self.assertIn("xmit", said)
        self.assertIn("Nothing here matching the report", said)
        self.assertIn(self.room1.key, said)

    def test_it_uses_the_real_verb(self):
        """Same discipline as the responding ack: its own comms, its own
        voice, and a wrecked transceiver means silence."""
        call = calls_mod.open_call(said="help", kind="fire", room=self.room1)
        a = _Assignment(_Event(call["id"], self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd") as ran:
            close_call_for(a, "detained", self.char2)
        self.assertTrue(str(ran.call_args_list[0]).strip().find("xmit") > 0)


class TestWhatIsNotACall(EvenniaCommandTest):
    def test_a_witnessed_crime_closes_nothing(self):
        """Only PHONED-IN incidents carry a call id. A crime somebody
        saw is not a call, and closing one would invent a caller who
        never rang."""
        a = _Assignment(_Event(None, self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd") as ran:
            close_call_for(a, "unfounded", self.char2)
        ran.assert_not_called()

    def test_an_unknown_call_id_says_nothing(self):
        a = _Assignment(_Event(999999, self.room1))
        with mock.patch.object(type(self.char2), "execute_cmd") as ran:
            close_call_for(a, "unfounded", self.char2)
        ran.assert_not_called()
