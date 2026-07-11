"""NPC perception of combat (#954, combat-first slice).

Bystander LLM brains buffer witness-testimony beats — who started on
whom, who went down, how it ended — through the same [RECENTLY] rails
poses ride. Perception-gated, perceived-identity rendered, observe-only.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.llm.observation as obs
from world.llm.observation import (
    combat_exit_line, combat_join_line, observe_event,
    personal_attack_line)


def _npc(llm=True):
    npc = MagicMock()
    npc.db = SimpleNamespace(llm_driven=llm)
    npc._observe_action = MagicMock()
    return npc


def _room(contents):
    room = MagicMock()
    room.contents = contents
    return room


class TestObserveEvent(TestCase):
    def test_sighted_llm_bystander_buffers_the_rendered_line(self):
        npc = _npc()
        with patch("world.perception.can_see", return_value=True):
            observe_event(_room([npc]),
                          lambda o: "a wiry man attacks a heavyset woman!")
        npc._observe_action.assert_called_once()
        self.assertIn("wiry man", npc._observe_action.call_args.args[1])

    def test_blind_bystander_gets_the_sound_only(self):
        npc = _npc()
        with patch("world.perception.can_see", return_value=False), \
                patch("world.perception.can_hear", return_value=True):
            observe_event(_room([npc]), lambda o: "the visual line",
                          sound="sudden violence erupts nearby")
        self.assertEqual(npc._observe_action.call_args.args[1],
                         "sudden violence erupts nearby")

    def test_deaf_and_blind_get_nothing(self):
        npc = _npc()
        with patch("world.perception.can_see", return_value=False), \
                patch("world.perception.can_hear", return_value=False):
            observe_event(_room([npc]), lambda o: "line", sound="sound")
        npc._observe_action.assert_not_called()

    def test_non_llm_and_excluded_are_skipped(self):
        plain = MagicMock()
        plain.db = SimpleNamespace(llm_driven=None)   # strict is True
        fighter = _npc()
        watcher = _npc()
        with patch("world.perception.can_see", return_value=True):
            observe_event(_room([plain, fighter, watcher]),
                          lambda o: "line", exclude=(fighter,))
        plain._observe_action.assert_not_called()
        fighter._observe_action.assert_not_called()
        watcher._observe_action.assert_called_once()

    def test_magicmock_truthiness_guard(self):
        impostor = MagicMock()   # bare mock: db.llm_driven is a Mock
        with patch("world.perception.can_see", return_value=True):
            observe_event(_room([impostor]), lambda o: "line")
        impostor._observe_action.assert_not_called()


class TestRenderers(TestCase):
    def _seen_as(self, name):
        char = MagicMock()
        char.get_display_name.return_value = name
        return char

    def test_join_names_the_opening_target(self):
        char = self._seen_as("a wiry man")
        target = self._seen_as("a heavyset woman")
        observer = MagicMock()
        self.assertEqual(combat_join_line(char, target)(observer),
                         "a wiry man attacks a heavyset woman!")

    def test_join_addresses_the_observer_when_targeted(self):
        char = self._seen_as("a wiry man")
        observer = MagicMock()
        line = combat_join_line(char, observer)(observer)
        self.assertEqual(line, "a wiry man comes straight at you!")

    def test_exit_states(self):
        char = self._seen_as("a wiry man")
        observer = MagicMock()
        self.assertIn("doesn't move",
                      combat_exit_line(char, "dead")(observer))
        self.assertIn("out cold",
                      combat_exit_line(char, "unconscious")(observer))
        self.assertIn("steps back",
                      combat_exit_line(char, "walked")(observer))

    def test_personal_attack_renders_from_target_pov(self):
        attacker = MagicMock()
        attacker.get_display_name.return_value = "a scarred woman"
        target = _npc()
        hit = personal_attack_line(attacker, target, "a knife", hit=True)
        miss = personal_attack_line(attacker, target, None, hit=False)
        self.assertEqual(hit, "a scarred woman hits you with a knife!")
        self.assertEqual(miss, "a scarred woman attacks you and misses!")
        attacker.get_display_name.assert_called_with(target)


class TestCombatWiring(TestCase):
    def test_remove_combatant_feeds_bystander_memory(self):
        from world.combat.constants import DB_CHAR
        from world.combat.utils import remove_combatant
        char = MagicMock()
        char.is_dead.return_value = True
        char.is_unconscious.return_value = False
        char.location = MagicMock()
        handler = MagicMock()
        handler._active_combatants_list = None
        handler.db.combatants = [{DB_CHAR: char}]
        with patch("world.llm.observation.observe_event") as tap, \
                patch("world.identity_utils.msg_room_identity"), \
                patch("world.combat.utils.get_splattercast",
                      return_value=MagicMock()), \
                patch("world.combat.utils.cleanup_combatant_state"):
            remove_combatant(handler, char)
        tap.assert_called_once()
        self.assertEqual(tap.call_args.kwargs.get("sound"),
                         "a body hits the floor nearby")
