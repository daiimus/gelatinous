"""Person-subject verbs in longdesc prose (#2150).

The ordinary ``{verb}`` token agrees with the BODY PART's number, which
is the right subject for "{Their} {thighs} {are} bruised" and the wrong
one the moment the sentence's subject is the person. A paired slot
rendered "she keep", "he have", "she walk" — visible in the most-read
prose in the game, on every gendered character.

``{they walk}`` puts the pronoun and its verb in one token and agrees
with the person instead. The self-view is free: "you" takes the base
form, exactly as a plural subject does.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.anatomy.longdesc_tokens import substitute_pronoun_tokens


class TestPersonVerbAgreesWithThePerson(EvenniaCommandTest):
    def _render(self, text, gender, number="plural"):
        return substitute_pronoun_tokens(
            text, gender=gender, name="Nonna", number=number)

    def test_paired_slot_no_longer_disagrees(self):
        """The bug: part is plural, subject is the person."""
        line = "{Their} {thighs} {are} bare, and {they walk} without hurry."
        self.assertEqual(
            self._render(line, "female"),
            "Her thighs are bare, and she walks without hurry.")

    def test_plural_gender_keeps_the_base_form(self):
        line = "{Their} {thighs} {are} bare, and {they walk} without hurry."
        self.assertEqual(
            self._render(line, "nonbinary"),
            "Their thighs are bare, and they walk without hurry.")

    def test_only_the_first_word_of_a_phrase_carries_agreement(self):
        line = "a smear {they have not noticed}."
        self.assertEqual(self._render(line, "male"),
                         "a smear he has not noticed.")
        self.assertEqual(self._render(line, "nonbinary"),
                         "a smear they have not noticed.")

    def test_part_subject_verbs_are_untouched(self):
        """The existing template must keep flexing against the part."""
        line = "{Their} {thighs} {are} unremarkable."
        self.assertEqual(self._render(line, "female", number="plural"),
                         "Her thighs are unremarkable.")
        self.assertEqual(self._render(line, "female", number="singular"),
                         "Her thigh is unremarkable.")


class TestAtTheSurfacePlayersTouch(EvenniaCommandTest):
    """Not the helper — what `look` actually prints.

    Longdescs render in the third person on every path, including when
    you look at yourself, so agreement here is driven entirely by the
    looked-at character's own pronouns.
    """

    LINE = "{Their} {thighs} {are} bare, and {they walk} without hurry."

    def _appearance(self, sex, paired=True):
        self.char1.sex = sex      # AttributeProperty, category "biology"
        if paired:
            self.char1.set_longdesc("left_thigh", self.LINE)
            self.char1.set_longdesc("right_thigh", self.LINE)
        else:
            self.char1.set_longdesc("left_thigh", self.LINE)
        return self.char1.get_longdesc_appearance(looker=self.char2)

    def test_a_woman_walks(self):
        self.assertIn("she walks without hurry", self._appearance("female"))

    def test_a_man_walks(self):
        self.assertIn("he walks without hurry", self._appearance("male"))

    def test_singular_they_keeps_the_base_form(self):
        out = self._appearance("ambiguous")
        self.assertIn("they walk without hurry", out)
        self.assertNotIn("they walks", out)

    def test_a_lone_side_still_agrees_with_the_person(self):
        """The part goes singular; the person does not."""
        out = self._appearance("female", paired=False)
        self.assertIn("she walks without hurry", out)


class TestTheCatalogueIsClean(EvenniaCommandTest):
    """No shipped line may put a present-tense verb on a bare {they}.

    Past tense and modals are invariant across person and stay legal.
    """

    SAFE_NEXT_WORD = {
        "could", "would", "should", "might", "must", "can", "will",
        "fell", "slept", "had", "was", "were", "did", "went", "stopped",
        "left", "kept", "spent", "lost", "found", "made", "took", "saw",
    }

    def test_no_bare_person_subject_present_tense(self):
        import glob
        import re

        offenders = []
        pattern = re.compile(r"\{[Tt]hey\}\s+([A-Za-z']+)")
        for path in sorted(glob.glob("world/mob_flavor/longdescs*.py")):
            with open(path) as handle:
                for lineno, text in enumerate(handle, 1):
                    for word in pattern.findall(text):
                        if word.lower() not in self.SAFE_NEXT_WORD:
                            offenders.append(f"{path}:{lineno} {{they}} {word}")
        self.assertEqual(
            offenders, [],
            "use {they <verb>} so the verb agrees with the person:\n"
            + "\n".join(offenders))
