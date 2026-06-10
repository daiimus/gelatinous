"""
Tests for inventory/throw command identity targeting (PR β).

Verifies that ``give``, ``wrest``, and ``throw`` route character-target
resolution through ``commands._identity_targeting.resolve_character_target``
rather than calling ``caller.search`` directly.

The helper itself is exhaustively tested in
``test_combat_command_identity``; here we only assert call-site wiring:

  - the helper is invoked with the correct query string,
  - command flow honours its return value (target vs None),
  - cross-room throw passes ``candidates=destination.contents``.

Run via::

    evennia test world.tests.test_inventory_command_identity
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


# ===================================================================
# CmdGive — same-room target resolution
# ===================================================================


class TestCmdGiveIdentityTargeting(TestCase):
    """``give`` resolves its target via the identity helper."""

    def _make_cmd(self, item_name="apple", target_name="man"):
        from commands.CmdInventory import CmdGive

        cmd = CmdGive()
        cmd.caller = MagicMock()
        cmd.caller.hands = {"right": MagicMock(key="apple")}
        cmd.caller.location = MagicMock()
        cmd.item_name = item_name
        cmd.target_name = target_name
        return cmd

    @patch("commands.CmdInventory.resolve_character_target")
    def test_give_calls_identity_helper_with_target_name(self, mock_resolve):
        """``give apple to man`` invokes helper with 'man'."""
        mock_resolve.return_value = None  # short-circuit after resolution
        cmd = self._make_cmd(target_name="man")
        cmd.func()
        mock_resolve.assert_called_once_with(cmd.caller, "man")

    @patch("commands.CmdInventory.resolve_character_target")
    def test_give_aborts_with_message_when_target_not_found(self, mock_resolve):
        mock_resolve.return_value = None
        cmd = self._make_cmd(target_name="ghost")
        cmd.func()
        # caller.msg called with not-found message containing query.
        msg_calls = [c.args[0] for c in cmd.caller.msg.call_args_list]
        self.assertTrue(any("ghost" in m for m in msg_calls))

    @patch("commands.CmdInventory.resolve_character_target")
    def test_give_proceeds_past_resolution_when_target_found(self, mock_resolve):
        """When helper returns a target, command continues to hand checks."""
        target = MagicMock()
        target.hands = {"left": None}
        mock_resolve.return_value = target
        cmd = self._make_cmd(target_name="man")
        cmd.func()
        # caller.msg was called for some downstream condition — but NOT
        # the not-found message.
        msg_calls = [c.args[0] for c in cmd.caller.msg.call_args_list]
        self.assertFalse(
            any("don't see" in m for m in msg_calls),
            f"unexpected not-found path; messages={msg_calls}",
        )

    @patch("commands.CmdInventory.resolve_character_target")
    def test_give_does_not_use_caller_search_for_target(self, mock_resolve):
        """``give`` no longer calls caller.search for the target."""
        mock_resolve.return_value = None
        cmd = self._make_cmd()
        cmd.func()
        cmd.caller.search.assert_not_called()


# ===================================================================
# CmdWrest — victim resolution via _find_target_in_room
# ===================================================================


class TestCmdWrestIdentityTargeting(TestCase):
    """``wrest`` victim lookup uses the identity helper."""

    def _make_cmd(self, object_name="knife", target_name="man"):
        from commands.CmdInventory import CmdWrest

        cmd = CmdWrest()
        cmd.caller = MagicMock()
        cmd.caller.location = MagicMock()
        cmd.object_name = object_name
        cmd.target_name = target_name
        return cmd

    @patch("commands.CmdInventory.resolve_character_target")
    def test_find_target_in_room_calls_helper(self, mock_resolve):
        mock_resolve.return_value = None
        cmd = self._make_cmd(target_name="man")
        result = cmd._find_target_in_room()
        mock_resolve.assert_called_once_with(cmd.caller, "man")
        self.assertIsNone(result)

    @patch("commands.CmdInventory.resolve_character_target")
    def test_find_target_in_room_requires_hands(self, mock_resolve):
        """Non-character matches (no .hands) are rejected."""
        non_char = MagicMock(spec=[])  # no hands attribute
        mock_resolve.return_value = non_char
        cmd = self._make_cmd()
        self.assertIsNone(cmd._find_target_in_room())

    @patch("commands.CmdInventory.resolve_character_target")
    def test_find_target_in_room_returns_character_with_hands(
        self, mock_resolve
    ):
        target = MagicMock()
        target.hands = {"left": None, "right": None}
        mock_resolve.return_value = target
        cmd = self._make_cmd()
        self.assertIs(cmd._find_target_in_room(), target)


# ===================================================================
# CmdThrow — same-room and cross-room (aimed) target resolution
# ===================================================================


class TestCmdThrowIdentityTargeting(TestCase):
    """``throw`` target lookup (same-room and aimed cross-room)."""

    def _make_cmd(self, target_name="man"):
        from commands.CmdThrow import CmdThrow

        cmd = CmdThrow()
        cmd.caller = MagicMock()
        cmd.caller.location = MagicMock()
        cmd.caller.location.id = 1
        cmd.target_name = target_name
        # No aim direction by default
        cmd.caller.ndb = MagicMock()
        return cmd

    @patch("commands.CmdThrow.get_splattercast")
    @patch("commands.CmdThrow.resolve_character_target")
    def test_same_room_lookup_uses_helper(self, mock_resolve, _mock_channel):
        target = MagicMock()
        target.hands = {"left": None}
        mock_resolve.return_value = target
        cmd = self._make_cmd(target_name="man")
        # No aim: skip aim_direction path
        from world.combat.constants import NDB_AIMING_DIRECTION

        setattr(cmd.caller.ndb, NDB_AIMING_DIRECTION, None)
        # Stub aim_direction lookup
        result = cmd.find_target()
        # Helper called for same-room lookup (positional)
        same_room_call = mock_resolve.call_args_list[0]
        self.assertEqual(same_room_call.args, (cmd.caller, "man"))
        self.assertIs(result, target)

    @patch("commands.CmdThrow.get_splattercast")
    @patch("commands.CmdThrow.resolve_character_target")
    def test_no_target_no_aim_messages_no_aim_error(
        self, mock_resolve, _mock_channel
    ):
        from world.combat.constants import NDB_AIMING_DIRECTION

        mock_resolve.return_value = None
        cmd = self._make_cmd(target_name="ghost")
        setattr(cmd.caller.ndb, NDB_AIMING_DIRECTION, None)
        cmd.find_target()
        msg_calls = [c.args[0] for c in cmd.caller.msg.call_args_list]
        # Should hit the NO_AIM_CROSS_ROOM branch
        self.assertTrue(msg_calls)

    @patch("commands.CmdThrow.get_splattercast")
    @patch("commands.CmdThrow.resolve_character_target")
    def test_cross_room_lookup_passes_destination_contents(
        self, mock_resolve, _mock_channel
    ):
        """Aimed cross-room lookup uses destination.contents as candidates."""
        from world.combat.constants import NDB_AIMING_DIRECTION

        # Same-room: no match. Cross-room: hit.
        target = MagicMock()
        target.hands = {"left": None}
        mock_resolve.side_effect = [None, target]

        cmd = self._make_cmd(target_name="man")
        setattr(cmd.caller.ndb, NDB_AIMING_DIRECTION, "north")

        destination = MagicMock()
        destination.id = 2
        destination.contents = ["thing-a", "thing-b"]
        cmd.get_destination_room = MagicMock(return_value=destination)

        result = cmd.find_target()
        self.assertIs(result, target)

        # Second call should be cross-room with candidates kwarg.
        cross_call = mock_resolve.call_args_list[1]
        self.assertEqual(cross_call.args, (cmd.caller, "man"))
        self.assertEqual(
            cross_call.kwargs.get("candidates"), destination.contents
        )

    @patch("commands.CmdThrow.get_splattercast")
    @patch("commands.CmdThrow.resolve_character_target")
    def test_does_not_use_caller_search_for_target(
        self, mock_resolve, _mock_channel
    ):
        """``throw`` find_target no longer calls caller.search."""
        from world.combat.constants import NDB_AIMING_DIRECTION

        mock_resolve.return_value = None
        cmd = self._make_cmd()
        setattr(cmd.caller.ndb, NDB_AIMING_DIRECTION, None)
        cmd.find_target()
        cmd.caller.search.assert_not_called()
