# Remote Detonator System Specification

A handheld remote detonator scans explosive devices and triggers them remotely. It holds a list of up to 20 scanned explosives and can trigger them one at a time or all at once. Triggering pulls the charge's pin and starts its normal fuse countdown. It works with every explosive type (sticky grenades, rigged explosives, standard grenades) and respects each one's own behaviour.

The item is `RemoteDetonator` in `typeclasses/items.py`. Its four commands, `CmdScan`, `CmdDetonate`, `CmdDetonateList` and `CmdClearDetonator`, live in `commands/CmdExplosives.py`, the explosives command file. There is no separate detonator cmdset: the four commands are added to the character cmdset (`CharacterCmdSet` in `commands/default_cmdsets.py`).

## Design Philosophy

**Key principle:** remote detonation **initiates** the explosive's normal behaviour; it does not bypass it.

- Remote detonation **pulls the pin** and starts the fuse countdown.
- SPDR M9 sticky grenades still get their 10-second countdown to seek/stick.
- Rigged explosives still get their 1-second countdown.
- Tactical grenades with 5-second fuses give 5 seconds to react.
- This keeps explosive types distinct and prevents instant-death scenarios.

**Tactical gameplay:**
- Plan complex multi-stage detonations with timed delays.
- Create distractions with long-fuse grenades while rigged traps explode quickly.
- Override your own rigged traps remotely before victims trigger them. A trap answers only to its rigger's detonator; anyone else must defuse it (owner ruling 2026-09-18, #3351).
- Mass detonation creates chaos with staggered explosion timing.

The override mechanics prevent conflicts while allowing detonator theft/takeover gameplay.

---

## 1. Remote Detonator Item

### Item properties

`RemoteDetonator.at_object_creation` sets three attributes:

- `scanned_explosives`: a list of the scanned explosives' ids (max 20)
- `max_capacity`: 20
- `device_type`: `"remote_detonator"`

### Prototype

`REMOTE_DETONATOR` in `world/prototypes.py` is branded, per the everything-branded mandate:

- key `"VECTOR UEM3 detonator"`
- aliases `["vector", "uem3", "uem-3", "detonator", "remote", "trigger"]`
- typeclass `typeclasses.items.RemoteDetonator`
- a VECTOR UEM3 desc (a compact military-grade remote detonator with a digital display of scanned explosive signatures, room for up to 20 of them, and a red safety cover over the main detonation switch)
- tags `("item", "general")` and `("tool", "category")`
- attrs `scanned_explosives` `[]`, `max_capacity` `20`, `device_type` `"remote_detonator"`

No key carries a dash followed by digits (#3779): Evennia's `name-N` ordinal form reads the first `-N` it meets, so a player could not narrow a twin.

---

## 2. Explosive Tracking

### Bidirectional relationship

Each explosive can be scanned by only ONE detonator at a time; a detonator can scan many explosives.

- On the explosive: `db.scanned_by_detonator` holds the detonator's id, or `None`. Explosive prototypes carry it as `None`.
- On the detonator: `db.scanned_explosives` is the list of explosive ids.

Both sides store the integer `.id`, never a `#dbref` string. `RemoteDetonator.add_explosive` (`typeclasses/items.py`) appends `explosive.id` to the list and sets `explosive.db.scanned_by_detonator = self.id`. Lookups rebuild the string (`search_object(f"#{id}")` in the detonator commands). The player-facing signature is `e-<id>`.

### Scanning rules

1. **One detonator per explosive.**
   - An explosive can be linked to only one detonator at a time.
   - Scanning with a new detonator **overrides** the previous link.
   - The previous detonator removes the explosive from its list.
2. **Capacity limit.**
   - A detonator can scan up to 20 explosives.
   - Scanning beyond capacity is refused with an error message.
   - Explosives must be cleared to free slots.
3. **No range limit.**
   - Once scanned, detonation works from any distance.
   - It works across rooms, floors and locations.
   - The link persists until the explosive detonates or is cleared.
4. **Automatic cleanup.**
   - Detonated explosives are removed from the detonator's list.
   - Destroyed explosives are removed from the detonator's list.
   - The detonator prunes dead entries on `scan`, `detonate list` and `detonate all`; `detonate e-<id>` drops a dead entry when it hits it.
   - Pruning is `RemoteDetonator.validate_scanned_list` (`typeclasses/items.py`); `remove_explosive` drops one entry; `get_scanned_count` validates the list, then counts it.
   - A dud is not destroyed: its pin is reset and it stays in the detonator's memory, so it can be detonated again (#2539).

---

## 3. Commands

**Requirement for every command:** the detonator must be wielded/held, not just carried in inventory.

| Command | Does |
|---|---|
| `scan <explosive> with <detonator>` | Scans the explosive into detonator memory. Max 20 per detonator. Overrides a previous detonator's link. |
| `detonate e-<id> with <detonator>` | Remotely detonates one explosive: pulls its pin and starts its fuse countdown, respecting its type's behaviour. |
| `detonate all with <detonator>` | Remotely detonates every scanned explosive: pulls the pins and starts all the countdowns. No confirmation required (embrace chaos). |
| `detonate list with <detonator>` or `detonator list` | Shows a table of scanned explosives: ID, type, status, fuse time, location. Validates and cleans invalid entries. |
| `clear e-<id> from <detonator>` | Removes one explosive from the detonator. Breaks the link; the explosive is no longer remotely detonable. |
| `clear all from <detonator>` or `detonator clear` | Removes all explosives from the detonator. Breaks every link; frees all 20 capacity slots. |

The `e-<id>` signature is the explosive's integer id.

### Scan

**Syntax:** `scan <explosive> with <detonator>`

In order (`CmdScan.func`, with the list work in `RemoteDetonator.add_explosive`):

1. Find the explosive in the caller's inventory OR the caller's room (#3351), and the detonator in the caller's inventory.
2. Confirm the explosive has `is_explosive`.
3. A rigged explosive (`db.rigged_to_exit` set) is refused unless `db.rigged_by` is the caller: "X is someone else's trap. Defuse it if you want it gone."
4. Check the detonator is wielded/held.
5. Check capacity (< 20), after pruning dead entries.
6. If the explosive is already scanned by a different detonator, override the old link (remove it from the old detonator's list) and add it to this one; otherwise add it.
7. Set both references and send the success messages.

**Messages:**
```
You: You scan {key} into {detonator}'s memory.
       Signature: e-{id}
       Capacity: n/20

Room: {actor} points a device at {key}, which emits a soft beep.
```

**Edge cases:**
- Already scanned by this detonator: "The SPDR M9 grenade is already scanned by this detonator."
- Capacity full: "Detonator at maximum capacity (20 explosives)."
- Already scanned by a different detonator: override the old link and show message.
- Non-explosive item: "The sword is not an explosive device."

### Detonate single

**Syntax:** `detonate e-<id> with <detonator>`

In order (`CmdDetonate.detonate_single`):

1. Check the id is in the detonator's scanned list.
2. Get the explosive; if it no longer exists, say so and drop the entry.
3. If its pin is already pulled (countdown active), refuse: "{key} is already detonating!"
4. Otherwise arm it: set `db.pin_pulled`, clear `db.hidden` (an armed charge cannot stay hidden, #3767), and set the countdown from `armed_fuse(explosive)`.
5. Send the operator's and the operator's room's lines, then the arming beep (`announce_arming`, see "Who hears the arming beep" below), then start `start_grenade_ticker`, then erase a trap's exit registration (`clear_exit_rigging`).
6. Keep the explosive in the scanned list; it is removed when it explodes.

The countdown is `armed_fuse(explosive)`: the charge's own `db.fuse_time` (10 for an SPDR M9, 8 if none is set), or `TRAP_FUSE_TIME` (1) for a rigged trap.

**Messages:**
```
You: You flip open the red safety cover on {detonator} and press the large button. A distant beep echoes!

Operator's Room: {actor} flips open a red safety cover on their {detonator} and presses a large button.

Grenade's Location (if different room): An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]

Same Room (if operator and grenade in same location):
  {actor} flips open a red safety cover on their {detonator} and presses a large button.
  An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]
```

The `[N seconds]` tag is shown only to viewers with Builder permission (#3350); players see the line without it.

**Edge cases:**
- Id not in the list: "e-1234 is not in this detonator's memory."
- Explosive no longer exists: "e-1234 no longer exists." and the entry is removed from the list.
- Already detonating: "{key} is already detonating!"

### Detonate all

**Syntax:** `detonate all with <detonator>`

In order (`CmdDetonate.detonate_all`):

1. Prune dead entries from the list.
2. Go through every scanned explosive: skip one that no longer exists, skip one already detonating, and arm each other one exactly as `detonate e-<id>` does (pin pulled, `db.hidden` cleared, countdown from `armed_fuse`).
3. Send the operator's lines and the operator's room's line.
4. Then, per armed charge: the arming beep, then `start_grenade_ticker`, then `clear_exit_rigging`.
5. Explosives are removed from the list as they explode.

`detonate all` and `detonate e-<id>` take a charge's fuse from the same `armed_fuse(explosive)`: a rigged trap gets `TRAP_FUSE_TIME` (1 second) through either command, and every other charge gets its own `fuse_time`, or 8 if it has none (#2547, #3348). Countdowns are staggered by each explosive's fuse.

**Messages:**
```
You: You flip open the red safety cover on {detonator} and press the large button. Multiple distant beeps echo from various locations!
     Detonated {n} explosive(s).

Operator's Room: {actor} flips open a red safety cover on their {detonator} and presses a large button. Multiple distant beeps echo from various locations!

Grenade 1 Location: An SPDR M9 grenade beeps and its light begins flashing! [10 seconds]
Grenade 2 Location: A tactical grenade beeps and its light begins flashing! [5 seconds]
Grenade 3 Location (a rigged trap): An SPDR M9 grenade beeps and its light begins flashing! [1 seconds]
```

- The operator sees one "multiple beeps" line, plus the count.
- The operator's room sees the button press plus "multiple beeps".
- Each grenade's location gets its own activation line.
- The `[N seconds]` tag is shown only to viewers with Builder permission (#3350).

That is all the operator reads. Charges already detonating are counted only on the splattercast debug channel; invalid entries are silently skipped, never counted, listed or reported.

**Edge cases:**
- Empty list: "<detonator> has no scanned explosives." (after pruning dead entries: "<detonator> has no valid explosives to detonate.")
- All already active: "All scanned explosives are already detonating."
- Mixed results: 📋 UNBUILT (no issue), see "Unbuilt".

### Cross-room messaging

Both the operator's location and the grenade's location get messages (Decision 5).

- The operator always sees the button-press action.
- The operator's room sees "flips open ... presses a large button".
- The grenade's room, if different, sees "grenade beeps and its light begins flashing".
- If the operator and grenade share a room, both lines go to that room.
- Observers see different perspectives depending on where they are.

### Who hears the arming beep

The arming beep reaches the bearer and their room (#3350, 2026-09-18; owner: tell the room, never re-tell the person it is on, and show the bracketed countdown to builders only).

A charge's `location` is often not a room: stuck, it is the armor item; carried or held, it is the character. `arming_audience(explosive)` (`commands/CmdExplosives.py`) walks up to the room and returns `(room, bearer, armor)`. `announce_arming(caller, explosive, fuse_time)` is the one door for both `detonate e-<id>` and `detonate all`. It is called after the operator's own lines and BEFORE `start_grenade_ticker`, because the sticky ticker's first countdown warning fires synchronously, so the beep must come before the count.

- The bearer gets one personal line: "The X stuck to your <armor> beeps and its light begins flashing!" / "The X in your hand beeps..." / "The X in your pocket beeps..."
- Their room hears it on them through the identity door, with the bearer excluded: "The X stuck to {target_char}'s <armor> beeps..." / "The X in {target_char}'s hand beeps..." / "Something in {target_char}'s pocket beeps!"
- A loose charge is announced to its room.
- `fuse_tag(viewer, fuse_time)` appends ` [N seconds]` only for viewers with Builder permission; `tell_room_arming` renders a room line with and without it.
- The sticky ticker's per-second `*** N SECONDS ***` warnings reach a wearer and follow the beep.

### List

**Syntax:** `detonate list with <detonator>` or `detonator list` (if wielded)

`CmdDetonateList.func` prunes dead entries, then shows an `EvTable(border="cells", width=78)` framed by `=` rules: a "REMOTE DETONATOR - SCANNED DEVICES" heading, a `Capacity: n/20` line, five columns (ID, Device, Status, Fuse, Location), and the legend:

```
Status Legend:
  READY  - Armed and ready for remote detonation
  ACTIVE - Currently counting down (pin already pulled)
  STUCK  - Sticky grenade adhered to target
  TRAP   - Rigged explosive waiting for trigger
```

Status and location strings are built inline in `CmdDetonateList.func`.

**Status:**
- **READY**: pin not pulled, ready for remote detonation. Fuse shows the fuse it will get, e.g. `10s`.
- **ACTIVE**: pin pulled, countdown in progress. Fuse shows the time left, e.g. `3s left!`.
- **STUCK**: sticky grenade adhered to armor/character.
- **TRAP**: rigged explosive set up as a trap. Fuse shows the fuse the trap will actually get, `1s (trap)`, from the same `armed_fuse` the two detonate commands use (#3349).

**Location:**
- The room name if in a room; a charge on the ground shows the bare room key.
- "Your inventory" if carried by the user.
- "On {character_name}" if stuck to a character.

**Edge cases:**
- Empty list: "<detonator> has no scanned explosives."
- All invalid: dead entries are pruned and the same "<detonator> has no scanned explosives." is shown.

### Clear single

**Syntax:** `clear e-<id> from <detonator>`

`CmdClearDetonator.clear_single` checks the id is in the scanned list, removes it from the detonator's list, and clears the explosive's `scanned_by_detonator` if the explosive still exists.

**Messages:**
```
You: You clear e-1234 (SPDR M9 grenade) from your remote detonator's memory.

Room: {char_name} presses several buttons on their remote detonator.
```

**Edge cases:**
- Id not in the list: "e-1234 is not in this detonator's memory."
- Explosive no longer exists: removed like any other entry; the confirmation shows the signature in place of the name: "You clear e-1234 (e-1234) from <detonator>'s memory."

### Clear all

**Syntax:** `clear all from <detonator>` or `detonator clear`

`CmdClearDetonator.clear_all` clears `scanned_by_detonator` on every explosive that still exists, empties the detonator's list, and reports the count.

**Messages:**
```
You: You clear all 8 explosive signatures from your remote detonator's memory.

Room: {char_name} holds down a button on their remote detonator, which emits a series of beeps before going silent.
```

**Edge cases:**
- Empty list: "<detonator> has no scanned explosives to clear."

---

## 4. Integration with Existing Explosion Logic

### Pin pull

Remote detonation uses the **same pin-pull logic** as manual grenade use. If `db.pin_pulled` is already set, the charge is not re-armed. Otherwise the detonate commands set `db.pin_pulled`, set the countdown (`ndb` countdown remaining) from `armed_fuse()`, announce the arming beep, and start the same `start_grenade_ticker` that `pull` uses. Neither command calls `pull_pin()`.

The pin flag is the raw attribute `db.pin_pulled`. Attributes are addressed by raw name; no `DB_*` constants exist (#3386). Explosives are a backbone of the mining experience, so the attribute contract lives here: `pin_pulled`, `blast_damage`, `blast_radius`, `dud_chance`, `chain_trigger`, `requires_pin`, `detonation_deadline`.

### Explosive type behaviours

- **Standard grenades (frag, tactical, demo):** remote detonation → pin pulled → countdown starts → explosion at location, through `explode_standalone_grenade` in `commands/explosion_utils.py`.
- **SPDR M9 sticky grenades:** remote detonation → pin pulled → 10s countdown. During the countdown, if thrown, it still seeks magnetic targets. If stuck, it explodes stuck to armor; if on the ground, it explodes at the ground location (existing behaviour).
- **Rigged explosives:** remote detonation → pin pulled → 1s countdown → explosion. This bypasses the trap trigger logic (remote override). It explodes through `explode_standalone_grenade` like any remotely armed charge, not the tripwire's own explosion, and respects the proximity system for damage.
- **Thrown grenades (in flight or counting down):** if the countdown has already started, a remote detonation attempt gets the "already active" message. An explosive already counting down cannot be re-triggered.

### Explosion path

The detonator calls the existing explosion path: `CmdDetonate` → `start_grenade_ticker(explosive)` (`commands/explosion_utils.py`) → `explode_standalone_grenade(explosive)`. That function finds the location (room or armor hierarchy), gets the proximity list, calculates and applies damage to all in proximity, checks human-shield mechanics, sends the explosion messages and deletes the grenade. `Item.at_object_delete` then removes it from its detonator's list.

---

## 5. Edge Cases and Special Scenarios

### Sticky grenades

For who hears the arming beep when the charge is on a person, see "Who hears the arming beep" in section 3.

- **Stuck to armor:** an SPDR M9 magnetically stuck to a character's plate mail. Remote detonation pulls the pin → 10s countdown. It explodes while stuck to the armor (existing behaviour); damage goes to the wearer and those in proximity.
- **In inventory:** remote detonation pulls the pin → 10s countdown. The character is holding a live grenade (existing behaviour) and can drop it before it explodes.
- **On the ground:** remote detonation pulls the pin → 10s countdown. It explodes at the ground location and damages everyone in proximity (existing logic).

### Already-active explosives

- **Pin already pulled:** someone manually pulls the pin and the countdown starts. A remote detonation attempt checks `db.pin_pulled`. `detonate e-<id>` answers "<charge name> is already detonating!"; `detonate all` skips it silently unless nothing else was armed. No re-trigger; the countdown continues normally.
- **Multiple detonators:** detonator A detonates a grenade and the countdown starts. Detonator B's attempt checks `db.pin_pulled` and gets the same answers. This prevents the exploit of resetting/extending a countdown.

### Rigged explosives

- **Trap override:** a rigged explosive set as a trap in a doorway. Remote detonation pulls the pin → 1s countdown (`TRAP_FUSE_TIME`, via `armed_fuse`). It explodes BEFORE anyone triggers the trap. Useful for clearing your own traps safely.
- **Trap + remote:** a rigged explosive scanned by a detonator. Someone triggers the trap: `db.pin_pulled` is set and the 1s countdown starts. A remote detonation attempt checks `db.pin_pulled`; `detonate e-<id>` answers "<charge name> is already detonating!" and `detonate all` skips it silently unless nothing else was armed. It cannot be re-triggered during the countdown.

**One eraser, three doors (#3388, 2026-09-18).** A trap's registration (`exit.db.rigged_grenade` on the rigged exit and on its return exit) is cleared by `clear_exit_rigging(grenade)` in `commands/explosion_utils.py`. The tripwire door, `defuse`, and both remote doors (`detonate e-<id>` and `detonate all`, right after the fuse starts) all call it, so both sides of the doorway are disarmed the moment the fuse starts (a second walker crossing during the fuse second cannot re-fire the same live grenade), and no exit keeps a stored record naming the deleted grenade. The grenade's own `rigged_to_exit` stays set until `defuse` clears it: `defuse`, `scan`'s ownership guard and `detonate list` read it.

**One restore door, and the door itself (#3560, 2026-09-21).** Taking a trap OFF — both exits' records, the grenade's `rigged_to_exit`/`rigged_by`, and the room-render state `rig` set (`integrate`, `integration_desc`, `integration_priority`, restored from `original_*`) — is `unrig_grenade(grenade)` in `commands/explosion_utils.py`. `defuse` adds its lines around it, and `Exit.at_object_delete` calls it when the door the wire was strung across is destroyed, so a trap never outlives its door. The crane car keeps its exits across rides (see `CraneContainer`).

**Naming the charge (#3783).** `rig <name> to <exit>` and `defuse <name>` resolve the name with the one core matcher, `Character.search(name, candidates=pool)`: exact key or alias first (a branded charge's alias works, such as `dx-15` for "HDG DX15 demolition charge"), then word-start partials, ordinals (`2nd grenade`) and the presence gate. A fragment from inside a word (`nade`) does not match.
- `rig`'s pool is what is in your hands. A held non-explosive or pin-pulled charge keeps its own refusal, and a name nothing in hand matches falls back to "You must be wielding" (carried) or "You don't have" (nowhere).
- `defuse` tries the explosives already in reach first (live or not, so a dud in reach answers "not armed"), then the live ones in the room or your inventory (pin pulled or rigged).
- Each pool is filtered before matching, so an ordinal counts only those.
- Several matches still refuse with "Be more specific", answerable with an ordinal or an alias.

### Multiple detonators

Detonator A scans a grenade (`grenade.db.scanned_by_detonator` = A). Detonator B scans the same grenade: it is removed from A's list, added to B's list, and `scanned_by_detonator` becomes B. Detonator A can no longer detonate it.

### Automatic cleanup

- **Explosive detonated** (any method: manual, remote, trap): the explosion deletes the explosive, and `Item.at_object_delete` looks up its detonator through `scanned_by_detonator` and removes it from that detonator's list.
- **Explosive destroyed** (taken from a corpse, object destroyed, etc.): `Item.at_object_delete` removes it from its detonator's list; failing that, the next `scan`, `detonate list` or `detonate all` prunes it.
- **Detonator destroyed:** `RemoteDetonator.at_object_delete` clears `scanned_by_detonator` on every linked explosive. Those explosives are no longer remotely detonable.

---

## 6. Decisions

**1. Already-active grenade behaviour**
- **Decision:** show the "already detonating" message; don't re-trigger.
- **Rationale:** prevents exploits and keeps behaviour predictable.
- **Implementation:** check `db.pin_pulled` before remote detonation.

**2. Code organization**
- **Decision:** detonator commands live in `commands/CmdExplosives.py`, the dedicated explosives command file.
- **Rationale:** explosives commands are grouped together in their own module.

**3. Rigged explosive countdown timing**
- **Decision:** a rigged trap gets `TRAP_FUSE_TIME` (1 second) however it is set off.
- **Implementation:** `armed_fuse(explosive)` in `commands/CmdExplosives.py` returns `TRAP_FUSE_TIME` when `db.rigged_to_exit` is set. Rigging does not touch the grenade's own `fuse_time` (#2547).
- **Rationale:** (was: "Rigging process already sets `grenade.db.fuse_time = 1`, no special handling needed"; nothing ever wrote that, see #2547)

**4. Cleanup integration point**
- **Decision:** use the `at_object_delete()` hook: `Item.at_object_delete` (`typeclasses/items.py`) for explosives, `RemoteDetonator.at_object_delete` for the detonator. (`at_delete` is not an Evennia hook; #2590.)
- **Rationale:** catches every deletion case cleanly (explosion, pickup, destroy, etc.).

**5. Cross-room messaging**
- **Decision:** both the operator's location and the grenade's location get messages.
- **Rationale:** "Operator just presses a button and that's what people see. Locations see the whole shebang."
- **Implementation:** operator's room: "{actor} flips open a red safety cover on their {detonator} and presses a large button."; grenade's room: "An SPDR M9 grenade beeps and its light begins flashing!"

**6. Wielding requirement**
- **Decision:** the detonator must be wielded/held to use (not just in inventory).
- **Rationale:** requires active use; prevents passive inventory operation.

**7. Pin state handling**
- **Decision:** a charge whose pin is already pulled is not re-armed (see Decisions 1 and 8).
- **Implementation:** `detonate e-<id>` refuses with "<charge name> is already detonating!" and `detonate all` skips the charge; neither calls `pull_pin()`.

**8. Fuse countdown preservation**
- **Decision:** remote detonation preserves and respects an existing fuse countdown.
- **Rationale:** if someone manually pulled the pin, remote detonation does not interfere with the active countdown.
- **Implementation:** check `db.pin_pulled` before arming the charge.

---

## 7. Unbuilt

- 📋 UNBUILT (no issue) **`detonate all` per-signature report.** A summary line ("Your remote detonator confirms: 5 explosives armed, 1 already active, 2 invalid.") and a display block listing each signature's result:
  ```
  Your remote detonator displays:
    e-1234: ARMED (10s) - SPDR M9 grenade
    e-1235: ARMED (8s) - frag grenade
    e-1236: ARMED (5s) - tactical grenade
    e-1237: ARMED (10s) - demo charge
    e-1238: ARMED (1s) - rigged SPDR M9 grenade
    e-1239: [ALREADY ACTIVE]
    e-1240: [INVALID - REMOVED]
    e-1241: [INVALID - REMOVED]
  ```
  For mixed results, a detailed breakdown of successes and failures.

### Future enhancements (not in the initial implementation)

📋 UNBUILT (no issue), each:

**Range limitations:**
- A signal strength system
- Require line-of-sight or proximity
- Interference from walls/materials

**Security features:**
- Encrypted detonators with passcodes
- Anti-tamper mechanisms
- Signal jamming devices

**Advanced features:**
- Timed/delayed remote detonation
- Sequential detonation patterns
- Multi-detonator synchronization
- Abort/disarm capabilities

**UI improvements:**
- Sort the detonator list by type/location/status
- Filter active vs ready explosives
- Highlight explosives in the current room

---

## 8. Design Notes

**Why no instant detonation:**
- Keeps explosive types distinct (sticky vs standard vs rigged)
- Creates tactical timing windows
- Prevents instant-death griefing
- Allows counterplay (flee during the countdown)
- Respects existing explosion code paths

**Why one detonator per explosive:**
- Prevents detonator conflicts
- Clear ownership model
- Simplifies state tracking
- Makes override behaviour intuitive

**Why no range limit:**
- Simpler implementation
- More cinematic gameplay
- Prevents frustrating "out of range" edge cases
- Range limits can be added later if needed

**Why 20 capacity:**
- High enough for tactical complexity
- Low enough to require planning
- Reasonable to display in the UI
- Can be adjusted based on gameplay testing
