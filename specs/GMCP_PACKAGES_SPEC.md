# GMCP Packages Specification

## Overview

This spec defines the Generic MUD Communication Protocol (GMCP) packages
that Gelatinous should send to clients over WebSocket connections. GMCP
enables structured, machine-readable data alongside the traditional text
stream, allowing clients like Telix to provide rich UI features (room maps,
vitals gauges, chat panels) without fragile screen-scraping.

Gelatinous uses the `gmcp.mudstandards.org` WebSocket subprotocol via the
Evennia `evennia-mudstandards` fork. In this wire format, BINARY frames
carry raw ANSI text and TEXT frames carry GMCP messages in the standard
`"Package.Name json_payload"` format.

**Current state**: Gelatinous advertises `"GMCP": "1"` in MSSP but sends
no custom GMCP packages. All output is plain `msg(text=...)` calls.

---

## Design Philosophy

1. **Standard package names** -- Use established GMCP package names from
   the community spec (mudstandards.org / Aardwolf / IRE) wherever
   possible. Invent new names only for game-specific data.

2. **Incremental adoption** -- Each package is independently useful.
   Implement in priority order; clients degrade gracefully when packages
   are absent.

3. **Server-push model** -- The server sends GMCP messages at natural
   game events (room entry, stat change, chat message). Clients do not
   poll.

4. **Minimal payloads** -- Send only what clients need for display.
   Internal IDs and implementation details stay server-side.

---

## Package Inventory

| Package | Purpose | Priority |
|---------|---------|----------|
| `Room.Info` | Room identity, exits, area | Phase 1 |
| `Char.Vitals` | Health, consciousness, blood, pain | Phase 1 |
| `Char.Stats` | G.R.I.M. base stats | Phase 2 |
| `Char.Status` | Combat state, conditions | Phase 2 |
| `Comm.Channel.Text` | Channel message delivery | Phase 2 |
| `Comm.Channel.List` | Available channels | Phase 3 |
| `Char.Items.Inv` | Inventory contents | Phase 3 |
| `Char.Items.Hands` | Wielded/held items | Phase 3 |

---

## Phase 1: Core Packages

### Room.Info

Sent when a character enters a room or the room state changes
significantly (exit added/removed, room renamed).

**Trigger**: Override `Character.at_post_move()` or
`Room.return_appearance()` to call
`session.msg(oob=("Room.Info", payload))` after the look text.

**Payload**:

```json
{
  "num": 42,
  "name": "Cargo Bay 7",
  "area": "Station Core",
  "type": "interior",
  "outside": false,
  "exits": {
    "north": 43,
    "south": 41,
    "up": 100
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `num` | int | Room database ID (`room.id`). Stable across restarts. |
| `name` | str | Room display name (`room.key`). |
| `area` | str | Zone or area name. Use room tags with category `"area"`, or fall back to `"Unknown"`. |
| `type` | str/null | Room type from `room.type` attribute (`"street"`, `"interior"`, `"bridge"`, `"sky"`, `"alley"`, `"corridor"`, or `null`). |
| `outside` | bool | Whether the room is outdoors (`room.outside`). |
| `exits` | dict | Map of exit name to destination room ID. Cardinal directions use short names (`"north"` not `"n"`). Custom exit names preserved as-is. |

**Implementation notes**:
- Use `room.id` (the Django model PK) as the stable room identifier, not
  `room.dbref` (which is a string like `"#42"`).
- Exit destinations: `exit.destination.id` for each exit in
  `room.exits`. Skip exits with no destination.
- Area: Check `room.tags.get(category="area")`. If no area tag exists,
  use `"Unknown"`.

---

### Char.Vitals

Sent when any vital sign changes: taking damage, bleeding tick, healing,
consciousness change, or combat round processing.

**Trigger**: Call after any medical state mutation -- wound application,
bleeding tick, healing action, consciousness change. Hook into
`MedicalState` mutation methods or add a `send_vitals()` helper called
from combat resolution and medical tick processing.

**Payload**:

```json
{
  "blood": 85,
  "blood_max": 100,
  "pain": 12,
  "consciousness": 95,
  "alive": true,
  "conscious": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `blood` | int | Current blood level (0-100 percentage). From `medical_state.blood_level`. |
| `blood_max` | int | Always `100`. Included for client gauge calculations. |
| `pain` | int | Current pain level (0+). From `medical_state.pain_level`. Rounded to int. |
| `consciousness` | int | Consciousness percentage (0-100). From `medical_state.consciousness * 100`. Rounded to int. |
| `alive` | bool | `True` if character is alive. From `not character.is_dead()`. |
| `conscious` | bool | `True` if character is conscious. From `not character.is_unconscious()`. |

**Implementation notes**:
- Round float values to integers for client display simplicity.
- `blood_max` is always 100 (percentage-based system), but including it
  lets clients render gauges without hardcoding the max.
- Death threshold is at 85% blood loss (`BLOOD_LOSS_DEATH_THRESHOLD`);
  unconsciousness at consciousness below 0.3
  (`CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD / 100`). Clients should not
  hardcode these -- use the `alive` and `conscious` booleans.

---

## Phase 2: Extended Packages

### Char.Stats

Sent on login and when base stats change (rare -- stat changes are
uncommon after character creation).

**Trigger**: Send once during session initialization (after character
selection) and whenever a stat value is modified.

**Payload**:

```json
{
  "grit": 75,
  "resonance": 60,
  "intellect": 90,
  "motorics": 75
}
```

| Field | Type | Description |
|-------|------|-------------|
| `grit` | int | Physical toughness (1-150). From `character.grit`. |
| `resonance` | int | Social influence (1-150). From `character.resonance`. |
| `intellect` | int | Knowledge/crafting (1-150). From `character.intellect`. |
| `motorics` | int | Agility/reflexes (1-150). From `character.motorics`. |

---

### Char.Status

Sent when combat state changes: entering/leaving combat, grapple state
changes, aiming, proximity changes, or condition changes.

**Trigger**: Hook into `CombatHandler.add_combatant()`,
`CombatHandler.remove_combatant()`, grapple/proximity state changes,
and medical condition application/removal.

**Payload**:

```json
{
  "in_combat": true,
  "yielding": false,
  "grappling": null,
  "grappled_by": null,
  "aiming_at": null,
  "proximity": ["Rask", "Kell"],
  "conditions": ["bleeding", "pain"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `in_combat` | bool | Whether the character is in active combat. |
| `yielding` | bool | Whether the character is in yielding (non-violent) state. |
| `grappling` | str/null | Name of character being grappled, or `null`. |
| `grappled_by` | str/null | Name of character grappling this one, or `null`. |
| `aiming_at` | str/null | Name of character being aimed at, or `null`. |
| `proximity` | list[str] | Names of characters in melee proximity. |
| `conditions` | list[str] | Active medical condition types: `"bleeding"`, `"pain"`, `"infection"`, `"unconscious"`. |

**Implementation notes**:
- Use display names (`.key`) for character references, not dbrefs.
  Clients use these for display only -- commands use target names from
  the text stream.
- `conditions` is a list of active condition type strings, not detailed
  severity data. Severity is communicated through the text stream.
- Only send when state actually changes to avoid flooding the client.

---

### Comm.Channel.Text

Sent when a message is posted to a channel the character is subscribed to.

**Trigger**: Override channel message delivery to include a GMCP message
alongside the normal text output.

**Payload**:

```json
{
  "channel": "Public",
  "sender": "Rask",
  "text": "Anyone seen the supply drop?"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `channel` | str | Channel name. |
| `sender` | str | Display name of the message sender. |
| `text` | str | Plain text content of the message (no ANSI). |

**Implementation notes**:
- Strip ANSI color codes from `text` -- the client applies its own
  channel color scheme.
- The normal colorized channel text still arrives via the BINARY text
  stream. This GMCP message provides structured metadata for clients
  that want to render channels in dedicated panels.

---

## Phase 3: Supplementary Packages

### Comm.Channel.List

Sent on login and when channel subscriptions change.

**Payload**:

```json
[
  {"name": "Public", "caption": "General chat"},
  {"name": "Splattercast", "caption": "Combat debug"}
]
```

Each entry:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Channel key used in commands. |
| `caption` | str | Human-readable channel description. |

---

### Char.Items.Inv

Sent when inventory changes (pick up, drop, give, receive).

**Payload**:

```json
{
  "items": [
    {"name": "Combat Knife", "dbref": "#145", "type": "weapon"},
    {"name": "Kevlar Vest", "dbref": "#201", "type": "armor", "worn": true},
    {"name": "Medkit", "dbref": "#302", "type": "item"}
  ]
}
```

Each item:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Item display name. |
| `dbref` | str | Item dbref for disambiguation in commands. |
| `type` | str | Category: `"weapon"`, `"armor"`, `"item"`. |
| `worn` | bool | Present and `true` if the item is currently worn. Omitted if not worn. |

---

### Char.Items.Hands

Sent when wielded items change (wield, unwield, disarm).

**Payload**:

```json
{
  "left": {"name": "Combat Knife", "dbref": "#145"},
  "right": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `left` | object/null | Item in left hand, or `null` if empty. |
| `right` | object/null | Item in right hand, or `null` if empty. |

Each hand item:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Item display name. |
| `dbref` | str | Item dbref. |

---

## Evennia Implementation Pattern

All GMCP messages are sent through Evennia's OOB (Out-Of-Band) system.
The `evennia-mudstandards` fork routes `oob` kwargs through the
`gmcp.mudstandards.org` wire format codec, which encodes them as
WebSocket TEXT frames.

### Sending a GMCP message

```python
# From any command or hook with access to the character
def send_room_info(character):
    """Send Room.Info GMCP to all sessions."""
    room = character.location
    if not room:
        return

    exits = {}
    for ex in room.exits:
        if ex.destination:
            exits[ex.key] = ex.destination.id

    area = room.tags.get(category="area") or "Unknown"

    payload = {
        "num": room.id,
        "name": room.key,
        "area": area,
        "type": getattr(room, "type", None),
        "outside": getattr(room, "outside", False),
        "exits": exits,
    }

    character.msg(oob=("Room.Info", payload))
```

### Hook points

| Package | Where to hook |
|---------|---------------|
| `Room.Info` | `Character.at_post_move()`, after the look text is sent |
| `Char.Vitals` | After medical state mutations in `world/medical/` |
| `Char.Stats` | `Character.at_post_login()` and stat modification commands |
| `Char.Status` | `CombatHandler` state change methods, condition apply/remove |
| `Comm.Channel.Text` | Channel `.msg()` override or `at_post_channel_msg()` |
| `Comm.Channel.List` | `Character.at_post_login()` and channel join/leave |
| `Char.Items.Inv` | `Character.at_get()`, `at_drop()`, `at_give()` |
| `Char.Items.Hands` | Wield/unwield commands |

---

## Client Integration (Telix)

Telix already has infrastructure for these packages:

- **Room.Info** -- `rooms.py` (`RoomStore`) persists room graph to
  SQLite. `on_room_info` callback in `session_context.py` updates
  `ctx.current_room_num` and the room graph. Enables F7 room browser,
  fast-travel, randomwalk, and autodiscover.

- **Char.Vitals** -- `progressbars.py` renders configurable progress
  bars in the REPL toolbar from GMCP data in `ctx.gmcp_data`.

- **Comm.Channel.Text** -- `chat.py` persists channel messages to
  SQLite. `on_chat_text` callback enables the F9 chat panel.

- **Comm.Channel.List** -- `on_chat_channels` callback populates
  channel list for the chat panel.

When Gelatinous implements these packages, Telix features activate
automatically through the existing GMCP dispatch in both the telnet
and WebSocket shells (`telix_client_shell` and `ws_client_shell`).

---

## Implementation Roadmap

### Phase 1 -- Core (High Priority)

- [ ] `Room.Info` -- Hook `Character.at_post_move()` to send room data
  after movement
- [ ] `Char.Vitals` -- Add `send_vitals()` helper, call from medical
  state mutation points
- [ ] Area tagging -- Add `"area"` category tags to rooms for zone names

### Phase 2 -- Extended

- [ ] `Char.Stats` -- Send on login and stat change
- [ ] `Char.Status` -- Hook combat handler state transitions
- [ ] `Comm.Channel.Text` -- Override channel message delivery

### Phase 3 -- Supplementary

- [ ] `Comm.Channel.List` -- Send on login and subscription change
- [ ] `Char.Items.Inv` -- Hook inventory change methods
- [ ] `Char.Items.Hands` -- Hook wield/unwield commands

---

## Testing

Each package should have tests verifying:

1. **Payload correctness** -- Mock a character/room, call the send
   function, assert the `msg()` call contains the expected `oob` tuple.
2. **Trigger points** -- Verify the GMCP message is sent at the correct
   game events (room entry, damage, channel message).
3. **Edge cases** -- Room with no exits, character with no medical state,
   empty inventory, null hand slots.
4. **Wire format** -- Connect a test WebSocket client, verify TEXT frames
   contain properly formatted `"Package.Name {json}"` strings.
