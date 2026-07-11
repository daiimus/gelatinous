"""Tests for the crime-report funnel (slices 2+3): crowd-gated witness,
crime-time BOLO snapshot, per-scene debounce, lawful-force exclusion."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import crime as cmod
from world.director.crime import CRIME_SEVERITY, report_crime


class _Room:
    def __init__(self, name):
        self.name = name


class _Char:
    def __init__(self, name, role=None, uid="UID", height="tall", build="lean"):
        self.name = name
        self.uid = uid
        self.height = height
        self.build = build
        self.db = SimpleNamespace(role=role)


class TestReportCrime(TestCase):
    def setUp(self):
        cmod._RECENT.clear()

    def tearDown(self):
        cmod._RECENT.clear()

    @patch("world.director.crime.build_bolo",
           side_effect=lambda p: {"uid": getattr(p, "uid", None)})
    @patch("world.director.crime.spawn_witness")
    @patch("world.director.crime.delay")
    def test_witnessed_crime_hands_window_to_witness(
            self, mock_delay, mock_spawn, _bolo):
        witness = MagicMock(name="witness")
        mock_spawn.return_value = witness
        perp = _Char("perp", uid="AT_CRIME_TIME")
        self.assertTrue(report_crime("assault", _Room("scene"), perp=perp))
        secs, fn, w, event = mock_delay.call_args.args
        self.assertEqual(secs, cmod.WITNESS_REPORT_DELAY)
        self.assertIs(fn, cmod.witness_report)
        self.assertIs(w, witness)
        self.assertEqual(event.type, "assault")
        self.assertEqual(event.severity, CRIME_SEVERITY["assault"])
        # BOLO captured NOW — changing presentation later can't touch it.
        self.assertEqual(event.payload["bolo"], {"uid": "AT_CRIME_TIME"})

    @patch("world.director.crime.spawn_witness", return_value=None)
    @patch("world.director.crime.delay")
    def test_no_witness_no_report_ever(self, mock_delay, _spawn):
        # The empty alley is free — no event is even built.
        self.assertFalse(report_crime("assault", _Room("alley"),
                                      perp=_Char("perp")))
        mock_delay.assert_not_called()

    @patch("world.director.crime.spawn_witness", return_value=None)
    @patch("world.director.crime.delay")
    def test_unwitnessed_scene_still_debounced(self, mock_delay, mock_spawn):
        # The same brawl doesn't re-roll a witness every swing.
        scene = _Room("scene")
        report_crime("assault", scene)
        report_crime("assault", scene)
        self.assertEqual(mock_spawn.call_count, 1)

    @patch("world.director.crime.spawn_witness", return_value=MagicMock())
    @patch("world.director.crime.build_bolo", return_value=None)
    @patch("world.director.crime.delay")
    def test_debounce_one_report_per_scene(self, mock_delay, _b, _s):
        scene = _Room("scene")
        self.assertTrue(report_crime("assault", scene, perp=_Char("a")))
        self.assertFalse(report_crime("assault", scene, perp=_Char("b")))
        self.assertEqual(mock_delay.call_count, 1)
        # a different crime type at the same scene is its own incident
        self.assertTrue(report_crime("vandalism", scene, perp=_Char("c")))

    @patch("world.director.crime.spawn_witness", return_value=MagicMock())
    @patch("world.director.crime.build_bolo", return_value=None)
    @patch("world.director.crime.delay")
    def test_debounce_expires(self, mock_delay, _b, _s):
        scene = _Room("scene")
        report_crime("assault", scene)
        cmod._RECENT[(scene, "assault")] -= cmod.REPORT_DEBOUNCE + 1
        self.assertTrue(report_crime("assault", scene))

    @patch("world.director.crime.spawn_witness")
    @patch("world.director.crime.delay")
    def test_security_actions_are_lawful(self, mock_delay, mock_spawn):
        bot = _Char("bot", role="security")
        self.assertFalse(report_crime("assault", _Room("scene"), perp=bot))
        mock_spawn.assert_not_called()
        mock_delay.assert_not_called()

    @patch("world.director.crime.delay")
    def test_no_location_no_report(self, mock_delay):
        self.assertFalse(report_crime("assault", None))
        mock_delay.assert_not_called()

    def test_taxonomy_ladder_shape(self):
        # frugal ladder: violence scales, everything else sends one
        self.assertEqual(CRIME_SEVERITY["murder"], 3)
        self.assertEqual(CRIME_SEVERITY["shoplifting"], 1)
        self.assertEqual(CRIME_SEVERITY["sabotage"], 1)
        self.assertGreater(CRIME_SEVERITY["robbery"], CRIME_SEVERITY["pickpocketing"])
        self.assertEqual(max(CRIME_SEVERITY.values()), 3)
