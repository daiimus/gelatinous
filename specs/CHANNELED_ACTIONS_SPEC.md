# Channeled Actions Spec — timed, interruptible acts

A channeled act is the game's generic **timed-act primitive**
(`world/channeled.py`): an action that occupies its actor for a real
duration, shows a visible tell, and resolves to a full result on completion
or a **partial result on interruption**. The crux of the design is the
**interrupt taxonomy** (§2): what a channeling character can still do
freely, what is blocked, and what breaks the channel.

Consumers:

* **Graffiti tagging** (§3): duration proportional to letters, the anti-spam
  that is also the fiction.
* **Solvent cleaning** (§3.1).
* **Breach** (#1164, `commands/CmdBreach.py`): `sabotage` (90s) and the
  structure branch of `repair` (180s) on `db.breachable` masts.
* **Surgery** (#2926, owner ruling 2026-09-06): `start_procedure`
  (`world/medical/procedures.py`) opens the channel, and the channel IS the
  procedure timer, so an operation inherits the whole taxonomy without new
  interruption logic. Exception: when the surgeon is already channeling,
  `begin_channel` refuses, and that procedure runs on a plain timer instead
  (the pre-#2926 one), so the channel taxonomy does not apply to it.

Wrest and disarm are not consumers. They are a §2.3 BREAKING row, met by the
tool rule (#3376): wrest/disarm had been queued as the next consumer, and the
tool rule replaced that.

---

## 0 · Why a primitive, not a graffiti patch

Acts that are not channeled are instantaneous, or run on their own bespoke
machinery (combat rounds, medical script, death progression). A per-letter
timer for tagging is the general thing, so it is built once, small, and
consumers share the interrupt rules instead of each inventing their own. A
player who learns "being attacked ruins careful work" learns it for every
channeled act in the game.

## 1 · The model

One channel per character, ndb-backed (a reload silently kills the act:
nothing lands, nothing is spent; see §1.1).

`begin_channel` takes:

* `duration`: seconds, computed by the consumer (graffiti: letters × rate);
* `tell`: the placement line while channeling ("crouched at the wall, spray
  can hissing");
* `on_complete`: the full result (the tag lands, paint deducts);
* `on_interrupt`: the partial result; receives the elapsed fraction;
* `key`: what the actor is doing, for messages ("spraying");
* `tools`: objects the act needs on the actor; one leaving breaks the act
  (§2.3).

* **Visible from the first second:** the tell rides the existing placement
  system (`look_place`/`override_place`), so anyone glancing at the room
  sees the act in progress. Channels are inherently *public* time.
* **One at a time:** starting a channel while one runs is refused: "You're
  busy spraying — 'stop' first."
* **Progress is linear:** `on_interrupt` receives `elapsed / duration`; the
  consumer decides what a fraction means (graffiti: letters completed).

### 1.1 · Resolution

* **Completion** → `on_complete` fires, tell clears, costs deduct in full.
* **Interruption** (voluntary or breaking event, §2) → `on_interrupt(frac)`
  fires: partial result, pro-rata cost, tell clears. The partial is *real*:
  a half-tag on the wall is forensic evidence of an interrupted act.
* **Reload** → ndb clears; the act evaporates: no result, no cost. Rare and
  acceptable; deduct-at-resolution makes it lossless for the actor.
  The tell is a persistent placement line and would outlive the reload, so
  `begin_channel` also writes a persistent `channel_strand` attribute, and
  `sweep_stranded_tells` (run from `at_server_start`) puts back the earlier
  placement line wherever the tell is still the line showing (#2774).

### 1.2 · Deliberate non-goals

No progress bars, no queued actions, no multi-channel, no channel while
moving. This is a *stillness* primitive: you are somewhere, doing a thing,
for a time, visibly.

## 2 · The interrupt taxonomy — the crux

Three classes. The test for each command/event is: *does it require the
actor's hands or full attention, or is it something a person mid-task
plainly does?*

### 2.1 · FREE — never touches the channel

Perception and speech: a tagger can absolutely talk over their shoulder.

* `look`, glance, reading, examining, all pure perception
* `say` / `whisper` / `to <person>` / `emote` / `pose` / `think`:
  communication is hands-free (garbled/deaf gating unaffected); `to <radio>`
  is device work and is BLOCKED (§2.2)
* Being looked at, spoken to, radio *reception*: passive receipt
* Inventory inspection (`i`), checking your own state

### 2.2 · BLOCKED — refused while channeling ("stop first")

Acts that need the hands or would begin a second activity. Refused with a
clear message, never a silent cancel: no accidental loss of 80 seconds of
work because of a mistyped verb. Each blocked command calls
`refuse_if_channeling` first.

* Movement (any exit traversal, jump, climb): channels prevent movement;
  leaving requires an explicit stop. The refusal is in
  `Character.at_pre_move`.
  * `flee` (`commands/combat/movement.py`) and both kinds of `jump` (off an
    edge and across a gap, `commands/combat/jump.py`) ask
    `refuse_if_channeling` themselves, before paying the price of leaving a
    fight, rather than letting `at_pre_move` refuse the move after the aim
    contest and the disengage roll have been charged (#3685, #3687).
* `wield` (`commands/CmdInventory.py`)/`unwield`, `get`/`drop`/`give`,
  `put`, wear/remove, style verbs
* `slot`/`unslot` (plates move through the hands by the #3463 ruling).
  `get`/`put` and `unslot`/`slot` are the same doors and carry the same
  guard (#3619, #3635).
* Starting an attack (`attack`, `commands/combat/core_actions.py`), aiming (`aim`), throwing (`throw`)
* `xmit`/`tune`/`toggle` (`commands/CmdRadio.py`; device work is
  hands-work), and the radio branch of `to` (`commands/CmdCommunication.py`)
* Starting another channel (the refusal inside `begin_channel`), using a
  kiosk or button (`press`), trading (`buy`)

**Ruled 2026-09-13 (#3376, option A -- finish the list):** every verb in the
list above refuses while channeling. And the tool problem is solved in the
PRIMITIVE, not per consumer: `begin_channel(..., tools=[...])` declares the
objects an act needs on the actor (see the tool row in §2.3). Graffiti,
solvent and surgery declare their tools; future consumers just pass theirs.

Voluntary exit: **`stop`** (the existing stop-verb family, `commands/combat/core_actions.py`)
aborts the channel deliberately → `on_interrupt` with the current fraction.
Bare `stop`, or `stop <act>` naming the act's key (`stop spraying`), aborts
it; `stop_channel` does the work. You keep what you finished.

### 2.3 · BREAKING — involuntary, ends the channel with a partial

The world doesn't ask permission. Each of these fires `on_interrupt`
immediately (`interrupt_channel`):

| Event | Hook seam |
|---|---|
| **Taking damage** (attacked, shot from afar, caught in a blast) | `take_damage` |
| **Being grappled / shoved / grapple-dragged** | grapple establish / movement resolution |
| **Being enrolled in combat** (even before the first hit lands) | combat handler `add_combatant` |
| **Falling unconscious / dying** (bleed-out mid-act) | medical unconscious/death hooks |
| **The tool leaving your hands** (disarm, `wrest` the spray can away) | `tool_left_hands`, from `Character.release_slots` and `at_object_leave` |
| **Forced movement** (dragged, thrown, gravity/fall) | movement-resolution seams: `at_post_move`; for the hookless door drags, by hand in `drag_victim_to` (#2774, #3663); for falls, `world/gravity.py` breaks the act before the step (`at_pre_move` would refuse it) |

**The tool row.** `tool_left_hands` breaks the channel the moment a declared
tool leaves the actor by ANY route: drop, give, wrest, disarm, theft
(#3376, #3377, #3385). `resolve_disarm` (`world/combat/actions.py`) and
`CmdWrest` (`commands/CmdInventory.py`) move the item with hooks on, so
neither calls `interrupt_channel` itself. `_finish` re-validates as
belt-and-braces: a tool that left by a move with `move_hooks=False` (whose
caller did not call `release_slots`) slips past `tool_left_hands`, and
`_finish` then lands the act as interrupted at fraction 1.0, never as
complete.

**The unconscious/dying row is the actor** (owner ruling 2026-09-13,
#3368). A **patient** dying under the surgeon's hands does NOT break the
surgeon's channel. A procedure is a commitment with expected flatlines
(heart/brain transplants pass through death into the 90-second revival
window; for the brain, through `brain_integrity`, #3248); the surgeon keeps
working, the room sees the death, and `stop` is the exit if things turn.
`at_death` still clears the procedure record on the body (#2926) so nothing
resolves on a corpse; the surgeon's own channel runs out on its own.

**A patient dragged away** by a grappler (through a door, by `advance`, or
off an edge) is different: `break_victim_acts`
(`world/combat/grappling.py`) calls `take_patient_away`
(`world/medical/procedures.py`, #3669), which ends the procedure on them and
breaks the surgeon's channel if that channel is timing this procedure. A
surgeon channeling something unrelated keeps it. The surgeon is told, and so
are the patient and the room when the surgeon was with them (#3681).

Explicitly **not** breaking: noise, room messages, someone looking at you,
weather, crowd jostle prose, receiving speech or radio traffic. Fiction may
say the street is chaos; only *contact* breaks concentration.

## 3 · First consumer — graffiti tagging (per-letter timer)

* `spray <message>` computes `duration = SETUP + len(message) × RATE`
  (defaults: `SETUP = 3s`, the can-rattle, whose atmospheric messaging
  already exists, and `RATE = 1s/char`, both
  constants).
* Tell: *"crouched at the wall, spray can hissing."*
* **Completion:** the full tag lands (`GraffitiObject` flow), paint deducts
  1/char, atmospherics fire.
* **Interruption:** each full second of work after the 3-second setup lands
  one letter (`(elapsed − SETUP) ÷ RATE`, rounded down), **with the `...`
  truncation the paint-out path renders** (an interrupted `KRAK...` is
  evidence), and only those letters' paint deducts. Breaking off during the
  setup lands nothing and costs nothing: "You break off before the nozzle
  ever touches the wall."
* **Vandalism is committable:** any tag that lands, whole or partial, files
  `report_crime("vandalism", room, perp=tagger)` (in `_land_tag`); an
  interruption before the first letter files nothing. The severity table
  weighs `"vandalism": 1`. The duration is what makes the crowd-gated
  witness *fair*: a 10-char throw-up is ~13s of exposure; a 100-char
  manifesto is ~103s, well past the 40s witness window. Length is risk;
  that's the fiction working.

### 3.1 · Solvent cleaning

Solvent **cleaning** is a channel too (`_handle_clean_with_solvent`): 3 s
setup plus 1 s per solvent unit, at most 10 units (13 s) per scrub. Each
unit worked removes one random graffiti character; an interruption counts
only the full seconds worked after the setup, so graffiti scrubs pro-rata.
**Blood breaks down only on completion**: the solvent needs dwell time, so
bailing mid-scrub leaves the evidence.

## 4 · Unbuilt — future consumers (design against, don't build)

📋 UNBUILT (no issue): forced-entry/biometric-spoof attempts (verticality
§2.4) and other lockpick-analogues, repairs, device/salvage work, the moving
lift ride, any future ritual or craft act. Each brings only: a duration
formula, a tell, and the two callbacks.

## 5 · Not decided

1. **Combat-round interplay** — a channel inside an active combat room but
   not enrolled: allowed (you can tag beside a brawl) until the brawl
   *touches* you (§2.3). Confirm.
2. **`stop` grammar** — bare `stop` aborts the current channel vs. named
   (`stop spraying`). Proposal: bare `stop` with no channel falls through
   to existing stop-verbs; with one, aborts it.
3. **Rates as balance levers** — 3s + 1s/char are constants; tune in play.
