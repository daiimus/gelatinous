"""The station must not read registry keys on air (#2785).

`_cue` interpolated `get_current_time_period()` straight into broadcast
prose. Those are identifiers from a fixed vocabulary, so for 18 of every
24 hours the station was saying:

    "It is late_evening in the colony; the weather is clear."

The weather half has the same defect, which the issue did not notice:
11 of the 19 weather values are underscored identifiers, so it would
also read "the weather is dry_thunderstorm" on air.

De-underscored rather than hand-mapped: every value reads correctly that
way, and a lookup table would fall back to the raw key the first time
somebody adds a period or a weather type — which is the exact failure
being fixed.
"""
from unittest import TestCase, mock

from world.director import broadcasts
# `world.weather.time_system` the NAME is a TimeSystem instance, not the
# module — the package __init__ shadows the submodule (#2754 family). The
# instance is what `_cue` calls the getters on, so it is what the tests
# patch; the helpers come from the real submodule path.
from world.weather import time_system as time_instance
from world.weather import weather_system as weather_instance
from world.weather.time_system import TIME_PERIODS, spoken_period
from world.weather.weather_messages import WEATHER_INTENSITY
from world.weather.weather_system import spoken_weather


class TestNoRegistryKeysReachTheAir(TestCase):
    def test_every_time_period_is_speakable(self):
        for period in TIME_PERIODS:
            with self.subTest(period=period):
                self.assertNotIn("_", spoken_period(period))

    def test_every_weather_type_is_speakable(self):
        for weather in WEATHER_INTENSITY:
            with self.subTest(weather=weather):
                self.assertNotIn("_", spoken_weather(weather))

    def test_the_reported_case_reads_as_prose(self):
        self.assertEqual(spoken_period("late_evening"), "late evening")

    def test_a_multiword_weather_reads_as_prose(self):
        self.assertEqual(spoken_weather("dry_thunderstorm"),
                         "dry thunderstorm")

    def test_single_word_values_are_untouched(self):
        """The pin: most values are already fine and must stay so."""
        self.assertEqual(spoken_period("dawn"), "dawn")
        self.assertEqual(spoken_weather("clear"), "clear")

    def test_empty_values_pass_through(self):
        for empty in (None, ""):
            self.assertEqual(spoken_period(empty), empty)
            self.assertEqual(spoken_weather(empty), empty)


class TestTheCueLineItself(TestCase):
    def _cue_with(self, period, weather):
        with mock.patch.object(time_instance, "get_current_time_period",
                               return_value=period), \
             mock.patch.object(weather_instance, "get_current_weather",
                               return_value=weather):
            return broadcasts._cue()

    def test_the_line_carries_no_underscores(self):
        line = self._cue_with("late_evening", "dry_thunderstorm")
        self.assertNotIn("_", line)

    def test_the_line_still_says_both_things(self):
        line = self._cue_with("late_evening", "dry_thunderstorm")
        self.assertIn("late evening", line)
        self.assertIn("dry thunderstorm", line)

    def test_no_weather_omits_the_clause(self):
        line = self._cue_with("dawn", None)
        self.assertIn("dawn", line)
        self.assertNotIn("the weather is", line)

    def test_a_dead_clock_still_produces_a_line(self):
        """The fallback path already produced prose and must keep doing
        so — the cue never invents more than the world knows."""
        with mock.patch.object(time_instance, "get_current_time_period",
                               side_effect=RuntimeError("clock down")):
            line = broadcasts._cue()
        self.assertIn("in the colony", line)
        self.assertNotIn("_", line)
