"""The combat reflex lane (#954 follow-on): one elected bystander, one
guardrail-safe beat, one real say command — silence on every failure."""

import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.llm.reflex as rx
from world.llm.reflex import (
    REFLEX_BEATS, _clean_reflex, _elect_bystander, fire_combat_reflex)


def _npc(dbref=10, llm=True, cooldown_ago=9999):
    npc = MagicMock()
    npc.id = dbref
    npc.key = "Sable"
    npc.db = SimpleNamespace(llm_driven=llm,
                             llm_persona={"name": "Sable",
                                          "description": "a bartender"})
    npc.ndb = SimpleNamespace(
        last_combat_reflex=time.time() - cooldown_ago)
    npc.is_dead.return_value = False
    npc.is_unconscious.return_value = False
    return npc


def _handler(fired=False, combatants=()):
    from world.combat.constants import DB_CHAR
    h = MagicMock()
    h.ndb = SimpleNamespace(
        combat_reflex_done=True if fired else None)
    h.db.combatants = [{DB_CHAR: c} for c in combatants]
    return h


def _room(contents):
    room = MagicMock()
    room.contents = list(contents)
    return room


class TestBeatSafety(TestCase):
    def test_no_beat_carries_gore_phrasing(self):
        # the probe-mapped tripwires stay out of the small model's input
        for text in REFLEX_BEATS.values():
            for word in ("blood", "bleeding", "knife", "wound", "stab",
                         "dead", "kill", "corpse", "not moving"):
                self.assertNotIn(word, text.lower())


class TestCleanReflex(TestCase):
    def test_strips_stage_directions_and_quotes(self):
        self.assertEqual(
            _clean_reflex('*Eyes widen* "What the hell?"'),
            "What the hell?")

    def test_declines_and_meta_are_silence(self):
        self.assertIsNone(_clean_reflex("NOTHING"))
        self.assertIsNone(_clean_reflex("I cannot respond to that."))
        self.assertIsNone(_clean_reflex(""))
        self.assertIsNone(_clean_reflex("**"))


class TestElection(TestCase):
    def _see_hear(self):
        return (patch("world.perception.can_see", return_value=True),
                patch("world.perception.can_hear", return_value=True))

    def test_lowest_dbref_wins_fighters_excluded(self):
        see, hear = self._see_hear()
        low, high, fighter = _npc(5), _npc(9), _npc(1)
        with see, hear:
            winner = _elect_bystander(_room([high, low, fighter]),
                                      {fighter})
        self.assertIs(winner, low)

    def test_cooldown_and_non_llm_are_ineligible(self):
        see, hear = self._see_hear()
        cooling = _npc(3, cooldown_ago=5)          # reflexed recently
        plain = _npc(4, llm=False)
        ready = _npc(8)
        with see, hear:
            winner = _elect_bystander(_room([cooling, plain, ready]), set())
        self.assertIs(winner, ready)

    def test_imperceptive_room_elects_nobody(self):
        with patch("world.perception.can_see", return_value=False), \
                patch("world.perception.can_hear", return_value=False):
            self.assertIsNone(_elect_bystander(_room([_npc()]), set()))


class TestFire(TestCase):
    def _fire(self, handler, room, category="fight_started"):
        calls = {}
        def fake_request(instructions, prompt, on_reply, on_fail):
            calls["instructions"] = instructions
            calls["prompt"] = prompt
            on_reply('*ducks* "Hey! Take it outside!"')
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line",
                      side_effect=fake_request), \
                patch.object(rx, "delay",
                             side_effect=lambda t, fn: fn()), \
                patch("world.perception.can_see", return_value=True), \
                patch("world.perception.can_hear", return_value=True):
            fire_combat_reflex(handler, room, category)
        return calls

    def test_full_path_barks_through_the_real_command(self):
        npc = _npc()
        handler = _handler()
        calls = self._fire(handler, _room([npc]))
        self.assertEqual(calls["prompt"], REFLEX_BEATS["fight_started"])
        self.assertIn("Sable", calls["instructions"])
        npc.execute_cmd.assert_called_once_with(
            "say Hey! Take it outside!")
        self.assertIs(handler.ndb.combat_reflex_done, True)

    def test_one_reflex_per_fight(self):
        npc = _npc()
        calls = self._fire(_handler(fired=True), _room([npc]))
        self.assertEqual(calls, {})
        npc.execute_cmd.assert_not_called()

    def test_combatants_never_reflex(self):
        fighter = _npc(2)
        handler = _handler(combatants=(fighter,))
        self._fire(handler, _room([fighter]))
        fighter.execute_cmd.assert_not_called()

    def test_civic_lane_off_is_silence(self):
        npc = _npc()
        with patch("world.llm.client.civic_enabled", return_value=False):
            fire_combat_reflex(_handler(), _room([npc]), "fight_started")
        npc.execute_cmd.assert_not_called()
