"""Staff is one question (#3818).

Staff may reach a person by real name. Six doors grant that, and they
asked two different questions about who staff is:

* `check_permstring("Builder")` on the character: the permission tags
  on the CHARACTER, or a superuser who is not quelled. A Builder, Admin
  or Developer account whose character carries only `player` failed it.
* the lock `perm(Builder)`: the puppeting ACCOUNT's permission, the
  object's own when nobody is puppeting it, and while quelled the lower
  of the two.

Observed in play with a Developer account, not quelled:
`.nod at <real name>` reached the person and `look <real name>` did not.

`world.search.may_use_real_names` is the second question, asked in one
place. Pinned here: who it says yes to, with real accounts; and that
every door asks it and nothing else.
"""
import inspect
from types import SimpleNamespace
from unittest import mock

from evennia import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character

REAL = "Jorvik Ansel"


def may_use_real_names(who):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree: a module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence."""
    from world import search
    return search.may_use_real_names(who)


class _Bodies(EvenniaTest):
    def body(self, key, height="short", build="stocky", keyword="woman"):
        char = create_object(Character, key=key, location=self.room1)
        char.sleeve_uid = f"sleeve-{key.lower()}"
        char.height, char.build, char.sdesc_keyword = height, build, keyword
        char.recognition_memory = {}
        char.permissions.add("Player")
        return char

    def played_by(self, char, *, permission="Player", superuser=False):
        """An account of that rank, puppeting *char* the way a login
        leaves it: the link, and the lock handler's superuser flag."""
        account = create_account(
            f"Acct{char.id}", email="t@example.com",
            password="zx-Harbor-93-lantern", is_superuser=superuser)
        account.permissions.clear()
        account.permissions.add(permission)
        char.account = account
        char.locks.cache_lock_bypass(char)
        return account

    def quell(self, char):
        """What the `quell` command does."""
        char.account.attributes.add("_quell", True)
        char.locks.reset()


class TestWhoIsStaff(_Bodies):
    def setUp(self):
        super().setUp()
        self.char = self.body("Petra Lund")

    def test_a_player(self):
        self.played_by(self.char)
        self.assertFalse(may_use_real_names(self.char))

    def test_a_builder_account_whose_character_is_tagged_player(self):
        """The case the old check got wrong."""
        self.played_by(self.char, permission="Builder")
        self.assertTrue(may_use_real_names(self.char))

    def test_a_developer_account(self):
        self.played_by(self.char, permission="Developer")
        self.assertTrue(may_use_real_names(self.char))

    def test_a_helper_account_is_below_the_line(self):
        self.played_by(self.char, permission="Helper")
        self.assertFalse(may_use_real_names(self.char))

    def test_any_of_them_quelled(self):
        for permission in ("Builder", "Admin", "Developer"):
            with self.subTest(permission=permission):
                char = self.body(f"Quelled {permission}")
                self.played_by(char, permission=permission)
                self.assertTrue(may_use_real_names(char))
                self.quell(char)
                self.assertFalse(may_use_real_names(char))

    def test_a_superuser(self):
        self.played_by(self.char, superuser=True)
        self.assertTrue(may_use_real_names(self.char))

    def test_a_superuser_quelled(self):
        self.played_by(self.char, superuser=True)
        self.quell(self.char)
        self.assertFalse(may_use_real_names(self.char))

    def test_a_tag_on_the_character_does_not_lift_a_player_account(self):
        """It did, under the old check. A rank is the account's."""
        self.played_by(self.char)
        self.char.permissions.add("Builder")
        self.assertFalse(may_use_real_names(self.char))

    def test_nobody_puppeting_reads_the_bodys_own_rank(self):
        """An NPC."""
        self.assertFalse(may_use_real_names(self.char))
        self.char.permissions.add("Builder")
        self.assertTrue(may_use_real_names(self.char))

    def test_something_with_no_lock_handler_is_not_staff(self):
        self.assertFalse(may_use_real_names(SimpleNamespace()))
        self.assertFalse(may_use_real_names(None))


class TestEveryDoorAsksIt(_Bodies):
    """Each door, with the one question answered both ways."""

    def setUp(self):
        super().setUp()
        self.viewer = self.body("Petra Lund")
        self.them = self.body(REAL, "tall", "lean", "man")
        # Somebody in the next room, for the look down an aim.
        self.far = self.body("Odile Marsh", "tall", "lean", "man")
        self.far.move_to(self.room2, quiet=True, move_hooks=False)

    def aimed_look(self, words):
        """`look <words>` while aiming into the next room: the door in
        `CmdLook.aimed_target`, called as the command calls it."""
        from commands.CmdLook import CmdLook
        cmd = CmdLook()
        cmd.caller = self.viewer
        cmd.args = words
        return cmd.aimed_target(self.viewer, self.room2)

    def answer(self, yes):
        asked = mock.patch("world.search.may_use_real_names",
                           side_effect=lambda who: yes and who is self.viewer)
        asked.start()
        self.addCleanup(asked.stop)

    def reached(self):
        from commands._identity_targeting import (
            resolve_character_in_rooms, resolve_character_target,
        )
        from world.emote import build_char_candidates
        return {
            "the ordinary search":
                self.viewer.search(REAL, quiet=True) == [self.them],
            "a handed-over pool":
                self.viewer.search(REAL, location=self.room1,
                                   quiet=True) == [self.them],
            "resolve_character_target":
                resolve_character_target(self.viewer, REAL) is self.them,
            "resolve_character_in_rooms":
                resolve_character_in_rooms(
                    self.viewer, REAL, [self.room1]) is self.them,
            "an emote token":
                any(name == REAL for name, _who, _cap in
                    build_char_candidates(self.viewer, [self.them])),
            "a look down an aim":
                self.aimed_look("Odile Marsh") is self.far,
        }

    def test_yes_opens_every_one(self):
        self.answer(True)
        for door, opened in self.reached().items():
            with self.subTest(door=door):
                self.assertTrue(opened)

    def test_no_opens_none(self):
        self.answer(False)
        for door, opened in self.reached().items():
            with self.subTest(door=door):
                self.assertFalse(opened)

    def test_the_aimed_look_still_finds_them_by_description(self):
        """The control on the aimed door: it is the real name that the
        answer decides, not whether the look works at all."""
        self.answer(False)
        self.assertIs(self.aimed_look("gaunt man"), self.far)

    def test_and_no_door_asks_the_old_question(self):
        """Read off the source of each door."""
        import commands._identity_targeting as targeting
        from commands.CmdLook import CmdLook
        from typeclasses.llm_npc import LLMNpc
        from world.emote import build_char_candidates
        doors = {
            "Character.search": Character.search,
            "Character.get_search_candidates":
                Character.get_search_candidates,
            "resolve_character_target": targeting.resolve_character_target,
            "resolve_character_in_rooms":
                targeting.resolve_character_in_rooms,
            "CmdLook.aimed_target": CmdLook.aimed_target,
            "build_char_candidates": build_char_candidates,
            "LLMNpc._mentions_self": LLMNpc._mentions_self,
        }
        for name, door in doors.items():
            with self.subTest(door=name):
                source = inspect.getsource(door)
                code = "\n".join(line for line in source.splitlines()
                                 if not line.strip().startswith("#"))
                self.assertIn("may_use_real_names(", code)
                self.assertNotIn(".check_permstring(", code)
                self.assertNotIn("check_lockstring(", code)


class TestAnOrdinaryStaffAccountAtTheDoorItWasShutOutOf(_Bodies):
    """The behaviour that changes: `look <real name>` for a Builder
    account, as it already was in an emote."""

    def setUp(self):
        super().setUp()
        self.viewer = self.body("Petra Lund")
        self.them = self.body(REAL, "tall", "lean", "man")
        self.played_by(self.viewer, permission="Builder")

    def test_not_quelled_the_real_name_reaches_them(self):
        self.assertEqual(self.viewer.search(REAL, quiet=True), [self.them])

    def test_quelled_it_does_not(self):
        self.quell(self.viewer)
        self.assertEqual(self.viewer.search(REAL, quiet=True), [])
