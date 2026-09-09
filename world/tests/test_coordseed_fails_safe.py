"""The dry run is a safety, so a typo must not remove it (#2573, #2577).

## #2573 — the safety switch failed open

```python
dry = "check" in switches
if not dry:
    for room, coord in assignments.items():
        set_xyz(room, *coord)
```

`dry` was True only for the exact lowercase token `check`. Evennia
**preserves switch case** and the class declared no `switch_options`, so
`/Check`, `/CHECK`, `/chek`, `/dry` all produced `dry = False` — and the
command wrote coordinates to **1,069 live rooms**, reporting *"Seeded
1069 room(s)"*, on the switch whose own help says *"write nothing."*

**Declaring `switch_options` is not enough on its own.** Evennia's
handling of an unmatched switch is to print *"Extra switch ignored"* and
**carry on** — which is the right polarity when a typo merely loses a
feature (#2565, #2569) and the wrong one here, where the typo removes
the guard and the default is the destructive path. So switches are
lower-cased first, and an unrecognised one **aborts**.

## #2577 — /clear was a one-way delete for 319 rooms

It stripped coordinates from every room carrying one, on the premise
that a later seed rebuilds them. Coordinates come from three writers and
the walk is only one:

* the seed walk, which follows **cardinal** exits from the pinned origin
* direct stamping — `@airfill` and ~20 build scripts
* runtime movers — the elevator and crane cars, which carry their own

Rooms reachable only by `in` / `out` / `elevator`, or by no exit at all,
are never visited. Measured live: **1,069 on-grid, 750 reachable, 319
unrecoverable.**

`/clear` now previews that split and does nothing; `/clear/confirm`
performs it. The preview names the number that nothing can restore,
which is the fact the operator needs and did not have.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdCoordSeed import CmdCoordSeed


class _SeedCase(EvenniaCommandTest):
    def run_switches(self, *switches):
        """Drive `func` directly with a given switch list, capturing what
        the caller is told and whether anything was written.

        `all_coordinate_rooms` is stubbed with two rooms: the test
        database has none, so a confirmed clear would loop over an empty
        list and "did nothing" would be true for the wrong reason.
        """
        cmd = CmdCoordSeed()
        cmd.caller = self.char1
        cmd.switches = list(switches)
        cmd.args = ""
        said = []
        self.char1.msg = lambda *a, **k: said.append(str(a[0] if a else ""))
        # An origin MUST be pinned and the walk MUST return assignments,
        # or `func` bails with "No origin is pinned" before reaching the
        # write — and every "it wrote nothing" assertion passes for that
        # reason instead of the one under test.
        with mock.patch("commands.CmdCoordSeed.set_xyz") as wrote, \
             mock.patch("commands.CmdCoordSeed.clear_xyz") as cleared, \
             mock.patch("commands.CmdCoordSeed.all_coordinate_rooms",
                        return_value=[self.room1, self.room2]), \
             mock.patch("commands.CmdCoordSeed.pinned_origin",
                        return_value=self.room1), \
             mock.patch("commands.CmdCoordSeed.seed_coordinates",
                        return_value=({self.room1: (0, 0, 0)}, [])):
            cmd.func()
        return " ".join(said), wrote, cleared


class TestATypoWritesNothing(_SeedCase):
    def test_a_misspelled_check_aborts(self):
        said, wrote, _cleared = self.run_switches("chek")
        wrote.assert_not_called()
        self.assertIn("Unrecognised switch", said)

    def test_an_invented_switch_aborts(self):
        said, wrote, _cleared = self.run_switches("dryrun")
        wrote.assert_not_called()
        self.assertIn("Unrecognised switch", said)

    def test_a_typo_alongside_a_real_switch_still_aborts(self):
        """The dangerous shape: one good switch makes it look fine."""
        said, wrote, cleared = self.run_switches("check", "clera")
        wrote.assert_not_called()
        cleared.assert_not_called()
        self.assertIn("Unrecognised switch", said)


class TestCaseDoesNotMatter(_SeedCase):
    def test_a_bare_run_does_write(self):
        """The control for the two below: with an origin pinned, the
        default path really does write — so "it wrote nothing" means
        something."""
        _said, wrote, _cleared = self.run_switches()
        self.assertTrue(wrote.called, "the write path is unreachable")

    def test_capital_check_is_still_a_dry_run(self):
        said, wrote, _cleared = self.run_switches("Check")
        wrote.assert_not_called()
        self.assertNotIn("Unrecognised switch", said)

    def test_shouted_check_is_still_a_dry_run(self):
        _said, wrote, _cleared = self.run_switches("CHECK")
        wrote.assert_not_called()

    def test_capital_clear_still_previews(self):
        said, _wrote, cleared = self.run_switches("Clear")
        cleared.assert_not_called()
        self.assertIn("would strip", said)


class TestClearPreviewsBeforeItDeletes(_SeedCase):
    def test_bare_clear_deletes_nothing(self):
        _said, _wrote, cleared = self.run_switches("clear")
        cleared.assert_not_called()

    def test_bare_clear_reports_the_one_way_count(self):
        said, _wrote, _cleared = self.run_switches("clear")
        self.assertIn("one-way", said)
        self.assertIn("@coordseed/clear/confirm", said)

    def test_confirm_actually_clears(self):
        _said, _wrote, cleared = self.run_switches("clear", "confirm")
        self.assertEqual(cleared.call_count, 2,
                         "confirmed clear did not clear both rooms")

    def test_confirm_alone_is_not_a_clear(self):
        """`/confirm` without `/clear` must not delete anything."""
        _said, _wrote, cleared = self.run_switches("confirm")
        cleared.assert_not_called()


class TestEvenniaIgnoresUnknownSwitches(EvenniaCommandTest):
    """Why `switch_options` alone was not the fix — pinned against the
    installed Evennia, so if upstream ever starts REFUSING unknown
    switches this local abort becomes redundant and can be dropped."""

    def _parse_source(self):
        import inspect

        from evennia.commands.default.muxcommand import MuxCommand
        return inspect.getsource(MuxCommand.parse)

    def test_an_unmatched_switch_is_only_reported(self):
        src = self._parse_source()
        self.assertIn("Extra switch", src)
        self.assertIn("ignored", src)

    def test_it_compares_the_raw_token(self):
        """Which is why `/Check` missed: the OPTIONS are lower-cased,
        the supplied switch is not."""
        src = self._parse_source()
        self.assertIn("opt.lower() for opt in self.switch_options", src)


class TestTheCommandDeclaresItsSwitches(EvenniaCommandTest):
    def test_every_switch_it_handles_is_declared(self):
        """DECLARED == HANDLED, not a fixed list.

        This asserted the exact set `{check, origin, clear, confirm}`,
        so adding `/force` -- a switch the command genuinely handles --
        failed it, with the invariant intact. Same shape as the count
        pin fixed in #3137: a test that fails when the thing it guards
        is extended properly teaches people to edit the literal.

        Both directions matter here, which is why the sets are compared
        rather than one containment checked:
          * handled but NOT declared -> the unknown-switch abort rejects
            it, so the feature is unreachable;
          * declared but NOT handled -> dead switch, silently ignored.
        """
        import inspect
        import re
        src = inspect.getsource(CmdCoordSeed.func)
        handled = set(re.findall(r'"(\w+)"\s+(?:not\s+)?in\s+switches', src))
        declared = set(CmdCoordSeed.switch_options)
        self.assertTrue(handled, "no switch handling found at all")
        self.assertEqual(
            handled, declared,
            f"handled-but-undeclared: {sorted(handled - declared)}; "
            f"declared-but-dead: {sorted(declared - handled)}")

    def test_the_help_documents_confirm(self):
        self.assertIn("@coordseed/clear/confirm", CmdCoordSeed.__doc__)
