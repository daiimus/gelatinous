"""A blind looker is not told what lies in the room or beyond the door
(#3479, #3382).

`Room.get_display_desc` already gives a sightless looker the void line and
withholds visual integrate prose (#3373); the doorway glance withholds who
stands beyond (#2793). But the room still listed its objects ("You see a
crate.") and who was standing here, and `look <direction>` still described
streetlight, shadow and the precarious edge. Both are visual reads and now
honour the same predicate. The exits line stays: a blind character can be
told an exit exists, as the #2793 test already records, and `look <dir>`
tells them the same KIND the footer does (an edge, a gap, open air, the
street's shape) so the two never disagree. The passive stealth roll is a
Resonance sense, not a glance, and still runs for blind eyes; all it can
give them is the prickling-sense cue.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.perception import can_perceive_sense
from world.stealth import ALERT, SUSPICIOUS, set_awareness


class _Scene(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.beyond = create_object("typeclasses.rooms.Room", key="beyond")
        self.door = create_object("typeclasses.exits.Exit", key="north",
                                  location=self.room1, destination=self.beyond)
        self.crate = create_object("typeclasses.items.Item", key="crate", location=self.room1)
        self.looker = create_object("typeclasses.characters.Character", key="a looker", location=self.room1)
        self.looker.msg = lambda text=None, **kw: None
        self.bystander = create_object("typeclasses.characters.Character", key="Orrin", location=self.room1)
        self.bystander.msg = lambda text=None, **kw: None

    def blind(self, who):
        state = who.medical_state
        for organ in state.organs.values():
            if (organ.data or {}).get("capacity") == "sight":
                organ.current_hp = 0
        who.medical_state = state
        who.save_medical_state()
        who._medical_state = None

    def room(self):
        return (self.room1.return_appearance(self.looker) or "")

    def door_desc(self):
        return self.door.get_display_desc(self.looker) or ""


class TheSightedControl(_Scene):

    def test_the_sighted_looker_is_told_everything(self):
        self.assertTrue(can_perceive_sense(self.looker, "visual"))
        out = self.room()
        self.assertIn("You see", out)                  # the object list, colour-coded names
        self.assertIn("crate", out)
        self.assertIn("Orrin", out)
        self.assertIn("standing here", out)
        self.assertIn("north", out.lower())
        self.assertIn("Northward lies deeper shadow", self.door_desc())

    def test_zeroing_the_eyes_really_blinds(self):
        self.blind(self.looker)
        self.assertFalse(can_perceive_sense(self.looker, "visual"))


class TheBlindLookerInTheRoom(_Scene):

    def test_no_object_list_and_nobody_named(self):
        self.blind(self.looker)
        out = self.room()
        self.assertNotIn("You see", out)
        self.assertNotIn("crate", out.lower())
        self.assertNotIn("orrin", out.lower())
        self.assertNotIn("standing here", out.lower())

    def test_the_exits_line_still_speaks(self):
        self.blind(self.looker)
        self.assertIn("north", self.room().lower())

    def test_the_things_and_characters_renderers_are_empty(self):
        self.blind(self.looker)
        self.assertEqual(self.room1.get_display_things(self.looker), "")
        self.assertEqual(self.room1.get_display_characters(self.looker), "")

    def test_the_passive_roll_still_runs_for_blind_eyes(self):
        # Resonance is "the sense that someone's there" (stealth spec §3.1);
        # the arrival glance rolls it for blind eyes, and so does the look
        self.blind(self.looker)
        self.bystander.db.hidden = True
        with mock.patch("world.stealth.passive_check", return_value=0) as roll:
            self.room1.get_display_characters(self.looker)
        roll.assert_called_once_with(self.looker, self.bystander)

    def test_a_suspicious_blind_looker_gets_the_cue_and_no_name(self):
        self.blind(self.looker)
        self.bystander.db.hidden = True
        set_awareness(self.looker, self.bystander, SUSPICIOUS)
        with mock.patch("world.stealth.passive_check", return_value=SUSPICIOUS):
            out = self.room1.get_display_characters(self.looker)
        self.assertIn("not alone", out.lower())
        self.assertNotIn("orrin", out.lower())

    def test_even_an_alert_blind_looker_names_nobody(self):
        # fully made, and still unseen: the cue is the ceiling without eyes
        self.blind(self.looker)
        self.bystander.db.hidden = True
        set_awareness(self.looker, self.bystander, ALERT)
        with mock.patch("world.stealth.passive_check", return_value=ALERT):
            out = self.room1.get_display_characters(self.looker)
        self.assertIn("not alone", out.lower())
        self.assertNotIn("orrin", out.lower())

    def test_a_flying_object_is_not_announced_to_the_blind(self):
        from world.combat.constants import NDB_FLYING_OBJECTS
        setattr(self.room1.ndb, NDB_FLYING_OBJECTS, [self.crate])
        self.assertIn("flying through the air", self.room())
        self.blind(self.looker)
        self.assertNotIn("flying", self.room().lower())


class TheBlindLookerAtTheDoor(_Scene):

    def test_the_directional_prose_is_withheld_and_the_fallback_speaks(self):
        self.blind(self.looker)
        self.assertEqual(self.door_desc(), "A passageway leading elsewhere.")

    def test_an_authored_exit_desc_is_withheld_like_the_rooms_own(self):
        # the room withholds its authored desc from a blind looker (#591);
        # an exit's authored desc is the same kind of prose
        self.door.db.desc = "A rusted iron door, red paint flaking."
        self.assertIn("rusted iron door", self.door_desc())
        self.blind(self.looker)
        self.assertEqual(self.door_desc(), "A passageway leading elsewhere.")

    def test_the_edge_is_named_as_an_edge_not_a_passageway(self):
        # the exits footer tells the blind looker "There is an edge to the
        # north." and the walk refuses with "it's an edge!"; the look agrees
        self.door.db.is_edge = True
        self.assertIn("precarious edge", self.door_desc())
        self.blind(self.looker)
        self.assertIn("There is an edge to the north", self.room())
        self.assertEqual(self.door_desc(), "An edge where the floor ends.")

    def test_the_gap_and_the_open_air_are_named_too(self):
        self.blind(self.looker)
        self.door.db.is_gap = True
        self.assertEqual(self.door_desc(), "A gap in the floor.")
        self.door.db.is_gap = False
        self.beyond.is_sky_room = True
        self.assertEqual(self.door_desc(), "An opening into open air.")

    def test_the_street_is_not_described_to_the_blind(self):
        from world.weather import weather_system
        self.beyond.type = "street"
        self.beyond.outside = True
        far = create_object("typeclasses.rooms.Room", key="far")
        far.type = "street"
        create_object("typeclasses.exits.Exit", key="north", location=self.beyond, destination=far)
        create_object("typeclasses.exits.Exit", key="south", location=self.beyond, destination=self.room1)
        weather_system.set_weather("rain")
        self.addCleanup(weather_system.set_weather, "clear")
        sighted = self.door_desc()
        self.assertIn("Through the steady rain", sighted)
        self.assertIn("dead-end", sighted)
        self.blind(self.looker)
        # the footer calls it a dead-end to the blind looker; so does the look
        self.assertIn("There is a dead-end to the north", self.room())
        self.assertEqual(self.door_desc(), "The street northward comes to a dead end.")
        self.assertNotIn("Through the", self.door_desc())


class TheBlindLookerAtAClosedDoor(_Scene):
    """The closed door is the second door onto `look <dir>`: it never
    reaches `Exit.get_display_desc`."""

    def setUp(self):
        super().setUp()
        self.door.delete()
        self.door = create_object("typeclasses.doors.DoorExit", key="north",
                                  location=self.room1, destination=self.beyond)
        self.door.db.desc = "A steel door, its red paint flaking."

    def test_the_sighted_control_sees_paint_and_amber(self):
        self.assertIn("red paint", self.door.return_appearance(self.looker))
        self.door.db.door_locked = True
        self.assertIn("amber", self.door.return_appearance(self.looker))

    def test_the_blind_looker_knows_a_door_and_whether_it_gives(self):
        self.blind(self.looker)
        self.assertEqual(self.door.return_appearance(self.looker), "A door. It is closed.")
        self.door.db.door_locked = True
        self.assertEqual(self.door.return_appearance(self.looker), "A door. It is sealed.")
