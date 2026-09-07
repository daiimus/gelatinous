""""Traces remain" is only true if something remains (#2601), and a
relocation across buildings still wants a confirm (#2607).

## #2601 — the failed roll deleted the stain

`clean_with_solvent`'s **failed**-roll branch removed
`max(1, n // 2)` incidents. For `n == 1` that is 1 — the only one — and
`_update_description` deletes a pool with no incidents left. So the
stain vanished while the player was told *"Some of the blood stains have
been cleaned, but traces remain."*

The failure branch was reporting the success outcome, and reporting it
wrongly: a scrub that failed its roll erased the evidence completely.

The split now always leaves something:

```
incidents  1 -> removed 0, remaining 1     (refused, and says so)
incidents  2 -> removed 1, remaining 1
incidents  5 -> removed 2, remaining 3
```

A single stain that fails its roll removes nothing and says *"you work
at the stain with solvent, but it resists you"* — a failed scrub is a
failed scrub. Only the **successful** branch deletes the pool, which is
where deletion belongs.

## #2607 — already fixed, pinned here

The report is accurate about the old gate: it asked only *"does the
typed label denote my current cube?"*, never *"is my current cube on
this board?"* — and Brackett units and Halcyon cabins share every unit
label. A Brackett 9B tenant pressing `rent 9b` at the **Halcyon** kiosk
matched their own Brackett cube, the gate concluded *"not relocating"*,
and they were moved across the colony on one keystroke, with the old
lease already released into a 48-hour window.

`current in cubes` now comes **first**, fixed under #2457. Run over the
issue's own scenario:

```
Brackett tenant, 'rent 9b' at HALCYON    old: relocating=False   now: True
Brackett tenant, 'rent 9b' at BRACKETT   old: relocating=False   now: False
Brackett tenant, 'rent 10a' at BRACKETT  old: relocating=True    now: True
```

Pinned rather than closed on a reading, because the difference between
those two boolean expressions is one line and easy to undo.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.access import sleeve_uid_of


def _relocating(current, cubes, unit):
    """The gate as `terminals.py` now expresses it."""
    from world.rental import unit_matches
    return current is not None and not (
        current in cubes
        and (not unit or unit_matches(current, unit)))


def _old_relocating(current, cubes, unit):
    """As it was — kept so the defect is demonstrated, not described."""
    from world.rental import unit_matches
    return current is not None and not (
        (unit and unit_matches(current, unit))
        or (not unit and current in cubes))


class _PoolCase(EvenniaTest):
    def pool(self, incidents):
        import time
        obj = create_object("typeclasses.objects.BloodPool",
                            key="blood stains", location=self.room1)
        obj.db.bleeding_incidents = [
            {"character": f"someone{i}", "severity": 3,
             "timestamp": time.time(), "sleeve_uid": f"s{i}"}
            for i in range(incidents)
        ]
        obj.db.total_volume = 3 * incidents
        return obj

    def solvent(self):
        obj = create_object("typeclasses.items.Item", key="a solvent can",
                            location=self.char1)
        obj.db.solvent_strength = 1
        return obj

    def fail_the_roll(self):
        from unittest import mock
        # effectiveness is at least 20, so 101 always fails
        return mock.patch("typeclasses.objects.random.randint",
                          return_value=101)


class TestAFailedScrubLeavesTheStain(_PoolCase):
    def test_a_single_incident_pool_survives(self):
        pool = self.pool(1)
        with self.fail_the_roll():
            pool.clean_with_solvent(self.solvent())
        self.assertTrue(pool.pk, "a failed scrub deleted the stain")

    def test_and_keeps_its_incident(self):
        pool = self.pool(1)
        with self.fail_the_roll():
            pool.clean_with_solvent(self.solvent())
        self.assertEqual(len(pool.db.bleeding_incidents or []), 1)

    def test_it_says_the_stain_resisted(self):
        pool = self.pool(1)
        with self.fail_the_roll():
            _vol, msg = pool.clean_with_solvent(self.solvent())
        self.assertIn("resists", msg)
        self.assertNotIn("traces remain", msg)

    def test_it_reports_removing_nothing(self):
        pool = self.pool(1)
        with self.fail_the_roll():
            vol, _msg = pool.clean_with_solvent(self.solvent())
        self.assertEqual(vol, 0)


class TestAPartialCleanStillWorks(_PoolCase):
    """The fix must not stop partial cleans happening."""

    def test_two_incidents_lose_one(self):
        pool = self.pool(2)
        with self.fail_the_roll():
            pool.clean_with_solvent(self.solvent())
        self.assertEqual(len(pool.db.bleeding_incidents or []), 1)

    def test_five_incidents_lose_two(self):
        pool = self.pool(5)
        with self.fail_the_roll():
            pool.clean_with_solvent(self.solvent())
        self.assertEqual(len(pool.db.bleeding_incidents or []), 3)

    def test_the_message_is_honest_when_traces_do_remain(self):
        pool = self.pool(4)
        with self.fail_the_roll():
            _vol, msg = pool.clean_with_solvent(self.solvent())
        self.assertIn("traces remain", msg)
        self.assertTrue(pool.db.bleeding_incidents)

    def test_the_arithmetic_never_empties_the_pool(self):
        for total in range(1, 12):
            removed = min(max(1, total // 2), max(0, total - 1))
            self.assertLess(removed, total, f"{total} would be emptied")


class TestOnlySuccessDeletes(_PoolCase):
    def test_a_successful_clean_removes_the_pool(self):
        from unittest import mock
        pool = self.pool(1)
        with mock.patch("typeclasses.objects.random.randint",
                        return_value=1):
            _vol, msg = pool.clean_with_solvent(self.solvent())
        self.assertFalse(pool.pk)
        self.assertIn("successfully cleaned", msg)


class TestTheRelocationGateStillAsksBothQuestions(EvenniaTest):
    """Real cube objects, not strings: `unit_matches` reads `cube.key`,
    and a string fixture only proves something about strings."""

    def cube(self, key):
        return create_object("typeclasses.rooms.Room", key=key,
                             location=None)

    def setUp(self):
        super().setUp()
        self.brackett = self.cube("The Brackett Arms - Unit 9B")
        self.brackett_other = self.cube("The Brackett Arms - Unit 10A")
        self.halcyon = self.cube("The Halcyon Cabin 9B")

    def test_the_cross_building_press_now_wants_a_confirm(self):
        self.assertTrue(
            _relocating(self.brackett, [self.halcyon], "9b"))

    def test_the_old_gate_waved_it_through(self):
        """Demonstrated, not described: both cubes answer to "9b"."""
        self.assertFalse(
            _old_relocating(self.brackett, [self.halcyon], "9b"))

    def test_the_labels_really_do_collide(self):
        from world.rental import unit_matches
        self.assertTrue(unit_matches(self.brackett, "9b"))
        self.assertTrue(unit_matches(self.halcyon, "9b"))

    def test_your_own_cube_on_your_own_board_needs_no_confirm(self):
        self.assertFalse(
            _relocating(self.brackett, [self.brackett], "9b"))

    def test_a_bare_press_at_your_own_board_needs_no_confirm(self):
        self.assertFalse(
            _relocating(self.brackett, [self.brackett], None))

    def test_a_bare_press_elsewhere_does(self):
        self.assertTrue(
            _relocating(self.brackett, [self.halcyon], None))

    def test_a_different_unit_on_your_own_board_does(self):
        self.assertTrue(
            _relocating(self.brackett,
                        [self.brackett, self.brackett_other], "10a"))

    def test_someone_with_no_cube_is_never_relocating(self):
        self.assertFalse(_relocating(None, [self.halcyon], "9b"))

    def test_the_source_checks_the_board_first(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "terminals.py").read_text(
            errors="ignore")
        start = body.index("relocating = current is not None")
        window = body[start:start + 200]
        self.assertIn("current in cubes", window)
        self.assertLess(window.index("current in cubes"),
                        window.index("unit_matches"))


class TestTheKioskItself(EvenniaTest):
    """Driven through `at_press`, the way a player reaches it — the
    expressions above are transcriptions, and a transcription can agree
    with itself while the machine disagrees with both."""

    def cube(self, key):
        """A cube with a DOOR. `is_free` refuses a doorless cube, so a
        fixture without one makes every claim fail for the wrong
        reason -- which is how my first version of this passed on the
        gate tests while the confirm test failed silently."""
        room = create_object("typeclasses.rooms.Room", key=key)
        door = create_object("typeclasses.doors.DoorExit", key="door",
                             location=self.room1, destination=room)
        room.db.cube_door = door
        return room

    def setUp(self):
        super().setUp()
        self.brackett = self.cube("The Brackett Arms - Unit 9B")
        self.halcyon = self.cube("The Halcyon Cabin 9B")
        self.kiosk = create_object("typeclasses.terminals.RentalTerminal",
                                   key="a rental kiosk",
                                   location=self.room1)
        self.kiosk.db.cubes = [self.halcyon]
        self.char1.db.residence = self.brackett
        self.brackett.db.resident = self.char1
        # `assign_cube` refuses a sleeveless presser outright, so
        # without this the confirm path "passes" by never running.
        self.assertIsNotNone(sleeve_uid_of(self.char1))
        from world.rental import is_free
        self.assertTrue(is_free(self.halcyon),
                        "fixture: the target cube must be claimable")

    def press(self, arg):
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        self.kiosk.at_press(self.char1, arg)
        return "\n".join(said)

    def test_pressing_rent_9b_at_the_halcyon_asks_first(self):
        self.assertIn("relocates you", self.press("rent 9b"))

    def test_it_names_the_cube_you_would_be_giving_up(self):
        self.assertIn("Brackett", self.press("rent 9b"))

    def test_it_does_not_move_you_on_that_press(self):
        self.press("rent 9b")
        self.assertEqual(self.char1.db.residence, self.brackett)

    def test_a_bare_press_at_a_foreign_board_asks_too(self):
        self.assertIn("relocates you", self.press("rent"))

    def test_confirm_goes_through(self):
        self.press("rent 9b")
        self.press("confirm 9b")
        self.assertEqual(self.char1.db.residence, self.halcyon)

    def test_your_own_board_does_not_ask(self):
        self.kiosk.db.cubes = [self.brackett]
        self.assertNotIn("relocates you", self.press("rent 9b"))


class TestTheCommandSaysTheScrubHappened(EvenniaTest):
    """`_apply_solvent` discards the pool's message and gates on volume,
    so a failed single-stain scrub fell through to "the solvent doesn't
    seem to affect anything here" — which reads as "there is no blood
    here" to someone standing over a pool of it.

    Driven at `_apply_solvent`, the RESOLUTION, because cleaning is
    channeled: `_handle_clean_with_solvent` only starts the channel and
    the blood never breaks down until the dwell completes.
    """

    def setUp(self):
        super().setUp()
        import time
        self.pool = create_object("typeclasses.objects.BloodPool",
                                  key="blood stains", location=self.room1)
        self.pool.db.bleeding_incidents = [{
            "character": "someone", "severity": 4,
            "timestamp": time.time(), "sleeve_uid": "s1"}]
        self.pool.db.total_volume = 4
        self.can = create_object("typeclasses.items.SolventCanItem",
                                 key="a solvent can", location=self.char1)
        self.can.db.aerosol_level = 20
        self.char1.location = self.room1

    def scrub(self):
        from unittest import mock
        from commands.CmdGraffiti import CmdGraffiti
        said = []
        cmd = CmdGraffiti()
        cmd.caller = self.char1
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        with mock.patch("typeclasses.objects.random.randint",
                        return_value=101), \
                mock.patch("commands.CmdGraffiti.msg_room_identity"), \
                mock.patch("commands.CmdGraffiti.delay"):
            cmd._apply_solvent(self.char1, self.can, 5)
        return "\n".join(said)

    def test_it_does_not_claim_there_is_nothing_here(self):
        self.assertNotIn("doesn't seem to affect anything", self.scrub())

    def test_it_says_the_stain_resisted(self):
        self.assertIn("resists", self.scrub())

    def test_and_the_stain_is_still_there(self):
        self.scrub()
        self.assertTrue(self.pool.pk)

    def test_a_successful_scrub_still_reports_success(self):
        from unittest import mock
        from commands.CmdGraffiti import CmdGraffiti
        said = []
        cmd = CmdGraffiti()
        cmd.caller = self.char1
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        with mock.patch("typeclasses.objects.random.randint",
                        return_value=1), \
                mock.patch("commands.CmdGraffiti.msg_room_identity"), \
                mock.patch("commands.CmdGraffiti.delay"):
            cmd._apply_solvent(self.char1, self.can, 5)
        self.assertIn("You apply solvent", "\n".join(said))
