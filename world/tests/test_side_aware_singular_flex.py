"""Side-aware singular flex for paired body nouns (issue #341).

When a paired body-noun token (``{arms}``, ``{eyes}``, ``{ears}``,
``{hands}``, ``{thighs}``, ``{shins}``, ``{feet}``) flexes to singular
because only one side remains, the side is prefixed onto the noun.

Pre-fix: ``Her arm is wiry`` (lost the side info).
Post-fix: ``Her right arm is wiry`` (side preserved).

Tests cover:

* The ``substitute_pronoun_tokens`` helper (used by corpse + Appendage).
* All 7 pair-keyed nouns × both sides.
* Plural flex (no side info needed) is unchanged.
* Locations without left/right prefix produce no side prefix.
* Articles re-agree (``{an arm}`` + ``side="right"`` → ``"a right arm"``).
* Case-matching preserves leading-letter case from the body token.
* Non-pair flex nouns (``{leg}``, ``{shoulder}``) are unaffected.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import substitute_pronoun_tokens


class PairNounSideFlex(TestCase):

    def test_arm_singular_with_side_right(self):
        out = substitute_pronoun_tokens(
            "{Their} {arms} are wiry.",
            gender="female", number="singular", side="right",
        )
        self.assertEqual(out, "Her right arm are wiry.")
        # Verb agreement is #331, not in scope here — `are` stays bare.

    def test_arm_singular_with_side_left(self):
        out = substitute_pronoun_tokens(
            "{Their} {arms} are wiry.",
            gender="male", number="singular", side="left",
        )
        self.assertEqual(out, "His left arm are wiry.")

    def test_no_side_falls_back_to_bare_singular(self):
        out = substitute_pronoun_tokens(
            "{Their} {arms} are wiry.",
            gender="female", number="singular", side=None,
        )
        self.assertEqual(out, "Her arm are wiry.")

    def test_plural_ignores_side(self):
        # Side info is irrelevant when both sides are present.
        out = substitute_pronoun_tokens(
            "{Their} {arms} are wiry.",
            gender="female", number="plural", side="right",
        )
        self.assertEqual(out, "Her arms are wiry.")

    def test_all_pair_nouns_with_side(self):
        # Spot-check every PAIR_MERGE_KEYS noun + both sides.
        cases = [
            ("eyes", "right", "right eye"),
            ("eyes", "left", "left eye"),
            ("ears", "right", "right ear"),
            ("ears", "left", "left ear"),
            ("hands", "right", "right hand"),
            ("hands", "left", "left hand"),
            ("thighs", "right", "right thigh"),
            ("thighs", "left", "left thigh"),
            ("shins", "right", "right shin"),
            ("shins", "left", "left shin"),
            ("feet", "right", "right foot"),
            ("feet", "left", "left foot"),
        ]
        for token, side, expected in cases:
            with self.subTest(token=token, side=side):
                out = substitute_pronoun_tokens(
                    f"the {{{token}}}.",
                    gender="male", number="singular", side=side,
                )
                self.assertEqual(out, f"the {expected}.")


class CapitalisationPreserved(TestCase):

    def test_capitalised_token_capitalises_side(self):
        # {Arms} starts with uppercase → output starts with uppercase.
        out = substitute_pronoun_tokens(
            "{Arms} extend.",
            gender="male", number="singular", side="right",
        )
        self.assertEqual(out, "Right arm extend.")

    def test_lowercase_token_lowercase_side(self):
        out = substitute_pronoun_tokens(
            "her {arms}.",
            gender="female", number="singular", side="left",
        )
        self.assertEqual(out, "her left arm.")


class ArticleReAgreement(TestCase):

    def test_an_arm_becomes_a_right_arm(self):
        # "an arm" → "a right arm" (article re-agrees with the consonant
        # start of "right").
        out = substitute_pronoun_tokens(
            "It is {an arm}.",
            gender=None, number="singular", side="right",
        )
        self.assertEqual(out, "It is a right arm.")

    def test_an_eye_becomes_a_right_eye(self):
        # "an eye" → "a right eye".
        out = substitute_pronoun_tokens(
            "It is {an eye}.",
            gender=None, number="singular", side="right",
        )
        self.assertEqual(out, "It is a right eye.")

    def test_an_eye_left_is_a_left_eye(self):
        # "left" also starts with a consonant.
        out = substitute_pronoun_tokens(
            "It is {an eye}.",
            gender=None, number="singular", side="left",
        )
        self.assertEqual(out, "It is a left eye.")


class NonPairTokensUnaffected(TestCase):
    """Side prefix applies ONLY to pair-keyed nouns."""

    def test_leg_unaffected(self):
        # "leg" is in LONGDESC_FLEX_NOUNS but not in PAIR_MERGE_KEYS
        # singulars — should NOT get a side prefix.
        out = substitute_pronoun_tokens(
            "the {leg}.",
            gender=None, number="singular", side="right",
        )
        self.assertEqual(out, "the leg.")

    def test_shoulder_unaffected(self):
        out = substitute_pronoun_tokens(
            "the {shoulder}.",
            gender=None, number="singular", side="left",
        )
        self.assertEqual(out, "the shoulder.")


class LivingCharacterRenderer(TestCase):
    """The AppearanceMixin renderer also threads side through."""

    def test_side_helper_recognises_prefixes(self):
        from typeclasses.appearance_mixin import AppearanceMixin
        self.assertEqual(
            AppearanceMixin._side_from_location("left_arm"), "left"
        )
        self.assertEqual(
            AppearanceMixin._side_from_location("right_foot"), "right"
        )
        self.assertIsNone(
            AppearanceMixin._side_from_location("face")
        )
        self.assertIsNone(
            AppearanceMixin._side_from_location("hair")
        )
        self.assertIsNone(
            AppearanceMixin._side_from_location(None)
        )
