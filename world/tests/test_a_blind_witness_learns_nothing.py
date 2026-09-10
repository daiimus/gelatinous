"""An unmasking is only witnessed by those who can perceive it (#2647).

`_collect_unmasking_observers` filtered on location, self,
`recognition_memory` and consciousness. It never asked whether the
observer could actually SEE the person unmasking, or whether that person
was hidden from them — and what it returns is written into PERSISTENT
recognition memory.

So a blind character learned who was behind a mask, permanently. So did
one the unmasker was hidden from. Being in the room is not the same as
seeing what happens in it, and that was the only kind of perception this
modelled.

Both new gates fail OPEN, matching `world/perception`'s own polarity: no
medical model, no stealth surface, or an exception, and the observer
stays in. Only an affirmative "cannot" removes anyone.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.identity import _collect_unmasking_observers
from world import perception as perception_mod


class _Room(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.masked = self.char1
        self.watcher = self.char2
        self.masked.location = self.room1
        self.watcher.location = self.room1


class TestTheOrdinaryWitnessStillSees(_Room):

    def test_somebody_in_the_room_witnesses_it(self):
        """Control: if nobody were ever collected, every exclusion
        below would pass for the wrong reason."""
        self.assertIn(self.watcher,
                      _collect_unmasking_observers(self.masked))

    def test_the_unmasker_does_not_witness_themselves(self):
        self.assertNotIn(self.masked,
                         _collect_unmasking_observers(self.masked))

    def test_somebody_elsewhere_does_not(self):
        self.watcher.location = self.room2
        self.assertNotIn(self.watcher,
                         _collect_unmasking_observers(self.masked))


class TestTheBlindLearnNothing(_Room):

    def test_a_blind_observer_is_excluded(self):
        with patch.object(perception_mod, "can_see",
                          side_effect=lambda who: who is not self.watcher):
            self.assertNotIn(self.watcher,
                             _collect_unmasking_observers(self.masked))

    def test_a_sighted_one_beside_them_is_not(self):
        """Control: the gate is per-observer, not per-room."""
        third = create_object("typeclasses.characters.Character",
                              key="Cee", location=self.room1)
        with patch.object(perception_mod, "can_see",
                          side_effect=lambda who: who is not self.watcher):
            observers = _collect_unmasking_observers(self.masked)
        self.assertNotIn(self.watcher, observers)
        self.assertIn(third, observers)


class TestTheHiddenRevealNothing(_Room):

    def test_an_observer_the_unmasker_is_hidden_from_is_excluded(self):
        with patch.object(perception_mod, "can_perceive",
                          side_effect=lambda looker, target: False):
            self.assertNotIn(self.watcher,
                             _collect_unmasking_observers(self.masked))

    def test_the_gate_asks_about_the_right_pair(self):
        """`can_perceive(looker, target)` — the OBSERVER must perceive
        the UNMASKER, not the other way round. Reversed, a hidden
        watcher would be the one excluded."""
        seen = []
        with patch.object(perception_mod, "can_perceive",
                          side_effect=lambda looker, target: (
                              seen.append((looker, target)) or True)):
            _collect_unmasking_observers(self.masked)
        self.assertIn((self.watcher, self.masked), seen)


class TestItFailsOpen(_Room):
    """Nothing that merely lacks the machinery is excluded — the same
    polarity `is_conscious` uses."""

    def test_a_raising_perception_layer_keeps_everyone(self):
        with patch.object(perception_mod, "can_see",
                          side_effect=RuntimeError("no medical model")):
            self.assertIn(self.watcher,
                          _collect_unmasking_observers(self.masked))

    def test_and_so_does_a_raising_stealth_layer(self):
        with patch.object(perception_mod, "can_perceive",
                          side_effect=RuntimeError("no stealth surface")):
            self.assertIn(self.watcher,
                          _collect_unmasking_observers(self.masked))
