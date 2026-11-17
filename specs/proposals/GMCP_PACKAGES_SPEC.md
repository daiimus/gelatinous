# GMCP Packages Specification

> **Status:** 📋 Proposal — not implemented (tracking #305). The game advertises GMCP in MSSP but sends no custom packages yet.

## Overview

This spec defines the Generic MUD Communication Protocol (GMCP) packages
that Gelatinous should send to clients over WebSocket connections. GMCP
enables structured, machine-readable data alongside the traditional text
stream, allowing clients like Telix to provide rich UI features (room maps,
vitals gauges, chat panels) without fragile screen-scraping.

Gelatinous speaks the `gmcp.mudstandards.org` WebSocket subprotocol through
its own handler, `GmcpWebSocketClient` in `server/conf/gmcp_websocket.py`.
BINARY frames carry raw ANSI text and TEXT frames carry GMCP messages in the
standard `"Package.Name json_payload"` format.

> **Correction (2026-09-12):** there is no forked Evennia. The
> `evennia-mudstandards` fork's work landed **upstream**. Evennia 6.1.0 (July 5 2026) ships WebSocket subprotocol
> negotiation natively — CHANGELOG `[Feat][pull3867]`: "Add WebSocket
> subprotocol negotiation per MUD Standards proposal. Supports
> `json.mudstandards.org`, `gmcp.mudstandards.org`,
> `terminal.mudstandards.org` and `v1.evennia.com` … New
> `WEBSOCKET_SUBPROTOCOLS` setting. (daiimus)" — implemented in
> `evennia/server/portal/wire_formats/gmcp_standard.py`. The container runs
> that stock `evennia/evennia:latest` (6.1.0); there is no forked Evennia.
>
> Gelatinous does **not** use the stock codec. `server/conf/settings.py`
> sets `WEBSOCKET_PROTOCOL_CLASS =
> "server.conf.gmcp_websocket.GmcpWebSocketClient"`, and that in-repo
> subclass accepts the subprotocol in its own `onConnect()` and overrides
> `send_text` / `send_prompt` / `send_default` / `onMessage`, so the stock
> wire-format codec never runs. `server/conf/gmcp_websocket.py` is the live
> wire contract this spec must satisfy — and it is **not** the same contract
> as the stock codec; see the correction under "Evennia Implementation
> Pattern" before writing any send call.

**Current state**: Gelatinous advertises `"GMCP": "1"` in MSSP but sends
no game GMCP packages. Besides text, the only TEXT frame a GMCP client
receives is a bare `logged_in` at login, from `session.msg(logged_in={})`
in `Account.at_post_login` (`typeclasses/accounts.py`).

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
`character.msg(**{"Room.Info": [[payload], {}]})` after the look text.

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
| `type` | str/null | Room type from the `room.type` attribute (for example `"street"`, `"interior"`, `"market"`, `"sky"`, `"shaft"`, `"rooftop"`), or `null`. The set is open: builders add types, so clients must accept any string. |
| `outside` | bool | Whether the room is outdoors (`room.outside`). |
| `exits` | dict | Map of exit name to destination room ID. Cardinal directions use short names (`"north"` not `"n"`). Custom exit names preserved as-is. |

**Implementation notes**:
- Use `room.id` (the Django model PK) as the stable room identifier, not
  `room.dbref` (which is a string like `"#42"`).
- Exits: build the map from `room._visible_exits(character)`, never from
  `room.exits`. A secret (view-locked) exit the character has not found
  must not appear. Skip exits with no destination.
- Area: Check `room.tags.get(category="area")`. If no area tag exists,
  use `"Unknown"`. No room carries an `area` tag today, so as written every
  room sends `"Unknown"`. `world.wsis.zone_of(room)` already names a
  room's street or building (the room key before " - ").

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
- Death comes at 85% blood loss (`BLOOD_LOSS_DEATH_THRESHOLD`) or when a
  lethal body capacity (heart, breathing, digestion, neck, brain) reaches
  zero. Unconsciousness comes when consciousness falls below 0.3
  (`CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD / 100`). Both thresholds are
  untuned placeholders. Clients should not hardcode either -- use the
  `alive` and `conscious` booleans.

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
| `conditions` | list[str] | Active medical condition types, from `condition.condition_type`: `"bleeding"`, `"pain"`, `"infection"`, `"consciousness_suppression"`, `"renal_failure"`, `"addiction"`. Unconsciousness is not a condition; it is the `conscious` field of `Char.Vitals`. |

**Implementation notes**:
- Name each character as this character perceives them:
  `get_display_name_safe(other, character)` (`world/combat/utils.py`).
  Never use `.key`, which is the real name. Clients use these names for
  display only -- commands use target names from the text stream.
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
| `dbref` | str | Item dbref. Players cannot type a dbref in commands (Evennia's search accepts one only from builders), so it identifies the item to the client only. Whether payloads carry dbrefs is not decided. |
| `type` | str | Category: `"weapon"`, `"armor"`, `"item"`. |
| `worn` | bool | Present and `true` if the item is currently worn. Omitted if not worn. |

---

### Char.Items.Hands

Sent when wielded items change (wield, unwield, disarm).

**Payload**:

```json
{
  "left_hand": {"name": "Combat Knife", "dbref": "#145"},
  "right_hand": null
}
```

The payload is keyed by each grasping slot the body has now, as
`character.hands` returns it (for example `left_hand`, `right_hand`, or
the slot of a grasping augment such as a prehensile tail). Each key maps
to the held item, or `null` if the slot is empty. A severed hand has no
key.

Each hand item:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Item display name. |
| `dbref` | str | Item dbref. |

---

## Evennia Implementation Pattern

Each GMCP message is an outputfunc call on `msg()`: the kwarg name becomes
the GMCP package name, and `GmcpWebSocketClient.send_default` sends it as a
WebSocket TEXT frame. Nothing routes an `oob` kwarg.

> **Correction (2026-09-12):** no codec keys off an `oob` kwarg — the
> **outputfunc cmdname becomes the GMCP package name**.
>
> Evennia normalizes `msg()` kwargs in `evennia/server/sessionhandler.py`:
> because `is_iter("Room.Info")` is False and the payload is a dict,
> `msg(oob=("Room.Info", payload))` becomes `{"oob": [["Room.Info"],
> payload]}` — the payload is captured as cmd*kwargs*, not cmdargs — and
> `portalsessionhandler.py` then calls `send_default("oob", "Room.Info",
> **payload)`.
>
> There are two codecs, and they want **opposite** call shapes. Measured
> output for the same payload:
>
> | call | in-repo codec (live) | stock Evennia 6.1.0 codec |
> |------|----------------------|---------------------------|
> | `msg(oob=("Room.Info", payload))` | `oob "Room.Info"` (payload dropped) | `Core.Oob ["Room.Info", {…}]` |
> | `msg(**{"Room.Info": [[payload], {}]})` | **`Room.Info {…}`** ✅ | `Core.Room.Info {…}` ❌ |
> | `msg(room_info=payload)` | `room_info` (payload dropped) ❌ | **`Room.Info {…}`** ✅ |
>
> Gelatinous currently runs the **in-repo** codec
> (`GmcpWebSocketClient.send_default`, `server/conf/gmcp_websocket.py`), so
> the shape to use today is:
>
> ```python
> character.msg(**{"Room.Info": [[payload], {}]})
> ```
>
> Two caveats. (1) The tempting shorthands both fail the same way: a bare
> dict (`{"Room.Info": payload}`) or a bare list (`{"Room.Info": [payload]}`)
> routes the payload into cmdkwargs, and the in-repo `send_default` ignores
> `**kwargs` entirely — you get a package name with no payload. (2) This
> shape is **codec-specific**. The in-repo codec emits `cmdname` verbatim;
> stock Evennia's `gmcp_utils.encode_gmcp` maps `room_info` → `Room.Info`
> and prefixes any dotted-but-unmapped name with `Core.`. If the
> `WEBSOCKET_PROTOCOL_CLASS` override is ever dropped in favour of stock
> 6.1.0's native `gmcp.mudstandards.org` wire format, every call written to
> the shape above starts emitting `Core.Room.Info` and must be reworked to
> the `msg(room_info=payload)` idiom. Decide which codec Phase 1 targets
> before writing the first send.

### Sending a GMCP message

```python
# From any command or hook with access to the character
def send_room_info(character):
    """Send Room.Info GMCP to all sessions."""
    room = character.location
    if not room:
        return

    exits = {}
    for ex in room._visible_exits(character):
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

    character.msg(**{"Room.Info": [[payload], {}]})
```

> **Note (2026-09-12):** the final line is the call shape for the in-repo
> codec. Against stock Evennia 6.1.0's native codec it is
> `character.msg(room_info=payload)`. See the correction under "Evennia
> Implementation Pattern" for the trace and the comparison table.

### Hook points

| Package | Where to hook |
|---------|---------------|
| `Room.Info` | `Character.at_post_move()`, after the look text is sent; `Character.at_post_puppet()`, after its first look |
| `Char.Vitals` | After medical state mutations in `world/medical/` |
| `Char.Stats` | `Character.at_post_puppet()` and stat modification commands |
| `Char.Status` | `CombatHandler` state change methods, condition apply/remove |
| `Comm.Channel.Text` | Channel `.msg()` override or `at_post_channel_msg()` |
| `Comm.Channel.List` | `Character.at_post_puppet()` and channel join/leave |
| `Char.Items.Inv` | `Character.at_object_receive()` and `Character.at_object_leave()`, which fire for every item moved into or out of the inventory |
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

## Not decided

- Which codec the sends target: the in-repo `GmcpWebSocketClient` (call
  shape `msg(**{"Package.Name": [[payload], {}]})`) or stock Evennia's
  native `gmcp.mudstandards.org` wire format (`msg(room_info=payload)`).
  See "Evennia Implementation Pattern".
- Whether payloads may carry database ids (the room `num`, item dbrefs).
  The Design Philosophy keeps internal IDs server-side; the `Room.Info`,
  `Char.Items.Inv` and `Char.Items.Hands` payloads carry them.
- Where a room's `area` comes from: new `"area"` tags, or
  `world.wsis.zone_of`.

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
   function, assert that `msg()` received `{"Room.Info": [[payload], {}]}`
   (the outputfunc kwarg the send uses).

   > **Note (2026-09-12):** the kwarg shape is codec-specific (see
   > "Evennia Implementation Pattern"), so prefer the wire-format check
   > (item 4 below) as the real guarantee.
2. **Trigger points** -- Verify the GMCP message is sent at the correct
   game events (room entry, damage, channel message).
3. **Edge cases** -- Room with no exits, character with no medical state,
   empty inventory, null hand slots.
4. **Wire format** -- Connect a test WebSocket client, verify TEXT frames
   contain properly formatted `"Package.Name {json}"` strings.
