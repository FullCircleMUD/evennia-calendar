# Installing

What a game has to do to run this library. Written as each requirement is decided rather than
reconstructed afterwards, so it describes what exists.

Three steps, then the background: what Evennia's own time settings do, and what this library's
calendar is fixed at.

## 1. Install the package

Nothing is published yet, so install from a checkout:

```
pip install -e path/to/evennia-calendar
```

## 2. Add the app

In your settings:

```python
INSTALLED_APPS += ["evennia_calendar"]
```

**This is what runs the boot check.** Leave it out and the library is importable and validates
nothing, so a mistyped `CALENDAR_STARTING_YEAR` reaches the arithmetic instead of being refused.

## 3. Choose what year your world starts in

Optional — leave it out and your world starts in year 1000.

```python
CALENDAR_STARTING_YEAR = 850
```

Detail and the rules it has to satisfy are under [Optional settings](#optional-settings) below.

## Using it

One call, one frozen result:

```python
from evennia_calendar import game_date

date = game_date()
```

| Field | Range | |
|---|---|---|
| `year` | from `CALENDAR_STARTING_YEAR` | |
| `day_of_year` | 1–360 | |
| `month` | 1–12 | `MONTH_NAMES[date.month - 1]` |
| `day_of_month` | 1–30 | |
| `week` | 1–36 | |
| `day_of_week` | 1–10 | `DAY_NAMES[date.day_of_week - 1]` |
| `season` | a `Season` | `Season.SPRING` … `Season.WINTER` |
| `hour` | 0–23 | |
| `minute` | 0–59 | |
| `phase` | 1–6 | `PHASE_NAMES[date.phase - 1]` |

**Every calendar position counts from one**, because nobody writes "0/0/1000". So a name lookup takes
the offset back off: `MONTH_NAMES[date.month - 1]`. One rule, no exceptions to remember.

`hour` and `minute` are the exception and count from zero, because 00:00 is midnight rather than a
zeroth hour. That is a clock, not a calendar position.

`season` carries the enum rather than a number, because a game branches on it — `if date.season is
Season.WINTER` — rather than displaying it.

```python
from evennia_calendar.config import DAY_NAMES, MONTH_NAMES, PHASE_NAMES

f"{PHASE_NAMES[date.phase - 1]} watch, "
f"{DAY_NAMES[date.day_of_week - 1]} "
f"{date.day_of_month} {MONTH_NAMES[date.month - 1]}, year {date.year}"
# "Afternoon watch, Manuh 6 Caitra, year 1000"
```

**Nothing is stored.** Every call builds a new `GameDate` from the clock, so an instance you hold on
to is a snapshot. Call again for the current date rather than keeping one around.

## Evennia's time settings, and what this library does with them

**Three settings belong to Evennia, not to this library.** They are core Evennia settings that exist
whether or not you install anything of ours. This library **reads them and never sets, overrides or
warns about them** — your clock is yours, and all three have defaults, so a game that declares none of
them still boots and still has a working calendar.

| Setting | Evennia default | What it does |
|---|---|---|
| `TIME_FACTOR` | `2.0` | How many game seconds pass per real second. Raise it and a game day takes less real time |
| `TIME_IGNORE_DOWNTIMES` | `False` | Whether the game world keeps running while the server is down |
| `TIME_GAME_EPOCH` | `None` | The clock's starting value, in game seconds. **This library does not read it** |

Change any of them by declaring it in your own settings file. There is nothing to do on our side.

### `TIME_FACTOR` — how fast game time runs

At the default `2.0`, a 24-hour game day takes 12 real hours. The setting is a multiplier, but the
question you are usually asking is how long a game day should take, so convert:

```
TIME_FACTOR = game_hours_per_day / real_hours_per_game_day
```

A 24-hour game day that should pass in one real hour is `TIME_FACTOR = 24`; in two real hours,
`TIME_FACTOR = 12`.

### `TIME_IGNORE_DOWNTIMES` — whether the world runs while the server is down

| Value | The calendar advances by | What that means |
|---|---|---|
| `False` (default) | accumulated server **uptime** | The world pauses while the game is down. A week's outage advances nothing. The count lives in the database, so **wiping the game database resets the calendar** |
| `True` | elapsed **wall-clock** time since first server start | The world keeps running while the game is down. A week's outage at `TIME_FACTOR = 24` advances the calendar by 168 game days. Still anchored to first server start, so a database wipe still resets it |

Neither branch survives a database wipe, because both measure from a first-start timestamp held in
`ServerConfig`. A game that rebuilds its world regularly can carry the year forward by reading the
date before shutting down and raising `CALENDAR_STARTING_YEAR` to match. The year survives that way;
the position within the year does not, because there is no starting-day setting — the world restarts
on day 0 of whatever year you name.

### `TIME_GAME_EPOCH` — read by Evennia, not by us

It sets the game clock's value at first server start, expressed as a bare count of game seconds. To
mean "year 850" you would write `850 × 360 × 86400` and put that number in your settings.

This library reads `gametime(absolute=False)`, which zeroes that term. Where the calendar starts is
expressed as a year in our own setting instead — so setting `TIME_GAME_EPOCH` will not move our dates.
It still affects anything else in your game calling `gametime(absolute=True)`.

## Required settings

None. This library has one setting and it is optional.

## Optional settings

### `CALENDAR_STARTING_YEAR` — what year the world begins in

**Default: `1000`.** Leave it out and your world starts in year 1000, which is a perfectly good year
— the setting exists for games that want a particular one.

**If you set it, it must be zero or a positive integer.** A value that is not — a negative number,
`"850"`, `850.0`, `True` — is refused at boot with the setting named. There is one form to write.
Year `0` is allowed: a world may begin at zero.

It shifts the year and nothing else. Day-of-year, season, month and phase all come from the position
*within* the year, which the offset does not move — so whatever you set, the world still begins on
day 0, the first day of spring.

## The calendar itself is not configurable

Deliberately, and it is worth knowing before you install: the calendar is fixed so that every unit
divides the one above it with nothing left over.

| Unit | Length |
|---|---|
| Year | 360 days |
| Season | 90 days — spring, summer, autumn, winter |
| Month | 30 days — 12 per year, 3 per season |
| Week | 10 days — 36 per year, 3 per month |
| Day | 24 hours |
| Watch | 4 hours — six per day |

A configurable year length cannot promise that. At 365 days the seasons stop being equal, the months
stop being whole, and the weeks stop lining up with the months — so the year length is not offered as
a knob rather than offered and then broken.

If your game needs a different calendar, this library is the wrong one.

### The day and month names are placeholders

The library ships ten day names and twelve month names so it is not empty. They are real — the days
are the Balinese Pawukon calendar's Dasawara cycle, the months are from Old Javanese inscriptions —
and they are almost certainly not what your world calls them.

You are not expected to override anything. A `GameDate` carries **numbers**: `day_of_week` 0–9 and
`month` 0–11. `DAY_NAMES` and `MONTH_NAMES` are a convenience for games with no opinion. A game with
one indexes its own tuple with the same number and never imports ours.

Seasons are different. `Season` is an enum rather than a name, because a game branches on it —
`Season.WINTER`, not `season == 3` — and spring, summer, autumn and winter are what those seasons are
called in English rather than something we invented. What your world *displays* for them is still
yours.

## Running more than one instance

This library reports whatever `gametime()` says, and **assumes every instance has been given a clock
that agrees**.

Evennia derives game time from `server_epoch`, a first-start timestamp held in each instance's own
`ServerConfig`. Instances with separate databases have separate epochs and will disagree about the
date — by however long apart they were installed, multiplied by `TIME_FACTOR`. That is a property of
Evennia's clock rather than of this library: the same gap affects `gametime.schedule()` in a
deployment with no calendar installed at all.

**Synchronising it is the job of whatever gives you multiple instances**, not of the calendar. If
instances disagree about the clock, they will disagree about the date, and nothing here detects or
corrects that.

Two things follow if you run more than one:

- **`TIME_IGNORE_DOWNTIMES` must be `True`.** On the other branch the clock counts each instance's own
  accumulated uptime, which cannot be synchronised by any means — two instances that were down for
  different lengths of time are permanently apart.
- **The epochs must be made to match**, once, and again whenever an instance's database is rebuilt.
  A rebuilt database is a new epoch.

## What is not checked for you

- **`INSTALLED_APPS`.** Leave the library out of it and `AppConfig.ready()` never runs, so nothing
  the library might validate gets validated. This is always the first thing to check when a library
  appears to be doing nothing.
- **Which `TIME_IGNORE_DOWNTIMES` branch you want.** Both are valid and the library cannot tell which
  one your game meant. See the `TIME_IGNORE_DOWNTIMES` table above.
- **Calendar continuity across a database wipe.** Nothing detects that the world's date went
  backwards.
- **Whether your instances agree about the clock.** See *Running more than one instance* above. A
  drifted instance looks completely healthy and simply reports a different date.
