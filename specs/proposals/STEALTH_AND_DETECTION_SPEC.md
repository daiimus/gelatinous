# Stealth & Detection Spec — Hiding, Searching, and Graded Awareness

> **Status:** 🚧 **PHASES 1–2 + PASSIVE TIER + DISPLAY INTEGRATION SHIPPED
> (2026-07-03).** Live: `world/stealth.py` (opposed Motorics-hider vs
> Resonance-searcher contest; per-observer graded awareness store keyed on
> apparent-uid, lazy decay), `hide`/`unhide`/`sneak`/`search` commands, the
> **passive tier** (§3.4), display integration (room roster filters
> Unaware/Suspicious; the *Suspicious* "prickling sense" cue; the "lurking
> in the shadows" placement for the Detected; hidden objects out of the
> things list; hidden movers' announcements suppressed to the unaware), and
> break-on-action (speech, attack, open movement). NOT yet built: the full
> perception-gate choke (§7 — say/emote/combat-target leak sweep; note the
> phase layer's `filter_present` does NOT exist yet, §7 must build it), the
> NPC hunt (§5), ambush advantage (§6.1), theft (§6.2), environmental
> modifiers (light/cover/crowd — v1 is the flat tier spread).
> Original abstract: designs the **presence-concealment**
> layer: `hide` (self or object) vs `search` (a room), resolved as an opposed
> **Resonance/Motorics** contest, surfaced as a **per-observer graded awareness
> meter** (unaware → suspicious → searching → alert) that drives **deterministic
> (non-LLM) NPC behaviour** — the headline feature. The PC and NPC detection
> loops are **theoretically identical**. Built on the unified perception gate
> from `PHASE_LAYER_SPEC`; consumes `SPATIAL_COORDINATE_SYSTEM_SPEC` (line-of-
> sight, last-known position, search pathing) and feeds
> `NPC_DISPATCH_AND_SIMULATION_SPEC` (the hunt).

---

## 1 · Intent & the core loop

Make the world's eyes *contestable*. A character can **hide** — themselves, or an
object — and another can **search** to find them. The outcome isn't a binary
flag flip; it's a **graded, per-observer awareness** that, for NPCs, drives a
deterministic MGS/Hitman/Thief-style response cycle: a guard grows *suspicious*,
*searches* your last-known position, *alerts* allies, and eventually *gives up*
and returns to routine — all without the LLM. That deterministic awareness loop
is the noteworthy, MUD-rare payoff.

**Core loop:** `hide` (self / object) ↔ `search` (room) → an opposed
Resonance/Motorics contest → updates the searcher's **awareness** of the target.

---

## 2 · The big picture — stealth is the graded sibling of phase

`PHASE_LAYER_SPEC` built the unified perception gate (`co_present` /
`can_perceive` / `filter_present` in `world/perception.py`). Stealth lives in the
same gate, as its **graded** counterpart:

| | Phase | Stealth |
|---|---|---|
| Question | "are you in my reality?" | "you're in my reality — do I *notice* you?" |
| Shape | **binary** membership | **graded**, per-observer awareness |
| On "no" | you don't exist to me — **no AoE, no sound, no consequence** | I don't passively notice you — **but AoE, sound, and search still reach you** |

This is the precise distinction: **phase removes you from consequence; stealth
removes you only from passive notice.** A hidden character is still
`co_present` — a grenade, a shout, or a `search` finds them. So stealth is a
*new clause* inside `can_perceive`, not a second gate, and it reuses the
single-choke-point discipline (`filter_present`) that makes the gate safe.

### 2.1 · Where stealth sits among the concealment axes

The game has four ways to be unseen; this spec owns one:

| Axis | "Hide your…" | Home |
|---|---|---|
| Identity | who you are | `IDENTITY_RECOGNITION_SPEC` (built) |
| Reality | which plane | `PHASE_LAYER_SPEC` (specced) |
| **Presence** | **whether you're noticed** | **this spec** |
| Threat / carry | that you're armed | **organic** — wielding + sdesc + weapon-priority (§9) |

---

## 3 · The detection contest

### 3.1 · The opposed roll

Detection is an **opposed Resonance/Motorics** check between hider and searcher.
*(Stat-direction to confirm and expand later: working assumption — the **hider**
leans **Motorics** (quiet movement, stillness, physical craft of concealment) and
the **searcher** leans **Resonance** (perceptive awareness, the sense that
someone's there). The pairing is fixed; the direction and any blend are the
"expand later" detail.)* The contest is **symmetric**: a PC hiding from an NPC
and an NPC hiding from a PC run the identical math.

### 3.2 · Environmental modifiers

The roll is heavily shaped by situation — which is where the parked-stats design
keeps stealth *gear- and world-driven* rather than stat-driven:

* **Light / shadow** — darkness favours the hider (gated by the searcher's
  sight / blindsight via `world/perception.py`).
* **Cover & line-of-sight** — coordinate-aware (`SPATIAL_COORDINATE_SYSTEM_SPEC`):
  a wall/`barrier` face or an occluding object breaks LoS and favours hiding.
* **Crowd** — density (the existing crowd system) is concealment for *blending*,
  noise for *searching*.
* **Noise & movement** — staying still beats sneaking beats running; loud actions
  (combat, shouting) spike detectability.
* **Distance** — coordinate distance bands degrade passive detection.

### 3.3 · What you can hide, and the commands

* **Self (static)** — `hide` / `unhide` toggles the hidden state in the current
  room (best in cover / shadow / crowd).
* **Self (moving)** — `sneak <direction>` is "move while hiding": it carries you
  through an exit and **induces the hidden state** on arrival (a fresh contest in
  the new room). Sneaking is the in-motion form of `hide`; the same toggle state,
  re-rolled per room, with the movement penalty from §3.2.
* **Object** — `hide <object>` stashes an item in the room; `search` may turn it
  up. (Stashed contraband, a planted bug, a dropped weapon.)

`search` is the active counter: it spends an action to roll against everything
hidden in the room, raising the searcher's awareness on success.

### 3.4 · The passive tier (2026-07-03, user-decided)

Between "never noticed" and "actively searched" sits the free glance:
**entering a room and looking around each run a passive check** against
hidden things — weaker than `search` (the active bonus is withheld) and
**rate-limited per observer→target** (repeat looks reuse the standing
result until a cooldown passes or the hider re-rolls), so look-spam never
equals searching. A clear win spots the hider outright (Detected); a near
miss yields *Suspicious* ("you get the prickling sense that you are not
alone here"). The point: someone perceptive vs someone terrible at hiding
will spot them **inherently**, no action spent.

---

## 4 · Per-observer graded awareness (the headline)

Awareness is **per (observer → target)**, mirroring how `recognition_memory` is
per-observer (`IDENTITY_RECOGNITION_SPEC`). Each observer holds an awareness
level toward each hidden thing:

| Level | Meaning | Passive perception of the target |
|---|---|---|
| **0 · Unaware** | no idea they're there | **filtered out** — not in "who's here", not targetable |
| **1 · Suspicious** | "something's off" | knows *a* presence, not who/where precisely |
| **2 · Searching** | actively hunting | investigating last-known area |
| **3 · Alert / Detected** | fully made | **filtered back in** — stealth broken for this observer |

The level **modulates what `can_perceive` returns for that observer** — this is
the graded gate in action. Levels rise on failed-hide / successful-search /
noise events and **decay over time** when contact is lost (the give-up arc).

**The "lurking" tell.** When a hidden character *is* perceived — a *Detected*
observer, or a failed hide roll where the watcher still sees them — they do **not**
render normally. The stealth state contributes a placement at the top of the
existing hierarchy (`override_place` > `temp_place` > `look_place` > "standing
here." in `get_display_characters`), so to those who see them they read as
**"lurking in the shadows"** rather than "standing here." Failed concealment
doesn't restore a normal appearance; it makes you *visibly furtive* — onlookers
can tell this is someone who doesn't want to be seen. (At *Suspicious* the
watcher gets only the "you sense something" cue, no placement; the lurking
placement appears at *Detected*.)

**Identical loop, two consumers.** The same per-observer awareness data is:
* **rendered to a PC** ("you sense something nearby…" at *Suspicious*; the target
  appears at *Alert*), and
* **read by a deterministic NPC** as the input to its behaviour state machine
  (§5).

That symmetry — one mechanic, a human reads it as tension, an AI reads it as a
state transition — is the design's point.

---

## 5 · NPC hunt behaviour (deterministic, MGS/Hitman/Thief)

The awareness meter drives a hardcoded NPC state machine — **no LLM** — wired
into `NPC_DISPATCH_AND_SIMULATION_SPEC`:

```
Unaware ──(detect)──▶ Suspicious ──(confirm)──▶ Searching ──(reacquire)──▶ Alert
   ▲                      │                          │                       │
   └──(decay/give up)─────┴───────(timeout)──────────┘                  (engage)
```

* **Suspicious** — break routine, orient toward the stimulus (a noise's bearing,
  a glimpsed coordinate).
* **Searching** — the hunt: move toward **last-known position** (stored on the
  awareness record), run a **Dijkstra search pattern** over nearby rooms (coord +
  pathfinder), and **alert allies** by raising a dispatch event so other NPCs
  escalate too (alert propagation).
* **Alert** — reacquired → engage (combat / challenge), via real commands.
* **Give up** — search times out with no reacquire → awareness **decays** back
  down to Unaware and the NPC returns to routine. The cooldown is the
  Hitman/Thief "they lost me" beat.

The LLM may *optionally* be handed an Alert beat for flavour (budget permitting,
per the dispatch escalation gate) — but the **awareness and the hunt are fully
deterministic**, which is exactly why this scales without LLM cost.

---

## 6 · Applied contest — ambush, theft, breaking stealth

### 6.1 · Ambush

Acting on a target at **Unaware** toward you is an ambush: a first-strike
advantage routed through the existing aim/initiative systems (`world/combat`),
not a new combat path.

### 6.2 · Theft (steal & pickpocket)

**Theft is applied stealth** — a nonconsensual Resonance/Motorics contest whose
risk is *getting caught*. It is the contest engine (§3) and the awareness meter
(§4) pointed at taking things, not a separate system.

* **`steal <item> from <target>`** — take a *specific, perceivable* item (a
  visible worn/carried object). Contest: thief vs the victim's awareness, modified
  by §3.2 (crowd/distraction help; a prominent or worn item is harder than a loose
  one; a victim in active combat is distracted). **Success** → the item transfers
  with little awareness gained. **Failure** → *caught*: the victim (and witnesses
  in LoS) jump toward **Alert** toward the thief, recognition keys on the thief's
  **apparent-UID** (a mask/disguise protects you — `IDENTITY_RECOGNITION_SPEC`),
  and a witnessed theft can raise a **dispatch** event (the victim swings, a guard
  responds).
* **`pickpocket <target>`** — **tokens (currency) only**: a blind grab for cash,
  lower-stakes and more deniable than targeted theft (you don't choose *what*, you
  lift *some*). Same contest and caught-consequences, tuned lighter. Specific
  items are the riskier `steal`.
* **Subdued / unconscious / dead target** → **free action** (it's just looting),
  via the `TRUST_AND_CONSENT_SPEC` predicate. The contest only matters for an
  awake target who could notice — which is the whole skill.
* **Concealed items** can't be `steal`-targeted until revealed: you take what you
  can perceive (sdesc-visible) or what a `frisk` (§6.3) has surfaced. Frisk-then-
  steal on a subdued mark is the mugging loop.
* **Proximity** required (same room, close/adjacent) — theft rides the combat
  proximity substrate.

### 6.3 · Frisk (the consent-gated reveal)

`frisk <target>` **identifies the items on a person — worn, carried, and
concealed** (the holdout the sdesc hides). It is **not** a contest: it is the
`search`/`frisk` action class in `TRUST_AND_CONSENT_SPEC`, so it **requires
consent, or a target who is unconscious / restrained / dead** (the free-action
path). Frisk is the active counter to organic concealment (§9) and the
information step before confiscation or `steal`. *(Effect defined here; gating
owned by the trust spec.)*

### 6.4 · Breaking stealth

Attacking, loud actions, a failed theft, or being searched-and-found pushes the
relevant observers to **Alert** and drops your hidden state for them. Stealth
breaks **per-observer**: ambushing or robbing one guard doesn't auto-reveal you
to one across the building (until alert propagation reaches them).

**The emergence beat (2026-07-03):** when stealth breaks as a side effect of
an action (speech, a pose), observers who couldn't see you get
"…emerges from concealment." *before* the words render — a voice never just
materializes mid-sentence. Trackers who watched you lurk get no redundant line.

**The whisper carve-out (2026-07-03, user-decided):** `whisper` does NOT break
stealth — it's the creepy channel — and it **rides the say parent** (the
shared speech rails, `world/speech.py`): voice flavour/garble apply, the
structured speech payload reaches NPC brains, and attribution follows the
full **sight → voice → someone** chain, now stealth-aware — concealment
gates the VISUAL attribution channel (`resolve_speaker_attribution`), so a
hidden whisperer with a voice the target KNOWS gets named by it ("Roony
whispers to you, …"); an unknown voice reads "Someone whispers to you, …";
a voice modulator defeats the recognition. An unseen whisper leaves the
target **Suspicious**, and bystanders perceive a whisper visually (the
lean-in) — those who can't see the whisperer see nothing. Syntax:
``whisper "Wakka." to <person>`` (legacy ``whisper <person> = <message>``
still accepted).

---

## 7 · Perception-gate integration (the safety model)

A hidden target is filtered from an unaware observer **only in passive
perception**, through the same `filter_present` choke the phase layer
established:

* **Room display** (`get_display_characters` / `get_display_things`) — drops
  targets the looker is Unaware of.
* **Broadcasts** (`msg_contents`) — a hidden mover's incidental messages are
  suppressed to the unaware; deliberate noise *raises awareness* instead.
* **Combat / proximity** — you can't passively target someone you're Unaware of;
  detection (or AoE) is the precondition.

But because hidden ≠ phased, **AoE, area sound, and `search` bypass awareness** —
they reach the target regardless, and may *raise* awareness. This keeps "hidden"
honest: concealment, not invulnerability. One choke point, one new clause; no new
enumeration path (the leak-completeness rule from `PHASE_LAYER_SPEC` §3 applies
unchanged).

---

## 8 · Data model

* **Hidden state** — `char.db.hidden` (bool/room-scoped) for self; `obj.db.hidden`
  for stashed objects. Cleared on move/reveal.
* **Awareness store** — per-observer, mirroring `recognition_memory`:
  `observer.db.awareness = { target_key: { level, last_known_pos, last_roll_t,
  decay_t } }` (`target_key` = stable id; for players, tie to the identity
  apparent-UID so awareness respects disguise — you can be "made" as a presence
  without being identified). `ndb` cache for the hot combat/tick reads.
* **Symmetric** — the same structures live on PCs and NPCs; only the *consumer*
  differs (render vs. state machine).

---

## 9 · Explicitly out of scope (organic or deferred)

* **Concealed carry / "is she armed?"** — *not* a subsystem here. It's already
  organic: a **wielded** weapon shows in sdesc/longdesc; an unwielded one doesn't
  prominently; weapon-priority and the longdesc/clothing-coverage systems convey
  the rest. That is sufficient to inform a player *and* an NPC's threat read.
  Expandable later (dedicated holster/print mechanics) but not now.
* **Free-roam sneak movement** — start **room-scoped** (`hide`/`search` in a
  room). Carry-stealth across the whole map is a later expansion.
* **Stat expansion** — the contest is Resonance/Motorics now; depth (skills,
  specialised gear modifiers) comes later, consistent with the parked
  stat/skill direction (gear + situation carry the weight for v1).

---

## 10 · Integration map

| System | Relationship |
|---|---|
| **Perception** (`world/perception.py`) | Home of the gate; awareness is a new graded clause in `can_perceive` / `filter_present`. |
| **Phase** (`PHASE_LAYER_SPEC`) | Binary sibling; stealth is graded. Same choke points, same leak discipline. |
| **Coordinates** (`SPATIAL_COORDINATE_SYSTEM_SPEC`) | LoS/cover (face state §6.1), distance bands, last-known position, Dijkstra search pattern. |
| **Dispatch** (`NPC_DISPATCH_AND_SIMULATION_SPEC`) | Awareness drives the deterministic NPC state machine; alert propagation is a bus event. |
| **Identity** (`IDENTITY_RECOGNITION_SPEC`) | Parallel concealment axis; awareness store mirrors `recognition_memory` and keys on apparent-UID (detected-as-presence ≠ identified). |
| **Crowd** | Concealment for blending; noise for searching. |
| **Combat** | Ambush opener; attacking breaks stealth per-observer; a caught theft can trigger retaliation / a dispatch response. |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | `frisk` is the *consent-gated* reveal (its effect defined in §3.2 there); `steal`/`pickpocket` (§6.2) are the *nonconsensual contest* — frisk asks, theft takes. On a subdued target both are free actions. |

---

## 11 · Build ladder

| Phase | Scope | Notes |
|---|---|---|
| **1 — Hide/search contest** | `hide` (self/object) + `search`; opposed Resonance/Motorics with environmental modifiers | Room-scoped; gear/situation-driven |
| **2 — Graded awareness store** | Per-observer awareness levels (mirrors `recognition_memory`); decay | The data spine |
| **3 — Gate integration** | Awareness clause in `can_perceive`/`filter_present`; hidden filtered from passive perception; AoE/sound/search bypass | Reuses phase's choke points |
| **4 — NPC hunt** | Deterministic state machine + last-known position + Dijkstra search + alert propagation (dispatch) | The headline MUD feature |
| **5 — Ambush** | Surprise opener via existing aim/initiative; break-on-attack | |
| **6 — Theft** | `steal <item> from <target>` + `pickpocket <target>` (tokens) as contests off the §3 engine; caught → awareness spike + recognition + dispatch; free action on subdued. `frisk` reveal lands with the trust gate | Applied stealth (§6.2) |

Phases 1–2 are the testable core; the gate integration (3) is the safety-
critical step; the hunt (4) is the showcase.

---

## 12 · Risks & open questions

* **Resonance/Motorics direction.** Which stat is hider vs searcher, and any
  blend — fixed pairing, direction TBD (§3.1), expandable.
* **Leak-completeness.** Same risk and same mitigation as phase: one
  `filter_present` choke, tests asserting no unaware-observer leak through
  look/say/combat/emote/crowd.
* **Hidden-but-reachable.** Confirm AoE / area-sound / `search` always bypass
  awareness so concealment never becomes invulnerability or a consequence-dodge.
* **Awareness at crowd scale.** Per-observer × per-target awareness could grow;
  bound it (only track non-default awareness; `ndb` cache; prune on give-up).
* **PC-side UX.** How much to surface to a *player* — the "you sense something"
  Suspicious cue without spoiling the hidden target's identity/position.
* **Persistence.** Does awareness survive logout (probably decays away; NPC
  awareness resets with the population LOD round-trip — reconcile with the
  dispatch director's materialization state).
* **Search-pattern smartness.** How thorough the Dijkstra hunt is before give-up
  (radius, room budget) — tune for fun, not omniscience.
