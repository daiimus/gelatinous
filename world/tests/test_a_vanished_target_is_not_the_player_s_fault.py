"""A queued action whose target vanished says so (#3569).

``advance``, ``charge`` and ``disarm`` are queued one round and resolved
the next against a DIRECT object reference stored on the entry. When
that target is deleted in between, the reference deserializes to
``None`` with the key still present, and all three guards answered "No
target specified for <action> action" -- blaming the player for a
target they supplied, and spending the turn. The one resolver they now
share tells the two apart: no key means no target was given; a key
holding ``None`` means the target is gone.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.combat.utils as cu
from world.combat.constants import DB_CHAR, DB_COMBAT_ACTION_TARGET


def _char():
    c = MagicMock(); c.key = "Alice"; c.msg = MagicMock(); return c


class TestTheResolverTellsThemApart(TestCase):
    def test_a_present_target_is_returned(self):
        alice, bob = _char(), _char()
        got = cu.queued_action_target({DB_CHAR: alice, DB_COMBAT_ACTION_TARGET: bob}, alice, "advance")
        self.assertIs(got, bob)
        alice.msg.assert_not_called()

    def test_no_target_given_is_the_player_s_omission(self):
        alice = _char()
        got = cu.queued_action_target({DB_CHAR: alice}, alice, "advance")
        self.assertIsNone(got)
        self.assertIn("No target specified for advance", alice.msg.call_args[0][0])

    def test_a_vanished_target_is_not(self):
        alice = _char()
        with patch.object(cu, "logger") as log:
            got = cu.queued_action_target({DB_CHAR: alice, DB_COMBAT_ACTION_TARGET: None}, alice, "charge")
        self.assertIsNone(got)
        self.assertIn("no longer there", alice.msg.call_args[0][0])
        self.assertNotIn("No target specified", alice.msg.call_args[0][0])
        log.log_warn.assert_called()


class TestTheGuardsUseIt(TestCase):
    """The three resolvers reach the resolver, through the player-facing
    entry point, and stop there."""

    def _run(self, fn, action, *extra):
        alice = _char()
        handler = MagicMock(); handler.db.combatants = []
        with patch.object(cu, "logger"):
            fn(handler, alice, {DB_CHAR: alice, DB_COMBAT_ACTION_TARGET: None}, *extra)
        return alice.msg.call_args[0][0]

    def test_advance(self):
        from world.combat.movement_resolution import resolve_advance
        self.assertIn("no longer there", self._run(resolve_advance, "advance"))

    def test_charge(self):
        from world.combat.movement_resolution import resolve_charge
        self.assertIn("no longer there", self._run(resolve_charge, "charge", []))

    def test_disarm(self):
        from world.combat.actions import resolve_disarm
        self.assertIn("no longer there", self._run(resolve_disarm, "disarm"))
