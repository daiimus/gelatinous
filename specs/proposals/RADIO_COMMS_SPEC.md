# Radio Comms Spec — The Colony's Primary Communications

> **Status:** 📋 Proposal — not implemented. Designs **radio** as Gelatinous's
> primary means of communication: handheld walkie-talkies, base stations, and
> rooftop antenna infrastructure, carried over channels with coordinate-based
> range. Radio is the **carrier for the dispatch information chain**
> (`NPC_DISPATCH_AND_SIMULATION_SPEC` §5.1): witness reports, dispatch orders,
> and the base intel-sync all ride it — which is exactly why **disrupting it is
> first-class criminal play** (snatch the walkie, break the antenna, jam the
> band). Consumes the spatial substrate (distance/`rooms_within`) and the voice
> system (speech over radio is *voice*, with recognition intact).

---

## 1 · Intent

The colony has no cell network and no magic tells. When information moves, it
moves by **radio** — and when radio fails, information *stops moving*. Two
audiences:

* **Players** — carry handhelds, talk across the city, monitor channels
  (scanner play), coordinate heists, and *attack* the medium: eavesdrop, jam,
  break infrastructure, take a witness's walkie before the report goes out.
* **The simulation** — the dispatch chain's report link and the security
  force's intel-sync ride radio for real. No transmission → the force never
  learns. This replaces §5.1's acknowledged "magic report" placeholder with a
  physical, attackable system.

Design stance: **radio is physical.** Range is coordinate distance, antennae
are objects on rooftops, a walkie is a thing in a hand. Every property that
makes it useful makes it attackable.

## 2 · The model

### 2.1 · Devices

| Device | What it is | Notes |
|---|---|---|
| **Walkie-talkie** | handheld transceiver item | carried/held; **snatchable** (grab/steal/disarm play); tunable to a channel; limited range without the antenna network |
| **Base station** | fixed room object | strong range; where an org's traffic converges (security base = the intel-sync point) |
| **Rooftop antenna / repeater** | fixed infrastructure object, placed high (`Z > 0` rooftops) | extends channel coverage across the city; **breakable** (climb up and smash it) and **repairable** — a physical target for sabotage |
| **Built-in transceiver** | a robot component (chassis organ) | security bots report/receive via an internal radio — destroying that component (or EMP) mutes the bot without destroying it |

### 2.2 · Channels

Traffic is organized by **channel** (a small integer dial / named band):

* **Open channels** — public bands anyone can tune (colony chatter).
* **Org channels** — security's dispatch band, a gang's band. **Tunable by
  anyone with the number** — secrecy is *procedural*, not cryptographic, at
  v1 (scanner play: listen to security traffic if you find the band).
  Encryption/scrambling is a reserved later layer.
* A device holds one tuned channel at a time (v1); switching is a command.

### 2.3 · Range & propagation (the spatial consumer)

* **Direct device-to-device**: coordinate straight-line distance
  (`world/spatial.distance`) under a per-device range.
* **Network coverage**: within range of any **antenna/repeater** carrying that
  channel, coverage extends to the union of the antenna network — practically
  city-wide *while the antennae stand*. Kill the right antenna → a **coverage
  hole** (a district goes dark for that channel).
* **Vertical matters**: rooftop antennae see far; the Drifts (`Z < 0` — the future mines/sewers) is
  naturally radio-dark unless wired repeaters are placed — mines and tunnels
  are out of contact by default (ties to the mining/S&R fiction: a collapse
  cuts contact).

### 2.4 · Speech over radio — voice, not text

Radio speech reuses the **voice system** (`world/voice.py`) end-to-end:

* A transmission renders with the speaker's **voice phrase** — and listeners
  run **voice recognition** (`get_apparent_voice_uid` / voice memory) exactly
  as if hearing them in the room. You can be *recognized by voice on the air*
  — and a **voice modulator defeats that** (existing chrome).
* **Hearing-gated**: a deaf listener gets nothing from a speaker grille; the
  existing perception machinery applies.
* Radio voices are attributed by voice only — never by sight (you can't see
  the speaker). The "unrecognised voice = 'someone'" rule carries over
  naturally.

## 3 · The dispatch chain rides radio

Mapping `NPC_DISPATCH_AND_SIMULATION_SPEC` §5.1's links onto the medium:

| Chain link | Radio reality | Attack |
|---|---|---|
| Witness report | witness NPC transmits on a public/security band from their walkie | **snatch the walkie** from their hand; harm them first; no device → they must physically travel to report |
| Dispatch order | base broadcasts to units on the security channel | jam the band; coverage hole (break the antenna) → units in the dark |
| Unit ↔ base | bots report/receive via built-in transceivers | EMP/destroy the transceiver component; the intel-sync stays physical (return-to-base) but *urgent* traffic rides radio |
| Backup call | an engaged bot calls for reinforcement | mute the bot before it transmits (the no-trace window §5.1) |

A jammed/holed/deviceless link doesn't degrade gracefully into magic — **the
information simply does not arrive.** That hard rule is what makes sabotage
real play.

## 4 · Command surface (sketch)

* `radio <message>` — transmit on the held device's channel.
* `radio/tune <channel>` — retune.
* `radio/listen` (or just holding one powered on) — receive; traffic renders
  as heard speech ("A gravelly voice crackles over the walkie: …").
* Snatching/breaking rides existing systems: the grab/steal machinery
  (`STEALTH_AND_DETECTION_SPEC` §6.2 / wrest) for the walkie; ordinary object
  damage for antennae; jamming device TBD (§6).

## 5 · Integration seams

* **Dispatch / director** — the §3 mapping; replaces the report placeholder.
* **Spatial** — range/coverage from `distance` / `rooms_within`; antennae live
  at real coordinates (kill *this* rooftop → *this* district's hole);
  the Drifts dark-by-default.
* **Voice / identity** — §2.4; voice recognition + modulators carry over.
* **Perception** — hearing gates reception; a transmission into a room is an
  auditory event (stealth: a squawking radio gives you away).
* **Robots** — the built-in transceiver is a chassis component
  (`ROBOT_SPECIES_AND_MOB_SPEC`), destroyable/EMP-able.
* **Phase/net** — reserved: a decker tapping/spoofing radio traffic from the
  net (a cross-phase window; `PHASE_LAYER_SPEC` §7).
* **Gigs/factions** — org channels give gangs/employers a coordination
  texture; a gig can arrive over the air.

## 6 · Risks & open questions

* **Jamming device** — dedicated jammer item (area denial around a coordinate)
  vs. only infrastructure attacks at v1? Lean: v1 = antennae + walkie
  snatching only; jammer as follow-up gear.
* **Channel secrecy** — how do players *learn* a band (found notes, extracted
  from a captured walkie tuned to it, bought intel)? A captured security
  walkie being a listening post is great play — confirm intended.
* **Traffic volume** — NPC/dispatch chatter on open channels must be
  rate-limited so scanners are flavorful, not spammy.
* **Repair loop** — who fixes a broken antenna and how fast (a repair crew
  dispatch event — the director dispatching *maintenance* is a nice dogfood).
* **Power/battery** — do handhelds consume charge (the disposable-lighter
  pattern)? Lean: not v1.
* **Encryption** — later layer for org channels once scanner play needs a
  counter.
