"""Waking up gives you your commands back (#2416).

`apply_unconscious_state` swaps in `UnconsciousCmdSet` via `add_default`,
which is PERSISTENT -- it survives a reload and a reconnect. Only
`remove_unconscious_state` puts `CharacterCmdSet` back, and it had three
call sites: `@heal`, `@testunconscious` (both Builder-locked) and the
death transition.

The natural-recovery branch of the medical tick was not one of them. It
cleared `ndb.unconsciousness_processed` and `override_place` and stopped.
So a character who went down to pain, blood loss or sedation and came
round on their own stood up in the room description holding `help`,
`who`, `time` and `quit`: no `look`, no movement, no actions, and
reconnecting did not clear it.

The medical model owned half the transition and the command layer owned
the other half, and only the first half ever ran.

This is the scenario `world/medical/constants.py:205-213` was explicitly
tuned for -- "a blackout is a brief nap, not a ~30-minute lockout".

These tests assert what a PLAYER can do, by looking for the commands in
the cmdset the character actually ends up with, rather than asserting
which cmdset object was installed. A blackout that ends with no `look` is
the bug, whatever the mechanism is called.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


def _command_keys(char):
    """Every command key *char* can actually reach right now.

    `cmdset.get()` returns the whole STACK, which still holds the
    character's other cmdsets and so answers "yes, look exists" even
    while the player cannot type it. The merged `current` set is what the
    command handler resolves against, which is what the player has.
    """
    char.cmdset.update()
    return {cmd.key for cmd in char.cmdset.current.commands}


class _BlackoutCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1

    def go_under(self):
        """`apply_unconscious_state` no-ops unless the character really
        is unconscious, and again for staff -- `force_test` is the flag
        `@testunconscious` uses to drive it directly."""
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True

    def wake_via_the_medical_tick(self):
        """Drive the real recovery branch of `MedicalScript.at_repeat`."""
        from evennia import create_script
        from world.medical.script import MedicalScript

        script = create_script(MedicalScript, obj=self.char, autostart=False)
        state = mock.MagicMock()
        state.conditions = [mock.MagicMock(requires_ticker=False)]
        state.is_dead.return_value = False
        state.is_unconscious.return_value = False
        with mock.patch.object(type(self.char), "medical_state",
                               new_callable=mock.PropertyMock,
                               return_value=state):
            script.at_repeat()
        return script


class TestGoingUnderTakesTheCommandsAway(_BlackoutCase):
    def test_an_unconscious_character_cannot_look(self):
        self.char.apply_unconscious_state(force_test=True)
        self.assertNotIn("look", _command_keys(self.char))

    def test_they_keep_the_out_of_character_ones(self):
        self.char.apply_unconscious_state(force_test=True)
        keys = _command_keys(self.char)
        self.assertIn("help", keys)
        self.assertIn("quit", keys)


class TestComingRoundGivesThemBack(_BlackoutCase):
    def test_look_works_again_after_natural_recovery(self):
        """The whole finding. Not `@heal`, not death -- coming round on
        your own, which is the common case."""
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        self.wake_via_the_medical_tick()
        self.assertIn("look", _command_keys(self.char))

    def test_movement_works_again(self):
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        self.wake_via_the_medical_tick()
        self.assertIn("get", _command_keys(self.char))

    def test_the_processed_flag_is_cleared(self):
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        self.wake_via_the_medical_tick()
        self.assertFalse(getattr(self.char.ndb,
                                 "unconsciousness_processed", False))

    def test_the_unconscious_placement_is_cleared(self):
        """`remove_unconscious_state` clears the same `override_place`
        the branch used to clear by hand, so nothing was lost by
        deferring to it."""
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        self.wake_via_the_medical_tick()
        self.assertIsNone(self.char.override_place or None)

    def test_the_player_is_told(self):
        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        said = []
        with mock.patch.object(type(self.char), "msg",
                               side_effect=lambda text=None, **kw:
                               said.append(str(text))):
            self.wake_via_the_medical_tick()
        self.assertTrue(any("regain" in s.lower() for s in said),
                        f"nothing said about waking up: {said}")


class TestRecoveryDoesNotFireForTheDead(_BlackoutCase):
    def test_a_dead_character_is_not_given_their_commands_back(self):
        """`apply_death_state` installs `DeathCmdSet`; the recovery
        branch must not undo it."""
        from evennia import create_script
        from world.medical.script import MedicalScript

        self.char.apply_unconscious_state(force_test=True)
        self.char.ndb.unconsciousness_processed = True
        script = create_script(MedicalScript, obj=self.char, autostart=False)
        state = mock.MagicMock()
        state.conditions = [mock.MagicMock(requires_ticker=False)]
        state.is_dead.return_value = True
        state.is_unconscious.return_value = False
        with mock.patch.object(type(self.char), "medical_state",
                               new_callable=mock.PropertyMock,
                               return_value=state):
            script.at_repeat()
        self.assertNotIn("look", _command_keys(self.char))
