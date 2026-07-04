# Decking Spec — Runs, Traces, and the Net's Game Loop

> **Status:** 📋 **DRAFT FOR DISCUSSION** — not implemented, not yet fully
> designed. The net's *substrate* is `PHASE_LAYER_SPEC` (net = a phase over
> the same geography; the two-body model; the single perception gate). This
> spec designs the **game** that runs on that substrate: what a decker
> actually does, minute to minute. Primary reference:
> **uplink-headless-mod** (https://github.com/hosler/uplink-headless-mod) —
> a reverse-engineered, GUI-stripped *Uplink* whose engine reduces the
> entire hacking genre to ~40 discrete commands over JSON. That reduction
> is the proof we need: **Uplink's loop is already a text game.** We adopt
> its loop (bounce → intrude → work under a trace timer → clean logs →
> jack out) and implement it on machinery Gelatinous has already built.

---

## 1 · Why Uplink, specifically

The headless mod demonstrates four things that map straight onto a MUD:

1. **A discrete command surface is enough.** Forty operations carry the
   whole game — connection management, file ops, cracking, tracing, log
   work, missions, shopping. No GUI required; the interface was always
   incidental to the loop.
2. **Timed async operations are the tension.** Cracks and copies take real
   seconds while a trace advances — tension without twitch. Evennia's
   `delay` and the director heartbeat already run this shape.
3. **Layered navigation** (map → node → console) mirrors rooms → objects →
   commands. We don't need to invent an interface metaphor; the MUD *is*
   one.
4. **Missions close the loop** (accept → run → deliver → get paid) — which
   is Gelatinous's gig/favor direction verbatim.

## 2 · The stack (what's substrate, what's this spec)

| Layer | Owner | Status |
|---|---|---|
| Net as a phase; two-body model; perception gate | `PHASE_LAYER_SPEC` | specced |
| Net topology over real geography (§3) | this spec | draft |
| The run loop: bounce, intrusion, tools, logs (§4) | this spec | draft |
| Trace = the hunt, pointed at the net (§5) | this spec ← `world/director/hunt.py` | draft |
| ICE = deterministic NPCs (§6) | this spec ← robot/mob pattern | draft |
| Deck & programs = gear (§7) | this spec ← parked-stats stance | draft |
| Jobs = gigs over the BBS (§8) | this spec ← growth direction | draft |
| Cross-phase effects (cameras, doors, radio taps) | `PHASE_LAYER_SPEC` §7/§9 | reserved |

## 3 · Topology — hosts live somewhere

Per the phase layer, the net overlays the **same geography**: a corp's host
is *in its building*, the colony's utility grid is *under its streets*.
Net-rooms (nodes/hosts) are rooms in `phase = net`, usually anchored to the
real coordinates of the machine that runs them:

* **Public grid** — the walkable net commons (the bounce fabric): exchange
  nodes roughly following district geography.
* **Hosts** — a facility's system: entry node (gate/ICE) → interior nodes
  (filesystems, controls, logs) — a small "building" in the net whose
  meat-space twin is a real place. **This is the high-rise dependency
  shared with radio: corporate towers are where the good hosts live.**
* **Dark nodes** — unlisted addresses (found, bought, extracted): the
  net's speakeasies.

Navigation is movement; the map is the room graph; "layered navigation"
comes free.

## 4 · The run loop (Uplink's, adapted)

1. **Jack in** — from a terminal or a deck (portable item; interior-grade
   chrome later). Body slumps in meat-space: a **free-action target** (the
   trust spec's contest predicate already covers this — guard your meat).
2. **Bounce** — route your entry through public/compromised nodes before
   the target. Your bounce path is real: it is the literal sequence of
   net-rooms your connection traverses, and **the trace walks it back**.
   More hops = longer trace runway;