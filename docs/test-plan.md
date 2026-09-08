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

## Fixtures

The fake objects the suite needs, named and purposed.

| Fixture | Purpose |
|---|---|
| `django.test.override_settings` | Declares, changes or removes `CALENDAR_STARTING_YEAR` per case. The `CF` cases need nothing beyond it — there is one setting and it holds a plain value |

A fake clock will be needed as soon as anything derives a date, since the whole library is a function
of the number the time source returns. It is not listed until the seam it plugs into is agreed.

## Cases

One section per function or surface, each with its own prefix and its own table.

### `SC` — the scaffold

| ID | Case | Test function |
|---|---|---|
| SC-01 | The package is importable and carries a version | `test_sc_01_the_package_is_importable_and_versioned` |
| SC-02 | The log shim is a silent no-op outside an Evennia engine, returning `None` rather than raising | `test_sc_02_the_log_shim_is_a_no_op_outside_evennia` |

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
