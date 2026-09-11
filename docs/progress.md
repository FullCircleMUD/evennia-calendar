# Progress

Running log of milestones with links to evidence. Reverse chronological — newest first.

## 2026-09-10 — logging binds through evennia-logging-extension, and the boot check logs again

87 tests. `log.py` is three lines — `calendar_log = make_logger("calendar.log")` — with the call
sites, the bound name and the filename all unchanged, and the extension declared in `pyproject.toml`.
It writes the pre-reactor window synchronously, which retires the rule the entry below recorded: a
line *can* reach disk from `AppConfig.ready()` now.

- **`check_settings()` logs its refusal at ERROR before raising** — `CF-11` and `CF-12`, reinstated
  with new meanings. Both read the line back from disk; the earlier mocked versions passed while
  nothing landed, which is why the plan wording forbids mocking the shim.
- **`SC-02` retired.** The no-op-outside-Evennia contract belonged to the old hand-rolled shim; the
  extension owns its delivery behaviour and covers it in its own suite.
- **Validated live in the demo gamedir** — boot line, a WARN, and an ERROR with traceback all
  delivered to `calendar.log`.
- One suite trap, documented at the test helper: Evennia caches log-file handles, so a test clearing
  `LOG_DIR` must truncate, never delete — a removed file leaves the cached handle appending to an
  unlinked inode and every later line silently vanishes.

## 2026-09-10 — run against a real game, which found two things the suite could not

86 tests. A demo gamedir under `examples/` boots a real Evennia server with the library installed, and
everything the library claims to do was watched happening in it.

**Proven live:** `game_date()` through a `gametime` command, the hour advancing between calls;
`phase_changed` and `day_changed` announcing; a consumer-registered `market_bell` firing on a
six-hour cycle, which is not one of the library's units; all three arriving on the same tick at a day
boundary, coarse and fine together. Reload survival too, unplanned — the server was reloaded
mid-session and the signals kept firing, so `at_server_start()` re-registered and re-connected after
the module state died.

**Two bugs, both from fixtures that encoded an assumption rather than the world's behaviour:**

- **Every field came back a float.** `gametime()` returns one, because `time.time()` does, and floor
  division on a float gives a float. Every case in the suite patched the clock with an *integer*, so
  88 passing tests said nothing about it — and the first thing a consumer wrote,
  `f"{date.hour:02d}"`, raised. Fixed by coercing at `_day_number()` and `_seconds_into_day()`, the
  two places the raw clock value enters, so every helper after them is integer arithmetic. `GD-04`
  now feeds a float and asserts every field is an `int`.
- **The boot check's logging never worked.** `check_settings()` runs from `AppConfig.ready()` during
  `django.setup()`, and Evennia's `log_file()` defers every write to the reactor's thread pool, which
  does not exist yet — the deferred is created, never runs, and dies with the process, leaving a
  zero-byte file. `CF-11` and `CF-12` passed throughout because they mocked the shim and asserted it
  was called. Both retired, the log call removed, and **the exception is the only channel at boot**.
  Recorded as a project-level rule in
  [library-standards.md](../../../design/library-standards.md) § Nothing can be logged from
  `AppConfig.ready()`, since it applies to every library.

**And one design property proven by accident.** The float bug was breaking the demo's receivers on
every watch change before anyone noticed, and `send_robust` did exactly what it was built to do — the
failure was logged with the receiver's name and a full traceback, and the clock kept ticking. Nothing
would have tested that deliberately.

Also learned: **the detection window is exactly `TIME_FACTOR` game seconds**, because the tick is
always one real second. The demo runs at 360, so announcements land up to six game minutes late and
you can see it. At FCM's 24 the window is 24 game seconds, which displays as `HH:00` — at any factor
of 60 or below an hourly announcement always reads on the hour.

Still untested live: `week`, `month`, `season` and `year` firing. They go through the same
`_UNIT_SIGNALS` loop as the three that did, and are unit-tested. Accepted on that basis.

Not yet run against a real game: nothing. That line has been in this log since the scaffold and is
now gone.

## 2026-09-10 — the clock announces, and a consumer can add their own

87 tests, all passing. Feature complete against what it set out to do, untried against a real game.
Thirty cases — `CU-01` to `CU-05`, `CK-01` to `CK-08`, `SG-01` to `SG-10`, `RS-01` to `RS-07`.

- **A Twisted `LoopingCall`, not an Evennia script.** Nothing persistent to get stuck stopped,
  recreated at every boot, started from the consumer's `at_server_start()`. Not from
  `AppConfig.ready()`, which also runs during `evennia migrate` where a clock should not spin up.
- **One real second, and the cost was measured rather than assumed.** `game_date()` is 8.78
  microseconds, so a one-second tick is 0.0009% of a core — about one second of CPU every 31 hours.
  Tick rate buys detection latency and nothing else: the work happens at the *transition* rate, which
  the calendar fixes.
- **The comparison is a pure function of two dates.** `_changed_units()` takes `previous` and
  `current` and returns a frozenset of unit names; the clock holds the memory. That split is what
  makes the arithmetic testable without a clock and the lifecycle testable without a reactor.
- **A unit turned over if it or anything coarser did.** `_UNIT_FIELDS` maps each unit to the fields
  that identify it — day is `(year, day_of_year)` — because two dates a year apart share a
  day-of-year and are not the same day.
- **Seven Django signals, sent with `send_robust`.** One consumer's broken handler cannot silence the
  subscriber behind it. Failures are logged with the receiver's name, since a game running several
  libraries needs to know whose handler broke.
- **`register_signal()` lets a consumer add their own**, giving a signal, a pure key function over the
  date, and a name. The clock compares `key(previous)` against `key(current)` exactly as it does the
  built-ins. A key that raises is logged and skipped, and the other units still announce.
- **A name in use is refused, never replaced.** Two developers on one game can both reach for
  `"market_day"`, and the second silently clobbering the first would stop that subsystem firing with
  nothing to say why. The seven built-in names are reserved and cannot be unregistered either.

Two things found by running it rather than reasoning about it:

- **`Signal.connect()` holds receivers weakly.** A demo written with inline lambdas fired nothing at
  all — they were collected before the first tick, and the connections went with them. Silently. That
  is the trap consumers will hit, and it now has its own section in
  [custom-signals.md](custom-signals.md).
- **`RS-01` failed on a one-based field.** The market key `day_of_year // 10` at elapsed days 10 and
  11 is `11 // 10` and `12 // 10` — both 1, no boundary crossed. The code was right and the test was
  wrong, which is the same mistake a consumer will make writing their first key function. Recorded in
  the custom-signals guide.

Also landed: [custom-signals.md](custom-signals.md), and `installing.md` grew a fourth step covering
the clock, the seven signals and how to subscribe without losing your receiver.

## 2026-09-10 — the whole date, and the day divided into watches

57 tests, all passing. `game_date()` returns ten fields. Twenty-two cases — `MO`, `WK`, `SE`, `TD`,
`PH` and `CN-05`.

- **Six four-hour watches, not four six-hour phases.** The traditional nautical watches land on
  exactly these hours without being nudged — Middle, Morning, Forenoon, Afternoon, Dog, First — and
  six gives a game three choices of night length (one, two or three dark watches, so 4, 8 or 12
  hours) where four offered only 6 or 12. `First` sits at index 5 because the naval day began at
  noon; historically right, reads oddly, kept for the flavour.
- **Every calendar position counts from one; the clock counts from zero.** One rule, so there is
  nothing to remember about which field is which: subtract one to index a name tuple. `hour` and
  `minute` are the exception because 00:00 is midnight rather than a zeroth hour. The offset is
  applied once, at assembly, and the helpers stay zero-based throughout.
- **`GD-02` is the only case that pins the offset**, by asserting the whole tuple. A dropped `+ 1`
  fails there and nowhere else.
- **Half-open boundaries in the docs** — 00:00–03:59 rather than 00:00–04:00 — so which watch owns
  04:00 is never a question.
- **Constants for every divisor**, so `clock.py` holds no magic numbers.

Also recorded: **synchronising the clock across instances is not this library's job.** Evennia derives
game time from a per-instance `server_epoch`, so separate databases mean separate epochs — a gap that
exists with no calendar installed at all. Whatever provides the multi-instance deployment owns it;
we report what `gametime()` says. Ruled in [../CLAUDE.md](../CLAUDE.md) § Out of scope.

And: **the name stays `evennia-calendar`.** It is narrower than the job — the library is about game
time in every unit, not only dates — but the churn of renaming to `evennia-timekeeper` was not worth
it. `README.md` and `CLAUDE.md` describe the real scope instead.

## 2026-09-08 — the calendar's vocabulary

35 tests, all passing. `Season`, `DAY_NAMES` and `MONTH_NAMES` declared in `config.py`. Nothing
indexes them yet — the fields that will are the next slice. Four cases, `CN-01` to `CN-04`.

- **`Season` is an enum, the names are tuples.** A game branches on the season, so `Season.WINTER`
  earns an enum over `season == 3`. The day and month names are looked up by index and displayed,
  nothing computes from them, so a tuple a consumer can swap in one line beats something to subclass.
- **`Season`'s values are its position in the year**, making the lookup `Season(day_of_year // 90)`
  with no mapping table in between. `SPRING = 0` is what makes
  [installing.md](installing.md)'s promise true — that every world begins on day 0, the first day of
  spring — rather than an arbitrary ordering.
- **The lengths are load-bearing and have their own cases.** Eleven months does not raise; it returns
  the wrong month for a third of the year. `CN-01` and `CN-02` are both needed, because pinning the
  values 0–3 does not stop a fifth member being added beside them.
- **The names are real and checked against sources**, not invented: the ten days are the Balinese
  Pawukon calendar's Dasawara cycle, the twelve months are from Old Javanese inscriptions. Diacritics
  stripped — terminals vary and players may end up typing them.
- **They are placeholders and say so at the declaration.** Naming the days of an invented world is the
  consumer's business; the library ships a working set so it is not empty, and expects to be
  overridden.
- **No case pins the individual names.** Nothing computes from the strings, so such a test would only
  restate the tuple and be edited every time the tuple was. Length and order are what matter.

## 2026-09-08 — a stable public import path

31 tests, all passing. `from evennia_calendar import game_date` works. Two cases, `SC-03` and `SC-04`.

- **The re-export has to be lazy.** The package sits in `INSTALLED_APPS`, so `__init__.py` runs during
  `django.setup()`, and a plain `from .clock import game_date` there pulls in
  `evennia.utils.gametime`, which reaches for a model before the app registry is built. Tried it and
  the server did not start — `AppRegistryNotReady`. A module-level `__getattr__` resolves the names on
  first use instead.
- **What it buys is the import path, not the keystrokes.** `__all__` states the contract, so
  `clock.py` is ours to split or rename without breaking a consumer.
- **Both cases were mutation-checked**, because both passed the moment they were written. Removing
  `__getattr__` fails `SC-03` alone; `SC-04` still passes there, since Python raises `AttributeError`
  by itself when no `__getattr__` exists. So that case cannot catch an absent one, and the plan says
  so.
- **The `__all__` guard prevents infinite recursion, not just silent typos.** The second mutation
  found it: without the guard, `from evennia_calendar import clock` inside the function re-enters the
  function looking for `clock`. The guard was written for the wrong reason and happened to be right;
  it is now commented at the code so it is not tidied away.

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
  10, four seasons of 90, a 24-hour day and six four-hour watches. Fixed because every unit then
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
