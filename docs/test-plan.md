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
| `DN` | `_day_number()` — elapsed game seconds to an absolute day count |
| `DY` | `_day_of_year()` — an absolute day count to a position within the year |
| `YR` | `_year()` — an absolute day count and a starting year to the year |
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

### `GD` — `GameDate` and `game_date()`

The first cut carries two fields, `year` and `day_of_year`. `GameDate` is frozen and nothing stores
one — every call builds a new instance from the clock, so a consumer holding an old one is holding a
snapshot rather than something that goes stale in place.

| ID | Case | Test function |
|---|---|---|
| GD-01 | `GameDate` is frozen — assigning to a field raises rather than mutating the instance | `test_gd_01_the_dataclass_is_frozen` |
| GD-02 | `game_date()` reads the clock and returns both fields composed from it | `test_gd_02_the_factory_reads_the_clock_and_composes_both_fields` |
| GD-03 | The year comes through the `CALENDAR_STARTING_YEAR` accessor, so an undeclared setting gives the default of 1000 | `test_gd_03_the_year_comes_through_the_accessor` |

Three cases, and they stay three however many fields are added. `GD-02` proves the clock is read and
the helpers are composed; `GD-03` proves the offset arrives through the accessor rather than being
reached for directly or hardcoded.

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
months of 30 days, 36 weeks of 10 days, four seasons of 90 days, a 24-hour day and four six-hour
phases. Seasons are the four standard names. There is no `days_per_year`, `hours_per_day` or
`starting_day` setting — a game starts on day 0 of whatever year it declares.
