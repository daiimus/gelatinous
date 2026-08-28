"""Some posts are worked SITTING DOWN (#2225).

`world.radio.seated_base_station` has been the law for a while — a
console is desk work, you take the chair, and whoever holds the chair
holds the voice. But nothing in the souls layer ever put anybody in a
chair. Placement was cosmetic (`temp_place`), so an operator "at her
console" was standing next to it, which meant `active_transmit_radio`
found nothing and she could not key up at all.

That went unnoticed for as long as the console did the talking. The
moment the voice became hers (#2223), the empty chair became the
difference between a dispatcher and a mute.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls.jobs import _leave_the_post, _post_seat, _take_the_post


def _run_sit(caller, target):
    """Drive the real `sit` command.

    `caller.execute_cmd` — which is what the souls layer actually calls,
    and what the NPC-uses-real-commands mandate requires — does not
    dispatch under `EvenniaCommandTest`, which gives its characters no
    session. So the mock-based tests below pin that the right command
    string is ISSUED, and the state-level ones drive the same command
    class directly to pin what it does."""
    from commands.CmdFurniture import CmdSit
    cmd = CmdSit()
    cmd.caller = caller
    cmd.args = f" on {target.key}"
    cmd.func()


class _SeatCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.post = self.room1
        self.soul.db.soul_post = self.post
        self.chair = self.obj1
        self.chair.swap_typeclass("typeclasses.furniture.Furniture",
                                  clean_attributes=False,
                                  run_start_hooks="all")
        self.chair.location = self.post
        self.chair.key = "the dispatch chair"
        self.chair.db.post_work_seat = True
        self.soul.location = self.post


class TestFindingTheChair(_SeatCase):
    def test_a_declared_seat_is_found(self):
        self.assertIs(_post_seat(self.soul), self.chair)

    def test_ordinary_furniture_is_not_a_work_seat(self):
        """A waiting-room bench in the same room must not claim the
        keeper — the post declares its own chair."""
        self.chair.db.post_work_seat = None
        self.assertIsNone(_post_seat(self.soul))

    def test_no_post_no_seat(self):
        self.soul.db.soul_post = None
        self.assertIsNone(_post_seat(self.soul))


class TestTakingTheChair(_SeatCase):
    def test_starting_the_shift_sits_down(self):
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _take_the_post(self.soul)
        ran.assert_called_once_with("sit on the dispatch chair")

    def test_the_command_it_issues_actually_seats_her(self):
        """Not a direct `db.furniture` poke: occupancy, posture and the
        room messaging all have to hold, and a full chair has to refuse
        exactly as it would for a player."""
        _run_sit(self.soul, self.chair)
        self.assertIs(self.soul.db.furniture, self.chair)
        self.assertEqual(self.soul.db.posture, "sitting")

    def test_already_seated_does_not_re_sit_every_beat(self):
        _run_sit(self.soul, self.chair)
        self.soul.db.seated_by_shift = True
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _take_the_post(self.soul)
        ran.assert_not_called()

    def test_a_post_with_no_chair_is_unchanged(self):
        self.chair.db.post_work_seat = None
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _take_the_post(self.soul)
        ran.assert_not_called()

    def test_a_chair_in_another_room_is_not_taken(self):
        """Placement is cosmetic and can run anywhere; sitting cannot."""
        self.chair.location = self.room2
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _take_the_post(self.soul)
        ran.assert_not_called()

    def test_a_squatted_chair_is_not_fought_over(self):
        """Somebody else in the seat keeps it. A desk that can\'t
        broadcast is content, not a bug — and she doesn\'t retry into a
        refusal every beat of the shift."""
        _run_sit(self.char2, self.chair)
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _take_the_post(self.soul)
        ran.assert_not_called()


class TestGivingItBack(_SeatCase):
    def test_ending_the_shift_stands_up(self):
        _run_sit(self.soul, self.chair)
        self.soul.db.seated_by_shift = True
        with mock.patch.object(type(self.soul), "execute_cmd") as ran:
            _leave_the_post(self.soul)
        ran.assert_called_once_with("stand")

    def test_a_seat_we_did_not_take_is_left_alone(self):
        """Somebody who sat down of their own accord — a player-posed
        NPC, an off-shift regular — is not stood up by a shift ending."""
        _run_sit(self.soul, self.chair)
        self.assertIs(self.soul.db.furniture, self.chair)
        _leave_the_post(self.soul)                  # never seated BY the shift
        self.assertIs(self.soul.db.furniture, self.chair)


class TestTheChairIsTheVoice(_SeatCase):
    """The whole reason this matters: the seat is what reaches the air."""

    def test_seated_at_the_console_she_can_transmit(self):
        from world.radio import active_transmit_radio

        console = self.obj2
        console.location = self.post
        console.db.is_radio = True
        console.db.is_base_station = True
        console.db.radio_on = True
        console.db.frequency = "911MHz"

        self.assertIsNone(active_transmit_radio(self.soul))  # standing: mute
        _run_sit(self.soul, self.chair)
        self.assertIs(active_transmit_radio(self.soul), console)
