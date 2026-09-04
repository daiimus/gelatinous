"""`help tokens` states a design premise, and the cmdset has to honour it.

    "Time tokens read the colony clock. They belong on TIMEPIECES -- a
    worn chrono, a platform clock, an integrated display -- and that is
    deliberate: there is no command that tells you the hour. A character
    carrying nothing does not know what time it is."

That is what makes a chrono worth carrying. Evennia's stock `@time` sat
in the live player cmdset at `perm(Player)`, and what it printed was
worse than a clock: `datetime.now()`, the REAL-WORLD date, in the wrong
century and the wrong timezone (#2819).
"""
from unittest import TestCase

from evennia.utils.test_resources import EvenniaCommandTest

from commands.default_cmdsets import CharacterCmdSet
from world import help_entries


def _keys():
    cs = CharacterCmdSet()
    cs.at_cmdset_creation()
    keys = set()
    for cmd in cs.commands:
        keys.add(cmd.key)
        keys.update(getattr(cmd, "aliases", ()) or ())
    return keys


class TestNothingTellsYouTheHour(TestCase):
    def test_no_time_command_is_reachable(self):
        keys = _keys()
        for name in ("time", "@time", "uptime", "@uptime"):
            self.assertNotIn(name, keys,
                             f"'{name}' defeats the timepiece design")

    def test_the_rest_of_the_default_set_survives(self):
        """The pin: removing one inherited command must not cost the
        cmdset the defaults it is built on."""
        keys = _keys()
        for name in ("look", "get", "say", "inventory"):
            self.assertIn(name, keys)


class TestTheHelpDoesNotPromiseWhatTheRendererDoesNot(TestCase):
    """The same entry claimed an unrecognised braced word is "left on
    screen literally with its braces intact ... rather than silently
    vanishing", using {thier} as the reassuring example. The renderer
    conjugates it: {thier} comes out as "thiers". The paragraph told a
    builder a preview would catch their typos, so they would not look.
    """

    def _tokens_entry(self):
        for entry in help_entries.HELP_ENTRY_DICTS:
            if entry.get("key") == "tokens":
                return entry["text"]
        self.fail("the 'tokens' help entry is gone")

    def test_it_does_not_promise_surviving_braces(self):
        text = self._tokens_entry()
        self.assertNotIn("braces intact", text)
        self.assertNotIn("silently vanishing", text)

    def test_it_still_documents_the_verb_rule(self):
        text = self._tokens_entry()
        self.assertIn("conjugated", text)


class TestTheRendererReallyDoesConjugate(EvenniaCommandTest):
    """The behaviour the help now describes, asserted against the real
    renderer rather than taken on trust."""

    def test_an_unknown_braced_word_loses_its_braces(self):
        out = self.char1._render_body_longdesc(
            "chest", "A typo like {thier} scar runs deep.", self.char1)
        self.assertNotIn("{", out)
        self.assertIn("thiers", out)
