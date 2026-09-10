"""`_render_cuts` is grammatical at every count (#2688).

The butcher's emote is room-visible — everyone present reads it — and
it was ungrammatical on the ordinary path:

    '2 rat tail'
    'a rat tail, and a rat chops'
    '2 rat tail, a rat chops, and a rat haunch'

Three separate faults. Two were fixed under #2814: the missing
pluralisation, and the serial comma on a two-item list. The third
survived — `with_article` reaches for an article on any name it does
not recognise as pluralia tantum, and "chops" is not one, because a
chop IS a thing. Only THIS product's name happens to be plural.

The count > 1 branch was already right: `pluralize_noun("rat chops")`
returns "rat chops", because inflect knows it is a plural already.
"""
from evennia.utils.test_resources import EvenniaTest

from world.butchery import RAT_PRODUCTS, _render_cuts


class TestEveryProductRendersAtEveryCount(EvenniaTest):

    def test_the_table_is_populated(self):
        """Control: an empty table renders 'nothing worth wrapping' for
        everything, and the assertions below would be vacuous."""
        self.assertGreaterEqual(len(RAT_PRODUCTS), 5)

    def test_no_singular_takes_a_wrong_article(self):
        """Sweeps the whole table rather than naming chops, so a new
        plural-named product is caught when it is added."""
        for key, entry in RAT_PRODUCTS.items():
            rendered = _render_cuts([(key, 1)])
            name = entry["name"]
            if entry.get("plural"):
                self.assertEqual(rendered, name,
                                 f"{key}: an article on a plural name")
            elif entry.get("unit"):
                self.assertIn(entry["unit"], rendered, key)
            else:
                self.assertTrue(rendered.startswith(("a ", "an ")),
                                f"{key}: {rendered!r} has no article")

    def test_no_plural_is_left_singular(self):
        for key, entry in RAT_PRODUCTS.items():
            rendered = _render_cuts([(key, 3)])
            self.assertTrue(rendered.startswith("3 "), f"{key}: {rendered!r}")
            if not entry.get("unit") and not entry.get("plural"):
                self.assertNotEqual(
                    rendered, f"3 {entry['name']}",
                    f"{key}: {rendered!r} was not pluralised")


class TestTheReportedLines(EvenniaTest):
    """The exact strings in the issue."""

    def test_two_tails(self):
        self.assertEqual(_render_cuts([("rat_tail", 2)]), "2 rat tails")

    def test_one_chops(self):
        self.assertEqual(_render_cuts([("rat_chops", 1)]), "rat chops")

    def test_a_two_item_list_has_no_serial_comma(self):
        self.assertEqual(
            _render_cuts([("rat_tail", 1), ("rat_chops", 1)]),
            "a rat tail and rat chops")

    def test_a_three_item_list_does(self):
        self.assertEqual(
            _render_cuts([("rat_tail", 2), ("rat_chops", 1),
                          ("rat_haunch", 1)]),
            "2 rat tails, rat chops, and a rat haunch")

    def test_a_mass_noun_takes_a_portion(self):
        self.assertEqual(_render_cuts([("rat_offal", 3)]),
                         "3 twists of rat offal")

    def test_nothing_still_reads(self):
        self.assertEqual(_render_cuts([]), "nothing worth wrapping")
