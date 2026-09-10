"""A drink can be ordered by its own name (#2684).

`match_recipe` scanned the board in order and returned on the FIRST hit,
so a drink whose name contains another drink's name could never be
ordered by its own name. Measured live on both boards that carry it:

    menu: Negroni, Martini, Margarita, Old Fashioned, Daiquiri,
          Espresso Martini

    order 'espresso martini'  ->  Martini
    order 'martini'           ->  Martini
    order 'espresso'          ->  Espresso Martini

"Martini" is listed first, "martini" is a whole phrase inside "espresso
martini", and the shorter entry claimed the longer request. A patron
typed the name printed on the board, was served something else, and was
charged for it. Every door onto the board shares this resolver — a
spoken order, a whispered one, and the keeper's own `prepare` all failed
identically.
"""
from evennia.utils.test_resources import EvenniaTest

from world.bar import match_recipe

#: The live board, in its live order and with its live keywords.
#:
#: The keywords matter and a simplified fixture hid the real shape: on
#: the board, Espresso Martini is keyed ["espresso", "martini"] — two
#: single words, not one phrase. A fixture that keyed each drink by its
#: full name passed a longest-single-keyword rule that would still have
#: served a plain Martini to anyone ordering a Dry Martini.
BOARD = [
    {"name": "Negroni", "order_keywords": ["negroni"]},
    {"name": "Martini", "order_keywords": ["martini"]},
    {"name": "Margarita", "order_keywords": ["margarita"]},
    {"name": "Old Fashioned", "order_keywords": ["old", "fashioned"]},
    {"name": "Daiquiri", "order_keywords": ["daiquiri"]},
    {"name": "Espresso Martini", "order_keywords": ["espresso", "martini"]},
]


class TestTheLongerNameWins(EvenniaTest):

    def test_the_board_actually_collides(self):
        """Control: if the two entries did not share a keyword, every
        assertion below would pass on any resolver at all."""
        keys = [set(r["order_keywords"]) for r in BOARD]
        shared = [a & b for i, a in enumerate(keys)
                  for b in keys[i + 1:] if a & b]
        self.assertTrue(shared, "no two drinks on this board collide")

    def test_the_full_name_gets_the_right_drink(self):
        self.assertEqual(match_recipe("espresso martini", BOARD)["name"],
                         "Espresso Martini")

    def test_the_shorter_name_still_gets_the_shorter_drink(self):
        """The half that must not break: fixing this by preferring the
        longest name on the BOARD rather than the longest MATCH would
        serve an Espresso Martini to anyone asking for a Martini."""
        self.assertEqual(match_recipe("martini", BOARD)["name"], "Martini")

    def test_a_partial_name_still_reaches_it(self):
        self.assertEqual(match_recipe("espresso", BOARD)["name"],
                         "Espresso Martini")

    def test_a_polite_order_still_resolves(self):
        self.assertEqual(
            match_recipe("an old fashioned, when you get a moment",
                         BOARD)["name"], "Old Fashioned")

    def test_and_a_full_name_inside_a_sentence(self):
        self.assertEqual(
            match_recipe("could I get an espresso martini please",
                         BOARD)["name"], "Espresso Martini")


class TestTheOrdinaryCasesAreUntouched(EvenniaTest):
    """Controls. The scan answers every other order exactly as before."""

    def test_each_drink_by_its_own_name(self):
        for recipe in BOARD:
            self.assertEqual(
                match_recipe(recipe["name"].lower(), BOARD)["name"],
                recipe["name"])

    def test_nothing_on_the_board_is_nothing(self):
        self.assertIsNone(match_recipe("a glass of paint thinner", BOARD))

    def test_an_empty_order_is_nothing(self):
        self.assertIsNone(match_recipe("", BOARD))
        self.assertIsNone(match_recipe("martini", []))

    def test_a_word_boundary_is_still_required(self):
        """#2779's fix must survive: 'the blacksmith on Pessoa' does not
        buy a mug of black recyc."""
        board = [{"name": "black recyc", "order_keywords": ["black"]}]
        self.assertIsNone(match_recipe("the blacksmith on Pessoa", board))

    def test_a_tie_keeps_menu_order(self):
        board = [{"name": "Rye", "order_keywords": ["rye"]},
                 {"name": "Gin", "order_keywords": ["rye"]}]
        self.assertEqual(match_recipe("rye", board)["name"], "Rye")

    def test_counting_keywords_beats_measuring_one(self):
        """The case a longest-single-keyword rule still gets wrong, and
        the reason this scores on HOW MANY keywords matched first.

        On the live board it would have picked Espresso Martini out of
        "espresso martini" only because "espresso" (8) is longer than
        "martini" (7) — right answer, wrong reason. Add a drink whose
        distinguishing word is SHORTER and the luck runs out."""
        board = BOARD + [{"name": "Dry Martini",
                          "order_keywords": ["dry", "martini"]}]
        self.assertEqual(match_recipe("dry martini", board)["name"],
                         "Dry Martini")
        self.assertEqual(match_recipe("martini", board)["name"], "Martini")
