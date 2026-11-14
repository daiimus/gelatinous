"""A real name opens no door (#3816).

The owner, testing a disguise: "I'm still able to guess the object actual
name ... to look at or otherwise interact with them even when the
disguise ... holds up."

`look` refused a real name. Nine other commands did not, because they
hand `Character.search` a pool (`candidates=`, `location=`) and a pool
used to switch the identity rule off. Each of them was looking for a
THING, found the person whose real key the word matched, and refused to
act on a person; the refusal told the player the guess was right and
whose name it was, and `jump on` printed the key back.

Real commands on fresh bodies. What is pinned:

* at every one of the nine doors, typing somebody's real name gets, word
  for word, what typing a name nobody has gets;
* the same for a fragment of it and for a word two real names share;
* every call shape of `Character.search` that carries a pool;
* the controls: a thing in the same pool is still found, a name the
  searcher gave is still theirs to type, staff keep the privilege, and a
  global search stays plain Evennia;
* that no command a player can run searches the whole game.
"""
import ast
import re
from pathlib import Path

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character


def only_what_they_can_name(*args, **kwargs):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree: a module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence."""
    from world import search
    return search.only_what_they_can_name(*args, **kwargs)

REAL = "Jorvik Ansel"
SHARES_A_WORD = "Jorvik Brandt"
SDESC = "gaunt man"
NOBODY = "zzyzx qorv"

#: Every command found handing the search a pool that holds people.
#: `{}` is where the typed name goes.
DOORS = (
    "get {}",
    "get thing from {}",
    "get {} from here",
    "inspect {}",
    "sever {}",
    "buy thing from {}",
    "jump on {}",
    "jump off {} edge",
    "jump across {} edge",
    "throw rock to {}",
)


def plain(text):
    return re.sub(r"\|[a-zA-Z0-9/\[\]#=]+?|\x1b\[[0-9;]*m", "", text)


class _Strangers(EvenniaTest):
    """A viewer who has remembered nobody, and two strangers.

    Fresh bodies with no account: `execute_cmd` on the harness's own
    `char1` (an account and no session) never completes without a
    reactor, and prints and writes nothing."""

    def setUp(self):
        super().setUp()
        self.viewer = self.body("Petra Lund", "short", "stocky", "woman")
        self.them = self.body(REAL, "tall", "lean", "man")
        self.other = self.body(SHARES_A_WORD, "short", "lean", "woman")
        self.rock = create_object("typeclasses.items.Item", key="rock",
                                  location=self.viewer)
        self.viewer.hands = {"left_hand": self.rock}
        self.heard = []

        def hear(text=None, **kwargs):
            if isinstance(text, (tuple, list)):
                text = text[0]
            if text:
                self.heard.append(plain(str(text)))

        self.viewer.msg = hear

    def body(self, key, height, build, keyword):
        char = create_object(Character, key=key, location=self.room1)
        char.sleeve_uid = f"sleeve-{key.lower()}"
        char.height, char.build, char.sdesc_keyword = height, build, keyword
        char.recognition_memory = {}
        char.db.disguise_pierce_cache = None
        return char

    def do(self, command):
        self.heard.clear()
        self.viewer.execute_cmd(command)
        return "\n".join(self.heard)

    def told_for(self, door, word):
        """What the door answers, with the typed word blanked out."""
        return re.sub(re.escape(word), "*", self.do(door.format(word)),
                      flags=re.IGNORECASE)


class TestTheNineDoors(_Strangers):
    def test_the_setup_is_what_it_says(self):
        """The control on everything below: the stranger is there, is
        seen by description, and that description is not his name."""
        self.assertEqual(self.them.get_sdesc(), SDESC)
        self.assertIn(SDESC, self.do("look"))
        self.assertNotIn("Jorvik", self.do("look"))

    def test_a_real_name_gets_what_a_name_nobody_has_gets(self):
        for door in DOORS:
            with self.subTest(door=door):
                real = self.told_for(door, REAL.lower())
                self.assertTrue(real, "the command said nothing at all")
                self.assertEqual(real, self.told_for(door, NOBODY))
                self.assertNotIn(SDESC, real)

    def test_so_does_a_fragment_of_it(self):
        for door in DOORS:
            with self.subTest(door=door):
                real = self.told_for(door, "ans")
                self.assertEqual(real, self.told_for(door, "zzy"))
                self.assertNotIn(SDESC, real)
                self.assertNotIn(REAL, self.do(door.format("ans")))

    def test_and_a_word_two_real_names_share_lists_nobody(self):
        for door in DOORS:
            with self.subTest(door=door):
                real = self.told_for(door, "jorvik")
                self.assertEqual(real, self.told_for(door, "zzyzx"))
                self.assertNotIn("man", real)

    def test_the_door_that_always_held_still_does(self):
        self.assertEqual(self.do(f"look {REAL.lower()}"),
                         f"Could not find '{REAL.lower()}'.")


class TestWhatIsStillFound(_Strangers):
    """The controls. The rule drops a person reached by real name and
    nothing else."""

    def test_a_thing_in_the_same_pool(self):
        pebble = create_object("typeclasses.items.Item", key="pebble",
                               location=self.room1)
        told = self.do("get pebble")
        self.assertNotIn("don't see", told)
        self.assertEqual(pebble.location, self.viewer)

    def test_somebody_by_a_name_the_searcher_gave_them(self):
        """They named him with a word of his real name. It is their
        name for him now, and theirs to type."""
        self.do("remember gaunt man as Ansel")
        self.assertEqual(self.do("get ansel"), "You can't pick up Ansel.")

    def test_staff(self):
        self.viewer.check_permstring = lambda perm: True
        self.assertEqual(self.do(f"get {REAL.lower()}"),
                         f"You can't pick up a {SDESC}.")

    def test_a_handed_over_pool_does_not_turn_a_description_into_a_person(
            self):
        """As it always was: `get` is looking for a thing, and Evennia
        matches the pool by key. A command that means a person asks
        `resolve_character_target`."""
        self.assertEqual(self.do("get gaunt man"),
                         "You don't see a 'gaunt man' here.")


class TestEveryCallShape(_Strangers):
    """`Character.search` itself, however it is called."""

    def found(self, query, **kwargs):
        return self.viewer.search(query, quiet=True, **kwargs)

    def test_a_list_of_candidates(self):
        self.assertEqual(self.found(REAL, candidates=[self.them]), [])

    def test_a_location(self):
        self.assertEqual(self.found(REAL, location=self.room1), [])

    def test_both(self):
        self.assertEqual(
            self.found(REAL, candidates=[self.them], location=self.room1),
            [])

    def test_out_loud_it_reads_as_nothing_found(self):
        self.heard.clear()
        self.assertIsNone(self.viewer.search(REAL, location=self.room1))
        self.assertEqual(self.heard, [f"Could not find '{REAL}'."])

    def test_two_people_matched_by_real_name_are_not_listed(self):
        self.heard.clear()
        self.assertIsNone(self.viewer.search("jorvik", location=self.room1))
        self.assertEqual(self.heard, ["Could not find 'jorvik'."])

    def test_a_thing_beside_them_in_the_pool_is_found(self):
        self.assertEqual(
            self.found("Obj", candidates=[self.obj1, self.them]),
            [self.obj1])

    def test_one_thing_and_one_person_by_real_name_is_one_match(self):
        """Not a multimatch that lists the person."""
        thing = create_object("typeclasses.items.Item", key="jorvik idol",
                              location=self.room1)
        self.heard.clear()
        self.assertEqual(self.viewer.search("jorvik", location=self.room1),
                         thing)
        self.assertEqual(self.heard, [])

    def test_staff_keep_the_real_name(self):
        self.viewer.check_permstring = lambda perm: True
        self.assertEqual(self.found(REAL, candidates=[self.them]),
                         [self.them])

    def test_a_search_of_the_whole_game_is_plain_evennia(self):
        """The one exemption. No command a player can run makes one;
        `TestNoPlayerCommandSearchesTheWholeGame` holds that."""
        self.assertEqual(self.found(REAL, global_search=True), [self.them])

    def test_an_object_number_is_refused_to_a_player(self):
        self.assertEqual(self.found(self.them.dbref), [])


class TestTheRule(_Strangers):
    def test_staff_keep_everything(self):
        found = [self.obj1, self.them]
        self.assertEqual(
            only_what_they_can_name(self.viewer, found, REAL, staff=True),
            found)

    def test_a_player_keeps_things_and_people_they_can_name(self):
        self.assertEqual(
            only_what_they_can_name(self.viewer, [self.obj1, self.them],
                                    REAL, staff=False),
            [self.obj1])
        self.assertEqual(
            only_what_they_can_name(self.viewer, [self.them], SDESC,
                                    staff=False),
            [self.them])


COMMANDS = Path(__file__).resolve().parents[2] / "commands"


def _lock_of(cls: ast.ClassDef) -> str:
    for node in cls.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "locks"
                for t in node.targets):
            if isinstance(node.value, ast.Constant):
                return str(node.value.value)
    return ""


class TestNoPlayerCommandSearchesTheWholeGame(EvenniaTest):
    """`global_search=True` is the one shape the identity rule does not
    cover: it is Evennia's own search by key, for staff tooling. So it
    may only appear in a command whose lock names a permission."""

    def test_every_global_search_sits_behind_a_staff_lock(self):
        seen = 0
        for path in sorted(COMMANDS.rglob("*.py")):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text())
            for cls in (n for n in ast.walk(tree)
                        if isinstance(n, ast.ClassDef)):
                for call in (n for n in ast.walk(cls)
                             if isinstance(n, ast.Call)):
                    if not any(kw.arg == "global_search"
                               and isinstance(kw.value, ast.Constant)
                               and kw.value.value is True
                               for kw in call.keywords):
                        continue
                    seen += 1
                    with self.subTest(file=path.name, command=cls.name):
                        self.assertIn("perm(", _lock_of(cls))
        self.assertGreater(seen, 0, "the scan found nothing to check")

    def test_and_none_sits_outside_a_command_class(self):
        for path in sorted(COMMANDS.rglob("*.py")):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text())
            inside = {id(call) for cls in ast.walk(tree)
                      if isinstance(cls, ast.ClassDef)
                      for call in ast.walk(cls)
                      if isinstance(call, ast.Call)}
            for call in (n for n in ast.walk(tree)
                         if isinstance(n, ast.Call)):
                if any(kw.arg == "global_search" for kw in call.keywords):
                    with self.subTest(file=path.name, line=call.lineno):
                        self.assertIn(id(call), inside)
