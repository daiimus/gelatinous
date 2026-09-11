"""A downed character does not take a defensive stance (#1584).

Reported from a live deathmatch: the victim collapsed, and for the ~90s
death-progression window kept emitting combat poses -- "cracks their
knuckles with a dead-eyed stare, looking right at you", "shifts their
weight from heel to heel -- it looks like fight time with you" -- while
their session was running the dying narrative.

## Where it was NOT

The round loop was the obvious suspect and is innocent. Simulating rounds
directly (the sweep fires on the ticker, between player commands, so a
synchronous probe misses it):

    dead combatant       -> skipped, ejected, handler dissolved, 1 round
    unconscious combatant-> skipped, ejected, handler dissolved, 1 round
    two healthy fighters -> both retained, handler alive, round advances

The last line is the control: without it, "everyone was removed" cannot
be told apart from a fixture that never enrolled anyone.

## Where it was

`CmdAttack` emits the TARGET's defensive initiate at ENROLMENT, before
any round runs, and gated it only on whether the target was already in
combat or already had a target -- never on whether they can still react.
So attacking a body produced, verbatim:

    Bravo flexes, joints popping, eyes locked on you.

from a character whose `is_dead()` was already True. The handler then
ejected them on the next tick, which is exactly why this read as "the
dying keep taking turns" while the round loop looked correct.

Only the target's DEFENSIVE reaction is gated. The attacker still swings:
a body stays attackable, which is the half the issue explicitly allowed
("attackable as a body, perhaps, but not performing combat idles").
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from commands.combat import core_actions
from commands.combat.core_actions import CmdAttack
from world.combat.handler import get_or_create_combat
from world.combat.utils import add_combatant


class _InitiateSpy:
    """Records who gets an `initiate` message, delegating to the real one.

    Counting calls rather than matching text: the message banks are
    random, so asserting on a specific line would pass or fail on a dice
    roll rather than on the defect.
    """

    def __init__(self):
        self.initiators = []
        self._real = core_actions.get_combat_message

    def __call__(self, weapon_type, phase, attacker=None, target=None, **kw):
        if phase == "initiate":
            self.initiators.append(attacker)
        return self._real(weapon_type, phase, attacker=attacker,
                          target=target, **kw)


class BodyDoesNotSquareUpTest(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.bravo = create_object("typeclasses.characters.Character",
                                   key="Bravo", location=self.room1)

    def _kill(self, char):
        ms = char.medical_state
        ms.blood_level = 0
        ms._cached_is_dead = None
        return char

    def _knock_out(self, char):
        char.medical_state.consciousness = 0.0
        return char

    def _attack(self):
        spy = _InitiateSpy()
        with patch.object(core_actions, "get_combat_message", spy):
            self.call(CmdAttack(), "Bravo", caller=self.char1)
        return spy

    # --- control ---------------------------------------------------------

    def test_a_healthy_target_does_square_up(self):
        # Passes on the fixed and unfixed tree alike. Without it, "the
        # target sent no initiate" cannot be told apart from a command
        # that never reached the messaging at all.
        spy = self._attack()
        self.assertIn(self.char1, spy.initiators, "attacker never initiated")
        self.assertIn(self.bravo, spy.initiators,
                      "a healthy target should react defensively")

    # --- the defect ------------------------------------------------------

    def test_a_dead_target_does_not_square_up(self):
        self._kill(self.bravo)
        self.assertTrue(self.bravo.is_dead(), "fixture failed to kill Bravo")
        spy = self._attack()
        self.assertNotIn(self.bravo, spy.initiators,
                         "a dead character emitted a combat initiate pose")

    def test_an_unconscious_target_does_not_square_up(self):
        self._knock_out(self.bravo)
        self.assertTrue(self.bravo.is_unconscious(),
                        "fixture failed to knock Bravo out")
        spy = self._attack()
        self.assertNotIn(self.bravo, spy.initiators,
                         "an unconscious character emitted a combat pose")

    def test_a_body_is_still_attackable(self):
        # The half the issue explicitly allowed. If this fails, the fix
        # went too far and made corpses unattackable.
        self._kill(self.bravo)
        spy = self._attack()
        self.assertIn(self.char1, spy.initiators,
                      "the attacker stopped being able to attack a body")


class RoundLoopEjectsTheIncapacitatedTest(EvenniaTest):
    """Regression pins for the half that was already correct.

    The sweep runs on the ticker between player commands, so these
    simulate a round directly rather than probing after a command.
    """

    def _arena(self, key):
        room = create_object("typeclasses.rooms.Room", key=key)
        a = create_object("typeclasses.characters.Character", key="Alpha",
                          location=room)
        b = create_object("typeclasses.characters.Character", key="Bravo",
                          location=room)
        handler = get_or_create_combat(room)
        add_combatant(handler, a, target=b)
        add_combatant(handler, b, target=a)
        return a, b, handler

    def _names(self, handler):
        return sorted(e.get("char").key
                      for e in (handler.db.combatants or []) if e.get("char"))

    def test_control_two_healthy_fighters_keep_fighting(self):
        a, b, handler = self._arena("control arena")
        handler.at_repeat()
        self.assertEqual(self._names(handler), ["Alpha", "Bravo"])
        self.assertTrue(handler.pk, "handler dissolved on a live fight")

    def test_a_dead_combatant_is_ejected_and_combat_ends(self):
        a, b, handler = self._arena("dead arena")
        b.medical_state.blood_level = 0
        b.medical_state._cached_is_dead = None
        handler.at_repeat()
        self.assertEqual(self._names(handler), [])
        self.assertFalse(handler.pk, "handler survived with nobody left")

    def test_an_unconscious_combatant_is_ejected(self):
        a, b, handler = self._arena("ko arena")
        b.medical_state.consciousness = 0.0
        handler.at_repeat()
        self.assertNotIn("Bravo", self._names(handler))
