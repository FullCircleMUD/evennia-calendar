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
from evennia_calendar import service
from evennia_calendar.service import (
    _changed_units,
    register_signal,
    start_calendar_clock,
    stop_calendar_clock,
    unregister_signal,
)
from evennia_calendar.signals import (
    day_changed,
    hour_changed,
    month_changed,
    phase_changed,
    season_changed,
    week_changed,
    year_changed,
)

ALL_UNITS = frozenset(
    {"hour", "phase", "day", "week", "month", "season", "year"}
)


def date_at(elapsed_seconds):
    """Build the GameDate for a number of elapsed game seconds.

    Cheaper and safer than hand-writing ten fields: a date built this way
    cannot be internally inconsistent, which one assembled by hand can.
    """
    with mock.patch(
        "evennia_calendar.clock.gametime", return_value=elapsed_seconds
    ):
        return game_date()


class ScaffoldTests(TestCase):
    """SC — the library is installed and the runner reaches it."""

    def test_sc_01_the_package_is_importable_and_versioned(self):
        """SC-01"""
        self.assertTrue(evennia_calendar.__version__)

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


class ChangedUnitsTests(SimpleTestCase):
    """CU — which units turned over between two dates."""

    def test_cu_01_identical_dates_change_nothing(self):
        """CU-01"""
        at_ten = date_at(10 * 3600)
        self.assertEqual(_changed_units(at_ten, at_ten), frozenset())

    def test_cu_02_one_hour_apart_changes_only_the_hour(self):
        """CU-02"""
        # 10:00 to 11:00 — both fall inside the Forenoon watch, so nothing
        # coarser than the hour moves.
        self.assertEqual(
            _changed_units(date_at(10 * 3600), date_at(11 * 3600)),
            frozenset({"hour"}),
        )

    def test_cu_03_the_watch_turns_with_the_hour(self):
        """CU-03"""
        self.assertEqual(
            _changed_units(
                date_at(3 * 3600 + 59 * 60), date_at(4 * 3600)
            ),
            frozenset({"hour", "phase"}),
        )

    def test_cu_04_the_turn_of_a_year_changes_every_unit(self):
        """CU-04"""
        last_hour = 359 * SECONDS_PER_GAME_DAY + 23 * 3600
        self.assertEqual(
            _changed_units(
                date_at(last_hour), date_at(last_hour + 3600)
            ),
            ALL_UNITS,
        )

    def test_cu_05_the_same_day_a_year_apart_is_not_the_same_day(self):
        """CU-05"""
        day_96 = 96 * SECONDS_PER_GAME_DAY
        changed = _changed_units(
            date_at(day_96), date_at(day_96 + 360 * SECONDS_PER_GAME_DAY)
        )
        self.assertIn("day", changed)
        self.assertEqual(changed, ALL_UNITS)


class CalendarClockTests(SimpleTestCase):
    """CK — starting, stopping, remembering, and surviving a raising hook."""

    def tearDown(self):
        stop_calendar_clock()

    @staticmethod
    def _fake_reactor():
        from twisted.internet.task import Clock

        return Clock()

    def test_ck_01_starting_returns_a_running_clock_ticking_every_second(self):
        """CK-01"""
        from twisted.internet.task import LoopingCall

        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            loop = start_calendar_clock(clock=self._fake_reactor())

        self.assertIsInstance(loop, LoopingCall)
        self.assertTrue(loop.running)
        self.assertEqual(loop.interval, 1.0)

    def test_ck_02_starting_again_returns_the_clock_already_running(self):
        """CK-02"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            first = start_calendar_clock(clock=self._fake_reactor())
            second = start_calendar_clock(clock=self._fake_reactor())

        self.assertIs(second, first)

    def test_ck_03_stopping_stops_it_and_a_later_start_is_a_new_clock(self):
        """CK-03"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            first = start_calendar_clock(clock=self._fake_reactor())
            stop_calendar_clock()
            self.assertFalse(first.running)

            second = start_calendar_clock(clock=self._fake_reactor())

        self.assertIsNot(second, first)

    def test_ck_04_stopping_when_nothing_runs_does_nothing(self):
        """CK-04"""
        stop_calendar_clock()  # must not raise

    def test_ck_05_the_first_tick_takes_a_baseline_and_announces_nothing(self):
        """CK-05"""
        reactor = self._fake_reactor()
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            with mock.patch.object(service, "_dispatch") as dispatched:
                start_calendar_clock(clock=reactor)
                reactor.advance(1)

        dispatched.assert_not_called()
        self.assertEqual(service._remembered, date_at(0))

    def test_ck_06_a_tick_with_nothing_turned_over_announces_nothing(self):
        """CK-06"""
        reactor = self._fake_reactor()
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            with mock.patch.object(service, "_dispatch") as dispatched:
                start_calendar_clock(clock=reactor)
                reactor.advance(1)
                reactor.advance(1)

        dispatched.assert_not_called()

    def test_ck_07_a_tick_where_the_hour_turned_announces_it(self):
        """CK-07"""
        reactor = self._fake_reactor()
        before, after = 10 * 3600, 11 * 3600
        with mock.patch(
            "evennia_calendar.clock.gametime", side_effect=[before, after]
        ):
            with mock.patch.object(service, "_dispatch") as dispatched:
                start_calendar_clock(clock=reactor)
                reactor.advance(1)
                reactor.advance(1)

        dispatched.assert_called_once_with(
            date_at(before), date_at(after), frozenset({"hour"})
        )
        self.assertEqual(service._remembered, date_at(after))

    def test_ck_08_a_raising_dispatch_does_not_stop_the_clock(self):
        """CK-08"""
        reactor = self._fake_reactor()
        with mock.patch(
            "evennia_calendar.clock.gametime",
            side_effect=[10 * 3600, 11 * 3600],
        ):
            with mock.patch.object(
                service, "_dispatch", side_effect=RuntimeError("boom")
            ):
                with mock.patch.object(service, "calendar_log") as logged:
                    loop = start_calendar_clock(clock=reactor)
                    reactor.advance(1)
                    reactor.advance(1)

        self.assertTrue(loop.running)

        # Starting the clock logs a line of its own, so look for the refusal
        # rather than counting calls.
        errors = [
            call
            for call in logged.call_args_list
            if call.kwargs.get("level") == "ERROR"
        ]
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].kwargs.get("trace"))


class SignalTests(SimpleTestCase):
    """SG — what a consumer subscribes to, and a receiver that misbehaves."""

    def setUp(self):
        self.received = []

    def tearDown(self):
        stop_calendar_clock()
        for signal, receiver in getattr(self, "_connected", []):
            signal.disconnect(receiver)

    def _connect(self, receiver, signal=hour_changed):
        """Connect a receiver and undo it afterwards.

        Signal connections are module state and outlive a test, so a receiver
        left connected fires in every case that follows.
        """
        self._connected = getattr(self, "_connected", [])
        self._connected.append((signal, receiver))
        signal.connect(receiver)

    def _assert_fires(self, signal, times):
        """Assert ``signal`` reaches a receiver while walking ``times``."""
        def record(sender, previous, current, **kwargs):
            self.received.append(current)

        self._connect(record, signal)
        self._run(times)
        self.assertEqual(len(self.received), 1)

    def _run(self, times):
        """Start the clock, advance it once per entry in ``times``, stop."""
        from twisted.internet.task import Clock

        reactor = Clock()
        with mock.patch(
            "evennia_calendar.clock.gametime", side_effect=times
        ):
            start_calendar_clock(clock=reactor)
            for _ in times:
                reactor.advance(1)
        stop_calendar_clock()

    def test_sg_01_the_hour_turning_sends_the_signal_with_both_dates(self):
        """SG-01"""
        def record(sender, previous, current, **kwargs):
            self.received.append((previous, current))

        self._connect(record)
        before, after = 10 * 3600, 11 * 3600
        self._run([before, after])

        self.assertEqual(self.received, [(date_at(before), date_at(after))])

    def test_sg_02_an_unchanged_hour_sends_nothing(self):
        """SG-02"""
        def record(sender, **kwargs):
            self.received.append(kwargs)

        self._connect(record)
        self._run([10 * 3600, 10 * 3600 + 59])

        self.assertEqual(self.received, [])

    def test_sg_03_a_raising_receiver_is_logged_with_its_traceback(self):
        """SG-03"""
        def explode(sender, **kwargs):
            raise RuntimeError("boom")

        self._connect(explode)
        with mock.patch.object(service, "calendar_log") as logged:
            self._run([10 * 3600, 11 * 3600])

        errors = [
            call
            for call in logged.call_args_list
            if call.kwargs.get("level") == "ERROR"
        ]
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].kwargs.get("trace"))

    def test_sg_04_a_raising_receiver_does_not_block_the_next(self):
        """SG-04"""
        def explode(sender, **kwargs):
            raise RuntimeError("boom")

        def record(sender, **kwargs):
            self.received.append("reached")

        self._connect(explode)
        self._connect(record)
        with mock.patch.object(service, "calendar_log"):
            self._run([10 * 3600, 11 * 3600])

        self.assertEqual(self.received, ["reached"])

    # SG-05 to SG-10. A coarse unit cannot turn over alone — a month brings the
    # day, the watch and the hour with it — so each asserts only that its own
    # signal fired, not that the others stayed quiet.

    def test_sg_05_the_watch_turning_sends_phase_changed(self):
        """SG-05"""
        self._assert_fires(phase_changed, [3 * 3600 + 59 * 60, 4 * 3600])

    def test_sg_06_the_day_turning_sends_day_changed(self):
        """SG-06"""
        self._assert_fires(
            day_changed, [23 * 3600, SECONDS_PER_GAME_DAY]
        )

    def test_sg_07_the_week_turning_sends_week_changed(self):
        """SG-07"""
        self._assert_fires(
            week_changed,
            [9 * SECONDS_PER_GAME_DAY, 10 * SECONDS_PER_GAME_DAY],
        )

    def test_sg_08_the_month_turning_sends_month_changed(self):
        """SG-08"""
        self._assert_fires(
            month_changed,
            [29 * SECONDS_PER_GAME_DAY, 30 * SECONDS_PER_GAME_DAY],
        )

    def test_sg_09_the_season_turning_sends_season_changed(self):
        """SG-09"""
        self._assert_fires(
            season_changed,
            [89 * SECONDS_PER_GAME_DAY, 90 * SECONDS_PER_GAME_DAY],
        )

    def test_sg_10_the_year_turning_sends_year_changed(self):
        """SG-10"""
        self._assert_fires(
            year_changed,
            [359 * SECONDS_PER_GAME_DAY, 360 * SECONDS_PER_GAME_DAY],
        )


class RegisterSignalTests(SimpleTestCase):
    """RS — a consumer's own signal, fired on a condition they define."""

    def setUp(self):
        from django.dispatch import Signal

        self.received = []
        self.market_day = Signal()
        self.registered = []
        self.connected = []

    def tearDown(self):
        stop_calendar_clock()
        for name in self.registered:
            try:
                unregister_signal(name)
            except Exception:
                pass
        for signal, receiver in self.connected:
            signal.disconnect(receiver)

    def _register(self, signal, key, name):
        self.registered.append(name)
        register_signal(signal, key=key, name=name)

    def _listen(self, signal):
        """Connect a recorder, holding a strong reference to it.

        ``Signal.connect()`` keeps receivers weakly, so one with no other
        reference is collected and the connection quietly disappears.
        """
        def record(sender, previous, current, **kwargs):
            self.received.append(current)

        self.connected.append((signal, record))
        signal.connect(record)
        return record

    def _run(self, times):
        from twisted.internet.task import Clock

        reactor = Clock()
        with mock.patch(
            "evennia_calendar.clock.gametime", side_effect=times
        ):
            start_calendar_clock(clock=reactor)
            for _ in times:
                reactor.advance(1)
        stop_calendar_clock()

    def test_rs_01_a_registered_signal_fires_when_its_key_changes(self):
        """RS-01"""
        # A market every tenth day. day_of_year counts from one, so elapsed
        # day 18 is day-of-year 19 and elapsed day 19 is day-of-year 20 — the
        # key moves from 1 to 2 across that pair.
        self._register(
            self.market_day,
            key=lambda date: date.day_of_year // 10,
            name="market_day",
        )
        self._listen(self.market_day)
        self._run(
            [18 * SECONDS_PER_GAME_DAY, 19 * SECONDS_PER_GAME_DAY]
        )

        self.assertEqual(len(self.received), 1)

    def test_rs_02_a_registered_signal_is_quiet_when_its_key_is_unchanged(self):
        """RS-02"""
        self._register(
            self.market_day,
            key=lambda date: date.day_of_year // 10,
            name="market_day",
        )
        self._listen(self.market_day)
        # Day 11 to day 12 — same market, so the key does not move.
        self._run(
            [11 * SECONDS_PER_GAME_DAY, 12 * SECONDS_PER_GAME_DAY]
        )

        self.assertEqual(self.received, [])

    def test_rs_03_a_name_another_registration_uses_is_refused(self):
        """RS-03"""
        from django.dispatch import Signal

        self._register(
            self.market_day, key=lambda date: date.day_of_year, name="market_day"
        )

        with self.assertRaises(ValueError) as caught:
            register_signal(
                Signal(), key=lambda date: date.week, name="market_day"
            )
        self.assertIn("market_day", str(caught.exception))

    def test_rs_04_a_raising_key_does_not_silence_the_other_units(self):
        """RS-04"""
        def explode(date):
            raise RuntimeError("boom")

        self._register(self.market_day, key=explode, name="market_day")
        self._listen(day_changed)

        with mock.patch.object(service, "calendar_log") as logged:
            self._run([23 * 3600, SECONDS_PER_GAME_DAY])

        self.assertEqual(len(self.received), 1)
        errors = [
            call
            for call in logged.call_args_list
            if call.kwargs.get("level") == "ERROR"
        ]
        self.assertEqual(len(errors), 1)

    def test_rs_05_unregistering_removes_a_consumers_registration(self):
        """RS-05"""
        self._register(
            self.market_day,
            key=lambda date: date.day_of_year // 10,
            name="market_day",
        )
        self._listen(self.market_day)
        unregister_signal("market_day")

        self._run(
            [10 * SECONDS_PER_GAME_DAY, 11 * SECONDS_PER_GAME_DAY]
        )

        self.assertEqual(self.received, [])

    def test_rs_06_a_name_a_built_in_unit_uses_is_refused(self):
        """RS-06"""
        with self.assertRaises(ValueError) as caught:
            register_signal(
                self.market_day, key=lambda date: date.year, name="season"
            )
        self.assertIn("season", str(caught.exception))

    def test_rs_07_a_built_in_unit_cannot_be_unregistered(self):
        """RS-07"""
        with self.assertRaises(ValueError) as caught:
            unregister_signal("season")
        self.assertIn("season", str(caught.exception))


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

    def test_gd_04_a_float_clock_still_gives_integer_fields(self):
        """GD-04"""
        # gametime() returns a float, because time.time() does. Every case in
        # this suite patched it with an int, so nothing caught that floor
        # division on a float yields a float — and every field arrived as one.
        elapsed = float(SECONDS_PER_GAME_DAY) * 725 + 13 * 3600 + 32.75 * 60
        with mock.patch(
            "evennia_calendar.clock.gametime", return_value=elapsed
        ):
            date = game_date()

        for field in (
            "year",
            "day_of_year",
            "month",
            "day_of_month",
            "week",
            "day_of_week",
            "hour",
            "minute",
            "phase",
        ):
            value = getattr(date, field)
            self.assertIsInstance(value, int, f"{field} is {type(value)}")

    def test_gd_03_the_year_comes_through_the_accessor(self):
        """GD-03"""
        with mock.patch("evennia_calendar.clock.gametime", return_value=0):
            date = game_date()

        self.assertEqual(date.year, DEFAULT_STARTING_YEAR)
