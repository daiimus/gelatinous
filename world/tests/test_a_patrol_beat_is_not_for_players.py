"""A player's body is never put on a beat, and never walked by one.

Regression pin for #2567. `CmdPatrol._find_npc` checked only that the
target is a `Character` -- which a PLAYER is -- so a player could be
posted, and the director's heartbeat then walked their body: executing
exits, and at a gap tile a `jump across` the travel code documents can
kill the traverser.

Guarded at BOTH doors, because they are genuinely two: the command
writes the attribute, and `tick_all` selects on the attribute regardless
of how it got written (a build script, a hand edit, or a beat set before
the guard existed).

`is_player_owned` rather than `has_account`: the account link exists
only while PUPPETED, so a logged-out player character reads as
ownerless by that field. `world/ownership.py` exists because this
codebase has already lost bodies to that assumption.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.director.routines as routines


class TestAPatrolBeatIsNotForPlayers(TestCase):

    def test_the_heartbeat_skips_a_player_body(self):
        pc, npc = MagicMock(), MagicMock()
        with patch("evennia.objects.models.ObjectDB") as odb, \
             patch("world.ownership.is_player_owned",
                   side_effect=lambda o: o is pc), \
             patch.object(routines, "tick_npc", return_value="walked") as tick:
            odb.objects.filter.return_value.distinct.return_value = [pc, npc]
            counts = routines.tick_all()
        tick.assert_called_once_with(npc)
        self.assertEqual(counts.get("player_skipped"), 1)

    def test_the_heartbeat_still_walks_npcs(self):
        """The control — a guard that skipped everything would pass the
        test above."""
        npc = MagicMock()
        with patch("evennia.objects.models.ObjectDB") as odb, \
             patch("world.ownership.is_player_owned", return_value=False), \
             patch.object(routines, "tick_npc", return_value="walked") as tick:
            odb.objects.filter.return_value.distinct.return_value = [npc]
            counts = routines.tick_all()
        tick.assert_called_once_with(npc)
        self.assertEqual(counts.get("walked"), 1)
        self.assertIsNone(counts.get("player_skipped"))

    def _guard(self, present):
        """Patch the command's guard, reporting its ABSENCE as a named
        failure rather than an error. On an unfixed tree the name is not
        imported, and `patch` raises AttributeError — which reads like a
        broken harness instead of a missing guard."""
        import commands.CmdPatrol as mod
        if not hasattr(mod, "is_player_owned"):
            self.fail("CmdPatrol does not consult is_player_owned, so a "
                      "player can be posted to a beat")
        return patch.object(mod, "is_player_owned", return_value=present)

    def test_the_command_refuses_a_player(self):
        from commands.CmdPatrol import CmdPatrol

        cmd = CmdPatrol()
        cmd.caller = MagicMock()
        target = MagicMock()
        target.is_typeclass.return_value = True
        cmd.caller.search.return_value = target
        with self._guard(True):
            self.assertIsNone(cmd._find_npc("someone"))
        cmd.caller.msg.assert_called()

    def test_the_command_still_accepts_an_npc(self):
        from commands.CmdPatrol import CmdPatrol

        cmd = CmdPatrol()
        cmd.caller = MagicMock()
        target = MagicMock()
        target.is_typeclass.return_value = True
        cmd.caller.search.return_value = target
        with self._guard(False):
            self.assertIs(cmd._find_npc("bot"), target)
