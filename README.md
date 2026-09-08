# evennia-calendar

A game-world calendar for Evennia. Evennia tells you how many game seconds have passed; this library
turns that into a date, a season and a time of day.

## Status

**Configuration only.** You can declare what year your world starts in, and a value the library
cannot use is refused at boot. Nothing derives a date yet. See
[docs/progress.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/progress.md).

## The problem it solves

Evennia ships a clock and no calendar. `gametime()` hands back a count of game seconds and has no
opinion about days, weeks, seasons or years — so every game that wants a season writes the division
itself.

The tempting shortcut is to read that number as a Unix timestamp and let `datetime` do the work. It
looks right and it borrows a 365-day year, leap years and a real month structure into a world that
has none of them.

## The approach

Take the number Evennia already produces and do our own integer arithmetic on it. Elapsed seconds to
day, day to day-of-year and year, day-of-year to season, remainder to hour and phase of day. No
`datetime`, no borrowed calendar, and nothing stored — the whole calendar is a function of game time,
so it needs no database, survives a reload, and every process computes the same answer.

Evennia owns the clock. This library owns the calendar.

## Is this for you?

Probably, if you want dates, seasons or a day/night cycle in an Evennia game and would rather declare
a calendar than write the division.

Probably not, if your world runs on the real calendar — `datetime` on `gametime(absolute=True)`
already does that, and this library exists because that is the wrong answer for an invented world.

## Install

**What a game declares is in
[docs/installing.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/installing.md).**

Nothing is published yet. Editable install for development against a checkout:

```
git clone https://github.com/FullCircleMUD/evennia-calendar.git
cd evennia-calendar
python -m venv venv
# Activate the venv (platform-specific)
pip install evennia
pip install -e .
python runtests.py
```

## Learn more

- [docs/INDEX.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/INDEX.md) — the design wiki
- [docs/installing.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/installing.md) — everything a game declares, growing as each requirement is decided
- [docs/test-plan.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/test-plan.md) — every case the library commits to covering
- [docs/interoperability.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/docs/interoperability.md) — this library against its siblings
- [CLAUDE.md](https://github.com/FullCircleMUD/evennia-calendar/blob/main/CLAUDE.md) — context for LLM agents working in this repo

## Licence

BSD 3-Clause. See [LICENSE](https://github.com/FullCircleMUD/evennia-calendar/blob/main/LICENSE).
