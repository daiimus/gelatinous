"""A registered species with no prose gets silence, not human flesh
(#2725).

`get_severed_part_description` fell back to the human table whenever a
species had no bank of its own. `SEVERED_PART_DESCRIPTIONS` covers human
and rat; `SPECIES_DEFINITIONS` registers four. So:

    robot               'A severed human head, ... weeping a thin rim
                         of blood...'
    synthetic_humanoid  'A severed human head, ... weeping a thin rim
                         of blood...'

A severed robot head described itself as a human head weeping blood.

Silence is the lesser wrong, and it is the contract the function already
documents: *"Callers should treat empty as 'no default desc available,
fall back to whatever Evennia does next' rather than asserting."* A
missing sentence is a gap; a robot bleeding is a claim about the world
that is false, and players act on prose. The severable limb containers
already return "" for every species including human, so an empty answer
here is an established shape rather than a new one.

THE HUMAN FALLBACK IS KEPT for a genuinely unknown species -- a body of
unknown make is most likely flesh, and there is nothing better to say.
The distinction is between "this species was registered and nobody wrote
its prose yet" (a content gap, say nothing) and "we have never heard of
this" (guess flesh).

Writing the robot and synthetic banks is authoring work and is left to
whoever owns that voice; this only stops the wrong sentence being
asserted in the meantime.
"""
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import get_severed_part_description
from world.anatomy.species import SPECIES_DEFINITIONS


class TestSpeciesProseIsNotBorrowed(EvenniaTest):

    def test_human_still_has_its_prose(self):
        """Control: the species WITH a bank must still answer."""
        got = get_severed_part_description("human", "head", "pristine")
        self.assertTrue(got)
        self.assertIn("human", got.lower())

    def test_rat_still_has_its_own(self):
        """Control: and the second bank is still distinct."""
        got = get_severed_part_description("rat", "head", "pristine")
        self.assertTrue(got)
        self.assertNotEqual(
            got, get_severed_part_description("human", "head", "pristine"))

    def test_a_robot_head_does_not_weep_blood(self):
        got = get_severed_part_description("robot", "head", "pristine")
        self.assertNotIn("blood", got.lower())
        self.assertNotIn("human", got.lower())

    def test_a_synthetic_head_does_not_either(self):
        got = get_severed_part_description(
            "synthetic_humanoid", "head", "pristine")
        self.assertNotIn("blood", got.lower())
        self.assertNotIn("human", got.lower())

    def test_an_unknown_species_still_guesses_flesh(self):
        """Kept deliberately: nothing better is available, and a body of
        unknown make is most likely flesh."""
        got = get_severed_part_description("kroolian", "head", "pristine")
        self.assertEqual(
            got, get_severed_part_description("human", "head", "pristine"))

    def test_the_two_cases_are_actually_different(self):
        """Control on the distinction itself: a registered species and an
        unknown one must not take the same branch."""
        self.assertIn("robot", SPECIES_DEFINITIONS)
        self.assertNotIn("kroolian", SPECIES_DEFINITIONS)
