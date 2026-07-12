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


class TestAirFill(TestCase):
    """@airfill stamps the hand-proven parkour atom: SkyRoom + one-way
    fall edge + plain exits to roofs + edge/gap exits from roofs in."""

    def _index(self, cells):
        index = {}
        for cell, sky in cells.items():
            room = MagicMock()
            room.db = SimpleNamespace(is_sky_room=sky)
            room.exits = []
            index[cell] = room
        return index

    def test_candidates_need_roof_beside_and_floor_below(self):
        from commands.CmdBuildTools import air_candidates
        index = self._index({
            (0, 0, 1): False,      # a rooftop at z=1
            (0, 0, 0): False,      # street under the roof
            (1, 0, 0): False,      # street beside it (support for air)
        })
        self.assertEqual(air_candidates(1, index), [(1, 0, 1)])

    def test_no_support_below_no_air(self):
        from commands.CmdBuildTools import air_candidates
        index = self._index({(0, 0, 1): False, (0, 0, 0): False})
        # the cell east of the roof has nothing under it — skip
        self.assertEqual(air_candidates(1, index), [])

    def test_sky_neighbours_never_seed(self):
        # re-runs must not balloon outward ring by ring
        from commands.CmdBuildTools import air_candidates
        index = self._index({
            (0, 0, 1): True,       # existing air
            (0, 0, 0): False, (1, 0, 0): False,
        })
        self.assertEqual(air_candidates(1, index), [])

    def test_box_limits_the_fill(self):
        from commands.CmdBuildTools import air_candidates
        index = self._index({
            (0, 0, 1): False, (0, 0, 0): False,
            (1, 0, 0): False, (-1, 0, 0): False,
        })
        self.assertEqual(air_candidates(1, index, box=(0, 0, 5, 5)),
                         [(1, 0, 1)])

    def test_fill_stamps_the_atom(self):
        from commands import CmdBuildTools as bt
        index = self._index({
            (0, 0, 1): False,      # rooftop west of the new cell
            (1, 0, 0): False,      # street below it
        })
        roof = index[(0, 0, 1)]
        made_exits = []

        def fake_create(tclass, key=None, aliases=None, location=None,
                        destination=None):
            obj = MagicMock()
            obj.key = key
            obj.db = SimpleNamespace(is_sky_room="rooms" in tclass)
            obj.exits = []
            if "exits" in tclass:
                made_exits.append((location, key, destination,
                                   obj))
                if hasattr(location, "exits"):
                    location.exits.append(obj)
            return obj

        with patch("evennia.create_object", side_effect=fake_create), \
             patch("world.spatial.set_xyz"):
            room, count = bt.fill_air_cell((1, 0, 1), index)
        keys = [(src is room and "air" or "roof", key)
                for src, key, dest, _e in made_exits]
        self.assertIn(("air", "down"), keys)     # gravity's edge
        self.assertIn(("air", "west"), keys)     # air -> roof, plain
        self.assertIn(("roof", "east"), keys)    # roof -> air, edge+gap
        roof_exit = next(e for src, key, dest, e in made_exits
                         if key == "east")
        self.assertIs(roof_exit.db.is_edge, True)
        self.assertIs(roof_exit.db.is_gap, True)
        # down is one-way: no exit hung on the street below
        street = index[(1, 0, 0)]
        self.assertEqual(street.exits, [])
