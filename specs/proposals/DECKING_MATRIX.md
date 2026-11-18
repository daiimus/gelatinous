# Decking & the Matrix — Runs, Traces, and the Net's Game Loop

Decking is the net's game loop: a decker jacks in, bounces through nodes,
breaks into a host, works under a trace, cleans the logs and jacks out. This
spec is a design draft, spec-first and built when the world is ready; the
design sharpens as the colony fills in. Its substrate is `PHASE_LAYER_SPEC`
(net = a phase over the same geography; the two-body model; the single
perception gate), which is 📋 UNBUILT (no issue). Everything here waits on
that phase layer, except the program layer (§14 phase 1).

The design takes the classic net-runner loop (bounce → intrude →
work-under-a-trace → clean-logs → jack-out), which reduces cleanly to a small
set of discrete commands — the hacking genre is *already* a text game. That
loop and CLI shape are the skeleton. Two things make it ours: a
**roll-your-own programming layer** (§6) and one doctrine: **everything is a
file** (§2). Source material is paraphrased, not cited.

---

## 1 · Why the discrete-command model

The reduction of the genre to a handful of operations shows four things that
map straight onto a MUD:

1. **A discrete command surface is enough.** A few dozen operations carry the
   whole game — connect/bounce/navigate, file & log ops, LAN scan, cracking,
   tracing, mail/jobs/boards, hardware & software acquisition. The GUI was
   always incidental to the loop.
2. **Timed async operations are the tension.** Cracks and copies take real
   seconds while a trace advances — tension without twitch. The game already
   has this shape: a channeled act (`world/channeled.py` `begin_channel`,
   which `sabotage` uses) runs for a set time, shows a visible tell, can be
   broken off, and reports how far it got. The director heartbeat ticks the
   deterministic side.
3. **Layered navigation** (map → node → console) mirrors rooms → objects →
   commands. The MUD *is* the interface metaphor; nothing to invent.
4. **Jobs close the loop** (accept → run → deliver → get paid) — which is
   Gelatinous's gig/favor direction verbatim.

The starting command set is a **CLI vocabulary**: `connect`, `bounce`,
`scan`, `navigate`, `files`, `copy`, `delete`, `logs`, `crack`, `trace`,
`mail`, `jobs`, `board`, `balance`, `buy`. Beside it sits a **hardware axis**
(CPU / memory / modem as capability tiers). What goes on top — the
programming layer and the file doctrine — is what makes it Gelatinous rather
than a port.

## 2 · Everything is a file (the doctrine)

The net is not a minigame bolted beside the world. It is the **data layer of
the world**, and in that layer *everything is a file*:

* A **gig / contract** is a file on a board or a fixer's host.
* A **contact / dossier** is a file (who knows whom; a face-to-name link).
* A **schematic** — clothing, a weapon, a cyberware mod — is a file you feed a
  **3-D printer** to fabricate the real object (ties crafting to the net).
* The **wanted record** is a file. `world/director/intel.py` stores it; a
  decker who cracks the right host can **clear their own wanted flag** or
  **frame an enemy** by writing one in. Crime and reputation gain a digital
  attack surface. The record is one `ServerConfig` row holding one entry per
  apparent UID (a count of offences and the last crime). A bot carries its
  own unsynced sightings (`db.local_sightings`) and merges them into the
  force-wide record only when it stands in its post room
  (`world/director/intel.py` `sync_bot_intel`), so an edit to the force-wide
  record leaves those sightings in place.
* **Currency, logs, mail, door/camera ACLs, a bot's directive table** — files.

Two consequences make this a first-class play space:

* **You can steal data _or_ hardware.** Copy the schematic file (data theft,
  quiet, duplicable) *or* rip the physical component out of a machine in
  meat-space (hardware theft). Two routes to the same prize, different risk
  shapes. Hardware theft is work this spec proposes, not a layer it can lean
  on (📋 UNBUILT, §10). `STEALTH_AND_DETECTION_SPEC` §6.2, "Theft (steal &
  pickpocket)" (`commands/CmdTheft.py`), is person-to-person theft only: it
  refuses any target without `get_sdesc` and lifts loose items from what
  someone is carrying. Nothing pulls a component out of a fixed machine:
  `sabotage` (`commands/CmdBreach.py`) wrecks infrastructure rather than
  yielding a part, and `harvest` is surgical, against a body or robot
  chassis.
* **Editing a file edits the world.** These files are the same objects the
  deterministic systems read (the wanted record, a gig board, a printer's
  queue), so changing the file *changes reality* — no separate "apply" step.

Design rule: a net-file is a real game object with a phase-`net` presence and a
meat-space twin (the machine that hosts it). Perceiving/reading it is
phase-gated; changing it goes through the same validation the meat systems use.

## 3 · The stack (what's substrate, what's this spec)

| Layer | Owner |
|---|---|
| Net as a phase; two-body model | `PHASE_LAYER_SPEC` — 📋 UNBUILT (no issue) |
| Perception gate (`can_perceive` / `filter_present`, which stealth uses today) | `world/perception.py` ← `PHASE_LAYER_SPEC`; its phase clause is 📋 UNBUILT (no issue) |
| Everything-is-a-file doctrine (§2) | this spec — draft |
| Net topology over real geography (§4) | this spec — draft |
| The run loop: bounce, intrusion, logs (§5) | this spec — draft |
| **Programs — roll-your-own (§6)** | this spec — draft |
| Trace = the hunt, pointed at the net (§7) | this spec ← `world/director/hunt.py` — draft |
| ICE = deterministic NPCs (§8) | this spec ← robot/mob pattern — draft |
| Deck & components = gear (§9) | this spec ← parked-stats stance — draft |
| Data as target (§10) | this spec ← `intel.py`, crafting — draft |
| Jobs = gigs over a board (§11) | this spec ← growth direction — draft |
| Cross-phase effects (cameras, doors, radio taps) | `PHASE_LAYER_SPEC` §7/§9 — reserved |

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

## 5 · The run loop

1. **Jack in** — from a fixed terminal or a portable **deck**. The body slumps
   in meat-space. For it to be a **free-action target**, jacking in must set a
   state the trust check reads as helpless: an unconscious-equivalent medical
   flag or a restraint-equivalent. `can_contest` (`world/consent.py`) returns
   False only for the dead, the unconscious and the restrained (grappled, or in
   restraint furniture); a slumped decker who is medically awake and not
   grappled can contest (`PHASE_LAYER_SPEC` §5.3). 📋 UNBUILT (no issue).
   Guard your meat, or someone frisks or knifes it while you're under.
2. **Bounce** — route your entry through public/compromised nodes before the
   target. Your bounce path is *real* — the literal sequence of net-rooms your
   connection traverses — and **the trace walks it back**. More hops = longer
   trace runway but slower work; the classic tension.
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

The genre convention is "buy `Cracker_v3.exe`, click it." **We let you write
it.** A decker's tools are **programs they author** from a palette of
instructions. A program's sophistication is bounded by what instructions the
decker can use and what their deck can run. This replaces "buy a better tool"
with "*write* a better tool," which fits the gear/favor progression stance and
makes hacking a craft.

### 6.1 · The model

* A **program** is an ordered list of **instructions** (steps that run top to
  bottom), each an operation with **typed arguments validated as you build**
  (a malformed program won't save).
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
  proper **decking skill** replaces/augments this later; the seam is designed
  so that swap is additive, not a rewrite. Some instructions are additionally
  gated on **acquired knowledge** — an instruction library you buy, find, or
  extract — so an unlock can also be *a place you went and a thing you did*,
  keeping it true to gear/favor.

  The skill board is ruled final at fourteen ratings
  (`SKILLS_AND_DESIGNATION_SPEC` §5, ruled 2026-08-19). The ratings live in
  `world/manifest.py`, seeded at creation by `ensure_manifest`/`seed_skills`
  (called from `commands/charcreate.py`, `web/website/views/characters.py`,
  `world/souls/population.py`), with `check_value(char, skill)` as the check helper. Decking's rating is
  already named: **`systems`**, Intellect-governed — "everything done through
  a machine's interface: decking, consoles, radio & broadcast procedure,
  electronic locks". The XP/dice layer above the snapshot is not built, so the
  Intellect-now/skill-later seam still holds. Whether `systems` is the later
  decking gate is not decided (§13).
* **What your deck can run** — the **hardware axis** (§9): CPU sets execution
  speed, memory sets program size, and the rig's grade sets how much **heat**
  (trace pressure) it can absorb before it cooks. **Better rigs handle more
  heat; rare components are harder to acquire** — the scarcity is the
  progression.

Net: Intellect (→ skill) opens the *vocabulary*; the rig sets the *envelope*.
A brilliant decker on a cheap deck writes elegant programs they can't run big;
a rich one on a monster rig runs brute-force garbage that still works.

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

The rig is the gear axis (the hardware model, our scarcity):

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
* **Steal hardware** — the meat-space route: rip the component out of the
  machine. 📋 UNBUILT (no issue): no verb does this; `STEALTH_AND_DETECTION_SPEC`
  §6.2 theft is person-to-person only (open question, §13). Two paths, one
  prize.
* **Edit the crime database** — clear your own wanted flag, forge an enemy's
  (`intel.py` is the file). High-value, high-ICE — the marquee corp-host run.
* **Sabotage** — flip a door/camera ACL, corrupt a printer queue, brick a
  bot's directive table, mute a base station (radio §5 cross-tap).
* **Plant / forge** — write a file into a host: false evidence, a backdoor, a
  logic bomb.

## 11 · Jobs — gigs over a board

A decking contract is a **gig** (growth direction) that lives as a file on a
board or fixer host: accept → run → deliver the payload (a copied file, a
confirmed edit) → get paid in tokens, gear, or favor. The net gives the
gig/favor economy its first rich, repeatable content loop and a reason to own
a deck.

## 12 · Integration seams

| System | Relationship |
|---|---|
| **Phase** (`PHASE_LAYER_SPEC`) | The substrate: net = phase, two-body model, perception gate. Build FIRST. |
| **Hunt** (`world/director/hunt.py`) | Trace is a parallel, same-idiom re-implementation (§7). |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | The slumped meat body should be a free-action target. 📋 UNBUILT (no issue): jacking in must set a helpless state that `can_contest` reads (§5 step 1; `PHASE_LAYER_SPEC` §5.3). |
| **Intel / wanted** (`world/director/intel.py`) | The wanted record IS a hackable file (§10) — clear/forge flags. |
| **Stealth / theft** (`STEALTH_AND_DETECTION_SPEC`) | Hardware theft is the meat route to a net prize (§2); net "noise" mirrors stealth's contest. |
| **Identity** | Net actions key on apparent-UID; a decker can be traced-as-presence without being named (voice/face parallel). |
| **Crafting / 3-D printer** | Schematics are stealable/printable files (§2, §10). |
| **Radio** (`RADIO_COMMS_SPEC`) | Reserved cross-phase tap: a decker reads/spoofs radio traffic from the net. **The security intel-sync is NET-driven, not radio** (decided 2026-07-03): the wanted/intel database is a hosted file — radio carries voices, the net carries databases. Today the sync is physical: a bot's sightings merge into the force-wide record only in its post room (§2, `sync_bot_intel`). Moving that record onto a net host is 📋 UNBUILT (no issue). |
| **Coordinates / verticality** | Hosts live at real coords in towers. The coordinate volume (`world/spatial/`) and the towers exist, so they no longer gate the build; the remaining gate is `PHASE_LAYER_SPEC`. |

## Physical interface layer — TERMINALS

`typeclasses/terminals.py` holds fixed machines operated through the ordinary
`press`/`push` grammar (`press rent on kiosk`), sharing the
`at_press(presser, arg)` contract with elevator panels and call buttons:

* the Queen of Cups rental terminal — housing records are the grant files on
  cube doors (the shape of `VERTICALITY_AND_BUILDINGS_SPEC` §2.2, "Biometric
  access — everything is a file"; that spec's §2.5 is the housing guarantee
  `typeclasses/terminals.py` cites);
* the decant jumpsuit dispenser (`SleeveDispenser`);
* the sleeve-policy terminal (`InsuranceTerminal`), whose policy records live
  in `world/insurance.py`, one `ServerConfig` row per sleeve UID — a second
  record that becomes a net file when this spec builds.

When this spec builds, these are the boxes whose records become net-visible
files. The buttons remain the street-level interface; the truth moves to the
host.

## 13 · Risks & open questions (not decided)

* **Skill-vs-Intellect timing.** Intellect gates the palette now; confirm the
  additive path to a real decking skill so the later swap doesn't rewrite
  content. OPEN (#3335): is `systems` that skill, or is a separate decking
  rating still wanted?
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
* **Hardware theft verb (OPEN, #3335).** Does ripping a component out of a
  fixed machine grow out of the stealth theft contest
  (`STEALTH_AND_DETECTION_SPEC` §6.2), or get its own verb? Nothing does it
  today: `steal` and `pickpocket` (`commands/CmdTheft.py`) refuse any target
  without `get_sdesc`. The verb itself is 📋 UNBUILT (no issue) (§10).
* **Phase 1 timing (OPEN, #3335).** Is the program layer still to be
  prototyped ahead of the net (§14), or is the document dormant until the
  phase layer?

## 14 · Build ladder (all gated on the phase layer)

| Phase | Scope | Depends on |
|---|---|---|
| **0** | `PHASE_LAYER_SPEC` built (net phase, two-body, gate) | — |
| **1** | The program layer standalone: composer (`operate`-style) + hand-typed authoring, instruction palette, Intellect/library unlock, deck size/speed budget — **authorable and dry-runnable before the net exists** | — (can prototype ahead) |
| **2** | Topology + run loop: hosts, bounce, connect/crack/navigate/files/copy/logs | phase 0 |
| **3** | Trace (the net hunt) + ICE | phase 2, hunt.py |
| **4** | Data-as-target: crime-DB edits, schematics→printer, sabotage | phase 2, intel/crafting |
| **5** | Gigs over a board; radio cross-tap; economy | growth-direction systems |

Phase 1 is the one piece that can be **prototyped now** — the programming
model doesn't need the net to exist to be authored and tested. Everything else
waits for the phase layer. The coordinate volume and the vertical world are
not the gate; `PHASE_LAYER_SPEC` is.

## Related documents

`PHASE_LAYER_SPEC` (substrate), `TRUST_AND_CONSENT_SPEC`,
`STEALTH_AND_DETECTION_SPEC`, `RADIO_COMMS_SPEC`,
`SKILLS_AND_DESIGNATION_SPEC`, `VERTICALITY_AND_BUILDINGS_SPEC`,
`SPATIAL_COORDINATE_SYSTEM_SPEC`.
