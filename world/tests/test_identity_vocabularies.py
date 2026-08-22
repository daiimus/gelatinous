"""Everyone rolls from the same vocabularies (#2174).

The soul spawner carried hand-written subsets of the identity axes —
four builds of six, three heights of five, and a skintone tuple
containing "dark", which the palette has never known. An unknown
skintone does not raise; `SKINTONE_PALETTE.get()` returns None and the
body simply renders with no colour, so a quarter of arrivals were
quietly plainer than everyone else.

These pin the invariants that make that class of drift loud.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.combat.constants import SKINTONE_PALETTE, VALID_SKINTONES
from world.director.civilians import HUMAN_SKINTONES
from world.identity import BUILDS, HEIGHTS


class TestSkintonesResolve(EvenniaCommandTest):
    def test_every_rollable_human_tone_is_in_the_palette(self):
        for tone in HUMAN_SKINTONES:
            self.assertIn(tone, SKINTONE_PALETTE,
                          f"{tone!r} is rollable but has no colour")
            self.assertIn(tone, VALID_SKINTONES)

    def test_dark_is_still_not_a_skintone(self):
        """The specific value that was being assigned. If somebody adds
        it later this test should be deleted, not worked around."""
        self.assertNotIn("dark", VALID_SKINTONES)


class TestSpawnersUseTheFullRange(EvenniaCommandTest):
    """Every population draws from the same lists, so no group is
    quietly barred from a body type."""

    def _source(self):
        import inspect

        from world.souls import population
        return inspect.getsource(population.generate_resident)

    def test_souls_roll_the_canonical_builds(self):
        src = self._source()
        self.assertIn("choice(BUILDS)", src)
        self.assertIn("choice(HEIGHTS)", src)
        self.assertIn("choice(HUMAN_SKINTONES)", src)

    def test_souls_do_not_hand_roll_an_identity_subset(self):
        src = self._source()
        for literal in ('"slight", "lean", "average", "stocky"',
                        '"short", "average", "tall"',
                        '"pale", "tan", "olive", "dark"'):
            self.assertNotIn(literal, src)

    def test_the_axes_are_non_empty(self):
        self.assertTrue(BUILDS)
        self.assertTrue(HEIGHTS)
        self.assertTrue(HUMAN_SKINTONES)
