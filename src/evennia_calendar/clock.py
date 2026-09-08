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

from .config import DAYS_PER_YEAR, SECONDS_PER_GAME_DAY, get_starting_year


@dataclass(frozen=True)
class GameDate:
    """Where the game world's calendar stands, at the moment it was asked.

    Nothing stores one. Every call to ``game_date()`` builds a new instance, so
    an instance held onto is a snapshot rather than something that goes stale
    in place.
    """

    year: int
    day_of_year: int


def _day_number(elapsed_seconds: int) -> int:
    """Return the absolute day count for a number of elapsed game seconds.

    Floor division, not rounding: most of a day is still that day, and a day
    only turns over when it is complete.
    """
    return elapsed_seconds // SECONDS_PER_GAME_DAY


def _day_of_year(day_number: int) -> int:
    """Return the position within the year for an absolute day count."""
    return day_number % DAYS_PER_YEAR


def _year(day_number: int, starting_year: int) -> int:
    """Return the year for an absolute day count and a starting year.

    Takes the starting year rather than reading the setting, so it stays a pure
    conversion and the accessor remains the factory's business.
    """
    return starting_year + day_number // DAYS_PER_YEAR


def game_date() -> GameDate:
    """Return the game world's date now.

    ``absolute=False`` zeroes Evennia's own epoch term, so what comes back is
    scaled seconds since the server first started and where the calendar begins
    is expressed as a year in our setting instead. See docs/installing.md for
    what that means for ``TIME_GAME_EPOCH``.
    """
    day = _day_number(gametime(absolute=False))
    return GameDate(
        year=_year(day, get_starting_year()),
        day_of_year=_day_of_year(day),
    )
