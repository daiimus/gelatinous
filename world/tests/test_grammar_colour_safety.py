"""The grammar engine handles coloured text (#2207).

Almost everything this module is handed has already been coloured —
item keys, sdescs, longdescs, combat lines. Markup is not text, so any
rule that looks at "the first character" or "does this start with a
vowel" has to see past it.

Found by asking which functions the game actually leans on, rather
than which ones a bug happened to surface:

    capitalize_first          84 callers   <- was corrupting colour
    with_article              37 callers   <- was blind to it
    get_article                7 callers   <- ditto
    conjugate_third_person     5 callers   <- the one I had been fixing
    flex_verb                  5 callers

The two most-used functions had never been examined.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.grammar import (
    _visible,
    capitalize_first,
    get_article,
    pluralize_noun,
    with_article,
)


class TestCapitaliseSeesPastColour(EvenniaCommandTest):
    def test_it_capitalises_the_word_not_the_colour_code(self):
        self.assertEqual(capitalize_first("|rblood|n"), "|rBlood|n")
        self.assertEqual(capitalize_first("|whello"), "|wHello")
        self.assertEqual(capitalize_first("|=lblack boots"),
                         "|=lBlack boots")
        self.assertEqual(capitalize_first("|555a console|n"),
                         "|555A console|n")

    def test_it_never_alters_the_markup(self):
        """|r is red and |R is bright red — changing the case of a
        colour code changes the colour."""
        for text in ("|rblood", "|whello", "|=lblack", "|[rmarked",
                     "|555thing", "|n"):
            before = text.replace("|", "\x00")     # markup fingerprint
            after = capitalize_first(text).replace("|", "\x00")
            self.assertEqual(
                [c for c in before if c == "\x00"],
                [c for c in after if c == "\x00"],
                f"markup count changed on {text!r}")
        self.assertEqual(capitalize_first("|n"), "|n")
        self.assertEqual(capitalize_first("|555"), "|555")

    def test_plain_text_is_unaffected(self):
        self.assertEqual(capitalize_first("the Rook"), "The Rook")
        self.assertEqual(capitalize_first('"get down!" he shouts'),
                         '"Get down!" he shouts')
        self.assertEqual(capitalize_first(""), "")


class TestHexTruecolourIsMarkupToo(EvenniaCommandTest):
    """`|#rrggbb` is colour, not letters (#2805).

    `_ANSI_TOKEN` is deliberately a LOCAL pattern rather than Evennia's,
    so this module keeps no Evennia dependency in its core functions.
    The cost is that it cannot track upstream: Evennia 6.1 renders
    `|#ff0000` and `|[#00ff00` as truecolour, and the local pattern
    matched neither — so `_visible()` counted eight characters of markup
    as text a reader sees, and every grammar decision built on it
    (article choice, capitalisation, width) worked from punctuation.

    No live content uses hex markup yet. This pins it so the next form
    Evennia adds fails here rather than silently mis-measuring prose.
    """

    def test_hex_foreground_is_not_visible_text(self):
        self.assertEqual(_visible("|#ff0000red"), "red")

    def test_hex_background_is_not_visible_text(self):
        self.assertEqual(_visible("|[#00ff00green"), "green")

    def test_the_older_forms_still_strip(self):
        self.assertEqual(_visible("|rbasic|n"), "basic")
        self.assertEqual(_visible("|500xterm|n"), "xterm")
        self.assertEqual(_visible("|=lgrey|n"), "grey")
        self.assertEqual(_visible("||literal"), "literal")

    def test_capitalise_sees_past_a_hex_code(self):
        self.assertEqual(capitalize_first("|#ff0000blood"), "|#ff0000Blood")


class TestArticlesSeePastColour(EvenniaCommandTest):
    def test_a_coloured_vowel_noun_still_takes_an(self):
        for noun in ("|555interior", "|rinterior|n", "|555elevator",
                     "|rapple"):
            self.assertEqual(get_article(noun), "an", noun)

    def test_with_article_keeps_the_colour_and_agrees(self):
        self.assertEqual(with_article("|555interior|n"),
                         "an |555interior|n")
        self.assertEqual(with_article("|rapple|n"), "an |rapple|n")

    def test_consonants_still_take_a(self):
        self.assertEqual(get_article("|555collar"), "a")
        self.assertEqual(with_article("|rknife"), "a |rknife")

    def test_a_coloured_phrase_that_already_has_an_article_keeps_it(self):
        self.assertEqual(with_article("|555a bowl of kuro-nikomi|n"),
                         "|555a bowl of kuro-nikomi|n")


class TestPluraliseIsIdempotent(EvenniaCommandTest):
    def test_already_plural_nouns_are_left_alone(self):
        for word in ("boots", "glasses", "gloves", "shoes", "trousers",
                     "scissors", "hands", "feet"):
            self.assertEqual(pluralize_noun(word), word, word)

    def test_singulars_still_pluralise(self):
        self.assertEqual(pluralize_noun("hand"), "hands")
        self.assertEqual(pluralize_noun("foot"), "feet")
        self.assertEqual(pluralize_noun("knife"), "knives")

    def test_capitalisation_is_preserved(self):
        self.assertEqual(pluralize_noun("Hand"), "Hands")
