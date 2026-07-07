# Channeled Actions Spec — timed, interruptible acts

> **Status:** 📋 **PROPOSAL (2026-07-06) — design only.** The game's first
> generic **timed-act primitive**: an action that occupies its actor for a
> real duration, shows a visible tell, and resolves to a full result on
> completion or a **partial result on interruption**. First consumer:
> **graffiti tagging** (duration proportional to letters — the anti-spam
> that is also the fiction). The crux of the design is the **interrupt
> taxonomy** (§2): what a channeling character can still do freely, what is
> blocked, and what breaks the channel. Queue behind the primitive: solvent
> cleaning, forced-entry/lockpick-analogues, repairs, future ritualized
> acts.

---

## 0 · Why a primitive, not a graffiti patch

Nothing in the game currently models "you are busy doing X for N seconds."
Every act is instantaneous (spray, clean) or runs on its own bespoke
machinery (combat rounds, medical script, death progression). The moment we
give tagging a per-letter timer we are building the general thing — so build
it once, small, and let consumers share the interrupt rules instead of each
inventing their own. A player who learns "being attacked ruins careful work"
learns it for every channeled act in the game.

## 1 · The model

One channel per character, ndb-backed (a reload silently kills the act —
nothing lands, nothing is spent; see §1.2):

```
begin_channel(actor,
    duration,        # seconds, computed by the consumer (letters × rate)
    tell,            # placement line while channeling ("crouched at the
                     #  wall, spray can hissing")
    on_complete,     # full result (the tag lands, paint deducts)
    on_interrupt,    # partial result, receives elapsed fraction
    key)             # what the actor is doing, for messages ("spraying")
```

* **Visible from the first second:** the tell rides the existing placement
  system (`look_place`/`override_place`), so anyone glancing at the room
  sees the act in progress — channels are inherently *public* time.
* **One at a time:** starting a channel while one runs is refused ("you're
  busy spraying — stop first").
* **Progress is linear:** `on_interrupt` receives `elapsed / duration`; the
  consumer decides what a fraction means (graffiti: letters completed).

### 1.1 · Resolution

* **Completion** → `on_complete` fires, tell clears, costs deduct in full.
* **Interruption** (voluntary or breaking event, §2) → `on_interrupt(frac)`
  fires: partial result, pro-rata cost, tell clears. The partial is *real* —
  a half-tag on the wall is forensic evidence of an interrupted act.
* **Reload** → ndb clears; the act evaporates: no result, no cost. Rare and
  acceptable; deduct-at-resolution makes it lossless for the actor.

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
* `say` / `whisper` / `to` / `emote` / `pose` / `think` — communication is
  hands-free (garbled/deaf gating unaffected)
* Being looked at, spoken to, radio *reception* — passive receipt
* Inventory inspection (`i`), checking your own state

### 2.2 · BLOCKED — refused while channeling ("stop first")

Acts that need the hands or would begin a second activity. Refused with a
clear message, never a silent cancel — no accidental loss of 80 seconds of
work because of a mistyped verb:

* Movement (any exit traversal, jump, climb) — the spec-of-record line:
  channels prevent movement; leaving requires an explicit stop
* `wield`/`unwield`, `get`/`drop`/`give`, wear/remove, style verbs
* Starting an attack, aiming, throwing
* `xmit`/`tune`/`toggle` (device work is hands-work)
* Starting another channel, using a kiosk, trading

Voluntary exit: **`stop`** (the existing stop-verb family) aborts the
channel deliberately → `on_interrupt` with the current fraction. You keep
what you finished.

### 2.3 · BREAKING — involuntary, ends the channel with a partial

The world doesn't ask permission. Each of these fires `on_interrupt`
immediately:

| Event | Hook seam |
|---|---|
| **Taking damage** (attacked, shot from afar, caught in a blast) | damage application path |
| **Being grappled / shoved / grapple-dragged** | grapple establish / movement resolution |
| **Being enrolled in combat** (even before the first hit lands) | combat handler `add_combatant` |
| **Falling unconscious / dying** (bleed-out mid-act) | medical unconscious/death hooks |
| **The tool leaving your hands** (disarm, `wrest` the spray can away) | disarm/wrest resolution |
| **Forced movement** (dragged, thrown, gravity/fall) | movement-resolution seams |

Explicitly **not** breaking: noise, room messages, someone looking at you,
weather, crowd jostle prose, receiving speech or radio traffic. Fiction may
say the street is chaos; only *contact* breaks concentration.

## 3 · First consumer — graffiti tagging (per-letter timer)

* `spray <message>` computes `duration = SETUP + len(message) × RATE`
  (defaults: `SETUP = 3s` — the can-rattle, whose atmospheric messaging
  already exists — and `RATE = 1s/char`, both constants).
* Tell: *"crouched at the wall, spray can hissing."*
* **Completion:** the full tag lands (existing `GraffitiObject` flow), paint
  deducts 1/char, atmospherics fire as today.
* **Interruption at fraction f:** `floor(f × len)` letters land **with the
  ellipsis truncation the paint-out path already renders** — an interrupted
  `KRAK…` is evidence — and only those letters' paint deducts.
* **Vandalism becomes committable:** completion *or* interruption files
  `report_crime("vandalism", room, perp=tagger)` — the severity table has
  carried `"vandalism": 1` since the crime slice with no caller. The
  duration is what makes the crowd-gated witness *fair*: a 10-char throw-up
  is ~13s of exposure; a 100-char manifesto is ~103s, well past the 40s
  witness window. Length is risk; that's the fiction working.
* Solvent **cleaning** channels identically (per character removed) in the
  same slice or the one after.

## 4 · Future consumers (design against, don't build)

Forced-entry/biometric-spoof attempts (verticality §2.4), repairs,
device/salvage work, the moving lift ride, any future ritual or craft act.
Each brings only: a duration formula, a tell, and the two callbacks.

## 5 · Open questions

1. **Combat-round interplay** — a channel inside an active combat room but
   not enrolled: allowed (you can tag beside a brawl) until the brawl
   *touches* you (§2.3). Confirm.
2. **`stop` grammar** — bare `stop` aborts the current channel vs. named
   (`stop spraying`). Proposal: bare `stop` with no channel falls through
   to existing stop-verbs; with one, aborts it.
3. **Rates as balance levers** — 3s + 1s/char shipped as constants; tune in
   play.
