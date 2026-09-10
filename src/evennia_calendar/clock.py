# SPDX-License-Identifier: BSD-3-Clause
"""Reading Evennia's clock and turning it into a date.

Evennia hands back a count of game seconds and has no opinion about days,
weeks, seasons or years. Everything here is integer arithmetic on that number
— never ``datetime``, which would silently borrow a 365-day year, leap years
and a real month structure into a world that has none of them.

Each conversion is a private helper taking integers and returning integers,
with its own cases. ``game_date()`` reads the clock, calls them, and assembles
a ``GameDate`` — so adding a field means adding a helper, not complicating the
factory.
"""

from dataclasses import dataclass

# Reading the game clock is what this module is for, so it is the one place
# outside log.py that reaches for Evennia. Imported at module scope rather than
# inside the function so the suite has a single name to patch.
from evennia.utils.gametime import gametime

from .config import (
    DAYS_PER_MONTH,
    DAYS_PER_SEASON,
    DAYS_PER_WEEK,
    DAYS_PER_YEAR,
    HOURS_PER_WATCH,
    SECONDS_PER_GAME_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    Season,
    get_starting_year,
)


@dataclass(frozen=True)
class GameDate:
    """Where the game world's calendar stands, at the moment it was asked.

    Nothing stores one. Every call to ``game_date()`` builds a new instance, so
    an instance held onto is a snapshot rather than something that goes stale
    in place.

    **Every calendar position counts from one.** ``day_of_year``, ``month``,
    ``day_of_month``, ``week`` and ``day_of_week`` are all one-based, because
    nobody writes "0/0/1000" and nobody calls it the zeroth day of the week.
    ``phase`` follows the same rule.

    One rule, so there is nothing to remember about which fields are which:
    **subtract one to index a name tuple** — ``MONTH_NAMES[date.month - 1]``,
    ``DAY_NAMES[date.day_of_week - 1]``, ``PHASE_NAMES[date.phase - 1]``.

    ``hour`` and ``minute`` are the one exception, and count from zero, because
    00:00 is midnight rather than a zeroth hour. That is a clock, not a calendar
    position.

    The helpers below are zero-based throughout — they are arithmetic and they
    feed each other. The offset is applied once, here, at assembly.

    The names are placeholders. A game with its own indexes its own tuple the
    same way. ``season`` carries the enum rather than a number, because a game
    branches on it rather than displaying it.
    """

    year: int
    day_of_year: int
    month: int
    day_of_month: int
    week: int
    day_of_week: int
    season: Season
    hour: int
    minute: int
    phase: int


def _day_number(elapsed_seconds: float) -> int:
    """Return the absolute day count for a number of elapsed game seconds.

    Floor division, not rounding: most of a day is still that day, and a day
    only turns over when it is complete.

    **Coerced to `int`, because `gametime()` returns a float** — `time.time()`
    does, so everything downstream of it does too. Floor division on a float
    gives a float, and a float would travel the whole way to a consumer writing
    ``f"{date.hour:02d}"`` and raise there. This and ``_seconds_into_day()``
    are the two places the raw clock value enters, so coercing here means every
    helper after them is integer arithmetic.
    """
    return int(elapsed_seconds // SECONDS_PER_GAME_DAY)


def _day_of_year(day_number: int) -> int:
    """Return the position within the year for an absolute day count."""
    return day_number % DAYS_PER_YEAR


def _year(day_number: int, starting_year: int) -> int:
    """Return the year for an absolute day count and a starting year.

    Takes the starting year rather than reading the setting, so it stays a pure
    conversion and the accessor remains the factory's business.
    """
    return starting_year + day_number // DAYS_PER_YEAR


def _month(day_of_year: int) -> int:
    """Return the month for a day of the year. Twelve months of thirty days."""
    return day_of_year // DAYS_PER_MONTH


def _day_of_month(day_of_year: int) -> int:
    """Return the day within the month for a day of the year."""
    return day_of_year % DAYS_PER_MONTH


def _week(day_of_year: int) -> int:
    """Return the week for a day of the year. Thirty-six weeks of ten days."""
    return day_of_year // DAYS_PER_WEEK


def _day_of_week(day_of_year: int) -> int:
    """Return the day within the week for a day of the year."""
    return day_of_year % DAYS_PER_WEEK


def _season(day_of_year: int) -> Season:
    """Return the Season for a day of the year. Four seasons of ninety days.

    ``Season``'s values are the season's position in the year, so the division
    is the lookup and there is no mapping table in between.
    """
    return Season(day_of_year // DAYS_PER_SEASON)


def _seconds_into_day(elapsed_seconds: float) -> int:
    """Return how far into the day a number of elapsed game seconds falls.

    The remainder ``_day_number()`` discards — the two take the same input and
    divide it between them, and both coerce to ``int`` for the reason given
    there.
    """
    return int(elapsed_seconds % SECONDS_PER_GAME_DAY)


def _hour(seconds_into_day: int) -> int:
    """Return the hour of the day for a position within it."""
    return seconds_into_day // SECONDS_PER_HOUR


def _minute(seconds_into_day: int) -> int:
    """Return the minute of the hour for a position within the day."""
    return seconds_into_day % SECONDS_PER_HOUR // SECONDS_PER_MINUTE


def _phase(hour: int) -> int:
    """Return the phase for an hour. Six watches of four hours.

    Taken from the hour rather than the seconds, so the phase cannot disagree
    with the clock displayed beside it.
    """
    return hour // HOURS_PER_WATCH


def game_date() -> GameDate:
    """Return the game world's date now.

    ``absolute=False`` zeroes Evennia's own epoch term, so what comes back is
    scaled seconds since the server first started and where the calendar begins
    is expressed as a year in our setting instead. See docs/installing.md for
    what that means for ``TIME_GAME_EPOCH``.
    """
    elapsed = gametime(absolute=False)

    day = _day_number(elapsed)
    day_of_year = _day_of_year(day)

    seconds_into_day = _seconds_into_day(elapsed)
    hour = _hour(seconds_into_day)

    # Every calendar position is offset here and nowhere else. The clock is not
    # — 00:00 is midnight. See GameDate's docstring.
    return GameDate(
        year=_year(day, get_starting_year()),
        day_of_year=day_of_year + 1,
        month=_month(day_of_year) + 1,
        day_of_month=_day_of_month(day_of_year) + 1,
        week=_week(day_of_year) + 1,
        day_of_week=_day_of_week(day_of_year) + 1,
        season=_season(day_of_year),
        hour=hour,
        minute=_minute(seconds_into_day),
        phase=_phase(hour) + 1,
    )
