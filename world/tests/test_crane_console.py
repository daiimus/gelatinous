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
        """Just the floor — relative-ness is pinned separately below."""
        return self.console._parse_floor(text.lower(), self.car)[0]

    def _parse(self, text):
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

    def test_relative_orders_are_arithmetic_not_floor_numbers(self):
        """"Down two" used to reach the spelled-out-number branch and
        mean FLOOR 2 — sending the car to the bottom of the shaft with
        people standing in it, because the container is a room (#2217).

        Relative is read first now: a direction word with a count is
        arithmetic, whatever the count happens to look like."""
        self.car.db.level = 5                    # floor 6
        self.assertEqual(self._parse("up one"), (7, True))
        self.assertEqual(self._parse("up a floor"), (7, True))
        self.assertEqual(self._parse("down 1"), (5, True))
        self.assertEqual(self._parse("up two"), (8, True))     # was 2
        self.assertEqual(self._parse("down two"), (4, True))   # was 2

    def test_a_floor_called_out_plainly_is_absolute(self):
        """No direction word, no arithmetic — just take them there."""
        self.car.db.level = 5
        self.assertEqual(self._parse("floor 9"), (9, False))
        self.assertEqual(self._parse("the twelfth"), (12, False))
        self.assertEqual(self._parse("take her to the top"), (17, False))

    def test_going_up_TO_a_floor_is_still_absolute(self):
        """"Up to nine" names a floor; "up nine" counts nine of them."""
        self.car.db.level = 5
        self.assertEqual(self._parse("bring her up to nine"), (9, False))

    def test_bare_direction_words_move_nothing(self):
        self.car.db.level = 5
        self.assertIsNone(self._floor("nice weather up there"))

    def test_nothing_readable_is_none(self):
        self.assertIsNone(self._floor("how's the family"))


class TestArithmeticIsReadBack(_CraneCase):
    """A floor named plainly is taken at once; a floor WORKED OUT is
    confirmed first, because the car is a room with people in it
    (owner ruling, 2026-08-23)."""

    def test_a_relative_order_asks_before_it_moves(self):
        self.car.db.level = 8                    # floor 9
        answered = self._order("crane, bring her down two",
                               operator=self.char2)
        self.assertTrue(answered.called)
        self.assertIn("7th", answered.call_args[0][0])
        self.assertIn("confirm", answered.call_args[0][0].lower())
        self.car.move_to_level.assert_not_called()

    def test_confirming_moves_it(self):
        self.car.db.level = 8
        self._order("crane, bring her down two", operator=self.char2)
        self._order("crane, confirmed", operator=self.char2)
        # the copy goes out and the drive is scheduled a beat later
        self.assertIsNone(self.console.ndb.pending)

    def test_a_plain_floor_is_taken_at_once(self):
        answered = self._order("crane, ninth floor", operator=self.char2)
        self.assertTrue(answered.called)
        self.assertNotIn("confirm", answered.call_args[0][0].lower())

    def test_a_yes_out_of_the_blue_moves_nothing(self):
        answered = self._order("crane, yes", operator=self.char2)
        self.assertIsNone(self.console.ndb.pending)
