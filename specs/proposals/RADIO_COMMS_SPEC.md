# Radio Comms Spec — The Colony's Primary Communications

Radio is Gelatinous's primary means of communication: handheld
walkie-talkies, base stations and rooftop antenna infrastructure, carried over
bands on a megahertz dial with coordinate-based range (`world/radio.py`,
`commands/CmdRadio.py`). Radio is the **carrier for the dispatch information
chain** (`NPC_DISPATCH_AND_SIMULATION_SPEC` §5.1): witness reports, dispatch
orders and unit traffic ride it — which is exactly why **disrupting it is
first-class criminal play** (snatch the walkie, break the antenna, jam the
band). It consumes the spatial substrate (distance/`rooms_within`) and the
voice system (speech over radio is *voice*, with recognition intact).

The design comes in two layers. **Phase 1** (scoped and decided 2026-07-03,
§6) is the device layer: devices, the channel backend, voice over radio, and
the witness-report and dispatch-order links. **Phase 2** (decided 2026-07-10,
#1128, §2.3) is range: distance, antennae and coverage.

---

## 1 · Intent

The colony has no cell network and no magic tells. When information moves, it
moves by **radio** — and when radio fails, information *stops moving*. Two
audiences:

* **Players** — carry handhelds, talk across the city, monitor channels
  (scanner play), coordinate heists, and *attack* the medium: eavesdrop, jam,
  break infrastructure, take a witness's walkie before the report goes out.
* **The simulation** — the dispatch chain's report link and the security
  force's unit traffic ride radio for real. No transmission → the force never
  learns. This replaces §5.1's "magic report" placeholder with a physical,
  attackable system.

Design stance: **radio is physical.** Range is coordinate distance, antennae
are objects on rooftops, a walkie is a thing in a hand. Every property that
makes it useful makes it attackable.

## 2 · The model

### 2.1 · Devices

| Device | What it is | Notes |
|---|---|---|
| **Walkie-talkie** | handheld transceiver item (`Radio` typeclass, `WALKIE_TALKIE` prototype) | carried/held; **snatchable** (grab/steal/disarm play); tunable to one band; powered on and off; limited range without the antenna network |
| **Base station** | fixed room object (`BASE_STATION`) | longer range when linked to an intact mast; where an org's traffic converges. The dispatch console is one (below) |
| **Rooftop antenna / repeater** | fixed infrastructure object, placed high (`Z > 0` rooftops) | extends a band's coverage across the city; **breakable** and **repairable** — a physical target for sabotage (§2.3) |
| **Built-in transceiver** | a robot component (chassis organ) | security bots report/receive via an internal radio — destroying that component (or EMP) mutes the bot without destroying it |

A device's look-readout is state-aware: the frequency shows only while it is
powered.

**Security bots' comms module.** A security bot carries a built-in **comms
module** — an ear/antenna augment organ fitted at the factory
(`factory_fit_comms`, like the riot gun), tuned to the emergency band,
**911MHz**. A bot hears the net through it (`comms_organ_frequency`).
Destroy or harvest the ear and the bot goes deaf; the EMP/mute seam falls out
of medical hit-location.

**The dispatch console.** The base station that is dispatch's board is kept
by upkeep in the **dispatch room** (`@patrol/dispatch` tag; the security base
is the fallback) — `ensure_base_station` in `world/director/population.py`,
idempotent, run at heartbeat start. Dispatch answers from the Constabulary's
secure 2nd floor; units respawn at the security base, the Colonial Landing
Pad.

* **The far end is a PERSON.** The dispatch operator is an embodied GM-lane
  NPC seated at the console. Three shifts staff it (Petra/Kiro/Ines, #2233);
  rotating the shift cast is the agreed follow-up. A dead dispatcher is a
  vacancy on the dispatch post (#3667), returned by her own sleeve policy or
  replaced by the sweep; the security base is not her respawn point.
* **Dead/unconscious/absent operator = SILENCE** (2026-08-23, #2223/#2228).
  The automation voice is deleted, not disabled: the colony is operated by its
  people, and an unmanned emergency line is the setting rather than a hole in
  it. The console neither speaks nor dispatches; whoever is seated at it
  judges the call and answers in their own voice through the real `xmit`, so
  nothing anywhere has to check whether the desk is empty — nobody is there
  to hear it. *(Overturned intention: the
  console was first built to speak deterministic template acks itself, with
  a canned fallback line on model failure; the 2026-08-23 ruling replaced
  that with silence.)*
* **Failure is silence at every layer.** `_try_llm_reply` defaults
  `on_fail=_llm_silent`; `consider_radio_report` is silent on every failure;
  `AnsweringFixture`: "Silence is the honest report". The canned
  `DESK_FALLBACK_LINES` are `desk_discipline` substitutions that
  `salience.filter_for_duty` applies to a line the model DID produce (phantom
  units, promises to leave the chair); they are not a failure fallback.
* **Answering a call.** `LLMNpcMixin._hear_radio` defers emergency-band
  traffic heard at a seated board to `world/souls/salience.py`
  `_work_radio_traffic`, which judges the call and then calls `answer_traffic`
  → `_try_llm_reply(…, "radio")` — the NPC's ordinary GM lane. The gate is
  "seated at a powered 911MHz board". The civic LLM lane (`CIVIC_LLM_URL`, a
  second OpenAI-compatible endpoint, swappable by URL; the game never knows
  which backend serves it) serves the structured
  report classifier (`request_civic_verdict`, `world/director/radio_report.py`)
  and the combat reflex (`world/llm/reflex.py`), not the reply. NPC, unit and
  own traffic is never answered (loop guard). The availability count grounds
  the reply. The directed radio turn rides `LLM_DIRECTED_COOLDOWN = 4.0`
  (`typeclasses/llm_npc.py`) and `AnsweringFixture.ANSWER_COOLDOWN = 4.0`
  (`typeclasses/items.py`); `consider_radio_report` is deliberately not gated
  by any answer cooldown.
* **Acks.** No LLM writes an ack. When units roll there is no dispatch line: each responder acks in
  its own voice via `_unit_ack` (`Unit <id> responding — <where>.`,
  staggered). The dispatch template survives only for a drained pool — the
  finite pool made audible — and the operator airs it through `xmit`
  (`_transmit_ack`): `Dispatch copies — <what> at <where>. No units
  available.` The ack beat varies 1.5–3.5s (a human pause, not a trigger).
  Operator lines carry the operator's own voice on the air
  (voice-recognisable and rememberable; a modulator makes it harder to place).
* **The desk seam.** A base station is a TRANSMIT device for whoever is
  SEATED at it (`seated_base_station`; worn/held gear still wins; `xmit` low,
  `to <console>, <msg>` overt). Whoever holds the chair holds the desk:
  attribution stays honestly the sitter's voice, so a seized board broadcasts
  the seizer, not the operator — and a dead console keys nothing (the
  sabotage gate). Switch it off or wreck it and dispatch goes silent.

### 2.2 · Channels

Traffic is organized by **channel**: a band on a megahertz dial, 1–999.9 at
one decimal (§6.3):

* **Open channels** — public bands anyone can tune (colony chatter). The
  civilian band is **88.8MHz = 'the Birdhouse'** (colony street name).
* **Org channels** — security's dispatch band (911MHz, the emergency band), a
  gang's band. **Tunable by anyone with the number** — secrecy is
  *procedural*, not cryptographic (scanner play: listen to security traffic
  if you find the band). Encryption/scrambling is a reserved later layer.
* A device holds one tuned band at a time; switching is a command. Scan mode
  catches every band, frequency-tagged.

### 2.3 · Range & propagation (the spatial consumer)

Phase 2 range (decided 2026-07-10, #1128). Range is wiring between machinery
that already exists.

* **Distance.** Rooms carry live (x,y,z). Range is grid distance: the larger
  of the x and y gaps plus the z gap (`world/radio.py` `_chebyshev`), measured
  speaker → receiver by `_deliver`.
* **Reach per device.** 12 cells (`RADIO_TX_RANGE`) for a handheld or comms
  organ; 20 (`MAST_TX_RANGE`) for a base station whose mast is standing; plus
  2 per storey of the transmitting room's height (`RANGE_ELEVATION_BONUS`) —
  rooftops matter, basements swallow signal.
* **Falloff is RENDERED, not binary.** `_deliver` grades every receiving set
  by distance / reach:
  * ≤ 0.7 (`RANGE_CLEAR_FRACTION`) — **clear**, every word.
  * 0.7–1.0 — **fuzzy**: clarity slides 1.0 → 0.2 through the existing
    letter-drop comprehension renderer (`_obscure_heard`; the mutter
    machinery doubles as signal degradation — "c-ver the b-ck d--r" at the
    fringe of coverage).
  * ≤ 1.15 (`RANGE_STATIC_FRACTION`) — **static**: an existence-only hiss, no
    speech payload, never elected (§7.2).
  * beyond — **gone**: silence.
* **The antenna is the RELAY.** A repeater is a powered on-band base station
  whose mast is not down (`mast_down`). A station never linked to a mast
  relays too, from its own room; a wrecked or deleted mast stops it. A
  repeater picks up traffic within the larger of the origin's reach and its
  own, and regenerates it clean at its own reach. One hop; no relay chains.
* **Links are RECIPROCAL.** Effective reach is the larger of both ends'
  antennae: the witness's handheld reaches dispatch because the console's mast
  is tall; repeaters pick up anything their own ears cover; wrecking the mast
  deafens dispatch as well as muting it.
* **Radio geography (#1311).** A mast-linked station transmits, receives and
  relays FROM ITS STEEL — the mast's position and elevation (`_antenna_site`,
  at all four seams). Each mast covers its own 20 cells (plus height), so the
  union of the antenna network has real edges and dead zones (911MHz goes
  thin in the deep southwest; the far north is silent), and holds only
  *while the antennae stand*. Kill the right antenna → a **coverage hole** (a
  district goes dark for that band). Wrecking the Constabulary mast collapses
  911MHz into walkie-range clusters — dispatch goes deaf AND quiet beyond a
  few blocks.
* **Fail-open off-grid.** A coordinate-less room hears everything (no
  regression off-grid), except Evennia's default home room, where deleted
  things land, which receives nothing (#2655).
* **Vertical matters**: rooftop antennae see far; the Drifts (`Z < 0` — the
  future mines/sewers) are naturally radio-dark unless wired repeaters are
  placed — mines and tunnels are out of contact by default (ties to the
  mining/S&R fiction: a collapse cuts contact). This Drifts-dark rule is
  unbuilt (§6.5).

**Masts in the world.** Every mast is a two-object standard: a mast structure
(`db.intact`, `db.breachable`) and a powered base-station cabinet linked to it
(`console.db.antenna`). Coverage follows the object.

* **The dispatch transmission mast** (#1124) — 'antenna mast' on the
  Constabulary roof, linked to the dispatch console. Wrecked (`db.intact`
  False) = no carrier on either voice path (acks and console answers).
* **The Queen of Cups house band** — a tenant-rigged 'antenna mast' (#5081)
  and 'repeater cabinet' (#5082, powered base station, antenna-linked), fixed
  on 88.8MHz. The cabinet sits on the z12 roof; the mast now lies in "The
  Fallen Antenna" parkour crossing at (-3,-15,12). Any handheld on the band is
  heard by the mast's ears (reciprocity) and regenerated — the civilian
  counterpart to the 911MHz dispatch mast, scan-discoverable, sabotage-able
  the same way.
* **The Brackett AWE Sentinel9** — mast #5641 on the climbable antenna
  platform at the mast head, (-10,-18,19); head-end cabinet #6027 in the
  basement Utility Room, antenna-linked. Retuned to 88.8MHz: two masts union
  the civilian band.

**Attack and repair (#1164).** `sabotage <structure>` and the shared `repair`
verb are channeled acts (90s / 180s) with visible tells, gated on
`db.breachable is True` on both masts. Wrecking stashes the authored prose and
repair restores it. A completed sabotage is a witnessed crime via
`report_crime`. Reciprocity makes it the heist: the wrecked mast can't carry
the report of its own wrecking. Infrastructure reuses the standard verbs; no
bespoke breaker commands.

### 2.4 · Speech over radio — voice, not text

Radio speech reuses the **voice system** (`world/voice.py`) end-to-end:

* A transmission renders with the speaker's **voice phrase** — and listeners
  run **voice recognition** (`get_apparent_voice_uid` / voice memory) exactly
  as if hearing them in the room. You can be *recognized by voice on the air*
  — a **voice modulator** (existing chrome) changes the voice and adds 3 to
  the speaker's side of the placing roll, but a listener who has named the
  natural voice can still place it.
* **Hearing-gated**: a deaf listener reads only that a radio crackled ("Your
  radio / A radio nearby crackles, but you can't make out a word.") and gets
  no words; the existing perception machinery applies.
* Radio voices are attributed by voice only — never by sight (you can't see
  the speaker). A voice the listener does not place is "A voice", and the
  speaker's voice phrase follows it when they have set one: `A voice crackles
  over the radio: *speaking Common, in a smoky rasp* "…"` (`world/radio.py`
  `_render_radio_line`). An NPC brain hears "a <description> voice", or "an
  unfamiliar voice" when none is set (`radio_voice_handle`).

## 3 · The dispatch chain rides radio

Mapping `NPC_DISPATCH_AND_SIMULATION_SPEC` §5.1's links onto the medium:

| Chain link | Radio reality | Attack |
|---|---|---|
| Witness report | witness NPC transmits on the emergency band from their walkie | **snatch the walkie** from their hand; harm them first; no device → they must physically travel to report |
| Dispatch order | base broadcasts to units on the security channel | jam the band; coverage hole (break the antenna) → units in the dark |
| Unit ↔ base | bots report/receive via built-in transceivers | EMP/destroy the transceiver component; *urgent* traffic rides radio |
| Intel-sync | **NOT radio (decided 2026-07-03): the force-wide intel/wanted sync is NET-driven** — it's a file on a host (`DECKING_MATRIX.md` §2/§10); radio carries voices, the net carries databases | hack the host (the marquee decking run), not the airwaves |
| Backup call | an engaged bot calls for reinforcement | mute the bot before it transmits (the no-trace window §5.1) |

*(Overturned intention: the intel-sync was first scoped to ride radio with
the base station as the sync point; the 2026-07-03 decision moved it to the
net.)*

A jammed/holed/deviceless link doesn't degrade gracefully into magic — **the
information simply does not arrive.** That hard rule is what makes sabotage
real play.

**The witness link (#1009).** The witness spawns with a real
`WALKIE_TALKIE` on the emergency band (911MHz), and `witness_report` gates on
it: snatch, break or knock out the witness = no report — a physical
interdiction besides killing them. Robbing them nets a walkie pre-tuned to
the cop channel.

**NPCs use the real verbs.** The witness readies and calls it in through the
actual player commands — `wield magpie` / `toggle magpie on` / `tune magpie
to 911MHz` at spawn, `xmit <report>` + `emote` at report — never a backdoor
`transmit()` call or a direct `db` write. The NPC path is identical to the
player path (level playing field; NPCs lead by example). Courier, hunt,
dispatch and witness voices all go through `xmit`.

## 4 · Command surface

* `transmit <message>` (also `xmit`, `xm`; add `on <device>` to pick one) —
  transmit low through a worn radio first, then one in hand, then the board
  you are seated at, then a built-in comms organ. No device, no voice on the
  air.
* `to <radio>, <message>` — transmit openly; the whole room hears.
* `tune <device> to <MHz|scan>` — retune (§6.3).
* `toggle <device> [on|off]` — a powered radio receives with no other command;
  traffic renders as heard speech (`A voice crackles over the radio: …`).
* `sabotage <structure>` / `repair` — attack and restore a mast (§2.3).
* Snatching rides existing systems: the grab/steal machinery
  (`STEALTH_AND_DETECTION_SPEC` §6.2 / wrest) for the walkie; jamming device
  TBD (§6.5, §8).

## 5 · Integration seams

* **Dispatch / director** — the §3 mapping; replaces the report placeholder.
* **Spatial** — range/coverage from `distance` / `rooms_within`; antennae live
  at real coordinates (kill *this* rooftop → *this* district's hole);
  the Drifts dark-by-default.
* **Voice / identity** — §2.4; voice recognition + modulators carry over.
* **Perception** — hearing gates reception; a transmission into a room is an
  auditory event: bystanders hear the grille. A hidden holder is not revealed
  by it; whether it should be is not decided (§8).
* **Robots** — the built-in transceiver is a chassis component
  (`ROBOT_SPECIES_AND_MOB_SPEC`), destroyable/EMP-able.
* **Phase/net** — reserved: a decker tapping/spoofing radio traffic from the
  net (a cross-phase window; `PHASE_LAYER_SPEC` §7).
* **Gigs/factions** — org channels give gangs/employers a coordination
  texture; a gig can arrive over the air.
* **NPC broadcasts (#1313/#1319)** — LLM radio-mode replies air via the real
  `xmit`, never room-say (§7.3). `world/director/broadcasts.py` gives flagged
  NPCs scheduled on-air segments (the Rook, sealed in the Brackett basement,
  is the first station voice). Venue **AWE Fireside shelf radios** fan the
  band to whole rooms via the grille rule (§6.1).

## 6 · Phase 1 — scoped & decided (2026-07-03)

The device layer: the *device* is the gate. A functional, powered, tuned
radio reaches the band; a snatched, broken, switched-off or absent one
doesn't. Range on top of it is §2.3. *(Overturned intention: Phase 1 first
abstracted range — Option A, network assumed present; Phase 2, 2026-07-10,
#1128, made it physical.)*

### 6.1 · Backend — ONE channel, the walkie sorts it out

**A single staff-locked Evennia Channel ("Radio") carries ALL traffic**; each
transmission is tagged with its **frequency**, and the tuned device filters at
echo time (decided 2026-07-03 — one channel beats channel-per-frequency):

* **Why one**: frequencies are a *dial* — a large number space (scanning /
  lucky guesses) — so per-frequency channels would mean unbounded channel
  creation/GC. One channel makes frequency pure data: retuning is a device
  attribute write, no subscription churn. And the admin gets **one log**: the
  entire grid as a single chronological stream — `[<frequency>] <Name>
  (<voice>): "…"` — which is both the live monitor and the forensic timeline.
  Per-band views are a filter, not an object.
* **Admin/builder view** — subscribe to the one channel: raw readout with
  Name, Voice/attribution metadata, and Frequency per line. History,
  persistence, and staff distribution come free from the channel system.
* **Player view** — players NEVER subscribe. A radio tuned to a frequency
  **echoes** matching traffic, re-rendered through the say/voice rails (§2.4).

**The four-perspective display model** (amended 2026-07-06; registers
playtest-decided 2026-07-07). *(Overturned intention: the echo was first
scoped to the holder alone; the speaker-grille stance of §2.4 extended it to
the rooms below.)*

1. **Speaker** — `You transmit on 911MHz: "…"`.
2. **Speaker's ROOM** — two registers:
   * `xmit` is keying the handset and speaking **LOW**. Each bystander rolls
     to catch it (listener Intellect vs speaker Resonance, the voice-discern
     pairing) and the MARGIN grades comprehension: a clean win hears every
     word, an even ear catches letter-dropped fragments ("c-ver the b-ck
     d--r" — shape and punctuation intact, letters lost), a bad miss gets
     only the act ("mutters something into the radio"). An NPC brain's speech
     payload carries exactly the fragments that listener heard, not the
     secret.
   * `to <radio>, <message>` is **openly** addressing the device — ordinary
     room speech, everyone hears (the full say rails, `says into the
     radio,`).
   * Whisper stays contentless to bystanders; the mutter sits between whisper
     and say.
3. **Remote listeners** — the crackle line, voice-only attribution,
   scan-tagged.
4. **A receiving radio's ROOM** — the grille is a speaker: traffic is audible
   to everyone in the radio's room (carried → the holder's room; lying on the
   floor → its room), hearing-gated per observer ("A radio nearby crackles…"
   for non-holders when deaf). Carrying a live radio is a stealth liability —
   as the `toggle` help says.
   * **Comms ORGANS stay internal** for receiving (in the ear = private to the
     unit). Transmitting through one is not private: the room hears the words
     in full, "<unit> says over comms, "…"", with no mutter roll
     (`transmit_organ`).
   * **Double render** (playtest-decided 2026-07-07): a matching radio beside
     the speaker DOES echo. With xmit's low voice this is load-bearing
     counter-play: you may fail to catch the mutter, but if your handset
     repeats it you've just learned you share their band — and heard the
     content anyway. *(Overturned intention: same-room echoes were first
     suppressed.)*

### 6.2 · Devices & acquisition

The **walkie-talkie item**: held/carried, powered, tuned to one frequency.
Acquisition = **all three**: vendor purchase (the store), loot (gangers /
security units carry them), and spawn kit where role-appropriate. Snatchable
via the existing theft/wrest machinery; breakable via ordinary damage.

Placement (2026-07-04): the **Colonial Armory** stocks `WALKIE_TALKIE` at
**0 tokens** (a live builder change to the hand-built shop object, not a
prototype), and the **ganger** civilian role carries one on a **~1-in-3**
roll (`chance_stock` in `world/director/civilians.py`) — a loot/frisk/steal
path. Witnesses spawn with an emergency-band walkie (#1009). Broader
vendor/loot spread waits on Phase 2 geography.

### 6.3 · Tuning & discovery

`tune <device> to <freq|scan>` — a radio hears only its tuned band (scan
hears all, frequency-tagged). **The dial reads megahertz (DECIDED
2026-07-06):** a band is a NUMBER, 1–999.9 MHz at one-decimal resolution (~10k
channels — searchable, not infinite), stored and displayed canonically
(`912` → `912MHz`, `911mhz` → `911MHz`; `CmdTune.func` writes
`normalize_band`); prose is refused ("'banana' isn't a frequency"). Band
matching is case-insensitive: `same_band` normalizes both sides, so a band
typed `911mhz` still reaches bots and constants stored as `911MHz`, and legacy
loose values keep matching.

Discovery is **scanning** (sweep bands and listen), **lucky guesses**, and
**captured walkies** (a lifted security handheld arrives tuned to their band
— the listening post). Secrecy is procedural, not cryptographic.

### 6.4 · The dispatch chain in Phase 1

* **Witness report** — the marquee: a witness NPC transmits its report from
  its OWN walkie on the emergency band. **Snatch or break the device before
  it keys up and the report never goes out** — silence-the-witness, literal,
  riding theft + dispatch.
* **Dispatch orders** — the force runs its own frequency: base-to-units
  traffic rides it (tunable by anyone who finds the band — scanner play
  against security).
* **Intel-sync** — explicitly NOT radio (§3): net-driven, owned by
  `DECKING_MATRIX.md`.

### 6.5 · Unbuilt

📋 UNBUILT (no issue): the Drifts-dark rule (§2.3), jamming devices,
**power/battery**, and encryption/scrambling. The robot built-in-transceiver
attacks beyond destroying the ear (EMP) ride the robot-component work.

Jamming is the inverse object of the antenna; battery is orthogonal to range.

## 7 · NPC radio comprehension

Radio reaches the NPC brains through the real device. **Payoff:** a dispatcher
who answers over the air, a fixer who calls a job in, a companion you can
raise from across the city, secbot chatter on the band — all through the real
device, all voice-attributed.

In short: delivery attaches the say-rails structured payload (`speech=` for
hearing listeners only) plus `radio_frequency` / `radio_elected`;
`LLMNpcMixin._hear_radio` (`typeclasses/llm_npc.py`) gates it like room
speech; the `radio` action tool keys the REAL `xmit`. Physical gates hold
throughout: delivery is the hearing gate, the command refusal is the mute
gate.

### 7.1 · Hearing — radio into the brain

A radio transmission delivered to an LLM NPC reaches `at_msg_receive` as
**heard words tagged as radio** — distinct from in-room speech, so the model
knows the source is the *air* (a remote voice), not the person beside it. The
turn frames it that way ("over the radio, <voice> says: …"). Radio turns
carry no visual perception. Attribution is **voice-only** (the echo render's
rule, `radio_voice_handle`, shared with the echo): the NPC recognises a known
voice (voice memory) or hears "a <description> voice" / "an unfamiliar
voice"; a modulator makes the voice harder to place (§2.4). Memory of a radio
turn is scoped to the VOICE identity (`voice:<uid>` subject threaded through
storage, so nothing cross-sensory leaks); when the NPC forgets a name, what it
filed under the voices that went with it is dropped too (#3861). The NPC hears
**only the band(s) its device is tuned to** — a unit on 911MHz hears 911MHz,
not the whole spectrum.

### 7.2 · Gating (the crux — saturation is the enemy)

Radio reaches *every* listener on a band at once, so ungated it would fire an
LLM turn on every NPC per squawk and saturate the single-threaded model. It
reuses the room-speech discipline exactly:

* **Directed radio** — the transmission names this NPC (callsign / name / role
  — "Unit 7, respond"; "all units"). Eligible to answer, subject to the
  directed cooldown.
* **Ambient radio** — general chatter. **Observe-only** into the action buffer
  (no LLM call), with the rare gated volunteer (`radio_ambient`; ambient
  cooldown + roll) — mirrors ambient poses/room-speech.
* **Loop guard** — an **NPC-sourced** transmission is never LLM-reacted (the
  `_is_npc_speaker` guard). This is load-bearing: the witness's report and any
  bot chatter are NPC-sourced, so bots hearing the witness don't spin up
  turns, and two NPCs on a band can't ping-pong.
* **"All units" de-confliction** — a broadcast addressed to many must not make
  *all* of them answer. One responds. The elected answerer (chosen in
  `_deliver`) is the lowest-dbref AI NPC that received the call on a radio it
  carries or its own comms organ, with words it could make out (clear or
  fuzzy); nothing chooses by nearness. Only a call containing a band-wide
  phrase ("all units", "any unit", "all stations", "anyone on this band",
  "anyone copy", "does anyone copy") waits for that NPC; an NPC named in the
  call answers itself, and one seated at a powered 911MHz board answers only
  after the souls layer has judged the call (§2.1). The rest observe — this
  is the multi-NPC de-confliction the LLM spec parks as future; radio is its
  first forcing case.

### 7.3 · Transmitting — the NPC keys up

Through the **real command** (the execute-cmd mandate), never a backdoor: a
`radio` **action tool** in the LLM turn schema (archetype-scoped — granted to
the merchant, dispatcher, dj and security archetypes and withheld from
bartender, companion, doctor, colonist and butcher), routed to `xmit`. `xmit`'s
no-handheld fallback keys a built-in comms organ (`transmit_organ`), so bots
and any future implanted player transmit through the identical command. The
persona/context carries the NPC's radio state ("you carry a walkie tuned to
911MHz", or the bot's comms organ) so the model knows it *can*. A radio-heard
turn does not choose (#2585): its reply goes to the NPC's real `xmit` and is
not spoken in the room, and if `xmit` refuses nothing is said (§7.5). When the
model also calls the radio tool, that call carries the transmission and the
reply's speech is spoken in the room.

### 7.4 · Security bots come along for free

Secbots are `LLMNpc` + a comms organ. §7.1–7.3 give them **gated radio
voice** with no new plumbing: a bot hears a report and its LLM brain may key
up ("Unit responding, en route") — *flavour* — while the **deterministic
dispatch (`raise_event` + hunt) stays authoritative** for the actual action.
Clean split: the director moves the body, the LLM works the mic.

### 7.5 · The physical gate holds

No new perception path around the device: an NPC hears/speaks radio only with
a **powered, tuned** device (walkie or intact comms organ). Snatch the walkie,
break it, destroy the ear → the NPC goes deaf/mute exactly as the mechanics
enforce for the witness and the EMP-muted bot. Comprehension rides the same
physical gate players do.

**Refusals too (2026-10-26, #2585).** Owner: "NPCs and players should seem
identical. We can't have NPCs cheating." A radio turn's words go to `xmit` and
nowhere else; the brain never renders them to the room. `xmit` refuses an NPC
as it refuses a player (no radio worn or in hand and no working comms organ,
switched off, sweeping, untuned), and every such refusal carries
`type="refusal"` (`world.perception.REFUSAL`; the channel gate's "You're busy
… — 'stop' first" carries it too). A player reads it on their screen; the LLM
brain buffers it as a witnessed event ("You could not: …") so the next turn
can act on it (`wield` the radio in its pocket), and the turn in flight does
not remember the refused words as said; a scripted voice (courier, hunt,
dispatch, witness — all through `xmit`) simply fails like a player who is not
looking. Any other command's refusal may carry the same tag and is heard the
same way.

The radio's own refusals also name their verb (`verb="transmit"`; the channel
gate's refusal does not), and a soul hearing that verb raises the **comms**
goal (NPC_NEEDS_AND_GOALS §3.9, #3777): the think tree takes the handheld out
of the pocket and switches it on through `wield` and `toggle`, the same
commands a player would type.

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
  over the air. The turn framing (§7.1) must be unambiguous. A radio turn's
  reply goes to `xmit`, never to the room, unless the model also calls the
  radio tool (§7.3).

## 8 · Risks & open questions

Not decided:

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
* **Hidden holders** — a transmission into a room does not reveal a hidden
  holder; whether it should (§5).

## 9 · Related documents

* `NPC_DISPATCH_AND_SIMULATION_SPEC` §5.1 — the dispatch information chain.
* `DECKING_MATRIX.md` §2/§10 — the net-driven intel-sync.
* `STEALTH_AND_DETECTION_SPEC` §6.2 — grab/steal/wrest.
* `ROBOT_SPECIES_AND_MOB_SPEC` — the chassis transceiver.
* `PHASE_LAYER_SPEC` §7 — the reserved cross-phase tap.
* NPC_NEEDS_AND_GOALS §3.9 — the comms goal.
