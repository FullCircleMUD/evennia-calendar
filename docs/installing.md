# Installing

What a game has to do to run this library. Written as each requirement is decided rather than
reconstructed afterwards, so it describes what exists.

**The library is at scaffold stage.** The two numbered steps are real. The Evennia settings below are
a decision a consumer has to make whatever this library ends up looking like, so they are recorded now.

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
`ServerConfig`. A game that rebuilds its world regularly and wants calendar continuity across a
rebuild reads the current date before shutting down and carries it forward in the library's own
starting-date settings.

`[TBD — needs discussion: those starting-date settings. Starting year and starting day were agreed in
principle; the names and defaults are not settled.]`

### `TIME_GAME_EPOCH` — read by Evennia, not by us

It sets the game clock's value at first server start, expressed as a bare count of game seconds. To
mean "year 850" you would write `850 × days_per_year × seconds_per_day` and put that number in your
settings.

This library reads `gametime(absolute=False)`, which zeroes that term. Where the calendar starts is
expressed in the library's own settings instead, in years and days rather than a timestamp — so
setting `TIME_GAME_EPOCH` will not move our dates. It still affects anything else in your game calling
`gametime(absolute=True)`.

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

This is what runs the boot check. Leave it out and the library is importable, validates nothing, and
a mistyped `CALENDAR_STARTING_YEAR` reaches the arithmetic instead of being refused.

## Required settings

None. This library has one setting and it is optional.

## Optional settings

### `CALENDAR_STARTING_YEAR` — what year the world begins in

```python
CALENDAR_STARTING_YEAR = 850
```

**Default: `1000`.** Leave it out and your world starts in year 1000, which is a perfectly good year
— the setting exists for games that want a particular one.

**If you set it, it must be zero or a positive integer.** A value that is not — a negative number,
`"850"`, `850.0` — is refused at boot with the setting named. There is one form to write. Year `0` is
allowed: a world may begin at zero.

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
| Phase | 6 hours — four per day |

A configurable year length cannot promise that. At 365 days the seasons stop being equal, the months
stop being whole, and the weeks stop lining up with the months — so the year length is not offered as
a knob rather than offered and then broken.

If your game needs a different calendar, this library is the wrong one.

## What is not checked for you

- **`INSTALLED_APPS`.** Leave the library out of it and `AppConfig.ready()` never runs, so nothing
  the library might validate gets validated. This is always the first thing to check when a library
  appears to be doing nothing.
- **Which `TIME_IGNORE_DOWNTIMES` branch you want.** Both are valid and the library cannot tell which
  one your game meant. See the `TIME_IGNORE_DOWNTIMES` table above.
- **Calendar continuity across a database wipe.** Nothing detects that the world's date went
  backwards.
