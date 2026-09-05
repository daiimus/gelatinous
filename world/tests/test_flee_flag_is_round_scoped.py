"""One stray `flee` must not disable fleeing forever (#2423).

`flee_attempted_this_round` is a ROUND-scoped token. It was set at the
top of `CmdFlee.func`, before every validation -- including the "nothing
to flee from" bail -- and the only thing in the codebase that clears it
is the handler's per-combatant loop (`world/combat/handler.py:606`),
which needs you enrolled in a running fight AND reaching your turn.

So typing `flee` once in a quiet room set a flag nothing would ever
clear. Every later attempt answered "You have already attempted to flee
this combat round! Wait for the next round." -- a round that never came.
It persisted until the character entered real combat and survived to
their turn, or until a server reload, since it is `ndb`.

That included the aim-break flee, which is the ONLY escape from an aim
lock other than winning the roll. Someone who typed a stray `flee` and
was later aimed at had no way out.

The tests below are written against what a player experiences: type
`flee` with nothing to flee from, then try again, and see whether the
game says no.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.combat.movement import CmdFlee
from world.combat.constants import NDB_AIMED_AT_BY, NDB_COMBAT_HANDLER


class _FleeCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1
        self.said = []

    def flee(self):
        """Run the real command and collect what the player is told."""
        self.said = []
        cmd = CmdFlee()
        cmd.caller = self.char
        cmd.args = ""
        cmd.obj = self.char
        with mock.patch.object(type(self.char), "msg",
                               side_effect=lambda text=None, **kw:
                               self.said.append(str(text))):
            cmd.func()
        return " ".join(self.said)

    def flagged(self):
        return bool(getattr(self.char.ndb, "flee_attempted_this_round",
                            False))


class TestFleeingWithNothingToFleeFrom(_FleeCase):
    def test_it_does_not_set_the_round_token(self):
        """There is no round, so there is nothing for a round-scoped
        token to mean."""
        self.flee()
        self.assertFalse(self.flagged())

    def test_a_second_attempt_is_not_refused_as_a_repeat(self):
        """The whole finding."""
        self.flee()
        out = self.flee()
        self.assertNotIn("already attempted to flee", out)

    def test_it_stays_usable_after_many_attempts(self):
        for _ in range(5):
            self.flee()
        self.assertNotIn("already attempted to flee", self.flee())


class TestAStaleFlagHeals(_FleeCase):
    def test_an_existing_stale_flag_is_cleared_not_obeyed(self):
        """`ndb` survives until a reload, so anyone already carrying the
        old flag has to be let out without one."""
        self.char.ndb.flee_attempted_this_round = True
        out = self.flee()
        self.assertNotIn("already attempted to flee", out)
        self.assertFalse(self.flagged())


class TestInsideARoundTheLimitStillHolds(_FleeCase):
    """The flag exists to stop flee-spam within a round. That must
    survive the fix."""

    def _in_combat(self):
        handler = mock.MagicMock()
        handler.db.combatants = [{"char": self.char}]
        setattr(self.char.ndb, NDB_COMBAT_HANDLER, handler)
        return handler

    def test_a_flee_in_combat_sets_the_token(self):
        self._in_combat()
        self.flee()
        self.assertTrue(self.flagged())

    def test_a_second_flee_in_the_same_round_is_refused(self):
        self._in_combat()
        self.flee()
        out = self.flee()
        self.assertIn("already attempted to flee", out)

    def test_being_aimed_at_counts_as_a_round(self):
        """The aim-break flee is a real attempt and is rate-limited the
        same way."""
        setattr(self.char.ndb, NDB_AIMED_AT_BY, self.char2)
        self.flee()
        self.assertTrue(self.flagged())
