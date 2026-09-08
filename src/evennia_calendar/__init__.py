# SPDX-License-Identifier: BSD-3-Clause
"""evennia-calendar: a game-world calendar for Evennia.

Tagline: *Dates, seasons and time of day for Evennia — derived from the game
clock, stored nowhere.*

``game_date()`` is the whole public surface. It reads Evennia's game seconds
and hands back a frozen ``GameDate``. Nothing is stored, so a returned instance
is a snapshot: call again for the current date rather than holding one.

See docs/INDEX.md for the design wiki and docs/test-plan.md for the cases
the library commits to.
"""

__version__ = "0.0.1"

__all__ = ["GameDate", "game_date"]


def __getattr__(name):
    """Resolve the public surface on first use, not at import.

    A plain ``from .clock import game_date`` at module scope would run while
    Django is still building its app registry — this package is in
    ``INSTALLED_APPS``, and ``clock.py`` imports ``evennia.utils.gametime``,
    which reaches for a model. That raises ``AppRegistryNotReady`` and the
    server does not start.

    Deferring costs one lookup the first time a consumer touches the name and
    nothing afterwards, since Python caches the result on the module.

    **The ``__all__`` check is load-bearing, and not only for typos.** Without
    it, ``from evennia_calendar import clock`` below re-enters this function
    looking for ``clock``, which runs the same import again — infinite
    recursion rather than a missing attribute. Rejecting every name we do not
    publish is what lets Python's normal submodule import handle the rest.
    """
    if name in __all__:
        from evennia_calendar import clock

        return getattr(clock, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


