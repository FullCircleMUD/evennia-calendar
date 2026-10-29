# Custom signals

How to have the calendar clock fire a signal of your own, on a condition you define — a market every
tenth day, a festival on a particular date, a fortnight, a tax day, a cadence in real seconds. You
write a pure function of the date; the clock does the remembering and the comparing.

This page assumes you already have the clock running and know how to subscribe to the seven built-in
signals. If not, start with [installing.md](installing.md).

## The shape

Three things: a signal you own, a function that derives a value from a `GameDate`, and a name.

```python
from django.dispatch import Signal
from evennia_calendar.service import register_signal

market_day = Signal()

register_signal(
    market_day,
    key=lambda date: date.day_of_year // 10,
    name="market_day",
)
```

On every tick the clock computes `key(previous)` and `key(current)`. When they differ, your signal is
sent, carrying `previous` and `current` — the same payload the built-in signals use, so a receiver
looks identical whichever it is connected to.

You never store a previous value and you never write a comparison.

**Your key is evaluated every tick**, whether or not anything on the calendar moved. It is your
condition, and when it is worth asking is not ours to decide.

## A cadence in real time

Every field on a `GameDate` is a position in game time and moves at `TIME_FACTOR` — except two.
`elapsed_real_seconds` is real seconds since the clock started, and it does not scale.

```python
regen_due = Signal()

register_signal(
    regen_due,
    key=lambda date: date.elapsed_real_seconds // 20,
    name="regen_due",
)
```

Every twenty real seconds, whatever speed the game world runs at.

Two things follow from what it is:

- **It cannot go finer than the tick.** The clock looks once a real second, so a cadence shorter than
  that is not expressible.
- **It starts from zero each time the Server process does.** It is counted rather than derived, so
  unlike the date it cannot be recomputed after a reload. Intervals are unaffected; where the
  boundaries fall is not.

Offsetting two cadences keeps them off the same tick:

```python
key=lambda date: date.elapsed_real_seconds // 1200          # meters
key=lambda date: (date.elapsed_real_seconds + 7) // 20      # regeneration, staggered
```

## A cadence on the wall clock

`wall_clock_seconds` is the other: the system clock's reading when the date was built, in seconds
since the epoch. Key on it when a cadence must not restart with the Server process — a period long
enough that a reload would keep pushing it back — or when it has to land at a set time of day.

```python
key=lambda date: int(date.wall_clock_seconds // 86400)                # once a day, at midnight UTC
key=lambda date: int((date.wall_clock_seconds - 300) // 3600)         # five past every hour
```

**Read the time from the date you are handed.** The clock asks your key about the last tick's date and
this tick's in the same instant. A key that reads the system clock itself — `time.time()`,
`timezone.now()` — gets the same answer for both and never fires. `wall_clock_seconds` carries the
reading taken when each date was built, so `key(previous)` gets the last tick's.

## Register it from the same place you start the clock

```python
# server/conf/at_server_startstop.py
def at_server_start():
    register_signal(market_day, key=..., name="market_day")
    start_calendar_clock()
```

**Registrations do not survive a reload.** They are module state in the Server process, which restarts
when Evennia reloads, so they go with it. Registering from `at_server_start()` is what puts them back.

## Holding on to your receiver

This one catches people, and it is Django rather than us.

**`Signal.connect()` keeps receivers weakly.** If nothing else in your code holds a reference to your
handler, Python collects it, the connection disappears, and your handler never runs. No error, no
warning, nothing in a log.

```python
# BROKEN — the lambda is collected the moment this function returns
def at_server_start():
    market_day.connect(lambda sender, **kw: do_something())

# BROKEN — same, a local function has no other reference
def at_server_start():
    def on_market(sender, **kw):
        do_something()
    market_day.connect(on_market)

# FINE — a module-level function is held by its module
def on_market(sender, previous, current, **kwargs):
    do_something()

def at_server_start():
    market_day.connect(on_market)

# ALSO FINE — tell Django to hold it strongly
def at_server_start():
    def on_market(sender, **kw):
        do_something()
    market_day.connect(on_market, weak=False)
```

A bound method survives as long as its instance does, so `market_day.connect(self.on_market)` is fine
while `self` is alive and gone the moment it is not.

If a handler is silently not running, this is the first thing to check.

## The naming rules

**A name already in use is refused.** Not replaced — refused, with a `ValueError` naming the name.

```python
register_signal(market_day, key=..., name="market_day")
register_signal(other, key=..., name="market_day")   # ValueError
```

The reason is that two developers on one game can both reach for `"market_day"`, and if the second
silently replaced the first, the first subsystem would stop firing with nothing to say why. Being told
at registration, you rename or unregister deliberately.

To reuse a name, remove the first registration:

```python
unregister_signal("market_day")
register_signal(other, key=..., name="market_day")
```

**The seven built-in names are reserved.** `hour`, `phase`, `day`, `week`, `month`, `season` and
`year` cannot be registered over, and cannot be unregistered:

```python
register_signal(mine, key=..., name="season")   # ValueError
unregister_signal("season")                     # ValueError
```

A game that could unregister `season` could turn off part of the calendar by accident, and the
built-ins are not yours to remove. Pick another name — `growing_season`, `harvest`, whatever your
world calls it.

## What makes a good key function

**Pure, and cheap.** It is called twice per tick, once per second. Reading two fields off a dataclass
and doing arithmetic is what it is for; a database query is not.

**Returning anything comparable.** An integer is usual, but a tuple, a string or an enum all work —
the clock only asks whether this tick's value differs from last tick's.

```python
key=lambda date: date.day_of_year // 10                  # every tenth day
key=lambda date: (date.year, date.month)                 # start of each month
key=lambda date: date.day_of_year // 20                  # a fortnight
key=lambda date: date.season is Season.WINTER            # entering and leaving winter
key=lambda date: date.elapsed_real_seconds // 20         # every twenty real seconds
```

That last one fires twice a year — once when the value becomes `True` and once when it becomes
`False`. The clock reports *change*, not truth, so if you only want one of those, check `current` in
your receiver.

**Mind the one-based fields.** `day_of_year`, `month`, `day_of_month`, `week` and `day_of_week` all
count from one. So `date.day_of_year // 10` changes on days 10, 20 and 30 rather than 1, 11 and 21 —
which may not be the market you had in mind. Subtract one if you want the other:

```python
key=lambda date: (date.day_of_year - 1) // 10            # days 1, 11, 21 …
```

**If it raises, the signal is skipped.** The failure is written to `calendar.log` with its traceback
and the name you registered under, the clock carries on, and every other signal that tick still fires.
Your broken key function is yours to fix; it cannot take the calendar down with it.
