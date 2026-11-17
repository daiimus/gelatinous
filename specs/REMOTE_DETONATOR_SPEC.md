# Remote Detonator System Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.

## Status: ✅ IMPLEMENTED

*Shipped. `RemoteDetonator` lives in `typeclasses/items.py`; the detonator
commands (`CmdScan`, `CmdDetonate`, `CmdDetonateList`, `CmdClearDetonator`) live
in `commands/CmdExplosives.py`. Spec finalized 2025-01-13.*

## Overview
A handheld remote detonator device that can scan and remotely trigger explosive devices. The detonator maintains a list of up to 20 scanned explosives and can trigger them individually or simultaneously by pulling their pins and starting their normal fuse countdowns. This system integrates with all existing explosive types (sticky grenades, rigged explosives, standard grenades) and respects their unique behaviors.

## Design Philosophy

**Key Principle:** Remote detonation **initiates** the explosive's normal behavior, it doesn't bypass it.

- Remote detonation **pulls the pin** and starts the fuse countdown
- SPDR M9 sticky grenades still get their 10-second countdown to seek/stick
- Rigged explosives still get their 1-second countdown
- Tactical grenades with 5-second fuses give 5 seconds to react
- This maintains explosive type diversity and prevents instant-death scenarios

**Detonation Messages (Detonate All):**

*Note: Each grenade's location receives individual activation message*

```
You: You flip open the red safety cover on your remote detonator and press the large button. Multiple distant beeps echo from various locations!

Operator's Room: {char_name} flips open a red safety cover on their remote detonator and presses a large button. Multiple distant beeps echo from various locations!

Grenade 1 Location: An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]
Grenade 2 Location: A tactical grenade beeps and its light begins flashing! [5 seconds]
Grenade 3 Location (a rigged trap): An SPDR M9 grenade beeps and its light begins flashing! [1 seconds]
```

*The `[N seconds]` tag is shown only to viewers with Builder permission (#3350; see the note under Sticky Grenades); players see the line without it.*

**Multi-Detonation Messaging:**
- Operator sees single "multiple beeps" message
- Operator's room sees button press + "multiple beeps"
- Each grenade's location sees individual activation message
- Staggered countdowns begin based on each explosive's fuse_time

*Note: Cross-room messaging sends different messages to operator's location and grenade's location*

```
You: You flip open the red safety cover on your remote detonator and press the large button. A distant beep echoes!

Operator's Room: {char_name} flips open a red safety cover on their remote detonator and presses a large button.

Grenade's Location (if different room): An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]

Same Room (if operator and grenade in same location): 
  {char_name} flips open a red safety cover on their remote detonator and presses a large button.
  An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]
```

*The `[N seconds]` tag is shown only to viewers with Builder permission (#3350; see the note under Sticky Grenades); players see the line without it.*

**Cross-Room Messaging Logic:**
- Operator always sees button press action
- Operator's room sees: "flips open... presses button"
- Grenade's room (if different) sees: "grenade beeps and light flashes"
- If same room: Both messages sent to room
- Observers see different perspectives based on location

**Tactical Gameplay:**
- Plan complex multi-stage detonations with timed delays
- Create distractions with long-fuse grenades while rigged traps explode quickly
- Override your own rigged traps remotely before they're triggered by victims (a trap answers only to its rigger's detonator; anyone else must defuse it -- owner ruling 2026-09-18, #3351)
- Mass detonation creates chaos with staggered explosion timing

---

## 1. Remote Detonator Item

### Item Properties

```python
# New item typeclass: RemoteDetonator
class RemoteDetonator(Item):
    """
    Handheld remote detonator for explosive devices.
    Can scan and remotely trigger up to 20 explosives.
    """
    
    def at_object_creation(self):
        """Set up detonator attributes"""
        self.db.scanned_explosives = []  # List of explosive dbrefs (max 20)
        self.db.max_capacity = 20        # Maximum scanned explosives
        self.db.device_type = "remote_detonator"
```

### Prototype

> *2026-10-27 (#3779): key renamed `"VECTOR UEM3 detonator"`, desc to match; no key carries a dash followed by digits, because Evennia's `name-N` ordinal form reads the first `-N` it meets and a player could not narrow a twin. Aliases unchanged. The 2026-09-12 note below records the key as it shipped then.*
>
> *2026-09-12: the shipped prototype is BRANDED per the everything-branded mandate (`REMOTE_DETONATOR` in `world/prototypes.py`): key `"VECTOR UEM-3 detonator"`, aliases `["vector", "uem3", "uem-3", "detonator", "remote", "trigger"]`, a VECTOR UEM-3 desc, and tags `("item", "general")` / `("tool", "category")`. The typeclass path and the three `attrs` below still match exactly; the key, aliases and desc below are the pre-brand draft.*

```python
REMOTE_DETONATOR = {
    "key": "remote detonator",
    "aliases": ["detonator", "remote", "trigger"],
    "typeclass": "typeclasses.items.RemoteDetonator",
    "desc": "A compact military-grade remote detonator with a digital display showing scanned explosive devices. The device can store up to 20 explosive signatures and trigger them remotely with the press of a button. A red safety cover protects the main detonation switch.",
    "attrs": [
        ("scanned_explosives", []),  # List of explosive dbrefs
        ("max_capacity", 20),        # Maximum capacity
        ("device_type", "remote_detonator"),
    ]
}
```

---

## 2. Explosive Tracking

### Bidirectional Relationship

> *2026-09-12: both sides store the integer `.id`, never a `#dbref` string — `RemoteDetonator.add_explosive` (`typeclasses/items.py`) runs `self.db.scanned_explosives.append(explosive.id)` and `explosive.db.scanned_by_detonator = self.id`. Lookups rebuild the string (`search_object(f"#{explosive_dbref}")` in the detonator commands, `commands/CmdExplosives.py`), and the player-facing signature is `e-<id>`. Read `dbref` below as "id" throughout, including in the `scan` pseudo-code at §3.*

Each explosive can only be scanned by ONE detonator at a time, but detonators can scan multiple explosives:

```python
# On explosive
explosive.db.scanned_by_detonator = detonator_dbref or None

# On detonator  
detonator.db.scanned_explosives = [explosive_dbref1, explosive_dbref2, ...]
```

### Scanning Rules

1. **One Detonator Per Explosive:**
   - An explosive can only be linked to one detonator at a time
   - Scanning with a new detonator **overrides** the previous link
   - Previous detonator automatically removes explosive from its list

2. **Capacity Limit:**
   - Detonators can scan up to 20 explosives
   - Attempting to scan beyond capacity shows error message
   - Must clear explosives to free up slots

3. **No Range Limit:**
   - Once scanned, detonation works from any distance
   - Works across rooms, floors, locations
   - Persistent link until explosive detonates or is cleared

4. **Automatic Cleanup:**
   - Detonated explosives auto-remove from detonator list
   - Destroyed explosives auto-remove from detonator list
   - The detonator prunes dead entries on `scan`, `detonate list` and `detonate all`; `detonate e-<id>` drops a dead entry when it hits it
   - A dud is not destroyed: its pin is reset and it stays in the detonator's memory, so it can be detonated again (#2539)

---

## 3. Command System

### Scan Command

> *2026-09-12 — message drift: the shipped strings are "You scan {key} into {detonator}'s memory." plus separate `  Signature: e-{id}` and `  Capacity: n/20` lines, with the room getting "{actor} points a device at {key}, which emits a soft beep." (`CmdScan.func` in `commands/CmdExplosives.py`). The capacity refusal is "Detonator at maximum capacity (20 explosives)." (`RemoteDetonator.add_explosive` in `typeclasses/items.py`), not the `(20/20) … Clear some explosives first.` form below. The already-scanned and not-an-explosive refusals do match.*

**Syntax:** `scan <explosive> with <detonator>`

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Validate both objects exist: the explosive in the caller's inventory OR the caller's room (#3351, 2026-09-18; before that `caller.search(name, location=caller)` reached inventory only, so a rigged grenade -- moved onto the exit by `rig` -- could be scanned only before it was set); the detonator in the caller's inventory. A rigged explosive (`db.rigged_to_exit` set) is refused unless `db.rigged_by` is the caller: "X is someone else's trap. Defuse it if you want it gone."
2. Confirm explosive has is_explosive attribute
3. Check detonator capacity (< 20)
4. Check if explosive already scanned by different detonator:
   - If yes: Override old detonator link, add to new detonator
   - If no: Add to detonator
5. Set bidirectional references:
   explosive.db.scanned_by_detonator = detonator.dbref
   detonator.db.scanned_explosives.append(explosive.dbref)
6. Send success messages
```

**Messages:**
```
You: You scan the SPDR M9 grenade with your remote detonator. A soft beep confirms the explosive signature has been registered as e-1234.

Room: {char_name} scans a SPDR M9 grenade with their remote detonator, which emits a soft confirmation beep.
```

**Edge Cases:**
- Scanning already-scanned explosive: "The SPDR M9 grenade is already scanned by this detonator."
- Capacity full: "Your remote detonator is at maximum capacity (20/20). Clear some explosives first."
- Already scanned by different detonator: Override old link and show message
- Non-explosive item: "The sword is not an explosive device."

---

### Detonate Single Command

> *2026-09-12 — message drift: there is no blue-LED text anywhere in the code. `CmdDetonate.detonate_single` in `commands/CmdExplosives.py` sends the red-safety-cover pair this spec itself sketches at the top of the file (§Cross-Room Messaging) — "You flip open the red safety cover … A distant beep echoes!" plus the arming beep from `announce_arming` (countdown tag for builders only). The already-active refusal is "{key} is already detonating!", not "e-1234 is already armed and counting down!". The countdown is `armed_fuse(explosive)`: the charge's own `db.fuse_time` (10 for an SPDR M9, 8 if none is set), or `TRAP_FUSE_TIME` (1) for a rigged trap.*

**Syntax:** `detonate e-<dbref> with <detonator>`

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Validate dbref is in detonator's scanned list
2. Get explosive object from dbref
3. Validate explosive still exists and is valid
4. Check if pin already pulled:
   - If countdown already active: "<charge name> is already detonating!"
   - If not: Pull pin and start countdown
5. Trigger explosive's normal pin-pull behavior:
   explosive.db.pin_pulled = True
   explosive.db.hidden = False  # an armed charge cannot stay hidden (#3767)
   explosive.ndb.countdown_remaining = armed_fuse(explosive)
   start_grenade_ticker(explosive)
6. Send detonation messages
7. Keep explosive in scanned list (will auto-remove on explosion)
```

**Messages:**
```
You: You press the button for e-1234 on your remote detonator. The SPDR M9 grenade's blue LED begins pulsing rapidly! (6 seconds)

Room: {char_name} presses a button on their remote detonator. A SPDR M9 grenade's blue LED begins pulsing rapidly!

Observer at grenade location (if different room): A SPDR M9 grenade suddenly activates, its blue LED pulsing rapidly!
```

**Edge Cases:**
- Invalid dbref: "e-1234 is not in this detonator's memory."
- Explosive doesn't exist: "e-1234 no longer exists. [Auto-removed from list]"
- Already detonating: "e-1234 is already armed and counting down!"

---

### Detonate All Command

> *2026-09-12 — the per-signature report below was never built.* `CmdDetonate.detonate_all` (`commands/CmdExplosives.py`) sends the safety-cover line plus "Detonated {n} explosive(s)." and nothing else: `already_active_count` goes only to the splattercast debug channel, and invalid entries are silently skipped — never counted, never listed, never reported as `[INVALID - REMOVED]`. The "5 armed, 1 already active, 2 invalid" summary and the ARMED/ALREADY ACTIVE/INVALID display block are UNBUILT, not shipped.
>
> `detonate all` and `detonate e-<id>` both take a charge's fuse from `armed_fuse(explosive)`: a rigged trap gets `TRAP_FUSE_TIME` (1 second) through either command, and every other charge gets its own `fuse_time`, or 8 if it has none (#2547, #3348).

**Syntax:** `detonate all with <detonator>`

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Validate detonator has scanned explosives
2. Iterate through all scanned explosives:
   - Validate explosive exists
   - Check if already detonating
   - Pull pin and start countdown for each valid explosive
3. Track success/failure counts
4. Send summary message
5. Explosives will auto-remove from list as they explode
```

**Messages:**
```
You: You flip open the red safety cover and press the DETONATE ALL button. Your remote detonator confirms: 5 explosives armed, 1 already active, 2 invalid.

Your remote detonator displays:
  e-1234: ARMED (10s) - SPDR M9 grenade
  e-1235: ARMED (8s) - frag grenade  
  e-1236: ARMED (5s) - tactical grenade
  e-1237: ARMED (10s) - demo charge
  e-1238: ARMED (1s) - rigged SPDR M9 grenade
  e-1239: [ALREADY ACTIVE]
  e-1240: [INVALID - REMOVED]
  e-1241: [INVALID - REMOVED]

Room: {char_name} flips open a red safety cover on their remote detonator and presses a large button. Multiple distant beeps echo from various locations!
```

**Edge Cases:**
- Empty list: "<detonator> has no scanned explosives." (after pruning dead entries: "<detonator> has no valid explosives to detonate.")
- All already active: "All scanned explosives are already detonating."
- Mixed results: Show detailed breakdown of successes/failures

---

### List Command

> *2026-09-12 — shipped shape: an `EvTable(border="cells", width=78)` framed by `=` rules (`CmdDetonateList.func` in `commands/CmdExplosives.py`), not the drawn box below. Same five columns, same `Capacity: n/20` line, same four-state legend, different glyphs. The TRAP row shows the fuse the trap will actually get, `1s (trap)`, from the same `armed_fuse` the two detonate commands use (#3349). There is no "Dropped at {room}" string — a charge on the ground shows the bare room key. An all-invalid list falls through to "{key} has no scanned explosives.", not "All previously scanned explosives are invalid. List cleared."*

**Syntax:** `detonate list with <detonator>` or `detonator list` (if wielded)

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Validate detonator has scanned explosives
2. Iterate through scanned list:
   - Get explosive object
   - Check if exists and valid
   - Get explosive state (pin_pulled, countdown_remaining, location)
   - Auto-remove invalid explosives
3. Display a table with explosive information
```

**Display Format:**
```
╔════════════════════════════════════════════════════════════════════╗
║                   REMOTE DETONATOR - SCANNED DEVICES                ║
║                              Capacity: 8/20                         ║
╠═══════╦══════════════════════╦════════╦═══════════╦════════════════╣
║ ID    ║ Device               ║ Status ║ Fuse      ║ Location       ║
╠═══════╬══════════════════════╬════════╬═══════════╬════════════════╣
║ e-123 ║ SPDR M9 grenade      ║ READY  ║ 10s       ║ Armory         ║
║ e-124 ║ frag grenade         ║ ACTIVE ║ 3s left!  ║ Hallway        ║
║ e-125 ║ tactical grenade     ║ READY  ║ 5s        ║ Your inventory ║
║ e-126 ║ demo charge          ║ READY  ║ 10s       ║ Storage room   ║
║ e-127 ║ rigged SPDR M9       ║ READY  ║ 1s (trap) ║ Doorway        ║
║ e-128 ║ SPDR M9 grenade      ║ STUCK  ║ 4s left!  ║ On Marcia      ║
║ e-129 ║ smoke grenade        ║ READY  ║ 4s        ║ Your inventory ║
║ e-130 ║ flashbang            ║ READY  ║ 6s        ║ Your inventory ║
╚═══════╩══════════════════════╩════════╩═══════════╩════════════════╝

Status Legend:
  READY  - Armed and ready for remote detonation
  ACTIVE - Currently counting down (pin already pulled)
  STUCK  - Sticky grenade adhered to target
  TRAP   - Rigged explosive waiting for trigger
```

**State Information:**
- **READY**: Pin not pulled, ready for remote detonation
- **ACTIVE**: Pin pulled, countdown in progress
- **STUCK**: Sticky grenade adhered to armor/character
- **TRAP**: Rigged explosive set up as trap

**Location Information:**
- Room name if in a room
- "Your inventory" if carried by user
- "On {character_name}" if stuck to character
- "Dropped at {room}" if on ground

**Edge Cases:**
- Empty list: "<detonator> has no scanned explosives."
- All invalid: dead entries are pruned and the same "<detonator> has no scanned explosives." is shown

---

### Clear Single Command

**Syntax:** `clear e-<dbref> from <detonator>`

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Validate dbref is in detonator's scanned list
2. Get explosive object (if exists)
3. Remove bidirectional references:
   detonator.db.scanned_explosives.remove(explosive_dbref)
   explosive.db.scanned_by_detonator = None (if explosive exists)
4. Send success message
```

**Messages:**
```
You: You clear e-1234 (SPDR M9 grenade) from your remote detonator's memory.

Room: {char_name} presses several buttons on their remote detonator.
```

**Edge Cases:**
- Invalid dbref: "e-1234 is not in this detonator's memory."
- Explosive doesn't exist: removed like any other entry; the confirmation shows the signature in place of the name: "You clear e-1234 (e-1234) from <detonator>'s memory."

---

### Clear All Command

**Syntax:** `clear all from <detonator>` or `detonator clear`

**Requirements:** Detonator must be wielded/held (not just in inventory)

**Behavior:**
```python
1. Iterate through all scanned explosives
2. For each valid explosive:
   explosive.db.scanned_by_detonator = None
3. Clear detonator's list:
   detonator.db.scanned_explosives = []
4. Send success message with count
```

**Messages:**
```
You: You clear all 8 explosive signatures from your remote detonator's memory.

Room: {char_name} holds down a button on their remote detonator, which emits a series of beeps before going silent.
```

**Edge Cases:**
- Empty list: "<detonator> has no scanned explosives to clear."

---

## 4. Integration with Existing Explosion Logic

### Pin Pull Mechanism

Remote detonation uses the **same pin-pull logic** as manual grenade usage:

```python
def remote_detonate_explosive(explosive):
    """
    Remotely detonate an explosive by pulling its pin.
    Starts normal fuse countdown - does NOT bypass explosive behavior.
    
    NOTE (2026-09-15, #3386): the pin flag is the raw attribute `db.pin_pulled`; the `DB_PIN_PULLED` constant this section once cited was never read by any code and was deleted. Explosives are a backbone of the mining experience, so the attribute contract lives HERE: `pin_pulled`, `blast_damage`, `blast_radius`, `dud_chance`, `chain_trigger`, `requires_pin`, `detonation_deadline`.
    (was:) DB_PIN_PULLED constant imported at top of CmdThrow.py via:
          from world.combat.constants import *
    """
    
    # Check if already detonating (use constant from world.combat.constants)
    if explosive.db.pin_pulled:
        return False, "already_active"
    
    # Pull the pin (same as manual pull) - use constant
    explosive.db.pin_pulled = True
    
    # Get the fuse: TRAP_FUSE_TIME for a rigged trap, else the charge's own
    fuse_time = armed_fuse(explosive)
    
    # Set countdown
    explosive.ndb.countdown_remaining = fuse_time
    
    # Start countdown using existing system
    start_grenade_ticker(explosive)
    
    return True, fuse_time
```

### Explosive Type Behaviors

**Standard Grenades (frag, tactical, demo):**
```python
# Remote detonation → Pin pulled → Countdown starts → Explosion at location
# Uses explode_standalone_grenade in commands/explosion_utils.py
```

**SPDR M9 Sticky Grenades:**
```python
# Remote detonation → Pin pulled → 10s countdown
# During countdown: If thrown, still seeks magnetic targets
# If stuck: Explodes stuck to armor (existing behavior)
# If on ground: Explodes at ground location (existing behavior)
```

**Rigged Explosives:**
```python
# Remote detonation → Pin pulled → 1s countdown → Explosion
# Bypasses trap trigger logic (remote override)
# Explodes through explode_standalone_grenade like any remotely armed charge, not the tripwire's own explosion
# Respects proximity system for damage calculation
```

**Thrown Grenades (in flight or countdown):**
```python
# If grenade is thrown and countdown already started:
# Remote detonation attempt → "already active" message
# Cannot re-trigger already-counting explosives
```

### Explosion Function Integration

The detonator calls existing explosion paths:

```python
# Standard explosive explosion
# Located in: commands/explosion_utils.py
def explode_standalone_grenade(grenade):
    """Existing explosion logic"""
    # Get location (room or armor hierarchy)
    # Get proximity list
    # Calculate damage
    # Apply damage to all in proximity
    # Check human shield mechanics
    # Destroy grenade object
    # Send explosion messages

# Remote detonation simply triggers this:
CmdDetonate → start_grenade_ticker(explosive) (commands/explosion_utils.py) → explode_standalone_grenade(explosive), which deletes the grenade; Item.at_object_delete then removes it from its detonator's list
```

---

## 5. Edge Cases and Special Scenarios

### Sticky Grenades

> **The arming beep reaches the bearer and their room (#3350, 2026-09-18; owner: tell the room, never re-tell the person it is on, and show the bracketed countdown to builders only).** A charge's `location` is often not a room: stuck, it is the armor item; carried or held, the character. Both remote doors used to broadcast the arming line to that location, so the armor's contents or the holder's other pockets were told and the wearer, the holder and their room heard nothing until the blast. `commands/CmdExplosives.arming_audience(explosive)` walks up to the room and returns `(room, bearer, armor)`; `announce_arming(caller, explosive, fuse_time)` is the one door for `detonate e-<id>` and `detonate all`, called after the operator's own lines and BEFORE `start_grenade_ticker` (the sticky ticker's first countdown warning fires synchronously, so the beep must precede the count). The bearer gets one personal line ("The X stuck to your <armor> beeps and its light begins flashing!" / "The X in your hand beeps..." / "The X in your pocket beeps..."); their room hears it on them through the identity door with the bearer excluded ("The X stuck to {target_char}'s <armor> beeps..." / "The X in {target_char}'s hand beeps..." / "Something in {target_char}'s pocket beeps!"); a loose charge is announced to its room as before. `fuse_tag(viewer, fuse_time)` appends ` [N seconds]` only for viewers with Builder permission; `tell_room_arming` renders a room line with and without it. The sticky ticker's per-second `*** N SECONDS ***` warnings were already reaching a wearer and now follow the beep.

**Scenario 1: Stuck to Armor**
```python
# SPDR M9 is magnetically stuck to character's plate mail
# Remote detonation pulls pin → 10s countdown
# Grenade explodes while stuck to armor (existing behavior)
# Damage applied to wearer and proximity
```

**Scenario 2: In Inventory**
```python
# SPDR M9 in character's inventory
# Remote detonation pulls pin → 10s countdown
# Character holding live grenade (existing behavior)
# Can drop before explosion
```

**Scenario 3: On Ground**
```python
# SPDR M9 on ground in room
# Remote detonation pulls pin → 10s countdown
# Explodes at ground location
# Damages everyone in proximity (existing logic)
```

### Already-Active Explosives

**Scenario 1: Pin Already Pulled**
```python
# Someone manually pulls pin on grenade → countdown starts
# Remote detonation attempt → check `db.pin_pulled`
# Message: "<charge name> is already detonating!" (single); `detonate all` skips it silently unless nothing else was armed
# No re-trigger, countdown continues normally
```

**Scenario 2: Multiple Detonators**
```python
# Detonator A detonates grenade → countdown starts
# Detonator B attempts detonation → check `db.pin_pulled`
# Message: "<charge name> is already detonating!" (single); `detonate all` skips it silently unless nothing else was armed
# Prevents exploit of resetting/extending countdown
```

### Rigged Explosives

> **One eraser, three doors (#3388, 2026-09-18).** A trap's registration (`exit.db.rigged_grenade` on the rigged exit and on its return exit) is cleared by `commands/explosion_utils.clear_exit_rigging(grenade)`, called by the tripwire door, by `defuse`, and by both remote doors (`detonate e-<id>` and `detonate all`) right after the fuse starts. Before this, `defuse` cleared both exits, the tripwire's inline copy cleared only the exit that was walked (its return-exit match ran post-move against the wrong room, so the other side of the doorway stayed armed and a second walker crossing during the fuse second re-fired the same live grenade), and the remote doors cleared nothing. Played 2026-09-18 on the remote door: after the blast the exits' stored records still named the deleted grenade (`('__packed_dbobj__', ..., 22506)`) while every read resolved them to `None`, so the doorway could be walked and re-rigged. The grenade's own `rigged_to_exit` stays set until `defuse` clears it: `defuse`, `scan`'s ownership guard and `detonate list` read it.
>
> **One restore door, and the door itself (#3560, 2026-09-21).** Taking a trap OFF -- both exits' records, the grenade's `rigged_to_exit`/`rigged_by`, and the room-render state `rig` set (`integrate`, `integration_desc`, `integration_priority`, restored from `original_*`) -- is `commands/explosion_utils.unrig_grenade(grenade)`. `defuse` adds its lines around it, and `Exit.at_object_delete` calls it when the door the wire was strung across is destroyed, so a trap never outlives its door. Before this, `defuse` inlined the restore and gated it on `rigged_to_exit` being live, so a grenade whose exit had been deleted kept rendering a trip wire forever and `defuse` refused it as "not armed" (the crane car rebuilt its exits on every ride; it now keeps them, see `CraneContainer`).
>
> **Naming the charge (#3783).** `rig <name> to <exit>` and `defuse <name>` resolve the name with the one core matcher, `Character.search(name, candidates=pool)`: exact key or alias first, then word-start partials, ordinals (`2nd grenade`) and the presence gate. `rig`'s pool is what is in your hands; a held non-explosive or pin-pulled charge keeps its own refusal, and a name nothing in hand matches falls back to "You must be wielding" (carried) or "You don't have" (nowhere). `defuse` tries the explosives already in reach first (live or not, so a dud in reach answers "not armed"), then the live ones in the room or your inventory (pin pulled or rigged); each pool is filtered before matching, so an ordinal counts only those. Several matches still refuse with "Be more specific", now answerable with an ordinal or an alias. Before this both commands matched the typed text as a substring of the key: a branded charge's alias (`dx-15` for "HDG DX15 demolition charge") never worked, and a fragment from inside a word (`nade`) did.

**Scenario 1: Trap Override**
```python
# Rigged explosive set up as trap in doorway
# Remote detonation pulls pin → 1s countdown (TRAP_FUSE_TIME, via armed_fuse)
# Explodes BEFORE anyone triggers trap
# Useful for clearing your own traps safely
# (was: fuse_time already 1 from rigging; never true, see #2547)
```

**Scenario 2: Trap + Remote**
```python
# Rigged explosive scanned by detonator
# Someone triggers trap → `db.pin_pulled` set, 1s countdown starts
# Remote detonation attempt → check `db.pin_pulled`
# Message: "<charge name> is already detonating!" (single); `detonate all` skips it silently unless nothing else was armed
# Cannot re-trigger during countdown
```

### Multiple Detonators

**Scenario: Override Behavior**
```python
# Detonator A scans grenade → grenade.db.scanned_by_detonator = A
# Detonator B scans same grenade:
#   - Remove from Detonator A's list
#   - Add to Detonator B's list  
#   - grenade.db.scanned_by_detonator = B
# Detonator A can no longer detonate it
```

### Automatic Cleanup

**Scenario: Explosive Detonated**
```python
# Explosive explodes (any method: manual, remote, trap)
# On explosion completion:
#   - explosive.db.scanned_by_detonator → get detonator
#   - detonator.db.scanned_explosives.remove(explosive_dbref)
#   - Cleanup happens automatically in explosion function
```

**Scenario: Explosive Destroyed**
```python
# Explosive destroyed (taken from corpse, destroyed object, etc)
# On object destruction:
#   - Check explosive.db.scanned_by_detonator
#   - Remove from detonator's list
#   - Or validate on next list command
```

**Scenario: Detonator Destroyed**
```python
# Detonator destroyed/taken
# Iterate through detonator.db.scanned_explosives
# Clear explosive.db.scanned_by_detonator for each
# Explosives no longer remotely detonable
```

---

## 6. Implementation Checklist

### New Code Required

**1. RemoteDetonator Typeclass** (`typeclasses/items.py`)
```python
class RemoteDetonator(Item):
    """Remote detonator for explosive devices"""
    def at_object_creation(self):
        # Initialize attributes
    
    def validate_scanned_list(self):
        # Clean up invalid explosives
    
    def add_explosive(self, explosive):
        # Add to scanned list with validation
    
    def remove_explosive(self, explosive):
        # Remove from scanned list
    
    def get_scanned_count(self):
        # Validate the list, then count it
    
    def at_object_delete(self):
        """Called when detonator is destroyed"""
        # Clear scanned_by_detonator on all linked explosives
```

**2. Explosive Cleanup Hook** (`typeclasses/items.py`)
```python
# Add to all explosive item classes (or base explosive class)
def at_object_delete(self):
    """Called when explosive is destroyed"""
    # Remove from detonator's scanned list if linked
    if hasattr(self.db, 'scanned_by_detonator') and self.db.scanned_by_detonator:
        detonator = search_object(f"#{self.db.scanned_by_detonator}")
        if detonator and hasattr(detonator[0].db, 'scanned_explosives'):
            try:
                detonator[0].db.scanned_explosives.remove(self.id)
            except ValueError:
                pass  # Already removed
```

**3. New Commands** (`commands/CmdExplosives.py`)
```python
# NOTE: All detonator commands live in CmdExplosives.py (the explosives command file)
# NOTE (2026-09-15): attributes are addressed by raw name (`db.pin_pulled`); no DB_* constants exist (#3386). (was:) Constants like DB_PIN_PULLED are already imported at top of file via:
#       from world.combat.constants import *

class CmdScan(Command):
    """Scan explosive with detonator"""
    # Must be wielding/holding detonator to use
    
class CmdDetonate(Command):
    """Detonate single or all explosives"""
    # Must be wielding/holding detonator to use
    # Already-active explosives show "already detonating" message (no re-trigger)
    
class CmdDetonateList(Command):
    """List scanned explosives"""
    # Must be wielding/holding detonator to use
    
class CmdClearDetonator(Command):
    """Clear single or all explosives from detonator"""
    # Must be wielding/holding detonator to use

# No separate detonator cmdset: the four commands are added to the
# character cmdset (CharacterCmdSet in commands/default_cmdsets.py)
```

**4. Integration Hooks** (`commands/CmdThrow.py` - modify existing functions; the game does not do it this way: detonator cleanup runs in `Item.at_object_delete` in `typeclasses/items.py`, and the explosion is `explode_standalone_grenade` in `commands/explosion_utils.py`)
```python
# In existing pull_pin() function:
def pull_pin(self, grenade):
    # ... existing pin pull logic ...
    
    # NEW: Auto-cleanup detonator reference after explosion completes
    # This happens in explosion completion, not in pull_pin
    
# In existing explode_grenade() function or completion:
def explode_grenade(self, grenade):
    # ... existing explosion logic ...
    
    # NEW: Auto-cleanup detonator reference
    if hasattr(grenade.db, 'scanned_by_detonator'):
        detonator_dbref = grenade.db.scanned_by_detonator
        if detonator_dbref:
            from evennia.utils.search import search_object
            detonator = search_object(f"#{detonator_dbref}")
            if detonator and hasattr(detonator[0].db, 'scanned_explosives'):
                try:
                    detonator[0].db.scanned_explosives.remove(grenade.id)
                except ValueError:
                    pass  # Already removed
    
    # ... rest of explosion logic ...

# In existing explode_rigged_grenade() function:
def explode_rigged_grenade(grenade):
    # ... existing rigged explosion logic ...
    
    # NEW: Same cleanup as above
    # (was: rigged explosives already use 1-second fuse_time from rigging; never true, see #2547)
    # Remote detonation reads TRAP_FUSE_TIME through armed_fuse()
```

**5. Utility Functions** (`commands/CmdThrow.py` - add helper functions; not made as helpers: list validation is `RemoteDetonator.validate_scanned_list` in `typeclasses/items.py`, and status and location strings are built inline in `CmdDetonateList.func`)
```python
def validate_detonator_list(detonator):
    """Clean up invalid explosives from detonator list"""

def format_detonator_display(detonator):
    """Generate boxtable display for scanned explosives"""
    
def get_explosive_state_string(explosive):
    """Return state string (READY/ACTIVE/STUCK/TRAP)"""
    
def get_explosive_location_string(explosive):
    """Return location string for display"""
```

### Modified Code

**1. Explosive Items** (`world/prototypes.py` or existing explosives)
```python
# Add to all explosive prototypes:
"attrs": [
    # ... existing attrs ...
    ("scanned_by_detonator", None),  # Detonator dbref or None
]
```

**2. Explosion Functions** (`commands/explosion_utils.py`)
```python
# Add cleanup hook to explosion completion
# Ensure sticky grenades, rigged explosives, standard explosives all clean up
# Happens automatically via at_object_delete() hook on explosive objects
```

### Testing Priorities

1. ✅ Scan explosive with detonator
2. ✅ Display detonator list as a table
3. ✅ Remote detonate single explosive → countdown starts
4. ✅ Remote detonate all → multiple countdowns
5. ✅ SPDR M9 remote detonation → still seeks/sticks during countdown
6. ✅ Rigged explosive remote detonation → 1s countdown
7. ✅ Explosive override (scan with second detonator)
8. ✅ Auto-cleanup after explosion
9. ✅ Clear single explosive from detonator
10. ✅ Clear all explosives from detonator

---

## 7. Implementation Decisions

### Decision Log

These decisions were made during the specification phase to resolve implementation questions:

**1. Already-Active Grenade Behavior**
- **Decision:** Show "already detonating" message, don't re-trigger
- **Rationale:** Prevents exploits and maintains predictability
- **Implementation:** Check `db.pin_pulled` before remote detonation (raw attribute; the constant was deleted in #3386)

**2. Code Organization**
- **Decision:** Detonator commands live in `commands/CmdExplosives.py` (the dedicated explosives command file)
- **Rationale:** Explosives commands are grouped together in their own module
- **Implementation:** CmdScan, CmdDetonate, CmdDetonateList, CmdClearDetonator all in `commands/CmdExplosives.py`

**3. Rigged Explosive Countdown Timing**
- **Decision:** A rigged trap gets `TRAP_FUSE_TIME` (1 second) however it is set off
- **Rationale:** (was: "Rigging process already sets `grenade.db.fuse_time = 1`, no special handling needed"; nothing ever wrote that, see #2547)
- **Implementation:** `armed_fuse(explosive)` in `commands/CmdExplosives.py` returns `TRAP_FUSE_TIME` when `db.rigged_to_exit` is set; rigging does not touch the grenade's own `fuse_time`. The detonate commands set `db.pin_pulled`, set the countdown from `armed_fuse()`, announce the arming beep, and start the same `start_grenade_ticker` that `pull` uses

**4. Cleanup Integration Point**
- **Decision:** Use the `at_object_delete()` hook (`Item.at_object_delete` for explosives, `RemoteDetonator.at_object_delete` for the detonator). `at_delete` is not an Evennia hook; until #2590 the cleanup was written under that name and never ran
- **Rationale:** Catches all deletion scenarios cleanly (explosion, pickup, destroy, etc.)
- **Implementation:** `Item.at_object_delete` in `typeclasses/items.py` removes a deleted explosive from its detonator's list

**5. Cross-Room Messaging**
- **Decision:** Both operator location and grenade location get messages
- **Rationale:** "Operator just presses a button and that's what people see. Locations see the whole shebang."
- **Implementation:**
  - Operator's room: "{char_name} flips open a red safety cover and presses a button."
  - Grenade's room: "An SPDR M9 grenade beeps and its light begins flashing!"

**6. Wielding Requirement**
- **Decision:** Detonator must be wielded/held to use (not just in inventory)
- **Rationale:** Requires active use, prevents passive inventory operation
- **Implementation:** Check for wielded weapon or held item before allowing detonator commands

**7. Pin State Handling**
- **Decision:** A charge whose pin is already pulled is not re-armed (see Decisions 1 and 8)
- **Rationale:** (was: "Pin state doesn't matter for remote detonation"; this contradicted Decisions 1 and 8)
- **Implementation:** `detonate e-<id>` refuses with "<charge name> is already detonating!" and `detonate all` skips the charge; neither calls `pull_pin()`

**8. Fuse Countdown Preservation**
- **Decision:** Remote detonation preserves and respects existing fuse countdown
- **Rationale:** If someone manually pulled pin, remote detonation doesn't interfere with active countdown
- **Implementation:** Check `db.pin_pulled` before arming the charge

---

## 8. Command Reference Summary

```
scan <explosive> with <detonator>
  - Scan explosive device into detonator memory
  - Max 20 explosives per detonator
  - Overrides previous detonator link

detonate e-<dbref> with <detonator>
  - Remotely detonate specific explosive
  - Pulls pin and starts fuse countdown
  - Respects explosive type behavior

detonate all with <detonator>
  - Remotely detonate all scanned explosives
  - Pulls pins and starts countdowns for all
  - No confirmation required (embrace chaos)

detonate list with <detonator>
  - Display a table of scanned explosives
  - Shows ID, type, status, fuse time, location
  - Auto-validates and cleans invalid entries

clear e-<dbref> from <detonator>
  - Remove single explosive from detonator
  - Breaks bidirectional link
  - Explosive no longer remotely detonable

clear all from <detonator>
  - Remove all explosives from detonator
  - Breaks all bidirectional links
  - Frees all 20 capacity slots
```

---

## 9. Future Enhancements (Not in Initial Implementation)

**Range Limitations:**
- Add signal strength system
- Require line-of-sight or proximity
- Interference from walls/materials

**Security Features:**
- Encrypted detonators with passcodes
- Anti-tamper mechanisms
- Signal jamming devices

**Advanced Features:**
- Timed/delayed remote detonation
- Sequential detonation patterns
- Multi-detonator synchronization
- Abort/disarm capabilities

**UI Improvements:**
- Sort detonator list by type/location/status
- Filter active vs ready explosives
- Highlight explosives in current room

---

## 10. Design Notes

**Why No Instant Detonation:**
- Maintains explosive type diversity (sticky vs standard vs rigged)
- Creates tactical timing windows
- Prevents instant-death griefing
- Allows counterplay (flee during countdown)
- Respects existing explosion code paths

**Why One Detonator Per Explosive:**
- Prevents detonator conflicts
- Clear ownership model
- Simplifies state tracking
- Makes override behavior intuitive

**Why No Range Limit:**
- Simpler implementation
- More cinematic gameplay
- Prevents frustrating "out of range" edge cases
- Can add range limits later if needed

**Why 20 Capacity:**
- High enough for tactical complexity
- Low enough to require planning
- Reasonable to display in UI
- Can adjust based on gameplay testing

---

## Conclusion

The remote detonator adds a powerful tactical tool for explosive management while respecting all existing explosive behaviors. By triggering normal pin-pull and countdown logic rather than bypassing it, the system maintains the unique characteristics of each explosive type (SPDR M9 magnetic seeking, rigged explosive trap mechanics, varied fuse times) while enabling complex multi-stage detonation plans.

The bidirectional tracking system ensures clean state management, and the override mechanics prevent conflicts while allowing detonator theft/takeover gameplay. Combined with the table display and capacity management, this creates a robust foundation for explosive-focused tactical gameplay.
