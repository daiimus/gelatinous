"""A surname spelled with Roman letters is a surname, not a numeral (#3359).

`build_name_from_death_count` strips a trailing generation numeral before
appending the current one. It matched that numeral case-INsensitively, so
any separate lowercase token made only of I/V/X/L/C/D/M was read as a
numeral and discarded: "Mary Dix" was decanted as "Mary I", the surname
never stored. The uniqueness scan in `validate_name` used the same loose
pattern, so it looked for a "Mary Dix" that never existed while the row
the new sleeve actually collides with is keyed "Mary I".

The spec (WEB_RESPAWN_CHARACTER_CREATION_SPEC, "Roman Numeral Parsing
Bug") records this defect as FIXED by requiring whitespace before the
numeral -- that closed the no-space case ("Drivel" -> "Drive II") only.

Now: one strict parser, `roman_value` / `split_roman_suffix`, shared by
the strip, the uniqueness scan and the web sleeve sort. A token is a
numeral only if it is uppercase, Roman letters only, and round-trips
through `int_to_roman`. The suffix we append is always exactly that form,
so nothing legitimate is lost. Residual edge, accepted: a player who
names themselves literally "XI" in uppercase is read as generation 11 --
that IS a canonical numeral, and the web parser already treats it so.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate
from commands.charcreate import build_name_from_death_count, validate_name

# The helpers are new; on the unfixed tree they are absent. Resolve lazily so
# the CONTROL run measures behaviour, not an ImportError (harness trap #4).
roman_value = getattr(charcreate, "roman_value", None)
split_roman_suffix = getattr(charcreate, "split_roman_suffix", None)


def _needs_helpers(test):
    if roman_value is None or split_roman_suffix is None:
        test.skipTest("strict helpers not present (unfixed tree)")


class SurnameIsNotANumeralTest(EvenniaTest):

    # --- the defect ------------------------------------------------------

    def test_roman_letter_surnames_survive_decant(self):
        for full in ("Mary Dix", "Sam Mill", "Cid Mix", "Mary Dill",
                     "Anya Lim", "Ida Civil"):
            self.assertEqual(build_name_from_death_count(full, 1),
                             f"{full} I", "%r lost its surname" % full)

    def test_lowercase_token_is_not_a_numeral(self):
        _needs_helpers(self)
        for tok in ("dix", "mill", "mix", "Dix", "Mix", "iv"):
            self.assertIsNone(roman_value(tok), "%r read as a numeral" % tok)

    def test_uppercase_word_that_is_not_canonical_is_not_a_numeral(self):
        _needs_helpers(self)
        # Non-canonical spellings are names, not numbers. (Note "MIX" IS
        # canonical -- M + IX = 1009 -- so an all-caps MIX is read as a
        # numeral; a real surname arrives as "Mix" and is safe.)
        self.assertEqual(roman_value("MIX"), 1009)
        self.assertIsNone(roman_value("IIII"))
        self.assertIsNone(roman_value("VX"))

    def test_uniqueness_scan_sees_the_roman_letter_surname(self):
        # Post-fix invariant: a second "Mary Dix" is refused. (The unfixed
        # loose scan also passes this -- it is a superset -- so this guards
        # the fix rather than discriminating the bug; the decant test above
        # is the discriminator.)
        create_object("typeclasses.characters.Character", key="Mary Dix I")
        ok, err = validate_name("Mary Dix")
        self.assertFalse(ok, "second Mary Dix was allowed through")

    # --- controls: real numerals still strip and re-number ----------------

    def test_real_generation_numeral_is_replaced(self):
        self.assertEqual(build_name_from_death_count("Brock II", 3), "Brock III")
        self.assertEqual(build_name_from_death_count("Laszlo XLIV", 45), "Laszlo XLV")
        self.assertEqual(build_name_from_death_count("Mick Doe I", 2), "Mick Doe II")

    def test_split_roman_suffix(self):
        _needs_helpers(self)
        self.assertEqual(split_roman_suffix("Brock III"), ("Brock", 3))
        self.assertEqual(split_roman_suffix("Mary Dix"), ("Mary Dix", None))
        self.assertEqual(split_roman_suffix("Drivel"), ("Drivel", None))
        self.assertEqual(split_roman_suffix("Mary Dix I"), ("Mary Dix", 1))

    def test_no_space_case_still_fixed(self):
        # The earlier half-fix's own case must keep working.
        self.assertEqual(build_name_from_death_count("Drivel", 2), "Drivel II")

    def test_roman_value_canonical(self):
        _needs_helpers(self)
        for n in (1, 4, 9, 14, 40, 44, 90, 400, 1994):
            from commands.charcreate import int_to_roman
            self.assertEqual(roman_value(int_to_roman(n)), n)
