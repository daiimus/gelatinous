"""Typing "the" does not rent you a cube (#2674).

`unit_matches` compared the requested name against every whitespace
token of the cube's FULL key, so the building's own words claimed every
one of its units:

    'the'       matched 134 of 134 Brackett units
    'halcyon'   matched  35 of  35 Halcyon cabins
    'cabin'     matched  35 of  35
    '-'         matched  35 of  35

`assign_cube` then handed the caller an arbitrary one — and a cube
assignment carries a 48-hour relocation, so a stray word moved somebody
into a room they never asked for.

A DESIGNATOR CARRIES A NUMBER. Checked against all 229 live cubes: every
unit label contains a digit, and none of "the", "halcyon", "brackett",
"arms", "cabin" or "unit" does. Cheaper and more honest than a stop-word
list, which would need extending for every building ever named.

The issue's other half — that the Halcyon board printed "Cabin 3B" and
its own parser rejected it — shipped under #2457, which gave the printer
and the parser one shared `unit_label`. A test below pins that they
still agree, since this change touches the parser side of that pair.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.rental import unit_label, unit_matches

#: The three live key shapes.
KEYS = ("The Brackett Arms - Unit 3B",
        "The Halcyon - Cabin 1B",
        "R0-01")


class _Cubes(EvenniaTest):
    def cube(self, key):
        return create_object("typeclasses.rooms.Room", key=key,
                             location=None)


class TestABuildingWordClaimsNothing(_Cubes):

    def test_articles_and_building_words(self):
        for key in KEYS:
            cube = self.cube(key)
            for want in ("the", "brackett", "arms", "unit", "halcyon",
                         "cabin", "-", "a", "room"):
                self.assertFalse(
                    unit_matches(cube, want),
                    f"{want!r} claimed {key!r}")

    def test_an_empty_request_claims_nothing(self):
        cube = self.cube(KEYS[0])
        self.assertFalse(unit_matches(cube, ""))
        self.assertFalse(unit_matches(cube, None))
        self.assertFalse(unit_matches(cube, "   "))


class TestARealNameStillWorks(_Cubes):
    """Controls. A matcher that stopped resolving units would be worse
    than one that over-resolves — nobody could rent at all."""

    def test_the_bare_designator(self):
        for key, want in (("The Brackett Arms - Unit 3B", "3b"),
                          ("The Halcyon - Cabin 1B", "1b"),
                          ("R0-01", "r0-01")):
            self.assertTrue(unit_matches(self.cube(key), want), key)

    def test_the_label_a_board_prints(self):
        """The printer and the parser share `unit_label` (#2457) and
        must keep agreeing — this change touches the parser side."""
        for key in KEYS:
            cube = self.cube(key)
            self.assertTrue(unit_matches(cube, unit_label(cube)), key)
            self.assertTrue(unit_matches(cube, unit_label(cube).lower()),
                            key)

    def test_the_full_tail(self):
        """"a player can always type back what they were just shown"."""
        for key in KEYS:
            cube = self.cube(key)
            tail = key.split(" - ")[-1]
            self.assertTrue(unit_matches(cube, tail), key)
            self.assertTrue(unit_matches(cube, tail.lower()), key)

    def test_a_designator_does_not_claim_its_neighbour(self):
        a = self.cube("The Halcyon - Cabin 1B")
        b = self.cube("The Halcyon - Cabin 2B")
        self.assertTrue(unit_matches(a, "1b"))
        self.assertFalse(unit_matches(b, "1b"))
