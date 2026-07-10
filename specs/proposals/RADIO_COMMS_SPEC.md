# Radio Comms Spec — The Colony's Primary Communications

> **Status:** 🚧 **PHASE 1 CORE SHIPPED (2026-07-04): player-facing radio is LIVE** — `world/radio.py` (single staff-locked channel + device-gated voice echo), `Radio` typeclass + `WALKIE_TALKIE` prototype, `transmit`/`xmit`/`xm` + `to <radio>,` retarget, `tune <device> to <freq|scan>`, `toggle <device> [on/off]`, state-aware look-readout (frequency shown only when powered). Voice-attributed (recognition on the air, modulator-defeatable), hearing-gated, every powered carried radio receives its band (scan catches all, freq-tagged). **WITNESS LINK + BOT TRANSCEIVERS ALSO SHIPPED (#1009):** the witness spawns with a real `WALKIE_TALKIE` on the **emergency band (911MHz)** and `witness_report` gates on it — snatch/break/KO = no report (a physical interdiction beside killing them; robbing them nets a walkie pre-tuned to the cop channel). Security bots carry a built-in **comms module** (ear/antenna augment organ, `factory_fit_comms`, like the riot gun) tuned to 911MHz — they hear the net via `comms_organ_frequency`; destroy/harvest the ear and the bot goes deaf (EMP/mute seam via medical hit-location). **ACQUISITION PLACED (2026-07-04):** the Colonial Armory stocks `WALKIE_TALKIE` at 0 tokens (live shop object) and ~1-in-3 gangers carry one (`chance_stock`) — Phase 1 is now player-obtainable end to end. **NPCs DOGFOOD THE REAL VERBS (2026-07-04):** the witness readies and calls it in through the actual player commands — `wield magpie` / `toggle magpie on` / `tune magpie to 911MHz` at spawn, `xmit <report>` + `emote` at report — never a backdoor `transmit()` call or direct `db` write. The NPC path is identical to the player path (level playing field; NPCs lead by example). Surfaced + fixed a real bug in the process: band matching is now **case-insensitive** (`world.radio.same_band`) so a band typed `911mhz` still reaches bots/constants stored as `911MHz`, while `tune` preserves the typed case for clean display. **PHASE 2:** antennae/range/coverage, battery, jamming, encryption (gated on verticality). Original scoping below.
>
> **PHASE 1 SCOPED & DECIDED
> (2026-07-03, §7): buildable now, vertical-independent** — devices +
> channel-system backend + voice-over-radio + the witness-report and
> dispatch-order links. Phase 2 (range/antennae/coverage) waits on the
> high-rise buildout. Designs **radio** as Gelatinous's
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
| **Base station** | fixed room object | strong range; where an org's traffic converges (security base = the intel-sync point). **✅ FIRST BUILD (2026-07-10):** `BASE_STATION` console at the security base (heartbeat-installed, idempotent) — **dispatch's voice**: deterministic template acks on 911MHz for every event (`Dispatch copies — an assault at Cobb Street. Unit responding.` / `No units available.` when the pool drains — the finite pool made audible). Switch it off or wreck it and dispatch goes silent (the sabotage seam, live). No LLM for acks — and **the ANSWERING brain SHIPPED (2026-07-10)**: traffic that names dispatch ('dispatch/control/base') from a non-NPC speaker gets an answered line via the **civic LLM lane** (`CIVIC_LLM_URL` — a second OpenAI-compatible endpoint; an on-device AFM shim serves it today at ~0.4s warm, but the game never learns Apple exists — swap by URL). **OPERATOR v1 (2026-07-10): the far end is a PERSON.** Vess — an embodied GM-lane NPC seated at the base (heartbeat-ensured) — is the voice of dispatch: acks and answers transmit AS HER (smoky rasp on the air, voice-recognisable/rememberable/modulator-defeatable), her register carried by operator-voiced exemplars in the civic instructions. Dead/unconscious/kidnapped/absent operator = the console's automation voice takes over — a difference anyone on the band can hear; the ack beat varies 1.5–3.5s (a human pause, not a trigger). Rotating shift cast = the agreed follow-up. Template fallback is STRUCTURAL (model failure/refusal → canned line, never silence); loop-guarded (NPC/unit/own traffic never answered); 10s cooldown; availability count grounds the reply |
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
| Unit ↔ base | bots report/receive via built-in transceivers | EMP/destroy the transceiver component; *urgent* traffic rides radio |
| Intel-sync | **NOT radio (decided 2026-07-03): the force-wide intel/wanted sync is NET-driven** — it's a file on a host (`DECKING_MATRIX.md` §2/§10); radio carries voices, the net carries databases | hack the host (the marquee decking run), not the airwaves |
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

## 6 · Phase 1 — scoped & decided (2026-07-03)

Everything vertical-independent; range is **abstracted** (Option A): the
*device* is the gate, not the distance — a functional, tuned walkie reaches
the network (assumed present); a snatched/broken/absent one doesn't. Phase 2
physicalizes range with antennae/coverage when the high-rises exist.

### 6.1 · Backend — ONE channel, the walkie sorts it out

**A single staff-locked Evennia Channel ("Radio") carries ALL traffic**;
each transmission is tagged with its **frequency**, and the tuned walkie
filters at echo time (decided 2026-07-03 — one channel beats
channel-per-frequency):

* **Why one**: frequencies are a *dial* — an effectively continuous number
  space (scanning / lucky guesses) — so per-frequency channels would mean
  unbounded channel creation/GC. One channel makes frequency pure data:
  retuning is a device attribute write, no subscription churn. And the
  admin gets **one log**: the entire grid as a single chronological
  stream — `[447] <Name> (<voice>): "…"` — which is both the live monitor
  and the forensic timeline. Per-band views are a filter, not an object.
* **Admin/builder view** — subscribe to the one channel: raw readout with
  Name, Voice/attribution metadata, and Frequency per line. History,
  persistence, and staff distribution come free from the channel system.
* **Player view** — players NEVER subscribe. A walkie tuned to a frequency
  **echoes** matching traffic, re-rendered through the say/voice rails: the
  speaker's **voice phrase**, **voice recognition** (recognisable on the
  air; a modulator defeats it), **hearing-gated**, attributed **by voice
  only** (never sight). "A gravelly voice crackles over the walkie: …"

  **AMENDED (2026-07-06) — the four-perspective display model.** The
  original text scoped the echo "to its holder"; the physical stance (§2.4
  literally says *speaker grille*) demands more, so:
  1. **Speaker** — `You transmit on 911MHz: "…"` (unchanged).
  2. **Speaker's ROOM** — two registers (playtest-decided 2026-07-07):
     `xmit` is keying the handset and speaking **LOW** — each bystander
     rolls to catch it (listener Intellect vs speaker Resonance, the
     voice-discern pairing) and the MARGIN grades comprehension
     (playtest-refined 2026-07-07): a clean win hears every word, an even
     ear catches letter-dropped fragments ("c-ver the b-ck d--r" — shape
     and punctuation intact, letters lost), a bad miss gets only the act
     ("mutters something into the radio"). An NPC brain's speech payload
     carries exactly the fragments that listener heard, not the secret. `to <radio>, <message>` is **openly**
     addressing the device — ordinary room speech, everyone hears (the
     full say rails, `says into the radio,`). Whisper stays contentless
     to bystanders; the mutter sits between whisper and say.
  3. **Remote listeners** — the crackle line, voice-only attribution,
     scan-tagged (unchanged).
  4. **A receiving walkie's ROOM** — the grille is a speaker: traffic is
     audible to everyone in the radio's room (carried → the holder's room;
     lying on the floor → its room), hearing-gated per observer ("A radio
     nearby crackles…" for non-holders when deaf). Carrying a live radio
     is a stealth liability — as the `toggle` help always promised.
     **Comms ORGANS stay internal** (in the ear = private to the unit).
     **DOUBLE RENDER (2026-07-07, playtest-decided — replaces the earlier
     same-room suppression):** a matching radio beside the speaker DOES
     echo. With xmit's low voice this is load-bearing counter-play: you
     may fail to catch the mutter, but if your handset repeats it you've
     just learned you share their band — and heard the content anyway.
* **Transmitting** — `radio <message>` posts to the channel *through the
  device*, tagged with the device's frequency; every matching-tuned walkie
  echoes it. No device, no voice on the air.

### 6.2 · Devices & acquisition

The **walkie-talkie item**: held/carried, powered, tuned to one frequency.
Acquisition = **all three**: vendor purchase (the store), loot (gangers /
security units carry them), and spawn kit where role-appropriate. Snatchable
via the existing theft/wrest machinery; breakable via ordinary damage.

**Shipped placement (2026-07-04):** the **Colonial Armory** stocks
`WALKIE_TALKIE` at **0 tokens** (a live builder change to the hand-built shop
object, not a prototype), and the **ganger** civilian role carries one on a
**~1-in-3** roll (`chance_stock` in `world/director/civilians.py`) — a
loot/frisk/steal path. Witnesses already spawn with an emergency-band walkie
(#1009). Broader vendor/loot spread waits on Phase 2 geography.

### 6.3 · Tuning & discovery

`radio/tune <frequency>` — a walkie hears only its tuned band. **The dial
reads megahertz (DECIDED 2026-07-06):** a band is a NUMBER, 1–999.9 MHz at
one-decimal resolution (~10k channels — searchable, not infinite), stored
canonically (`912` → `912MHz`; `normalize_band`); prose is refused ("'banana'
isn't a frequency"). `same_band` normalizes both sides, so legacy loose
values keep matching. Discovery is
**scanning** (sweep bands and listen), **lucky guesses**, and **captured
walkies** (a lifted security handheld arrives tuned to their band — the
listening post). Secrecy is procedural, not cryptographic (encryption is a
later phase).

### 6.4 · The dispatch chain in Phase 1

* **Witness report** — the marquee: a witness NPC transmits its report from
  its OWN walkie on a public/security band. **Snatch or break the device
  before it keys up and the report never goes out** — silence-the-witness,
  literal, riding theft + dispatch (both live).
* **Dispatch orders** — the force runs its own frequency: base-to-units
  traffic rides it (tunable by anyone who finds the band — scanner play
  against security is on from day one).
* **Intel-sync** — explicitly NOT radio (§3): net-driven, owned by
  `DECKING_MATRIX.md`.

### 6.5 · Explicitly deferred to Phase 2+

Antennae/repeaters/coverage holes, real coordinate range, the Drifts-dark
rule, jamming devices, **power/battery**, encryption/scrambling, and the
robot built-in-transceiver attacks (ride the robot-component work).

## 7 · NPC radio comprehension — ✅ SHIPPED (2026-07-04)

> **Shipped as designed, all six sub-sections.** Delivery attaches the
> say-rails structured payload (`speech=` for hearing listeners only) +
> `radio_frequency`/`radio_elected`; `LLMNpcMixin._hear_radio` gates exactly
> like room speech (named → answer; broadcast → elected unit only —
> deterministic lowest-dbref election in `_deliver`; NPC-sourced →
> observe-only loop guard; chatter → buffer + rare `radio_ambient`
> volunteer). Radio turns attribute by VOICE (`radio_voice_handle`, shared
> with the echo render), carry no visual perception, and scope memory to the
> VOICE identity (`voice:<uid>` subject threaded through storage so nothing
> cross-sensory leaks). Transmit = the `radio` action tool (granted to
> `security`; withheld from `colonist`) → the REAL `xmit` command, whose new
> no-handheld fallback keys a built-in comms organ (`transmit_organ`) — so
> bots and any future implanted player transmit through the identical
> command. Persona card advertises the device + band. Turn framing makes
> air-vs-room unambiguous (§7.6). Physical gates hold throughout: delivery
> is the hearing gate, the command refusal is the mute gate.

Phase 1 built the physical medium and a scripted witness one-shot, but radio
does **not** yet reach the NPC brains. Today: an LLM NPC with a powered walkie
hears nothing (radio `.msg` carries no `speech` payload → `at_msg_receive`'s
`if not speech: return True` drops it); it has no way to key up; and security
bots *receive* the report but no behaviour consumes it (dispatch rides
`raise_event`, independent of hearing). This slice bridges radio ↔ the LLM-NPC
layer. **Payoff:** a dispatcher who answers over the air, a fixer who calls a
job in, a companion you can raise from across the city, secbot chatter on the
band — all through the real device, all voice-attributed.

### 7.1 · Hearing — radio into the brain

A radio transmission delivered to an LLM NPC must reach `at_msg_receive` as
**heard words tagged as radio** — distinct from in-room speech, so the model
knows the source is the *air* (a remote voice), not the person beside it. The
turn frames it that way ("over the radio, <voice> says: …"). Attribution is
**voice-only** (the echo render's rule): the NPC recognises a known voice
(voice memory) or hears "an unfamiliar voice"; a modulator defeats it. The NPC
hears **only the band(s) its device is tuned to** — a unit on 911MHz hears
911MHz, not the whole spectrum.

### 7.2 · Gating (the crux — saturation is the enemy)

Radio reaches *every* listener on a band at once, so ungated it would fire an
LLM turn on every NPC per squawk and saturate the single-threaded model. Reuse
the room-speech discipline exactly:

* **Directed radio** — the transmission names this NPC (callsign / name / role
  — "Unit 7, respond"; "all units"). Eligible to answer, subject to the
  directed cooldown.
* **Ambient radio** — general chatter. **Observe-only** into the action buffer
  (no LLM call), with the rare gated volunteer (ambient cooldown + roll) —
  mirrors ambient poses/room-speech.
* **Loop guard** — an **NPC-sourced** transmission is never LLM-reacted (the
  existing `_is_npc_speaker` guard). This is load-bearing: the witness's
  report and any bot chatter are NPC-sourced, so bots hearing the witness
  don't spin up turns, and two NPCs on a band can't ping-pong.
* **"All units" de-confliction** — a broadcast addressed to many must not make
  *all* of them answer. One responds (nearest / a single elected speaker),
  the rest observe — this is the multi-NPC de-confliction the LLM spec parks
  as future; radio is its first forcing case.

### 7.3 · Transmitting — the NPC keys up

Through the **real command** (the execute-cmd mandate), never a backdoor: a
`radio`/`transmit` **action tool** in the LLM turn schema (archetype-scoped —
granted to dispatcher/security/fixer/companion, withheld from a mute
colonist), routed to `transmit`/`to <device>,`. The persona/context carries the
NPC's radio state ("you carry a walkie tuned to 911MHz", or the bot's comms
organ) so the model knows it *can*. On a radio-heard turn the model **chooses
its channel** — answer over the air (the radio tool) or speak in the room
(normal `say`) — a startled bystander mutters aloud; a dispatcher keys back.

### 7.4 · Security bots come along for free

Secbots are already `LLMNpc` + a comms organ (they receive). Wiring §7.1–7.3
gives them **gated radio voice** with no new plumbing: a bot hears a report and
its LLM brain may key up ("Unit responding, en route") — *flavour* — while the
**deterministic dispatch (`raise_event` + hunt) stays authoritative** for the
actual action. Clean split: the director moves the body, the LLM works the mic.

### 7.5 · The physical gate holds

No new perception path around the device: an NPC hears/speaks radio only with a
**powered, tuned** device (walkie or intact comms organ). Snatch the walkie,
break it, destroy the ear → the NPC goes deaf/mute exactly as the mechanics
already enforce for the witness and the EMP-muted bot. Comprehension rides the
same physical gate players do.

### 7.6 · Risks

* **Saturation / cost** — the gating (§7.2) is the whole game; radio turns
  count against the LLM budget like any other, and a busy band could be
  expensive. Ambient-observe-only + de-confliction bound it.
* **NPC↔NPC loops** — the `_is_npc_speaker` guard must cover radio-sourced
  speech, or dispatcher↔unit chatter ping-pongs.
* **De-confliction** — "all units" needs a single-answerer election; getting
  this wrong is either silence or a chorus.
* **Channel choice** — the model conflating radio-back vs room-speech would
  have a bot muttering to an empty street or answering a face-to-face question
  over the air. The turn framing (§7.1) must be unambiguous.

## 8 · Risks & open questions

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
