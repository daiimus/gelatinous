# Time System Specification

## Overview

The Gelatinous Monster universe runs on Terran Standard Time (TST): Earth's
UTC calendar, kept across all human settlements and installations. The colony
clock is `world/gametime.py`. Weather, director broadcasts, the admin readout,
crowd density, NPC shift schedules, the chargen decant stamp, the connection
screen's year and the website's character dates all read the colony clock
from it (#301).

This document gives the clock's rules, then the in-fiction reasons the colony
keeps Earth time.

## Core Time System

### Base Configuration

- **Time Factor**: 1.0 (real-time synchronization).
- **Base Standard**: UTC/Terran Standard Time.
- **Implementation**: `world/gametime.py` is the single source of truth.
  Nothing else may call `time.localtime()`: the container runs UTC and the
  colony does not. (When the weather system read `time.localtime()`, it read
  the container's clock, so "night" ran eight hours away from the colony's own
  night.)

`server/conf/settings.py` sets `TIME_FACTOR = 1.0`. `TIME_GAME_EPOCH` and
`TIME_IGNORE_DOWNTIMES` are not set, so Evennia's defaults apply. Nothing in
the game reads Evennia's gametime for the hour: the colony clock reads the
real wall clock, so server downtime cannot pause or shift it.

### The three decisions

| | | why |
|---|---|---|
| **1:1 with real time** | no acceleration | an hour is an hour; `TIME_FACTOR = 1.0` (Evennia ships 2.0) |
| **Fixed UTC−8, no DST** | colony local time | matches the owner's winter clock; a stranded colony has no reason to shift clocks twice a year, and no authority left to tell it to |
| **Year = real + 1200** | today is **3226 TST** | see below |

**Why 1200 and not a rounder 1000.** The Gregorian calendar repeats on a
**400-year cycle**, so only multiples of 400 preserve the day of the week.
+1000 keeps the month and day but shifts every weekday, which breaks the
moment anything is scheduled (a Friday night at the bar that is not Friday for
the people playing). 1200 keeps month, day **and** weekday, so a real date and
its TST date are the same day in every sense.

It also makes leap years line up: leap rules depend on the year mod 4, 100 and
400, so a 400-aligned offset cannot change whether a year is leap. Feb 29
always has a Feb 29 to land on. `_shift_year` still moves a shifted Feb 29 to
Mar 1 if the target year has none; with a 400-aligned offset that never
happens.

**The offset must stay a multiple of 400.** The constant carries that warning,
and `test_weekday_alignment_depends_on_the_offset` pins the fact.

### Two reckonings

- **TST**: Terran Standard Time, the network's calendar. Institutional: gate
  manifests, salvaged paperwork, anything official.
- **CY**: Colony Year, zero at **3165 TST** (planetfall). Currently **CY 61**.
  What people actually say.

Anything the colony wrote itself tends to be CY; anything from before or
outside is TST. Free texture: use the split.

### Timestamps

`gametime.stamp()` returns **real POSIX seconds**, deliberately unshifted and
unlocalised, so durations stay subtraction and nothing depends on a calendar
offset. Shift on the way out with `format_stamp()`. `wound_timestamp` in
`world/medical/core.py` uses this.

Forensic evidence (blood pools, graffiti) is stamped the same way, and its
age is read with `gametime.since()`, which clamps a negative elapsed time to
zero. A stamp below `LEGACY_RUNTIME_STAMP_MAX` (`typeclasses/objects.py`) is
a leftover from the older `evennia.utils.gametime` clock, which counts server
runtime and rewinds on a database restore (#2414); it reads as age 0.
Harvested organic organs carry `db.harvested_at = stamp()` (#3498); no game
code reads it.

### Reading the hour in-world

Time is legible through **objects**, not a command: the owner ruling behind
#2819, and what makes a working chrono worth carrying. The layer lives in
`world/gametime.py`:

- `render_time_tokens(text, obj=None)` substitutes authored braces in any
  description. The tokens (`TIME_TOKENS` in `world/gametime.py`) are
  `{time}`, `{time12}`, `{date}`, `{datetime}`, `{cy}`, `{hour}`, `{period}`.
  Text holding no token comes back untouched, so it is safe to run over every
  description.
- It has **three** call sites, all of them `get_display_desc`:
  `ObjectParent.get_display_desc` (`typeclasses/objects.py`),
  `Room.get_display_desc` (`typeclasses/rooms.py`) and
  `Exit.get_display_desc` (`typeclasses/exits.py`). Only the first is
  inherited: `Room` composes its own perception-gated string and never
  reaches `super()`, and `Exit` does not inherit `ObjectParent` at all, so
  each is wired separately (#2772). For that reason the tests assert through
  `get_display_desc` rather than through the helper: a helper-level test
  passed while rooms and exits rendered `{time}` literally.
- Two attributes let timepieces disagree with each other, which is the point
  of owning more than one: `db.clock_skew` (minutes fast or slow) and
  `db.clock_stopped` (a POSIX stamp the device then shows forever).
- `{cy}` and `colony_year()` both render from `colony_now()`, so they agree
  even in the eight-hour window where UTC and the colony disagree about the
  year (#2772).

### No clock command

There is no `@time`. Evennia's stock `CmdTime` is removed from
`CharacterCmdSet` (`CharacterCmdSet.at_cmdset_creation`,
`commands/default_cmdsets.py`) by #2819, because it printed `datetime.now()`
(the real-world date, wrong century, wrong timezone) and because `help tokens`
states the design premise that *no command tells you the hour*.

`UnconsciousCmdSet` does not add `CmdTime` either (#2691); that set becomes a
downed non-Builder's entire default cmdset, so carrying it would let a
knocked-out player read the real-world date. `DeathCmdSet` does not have it.
`world/tests/test_no_clock_command.py` builds all three sets, awake,
unconscious and dead, and asserts that none of them carries a time or uptime
command.

### Where the hour is read

`TimeSystem.get_current_hour()` in `world/weather/time_system.py` delegates to
`world.gametime.colony_hour()`. That is the seam weather, the director's
on-air line (`_cue` in `world/director/broadcasts.py`) and the `@weather`
staff readout (`CmdWeather.func` in `commands/CmdAdmin.py`) all read. The
`@weather` readout's "Real time:" line shows colony time, from
`colony_now()`.

To check the clock: `@weather` (staff), an authored `{time}` token on an
object, or `world.gametime.format_now()` from `@py`.

### Overturned intention: Evennia settings and `@time`

The intended implementation was to set `TIME_IGNORE_DOWNTIMES = True`
alongside `TIME_FACTOR = 1.0` in `server/conf/settings.py`, restart, and
verify with `@time`. `TIME_FACTOR = 1.0` is set. The rest was not followed:
the clock is `world/gametime.py`, which reads the real wall clock, so
`TIME_IGNORE_DOWNTIMES` is never set, and there is no `@time` (#2819).

## Justification Framework

From here to *Worldbuilding Notes* is in-fiction justification and
aspiration, not a description of code, despite the "Implementation Details",
"Technical Requirements", "Operational Necessities" and "System Architecture"
headings. Nothing in the game models commodity exchanges, shipping manifests,
FTL arrays or fleet operations. Three statements in that stretch are
code-true: the weather system runs an Earth-like day/night cycle
(`TIME_PERIODS` in `world/weather/time_system.py`), NPC shifts run on the
24-hour colony clock (`current_shift` in `world/souls/posts.py`, over
`SCHEDULES` in `world/souls/engine.py`), and stored timestamps stay UTC POSIX
seconds (`gametime.stamp()`).

The persistence of Earth time in space is driven by three critical practical
necessities:

### 1. Trade Synchronization

**Market Coordination Requirements:**
- All human colonies use Earth time for market coordination
- Commodity exchanges operate on synchronized trading windows
- Supply chain logistics require precise temporal alignment
- Contract deadlines and delivery schedules standardized across parsecs

**Implementation Details:**
- Trade negotiations reference TST timestamps
- Market opening/closing times uniform across colonies
- Shipping manifests use Earth calendar dates
- Economic reports synchronized to Earth fiscal periods

### 2. Communication Protocols

**Subspace Radio Networks:**
- Subspace radio networks require synchronized timestamps
- Message routing depends on temporal packet ordering
- Communication delays calculated using TST references
- Emergency broadcasts coordinated via Earth time

**Technical Requirements:**
- FTL communication arrays calibrated to Earth chronometers
- Signal degradation calculations based on TST transmission times
- Quantum entanglement communicators maintain Earth-sync
- Diplomatic channels operate on Earth time protocols

### 3. Military Command

**Unified Fleet Operations:**
- Unified fleet operations demand universal time standard
- Joint military exercises require synchronized timing
- Strategic coordination across multiple star systems
- Emergency response protocols standardized to TST

**Operational Necessities:**
- Fleet movements planned using Earth time references
- Multi-system battle coordination requires unified chronometry
- Supply line security depends on precise timing windows
- Chain of command operates on Earth time duty schedules

### Cultural Implementation

**Character Interactions**
- NPCs reference Earth time naturally in conversations
- Official documents display TST timestamps
- Work shifts and duty rotations follow Earth hour cycles
- Social events planned using familiar Earth calendar references

**Environmental Integration**
- Ship lighting cycles simulate Earth day/night patterns
- Station atmospherics maintain Earth-normal temporal rhythms
- Hydroponics bays operate on Earth agricultural calendars
- Recreation areas follow Earth-based scheduling conventions

### Technical Considerations

**System Architecture**
- Weather system maintains Earth-like day/night cycles
- NPC schedules operate on 24-hour Earth time periods
- Event scripting uses standard Earth calendar references
- Database timestamps maintain UTC compatibility

**Future Expansion Possibilities**
- Regional time zones for different colonies (still Earth-based)
- Holiday/festival systems based on Earth calendar
- Historical event anniversaries using Earth dates
- Biological rhythm simulation for character health/mood

## Worldbuilding Notes

### Resistance and Adaptation
- Some outer colonies may privately use local time but maintain TST for official purposes
- Characters might grumble about Earth time but recognize its necessity
- Local astronomical phenomena noted but not used for official timekeeping
- Cultural tension between "home time" and "local time" creates RP opportunities

### Practical Complaints
- "Why are we using 24-hour days on a 31-hour planet?"
- "The nav computers would need complete rewrites to change the time standard"
- "Supply ships arriving 7 hours off schedule because of local time confusion"
- "Military operations can't afford temporal coordination failures"

---

*"Time is the universal constant that keeps human civilization from falling apart across the void. We may have lost Earth, but we kept her clock."*
- Admiral Chen Wei, Terran Fleet Command, 2387 TST

## Not decided

- Should the closing epigraph, dated 2387 TST, be re-dated to fit the 3226 TST calendar, or deleted?
