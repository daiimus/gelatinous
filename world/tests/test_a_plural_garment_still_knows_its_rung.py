"""`derive_rung` and `derive_presentation` share one token matcher
(#2657).

Two mistakes in the same module, pulling in opposite directions.

`derive_presentation` matched at the FRONT of a word, so "bra" claimed
brass knuckles and the brass-toed boots the module's own comment names
as the motivating case. That half was fixed in #2478.

`derive_rung` demanded a whole-token match against a table that lists
only singulars, so `"grey work coveralls"` — a live key on 17 objects —
derived nothing and fell to `DEFAULT_RUNG` 1, where a coverall competed
for layering with shirts and underwear instead of sitting over them.

One helper now answers for both, because a module with two matchers
that disagree about strictness is how you get one of each.
"""
from evennia.utils.test_resources import EvenniaTest

from world.style import derive_presentation, derive_rung


class TestPluralsDeriveTheSameRung(EvenniaTest):

    def test_the_singular_still_works(self):
        """Control: if the singular were broken, every plural
        assertion below would be measuring nothing."""
        self.assertEqual(derive_rung("coverall"), derive_rung("coverall"))
        self.assertIsNotNone(derive_rung("coverall"))

    def test_the_live_key(self):
        self.assertEqual(derive_rung("grey work coveralls"),
                         derive_rung("coverall"))

    def test_and_the_other_plurals(self):
        for singular, plural in (("coat", "coats"),
                                 ("jacket", "jackets"),
                                 ("apron", "aprons")):
            self.assertEqual(derive_rung(plural), derive_rung(singular),
                             f"{plural!r} did not derive {singular!r}'s rung")

    def test_a_word_the_table_does_not_know_still_derives_nothing(self):
        """Control: the looser matcher must not start answering for
        everything."""
        self.assertIsNone(derive_rung("dispatch headset"))
        self.assertIsNone(derive_rung("plate mail"))


class TestTheBraDoesNotComeBack(EvenniaTest):
    """The plural suffix sits INSIDE the trailing boundary, so relaxing
    the matcher must not reopen #2478."""

    def test_brass_is_not_a_bra(self):
        self.assertEqual(derive_presentation("brass-toed boots"), ())
        self.assertEqual(derive_presentation("brass knuckles"), ())

    def test_nor_is_a_brace(self):
        self.assertEqual(derive_presentation("a braced harness"), ())

    def test_nor_a_slipstream_jacket(self):
        self.assertEqual(derive_presentation("slipstream jacket"), ())

    def test_but_a_bra_still_is(self):
        """Control: the matcher still matches the word it is for."""
        self.assertEqual(derive_presentation("lace bra"), ("femme",))

    def test_and_so_are_bras(self):
        self.assertEqual(derive_presentation("two lace bras"), ("femme",))


class TestClosedCompoundsStillMiss(EvenniaTest):
    """Deliberate, and recorded so a later reader does not read it as an
    oversight: matching a table word at the END of a longer token is
    linguistically right for English compound heads, and it makes
    "zebra" a bra. A compound the tables should know belongs in the
    tables."""

    def test_a_trenchcoat_is_not_derived_from_coat(self):
        self.assertIsNone(derive_rung("trenchcoat"))

    def test_and_zebra_is_not_a_bra(self):
        self.assertEqual(derive_presentation("zebra print top"), ())
