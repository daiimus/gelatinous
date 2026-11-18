# New-Player Experience Spec

The first thirty minutes of contact: connection screen → account →
character initialization → decant → first look. This spec records that
flow and the **messaging conventions** the owner locked in while polishing
it (2026-08-04, #1572–#1591). Anything touching chargen, death/respawn, or
system-to-player messaging should follow these rules.

---

## 1 · The flow

1. **Connection screen** (`server/conf/connection_screens.py`) — the
   test-pattern broadcast. `YEAR:` is derived from the clock at render
   time via `world.gametime.tst_now()`. Accounts are **email-keyed**;
   `create` does **not** auto-login — the player must `connect` after.
2. **Login routing** — `typeclasses/accounts.py::at_post_login` decides
   what happens next. It replaces Evennia's default outright;
   `AUTO_PUPPET_ON_LOGIN = False` (`server/conf/settings.py`) is what hands
   it the decision.
   - Zero live sleeves → chargen, or the respawn menu when
     `respawn_candidate()` returns one (#2615).
   - Zero sleeves with a menu already running in another session → a
     message instead of a restart, so a second tab cannot tear down a
     decant in progress (#2625).
   - Exactly one live sleeve → auto-puppet.
   - Two or more → the sleeve picker, scoped to the live ones (#2614).

   It also re-sends the non-puppeting preamble Evennia's default owns:
   saved protocol flags, the `logged_in` OOB message, and the
   connect-channel line (#2613).
3. **Character initialization** (`commands/charcreate.py`, EvMenu) —
   protocol-voiced nodes: a welcome screen, identity (first/last name,
   each 2-30 characters and at most 30 together, #3436), biological sex,
   height/build/hair (bald skips the style node), G.R.I.M. point
   distribution (300 points in all, each stat 1-150, each starting at 75),
   final confirmation. If the name is taken by the time the sleeve is
   created, the player goes back to the first-name prompt with the rest of
   their choices kept (#2550). Node furniture (underscore rules) comes from
   EvMenu's default `node_formatter`.
4. **Finalize** — the decant. Ordering is load-bearing; see §2.
5. **First look** — the spawn room (`START_LOCATION`, secret settings)
   arrives as the payoff of "you open your eyes", *outside* the framed
   protocol block.

### Respawn and the web door

Respawn (template sleeves / flash clone) and web-created characters share
the same conventions for the room-facing and data side; the player-facing
frame differs on the web door (§5). The flash-clone envelope doubles as a
morgue tag (§4).

- **Flash clone gate** (#3667, 2026-09-25). The flash clone is offered only
  when the body died (archived as a death, not shelved) and held its own
  sleeve policy; otherwise the respawn menu shows the refusal in its place.
  `create_flash_clone` asks the same question again before it builds the
  clone, and also refuses while the dead body's death progression is still
  running ("That sleeve is still on the table.").
- **Template sleeve** — comes as rolled: its sex is the one it was
  generated with, and the respawn menu does not ask for it
  (`respawn_confirm_template`, #3358).
- **Flash-clone option name** — names the sleeve the player will wake up
  as, numeral included (`flash_clone_name`, #3364).

## 2 · Finalize ordering — move BEFORE puppet

All three telnet finalize paths (first character, template respawn, flash
clone) do, in order:

1. `char.move_to(spawn, quiet=True)` — **before puppeting**. Pre-puppet
   the character has no session, so nothing renders; the player never sees
   the Limbo staging area (boilerplate desc, archived sleeves).
2. Send the framed decant block to the **account** (`caller.msg`).
3. `caller.puppet_object(...)` last — the puppet-look of the spawn room
   lands after the narrative (#1572).

**Abandonment:** the menu's `cmd_on_exit` callback disconnects only the
session that was actually running the abandoned menu, and only while that
session is still alive (`menu._session`). Kicking the account's *current*
session instead locks every reconnect out until a reload (#1574). Any
`cmd_on_exit` that disconnects must make the same check.

## 3 · Messaging conventions (owner-locked)

- **Standard frame.** Post-menu narrative blocks wear the menus' own
  furniture: a 66-underscore rule, the box banner, body, closing rule —
  sent as **one message** so blank lines survive intact and the block
  lands atomically. The room description always arrives *outside* the
  frame: the protocol ends, the world begins.
- **Terminal-informed wrap.** Prose paragraphs are **single unwrapped
  lines** — the client wraps to its own width, exactly like room
  descriptions. Never hand-wrap narrative at ~64 columns. Fixed layout is
  reserved for banners, rules, and label print.
- **TST dates, never real-world.** Every displayed year/date derives from
  `world/gametime.py` (Terran Standard Time = real year + 1200; e.g.
  `DECANTED: 04 AUG 3226`, `YEAR: 3226`). No hardcoded years — everything
  ticks with the clock. The functions differ by display: `YEAR:` on the
  connection screen reads `gametime.tst_now()`, while `DECANTED` reads
  `gametime.colony_now()` in all three telnet finalize nodes (#1581). Same
  TST calendar, but colony-local at a fixed UTC-8 (`COLONY_UTC_OFFSET` in
  `world/gametime.py`), so the two can name different dates for eight
  hours of every day.
- **Informing, not telling.** The world reports; the narrator does not
  assert. State arrives through labels, consoles, and readouts ("Memory
  integrity: PARTIAL", "a console ticks through your vitals and finds
  nothing to flag") — never "You are real." The envelope label is the
  canonical example: name, numeral, date, prior termination, death count
  — all fiction-legible facts, zero meta.
- **Branding.** The sleeve envelope is a **THAWN-HARRISON SINGLE-USE
  SLEEVE ENVELOPE** (`BIOSTATIC · FRAGILE · DO NOT CONSUME NUTRIGEL`).
  Imagery homages its inspirations; all print text and marks are ours
  (world rule: everything branded, nothing lifted). The respawn menu's
  banner (`respawn_welcome`) prints
  `VECTOR INDUSTRIES - MEDICAL RECONSTRUCTION DIVISION`, the only use of
  that brand (whether it is canon is not decided — see Not decided).

## 4 · The envelope as record

The yellow print does the informing:

```
    THAWN-HARRISON SINGLE-USE SLEEVE ENVELOPE
    CONTENTS: <NAME> <NUMERAL>
    MANIFEST: <RANK, DEPT — HULL>   (first character only)
    DECANTED: <DD MON YYYY, TST>
    PRIOR TERMINATION: <CAUSE>      (flash clone only)
    DEATH COUNT: <N>                (flash clone only)
    SLEEVE POLICY: <NONE ON FILE · POLICY TERMINAL IN LOBBY | ON FILE | STANDING>
    BIOSTATIC · FRAGILE · DO NOT CONSUME NUTRIGEL
```

- **`CONTENTS`** is the diegetic name reveal — the sleeve numbering
  fiction doing its own worldbuilding.
- **`MANIFEST`** (#2139, *Designation P1: the manifest*) is printed by
  `commands/charcreate.py::first_char_finalize` via `_manifest_stamp` →
  `world.manifest.designation_line`, e.g.
  `CHIEF, LIFE SYSTEMS — SBL-0117 HALCYON DAYS`, or `NO RECORD` for anyone
  the manifest never listed — "which is its own kind of record", as that
  function's docstring puts it. It is the purest case of the "informing,
  not telling" rule: a chart that never stood up, still knowing your
  berth. It prints on the **first-character** envelope only. All four
  creation doors *stamp* a designation with `ensure_manifest` (#3033): the
  telnet first character, both respawn doors
  (`create_character_from_template`, and `create_flash_clone`, which
  inherits it via `ensure_manifest(char, inherit_from=old_character)`), and
  the website (which stamps a designation but sends no envelope to print
  it). Neither respawn label prints it (`respawn_finalize_template`,
  `respawn_flash_clone`).
- **`DECANTED`** reads `gametime.colony_now()` (§3).
- **`PRIOR TERMINATION`** reads `old_char.db.death_cause`, which the death
  flow mirrors onto the character at corpse construction (#1582). If it is
  still empty when the body is archived, it is filled from the medical
  state's cause, or `unknown`; the envelope prints `UNKNOWN` when it is
  empty.
- **`SLEEVE POLICY`** (#3667, 2026-09-25; `world.insurance.envelope_line`)
  tells the player where they stand before it matters: every body starts
  uninsured and an uninsured death is permanent. The web door sends no
  envelope, so the same line is also read off a card in the pod lid at the
  first puppet (§5), which every creation door reaches.

## 5 · Puppet lifecycle messages

`typeclasses/characters.py` overrides both puppet hooks; **no stock
Evennia meta lines** ("You become X.", "X has entered/left the game.")
reach players. All room broadcasts go through
`world.identity_utils.msg_room_identity` (per-observer recognition;
capitalization only at genuine sentence starts, #1588).

| Event | Player sees | Room sees |
|-------|-------------|-----------|
| First puppet ever | framed decant block, then the room (telnet doors only today — see below), then "A card is taped inside the pod lid: SLEEVE POLICY: …" (every door, #3667); on the telnet first-character door, then "Type help for a list of commands." | the tech scene: pod cracked, envelope unzipped, body peeled from the nutrigel (one-shot `db.decant_announce_pending`, set at every creation point incl. web) |
| Later logins | the room | "{Actor} stirs as consciousness returns." |
| Logout | — | "{Actor} goes still, eyes emptying to static; the vacant sleeve is quietly gone." (stow-away behavior preserved: `prelogout_location`, body off-grid) |

A hidden character stays hidden across login and logout: the decant, stir
and logout lines reach only observers who can perceive them (#3037).
Logout also stands the body up and frees any seat before it leaves the
grid (#2579).

**The web door sends no framed block.** The table's row is left as
intent, not narrowed to telnet. The envelope exists in exactly
three places, all telnet EvMenu finalize nodes in `commands/charcreate.py`:
`respawn_finalize_template` (template respawn), `respawn_flash_clone`
(flash clone) and `first_char_finalize` (first character). Both web doors
end in a Django `messages.success(...)` and a redirect
(`web/website/views/characters.py`: both branches of
`CharacterCreateView.handle_respawn_submission`, and
`CharacterCreateView.form_valid`), and nothing replays the envelope at that
character's first puppet (`at_post_puppet` sends `at_look`, the room scene
and the pod-lid `SLEEVE POLICY` card — nothing else). So a web player's
first puppet is the room plus that one card, and a web-respawned player
never sees their own `PRIOR TERMINATION` or `DEATH COUNT` — the §4 morgue
tag, unread. This is held as an open gap for an owner call, not as correct
behavior: the last time this table and the web door disagreed, the code
was the defect and was fixed (#2449, which added
`decant_announce_pending` to the web path on the strength of this table's "set at every creation point incl. web"; its test file,
`world/tests/test_web_sleeves_are_not_second_class.py`, opens on "two doors
onto the same act, and only one of them carries the act's obligations").

The **room** column holds on every path: `decant_announce_pending` is set
at all four creation points (`create_character_from_template`,
`create_flash_clone` and `first_char_finalize` in
`commands/charcreate.py`, and `CharacterCreateView.form_valid` in
`web/website/views/characters.py`). The other known divergence on the web
door — hair is neither asked for nor set, leaving every web sleeve bald in
its sdesc — is recorded in
[`WEB_CHARACTER_CREATION_ALIGNMENT.md`](WEB_CHARACTER_CREATION_ALIGNMENT.md)
§Notes (2026-09-11, #2449).

The logout stow-away is slated to become in-world sleeping persistence
eventually — see
[`proposals/SLEEPING_SLEEVES_SPEC.md`](proposals/SLEEPING_SLEEVES_SPEC.md).

## 6 · Testing

End-to-end verification runs a raw-socket telnet probe **inside the game
container** (port 23; strip IAC negotiation; email-keyed accounts;
create-then-connect). Walk the full menu, capture every screen, assert on
the finale (no "Limbo", no stock meta lines, banner before room).
Throwaway accounts/characters are deleted afterward via the external
shell, followed by a reload so the server drops its cached copies
(idmapper): `@reload` from a logged-in developer character, asked for when
it is due (`AGENTS.md`, "Reload from inside the game"). The probe scripts
live in session scratch space, not the repo — they are ten lines of socket
code and this spec is their documentation.

## Not decided

All open on #3320 unless noted.

- **Respawn banner brand.** `respawn_welcome` prints
  `VECTOR INDUSTRIES - MEDICAL RECONSTRUCTION DIVISION`: is that canon, or
  should it read Thawn-Harrison?
- **`MANIFEST` on respawn labels.** Both respawn doors stamp a designation
  but neither label prints it: should the respawn labels print it?
- **Web envelope.** Should a web sleeve get the framed envelope at its
  first puppet, or does the "First puppet ever" row cover telnet only?
- **Web hair.** Web sleeves are neither asked for nor given hair; an open
  owner call recorded in
  [`WEB_CHARACTER_CREATION_ALIGNMENT.md`](WEB_CHARACTER_CREATION_ALIGNMENT.md)
  §Notes (2026-09-11, #2449), not on #3320.
- **Testing method.** Is the raw-socket telnet probe (§6) still the
  end-to-end method?

## Related

- [`WEB_CHARACTER_CREATION_ALIGNMENT.md`](WEB_CHARACTER_CREATION_ALIGNMENT.md)
  (web/telnet data parity)
- [`EVMENU_PATTERNS_SPEC.md`](EVMENU_PATTERNS_SPEC.md) (menu mechanics)
- [`TIME_SYSTEM_SPEC.md`](TIME_SYSTEM_SPEC.md) (the clock)
- [`IDENTITY_RECOGNITION_SPEC.md`](IDENTITY_RECOGNITION_SPEC.md)
  (per-observer rendering)
- [`proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`](proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md)
  (what happens at the other end)
- [`SLEEVE_INSURANCE_SPEC.md`](SLEEVE_INSURANCE_SPEC.md) (the
  `SLEEVE POLICY` line and the flash-clone gate)
- [`WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`](WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
  (the web respawn door)
- [`proposals/SLEEPING_SLEEVES_SPEC.md`](proposals/SLEEPING_SLEEVES_SPEC.md)
  (sleeping persistence for the logout stow-away)
