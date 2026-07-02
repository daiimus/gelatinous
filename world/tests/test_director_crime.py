"""Tests for the crime-report funnel (slice 2): delayed delivery,
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
    @patch("world.director.crime.delay")
    def test_report_schedules_delayed_delivery_with_crime_time_bolo(
            self, mock_delay, _bolo):
        perp = _Char("perp", uid="AT_CRIME_TIME")
        self.assertTrue(report_crime("assault", _Room("scene"), perp=perp))
        mock_delay.assert_called_once()
        secs, fn, event = mock_delay.call_args.args
        self.assertEqual(secs, cmod.REPORT_DELAY)
        self.assertIs(fn, cmod._deliver)
        self.assertEqual(event.type, "assault")
        self.assertEqual(event.severity, CRIME_SEVERITY["assault"])
        # BOLO captured NOW — changing presentation later can't touch it.
        self.assertEqual(event.payload["bolo"], {"uid": "AT_CRIME_TIME"})

    @patch("world.director.crime.build_bolo", return_value=None)
    @patch("world.director.crime.delay")
    def test_debounce_one_report_per_scene(self, mock_delay, _b):
        scene = _Room("scene")
        self.assertTrue(report_crime("assault", scene, perp=_Char("a")))
        # the brawl continues — the counter-attacker does NOT file a second
        self.assertFalse(report_crime("assault", scene, perp=_Char("b")))
        self.assertEqual(mock_delay.call_count, 1)
        # a different crime type at the same scene is its own incident
        self.assertTrue(report_crime("vandalism", scene, perp=_Char("c")))

    @patch("world.director.crime.build_bolo", return_value=None)
    @patch("world.director.crime.delay")
    def test_debounce_expires(self, mock_delay, _b):
        scene = _Room("scene")
        report_crime("assault", scene)
        cmod._RECENT[(scene, "assault")] -= cmod.REPORT_DEBOUNCE + 1
        self.assertTrue(report_crime("assault", scene))

    @patch("world.director.crime.delay")
    def test_security_actions_are_lawful(self, mock_delay):
        bot = _Char("bot", role="security")
        self.assertFalse(report_crime("assault", _Room("scene"), perp=bot))
        mock_delay.assert_not_called()

    @patch("world.director.crime.delay")
    def test_no_location_no_report(self, mock_delay):
        self.assertFalse(report_crime("assault", None))
        mock_delay.assert_not_called()

    @patch("world.director.crime.raise_event")
    def test_deliver_hands_to_dispatcher(self, mock_raise):
        event = MagicMock()
        cmod._deliver(event)
        mock_raise.assert_called_once_with(event)

    @patch("world.director.crime.raise_event", side_effect=RuntimeError)
    def test_deliver_never_raises(self, _r):
        cmod._deliver(MagicMock())  # must not blow up inside delay

    def test_taxonomy_ladder_shape(self):
        self.assertEqual(CRIME_SEVERITY["murder"], 5)
        self.assertEqual(CRIME_SEVERITY["shoplifting"], 1)
        self.assertGreater(CRIME_SEVERITY["robbery"], CRIME_SEVERITY["pickpocketing"])
