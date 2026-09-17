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


class _RoomDB(SimpleNamespace):
    """A room's `db` handler, which answers None for anything unset.

    A bare `SimpleNamespace` raises AttributeError instead, so it is a
    STRICTER object than the thing it stands in for -- and `fill_air_cell`
    reads `neighbour.db.outside`, a flag these fixtures never set. On a
    real room that read is None and the branch is simply not taken; on
    the double it exploded, and the test had been red on clean master
    since #1487 was filed.

    Production is fine here: `db.outside` is None on a room that never
    set it. The double was the only thing that could not answer.
    """

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            # Dunders must still raise. A stub that answers None to
            # `__deepcopy__`/`__iter__`/`__len__` breaks copy, pickle and
            # truthiness in ways that look nothing like their cause.
            raise AttributeError(name)
        return None


class TestAirFill(TestCase):
    """@airfill stamps the hand-proven parkour atom: SkyRoom + one-way
    fall edge + plain exits to roofs + edge/gap exits from roofs in."""

    def _index(self, cells):
        index = {}
        for cell, sky in cells.items():
            room = MagicMock()
            room.db = _RoomDB(is_sky_room=sky)
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
        # ...and SAY it is a roof. `fill_air_cell` links air to a
        # neighbour only when that neighbour declares itself walkable
        # outdoor surface -- `db.type == "rooftop"` or `db.outside is
        # True` -- and the fixture only ever set `is_sky_room=False`.
        # The cell was a rooftop in the comment and an anonymous room to
        # the code.
        #
        # This was invisible while the double raised AttributeError on
        # `outside` (#1487): the test died before reaching the branch,
        # so "no west exit" never got a chance to be noticed. Fixing the
        # double turned an ERROR into a FAILURE, which is how the real
        # gap surfaced.
        roof.db.type = "rooftop"
        made_exits = []

        def fake_create(tclass, key=None, aliases=None, location=None,
                        destination=None):
            obj = MagicMock()
            obj.key = key
            obj.db = _RoomDB(is_sky_room="rooms" in tclass)
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
        # No walkable surface stands across the cell, so this is a DROP,
        # not a crossing: no gap, no perch (#3415). A gap stamped here
        # would be refused on the roof (#3579) -- a crossing nobody can
        # make.
        self.assertIsNone(roof_exit.db.is_gap)
        self.assertIsNone(roof_exit.db.gap_destination)
        # down is one-way: no exit hung on the street below
        street = index[(1, 0, 0)]
        self.assertEqual(street.exits, [])

    def _fill(self, index, cell):
        from commands import CmdBuildTools as bt
        made_exits = []

        def fake_create(tclass, key=None, aliases=None, location=None,
                        destination=None):
            obj = MagicMock()
            obj.key = key
            obj.db = _RoomDB(is_sky_room="rooms" in tclass)
            obj.exits = []
            if "exits" in tclass:
                made_exits.append((location, key, destination, obj))
                if hasattr(location, "exits"):
                    location.exits.append(obj)
            return obj

        with patch("evennia.create_object", side_effect=fake_create), \
             patch("world.spatial.set_xyz"):
            room, count = bt.fill_air_cell(cell, index)
        return room, made_exits

    def test_a_gap_is_stamped_only_with_a_perch_one_cell_across(self):
        """Two roofs one air cell apart: each roof's edge into the cell is
        a GAP whose gap_destination is the OTHER roof (#3415)."""
        index = self._index({
            (0, 0, 1): False,      # west roof
            (2, 0, 1): False,      # east roof, one cell across
            (1, 0, 0): False,      # street under the air
        })
        west, east = index[(0, 0, 1)], index[(2, 0, 1)]
        west.db.type = "rooftop"; west.id = 100
        east.db.type = "rooftop"; east.id = 200
        room, made = self._fill(index, (1, 0, 1))
        west_exit = next(e for src, key, dest, e in made if src is west)
        east_exit = next(e for src, key, dest, e in made if src is east)
        self.assertIs(west_exit.db.is_edge, True)
        self.assertIs(west_exit.db.is_gap, True)
        self.assertEqual(west_exit.db.gap_destination, 200)
        self.assertIs(east_exit.db.is_gap, True)
        self.assertEqual(east_exit.db.gap_destination, 100)

    def test_an_interior_across_the_air_is_not_a_perch(self):
        """The far cell exists but is not a walkable surface: edge only."""
        index = self._index({
            (0, 0, 1): False, (2, 0, 1): False, (1, 0, 0): False,
        })
        index[(0, 0, 1)].db.type = "rooftop"
        index[(2, 0, 1)].db.type = "apartment"      # a wall, not a perch
        room, made = self._fill(index, (1, 0, 1))
        west_exit = next(e for src, key, dest, e in made
                         if src is index[(0, 0, 1)])
        self.assertIs(west_exit.db.is_edge, True)
        self.assertIsNone(west_exit.db.is_gap)
        # and the interior got NO links at all (the B-line incident)
        self.assertEqual(index[(2, 0, 1)].exits, [])


class TestTheEdgeAudit(TestCase):
    """@airfill/audit (#3582): the closing question of every air build,
    answered by a read-only report instead of a sentence in the playbook."""

    def _room(self, sky=False, type_=None, outside=None, rid=1, exits=None):
        room = MagicMock()
        room.db = _RoomDB(is_sky_room=sky, type=type_, outside=outside)
        room.exits = exits or []
        room.id = rid
        room.key = "In the Air" if sky else f"Roof {rid}"
        return room

    def _exit(self, src, dest, key, **flags):
        ex = MagicMock()
        ex.key = key
        ex.destination = dest
        ex.location = src
        ex.db = _RoomDB(**flags)
        ex.id = 900 + len(src.exits)
        src.exits.append(ex)
        return ex

    def test_a_roof_beside_air_with_no_edge_is_reported(self):
        from commands.CmdBuildTools import audit_air
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        street = self._room(outside=True, rid=3)
        self._exit(air, street, "down")
        index = {(0, 0, 1): roof, (1, 0, 1): air, (1, 0, 0): street}
        f = audit_air(1, index)
        self.assertEqual([(r.id, c.id, d) for r, c, d in f["missing_edges"]],
                         [(1, 2, "east")])
        self.assertEqual(f["bare_cells"], [])
        self.assertEqual(f["bad_gaps"], [])

    def test_a_wired_edge_is_not_reported(self):
        from commands.CmdBuildTools import audit_air
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        street = self._room(outside=True, rid=3)
        self._exit(air, street, "down")
        self._exit(roof, air, "east", is_edge=True)
        f = audit_air(1, {(0, 0, 1): roof, (1, 0, 1): air, (1, 0, 0): street})
        self.assertEqual(f["missing_edges"], [])

    def test_a_deliberate_omission_is_skipped(self):
        from commands.CmdBuildTools import audit_air
        roof = self._room(type_="rooftop", rid=1)
        roof.db.no_edge = "the parapet is a metre of blast glass"
        air = self._room(sky=True, rid=2)
        self._exit(air, self._room(outside=True, rid=3), "down")
        f = audit_air(1, {(0, 0, 1): roof, (1, 0, 1): air})
        self.assertEqual(f["missing_edges"], [])

    def test_a_bare_cell_is_reported_not_repaired(self):
        from commands.CmdBuildTools import audit_air
        air = self._room(sky=True, rid=2)          # no down
        f = audit_air(1, {(1, 0, 1): air})
        self.assertEqual([c.id for c in f["bare_cells"]], [2])
        self.assertEqual(air.exits, [])            # nothing was hung

    def test_a_gap_without_a_perch_is_a_bad_gap(self):
        from commands.CmdBuildTools import audit_air
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        self._exit(air, self._room(outside=True, rid=3), "down")
        self._exit(roof, air, "east", is_edge=True, is_gap=True)   # @airfill's old stamp
        f = audit_air(1, {(0, 0, 1): roof, (1, 0, 1): air})
        self.assertEqual([reason for _e, reason in f["bad_gaps"]],
                         ["no gap_destination"])

    def test_a_gap_whose_perch_is_not_one_cell_across_is_a_bad_gap(self):
        from commands.CmdBuildTools import audit_air
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        far = self._room(type_="rooftop", rid=4)
        self._exit(air, self._room(outside=True, rid=3), "down")
        self._exit(roof, air, "east", is_edge=True, is_gap=True, gap_destination=4)
        # the perch sits two cells across, not one
        index = {(0, 0, 1): roof, (1, 0, 1): air, (3, 0, 1): far}
        f = audit_air(1, index)
        self.assertEqual(len(f["bad_gaps"]), 1)
        self.assertIn("not one cell across", f["bad_gaps"][0][1])

    def test_a_correct_gap_is_clean(self):
        from commands.CmdBuildTools import audit_air, format_air_audit
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        far = self._room(type_="rooftop", rid=4)
        self._exit(air, self._room(outside=True, rid=3), "down")
        self._exit(roof, air, "east", is_edge=True, is_gap=True, gap_destination=4)
        self._exit(far, air, "west", is_edge=True, is_gap=True, gap_destination=1)
        index = {(0, 0, 1): roof, (1, 0, 1): air, (2, 0, 1): far}
        f = audit_air(1, index)
        self.assertEqual(f["bad_gaps"], [])
        self.assertEqual(f["missing_edges"], [])
        self.assertIn("Clean.", format_air_audit(1, f, index))

    def test_the_report_names_dbrefs_and_coordinates(self):
        from commands.CmdBuildTools import audit_air, format_air_audit
        roof = self._room(type_="rooftop", rid=1)
        air = self._room(sky=True, rid=2)
        index = {(5, -3, 1): roof, (6, -3, 1): air}
        text = format_air_audit(1, audit_air(1, index), index)
        self.assertIn("#1 at (5,-3)", text)
        self.assertIn("air to the east (#2)", text)
        self.assertIn("bare cell", text)
        self.assertIn("nothing written", text)
        self.assertNotIn("Clean.", text)

    def test_the_command_audit_switch_writes_nothing(self):
        """`@airfill/audit 1` reports and returns before any fill."""
        from commands import CmdBuildTools as bt
        cmd = bt.CmdAirFill()
        cmd.caller = MagicMock()
        cmd.args = "1"; cmd.lhs = "1"; cmd.rhs = None; cmd.switches = ["audit"]
        with patch.object(bt, "_room_cell_index", return_value={}), \
             patch.object(bt, "fill_air_cell") as fill, \
             patch.object(bt, "air_candidates") as cands:
            cmd.func()
        fill.assert_not_called()
        cands.assert_not_called()
        cmd.caller.msg.assert_called_once()
        self.assertIn("Edge audit", cmd.caller.msg.call_args.args[0])
