"""The crane answers the chair, not the man (#2216).

Ossie's typeclass used to BE the crane: `CraneOperator._hear_radio`
held the band gate, the floor parser and the drive call, so the hoist
answered him and nobody else. A relief operator would have sat in that
chair mute.

It lives on the console now, on the `AnsweringFixture` standard, which
means the day shift can change hands without the crane going deaf —
and an EMPTY cab never drives itself, because the container is a room
and somebody may be standing in it.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.crane import CraneConsole


class _CraneCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.console = self.obj1
        self.console.swap_typeclass("typeclasses.crane.CraneConsole",
                                    clean_attributes=False,
                                    run_start_hooks=None)
        self.console.location = self.room1
        self.car = mock.MagicMock()
        self.car.db.level = 1

    def _order(self, speech, operator=None, band="27.0"):
        with mock.patch.object(CraneConsole, "_find_car",
                               return_value=self.car), \
             mock.patch.object(CraneConsole, "_operator",
                               return_value=operator), \
             mock.patch.object(CraneConsole, "_answer") as answered, \
             mock.patch("world.radio.same_band",
                        return_value=(band == "27.0")):
            self.console.at_msg_receive(
                type="radio", speech=speech, from_obj=self.char1,
                radio_frequency=band)
        return answered


class TestTheChairDrivesIt(_CraneCase):
    def test_an_order_with_an_operator_moves_the_car(self):
        self._order("crane, take her to the ninth", operator=self.char2)
        self.car.move_to_level.assert_not_called()   # driven after a beat
        # the copy goes out immediately, in the operator's voice
        # (the move itself is delayed by design)

    def test_an_empty_cab_never_drives_itself(self):
        """The container is a ROOM — an unmanned crane must not move."""
        self._order("crane, take her to the ninth", operator=None)
        self.car.move_to_level.assert_not_called()

    def test_an_empty_cab_says_nothing_at_all(self):
        """Nobody in the cab, so nobody picks up. The console does not
        speak for itself — an unmanned station going quiet is the
        consequence of an NPC-operated world (owner ruling,
        2026-08-22)."""
        answered = self._order("crane, ninth floor", operator=None)
        self.assertFalse(answered.called)

    def test_chatter_is_not_an_order(self):
        """A transmission must ADDRESS the crane, or 'heading up to the
        second' would drive the hoist."""
        answered = self._order("heading up to the second in a minute",
                               operator=self.char2)
        self.assertFalse(answered.called)

    def test_another_band_is_ignored(self):
        answered = self._order("crane, ninth floor", operator=self.char2,
                               band="911")
        self.assertFalse(answered.called)

    def test_an_unreadable_floor_asks_again(self):
        answered = self._order("crane, take her up somewhere",
                               operator=self.char2)
        self.assertTrue(answered.called)
        self.assertIn("say again", answered.call_args[0][0].lower())


class TestFloorParsing(EvenniaCommandTest):
    """Moved wholesale from the operator; pinned so the move is faithful."""

    def setUp(self):
        super().setUp()
        self.console = self.obj1
        self.console.swap_typeclass("typeclasses.crane.CraneConsole",
                                    clean_attributes=False,
                                    run_start_hooks=None)
        self.car = mock.MagicMock()
        self.car.db.level = 1

    def _floor(self, text):
        return self.console._parse_floor(text.lower(), self.car)

    def test_named_destinations(self):
        self.assertEqual(self._floor("take her to the dock"), 2)
        self.assertEqual(self._floor("all the way to the top"), 17)
        self.assertEqual(self._floor("level with the queen"), 13)

    def test_digits_and_ordinals(self):
        self.assertEqual(self._floor("floor 9"), 9)
        self.assertEqual(self._floor("the 12th"), 12)

    def test_spelled_out(self):
        self.assertEqual(self._floor("bring her to eleven"), 11)

    def test_a_typo_in_a_teen_still_lands(self):
        self.assertEqual(self._floor("take her to forteen"), 14)

    def test_relative_works_for_the_counts_that_reach_it(self):
        """Pins ACTUAL behaviour, which is narrower than intended.

        The absolute branches run first, so a relative order only
        survives when its count is not a number word ("one", "a floor",
        "a level") and not a digit the floor regex claims. "up two"
        reads as FLOOR 2, not up-by-two — see #2217, raised separately
        rather than fixed inside a standardisation change.
        """
        self.car.db.level = 5                    # floor 6
        self.assertEqual(self._floor("up one"), 7)
        self.assertEqual(self._floor("up a floor"), 7)
        self.assertEqual(self._floor("down 1"), 5)
        # the documented-but-broken forms, pinned so the fix is visible
        self.assertEqual(self._floor("up two"), 2)      # intended: 8
        self.assertEqual(self._floor("down two"), 2)    # intended: 4

    def test_bare_direction_words_move_nothing(self):
        self.car.db.level = 5
        self.assertIsNone(self._floor("nice weather up there"))

    def test_nothing_readable_is_none(self):
        self.assertIsNone(self._floor("how's the family"))
