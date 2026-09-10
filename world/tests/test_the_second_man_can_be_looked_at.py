"""`look the 2nd man` finds the second man (#2661).

The ordinal was parsed BEFORE the leading article was stripped, and in
that order the first step cancels the second: `parse_ordinal("the 2nd
man")` sees no leading ordinal and returns the string untouched, so the
strip yields `"2nd man"` — matched against sdescs as a description,
which no character has. `identity_match_characters` returned `[]`,
`Character.search` fell through to the default Evennia search, and the
player got a generic not-found for someone standing in front of them.

Both steps existed and both worked. Only the order was wrong, and the
function's own docstring advertised both behaviours as working:
individually true, and in that order mutually exclusive.

Writing "the" before a disambiguator is the natural phrasing, which
makes this the form players reach for in exactly the situation ordinals
exist to resolve.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import search as search_mod
from world.search import identity_match_characters, parse_ordinal

#: Read off the module so this file still LOADS against the unfixed
#: tree — importing a name that does not exist yet is an error, not a
#: control, and an error stops the test before it can assert anything.
parse_target_query = getattr(
    search_mod, "parse_target_query",
    lambda q: parse_ordinal(search_mod.strip_leading_article(q)))


class TestTheArticleComesOffFirst(EvenniaTest):
    """NOTE: the fallback above implements the fix, so these four pass
    against the unfixed tree as well. They document the contract; the
    CLAIM is carried by `TestTheSecondManIsFound`, which drives the
    matcher and does fail there, and by the one structural assertion
    below."""

    def test_the_two_steps_live_in_one_place(self):
        """They were split across two call sites that had to agree on
        the order and did not. One function is the fix."""
        self.assertTrue(
            hasattr(search_mod, "parse_target_query"),
            "the article strip and the ordinal parse are still two "
            "separate steps at each call site, free to drift apart")

    def test_a_bare_ordinal_still_parses(self):
        """Control: the form that always worked must keep working, or
        a green suite below would mean the parser was simply broken in
        a new direction."""
        self.assertEqual(parse_target_query("2nd man"), (2, "man"))
        self.assertEqual(parse_target_query("second man"), (2, "man"))
        self.assertEqual(parse_target_query("1.man"), (1, "man"))

    def test_an_article_prefixed_ordinal_parses(self):
        self.assertEqual(parse_target_query("the 2nd man"), (2, "man"))
        self.assertEqual(parse_target_query("a 3rd woman"), (3, "woman"))
        self.assertEqual(parse_target_query("the second man"), (2, "man"))

    def test_an_article_with_no_ordinal_still_strips(self):
        self.assertEqual(parse_target_query("the tall man"),
                         (None, "tall man"))

    def test_no_article_no_ordinal_is_untouched(self):
        self.assertEqual(parse_target_query("tall man"), (None, "tall man"))


class TestTheSecondManIsFound(EvenniaTest):
    """The player-visible half: the matcher, not just the parser.

    Two characters who look alike, which is the only situation an
    ordinal is for.
    """

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.a = self.char2
        self.a.location = self.room1
        self.b = create_object("typeclasses.characters.Character",
                               key="Bee", location=self.room1)
        for who in (self.a, self.b):
            who.height = "average"
            who.build = "stocky"          # both read "stocky person"

    def match(self, query):
        return identity_match_characters(self.char1, query, [self.a, self.b])

    def test_they_look_alike(self):
        """Control: if the two had different sdescs the ordinal would
        be doing nothing and every assertion below would be hollow."""
        self.assertEqual(self.a.get_sdesc(), self.b.get_sdesc())
        self.assertEqual(self.match("person"), [self.a, self.b])

    def test_a_bare_ordinal_picks_the_second(self):
        """Control: the form that always worked."""
        self.assertEqual(self.match("2nd person"), [self.b])
        self.assertEqual(self.match("second person"), [self.b])

    def test_the_article_form_picks_the_second_too(self):
        self.assertEqual(
            self.match("the 2nd person"), [self.b],
            "an article in front of the ordinal emptied the match set")
        self.assertEqual(self.match("the second person"), [self.b])
        self.assertEqual(self.match("a 2nd person"), [self.b])

    def test_the_evennia_native_form_takes_an_article_as_well(self):
        self.assertEqual(self.match("the 2.person"), [self.b])
