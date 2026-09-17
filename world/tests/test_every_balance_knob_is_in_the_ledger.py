"""Every tunable number in the gravity layer is written down (#3579).

The defect this guards is the one BALANCE_PASS_PENDING keeps filing: a
knob ships inside a module, nobody records what it was sized against,
and a year later the only way to learn whether ``FALL_DAMAGE_PER_STORY``
was ever balanced against bleeding is to read the diff that introduced
it. Two lists have to stay pinned to each other:

* every constant in ``world/combat/constants.py`` whose own ``#:``
  docstring block says ``BALANCE:`` must have a row in
  ``specs/roadmaps/BALANCE_LEDGER.md``; and
* every ``FALL_*`` / ``GAP_*`` name the ledger quotes in backticks must
  still exist in ``constants.py`` -- a renamed knob leaves the ledger
  describing a number nothing reads.

Neither direction is checkable from the module alone, so this reads both
files off disk. If the ledger is missing the test fails loudly: an
undocumented knob and an absent ledger are the same defect.
"""

from __future__ import annotations

import pathlib
import re
from unittest import TestCase

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONSTANTS = _ROOT / "world" / "combat" / "constants.py"
_LEDGER = _ROOT / "specs" / "roadmaps" / "BALANCE_LEDGER.md"

#: A module-level constant assignment: ``NAME = ...`` at column zero.
_ASSIGN = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=")
#: A backticked ALL-CAPS identifier -- the shape a constant is written
#: in inside a ledger table row. Anchored on both backticks so a cited
#: filename (`PARKOUR_TEMPLATE_LIBRARY.md`) is not mistaken for one.
_TABLE_NAME = re.compile(r"`([A-Z][A-Z0-9_]{3,})`")


def _balance_knobs(source: str) -> list[str]:
    """Names whose IMMEDIATELY preceding ``#:`` block says ``BALANCE:``.

    The block is the run of ``#:`` lines directly above the assignment;
    any other line (blank, plain ``#`` banner, code) ends it. That is
    what makes the marker belong to one constant rather than leaking
    down a whole section.
    """
    knobs = []
    block: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#:"):
            block.append(stripped)
            continue
        match = _ASSIGN.match(line)
        if match:
            if any("BALANCE:" in entry for entry in block):
                knobs.append(match.group(1))
        block = []
    return knobs


class TestTheLedgerExists(TestCase):
    def test_the_ledger_file_is_on_disk(self):
        self.assertTrue(
            _LEDGER.is_file(),
            f"{_LEDGER} is missing. Every `# BALANCE:` knob in "
            f"world/combat/constants.py promises a row there; with no "
            f"file the promise is unkept and the numbers are undocumented.",
        )


class TestEveryKnobIsWrittenDown(TestCase):
    """constants.py -> ledger."""

    def setUp(self):
        self.source = _CONSTANTS.read_text(encoding="utf-8")
        self.knobs = _balance_knobs(self.source)

    def test_the_parser_found_the_gravity_knobs(self):
        """A control: a parser that found NOTHING would pass the pin
        below vacuously."""
        self.assertIn("FALL_DAMAGE_PER_STORY", self.knobs)
        self.assertIn("GAP_DIFFICULTY_DEFAULT", self.knobs)
        self.assertGreaterEqual(len(self.knobs), 10)

    def test_a_plain_constant_is_not_mistaken_for_a_knob(self):
        """Control in the other direction: ``DB_FALLING`` sits in the
        same section with a ``#:`` block that does NOT say BALANCE."""
        self.assertNotIn("DB_FALLING", self.knobs)
        self.assertNotIn("NDB_AIRBORNE_TOKEN", self.knobs)

    def test_every_knob_has_a_row_in_the_ledger(self):
        if not _LEDGER.is_file():
            self.fail(f"{_LEDGER} is missing; see TestTheLedgerExists.")
        ledger = _LEDGER.read_text(encoding="utf-8")
        missing = [name for name in self.knobs if name not in ledger]
        self.assertEqual(
            missing, [],
            f"BALANCE knobs with no row in BALANCE_LEDGER.md: {missing}",
        )


class TestTheLedgerDescribesLiveNumbers(TestCase):
    """ledger -> constants.py.

    The first version of this check only looked at names starting
    ``FALL_`` or ``GAP_``, which is the one prefix set the gravity layer
    happens to use. A ledger that is meant to register *every* tunable
    constant in the game cannot have its reverse check scoped to one
    feature's naming convention: the first medical or wage row to be
    renamed out from under its constant would have gone unnoticed.

    So: every backticked ALL-CAPS identifier appearing in a TABLE ROW
    (a line starting ``|``) must exist as a module-level name in
    ``world/combat/constants.py``. Table rows only, because the prose
    above the table discusses the convention itself rather than naming
    live constants.
    """

    def _rows(self):
        return [line for line in _LEDGER.read_text(encoding="utf-8").splitlines()
                if line.startswith("|")]

    def _quoted(self):
        names = set()
        for row in self._rows():
            names |= set(_TABLE_NAME.findall(row))
        return names

    def test_the_ledger_has_a_table_at_all(self):
        if not _LEDGER.is_file():
            self.fail(f"{_LEDGER} is missing; see TestTheLedgerExists.")
        self.assertGreater(
            len(self._rows()), 3,
            "BALANCE_LEDGER.md has no table -- the register is the table",
        )

    def test_the_extractor_finds_the_names(self):
        """Control: an extractor that found nothing would pass the pin
        below against any ledger at all, including an empty one."""
        if not _LEDGER.is_file():
            self.fail(f"{_LEDGER} is missing; see TestTheLedgerExists.")
        quoted = self._quoted()
        self.assertIn("FALL_DAMAGE_PER_STORY", quoted)
        self.assertGreaterEqual(len(quoted), 10)

    def test_it_does_not_mistake_a_document_name_for_a_constant(self):
        """``PARKOUR_TEMPLATE_LIBRARY.md`` is cited in a row; a pattern
        that swallowed the extension would demand a constant by that
        name."""
        self.assertEqual(
            _TABLE_NAME.findall("| see `PARKOUR_TEMPLATE_LIBRARY.md` §1 |"),
            [])
        self.assertEqual(
            _TABLE_NAME.findall("| `edge_difficulty` and `FALL_MAX_CELLS` |"),
            ["FALL_MAX_CELLS"])

    def test_every_name_it_quotes_still_exists(self):
        if not _LEDGER.is_file():
            self.fail(f"{_LEDGER} is missing; see TestTheLedgerExists.")
        from world.combat import constants

        gone = sorted(n for n in self._quoted() if not hasattr(constants, n))
        self.assertEqual(
            gone, [],
            f"BALANCE_LEDGER.md table rows name constants that do not "
            f"exist in world/combat/constants.py: {gone}. A row outlives "
            f"its constant only when the removal PR forgot the ledger.",
        )
