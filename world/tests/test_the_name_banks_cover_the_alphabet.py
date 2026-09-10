"""No name bank is truncated partway through the alphabet (#2638).

`FIRST_NAMES_FEMALE` was alphabetically sorted and stopped dead at
`Martha`. No female NPC in the colony could be born with a name starting
N through Z, and a live census found 25 generated women, none named past
M. Every sibling bank covered the alphabet; the female bank's gap was
thirteen CONSECUTIVE letters, which is a truncation, not curation.

This is the kind of defect that is invisible in review and obvious in
aggregate, so the guard is about SHAPE rather than about any name:

  * no run of missing initials long enough to be a truncation,
  * nothing missing off the END, which is what a truncation looks like,
  * the sex-keyed banks within reach of each other in size, so one sex
    does not repeat names far more often than the other.

X, Q and U genuinely thin out in the name space -- the male bank has no
X and no Y -- so isolated gaps are allowed and only runs are not.

Deliberately says nothing about the CONTENT of the entries. `LAST_NAMES`
holds machine-generated particle x base cross-products ("O' Fischer",
"St. Cruz", "von Silva") which #2639 governs; a well-formedness rule
here would either have to be written around them or drag that issue's
fix into this one.
"""
import string

from evennia.utils.test_resources import EvenniaTest

from world.namebank import (
    FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE, FIRST_NAMES_MALE, LAST_NAMES,
)

BANKS = {
    "FIRST_NAMES_MALE": FIRST_NAMES_MALE,
    "FIRST_NAMES_FEMALE": FIRST_NAMES_FEMALE,
    "FIRST_NAMES_AMBIGUOUS": FIRST_NAMES_AMBIGUOUS,
    "LAST_NAMES": LAST_NAMES,
}

#: A truncation shows up as CONSECUTIVE missing letters. Three in a row
#: is past anything the name space produces on its own.
LONGEST_ALLOWED_GAP = 3


def initials(bank):
    return {n[0].upper() for n in bank if n}


class TestTheNameBanksCoverTheAlphabet(EvenniaTest):

    def test_the_banks_are_populated(self):
        """Control: an empty bank has no gaps at all and would sail
        through every assertion below."""
        for name, bank in BANKS.items():
            self.assertGreater(len(bank), 50, name)

    def test_no_bank_is_truncated_partway(self):
        for name, bank in BANKS.items():
            have = initials(bank)
            missing = [c for c in string.ascii_uppercase if c not in have]
            runs, run = [], []
            for c in string.ascii_uppercase:
                if c in have:
                    if run:
                        runs.append(run)
                    run = []
                else:
                    run.append(c)
            if run:
                runs.append(run)
            worst = max((len(r) for r in runs), default=0)
            self.assertLessEqual(
                worst, LONGEST_ALLOWED_GAP,
                f"{name} is missing {worst} consecutive initials "
                f"({''.join(missing)}) — that is a truncated list, not a "
                f"thin patch of the name space")

    def test_no_bank_stops_before_the_end_of_the_alphabet(self):
        """The specific shape of this defect: the list ran out."""
        for name, bank in BANKS.items():
            last = max(initials(bank))
            self.assertGreaterEqual(
                last, "W",
                f"{name} has nothing past {last} — a sorted list that "
                f"ends early is a list someone stopped writing")

    def test_neither_sex_draws_from_a_much_smaller_pool(self):
        """A third fewer names means a third more repeats."""
        smaller = min(len(FIRST_NAMES_MALE), len(FIRST_NAMES_FEMALE))
        larger = max(len(FIRST_NAMES_MALE), len(FIRST_NAMES_FEMALE))
        self.assertGreater(
            smaller / larger, 0.75,
            f"male {len(FIRST_NAMES_MALE)} vs female "
            f"{len(FIRST_NAMES_FEMALE)}")

    def test_the_banks_hold_no_duplicates(self):
        for name, bank in BANKS.items():
            self.assertEqual(len(bank), len(set(bank)), name)
