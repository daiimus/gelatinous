"""You can type the name the game just printed (#2276).

`get_organ_display_name` gave the world a per-species vocabulary for
organs. Input never got its mirror, so every command matched raw
canonical keys — and `harvest` listed "processor core, left optical
sensor, right audio sensor" and then rejected all three, accepting only
the hidden human key `brain`.

The rule for ambiguity is the owner's, and it is the same one that
governs eating an unidentified stew: ASK, never guess. On a command
that opens a body, picking between a processor core and a power core
is not a mistake anybody can walk back.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.anatomy import (Ambiguous, get_organ_display_name,
                           name_the_options, resolve_organ)

ROBOT_ORGANS = ["brain", "heart", "liver", "left_kidney", "right_kidney",
                "left_eye", "right_eye", "left_lung", "right_lung"]


class TestYouCanTypeWhatYouWereShown(EvenniaCommandTest):
    def test_the_machine_name_resolves(self):
        self.assertEqual(resolve_organ("power core", ROBOT_ORGANS, "robot"),
                         "heart")

    def test_every_name_the_command_would_print(self):
        """The exact failure: each listed name must come back."""
        for key in ROBOT_ORGANS:
            shown = get_organ_display_name(key, "robot")
            with self.subTest(shown=shown):
                self.assertEqual(resolve_organ(shown, ROBOT_ORGANS, "robot"),
                                 key)

    def test_the_canonical_key_still_works(self):
        """Builders, scripts and habit all use the key. It must not
        stop working just because a display name now does."""
        self.assertEqual(resolve_organ("heart", ROBOT_ORGANS, "robot"),
                         "heart")
        self.assertEqual(resolve_organ("left_kidney", ROBOT_ORGANS, "robot"),
                         "left_kidney")

    def test_case_and_spacing_are_forgiven(self):
        for typed in ("Power Core", "  power   core  ", "POWER CORE"):
            with self.subTest(typed=typed):
                self.assertEqual(
                    resolve_organ(typed, ROBOT_ORGANS, "robot"), "heart")

    def test_a_person_still_speaks_organically(self):
        self.assertEqual(resolve_organ("heart", ROBOT_ORGANS, "human"),
                         "heart")
        self.assertIsNone(resolve_organ("power core", ROBOT_ORGANS, "human"))


class TestItAsksRatherThanGuesses(EvenniaCommandTest):
    def test_a_pair_is_a_question(self):
        got = resolve_organ("coolant filter", ROBOT_ORGANS, "robot")
        self.assertIsInstance(got, Ambiguous)
        self.assertEqual(sorted(got), ["left_kidney", "right_kidney"])

    def test_the_dangerous_one(self):
        """'core' reaches both the processor core and the power core.
        Guessing here is the difference between a mistake and a
        fatality."""
        got = resolve_organ("core", ROBOT_ORGANS, "robot")
        self.assertIsInstance(got, Ambiguous)
        self.assertEqual(sorted(got), ["brain", "heart"])

    def test_the_question_is_asked_in_this_body_s_words(self):
        got = resolve_organ("core", ROBOT_ORGANS, "robot")
        self.assertEqual(name_the_options(got, "robot"),
                         "power core, processor core")

    def test_naming_one_side_settles_it(self):
        self.assertEqual(
            resolve_organ("left coolant filter", ROBOT_ORGANS, "robot"),
            "left_kidney")

    def test_a_full_name_is_never_overridden_by_a_partial(self):
        """'left eye' names exactly one thing even though 'eye' names
        two — a complete name must not be dragged into a question."""
        self.assertEqual(
            resolve_organ("left optical sensor", ROBOT_ORGANS, "robot"),
            "left_eye")

    def test_an_unknown_name_is_not_a_question(self):
        self.assertIsNone(resolve_organ("flux capacitor", ROBOT_ORGANS,
                                        "robot"))

    def test_nothing_is_not_a_question(self):
        for junk in ("", "   ", None, 7):
            with self.subTest(junk=junk):
                self.assertIsNone(resolve_organ(junk, ROBOT_ORGANS, "robot"))

    def test_it_only_offers_what_the_caller_allowed(self):
        """Filtering (harvestable / present / undestroyed) stays the
        caller's job; the resolver never widens the set."""
        self.assertIsNone(resolve_organ("power core", ["brain"], "robot"))


class TestTheOneDeliberateTieBreak(EvenniaCommandTest):
    """A complete name beats a partial, and ONLY that.

    The owner's ruling was ask-never-guess, and this does not bend it:
    guessing between PARTIAL matches never happens. But if one organ's
    full name is nested inside another's, flat matching would make the
    shorter organ permanently unreachable — every token that names it
    also names its longer neighbour, so the command could only ever ask
    a question the player has no way to answer.

    No organ in the game collides this way today, so this changes no
    live behaviour. It is here so the resolver can't strand a component
    the moment someone authors one that does.
    """

    def test_a_nested_name_stays_reachable(self):
        from unittest import mock
        from world.anatomy import organs as organs_mod
        names = {"core_unit": "core", "power_plant": "power core"}
        with mock.patch.object(organs_mod, "get_organ_display_name",
                               side_effect=lambda k, s=None: names.get(k, k)):
            keys = list(names)
            # the nested one resolves outright...
            self.assertEqual(
                organs_mod.resolve_organ("core", keys, "robot"), "core_unit")
            # ...its neighbour still resolves too...
            self.assertEqual(
                organs_mod.resolve_organ("power core", keys, "robot"),
                "power_plant")
            # ...and a genuine partial still asks
            got = organs_mod.resolve_organ("cor", keys, "robot")
            self.assertIsInstance(got, organs_mod.Ambiguous)

    def test_partials_are_never_guessed_between(self):
        """The rule that actually matters, restated as a test."""
        for token in ("core", "coolant filter", "kidney", "eye", "lung"):
            with self.subTest(token=token):
                got = resolve_organ(token, ROBOT_ORGANS, "robot")
                self.assertNotIsInstance(got, str,
                                         f"{token!r} was guessed, not asked")
