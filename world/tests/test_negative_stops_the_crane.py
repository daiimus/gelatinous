"""The crane console hears a refusal, and re-checks the chair before it
drives (#2624).

**No negative vocabulary existed anywhere in the file.** `_handle` armed
`ndb.pending` on a read-back and cleared it in exactly three places —
confirmation, a fresh parseable floor, and a 45-second expiry. So
"negative" did nothing at all, the read-back stayed armed, and any
stray "roger" on band 27.0 inside that window drove the car to the floor
that had just been refused. The container is a ROOM; somebody is
standing in it.

**And `_drive` moved the car before re-checking the chair.** The module
opens by stating the invariant — *"an unmanned crane must never drive
itself: somebody could be standing in it"* — and `_handle` enforced it
at HEAR time only. Two seconds pass between the copy and the drive. An
operator who stands up, is dragged out or dies inside that beat has
stopped being the operator, and the car moved anyway; the re-read that
was already there only decided who NARRATES the landing.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.crane as cmod


def _console(operator=None, car=None):
    console = MagicMock(name="console")
    console.ndb = SimpleNamespace(pending=None)
    console.key = "crane console"
    console.id = 1
    for name in ("_handle", "_is_confirmation", "_is_refusal",
                 "_pending_floor", "_drive"):
        real = getattr(cmod.CraneConsole, name, None)
        if real is not None:
            setattr(console, name, real.__get__(console, cmod.CraneConsole))
    for name in ("_CONFIRM", "_DENY", "CONFIRM_WINDOW", "QOC_FLOOR",
                 "MIN_FLOOR", "MAX_FLOOR"):
        if hasattr(cmod.CraneConsole, name):
            setattr(console, name, getattr(cmod.CraneConsole, name))
    console._operator.return_value = operator
    console._find_car.return_value = car
    # Explicit defaults: a bare MagicMock answers every question yes and
    # unpacks into nothing, which turns a behavioural failure into a
    # TypeError three frames away from the thing under test.
    console._parse_floor.return_value = (None, False)
    console._mentions.return_value = False
    return console


class TestARefusalIsHeard(TestCase):

    def setUp(self):
        self.console = _console(operator=MagicMock(name="Ossie"),
                                car=MagicMock(name="car"))

    def hear(self, line):
        """`_handle(speech, speaker, kwargs)` — the radio's own shape."""
        return self.console._handle(line, MagicMock(name="caller"), {})

    def test_a_confirmation_still_runs_it(self):
        """Control: if confirmation were broken, every refusal
        assertion below would pass for the wrong reason."""
        self.console.ndb.pending = (4, cmod.monotonic())
        self.hear("roger")
        self.console._run_crane.assert_called_once()

    def test_negative_does_not(self):
        self.console.ndb.pending = (4, cmod.monotonic())
        self.hear("negative")
        self.console._run_crane.assert_not_called()

    def test_and_it_disarms_the_read_back(self):
        """The one that mattered: a refused read-back that stays armed
        is answered by the next stray 'roger' on band."""
        self.console.ndb.pending = (4, cmod.monotonic())
        self.hear("negative")
        self.assertIsNone(self.console.ndb.pending)
        self.hear("roger")
        self.console._run_crane.assert_not_called()

    def test_the_caller_is_told(self):
        self.console.ndb.pending = (4, cmod.monotonic())
        self.hear("negative")
        said = " ".join(str(c.args[0]) for c in
                        self.console._answer.call_args_list if c.args)
        self.assertIn("Belayed", said)

    def test_a_refusal_beats_a_confirmation_in_one_breath(self):
        """Moving is the irreversible half, so both words means no."""
        self.console.ndb.pending = (4, cmod.monotonic())
        self.hear("negative — no, cancel that, roger?")
        self.console._run_crane.assert_not_called()

    def test_a_refusal_with_no_read_back_pending_is_just_chatter(self):
        """Control: `negative` on band with nothing armed must not
        become an address of its own."""
        self.hear("negative")
        self.console._answer.assert_not_called()


class TestTheChairIsCheckedBeforeTheCarMoves(TestCase):

    def test_an_empty_chair_stops_the_drive(self):
        car = MagicMock(name="car")
        console = _console(operator=None, car=car)
        console._drive(car, 3, 3, MagicMock(name="the operator who left"))
        car.move_to_level.assert_not_called()

    def test_and_nothing_is_announced(self):
        """The console does not speak for itself — an unmanned station
        goes quiet (owner ruling, 2026-08-22)."""
        car = MagicMock(name="car")
        console = _console(operator=None, car=car)
        console._drive(car, 3, 3, MagicMock())
        console._answer.assert_not_called()

    def test_a_manned_chair_still_drives(self):
        """Control: the guard has not simply stopped the crane."""
        car = MagicMock(name="car")
        console = _console(operator=MagicMock(name="Ossie"), car=car)
        console._drive(car, 3, 3, MagicMock())
        car.move_to_level.assert_called_once_with(3)
        console._answer.assert_called()
