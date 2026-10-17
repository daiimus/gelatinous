"""#3753 -- the neighbour glance ("You see a lone figure to the north.")
is a sightline: it renders when the looker is alone, it looks only into
open ground, and a heavy crowd over there is all it reports.

Two faults, one renderer, two rulings. `Room.get_display_characters`
returned early for an empty room before it reached the glance, so the one
case the glance was written for -- you alone, someone beyond the open
doorway -- never showed it. And the glance had no notion of what kind of
room it looked into, so a rented unit with its door standing open was
reported from the landing. Owner, 2026-10-15: "Streets, sure. Cubes? Not
so much." Owner, 2026-10-17: "I think open air should be a combination of
room types and crowd size." and, offered a gate (room type says the far
room is open air, its crowd size says what you can make out), a report, or
a definition: "1."

Everything here goes through `return_appearance` (what `look` prints)
unless the test is about a helper itself. Fixture: a third room beyond an
exit of our own, typed `street`, because the harness already links room1
-> room2 by "out"; that exit is view-locked so it stays out of the prose,
and char2 is parked in room2 so the looker is alone. The crowd level reads
the colony clock and the weather, so the crowd tests pin both.

Rendering alone widened two places the glance already reached (round-3
review): every air cell of a fall, where only a drag-fall pair had company
to trigger it, and the aim view, whose far room has an exit back to the
shooter's own company and reported it whenever the far room was occupied.
A sky cell is now never glanced from, and the looker's own room is never
glanced into.
"""
import inspect
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from world.crowd import crowd_system
from world.crowd.crowd_messages import (
    CROWD_INTENSITY, FIGURES_LOST_IN_CROWD, OPEN_AIR_ROOM_TYPES,
    room_type_is_open_air,
)
from world.weather import weather_system

LONE = "You see a lone figure to the north."
GROUP = "You see a group of people standing to the north."
CROWD = "You see a crowd to the north."


@contextmanager
def pinned_clock(hour=12, weather="overcast"):
    """Noon under an overcast sky: +0.3 for the hour, nothing for the
    weather, so a base level means the same thing at 02:00 in a blizzard.
    The weather is patched on the instance: `world.weather` holds both a
    submodule and an instance called `weather_system`, and a dotted
    `patch` target resolves to the submodule."""
    with patch("world.gametime.colony_hour", return_value=hour), \
         patch.object(weather_system, "get_current_weather",
                      return_value=weather):
        yield


class _Alone(EvenniaTest):
    """char1 alone in room1; a neighbour stands in `beyond`, a street to
    the north."""

    far_type = "street"

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room2
        self.exit.locks.add("view:false()")
        self.beyond = create.create_object("typeclasses.rooms.Room", key="beyond")
        self.beyond.db.type = self.far_type
        self.north = self.make_exit()
        self.neighbour = create.create_object(
            "typeclasses.characters.Character", key="a neighbour",
            location=self.beyond)
        self.neighbour.msg = lambda text=None, **kw: None

    def make_exit(self):
        return create.create_object("typeclasses.exits.Exit", key="north",
                                    location=self.room1, destination=self.beyond)

    def look(self):
        return self.room1.return_appearance(self.char1) or ""

    def others_here(self):
        return [o for o in self.room1.contents
                if o.is_typeclass("typeclasses.characters.Character", exact=False)
                and o != self.char1]


class TestTheGlanceRendersWhenAlone(_Alone):

    def test_the_premise_the_looker_is_alone(self):
        self.assertEqual(self.others_here(), [])

    def test_the_room_look_names_the_direction(self):
        self.assertIn(LONE, self.look())

    def test_two_neighbours_read_as_a_group(self):
        self.char2.location = self.beyond
        self.assertIn(GROUP, self.look())

    def test_the_control_with_company_still_renders_it(self):
        self.char2.location = self.room1
        self.assertIn(LONE, self.look())

    def test_an_empty_street_beyond_says_nothing(self):
        self.neighbour.location = self.room2
        look = self.look()
        self.assertNotIn("lone figure", look)
        self.assertNotIn("group of people", look)
        self.assertNotIn("crowd to the", look)

    def test_alone_the_glance_lays_out_as_it_does_with_company(self):
        """The formatter padded any line starting "You see" as a things
        line, so alone the glance became its own paragraph (review of
        #3753). Now it sits directly above the exits either way."""
        alone = self.look()
        self.assertNotIn("\n\n", alone[alone.index(LONE):])
        self.char2.location = self.room1
        together = self.look()
        self.assertNotIn("\n\n", together[together.index(LONE):])

    def test_the_things_line_keeps_its_blank_line(self):
        things = self.room1.get_display_things(self.char1)
        self.assertTrue(things.startswith("You see"), things)
        out = self.look()
        self.assertIn(things + "\n\n", out)
        self.assertIn(LONE, out)

    def test_alone_with_a_crowd_here_the_glance_follows_the_crowd_line(self):
        self.room1.crowd_base_level = 2
        with pinned_clock():
            people = self.room1.get_display_characters(self.char1) or ""
            out = self.look()
        self.assertIn(LONE, people)
        self.assertGreater(people.index(LONE), 0, people)
        self.assertNotIn("\n", people)
        self.assertNotIn("\n\n", out[out.index(LONE):])

    def test_the_glance_sits_before_the_empty_room_return(self):
        """The fault was placement; pin the order so it cannot drift back."""
        from typeclasses.rooms import Room
        body = inspect.getsource(Room.get_display_characters)
        call = "self.get_adjacent_character_sightings(looker)"
        self.assertEqual(body.count(call), 1)
        self.assertLess(body.index(call), body.index("if not characters:"))


class TestAloneTheDoorStillDecides(_Alone):
    """#3750's gate holds for a looker alone: the owner's first condition,
    "make sure this doesn't work between closed doors". A courtyard behind
    a gate, so the door is the only variable."""

    far_type = "courtyard"

    def make_exit(self):
        return create.create_object("typeclasses.doors.DoorExit", key="north",
                                    location=self.room1, destination=self.beyond)

    def test_a_freshly_hung_door_is_shut(self):
        self.assertFalse(self.north.is_open())
        self.assertTrue(self.north.blocks_sight())

    def test_shut_the_room_says_nothing(self):
        self.assertNotIn("lone figure", self.look())

    def test_open_the_room_names_the_direction(self):
        self.north.db.door_closed = False
        self.assertIn(LONE, self.look())

    def test_shut_again_it_goes_quiet(self):
        self.north.db.door_closed = False
        self.assertIn(LONE, self.look())
        self.north.db.door_closed = True
        self.assertNotIn("lone figure", self.look())


class TestOnlyOpenGroundIsGlancedInto(_Alone):
    """Owner: "Streets, sure. Cubes? Not so much." Through an OPEN door
    throughout, so the door is never the reason."""

    def make_exit(self):
        door = create.create_object("typeclasses.doors.DoorExit", key="north",
                                    location=self.room1, destination=self.beyond)
        door.db.door_closed = False
        return door

    def test_the_control_a_street_is_glanced_into(self):
        self.assertEqual(self.beyond.db.type, "street")
        self.assertIn(LONE, self.look())

    def test_every_open_air_type_is_glanced_into(self):
        for word in sorted(OPEN_AIR_ROOM_TYPES):
            self.beyond.db.type = word
            self.assertIn(LONE, self.look(), word)

    def test_an_untyped_room_is_an_interior(self):
        self.beyond.db.type = None
        self.assertNotIn("lone figure", self.look())

    def test_a_cube_hotel_unit_is_not_glanced_into(self):
        self.beyond.db.type = "cube hotel"
        look = self.look()
        self.assertNotIn("lone figure", look)
        self.assertNotIn("group of people", look)

    def test_a_tenement_flat_is_not(self):
        self.beyond.db.type = "tenement"
        self.assertNotIn("lone figure", self.look())

    def test_the_constabulary_is_not(self):
        """Named for the owner: the Secure Corridor and Dispatch, both
        typed constabulary, stop seeing each other through the open door."""
        self.room1.db.type = "constabulary"
        self.beyond.db.type = "constabulary"
        self.assertNotIn("lone figure", self.look())

    def test_the_unruled_words_are_interiors_for_now(self):
        for word in ("sky", "farm", "hull", "garden", "agridome"):
            self.beyond.db.type = word
            self.assertNotIn("lone figure", self.look(), word)

    def test_nor_with_company_in_the_corridor(self):
        self.char2.location = self.room1
        self.beyond.db.type = "tenement"
        self.assertNotIn("lone figure", self.look())

    def test_the_open_door_itself_still_shows_who_is_inside(self):
        """Only the automatic sentence goes; `look north` through an open
        door is a look through an open door."""
        self.beyond.db.type = "tenement"
        shown = self.north.return_appearance(self.char1) or ""
        self.assertIn(self.neighbour.get_display_name(self.char1), shown)

    def test_the_rule_reads_the_room_glanced_into(self):
        """From a tenement hall into a street the glance speaks; from the
        street back into the hall it does not."""
        create.create_object("typeclasses.exits.Exit", key="south",
                             location=self.beyond, destination=self.room1)
        self.room1.db.type = "tenement"
        self.assertIn(LONE, self.look())
        seen = self.beyond.return_appearance(self.neighbour) or ""
        self.assertNotIn("lone figure to the south", seen)
        self.room1.db.type = "street"
        self.assertIn("You see a lone figure to the south.",
                      self.beyond.return_appearance(self.neighbour) or "")


class TestAHeavyCrowdHidesTheFigures(_Alone):
    """Owner's gate, 2026-10-17: the far room's crowd size says what you
    can make out. Noon, overcast, one neighbour over there: base 1 reads
    moderate (1 + 0.5 + 0.3 -> 2), base 2 reads heavy (2.8 -> 3)."""

    def test_thin_the_figure_shows(self):
        self.beyond.crowd_base_level = 1
        with pinned_clock():
            self.assertEqual(crowd_system.calculate_crowd_level(self.beyond), 2)
            look = self.look()
        self.assertIn(LONE, look)
        self.assertNotIn("crowd to the", look)

    def test_heavy_only_the_crowd_shows(self):
        self.beyond.crowd_base_level = 2
        with pinned_clock():
            self.assertEqual(crowd_system.calculate_crowd_level(self.beyond), 3)
            look = self.look()
        self.assertIn(CROWD, look)
        self.assertNotIn("lone figure", look)

    def test_packed_the_same(self):
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            self.assertEqual(crowd_system.get_crowd_level_description(
                crowd_system.calculate_crowd_level(self.beyond)), "packed")
            look = self.look()
        self.assertIn(CROWD, look)
        self.assertNotIn("lone figure", look)

    def test_a_group_is_lost_in_it_too(self):
        self.char2.location = self.beyond
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            look = self.look()
        self.assertIn(CROWD, look)
        self.assertNotIn("group of people", look)

    def test_the_crowd_shows_with_nobody_over_there(self):
        self.neighbour.location = self.room2
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            self.assertIn(CROWD, self.look())

    def test_base_zero_means_no_crowd_whatever_the_bodies(self):
        """Base 0 is the default and the builder's off switch. The room's
        own crowd line is silent at 0 however many stand there; so is the
        glance's crowd, which then counts them."""
        self.assertEqual(self.beyond.crowd_base_level, 0)
        for n in range(5):
            extra = create.create_object("typeclasses.characters.Character",
                                         key=f"a bystander {n}",
                                         location=self.beyond)
            extra.msg = lambda text=None, **kw: None
        with pinned_clock():
            self.assertGreaterEqual(
                crowd_system.calculate_crowd_level(self.beyond), 3)
            self.assertFalse(crowd_system.crowd_hides_figures(self.beyond))
            look = self.look()
        self.assertIn(GROUP, look)
        self.assertNotIn("crowd to the", look)

    def test_an_interior_crowd_is_not_seen_at_all(self):
        self.beyond.db.type = "tenement"
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            look = self.look()
        self.assertNotIn("crowd to the", look)
        self.assertNotIn("lone figure", look)

    def test_two_crowded_streets_share_one_sentence(self):
        east = create.create_object("typeclasses.rooms.Room", key="east street")
        east.db.type = "street"
        east.crowd_base_level = 9
        create.create_object("typeclasses.exits.Exit", key="east",
                             location=self.room1, destination=east)
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            look = self.look()
        self.assertIn("You see crowds to the north and east.", look)
        self.assertNotIn(CROWD, look)

    def test_a_crowded_street_beside_a_quiet_one(self):
        east = create.create_object("typeclasses.rooms.Room", key="east street")
        east.db.type = "street"
        create.create_object("typeclasses.exits.Exit", key="east",
                             location=self.room1, destination=east)
        self.char2.location = east
        self.beyond.crowd_base_level = 9
        with pinned_clock():
            look = self.look()
        self.assertIn("You see a lone figure to the east.", look)
        self.assertIn(CROWD, look)

    def test_the_threshold_is_the_crowd_lines_own_words(self):
        self.assertEqual(FIGURES_LOST_IN_CROWD, {"heavy", "packed"})
        hidden = {level for level, word in CROWD_INTENSITY.items()
                  if word in FIGURES_LOST_IN_CROWD}
        self.assertEqual(hidden, {3, 4})


class TestTwoRoomsAreNeverGlancedFromOrInto(_Alone):
    """Round-3 review of #3753: rendering alone widened two places the
    glance already reached. A faller passes populated roofs, and a sky
    cell shows no exits, so it should name no directions either (before,
    only a drag-fall pair had the company to trigger it there). And the
    aim view renders the far room from over there, whose exit back counted
    the shooter's own company whenever the far room was occupied, and
    would have for an empty one too."""

    def test_a_sky_cell_is_not_glanced_from(self):
        self.assertIn(LONE, self.look())                       # control
        self.room1.is_sky_room = True
        self.assertNotIn("lone figure", self.look())
        self.assertEqual(
            self.room1.get_adjacent_character_sightings(self.char1), "")

    def test_the_room_you_stand_in_is_never_glanced_into(self):
        create.create_object("typeclasses.exits.Exit", key="south",
                             location=self.beyond, destination=self.room1)
        self.room1.db.type = "street"        # open air, so only the rule stops it
        self.char2.location = self.room1              # the looker's company
        # control: from over there, someone in the street sees them both
        self.assertEqual(
            self.beyond.get_adjacent_character_sightings(self.neighbour),
            "You see a group of people standing to the south.")
        # the looker who stands here is not shown their own room
        self.assertEqual(
            self.beyond.get_adjacent_character_sightings(self.char1), "")

    def test_the_aim_view_does_not_report_your_own_company(self):
        """`look` while aiming renders the aimed room; aiming north into an
        empty street read "You see a lone figure to the south." -- the
        friend standing beside the shooter."""
        create.create_object("typeclasses.exits.Exit", key="south",
                             location=self.beyond, destination=self.room1)
        self.room1.db.type = "street"        # open air, so only the rule stops it
        self.char2.location = self.room1
        # control: from the street, someone standing there sees them both
        self.assertEqual(
            self.beyond.get_adjacent_character_sightings(self.neighbour),
            "You see a group of people standing to the south.")

        def aimed_look():
            self.char1.ndb.aiming_direction = "north"
            try:
                return self.room1.return_appearance(self.char1) or ""
            finally:
                self.char1.ndb.aiming_direction = None

        # the occupied street: master already reported the company here
        aimed = aimed_look()
        self.assertIn(self.beyond.key, aimed)          # it is the far room
        # the roster capitalises the sentence: "A neighbour is standing here."
        self.assertIn(self.neighbour.get_display_name(self.char1).lower(),
                      aimed.lower())
        self.assertNotIn("lone figure", aimed)
        self.assertNotIn("group of people", aimed)
        # the empty street: the case rendering alone added
        self.neighbour.location = self.room2
        aimed = aimed_look()
        self.assertIn(self.beyond.key, aimed)
        self.assertNotIn("lone figure", aimed)
        self.assertNotIn("group of people", aimed)


class TestThePredicate(TestCase):

    def test_the_open_air_words(self):
        for word in sorted(OPEN_AIR_ROOM_TYPES) + ["Street", "FIRE ESCAPE"]:
            self.assertTrue(room_type_is_open_air(word), word)

    def test_everything_else_is_an_interior(self):
        for word in ("cube hotel", "tenement", "constabulary", "stairwell",
                     "shaft", "interior", "bar", "shop", "hospital",
                     "sky", "farm", "hull", "garden", "agridome", "", None):
            self.assertFalse(room_type_is_open_air(word), repr(word))

    def test_the_set_is_the_eight_words_proposed(self):
        """A change here is a visible decision about what players see;
        the owner has not ruled on sky, farm, hull, garden or agridome."""
        self.assertEqual(OPEN_AIR_ROOM_TYPES, {
            "street", "alley", "market", "bridge", "rooftop", "courtyard",
            "balcony", "fire escape"})


class TestTheFormatterPlacesBlankLinesByPosition(_Alone):
    """Review of #3753, round 2: the formatter re-renders the things line
    to find it, and for more than fifty of a kind the wording is drawn at
    random, so an identity match could miss. It now counts from the end."""

    def test_a_things_line_that_renders_differently_twice_is_still_found(self):
        from typeclasses.rooms import Room
        first = "You see a shitload of |wcrates|n."
        second = "You see more |wcrates|n than you know what to do with."
        with patch.object(Room, "get_display_things",
                          side_effect=[first, second]) as things:
            out = self.look()
        self.assertEqual(things.call_count, 2)
        self.assertIn(first + "\n\n", out)
        self.assertNotIn(second, out)
        self.assertNotIn("\n\n", out[out.index(LONE):])

    def test_no_things_line_means_one_blank_line_after_the_description(self):
        from typeclasses.rooms import Room
        with patch.object(Room, "get_display_things", return_value=""):
            out = self.look()
        self.assertEqual(out[:out.index(LONE)].count("\n\n"), 1)

    def test_the_old_text_matches_are_gone(self):
        """A revert guard for the three spellings master and round 2 used;
        the property itself, blank lines by position, is what the two
        tests above check."""
        from typeclasses.rooms import Room
        src = inspect.getsource(Room.format_appearance)
        self.assertNotIn('startswith("You see")', src)
        self.assertNotIn("== things.strip()", src)
        self.assertNotIn("== desc.strip()", src)
