"""A dead or unconscious combatant is not re-pointed at a new opponent (#3347).

When someone leaves a fight, `remove_combatant` re-targets everyone who
was targeting them and announces it with the weapon's initiate pose.
The announcer was never checked: a body still enrolled (death does not
eject; only the attack path and the end-of-round sweep do) emitted
"flexes, joints popping, eyes locked on you" at a new target. #1584
gated the same pose on the attack command's side; this is the other
side.

Counting `initiate` calls rather than matching text: the banks are
random, so a specific line would pass or fail on a dice roll.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat import messages as combat_messages
from world.combat.constants import (
    DB_CHAR, DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, DB_IS_YIELDING, DB_TARGET_DBREF,
)
from world.combat.handler import get_or_create_combat
from world.combat.utils import add_combatant


class _InitiateSpy:
    def __init__(self):
        self.initiators = []
        self._real = combat_messages.get_combat_message

    def __call__(self, weapon_type, phase, attacker=None, target=None, **kw):
        if phase == "initiate":
            self.initiators.append(attacker)
        return self._real(weapon_type, phase, attacker=attacker, target=target, **kw)


class BodyDoesNotRetargetTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.alpha = self.char1
        self.bravo = create_object("typeclasses.characters.Character", key="Bravo", location=self.room1)
        self.charlie = create_object("typeclasses.characters.Character", key="Charlie", location=self.room1)
        self.handler = get_or_create_combat(self.room1)
        # Alpha <-> Bravo, and Charlie is on Bravo. When Alpha leaves,
        # Bravo's only candidate is Charlie.
        add_combatant(self.handler, self.alpha, target=self.bravo)
        add_combatant(self.handler, self.bravo, target=self.alpha)
        add_combatant(self.handler, self.charlie, target=self.bravo)

    def _kill(self, char):
        ms = char.medical_state
        ms.blood_level = 0
        ms._cached_is_dead = None

    def _knock_out(self, char):
        char.medical_state.consciousness = 0.0

    def _entry(self, char):
        return next((e for e in (self.handler.db.combatants or []) if e.get(DB_CHAR) == char), None)

    def _remove(self, char):
        spy = _InitiateSpy()
        with patch.object(combat_messages, "get_combat_message", spy):
            self.handler.remove_combatant(char)
        return spy

    def _tick(self):
        spy = _InitiateSpy()
        with patch.object(combat_messages, "get_combat_message", spy):
            self.handler.at_repeat()
        return spy

    # --- control: a live fighter does square up on the survivor ----------

    def test_control_a_live_fighter_is_retargeted_and_poses(self):
        spy = self._remove(self.alpha)
        self.assertIn(self.bravo, spy.initiators, "control: live Bravo did not retarget")
        self.assertEqual(self._entry(self.bravo).get(DB_TARGET_DBREF), self.handler._get_dbref(self.charlie))

    # --- the defect ------------------------------------------------------

    def test_a_dead_fighter_is_not_retargeted(self):
        self._kill(self.bravo)
        spy = self._remove(self.alpha)
        self.assertNotIn(self.bravo, spy.initiators, "a corpse squared up")
        self.assertIsNone(self._entry(self.bravo).get(DB_TARGET_DBREF))

    def test_an_unconscious_fighter_is_not_retargeted(self):
        self._knock_out(self.bravo)
        spy = self._remove(self.alpha)
        self.assertNotIn(self.bravo, spy.initiators, "an unconscious body squared up")
        self.assertIsNone(self._entry(self.bravo).get(DB_TARGET_DBREF))

    # --- the player-visible path: two non-attack deaths, one round --------

    def test_two_deaths_in_one_round_neither_poses(self):
        # A grenade's shape: Alpha and Bravo both dead before the round,
        # Bravo targeting Alpha. The sweep removes Alpha first, and Bravo
        # is still enrolled and dead when the retarget loop reaches him.
        self._kill(self.alpha)
        self._kill(self.bravo)
        spy = self._tick()
        self.assertNotIn(self.bravo, spy.initiators, "a corpse squared up during the sweep")
        names = [e.get(DB_CHAR).key for e in (self.handler.db.combatants or []) if e.get(DB_CHAR)] if self.handler.pk else []
        self.assertNotIn("Bravo", names)
        self.assertNotIn(self.alpha.key, names)

    def test_two_knockouts_in_one_round_neither_poses(self):
        # The common case: a knockout in combat is ejected five seconds
        # later, not on the hit, so two fighters dropped in one round are
        # both still enrolled when the sweep runs.
        self._knock_out(self.alpha)
        self._knock_out(self.bravo)
        spy = self._tick()
        self.assertNotIn(self.bravo, spy.initiators, "an unconscious body squared up during the sweep")
        names = [e.get(DB_CHAR).key for e in (self.handler.db.combatants or []) if e.get(DB_CHAR)] if self.handler.pk else []
        self.assertNotIn("Bravo", names)

    # --- a hold is a hold (#3622) ------------------------------------------

    def _set_entry(self, char, **fields):
        combatants = self.handler.db.combatants or []
        for e in combatants:
            if e.get(DB_CHAR) == char:
                e.update(fields)
        self.handler.db.combatants = combatants

    def test_a_yielding_survivor_is_not_repointed_and_keeps_yielding(self):
        # Bravo typed `stop attacking`: yielding, still pointed at Alpha, Charlie on him.
        self._set_entry(self.bravo, **{DB_IS_YIELDING: True})
        with patch.object(self.bravo, "msg") as told:
            spy = self._remove(self.alpha)
        self.assertNotIn(self.bravo, spy.initiators, "a yielder squared up")
        entry = self._entry(self.bravo)
        self.assertIsNone(entry.get(DB_TARGET_DBREF), "a yielder was re-pointed")
        self.assertTrue(entry.get(DB_IS_YIELDING), "the retarget un-yielded a holder")
        said = " ".join(str(c) for c in told.call_args_list)
        self.assertIn("has left combat", said)
        self.assertIn("still targeting you", said, "the yielder was not told who is still on them")
        self.assertIn("resume malicious intentions", said, "the yielder was not reminded they are yielding")

    def test_a_held_yielder_stays_held_and_yielding(self):
        # The shield case: Charlie holds Bravo consensually (both yield),
        # Bravo still pointed at Alpha from before the hold. Alpha leaves.
        self._set_entry(self.charlie, **{DB_IS_YIELDING: True, DB_GRAPPLING_DBREF: self.handler._get_dbref(self.bravo)})
        self._set_entry(self.bravo, **{DB_IS_YIELDING: True, DB_GRAPPLED_BY_DBREF: self.handler._get_dbref(self.charlie)})
        spy = self._remove(self.alpha)
        entry = self._entry(self.bravo)
        self.assertTrue(entry.get(DB_IS_YIELDING), "a held person was turned violent by a third party leaving")
        self.assertIsNone(entry.get(DB_TARGET_DBREF))
        self.assertNotIn(self.bravo, spy.initiators)
        self.assertEqual(entry.get(DB_GRAPPLED_BY_DBREF), self.handler._get_dbref(self.charlie))

    def test_control_a_non_yielding_survivor_stays_non_yielding(self):
        spy = self._remove(self.alpha)
        self.assertIn(self.bravo, spy.initiators)
        self.assertFalse(self._entry(self.bravo).get(DB_IS_YIELDING, False))
