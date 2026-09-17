"""The §M1 map export: deterministic, read-only, classified links."""

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.mapping import export_map


class TestExportMap(BaseEvenniaTest):
    def _room(self, key, xyz, **db):
        r = create_object("typeclasses.rooms.Room", key=key, location=None)
        r.db.xyz = xyz
        for k, v in db.items():
            r.attributes.add(k, v)
        return r

    def _exit(self, key, src, dst, **db):
        ex = create_object("typeclasses.exits.Exit", key=key,
                          location=src, destination=dst)
        for k, v in db.items():
            ex.attributes.add(k, v)
        return ex

    def _world(self):
        street = self._room("Test Street", (0, 0, 0), type="street",
                            outside=True, is_ground=True,
                            crowd_base_level=2)
        roof = self._room("Test Roof", (0, 1, 1), type="rooftop",
                          outside=True)
        sky = self._room("In the Air", (1, 0, 1), is_sky_room=True,
                         outside=True)
        offgrid = create_object("typeclasses.rooms.Room",
                                key="Interior", location=None)
        self._exit("north", street, roof)
        self._exit("south", roof, street, is_door=True, door_locked=True)
        # #3579 retired the edge-carried flight plan (sky_room /
        # fall_distance / fall_damage): the exit's destination IS the
        # air cell and the column below it is the fall, re-resolved
        # every tick. What an edge still carries is the landing room
        # (`fall_room`, #3580) and the two difficulties.
        self._exit("east", roof, sky, is_edge=True,
                   fall_room=street.id, edge_difficulty=8)
        self._exit("northeast", roof, sky, is_gap=True,
                   gap_difficulty=12, gap_destination=street.id)
        self._exit("down", sky, street)
        self._exit("in", street, offgrid)      # off-grid end: absent
        return street, roof, sky

    def test_cells_flags_and_offgrid_absence(self):
        self._world()
        data = export_map()
        keys = {c["key"] for c in data["cells"]}
        self.assertIn("Test Street", keys)
        self.assertNotIn("Interior", keys)
        street = next(c for c in data["cells"]
                      if c["key"] == "Test Street")
        self.assertEqual(street["xyz"], [0, 0, 0])
        self.assertEqual(sorted(street["flags"]), ["ground", "outside"])
        self.assertEqual(street["crowd"], 2)
        air = next(c for c in data["cells"] if c["key"] == "In the Air")
        self.assertIn("sky", air["flags"])

    def test_link_classification(self):
        street, roof, sky = self._world()
        kinds = {(l["key"], l["kind"]): l for l in export_map()["links"]
                 if l["from"] in (f"#{street.id}", f"#{roof.id}",
                                  f"#{sky.id}")}
        self.assertIn(("north", "walk"), kinds)
        self.assertIn(("south", "door"), kinds)
        # A door is still TYPED as a door -- the atlas draws ways by
        # kind -- but its live lock state must not leave the game. This
        # used to assert the opposite; `export_map` feeds two
        # unauthenticated public pages, so shipping it meant anyone with
        # the URL could read which homes were locked (#2682).
        self.assertNotIn("door", kinds[("south", "door")])
        self.assertIn(("east", "edge"), kinds)
        edge = kinds[("east", "edge")]["edge"]
        self.assertEqual(edge["fall_room"], street.id)
        self.assertEqual(edge["edge_difficulty"], 8)
        # The retired flight plan must not come back: an exporter that
        # still shipped `sky_room`/`fall_distance`/`fall_damage` would be
        # publishing numbers no longer read by anything (#3579).
        for retired in ("sky_room", "fall_distance", "fall_damage"):
            self.assertNotIn(retired, edge)
        gap = kinds[("northeast", "gap")]["edge"]
        self.assertEqual(gap["gap_difficulty"], 12)
        self.assertEqual(gap["gap_destination"], street.id)
        self.assertIn(("down", "fall"), kinds)   # one-way out of the sky

    def test_deterministic(self):
        self._world()
        self.assertEqual(export_map(), export_map())
