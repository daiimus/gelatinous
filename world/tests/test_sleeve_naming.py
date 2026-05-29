"""
Tests for sleeve display-name composition (issue #50).

Covers ``commands.charcreate.build_name_from_death_count`` — the single
source of truth for rendering a character's display name with a Roman
numeral suffix that reflects the sleeve iteration (``death_count``).

These are pure-function tests; no Evennia DB fixtures required.
"""

import unittest

from commands.charcreate import build_name_from_death_count


class TestBuildNameFromDeathCount(unittest.TestCase):
    """Helper renders the Roman numeral suffix correctly across cases."""

    def test_first_sleeve_appends_i(self):
        """death_count=1 → bare name gets " I" appended."""
        self.assertEqual(
            build_name_from_death_count("Brock", 1),
            "Brock I",
        )

    def test_second_sleeve_appends_ii(self):
        """death_count=2 → " II" suffix (first clone)."""
        self.assertEqual(
            build_name_from_death_count("Brock", 2),
            "Brock II",
        )

    def test_high_death_count_uses_large_numeral(self):
        """death_count=44 → XLIV suffix (matches user sample)."""
        self.assertEqual(
            build_name_from_death_count("Laszlo", 44),
            "Laszlo XLIV",
        )

    def test_strips_existing_roman_numeral_before_appending(self):
        """Existing suffix is stripped so re-application doesn't compound."""
        self.assertEqual(
            build_name_from_death_count("Brock III", 4),
            "Brock IV",
        )

    def test_preserves_name_ending_in_roman_letter(self):
        """Names like 'Drivel' (ends in L) are NOT stripped — needs whitespace."""
        # No whitespace before the trailing "L", so strip regex must skip it.
        self.assertEqual(
            build_name_from_death_count("Drivel", 1),
            "Drivel I",
        )

    def test_none_death_count_falls_back_to_one(self):
        """Defensive: None → treat as first sleeve."""
        self.assertEqual(
            build_name_from_death_count("Ghost", None),
            "Ghost I",
        )

    def test_zero_death_count_falls_back_to_one(self):
        """Defensive: pre-fix legacy 0 → treat as first sleeve."""
        self.assertEqual(
            build_name_from_death_count("Ghost", 0),
            "Ghost I",
        )

    def test_negative_death_count_falls_back_to_one(self):
        """Defensive: <1 → treat as first sleeve."""
        self.assertEqual(
            build_name_from_death_count("Ghost", -3),
            "Ghost I",
        )

    def test_two_word_name_only_strips_trailing_numeral(self):
        """First/last name preserved; only trailing numeral stripped."""
        self.assertEqual(
            build_name_from_death_count("Marcus Aurelius II", 3),
            "Marcus Aurelius III",
        )


class TestCharacterDeathCountDefault(unittest.TestCase):
    """AttributeProperty default is 1 (issue #50)."""

    def test_default_is_one(self):
        """death_count AttributeProperty default must be 1, not 0."""
        from typeclasses.characters import Character

        # Inspect the class-level AttributeProperty descriptor.
        descriptor = Character.__dict__["death_count"]
        # AttributeProperty stores its default as the first positional arg;
        # Evennia exposes it as ``_default`` on the descriptor.
        default = getattr(descriptor, "_default", None)
        self.assertEqual(
            default,
            1,
            "death_count AttributeProperty default must be 1 so the "
            "first sleeve renders as '<name> I' (issue #50).",
        )


if __name__ == "__main__":
    unittest.main()
