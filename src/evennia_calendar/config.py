# SPDX-License-Identifier: BSD-3-Clause
"""Settings, their accessors, and the boot check.

Every module-level constant the library declares lives here, and every other
module imports it from here — one file to check before minting a second name
for a value that already has one.

The library has a single setting, and it is optional. Absence is the case the
default exists for, so ``check_settings()`` never complains about a setting
that is not declared; it judges only a value the consumer actually set.
"""

from enum import Enum

from .signals import (
    day_changed,
    hour_changed,
    month_changed,
    phase_changed,
    season_changed,
    week_changed,
    year_changed,
)

# The calendar's shape, fixed rather than configurable. Every unit divides the
# one above it with nothing left over — 360 = 4 × 90 = 12 × 30 = 36 × 10 — which
# a settable year length could not promise. See CLAUDE.md principle 7 before
# reaching for the idea of making any of these a setting.
SECONDS_PER_GAME_DAY = 86400
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60
DAYS_PER_YEAR = 360
DAYS_PER_SEASON = 90
DAYS_PER_MONTH = 30
DAYS_PER_WEEK = 10
HOURS_PER_WATCH = 4


class Season(Enum):
    """The four seasons, ninety days each.

    The values are the season's position in the year, so a season is looked up
    as ``Season(day_of_year // 90)`` against the zero-based day the helpers work
    in. Spring is 0 because the year opens in spring — a promise made to
    consumers in docs/installing.md, and true only while this order holds.

    A consumer never sees these numbers; they branch on the member. That is why
    this stays zero-based while every calendar position on a ``GameDate`` counts
    from one.

    An enum rather than a tuple of names: a game branches on the season, and
    ``Season.WINTER`` says what ``season == 3`` does not.
    """

    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3


# The ten days of the week, from the Balinese Pawukon calendar's Dasawara
# cycle, and the twelve months, from the Old Javanese inscriptions. Both are
# real, both are indexed by arithmetic on the day of the year, and both are
# placeholders a game is expected to replace — naming the days of an invented
# world is the consumer's business, not a library's.
#
# Tuples rather than enums because nothing computes from the strings: they are
# looked up by index and displayed. A game swapping them writes one tuple.
#
# INDEXED BY THE FIELD MINUS ONE. Every calendar position on a GameDate counts
# from one, so DAY_NAMES[date.day_of_week - 1] and MONTH_NAMES[date.month - 1].
# Miss the offset and you silently get the following name, every time.
#
# The lengths are load-bearing. Ten and twelve are what the arithmetic divides
# by; a tuple one short does not raise, it returns the wrong name.
DAY_NAMES = (
    "Pandita",
    "Pati",
    "Suka",
    "Duka",
    "Sri",
    "Manuh",
    "Manusa",
    "Raja",
    "Dewa",
    "Raksasa",
)

# The six watches of the day, four hours each, from the traditional nautical
# watch system — they land on exactly these hours without being nudged. "First"
# sits at index 5 rather than 0 because the naval day began at noon, so the
# first watch of the new day started at 20:00.
#
# Six rather than four quarters because it gives a game three choices of night
# length — one, two or three dark watches, so 4, 8 or 12 hours. Which of them
# are dark is the game's business, not ours.
#
# Indexed by PHASE_NAMES[date.phase - 1], as the other two are.
PHASE_NAMES = (
    "Middle",
    "Morning",
    "Forenoon",
    "Afternoon",
    "Dog",
    "First",
)

MONTH_NAMES = (
    "Caitra",
    "Waisakha",
    "Jyestha",
    "Ashadha",
    "Sravana",
    "Bhadrapada",
    "Asvina",
    "Kartika",
    "Margasirsa",
    "Pausa",
    "Magha",
    "Phalguna",
)

# What each unit of time is, as the fields on a GameDate that identify it. A
# unit turned over between two dates if any of them differ — which is how the
# coarser fields get carried: two dates a year apart share a day-of-year, and
# are not the same day.
#
# This table is also the set of reserved unit names. A consumer registering a
# signal of their own cannot use one of these, and cannot unregister them.
UNIT_FIELDS = {
    "year": ("year",),
    "season": ("year", "season"),
    "month": ("year", "month"),
    "week": ("year", "week"),
    "day": ("year", "day_of_year"),
    "phase": ("year", "day_of_year", "phase"),
    "hour": ("year", "day_of_year", "hour"),
}

# Which signal announces which unit. Wiring rather than public surface — a
# consumer connects to the names in signals.py and never reads this.
UNIT_SIGNALS = {
    "hour": hour_changed,
    "phase": phase_changed,
    "day": day_changed,
    "week": week_changed,
    "month": month_changed,
    "season": season_changed,
    "year": year_changed,
}

SETTING_STARTING_YEAR = "CALENDAR_STARTING_YEAR"

# Any year would do — the world has to start somewhere and nothing downstream
# reads the number except to add it. 1000 is far enough from zero to read as a
# world with history behind it, and round enough to be obviously arbitrary.
DEFAULT_STARTING_YEAR = 1000

# Prefixes every problem check_settings() reports, so a consumer can see at a
# glance which library refused the boot, and a test can count problems without
# pinning any wording.
PROBLEM_PREFIX = "evennia-calendar:"


def get_starting_year() -> int:
    """Return ``CALENDAR_STARTING_YEAR``, defaulting to 1000.

    No coercion and no validation: ``check_settings()`` has already refused a
    declared value that is not usable, so anything reaching here is either the
    consumer's integer or our default.

    The ``from django.conf import settings`` import belongs inside the body:
    at module scope it would run when the library is first imported, which can
    be while the consumer's settings module is still executing.
    """
    from django.conf import settings

    return getattr(settings, SETTING_STARTING_YEAR, DEFAULT_STARTING_YEAR)


def check_settings():
    """Refuse to start when a declared setting is unusable.

    Collects every problem and raises once, so a consumer gets the whole list
    rather than one restart per mistake. With a single setting there can only
    ever be one problem today; the shape is here because the second setting
    should not have to introduce it.

    Called from ``AppConfig.ready()`` and nowhere else.
    """
    from django.conf import settings

    problems = []

    # ``None`` as the sentinel rather than ``settings.NAME``, so an undeclared
    # setting reaches this as "absent" instead of raising AttributeError.
    # Absence is the case the default exists for, so it is not a problem.
    # ``bool`` is a subclass of ``int``, so the isinstance test alone accepts
    # True and reads it as year 1. Excluded explicitly, before the int check.
    year = getattr(settings, SETTING_STARTING_YEAR, None)
    if year is not None and (
        isinstance(year, bool) or not isinstance(year, int) or year < 0
    ):
        problems.append(
            f"{PROBLEM_PREFIX} {SETTING_STARTING_YEAR} is {year!r}. It must be "
            f"zero or a positive integer — the year the world begins in. "
            f"A string and a float are both refused so there is one form to "
            f"write. Leave the setting out to start in "
            f"{DEFAULT_STARTING_YEAR}."
        )

    if problems:
        from django.core.exceptions import ImproperlyConfigured

        # **The exception is the only channel here.** Nothing is logged,
        # because nothing can be: this runs from AppConfig.ready() during
        # django.setup(), and Evennia's log_file() defers every write to the
        # reactor's thread pool, which does not exist yet. The deferred is
        # created, never runs, and dies with the process. Verified — it leaves
        # a zero-byte log file and no line.
        #
        # So the message carries everything a consumer needs, and it reaches
        # whoever ran the command. See design/library-standards.md § Logging.
        raise ImproperlyConfigured(" ".join(problems))
