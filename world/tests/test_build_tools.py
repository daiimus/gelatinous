"""@room / @building — the builder QoL pair."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _room_cmd(switches=(), args=""):
    from commands.CmdBuildTools import CmdRoomProfile
    cmd = CmdRoomProfile()
    cmd.switches = list(switches)
    cmd.args = args
    cmd.caller = MagicMock()
    return cmd


class TestRoomProfile(TestCase):
    def test_set_type_reports_crowd_pool(self):
        cmd = _room_cmd(switches=("type",), args="cube hotel")
        cmd.func()
        self.assertEqual(cmd.caller.location.db.type, "cube hotel")
        self.assertIn("residential", cmd.caller.msg.call_args.args[0])

    def test_set_crowd_zero_notes_disabled(self):
        cmd = _room_cmd(switches=("crowd",), args="0")
        cmd.func()
        self.assertEqual(cmd.caller.location.db.crowd_base_level, 0)
        self.assertIn("disabled", cmd.caller.msg.call_args.args[0])

    def test_outside_flag(self):
        cmd = _room_cmd(switches=("outside",), args="on")
        cmd.func()
        self.assertIs(cmd.caller.location.db.outside, True)

    def test_profile_renders(self):
        from commands.CmdBuildTools import _room_profile_lines
        room = MagicMock()
        room.get_display_name.return_value = "Queen of Cups - Lobby (#1917)"
        room.typeclass_path = "typeclasses.rooms.IndoorRoom"
        room.db.type = "cube hotel"
        room.db.crowd_base_level = 1
        room.db.outside = False
        room.db.sense_descs = {"auditory": "hum", "olfactory": "noodles"}
        room.db.desc = "x" * 120
        room.exits = []
        from world.crowd import crowd_system
        with patch.object(crowd_system, "calculate_crowd_level",
                          return_value=1), \
             patch("world.spatial.get_xyz", return_value=(-2, -15, 0)):
            text = "\n".join(_room_profile_lines(room, MagicMock()))
        self.assertIn("residential", text)
        self.assertIn("auditory, olfactory", text)
        self.assertIn("missing: tactile, atmospheric", text)


class TestDoorStates(TestCase):
    def test_states_summarised(self):
        from commands.CmdBuildTools import _door_states
        def ex(key, closed, locked):
            e = MagicMock()
            e.key = key
            e.db = SimpleNamespace(door_closed=closed, door_locked=locked)
            return e
        plain = MagicMock()
        plain.db = SimpleNamespace(door_closed=None, door_locked=None)
        plain.key = "north"
        room = SimpleNamespace(exits=[ex("west", True, True),
                                      ex("south", True, False),
                                      ex("east", False, False), plain])
        self.assertEqual(_door_states(room),
                         "west locked, south closed, east open")
