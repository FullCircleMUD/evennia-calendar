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
    _day_of_year,
    _year,
    game_date,
)
from evennia_calendar.config import (
    DEFAULT_STARTING_YEAR,
    SECONDS_PER_GAME_DAY,
    SETTING_STARTING_YEAR,
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


class GameDateTests(SimpleTestCase):
    """GD — the frozen result, and the factory that composes one."""

    def test_gd_01_the_dataclass_is_frozen(self):
        """GD-01"""
        date = GameDate(year=850, day_of_year=0)
        with self.assertRaises(FrozenInstanceError):
            date.year = 851

    @override_settings(CALENDAR_STARTING_YEAR=850)
    def test_gd_02_the_factory_reads_the_clock_and_composes_both_fields(self):
        """GD-02"""
        elapsed = SECONDS_PER_GAME_DAY * 725
        with mock.patch(
            "evennia_calendar.clock.gametime", return_value=elapsed
        ) as clock:
            date = game_date()

        clock.assert_called_once_with(absolute=False)
        self.assertEqual(date.year, 852)
        self.assertEqual(date.day_of_year, 5)

    def test_gd_03_the_year_comes_through_the_accessor(self):
        """GD-03"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            date = game_date()

        self.assertEqual(date.year, DEFAULT_STARTING_YEAR)
