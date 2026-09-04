"""Radio reports roll real units — the deterministic half.

The model half is a fixed contract (constrained decoding, proven at the
shim); these tests pin everything the game decides: the two-signal gate,
plain-code location resolution, the scene debounce, the event shape,
and the NPC no-double-dispatch guard.

The console's reply-sanitation suites lived here too, and went with the
console (#2228). Where each guard ended up:

* **phantom units** and **promising to leave the desk** were dispatch
  SEMANTICS, not formatting — they are `world.director.dispatch.
  desk_discipline` now, pinned in `test_director_dispatch`, and apply
  to whoever holds the chair.
* **stutter collapse, label scrubbing, scaffolding echo** were
  compensating for a RAW COMPLETION. The operator's own lane is
  schema-constrained: the model returns a `speech` field, not a line
  of prose that might arrive wearing "Petra:" or a `[CONTEXT]` header.
  The failure mode they guarded no longer has a path.
* **the parrot guards** — `is_echo` already runs on every NPC turn
  (`llm_npc._agentic_round`). The short-noun variant was chatter-lane
  specific and is not reimplemented; if parroting resurfaces on the
  band it belongs with the other desk discipline, not here.
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
    # possessive and single-word venues: the two shapes this module has
    # historically got wrong in OPPOSITE directions (see the class below)
    _room(1452, "Riveter's Way"),
    _room(5001, "The Kettle - Entrance"),
    _room(5002, "Rack 3"),
]


class TestVenueNaming(TestCase):
    """`_room_named_in` must name a venue ONLY when one was named.

    This module has failed both ways and the fixes chase each other, so
    both directions are pinned here together — changing one must not
    silently reopen the other.

    * **#2240** — a two-token guard, added to stop "in the street"
      pinning a street, swallowed every single-word venue in the colony
      (the Kettle, the Halcyon, Ramirez). Removed.
    * **#2764** — with the guard gone, the tokeniser's bare ``s`` from
      a possessive ("there's") matched the ``s`` in any apostrophe-s
      room name, so ordinary speech pinned an unrelated room — and
      OVERRODE a location the caller had actually given.
    """

    # --- must NOT name a venue: nobody said a place ------------------
    def test_contraction_names_no_venue(self):
        for said in ("there's a fight", "he's stabbing someone",
                     "somebody's down", "it's bad, hurry"):
            with self.subTest(said=said):
                self.assertEqual(rr._room_named_in(said, ROOMS), "")

    def test_bare_digit_names_no_venue(self):
        for said in ("3 of them", "two down", "level 5 now"):
            with self.subTest(said=said):
                self.assertEqual(rr._room_named_in(said, ROOMS), "")

    def test_stated_location_is_not_overridden(self):
        # the #2764 headline: a contraction must not beat a real venue
        self.assertEqual(
            rr._room_named_in("there's a fight at the Kettle", ROOMS),
            "The Kettle - Entrance",
        )

    # --- must STILL name a venue: the #2240 direction ----------------
    def test_single_word_venue_still_resolves(self):
        self.assertEqual(
            rr._room_named_in("fight at the Kettle", ROOMS),
            "The Kettle - Entrance",
        )

    def test_possessive_venue_still_resolves(self):
        # the room whose name caused #2764 must remain reachable when
        # somebody actually means it
        self.assertEqual(
            rr._room_named_in("trouble on Riveter's Way", ROOMS),
            "Riveter's Way",
        )

    def test_multiword_venue_still_resolves(self):
        self.assertEqual(
            rr._room_named_in("outside the laundromat", ROOMS),
            "Suds & Bubbles Laundromat",
        )


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
        """Traffic the DETERMINISTIC layer can't read goes to the model.
        (It has to be genuinely unreadable now — "help, assault!" is
        plain code's business since #2238.)"""
        speaker = MagicMock()
        speaker.db.is_npc = None
        speaker.db.llm_driven = None
        speaker.db.is_base_station = None
        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict") as req:
            rr.consider_radio_report(
                MagicMock(), speaker,
                "there's a fella acting the maggot outside the Shell")
        req.assert_called_once()
        self.assertEqual(req.call_args.args[2], rr.DISPATCH_VERDICT_SCHEMA)

    def test_words_it_knows_never_reach_the_model(self):
        """Deterministic FIRST: the model is a refiner, not the gate."""
        speaker = MagicMock()
        speaker.db.is_npc = None
        speaker.db.llm_driven = None
        speaker.db.is_base_station = None
        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict") as req, \
             patch.object(rr, "apply_verdict", return_value=[]):
            rr.consider_radio_report(MagicMock(), speaker,
                                     "Being assaulted on Pessoa Street!")
        req.assert_not_called()

    def test_disabled_lane_is_silence(self):
        with patch("world.llm.client.civic_enabled", return_value=False), \
             patch("world.llm.client.request_civic_verdict") as req:
            rr.consider_radio_report(MagicMock(), MagicMock(), "assault!")
        req.assert_not_called()


class TestConsiderOnResult(TestCase):
    """consider_radio_report reports its finding back for grounding."""

    def _speaker(self):
        speaker = MagicMock()
        speaker.db.is_npc = None
        speaker.db.llm_driven = None
        speaker.db.is_base_station = None
        return speaker

    def test_on_result_receives_verdict_and_dispatched(self):
        verdict = {"is_incident_report": True, "incident_type": "assault",
                   "location_text": "Rack 0"}
        results = []

        def fake_request(instructions, prompt, schema, on_verdict, on_fail):
            on_verdict(verdict)

        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict",
                   side_effect=fake_request), \
             patch.object(rr, "apply_verdict",
                          return_value=["unit"]) as applied:
            in_flight = rr.consider_radio_report(
                MagicMock(), self._speaker(), "gunfight!",
                on_result=lambda v, d: results.append((v, d)))
        self.assertTrue(in_flight)
        applied.assert_called_once()
        self.assertEqual(results, [(verdict, ["unit"])])

    def test_on_result_none_none_on_failure(self):
        results = []

        def fake_request(instructions, prompt, schema, on_verdict, on_fail):
            on_fail()

        with patch("world.llm.client.civic_enabled", return_value=True), \
             patch("world.llm.client.request_civic_verdict",
                   side_effect=fake_request):
            in_flight = rr.consider_radio_report(
                MagicMock(), self._speaker(), "gunfight!",
                on_result=lambda v, d: results.append((v, d)))
        self.assertTrue(in_flight)
        self.assertEqual(results, [(None, None)])

    def test_declined_lane_returns_false(self):
        with patch("world.llm.client.civic_enabled", return_value=False):
            self.assertFalse(rr.consider_radio_report(
                MagicMock(), self._speaker(), "gunfight!"))
