"""Every authored disposition field reaches the prompt.

Regression pin for #2730. `manner`, `wants` and `boundaries` sat BELOW
an early return on `personality`, so they read as a FALLBACK for a seed
with no personality line rather than as additions to one.

Any seed setting both discarded all three. Measured live: 64 of the
colony's 80 personas, 192 authored fields -- including all six security
robots losing every one.

They are different facts, not competing versions of one: a manner is how
they carry themselves, a want is what they are after, a boundary is what
they will not do. A personality line does not contain them.
"""

from unittest import TestCase

from world.llm.prompt import _personality

FULL = {
    "personality": "Taciturn.",
    "manner": "wipes the same glass",
    "wants": "a quiet shift",
    "boundaries": "break up a fight",
}


class TestTheAuthoredPersonaReachesThePrompt(TestCase):

    def test_every_field_reaches_the_prompt(self):
        out = _personality(FULL)
        self.assertIn("Taciturn.", out)
        self.assertIn("wipes the same glass", out)
        self.assertIn("wants a quiet shift", out)
        self.assertIn("won't break up a fight", out)

    def test_personality_leads(self):
        """It is the summary line; the rest qualify it."""
        self.assertTrue(_personality(FULL).startswith("Taciturn."))

    # -- controls: the fallback behaviour must survive ---------------

    def test_a_seed_with_only_a_personality_is_unchanged(self):
        self.assertEqual(_personality({"personality": "Taciturn."}),
                         "Taciturn.")

    def test_a_seed_with_no_personality_still_composes(self):
        self.assertEqual(
            _personality({"manner": "wipes the same glass",
                          "wants": "a quiet shift"}),
            "wipes the same glass; wants a quiet shift",
        )

    def test_an_empty_seed_is_empty(self):
        self.assertEqual(_personality({}), "")
