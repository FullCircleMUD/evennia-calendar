"""Everything this demo does with evennia-calendar.

Three things, which are the three a consumer does:

1. **Ask what time it is** — ``game_date()``, used by the ``gametime`` command.
2. **React to a built-in signal** — ``phase_changed``, announcing each watch.
3. **Define a condition of its own** — ``market_bell``, registered with
   ``register_signal()`` and firing every six game hours, which is not any of
   the library's units.

Everything announced here goes to the server log as well as to connected
players, so the demo can be verified by reading a file rather than by sitting
in a client.

**Every receiver in this file is a module-level function, deliberately.**
``Signal.connect()`` holds receivers weakly, so a lambda or a function defined
inside ``at_server_start()`` is collected the moment that call returns and the
connection disappears with it — silently, with nothing in any log. A
module-level function is held by its module and survives. See the library's
docs/custom-signals.md.
"""

from django.dispatch import Signal
from evennia import SESSION_HANDLER
from evennia.utils import logger

from evennia_calendar import game_date
from evennia_calendar.config import DAY_NAMES, MONTH_NAMES, PHASE_NAMES
from evennia_calendar.service import register_signal, start_calendar_clock
from evennia_calendar.signals import day_changed, phase_changed

#: Our own signal. The library knows nothing about it beyond what we register.
market_bell = Signal()


def describe(date) -> str:
    """Render a GameDate the way this world says it.

    Every calendar position counts from one, so a name lookup takes the offset
    back off — ``MONTH_NAMES[date.month - 1]``. Miss that and you get the
    following month, all year.
    """
    return (
        f"{date.hour:02d}:{date.minute:02d}, the {PHASE_NAMES[date.phase - 1]} "
        f"watch — {DAY_NAMES[date.day_of_week - 1]}, "
        f"day {date.day_of_month} of {MONTH_NAMES[date.month - 1]}, "
        f"year {date.year} ({date.season.name.lower()})"
    )


def announce(message: str) -> None:
    """Say something to the log and to anyone connected."""
    logger.log_info(f"[calendar-demo] {message}")
    SESSION_HANDLER.announce_all(f"|w{message}|n")


# --- receivers ------------------------------------------------------------


def on_phase_changed(sender, previous, current, **kwargs):
    """A built-in signal: the watch turned over."""
    announce(f"The {PHASE_NAMES[current.phase - 1]} watch begins. {describe(current)}")


def on_day_changed(sender, previous, current, **kwargs):
    """Another built-in. Fires alongside the watch, since a new day is also a
    new watch — subscribing to both means two messages on that tick."""
    announce(
        f"A new day dawns: {DAY_NAMES[current.day_of_week - 1]}, "
        f"day {current.day_of_month} of {MONTH_NAMES[current.month - 1]}."
    )


def on_market_bell(sender, previous, current, **kwargs):
    """Our own signal, on a condition the library has no concept of."""
    announce("The market bell rings across the square.")


# --- wiring ---------------------------------------------------------------


def start_calendar_demo() -> None:
    """Register, connect and start. Called from ``at_server_start()``.

    Registering and connecting both have to happen here rather than at import
    time, because both are module state that dies when the Server process
    restarts on reload.
    """
    register_signal(
        market_bell,
        # Every six game hours — a minute of real time at TIME_FACTOR 360, and
        # deliberately not one of the library's units, which divide the day
        # into six four-hour watches.
        key=lambda date: date.hour // 6,
        name="market_bell",
    )

    phase_changed.connect(on_phase_changed)
    day_changed.connect(on_day_changed)
    market_bell.connect(on_market_bell)

    start_calendar_clock()

    logger.log_info(f"[calendar-demo] started. It is now {describe(game_date())}")
