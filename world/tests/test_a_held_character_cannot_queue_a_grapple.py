"""A held character cannot start a grapple, and an intent queued before
the hold does not outlive it (#3352).

GRAPPLE_SYSTEM_SPEC prerequisites: "Cannot grapple if being grappled by
someone else." `grapple` never asked; a held victim's `grapple <anyone>`
was accepted, pulled the named person into combat, echoed "You prepare
to grapple X", and the intent sat unread through every held round --
the auto-escape consumes the turn before dispatch and nothing cleared
the slot -- then fired on the first round after the break, a grapple
asked for many rounds earlier. Reproduced in the live server before the
fix (Bravo held by Alpha typed `grapple Charlie`; two rounds later
Charlie read "Bravo grapples you!").

Now: the command refuses through the shared `validate_grapple_action`
guard (which nothing in production called), before the target is
enrolled; and the round loop expires the queued intent whenever a held
or yielding turn is spent without dispatch.
"""
import contextlib
import random
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

import world.combat.actions as actions_mod
import world.combat.grappling as grappling_mod
import world.combat.handler as handler_mod
import world.combat.utils as utils_mod
from world.combat.constants import (
    COMBAT_ACTION_GRAPPLE_INITIATE, DB_CHAR, DB_COMBAT_ACTION, DB_GRAPPLED_BY_DBREF,
)


class _Cap:
    def msg(self, text, **kw): pass


class _Held(EvenniaTest):
    def setUp(self):
        super().setUp()
        mk = lambda key: create_object("typeclasses.characters.Character", key=key, location=self.room1)
        self.A, self.B, self.C = mk("Alpha"), mk("Bravo"), mk("Charlie")
        from world.combat.proximity import establish_proximity
        establish_proximity(self.A, self.B); establish_proximity(self.B, self.C); establish_proximity(self.A, self.C)
        self.quiet = contextlib.ExitStack()
        for mod in (handler_mod, actions_mod, grappling_mod, utils_mod):
            if hasattr(mod, "get_splattercast"):
                self.quiet.enter_context(patch.object(mod, "get_splattercast", lambda: _Cap()))
        self.addCleanup(self.quiet.close)
        self.h = handler_mod.get_or_create_combat(self.room1)
        utils_mod.add_combatant(self.h, self.A, target=self.B)
        utils_mod.add_combatant(self.h, self.B, target=self.A)
        ok, _ = grappling_mod.establish_grapple(self.h, self.A, self.B)
        self.assertTrue(ok, "fixture: Alpha must hold Bravo")
        self.said = {}
        for ch in (self.A, self.B, self.C):
            self.said[ch] = []
            ch.msg = (lambda who: (lambda text=None, **kw: self.said[who].append(str(text))))(ch)

    def entry(self, ch):
        return next(e for e in self.h.db.combatants if e.get(DB_CHAR) == ch)

    def grapple(self, who, target_key):
        from commands.combat.special_actions import CmdGrapple
        cmd = CmdGrapple(); cmd.caller = who; cmd.args = target_key; cmd.cmdstring = "grapple"; cmd.switches = []
        cmd.func()
        return " ".join(self.said[who])


class TestAHeldCharacterIsRefused(_Held):
    def test_the_refusal_names_the_grappler(self):
        said = self.grapple(self.B, "Charlie")
        self.assertIn("grappling you", said, said)
        self.assertNotIn("prepare to grapple", said, said)

    def test_nothing_is_queued_and_nobody_is_enrolled(self):
        self.grapple(self.B, "Charlie")
        self.assertIsNone(self.entry(self.B).get(DB_COMBAT_ACTION))
        self.assertFalse(any(e.get(DB_CHAR) == self.C for e in self.h.db.combatants),
                         "the named target was pulled into combat by a refused grapple")

    def test_a_free_character_can_still_grapple(self):
        """Control: the guard is about being HELD, not about combat."""
        said = self.grapple(self.C, "Alpha")
        self.assertIn("prepare to grapple", said, said)


class TestAQueuedIntentDoesNotOutliveTheHold(_Held):
    def _round_still_held(self):
        # rolls pinned to their max: Alpha (100) keeps Bravo (1) held
        self.A.motorics, self.B.motorics = 100, 1
        with patch.object(random, "randint", lambda a, b: b), patch.object(actions_mod, "randint", lambda a, b: b):
            self.h.at_repeat()

    def test_an_intent_queued_before_the_hold_expires_with_the_turn(self):
        e = self.entry(self.B); e[DB_COMBAT_ACTION] = COMBAT_ACTION_GRAPPLE_INITIATE
        self.h.db.combatants = self.h.db.combatants
        self._round_still_held()
        self.assertIsNotNone(self.entry(self.B).get(DB_GRAPPLED_BY_DBREF), "fixture: still held")
        self.assertIsNone(self.entry(self.B).get(DB_COMBAT_ACTION),
                          "a queued grapple survived a held round and would fire after the break")
