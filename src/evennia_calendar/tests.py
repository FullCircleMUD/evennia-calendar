# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for evennia-calendar. Run via ``python runtests.py``.

Every test carries its case ID from docs/test-plan.md as its docstring, so
the coverage trail reads in both directions.
"""

from dataclasses import FrozenInstanceError
from unittest import TestCase, mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

import evennia_calendar
from evennia_calendar.clock import (
    GameDate,
    _day_number,
    _day_of_month,
    _day_of_week,
    _day_of_year,
    _hour,
    _minute,
    _month,
    _phase,
    _season,
    _seconds_into_day,
    _week,
    _year,
    game_date,
)
from evennia_calendar.config import (
    DAY_NAMES,
    DEFAULT_STARTING_YEAR,
    MONTH_NAMES,
    PHASE_NAMES,
    SECONDS_PER_GAME_DAY,
    SETTING_STARTING_YEAR,
    Season,
    check_settings,
    get_starting_year,
)
from evennia_calendar.log import calendar_log


class ScaffoldTests(TestCase):
    """SC — the library is installed and the runner reaches it."""

    def test_sc_01_the_package_is_importable_and_versioned(self):
        """SC-01"""
        self.assertTrue(evennia_calendar.__version__)

    def test_sc_02_the_log_shim_is_a_no_op_outside_evennia(self):
        """SC-02"""
        self.assertIsNone(calendar_log("scaffold check"))

    def test_sc_03_the_public_surface_resolves_from_the_package_root(self):
        """SC-03"""
        self.assertIs(evennia_calendar.game_date, game_date)
        self.assertIs(evennia_calendar.GameDate, GameDate)

    def test_sc_04_an_unknown_package_attribute_raises(self):
        """SC-04"""
        with self.assertRaises(AttributeError):
            evennia_calendar.game_dat3


class StartingYearTests(SimpleTestCase):
    """CF — CALENDAR_STARTING_YEAR, its accessor and its boot check.

    ``tests/test_settings.py`` deliberately does not declare the setting, so
    absence is the suite's baseline and a case wanting a value overrides one
    in.
    """

    def test_cf_01_the_accessor_defaults_when_the_setting_is_absent(self):
        """CF-01"""
        self.assertEqual(get_starting_year(), DEFAULT_STARTING_YEAR)

    @override_settings(CALENDAR_STARTING_YEAR=850)
    def test_cf_02_the_accessor_returns_the_declared_value(self):
        """CF-02"""
        self.assertEqual(get_starting_year(), 850)

    def test_cf_03_the_check_passes_when_the_setting_is_absent(self):
        """CF-03"""
        check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=850)
    def test_cf_04_the_check_passes_for_a_positive_integer(self):
        """CF-04"""
        check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=0)
    def test_cf_05_the_check_passes_for_zero(self):
        """CF-05"""
        check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=-1)
    def test_cf_06_the_check_refuses_a_negative_integer(self):
        """CF-06"""
        with self.assertRaises(ImproperlyConfigured):
            check_settings()

    @override_settings(CALENDAR_STARTING_YEAR="1000")
    def test_cf_07_the_check_refuses_a_string(self):
        """CF-07"""
        with self.assertRaises(ImproperlyConfigured):
            check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=1000.0)
    def test_cf_08_the_check_refuses_a_float(self):
        """CF-08"""
        with self.assertRaises(ImproperlyConfigured):
            check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=-1)
    def test_cf_09_the_refusal_names_the_setting(self):
        """CF-09"""
        with self.assertRaises(ImproperlyConfigured) as caught:
            check_settings()
        self.assertIn(SETTING_STARTING_YEAR, str(caught.exception))

    @override_settings(CALENDAR_STARTING_YEAR=True)
    def test_cf_10_the_check_refuses_a_boolean(self):
        """CF-10"""
        with self.assertRaises(ImproperlyConfigured):
            check_settings()

    @override_settings(CALENDAR_STARTING_YEAR=-1)
    def test_cf_11_a_refusal_is_logged_with_the_exception_text(self):
        """CF-11"""
        with mock.patch("evennia_calendar.config.calendar_log") as logged:
            with self.assertRaises(ImproperlyConfigured) as caught:
                check_settings()

        logged.assert_called_once()
        self.assertEqual(logged.call_args.args[0], str(caught.exception))
        self.assertEqual(logged.call_args.kwargs.get("level"), "ERROR")

    def test_cf_12_a_passing_check_logs_nothing(self):
        """CF-12"""
        with mock.patch("evennia_calendar.config.calendar_log") as logged:
            check_settings()

        logged.assert_not_called()


class CalendarNamesTests(TestCase):
    """CN — the calendar's vocabulary."""

    def test_cn_01_there_are_exactly_four_seasons(self):
        """CN-01"""
        self.assertEqual(len(Season), 4)

    def test_cn_02_the_seasons_run_spring_first_with_values_zero_to_three(self):
        """CN-02"""
        self.assertEqual(
            [Season(index).name for index in range(4)],
            ["SPRING", "SUMMER", "AUTUMN", "WINTER"],
        )

    def test_cn_03_there_are_exactly_ten_day_names(self):
        """CN-03"""
        self.assertEqual(len(DAY_NAMES), 10)

    def test_cn_04_there_are_exactly_twelve_month_names(self):
        """CN-04"""
        self.assertEqual(len(MONTH_NAMES), 12)

    def test_cn_05_there_are_exactly_six_phase_names(self):
        """CN-05"""
        self.assertEqual(len(PHASE_NAMES), 6)


class DayNumberTests(TestCase):
    """DN — elapsed game seconds to an absolute day count."""

    def test_dn_01_zero_seconds_is_day_zero(self):
        """DN-01"""
        self.assertEqual(_day_number(0), 0)

    def test_dn_02_one_second_short_of_a_day_is_still_day_zero(self):
        """DN-02"""
        self.assertEqual(_day_number(SECONDS_PER_GAME_DAY - 1), 0)

    def test_dn_03_exactly_one_day_is_day_one(self):
        """DN-03"""
        self.assertEqual(_day_number(SECONDS_PER_GAME_DAY), 1)

    def test_dn_04_it_divides_rather_than_counting_one_boundary(self):
        """DN-04"""
        self.assertEqual(_day_number(SECONDS_PER_GAME_DAY * 725), 725)


class DayOfYearTests(TestCase):
    """DY — an absolute day count to a position within the year."""

    def test_dy_01_day_zero_is_day_of_year_zero(self):
        """DY-01"""
        self.assertEqual(_day_of_year(0), 0)

    def test_dy_02_day_359_is_the_last_day_of_the_year(self):
        """DY-02"""
        self.assertEqual(_day_of_year(359), 359)

    def test_dy_03_day_360_wraps_to_zero(self):
        """DY-03"""
        self.assertEqual(_day_of_year(360), 0)

    def test_dy_04_it_wraps_more_than_once(self):
        """DY-04"""
        self.assertEqual(_day_of_year(725), 5)


class YearTests(TestCase):
    """YR — an absolute day count and a starting year to the year."""

    def test_yr_01_day_zero_is_the_starting_year(self):
        """YR-01"""
        self.assertEqual(_year(0, 850), 850)

    def test_yr_02_day_359_does_not_roll_early(self):
        """YR-02"""
        self.assertEqual(_year(359, 850), 850)

    def test_yr_03_day_360_is_the_next_year(self):
        """YR-03"""
        self.assertEqual(_year(360, 850), 851)

    def test_yr_04_it_divides_rather_than_counting_one_boundary(self):
        """YR-04"""
        self.assertEqual(_year(725, 850), 852)


class MonthTests(TestCase):
    """MO — where in the year by month."""

    def test_mo_01_day_zero_is_the_first_day_of_the_first_month(self):
        """MO-01"""
        self.assertEqual((_month(0), _day_of_month(0)), (0, 0))

    def test_mo_02_day_29_is_the_last_day_of_the_first_month(self):
        """MO-02"""
        self.assertEqual((_month(29), _day_of_month(29)), (0, 29))

    def test_mo_03_day_30_rolls_into_the_second_month(self):
        """MO-03"""
        self.assertEqual((_month(30), _day_of_month(30)), (1, 0))

    def test_mo_04_the_last_day_of_the_year_does_not_run_past_month_eleven(self):
        """MO-04"""
        self.assertEqual((_month(359), _day_of_month(359)), (11, 29))


class WeekTests(TestCase):
    """WK — where in the year by week."""

    def test_wk_01_day_zero_is_the_first_day_of_the_first_week(self):
        """WK-01"""
        self.assertEqual((_week(0), _day_of_week(0)), (0, 0))

    def test_wk_02_day_9_is_the_last_day_of_the_first_week(self):
        """WK-02"""
        self.assertEqual((_week(9), _day_of_week(9)), (0, 9))

    def test_wk_03_day_10_rolls_into_the_second_week(self):
        """WK-03"""
        self.assertEqual((_week(10), _day_of_week(10)), (1, 0))

    def test_wk_04_the_last_day_of_the_year_does_not_run_past_week_35(self):
        """WK-04"""
        self.assertEqual((_week(359), _day_of_week(359)), (35, 9))


class SeasonLookupTests(TestCase):
    """SE — a day of the year to a Season."""

    def test_se_01_day_zero_is_spring(self):
        """SE-01"""
        self.assertIs(_season(0), Season.SPRING)

    def test_se_02_day_89_is_still_spring(self):
        """SE-02"""
        self.assertIs(_season(89), Season.SPRING)

    def test_se_03_day_90_is_summer(self):
        """SE-03"""
        self.assertIs(_season(90), Season.SUMMER)

    def test_se_04_the_last_day_of_the_year_is_winter(self):
        """SE-04"""
        self.assertIs(_season(359), Season.WINTER)


class TimeOfDayTests(TestCase):
    """TD — seconds into the day, and the hour and minute from them."""

    def test_td_01_zero_elapsed_is_zero_seconds_into_the_day(self):
        """TD-01"""
        self.assertEqual(_seconds_into_day(0), 0)

    def test_td_02_it_keeps_what_the_day_number_discards(self):
        """TD-02"""
        self.assertEqual(_seconds_into_day(SECONDS_PER_GAME_DAY + 1), 1)

    def test_td_03_the_start_of_the_day_is_hour_zero_minute_zero(self):
        """TD-03"""
        self.assertEqual((_hour(0), _minute(0)), (0, 0))

    def test_td_04_thirteen_hours_thirty_two_minutes_in(self):
        """TD-04"""
        seconds = 13 * 3600 + 32 * 60
        self.assertEqual((_hour(seconds), _minute(seconds)), (13, 32))

    def test_td_05_the_last_second_of_the_day_does_not_run_over(self):
        """TD-05"""
        last = SECONDS_PER_GAME_DAY - 1
        self.assertEqual((_hour(last), _minute(last)), (23, 59))


class PhaseTests(TestCase):
    """PH — an hour to one of the six four-hour watches."""

    def test_ph_01_hour_zero_is_the_first_watch(self):
        """PH-01"""
        self.assertEqual(_phase(0), 0)

    def test_ph_02_hour_3_is_still_the_first_watch(self):
        """PH-02"""
        self.assertEqual(_phase(3), 0)

    def test_ph_03_hour_4_is_the_second_watch(self):
        """PH-03"""
        self.assertEqual(_phase(4), 1)

    def test_ph_04_the_last_hour_does_not_run_past_the_sixth_watch(self):
        """PH-04"""
        self.assertEqual(_phase(23), 5)


class GameDateTests(SimpleTestCase):
    """GD — the frozen result, and the factory that composes one."""

    def test_gd_01_the_dataclass_is_frozen(self):
        """GD-01"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            date = game_date()

        with self.assertRaises(FrozenInstanceError):
            date.year = 851

    @override_settings(CALENDAR_STARTING_YEAR=850)
    def test_gd_02_the_factory_reads_the_clock_and_composes_every_field(self):
        """GD-02"""
        # Two years and five days on, thirteen hours and thirty-two minutes
        # into that day. Day 5 of a year is month 0 day 5, week 0 day 5, spring.
        elapsed = SECONDS_PER_GAME_DAY * 725 + 13 * 3600 + 32 * 60
        with mock.patch(
            "evennia_calendar.clock.gametime", return_value=elapsed
        ) as clock:
            date = game_date()

        clock.assert_called_once_with(absolute=False)
        self.assertEqual(
            (
                date.year,
                date.day_of_year,
                date.month,
                date.day_of_month,
                date.week,
                date.day_of_week,
                date.season,
                date.hour,
                date.minute,
                date.phase,
            ),
            (852, 6, 1, 6, 1, 6, Season.SPRING, 13, 32, 4),
        )

    def test_gd_03_the_year_comes_through_the_accessor(self):
        """GD-03"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            date = game_date()

        self.assertEqual(date.year, DEFAULT_STARTING_YEAR)
