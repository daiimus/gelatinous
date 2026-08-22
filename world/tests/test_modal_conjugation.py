"""Modals do not take an -s (#2162).

``conjugate_third_person`` falls through to its default rule for any
verb it does not recognise, and a modal is not recognised: "could"
becomes "coulds", "can" becomes "cans", "must" becomes "musts".

This is the grammar engine, so it is not one system's problem. The
emote renderer conjugates player-supplied verbs through it — a pose of
``.can barely stand`` shows the room "Jorge Jackson cans barely
stand". The longdesc person-verb token from #2160 hit the same wall
and patched it locally; the fix belongs here, where both callers get
it.
"""
from unittest import TestCase

from world.grammar import MODALS, conjugate_third_person, flex_verb
from world.tests.test_emote import _make_character
from world.emote import render_for_observer, tokenize_dot_pose


class TestModalsAreNotConjugated(TestCase):
    def test_the_modals_pass_through_unchanged(self):
        for modal in ("could", "would", "should", "might", "must",
                      "can", "will", "shall", "may"):
            self.assertEqual(conjugate_third_person(modal), modal)

    def test_case_is_preserved(self):
        self.assertEqual(conjugate_third_person("Could"), "Could")

    def test_a_real_verb_still_conjugates(self):
        self.assertEqual(conjugate_third_person("lean"), "leans")
        self.assertEqual(conjugate_third_person("catch"), "catches")
        self.assertEqual(conjugate_third_person("have"), "has")

    def test_a_modal_survives_number_flexing_both_ways(self):
        self.assertEqual(flex_verb("could", "singular"), "could")
        self.assertEqual(flex_verb("could", "plural"), "could")

    def test_can_is_a_modal_not_a_container(self):
        """'can' is in the table as a modal; the noun sense is not our
        problem here, since only verb tokens reach this function."""
        self.assertIn("can", MODALS)


class TestAtTheSurfacePlayersTouch(TestCase):
    """What the room actually sees when somebody poses a modal."""

    def setUp(self):
        self.actor = _make_character(key="Jorge Jackson", sex="male")
        self.observer = _make_character(key="Someone Else", sex="female",
                                        sleeve_uid="uid-observer")

    def _pose(self, text):
        return render_for_observer(
            tokenize_dot_pose(text, self.actor), self.actor, self.observer)

    def test_a_posed_modal_is_not_pluralised(self):
        out = self._pose("can barely stand.")
        self.assertNotIn("cans", out)
        self.assertIn("can barely stand", out)

    def test_the_actor_view_was_always_fine(self):
        """The self-view never conjugates, so it read correctly all
        along — which is how this survived."""
        out = render_for_observer(
            tokenize_dot_pose("can barely stand.", self.actor),
            self.actor, self.actor)
        self.assertEqual(out, "You can barely stand.")
