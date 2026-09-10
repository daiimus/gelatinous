"""`parse_introduction` stores a name, not a sentence (#2649).

`_clean_intro_name` took up to four words after an introduction lead and
stopped only at punctuation or the word "and". Prepositions were not
stops, so a normal self-introduction was stored verbatim as a name — and
a longer one was stored truncated mid-phrase by the four-word cap:

    'my name is Marcus from Southside'  ->  'Marcus from Southside'
    "I'm Kade Vance of the Ash"         ->  'Kade Vance of the'

The second is the worse of the two: a dangling "of the" is not a name
anybody typed or meant, and what this produces goes into recognition
memory as an `assigned_name` — the label an NPC will call you by from
then on.

Stopping at the connective is what the punctuation branch already did
for "call me Doc, the medic".

NOT solved by adding the connectives to `_NOT_A_NAME`, which rejects the
whole match: that would make an NPC learn NOTHING from "my name is
Marcus from Southside". A short right answer beats no answer.
"""
from evennia.utils.test_resources import EvenniaTest

from world.identity import parse_introduction


class TestTheReportedCases(EvenniaTest):

    def test_a_preposition_stops_the_name(self):
        self.assertEqual(
            parse_introduction("my name is Marcus from Southside"),
            "Marcus")

    def test_the_truncation_case(self):
        """Five words capped at four left 'Kade Vance of the'."""
        self.assertEqual(
            parse_introduction("I'm Kade Vance of the Ash"), "Kade Vance")

    def test_punctuation_still_stops_it(self):
        """Control: the branch that already worked."""
        self.assertEqual(parse_introduction("call me Doc, the medic"), "Doc")

    def test_and_still_stops_it(self):
        self.assertEqual(
            parse_introduction("my name is Marcus and I run cargo"),
            "Marcus")


class TestOrdinaryNamesSurvive(EvenniaTest):
    """Controls. A stop list that ate real names would be worse than the
    defect — an NPC that learns nothing is worse than one that learns a
    long name."""

    def test_a_bare_name(self):
        self.assertEqual(parse_introduction("I'm Wren"), "Wren")
        self.assertEqual(parse_introduction("name's Ossie"), "Ossie")

    def test_a_coined_name_keeps_its_article(self):
        """"They call me the Toe Guy" — the capital that tells a name
        from ordinary speech sits on the word AFTER the article."""
        self.assertEqual(parse_introduction("they call me the Rook"),
                         "the Rook")

    def test_a_full_name_with_a_title(self):
        self.assertEqual(
            parse_introduction("I am Doctor Nikolai Kasparov"),
            "Doctor Nikolai Kasparov")

    def test_a_stop_word_inside_a_name_is_not_a_stop(self):
        """`\\b` matters: "Ofelia" starts with "of" and must survive."""
        self.assertEqual(parse_introduction("I'm Ofelia"), "Ofelia")
        self.assertEqual(parse_introduction("I'm Instance Green"),
                         "Instance Green")

    def test_something_that_is_not_an_introduction_is_still_nothing(self):
        self.assertIsNone(parse_introduction("what's the time"))
        self.assertIsNone(parse_introduction(""))


class TestEveryConnectiveStops(EvenniaTest):

    def test_the_common_ones(self):
        for line, want in (
                ("call me Tobias working the yard", "Tobias"),
                ("I'm Sunny at the pawn counter", "Sunny"),
                ("my name is Pia with the snails", "Pia"),
                ("I'm Marek who runs the stall", "Marek"),
                ("call me Halina since you asked", "Halina")):
            self.assertEqual(parse_introduction(line), want, line)
