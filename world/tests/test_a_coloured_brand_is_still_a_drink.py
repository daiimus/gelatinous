"""A brand may carry colour; the drink is still called what it's called.

Regression pin for #2605.  A recipe name is free text typed by a
bartender at the branding prompt, and nothing strips colour codes from
it.  Two things then read the raw string as if it were plain:

* `_recipe_keywords` split it into order keywords, so `|rBloodwork|n`
  produced the keyword `|rbloodwork|n` and `order a bloodwork` matched
  NOTHING.  The drink sat on the menu, unorderable by its own name.
* `CmdBarMenu` padded with `len(label)` under a comment asserting
  "Labels are plain (no colour codes), so visible length == len()",
  so one `|r` shifted every other row's price column.

The issue reported the second, as latent and cosmetic.  Measuring it
turned up the first, which is neither cosmetic nor obvious -- a
bartender brands a pour, it renders beautifully, and no customer can
order it.

Colour stays in the NAME.  It is the bartender's branding and it
renders; it just isn't part of what the drink is called, and it isn't
part of how wide the name is.

Latent when fixed: 27 recipes live in the world, none carrying a colour
code, so nothing needed migrating.
"""

from __future__ import annotations

from unittest import TestCase

from evennia.utils.ansi import strip_ansi

from commands.bar_menu import _recipe_keywords
from world.bar import match_recipe
from world.grammar import capitalize_first

PLAIN = "Bloodwork"
COLOURED = "|rBloodwork|n"
PARTLY = "the |512Last|n Word"


def _recipe(name):
    return {"name": name, "order_keywords": _recipe_keywords(name),
            "price": 0}


class TestAColouredBrandIsStillADrink(TestCase):

    # -- the defect the measurement turned up ------------------------

    def test_a_coloured_brand_is_orderable_by_its_name(self):
        hit = match_recipe("a bloodwork please", [_recipe(COLOURED)])
        self.assertIsNotNone(
            hit,
            "a drink branded with colour could not be ordered by its "
            "own name — the markup became part of the keyword",
        )

    def test_keywords_carry_no_markup(self):
        for name in (COLOURED, PARTLY):
            with self.subTest(name):
                for kw in _recipe_keywords(name):
                    self.assertNotIn("|", kw)

    def test_a_partly_coloured_name_matches_on_the_coloured_word(self):
        """`the |512Last|n Word` must be orderable as "last word".

        It already matched on "word" alone, by accident — the uncoloured
        half. That is not the same as working.
        """
        hit = match_recipe("pour me a last word", [_recipe(PARTLY)])
        self.assertIsNotNone(hit)
        self.assertIn("last", _recipe_keywords(PARTLY))

    def test_a_coloured_brand_is_not_confused_with_a_plainer_one(self):
        """The worst symptom, and only visible on a realistic board.

        With `Bloodwork` (12) and `|rBloodwork Red|n` (15) both on the
        menu, "a bloodwork red please" matched the PLAIN one: the
        coloured keyword could not match, and the shorter plain name
        could. The customer asked for one drink, was served another,
        and was charged the other price.

        Measured on a single-recipe list this reads as a harmless
        no-match. It is a mis-serve.
        """
        board = [_recipe(PLAIN), _recipe("|rBloodwork Red|n")]
        hit = match_recipe("a bloodwork red please", board)
        self.assertIsNotNone(hit)
        self.assertEqual(
            hit["name"], "|rBloodwork Red|n",
            "the coloured brand lost its own order to a plainer "
            "drink on the same board",
        )

    # -- the defect as filed -----------------------------------------

    def test_the_price_column_is_measured_on_visible_length(self):
        labels = [capitalize_first(n) for n in (PLAIN, COLOURED, PARTLY)]
        width = max(len(strip_ansi(l)) for l in labels)
        rendered = [l + " " * max(0, width - len(strip_ansi(l)))
                    for l in labels]
        visible = {len(strip_ansi(r)) for r in rendered}
        self.assertEqual(
            len(visible), 1,
            f"rows do not line up for a viewer: widths {visible}",
        )

    # -- controls ----------------------------------------------------

    def test_a_plain_name_is_unchanged(self):
        self.assertEqual(_recipe_keywords(PLAIN), ("bloodwork",))
        self.assertIsNotNone(
            match_recipe("a bloodwork please", [_recipe(PLAIN)]))

    def test_short_words_are_still_dropped(self):
        """The >2 rule is the existing contract and must survive."""
        self.assertEqual(_recipe_keywords("a |rgin|n on ice"),
                         ("gin", "ice"))

    def test_a_name_that_is_only_colour_yields_no_keywords(self):
        """Degenerate input must not crash or invent a keyword."""
        self.assertEqual(_recipe_keywords("|r|n"), ())

    def test_an_unrelated_order_still_does_not_match(self):
        """The negative control: stripping markup must not widen
        matching into things the player did not ask for."""
        self.assertIsNone(
            match_recipe("i'm trying to stay sober", [_recipe(COLOURED)]))
