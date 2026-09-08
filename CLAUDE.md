# CLAUDE.md

> **Project-wide working rules and cross-repo context live in the FCM umbrella repo's `CLAUDE.md`**,
> loaded automatically when you work from the umbrella root. If you opened this repo directly instead
> of via the umbrella, relaunch from the umbrella root for the full context. This file holds only this
> repo's specific instructions.

Instructions for Claude (and other LLM agents) working in this repository.

## What this project is

`evennia-calendar` turns [Evennia](https://www.evennia.com/)'s game clock into a game-world calendar —
a date, a season and a time of day. Tagline: **"Dates, seasons and time of day for Evennia."**

Evennia's `gametime()` returns a count of game seconds and nothing else; the division into days,
years, seasons and phases is this library's job. FullCircleMUD is the intended first consumer and has
its own working version, in `typeclasses/scripts/day_night_service.py` and `season_service.py`.
Nothing has been taken from it wholesale.

For the big-picture overview, read [README.md](README.md).
For the design wiki, read [docs/INDEX.md](docs/INDEX.md).

## Project status

**The clock works.** `game_date()` returns the world's year and day of that year, derived from
Evennia's game seconds. A bad setting is refused at boot and written to `calendar.log`. Still to come:
month, week, season, hour and phase — each an added field with its own helper.
29 tests passing. See [docs/progress.md](docs/progress.md).

## Where to read first

1. [docs/test-plan.md](docs/test-plan.md) — the cases the library commits to. **A behavioural change
   starts here**, not in the code. **Start here.**
2. [README.md](README.md) — what the library is and its status.
3. [docs/INDEX.md](docs/INDEX.md) — map of all design docs.
4. [docs/installing.md](docs/installing.md) — what a consumer declares.
5. [docs/interoperability.md](docs/interoperability.md) — this library against its siblings.

**FCM's day/night and season services describe the system being extracted, not this library.** They
are the source to read for how it behaves today, not a specification for what belongs here.

## Load-bearing architectural principles

Every implementation decision must respect them.

1. **The library does not own game concepts.** Rooms, weather, lighting, festivals, NPC schedules and
   what a season *means* belong to the consumer game. The library provides the calendar and answers
   questions about it.

2. **No FCM-specific assumptions.** This library is being extracted from work on FullCircleMUD. FCM's
   season names, phase boundaries, year length and typeclass names all stay in FCM. Default to
   "consumer concern" when uncertain.

3. **Test-first.** A case lands in [docs/test-plan.md](docs/test-plan.md), then the test, then the
   code. See [test-first-process.md](../../design/test-first-process.md) for the process and the
   rationale.

4. **The calendar is derived, never stored.** Every value the library reports is a function of the
   number Evennia hands back. No tables, no `ndb`, no persisted state — so it survives a reload, needs
   no migration, and every process in a multi-process deployment computes the same answer without
   coordinating.

5. **Evennia owns the clock; this library owns the calendar.** We read the game seconds and do our own
   integer division. **Never `datetime`.** Reading the game timestamp through `datetime.fromtimestamp`
   silently borrows a 365-day year, leap years and a real month structure — that is the defect being
   extracted away from, not a shortcut to reuse.

6. **The consumer's Evennia time settings are theirs, not ours.** `TIME_FACTOR`,
   `TIME_IGNORE_DOWNTIMES` and `TIME_GAME_EPOCH` are read, respected, and their implications
   documented in [docs/installing.md](docs/installing.md). The library does not choose between them,
   warn about them, or work around them.

7. **The calendar's shape is fixed, and only where it starts is configurable.** 360-day year, 12
   months of 30 days, 36 weeks of 10 days, four seasons of 90 days, a 24-hour day, four six-hour
   phases. Every unit divides the one above it with nothing left over, and that is the reason: a
   configurable year length cannot promise it — at 365 the seasons stop being equal and the months
   stop being whole. **Do not add a `days_per_year` or `hours_per_day` setting.** It looks like an
   obvious kindness to a consumer and it breaks months, weeks and seasons at the same stroke.

## Out of scope

Decided as questions arise. Rulings so far:

- **Weather.** Terrain-driven weather, its tables and its gameplay effects are a separate library that
  depends on this one. This library answers "what season is it" and stops there.
  `[TBD — needs discussion: that library's name. `evennia-terrain-weather` and `evennia-weather` were
  both put up; the choice turns on whether terrain or region keys the tables.]`
- **The library owns no tables.** The calendar is derived from game time, so there is nothing to
  store. No alias, no router, no migration for a consumer to configure. Revisit only if the library
  gains data of its own.

## Working conventions

- **Behavioural change starts in the test plan.** Add the case, write the test, then implement. Fill
  the **Test function** column when the test exists — it is a coverage claim and the linter checks it
  both ways.
- **Editing design docs.** Update or add design documents whenever an architectural decision is made
  or refined. Capture the *why*, not just the *what*. Index new docs in [docs/INDEX.md](docs/INDEX.md).
- **Don't put implementation detail in this file or README.** Link out to `docs/` instead. Keep
  `CLAUDE.md` and `README.md` stable; let `docs/` churn.
- **License.** BSD 3-Clause. Source files carry an SPDX header on the first line
  (`# SPDX-License-Identifier: BSD-3-Clause`).

## Documentation discipline (load-bearing)

Design documents in `docs/` must reflect decisions **actually discussed and agreed on with the project
owner**. They are not a place to forward-design the system from first principles or extrapolate
"reasonable defaults" from a starting point.

**Rules:**

1. **Only capture what was discussed and agreed.** If the conversation establishes a principle, do not
   extrapolate it into specifics that were not raised — season counts, phase boundaries, setting
   names, defaults.
2. **Flag open questions explicitly.** Write `[TBD — needs discussion: <what is open>]` so a future
   session picks the topic up deliberately rather than inheriting an unagreed assumption.
3. **Smaller is better.** Three discussed points captured faithfully beat three discussed points plus
   seven invented ones. Resist filling out sections "for completeness".

**The tempting source of unasked-for answers is FCM's own implementation.** It has a working shape for
every question this library will face, ready to be lifted. A shape lifted from it is an invention
unless it has been discussed here — the extraction is a design exercise, not a copy.

## Repository layout

```
evennia-calendar/
├── CLAUDE.md                  # this file
├── README.md
├── LICENSE                    # BSD 3-Clause
├── pyproject.toml
├── runtests.py                # standalone test runner; no gamedir required
├── .gitignore
├── docs/                      # design wiki (humans + LLMs)
│   ├── INDEX.md
│   ├── installing.md          # what a consumer declares; grows as we decide
│   ├── progress.md
│   ├── test-plan.md
│   ├── interoperability.md
│   └── archive/               # historical context, not authoritative
├── src/
│   └── evennia_calendar/      # library code (src layout)
│       ├── __init__.py
│       ├── apps.py            # AppConfig — ready() runs the boot check
│       ├── clock.py           # GameDate, game_date(), and the conversions
│       ├── config.py          # the setting, its accessor, check_settings()
│       ├── log.py             # shim onto Evennia's logger → calendar.log
│       └── tests.py           # unit tests, run via runtests.py
└── tests/                     # standalone test infrastructure
    ├── __init__.py
    ├── test_settings.py
    └── urls.py
```

**`tests/test_settings.py` deliberately does not declare `CALENDAR_STARTING_YEAR`**, so absence is
the suite's baseline and a case wanting a value overrides one in. Declaring it there would make
`CF-01` and `CF-03` untestable without removing it again.

No `contrib/` — nothing opt-in exists, and the standards forbid scaffolding one empty.

No `examples/` — no demo gamedir yet. It lands when there is a surface to exercise end to end.

## Tools and environment

- Python 3.10+ (pinned via `pyproject.toml`).
- Evennia is the only runtime dependency.
- **Tests use Django's test runner** via `python runtests.py`, which bootstraps Django then calls
  `evennia._init()`, as the siblings do. Not pytest, and no gamedir required.
- Development uses a dedicated venv at `venv/` (gitignored), independent of any consumer game.

## Sibling libraries to reference

- **[../evennia-survival/](../evennia-survival/)** — the closest reference shape for repo structure,
  the test runner, and the docs surfaces. Also a likely consumer: hunger and thirst are the mechanics
  a calendar-driven weather layer would first reach for.
- **[../evennia-shards/](../evennia-shards/)** — documents how state behaves when the game runs as
  more than one process. This library's answer is to hold none, which is worth reading against.
