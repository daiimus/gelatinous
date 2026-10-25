"""#3755 -- up and down are exits, not compass points.

Every exits-footer sentence and all three neighbour-glance sentences put
the exit key after "to the", a shape written for compass words. It read
"The fire escape continues to the up (u) and down (d)." on the Brackett
fire-escape landings and the Halcyon companionways, and, since #3753 let
the glance into the Greenhaus towers, "You see a lone figure to the up."
from a growing platform.

Owner, 2026-10-23: "Up and down are very common exit names - so we should
probably account for them." The others ("to the window", "to the 3B")
"can be put off for now. I don't take issue with them."

The wording the owner approved, by sentence:

    continues        The fire escape continues up (u) and down (d).
    continues, mixed The tenement continues to the southeast (se). It continues up (u) and down (d).
    there is         There is a fire escape above (u).
    there are        There are exits above (u) and below (d).
    glance           You see a lone figure above.
    glance, crowd    You see a crowd below.

A group holding both kinds gets two sentences (owner, 2026-10-23, shown
the 15 Brackett stairwells and 27 Greenhaus stair cores: "That's fine."),
so the "and" never doubles. The exit's KEY decides
(`typeclasses.rooms.VERTICAL_EXITS`). An exit named `hatch` or `drop`
that merely answers to `down` is a named exit and keeps "to the": that
is the part put off.
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import VERTICAL_EXITS


class _Footer(EvenniaTest):
    """char1 alone in room1, which the default fixture leaves untyped;
    `self.exit` (room1 -> room2, key "out") is view-locked so only the
    exits each test hangs are in the footer."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room2
        self.exit.locks.add("view:false()")

    def room(self, room_type=None, key="beyond"):
        room = create.create_object("typeclasses.rooms.Room", key=key)
        if room_type:
            room.db.type = room_type
        return room

    def hang(self, key, destination, alias=None, source=None):
        exit_obj = create.create_object(
            "typeclasses.exits.Exit", key=key, location=source or self.room1,
            destination=destination)
        if alias:
            exit_obj.aliases.add(alias)
        return exit_obj

    def footer(self):
        return self.room1.get_custom_exit_display(self.char1)

    def look(self):
        return self.room1.return_appearance(self.char1) or ""


class TestTheFooterContinues(_Footer):

    def test_a_vertical_pair_continues_up_and_down(self):
        self.room1.db.type = "fire escape"
        self.hang("up", self.room("fire escape", "landing above"), "u")
        self.hang("down", self.room("fire escape", "landing below"), "d")
        self.assertEqual(self.footer(),
                         "The fire escape continues up (u) and down (d).")

    def test_mixed_the_vertical_exits_get_their_own_sentence(self):
        """The Brackett stairwells: one hall and the stair both ways."""
        self.room1.db.type = "tenement"
        self.hang("southeast", self.room("tenement", "hall"), "se")
        self.hang("up", self.room("tenement", "stair above"), "u")
        self.hang("down", self.room("tenement", "stair below"), "d")
        self.assertEqual(
            self.footer(),
            "The tenement continues to the southeast (se). "
            "It continues up (u) and down (d).")

    def test_mixed_the_greenhaus_shape(self):
        """The Greenhaus stair column as built 055 typed it, `farm` like
        the platforms north and south of it (build 170 retyped it
        `stairwell`, #3757; the shape still has to render)."""
        self.room1.db.type = "farm"
        self.hang("north", self.room("farm", "platform north"), "n")
        self.hang("south", self.room("farm", "platform south"), "s")
        self.hang("down", self.room("farm", "core below"), "d")
        self.hang("up", self.room("farm", "core above"), "u")
        self.assertEqual(
            self.footer(),
            "The farm continues to the north (n) and south (s). "
            "It continues down (d) and up (u).")

    def test_mixed_one_of_each_is_still_two_sentences(self):
        self.room1.db.type = "tenement"
        self.hang("west", self.room("tenement", "hall west"), "w")
        self.hang("up", self.room("tenement", "landing above"), "u")
        self.assertEqual(self.footer(),
                         "The tenement continues to the west (w). "
                         "It continues up (u).")

    def test_the_compass_words_come_first_whatever_the_build_order(self):
        self.room1.db.type = "tenement"
        self.hang("up", self.room("tenement", "landing above"), "u")
        self.hang("west", self.room("tenement", "hall west"), "w")
        self.assertEqual(self.footer(),
                         "The tenement continues to the west (w). "
                         "It continues up (u).")

    def test_no_and_is_ever_doubled(self):
        self.room1.db.type = "tenement"
        self.hang("southeast", self.room("tenement", "hall"), "se")
        self.hang("up", self.room("tenement", "stair above"), "u")
        self.hang("down", self.room("tenement", "stair below"), "d")
        self.assertNotIn(", and up", self.footer())
        self.assertNotIn("and up (u) and down", self.footer())

    def test_a_street_continues_up_too(self):
        """The street branch classifies by the far room's street exits;
        a vertical street exit is phrased like any other."""
        self.room1.db.type = "street"
        ramp = self.room("street", "ramp")
        self.hang("down", ramp, "d")
        # two street exits out of the far room make it a "continues"
        self.hang("north", self.room("street", "a"), source=ramp)
        self.hang("south", self.room("street", "b"), source=ramp)
        self.assertEqual(self.footer(), "The street continues down (d).")


class TestTheFooterThereIs(_Footer):

    def test_one_vertical_neighbour_is_above(self):
        self.hang("up", self.room("fire escape", "landing"), "u")
        self.assertEqual(self.footer(), "There is a fire escape above (u).")

    def test_one_vertical_neighbour_is_below(self):
        self.hang("down", self.room("cellar", "cellar"), "d")
        self.assertEqual(self.footer(), "There is a cellar below (d).")

    def test_untyped_neighbours_are_exits_above_and_below(self):
        self.hang("up", self.room(key="attic"), "u")
        self.hang("down", self.room(key="cellar"), "d")
        self.assertEqual(self.footer(), "There are exits above (u) and below (d).")

    def test_a_mixed_there_is_group_splits_and_counts_each_half(self):
        """Singular or plural follows each sentence's own exits."""
        self.hang("north", self.room(key="a yard"), "n")
        self.hang("up", self.room(key="attic"), "u")
        self.hang("down", self.room(key="cellar"), "d")
        self.assertEqual(self.footer(),
                         "There is an exit to the north (n). "
                         "There are exits above (u) and below (d).")

    def test_a_mixed_typed_group_agrees_its_article_each_time(self):
        self.hang("north", self.room("alley", "an alley"), "n")
        self.hang("down", self.room("alley", "a sunken alley"), "d")
        self.assertEqual(self.footer(),
                         "There is an alley to the north (n). "
                         "There is an alley below (d).")

    def test_a_dead_end_street_above(self):
        self.hang("up", self.room("street", "a stub"), "u")
        self.assertEqual(self.footer(), "There is a dead-end above (u).")

    def test_an_edge_below(self):
        drop = self.hang("down", self.room(key="the yard"), "d")
        drop.db.is_edge = True
        self.assertEqual(self.footer(), "There is an edge below (d).")

    def test_the_exit_typeclass_supplies_the_hint_itself(self):
        """Hung with no alias, an `up` exit still prints "(u)": the Exit
        typeclass adds the short form for the standard directions, so a
        bare "above." never renders for a key the game knows."""
        self.hang("up", self.room("fire escape", "landing"))
        self.assertEqual(self.footer(), "There is a fire escape above (u).")


class TestWhatIsPutOff(_Footer):

    def test_a_compass_exit_still_reads_to_the(self):
        self.hang("north", self.room("fire escape", "landing"), "n")
        self.assertEqual(self.footer(), "There is a fire escape to the north (n).")

    def test_a_named_exit_still_reads_to_the(self):
        """The Brackett landing's `window` (owner, 2026-10-23: "The others
        can be put off for now. I don't take issue with them.")."""
        self.hang("window", self.room("fire escape", "landing"))
        self.assertEqual(self.footer(), "There is a fire escape to the window.")

    def test_a_named_exit_answering_to_down_is_still_named(self):
        """`drop` with alias `down`, as on the Brackett fire escape: the
        key decides, so it keeps "to the"."""
        drop = self.hang("drop", self.room(key="the alley"), "down")
        self.assertEqual(self.footer(), "There is an exit to the drop (down).")

    def test_the_vertical_words_are_up_and_down_only(self):
        self.assertEqual(VERTICAL_EXITS, {"up": "above", "down": "below"})


class TestTheGlance(_Footer):
    """A figure stands in an open-air room reached by a vertical exit."""

    def setUp(self):
        super().setUp()
        self.platform = self.room("farm", "a growing platform")
        self.neighbour = create.create_object(
            "typeclasses.characters.Character", key="a neighbour",
            location=self.platform)
        self.neighbour.msg = lambda text=None, **kw: None

    def test_a_lone_figure_above(self):
        self.hang("up", self.platform, "u")
        self.assertIn("You see a lone figure above.", self.look())
        self.assertNotIn("to the up", self.look())

    def test_a_lone_figure_below(self):
        self.hang("down", self.platform, "d")
        self.assertIn("You see a lone figure below.", self.look())

    def test_a_group_above(self):
        create.create_object("typeclasses.characters.Character",
                             key="another", location=self.platform
                             ).msg = lambda text=None, **kw: None
        self.hang("up", self.platform, "u")
        self.assertIn("You see a group of people standing above.", self.look())

    def test_a_crowd_below(self):
        from unittest.mock import patch
        from typeclasses.rooms import crowd_system
        self.hang("down", self.platform, "d")
        with patch.object(crowd_system, "crowd_hides_figures", return_value=True):
            look = self.look()
        self.assertIn("You see a crowd below.", look)

    def test_a_crowd_to_the_north_and_a_crowd_below_are_two_sentences(self):
        from unittest.mock import patch
        from typeclasses.rooms import crowd_system
        self.hang("north", self.room("street", "a street"), "n")
        self.hang("down", self.platform, "d")
        with patch.object(crowd_system, "crowd_hides_figures", return_value=True):
            look = self.look()
        self.assertIn("You see a crowd to the north. You see a crowd below.", look)

    def test_two_crowded_streets_still_share_one_sentence(self):
        from unittest.mock import patch
        from typeclasses.rooms import crowd_system
        self.hang("north", self.room("street", "a street"), "n")
        self.hang("east", self.room("street", "another"), "e")
        with patch.object(crowd_system, "crowd_hides_figures", return_value=True):
            look = self.look()
        self.assertIn("You see crowds to the north and east.", look)

    def test_the_control_a_compass_glance_is_unchanged(self):
        self.hang("north", self.platform, "n")
        self.assertIn("You see a lone figure to the north.", self.look())
