"""The two pose commands, and what each one promises (#2211).

LambdaMOO-style posing: you write in the FIRST person and dot-mark
each verb —

    .stand and .brush off my coat.

so the verbs are always base forms, because you are writing "I stand
and brush off my coat." The renderer conjugates for observers.

There is a SECOND command for third-person authoring — ``emote`` /
``:`` / ``pose`` — where you write "stands and brushes off his coat"
and it is prepended with your name, verbatim.

These tests exist because I blurred that line: I fed third-person
verbs to the first-person command in a probe, treated the output as a
bug, and normalised it away — which would have made ``.stands`` and
``.stand`` identical and quietly absorbed the other command's job.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.emote import render_for_observer, tokenize_dot_pose
from world.tests.test_emote import _make_character


class TestFirstPersonPose(EvenniaCommandTest):
    """`.` — the player writes base-form verbs, first person."""

    def setUp(self):
        super().setUp()
        self.actor = _make_character(key="Jorge Jackson", sex="male")
        self.observer = _make_character(key="Someone", sex="female",
                                        sleeve_uid="uid-observer")

    def _both(self, pose):
        tokens = tokenize_dot_pose(pose, self.actor)
        return (render_for_observer(tokens, self.actor, self.actor),
                render_for_observer(tokens, self.actor, self.observer))

    def test_the_canonical_pose(self):
        """`.stand and .brush off my coat.` — the owner's own example."""
        first, third = self._both("stand and .brush off my coat.")
        self.assertEqual(first, "You stand and brush off your coat.")
        self.assertIn("stands and brushes off his coat", third)

    def test_a_single_verb(self):
        first, third = self._both("lean back.")
        self.assertEqual(first, "You lean back.")
        self.assertIn("leans back", third)

    def test_a_modal_is_not_pluralised(self):
        """`.can barely stand` — "cans" was a real bug (#2163), because
        a modal IS valid first-person input."""
        first, third = self._both("can barely stand.")
        self.assertEqual(first, "You can barely stand.")
        self.assertIn("can barely stand", third)
        self.assertNotIn("cans", third)

    def test_pronouns_transform_per_perspective(self):
        first, third = self._both("scratch my jaw.")
        self.assertIn("your jaw", first)
        self.assertIn("his jaw", third)

    def test_participles_pass_through(self):
        first, third = self._both("diving for cover.")
        self.assertIn("diving", first)
        self.assertIn("diving", third)


class TestTheTwoCommandsStaySeparate(EvenniaCommandTest):
    """`emote` is third-person authoring and must stay verbatim.

    Its renderer has no verb branch at all, which is what keeps the two
    apart. If verb handling ever appears there, an author who
    deliberately wrote "stands" would find their own emote rewritten.
    """

    def setUp(self):
        super().setUp()
        self.actor = _make_character(key="Jorge Jackson", sex="male")
        self.observer = _make_character(key="Someone", sex="female",
                                        sleeve_uid="uid-observer")

    def _emote(self, text):
        from world.emote import render_emote_for_observer, tokenize_emote
        tokens = tokenize_emote(text, self.actor, [])
        return (render_emote_for_observer(tokens, self.actor, self.actor),
                render_emote_for_observer(tokens, self.actor, self.observer))

    def test_third_person_authoring_is_verbatim(self):
        actor_view, observer_view = self._emote(
            "stands and brushes off his coat.")
        for view in (actor_view, observer_view):
            self.assertIn("stands and brushes off his coat", view)
            self.assertNotIn("stand and brush", view)

    def test_third_person_authoring_never_says_you(self):
        actor_view, _ = self._emote("leans against the wall.")
        self.assertTrue(actor_view.startswith("Jorge Jackson"), actor_view)

    def test_the_emote_renderer_has_no_verb_handling(self):
        import inspect

        from world import emote
        src = inspect.getsource(emote.render_emote_for_observer)
        self.assertNotIn("VerbToken", src)
        self.assertNotIn("conjugate_third_person", src)
        self.assertNotIn("to_base_form", src)
