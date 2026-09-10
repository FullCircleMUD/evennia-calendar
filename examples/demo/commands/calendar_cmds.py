"""The `gametime` command — ask the calendar what time it is."""

from evennia import Command

from world.calendar_demo import describe

from evennia_calendar import game_date


class CmdGameTime(Command):
    """
    Show the game world's date and time.

    Usage:
      gametime

    Every call reads the clock afresh. Nothing is stored, so the answer is a
    snapshot rather than something that goes stale in place.
    """

    key = "gametime"
    aliases = ["date", "time"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        self.caller.msg(describe(game_date()))
