"""A blind looker is not told what lies in the room or beyond the door
(#3479, #3382).

`Room.get_display_desc` already gives a sightless looker the void line and
withholds visual integrate prose (#3373); the doorway glance withholds who
stands beyond (#2793). But the room still listed its objects ("You see a
crate.") and who was standing here, and `look <direction>` still described
streetlight, shadow and the precarious edge. Both are visual reads and now
honour the same predicate. The exits line stays: a blind character can be
told an exit exists, as the #2793 test already records.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.perception import can_perceive_sense


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

    def test_a_hidden_bystander_is_not_passively_checked_by_blind_eyes(self):
        # the passive stealth tier is a glance; a looker who cannot see must
        # not spot a clumsy hider, nor earn the "not alone" cue from one
        self.blind(self.looker)
        self.bystander.db.hidden = True
        out = self.room1.get_display_characters(self.looker)
        self.assertNotIn("orrin", out.lower())
        self.assertNotIn("not alone", out.lower())


class TheBlindLookerAtTheDoor(_Scene):

    def test_the_directional_prose_is_withheld_and_the_fallback_speaks(self):
        self.blind(self.looker)
        self.assertEqual(self.door_desc(), "A passageway leading elsewhere.")

    def test_an_authored_exit_desc_still_speaks(self):
        self.door.db.desc = "A door."
        self.blind(self.looker)
        self.assertEqual(self.door_desc(), "A door.")

    def test_the_edge_is_not_described_to_the_blind(self):
        self.door.db.is_edge = True
        self.assertIn("precarious edge", self.door_desc())
        self.blind(self.looker)
        self.assertNotIn("edge", self.door_desc().lower())

    def test_the_street_is_not_described_to_the_blind(self):
        self.beyond.type = "street"
        self.beyond.outside = True
        far = create_object("typeclasses.rooms.Room", key="far")
        far.type = "street"
        create_object("typeclasses.exits.Exit", key="north", location=self.beyond, destination=far)
        create_object("typeclasses.exits.Exit", key="south", location=self.beyond, destination=self.room1)
        self.assertIn("street", self.door_desc().lower())
        self.blind(self.looker)
        self.assertNotIn("street", self.door_desc().lower())
        self.assertNotIn("Through the", self.door_desc())
