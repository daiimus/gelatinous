"""The manifest is two rows, and nothing is cut mid-word (#3033 follow-up).

`score` crammed rank, department AND vessel onto one 48-column row and
hard-truncated at 47. On a real sheet that read:

    ║ Specialist, Signals & Survey — SBL-0092 Perpetu║

— cut mid-word, with the ship's name lost. Owner's call after seeing it
in play: separate it out.

Now labelled like the Subject and File Reference rows above it:

    ║ Posting: Specialist, Signals & Survey          ║
    ║ Vessel:  SBL-0092 Perpetual Noon               ║

The widest posting the tables can produce is "Specialist, Security &
Marshal Service" at 38 characters, which fits a " Posting: " row
exactly at 48. That is tight by construction, so it is pinned: a longer
department label would silently start truncating again.

`designation_line` is unchanged and still serves the places that
genuinely have one line — the decant envelope's MANIFEST stamp,
`CmdSoul`, and the build script's roster.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import manifest as manifest_mod


class _SheetCase(EvenniaTest):
    def stamped(self, dept="signals", rank="specialist", vessel="SBL-0092"):
        char = create_object("typeclasses.characters.Character",
                             key="Subject", location=self.room1)
        char.db.designation = {"rank": rank, "dept": dept, "vessel": vessel}
        return char


class TestTheRowsSplit(_SheetCase):
    def test_the_posting_carries_rank_and_department(self):
        posting, _berth = manifest_mod.designation_rows(self.stamped())
        self.assertIn("Specialist", posting)
        self.assertIn(",", posting)

    def test_the_vessel_row_carries_the_ship(self):
        _posting, berth = manifest_mod.designation_rows(self.stamped())
        self.assertIn("SBL-0092", berth)

    def test_the_ships_NAME_is_not_lost(self):
        """The truncation ate exactly this."""
        _posting, berth = manifest_mod.designation_rows(self.stamped())
        self.assertGreater(len(berth), len("SBL-0092"))

    def test_an_unlisted_person_gets_two_empty_strings(self):
        char = create_object("typeclasses.characters.Character",
                             key="Nobody", location=self.room1)
        char.db.designation = None
        self.assertEqual(manifest_mod.designation_rows(char), ("", ""))


class TestNothingOverflowsTheBox(_SheetCase):
    """48 columns, and the widest posting fills it exactly."""

    BOX = 48

    def test_the_widest_posting_still_fits(self):
        widest_dept = max(manifest_mod.DEPARTMENTS.values(), key=len)
        widest_rank = max(manifest_mod.RANK_LABELS.values(), key=len)
        row = f" Posting: {widest_rank}, {widest_dept}"
        self.assertLessEqual(len(row), self.BOX,
                             f"{len(row)} > {self.BOX}: {row!r}")

    def test_the_widest_vessel_still_fits(self):
        widest = max(manifest_mod.VESSELS.values(), key=len)
        row = f" Vessel:  SBL-0000 {widest}"
        self.assertLessEqual(len(row), self.BOX, row)

    def test_every_real_combination_fits(self):
        for rank in manifest_mod.RANK_LABELS.values():
            for dept in manifest_mod.DEPARTMENTS.values():
                row = f" Posting: {rank}, {dept}"
                self.assertLessEqual(len(row), self.BOX, row)


class TestTheOneLineFormStillExists(_SheetCase):
    """The envelope, CmdSoul and the build roster all want one line."""

    def test_designation_line_still_works(self):
        line = manifest_mod.designation_line(self.stamped())
        self.assertIn("Specialist", line)
        self.assertIn("SBL-0092", line)

    def test_its_callers_are_untouched(self):
        import inspect
        from commands import charcreate, CmdSoul
        for module in (charcreate, CmdSoul):
            self.assertIn("designation_line", inspect.getsource(module))
