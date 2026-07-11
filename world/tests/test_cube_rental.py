"""The cube-hotel housing guarantee: one credit, one permanent
residence, relocation with a handover window (user design 2026-07-11).
Tenancy IS the door grant file — no new lock machinery."""

import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from world.access import is_granted
from world.rental import (
    RELOCATION_WINDOW, assign_cube, is_free, release_with_window,
    residence_of)


def _char(uid="uid-tenant"):
    char = MagicMock()
    char.sleeve_uid = uid
    char.db = SimpleNamespace(residence=None)
    return char


def _cube(key="R1-01", resident=None, grants=None):
    door = MagicMock()
    door.pk = 1
    door.db = SimpleNamespace(access_grants=list(grants or []))
    def mirror(**states):
        for k, v in states.items():
            setattr(door.db, k, v)
    door._mirror = mirror
    cube = MagicMock()
    cube.pk = 1
    cube.key = key
    cube.db = SimpleNamespace(resident=resident, cube_door=door)
    return cube


def _terminal(cubes):
    t = MagicMock()
    t.key = "rental terminal"
    t.db = SimpleNamespace(rental_terminal=True, cubes=list(cubes))
    return t


class TestFirstClaim(TestCase):
    def test_claim_grants_permanent_and_spends_the_credit(self):
        tenant = _char()
        cube = _cube()
        ok, msg = assign_cube(tenant, _terminal([cube]))
        self.assertTrue(ok)
        self.assertIs(cube.db.resident, tenant)
        self.assertIs(tenant.db.residence, cube)
        grants = cube.db.cube_door.db.access_grants
        self.assertTrue(is_granted(tenant, grants))
        self.assertIsNone(grants[-1]["until"])        # permanent
        self.assertIn("yours", msg)

    def test_no_sleeve_no_registration(self):
        ghost = _char(uid=None)
        ok, msg = assign_cube(ghost, _terminal([_cube()]))
        self.assertFalse(ok)
        self.assertIn("no sleeve", msg)

    def test_already_registered_here_is_refused(self):
        tenant = _char()
        cube = _cube()
        assign_cube(tenant, _terminal([cube]))
        ok, msg = assign_cube(tenant, _terminal([cube]))
        self.assertFalse(ok)
        self.assertIn("already", msg)


class TestRelocation(TestCase):
    def test_relocation_windows_the_old_door(self):
        tenant = _char()
        old, new = _cube("R1-01"), _cube("R2-03")
        assign_cube(tenant, _terminal([old]))
        ok, msg = assign_cube(tenant, _terminal([new]))
        self.assertTrue(ok)
        self.assertIs(tenant.db.residence, new)
        self.assertIsNone(old.db.resident)             # vacated now
        old_grant = old.db.cube_door.db.access_grants[0]
        self.assertAlmostEqual(old_grant["until"],
                               time.time() + RELOCATION_WINDOW, delta=5)
        self.assertTrue(is_granted(tenant,
                                   old.db.cube_door.db.access_grants))
        self.assertIn("move your things", msg)

    def test_windowed_cube_stays_off_the_market(self):
        mover, applicant = _char("uid-mover"), _char("uid-applicant")
        cube = _cube()
        assign_cube(mover, _terminal([cube]))
        release_with_window(mover, cube)
        self.assertFalse(is_free(cube))                # handover pending
        ok, msg = assign_cube(applicant, _terminal([cube]))
        self.assertFalse(ok)
        self.assertIn("NO VACANCY", msg)

    def test_expired_window_frees_the_cube(self):
        cube = _cube(grants=[{"sleeve": "uid-old",
                              "until": time.time() - 10,
                              "issued_by": "terminal"}])
        self.assertTrue(is_free(cube))
        applicant = _char("uid-new")
        ok, _ = assign_cube(applicant, _terminal([cube]))
        self.assertTrue(ok)
        grants = cube.db.cube_door.db.access_grants
        self.assertEqual(len(grants), 1)               # stale pruned
        self.assertEqual(grants[0]["sleeve"], "uid-new")


class TestVacancy(TestCase):
    def test_full_hotel_refuses(self):
        landlord = _char("uid-l")
        cube = _cube()
        assign_cube(landlord, _terminal([cube]))
        ok, msg = assign_cube(_char("uid-late"), _terminal([cube]))
        self.assertFalse(ok)
        self.assertIn("NO VACANCY", msg)

    def test_doorless_cube_is_not_rentable(self):
        cube = _cube()
        cube.db.cube_door = None
        self.assertFalse(is_free(cube))


class TestTerminalPressGrammar(TestCase):
    """The kiosk speaks press (user call): press rent on kiosk /
    press confirm on kiosk / bare press = status."""

    def _terminal_obj(self, cubes):
        from types import SimpleNamespace
        from typeclasses.terminals import RentalTerminal
        t = MagicMock()
        t.key = "rental terminal"
        t.db = SimpleNamespace(pressable=True, rental_terminal=True,
                               cubes=list(cubes))
        for name in ("at_press", "_press_rent", "_press_status", "_cubes"):
            setattr(t, name,
                    getattr(RentalTerminal, name).__get__(t, RentalTerminal))
        return t

    def test_press_rent_claims(self):
        tenant = _char()
        cube = _cube()
        terminal = self._terminal_obj([cube])
        self.assertTrue(terminal.at_press(tenant, "rent"))
        self.assertIs(tenant.db.residence, cube)
        self.assertIn("yours", tenant.msg.call_args_list[-1].args[0])

    def test_relocation_wants_explicit_confirm(self):
        tenant = _char()
        old, new = _cube("R1-01"), _cube("R2-02")
        old_terminal = self._terminal_obj([old])
        old_terminal.at_press(tenant, "rent")
        new_terminal = self._terminal_obj([new])
        self.assertTrue(new_terminal.at_press(tenant, "rent"))
        self.assertIs(tenant.db.residence, old)        # not yet moved
        self.assertIn("press confirm on kiosk",
                      tenant.msg.call_args.args[0])
        self.assertTrue(new_terminal.at_press(tenant, "confirm"))
        self.assertIs(tenant.db.residence, new)

    def test_bare_press_reads_status(self):
        tenant = _char()
        terminal = self._terminal_obj([_cube()])
        self.assertTrue(terminal.at_press(tenant, None))
        self.assertIn("unspent", tenant.msg.call_args.args[0])

    def test_unknown_button_is_not_ours(self):
        terminal = self._terminal_obj([_cube()])
        self.assertFalse(terminal.at_press(_char(), "jackpot"))


class TestResidenceReport(TestCase):
    """`memory`'s REGISTERED RESIDENCE dossier data."""

    def _cube(self, key="R0-01"):
        cube = MagicMock()
        cube.pk = 42
        cube.key = key
        cube.db.residence_building = "Queen of Cups"
        cube.db.residence_origin = "Pessoa Street"
        return cube

    def test_full_dossier(self):
        from world.rental import residence_report
        char = MagicMock()
        char.db.residence = self._cube()
        char.db.residence_handover = None
        char.db.residence_registered_at = "2026-07-11T00:00:00"
        report = residence_report(char)
        self.assertEqual(report["unit"], "R0-01")
        self.assertEqual(report["building"], "Queen of Cups")
        self.assertEqual(report["origin"], "Pessoa Street")
        self.assertIsNone(report["handover"])

    def test_live_handover_window(self):
        import time as _time
        from world.rental import residence_report
        char = MagicMock()
        char.db.residence = self._cube("R1-03")
        old = self._cube("R0-01")
        char.db.residence_handover = {"cube": old,
                                      "until": _time.time() + 7200}
        report = residence_report(char)
        self.assertEqual(report["handover"]["unit"], "R0-01")
        self.assertEqual(report["handover"]["hours_left"], 2)

    def test_expired_handover_prunes(self):
        import time as _time
        from world.rental import residence_report
        char = MagicMock()
        char.db.residence = self._cube()
        char.db.residence_handover = {"cube": self._cube("R0-02"),
                                      "until": _time.time() - 5}
        report = residence_report(char)
        self.assertIsNone(report["handover"])
        self.assertIsNone(char.db.residence_handover)

    def test_unspent_credit(self):
        from world.rental import residence_report
        char = MagicMock()
        char.db.residence = None
        self.assertIsNone(residence_report(char))


class TestMemoryReportPanel(TestCase):
    """The @stats-format panel renderer."""

    def test_rows_pad_to_uniform_width(self):
        import re
        from commands.CmdCharacter import _report_panel
        panel = _report_panel(["MNEMONIC RECALL REPORT", None,
                               "REGISTERED RESIDENCE", "Unit: R0-01"])
        widths = {len(re.sub(r"\|.", "", line))
                  for line in panel.splitlines()}
        self.assertEqual(len(widths), 1)          # every row same width
        self.assertEqual(panel.count("MNEMONIC"), 1)

    def test_residence_rows_render_dossier(self):
        from unittest.mock import patch
        from commands.CmdCharacter import _residence_rows
        report = {"unit": "R0-01", "building": "Queen of Cups",
                  "origin": "Pessoa Street",
                  "registered_at": "2026-07-11T00:00:00",
                  "handover": {"unit": "R4-05", "hours_left": 46}}
        with patch("world.rental.residence_report", return_value=report):
            rows = _residence_rows(MagicMock())
        joined = "\n".join(rows)
        self.assertIn("Queen of Cups", joined)
        self.assertIn("Pessoa Street", joined)
        self.assertIn("R4-05 answers your sleeve 46h more", joined)

    def test_no_residence(self):
        from unittest.mock import patch
        from commands.CmdCharacter import _residence_rows
        with patch("world.rental.residence_report", return_value=None):
            rows = _residence_rows(MagicMock())
        self.assertEqual(rows, ["None on file."])
