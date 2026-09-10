"""Only somebody who could have sailed holds a slowboat berth (#2670).

Build 100 backfilled the manifest and spelled its exclusion
`startswith("synth")` — inside the build script, the only place the rule
existed. A security robot walked straight through a filter written to
keep non-people off it:

    #3258 'a chrome-trimmed security robot'
      species:     'robot'
      designation: {'vessel': 'SBL-0117', 'dept': 'logistics',
                    'rank': 'specialist'}

A berth on the crossing is a thing only a person can have held, and it
rendered on `@soul` and on the character's own record.

The intent was never ambiguous: a synthetic is excluded precisely
because it did not travel as crew, and a robot is the clearer case of
the same rule. What was wrong is that the rule lived in a script rather
than in the module the manifest belongs to, so nothing else could
inherit it and nothing could test it.
"""
from types import SimpleNamespace

from evennia.utils.test_resources import EvenniaTest

from world import manifest as manifest_mod

travelled_as_crew = getattr(manifest_mod, "travelled_as_crew", None)


def _soul(species):
    return SimpleNamespace(db=SimpleNamespace(species=species))


class TestTheRuleExistsWhereItCanBeReused(EvenniaTest):

    def test_the_module_owns_it(self):
        """It lived in one build script, which is why it drifted."""
        self.assertIsNotNone(
            travelled_as_crew,
            "the manifest rule is still only in a build script")

    def test_the_excluded_species_are_named(self):
        self.assertIn("robot",
                      getattr(manifest_mod, "NEVER_ON_THE_MANIFEST", ()))


class TestWhoSailed(EvenniaTest):

    def setUp(self):
        super().setUp()
        if travelled_as_crew is None:
            self.skipTest("no rule in this tree")

    def test_an_unset_species_is_a_person(self):
        """Most of the colony carries no species attribute at all;
        defaulting those out would empty the manifest rather than clean
        it."""
        self.assertTrue(travelled_as_crew(_soul(None)))
        self.assertTrue(travelled_as_crew(_soul("")))

    def test_a_human_sailed(self):
        self.assertTrue(travelled_as_crew(_soul("human")))

    def test_a_robot_did_not(self):
        self.assertFalse(travelled_as_crew(_soul("robot")))

    def test_nor_did_a_synthetic(self):
        """The case the original rule DID cover — it must survive."""
        self.assertFalse(travelled_as_crew(_soul("synth")))
        self.assertFalse(travelled_as_crew(_soul("synthetic_humanoid")))

    def test_nor_a_rat(self):
        self.assertFalse(travelled_as_crew(_soul("rat")))

    def test_the_case_of_the_species_does_not_matter(self):
        self.assertFalse(travelled_as_crew(_soul("Robot")))
        self.assertFalse(travelled_as_crew(_soul("SYNTH")))


class TestTheBuildScriptAsksRatherThanRederives(EvenniaTest):
    """A second copy of the predicate is how the first one drifted."""

    def test_it_calls_the_module(self):
        """Comment lines are stripped first: the fix's own comment
        quotes the predicate it replaced, and counting that would make
        this test fail for describing itself."""
        with open("scripts/builds/100_the_manifest.py") as handle:
            code = "\n".join(line for line in handle.read().splitlines()
                             if not line.lstrip().startswith("#"))
        self.assertIn("travelled_as_crew", code)
        self.assertNotIn('startswith("synth")', code)
