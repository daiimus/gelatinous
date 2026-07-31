"""Tests for the colony clock (TIME_SYSTEM_SPEC)."""

from datetime import datetime, timedelta, timezone
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world import gametime


class TestColonyClock(EvenniaTest):
    """The three facts: 1:1, fixed UTC-8, +1200 years."""

    def _at(self, iso_utc):
        """Pin real UTC to a known instant."""
        moment = datetime.fromisoformat(iso_utc).replace(tzinfo=timezone.utc)
        return mock.patch.object(gametime, "_real_utc", return_value=moment)

    def test_year_is_offset(self):
        with self._at("2026-07-30T12:00:00"):
            self.assertEqual(gametime.tst_now().year, 3226)

    def test_offset_preserves_month_and_day(self):
        """Same calendar date, so conversion is one field and never drifts."""
        with self._at("2026-07-30T12:00:00"):
            real = datetime(2026, 7, 30, 12, tzinfo=timezone.utc)
            tst = gametime.tst_now()
            self.assertEqual((tst.month, tst.day), (real.month, real.day))

    def test_weekday_alignment_depends_on_the_offset(self):
        """
        The Gregorian calendar repeats every 400 years, so ONLY multiples of
        400 keep the weekday. +1000 does not; +1200 would. Nothing in the game
        would, so this pins the fact. The offset is 1200 precisely so this
        passes the aligned branch; if someone changes it to a non-multiple of
        400 this test still passes, but the game quietly loses weekday
        alignment — which is why the constant carries a warning too.
        """
        from datetime import date
        aligned = date(2026, 7, 30).weekday() == date(
            2026 + gametime.TST_YEAR_OFFSET, 7, 30).weekday()
        self.assertEqual(aligned, gametime.TST_YEAR_OFFSET % 400 == 0)

    def test_colony_is_utc_minus_eight(self):
        with self._at("2026-07-30T12:00:00"):
            self.assertEqual(gametime.colony_hour(), 4)

    def test_colony_date_rolls_back_across_midnight_utc(self):
        """03:00 UTC is still the previous evening in the colony."""
        with self._at("2026-07-31T03:00:00"):
            local = gametime.colony_now()
            self.assertEqual(local.hour, 19)
            self.assertEqual(local.day, 30)

    def test_no_daylight_saving(self):
        """Midsummer and midwinter share the same offset. That is the point."""
        with self._at("2026-01-15T12:00:00"):
            winter = gametime.colony_hour()
        with self._at("2026-07-15T12:00:00"):
            summer = gametime.colony_hour()
        self.assertEqual(winter, summer)

    def test_colony_year_counts_from_planetfall(self):
        with self._at("2026-07-30T12:00:00"):
            self.assertEqual(gametime.colony_year(), 3226 - 3165)

    def test_leap_day_passes_straight_through(self):
        """Feb 29 stays Feb 29 — see the leap-status test below for why."""
        for instant in ("2028-02-29T12:00:00", "2000-02-29T12:00:00"):
            with self.subTest(instant=instant), self._at(instant):
                moment = gametime.tst_now()
                self.assertEqual((moment.month, moment.day), (2, 29))

    def test_a_400_multiple_offset_also_preserves_leap_years(self):
        """
        Falling out of the 400-year cycle: leap rules depend on the year mod
        4, 100 and 400, so an offset divisible by 400 cannot change whether a
        year is leap. With 1200, Feb 29 always has a Feb 29 to land on and the
        fallback in _shift_year is unreachable.
        """
        import calendar
        self.assertEqual(gametime.TST_YEAR_OFFSET % 400, 0)
        for year in (2000, 2024, 2028, 2100, 2200, 2400):
            self.assertEqual(
                calendar.isleap(year),
                calendar.isleap(year + gametime.TST_YEAR_OFFSET),
                f"{year} and {year + gametime.TST_YEAR_OFFSET} disagree",
            )

    def test_fallback_protects_a_non_aligned_offset(self):
        """
        The fallback is dead code today, but it is the difference between a
        crash and a sane date if the offset is ever changed. 2000 is leap,
        3000 is not.
        """
        with mock.patch.object(gametime, "TST_YEAR_OFFSET", 1000), \
             self._at("2000-02-29T12:00:00"):
            moment = gametime.tst_now()
            self.assertEqual((moment.month, moment.day), (3, 1))


class TestStamps(EvenniaTest):
    """Stored time is a plain duration-friendly number."""

    def test_stamp_is_real_posix_seconds_not_shifted(self):
        """A stamp a thousand years in the future would break every duration."""
        now = datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(gametime.stamp(), now, delta=5)

    def test_since_measures_elapsed(self):
        self.assertAlmostEqual(gametime.since(1000.0, now=1060.0), 60.0)

    def test_since_never_returns_negative(self):
        self.assertEqual(gametime.since(2000.0, now=1000.0), 0.0)

    def test_since_tolerates_unstamped(self):
        self.assertIsNone(gametime.since(None))

    def test_format_stamp_renders_in_colony_time_and_tst(self):
        moment = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc).timestamp()
        # 12:00 UTC -> 04:00 colony, year +1200
        self.assertEqual(gametime.format_stamp(moment), "3226-07-30 04:00")

    def test_format_stamp_tolerates_unstamped(self):
        self.assertEqual(gametime.format_stamp(None), "unrecorded")


class TestWeatherUsesTheColonyClock(EvenniaTest):
    """Weather, broadcasts and the admin readout must not keep their own clock."""

    def test_weather_hour_is_the_colony_hour(self):
        from world.weather.time_system import TimeSystem

        with mock.patch.object(gametime, "_real_utc",
                               return_value=datetime(2026, 7, 30, 12, 0,
                                                     tzinfo=timezone.utc)):
            self.assertEqual(TimeSystem().get_current_hour(), 4)

    def test_period_follows_the_colony_hour_not_utc(self):
        from world.weather.time_system import get_current_time_period

        # 06:00 UTC is 22:00 in the colony — night, not morning.
        with mock.patch.object(gametime, "_real_utc",
                               return_value=datetime(2026, 7, 30, 6, 0,
                                                     tzinfo=timezone.utc)):
            self.assertNotIn(get_current_time_period(), ("dawn", "morning"))


class TestWoundTimestamp(EvenniaTest):
    """The TODO this work was tracked against."""

    def test_first_damage_stamps_the_wound(self):
        from world.medical.core import Organ

        organ = Organ("heart")
        self.assertIsNone(organ.wound_timestamp)
        organ.take_damage(5, injury_type="cut")
        self.assertIsNotNone(organ.wound_timestamp)
        self.assertAlmostEqual(organ.wound_timestamp, gametime.stamp(), delta=5)


class TestSleeveDatesRenderInColonyTime(EvenniaTest):
    """
    The stored values stay real; only the display shifts.

    This is the whole shape of the fix: no migration touched the records,
    because shifting stored timestamps +1200 years would break every
    duration in the game.
    """

    def test_format_stamp_shifts_a_real_stored_time(self):
        # A real sleeve record: 2025-11-13 05:43 UTC as stored.
        stored = datetime(2025, 11, 13, 5, 43, tzinfo=timezone.utc).timestamp()
        shown = gametime.format_stamp(stored)
        # -> colony local (UTC-8) is the previous evening, year +1200
        self.assertEqual(shown, "3225-11-12 21:43")

    def test_stored_value_is_untouched_by_display(self):
        stored = datetime(2025, 11, 13, 5, 43, tzinfo=timezone.utc).timestamp()
        before = stored
        gametime.format_stamp(stored)
        self.assertEqual(stored, before)

    def test_durations_still_work_on_stored_values(self):
        """The reason we did not migrate: elapsed time must stay sane."""
        born = datetime(2025, 11, 13, 5, 43, tzinfo=timezone.utc).timestamp()
        died = datetime(2025, 11, 13, 5, 45, tzinfo=timezone.utc).timestamp()
        self.assertEqual(gametime.since(born, now=died), 120.0)
