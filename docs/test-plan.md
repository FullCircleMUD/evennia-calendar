# Test plan

Every test case the library commits to covering, and the test function that covers it. The library is
built test-first: cases are agreed here, tests are written against them, then the implementation is
written to pass. The **Test function** column is the auditable trail — it is filled in as each test is
written, so an empty cell means the case is agreed but not yet covered.

Case IDs are stable and referenceable. Do not renumber; retire an ID rather than reuse it. Every test
function carries its case ID as its docstring, so the trail reads in both directions.

All test functions live in `src/evennia_calendar/tests.py`.

Behaviour is agreed here first, before any test or code — see
[test-first-process.md](../../../design/test-first-process.md).

**The library is at an early stage.** A case appears here when it has been discussed, not when it
seems likely.

| Prefix | Covers |
|---|---|
| `SC` | The scaffold — the library is installed and the runner reaches it |
| `CF` | `CALENDAR_STARTING_YEAR` — its accessor, and the boot check that judges a value the consumer set |
| `CN` | The calendar's vocabulary — `Season`, `DAY_NAMES` and `MONTH_NAMES` |
| `DN` | `_day_number()` — elapsed game seconds to an absolute day count |
| `DY` | `_day_of_year()` — an absolute day count to a position within the year |
| `YR` | `_year()` — an absolute day count and a starting year to the year |
| `MO` | `_month()` and `_day_of_month()` — where in the year by month |
| `WK` | `_week()` and `_day_of_week()` — where in the year by week |
| `SE` | `_season()` — a day of the year to a `Season` |
| `TD` | `_seconds_into_day()`, `_hour()` and `_minute()` — the time of day |
| `PH` | `_phase()` — an hour to one of the six four-hour watches |
| `GD` | `GameDate` and `game_date()` — the frozen result, and the factory that reads the clock and composes one |

## Fixtures

The fake objects the suite needs, named and purposed.

| Fixture | Purpose |
|---|---|
| `django.test.override_settings` | Declares, changes or removes `CALENDAR_STARTING_YEAR` per case. The `CF` cases need nothing beyond it — there is one setting and it holds a plain value |
| `mock.patch("evennia_calendar.clock.gametime")` | The fake clock, needed by the `GD` cases alone. Patched at the library's import site, not at Evennia's, so nothing else in the process is affected |

The `DN`, `DY` and `YR` cases need no fixtures at all: each helper takes integers and returns
integers, so a case is a call and an assertion. That is the point of having them — only the factory
has to reach for a clock.

## Cases

One section per function or surface, each with its own prefix and its own table.

### `SC` — the scaffold

| ID | Case | Test function |
|---|---|---|
| SC-01 | The package is importable and carries a version | `test_sc_01_the_package_is_importable_and_versioned` |
| SC-02 | The log shim is a silent no-op outside an Evennia engine, returning `None` rather than raising | `test_sc_02_the_log_shim_is_a_no_op_outside_evennia` |
| SC-03 | The public surface resolves from the package root — `from evennia_calendar import game_date` gives the same object as `evennia_calendar.clock.game_date` | `test_sc_03_the_public_surface_resolves_from_the_package_root` |
| SC-04 | An unknown attribute on the package raises `AttributeError` rather than resolving to something | `test_sc_04_an_unknown_package_attribute_raises` |

`SC-03` and `SC-04` cover the package's module-level `__getattr__`. The re-export has to be lazy: this
package sits in `INSTALLED_APPS`, so its `__init__.py` runs during `django.setup()`, and a plain
`from .clock import game_date` there pulls in `evennia.utils.gametime`, which reaches for a model
before the app registry is built — `AppRegistryNotReady`, and the server does not start.

That the export is *lazy* is proven by the suite booting at all. What `SC-03` adds is that it still
resolves, and `SC-04` that a `__getattr__` cannot quietly answer for names it does not have.

Both were mutation-checked rather than trusted, because both passed the moment they were written.
Removing `__getattr__` fails `SC-03` alone — `SC-04` still passes there, since Python raises
`AttributeError` by itself when no `__getattr__` exists, so that case cannot catch an absent one.
Dropping the `__all__` guard instead fails `SC-04`, and revealed that the guard prevents infinite
recursion rather than merely silent typos: `from evennia_calendar import clock` inside the function
re-enters it looking for `clock`. That is recorded at the code.

### `CF` — `CALENDAR_STARTING_YEAR`

The library's only setting. It is optional: absent, the default applies, and there is nothing to
refuse. Set, it must be zero or a positive integer — so the check judges a value that is *there*, and
never complains about one that is not.

| ID | Case | Test function |
|---|---|---|
| CF-01 | The accessor returns the default of 1000 when the setting is not declared | `test_cf_01_the_accessor_defaults_when_the_setting_is_absent` |
| CF-02 | The accessor returns the consumer's value when the setting is declared | `test_cf_02_the_accessor_returns_the_declared_value` |
| CF-03 | The boot check passes when the setting is not declared — absence is what the default is for | `test_cf_03_the_check_passes_when_the_setting_is_absent` |
| CF-04 | The boot check passes for a positive integer | `test_cf_04_the_check_passes_for_a_positive_integer` |
| CF-05 | The boot check passes for `0` — a world may begin in year zero | `test_cf_05_the_check_passes_for_zero` |
| CF-06 | The boot check refuses a negative integer | `test_cf_06_the_check_refuses_a_negative_integer` |
| CF-07 | The boot check refuses a string, including one that looks like a number (`"1000"`) | `test_cf_07_the_check_refuses_a_string` |
| CF-08 | The boot check refuses a float, including a whole-numbered one (`1000.0`) | `test_cf_08_the_check_refuses_a_float` |
| CF-09 | The refusal names `CALENDAR_STARTING_YEAR`, so a consumer knows which setting to fix | `test_cf_09_the_refusal_names_the_setting` |
| CF-10 | The boot check refuses a boolean, which Python counts as an integer | `test_cf_10_the_check_refuses_a_boolean` |
| CF-11 | A refusal is written to `calendar.log` at `ERROR`, carrying the same text as the exception, before the exception is raised | `test_cf_11_a_refusal_is_logged_with_the_exception_text` |
| CF-12 | A check that passes logs nothing | `test_cf_12_a_passing_check_logs_nothing` |

`CF-07` and `CF-08` are separate cases because they defeat different naive implementations: a
coercing check (`int(value) > 0`) accepts the string, and a bare comparison (`value > 0`) accepts the
float. One form to write, as the siblings do.

`CF-10` exists because `bool` is a subclass of `int` in Python: `isinstance(True, int)` is `True` and
`True >= 0`, so the obvious type check accepts `True` and quietly reads it as year 1. Nothing about
the value looks wrong afterwards, which is what makes it worth a case of its own.

`CF-11` and `CF-12` are the logging pair. A refusal stops the boot, and the traceback scrolls past —
so the reason has to be somewhere a consumer can go back and read. **The logged text is the exception
text, not a second wording of it**: two messages that drift apart is worse than one, and there is
nothing the log needs to say that the refusal does not.

`CF-12` exists to keep `calendar.log` quiet. A library that writes a line on every successful boot
trains its consumer to ignore the file, which costs exactly when it matters. The log has one thing to
say and only says it when it is true.

There is no "every problem in one raise" case yet — with a single setting there can only ever be one
problem. It lands with the second setting, if there is one.

### `CN` — the calendar's vocabulary

Three declarations in `config.py`, all indexed by arithmetic on `day_of_year`. Their **lengths are
load-bearing**: a tuple of eleven months does not raise, it silently returns the wrong month for a
third of the year, or an `IndexError` on the last one.

`Season` is an enum because games branch on it — `Season.WINTER` beats `season == 3`. The day and
month names are tuples because they are display strings and the part that is invention, so a consumer
replacing them should not have to subclass anything.

| ID | Case | Test function |
|---|---|---|
| CN-01 | `Season` has exactly four members | `test_cn_01_there_are_exactly_four_seasons` |
| CN-02 | The seasons run spring, summer, autumn, winter with values 0–3, so `Season(0)` is `SPRING` | `test_cn_02_the_seasons_run_spring_first_with_values_zero_to_three` |
| CN-03 | `DAY_NAMES` has exactly ten entries, one per day of the week | `test_cn_03_there_are_exactly_ten_day_names` |
| CN-04 | `MONTH_NAMES` has exactly twelve entries, one per month | `test_cn_04_there_are_exactly_twelve_month_names` |
| CN-05 | `PHASE_NAMES` has exactly six entries, one per watch | `test_cn_05_there_are_exactly_six_phase_names` |

`CN-01` and `CN-02` are both needed: pinning the values 0–3 does not stop a fifth member being added
alongside them.

`CN-02` is not data testing itself — the order is a documented promise. [installing.md](installing.md)
tells a consumer their world begins on day 0, the first day of spring, and that is only true while
`SPRING` is 0. The individual day and month *names* get no such case: nothing computes from them, so
a test would only restate the tuple and would be edited every time the tuple was.

### The shape: helpers convert, the factory composes

Each conversion is a private helper taking integers and returning integers, with its own cases. The
factory reads the clock, calls them, and assembles the result — so its own cases only have to prove
that it reads and composes, not that arithmetic it delegates is correct.

That is deliberate and it is why the case count looks high for two fields. Every field added later —
month, week, season, hour, phase — is one more helper with three or four narrow cases, and the
factory's cases do not grow. The alternative, exercising every conversion through the factory, means
each new field needs cases that construct a `gametime` value landing on the right day after the
offset, and a failure points at a chain rather than at a conversion.

The cost, stated plainly: these cases test private functions, so restructuring the helpers breaks
tests even where behaviour did not change. Accepted — these are fixed arithmetic conversions against
a calendar that is deliberately not configurable, so there is little for a restructure to be
responding to.

### `DN` — `_day_number()`

Elapsed game seconds to an absolute day count. One game day is 86,400 game seconds.

| ID | Case | Test function |
|---|---|---|
| DN-01 | Zero seconds is day 0 | `test_dn_01_zero_seconds_is_day_zero` |
| DN-02 | 86,399 seconds is still day 0 — it floors rather than rounds | `test_dn_02_one_second_short_of_a_day_is_still_day_zero` |
| DN-03 | 86,400 seconds is day 1 | `test_dn_03_exactly_one_day_is_day_one` |
| DN-04 | 62,640,000 seconds is day 725 — it divides rather than counting a single boundary | `test_dn_04_it_divides_rather_than_counting_one_boundary` |

`DN-02` and `DN-03` are a pair: a rounding implementation passes the second and fails the first.
`DN-04` defeats an implementation that returns 1 for anything past one day.

### `DY` — `_day_of_year()`

An absolute day count to a position within the year. The year is 360 days.

| ID | Case | Test function |
|---|---|---|
| DY-01 | Day 0 is day-of-year 0 | `test_dy_01_day_zero_is_day_of_year_zero` |
| DY-02 | Day 359 is day-of-year 359 — the last day before the year wraps | `test_dy_02_day_359_is_the_last_day_of_the_year` |
| DY-03 | Day 360 is day-of-year 0 | `test_dy_03_day_360_wraps_to_zero` |
| DY-04 | Day 725 is day-of-year 5 — it wraps more than once | `test_dy_04_it_wraps_more_than_once` |

### `YR` — `_year()`

An absolute day count and a starting year to the year. Takes the starting year as an argument rather
than reading the setting, so it stays a pure conversion and the accessor is the factory's business.

| ID | Case | Test function |
|---|---|---|
| YR-01 | Day 0 is the starting year | `test_yr_01_day_zero_is_the_starting_year` |
| YR-02 | Day 359 is still the starting year — it does not roll early | `test_yr_02_day_359_does_not_roll_early` |
| YR-03 | Day 360 is the starting year plus one | `test_yr_03_day_360_is_the_next_year` |
| YR-04 | Day 725 is the starting year plus two | `test_yr_04_it_divides_rather_than_counting_one_boundary` |

`YR-02` and `YR-03` are the boundary pair. `YR-04` exists because an implementation that adds one
year past 360, rather than dividing, passes everything above it.

### `MO` — `_month()` and `_day_of_month()`

Twelve months of thirty days, both off `day_of_year`. Each case asserts both, because "what month and
day is this" is one question.

| ID | Case | Test function |
|---|---|---|
| MO-01 | Day 0 is month 0, day 0 of that month | `test_mo_01_day_zero_is_the_first_day_of_the_first_month` |
| MO-02 | Day 29 is month 0, day 29 — the last day of the first month | `test_mo_02_day_29_is_the_last_day_of_the_first_month` |
| MO-03 | Day 30 is month 1, day 0 — the month rolls | `test_mo_03_day_30_rolls_into_the_second_month` |
| MO-04 | Day 359 is month 11, day 29 — the last day of the year, and the month does not run past eleven | `test_mo_04_the_last_day_of_the_year_does_not_run_past_month_eleven` |

`MO-04` is the one that matters most: a month of 12 indexes past the end of `MONTH_NAMES`, and the
whole reason `CN-04` pins that tuple's length is that the pair fails together.

### `WK` — `_week()` and `_day_of_week()`

Thirty-six weeks of ten days. Because 360 divides by 10 exactly, it makes no difference whether the
week runs continuously across years or resets each year — both give this answer.

| ID | Case | Test function |
|---|---|---|
| WK-01 | Day 0 is week 0, day 0 of that week | `test_wk_01_day_zero_is_the_first_day_of_the_first_week` |
| WK-02 | Day 9 is week 0, day 9 — the last day of the first week | `test_wk_02_day_9_is_the_last_day_of_the_first_week` |
| WK-03 | Day 10 is week 1, day 0 | `test_wk_03_day_10_rolls_into_the_second_week` |
| WK-04 | Day 359 is week 35, day 9 — the week does not run past thirty-five | `test_wk_04_the_last_day_of_the_year_does_not_run_past_week_35` |

### `SE` — `_season()`

Four seasons of ninety days, returning a `Season` rather than an integer, so a consumer branches on
the enum.

| ID | Case | Test function |
|---|---|---|
| SE-01 | Day 0 is spring — the promise made in installing.md | `test_se_01_day_zero_is_spring` |
| SE-02 | Day 89 is still spring | `test_se_02_day_89_is_still_spring` |
| SE-03 | Day 90 is summer | `test_se_03_day_90_is_summer` |
| SE-04 | Day 359 is winter, and the lookup does not run past the last member | `test_se_04_the_last_day_of_the_year_is_winter` |

### `TD` — `_seconds_into_day()`, `_hour()` and `_minute()`

The time of day. `_seconds_into_day()` keeps precisely what `_day_number()` discards — both take
elapsed game seconds, one divides and one takes the remainder.

`minute` exists for display and nothing computes from it. It is here because **a clock without a
minute hand gives a player no way to judge how long something took** — not because it was cheap to
add. There is deliberately no `second`: at any usable time factor it is noise.

| ID | Case | Test function |
|---|---|---|
| TD-01 | Zero elapsed seconds is 0 seconds into the day | `test_td_01_zero_elapsed_is_zero_seconds_into_the_day` |
| TD-02 | One day plus one second is 1 second into the day — it keeps what `_day_number()` drops | `test_td_02_it_keeps_what_the_day_number_discards` |
| TD-03 | 0 seconds into the day is hour 0, minute 0 | `test_td_03_the_start_of_the_day_is_hour_zero_minute_zero` |
| TD-04 | 13h 32m into the day is hour 13, minute 32 | `test_td_04_thirteen_hours_thirty_two_minutes_in` |
| TD-05 | The last second of the day is hour 23, minute 59 — neither runs over | `test_td_05_the_last_second_of_the_day_does_not_run_over` |

### `PH` — `_phase()`

Six watches of four hours, taken from the hour rather than from the seconds, so the phase cannot
disagree with the clock beside it.

Six rather than four quarters because the traditional nautical watches land on exactly these hours
without being nudged, and because six gives a game three choices of night length — one, two or three
dark watches, so 4, 8 or 12 hours — where four phases offered only 6 or 12.

| Watch | Hours |
|---|---|
| 0 Middle | 00:00–03:59 |
| 1 Morning | 04:00–07:59 |
| 2 Forenoon | 08:00–11:59 |
| 3 Afternoon | 12:00–15:59 |
| 4 Dog | 16:00–19:59 |
| 5 First | 20:00–23:59 |

`First` sits at index 5 rather than 0 because the naval day began at noon, so the first watch of the
new day started at 20:00. Historically right, and it reads oddly in a list that starts at midnight —
kept anyway, since the flavour is the whole reason for the naming.

| ID | Case | Test function |
|---|---|---|
| PH-01 | Hour 0 is watch 0 | `test_ph_01_hour_zero_is_the_first_watch` |
| PH-02 | Hour 3 is still watch 0 | `test_ph_02_hour_3_is_still_the_first_watch` |
| PH-03 | Hour 4 is watch 1 | `test_ph_03_hour_4_is_the_second_watch` |
| PH-04 | Hour 23 is watch 5, and does not run past five | `test_ph_04_the_last_hour_does_not_run_past_the_sixth_watch` |

The field stays `phase` rather than `watch`, and the names live in `PHASE_NAMES`. Same split as the
days and months: a neutral number on `GameDate`, flavour in a tuple a game replaces.

### `GD` — `GameDate` and `game_date()`

The first cut carries two fields, `year` and `day_of_year`. `GameDate` is frozen and nothing stores
one — every call builds a new instance from the clock, so a consumer holding an old one is holding a
snapshot rather than something that goes stale in place.

| ID | Case | Test function |
|---|---|---|
| GD-01 | `GameDate` is frozen — assigning to a field raises rather than mutating the instance | `test_gd_01_the_dataclass_is_frozen` |
| GD-02 | `game_date()` reads the clock and returns **every** field composed from it | `test_gd_02_the_factory_reads_the_clock_and_composes_every_field` |
| GD-03 | The year comes through the `CALENDAR_STARTING_YEAR` accessor, so an undeclared setting gives the default of 1000 | `test_gd_03_the_year_comes_through_the_accessor` |

Three cases, and they stay three however many fields are added. `GD-02` proves the clock is read and
the helpers are composed; `GD-03` proves the offset arrives through the accessor rather than being
reached for directly or hardcoded.

**`GD-02` widens as fields are added** rather than gaining a sibling case. It asserts the whole
result, so a factory that computes a field and forgets to pass it fails here — which a case pinned to
two named fields would not catch. The ID is not being reused: it is the same behaviour against a
wider object.

It is also **the only case that pins the one-based offset**. The `MO`, `WK` and `DY` helpers are
zero-based, so `_month(5)` is `0` while `game_date().month` for the same day is `1`. That difference
is deliberate — anything a player sees as a number counts from one, anything that only indexes a name
tuple counts from zero — and `GD-02` is where dropping a `+ 1` at assembly gets caught.

`GD-01` builds its instance through `game_date()` rather than constructing one by hand, so it does not
have to be edited every time the dataclass gains a field.

## Open decisions

Every `[TBD]` in this repo, collected. A case cannot be written against an open decision.

- **How the time source is supplied.** Taking it as an injectable parameter rather than importing
  `gametime` inside the library was agreed in principle — the shape of that seam is not.
- **The public surface.** One call returning everything, or separate functions for date, season and
  phase. It decides what the arithmetic returns, so it is settled before that is written.
- **Transitions.** "The season just changed" needs a previous value to compare against, which is
  state — and the library holds none. Whether that is a pure "what changed between A and B" function
  with the consumer owning the tick, or a carve-out from the derived-never-stored principle, is open.
- **Whether moon phases are in scope.** Out for now, pending research.

Settled, and recorded here so they are not reopened: the calendar is fixed at a 360-day year of 12
months of 30 days, 36 weeks of 10 days, four seasons of 90 days, a 24-hour day and six four-hour
watches. Seasons are the four standard names. There is no `days_per_year`, `hours_per_day` or
`starting_day` setting — a game starts on day 0 of whatever year it declares.
