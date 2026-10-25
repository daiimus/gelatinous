"""#3596 -- aiming widens nothing; `look` reaches the aimed room itself.

While a character aimed down an exit, every lookup that named no pool
(`caller.search(name)`) searched their room AND the aimed room
(`Character.get_search_candidates`). It reached things, not people: the
identity pipeline read the looker's own room only, so `look knife` found
a knife on the street below a parapet and `look <the figure's
description>` did not. And it let `put`, `scan`, `diagnose`, `tune`,
`remember`, `to` and targeted emotes act on things three storeys down,
none of them with a distance check.

Owner, 2026-10-24, on the audit: remove the widening; `look <target>`
gets the aimed room explicitly, as `attack` and `throw` already do; the
rest go back to this room. Three rulings: `look <description>` down the
barrel works (yes), emotes across the aim stay unavailable (yes), `to`
and `whisper` at an object in the aimed room go away (yes).

Driven as char2, who holds no staff permission; char1 is a Developer in
EvenniaTest and would name people by key.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdInventory import CmdPut
from commands.CmdLook import CmdLook

ITEM_DESC = "It's a thing. Heavy enough to hurt if used wrong."


class _AimingNorth(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room2
        self.north = create_object("typeclasses.rooms.Room", key="North Street")
        self.north.db.type = "street"
        create_object("typeclasses.exits.Exit", key="north", aliases=["n"],
                      location=self.room1, destination=self.north)
        self.char2.location = self.room1
        self.char2.ndb.aiming_direction = "north"
        # a stranger on the street: no height/build yet, so the sdesc falls
        # back to the key and the identity matcher takes a prefix of it
        self.hawker = create_object("typeclasses.characters.Character",
                                    key="hawker", location=self.north)
        self.hawker.msg = lambda text=None, **kw: None

    def thing(self, key, location):
        return create_object("typeclasses.items.Item", key=key, location=location)

    def as_player(self, cmd, args):
        return self.call(cmd, args, caller=self.char2) or ""


class TestLookReachesTheAimedRoom(_AimingNorth):

    def test_a_thing_on_the_street(self):
        self.thing("rusty knife", self.north)
        self.assertIn(ITEM_DESC, self.as_player(CmdLook(), "rusty knife"))

    def test_a_person_on_the_street_by_description(self):
        out = self.as_player(CmdLook(), "hawker")
        self.assertNotIn("Could not find", out)
        self.assertIn("hawker", out.lower())

    def test_your_own_knife_is_still_in_reach(self):
        self.thing("rusty knife", self.char2)
        self.assertIn(ITEM_DESC, self.as_player(CmdLook(), "rusty knife"))

    def test_the_aimed_room_comes_first_when_both_have_one(self):
        here = self.thing("rusty knife", self.room1)
        there = self.thing("rusty knife", self.north)
        there.db.desc = "A knife on the street."
        here.db.desc = "A knife at your feet."
        self.assertIn("on the street", self.as_player(CmdLook(), "rusty knife"))

    def test_the_aimed_rooms_exits_are_not_targets(self):
        create_object("typeclasses.exits.Exit", key="east", aliases=["e"],
                      location=self.north, destination=self.room2)
        out = self.as_player(CmdLook(), "east")
        self.assertIn("Could not find", out)

    def test_not_aiming_is_this_room_only(self):
        self.char2.ndb.aiming_direction = None
        self.thing("rusty knife", self.north)
        self.assertIn("Could not find", self.as_player(CmdLook(), "rusty knife"))
        self.assertIn("Could not find", self.as_player(CmdLook(), "hawker"))


class TestNothingElseReaches(_AimingNorth):

    def test_a_bare_search_is_this_room_and_your_pockets(self):
        self.thing("distant crate", self.north)
        self.assertEqual(list(self.char2.search("distant crate", quiet=True)), [])

    def test_put_cannot_reach_a_container_on_the_street(self):
        coin = self.thing("brass coin", self.char2)
        self.thing("steel crate", self.north)
        out = self.as_player(CmdPut(), "coin in crate")
        self.assertIn("You don't see a 'crate' here.", out)
        self.assertEqual(coin.location, self.char2)

    def test_the_glance_and_aim_view_still_read_the_aimed_room(self):
        """`aimed_room_for` is the one seam the aim view reads."""
        self.assertIs(self.room1.aimed_room_for(self.char2), self.north)
        self.char2.ndb.aiming_direction = None
        self.assertIsNone(self.room1.aimed_room_for(self.char2))
