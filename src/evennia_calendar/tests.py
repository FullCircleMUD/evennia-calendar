# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for evennia-calendar. Run via ``python runtests.py``.

Every test carries its case ID from docs/test-plan.md as its docstring, so
the coverage trail reads in both directions.
"""

from unittest import TestCase, mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

import evennia_calendar
from evennia_calendar.config import (
    DEFAULT_STARTING_YEAR,
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
