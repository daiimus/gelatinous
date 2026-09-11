"""Hunger and craving consult the same violence dial.

Regression pin for #2704. Two gates onto the same decision -- whether a
soul will rob someone -- with a comment asserting they are the same
gate:

    # a broke addict with lawless hands robs for the fix — the same
    # knife, mark, and mood gate as hunger (misery is the mechanism)

The hunger gate read `traits.dial(soul, "violence_gate", 0.25)`. The
craving gate hardcoded `0.25`, the dial's DEFAULT. The tell was that the
craving branch did not import `traits` at all: the dial was not dropped
mid-expression, it was never consulted there.

Live when fixed: 5 of 80 souls carry a tuned value -- two at 0.45, three
at 0.05 -- so those five were gated one way by hunger and another by
craving.
"""

import inspect
from unittest import TestCase

import world.souls.actions as actions


class TestOneGateForHungerAndCraving(TestCase):

    def test_both_gates_read_the_dial(self):
        src = inspect.getsource(actions)
        self.assertEqual(
            src.count('dial(soul, "violence_gate", 0.25)'), 2,
            "one of the two mugging gates is not reading the dial",
        )

    def test_no_gate_compares_mood_to_a_bare_number(self):
        """The shape of the defect, not just its one instance."""
        src = inspect.getsource(actions)
        self.assertNotIn("mood(soul) >= 0.25", src)

    def test_the_craving_branch_imports_traits(self):
        """The tell: the branch never consulted the dial at all."""
        src = inspect.getsource(actions)
        craving = src[src.index("a broke addict with lawless hands"):]
        self.assertIn("traits as traits_mod", craving[:600])
