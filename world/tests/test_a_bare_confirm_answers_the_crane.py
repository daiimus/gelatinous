""""Confirmed" answers the crane (#2472).

The crane reads a relative order back — *"That puts her at the 5th.
Confirm?"* — and a caller who answered "confirmed" got **silence**. The
read-back then expired unanswered 45 seconds later.

`_handle` ran the address gate first:

```python
if not self._mentions(low, self._ADDRESS):
    return                       # band chatter, not an order
```

and no word in `_CONFIRM` appears in `_ADDRESS`, so a bare confirmation
never reached the confirmation branch below it. The only way to answer
was to re-address the crane — *"crane, confirmed"* — which the prompt
never said and which is not how anyone answers a radio.

Relative orders are the **only** ones that go through this handshake,
and they are precisely the dangerous ones: the container is a room with
people standing in it, and "down two" is the order a tired operator and
a tired caller can mean differently (#2217). So the one prompt that
exists for safety was the one that ignored "yes".

**Owner ruling, 2026-09-06:** *"A bare confirm should work. It's
literally the frequency for the crane."* Being on band 27.0 is the
addressing.

The accepted cost, stated plainly: a stray "yeah" from someone else on
band inside the 45-second window will now confirm. The window only opens
after this crane has asked a question, and it was judged the better
trade against a prompt nobody could answer.
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

    _UNSET = object()

    def order(self, speech, operator=_UNSET):
        """One transmission on band 27.0. Returns what the crane said
        and whether the car was driven.

        `operator` uses a sentinel default, not None: the point of
        `test_no_operator_means_no_move` is to pass None through, and a
        `None`-means-default helper silently substitutes a real operator
        and the test passes for the wrong reason.
        """
        op = self.char2 if operator is self._UNSET else operator
        with mock.patch.object(CraneConsole, "_find_car",
                               return_value=self.car), \
             mock.patch.object(CraneConsole, "_operator", return_value=op), \
             mock.patch.object(CraneConsole, "_answer") as answered, \
             mock.patch.object(CraneConsole, "_run_crane") as ran, \
             mock.patch("world.radio.same_band", return_value=True):
            self.console.at_msg_receive(
                type="radio", speech=speech, from_obj=self.char1,
                radio_frequency="27.0")
        said = " ".join(str(c.args[0]) for c in answered.call_args_list
                        if c.args)
        drove = [c.args[0] for c in ran.call_args_list]
        return said, drove


class TestTheReadBackStillHappens(_CraneCase):
    def test_a_relative_order_is_read_back(self):
        said, drove = self.order("crane, take her up two")
        self.assertIn("Confirm?", said)
        self.assertEqual(drove, [], "it moved without confirmation")

    def test_a_plain_floor_is_not_read_back(self):
        said, drove = self.order("crane, twelfth floor")
        self.assertNotIn("Confirm?", said)
        self.assertEqual(drove, [12])


class TestABareConfirmAnswersIt(_CraneCase):
    def confirm_with(self, word):
        self.order("crane, take her up two")
        return self.order(word)

    def test_confirmed(self):
        _said, drove = self.confirm_with("confirmed")
        self.assertEqual(drove, [4])

    def test_yes(self):
        _said, drove = self.confirm_with("yes")
        self.assertEqual(drove, [4])

    def test_roger(self):
        _said, drove = self.confirm_with("roger")
        self.assertEqual(drove, [4])

    def test_go_ahead(self):
        _said, drove = self.confirm_with("go ahead")
        self.assertEqual(drove, [4])

    def test_re_addressing_still_works(self):
        """The old workaround must not break."""
        _said, drove = self.confirm_with("crane, confirmed")
        self.assertEqual(drove, [4])


class TestItDoesNotConfirmOutOfNowhere(_CraneCase):
    """The window only opens after the crane has asked something."""

    def test_a_bare_yes_with_nothing_pending_moves_nothing(self):
        _said, drove = self.order("yes")
        self.assertEqual(drove, [])

    def test_a_bare_yes_with_nothing_pending_says_nothing(self):
        said, _drove = self.order("yeah, sure")
        self.assertEqual(said, "")

    def test_plain_chatter_is_still_ignored(self):
        said, drove = self.order("anybody got a light")
        self.assertEqual((said, drove), ("", []))

    def test_an_expired_read_back_is_not_confirmable(self):
        from typeclasses.crane import CraneConsole as CC
        self.order("crane, take her up two")
        floor, asked_at = self.console.ndb.pending
        self.console.ndb.pending = (floor, asked_at - CC.CONFIRM_WINDOW - 1)
        _said, drove = self.order("confirmed")
        self.assertEqual(drove, [])

    def test_confirming_twice_only_moves_once(self):
        self.order("crane, take her up two")
        self.order("confirmed")
        _said, drove = self.order("confirmed")
        self.assertEqual(drove, [], "the read-back was reusable")


class TestTheUnmannedCabStillGoesQuiet(_CraneCase):
    """The 2026-08-22 ruling: an empty chair never drives the hoist —
    a bare confirmation must not become a way around it."""

    def test_no_operator_means_no_move(self):
        self.order("crane, take her up two")
        _said, drove = self.order("confirmed", operator=None)
        self.assertEqual(drove, [])
