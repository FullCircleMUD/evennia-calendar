# SPDX-License-Identifier: BSD-3-Clause
"""The Django app, and the one thing it does at boot.

``ready()`` validates the consumer's configuration and nothing else. Checking
here rather than at first use is the point: validation deferred to whenever a
date is first asked for means a misconfigured instance starts cleanly, runs,
and then fails somewhere that says nothing about the setting that was wrong.
"""

from django.apps import AppConfig


class CalendarConfig(AppConfig):
    """Refuses the boot when a declared calendar setting is unusable."""

    name = "evennia_calendar"
    label = "evennia_calendar"
    verbose_name = "Evennia Calendar"

    def ready(self):
        from evennia_calendar.config import check_settings

        check_settings()
