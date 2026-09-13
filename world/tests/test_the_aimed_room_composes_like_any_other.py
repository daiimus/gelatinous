"""The room you aim into renders its @integrate content and weather (#3374).

`Room.return_appearance` has an aiming path that returns the aimed room
through the parent class to avoid recursion -- and thereby skipped
`Room`'s own assembly, the only place @integrate content and weather are
spliced in. The one room a shooter stares into rendered bare.

Both paths now share `_compose_room_layers`, so the far room composes
exactly like a room you stand in.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses import rooms as rooms_mod


class AimedRoomComposesTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.here = self.room1
        self.there = create_object("typeclasses.rooms.Room", key="Far Yard")
        self.there.db.desc = "A cracked concrete yard."
        self.exit = create_object("typeclasses.exits.Exit", key="north", location=self.here, destination=self.there)
        self.char1.location = self.here
        wall = create_object("typeclasses.items.Item", key="far wall", location=self.there)
        wall.db.integrate = True
        wall.db.integration_desc = "PROBE-INTEGRATE blood pools under a shot-out lamp."
        # weather is room-specific; prove the LAYER is called for the aimed room
        self.weather = mock.patch.object(
            rooms_mod.weather_system, "get_weather_contributions",
            side_effect=lambda room, looker: "PROBE-WEATHER rain hammers the yard." if room is self.there else "")
        self.weather.start(); self.addCleanup(self.weather.stop)

    def look_here(self):
        return self.here.return_appearance(self.char1) or ""

    # --- the defect ---------------------------------------------------------

    def test_aimed_room_shows_its_integrate_content(self):
        self.char1.ndb.aiming_direction = "north"
        out = self.look_here()
        self.assertIn("Far Yard", out, "aiming did not render the far room: %r" % out)
        self.assertIn("PROBE-INTEGRATE", out, "aimed room rendered without its @integrate content")

    def test_aimed_room_shows_its_weather(self):
        self.char1.ndb.aiming_direction = "north"
        self.assertIn("PROBE-WEATHER", self.look_here(), "aimed room rendered without weather")

    # --- controls ------------------------------------------------------------

    def test_not_aiming_renders_here_without_the_far_layers(self):
        self.char1.ndb.aiming_direction = None
        out = self.look_here()
        self.assertNotIn("PROBE-INTEGRATE", out); self.assertNotIn("PROBE-WEATHER", out)

    def test_aimed_render_does_not_recurse(self):
        # A far room whose looker is aiming must not re-enter the aiming path.
        self.char1.ndb.aiming_direction = "north"
        orig = rooms_mod.Room.return_appearance
        entries = []
        def spy(room, looker, **kw):
            entries.append(room)
            return orig(room, looker, **kw)
        with mock.patch.object(rooms_mod.Room, "return_appearance", spy):
            self.here.return_appearance(self.char1)
        # Only the room we stand in enters Room.return_appearance; the far
        # room is rendered via the parent class and then composed.
        self.assertEqual(entries, [self.here])
