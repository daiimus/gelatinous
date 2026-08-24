"""The operate pickers ask instead of guessing (#2276).

`_parse_pick` returned the FIRST substring match. So typing `arm` at
the amputate picker silently took the LEFT arm, and `kidney` at the
harvest picker silently took a kidney. The wrong-organ case never
surfaced as an error — it just went quietly onto the surgical chart.

That is the one behaviour the owner explicitly ruled out. On a command
that opens a body, guessing is the difference between a mistake and a
fatality.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from commands import CmdOperate as op

ORGANS = [("heart", "chest"), ("left_kidney", "abdomen"),
          ("right_kidney", "abdomen"), ("brain", "head")]
LIMBS = ["left_arm", "right_arm", "head"]


class TestItNoLongerGuesses(EvenniaCommandTest):
    def test_a_side_less_limb_is_a_question(self):
        """The amputation case. This used to return the left arm."""
        got = op._parse_pick("arm", LIMBS)
        self.assertIsInstance(got, op._Several)
        self.assertEqual(sorted(got), ["left_arm", "right_arm"])

    def test_a_paired_organ_is_a_question(self):
        got = op._parse_pick("kidney", ORGANS)
        self.assertIsInstance(got, op._Several)
        self.assertEqual(len(got), 2)

    def test_naming_the_side_settles_it(self):
        self.assertEqual(op._parse_pick("left arm", LIMBS), "left_arm")

    def test_numbers_still_pick_exactly(self):
        self.assertEqual(op._parse_pick("1", LIMBS), "left_arm")
        self.assertEqual(op._parse_pick("3", LIMBS), "head")

    def test_a_number_off_the_end_is_not_a_wild_guess(self):
        self.assertIsNone(op._parse_pick("9", LIMBS))

    def test_an_unknown_name_matches_nothing(self):
        self.assertIsNone(op._parse_pick("flux capacitor", LIMBS))


class TestItSpeaksTheBodysLanguage(EvenniaCommandTest):
    def test_a_machine_name_picks_the_right_organ(self):
        """The picker prints 'power core'; typing it back must work."""
        self.assertEqual(op._parse_pick("power core", ORGANS, "robot"),
                         ("heart", "chest"))

    def test_the_canonical_key_still_picks(self):
        self.assertEqual(op._parse_pick("heart", ORGANS, "robot"),
                         ("heart", "chest"))

    def test_the_dangerous_partial_asks_in_machine_words(self):
        got = op._parse_pick("core", ORGANS, "robot")
        self.assertIsInstance(got, op._Several)
        self.assertEqual(op._name_picks(got, "robot"),
                         "power core, processor core")

    def test_a_person_is_asked_in_organic_words(self):
        got = op._parse_pick("kidney", ORGANS, "human")
        self.assertEqual(op._name_picks(got, "human"),
                         "left kidney, right kidney")


class TestEveryPickerGotIt(EvenniaCommandTest):
    def test_all_four_pickers_ask(self):
        """One matcher, four pickers. If a site were missed it would
        silently keep guessing, which is exactly the failure mode."""
        import inspect
        src = inspect.getsource(op)
        self.assertEqual(src.count("isinstance(pick, _Several)"), 4)
        self.assertEqual(src.count("pick = _parse_pick(raw,"), 4)
