# SPDX-License-Identifier: BSD-3-Clause
"""The clock that notices the date changing.

``clock.py`` answers what time it is. This runs, and says when it turned over.

A Twisted ``LoopingCall`` rather than an Evennia script: nothing persistent to
get stuck stopped, and recreated at every boot. Started from the consumer's
``at_server_start()``, not from ``AppConfig.ready()`` — that also runs during
``evennia migrate``, where a clock should not be spinning up.

The comparison is a pure function taking two dates, so the lifecycle is
testable without a reactor and the arithmetic is testable without a clock.
"""

from .clock import game_date
from .config import UNIT_FIELDS, UNIT_SIGNALS
from .log import calendar_log

#: The running clock, or ``None``. Module state so a second ``start`` cannot
#: begin a rival loop — Evennia runs ``at_server_start()`` on reload as well as
#: boot, so a consumer following the instructions calls it twice.
_clock = None

#: The last date the clock saw, or ``None`` before its first tick.
_remembered = None

#: Consumers' own signals: ``name -> (key function, signal)``. Lower case
#: because it is live state rather than a constant — it changes as a game
#: registers and unregisters, and it empties when the Server process restarts,
#: so a consumer re-registering from ``at_server_start()`` after a reload never
#: collides with itself.
_registered = {}


def _changed_units(previous, current) -> frozenset:
    """Return the units that turned over between two dates.

    A unit turned over if it or anything coarser did, so each comparison
    carries its coarser fields with it — two dates a year apart share a
    day-of-year and are not the same day.
    """
    return frozenset(
        unit
        for unit, fields in UNIT_FIELDS.items()
        if any(
            getattr(previous, field) != getattr(current, field)
            for field in fields
        )
    )


def register_signal(signal, key, name: str) -> None:
    """Fire ``signal`` when ``key(date)`` changes between two ticks.

    ``key`` is a pure function of a ``GameDate``, so a consumer describes their
    condition and never remembers a previous value or writes a comparison::

        register_signal(market_day, key=lambda d: d.day_of_year // 10,
                        name="market_day")

    **A name already in use is refused, never replaced.** Two developers on one
    game can both reach for the same name, and the second silently clobbering
    the first would stop that subsystem firing with nothing to say why.
    """
    if name in UNIT_FIELDS:
        raise ValueError(
            f"{name!r} is a built-in calendar unit and cannot be registered "
            f"over. Choose another name."
        )
    if name in _registered:
        raise ValueError(
            f"{name!r} is already registered. Unregister it first, or choose "
            f"another name — a second registration would silently stop the "
            f"first from firing."
        )

    _registered[name] = (key, signal)


def unregister_signal(name: str) -> None:
    """Remove a consumer's registration.

    Refuses the seven built-in units — a game that could unregister ``season``
    could turn off part of the calendar by accident, and they are not a
    consumer's to remove.
    """
    if name in UNIT_FIELDS:
        raise ValueError(
            f"{name!r} is a built-in calendar unit and cannot be unregistered."
        )
    _registered.pop(name, None)


def _dispatch(previous, current, changed) -> None:
    """Send a signal for each unit that turned over.

    ``send_robust`` rather than ``send``: it catches each receiver's exception
    and hands it back, so one consumer's broken handler cannot silence the
    subscriber behind it. Their bug is theirs to fix — we log it and carry on.
    """
    for unit in changed:
        signal = UNIT_SIGNALS.get(unit)
        if signal is not None:
            _send(unit, signal, previous, current)

    for name, (key, signal) in list(_registered.items()):
        if _key_changed(name, key, previous, current):
            _send(name, signal, previous, current)


def _key_changed(name, key, previous, current) -> bool:
    """Whether a consumer's key function reports a change.

    Their code, so it is guarded: a key that raises is logged and its signal
    skipped, rather than allowed to stop the clock or silence the units behind
    it in the loop.
    """
    try:
        return key(previous) != key(current)
    except Exception:
        calendar_log(
            f"the key function registered for {name!r} raised; "
            f"its signal was skipped",
            level="ERROR",
            trace=True,
        )
        return False


def _send(name, signal, previous, current) -> None:
    """Send one signal, reporting any receiver that raised."""
    for receiver, response in signal.send_robust(
        sender=None, previous=previous, current=current
    ):
        if isinstance(response, Exception):
            _log_receiver_failure(name, receiver, response)


def _log_receiver_failure(unit, receiver, error) -> None:
    """Report a subscriber that raised, naming whose it is.

    ``send_robust`` returns the exception rather than raising it, so there is
    no live traceback for ``trace=True`` to pick up — it is formatted from the
    exception itself.
    """
    import traceback

    name = getattr(receiver, "__qualname__", repr(receiver))
    detail = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    calendar_log(
        f"a receiver of {unit}_changed raised: {name}\n{detail.rstrip()}",
        level="ERROR",
        trace=True,
    )


def _tick() -> None:
    """One pass: read the date, compare it to the last, announce any change.

    The first tick has nothing to compare against. It takes a baseline and
    says nothing — starting to watch is not a transition.
    """
    global _remembered

    current = game_date()
    previous, _remembered = _remembered, current

    if previous is None:
        return

    changed = _changed_units(previous, current)
    if changed:
        _dispatch(previous, current, changed)


def _guarded_tick() -> None:
    """What the loop calls. Nothing may escape it.

    An exception reaching a ``LoopingCall`` stops it, and the clock then goes
    quietly dead while the game looks healthy. The realistic source is a
    consumer's own handler, which is not ours to fix — so it is logged with its
    traceback and the clock carries on.
    """
    try:
        _tick()
    except Exception:
        calendar_log(
            "the calendar tick raised; the clock continues",
            level="ERROR",
            trace=True,
        )


def start_calendar_clock(interval: float = 1.0, clock=None):
    """Start the clock. Call once from ``at_server_start()``.

    Starting twice is a no-op returning the clock already running, because
    Evennia runs ``at_server_start()`` on reload as well as boot.

    ``clock`` is a testing seam — pass a ``twisted.internet.task.Clock`` to
    drive the loop without a reactor. Production leaves it alone.
    """
    global _clock

    from twisted.internet.task import LoopingCall

    if _clock is not None and _clock.running:
        return _clock

    _clock = LoopingCall(_guarded_tick)
    if clock is not None:
        _clock.clock = clock
    _clock.start(interval, now=False)

    calendar_log(f"calendar clock started, ticking every {interval}s")
    return _clock


def stop_calendar_clock() -> None:
    """Stop the clock, if one is running."""
    global _clock, _remembered

    if _clock is None or not _clock.running:
        return

    _clock.stop()
    _clock = None
    _remembered = None
