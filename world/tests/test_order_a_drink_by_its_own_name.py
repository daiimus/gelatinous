"""A drink whose name carries an apostrophe is orderable by that name (#3195).

`_keyword_in` guards against the inside-a-word false positive that made
"the blacksmith on Pessoa" buy a mug of black recyc (#2779). It did so
with `(?<![a-z0-9'])kw(?![a-z0-9'])` -- excluding the apostrophe on BOTH
sides.

The right-hand exclusion had a cost nobody measured. Live, the chain-hoist
bar in The Last Shift carries:

    name            : "pint of shift's end"
    order_keywords  : ('shift', 'pint', 'stout', 'dark', 'beer')

`shift` cannot match `shift's`, so "i'd like a shift's end please" resolved
to nothing. The drink was still buyable -- as "a pint" -- but not by its
own name.

The fix consumes an optional possessive before asserting the boundary, so
the guard this function exists for survives intact. That is what the
`wordy`, `o'clock` and `blacksmith` cases below are: controls. If a future
change to this regex loosens it into a plain substring test again, they
fail before the possessive cases do.
"""
from evennia.utils.test_resources import EvenniaTest

from world import bar as bar_mod

_keyword_in = getattr(bar_mod, "_keyword_in", None)

# The live board, copied verbatim from the running game.
SHIFTS_END = {
    "name": "pint of shift's end",
    "order_keywords": ("shift", "pint", "stout", "dark", "beer"),
}
BLACK_RECYC = {
    "name": "mug of black recyc",
    "order_keywords": ("black", "recyc"),
}
MENU = [SHIFTS_END, BLACK_RECYC]


class KeywordBoundaryTest(EvenniaTest):

    def test_helper_exists(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in is missing")

    # --- the defect ------------------------------------------------------

    def test_possessive_matches_the_bare_keyword(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertTrue(_keyword_in("shift", "i'd like a shift's end please"))

    def test_possessive_is_symmetric_for_any_keyword(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertTrue(_keyword_in("word", "the word's out"))

    def test_smart_apostrophe_behaves_the_same(self):
        # U+2019 worked already, by the accident of not being in the
        # excluded set. Pinned so the two forms cannot drift apart.
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertTrue(_keyword_in("shift", "i'd like a shift’s end"))

    # --- controls: the guard this function exists for --------------------

    def test_blacksmith_still_does_not_buy_black_recyc(self):
        # #2779, the reason the boundary exists at all.
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertFalse(_keyword_in("black", "the blacksmith on pessoa"))

    def test_keyword_still_does_not_match_inside_a_word(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertFalse(_keyword_in("word", "that was wordy"))

    def test_oclock_is_not_an_order(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertFalse(_keyword_in("o", "meet me at five o'clock"))

    def test_bare_plural_is_not_a_possessive(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertFalse(_keyword_in("shift", "two shifts tonight"))

    def test_plain_match_still_works(self):
        self.assertIsNotNone(_keyword_in, "world.bar._keyword_in missing")
        self.assertTrue(_keyword_in("black", "a mug of black recyc"))


class OrderByOwnNameTest(EvenniaTest):
    """Through the real matcher, not the helper -- where players touch it."""

    def test_the_live_board_resolves_its_own_drink_name(self):
        got = bar_mod.match_recipe("i'd like a shift's end please", MENU)
        self.assertIsNotNone(
            got, "'shift's end' resolved to nothing against the board that "
                 "carries it")
        self.assertEqual(got["name"], SHIFTS_END["name"])

    def test_asking_for_a_pint_still_works(self):
        # The workaround players had. It must not regress.
        got = bar_mod.match_recipe("pour me a pint", MENU)
        self.assertIsNotNone(got)
        self.assertEqual(got["name"], SHIFTS_END["name"])

    def test_blacksmith_remark_orders_nothing(self):
        # Control at the matcher level: the whole menu, not one keyword.
        self.assertIsNone(
            bar_mod.match_recipe("the blacksmith on pessoa", MENU))
