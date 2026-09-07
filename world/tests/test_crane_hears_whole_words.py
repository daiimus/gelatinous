""""crane, stop" does not mean floor seventeen (#2440).

The named-destination lists were plain substring tests:

```python
if any(w in low for w in ("top", "topmost", "highest", "the top", ...)):
    return self.MAX_FLOOR, False
```

`"top" in "stop"` is True. So an emergency stop parsed as a named
destination, returned `(17, False)` — **not relative** — and therefore
skipped the read-back guard that only relative orders get. It went
straight to `_run_crane(17)`: *"Copy, the 17th. Bringing her up..."*,
and the container, which is a room with people standing in it, went to
the top of the mast.

The phrase most likely to be shouted at a crane was the phrase that
bypassed the safety #2217 added.

The relative branch and both numeric branches were already
`\\b`-anchored — only these lists drifted, which is why the suite stayed
green: the existing cases cover "all the way to the top" and "take her
to the top", both of which legitimately mean 17.

`_mentions` tolerates a trailing plural so "the cranes", "operators"
and "docked" keep addressing the crane the way they always did.

**Not addressed here, and it needs an owner call:** "crane, stop" now
gets *"Say again — which floor?"* rather than halting anything. That is
strictly better than driving to the mast top, but it is not a stop. A
real halt would cancel the two-second `delay` between the copy and
`move_to_level`; whether the crane should gain that verb is a design
question, filed separately.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.crane import CraneConsole


class _ParseCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.console = self.obj1
        self.console.swap_typeclass("typeclasses.crane.CraneConsole",
                                    clean_attributes=False,
                                    run_start_hooks=None)
        self.car = mock.MagicMock()
        self.car.db.level = 1

    def floor(self, speech):
        return self.console._parse_floor(speech.lower(), self.car)

    def addressed(self, speech):
        return self.console._mentions(speech.lower(), CraneConsole._ADDRESS)


class TestStopIsNotTheTop(_ParseCase):
    def test_stop_reads_as_no_floor(self):
        self.assertEqual(self.floor("crane, stop"), (None, False))

    def test_shouted_stop_reads_as_no_floor(self):
        self.assertEqual(self.floor("ossie, STOP!"), (None, False))

    def test_repeated_stop_reads_as_no_floor(self):
        self.assertEqual(self.floor("crane stop stop stop"), (None, False))

    def test_stopped_reads_as_no_floor(self):
        self.assertEqual(self.floor("crane, is she stopped?"), (None, False))

    def test_nonstop_reads_as_no_floor(self):
        self.assertEqual(self.floor("crane, nonstop today huh"),
                         (None, False))


class TestTheOtherCollisions(_ParseCase):
    """Same family, same file — flagged in the issue at lower severity."""

    def test_underground_is_not_the_ground_floor(self):
        self.assertEqual(self.floor("operator, the underground is flooded"),
                         (None, False))

    def test_playground_is_not_the_ground_floor(self):
        self.assertEqual(self.floor("watch the playground on the way down"),
                         (None, False))

    def test_a_candle_does_not_address_the_crane(self):
        self.assertFalse(self.addressed("the candle blew out again"))

    def test_a_cup_is_not_an_order(self):
        self.assertFalse(
            self.console._mentions("hand me that cup", CraneConsole._INTENT))


class TestTheRealOrdersStillWork(_ParseCase):
    """The whole point of the lists — these must not regress."""

    def test_take_her_to_the_top(self):
        self.assertEqual(self.floor("crane, take her to the top"),
                         (CraneConsole.MAX_FLOOR, False))

    def test_all_the_way_to_the_top(self):
        self.assertEqual(self.floor("all the way to the top please"),
                         (CraneConsole.MAX_FLOOR, False))

    def test_topmost(self):
        self.assertEqual(self.floor("crane, topmost floor"),
                         (CraneConsole.MAX_FLOOR, False))

    def test_seventeenth(self):
        self.assertEqual(self.floor("take her to the seventeenth"),
                         (CraneConsole.MAX_FLOOR, False))

    def test_the_ground(self):
        self.assertEqual(self.floor("bring her to the ground"),
                         (CraneConsole.MIN_FLOOR, False))

    def test_dock_her(self):
        self.assertEqual(self.floor("crane, dock her"),
                         (CraneConsole.MIN_FLOOR, False))

    def test_docked(self):
        self.assertEqual(self.floor("crane, get her docked"),
                         (CraneConsole.MIN_FLOOR, False))

    def test_street_level(self):
        self.assertEqual(self.floor("take her to street level"),
                         (CraneConsole.MIN_FLOOR, False))

    def test_a_plain_number_is_untouched(self):
        self.assertEqual(self.floor("crane, twelfth floor"), (12, False))

    def test_a_relative_order_is_still_relative(self):
        floor, relative = self.floor("crane, bring her down two")
        self.assertTrue(relative, "the read-back guard was lost")


class TestAddressingStillWorks(_ParseCase):
    def test_the_crane_answers_to_its_name(self):
        self.assertTrue(self.addressed("crane, take her up one"))

    def test_and_to_its_plural(self):
        self.assertTrue(self.addressed("cranes, come in"))

    def test_and_to_the_operator(self):
        self.assertTrue(self.addressed("operator, you there?"))

    def test_and_to_a_multi_word_handle(self):
        self.assertTrue(self.addressed("boiler run, come back"))

    def test_plain_chatter_is_still_ignored(self):
        self.assertFalse(self.addressed("anybody got a light"))
