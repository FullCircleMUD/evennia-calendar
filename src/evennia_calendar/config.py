# SPDX-License-Identifier: BSD-3-Clause
"""Settings, their accessors, and the boot check.

Every module-level constant the library declares lives here, and every other
module imports it from here — one file to check before minting a second name
for a value that already has one.

The library has a single setting, and it is optional. Absence is the case the
default exists for, so ``check_settings()`` never complains about a setting
that is not declared; it judges only a value the consumer actually set.
"""

# The log shim is imported at module scope, and this is the one module that
# does it — a refusal has to reach calendar.log as well as the traceback. The
# dependency runs this way deliberately: log.py imports nothing of ours, so
# there is no cycle.
from .log import calendar_log

# The calendar's shape, fixed rather than configurable. Every unit divides the
# one above it with nothing left over — 360 = 4 × 90 = 12 × 30 = 36 × 10 — which
# a settable year length could not promise. See CLAUDE.md principle 7 before
# reaching for the idea of making any of these a setting.
SECONDS_PER_GAME_DAY = 86400
DAYS_PER_YEAR = 360

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

        # Logged before it is raised, and with the exception's own text rather
        # than a second wording of it. The traceback scrolls past; the log is
        # where a consumer goes back to read why the game would not start.
        message = " ".join(problems)
        calendar_log(message, level="ERROR")
        raise ImproperlyConfigured(message)
