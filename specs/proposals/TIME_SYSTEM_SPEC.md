# Time System Specification

> **Status:** 📋 Proposal — not implemented (tracking #301). The TST real-time clock is the future-clock seam the cadence system already references; current TIME_FACTOR is unchanged.

## Overview

The Gelatinous Monster universe operates on Terran Standard Time (TST) - Earth's UTC calendar system maintained across all human settlements and installations. This specification outlines the practical, technical, and cultural reasons for this temporal standardization in a spacefaring civilization.

## Core Time System

### Base Configuration
- **Time Factor**: 1.0 (real-time synchronization)
- **Base Standard**: UTC/Terran Standard Time
- **Implementation**: Evennia's native gametime system with real-world alignment

### Justification Framework

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
