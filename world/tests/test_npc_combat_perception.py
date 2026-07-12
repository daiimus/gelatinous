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


class TestDirectedActionPerception(TestCase):
    """#954 remainder: give/dress/undress reach LLM NPCs — buffered for
    bystanders, felt personally (with a reaction) by the target."""

    def _llm_target(self, npc_actor=False):
        target = MagicMock()
        target.db.llm_driven = True
        target._is_npc_speaker.return_value = npc_actor
        return target

    def test_target_buffers_and_reacts(self):
        from world.llm import observation as omod
        target = self._llm_target()
        actor = MagicMock()
        with patch("typeclasses.llm_npc.llm_enabled", return_value=True), \
             patch("evennia.utils.utils.delay") as mock_delay:
            omod.observe_directed_action(actor, target,
                                         "someone hands you a shiv.")
        target._observe_action.assert_called_once_with(
            actor, "someone hands you a shiv.")
        self.assertEqual(mock_delay.call_args.args[1:],
                         (target._try_llm_reply,
                          "someone hands you a shiv.", actor, "action"))

    def test_react_false_buffers_only(self):
        from world.llm import observation as omod
        target = self._llm_target()
        with patch("evennia.utils.utils.delay") as mock_delay:
            omod.observe_directed_action(MagicMock(), target,
                                         "line", react=False)
        target._observe_action.assert_called_once()
        mock_delay.assert_not_called()

    def test_npc_actor_never_triggers_reaction(self):
        # the NPC<->NPC loop guard: buffer yes, reply no
        from world.llm import observation as omod
        target = self._llm_target(npc_actor=True)
        with patch("typeclasses.llm_npc.llm_enabled", return_value=True), \
             patch("evennia.utils.utils.delay") as mock_delay:
            omod.observe_directed_action(MagicMock(), target, "line")
        target._observe_action.assert_called_once()
        mock_delay.assert_not_called()

    def test_non_llm_target_is_a_no_op(self):
        from world.llm import observation as omod
        target = MagicMock()
        target.db.llm_driven = None
        omod.observe_directed_action(MagicMock(), target, "line")
        target._observe_action.assert_not_called()

    def test_transfer_line_renders_per_observer(self):
        from world.llm.observation import transfer_line
        giver, item, receiver, observer = (MagicMock() for _ in range(4))
        giver.get_display_name.return_value = "a wiry man"
        receiver.get_display_name.return_value = "a shaken tenant"
        item.get_display_name.return_value = "a battered walkie"
        line = transfer_line(giver, item, receiver)(observer)
        self.assertEqual(
            line, "a wiry man hands a shaken tenant a battered walkie.")
        giver.get_display_name.assert_called_with(observer)

    def test_clothing_lines(self):
        from world.llm.observation import clothing_line
        actor, target, item, observer = (MagicMock() for _ in range(4))
        actor.get_display_name.return_value = "a clerk"
        target.get_display_name.return_value = "a slumped figure"
        item.get_display_name.return_value = "a house robe"
        self.assertEqual(
            clothing_line(actor, target, item, dressing=True)(observer),
            "a clerk dresses a slumped figure in a house robe.")
        self.assertEqual(
            clothing_line(actor, target, dressing=False)(observer),
            "a clerk strips the clothes off a slumped figure.")
