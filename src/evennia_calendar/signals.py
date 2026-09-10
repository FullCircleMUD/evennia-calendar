# SPDX-License-Identifier: BSD-3-Clause
"""The signals a consumer subscribes to.

``django.dispatch.Signal``, one per unit of time. A consumer connects a
receiver and is woken when that unit turns over::

    from evennia_calendar.signals import hour_changed

    def on_hour(sender, previous, current, **kwargs):
        ...

    hour_changed.connect(on_hour)

Each carries ``previous`` and ``current`` — the two ``GameDate``s — and nothing
else. The signal's name already says which unit turned over, and anything else
a receiver wants is on the two dates.

**Connections are module state and do not survive a reload.** A consumer
reconnects from whatever runs at startup, alongside starting the clock.

Declared here rather than in ``config.py`` because ``signals.py`` is where a
Django developer looks for them.
"""

from django.dispatch import Signal

hour_changed = Signal()
phase_changed = Signal()
day_changed = Signal()
week_changed = Signal()
month_changed = Signal()
season_changed = Signal()
year_changed = Signal()
