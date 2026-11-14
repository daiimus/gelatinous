"""A combat line names nobody by real name (#3819).

Two lines sent to players carried a character's real key:

* break free of somebody's aim, and the AIMER read "You stop aiming at
  ... as <real name> breaks free.";
* use somebody as a shield against a blast, and each of the two was told
  the other's real name.

Both came from the same omission. The second went through
`get_display_name_safe(character)`, whose reader was optional, and a
call that left the reader out got the real key. The reader is required
now; `None` says "this is a log line" out loud.
"""
import ast
import inspect
import re
from pathlib import Path
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.combat.utils import get_display_name_safe

ROOT = Path(__file__).resolve().parents[2]


def plain(text):
    return re.sub(r"\|[a-zA-Z0-9/\[\]#=]+?|\x1b\[[0-9;]*m", "", text)


class _Strangers(EvenniaTest):
    """Three people who have remembered nobody."""

    def setUp(self):
        super().setUp()
        self.heard = {}
        self.petra = self.body("Petra Lund", "short", "stocky", "woman")
        self.jorvik = self.body("Jorvik Ansel", "tall", "lean", "man")
        self.watcher = self.body("Odile Marsh", "short", "lean", "woman")

    def body(self, key, height, build, keyword):
        char = create_object(Character, key=key, location=self.room1)
        char.sleeve_uid = f"sleeve-{key.lower()}"
        char.height, char.build, char.sdesc_keyword = height, build, keyword
        char.recognition_memory = {}
        lines = self.heard.setdefault(char, [])

        def hear(text=None, **kwargs):
            if isinstance(text, (tuple, list)):
                text = text[0]
            if text:
                lines.append(plain(str(text)))

        char.msg = hear
        return char

    def nobody_named(self, lines):
        for line in lines:
            for name in ("Petra", "Lund", "Jorvik", "Ansel", "Odile", "Marsh"):
                self.assertNotIn(name, line)


class TestBreakingFreeOfAnAim(_Strangers):
    def setUp(self):
        super().setUp()
        self.petra.ndb.aiming_at = self.jorvik
        self.jorvik.ndb.aimed_at_by = self.petra
        rolls = mock.patch("commands.combat.movement.standard_roll",
                           side_effect=[(20, 0, 0), (1, 0, 0)])
        rolls.start()
        self.addCleanup(rolls.stop)
        from commands.combat.movement import break_aim_lock
        self.freed = break_aim_lock(self.jorvik)

    def test_he_got_away(self):
        """The control: the branch that speaks was taken."""
        self.assertTrue(self.freed)
        self.assertIsNone(self.petra.ndb.aiming_at)

    def test_the_aimer_reads_him_as_she_sees_him(self):
        line = next(l for l in self.heard[self.petra]
                    if l.startswith("You stop aiming"))
        self.assertTrue(line.endswith("as a gaunt man breaks free."), line)

    def test_and_no_line_she_gets_has_a_real_name(self):
        self.assertTrue(self.heard[self.petra])
        self.nobody_named(self.heard[self.petra])


class TestAHumanShield(_Strangers):
    def setUp(self):
        super().setUp()
        # The room line is only rendered for somebody with a session or
        # an `at_msg_receive` of their own; these bodies have neither.
        heard = mock.patch("world.identity_utils._hears_broadcasts",
                           return_value=True)
        heard.start()
        self.addCleanup(heard.stop)
        from world.combat.explosives import send_grenade_shield_messages
        send_grenade_shield_messages(self.petra, self.jorvik)

    def test_the_one_holding_reads_the_shield_as_she_sees_him(self):
        self.assertEqual(len(self.heard[self.petra]), 1)
        self.assertIn("a gaunt man", self.heard[self.petra][0])

    def test_the_shield_reads_her_as_he_sees_her(self):
        self.assertEqual(len(self.heard[self.jorvik]), 1)
        self.assertIn("a squat woman", self.heard[self.jorvik][0])

    def test_somebody_watching_reads_both_their_own_way(self):
        self.assertEqual(len(self.heard[self.watcher]), 1)
        self.assertIn("gaunt man", self.heard[self.watcher][0])
        self.assertIn("squat woman", self.heard[self.watcher][0])

    def test_and_nobody_is_told_a_real_name(self):
        for lines in self.heard.values():
            self.nobody_named(lines)


class TestTheHelperWantsAReader(_Strangers):
    def test_the_reader_cannot_be_left_out(self):
        reader = inspect.signature(get_display_name_safe).parameters["observer"]
        self.assertIs(reader.default, inspect.Parameter.empty)

    def test_a_reader_gets_their_own_view(self):
        self.assertEqual(get_display_name_safe(self.jorvik, self.petra),
                         "a gaunt man")

    def test_none_is_a_log_line_and_gets_the_key(self):
        self.assertEqual(get_display_name_safe(self.jorvik, None),
                         "Jorvik Ansel")

    def test_no_call_in_the_game_leaves_the_reader_out(self):
        """Read off the syntax tree, so a call split over two lines is
        seen and prose in a comment is not."""
        seen = 0
        for top in ("commands", "typeclasses", "world"):
            for path in sorted((ROOT / top).rglob("*.py")):
                for node in ast.walk(ast.parse(path.read_text())):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    name = (func.id if isinstance(func, ast.Name)
                            else getattr(func, "attr", ""))
                    if name != "get_display_name_safe":
                        continue
                    seen += 1
                    with self.subTest(file=path.name, line=node.lineno):
                        self.assertGreaterEqual(
                            len(node.args) + len(node.keywords), 2)
        self.assertGreater(seen, 100, "the scan found too little to trust")
