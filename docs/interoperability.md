# Interoperability

This library against every sibling library in `libraries/`, including itself. A reader deciding
whether two of our libraries can be co-installed gets a definite statement from either side rather
than inferring from silence.

Each section names the relationship — **hard dependency**, **optional integration**, or **no
coupling** — followed either by the constraints that apply or by an explicit clearance stating *why* it
is clear in terms of what this library does. "No known issues" is not a clearance.

**Nothing here has run against a real game yet**, so every statement below is provisional. The
clearances rest on three properties the library holds today: it owns no tables and issues no ORM
writes, it reads Evennia's clock rather than the database, and it searches for and holds no game
objects.

One qualification since the clock landed: the library is no longer entirely passive. It runs a Twisted
`LoopingCall` once a real second and remembers the last date it saw in module state, and it sends
Django signals to whatever a consumer connected. It still writes nothing and reads no game object —
but "does nothing until asked" is no longer true, and a sibling's clearance that rested on it should
be re-read.

**A recurring theme, stated once.** Several siblings are ones a consumer would plausibly *compose*
with this library — spawning that varies by season, an NPC prompt carrying the time of day, hunger
that rises faster in the heat. Composition in a consumer's own code is not a coupling: it needs no
import in either direction and constrains neither library. Where that is the whole of the
relationship, the section says so.

## evennia-ai-memory

**No coupling.** Neither library imports the other. ai-memory owns tables on an alias of its own; this
library owns none and issues no ORM writes, so there is no database interaction to constrain.

## evennia-archive

**No coupling.** Neither library imports the other. Archive clones Evennia's schema so a character can
survive a world rebuild; this library stores nothing, so it has nothing to archive and nothing a
rebuild could take.

Worth knowing rather than a constraint: the calendar's *anchor* does not survive a rebuild either, but
for a different reason — it is Evennia's `ServerConfig` first-start timestamp, which is Evennia's
state and not this library's. See [installing.md](installing.md) § Evennia's time settings.

## evennia-calendar

This library.

## evennia-database-cascade

**No coupling.** This library owns no tables, needs no alias, and ships no router — so the cascade has
nothing to resolve on its behalf. Revisit only if the library ever gains data of its own, which the
current design says it will not.

## evennia-equipment

**No coupling.** Neither library imports the other. Equipment governs what an object wears and carries
and writes to the objects it is handed; this library holds no objects and writes nothing.

## evennia-llm-service

**No coupling.** Neither library imports the other. llm-service dispatches model calls off the reactor
thread; this library does arithmetic on a number and dispatches nothing. A game putting the season
into an NPC prompt is composition in the consumer's code, not a coupling between the two.

## evennia-logging-extension

**Hard dependency.** `log.py` binds `calendar_log` through its `make_logger`, and every line the
library emits goes through that binding to `calendar.log`. The library does not run without it —
`pyproject.toml` declares it. Nothing flows the other way: the extension knows nothing about the
calendar.

## evennia-message-bus

**No coupling.** Neither library imports the other. The bus exists to coordinate state between
processes, and this library's answer to multiple processes is to hold no state at all — every process
derives the same date from the same clock, so there is nothing to publish and nothing to subscribe to.

## evennia-mob-spawner

**No coupling.** Neither library imports the other. Spawning that varies by season or time of day is
an anticipated pattern, and it is the consumer composing two libraries rather than either depending
on the other.

## evennia-portal-multiplex

**No coupling.** Neither library imports the other. Multiplex operates at the Portal/Server transport
layer; this library reads a clock inside the Server process and touches no connection.

## evennia-scaling

**No coupling.** Neither library imports the other. This library derives every value from the clock and
persists nothing, so a character moving between instances carries no calendar state with it and each
instance answers identically without being told.

## evennia-shards

**No coupling.** Neither library imports the other, and the problem shards documents — a global script
holding state that several processes each want to own — is one this library does not have. Every
process derives the same date from the same clock.

The caveat is Evennia's, not ours: on the accumulated-uptime branch two independently-installed
instances measure from different first-start timestamps and will disagree about the date. See
[installing.md](installing.md) § Evennia's time settings.

## evennia-survival

**No coupling.** Neither library imports the other. Survival's meters are stepped by its own clocks and
know nothing about the season; this library reports the season and knows nothing about meters.

The likely real interaction is composition rather than coupling — hunger and thirst rates varying with
weather — and the weather layer that would drive it is a separate library that depends on this one,
not this one. `[TBD — needs discussion: whether that weather library couples to survival directly, or
whether the consumer composes both. It is that library's question, recorded here so it is not lost.]`

## evennia-targeting

**No coupling.** Neither library imports the other. Targeting filters candidate lists from
`caller.search()`; this library searches for nothing and holds no objects — it answers questions about
the clock.

## evennia-world-builder

**No coupling.** Neither library imports the other. World-builder writes rooms and exits from YAML;
this library reads none of them. Room-level content such as terrain or climate is a real question, but
it belongs to the weather library that depends on this one rather than to the calendar.

## evennia-yaml-reader

**No coupling.** Neither library imports the other. yaml-reader depends only on `pyyaml`, has no
Evennia dependency and touches no database, so nothing it does is visible to this library and nothing
this library does is visible to it.

## fcm-telemetry-spawn

**No coupling.** Neither library imports the other. It is an FCM-coupled library and is not offered
for outside consumption, so co-installation is not a case a reader of this document reaches.

## fcm-xrpl

**No coupling.** Neither library imports the other. It is an FCM-coupled library and is not offered
for outside consumption, so co-installation is not a case a reader of this document reaches.
