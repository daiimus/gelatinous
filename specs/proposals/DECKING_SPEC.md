# Decking Spec — Runs, Traces, and the Net's Game Loop

> **Status:** 📋 **DESIGN DRAFT — spec-first, build-later.** The net's
> *substrate* is `PHASE_LAYER_SPEC` (net = a phase over the same geography;
> the two-body model; the single perception gate), which is itself unbuilt and
> depends on the vertical/coordinate world. So this whole system is
> **deliberately spec-now, build-when-the-world-is-ready** — the solution and
> the vibes sharpen as the colony fills in. Primary reference:
> **uplink-headless-mod** (https://github.com/hosler/uplink-headless-mod) — a
> reverse-engineered, GUI-stripped *Uplink* whose engine reduces the entire
> hacking genre to ~40 discrete commands. That reduction is the proof:
> **Uplink's loop is already a text game.** We adopt its loop (bounce →
> intrude → work under a trace → clean logs → jack out) and its CLI, then make
> it ours with a **roll-your-own programming layer** (§6) and one unifying
> doctrine: **everything is a file** (§2).

---

## 1 · Why Uplink, specifically

The headless mod demonstrates four things that map straight onto a MUD:

1. **A discrete command surface is enough.** ~40 operations carry the whole
   game — connect/bounce/navigate, file & log ops, LAN scan, cracking,
   tracing, mail/missions/BBS, hardware & software shopping. The GUI was
   always incidental to the loop.
2. **Timed async operations are the tension.** Cracks and copies take real
   seconds while a trace advances — tension without twitch. Evennia's `delay`
   and the director heartbeat already run this shape.
3. **Layered navigation** (map → node → console) mirrors rooms → objects →
   commands. The MUD *is* the interface metaphor; nothing to invent.
4. **Missions close the loop** (accept → run → deliver → get paid) — which is
   Gelatinous's gig/favor direction verbatim.

We take Uplink's **CLI vocabulary** as the starting command set (`connect`,
`bounce`, `scan`, `navigate`, `files`, `copy`, `delete`, `logs`, `crack`,
`trace`, `mail`, `missions`, `bbs`, `balance`, `buy`) and its **hardware axis**
(CPU / memory / modem as capability tiers). What we add on top — the
programming layer and the file doctrine — is what makes it Gelatinous rather
than a port.

## 2 · Everything is a file (the doctrine)

The net is not a minigame bolted beside the world — it is the **data layer of
the world**, and in that layer *everything is a file*:

* A **gig / contract** is a file on a BBS or a fixer's host.
* A **contact / dossier** is a file (who knows whom; a face-to-name link).
* A **schematic** — clothing, a weapon, a cyberware mod — is a file you feed a
  **3-D printer** to fabricate the real object (ties crafting to the net).
* The **wanted record** is a file. `world/director/intel.py` already stores it;
  a decker who cracks the right host can **clear their own wanted flag** or
  **frame an enemy** by writing one in. Crime and reputation gain a digital
  attack surface.
* **Currency, logs, mail, door/camera ACLs, a bot's directive table** — files.

Two consequences that make this a first-class play space:

* **You can steal data _or_ hardware.** Copy the schematic file (data theft,
  quiet, duplicable) *or* rip the physical component out of a machine in
  meat-space (hardware theft — the stealth/theft layer §6.2 already does
  this). Two routes to the same prize, different risk shapes.
* **Editing a file edits the world.** Because these files are the same objects
  the deterministic systems read (the wanted record, a gig board, a printer's
  queue), changing the file *changes reality* — no separate "apply" step.

Design rule: a net-file is a real game object with a phase-`net` presence and a
meat-space twin (the machine that hosts it). Perceiving/reading it is
phase-gated; changing it goes through the same validation the meat systems use.

## 3 · The stack (what's substrate, what's this spec)

| Layer | Owner | Status |
|---|---|---|
| Net as a phase; two-body model; perception gate | `PHASE_LAYER_SPEC` | specced, unbuilt |
| Everything-is-a-file doctrine (§2) | this spec | draft |
| Net topology over real geography (§4) | this spec | draft |
| The run loop: bounce, intrusion, logs (§5) | this spec ← Uplink | draft |
| **Programs — roll-your-own (§6)** | this spec | draft |
| Trace = the hunt, pointed at the net (§7) | this spec ← `world/director/hunt.py` | draft |
| ICE = deterministic NPCs (§8) | this spec ← robot/mob pattern | draft |
| Deck & components = gear (§9) | this spec ← parked-stats stance | draft |
| Data as target (§10) | this spec ← `intel.py`, crafting | draft |
| Jobs = gigs over the BBS (§11) | this spec ← growth direction | draft |
| Cross-phase effects (cameras, doors, radio taps) | `PHASE_LAYER_SPEC` §7/§9 | reserved |

## 4 · Topology — hosts live somewhere

Per the phase layer, the net overlays the **same geography**: a corp's host is
*in its building*, the colony's utility grid *under its streets*. Net-rooms
(nodes/hosts) are rooms in `phase = net`, anchored to the real coordinates of
the machine that runs them:

* **Public grid** — the walkable net commons (the bounce fabric): exchange
  nodes roughly following district geography.
* **Hosts** — a facility's system: entry node (gate/ICE) → interior nodes
  (filesystems, controls, logs) — a small "building" in the net whose
  meat-space twin is a real place. **This is the high-rise dependency shared
  with radio: corporate towers are where the good hosts live.**
* **Dark nodes** — unlisted addresses (found, bought, extracted): the net's
  speakeasies.

Navigation is movement; the map is the room graph; "layered navigation" comes
free.

## 5 · The run loop (Uplink's, adapted)

1. **Jack in** — from a fixed terminal or a portable **deck**. The body slumps
   in meat-space: a **free-action target** (the trust spec's `can_contest`
   predicate already covers this — guard your meat, or someone frisks/knifes
   it while you're under).
2. **Bounce** — route your entry through public/compromised nodes before the
   target. Your bounce path is *real* — the literal sequence of net-rooms your
   connection traverses — and **the trace walks it back**. More hops = longer
   trace runway but slower work; the classic Uplink tension.
3. **Intrude** — reach a host's entry node; get past its gate (a **crack**
   program vs. the host's auth) to enter the interior.
4. **Work** — the objective: `copy` a file, `delete`/edit one, `scan` a LAN,
   read `logs`. Every operation takes time and **advances the trace** (§7).
5. **Clean logs** — your intrusion wrote log entries at every hop; a
   log-scrub program removes the trail. Skip it and you're identified after
   the fact (a delayed wanted flag), even if you jack out clean.
6. **Jack out** — disconnect before the trace completes. Late → the host's
   security reacquires you: disconnection, counter-intrusion, a dispatch event
   at your **meat-space** coordinates (they know where the body is).

## 6 · Programs — roll-your-own (the headline twist)

Uplink sells you `Cracker_v3.exe`. **We let you write it.** A decker's tools
are **programs they author** from a palette of instructions, and the program's
sophistication is bounded by what instructions they can use and what their deck
can run. This replaces "buy a better tool" with "*write* a better tool," which
fits the gear/favor progression stance and makes hacking a craft.

### 6.1 · The model

* A **program** is an ordered list of **instructions** (steps that run top to
  bottom), each an operation with **typed arguments validated as you build**
  (a malformed program won't save — the reference model).
* Instructions span primitives (connect, read, output/log, a bare crack),
  **control flow** (loop, branch), **variables**, **network ops** (scan,
  bounce, copy), and **security ops** (delete-log, spoof, forge). The richer
  the instruction, the fancier the program.
* Programs are stored as **files** (§2) — shareable, stealable, tradeable. A
  good program is loot.

### 6.2 · The unlock axis — Intellect now, skill later, plus the rig

Two gates decide what you can write and run (user-decided 2026-07-03):

* **What instructions you may use** — gated on **Intellect** for now (the
  existing stat), so the palette widens as a smart character grows into it. A
  proper **decking skill** replaces/augments this later when the skill system
  lands (parked); the seam is designed so that swap is additive, not a
  rewrite. Some instructions are additionally gated on **acquired knowledge**
  — an instruction library you buy, find, or extract — so an unlock can also
  be *a place you went and a thing you did*, keeping it true to gear/favor.
* **What your deck can run** — the **Uplink hardware axis** (§9): CPU sets
  execution speed, memory sets program size, and the rig's grade sets how much
  **heat** (trace pressure) it can absorb before it cooks. **Better rigs
  handle more heat; rare components are harder to acquire** — the scarcity is
  the progression.

Net: Intellect (→ skill) opens the *vocabulary*; the rig sets the *envelope*.
A brilliant decker on a cheap deck writes elegant programs they can't run
big; a rich one on a monster rig runs brute-force garbage that still works.

### 6.3 · Authoring — the operate model, both ways

Two front-ends onto the same readable program (user-decided):

* **Guided composer** — an `operate`-style menu (the clinic's surgical-chart
  UX): pick an instruction, fill typed args with live validation, save to the
  deck. Friendly, discoverable, the default for most players.
* **Hand-typed** — write/edit the program as text directly, old-school. The
  same program, expressed as text; power users skip the menu.

Both produce the identical stored file, and a program **reads as text**
whichever way it was made (it's a MUD).

## 7 · Trace — the hunt, pointed at the net

A trace is **the deterministic hunt (`world/director/hunt.py`) re-idiomed for
the net** — parallel machinery, same shapes (user-decided: parallel, not
literal reuse; the net's topology differs from room geography, and we'll refine
until it feels right). The mapping:

* **Awareness → trace progress.** Intrusion accrues the host's awareness of
  you the way skulking accrues a guard's; noisy programs (more ops, longer
  runtime, low-skill instructions) advance it faster, elegant ones stay quiet
  — the §6 craft has a **consequence axis**, mirroring stealth's contest.
* **Searching → walking the bounce path.** The trace back-walks your hops
  (last-known → adjacent), exactly the hunt's last-known-room sweep.
* **Reacquire → engage.** Completed trace = you're identified: disconnect,
  counter-intrusion, and a **dispatch event at your meat coordinates** (they
  learned where the body is — the two-phase payoff).
* **Give up → decay.** Jack out and stay off the host and the trail goes cold,
  the same decay curve.

## 8 · ICE — deterministic NPCs in the net

Intrusion Countermeasures are net-side NPCs on the existing robot/mob +
deterministic-behavior pattern (the hunt/dispatch machinery, not the LLM):
gate ICE challenges entry, patrol ICE sweeps interior nodes, black ICE engages
(net "combat" per `PHASE_LAYER_SPEC` §5.4). They read the same awareness/trace
meter a security bot reads on the street — one behavior model, two theatres.

## 9 · The deck & components — gear

The rig is the gear axis (Uplink's hardware, our scarcity):

* **CPU** — execution speed (how fast a program's instructions run vs. the
  trace clock).
* **Memory** — program size (how many instructions / how much data you can
  hold).
* **Modem / interface** — connection speed, bounce capacity.
* **Grade / shielding** — **heat tolerance**: how much trace pressure the rig
  absorbs before failure.
* **Components are physical objects** (§2 hardware theft applies) and **rare
  ones are hard to acquire** — bought from fringe vendors, looted, printed
  from a stolen schematic, or won as gig payment. The rig you can assemble is
  your progression.

## 10 · Data as target (what a run is *for*)

Because everything is a file (§2), a run's objective is concrete and varied:

* **Steal data** — `copy` a schematic (→ print the object), a dossier (→
  intel/blackmail), a gig, a password file.
* **Steal hardware** — the meat-space route: rip the component out (stealth
  §6.2). Two paths, one prize.
* **Edit the crime database** — clear your own wanted flag, forge an enemy's
  (`intel.py` is the file). High-value, high-ICE — the marquee corp-host run.
* **Sabotage** — flip a door/camera ACL, corrupt a printer queue, brick a
  bot's directive table, mute a base station (radio §5 cross-tap).
* **Plant / forge** — write a file into a host: false evidence, a backdoor, a
  logic bomb.

## 11 · Jobs — gigs over the BBS

A decking contract is a **gig** (growth direction) that lives as a file on a
BBS or fixer host: accept → run → deliver the payload (a copied file, a
confirmed edit) → get paid in tokens, gear, or favor. The net gives the
gig/favor economy its first rich, repeatable content loop and a reason to own
a deck.

## 12 · Integration seams

| System | Relationship |
|---|---|
| **Phase** (`PHASE_LAYER_SPEC`) | The substrate: net = phase, two-body model, perception gate. Build FIRST. |
| **Hunt** (`world/director/hunt.py`) | Trace is a parallel, same-idiom re-implementation (§7). |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | The slumped meat body is a `can_contest`-false free-action target — already covered. |
| **Intel / wanted** (`world/director/intel.py`) | The wanted record IS a hackable file (§10) — clear/forge flags. |
| **Stealth / theft** (`STEALTH_AND_DETECTION_SPEC`) | Hardware theft is the meat route to a net prize (§2); net "noise" mirrors stealth's contest. |
| **Identity** | Net actions key on apparent-UID; a decker can be traced-as-presence without being named (voice/face parallel). |
| **Crafting / 3-D printer** | Schematics are stealable/printable files (§2, §10). |
| **Radio** (`RADIO_COMMS_SPEC`) | Reserved cross-phase tap: a decker reads/spoofs radio traffic from the net (§9 there). |
| **Coordinates / verticality** | Hosts live at real coords in towers — the shared high-rise dependency that gates the build. |

## 13 · Risks & open questions

* **Skill-vs-Intellect timing.** Intellect gates the palette now; confirm the
  additive path to a real decking skill so the later swap doesn't rewrite
  content.
* **Program-noise tuning.** How much does instruction quality vs. deck grade
  vs. hop count each weight the trace? The fun is in that curve; tune in play.
* **Griefing via the crime DB.** Forging wanted flags is powerful — needs
  friction (high ICE, traceability, a reversal path) so it's a heist, not a
  toy.
* **Solo-loop isolation.** A decker in the net must still feel the room
  (their meat body is exposed) — the two-body tension has to be legible to
  both the decker and whoever's standing over their body.
* **Offline/async.** Do hosts persist state between runs (a deleted file stays
  deleted, a planted backdoor waits)? Lean: yes — the world-as-database only
  matters if edits stick.

## 14 · Build ladder (all gated on the phase layer)

| Phase | Scope | Depends on |
|---|---|---|
| **0** | `PHASE_LAYER_SPEC` built (net phase, two-body, gate) | vertical/coordinate world |
| **1** | The program layer standalone: composer (`operate`-style) + hand-typed authoring, instruction palette, Intellect/library unlock, deck size/speed budget — **authorable and dry-runnable before the net exists** | — (can prototype ahead) |
| **2** | Topology + run loop: hosts, bounce, connect/crack/navigate/files/copy/logs | phase 0 |
| **3** | Trace (the net hunt) + ICE | phase 2, hunt.py |
| **4** | Data-as-target: crime-DB edits, schematics→printer, sabotage | phase 2, intel/crafting |
| **5** | Gigs over the BBS; radio cross-tap; economy | growth-direction systems |

Phase 1 is the one piece that can be **prototyped now** — the programming
model doesn't need the net to exist to be authored and tested. Everything
else waits for the vertical world.
