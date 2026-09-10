# Custom signals

How to have the calendar clock fire a signal of your own, on a condition you define — a market every
tenth day, a festival on a particular date, a fortnight, a tax day. You write a pure function of the
date; the clock does the remembering and the comparing.

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

You never store a previous value and you never write a comparison. Anything expressible as "a value
derived from the date" works.

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
