"""Issue #306: the charge penalty finally bites, and combatants leave
the fight with a visible exit."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.combat.attack import _consume_charge_penalty


class TestChargePenalty(TestCase):
    def _char(self, flagged=True):
        c = MagicMock()
        c.ndb = SimpleNamespace()
        if flagged:
            c.ndb.charge_penalty = True
        return c

    def test_off_balance_halves_dodge_once(self):
        char = self._char()
        self.assertEqual(_consume_charge_penalty(char), 0.5)
        self.assertFalse(hasattr(char.ndb, "charge_penalty"))  # consumed
        self.assertEqual(_consume_charge_penalty(char), 1.0)   # one-shot
        self.assertIn("off-balance", char.msg.call_args_list[0].args[0])

    def test_unflagged_pays_nothing(self):
        char = self._char(flagged=False)
        self.assertEqual(_consume_charge_penalty(char), 1.0)
        char.msg.assert_not_called()

    def test_magic_mock_truthiness_guard(self):
        # a bare MagicMock ndb attr must not read as flagged
        char = MagicMock()
        self.assertEqual(_consume_charge_penalty(char), 1.0)


class TestCombatExitNarrative(TestCase):
    def _leaver(self, dead=False, unconscious=False):
        char = MagicMock()
        char.is_dead.return_value = dead
        char.is_unconscious.return_value = unconscious
        char.location = MagicMock()
        return char

    def _remove(self, char):
        from world.combat.constants import DB_CHAR
        from world.combat.utils import remove_combatant
        handler = MagicMock()
        handler._active_combatants_list = None
        handler.db.combatants = [{DB_CHAR: char}]
        with patch("world.identity_utils.msg_room_identity") as broadcast, \
                patch("world.combat.utils.get_splattercast",
                      return_value=MagicMock()), \
                patch("world.combat.utils.cleanup_combatant_state"):
            remove_combatant(handler, char)
        return broadcast

    def test_walking_out_is_visible(self):
        char = self._leaver()
        broadcast = self._remove(char)
        broadcast.assert_called_once()
        self.assertIn("lowers their guard",
                      broadcast.call_args.kwargs["template"])
        self.assertIn("step back", char.msg.call_args.args[0])

    def test_the_dead_do_not_lower_their_guard(self):
        broadcast = self._remove(self._leaver(dead=True))
        broadcast.assert_not_called()

    def test_the_unconscious_do_not_either(self):
        broadcast = self._remove(self._leaver(unconscious=True))
        broadcast.assert_not_called()
