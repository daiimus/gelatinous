# Stealth & Detection Spec — Hiding, Searching, and Graded Awareness

> **Status:** 🚧 **PHASES 1–2 + PASSIVE TIER + DISPLAY INTEGRATION SHIPPED
> (2026-07-03).** Live: `world/stealth.py` (opposed Motorics-hider vs
> Resonance-searcher contest; per-observer graded awareness store keyed on
> apparent-uid, lazy decay), `hide`/`unhide`/`sneak`/`search` commands, the
> **passive tier** (§3.4), display integration (room roster filters
> Unaware/Suspicious; the *Suspicious* "prickling sense" cue; the "lurking
> in the shadows" placement for the Detected; hidden objects out of the
> things list; hidden movers' announcements suppressed to the unaware), and
> break-on-action (speech, attack, open movement). **PHASE 3 (LEAK SWEEP)
> SHIPPED (2026-07-03):** `world/perception.py` now owns the presence gate —
> `can_perceive(looker, target)` + the single enumeration choke
> `filter_present` (built HERE; the phase layer's binary clause slots in
> later) — wired through: room roster (P1), adjacent-room sightings,
> identity targeting (`resolve_character_target` — attack/operate/frisk/
> trust all refuse targets you're unaware of), emote char-ref candidacy
> (can't pose AT someone you're unaware of), the LLM NPC PRESENT roster,
> move announcements, whisper bystanders, and speech attribution
> (stealth-aware `resolve_speaker_attribution` — hidden speakers attribute
> by VOICE). Leak-completeness tests drive each real path. Deliberate
> bypasses hold: AoE, area sound, `search`. **PHASE 4 (THE HUNT) SHIPPED
> (2026-07-03):** `world/director/hunt.py` — the deterministic state
> machine off the awareness meter, ticked by the director heartbeat
> before the patrol beat: Suspicious → orient beat (the player's audible
> cue) + commit; Searching → director-travel to the LAST-KNOWN room
> (stamped on awareness records) and sweep it with the REAL `search`
> command, fanning through unswept adjacents on a bounded budget
> (SEARCH_BUDGET=4); reacquire → challenge ("Halt, Colonist."), raise a
> `disturbance` (existing dispatch/challenge machinery takes over), and
> PROPAGATE (every other security unit seeded to Searching at the
> sighting room); budget out / record decayed → give-up beat, records
> dropped, patrol resumes. v1 fan-out is adjacency, not full Dijkstra;
> hunters are role=security. **2026-07-03 follow-ups (user-decided):**
> the CROWD hider bonus is live (first environmental modifier — crowd
> density, up to +3, helps the hider at every contest tier; "blending
> in" is mechanically real; light/cover still ride the coordinate
> integration), and **THE HUNT REQUIRES CAUSE** (user-decided, revised
> same day): the wanted-record check (same apparent-uid key) is SILENT
> and gates hunt COMMITMENT itself — an unwanted hidden presence is
> ignored entirely (no orient, no sweep, no roust; hiding is not a
> crime and security must not small-world every wallflower). The
> detected innocent simply reads as visibly furtive via the crowd-aware
> lurk placement ("a nervous, somewhat off face in the crowd" in a
> throng; "lurking in the shadows" in an empty room). A pardon mid-hunt
> stands the bot down silently. **SITUATIONAL CAUSE (user-decided, same
> day):** cause has two axes — STATUS (the wanted record) and SITUATION:
> every `raise_event` logs an incident (ServerConfig, rolling, 10-min
> window); a **sourceless** event (an explosion — detonations now raise
> a severity-2 sourceless `disturbance` — an anonymous crime) runs the
> scene HOT in its room + adjacents, and a hidden presence near a hot
> scene IS reasonable suspicion: the hunt commits and the reacquire
> challenge applies even without a wanted record. Known-source events
> don't heat the scene (that perp is hunted by uid). **Marked for
> eventual reconsideration (user):** whether/where loitering itself
> warrants a response — e.g. zone-dependent (corporate blocks vs the
> sprawl) — revisit with the faction/zone work. NOT yet built: ambush
> advantage (§6.1), theft (§6.2), light/cover modifiers.
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

### 6.1 · Ambush — SHIPPED (2026-07-03)

Acting on a target who **can't perceive you** is an ambush: the opener lands
with a first-strike advantage, routed through existing systems, not a new
combat path. `world.stealth.is_ambush(attacker, target)` = the presence gate
(`not can_perceive(target, attacker)`), read BEFORE `break_stealth` flips them
to Alert. Covers **both** the combat and non-combat openers (user-decided):

* **attack / grapple** — `AMBUSH_INITIATIVE_BONUS` (+20) folds into the
  attacker's combat initiative via `add_combatant(..., ambush_bonus=)`, so
  from concealment you act first; the grapple resolves on that first turn
  before the target can contest. "You strike/lunge from concealment!"
* **theft** — `AMBUSH_CONTEST_BONUS` (+6) on the steal/pickpocket contest
  (§6.2): a mark who doesn't know you're there is far easier to lift.

v1 scope: initiative primacy (going first IS the ambush). A separate accuracy
bump is a future tune — deliberately not a stealth-insta-kill.

### 6.2 · Theft (steal & pickpocket)

**Theft is applied stealth** — a nonconsensual Resonance/Motorics contest whose
risk is *getting caught*. It is the contest engine (§3) and the awareness meter
(§4) pointed at taking things, not a separate system.

**SHIPPED (2026-07-03; user-corrected: no frisk gate).**

* **`steal <target>`** — lift something **at random from what they're
  carrying** (not worn, not in-hand). No frisk required: theft is accessible
  to anyone. **`steal <item> from <target>`** is the *precision path* — go for
  a named piece, but only one you can actually perceive/reach (frisked,
  tipped, in plain sight); intel lets you CHOOSE, it's never a gate.
  Contest: thief-vs-victim (world.stealth.contest, crowd + ambush folded in).
  **Success** → the item transfers, clean. **Failure** → *caught*: the victim
  and every witness in LoS jump to **Alert** toward the thief, recognition
  keys on the thief's **apparent-UID** (a mask protects you), and a
  **sourceless `crime` event** runs the block hot (situational cause — the
  hunt reads it). Same-room is the ONLY spatial gate — theft is stealth, not
  combat, so it never requires proximity or an advance.
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
