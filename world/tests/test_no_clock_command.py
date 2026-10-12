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

from commands.default_cmdsets import (
    CharacterCmdSet,
    DeathCmdSet,
    UnconsciousCmdSet,
)
from world import help_entries


def _tokens_text(testcase):
    for entry in help_entries.HELP_ENTRY_DICTS:
        if entry.get("key") == "tokens":
            return entry["text"]
    testcase.fail("the 'tokens' help entry is gone")


def _keys(cmdset_class=CharacterCmdSet):
    cs = cmdset_class()
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
        return _tokens_text(self)

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


class TestNothingTellsYouTheHourWhileOutCold(TestCase):
    """#2819 removed `@time` from the awake set and left it in the
    lockout set, so a knocked-out character could still read the
    real-world clock (#2691). The lockout sets replace the awake set
    entirely, so each one has to honour the premise on its own.
    """

    def test_no_time_command_while_unconscious(self):
        keys = _keys(UnconsciousCmdSet)
        for name in ("time", "@time", "uptime", "@uptime"):
            self.assertNotIn(name, keys,
                             f"'{name}' is reachable while unconscious")

    def test_no_time_command_while_dead(self):
        keys = _keys(DeathCmdSet)
        for name in ("time", "@time", "uptime", "@uptime"):
            self.assertNotIn(name, keys, f"'{name}' is reachable while dead")

    def test_the_lockout_sets_keep_their_out_of_character_commands(self):
        for cmdset_class in (UnconsciousCmdSet, DeathCmdSet):
            keys = _keys(cmdset_class)
            for name in ("help", "who", "quit"):
                self.assertIn(name, keys, f"{cmdset_class.__name__} lost {name}")


def _human_body_nouns():
    from world.anatomy.species import (
        get_species_longdesc_flex_nouns,
        get_species_pair_keys,
    )
    nouns = set(get_species_longdesc_flex_nouns("human"))
    nouns |= {left.split("_", 1)[1]
              for left, _right in get_species_pair_keys("human").values()}
    return nouns


class TestTheHelpDescribesTheRendererWeHave(TestCase):
    """#2691. The pronoun section promised a second-person self-view
    ("you see -> ... your cheek") that no player-visible path renders:
    every production caller forces third person, as the longdesc spec
    requires. The number section listed seven nouns and called every
    other braced word a verb; the human vocabulary is 38 nouns. The
    worked example omitted the side the renderer adds to a lone pair
    part. `help describe` repeated two of the three.
    """

    def test_no_second_person_self_view_is_promised(self):
        text = _tokens_text(self)
        for phrase in ("your cheek", "you see", 'sees "you'):
            self.assertNotIn(phrase, text)
        self.assertIn("third-person", text)

    def test_the_one_present_example_names_the_side(self):
        self.assertIn("left eye accents", _tokens_text(self))

    def test_the_vocabulary_paragraph_lists_every_human_body_noun(self):
        import re
        text = _tokens_text(self)
        start = text.index("The recognised body nouns are")
        end = text.index("Other species carry")
        paragraph = text[start:end]
        missing = sorted(n for n in _human_body_nouns()
                         if not re.search(rf"\b{re.escape(n)}\b", paragraph))
        self.assertEqual(missing, [],
                         f"help tokens does not list these body nouns: {missing}")

    def test_help_describe_agrees(self):
        from commands.CmdCharacter import CmdDescribe
        doc = CmdDescribe.__doc__
        self.assertIn("left eye accents", doc)
        self.assertNotIn("the viewer", doc)


class TestTheRendererDoesWhatTheHelpNowSays(EvenniaCommandTest):
    """Asserted through `_render_body_longdesc`, the per-location path
    `look` takes (third person, side from the location, singular)."""

    def test_a_lone_pair_part_names_its_side(self):
        out = self.char1._render_body_longdesc(
            "left_eye", "{Their} bright brown {eyes} {accent} {their} skin.",
            self.char1)
        self.assertIn("left eye accents", out)
        self.assertNotIn("your", out.lower())

    def test_a_self_look_stays_third_person(self):
        out = self.char1._render_body_longdesc(
            "face", "A long scar runs down {their} cheek.", self.char1)
        self.assertNotIn("your", out)
        self.assertRegex(out, r"runs down (his|her|their) cheek")

    def test_every_listed_body_noun_is_treated_as_a_noun(self):
        """A verb would gain an -s in the singular ("asses"); a noun stays
        itself. `{ass}` failed this before #2691 because inflect
        singularized it to "as"."""
        wrong = {}
        for noun in sorted(_human_body_nouns()):
            out = self.char1._render_body_longdesc(
                "chest", "{" + noun + "}", self.char1)
            if out != noun:
                wrong[noun] = out
        self.assertEqual(wrong, {})

    def test_body_nouns_beyond_the_pairs_flex_as_nouns(self):
        out = self.char1._process_description_variables(
            "{Their} {shoulder} and {leg} and {scar} and {ass}.", self.char1,
            force_third_person=True, number="plural")
        self.assertIn("shoulders and legs and scars and asses", out)
