"""NPCs learn names without the model (#2390) — platform criterion 10.

An NPC learning your name used to happen ONLY when the LLM decided to call
the `remember` tool. Turn the breaker off and no NPC in the colony ever
learned anybody's name again: a conversational courtesy living behind a
model turn, which platform law 4 forbids.

Introductions are clerical, so the engine does them. The LLM keeps
`remember` for the thing it is genuinely better at — coining a nickname
nobody offered.

What gets written is an `assigned_name`: an observer's chosen LABEL, not a
verified identity. A name given in speech is a claim and may be a lie, and
that is correct — recognition memory records what the NPC believes, and the
disguise layer is built on that belief being wrong sometimes. A verified
name needs proof and is a separate field this never touches.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.identity import parse_introduction


class TestTheParser(BaseEvenniaTest):
    """Table-driven: a false positive is worse than a miss, because the name
    becomes the NPC's address handle and shows up in every later pose."""

    def test_it_catches_the_ways_people_introduce_themselves(self):
        for line, expected in [
            ("My name is Marcus", "Marcus"),
            ("my name is marcus", "marcus"),          # strong lead, no capital
            ("My name's Marcus", "Marcus"),
            ("The name's Blade", "Blade"),
            ("I go by Red", "Red"),
            ("I'm called Doc", "Doc"),
            ("I am called Doc", "Doc"),
            ("I'm Marcus", "Marcus"),
            ("I am Marcus", "Marcus"),
            ("Call me Blade", "Blade"),
            ("You can call me Blade", "Blade"),
            ("They call me the Toe Guy", "the Toe Guy"),
            ("Name's Ruiz", "Ruiz"),
            ("I'm Robert Paulson", "Robert Paulson"),
            ("I'm Marcus, and I need work", "Marcus"),
            ("I'm Marcus. Need a drink.", "Marcus"),
            ("Evening. My name is Ruiz", "Ruiz"),
        ]:
            self.assertEqual(parse_introduction(line), expected, line)

    def test_it_does_not_christen_people_after_ordinary_speech(self):
        for line in [
            "I'm tired",
            "I'm fine",
            "I'm broke",
            "I'm looking for work",
            "I'm not interested",
            "I'm just here for the drink",
            "call me later",
            "Call me back",
            "call me when you hear something",
            "call me if it goes bad",
            "they call me whatever they like",
            "I'm sorry",
            "I am busy",
            "I'm no friend of his",
            "",
            "what's your name?",
            "the name of the game",
        ]:
            self.assertIsNone(parse_introduction(line), line)

    def test_a_lowercase_ambiguous_lead_is_refused(self):
        """'i'm marcus' is a real introduction and 'i'm tired' is not, and
        lowercase gives nothing to tell them apart. The strong forms exist
        for exactly this — 'my name is marcus' still lands."""
        self.assertIsNone(parse_introduction("i'm marcus"))
        self.assertEqual(parse_introduction("my name is marcus"), "marcus")

    def test_a_name_is_bounded(self):
        long_line = "I'm " + " ".join(["Word"] * 12)
        self.assertEqual(len(parse_introduction(long_line).split()), 4)


class TestTheNpcWritesItDown(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="npc", location=self.room1)

    def test_an_introduction_is_recorded_through_the_real_command(self):
        """Not a bespoke write — the same `remember` command a player types,
        so the guards and the messaging stay in one place."""
        with mock.patch.object(self.npc, "execute_cmd") as cmd, \
                mock.patch("world.identity.get_assigned_name",
                           return_value=None):
            self.npc._note_introduction("I'm Marcus", self.char1)
        self.assertTrue(cmd.called)
        self.assertIn("as Marcus", cmd.call_args.args[0])

    def test_ordinary_speech_records_nothing(self):
        with mock.patch.object(self.npc, "execute_cmd") as cmd:
            self.npc._note_introduction("I'm tired", self.char1)
        cmd.assert_not_called()

    def test_it_works_with_the_llm_off(self):
        """The whole point of criterion 10. `_handle_directed_speech` runs
        before any LLM gate, so this must not depend on one."""
        with mock.patch("typeclasses.llm_npc.llm_enabled",
                        return_value=False), \
                mock.patch.object(self.npc, "execute_cmd") as cmd, \
                mock.patch("world.identity.get_assigned_name",
                           return_value=None):
            self.npc._note_introduction("My name is Ruiz", self.char1)
        self.assertTrue(cmd.called)

    def test_an_introduction_still_gets_a_reply(self):
        """Recording is clerical and must NOT swallow the turn — saying your
        name to someone should not be met with silence."""
        with mock.patch.object(self.npc, "_note_introduction"), \
                mock.patch("world.service.serve", return_value=False), \
                mock.patch.object(self.npc, "_classify_speech",
                                  return_value="directed"), \
                mock.patch("world.service.post_for", return_value=None):
            handled = self.npc._handle_directed_speech(
                "I'm Marcus", self.char1, {"addressed": True})
        self.assertFalse(handled)   # falls through to conversation

    def test_naming_never_eats_a_reply(self):
        with mock.patch("world.identity.parse_introduction",
                        side_effect=RuntimeError("boom")):
            self.npc._note_introduction("I'm Marcus", self.char1)   # no raise

    def test_a_lie_is_recorded_as_given(self):
        """Recognition memory is what the NPC BELIEVES. Someone giving a false
        name is the disguise layer working, not a bug to guard against."""
        with mock.patch.object(self.npc, "execute_cmd") as cmd, \
                mock.patch("world.identity.get_assigned_name",
                           return_value=None):
            self.npc._note_introduction("I'm Robert Paulson", self.char1)
        self.assertIn("as Robert Paulson", cmd.call_args.args[0])
