"""Radio reports roll real units — the deterministic half.

The model half is a fixed contract (constrained decoding, proven at the
shim); these tests pin everything the game decides: the two-signal gate,
plain-code location resolution, the scene debounce, the event shape,
and the NPC no-double-dispatch guard.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.director.radio_report as rr


def _room(rid, key):
    return SimpleNamespace(id=rid, key=key)


ROOMS = [
    _room(1917, "Queen of Cups - Lobby"),
    _room(4987, "Queen of Cups - Rack 0"),
    _room(954, "Pessoa Street"),
    _room(2001, "Maxwell Medical Clinic - Waiting Room"),
    _room(3001, "Suds & Bubbles Laundromat"),
    _room(3002, "Colonial Constabulary Lobby"),
]


class TestResolveLocation(TestCase):
    def test_exact_scene_wins(self):
        room = rr.resolve_location("Rack 0 in the Queen of Cups", ROOMS)
        self.assertEqual(room.id, 4987)

    def test_partial_name_resolves(self):
        room = rr.resolve_location("the Maxwell clinic", ROOMS)
        self.assertEqual(room.id, 2001)

    def test_street_beats_weak_match(self):
        room = rr.resolve_location("laundromat on Pessoa Street", ROOMS)
        self.assertEqual(room.id, 954)

    def test_garbage_resolves_nothing(self):
        self.assertIsNone(rr.resolve_location("behind the third moon", ROOMS))
        self.assertIsNone(rr.resolve_location("", ROOMS))
        self.assertIsNone(rr.resolve_location(None, ROOMS))


class TestApplyVerdict(TestCase):
    def setUp(self):
        rr._RECENT.clear()
        self.speaker = MagicMock()
        self.speaker.location = ROOMS[0]

    def _apply(self, verdict):
        with patch.object(rr, "_candidate_rooms", return_value=ROOMS), \
             patch("world.director.dispatch.raise_event",
                   return_value=["unit"]) as raised:
            result = rr.apply_verdict(verdict, self.speaker, "traffic")
        return result, raised

    def test_confirmed_report_dispatches_to_named_room(self):
        result, raised = self._apply({
            "is_incident_report": True, "incident_type": "assault",
            "location_text": "Rack 0 in the Queen of Cups"})
        self.assertEqual(result, ["unit"])
        event = raised.call_args.args[0]
        self.assertEqual(event.type, "assault")
        self.assertEqual(event.severity, 2)
        self.assertEqual(event.location.id, 4987)
        self.assertTrue(event.payload["radio_report"])

    def test_contradictory_verdict_holds(self):
        result, raised = self._apply({
            "is_incident_report": True, "incident_type": "none"})
        self.assertIsNone(result)
        raised.assert_not_called()

    def test_not_a_report_holds(self):
        result, raised = self._apply({
            "is_incident_report": False, "incident_type": "assault"})
        raised.assert_not_called()

    def test_unresolvable_place_falls_back_to_caller_room(self):
        result, raised = self._apply({
            "is_incident_report": True, "incident_type": "fire",
            "location_text": "behind the third moon"})
        event = raised.call_args.args[0]
        self.assertEqual(event.location.id, 1917)
        self.assertEqual(event.type, "fire")

    def test_scene_debounce(self):
        self._apply({"is_incident_report": True,
                     "incident_type": "disturbance",
                     "location_text": "Pessoa Street"})
        result, raised = self._apply({
            "is_incident_report": True, "incident_type": "disturbance",
            "location_text": "Pessoa Street"})
        self.assertIsNone(result)
        raised.assert_not_called()

    def test_medical_maps_to_disturbance(self):
        result, raised = self._apply({
            "is_incident_report": True, "incident_type": "medical",
            "location_text": "the Maxwell clinic"})
        event = raised.call_args.args[0]
        self.assertEqual(event.type, "disturbance")
        self.assertEqual(event.severity, 1)

    def test_malformed_verdict_is_silence(self):
        result, raised = self._apply(None)
        self.assertIsNone(result)
        raised.assert_not_called()


class TestConsiderGuards(TestCase):
    def test_npc_traffic_never_classifies(self):
        speaker = MagicMock()
        speaker.db.is_npc = True
        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict") as req:
            rr.consider_radio_report(MagicMock(), speaker, "help, assault!")
        req.assert_not_called()

    def test_player_traffic_classifies(self):
        speaker = MagicMock()
        speaker.db.is_npc = None
        speaker.db.llm_driven = None
        speaker.db.is_base_station = None
        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict") as req:
            rr.consider_radio_report(MagicMock(), speaker, "help, assault!")
        req.assert_called_once()
        self.assertEqual(req.call_args.args[2], rr.DISPATCH_VERDICT_SCHEMA)

    def test_disabled_lane_is_silence(self):
        with patch("world.llm.client.civic_enabled", return_value=False), \
             patch("world.llm.client.request_civic_verdict") as req:
            rr.consider_radio_report(MagicMock(), MagicMock(), "assault!")
        req.assert_not_called()
