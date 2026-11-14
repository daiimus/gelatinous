"""Remains are named for the reader (#3821).

Two places told people who a body was.

* A preserved description that says ``{name}`` ("{name} has a scar")
  was filled, on a corpse or a severed part, with the dead character's
  REAL KEY, for everybody who looked. On a living body the same token
  is the looker's own name for them.
* `get`, `drop`, `give` and `wrest` wrote a corpse or a severed head
  into the room's line the way the ACTOR sees it. Remains are named per
  observer ("fresh corpse (Jorge)" to somebody who knew him), so the
  room read who the actor took the dead to be.

Pinned: the name in the prose is the name the reader knew them by, or
"the corpse"; the real key is in no line anybody reads; and each of the
four commands hands remains to the room to be named per reader.
"""
import inspect
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import get_apparent_uid_for_decay

REAL = "Jorvik Ansel"


def named_for_each(*args):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree: a module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence."""
    from world import identity_utils
    return identity_utils.named_for_each(*args)


class _AtTheBody(EvenniaTest):
    """A corpse whose description names the dead, somebody who knew him
    as Jorge, and a stranger."""

    def setUp(self):
        super().setUp()
        self.corpse = create_object("typeclasses.corpse.Corpse",
                                    key="fresh corpse", location=self.room1)
        self.corpse.db.sleeve_uid = "sleeve-dead"
        self.corpse.db.original_character_name = REAL
        self.corpse.db.original_gender = "male"
        self.corpse.db.species = "human"
        self.corpse.db.longdesc_data = {
            "chest": "{name} has a scar across {their} chest."}
        self.friend = self.body("Petra Lund")
        self.stranger = self.body("Odile Marsh")
        look = get_apparent_uid_for_decay(self.corpse,
                                          self.corpse.get_decay_stage())
        self.friend.recognition_memory = {look: {"assigned_name": "Jorge"}}

    def body(self, key):
        char = create_object(Character, key=key, location=self.room1)
        char.sleeve_uid = f"sleeve-{key.lower()}"
        char.height, char.build, char.sdesc_keyword = "short", "lean", "woman"
        char.recognition_memory = {}
        return char


class TestWhoTheBodyIsToEachOfThem(_AtTheBody):
    def test_the_setup_is_what_it_says(self):
        """The control: the header already told them apart."""
        self.assertTrue(
            self.corpse.get_display_name(self.friend).endswith("(Jorge)"))
        self.assertNotIn("(", self.corpse.get_display_name(self.stranger))

    def test_the_bearer_gives_the_name_alone(self):
        self.assertEqual(self.corpse.recognised_as(self.friend), "Jorge")
        self.assertIsNone(self.corpse.recognised_as(self.stranger))
        self.assertIsNone(self.corpse.recognised_as(None))


class TestTheNameInTheProse(_AtTheBody):
    def test_somebody_who_knew_him_reads_the_name_they_knew(self):
        seen = self.corpse.return_appearance(self.friend)
        self.assertIn("Jorge has a scar across his chest.", seen)

    def test_a_stranger_reads_the_corpse(self):
        seen = self.corpse.return_appearance(self.stranger)
        self.assertIn("the corpse has a scar across his chest.", seen)

    def test_nobody_reads_the_real_name(self):
        for who in (self.friend, self.stranger):
            with self.subTest(who=who.key):
                seen = self.corpse.return_appearance(who)
                self.assertNotIn("Jorvik", seen)
                self.assertNotIn("Ansel", seen)

    def test_a_severed_limb_never_names_anybody(self):
        """Only the head carries a face."""
        arm = create_object("typeclasses.items.Appendage",
                            key="severed arm", location=self.room1)
        arm.db.original_character_name = REAL
        arm.db.original_gender = "male"
        arm.db.longdesc_data = {"left_arm": "{name} wore a tattoo here."}
        for who in (self.friend, self.stranger):
            with self.subTest(who=who.key):
                seen = arm.return_appearance(who)
                self.assertIn("the corpse wore a tattoo here.", seen)
                self.assertNotIn("Jorvik", seen)


class TestTheRoomsLine(_AtTheBody):
    def heard_by(self, template, refs, exclude=()):
        from world.identity_utils import msg_room_identity
        heard = {}
        for who in (self.friend, self.stranger):
            lines = heard.setdefault(who, [])
            who.msg = (lambda text=None, _lines=lines, **kw:
                       _lines.append(text[0] if isinstance(text, tuple)
                                     else text))
        hears = mock.patch("world.identity_utils._hears_broadcasts",
                           return_value=True)
        hears.start()
        self.addCleanup(hears.stop)
        msg_room_identity(location=self.room1, template=template,
                          char_refs=refs, exclude=list(exclude))
        return heard

    def test_a_thing_is_written_as_the_actor_sees_it(self):
        refs = {"actor": self.char1}
        self.assertEqual(named_for_each(self.obj1, self.char1, "item", refs),
                         self.obj1.get_display_name(self.char1))
        self.assertEqual(list(refs), ["actor"])

    def test_remains_are_handed_to_the_room_to_name(self):
        refs = {"actor": self.char1}
        self.assertEqual(
            named_for_each(self.corpse, self.char1, "item", refs), "{item}")
        self.assertIs(refs["item"], self.corpse)

    def test_and_each_reader_gets_their_own(self):
        refs = {"actor": self.char1}
        written = named_for_each(self.corpse, self.friend, "item", refs)
        heard = self.heard_by(f"{{actor}} drops {written}.", refs)
        self.assertTrue(heard[self.friend][0].endswith("(Jorge)."),
                        heard[self.friend])
        self.assertNotIn("Jorge", heard[self.stranger][0])
        self.assertTrue(heard[self.stranger][0].endswith("corpse."),
                        heard[self.stranger])

    def test_all_four_commands_do_it(self):
        """Read off the source: the room's line of each is built with
        `named_for_each`, and none writes the actor's own name for the
        thing into a room template any more."""
        from commands import CmdInventory as inv
        for name, func in (
                ("drop", inv.CmdDrop.func),
                ("get", inv.CmdGet._give_item_to_character),
                ("give", inv.CmdGive.func),
                ("wrest (won)", inv.CmdWrest._announce_success),
                ("wrest (lost)", inv.CmdWrest._announce_failure)):
            with self.subTest(command=name):
                source = inspect.getsource(func)
                self.assertIn("named_for_each(", source)
                for line in source.splitlines():
                    if "template=f" in line:
                        self.assertNotIn("{item_name}", line)
                        self.assertNotIn("{container_name}", line)
