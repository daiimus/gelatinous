"""Skintone belongs to the species; worn pronouns belong to the wearer (#2396).

`@skintone` validated against the WHOLE palette, so a human could be
`chrome` and a bioroid `tan`. The synthetic spectrum exists to read as "not
quite human" beside the realistic range, and an unguarded palette dissolves
the distinction it was built to make.

The gate is ASYMMETRIC, and the live cast is why: Tomas is `fair`, Cynthia
`olive`, Angela `golden` — synths built to pass — while Ossie is `pewter`
and the Rook `alabaster`. Restricting synthetics to the metallic end would
have invalidated eight existing NPCs. A human cannot be chrome; a synthetic
can be anything, because it was manufactured.

The second half covers worn descriptions. They run through the same token
processor as longdescs, so `{their}` renders his/her/its and a LITERAL
"their" renders "their" on everybody regardless of gender.
"""
from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.combat.constants import (ORGANIC_SKINTONES, SYNTHETIC_SKINTONES,
                                    skintones_for_species)


class TestTheSpeciesGate(BaseEvenniaTest):

    def test_a_human_cannot_be_chrome(self):
        allowed = skintones_for_species("human")
        self.assertIn("tan", allowed)
        self.assertNotIn("chrome", allowed)
        self.assertNotIn("cobalt", allowed)

    def test_a_synthetic_can_be_either(self):
        """The passing-synth case. Tomas is `fair` and Ossie is `pewter`;
        both must remain legal."""
        allowed = skintones_for_species("synthetic_humanoid")
        self.assertIn("fair", allowed)      # built to pass
        self.assertIn("pewter", allowed)    # built to read as a machine

    def test_an_unset_species_is_treated_as_human(self):
        self.assertEqual(skintones_for_species(None), ORGANIC_SKINTONES)

    def test_an_unknown_species_is_not_constrained(self):
        """A species added later must not be silently limited by a check
        written before it existed."""
        allowed = skintones_for_species("something_new")
        self.assertIn("chrome", allowed)

    def test_the_halves_do_not_overlap(self):
        self.assertFalse(set(ORGANIC_SKINTONES) & set(SYNTHETIC_SKINTONES))

    def test_every_live_synthetic_npc_tone_stays_legal(self):
        """The regression this test exists for: a stricter rule would have
        invalidated the eight synths who wear natural tones."""
        allowed = skintones_for_species("synthetic_humanoid")
        for tone in ("fair", "olive", "golden", "tan", "pale", "rich",
                     "light", "jade", "alabaster", "pewter"):
            self.assertIn(tone, allowed, tone)


class TestWornPronounsFlex(BaseEvenniaTest):
    """A literal pronoun in a worn_desc is gender-blind: worn descriptions
    go through `_process_description_variables`, which resolves `{their}`
    and leaves a bare `their` alone."""

    def test_no_worn_desc_uses_a_literal_pronoun_for_the_wearer(self):
        import re

        from world import prototypes
        src = open(prototypes.__file__.replace(".pyc", ".py")).read()
        offenders = []
        for line in src.splitlines():
            if '"worn_desc"' not in line:
                continue
            body = line.split('"worn_desc"', 1)[1]
            stripped = re.sub(r"\{(their|them|they)\}", "", body)
            # `their` may legitimately refer to the GARMENT ("its ripstop
            # fabric", "holding their line") — those are plural-noun
            # possessives, not the wearer, and are checked by eye.
            if re.search(r"\b(hugs|encases|clings to|across) their\b",
                         stripped):
                offenders.append(line.strip()[:70])
        self.assertEqual(offenders, [], f"gender-blind pronouns: {offenders}")
