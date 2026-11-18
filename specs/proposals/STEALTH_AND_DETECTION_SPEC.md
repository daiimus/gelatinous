# Stealth & Detection Spec — Hiding, Searching, and Graded Awareness

This spec covers the **presence-concealment** layer: `hide` (self or object)
against `search` (a room), resolved as an opposed **Resonance/Motorics**
contest and surfaced as a **per-observer graded awareness meter** (unaware →
suspicious → searching → alert). The meter drives **deterministic (non-LLM)
NPC behaviour**, the hunt, which is the headline feature. The PC and NPC
detection loops are **theoretically identical**. The contest engine and the
awareness store live in `world/stealth.py`; the presence gate is
`can_perceive` / `filter_present` in `world/perception.py`; the hunt is
`world/director/hunt.py`. The spec consumes `SPATIAL_COORDINATE_SYSTEM_SPEC`
(line-of-sight, last-known position, search pathing) and feeds
`NPC_DISPATCH_AND_SIMULATION_SPEC` (the hunt).

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

The unified perception gate is `can_perceive` / `filter_present` in
`world/perception.py`, built by this spec's Phase 3 (§7). `PHASE_LAYER_SPEC` is a proposal
whose binary clause slots into the same gate later (its proposed name for
that clause is `co_present`, which exists nowhere in the code). Stealth lives
in the gate as the **graded** counterpart to phase:

| | Phase | Stealth |
|---|---|---|
| Question | "are you in my reality?" | "you're in my reality — do I *notice* you?" |
| Shape | **binary** membership | **graded**, per-observer awareness |
| On "no" | you don't exist to me — **no AoE, no sound, no consequence** | I don't passively notice you — **but AoE, sound, and search still reach you** |

This is the precise distinction: **phase removes you from consequence; stealth
removes you only from passive notice.** A hidden character is still present in
the phase sense — a grenade, a shout, or a `search` finds them. AoE, area
sound and `search` do not route through the gate at all. So stealth is a
*new clause* inside `can_perceive`, not a second gate, and it reuses the
single-choke-point discipline (`filter_present`) that makes the gate safe.

### 2.1 · Where stealth sits among the concealment axes

The game has four ways to be unseen; this spec owns one:

| Axis | "Hide your…" | Home |
|---|---|---|
| Identity | who you are | `IDENTITY_RECOGNITION_SPEC` |
| Reality | which plane | `PHASE_LAYER_SPEC` (proposal) |
| **Presence** | **whether you're noticed** | **this spec** |
| Threat / carry | that you're armed | **organic** — wielding + sdesc + weapon-priority (§9) |

---

## 3 · The detection contest

### 3.1 · The opposed roll

Detection is an **opposed Resonance/Motorics** check between hider and searcher
(`contest` in `world/stealth.py`). Working assumption: the **hider** leans
**Motorics** (quiet movement, stillness, physical craft of concealment) and the
**searcher** leans **Resonance** (perceptive awareness, the sense that someone's
there). The pairing is fixed; the direction and any blend are to confirm and
expand later (§12). The contest is **symmetric**: a PC hiding from an NPC and an
NPC hiding from a PC run the identical math.

### 3.2 · Environmental modifiers

The roll is heavily shaped by situation — which is where the parked-stats design
keeps stealth *gear- and world-driven* rather than stat-driven:

* **Light / shadow** — 📋 UNBUILT (no issue): darkness favours the hider (gated
  by the searcher's sight / blindsight via `world/perception.py`).
* **Cover & line-of-sight** — 📋 UNBUILT (no issue): coordinate-aware
  (`SPATIAL_COORDINATE_SYSTEM_SPEC`): a wall/`barrier` face or an occluding object
  breaks LoS and favours hiding.
* **Crowd** (user-decided 2026-07-03) — the room's crowd level, capped at +3, is
  added to the hider at every contest tier (`crowd_hider_bonus` in
  `world/stealth.py`). "Blending in" is mechanically real.
* **Noise & movement** — hiding on the move (`sneak`) costs 3; any speech or other
  announced act breaks the hide (§6.4). Running as its own penalty is
  📋 UNBUILT (no issue).
* **Distance** — 📋 UNBUILT (no issue): coordinate distance bands degrade passive
  detection.

### 3.3 · What you can hide, and the commands

* **Self (static)** — `hide` / `unhide` toggles the hidden state in the current
  room (a crowd helps; cover and shadow are 📋 UNBUILT (no issue), §3.2). `hide`
  is refused while in combat or while someone in the room is aiming at you
  (§6.4).
* **Self (moving)** — `sneak <direction>` is "move while hiding": it carries you
  through an exit and **induces the hidden state** on arrival (a fresh contest in
  the new room). Sneaking is the in-motion form of `hide`; the same toggle state,
  re-rolled per room, with the movement penalty from §3.2. If you are not already
  hidden, `sneak` first hides you (no penalty) in the room you leave, so watchers
  there can keep track of you; a locked exit is refused before any roll. Watchers
  in the new room who win the contest read "You catch <name> slipping in."
* **Object** — `hide <object>` stashes something you carry into the room. The
  same checks as `drop` apply (`release_to_ground`), and a live or rigged
  explosive is refused (§6.4). Its hiding quality is rolled once (d20 +
  Motorics). Until a `search` beats that roll (d20 + Resonance + 4), the item is
  gone from sight and from name search for everyone, the one who hid it
  included. Once found, it is in sight for everyone. Picking it up, or a fall,
  ends the stash (§6.4). (Stashed contraband, a planted bug, a dropped weapon.)

`search` is the active counter: it spends an action to roll against everything
hidden in the room, raising the searcher's awareness on success. Searching is
done in the open: the room is told the searcher "searches the area carefully",
which ends the searcher's own hide first (§6.4). A person it finds is told they
have been spotted, and stays hidden from everyone but the searcher.

**Secret exits (#1114).** `search` also rolls for view-locked (secret) exits,
in the stash idiom: d20 + Resonance + the search bonus against the exit's
`db.search_difficulty` (default 14, higher than a stash's default of 10;
`search_hidden_exits`). A find is **per searcher**: the exit goes into that
searcher's `db.found_exits` and joins *their* exit prose for good, while
everyone else keeps seeing nothing. An exit may carry its own
`db.search_found_msg`. A secret exit hides only from the exit list: anyone who
types its name can still go through it. First consumer: the Constabulary roof
hatch.

### 3.4 · The passive tier (2026-07-03, user-decided)

Between "never noticed" and "actively searched" sits the free glance:
**entering a room and looking around each run a passive check** against
hidden things — weaker than `search` (the active bonus is withheld) and
**rate-limited per observer→target** (repeat looks reuse the standing
result until a cooldown passes or the hider re-rolls), so look-spam never
equals searching. A clear win spots the hider outright (Detected); a near
miss yields *Suspicious* ("you get the prickling sense that you are not
alone here"). The numbers are in §4. The point: someone perceptive vs someone
terrible at hiding will spot them **inherently**, no action spent.

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
the graded gate in action. The awareness level decides, not the hidden flag
alone: an Alert looker still finds the hidden. Levels rise on failed-hide /
successful-search / noise events and **decay over time** when contact is lost
(the give-up arc). Awareness drops one level per 5 minutes without contact
(`AWARENESS_DECAY`). A passive glance at the same hider re-rolls at most once a
minute; one that falls short by less than 3 gives Suspicious. An active search
adds +4.

**The "lurking" tell.** When a hidden character *is* perceived — a *Detected*
observer, or a failed hide roll where the watcher still sees them — they do **not**
render normally. The stealth state contributes a placement at the top of the
existing hierarchy (`override_place` > `temp_place` > `look_place` > "standing
here." in `get_display_characters`), so to those who see them they read as
**"lurking in the shadows"** rather than "standing here." Failed concealment
doesn't restore a normal appearance; it makes you *visibly furtive* — onlookers
can tell this is someone who doesn't want to be seen. At *Suspicious* the
watcher gets only the cue "You get the prickling sense that you are not alone
here.", no placement; the lurking placement appears at *Detected*: "lurking in
the shadows." in a quiet room, "holding an unconvincing calm — a nervous,
somewhat off face in the crowd." in a crowd of level 2 or more
(`lurk_placement`). A blind looker gets no cue and sees nobody in the room,
hidden or not.

**Identical loop, two consumers.** The same per-observer awareness data is:
* **rendered to a PC** ("You get the prickling sense that you are not alone
  here." at *Suspicious*; the target appears at *Alert*), and
* **read by a deterministic NPC** as the input to its behaviour state machine
  (§5).

That symmetry — one mechanic, a human reads it as tension, an AI reads it as a
state transition — is the design's point.

---

## 5 · NPC hunt behaviour (deterministic, MGS/Hitman/Thief)

Only security units (`db.role == "security"`) hunt, and only with cause.

**The hunt requires cause** (user-decided 2026-07-03, revised the same day).
Cause has two axes:

* **Status** — a wanted record on the presence's apparent-UID (the same key the
  awareness store uses). The check is silent.
* **Situation** (user-decided, same day) — every `raise_event` logs an incident
  (ServerConfig, rolling, 10-minute window). An unresolved incident — a raised
  event with no known source, in the last 10 minutes — runs the scene **hot** in
  its room and the adjacent rooms. A detonation raises a severity-2 sourceless
  `disturbance` (an explosion is an anonymous crime). A hidden presence near a
  hot scene is reasonable suspicion: the hunt commits and the reacquire
  challenge applies even without a wanted record. Known-source events don't heat
  the scene; that perpetrator is hunted by UID.

Cause counts when the incident is in or next to the hunter's room or the
presence's last-known room (`_has_cause`). Cause gates hunt **commitment**
itself: without cause the presence is ignored entirely — no orient, no sweep,
no roust. Hiding is not a crime, and security must not small-world every
wallflower. A detected innocent simply reads as visibly furtive through the
crowd-aware lurk placement (§4). A pardon mid-hunt stands the unit down
silently.

The souls scheduler offers the hunt (`wants_hunt` in `world/souls/engine.py`
queues a `hunt` job; `world/souls/jobs.py` runs `tick_hunt`) in a low band, so
a unit already busy (on a call, in combat, travelling or talking) does not
hunt. Nothing in the director ticks it (#2373).

The awareness meter drives a hardcoded NPC state machine — **no LLM** — wired
into `NPC_DISPATCH_AND_SIMULATION_SPEC`:

```
Unaware ──(detect)──▶ Suspicious ──(confirm)──▶ Searching ──(reacquire)──▶ Alert
   ▲                      │                          │                       │
   └──(decay/give up)─────┴───────(timeout)──────────┘                  (engage)
```

In the code a hunter commits at Suspicious and its own record stays there
(`tick_hunt`). Level 2 (Searching) is written only by alert propagation, onto
the other security units; any other observer's awareness is 0, 1 or 3.

* **Suspicious** — break routine and commit: the unit emotes "snaps alert,
  optics sweeping for something it half-caught." (the player's visible cue to
  move). Turning toward a noise's bearing or a glimpsed coordinate is
  📋 UNBUILT (no issue).
* **Searching** — the hunt: director travel to the **last-known room** (stamped
  on the awareness record) and sweep it with the real `search` command, then
  sweep that room's neighbours one at a time, skipping any the hunter cannot
  reach, until 4 rooms (`SEARCH_BUDGET`) are spent; a room it tries and cannot
  get into still costs one. The fan-out is adjacency, not full Dijkstra. Allies
  are alerted on reacquire (below), not while searching. A **Dijkstra search
  pattern** over coordinates is 📋 UNBUILT (no issue).
* **Alert** — reacquired with cause → the unit says "Halt, Colonist. Remain
  where you are.", radios "Unit engaging — backup to <room>." (`xmit`), raises a
  severity-2 `disturbance` naming the target (dispatch takes over from there),
  and sets every other security unit to Searching at that room (alert
  propagation, `propagate_alert`). It starts no combat itself. If the cause has
  gone (a pardon), it stands down silently.
* **Give up** — the budget runs out with no reacquire, or the record has
  decayed → the hunter's awareness of the target goes back to Unaware, the unit
  gives a give-up beat, and it returns to its patrol routine. The cooldown is
  the Hitman/Thief "they lost me" beat.

The LLM may *optionally* be handed an Alert beat for flavour (budget permitting,
per the dispatch escalation gate) — but the **awareness and the hunt are fully
deterministic**, which is exactly why this scales without LLM cost.

---

## 6 · Applied contest — ambush, theft, breaking stealth

### 6.1 · Ambush

Acting on a target who **can't perceive you** is an ambush: the opener lands
with a first-strike advantage, routed through existing systems, not a new
combat path. `world.stealth.is_ambush(attacker, target)` = the presence gate
(`not can_perceive(target, attacker)`), read BEFORE `break_stealth` flips them
to Alert. Covers **both** the combat and non-combat openers (user-decided):

* **attack / grapple** — `AMBUSH_INITIATIVE_BONUS` (+20) folds into the
  attacker's combat initiative via `add_combatant(..., ambush_bonus=)` (called
  from `commands/combat/core_actions.py` and
  `commands/combat/special_actions.py`), so from concealment you act first; the
  grapple resolves on that first turn before the target can contest. "You
  strike/lunge from concealment!" A grab the target has consented to is never
  an ambush and takes no bonus (#3363).
* **theft** — `AMBUSH_CONTEST_BONUS` (+6) on the steal/pickpocket contest
  (§6.2): a mark who doesn't know you're there is far easier to lift.

v1 scope: initiative primacy (going first IS the ambush). A separate accuracy
bump is a future tune — deliberately not a stealth-insta-kill.

### 6.2 · Theft (steal & pickpocket)

**Theft is applied stealth** — a nonconsensual Resonance/Motorics contest whose
risk is *getting caught*. It is the contest engine (§3) and the awareness meter
(§4) pointed at taking things, not a separate system. The commands live in
`commands/CmdTheft.py`.

**No frisk gate (user-corrected, 2026-07-03).** The design had concealed items
untargetable by `steal` until perceived or surfaced by a `frisk`; the user
corrected that: theft is accessible to anyone. The design also had theft
requiring combat proximity (close/adjacent); same-room is the only spatial
gate.

* **`steal <target>`** — lift something **at random from what they're
  carrying** (not worn, not in a hand slot, even a ruined hand's; never integrated
  cyberware; `_stealable_inventory`). No frisk required: theft is accessible
  to anyone. **`steal <item> from <target>`** is the *precision path* — name a
  piece and it is taken if it is among what they carry (not worn, not in a
  hand); you do not need to have seen it. Neither path is perception- or
  frisk-gated. Knowing what they carry (a frisk, a tip) only tells you what to
  name: frisk-then-steal on a subdued mark is the mugging loop, as intel, never
  as a gate.
  Contest: thief-vs-victim (`world.stealth.contest`, crowd + ambush folded in).
  **Success** → the item transfers, clean. **Failure** → *caught*: the victim
  and every character in the room who can see jump to **Alert** toward the thief, recognition
  keys on the thief's **apparent-UID** (a mask protects you), and the
  theft is reported as `pickpocketing` with no named thief (`report_crime` in
  `world/director/crime.py`). A security unit in the room raises the report at
  once; otherwise a witness is rolled from the crowd and calls it in after a
  delay, and can be silenced first; with neither, nothing is reported. A raised
  report has no known source, so it runs the room and its neighbours hot for the
  hunt (situational cause, §5). Same-room is the ONLY spatial gate — theft is
  stealth, not combat, so it never requires proximity or an advance.
* **`pickpocket <target>`** — **tokens (currency) only**: a blind grab for cash,
  lower-stakes and more deniable than targeted theft (you don't choose *what*, you
  lift *some*). Same contest and same consequences when
  caught as `steal`; lighter tuning is 📋 UNBUILT (no issue). The amount lifted
  is random, from 1 up to a third of the tokens the mark carries. Specific
  items are the riskier `steal`.
* **Subdued / unconscious / dead target** → **free action** (it's just looting),
  via the `TRUST_AND_CONSENT_SPEC` predicate. The contest only matters for an
  awake target who could notice — which is the whole skill.

### 6.3 · Frisk (the consent-gated reveal)

`frisk <target>` **lists everything on a person — worn, in hand, carried
(what a look never shows) and their tokens**. A corpse or a severed part can
always be frisked. It is **not** a contest: it is the
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

**Acting reveals (2026-10-24, #3763, #3767, #3769; 2026-10-25, #3773; part of
#3659).** Hiding lasts until you do something visible or something visibly
happens to you, and a few things cannot be started from hiding at all.

* **Owner, against five played-out scenes (#3763, 2026-10-24):**
  * sitting or lying down breaks the hide (the pose `_take_posture` issues goes
    through `CmdDotPose`, which breaks it);
  * being hit breaks it and a miss does not (`take_damage`, where every hit
    lands: melee, a shot, a thrown object, a blast, a fall);
  * an untargeted throw never lands on a person the thrower cannot perceive
    (`select_random_target_in_room` / `select_most_magnetic_target_in_room` take
    the thrower as `seen_by`);
  * buying breaks it (`ShopContainer.purchase_item`, so the spoken counter order
    and the `buy` command agree);
  * `hide` is refused while in combat or while someone in the room is aiming at
    you.

  Each of these reveals is one `break_stealth` call at the place the action
  happens, not quiet, so the emergence beat lands before the line that names
  you.
* **Quiet endings.** Falling unconscious, dying, or moving any way other than
  `sneak` ends the hide quietly, with no emergence line.
* **Explosives and LLM company (#3767, 2026-10-24).** A live or rigged explosive
  cannot be stashed (`hide <device>` refuses: "A trap is in plain sight to
  anyone in the room with it"), a detonator arming a stashed charge brings it
  into sight before its beep, and an LLM NPC counts only the company it
  perceives when deciding a speaker is alone with it (the PRESENT roster and
  the arrival notice do the same, #2589).
* **Every announced act reveals (#3769, 2026-10-24), the core.** Every act a
  hidden character announces to the room reveals them, in the announcer itself.
  `msg_room_identity` breaks the hide of the referent of each ``acting``
  placeholder (the ``actor`` by default; ``surgeon``, ``physician``, ``buyer``,
  ``caller``, ``target_char`` where a call names its actor otherwise) before it
  renders, so the emergence beat lands first; announcements that are not acts
  (collapsing, waking, dying, a garment tearing, a part severed, falling, a
  bleed, the move lines a sneak relies on) pass ``acting=()``. `wield`
  announces nothing and reveals on its own. Owner, on the audit of 234
  announcements: changing clothes, eating or treating yourself, picking up or
  dropping, aiming ("Aiming is not an ambush. It reveals you."), following and
  throwing all reveal; whisper and sneak are the only quiet acts; tailing
  someone unseen will be its own command, `shadow`.
* **Search reveals too** (owner, 2026-10-25), superseding #2562's quiet
  searcher: the searcher's own hide ends when they search (§3.3).
* **Followers, recognition, falling stashes (#3773, 2026-10-25).** A hidden
  leader who sneaks out leaves behind every follower who lost track of them,
  silently; no line to the follower, none to the room ("The onus is on them to
  'look' and notice someone is gone."). A follower who kept track still trails.
  Walking into a room does not refresh your recognition memory of anyone you
  cannot perceive. A stashed item that falls through open air ends its fall in
  plain sight, landed or stranded in a cell with nothing beneath, its hiding
  place forgotten the way a pickup forgets it. The recency pass runs after the
  arrival's glances, so a hider you spot as you walk in is marked seen. A
  stashed workbench counting for repair was ruled moot. Tailing someone unseen
  is its own enhancement, `shadow` (#3772).

**The whisper carve-out (2026-07-03, user-decided):** `whisper` does NOT break
stealth — it's the creepy channel — and it **rides the say parent** (the
shared speech rails, `world/speech.py`): voice flavour/garble apply, the
structured speech payload reaches NPC brains, and attribution follows the
full **sight → voice → someone** chain, stealth-aware — concealment
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
perception**, through the single enumeration choke `filter_present`
(`can_perceive(looker, target)` in `world/perception.py`):

* **Room display** — `get_display_characters` drops a hidden person for any
  looker below Alert (a Suspicious looker gets only the cue line);
  `get_display_things` drops every stashed object for everyone until a search
  turns it up.
* **Adjacent-room sightings** — gated the same way.
* **Broadcasts** (`msg_contents`) — a hidden mover's incidental messages and
  move announcements are suppressed to the unaware; deliberate noise *raises
  awareness* instead (§6.4).
* **Combat / proximity and targeting** — you can't passively target someone
  you're Unaware of; detection (or AoE) is the precondition. Identity targeting
  (`resolve_character_target`) refuses targets you are unaware of, so attack,
  operate, frisk and trust all refuse them.
* **Emotes** — char-ref candidacy is gated: you can't pose AT someone you're
  unaware of.
* **Speech** — attribution is stealth-aware (`resolve_speaker_attribution`):
  hidden speakers are attributed by VOICE. Whisper bystanders are gated.
* **LLM NPCs** — the PRESENT roster lists only those the NPC perceives.
* **Name search** (`Character.get_search_candidates`, #3637) — every local
  search's pool drops what the searcher cannot perceive, before Evennia matches,
  for people and things alike: the default reach, `location=`, and a command's
  own `candidates=`. So `look <stashed item>`, `get <x> from <stashed
  container>`, and a key search for a hidden person (`look alice` after
  `remember alice as Alice`) find nothing. Ordinals and exact-before-partial
  matching count only what the searcher perceives. `defuse` and
  `remember <papers>` (`held_by_others`) match names over room contents by hand
  and take the same gate; `get`/`put` and the whisper/`to` target check rely on
  the pool gate. Global and #dbref searches (staff tooling) have no pool and
  stay ungated.

What still names or counts the hidden outside name search (broadcasts,
occupancy, relations) is tracked in #3659.

But because hidden ≠ phased, **AoE, area sound, and `search` bypass awareness** —
they reach the target regardless, and may *raise* awareness. This keeps "hidden"
honest: concealment, not invulnerability. One choke point, one new clause; no new
enumeration path (the leak-completeness rule from `PHASE_LAYER_SPEC` §3 applies
unchanged).

---

## 8 · Data model

* **Hidden state** — `char.db.hidden` (bool/room-scoped) for self; `obj.db.hidden`
  for stashed objects (with `obj.db.stash_roll`, the hiding quality rolled at
  stash time). Cleared on reveal and on any move but `sneak`.
* **Awareness store** — per-observer, mirroring `recognition_memory`:
  `observer.db.awareness = { target_key: { level, t, t_roll, last_room } }`
  (`set_awareness` in `world/stealth.py`). Decay is computed lazily from `t`
  against `AWARENESS_DECAY` (300 s per level); there is no stored decay field.
  There is no `ndb` cache: `_records` reads `db.awareness` on every read.
  `target_key` = stable id; for players, tied to the identity apparent-UID so
  awareness respects disguise — you can be "made" as a presence without being
  identified.
* **Symmetric** — the same structures live on PCs and NPCs; only the *consumer*
  differs (render vs. state machine).

---

## 9 · Explicitly out of scope (organic or deferred)

* **Concealed carry / "is she armed?"** — *not* a subsystem here. It's already
  organic: a **wielded** weapon shows in sdesc/longdesc; an unwielded one doesn't
  prominently; weapon-priority and the longdesc/clothing-coverage systems convey
  the rest. That is sufficient to inform a player *and* an NPC's threat read.
  Expandable later (dedicated holster/print mechanics) but not now.
* **Free-roam sneak movement** — hiding carries from room to room only through
  `sneak`, which contests again in each new room; any other move ends it.
  Whether anything beyond that is wanted is not decided (§12).
* **Stat expansion** — the contest is Resonance/Motorics now; depth (skills,
  specialised gear modifiers) comes later, consistent with the parked
  stat/skill direction (gear + situation carry the weight for v1).

---

## 10 · Integration map

| System | Relationship |
|---|---|
| **Perception** (`world/perception.py`) | Home of the gate; awareness is a graded clause in `can_perceive` / `filter_present`. |
| **Phase** (`PHASE_LAYER_SPEC`) | Binary sibling; stealth is graded. Same choke points, same leak discipline. |
| **Coordinates** (`SPATIAL_COORDINATE_SYSTEM_SPEC`) | LoS/cover (face state, §6.1 there), distance bands, last-known position, Dijkstra search pattern. |
| **Dispatch** (`NPC_DISPATCH_AND_SIMULATION_SPEC`) | Awareness drives the deterministic NPC hunt; alert propagation writes Searching awareness straight onto the other security units (`propagate_alert`), and the reacquire raises a `disturbance` for dispatch. |
| **Identity** (`IDENTITY_RECOGNITION_SPEC`) | Parallel concealment axis; awareness store mirrors `recognition_memory` and keys on apparent-UID (detected-as-presence ≠ identified). |
| **Crowd** | Concealment for blending; noise for searching. |
| **Combat** | Ambush opener; attacking breaks stealth per-observer; a caught theft can trigger retaliation / a dispatch response. |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | `frisk` is the *consent-gated* reveal (its effect defined in §3.2 there); `steal`/`pickpocket` (§6.2) are the *nonconsensual contest* — frisk asks, theft takes. On a subdued target both are free actions. |

The phase names other documents use map to sections here: Phase 1, hide/search
contest (§3); Phase 2, graded awareness store (§4); Phase 3, gate integration,
the leak sweep (§7); Phase 4, NPC hunt (§5); Phase 5, ambush (§6.1); Phase 6,
theft (§6.2).

---

## 11 · Unbuilt

* **Light / shadow modifier** — 📋 UNBUILT (no issue), §3.2.
* **Cover & line-of-sight modifier** — 📋 UNBUILT (no issue), §3.2.
* **Running as its own penalty** — 📋 UNBUILT (no issue), §3.2.
* **Distance bands** — 📋 UNBUILT (no issue), §3.2.
* **Hunter turns toward a noise's bearing or a glimpsed coordinate** —
  📋 UNBUILT (no issue), §5.
* **Dijkstra search pattern over coordinates** — 📋 UNBUILT (no issue), §5.
* **Lighter tuning for `pickpocket`** — 📋 UNBUILT (no issue), §6.2.

---

## 12 · Not decided (risks & open questions)

* **Resonance/Motorics direction.** Which stat is hider vs searcher, and any
  blend — fixed pairing, direction TBD (§3.1), expandable.
* **Loitering** (marked by the user for eventual reconsideration). Whether and
  where loitering itself warrants a response — e.g. zone-dependent (corporate
  blocks vs the sprawl) — revisit with the faction/zone work.
* **Free-roam sneak movement.** Whether anything beyond `sneak` is wanted (§9).
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
