"""A pose reads correctly from BOTH ends (#2209).

Players type verbs already conjugated — `.stands back`, `.tries to
focus` — because that is how you describe yourself in the third person
in your head. The observer's view conjugates, so it was fixed when
`conjugate_third_person` became idempotent (#2165). The ACTOR's view
renders "You <verb>" and used the typed form verbatim, so it said
"You stands" and nobody fixed it, because the bug that surfaced was
the observer's.

That is the failure mode this test exists for: the same input, checked
from both perspectives, in one place.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.emote import render_for_observer, tokenize_dot_pose
from world.grammar import to_base_form
from world.tests.test_emote import _make_character


class TestBaseForm(EvenniaCommandTest):
    def test_conjugated_forms_normalise(self):
        self.assertEqual(to_base_form("stands"), "stand")
        self.assertEqual(to_base_form("tries"), "try")
        self.assertEqual(to_base_form("watches"), "watch")
        self.assertEqual(to_base_form("goes"), "go")

    def test_base_forms_are_unchanged(self):
        for verb in ("lean", "stand", "try", "watch", "pass", "cross"):
            self.assertEqual(to_base_form(verb), verb)

    def test_irregulars_take_the_you_form(self):
        self.assertEqual(to_base_form("is"), "are")
        self.assertEqual(to_base_form("has"), "have")
        self.assertEqual(to_base_form("does"), "do")

    def test_modals_are_untouched(self):
        for verb in ("can", "could", "will", "must"):
            self.assertEqual(to_base_form(verb), verb)

    def test_it_is_idempotent(self):
        for verb in ("stands", "lean", "is", "can", "tries"):
            once = to_base_form(verb)
            self.assertEqual(to_base_form(once), once)

    def test_it_round_trips_with_the_third_person(self):
        from world.grammar import conjugate_third_person
        for typed in ("stands", "stand", "tries", "try", "watches",
                      "goes", "passes", "is", "has"):
            base = to_base_form(typed)
            third = conjugate_third_person(typed)
            self.assertEqual(conjugate_third_person(base), third,
                             f"{typed!r}: base and typed disagree")


class TestBothEndsOfAPose(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.actor = _make_character(key="Jorge Jackson", sex="male")
        self.observer = _make_character(key="Someone", sex="female",
                                        sleeve_uid="uid-observer")

    def _both(self, pose):
        tokens = tokenize_dot_pose(pose, self.actor)
        return (render_for_observer(tokens, self.actor, self.actor),
                render_for_observer(tokens, self.actor, self.observer))

    def test_a_conjugated_verb_reads_right_from_both_ends(self):
        first, third = self._both("stands and .brushes off my coat.")
        self.assertIn("You stand and brush off your coat", first)
        self.assertIn("stands and brushes off his coat", third)

    def test_base_form_input_still_works(self):
        first, third = self._both("lean back.")
        self.assertIn("You lean back", first)
        self.assertIn("leans back", third)

    def test_modals_are_right_from_both_ends(self):
        first, third = self._both("can barely stand.")
        self.assertIn("You can barely stand", first)
        self.assertIn("can barely stand", third)
        self.assertNotIn("cans", third)

    def test_a_second_verb_normalises_too(self):
        first, _ = self._both("watches the door, then .looks away.")
        self.assertIn("You watch the door, then look away", first)

    def test_speech_keeps_its_verb(self):
        first, third = self._both('say "get down" and .duck.')
        self.assertIn("You say", first)
        self.assertIn("says", third)

    def test_participles_pass_through_both_ways(self):
        """`_should_conjugate` exempts -ing forms; base-forming must
        respect the same exemption."""
        first, third = self._both("diving for cover.")
        self.assertIn("diving", first)
        self.assertIn("diving", third)
