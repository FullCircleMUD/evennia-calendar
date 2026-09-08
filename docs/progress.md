# Progress

Running log of milestones with links to evidence. Reverse chronological — newest first.

## 2026-09-08 — the clock, and a date to show for it

29 tests, all passing. `game_date()` returns the world's year and day of that year. Fifteen cases,
`DN-01` to `DN-04`, `DY-01` to `DY-04`, `YR-01` to `YR-04` and `GD-01` to `GD-03`.

- **Helpers convert, the factory composes.** `_day_number()`, `_day_of_year()` and `_year()` each take
  integers and return integers; `game_date()` reads the clock, calls them, and assembles a
  `GameDate`. Chosen for the test shape rather than the code shape — twelve of the fifteen cases are a
  call and an assertion, needing no clock, no settings and no mocking.
- **The factory's cases stay at three however many fields arrive.** Every field still to come — month,
  week, season, hour, phase — is one more helper with its own narrow cases. Exercising each new
  conversion through the factory instead would mean constructing a `gametime` value that lands on the
  right day after the offset, and a failure that points at a chain rather than a conversion.
- **`_year()` takes the starting year as an argument** rather than reading the setting, so it stays a
  pure conversion and the accessor remains the factory's business. `GD-03` is what proves the factory
  actually goes through it.
- **`GD-02` asserts the call is `gametime(absolute=False)`**, not merely that the clock was read. That
  puts the decision to ignore `TIME_GAME_EPOCH` in a test rather than only in prose.
- **Floor division throughout, never `datetime`.** `DN-02` and `DN-03` are the pair that catches a
  rounding implementation; `DY-04` and `YR-04` catch one that handles a single year boundary rather
  than dividing.
- **`GameDate` is frozen and nothing stores one.** A consumer holding an instance holds a snapshot.

`gametime` is imported at module scope in `clock.py` — the one place outside `log.py` that reaches for
Evennia, commented as the standards require, and a single name for the suite to patch.

Still open: how a consumer imports the public surface. `from evennia_calendar.clock import game_date`
works today; re-exporting from `__init__.py` would read better but runs `clock.py`'s Evennia import
while Django is still building its app registry, so it needs checking rather than assuming.

## 2026-09-08 — a game can be configured, and refused

14 tests, all passing. The library has one setting, it is validated at boot, and a refusal reaches
`calendar.log`. Nothing derives a date yet. Twelve cases, `CF-01` to `CF-12`.

- **The calendar is fixed; only where it starts is not.** 360-day year, 12 months of 30, 36 weeks of
  10, four seasons of 90, a 24-hour day and four six-hour phases. Fixed because every unit then
  divides the one above it with nothing left over, which a configurable year length cannot promise —
  at 365 the seasons stop being equal and the months stop being whole. Recorded in
  [installing.md](installing.md) § The calendar itself is not configurable.
- **`CALENDAR_STARTING_YEAR`** is the whole settings surface, and it is optional. Absence is the case
  the default exists for, so `check_settings()` never complains about a setting that is not there —
  `CF-03` pins that, because a naive `if not value: raise` would fail it.
- **Zero is allowed, a negative is not.** A world may begin at year zero.
- **A string and a float are refused separately**, `CF-07` and `CF-08`, because they defeat different
  naive implementations: `int(value) > 0` accepts `"1000"`, and `value >= 0` accepts `1000.0`. One
  form to write.
- **A boolean is refused explicitly**, `CF-10`. `bool` subclasses `int`, so `isinstance(True, int)` is
  `True` and `True >= 0` — the obvious type check accepts it and reads it as year 1, with nothing
  about the value looking wrong afterwards. The exclusion goes before the int check, not folded into
  it.
- **The accessor neither coerces nor validates.** Boot has already refused anything unusable, so its
  whole job is to defer the read and supply the fallback.
- **The refusal names the setting** — `CF-09`. A message that says a value is wrong without saying
  which setting held it costs a grep.
- **The refusal is logged before it is raised**, at `ERROR`, with the exception's own text rather than
  a second wording of it — `CF-11`. A failed boot scrolls its traceback past; the log is where a
  consumer goes back to read why the game would not start. Two messages that could drift apart is
  worse than one.
- **`calendar.log` stays quiet otherwise** — `CF-12`. A line on every successful boot trains a
  consumer to ignore the file, which costs exactly when it matters. `config.py` is the one module that
  imports the shim at module scope, which is what the standards' `log.py` constant exemption exists
  for.

Also settled and recorded: the three Evennia time settings (`TIME_FACTOR`, `TIME_IGNORE_DOWNTIMES`,
`TIME_GAME_EPOCH`) are Evennia's. This library reads them, never sets them, and documents what each
default means — [installing.md](installing.md) § Evennia's time settings.

Still open, and the next conversation: how the time source is supplied, what the public surface looks
like, and whether transitions belong here at all given the library holds no state.

## 2026-09-08 — scaffold

The repo is set up to [library-standards.md](../../../design/library-standards.md) and the test runner
reaches the package. No library code.

- **Package, runner and test infrastructure** — `src/evennia_calendar/`, `runtests.py`,
  `tests/test_settings.py`. Two scaffold cases pass: the package imports and carries a version, and
  the log shim is a silent no-op outside an Evennia engine.
- **The log shim** — `calendar_log`, writing to `calendar.log`, copied verbatim from
  `evennia-message-bus` with the name and filename changed.
- **No tables, no alias, no router.** The calendar is derived from game time, so there is nothing to
  store. Recorded as a ruling in [../CLAUDE.md](../CLAUDE.md).
- **No `config.py` or `apps.py`.** The library reads no settings and validates nothing yet, so
  neither has anything to hold. They land with the first setting.
- **Documentation surfaces** — `README.md`, `CLAUDE.md`, and this wiki with its index, installing
  document, test plan and interoperability statement.

What was decided in the conversation that produced this scaffold, and is recorded as principles in
[../CLAUDE.md](../CLAUDE.md):

- **The calendar is derived, never stored.** It is a function of the number Evennia hands back, so it
  survives a reload and every process agrees without coordinating.
- **Evennia owns the clock, the library owns the calendar.** Read the game seconds, do our own
  integer division. Never `datetime` — reading the game timestamp through `datetime.fromtimestamp`
  borrows a 365-day year into a world that does not have one, which is the defect being extracted
  away from.
- **`gametime(absolute=False)`**, so Evennia's epoch term is zeroed and the starting date is expressed
  in the library's own settings, in years and days.
- **The consumer's Evennia time settings are theirs.** `TIME_IGNORE_DOWNTIMES` in particular: both
  branches are legitimate, the implications differ, and the library documents them rather than
  choosing. See [installing.md](installing.md) § Evennia's time settings.

What is not here: the calendar itself. The system being extracted is in FullCircleMUD's
`typeclasses/scripts/day_night_service.py` and `season_service.py`. The settings that describe a
calendar's shape were discussed but not settled — see the `[TBD]`s in [installing.md](installing.md).
