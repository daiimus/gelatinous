"""`.leans on the bar` shows you "You lean" (#3197).

The mirror of #2642, on the other side of the same renderer. The
observer branch conjugated the verb; the actor branch printed it
verbatim on the assumption that a player types the BASE form:

    if is_actor:
        # Actor self-view: "You lean" or "you lean" if speech came first
        parts.append(f"{you} {token.base_form}")

Nothing enforced that, and the observer side explicitly does not assume
it — `conjugate_third_person`'s docstring says ".stands back is an
ordinary thing to type". So one side of the renderer decided typing the
`-s` form was ordinary and the other never got the matching treatment,
and only the person who typed it saw the mistake.

English second person takes the plural form, which `inflect`'s
`plural_verb` gives — already used inside `conjugate_third_person` for
its normalisation step. Modals and irregular past pass through, which is
right for the actor line too: "You could", "You went".
"""
from evennia.utils.test_resources import EvenniaTest

from world import grammar as grammar_mod

#: Bound with a verbatim fallback — the unfixed behaviour — so the file
#: still LOADS against a tree without the function and the assertions
#: fail on their own terms rather than erroring.
conjugate_second_person = getattr(grammar_mod, "conjugate_second_person",
                                  lambda verb: verb)


class TestTheSecondPersonForm(EvenniaTest):

    def test_a_typed_third_person_form_is_reduced(self):
        for typed, want in (("leans", "lean"), ("stands", "stand"),
                            ("goes", "go"), ("tries", "try"),
                            ("catches", "catch"), ("runs", "run")):
            self.assertEqual(conjugate_second_person(typed), want, typed)

    def test_a_base_form_is_left_alone(self):
        """Control: the case the renderer always assumed, and the one it
        must not break."""
        for verb in ("lean", "stand", "go", "try", "catch", "run",
                     "cross", "pass", "focus", "discuss", "process",
                     "gaze", "brace", "wince"):
            self.assertEqual(conjugate_second_person(verb), verb, verb)

    def test_be_and_have_take_their_second_person_forms(self):
        for typed, want in (("is", "are"), ("was", "were"),
                            ("has", "have"), ("does", "do"),
                            ("am", "are")):
            self.assertEqual(conjugate_second_person(typed), want, typed)

    def test_modals_and_past_tense_pass_through(self):
        for verb in ("can", "could", "should", "went", "said", "took",
                     "gave", "stood"):
            self.assertEqual(conjugate_second_person(verb), verb, verb)

    def test_capitalisation_survives(self):
        self.assertEqual(conjugate_second_person("Leans"), "Lean")
        self.assertEqual(conjugate_second_person("Is"), "Are")

    def test_an_empty_verb_does_not_raise(self):
        self.assertEqual(conjugate_second_person(""), "")


class TestBothHalvesOfThePoseRead(EvenniaTest):
    """Driven through the RENDERER, because the defect is that the two
    halves of one render disagree — a helper test cannot see that.

    Not through `execute_cmd`: `EvenniaTest` does not load the character
    cmdset, so the pose command never runs and every assertion passes on
    an empty string. The live probe on the running server used the real
    command; here the renderer is the honest seam.
    """

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.watcher = self.char2
        for who in (self.actor, self.watcher):
            who.location = self.room1
            who.height = "average"
            who.build = "stocky"

    def pose(self, raw):
        from world.emote import render_for_observer, tokenize_dot_pose
        tokens = tokenize_dot_pose(raw, self.actor, [self.actor,
                                                     self.watcher])
        return (render_for_observer(tokens, self.actor, self.actor),
                render_for_observer(tokens, self.actor, self.watcher))

    def test_the_room_still_reads_correctly(self):
        """Control: if the observer half broke, the actor assertions
        below would be measuring a renderer that was wrong twice."""
        _mine, theirs = self.pose(".leans on the bar")
        self.assertIn("leans on the bar", theirs)

    def test_and_so_does_the_actor(self):
        mine, _theirs = self.pose(".leans on the bar")
        self.assertIn("You lean on the bar", mine)
        self.assertNotIn("You leans", mine)

    def test_a_base_form_still_reads_both_ways(self):
        mine, theirs = self.pose(".lean on the bar")
        self.assertIn("You lean on the bar", mine)
        self.assertIn("leans on the bar", theirs)

    def test_past_tense_reads_both_ways(self):
        mine, theirs = self.pose(".went to the counter")
        self.assertIn("You went to the counter", mine)
        self.assertIn("went to the counter", theirs)
