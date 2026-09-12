# Time System Specification

> **Status:** ✅ **IMPLEMENTED 2026-07-30** (#301). Canonical clock is
> `world/gametime.py`; `TIME_FACTOR` is now 1.0. Weather, director broadcasts
> and the admin readout all read the colony hour from it.

## Overview

The Gelatinous Monster universe operates on Terran Standard Time (TST) - Earth's UTC calendar system maintained across all human settlements and installations. This specification outlines the practical, technical, and cultural reasons for this temporal standardization in a spacefaring civilization.

## Core Time System

### Base Configuration
- **Time Factor**: 1.0 (real-time synchronization)
- **Base Standard**: UTC/Terran Standard Time
- **Implementation**: `world/gametime.py` — the single source of truth.
  Nothing else may call `time.localtime()`; the container runs UTC and the
  colony does not.

### The three decisions

| | | why |
|---|---|---|
| **1:1 with real time** | no acceleration | an hour is an hour; `TIME_FACTOR = 1.0` (Evennia ships 2.0) |
| **Fixed UTC−8, no DST** | colony local time | matches the owner's winter clock; a stranded colony has no reason to shift clocks twice a year, and no authority left to tell it to |
| **Year = real + 1200** | today is **3226 TST** | see below |

**Why 1200 and not a rounder 1000.** The Gregorian calendar repeats on a
**400-year cycle**, so only multiples of 400 preserve the day of the week.
+1000 keeps the month and day but shifts every weekday — which breaks the
moment anything is scheduled (a Friday night at the bar that is not Friday for
the people playing). 1200 keeps month, day **and** weekday, so a real date and
its TST date are the same day in every sense.

It also makes leap years line up: leap rules depend on the year mod 4, 100 and
400, so a 400-aligned offset cannot change whether a year is leap. Feb 29
always has a Feb 29 to land on.

**The offset must stay a multiple of 400.** The constant carries that warning,
and `test_weekday_alignment_depends_on_the_offset` pins the fact.

### Two reckonings

- **TST** — Terran Standard Time, the network's calendar. Institutional: gate
  manifests, salvaged paperwork, anything official.
- **CY** — Colony Year, zero at **3165 TST** (planetfall). Currently **CY 61**.
  What people actually say.

Anything the colony wrote itself tends to be CY; anything from before or
outside is TST. Free texture — use the split.

### Timestamps

`gametime.stamp()` returns **real POSIX seconds**, deliberately unshifted and
unlocalised, so durations stay subtraction and nothing depends on a calendar
offset. Shift on the way out with `format_stamp()`. `wound_timestamp` in
`world/medical/core.py` uses this.

### Reading the hour in-world

*(Added to the spec 2026-09-12; shipped earlier and never written down here.)*

Time is legible through **objects**, not a command — the owner ruling behind
#2819, and what makes a working chrono worth carrying. The layer lives in
`world/gametime.py`:

- `render_time_tokens(text, obj=None)` substitutes authored braces in any
  description. The tokens (`TIME_TOKENS`, `world/gametime.py:179`) are
  `{time}`, `{time12}`, `{date}`, `{datetime}`, `{cy}`, `{hour}`, `{period}`.
  Text holding no token comes back untouched, so it is safe to run over every
  description.
- It has **three** call sites, all of them `get_display_desc`: `ObjectParent`
  (`typeclasses/objects.py:47`), `Room` (`typeclasses/rooms.py:98`) and `Exit`
  (`typeclasses/exits.py:532`). Only the first is inherited — `Room` composes
  its own perception-gated string and never reaches `super()`, and `Exit` does
  not inherit `ObjectParent` at all — so an authored `{time}` rendered
  literally on both until each was wired separately (#2772). That is why the
  tests assert through `get_display_desc` rather than through the helper: the
  defect shipped once already behind a helper-level test.
- Two attributes let timepieces disagree with each other, which is the point
  of owning more than one: `db.clock_skew` (minutes fast or slow) and
  `db.clock_stopped` (a POSIX stamp the device then shows forever).
- `{cy}` and `colony_year()` both render from `colony_now()`, so they agree
  even in the eight-hour window where UTC and the colony disagree about the
  year (#2772).

### Justification Framework

> **Scope note 2026-09-12.** From here to *Worldbuilding Notes* is in-fiction
> justification and aspiration, not a description of code — despite the
> "Implementation Details", "Technical Requirements", "Operational
> Necessities" and "System Architecture" headings. Nothing in the game models
> commodity exchanges, shipping manifests, FTL arrays or fleet operations.
> Three statements in that stretch are code-true: the weather system runs an
> Earth-like day/night cycle (`TIME_PERIODS`,
> `world/weather/time_system.py:11`), NPC shifts run on the 24-hour colony
> clock (`current_shift`, `world/souls/posts.py:70`, over `SCHEDULES`,
> `world/souls/engine.py:35`), and stored timestamps stay UTC POSIX seconds
> (`gametime.stamp()`).

The persistence of Earth time in space is driven by three critical practical necessities:

## 1. Trade Synchronization

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

## 2. Communication Protocols

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

## 3. Military Command

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

## Cultural Implementation

### Character Interactions
- NPCs reference Earth time naturally in conversations
- Official documents display TST timestamps
- Work shifts and duty rotations follow Earth hour cycles
- Social events planned using familiar Earth calendar references

### Environmental Integration
- Ship lighting cycles simulate Earth day/night patterns
- Station atmospherics maintain Earth-normal temporal rhythms
- Hydroponics bays operate on Earth agricultural calendars
- Recreation areas follow Earth-based scheduling conventions

## Technical Considerations

### System Architecture
- Weather system maintains Earth-like day/night cycles
- NPC schedules operate on 24-hour Earth time periods
- Event scripting uses standard Earth calendar references
- Database timestamps maintain UTC compatibility

### Future Expansion Possibilities
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

## Implementation Status

### Current Configuration
- **TIME_FACTOR**: 2.0 (Evennia default - game time runs twice as fast as real time)
- **TIME_GAME_EPOCH**: None (uses server start time as epoch)  
- **TIME_IGNORE_DOWNTIMES**: False (game time pauses during server downtime)
- **Location**: These settings belong in `server/conf/settings.py`

### Proposed TST Implementation
```python
# In server/conf/settings.py
TIME_FACTOR = 1.0              # Real-time sync (1:1 ratio with real world)
TIME_GAME_EPOCH = None         # Keep current epoch handling
TIME_IGNORE_DOWNTIMES = True   # Maintain continuity during downtime
```

### Integration Points
- **Infrastructure**: Existing weather/time system in `world/weather/time_system.py` ready for TST
- **Dependencies**: No breaking changes - only adjustment to time flow rate
- **Validation**: Use `@time` command to verify synchronization after implementation

> **Corrected 2026-09-12.** `world/weather/time_system.py` is no longer
> merely "ready": `TimeSystem.get_current_hour()` delegates to
> `world.gametime.colony_hour()` (`world/weather/time_system.py:62-67`),
> and that is the seam weather, the director's on-air line
> (`world/director/broadcasts.py:54-55`) and the `@weather` staff readout
> (`commands/CmdAdmin.py:812-813`) all read. The comment there records the
> bug this closed — the old `time.localtime()` was the CONTAINER's clock,
> so "night" ran eight hours away from the colony's own night.
>
> **`@time` is not the validation path; it is not in the player cmdset.**
> Evennia's stock `CmdTime` was removed from `CharacterCmdSet` by #2819
> (`commands/default_cmdsets.py:299-300`) because it printed
> `datetime.now()` — the real-world date, wrong century, wrong timezone —
> and because `help tokens` states the design premise that *no command
> tells you the hour*. `world/tests/test_no_clock_command.py` pins its
> absence. Verify instead with `@weather` (staff), an authored `{time}`
> token on an object, or `world.gametime.format_now()` from `@py`.
>
> One residue survives, and it is a **code** defect rather than a licence to
> restore the bullet above: `UnconsciousCmdSet` still adds `CmdTime`
> explicitly (`commands/default_cmdsets.py:97`), and that set becomes a downed
> non-Builder's entire default cmdset (`typeclasses/characters.py:871-872`),
> so a knocked-out player can still read the real-world date. Tracked on
> #2691; the guarding test builds only `CharacterCmdSet`, so it does not see
> it.

### Implementation Steps
1. **Edit Configuration**: Add/modify settings in `server/conf/settings.py`:
   ```python
   # Real-time Terran Standard Time synchronization
   TIME_FACTOR = 1.0
   TIME_IGNORE_DOWNTIMES = True
   ```

2. **Server Restart**: Execute `@shutdown` followed by server restart to apply new time factor

3. **Verification**: Use `@time` command to confirm:
   - Game time now matches real time (1:1 ratio)
   - Time continues during server downtime
   - Weather system integration remains functional

4. **Documentation**: Update any time-dependent systems that assumed 2x speed factor

---

*"Time is the universal constant that keeps human civilization from falling apart across the void. We may have lost Earth, but we kept her clock."*
- Admiral Chen Wei, Terran Fleet Command, 2387 TST
