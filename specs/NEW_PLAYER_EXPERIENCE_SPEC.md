# New-Player Experience Spec

The first thirty minutes of contact: connection screen → account →
character initialization → decant → first look. This spec records the
**shipped** flow and, more importantly, the **messaging conventions**
the owner locked in while polishing it (2026-08-04, #1572–#1591).
Anything touching chargen, death/respawn, or system-to-player messaging
should follow these rules.

Related: [`WEB_CHARACTER_CREATION_ALIGNMENT.md`](WEB_CHARACTER_CREATION_ALIGNMENT.md)
(web/telnet data parity), [`EVMENU_PATTERNS_SPEC.md`](EVMENU_PATTERNS_SPEC.md)
(menu mechanics), [`TIME_SYSTEM_SPEC.md`](TIME_SYSTEM_SPEC.md) (the clock),
[`IDENTITY_RECOGNITION_SPEC.md`](IDENTITY_RECOGNITION_SPEC.md) (per-observer
rendering), and
[`proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`](proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md)
(what happens at the other end).

---

## 1 · The flow

1. **Connection screen** (`server/conf/connection_screens.py`) — the
   test-pattern broadcast. `YEAR:` is derived from the clock at render
   time via `world.gametime.tst_now()`. Accounts are **email-keyed**;
   `create` does **not** auto-login — the player must `connect` after.
2. **Character initialization** (`commands/charcreate.py`, EvMenu) —
   protocol-voiced nodes: identity (first/last name), biological sex,
   height/build/hair (bald skips the style node), G.R.I.M. point
   distribution, final confirmation. Node furniture (underscore rules)
   comes from EvMenu's default `node_formatter`.
3. **Finalize** — the decant. Ordering is load-bearing; see §2.
4. **First look** — the spawn room (`START_LOCATION`, secret settings)
   arrives as the payoff of "you open your eyes", *outside* the framed
   protocol block.

Respawn (template sleeves / flash clone) and web-created characters
share the same conventions; the flash-clone envelope doubles as a
morgue tag (§4).

## 2 · Finalize ordering — move BEFORE puppet

All three telnet finalize paths (first character, template respawn,
flash clone) do, in order:

1. `char.move_to(spawn, quiet=True)` — **before puppeting**. Pre-puppet
   the character has no session, so nothing renders; the player never
   sees the Limbo staging area (boilerplate desc, archived sleeves).
2. Send the framed decant block to the **account** (`caller.msg`).
3. `caller.puppet_object(...)` last — the puppet-look of the spawn room
   lands after the narrative (#1572).

**Abandonment:** the menu's `cmd_on_exit` callback disconnects only the
session that was actually running the abandoned menu, and only while
that session is still alive (`menu._session`). Kicking the account's
*current* session locks every reconnect out until a reload — that bug
shipped and was fixed as #1574. Any future `cmd_on_exit` that
disconnects must make the same check.

## 3 · Messaging conventions (owner-locked)

- **Standard frame.** Post-menu narrative blocks wear the menus' own
  furniture: a 66-underscore rule, the box banner, body, closing rule —
  sent as **one message** so blank lines survive intact and the block
  lands atomically. The room description always arrives *outside* the
  frame: the protocol ends, the world begins.
- **Terminal-informed wrap.** Prose paragraphs are **single unwrapped
  lines** — the client wraps to its own width, exactly like room
  descriptions. Never hand-wrap narrative at ~64 columns. Fixed layout
  is reserved for banners, rules, and label print.
- **TST dates, never real-world.** Every displayed year/date derives
  from `world/gametime.py` (Terran Standard Time = real year + 1200;
  e.g. `DECANTED: 04 AUG 3226`, `YEAR: 3226`). No hardcoded years —
  everything ticks with the clock.
- **Informing, not telling.** The world reports; the narrator does not
  assert. State arrives through labels, consoles, and readouts
  ("Memory integrity: PARTIAL", "a console ticks through your vitals
  and finds nothing to flag") — never "You are real." The envelope
  label is the canonical example: name, numeral, date, prior
  termination, death count — all fiction-legible facts, zero meta.
- **Branding.** The sleeve envelope is a **THAWN-HARRISON SINGLE-USE
  SLEEVE ENVELOPE** (`BIOSTATIC · FRAGILE · DO NOT CONSUME NUTRIGEL`).
  Imagery homages its inspirations; all print text and marks are ours
  (world rule: everything branded, nothing lifted).

## 4 · The envelope as record

The yellow print does the informing:

```
    THAWN-HARRISON SINGLE-USE SLEEVE ENVELOPE
    CONTENTS: <NAME> <NUMERAL>
    DECANTED: <DD MON YYYY, TST>
    PRIOR TERMINATION: <CAUSE>      (flash clone only)
    DEATH COUNT: <N>                (flash clone only)
    BIOSTATIC · FRAGILE · DO NOT CONSUME NUTRIGEL
```

`CONTENTS` is the diegetic name reveal — the sleeve numbering fiction
doing its own worldbuilding. `PRIOR TERMINATION` reads
`old_char.db.death_cause`, which the death flow mirrors onto the
character at corpse construction (#1582).

## 5 · Puppet lifecycle messages

`typeclasses/characters.py` overrides both puppet hooks; **no stock
Evennia meta lines** ("You become X.", "X has entered/left the game.")
reach players. All room broadcasts go through
`world.identity_utils.msg_room_identity` (per-observer recognition;
capitalization only at genuine sentence starts, #1588).

| Event | Player sees | Room sees |
|-------|-------------|-----------|
| First puppet ever | framed decant block, then the room | the tech scene: pod cracked, envelope unzipped, body peeled from the nutrigel (one-shot `db.decant_announce_pending`, set at every creation point incl. web) |
| Later logins | the room | "{Actor} stirs as consciousness returns." |
| Logout | — | "{Actor} goes still, eyes emptying to static; the vacant sleeve is quietly gone." (stow-away behavior preserved: `prelogout_location`, body off-grid) |

The logout stow-away is slated to become in-world sleeping persistence
eventually — see
[`proposals/SLEEPING_SLEEVES_SPEC.md`](proposals/SLEEPING_SLEEVES_SPEC.md).

## 6 · Testing

End-to-end verification runs a raw-socket telnet probe **inside the
game container** (port 23; strip IAC negotiation; email-keyed accounts;
create-then-connect). Walk the full menu, capture every screen, assert
on the finale (no "Limbo", no stock meta lines, banner before room).
Throwaway accounts/characters are deleted afterward via the external
shell **followed by a foreground reload** (idmapper). The probe scripts
live in session scratch space, not the repo — they are ten lines of
socket code and this spec is their documentation.
