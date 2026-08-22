"""The colony understands a call for help without a model (#2221).

The civic classifier used to be the GATE: `consider_radio_report`
returned early when `civic_enabled()` was False, so with the sidecar
down a player could shout "shots fired on Volta Street" and no event
was raised and no unit rolled — silently.

Owner ruling (2026-08-22): deterministic first, model as refiner.
Words the colony understands are read in plain code; the model only
catches what the words missed.

False positives are expected and accepted — it is an open frequency
and people will prank it. Units rolling on a prank is content. A real
call falling silent is not.
"""
import re

from evennia.utils.test_resources import EvenniaCommandTest

from world.director.radio_report import (
    INCIDENT_WORDS,
    classify_report,
)


class TestItReadsACallForHelp(EvenniaCommandTest):
    def _kind(self, speech):
        verdict = classify_report(speech, rooms=[])
        return verdict["incident_type"] if verdict else None

    def test_the_things_people_actually_shout(self):
        cases = {
            "Dispatch, shots fired on Volta Street!": "assault",
            "someone just got stabbed outside the bar": "assault",
            "he's got a knife": "assault",
            "there's a fire in the stairwell": "fire",
            "smoke coming out of the vents": "fire",
            "she's bleeding out, I need a medic": "medical",
            "guy's unconscious in the alley": "medical",
            "they robbed me": "theft",
            "my kit got jacked": "theft",
            "there's a brawl in the market": "disturbance",
        }
        for speech, expected in cases.items():
            self.assertEqual(self._kind(speech), expected, speech)

    def test_violence_wins_when_a_call_hits_two(self):
        """Most-severe-first: over-responding to violence is the right
        error."""
        self.assertEqual(
            self._kind("they're fighting and someone's got a knife"),
            "assault")
        self.assertEqual(
            self._kind("screaming, I think somebody got shot"), "assault")

    def test_an_unreadable_call_is_a_question_not_a_decision(self):
        """None means 'ask', not 'nothing happened'."""
        for speech in ("help", "is anyone there", "hello?",
                       "how's your night going"):
            self.assertIsNone(classify_report(speech, rooms=[]), speech)

    def test_empty_traffic_is_none(self):
        self.assertIsNone(classify_report("", rooms=[]))
        self.assertIsNone(classify_report(None, rooms=[]))


class TestWordAnchoring(EvenniaCommandTest):
    """Substring matching has bitten this codebase three times —
    "brass-toed" -> bra, "collarless" -> collar, "dress shirt" -> dress.
    These words are short and common enough to do it again."""

    def _kind(self, speech):
        verdict = classify_report(speech, rooms=[])
        return verdict["incident_type"] if verdict else None

    def test_od_does_not_match_inside_other_words(self):
        for innocent in ("the food cart is closed", "good evening",
                         "wood smoke"):    # 'wood smoke' still fires FIRE
            kind = self._kind(innocent)
            self.assertNotEqual(kind, "medical", innocent)

    def test_shot_does_not_match_shoddy(self):
        self.assertIsNone(self._kind("shoddy wiring in here"))

    def test_gun_does_not_match_begun(self):
        self.assertIsNone(self._kind("the shift has begun"))

    def test_every_pattern_is_word_anchored(self):
        """Structural: no pattern may be a bare substring test."""
        from world.director.radio_report import _INCIDENT_PATTERNS
        for kind, pattern in _INCIDENT_PATTERNS:
            self.assertTrue(pattern.pattern.startswith(r"\b"), kind)
            self.assertTrue(pattern.pattern.endswith(r"\b"), kind)


class TestTheVerdictShape(EvenniaCommandTest):
    """It must be the SAME shape the model emits, so `apply_verdict`
    consumes it unchanged — that is what keeps one downstream."""

    def test_it_matches_the_model_contract(self):
        verdict = classify_report("shots fired", rooms=[])
        self.assertEqual(set(verdict),
                         {"is_incident_report", "incident_type",
                          "location_text"})
        self.assertIs(verdict["is_incident_report"], True)

    def test_every_kind_maps_to_a_real_event(self):
        from world.director.radio_report import REPORTED_EVENTS
        for kind, _words in INCIDENT_WORDS:
            self.assertIn(kind, REPORTED_EVENTS, kind)


class TestFindingTheRoomTheyNamed(EvenniaCommandTest):
    def test_a_named_room_is_found(self):
        self.room1.key = "Volta Street"
        verdict = classify_report("shots fired on Volta Street!",
                                  rooms=[self.room1])
        self.assertEqual(verdict["location_text"], "Volta Street")

    def test_one_common_word_is_not_a_location(self):
        """'street' alone must not pin a room — people say it constantly."""
        self.room1.key = "Volta Street"
        verdict = classify_report("shots fired in the street",
                                  rooms=[self.room1])
        self.assertEqual(verdict["location_text"], "")

    def test_an_unnamed_place_resolves_to_nothing_here(self):
        """Downstream falls back to the caller's own room — people
        report what is in front of them."""
        self.room1.key = "Volta Street"
        verdict = classify_report("someone's bleeding", rooms=[self.room1])
        self.assertEqual(verdict["location_text"], "")
