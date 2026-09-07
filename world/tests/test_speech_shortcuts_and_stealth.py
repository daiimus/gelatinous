""""hello works, and a typo does not blow your cover (#2529, #2530).

## #2529 — the shortcuts matched no command

`Command.match` tests `arg_regex` against **the remainder of the raw
input**, and `COMMAND_DEFAULT_ARG_REGEX` is `^[ /]|\\n|$`:

| input | alias | remainder tested | matches |
|---|---|---|---|
| `"hello there` | `"` | `hello there` | **no** |
| `" hello there` | `"` | ` hello there` | yes |
| `:waves` | `:` | `waves` | **no** |
| `: waves` | `:` | ` waves` | yes |

So the two speech shortcuts the game's own help advertises — and the
commonest speech idiom in MUDs — did nothing. Evennia's own `CmdSay`
carries `arg_regex = None` with the comment *"don't require a space
after `say/'/\"`"*, and `CmdPose` carries the same; this game's
replacements dropped it. `CmdDotPose` already had its own
(`r"(?s).*"`), which is why `.pose` was never affected.

Fixed the vanilla way — the upstream line, not a local parser.

## #2530 — the reveal ran before the guards

All four speech/pose commands called `break_stealth(caller)` as the
first statement of `func()`. `break_stealth` is not a test; it is the
reveal. It clears `db.hidden`, pushes **every** occupant of the room to
`ALERT`, tells the actor *"You abandon any pretense of hiding"* and
narrates their emergence to everyone who could not previously see them.

None of that was conditional on the command succeeding, and nothing
re-hides on an error path. So a hidden character who typed `say` with no
argument, or `to bob` with no message, or misspelled a target name, was
un-hidden for an action that never happened.

The comment above each call already said the intent — *speaking* gives
you away. The placement made *typing* give you away. Each call now sits
below its command's last guard, `CmdTo`'s below the target search.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdCommunication import (CmdDotPose, CmdEmote, CmdSay,
                                       CmdTo)


class TestTheShortcutsMatch(EvenniaCommandTest):
    """Exercised through `Command.match`, the thing that was failing —
    not through `func`, which was never reached."""

    def matches(self, cmd, raw):
        """`match` returns a (key, alias) PAIR, and a failed match is
        `(None, None)` — a truthy tuple. Asserting on the return value
        itself passes either way; the matched key is the real answer."""
        return cmd.match(raw.lower())[0]

    def test_a_quote_with_no_space_matches_say(self):
        self.assertEqual(self.matches(CmdSay(), '"hello there'), '"')

    def test_a_quote_with_a_space_still_matches(self):
        self.assertEqual(self.matches(CmdSay(), '" hello there'), '"')

    def test_a_colon_with_no_space_matches_emote(self):
        self.assertEqual(self.matches(CmdEmote(), ":waves"), ":")

    def test_a_colon_with_a_space_still_matches(self):
        self.assertEqual(self.matches(CmdEmote(), ": waves"), ":")

    def test_the_word_keys_still_match(self):
        self.assertEqual(self.matches(CmdSay(), "say hello"), "say")
        self.assertEqual(self.matches(CmdEmote(), "emote waves"), "emote")
        self.assertEqual(self.matches(CmdEmote(), "pose waves"), "pose")

    def test_dot_pose_was_never_affected(self):
        self.assertEqual(self.matches(CmdDotPose(), ".lean back"), ".")


class _HiddenCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        for c in (self.char1, self.char2):
            c.location = self.room1
        self.char1.db.hidden = True

    def hidden(self):
        return self.char1.db.hidden is True


class TestATypoDoesNotRevealYou(_HiddenCase):
    def test_say_with_no_argument(self):
        self.call(CmdSay(), "", "Say what?")
        self.assertTrue(self.hidden())

    def test_emote_with_no_argument(self):
        self.call(CmdEmote(), "", "What do you want to emote?")
        self.assertTrue(self.hidden())

    def test_to_with_no_message(self):
        self.call(CmdTo(), "bob", "Usage: to <target> <message>")
        self.assertTrue(self.hidden())

    def test_to_with_a_target_that_is_not_there(self):
        """`CmdTo` revealed you before even searching for the target."""
        self.call(CmdTo(), "nobodyatall hello")
        self.assertTrue(self.hidden())

    def test_dot_pose_with_no_text(self):
        self.call(CmdDotPose(), "", "Usage:")
        self.assertTrue(self.hidden())


class TestSpeakingStillRevealsYou(_HiddenCase):
    """The spec's actual rule — the fix must not simply stop revealing."""

    def test_saying_something_reveals_you(self):
        self.call(CmdSay(), "hello there")
        self.assertFalse(self.hidden())

    def test_emoting_reveals_you(self):
        self.call(CmdEmote(), "waves slowly")
        self.assertFalse(self.hidden())

    def test_posing_reveals_you(self):
        self.call(CmdDotPose(), "lean back.")
        self.assertFalse(self.hidden())

    def test_speaking_to_someone_reveals_you(self):
        self.call(CmdTo(), f"{self.char2.key} hello")
        self.assertFalse(self.hidden())


class TestTheObserversAreNotAlertedEither(_HiddenCase):
    """`break_stealth` pushes every occupant to ALERT, which
    `is_hidden_from` reads as fully placed. A refused command must not
    leave that behind."""

    def awareness(self):
        from world.stealth import get_awareness
        return get_awareness(self.char2, self.char1)

    def test_a_refused_say_leaves_awareness_alone(self):
        before = self.awareness()
        self.call(CmdSay(), "", "Say what?")
        self.assertEqual(self.awareness(), before)

    def test_a_real_say_does_alert_them(self):
        self.call(CmdSay(), "hello there")
        from world.stealth import ALERT
        self.assertEqual(self.awareness(), ALERT)


class TestTheSourceKeepsTheOrder(EvenniaCommandTest):
    """Pinned: the whole defect was a call placed three lines too early,
    which reads as correct at a glance."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdCommunication.py").read_text(
            errors="ignore")

    def test_no_reveal_is_the_first_statement_of_a_func(self):
        body = self._source()
        self.assertNotIn("""        caller = self.caller
        # Speaking gives you away""", body)

    def test_both_shortcut_commands_declare_arg_regex(self):
        body = self._source()
        self.assertEqual(body.count("arg_regex = None"), 2)
