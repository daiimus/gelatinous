"""A real name opens no door (#3816).

The owner, testing a disguise: "I'm still able to guess the object actual
name ... to look at or otherwise interact with them even when the
disguise ... holds up."

`look` refused a real name. Ten other commands did not, because they
hand `Character.search` a pool (`candidates=`, `location=`) and Evennia
matches a pool by key and alias. Each of them was looking for a THING,
found the person whose real key the word matched, and refused to act on
a person; the refusal told the player the guess was right and whose name
it was, and `jump on` printed the key back.

The fix takes people whose real name is not on show out of the POOL,
before anything is matched (`Character.get_search_candidates`). A first
attempt filtered the RESULTS and review found the real name still
steering the answer three ways; each is a test here.

Real commands on fresh bodies. What is pinned:

* THE INVARIANT: whatever is typed, at every door and in every call
  shape, the answer is the same whether or not the words are somebody's
  real name or alias. Checked by asking twice, renaming everybody in
  between;
* at every door, a real name, a fragment of it and a word two real names
  share get, word for word, what a name nobody has gets;
* the three ways a filter on results fails: an alias hiding the thing
  beside it, a description word that is also the start of a real name,
  and a guess made by `remember`;
* the controls: a thing is still found, a body that is SEEN as its key
  is still reached by it, staff keep the privilege, a global search
  stays plain Evennia;
* that no command a player can run searches the whole game.
"""
import ast
import re
from pathlib import Path

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character

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

#: The doors that change nothing when the word happens to be a THING's
#: name, so the same question can be asked twice. With them, the
#: ordinary search, which has a fallback to Evennia's of its own.
ASKS_ONLY = tuple(d for d in DOORS if not d.startswith("get {}")) + (
    "look {}",
)


def name_is_hidden(obj):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree: a module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence."""
    from world import search
    return search.name_is_hidden(obj)


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

    def thing(self, key):
        return create_object("typeclasses.items.Item", key=key,
                             location=self.room1)

    def do(self, command):
        self.heard.clear()
        self.viewer.execute_cmd(command)
        return "\n".join(self.heard)

    def told_for(self, door, word):
        """What the door answers, with the typed word blanked out."""
        return re.sub(re.escape(word), "*", self.do(door.format(word)),
                      flags=re.IGNORECASE)


class TestTheDoors(_Strangers):
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


class TestARealNameChangesNothing(_Strangers):
    """The invariant itself. The room is set up the way the three review
    findings need it, every question is asked, everybody is given a
    different real name and no aliases, and every question is asked
    again. Nothing a player can read may differ."""

    WORDS = (REAL.lower(), "ans", "jorvik", "ansel", "brown",
             "man", "gaunt man", "manfred",
             "1st jorvik", "2nd jorvik", "jorvik-1", "jorvik-2",
             "2nd brown")

    def setUp(self):
        super().setUp()
        # A souled NPC is keyed "First Last" with both as aliases.
        self.them.aliases.add(["jorvik", "ansel", "brown"])
        # A second man, whose real name starts with a description word.
        # He is not built like the first: two men of one description
        # and `remember gaunt man as ...` below names neither of them.
        self.manfred = self.body("Manfred Ostrow", "short", "stocky", "man")
        # Things whose names a real name or alias would shadow.
        self.wig = self.thing("brown wig")
        self.idol = self.thing("jorvik idol")
        # A guess, made the only way a player can make one stick.
        self.do("remember gaunt man as Jorvik")
        from world.identity import get_assigned_name
        self.assertEqual(get_assigned_name(self.viewer, self.them), "Jorvik",
                         "the setup did not store the guess")

    def every_answer(self):
        answers = {}
        for door in ASKS_ONLY:
            for word in self.WORDS:
                answers[door, word] = self.do(door.format(word))
        for word in self.WORDS:
            for shape, kwargs in (
                    ("location", {"location": self.room1}),
                    ("candidates",
                     {"candidates": list(self.room1.contents)}),
                    ("ordinary", {})):
                found = self.viewer.search(word, quiet=True, **kwargs)
                answers[shape, word] = sorted(
                    "a person" if isinstance(obj, Character) else obj.key
                    for obj in found)
        return answers

    def test_ask_everything_rename_everybody_ask_again(self):
        before = self.every_answer()
        for who, new in ((self.them, "Qqq Www"), (self.other, "Rrr Ttt"),
                         (self.manfred, "Sss Vvv")):
            who.aliases.clear()
            who.key = new
        after = self.every_answer()
        for question in before:
            with self.subTest(question=question):
                self.assertEqual(before[question], after[question])

    def test_the_questions_were_worth_asking(self):
        """The control: some of them do find a thing, so equal answers
        are not two blanks."""
        answers = self.every_answer()
        self.assertEqual(answers["location", "brown"], ["brown wig"])
        self.assertEqual(answers["candidates", "jorvik"], ["jorvik idol"])
        self.assertIn("a person", answers["ordinary", "gaunt man"])
        # ... and the guess is in force: the ordinary search answers to it.
        self.assertEqual(answers["ordinary", "jorvik"], ["a person"])
        self.assertIn("Jorvik (a gaunt man)", answers["look {}", "jorvik"])


class TestWhatAFilterOnResultsGetsWrong(_Strangers):
    """The three review findings against the first attempt, one each,
    as a player would meet them."""

    def test_a_surname_alias_does_not_hide_the_wig(self):
        """Evennia tries an exact name before a partial one, and the
        alias was exact."""
        self.them.aliases.add(["jorvik", "ansel", "brown"])
        wig = self.thing("brown wig")
        self.do("get brown")
        self.assertEqual(wig.location, self.viewer)

    def test_nor_take_a_place_in_the_count(self):
        self.them.aliases.add(["jorvik"])
        idol = self.thing("jorvik idol")
        self.assertEqual(
            self.viewer.search("1st jorvik", location=self.room1,
                               quiet=True), [idol])
        self.assertEqual(
            self.viewer.search("2nd jorvik", location=self.room1,
                               quiet=True), [])

    def test_a_description_word_that_starts_a_real_name_finds_nobody(self):
        """`get man` found the one man whose real name began with it,
        and so said which man that was."""
        self.body("Manfred Ostrow", "tall", "lean", "man")
        self.assertEqual(self.do("get man"), "You don't see a 'man' here.")

    def test_a_guess_made_with_remember_is_not_confirmed(self):
        self.do("remember gaunt man as Jorvik")
        right = self.do("get jorvik")
        self.do("remember gaunt man as Zzyzx")
        wrong = self.do("get zzyzx")
        self.assertEqual(right.replace("jorvik", "*"),
                         wrong.replace("zzyzx", "*"))


class TestWhatIsStillFound(_Strangers):
    """The controls. The gate takes out a person whose real name is not
    on show, and nothing else."""

    def test_a_thing_in_the_same_pool(self):
        pebble = self.thing("pebble")
        told = self.do("get pebble")
        self.assertNotIn("don't see", told)
        self.assertEqual(pebble.location, self.viewer)

    def test_a_body_that_is_seen_as_its_key(self):
        """A mob, or an NPC with no description of its own: the key is
        what everybody sees, so it is no secret."""
        rat = create_object(Character, key="scrawny rat",
                            location=self.room1)
        self.assertFalse(name_is_hidden(rat))
        self.assertEqual(self.do("get rat"),
                         "You can't pick up scrawny rat.")

    def test_staff(self):
        self.viewer.check_permstring = lambda perm: True
        self.assertEqual(self.do(f"get {REAL.lower()}"),
                         f"You can't pick up a {SDESC}.")

    def test_a_handed_over_pool_does_not_find_people_by_description(self):
        """As it always was: `get` is looking for a thing. A command
        that means a person makes an ordinary search or asks
        `resolve_character_target`."""
        self.assertEqual(self.do("get gaunt man"),
                         "You don't see a 'gaunt man' here.")

    def test_the_ordinary_search_still_does(self):
        self.assertEqual(self.viewer.search("gaunt man", quiet=True),
                         [self.them])


class TestThePool(_Strangers):
    """`Character.get_search_candidates`, where the gate is."""

    def pool(self, **kwargs):
        return self.viewer.get_search_candidates("anything", **kwargs)

    def test_whose_name_is_hidden(self):
        self.assertTrue(name_is_hidden(self.them))
        self.assertFalse(name_is_hidden(self.obj1))
        self.assertFalse(name_is_hidden(self.char1))    # seen as "Char"

    def test_a_handed_over_list(self):
        self.assertEqual(
            self.pool(candidates=[self.obj1, self.them, self.char1]),
            [self.obj1, self.char1])

    def test_a_location(self):
        pool = self.pool(location=self.room1)
        self.assertIn(self.obj1, pool)
        self.assertNotIn(self.them, pool)
        self.assertNotIn(self.other, pool)

    def test_the_ordinary_reach(self):
        pool = self.pool()
        self.assertIn(self.viewer, pool)
        self.assertIn(self.room1, pool)
        self.assertNotIn(self.them, pool)

    def test_staff_keep_everybody(self):
        self.viewer.check_permstring = lambda perm: True
        self.assertIn(self.them, self.pool(location=self.room1))

    def test_a_search_of_the_whole_game_has_no_pool(self):
        """The one exemption, and it is Evennia's own: staff tooling.
        `TestNoPlayerCommandSearchesTheWholeGame` holds the other end."""
        self.assertIsNone(self.pool(global_search=True))
        self.assertEqual(
            self.viewer.search(REAL, global_search=True, quiet=True),
            [self.them])

    def test_an_object_number_is_refused_to_a_player(self):
        self.assertEqual(self.viewer.search(self.them.dbref, quiet=True),
                         [])


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
    """`global_search=True` is the one shape the identity gate does not
    cover: it has no pool. So it may only appear in a command whose lock
    names a permission."""

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
